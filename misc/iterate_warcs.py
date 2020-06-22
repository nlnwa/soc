import os
import re
from concurrent.futures.process import ProcessPoolExecutor
from concurrent.futures.thread import ThreadPoolExecutor

from dateutil import parser
import pandas as pd
from warcio.archiveiterator import WARCIterator
from warcio.warcwriter import WARCWriter

from WebPage import WebPage


def record_to_webpage(record):
    uri = record.rec_headers.get_header('WARC-Target-URI')
    if record.rec_type in {"response", "revisit"} \
            and record.content_type == 'application/http; msgtype=response' \
            and record.http_headers.get_statuscode() == "200" \
            and re.fullmatch(r"https?:\/\/[\w.]+no(:\d+)?\/?", uri):
        encoding = []  # re.findall("charset=([^;]+)", record.http_headers.get_header("Content-Type"))
        encoding.append("utf-8")
        html = str(record.raw_stream.read(), "utf-8", errors="replace")
        ip = record.rec_headers.get_header('WARC-IP-Address')
        content_language = record.http_headers.get_header('Content-Language')
        last_modified = record.http_headers.get_header("Last-Modified")
        etag = record.http_headers.get_header("ETag")
        timestamp = parser.parse(record.rec_headers.get_header("WARC-Date")).timestamp()
        webpage = WebPage(orig_url=uri, redirect_url=uri, raw_html=html, ip=ip, timestamp=int(timestamp), geo_loc=None,
                          content_language=content_language, last_modified=last_modified, etag=etag)
        return webpage
    return None


if __name__ == '__main__':
    responses = []
    path = "/run/media/rolv-arild/Seagate Expansion Drive"
    # path = "res"
    all_files = os.listdir(path)

    writer = WARCWriter(open("res/webpages.warc.gz", "wb"))  # Keep all relevant records for faster access

    def visit(arg):
        i, file = arg
        if file.startswith("."):
            return
        c = 0

        with open(f"{path}/{file}", "rb") as stream:
            for record in WARCIterator(stream):
                wp = record_to_webpage(record)
                if wp:
                    writer.write_record(record)
                    responses.append(wp.extra_info)
                    c += 1
        print(f"{i} ({100 * i / len(all_files):.2f}%): {file} ({c} pages added)")

    with ProcessPoolExecutor() as ex:
        ex.map(visit, enumerate(all_files))

    # visit((0, "webpages.warc.gz"))

    df = pd.json_normalize(responses)
    df.to_csv("warc_pages.csv")
