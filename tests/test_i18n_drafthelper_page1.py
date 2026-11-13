import unittest

from components import drafthelper
from components import i18n
from components.i18n_en.drafthelper_page1 import PAGE as TABLE
from tests.i18n_check import english, german_leftovers

LIMIT = 660


class DraftHelperPage1Test(unittest.TestCase):
    def test_every_key_occurs_in_page(self):
        for key in TABLE:
            self.assertIn(key, drafthelper.PAGE, key)

    def test_chunk_english_has_no_german(self):
        chunk = "\n".join(drafthelper.PAGE.splitlines()[:LIMIT])
        with english():
            out = i18n.tr_block(chunk, TABLE)
        self.assertEqual(german_leftovers(out, allow=["const im=", "im.", "(im)", "appendChild(im"]), [])

    def test_german_unchanged(self):
        chunk = "\n".join(drafthelper.PAGE.splitlines()[:LIMIT])
        self.assertEqual(i18n.tr_block(chunk, TABLE), chunk)


if __name__ == "__main__":
    unittest.main()
