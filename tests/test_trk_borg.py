"""Star Trek (TRK), Paket E (Nutzer 2026-11-01): Borg und Artefaktkreaturen - Schluesselwoerter fuer Artefaktkreaturen
(auch als Station-Stufe), Collective Drone, verliehene Kampfschaden-Ausloeser (Hive Mind Coprocessor, Antagonist
Incorporator), Organic Avulsion Unit, Collation Trimatrix, Assimilate (Death Is Irrelevant, Borg Cube) und Affinity for
artifact creatures. Nur Kampfmodell. Kartentexte aus TRK."""
import unittest

from components import battle as bt
from components.cards import card_info, token_card
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]
ASSIMILATE = (" (Put it onto the battlefield under your control with a +1/+1 counter. It's a Borg artifact creature and "
              "loses all other creature types.)")


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="B"):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)


RAW = {
    "adjunct": raw("Primary Unimatrix Adjunct", f"Artifact Creature {DASH} Borg", "{3}{W}", 4,
                   "Artifact creatures you control have double strike.", "2", "3", colors="W"),
    "irrelevant": raw("Death Is Irrelevant", "Enchantment", "{6}{B}{B}", 8, "Artifact creatures you control have "
                      "indestructible.\nAt the beginning of your end step, assimilate target creature card from a "
                      "graveyard." + ASSIMILATE, keywords=["Assimilate"]),
    "collective": raw("Collective Drone", f"Artifact Creature {DASH} Borg", "{1}{B}", 2, "Collective Drone's power is "
                      "equal to the number of artifact creatures you control.", "*", "2"),
    "hive": raw("Hive Mind Coprocessor", f"Artifact Creature {DASH} Borg", "{4}{B}", 5, "Artifact creatures you "
                "control have \"Whenever this creature deals combat damage to a player, you may pay 1 life. If you do, "
                "draw a card.\"", "4", "4"),
    "antagonist": raw("Antagonist Incorporator", f"Artifact Creature {DASH} Borg", "{1}{W}", 2, "Artifact creatures "
                      "you control have \"Whenever this creature deals combat damage to a player, you may pay {1}. If "
                      "you do, create a 1/1 colorless Borg artifact creature token.\"", "2", "3", colors="W"),
    "avulsion": raw("Organic Avulsion Unit", f"Artifact Creature {DASH} Borg", "{2}{B}", 3, "{2}: Artifact creatures "
                    "you control gain menace until end of turn. (A creature with menace can't be blocked except by two "
                    "or more creatures.)", "2", "3"),
    "trimatrix": raw("Collation Trimatrix", f"Artifact Creature {DASH} Borg", "{B}", 1, "Tap three untapped artifact "
                     "creatures you control: You draw a card and lose 1 life.", "1", "1"),
    "cube": raw("Borg Cube", f"Artifact {DASH} Spacecraft", "{5}{W}{B}", 7, "Affinity for artifact creatures\nWhenever "
                "this Spacecraft enters or attacks, assimilate a creature card exiled with it. If you can't, exile up "
                "to one target creature. (To assimilate a card, put it onto the battlefield under your control with a "
                "+1/+1 counter. It's a Borg artifact creature and loses all other creature types.)\nStation\n12+ | "
                "Artifact creatures you control have flying.", "6", "6", ["Assimilate", "Affinity", "Station"], "WB"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}
OGRE = card_info(_card("Ogre", f"Creature {DASH} Ogre", "{2}{R}", 3, "R", "", [], "3", "3"))[0]
GIANT = card_info(_card("Giant", f"Creature {DASH} Giant", "{4}{R}", 5, "R", "", [], "5", "5"))[0]
SEER = card_info(_card("Seer", f"Creature {DASH} Human", "{2}{U}", 3, "U", "When this creature enters, draw a card.",
                       [], "1", "1"))[0]
GOLEM = card_info(_card("Golem", f"Artifact Creature {DASH} Golem", "{3}", 3, "", "", [], "3", "3"))[0]
DRONE = token_card("Borg", True, 1, 1, True, types=("borg",))


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def pair(library=None):
    me, opp = player(library=library), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


def put(p, card, entered=0):
    c = bt.Creature(card, entered)
    c.gy, c.ctl = p.graveyard, p
    p.creatures.append(c)
    return c


class ParseTests(unittest.TestCase):
    def test_artifact_keywords(self):
        self.assertEqual(C["adjunct"].cond_static, ((("always",), "artifact", 0, 0, ("double strike",)),))
        self.assertEqual(C["irrelevant"].cond_static, ((("always",), "artifact", 0, 0, ("indestructible",)),))
        self.assertTrue(C["irrelevant"].end_assimilate)

    def test_other_fields(self):
        self.assertTrue(C["collective"].artifact_count_power)
        self.assertTrue(C["hive"].artifact_hit_draw)
        self.assertEqual(C["antagonist"].artifact_hit_token[0], ((1, ()),))
        self.assertEqual(C["antagonist"].artifact_hit_token[1].name, "Borg")
        self.assertEqual(C["avulsion"].artifact_kw_ability, (((2, ()),), ("menace",)))
        self.assertEqual(C["trimatrix"].tap3_draw, 3)
        self.assertTrue(C["cube"].cube_assimilate)
        self.assertEqual(C["cube"].self_discount, ("artifact_creatures",))
        self.assertEqual(C["cube"].station[3], ((12, (), (0, 0, "artifact", ("flying",))),))

    def test_coverage(self):
        for key, r in RAW.items():
            self.assertEqual([l for _c, _m, l in analyze_card(r)], [], key)


class StaticTests(unittest.TestCase):
    def test_adjunct_double_strike(self):
        me, _opp = pair()
        put(me, C["adjunct"])
        golem, ogre = put(me, GOLEM), put(me, OGRE)
        self.assertEqual((golem.has("double strike"), ogre.has("double strike")), (True, False))

    def test_irrelevant_indestructible(self):
        me, _opp = pair()
        me.perms.append(C["irrelevant"])
        golem = put(me, GOLEM)
        golem.damage = 5
        self.assertFalse(bt.is_dying(golem))

    def test_collective_drone(self):
        me, _opp = pair()
        drone = put(me, C["collective"])
        self.assertEqual(drone.power, 1)
        put(me, GOLEM), put(me, OGRE)
        self.assertEqual(drone.power, 2)


class CombatHitTests(unittest.TestCase):
    def test_hive_mind_draws(self):
        me, opp = pair(library=[PLAINS] * 5)
        put(me, C["hive"])
        golem, ogre = put(me, GOLEM), put(me, OGRE)
        bt.artifact_hit_triggers(me, [golem, ogre], 5, entry())
        self.assertEqual((len(me.hand), me.life), (1, 19))  # nur die Artefaktkreatur

    def test_hive_mind_not_at_low_life(self):
        me, opp = pair(library=[PLAINS] * 5)
        put(me, C["hive"])
        golem = put(me, GOLEM)
        me.life = 5
        bt.artifact_hit_triggers(me, [golem], 5, entry())
        self.assertEqual((len(me.hand), me.life), (0, 5))

    def test_antagonist_token_with_free_mana(self):
        me, opp = pair()
        put(me, C["antagonist"])
        golem = put(me, GOLEM)
        me.open = [("W",)]
        bt.artifact_hit_triggers(me, [golem], 5, entry())
        self.assertEqual([c.card.name for c in me.creatures].count("Borg"), 1)
        bt.artifact_hit_triggers(me, [golem], 5, entry())  # kein Mana mehr
        self.assertEqual([c.card.name for c in me.creatures].count("Borg"), 1)


class AbilityTests(unittest.TestCase):
    def test_avulsion_menace_before_attack(self):
        me, opp = pair()
        put(me, C["avulsion"])
        golem, ogre = put(me, GOLEM), put(me, OGRE)
        put(opp, OGRE)
        me.open = [("B",), ("B",)]
        bt.artifact_menace(me, opp, 5, entry())
        self.assertEqual((golem.has("menace"), ogre.has("menace"), me.open), (True, False, []))

    def test_avulsion_not_without_blockers(self):
        me, opp = pair()
        put(me, C["avulsion"])
        put(me, GOLEM)
        me.open = [("B",), ("B",)]
        bt.artifact_menace(me, opp, 5, entry())
        self.assertEqual(len(me.open), 2)

    def test_trimatrix_at_end_of_opponents_turn(self):
        me, opp = pair(library=[PLAINS] * 5)
        put(me, C["trimatrix"]), put(me, GOLEM), put(me, GOLEM), put(me, OGRE)
        bt.tap3_draws(me, entry())
        self.assertEqual((len(me.hand), me.life), (1, 19))
        self.assertEqual(sum(c.tapped for c in me.creatures), 3)
        self.assertFalse(me.creatures[3].tapped)  # keine Artefaktkreatur

    def test_trimatrix_needs_three(self):
        me, _opp = pair(library=[PLAINS] * 5)
        put(me, C["trimatrix"]), put(me, GOLEM)
        bt.tap3_draws(me, entry())
        self.assertEqual(len(me.hand), 0)


class AssimilateTests(unittest.TestCase):
    def test_assimilate_from_graveyard(self):
        me, opp = pair(library=[PLAINS] * 5)
        opp.graveyard = [OGRE, SEER]
        me.graveyard = [GIANT]
        me.perms.append(C["irrelevant"])
        bt.end_assimilate(me, opp, 5, entry())
        borg = next(c for c in me.creatures if c.card.name == "Giant")
        self.assertEqual((borg.bonus, borg.card.is_artifact, borg.card.creature_types), (1, True, ("borg",)))
        self.assertEqual(me.graveyard, [])

    def test_assimilated_enters_and_returns_to_owner(self):
        me, opp = pair(library=[PLAINS] * 5)
        opp.graveyard = [SEER]
        me.perms.append(C["irrelevant"])
        bt.end_assimilate(me, opp, 5, entry())
        self.assertEqual(len(me.hand), 1)  # Betreten-Ausloeser
        borg = me.creatures[0]
        self.assertTrue(borg.has("indestructible"))  # jetzt eine Artefaktkreatur
        borg.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual((opp.graveyard, me.graveyard), ([SEER], []))

    def test_cube_exiles_then_assimilates(self):
        me, opp = pair()
        giant = put(opp, GIANT)
        me.perms.append(C["cube"])
        bt.permanent_enters(me, opp, C["cube"], 5, entry())
        self.assertNotIn(giant, opp.creatures)
        self.assertEqual(me.cube_exiled, [(GIANT, opp)])
        cube = put(me, C["cube"]._replace(is_creature=True, power=6, toughness=6))
        bt.cube_attack(me, opp, [cube], 6, entry())
        self.assertEqual([c.card.name for c in me.creatures], ["Borg Cube", "Giant"])
        self.assertEqual(me.cube_exiled, [])

    def test_cube_attack_exiles_if_nothing_to_assimilate(self):
        me, opp = pair()
        ogre = put(opp, OGRE)
        cube = put(me, C["cube"]._replace(is_creature=True, power=6, toughness=6))
        bt.cube_attack(me, opp, [cube], 6, entry())
        self.assertNotIn(ogre, opp.creatures)

    def test_cube_affinity(self):
        me, _opp = pair()
        put(me, GOLEM), put(me, GOLEM), put(me, OGRE)
        self.assertEqual(bt._alts(me, C["cube"]), ((3, (("B", 1), ("W", 1))),))

    def test_cube_station_flying(self):
        me, opp = pair()
        me.perms.append(C["cube"])
        bt.permanent_enters(me, opp, C["cube"], 5, entry())
        golem = put(me, GOLEM)
        me.stations[0]["charge"] = 12
        bt.update_stations(me, 5, entry())
        self.assertTrue(golem.has("flying"))


if __name__ == "__main__":
    unittest.main()
