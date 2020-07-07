import logging
import math
import time
from concurrent.futures.thread import ThreadPoolExecutor
from io import BytesIO
from sched import scheduler
from threading import RLock, Thread

import requests
from warcio import WARCWriter, StatusAndHeaders

from misc.util import jaccard, text_to_counter, fit_similarity, inverse_exponential_decay
from souper import HEADERS, get_text

daf_args = ["default_delay", "target", "history"]


def simple_adjust_func(default_delay, target, history):
    if len(history) == 0:
        return default_delay
    t0, t1, sim = history[-1]
    current_delay = t1 - t0
    return current_delay * sim / target


def fit_adjust_func(default_delay, target, history):
    # Example function which uses history
    base = simple_adjust_func(default_delay, target, history)
    if len(history) < 5:
        return base
    ts_diffs, sims = zip(*[((t1 - t0) / 3600, sim) for t0, t1, sim in history[-64:]])
    func, params, fitness = fit_similarity(ts_diffs, sims)
    if params[0] >= 0.99:  # Fallback to prevent excessive result
        params[0] = 0.99
    estimate = inverse_exponential_decay(target, params[0], 0) * 3600  # Function uses hours
    if math.isnan(estimate) or math.isnan(fitness):
        return base
    return fitness * estimate + (1 - fitness) * base


class Harvester:
    def __init__(self, name, default_delay=3600, delay_adjust_func=None, n_thread=None):
        file = open(f"{name}.warc.gz", "wb")
        self.writer = WARCWriter(file)
        self.lock = RLock()
        self.scheduler = scheduler(time.time)
        self.executor = ThreadPoolExecutor(n_thread)
        self.default_delay = default_delay
        self.delay_adjust_func = delay_adjust_func or (lambda x, *_: x)  # Constant delay
        self.history = {}

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
        t = get_text(resp.content)
        c = text_to_counter(t)
        return c, (ts1 + ts0) / 2

    def foo(self, c0, ts0, target, website, lower_limit, upper_limit):
        try:
            # last = info[website]["last"]
            # target = info[website]["target"]
            c1, ts1 = self.visit(website)

            if c0 is None or ts0 is None:
                new_delay = self.default_delay
                logging.info(f"website={website}")
                self.history.setdefault(website, [])
            else:
                sim = jaccard(c0, c1)
                delay = ts1 - ts0

                hist = self.history[website]
                hist.append((ts0, ts1, sim))
                estimate = self.delay_adjust_func(self.default_delay, target, hist)

                new_delay = max(lower_limit, min(upper_limit, estimate))
                logging.info(f"website={website}, delay={delay}, sim={sim}, estimate={estimate}, new_delay={new_delay}")

            self.scheduler.enterabs(ts1 + new_delay, 1, self.executor.submit,
                                    (self.foo, c1, ts1, target, website, lower_limit, upper_limit))
        except Exception as e:
            logging.warning(f"Error: {e}, website={website}")

    def harvest(self, websites, target):
        logging.info(f"Starting harvest with {len(websites)} websites and delay function "
                     f"{self.delay_adjust_func.__name__}, target={target}")
        start_time = time.time() + 60
        diff = self.default_delay / len(websites)  # Distribute initial harvests equally
        for ws in websites:
            start_time += diff
            self.scheduler.enterabs(start_time, 1, self.executor.submit, (self.foo, None, None, target, ws, 60, 86400))
        while True:
            try:
                self.scheduler.run()
            except Exception as e:
                logging.warning(f"Exception occured: {e}, stopping harvest...")
                return


def create_and_harvest(name, urls, daf, targ, dd=3600):
    logging.basicConfig(filename=f"{name}.log", level=logging.INFO)
    harvester = Harvester(name, default_delay=dd, delay_adjust_func=daf)
    t = Thread(target=harvester.harvest, args=(urls, targ))
    t.start()
    return harvester


if __name__ == '__main__':
    from misc.util import find_new_delay

    urls = sorted(set(s.strip() for s in open("misc/news.txt")))
    create_and_harvest("tracked", urls, find_new_delay, 0.9)
