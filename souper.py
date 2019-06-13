import os
import re
import socket
import csv
from http.client import IncompleteRead
from ssl import CertificateError
from urllib.error import HTTPError, URLError
from urllib.request import urlopen, urlparse

import pycld2
from bs4 import BeautifulSoup
from geoip2.database import Reader

from languagemodel import LanguageModel, split_and_clean

reader = Reader('res/GeoIP2-Country.mmdb')


def get_text(url):
    with urlopen(url, timeout=10) as html:
        # https://stackoverflow.com/questions/1936466/beautifulsoup-grab-visible-webpage-text/1983219#1983219
        soup = BeautifulSoup(html, "html.parser")

        [s.extract() for s in soup(['style', 'script', '[document]', 'head', 'title'])]

        return soup.getText()


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

    # Names
    # Etternavn
    source = open("res/etternavn.csv")
    rdr = csv.reader(source, delimiter = ";")
    etternavn = ""
    for row in rdr:
        etternavn += row[0][0].upper() + row[0][1:].lower() + " |"

    etternavn = etternavn[5:-1]
    #print(etternavn)


    # Fornavn gutter
    source = open("res/guttenavn_alle.csv")
    rdr = csv.reader(source, delimiter=";")
    guttenavn = ""
    for row in rdr:
        guttenavn += " " + row[0][0].upper() + row[0][1:].lower() + " |"

    guttenavn = guttenavn[5:-1]
    #print(guttenavn)

    # Fornavn jenter
    source = open("res/jentenavn_alle.csv")
    rdr = csv.reader(source, delimiter=";")
    jentenavn = ""
    for row in rdr:
        jentenavn += " " + row[0][0].upper() + row[0][1:].lower() + " |"

    jentenavn = jentenavn[5:-1]
    #print(jentenavn)


    rex = f"(({guttenavn})|({jentenavn}))({etternavn})"
    #print(rex)
    person_names = re.search(rex, txt) is not None


    # Postal code + city
    source = open("res/Postnummerregister-ansi.txt", encoding="iso 8859-1")
    rdr = csv.reader(source, delimiter="\t")
    postnummer = ""

    for row in rdr:
        postnummer += row[0] + " " + row[1] + "|"

    postnummer = postnummer[:-1]

    location = re.search(postnummer, txt, re.IGNORECASE) is not None

    #phone or name or counties or person_names or location
    return phone or name or counties or person_names or location


if __name__ == '__main__':
    # model = LanguageModel(["no", "other"], weights="LM3.h5")
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

                    try:
                        lang = pycld2.detect(txt, isPlainText=True)
                        print(lang)
                        # if lang == "NORWEGIAN":
                        #     print(s)
                    except pycld2.error:
                        print(f"ERROR")

                    split = [s for s in split_and_clean(txt)]

                    for s in split:
                        if reg(s):
                            print(url)
                            print(s)

                    # for s in split:
                    #     if geo(s):
                    #         print(s)
                except (HTTPError, CertificateError, URLError, ConnectionResetError, IncompleteRead, socket.timeout):
                    pass
                    # print("Error")
