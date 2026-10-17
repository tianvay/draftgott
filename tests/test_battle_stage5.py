"""Kampfmodell Stufe 5: Angriff auf Jace und Kreaturen mit Kampfwirkung beim Betreten in Main 1."""
import random
import unittest

from components import battle as bt
from components.battle_report import _attacks_html
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS, ISLAND = W["Plains"], W["Island"]


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=()):
    return card_info(_card(name, type_line, cost, cmc, "W", text, list(keywords), power, toughness))[0]


BEAR = W["Test Bear"]
CUB = make("Cub", CRE, "{W}", 1, "", "1", "1")
OGRE = make("Ogre", CRE, "{2}{R}", 3, "", "3", "3")
SQUIRE = make("Squire", CRE, "{2}{W}", 3, "", "3", "3")
PHANTASM = make("Surveillance Phantasm", CRE, "{1}{U}", 2, "Defender, flying, vigilance\nAs long as you've scried or "
                "surveilled this turn, this creature can attack as though it didn't have defender.\n{3}{U}: Surveil 1.",
                "2", "3", ["Defender", "Flying", "Vigilance"])
SEER = make("Seer", CRE, "{1}{U}", 2, "When this creature enters, surveil 1.", "1", "1")
SNIPER = make("Sniper", CRE, "{2}{W}", 3, "When this creature enters, it deals 3 damage to target creature an opponent "
              "controls.", "2", "2")
TRAINER = make("Trainer", CRE, "{1}{W}", 2, "When this creature enters, put a +1/+1 counter on target creature.",
               "1", "1")
PROPAGATOR = make("Greenhouse Propagator", CRE, "{2}{G}", 3, "Whenever another creature you control enters, you gain "
                  "1 life.", "2", "3")
LYRA = make("Lyra, Archangel of Dawn", f"Legendary Creature {DASH} Angel Knight", "{2}{W}", 3,
            "Flying\nWhenever you gain life, put a +1/+1 counter on each Angel you control.", "3", "3", ["Flying"])
MABEL = make("Mabel, Valley Hero", f"Legendary Creature {DASH} Mouse Soldier", "{1}{W}", 2, "Whenever Mabel or "
             "another creature you control enters, put a +1/+1 counter on target creature that entered this turn.",
             "1", "2")
HASTY = make("Hasty", CRE, "{1}{W}", 2, "Haste", "2", "2", ["Haste"])
PUMPER = make("Pumper", CRE, "{1}{W}", 2, "{2}: This creature gets +2/+2 until end of turn.", "2", "2")
PYRO = make("Frostbite Pyromental", CRE, "{U}{R}{R}", 3, "Trample, haste\nWhenever this creature deals combat damage "
            "to a player, draw two cards.", "4", "4", ["Trample", "Haste"])


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def attack(creatures, jace, life=20, opp_creatures=()):
    me, opp = player(), player("Gegner")
    me.creatures = [bt.Creature(c, 0) for c in creatures]
    opp.creatures = [bt.Creature(c, 0) for c in opp_creatures]
    opp.jace.loyalty, opp.life = jace, life
    e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
    return opp, e


class JaceAttackTests(unittest.TestCase):
    def test_attack_jace_with_three(self):
        opp, e = attack([BEAR], 3)
        self.assertEqual((opp.jace.loyalty, opp.life), (1, 20))
        self.assertTrue(e["attacks"][0]["jace"])

    def test_kill_small_jace(self):
        opp, _e = attack([BEAR], 2)
        self.assertEqual((opp.jace.loyalty, opp.life), (0, 20))

    def test_no_attack_if_small_jace_survives(self):
        opp, _e = attack([CUB], 2)
        self.assertEqual((opp.jace.loyalty, opp.life), (2, 19))

    def test_no_attack_if_jace_stays_at_three(self):
        opp, _e = attack([BEAR], 5)
        self.assertEqual((opp.jace.loyalty, opp.life), (5, 18))

    def test_just_enough_attackers(self):
        opp, _e = attack([BEAR, BEAR], 5)
        self.assertEqual((opp.jace.loyalty, opp.life), (1, 20))

    def test_weakest_attacker_goes_to_jace(self):
        opp, _e = attack([OGRE, CUB, BEAR], 3)
        self.assertEqual((opp.jace.loyalty, opp.life), (2, 15))  # Cub auf Jace (3 -> 2), Oger und Baer auf den Spieler

    def test_lethal_goes_to_the_player(self):
        opp, _e = attack([BEAR], 3, life=2)
        self.assertEqual((opp.jace.loyalty, opp.life), (3, 0))

    def test_no_card_draw_when_attacking_jace(self):
        me, opp = player(library=[BEAR] * 5), player("Gegner")
        me.creatures = [bt.Creature(PYRO, 5)]
        opp.jace.loyalty = 4
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((opp.jace.loyalty, me.hand), (0, []))

    def test_opponent_attacks_our_jace(self):
        me, opp = player(), player("Gegner")
        opp.creatures = [bt.Creature(BEAR, 0)]
        me.jace.loyalty = 3
        bt.take_turn(opp, me, 6, 3, skip_draw=True)
        self.assertEqual((me.jace.loyalty, me.life), (1, 20))

    def test_no_chump_to_protect_jace(self):
        big = bt.Creature(make("Giant", CRE, "{4}", 4, "", "5", "5"), 0)
        cub = bt.Creature(CUB, 0)
        self.assertEqual(bt.choose_blocks([big], [cub], 3), [(big, [cub])])
        big.at_jace = True
        self.assertEqual(bt.choose_blocks([big], [cub], 3), [(big, [])])

    def test_pump_with_free_mana_for_jace(self):
        me, opp = player(), player("Gegner")
        me.lands, me.creatures, opp.jace.loyalty = [PLAINS] * 2, [bt.Creature(PUMPER, 0)], 4
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((opp.jace.loyalty, opp.life), (0, 20))

    def test_jace_target_ends_with_the_turn(self):
        me, opp = player(), player("Gegner")
        me.creatures, opp.jace.loyalty = [bt.Creature(BEAR, 0)], 3
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertFalse(me.creatures[0].at_jace)

    def test_protocol_shows_jace(self):
        html = _attacks_html([{"attacker": "Bear (2/2)", "blockers": [], "attacker_dies": False, "blockers_die": [],
                               "jace": True}])
        self.assertIn("Jace", html)


class MainOneTests(unittest.TestCase):
    def turn(self, hand, board=(), opp_board=(), lands=None):
        me, opp = player(library=[BEAR] * 5), player("Gegner")
        me.lands = lands or [PLAINS] * 4
        me.hand = list(hand)
        me.creatures = [bt.Creature(c, 0) for c in board]
        opp.creatures = [bt.Creature(c, 0) for c in opp_board]
        return bt.take_turn(me, opp, 5, 3, skip_draw=True), me, opp

    def test_surveil_creature_first_for_a_waiting_phantasm(self):
        e, _me, _opp = self.turn([SEER], [PHANTASM], lands=[ISLAND] * 2)
        self.assertEqual((e["main1"], e["damage"]), (["Seer"], 2))

    def test_surveil_creature_stays_in_main2_without_phantasm(self):
        e, _me, _opp = self.turn([SEER], [BEAR], lands=[ISLAND] * 2)
        self.assertEqual((e["main1"], e["main2"]), ([], ["Seer"]))

    def test_etb_removal_clears_a_blocker(self):
        e, _me, opp = self.turn([SNIPER], [BEAR], [OGRE])
        self.assertEqual(e["main1"], ["Sniper"])
        self.assertEqual((opp.creatures, e["damage"]), ([], 2))

    def test_etb_removal_without_eater_stays_in_main2(self):
        e, _me, _opp = self.turn([SNIPER], [OGRE], [BEAR])
        self.assertEqual(e["main2"], ["Sniper"])

    def test_etb_counter_on_an_attacker(self):
        e, me, _opp = self.turn([TRAINER], [BEAR])
        self.assertEqual((e["main1"], e["damage"]), (["Trainer"], 3))

    def test_plain_creature_stays_in_main2(self):
        e, _me, _opp = self.turn([SQUIRE], [BEAR])
        self.assertEqual((e["main1"], e["main2"]), ([], ["Squire"]))

    def test_mabel_first_for_a_hasty_creature(self):
        e, _me, _opp = self.turn([MABEL, HASTY])
        self.assertIn("Mabel, Valley Hero", e["main1"])
        self.assertEqual(e["damage"], 3)

    def test_mabel_without_haste_stays_in_main2(self):
        e, _me, _opp = self.turn([MABEL], [BEAR])
        self.assertEqual(e["main2"], ["Mabel, Valley Hero"])

    def test_lifegain_grows_an_angel_before_combat(self):
        e, me, _opp = self.turn([CUB], [PROPAGATOR, LYRA])
        self.assertEqual(e["main1"], ["Cub"])
        self.assertEqual(e["damage"], 2 + 4)


class GameTests(unittest.TestCase):
    def test_games_with_jace(self):
        deck = [PLAINS] * 9 + [ISLAND] * 8 + [W["Test Empower Creature"], W["Test Empower"], BEAR, OGRE, SEER,
                                              PHANTASM, TRAINER, SNIPER] * 3
        random.seed(19)
        r = bt.battle(deck, deck, 60, on_draw=False)
        self.assertEqual(r["wins"] + r["losses"] + r["draws"], 60)
        attacks = [a for g in r["results_all"] for e in g["log"] for a in e.get("attacks", [])]
        self.assertTrue(any(a.get("jace") for a in attacks))


if __name__ == "__main__":
    unittest.main()
