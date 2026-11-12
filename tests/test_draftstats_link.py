"""Draft-Statistik: Drafts ohne Eventnamen (Pick Two, Drafts mit Menschen: nur Draft-Kennung) bekommen Event, Set,
Deck und Matches richtig zugeordnet; Neuaufbau aus den Protokollen."""
import pathlib
import tempfile
import unittest

from components import draftstats as ds
from tests.test_draftstats import (EVENT, auth_line, course_line, deck_line, end_line, lookup, notify, pick,
                                   start_line)

SETS = {101: "TRK", 102: "TRK", 103: "TRK", 104: "TRK", 105: "TRK"}


def draft(draft_id, cards):
    lines = []
    for i, c in enumerate(cards):
        lines += [notify(i + 1, cards[i:], draft=draft_id), pick([c], draft=draft_id)]
    return lines


D1 = draft("d1", [101, 102, 103])
D2 = draft("d2", [104, 105])
DECK1 = deck_line([(101, 1), (103, 1), (201, 15)], [(102, 1)])
DECK2 = deck_line([(104, 1), (105, 1), (202, 15)], [])


class LinkTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.dir.name) / "draftstatistik.json"
        self.t = ds.Tracker(self.path, lookup, SETS.get)

    def tearDown(self):
        self.dir.cleanup()

    def feed(self, *lines):
        for line in lines:
            self.t.feed_line(line)
        return ds.load_stats(self.path)["drafts"]

    def test_set_from_the_cards_while_drafting(self):
        d = self.feed(*D1)[0]
        self.assertEqual((d["event"], d["set"], d["draft_id"]), (None, "TRK", "d1"))

    def test_deck_and_matches_go_to_the_draft_without_event(self):
        old = [course_line([(102, 1)]), auth_line(), start_line("m0"), end_line("m0", [2], 2)]  # frueherer Lauf
        drafts = self.feed(*old, *D1, DECK1, start_line("m1"), end_line("m1", [2], 2))
        self.assertEqual(len(drafts), 2)
        d = drafts[1]
        self.assertEqual((d["event"], d["set"]), (EVENT, "TRK"))
        self.assertEqual(d["deck"]["main"], {"Test Bear": 1, "Test Spell": 1, "Plains": 15})
        self.assertEqual([m["id"] for m in d["matches"]], ["m1"])
        self.assertEqual([m["id"] for m in drafts[0]["matches"]], ["m0"])

    def test_two_drafts_of_the_same_event(self):
        drafts = self.feed(auth_line(), *D1, DECK1, start_line("m1"), end_line("m1", [2], 2),
                           *D2, course_line([(101, 1), (103, 1), (201, 15)]),  # altes Deck kommt waehrend D2 noch
                           course_line([]),  # leeres Deck (Event ohne Deck) zaehlt nicht
                           DECK2, start_line("m2"), end_line("m2", [1], 1))
        self.assertEqual(len(drafts), 2)
        one, two = drafts
        self.assertEqual([m["id"] for m in one["matches"]], ["m1"])
        self.assertEqual([m["id"] for m in two["matches"]], ["m2"])
        self.assertEqual(two["deck"]["main"], {"Test Gold": 1, "Test Big": 1, "Mountain": 15})
        self.assertEqual(one["deck"]["main"], {"Test Bear": 1, "Test Spell": 1, "Plains": 15})
        self.assertEqual(two["event"], EVENT)

    def test_old_deck_does_not_land_on_the_new_draft(self):
        drafts = self.feed(*D1, DECK1, *D2, course_line([(101, 1), (103, 1), (201, 15)]))
        self.assertIsNone(drafts[1]["deck"])  # D2 hat noch kein eigenes Deck
        self.assertIsNone(drafts[1]["event"])

    def test_card_numbers_count_drafts_without_event(self):
        self.feed(*D1)
        st = ds.card_stats(ds.load_stats(self.path), "TRK")
        self.assertEqual(st["Test Bear"]["drafted"], 1)


class PickNumberTests(unittest.TestCase):
    def test_pick_two_counts_picks_not_cards(self):
        data = {"drafts": [{"set": "TRK", "picks": ["A", "B", "C", "D", "E", "F"],
                            "pick_sizes": [14, 14, 12, 12, 10, 10], "deck": None, "matches": []}]}
        st = ds.card_stats(data, "TRK")
        self.assertEqual([st[n]["avg_pick"] for n in "ABCDEF"], [1, 1, 2, 2, 3, 3])

    def test_normal_draft(self):
        data = {"drafts": [{"set": "TRK", "picks": ["A", "B", "C"], "pick_sizes": [14, 13, 12], "deck": None,
                            "matches": []}]}
        self.assertEqual(ds.card_stats(data, "TRK")["C"]["avg_pick"], 3)


class ReportOrderTests(unittest.TestCase):
    def test_newest_draft_first_on_the_same_day(self):
        from components import setreport
        rec = {"set": "TRK", "started": "2026-11-12", "picks": [], "deck": None, "matches": []}
        data = {"drafts": [dict(rec, event="FirstDraft_TRK_1"), dict(rec, event="SecondDraft_TRK_1")]}
        html = setreport.render_set_report(data, "TRK", {}, {}, {})
        self.assertLess(html.index("Second Draft"), html.index("First Draft"))


class RebuildTests(unittest.TestCase):
    def test_rebuild_from_logs_keeps_a_backup(self):
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            prev, cur, path = d / "Player-prev.log", d / "Player.log", d / "draftstatistik.json"
            prev.write_text("\n".join([auth_line(), *D1, DECK1, start_line("m1"), end_line("m1", [2], 2)]) + "\n",
                            encoding="utf-8")
            cur.write_text("\n".join([auth_line(), *D2, DECK2, start_line("m2"), end_line("m2", [1], 1)]) + "\n",
                           encoding="utf-8")
            path.write_text('{"version": 1, "drafts": [{"event": null, "set": "", "picks": ["kaputt"]}]}',
                            encoding="utf-8")
            backup = ds.rebuild(path, [prev, cur, d / "fehlt.log"], lookup, SETS.get)
            self.assertTrue(backup.exists())
            self.assertIn("kaputt", backup.read_text(encoding="utf-8"))
            drafts = ds.load_stats(path)["drafts"]
            self.assertEqual([len(x["matches"]) for x in drafts], [1, 1])
            self.assertEqual([x["set"] for x in drafts], ["TRK", "TRK"])


class CliTests(unittest.TestCase):
    def test_option(self):
        from components.cli import parse_args
        self.assertTrue(parse_args(["--statistik-neu"]).statistik_neu)
        readme = (pathlib.Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
        self.assertIn("--statistik-neu", readme)
        from components.howitworks import render_help_page
        self.assertIn("--statistik-neu", render_help_page())


if __name__ == "__main__":
    unittest.main()
