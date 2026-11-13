"""Scryfall-Kartencache: keine Konsolenmeldungen, wenn alles aus dem Cache kommt (Live-Modus fragt staendig nach)."""
import contextlib
import io
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from components import scryfall


class CachedFetchTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.file = pathlib.Path(tmp.name) / "scryfall_cache.json"
        self.file.write_text(json.dumps({"Test Bear": {"name": "Test Bear"}}), encoding="utf-8")
        patcher = mock.patch.object(scryfall, "CACHE_FILE", self.file)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_all_cached_is_silent_and_offline(self):
        err, out = io.StringIO(), io.StringIO()
        with mock.patch.object(scryfall, "fetch_cards", side_effect=AssertionError("kein Netz erwartet")), \
                contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            data = scryfall.fetch_cards_cached(["Test Bear"])
        self.assertEqual(data["Test Bear"]["name"], "Test Bear")
        self.assertEqual(err.getvalue(), "")
        self.assertEqual(out.getvalue(), "")

    def test_missing_card_is_fetched_and_saved(self):
        with mock.patch.object(scryfall, "fetch_cards", lambda names: {n: {"name": n} for n in names}):
            data = scryfall.fetch_cards_cached(["Test Bear", "Test Wolf"])
        self.assertIn("Test Wolf", data)
        self.assertIn("Test Wolf", json.loads(self.file.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
