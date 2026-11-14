"""Im Spiel auf Englisch: die Gruppen der Ziehchancen (Spielbar, Land, Kreatur, Removal, Farbquellen) kommen
uebersetzt aus gamestate, auf Deutsch bleiben sie wie bisher (Nutzer 14.11.2026: "Spielbar", "Kreatur",
"W-Quelle" standen im englischen Stream)."""
import unittest

from components import gamestate as gs
from components import overlay
from tests.i18n_check import english, german_leftovers
from tests.test_gamestate import PLAY, START, feed, info


def view():
    return gs.game_view(feed(gs.GameState(), *START, PLAY), info())


class GameLabelTests(unittest.TestCase):
    def test_german_labels_unchanged(self):
        labels = {g["key"]: g["label"] for g in view()["groups"]}
        self.assertEqual((labels["castable"], labels["land"], labels["creature"], labels["removal"]),
                         ("Spielbar", "Land", "Kreatur", "Removal"))
        self.assertEqual(labels["src_W"], "W-Quelle")

    def test_english_labels(self):
        with english():
            labels = {g["key"]: g["label"] for g in view()["groups"]}
        self.assertEqual((labels["castable"], labels["land"], labels["creature"], labels["removal"]),
                         ("Castable", "Land", "Creature", "Removal"))
        self.assertEqual(labels["src_W"], "W source")

    def test_english_game_rows_without_german(self):
        with english():
            text = "\n".join(r[0] for r in overlay.rows_for({"game": view()}))
        self.assertEqual(german_leftovers(text, allow=("Test Bear", "Test Spell", "Test Hasty", "Test Bolt")), [])


if __name__ == "__main__":
    unittest.main()
