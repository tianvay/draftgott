"""Pack-Rangliste: Synergie zaehlt nur fuer Karten, die in den erkannten Archetyp passen (Farben, Zuordnung oder
farblos). Sonst schlug draftgott fuer W/B eine gruene MustPlay-Karte mit Synergie vor statt der farblosen
Archetyp-Karte (Nutzer 14.11.2026: Dominion Supervisor vor Class-F Shuttlecraft)."""
import unittest
from unittest import mock

from components import cardarchetypes as ca

SYN = {"gives": {}, "wants": {}}
GREEN = {"name": "Green Doctor", "colors": ["G"], "syn": SYN}
SHIP = {"name": "Shuttle", "colors": [], "syn": SYN}
SPY = {"name": "Black Spy", "colors": ["B"], "syn": SYN}
GADGET = {"name": "Gadget", "colors": [], "syn": SYN}
RATINGS = {"Green Doctor": "mustplay", "Shuttle": "filler", "Black Spy": "mustplay", "Gadget": "filler"}
ASSIGN = {"Shuttle": ["WB"]}
BONUS = {"Green Doctor": 1.7, "Shuttle": 0.1, "Black Spy": 0.1, "Gadget": 1.0}


def fake_bonus(pool, card):
    return BONUS[card["name"]], []


class OffColorSynergyTests(unittest.TestCase):
    def rank(self, pack, main="WB"):
        with mock.patch.object(ca.synergy, "pick_bonus", fake_bonus):
            return ca.rank(pack, RATINGS, ASSIGN, main, pool=[])

    def test_off_color_card_gets_no_synergy_points(self):
        out = self.rank([GREEN, SHIP, SPY])
        self.assertEqual([c["name"] for c in out], ["Black Spy", "Shuttle", "Green Doctor"])
        green = next(c for c in out if c["name"] == "Green Doctor")
        self.assertEqual(green["points"], 3)
        self.assertEqual(green["synergy"], 1.7)  # bleibt sichtbar, zaehlt aber nicht

    def test_colorless_card_keeps_synergy(self):
        gadget = next(c for c in self.rank([GADGET]) if c["name"] == "Gadget")
        self.assertEqual(gadget["points"], 2.0)  # Filler 1 + Synergie 1

    def test_without_archetype_synergy_counts_for_all(self):
        green = next(c for c in self.rank([GREEN], main=None) if c["name"] == "Green Doctor")
        self.assertEqual(green["points"], 4.7)


if __name__ == "__main__":
    unittest.main()
