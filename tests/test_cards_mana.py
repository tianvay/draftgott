import unittest

from components.cards import card_info
from components.mana import can_cast_all, cost_alternatives, has_two_colors, land_key, mana_value, required_colors
from components.mulligan import MULL_COLORS, MULL_LANDS_HIGH, MULL_LANDS_LOW, mulligan_reasons
from tests.fixtures import CARDS


def card(name):
    return card_info(CARDS[name])[0]


class CardInfoTests(unittest.TestCase):
    def test_basic_land(self):
        c = card("Plains")
        self.assertTrue(c.is_land)
        self.assertEqual(c.land_colors, ("W",))
        self.assertEqual(c.tap_mode, "no")

    def test_creature_stats_and_flags(self):
        c = card("Test Hasty")
        self.assertTrue(c.is_creature)
        self.assertEqual((c.power, c.toughness, c.mv), (3, 1, 1))
        self.assertTrue(c.haste)
        self.assertFalse(c.defender)

    def test_defender_keyword(self):
        c = card("Test Defender")
        self.assertTrue(c.defender)
        self.assertFalse(c.haste)

    def test_plain_creature_has_neither_haste_nor_defender(self):
        c = card("Test Bear")
        self.assertFalse(c.haste or c.defender)

    def test_instant_is_not_a_creature(self):
        c = card("Test Spell")
        self.assertTrue(c.is_instant_sorcery)
        self.assertFalse(c.is_creature)
        self.assertEqual((c.power, c.toughness), (0, 0))

    def test_shown_text_mentions_haste_and_defender(self):
        self.assertIn("Haste", card_info(CARDS["Test Hasty"])[1])
        self.assertIn("Defender", card_info(CARDS["Test Defender"])[1])


class ManaTests(unittest.TestCase):
    def test_mana_value(self):
        self.assertEqual(mana_value("{3}{W}{W}"), 5)
        self.assertEqual(mana_value("{X}{G}{G}"), 2)
        self.assertEqual(mana_value("{2/W}"), 2)
        self.assertEqual(mana_value(""), 0)

    def test_hybrid_has_two_ways_to_pay(self):
        self.assertEqual(len(cost_alternatives("{W/B}")), 2)

    def test_gold_card_needs_both_colors(self):
        alts = card("Test Gold").alts
        only_white = land_key([("W",), ("W",)])
        both = land_key([("W",), ("B",)])
        self.assertFalse(can_cast_all((alts,), only_white))
        self.assertTrue(can_cast_all((alts,), both))

    def test_two_cards_need_enough_lands(self):
        bear = card("Test Bear").alts
        self.assertTrue(can_cast_all((bear, bear), land_key([("W",), ("W",)])))
        self.assertFalse(can_cast_all((bear, bear), land_key([("W",)])))

    def test_required_colors(self):
        self.assertEqual(required_colors(card("Test Gold")), {"W", "B"})
        self.assertEqual(required_colors(card("Test Bear")), {"W"})

    def test_has_two_colors(self):
        self.assertTrue(has_two_colors(land_key([("W",), ("B",)])))
        self.assertFalse(has_two_colors(land_key([("W",), ("W",)])))


class MulliganTests(unittest.TestCase):
    def test_keepable_hand(self):
        hand = [card("Plains")] * 3 + [card("Test Bear")] * 4
        self.assertEqual(mulligan_reasons(hand), [])

    def test_six_lands_is_a_mulligan(self):
        hand = [card("Plains")] * 6 + [card("Test Bear")]
        self.assertIn(MULL_LANDS_HIGH, mulligan_reasons(hand))

    def test_no_land_hand(self):
        hand = [card("Test Bear")] * 7
        reasons = mulligan_reasons(hand)
        self.assertIn(MULL_COLORS, reasons)
        self.assertIn(MULL_LANDS_LOW, reasons)

    def test_wrong_colors(self):
        hand = [card("Mountain")] * 3 + [card("Test Bear")] * 4
        self.assertIn(MULL_COLORS, mulligan_reasons(hand))


if __name__ == "__main__":
    unittest.main()
