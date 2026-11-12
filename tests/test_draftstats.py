"""Draft-Statistik: Decks und Matches aus dem Arena-Protokoll, Sammeln je Draft (draftstatistik.json), Zahlen je
Karte und Archetyp, Anzeige in Drafthelper, Seitenfenster und Bericht, Setauswertung als HTML."""
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from components import arenalog as al
from components import draftstats as ds
from components import overlay
from components import setreport
from components.cli import parse_args

ME, OTHER = "MEUSERID00000000000000000", "OTHERUSER0000000000000000"
NAMES = {101: "Test Bear", 102: "Test Hasty", 103: "Test Spell", 104: "Test Gold", 105: "Test Big",
         201: "Plains", 202: "Mountain"}
EVENT = "PickTwoDraft_TRK_20261110"


def lookup(grp):
    return NAMES.get(grp)


def deck_line(main, side=(), event=EVENT, key="Deck"):
    deck = {"MainDeck": [{"cardId": g, "quantity": q} for g, q in main],
            "Sideboard": [{"cardId": g, "quantity": q} for g, q in side]}
    return "[UnityCrossThreadLogger]==> EventSetDeckV3 " + json.dumps(
        {"id": "x", "request": json.dumps({"EventName": event, key: deck})})


def course_line(main, event=EVENT):
    return json.dumps({"CourseId": "c", "InternalEventName": event, "CurrentModule": "CreateMatch",
                       "CourseDeck": {"MainDeck": [{"cardId": g, "quantity": q} for g, q in main], "Sideboard": []}})


def auth_line(user=ME):
    return json.dumps({"transactionId": "t", "authenticateResponse": {"clientId": user, "sessionId": "s"}})


def start_line(match, my_team=2, event=EVENT):
    players = [{"userId": OTHER, "playerName": "a", "systemSeatId": 3 - my_team, "teamId": 3 - my_team,
                "eventId": event},
               {"userId": ME, "playerName": "b", "systemSeatId": my_team, "teamId": my_team, "eventId": event}]
    return json.dumps({"transactionId": "t", "matchGameRoomStateChangedEvent": {"gameRoomInfo": {
        "gameRoomConfig": {"reservedPlayers": players, "matchId": match},
        "stateType": "MatchGameRoomStateType_Playing"}}})


def end_line(match, games, winner):
    results = [{"scope": "MatchScope_Game", "result": "ResultType_WinLoss", "winningTeamId": g,
                "reason": "ResultReason_Game"} for g in games]
    results.append({"scope": "MatchScope_Match", "result": "ResultType_WinLoss", "winningTeamId": winner,
                    "reason": "ResultReason_Game"})
    return json.dumps({"transactionId": "t", "matchGameRoomStateChangedEvent": {"gameRoomInfo": {
        "gameRoomConfig": {"matchId": match}, "stateType": "MatchGameRoomStateType_MatchCompleted",
        "finalMatchResult": {"matchId": match, "matchCompletedReason": "MatchCompletedReasonType_Success",
                             "resultList": results}}}})


def notify(n, cards, draft="d1"):
    return ('[UnityCrossThreadLogger]Draft.Notify {"draftId":"%s","SelfPick":%d,"SelfPack":1,"PackCards":"%s"}'
            % (draft, n, ",".join(map(str, cards))))


def bot_pack(cards, picked, event=EVENT):
    return json.dumps({"CurrentModule": "BotDraft", "Payload": json.dumps(
        {"EventName": event, "DraftPack": [str(c) for c in cards], "PickedCards": [str(c) for c in picked]})})


def bot_pick(cards, event=EVENT):
    return "[UnityCrossThreadLogger]==> BotDraft_DraftPick " + json.dumps({"id": "x", "request": json.dumps(
        {"EventName": event, "PickInfo": {"EventName": event, "CardIds": [str(c) for c in cards],
                                          "PackNumber": 0, "PickNumber": 0}})})


def pick(cards, draft="d1"):
    return "[UnityCrossThreadLogger]==> Event_PlayerDraftMakePick " + json.dumps(
        {"id": "x", "request": json.dumps({"DraftId": draft, "GrpIds": cards, "Pack": 1, "Pick": 1})})


DRAFT = [bot_pack([101, 102, 103, 104], []), bot_pick([101, 102]), bot_pack([103, 105], [101, 102]),
         bot_pick([103, 105])]


class ScanTests(unittest.TestCase):
    def test_own_user(self):
        self.assertEqual(al.scan_match_line(auth_line()), [{"kind": "user", "id": ME}])
        self.assertEqual(al.scan_match_line(f"[UnityCrossThreadLogger]12.11.2026 15:53:49: Match to {ME}: "
                                            "AuthenticateResponse"), [{"kind": "user", "id": ME}])

    def test_submitted_and_course_deck(self):
        ev = al.scan_match_line(deck_line([(101, 1), (201, 9)], [(104, 1)]))
        self.assertEqual(ev, [{"kind": "deck", "event": EVENT, "main": {101: 1, 201: 9}, "side": {104: 1}}])
        ev = al.scan_match_line(course_line([(102, 2)]))
        self.assertEqual(ev[0]["main"], {102: 2})
        self.assertEqual(ev[0]["event"], EVENT)

    def test_match_start_and_end(self):
        ev = al.scan_match_line(start_line("m1"))
        self.assertEqual(ev, [{"kind": "match_start", "match": "m1", "event": EVENT,
                               "players": [{"user": OTHER, "team": 1}, {"user": ME, "team": 2}]}])
        ev = al.scan_match_line(end_line("m1", [2, 1, 2], 2))
        self.assertEqual(ev, [{"kind": "match_end", "match": "m1", "games": [2, 1, 2], "winner": 2}])

    def test_other_lines(self):
        for line in ["", "nichts", notify(1, [101]), '{"MainDeck": "kaputt"}',
                     '{"Deck":{"MainDeck":[{"cardId":5,"quantity":2}]}}']:  # Deck ohne Event zaehlt nicht
            self.assertEqual(al.scan_match_line(line), [], line)

    def test_limited_events(self):
        self.assertTrue(ds.is_limited("PickTwoDraft_TRK_20261110"))
        self.assertTrue(ds.is_limited("QuickDraft_FRA_20261001"))
        self.assertTrue(ds.is_limited("Sealed_TRK_20261113"))
        self.assertFalse(ds.is_limited("Play"))
        self.assertFalse(ds.is_limited("ColorChallenge_Node5_W"))
        self.assertFalse(ds.is_limited(None))


class TrackerTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.dir.name) / "draftstatistik.json"
        self.t = ds.Tracker(self.path, lookup)

    def tearDown(self):
        self.dir.cleanup()

    def feed(self, *lines, tracker=None):
        changed = False
        for line in lines:
            changed = (tracker or self.t).feed_line(line) or changed
        return changed


FULL = DRAFT + [deck_line([(101, 1), (103, 1), (201, 9)], [(102, 1), (105, 1)]), auth_line(),
                start_line("m1", my_team=2), end_line("m1", [2], 2),
                start_line("m2", my_team=1), end_line("m2", [2, 1, 2], 2)]


class TrackerTests(TrackerTestCase):
    def test_full_draft(self):
        self.assertTrue(self.feed(*FULL))
        data = ds.load_stats(self.path)
        self.assertEqual(len(data["drafts"]), 1)
        d = data["drafts"][0]
        self.assertEqual((d["event"], d["set"]), (EVENT, "TRK"))
        self.assertEqual(d["picks"], ["Test Bear", "Test Hasty", "Test Spell", "Test Big"])
        self.assertEqual(d["pick_sizes"], [4, 4, 2, 2])
        self.assertEqual(d["deck"], {"main": {"Test Bear": 1, "Test Spell": 1, "Plains": 9},
                                     "side": {"Test Hasty": 1, "Test Big": 1}})
        self.assertEqual([(m["id"], m["games"], m["win"]) for m in d["matches"]],
                         [("m1", [True], True), ("m2", [False, True, False], False)])
        self.assertEqual(d["matches"][0]["deck"], {"Test Bear": 1, "Test Spell": 1, "Plains": 9})

    def test_feeding_the_same_log_again_changes_nothing(self):
        self.feed(*FULL)
        before = self.path.read_text(encoding="utf-8")
        again = ds.Tracker(self.path, lookup)  # draftgott neu gestartet, Protokoll von vorn
        self.assertFalse(self.feed(*FULL, tracker=again))
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)

    def test_second_draft_of_the_same_event(self):
        self.feed(*FULL)
        self.feed(bot_pack([104, 105], []), bot_pick([104, 105]))
        data = ds.load_stats(self.path)
        self.assertEqual(len(data["drafts"]), 2)
        self.assertEqual(data["drafts"][1]["picks"], ["Test Gold", "Test Big"])
        self.assertEqual(data["drafts"][0]["picks"], ["Test Bear", "Test Hasty", "Test Spell", "Test Big"])

    def test_match_without_tracked_draft(self):
        self.feed(course_line([(102, 1)]), auth_line(), start_line("m9"), end_line("m9", [2], 2))
        d = ds.load_stats(self.path)["drafts"][0]
        self.assertEqual(d["picks"], [])
        self.assertEqual(d["matches"][0]["deck"], {"Test Hasty": 1})
        self.assertTrue(d["matches"][0]["win"])

    def test_constructed_and_unknown_user_are_ignored(self):
        self.feed(auth_line(), start_line("p1", event="Play"), end_line("p1", [2], 2))
        self.assertEqual(ds.load_stats(self.path)["drafts"], [])
        t = ds.Tracker(pathlib.Path(self.dir.name) / "b.json", lookup)
        self.feed(*DRAFT, start_line("m1"), end_line("m1", [2], 2), tracker=t)  # eigene Kennung unbekannt
        self.assertEqual(ds.load_stats(pathlib.Path(self.dir.name) / "b.json")["drafts"][0]["matches"], [])

    def test_match_without_own_player(self):
        line = start_line("m5").replace(ME, "SOMEONEELSE00000000000000")  # eigene Kennung nicht im Match
        self.feed(*DRAFT, auth_line(), line, end_line("m5", [2], 2))
        self.assertEqual(ds.load_stats(self.path)["drafts"][0]["matches"], [])

    def test_deck_change_between_matches(self):
        self.feed(*DRAFT, deck_line([(101, 1)]), auth_line(), start_line("m1"), end_line("m1", [2], 2),
                  deck_line([(105, 1)]), start_line("m2"), end_line("m2", [1], 1))
        d = ds.load_stats(self.path)["drafts"][0]
        self.assertEqual([m["deck"] for m in d["matches"]], [{"Test Bear": 1}, {"Test Big": 1}])
        self.assertEqual(d["deck"]["main"], {"Test Big": 1})

    def test_human_draft_with_draft_id(self):
        self.feed(notify(1, [101, 102]), pick([101]), notify(2, [103]), pick([103]))
        self.assertEqual(ds.load_stats(self.path)["drafts"][0]["picks"], ["Test Bear", "Test Spell"])
        self.assertEqual(ds.load_stats(self.path)["drafts"][0]["draft_id"], "d1")

    def test_broken_or_missing_file(self):
        self.assertEqual(ds.load_stats(self.path), {"version": 1, "drafts": []})
        self.path.write_text("kaputt", encoding="utf-8")
        self.assertEqual(ds.load_stats(self.path), {"version": 1, "drafts": []})

    def test_not_in_git(self):
        ignore = (pathlib.Path(__file__).resolve().parent.parent / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("draftstatistik*.json", ignore)


def sample_data():
    return {"version": 1, "drafts": [
        {"event": EVENT, "set": "TRK", "started": "2026-11-12", "picks": ["A", "B", "C", "A"],
         "pick_sizes": [14, 13, 12, 11],
         "deck": {"main": {"A": 2, "C": 1, "Plains": 8}, "side": {"B": 1}},
         "matches": [{"id": "1", "deck": {"A": 2, "C": 1, "Plains": 8}, "games": [True], "win": True},
                     {"id": "2", "deck": {"A": 2, "Plains": 8}, "games": [False, True, False], "win": False}]},
        {"event": "QuickDraft_FRA_1", "set": "FRA", "started": "2026-10-01", "picks": ["Z"], "pick_sizes": [14],
         "deck": None, "matches": []}]}


class AggregateTests(unittest.TestCase):
    def test_card_numbers(self):
        st = ds.card_stats(sample_data(), "trk")
        a = st["A"]
        self.assertEqual((a["drafted"], a["drafts"], a["decks"]), (2, 1, 1))
        self.assertEqual((a["games"], a["wins"], a["matches"], a["match_wins"]), (4, 2, 2, 1))
        self.assertEqual(a["avg_pick"], 2.5)  # Pick 1 (14 Karten) und Pick 4 (11 Karten)
        self.assertEqual((st["C"]["games"], st["C"]["wins"]), (1, 1))  # nur im ersten Match im Deck
        self.assertEqual((st["B"]["decks"], st["B"]["games"]), (0, 0))
        self.assertNotIn("Plains", st)
        self.assertNotIn("Z", st)  # anderes Set
        self.assertIn("Z", ds.card_stats(sample_data()))

    def test_summary(self):
        s = ds.summary(sample_data(), "TRK")
        self.assertEqual((s["drafts"], s["matches"], s["match_wins"], s["games"], s["wins"]), (1, 2, 1, 4, 2))
        self.assertEqual(ds.sets_in(sample_data()), ["TRK", "FRA"])

    def test_win_rate_text(self):
        self.assertEqual(ds.rate_text({"games": 0, "wins": 0}), "")
        self.assertEqual(ds.rate_text({"games": 4, "wins": 3}), "75 % in 4 Games")


class DisplayTests(unittest.TestCase):
    """Zahlen je Karte im Drafthelper (Pool, Live-Pack, Set-Ansicht) und im Bericht."""

    def setUp(self):
        import threading
        from components import drafthelper as dh
        from components import livedraft as ld
        from tests.fixtures import CARDS, args_for
        from tests.test_drafthelper import load
        self.dir = tempfile.TemporaryDirectory()
        d = pathlib.Path(self.dir.name)
        self.stats = d / "draftstatistik.json"
        self.stats.write_text(json.dumps({"version": 1, "drafts": [
            {"event": EVENT, "set": "TST", "started": "2026-11-12", "picks": ["Test Bear", "Test Hasty"],
             "pick_sizes": [3, 2], "deck": {"main": {"Test Bear": 1}, "side": {}},
             "matches": [{"id": "1", "deck": {"Test Bear": 1}, "games": [True, False, True], "win": True}]}]}),
            encoding="utf-8")
        self.log = d / "Player.log"
        self.log.write_text(notify(1, [101, 102]) + "\n", encoding="utf-8")
        names = {101: {"name": "Test Bear", "set": "TST", "number": "10"},
                 102: {"name": "Test Hasty", "set": "TST", "number": "11"}}
        live = ld.LiveDraft(self.log, d / "pool.txt", names=names, fetch=lambda n, refresh=False: CARDS)
        live.step()
        cards, basics, sig = load()
        self.app = {"pool": cards, "basics": basics, "signature": sig, "args": args_for(["--drafthelper"]),
                    "simulate": None, "save": None, "job": dh.Job(), "options": [1000], "file": "pool.txt",
                    "live": live, "stats": self.stats, "reload_pool": lambda: (cards, basics, sig),
                    "fetch_set": lambda code: [dict(CARDS["Test Bear"], set=code, collector_number="10")]}
        self.server = dh.LocalServer(("127.0.0.1", 0), dh.make_handler(self.app))
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.dir.cleanup()

    def get(self, path):
        import urllib.request
        with urllib.request.urlopen(self.base + path, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))

    def test_pool_live_and_set_view(self):
        self.assertEqual(self.get("/api/pool")["cardstats"]["Test Bear"]["games"], 3)
        bear = next(c for c in self.get("/api/live")["pack"] if c["name"] == "Test Bear")
        self.assertEqual((bear["stats"]["wins"], bear["stats"]["drafted"]), (2, 1))
        self.assertEqual(self.get("/api/setcards?set=tst")["cardstats"]["Test Bear"]["decks"], 1)

    def test_report_panel(self):
        from components.report_cards import render_stats_panel
        from tests.test_archetypes import _deck
        ctx = _deck({"White Bear": 8, "Plains": 9}, "trk")
        self.assertEqual(render_stats_panel(ctx), "")
        ctx["cardstats"] = {"White Bear": {"drafted": 3, "drafts": 2, "decks": 2, "games": 5, "wins": 4,
                                           "matches": 3, "match_wins": 2, "avg_pick": 2.0}}
        html = render_stats_panel(ctx)
        self.assertIn("Draft-Statistik", html)
        self.assertIn("White Bear", html)
        self.assertIn("80 %", html)

    def test_entries_carry_the_stats(self):
        from components import drafthelper as dh
        pool = [{"name": "A", "qty": 1}]
        e = dh.variant_entries(pool, [["core"]], {}, {}, cardstats={"A": {"games": 1}, "Z": {"games": 2}})
        self.assertEqual(e[0]["cardstats"], {"A": {"games": 1}})


class TextTests(unittest.TestCase):
    def test_help_and_readme(self):
        from components.howitworks import render_help_page
        page = render_help_page()
        self.assertIn("draftstatistik.json", page)
        self.assertIn("Setauswertung", page)
        readme = (pathlib.Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
        self.assertIn("--setauswertung", readme)
        self.assertIn("draftstatistik.json", readme)


class OverlayTests(unittest.TestCase):
    def test_row_shows_win_rate(self):
        snap = {"status": "pack", "pick": 1, "detect": {"main": None, "scores": []},
                "pack": [{"name": "A", "level": "", "rating": "", "colors": ["W"], "arch": [], "points": 1.5,
                          "stats": {"games": 4, "wins": 3, "drafted": 2}}]}
        self.assertIn("75 %", overlay.rows_for(snap)[-1][0])


class SetReportTests(unittest.TestCase):
    def test_report_sections(self):
        cards = {"A": {"name": "A", "colors": ["W"], "mana_cost": "{W}", "rarity": "common", "type_line": "Creature"},
                 "C": {"name": "C", "colors": ["U"], "mana_cost": "{U}", "rarity": "rare", "type_line": "Instant"}}
        html = setreport.render_set_report(sample_data(), "TRK", cards, {"A": ["WU"]}, {"A": "mustplay"})
        for text in ("Setauswertung TRK", "Überblick", "Archetypen", "Karten", "Bewertung", "Drafts",
                     "1 Draft", "1-1", "Spacecraft"):
            self.assertIn(text, html)
        self.assertIn("<td class=\"l\">A</td>", html.replace("<b>", "").replace("</b>", ""))
        self.assertIn("50 %", html)

    def test_few_games_are_grey(self):
        data = sample_data()
        many = [{"id": str(i), "deck": {"A": 1}, "games": [i % 2 == 0], "win": i % 2 == 0} for i in range(20)]
        data["drafts"][0]["matches"] = many
        html = setreport.render_set_report(data, "TRK", {}, {}, {})
        row = next(r for r in html.split("<tr>") if '<td class="l">A</td>' in r)
        self.assertNotIn('class="few"', row)  # 20 Games
        data["drafts"][0]["matches"] = many[:19]
        html = setreport.render_set_report(data, "TRK", {}, {}, {})
        row = next(r for r in html.split("<tr>") if '<td class="l">A</td>' in r)
        self.assertIn('class="few"', row)

    def test_empty_set(self):
        html = setreport.render_set_report({"version": 1, "drafts": []}, "TRK", {}, {}, {})
        self.assertIn("Noch keine Drafts", html)

    def test_output_file_name(self):
        self.assertEqual(setreport.output_name("TRK"), "setauswertung_trk.html")

    def test_cli_and_batch(self):
        a = parse_args(["--setauswertung"])
        self.assertEqual(a.setauswertung, "")
        self.assertEqual(a.statistik, "draftstatistik.json")
        self.assertEqual(parse_args(["--setauswertung", "TRK"]).setauswertung, "TRK")
        bat = (pathlib.Path(__file__).resolve().parent.parent / "draftgott.bat").read_text(encoding="utf-8")
        self.assertIn("--setauswertung", bat)
        self.assertIn("4 = Setauswertung", bat)

    def test_run_writes_the_file(self):
        with tempfile.TemporaryDirectory() as d:
            stats = pathlib.Path(d) / "s.json"
            stats.write_text(json.dumps(sample_data()), encoding="utf-8")
            args = parse_args(["--setauswertung", "--statistik", str(stats), "--nicht-oeffnen"])
            with mock.patch.object(setreport, "fetch_cards_cached", lambda names, refresh=False: {}), \
                    mock.patch.object(setreport, "OUT_DIR", pathlib.Path(d)):
                out = setreport.run(args)
            self.assertEqual(out.name, "setauswertung_trk.html")  # haeufigstes Set
            self.assertIn("Setauswertung TRK", out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
