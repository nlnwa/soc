from http import HTTPStatus
from http import HTTPStatus
from http.client import IncompleteRead
from ssl import CertificateError
from urllib.error import HTTPError, URLError
from urllib.parse import urlunparse
from urllib.request import Request, urlopen

from souper import *


class WebPage:
    """
    Simple class to handle logic for web pages.
    """

    def __init__(self, orig_url: str, redirect_url: str, raw_html: str, ip: str, geo_loc: Optional[str] = None,
                 content_language: Optional[str] = None, no_version: Optional[str] = None):
        """
        :param orig_url: the original URL.
        :param redirect_url: the new URL after being redirected.
        :param raw_html: the HTML of the web page.
        :param geo_loc: the geolocation of the site.
        :param ip: the ip of the page.
        :param content_language: the value of the content-language header received.
        :param no_version: Norwegian version of the site if applicable.
        """
        self.original_url = orig_url
        self.redirect_url = redirect_url
        self.raw_html = raw_html
        self.no_version = no_version
        self.ip = ip
        self.geo_loc = geo_loc or ""
        self.content_language = content_language

    @staticmethod
    def from_url(url: str):
        """
        Creates a WebPage object from a URL
        :param url: URL to create object from.
        :return: a new WebPage object containing the information from the URL.
        """
        req = Request(url=url, headers=headers)
        conn = urlopen(req, timeout=30)
        content_language = conn.info()["content-language"]
        html = str(conn.read(), "utf-8", errors="replace")
        redir = conn.geturl()
        ip = get_ip(conn)
        geoloc = geo(ip)

        del conn  # Disconnect
        return WebPage(orig_url=url, redirect_url=redir, raw_html=html, geo_loc=geoloc, ip=ip,
                       content_language=content_language)

    @staticmethod
    def norvegica_score(resp: dict) -> float:
        """
        Gives a score of how Norwegian a page is, normalized between 0 and 1
        """
        norwegian = resp["language"]["norwegian_score"] * 2

        reg = resp["regex"]
        postal = normalize(reg["postal"]["unique"], 1, 2.0)
        phone = normalize(reg["phone"]["unique"], 1, 1.3)
        mail = normalize(reg["email"]["unique"], 1, 1.2)
        county = normalize(reg["county"]["total"], 1, 1.1)
        norway = normalize(reg["norway"]["total"], 2, 1.1)

        # Give less weight for other countries that
        # - Use kr as currency symbol
        # - Share some common names
        mul = 1
        if pattern_kr_dom.fullmatch(resp["domain"]) \
                or pattern_kr_dom.fullmatch(resp["geo"]) \
                or pattern_kr_lan.fullmatch(resp["language"]["details"]["0"]["language_code"]):
            mul = 0.1
        kroner = normalize(reg["kroner"]["total"], 1, 0.1 * mul)
        names = normalize(reg["name"]["unique"], 1, 0.5 * mul)

        geo_score = 0.25 if resp["geo"] == "NO" else 0.0
        cl_score = 0.25 if pattern_no_html_lang.search(resp["content_language"] or "") else 0.0
        hl_score = 0.25 if pattern_no_html_lang.search(resp["html_lang"] or "") else 0.0

        score = norwegian + postal + phone + county + names + norway + mail + kroner + geo_score + cl_score + hl_score
        score = normalize(score, 1.0)

        return score

    def values(self) -> dict:
        """
        Retrieves relevant information from the page.
        """
        dom = get_domain(self.redirect_url)

        txt = get_text(self.raw_html)

        soup = BeautifulSoup(self.raw_html, "html.parser")
        tag = soup.find("html")
        html_lang = tag.get("lang") if tag else None

        language = detect_language(self.raw_html, txt, dom, self.content_language)
        no_per, no_score = norwegian_score(language["is_reliable"], language["details"])
        nor_score = normalize(language["text_bytes_found"] * no_per * no_score, 1e7)  # 200*100*500 gives 50%
        language["norwegian_score"] = nor_score

        postal = has_postal(txt)
        phone = has_phone_number(txt)
        county = has_county(txt)
        name = has_name(txt)
        norway = has_norway(txt)
        kroner = has_kroner(txt)
        email = has_email(txt)

        no_version = self.norwegian_version()

        response = {
            "original_url": self.original_url,
            "redirect_url": self.redirect_url,
            "ip": self.ip,
            "geo": self.geo_loc,
            "domain": dom,
            "html_lang": html_lang,
            "content_language": self.content_language,
            "norwegian_version": no_version,
            "language": language,
            "regex": {
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

        no_score = self.norvegica_score(response)

        response["norvegica_score"] = no_score
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

        schemes_links = {k: [] for k in SCHEMES}

        # Either already_no or replace, not both.
        if url_parts[-1] == "no":
            schemes_links[ALREADY_NO].append(self.redirect_url)
        else:
            new_url_parts = list(url_parts)
            if url_parts[-2] in {"com", "co"}:  # E.g. co.uk -> no instead of co.no
                del new_url_parts[-1]

            new_url_parts[-1] = "no"

            new_base_url = ".".join(new_url_parts)

            new_url = urlunparse(
                (parsed.scheme, new_base_url, parsed.path, parsed.params, parsed.query, parsed.fragment))

            schemes_links[REPLACE].append(new_url)

        soup = BeautifulSoup(self.raw_html, "html.parser")

        for tag in soup.find_all(["a", "link"]):
            schemes_links[place_tag(tag)].append(tag.get("href"))

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
                new_connection = urlopen(Request(url=new_u, headers=headers), timeout=30)

                status = new_connection.getcode()
                if (status == HTTPStatus.OK
                        or status == HTTPStatus.MOVED_PERMANENTLY
                        or status == HTTPStatus.FOUND):
                    ip_o = get_ip(new_connection)
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

        for scheme in SCHEMES:
            # Since ALREADY_NO is uninteresting and quite trivial we ignore it to get something more meaningful
            if scheme != NO_MATCH and scheme != ALREADY_NO:
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
                        res = try_url(new_url)
                        if res:
                            return {"url": res[1], "scheme": sch, "ip_match": res[0]}
                if queue:
                    return {"url": self.redirect_url, "scheme": queue, "ip_match": 4}

        if schemes_links[ALREADY_NO]:
            return {"url": self.redirect_url, "scheme": ALREADY_NO, "ip_match": 4}

        return {"url": None, "scheme": NO_MATCH, "ip_match": 0}
