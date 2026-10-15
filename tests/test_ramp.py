"""Mana ausser Laendern (Ramp): Manaquellen, Treasure, Angriff getappter Kreaturen, Bericht und Uebersichten."""
import random
import shutil
import unittest
from unittest import mock

import mtg_sim
from components import simulation as sim
from components.cards import card_info
from components.coverage import analyze_card
from components.mana import land_key
from tests.fixtures import args_for
from tests.fixtures_walkers import _card

DASH = "—"
CREATURE = f"Creature {DASH} Elf Druid"
ANY = ("B", "G", "R", "U", "W")

RAW = {c["name"]: c for c in [
    _card("Forest", f"Basic Land {DASH} Forest", text="({T}: Add {G}.)", produced=["G"]),
    _card("Test Elves", CREATURE, "{G}", 1, "G", "{T}: Add {G}.", power="1", toughness="1"),
    _card("Test Hasty Elves", CREATURE, "{G}", 1, "G", "Haste\n{T}: Add {G}.", ["Haste"], "1", "1"),
    _card("Test Rock", "Artifact", "{2}", 2, "", "{T}: Add {C}{C}."),
    _card("Test Prism", "Artifact", "{1}", 1, "", "{T}: Add one mana of any color."),
    _card("Test Shaper", f"Creature {DASH} Test", "{1}{G}{G}", 3, "G", "", power="3", toughness="3"),
    _card("Test Bear", f"Creature {DASH} Bear", "{G}", 1, "G", power="2", toughness="2"),
    _card("Test Big", f"Creature {DASH} Test", "{4}{G}", 5, "G", power="5", toughness="5"),
    _card("Test Sprout", f"Creature {DASH} Test", "{G}", 1, "G", power="1", toughness="1"),
    _card("Test Pirate", f"Creature {DASH} Pirate", "{1}{G}", 2, "G", "When this creature enters, create a Treasure "
          "token.", power="2", toughness="1"),
]}
C = {name: card_info(raw)[0] for name, raw in RAW.items()}


def mana_src(text, type_line=CREATURE, keywords=()):
    return card_info(_card("T", type_line, "{G}", 1, "G", text, keywords, "1", "1"))[0].mana_src


def treasure(text, type_line=CREATURE):
    return card_info(_card("T", type_line, "{G}", 1, "G", text, (), "1", "1"))[0].treasure


class ParsingTests(unittest.TestCase):
    def test_single_color(self):
        self.assertEqual(mana_src("{T}: Add {G}."), (("G",),))

    def test_choice_of_colors(self):
        self.assertEqual(mana_src("{T}: Add {R} or {G}."), (("G", "R"),))

    def test_any_color(self):
        self.assertEqual(mana_src("{T}: Add one mana of any color."), (ANY,))

    def test_two_colorless(self):
        self.assertEqual(mana_src("{T}: Add {C}{C}.", type_line="Artifact"), (("C",), ("C",)))

    def test_not_modelled(self):
        for text in ("{1}, {T}: Add {R}{G}.", "Sacrifice this creature: Add {C}.", "{T}, Pay 1 life: Add {B}.",
                     "Add {C}{C}{C}.", "+1: Add {R}{R}."):
            with self.subTest(text=text):
                self.assertEqual(mana_src(text), ())

    def test_treasure(self):
        self.assertEqual(treasure("When this creature enters, create a Treasure token."), 1)
        self.assertEqual(treasure("When this creature enters, create two Treasure tokens."), 2)
        self.assertEqual(treasure("Create a Treasure token. Draw a card.", type_line="Instant"), 1)

    def test_treasure_not_modelled(self):
        for text, tl in (("Gift a Treasure\nCounter target spell.", "Instant"),
                         ("Target opponent creates a Treasure token.", "Sorcery"),
                         ("Whenever this creature attacks, create a Treasure token.", CREATURE)):
            with self.subTest(text=text):
                self.assertEqual(treasure(text, tl), 0)

    def test_tags_in_the_card_list(self):
        self.assertIn("[Mana: {G}]", card_info(RAW["Test Elves"])[1])
        self.assertIn("[Treasure 1]", card_info(RAW["Test Pirate"])[1])


class CoverageTests(unittest.TestCase):
    def cats(self, text, type_line=CREATURE):
        return {c for c, _m, _l in analyze_card(_card("T", type_line, "{G}", 1, "G", text, (), "1", "1"))}

    def test_modelled_lines_are_not_flagged(self):
        self.assertEqual(self.cats("{T}: Add {G}."), set())
        self.assertEqual(self.cats("{T}: Add one mana of any color.", "Artifact"), set())
        self.assertEqual(self.cats("When this creature enters, create a Treasure token."), set())

    def test_open_cases_stay_flagged(self):
        self.assertIn("Mana außer Ländern", self.cats("{1}, {T}: Add {R}{G}."))
        self.assertIn("Mana außer Ländern", self.cats("Whenever this creature attacks, create a Treasure token."))


class SourceTests(unittest.TestCase):
    def test_summoning_sick_creature_gives_no_mana(self):
        perms = [(C["Test Elves"], 2)]
        self.assertEqual(sim.mana_units(perms, 2), [])
        self.assertEqual([u for u, _i in sim.mana_units(perms, 3)], [("G",)])

    def test_haste_and_artifacts_give_mana_at_once(self):
        perms = [(C["Test Hasty Elves"], 2), (C["Test Rock"], 2)]
        self.assertEqual(sorted(u for u, _i in sim.mana_units(perms, 2)), [("C",), ("C",), ("G",)])

    def test_creature_units_know_their_creature(self):
        units = sim.mana_units([(C["Test Rock"], 1), (C["Test Elves"], 1)], 2)
        self.assertEqual([(u, i) for u, i in units if i is not None], [(("G",), 1)])


class TappingTests(unittest.TestCase):
    def test_dork_needed_for_the_spell(self):
        lands = [("G",), ("G",)]
        tapped = sim.tapped_for_mana([C["Test Shaper"].alts], lands, [(("G",), 0)], [C["Test Elves"]])
        self.assertEqual(tapped, {0})

    def test_dork_not_needed(self):
        lands = [("G",), ("G",), ("G",)]
        self.assertEqual(sim.tapped_for_mana([C["Test Shaper"].alts], lands, [(("G",), 0)], [C["Test Elves"]]), set())

    def test_weakest_creature_is_tapped(self):
        lands = [("G",), ("G",)]
        units = [(("G",), 0), (("G",), 1)]
        strong = card_info(_card("Test Strong Elves", CREATURE, "{G}", 1, "G", "{T}: Add {G}.", (), "4", "4"))[0]
        self.assertEqual(sim.tapped_for_mana([C["Test Shaper"].alts], lands, units, [strong, C["Test Elves"]]), {1})


class TreasureUseTests(unittest.TestCase):
    def test_treasure_only_when_it_enables_more(self):
        k, chosen = sim.use_treasures([C["Test Shaper"]], [("G",), ("G",)], 2, True, True)
        self.assertEqual((k, [c.name for c in chosen]), (1, ["Test Shaper"]))

    def test_no_treasure_if_not_needed(self):
        k, _chosen = sim.use_treasures([C["Test Bear"]], [("G",), ("G",)], 2, True, True)
        self.assertEqual(k, 0)

    def test_no_treasure_without_tokens(self):
        self.assertEqual(sim.use_treasures([C["Test Shaper"]], [("G",)], 0, True, True)[0], 0)


def run(deck, sims=300, seed=23):
    cards = [c for name, n in deck.items() for c in [C[name]] * n]
    random.seed(seed)
    return sim.simulate(cards, sims, False, 3, 8, True, False, None, 11, 20, 6, True, 3, 6, False, True, 5, True)


class ExampleTests(unittest.TestCase):
    """Beispiel des Nutzers: Runde 1 Forest + Llanowar Elves, Runde 2 Simulacrum Shaper ({1}{G}{G})."""

    def run_hand(self, dork):
        deck = [C["Forest"]] * 2 + [C[dork], C["Test Shaper"]] + [C["Test Big"]] * 3 + [C["Forest"]] * 33
        with mock.patch.object(sim, "deal_opening", lambda cards, mull, mn: (deck[:7], deck[7:], 0, [])):
            random.seed(1)
            return sim.simulate(deck, 1, False, 3, 3, True, False, None, 11, 20, 6, True, 3, 6, False, True, 5, True)

    def test_shaper_on_turn_two(self):
        res = self.run_hand("Test Elves")
        self.assertEqual(res["curve"]["spent"][1], 1)  # Elves
        self.assertEqual(res["curve"]["spent"][2], 3)  # Shaper mit 2 Forest + Elves
        self.assertEqual(res["ramp"]["first_avg"], 2)

    def test_without_dork_no_shaper_on_turn_two(self):
        res = self.run_hand("Test Sprout")
        self.assertLess(res["curve"]["spent"][2], 3)


class SimulationTests(unittest.TestCase):
    DORKS = {"Forest": 16, "Test Elves": 6, "Test Shaper": 10, "Test Big": 8}
    PLAIN = {"Forest": 16, "Test Sprout": 6, "Test Shaper": 10, "Test Big": 8}

    def test_ramp_is_measured(self):
        r = run(self.DORKS)["ramp"]
        self.assertTrue(r["on"])
        self.assertGreater(r["games"], 0.4)
        self.assertLess(r["first_avg"], 4)
        self.assertGreater(r["extra"][2], 0.2)
        self.assertGreater(r["held_back"], 0)

    def test_more_mana_spent_early_than_without_dorks(self):
        dorks, plain = run(self.DORKS), run(self.PLAIN)
        early = lambda r: r["curve"]["spent"][2] + r["curve"]["spent"][3]
        self.assertGreater(early(dorks), early(plain))

    def test_curve_counts_extra_mana_as_available(self):
        res = run(self.DORKS)
        cv = res["curve"]
        for t in cv["avail"]:
            self.assertLessEqual(cv["spent"][t], cv["avail"][t])

    def test_treasure(self):
        r = run({"Forest": 16, "Test Pirate": 10, "Test Shaper": 8, "Test Big": 6})["ramp"]
        self.assertGreater(r["treasure_made"], 0.5)
        self.assertLessEqual(r["treasure_used"], r["treasure_made"])
        self.assertGreater(r["treasure_used"], 0)

    def test_off_without_sources(self):
        r = run({"Forest": 17, "Test Bear": 23})["ramp"]
        self.assertFalse(r["on"])
        self.assertEqual(r["games"], 0.0)


def build(deck):
    entries = [{"path": "", "name": "A", "deck": dict(deck), "parts": [("A", dict(deck))]}]
    with mock.patch.object(mtg_sim, "fetch_cards_cached", lambda n, refresh=False: RAW):
        return mtg_sim.simulate_entries(entries, args_for(["deck.txt", "--sims", "100"]), progress=lambda m: None)


class ReportTests(unittest.TestCase):
    def test_section_with_mana_sources(self):
        html = build(SimulationTests.DORKS)
        report, help_view = html[:html.index('id="view-help"')], html[html.index('id="view-help"'):]
        self.assertIn('id="ramp"', report)
        self.assertIn("Spiele mit Ramp", report)
        self.assertIn("Test Elves", report[report.index('id="ramp"'):])
        self.assertIn("Manaquellen (Karten)", report)
        self.assertIn('id="hiw-ramp"', help_view)

    def test_no_section_without_sources(self):
        html = build({"Forest": 17, "Test Bear": 23})
        self.assertNotIn('id="ramp"', html)
        self.assertNotIn("Manaquellen (Karten)", html)


@unittest.skipUnless(shutil.which("node"), "Node.js nicht installiert")
class PageCountsTests(unittest.TestCase):
    def test_counts_and_parity(self):
        from tests.test_type_overview import run_js
        from components.report_cards import type_counts
        copies = [{"kinds": ["creature"], "mark": "core", "empower": False, "points": 0, "flow": [], "ramp": True},
                  {"kinds": ["creature"], "mark": "splash", "empower": False, "points": 0, "flow": []}]
        r = run_js(copies, [])
        self.assertEqual((r["splash"]["ramp"], r["nosplash"]["ramp"]), (1, 1))
        ctx = {"rows": [("A", 1, None, "")], "info": {"A": {"kinds": ["creature"], "ramp": True}}}
        self.assertEqual(type_counts(ctx)["ramp"], 1)

    def test_page_passes_the_field(self):
        from tests.test_card_flow import run_copies_of
        out = run_copies_of([{"mark": "core", "card": {"kinds": ["creature"], "ramp": True}},
                             {"mark": "core", "card": {}}])
        self.assertTrue(out[0]["ramp"])
        self.assertNotIn("ramp", out[1])


if __name__ == "__main__":
    unittest.main()
