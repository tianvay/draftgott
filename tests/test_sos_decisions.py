"""SOS: Spielentscheidungen nach Rueckmeldung des Nutzers (2026-11-15) - Rejoinder enttappt eine eigene Mana-Kreatur,
wenn dadurch eine weitere Karte wirkbar wird; Practiced Offense nur mit Angreifer; Rubble Rouser auch im eigenen Zug,
wenn das Lethal bringt."""
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card
from tests.test_sos_package_a import C as A

DASH = "—"
PLAINS = W["Plains"]


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="G"):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)


DORK = card_info(raw("Elf Dork", f"Creature {DASH} Elf Druid", "{G}", 1, "{T}: Add {G}.", "1", "1"))[0]
SPROUT = card_info(raw("Sprout", f"Creature {DASH} Plant", "{G}", 1, "", "1", "1"))[0]
OGRE = card_info(raw("Ogre", "Creature — Ogre", "{2}{R}", 3, "", "3", "3", colors="R"))[0]
ROUSER = card_info(raw("Rubble Rouser", f"Creature {DASH} Dwarf Sorcerer", "{2}{R}", 3,
                       "When this creature enters, you may discard a card. If you do, draw a card.\n{T}, Exile a card "
                       "from your graveyard: Add {R}. When you do, this creature deals 1 damage to each opponent.", "1",
                       "4", colors="R"))[0]


def player(name="Wir"):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], [PLAINS] * 20
    return p


def pair():
    me, opp = player(), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


def entry():
    return {"face": 0, "damage": 0, "events": [], "deaths": [], "main1": [], "main2": []}


def on_board(p, card, entered=0):
    c = bt.Creature(card, entered)
    c.gy, c.ctl = p.graveyard, p
    p.creatures.append(c)
    return c


class RejoinderTests(unittest.TestCase):
    def test_untaps_dork_to_cast_another_card(self):
        me, opp = pair()
        me.turn_start = me.now
        dork = on_board(me, DORK)
        dork.tapped = True
        ogre = on_board(opp, OGRE)
        me.hand, me.open = [SPROUT], []
        bt._resolve(me, opp, A["rejoinder"], 3, entry())
        self.assertTrue(any(c.card is SPROUT for c in me.creatures))
        self.assertFalse(ogre.tapped)
        self.assertTrue(dork.tapped)  # das Mana ist wieder verbraucht

    def test_taps_opponent_when_nothing_to_cast(self):
        me, opp = pair()
        me.turn_start = me.now
        dork = on_board(me, DORK)
        dork.tapped = True
        on_board(me, OGRE)
        wall = on_board(opp, card_info(raw("Wall", "Creature — Wall", "{1}{W}", 2, "", "0", "6", colors="W"))[0])
        me.hand, me.open = [], []
        bt._resolve(me, opp, A["rejoinder"], 3, entry())
        self.assertTrue(wall.tapped)


class PracticedOffenseTests(unittest.TestCase):
    def test_only_with_an_attacker(self):
        me, opp = pair()
        me.now = 3
        me.hand = [A["offense"]]
        self.assertNotIn(A["offense"], bt.main_phase_spells(me, opp))
        on_board(me, OGRE, entered=0)
        self.assertIn(A["offense"], bt.main_phase_spells(me, opp))


class RubbleRouserTests(unittest.TestCase):
    def test_own_turn_for_lethal(self):
        me, opp = pair()
        me.turn_start = 1
        on_board(me, ROUSER)
        on_board(me, ROUSER)
        me.graveyard.extend([PLAINS, PLAINS])
        opp.life = 2
        bt.sos_main2(me, entry())
        self.assertLessEqual(opp.life, 0)

    def test_not_in_own_turn_without_lethal(self):
        me, opp = pair()
        me.turn_start = 1
        r = on_board(me, ROUSER)
        me.graveyard.append(PLAINS)
        opp.life = 5
        bt.sos_main2(me, entry())
        self.assertEqual((opp.life, r.tapped), (5, False))


if __name__ == "__main__":
    unittest.main()
