"""Zwei Saeulen ueber Arena beim Draften (Nutzer 15.11.2026, Entwurf B): links die Zahlen des Decks (Kreaturen und
Removal gross, Kurve, Farben), in der Luecke zwischen Pack und Deckliste alles zum Pick (Warnung, Top-Pick, Archetypen,
Signale, Tipp). Daten, Lage, Sichtbarkeit und Englisch."""
import unittest

from components import arenapanels as ap
from components import livedraft as ld
from components import overlay
from tests.i18n_check import english, german_leftovers

ARCH = {"cards": 7, "creatures": 4, "removal": 2, "removal_points": 2.5, "flow": 1, "spacecraft": 1,
        "curve": [1, 2, 3, 1, 0, 0], "colors": {"W": 4, "R": 3}}
INFO = {"cards": 9, "creatures": 5, "removal": 3, "removal_points": 3.5, "flow": 2, "spacecraft": 0,
        "curve": [1, 3, 3, 1, 1, 0], "colors": {"W": 4, "R": 3, "U": 2}, "arch": ARCH}
DRAFT = {"status": "pack", "pick": 10, "detect": {"main": "WR", "manual": False, "scores": [
             {"colors": "WR", "name": "Boros", "score": 3.5}, {"colors": "UR", "name": "Izzet", "score": 2},
             {"colors": "WB", "name": "Orzhov", "score": 1.5}, {"colors": "UG", "name": "Simic", "score": 0}]},
         "archetypes": [{"colors": "WR", "name": "Boros", "tips": ["Tipp eins", "Tipp zwei"]}],
         "draftinfo": INFO,
         "hints": [{"name": "Test Bolt", "rating": "mustplay", "best": "WR", "best_name": "Boros", "state": "in"}],
         "signals": {"format": "Draft", "colors": {"W": {"level": "open", "score": 2},
                                                   "R": {"level": "maybe", "score": 1},
                                                   "U": {"level": None, "score": 0}}, "notes": []},
         "pack": [{"name": "Test Bolt", "colors": ["R"], "rating": "mustplay", "level": "arch", "arch": ["WR"]}],
         "order": [1]}
WARN = {"cards": 10, "avg_mv": 3.6, "heavy": 6, "cheap": 1, "reasons": ["avg"], "heavy23": 14, "cheap23": 2}
ARENA = {"found": True, "minimized": False, "foreground": True, "origin": (100, 50), "size": (2000, 1125)}


def tiles(snap):
    return {tile["key"]: tile for tile in ap.deck_column(snap)["tiles"]}


class DeckColumnTests(unittest.TestCase):
    def test_counts_all_picks_without_sideboard(self):
        # Nutzer 15.11.2026 (Freigabe, vorher nur Archetyp-Farben: 4 Kreaturen, 2,5 P.): ein Splash zaehlt mit, was
        # nicht ins Deck soll, liegt im Sideboard (draftinfo zaehlt schon ohne Sideboard)
        col = ap.deck_column(DRAFT)
        cr, rm = tiles(DRAFT)["creatures"], tiles(DRAFT)["removal"]
        self.assertEqual((cr["value"], cr["target"], cr["big"]), (5, ap.CREATURE_TARGET, "5"))
        self.assertEqual((rm["value"], rm["target"], rm["big"]), (3.5, 4.0, "3,5"))
        self.assertIn("Boros", col["title"])
        self.assertEqual(col["curve"], [1, 3, 3, 1, 1, 0])
        self.assertEqual(col["colors"], [("W", 4), ("R", 3), ("U", 2)])
        self.assertIn(("Kartenfluss", "2"), col["more"])
        self.assertIn("9", tiles(DRAFT)["creatures"]["sub"])

    def test_without_archetype_counts_all_picks(self):
        snap = dict(DRAFT, detect={"main": None, "scores": []})
        self.assertEqual(tiles(snap)["creatures"]["value"], 5)
        self.assertEqual(tiles(snap)["removal"]["value"], 3.5)
        self.assertEqual(ap.deck_column(snap)["colors"], [("W", 4), ("R", 3), ("U", 2)])
        self.assertNotIn(("Spacecraft", "0"), ap.deck_column(snap)["more"])  # nur, wenn es welche gibt

    def test_levels(self):
        self.assertEqual(tiles(DRAFT)["creatures"]["level"], "progress")
        self.assertEqual(tiles(DRAFT)["removal"]["level"], "yellow")  # 3,5 P.: ueber der gelben Schwelle 2,5
        rich = dict(DRAFT, draftinfo=dict(INFO, creatures=15, removal_points=4.0))
        self.assertEqual(tiles(rich)["creatures"]["level"], "green")
        self.assertEqual(tiles(rich)["removal"]["level"], "green")
        poor = dict(DRAFT, draftinfo=dict(INFO, removal_points=1.0))
        self.assertEqual(tiles(poor)["removal"]["level"], "progress")

    def test_bar_fraction_is_capped(self):
        self.assertEqual(ap.bar_fraction(20, 15), 1.0)
        self.assertEqual(ap.bar_fraction(0, 15), 0.0)
        self.assertAlmostEqual(ap.bar_fraction(3, 6), 0.5)
        self.assertEqual(ap.bar_fraction(3, 0), 0.0)

    def test_nothing_before_the_first_pick(self):
        self.assertIsNone(ap.deck_column({"status": "pack", "pick": 1, "pack": []}))
        self.assertIsNone(ap.deck_column(None))


class PickColumnTests(unittest.TestCase):
    def test_contents(self):
        col = ap.pick_column(dict(DRAFT, curve_warning=WARN))
        self.assertEqual(col["head"], "Pick 10")
        self.assertIn("Kurve zu hoch", col["warn"][0])
        self.assertTrue(any("günstige" in x for x in col["warn"]))
        self.assertEqual(col["hints"], ["Test Bolt"])
        self.assertEqual(col["archs"], [("Boros", "3,5", True), ("Izzet", "2", False), ("Orzhov", "1,5", False)])
        self.assertEqual(col["signals"], [("W offen +2", "open"), ("R evtl. offen +1", "maybe")])
        self.assertEqual(col["dots"], [("W", "open", "+2"), ("R", "maybe", "+1")])  # oben als Manakreise
        self.assertEqual(col["tips"], ["Tipp eins", "Tipp zwei"])

    def test_manual_archetype_and_switch(self):
        snap = dict(DRAFT, detect=dict(DRAFT["detect"], manual=True,
                                       switch={"name": "Izzet", "colors": "UR", "score": 4, "plan_score": 2}),
                    side={"Test Bear": 1})
        col = ap.pick_column(snap)
        self.assertIn("eigene Wahl", col["arch_note"])
        self.assertIn("↔ Izzet", col["switch"])
        self.assertIn("Sideboard 1", col["switch"])

    def test_no_hints_while_waiting_or_with_card_overlay(self):
        self.assertEqual(ap.pick_column(dict(DRAFT, status="waiting"))["hints"], [])
        self.assertEqual(ap.pick_column(DRAFT, slim=True)["hints"], [])  # stehen schon lila auf den Karten
        self.assertIn("nächste Pack", ap.pick_column(dict(DRAFT, status="waiting", pack=[]))["state"])

    def test_empty_parts(self):
        col = ap.pick_column({"status": "pack", "pick": 2, "detect": {"main": None, "scores": []}, "pack": []})
        self.assertEqual((col["warn"], col["hints"], col["archs"], col["signals"], col["tips"]), ([], [], [], [], []))
        self.assertIn("offen", col["arch_note"])


class VisibilityTests(unittest.TestCase):
    def test_only_while_drafting(self):
        self.assertTrue(ap.active(True, DRAFT, ARENA))
        self.assertTrue(ap.active(True, dict(DRAFT, status="waiting"), ARENA))
        self.assertFalse(ap.active(False, DRAFT, ARENA))
        self.assertFalse(ap.active(True, dict(DRAFT, complete=True), ARENA))
        self.assertFalse(ap.active(True, dict(DRAFT, game={"active": True}), ARENA))
        self.assertFalse(ap.active(True, {"status": "idle"}, ARENA))
        self.assertFalse(ap.active(True, None, ARENA))

    def test_needs_arena(self):
        self.assertFalse(ap.active(True, DRAFT, {"found": False}))
        self.assertFalse(ap.active(True, DRAFT, dict(ARENA, minimized=True)))
        self.assertTrue(ap.active(True, DRAFT, dict(ARENA, foreground=False)))  # Seitenfenster springt nicht
        self.assertFalse(ap.should_draw(True, DRAFT, dict(ARENA, foreground=False)))
        self.assertTrue(ap.should_draw(True, DRAFT, ARENA))

    def test_side_window_steps_aside(self):
        on = {"main": True, "tricks": True}
        self.assertNotIn("main", overlay.visible_windows(on, DRAFT, columns=True))
        self.assertIn("main", overlay.visible_windows(on, DRAFT, columns=False))
        self.assertEqual(overlay.visible_windows(on, DRAFT), overlay.visible_windows(on, DRAFT, columns=False))


class LayoutTests(unittest.TestCase):
    def test_default_layout_matches_arena(self):
        r = ap.column_rects((2000, 1125), None)
        x, y, w, h = r["deck"]
        self.assertLess(x, 30)
        self.assertGreater(w, 220)
        self.assertLess(x + w, 290)  # links neben der ersten Kartenspalte (x 288)
        self.assertGreater(y, 175)  # unter den Nachbar-Bannern
        px, py, pw, ph = r["pick"]
        self.assertGreater(px, 1293)  # rechts neben der letzten Kartenspalte
        self.assertLess(px + pw, 1532)  # vor Arenas Deckliste
        self.assertLess(py + ph, 1030)  # ueber dem Knopf "Select"

    def test_follows_the_calibrated_card_grid(self):
        cal = {"x": 0.2, "y": 0.17, "w": 0.09, "h": 0.23, "dx": 0.1, "dy": 0.25, "cols": 4, "size": [2000, 1125]}
        r = ap.column_rects((2000, 1125), cal)
        x, _, w, _ = r["deck"]
        self.assertLessEqual(x + w, 400)
        px, _, pw, _ = r["pick"]
        self.assertGreaterEqual(px, round((0.2 + 3 * 0.1 + 0.09) * 2000))

    def test_scales_with_the_window(self):
        big, small = ap.column_rects((2000, 1125), None), ap.column_rects((1000, 562), None)
        self.assertAlmostEqual(small["deck"][2], big["deck"][2] / 2, delta=2)

    def test_silly_calibration_falls_back(self):
        cal = {"x": 0.6, "y": 0.17, "w": 0.09, "h": 0.23, "dx": 0.1, "dy": 0.25, "cols": 5, "size": [2000, 1125]}
        self.assertEqual(ap.column_rects((2000, 1125), cal), ap.column_rects((2000, 1125), None))


CLICKS = [(20, 190), (270, 1010), (1306, 190), (1520, 1000)]  # bei 2000x1125


class ColumnCalibrationTests(unittest.TestCase):
    """Eigene Kalibrierung der Saeulen (Nutzer 15.11.2026: andere Aufloesung): vier Klicks, Anteile am Arena-Fenster."""

    def test_four_clicks_give_fractions(self):
        cal = ap.calibrate_columns(CLICKS, (2000, 1125))
        self.assertEqual(cal["size"], [2000, 1125])
        self.assertEqual([round(v, 4) for v in cal["deck"]], [0.01, round(190 / 1125, 4), 0.125, round(820 / 1125, 4)])
        self.assertAlmostEqual(cal["pick"][0], 0.653)

    def test_rects_follow_the_column_calibration_and_scale(self):
        cal = ap.calibrate_columns(CLICKS, (2000, 1125))
        self.assertEqual(ap.column_rects((2000, 1125), None, cal)["deck"], (20, 190, 250, 820))
        self.assertEqual(ap.column_rects((1000, 562), None, cal)["pick"], (653, 95, 107, 405))
        card_cal = {"x": 0.2, "y": 0.17, "w": 0.09, "h": 0.23, "dx": 0.1, "dy": 0.25, "cols": 4, "size": [2000, 1125]}
        self.assertEqual(ap.column_rects((2000, 1125), card_cal, cal)["deck"], (20, 190, 250, 820))  # geht vor

    def test_other_aspect_ratio_falls_back(self):
        cal = ap.calibrate_columns(CLICKS, (2000, 1125))
        self.assertEqual(ap.column_rects((1600, 1200), None, cal), ap.column_rects((1600, 1200), None))
        self.assertIn("neu kalibrieren", ap.column_status(cal, {"found": True, "size": (1600, 1200)}))
        self.assertEqual(ap.column_status(cal, {"found": True, "size": (1000, 562)}), "")
        self.assertIn("Standardlage", ap.column_status(None, {"found": True, "size": (2000, 1125)}))

    def test_wrong_clicks(self):
        for clicks in ([(270, 1010), (20, 190)] + CLICKS[2:],  # unten rechts vor oben links
                       CLICKS[:2] + [(1306, 190), (1310, 300)],  # Saeule zu schmal
                       CLICKS[:3]):
            with self.assertRaises(ValueError, msg=clicks):
                ap.calibrate_columns(clicks, (2000, 1125))

    def test_save_and_load(self):
        import pathlib
        import tempfile
        cal = ap.calibrate_columns(CLICKS, (2000, 1125))
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "saeulen.json"
            self.assertIsNone(ap.load_column_calibration(path))
            ap.save_column_calibration(path, cal)
            self.assertEqual(ap.load_column_calibration(path), cal)
            path.write_text("{}", encoding="utf-8")
            self.assertIsNone(ap.load_column_calibration(path))
            ap.save_column_calibration(path, None)  # Standardlage: Datei weg
            self.assertFalse(path.exists())

    def test_file_is_not_in_git(self):
        import pathlib
        ignore = (pathlib.Path(__file__).resolve().parent.parent / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(ap.COL_FILE.name, ignore.split())

    def test_english(self):
        with english():
            out = "\n".join([ap.column_status(None, {"found": True, "size": (2000, 1125)}),
                             ap.column_status(ap.calibrate_columns(CLICKS, (2000, 1125)),
                                              {"found": True, "size": (1600, 1200)})] +
                            [ap.calibration_title(i) for i in range(4)] + [ap.calibration_help()])
            for clicks in ([(270, 1010), (20, 190)] + CLICKS[2:], CLICKS[:2] + [(1306, 190), (1310, 300)]):
                try:
                    ap.calibrate_columns(clicks, (2000, 1125))
                except ValueError as err:
                    out += "\n" + str(err)
        self.assertEqual(german_leftovers(out), [])


PICKCARDS = [{"name": "Bear", "colors": ["W"], "mv": 2, "land": False, "creature": True, "removal": 0},
             {"name": "Bolt", "colors": ["R"], "mv": 1, "land": False, "creature": False, "removal": 2.5},
             {"name": "Bolt", "colors": ["R"], "mv": 1, "land": False, "creature": False, "removal": 2.5},
             {"name": "Wisp", "colors": ["U"], "mv": 3, "land": False, "creature": True, "removal": 0},
             {"name": "Golem", "colors": [], "mv": 4, "land": False, "creature": True, "removal": 0},
             {"name": "Charm", "colors": ["W", "R"], "mv": 2, "land": False, "creature": False, "removal": 1},
             {"name": "Planet", "colors": [], "mv": 0, "land": True, "creature": False, "removal": 0}]
PICKSNAP = dict(DRAFT, pickcards=PICKCARDS, side={"Bolt": 1, "Wisp": 1})


class PicksPanelTests(unittest.TestCase):
    """Picks-Fenster (Nutzer 15.11.2026): alle Picks nach Farbe, ein Klick legt eine Karte ins Sideboard oder zurueck,
    ohne Umweg ueber die Seite."""

    def groups(self, snap=PICKSNAP):
        return {label: entries for label, entries in ap.picks_groups(snap)}

    def test_groups_by_color(self):
        g = self.groups()
        self.assertEqual(list(g), ["W", "U", "R", "Mehrfarbig", "Farblos", "Länder"])
        self.assertEqual([(e["name"], e["sb"]) for e in g["R"]], [("Bolt", False), ("Bolt", True)])  # letzte Kopie
        self.assertEqual([(e["name"], e["sb"]) for e in g["U"]], [("Wisp", True)])
        self.assertEqual(g["W"][0]["mv"], 2)
        self.assertTrue(g["W"][0]["creature"])

    def test_sorted_by_mana_value(self):
        snap = dict(PICKSNAP, pickcards=[dict(PICKCARDS[0], name="Late", mv=5), dict(PICKCARDS[0], name="Early", mv=1)])
        self.assertEqual([e["name"] for e in self.groups(snap)["W"]], ["Early", "Late"])

    def test_toggle(self):
        self.assertEqual(ap.toggle_side({"Bolt": 1}, "Bolt", True), {})  # zurueck ins Deck
        self.assertEqual(ap.toggle_side({"Bolt": 1}, "Bolt", False), {"Bolt": 2})
        self.assertEqual(ap.toggle_side({}, "Bear", False), {"Bear": 1})
        self.assertEqual(ap.toggle_side({"Bolt": 1, "Wisp": 1}, "Wisp", True), {"Bolt": 1})

    def test_head(self):
        head = ap.picks_head(PICKSNAP)
        self.assertIn("7", head)
        self.assertIn("Sideboard 2", head)

    def test_button_text(self):
        self.assertIn("Sideboard 2", ap.picks_button(PICKSNAP, False))
        self.assertTrue(ap.picks_button(PICKSNAP, False).startswith("▸"))
        self.assertTrue(ap.picks_button(PICKSNAP, True).startswith("▾"))
        self.assertIsNone(ap.picks_button(dict(DRAFT, pickcards=[]), False))

    def test_rect_between_the_columns(self):
        r = ap.column_rects((2000, 1125), None)
        x, y, w, h = ap.picks_rect((2000, 1125), None)
        self.assertGreaterEqual(x, r["deck"][0] + r["deck"][2])
        self.assertLessEqual(x + w, r["pick"][0] + r["pick"][2])
        self.assertLess(y + h, 1030)

    def test_send_side_without_server(self):
        self.assertIsNone(ap.send_side("http://127.0.0.1:9", {"Bolt": 1}, timeout=0.2))

    def test_english(self):
        with english():
            out = "\n".join([label for label, _ in ap.picks_groups(PICKSNAP)] + [
                ap.picks_head(PICKSNAP), ap.picks_button(PICKSNAP, False), ap.picks_help()])
        self.assertEqual(german_leftovers(out), [])
        self.assertIn("Multicolor", out)


class PickCardsSnapshotTests(unittest.TestCase):
    def test_snapshot_lists_the_picks_with_colors_and_mana_value(self):
        from tests.test_live_sideboard import SideboardTestCase

        class Case(SideboardTestCase):
            def runTest(self):
                pass
        case = Case()
        case.setUp()
        try:
            snap = case.snap()
            self.assertEqual([c["name"] for c in snap["pickcards"]], snap["picks"])
            first = snap["pickcards"][0]
            self.assertEqual(set(first), {"name", "colors", "mv", "land", "creature", "removal"})
        finally:
            case.tearDown()

    def test_page_takes_over_the_sideboard_of_the_server(self):
        import pathlib
        page = (pathlib.Path(__file__).resolve().parent.parent / "components" / "drafthelper.py").read_text(
            encoding="utf-8")
        self.assertIn("function syncSide()", page)
        self.assertIn("syncSide()", page.split("async function pollLive", 1)[1].split("function liveSide", 1)[0])


class PoolInfoTests(unittest.TestCase):
    def test_curve_and_colors_of_spells(self):
        cards = [{"mv": 1, "colors": ["W"], "land": False}, {"mv": 3, "colors": ["W", "R"], "land": False},
                 {"mv": 7, "colors": ["R"], "land": False}, {"mv": 0, "colors": [], "land": True},
                 {"mv": 2, "colors": ["U"], "land": False}]
        i = ld.pool_info(cards, "WR")
        self.assertEqual(i["curve"], [1, 1, 1, 0, 0, 1])
        self.assertEqual(i["colors"], {"W": 2, "R": 2, "U": 1})
        self.assertEqual(i["arch"]["curve"], [1, 0, 1, 0, 0, 1])
        self.assertEqual(i["arch"]["colors"], {"W": 2, "R": 2})


class EnglishTests(unittest.TestCase):
    def all_text(self):
        out = []
        for snap in (dict(DRAFT, curve_warning=WARN), dict(DRAFT, detect={"main": None, "scores": []}),
                     dict(DRAFT, status="waiting", pack=[], detect=dict(DRAFT["detect"], manual=True, switch={
                         "name": "Izzet", "colors": "UR", "score": 4, "plan_score": 2}), side={"x": 1})):
            d, p = ap.deck_column(snap), ap.pick_column(snap)
            out += [d["title"]] + [x for tl in d["tiles"] for x in (tl["label"], tl["big"], tl["unit"], tl["sub"])]
            out += [k for k, _ in d["more"]] + list(ap.sections().values())
            out += [p["head"], p["arch_note"], p["switch"] or "", p["state"] or ""] + p["warn"]
            out += [s for s, _ in p["signals"]]
        return "\n".join(out)

    def test_no_german_leftovers(self):
        with english():
            out = self.all_text()
        self.assertEqual(german_leftovers(out, allow=["Boros", "Izzet", "Test Bolt"]), [])
        self.assertIn("CREATURES", out)
        self.assertIn("W open +2", out)

    def test_german_unchanged(self):
        de = self.all_text()
        with english():
            self.all_text()
        self.assertEqual(self.all_text(), de)
        self.assertIn("KREATUREN", de)


if __name__ == "__main__":
    unittest.main()
