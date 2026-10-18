"""Kampfmodell: Mana fuer Removal im Zug des Gegners freihalten (Variante B). Hat der Gegner jetzt eine Kreatur, die
unser Removal toeten kann, bleiben in der Main Phase die Kosten des billigsten solchen Removals offen: Instants,
Removal per Abwerfen von der Hand (Sureshot Sower) und Flash-Kreaturen mit Removal beim Betreten."""
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS = W["Plains"]


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="B"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


SWAMP, FOREST = land("Swamp", "B"), land("Forest", "G")
FOUR = make("Big Bat", CRE, "{3}{B}", 4, "", "4", "4")
TWO = make("Small Bat", CRE, "{1}{B}", 2, "", "2", "2")
FIVE = make("Titan", CRE, "{4}{G}", 5, "", "5", "5", colors="G")
OGRE = make("Ogre", CRE, "{2}{R}", 3, "", "3", "3", colors="R")
FLYER = make("Bird", CRE, "{1}{W}", 2, "Flying", "2", "2", ["Flying"], "W")
KILL = make("Murder", "Instant", "{1}{B}", 2, "Destroy target creature.")
BIGKILL = make("Doom", "Instant", "{2}{B}", 3, "Destroy target creature.")
SHOCK = make("Shock", "Instant", "{B}", 1, "Shock deals 2 damage to target creature.")
ASSASSIN = make("Night Assassin", CRE, "{1}{B}", 2, "Flash\nWhen this creature enters, destroy target creature an "
                "opponent controls.", "1", "1", ["Flash"])
SOWER = make("Sureshot Sower", f"Creature {DASH} Human Archer", "{1}{G}", 2, "Reach\n{3}{G}, Discard this card: "
             "Destroy target creature with flying.", "1", "3", ["Reach"], "G")


def player(name="Wir"):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], [PLAINS] * 20
    return p


def pair():
    me, opp = player(), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


def on_board(p, card, entered=0):
    c = bt.Creature(card, entered)
    c.gy, c.ctl = p.graveyard, p
    p.creatures.append(c)
    return c


def turn(hand, lands, enemy=()):
    me, opp = pair()
    for card in enemy:
        on_board(opp, card).tapped = True  # blockt nicht, bleibt aber Ziel
    me.lands, me.hand = list(lands), list(hand)
    e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
    return me, e


class HoldTests(unittest.TestCase):
    def test_holds_murder_against_a_target(self):
        me, e = turn([FOUR, TWO, KILL], [SWAMP] * 4, [OGRE])
        self.assertEqual(e["main2"], ["Small Bat"])
        self.assertEqual((len(me.open), KILL in me.hand), (2, True))

    def test_no_target_no_hold(self):
        me, e = turn([FOUR, TWO, KILL], [SWAMP] * 4)
        self.assertEqual(e["main2"], ["Big Bat"])

    def test_removal_that_cannot_kill_is_not_held(self):
        me, e = turn([FOUR, SHOCK], [SWAMP] * 4, [OGRE])
        self.assertEqual(e["main2"], ["Big Bat"])

    def test_holds_the_cheapest(self):
        me, e = turn([TWO, TWO, KILL, BIGKILL], [SWAMP] * 4, [OGRE])
        self.assertEqual((e["main2"], len(me.open)), (["Small Bat"], 2))

    def test_holds_flash_creature_with_enter_removal(self):
        me, e = turn([FOUR, TWO, ASSASSIN], [SWAMP] * 4, [OGRE])
        self.assertEqual((e["main2"], ASSASSIN in me.hand, len(me.open)), (["Small Bat"], True, 2))

    def test_holds_sower_ability(self):
        me, e = turn([FIVE, SOWER], [FOREST] * 5, [FLYER])
        self.assertEqual((e["main2"], SOWER in me.hand, len(me.open)), ([], True, 5))
        me, e = turn([FIVE, SOWER], [FOREST] * 5)
        self.assertEqual(e["main2"], ["Titan"])

    def test_held_sower_is_not_cast_as_creature(self):
        me, e = turn([SOWER], [FOREST] * 6, [FLYER])
        self.assertEqual((e["main2"], SOWER in me.hand), ([], True))

    def test_held_murder_is_used_in_the_opponents_turn(self):
        me, opp = pair()
        on_board(opp, OGRE).tapped = True
        me.lands, me.hand = [SWAMP] * 4, [FOUR, TWO, KILL]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        bt.end_step_instants(me, opp, {"face": 0, "events": [], "deaths": []}, 6)
        self.assertEqual((opp.creatures, KILL in me.graveyard), ([], True))


if __name__ == "__main__":
    unittest.main()
