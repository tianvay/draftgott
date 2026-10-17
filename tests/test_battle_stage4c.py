"""Kampfmodell Stufe 4b, Paket C: Token, Mill, Enlightened Confidant und Null Summoner."""
import random
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
LEG = f"Legendary Creature {DASH} Test"
PLAINS, ISLAND = W["Plains"], W["Island"]
GR = ("G", "R")


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)", produced=[color]))[0]


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=()):
    return card_info(_card(name, type_line, cost, cmc, "G", text, list(keywords), power, toughness))[0]


FOREST, MOUNTAIN, SWAMP = land("Forest", "G"), land("Mountain", "R"), land("Swamp", "B")
TETHERMAGE = make("Tenured Tethermage", CRE, "{1}{R}{G}", 3, "When this creature enters, you may sacrifice a land. If "
                  "you do, create two tapped Heartwood tokens. (They're red and green artifacts with \"{T}: Add {R} "
                  "or {G}.\")\nTap two untapped artifacts you control: Put two +1/+1 counters on this creature.",
                  "1", "1")
VRASKA = make("Vraska, Soul of Stone", LEG, "{U}{R}{W}", 3, "Artifact creatures you control have vigilance.\nWhenever "
              "you cast a noncreature spell, create a 1/1 colorless Sculpture Treasure artifact creature token with "
              "\"{T}, Sacrifice this token: Add one mana of any color.\"", "3", "3")
WITCHSTALKER = make("Primal Witchstalker", CRE, "{1}{B}{G}", 3, "Menace\nWhen this creature enters, mill four cards. "
                    "When you do, return target land card from your graveyard to the battlefield tapped.", "2", "1",
                    ["Menace"])
CONFIDANT = make("Enlightened Confidant", CRE, "{1}{W}", 2, "Lifelink\nAt the beginning of your end step, if you "
                 "gained life this turn, surveil 1. If you put a card with mana value less than or equal to the "
                 "amount of life you gained this turn into your graveyard this way, put that card into your hand.",
                 "2", "1", ["Lifelink"])
NULL = make("Null Summoner", CRE, "{2}{U}{B}", 4, "When this creature enters, if you cast it, target opponent reveals "
            "their hand. You choose a nonland card from it. Exile that card.\nThreshold — As long as there are seven "
            "or more cards in your graveyard, you may cast the exiled card, and mana of any type can be spent to cast "
            "that spell.", "4", "2")
CONSTRUCT = make("Construct", f"Artifact Creature {DASH} Construct", "{2}", 2, "", "2", "2")
DIVINATION = make("Divination", "Sorcery", "{2}{U}", 3, "Draw two cards.")
BOLT = make("Bolt", "Instant", "{1}{R}", 2, "Bolt deals 3 damage to target creature.")
QUICK = make("Quick", "Instant", "{1}{U}", 2, "Draw a card.")
BEAR = W["Test Bear"]
OGRE = make("Ogre", CRE, "{2}{R}", 3, "", "3", "3")


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


class ParseTests(unittest.TestCase):
    def test_tethermage(self):
        n, token = TETHERMAGE.land_to_tokens
        self.assertEqual((n, token.name, token.mana_src, token.is_artifact, token.is_token), (2, "Heartwood", (GR,),
                                                                                              True, True))
        self.assertEqual(TETHERMAGE.tap_artifacts, (2, (("counter", 2, "self"),)))

    def test_vraska(self):
        token = VRASKA.cast_token
        self.assertEqual((token.name, token.power, token.toughness, token.is_creature, token.is_artifact,
                          token.sac_mana, token.is_token), ("Sculpture", 1, 1, True, True, True, True))
        self.assertTrue(VRASKA.artifact_vigilance)

    def test_others(self):
        self.assertEqual(WITCHSTALKER.mill_land, 4)
        self.assertTrue(CONFIDANT.confidant)
        self.assertTrue(NULL.null_summoner)


class TokenTests(unittest.TestCase):
    def test_tethermage_sacrifices_a_redundant_land(self):
        me, opp = player(), player("Gegner")
        me.lands = [FOREST, FOREST, MOUNTAIN]
        bt._resolve(me, opp, TETHERMAGE, 3, entry())
        self.assertEqual(me.lands, [FOREST, MOUNTAIN])
        self.assertIn(FOREST, me.graveyard)
        self.assertEqual([c.name for c in me.perms], ["Heartwood", "Heartwood"])
        self.assertEqual(bt._mana(me, 5)[0].count(GR), 2)

    def test_tethermage_prefers_a_tapped_land(self):
        me, opp = player(), player("Gegner")
        me.lands, me.open = [FOREST, FOREST, MOUNTAIN, MOUNTAIN], [("R",), ("R",)]  # Forests getappt
        bt._resolve(me, opp, TETHERMAGE, 3, entry())
        self.assertEqual((me.lands, me.open), ([FOREST, MOUNTAIN, MOUNTAIN], [("R",), ("R",)]))
        me, opp = player(), player("Gegner")
        me.lands, me.open = [FOREST, FOREST, MOUNTAIN, MOUNTAIN], [("G",), ("G",)]  # Mountains getappt
        bt._resolve(me, opp, TETHERMAGE, 3, entry())
        self.assertEqual((me.lands, me.open), ([FOREST, FOREST, MOUNTAIN], [("G",), ("G",)]))

    def test_untapped_sacrificed_land_takes_its_mana(self):
        me, opp = player(), player("Gegner")
        me.lands, me.open = [FOREST, FOREST, MOUNTAIN], [("G",), ("G",), ("R",)]
        bt._resolve(me, opp, TETHERMAGE, 3, entry())
        self.assertEqual((me.lands, sorted(me.open)), ([FOREST, MOUNTAIN], [("G",), ("R",)]))

    def test_tethermage_taps_artifacts_at_end_of_opponents_turn(self):
        dfn, act = player("Gegner"), player()
        teth = bt.Creature(TETHERMAGE, 0)
        dfn.creatures = [teth]
        dfn.perms = [TETHERMAGE.land_to_tokens[1]] * 2
        dfn.open = [GR, GR]
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual((teth.bonus, dfn.open), (2, []))

    def test_tethermage_taps_artifact_creatures(self):
        dfn, act = player("Gegner"), player()
        teth, c1, c2 = bt.Creature(TETHERMAGE, 0), bt.Creature(CONSTRUCT, 0), bt.Creature(CONSTRUCT, 0)
        dfn.creatures = [teth, c1, c2]
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual((teth.bonus, c1.tapped, c2.tapped), (2, True, True))

    def test_vraska_makes_sculptures(self):
        me, opp = player(), player("Gegner")
        me.creatures = [bt.Creature(VRASKA, 0)]
        bt._resolve(me, opp, DIVINATION, 3, entry())
        bt._resolve(me, opp, BEAR, 3, entry())
        self.assertEqual([c.card.name for c in me.creatures], ["Vraska, Soul of Stone", "Sculpture", "Test Bear"])

    def test_sculpture_is_a_treasure(self):
        me = player()
        sculpture = bt.Creature(VRASKA.cast_token, 2)
        me.creatures, me.hand, me.open, me.turn_start = [sculpture], [QUICK], [("U",)], 5
        self.assertTrue(bt.affordable(me, QUICK))
        self.assertTrue(bt._cast_from_open(me, QUICK))
        self.assertEqual((me.creatures, me.graveyard), ([], []))

    def test_sculpture_as_treasure_in_the_main_phase(self):
        me, opp = player(), player("Gegner")
        me.lands, me.hand = [PLAINS], [make("Squire", CRE, "{1}{W}", 2, "", "2", "2")]
        me.creatures = [bt.Creature(VRASKA.cast_token, 0)]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["main2"], ["Squire"])
        self.assertEqual([c.card.name for c in me.creatures], ["Squire"])

    def test_fresh_sculpture_cannot_be_sacrificed(self):
        me = player()
        me.creatures, me.hand, me.open, me.turn_start = [bt.Creature(VRASKA.cast_token, 5)], [QUICK], [("U",)], 5
        self.assertFalse(bt.affordable(me, QUICK))

    def test_artifact_vigilance(self):
        me, opp = player(), player("Gegner")
        construct = bt.Creature(CONSTRUCT, 0)
        me.creatures = [bt.Creature(VRASKA, 0), construct]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((opp.life, construct.tapped, me.creatures[0].tapped), (15, False, True))

    def test_tokens_do_not_go_to_the_graveyard(self):
        me = player()
        token = bt.Creature(VRASKA.cast_token, 0)
        token.dead = True
        me.creatures = [token]
        bt.bury((me,), entry())
        self.assertEqual((me.creatures, me.graveyard, me.deaths), ([], [], 1))


class MillTests(unittest.TestCase):
    def test_witchstalker_returns_a_land(self):
        me, opp = player(library=[BEAR, SWAMP, BEAR, FOREST, BEAR]), player("Gegner")
        me.lands = [FOREST, FOREST]
        bt._resolve(me, opp, WITCHSTALKER, 3, entry())
        self.assertEqual(me.lands, [FOREST, FOREST, SWAMP])  # neue Farbe vor einem weiteren Forest
        self.assertEqual(me.library, [BEAR])
        self.assertEqual(sorted(c.name for c in me.graveyard), ["Forest", "Test Bear", "Test Bear"])


class ConfidantTests(unittest.TestCase):
    def test_returns_surveilled_card(self):
        me = player(library=[PLAINS, BEAR])
        me.lands = [PLAINS] * 5
        me.creatures = [bt.Creature(CONFIDANT, 0)]
        bt.gain_life(me, 2)
        bt.confidant_end_step(me, entry())
        self.assertEqual((me.hand, me.library), ([PLAINS], [BEAR]))

    def test_nothing_without_life_gain(self):
        me = player(library=[PLAINS, BEAR])
        me.lands = [PLAINS] * 5
        me.creatures = [bt.Creature(CONFIDANT, 0)]
        bt.confidant_end_step(me, entry())
        self.assertEqual(me.library, [PLAINS, BEAR])

    def test_lifelink_in_a_real_turn(self):
        me, opp = player(library=[PLAINS, BEAR]), player("Gegner")
        me.lands = [PLAINS] * 5
        me.creatures = [bt.Creature(CONFIDANT, 0)]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((me.life, me.hand), (22, [PLAINS]))
        self.assertEqual(me.gained, 0)  # "this turn" endet mit dem Zug


class NullSummonerTests(unittest.TestCase):
    def test_exiles_removal_first(self):
        me, opp = player(), player("Gegner")
        opp.hand = [OGRE, BOLT, PLAINS]
        bt._resolve(me, opp, NULL, 3, entry())
        self.assertEqual((me.exiled, opp.hand), ([BOLT], [OGRE, PLAINS]))

    def test_exiles_most_expensive_otherwise(self):
        me, opp = player(), player("Gegner")
        opp.hand = [BEAR, OGRE, PLAINS]
        bt._resolve(me, opp, NULL, 3, entry())
        self.assertEqual(me.exiled, [OGRE])

    def test_threshold_casts_exiled_card_with_any_mana(self):
        me, opp = player(library=[BEAR] * 5), player("Gegner")
        me.lands, me.exiled, me.graveyard[:] = [PLAINS] * 3, [DIVINATION], [BEAR] * 7
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["main1"], me.exiled), (["Divination"], []))
        self.assertIn(DIVINATION, opp.graveyard)  # Friedhof des Besitzers
        self.assertNotIn(DIVINATION, me.graveyard)

    def test_no_cast_below_threshold(self):
        me, opp = player(library=[BEAR] * 5), player("Gegner")
        me.lands, me.exiled, me.graveyard[:] = [PLAINS] * 3, [DIVINATION], [BEAR] * 6
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["main1"], me.exiled, me.hand), ([], [DIVINATION], []))

    def test_exiled_card_stays_in_exile_without_mana(self):
        me, opp = player(library=[BEAR] * 5), player("Gegner")
        me.exiled, me.graveyard[:] = [DIVINATION], [BEAR] * 7
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((me.exiled, me.hand), ([DIVINATION], []))

    def test_exiled_creature_dies_into_owners_graveyard(self):
        me, opp = player(library=[BEAR] * 5), player("Gegner")
        me.lands, me.exiled, me.exiled_from, me.graveyard[:] = [PLAINS] * 3, [OGRE], opp, [BEAR] * 7
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        ogre = me.creatures[-1]
        self.assertEqual((ogre.card, ogre.owner), (OGRE, opp))
        ogre.dead = True
        bt.bury((me, opp), entry())
        self.assertIn(OGRE, opp.graveyard)
        self.assertNotIn(OGRE, me.graveyard)

    def test_exiled_creature_bounces_to_owners_hand(self):
        me, opp = player(), player("Gegner")
        ogre = bt.Creature(OGRE, 0)
        ogre.owner = me
        opp.creatures = [ogre]
        bounce = make("Unsummon", "Instant", "{U}", 1, "Return target creature to its owner's hand.")
        bt.cast_removal(bounce, me, opp, entry(), 5)
        self.assertEqual((me.hand, opp.hand), ([OGRE], []))

    def test_null_summoner_remembers_the_owner(self):
        me, opp = player(), player("Gegner")
        opp.hand = [BOLT]
        bt._resolve(me, opp, NULL, 3, entry())
        self.assertIs(me.exiled_from, opp)

    def test_threshold_instant_removal(self):
        me, opp = player(), player("Gegner")
        opp.creatures = [bt.Creature(BEAR, 0)]
        me.exiled, me.exiled_from, me.graveyard[:], me.open = [BOLT], opp, [BEAR] * 7, [("W",), ("W",)]
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual((me.exiled, opp.creatures), ([], []))
        self.assertIn(BOLT, opp.graveyard)


class GameTests(unittest.TestCase):
    def test_games(self):
        deck = [FOREST] * 6 + [MOUNTAIN] * 4 + [SWAMP] * 3 + [ISLAND] * 2 + [PLAINS] * 2 + \
            [TETHERMAGE, VRASKA, WITCHSTALKER, CONFIDANT, NULL, CONSTRUCT, DIVINATION, BOLT, OGRE, BEAR] * 2 + [QUICK]
        random.seed(13)
        r = bt.battle(deck, deck, 60, on_draw=False)
        self.assertEqual(r["wins"] + r["losses"] + r["draws"], 60)


if __name__ == "__main__":
    unittest.main()
