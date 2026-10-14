import unittest
from unittest import mock

import mtg_sim
from components import simulation as sim
from components.jace import JaceState, surveil
from tests.fixtures import CARDS as BASE_DATA, args_for
from tests.fixtures_walkers import CARDS

PLAINS, BIG, BEAR, EMPOWER = CARDS["Plains"], CARDS["Test Big"], CARDS["Test Bear"], CARDS["Test Empower"]


class SurveilDecisionTests(unittest.TestCase):
    def test_land_stays_on_top_when_lands_are_missing_for_the_most_expensive_card(self):
        library = [PLAINS, BEAR]
        binned = surveil(library, 1, hand=[BIG], battlefield=[PLAINS, PLAINS])  # 2 Laender, Big kostet 4
        self.assertEqual(binned, [])
        self.assertEqual(library, [PLAINS, BEAR])

    def test_land_goes_to_the_graveyard_when_enough_lands_are_there(self):
        library = [PLAINS, BEAR]
        binned = surveil(library, 1, hand=[BIG], battlefield=[PLAINS] * 4)
        self.assertEqual(binned, [PLAINS])
        self.assertEqual(library, [BEAR])

    def test_lands_in_hand_count_as_available(self):
        library = [PLAINS, BEAR]
        binned = surveil(library, 1, hand=[BIG, PLAINS, PLAINS], battlefield=[PLAINS, PLAINS])
        self.assertEqual(binned, [PLAINS])

    def test_spells_always_stay_on_top(self):
        library = [BIG, PLAINS]
        self.assertEqual(surveil(library, 1, hand=[BEAR], battlefield=[PLAINS] * 5), [])
        self.assertEqual(library, [BIG, PLAINS])

    def test_without_spells_in_hand_a_land_goes_to_the_graveyard(self):
        library = [PLAINS]
        self.assertEqual(surveil(library, 1, hand=[PLAINS], battlefield=[]), [PLAINS])

    def test_surveil_two_keeps_only_as_many_lands_as_needed(self):
        library = [PLAINS, PLAINS, BEAR]
        binned = surveil(library, 2, hand=[BIG], battlefield=[PLAINS] * 3)  # es fehlt genau 1 Land
        self.assertEqual(binned, [PLAINS])
        self.assertEqual(library, [PLAINS, BEAR])

    def test_order_of_kept_cards_is_unchanged(self):
        library = [BIG, PLAINS, BEAR, PLAINS]
        surveil(library, 3, hand=[BIG], battlefield=[])
        self.assertEqual(library, [BIG, PLAINS, BEAR, PLAINS])

    def test_empty_library(self):
        library = []
        self.assertEqual(surveil(library, 1, hand=[BIG], battlefield=[]), [])


class JaceAbilityTests(unittest.TestCase):
    def jace(self, loyalty):
        j = JaceState()
        j.loyalty = loyalty
        return j

    def test_three_or_more_loyalty_always_draws(self):
        j, hand, library = self.jace(3), [], [BEAR, PLAINS]
        self.assertTrue(j.try_activate(hand, library, 2, battlefield=[], allow_surveil=True))
        self.assertEqual((j.loyalty, j.acts, j.surveils, hand), (0, 1, 0, [BEAR]))

    def test_below_three_surveils_after_casting(self):
        j, library = self.jace(2), [PLAINS, BEAR]
        self.assertTrue(j.try_activate([BIG], library, 2, battlefield=[PLAINS] * 4, allow_surveil=True))
        self.assertEqual((j.loyalty, j.acts, j.surveils, j.surveil_lands), (1, 0, 1, 1))
        self.assertEqual(library, [BEAR])

    def test_surveil_down_to_zero_removes_the_token(self):
        j = self.jace(1)
        j.try_activate([BIG], [BEAR], 2, battlefield=[], allow_surveil=True)
        self.assertEqual(j.loyalty, 0)

    def test_no_surveil_when_not_allowed(self):
        j = self.jace(2)
        self.assertFalse(j.try_activate([BIG], [PLAINS], 2))
        self.assertEqual((j.loyalty, j.surveils), (2, 0))

    def test_only_once_per_turn(self):
        j = self.jace(2)
        j.try_activate([BIG], [PLAINS, PLAINS], 2, battlefield=[], allow_surveil=True)
        self.assertFalse(j.try_activate([BIG], [PLAINS], 2, battlefield=[], allow_surveil=True))
        self.assertEqual(j.surveils, 1)

    def test_nothing_without_loyalty_or_library(self):
        self.assertFalse(self.jace(0).try_activate([BIG], [PLAINS], 2, battlefield=[], allow_surveil=True))
        self.assertFalse(self.jace(2).try_activate([BIG], [], 2, battlefield=[], allow_surveil=True))


def fixed_game(order, horizon=1):
    """Ein Spiel ohne Mischen (Starthand = erste 7 Karten), On the Play."""
    with mock.patch("components.mulligan.random.shuffle", lambda x: None):
        return sim.simulate(list(order), 1, False, 1, horizon, True, False, None, 11, 20, 6, True, 3, 6, False,
                            False, 5, True)


class SimulationWiringTests(unittest.TestCase):
    def test_surveil_keeps_a_land_when_the_hand_needs_more_lands(self):
        # Runde 1: Plains, Test Empower -> Loyalty 1 -> Surveil 1 sieht Plains; Big (4) braucht mehr Laender
        order = [PLAINS, PLAINS, PLAINS, EMPOWER, BIG, BIG, BIG, PLAINS] + [BIG] * 20
        jc = fixed_game(order)["jace"]
        self.assertEqual((jc["surveil_all"], jc["surveil_lands_all"]), (1, 0))

    def test_surveil_bins_a_land_when_enough_lands_are_there(self):
        order = [PLAINS, PLAINS, PLAINS, PLAINS, EMPOWER, EMPOWER, EMPOWER, PLAINS] + [BIG] * 20
        jc = fixed_game(order)["jace"]
        self.assertEqual((jc["surveil_all"], jc["surveil_lands_all"]), (1, 1))

    def test_start_of_turn_only_draws_and_after_casting_surveil_is_allowed(self):
        calls = []
        real = JaceState.try_activate

        def spy(self, hand, library, turn, battlefield=None, allow_surveil=False):
            calls.append((turn, battlefield is not None, allow_surveil))
            return real(self, hand, library, turn, battlefield=battlefield, allow_surveil=allow_surveil)

        order = [PLAINS, PLAINS, PLAINS, EMPOWER, BIG, BIG, BIG] + [PLAINS, BIG] * 10
        with mock.patch.object(JaceState, "try_activate", spy):
            fixed_game(order, horizon=3)
        for turn in (1, 2, 3):
            this_turn = [c for c in calls if c[0] == turn]
            self.assertEqual(this_turn, [(turn, False, False), (turn, True, True)], this_turn)

    def test_decks_without_empower_are_unchanged(self):
        args = args_for(["deck.txt", "--sims", "100"])
        entry = {"name": "T", "deck": {"Plains": 17, "Test Bear": 23}, "parts": []}
        dd = mtg_sim.build_deck(entry, BASE_DATA, args)
        mtg_sim.simulate_deck(dd, args, 0, 15, progress=lambda m: None)
        self.assertEqual(dd["results"]["On the Play"]["jace"]["surveil_all"], 0)


if __name__ == "__main__":
    unittest.main()
