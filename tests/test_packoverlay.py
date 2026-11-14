"""Karten-Overlay ueber Arena (components/packoverlay.py): Kalibrierung aus fuenf Klicks, Raster der Karten im
Arena-Fenster, Inhalt je Karte (Rang, Bewertung, Punkte, Archetyp, Chips, eigene Siegquote, Rahmen) in der
Reihenfolge des Packs im Protokoll."""
import json
import pathlib
import tempfile
import unittest

from components import packoverlay as po
from tests.i18n_check import english, german_leftovers

CLIENT = (1600, 900)
# Karte 1 oben links / unten rechts, Karte 2 oben links, letzte Karte der ersten Reihe oben links, erste Karte der
# zweiten Reihe oben links (Pixel im Arena-Fenster)
CLICKS = [(100, 200), (300, 480), (320, 200), (1420, 200), (100, 500)]


class CalibrationTests(unittest.TestCase):
    def test_from_clicks(self):
        cal = po.calibrate(CLICKS, CLIENT)
        self.assertEqual(cal["cols"], 7)
        self.assertAlmostEqual(cal["x"], 100 / 1600)
        self.assertAlmostEqual(cal["y"], 200 / 900)
        self.assertAlmostEqual(cal["w"], 200 / 1600)
        self.assertAlmostEqual(cal["h"], 280 / 900)
        self.assertAlmostEqual(cal["dx"], 220 / 1600)
        self.assertAlmostEqual(cal["dy"], 300 / 900)
        self.assertEqual(cal["size"], [1600, 900])

    def test_invalid(self):
        bad = [
            [(300, 480), (100, 200), (320, 200), (1420, 200), (100, 500)],  # unten rechts vor oben links
            [(100, 200), (300, 480), (90, 200), (1420, 200), (100, 500)],  # Karte 2 links von Karte 1
            [(100, 200), (300, 480), (320, 200), (1420, 200), (100, 150)],  # zweite Reihe ueber der ersten
            CLICKS[:4],
        ]
        for clicks in bad:
            with self.assertRaises(ValueError, msg=clicks):
                po.calibrate(clicks, CLIENT)

    def test_one_row_only(self):  # letzte Karte der ersten Reihe = Karte 2: zwei Spalten
        cal = po.calibrate([(100, 200), (300, 480), (320, 200), (320, 200), (100, 500)], CLIENT)
        self.assertEqual(cal["cols"], 2)

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "kartenoverlay.json"
            self.assertIsNone(po.load_calibration(path))
            cal = po.calibrate(CLICKS, CLIENT)
            po.save_calibration(path, cal)
            self.assertEqual(po.load_calibration(path), cal)
            path.write_text("kaputt", encoding="utf-8")
            self.assertIsNone(po.load_calibration(path))
            path.write_text(json.dumps({"x": 1}), encoding="utf-8")
            self.assertIsNone(po.load_calibration(path))


class GridTests(unittest.TestCase):
    def setUp(self):
        self.cal = po.calibrate(CLICKS, CLIENT)

    def test_rects(self):
        rects = po.card_rects(self.cal, 9, (10, 20), CLIENT)
        self.assertEqual(len(rects), 9)
        self.assertEqual(rects[0], (110, 220, 310, 500))
        self.assertEqual(rects[1], (330, 220, 530, 500))
        self.assertEqual(rects[6], (1430, 220, 1630, 500))
        self.assertEqual(rects[7], (110, 520, 310, 800))  # zweite Reihe
        self.assertEqual(rects[8], (330, 520, 530, 800))

    def test_scaled_window(self):  # Arena-Fenster halb so gross: alles halb so gross
        rects = po.card_rects(self.cal, 2, (0, 0), (800, 450))
        self.assertEqual(rects[0], (50, 100, 150, 240))
        self.assertEqual(rects[1], (160, 100, 260, 240))

    def test_size_changed(self):
        self.assertFalse(po.size_changed(self.cal, CLIENT))
        self.assertFalse(po.size_changed(self.cal, (800, 450)))  # gleiches Seitenverhaeltnis
        self.assertTrue(po.size_changed(self.cal, (1600, 1200)))


def ranked(name, points, rating="", level="", hint="", colors=("B",), best="", removal=0, flow=(), synergy=0,
           stats=None, creature=False):
    return {"name": name, "points": points, "rating": rating, "level": level, "hint": hint, "colors": list(colors),
            "best": best, "removal": removal, "flow": list(flow), "synergy": synergy, "stats": stats,
            "creature": creature, "land": False}


SNAP = {"status": "pack", "complete": False, "game": {"active": False}, "detect": {"main": "BR"},
        "order": ["Quark's Bar", "Grand Nagus Zek", "Tactical Officer", "Tactical Officer"],
        "pack": [ranked("Grand Nagus Zek", 9.5, "matchwinner", "best", "in", ("B", "R"), "BR", removal=2,
                        flow=("draw",), synergy=0.5, stats={"games": 23, "wins": 15}),
                 ranked("Tactical Officer", 4, "mustplay", "color", "near", ("R",), "WR", creature=True,
                        stats={"games": 9, "wins": 5}),
                 ranked("Tactical Officer", 4, "mustplay", "color", "near", ("R",), "WR", creature=True),
                 ranked("Quark's Bar", 1.5, "filler", "", "", (), "")]}


class ViewTests(unittest.TestCase):
    def test_order_and_rank(self):
        views = po.pack_views(SNAP)
        self.assertEqual([v["name"] for v in views], SNAP["order"])  # Reihenfolge wie im Protokoll (Arena)
        self.assertEqual([v["rank"] for v in views], [4, 1, 2, 3])

    def test_top_card(self):
        v = po.pack_views(SNAP)[1]
        self.assertEqual(v["rating"], "♛ MW")
        self.assertEqual(v["points"], "9,5")
        self.assertEqual(v["colors"], ["B", "R"])
        self.assertEqual(v["frame"], "top")
        self.assertIn("dein Archetyp", v["fit"])
        self.assertEqual(v["chips"], ["Removal 2 P.", "Kartenfluss", "Syn +0,5"])
        self.assertEqual(v["stats"], "Deine Decks: 65 % · 23 G.")

    def test_other_frames(self):
        views = po.pack_views(SNAP)
        self.assertEqual(views[2]["frame"], "top")  # Top-Pick-Hinweis "nahe dran"
        self.assertIn("nahe dran", views[2]["fit"])
        self.assertEqual(views[0]["frame"], "off")
        self.assertEqual(views[0]["stats"], "Deine Decks: –")
        self.assertEqual(views[3]["chips"], ["Kreatur"])

    def test_neverplay_and_colors_only(self):
        snap = dict(SNAP, order=["A", "B"], pack=[ranked("A", 0, "neverplay", "color"), ranked("B", 2, "", "color")])
        a, b = po.pack_views(snap)
        self.assertEqual(a["frame"], "never")
        self.assertEqual(a["rating"], "NP")
        self.assertEqual(b["frame"], "fit")
        self.assertIn("Farben passen", b["fit"])
        self.assertEqual(b["rating"], "")

    def test_no_archetype_yet(self):
        snap = dict(SNAP, detect={"main": None}, order=["A"], pack=[ranked("A", 1.5)])
        self.assertIn("noch offen", po.pack_views(snap)[0]["fit"])

    def test_english(self):
        with english():
            views = po.pack_views(SNAP)
        text = json.dumps(views, ensure_ascii=False)
        self.assertIn("your archetype", text)
        self.assertEqual(german_leftovers(text, allow=["Grand Nagus Zek", "Tactical Officer", "Quark's Bar"]), [])


def arena_card(name, rarity, number, points=1):
    return dict(ranked(name, points), rarity=rarity, number=number)


class ArenaOrderTests(unittest.TestCase):
    """Arena zeigt das Pack nach Seltenheit (mythic, rare, uncommon, common) und dann nach Sammlernummer, nicht in der
    Reihenfolge des Protokolls (Pack aus dem Screenshot vom 14.11.2026, TRK)."""

    PACK = [("Tactical Officer", "common", "38"), ("Open Communications", "common", "76"),
            ("Moopsy", "common", "207"), ("Cetacean Ops", "common", "48"), ("He's Dead, Jim", "common", "114"),
            ("Oberth-Class Starship", "common", "26"), ("Plasma Cascade", "common", "164"),
            ("Transporter Malfunction", "uncommon", "178"), ("Saru, Unthreatened", "uncommon", "212"),
            ("La'An Noonien-Singh, Security", "uncommon", "156"), ("Hallowed Fountain", "rare", "286"),
            ("Organic Avulsion Unit", "uncommon", "121"), ("Spatial Anomaly", "uncommon", "296"),
            ("Risa", "common", "293")]
    ARENA = ["Hallowed Fountain", "Organic Avulsion Unit", "La'An Noonien-Singh, Security", "Transporter Malfunction",
             "Saru, Unthreatened", "Spatial Anomaly", "Oberth-Class Starship", "Tactical Officer", "Cetacean Ops",
             "Open Communications", "He's Dead, Jim", "Plasma Cascade", "Moopsy", "Risa"]

    def snap(self, pack):
        cards = [arena_card(n, r, no, points=i) for i, (n, r, no) in enumerate(pack)]
        return dict(SNAP, order=[n for n, _, _ in pack], pack=sorted(cards, key=lambda c: -c["points"]))

    def test_screenshot_pack(self):
        self.assertEqual([v["name"] for v in po.pack_views(self.snap(self.PACK))], self.ARENA)

    def test_mythic_before_rare_and_numbers_numeric(self):
        pack = [("C9", "common", "9"), ("C10", "common", "10"), ("R", "rare", "300"), ("M", "mythic", "301"),
                ("U2", "uncommon", "2a")]
        self.assertEqual([v["name"] for v in po.pack_views(self.snap(pack))], ["M", "R", "U2", "C9", "C10"])

    def test_rank_stays_with_card(self):
        views = po.pack_views(self.snap(self.PACK))
        self.assertEqual(views[-1]["name"], "Risa")
        self.assertEqual(views[-1]["rank"], 1)  # meiste Punkte
        self.assertEqual(views[0]["rank"], 4)  # Hallowed Fountain: Punkte 10 von 0..13

    def test_without_rarity_protocol_order(self):  # fehlen Seltenheit oder Nummer: Reihenfolge des Protokolls
        pack = [("A", "", ""), ("B", "rare", ""), ("C", "rare", "")]
        self.assertEqual([v["name"] for v in po.pack_views(self.snap(pack))], ["B", "C", "A"])


class ShowTests(unittest.TestCase):
    def setUp(self):
        self.cal = po.calibrate(CLICKS, CLIENT)
        self.arena = {"found": True, "minimized": False, "foreground": True, "origin": (0, 0), "size": CLIENT}

    def test_shown_while_picking(self):
        self.assertTrue(po.should_show(True, SNAP, self.cal, self.arena))

    def test_hidden(self):
        cases = [
            (False, SNAP, self.cal, self.arena),
            (True, None, self.cal, self.arena),
            (True, dict(SNAP, status="waiting"), self.cal, self.arena),
            (True, dict(SNAP, complete=True), self.cal, self.arena),
            (True, dict(SNAP, game={"active": True}), self.cal, self.arena),
            (True, dict(SNAP, order=[]), self.cal, self.arena),
            (True, SNAP, None, self.arena),
            (True, SNAP, self.cal, dict(self.arena, found=False)),
            (True, SNAP, self.cal, dict(self.arena, minimized=True)),
            (True, SNAP, self.cal, dict(self.arena, foreground=False)),
        ]
        for i, args in enumerate(cases):
            self.assertFalse(po.should_show(*args), i)


class StatusTests(unittest.TestCase):
    """Kurzer Hinweis im Steuerfenster unter dem Schalter "Karten-Overlay"."""

    def test_texts(self):
        cal = po.calibrate(CLICKS, CLIENT)
        arena = {"found": True, "minimized": False, "foreground": True, "origin": (0, 0), "size": CLIENT}
        self.assertIn("nicht kalibriert", po.status_text(None, arena))
        self.assertIn("Arena nicht gefunden", po.status_text(cal, {"found": False}))
        self.assertIn("neu kalibrieren", po.status_text(cal, dict(arena, size=(1600, 1200))))
        self.assertEqual(po.status_text(cal, arena), "")

    def test_control_window_has_room(self):
        from components import overlay
        self.assertGreaterEqual(overlay.CONTROL_SIZE[1], 150)
        self.assertEqual([k for k, _ in overlay.WINDOWS], ["main", "tricks"])


class SnapshotOrderTests(unittest.TestCase):
    def test_live_snapshot_has_pack_order(self):
        from components import livedraft as ld
        from tests.fixtures import CARDS
        from tests.test_draftstats import notify
        from tests.test_enemy_autosave import INFO
        names = {g: {k: v for k, v in i.items() if k != "colors"} for g, i in INFO.items()}
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            log = d / "Player.log"
            log.write_text(notify(1, [105, 101, 102], draft="d9") + "\n", encoding="utf-8")
            live = ld.LiveDraft(log, d / "pool.txt", names=names, fetch=lambda n, refresh=False: CARDS)
            live.step()
            snap = live.snapshot({}, {}, None)
        self.assertEqual(snap["order"], ["Test Big", "Test Bear", "Test Hasty"])


if __name__ == "__main__":
    unittest.main()
