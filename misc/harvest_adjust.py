import math
import re
from collections import Counter
from concurrent.futures.thread import ThreadPoolExecutor
from time import sleep

import pandas as pd

from WebPage import WebPage


def jaccard(A, B):
    intersect = A & B
    absA = sum(A.values())
    absB = sum(B.values())
    absI = sum(intersect.values())
    return absI / (absA + absB - absI)


global_tracker = []


def track(website, init_delay=900, target=0.7, lower_limit=60, upper_limit=86400):
    delay = init_delay

    # tracker = []

    wp1 = WebPage.from_url(website)
    c1 = Counter(re.split("\\W+", wp1.text.lower()))
    global_tracker.append(wp1.extra_info)
    while True:
        sleep(delay)
        wp0 = wp1
        c0 = c1
        wp1 = WebPage.from_url(website)
        c1 = Counter(re.split("\\W+", wp1.text.lower()))

        global_tracker.append(wp1.extra_info)

        sim = jaccard(c0, c1)
        # delay *= sim / target
        delay = max(lower_limit, min(upper_limit, delay * sim / target))

    # return tracker


if __name__ == '__main__':
    websites = [s.strip() for s in open("misc/news.txt")]
    with ThreadPoolExecutor(len(websites)) as ex:
        ex.map(track, websites)
        while True:
            sleep(3600)
            print("Saving...")
            df = pd.json_normalize(global_tracker)
            df.to_csv("tracked.csv")
            print(f"Saved (len={len(df)})")
