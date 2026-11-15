"""Spacecraft in den Uebersichten (Nutzer 15.11.2026): Typ-Uebersicht des Drafthelpers (typeCounts) und Kartentypen
im Bericht, Kennzahlen im Live-Draft (pool_info, deck_summary), Seitenfenster, minimierter Kasten und Stream-Overlay."""
import shutil
import unittest

from components import livedraft as ld
from components import overlay
from components.cardkinds import type_kinds
from components.report_cards import render_type_table, type_counts
from components.streamdata import payload
from tests.i18n_check import english
from tests.test_type_overview import run_js

DASH = "—"
SHIP = {"name": "Test Ship", "type_line": f"Artifact {DASH} Spacecraft", "mana_cost": "{3}", "cmc": 3,
        "colors": [], "oracle_text": "Station\n7+ | Flying\n4/4", "keywords": ["Station"], "layout": "normal"}
PILOT = {"name": "Test Pilot", "type_line": f"Creature {DASH} Human Pilot", "mana_cost": "{W}", "cmc": 1,
         "colors": ["W"], "oracle_text": "Whenever you cast a creature or Spacecraft spell, scry 1.",
         "power": "1", "toughness": "1", "layout": "normal"}


class TypeKindTests(unittest.TestCase):
    def test_spacecraft_is_an_artifact_and_a_spacecraft(self):
        self.assertEqual(type_kinds(f"Artifact {DASH} Spacecraft"), ["artifact", "spacecraft"])
        self.assertEqual(type_kinds(f"Legendary Artifact {DASH} Spacecraft"), ["artifact", "spacecraft"])

    def test_only_the_subtype_counts(self):
        self.assertNotIn("spacecraft", type_kinds(f"Creature {DASH} Human Pilot"))
        self.assertNotIn("spacecraft", type_kinds("Artifact"))

    def test_double_faced_card_uses_the_front(self):
        self.assertNotIn("spacecraft", type_kinds(f"Sorcery // Artifact {DASH} Spacecraft"))


class ReportTests(unittest.TestCase):
    def ctx(self, ship_qty):
        rows = [("Test Pilot", 2, None, "")] + ([("Test Ship", ship_qty, None, "")] if ship_qty else [])
        return {"rows": rows, "info": {"Test Pilot": {"kinds": ["creature"]},
                                       "Test Ship": {"kinds": ["artifact", "spacecraft"]}}}

    def test_counts_copies(self):
        self.assertEqual(type_counts(self.ctx(3))["spacecraft"], 3)
        self.assertEqual(type_counts(self.ctx(3))["artifact"], 3)

    def test_row_only_with_spacecraft(self):
        html = render_type_table(self.ctx(3))
        self.assertIn("Spacecraft (Karten)", html)
        self.assertNotIn("Spacecraft", render_type_table(self.ctx(0)))


def copy(kinds, mark="core"):
    return {"kinds": kinds, "mark": mark, "empower": False, "points": 0, "flow": []}


@unittest.skipUnless(shutil.which("node"), "Node.js nicht installiert")
class PageTests(unittest.TestCase):
    def test_spacecraft_per_variant(self):
        r = run_js([copy(["artifact", "spacecraft"]), copy(["artifact", "spacecraft"], "nosplash"),
                    copy(["artifact", "spacecraft"], "off"), copy(["creature"])], [])
        self.assertEqual((r["splash"]["spacecraft"], r["nosplash"]["spacecraft"]), (1, 2))

    def test_same_count_as_the_report(self):
        js = run_js([copy(["artifact", "spacecraft"]), copy(["artifact", "spacecraft"])], [])["splash"]["spacecraft"]
        self.assertEqual(js, type_counts(ReportTests().ctx(2))["spacecraft"])


class PageRowTests(unittest.TestCase):
    def test_row_appears_only_with_spacecraft_in_the_pool(self):
        from components import drafthelper as dh
        self.assertIn('["spacecraft","Spacecraft (Karten)","sep"]', dh.PAGE)
        self.assertIn('pool.some(c=>(c.kinds||[]).includes("spacecraft"))', dh.PAGE)


class LiveTests(unittest.TestCase):
    def test_card_summary_marks_spacecraft(self):
        self.assertTrue(ld.card_summary(SHIP, "Test Ship")["spacecraft"])
        self.assertFalse(ld.card_summary(PILOT, "Test Pilot")["spacecraft"])
        self.assertFalse(ld.card_summary(None, "Unbekannt")["spacecraft"])

    def test_pool_info_counts_spacecraft_also_in_the_archetype(self):
        cards = [ld.card_summary(SHIP, "Test Ship"), ld.card_summary(SHIP, "Test Ship"),
                 ld.card_summary(PILOT, "Test Pilot")]
        info = ld.pool_info(cards, "UB")
        self.assertEqual(info["spacecraft"], 2)
        self.assertEqual(info["arch"]["spacecraft"], 2)  # farblos zaehlt im Archetyp mit

    def test_deck_summary_counts_copies(self):
        cards = [dict(ld.card_summary(SHIP, "Test Ship"), qty=3), dict(ld.card_summary(PILOT, "Test Pilot"), qty=2)]
        self.assertEqual(ld.deck_summary(cards, {}, "arena")["spacecraft"], 3)


INFO = {"cards": 5, "creatures": 2, "removal": 1, "removal_points": 1, "flow": 0, "flow_kinds": {}}
DRAFT = {"status": "pack", "pick": 6, "pack": [{"name": "X", "colors": ["W"], "level": ""}],
         "detect": {"main": "WU", "scores": []}, "archetypes": [{"colors": "WU", "name": "Spacecraft"}],
         "draftinfo": dict(INFO, spacecraft=2, arch=dict(INFO, spacecraft=2))}
DECK = {"status": "done", "complete": True, "detect": {"main": "WU"},
        "archetypes": [{"colors": "WU", "name": "Spacecraft"}],
        "deckinfo": {"source": "arena", "cards": 40, "lands": 17, "spells": 23, "avg_mv": 3.0,
                     "curve": [1, 5, 6, 5, 4, 2], "creatures": 12, "removal": 3, "removal_points": 3, "flow": 2,
                     "colors": {"W": 12, "U": 11}, "top": [], "spacecraft": 4}}


def texts(rows):
    return [r[0] for r in rows]


class OverlayTests(unittest.TestCase):
    def test_side_window_in_the_draft(self):
        self.assertIn(("Spacecraft 2", "ship"), overlay.rows_for(DRAFT))
        self.assertIn(("Spacecraft 2", "ship"), overlay.rows_for(DRAFT, slim=True))

    def test_side_window_counts_the_archetype(self):
        snap = dict(DRAFT, draftinfo=dict(INFO, spacecraft=3, arch=dict(INFO, spacecraft=2)))
        self.assertIn(("Spacecraft 2", "ship"), overlay.rows_for(snap))
        snap = dict(snap, detect={"main": None, "scores": []})
        self.assertIn(("Spacecraft 3", "ship"), overlay.rows_for(snap))

    def test_side_window_without_spacecraft(self):
        snap = dict(DRAFT, draftinfo=dict(INFO, spacecraft=0, arch=dict(INFO, spacecraft=0)))
        self.assertFalse(any("Spacecraft 0" in x for x in texts(overlay.rows_for(snap))))

    def test_deck_rows_show_spacecraft(self):
        self.assertIn(("Spacecraft 4", "ship"), overlay.deck_rows(DECK))
        self.assertFalse(any("Spacecraft 0" in x for x in texts(overlay.deck_rows(
            dict(DECK, deckinfo=dict(DECK["deckinfo"], spacecraft=0))))))

    def test_mini_box_in_the_draft(self):
        self.assertIn(("Spacecraft 2", "ship"), overlay.mini_rows(DRAFT))
        self.assertIn(("Spacecraft 2", "ship"), overlay.mini_rows(DRAFT, slim=True))

    def test_mini_box_after_the_draft(self):
        self.assertIn(("Spacecraft 4", "ship"), overlay.mini_rows(DECK))

    def test_mini_box_without_spacecraft(self):
        snap = dict(DRAFT, draftinfo=dict(INFO, spacecraft=0, arch=dict(INFO, spacecraft=0)))
        self.assertFalse(any(tag == "ship" for _x, tag in overlay.mini_rows(snap)))  # Archetyp heisst Spacecraft

    def test_mini_box_has_a_style_for_the_row(self):
        self.assertIn("ship", overlay.MINI_TAGS)
        self.assertIn("ship", overlay.COLORS)

    def test_english(self):
        with english():
            self.assertIn(("Spacecraft 4", "ship"), overlay.deck_rows(DECK))
            self.assertIn(("Spacecraft 2", "ship"), overlay.mini_rows(DRAFT))


class StreamTests(unittest.TestCase):
    def test_stream_has_the_rows_and_the_number(self):
        p = payload(DRAFT)
        self.assertIn(["Spacecraft 2", "ship"], [r for r in p["main"] if r[1] == "ship"])
        self.assertEqual(p["spacecraft"], 2)
        self.assertEqual(payload(DECK)["spacecraft"], 4)

    def test_stream_without_spacecraft(self):
        self.assertEqual(payload({"status": "pack", "pick": 1, "pack": [], "detect": {"main": None}})["spacecraft"],
                         0)
        self.assertEqual(payload(None)["spacecraft"], 0)


if __name__ == "__main__":
    unittest.main()
