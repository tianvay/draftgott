"""Trick-Warner aufgeteilt in Instants, Flash-Kreaturen und andere Karten mit Flash (Nutzer 14.11.2026)."""
import unittest

from components import overlay
from tests.i18n_check import english

INSTANT = {"name": "Shock", "cost": "{R}", "flash": False, "type": "Instant", "removal": 1}
CREATURE = {"name": "Ambush Bear", "cost": "{1}{G}", "flash": True, "type": "Creature — Bear", "removal": 0}
AURA = {"name": "Quick Shield", "cost": "{W}", "flash": True, "type": "Enchantment — Aura", "removal": 0}
OLD = {"name": "Old Trick", "cost": "{U}", "removal": 0}  # aeltere Daten ohne flash/type


def tricks(*cards):
    return {"open": 3, "lands": 4, "colors": {"R": 1, "G": 1, "W": 1}, "now": list(cards)}


class TrickGroupTests(unittest.TestCase):
    def test_groups_in_fixed_order(self):
        rows = overlay.trick_rows(tricks(CREATURE, INSTANT, AURA))
        self.assertEqual([r for r in rows[1:]], [
            ("Instants (1)", "group"), ("• Shock  {R}  R1", "arch"),
            ("Flash-Kreaturen (1)", "group"), ("• Ambush Bear  {1}{G}", "color"),
            ("Andere mit Flash (1)", "group"), ("• Quick Shield  {W}", "color")])

    def test_empty_groups_are_left_out(self):
        rows = overlay.trick_rows(tricks(INSTANT))
        groups = [r[0] for r in rows if r[1] == "group"]
        self.assertEqual(groups, ["Instants (1)"])

    def test_old_data_counts_as_instant(self):
        rows = overlay.trick_rows(tricks(OLD, CREATURE))
        self.assertEqual(rows[1:3], [("Instants (1)", "group"), ("• Old Trick  {U}", "color")])

    def test_group_rows_have_no_card_tip(self):
        snap = {"game": {"active": True, "turn": 2, "tricks": tricks(INSTANT, CREATURE)}}
        tips = overlay.trick_tips(snap)
        for line, tag in overlay.trick_window_rows(snap):
            if tag == "group":
                self.assertIsNone(overlay.tip_for_line(line, tips))

    def test_english(self):
        with english():
            groups = [r[0] for r in overlay.trick_rows(tricks(INSTANT, CREATURE, AURA)) if r[1] == "group"]
        self.assertEqual(groups, ["Instants (1)", "Flash creatures (1)", "Other flash cards (1)"])


if __name__ == "__main__":
    unittest.main()
