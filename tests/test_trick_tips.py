"""Trick-Warner: beim Ueberfahren mit der Maus erscheint der Kartentext des Tricks (Kosten, Typzeile, Text,
Staerke/Widerstand), damit man auch unbekannte Karten einordnen kann."""
import unittest

from components import overlay
from components import tricks


def sc(name, type_line, cost, text, **kw):
    return dict({"name": name, "type_line": type_line, "mana_cost": cost, "cmc": 1, "colors": ["W"],
                 "oracle_text": text, "keywords": []}, **kw)


class TrickCardTextTests(unittest.TestCase):
    def test_trick_cards_carry_type_text_and_pt(self):
        bear = sc("Flash Bear", "Creature — Bear", "{2}{G}", "Flash\nWhen this enters, tap target creature.",
                  keywords=["Flash"], power="2", toughness="2")
        trick = sc("Trick W", "Instant", "{W}", "Target creature gets +2/+2 until end of turn.")
        out = {c["name"]: c for c in tricks.trick_cards([bear, trick])}
        self.assertEqual(out["Flash Bear"]["type"], "Creature — Bear")
        self.assertEqual(out["Flash Bear"]["text"], "Flash\nWhen this enters, tap target creature.")
        self.assertEqual(out["Flash Bear"]["pt"], "2/2")
        self.assertEqual(out["Trick W"]["type"], "Instant")
        self.assertEqual(out["Trick W"]["pt"], "")

    def test_double_faced_uses_front_text(self):
        mdfc = {"name": "Front // Back", "type_line": "Instant // Land", "cmc": 2, "colors": ["W"],
                "card_faces": [{"name": "Front", "type_line": "Instant", "mana_cost": "{1}{W}", "colors": ["W"],
                                "oracle_text": "Tap target creature."},
                               {"name": "Back", "type_line": "Land", "mana_cost": "", "oracle_text": "{T}: Add {W}."}]}
        card = tricks.trick_cards([mdfc])[0]
        self.assertEqual((card["type"], card["text"]), ("Instant", "Tap target creature."))


class TipTests(unittest.TestCase):
    CARD = {"name": "Trick W", "cost": "{W}", "type": "Instant", "text": "Target creature gets +2/+2.", "pt": "",
            "removal": 0, "rating": "filler"}

    def test_tip_shows_name_cost_type_and_text(self):
        tip = overlay.trick_tip(self.CARD)
        lines = tip.split("\n")
        self.assertEqual(lines[0], "Trick W  {W}")
        self.assertEqual(lines[1], "Instant")
        self.assertIn("Target creature gets +2/+2.", tip)

    def test_tip_with_pt_and_removal(self):
        tip = overlay.trick_tip(dict(self.CARD, type="Creature — Bear", pt="2/2", removal=1.5))
        self.assertIn("Creature — Bear · 2/2", tip)
        self.assertIn("Removal 1,5 P.", tip)

    def test_tip_without_text_data(self):
        tip = overlay.trick_tip({"name": "Old", "cost": "", "removal": 0})
        self.assertTrue(tip.startswith("Old  {0}"))
        self.assertIn("Kein Kartentext", tip)

    def test_tips_and_line_lookup(self):
        other = dict(self.CARD, name="Trick", text="Other.")
        snap = {"game": {"active": True, "tricks": {"open": 1, "lands": 2, "now": [self.CARD, other]}}}
        tips = overlay.trick_tips(snap)
        self.assertEqual(set(tips), {"Trick W", "Trick"})
        rows = overlay.trick_window_rows(snap)
        lines = [line for line, _ in rows if line.startswith("• ")]
        self.assertEqual(overlay.tip_for_line(lines[0], tips), tips["Trick W"])
        self.assertEqual(overlay.tip_for_line(lines[1], tips), tips["Trick"])  # kein Verwechseln mit "Trick W"
        self.assertIsNone(overlay.tip_for_line(rows[0][0], tips))
        self.assertEqual(overlay.trick_tips({"game": {"active": False}}), {})


if __name__ == "__main__":
    unittest.main()
