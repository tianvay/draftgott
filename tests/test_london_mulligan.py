"""London-Mulligan (103.5): immer 7 Karten ziehen, nach k Mulligans k davon unter die Bibliothek. Behalten wird die
Auswahl ohne Mulligan-Grund, bei Gleichstand der Laenderanteil am naechsten am Deck (lieber ein Land mehr), dann die
meisten mit den behaltenen Laendern bezahlbaren Karten, dann die geringsten Manakosten. Landcycling-Ausnahme: eine Hand
mit 6 oder 7 Karten, mindestens 2 Laendern, einer Karte mit Basic Landcycling und einer anderen Nichtland-Karte mit
Manawert hoechstens 3 wird behalten ("6 oder mehr Laender" bleibt ein Grund). Der Gegner gibt nie auf."""
import random
import unittest
from unittest import mock

from components import battle as bt
from components import mulligan as mu
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS, BEAR, BIG = W["Plains"], W["Test Bear"], W["Test Big"]


def make(name, type_line, cost, cmc, text, power=None, toughness=None, colors="W"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, [], power, toughness))[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


MOUNTAIN = land("Mountain", "R")
CYCLER = make("Hexhaven Battalion", "Sorcery", "{5}{W}", 6, "Create three 2/2 colorless Wizard Soldier creature tokens "
              "named Cadet.\nBasic landcycling {2} ({2}, Discard this card: Search your library for a basic land card, "
              "reveal it, put it into your hand, then shuffle.)")
DRAKE = make("Drake", CRE, "{2}{W}", 3, "", "2", "2")
FIVE = make("Five Drop", CRE, "{4}{W}", 5, "", "5", "5")


class LandcyclingKeepTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(CYCLER.cycle_target, "basic")

    def test_keep_with_two_lands_cycler_and_cheap_card(self):
        hand = [PLAINS, PLAINS, CYCLER, DRAKE, FIVE, FIVE, FIVE]
        self.assertEqual(mu.mulligan_reasons(hand), [])

    def test_also_with_wrong_colors(self):
        hand = [MOUNTAIN, MOUNTAIN, CYCLER, DRAKE, FIVE, FIVE]  # 6 Karten, keine weisse Quelle
        self.assertEqual(mu.mulligan_reasons(hand), [])

    def test_not_with_one_land(self):
        hand = [PLAINS, CYCLER, DRAKE, FIVE, FIVE, FIVE, FIVE]
        self.assertIn(mu.MULL_LANDS_LOW, mu.mulligan_reasons(hand))

    def test_not_without_another_cheap_card(self):
        hand = [PLAINS, PLAINS, CYCLER, FIVE, FIVE, FIVE, FIVE]
        self.assertIn(mu.MULL_LANDS_LOW, mu.mulligan_reasons(hand))

    def test_not_with_five_cards(self):
        hand = [PLAINS, PLAINS, CYCLER, DRAKE, FIVE]
        self.assertIn(mu.MULL_LANDS_LOW, mu.mulligan_reasons(hand))

    def test_six_lands_stay_a_mulligan(self):
        hand = [PLAINS] * 6 + [CYCLER]
        self.assertIn(mu.MULL_LANDS_HIGH, mu.mulligan_reasons(hand))


class BottomChoiceTests(unittest.TestCase):
    def test_bottom_makes_the_hand_keepable(self):
        hand = [PLAINS] * 6 + [BEAR]  # 6 Laender: Mulligan; behalten 6 Karten mit 5 Laendern? weiterhin zu viele
        kept, bottom = mu.choose_keep(hand, 1, 0.4)
        self.assertEqual(sorted(c.name for c in bottom), ["Plains"])
        self.assertEqual(sum(c.is_land for c in kept), 5)

    def test_land_share_closest_to_the_deck(self):
        hand = [PLAINS] * 4 + [BEAR] * 3
        kept, bottom = mu.choose_keep(hand, 1, 17 / 40)  # 6 Karten: 2,55 Laender -> 3 (lieber eins mehr)
        self.assertEqual((sum(c.is_land for c in kept), [c.name for c in bottom]), (3, ["Plains"]))
        kept, bottom = mu.choose_keep(hand, 2, 17 / 40)  # 5 Karten: 2,1 Laender -> 2
        self.assertEqual(sum(c.is_land for c in kept), 2)

    def test_more_castable_then_cheaper(self):
        hand = [PLAINS] * 3 + [BEAR, BEAR, BIG, FIVE]
        kept, bottom = mu.choose_keep(hand, 1, 0.5)  # 3 Laender bleiben; Five Drop (am teuersten) geht
        self.assertEqual([c.name for c in bottom], ["Five Drop"])

    def test_no_reason_beats_land_share(self):
        hand = [PLAINS, PLAINS, PLAINS, BEAR, BEAR, FIVE, FIVE]
        kept, _bottom = mu.choose_keep(hand, 1, 0.3)  # 1,8 Laender waeren am naechsten, 2 Laender haben aber einen Grund
        self.assertEqual((sum(c.is_land for c in kept), mu.mulligan_reasons(kept)), (3, []))


class DealTests(unittest.TestCase):
    def test_draws_seven_and_bottoms(self):
        deck = [PLAINS] * 6 + [BEAR] + [PLAINS] * 3 + [BEAR] * 30  # erste 7: 6 Laender -> Mulligan
        order = iter([list(deck), [PLAINS] * 6 + [BEAR] + [BEAR] * 33])

        def shuffle(x):
            x[:] = next(order)

        with mock.patch("components.mulligan.random.shuffle", shuffle):
            hand, library, mulls, first = mu.deal_opening(deck, True, 5)
        self.assertEqual((len(hand), mulls, first), (6, 1, [mu.MULL_LANDS_HIGH]))
        self.assertEqual((len(hand) + len(library), library[-1].name), (40, "Plains"))  # unten liegt ein Land

    def test_enemy_never_concedes(self):
        with mock.patch("components.mulligan.mulligan_reasons", lambda hand: ["immer Mulligan"]):
            hand, library, mulls, _f = mu.deal_opening([PLAINS] * 17 + [BEAR] * 23, True, 5, keep_at_min=True)
            gone, _l, mulls2, _f2 = mu.deal_opening([PLAINS] * 17 + [BEAR] * 23, True, 5)
        self.assertEqual((len(hand), len(library), mulls, gone), (5, 35, 2, None))

    def test_cycler_hand_kept_in_a_real_deal(self):
        deck = [PLAINS, PLAINS, CYCLER, DRAKE, FIVE, FIVE, FIVE] + [PLAINS] * 15 + [FIVE] * 18
        with mock.patch("components.mulligan.random.shuffle", lambda x: None):
            hand, _library, mulls, first = mu.deal_opening(deck, True, 5)
        self.assertEqual((mulls, len(hand), first), (0, 7, []))

    def test_battle_player_uses_it(self):
        random.seed(5)
        p = bt.Player("Wir", [PLAINS] * 17 + [BEAR] * 23)
        self.assertEqual(len(p.hand) + len(p.library), 40)


if __name__ == "__main__":
    unittest.main()
