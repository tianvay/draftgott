"""Mehrfach-Farbsymbole: je Farbe und Symbolzahl die guenstigste Karte, Quellen bis zu ihrer Runde (inkl.
Manaquellen); 'Alle Farben bis Runde 3' zaehlt Manaquellen mit."""
import random
import unittest
from unittest import mock

from components.cards import card_info
from components.mana import pip_checks
from components.report_cards import render_color_availability
from components.simulation import simulate
from tests.fixtures_walkers import _card

DASH = "—"
RAW = {c["name"]: c for c in [
    _card("Plains", f"Basic Land {DASH} Plains", text="({T}: Add {W}.)", produced=["W"]),
    _card("Swamp", f"Basic Land {DASH} Swamp", text="({T}: Add {B}.)", produced=["B"]),
    _card("Forest", f"Basic Land {DASH} Forest", text="({T}: Add {G}.)", produced=["G"]),
    _card("Twisted Fates", "Sorcery", "{2}{W}{W}{B}", 5, "WB", "Destroy target nonland permanent."),
    _card("Violent Echoes", "Instant", "{2}{R}{R}", 4, "R", ""),
    _card("Hexhaven Invigorator", f"Creature {DASH} Test", "{G}{G}{G}{G}", 4, "G", power="4", toughness="4"),
    _card("Green Twin", f"Creature {DASH} Test", "{1}{G}{G}", 3, "G", power="3", toughness="3"),
    _card("Green Late Twin", f"Creature {DASH} Test", "{3}{G}{G}", 5, "G", power="5", toughness="5"),
    _card("Hybrid Pair", f"Creature {DASH} Test", "{G/W}{G/W}", 2, "GW", power="2", toughness="2"),
    _card("Green Bear", f"Creature {DASH} Bear", "{G}", 1, "G", power="2", toughness="2"),
    _card("White Bear", f"Creature {DASH} Bear", "{W}", 1, "W", power="2", toughness="2"),
    _card("Test Elves", f"Creature {DASH} Elf", "{G}", 1, "G", "{T}: Add {G}.", power="1", toughness="1"),
    _card("Green Stone", "Artifact", "{1}", 1, "", "{T}: Add {G}."),
    _card("Grey Stone", "Artifact", "{1}", 1, "", ""),
]}
C = {n: card_info(r)[0] for n, r in RAW.items()}


class DefinitionTests(unittest.TestCase):
    def checks(self, names):
        return [(c["color"], c["k"], c["turn"], c["cards"]) for c in pip_checks([C[n] for n in names])]

    def test_examples(self):
        self.assertEqual(self.checks(["Twisted Fates"]), [("W", 2, 5, ["Twisted Fates"])])
        self.assertEqual(self.checks(["Violent Echoes"]), [("R", 2, 4, ["Violent Echoes"])])
        self.assertEqual(self.checks(["Hexhaven Invigorator"]), [("G", 4, 4, ["Hexhaven Invigorator"])])

    def test_one_check_per_symbol_count_with_the_cheapest_card(self):
        got = self.checks(["Hexhaven Invigorator", "Green Twin", "Green Late Twin"])
        self.assertEqual(got, [("G", 2, 3, ["Green Late Twin", "Green Twin"]),
                               ("G", 4, 4, ["Hexhaven Invigorator"])])

    def test_hybrid_and_single_symbols_do_not_count(self):
        self.assertEqual(self.checks(["Hybrid Pair", "Green Bear", "Plains"]), [])


def run(names_counts, checks, colors, sims=200, seed=31, horizon=8):
    cards = [C[n] for n, k in names_counts.items() for _ in range(k)]
    random.seed(seed)
    return simulate(cards, sims, False, 3, horizon, True, True, None, 11, 20, 6, True, 3, 6, False, True, 5, True,
                    color_check={"colors": colors, "checks": checks})["color_avail"]


class MeasurementTests(unittest.TestCase):
    def test_four_green_sources_in_turn_four(self):
        checks = pip_checks([C["Hexhaven Invigorator"]])
        ca = run({"Forest": 17, "Hexhaven Invigorator": 4, "Green Bear": 19}, checks, ["G"])
        r = ca["checks"][0]
        self.assertEqual((r["color"], r["k"], r["turn"]), ("G", 4, 4))
        self.assertTrue(r["measured"])
        self.assertGreater(r["ok"], 0)
        self.assertLess(r["ok"], ca["games"])  # nicht jedes Spiel hat 4 Laender in Runde 4

    def test_turn_beyond_the_horizon_is_not_measured(self):
        checks = pip_checks([C["Twisted Fates"]])
        ca = run({"Plains": 10, "Swamp": 7, "Twisted Fates": 4, "White Bear": 19}, checks, ["W", "B"], horizon=4)
        self.assertFalse(ca["checks"][0]["measured"])

    def test_mana_sources_count(self):
        checks = pip_checks([C["Green Twin"]])
        with_elves = run({"Forest": 2, "Plains": 15, "Green Stone": 12, "Green Twin": 4, "White Bear": 7}, checks,
                         ["G", "W"], sims=400)
        no_elves = run({"Forest": 2, "Plains": 15, "Grey Stone": 12, "Green Twin": 4, "White Bear": 7}, checks,
                       ["G", "W"], sims=400)
        self.assertGreater(with_elves["checks"][0]["ok"], no_elves["checks"][0]["ok"])
        self.assertGreater(with_elves["t3"]["G"], no_elves["t3"]["G"])


class RenderTests(unittest.TestCase):
    def test_rows(self):
        checks = [{"color": "W", "k": 2, "turn": 5, "cards": ["Twisted Fates"], "ok": 81, "measured": True},
                  {"color": "G", "k": 4, "turn": 4, "cards": ["Hexhaven Invigorator"], "ok": 40, "measured": True}]
        res = {"color_avail": {"colors": ["W", "B", "G"], "t3": {"W": 99, "B": 95, "G": 97}, "t3_all": 92,
                               "games": 100, "checks": checks}}
        html = render_color_availability({"results": {"On the Play": res, "On the Draw": res}})
        self.assertIn("≥ 2 Quellen Weiß bis Runde 5", html)
        self.assertIn("wegen WW in: Twisted Fates", html)
        self.assertIn("≥ 4 Quellen Grün bis Runde 4", html)
        self.assertIn("wegen GGGG in: Hexhaven Invigorator", html)
        self.assertIn('class="bad">40%', html)


if __name__ == "__main__":
    unittest.main()
