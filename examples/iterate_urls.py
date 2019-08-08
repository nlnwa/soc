import os
import random
from concurrent.futures import ThreadPoolExecutor
from time import sleep

from pandas.io.json import json_normalize

from souper import *

# Iterates through OOS list and writes information to CSV
if __name__ == '__main__':
    responses = []

    def visit_url(url, save=True):
        """
        Visits URL and adds to dict, returns WebPageValues
        """
        try:
            wp = WebPage.from_url(url)

            val = wp.values()

            # pprint(val)

            if save:
                responses.append(val)

            return val
        except (HTTPError, CertificateError, URLError, ConnectionResetError, IncompleteRead, socket.timeout,
                socket.gaierror) as err:
            print(url, err)
            pass

    urls = []

    files = os.listdir("res/oos_liste_03.01.19")

    for file in files:
        if not re.match(r"uri_(\W|_)", file):
            f = open(f"res/oos_liste_03.01.19/{file}")
            urls += [url.strip() for url in f]

    random.shuffle(urls)

    print(len(urls))

    with ThreadPoolExecutor(max_workers=16) as pool:
        pool.map(visit_url, urls, timeout=120)
        while not pool._work_queue.empty():
            print("Sleeping")
            sleep(1000)
            print("Slept")
            try:
                df = json_normalize(responses)
                df.to_csv("uri_scores.csv", index=False)
                print("CSV saved")
            except ValueError as e:
                print(e)
        pool.shutdown(False)

    # in case it actually finishes
    df = json_normalize(responses)
    df.to_csv("uri_scores.csv", index=False)
