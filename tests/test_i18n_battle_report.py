"""Englischer Kampfbericht (components/battle_report.py): keine deutschen Reste, Deutsch unveraendert.

Die Ereigniszeilen der Zugprotokolle (events, note) kommen aus components/battle.py und werden dort uebersetzt;
sie werden hier vor der Pruefung aus den Spielen entfernt."""
import copy
import random
import unittest

from components import battle as bt
from components import battle_report as br
from components import i18n
from components.battle_report import render_battle_html
from tests.fixtures import args_for
from tests.i18n_check import english, german_leftovers
from tests.test_battle_stage3 import ME, THEM, decks_with

ALLOW = ["Mauern", "Splash", "NoSplash"]


def strip_events(obj):
    """Entfernt die Ereigniszeilen (kommen aus battle.py) aus allen Spielprotokollen."""
    if isinstance(obj, dict):
        if "events" in obj:
            obj["events"] = []
        if "note" in obj:
            obj["note"] = ""
        for v in obj.values():
            strip_events(v)
    elif isinstance(obj, list):
        for v in obj:
            strip_events(v)


class BattleReportEnglish(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        random.seed(6)
        cls.play = bt.battle(ME, THEM, 60, on_draw=False)
        cls.draw = bt.battle(ME, THEM, 60, on_draw=True)
        cls.args = args_for(["deck.txt"])

    def decks(self, multi=False):
        decks = decks_with(copy.deepcopy(self.play), copy.deepcopy(self.draw))
        if multi:
            decks.append(copy.deepcopy(decks_with(self.play, self.draw, "NoSplash")[0]))
        return decks

    def render(self, decks):
        return render_battle_html(decks, self.args)

    def test_no_german_leftovers(self):
        for multi in (False, True):
            decks = self.decks(multi)
            strip_events(decks)
            with english():
                html = self.render(decks)
            self.assertIn('<html lang="en">', html)
            self.assertEqual(german_leftovers(html, allow=ALLOW), [], f"multi={multi}")

    def test_game_protocol_title(self):
        game = self.play["longest_game"]
        game = copy.deepcopy(game)
        strip_events(game)
        with english():
            html = br.protocol_html(game, "On the Play", "Spiel 3: Sieg")
        self.assertIn("Game 3: Win", html)
        self.assertEqual(german_leftovers(html), [])

    def test_german_unchanged(self):
        a = self.render(self.decks())
        with english():
            self.render(self.decks())
        b = self.render(self.decks())
        # Zeitstempel (Minute) kann sich unterscheiden
        strip = lambda h: h.split("erstellt am", 1)[0] + h.split("erstellt am", 1)[1].split("</span>", 1)[1]
        self.assertEqual(strip(a), strip(b))
        self.assertIn('<html lang="de">', a)
        self.assertIn("So funktioniert der Kampf", a)

    def test_every_rule_and_key_has_english(self):
        table = i18n.en_table()
        for r in br.RULES:
            self.assertIn(r, table)
            self.assertNotEqual(table[r], r)
        keys = list(br.SPECIAL_NOTE.values()) + list(br.RESULT_LABEL.values()) + [s[2] for s in br.SPECIALS]
        for k in keys:
            self.assertIn(k, table)

    def test_js_table_keys_in_template(self):
        for k in br.GAMES_JS_EN:
            self.assertIn(k, br.GAMES_JS)


if __name__ == "__main__":
    unittest.main()
