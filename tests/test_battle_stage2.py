"""Kampfmodell Stufe 2: Removal, Instants, Flash, Kampftricks, Abwerfen."""
import random
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import _card

DASH = "—"
CRE = f"Creature {DASH} Test"


def make(name, type_line, cost, text, power=None, toughness=None, keywords=()):
    from components.mana import mana_value
    return card_info(_card(name, type_line, cost, mana_value(cost), "", text, list(keywords), power, toughness))[0]


def creature(name, p, t, cost="{2}", text="", keywords=()):
    return make(name, CRE, cost, text, str(p), str(t), keywords)


KILL = make("Kill", "Instant", "{1}{B}", "Destroy target creature.")
SORC_KILL = make("Sorc Kill", "Sorcery", "{1}{B}", "Destroy target creature or planeswalker.")
GASP = make("Gasp", "Instant", "{1}{B}", "Target creature gets -3/-3 until end of turn.")
BOLT = make("Bolt", "Sorcery", "{1}{R}", "Bolt deals 3 damage to any target.")
HEX = make("Hex", "Instant", "{B}", "Destroy target creature with mana value 2 or less.")
REFUTE = make("Refute", "Sorcery", "{1}{W}", "Exile target creature or planeswalker that's green or blue. Surveil 1.")
EDICT = make("Pressure", "Instant", "{2}{B}", "Target opponent sacrifices a creature or planeswalker with the greatest "
             "mana value among creatures and planeswalkers they control.")
UNSUMMON = make("Unsummon", "Instant", "{U}", "Return target creature to its owner's hand.")
LOCK = make("Coursework", f"Enchantment {DASH} Aura", "{2}{U}", "Enchant creature\nEnchanted creature loses all "
            "abilities and doesn't untap during its controller's untap step.")
WRATH = make("Wrath", "Sorcery", "{4}{W}", "Destroy all creatures.")
GROWTH = make("Growth", "Instant", "{G}", "Target creature gets +3/+3 until end of turn.")
DRAW = make("Insight", "Instant", "{U}", "Draw a card.")
RAT = creature("Rat", 1, 1, "{1}{B}", "When this creature enters, each opponent discards a card.")
TECH = creature("Technician", 4, 5, "{4}{R}", "Reach\nWhen this creature enters, you may discard a card. When you do, "
                "this creature deals 2 damage to any target.", ("Reach",))
HAPATRA = creature("Hapatra", 3, 3, "{2}{B}{B}", "When Hapatra enters, for each opponent, put X -1/-1 counters on up to "
                   "one target creature that player controls, where X is the greatest mana value among cards in your "
                   "graveyard.")
FLASHY = creature("Ambusher", 3, 3, "{2}{G}", "Flash", ("Flash",))
BEAR, OGRE, GIANT = creature("Bear", 2, 2, "{1}{G}"), creature("Ogre", 3, 3, "{2}{R}"), creature("Giant", 5, 5, "{4}{G}")
BIRD = creature("Bird", 2, 2, "{1}{U}", "Flying", ("Flying",))
PLAINS = card_info(_card("Swamp", f"Basic Land {DASH} Swamp", text="({T}: Add {B}.)", produced=["B"]))[0]


class SpecTests(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(KILL.removal[:2], ("destroy", 0))
        self.assertEqual(GASP.removal[:2], ("minus", 3))
        self.assertEqual(BOLT.removal[:2], ("damage", 3))
        self.assertTrue(BOLT.removal[3])        # any target
        self.assertEqual(EDICT.removal[0], "edict")
        self.assertIn(("greatest",), EDICT.removal[2])
        self.assertEqual(UNSUMMON.removal[0], "bounce")
        self.assertEqual(LOCK.removal[0], "lock")
        self.assertEqual(WRATH.removal[0], "sweep")
        self.assertEqual(HAPATRA.removal[:2], ("counters", -3))
        self.assertEqual(HAPATRA.removal[4], "etb")
        self.assertEqual(TECH.removal[:2], ("damage", 2))
        self.assertTrue(TECH.removal[5])        # wir werfen dafuer eine Karte ab

    def test_conditions(self):
        self.assertIn(("mv_le", 2), HEX.removal[2])
        self.assertIn(("color", "G", "U"), REFUTE.removal[2])

    def test_flags(self):
        self.assertTrue(KILL.is_instant and not SORC_KILL.is_instant)
        self.assertTrue(FLASHY.flash and not BEAR.flash)
        self.assertEqual(RAT.discard, 1)

    def test_abilities_have_no_spell_spec(self):
        sower = creature("Sower", 3, 1, "{1}{G}", "Reach\n{3}{G}, Discard this card: Destroy target creature with flying.")
        self.assertEqual(sower.removal, ())


def cr(card, entered=0):
    return bt.Creature(card, entered)


def player(name="Wir"):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], [PLAINS] * 20
    return p


class TargetTests(unittest.TestCase):
    def test_most_dangerous_valid_target(self):
        opp = player("Gegner")
        opp.creatures = [cr(BEAR), cr(GIANT), cr(BIRD)]
        self.assertEqual(bt.choose_target(KILL.removal, player(), opp).card.name, "Giant")
        self.assertEqual(bt.choose_target(HEX.removal, player(), opp).card.name, "Bird")  # nur MW <= 2, Flying zuerst

    def test_damage_needs_a_killable_target(self):
        opp = player("Gegner")
        opp.creatures = [cr(GIANT)]
        self.assertIsNone(bt.choose_target(GASP.removal, player(), opp))
        opp.creatures.append(cr(OGRE))
        self.assertEqual(bt.choose_target(GASP.removal, player(), opp).card.name, "Ogre")


class ApplyTests(unittest.TestCase):
    def setUp(self):
        self.me, self.opp = player(), player("Gegner")
        self.e = {"face": 0, "events": [], "deaths": []}

    def test_destroy_goes_to_graveyard(self):
        self.opp.creatures = [cr(OGRE)]
        bt.cast_removal(KILL, self.me, self.opp, self.e, 3)
        self.assertEqual((self.opp.creatures, self.opp.graveyard), ([], [OGRE]))

    def test_any_target_kills_a_creature_unless_face_is_lethal(self):
        self.opp.creatures = [cr(BEAR)]
        bt.cast_removal(BOLT, self.me, self.opp, self.e, 3)
        self.assertEqual((self.opp.creatures, self.opp.life), ([], 20))
        self.opp.creatures, self.opp.life = [cr(BEAR)], 3
        bt.cast_removal(BOLT, self.me, self.opp, self.e, 3)
        self.assertEqual((len(self.opp.creatures), self.opp.life), (1, 0))

    def test_any_target_without_killable_creature_goes_face(self):
        self.opp.creatures = [cr(GIANT)]
        bt.cast_removal(BOLT, self.me, self.opp, self.e, 3)
        self.assertEqual((len(self.opp.creatures), self.opp.life), (1, 17))

    def test_edict_greatest(self):
        self.opp.creatures = [cr(BEAR), cr(GIANT)]
        bt.cast_removal(EDICT, self.me, self.opp, self.e, 3)
        self.assertEqual([c.card.name for c in self.opp.creatures], ["Bear"])

    def test_bounce_returns_to_hand(self):
        self.opp.creatures = [cr(OGRE)]
        bt.cast_removal(UNSUMMON, self.me, self.opp, self.e, 3)
        self.assertEqual((self.opp.creatures, self.opp.hand), ([], [OGRE]))

    def test_lock(self):
        self.opp.creatures = [cr(OGRE)]
        bt.cast_removal(LOCK, self.me, self.opp, self.e, 3)
        self.assertTrue(self.opp.creatures[0].locked)
        self.assertFalse(bt.can_attack(self.opp.creatures[0], 9))
        self.assertFalse(bt.can_block(self.opp.creatures[0], cr(BEAR)))

    def test_sweep_hits_both_sides(self):
        self.opp.creatures, self.me.creatures = [cr(OGRE)], [cr(BEAR)]
        bt.cast_removal(WRATH, self.me, self.opp, self.e, 3)
        self.assertEqual((self.opp.creatures, self.me.creatures), ([], []))

    def test_hapatra_uses_the_graveyard(self):
        self.opp.creatures = [cr(GIANT)]
        self.me.graveyard = [GIANT]  # Manawert 5
        bt.cast_removal(HAPATRA, self.me, self.opp, self.e, 3)
        self.assertEqual(self.opp.creatures, [])


class DiscardTests(unittest.TestCase):
    def test_excess_land_first(self):
        p = player()
        p.lands = [PLAINS] * 3
        p.hand = [PLAINS, OGRE, BEAR]  # 3 Laender auf dem Feld + 1 auf der Hand >= hoechster MW 3
        self.assertIs(bt.choose_discard(p), PLAINS)

    def test_cheapest_card_otherwise(self):
        p = player()
        p.lands = [PLAINS]
        p.hand = [PLAINS, GIANT, BEAR]
        self.assertIs(bt.choose_discard(p), BEAR)


class TimingTests(unittest.TestCase):
    def test_main_phase_skips_instants_flash_and_removal_without_target(self):
        me, opp = player(), player("Gegner")
        me.hand = [KILL, FLASHY, SORC_KILL, BEAR]
        names = [c.name for c in bt.main_phase_spells(me, opp)]
        self.assertEqual(names, ["Bear"])  # Sorc Kill hat kein Ziel
        opp.creatures = [cr(OGRE)]
        self.assertIn("Sorc Kill", [c.name for c in bt.main_phase_spells(me, opp)])

    def test_defender_removes_the_most_dangerous_attacker(self):
        att, dfn = player(), player("Gegner")
        a1, a2 = cr(BEAR), cr(GIANT)
        att.creatures = [a1, a2]
        dfn.hand, dfn.open = [KILL], [("B",), ("B",)]
        e = {"face": 0, "events": [], "deaths": []}
        left = bt.respond_to_attack(dfn, att, [a1, a2], e, 5)
        self.assertEqual([a.card.name for a in left], ["Bear"])
        self.assertEqual(dfn.hand, [])

    def test_removal_at_end_step_without_attack(self):
        act, dfn = player(), player("Gegner")
        act.creatures = [cr(OGRE)]
        dfn.hand, dfn.open = [KILL, DRAW], [("B",), ("B",), ("U",)]
        e = {"face": 0, "events": [], "deaths": []}
        bt.end_step_instants(dfn, act, e, 5)
        self.assertEqual(act.creatures, [])
        self.assertEqual(len(dfn.hand), 1)  # Insight gewirkt, eine Karte gezogen
        self.assertNotIn(DRAW, dfn.hand)

    def test_flash_blocker_against_lethal(self):
        att, dfn = player(), player("Gegner")
        a = cr(OGRE)
        att.creatures = [a]
        dfn.life, dfn.hand, dfn.open = 3, [FLASHY], [("G",), ("G",), ("G",)]
        e = {"face": 0, "events": [], "deaths": []}
        bt.respond_to_attack(dfn, att, [a], e, 5)
        self.assertEqual([c.card.name for c in dfn.creatures], ["Ambusher"])

    def test_trick_saves_attacker_and_kills_blocker(self):
        me, opp = player(), player("Gegner")
        a, b = cr(BEAR), cr(OGRE)
        me.creatures, opp.creatures = [a], [b]
        me.hand, me.open = [GROWTH], [("G",)]
        e = {"face": 0, "events": [], "deaths": []}
        bt.combat_tricks(me, [(a, [b])], opp, e, 5, attacking=True)
        self.assertEqual(a.power, 5)
        self.assertEqual(me.hand, [])

    def test_no_trick_without_benefit(self):
        me, opp = player(), player("Gegner")
        a = cr(GIANT)
        me.creatures = [a]
        me.hand, me.open = [GROWTH], [("G",)]
        bt.combat_tricks(me, [(a, [])], opp, {"face": 0, "events": [], "deaths": []}, 5, attacking=True)
        self.assertEqual(me.hand, [GROWTH])  # ungeblockt und kein Lethal: Trick bleibt auf der Hand


class GameTests(unittest.TestCase):
    def test_removal_helps_against_big_creatures(self):
        lands = [PLAINS] * 17
        black_bear = creature("Black Bear", 2, 2, "{1}{B}")
        with_removal = lands + [KILL] * 8 + [black_bear] * 15
        without = lands + [black_bear] * 23
        brutes = lands + [creature("Brute", 4, 4, "{1}{B}")] * 23  # guenstig und stark: ohne Removal kaum zu schlagen
        random.seed(11)
        r1 = bt.battle(with_removal, brutes, 150, on_draw=False)
        random.seed(11)
        r2 = bt.battle(without, brutes, 150, on_draw=False)
        self.assertGreater(r1["wins"], r2["wins"] + 10)

    def test_any_target_ignores_harmless_creatures(self):
        me, opp = player(), player("Gegner")
        opp.creatures = [cr(creature("Wall", 0, 1, "{W}", "Defender", ("Defender",)))]
        bt.cast_removal(BOLT, me, opp, {"face": 0, "events": [], "deaths": []}, 3)
        self.assertEqual((len(opp.creatures), opp.life), (1, 17))


if __name__ == "__main__":
    unittest.main()
