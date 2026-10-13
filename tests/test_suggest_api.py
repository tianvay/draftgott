import io
import json
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock

from components import drafthelper as dh
from tests.fixtures import args_for
from tests.test_drafthelper import load


class SuggestApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cards, basics, sig = load()
        cls.app = {"pool": cards, "basics": basics, "signature": sig, "args": args_for(["--drafthelper"]),
                   "simulate": lambda entries, args, progress: "", "save": lambda html, args: None,
                   "job": dh.Job(), "options": [1000], "file": "pool.txt"}
        cls._stderr = mock.patch("sys.stderr", io.StringIO())
        cls._stderr.start()
        cls.server = dh.LocalServer(("127.0.0.1", 0), dh.make_handler(cls.app))
        cls.app["server"] = cls.server
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls._stderr.stop()

    def post(self, body):
        req = urllib.request.Request(self.base + "/api/suggest", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def body(self, **extra):
        pool = self.app["pool"]
        body = {"marks": [["off"] * c["qty"] for c in pool],
                "basics": {"Plains": {"core": 4, "splash": 0, "nosplash": 0}},
                "cats": {"Test Big": "mustplay", "Test Defender": "splashworthy", "Test Spell": "neverplay",
                         "Test Gold": "filler", "Test Bear": "filler", "Test Hasty": "filler"},
                "target": 10, "sort": "mv"}
        body.update(extra)
        return body

    def idx(self, name):
        return [c["name"] for c in self.app["pool"]].index(name)

    def test_returns_new_marks_per_card_and_a_summary(self):
        status, answer = self.post(self.body())
        self.assertEqual(status, 200)
        self.assertTrue(answer["ok"])
        marks = answer["marks"]
        self.assertEqual(len(marks), len(self.app["pool"]))
        self.assertEqual(marks[self.idx("Test Big")], ["core"])
        self.assertEqual(marks[self.idx("Test Defender")], ["splash", "splash"])
        self.assertEqual(marks[self.idx("Test Spell")], ["off"])
        # Core: Test Big + 4 Plains = 5, Splash 2 -> Splash 7, NoSplash 5, Ziel 10 -> 3 Filler Core, 2 NoSplash
        self.assertEqual(answer["summary"]["sizes"], {"splash": 10, "nosplash": 10})
        self.assertEqual(answer["summary"]["warnings"], [])

    def test_does_not_start_a_simulation(self):
        self.post(self.body())
        self.assertEqual(self.app["job"].status()["state"], "idle")

    def test_wrong_shape_of_marks_is_rejected(self):
        self.assertEqual(self.post(self.body(marks=[["core"]]))[0], 400)

    def test_unknown_mark_is_rejected(self):
        body = self.body()
        body["marks"][0][0] = "irgendwas"
        self.assertEqual(self.post(body)[0], 400)

    def test_target_out_of_range_is_rejected(self):
        self.assertEqual(self.post(self.body(target=3))[0], 400)
        self.assertEqual(self.post(self.body(target=5000))[0], 400)

    def test_unknown_sort_is_rejected(self):
        self.assertEqual(self.post(self.body(sort="zufall"))[0], 400)

    def test_basic_land_out_of_range_is_rejected(self):
        bad = {"Plains": {"core": 999, "splash": 0, "nosplash": 0}}
        self.assertEqual(self.post(self.body(basics=bad))[0], 400)

    def test_unknown_categories_are_ignored(self):
        status, answer = self.post(self.body(cats={"Gibt Es Nicht": "mustplay", "Test Big": "unsinn"}))
        self.assertEqual(status, 200)
        self.assertEqual(answer["marks"][self.idx("Test Big")], ["off"])


if __name__ == "__main__":
    unittest.main()
