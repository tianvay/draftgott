"""Planeswalker-Umfeld: Liliana the Faultless (1 Leben, wenn eine andere Kreatur oder ein Planeswalker kommt, auch der
neu erschaffene Jace-Token), Liliana the Repentant (Mill 2 bei denselben Ausloesern; Exhaust {5}{B} einmal in Main 2
mit uebrigem Mana fuer eine Kreatur oder einen Planeswalker ab Manawert 4), Mabel, Bitter Recluse (bis zu 3 Marken
entfernen: Planeswalker mit hoechstens 3 Loyalty > Kreatur mit den meisten +1/+1-Marken > Planeswalker mit der meisten
Loyalty > eigene Kreatur mit Stun-Marken), Tam, the Possibility (Planeswalker-Zauber {1} billiger, 601.2f), Rewrite
Regrets (Kreatur oder Planeswalker bis Manawert 6 zurueck, Empower 2)."""
import unittest
from unittest import mock

from components import battle as bt
from components import simulation as sim
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS, BEAR = W["Plains"], W["Test Bear"]


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="B"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


def walker(name, cost, cmc, loyalty, text, sub, colors="R"):
    d = _card(name, f"Legendary Planeswalker {DASH} {sub}", cost, cmc, colors, text)
    d["loyalty"] = str(loyalty)
    return card_info(d)[0]


SWAMP, MOUNTAIN = land("Swamp", "B"), land("Mountain", "R")
FAULTLESS = make("Liliana the Faultless", f"Legendary Creature {DASH} Human Cleric", "{W}", 1, "Whenever another "
                 "creature or planeswalker you control enters, you gain 1 life.\n{1}, {T}, Discard a card: Another "
                 "target creature or planeswalker you control gains hexproof until end of turn.", "1", "2", colors="W")
REPENTANT = make("Liliana the Repentant", f"Legendary Creature {DASH} Human Warlock", "{1}{B}", 2, "Whenever another "
                 "creature or planeswalker you control enters, mill two cards.\nExhaust — {5}{B}: Return target "
                 "creature or planeswalker card from your graveyard to the battlefield. Put a +1/+1 counter on "
                 "Liliana. Activate only as a sorcery. (Activate each exhaust ability only once.)", "2", "2")
MABEL = make("Mabel, Bitter Recluse", f"Legendary Creature {DASH} Mouse Warlock", "{B}", 1, "Deathtouch\nWhen Mabel "
             "enters, remove up to three counters from another target creature or planeswalker.", "1", "1",
             ["Deathtouch"])
TAM = make("Tam, the Possibility", f"Legendary Creature {DASH} Gorgon Wizard", "{1}{G}{U}", 3, "Planeswalker spells "
           "you cast cost {1} less to cast.\n{W}{U}{B}{R}{G}, {T}: Proliferate X times, where X is the number of "
           "planeswalker types among planeswalkers you control.", "2", "3", colors="GU")
REGRETS = make("Rewrite Regrets", "Sorcery", "{3}{B}", 4, "Return target creature or planeswalker card with mana value "
               "6 or less from your graveyard to the battlefield.\nEmpower Jace 2.")
HEALER = make("Healer", CRE, "{1}{W}", 2, "Whenever another creature you control enters, you gain 1 life.", "1", "1",
              colors="W")
TITAN = make("Titan", CRE, "{4}{B}", 5, "", "5", "5")
OGRE = make("Ogre", CRE, "{2}{B}", 3, "", "3", "3")
ELDER = make("Elder", CRE, "{6}{B}", 7, "", "7", "7")
RAT = make("Rat", CRE, "{B}", 1, "", "1", "1")
TORCH = walker("Chandra, Torch of Defiance", "{2}{R}{R}", 4, 4, "+1: Exile the top card of your library. You may cast "
               "that card. If you don't, Chandra deals 2 damage to each opponent.\n+1: Add {R}{R}.\n−3: Chandra deals 4 "
               "damage to target creature.\n−7: You get an emblem with \"Whenever you cast a spell, this emblem deals 5 "
               "damage to any target.\"", "Chandra")
THEORIST = walker("The Theorist, Jace Beleren", "{2}{U}{U}", 4, 3, "+1: Create a 1/1 blue Illusion creature token.",
                  "Jace", "U")
GARRUK = walker("Garruk, Curse Breaker", "{3}{G}{G}", 5, 5, "+2: Untap up to two target lands.", "Garruk", "G")


def player(name="Wir"):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], [PLAINS] * 20
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
        self.assertEqual((FAULTLESS.ally_enter_life, FAULTLESS.enter_pw_too), (1, True))
        self.assertEqual((REPENTANT.ally_enter_mill, REPENTANT.enter_pw_too), (2, True))
        self.assertEqual(REPENTANT.exhaust_reanimate[1], "creature_pw")
        self.assertEqual(MABEL.etb_remove_counters, 3)
        self.assertEqual(TAM.pw_discount, 1)
        self.assertEqual(REGRETS.reanimate, ("target", "creature_pw", 6, "battlefield", 0))
        self.assertFalse(BEAR.enter_pw_too or BEAR.ally_enter_mill or BEAR.pw_discount)


class FaultlessTests(unittest.TestCase):
    def test_creature_walker_and_new_jace_token(self):
        me, opp = pair()
        on_board(me, FAULTLESS)
        bt._resolve(me, opp, BEAR, 3, entry())
        self.assertEqual(me.life, 21)
        bt._resolve(me, opp, TORCH, 3, entry())
        self.assertEqual(me.life, 22)
        bt._jace_add(me, 2, entry())  # Jace-Token wird erschaffen
        self.assertEqual(me.life, 23)
        bt._jace_add(me, 2, entry())  # schon da: kein neuer Token
        self.assertEqual(me.life, 23)

    def test_creature_only_trigger_ignores_walkers(self):
        me, opp = pair()
        on_board(me, HEALER)
        bt._resolve(me, opp, TORCH, 3, entry())
        self.assertEqual(me.life, 20)

    def test_not_for_itself(self):
        me, opp = pair()
        bt._resolve(me, opp, FAULTLESS, 3, entry())
        self.assertEqual(me.life, 20)


class RepentantTests(unittest.TestCase):
    def test_mill_two(self):
        me, opp = pair()
        bt._resolve(me, opp, REPENTANT, 3, entry())
        self.assertEqual(len(me.library), 20)  # nicht fuer sich selbst
        bt._resolve(me, opp, BEAR, 3, entry())
        bt._resolve(me, opp, TORCH, 3, entry())
        bt._jace_add(me, 1, entry())
        self.assertEqual((len(me.library), len(me.graveyard)), (14, 6))

    def test_exhaust_once_for_mana_value_four_or_more(self):
        me, opp = pair()
        lili = on_board(me, REPENTANT)
        me.lands, me.graveyard = [SWAMP] * 6, [OGRE, TITAN]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((sorted(c.card.name for c in me.creatures), lili.bonus, me.graveyard),
                         (["Liliana the Repentant", "Titan"], 1, [OGRE, PLAINS, PLAINS]))  # Titan loest Mill 2 aus
        me.graveyard.append(TITAN._replace(name="Titan II"))
        bt.take_turn(me, opp, 7, 4, skip_draw=True)
        self.assertEqual(len(me.creatures), 2)  # Exhaust nur einmal (702.177)

    def test_exhaust_not_for_small_cards_or_without_mana(self):
        me, opp = pair()
        on_board(me, REPENTANT)
        me.lands, me.graveyard = [SWAMP] * 6, [OGRE]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(len(me.creatures), 1)
        me.lands, me.graveyard = [SWAMP] * 5, [TITAN]
        bt.take_turn(me, opp, 7, 4, skip_draw=True)
        self.assertEqual(len(me.creatures), 1)

    def test_exhaust_returns_a_walker(self):
        me, opp = pair()
        on_board(me, REPENTANT)
        me.lands, me.graveyard = [SWAMP] * 6, [TORCH]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(([w.card.name for w in me.walkers], me.walkers[0].loyalty), ([TORCH.name], 5))  # +1 danach


class MabelTests(unittest.TestCase):
    def _enter(self, me, opp):
        bt._resolve(me, opp, MABEL, 3, entry())

    def test_kills_a_small_walker_first(self):
        me, opp = pair()
        put(opp, THEORIST, 3)
        ogre = on_board(opp, OGRE)
        ogre.bonus = 2
        self._enter(me, opp)
        self.assertEqual((opp.walkers, ogre.bonus), ([], 2))

    def test_kills_a_small_jace_token(self):
        me, opp = pair()
        opp.jace.loyalty = 3
        self._enter(me, opp)
        self.assertEqual(opp.jace.loyalty, 0)

    def test_small_jace_token_before_counters(self):
        me, opp = pair()
        opp.jace.loyalty = 3
        ogre = on_board(opp, OGRE)
        ogre.bonus = 2
        self._enter(me, opp)
        self.assertEqual((opp.jace.loyalty, ogre.bonus), (0, 2))

    def test_then_the_creature_with_most_counters(self):
        me, opp = pair()
        put(opp, GARRUK, 5)
        a, b = on_board(opp, OGRE), on_board(opp, BEAR)
        a.bonus, b.bonus = 1, 4
        self._enter(me, opp)
        self.assertEqual((a.bonus, b.bonus, opp.walkers[0].loyalty), (1, 1, 5))

    def test_then_the_walker_with_most_loyalty(self):
        me, opp = pair()
        put(opp, GARRUK, 5)
        put(opp, TORCH, 4)
        self._enter(me, opp)
        self.assertEqual([w.loyalty for w in opp.walkers], [2, 4])

    def test_last_own_stun_counters(self):
        me, opp = pair()
        mine = on_board(me, OGRE)
        mine.stun = 2
        self._enter(me, opp)
        self.assertEqual(mine.stun, 0)


class TamTests(unittest.TestCase):
    def test_walker_one_cheaper(self):
        me, opp = pair()
        on_board(me, TAM)
        me.lands, me.hand = [MOUNTAIN] * 3, [TORCH]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual([w.card.name for w in me.walkers], [TORCH.name])
        self.assertEqual(TORCH.mv, 4)  # Manawert bleibt

    def test_not_for_other_spells(self):
        me, opp = pair()
        on_board(me, TAM)
        me.lands, me.hand = [SWAMP] * 2, [OGRE]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertIn(OGRE, me.hand)

    def test_goldfish(self):
        hand, _back = sim.discounted_hand([TORCH, OGRE], [(TAM, 1)], [0])
        self.assertEqual((sorted(g for g, _c in hand[0].alts), hand[1]), ([1], OGRE))


class RegretsTests(unittest.TestCase):
    def test_returns_a_walker_and_empowers(self):
        me, opp = pair()
        me.lands, me.hand, me.graveyard = [SWAMP] * 4, [REGRETS], [TORCH, OGRE]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual([w.card.name for w in me.walkers], [TORCH.name])
        self.assertGreaterEqual(me.jace.loyalty, 1)  # Empower 2, danach ggf. Surveil

    def test_not_above_mana_value_six(self):
        me, opp = pair()
        me.graveyard = [ELDER]
        self.assertFalse(bt.reanimate_ok(me, REGRETS))
        me.graveyard = [TITAN]
        self.assertTrue(bt.reanimate_ok(me, REGRETS))


class GoldfishTests(unittest.TestCase):
    def test_repentant_mills_in_the_goldfish(self):
        hand = [SWAMP, SWAMP, SWAMP, REPENTANT, RAT, RAT, PLAINS]  # R1 Rat, R2 Liliana, R3 zweite Rat
        with mock.patch("components.mulligan.random.shuffle", lambda x: None):
            r = sim.simulate(hand + [PLAINS] * 20, 1, False, 3, 5, True, False, None, 11, 20, 6, True, 3, 6, False,
                             False, 5, True)
        self.assertEqual(r["graveyard"]["size"][3], 2)  # Mill 2 fuer die zweite Rat


if __name__ == "__main__":
    unittest.main()
