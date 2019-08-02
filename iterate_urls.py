import os
import random
from concurrent.futures import ThreadPoolExecutor
from time import sleep

from pandas.io.json import json_normalize

from souper import *

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


    # Some simple assertions to make sure it's working correctly
    assert visit_url("http://www.destinasjonroros.no", save=False)["regexes"]["phone"]["total"] == 1
    assert visit_url("http://www.teknamotor.sk", save=False)["norwegian_version"]["url"]
    assert visit_url("https://www.infosoft.se", save=False)["norwegian_version"]["url"]
    assert visit_url("https://simplisoftware.se/", save=False)["norwegian_version"]["scheme"] == "href-norway-full"
    assert visit_url("http://hespe.blogspot.com", save=False)["language"]["text_bytes_found"] > 0
    assert visit_url("https://www.dedicare.se/", save=False)["norwegian_version"]["scheme"] == "href-norway-full"
    assert visit_url("https://bodilmunch.blogspot.com/", save=False)["norwegian_version"][
               "scheme"] == "href-norway-partial"
    assert visit_url("https://blog.e-hoi.de", save=False)["norwegian_version"]["scheme"] == "href-norway-partial"

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
