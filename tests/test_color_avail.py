import random
import unittest
from unittest import mock

import mtg_sim
from components.cards import card_info
from components.mana import double_pip_colors
from components.report_cards import render_color_availability
from components.simulation import simulate
from tests.fixtures import args_for

DASH = "—"


def raw(name, type_line, cost="", colors=(), text="", produced=None, power=None, toughness=None, cmc=0):
    d = {"name": name, "type_line": type_line, "mana_cost": cost, "cmc": float(cmc), "colors": list(colors),
         "oracle_text": text, "keywords": [], "layout": "normal", "power": power, "toughness": toughness}
    if produced:
        d["produced_mana"] = list(produced)
    return d


DATA = {c["name"]: c for c in [
    raw("Plains", f"Basic Land {DASH} Plains", text="({T}: Add {W}.)", produced=["W"]),
    raw("Mountain", f"Basic Land {DASH} Mountain", text="({T}: Add {R}.)", produced=["R"]),
    raw("Swamp", f"Basic Land {DASH} Swamp", text="({T}: Add {B}.)", produced=["B"]),
    raw("Orzhov Dual", "Land", text="{T}: Add {W} or {B}.", produced=["W", "B"]),
    raw("White Bear", f"Creature {DASH} Bear", "{1}{W}", "W", power="2", toughness="2", cmc=2),
    raw("Black Bear", f"Creature {DASH} Bear", "{1}{B}", "B", power="2", toughness="2", cmc=2),
    raw("Red Ogre", f"Creature {DASH} Ogre", "{2}{R}{R}", "R", power="4", toughness="4", cmc=4),
    raw("Red Shock", "Instant", "{R}", "R", cmc=1),
    raw("Hybrid Elf", f"Creature {DASH} Elf", "{R/G}{R/G}", "RG", power="2", toughness="2", cmc=2),
    raw("Black Knight", f"Creature {DASH} Knight", "{2}{B}{B}", "B", power="3", toughness="3", cmc=4),
]}
CARDS = {n: card_info(d)[0] for n, d in DATA.items()}


def deck(counts):
    return [CARDS[n] for n, q in counts.items() for _ in range(q)]


def run(counts, color_check, sims=300, seed=5, on_draw=False):
    random.seed(seed)
    return simulate(deck(counts), sims, on_draw, 3, 8, True, True, None, 11, 20, 6, True, 3, 6, False, True, 5, True,
                    color_check=color_check)


class DoublePipTests(unittest.TestCase):
    def test_double_colored_costs_are_found_with_card_names(self):
        cards = [CARDS["Red Ogre"], CARDS["Black Knight"], CARDS["Red Shock"], CARDS["Plains"]]
        self.assertEqual(double_pip_colors(cards), {"R": ["Red Ogre"], "B": ["Black Knight"]})

    def test_single_pip_and_hybrid_do_not_count(self):
        self.assertEqual(double_pip_colors([CARDS["White Bear"], CARDS["Hybrid Elf"], CARDS["Red Shock"]]), {})

    def test_duplicates_are_listed_once(self):
        self.assertEqual(double_pip_colors([CARDS["Red Ogre"]] * 3), {"R": ["Red Ogre"]})


class SimulationMeasurementTests(unittest.TestCase):
    def test_without_color_check_nothing_is_added(self):
        r = run({"Plains": 17, "White Bear": 23}, None)
        self.assertNotIn("color_avail", r)

    def test_measurement_does_not_change_the_other_results(self):
        counts = {"Plains": 9, "Swamp": 8, "White Bear": 12, "Black Bear": 11}
        a = run(counts, None)
        b = run(counts, {"colors": ["W", "B"], "double": []})
        for key in ("cast", "dmg", "any_screw", "flood", "empty_hand"):
            self.assertEqual(a[key], b[key], key)

    def test_color_without_sources_is_never_available(self):
        r = run({"Plains": 17, "White Bear": 20, "Black Bear": 3}, {"colors": ["W", "B"], "double": []})
        ca = r["color_avail"]
        self.assertEqual(ca["t3"]["B"], 0)
        self.assertEqual(ca["t3_all"], 0)
        self.assertGreater(ca["t3"]["W"], 0)

    def test_all_colors_never_exceeds_a_single_color(self):
        r = run({"Plains": 9, "Swamp": 8, "White Bear": 12, "Black Bear": 11}, {"colors": ["W", "B"], "double": []})
        ca = r["color_avail"]
        self.assertLessEqual(ca["t3_all"], min(ca["t3"].values()))
        self.assertLessEqual(max(ca["t3"].values()), ca["games"])

    def test_dual_lands_count_for_both_colors(self):
        r = run({"Orzhov Dual": 17, "White Bear": 12, "Black Bear": 11}, {"colors": ["W", "B"], "double": []})
        ca = r["color_avail"]
        self.assertEqual(ca["t3"]["W"], ca["t3"]["B"])
        self.assertEqual(ca["t3_all"], ca["t3"]["W"])

    def test_two_sources_impossible_with_a_single_red_land(self):
        r = run({"Mountain": 1, "Plains": 16, "White Bear": 20, "Red Ogre": 3}, {"colors": ["W", "R"], "double": ["R"]})
        self.assertEqual(r["color_avail"]["t4_double"]["R"], 0)

    def test_two_sources_are_reached_in_a_mono_red_deck(self):
        r = run({"Mountain": 17, "Red Shock": 20, "Red Ogre": 3}, {"colors": ["R"], "double": ["R"]})
        ca = r["color_avail"]
        self.assertGreater(ca["t4_double"]["R"], 0)
        self.assertTrue(ca["t4_measured"])

    def test_three_colors_from_basics_are_measured_after_the_third_land_drop(self):
        # drei Farben aus drei verschiedenen Standardlaendern gehen fruehestens in Runde 3; frueher gemessen waere es 0
        counts = {"Plains": 6, "Swamp": 6, "Mountain": 5, "White Bear": 8, "Black Bear": 8, "Red Shock": 7}
        r = run(counts, {"colors": ["W", "B", "R"], "double": []}, sims=400)
        self.assertGreater(r["color_avail"]["t3_all"], 0)

    def test_played_games_are_the_denominator(self):
        r = run({"Plains": 17, "White Bear": 23}, {"colors": ["W"], "double": []}, sims=120)
        self.assertEqual(r["color_avail"]["games"], 120)


class FixedOrderGameTests(unittest.TestCase):
    """Spiele ohne Mischen: Starthand = erste 7 Karten, dann wird in Reihenfolge gezogen (On the Play, ab Runde 2)."""

    def play(self, order, color_check):
        cards = [CARDS[n] for n in order]
        with mock.patch("components.mulligan.random.shuffle", lambda x: None):
            return simulate(cards, 1, False, 3, 8, True, True, None, 11, 20, 6, True, 3, 6, False, True, 5, True,
                            color_check=color_check)["color_avail"]

    def test_second_red_source_arrives_in_turn_four(self):
        # Runde 1 Mountain, 2 und 3 Plains, Runde 4 zieht Mountain und legt ihn (fuer Red Ogre)
        hand = ["Mountain", "Plains", "Plains", "Red Ogre", "Red Ogre", "Red Ogre", "Red Ogre"]
        order = hand + ["Plains", "White Bear", "Mountain"] + ["White Bear"] * 10
        ca = self.play(order, {"colors": ["W", "R"], "double": ["R"]})
        self.assertEqual(ca["t4_double"]["R"], 1)
        self.assertEqual((ca["t3"]["R"], ca["t3"]["W"], ca["t3_all"]), (1, 1, 1))

    def test_third_color_arrives_in_turn_three(self):
        hand = ["Plains", "Swamp", "White Bear", "White Bear", "Black Bear", "Black Bear", "Red Shock"]
        order = hand + ["White Bear", "Mountain"] + ["White Bear"] * 10
        ca = self.play(order, {"colors": ["W", "B", "R"], "double": []})
        self.assertEqual((ca["t3"]["W"], ca["t3"]["B"], ca["t3"]["R"], ca["t3_all"]), (1, 1, 1, 1))

    def test_third_color_in_turn_four_is_too_late(self):
        hand = ["Plains", "Swamp", "White Bear", "White Bear", "Black Bear", "Black Bear", "Red Shock"]
        order = hand + ["White Bear", "White Bear", "Mountain"] + ["White Bear"] * 10
        ca = self.play(order, {"colors": ["W", "B", "R"], "double": []})
        self.assertEqual((ca["t3"]["R"], ca["t3_all"]), (0, 0))


class DeckWiringTests(unittest.TestCase):
    def dd(self, counts):
        args = args_for(["deck.txt", "--sims", "100"])
        entry = {"name": "Test", "deck": dict(counts), "parts": [("Test", dict(counts))]}
        dd = mtg_sim.build_deck(entry, DATA, args)
        mtg_sim.simulate_deck(dd, args, 0, max(args.max_runden, args.turns, args.curve_runden), progress=lambda m: None)
        return dd

    def test_deck_colors_and_double_pips_reach_the_simulation(self):
        dd = self.dd({"Mountain": 9, "Plains": 8, "White Bear": 12, "Red Ogre": 11})
        self.assertEqual(dd["double_pips"], {"R": ["Red Ogre"]})
        for mode in ("On the Play", "On the Draw"):
            ca = dd["results"][mode]["color_avail"]
            self.assertEqual(ca["colors"], ["W", "R"])
            self.assertEqual(ca["double"], ["R"])


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        counts = {"Mountain": 9, "Plains": 8, "White Bear": 12, "Red Ogre": 11}
        args = args_for(["deck.txt", "--sims", "200"])
        entries = [{"path": "", "name": "A", "deck": dict(counts), "parts": [("A", dict(counts))]},
                   {"path": "", "name": "B", "deck": {"Plains": 17, "White Bear": 23},
                    "parts": [("B", {"Plains": 17, "White Bear": 23})]}]
        with mock.patch.object(mtg_sim, "fetch_cards_cached", lambda n, refresh=False: DATA):
            cls.html = mtg_sim.simulate_entries(entries, args, progress=lambda m: None)

    def test_section_with_all_colors_single_colors_and_doubles(self):
        self.assertIn("Farbverfügbarkeit", self.html)
        self.assertIn("Alle Farben bis Runde 3", self.html)
        self.assertIn("Weiß", self.html)
        self.assertIn("≥ 2 Quellen Rot bis Runde 4", self.html)
        self.assertIn("Red Ogre", self.html)

    def test_overview_and_comparison_contain_the_all_colors_row(self):
        self.assertGreaterEqual(self.html.count("Alle Farben bis Runde 3"), 3)

    def test_traffic_light_rule_is_explained(self):
        self.assertIn("grün ab 90 %", self.html)


class RenderTests(unittest.TestCase):
    def res(self, t3, all3, dbl, games=100, measured=True):
        return {"color_avail": {"colors": list(t3), "double": list(dbl), "t3": t3, "t3_all": all3, "t4_double": dbl,
                                "games": games, "t4_measured": measured}}

    def ctx(self, play, draw, double_pips=None):
        return {"results": {"On the Play": play, "On the Draw": draw}, "double_pips": double_pips or {}}

    def test_traffic_light_levels(self):
        play = self.res({"W": 95, "B": 85}, 79, {})
        html = render_color_availability(self.ctx(play, play))
        self.assertIn('class="good">95%', html)
        self.assertIn('class="warn">85%', html)
        self.assertIn('class="bad">79%', html)

    def test_no_double_rows_without_double_pip_cards(self):
        play = self.res({"W": 95}, 95, {})
        self.assertNotIn("≥ 2 Quellen", render_color_availability(self.ctx(play, play)))

    def test_double_row_names_the_cards(self):
        play = self.res({"R": 99}, 99, {"R": 88})
        html = render_color_availability(self.ctx(play, play, {"R": ["Red Ogre", "Red Giant"]}))
        self.assertIn("≥ 2 Quellen Rot bis Runde 4", html)
        self.assertIn("Red Ogre, Red Giant", html)

    def test_not_measured_turn_four_is_shown_as_dash(self):
        play = self.res({"R": 99}, 99, {"R": 0}, measured=False)
        html = render_color_availability(self.ctx(play, play, {"R": ["Red Ogre"]}))
        self.assertIn("–", html)

    def test_colorless_deck_has_no_section(self):
        play = self.res({}, 100, {})
        self.assertEqual(render_color_availability(self.ctx(play, play)), "")


if __name__ == "__main__":
    unittest.main()
