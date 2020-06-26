import re
import time
from collections import Counter
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime
from io import BytesIO
from sched import scheduler
from threading import RLock

from warcio import WARCWriter, StatusAndHeaders
from warcio.warcwriter import BufferWARCWriter
import requests

from misc.util import jaccard, find_new_delay
from souper import HEADERS, get_text

# global_tracker = capture_http()
file = open("tracked.warc.gz", "wb")
writer = WARCWriter(file)
lock = RLock()


def visit(site):
    ts0 = time.time()
    resp = requests.get(site, headers=HEADERS, stream=True)
    ts1 = time.time()
    headers_list = resp.raw.headers.items()
    http_headers = StatusAndHeaders('200 OK', headers_list, protocol='HTTP/1.0')
    record = writer.create_warc_record(resp.url, 'response',
                                       payload=BytesIO(resp.content),
                                       http_headers=http_headers)
    lock.acquire()
    writer.write_record(record)
    lock.release()
    t = get_text(resp.content)
    c = Counter(re.split("\\W+", t.lower()))
    return c, (ts1 + ts0) / 2


def foo(website, lower_limit, upper_limit):
    try:
        last = info[website]["last"]
        target = info[website]["target"]
        c1, ts1 = visit(website)

        if last is not None:
            c0, ts0 = last
            sim = jaccard(c0, c1)
            delay = ts1 - ts0

            # Pretty good and very simple
            # estimate = delay * sim / target

            # Should be more accurate since based on formula
            estimate = find_new_delay(delay, sim, target)

            new_delay = max(lower_limit, min(upper_limit, estimate))
        else:
            new_delay = default_delay
        info[website]["last"] = c1, ts1
        info[website]["visits"] += 1
        if (n := info[website]["visits"]) % 10 == 0:
            print(website, n)
        s.enter(new_delay, 1, ex.submit, (foo, website, lower_limit, upper_limit))
    except Exception as e:
        print(e)


if __name__ == '__main__':
    websites = [s.strip() for s in open("misc/news.txt")][:10]
    print(websites)
    # t_func, = lambda: datetime.utcnow(),

    default_delay = 3600

    s = scheduler(time.time)
    ex = ThreadPoolExecutor(16)
    info = {
        ws: {
            "last": None,
            "target": 0.7,
            "visits": 0
        }
        for ws in websites
    }
    start_time = time.time() + 60
    diff = default_delay / len(websites)  # Distribute initial harvests equally
    for ws in websites:
        start_time += diff
        s.enterabs(start_time, 1, ex.submit, (foo, ws, 60, 86400))
    while True:
        s.run()
