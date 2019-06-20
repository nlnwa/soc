import json
import os
import random
import re
import socket
from collections import Counter
from http.client import IncompleteRead
from itertools import chain
from ssl import CertificateError
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
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

        # for link in soup.findAll("a", href=True):
        #     # print(link.text)
        #     if ".no" in link["href"]:
        #         print("Nor:", link["href"])
        #     # if pattern_norway.search(link.text):
        #     #     print("Nor:", link["href"])
        #     # print(link["href"])

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


def has_norwegian(txt, domain):
    try:
        is_reliable, bytes_found, details = pycld2.detect(txt, isPlainText=True, hintTopLevelDomain=domain)
        if is_reliable:
            for lang, code, percent, score in details:
                if code in ["no", "nn"]:
                    return bytes_found, percent, score
                    # nor_score = bytes_found * percent * score
                    # return nor_score
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


# TODO sjekk URL på nytt etter redirect?

def iter_urls(urls):
    for url in urls:
        url = url.strip()
        try:
            # DataFrame()
            print(url)

            txt = get_text(url)
            domain = url.split(".")[-1]

            bytes_found, percentage, score = has_norwegian(txt, domain)
            postal = has_postal(txt)
            phone = has_phone_number(txt)
            county = has_county(txt)
            name = has_name(txt)
            norway = has_norway(txt)
            geoloc = geo(url)

            # parsed = urlparse(url)
            # base_url = parsed.netloc
            # url_parts = base_url.split('.')
            # if url_parts[-1] != "no":
            #     url_parts[-1] = "no"
            #     new_base_url = ""
            #     for part in url_parts:
            #         new_base_url += part + "."
            #
            #     new_base_url = new_base_url[:-1]
            #     # print(new_base_url)
            #     new_full_url = urlunparse(
            #         (parsed.scheme, new_base_url, parsed.path, parsed.params, parsed.query, parsed.fragment))
            #     try:
            #         r = requests.head(new_full_url)
            #         if r.status_code == 200 or 301 or 302:
            #             print("There exists a possible norwegian version at this page:", new_full_url)
            #     except requests.ConnectionError:
            #         # print("failed to connect")
            #         pass

            fw.write(
                f"{url},{domain},{bytes_found / 1000},{percentage},{score},{len(postal)},{sum(postal.values())},{len(phone)},"
                f"{sum(phone.values())},{len(county)},{sum(county.values())},{len(name)},"
                f"{sum(name.values())},{len(norway)},{sum(norway.values())},{geoloc}\n")

            # print("Score: ", score)
            # if score > 2:
            #     print("Probably norwegian")

            # print("Norwegian:", norwegian)
            # print("Postal:", "Score:", postal_value, postal)
            # print("Phone:", "Score:", phone_value, phone)
            # print("County:", "Score:", county_value, county)
            # print("Name:", "Score:", name_value, name)
            # print("Norway:", "Score:", norway_value, norway)
            # print("Geo:", "Score:", geo_value, geoloc)
            # print("Total score:", score)

        except (HTTPError, CertificateError, URLError, ConnectionResetError, IncompleteRead, socket.timeout):
            pass


if __name__ == '__main__':
    # df = DataFrame.from_csv("uri_scores.csv", index_col=None)
    #
    # df["Norwegian"] = df["Norwegian"].apply(lambda x: log(x + 1) if x >= 0 else 0)
    # fltr = df["URL"].str.contains(r"\.no$")
    # df = df[~fltr]
    #
    # df.to_csv("uri_scores_log_nono.csv", index=False)
    #
    # exit(0)

    fw = open("uri_scores3.csv", "w")
    fw.write("URL,Domain,KBytes,Percentage,Score,Postal_t,Postal_u,Phone_t,Phone_u,County_t,County_u,Name_t,Name_u,Norway_t,Norway_u,Geoloc\n")
    # model = LanguageModel(["no", "other"], weights="LM6.h5")
    i = 0
    it = []
    files = os.listdir("res/oos_liste_03.01.19")
    random.shuffle(files)  # Hopefully distributes urls evenly
    for file in files:
        if not re.match(r"uri_(\W)", file):
            f = open(f"res/oos_liste_03.01.19/{file}")
            it.append(f)
            if i == 100:
                i = 0
                t = Thread(target=iter_urls, args=(chain.from_iterable(it),))
                t.start()
            i += 1
            # iter_urls(f)
