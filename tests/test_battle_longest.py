"""Kampfbericht: laengstes Spiel (die meisten Runden, egal ob Sieg, Niederlage oder Unentschieden) mit Zugprotokoll."""
import random
import unittest

from components import battle as bt
from components.battle_report import render_battle_html
from tests.fixtures import args_for
from tests.test_battle_stage3 import ME, THEM, decks_with, fake


class LongestGameTests(unittest.TestCase):
    def test_most_rounds_over_all_results(self):
        games = [fake("a", 6, [(20, 20)]), fake("b", 9, [(20, 20)]), fake(None, 7, [(20, 20)])]
        self.assertIs(bt.special_games(games)["longest_game"], games[1])

    def test_tie_more_half_turns(self):
        games = [fake("a", 6, [(20, 20)]), fake("b", 6, [(20, 20), (18, 20)])]
        self.assertIs(bt.special_games(games)["longest_game"], games[1])

    def test_none_without_games(self):
        self.assertIsNone(bt.special_games([])["longest_game"])

    def test_report_section_with_result(self):
        random.seed(7)
        play = bt.battle(ME, THEM, 40, on_draw=False)
        draw = bt.battle(ME, THEM, 40, on_draw=True)
        html = render_battle_html(decks_with(play, draw), args_for(["deck.txt"]))
        self.assertIn('id="laengstes"', html)
        sec = html[html.index('id="laengstes"'):html.index("</section>", html.index('id="laengstes"'))]
        rounds = max(g["round"] for g in (play["longest_game"], draw["longest_game"]))
        self.assertIn(f"in Runde {rounds}", sec)
        self.assertTrue(any(w in sec for w in ("Sieg", "Niederlage", "Unentschieden")))


if __name__ == "__main__":
    unittest.main()
