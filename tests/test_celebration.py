"""Seitenfenster: kleine Feier (Pokal und Konfetti) beim 4. Sieg, Nachricht zur "Hall of Game" der Gegnerdecks."""
import random
import unittest

from components import overlay

NAME = "drafted_TRK_4wins_whitered_2026-11-12_1957.txt"


class TriggerTests(unittest.TestCase):
    def test_celebrate_once_per_new_deck(self):
        self.assertEqual(overlay.new_celebration(None, {"enemy_saved": NAME}), NAME)
        self.assertIsNone(overlay.new_celebration(NAME, {"enemy_saved": NAME}))  # schon gefeiert
        self.assertIsNone(overlay.new_celebration(None, {"enemy_saved": None}))
        self.assertIsNone(overlay.new_celebration(None, None))
        self.assertEqual(overlay.new_celebration(NAME, {"enemy_saved": "anderes.txt"}), "anderes.txt")


class TextTests(unittest.TestCase):
    def test_lines(self):
        lines = overlay.celebration_lines(NAME)
        text = " ".join(lines)
        self.assertIn("4 Siege", text)
        self.assertIn("Hall of Game", text)
        self.assertIn("drafted_TRK_4wins_whitered_2026-11-12_1957", text)
        self.assertTrue(all(ord(ch) <= 0xFFFF for ch in text))  # tkinter (Tk 8.6) kann keine Emoji ab U+10000

    def test_rows_mention_the_hall_of_game(self):
        rows = overlay.rows_for({"status": "idle", "message": "x", "enemy_saved": NAME})
        self.assertIn("Hall of Game", rows[0][0])
        self.assertTrue(all(ord(ch) <= 0xFFFF for r in rows for ch in r[0]))


class ConfettiTests(unittest.TestCase):
    def test_make_and_fall(self):
        parts = overlay.make_confetti(40, 380, 320, random.Random(1))
        self.assertEqual(len(parts), 40)
        self.assertTrue(all(p["y"] < 0 for p in parts))  # starten oberhalb
        self.assertTrue(all(p["color"] in overlay.CONFETTI_COLORS for p in parts))
        before = [p["y"] for p in parts]
        overlay.step_confetti(parts, 0.5)
        self.assertTrue(all(p["y"] > b for p, b in zip(parts, before)))  # fallen nach unten
        for _ in range(200):
            overlay.step_confetti(parts, 0.1)
        self.assertTrue(all(p["y"] > 320 for p in parts))  # irgendwann unten raus

    def test_same_seed_same_confetti(self):
        a = overlay.make_confetti(5, 100, 100, random.Random(7))
        b = overlay.make_confetti(5, 100, 100, random.Random(7))
        self.assertEqual(a, b)


class PageTests(unittest.TestCase):
    def test_page_and_help(self):
        from components.drafthelper import render_page
        from components.howitworks import render_help_page
        self.assertIn("Hall of Game", render_page())
        self.assertIn("Hall of Game", render_help_page())


if __name__ == "__main__":
    unittest.main()
