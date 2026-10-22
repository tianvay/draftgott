"""Kartenbewertung (Splashworthy, MustPlay, Filler, NeverPlay) je Kartenname in einer eigenen Datei
(kartenbewertung.json, nicht im Git), unabhaengig vom Kartenpool."""
import io
import json
import pathlib
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock

from components import drafthelper as dh
from components import ratings
from components.cli import parse_args
from tests.test_drafthelper import load
from tests.fixtures import args_for

ROOT = pathlib.Path(__file__).resolve().parent.parent


class FileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.tmp.name) / "kartenbewertung.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_file_is_empty(self):
        self.assertEqual(ratings.load_ratings(self.path), {})

    def test_broken_file_is_empty(self):
        self.path.write_text("{kaputt", encoding="utf-8")
        self.assertEqual(ratings.load_ratings(self.path), {})

    def test_unknown_categories_are_ignored(self):
        self.path.write_text(json.dumps({"A": "filler", "B": "super", "C": 3}), encoding="utf-8")
        self.assertEqual(ratings.load_ratings(self.path), {"A": "filler"})

    def test_set_and_remove(self):
        ratings.set_rating(self.path, "Lightning Bolt", "splashworthy")
        ratings.set_rating(self.path, "Abrade", "filler")
        self.assertEqual(ratings.load_ratings(self.path), {"Abrade": "filler", "Lightning Bolt": "splashworthy"})
        ratings.set_rating(self.path, "Abrade", "")
        self.assertEqual(ratings.load_ratings(self.path), {"Lightning Bolt": "splashworthy"})

    def test_file_is_sorted_and_readable(self):
        ratings.set_rating(self.path, "Zap", "filler")
        ratings.set_rating(self.path, "Abrade", "mustplay")
        text = self.path.read_text(encoding="utf-8")
        self.assertLess(text.index("Abrade"), text.index("Zap"))
        self.assertIn("\n", text)

    def test_invalid_category(self):
        with self.assertRaises(ValueError):
            ratings.set_rating(self.path, "Zap", "super")

    def test_merge_keeps_existing(self):
        ratings.set_rating(self.path, "Zap", "filler")
        out = ratings.merge_ratings(self.path, {"Zap": "neverplay", "Abrade": "mustplay", "X": "kaputt"})
        self.assertEqual(out, {"Abrade": "mustplay", "Zap": "filler"})
        self.assertEqual(ratings.load_ratings(self.path), out)


class SetupTests(unittest.TestCase):
    def test_default_file_and_option(self):
        self.assertEqual(parse_args(["--drafthelper"]).bewertung, "kartenbewertung.json")
        self.assertEqual(parse_args(["--drafthelper", "--bewertung", "anna.json"]).bewertung, "anna.json")

    def test_not_in_git(self):
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("kartenbewertung*.json", ignore)


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = pathlib.Path(cls.tmp.name) / "kartenbewertung.json"
        cards, basics, sig = load()
        cls.names = [c["name"] for c in cards]
        cls._stderr = mock.patch("sys.stderr", io.StringIO())
        cls._stderr.start()
        cls.app = {"pool": cards, "basics": basics, "signature": sig, "args": args_for(["--drafthelper"]),
                   "simulate": None, "save": None, "job": dh.Job(), "options": [1000], "file": "pool.txt",
                   "ratings": cls.path}
        cls.server = dh.LocalServer(("127.0.0.1", 0), dh.make_handler(cls.app))
        cls.app["server"] = cls.server
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls._stderr.stop()
        cls.tmp.cleanup()

    def setUp(self):
        if self.path.exists():
            self.path.unlink()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=10) as r:
            return json.loads(r.read())

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_ratings_for_the_pool(self):
        self.path.write_text(json.dumps({self.names[0]: "filler", "Karte ausserhalb": "mustplay"}), encoding="utf-8")
        self.assertEqual(self.get("/api/ratings")["ratings"], {self.names[0]: "filler"})

    def test_set_rating_saves_the_file(self):
        status, answer = self.post("/api/rating", {"name": self.names[1], "cat": "splashworthy"})
        self.assertEqual((status, answer["ok"]), (200, True))
        self.assertEqual(ratings.load_ratings(self.path), {self.names[1]: "splashworthy"})
        self.post("/api/rating", {"name": self.names[1], "cat": ""})
        self.assertEqual(ratings.load_ratings(self.path), {})

    def test_reject_unknown_card_or_category(self):
        self.assertEqual(self.post("/api/rating", {"name": "Gibt es nicht", "cat": "filler"})[0], 400)
        self.assertEqual(self.post("/api/rating", {"name": self.names[0], "cat": "super"})[0], 400)
        self.assertFalse(self.path.exists())

    def test_import_old_browser_ratings(self):
        ratings.set_rating(self.path, self.names[0], "filler")
        status, answer = self.post("/api/ratings/import", {"cats": {self.names[0]: "neverplay",
                                                                    "Andere Karte": "mustplay"}})
        self.assertEqual(status, 200)
        self.assertEqual(ratings.load_ratings(self.path), {self.names[0]: "filler", "Andere Karte": "mustplay"})
        self.assertEqual(answer["ratings"], {self.names[0]: "filler"})

    def test_page_uses_the_file(self):
        self.assertIn("/api/rating", dh.PAGE)
        self.assertIn("/api/ratings/import", dh.PAGE)


if __name__ == "__main__":
    unittest.main()
