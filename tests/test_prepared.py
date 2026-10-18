"""Prepared: Zauberhaelfte als Kopie wirken (Erkennung, Modell-Abdeckung, Auswahl, Simulation, Bericht)."""
import random
import unittest
from unittest import mock

import mtg_sim
from components import simulation as sim
from components.cards import card_info
from components.coverage import M_LETHAL, analyze_card, metrics_of
from tests.fixtures import args_for
from tests.fixtures_walkers import CARDS as W_CARDS, DATA as W_DATA

DASH = "—"
ENTERS = "This creature enters prepared. (While it's prepared, you may cast a copy of its spell. Doing so unprepares it.)"
UPKEEP = ("At the beginning of your upkeep, if this creature isn't prepared, it becomes prepared. (While it's prepared, "
          "you may cast a copy of its spell. Doing so unprepares it.)")


def prep(name, cost, cmc, text, spell_name, spell_cost, spell_text, power="2", toughness="2", extra=""):
    return {"name": f"{name} // {spell_name}", "layout": "prepare", "type_line": f"Creature {DASH} Test // Sorcery",
            "mana_cost": "", "cmc": float(cmc), "colors": ["W"], "keywords": ["Prepared"],
            "card_faces": [
                {"name": name, "type_line": f"Creature {DASH} Test", "mana_cost": cost, "power": power,
                 "toughness": toughness, "oracle_text": text + (("\n" + extra) if extra else "")},
                {"name": spell_name, "type_line": "Sorcery", "mana_cost": spell_cost, "oracle_text": spell_text}]}


P_DATA = {c["name"]: c for c in [
    prep("Test Scholar", "{1}{W}", 2, ENTERS, "Test Study", "{W}", "Draw a card."),
    prep("Test Lurker", "{W}", 1, UPKEEP, "Test Jab", "{W}", "Test Jab deals 1 damage to target opponent."),
    prep("Test Reviewer", "{3}{W}", 4, ENTERS, "Test Review", "{2}{W}",
         "Create a 1/1 black Rat creature token for each creature that died this turn. Surveil 1."),
]}
P = {name: card_info(c)[0] for name, c in P_DATA.items()}
PLAINS, BEAR = W_CARDS["Plains"], W_CARDS["Test Bear"]
SCHOLAR, LURKER = P["Test Scholar // Test Study"], P["Test Lurker // Test Jab"]


class PreparedParsingTests(unittest.TestCase):
    def test_enters_prepared(self):
        mode, spell = SCHOLAR.prepared
        self.assertEqual(mode, "enters")
        self.assertEqual(spell.name, "Test Study")
        self.assertTrue(spell.is_copy)
        self.assertTrue(spell.is_instant_sorcery)
        self.assertEqual((spell.mv, spell.draws), (1, 1))
        self.assertEqual(SCHOLAR.mv, 2)  # die Kreatur selbst wird wie bisher gewirkt
        self.assertTrue(SCHOLAR.is_creature)

    def test_upkeep_prepared(self):
        self.assertEqual(LURKER.prepared[0], "upkeep")

    def test_spell_half_effects(self):
        spell = P["Test Reviewer // Test Review"].prepared[1]
        self.assertEqual((spell.mv, spell.surveil), (3, 1))

    def test_normal_cards_have_no_spell_half(self):
        self.assertEqual(BEAR.prepared, ())

    def test_unknown_prepare_wording_is_not_modelled(self):
        card = prep("Test Odd", "{W}", 1, "Flying", "Test Odd Spell", "{W}", "Draw a card.")
        self.assertEqual(card_info(card)[0].prepared, ())

    def test_tag_in_the_card_list(self):
        self.assertIn("[Prepared: Test Study {W}]", card_info(P_DATA["Test Scholar // Test Study"])[1])


class PreparedCoverageTests(unittest.TestCase):
    def cats(self, card):
        return {c for c, _m, _l in analyze_card(card)}

    def test_modelled_spell_half_is_not_flagged(self):
        self.assertEqual(analyze_card(P_DATA["Test Scholar // Test Study"]), [])

    def test_unmodelled_effects_of_the_spell_half_keep_their_category(self):
        card = P_DATA["Test Reviewer // Test Review"]
        self.assertEqual(self.cats(card), {"Tokens erzeugen"})
        self.assertEqual(metrics_of(analyze_card(card)), {M_LETHAL})
        self.assertEqual(self.cats(P_DATA["Test Lurker // Test Jab"]), set())  # Schaden an den Gegner modelliert

    def test_unknown_prepare_wording_stays_prepared_category(self):
        card = prep("Test Odd", "{W}", 1, "Flying", "Test Odd Spell", "{W}", "Draw a card.")
        self.assertIn("Prepared-Zauberhälfte", self.cats(card))


class CopyChoiceTests(unittest.TestCase):
    def test_hand_card_wins_a_tie_against_a_copy(self):
        hand_spell = card_info({"name": "Test Hand Sorcery", "type_line": "Sorcery", "mana_cost": "{W}", "cmc": 1.0,
                                "colors": ["W"], "oracle_text": "Draw a card.", "keywords": [], "layout": "normal"})[0]
        copy = SCHOLAR.prepared[1]
        _score, chosen = sim.best_cast([copy, hand_spell], (("W",),), True, True)
        self.assertEqual(chosen, [hand_spell])

    def test_copy_is_cast_when_mana_is_left(self):
        copy = SCHOLAR.prepared[1]
        _score, chosen = sim.best_cast([copy, BEAR], (("W",), ("W",)), True, True)
        self.assertEqual(sorted(c.name for c in chosen), ["Test Bear", "Test Study"])


class SameTurnCopyTests(unittest.TestCase):
    def test_creature_entering_prepared_allows_a_copy_with_leftover_mana(self):
        hand, library, bf = [SCHOLAR], [BEAR, BEAR], [PLAINS, PLAINS, PLAINS]
        r = sim.resolve_draws(hand, library, [SCHOLAR], [c.land_colors for c in bf], bf, PLAINS, False, True,
                              False, False)
        names = [c.name for c in r["chosen"]]
        self.assertEqual(names[:2], ["Test Scholar // Test Study", "Test Study"])
        self.assertEqual(r["drawn"], 1)  # die Kopie zieht eine Karte

    def test_upkeep_creature_gives_no_copy_in_the_same_turn(self):
        hand, library, bf = [LURKER], [BEAR], [PLAINS, PLAINS]
        r = sim.resolve_draws(hand, library, [LURKER], [c.land_colors for c in bf], bf, PLAINS, False, True,
                              False, False)
        self.assertEqual(r["chosen"], [LURKER])

    def test_available_copies_from_earlier_turns(self):
        hand, library, bf = [BEAR], [], [PLAINS, PLAINS]
        copy = LURKER.prepared[1]
        r = sim.resolve_draws(hand, library, [BEAR], [c.land_colors for c in bf], bf, PLAINS, True, True,
                              False, False, copies=[copy])
        self.assertEqual(r["chosen"], [BEAR])  # keine neuen Karten oder Kopien -> nichts zu tun


def run(deck, sims=200, seed=17, horizon=8):
    cards = [c for name, n in deck.items() for c in [{**W_CARDS, **P}[name]] * n]
    random.seed(seed)
    return sim.simulate(cards, sims, False, 3, horizon, True, False, None, 11, 20, 6, True, 3, 6, False, True, 5,
                        True)


class PreparedSimulationTests(unittest.TestCase):
    def test_copies_are_cast(self):
        res = run({"Plains": 17, "Test Bear": 13, "Test Scholar // Test Study": 10})
        pr = res["prepared"]
        self.assertTrue(pr["on"])
        self.assertGreater(pr["games"], 0.5)
        self.assertGreater(pr["copies"], 0.5)
        self.assertGreaterEqual(pr["mana"], pr["copies"])  # jede Kopie kostet hier 1 Mana

    def test_enters_prepared_is_used_at_most_once_per_creature(self):
        res = run({"Plains": 17, "Test Bear": 22, "Test Scholar // Test Study": 1}, sims=300)
        self.assertLessEqual(res["prepared"]["copies"], 1.0)

    def test_upkeep_creature_prepares_again(self):
        res = run({"Plains": 17, "Test Bear": 22, "Test Lurker // Test Jab": 1}, sims=300, horizon=12)
        self.assertGreater(res["prepared"]["copies"], 1.5)

    def test_copies_use_mana(self):
        with_p = run({"Plains": 17, "Test Bear": 13, "Test Scholar // Test Study": 10}, sims=300)
        cards_only = run({"Plains": 17, "Test Bear": 23}, sims=300)
        util = lambda r: sum(r["curve"]["spent"].values()) / sum(r["curve"]["avail"].values())
        self.assertGreater(util(with_p), util(cards_only) - 0.2)
        self.assertGreater(with_p["prepared"]["mana"], 0)

    def test_off_without_prepared_cards(self):
        res = run({"Plains": 17, "Test Bear": 23})
        self.assertEqual(res["prepared"], {"on": False, "copies": 0.0, "games": 0.0, "mana": 0.0})


def build(deck):
    data = {**W_DATA, **P_DATA}
    entries = [{"path": "", "name": "A", "deck": dict(deck), "parts": [("A", dict(deck))]}]
    with mock.patch.object(mtg_sim, "fetch_cards_cached", lambda n, refresh=False: data):
        return mtg_sim.simulate_entries(entries, args_for(["deck.txt", "--sims", "100"]), progress=lambda m: None)


class PreparedReportTests(unittest.TestCase):
    def test_section_with_prepared_cards(self):
        html = build({"Plains": 17, "Test Bear": 13, "Test Scholar // Test Study": 10})
        report, help_view = html[:html.index('id="view-help"')], html[html.index('id="view-help"'):]
        self.assertIn('id="prepared"', report)
        self.assertIn("Ø Kopien", report)
        self.assertIn("Test Scholar", report)
        self.assertIn('id="hiw-prepared"', help_view)

    def test_no_section_without_prepared_cards(self):
        html = build({"Plains": 17, "Test Bear": 23})
        self.assertNotIn('id="prepared"', html)
        self.assertNotIn('id="hiw-prepared"', html)


if __name__ == "__main__":
    unittest.main()
