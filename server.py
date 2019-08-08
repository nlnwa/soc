from urllib.error import URLError

from aiohttp import web
from aiohttp.web_request import Request

from souper import WebPage, detect_language, get_text, get_domain

routes = web.RouteTableDef()


@routes.post("/language")
async def handle_language_detection(request: Request):
    data = await request.post()

    if "url" in data:
        try:
            wp = WebPage.from_url(data["url"])
            domain = get_domain(wp.redirect_url)
            http_lang = wp.content_language
            html = wp.raw_html
            text = get_text(wp.raw_html)
        except ValueError:
            return web.HTTPBadRequest(reason="Malformed url.")
        except URLError:
            return web.HTTPBadRequest(reason="Name or service not known.")
    else:
        domain = data["domain"] if "domain" in data else None
        http_lang = data["http_lang"] if "http_lang" in data else None
        html = data["html"] if "html" in data else None
        text = data["text"] if "text" in data else None

    if not html and not text:
        return web.HTTPUnprocessableEntity(reason="Unable to make prediction, missing 'url', 'text' or 'html'")

    resp = detect_language(html=html, txt=text, domain=domain, http_lang=http_lang)

    return web.json_response(data=resp)


@routes.post("/url")
async def handle_url_check(request: Request):
    data = await request.post()
    print(data)
    if "url" not in data:
        return web.HTTPUnprocessableEntity(reason="'url' field not present in request.")

    url = data["url"]
    try:
        wp = WebPage.from_url(url)
        resp = wp.values()

        return web.json_response(data=resp)
    except ValueError:
        return web.HTTPBadRequest(reason="Malformed url.")
    except URLError:
        return web.HTTPBadRequest(reason="Name or service not known.")

app = web.Application()
app.add_routes(routes)

web.run_app(app)
