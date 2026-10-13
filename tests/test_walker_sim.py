import unittest
from unittest import mock

import components.simulation as sim
from components.jace import creates_jace, creates_walker
from components.mana import can_cast_all, land_key
from components.simulation import simulate
from tests.fixtures_walkers import CARDS

DECK = ([CARDS["Test Commons"]] * 8 + [CARDS["Plains"]] * 6 + [CARDS["Island"]] * 2 + [CARDS["Test Sanctum"]] * 2 +
        [CARDS["Test Empower"]] * 5 + [CARDS["Test Empower Creature"]] * 3 + [CARDS["Test Walker"]] * 2 +
        [CARDS["Test Jace"]] * 2 + [CARDS["Test Bear"]] * 10)


class Recorder:
    """Merkt sich jeden Aufruf von choose_land samt Ergebnis (Wrapper um die echte Funktion)."""

    def __init__(self):
        self.calls = []
        self._real = sim.choose_land

    def __call__(self, hand, spells, pool, battlefield, walker_bf, jace_bf, has_creature, auras):
        result = self._real(hand, spells, pool, battlefield, walker_bf, jace_bf, has_creature, auras)
        self.calls.append(dict(hand=list(hand), spells=list(spells), pool=list(pool), battlefield=list(battlefield),
                               walker_bf=walker_bf, jace_bf=jace_bf, result=result))
        return result


def run_recorded(sims=300, seed=5):
    import random
    random.seed(seed)
    rec = Recorder()
    with mock.patch.object(sim, "choose_land", rec):
        for on_draw in (False, True):
            simulate(DECK, sims, on_draw, 3, 8, True, True, None, 11, 20, 6, True, 3, 6, False, True, 5, True)
    return rec.calls


def run_event_log(sims=200, seed=9):
    """Reihenfolge der Aufrufe: ('land', vorab_zauber) fuer choose_land und ('cast', must) fuer die Zauberwahl der
    Spielschleife (Aufrufe innerhalb von choose_land stehen davor)."""
    import random
    random.seed(seed)
    events = []
    real_choose, real_best = sim.choose_land, sim.best_cast

    def choose(*args):
        result = real_choose(*args)
        events.append(("land", result[2]))
        return result

    def best(spells, key, has_creature, auras, must=None):
        result = real_best(spells, key, has_creature, auras, must=must)
        events.append(("cast", must, result[1]))
        return result

    with mock.patch.object(sim, "choose_land", choose), mock.patch.object(sim, "best_cast", best):
        for on_draw in (False, True):
            simulate(DECK, sims, on_draw, 3, 8, True, True, None, 11, 20, 6, True, 3, 6, False, True, 5, True)
    return events


class ForcedSpellIsCastTests(unittest.TestCase):
    def test_the_spell_cast_before_the_land_is_part_of_the_turns_spells(self):
        events = run_event_log()
        checked = 0
        for i, ev in enumerate(events):
            if ev[0] != "land" or ev[1] is None:
                continue
            nxt = next(e for e in events[i + 1:] if e[0] == "cast")
            self.assertEqual(nxt[1], ev[1], "die Zauberwahl der Runde muss den vorab gewirkten Zauber erzwingen")
            self.assertIn(ev[1], nxt[2], "der vorab gewirkte Zauber muss in dieser Runde gespielt werden")
            checked += 1
        self.assertGreater(checked, 0)


class WalkerSimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calls = run_recorded()

    def test_the_real_loop_uses_choose_land(self):
        self.assertGreater(len(self.calls), 500)

    def test_first_turn_has_no_planeswalker_on_the_table(self):
        first = [c for c in self.calls if not c["battlefield"]]
        self.assertTrue(first)
        for c in first:
            self.assertFalse(c["walker_bf"] or c["jace_bf"])

    def test_a_spell_is_cast_first_in_some_games_and_is_valid(self):
        forced = [c for c in self.calls if c["result"][2] is not None]
        self.assertGreater(len(forced), 0, "der Fall 'Zauber vor dem Land' kam nie vor: Test waere leer")
        for c in forced:
            land, tapped, spell = c["result"]
            self.assertIn(land.tap_mode, ("planeswalker", "jace"))
            self.assertFalse(tapped)
            self.assertIn(spell, c["spells"])
            self.assertTrue(creates_walker(spell))
            self.assertTrue(can_cast_all((spell.alts,), land_key(c["pool"])), "vor dem Land bezahlbar")
            if land.tap_mode == "jace":
                self.assertTrue(creates_jace(spell))
            self.assertFalse(c["walker_bf"] if land.tap_mode == "planeswalker" else c["jace_bf"])

    def test_untapped_conditional_lands_have_a_reason(self):
        for c in self.calls:
            land, tapped, spell = c["result"]
            if land is None or tapped:
                continue
            if land.tap_mode == "planeswalker":
                self.assertTrue(c["walker_bf"] or spell is not None)
            if land.tap_mode == "jace":
                self.assertTrue(c["jace_bf"] or any(x.is_jace for x in c["hand"]) or spell is not None)

    def test_conditional_lands_are_tapped_only_when_no_planeswalker_is_available(self):
        for c in self.calls:
            land, tapped, spell = c["result"]
            if land is None or not tapped or land.tap_mode not in ("planeswalker", "jace"):
                continue
            key = land_key(c["pool"])
            enablers = [x for x in c["spells"] if creates_walker(x) and can_cast_all((x.alts,), key)]
            if land.tap_mode == "planeswalker":
                self.assertFalse(c["walker_bf"])
                self.assertEqual(enablers, [])
            else:
                self.assertFalse(c["jace_bf"] or any(x.is_jace for x in c["hand"]))
                self.assertEqual([x for x in enablers if creates_jace(x)], [])

    def test_some_conditional_lands_come_untapped_through_the_new_logic(self):
        untapped = [c for c in self.calls if c["result"][0] is not None
                    and c["result"][0].tap_mode in ("planeswalker", "jace") and not c["result"][1]]
        self.assertGreater(len(untapped), 0)


if __name__ == "__main__":
    unittest.main()
