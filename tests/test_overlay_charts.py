"""Grafiken im Seitenfenster: Mana-Kurve als Balken und Farben als geteilter Balken in der Deck-Uebersicht."""
import unittest

from components import overlay


class ParseTests(unittest.TestCase):
    def test_curve_bars_from_row_text(self):
        self.assertEqual(overlay.curve_bars("Kurve ≤1:0 2:9 3:4 4:5 5:6 6+:1"),
                         [("≤1", 0), ("2", 9), ("3", 4), ("4", 5), ("5", 6), ("6+", 1)])

    def test_color_parts_from_row_text(self):
        self.assertEqual(overlay.color_parts("Farben W 14 · R 9"), [("W", 14), ("R", 9)])
        self.assertEqual(overlay.color_parts("Farben W 5 · R 3 · B 1"), [("W", 5), ("R", 3), ("B", 1)])


class LayoutTests(unittest.TestCase):
    def test_curve_layout_heights_follow_counts(self):
        bars = overlay.curve_layout([("≤1", 0), ("2", 9), ("3", 3)], width=300, height=80)
        self.assertEqual([b["label"] for b in bars], ["≤1", "2", "3"])
        self.assertEqual([b["n"] for b in bars], [0, 9, 3])
        tallest = bars[1]["y1"] - bars[1]["y0"]
        self.assertGreater(tallest, 0)
        self.assertEqual(bars[0]["y1"] - bars[0]["y0"], 0)  # leerer Platz ohne Balken
        self.assertAlmostEqual((bars[2]["y1"] - bars[2]["y0"]) * 3, tallest, delta=1)
        self.assertTrue(all(0 <= b["x0"] < b["x1"] <= 300 for b in bars))
        self.assertTrue(bars[0]["x1"] <= bars[1]["x0"])  # nebeneinander, ohne Ueberlappung
        self.assertEqual(len({b["y1"] for b in bars}), 1)  # gemeinsame Grundlinie

    def test_curve_layout_all_zero(self):
        bars = overlay.curve_layout([("≤1", 0), ("2", 0)], width=200, height=60)
        self.assertTrue(all(b["y0"] == b["y1"] for b in bars))

    def test_color_layout_splits_width_by_share(self):
        segs = overlay.color_layout([("W", 14), ("R", 7)], width=300)
        self.assertEqual([s["color"] for s in segs], ["W", "R"])
        self.assertEqual(segs[0]["x0"], 0)
        self.assertEqual(segs[-1]["x1"], 300)
        self.assertEqual(segs[0]["x1"], segs[1]["x0"])
        self.assertAlmostEqual(segs[0]["x1"], 200, delta=1)
        self.assertTrue(all(s["fill"].startswith("#") for s in segs))
        self.assertEqual(overlay.color_layout([], width=300), [])


class DeckRowTagTests(unittest.TestCase):
    def test_deck_rows_mark_curve_and_colors_as_charts(self):
        info = {"cards": 40, "lands": 17, "spells": 23, "avg_mv": 3.52, "curve": [0, 9, 4, 5, 6, 1],
                "creatures": 17, "removal": 1, "removal_points": 0.2, "flow": 4, "colors": {"W": 14, "R": 9},
                "top": ["Deep Space 9"], "record": None, "source": "arena"}
        rows = overlay.deck_rows({"deckinfo": info, "detect": {"main": "RW"}, "archetypes": []})
        tags = {line.split(" ")[0]: tag for line, tag in rows}
        self.assertEqual(tags["Kurve"], "curve")
        self.assertEqual(tags["Farben"], "colors")


if __name__ == "__main__":
    unittest.main()
