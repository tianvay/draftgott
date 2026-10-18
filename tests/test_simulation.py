import unittest

import mtg_sim
from tests.fixtures import CARDS, MIXED_DECK, args_for

MODES = ("On the Play", "On the Draw")


def run_deck(deck, sims=300, seed=11):
    """Simuliert ein Deck ({Name: Anzahl}) mit den Testkarten und gibt die Deckdaten zurueck."""
    args = args_for(["deck.txt", "--sims", str(sims), "--seed", str(seed), "--schaden", "4"])
    entry = {"name": "Test", "deck": dict(deck), "parts": [("Test", dict(deck))]}
    dd = mtg_sim.build_deck(entry, CARDS, args)
    mtg_sim.simulate_deck(dd, args, 0, max(args.max_runden, args.turns, args.curve_runden), progress=lambda m: None)
    return dd


def expected_damage(log):
    """Handgerechneter Schaden je Runde aus dem Spielprotokoll: Kreaturen vom Vorzug greifen an, neue nur mit
    Haste, Defender nie."""
    out, board = [], []  # board: (Karte, Runde des Ausspielens)
    for turn, _drew, _land, _tapped, cast, _tdmg, _total, _cyc, _jace in log:
        board += [(c, turn) for c in cast if c.is_creature]  # in dieser Runde gewirkt: zaehlt nur mit Haste
        out.append(sum(c.power for c, t in board if not c.defender and (t < turn or c.haste)))
    return out


class DamageRulesTests(unittest.TestCase):
    """Einsatzverzoegerung und Defender, geprueft an den Protokollen des schnellsten Lethals."""

    def _check(self, deck):
        dd = run_deck(deck)
        for mode in MODES:
            best = dd["results"][mode]["best_lethal"]
            self.assertIsNotNone(best, "kein Lethal gefunden: der Test waere leer")
            log = best["log"]
            self.assertEqual([row[5] for row in log], expected_damage(log))
            self.assertEqual(log[-1][6], sum(row[5] for row in log))

    def test_creatures_without_haste_attack_one_turn_later(self):
        self._check({"Plains": 17, "Test Bear": 23})

    def test_haste_creatures_attack_immediately(self):
        self._check({"Mountain": 17, "Test Hasty": 23})

    def test_defender_never_deals_damage(self):
        self._check({"Plains": 17, "Test Defender": 11, "Test Bear": 12})

    def test_deck_of_only_defenders_never_reaches_lethal(self):
        dd = run_deck({"Plains": 17, "Test Defender": 23})
        for mode in MODES:
            self.assertEqual(dd["results"][mode]["dmg"], [])
            self.assertIsNone(dd["results"][mode]["best_lethal"])

    def test_lethal_is_never_earlier_than_turn_two_without_haste(self):
        # Eine Kreatur ohne Haste kann fruehestens in Runde 2 angreifen (Schadensziel 4, Power 2 je Kreatur)
        dd = run_deck({"Plains": 17, "Test Bear": 23})
        for mode in MODES:
            self.assertGreaterEqual(min(dd["results"][mode]["dmg"]), 2)


class ReproducibilityTests(unittest.TestCase):
    def test_same_seed_gives_same_results(self):
        a, b = run_deck(MIXED_DECK, sims=150, seed=3), run_deck(MIXED_DECK, sims=150, seed=3)
        for mode in MODES:
            self.assertEqual(a["results"][mode]["cast"], b["results"][mode]["cast"])
            self.assertEqual(a["results"][mode]["dmg"], b["results"][mode]["dmg"])

    def test_reference_run_with_fixed_seed(self):
        """Referenzlauf: haelt das Verhalten der Simulation zum Zeitpunkt der Testeinfuehrung fest. Aendert sich
        eine Zahl, hat sich die Simulationslogik geaendert. Gewollt: Referenz nur nach Freigabe anpassen.
        Ungewollt: Fehler im Code suchen."""
        dd = run_deck(MIXED_DECK, sims=200, seed=42)
        play, draw = dd["results"]["On the Play"], dd["results"]["On the Draw"]
        got = {
            "play_cast": dict(play["cast"]), "draw_cast": dict(draw["cast"]),
            "play_dmg": (len(play["dmg"]), sum(play["dmg"])), "draw_dmg": (len(draw["dmg"]), sum(draw["dmg"])),
            "play_lethal": play["best_lethal"]["key"] if play["best_lethal"] else None,
            "draw_lethal": draw["best_lethal"]["key"] if draw["best_lethal"] else None,
        }
        self.assertEqual(got, {
            "play_cast": {1: 199, 2: 186, 3: 170}, "draw_cast": {1: 197, 2: 193, 3: 177},
            "play_dmg": (200, 590), "draw_dmg": (200, 558),
            "play_lethal": (2, -9), "draw_lethal": (2, -12)})


if __name__ == "__main__":
    unittest.main()
