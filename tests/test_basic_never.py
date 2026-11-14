"""Standardlaender werden nie empfohlen (Nutzer 14.11.2026): im Pack zaehlen sie wie NeverPlay (0 Punkte, grauer
Rahmen, kein Top-Pick, ganz unten), egal wie sie bewertet sind und ob Scryfall-Daten da sind."""
import unittest

from components import cardarchetypes as ca
from components import overlay, packoverlay


def card(name, colors=(), type_line="", land=False):
    return {"name": name, "colors": list(colors), "type": type_line, "land": land}


PACK = [card("Plains", type_line="Basic Land — Plains", land=True),
        card("Snow-Covered Forest", type_line="Basic Snow Land — Forest", land=True),
        card("Wastes"),  # ohne Scryfall-Daten: nur der Name
        card("Junk", colors="W"),
        card("Evolving Wilds", type_line="Land", land=True)]


class BasicNeverTests(unittest.TestCase):
    def ranked(self, ratings=None):
        return {c["name"]: c for c in ca.rank(PACK, ratings or {}, {}, "WR",
                                              detect={"main": "WR", "scores": []}, pool=[])}

    def test_basics_like_neverplay(self):
        r = self.ranked({"Plains": "matchwinner"})
        for name in ("Plains", "Snow-Covered Forest", "Wastes"):
            self.assertEqual((r[name]["rating"], r[name]["points"], r[name]["hint"]), ("neverplay", 0, ""), msg=name)

    def test_other_lands_and_cards_unchanged(self):
        r = self.ranked()
        self.assertEqual(r["Evolving Wilds"]["rating"], "")
        self.assertGreater(r["Evolving Wilds"]["points"], 0)
        self.assertGreater(r["Junk"]["points"], 0)

    def test_at_the_bottom(self):
        names = [c["name"] for c in ca.rank(PACK, {}, {}, "WR")]
        self.assertEqual(set(names[-3:]), {"Plains", "Snow-Covered Forest", "Wastes"})

    def test_overlays_grey(self):
        r = self.ranked()
        self.assertEqual(packoverlay._frame(r["Plains"]), "never")
        rows = overlay.rows_for({"status": "pack", "pick": 1, "pack": list(r.values()),
                                 "detect": {"main": "WR", "scores": []}})
        self.assertIn("never", [tag for line, tag in rows if "Plains" in line])

    def test_is_basic(self):
        self.assertTrue(ca.is_basic(card("Island")))
        self.assertTrue(ca.is_basic(card("Snow-Covered Swamp", type_line="Basic Snow Land — Swamp")))
        self.assertFalse(ca.is_basic(card("Island Fish Jasconius")))
        self.assertFalse(ca.is_basic(card("Evolving Wilds", type_line="Land")))


if __name__ == "__main__":
    unittest.main()
