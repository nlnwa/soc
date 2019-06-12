import os
import re
import socket
from http.client import IncompleteRead
from ssl import CertificateError
from urllib.error import HTTPError, URLError
from urllib.request import urlopen, urlparse

from bs4 import BeautifulSoup
from geoip2.database import Reader

from languagemodel import LanguageModel, split_and_clean

reader = Reader('res/GeoIP2-Country.mmdb')

def get_text(url):
    with urlopen(url, timeout=10) as html:
        soup = BeautifulSoup(html)
        txt = ""
        for p in soup.findAll('p'):
            txt += p.text

        return txt


def geo(url):
    try:
        data = urlopen(url)
        ip = socket.gethostbyname(urlparse(data.geturl()).hostname)
        response = reader.country(ip)

        return response.country.iso_code == "NO"
    except socket.gaierror:
        return False



def reg(txt):
    phone = re.search(r"\+47( ?\d){8}", txt) is not None  # eg. "+47 51 99 00 00"
    name = re.search(r"nor(w(ay|egian)|ge|eg|sk)", txt, re.IGNORECASE) is not None
    counties = re.search(r"akershus|aust.?agder|buskerud|finnmark|hedmark|hordaland|møre|romsdal|nordland|oppland|oslo|"
                         r"rogaland|sogn|fjordane|telemark|troms|trøndelag|vest.?agder|vestfold|østfold",
                         txt, re.IGNORECASE) is not None
    return phone or name or counties


if __name__ == '__main__':
    model = LanguageModel(["no", "other"], weights="LM3.h5")
    for file in os.listdir("res/oos_liste_03.01.19"):
        if not re.match("uri_(\W|no)", file):
            f = open(f"res/oos_liste_03.01.19/{file}")
            for url in f:
                url = url.strip()
                try:
                    print(url)
                    # if geo(url):
                    #     print("Norwegian")

                    txt = get_text(url)

                    split = [s for s in split_and_clean(txt)]

                    # for s in split:
                    #     if reg(s):
                    #         print(url)
                    #         print(s)

                    # for s in split:
                    #     if geo(s):
                    #         print(s)

                    pre = model.predict(split, raw=True)
                    for p, s in zip(pre, split):
                        if p[0] > 0.5:
                            print(p[0], s)

                    # if get_info(url)["country_code"] == "NO":
                    #     print(url)

                except (HTTPError, CertificateError, URLError, ConnectionResetError, IncompleteRead):
                    pass
                    # print("Error")
