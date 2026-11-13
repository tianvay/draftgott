"""Englische Ausgabe von archetypes, synergy, signals, suggest, cardarchetypes, ratings."""
import unittest

from components import archetypes, signals, suggest, synergy
from components.i18n import en_table
from tests.i18n_check import english, german_leftovers


class TestDraftData(unittest.TestCase):
    def test_archetype_tips_english(self):
        raw = {k: [tip for a in v for tip in a["tips"]] for k, v in archetypes._RAW.items()}
        with english():
            for code in raw:
                for a in archetypes.for_set(code):
                    self.assertEqual(german_leftovers(" ".join(a["tips"])), [], a["name"])
            for code, lst in archetypes.ARCHETYPES.items():
                for a in lst:
                    self.assertEqual(german_leftovers(" ".join(a["tips"])), [])
            self.assertEqual(archetypes.pair_label("WU"), "White/Blue")
        for tips in raw.values():
            for tip in tips:
                self.assertIn(tip, en_table())

    def test_german_unchanged(self):
        self.assertEqual([a["tips"] for a in archetypes.for_set("trk")],
                         [a["tips"] for a in archetypes._RAW["trk"]])
        self.assertEqual(archetypes.pair_label("WU"), "Weiß/Blau")
        self.assertEqual(synergy.label("counters"), "+1/+1-Marken")
        self.assertEqual(synergy.label("type:elf"), "Kreaturtyp Elf")

    def test_synergy_labels(self):
        for key, (lab, _p) in synergy.RESOURCES.items():
            self.assertIn(lab, en_table(), key)
        with english():
            for key in synergy.RESOURCES:
                self.assertEqual(german_leftovers(synergy.label(key)), [], key)
            self.assertEqual(synergy.label("type:elf"), "Creature type Elf")

    def test_signals_notes(self):
        card = {1: {"name": "Foo", "colors": ["W"]}}
        history = [{"cards": list(range(1, 3)) * 1, "picked": [], "pick": 1}]
        with english():
            res = signals.analyze([], lambda g: card.get(g), {})
        self.assertEqual(res["notes"], [])
        with english():
            self.assertEqual(german_leftovers(signals.t("Pick {pick}: {card} kam zurück", pick=3, card="Foo")), [])
        self.assertTrue(history)

    def test_suggest_warnings(self):
        cards = [{"name": "A", "qty": 1, "colors": ["W"], "mv": 2}]
        with english():
            res = suggest.suggest(cards, [["core"]], {}, {"A": "filler"}, target=40)
            self.assertTrue(res["summary"]["warnings"])
            self.assertEqual(german_leftovers(" ".join(res["summary"]["warnings"])), [])
            res = suggest.propose(cards, [["core"]], {"A": "filler"}, "W", target=40)
            self.assertEqual(german_leftovers(" ".join(res["summary"]["warnings"] + res["summary"]["hints"])), [])
        de = suggest.suggest(cards, [["core"]], {}, {"A": "filler"}, target=40)
        self.assertIn("Nicht genug Filler", de["summary"]["warnings"][0])


if __name__ == "__main__":
    unittest.main()
