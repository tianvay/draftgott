"""Devotion (700.5): Zahl der Manasymbole einer Farbe in den Manakosten eigener Permanents; Hybrid- und
Phyrexian-Symbole zaehlen fuer jede ihrer Farben, bei zwei Farben zaehlt ein Symbol nur einmal. Kostensenkung "This
spell costs {X} less to cast, where X is your devotion to blue" (NAU Salinae, the Ocean Mother) im Goldfish und im
Kampfmodell."""
import unittest

from components import battle as bt
from components import simulation as sim
from components.cards import card_info
from components.coverage import analyze_card
from components.mana import devotion
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS = W["Plains"]
U = ("U",)


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="U"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


SALINAE_TEXT = ("This spell costs {X} less to cast, where X is your devotion to blue. (Each {U} in the mana costs of "
                "permanents you control counts toward your devotion to blue.)\nTrample\nWhenever you cast an artifact "
                "or creature spell, copy it, except the copy is a 1/1 Fish creature in addition to its other types. "
                "(The copy becomes a token.)")
SALINAE_RAW = _card("Salinae, the Ocean Mother", f"Legendary Creature {DASH} Whale God", "{6}{U}{U}", 8, "U",
                    SALINAE_TEXT, ["Trample"], "5", "7")
SALINAE = card_info(SALINAE_RAW)[0]
DUO = make("Izzet Pair", "Instant", "{3}", 3,
           "This spell costs {X} less to cast, where X is your devotion to blue and red.", colors="UR")

DRAKE = make("Twin Drake", CRE, "{2}{U}{U}", 4, "", "3", "3")  # Devotion zu Blau 2
HYBRID = make("Hybrid Sprite", CRE, "{W/U}{W/U}", 2, "", "2", "2", colors="WU")  # Weiss 2, Blau 2, Weiss+Blau 2
PHYREX = make("Phyrexian Eel", CRE, "{1}{U/P}", 2, "", "1", "1")  # Blau 1
MIXED = make("Storm Mage", CRE, "{U}{R}", 2, "", "2", "2", colors="UR")  # Blau 1, Rot 1, Blau+Rot 2
GOBLIN = make("Red Goblin", CRE, "{R}{R}", 2, "", "2", "2", colors="R")
TWO_U = make("Monohybrid", CRE, "{2/U}{2/U}", 4, "", "2", "2")  # Blau 2
RELIC = make("Blue Relic", "Artifact", "{1}{U}", 2, "{T}: Scry 1.")  # Nichtkreatur-Permanent, Blau 1
ISLAND = card_info(_card("Island", f"Basic Land {DASH} Island", text="({T}: Add {U}.)", produced=["U"]))[0]


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


class DevotionCountTests(unittest.TestCase):
    def test_plain_symbols(self):
        self.assertEqual(devotion([DRAKE], "U"), 2)
        self.assertEqual(devotion([DRAKE, PHYREX, MIXED], "U"), 4)
        self.assertEqual(devotion([GOBLIN], "U"), 0)
        self.assertEqual(devotion([ISLAND], "U"), 0)  # Laender haben keine Manakosten

    def test_hybrid_and_phyrexian_count_for_each_color(self):
        self.assertEqual(devotion([HYBRID], "U"), 2)
        self.assertEqual(devotion([HYBRID], "W"), 2)
        self.assertEqual(devotion([TWO_U], "U"), 2)
        self.assertEqual(devotion([PHYREX], "U"), 1)

    def test_two_colors_count_each_symbol_once(self):
        self.assertEqual(devotion([MIXED], "UR"), 2)
        self.assertEqual(devotion([HYBRID], "WU"), 2)  # {W/U} ist ein Symbol, nicht zwei
        self.assertEqual(devotion([DRAKE, GOBLIN], "UR"), 4)

    def test_reduced_card_keeps_its_symbols(self):
        self.assertEqual(devotion([sim.reduced(DRAKE, 2)], "U"), 2)


class ParseTests(unittest.TestCase):
    def test_self_discount(self):
        self.assertEqual(SALINAE.self_discount, ("devotion", "U"))
        self.assertEqual(DUO.self_discount, ("devotion", "UR"))
        self.assertEqual(SALINAE.mv, 8)  # Kostensenkung aendert den Manawert nicht

    def test_coverage_line_is_modelled(self):
        lines = [line for _c, _m, line in analyze_card(SALINAE_RAW)]
        self.assertFalse(any("devotion" in line for line in lines), lines)
        self.assertTrue(any("copy it" in line for line in lines))  # Fish-Kopien bleiben offen


class GoldfishTests(unittest.TestCase):
    def test_cost_reduction(self):
        self.assertEqual(sim.cost_reduction(SALINAE, perms=[DRAKE, HYBRID, GOBLIN]), 4)
        self.assertEqual(sim.cost_reduction(SALINAE), 0)
        self.assertEqual(sim.cost_reduction(DUO, perms=[MIXED, GOBLIN]), 4)

    def test_discounted_hand_counts_creatures_and_other_permanents(self):
        new, orig = sim.discounted_hand([SALINAE], [(DRAKE, 1), (GOBLIN, 1)], [0, 0], [RELIC])
        self.assertEqual(new[0].alts, ((3, (("U", 2),)),))  # {6}{U}{U} minus Devotion 3
        self.assertEqual(orig[new[0]], SALINAE)

    def test_reduction_only_lowers_generic_mana(self):
        new, _orig = sim.discounted_hand([SALINAE], [(DRAKE, 1)] * 4, [0] * 4)
        self.assertEqual(new[0].alts, ((0, (("U", 2),)),))  # Devotion 8, aber {U}{U} bleibt (601.2f)


class BattleTests(unittest.TestCase):
    def test_affordable_with_devotion(self):
        me, _opp = pair()
        me.hand, me.open = [SALINAE], [U] * 5
        self.assertFalse(bt.affordable(me, SALINAE))
        on_board(me, DRAKE)
        self.assertFalse(bt.affordable(me, SALINAE))  # 8 - 2 = 6 > 5
        me.perms.append(RELIC)
        self.assertTrue(bt.affordable(me, SALINAE))  # 8 - 3 = 5

    def test_own_reduction_counts_only_living_own_permanents(self):
        me, opp = pair()
        drake = on_board(me, DRAKE)
        on_board(opp, HYBRID)  # gegnerische Permanents zaehlen nicht
        self.assertEqual(bt.own_reduction(me, SALINAE), 2)
        drake.dead = True
        self.assertEqual(bt.own_reduction(me, SALINAE), 0)

    def test_planeswalker_counts(self):
        me, _opp = pair()
        jace = make("Blue Walker", f"Legendary Planeswalker {DASH} Jace", "{2}{U}{U}", 4, "+1: Draw a card.")
        me.walkers.append(bt.Walker(jace))
        self.assertEqual(bt.own_reduction(me, SALINAE), 2)


if __name__ == "__main__":
    unittest.main()
