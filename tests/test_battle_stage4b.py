"""Kampfmodell Stufe 4b: Ausloeser und Effekte der Gegnerkarten (Paket A) und Faehigkeiten mit Sonderkosten (Paket B)."""
import random
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
LEG = f"Legendary Creature {DASH} Test"
PLAINS = W["Plains"]
G, U, R, B, WH = ("G",), ("U",), ("R",), ("B",), ("W",)


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=()):
    return card_info(_card(name, type_line, cost, cmc, "G", text, list(keywords), power, toughness))[0]


ENFORCER = make("Repurposed Enforcer", CRE, "{1}{W}", 2, "Whenever this creature attacks, empower Jace X, where X is "
                "the number of creatures you control.", "3", "2", ["Empower Jace"])
PYRO = make("Frostbite Pyromental", CRE, "{U}{R}{R}", 3, "Trample, haste\nWhenever this creature deals combat damage "
            "to a player, draw two cards.\nAt the beginning of the end step, sacrifice this creature.", "4", "4",
            ["Trample", "Haste"])
PROPAGATOR = make("Greenhouse Propagator", CRE, "{2}{G}", 3, "Whenever another creature you control enters, you gain "
                  "1 life.\n{T}: Add {G}.", "2", "3")
MABEL = make("Mabel, Valley Hero", LEG, "{1}{R}{W}", 3, "Whenever Mabel or another creature you control enters, put a "
             "+1/+1 counter on target creature that entered this turn.", "1", "2")
COLOSSUS = make("Craterclaw Colossus", f"Artifact Creature {DASH} Beast", "{4}{R}{R}{R}", 7, "Haste\nWhen this "
                "creature enters, creatures you control gain trample and get +X/+0 until end of turn, where X is the "
                "number of artifacts you control.", "5", "5", ["Haste"])
GEIST = make("Geist of Saint Thalia", LEG, "{1}{U}", 2, "Flying\nNoncreature spells you cast cost {1} less to cast.",
             "1", "2", ["Flying"])
DANITHA = make("Danitha, Spear of Agony", LEG, "{2}{B}", 3, "First strike\nWhenever you cast a spell that targets an "
               "opponent or a creature an opponent controls, put a +1/+1 counter on Danitha.", "2", "2",
               ["First strike"])
SOWER = make("Sureshot Sower", CRE, "{1}{G}", 2, "Reach\n{3}{G}, Discard this card: Destroy target creature with "
             "flying.", "3", "1", ["Reach"])
CRIER = make("Campus Crier", CRE, "{1}{W}", 2, "{1}, Exile this card from your graveyard: Empower Jace 2.", "3", "1")
PHANTASM = make("Surveillance Phantasm", CRE, "{1}{U}", 2, "Defender, flying, vigilance\nAs long as you've scried or "
                "surveilled this turn, this creature can attack as though it didn't have defender.\n{3}{U}: Surveil 1.",
                "2", "3", ["Defender", "Flying", "Vigilance"])
BOLT = make("Bolt", "Instant", "{1}{R}", 2, "Bolt deals 3 damage to target creature.")
SHOCK_FACE = make("Jab", "Sorcery", "{R}", 1, "Jab deals 2 damage to target opponent.")
DIVINATION = make("Divination", "Sorcery", "{2}{U}", 3, "Draw two cards.")
GROWTH = make("Growth", "Instant", "{G}", 1, "Target creature gets +2/+2 until end of turn.")
BEAR = W["Test Bear"]
OGRE = make("Ogre", CRE, "{2}{R}", 3, "", "3", "3")
BIRD = make("Bird", CRE, "{1}{W}", 2, "Flying", "2", "2", ["Flying"])


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertEqual((PYRO.combat_draw, PYRO.end_sacrifice), (2, True))
        self.assertEqual(PROPAGATOR.ally_enter_life, 1)
        self.assertEqual(MABEL.enter_counter, 1)
        self.assertEqual((COLOSSUS.artifact_pump, COLOSSUS.is_artifact), (("trample",), True))
        self.assertEqual(GEIST.spell_discount, 1)
        self.assertEqual(DANITHA.target_cast_counter, 1)
        self.assertTrue(PHANTASM.surveil_attack)
        self.assertEqual([ab[4] for ab in PHANTASM.abilities], [(("surveil", 1),)])

    def test_targets_opponent(self):
        self.assertTrue(BOLT.targets_opp)
        self.assertTrue(SHOCK_FACE.targets_opp)
        self.assertFalse(GROWTH.targets_opp)
        self.assertFalse(DIVINATION.targets_opp)

    def test_hand_and_graveyard_abilities(self):
        alts, spec = SOWER.hand_removal
        self.assertEqual((spec[0], spec[2], spec[4]), ("destroy", (("flying",),), "spell"))
        self.assertEqual(SOWER.abilities, ())
        self.assertEqual(CRIER.gy_ability[1], (("empower", 2),))


class PackageATests(unittest.TestCase):
    def test_enforcer_empowers_by_creature_count(self):
        me, opp = player(), player("Gegner")
        me.creatures = [bt.Creature(ENFORCER, 0), bt.Creature(BEAR, 0), bt.Creature(BEAR, 0)]
        me.jace_perms = [(ENFORCER, 0)]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(me.jace.loyalty + 3 * me.jace.acts + me.jace.surveils, 3)

    def test_pyromental_draws_and_is_sacrificed(self):
        me, opp = player(library=[BEAR] * 5), player("Gegner")
        me.creatures = [bt.Creature(PYRO, 5)]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((opp.life, len(me.hand)), (16, 2))
        self.assertEqual(me.creatures, [])
        self.assertIn(PYRO, me.graveyard)
        self.assertTrue(any("Frostbite Pyromental" in d for d in e["deaths"]))

    def test_propagator_gains_life(self):
        me, opp = player(), player("Gegner")
        me.creatures = [bt.Creature(PROPAGATOR, 0)]
        bt._resolve(me, opp, BEAR, 3, entry())
        bt._resolve(me, opp, OGRE, 3, entry())
        self.assertEqual(me.life, 22)

    def test_mabel_counter_on_creature_that_entered(self):
        me, opp = player(), player("Gegner")
        old = bt.Creature(BEAR, 1)
        me.creatures = [old]
        bt._resolve(me, opp, MABEL, 3, entry())     # Mabel selbst kam in diesem Zug
        self.assertEqual(me.creatures[1].bonus, 1)
        bt._resolve(me, opp, OGRE, 3, entry())      # staerkste Kreatur dieses Zugs: der Oger (3/3) vor Mabel (2/3)
        self.assertEqual((old.bonus, me.creatures[1].bonus, me.creatures[2].bonus), (0, 1, 1))

    def test_colossus_pumps_the_team(self):
        me, opp = player(), player("Gegner")
        bear = bt.Creature(BEAR, 0)
        me.creatures = [bear]
        bt._resolve(me, opp, COLOSSUS, 3, entry())
        self.assertEqual((bear.power, bear.toughness, bear.has("trample")), (3, 2, True))
        self.assertEqual(me.creatures[1].power, 6)

    def test_geist_makes_noncreature_spells_cheaper(self):
        me = player()
        me.creatures, me.hand, me.open = [bt.Creature(GEIST, 0)], [BOLT], [R]
        self.assertTrue(bt.affordable(me, BOLT))
        me.hand, me.open = [OGRE], [R, R]
        self.assertFalse(bt.affordable(me, OGRE))

    def test_geist_in_the_main_phase(self):
        me, opp = player(), player("Gegner")
        me.lands = [W["Island"]] * 2
        me.creatures, me.hand = [bt.Creature(GEIST, 0)], [DIVINATION]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["main1"], ["Divination"])
        self.assertIn(DIVINATION, me.graveyard)  # die Originalkarte, nicht die verbilligte

    def test_danitha_grows_on_targeted_spells(self):
        me, opp = player(), player("Gegner")
        danitha = bt.Creature(DANITHA, 0)
        me.creatures, opp.creatures = [danitha], [bt.Creature(BEAR, 0)]
        bt._resolve(me, opp, SHOCK_FACE, 3, entry())
        bt._resolve(me, opp, DIVINATION, 3, entry())
        self.assertEqual(danitha.bonus, 1)
        me.hand, me.open = [BOLT], [R, R]
        bt.end_step_instants(me, opp, entry(), 4)  # Removal-Instant am Ende des gegnerischen Zugs
        self.assertEqual(danitha.bonus, 2)


class PackageBTests(unittest.TestCase):
    def test_sower_kills_an_attacking_flier_from_hand(self):
        dfn, act = player("Gegner"), player()
        bird = bt.Creature(BIRD, 0)
        act.creatures = [bird]
        dfn.hand, dfn.open = [SOWER], [G] * 4
        left = bt.respond_to_attack(dfn, act, [bird], entry(), 5)
        self.assertEqual((left, act.creatures), ([], []))
        self.assertIn(SOWER, dfn.graveyard)

    def test_sower_at_end_step(self):
        dfn, act = player("Gegner"), player()
        act.creatures = [bt.Creature(BIRD, 0)]
        dfn.hand, dfn.open = [SOWER], [G] * 4
        bt.end_step_instants(dfn, act, entry(), 5)
        self.assertEqual(act.creatures, [])

    def test_sower_needs_a_flier(self):
        dfn, act = player("Gegner"), player()
        act.creatures = [bt.Creature(OGRE, 0)]
        dfn.hand, dfn.open = [SOWER], [G] * 4
        bt.end_step_instants(dfn, act, entry(), 5)
        self.assertEqual(dfn.hand, [SOWER])

    def test_crier_from_graveyard(self):
        dfn, act = player("Gegner"), player()
        dfn.graveyard.append(CRIER)
        dfn.open = [WH]
        bt.end_step_instants(dfn, act, entry(), 5)
        self.assertEqual((dfn.jace.loyalty, dfn.graveyard), (2, []))

    def test_phantasm_surveils_to_attack(self):
        me, opp = player(library=[BEAR] * 5), player("Gegner")
        me.lands = [W["Island"]] * 4
        me.creatures = [bt.Creature(PHANTASM, 0)]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 2)
        self.assertFalse(bt.can_attack(me.creatures[0], 7))  # "this turn" endet mit dem Zug

    def test_phantasm_attacks_after_jace_surveil(self):
        me, opp = player(), player("Gegner")
        phantasm = bt.Creature(PHANTASM, 0)
        me.creatures = [phantasm]
        bt.surveil_cards(me, [1], entry(), "Test")
        self.assertTrue(bt.can_attack(phantasm, 5))

    def test_jace_surveil_counts(self):
        me = player()
        phantasm = bt.Creature(PHANTASM, 0)
        me.creatures = [phantasm]
        me.jace.add(1)
        bt._jace_activate(me, 5, entry(), True)
        self.assertTrue(bt.can_attack(phantasm, 5))

    def test_phantasm_surveil_at_end_step(self):
        dfn, act = player("Gegner", library=[PLAINS, BEAR]), player()
        dfn.lands = [PLAINS] * 5
        dfn.creatures, dfn.open = [bt.Creature(PHANTASM, 0)], [U] * 4
        bt.end_step_instants(dfn, act, entry(), 5)
        self.assertEqual(dfn.library, [BEAR])


class GameTests(unittest.TestCase):
    def test_games(self):
        lands = [W["Plains"]] * 6 + [W["Island"]] * 6
        deck = lands + [card_info(_card("Mountain", f"Basic Land {DASH} Mountain", text="({T}: Add {R}.)", produced=["R"]))[0]] * 5 + \
            [ENFORCER, PYRO, PROPAGATOR, MABEL, GEIST, DANITHA, SOWER, CRIER, PHANTASM, BOLT, SHOCK_FACE] * 2 + [BEAR]
        random.seed(11)
        r = bt.battle(deck, deck, 60, on_draw=False)
        self.assertEqual(r["wins"] + r["losses"] + r["draws"], 60)


if __name__ == "__main__":
    unittest.main()
