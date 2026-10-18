"""Draw-Zauber mit fester Zahl: Erkennung im Kartentext, Modell-Abdeckung, Ziehen in der Simulation und Bericht."""
import random
import unittest
from unittest import mock

import mtg_sim
from components import simulation as sim
from components.cards import card_info
from components.coverage import M_FLOW, M_LETHAL, analyze_card
from tests.fixtures_walkers import CARDS as W_CARDS, DATA as W_DATA, _card

DASH = "—"


def raw(text, type_line="Sorcery", cost="{W}", cmc=1, name="Test Draw", power=None, toughness=None):
    return _card(name, type_line, cost, cmc, "W", text, power=power, toughness=toughness)


def draws(text, **kw):
    return card_info(raw(text, **kw))[0].draws


DRAW_DATA = {c["name"]: c for c in [
    raw("Draw two cards.", name="Test Draw Two"),
    raw("Draw a card.", name="Test Draw One"),
    raw("When this creature enters, draw a card.", type_line=f"Creature {DASH} Test", cost="{1}{W}", cmc=2,
        name="Test Draw Creature", power="1", toughness="1"),
    raw("Draw three cards.", cost="{W}", name="Test Draw Three"),
]}
DRAW = {name: card_info(c)[0] for name, c in DRAW_DATA.items()}
PLAINS, BEAR, BIG = W_CARDS["Plains"], W_CARDS["Test Bear"], W_CARDS["Test Big"]
TWO, ONE, CREATURE = DRAW["Test Draw Two"], DRAW["Test Draw One"], DRAW["Test Draw Creature"]
W = ("W",)


class DrawParsingTests(unittest.TestCase):
    def test_draw_two_cards(self):
        self.assertEqual(draws("Draw two cards."), 2)

    def test_draw_a_card(self):
        self.assertEqual(draws("Draw a card."), 1)

    def test_digits_and_number_words(self):
        self.assertEqual(draws("Draw three cards."), 3)
        self.assertEqual(draws("Draw 4 cards."), 4)

    def test_draw_next_to_damage(self):
        self.assertEqual(draws("Draw two cards. Test Draw deals 2 damage to each player."), 2)

    def test_twinned_vision_is_always_cast_from_hand(self):
        self.assertEqual(draws("Draw a card. If this spell wasn't cast from your hand, draw two cards instead.\n"
                               "Flashback—{1}{U}, Discard a card."), 1)

    def test_draw_on_its_own_line_next_to_empower(self):
        card = card_info(raw("Empower Jace 6.\nDraw a card.", cost="{3}{U}", cmc=4))[0]
        self.assertEqual(card.draws, 1)
        self.assertEqual(sum(e[2] for e in card.empower), 6)

    def test_creature_that_draws_when_it_enters(self):
        self.assertEqual(draws("When this creature enters, draw a card.", type_line=f"Creature {DASH} Test",
                               power="1", toughness="1"), 1)
        self.assertEqual(draws("When Test Draw enters, draw two cards.", type_line=f"Creature {DASH} Test",
                               power="1", toughness="1"), 2)

    def test_not_modelled(self):
        for text, type_line in (
                ("Choose one —\n• Destroy target creature.\n• Draw a card.", "Sorcery"),
                ("Draw a card, then discard a card.", "Sorcery"),
                ("Draw two cards, then discard a card.", "Instant"),
                ("Draw X cards, where X is the number of creatures you control.", "Sorcery"),
                ("You may discard a card. If you do, draw a card.", "Sorcery"),
                ("Target player draws two cards.", "Sorcery"),
                ("Whenever you gain life, draw a card.", f"Creature {DASH} Test"),
                ("{T}, Discard a card: Draw a card.", f"Creature {DASH} Test"),
                ("When this creature dies, draw a card.", f"Creature {DASH} Test"),
                ("When this creature enters, you may draw a card. If you do, discard a card.", f"Creature {DASH} Test"),
                ("Draw a card.", f"Creature {DASH} Test"),  # nur Zauber ziehen ohne Ausloeser
        ):
            with self.subTest(text=text):
                self.assertEqual(draws(text, type_line=type_line, power="1", toughness="1"), 0)

    def test_tag_in_the_card_list(self):
        self.assertIn("[Zieht 2]", card_info(raw("Draw two cards."))[1])


class DrawCoverageTests(unittest.TestCase):
    def cats(self, text, type_line="Sorcery"):
        return {(c, m) for c, m, _l in analyze_card(raw(text, type_line=type_line, power="1", toughness="1"))}

    def test_modelled_draw_is_not_flagged(self):
        self.assertEqual(self.cats("Draw two cards."), set())
        self.assertEqual(self.cats("Draw a card."), set())
        self.assertEqual(self.cats("When this creature enters, draw a card.", f"Creature {DASH} Test"), set())

    def test_the_rest_of_the_line_is_still_checked(self):
        self.assertEqual(self.cats("Draw two cards. Exile target card from an opponent's graveyard."),
                         {("Interaktion mit dem Gegner", "keine (Gegner ist nicht Teil des Modells)")})

    def test_twinned_vision_only_flashback_remains(self):
        found = self.cats("Draw a card. If this spell wasn't cast from your hand, draw two cards instead.\n"
                          "Flashback—{1}{U}, Discard a card.")
        self.assertEqual(found, set())  # Ziehen, alternative Zahl und Flashback mit Abwerfen sind modelliert

    def test_unmodelled_draws_stay_flagged(self):
        for text, type_line in (("Whenever you gain life, draw a card.", f"Creature {DASH} Test"),
                                ("Whenever an opponent draws a card, draw a card.", f"Creature {DASH} Test")):
            with self.subTest(text=text):
                self.assertIn(("Kartenfluss", M_FLOW), self.cats(text, type_line))
        for text in ("Choose one —\n• Destroy target creature.\n• Draw a card.", "Draw a card, then discard a card."):
            self.assertEqual(self.cats(text, "Sorcery"), set(), text)  # modaler Zauber und Loot sind modelliert


class ResolveDrawsTests(unittest.TestCase):
    """resolve_draws: nach dem Zaubern ziehen, Landdrop nachholen, mit dem uebrigen Mana weiter zaubern."""

    def resolve(self, hand, library, chosen, battlefield, land_played, has_creature=False):
        pool = [c.land_colors for c in battlefield]
        return sim.resolve_draws(hand, library, chosen, pool, battlefield, land_played, has_creature, True,
                                 False, False)

    def test_drawn_spell_is_cast_with_the_leftover_mana(self):
        hand, library, bf = [TWO], [BEAR, BIG, PLAINS], [PLAINS, PLAINS]
        r = self.resolve(hand, library, [TWO], bf, PLAINS)
        self.assertEqual(r["chosen"], [TWO, BEAR])
        self.assertEqual(r["drawn"], 2)
        self.assertEqual(r["used"], 1)
        self.assertEqual(sorted(c.name for c in hand), ["Test Bear", "Test Big", "Test Draw Two"])  # Karten auf der Hand
        self.assertEqual(library, [PLAINS])

    def test_drawn_land_is_played_when_the_land_drop_is_free(self):
        hand, library, bf = [TWO], [PLAINS, BEAR], [PLAINS]
        r = self.resolve(hand, library, [TWO], bf, None)
        self.assertIs(r["land"], PLAINS)
        self.assertFalse(r["tapped"])
        self.assertEqual(len(bf), 2)
        self.assertEqual(r["chosen"], [TWO, BEAR])  # das neue Land bezahlt den Bear
        self.assertEqual(r["used"], 2)
        self.assertNotIn(PLAINS, hand)

    def test_no_second_land_when_one_was_already_played(self):
        hand, library, bf = [TWO], [PLAINS, PLAINS], [PLAINS, PLAINS]
        r = self.resolve(hand, library, [TWO], bf, PLAINS)
        self.assertIsNone(r["land"])
        self.assertEqual(len(bf), 2)
        self.assertEqual(sum(c.is_land for c in hand), 2)

    def test_chained_draw_spells(self):
        hand, library, bf = [ONE], [ONE, BEAR], [PLAINS, PLAINS, PLAINS]
        r = self.resolve(hand, library, [ONE], bf, PLAINS)
        self.assertEqual(r["chosen"], [ONE, ONE, BEAR])
        self.assertEqual(r["drawn"], 2)

    def test_drawn_card_stays_in_hand_without_mana(self):
        hand, library, bf = [TWO], [BIG, BEAR], [PLAINS]
        r = self.resolve(hand, library, [TWO], bf, PLAINS)
        self.assertEqual(r["chosen"], [TWO])
        self.assertEqual(r["used"], 0)
        self.assertIn(BIG, hand)
        self.assertIn(BEAR, hand)

    def test_empty_library_does_not_crash(self):
        hand, library, bf = [TWO], [BEAR], [PLAINS, PLAINS]
        r = self.resolve(hand, library, [TWO], bf, PLAINS)
        self.assertEqual(r["drawn"], 1)
        self.assertEqual(library, [])

    def test_without_draw_spells_nothing_changes(self):
        hand, library, bf = [BEAR], [BEAR], [PLAINS]
        r = self.resolve(hand, library, [BEAR], bf, PLAINS)
        self.assertEqual((r["chosen"], r["drawn"], r["used"]), ([BEAR], 0, 0))
        self.assertEqual(library, [BEAR])


def run(deck, sims=200, seed=11):
    cards = [c for name, n in deck.items() for c in [{**W_CARDS, **DRAW}[name]] * n]
    random.seed(seed)
    return sim.simulate(cards, sims, False, 3, 8, True, False, None, 11, 20, 6, True, 3, 6, False, True, 5, True)


class DrawSimulationTests(unittest.TestCase):
    def test_draw_spells_draw_more_cards(self):
        res = run({"Plains": 17, "Test Bear": 13, "Test Draw Two": 10})
        dr = res["draws"]
        self.assertTrue(dr["on"])
        self.assertGreater(dr["cards"], 1.0)  # zusaetzliche Karten pro Spiel
        self.assertGreater(dr["games"], 0.5)  # Anteil der Spiele mit mindestens einer gezogenen Karte
        self.assertGreaterEqual(dr["cards"], dr["used"])

    def test_more_lands_drawn_than_with_the_same_deck_without_draw(self):
        with_draw = run({"Plains": 17, "Test Bear": 13, "Test Draw Two": 10})
        without = run({"Plains": 17, "Test Bear": 23})
        self.assertGreater(with_draw["lands_drawn"], without["lands_drawn"] + 0.5)

    def test_off_without_draw_spells(self):
        res = run({"Plains": 17, "Test Bear": 23})
        self.assertEqual(res["draws"], {"on": False, "cards": 0.0, "games": 0.0, "used": 0.0})

    def test_running_out_of_cards_is_handled(self):
        res = run({"Plains": 17, "Test Draw Three": 23}, sims=50)
        self.assertGreater(res["draws"]["cards"], 5)


def build(deck):
    data = {**W_DATA, **DRAW_DATA}
    entries = [{"path": "", "name": "A", "deck": dict(deck), "parts": [("A", dict(deck))]}]
    from tests.fixtures import args_for
    with mock.patch.object(mtg_sim, "fetch_cards_cached", lambda n, refresh=False: data):
        return mtg_sim.simulate_entries(entries, args_for(["deck.txt", "--sims", "100"]), progress=lambda m: None)


class DrawReportTests(unittest.TestCase):
    def test_section_with_draw_spells(self):
        html = build({"Plains": 17, "Test Bear": 13, "Test Draw Two": 10})
        report, help_view = html[:html.index('id="view-help"')], html[html.index('id="view-help"'):]
        self.assertIn('id="ziehen"', report)
        self.assertIn("Draw-Zauber", report)
        self.assertIn("Ø zusätzlich gezogen", report)
        self.assertIn("Test Draw Two", report)
        self.assertIn('id="hiw-ziehen"', help_view)

    def test_no_section_without_draw_spells(self):
        html = build({"Plains": 17, "Test Bear": 23})
        self.assertNotIn('id="ziehen"', html)
        self.assertNotIn('id="hiw-ziehen"', html)


if __name__ == "__main__":
    unittest.main()
