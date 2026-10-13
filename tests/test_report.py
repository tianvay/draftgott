import unittest
from unittest import mock

import mtg_sim
from components.report import render_great
from tests.fixtures import CARDS, args_for


def deck_data(deck, parts, cats=None, role=None):
    args = args_for(["deck.txt"])
    entry = {"name": "Test", "deck": dict(deck), "parts": parts, "cats": cats or {}, "role": role}
    return mtg_sim.build_deck(entry, CARDS, args)


BASE = {"Plains": 17, "Test Bear": 12, "Test Big": 3, "Test Spell": 4, "Test Gold": 4}
PARTS = [("Core", {"Plains": 17, "Test Bear": 12, "Test Big": 3}), ("Splash", {"Test Spell": 4, "Test Gold": 4})]


class GreatInThisDeckTests(unittest.TestCase):
    def test_empty_without_categories(self):
        self.assertEqual(render_great(deck_data(BASE, PARTS)), "")

    def test_lists_splashworthy_and_mustplay_cards_with_origin(self):
        html = render_great(deck_data(BASE, PARTS, {"Test Gold": "splashworthy", "Test Big": "mustplay"}, "splash"))
        self.assertIn("Test Gold", html)
        self.assertIn("★ Splashworthy", html)
        self.assertIn("Test Big", html)
        self.assertIn("MustPlay", html)
        self.assertIn("Splash</span>", html)  # Bereich der Karte
        self.assertNotIn("Fehlt in diesem Deck", html)

    def test_filler_is_not_listed(self):
        html = render_great(deck_data(BASE, PARTS, {"Test Gold": "splashworthy", "Test Bear": "filler"}, "splash"))
        self.assertNotIn("Test Bear", html)

    def test_missing_mustplay_card_is_reported(self):
        html = render_great(deck_data(BASE, PARTS, {"Test Defender": "mustplay"}, "splash"))
        self.assertIn("Fehlt in diesem Deck", html)
        self.assertIn("Test Defender", html)

    def test_missing_splashworthy_is_reported_only_for_the_splash_variant(self):
        cats = {"Test Defender": "splashworthy", "Test Gold": "mustplay"}
        self.assertIn("Fehlt in diesem Deck", render_great(deck_data(BASE, PARTS, cats, "splash")))
        self.assertNotIn("Fehlt in diesem Deck", render_great(deck_data(BASE, PARTS, cats, "nosplash")))

    def test_neverplay_card_in_deck_is_flagged(self):
        html = render_great(deck_data(BASE, PARTS, {"Test Spell": "neverplay"}, "splash"))
        self.assertIn("NeverPlay-Karten im Deck", html)
        self.assertIn("Test Spell", html)


class EndToEndTests(unittest.TestCase):
    """Komplette Pipeline (Kartendaten, Simulation, HTML) ohne Netzwerk."""

    def build_report(self, cats):
        args = args_for(["deck.txt"])
        core = {"Plains": 12, "Test Bear": 8, "Test Big": 2}
        entries = [
            {"path": "", "name": "Splash", "deck": {**core, "Test Gold": 4, "Swamp": 4},
             "parts": [("Core", core), ("Splash", {"Test Gold": 4, "Swamp": 4})], "cats": cats, "role": "splash"},
            {"path": "", "name": "NoSplash", "deck": {**core, "Test Spell": 4, "Plains": 4 + 12},
             "parts": [("Core", core), ("NoSplash", {"Test Spell": 4, "Plains": 4})], "cats": cats, "role": "nosplash"},
        ]
        entries[1]["deck"] = {**core, "Test Spell": 4}
        entries[1]["deck"]["Plains"] = 16
        args.core = "Core"
        with mock.patch.object(mtg_sim, "fetch_cards_cached", lambda names, refresh=False: CARDS):
            return mtg_sim.simulate_entries(entries, args, progress=lambda m: None)

    def test_report_with_categories_has_great_section_for_each_variant(self):
        html = self.build_report({"Test Gold": "splashworthy", "Test Big": "mustplay"})
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertIn("Great in this deck!", html)
        self.assertIn("Deck-Vergleich", html)
        self.assertIn("Splash", html)
        self.assertIn("NoSplash", html)

    def test_report_without_categories_has_no_great_section(self):
        self.assertNotIn("Great in this deck!", self.build_report({}))


if __name__ == "__main__":
    unittest.main()
