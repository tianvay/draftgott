"""Archetypen je Set: Daten, Set-Erkennung, Hauptfarben, Einblendung im Drafthelper und im Bericht."""
import json
import threading
import unittest
import urllib.request
from unittest import mock

import mtg_sim
from components import archetypes as arch
from components.report_cards import render_archetype_panel
from tests.fixtures import args_for
from components import drafthelper as dh
from tests.test_drafthelper import load
from tests.test_report_cards import DATA

DASH = "—"


class DataTests(unittest.TestCase):
    def test_trk_has_all_ten_color_pairs(self):
        trk = arch.for_set("trk")
        self.assertEqual(len(trk), 10)
        pairs = {frozenset(a["colors"]) for a in trk}
        self.assertEqual(len(pairs), 10)
        self.assertTrue(all(len(a["colors"]) == 2 and set(a["colors"]) <= set("WUBRG") for a in trk))

    def test_every_archetype_has_name_and_tips(self):
        for a in arch.for_set("trk"):
            self.assertTrue(a["name"], a)
            self.assertTrue(a["tips"] and all(isinstance(t, str) and t for t in a["tips"]), a)

    def test_trk_contents_are_translated(self):
        by = {a["colors"]: a for a in arch.for_set("trk")}
        self.assertEqual(by["WU"]["name"], "Spacecraft")
        self.assertIn("Payoffs", " ".join(by["WU"]["tips"]))
        self.assertIn("Vigilance", " ".join(by["WU"]["tips"]))
        self.assertEqual(by["RW"]["name"], "8 Power/Go wide")
        self.assertIn("8 Power", " ".join(by["RW"]["tips"]))
        self.assertIn("+1/+1 counters", " ".join(by["GW"]["tips"]))
        self.assertIn("2-Drops", " ".join(by["RW"]["tips"]))

    def test_set_code_is_case_insensitive_and_unknown_sets_have_none(self):
        self.assertEqual(arch.for_set("TRK"), arch.for_set("trk"))
        self.assertIsNone(arch.for_set("fra"))
        self.assertIsNone(arch.for_set(""))
        self.assertIsNone(arch.for_set(None))


class SetDetectionTests(unittest.TestCase):
    def test_most_common_set_by_copies(self):
        rows = [{"set": "trk", "qty": 1}, {"set": "fra", "qty": 1}, {"set": "trk", "qty": 2}, {"set": "", "qty": 9}]
        self.assertEqual(arch.main_set(rows), "trk")

    def test_copies_decide_over_rows(self):
        rows = [{"set": "trk", "qty": 1}, {"set": "trk", "qty": 1}, {"set": "fra", "qty": 3}]
        self.assertEqual(arch.main_set(rows), "fra")

    def test_no_set_gives_none(self):
        self.assertIsNone(arch.main_set([]))
        self.assertIsNone(arch.main_set([{"set": "", "qty": 3}]))

    def test_info_for_pool(self):
        info = arch.info([{"set": "TRK", "qty": 1, "land": False}])
        self.assertEqual(info["set"], "TRK")
        self.assertEqual(len(info["list"]), 10)

    def test_basics_and_lands_do_not_decide_the_set(self):
        rows = [{"set": "trk", "qty": 2, "land": False}, {"set": "fra", "qty": 5, "land": True}]
        self.assertEqual(arch.info(rows)["set"], "TRK")

    def test_info_without_archetypes_is_none(self):
        self.assertIsNone(arch.info([{"set": "fra", "qty": 3, "land": False}]))


class MainPairTests(unittest.TestCase):
    def test_two_most_common_colors_in_wubrg_order(self):
        self.assertEqual(arch.main_pair({"G": 5, "W": 7, "R": 1}), "GW")
        self.assertEqual(arch.main_pair({"U": 4, "W": 3}), "WU")

    def test_ties_follow_wubrg(self):
        self.assertEqual(arch.main_pair({"R": 3, "B": 3, "G": 3}), "BR")

    def test_fewer_than_two_colors_gives_none(self):
        self.assertIsNone(arch.main_pair({"W": 5}))
        self.assertIsNone(arch.main_pair({"W": 5, "U": 0}))
        self.assertIsNone(arch.main_pair({}))

    def test_pair_names_match_archetype_keys(self):
        keys = {a["colors"] for a in arch.for_set("trk")}
        for c1 in "WUBRG":
            for c2 in "WUBRG":
                if c1 != c2:
                    self.assertIn(arch.main_pair({c1: 2, c2: 1}), keys)


class DrafthelperTests(unittest.TestCase):
    """Drafthelper-Server mit dem Testpool (Set "tst")."""

    @classmethod
    def setUpClass(cls):
        cards, basics, sig = load()
        cls.app = {"pool": cards, "basics": basics, "signature": sig, "args": args_for(["--drafthelper"]),
                   "simulate": None, "save": None, "job": dh.Job(), "options": [1000], "file": "pool.txt"}
        cls.server = dh.LocalServer(("127.0.0.1", 0), dh.make_handler(cls.app))
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=10) as r:
            return r.read().decode("utf-8")

    def test_pool_api_without_archetypes(self):
        self.assertIsNone(json.loads(self.get("/api/pool"))["archetypes"])

    def test_pool_api_with_archetypes_of_the_set(self):
        fake = {"tst": [{"colors": "WB", "name": "Testgilde", "tips": ["Tipp"]}]}
        with mock.patch.dict(arch.ARCHETYPES, fake):
            data = json.loads(self.get("/api/pool"))
        self.assertEqual(data["archetypes"]["set"], "TST")
        self.assertEqual(data["archetypes"]["list"][0]["name"], "Testgilde")

    def test_page_has_archetype_box(self):
        self.assertIn('id="archetypes"', self.get("/"))


def _deck(names, set_code):
    data = {n: dict(c, set=set_code) for n, c in DATA.items()}
    entry = {"name": "Testdeck", "deck": dict(names)}
    return mtg_sim.build_deck(entry, data, args_for(["deck.txt"]))


class ReportTests(unittest.TestCase):
    NAMES = {"White Bear": 6, "Quick Spell": 4, "Black Bear": 3, "Jace Spell": 1, "Plains": 9, "Swamp": 7}

    def test_build_deck_carries_set(self):
        ctx = _deck(self.NAMES, "trk")
        self.assertEqual(ctx["info"]["White Bear"]["set"], "trk")

    def test_panel_shows_archetype_of_main_colors(self):
        html = render_archetype_panel(_deck(self.NAMES, "trk"))
        self.assertIn("TRK", html)
        self.assertIn("Artifact Creatures", html)  # Weiß/Schwarz
        self.assertIn("Weiß/Schwarz", html)
        main = html.split("Weitere Archetypen")[0]
        self.assertIn("Artifact Creatures", main)
        self.assertNotIn("Spacecraft", main)

    def test_panel_lists_other_archetypes_of_the_set(self):
        html = render_archetype_panel(_deck(self.NAMES, "trk"))
        self.assertIn("Spacecraft", render_archetype_panel(_deck({"White Bear": 5, "Jace Spell": 3, "Plains": 9},
                                                                  "trk")))
        self.assertIn("Weitere Archetypen", html)

    def test_no_panel_for_sets_without_archetypes(self):
        self.assertEqual(render_archetype_panel(_deck(self.NAMES, "fra")), "")

    def test_mono_colored_deck_has_no_main_archetype(self):
        html = render_archetype_panel(_deck({"White Bear": 8, "Quick Spell": 4, "Plains": 17}, "trk"))
        self.assertIn("kein Farbpaar", html)

    def test_panel_appears_in_the_full_report(self):
        data = {n: dict(c, set="trk") for n, c in DATA.items()}
        entries = [{"path": "", "name": "Test", "deck": dict(self.NAMES), "parts": [("Test", dict(self.NAMES))]}]
        with mock.patch.object(mtg_sim, "fetch_cards_cached", lambda names, refresh=False: data):
            html = mtg_sim.simulate_entries(entries, args_for(["deck.txt", "--sims", "50"]), progress=lambda m: None)
        self.assertIn("Archetyp", html)
        self.assertIn("Artifact Creatures", html)


if __name__ == "__main__":
    unittest.main()
