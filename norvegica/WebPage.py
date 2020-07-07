import difflib
import re
import socket
import time
from collections import OrderedDict
from datetime import datetime
from functools import cached_property
from http import HTTPStatus
from http import HTTPStatus
from http.client import IncompleteRead
from ssl import CertificateError
from typing import Tuple, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlunparse, urlencode, urlparse
from urllib.request import Request, urlopen

import bs4
from dateutil import parser
from dateutil.parser import ParserError
from dateutil.tz import UTC

import souper


class WebPage:
    """
    Simple class to handle logic for web pages.
    """

    def __init__(self, orig_url: str, redirect_url: str, raw_html: str, ip: str, timestamp: Optional[int] = None,
                 geo_loc: Optional[str] = None, content_language: Optional[str] = None,
                 last_modified: Optional[int] = None, etag: Optional[str] = None, no_version: Optional[str] = None):
        """
        :param orig_url: the original URL.
        :param redirect_url: the new URL after being redirected.
        :param raw_html: the HTML of the web page.
        :param geo_loc: the geolocation of the site.
        :param ip: the ip of the page.
        :param content_language: the value of the content-language header received.
        :param no_version: Norwegian version of the site if applicable.
        :param timestamp: When the site was harvested. Preferably UTC time for consistency.
        """
        self.original_url = orig_url
        self.redirect_url = redirect_url
        self.raw_html = raw_html
        self.no_version = no_version
        self.ip = ip
        self.timestamp = timestamp
        self.geo_loc = geo_loc or (souper.geo(ip) if ip else "")
        self.content_language = content_language
        self.last_modified = last_modified
        self.etag = etag

    @staticmethod
    def from_url(url: str):
        """
        Creates a WebPage object from a URL
        :param url: URL to create object from.
        :return: a new WebPage object containing the information from the URL.
        """
        req = Request(url=url, headers=souper.HEADERS)
        conn = urlopen(req, timeout=30)
        stamp = int(datetime.utcnow().timestamp())
        http_headers = conn.info()
        content_language = http_headers["content-language"]
        etag = http_headers["etag"]
        last_modified = http_headers["last-modified"]
        if last_modified:
            try:
                last_modified = int(parser.parse(last_modified).astimezone(UTC).timestamp())
            except ParserError:
                last_modified = None
        html = str(conn.read(), "utf-8", errors="replace")
        redir = conn.geturl()
        ip = souper.get_ip(conn)

        del conn  # Disconnect
        return WebPage(orig_url=url, redirect_url=redir, raw_html=html, geo_loc=None, ip=ip, timestamp=stamp,
                       content_language=content_language, last_modified=last_modified, etag=etag)

    @staticmethod
    def norvegica_score(resp: dict) -> float:
        """
        Gives a score of how Norwegian a page is, normalized between 0 and 1
        """
        norwegian = resp["language"]["norwegian_score"] * 2

        reg = resp["regex"]
        postal = souper.normalize(reg["postal"]["unique"], 1, 2.0)
        phone = souper.normalize(reg["phone"]["unique"], 1, 1.3)
        mail = souper.normalize(reg["email"]["unique"], 1, 1.2)
        county = souper.normalize(reg["county"]["total"], 1, 1.1)
        norway = souper.normalize(reg["norway"]["total"], 2, 1.1)

        # Give less weight for other countries that
        # - Use kr as currency symbol
        # - Share some common names
        mul = 1
        if souper.pattern_kr_dom.fullmatch(resp["domain"]) \
                or souper.pattern_kr_dom.fullmatch(resp["geo"]) \
                or souper.pattern_kr_lan.fullmatch(resp["language"]["details"]["0"]["language_code"]):
            mul = 0.1
        kroner = souper.normalize(reg["kroner"]["total"], 1, 0.1 * mul)
        names = souper.normalize(reg["name"]["unique"], 1, 0.5 * mul)

        geo_score = 0.25 if resp["geo"] == "NO" else 0.0
        cl_score = 0.25 if souper.pattern_no_html_lang.search(resp["content_language"] or "") else 0.0
        hl_score = 0.25 if souper.pattern_no_html_lang.search(resp["html_lang"] or "") else 0.0

        score = norwegian + postal + phone + county + names + norway + mail + kroner + geo_score + cl_score + hl_score
        score = souper.normalize(score, 1.0)

        return score

    @cached_property
    def text(self):
        return souper.get_text(self.raw_html)

    @cached_property
    def extra_info(self) -> dict:
        """
        Retrieves relevant information from the page.
        """
        dom = souper.get_domain(self.redirect_url)

        txt = self.text

        soup = bs4.BeautifulSoup(self.raw_html, "html.parser")
        links = [link.get("href") for link in soup.find_all("a", attrs={"href": True})]
        tag = soup.find("html")
        html_lang = tag.get("lang") if tag else None

        language = souper.detect_language(self.raw_html, txt, dom, self.content_language)
        no_per, no_score = souper.norwegian_score(language["is_reliable"], language["details"])
        nor_score = souper.normalize(language["text_bytes_found"] * no_per * no_score, 1e7)  # 200*100*500 gives 50%
        language["norwegian_score"] = nor_score

        postal = souper.has_postal(txt)
        phone = souper.has_phone_number(txt)
        county = souper.has_county(txt)
        name = souper.has_name(txt)
        norway = souper.has_norway(txt)
        kroner = souper.has_kroner(txt)
        email = souper.has_email(txt)

        no_version = self.norwegian_version()

        response = OrderedDict(
            original_url=self.original_url,
            redirect_url=self.redirect_url,
            timestamp=self.timestamp,
            ip=self.ip,
            geo=self.geo_loc,
            domain=dom,
            content_language=self.content_language,
            last_modified=self.last_modified,
            etag=self.etag,
            html_lang=html_lang,
            language=language,
            norwegian_version=no_version,
        )

        response["regex"] = {
            name: {
                "unique": len(counter),
                "total": sum(counter.values())
            }
            for name, counter in
            [("postal", postal), ("phone", phone), ("county", county), ("name", name), ("norway", norway),
             ("kroner", kroner), ("email", email)]
        }

        no_score = self.norvegica_score(response)

        response["norvegica_score"] = no_score
        response["links"] = "\t".join(links)
        response["text"] = txt

        return response

    def find_norwegian_links(self) -> dict:
        """
        Finds possible candidates for a Norwegian version of the page.
        :return: a dict with a list of urls for each scheme
        """
        parsed = urlparse(self.redirect_url)
        base_url = parsed.netloc

        url_parts = base_url.split('.')

        schemes_links = {k: [] for k in souper.SCHEMES}

        # Either already_no or replace, not both.
        if url_parts[-1] == "no":
            schemes_links[souper.ALREADY_NO].append(self.redirect_url)
        else:
            new_url_parts = list(url_parts)
            if url_parts[-2] in {"com", "co"}:  # E.g. co.uk -> no instead of co.no
                del new_url_parts[-1]

            new_url_parts[-1] = "no"

            new_base_url = ".".join(new_url_parts)

            new_url = urlunparse(
                (parsed.scheme, new_base_url, parsed.path, parsed.params, parsed.query, parsed.fragment))

            schemes_links[souper.REPLACE].append(new_url)

        soup = bs4.BeautifulSoup(self.raw_html, "html.parser")

        for tag in soup.find_all(["a", "link"]):
            schemes_links[souper.place_tag(tag)].append(tag.get("href"))

        return schemes_links

    def norwegian_version(self, norwegian_links: Optional[dict] = None) -> dict:
        """
        Goes through candidates for Norwegian versions, and selects the best one that actually exists.

        :return: a dict containing the scheme in which it was discovered,
                 the number of matching bytes, and the URL of the page.
        """

        # Internal method that attempts to establish a connection to new URL
        def try_url(new_u):
            try:
                new_connection = urlopen(Request(url=new_u, headers=souper.HEADERS), timeout=30)

                status = new_connection.getcode()
                if (status == HTTPStatus.OK
                        or status == HTTPStatus.MOVED_PERMANENTLY
                        or status == HTTPStatus.FOUND):
                    ip_o = souper.get_ip(new_connection)
                    ip_n = self.ip

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

        schemes_links = norwegian_links or self.find_norwegian_links()

        for scheme in souper.SCHEMES:
            # Since ALREADY_NO is uninteresting and quite trivial we ignore it to get something more meaningful
            if scheme != souper.NO_MATCH and scheme != souper.ALREADY_NO:
                # Reverse sorting puts links starting with "/" at the end
                links = sorted(schemes_links[scheme], reverse=True)
                queue = None  # Queue is for matches where the url is the same as the original result
                for link in links:
                    if link.startswith("/"):
                        parsed = urlparse(self.redirect_url)
                        new_url = urlunparse((parsed.scheme, parsed.netloc, link, None, None, None))
                        sch = "/" + scheme
                    else:
                        sch = scheme
                        new_url = link

                    if new_url == self.original_url or new_url == self.redirect_url:
                        queue = sch
                    else:
                        # res = try_url(new_url)
                        res = new_url, -1
                        if res:
                            return {"url": res[1], "scheme": sch, "ip_match": res[0]}
                if queue:
                    return {"url": self.redirect_url, "scheme": queue, "ip_match": 4}

        if schemes_links[souper.ALREADY_NO]:
            return {"url": self.redirect_url, "scheme": souper.ALREADY_NO, "ip_match": 4}

        return {"url": None, "scheme": souper.NO_MATCH, "ip_match": 0}

    def diff(self, other: "WebPage") -> Tuple[set, set, set, set]:
        t1, t2 = self.text.split("\t"), other.text.split("\t")
        chars = " +-?"
        sets = set(), set(), set(), set()  # same, added, removed, neither
        for comp in difflib.Differ().compare(t1, t2):
            line = comp[2:]
            first = comp[0]
            for c, s in zip(chars, sets):
                if first == c:
                    s.add(line)
        return sets
