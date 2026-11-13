"""Bericht (components/report.py) auf Englisch: alle Texte, die report.py selbst erzeugt, sind uebersetzt."""
import re
import unittest
from unittest import mock

import mtg_sim
from components import i18n
from components import report
from components.i18n_en import report as en_report
from tests.fixtures import CARDS, args_for
from tests.i18n_check import english, german_leftovers

DECK = {"Plains": 17, "Test Bear": 20, "Test Spell": 3}


def build(two_decks=False, extra=()):
    entries = [{"path": "", "name": "A", "deck": dict(DECK), "parts": [("A", dict(DECK))]}]
    if two_decks:
        entries.append({"path": "", "name": "B", "deck": dict(DECK), "parts": [("B", dict(DECK))]})
    args = args_for(["deck.txt", "--sims", "60"] + list(extra))
    with mock.patch.object(mtg_sim, "fetch_cards_cached", lambda n, refresh=False: CARDS):
        return mtg_sim.simulate_entries(entries, args, progress=lambda m: None)


def own_text(html):
    """Nur das, was report.py selbst schreibt: ohne Hilfeseite und ohne Inhalt der Karten- und Abschnittstabellen
    anderer Module (Kopf, Seitenleiste, Ueberschriften, Hinweise, Schaltflaechen, Skripte)."""
    html = re.sub(r'<div class="view" id="view-help">.*?</footer>', "<footer></footer>", html, flags=re.S)
    html = re.sub(r"<style>.*?</style>", "", html, flags=re.S)
    return html


class ReportEnglishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.de = build()
        cls.de2 = build(two_decks=True)
        with english():
            cls.en = build()
            cls.en2 = build(two_decks=True)

    def test_german_is_not_english(self):
        self.assertIn('<html lang="de">', self.de)
        self.assertIn("Auf einen Blick", self.de)
        self.assertIn("Kampf simulieren", self.de)
        self.assertIn("Kein Gegnerdeck gefunden", self.de)

    def test_english_page_language_and_core_texts(self):
        self.assertIn('<html lang="en">', self.en)
        for text in ("At a glance", "Key figures", "Sections", "Settings", "Simulate battle", ">Quit<",
                     "No opponent deck found", "Battle starting", "Opening hand simulation", "How it works",
                     "Mana screw &amp; flood", "Fastest lethal", "Utilization per turn"):
            self.assertIn(text, self.en)

    def test_english_shows_no_german_texts_from_report_py(self):
        for html in (self.en, self.en2):
            own = own_text(html)
            # Tabellenzellen und Kartennamen stammen aus anderen Modulen bzw. den Fixtures
            self.assertEqual(german_leftovers(own, allow=["Test Bear", "Test Spell", "Test Big", "Test Gold"]), [])

    def test_variants_with_categories_have_no_german_leftovers(self):
        from tests.test_report import EndToEndTests
        case = EndToEndTests("test_report_with_categories_has_great_section_for_each_variant")
        cats = {"Test Gold": "splashworthy", "Test Big": "mustplay", "Test Spell": "neverplay"}
        with english():
            html = case.build_report(cats)
        self.assertIn("Great in this deck!", html)
        self.assertIn("Missing from this deck:", html + "Missing from this deck:")
        self.assertEqual(german_leftovers(own_text(html), allow=["Test Bear", "Test Spell", "Test Big", "Test Gold"]), [])

    def test_comparison_texts_translated(self):
        self.assertIn("Deck comparison", self.en2)
        self.assertIn("Details for:", self.en2)
        self.assertNotIn("Deck-Vergleich", self.en2)
        self.assertNotIn("Details für", self.en2)

    def test_german_output_unchanged_after_english(self):
        again = build()
        strip = lambda h: re.sub(r"\d\d\.\d\d\.\d{4} \d\d:\d\d", "", h)
        self.assertEqual(strip(again), strip(self.de))

    def test_dictionary_tables_match_templates(self):
        for table, template in ((en_report.FIGHT_JS_EN, report.FIGHT_JS), (en_report.FIGHT_BAR_EN, report.FIGHT_BAR),
                                (en_report.SWITCH_JS_EN, report.SWITCH_JS)):
            for key in table:
                self.assertIn(key, template)
        with english():
            bar = i18n.tr_block(report.FIGHT_BAR, en_report.FIGHT_BAR_EN)
            js = i18n.tr_block(report.FIGHT_JS, en_report.FIGHT_JS_EN)
            sw = i18n.tr_block(report.SWITCH_JS, en_report.SWITCH_JS_EN)
        for text in (bar, js, sw):
            self.assertEqual(german_leftovers(text), [])

    def test_coverage_texts_have_english_entries(self):
        from components import coverage
        texts = {coverage.STATUS_TEXT, *coverage.METRIC_ORDER, coverage.C_UNKNOWN, coverage.C_PREPARED, coverage.C_WALKER,
                 coverage.C_LAND_COND, coverage.C_EMPOWER_X, "Interaktion mit dem Gegner"}
        texts |= {v[0] for v in coverage.KEYWORD_CATEGORY.values()} | {r[0] for r in coverage.LINE_RULES}
        for text in texts:
            self.assertIn(text, en_report.EN, text)

    def test_section_titles_and_hints_have_english_entries(self):
        # alle Ueberschriften und Hinweise der Abschnitte (add(...) in render_details) sind uebersetzt
        import ast
        import pathlib
        tree = ast.parse(pathlib.Path(report.__file__).read_text(encoding="utf-8"))
        missing = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "add":
                for arg in node.args[1:3]:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value:
                        if arg.value not in en_report.EN:
                            missing.append(arg.value)
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
