import socket
from collections import Counter
from http.client import HTTPResponse
from typing import Optional
from urllib.parse import urlparse

import pycld2
from bs4 import BeautifulSoup, Tag
from geoip2.database import Reader

from patterns import *

NO_MATCH = "no_match"
REPLACE = "replace"
HREF_NORWAY_LINK = "href-norway-link"
HREF_NORWAY_PARTIAL = "href-norway-partial"
HREF_LANG = "href-lang"
HREF_NORWAY_FULL = "href-norway-full"
HREF_HREFLANG = "href-hreflang"
HREF_HREFLANG_REL = "href-hreflang-rel"
ALREADY_NO = "already_no"
SCHEMES = ALREADY_NO, HREF_HREFLANG_REL, HREF_NORWAY_FULL, HREF_HREFLANG, HREF_LANG, \
          REPLACE, HREF_NORWAY_PARTIAL, HREF_NORWAY_LINK, NO_MATCH  # Ordered from best to worst

reader = Reader('res/GeoIP2-Country.mmdb')


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/70.0.3538.77 Safari/537.36"}


# Methods
def has_name(txt: str) -> Counter:
    names = pattern_names.findall(txt)
    return Counter(n[1] for n in names)


def has_postal(txt: str) -> Counter:
    postals = pattern_postal.findall(txt)
    return Counter(postals)


def has_phone_number(txt: str) -> Counter:
    phones = pattern_phone.findall(txt)
    return Counter(p[1].replace(" ", "") for p in phones)


def has_norway(txt: str) -> Counter:
    nor = pattern_norway.findall(txt)
    return Counter(n[1] for n in nor)


def has_county(txt: str) -> Counter:
    cou = pattern_counties.findall(txt)
    return Counter(c[1] for c in cou)


def has_kroner(txt: str) -> Counter:
    kr = pattern_kroner.findall(txt)
    return Counter(k[0] for k in kr)


def has_email(txt: str) -> Counter:
    mail = pattern_email.findall(txt)
    return Counter(m for m in mail if m.endswith(".no"))


def get_text(connection_or_html) -> str:
    """
    Uses BeautifulSoup to get text from HTML
    """
    # https://stackoverflow.com/questions/1936466/beautifulsoup-grab-visible-webpage-text/1983219#1983219
    soup = BeautifulSoup(connection_or_html, "html.parser")

    [s.extract() for s in soup(['style', 'script', '[document]', 'head', 'title'])]

    txt = soup.get_text(separator=" ").strip()
    txt = re.sub(r"\s+", " ", txt)

    return txt


def geo(ip: str) -> str:
    """
    Attempts to find geolocation of connection from IP.
    """
    response = reader.country(ip)

    return response.country.iso_code


def detect_language(html: Optional[str] = None, txt: Optional[str] = None,
                    domain: Optional[str] = None, http_lang: Optional[str] = None) -> dict:
    """
    Uses cld2 to detect languages, and formats into dict.
    If both html and txt is supplied, it will attempt to pick the best one.

    :param domain: domain of web page, used to weight languages.
    :param html: the html of the page.
    :param txt: the extracted text from the page.
    :param http_lang: HTTP language header
    :return: is_reliable, bytes_found, details
    """
    irh, bfh, dth = False, 0, []  # HTML result
    irt, bft, dtt = False, 0, []  # Text result

    # Sometimes the cld2 html parser gives different results than BeautifulSoup
    # The cld2 html result is slightly preferred due to more in-depth analysis
    if html:
        try:
            irh, bfh, dth = pycld2.detect(html, isPlainText=False, hintTopLevelDomain=domain,
                                          hintLanguageHTTPHeaders=http_lang)
        except pycld2.error:
            pass

    if txt:
        if irh and bfh > len(txt):  # No point in raw text detection
            is_reliable, bytes_found, details = irh, bfh, dth
        else:
            try:
                txt = re.sub(r"\W+", " ", txt)  # To prevent invalid characters
                irt, bft, dtt = pycld2.detect(txt, isPlainText=True, hintTopLevelDomain=domain,
                                              hintLanguageHTTPHeaders=http_lang)
            except pycld2.error:
                pass

            # Picks most reliable
            if irh and not irt:
                is_reliable, bytes_found, details = irh, bfh, dth
            elif irt and not irh:
                is_reliable, bytes_found, details = irt, bft, dtt

            # Picks largest
            elif bft > bfh:
                is_reliable, bytes_found, details = irt, bft, dtt
            else:
                is_reliable, bytes_found, details = irh, bfh, dth
    else:
        is_reliable, bytes_found, details = irh, bfh, dth

    if not details:
        details = [("Unknown", "un", 0, 0)] * 3  # Fill missing values to ensure size

    details = {str(i): {"language_name": ln, "language_code": lc, "percent": p, "score": s} for i, (ln, lc, p, s) in
               enumerate(details)}  # Dict instead of string for constant size

    resp = {"is_reliable": is_reliable, "text_bytes_found": bytes_found, "details": details}

    return resp


def norwegian_score(is_reliable: bool, details: dict) -> (int, float):
    """
    Uses cld2 to find Norwegian.

    :param is_reliable: whether or not the detection is reliable.
    :param details: the details from the language detection.
    :return: bytes found, percentage of bytes in Norwegian, weighted average score for Norwegian.
    """
    # Gives a small score reduction if the prediction is unreliable
    reliability = 1.0 if is_reliable else 0.5

    p, s = 0, 0
    for d in details.values():
        lang, code, percent, score = d["language_name"], d["language_code"], d["percent"], d["score"]
        if code in ["no", "nn"] and percent > 1:
            # Due to rounding up we sometimes get 1% where it really is closer to 0%
            p += percent
            s += score * percent
    return p, reliability * s / (p or 1)


def get_ip(connection: HTTPResponse) -> str:
    """
    Finds IP of connection.
    """
    ip = socket.gethostbyname(urlparse(connection.geturl()).hostname)
    return ip


def get_domain(url: str) -> str:
    """
    Gets domain from URL. E.g. "https://stackoverflow.com/" -> "com"
    """
    parsed = urlparse(url)
    base_url = parsed.netloc
    url_parts = base_url.split('.')
    return url_parts[-1]


def normalize(x: float, midpoint: float, lim: float = 1.0) -> float:
    """
    Normalizes such that
    x == 0 -> 0,
    x == midpoint -> lim / 2,
    x == ∞ -> lim

    :param x: the value to normalize.
    :param midpoint: the point at which the function reaches the halfway point.
    :param lim: the maximal value of the function.
    :return: the normalized result.
    """
    return lim * (1 - 0.5 ** (x / midpoint)) if x > 0 else 0.0


def place_tag(t: Tag) -> str:
    """
    Analyzes a HTML tag and returns the associated scheme.
    """
    if not t.get("href"):
        return NO_MATCH

    # Schemes are ordered from presumed strongest to weakest
    # Method recommended by Google to specify alternate versions of page
    # https://support.google.com/webmasters/answer/189077?hl=en
    rel = t.get("rel", "")
    hreflang = t.get("hreflang", "")
    pat = re.compile("alternat(e|ive)")
    if t.name == "link" and pattern_no_html_lang.search(hreflang) and any(pat.search(r) for r in rel):
        return HREF_HREFLANG_REL

    # Full matches Norway regex in text with repetitions
    pat = re.compile(f"^(\\W*({expressions['norway_names']}|no|bokmål|nynorsk))+\\W*$", re.I)
    title = t.get("title", "")
    if t.name == "a" and (pat.search(t.get_text(separator=" ")) or pat.search(t.get("title", ""))):
        return HREF_NORWAY_FULL

    # Other hreflang links
    if pattern_no_html_lang.search(hreflang):
        return HREF_HREFLANG

    # Matches Norwegian lang tag
    lang = t.get("lang", "")
    if pattern_no_html_lang.search(lang):
        return HREF_LANG

    # Matches Norway regex in text
    if t.name == "a" and (pattern_norway.search(t.get_text(separator=" ")) or pattern_norway.search(title)):
        return HREF_NORWAY_PARTIAL

    # Matches Norway regex in link
    pat = re.compile(f"{expressions['norway_names']}|bokmål|nynorsk")
    hr = t.get("href", "")
    if t.name == "a" and pat.search(hr):
        return HREF_NORWAY_LINK

    return NO_MATCH


