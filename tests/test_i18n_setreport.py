"""Englische Setauswertung und Draft-Statistik: keine deutschen Reste, Deutsch unveraendert."""
import contextlib
import io
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from components import draftstats as ds
from components import setreport
from components.cli import parse_args
from tests.i18n_check import english, german_leftovers
from tests.test_draftstats import sample_data

CARDS = {"A": {"name": "A", "colors": ["W"], "mana_cost": "{W}", "rarity": "common", "type_line": "Creature"},
         "C": {"name": "C", "colors": ["U"], "mana_cost": "{U}", "rarity": "rare", "type_line": "Instant"}}


def many_games():
    data = sample_data()
    data["drafts"][0]["matches"] = [{"id": str(i), "deck": {"A": 1, "C": 1}, "games": [i % 2 == 0],
                                     "win": i % 2 == 0} for i in range(24)] + [
        {"id": "open", "deck": {"A": 1}, "games": [], "win": None}]
    return data


def render(data, cards=None):
    return setreport.render_set_report(data, "TRK", CARDS if cards is None else cards, {"A": ["WU"]},
                                       {"A": "mustplay", "C": "filler"})


class SetReportEnglish(unittest.TestCase):
    def check(self, html):
        self.assertEqual(german_leftovers(html, allow=["Spacecraft"]), [])

    def test_no_german_leftovers(self):
        with english():
            html = render(sample_data())
            self.check(html)
            self.assertIn('<html lang="en">', html)
            self.assertIn("Set report TRK", html)
            self.check(render(many_games()))  # Tabelle mit Balken, beste/schwaechste Karten
            self.check(render(sample_data(), {}))  # ohne Kartendaten
            self.check(setreport.render_set_report({"version": 1, "drafts": []}, "TRK", {}, {}, {}))

    def test_decimal_point(self):
        with english():
            html = render(sample_data())
            self.assertIn(">2.5</td>", html)  # Ø Pick
            self.assertIn("<b>1.0</b>", html)  # Siege je Draft
        html = render(sample_data())
        self.assertIn(">2,5</td>", html)
        self.assertIn("<b>1,0</b>", html)

    def test_german_unchanged(self):
        before = render(many_games())
        with english():
            render(many_games())
        self.assertEqual(render(many_games()), before)
        self.assertIn('<html lang="de">', before)
        for text in ("Setauswertung TRK", "Überblick", "mitgelesen", "Siege je Draft", "Sortieren", " von ",
                     'title="Sieg">S</i>', "Match-Verlauf (älteste zuerst)", "nur gespielte Karten"):
            self.assertIn(text, before)

    def test_js_table_keys_in_template(self):
        for key in setreport.JS_EN:
            self.assertIn(key, setreport.JS)

    def test_console_messages(self):
        with tempfile.TemporaryDirectory() as d, english():
            stats = pathlib.Path(d) / "s.json"
            stats.write_text(json.dumps(sample_data()), encoding="utf-8")
            args = parse_args(["--setauswertung", "--statistik", str(stats), "--nicht-oeffnen"])
            err = io.StringIO()
            with mock.patch.object(setreport, "fetch_cards_cached", lambda names, refresh=False: {}), \
                    mock.patch.object(setreport, "OUT_DIR", pathlib.Path(d)), contextlib.redirect_stderr(err):
                out = setreport.run(args)
            self.assertIn("Set report saved", err.getvalue())
            self.check(out.read_text(encoding="utf-8"))
            empty = pathlib.Path(d) / "e.json"
            args = parse_args(["--setauswertung", "--statistik", str(empty), "--nicht-oeffnen"])
            with self.assertRaises(SystemExit) as cm:
                setreport.run(args)
            self.assertEqual(german_leftovers(str(cm.exception)), [])
            self.assertIn("No drafts in", str(cm.exception))


class DraftStatsEnglish(unittest.TestCase):
    def test_enemy_deck_messages(self):
        tracker = ds.Tracker("unused.json", lambda g: None, enemy_dir=None)
        rec = {"set": "TRK", "matches": [{"win": True}] * 4, "deck": {"side": {}}}
        match = {"deck": {"A": 1}}
        with tempfile.TemporaryDirectory() as d, english():
            tracker.enemy_dir = pathlib.Path(d)
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                tracker._save_enemy(rec, match)
            self.assertIn("Opponent deck saved", err.getvalue())
            self.assertEqual(german_leftovers(err.getvalue()), [])
            tracker.enemy_dir = pathlib.Path(d) / "datei.txt"
            tracker.enemy_dir.write_text("x")
            rec2 = {"set": "TRK", "matches": [{"win": True}] * 4, "deck": {"side": {}}}
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                tracker._save_enemy(rec2, match)
            self.assertIn("Opponent deck not saved", err.getvalue())

    def test_rate_text_unchanged(self):
        self.assertEqual(ds.rate_text({"games": 4, "wins": 3}), "75 % in 4 Games")


if __name__ == "__main__":
    unittest.main()
