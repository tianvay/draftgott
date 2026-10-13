import unittest

from components.cards import card_info, enters_tapped, land_tap_info
from components.jace import creates_jace, creates_walker
from components.mana import land_key
from components.simulation import best_cast, choose_land
from tests.fixtures_walkers import CARDS, DATA

PLAINS, ISLAND = CARDS["Plains"], CARDS["Island"]
COMMONS, SANCTUM = CARDS["Test Commons"], CARDS["Test Sanctum"]


def choose(hand, battlefield=(), walker_bf=False, jace_bf=False, auras=True):
    """Ruft choose_land mit Haelfte/Feld wie in der Simulation auf. hand: Karten (Laender und Zauber)."""
    battlefield = list(battlefield)
    spells = [c for c in hand if not c.is_land]
    pool = [l.land_colors for l in battlefield]
    return choose_land(list(hand), spells, pool, battlefield, walker_bf, jace_bf, False, auras)


class LandParsingTests(unittest.TestCase):
    def test_planeswalker_condition_is_its_own_mode(self):
        self.assertEqual(COMMONS.tap_mode, "planeswalker")

    def test_behold_a_jace_is_its_own_mode(self):
        self.assertEqual(SANCTUM.tap_mode, "jace")

    def test_basic_land_untouched(self):
        self.assertEqual(PLAINS.tap_mode, "no")

    def test_landtype_condition_is_still_a_check(self):
        front = {"oracle_text": "This land enters tapped unless you control a Plains or an Island.\n{T}: Add {W}."}
        self.assertEqual(land_tap_info(front, front), ("check", ("island", "plains")))

    def test_two_or_more_other_lands_is_still_slow(self):
        front = {"oracle_text": "This land enters tapped unless you control two or more other lands."}
        self.assertEqual(land_tap_info(front, front)[0], "slow")

    def test_always_tapped_land_is_still_tapped(self):
        front = {"oracle_text": "This land enters tapped.\n{T}: Add {G}."}
        self.assertEqual(land_tap_info(front, front)[0], "tapped")


class EntersTappedTests(unittest.TestCase):
    def test_planeswalker_land_needs_a_planeswalker(self):
        self.assertTrue(enters_tapped(COMMONS, []))
        self.assertTrue(enters_tapped(COMMONS, [], walker=False, jace=True))   # Jace allein hilft nicht, braucht Walker
        self.assertFalse(enters_tapped(COMMONS, [], walker=True))

    def test_jace_land_needs_a_jace(self):
        self.assertTrue(enters_tapped(SANCTUM, []))
        self.assertTrue(enters_tapped(SANCTUM, [], walker=True))                # anderer Planeswalker reicht nicht
        self.assertFalse(enters_tapped(SANCTUM, [], walker=True, jace=True))

    def test_other_modes_ignore_the_flags(self):
        self.assertFalse(enters_tapped(PLAINS, [], walker=True, jace=True))


class CardFlagTests(unittest.TestCase):
    def test_jace_planeswalker_is_marked(self):
        self.assertTrue(CARDS["Test Jace"].is_jace)
        self.assertTrue(CARDS["Test Jace"].is_planeswalker)

    def test_other_planeswalker_is_not_a_jace(self):
        self.assertFalse(CARDS["Test Walker"].is_jace)
        self.assertTrue(CARDS["Test Walker"].is_planeswalker)

    def test_creature_is_not_a_jace(self):
        self.assertFalse(CARDS["Test Bear"].is_jace)

    def test_creates_walker(self):
        for name in ("Test Walker", "Test Jace", "Test Empower", "Test Empower Creature"):
            self.assertTrue(creates_walker(CARDS[name]), name)
        for name in ("Test Bear", "Plains", "Test Big"):
            self.assertFalse(creates_walker(CARDS[name]), name)

    def test_creates_jace_only_through_empower_or_jace_cards(self):
        self.assertTrue(creates_jace(CARDS["Test Empower"]))
        self.assertTrue(creates_jace(CARDS["Test Empower Creature"]))
        self.assertTrue(creates_jace(CARDS["Test Jace"]))
        self.assertFalse(creates_jace(CARDS["Test Walker"]))


class BestCastMustTests(unittest.TestCase):
    def test_must_card_is_always_included(self):
        key = land_key([("W",), ("W",)])
        spells = [CARDS["Test Bear"], CARDS["Test Bear"], CARDS["Test Empower"]]
        score, chosen = best_cast(spells, key, False, True, must=CARDS["Test Empower"])
        self.assertIn(CARDS["Test Empower"], chosen)
        self.assertEqual(len(chosen), 2)

    def test_without_must_behavior_is_unchanged(self):
        key = land_key([("W",), ("W",)])
        spells = [CARDS["Test Bear"], CARDS["Test Bear"], CARDS["Test Empower"]]
        self.assertEqual(best_cast(spells, key, False, True), best_cast(spells, key, False, True, must=None))

    def test_uncastable_must_is_reported_as_impossible(self):
        key = land_key([("W",)])
        score, chosen = best_cast([CARDS["Test Big"]], key, False, True, must=CARDS["Test Big"])
        self.assertEqual((score[0], chosen), (-1, []))


class ChooseLandTests(unittest.TestCase):
    def test_planeswalker_land_with_castable_empower_spell_is_cast_first_and_untapped(self):
        land, tapped, forced = choose([COMMONS, CARDS["Test Empower"]], [PLAINS])
        self.assertEqual((land, tapped, forced), (COMMONS, False, CARDS["Test Empower"]))

    def test_planeswalker_card_works_as_enabler(self):
        land, tapped, forced = choose([COMMONS, CARDS["Test Walker"]], [PLAINS, PLAINS, PLAINS])
        self.assertEqual((land, tapped, forced), (COMMONS, False, CARDS["Test Walker"]))

    def test_creature_with_empower_on_enter_works_as_enabler(self):
        land, tapped, forced = choose([COMMONS, CARDS["Test Empower Creature"]], [PLAINS, PLAINS])
        self.assertEqual((tapped, forced), (False, CARDS["Test Empower Creature"]))

    def test_without_enabler_the_land_enters_tapped(self):
        land, tapped, forced = choose([COMMONS, CARDS["Test Bear"]], [PLAINS])
        self.assertEqual((land, tapped, forced), (COMMONS, True, None))

    def test_enabler_that_needs_the_new_land_cannot_be_cast_first(self):
        # Test Walker kostet 3, vor dem Land liegen nur 2 Laender
        land, tapped, forced = choose([COMMONS, CARDS["Test Walker"]], [PLAINS, PLAINS])
        self.assertEqual((tapped, forced), (True, None))

    def test_planeswalker_on_the_battlefield_makes_the_land_untapped_without_forcing(self):
        land, tapped, forced = choose([COMMONS, CARDS["Test Bear"]], [PLAINS], walker_bf=True)
        self.assertEqual((tapped, forced), (False, None))

    def test_no_lands_in_hand(self):
        self.assertEqual(choose([CARDS["Test Bear"]], [PLAINS]), (None, False, None))

    def test_sanctum_untapped_with_jace_card_in_hand_without_casting_it(self):
        land, tapped, forced = choose([SANCTUM, CARDS["Test Jace"]], [PLAINS])
        self.assertEqual((land, tapped, forced), (SANCTUM, False, None))

    def test_sanctum_untapped_with_jace_token_on_the_battlefield(self):
        land, tapped, forced = choose([SANCTUM, CARDS["Test Bear"]], [PLAINS], jace_bf=True, walker_bf=True)
        self.assertEqual((tapped, forced), (False, None))

    def test_sanctum_needs_a_jace_not_just_any_planeswalker(self):
        land, tapped, forced = choose([SANCTUM, CARDS["Test Walker"]], [PLAINS, PLAINS, PLAINS], walker_bf=True)
        self.assertEqual((tapped, forced), (True, None))

    def test_planeswalker_card_in_hand_that_is_not_a_jace_does_not_help_sanctum(self):
        land, tapped, forced = choose([SANCTUM, CARDS["Test Walker"]], [PLAINS, PLAINS, PLAINS])
        self.assertEqual((tapped, forced), (True, None))

    def test_sanctum_with_empower_spell_forces_it_first(self):
        land, tapped, forced = choose([SANCTUM, CARDS["Test Empower"]], [PLAINS])
        self.assertEqual((tapped, forced), (False, CARDS["Test Empower"]))

    def test_jace_card_in_hand_does_not_make_a_planeswalker_land_untapped(self):
        # "control a planeswalker" verlangt einen Planeswalker auf dem Tisch; Karten auf der Hand zaehlen nicht
        land, tapped, forced = choose([COMMONS, CARDS["Test Jace"]], [PLAINS])
        self.assertEqual((tapped, forced), (True, None))

    def test_cheaper_total_loss_decides_between_enablers(self):
        # zwei Enabler: der teure Empower-Zauber (4 Mana) ist vor dem Land nicht bezahlbar, der guenstige schon
        hand = [COMMONS, CARDS["Test Empower Big"], CARDS["Test Empower"]]
        land, tapped, forced = choose(hand, [PLAINS, PLAINS])
        self.assertEqual((tapped, forced), (False, CARDS["Test Empower"]))

    def test_plain_land_is_preferred_when_it_spends_more_mana(self):
        # Commons erzwingt Test Empower ({W}); mit Plains koennen beide Baren gespielt werden (2 statt 1+1 Mana)
        hand = [COMMONS, PLAINS, CARDS["Test Empower"], CARDS["Test Bear"]]
        land, tapped, forced = choose(hand, [PLAINS])
        self.assertIn(land, (COMMONS, PLAINS))
        if land == COMMONS:
            self.assertEqual((tapped, forced), (False, CARDS["Test Empower"]))
        else:
            self.assertIsNone(forced)

    def test_chosen_land_is_always_a_land_from_the_hand(self):
        hand = [COMMONS, ISLAND, CARDS["Test Bear"]]
        land, _, _ = choose(hand, [PLAINS])
        self.assertIn(land, (COMMONS, ISLAND))


if __name__ == "__main__":
    unittest.main()
