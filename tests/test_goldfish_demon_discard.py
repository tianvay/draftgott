"""Goldfish: Curse-Marred Demon wirft beim Betreten zufaellig eine Handkarte ab. Werden im selben Zug weitere Karten
gewirkt, loest der Demon zuletzt auf (sonst koennte er eine Karte abwerfen, die wir in diesem Zug noch wirken wollen,
z. B. eine teurere: die Zauber eines Zugs loesen nach Manawert auf). Wirft ein zweiter Demon eine geplante Karte ab,
wird sie nicht mehr gewirkt (frueher: Absturz in take_from)."""
import random
import unittest
from unittest import mock

from components import simulation as sim
from components.cards import card_info
from tests.fixtures_walkers import _card

DASH = "—"


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="R"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


MOUNTAIN = card_info(_card("Mountain", f"Basic Land {DASH} Mountain", text="({T}: Add {R}.)", produced=["R"]))[0]
DEMON = make("Curse-Marred Demon", f"Creature {DASH} Demon", "{2}{R}{R}", 4, "Flying, trample\nWhen this creature "
             "enters, search your library for a card, put it into your hand, shuffle, then discard a card at random.",
             "4", "4", ["Flying", "Trample"])
IMP = make("Test Imp", f"Creature {DASH} Imp", "{R}", 1, "", "1", "1")
FIVE = make("Test Giant", f"Creature {DASH} Giant", "{4}{R}", 5, "", "5", "5")
SIX = make("Test Dragon", f"Creature {DASH} Dragon", "{5}{R}", 6, "", "6", "6")


def run(order, horizon, sims=1):
    return sim.simulate(order, sims, False, horizon, horizon, True, False, None, 11, 20, 6, True, 3, 6, False, False,
                        5, True)


class ResolveOrderTests(unittest.TestCase):
    def test_demon_last(self):
        self.assertEqual(sim.resolve_order([IMP, DEMON, FIVE]), [IMP, FIVE, DEMON])

    def test_unchanged_without_demon(self):
        self.assertEqual(sim.resolve_order([IMP, FIVE, SIX]), [IMP, FIVE, SIX])

    def test_two_demons_keep_order(self):
        self.assertEqual(sim.resolve_order([DEMON, FIVE, DEMON]), [FIVE, DEMON, DEMON])


class DemonDiscardTests(unittest.TestCase):
    def test_many_games_without_crash(self):
        deck = [MOUNTAIN] * 18 + [DEMON] * 8 + [FIVE] * 6 + [SIX] * 4 + [IMP] * 4
        random.seed(1)
        r = run(deck, 12, sims=300)
        self.assertIn("curve", r)

    def test_spell_discarded_by_first_demon_is_not_cast(self):
        # Zwei Demons im selben Zug (mit normalen Landdrops kaum erreichbar, daher erzwungen): der erste wirft den
        # zweiten ab (erste Zauberkarte, nicht die gesuchte), der zweite wird nicht mehr gewirkt
        first_card = lambda seq: next((c for c in seq[:-1] if not c.is_land), seq[0])
        real = sim.best_cast_reduced

        def both_demons(spells, *args, **kwargs):
            best = real(spells, *args, **kwargs)
            demons = [c for c in spells if c is DEMON]
            return (best[0], demons[:2]) if len(demons) >= 2 else best

        order = [DEMON, DEMON] + [MOUNTAIN] * 5 + [MOUNTAIN, IMP, IMP] + [MOUNTAIN] * 20
        with mock.patch("components.mulligan.random.shuffle", lambda x: None), \
                mock.patch("components.simulation.random.choice", first_card), \
                mock.patch("components.simulation.best_cast_reduced", both_demons):
            r = run(order, 4)
        self.assertIn("curve", r)


if __name__ == "__main__":
    unittest.main()
