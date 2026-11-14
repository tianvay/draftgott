"""Trick-Warner: Hat der Gegner keine Handkarten, kann er keine Tricks wirken; dann zeigt der Trick-Warner keine
Karten, nur den Hinweis (Nutzer 14.11.2026)."""
import unittest

from components import gamestate as gs
from components import overlay
from tests.i18n_check import english, german_leftovers
from tests.test_gamestate import START, feed, gre, state, zone
from tests.test_tricks import BOARD, view

EMPTY_HAND = gre(state(zones=[zone(31, "ZoneType_Hand", 1)]))  # Arena schickt die leere Zone ohne Kennungen


class OpponentHandTests(unittest.TestCase):
    def test_opponent_hand_size(self):
        g = feed(gs.GameState(), *START)
        self.assertEqual(g.opponent_hand_size(), 2)
        self.assertEqual(g.hand_size(), 7)  # eigene Hand unveraendert
        feed(g, EMPTY_HAND)
        self.assertEqual(g.opponent_hand_size(), 0)

    def test_unknown_without_seat_or_zone(self):
        self.assertIsNone(gs.GameState().opponent_hand_size())


class TricksViewTests(unittest.TestCase):
    def test_view_has_hand_count(self):
        v = view(feed(gs.GameState(), *START, BOARD))
        self.assertEqual(v["hand"], 2)
        self.assertTrue(v["now"])

    def test_no_tricks_without_hand_cards(self):
        v = view(feed(gs.GameState(), *START, BOARD, EMPTY_HAND))
        self.assertEqual(v["hand"], 0)
        self.assertEqual(v["open"], 2)  # das offene Mana bleibt sichtbar
        self.assertEqual((v["now"], v["next"]), ([], []))


TR = {"open": 2, "lands": 3, "colors": {"W": 1}, "spell_colors": [], "hand": 0, "now": [], "next": []}


class OverlayTests(unittest.TestCase):
    def test_trick_rows_without_hand_cards(self):
        rows = overlay.trick_rows(TR)
        text = "\n".join(r[0] for r in rows)
        self.assertIn("Gegner hat keine Handkarten: keine Tricks", text)
        self.assertNotIn("Keine Instants", text)
        self.assertEqual(len(rows), 2)

    def test_hand_count_in_the_head(self):
        tr = dict(TR, hand=3, now=[{"name": "Trick W", "cost": "{W}", "removal": 0}])
        self.assertIn("Hand 3", overlay.trick_rows(tr)[0][0])

    def test_old_data_without_hand_count(self):
        tr = dict(TR, now=[{"name": "Trick W", "cost": "{W}", "removal": 0}])
        del tr["hand"]
        text = "\n".join(r[0] for r in overlay.trick_rows(tr))
        self.assertIn("Trick W", text)
        self.assertNotIn("Hand", text)

    def test_mini_box(self):
        snap = {"game": {"active": True, "groups": [], "tricks": TR}}
        self.assertIn(("Gegner ohne Handkarten", "head"), overlay.mini_rows(snap))

    def test_english(self):
        snap = {"game": {"active": True, "groups": [], "tricks": TR}}
        with english():
            text = "\n".join(r[0] for r in overlay.trick_rows(TR) + overlay.trick_rows(dict(TR, hand=3))
                             + overlay.mini_rows(snap))
        self.assertEqual(german_leftovers(text), [])
        self.assertIn("Opponent has no cards in hand", text)


if __name__ == "__main__":
    unittest.main()
