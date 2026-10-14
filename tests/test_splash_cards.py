"""Spielbarkeit der Splash-Karten: Messung in der Simulation und Abschnitt im Bericht (nur Drafthelper-Splash)."""
import random
import unittest
from unittest import mock

import mtg_sim
from components import simulation as sim
from tests.fixtures import CARDS as RAW, args_for
from components.cards import card_info

C = {name: card_info(raw)[0] for name, raw in RAW.items()}


def run(deck, track, sims=300, seed=21, on_draw=False):
    cards = [c for name, n in deck.items() for c in [C[name]] * n]
    random.seed(seed)
    return sim.simulate(cards, sims, on_draw, 3, 8, True, True, None, 11, 20, 6, True, 3, 6, False, True, 5, True,
                        track=track)


class MeasurementTests(unittest.TestCase):
    def test_counts_are_consistent(self):
        res = run({"Plains": 14, "Mountain": 3, "Test Bear": 21, "Test Hasty": 2}, {"Test Hasty"})
        s = res["splash_cards"]["Test Hasty"]
        self.assertEqual(s["games"], 300)
        self.assertGreater(s["drawn"], 50)
        self.assertLessEqual(s["castable"], s["drawn"])
        self.assertLessEqual(s["on_time"], s["castable"])
        self.assertLessEqual(s["cast"], s["castable"])
        self.assertGreaterEqual(s["wait_sum"], 0)

    def test_without_sources_never_castable(self):
        res = run({"Plains": 17, "Test Bear": 21, "Test Hasty": 2}, {"Test Hasty"})
        s = res["splash_cards"]["Test Hasty"]
        self.assertGreater(s["drawn"], 0)
        self.assertEqual((s["castable"], s["cast"], s["on_time"]), (0, 0, 0))

    def test_more_sources_make_it_more_castable(self):
        few = run({"Plains": 15, "Mountain": 2, "Test Bear": 21, "Test Hasty": 2}, {"Test Hasty"})["splash_cards"]
        many = run({"Plains": 10, "Mountain": 7, "Test Bear": 21, "Test Hasty": 2}, {"Test Hasty"})["splash_cards"]
        rate = lambda s: s["Test Hasty"]["castable"] / s["Test Hasty"]["drawn"]
        self.assertGreater(rate(many), rate(few) + 0.15)

    def test_main_color_card_is_castable_almost_always(self):
        res = run({"Plains": 17, "Test Bear": 23}, {"Test Bear"})
        s = res["splash_cards"]["Test Bear"]
        self.assertGreater(s["castable"] / s["drawn"], 0.95)
        self.assertGreater(s["on_time"] / s["drawn"], 0.85)

    def test_no_tracking_by_default(self):
        cards = [C["Plains"]] * 17 + [C["Test Bear"]] * 23
        random.seed(1)
        res = sim.simulate(cards, 50, False, 3, 8, True, False, None, 11, 20, 6, True, 3, 6, False, True, 5, True)
        self.assertEqual(res["splash_cards"], {})

    def test_tracking_does_not_change_the_game(self):
        deck = {"Plains": 14, "Mountain": 3, "Test Bear": 21, "Test Hasty": 2}
        a = run(deck, {"Test Hasty"}, seed=5)
        b = run(deck, set(), seed=5)
        self.assertEqual((a["cast"], a["dmg"]), (b["cast"], b["dmg"]))


SPLASH = {"Test Hasty": 2}
CORE = {"Plains": 14, "Mountain": 3, "Test Bear": 21}


def build(entries):
    with mock.patch.object(mtg_sim, "fetch_cards_cached", lambda n, refresh=False: RAW):
        return mtg_sim.simulate_entries(entries, args_for(["deck.txt", "--sims", "100"]), progress=lambda m: None)


def drafthelper_entries():
    splash = dict(CORE, **SPLASH)
    nosplash = dict(CORE, **{"Test Bear": 23})
    return [{"path": "", "name": "Splash", "deck": splash, "parts": [("Core", dict(CORE)), ("Splash", dict(SPLASH))],
             "cats": {}, "role": "splash"},
            {"path": "", "name": "NoSplash", "deck": nosplash,
             "parts": [("Core", dict(CORE)), ("NoSplash", {"Test Bear": 2})], "cats": {}, "role": "nosplash"}]


class ReportTests(unittest.TestCase):
    def test_section_for_the_splash_variant(self):
        html = build(drafthelper_entries())
        report, help_view = html[:html.index('id="view-help"')], html[html.index('id="view-help"'):]
        self.assertIn('id="splashkarten"', report)        # Splash-Variante (erstes Deck)
        self.assertNotIn('id="splashkarten-1"', report)   # NoSplash-Variante hat keine Splash-Karten
        self.assertIn("Spielbar, wenn gezogen", report)
        self.assertIn("Test Hasty", report[report.index('id="splashkarten"'):])
        self.assertIn('id="hiw-splashkarten"', help_view)
        # direkt nach der Farbverfuegbarkeit
        self.assertLess(report.index('id="farben"'), report.index('id="splashkarten"'))

    def test_no_section_in_a_normal_run(self):
        html = build([{"path": "", "name": "A", "deck": dict(CORE, **SPLASH), "parts": []}])
        self.assertNotIn('id="splashkarten"', html)
        self.assertNotIn('id="hiw-splashkarten"', html)

    def test_only_nonland_cards_of_the_splash_group(self):
        entries = drafthelper_entries()
        entries[0]["parts"][1] = ("Splash", {"Test Hasty": 2, "Mountain": 1})
        entries[0]["deck"]["Mountain"] = 4
        html = build(entries)
        section = html[html.index('id="splashkarten"'):html.index("</section>", html.index('id="splashkarten"'))]
        self.assertIn("Test Hasty", section)
        self.assertNotIn(">Mountain<", section)


if __name__ == "__main__":
    unittest.main()
