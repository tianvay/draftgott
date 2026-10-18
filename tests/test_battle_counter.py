"""Kampfmodell L1: Counterspells. Gekontert wird (Prioritaet): ein Zauber, der Lethal bringt (Schaden am Spieler,
Kampftrick, Kreatur mit Haste vor dem Kampf), Removal auf unsere gefaehrlichste Kreatur (auch Massenremoval), eine
Kreatur ab Manawert 3. Weiche Counter ("unless its controller pays {N}") nur, wenn der Zaubernde nicht zahlen kann.
Ab Runde 5 halten wir Mana fuer den billigsten Counterspell frei. Keine Gegenkonter (ein Counterspell ist keiner
der drei Faelle)."""
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS = W["Plains"]
U = ("U",)


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="R"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


ISLAND, FOREST, SWAMP = land("Island", "U"), land("Forest", "G"), land("Swamp", "B")
BEAR = W["Test Bear"]
OGRE = make("Ogre", CRE, "{2}{R}", 3, "", "3", "3")
WHITE_OGRE = make("White Ogre", CRE, "{2}{W}", 3, "", "3", "3", colors="W")
TITAN = make("Titan", CRE, "{4}{G}", 5, "", "5", "5", colors="G")
BIRD = make("Bird", CRE, "{1}{W}", 2, "Flying", "1", "1", ["Flying"], "W")
RUNNER = make("Runner", CRE, "{1}{R}", 2, "Haste", "2", "2", ["Haste"])
FOUR = make("Big Bat", CRE, "{3}{U}", 4, "", "4", "4", colors="U")
BOLT = make("Bolt", "Instant", "{R}", 1, "Bolt deals 3 damage to any target.")
SLAY = make("Slay", "Sorcery", "{1}{B}", 2, "Destroy target creature.", colors="B")
KILL = make("Murder", "Instant", "{1}{B}", 2, "Destroy target creature.", colors="B")
SNIPE = make("Snipe", "Sorcery", "{1}{G}", 2, "Destroy target creature with flying.", colors="G")
WIPE = make("Wipe", "Sorcery", "{3}{W}", 4, "Destroy all creatures.", colors="W")
PUMP = make("Giant Growth", "Instant", "{G}", 1, "Target creature gets +3/+3 until end of turn.", colors="G")
PROWLER = make("Prowler", CRE, "{1}{B}", 2, "Prowess", "1", "1", ["Prowess"], "B")

REDACTION = make("Precise Redaction", "Instant", "{1}{U}", 2, "Counter target white or black spell.", colors="U")
SCULPT = make("Countersculpt", "Instant", "{U}{U}", 2, "As an additional cost to cast this spell, behold a Jace or "
              "pay {1}. (To behold a Jace, choose a Jace you control or reveal a Jace card from your hand.)\nCounter "
              "target spell. Empower Jace 1.", colors="U")
ICY = make("Icy Reception", "Instant", "{1}{U}", 2, "Choose one —\n• Counter target creature or legendary spell unless "
           "its controller pays {3}.\n• Target creature gets -5/-0 until end of turn.", colors="U")
THEORIX = make("Theorix Charm", "Instant", "{U}{B}", 2, "Choose one —\n• Counter target noncreature spell unless its "
               "controller pays {2}.\n• Target creature gets -2/-2 until end of turn.\n• Mill three cards, then draw "
               "a card.", colors="U")
MAGECRUSHER = make("Ruric Thar, Magecrusher", f"Legendary Creature {DASH} Ogre Warrior", "{5}{G}{G}", 7,
                   "This spell can't be countered.\nReach, vigilance, trample", "7", "7",
                   ["Reach", "Vigilance", "Trample"], "G")


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


def holder(opp, counter, mana=3):
    opp.hand, opp.open = [counter], [U] * mana


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertEqual(REDACTION.counter, ("any", ("B", "W"), 0))
        self.assertEqual(SCULPT.counter, ("any", (), 0))
        self.assertTrue(SCULPT.behold_jace)
        self.assertEqual(ICY.choices[1][0].counter, ("creature_or_legendary", (), 3))
        self.assertEqual(THEORIX.choices[1][0].counter, ("noncreature", (), 2))
        self.assertTrue(MAGECRUSHER.uncounterable)
        self.assertEqual(OGRE.counter, ())


class WhatWeCounterTests(unittest.TestCase):
    def test_creature_of_three_is_countered(self):
        me, opp = pair()
        holder(opp, SCULPT)
        bt._resolve(me, opp, OGRE, 3, entry())
        self.assertEqual((me.creatures, me.graveyard, opp.graveyard, opp.open), ([], [OGRE], [SCULPT], []))
        self.assertEqual(opp.jace.loyalty, 1)  # Empower Jace 1

    def test_small_creature_is_not(self):
        me, opp = pair()
        holder(opp, SCULPT)
        bt._resolve(me, opp, BEAR, 3, entry())
        self.assertEqual((len(me.creatures), opp.hand), (1, [SCULPT]))

    def test_redaction_only_white_or_black(self):
        me, opp = pair()
        holder(opp, REDACTION)
        bt._resolve(me, opp, OGRE, 3, entry())
        self.assertEqual(len(me.creatures), 1)
        bt._resolve(me, opp, WHITE_OGRE, 3, entry())
        self.assertEqual((len(me.creatures), WHITE_OGRE in me.graveyard), (1, True))

    def test_lethal_burn(self):
        me, opp = pair()
        holder(opp, SCULPT)
        opp.life = 3
        bt._resolve(me, opp, BOLT, 3, entry())
        self.assertEqual((opp.life, opp.hand), (3, []))

    def test_x_burn_counts_with_our_lands(self):
        me, opp = pair()
        fireball = make("Fireball", "Sorcery", "{X}{R}", 1, "Fireball deals X damage to any target.")
        me.lands = [FOREST] * 5
        holder(opp, SCULPT)
        opp.life = 5
        bt._resolve(me, opp, fireball, 3, entry())
        self.assertEqual((opp.life, opp.hand), (5, []))

    def test_burn_that_is_not_lethal(self):
        me, opp = pair()
        holder(opp, SCULPT)
        bt._resolve(me, opp, BOLT, 3, entry())
        self.assertEqual((opp.life, opp.hand), (17, [SCULPT]))

    def test_removal_on_our_most_dangerous_creature(self):
        me, opp = pair()
        titan = on_board(opp, TITAN)
        on_board(opp, BEAR)
        holder(opp, SCULPT)
        bt._resolve(me, opp, SLAY, 3, entry())
        self.assertEqual((titan in opp.creatures, opp.hand), (True, []))

    def test_removal_on_a_lesser_creature(self):
        me, opp = pair()
        on_board(opp, TITAN)
        bird = on_board(opp, BIRD)
        holder(opp, SCULPT)
        bt._resolve(me, opp, SNIPE, 3, entry())
        self.assertEqual((bird in opp.creatures, opp.hand), (False, [SCULPT]))

    def test_sweeper_that_kills_our_best(self):
        me, opp = pair()
        titan = on_board(opp, TITAN)
        holder(opp, SCULPT, mana=4)
        bt._resolve(me, opp, WIPE, 3, entry())
        self.assertIn(titan, opp.creatures)

    def test_sweeper_kills_even_hexproof(self):
        me, opp = pair()
        guard = make("Guard", CRE, "{3}{G}", 4, "Hexproof", "4", "4", ["Hexproof"], "G")
        g = on_board(opp, guard)
        holder(opp, SCULPT, mana=4)
        bt._resolve(me, opp, WIPE, 3, entry())
        self.assertIn(g, opp.creatures)

    def test_haste_creature_that_brings_lethal(self):
        me, opp = pair()
        holder(opp, SCULPT)
        opp.life = 2
        bt._resolve(me, opp, RUNNER, 3, entry())
        self.assertEqual(me.creatures, [])
        opp.life = 5
        opp.hand, opp.open = [SCULPT], [U] * 3
        bt._resolve(me, opp, RUNNER, 3, entry())
        self.assertEqual(len(me.creatures), 1)

    def test_lethal_combat_trick(self):
        me, opp = pair()
        on_board(me, BEAR)
        me.lands, me.hand = [FOREST], [PUMP]
        holder(opp, SCULPT)
        opp.life = 4
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((opp.life, PUMP in me.graveyard, opp.hand), (2, True, []))


class HowWeCounterTests(unittest.TestCase):
    def test_soft_counter_only_if_caster_cannot_pay(self):
        me, opp = pair()
        holder(opp, ICY)
        me.open = [U] * 3
        bt._resolve(me, opp, OGRE, 3, entry())
        self.assertEqual((len(me.creatures), opp.hand), (1, [ICY]))
        me.open = [U] * 2
        bt._resolve(me, opp, OGRE, 3, entry())
        self.assertEqual((len(me.creatures), opp.hand), (1, []))

    def test_creature_counter_cannot_hit_sorceries(self):
        me, opp = pair()
        on_board(opp, TITAN)
        holder(opp, ICY)
        bt._resolve(me, opp, SLAY, 3, entry())
        self.assertEqual((opp.creatures, opp.hand), ([], [ICY]))

    def test_counter_is_not_wasted_in_the_end_step(self):
        me, opp = pair()
        me.hand, me.open = [SCULPT], [U] * 3
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual(me.hand, [SCULPT])

    def test_noncreature_counter_cannot_hit_creatures(self):
        me, opp = pair()
        opp.hand, opp.open = [THEORIX], [U, ("B",), U]
        bt._resolve(me, opp, OGRE, 3, entry())
        self.assertEqual((len(me.creatures), opp.hand), (1, [THEORIX]))
        on_board(opp, TITAN)
        bt._resolve(me, opp, SLAY, 3, entry())
        self.assertEqual((len(opp.creatures), opp.hand), (1, []))

    def test_behold_a_jace_saves_one_mana(self):
        me, opp = pair()
        holder(opp, SCULPT, mana=2)
        bt._resolve(me, opp, OGRE, 3, entry())
        self.assertEqual(len(me.creatures), 1)  # ohne Jace: {U}{U} + {1}
        me.creatures = []
        opp.jace.loyalty = 2
        bt._resolve(me, opp, OGRE, 3, entry())
        self.assertEqual((me.creatures, opp.open), ([], []))

    def test_cannot_be_countered(self):
        me, opp = pair()
        holder(opp, SCULPT)
        bt._resolve(me, opp, MAGECRUSHER, 3, entry())
        self.assertEqual((len(me.creatures), opp.hand), (1, [SCULPT]))

    def test_cast_triggers_still_happen(self):
        me, opp = pair()
        prowler = on_board(me, PROWLER)
        on_board(opp, TITAN)
        holder(opp, SCULPT)
        bt._resolve(me, opp, SLAY, 3, entry())
        self.assertEqual((prowler.power, len(opp.creatures)), (2, 1))

    def test_instant_removal_in_the_end_step(self):
        me, opp = pair()
        titan = on_board(opp, TITAN)
        me.hand, me.open = [KILL], [("B",)] * 2
        holder(opp, SCULPT)
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual((titan in opp.creatures, KILL in me.graveyard), (True, True))

    def test_no_counter_wars(self):
        me, opp = pair()
        holder(opp, SCULPT)
        me.hand, me.open = [SCULPT], [U] * 3
        bt._resolve(me, opp, OGRE, 3, entry())
        self.assertEqual((me.creatures, me.hand), ([], [SCULPT]))


class HoldTests(unittest.TestCase):
    def test_hold_from_round_five(self):
        me, opp = pair()
        me.lands, me.hand = [ISLAND] * 4, [FOUR, SCULPT]
        e = bt.take_turn(me, opp, 9, 5, skip_draw=True)
        self.assertEqual((e["main2"], len(me.open)), ([], 4))

    def test_no_hold_before_round_five(self):
        me, opp = pair()
        me.lands, me.hand = [ISLAND] * 4, [FOUR, SCULPT]
        e = bt.take_turn(me, opp, 7, 4, skip_draw=True)
        self.assertEqual(e["main2"], ["Big Bat"])

    def test_hold_removal_and_counter(self):
        me, opp = pair()
        on_board(opp, OGRE).tapped = True
        me.lands, me.hand = [ISLAND] * 3 + [SWAMP] * 3, [FOUR, KILL, SCULPT]
        e = bt.take_turn(me, opp, 9, 5, skip_draw=True)
        self.assertEqual((e["main2"], len(me.open)), ([], 6))

    def test_only_counter_when_mana_is_short(self):
        me, opp = pair()
        on_board(opp, OGRE).tapped = True
        cheap = make("Small Bat", f"Artifact Creature {DASH} Test", "{1}", 1, "", "1", "1", colors="")
        me.lands, me.hand = [ISLAND] * 3 + [SWAMP], [cheap, KILL, SCULPT]
        e = bt.take_turn(me, opp, 9, 5, skip_draw=True)
        self.assertEqual((e["main2"], len(me.open)), (["Small Bat"], 3))
        self.assertIn("Wir: hält 3 Mana für Countersculpt offen", e["events"])
        self.assertFalse(any("für Murder" in ev for ev in e["events"]))


    def test_held_removal_cost_is_not_discounted_twice(self):
        me, opp = pair()
        geist = make("Geist of Saint Thalia", f"Legendary Creature {DASH} Spirit Cleric", "{1}{U}", 2,
                     "Flying\nNoncreature spells you cast cost {1} less to cast.", "1", "2", ["Flying"], "U")
        on_board(me, geist, entered=9)  # frisch: greift nicht an
        on_board(opp, OGRE).tapped = True
        doom = make("Doom", "Instant", "{2}{B}", 3, "Destroy target creature.", colors="B")
        three = make("Black Brute", CRE, "{2}{B}", 3, "", "3", "3", colors="B")
        me.lands, me.hand = [SWAMP] * 4, [doom, three]
        e = bt.take_turn(me, opp, 9, 4, skip_draw=True)
        self.assertEqual((e["main2"], len(me.open)), ([], 4))  # Doom kostet mit Geist 2, nicht 1


if __name__ == "__main__":
    unittest.main()
