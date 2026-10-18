"""Planeswalker-Kleinkram: Tomik, Orzhov Lawmage (hoechstens ein Angreifer je eigenem Planeswalker), Entrust the Spark
(opfert nur einen Jace-Token und holt den Planeswalker mit dem hoechsten Manawert aufs Feld) und Loyal Tutor (am Ende
des gegnerischen Zugs, ohne Planeswalker auf der Hand: der teuerste, den wir naechste Runde bezahlen koennen, sonst der
billigste, oben auf die Bibliothek). Teyo legt die Marke nie auf einen Planeswalker (unveraendert)."""
import unittest
from unittest import mock

from components import battle as bt
from components import simulation as sim
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS, BEAR = W["Plains"], W["Test Bear"]


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="R"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


def walker(name, cost, cmc, loyalty, text, sub, colors="U"):
    d = _card(name, f"Legendary Planeswalker {DASH} {sub}", cost, cmc, colors, text)
    d["loyalty"] = str(loyalty)
    return card_info(d)[0]


ISLAND, MOUNTAIN, FOREST = land("Island", "U"), land("Mountain", "R"), land("Forest", "G")
OGRE = make("Ogre", CRE, "{2}{R}", 3, "", "3", "3")
TOMIK = make("Tomik, Orzhov Lawmage", f"Legendary Creature {DASH} Human Advisor", "{1}{W}", 2, "Flying\nPlaneswalkers "
             "you control have \"No more than one creature can attack this planeswalker each combat.\"\n{T}: Target "
             "creature with a +1/+1 counter on it gains flying until end of turn.", "2", "1", ["Flying"], "W")
ENTRUST = make("Entrust the Spark", "Sorcery", "{3}{G}{U}", 5, "You may sacrifice a planeswalker. If you do, search "
               "your library for a planeswalker card, put it onto the battlefield, then shuffle.", colors="GU")
SPARKS = make("Sparks", "Sorcery", "{3}", 3, "Sparks deals 2 damage to each opponent.", colors="")
TUTOR = make("Loyal Tutor", "Instant", "{W}", 1, "Search your library for a planeswalker card, reveal it, then shuffle "
             "and put that card on top.", colors="W")
MACH = make("Jace's Machinations", "Instant", "{2}{U}", 3, "Until end of turn, you may activate loyalty abilities of "
            "Jace planeswalkers you control on any player's turn any time you could cast an instant.\nEmpower Jace 8.",
            colors="U")
THEORIST = walker("The Theorist, Jace Beleren", "{2}{U}{U}", 4, 3, "At the beginning of each opponent's draw step, you "
                  "draw a card.\n+1: Create a 1/1 blue Illusion creature token.\n−2: For each opponent, return up to "
                  "one target artifact or creature that player controls to its owner's hand.\n−6: Draw three cards. "
                  "Then put X +1/+1 counters on each creature you control, where X is the number of cards in your hand.",
                  "Jace")
TORCH = walker("Chandra, Torch of Defiance", "{2}{R}{R}", 4, 4, "+1: Exile the top card of your library. You may cast "
               "that card. If you don't, Chandra deals 2 damage to each opponent.\n+1: Add {R}{R}.\n−3: Chandra deals 4 "
               "damage to target creature.\n−7: You get an emblem with \"Whenever you cast a spell, this emblem deals 5 "
               "damage to any target.\"", "Chandra", "R")
GARRUK = walker("Garruk, Curse Breaker", "{3}{G}{G}", 5, 5, "Whenever a creature you control with power 4 or greater "
                "enters, draw a card.\n+2: Untap up to two target lands.\n−3: Create a 4/4 green Beast creature token "
                "with trample.\n−4: Until your next turn, whenever one or more creatures attack one of your opponents, "
                "those creatures get +2/+2 and gain trample until end of turn.", "Garruk", "G")


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def pair():
    me, opp = player(), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


def on_board(p, card, entered=0):
    c = bt.Creature(card, entered)
    c.gy, c.ctl = p.graveyard, p
    p.creatures.append(c)
    return c


def put(p, card, loyalty=None):
    w = bt.Walker(card, 0)
    if loyalty is not None:
        w.loyalty = loyalty
    p.walkers.append(w)
    return w


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertTrue(TOMIK.tomik_guard)
        self.assertTrue(ENTRUST.entrust)
        self.assertTrue(TUTOR.pw_tutor)
        self.assertFalse(OGRE.tomik_guard or OGRE.entrust or OGRE.pw_tutor)


class TomikTests(unittest.TestCase):
    def _board(self):
        me, opp = pair()
        on_board(opp, TOMIK).tapped = True  # Tomik blockt nicht
        on_board(me, BEAR)
        on_board(me, OGRE)
        return me, opp

    def test_one_attacker_per_walker(self):
        me, opp = self._board()
        w = put(opp, THEORIST, 4)  # ohne Tomik: Bear und Ogre zusammen
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((w.loyalty, opp.life), (1, 18))  # nur der staerkste (Ogre), Bear an den Spieler

    def test_smallest_single_killer(self):
        me, opp = self._board()
        put(opp, THEORIST, 2)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((opp.walkers, opp.life), ([], 17))  # Bear toetet ihn, Ogre an den Spieler

    def test_jace_token_only_with_a_single_attacker(self):
        me, opp = self._board()
        opp.jace.loyalty = 6  # unter 3 braucht 4 Schaden: kein einzelner Angreifer reicht
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((opp.jace.loyalty, opp.life), (6, 15))

    def test_jace_token_gets_the_weakest_single_attacker(self):
        me, opp = self._board()
        opp.jace.loyalty = 2
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((opp.jace.loyalty, opp.life), (0, 17))  # Bear auf Jace, Ogre an den Spieler

    def test_without_tomik_unchanged(self):
        me, opp = pair()
        on_board(me, BEAR)
        on_board(me, OGRE)
        w = put(opp, THEORIST, 4)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((w.loyalty, opp.life), (0, 20))


class EntrustTests(unittest.TestCase):
    def _me(self, library):
        me, opp = pair()
        me.lands = [FOREST, ISLAND, PLAINS, PLAINS, PLAINS]
        me.hand = [ENTRUST]
        me.library = list(library)
        return me, opp

    def test_sacrifices_the_jace_token(self):
        me, opp = self._me([PLAINS] * 10 + [TORCH])
        me.jace.loyalty = 2
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual([w.card.name for w in me.walkers], [TORCH.name])
        self.assertEqual((me.jace.loyalty, TORCH in me.library, me.walkers[0].loyalty), (0, False, 5))

    def test_highest_mana_value(self):
        me, opp = self._me([THEORIST, PLAINS, GARRUK])
        me.jace.loyalty = 2
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual([w.card.name for w in me.walkers], [GARRUK.name])

    def test_never_a_real_walker(self):
        me, opp = self._me([PLAINS] * 10 + [TORCH])
        put(me, THEORIST, 3)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((ENTRUST in me.hand, [w.card.name for w in me.walkers]), (True, [THEORIST.name]))

    def test_needs_a_walker_in_the_library(self):
        me, opp = self._me([PLAINS] * 10)
        me.jace.loyalty = 2
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertIn(ENTRUST, me.hand)

    def test_legend_rule(self):
        me, opp = self._me([TORCH])
        me.jace.loyalty = 2
        me.walkers = []
        put(me, TORCH, 4)
        self.assertNotIn(ENTRUST, bt.main_phase_spells(me, opp))


class TutorTests(unittest.TestCase):
    def _cast(self, me, opp):
        me.open = [PLAINS.land_colors]
        bt.end_step_instants(me, opp, entry(), 6)

    def test_affordable_next_turn(self):
        me, opp = pair()
        me.lands, me.hand = [PLAINS] * 3, [TUTOR]
        me.library = [PLAINS] * 10 + [GARRUK, TORCH]
        self._cast(me, opp)
        self.assertEqual((me.library[0], TUTOR in me.graveyard), (TORCH, True))
        me.lands, me.hand = [PLAINS] * 4, [TUTOR]
        me.library = [PLAINS] * 10 + [GARRUK, TORCH]
        self._cast(me, opp)
        self.assertEqual(me.library[0], GARRUK)

    def test_cheapest_otherwise(self):
        me, opp = pair()
        me.lands, me.hand = [PLAINS], [TUTOR]
        me.library = [PLAINS] * 10 + [GARRUK, TORCH]
        self._cast(me, opp)
        self.assertEqual(me.library[0], TORCH)

    def test_not_with_a_walker_in_hand_or_none_in_library(self):
        me, opp = pair()
        me.lands, me.hand = [PLAINS] * 3, [TUTOR, TORCH]
        me.library = [PLAINS] * 10 + [GARRUK]
        self._cast(me, opp)
        self.assertIn(TUTOR, me.hand)
        me.hand, me.library = [TUTOR], [PLAINS] * 10
        self._cast(me, opp)
        self.assertIn(TUTOR, me.hand)


class GoldfishTests(unittest.TestCase):
    def _run(self, order, horizon):
        with mock.patch("components.mulligan.random.shuffle", lambda x: None):
            return sim.simulate(order, 1, False, 3, horizon, True, False, None, 11, 20, 6, True, 3, 6, False, False, 5,
                                True)

    def test_entrust(self):
        hand = [ISLAND, ISLAND, FOREST, PLAINS, MACH, ENTRUST, PLAINS]
        order = hand + [PLAINS] * 10 + [TORCH] + [PLAINS] * 10
        r = self._run(order, 6)  # R3 Jace 8, R5 Entrust opfert Jace, holt Torch: R5 und R6 je 2 Schaden
        self.assertEqual(r["effects"]["face"], 4)

    def test_entrust_not_without_jace(self):
        hand = [ISLAND, ISLAND, FOREST, PLAINS, PLAINS, ENTRUST, PLAINS]
        order = hand + [PLAINS] * 10 + [TORCH] + [PLAINS] * 10
        r = self._run(order, 6)
        self.assertEqual(r["effects"]["face"], 0)

    def test_entrust_does_not_block_other_spells(self):
        hand = [ISLAND, ISLAND, FOREST, PLAINS, ENTRUST, PLAINS, PLAINS]
        order = hand + [PLAINS, PLAINS, PLAINS, SPARKS] + [PLAINS] * 10 + [TORCH]
        r = self._run(order, 5)  # R5: ohne Jace kein Entrust, also Sparks
        self.assertEqual(r["effects"]["face"], 2)

    def test_tutor(self):
        hand = [MOUNTAIN, MOUNTAIN, PLAINS, PLAINS, TUTOR, PLAINS, PLAINS]
        order = hand + [PLAINS] * 15 + [TORCH]
        r = self._run(order, 6)  # R1 Tutor, R2 zieht Torch, R4 Torch: R4-R6 je 2 Schaden
        self.assertEqual(r["effects"]["face"], 6)


if __name__ == "__main__":
    unittest.main()
