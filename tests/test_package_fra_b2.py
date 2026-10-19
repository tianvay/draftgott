"""FRA-Paket B, Spielentscheidungen nach den Vorgaben des Nutzers: Verdant-Kraken-Token loesen Landfall aus (Land);
Guiding Hydra nur mit mindestens 2 anderen eigenen Kreaturen, X = alles freie Mana (mindestens 1), zu Kampfbeginn immer
eine Marke an jede andere Kreatur, wenn mindestens 2 davon profitieren; Curse-Marred Demon sucht nie ein Land, sondern
die teuerste Karte, die wir naechsten Zug spielen koennen, dann zufaellig abwerfen; Pia wirft nur ein Land ab, wenn wir
mehr Laender haben als die teuerste Karte des Decks kostet, eine Verzauberung in der Bibliothek liegt und wir sie
naechsten Zug spielen koennen."""
import random
import unittest
from unittest import mock

from components import battle as bt
from components import simulation as sim
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS, BEAR = W["Plains"], W["Test Bear"]


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="W"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


FOREST, MOUNTAIN = land("Forest", "G"), land("Mountain", "R")
KRAKEN = make("Verdant Kraken", f"Creature {DASH} Plant Kraken", "{4}{G}{G}{G}", 7, "At the beginning of each player's "
              "upkeep, you create a 3/3 green Forest Tentacle land creature token. (It has \"{T}: Add {G}.\" It's "
              "affected by summoning sickness until your next turn.)", "6", "6", colors="G")
LANDFALLER = make("Landfall Scout", CRE, "{1}{R}", 2, "Landfall — Whenever a land you control enters, Landfall Scout "
                  "deals 1 damage to each opponent.", "1", "1", colors="R")
HYDRA = make("Guiding Hydra", f"Creature {DASH} Hydra Horror", "{X}{W}", 1, "This creature enters with X +1/+1 counters "
             "on it.\nAt the beginning of combat on your turn, you may remove a +1/+1 counter from this creature. If you "
             "do, put a +1/+1 counter on each other creature you control.", "1", "0")
DEMON = make("Curse-Marred Demon", f"Creature {DASH} Demon", "{2}{R}{R}", 4, "Flying, trample\nWhen this creature "
             "enters, search your library for a card, put it into your hand, shuffle, then discard a card at random.",
             "4", "4", ["Flying", "Trample"], colors="R")
PIA = make("Pia, Aether Ascetic", f"Legendary Creature {DASH} Human Druid", "{2}{G}", 3, "When Pia enters, you may "
           "discard a card. If you do, search your library for an enchantment card, reveal it, put it into your hand, "
           "then shuffle.", "2", "2", colors="G")
ENCH3 = make("Small Charm", "Enchantment", "{2}{G}", 3, "", colors="G")
ENCH6 = make("Big Charm", "Enchantment", "{5}{G}", 6, "", colors="G")
ENCH9 = make("Huge Charm", "Enchantment", "{8}{G}", 9, "", colors="G")
FIVE = make("Five Drop", CRE, "{4}{W}", 5, "", "5", "5")
SEVEN = make("Seven Drop", CRE, "{6}{W}", 7, "", "7", "7")


def player(name="Wir", library=None, deck=None):
    p = bt.Player(name, deck or [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def pair(deck=None):
    me, opp = player(deck=deck), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


def on_board(p, card, entered=0):
    c = bt.Creature(card, entered)
    c.gy, c.ctl = p.graveyard, p
    p.creatures.append(c)
    return c


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertTrue(HYDRA.x_counters and HYDRA.hydra_spread)
        self.assertTrue(DEMON.etb_tutor_any)
        self.assertTrue(PIA.etb_discard_enchant)
        self.assertEqual(KRAKEN.upkeep_token.land_types, ("forest",))


class KrakenLandfallTests(unittest.TestCase):
    def test_tentacle_triggers_landfall(self):
        me, opp = pair()
        on_board(me, KRAKEN)
        on_board(me, LANDFALLER)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertLessEqual(opp.life, 19)  # Landfall durch das Tentacle (danach greifen beide an)
        self.assertEqual(opp.life, 20 - 1 - 6 - 1)


class HydraTests(unittest.TestCase):
    def test_needs_two_other_creatures(self):
        me, opp = pair()
        on_board(me, BEAR)
        me.lands, me.hand = [PLAINS] * 4, [HYDRA]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertIn(HYDRA, me.hand)

    def test_x_is_all_free_mana(self):
        me, opp = pair()
        on_board(me, BEAR)
        on_board(me, BEAR)
        me.lands, me.hand = [PLAINS] * 4, [HYDRA]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        hydra = next(c for c in me.creatures if c.card.name == "Guiding Hydra")
        self.assertEqual(hydra.bonus, 3)

    def test_spread_at_combat(self):
        me, opp = pair()
        hydra = on_board(me, HYDRA)
        hydra.bonus = 3
        a, b = on_board(me, BEAR), on_board(me, BEAR)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((hydra.bonus, a.bonus, b.bonus), (2, 1, 1))

    def test_no_spread_with_one_other(self):
        me, opp = pair()
        hydra = on_board(me, HYDRA)
        hydra.bonus = 3
        a = on_board(me, BEAR)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((hydra.bonus, a.bonus), (3, 0))

    def test_goldfish_hydra(self):
        hand = [PLAINS] * 5 + [BEAR, BEAR]
        order = hand + [HYDRA] + [PLAINS] * 20
        with mock.patch("components.mulligan.random.shuffle", lambda x: None):
            r = sim.simulate(order, 1, False, 3, 4, True, False, None, 11, 20, 6, True, 3, 6, False, False, 5, True)
        self.assertGreaterEqual(r["effects"]["counters"], 2)  # Runde 3: Hydra, Runde 4: Marken verteilt


class DemonTests(unittest.TestCase):
    def test_finds_the_most_expensive_card_for_next_turn(self):
        me, opp = pair()
        me.lands, me.hand = [MOUNTAIN] * 4, [PLAINS]
        me.library = [PLAINS, FIVE, SEVEN, BEAR, PLAINS]
        with mock.patch("components.battle.random.choice", lambda seq: seq[-1]):  # "zufaellig": die letzte Karte
            bt._resolve(me, opp, DEMON, 3, entry())
        self.assertEqual((FIVE in me.library, me.graveyard, me.hand), (False, [FIVE], [PLAINS]))

    def test_never_a_land(self):
        me, opp = pair()
        me.lands = [MOUNTAIN] * 4
        me.hand = [PLAINS, PLAINS]
        me.library = [PLAINS] * 5 + [SEVEN]
        with mock.patch("components.battle.random.choice", lambda seq: seq[0]):
            bt._resolve(me, opp, DEMON, 3, entry())
        self.assertIn(SEVEN, me.hand)  # keine bezahlbare Karte: die billigste Nichtland-Karte


class GoldfishTutorTests(unittest.TestCase):
    def _run(self, order, horizon):
        with mock.patch("components.mulligan.random.shuffle", lambda x: None), \
                mock.patch("components.simulation.random.choice", lambda seq: seq[0]):
            return sim.simulate(order, 1, False, 3, horizon, True, False, None, 11, 20, 6, True, 3, 6, False, False,
                                5, True)

    def test_goldfish_demon(self):
        hand = [MOUNTAIN] * 4 + [DEMON, PLAINS, PLAINS]
        r = self._run(hand + [PLAINS] * 4 + [SEVEN, PLAINS, FIVE] + [PLAINS] * 20, 5)  # R4 Demon sucht Five Drop
        self.assertEqual(r["curve"]["spent"][5], 5)

    def test_goldfish_pia(self):
        hand = [FOREST] * 6 + [PLAINS]
        r = self._run(hand + [PLAINS, PLAINS, PIA] + [PLAINS] * 20 + [ENCH3], 5)  # R4 Pia (4 > 3), R5 Small Charm
        self.assertEqual(r["curve"]["spent"][5], 3)


class PiaTests(unittest.TestCase):
    DECK = [PLAINS] * 20 + [FIVE] * 10

    def test_discards_a_land_for_a_castable_enchantment(self):
        me, opp = pair(deck=self.DECK)
        me.lands, me.hand = [FOREST] * 6, [PLAINS, BEAR]  # 6 Laender > teuerste Deckkarte (5)
        me.library = [ENCH3, ENCH6, ENCH9, PLAINS]
        bt._resolve(me, opp, PIA, 3, entry())
        self.assertEqual((PLAINS in me.graveyard, ENCH6 in me.hand, BEAR in me.hand), (True, True, True))

    def test_not_with_too_few_lands(self):
        me, opp = pair(deck=self.DECK)
        me.lands, me.hand = [FOREST] * 5, [PLAINS]
        me.library = [ENCH3]
        bt._resolve(me, opp, PIA, 3, entry())
        self.assertEqual((me.graveyard, me.hand), ([], [PLAINS]))

    def test_not_without_a_land_or_a_castable_enchantment(self):
        me, opp = pair(deck=self.DECK)
        me.lands, me.hand = [FOREST] * 6, [BEAR]
        me.library = [ENCH3]
        bt._resolve(me, opp, PIA, 3, entry())
        self.assertEqual(me.hand, [BEAR])
        me.hand, me.library = [PLAINS], [ENCH9]
        bt._resolve(me, opp, PIA._replace(name="Pia II"), 3, entry())
        self.assertEqual(me.hand, [PLAINS])


if __name__ == "__main__":
    unittest.main()
