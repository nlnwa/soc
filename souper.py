import json
import re
import socket
from collections import Counter
from http import HTTPStatus
from http.client import IncompleteRead
from ssl import CertificateError
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen, Request

import pycld2
from bs4 import BeautifulSoup
from geoip2.database import Reader

reader = Reader('res/GeoIP2-Country.mmdb')

expressions = json.load(open("res/expressions.json"))

ensure_start = r"((?<=\W)|(?<=^))"  # Split up because lookbehind requires fixed width
ensure_end = r"(?=\W|$)"

boy_names = "|".join(expressions["boy_names"])
girl_names = "|".join(expressions["girl_names"])
surnames = "|".join(expressions["surnames"])
postal_codes = "|".join(expressions["postal"])
norway_names = "|".join(expressions["norway_names"])
counties = "|".join(expressions["counties"])

# Patterns
pattern_names = re.compile(f"{ensure_start}(({boy_names}|{girl_names}) ({surnames})){ensure_end}")
pattern_postal = re.compile(postal_codes, re.IGNORECASE)
pattern_phone = re.compile(r"([^\d]|^)((\(?(\+|00)?47\)?)(\W?\d){8})([^\d]|$)")  # eg. "+47 51 99 00 00"
pattern_norway = re.compile(f"{ensure_start}({norway_names}){ensure_end}", re.IGNORECASE)
pattern_counties = re.compile(f"{ensure_start}({counties}){ensure_end}", re.IGNORECASE)
pattern_kroner = re.compile(r"(\d+ ?(kr(oner)?|NOK))" + ensure_end, re.IGNORECASE)
pattern_email = re.compile(r"(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\"(?:["
                           r"\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")@("
                           r"?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:25["
                           r"0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|["
                           r"a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\["
                           r"\x01-\x09\x0b\x0c\x0e-\x7f])+)\])")  # https://emailregex.com/

pattern_kr_dom = re.compile("se|dk|is|fo|gl", re.IGNORECASE)  # Domains of countries that use kr
pattern_kr_lan = re.compile("sv|da|is|fo|kl", re.IGNORECASE)  # Language codes of countries that use kr
pattern_no_html_lang = re.compile("^(no|nb|nn|nno|nob|nor)|bokmaal|nynorsk", re.IGNORECASE)  # Norwegian HTML lang names

# All country code top level domains
pattern_cctld = re.compile("ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bl|bm|bn"
                           "|bo|br|bq|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cw|cx|cy|cz"
                           "|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl"
                           "|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp"
                           "|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mf|mg|mh|mk"
                           "|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe"
                           "|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|sk|sl|sm"
                           "|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk"
                           "|um|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zr|zw")


# Test the patterns
assert pattern_names.fullmatch("Jan Hansen")
assert pattern_postal.fullmatch("8624 Mo i Rana")
assert pattern_phone.fullmatch("+47 23 27 60 00")
assert pattern_norway.fullmatch("Norge")
assert pattern_counties.fullmatch("Nordland")
assert pattern_kroner.fullmatch("420 kr")
assert pattern_email.fullmatch("nb@nb.no")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/70.0.3538.77 Safari/537.36"}


# Methods
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


def has_email(txt):
    mail = pattern_email.findall(txt)
    return Counter(m for m in mail if m.endswith(".no"))


def get_text(connection_or_html):
    """
    Uses BeautifulSoup to get text from HTML
    """
    # https://stackoverflow.com/questions/1936466/beautifulsoup-grab-visible-webpage-text/1983219#1983219
    soup = BeautifulSoup(connection_or_html, "html.parser")

    [s.extract() for s in soup(['style', 'script', '[document]', 'head', 'title'])]

    txt = soup.getText(separator=" ").strip()
    txt = re.sub(r"\s+", " ", txt)

    return txt


def geo(connection):
    """
    Attempts to find geolocation of connection from IP.
    """
    ip = get_ip(connection)
    response = reader.country(ip)

    return response.country.iso_code


def detect_language(html=None, txt=None, domain=None):
    """
    Uses cld2 to detect languages, and formats into dict.

    :param domain: domain of web page, used to weight languages.
    :param html: the html of the page.
    :param txt: the extracted text from the page.
    :return: is_reliable, bytes_found, details
    """
    is_reliable, bytes_found, details = False, 0, []
    irh, bfh, dth = False, 0, []
    irt, bft, dtt = False, 0, []

    # Sometimes the cld2 html parser gives different results than BeautifulSoup
    # The cld2 html result is slightly preferred due to more in-depth analysis
    if html:
        try:
            irh, bfh, dth = pycld2.detect(html, isPlainText=False, hintTopLevelDomain=domain)
        except pycld2.error:
            pass

    if txt:
        if irh and bfh > len(txt):  # No point in raw text detection
            is_reliable, bytes_found, details = irh, bfh, dth
        else:
            try:
                txt = re.sub(r"\W+", " ", txt)  # To prevent invalid characters
                irt, bft, dtt = pycld2.detect(txt, isPlainText=True, hintTopLevelDomain=domain)
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
        details = [("Unknown", "un", 0, 0)] * 3

    details = {str(i): {"language_name": ln, "language_code": lc, "percent": p, "score": s} for i, (ln, lc, p, s) in
               enumerate(details)}

    resp = {"is_reliable": is_reliable, "text_bytes_found": bytes_found, "details": details}

    return resp


def has_norwegian(is_reliable, details):
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
            # Due to always rounding up we sometimes get 1% where it really is closer to 0%
            p += percent
            s += score * percent
    return p, reliability * s / (p or 1)


def get_ip(connection):
    """
    Finds IP of connection.
    """
    ip = socket.gethostbyname(urlparse(connection.geturl()).hostname)
    return ip


def get_domain(url):
    """
    Gets domain from URL. E.g. "https://stackoverflow.com/" -> "com"
    """
    parsed = urlparse(url)
    base_url = parsed.netloc
    url_parts = base_url.split('.')
    return url_parts[-1]


def norwegian_version(connection, html=None):
    """
    Attempts to find a Norwegian version of a page, first by looking for links that match the Norway regex,
    and afterwards by simply replacing the domain with .no,

    Most of the time this will give an actual Norwegian version of the page, though some false positives may occur.
    However, false positives will still return a valid Norwegian website,
    even though it may not be connected to the input page.
    :return: a dict containing the scheme in which it was discovered,
             the number of matching bytes, and the URL of the page.
    """

    # Internal method that attempts to establish a connection to new URL
    def try_url(new_u):
        try:
            new_connection = urlopen(Request(url=new_u, headers=headers), timeout=30)

            status = new_connection.getcode()
            if (status == HTTPStatus.OK
                    or status == HTTPStatus.MOVED_PERMANENTLY
                    or status == HTTPStatus.FOUND):
                ip_o = get_ip(new_connection)
                ip_n = get_ip(connection)

                i = 0
                for o, n in zip(ip_o.split("."), ip_n.split(".")):
                    if o == n:
                        i += 1
                    else:
                        break
                return i, new_connection.geturl()
        except (HTTPError, CertificateError, URLError, ConnectionResetError, IncompleteRead, socket.timeout,
                socket.gaierror):
            pass
        return None

    url = connection.geturl()
    parsed = urlparse(url)
    base_url = parsed.netloc

    url_parts = base_url.split('.')

    if url_parts[-1] == "no":
        return {"url": url, "scheme": "already_no", "ip_match": 4}  # No point in testing as it's already Norwegian

    if html:  # Goes through all links to check for language changers
        soup = BeautifulSoup(html, "html.parser")
        # Google recommends hreflang for specifying different languages for websites
        # https://support.google.com/webmasters/answer/189077?hl=en

        # Schemes are ordered from strongest to weakest
        it = soup.find_all(["a", "link"], hreflang=pattern_no_html_lang)
        scheme = "href-hreflang"
        if not it:
            it = soup.find_all("a", string=re.compile(f"^\\W*({norway_names}|no)\\W*$", re.IGNORECASE))
            scheme = "href-norway-full"
        if not it:
            it = soup.find_all("a", string=pattern_norway)
            scheme = "href-norway-partial"
        if not it:
            it = soup.find_all(["a", "link"], lang=pattern_no_html_lang)
            scheme = "href-lang"

        for link in it:
            href = link.get("href")
            if href:
                if href.startswith("/"):
                    # Only allow non-country domains, e.g. foo.com -> foo.com/bar but not foo.dk -> foo.dk/bar
                    # This is to prevent things like https://nordnatur.se/2018/08/01/besok-lofoten/
                    # But still allow for example https://www.winterhalter.com/no/
                    if scheme == "href-hreflang" or not re.fullmatch(pattern_cctld, url_parts[-1]):
                        new_url = parsed.scheme + base_url + href
                        scheme = "/" + scheme
                    else:
                        continue
                else:
                    new_url = href

                res = try_url(new_url)
                if res:
                    return {"url": res[1], "scheme": scheme, "ip_match": res[0]}

    if url_parts[-2] in {"com", "co"}:  # E.g. co.uk -> no instead of co.no
        del url_parts[-1]

    url_parts[-1] = "no"

    new_base_url = ".".join(url_parts)

    new_url = urlunparse(
        (parsed.scheme, new_base_url, parsed.path, parsed.params, parsed.query, parsed.fragment))

    res = try_url(new_url)
    if res:
        return {"url": res[1], "scheme": "replace", "ip_match": res[0]}

    return {"url": None, "scheme": "no_match", "ip_match": 0}


def normalize(x, midpoint, lim=1.0):
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
    return lim * (1 - 0.5 ** (x / midpoint))


class WebPage:
    """
    Simple class to handle logic for web pages.
    """

    def __init__(self, orig_url, redirect_url, raw_html, ip, geo_loc=None, content_language=None, no_version=None):
        """
        :param orig_url: the original URL.
        :param redirect_url: the new URL after being redirected.
        :param raw_html: the HTML of the web page.
        :param geo_loc: the geolocation of the site.
        :param ip: the ip of the page.
        :param content_language: the value of the content-language header received.
        :param no_version: Norwegian version of the site if applicable.
        """
        self.orig_url = orig_url
        self.redirect_url = redirect_url
        self.raw_html = raw_html
        self.ip = ip
        # Replace falsy values with strings for embedding projector compatibility
        self.geo_loc = geo_loc or "missing"
        self.content_language = content_language or "missing"
        self.no_version = no_version or "missing"

    @staticmethod
    def from_url(url):
        """
        Creates a WebPage object from a URL
        :param url: URL to create object from.
        :return: a new WebPage object containing the information from the URL.
        """
        req = Request(url=url, headers=headers)
        conn = urlopen(req, timeout=30)
        content_language = conn.info()["content-language"]
        html = str(conn.read(), "utf-8", errors="replace")
        geoloc = geo(conn)
        redir = conn.geturl()
        ip = get_ip(conn)

        no_ver = norwegian_version(conn, html)

        del conn  # Disconnect
        return WebPage(orig_url=url, redirect_url=redir, raw_html=html, geo_loc=geoloc, ip=ip,
                       content_language=content_language, no_version=no_ver)

    @staticmethod
    def is_norwegian(resp):
        """
        Gives a score of how Norwegian a page is, normalized between 0 and 1
        """
        norwegian = resp["language"]["nor_score"] * 2

        reg = resp["regexes"]
        postal = normalize(reg["postal"]["unique"], 1, 2.0)
        phone = normalize(reg["phone"]["unique"], 1, 1.3)
        mail = normalize(reg["email"]["unique"], 1, 1.2)
        county = normalize(reg["county"]["total"], 1, 1.1)
        norway = normalize(reg["norway"]["total"], 1, 1)

        # Give less weight for other countries that
        # - Use kr as currency symbol
        # - Share some common names
        mul = 1
        if pattern_kr_dom.fullmatch(resp["domain"]) \
                or pattern_no_html_lang.fullmatch(resp["geo"]) \
                or pattern_kr_lan.fullmatch(resp["language"]["details"]["0"]["language_code"]):
            mul = 0.1
        kroner = normalize(reg["kroner"]["total"], 1, 0.1 * mul)
        names = normalize(reg["name"]["unique"], 1, 0.5 * mul)

        geo_score = 0.25 if resp["geo"] == "NO" else 0.0

        score = norwegian + postal + phone + county + names + norway + mail + kroner + geo_score
        score = normalize(score, 1.0)

        return score

    def values(self):
        """
        Retrieves relevant information from the page.
        """
        dom = get_domain(self.redirect_url)

        txt = get_text(self.raw_html) or "missing"

        language = detect_language(self.raw_html, txt, dom)
        no_per, no_score = has_norwegian(language["is_reliable"], language["details"])
        nor_score = normalize(language["text_bytes_found"] * no_per * no_score, 1e7)  # 200*100*500 gives 50%
        language["nor_score"] = nor_score

        postal = has_postal(txt)
        phone = has_phone_number(txt)
        county = has_county(txt)
        name = has_name(txt)
        norway = has_norway(txt)
        kroner = has_kroner(txt)
        email = has_email(txt)

        response = {
            "orig_url": self.orig_url,
            "redir_url": self.redirect_url,
            "ip": self.ip,
            "geo": self.geo_loc,
            "domain": dom,
            "content_language": self.content_language,
            "norwegian_version": self.no_version,
            "language": language,
            "regexes": {
                "postal": {
                    "unique": len(postal),
                    "total": sum(postal.values())
                },
                "phone": {
                    "unique": len(phone),
                    "total": sum(phone.values())
                },
                "county": {
                    "unique": len(county),
                    "total": sum(county.values())
                },
                "name": {
                    "unique": len(name),
                    "total": sum(name.values())
                },
                "norway": {
                    "unique": len(norway),
                    "total": sum(norway.values())
                },
                "kroner": {
                    "unique": len(kroner),
                    "total": sum(kroner.values())
                },
                "email": {
                    "unique": len(email),
                    "total": sum(email.values())
                }
            },
        }

        no_score = self.is_norwegian(response)

        response["no_score"] = no_score
        response["text"] = txt

        return response
