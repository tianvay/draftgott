"""Gegnerdecks liegen im Ordner enemydecks (ohne Praefix im Dateinamen)."""
import pathlib
import unittest

import mtg_sim
from components.battle_server import ENEMY_DIR, enemy_decks

ROOT = pathlib.Path(__file__).resolve().parent.parent


class EnemyFolderTests(unittest.TestCase):
    def test_project_decks_are_found(self):
        decks = enemy_decks(ROOT)
        self.assertTrue(decks)
        self.assertTrue(all((ROOT / ENEMY_DIR / d["file"]).exists() for d in decks))
        self.assertFalse(any(d["file"].startswith("_enemydeck") for d in decks))
        self.assertEqual(list(ROOT.glob("_enemydeck*.txt")), [])

    def test_gegner_by_file_name(self):
        name = enemy_decks(ROOT)[0]["file"]
        by_name = mtg_sim.load_enemy(name)
        without_txt = mtg_sim.load_enemy(name[:-4])
        in_folder = mtg_sim.load_enemy(f"{ENEMY_DIR}/{name}")
        self.assertEqual(by_name, without_txt)
        self.assertEqual(by_name, in_folder)
        self.assertTrue(by_name["deck"])

    def test_name_without_prefix(self):
        path = ROOT / ENEMY_DIR / "bad_creatures.txt"
        text = path.read_text(encoding="utf-8")
        expected = "bad creatures" if not any(l.lower().startswith("name") for l in text.splitlines()) else None
        if expected:
            self.assertEqual(mtg_sim.enemy_name(path), expected)


if __name__ == "__main__":
    unittest.main()
