import unittest

from components import i18n
from components.howitworks import CONDITIONAL, render_help_page, render_help_view
from components.i18n_en.howitworks import EN
from tests.i18n_check import english, german_leftovers

# Namen und Begriffe, die auch in der englischen Ausgabe stehen (Kartennamen, Kommandozeilenoptionen, Dateinamen)
ALLOW = [
    "--min-handkarten", "--ohne-mulligan", "--ohne-jace", "--ohne-landcycling", "--auras-ohne-kreatur",
    "--landcycling-runden", "--landcycling-max-laender", "--landcycling-letzte-karte", "--max-runden",
    "--curve-runden", "--kein-overlay", "--statistik-neu", "--statistik", "--archetypen", "--setauswertung",
    "--schaden", "--drafthelper", "kartenarchetypen.json", "draftstatistik.json", "draftstatistik.backup.json",
    "setauswertung_&lt;set&gt;.html", "Player-prev.log", "scryfall_set_cache.json", "scryfall_symbols.json",
    "Deck + Sideboard", "Hall of Game",
]


class TestHowItWorksEnglish(unittest.TestCase):
    def test_german_unchanged_and_english_differs(self):
        de1 = render_help_page()
        with english():
            en = render_help_page()
        self.assertEqual(de1, render_help_page())
        self.assertNotEqual(de1, en)
        self.assertIn('lang="de"', de1)
        self.assertIn('lang="en"', en)
        self.assertIn("So funktioniert es", de1)

    def test_page_has_no_german_leftovers(self):
        with english():
            en = render_help_page()
        self.assertEqual(german_leftovers(en, allow=ALLOW), [])

    def test_view_without_conditional_sections(self):
        with english():
            en = render_help_view(present=set())
        self.assertEqual(german_leftovers(en, allow=ALLOW), [])
        self.assertIn("How it works", en)
        for sid in CONDITIONAL:
            self.assertNotIn(f'id="hiw-{sid}"', en)

    def test_decimal_point_in_english(self):
        with english():
            self.assertEqual(i18n.dec("2.5"), "2.5")
            en = render_help_view()
        self.assertIn("1.0 ·", en)
        self.assertNotIn("0,9 ·", en)

    def test_dictionary_values_filled(self):
        for k, v in EN.items():
            self.assertTrue(v.strip(), k)
            self.assertNotEqual(k, v) if len(k) > 40 else None


if __name__ == "__main__":
    unittest.main()
