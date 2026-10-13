import unittest
from unittest import mock

import mtg_sim
from components.coverage import M_LETHAL, M_NONE, STATUS_TEXT
from components.report import render_coverage
from tests.fixtures import args_for
from tests.fixtures_walkers import DATA

DASH = "—"

CARDS = dict(DATA)
CARDS.update({
    "Test Token Maker": {"name": "Test Token Maker", "type_line": f"Creature {DASH} Test", "mana_cost": "{2}{W}",
                         "cmc": 3.0, "colors": ["W"], "keywords": [], "layout": "normal", "power": "2",
                         "toughness": "2",
                         "oracle_text": "When this creature enters, create a 2/2 colorless Wizard Soldier creature "
                                        "token named Cadet.\nFlying"},
    "Test Removal": {"name": "Test Removal", "type_line": "Instant", "mana_cost": "{1}{W}", "cmc": 2.0,
                     "colors": ["W"], "keywords": [], "layout": "normal", "oracle_text": "Exile target creature."},
})


def deck(names):
    entry = {"name": "Test", "deck": dict(names), "parts": [("Test", dict(names))]}
    return mtg_sim.build_deck(entry, CARDS, args_for(["deck.txt"]))


MIXED = {"Plains": 17, "Test Bear": 12, "Test Token Maker": 4, "Test Removal": 2, "Test Empower": 5}


class BuildDeckCoverageTests(unittest.TestCase):
    def test_deck_carries_coverage_for_every_card(self):
        dd = deck(MIXED)
        self.assertEqual(set(dd["coverage"]), set(MIXED))

    def test_only_unmodeled_cards_have_items(self):
        cov = deck(MIXED)["coverage"]
        self.assertEqual(cov["Test Bear"], [])
        self.assertEqual(cov["Plains"], [])
        self.assertEqual(cov["Test Empower"], [])           # Empower Jace ist modelliert
        self.assertTrue(cov["Test Token Maker"])
        self.assertTrue(cov["Test Removal"])


class CoverageSectionTests(unittest.TestCase):
    def test_flagged_cards_are_listed_with_status_category_and_metric(self):
        html = render_coverage(deck(MIXED))
        self.assertIn("Test Token Maker", html)
        self.assertIn("Test Removal", html)
        self.assertIn(STATUS_TEXT, html)
        self.assertIn("Tokens erzeugen", html)
        self.assertIn("Interaktion mit dem Gegner", html)
        self.assertIn(M_LETHAL, html)
        self.assertIn(M_NONE, html)

    def test_modeled_cards_are_not_listed(self):
        html = render_coverage(deck(MIXED))
        self.assertNotIn("Test Bear", html)
        self.assertNotIn("Test Empower", html)
        self.assertNotIn(">Plains<", html)

    def test_quantity_is_shown(self):
        html = render_coverage(deck(MIXED))
        self.assertIn("<td>4</td>", html)  # Test Token Maker x4

    def test_summary_counts_cards_per_metric(self):
        html = render_coverage(deck(MIXED))
        self.assertIn("2 Karten", html)  # beide markierten Karten
        self.assertIn("6 Kopien", html)

    def test_message_when_nothing_is_flagged(self):
        html = render_coverage(deck({"Plains": 17, "Test Bear": 23}))
        self.assertIn("Keine Karte", html)
        self.assertNotIn(STATUS_TEXT, html)

    def test_section_appears_in_the_full_report(self):
        args = args_for(["deck.txt"])
        entries = [{"path": "", "name": "Test", "deck": dict(MIXED), "parts": [("Test", dict(MIXED))]}]
        with mock.patch.object(mtg_sim, "fetch_cards_cached", lambda names, refresh=False: CARDS):
            html = mtg_sim.simulate_entries(entries, args, progress=lambda m: None)
        self.assertIn("Modell-Abdeckung", html)
        self.assertIn(STATUS_TEXT, html)


if __name__ == "__main__":
    unittest.main()
