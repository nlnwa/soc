import os
import re
from concurrent.futures.process import ProcessPoolExecutor
from concurrent.futures.thread import ThreadPoolExecutor

from dateutil import parser
import pandas as pd
from warcio.archiveiterator import WARCIterator
from warcio.warcwriter import WARCWriter

import souper
from WebPage import WebPage


def record_to_webpage(record):
    uri = record.rec_headers.get_header('WARC-Target-URI')
    if record.rec_type in {"response", "revisit"} \
            and record.content_type == 'application/http; msgtype=response' \
            and record.http_headers.get_statuscode() == "200" \
            and re.fullmatch(r"https?:\/\/[\w.]+no(:\d+)?\/?", uri):
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


def get_info(record):
    uri = record.rec_headers.get_header('WARC-Target-URI')
    html = str(record.raw_stream.read(), "utf-8", errors="replace")
    content_language = record.http_headers.get_header('Content-Language')
    last_modified = record.http_headers.get_header("Last-Modified")
    etag = record.http_headers.get_header("ETag")
    timestamp = parser.parse(record.rec_headers.get_header("WARC-Date")).timestamp()
    return [uri, timestamp, content_language, last_modified, etag, html]


if __name__ == '__main__':
    responses = []
    # path = "/run/media/rolv-arild/Seagate Expansion Drive"
    path = ""

    # all_files = os.listdir(path)

    cols = ["uri", "timestamp", "content_language", "last_modified", "etag", "text", "links"]
    data = {c: [] for c in cols}

    # writer = WARCWriter(open("res/webpages.warc.gz", "wb"))  # Keep all relevant records for faster access


    def process(wp):
        html = wp[-1]
        txt, links = souper.get_text_and_links(html)
        wp[-1] = txt
        wp.append("\t".join(links))
        return wp
        # return wp.extra_info


    def visit(arg):
        i, file = arg
        if file.startswith("."):
            return

        c = 0
        with open(f"{path}{file}", "rb") as stream:
            queue = []
            for record in WARCIterator(stream):
                row = get_info(record)
                queue.append(row)

                # wp = record_to_webpage(record)
                # if wp:
                #     # writer.write_record(record)
                #     # processor.submit(process, wp)
                #     # responses.append(process(wp))
                #     queue.append(wp)
                #     c += 1
            for row in processor.map(process, queue):
                for col, r in zip(cols, row):
                    data[col].append(r)
        # print(f"{i} ({100 * i / len(all_files):.2f}%): {file} ({c} pages added, {len(responses)} total)")


    with ProcessPoolExecutor() as processor:
        # with ThreadPoolExecutor() as ex:
        #     ex.map(visit, enumerate(all_files))

        visit((0, "tracked.warc.gz"))

    df = pd.DataFrame(data, columns=cols)

    # df = pd.json_normalize(responses)
    df.to_csv("tracked2.csv")
