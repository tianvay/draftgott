"""Drafthelper: Kampf direkt aus der Zuordnung starten, ohne vorher den Goldfish zu simulieren."""
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


class DirectBattleTests(unittest.TestCase):
    def setUp(self):
        cards, basics, sig = load()
        self.tmp = tempfile.TemporaryDirectory()
        folder = pathlib.Path(self.tmp.name)
        (folder / "enemydecks").mkdir()
        (folder / "enemydecks" / "test_walls.txt").write_text("Deck\n17 Plains\n23 Test Bear\n", encoding="utf-8")
        self.calls, self.sims, self.saved = [], [], []

        def fake_battle(entries, enemy_path, args, progress):
            self.calls.append((entries, pathlib.Path(enemy_path).name, args))
            return "<p>KAMPFBERICHT</p>"

        def fake_simulate(entries, args, progress):
            self.sims.append(entries)
            return "<p>GOLDFISH</p>"

        self.app = {"pool": cards, "basics": basics, "signature": sig, "args": args_for(["--drafthelper"]),
                    "simulate": fake_simulate, "save": lambda html, args: None,
                    "battle": fake_battle, "save_battle": lambda html, args: self.saved.append(html),
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

    def state(self, **extra):
        marks = [["core"] * c["qty"] for c in self.app["pool"]]
        body = {"marks": marks, "basics": {"Plains": {"core": 4, "splash": 0, "nosplash": 0}}, "cats": {}}
        body.update(extra)
        return body

    def test_direct_battle_without_goldfish(self):
        body = self.state(enemy="test_walls.txt", games=50)
        body["marks"][[c["name"] for c in self.app["pool"]].index("Test Spell")] = ["splash"]
        status, answer = self.post("/api/battle", body)
        self.assertEqual((status, answer["ok"]), (200, True))
        self.assertEqual(self.wait()["state"], "done")
        self.assertEqual(self.sims, [])  # kein Goldfish
        self.assertIn("KAMPFBERICHT", self.get("/battle"))
        self.assertEqual(self.saved, ["<p>KAMPFBERICHT</p>"])
        entries, enemy_file, args = self.calls[0]
        self.assertEqual([e["name"] for e in entries], ["Splash", "NoSplash"])
        self.assertEqual(entries[0]["deck"]["Plains"], 4)
        self.assertEqual(enemy_file, "test_walls.txt")
        self.assertEqual(args.kaempfe, 50)
        self.assertEqual(args.core, "Core")
        self.assertIn("Noch kein Bericht", self.get("/report"))  # kein Goldfish-Bericht entstanden

    def test_direct_battle_uses_current_marks_not_the_last_report(self):
        old = [{"name": "Alt", "deck": {"Plains": 17}}]
        self.app["last_entries"], self.app["last_args"] = old, self.app["args"]
        self.assertEqual(self.post("/api/battle", self.state(enemy="test_walls.txt"))[0], 200)
        self.wait()
        self.assertEqual([e["name"] for e in self.calls[0][0]], ["Core"])

    def test_direct_battle_with_proposal(self):
        body = self.state(enemy="test_walls.txt", proposal={"colors": ["W"], "target": 40, "sort": "mv"})
        self.assertEqual(self.post("/api/battle", body)[0], 200)
        self.wait()
        self.assertIn("Vorschlag", [e["name"] for e in self.calls[0][0]])

    def test_invalid_marks_are_rejected(self):
        status, answer = self.post("/api/battle", self.state(enemy="test_walls.txt", marks=[["core"]]))
        self.assertEqual(status, 400)
        self.assertFalse(answer["ok"])
        self.assertEqual(self.calls, [])

    def test_unknown_enemy_keeps_the_last_report_entries(self):
        old = [{"name": "Alt", "deck": {"Plains": 17}}]
        self.app["last_entries"], self.app["last_args"] = old, self.app["args"]
        status, _answer = self.post("/api/battle", self.state(enemy="../geheim.txt"))
        self.assertEqual(status, 400)
        self.assertIs(self.app["last_entries"], old)

    def test_page_has_direct_battle_controls(self):
        page = self.get("/")
        for marker in ('id="dkenemy"', 'id="dkcount"', 'id="dkgo"', "Kampf ohne Goldfish", '<option value="500" selected'):
            self.assertIn(marker, page)

    def test_help_explains_direct_battle(self):
        self.assertIn("Kampf ohne Goldfish", self.get("/howitworks.html"))


if __name__ == "__main__":
    unittest.main()
