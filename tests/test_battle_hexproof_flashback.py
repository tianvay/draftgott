"""Kampfmodell: Hexproof (702.11, auch bedingt wie Ruric Thar) und Flashback (702.34)."""
import random
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS, ISLAND = W["Plains"], W["Island"]
R, U, WH = ("R",), ("U",), ("W",)


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=()):
    return card_info(_card(name, type_line, cost, cmc, "W", text, list(keywords), power, toughness))[0]


SHROUDED = make("Shrouded Bear", CRE, "{1}{G}", 2, "Hexproof", "2", "2", ["Hexproof"])
RURIC = make("Ruric Thar, Magecrusher", f"Legendary Creature {DASH} Ogre Warrior", "{5}{G}{G}", 7,
             "Reach, vigilance, trample\nRuric Thar has hexproof as long as they haven't dealt combat damage yet.",
             "7", "7", ["Reach", "Vigilance", "Trample"])
BOLT = make("Bolt", "Instant", "{1}{R}", 2, "Bolt deals 3 damage to target creature.")
SWEEP = make("Pyroclasm", "Sorcery", "{1}{R}", 2, "Pyroclasm deals 2 damage to each creature.")
EDICT = make("Diabolic Edict", "Instant", "{1}{B}", 2, "Each opponent sacrifices a creature.")
GROWTH = make("Giant Growth", "Instant", "{G}", 1, "Target creature gets +3/+3 until end of turn.")
PREP = make("Predictive Preparations", "Sorcery", "{1}{W}", 2, "Put a +1/+1 counter on each of one or two target "
            "creatures.\nFlashback {3}{W} (You may cast this card from your graveyard for its flashback cost. Then "
            "exile it.)", keywords=["Flashback"])
FBOLT = make("Flame Bolt", "Instant", "{1}{R}", 2, "Flame Bolt deals 3 damage to target creature.\nFlashback {3}{R}",
             keywords=["Flashback"])
THINK = make("Think Again", "Instant", "{1}{U}", 2, "Draw a card.\nFlashback {2}{U}", keywords=["Flashback"])
TWINNED = make("Twinned Vision", "Instant", "{1}{U/R}", 2, "Draw a card.\nFlashback—{1}{U/R}{U/R}, Discard a card.",
               keywords=["Flashback"])
BEAR = W["Test Bear"]
OGRE = make("Ogre", CRE, "{2}{R}", 3, "", "3", "3")


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


class HexproofParseTests(unittest.TestCase):
    def test_keyword_and_condition(self):
        self.assertIn("hexproof", SHROUDED.kw)
        self.assertTrue(RURIC.hexproof_until_damage)
        self.assertNotIn("hexproof", RURIC.kw)


class HexproofTests(unittest.TestCase):
    def test_we_cannot_target_it(self):
        me, opp = player(), player("Gegner")
        opp.creatures = [bt.Creature(SHROUDED, 0)]
        me.hand, me.open = [BOLT], [R, R]
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual((me.hand, len(opp.creatures)), ([BOLT], 1))

    def test_opponent_cannot_target_it_either(self):
        dfn, act = player("Gegner"), player()
        attacker = bt.Creature(SHROUDED, 0)
        act.creatures = [attacker]
        dfn.hand, dfn.open = [BOLT], [R, R]
        self.assertEqual(bt.respond_to_attack(dfn, act, [attacker], entry(), 5), [attacker])
        self.assertEqual(dfn.hand, [BOLT])

    def test_untargeted_effects_still_kill(self):
        me, opp = player(), player("Gegner")
        opp.creatures = [bt.Creature(SHROUDED, 0)]
        bt._resolve(me, opp, SWEEP, 3, entry())
        self.assertEqual(opp.creatures, [])
        opp.creatures = [bt.Creature(SHROUDED, 0)]
        bt._resolve(me, opp, EDICT, 3, entry())
        self.assertEqual(opp.creatures, [])

    def test_own_spells_may_target_it(self):
        me, opp = player(), player("Gegner")
        att, blk = bt.Creature(SHROUDED, 0), bt.Creature(OGRE, 0)
        me.creatures, opp.creatures, me.hand, me.open = [att], [blk], [GROWTH], [("G",)]
        bt.combat_tricks(me, [(att, [blk])], opp, entry(), 5, attacking=True)
        self.assertEqual(att.power, 5)

    def test_ruric_loses_hexproof_after_combat_damage(self):
        me, opp = player(), player("Gegner")
        ruric = bt.Creature(RURIC, 0)
        opp.creatures = [ruric]
        self.assertEqual(bt.valid_targets(("destroy", 0, (), False, "spell", False), me, opp), [])
        bt.resolve_combat([(ruric, [])])
        self.assertEqual(bt.valid_targets(("destroy", 0, (), False, "spell", False), me, opp), [ruric])

    def test_ruric_hexproof_survives_a_turn_without_damage(self):
        me, opp = player(), player("Gegner")
        ruric = bt.Creature(RURIC, 0)
        opp.creatures = [ruric]
        bt.cleanup((opp,))
        self.assertTrue(bt.hexproof(ruric))


class FlashbackParseTests(unittest.TestCase):
    def test_costs(self):
        self.assertEqual(PREP.flashback, ((3, (("W", 1),)),))
        self.assertEqual(THINK.flashback, ((2, (("U", 1),)),))
        self.assertTrue(TWINNED.flashback and TWINNED.flashback_discard)  # Zusatzkosten: eine Karte abwerfen


class FlashbackTests(unittest.TestCase):
    def test_sorcery_from_graveyard_in_the_main_phase(self):
        me, opp = player(), player("Gegner")
        me.lands, me.graveyard[:] = [PLAINS] * 4, [PREP]
        me.creatures = [bt.Creature(BEAR, 0)]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["main1"], ["Predictive Preparations"])
        self.assertEqual((me.graveyard, me.hand, e["damage"]), ([], [], 3))  # danach im Exil

    def test_not_enough_mana(self):
        me, opp = player(), player("Gegner")
        me.lands, me.graveyard[:] = [PLAINS] * 3, [PREP]
        me.creatures = [bt.Creature(BEAR, 0)]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["main1"], me.graveyard, me.hand), ([], [PREP], []))

    def test_hand_copy_goes_to_graveyard_then_flashback(self):
        me, opp = player(), player("Gegner")
        me.lands, me.hand = [PLAINS] * 2, [PREP]
        me.creatures = [bt.Creature(BEAR, 0)]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(me.graveyard, [PREP])
        me.lands += [PLAINS] * 2
        e = bt.take_turn(me, opp, 7, 4, skip_draw=True)
        self.assertEqual((e["main1"], me.graveyard, me.creatures[0].bonus), (["Predictive Preparations"], [], 2))

    def test_removal_instant_from_graveyard(self):
        me, opp = player(), player("Gegner")
        opp.creatures = [bt.Creature(BEAR, 0)]
        me.graveyard[:], me.open = [FBOLT], [R] * 4
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual((opp.creatures, me.graveyard), ([], []))

    def test_draw_instant_from_graveyard(self):
        me, opp = player(library=[BEAR] * 3), player("Gegner")
        me.graveyard[:], me.open = [THINK], [U] * 3
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual((me.hand, me.graveyard), ([BEAR], []))

    def test_flashback_against_attacker(self):
        dfn, act = player("Gegner"), player()
        attacker = bt.Creature(OGRE, 0)
        act.creatures = [attacker]
        dfn.graveyard[:], dfn.open = [FBOLT], [R] * 4
        self.assertEqual(bt.respond_to_attack(dfn, act, [attacker], entry(), 5), [])
        self.assertEqual(dfn.graveyard, [])


class GameTests(unittest.TestCase):
    def test_games(self):
        deck = [PLAINS] * 9 + [ISLAND] * 8 + [SHROUDED, RURIC, BOLT, PREP, FBOLT, THINK, BEAR, OGRE] * 3
        random.seed(31)
        r = bt.battle(deck, deck, 60, on_draw=False)
        self.assertEqual(r["wins"] + r["losses"] + r["draws"], 60)


if __name__ == "__main__":
    unittest.main()
