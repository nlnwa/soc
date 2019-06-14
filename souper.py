import json
import os
import re
import socket
from http.client import IncompleteRead
from ssl import CertificateError
from urllib.error import HTTPError, URLError
from urllib.request import urlopen, urlparse

import pycld2
from bs4 import BeautifulSoup
from geoip2.database import Reader

reader = Reader('res/GeoIP2-Country.mmdb')

expressions = json.load(open("res/expressions.json"))

ensure_start = "([^[A-ZÆØÅa-zæøå]|^)"
ensure_end = "([^[A-ZÆØÅa-zæøå]|$)"

boy_names = "|".join(expressions["boy_names"])
girl_names = "|".join(expressions["girl_names"])
surnames = "|".join(expressions["surnames"])
postal = "|".join(expressions["postal"])
norway_names = "|".join(expressions["norway_names"])
counties = "|".join(expressions["counties"])

# Patterns
pattern_names = re.compile(f"{ensure_start}(({boy_names}|{girl_names}) ({surnames})){ensure_end}")
pattern_postal = re.compile(postal, re.IGNORECASE)
pattern_phone = re.compile(r"((\(?(\+|00)?47\)?)( ?\d){8})")  # eg. "+47 51 99 00 00"
pattern_norway = re.compile(f"{ensure_start}(norwegian|norsk|{norway_names}){ensure_end}", re.IGNORECASE)
pattern_counties = re.compile(f"{ensure_start}({counties}){ensure_end}", re.IGNORECASE)


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

        return response.country.iso_code
    except socket.gaierror:
        return False


def has_norwegian(txt):
    try:
        is_reliable, bytes_found, details = pycld2.detect(txt, isPlainText=True)
        if is_reliable:
            for lang, code, percent, score in details:
                if code in ["no", "nn"]:
                    nor_score = bytes_found * percent * score / 1.5e7
                    return nor_score
        return 0
    except pycld2.error:
        return -1


def has_name(txt):
    names = pattern_names.findall(txt)
    return [n[1] for n in names]


def has_postal(txt):
    postals = pattern_postal.findall(txt)
    return postals


def has_phone_number(txt):
    phones = pattern_phone.findall(txt)
    return [p[0] for p in phones]


def has_norway(txt):
    nor = pattern_norway.findall(txt)
    return [n[1] for n in nor]


def has_county(txt):
    cou = pattern_counties.findall(txt)
    return [c[1] for c in cou]


if __name__ == '__main__':
    # model = LanguageModel(["no", "other"], weights="LM6.h5")
    for file in os.listdir("res/oos_liste_03.01.19"):
        if not re.match("uri_(\W|no)", file):
            f = open(f"res/oos_liste_03.01.19/{file}")
            for url in f:
                url = url.strip()
                try:
                    print(url)

                    txt = get_text(url)

                    norwegian = has_norwegian(txt)
                    postal = has_postal(txt)
                    phone = has_phone_number(txt)
                    county = has_county(txt)
                    name = has_name(txt)
                    norway = has_norway(txt)
                    geoloc = geo(url)

                    print("Norwegian:", norwegian)
                    print("Postal:", postal)
                    print("Phone:", phone)
                    print("County:", county)
                    print("Name:", name)
                    print("Norway:", norway)
                    print("Geo:", geoloc)

                except (HTTPError, CertificateError, URLError, ConnectionResetError, IncompleteRead, socket.timeout):
                    pass
