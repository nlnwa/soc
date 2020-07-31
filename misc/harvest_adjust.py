import logging
import time
from concurrent.futures.thread import ThreadPoolExecutor
from io import BytesIO
from sched import scheduler
from threading import RLock, Thread

import requests
from warcio import WARCWriter, StatusAndHeaders
import numpy as np

from misc.util import html_to_counters, HtmlResult, ExpDecayModel
from souper import HEADERS

daf_args = ["default_delay", "target", "history"]


class DelayAdjuster:
    def __init__(self, default_delay: int, target: float):
        self.default_delay = default_delay
        self.mean_squared_error = 0
        if 0 < target < 1:
            self.target = target
        else:
            raise ValueError

    def add_case(self, timestamp: float, result: HtmlResult):
        raise NotImplementedError

    def get_delay(self):
        raise NotImplementedError

    def __str__(self):
        return f"{self.__class__.__name__}(default_delay={self.default_delay},target={self.target})"


class ConstantDelayAdjuster(DelayAdjuster):
    def __init__(self, default_delay: int):
        super().__init__(default_delay, 0.5)

    def add_case(self, timestamp: float, result: HtmlResult):
        pass

    def get_delay(self):
        return self.default_delay


class SimpleDelayAdjuster(DelayAdjuster):
    def __init__(self, default_delay: int, target: float):
        super().__init__(default_delay, target)
        self.last = None
        self.current = None

    def add_case(self, timestamp: float, result: HtmlResult):
        self.last = self.current
        self.current = (timestamp, result)

    def get_delay(self):
        if self.last is not None:
            return self.default_delay
        (ts0, res0), (ts1, res1) = self.last, self.current
        cur_delay = ts1 - ts0
        sim = res0.similarity(res1)
        return cur_delay * (1 + 1 / (1 - self.target)) ** (sim - self.target)
        # return cur_delay * sim / self.target


class BisectionDelayAdjuster(DelayAdjuster):
    def __init__(self, default_delay: int, target: float):
        super().__init__(default_delay, target)
        self.initial = (0., 1 - target)
        self.hist = [self.initial]
        self.last = None  # Last result for comparing

    def add_case(self, timestamp: float, result: HtmlResult):
        if self.last is not None:
            x = timestamp - self.last[0]
            y = result.similarity(self.last[1]) - self.target
            self.hist.append((x, y))
        self.last = (timestamp, result)

    def get_delay(self):
        if len(self.hist) < 2:
            return self.default_delay
        xs, ys = zip(*self.hist)
        params = np.polyfit(xs, ys, 1, w=np.arange(1, len(self.hist) + 1, 1))
        a, b = params[0], params[1]
        sol = (self.target - b) / a  # Solution to ax+b=t
        if sol <= 0:
            x, y = self.hist[-1]
            return x * (1 + 1 / (1 - self.target)) ** y
        return sol


class ReciprocalDelayAdjuster(DelayAdjuster):
    """
    Tries to fit a reciprocal function f(x)=(1-a)*b/(x+b)+a to the results, and solves f(x)=target for new delay.
    Reciprocal is easier to solve than exponential since exponential requires numerical analysis whereas the
    reciprocal function can be solved symbolically, however they share some of the same properties
    (f(0)=1, f(∞)=0, decreasing), and are pretty much equally good at estimating similarity change in testing.
    Reciprocal should also be preferable to bisection or secant in that it mimics the actual function better,
    which should provide a better estimate.
    """

    def __init__(self, default_delay: int, target: float):
        super().__init__(default_delay, target)
        self.last_xy = None
        self.current_xy = None
        self.last = None

    def add_case(self, timestamp: float, result: HtmlResult):
        if self.last is not None:
            ts0, res0 = self.last
            self.last_xy = self.current_xy
            self.current_xy = (timestamp - ts0, result.similarity(res0))
        self.last = timestamp, result

    def get_delay(self):
        if self.current_xy is None:
            return self.default_delay
        elif self.last_xy is None:
            x, y = self.current_xy
            a = 0  # Assumed to make it solvable
            b = x * y / (1 - y) if y < 1 else 0
            if b <= 0:
                return x * (1 + 1 / (1 - self.target)) ** (y - self.target)
        else:
            x0, y0 = self.last_xy
            x1, y1 = self.current_xy
            if y0 == y1 == 1:  # Both a and b would give division by zero
                return x1 * (1 + 1 / (1 - self.target)) ** (1 - self.target)
            a = (x0 * y0 * (y1 - 1) - x1 * y1 * (y0 - 1)) / (x0 * (y1 - 1) - x1 * (y0 - 1))
            b = (x0 * x1 * (y0 - y1)) / (x0 * (y1 - 1) - x1 * (y0 - 1))
            if b <= 0 or not 0 <= a < self.target:
                if x0 < x1 and y0 > y1 or x1 < x0 and y1 > y0:
                    my0 = y0 - self.target
                    my1 = y1 - self.target
                    return (x0 * my1 - x1 * my0) / (my1 - my0)  # Fallback on regula falsi
                return x1 * (1 + 1 / (1 - self.target)) ** (y1 - self.target)

        return b * (1 - self.target) / (self.target - a)


class AverageDelayAdjuster(DelayAdjuster):
    def __init__(self, default_delay: int, target: float, decay_factor: float = 0.8):
        super().__init__(default_delay, target)
        self.decay_factor = decay_factor
        self.hist = []
        self.memo = {}

    def add_case(self, timestamp: float, result: HtmlResult):
        for ts, res in self.hist:
            self.memo[(ts, timestamp)] = result.similarity(res)
        self.hist.append((timestamp, result))

    def get_delay(self):
        tot = self.target
        n = 1
        now = self.hist[-1][0]
        for (ts0, ts1), sim in self.memo.items():
            diff = (ts1 - ts0) / self.default_delay
            age = (now - (ts1 + ts0) / 2) / self.default_delay
            w = len(self.memo) * self.decay_factor ** (age + 1 / diff) + 1
            tot += w * sim ** (1 / diff)
            n += w
        est = tot / n
        return ExpDecayModel().inv_eval(self.target, est, 0) * self.default_delay


class Harvester:
    def __init__(self, name, default_delay=3600, n_thread=None):
        file = open(f"{name}.warc.gz", "wb")
        self.writer = WARCWriter(file)
        self.lock = RLock()
        self.scheduler = scheduler(time.time)
        self.executor = ThreadPoolExecutor(n_thread)
        self.default_delay = default_delay
        self.delay_adjusters = {}  # Constant delay
        self.last = {}

    def visit(self, url):
        ts0 = time.time()
        resp = requests.get(url, headers=HEADERS, stream=True)
        ts1 = time.time()
        headers_list = resp.raw.headers.items()
        http_headers = StatusAndHeaders('200 OK', headers_list, protocol='HTTP/1.0')
        record = self.writer.create_warc_record(resp.url, 'response',
                                                payload=BytesIO(resp.content),
                                                http_headers=http_headers)
        self.lock.acquire()
        self.writer.write_record(record)
        self.lock.release()
        res = html_to_counters(resp.content)
        return res, (ts1 + ts0) / 2

    def foo(self, target, website, lower_limit, upper_limit):
        try:
            sr1, ts1 = self.visit(website)

            delay_adjuster = self.delay_adjusters[website]
            delay_adjuster.add_case(ts1, sr1)
            estimate = delay_adjuster.get_delay()

            new_delay = max(lower_limit, min(upper_limit, estimate))

            self.scheduler.enterabs(ts1 + new_delay, 1, self.executor.submit,
                                    (self.foo, target, website, lower_limit, upper_limit))

            if logging.root.level <= logging.INFO:
                delay = None
                sim = None
                ts0, sr0 = self.last.get(website, (None, None))
                self.last[website] = (ts1, sr1)
                if ts0 is not None and sr0 is not None:
                    sim = sr0.similarity(sr1)
                    delay = ts1 - ts0
                logging.info(
                    f"website={website}, delay={delay}, sim={sim}, estimate={estimate}, new_delay={new_delay}")
        except Exception as e:
            logging.exception(e)
            logging.exception(f"website={website}")

    def harvest(self, websites, target, delay_adjuster=None):
        logging.info(f"Starting harvest with {len(websites)} websites and delay adjuster "
                     f"{str(delay_adjuster)}, target={target}")
        start_time = time.time() + 10
        diff = self.default_delay / len(websites)  # Distribute initial harvests equally
        for ws in websites:
            if delay_adjuster is None:
                self.delay_adjusters[ws] = ConstantDelayAdjuster(self.default_delay)
            else:
                self.delay_adjusters[ws] = delay_adjuster(self.default_delay, target)
            start_time += diff
            self.scheduler.enterabs(start_time, 1, self.executor.submit, (self.foo, target, ws, 60, 86400))
        while True:
            try:
                self.scheduler.run()
            except Exception as e:
                logging.exception(e)
                logging.exception(f"Exception occured: {e}, stopping harvest...")
                return


def create_and_harvest(name, urls, da, targ, dd=3600):
    logging.basicConfig(filename=f"{name}.log", level=logging.INFO)
    harvester = Harvester(name, default_delay=dd)
    t = Thread(target=harvester.harvest, args=(urls, targ, da))
    t.start()
    return harvester


if __name__ == '__main__':
    urls = sorted(set(s.strip() for s in open("misc/news.txt")))
    create_and_harvest("test", urls[:16], ReciprocalDelayAdjuster, 0.9, dd=60)
