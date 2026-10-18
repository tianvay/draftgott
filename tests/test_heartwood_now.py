"""Heartwood sofort (offener Punkt 14): Nichtkreatur-Artefakte haben keine Einsatzverzoegerung (302.6 gilt nur fuer
Kreaturen). Ein Heartwood-Token aus einem Zauber oder Betreten-Effekt liefert schon in derselben Runde Mana fuer weitere
Zauber; entsteht er mitten im Zug (Aerid Konstrari stirbt), ist sein Mana offen fuer Instants."""
import unittest
from unittest import mock

from components import battle as bt
from components import simulation as sim
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS = W["Plains"]


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="R"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


MOUNTAIN = land("Mountain", "R")
SEED = make("Heartwood Seed", "Sorcery", "{1}{R}", 2, "Create a Heartwood token.")
GOBLIN = make("Goblin", CRE, "{R}", 1, "", "2", "1")
GROVE = make("Grove Keeper", CRE, "{1}{R}", 2, "When this creature enters, create a Heartwood token.", "1", "1")
SIGNET = make("Signet", "Artifact", "{2}", 2, "{T}: Add {R}.", colors="")
AERID = make("Aerid Konstrari", f"Legendary Creature {DASH} Elder Sphinx", "{1}{R}{G}{G}", 4, "Flying\nWhen Aerid "
             "Konstrari enters or dies, create a Heartwood token.\n{6}: Create a Heartwood token. Then Aerid Konstrari "
             "gets +X/+0 until end of turn, where X is the number of artifacts you control.", "3", "3", ["Flying"])


def player(name="Wir"):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], [PLAINS] * 20
    return p


def pair():
    me, opp = player(), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


class BattleTests(unittest.TestCase):
    def test_spell_heartwood_pays_for_another_spell(self):
        me, opp = pair()
        me.lands, me.hand = [MOUNTAIN] * 2, [SEED, GOBLIN]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(([c.card.name for c in me.creatures], me.hand), (["Goblin"], []))

    def test_enter_heartwood_pays_for_another_spell(self):
        me, opp = pair()
        me.lands, me.hand = [MOUNTAIN] * 2, [GROVE, GOBLIN]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(sorted(c.card.name for c in me.creatures), ["Goblin", "Grove Keeper"])

    def test_mana_artifact_in_the_same_turn(self):
        me, opp = pair()
        me.lands, me.hand = [MOUNTAIN] * 2, [SIGNET, GOBLIN]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(([c.card.name for c in me.creatures], me.hand), (["Goblin"], []))

    def test_unused_heartwood_mana_stays_open(self):
        me, opp = pair()
        me.lands, me.hand = [MOUNTAIN] * 2, [SEED]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(me.open, [("G", "R")])

    def test_death_heartwood_is_open_mana(self):
        me, _opp = pair()
        c = bt.Creature(AERID, 0)
        c.gy, c.ctl = me.graveyard, me
        me.creatures.append(c)
        c.dead = True
        bt.bury((me,), {"face": 0, "events": [], "deaths": []})
        self.assertEqual(me.open, [("G", "R")])


class GoldfishTests(unittest.TestCase):
    def test_heartwood_in_the_same_round(self):
        hand = [MOUNTAIN, MOUNTAIN, SEED, GOBLIN, GOBLIN, PLAINS, PLAINS]  # Runde 1: erster Goblin
        with mock.patch("components.mulligan.random.shuffle", lambda x: None):
            r = sim.simulate(hand + [PLAINS] * 20, 1, False, 3, 4, True, False, None, 11, 20, 6, True, 3, 6, False,
                             False, 5, True)
        self.assertEqual(r["curve"]["spent"][2], 3)  # Runde 2: Heartwood Seed und mit dem Heartwood-Mana Goblin

    def test_mana_artifact_in_the_same_round(self):
        hand = [MOUNTAIN, MOUNTAIN, SIGNET, GOBLIN, GOBLIN, PLAINS, PLAINS]  # Runde 1: erster Goblin
        with mock.patch("components.mulligan.random.shuffle", lambda x: None):
            r = sim.simulate(hand + [PLAINS] * 20, 1, False, 3, 4, True, False, None, 11, 20, 6, True, 3, 6, False,
                             False, 5, True)
        self.assertEqual(r["curve"]["spent"][2], 3)  # Runde 2: Signet und mit seinem Mana Goblin


if __name__ == "__main__":
    unittest.main()
