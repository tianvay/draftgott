"""Kampfmodell: Karten des weiss-blauen Gegnerdecks - Cadet-Token, Koth (Leben), Lyra (Lebensgewinne), Thalia (Steuer)."""
import random
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS, ISLAND = W["Plains"], W["Island"]
CADET_TEXT = "Create a 2/2 colorless Wizard Soldier creature token named Cadet."


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=()):
    return card_info(_card(name, type_line, cost, cmc, "W", text, list(keywords), power, toughness))[0]


ENLIST = make("Enlist", "Sorcery", "{1}{W}", 2, CADET_TEXT)
FORESEER = card_info({"name": "Semester Foreseer // Peer Review", "layout": "prepare", "mana_cost": "", "cmc": 4.0,
                      "type_line": f"Creature {DASH} Human Wizard // Sorcery", "colors": ["U"], "keywords": [],
                      "card_faces": [
                          {"name": "Semester Foreseer", "type_line": f"Creature {DASH} Human Wizard",
                           "mana_cost": "{3}{U}", "power": "3", "toughness": "4",
                           "oracle_text": "This creature enters prepared.\nWhen this creature enters, surveil 1."},
                          {"name": "Peer Review", "type_line": "Sorcery", "mana_cost": "{2}{U}",
                           "oracle_text": CADET_TEXT + " Surveil 1."}]})[0]
KOTH = make("Koth of the Homestead", f"Legendary Creature {DASH} Human Citizen", "{2}{W}", 3,
            "Landfall — Whenever a land you control enters, you gain 1 life.\nWhenever a Plains you control enters, "
            "put a +1/+1 counter on target creature.", "2", "3")
LYRA = make("Lyra, Archangel of Dawn", f"Legendary Creature {DASH} Angel Knight", "{2}{W}", 3,
            "Flying\nWhenever you gain life, put a +1/+1 counter on each Angel you control.", "3", "3", ["Flying"])
ANGEL = make("Guardian Angel", f"Creature {DASH} Angel", "{3}{W}", 4, "Flying", "2", "2", ["Flying"])
THALIA = make("Thalia, the Survivor", f"Legendary Creature {DASH} Human Soldier", "{3}{W}", 4,
              "Lifelink\nNoncreature spells your opponents cast cost {1} more to cast.", "3", "4", ["Lifelink"])
INGRIS = make("Ingris", f"Legendary Creature {DASH} Human Wizard", "{2}{W}", 3,
              "{4}: Create a 2/2 colorless Wizard Soldier creature token named Cadet. Then creatures you control gain "
              "haste until end of turn.", "3", "3")
LINK1 = make("Cleric", f"Creature {DASH} Human Cleric", "{W}", 1, "Lifelink", "1", "1", ["Lifelink"])
LINK3 = make("Knight", f"Creature {DASH} Human Knight", "{2}{W}", 3, "Lifelink", "3", "4", ["Lifelink"])
BIG = make("Wall", f"Creature {DASH} Wall", "{4}", 4, "", "5", "5")
BEAR = W["Test Bear"]
BOLT = make("Bolt", "Instant", "{1}{R}", 2, "Bolt deals 3 damage to target creature.")
DIVINATION = make("Divination", "Sorcery", "{2}{U}", 3, "Draw two cards.")
OGRE = make("Ogre", f"Creature {DASH} Ogre", "{2}{R}", 3, "", "3", "3")
R = ("R",)


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


class ParseTests(unittest.TestCase):
    def test_cadet_token(self):
        n, token = ENLIST.creates_tokens[0]
        self.assertEqual((n, token.name, token.power, token.toughness, token.is_creature, token.is_token,
                          token.is_artifact, token.creature_types), (1, "Cadet", 2, 2, True, True, False,
                                                                     ("wizard", "soldier")))

    def test_prepared_copy_creates_the_token(self):
        copy = FORESEER.prepared[1]
        self.assertEqual((copy.creates_tokens[0][1].name, copy.surveil), ("Cadet", 1))

    def test_creature_types(self):
        self.assertEqual(LYRA.creature_types, ("angel", "knight"))
        self.assertEqual(BOLT.creature_types, ())

    def test_koth_lyra_thalia(self):
        self.assertEqual(KOTH.landfall_life, 1)
        self.assertIn(("type_counter", "plains", 1), KOTH.landfall)
        self.assertEqual(LYRA.lifegain_counter, (1, "angel"))
        self.assertEqual(THALIA.opp_spell_tax, 1)

    def test_ingris_ability(self):
        atoms = INGRIS.abilities[0][4]
        self.assertEqual((atoms[0][0], atoms[0][1], atoms[0][2].name, atoms[1]),
                         ("token", 1, "Cadet", ("grant", ("haste",), "all")))


class CadetTests(unittest.TestCase):
    def test_spell_creates_a_creature_token(self):
        me, opp = pair()
        bt._resolve(me, opp, ENLIST, 3, entry())
        cadet = me.creatures[0]
        self.assertEqual((cadet.card.name, cadet.entered), ("Cadet", 3))
        cadet.dead = True
        bt.bury((me,), entry())
        self.assertNotIn(cadet.card, me.graveyard)

    def test_bounced_token_vanishes(self):
        me, opp = pair()
        bt._resolve(me, opp, ENLIST, 3, entry())
        bounce = make("Unsummon", "Instant", "{U}", 1, "Return target creature to its owner's hand.")
        bt.cast_removal(bounce, opp, me, entry(), 4)
        self.assertEqual((me.creatures, me.hand), ([], []))

    def test_prepared_copy_creates_cadet(self):
        me, opp = pair()
        bt._resolve(me, opp, FORESEER, 3, entry())
        bt._resolve(me, opp, FORESEER.prepared[1], 3, entry())
        self.assertEqual([c.card.name for c in me.creatures], ["Semester Foreseer // Peer Review", "Cadet"])

    def test_ingris_makes_a_hasty_cadet_with_free_mana(self):
        me, opp = pair()
        me.lands = [PLAINS] * 4
        me.creatures = [bt.Creature(INGRIS, 0)]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 5)

    def test_ingris_at_end_of_opponents_turn(self):
        dfn, act = pair()
        dfn.creatures, dfn.open = [bt.Creature(INGRIS, 0)], [("W",)] * 4
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual([c.card.name for c in dfn.creatures], ["Ingris", "Cadet"])


class LifeTests(unittest.TestCase):
    def test_koth_gains_life_on_landfall(self):
        me, opp = pair()
        me.creatures = [bt.Creature(KOTH, 0)]
        bt.on_land(me, opp, ISLAND, 3, entry())
        self.assertEqual((me.life, me.gained), (21, 1))

    def test_lyra_counts_life_gains(self):
        me, _opp = pair()
        lyra, angel, bear = bt.Creature(LYRA, 0), bt.Creature(ANGEL, 0), bt.Creature(BEAR, 0)
        me.creatures = [lyra, angel, bear]
        bt.gain_life(me, 3)
        self.assertEqual((lyra.bonus, angel.bonus, bear.bonus), (1, 1, 0))

    def test_two_lifelinkers_trigger_twice(self):
        me, opp = pair()
        lyra = bt.Creature(LYRA, 0)
        a1, a2 = bt.Creature(LINK1, 0), bt.Creature(LINK1, 0)
        me.creatures = [lyra, a1, a2]
        pairs = [(a1, []), (a2, [])]
        bt.combat_life(me, opp, bt.resolve_combat(pairs))
        self.assertEqual((lyra.bonus, me.life), (1 + 1, 22))

    def test_one_big_lifelinker_triggers_once(self):
        me, opp = pair()
        lyra, knight = bt.Creature(LYRA, 0), bt.Creature(LINK3, 0)
        me.creatures = [lyra, knight]
        bt.combat_life(me, opp, bt.resolve_combat([(knight, [])]))
        self.assertEqual((lyra.bonus, me.life), (1, 23))

    def test_lyra_dying_in_combat_gets_no_counter(self):
        me, opp = pair()
        lyra, angel = bt.Creature(LYRA, 0), bt.Creature(ANGEL, 0)
        cleric, wall = bt.Creature(LINK1, 0), bt.Creature(BIG, 0)
        me.creatures, opp.creatures = [lyra, angel, cleric], [wall]
        res = bt.resolve_combat([(cleric, []), (lyra, [wall])])
        bt.combat_life(me, opp, res)
        self.assertTrue(lyra.dead)
        self.assertEqual((lyra.bonus, angel.bonus), (0, 1))  # Lyra loest noch aus, nur lebende Engel bekommen Marken

    def test_defending_lifelink_counts(self):
        me, opp = pair()
        lyra, cleric = bt.Creature(LYRA, 0), bt.Creature(LINK1, 0)
        opp.creatures = [lyra, cleric]
        attacker = bt.Creature(OGRE, 0)
        me.creatures = [attacker]
        bt.combat_life(me, opp, bt.resolve_combat([(attacker, [cleric])]))
        self.assertEqual((lyra.bonus, opp.life), (1, 21))

    def test_lifelink_in_a_real_turn(self):
        me, opp = pair()
        lyra = bt.Creature(LYRA, 5)  # frisch, greift nicht an
        me.creatures = [lyra, bt.Creature(LINK1, 0), bt.Creature(LINK1, 0)]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(lyra.bonus, 2)


class ThaliaTests(unittest.TestCase):
    def test_opponents_noncreature_spells_cost_more(self):
        me, opp = pair()
        opp.creatures = [bt.Creature(THALIA, 0)]
        me.hand, me.open = [BOLT], [R, R]
        self.assertFalse(bt.affordable(me, BOLT))
        me.open = [R, R, R]
        self.assertTrue(bt.affordable(me, BOLT))

    def test_creatures_and_own_spells_are_not_taxed(self):
        me, opp = pair()
        opp.creatures = [bt.Creature(THALIA, 0)]
        me.hand, me.open = [OGRE], [R, R, R]
        self.assertTrue(bt.affordable(me, OGRE))
        opp.hand, opp.open = [BOLT], [R, R]
        self.assertTrue(bt.affordable(opp, BOLT))  # Thalia besteuert nur die Gegner

    def test_tax_in_the_main_phase(self):
        me, opp = pair()
        opp.creatures = [bt.Creature(THALIA, 0)]
        me.lands, me.hand = [ISLAND] * 3, [DIVINATION]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["main1"], me.hand), ([], [DIVINATION]))
        me.lands.append(ISLAND)
        e = bt.take_turn(me, opp, 7, 4, skip_draw=True)
        self.assertEqual(e["main1"], ["Divination"])

    def test_turn_knows_the_opponent(self):
        me, opp = player(), player("Gegner")
        opp.creatures = [bt.Creature(THALIA, 0)]
        me.lands, me.hand = [ISLAND] * 3, [DIVINATION]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["main1"], [])

    def test_tax_on_exiled_cards(self):
        me, opp = pair()
        opp.creatures = [bt.Creature(THALIA, 0)]
        me.lands, me.exiled, me.exiled_from, me.graveyard[:] = [ISLAND] * 3, [DIVINATION], opp, [BEAR] * 7
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["main1"], me.exiled), ([], [DIVINATION]))

    def test_tax_on_exiled_instants(self):
        me, opp = pair()
        opp.creatures = [bt.Creature(THALIA, 0), bt.Creature(BEAR, 0)]
        me.exiled, me.exiled_from, me.graveyard[:], me.open = [BOLT], opp, [BEAR] * 7, [R, R]
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual(me.exiled, [BOLT])
        me.open = [R, R, R]
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual(me.exiled, [])

    def test_tax_on_prepared_copies(self):
        me, opp = pair()
        opp.creatures = [bt.Creature(THALIA, 0)]
        me.creatures = [bt.Creature(FORESEER, 0)]
        me.lands = [ISLAND] * 3
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["main1"], [])
        me.lands.append(ISLAND)
        me.creatures[0].prepared = True
        e = bt.take_turn(me, opp, 7, 4, skip_draw=True)
        self.assertEqual(e["main1"], ["Peer Review"])


class GameTests(unittest.TestCase):
    def test_games(self):
        deck = [PLAINS] * 8 + [ISLAND] * 9 + [ENLIST, FORESEER, KOTH, LYRA, ANGEL, THALIA, INGRIS, LINK1, LINK3,
                                              BEAR, DIVINATION, OGRE] * 2
        random.seed(17)
        r = bt.battle(deck, deck, 60, on_draw=False)
        self.assertEqual(r["wins"] + r["losses"] + r["draws"], 60)


if __name__ == "__main__":
    unittest.main()
