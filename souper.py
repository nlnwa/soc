import csv
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


def _get_names(file, delimiter=";"):
    source = open("res/etternavn.csv")
    rdr = csv.reader(source, delimiter=delimiter)
    names = ""
    for row in rdr:
        names += row[0][0].upper() + row[0][1:].lower() + "|"

    names = names[5:-1]
    return names


surnames = _get_names("res/etternavn.csv")
boy_names = _get_names("res/guttenavn_alle.csv")
girl_names = _get_names("res/jentenavn_alle.csv")

rex = f"(({boy_names})|({girl_names})) ({surnames})"

# Postal code + city
source = open("res/Postnummerregister-ansi.txt", encoding="iso 8859-1")
rdr = csv.reader(source, delimiter="\t")
postal = ""

for row in rdr:
    postal += row[0] + " " + row[1] + "|"

postal = postal[:-1]

# Patterns
pattern_names = re.compile(rex)
pattern_postal = re.compile(postal, re.IGNORECASE)
pattern_phone = re.compile(r"(\(?(\+|00)?47\)?)( ?\d){8}")  # eg. "+47 51 99 00 00"

norway_names = "an Iorua|Naraoẏe|নরওয়ে|Na Uy|Nirribhidh|Noorweë|Noorwegen|Norge|Noreg|Noregur|Noreuwei|Norŭwei|노르웨이|" \
               "Norga|Norge|Norja|Norra|Norsko|Nórsko|Noruega|Noruwega|Noruwē|ノルウェー|Norveç|Norvèg·e|Norvège|" \
               "Norvegia|Norvégia|Norvehia|Норвегія|Norvēģija|Norvegija|Norvegio|Norvegiya|Норвегия|Norvegiya" \
               "|נורבגיה|" \
               "in-Norveġja|Norvegjia|Norvegye|נאָרװעגיע|Norveška|Норвешка|Norveška|Norvigía|Νορβηγία|Norway|" \
               "Norway|නෝර්වේ|Norweege|Norwegen|Norwègia|Norwegia|Norwegska|Norwéy|ኖርዌይ|Norwij|Nowe|นอร์เวย์|" \
               "Norwy|Nuówēi|挪威|Nuruwai|நோர்வே"

pattern_norway = re.compile(f"{norway_names}|norwegian|norsk", re.IGNORECASE)
pattern_counties = re.compile(
    r"akershus|aust.?agder|buskerud|finnmark|hedmark|hordaland|møre|romsdal|nordland|oppland|oslo|"
    r"rogaland|sogn|fjordane|telemark|troms|trøndelag|vest.?agder|vestfold|østfold", re.IGNORECASE)

assert pattern_phone.search("(+47) 902 51 088")


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


def has_name(txt):
    names = pattern_names.search(txt)
    return names is not None


def has_postal(txt):
    postal = pattern_postal.search(txt)
    return postal is not None


def has_phone_number(txt):
    phone = pattern_phone.search(txt)
    return phone is not None


def has_norway(txt):
    nor = pattern_norway.search(txt)
    return nor is not None


def has_county(txt):
    cou = pattern_counties.search(txt)
    return cou is not None


def has_any_regex(txt):
    return has_name(txt) or has_postal(txt) or has_phone_number(txt) or has_norway(txt) or has_county(txt)


if __name__ == '__main__':
    # model = LanguageModel(["no", "other"], weights="LM6.h5")
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
                        is_reliable, bytes_found, details = pycld2.detect(txt, isPlainText=True)
                        if is_reliable:
                            for lang, code, percent, score in details:
                                if code in ["no", "nn"]:
                                    nor_score = bytes_found * percent * score / 1.5e7
                                    print("NORWEGIAN", nor_score, details)
                    except pycld2.error:
                        print(f"ERROR")

                    if has_postal(txt):
                        print("POSTAL")

                    if has_phone_number(txt):
                        print("PHONE")

                    if has_county(txt):
                        print("COUNTY")

                    if has_name(txt):
                        print("NAME")

                    if has_norway(txt):
                        print("NORWAY")

                    # split = [s for s in split_and_clean(txt)]

                    # for s in split:
                    #     if has_any_regex(s):
                    #         print(url)
                    #         print(s)

                    # for s in split:
                    #     if geo(s):
                    #         print(s)
                except (HTTPError, CertificateError, URLError, ConnectionResetError, IncompleteRead, socket.timeout):
                    pass
                    # print("Error")
