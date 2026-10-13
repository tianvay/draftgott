import json
import shutil
import subprocess
import unittest

from components import drafthelper as dh


def region(name):
    page = dh.PAGE
    return page[page.index(f"// BEGIN {name}"):page.index(f"// END {name}")]


def run(fn, arg):
    script = region("colorCurve") + f"\nconst i = JSON.parse(process.argv[1]);\nconsole.log(JSON.stringify({fn}));\n"
    out = subprocess.run(["node", "-e", script, json.dumps(arg)], capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise RuntimeError(out.stderr)
    return json.loads(out.stdout)


def card(colors, mv=2, mark="core", land=False):
    return {"colors": colors, "mv": mv, "mark": mark, "land": land}


def curve(copies, variant="splash", mode="stacked"):
    return run("colorCurve(i.copies, i.variant, i.mode)", {"copies": copies, "variant": variant, "mode": mode})


@unittest.skipUnless(shutil.which("node"), "Node.js nicht installiert")
class ColorCurveTests(unittest.TestCase):
    def test_mono_colored_cards_land_in_their_color_and_bucket(self):
        r = curve([card(["W"], 1), card(["W"], 1), card(["B"], 3)])
        self.assertEqual(r["buckets"][1]["W"], 2)
        self.assertEqual(r["buckets"][3]["B"], 1)
        self.assertEqual(r["total"], 3)

    def test_colorless_cards_have_their_own_segment(self):
        r = curve([card([], 4)])
        self.assertEqual(r["buckets"][4]["C"], 1)

    def test_lands_are_excluded(self):
        r = curve([card([], 0, land=True), card(["W"], 1)])
        self.assertEqual(r["total"], 1)

    def test_stacked_mode_counts_a_multicolor_card_once_in_its_own_segment(self):
        r = curve([card(["G", "W"], 4)], mode="stacked")
        self.assertEqual(r["buckets"][4]["M"], 1)
        self.assertEqual((r["buckets"][4]["G"], r["buckets"][4]["W"]), (0, 0))
        self.assertEqual(r["total"], 1)

    def test_percolor_mode_counts_a_multicolor_card_in_each_of_its_colors(self):
        r = curve([card(["G", "W"], 4)], mode="percolor")
        self.assertEqual((r["buckets"][4]["G"], r["buckets"][4]["W"]), (1, 1))
        self.assertNotIn("M", r["keys"])
        self.assertEqual(r["total"], 1)   # die Kartenzahl bleibt 1

    def test_color_pairs_are_listed_in_wubrg_order_in_both_modes(self):
        copies = [card(["G", "W"]), card(["W", "G"]), card(["B", "W"]), card(["U", "B", "R"])]
        for mode in ("stacked", "percolor"):
            r = curve(copies, mode=mode)
            self.assertEqual(r["pairs"], {"W/G": 2, "W/B": 1, "U/B/R": 1})

    def test_mana_value_is_rounded_and_capped_at_six_plus(self):
        r = curve([card(["R"], 9), card(["R"], 6), card(["R"], 0), card(["R"], 2.4)])
        self.assertEqual(r["buckets"][6]["R"], 2)
        self.assertEqual(r["buckets"][0]["R"], 1)
        self.assertEqual(r["buckets"][2]["R"], 1)

    def test_variant_selection(self):
        copies = [card(["W"], 1, "core"), card(["U"], 1, "splash"), card(["R"], 1, "nosplash"),
                  card(["B"], 1, "off")]
        s = curve(copies, "splash")
        self.assertEqual((s["buckets"][1]["W"], s["buckets"][1]["U"], s["buckets"][1]["R"], s["buckets"][1]["B"]),
                         (1, 1, 0, 0))
        n = curve(copies, "nosplash")
        self.assertEqual((n["buckets"][1]["W"], n["buckets"][1]["U"], n["buckets"][1]["R"]), (1, 0, 1))

    def test_max_is_the_tallest_bucket_in_the_chosen_mode(self):
        copies = [card(["G", "W"], 2), card(["G"], 2), card(["W"], 2)]
        self.assertEqual(curve(copies, mode="stacked")["max"], 3)    # 1 + 1 + 1 gestapelt
        self.assertEqual(curve(copies, mode="percolor")["max"], 2)   # G=2, W=2 nebeneinander

    def test_empty_input(self):
        r = curve([])
        self.assertEqual(r["total"], 0)
        self.assertEqual(r["multi"], 0)
        self.assertEqual(r["max"], 1)

    def test_totals_for_the_note(self):
        r = curve([card(["W"]), card(["G", "W"]), card([]), card([], mv=1)])
        self.assertEqual((r["total"], r["multi"], r["colorless"]), (4, 1, 2))


@unittest.skipUnless(shutil.which("node"), "Node.js nicht installiert")
class ColorCurveStateMappingTests(unittest.TestCase):
    def test_tiles_are_mapped_with_the_fields_the_curve_needs(self):
        tiles = [{"mark": "splash", "card": {"colors": ["U"], "mv": 3, "land": False}},
                 {"mark": "core", "card": {}}]
        out = run("colorCopiesOf(i)", tiles)
        self.assertEqual(out, [{"colors": ["U"], "mv": 3, "mark": "splash", "land": False},
                               {"colors": [], "mv": 0, "mark": "core", "land": False}])


if __name__ == "__main__":
    unittest.main()
