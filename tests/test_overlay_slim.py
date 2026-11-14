"""Schlankes Seitenfenster bei aktivem Karten-Overlay (Nutzer 14.11.2026): Ist das Karten-Overlay angeschaltet und
kalibriert, stehen Pack-Liste und Top-Pick-Zeilen schon auf den Karten und fallen im Seitenfenster weg. Farb-Signale,
Archetyp-Tracker und Tipps bleiben."""
import unittest

from components import overlay
from components import packoverlay as po
from tests.i18n_check import english, german_leftovers
from tests.test_i18n_overlay import ALLOW, DRAFT, GAME, INFO

CAL = {"x": 0.1, "y": 0.2, "w": 0.1, "h": 0.3, "dx": 0.12, "dy": 0.33, "cols": 7, "size": [1600, 900]}
ARENA = {"found": True, "minimized": False, "foreground": False, "origin": (0, 0), "size": (1600, 900)}
SNAP = dict(DRAFT, order=["Test Bolt"])


def text_of(rows):
    return "\n".join(r[0] for r in rows)


class CoversPackTests(unittest.TestCase):
    def test_on_and_calibrated(self):
        self.assertTrue(po.covers_pack(True, SNAP, CAL, ARENA))

    def test_foreground_does_not_matter(self):
        """Kein Hin- und Herspringen beim Alt-Tab: Vordergrund spielt keine Rolle."""
        self.assertTrue(po.covers_pack(True, SNAP, CAL, dict(ARENA, foreground=True)))
        self.assertTrue(po.covers_pack(True, SNAP, CAL, dict(ARENA, foreground=False)))

    def test_not_covered(self):
        cases = [
            (False, SNAP, CAL, ARENA),  # Schalter aus
            (True, SNAP, None, ARENA),  # nicht kalibriert
            (True, SNAP, CAL, {"found": False}),  # Arena fehlt
            (True, SNAP, CAL, dict(ARENA, minimized=True)),
            (True, SNAP, CAL, dict(ARENA, size=(1600, 1200))),  # anders proportioniert: neu kalibrieren
            (True, dict(SNAP, order=[]), CAL, ARENA),  # Reihenfolge unbekannt: keine Karten im Overlay
            (True, dict(SNAP, status="waiting"), CAL, ARENA),
            (True, {"game": GAME}, CAL, ARENA),
            (True, {"complete": True, "deckinfo": INFO}, CAL, ARENA),
            (True, None, CAL, ARENA),
        ]
        for case in cases:
            self.assertFalse(po.covers_pack(*case), msg=case[1:])


class SlimRowsTests(unittest.TestCase):
    def test_default_unchanged(self):
        self.assertEqual(overlay.rows_for(SNAP), overlay.rows_for(SNAP, slim=False))
        self.assertEqual(overlay.mini_rows(SNAP), overlay.mini_rows(SNAP, slim=False))

    def test_pack_and_top_pick_gone(self):
        rows = overlay.rows_for(SNAP, slim=True)
        self.assertNotIn("hint", [tag for _, tag in rows])
        self.assertNotIn("Syn+", text_of(rows))
        self.assertNotIn("60 % (10 G.)", text_of(rows))
        self.assertIn("60 % (10 G.)", text_of(overlay.rows_for(SNAP)))
        self.assertIn(overlay.t("Bewertungen stehen auf den Karten (Karten-Overlay)"), text_of(rows))

    def test_signals_tracker_tips_stay(self):
        rows = overlay.rows_for(SNAP, slim=True)
        text = text_of(rows)
        self.assertTrue(rows[0][0].startswith("Pick 5"))
        self.assertIn("Signale (Draft)", text)
        self.assertIn("Boros: 2 Picks · im Pack: Test Bolt", text)  # Archetyp-Tracker vollstaendig
        self.assertIn("Tipps zu Boros", text)
        self.assertIn("• Tip", text)
        self.assertIn("Picks 4: ", text)
        self.assertIn("Boros 3.5", text)

    def test_curve_warning_stays(self):
        w = {"cards": 9, "avg_mv": 3.6, "heavy": 7, "cheap": 4, "reasons": ["avg"]}
        self.assertIn("warn", [tag for _, tag in overlay.rows_for(dict(SNAP, curve_warning=w), slim=True)])
        self.assertIn("warn", [tag for _, tag in overlay.mini_rows(dict(SNAP, curve_warning=w), slim=True)])

    def test_waiting_and_other_states_unchanged(self):
        for snap in (dict(SNAP, status="waiting", pack=[]), {"game": GAME}, None,
                     {"complete": True, "deckinfo": INFO, "detect": {"main": "WR"}}):
            self.assertEqual(overlay.rows_for(snap, slim=True), overlay.rows_for(snap), msg=snap)
            self.assertEqual(overlay.mini_rows(snap, slim=True), overlay.mini_rows(snap), msg=snap)

    def test_mini_without_best_card(self):
        rows = overlay.mini_rows(SNAP, slim=True)
        self.assertTrue(rows[0][0].startswith("Pick 5"))
        self.assertNotIn("Test Bolt", text_of(rows))
        self.assertIn("Test Bolt", text_of(overlay.mini_rows(SNAP)))

    def test_english(self):
        with english():
            out = text_of(overlay.rows_for(SNAP, slim=True) + overlay.mini_rows(SNAP, slim=True))
        self.assertEqual(german_leftovers(out, allow=ALLOW + ["Boros"]), [])
        self.assertIn("card overlay", out)


if __name__ == "__main__":
    unittest.main()
