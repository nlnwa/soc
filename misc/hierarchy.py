import json
import re
from collections import Counter
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse, quote
from urllib.request import urlopen, Request

from bs4 import BeautifulSoup

import souper


def extract_outlinks(url):
    try:
        req = Request(url=url, headers=souper.HEADERS)
        conn = urlopen(req, timeout=30)
        html = str(conn.read(), "utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        parsed = urlparse(url)
        base_url = parsed.netloc
        for a in soup.find_all("a", {"href": re.compile(base_url)}):
            href = a.get("href")
            split = urlparse(href)
            yield urlunparse([quote(part) for part in split])
    except (HTTPError, ValueError, URLError):
        print(url)


def get_layers(url, depth):
    urls = {"initial": {"outlinks": [url], "layer": 0, "visited": False}}
    for l in range(1, depth + 1):
        queue = set()
        for url, info in urls.items():
            if info["visited"]:
                continue
            for link in info["outlinks"]:
                queue.add((link, info["layer"] + 1))
            info["visited"] = True
        for link, layer in queue:
            urls.setdefault(link, {"outlinks": list(set(extract_outlinks(link))), "layer": layer, "visited": False})
    del urls["initial"]
    return urls


if __name__ == '__main__':
    lays = get_layers("https://www.vg.no/", 5)
    print(json.dumps(lays, indent=1))
    print(Counter(info["layer"] for url, info in lays.items()).most_common())
