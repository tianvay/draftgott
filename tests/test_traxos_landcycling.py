"""Regression: Traxos-Kostensenkung (verbilligte Fassung der Karte) zusammen mit Landcycling im Goldfish.
Fehler aus dem Drafthelper: plan_cycle -> without_many fand die verbilligte Traxos-Fassung nicht unter den Zaubern
(ValueError). Auch die Zaehlung der uebrigen Handkarten fuer Landcycling-Regel 1 muss die Fassungen zuordnen."""
import random
import unittest

from components import simulation as sim
from components.cards import card_info
from tests.fixtures_walkers import _card

DASH = "—"
ISLAND = card_info(_card("Island", f"Basic Land {DASH} Island", text="({T}: Add {U}.)", produced=["U"]))[0]
TRAXOS = card_info(_card("Traxos, Academy Guardian", f"Legendary Artifact Creature {DASH} Dragon Construct", "{3}{U}",
                         4, "U", "This spell costs {2} less to cast if you've cast a noncreature spell this turn.\n"
                         "Flying, vigilance\nProwess", ["Flying", "Vigilance", "Prowess"], "2", "2"))[0]
OPT = card_info(_card("Blue Study", "Sorcery", "{1}{U}", 2, "U", "Draw a card."))[0]
CYCLER = card_info(_card("Sea Beast", f"Creature {DASH} Beast", "{5}{U}", 6, "U", "Basic landcycling {2}",
                         ["Basic landcycling"], "5", "5"))[0]


class TraxosLandcyclingTests(unittest.TestCase):
    def test_without_many_finds_the_reduced_version(self):
        cheap = sim.reduced(TRAXOS, 2)
        self.assertEqual(sim.without_many([OPT, TRAXOS, CYCLER], [OPT, cheap]), [CYCLER])

    def test_cards_left_counts_the_reduced_version(self):
        left = sim.cards_left([OPT, TRAXOS, CYCLER], [OPT, sim.reduced(TRAXOS, 2)])
        self.assertEqual(sorted(c.name for c, k in left.items() if k > 0), ["Sea Beast"])
        self.assertFalse(any(k < 0 for k in left.values()))

    def test_goldfish_with_traxos_and_landcycling_runs(self):
        deck = [ISLAND] * 15 + [TRAXOS] * 8 + [OPT] * 9 + [CYCLER] * 8
        random.seed(1)
        r = sim.simulate(deck, 300, False, 3, 10, True, False, None, 11, 20, 6, True, 3, 6, False, True, 5, True)
        self.assertEqual(r["mulligan"]["deals"] - r["mulligan"]["lost"], 300)


if __name__ == "__main__":
    unittest.main()
