"""Warnung im Live-Draft, wenn die Mana-Kurve der Picks zu hoch ist (Nutzer 14.11.2026), und Fenster des Overlays,
die sich an ihren Inhalt anpassen, damit keine Zeilen abgeschnitten werden."""
import unittest

from components import livedraft as ld
from components import overlay
from tests.i18n_check import english, german_leftovers
from tests.test_livedraft import LiveTestCase, notify, pick


def spell(mv, colors=("R",)):
    return {"name": f"S{mv}", "mv": mv, "land": False, "colors": list(colors)}


def land():
    return {"name": "Mountain", "mv": 0, "land": True, "colors": []}


GOOD = [spell(1), spell(2), spell(2), spell(2), spell(3), spell(3), spell(3), spell(4), spell(4), spell(5)]
HEAVY = [spell(2), spell(3), spell(4), spell(4), spell(5), spell(5), spell(5), spell(6), spell(6), spell(7)]


class CurveWarningTests(unittest.TestCase):
    def test_good_curve_gives_no_warning(self):
        self.assertIsNone(ld.curve_warning(GOOD, "R"))

    def test_too_few_spells_gives_no_warning(self):
        self.assertIsNone(ld.curve_warning(HEAVY[:ld.CURVE_MIN_SPELLS - 1], "R"))
        self.assertIsNotNone(ld.curve_warning(HEAVY[-ld.CURVE_MIN_SPELLS:], "R"))

    def test_heavy_curve_warns_with_reasons(self):
        w = ld.curve_warning(HEAVY, "R")
        self.assertEqual(w["cards"], 10)
        self.assertEqual(w["avg_mv"], 4.7)
        self.assertEqual(w["heavy"], 6)
        self.assertEqual(w["cheap"], 1)
        self.assertEqual(w["curve"], [0, 1, 1, 2, 3, 3])
        self.assertEqual(w["reasons"], ["avg", "heavy", "cheap"])
        self.assertEqual(w["heavy23"], 14)  # 6 von 10 auf 23 Zauber hochgerechnet
        self.assertEqual(w["cheap23"], 2)

    def test_lands_and_other_colors_do_not_count(self):
        off = [spell(7, "U")] * 10
        self.assertIsNone(ld.curve_warning(GOOD + off + [land()] * 5, "R"))
        # ohne Archetyp zaehlen alle Zauber
        self.assertIsNotNone(ld.curve_warning(GOOD + off, None))

    def test_colorless_cards_count_for_the_archetype(self):
        w = ld.curve_warning(GOOD + [spell(6, ())] * 6, "RW")
        self.assertIn("heavy", w["reasons"])

    def test_single_reasons(self):
        many_threes = [spell(1)] + [spell(3)] * 6 + [spell(4)] * 3
        self.assertEqual(ld.curve_warning(many_threes, "R")["reasons"], ["cheap"])
        top_heavy = [spell(1)] * 4 + [spell(2)] * 2 + [spell(6)] * 4
        self.assertEqual(ld.curve_warning(top_heavy, "R")["reasons"], ["heavy"])


class SnapshotTests(LiveTestCase):
    def test_snapshot_has_curve_warning_key(self):
        self.write(notify(1, [101, 102]), pick([101]))
        self.live.step()
        snap = self.live.snapshot({}, {}, None)
        self.assertIn("curve_warning", snap)
        self.assertIsNone(snap["curve_warning"])  # ein Pick: zu frueh fuer eine Warnung


WARN = {"cards": 10, "avg_mv": 4.7, "heavy": 6, "cheap": 1, "curve": [0, 1, 1, 2, 3, 3],
        "reasons": ["avg", "heavy", "cheap"], "heavy23": 14, "cheap23": 2}
SNAP = {"status": "pack", "pick": 11, "detect": {"main": "R", "scores": []}, "curve_warning": WARN,
        "archetypes": [{"colors": "R", "name": "Rot"}],
        "pack": [{"name": "Test Bolt", "colors": ["R"], "rating": "", "level": "", "arch": []}]}


class OverlayRowTests(unittest.TestCase):
    def test_warning_rows_in_the_side_window(self):
        rows = overlay.rows_for(SNAP)
        self.assertEqual(rows[1][1], "warn")  # gleich unter der Kopfzeile
        text = "\n".join(r[0] for r in rows)
        self.assertIn("Mana-Kurve zu hoch", text)
        self.assertIn("Ø Manawert 4,7", text)
        self.assertIn("6 Karten mit 5+ Mana", text)
        self.assertIn("Nur 1 Karte bis 2 Mana", text)
        self.assertIn("günstige Karten", text)

    def test_only_given_reasons_are_listed(self):
        rows = overlay.curve_rows(dict(WARN, reasons=["heavy"]), "Rot")
        text = "\n".join(r[0] for r in rows)
        self.assertIn("5+ Mana", text)
        self.assertNotIn("Ø Manawert", text)
        self.assertNotIn("bis 2 Mana", text)

    def test_no_rows_without_warning(self):
        self.assertEqual(overlay.curve_rows(None, "Rot"), [])
        rows = overlay.rows_for(dict(SNAP, curve_warning=None))
        self.assertNotIn("warn", [tag for _, tag in rows])

    def test_warning_also_while_waiting_and_in_the_mini_box(self):
        self.assertIn("warn", [tag for _, tag in overlay.rows_for(dict(SNAP, status="waiting", pack=[]))])
        mini = overlay.mini_rows(SNAP)
        self.assertIn(("⚠ Kurve zu hoch", "warn"), mini)

    def test_not_after_the_draft_or_in_a_game(self):
        info = {"cards": 40, "lands": 17, "spells": 23, "avg_mv": 3.0, "curve": [1, 6, 6, 5, 3, 2], "creatures": 15,
                "removal": 3, "removal_points": 4, "flow": 2, "colors": {"R": 23}, "top": [], "record": None}
        done = dict(SNAP, complete=True, deckinfo=info)
        self.assertNotIn("warn", [tag for _, tag in overlay.rows_for(done)])
        game = dict(SNAP, game={"active": True, "library": 30, "groups": []})
        self.assertNotIn("warn", [tag for _, tag in overlay.rows_for(game)])

    def test_english(self):
        with english():
            text = "\n".join(r[0] for r in overlay.rows_for(SNAP) + overlay.mini_rows(SNAP))
        self.assertEqual(german_leftovers(text, allow=["Rot", "Test Bolt"]), [])
        self.assertIn("Mana curve too high", text)


class FitGeometryTests(unittest.TestCase):
    def test_window_grows_to_its_content(self):
        self.assertEqual(overlay.fit_geometry(700, y=80, screen_height=1080), (700, 80))

    def test_window_shrinks_but_not_below_the_minimum(self):
        self.assertEqual(overlay.fit_geometry(300, y=80, screen_height=1080), (300, 80))
        self.assertEqual(overlay.fit_geometry(20, y=80, screen_height=1080), (overlay.FIT_MIN_HEIGHT, 80))

    def test_window_moves_up_before_it_leaves_the_screen(self):
        h, y = overlay.fit_geometry(900, y=400, screen_height=1080)
        self.assertEqual(h, 900)
        self.assertEqual(y + h, 1080 - overlay.FIT_MARGIN)

    def test_window_never_taller_than_the_screen(self):
        h, y = overlay.fit_geometry(5000, y=400, screen_height=1080)
        self.assertEqual(y, 0)
        self.assertEqual(h, 1080 - overlay.FIT_MARGIN)


class HelpTests(unittest.TestCase):
    def test_help_page_mentions_curve_warning(self):
        from components.howitworks import render_help_page
        self.assertIn("Mana-Kurve zu hoch", render_help_page())


if __name__ == "__main__":
    unittest.main()
