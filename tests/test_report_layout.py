import re
import unittest
from unittest import mock

import mtg_sim
from components.html_base import HTML_CSS
from tests.fixtures import CARDS, args_for


def report(two_decks=False):
    deck = {"Plains": 17, "Test Bear": 20, "Test Spell": 3}
    entries = [{"path": "", "name": "A", "deck": dict(deck), "parts": [("A", dict(deck))]}]
    if two_decks:
        entries.append({"path": "", "name": "B", "deck": dict(deck), "parts": [("B", dict(deck))]})
    with mock.patch.object(mtg_sim, "fetch_cards_cached", lambda n, refresh=False: CARDS):
        return mtg_sim.simulate_entries(entries, args_for(["deck.txt", "--sims", "100"]), progress=lambda m: None)


class SideNavigationTests(unittest.TestCase):
    def test_navigation_sits_in_a_layout_next_to_the_content(self):
        html = report()
        self.assertRegex(html, r'<div class="layout"><nav[^>]*>.*?</nav><main>', )

    def test_navigation_links_are_stacked_vertically_on_wide_screens(self):
        self.assertIn("grid-template-columns:220px minmax(0,1fr)", HTML_CSS)
        self.assertRegex(HTML_CSS, r"nav \.in\{[^}]*flex-direction:column")

    def test_narrow_screens_fall_back_to_a_horizontal_bar(self):
        m = re.search(r"@media\s*\(max-width:\s*900px\)\{(.*?)\}\}", HTML_CSS, re.S)
        self.assertIsNotNone(m)
        self.assertIn("grid-template-columns:1fr", m.group(1))

    def test_every_section_has_a_link(self):
        html = report()
        ids = re.findall(r'<section id="([^"]+)"', html)
        links = set(re.findall(r'href="#([^"]+)"', html))
        self.assertTrue(ids)
        self.assertEqual(set(ids) - links, set())

    def test_deck_comparison_keeps_one_link_list_per_deck(self):
        html = report(two_decks=True)
        nav = re.search(r"<nav[^>]*>(.*?)</nav>", html, re.S).group(1)
        self.assertEqual(nav.count('class="in grpnav'), 2)


class JaceReportTests(unittest.TestCase):
    def test_jace_rules_mention_surveil_and_the_land_rule(self):
        from components.report_sections import JACE_RULES
        text = " ".join(JACE_RULES)
        self.assertIn("−1: Surveil 1", text)
        self.assertIn("teuerste Karte", text)
        self.assertIn("Zauber bleiben immer oben", text)


if __name__ == "__main__":
    unittest.main()
