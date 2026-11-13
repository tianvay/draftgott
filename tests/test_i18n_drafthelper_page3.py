"""Englische Drafthelper-Seite, Teil 3 (JavaScript ab Zeile 1010 von PAGE)."""
import unittest

from components import drafthelper, i18n
from components.i18n_en.drafthelper_page3 import PAGE as TABLE
from tests.i18n_check import english, german_leftovers

START = 1010


class PageThree(unittest.TestCase):
    def test_keys_in_page(self):
        for k in TABLE:
            self.assertIn(k, drafthelper.PAGE, k)

    def test_chunk_english(self):
        lines = drafthelper.PAGE.splitlines()
        chunk = "\n".join(lines[START:])
        with english():
            out = i18n.tr_block(chunk, TABLE)
        # "im" ist hier die JS-Variable des Kartenbilds, kein deutsches Wort
        allow = ["const im=", "im.src", "im.alt", "im.loading", "im.onclick", "appendChild(im)"]
        self.assertEqual(german_leftovers(out, allow=allow), [])
        self.assertNotIn("de-DE", out)

    def test_german_unchanged(self):
        self.assertEqual(i18n.tr_block(drafthelper.PAGE, TABLE), drafthelper.PAGE)


if __name__ == "__main__":
    unittest.main()
