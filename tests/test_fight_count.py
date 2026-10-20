"""Auswahl der Kampfzahl in der Kampf-Leiste des Berichts (Spiele je Modus), wird an den Kampf durchgereicht."""
import pathlib
import tempfile
import unittest

from components.battle_server import FIGHT_COUNTS, start_battle
from components.report import FIGHT_BAR, FIGHT_JS
from tests.fixtures import args_for


class Job:
    def start(self, work):
        work(lambda message: None)
        return True


class BarTests(unittest.TestCase):
    def test_select_with_counts(self):
        self.assertIn('id="fbcount"', FIGHT_BAR)
        for n in FIGHT_COUNTS:
            self.assertIn(f'<option value="{n}"', FIGHT_BAR)
        self.assertIn('<option value="500" selected>', FIGHT_BAR)

    def test_script_sends_the_count(self):
        self.assertIn("games:", FIGHT_JS)
        self.assertIn("fbcount", FIGHT_JS)


class StartTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = pathlib.Path(self.tmp.name)
        (self.folder / "_enemydeck_walls.txt").write_text("Deck\n17 Plains\n", encoding="utf-8")
        self.seen = []
        self.args = args_for(["deck.txt", "--kaempfe", "500"])
        self.app = {"last_entries": [{"name": "Wir"}], "last_args": self.args, "job": Job(),
                    "battle": lambda entries, enemy, args, progress: self.seen.append(args.kaempfe) or "<p>K</p>"}

    def tearDown(self):
        self.tmp.cleanup()

    def test_chosen_count_is_used(self):
        code, _answer = start_battle(self.app, {"enemy": "_enemydeck_walls.txt", "games": 100}, self.folder)
        self.assertEqual((code, self.seen), (200, [100]))
        self.assertEqual(self.args.kaempfe, 500)  # die Einstellung des Berichts bleibt

    def test_count_as_text(self):
        start_battle(self.app, {"enemy": "_enemydeck_walls.txt", "games": "250"}, self.folder)
        self.assertEqual(self.seen, [250])

    def test_without_count_uses_the_setting(self):
        start_battle(self.app, {"enemy": "_enemydeck_walls.txt"}, self.folder)
        self.assertEqual(self.seen, [500])

    def test_invalid_count(self):
        for bad in (0, -5, "viele", 100000):
            code, answer = start_battle(self.app, {"enemy": "_enemydeck_walls.txt", "games": bad}, self.folder)
            self.assertEqual((code, answer["ok"]), (400, False), bad)
        self.assertEqual(self.seen, [])


if __name__ == "__main__":
    unittest.main()
