"""Hauptordner aufgeraeumt (Nutzer 17.11.2026): Kartenpools des Drafthelpers (_livedraft.txt, _draftedcardpool.txt)
liegen in daten, die Beispieldeckliste _normaldeck.txt im Ordner decks. Ein blosser Name wird dort gefunden."""
import os
import pathlib
import tempfile
import unittest
from unittest import mock

import mtg_sim
from components import drafthelper as dh
from components import paths
from components.cli import parse_args

ROOT = pathlib.Path(__file__).resolve().parent.parent


class Patched(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.dir.name)
        self.data = self.root / "daten"
        self.patches = [mock.patch.object(paths, "ROOT", self.root), mock.patch.object(paths, "DATA_DIR", self.data),
                        mock.patch.object(paths, "DECK_DIR", self.root / "decks"),
                        mock.patch.object(dh, "SCRIPT_DIR", self.root)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.dir.cleanup()


class MovePools(Patched):
    def test_moves_both_pools(self):
        for name in paths.POOL_FILES:
            (self.root / name).write_text("Deck\n1 Bear\n", encoding="utf-8")
        self.assertEqual(paths.move_pools(), 2)
        for name in paths.POOL_FILES:
            self.assertFalse((self.root / name).exists())
            self.assertEqual((self.data / name).read_text(encoding="utf-8"), "Deck\n1 Bear\n")

    def test_never_overwrites(self):
        self.data.mkdir()
        (self.root / "_livedraft.txt").write_text("alt", encoding="utf-8")
        (self.data / "_livedraft.txt").write_text("neu", encoding="utf-8")
        self.assertEqual(paths.move_pools(), 0)
        self.assertEqual((self.data / "_livedraft.txt").read_text(encoding="utf-8"), "neu")
        self.assertTrue((self.root / "_livedraft.txt").exists())

    def test_nothing_to_move(self):
        (self.root / "README.md").write_text("x", encoding="utf-8")
        self.assertEqual(paths.move_pools(), 0)
        self.assertTrue((self.root / "README.md").exists())


class FindPool(Patched):
    def test_bare_name_found_in_data(self):
        self.data.mkdir()
        (self.data / "_draftedcardpool.txt").write_text("Deck\n", encoding="utf-8")
        self.assertEqual(dh.pool_path("_draftedcardpool.txt"), self.data / "_draftedcardpool.txt")

    def test_live_pool_created_in_data(self):
        p = dh.live_pool_file("_livedraft.txt")
        self.assertEqual(p, self.data / "_livedraft.txt")
        self.assertEqual(p.read_text(encoding="utf-8"), "Deck\n")
        self.assertFalse((self.root / "_livedraft.txt").exists())

    def test_live_pool_kept_where_it_is(self):
        self.data.mkdir()
        (self.data / "_livedraft.txt").write_text("Deck\n1 Bear\n", encoding="utf-8")
        self.assertEqual(dh.live_pool_file("_livedraft.txt").read_text(encoding="utf-8"), "Deck\n1 Bear\n")

    def test_missing_pool_names_the_data_folder(self):
        here = os.getcwd()
        os.chdir(self.root)  # nicht die echte Datei im Arbeitsordner finden
        try:
            with self.assertRaises(SystemExit) as cm:
                dh.pool_path("_draftedcardpool.txt")
        finally:
            os.chdir(here)
        self.assertIn("daten", str(cm.exception.code))

    def test_sideboard_next_to_pool_in_data(self):
        self.data.mkdir()
        self.assertEqual(paths.beside(self.data / "_livedraft.txt", "_sideboard.json"),
                         self.data / "_livedraft_sideboard.json")


class Decks(Patched):
    def test_bare_deck_name_found_in_decks(self):
        (self.root / "decks").mkdir()
        (self.root / "decks" / "mein.txt").write_text("Deck\n", encoding="utf-8")
        self.assertEqual(paths.deck_file("mein.txt"), self.root / "decks" / "mein.txt")

    def test_given_path_wins_and_unknown_stays(self):
        p = self.root / "anders.txt"
        p.write_text("Deck\n", encoding="utf-8")
        self.assertEqual(paths.deck_file(str(p)), str(p))
        self.assertEqual(paths.deck_file("fehlt.txt"), "fehlt.txt")


class Repo(unittest.TestCase):
    def test_example_deck_in_decks_folder(self):
        self.assertTrue((ROOT / "decks" / "_normaldeck.txt").is_file())
        self.assertFalse((ROOT / "_normaldeck.txt").exists())

    def test_analysis_reads_deck_from_decks_folder(self):
        entries = mtg_sim.entries_from_files(parse_args(["_normaldeck.txt", "--nicht-oeffnen"]))
        self.assertEqual(pathlib.Path(entries[0]["path"]), ROOT / "decks" / "_normaldeck.txt")
        self.assertTrue(entries[0]["deck"])

    def test_start_moves_pools(self):
        with mock.patch.object(paths, "move_pools") as move, mock.patch.object(paths, "tidy_up"), \
                mock.patch.object(mtg_sim, "run", lambda args: None):
            mtg_sim.main(["--setauswertung", "--nicht-oeffnen"])
        move.assert_called_once()


if __name__ == "__main__":
    unittest.main()
