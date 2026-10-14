import json
import pathlib
import re
import shutil
import subprocess
import tempfile
import threading
import unittest
import urllib.request
from unittest import mock

import mtg_sim
from components import drafthelper as dh
from components.howitworks import render_help_page
from components.report_sections import JACE_RULES
from tests.fixtures import args_for
from tests.fixtures_walkers import DATA

DECK = {"Plains": 17, "Test Bear": 12, "Test Big": 4, "Test Empower": 4, "Test Empower Creature": 3}


def build(two_decks=False):
    entries = [{"path": "", "name": "A", "deck": dict(DECK), "parts": [("A", dict(DECK))]}]
    if two_decks:
        entries.append({"path": "", "name": "B", "deck": dict(DECK), "parts": [("B", dict(DECK))]})
    with mock.patch.object(mtg_sim, "fetch_cards_cached", lambda n, refresh=False: DATA):
        return mtg_sim.simulate_entries(entries, args_for(["deck.txt", "--sims", "100"]), progress=lambda m: None)


def split(html):
    i = html.index('id="view-help"')
    return html[:i], html[i:]


MOVED = [
    "Die Regeln gelten der Reihe nach",                 # Spiellogik
    "Bei einem Mulligan wird das Deck neu gemischt",    # Mulligan
    JACE_RULES[0][:45],                                 # Jace
    "Quelle = Land auf dem Feld",                       # Farbverfuegbarkeit
    "Ampel Zauber pro Runde",                           # Auf einen Blick
    "Ausgegebenes geteilt durch verfügbares Mana",      # Curve-Auslastung
    "Gezählt werden Kopien. Artefakte",                 # Kartentypen
    "Karten = Nichtland-Karten, die die Farbe brauchen",  # Farbverteilung
    "Anteil der Spiele, in denen in dieser Runde mindestens ein Zauber",  # Zauber pro Runde
    "Die Erkennung arbeitet über den Kartentext",       # Modell-Abdeckung
    "Ø und Median nur über Spiele",                     # Schaden / Tempo
    "Jede Nichtland-Karte wird gespielt, sobald sie bezahlbar ist",  # Modellannahmen
]


class OneFileTwoViewsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = build()
        cls.report, cls.help = split(cls.html)
        cls.html2 = build(two_decks=True)
        cls.report2, cls.help2 = split(cls.html2)

    def test_both_views_are_in_one_file(self):
        self.assertIn('id="view-report"', self.report)
        self.assertIn('id="view-help"', self.html)

    def test_header_switches_between_the_views(self):
        self.assertIn(">Bericht<", self.report)
        self.assertIn(">So funktioniert es<", self.report)

    def test_explanations_moved_out_of_the_report(self):
        for text in MOVED[:3] + MOVED[4:]:
            self.assertNotIn(text, self.report, text)
            self.assertIn(text, self.help, text)

    def test_comparison_statistics_are_explained_on_the_help_view(self):
        self.assertNotIn("95-%-Konfidenzintervall", self.report2)
        self.assertIn("95-%-Konfidenzintervall", self.help2)

    def test_color_availability_rule_moved(self):
        self.assertIn(MOVED[3], self.help)
        self.assertNotIn(MOVED[3], self.report)

    def test_deck_specific_notes_stay_in_the_report(self):
        self.assertIn("Nichtland-Karten, davon", self.report)
        self.assertIn("Jede Karte steht genau einmal", self.report)   # Bildunterschrift der Farbkurve
        self.assertIn("Top Card:", self.report)

    def test_rule_sections_only_on_the_help_view(self):
        for sid in ("logik", "annahmen"):
            self.assertNotIn(f'<section id="{sid}"', self.report)
            self.assertIn(f'<section id="hiw-{sid}"', self.help)

    def test_every_report_section_links_to_its_explanation(self):
        ids = re.findall(r'<section id="([^"]+)"', self.report2)
        self.assertTrue(ids)
        help_ids = set(re.findall(r'<section id="(hiw-[^"]+)"', self.help2))
        for sid in ids:
            base = re.sub(r"-\d+$", "", sid)
            self.assertIn(f'href="#hiw-{base}"', self.report2, sid)
            self.assertIn(f"hiw-{base}", help_ids, sid)

    def test_explanations_appear_only_once_even_with_two_decks(self):
        self.assertEqual(self.html2.count(JACE_RULES[0][:45]), 1)
        self.assertEqual(self.html2.count("Die Regeln gelten der Reihe nach"), 1)

    def test_help_view_has_its_own_navigation_and_a_way_back(self):
        nav = re.search(r"<nav[^>]*>(.*?)</nav>", self.help, re.S).group(1)
        self.assertIn('href="#hiw-drafthelper"', nav)
        self.assertIn("Zurück zum Bericht", self.help)

    def test_parameters_are_described_generally(self):
        self.assertIn("--flood", self.help)
        self.assertIn("Standard 11", self.help)

    def test_drafthelper_section(self):
        part = self.help[self.help.index('id="hiw-drafthelper"'):]
        for text in ("Splashworthy", "MustPlay", "Filler", "NeverPlay", "Deckvorschlag", "15 bis 17",
                     "Zuordnung nach Kategorien"):
            self.assertIn(text, part, text)

    @unittest.skipUnless(shutil.which("node"), "Node.js nicht installiert")
    def test_report_scripts_are_valid_javascript(self):
        scripts = re.findall(r"<script>(.*?)</script>", self.html2, re.S)
        self.assertTrue(scripts)
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "r.js"
            path.write_text("\n".join(scripts), encoding="utf-8")
            out = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)


class StandaloneHelpPageTests(unittest.TestCase):
    def test_standalone_page_contains_only_the_explanations(self):
        page = render_help_page()
        self.assertTrue(page.startswith("<!DOCTYPE html>"))
        self.assertIn('id="hiw-drafthelper"', page)
        self.assertIn("So funktioniert es", page)
        self.assertNotIn('id="view-report"', page)

    def test_drafthelper_serves_the_help_page(self):
        server = dh.LocalServer(("127.0.0.1", 0), dh.make_handler({}))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            url = f"http://127.0.0.1:{server.server_address[1]}/howitworks.html"
            with urllib.request.urlopen(url, timeout=10) as r:
                body = r.read().decode("utf-8")
            self.assertIn('id="hiw-drafthelper"', body)
        finally:
            server.shutdown()
            server.server_close()

    def test_drafthelper_page_links_to_the_help_and_keeps_its_box_short(self):
        box = re.search(r'<div class="help">(.*?)</div>', dh.PAGE, re.S).group(1)
        self.assertIn('href="/howitworks.html', box)
        self.assertLess(len(re.sub(r"<[^>]+>", "", box)), 500)


if __name__ == "__main__":
    unittest.main()
