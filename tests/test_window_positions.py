"""Fenster merken sich ihre letzte Lage (Nutzer 15.11.2026): Steuerleiste, Seitenfenster und Trick-Warner stehen beim
naechsten Start dort, wo sie zuletzt waren; liegt die Lage ausserhalb der Bildschirme (Monitor abgesteckt), gilt die
Standardlage."""
import pathlib
import tempfile
import unittest

from components import overlay

SCREEN = (0, 0, 1920, 1080)


class PlacedGeometryTests(unittest.TestCase):
    def test_without_saved_position_the_default(self):
        self.assertEqual(overlay.placed_geometry("360x560+1540+80", None, SCREEN), "360x560+1540+80")

    def test_saved_position_wins(self):
        self.assertEqual(overlay.placed_geometry("360x560+1540+80", [100, 200], SCREEN), "360x560+100+200")

    def test_saved_width_wins(self):
        self.assertEqual(overlay.placed_geometry("360x560+1540+80", [100, 200, 420], SCREEN), "420x560+100+200")

    def test_position_only(self):
        self.assertEqual(overlay.placed_geometry("+800+0", [50, 60], SCREEN), "+50+60")

    def test_off_screen_falls_back(self):
        for saved in ([3000, 200], [100, 1200], [-500, 200], [100, -50]):
            self.assertEqual(overlay.placed_geometry("360x560+1540+80", saved, SCREEN), "360x560+1540+80", saved)

    def test_partly_visible_is_kept(self):
        self.assertEqual(overlay.placed_geometry("360x560+1540+80", [1800, 900], SCREEN), "360x560+1800+900")

    def test_second_monitor_left(self):
        both = (-1920, 0, 3840, 1080)
        self.assertEqual(overlay.placed_geometry("360x560+1540+80", [-1500, 100], both), "360x560+-1500+100")

    def test_broken_entries_ignored(self):
        for saved in (["a", 3], [1], "x", [1, 2, 3, 4]):
            self.assertEqual(overlay.placed_geometry("360x560+1540+80", saved, SCREEN), "360x560+1540+80", saved)


class FileTests(unittest.TestCase):
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "fensterlage.json"
            self.assertEqual(overlay.load_positions(path), {})
            pos = {"control": [700, 0], "main": [1500, 80, 380], "tricks": [0, 276, 340]}
            overlay.save_positions(path, pos)
            self.assertEqual(overlay.load_positions(path), pos)

    def test_broken_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "fensterlage.json"
            path.write_text("{kaputt", encoding="utf-8")
            self.assertEqual(overlay.load_positions(path), {})
            path.write_text('{"main": [1, 2], "x": "y", "tricks": [1, "b"]}', encoding="utf-8")
            self.assertEqual(overlay.load_positions(path), {"main": [1, 2]})

    def test_file_next_to_the_other_settings(self):
        self.assertEqual(overlay.POS_FILE.name, "fensterlage.json")
        # Nutzer 17.11.2026: alle JSON-Dateien im Ordner daten (vorher direkt im Projektordner)
        self.assertEqual(overlay.POS_FILE.parent, pathlib.Path(overlay.__file__).resolve().parent.parent / "daten")


if __name__ == "__main__":
    unittest.main()
