"""Kategorie "Matchwinner" ueber Splashworthy: entscheidet ein Match allein (Bombe). Verhaelt sich wie Splashworthy
(kommt immer rein, auch als Splash), wiegt aber mehr; Bomben in der Deck-Uebersicht sind Matchwinner und
Splashworthy, Must-Play nicht mehr."""
import pathlib
import tempfile
import unittest

from components import cardarchetypes, livedraft, overlay, ratings, report, setreport, suggest
from components.drafthelper import CATEGORIES as DH_CATEGORIES, render_page

MW = "matchwinner"


class CategoryTests(unittest.TestCase):
    def test_known_everywhere_and_first(self):
        self.assertEqual(ratings.CATEGORIES[0], MW)
        self.assertEqual(DH_CATEGORIES[0], MW)
        self.assertIn(MW, overlay.RATING_ABBR)
        self.assertTrue(all(ord(ch) <= 0xFFFF for ch in overlay.RATING_ABBR[MW]))
        self.assertIn("Matchwinner", report.CAT_LABEL[MW])
        self.assertIn("Matchwinner", setreport.CAT_LABEL[MW])
        self.assertIn(MW, setreport.CAT_CLASS)

    def test_saved_and_loaded(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "r.json"
            ratings.set_rating(p, "Bombe", MW)
            self.assertEqual(ratings.load_ratings(p), {"Bombe": MW})

    def test_page_offers_it(self):
        page = render_page()
        self.assertIn('key:"matchwinner"', page)
        self.assertIn("c-matchwinner", page)
        self.assertLess(page.index('key:"matchwinner"'), page.index('key:"splashworthy"'))


class RankTests(unittest.TestCase):
    def test_above_splashworthy(self):
        self.assertGreater(cardarchetypes.POINTS[MW], cardarchetypes.POINTS["splashworthy"])
        self.assertGreaterEqual(cardarchetypes.WEIGHT[MW], cardarchetypes.WEIGHT["splashworthy"])
        self.assertLess(cardarchetypes.RATING_ORDER[MW], cardarchetypes.RATING_ORDER["splashworthy"])
        pack = [{"name": "Sw", "colors": ["W"]}, {"name": "Mw", "colors": ["W"]}]
        ranked = cardarchetypes.rank(pack, {"Sw": "splashworthy", "Mw": MW}, {}, None)
        self.assertEqual(ranked[0]["name"], "Mw")


class DeckBuildingTests(unittest.TestCase):
    CARDS = [{"name": "Mw", "qty": 1, "colors": ["B"], "mv": 4, "land": False},
             {"name": "Bear", "qty": 1, "colors": ["W"], "mv": 2, "land": False}]

    def test_suggest_puts_it_on_splash(self):
        out = suggest.suggest(self.CARDS, [["off"], ["off"]], {}, {"Mw": MW, "Bear": "mustplay"})
        self.assertEqual(out["marks"][0], ["splash"])

    def test_propose_takes_it_off_color(self):
        out = suggest.propose(self.CARDS, [["off"], ["off"]], {"Mw": MW, "Bear": "mustplay"}, "W")
        self.assertEqual(out["deck"].get("Mw"), 1)


class BombTests(unittest.TestCase):
    def test_bombs_are_matchwinner_and_splashworthy(self):
        cards = [{"name": n, "mv": 3, "qty": 1, "colors": ["W"]} for n in ("A", "B", "C", "D")]
        r = {"A": "mustplay", "B": "splashworthy", "C": MW, "D": "filler"}
        self.assertEqual(livedraft.deck_summary(cards, r, "arena")["top"], ["C", "B"])  # Matchwinner zuerst

    def test_help_and_readme(self):
        from components.howitworks import render_help_page
        self.assertIn("Matchwinner", render_help_page())
        readme = (pathlib.Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
        self.assertIn("Matchwinner", readme)


if __name__ == "__main__":
    unittest.main()
