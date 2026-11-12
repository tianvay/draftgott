"""Live-Draft: Arena-Protokoll mitlesen, Picks in die Pool-Datei schreiben, Pack bewerten; Server-Schnittstellen
des Drafthelpers dafuer (Live-Stand, Archetyp-Zuordnung, Set-Karten) und die Zeilen des Seitenfensters."""
import json
import pathlib
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock

from components import archetypes as arch
from components import drafthelper as dh
from components import livedraft as ld
from components import overlay
from components.cli import parse_args
from tests.fixtures import CARDS, args_for
from tests.test_drafthelper import load

NAMES = {101: {"name": "Test Bear", "set": "TST", "number": "10"},
         102: {"name": "Test Hasty", "set": "TST", "number": "11"},
         103: {"name": "Test Spell", "set": "TST", "number": "15"},
         201: {"name": "Test Gold", "set": "TST", "number": "14"},
         202: {"name": "Test Big", "set": "TST", "number": "13"}}
TST = {"tst": [{"colors": "WB", "name": "Testgilde", "tips": ["Tipp"]},
               {"colors": "RW", "name": "Rotweiss", "tips": ["Tipp"]}]}


def notify(n, cards, draft="d1"):
    return ('[UnityCrossThreadLogger]Draft.Notify {"draftId":"%s","SelfPick":%d,"SelfPack":1,"PackCards":"%s"}'
            % (draft, n, ",".join(map(str, cards))))


def pick(cards, draft="d1"):
    return "[UnityCrossThreadLogger]==> Event_PlayerDraftMakePick " + json.dumps(
        {"id": "x", "request": json.dumps({"DraftId": draft, "GrpIds": cards, "Pack": 1, "Pick": 1})})


def fake_fetch(names, refresh=False):
    return CARDS


class LiveTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.log = pathlib.Path(self.dir.name) / "Player.log"
        self.pool = pathlib.Path(self.dir.name) / "_livedraft.txt"
        self.live = ld.LiveDraft(self.log, self.pool, names=NAMES, fetch=fake_fetch)

    def tearDown(self):
        self.dir.cleanup()

    def write(self, *lines):
        with self.log.open("a", encoding="utf-8") as fh:
            fh.write("".join(line + "\n" for line in lines))


class LiveDraftTests(LiveTestCase):
    def test_without_log(self):
        self.assertFalse(self.live.step())
        snap = self.live.snapshot({}, {}, None)
        self.assertEqual(snap["status"], "nolog")
        self.assertIn("Player.log", snap["message"])

    def test_log_without_draft(self):
        self.write("[UnityCrossThreadLogger]Client.SceneChange {}")
        self.live.step()
        self.assertEqual(self.live.snapshot({}, {}, None)["status"], "idle")

    def test_pack_is_shown_with_card_data(self):
        self.write(notify(1, [101, 102, 103]))
        self.assertTrue(self.live.step())
        snap = self.live.snapshot({}, {}, None)
        self.assertEqual(snap["status"], "pack")
        self.assertEqual(snap["pick"], 1)
        self.assertEqual({c["name"] for c in snap["pack"]}, {"Test Bear", "Test Hasty", "Test Spell"})
        bear = next(c for c in snap["pack"] if c["name"] == "Test Bear")
        self.assertEqual((bear["colors"], bear["set"], bear["number"]), (["W"], "TST", "10"))
        self.assertIn("level", bear)

    def test_picks_go_into_the_pool_file(self):
        self.write(notify(1, [101, 102, 103]), pick([101]))
        self.live.step()
        self.assertEqual(self.pool.read_text(encoding="utf-8"), "Deck\n1 Test Bear (TST) 10\n")
        version = self.live.version
        self.write(notify(2, [201, 202]), pick([202]), notify(3, [101]), pick([101]))
        self.live.step()
        self.assertEqual(self.pool.read_text(encoding="utf-8"),
                         "Deck\n2 Test Bear (TST) 10\n1 Test Big (TST) 13\n")
        self.assertGreater(self.live.version, version)
        snap = self.live.snapshot({}, {}, None)
        self.assertEqual(snap["status"], "waiting")
        self.assertEqual(snap["picks"], ["Test Bear", "Test Big", "Test Bear"])
        self.assertEqual(snap["pick"], 4)

    def test_pool_file_untouched_without_draft(self):
        self.pool.write_text("Deck\n1 Alte Karte\n", encoding="utf-8")
        self.write("nichts")
        self.live.step()
        self.assertEqual(self.pool.read_text(encoding="utf-8"), "Deck\n1 Alte Karte\n")

    def test_ranking_and_archetype_from_picks(self):
        self.write(notify(1, [201]), pick([201]), notify(2, [202]), pick([202]), notify(3, [101, 102, 103]))
        self.live.step()
        with mock.patch.dict(arch.ARCHETYPES, TST):
            snap = self.live.snapshot({"Test Hasty": "mustplay"}, {"Test Gold": ["WB"], "Test Spell": ["WB"]}, None)
        self.assertEqual(snap["set"], "TST")
        self.assertEqual(snap["detect"]["main"], "WB")  # Gold (W+B, zugeordnet) und Big (W): WB 2 + 1 = 3, RW 1
        self.assertEqual(snap["pack"][0]["name"], "Test Spell")  # Archetyp-Karte vorn
        self.assertEqual(snap["pack"][0]["level"], "arch")
        self.assertEqual([a["colors"] for a in snap["archetypes"]], ["WB", "RW"])

    def test_manual_archetype(self):
        self.write(notify(1, [101, 102]))
        self.live.step()
        with mock.patch.dict(arch.ARCHETYPES, TST):
            snap = self.live.snapshot({}, {}, "RW")
        self.assertEqual(snap["detect"]["main"], "RW")
        self.assertEqual(next(c for c in snap["pack"] if c["name"] == "Test Hasty")["level"], "color")

    def test_unknown_cards_are_listed(self):
        self.write(notify(1, [101, 999]))
        self.live.step()
        snap = self.live.snapshot({}, {}, None)
        self.assertEqual(snap["unknown"], [999])
        self.assertEqual(len(snap["pack"]), 1)

    def test_known_names(self):
        self.write(notify(1, [101, 102]), pick([101]))
        self.live.step()
        self.assertEqual(self.live.known_names(), {"Test Bear", "Test Hasty"})

    def test_scryfall_failure_keeps_names(self):
        def broken(names, refresh=False):
            raise urllib.error.URLError("offline")
        live = ld.LiveDraft(self.log, self.pool, names=NAMES, fetch=broken)
        self.write(notify(1, [101]))
        live.step()
        self.assertEqual(live.snapshot({}, {}, None)["pack"][0]["name"], "Test Bear")


class ServerTests(LiveTestCase):
    def setUp(self):
        super().setUp()
        cards, basics, sig = load()
        self.assign = pathlib.Path(self.dir.name) / "kartenarchetypen.json"
        self.ratings = pathlib.Path(self.dir.name) / "kartenbewertung.json"
        self.app = {"pool": cards, "basics": basics, "signature": sig, "args": args_for(["--drafthelper"]),
                    "simulate": None, "save": None, "job": dh.Job(), "options": [1000], "file": "pool.txt",
                    "ratings": self.ratings, "cardarch": self.assign, "live": self.live,
                    "reload_pool": lambda: load("Deck\n1 Test Bear (TST) 10\n"),
                    "fetch_set": lambda code: [dict(CARDS["Test Defender"], set=code, collector_number="12")]}
        self.server = dh.LocalServer(("127.0.0.1", 0), dh.make_handler(self.app))
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    def test_live_state(self):
        self.write(notify(1, [101, 102]))
        self.live.step()
        snap = self.get("/api/live")
        self.assertEqual(snap["status"], "pack")
        self.assertEqual(len(snap["pack"]), 2)

    def test_live_state_without_live_mode(self):
        self.app["live"] = None
        self.assertEqual(self.get("/api/live")["status"], "off")

    def test_manual_archetype_is_kept(self):
        self.write(notify(1, [101, 102]))
        self.live.step()
        with mock.patch.dict(arch.ARCHETYPES, TST):
            self.assertEqual(self.post("/api/live/archetype", {"arch": "RW"})[0], 200)
            self.assertEqual(self.get("/api/live")["detect"]["main"], "RW")
            self.assertTrue(self.get("/api/live")["detect"]["manual"])
            self.assertEqual(self.post("/api/live/archetype", {"arch": "XY"})[0], 400)
            self.post("/api/live/archetype", {"arch": ""})
            self.assertFalse(self.get("/api/live")["detect"]["manual"])

    def test_card_archetype_for_pool_and_live_cards(self):
        status, data = self.post("/api/cardarch", {"name": "Test Bear", "arch": ["WB"]})
        self.assertEqual(status, 200)
        self.assertEqual(data["cardarch"], {"Test Bear": ["WB"]})
        self.assertEqual(json.loads(self.assign.read_text(encoding="utf-8")), {"Test Bear": ["WB"]})
        self.app["pool"] = [c for c in self.app["pool"] if c["name"] != "Test Hasty"]  # nur im Live-Pack
        self.assertEqual(self.post("/api/cardarch", {"name": "Test Hasty", "arch": ["RW"]})[0], 400)
        self.write(notify(1, [102]))
        self.live.step()
        self.assertEqual(self.post("/api/cardarch", {"name": "Test Hasty", "arch": ["RW"]})[0], 200)
        self.assertEqual(self.post("/api/cardarch", {"name": "Unbekannt", "arch": ["RW"]})[0], 400)
        self.assertEqual(self.post("/api/cardarch", {"name": "Test Bear", "arch": ["QQ"]})[0], 400)
        self.assertEqual(self.get("/api/live")["cardarch"]["Test Hasty"], ["RW"])

    def test_rating_for_live_cards(self):
        self.app["pool"] = [c for c in self.app["pool"] if c["name"] != "Test Hasty"]  # nur im Live-Pack
        self.assertEqual(self.post("/api/rating", {"name": "Test Hasty", "cat": "mustplay"})[0], 400)
        self.write(notify(1, [102]))
        self.live.step()
        status, _ = self.post("/api/rating", {"name": "Test Hasty", "cat": "mustplay"})
        self.assertEqual(status, 200)
        self.assertEqual(self.get("/api/live")["pack"][0]["rating"], "mustplay")

    def test_pool_api_has_assignments_and_archetypes_of_all_sets(self):
        self.post("/api/cardarch", {"name": "Test Bear", "arch": ["WB"]})
        data = self.get("/api/pool")
        self.assertEqual(data["cardarch"], {"Test Bear": ["WB"]})
        self.assertIn("trk", data["archsets"])
        self.assertTrue(data["live"])

    def test_pool_is_reloaded_after_a_pick(self):
        self.assertEqual(len(self.get("/api/pool")["cards"]), len(self.app["pool"]))
        self.write(notify(1, [101]), pick([101]))
        self.live.step()
        data = self.get("/api/pool")
        self.assertEqual([c["name"] for c in data["cards"]], ["Test Bear"])
        self.assertEqual(data["pool_version"], self.live.version)

    def test_set_cards(self):
        data = self.get("/api/setcards?set=tst")
        self.assertEqual(data["set"], "TST")
        self.assertEqual(data["cards"][0]["name"], "Test Defender")
        self.assertEqual(data["cards"][0]["colors"], ["W"])
        self.assertEqual(self.post("/api/cardarch", {"name": "Test Defender", "arch": ["WB"]})[0], 200)

    def test_archetype_detection_of_the_pool(self):
        marks = [["core"] * c["qty"] for c in self.app["pool"]]
        with mock.patch.dict(arch.ARCHETYPES, TST):
            self.post("/api/cardarch", {"name": "Test Gold", "arch": ["WB"]})
            self.post("/api/cardarch", {"name": "Test Bear", "arch": ["WB"]})  # sonst WB und RW gleichauf
            status, data = self.post("/api/archdetect", {"marks": marks, "basics": {}, "cats": {}})
        self.assertEqual(status, 200)
        self.assertEqual(data["detect"]["main"], "WB")
        by = {s["colors"]: s for s in data["detect"]["scores"]}
        self.assertEqual(by["WB"]["assigned"], 4)  # Gold + 3 Bear

    def test_page_has_live_panel_and_set_view(self):
        with urllib.request.urlopen(self.base + "/", timeout=10) as r:
            page = r.read().decode("utf-8")
        self.assertIn('id="live"', page)
        self.assertIn('id="setview"', page)


class CliTests(unittest.TestCase):
    def test_live_options(self):
        a = parse_args(["--drafthelper", "_livedraft.txt", "--live"])
        self.assertTrue(a.live)
        self.assertFalse(a.kein_overlay)
        self.assertIsNone(a.arena_log)
        self.assertEqual(a.archetypen, "kartenarchetypen.json")
        a = parse_args(["--drafthelper", "--live", "--kein-overlay", "--arena-log", "x.log", "--archetypen", "a.json"])
        self.assertEqual((a.kein_overlay, a.arena_log, a.archetypen), (True, "x.log", "a.json"))

    def test_overlay_alone(self):
        self.assertEqual(parse_args(["--overlay", "http://127.0.0.1:8765/"]).overlay, "http://127.0.0.1:8765/")

    def test_batch_has_live_menu(self):
        bat = (pathlib.Path(__file__).resolve().parent.parent / "draftgott.bat").read_text(encoding="utf-8")
        self.assertIn("--live", bat)
        self.assertIn("_livedraft.txt", bat)

    def test_live_pool_not_in_git(self):
        ignore = (pathlib.Path(__file__).resolve().parent.parent / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("_livedraft.txt", ignore)


class HelpTests(unittest.TestCase):
    def test_help_page_explains_live_draft_and_assignment(self):
        from components.howitworks import render_help_page
        page = render_help_page()
        self.assertIn('id="hiw-live"', page)
        self.assertIn("Detailed Logs", page)
        self.assertIn("kartenarchetypen.json", page)
        self.assertIn("Seitenfenster", page)

    def test_readme_mentions_live_draft(self):
        readme = (pathlib.Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
        self.assertIn("Live-Draft", readme)
        self.assertIn("--live", readme)


class OverlayRowsTests(unittest.TestCase):
    def test_rows_for_a_pack(self):
        snap = {"status": "pack", "pick": 3, "message": "", "detect": {"main": "WB", "manual": False, "scores": [
            {"colors": "WB", "name": "Testgilde", "score": 4, "assigned": 1}]},
                "pack": [{"name": "Test Gold", "level": "arch", "rating": "mustplay", "colors": ["W", "B"],
                          "arch": ["WB"], "points": 6},
                         {"name": "Test Hasty", "level": "", "rating": "", "colors": ["R"], "arch": [], "points": 1.5}]}
        rows = overlay.rows_for(snap)
        self.assertIn("Testgilde", rows[0][0])
        self.assertIn("Pick 3", rows[0][0])
        gold = next(r for r in rows if "Test Gold" in r[0])
        self.assertEqual(gold[1], "arch")
        self.assertIn("MP", gold[0])
        self.assertIn("Test Hasty", rows[-1][0])

    def test_rows_while_waiting_or_without_log(self):
        self.assertIn("nächste Pack", overlay.rows_for({"status": "waiting", "pick": 2, "pack": [],
                                                         "detect": {"main": None}})[-1][0])
        self.assertIn("kein Protokoll", overlay.rows_for({"status": "nolog", "message": "kein Protokoll"})[-1][0])
        self.assertTrue(overlay.rows_for(None))  # Drafthelper nicht erreichbar


if __name__ == "__main__":
    unittest.main()
