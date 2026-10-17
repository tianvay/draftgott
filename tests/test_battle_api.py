"""Drafthelper: Gegnerdecks auflisten, Kampf nach dem Bericht starten, Kampfbericht abrufen."""
import io
import json
import pathlib
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest import mock

from components import drafthelper as dh
from tests.fixtures import args_for
from tests.test_drafthelper import load


class BattleApiTests(unittest.TestCase):
    def setUp(self):
        cards, basics, sig = load()
        self.tmp = tempfile.TemporaryDirectory()
        folder = pathlib.Path(self.tmp.name)
        (folder / "_enemydeck_test_walls.txt").write_text("Deck\n17 Plains\n23 Test Bear\n", encoding="utf-8")
        (folder / "_enemydeck_other.txt").write_text("Name Andere\nDeck\n17 Plains\n", encoding="utf-8")
        (folder / "notes.txt").write_text("kein Gegner", encoding="utf-8")
        self.calls = []

        def fake_battle(entries, enemy_path, args, progress):
            self.calls.append((entries, pathlib.Path(enemy_path).name, args))
            return "<p>KAMPFBERICHT</p>"

        self.app = {"pool": cards, "basics": basics, "signature": sig, "args": args_for(["--drafthelper"]),
                    "simulate": lambda entries, args, progress: "", "save": lambda html, args: None,
                    "battle": fake_battle, "save_battle": lambda html, args: None,
                    "job": dh.Job(), "options": [1000], "file": "pool.txt"}
        self._dir = mock.patch.object(dh, "SCRIPT_DIR", folder)
        self._dir.start()
        self._stderr = mock.patch("sys.stderr", io.StringIO())
        self._stderr.start()
        self.server = dh.LocalServer(("127.0.0.1", 0), dh.make_handler(self.app))
        self.app["server"] = self.server
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self._stderr.stop()
        self._dir.stop()
        self.tmp.cleanup()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=10) as r:
            return r.read().decode("utf-8")

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def wait(self):
        for _ in range(100):
            s = json.loads(self.get("/api/status"))
            if s["state"] != "running":
                return s
            time.sleep(0.05)
        self.fail("Job endet nicht")

    def test_enemy_decks_are_listed(self):
        enemies = json.loads(self.get("/api/enemies"))["enemies"]
        self.assertEqual({e["file"] for e in enemies}, {"_enemydeck_test_walls.txt", "_enemydeck_other.txt"})
        names = {e["file"]: e["name"] for e in enemies}
        self.assertEqual(names["_enemydeck_test_walls.txt"], "test walls")
        self.assertEqual(names["_enemydeck_other.txt"], "Andere")

    def test_battle_needs_a_report_first(self):
        status, answer = self.post("/api/battle", {"enemy": "_enemydeck_test_walls.txt"})
        self.assertEqual(status, 400)
        self.assertIn("zuerst", answer["error"])

    def test_unknown_enemy_file(self):
        self.app["last_entries"], self.app["last_args"] = [{"name": "X", "deck": {}}], self.app["args"]
        status, _answer = self.post("/api/battle", {"enemy": "../geheim.txt"})
        self.assertEqual(status, 400)

    def test_battle_after_the_report(self):
        entries = [{"name": "Splash", "deck": {"Plains": 17}}, {"name": "NoSplash", "deck": {"Plains": 17}}]
        self.app["last_entries"], self.app["last_args"] = entries, self.app["args"]
        self.app["report_html"] = "<p>GOLDFISH</p>"
        status, answer = self.post("/api/battle", {"enemy": "_enemydeck_test_walls.txt"})
        self.assertEqual((status, answer["ok"]), (200, True))
        self.assertEqual(self.wait()["state"], "done")
        self.assertIn("KAMPFBERICHT", self.get("/battle"))
        self.assertIn("GOLDFISH", self.get("/report"))  # der normale Bericht bleibt
        used_entries, enemy_file, _args = self.calls[0]
        self.assertEqual([e["name"] for e in used_entries], ["Splash", "NoSplash"])
        self.assertEqual(enemy_file, "_enemydeck_test_walls.txt")

    def test_battle_controls_are_in_the_report_not_in_the_page(self):
        page = self.get("/")
        self.assertNotIn('id="fight"', page)  # die Leiste steht im Bericht selbst (FIGHT_JS)
        answer = json.loads(self.get("/api/enemies"))
        self.assertFalse(answer.get("quit"))  # im Drafthelper beendet die Seite selbst


if __name__ == "__main__":
    unittest.main()
