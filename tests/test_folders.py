"""Aufgeraeumter Projektordner (Nutzer 17.11.2026): alle JSON-Dateien (Bewertung, Archetypen, Statistik, Caches,
Fensterlagen, Kalibrierungen) liegen im Ordner daten, alle erzeugten HTML-Berichte im Ordner berichte. Ein blosser
Dateiname landet im passenden Ordner, ein Pfad mit Ordner oder ein absoluter Pfad gilt wie angegeben. Beim Start
zieht draftgott vorhandene Dateien aus dem Projektordner einmalig um (nichts wird ueberschrieben)."""
import io
import pathlib
import tempfile
import unittest
from unittest import mock

import mtg_sim
from components import arenapanels, drafthelper, overlay, packoverlay, paths, scryfall, setreport, symbols
from components.cli import parse_args

ROOT = pathlib.Path(__file__).resolve().parent.parent


class FolderTests(unittest.TestCase):
    def test_folders_in_the_project(self):
        self.assertEqual(paths.ROOT, ROOT)
        self.assertEqual(paths.DATA_DIR, ROOT / "daten")
        self.assertEqual(paths.REPORT_DIR, ROOT / "berichte")

    def test_bare_name_goes_into_the_folder(self):
        self.assertEqual(paths.data_file("x.json"), ROOT / "daten" / "x.json")
        self.assertEqual(paths.report_file("x.html"), ROOT / "berichte" / "x.html")

    def test_path_with_folder_or_absolute_stays(self):
        absolute = pathlib.Path(tempfile.gettempdir()) / "x.json"
        self.assertEqual(paths.data_file(str(absolute)), absolute)
        self.assertEqual(paths.report_file(absolute), absolute)
        self.assertEqual(paths.data_file("sub/x.json"), pathlib.Path("sub/x.json"))
        self.assertEqual(paths.report_file("sub/x.html"), pathlib.Path("sub/x.html"))

    def test_folder_is_created_on_demand(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(paths, "DATA_DIR", pathlib.Path(d) / "daten"):
                p = paths.data_file("x.json")
            self.assertTrue(p.parent.is_dir())

    def test_files_of_the_modules_lie_in_daten(self):
        for f in (scryfall.CACHE_FILE, scryfall.IMAGE_CACHE_FILE, scryfall.SET_CACHE_FILE, symbols.SYMBOL_FILE,
                  overlay.POS_FILE, arenapanels.COL_FILE, packoverlay.CAL_FILE):
            self.assertEqual(f.parent, ROOT / "daten", f)

    def test_drafthelper_files_lie_in_daten(self):
        args = parse_args(["--drafthelper"])
        self.assertEqual(drafthelper.ratings_path(args), ROOT / "daten" / "kartenbewertung.json")
        self.assertEqual(drafthelper.stats_path(args), ROOT / "daten" / "draftstatistik.json")
        self.assertEqual(drafthelper.archetypes_path(args), ROOT / "daten" / "kartenarchetypen.json")

    def test_set_report_goes_to_berichte(self):
        self.assertEqual(setreport.OUT_DIR, ROOT / "berichte")

    def test_report_with_bare_name_goes_to_berichte(self):
        with tempfile.TemporaryDirectory() as d:
            args = parse_args(["deck.txt", "--html", "bericht_test.html"])
            with mock.patch.object(paths, "REPORT_DIR", pathlib.Path(d)), mock.patch("sys.stderr", io.StringIO()):
                out = mtg_sim.save_report("<html>", args)
                battle = mtg_sim.save_battle_report("<html>", args)
            self.assertEqual(out, pathlib.Path(d) / "bericht_test.html")
            self.assertEqual(battle, pathlib.Path(d) / "mtg_kampf.html")
            self.assertTrue(out.exists() and battle.exists())

    def test_gitignore_ignores_both_folders(self):
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8").split()
        self.assertIn("daten/", ignore)
        self.assertIn("berichte/", ignore)


class MoveTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def move(self):
        with mock.patch.object(paths, "ROOT", self.root), \
                mock.patch.object(paths, "DATA_DIR", self.root / "daten"), \
                mock.patch.object(paths, "REPORT_DIR", self.root / "berichte"):
            return paths.tidy_up()

    def test_moves_json_and_html(self):
        (self.root / "kartenbewertung.json").write_text("{}", encoding="utf-8")
        (self.root / "mtg_bericht.html").write_text("<html>", encoding="utf-8")
        moved = self.move()
        self.assertEqual(moved, 2)
        self.assertEqual((self.root / "daten" / "kartenbewertung.json").read_text(encoding="utf-8"), "{}")
        self.assertTrue((self.root / "berichte" / "mtg_bericht.html").exists())
        self.assertFalse((self.root / "kartenbewertung.json").exists())
        self.assertFalse((self.root / "mtg_bericht.html").exists())

    def test_other_files_stay(self):
        for name in ("README.md", "_livedraft.txt", "draftgott.bat", "x.json.tmp"):
            (self.root / name).write_text("x", encoding="utf-8")
        self.assertEqual(self.move(), 0)
        for name in ("README.md", "_livedraft.txt", "draftgott.bat", "x.json.tmp"):
            self.assertTrue((self.root / name).exists(), name)

    def test_never_overwrites(self):
        (self.root / "daten").mkdir()
        (self.root / "daten" / "draftstatistik.json").write_text("neu", encoding="utf-8")
        (self.root / "draftstatistik.json").write_text("alt", encoding="utf-8")
        self.assertEqual(self.move(), 0)
        self.assertEqual((self.root / "daten" / "draftstatistik.json").read_text(encoding="utf-8"), "neu")
        self.assertEqual((self.root / "draftstatistik.json").read_text(encoding="utf-8"), "alt")

    def test_nothing_to_do_creates_nothing(self):
        self.assertEqual(self.move(), 0)
        self.assertFalse((self.root / "daten").exists())


class SideboardFileTests(unittest.TestCase):
    def test_pool_in_project_folder_keeps_sideboard_in_daten(self):
        self.assertEqual(paths.beside(ROOT / "_livedraft.txt", "_sideboard.json"),
                         ROOT / "daten" / "_livedraft_sideboard.json")

    def test_pool_elsewhere_keeps_sideboard_beside_it(self):
        pool = pathlib.Path(tempfile.gettempdir()) / "pool.txt"
        self.assertEqual(paths.beside(pool, "_sideboard.json"), pool.with_name("pool_sideboard.json"))


if __name__ == "__main__":
    unittest.main()
