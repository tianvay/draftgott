"""Kampfmodell Paket M, Teil 2: Loot und Rummage (Arni Humble Scribe, Hallway Heckler, Marwyn the Clearcutter,
Improvised Act), Faehigkeiten fuer Ausweichen und Pump (Eardrum Rattler, Tomik, Pia), Ausloeser beim Betreten anderer
Kreaturen (Arni Renowned Champion, Gideon the Oathless) und Ward (702.21)."""
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS = W["Plains"]
B, R, WH = ("B",), ("R",), ("W",)


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="R"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


SWAMP, MOUNTAIN, FOREST = land("Swamp", "B"), land("Mountain", "R"), land("Forest", "G")
BEAR = W["Test Bear"]
TITAN = make("Titan", CRE, "{4}{G}", 5, "", "5", "5", colors="G")
WALL = make("Wall", CRE, "{2}{W}", 3, "", "3", "3", colors="W")
OGRE = make("Ogre", CRE, "{2}{R}", 3, "", "3", "3")
BIG = make("Big Ground", CRE, "{3}{G}", 4, "", "4", "4", colors="G")
KILL = make("Murder", "Instant", "{1}{B}", 2, "Destroy target creature.", colors="B")
SLAY = make("Slay", "Sorcery", "{1}{B}", 2, "Destroy target creature.", colors="B")
SHOCKER = make("Shocker", CRE, "{2}{R}", 3, "When this creature enters, it deals 3 damage to target creature.", "2",
               "2")
ARTIFACT = make("Trinket", "Artifact", "{1}", 1, "", colors="")

SCRIBE = make("Arni, Humble Scribe", f"Legendary Creature {DASH} Human Wizard", "{2}{U}", 3,
              "Whenever another nontoken creature you control enters, untap Arni.\n{T}: Draw a card, then discard a "
              "card.", "1", "3", colors="U")
HECKLER = make("Hallway Heckler", f"Creature {DASH} Elemental Sorcerer", "{2}{R}", 3, "{T}, Discard a card: Draw a "
               "card.", "2", "2")
CLEARCUTTER = make("Marwyn, the Clearcutter", f"Legendary Creature {DASH} Elf Warrior", "{R}", 1,
                   "{2}, {T}, Sacrifice an artifact or land: Draw a card.", "1", "1")
ACT = make("Improvised Act", "Sorcery", "{R}", 1, "You may discard a card. If you do, draw a card.")
RATTLER = make("Eardrum Rattler", f"Creature {DASH} Human Bard", "{1}{R}", 2, "{1}, {T}: Another target creature "
               "you control with power 2 or less can't be blocked this turn.", "2", "2")
TOMIK = make("Tomik, Orzhov Lawmage", f"Legendary Creature {DASH} Human Advisor", "{1}{W}", 2,
             "Flying\nPlaneswalkers you control have \"No more than one creature can attack this planeswalker each "
             "combat.\"\n{T}: Target creature with a +1/+1 counter on it gains flying until end of turn.", "2", "3",
             ["Flying"], "W")
PIA = make("Pia, Determined Rebuilder", f"Legendary Creature {DASH} Human Artificer", "{2}{R}", 3,
           "When Pia enters, create a 1/1 colorless Thopter artifact creature token with flying.\n{5}{R}: Target "
           "creature gets +X/+0 until end of turn, where X is the number of artifacts you control.", "2", "2")
CHAMPION = make("Arni, Renowned Champion", f"Legendary Creature {DASH} Human Berserker", "{3}{R}", 4,
                "Trample\nWhenever another creature you control enters, Arni gets +X/+0 until end of turn, where X is "
                "that creature's power.", "3", "3", ["Trample"])
GIDEON = make("Gideon the Oathless", f"Legendary Creature {DASH} Human Mercenary", "{2}{B}", 3,
              "Ward—Discard a card.\nWhenever a creature an opponent controls enters, Gideon deals 1 damage to that "
              "player.\nWhenever an opponent activates a loyalty ability, Gideon deals 1 damage to that player.", "3",
              "3", ["Ward"], "B")
GECKO = make("Wrecking Gecko", f"Artifact Creature {DASH} Lizard Construct", "{4}{G}", 5, "Ward {2} (Whenever this "
             "creature becomes the target of a spell or ability an opponent controls, counter it unless that player "
             "pays {2}.)", "4", "4", ["Ward"], "G")
HORTI = make("Unflinching Hortimancer", f"Creature {DASH} Human Cleric", "{1}{W}", 2, "Ward {1}\nWhenever you gain "
             "life, put a +1/+1 counter on this creature.", "2", "2", ["Ward"], "W")


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


class ParseTests(unittest.TestCase):
    def test_draw_abilities(self):
        self.assertEqual(SCRIBE.draw_abilities, ((((0, ()),), True, "loot"),))
        self.assertTrue(SCRIBE.ally_untap)
        self.assertEqual(HECKLER.draw_abilities, ((((0, ()),), True, "rummage"),))
        self.assertEqual(CLEARCUTTER.draw_abilities, ((((2, ()),), True, "sac_land"),))
        self.assertTrue(ACT.rummage_spell)

    def test_abilities(self):
        self.assertEqual(RATTLER.abilities[0][4], (("grant", ("unblockable",), "pow_le_2"),))
        self.assertEqual(RATTLER.abilities[0][2], True)
        self.assertEqual(TOMIK.abilities[0][4], (("grant", ("flying",), "target_counter"),))
        self.assertEqual(PIA.abilities[0][4], (("pump", "artifacts", 0, "target"),))

    def test_enter_and_ward(self):
        self.assertTrue(CHAMPION.ally_enter_pump)
        self.assertEqual((GIDEON.opp_enter_ping, GIDEON.opp_loyalty_ping, GIDEON.ward), (1, 1, ("discard",)))
        self.assertEqual((GECKO.ward, HORTI.ward), (("mana", 2), ("mana", 1)))


class LootTests(unittest.TestCase):
    def test_scribe_loots_at_the_end_of_the_opponents_turn(self):
        me, opp = pair()
        scribe = on_board(me, SCRIBE)
        me.turn_start, me.lands, me.hand = 1, [PLAINS] * 5, [TITAN]
        bt.end_step_instants(me, opp, entry(), 2)
        self.assertEqual((me.hand, me.graveyard, scribe.tapped, len(me.library)), ([TITAN], [PLAINS], True, 19))

    def test_scribe_cast_in_our_last_turn_cannot_tap(self):
        me, opp = pair()
        scribe = on_board(me, SCRIBE, entered=1)  # 302.6: nicht seit Beginn unseres letzten Zugs unter Kontrolle
        me.turn_start = 1
        bt.end_step_instants(me, opp, entry(), 2)
        self.assertEqual((scribe.tapped, len(me.library)), (False, 20))

    def test_scribe_loots_in_our_turn_when_a_creature_follows(self):
        me, opp = pair()
        scribe = on_board(me, SCRIBE)
        me.lands, me.hand = [PLAINS], [BEAR]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["damage"], scribe.tapped, me.graveyard), (0, False, [PLAINS]))

    def test_scribe_attacks_without_creature_to_cast(self):
        me, opp = pair()
        on_board(me, SCRIBE)
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["damage"], me.graveyard), (1, []))

    def test_heckler_rummages_only_a_surplus_land(self):
        me, opp = pair()
        heckler = on_board(me, HECKLER)
        me.turn_start, me.lands, me.hand = 1, [PLAINS] * 3, [BEAR]
        bt.end_step_instants(me, opp, entry(), 2)
        self.assertEqual((heckler.tapped, me.hand), (False, [BEAR]))
        me.lands, me.hand = [], [TITAN, PLAINS]  # Land auf der Hand, aber nicht ueberzaehlig
        bt.end_step_instants(me, opp, entry(), 2)
        self.assertEqual((heckler.tapped, me.hand), (False, [TITAN, PLAINS]))
        me.lands, me.hand = [PLAINS] * 3, [BEAR, PLAINS]
        bt.end_step_instants(me, opp, entry(), 2)
        self.assertEqual((heckler.tapped, me.hand, me.graveyard), (True, [BEAR, PLAINS], [PLAINS]))

    def test_clearcutter_sacrifices_a_land_when_flooded(self):
        me, opp = pair()
        cutter = on_board(me, CLEARCUTTER)
        me.turn_start, me.lands, me.hand, me.open = 1, [PLAINS] * 5, [BEAR], [WH] * 2
        bt.end_step_instants(me, opp, entry(), 2)
        self.assertEqual((cutter.tapped, len(me.lands)), (False, 5))
        me.lands = [PLAINS] * 6
        bt.end_step_instants(me, opp, entry(), 2)
        self.assertEqual((cutter.tapped, len(me.lands), len(me.hand), me.open), (True, 5, 2, []))

    def test_rummage_spell(self):
        me, opp = pair()
        me.hand = [BEAR]
        bt._resolve(me, opp, ACT, 3, entry())
        self.assertEqual(me.hand, [BEAR])
        me.hand = [BEAR, PLAINS]
        bt._resolve(me, opp, ACT, 3, entry())
        self.assertEqual((len(me.hand), PLAINS in me.graveyard), (2, True))

    def test_rummage_spell_only_cast_with_a_surplus_land(self):
        me, opp = pair()
        me.lands, me.hand = [MOUNTAIN], [ACT]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["main1"], [])
        me.hand = [ACT, MOUNTAIN, MOUNTAIN]
        e = bt.take_turn(me, opp, 7, 4, skip_draw=True)
        self.assertEqual(e["main1"], ["Improvised Act"])


class EvasionTests(unittest.TestCase):
    def test_rattler_makes_bear_unblockable(self):
        me, opp = pair()
        on_board(me, RATTLER)
        on_board(me, BEAR)
        on_board(opp, WALL)
        me.lands = [MOUNTAIN]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 2)

    def test_rattler_without_mana(self):
        me, opp = pair()
        on_board(me, RATTLER)
        on_board(me, BEAR)
        on_board(opp, WALL)
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 0)

    def test_tomik_gives_flying_to_countered_creature(self):
        me, opp = pair()
        on_board(me, TOMIK)
        on_board(me, BEAR).bonus = 1
        on_board(opp, BIG)
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 3)

    def test_tomik_needs_a_creature_with_counter(self):
        me, opp = pair()
        on_board(me, TOMIK)
        on_board(me, OGRE)  # ohne Marke kein Ziel
        on_board(opp, BIG)
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 2)

    def test_tomik_attacks_himself_when_not_better(self):
        me, opp = pair()
        on_board(me, TOMIK)
        on_board(me, BEAR._replace(power=1, toughness=1)).bonus = 1  # 2/2 mit Marke: Flying bringt nicht mehr
        on_board(opp, BIG)
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 2)
        self.assertFalse(any("Tomik" in ev for ev in e["events"]))

    def test_rattler_only_for_small_creatures(self):
        me, opp = pair()
        on_board(me, RATTLER)
        on_board(me, OGRE)
        on_board(opp, BIG)
        me.lands = [MOUNTAIN]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 0)

    def test_pia_pump_counts_artifacts(self):
        me, _opp = pair()
        pia = on_board(me, PIA)
        bear = on_board(me, BEAR)
        on_board(me, BEAR._replace(name="Thopter", is_artifact=True, is_token=True))
        me.perms, me.treasures = [ARTIFACT], 1
        bt.apply_ability(me, pia, PIA.abilities[0], bear)
        self.assertEqual((bear.power, bear.toughness), (5, 2))


class EnterTriggerTests(unittest.TestCase):
    def test_champion_grows(self):
        me, opp = pair()
        arni = on_board(me, CHAMPION)
        bt._resolve(me, opp, TITAN, 3, entry())
        self.assertEqual(arni.power, 8)
        bt.cleanup((me,))
        self.assertEqual(arni.power, 3)

    def test_champion_creatures_in_main_one(self):
        me, opp = pair()
        on_board(me, CHAMPION)
        me.lands, me.hand = [FOREST] * 5, [TITAN]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["main1"], e["damage"]), (["Titan"], 8))

    def test_gideon_pings_entering_creatures(self):
        me, opp = pair()
        on_board(opp, GIDEON)
        bt._resolve(me, opp, BEAR, 3, entry())
        self.assertEqual((me.life, opp.dealt_direct), (19, 1))

    def test_gideon_pings_jace_activations(self):
        me, opp = pair()
        on_board(opp, GIDEON)
        me.jace.loyalty = 3
        bt.jace_turn_start(me, 5, entry())
        self.assertEqual((me.jace.loyalty, me.life), (0, 19))


class WardTests(unittest.TestCase):
    def test_pays_ward_for_the_best_target(self):
        me, opp = pair()
        gecko, bear = on_board(opp, GECKO), on_board(opp, BEAR)
        me.open = [B] * 2
        bt.cast_removal(KILL, me, opp, entry(), 5)
        self.assertEqual((gecko in opp.creatures, bear in opp.creatures, me.open), (False, True, []))

    def test_second_best_target_when_ward_is_too_expensive(self):
        me, opp = pair()
        gecko, bear = on_board(opp, GECKO), on_board(opp, BEAR)
        me.open = [B]
        bt.cast_removal(KILL, me, opp, entry(), 5)
        self.assertEqual((gecko in opp.creatures, bear in opp.creatures, me.open), (True, False, [B]))

    def test_given_target_with_unpayable_ward_is_replaced(self):
        me, opp = pair()
        gecko, bear = on_board(opp, GECKO), on_board(opp, BEAR)
        me.open = [B]
        bt.cast_removal(KILL, me, opp, entry(), 5, target=gecko)
        self.assertEqual((gecko in opp.creatures, bear in opp.creatures), (True, False))

    def test_main_phase_plans_the_ward_cost(self):
        me, opp = pair()
        on_board(opp, GECKO)
        me.lands, me.hand = [SWAMP] * 4, [SLAY]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["main1"], opp.creatures), (["Slay"], []))
        self.assertIn(SLAY, me.graveyard)

    def test_main_phase_skips_removal_without_payable_target(self):
        me, opp = pair()
        on_board(opp, GECKO)
        me.lands, me.hand = [SWAMP] * 3, [SLAY]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["main1"], me.hand), ([], [SLAY]))

    def test_main_phase_takes_second_best_target(self):
        me, opp = pair()
        on_board(opp, GECKO)
        bear = on_board(opp, BEAR)
        me.lands, me.hand = [SWAMP] * 3, [SLAY]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertNotIn(bear, opp.creatures)
        self.assertEqual(len(opp.creatures), 1)

    def test_discard_ward(self):
        me, opp = pair()
        gideon = on_board(opp, GIDEON)
        me.hand = [BEAR]
        bt.cast_removal(KILL, me, opp, entry(), 5)
        self.assertEqual((gideon in opp.creatures, me.hand, me.graveyard), (False, [], [BEAR]))
        gideon = on_board(opp, GIDEON)
        bt.cast_removal(KILL, me, opp, entry(), 5)
        self.assertIn(gideon, opp.creatures)
        bear = on_board(opp, BEAR)  # leere Hand: das zweitbeste Ziel
        bt.cast_removal(KILL, me, opp, entry(), 5)
        self.assertEqual((gideon in opp.creatures, bear in opp.creatures), (True, False))

    def test_ward_on_enter_trigger(self):
        me, opp = pair()
        horti = on_board(opp, HORTI)
        me.open = [R]
        bt._resolve(me, opp, SHOCKER, 3, entry())
        self.assertNotIn(horti, opp.creatures)
        horti = on_board(opp, HORTI)
        me.open = []
        bt._resolve(me, opp, SHOCKER, 3, entry())
        self.assertIn(horti, opp.creatures)


if __name__ == "__main__":
    unittest.main()
