from urllib.error import URLError

from aiohttp import web
from aiohttp.web_request import Request
from pycld2 import detect

from souper import WebPage

routes = web.RouteTableDef()


@routes.post("/language")
async def handle_ld(request: Request):
    data = await request.post()
    if "text" not in data:
        return web.HTTPUnprocessableEntity(reason="'text' field not present in request.")

    txt = data["text"]
    is_reliable, text_bytes_found, details = detect(txt)

    details = [{"languageName": lm, "languageCode": lc, "percent": p, "score": s} for lm, lc, p, s in details]
    resp = {"isReliable": is_reliable, "textBytesFound": text_bytes_found, "details": details}

    return web.json_response(data=resp)


@routes.post("/url")
async def handle_url_check(request: Request):
    data = await request.post()
    if "url" not in data:
        return web.HTTPUnprocessableEntity(reason="'url' field not present in request.")

    url = data["url"]
    try:
        wp = WebPage.from_url(url)
        resp = wp.values()._asdict()

        return web.json_response(data=resp)
    except ValueError:
        return web.HTTPBadRequest(reason="Malformed url.")
    except URLError:
        return web.HTTPBadRequest(reason="Name or service not known.")

app = web.Application()
app.add_routes(routes)

web.run_app(app)
