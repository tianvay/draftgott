import json
import random
import shutil
import subprocess
import unittest
from unittest import mock

import mtg_sim
from components import drafthelper as dh
from components.cardkinds import card_colors, color_curve, empower_points
from components.report_cards import render_color_curves, render_type_table, render_types_compare
from tests.fixtures import args_for

DASH = "—"


def raw(name, type_line, cost="", colors=(), text="", keywords=(), power=None, toughness=None, cmc=0, produced=None):
    d = {"name": name, "type_line": type_line, "mana_cost": cost, "cmc": float(cmc), "colors": list(colors),
         "oracle_text": text, "keywords": list(keywords), "layout": "normal", "power": power, "toughness": toughness}
    if produced:
        d["produced_mana"] = list(produced)
    return d


DATA = {c["name"]: c for c in [
    raw("Plains", f"Basic Land {DASH} Plains", text="({T}: Add {W}.)", produced=["W"]),
    raw("Swamp", f"Basic Land {DASH} Swamp", text="({T}: Add {B}.)", produced=["B"]),
    raw("Odd Land", "Land", text="{T}: Add {W} or {B}.", produced=["W", "B"]),
    raw("White Bear", f"Creature {DASH} Bear", "{1}{W}", "W", power="2", toughness="2", cmc=2),
    raw("Black Bear", f"Creature {DASH} Bear", "{1}{B}", "B", power="2", toughness="2", cmc=2),
    raw("Gold Knight", f"Creature {DASH} Knight", "{W}{B}", "WB", power="2", toughness="2", cmc=2),
    raw("Gray Golem", f"Artifact Creature {DASH} Golem", "{3}", "", power="3", toughness="3", cmc=3),
    raw("Quick Spell", "Instant", "{W}", "W", text="Draw a card.", cmc=1),
    raw("Slow Spell", "Sorcery", "{2}{B}", "B", text="Surveil 2.", cmc=3),
    raw("Shiny Rock", "Artifact", "{2}", "", cmc=2),
    raw("Old Aura", f"Enchantment {DASH} Aura", "{1}{W}", "W", text="Enchant creature", keywords=["Enchant"], cmc=2),
    raw("Test Walker", f"Legendary Planeswalker {DASH} Ajani", "{2}{W}", "W", cmc=3),
    raw("Jace Spell", "Sorcery", "{U}", "U", text="Empower Jace 3.", keywords=["Empower Jace"], cmc=1),
]}

DECK = {"Plains": 6, "Swamp": 4, "Odd Land": 1, "White Bear": 3, "Black Bear": 2, "Gold Knight": 2, "Gray Golem": 1,
        "Quick Spell": 2, "Slow Spell": 1, "Shiny Rock": 1, "Old Aura": 1, "Test Walker": 1, "Jace Spell": 2}


def deck(names=None):
    names = dict(names or DECK)
    entry = {"name": "Test", "deck": names, "parts": [("Test", dict(names))]}
    return mtg_sim.build_deck(entry, DATA, args_for(["deck.txt"]))


def item(colors, mv=2, land=False, qty=1):
    return {"colors": colors, "mv": mv, "land": land, "qty": qty}


class CardColorsTests(unittest.TestCase):
    def test_top_level_colors(self):
        self.assertEqual(card_colors({"colors": ["W", "U"]}), ["W", "U"])

    def test_front_face_colors_for_double_faced_cards(self):
        self.assertEqual(card_colors({"card_faces": [{"colors": ["R"]}, {"colors": ["G"]}]}), ["R"])

    def test_colorless(self):
        self.assertEqual(card_colors({}), [])


class EmpowerPointsTests(unittest.TestCase):
    def test_only_immediate_effects_count(self):
        effects = ((0, "spell", 2, "", (), False, False, False), (0, "trigger", 5, "attack", (), False, False, False),
                   (0, "etb", 1, "", (), False, False, False), (0, "etb", 9, "", (), False, True, False))
        self.assertEqual(empower_points(effects), 3)


class ColorCurveTests(unittest.TestCase):
    def test_mono_cards_by_color_and_bucket(self):
        r = color_curve([item(["W"], 1, qty=2), item(["B"], 3)], "stacked", 8)
        self.assertEqual((r["buckets"][1]["W"], r["buckets"][3]["B"], r["total"]), (2, 1, 3))

    def test_quantity_is_used(self):
        r = color_curve([item(["R"], 2, qty=4)], "stacked", 8)
        self.assertEqual((r["buckets"][2]["R"], r["total"]), (4, 4))

    def test_lands_are_excluded(self):
        self.assertEqual(color_curve([item([], 0, land=True, qty=5)], "stacked", 8)["total"], 0)

    def test_colorless(self):
        self.assertEqual(color_curve([item([], 3)], "stacked", 8)["buckets"][3]["C"], 1)

    def test_stacked_counts_multicolor_once_in_its_own_segment(self):
        r = color_curve([item(["G", "W"], 4)], "stacked", 8)
        self.assertEqual((r["buckets"][4]["M"], r["buckets"][4]["G"], r["buckets"][4]["W"], r["total"]), (1, 0, 0, 1))

    def test_percolor_counts_multicolor_in_every_color(self):
        r = color_curve([item(["G", "W"], 4)], "percolor", 8)
        self.assertEqual((r["buckets"][4]["G"], r["buckets"][4]["W"], r["total"]), (1, 1, 1))
        self.assertNotIn("M", r["keys"])

    def test_pairs_in_wubrg_order(self):
        r = color_curve([item(["G", "W"]), item(["W", "G"], qty=2), item(["U", "B", "R"])], "stacked", 8)
        self.assertEqual(r["pairs"], {"W/G": 3, "U/B/R": 1})
        self.assertEqual(r["multi"], 4)

    def test_cap_and_rounding(self):
        r = color_curve([item(["R"], 12), item(["R"], 7), item(["R"], 2.4)], "stacked", 8)
        self.assertEqual((r["buckets"][7]["R"], r["buckets"][2]["R"]), (2, 1))

    def test_max_per_mode(self):
        copies = [item(["G", "W"], 2), item(["G"], 2), item(["W"], 2)]
        self.assertEqual(color_curve(copies, "stacked", 8)["max"], 3)
        self.assertEqual(color_curve(copies, "percolor", 8)["max"], 2)

    def test_empty(self):
        r = color_curve([], "stacked", 8)
        self.assertEqual((r["total"], r["multi"], r["max"]), (0, 0, 1))


@unittest.skipUnless(shutil.which("node"), "Node.js nicht installiert")
class ParityWithThePageTests(unittest.TestCase):
    """Die Zaehllogik steht in Python (Bericht) und in JavaScript (Seite): beide muessen dasselbe liefern."""

    def js(self, copies, mode):
        page = dh.PAGE
        code = page[page.index("// BEGIN colorCurve"):page.index("// END colorCurve")]
        script = code + "\nconst i = JSON.parse(process.argv[1]);\n" \
                        "console.log(JSON.stringify(colorCurve(i.c, 'splash', i.m)));\n"
        out = subprocess.run(["node", "-e", script, json.dumps({"c": copies, "m": mode})],
                             capture_output=True, text=True, timeout=30)
        if out.returncode != 0:
            raise RuntimeError(out.stderr)
        return json.loads(out.stdout)

    def test_random_inputs_give_identical_results(self):
        rng = random.Random(4)
        pool = ["W", "U", "B", "R", "G"]
        for mode in ("stacked", "percolor"):
            copies = [{"colors": rng.sample(pool, rng.choice([0, 0, 1, 1, 1, 2, 3])), "mv": rng.choice([0, 1, 2, 2.4, 3, 5,
                      6, 8]), "land": rng.random() < 0.2, "mark": "core"} for _ in range(150)]
            py = color_curve([dict(c, qty=1) for c in copies], mode, 7)
            js = self.js(copies, mode)
            for key in ("buckets", "keys", "pairs", "total", "multi", "colorless", "max"):
                self.assertEqual(py[key], js[key], (mode, key))


class DeckInfoTests(unittest.TestCase):
    def test_build_deck_carries_kinds_flow_colors_and_empower(self):
        info = deck()["info"]
        self.assertEqual(info["White Bear"]["kinds"], ["creature"])
        self.assertEqual(info["Gold Knight"]["colors"], ["W", "B"])
        self.assertEqual(info["Quick Spell"]["flow"], ["draw"])
        self.assertEqual(info["Slow Spell"]["flow"], ["surveil"])
        self.assertTrue(info["Jace Spell"]["empower"])
        self.assertEqual(info["Jace Spell"]["points"], 3)
        self.assertEqual(info["Odd Land"]["kinds"], ["land", "nonbasic_land"])


class RenderColorCurvesTests(unittest.TestCase):
    def setUp(self):
        self.html = render_color_curves(deck())

    def test_both_views_with_charts_and_legend(self):
        for text in ("Mana-Kurve nach Farben", "Mehrfarbige gesondert", "Je Farbe", "Weiß", "Schwarz", "Mehrfarbig",
                     "Farblos"):
            self.assertIn(text, self.html)
        self.assertEqual(self.html.count("<svg"), 2)

    def test_explanations_and_color_pairs(self):
        self.assertIn("Jede Karte steht genau einmal", self.html)
        self.assertIn("zählt bei jeder ihrer Farben", self.html)
        self.assertIn("Weiß/Schwarz 2", self.html)

    def test_totals(self):
        # Nichtland: 3+2+2+1 Kreaturen, 2+1 Zauber, Rock, Aura, Walker, 2 Jace-Zauber = 16... ohne Laender
        self.assertIn("16 Nichtland-Karten", self.html)
        self.assertIn("davon 2 mehrfarbig", self.html)

    def test_multicolor_segment_uses_the_gold_color(self):
        self.assertIn("#d9a400", self.html)

    def test_no_pairs_text_without_multicolor_cards(self):
        html = render_color_curves(deck({"Plains": 10, "White Bear": 5}))
        self.assertNotIn("Mehrfarbig:", html)


class RenderTypeTableTests(unittest.TestCase):
    def setUp(self):
        self.html = render_type_table(deck())

    def cell(self, label):
        """Wert (erste Zahlenspalte) der Tabellenzeile mit diesem Label."""
        import re
        m = re.search(re.escape(label) + r"</td>\s*<td[^>]*>(.*?)</td>", self.html, re.S)
        self.assertIsNotNone(m, f"Zeile fehlt: {label}")
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()

    def test_rows_and_counts(self):
        expected = {"Karten gesamt": "27", "Kreaturen": "8", "Instants": "2", "Sorceries": "3",
                    "Artefakte (ohne Kreaturen)": "1", "Verzauberungen": "1", "Planeswalker": "1",
                    "Länder gesamt": "11", "davon Nicht-Standard-Länder": "1"}
        for label, value in expected.items():
            self.assertEqual(self.cell(label), value, label)

    def test_empower_and_points(self):
        self.assertEqual(self.cell("Empower Jace (Karten)"), "2")
        self.assertEqual(self.cell("Σ Loyalty beim Wirken/Betreten"), "6")

    def test_card_flow_kinds_appear_only_if_present(self):
        self.assertEqual(self.cell("Kartenfluss (Karten)"), "3")
        self.assertIn("Ziehen (Draw)", self.html)
        self.assertIn("Surveil", self.html)
        self.assertNotIn("Scry", self.html)
        self.assertNotIn("Explore", self.html)
        self.assertNotIn("Mill", self.html)

    def test_no_flow_block_without_flow_cards(self):
        html = render_type_table(deck({"Plains": 10, "White Bear": 5}))
        self.assertNotIn("Kartenfluss", html)


class RenderTypesCompareTests(unittest.TestCase):
    def test_one_column_per_deck(self):
        a, b = deck(), deck({"Plains": 10, "White Bear": 5, "Quick Spell": 3})
        b["name"] = "Variante B"
        html = render_types_compare([a, b])
        self.assertIn("Test", html)
        self.assertIn("Variante B", html)
        self.assertIn("Kreaturen", html)

    def test_differences_are_marked(self):
        a = deck({"Plains": 10, "White Bear": 5})
        b = deck({"Plains": 10, "White Bear": 4})
        b["name"] = "B"
        self.assertIn('class="diff"', render_types_compare([a, b]))


class FullReportTests(unittest.TestCase):
    def test_report_contains_the_new_sections(self):
        names = dict(DECK)
        entries = [{"path": "", "name": "A", "deck": dict(names), "parts": [("A", dict(names))]}]
        with mock.patch.object(mtg_sim, "fetch_cards_cached", lambda n, refresh=False: DATA):
            html = mtg_sim.simulate_entries(entries, args_for(["deck.txt"]), progress=lambda m: None)
        self.assertIn("Mana-Kurve nach Farben", html)
        self.assertIn("Kartentypen", html)
        self.assertIn("Kartenfluss (Karten)", html)


if __name__ == "__main__":
    unittest.main()
