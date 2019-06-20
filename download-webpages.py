import os
import random
import re
import socket
import urllib
from http.client import IncompleteRead
from itertools import chain
from ssl import CertificateError
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from bs4 import BeautifulSoup

base_path = "res/webpages"


# df = DataFrame.from_csv("uri_scores3.csv", index_col=None)
# df["Domain"] = df["Domain"] == "no"
# df["Domain"].fillna("other", inplace=True)
# df["Geoloc"] = df["Geoloc"] == "no"
# df["Geoloc"].fillna("other", inplace=True)
# df.to_csv("uri_scores4.csv", index=False)


def url_iterate(urls):
    for url in urls:
        url = url.strip()
        try:
            with urlopen(url, timeout=10) as html:
                # https://stackoverflow.com/questions/1936466/beautifulsoup-grab-visible-webpage-text/1983219#1983219
                soup = BeautifulSoup(html, "html.parser")

                [s.extract() for s in soup(['style', 'script', '[document]', 'head', 'title'])]

                scheme, netloc, *rest = urllib.request.urlparse(url)
                path = f"{base_path}/{scheme}-{netloc}.txt"
                with open(path, "x") as w:
                    w.write(f"{url}\n")
                    w.write(soup.getText())
        except (HTTPError, CertificateError, URLError, ConnectionResetError, IncompleteRead, socket.timeout):
            pass


if __name__ == '__main__':
    i = 0
    it = []
    files = os.listdir("res/oos_liste_03.01.19")
    random.shuffle(files)  # Hopefully distributes urls evenly
    for file in files:
        if not re.match(r"uri_(\W)", file):
            f = open(f"res/oos_liste_03.01.19/{file}")
            # url_iterate(f)
            it.append(f)
            if i == 100:
                i = 0
                t = Thread(target=url_iterate, args=(chain.from_iterable(it),))
                t.start()
            i += 1
