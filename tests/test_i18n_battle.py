"""Englische Ausgabe des Kampfmotors: Spielprotokoll (Ereignisse) und Meldungen der Kampf-Schnittstelle."""
import ast
import contextlib
import json
import pathlib
import random
import unittest
from unittest import mock

from components import battle as bt
from components import battle_server as bs
from components import i18n
from components.i18n_en.battle import EN as EN_BATTLE
from components.i18n_en.battle_server import EN as EN_SERVER
from tests.i18n_check import english, german_leftovers
from tests.test_battle import deck
from tests.test_battle_ours import APEX, INGRIS, player

ROOT = pathlib.Path(__file__).resolve().parent.parent


def all_events(res):
    return [x for g in res["results_all"] for e in g["log"] for x in e.get("events", [])]


def run(seed, lang_en):
    random.seed(seed)
    d1 = deck({"Plains": 17, "Test Giant": 8, "Test Bear": 9, "Test Bolt": 6})
    d2 = deck({"Plains": 17, "Test Wall": 10, "Test Bear": 13})
    if lang_en:
        with english():
            return bt.battle(d1, d2, 12, on_draw=False)
    return bt.battle(d1, d2, 12, on_draw=False)


def dumps(res):
    return json.dumps(res, default=str, ensure_ascii=False, sort_keys=True)


class BattleEventsEnglish(unittest.TestCase):
    def test_battle_events_english_have_no_german(self):
        events = []
        for seed in (1, 2, 3):
            events += all_events(run(seed, True))
        self.assertGreater(len(events), 50)
        for ev in events:
            self.assertEqual(german_leftovers(ev, allow=["Test Giant", "Test Bear", "Test Wall", "Test Bolt"]), [], ev)
        self.assertTrue(any(ev.startswith("We: ") for ev in events))

    def test_german_battle_unchanged_and_deterministic(self):
        a, b = run(5, False), run(5, False)
        self.assertEqual(dumps(a), dumps(b))
        events = all_events(a)
        self.assertTrue(any(ev.startswith("Wir: ") for ev in events))
        self.assertTrue(all(german_leftovers(ev) is not None for ev in events))
        # Englisch und Deutsch spielen dieselben Spiele (nur der Text unterscheidet sich)
        en = run(5, True)
        self.assertEqual([g["winner"] for g in a["results_all"]], [g["winner"] for g in en["results_all"]])
        self.assertEqual(len(all_events(a)), len(all_events(en)))

    def test_unit_events_in_both_languages(self):
        for lang_en in (False, True):
            random.seed(1)
            me, opp = player(), player("Gegner")
            me.creatures = [bt.Creature(INGRIS, 0)]
            me.hand = [APEX]
            if lang_en:
                with english():
                    e = bt.take_turn(me, opp, 7, 3, skip_draw=True)
            else:
                e = bt.take_turn(me, opp, 7, 3, skip_draw=True)
            text = " | ".join(e["events"])
            self.assertEqual(bool(german_leftovers(text, allow=["Apex Witchstalker", "Ingris Stingerquill"])),
                             not lang_en, text)

    def test_mulligan_loss_note_and_detection_in_english(self):
        real = bt.deal_opening

        def deal_factory():
            calls = {"n": 0}

            def deal(cards, mulligan, min_hand, keep_at_min=False):
                calls["n"] += 1
                if calls["n"] == 1:
                    return None, None, 3, []
                return real(cards, mulligan, min_hand, keep_at_min=keep_at_min)
            return deal

        results = {}
        for lang_en in (False, True):
            random.seed(4)
            with mock.patch.object(bt, "deal_opening", deal_factory()):
                d1, d2 = deck({"Plains": 17, "Test Bear": 23}), deck({"Plains": 17, "Test Wall": 23})
                if lang_en:
                    with english():
                        results[lang_en] = bt.battle(d1, d2, 3, on_draw=False)
                else:
                    results[lang_en] = bt.battle(d1, d2, 3, on_draw=False)
        self.assertEqual(results[False]["mull_losses"], 1)
        self.assertEqual(results[True]["mull_losses"], 1)
        notes_de = [g.get("note") for g in results[False]["results_all"] if g.get("note")]
        notes_en = [g.get("note") for g in results[True]["results_all"] if g.get("note")]
        self.assertEqual(notes_de, ["Spiel durch Mulligan verloren"])
        self.assertEqual(notes_en, ["Game lost by mulligan"])

    def test_hold_mana_prefix_matches_event_text(self):
        # Die Erkennung "haelt Mana frei" nutzt dasselbe Praefix wie der Ereignistext, in beiden Sprachen
        for lang_en, prefix in ((False, "Wir: hält "), (True, "We: holds ")):
            with (english() if lang_en else contextlib.nullcontext()):
                self.assertEqual(i18n.t("{me}: hält ", me=i18n.t("Wir")), prefix)
                self.assertTrue(i18n.t("{me}: hält {x2} Mana für {x3} offen", me=i18n.t("Wir"), x2=2, x3="X")
                                .startswith(prefix))


class BattleDictionary(unittest.TestCase):
    def test_every_battle_key_translated_and_placeholders_match(self):
        tree = ast.parse((ROOT / "components" / "battle.py").read_text(encoding="utf-8"))
        keys = set()
        for n in ast.walk(tree):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "t"
                    and getattr(n.func.value, "id", "") == "i18n" and isinstance(n.args[0], ast.Constant)):
                keys.add(n.args[0].value)
        self.assertGreater(len(keys), 300)
        self.assertEqual([k for k in keys if k not in EN_BATTLE], [])
        for k in list(EN_BATTLE) + list(EN_SERVER):
            self.assertEqual(german_leftovers(EN_BATTLE.get(k) or EN_SERVER[k], allow=["Klingon"]), [], k)

    def test_texts_from_variables_are_in_dictionary(self):
        for key in ("Auslöser beim Wirken", "Wir", "Gegner", "Ende des gegnerischen Zugs", "Land fehlt", "Fähigkeit"):
            self.assertIn(key, EN_BATTLE)


class BattleServerEnglish(unittest.TestCase):
    def test_game_fragment_messages(self):
        app = {"battle_games": {}}
        with english():
            html = bs.game_fragment(app, "d=0&e=0&n=0&m=play")
        self.assertEqual(html, '<p class="muted">Game not found (recreate the battle report).</p>')
        self.assertIn("Spiel nicht gefunden", bs.game_fragment(app, "d=0&e=0&n=0&m=play"))

    def test_game_fragment_note(self):
        app = {"battle_games": {(0, 0, "play"): [{"winner": "b", "note": "x"}]}}
        with english():
            self.assertEqual(bs.game_fragment(app, "d=0&e=0&n=0&m=play"), '<p class="muted">Game 1: x (no turns).</p>')
        self.assertEqual(bs.game_fragment(app, "d=0&e=0&n=0&m=play"),
                         '<p class="muted">Spiel 1: x (keine Züge).</p>')

    def test_start_battle_errors(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            folder = pathlib.Path(tmp)
            (folder / "enemydecks").mkdir()
            (folder / "enemydecks" / "a.txt").write_text("Deck\n17 Plains\n", encoding="utf-8")
            with english():
                self.assertEqual(bs.start_battle({}, {"enemy": "zz.txt"}, folder)[1]["error"], "Unknown opponent deck")
                self.assertIn("Please simulate first", bs.start_battle({}, {"enemy": "a.txt"}, folder)[1]["error"])
                app = {"last_entries": [1], "last_args": None, "battle": lambda *a: ""}
                self.assertEqual(bs.start_battle(app, {"enemy": "a.txt", "games": 99999}, folder)[1]["error"],
                                 "Invalid number of battles (1 to 5000)")
            self.assertEqual(bs.start_battle({}, {"enemy": "zz.txt"}, folder)[1]["error"], "Unbekanntes Gegnerdeck")


if __name__ == "__main__":
    unittest.main()
