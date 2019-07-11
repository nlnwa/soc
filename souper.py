import json
import os
import random
import re
import socket
from collections import Counter, namedtuple
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus
from http.client import IncompleteRead
from ssl import CertificateError
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen, Request

import pandas as pd
import pycld2
import requests
from bs4 import BeautifulSoup
from geoip2.database import Reader
from math import tanh, atanh

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
pattern_kroner = re.compile(r"(\d+ ?(kr(oner)?|NOK)(?=([^\w]|$)))", re.IGNORECASE)


def get_text(connection):
    html = connection
    # https://stackoverflow.com/questions/1936466/beautifulsoup-grab-visible-webpage-text/1983219#1983219
    soup = BeautifulSoup(html, "html.parser")

    [s.extract() for s in soup(['style', 'script', '[document]', 'head', 'title'])]

    return soup.getText()


def geo(connection):
    ip = get_ip(connection)
    response = reader.country(ip)

    return response.country.iso_code


def has_norwegian(txt, domain):
    try:
        is_reliable, bytes_found, details = pycld2.detect(txt, isPlainText=True, hintTopLevelDomain=domain)
        if is_reliable:
            p, s, n = 0, 0, 0
            for lang, code, percent, score in details:
                if code in ["no", "nn"]:
                    p += percent
                    s += score
                    n += 1
            return bytes_found, p, s / (n or 1)
        return bytes_found, 0, 0
    except pycld2.error:
        return 0, 0, 0


def has_name(txt):
    names = pattern_names.findall(txt)
    return Counter(n[1] for n in names)


def has_postal(txt):
    postals = pattern_postal.findall(txt)
    return Counter(postals)


def has_phone_number(txt):
    phones = pattern_phone.findall(txt)
    return Counter(p[1].replace(" ", "") for p in phones)


def has_norway(txt):
    nor = pattern_norway.findall(txt)
    return Counter(n[1] for n in nor)


def has_county(txt):
    cou = pattern_counties.findall(txt)
    return Counter(c[1] for c in cou)


def has_kroner(txt):
    kr = pattern_kroner.findall(txt)
    return Counter(k[0] for k in kr)


def get_ip(connection):
    ip = socket.gethostbyname(urlparse(connection.geturl()).hostname)
    return ip


def get_domain(url):
    parsed = urlparse(url)
    base_url = parsed.netloc
    url_parts = base_url.split('.')
    return url_parts[-1]


def has_norwegian_version(connection):
    url = connection.geturl()
    parsed = urlparse(url)
    base_url = parsed.netloc
    url_parts = base_url.split('.')

    if url_parts[-1] == "no":
        return -1, None

    url_parts[-1] = "no"

    new_base_url = ".".join(url_parts)

    new_url = urlunparse(
        (parsed.scheme, new_base_url, parsed.path, parsed.params, parsed.query, parsed.fragment))

    try:
        redir = requests.get(new_url)

        if (redir.status_code == HTTPStatus.OK
                or redir.status_code == HTTPStatus.MOVED_PERMANENTLY
                or redir.status_code == HTTPStatus.FOUND):

            new_connection = urlopen(new_url)
            ip_o = get_ip(new_connection)
            ip_n = get_ip(connection)

            i = 0
            for o, n in zip(ip_o.split("."), ip_n.split(".")):
                if o == n:
                    i += 1
                else:
                    break
            if i > 0:
                return i, new_connection
    except (requests.ConnectionError, requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError, requests.exceptions.TooManyRedirects, socket.timeout):
        pass
    return 0, None


WebPageValues = namedtuple("WebPageValues",
                           ["o_url", "r_url", "geo", "no_ver", "dom", "bytes", "percentage", "score", "nor_score",
                            "postal_u", "postal_t", "phone_u", "phone_t", "county_u", "county_t", "names_u",
                            "names_t", "norway_u", "norway_t", "kroner_u", "kroner_t", "raw_html"])


def normalize(x, midpoint):
    # Normalizes such that
    # x == 0 -> 0,
    # x == midpoint -> 0.5,
    # x == ∞ -> 1
    return tanh(x * atanh(0.5) / midpoint)


class WebPage:
    def __init__(self, orig_url, redirect_url, raw_html, geo_loc, norwegian_version=None):
        self.orig_url = orig_url
        self.redirect_url = redirect_url
        self.raw_html = raw_html
        self.geo_loc = geo_loc
        self.norwegian_version = norwegian_version

    @staticmethod
    def from_url(url):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/70.0.3538.77 Safari/537.36"}
        req = Request(url=url, headers=headers)
        conn = urlopen(req, timeout=30)
        html = str(conn.read(), "utf-8", errors='replace')
        geoloc = geo(conn)
        redir = conn.geturl()

        no_ver = has_norwegian_version(conn)
        if no_ver[1] is not None:
            no_ver = no_ver[1].geturl()
        else:
            no_ver = None

        del conn  # Disconnect
        return WebPage(orig_url=url, redirect_url=redir, raw_html=html, geo_loc=geoloc, norwegian_version=no_ver)

    def get_text(self):
        return get_text(self.raw_html)

    def get_ip(self):
        return get_ip(self.redirect_url)

    def is_norwegian(self):
        norwegian = self.values().nor_score * 1.6
        postal = self.values().postal_u * 2
        phone = self.values().phone_u * 0.3
        county = self.values().county_t * 0.6
        names = self.values().names_u * 0.2
        norway = self.values().norway_t * 0.15
        kroner = self.values().kroner_u * 0.05
        geo_score = 0
        if self.geo_loc and self.geo_loc == "NO":
            geo_score = 1.0
        score = norwegian + postal + phone + county + names + norway + kroner + geo_score
        print("Total score:", score)
        score = normalize(score, 1.4)
        print("Normalized score:", score)

        print("Norwegian score:", norwegian, " (", self.values().nor_score, ")")
        print("Postal score:", postal)
        print("Phone score:", phone)
        print("County score:", county)
        print("Name score:", names)
        print("Norway score:", norway)
        print("Kroner score:", kroner)
        print("Geo ip:", geo_score)

        return score

    def values(self):
        # dom = get_domain(self.orig_url)

        dom = get_domain(self.redirect_url)

        txt = self.get_text()

        b, p, s = has_norwegian(txt, domain=dom)

        nor_score = normalize(b * p * s, 1e7)  # 200*100*500 gives 50%

        postal = has_postal(txt)
        phone = has_phone_number(txt)
        county = has_county(txt)
        name = has_name(txt)
        norway = has_norway(txt)
        kroner = has_kroner(txt)

        txt = re.sub(r"[\s,\"'’`©]+", " ", self.get_text())  # Remove csv-troublesome characters

        return WebPageValues(self.orig_url, self.redirect_url, self.geo_loc, self.norwegian_version, dom, b, p, s,
                             nor_score, len(postal), sum(postal.values()), len(phone), sum(phone.values()), len(county),
                             sum(county.values()), len(name), sum(name.values()), len(norway), sum(norway.values()),
                             len(kroner), sum(kroner.values()), txt)


def iter_urls(url):
    try:
        # print(url)

        wp = WebPage.from_url(url)

        for k, v in wp.values()._asdict().items():
            d[k].append(v)

        score = wp.is_norwegian()

        print("Probability Norvegica:", score)

        if score > 0.70:
            print("It's på norsk", url, "\n")

        elif score > 0.5:
            print("Possibly norwegian, do manual check", url, "\n")

        else:
            print("Not norsk:", url, "\n")

    except (HTTPError, CertificateError, URLError, ConnectionResetError, IncompleteRead, socket.timeout) as e:
        # print(url, e)
        pass


if __name__ == '__main__':
    # print(pd.DataFrame.from_csv("uri_scores.csv"))

    d = {k: [] for k in WebPageValues._fields}
    files = os.listdir("res/oos_liste_03.01.19")

    urls = []

    for file in files:
        if not re.match(r"uri_(\W|_)", file):
            f = open(f"res/oos_liste_03.01.19/{file}")

            urls += [url.strip() for url in f]

    random.shuffle(urls)

    print(len(urls))
    for url in urls:
        iter_urls(url)

    # with ThreadPoolExecutor(max_workers=16) as pool:
    #     future = pool.map(iter_urls, urls[:100])

    # df = pd.DataFrame.from_dict(d)
    # df.to_csv("uri_scores.csv", index=False)
