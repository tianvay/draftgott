"""Fenster des Live-Drafts: Steuerfenster am linken Bildschirmrand schaltet Seitenfenster (Draft/Bibliothek) und
Trick-Warner an und ab (Nutzer 13.11.2026)."""
import unittest

from components import overlay


def game(active=True, tricks=None):
    g = {"active": active, "turn": 3, "library": 30, "hand": 5, "groups": [], "cards": []}
    if tricks is not None:
        g["tricks"] = tricks
    return {"status": "waiting", "game": g}


TRICKS = {"open": 2, "lands": 3, "colors": {"W": 2}, "now": [{"name": "Trick 1W", "cost": "{1}{W}"}]}


class WindowListTests(unittest.TestCase):
    def test_two_windows_with_names(self):
        keys = [k for k, _ in overlay.WINDOWS]
        self.assertEqual(keys, ["main", "tricks"])
        labels = " ".join(label for _, label in overlay.WINDOWS)
        self.assertIn("Bibliothek", labels)
        self.assertIn("Trick", labels)

    def test_all_windows_on_by_default(self):
        self.assertEqual(overlay.default_enabled(), {"main": True, "tricks": True})


class VisibleTests(unittest.TestCase):
    def test_main_window_follows_the_switch(self):
        self.assertIn("main", overlay.visible_windows({"main": True, "tricks": True}, None))
        self.assertNotIn("main", overlay.visible_windows({"main": False, "tricks": True}, game()))

    def test_trick_window_only_during_a_game(self):
        on = {"main": True, "tricks": True}
        self.assertIn("tricks", overlay.visible_windows(on, game(tricks=TRICKS)))
        self.assertNotIn("tricks", overlay.visible_windows(on, game(active=False)))
        self.assertNotIn("tricks", overlay.visible_windows(on, {"status": "pack", "pick": 3}))
        self.assertNotIn("tricks", overlay.visible_windows(on, None))

    def test_trick_window_off(self):
        self.assertNotIn("tricks", overlay.visible_windows({"main": True, "tricks": False}, game(tricks=TRICKS)))


class TrickWindowRowsTests(unittest.TestCase):
    def test_rows_with_tricks(self):
        text = "\n".join(r[0] for r in overlay.trick_window_rows(game(tricks=TRICKS)))
        self.assertIn("Zug 3", text)
        self.assertIn("Gegner offen 2", text)
        self.assertIn("Trick 1W", text)
        self.assertNotIn("Bibliothek", text)

    def test_rows_without_trick_data(self):
        rows = overlay.trick_window_rows(game())
        self.assertTrue(rows)
        self.assertNotIn("Gegner offen", "\n".join(r[0] for r in rows))

    def test_rows_outside_a_game(self):
        self.assertTrue(overlay.trick_window_rows(None))
        self.assertTrue(overlay.trick_window_rows({"status": "pack"}))


class GameRowsTests(unittest.TestCase):
    def test_library_window_without_tricks(self):
        text = "\n".join(r[0] for r in overlay.rows_for(game(tricks=TRICKS)))
        self.assertIn("Bibliothek 30", text)
        self.assertNotIn("Gegner offen", text)
        self.assertNotIn("Trick 1W", text)


class GeometryTests(unittest.TestCase):
    @staticmethod
    def parse(geo):
        size, x, y = geo.split("+")
        w, h = size.split("x")
        return int(w), int(h), int(x), int(y)

    def test_control_window_on_the_left_edge(self):
        w, h, x, y = self.parse(overlay.control_geometry())
        self.assertEqual(x, 0)
        self.assertGreater(w, 100)
        self.assertGreaterEqual(y, 0)

    def test_trick_window_left_below_the_control_window(self):
        cw, ch, cx, cy = self.parse(overlay.control_geometry())
        w, h, x, y = self.parse(overlay.trick_geometry())
        self.assertEqual(x, 0)
        self.assertGreaterEqual(y, cy + ch)

    def test_main_window_on_the_right_edge(self):
        w, h, x, y = self.parse(overlay.main_geometry(1920))
        self.assertEqual(x + w, 1920 - 20)


class TextTests(unittest.TestCase):
    def test_help_and_readme_mention_the_control_window(self):
        import pathlib
        from components.howitworks import render_help_page
        page = render_help_page()
        self.assertIn("Steuerfenster", page)
        self.assertIn("Trick-Warner", page)
        readme = (pathlib.Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
        self.assertIn("Steuerfenster", readme)
        self.assertIn("Trick-Warner", readme)


if __name__ == "__main__":
    unittest.main()
