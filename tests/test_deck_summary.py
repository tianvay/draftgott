"""Nach dem Draft (und zwischen den Spielen) zeigt das Seitenfenster statt "Pick 43" eine kurze Deck-Uebersicht wie
auf der Drafthelper-Seite: Bilanz, Karten und Laender, Mana-Kurve, Kreaturen, Removal, Kartenfluss, Farben, Bomben."""
import pathlib
import tempfile
import unittest

from components import draftstats as ds
from components import livedraft as ld
from components import overlay
from tests.fixtures import CARDS
from tests.test_deck_transfer import DECK, DRAFT, NAMES
from tests.test_draftstats import auth_line, end_line, start_line

EVENT = "PremierDraft_TST_20261110"  # wie DECK in test_deck_transfer


def card(name, mv=1, qty=1, colors="W", land=False, creature=False, removal=0, flow=()):
    return {"name": name, "mv": mv, "qty": qty, "colors": list(colors), "land": land, "creature": creature,
            "removal": removal, "flow": list(flow)}


DECK_CARDS = [card("Plains", 0, 9, "", land=True), card("Mountain", 0, 8, "", land=True),
              card("Bear", 2, 3, "W", creature=True), card("Bolt", 1, 2, "R", removal=1.5),
              card("Big", 6, 1, "W", creature=True), card("Seven", 7, 1, "R", creature=True),
              card("Gold", 3, 1, "WB", creature=True, flow=["draw"]), card("Zero", 0, 1, "")]


class SummaryTests(unittest.TestCase):
    def test_numbers(self):
        s = ld.deck_summary(DECK_CARDS, {"Big": "matchwinner", "Bolt": "mustplay", "Bear": "filler"}, "arena")
        self.assertEqual(s["source"], "arena")
        self.assertEqual((s["cards"], s["lands"], s["spells"]), (26, 17, 9))
        self.assertEqual(s["curve"], [3, 3, 1, 0, 0, 2])  # <=1, 2, 3, 4, 5, 6+ (Laender zaehlen nicht)
        self.assertEqual(s["avg_mv"], round((0 + 1 * 2 + 2 * 3 + 3 + 6 + 7) / 9, 2))
        self.assertEqual((s["creatures"], s["removal"], s["removal_points"], s["flow"]), (6, 2, 3.0, 1))
        self.assertEqual(s["colors"], {"W": 5, "R": 3, "B": 1})
        self.assertEqual(s["top"], ["Big"])  # nur Matchwinner (Nutzer 13.11.2026), Must-Play und Filler nicht

    def test_empty(self):
        s = ld.deck_summary([], {}, "picks")
        self.assertEqual((s["cards"], s["spells"], s["avg_mv"]), (0, 0, 0))


class RowsTests(unittest.TestCase):
    def snap(self, **kw):
        info = dict(ld.deck_summary(DECK_CARDS, {"Big": "matchwinner"}, "arena"),
                    record={"wins": 2, "losses": 1, "matches": 3})
        base = {"status": "waiting", "pick": 43, "complete": True, "deckinfo": info, "set": "TST",
                "detect": {"main": "WR", "scores": []}, "archetypes": [{"colors": "WR", "name": "Boros"}],
                "deck": {"ready": True, "main": 27, "side": 3, "applied": True}, "game": {"active": False}}
        base.update(kw)
        return base

    def test_deck_view_instead_of_pick_43(self):
        rows = overlay.rows_for(self.snap())
        text = "\n".join(r[0] for r in rows)
        self.assertNotIn("Pick 43", text)
        self.assertNotIn("Warte auf das nächste Pack", text)
        self.assertIn("Boros", rows[0][0])
        self.assertIn("Bilanz 2–1", rows[0][0])
        self.assertIn("26 Karten · 17 Länder · 9 Zauber", text)
        self.assertIn("Ø Manawert 2,67", text)
        self.assertIn("Kurve ≤1:3 2:3 3:1 4:0 5:0 6+:2", text)
        self.assertIn("Kreaturen 6 · Removal 2 (3 P.) · Kartenfluss 1", text)
        self.assertIn("Farben W 5 · R 3 · B 1", text)
        self.assertIn("Bomben: Big", text)
        self.assertTrue(all(ord(ch) <= 0xFFFF for r in rows for ch in r[0]))

    def test_no_record_yet_and_picks_only(self):
        info = dict(ld.deck_summary(DECK_CARDS, {}, "picks"), record=None)
        rows = overlay.rows_for(self.snap(deckinfo=info))
        text = "\n".join(r[0] for r in rows)
        self.assertNotIn("Bilanz", text)
        self.assertNotIn("Bomben", text)
        self.assertIn("alle Picks", text)  # noch kein Deck in Arena abgegeben

    def test_game_and_hall_of_game_still_win(self):
        game = {"active": True, "turn": 3, "library": 30, "hand": 5, "groups": [], "cards": []}
        self.assertTrue(overlay.rows_for(self.snap(game=game))[0][0].startswith("Im Spiel"))
        rows = overlay.rows_for(self.snap(enemy_saved="x.txt"))
        self.assertIn("Hall of Game", rows[0][0])
        self.assertIn("Bilanz", rows[2][0])

    def test_during_the_draft_unchanged(self):
        rows = overlay.rows_for(self.snap(complete=False, pick=12, deckinfo=None))
        self.assertTrue(rows[0][0].startswith("Pick 12"))

    def test_mini(self):
        rows = overlay.mini_rows(self.snap())
        text = " ".join(r[0] for r in rows)
        self.assertNotIn("Pick", text)
        self.assertIn("Bilanz 2–1", text)
        self.assertIn("Kreaturen 6", text)
        self.assertIn("Removal 2", text)


class RecordTests(unittest.TestCase):
    def test_record_of_the_draft(self):
        with tempfile.TemporaryDirectory() as d:
            t = ds.Tracker(pathlib.Path(d) / "s.json", lambda g: (NAMES.get(g) or {}).get("name"))
            self.assertIsNone(t.record("d1", None))
            for line in [auth_line(), *DRAFT, DECK]:
                t.feed_line(line)
            self.assertEqual(t.record("d1", None), {"wins": 0, "losses": 0, "matches": 0})
            for line in [start_line("m1", event=EVENT), end_line("m1", [2, 2], 2),
                         start_line("m2", event=EVENT), end_line("m2", [1, 1], 1),
                         start_line("m3", event=EVENT)]:  # m3 laeuft noch
                t.feed_line(line)
            self.assertEqual(t.record("d1", None), {"wins": 1, "losses": 1, "matches": 3})
            self.assertEqual(t.record(None, EVENT), {"wins": 1, "losses": 1, "matches": 3})
            self.assertIsNone(t.record("anderer", None))


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        d = pathlib.Path(self.dir.name)
        self.log = d / "Player.log"
        self.live = ld.LiveDraft(self.log, d / "_livedraft.txt", names=NAMES,
                                 fetch=lambda n, refresh=False: CARDS, stats=d / "s.json")

    def tearDown(self):
        self.dir.cleanup()

    def write(self, *lines):
        with self.log.open("a", encoding="utf-8") as fh:
            fh.write("".join(line + "\n" for line in lines))
        self.live.step()

    def test_deckinfo_from_the_arena_deck(self):
        self.write(auth_line(), *DRAFT)
        self.assertIsNone(self.live.snapshot({}, {}, None).get("deckinfo"))  # Draft laeuft noch
        self.write(DECK, start_line("m1", event=EVENT), end_line("m1", [2, 2], 2))
        info = self.live.snapshot({"Test Bear": "matchwinner"}, {}, None)["deckinfo"]
        self.assertEqual(info["source"], "arena")
        self.assertEqual((info["cards"], info["lands"], info["spells"]), (19, 17, 2))
        self.assertEqual((info["creatures"], info["flow"]), (1, 1))
        self.assertEqual(info["colors"], {"W": 2})
        self.assertEqual(info["top"], ["Test Bear"])
        self.assertEqual(info["record"], {"wins": 1, "losses": 0, "matches": 1})

    def test_deckinfo_from_42_picks_without_deck(self):
        lines = []
        for i in range(ld.DRAFT_PICKS):
            lines += [ld_notify(i + 1), ld_pick()]
        self.write(*lines)
        info = self.live.snapshot({}, {}, None)["deckinfo"]
        self.assertEqual(info["source"], "picks")
        self.assertEqual(info["cards"], ld.DRAFT_PICKS)
        self.assertEqual(info["record"], {"wins": 0, "losses": 0, "matches": 0})  # noch kein Match


def ld_notify(n):
    from tests.test_livedraft import notify
    return notify(n, [101, 102])


def ld_pick():
    from tests.test_livedraft import pick
    return pick([101])


class HelpTests(unittest.TestCase):
    def test_help_and_readme(self):
        from components.howitworks import render_help_page
        self.assertIn("Deck-Übersicht", render_help_page())
        readme = (pathlib.Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
        self.assertIn("Deck-Übersicht", readme)


if __name__ == "__main__":
    unittest.main()
