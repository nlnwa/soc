import unittest

from norvegica.WebPage import *


class TestWebPage(unittest.TestCase):

    def test_nb(self):
        val = WebPage.from_url("https://www.nb.no").values()
        self.assertGreater(val["language"]["text_bytes_found"], 0)
        self.assertEqual("no", val["domain"])
        self.assertEqual("NO", val["geo"])
        self.assertEqual("nb-NO", val["html_lang"])
        self.assertGreater(val["language"]["norwegian_score"], 0.5)
        self.assertEqual("href-hreflang-rel", val["norwegian_version"]["scheme"])
        self.assertGreater(val["regex"]["county"]["unique"], 0)
        self.assertGreater(val["norvegica_score"], 0.5)

    def test_dnva(self):
        # Some simple assertions to make sure it's working correctly
        val = WebPage.from_url("http://www.dnva.no").values()
        self.assertGreater(val["language"]["text_bytes_found"], 0)
        self.assertEqual("nb", val["content_language"])
        self.assertEqual("no", val["domain"])

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

    def test_language_detection(self):
        wp = WebPage("https://nb.no", "https://www.nb.no",
                     "<h1>Dette er en norsk tekst for testing av språkdeteksjon</h1>",
                     "151.101.85.140")
        self.assertEqual("no", wp.values()["language"]["details"]["0"]["language_code"])


if __name__ == '__main__':
    unittest.main()
