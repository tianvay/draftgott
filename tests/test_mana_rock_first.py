"""Manastein zuerst: Eine Karte, die sofort Mana liefert (Nichtkreatur-Manaquelle, Haste-Kreatur, Zauber mit
Heartwood-Token), wird zuerst eingeplant, wenn ihr Mana einen weiteren Zauber ermoeglicht (Nichtkreatur-Artefakte haben
keine Einsatzverzoegerung, 302.6). Kreaturen ohne Haste nicht: sie kommen im Kampfmodell erst in Main 2."""
import unittest
from unittest import mock

from components import battle as bt
from components import simulation as sim
from components.cards import card_info
from components.mana import land_key
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
SIGNET = make("Signet", "Artifact", "{1}", 1, "{T}: Add {R}.", colors="")
GOBLIN = make("Goblin", CRE, "{R}", 1, "", "2", "1")
BRUTE = make("Brute", CRE, "{1}{R}", 2, "", "2", "2")
OGRE = make("Ogre", CRE, "{2}{R}", 3, "", "3", "3")
SEED = make("Ember Seed", "Sorcery", "{R}", 1, "Create a Heartwood token.")
GROVE = make("Grove Keeper", CRE, "{1}{R}", 2, "When this creature enters, create a Heartwood token.", "1", "1")
SHOCK = make("Shock Wave", "Sorcery", "{R}", 1, "Shock Wave deals 1 damage to each opponent.")
DRAKE = make("Drake", CRE, "{U}{U}", 2, "", "3", "3", colors="U")
IMP = make("Imp", CRE, "{R}", 1, "", "1", "1")
HASTY = make("Hasty Shaman", CRE, "{R}", 1, "Haste\n{T}: Add {R}.", "1", "1", ["Haste"])


def pair():
    me = bt.Player("Wir", [PLAINS] * 30, mulligan=False)
    opp = bt.Player("Gegner", [PLAINS] * 30, mulligan=False)
    for p in (me, opp):
        p.hand, p.library = [], [PLAINS] * 20
    me.opponent, opp.opponent = opp, me
    return me, opp


def plan(spells, pool):
    return sorted(c.name for c in sim.best_cast_reduced(spells, land_key(pool), False, True)[1])


class PlanTests(unittest.TestCase):
    def test_signet_first(self):
        self.assertEqual(plan([SIGNET, GOBLIN], [("R",)]), ["Goblin", "Signet"])

    def test_heartwood_spell_first(self):
        self.assertEqual(plan([SEED, BRUTE], [("R",), ("R",)]), ["Brute", "Ember Seed"])

    def test_haste_mana_creature_first(self):
        self.assertEqual(plan([HASTY, BRUTE], [("R",), ("R",)]), ["Brute", "Hasty Shaman"])

    def test_not_a_creature_without_haste(self):
        self.assertEqual(plan([GROVE, SHOCK, OGRE], [("R",), ("R",)]), ["Grove Keeper"])

    def test_only_when_it_is_better(self):
        self.assertEqual(plan([SIGNET, OGRE], [("R",)] * 3), ["Ogre", "Signet"])  # 2 Rest + Signet zahlen den Ogre
        self.assertEqual(plan([SIGNET, OGRE], [("R",)] * 2), ["Signet"])  # 1 Rest + Signet reicht nicht
        self.assertEqual(plan([SIGNET, GOBLIN], [("R",)] * 2), ["Goblin", "Signet"])  # passt ohnehin
        self.assertEqual(plan([SIGNET, DRAKE, IMP], [("U",)] * 2), ["Drake"])  # Signet + Imp waere schwaecher


class BattleTests(unittest.TestCase):
    def test_battle_casts_both(self):
        me, opp = pair()
        me.lands, me.hand = [MOUNTAIN], [SIGNET, GOBLIN]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(([c.card.name for c in me.creatures], [c.name for c in me.perms], me.hand),
                         (["Goblin"], ["Signet"], []))

    def test_battle_heartwood_first(self):
        me, opp = pair()
        me.lands, me.hand = [MOUNTAIN] * 2, [SEED, BRUTE]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(([c.card.name for c in me.creatures], [c.name for c in me.perms]), (["Brute"], ["Heartwood"]))


class GoldfishTests(unittest.TestCase):
    def test_goldfish_signet_first(self):
        hand = [MOUNTAIN, SIGNET, GOBLIN, PLAINS, PLAINS, PLAINS, PLAINS]
        with mock.patch("components.mulligan.random.shuffle", lambda x: None):
            r = sim.simulate(hand + [PLAINS] * 20, 1, False, 3, 4, True, False, None, 11, 20, 6, True, 3, 6, False,
                             False, 5, True)
        self.assertEqual(r["curve"]["spent"][1], 2)  # Runde 1: Signet und mit seinem Mana Goblin


if __name__ == "__main__":
    unittest.main()
