"""Englische Ausgabe der Bausteine (stats, html_base, landadvice, simulation) und der Konstanten-Woerterbuch-Eintraege."""
import types
import unittest

from components import coverage, graveyard, html_base, i18n, landadvice, mulligan, removal, simulation  # noqa: F401
from components.i18n_en.helpers import EN
from components.stats import compare_metrics
from tests.i18n_check import english, german_leftovers


def fake_deck():
    res = {"mulligan": {"on": True, "first_any": 3, "lost": 1, "deals": 20}, "cast": {1: 5, 2: 18, 3: 19},
           "color_avail": {"colors": ["R"], "t3_all": 15, "games": 20,
                           "checks": [{"color": "R", "k": 2, "turn": 3, "ok": 12, "measured": True}]},
           "any_screw": 0.1, "flood": 0.05,
           "samples": {"creatures": [1, 2, 3], "power": [2, 3, 4], "util": [0.5, 0.6], "jace": [1, 2]},
           "dmg": [5, 6, 7], "jace": {"on": True}}
    return {"results": {"On the Play": res}}


class TestHelpersEnglish(unittest.TestCase):
    def test_compare_metrics(self):
        args = types.SimpleNamespace(sims=20, turns=3, curve_runden=5, flood=7, max_runden=8, schaden=20)
        decks = [fake_deck(), fake_deck()]
        de = [r[0] for r in compare_metrics(decks, args, "On the Play")]
        with english():
            en = [r[0] for r in compare_metrics(decks, args, "On the Play")]
        self.assertEqual(len(de), len(en))
        self.assertIn("Zauber gespielt in Runde 1", de)
        self.assertEqual(german_leftovers("\n".join(en)), [])
        self.assertIn("≥ 2 Red sources by turn 3", en)
        self.assertEqual(de, [r[0] for r in compare_metrics(decks, args, "On the Play")])

    def test_html_base(self):
        de = html_base.svg_lines(["1", "2"], {"On the Play": [0.1, 0.2]}) + html_base.h_section("a", "T", "", "", "h")
        with english():
            en = html_base.svg_lines(["1", "2"], {"On the Play": [0.1, 0.2]}) + html_base.h_section("a", "T", "", "", "h")
        self.assertIn("Runde 1", de)
        self.assertEqual(german_leftovers(en), [])
        self.assertIn("How it works", en)

    def test_landadvice_warnings(self):
        pool = [{"name": "Bolt", "qty": 4, "cost": "{R}", "mv": 1, "land": False},
                {"name": "Guildgate", "qty": 20, "cost": "", "mv": 0, "land": True, "produces": ["R"]}]
        marks = [["core"] * 4, ["core"] * 20]
        de = landadvice.recommend(pool, marks)
        with english():
            en = landadvice.recommend(pool, marks)
        self.assertTrue(de["warnings"])
        self.assertEqual(len(de["warnings"]), len(en["warnings"]))
        self.assertEqual(german_leftovers(" ".join(en["warnings"])), [])
        self.assertEqual(de["warnings"], landadvice.recommend(pool, marks)["warnings"])

    def test_constants_have_english(self):
        keys = [coverage.STATUS_TEXT, *coverage.METRIC_ORDER, coverage.C_UNKNOWN, coverage.C_PREPARED,
                coverage.C_WALKER, coverage.C_LAND_COND, coverage.C_EMPOWER_X, mulligan.MULL_COLORS,
                mulligan.MULL_LANDS_HIGH, mulligan.MULL_LANDS_LOW]
        keys += [c for c, _m in coverage.KEYWORD_CATEGORY.values()] + [c for c, _m, _p in coverage.LINE_RULES]
        for k in keys:
            self.assertIn(k, EN)
        with english():
            self.assertEqual(german_leftovers(" ".join(i18n.t(k) for k in keys)), [])

    def test_runtime_error_message(self):
        with english():
            msg = i18n.t("Fast jede Starthand fuehrt zum Mulligan: nur {played} von {sims} Spielen wurden gespielt. "
                         "Das Deck ist mit diesen Mulligan-Regeln praktisch unspielbar.", played=1, sims=5)
        self.assertEqual(german_leftovers(msg), [])


if __name__ == "__main__":
    unittest.main()
