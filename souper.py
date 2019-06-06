import os
import re
from ssl import CertificateError
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from bs4 import BeautifulSoup

from languagemodel import LanguageModel

url = "https://en.wikipedia.org/wiki/Machine_learning"


def get_text(url):
    with urlopen(url, timeout=10) as html:
        soup = BeautifulSoup(html)
        txt = ""
        for p in soup.findAll('p'):
            txt += p.text

        return txt


if __name__ == '__main__':
    model = LanguageModel(["nob", "nno", "other"], weights="LanguageModel-3-40.hdf5")
    for file in os.listdir("res/oos_liste_03.01.19"):
        if not re.match("uri_(\W|no)", file):
            f = open(f"res/oos_liste_03.01.19/{file}")
            for url in f:
                try:
                    print(url)
                    txt = get_text(url)
                    split = re.split("[.?!\n]", txt)
                    pre = model.predict(split)
                    for p, s in zip(pre, split):
                        if p == "nob" or p == "nno":
                            print(s)
                except (HTTPError, CertificateError, URLError):
                    print("Error")
