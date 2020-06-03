import unittest

from norvegica.WebPage import *


class TestWebPage(unittest.TestCase):

    def test_initial(self):
        # Some simple assertions to make sure it's working correctly
        val = WebPage.from_url("http://www.dnva.no").values()
        self.assertGreater(val["language"]["text_bytes_found"], 0)
        self.assertEqual(val["content_language"], "nb")
        self.assertEqual(val["domain"], "no")
        self.assertEqual(val["geo"], "NL")
        self.assertEqual(val["html_lang"], "nb")
        self.assertGreater(val["norvegica_score"], 0.5)
        self.assertEqual(val["norwegian_version"]["scheme"], "/" + HREF_HREFLANG)
        for k, v in val["regex"].items():
            self.assertEqual(v["total"], 0)

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
            ("https://www.nordicnetcare.dk/", "/" + HREF_LANG)
        ]:
            self.assertEqual(WebPage.from_url(url).values()["norwegian_version"]["scheme"], scheme, msg=url)

    def test_detailed(self):
        self.assertEqual(WebPage.from_url("http://www.destinasjonroros.no").values()["regex"]["phone"]["total"], 1)
        self.assertGreater(WebPage.from_url("http://hespe.blogspot.com").values()["language"]["text_bytes_found"], 0)


if __name__ == '__main__':
    unittest.main()
