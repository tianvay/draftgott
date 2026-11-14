"""Setauswertung, Archetypen-Kacheln: die Zeile "Games gewonnen" erscheint nur, wenn sie etwas anderes zeigt als
"Matches gewonnen" (bei Bo1 ist jedes Match genau ein Game, dann waere sie doppelt)."""
import unittest

from components import setreport
from tests.i18n_check import english


def rec(event, matches):
    return {"event": event, "set": "TRK", "started": "2026-11-14", "picks": [], "pick_sizes": [],
            "deck": {"main": {"A": 1}, "side": {}}, "matches": matches}


def bo1(i, win):
    return {"id": str(i), "deck": {"A": 1}, "games": [win], "win": win}


def bo3(i, games):
    return {"id": str(i), "deck": {"A": 1}, "games": games, "win": sum(games) >= 2}


def tiles(records):
    return setreport._archetypes(records, "TRK", {}, {}, {})


class ArchetypeGamesRowTests(unittest.TestCase):
    def test_bo1_shows_only_matches_row(self):
        html = tiles([rec("PremierDraft_TRK_1", [bo1(1, True), bo1(2, False), bo1(3, True)])])
        self.assertIn("Matches gewonnen", html)
        self.assertNotIn("Games gewonnen", html)
        self.assertEqual(html.count('class="meter'), html.count("Matches gewonnen"))

    def test_bo3_with_different_rate_shows_games_row(self):
        html = tiles([rec("TradDraft_TRK_1", [bo3(1, [True, False, True]), bo3(2, [False, False])])])
        self.assertIn("Matches gewonnen", html)  # 1 von 2 = 50 %
        self.assertIn("Games gewonnen", html)  # 2 von 5 = 40 %

    def test_bo3_with_same_rate_hides_games_row(self):
        html = tiles([rec("TradDraft_TRK_1", [bo3(1, [True, True]), bo3(2, [False, False])])])
        self.assertNotIn("Games gewonnen", html)  # 1/2 Matches, 2/4 Games: beides 50 %

    def test_english(self):
        with english():
            html = tiles([rec("TradDraft_TRK_1", [bo3(1, [True, False, True]), bo3(2, [False, False])])])
            self.assertIn("Matches won", html)
            self.assertIn("Games won", html)
            html = tiles([rec("PremierDraft_TRK_1", [bo1(1, True)])])
            self.assertNotIn("Games won", html)


if __name__ == "__main__":
    unittest.main()
