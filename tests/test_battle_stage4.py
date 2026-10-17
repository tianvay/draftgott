"""Kampfmodell Stufe 4a: Surveil, Prepared, Treasure, Jace und Landcycling im Kampf."""
import random
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS = W["Plains"]


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=()):
    return card_info(_card(name, type_line, cost, cmc, "W", text, list(keywords), power, toughness))[0]


SURVEIL2 = make("Look Ahead", "Sorcery", "{W}", 1, "Surveil 2.")
TREASURE_MAKER = make("Pirate", CRE, "{1}{W}", 2, "When this creature enters, create a Treasure token.", "2", "1")
CYCLER = make("Big Cycler", CRE, "{5}{W}{W}", 7, "Plainscycling {2}", "6", "6", ("Plainscycling",))
TWO_DROP_INSTANT = make("Quick Draw", "Instant", "{1}{W}", 2, "Draw a card.")
BEAR = W["Test Bear"]
PREP = card_info({"name": "Scholar // Study", "layout": "prepare", "type_line": f"{CRE} // Sorcery", "mana_cost": "",
                  "cmc": 2.0, "colors": ["W"], "keywords": ["Prepared"], "card_faces": [
                      {"name": "Scholar", "type_line": CRE, "mana_cost": "{1}{W}", "power": "2", "toughness": "2",
                       "oracle_text": "This creature enters prepared."},
                      {"name": "Study", "type_line": "Sorcery", "mana_cost": "{W}", "oracle_text": "Draw a card."}]})[0]
UPKEEP_PREP = card_info({"name": "Lurker // Jab", "layout": "prepare", "type_line": f"{CRE} // Sorcery",
                         "mana_cost": "", "cmc": 1.0, "colors": ["W"], "keywords": ["Prepared"], "card_faces": [
                             {"name": "Lurker", "type_line": CRE, "mana_cost": "{W}", "power": "1", "toughness": "1",
                              "oracle_text": "At the beginning of your upkeep, if this creature isn't prepared, it "
                                             "becomes prepared."},
                             {"name": "Jab", "type_line": "Sorcery", "mana_cost": "{W}",
                              "oracle_text": "Jab deals 1 damage to target opponent."}]})[0]


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


class SurveilTests(unittest.TestCase):
    def test_spell_surveil_bins_unneeded_lands(self):
        me, opp = player(library=[PLAINS, PLAINS, BEAR]), player("Gegner")
        me.lands = [PLAINS] * 5
        bt._resolve(me, opp, SURVEIL2, 3, entry())
        self.assertEqual(me.library[0], BEAR)
        self.assertEqual(me.graveyard.count(PLAINS), 2)

    def test_land_surveil(self):
        land = card_info(_card("Backstreet", f"Land {DASH} Plains Swamp", text="When this land enters, surveil 1.",
                               produced=["W", "B"]))[0]
        me, opp = player(library=[PLAINS, BEAR]), player("Gegner")
        me.lands = [PLAINS] * 5
        bt.on_land(me, opp, land, 3, entry())
        self.assertEqual(me.library[0], BEAR)


class PreparedTests(unittest.TestCase):
    def test_enters_prepared_and_copy_is_castable(self):
        me, opp = player(), player("Gegner")
        bt._resolve(me, opp, PREP, 3, entry())
        self.assertTrue(me.creatures[0].prepared)
        copy = PREP.prepared[1]
        self.assertIn(copy, bt.main_phase_spells(me, opp))
        bt._resolve(me, opp, copy, 3, entry())
        self.assertFalse(me.creatures[0].prepared)
        self.assertNotIn(copy, me.graveyard)  # Kopien kommen nicht in den Friedhof
        self.assertEqual(len(me.hand), 1)     # Study zieht eine Karte

    def test_upkeep_prepares_again(self):
        me = player()
        me.creatures = [bt.Creature(UPKEEP_PREP, 1)]
        self.assertFalse(me.creatures[0].prepared)
        bt.upkeep(me)
        self.assertTrue(me.creatures[0].prepared)


class TreasureTests(unittest.TestCase):
    def test_treasure_is_created_and_used_for_an_instant(self):
        me, opp = player(), player("Gegner")
        bt._resolve(me, opp, TREASURE_MAKER, 3, entry())
        self.assertEqual(me.treasures, 1)
        me.hand, me.open = [TWO_DROP_INSTANT], [("W",)]
        self.assertTrue(bt.affordable(me, TWO_DROP_INSTANT))
        self.assertTrue(bt._cast_from_open(me, TWO_DROP_INSTANT))
        self.assertEqual(me.treasures, 0)

    def test_treasure_not_used_if_not_needed(self):
        me = player()
        me.treasures, me.hand, me.open = 1, [TWO_DROP_INSTANT], [("W",), ("W",)]
        bt._cast_from_open(me, TWO_DROP_INSTANT)
        self.assertEqual(me.treasures, 1)


class JaceTests(unittest.TestCase):
    def test_empower_and_draw_at_turn_start(self):
        me, opp = player(library=[BEAR, BEAR, BEAR]), player("Gegner")
        bt._resolve(me, opp, W["Test Empower Big"], 3, entry())  # Empower Jace 3
        self.assertEqual(me.jace.loyalty, 3)
        bt.jace_turn_start(me, 5)
        self.assertEqual((me.jace.loyalty, me.hand), (0, [BEAR]))

    def test_jace_counts_as_walker_for_lands(self):
        me = player()
        me.jace.add(2)
        self.assertEqual(bt.walker_flags(me), (True, True))

    def test_tethermage_grows_with_empower(self):
        me, opp = player(), player("Gegner")
        teth = make("Teth", CRE, "{2}{W}", 3, "Whenever you put one or more loyalty counters on a planeswalker, put a "
                    "+1/+1 counter on this creature.", "3", "2")
        me.creatures = [bt.Creature(teth, 1)]
        bt._resolve(me, opp, W["Test Empower"], 3, entry())
        self.assertEqual(me.creatures[0].bonus, 1)


class LandcyclingTests(unittest.TestCase):
    def test_cycle_when_no_land_for_the_drop(self):
        me, opp = player(library=[BEAR] * 5 + [PLAINS] * 5), player("Gegner")
        me.lands = [PLAINS, PLAINS]
        me.hand = [CYCLER, BEAR]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertTrue(any("Landcycling" in x for x in e["events"]))
        self.assertEqual(len(me.lands), 3)  # das geholte Land wurde gelegt
        self.assertIn(CYCLER, me.graveyard)

    def test_cycle_at_opponents_end_step(self):
        dfn, act = player("Gegner", library=[BEAR] * 5 + [PLAINS] * 5), player()
        dfn.lands = [PLAINS] * 3
        dfn.hand, dfn.open = [CYCLER, BEAR], [("W",), ("W",)]
        e = entry()
        bt.end_step_instants(dfn, act, e, 6)
        self.assertIn(CYCLER, dfn.graveyard)
        self.assertEqual(sum(c.is_land for c in dfn.hand), 1)

    def test_no_cycle_with_enough_lands(self):
        dfn, act = player("Gegner"), player()
        dfn.lands = [PLAINS] * 6
        dfn.hand, dfn.open = [CYCLER, BEAR], [("W",), ("W",)]
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertIn(CYCLER, dfn.hand)


class GameTests(unittest.TestCase):
    def test_full_games_with_all_mechanics(self):
        deck = ([PLAINS] * 16 + [CYCLER] * 2 + [PREP] * 4 + [UPKEEP_PREP] * 2 + [TREASURE_MAKER] * 4
                + [W["Test Empower"]] * 4 + [W["Test Empower Creature"]] * 4 + [SURVEIL2] * 2 + [BEAR] * 2)
        random.seed(3)
        r = bt.battle(deck, [PLAINS] * 17 + [BEAR] * 23, 80, on_draw=False)
        self.assertEqual(r["wins"] + r["losses"] + r["draws"], 80)
        events = [x for g in r["results_all"] for e in g["log"] for x in e.get("events", [])]
        self.assertTrue(any("Jace" in x for x in events))


if __name__ == "__main__":
    unittest.main()
