"""Land-Empfehlung: Deckfarben, passende Nicht-Standardlaender, Hypergeometrie, Verteilung und Gruppen."""
import io
import json
import threading
import unittest
import urllib.error
import urllib.request
from math import comb
from unittest import mock

from components import drafthelper as dh
from components import landadvice as la
from components.mana import cost_alternatives
from tests.fixtures import args_for
from tests.test_drafthelper import load


def spell(name, cost, mv, qty=1):
    return {"name": name, "qty": qty, "cost": cost, "mv": mv, "land": False, "colors": [], "found": True}


def land(name, produces, qty=1):
    return {"name": name, "qty": qty, "cost": "", "mv": 0, "land": True, "produces": list(produces), "found": True}


def item(cost, mv, qty=1):
    return {"needs": la.needs_of_alts(cost_alternatives(cost)), "mv": mv, "qty": qty, "name": cost}


class DeckColorTests(unittest.TestCase):
    def test_a_single_symbol_is_enough(self):
        self.assertEqual(la.colors_of_alts(cost_alternatives("{3}{R}")), {"R"})

    def test_hybrid_counts_for_both_colors(self):
        self.assertEqual(la.colors_of_alts(cost_alternatives("{1}{G/U}")), {"G", "U"})

    def test_needs_ignore_hybrid_and_count_double_pips(self):
        self.assertEqual(la.needs_of_alts(cost_alternatives("{1}{G/U}")), {})
        self.assertEqual(la.needs_of_alts(cost_alternatives("{1}{R}{R}{G}")), {"R": 2, "G": 1})
        self.assertEqual(la.needs_of_alts(cost_alternatives("{R/P}")), {})


class LandFitsTests(unittest.TestCase):
    """Beispiele des Nutzers: ein R/G-Land passt nur, wenn R und G im Deck vorkommen."""

    def test_rg_land_in_rgw_deck(self):
        self.assertTrue(la.land_fits(("G", "R"), {"R", "G", "W"}))

    def test_rg_land_without_red(self):
        self.assertFalse(la.land_fits(("G", "R"), {"G", "W"}))

    def test_rg_land_without_green(self):
        self.assertFalse(la.land_fits(("G", "R"), {"R", "W"}))

    def test_rg_land_without_both(self):
        self.assertFalse(la.land_fits(("G", "R"), {"W", "U"}))

    def test_land_without_colors_never_fits(self):
        self.assertFalse(la.land_fits(("C",), {"W"}))
        self.assertFalse(la.land_fits((), {"W"}))

    def test_one_color_land(self):
        self.assertTrue(la.land_fits(("R",), {"R", "G"}))


class HypergeometricTests(unittest.TestCase):
    def test_matches_the_formula(self):
        expected = 1 - comb(23, 7) / comb(40, 7)  # mindestens 1 von 17 Laendern in 7 Karten
        self.assertAlmostEqual(la.p_at_least(40, 17, 7, 1), expected)
        expected2 = 1 - (comb(32, 9) + 8 * comb(32, 8)) / comb(40, 9)  # mindestens 2 von 8 in 9 Karten
        self.assertAlmostEqual(la.p_at_least(40, 8, 9, 2), expected2)

    def test_edge_cases(self):
        self.assertEqual(la.p_at_least(40, 0, 9, 1), 0.0)
        self.assertEqual(la.p_at_least(40, 5, 9, 0), 1.0)
        self.assertEqual(la.p_at_least(40, 40, 9, 1), 1.0)

    def test_on_time_uses_mana_value_as_turn_on_the_play(self):
        self.assertEqual(la.seen_by_turn(3), 9)
        self.assertEqual(la.seen_by_turn(0), 7)
        p = la.on_time(item("{1}{R}{G}", 3), {"R": 8, "G": 9}, 40)
        self.assertAlmostEqual(p, la.p_at_least(40, 8, 9, 1) * la.p_at_least(40, 9, 9, 1))


class DistributeTests(unittest.TestCase):
    def test_mono_color_gets_everything(self):
        self.assertEqual(la.distribute([item("{1}{B}", 2, 23)], {}, 17, 40, {"B"}), {"B": 17})

    def test_heavier_color_gets_more(self):
        items = [item("{1}{B}", 2, 15), item("{1}{G}", 2, 6)]
        a = la.distribute(items, {}, 17, 40, {"B", "G"})
        self.assertEqual(sum(a.values()), 17)
        self.assertGreater(a["B"], a["G"])
        self.assertGreaterEqual(a["G"], 3)

    def test_splash_color_gets_at_least_three_sources(self):
        items = [item("{1}{B}", 2, 11), item("{1}{G}", 2, 10), item("{3}{R}", 4, 1)]
        self.assertEqual(la.distribute(items, {}, 17, 40, {"B", "G", "R"})["R"], 3)

    def test_nonbasic_sources_count_towards_the_minimum(self):
        items = [item("{1}{B}", 2, 11), item("{1}{G}", 2, 10), item("{3}{R}", 4, 1)]
        a = la.distribute(items, {"R": 1, "G": 1}, 16, 40, {"B", "G", "R"})
        self.assertEqual(a["R"], 2)
        self.assertEqual(sum(a.values()), 16)

    def test_hybrid_only_color_gets_no_basics(self):
        items = [item("{1}{B}", 2, 20), item("{G/U}", 1, 1)]
        self.assertEqual(la.distribute(items, {}, 17, 40, {"B", "G", "U"}), {"B": 17})


class RecommendTests(unittest.TestCase):
    """recommend(pool, marks, target): Nicht-Standardlaender zuordnen, Standardlaender je Gruppe."""

    def setUp(self):
        self.pool = [
            spell("Black", "{1}{B}", 2, 11), spell("Green", "{1}{G}", 2, 10), spell("Red Splash", "{3}{R}", 4, 2),
            spell("Green Extra", "{2}{G}", 3, 2),
            land("BG Land", "BG"), land("RG Land", "GR"), land("WR Land", "RW", 2), land("Colorless", "C"),
        ]

    def marks(self, **by_name):
        return [[by_name.get(c["name"], "off")] * c["qty"] for c in self.pool]

    def basics_total(self, r, group):
        return {n: v[group] for n, v in r["basics"].items() if v[group]}

    def test_core_only(self):
        r = la.recommend(self.pool, self.marks(Black="core", Green="core"), 40)
        self.assertEqual([v["key"] for v in r["variants"]], ["core"])
        groups = {l["name"]: l["group"] for l in r["lands"]}
        self.assertEqual(groups, {"BG Land": "core", "RG Land": "off", "WR Land": "off", "Colorless": "off"})
        v = r["variants"][0]
        self.assertEqual((v["spells"], v["lands"], v["nonbasic"]), (21, 17, 1))  # 40 - 21 = 19 -> Faustregel max 17
        basics = self.basics_total(r, "core")
        self.assertEqual(sum(basics.values()), 16)
        self.assertEqual(set(basics), {"Swamp", "Forest"})
        self.assertTrue(any("38" in w for w in r["warnings"]))  # 21 + 17 = 38 Karten statt 40

    def test_land_marks_are_set_and_spell_marks_stay(self):
        marks = self.marks(Black="core", Green="core", **{"RG Land": "core", "Colorless": "core"})
        r = la.recommend(self.pool, marks, 40)
        names = [c["name"] for c in self.pool]
        self.assertEqual(r["marks"][names.index("BG Land")], ["core"])
        self.assertEqual(r["marks"][names.index("RG Land")], ["off"])
        self.assertEqual(r["marks"][names.index("Colorless")], ["off"])
        self.assertEqual(r["marks"][names.index("WR Land")], ["off", "off"])
        self.assertEqual(r["marks"][names.index("Black")], ["core"] * 11)

    def test_splash_and_nosplash(self):
        marks = self.marks(Black="core", Green="core", **{"Red Splash": "splash", "Green Extra": "nosplash"})
        r = la.recommend(self.pool, marks, 40)
        self.assertEqual([v["key"] for v in r["variants"]], ["splash", "nosplash"])
        groups = {l["name"]: l["group"] for l in r["lands"]}
        self.assertEqual(groups["BG Land"], "core")       # passt zu B/G/R und B/G
        self.assertEqual(groups["RG Land"], "splash")     # passt nur zur Splash-Variante B/G/R
        self.assertEqual(groups["WR Land"], "off")
        by = {v["key"]: v for v in r["variants"]}
        for key in ("splash", "nosplash"):
            v = by[key]
            basics = sum(b["core"] + b[key] for b in r["basics"].values())
            self.assertEqual(basics + v["nonbasic"], v["lands"], key)
            self.assertEqual(v["spells"] + v["lands"], 40, key)
        self.assertEqual(by["splash"]["sources"]["R"], 3)  # RG Land + 2 Mountain
        self.assertEqual(r["basics"]["Mountain"], {"core": 0, "splash": 2, "nosplash": 0})
        # Core enthaelt nur, was beide Varianten brauchen
        for name, b in r["basics"].items():
            self.assertTrue(b["splash"] == 0 or b["nosplash"] == 0, name)

    def test_report_per_color(self):
        r = la.recommend(self.pool, self.marks(Black="core", Green="core"), 40)
        rep = r["variants"][0]["report"]
        self.assertEqual(set(rep), {"B", "G"})
        self.assertEqual(rep["B"]["cards"], 11)
        self.assertTrue(0 < rep["B"]["avg"] < 1)
        self.assertIn(rep["B"]["worst"]["name"], ("Black",))

    def test_land_count_follows_the_target(self):
        pool = [spell("Black", "{1}{B}", 2, 25)]
        r = la.recommend(pool, [["core"] * 25], 40)
        self.assertEqual(r["variants"][0]["lands"], 15)
        r = la.recommend([spell("Black", "{1}{B}", 2, 23)], [["core"] * 23], 40)
        self.assertEqual(r["variants"][0]["lands"], 17)
        self.assertEqual(r["warnings"], [])

    def test_no_colored_spells(self):
        r = la.recommend([spell("Artifact", "{3}", 3, 23)], [["core"] * 23], 40)
        self.assertEqual(sum(b["core"] for b in r["basics"].values()), 0)
        self.assertTrue(r["warnings"])


class LandsApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cards, basics, sig = load()
        cls.app = {"pool": cards, "basics": basics, "signature": sig, "args": args_for(["--drafthelper"]),
                   "simulate": lambda entries, args, progress: "", "save": lambda html, args: None,
                   "job": dh.Job(), "options": [1000], "file": "pool.txt"}
        cls._stderr = mock.patch("sys.stderr", io.StringIO())
        cls._stderr.start()
        cls.server = dh.LocalServer(("127.0.0.1", 0), dh.make_handler(cls.app))
        cls.app["server"] = cls.server
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls._stderr.stop()

    def post(self, body):
        req = urllib.request.Request(self.base + "/api/lands", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_recommendation_for_the_marked_cards(self):
        pool = self.app["pool"]
        marks = [["core" if not c["land"] else "off"] * c["qty"] for c in pool]
        status, answer = self.post({"marks": marks, "basics": {}, "cats": {}, "target": 40})
        self.assertEqual(status, 200)
        self.assertTrue(answer["ok"])
        self.assertEqual(len(answer["marks"]), len(pool))
        self.assertEqual(set(answer["basics"]), set(dh.BASIC_LANDS))
        self.assertGreater(sum(b["core"] for b in answer["basics"].values()), 0)
        self.assertEqual(answer["variants"][0]["key"], "core")

    def test_invalid_target(self):
        pool = self.app["pool"]
        status, answer = self.post({"marks": [["off"] * c["qty"] for c in pool], "target": 5})
        self.assertEqual(status, 400)
        self.assertFalse(answer["ok"])

    def test_pool_cards_carry_their_mana_colors(self):
        self.assertTrue(all("produces" in c for c in self.app["pool"] if c["land"]))


class ReportOnTimeTests(unittest.TestCase):
    def test_color_table_shows_on_time_chance(self):
        import mtg_sim
        from tests.fixtures import CARDS
        entries = [{"path": "", "name": "A", "deck": {"Plains": 9, "Mountain": 8, "Test Bear": 12, "Test Hasty": 11},
                    "parts": []}]
        with mock.patch.object(mtg_sim, "fetch_cards_cached", lambda n, refresh=False: CARDS):
            html = mtg_sim.simulate_entries(entries, args_for(["deck.txt", "--sims", "100"]), progress=lambda m: None)
        report = html[:html.index('id="view-help"')]
        self.assertIn("Ø pünktlich", report)
        self.assertIn("Am knappsten", report)
        p = la.on_time(item("{W}", 1), {"W": 9}, 40)
        self.assertIn(f"{p:.0%}", report)
        self.assertIn("Ø pünktlich", html[html.index('id="view-help"'):])  # Erklaerung


if __name__ == "__main__":
    unittest.main()
