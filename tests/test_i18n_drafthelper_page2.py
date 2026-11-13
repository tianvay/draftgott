"""Englische Drafthelper-Seite, Teil 2 (PAGE-Zeilen 660..1009): Schluessel kommen vor, keine deutschen Reste."""
import unittest

from components import drafthelper, i18n
from components.i18n_en.drafthelper_page2 import PAGE as TABLE
from tests.i18n_check import english, german_leftovers

LO, HI = 660, 1010


class DrafthelperPage2Test(unittest.TestCase):
    def chunk(self):
        return "\n".join(drafthelper.PAGE.splitlines()[LO:HI])

    def test_keys_in_page(self):
        for k in TABLE:
            self.assertIn(k, drafthelper.PAGE, k)

    def test_chunk_english(self):
        chunk = self.chunk()
        with english():
            out = i18n.tr_block(chunk, TABLE)
        self.assertEqual(german_leftovers(out), [])
        self.assertNotEqual(out, chunk)

    def test_german_unchanged(self):
        chunk = self.chunk()
        self.assertEqual(i18n.tr_block(chunk, TABLE), chunk)


if __name__ == "__main__":
    unittest.main()
