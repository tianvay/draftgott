"""Live-Draft: nach dem Draft das in Arena abgegebene Deck samt Sideboard in den Drafthelper uebernehmen (Knopf auf
der Seite und im Seitenfenster)."""
import json
import pathlib
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from components import drafthelper as dh
from components import livedraft as ld
from components import overlay
from tests.fixtures import CARDS, args_for
from tests.test_drafthelper import load
from tests.test_livedraft import NAMES as BASE_NAMES, notify, pick

NAMES = {**BASE_NAMES, 301: {"name": "Plains", "set": "TST", "number": "1"},
         302: {"name": "Mountain", "set": "TST", "number": "4"}}
EVENT = "PremierDraft_TST_20261110"


def deck_line(main, side, event=EVENT):
    deck = {"MainDeck": [{"cardId": g, "quantity": q} for g, q in main],
            "Sideboard": [{"cardId": g, "quantity": q} for g, q in side]}
    return "[UnityCrossThreadLogger]==> EventSetDeckV3 " + json.dumps(
        {"id": "x", "request": json.dumps({"EventName": event, "Deck": deck})})


DRAFT = [notify(1, [101, 102, 103]), pick([101]), notify(2, [102, 103]), pick([102]), notify(3, [103]),
         pick([103])]
DECK = deck_line([(101, 1), (103, 1), (301, 9), (302, 8)], [(102, 1)])


class TransferTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        d = pathlib.Path(self.dir.name)
        self.log, self.pool = d / "Player.log", d / "_livedraft.txt"
        self.live = self.new_live()

    def new_live(self):
        return ld.LiveDraft(self.log, self.pool, names=NAMES, fetch=lambda n, refresh=False: CARDS)

    def tearDown(self):
        self.dir.cleanup()

    def write(self, *lines):
        with self.log.open("a", encoding="utf-8") as fh:
            fh.write("".join(line + "\n" for line in lines))


class LiveDeckTests(TransferTestCase):
    def test_deck_appears_after_done_in_arena(self):
        self.write(*DRAFT)
        self.live.step()
        snap = self.live.snapshot({}, {}, None)
        self.assertEqual(snap["deck"], {"ready": False, "main": 0, "side": 0, "applied": False})
        self.assertFalse(snap["complete"])
        self.write(DECK)
        self.assertTrue(self.live.step())
        snap = self.live.snapshot({}, {}, None)
        self.assertEqual(snap["deck"], {"ready": True, "main": 19, "side": 1, "applied": False})
        self.assertTrue(snap["complete"])

    def test_apply_writes_deck_and_sideboard(self):
        self.write(*DRAFT, DECK)
        self.live.step()
        version = self.live.version
        self.live.apply_deck()
        self.assertEqual(self.pool.read_text(encoding="utf-8"),
                         "Deck\n1 Test Bear (TST) 10\n1 Test Spell (TST) 15\n9 Plains (TST) 1\n8 Mountain (TST) 4\n"
                         "\nSideboard\n1 Test Hasty (TST) 11\n")
        self.assertGreater(self.live.version, version)
        self.assertTrue(self.live.snapshot({}, {}, None)["deck"]["applied"])

    def test_apply_without_deck(self):
        self.write(*DRAFT)
        self.live.step()
        with self.assertRaises(ValueError):
            self.live.apply_deck()

    def test_restart_keeps_the_applied_deck(self):
        self.write(*DRAFT, DECK)
        self.live.step()
        self.live.apply_deck()
        before = self.pool.read_text(encoding="utf-8")
        again = self.new_live()  # draftgott neu gestartet: Protokoll von vorn, gleiche Karten
        again.step()
        self.assertEqual(self.pool.read_text(encoding="utf-8"), before)
        self.assertTrue(again.snapshot({}, {}, None)["deck"]["applied"])

    def test_deck_of_another_draft_is_ignored(self):
        self.write(deck_line([(201, 1), (202, 1), (301, 15)], []), *DRAFT)  # altes Deck desselben Events
        self.live.step()
        self.assertFalse(self.live.snapshot({}, {}, None)["deck"]["ready"])

    def test_new_picks_after_apply_are_written_again(self):
        self.write(*DRAFT, DECK)
        self.live.step()
        self.live.apply_deck()
        self.write(notify(1, [201, 202], draft="d2"), pick([201], draft="d2"))  # naechster Draft
        self.live.step()
        self.assertEqual(self.pool.read_text(encoding="utf-8"), "Deck\n1 Test Gold (TST) 14\n")
        self.assertFalse(self.live.snapshot({}, {}, None)["deck"]["ready"])

    def test_complete_after_42_picks_without_deck(self):
        self.write("nichts")  # Protokoll vorhanden
        self.live.state.picks = [101] * 42
        self.live.state.draft = "d1"
        snap = self.live.snapshot({}, {}, None)
        self.assertTrue(snap["complete"])
        self.assertFalse(snap["deck"]["ready"])


class ServerTests(TransferTestCase):
    def setUp(self):
        super().setUp()
        cards, basics, sig = load()
        pool_file = self.pool

        def reload_pool():
            return load(pool_file.read_text(encoding="utf-8"))

        self.app = {"pool": cards, "basics": basics, "signature": sig, "args": args_for(["--drafthelper"]),
                    "simulate": None, "save": None, "job": dh.Job(), "options": [1000], "file": "pool.txt",
                    "live": self.live, "reload_pool": reload_pool}
        self.server = dh.LocalServer(("127.0.0.1", 0), dh.make_handler(self.app))
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def post(self, path):
        req = urllib.request.Request(self.base + path, data=b"{}", headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    def test_transfer_button(self):
        self.write(*DRAFT)
        self.live.step()
        status, data = self.post("/api/live/deck")
        self.assertEqual(status, 400)
        self.assertIn("Fertig", data["error"])
        self.write(DECK)
        self.live.step()
        self.assertEqual(self.post("/api/live/deck")[0], 200)
        with urllib.request.urlopen(self.base + "/api/pool", timeout=10) as r:
            pool = json.loads(r.read().decode("utf-8"))
        sections = {c["name"]: c["section"] for c in pool["cards"]}
        self.assertEqual(sections, {"Test Bear": "deck", "Test Spell": "deck", "Test Hasty": "sideboard"})
        basics = {b["name"]: b["core"] for b in pool["basics"]}
        self.assertEqual((basics["Plains"], basics["Mountain"]), (9, 8))

    def test_page_has_the_button(self):
        with urllib.request.urlopen(self.base + "/", timeout=10) as r:
            self.assertIn('id="ldeck"', r.read().decode("utf-8"))


class TextTests(unittest.TestCase):
    def test_help_and_readme(self):
        from components.howitworks import render_help_page
        self.assertIn("Deck + Sideboard übernehmen", render_help_page())
        readme = (pathlib.Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
        self.assertIn("Deck übernehmen", readme)


class OverlayButtonTests(unittest.TestCase):
    def test_button_state(self):
        self.assertIsNone(overlay.deck_button({"status": "pack", "complete": False, "deck": {"ready": False}}))
        label, active = overlay.deck_button({"status": "waiting", "complete": True,
                                             "deck": {"ready": False, "applied": False}})
        self.assertFalse(active)
        self.assertIn("Fertig", label)
        label, active = overlay.deck_button({"status": "waiting", "complete": True,
                                             "deck": {"ready": True, "applied": False, "main": 40, "side": 2}})
        self.assertTrue(active)
        self.assertIn("Sideboard", label)
        label, active = overlay.deck_button({"status": "waiting", "complete": True,
                                             "deck": {"ready": True, "applied": True}})
        self.assertFalse(active)
        self.assertIn("übernommen", label)
        self.assertIsNone(overlay.deck_button(None))


if __name__ == "__main__":
    unittest.main()
