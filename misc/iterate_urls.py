import os
import random
import time
from concurrent.futures import ThreadPoolExecutor
from http.client import IncompleteRead
from ssl import CertificateError
from time import sleep
from urllib.error import HTTPError, URLError

import pandas as pd

from norvegica.WebPage import WebPage
from norvegica.souper import *


def visit_urls(urls, fn, repeat=1, delay=1000):
    responses = []

    def visit_url(url, save=False):
        """
        Visits URL and adds to dict, returns WebPageValues
        """
        try:
            wp = WebPage.from_url(url)

            val = wp.extra_info

            # pprint(val)

            if save:
                responses.append(val)

            return val
        except (HTTPError, CertificateError, URLError, ConnectionResetError, IncompleteRead, socket.timeout,
                socket.gaierror) as err:
            print(url, err)
            pass

    print(len(urls))
    t0 = time.time()

    def save(fn):
        try:
            df = pd.json_normalize(responses)
            cols = list(df.columns)
            cols.remove("text")
            df = df[cols + ["text"]]
            df.to_csv(fn, index=False)
            t1 = time.time()
            print(f"CSV saved (t={t1 - t0:.1f},l={len(responses)})")
        except ValueError as e:
            print(e)

    target = time.time()
    for n in range(repeat):
        print(n)
        with ThreadPoolExecutor(max_workers=16) as pool:
            for res in pool.map(visit_url, urls, timeout=delay):
                if res:
                    responses.append(res)
            save(f"{fn}_temp.csv")
            target += delay
            remaining = target - time.time() - 5
            print(f"Sleeping for {remaining:.1f} seconds")
            sleep(remaining)
            print("Slept")
            while time.time() < target:
                pass

    # in case it actually finishes
    save(f"{fn}.csv")


def get_oos_urls():
    urls = set()

    files = os.listdir("res/oos")

    for file in files:
        if not re.match(r"uri_(\W|_)", file):
            f = open(f"res/oos/{file}")
            for url in f:
                urls.add(url.strip())
    return urls


def get_news_urls():
    return [s.strip() for s in open("misc/news.txt")]


# Iterates through OOS list and writes information to CSV
if __name__ == '__main__':
    urls = list(get_news_urls())
    random.shuffle(urls)
    sleep(2100)
    visit_urls(urls, "news2", 720, 3600)
