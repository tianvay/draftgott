"""Kampfmodell: modale Karten ("Choose one/two —"). Jeder Aufzaehlungspunkt ist ein Modus; gewaehlt wird nach
Lethal > Removal > Karte ziehen > Token > Marken/Pumps > Leben. Die Goldfish-Modi (Card.modes) bleiben unveraendert."""
import random
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS = W["Plains"]
R, B, G, WH = ("R",), ("B",), ("G",), ("W",)


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=()):
    return card_info(_card(name, type_line, cost, cmc, "R", text, list(keywords), power, toughness))[0]


CRUSHER = make("Craftwork Crusher", f"Artifact Creature {DASH} Boar Construct", "{3}{R}{R}{G}{G}", 7,
               "Trample\nWhen this creature enters, choose two —\n• This creature deals 4 damage to target creature "
               "or planeswalker.\n• Create a 2/2 colorless Wizard Soldier creature token named Cadet.\n• Draw a card.",
               "7", "5", ["Trample"])
CHARM = make("Stingerquill Charm", "Instant", "{B}{R}", 2, "Choose one —\n• Stingerquill Charm deals 3 damage to any "
             "target.\n• Target creature gains first strike and deathtouch until end of turn.\n• Create a 2/2 colorless "
             "Wizard Soldier creature token named Cadet. It gains haste until end of turn.")
SURGICAL = make("Surgical Precision", "Sorcery", "{1}{W}", 2, "Choose one —\n• Destroy target creature with toughness 4 "
                "or greater. You gain 1 life.\n• You draw a card and gain 2 life.")
CHARGE = make("Charge the Sanctum", "Instant", "{2}{R/W}", 3, "Choose one —\n• Creatures you control get +2/+0 until "
              "end of turn.\n• Target creature gets +2/+0 and gains first strike until end of turn. Put a +1/+1 counter "
              "on it.")
VIGOR = make("Vigorbloom Charm", "Instant", "{G}{W}", 2, "Choose one —\n• Target permanent you control gains hexproof "
             "and indestructible until end of turn.\n• You draw a card and gain 3 life.\n• Put a +1/+1 counter on "
             "target creature you control. Then it fights target creature an opponent controls.")
BEAR = W["Test Bear"]
OGRE = make("Ogre", CRE, "{2}{R}", 3, "", "3", "3")
TITAN = make("Titan", CRE, "{4}{G}", 5, "", "4", "4")


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def pair(library=None):
    me, opp = player(library=library), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


class ParseTests(unittest.TestCase):
    def test_crusher(self):
        n, subs = CRUSHER.choices
        self.assertEqual(n, 2)
        self.assertEqual(subs[0].removal[:2] + (subs[0].removal[4],), ("damage", 4, "etb"))
        self.assertEqual(subs[1].creates_tokens[0][1].name, "Cadet")
        self.assertEqual(subs[2].draws, 1)

    def test_charm(self):
        n, subs = CHARM.choices
        self.assertEqual((n, len(subs)), (1, 3))
        self.assertTrue(subs[0].removal[3])  # any target
        self.assertEqual(subs[1].grant_kw, ("first strike", "deathtouch"))
        self.assertTrue(subs[2].creates_tokens[0][1].haste)

    def test_draw_and_life(self):
        sub = SURGICAL.choices[1][1]
        self.assertEqual((sub.draws, sub.spell_life), (1, 2))
        self.assertEqual(SURGICAL.choices[1][0].spell_life, 1)

    def test_goldfish_modes_unchanged(self):
        self.assertEqual(CHARGE.modes, ((("pump_all", 2),), (("pump", 2), ("counter", 1, 1))))
        self.assertEqual(BEAR.choices, ())


class CrusherTests(unittest.TestCase):
    def test_kill_and_draw(self):
        me, opp = pair(library=[BEAR] * 3)
        opp.creatures = [bt.Creature(OGRE, 0)]
        bt._resolve(me, opp, CRUSHER, 5, entry())
        self.assertEqual((opp.creatures, me.hand, [c.card.name for c in me.creatures]),
                         ([], [BEAR], ["Craftwork Crusher"]))

    def test_draw_and_cadet_without_target(self):
        me, opp = pair(library=[BEAR] * 3)
        bt._resolve(me, opp, CRUSHER, 5, entry())
        self.assertEqual((me.hand, sorted(c.card.name for c in me.creatures)),
                         ([BEAR], ["Cadet", "Craftwork Crusher"]))

    def test_no_kill_no_damage_mode(self):
        me, opp = pair(library=[BEAR] * 3)
        big = bt.Creature(make("Wall", CRE, "{5}", 5, "", "0", "8"), 0)
        opp.creatures = [big]
        bt._resolve(me, opp, CRUSHER, 5, entry())
        self.assertEqual((big.damage, len(me.creatures)), (0, 2))


class CharmTests(unittest.TestCase):
    def test_removal_at_end_step(self):
        me, opp = pair()
        opp.creatures = [bt.Creature(BEAR, 0)]
        me.hand, me.open = [CHARM], [B, R]
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual((opp.creatures, me.creatures, opp.life), ([], [], 20))

    def test_cadet_without_target(self):
        me, opp = pair()
        me.hand, me.open = [CHARM], [B, R]
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual(([c.card.name for c in me.creatures], opp.life), (["Cadet"], 20))

    def test_lethal_to_the_face(self):
        me, opp = pair()
        opp.life, me.hand, me.open = 3, [CHARM], [B, R]
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual((opp.life, me.creatures), (0, []))

    def test_first_strike_and_deathtouch_trick(self):
        me, opp = pair()
        att, blk = bt.Creature(BEAR, 0), bt.Creature(OGRE, 0)
        me.creatures, opp.creatures, me.hand, me.open = [att], [blk], [CHARM], [B, R]
        bt.combat_tricks(me, [(att, [blk])], opp, entry(), 5, attacking=True)
        self.assertTrue(att.has("first strike") and att.has("deathtouch"))
        self.assertEqual(bt.outcome(att, [blk]), (False, [True]))
        self.assertEqual(me.hand, [])

    def test_charge_trick_with_first_strike(self):
        me, opp = pair()
        att, blk = bt.Creature(BEAR, 0), bt.Creature(OGRE, 0)
        me.creatures, opp.creatures, me.hand, me.open = [att], [blk], [CHARGE], [R] * 3
        bt.combat_tricks(me, [(att, [blk])], opp, entry(), 5, attacking=True)
        self.assertEqual((att.power, att.toughness, att.has("first strike")), (5, 3, True))


class RankTests(unittest.TestCase):
    def test_lethal_mode_beats_drawing(self):
        blast = make("Blast", "Sorcery", "{1}{R}", 2, "Choose one —\n• Blast deals 3 damage to each opponent.\n"
                     "• Draw a card.")
        me, opp = pair(library=[BEAR] * 3)
        opp.life = 3
        bt._resolve(me, opp, blast, 3, entry())
        self.assertEqual((opp.life, me.hand), (0, []))
        opp.life = 10
        bt._resolve(me, opp, blast, 3, entry())
        self.assertEqual((opp.life, me.hand), (10, [BEAR]))

    def test_removal_mode_has_only_its_own_effects(self):
        choice = make("Choice", "Instant", "{1}{B}", 2, "Choose one —\n• Destroy target creature.\n• You gain 5 life.")
        me, opp = pair()
        opp.creatures = [bt.Creature(BEAR, 0)]
        me.hand, me.open = [choice], [B, B]
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual((opp.creatures, me.life), ([], 20))


class OtherModalTests(unittest.TestCase):
    def test_surgical_destroys_a_big_creature(self):
        me, opp = pair(library=[BEAR] * 3)
        opp.creatures = [bt.Creature(TITAN, 0)]
        bt._resolve(me, opp, SURGICAL, 3, entry())
        self.assertEqual((opp.creatures, me.life, me.hand), ([], 21, []))

    def test_surgical_draws_otherwise(self):
        me, opp = pair(library=[BEAR] * 3)
        opp.creatures = [bt.Creature(BEAR, 0)]
        bt._resolve(me, opp, SURGICAL, 3, entry())
        self.assertEqual((len(opp.creatures), me.life, me.hand), (1, 22, [BEAR]))

    def test_surgical_is_cast_without_a_target(self):
        me, opp = pair(library=[BEAR] * 3)
        me.lands, me.hand = [PLAINS] * 2, [SURGICAL]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["main1"], ["Surgical Precision"])

    def test_vigorbloom_value_at_end_step(self):
        me, opp = pair(library=[BEAR] * 3)
        me.hand, me.open = [VIGOR], [G, WH]
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual((me.hand, me.life), ([BEAR], 23))

    def test_vigorbloom_fight_at_end_step(self):
        me, opp = pair(library=[BEAR] * 3)
        me.creatures, opp.creatures = [bt.Creature(OGRE, 0)], [bt.Creature(BEAR, 0)]
        me.hand, me.open = [VIGOR], [G, WH]
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual((opp.creatures, me.life), ([], 20))


class GameTests(unittest.TestCase):
    def test_games(self):
        mountain = card_info(_card("Mountain", f"Basic Land {DASH} Mountain", text="({T}: Add {R}.)",
                                   produced=["R"]))[0]
        deck = [PLAINS] * 8 + [mountain] * 9 + [CRUSHER, CHARM, SURGICAL, CHARGE, VIGOR, BEAR, OGRE, TITAN] * 3
        random.seed(43)
        r = bt.battle(deck, deck, 60, on_draw=False)
        self.assertEqual(r["wins"] + r["losses"] + r["draws"], 60)


if __name__ == "__main__":
    unittest.main()
