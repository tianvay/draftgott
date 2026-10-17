"""Kampfmodell Stufe 3: Kennzahlen, besondere Spiele, Mulligan-Kennzeichnung, Spieleliste, Protokolle auf Abruf."""
import io
import json
import pathlib
import random
import tempfile
import time
import unittest
import urllib.request
from unittest import mock

from components import battle as bt
from components import report_server as rs
from components.battle_report import render_battle_html
from components.cards import card_info
from tests.fixtures import args_for
from tests.fixtures_walkers import _card

DASH = "—"
PLAINS = card_info(_card("Plains", f"Basic Land {DASH} Plains", text="({T}: Add {W}.)", produced=["W"]))[0]
BEAR = card_info(_card("Bear", f"Creature {DASH} Bear", "{W}", 1, "W", power="2", toughness="2"))[0]
OGRE = card_info(_card("Ogre", f"Creature {DASH} Ogre", "{1}{W}", 2, "W", power="3", toughness="2"))[0]
BOLT = card_info(_card("Bolt", "Sorcery", "{W}", 1, "W", "Bolt deals 2 damage to target opponent."))[0]
ME = [PLAINS] * 17 + [OGRE] * 13 + [BOLT] * 10
THEM = [PLAINS] * 17 + [BEAR] * 23


def fake(winner, rnd, lives):
    """Spiel mit Lebenspunkten nach jedem Halbzug: lives = [(Wir, Gegner), ...]."""
    return {"winner": winner, "round": rnd, "log": [{"round": i // 2 + 1, "life": {"Wir": w, "Gegner": g}}
                                                    for i, (w, g) in enumerate(lives)]}


class SpecialGameTests(unittest.TestCase):
    def test_definitions(self):
        games = [fake("a", 6, [(20, 20), (18, 12), (15, 0)]),     # Sieg mit 15 Leben
                 fake("a", 7, [(20, 20), (3, 18), (2, 0)]),       # Sieg mit 2 Leben, Rueckstand 15
                 fake("b", 5, [(20, 20), (0, 9)]),                # Niederlage, Gegner bei 9
                 fake("b", 8, [(20, 4), (16, 1), (0, 1)]),        # Niederlage, Gegner bei 1, Vorsprung 15
                 fake(None, 20, [(20, 20)])]
        sp = bt.special_games(games)
        self.assertIs(sp["closest_win"], games[1])
        self.assertIs(sp["comeback_win"], games[1])
        self.assertIs(sp["closest_loss"], games[3])
        self.assertIs(sp["comeback_loss"], games[3])

    def test_no_wins_no_specials(self):
        sp = bt.special_games([fake("b", 5, [(0, 20)])])
        self.assertIsNone(sp["closest_win"])
        self.assertIsNone(sp["comeback_win"])


class StatsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        random.seed(5)
        cls.r = bt.battle(ME, THEM, 120, on_draw=False)

    def test_summary_list_and_full_games(self):
        self.assertEqual(len(self.r["games_list"]), 120)
        self.assertEqual(len(self.r["results_all"]), 120)
        g = self.r["games_list"][0]
        for key in ("n", "winner", "round", "life", "mulligans", "mulligan_loss"):
            self.assertIn(key, g)

    def test_wins_by_round_add_up(self):
        played_wins = self.r["wins"] - self.r["mull_wins"]
        self.assertEqual(sum(self.r["win_by_round"].values()), played_wins)

    def test_life_curve_and_end_life(self):
        curve = self.r["life_curve"]
        self.assertEqual(curve["Wir"][0], 20)
        self.assertLess(curve["Gegner"][-1], 20)
        self.assertTrue(all(0 < x <= 20 for x in self.r["end_life_win"]))

    def test_damage_sources_and_deaths(self):
        self.assertGreater(self.r["combat_damage"]["Wir"], 0)
        self.assertGreater(self.r["direct_damage"]["Wir"], 0)   # Bolt
        self.assertEqual(self.r["direct_damage"]["Gegner"], 0)
        self.assertGreaterEqual(self.r["deaths"]["Gegner"], 0)

    def test_special_games_are_returned(self):
        for key in ("closest_win", "closest_loss", "comeback_win", "comeback_loss"):
            self.assertIn(key, self.r)


def decks_with(results_play, results_draw, name="Splash"):
    return [{"name": name, "battles": [{"enemy": "Mauern", "results": {"On the Play": results_play,
                                                                       "On the Draw": results_draw}}]}]


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        random.seed(6)
        cls.play = bt.battle(ME, THEM, 60, on_draw=False)
        cls.draw = bt.battle(ME, THEM, 60, on_draw=True)

    def html(self, play=None):
        return render_battle_html(decks_with(play or self.play, self.draw), args_for(["deck.txt"]))

    def test_overview_marks_mulligan_losses(self):
        html = self.html()
        self.assertIn("durch Mulligan", html)
        self.assertIn("ohne Mulligan-Aufgaben", html)

    def test_warning_when_many_mulligan_losses(self):
        heavy = dict(self.play, mull_losses=10, losses=self.play["losses"] + 10)
        self.assertIn('class="warnbox"', self.html(heavy))
        self.assertNotIn('class="warnbox"', self.html(dict(self.play, mull_losses=0)))

    def test_charts_and_metrics(self):
        html = self.html()
        sec = html[html.index('id="verlauf"'):html.index("</section>", html.index('id="verlauf"'))]
        self.assertEqual(sec.count("<svg"), 3)  # Siege bis Runde N, Leben Play, Leben Draw
        for text in ("Siege bis Runde", "Lebenspunkte", "Ø Leben am Ende", "Kampfschaden", "direkter Schaden",
                     "gestorbene Kreaturen"):
            self.assertIn(text, sec)

    def test_special_protocol_sections(self):
        html = self.html()
        for sid in ("sieg", "niederlage", "knapp-sieg", "knapp-niederlage", "gedreht-sieg", "gedreht-niederlage"):
            self.assertIn(f'id="{sid}"', html)

    def test_game_list(self):
        html = self.html()
        sec = html[html.index('id="spiele"'):html.index("</section>", html.index('id="spiele"'))]
        self.assertEqual(sec.count('class="game"'), 120)
        self.assertIn('data-m="play"', sec)
        self.assertIn('data-n="0"', sec)
        self.assertIn('id="gameview"', sec)


class GameEndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        folder = pathlib.Path(self.tmp.name)
        (folder / "_enemydeck_walls.txt").write_text("Deck\n17 Plains\n", encoding="utf-8")
        random.seed(7)
        games = {(0, 0, "play"): bt.battle(ME, THEM, 5, on_draw=False)["results_all"]}

        def fake_battle(entries, enemy_path, args, progress):
            return "<p>KAMPF</p>", games

        self._err = mock.patch("sys.stderr", io.StringIO())
        self._err.start()
        self.app = rs.make_app("<p>BERICHT</p>", [{"name": "Wir", "deck": {}}], args_for(["deck.txt"]),
                               fake_battle, None, folder)
        self.server = rs.start(self.app, port=0)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self._err.stop()
        self.tmp.cleanup()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=10) as r:
            return r.read().decode("utf-8")

    def test_protocol_on_demand(self):
        req = urllib.request.Request(self.base + "/api/battle", data=json.dumps({"enemy": "_enemydeck_walls.txt"})
                                     .encode(), headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10).read()
        for _ in range(100):
            if json.loads(self.get("/api/status"))["state"] != "running":
                break
            time.sleep(0.05)
        page = self.get("/game?d=0&e=0&m=play&n=2")
        self.assertIn("Starthand", page)
        self.assertIn("Main 1", page)
        self.assertIn("nicht gefunden", self.get("/game?d=9&e=0&m=play&n=0"))


if __name__ == "__main__":
    unittest.main()
