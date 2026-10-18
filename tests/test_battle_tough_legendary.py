"""Kampfmodell: +X/+Y erhoeht auch die Toughness (Kampftricks, Zauber, Betreten); legendaere Kreaturen."""
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
LEG = f"Legendary Creature {DASH} Test"
PLAINS = W["Plains"]
G = ("G",)


def make(name, type_line, cost, cmc, text, power=None, toughness=None):
    return card_info(_card(name, type_line, cost, cmc, "G", text, [], power, toughness))[0]


GIANT_GROWTH = make("Giant Growth", "Instant", "{G}", 1, "Target creature gets +2/+2 until end of turn.")
SHIELD = make("Shield", "Instant", "{G}", 1, "Target creature gets +0/+3 until end of turn.")
RALLY = make("Rally", "Instant", "{G}", 1, "Creatures you control get +1/+1 until end of turn.")
ROAR = make("Roar", "Sorcery", "{G}", 1, "Target creature gets +2/+2 until end of turn.")
HYPE = make("Hype", "Instant", "{G}", 1, "Target creature gets +3/+1 until end of turn.")
BEAR = make("Bear", CRE, "{1}{G}", 2, "", "2", "2")
OGRE = make("Ogre", CRE, "{2}{R}", 3, "", "3", "3")
HERO = make("Hero", LEG, "{3}{G}", 4, "", "5", "5")
YOSHI = make("Yoshimaru, Scrappy Stray", LEG, "{1}{W}", 2,
             "{6}: Put a +1/+1 counter on target nonlegendary creature.", "2", "1")
TAPPER = make("Tapper", CRE, "{1}{G}", 2, "{T}: Put a +1/+1 counter on target nonlegendary creature.", "3", "3")


def player(name="Wir"):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], [PLAINS] * 20
    return p


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


class ParseTests(unittest.TestCase):
    def test_toughness_next_to_the_modes(self):
        self.assertEqual(GIANT_GROWTH.modes, ((("pump", 2),),))  # Form der Effekte bleibt gleich
        self.assertEqual(GIANT_GROWTH.pump_tough, ((2,),))
        self.assertEqual(SHIELD.pump_tough, ((3,),))
        self.assertEqual(HYPE.pump_tough, ((1,),))
        self.assertEqual(RALLY.pump_tough, ((1,),))
        self.assertEqual(BEAR.pump_tough, ())

    def test_legendary(self):
        self.assertTrue(HERO.legendary)
        self.assertFalse(BEAR.legendary)


class TrickTests(unittest.TestCase):
    def test_trick_saves_the_attacker(self):
        me, opp = player(), player("Gegner")
        att, blk = bt.Creature(BEAR, 0), bt.Creature(OGRE, 0)
        me.creatures, opp.creatures, me.hand, me.open = [att], [blk], [GIANT_GROWTH], [G]
        bt.combat_tricks(me, [(att, [blk])], opp, entry(), 5, attacking=True)
        self.assertEqual((att.power, att.toughness), (4, 4))
        self.assertEqual(bt.outcome(att, [blk]), (False, [True]))

    def test_toughness_only_trick_saves_a_blocker(self):
        dfn, act = player("Gegner"), player()
        att, blk = bt.Creature(BEAR, 0), bt.Creature(BEAR, 0)
        act.creatures, dfn.creatures, dfn.hand, dfn.open = [att], [blk], [SHIELD], [G]
        bt.combat_tricks(dfn, [(att, [blk])], act, entry(), 6, attacking=False)
        self.assertEqual((blk.power, blk.toughness), (2, 5))
        self.assertEqual(bt.outcome(att, [blk]), (True, [False]))

    def test_rally_pumps_toughness_of_all(self):
        me, opp = player(), player("Gegner")
        a1, a2, blk = bt.Creature(BEAR, 0), bt.Creature(BEAR, 0), bt.Creature(make("Elf", CRE, "{G}", 1, "", "2", "1"), 0)
        me.creatures, opp.creatures, me.hand, me.open = [a1, a2], [blk], [RALLY], [G]
        bt.combat_tricks(me, [(a1, [blk]), (a2, [])], opp, entry(), 5, attacking=True)
        self.assertEqual([c.toughness for c in (a1, a2)], [3, 3])

    def test_sorcery_pump_raises_toughness(self):
        me, opp = player(), player("Gegner")
        me.creatures = [bt.Creature(BEAR, 0)]
        bt._resolve(me, opp, ROAR, 5, entry())
        self.assertEqual((me.creatures[0].power, me.creatures[0].toughness), (4, 4))

    def test_toughness_pump_ends_with_the_turn(self):
        me, opp = player(), player("Gegner")
        me.creatures = [bt.Creature(BEAR, 0)]
        bt._resolve(me, opp, ROAR, 5, entry())
        bt.cleanup((me,))
        self.assertEqual(me.creatures[0].toughness, 2)


class LegendaryTargetTests(unittest.TestCase):
    def test_nonlegendary_skips_other_legendary_creatures(self):
        dfn, act = player("Gegner"), player()
        yoshi, hero, bear = bt.Creature(YOSHI, 0), bt.Creature(HERO, 0), bt.Creature(BEAR, 0)
        dfn.creatures, dfn.open = [yoshi, hero, bear], [G] * 6
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual((yoshi.bonus, hero.bonus, bear.bonus), (0, 0, 1))

    def test_nonlegendary_source_may_target_itself(self):
        dfn, act = player("Gegner"), player()
        tapper, bear = bt.Creature(TAPPER, 0), bt.Creature(BEAR, 0)
        dfn.creatures = [bear, tapper]
        dfn.turn_start = 1  # 302.6: seit Beginn des letzten eigenen Zugs da
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual((tapper.bonus, bear.bonus), (1, 0))  # staerkste passende Kreatur ist der Tapper selbst


if __name__ == "__main__":
    unittest.main()
