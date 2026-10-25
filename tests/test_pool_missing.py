"""Drafthelper ohne Kartenpool-Datei: _draftedcardpool.txt liegt nicht mehr im Git (jeder Nutzer hat seinen eigenen
Pool). Fehlt die Datei, bricht der Drafthelper sofort mit einer erklaerenden Meldung ab - vor jedem Scryfall-Zugriff."""
import os
import pathlib
import tempfile
import unittest
from unittest import mock

import mtg_sim
from components import drafthelper as dh
from components.cli import parse_args


class PoolPathTests(unittest.TestCase):
    def test_missing_file_message(self):
        with self.assertRaises(SystemExit) as cm:
            dh.pool_path("gibt_es_nicht.txt")
        msg = str(cm.exception.code)
        for part in ("gibt_es_nicht.txt", "nicht gefunden", "Deck", "Sideboard"):
            self.assertIn(part, msg)

    def test_existing_file_is_returned(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "pool.txt"
            path.write_text("Deck\n1 Test Bear\n", encoding="utf-8")
            self.assertEqual(dh.pool_path(str(path)), path)

    def test_relative_to_project_folder(self):
        here = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)  # aus einem anderen Ordner gestartet
            try:
                self.assertEqual(dh.pool_path("README.md"), dh.SCRIPT_DIR / "README.md")
            finally:
                os.chdir(here)

    def test_run_stops_before_scryfall(self):
        args = parse_args(["--drafthelper", "gibt_es_nicht.txt", "--nicht-oeffnen"])
        with mock.patch("mtg_sim.fetch_symbols") as symbols, self.assertRaises(SystemExit):
            mtg_sim.run(args)
        symbols.assert_not_called()


class GitTests(unittest.TestCase):
    def test_pool_file_is_ignored(self):
        lines = (dh.SCRIPT_DIR / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("_draftedcardpool.txt", lines)


if __name__ == "__main__":
    unittest.main()
