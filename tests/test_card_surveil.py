"""Surveil durch Karten (fester Wert): Erkennung, Modell-Abdeckung, Simulation und Bericht."""
import random
import unittest
from unittest import mock

import mtg_sim
from components import simulation as sim
from components.cards import card_info
from components.coverage import M_FLOW, M_NONE, analyze_card
from tests.fixtures import args_for
from tests.fixtures_walkers import CARDS as W_CARDS, DATA as W_DATA, _card

DASH = "—"
CREATURE = f"Creature {DASH} Test"


def raw(text, type_line="Sorcery", cost="{W}", cmc=1, name="Test Surveil", power=None, toughness=None,
        produced=None):
    return _card(name, type_line, cost, cmc, "W", text, power=power, toughness=toughness, produced=produced)


def surveils(text, **kw):
    return card_info(raw(text, **kw))[0].surveil


SV_DATA = {c["name"]: c for c in [
    raw("Surveil 2.", name="Test Surveil Two"),
    raw("When this creature enters, surveil 1.", type_line=CREATURE, cost="{1}{W}", cmc=2, name="Test Surveil Bear",
        power="2", toughness="2"),
    raw("({T}: Add {W}.)\nWhen this land enters, surveil 1.", type_line=f"Land {DASH} Plains", cost="", cmc=0,
        name="Test Surveil Land", produced=["W"]),
]}
SV = {name: card_info(c)[0] for name, c in SV_DATA.items()}
PLAINS, BEAR, BIG = W_CARDS["Plains"], W_CARDS["Test Bear"], W_CARDS["Test Big"]


class SurveilParsingTests(unittest.TestCase):
    def test_spell(self):
        self.assertEqual(surveils("Surveil 2."), 2)

    def test_spell_with_surveil_after_another_effect(self):
        self.assertEqual(surveils("Exile target creature or planeswalker that's green or blue. Surveil 1. "
                                  "(Look at the top card of your library. You may put it into your graveyard.)"), 1)

    def test_creature_enters(self):
        self.assertEqual(surveils("When this creature enters, surveil 1.", type_line=CREATURE, power="1",
                                  toughness="1"), 1)
        self.assertEqual(surveils("When Test Surveil enters, surveil 2.", type_line=CREATURE, power="1",
                                  toughness="1"), 2)

    def test_land_enters(self):
        card, shown = card_info(SV_DATA["Test Surveil Land"])
        self.assertEqual(card.surveil, 1)
        self.assertTrue(card.is_land)
        self.assertIn("[Surveil 1]", shown)

    def test_tag_in_the_card_list(self):
        self.assertIn("[Surveil 2]", card_info(raw("Surveil 2."))[1])

    def test_not_modelled(self):
        for text, type_line in (
                ("Whenever another creature you control with power 2 or less enters, surveil 1.", CREATURE),
                ("{3}{U}: Surveil 1.", CREATURE),
                ("Sacrifice another creature or artifact: Surveil 1.", CREATURE),
                ("Choose one —\n• Destroy target creature.\n• Surveil 2.", "Sorcery"),
                ("Surveil 1, then draw a card.", "Sorcery"),
                ("Surveil X, where X is the number of creatures you control.", "Sorcery"),
                ("Whenever you scry or surveil, create a 1/1 Thopter token.", CREATURE),
                ("When this creature dies, surveil 1.", CREATURE),
        ):
            with self.subTest(text=text):
                self.assertEqual(surveils(text, type_line=type_line, power="1", toughness="1"), 0)

    def test_prepared_spell_half_is_not_modelled(self):
        card = {"name": "Test Prep", "layout": "prepare", "type_line": f"{CREATURE} // Sorcery", "mana_cost": "",
                "colors": ["U"], "keywords": [], "card_faces": [
                    {"name": "Test Prep", "type_line": CREATURE, "mana_cost": "{3}{U}", "power": "2",
                     "toughness": "2", "oracle_text": "Flying"},
                    {"name": "Peer Review", "type_line": "Sorcery", "mana_cost": "{2}{U}",
                     "oracle_text": "Surveil 1."}]}
        self.assertEqual(card_info(card)[0].surveil, 0)


class SurveilCoverageTests(unittest.TestCase):
    def cats(self, text, type_line="Sorcery", produced=None):
        return {(c, m) for c, m, _l in analyze_card(raw(text, type_line=type_line, power="1", toughness="1",
                                                        produced=produced))}

    def test_modelled_surveil_is_not_flagged(self):
        self.assertEqual(self.cats("Surveil 2."), set())
        self.assertEqual(self.cats("When this creature enters, surveil 1.", CREATURE), set())
        self.assertEqual(self.cats("({T}: Add {W}.)\nWhen this land enters, surveil 1.", f"Land {DASH} Plains",
                                   ["W"]), set())

    def test_the_rest_of_the_line_is_still_checked(self):
        self.assertEqual(self.cats("Exile target card from an opponent's graveyard. Surveil 1."),
                         {("Interaktion mit dem Gegner", M_NONE)})

    def test_unmodelled_surveil_stays_flagged(self):
        for text in ("Whenever another creature you control with power 2 or less enters, surveil 1.",):
            with self.subTest(text=text):
                self.assertIn(("Kartenfluss", M_FLOW), self.cats(text, CREATURE))
        self.assertEqual(self.cats("{3}{U}: Surveil 1.", CREATURE), set())  # Faehigkeit inzwischen modelliert


class ApplySurveilTests(unittest.TestCase):
    def test_land_goes_to_the_graveyard_with_enough_lands(self):
        library = [PLAINS, BEAR]
        events, binned = sim.apply_surveils([1], library, [BIG], [PLAINS] * 4)
        self.assertEqual((events, binned), (1, 1))
        self.assertEqual(library, [BEAR])

    def test_land_stays_when_lands_are_missing(self):
        library = [PLAINS, BEAR]
        self.assertEqual(sim.apply_surveils([1], library, [BIG], [PLAINS, PLAINS]), (1, 0))
        self.assertEqual(library, [PLAINS, BEAR])

    def test_several_sources_one_after_another(self):
        library = [PLAINS, PLAINS, BEAR]
        self.assertEqual(sim.apply_surveils([1, 1], library, [BEAR], [PLAINS] * 4), (2, 2))
        self.assertEqual(library, [BEAR])

    def test_empty_library(self):
        self.assertEqual(sim.apply_surveils([2], [], [BEAR], [PLAINS]), (0, 0))


def run(deck, sims=200, seed=13):
    cards = [c for name, n in deck.items() for c in [{**W_CARDS, **SV}[name]] * n]
    random.seed(seed)
    return sim.simulate(cards, sims, False, 3, 8, True, False, None, 11, 20, 6, True, 3, 6, False, True, 5, True)


class SurveilSimulationTests(unittest.TestCase):
    def test_surveil_cards_surveil(self):
        res = run({"Plains": 12, "Test Surveil Land": 5, "Test Bear": 13, "Test Surveil Two": 5,
                   "Test Surveil Bear": 5})
        sv = res["card_surveil"]
        self.assertTrue(sv["on"])
        self.assertGreater(sv["events"], 1.0)
        self.assertGreater(sv["games"], 0.5)
        self.assertGreater(sv["lands"], 0.3)
        self.assertGreaterEqual(sv["events"] * 2, sv["lands"])

    def test_fewer_lands_drawn_than_without_surveil(self):
        with_sv = run({"Plains": 17, "Test Bear": 13, "Test Surveil Two": 10}, sims=400)
        without = run({"Plains": 17, "Test Bear": 23}, sims=400)
        self.assertLess(with_sv["lands_drawn"], without["lands_drawn"])

    def test_off_without_surveil_cards(self):
        res = run({"Plains": 17, "Test Bear": 23})
        self.assertEqual(res["card_surveil"], {"on": False, "events": 0.0, "games": 0.0, "lands": 0.0})


def build(deck):
    data = {**W_DATA, **SV_DATA}
    entries = [{"path": "", "name": "A", "deck": dict(deck), "parts": [("A", dict(deck))]}]
    with mock.patch.object(mtg_sim, "fetch_cards_cached", lambda n, refresh=False: data):
        return mtg_sim.simulate_entries(entries, args_for(["deck.txt", "--sims", "100"]), progress=lambda m: None)


class SurveilReportTests(unittest.TestCase):
    def test_section_with_surveil_cards(self):
        html = build({"Plains": 12, "Test Surveil Land": 5, "Test Bear": 18, "Test Surveil Two": 5})
        report, help_view = html[:html.index('id="view-help"')], html[html.index('id="view-help"'):]
        self.assertIn('id="surveil"', report)
        self.assertIn("Surveil durch Karten", report)
        self.assertIn("Ø Länder in den Friedhof", report)
        self.assertIn("Test Surveil Land", report)
        self.assertIn('id="hiw-surveil"', help_view)

    def test_no_section_without_surveil_cards(self):
        html = build({"Plains": 17, "Test Bear": 23})
        self.assertNotIn('id="surveil"', html)
        self.assertNotIn('id="hiw-surveil"', html)


if __name__ == "__main__":
    unittest.main()
