"""Im Spiel: Chance auf eine "spielbare Bombe" als naechste Karte (Nutzer 14.11.2026): Bomben (eigene Bewertung
Matchwinner) in der Bibliothek, die mit den eigenen Laendern auf dem Spielfeld schon bezahlbar sind. Steht in der
grossen Ansicht und im minimierten Kasten, aber nur, wenn das Deck ueberhaupt eine Bombe hat."""
import unittest

from components import gamestate as gs
from components import overlay
from components.i18n import set_lang
from tests.test_gamestate import PLAY, START, feed, info


def view(ratings):
    # Bibliothek 12: Bear x2 {W}, Spell {W} spielbar; Hasty {R}, Bolt {R} nicht (nur eine Plains)
    return gs.game_view(feed(gs.GameState(), *START, PLAY), info(), ratings)


def group(v, key):
    return {r["key"]: r for r in v["groups"]}.get(key)


class BombGroupTests(unittest.TestCase):
    def test_castable_bombs_only(self):
        g = group(view({"Test Bear": "matchwinner", "Test Bolt": "matchwinner"}), "bomb")
        self.assertEqual(g["label"], "Spielbare Bombe")
        self.assertEqual(g["n"], 2)  # Bear x2; Bolt ist eine Bombe, aber mit {R} nicht bezahlbar
        self.assertAlmostEqual(g["next"], 2 / 12)

    def test_bomb_in_deck_but_not_castable_yet(self):
        g = group(view({"Test Bolt": "matchwinner"}), "bomb")
        self.assertEqual((g["n"], g["next"]), (0, 0))

    def test_only_matchwinner_counts(self):
        v = view({"Test Bear": "splashworthy", "Test Spell": "mustplay", "Test Hasty": "playable"})
        self.assertIsNone(group(v, "bomb"))  # Deck ohne Bombe: keine Zeile

    def test_without_ratings_unchanged(self):
        self.assertIsNone(group(gs.game_view(feed(gs.GameState(), *START, PLAY), info()), "bomb"))
        self.assertEqual(view({})["groups"][0]["key"], "castable")


class BombOverlayTests(unittest.TestCase):
    def tearDown(self):
        set_lang("de")

    def test_mini_and_expanded(self):
        snap = {"game": view({"Test Bear": "matchwinner"})}
        mini = overlay.mini_rows(snap)
        self.assertIn(("Spielbare Bombe 17 %", "hint"), mini)
        self.assertEqual([r[0].split()[0] for r in mini[:3]], ["Removal", "Land", "Kreatur"])  # Reihenfolge wie bisher
        text = "\n".join(r[0] for r in overlay.rows_for(snap))
        self.assertIn("Spielbare Bombe: 2 übrig", text)

    def test_mini_without_bomb_in_deck(self):
        mini = overlay.mini_rows({"game": view({})})
        self.assertFalse(any("Bombe" in r[0] for r in mini))

    def test_english(self):
        set_lang("en")
        mini = overlay.mini_rows({"game": view({"Test Bear": "matchwinner"})})
        self.assertIn("Castable bomb 17%", [r[0] for r in mini])


if __name__ == "__main__":
    unittest.main()
