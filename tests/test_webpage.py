import unittest

from norvegica.WebPage import *


class TestWebPage(unittest.TestCase):

    def test_initial(self):
        # Some simple assertions to make sure it's working correctly
        val = WebPage.from_url("http://www.dnva.no").values()
        self.assertGreater(val["language"]["text_bytes_found"], 0)
        self.assertEqual("nb", val["content_language"])
        self.assertEqual("no", val["domain"])
        self.assertEqual("NL", val["geo"])
        self.assertEqual("nb", val["html_lang"])
        self.assertGreater(val["norvegica_score"], 0.5)
        self.assertEqual("/" + HREF_HREFLANG, val["norwegian_version"]["scheme"])
        for k, v in val["regex"].items():
            self.assertEqual(0, v["total"])

    def test_norwegian_version(self):
        for url, scheme in [
            ("http://www.teknamotor.sk", REPLACE),
            ("https://bodilmunch.blogspot.no/", REPLACE),
            ("https://blog.e-hoi.de", HREF_NORWAY_PARTIAL),
            ("https://shop.nets.eu/", f"/{HREF_NORWAY_FULL}"),
            ("https://herbalifeskin.it/", HREF_NORWAY_FULL),
            ("https://www.viessmann.ae", HREF_NORWAY_FULL),
            ("http://www.mammut.ch", HREF_HREFLANG_REL),
            ("http://www.stenastal.no", f"/{HREF_NORWAY_FULL}"),
            ("https://katalog.uu.se", NO_MATCH),
            ("https://www.nordicnetcare.dk/", REPLACE)
        ]:
            self.assertEqual(scheme, WebPage.from_url(url).values()["norwegian_version"]["scheme"], msg=url)

    def test_detailed(self):
        self.assertEqual(WebPage.from_url("http://www.destinasjonroros.no").values()["regex"]["phone"]["total"], 1)
        self.assertGreater(WebPage.from_url("http://hespe.blogspot.com").values()["language"]["text_bytes_found"], 0)


if __name__ == '__main__':
    unittest.main()
