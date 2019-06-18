import json
import os
import re
import socket
import requests
from urllib.parse import urlparse, urlunparse
from http.client import IncompleteRead
from ssl import CertificateError
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

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
postal_codes = "|".join(expressions["postal"])
norway_names = "|".join(expressions["norway_names"])
counties = "|".join(expressions["counties"])

# Patterns
pattern_names = re.compile(f"{ensure_start}(({boy_names}|{girl_names}) ({surnames})){ensure_end}")
pattern_postal = re.compile(postal_codes, re.IGNORECASE)
pattern_phone = re.compile(r"([^\d]|^)((\(?(\+|00)?47\)?)( ?\d){8})([^\d]|$)")  # eg. "+47 51 99 00 00"
pattern_norway = re.compile(f"{ensure_start}(norwegian|norsk|{norway_names}){ensure_end}", re.IGNORECASE)
pattern_counties = re.compile(f"{ensure_start}({counties}){ensure_end}", re.IGNORECASE)


def get_text(url):
    with urlopen(url, timeout=10) as html:
        # https://stackoverflow.com/questions/1936466/beautifulsoup-grab-visible-webpage-text/1983219#1983219
        soup = BeautifulSoup(html, "html.parser")

        for link in soup.findAll("a", href=True):
            # print(link.text)
            if ".no" in link["href"]:
                print("Nor:", link["href"])
            # if pattern_norway.search(link.text):
            #     print("Nor:", link["href"])
            # print(link["href"])

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
    return [p[1] for p in phones]


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


                    parsed = urlparse(url)
                    base_url = parsed.netloc
                    url_parts = base_url.split('.')
                    if url_parts[-1] != "no":
                        url_parts[-1] = "no"
                        new_base_url = ""
                        for part in url_parts:
                            new_base_url += part + "."

                        new_base_url = new_base_url[:-1]
                        # print(new_base_url)
                        new_full_url = urlunparse((parsed.scheme, new_base_url, parsed.path, parsed.params, parsed.query, parsed.fragment))
                        try:
                            r = requests.head(new_full_url)
                            if r.status_code == 200 or 301 or 302:
                                print("There exists a possible norwegian version at this page:", new_full_url)
                        except requests.ConnectionError:
                            # print("failed to connect")
                            pass


                    postal_value = 0
                    phone_value = 0
                    county_value = 0
                    name_value = 0
                    norway_value = 0
                    geo_value = 0

                    if len(postal):
                        postal_value = len(postal)

                    if len(phone):
                        phone_value = len(phone)

                    if len(county):
                        county_value = len(county)

                    if len(name):
                        name_value = len(name)

                    if len(norway):
                        norway_value = len(norway)

                    if geoloc and geoloc == 'NO':
                        geo_value = 1

                    postal_value = postal_value * 2
                    phone_value = phone_value * 0.5
                    county_value = county_value * 1
                    name_value = name_value * 0.3
                    norway_value = norway_value * 0.2
                    geo_value = geo_value * 0.05

                    score = norwegian + postal_value + phone_value + county_value + name_value + norway_value + geo_value
                    # print("Score: ", score)
                    if score > 2:
                        print("Probably norwegian")


                    print("Norwegian:", norwegian)
                    print("Postal:", "Score:", postal_value, postal)
                    print("Phone:", "Score:", phone_value, phone)
                    print("County:", "Score:", county_value, county)
                    print("Name:", "Score:", name_value, name)
                    print("Norway:", "Score:", norway_value, norway)
                    print("Geo:", "Score:", geo_value, geoloc)
                    print("Total score:", score)

                except (HTTPError, CertificateError, URLError, ConnectionResetError, IncompleteRead, socket.timeout):
                    pass
