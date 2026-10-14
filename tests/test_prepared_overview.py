"""Prepared in den Uebersichten: Seitenleiste des Drafthelpers (typeCounts) und Kartentypen im Bericht."""
import shutil
import unittest

from components.report_cards import render_type_table, type_counts
from tests.test_prepared import P_DATA
from tests.test_type_overview import load_cards, run_js


class PoolFlagTests(unittest.TestCase):
    def test_pool_cards_carry_the_prepared_flag(self):
        from unittest import mock
        from tests import test_type_overview as tto
        with mock.patch.dict(tto.DATA, P_DATA):
            cards = load_cards(["Test Scholar // Test Study", "Plain"])
        self.assertTrue(cards["Test Scholar // Test Study"]["prepared"])
        self.assertFalse(cards["Plain"]["prepared"])


def copy(kinds, mark="core", prepared=False):
    return {"kinds": kinds, "mark": mark, "empower": False, "points": 0, "flow": [], "prepared": prepared}


@unittest.skipUnless(shutil.which("node"), "Node.js nicht installiert")
class PageCountsTests(unittest.TestCase):
    def test_prepared_cards_per_variant(self):
        r = run_js([copy(["creature"], prepared=True), copy(["creature"], "splash", prepared=True),
                    copy(["creature"])], [])
        self.assertEqual((r["splash"]["prepared"], r["nosplash"]["prepared"]), (2, 1))

    def test_same_count_as_the_report(self):
        copies = [copy(["creature"], prepared=True), copy(["creature"], prepared=True), copy(["sorcery"])]
        js = run_js(copies, [])["splash"]["prepared"]
        ctx = {"rows": [("A", 2, None, ""), ("B", 1, None, "")],
               "info": {"A": {"kinds": ["creature"], "prepared": True}, "B": {"kinds": ["sorcery"]}}}
        self.assertEqual(type_counts(ctx)["prepared"], js)


@unittest.skipUnless(shutil.which("node"), "Node.js nicht installiert")
class PageStateTests(unittest.TestCase):
    def test_prepared_flag_reaches_the_counting_function(self):
        from tests.test_card_flow import run_copies_of
        out = run_copies_of([{"mark": "core", "card": {"kinds": ["creature"], "prepared": True}},
                             {"mark": "core", "card": {"kinds": ["creature"]}}])
        self.assertTrue(out[0]["prepared"])
        self.assertNotIn("prepared", out[1])
        self.assertEqual(run_js(out, [])["splash"]["prepared"], 1)


class ReportTypeTableTests(unittest.TestCase):
    def ctx(self, prepared):
        return {"rows": [("A", 3, None, "")], "info": {"A": {"kinds": ["creature"], "prepared": prepared}}}

    def test_row_with_prepared_cards(self):
        html = render_type_table(self.ctx(True))
        self.assertIn("Prepared (Karten)", html)
        self.assertIn("<td>3</td>", html)

    def test_no_row_without_prepared_cards(self):
        self.assertNotIn("Prepared", render_type_table(self.ctx(False)))


if __name__ == "__main__":
    unittest.main()
