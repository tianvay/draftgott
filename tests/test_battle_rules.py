"""Kampfmodell: Legend-Regel (704.5j), Handlimit (514.1) und Winter, Tormented Loner."""
import random
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
LEG = f"Legendary Creature {DASH} Human Knight"
PLAINS = W["Plains"]


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=()):
    return card_info(_card(name, type_line, cost, cmc, "W", text, list(keywords), power, toughness))[0]


DANITHA = make("Danitha, Spear of Agony", LEG, "{2}{W}", 3, "First strike", "2", "2", ["First strike"])
MENTOR = make("Way of the Mentor", f"Legendary Enchantment {DASH} Saga", "{1}{W}", 2, "")
WINTER = make("Winter, Tormented Loner", f"Legendary Creature {DASH} Human Warlock", "{2}{W}", 3,
              "When Winter enters, you may sacrifice a creature or planeswalker. When you do, each opponent sacrifices "
              "a creature of their choice.\nWinter gets +1/+0 for each creature and planeswalker card in your "
              "graveyard.", "0", "3")
BEAR = W["Test Bear"]
CUB = make("Cub", CRE, "{W}", 1, "", "1", "1")
OGRE = make("Ogre", CRE, "{2}{W}", 3, "", "3", "3")
CADET = make("Recruiter", "Sorcery", "{W}", 1, "Create a 1/1 colorless Soldier creature token named Recruit.")


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


class LegendTests(unittest.TestCase):
    def test_only_one_with_the_same_name(self):
        me, opp = player(), player("Gegner")
        bt._resolve(me, opp, DANITHA, 3, entry())
        me.creatures[0].bonus = 1  # die erste ist staerker und bleibt
        first = me.creatures[0]
        bt._resolve(me, opp, DANITHA, 5, entry())
        self.assertEqual(me.creatures, [first])
        self.assertEqual(me.graveyard, [DANITHA])

    def test_newer_one_stays_if_stronger(self):
        me, opp = player(), player("Gegner")
        old = bt.Creature(DANITHA, 1)
        old.damage = 0
        old.bonus = -1
        me.creatures = [old]
        bt._resolve(me, opp, DANITHA, 5, entry())
        self.assertEqual([c.entered for c in me.creatures], [5])

    def test_each_player_may_have_one(self):
        me, opp = player(), player("Gegner")
        opp.creatures = [bt.Creature(DANITHA, 0)]
        bt._resolve(me, opp, DANITHA, 3, entry())
        self.assertEqual((len(me.creatures), len(opp.creatures)), (1, 1))

    def test_legendary_enchantment(self):
        me, opp = player(), player("Gegner")
        bt._resolve(me, opp, MENTOR, 3, entry())
        bt._resolve(me, opp, MENTOR, 5, entry())
        self.assertEqual((me.perms, me.graveyard), ([MENTOR], [MENTOR]))

    def test_second_copy_is_not_cast(self):
        me, opp = player(), player("Gegner")
        me.lands, me.hand = [PLAINS] * 3, [DANITHA]
        me.creatures = [bt.Creature(DANITHA, 0)]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["main1"], e["main2"], me.hand), ([], [], [DANITHA]))


    def test_second_flash_copy_is_not_cast(self):
        edgar = make("Edgar, Moonlit Sovereign", f"Legendary Creature {DASH} Werewolf Noble", "{3}{W}", 4, "Flash",
                     "4", "4", ["Flash"])
        dfn, act = player("Gegner"), player()
        dfn.creatures, dfn.hand, dfn.open = [bt.Creature(edgar, 0)], [edgar], [("W",)] * 4
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual(dfn.hand, [edgar])
        attacker = bt.Creature(OGRE, 0)
        act.creatures = [attacker]
        bt.respond_to_attack(dfn, act, [attacker], entry(), 7)
        self.assertEqual(dfn.hand, [edgar])


class HandSizeTests(unittest.TestCase):
    def test_discard_to_seven_at_end_of_own_turn(self):
        me, opp = player(), player("Gegner")
        me.hand = [OGRE] * 9
        opp.hand = [OGRE] * 9
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((len(me.hand), len(opp.hand)), (7, 9))
        self.assertEqual(me.graveyard.count(OGRE), 2)
        self.assertTrue(any("Handlimit" in x for x in e["events"]))

    def test_no_discard_with_seven(self):
        me, opp = player(), player("Gegner")
        me.hand = [OGRE] * 7
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(len(me.hand), 7)


class WinterTests(unittest.TestCase):
    def test_parse(self):
        self.assertTrue(WINTER.edict_cost)
        self.assertEqual(WINTER.gy_power, ("creature", "planeswalker"))

    def test_both_sacrifice_their_weakest(self):
        me, opp = player(), player("Gegner")
        me.creatures = [bt.Creature(BEAR, 0), bt.Creature(CUB, 0)]
        opp.creatures = [bt.Creature(OGRE, 0), bt.Creature(CUB, 0)]
        bt._resolve(me, opp, WINTER, 3, entry())
        self.assertEqual([c.card.name for c in me.creatures], ["Test Bear", "Winter, Tormented Loner"])
        self.assertEqual([c.card.name for c in opp.creatures], ["Ogre"])
        self.assertEqual(me.creatures[1].power, 1)  # Cub im Friedhof

    def test_no_sacrifice_without_another_creature(self):
        me, opp = player(), player("Gegner")
        opp.creatures = [bt.Creature(OGRE, 0)]
        bt._resolve(me, opp, WINTER, 3, entry())
        self.assertEqual((len(me.creatures), len(opp.creatures)), (1, 1))

    def test_no_sacrifice_if_opponent_has_no_creature(self):
        me, opp = player(), player("Gegner")
        me.creatures = [bt.Creature(CUB, 0)]
        bt._resolve(me, opp, WINTER, 3, entry())
        self.assertEqual(len(me.creatures), 2)

    def test_token_is_sacrificed_but_does_not_count(self):
        me, opp = player(), player("Gegner")
        bt._resolve(me, opp, CADET, 3, entry())
        me.creatures.append(bt.Creature(BEAR, 0))
        opp.creatures = [bt.Creature(OGRE, 0)]
        bt._resolve(me, opp, WINTER, 3, entry())
        self.assertEqual([c.card.name for c in me.creatures], ["Test Bear", "Winter, Tormented Loner"])
        self.assertEqual((opp.creatures, me.creatures[1].power), ([], 0))

    def test_planeswalker_cards_count(self):
        me, opp = player(), player("Gegner")
        me.graveyard[:] = [W["Test Walker"], BEAR, PLAINS, W["Test Empower"]]
        bt._resolve(me, opp, WINTER, 3, entry())
        self.assertEqual(me.creatures[0].power, 2)


class GameTests(unittest.TestCase):
    def test_games(self):
        deck = [PLAINS] * 17 + [DANITHA, MENTOR, WINTER, BEAR, CUB, OGRE, CADET] * 3
        random.seed(29)
        r = bt.battle(deck, deck, 60, on_draw=False)
        self.assertEqual(r["wins"] + r["losses"] + r["draws"], 60)


if __name__ == "__main__":
    unittest.main()
