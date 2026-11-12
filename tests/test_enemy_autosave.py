"""Decks mit 4 Siegen landen automatisch als Gegnerdeck in enemydecks/:
drafted_<SET>_4wins_<Farben aus dem Hauptdeck>_<JJJJ-MM-TT>_<hhmm>.txt"""
import json
import pathlib
import tempfile
import unittest

from components import draftstats as ds
from tests.test_draftstats import EVENT, auth_line, deck_line, end_line, lookup, notify, pick, start_line

INFO = {101: {"name": "Test Bear", "set": "TST", "number": "10", "colors": ["W"]},
        102: {"name": "Test Hasty", "set": "TST", "number": "11", "colors": ["R"]},
        103: {"name": "Test Spell", "set": "TST", "number": "15", "colors": ["W"]},
        104: {"name": "Test Gold", "set": "TST", "number": "14", "colors": ["W", "B"]},
        105: {"name": "Test Big", "set": "TST", "number": "13", "colors": ["W"]},
        201: {"name": "Plains", "set": "TST", "number": "1", "colors": []},
        202: {"name": "Mountain", "set": "TST", "number": "4", "colors": []}}
DRAFT = []
for _i, _g in enumerate([101, 102, 103, 104, 105]):
    DRAFT += [notify(_i + 1, [_g, 201], draft="d1"), pick([_g], draft="d1")]
DECK = deck_line([(101, 1), (103, 1), (105, 1), (102, 1), (201, 9)], [(104, 1)])  # 3x Weiss, 1x Rot


def stamp(text="12.11.2026 20:47:13"):
    return f"[UnityCrossThreadLogger]{text}: Match to ME: MatchGameRoomStateChangedEvent"


def matches(results, start=1):
    """Matches mit Ergebnis (True = Sieg); eigenes Team 2."""
    lines = []
    for i, win in enumerate(results, start):
        lines += [start_line(f"m{i}"), stamp(), end_line(f"m{i}", [2 if win else 1], 2 if win else 1)]
    return lines


class AutosaveTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        d = pathlib.Path(self.dir.name)
        self.path, self.enemies = d / "draftstatistik.json", d / "enemydecks"
        self.enemies.mkdir()

    def tearDown(self):
        self.dir.cleanup()

    def tracker(self):
        return ds.Tracker(self.path, lookup, lambda g: "TRK", enemy_dir=self.enemies, card_info=INFO.get)

    def feed(self, t, *lines):
        for line in lines:
            t.feed_line(line)
        return sorted(p.name for p in self.enemies.iterdir())

    def test_fourth_win_saves_the_deck(self):
        t = self.tracker()
        self.assertEqual(self.feed(t, auth_line(), *DRAFT, DECK, *matches([True, False, True, True])), [])
        files = self.feed(t, *matches([True], start=5))
        self.assertEqual(files, ["drafted_TRK_4wins_whitesplashred_2026-11-12_2047.txt"])
        self.assertEqual(t.last_saved, files[0])
        text = (self.enemies / files[0]).read_text(encoding="utf-8")
        self.assertEqual(text, "Deck\n1 Test Bear (TST) 10\n1 Test Spell (TST) 15\n1 Test Big (TST) 13\n"
                               "1 Test Hasty (TST) 11\n9 Plains (TST) 1\n\nSideboard\n1 Test Gold (TST) 14\n")
        rec = ds.load_stats(self.path)["drafts"][0]
        self.assertEqual(rec["enemy_deck"], files[0])

    def test_only_once_and_not_again_after_restart(self):
        lines = [auth_line(), *DRAFT, DECK, *matches([True] * 5)]
        self.assertEqual(len(self.feed(self.tracker(), *lines)), 1)  # 5. Sieg legt keine zweite Datei an
        for p in self.enemies.iterdir():
            p.write_text("von Hand geaendert", encoding="utf-8")
        self.feed(self.tracker(), *lines)  # draftgott neu gestartet, Protokoll von vorn
        self.assertEqual([p.read_text(encoding="utf-8") for p in self.enemies.iterdir()], ["von Hand geaendert"])

    def test_existing_file_is_never_overwritten(self):
        lines = [auth_line(), *DRAFT, DECK, *matches([True] * 4)]
        self.feed(self.tracker(), *lines)
        for p in self.enemies.iterdir():
            p.write_text("von Hand geaendert", encoding="utf-8")
        self.path.unlink()  # Statistik geloescht: alles wird neu gesammelt
        t = self.tracker()
        self.feed(t, *lines)
        self.assertEqual([p.read_text(encoding="utf-8") for p in self.enemies.iterdir()], ["von Hand geaendert"])
        self.assertIsNone(t.last_saved)

    def test_three_wins_save_nothing(self):
        self.assertEqual(self.feed(self.tracker(), auth_line(), *DRAFT, DECK, *matches([True, True, True, False])),
                         [])

    def test_without_enemy_dir_nothing_is_saved(self):
        t = ds.Tracker(self.path, lookup, lambda g: "TRK")
        self.assertEqual(self.feed(t, auth_line(), *DRAFT, DECK, *matches([True] * 4)), [])
        self.assertIsNone(t.last_saved)

    def test_rebuild_saves_nothing(self):
        log = pathlib.Path(self.dir.name) / "Player.log"
        log.write_text("\n".join([auth_line(), *DRAFT, DECK, *matches([True] * 4)]) + "\n", encoding="utf-8")
        ds.rebuild(self.path, [log], lookup, lambda g: "TRK")
        self.assertEqual(list(self.enemies.iterdir()), [])


class NameTests(unittest.TestCase):
    def colors(self, *cards):
        return ds.color_name({n: q for n, q in cards}, {"A": ["W"], "B": ["R"], "C": ["U"], "D": ["W", "U"],
                                                         "L": []})

    def test_order_and_splash(self):
        self.assertEqual(self.colors(("A", 3), ("B", 1)), "whitesplashred")
        self.assertEqual(self.colors(("A", 3), ("B", 5)), "redwhite")  # meiste Karten zuerst
        self.assertEqual(self.colors(("A", 2), ("B", 5)), "redsplashwhite")  # 2 Karten: Splash
        self.assertEqual(self.colors(("A", 3), ("B", 3)), "whitered")  # Gleichstand: WUBRG
        self.assertEqual(self.colors(("A", 4), ("B", 4), ("C", 2)), "whiteredsplashblue")
        self.assertEqual(self.colors(("B", 7)), "red")
        self.assertEqual(self.colors(("D", 3), ("B", 3)), "whitebluered")  # Gleichstand aller drei: WUBRG
        self.assertEqual(self.colors(("L", 5)), "colorless")
        self.assertEqual(self.colors(("A", 1)), "white")  # nur eine Farbe: kein Splash

    def test_hybrid_counts_for_a_color_the_deck_plays(self):
        cols = {"A": ds.cost_colors("{1}{W}"), "B": ds.cost_colors("{R}{R}"), "H": ds.cost_colors("{3}{G/W}{G/W}"),
                "P": ds.cost_colors("{2/B}{R}"), "Q": ds.cost_colors("{U/P}")}
        self.assertEqual(ds.color_name({"A": 3, "B": 4, "H": 1, "P": 1, "Q": 1}, cols), "redwhite")
        self.assertEqual(ds.color_name({"H": 2}, cols), "green")  # nur Hybrid: erste Farbe
        self.assertEqual(ds.cost_colors("{3}{G/W}{G/W}"), ["G/W"])
        self.assertEqual(ds.cost_colors("{W}{U}"), ["W", "U"])
        self.assertEqual(ds.cost_colors("{2/B}{U/P}"), [])  # auch ohne die Farbe bezahlbar
        self.assertEqual(ds.cost_colors(""), [])

    def test_file_name(self):
        self.assertEqual(ds.enemy_file_name("TRK", "redwhite", "2026-11-12 20:47"),
                         "drafted_TRK_4wins_redwhite_2026-11-12_2047.txt")

    def test_timestamps(self):
        self.assertEqual(ds.log_stamp("[UnityCrossThreadLogger]12.11.2026 20:47:13: Match to X"), "2026-11-12 20:47")
        self.assertEqual(ds.log_stamp("[UnityCrossThreadLogger]11/12/2026 8:47:13 PM: Match to X"), "2026-11-12 20:47")
        self.assertEqual(ds.log_stamp("[UnityCrossThreadLogger]11/12/2026 12:05:00 AM: x"), "2026-11-12 00:05")
        self.assertIsNone(ds.log_stamp("nichts"))


class LiveTests(unittest.TestCase):
    def test_snapshot_reports_the_saved_deck(self):
        from components import livedraft as ld
        from components import overlay
        from tests.fixtures import CARDS
        names = {g: {k: v for k, v in i.items() if k != "colors"} for g, i in INFO.items()}
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            (d / "enemydecks").mkdir()
            log = d / "Player.log"
            log.write_text("\n".join([auth_line(), *DRAFT, DECK, *matches([True] * 4)]) + "\n", encoding="utf-8")
            live = ld.LiveDraft(log, d / "pool.txt", names=names, fetch=lambda n, refresh=False: CARDS,
                                stats=d / "s.json", enemy_dir=d / "enemydecks")
            live.step()
            snap = live.snapshot({}, {}, None)
            self.assertTrue(snap["enemy_saved"].startswith("drafted_TRK_4wins_white"))
            self.assertIn("Gegnerdeck gespeichert", "\n".join(r[0] for r in overlay.rows_for(snap)))
            self.assertEqual(len(list((d / "enemydecks").iterdir())), 1)

    def test_page_and_help(self):
        from components.drafthelper import render_page
        from components.howitworks import render_help_page
        self.assertIn("enemy_saved", render_page())
        self.assertIn("4wins", render_help_page())
        readme = (pathlib.Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
        self.assertIn("4wins", readme)


if __name__ == "__main__":
    unittest.main()
