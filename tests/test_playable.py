"""Kategorie "Playable" zwischen MustPlay und Filler (Nutzer 14.11.2026): solide Karte, die gespielt wird, wenn wir
die Farbe spielen, aber nicht zwingend. Zaehlt weniger als MustPlay und mehr als Filler, fuellt im Deckvorschlag vor
den Fillern auf und zaehlt nicht als starke Karte (Top-Pick, Signale)."""
import pathlib
import tempfile
import unittest

from components import cardarchetypes, overlay, packoverlay, ratings, report, setreport, signals, suggest
from components.drafthelper import CATEGORIES as DH_CATEGORIES, render_page

PL = "playable"


class CategoryTests(unittest.TestCase):
    def test_between_mustplay_and_filler(self):
        for cats in (ratings.CATEGORIES, DH_CATEGORIES):
            self.assertEqual(cats.index(PL), cats.index("mustplay") + 1)
            self.assertEqual(cats.index("filler"), cats.index(PL) + 1)

    def test_labels_everywhere(self):
        self.assertIn(PL, overlay.RATING_ABBR)
        self.assertIn(PL, packoverlay.RATING_LABEL)
        self.assertIn("Playable", report.CAT_LABEL[PL])
        self.assertIn("Playable", setreport.CAT_LABEL[PL])
        self.assertIn(PL, setreport.CAT_CLASS)
        self.assertEqual(len(set(setreport.CAT_CLASS.values())), len(setreport.CAT_CLASS))

    def test_saved_and_loaded(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "r.json"
            ratings.set_rating(p, "Bear", PL)
            self.assertEqual(ratings.load_ratings(p), {"Bear": PL})

    def test_page_offers_it(self):
        page = render_page()
        self.assertIn('key:"playable"', page)
        self.assertIn("c-playable", page)
        self.assertLess(page.index('key:"mustplay"'), page.index('key:"playable"'))
        self.assertLess(page.index('key:"playable"'), page.index('key:"filler"'))

    def test_english_page(self):
        from components import i18n
        old = i18n.get_lang() if hasattr(i18n, "get_lang") else None
        try:
            i18n.set_lang("en")
            page = render_page()
        finally:
            i18n.set_lang(old or "de")
        self.assertIn('key:"playable"', page)
        self.assertNotIn("nicht zwingend", page)


class RankTests(unittest.TestCase):
    def test_values_between(self):
        for table in (cardarchetypes.POINTS, cardarchetypes.WEIGHT):
            self.assertLess(table[PL], table["mustplay"])
            self.assertGreater(table[PL], table["filler"])
        self.assertGreater(cardarchetypes.POINTS[PL], 1.5)  # ueber unbewertet
        order = cardarchetypes.RATING_ORDER
        self.assertTrue(order["mustplay"] < order[PL] < order[""] < order["filler"])

    def test_pack_order(self):
        pack = [{"name": n, "colors": ["W"]} for n in ("Fi", "Pl", "Mp", "None")]
        ranked = cardarchetypes.rank(pack, {"Fi": "filler", "Pl": PL, "Mp": "mustplay"}, {}, None)
        self.assertEqual([c["name"] for c in ranked], ["Mp", "Pl", "None", "Fi"])

    def test_not_strong(self):
        self.assertNotIn(PL, cardarchetypes.HINT_RATINGS)
        self.assertNotIn(PL, signals.STRONG)


class DeckBuildingTests(unittest.TestCase):
    # Filler hat den kleineren Manawert und kaeme sonst zuerst
    CARDS = [{"name": "Fi", "qty": 1, "colors": ["W"], "mv": 1, "land": False},
             {"name": "Pl", "qty": 1, "colors": ["W"], "mv": 5, "land": False},
             {"name": "PlOff", "qty": 1, "colors": ["B"], "mv": 2, "land": False}]
    CATS = {"Fi": "filler", "Pl": PL, "PlOff": PL}

    def test_suggest_fills_playable_first(self):
        out = suggest.suggest(self.CARDS[:2], [["off"], ["off"]], {}, self.CATS, target=1)
        self.assertEqual(out["marks"], [["off"], ["core"]])

    def test_propose_playable_first_and_only_in_colors(self):
        cats = dict(self.CATS, Mp="mustplay")
        for mp, fi_in in ((21, True), (22, False)):  # 40 Karten = 17 Laender + MustPlay + 2 bzw. 1 freie Plaetze
            cards = self.CARDS + [{"name": "Mp", "qty": mp, "colors": ["W"], "mv": 3, "land": False}]
            out = suggest.propose(cards, [["off"]] * 3 + [["off"] * mp], cats, "W")
            self.assertEqual(out["deck"].get("Pl"), 1)
            self.assertEqual("Fi" in out["deck"], fi_in)
            self.assertNotIn("PlOff", out["deck"])


class DocsTests(unittest.TestCase):
    def test_help_and_readme(self):
        from components.howitworks import render_help_page
        self.assertIn("Playable", render_help_page())
        readme = (pathlib.Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
        self.assertIn("Playable", readme)


if __name__ == "__main__":
    unittest.main()
