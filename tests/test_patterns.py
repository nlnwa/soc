import unittest

from norvegica.patterns import *


class TestPatterns(unittest.TestCase):

    def test_names(self):
        self.assertTrue(pattern_names.fullmatch("Jan Hansen"))

    def test_postal(self):
        self.assertTrue(pattern_postal.fullmatch("8624 Mo i Rana"))

    def test_phone(self):
        self.assertTrue(pattern_phone.fullmatch("+47 23 27 60 00"), )

    def test_norway(self):
        self.assertTrue(pattern_norway.fullmatch("Norge"))

    def test_county(self):
        self.assertTrue(pattern_counties.fullmatch("Nordland"))

    def test_kroner(self):
        self.assertTrue(pattern_kroner.fullmatch("420 kr"))

    def test_email(self):
        self.assertTrue(pattern_email.fullmatch("nb@nb.no"))


if __name__ == '__main__':
    unittest.main()
