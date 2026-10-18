"""Splinter Twin: Aura (303.4a), die verzauberte Kreatur hat "{T}: Create a token that's a copy of this creature,
except it has haste. Exile that token at the beginning of the next end step."
Ziel: Kreatur mit Betreten-Effekt (hoechster Removal-Score, dann Manawert), sonst die gefaehrlichste nicht legendaere;
legendaere nur, wenn ihr Betreten-Effekt Lethal bringt. Aktivierung am Ende des gegnerischen Zugs (513.2: die Kopie
lebt bis zu unserem Zugende), im eigenen Zug nur fuer Lethal. Kopie: nur aufgedruckte Werte (707.2) plus Haste;
Betreten-Effekte ja (603.6a), "if you cast it" nein. Die Aura geht in den Friedhof, wenn die Kreatur geht (704.5m).
Im Goldfish gilt dasselbe gegen einen Gegner, der nichts tut."""
import random
import unittest

from components import battle as bt
from components import simulation as sim
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS = W["Plains"]
R = ("R",)


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="R"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


MOUNTAIN = land("Mountain", "R")
TWIN = make("Splinter Twin", f"Enchantment {DASH} Aura", "{2}{R}{R}", 4, "Enchant creature\nEnchanted creature has "
            "\"{T}: Create a token that's a copy of this creature, except it has haste. Exile that token at the "
            "beginning of the next end step.\"")
SHOOTER = make("Shooter", CRE, "{2}{R}", 3, "When this creature enters, it deals 3 damage to target creature.", "2", "2")
SEER = make("Seer", CRE, "{4}{R}", 5, "When this creature enters, draw a card.", "1", "1")
PINGER = make("Pinger", CRE, "{1}{R}", 2, "When this creature enters, it deals 2 damage to each opponent.", "2", "2")
BIG = make("Big", CRE, "{4}{R}", 5, "", "5", "5")
LEGEND = make("Legend", f"Legendary Creature {DASH} Test", "{4}{R}", 5, "", "6", "6")
LEGEND_PING = make("Ping Lord", f"Legendary Creature {DASH} Test", "{2}{R}", 3, "When Ping Lord enters, it deals 3 "
                   "damage to each opponent.", "1", "1")
BEAR = W["Test Bear"]


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def pair():
    me, opp = player(), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


def on_board(p, card, entered=0):
    c = bt.Creature(card, entered)
    c.gy, c.ctl = p.graveyard, p
    p.creatures.append(c)
    return c


def enchant(p, host):
    p.perms.append(TWIN)
    host.auras.append(TWIN)


class ParseTests(unittest.TestCase):
    def test_field(self):
        self.assertTrue(TWIN.twin)
        self.assertFalse(SHOOTER.twin)


class TargetTests(unittest.TestCase):
    def _host(self, cards, opp_life=20):
        me, opp = pair()
        opp.life = opp_life
        mine = [on_board(me, c) for c in cards]
        return bt.twin_host(me, opp), mine

    def test_highest_removal_score_first(self):
        host, mine = self._host([BIG, SEER, SHOOTER])
        self.assertIs(host, mine[2])

    def test_then_mana_value(self):
        host, mine = self._host([BIG, PINGER, SEER])
        self.assertIs(host, mine[2])

    def test_without_enter_effect_the_strongest_nonlegendary(self):
        host, mine = self._host([BEAR, LEGEND, BIG])
        self.assertIs(host, mine[2])

    def test_legendary_only_for_lethal(self):
        host, _mine = self._host([LEGEND_PING])
        self.assertIsNone(host)
        host, mine = self._host([LEGEND_PING], opp_life=3)
        self.assertIs(host, mine[0])

    def test_twin_not_cast_without_host(self):
        me, opp = pair()
        on_board(me, LEGEND)
        me.lands, me.hand = [MOUNTAIN] * 4, [TWIN]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["main1"], me.hand), ([], [TWIN]))

    def test_cast_and_attached(self):
        me, opp = pair()
        big = on_board(me, BIG)
        me.lands, me.hand = [MOUNTAIN] * 4, [TWIN]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((big.auras, TWIN in me.perms), ([TWIN], True))


class ActivationTests(unittest.TestCase):
    def test_copy_at_the_end_of_the_opponents_turn(self):
        me, opp = pair()
        seer = on_board(me, SEER)
        enchant(me, seer)
        me.turn_start = 1
        bt.end_step_instants(me, opp, entry(), 2)
        tokens = [c for c in me.creatures if c.card.is_token]
        self.assertEqual((seer.tapped, len(tokens), len(me.hand)), (True, 1, 1))
        self.assertTrue(tokens[0].card.haste and bt.can_attack(tokens[0], 2))
        self.assertEqual(tokens[0].card.name, "Seer")

    def test_copy_attacks_with_the_original_and_is_exiled(self):
        me, opp = pair()
        big = on_board(me, BIG)
        enchant(me, big)
        me.turn_start = 1
        bt.end_step_instants(me, opp, entry(), 2)
        e = bt.take_turn(me, opp, 3, 2, skip_draw=True)
        self.assertEqual(e["damage"], 10)
        self.assertEqual([c.card.name for c in me.creatures], ["Big"])
        self.assertEqual(me.graveyard, [])

    def test_not_for_a_creature_from_our_last_turn(self):
        me, opp = pair()
        big = on_board(me, BIG, entered=1)  # 302.6
        enchant(me, big)
        me.turn_start = 1
        bt.end_step_instants(me, opp, entry(), 2)
        self.assertEqual(len(me.creatures), 1)

    def test_copy_has_printed_values_only(self):
        me, opp = pair()
        big = on_board(me, BIG)
        big.bonus = 2
        enchant(me, big)
        me.turn_start = 1
        bt.end_step_instants(me, opp, entry(), 2)
        token = [c for c in me.creatures if c.card.is_token][0]
        self.assertEqual((token.power, token.auras), (5, []))

    def test_own_turn_only_for_lethal(self):
        me, opp = pair()
        pinger = on_board(me, PINGER)
        enchant(me, pinger)
        opp.life = 4
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertLessEqual(opp.life, 0)

    def test_no_activation_in_own_turn_without_lethal(self):
        me, opp = pair()
        pinger = on_board(me, PINGER)
        enchant(me, pinger)
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((opp.life, len(me.creatures), e["damage"]), (18, 1, 2))

    def test_legendary_copy_dies_to_the_legend_rule_after_its_trigger(self):
        me, opp = pair()
        lord = on_board(me, LEGEND_PING)
        enchant(me, lord)
        me.turn_start = 1
        bt.end_step_instants(me, opp, entry(), 2)
        self.assertEqual((opp.life, [c.card.name for c in me.creatures]), (17, ["Ping Lord"]))
        self.assertIs(me.creatures[0], lord)

    def test_aura_leaves_with_its_creature(self):
        me, opp = pair()
        big = on_board(me, BIG)
        enchant(me, big)
        big.dead = True
        bt.bury((me,), entry())
        self.assertEqual((TWIN in me.perms, TWIN in me.graveyard), (False, True))

    def test_aura_leaves_on_bounce(self):
        me, opp = pair()
        big = on_board(me, BIG)
        enchant(me, big)
        bounce = make("Unsummon", "Instant", "{U}", 1, "Return target creature to its owner's hand.", colors="U")
        bt.cast_removal(bounce, opp, me, entry(), 5, target=big)
        self.assertEqual((TWIN in me.perms, TWIN in me.graveyard, BIG in me.hand), (False, True, True))


class GoldfishTests(unittest.TestCase):
    def test_goldfish_copy_attacks_and_repeats_enter_effects(self):
        dud = make("Dud Aura", f"Enchantment {DASH} Aura", "{2}{R}{R}", 4, "Enchant creature")

        def lethal_turns(aura):
            deck = [MOUNTAIN] * 17 + [PINGER] * 12 + [aura] * 11
            random.seed(9)
            r = sim.simulate(deck, 60, False, 3, 10, True, False, None, 11, 20, 6, True, 3, 6, False, False, 5, False)
            return sum(r["dmg"]) / max(1, len(r["dmg"])), len(r["dmg"])

        with_twin, without = lethal_turns(TWIN), lethal_turns(dud)
        self.assertLess(with_twin[0], without[0])

    def _fixed_game(self, target):
        from unittest import mock
        hand = [MOUNTAIN] * 6 + [TWIN]
        order = hand + [MOUNTAIN] * 4 + [PINGER] + [MOUNTAIN] * 10  # Pinger kommt in Runde 6
        with mock.patch("components.mulligan.random.shuffle", lambda x: None):
            r = sim.simulate(order, 1, False, 3, 10, True, False, None, 11, target, 6, True, 3, 6, False, False, 5,
                             False)
        return r["dmg"]

    def test_goldfish_first_copy_after_round_seven(self):
        # R6: Pinger (2 Schaden beim Betreten) und Twin. R7: Pinger greift an (4). Erst nach R7 darf er tappen
        # (302.6): R8 Kopie 2 beim Betreten, Kopie und Pinger je 2 (10).
        self.assertEqual(self._fixed_game(8), [8])

    def test_goldfish_copy_attacks_too(self):
        self.assertEqual(self._fixed_game(9), [8])

    def test_goldfish_host_choice_matches_battle(self):
        board = [(BIG, 1), (SEER, 1), (SHOOTER, 1)]
        self.assertEqual(sim.twin_host_index(board, [0, 0, 0], need=99), 2)
        self.assertEqual(sim.twin_host_index([(LEGEND_PING, 1)], [0], need=99), None)
        self.assertEqual(sim.twin_host_index([(LEGEND_PING, 1)], [0], need=3), 0)


if __name__ == "__main__":
    unittest.main()
