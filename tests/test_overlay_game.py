"""Im Spiel: spielbare Karten mit dem aktuellen Mana, Knopf "Deck uebernehmen" verschwindet, kleiner Kasten
(minimiert) mit den Chancen auf Removal, Land und Kreatur."""
import unittest

from components import gamestate as gs
from components import overlay
from tests.test_gamestate import PLAY, START, feed, gre, info, obj, state, zone


class CastableTests(unittest.TestCase):
    def test_castable_with_lands_on_the_battlefield(self):
        v = gs.game_view(feed(gs.GameState(), *START, PLAY), info())
        self.assertEqual(v["mana"], {"lands": 1, "colors": {"W": 1}})
        by = {r["key"]: r for r in v["groups"]}
        # Bibliothek 12: Bear x2 {W}, Spell {W} spielbar; Hasty {R}, Bolt {R} nicht (nur eine Plains)
        self.assertEqual(by["castable"]["n"], 3)
        self.assertAlmostEqual(by["castable"]["next"], 3 / 12)
        self.assertEqual(v["groups"][0]["key"], "castable")
        cards = {c["name"]: c["castable"] for c in v["cards"]}
        self.assertEqual(cards, {"Test Bear": True, "Test Spell": True, "Test Hasty": False, "Test Bolt": False,
                                 "Plains": False, "Mountain": False})

    def test_no_lands_no_castable_cards(self):
        v = gs.game_view(feed(gs.GameState(), *START), info())
        self.assertEqual(v["mana"], {"lands": 0, "colors": {}})
        self.assertEqual({r["key"]: r for r in v["groups"]}["castable"]["n"], 0)

    def test_opponent_lands_do_not_count(self):
        theirs = gre(state(zones=[zone(28, "ZoneType_Battlefield", None, [8, 60])],
                           objects=[dict(obj(60, 302, 28, owner=1), controllerSeatId=1)]))
        v = gs.game_view(feed(gs.GameState(), *START, PLAY, theirs), info())
        self.assertEqual(v["mana"], {"lands": 1, "colors": {"W": 1}})

    def test_controlled_land_counts(self):
        stolen = gre(state(zones=[zone(28, "ZoneType_Battlefield", None, [8, 61])],
                           objects=[dict(obj(61, 302, 28, owner=1), controllerSeatId=2)]))
        v = gs.game_view(feed(gs.GameState(), *START, PLAY, stolen), info())
        self.assertEqual(v["mana"], {"lands": 2, "colors": {"W": 1, "R": 1}})
        self.assertEqual({r["key"]: r for r in v["groups"]}["castable"]["n"], 5)  # jetzt auch Hasty und Bolt

    def test_can_cast(self):
        self.assertTrue(gs.can_cast("{1}{W}", [{"W"}, {"R"}]))
        self.assertFalse(gs.can_cast("{W}{W}", [{"W"}, {"R"}]))
        self.assertTrue(gs.can_cast("{R/W}", [{"W"}]))
        self.assertFalse(gs.can_cast("", [{"W"}]))  # ohne Manakosten nicht normal spielbar
        self.assertTrue(gs.can_cast("{X}{R}", [{"R"}]))


class OverlayTests(unittest.TestCase):
    def view(self):
        return gs.game_view(feed(gs.GameState(), *START, PLAY), info())

    def test_deck_button_hidden_during_the_game(self):
        snap = {"complete": True, "deck": {"ready": True, "applied": False, "main": 40, "side": 2},
                "game": self.view()}
        self.assertIsNone(overlay.deck_button(snap))
        snap["game"] = {"active": False}
        self.assertIsNotNone(overlay.deck_button(snap))

    def test_expanded_rows_show_castable_and_mana(self):
        text = "\n".join(r[0] for r in overlay.rows_for({"game": self.view()}))
        self.assertIn("Spielbar", text)
        self.assertIn("25 %", text)
        self.assertIn("Mana 1", text)
        self.assertIn("✓ 2× Test Bear", text)  # spielbare Karten mit Haken
        self.assertNotIn("✓ 1× Test Bolt", text)

    def test_mini_rows_in_game(self):
        rows = overlay.mini_rows({"game": self.view()})
        text = " ".join(r[0] for r in rows)
        for word in ("Removal", "Land", "Kreatur"):
            self.assertIn(word, text)
        self.assertNotIn("Spielbar", text)
        self.assertIn("58 %", text)  # 7 Laender von 12

    def test_mini_rows_in_draft_and_without_data(self):
        snap = {"status": "pack", "pick": 5, "detect": {"main": "BR", "scores": [
            {"colors": "BR", "name": "Sacrifice", "score": 5}]},
                "pack": [{"name": "Bolt", "points": 6, "level": "arch"}]}
        text = " ".join(r[0] for r in overlay.mini_rows(snap))
        self.assertIn("Pick 5", text)
        self.assertIn("Sacrifice", text)
        self.assertIn("Bolt", text)
        self.assertTrue(overlay.mini_rows(None))


class TextTests(unittest.TestCase):
    def test_help_readme_and_page(self):
        import pathlib
        from components.drafthelper import render_page
        from components.howitworks import render_help_page
        help_page = render_help_page()
        self.assertIn("Spielbar", help_page)
        self.assertIn("minimieren", help_page)
        readme = (pathlib.Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
        self.assertIn("Seitenfenster minimieren", readme)
        page = render_page()
        self.assertIn("c.castable", page)
        self.assertIn("&&!playing", page)


if __name__ == "__main__":
    unittest.main()
