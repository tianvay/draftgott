"""Paket 1-4: Schaden an den Gegner, +1/+1-Marken und Pumps, Marken-Ausloeser, Friedhof und Hapatra."""
import random
import unittest
from unittest import mock

import mtg_sim
from components import simulation as sim
from components.cards import card_info, effect_modes
from components.coverage import analyze_card
from components.removal import removal_info
from tests.fixtures import args_for
from tests.fixtures_walkers import _card

DASH = "—"
CREATURE = f"Creature {DASH} Test"


def modes(text, type_line="Sorcery", name="Test Card"):
    return card_info(_card(name, type_line, "{W}", 1, "W", text, (), "2" if "Creature" in type_line else None,
                           "2" if "Creature" in type_line else None))[0].modes


RAW = {c["name"]: c for c in [
    _card("Plains", f"Basic Land {DASH} Plains", text="({T}: Add {W}.)", produced=["W"]),
    _card("Mountain", f"Basic Land {DASH} Mountain", text="({T}: Add {R}.)", produced=["R"]),
    _card("Test Bear", f"Creature {DASH} Bear", "{W}", 1, "W", power="2", toughness="2"),
    _card("Test Big", CREATURE, "{3}{W}", 4, "W", power="5", toughness="5"),
    _card("Test Bolt", "Sorcery", "{W}", 1, "W", "Test Bolt deals 3 damage to any target."),
    _card("Test Doubt", "Sorcery", "{2}{W}", 3, "W", "Draw two cards. Test Doubt deals 2 damage to each player."),
    _card("Test Growth", "Sorcery", "{W}", 1, "W", "Put a +1/+1 counter on up to one target creature. It gains "
          "vigilance until end of turn."),
    _card("Test Giant Growth", "Instant", "{W}", 1, "W", "Target creature gets +3/+3 until end of turn."),
    _card("Test Rally", "Instant", "{W}", 1, "W", "Creatures you control get +2/+0 until end of turn."),
    _card("Test Charge", "Instant", "{2}{W}", 3, "W", "Choose one —\n• Creatures you control get +2/+0 until end of "
          "turn.\n• Target creature gets +2/+0 and gains first strike until end of turn. Put a +1/+1 counter on it."),
    _card("Test Hunter", CREATURE, "{3}{W}", 4, "W", "When this creature enters, target creature gets +2/+2 and "
          "gains deathtouch until end of turn.", power="3", toughness="3"),
    _card("Test Koth", f"Legendary Creature {DASH} Human Warrior", "{2}{R}", 3, "R",
          "Landfall — Whenever a land you control enters, Test Koth deals 1 damage to each opponent. If that land is a "
          "Mountain, add {R}.", ["Landfall"], "3", "2"),
    _card("Test Homestead", f"Legendary Creature {DASH} Human", "{2}{W}", 3, "W",
          "Landfall — Whenever a land you control enters, you gain 1 life.\nWhenever a Plains you control enters, put "
          "a +1/+1 counter on target creature.", ["Landfall"], "2", "3"),
    _card("Test Edgar", f"Legendary Creature {DASH} Werewolf", "{3}{W}{W}", 5, "W",
          "Flash\nAt the beginning of your end step, if you didn't cast a spell this turn, put two +1/+1 counters on "
          "Test Edgar.", ["Flash"], "4", "4"),
    _card("Test Tethermage", f"Creature {DASH} Elf", "{2}{W}", 3, "W",
          "Whenever you put one or more loyalty counters on a planeswalker, put a +1/+1 counter on this creature.",
          power="3", toughness="2"),
    _card("Test Empower", "Sorcery", "{W}", 1, "W", "Empower Jace 1.", ["Empower Jace"]),
    _card("Test Hapatra", f"Legendary Creature {DASH} Human Cleric", "{2}{W}{W}", 4, "W",
          "When Test Hapatra enters, for each opponent, put X -1/-1 counters on up to one target creature that player "
          "controls, where X is the greatest mana value among cards in your graveyard.", power="3", toughness="3"),
    _card("Test Cycler", CREATURE, "{4}{W}{W}", 6, "W", "Plainscycling {2}", ["Plainscycling"], "5", "5"),
]}
C = {name: card_info(raw)[0] for name, raw in RAW.items()}


class ParsingTests(unittest.TestCase):
    def test_face_damage(self):
        self.assertEqual(modes("Test Card deals 3 damage to any target."), ((("face", 3),),))
        self.assertEqual(modes("Draw two cards. Test Card deals 2 damage to each player."), ((("face", 2),),))
        self.assertEqual(modes("Test Card deals 1 damage to target opponent."), ((("face", 1),),))

    def test_damage_to_creatures_is_not_face_damage(self):
        self.assertEqual(modes("Test Card deals 4 damage to target creature or planeswalker."), ())

    def test_permanent_counters(self):
        self.assertEqual(modes("Put a +1/+1 counter on up to one target creature. It gains vigilance until end of "
                               "turn."), ((("counter", 1, 1),),))
        self.assertEqual(modes("Put a +1/+1 counter on each of one or two target creatures."),
                         ((("counter", 1, 2),),))
        self.assertEqual(modes("Destroy target nonland permanent. Put a +1/+1 counter on each creature target player "
                               "controls."), ((("counter_all", 1),),))

    def test_until_end_of_turn(self):
        self.assertEqual(modes("Target creature gets +3/+3 until end of turn."), ((("pump", 3),),))
        self.assertEqual(modes("Creatures you control get +2/+0 until end of turn."), ((("pump_all", 2),),))

    def test_minus_is_not_a_pump(self):
        self.assertEqual(modes("Target creature gets -3/-3 until end of turn."), ())

    def test_modal(self):
        self.assertEqual(C["Test Charge"].modes, ((("pump_all", 2),), (("pump", 2), ("counter", 1, 1))))

    def test_etb(self):
        self.assertEqual(C["Test Hunter"].modes, ((("pump", 2),),))
        self.assertEqual(modes("When this creature enters, it deals 2 damage to any target.", CREATURE),
                         ((("face", 2),),))

    def test_triggers_are_not_spell_effects(self):
        self.assertEqual(modes("Whenever this creature attacks, it deals 1 damage to each opponent.", CREATURE), ())

    def test_landfall_endstep_loyalty(self):
        self.assertEqual(C["Test Koth"].landfall, (("face", 1), ("mountain_mana", "R")))
        self.assertEqual(C["Test Homestead"].landfall, (("type_counter", "plains", 1),))
        self.assertEqual(C["Test Edgar"].endstep_counters, 2)
        self.assertEqual(C["Test Tethermage"].loyalty_counter, 1)
        self.assertTrue(C["Test Hapatra"].gy_x)
        self.assertFalse(C["Test Bear"].gy_x)

    def test_effect_modes_helper_for_prepared_spell_half(self):
        self.assertEqual(effect_modes({"name": "Vicious Verse", "type_line": "Sorcery",
                                       "oracle_text": "Vicious Verse deals 1 damage to target opponent."}, "Sorcery"),
                         ((("face", 1),),))


class CoverageTests(unittest.TestCase):
    def cats(self, text, type_line="Sorcery"):
        return {c for c, _m, _l in analyze_card(_card("Test Card", type_line, "{W}", 1, "W", text, (), "2", "2"))}

    def test_modelled_effects_are_not_flagged(self):
        self.assertEqual(self.cats("Test Card deals 3 damage to any target."), set())
        self.assertEqual(self.cats("Target creature gets +3/+3 until end of turn.", "Instant"), set())
        self.assertEqual(self.cats("Put a +1/+1 counter on each of one or two target creatures."), set())
        self.assertEqual(self.cats("When this creature enters, target creature gets +2/+2 until end of turn.",
                                   CREATURE), set())

    def test_rest_of_the_line_stays(self):
        self.assertEqual(self.cats("Destroy target nonland permanent. Put a +1/+1 counter on each creature target "
                                   "player controls."), {"Interaktion mit dem Gegner"})

    def test_landfall_endstep_loyalty_lines_are_modelled(self):
        self.assertEqual(analyze_card(RAW["Test Koth"]), [])
        self.assertEqual(analyze_card(RAW["Test Tethermage"]), [])
        self.assertEqual({c for c, _m, _l in analyze_card(RAW["Test Edgar"])}, {"Timing (Flash)"})

    def test_negative_counters_and_minus_are_interaction_not_bonus(self):
        for text, type_line in ((RAW["Test Hapatra"]["oracle_text"], RAW["Test Hapatra"]["type_line"]),
                                ("Target creature gets -3/-3 until end of turn.", "Instant"),
                                ("Put two -1/-1 counters on target creature an opponent controls.", "Sorcery")):
            with self.subTest(text=text):
                found = {(c, m) for c, m, _l in analyze_card(_card("Test Hapatra", type_line, "{W}", 1, "W", text,
                                                                   (), "3", "3"))}
                self.assertEqual(found, {("Interaktion mit dem Gegner", "keine (Gegner ist nicht Teil des Modells)")})

    def test_negative_on_own_creature_stays_a_bonus_case(self):
        self.assertIn("Zählmarken / Stärkebonus", self.cats("Put a -1/-1 counter on target creature you control.",
                                                            "Sorcery"))

    def test_hapatra_counts_as_removal(self):
        info = removal_info(RAW["Test Hapatra"])
        self.assertEqual((info["points"], info["kind"]), (0.5, "−1/−1-Marken"))


class TargetTests(unittest.TestCase):
    """Wohin gehen Marken und Pumps? Zuerst an die staerkste Kreatur, die in dieser Runde angreift."""

    def board(self):
        # (Karte, Runde des Eintritts); Runde 3: Bear und Big greifen an, Hunter kam gerade
        return [(C["Test Bear"], 1), (C["Test Big"], 2), (C["Test Hunter"], 3)], [0, 0, 0]

    def test_pump_goes_to_the_strongest_attacker(self):
        board, bonus = self.board()
        pump = {}
        gain = sim.apply_effects(C["Test Giant Growth"], board, bonus, pump, 3)
        self.assertEqual(pump, {1: 3})
        self.assertEqual(gain["damage"], 3)

    def test_permanent_counter_stays(self):
        board, bonus = self.board()
        sim.apply_effects(C["Test Growth"], board, bonus, {}, 3)
        self.assertEqual(bonus, [0, 1, 0])

    def test_counter_without_attacker_goes_to_strongest_creature(self):
        board, bonus = [(C["Test Hunter"], 3)], [0]
        sim.apply_effects(C["Test Growth"], board, bonus, {}, 3)
        self.assertEqual(bonus, [1])

    def test_pump_without_attacker_is_wasted(self):
        board, bonus = [(C["Test Hunter"], 3)], [0]
        pump = {}
        gain = sim.apply_effects(C["Test Giant Growth"], board, bonus, pump, 3)
        self.assertEqual((pump, gain["damage"]), ({}, 0))

    def test_team_pump(self):
        board, bonus = self.board()
        pump = {}
        sim.apply_effects(C["Test Rally"], board, bonus, pump, 3)
        self.assertEqual(pump, {0: 2, 1: 2})

    def test_modal_picks_most_damage_then_counter(self):
        board, bonus = self.board()
        pump = {}
        sim.apply_effects(C["Test Charge"], board, bonus, pump, 3)  # Team: +4, Einzeln: +2 und +1 Marke = +3
        self.assertEqual(pump, {0: 2, 1: 2})
        board, bonus = [(C["Test Big"], 2)], [0]
        pump = {}
        sim.apply_effects(C["Test Charge"], board, bonus, pump, 3)  # gleich viel Schaden -> Modus mit Marke
        self.assertEqual((pump, bonus), ({0: 2}, [1]))

    def test_face_damage(self):
        gain = sim.apply_effects(C["Test Bolt"], [], [], {}, 1)
        self.assertEqual(gain["face"], 3)


def run(deck, sims=300, seed=29, horizon=8):
    cards = [c for name, n in deck.items() for c in [C[name]] * n]
    random.seed(seed)
    return sim.simulate(cards, sims, False, 3, horizon, True, False, None, 11, 20, 6, True, 3, 6, False, True, 5, True)


class SimulationTests(unittest.TestCase):
    def test_face_damage_speeds_up_lethal(self):
        burn = run({"Plains": 17, "Test Bear": 13, "Test Bolt": 10})
        plain = run({"Plains": 17, "Test Bear": 23})
        self.assertGreater(burn["effects"]["face"], 3)
        self.assertLess(sum(burn["dmg"]) / len(burn["dmg"]), sum(plain["dmg"]) / len(plain["dmg"]) + 0.5)

    def test_counters_increase_power(self):
        res = run({"Plains": 17, "Test Bear": 13, "Test Growth": 10})
        self.assertGreater(res["effects"]["counters"], 1)
        plain = run({"Plains": 17, "Test Bear": 23})
        self.assertGreater(res["power"] / max(res["creatures"], 1e-9), plain["power"] / max(plain["creatures"], 1e-9))

    def test_koth_landfall(self):
        res = run({"Mountain": 17, "Test Koth": 6, "Test Bear": 17})
        self.assertGreater(res["effects"]["face"], 0.5)

    def test_edgar_grows_on_quiet_turns(self):
        res = run({"Plains": 17, "Test Edgar": 8, "Test Bear": 15}, horizon=12)
        self.assertGreater(res["effects"]["counters"], 0.5)

    def test_tethermage_grows_with_empower(self):
        res = run({"Plains": 17, "Test Tethermage": 6, "Test Empower": 10, "Test Bear": 7})
        self.assertGreater(res["effects"]["counters"], 0.5)

    def test_graveyard_and_hapatra(self):
        res = run({"Plains": 16, "Test Cycler": 6, "Test Bolt": 8, "Test Hapatra": 4, "Test Bear": 6})
        gy = res["graveyard"]
        self.assertGreater(gy["size"][5], 1)
        self.assertGreaterEqual(gy["max_mv"][8], gy["max_mv"][3])
        self.assertGreater(gy["hapatra_n"], 0)
        self.assertGreater(gy["hapatra_x_avg"], 1)
        self.assertGreater(gy["x_ge5"], 0)  # gelandcycelte 6-Drops zaehlen mit ihren Manakosten

    def test_no_effects_without_such_cards(self):
        res = run({"Plains": 17, "Test Bear": 23})
        self.assertEqual((res["effects"]["face"], res["effects"]["counters"]), (0.0, 0.0))


class GraveyardTests(unittest.TestCase):
    def test_cycled_card_goes_to_the_graveyard(self):
        hand, library, gy = [C["Test Cycler"]], [C["Plains"], C["Test Bear"]], []
        sim.do_cycle(hand, library, C["Test Cycler"], C["Plains"], graveyard=gy)
        self.assertEqual(gy, [C["Test Cycler"]])

    def test_surveilled_land_goes_to_the_graveyard(self):
        library, gy = [C["Plains"], C["Test Bear"]], []
        sim.apply_surveils([1], library, [C["Test Big"]], [C["Plains"]] * 4, graveyard=gy)
        self.assertEqual(gy, [C["Plains"]])


def build(deck, data=None):
    entries = [{"path": "", "name": "A", "deck": dict(deck), "parts": [("A", dict(deck))]}]
    with mock.patch.object(mtg_sim, "fetch_cards_cached", lambda n, refresh=False: data or RAW):
        return mtg_sim.simulate_entries(entries, args_for(["deck.txt", "--sims", "100"]), progress=lambda m: None)


class DamageNoteTests(unittest.TestCase):
    def test_note_with_effects(self):
        html = build({"Plains": 17, "Test Bear": 13, "Test Bolt": 5, "Test Growth": 5})
        report = html[:html.index('id="view-help"')]
        section = report[report.index('id="schaden"'):report.index("</section>", report.index('id="schaden"'))]
        self.assertIn("Schaden an den Gegner", section)
        self.assertIn("+1/+1-Marken", section)

    def test_no_note_without_effects(self):
        html = build({"Plains": 17, "Test Bear": 23})
        report = html[:html.index('id="view-help"')]
        section = report[report.index('id="schaden"'):report.index("</section>", report.index('id="schaden"'))]
        self.assertNotIn("+1/+1-Marken", section)


class ReportTests(unittest.TestCase):
    def test_graveyard_section_with_hapatra(self):
        html = build({"Plains": 16, "Test Cycler": 6, "Test Bolt": 8, "Test Hapatra": 4, "Test Bear": 6})
        report = html[:html.index('id="view-help"')]
        self.assertIn('id="friedhof"', report)
        section = report[report.index('id="friedhof"'):report.index("</section>", report.index('id="friedhof"'))]
        self.assertIn("Ø Karten im Friedhof", section)
        self.assertIn("Test Hapatra", section)
        self.assertIn('id="hiw-friedhof"', html)


if __name__ == "__main__":
    unittest.main()
