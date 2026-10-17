"""Kampfmodell: Betreten-Effekte ("When this creature enters", 603.6a) wirken bei jedem Betreten, Effekte beim Wirken
("when you cast", "if you cast it") nur beim Wirken."""
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS = W["Plains"]
WH = ("W",)


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=()):
    return card_info(_card(name, type_line, cost, cmc, "W", text, list(keywords), power, toughness))[0]


SCHOLAR = make("Scholar", CRE, "{1}{W}", 2, "When this creature enters, draw a card.", "1", "1")
SNIPER = make("Sniper", CRE, "{2}{W}", 3, "When this creature enters, it deals 3 damage to target creature an "
              "opponent controls.", "2", "2")
RAT = make("Rank Rat", CRE, "{1}{W}", 2, "When this creature enters, each opponent discards a card.", "1", "1")
OCULUS = W["Test Empower Creature"]  # beim Betreten: Empower Jace 2
ACOLYTE = make("Acolyte", CRE, "{1}{W}", 2, "Whenever you cast a creature spell, empower Jace 1.", "1", "3",
               ["Empower Jace"])
FLASHER = make("Flash Scholar", CRE, "{1}{W}", 2, "Flash\nWhen this creature enters, draw a card.", "2", "2", ["Flash"])
TOKEN_ETB = make("Squad Leader", CRE, "{2}{W}", 3, "When this creature enters, create a 1/1 colorless Soldier creature "
                 "token named Recruit.", "2", "2")
REVIVAL = make("Generous Revival", "Sorcery", "{2}{W}", 3, "Return target creature card with mana value 3 or less "
               "from your graveyard to the battlefield with an additional +1/+1 counter on it.")
SURGE = make("Surge", "Sorcery", "{W}", 1, "Create a 1/1 colorless Soldier creature token named Recruit.")
BEAR = W["Test Bear"]
OGRE = make("Ogre", CRE, "{2}{W}", 3, "", "3", "3")


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


def revive(card, me=None, opp=None):
    me, opp = me or player(library=[BEAR] * 5), opp or player("Gegner")
    me.graveyard[:] = [card]
    bt._resolve(me, opp, REVIVAL, 3, entry())
    return me, opp


class ReturnedFromGraveyardTests(unittest.TestCase):
    def test_draw_on_enter(self):
        me, _opp = revive(SCHOLAR)
        self.assertEqual(me.hand, [BEAR])

    def test_removal_on_enter(self):
        opp = player("Gegner")
        opp.creatures = [bt.Creature(BEAR, 0)]
        _me, opp = revive(SNIPER, opp=opp)
        self.assertEqual(opp.creatures, [])

    def test_discard_on_enter(self):
        opp = player("Gegner")
        opp.hand = [OGRE]
        _me, opp = revive(RAT, opp=opp)
        self.assertEqual(opp.hand, [])

    def test_empower_on_enter(self):
        me, _opp = revive(OCULUS)
        self.assertEqual(me.jace.loyalty, 2)

    def test_token_on_enter(self):
        me, _opp = revive(TOKEN_ETB)
        self.assertEqual(sorted(c.card.name for c in me.creatures), ["Recruit", "Squad Leader"])

    def test_cast_trigger_not_on_return(self):
        me = player(library=[BEAR] * 5)
        me.creatures = [bt.Creature(ACOLYTE, 0)]
        me.jace_perms = [(ACOLYTE, 0)]
        revive(BEAR, me=me)
        self.assertEqual(me.jace.loyalty, 0)  # "whenever you cast a creature spell": zurueckgeholt ist nicht gewirkt
        bt._resolve(me, player("Gegner"), OGRE, 4, entry())
        self.assertEqual(me.jace.loyalty, 1)


class OtherWaysInTests(unittest.TestCase):
    def test_flash_blocker_draws_on_enter(self):
        dfn, act = player("Gegner", library=[BEAR] * 3), player()
        attacker = bt.Creature(make("Giant", CRE, "{4}", 4, "", "1", "1"), 0)
        act.creatures = [attacker]
        dfn.hand, dfn.open = [FLASHER], [WH] * 2
        bt.respond_to_attack(dfn, act, [attacker], entry(), 5)
        self.assertEqual(([c.card.name for c in dfn.creatures], dfn.hand), (["Flash Scholar"], [BEAR]))

    def test_flash_at_end_step_draws_once(self):
        dfn, act = player("Gegner", library=[BEAR] * 3), player()
        dfn.hand, dfn.open = [FLASHER], [WH] * 2
        bt.end_step_instants(dfn, act, entry(), 5)
        self.assertEqual(dfn.hand, [BEAR])

    def test_cast_from_hand_draws_once(self):
        me, opp = player(library=[BEAR] * 3), player("Gegner")
        bt._resolve(me, opp, SCHOLAR, 3, entry())
        self.assertEqual(me.hand, [BEAR])

    def test_cast_creature_empowers_once(self):
        me, opp = player(), player("Gegner")
        bt._resolve(me, opp, OCULUS, 3, entry())
        self.assertEqual(me.jace.loyalty, 2)

    def test_spell_effects_still_on_cast(self):
        me, opp = player(), player("Gegner")
        bt._resolve(me, opp, SURGE, 3, entry())
        self.assertEqual([c.card.name for c in me.creatures], ["Recruit"])


if __name__ == "__main__":
    unittest.main()
