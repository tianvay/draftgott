"""Live-Draft: Picks ins Sideboard legen (Nutzer 15.11.2026). Arena schreibt das Verschieben waehrend des Drafts nicht
ins Protokoll; im Drafthelper heisst "Aus" an einem Pick deshalb Sideboard. Sideboard-Karten zaehlen nicht zum Plan
(Archetyp, Kennzahlen, Kurve, Synergie), ein Wechsel zu einem Archetyp mit ihnen wird angezeigt."""
import json
import pathlib
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock

from components import archetypes as arch
from components import drafthelper as dh
from components import livedraft as ld
from components import overlay
from tests.fixtures import args_for
from tests.i18n_check import english
from tests.test_drafthelper import load
from tests.test_livedraft import NAMES, TST, LiveTestCase, fake_fetch, notify, pick

ASSIGN = {"Test Hasty": ["RW"]}
DRAFT = [notify(1, [201]), pick([201]), notify(2, [202]), pick([202]), notify(3, [102]), pick([102]),
         notify(4, [101]), pick([101]), notify(5, [103])]


class SideboardTestCase(LiveTestCase):
    def setUp(self):
        super().setUp()
        self.write(*DRAFT)
        self.live.step()

    def snap(self, manual=None):
        with mock.patch.dict(arch.ARCHETYPES, TST):
            return self.live.snapshot({}, ASSIGN, manual)


class SideboardTests(SideboardTestCase):
    def test_without_sideboard(self):
        snap = self.snap()
        self.assertEqual(snap["side"], {})
        self.assertEqual(snap["detect"]["main"], "RW")  # RW: Big, Hasty (+1 zugeordnet), Bear = 4; WB 3
        self.assertIsNone(snap["detect"]["switch"])
        self.assertEqual(snap["draftinfo"]["cards"], 4)

    def test_sideboard_goes_to_the_pool_file(self):
        version = self.live.version
        self.live.set_side({"Test Hasty": 1})
        self.assertEqual(self.pool.read_text(encoding="utf-8"),
                         "Deck\n1 Test Gold (TST) 14\n1 Test Big (TST) 13\n1 Test Bear (TST) 10\n"
                         "\nSideboard\n1 Test Hasty (TST) 11\n")
        self.assertGreater(self.live.version, version)

    def test_sideboard_does_not_count_for_the_plan(self):
        self.live.set_side({"Test Hasty": 1})
        snap = self.snap()
        self.assertEqual(snap["side"], {"Test Hasty": 1})
        self.assertEqual(snap["detect"]["main"], "WB")  # ohne Hasty: WB 3, RW 2
        self.assertEqual(snap["draftinfo"]["cards"], 3)
        self.assertEqual(snap["picks"], ["Test Gold", "Test Big", "Test Hasty", "Test Bear"])

    def test_switch_to_an_archetype_with_the_sideboard(self):
        self.live.set_side({"Test Hasty": 1})
        sw = self.snap()["detect"]["switch"]
        self.assertEqual(sw, {"colors": "RW", "name": "Rotweiss", "score": 4, "plan_score": 2, "cards": 1})
        by = {s["colors"]: s for s in self.snap()["detect"]["scores"]}
        self.assertEqual((by["RW"]["side"], by["WB"]["side"]), (2, 0))

    def test_no_switch_when_the_sideboard_changes_nothing(self):
        self.live.set_side({"Test Gold": 1})  # ohne Gold: RW 4, WB 2; mit Gold bleibt RW vorn
        snap = self.snap()
        self.assertEqual(snap["detect"]["main"], "RW")
        self.assertIsNone(snap["detect"]["switch"])

    def test_switch_also_with_own_choice(self):
        self.live.set_side({"Test Hasty": 1})
        snap = self.snap("WB")
        self.assertTrue(snap["detect"]["manual"])
        self.assertEqual(snap["detect"]["switch"]["colors"], "RW")

    def test_unknown_names_and_too_many_copies_are_ignored(self):
        self.live.set_side({"Test Hasty": 5, "Unbekannt": 1, "Test Spell": 1})  # Spell nur im Pack
        self.assertEqual(self.snap()["side"], {"Test Hasty": 1})

    def test_bad_values(self):
        for bad in ({"Test Hasty": "x"}, ["Test Hasty"], {"Test Hasty": -1}):
            with self.assertRaises(ValueError):
                self.live.set_side(bad)

    def test_back_to_the_deck(self):
        self.live.set_side({"Test Hasty": 1})
        self.live.set_side({})
        self.assertEqual(self.snap()["side"], {})
        self.assertNotIn("Sideboard", self.pool.read_text(encoding="utf-8"))

    def test_next_pick_keeps_the_sideboard(self):
        self.live.set_side({"Test Hasty": 1})
        self.write(pick([103]))
        self.live.step()
        text = self.pool.read_text(encoding="utf-8")
        self.assertIn("1 Test Spell (TST) 15\n\nSideboard\n1 Test Hasty (TST) 11\n", text)

    def test_kept_after_a_restart(self):
        self.live.set_side({"Test Hasty": 1})
        live = ld.LiveDraft(self.log, self.pool, names=NAMES, fetch=fake_fetch)
        live.step()
        with mock.patch.dict(arch.ARCHETYPES, TST):
            self.assertEqual(live.snapshot({}, ASSIGN, None)["side"], {"Test Hasty": 1})

    def test_new_draft_starts_without_sideboard(self):
        self.live.set_side({"Test Hasty": 1})
        self.write(notify(1, [102], draft="d2"), pick([102], draft="d2"))
        self.live.step()
        self.assertEqual(self.snap()["side"], {})
        self.assertEqual(self.pool.read_text(encoding="utf-8"), "Deck\n1 Test Hasty (TST) 11\n")

    def test_archetype_map_lists_sideboard_cards_apart(self):
        self.live.set_side({"Test Hasty": 1})
        rw = next(a for a in self.snap()["archmap"] if a["colors"] == "RW")
        self.assertEqual((rw["count"], rw["side"]), (0, 1))


class OverlayTests(SideboardTestCase):
    def test_rows_show_sideboard_and_switch(self):
        self.live.set_side({"Test Hasty": 1})
        rows = overlay.rows_for(self.snap())
        self.assertIn((overlay.t("Sideboard: {n} Karte(n), zählen nicht zum Plan", n=1), "sub"), rows)
        self.assertIn(("↔ Wechsel möglich: Rotweiss (RW) mit Sideboard 4 P., ohne 2 P.", "color"), rows)

    def test_archetype_map_row(self):
        self.live.set_side({"Test Hasty": 1})
        self.assertTrue(any(r[0].startswith("Rotweiss: 0 Picks (+1 im Sideboard)") for r in
                            overlay.rows_for(self.snap())))

    def test_mini_box_shows_the_switch(self):
        self.live.set_side({"Test Hasty": 1})
        self.assertIn(("↔ Rotweiss", "color"), overlay.mini_rows(self.snap()))

    def test_no_rows_without_sideboard(self):
        rows = overlay.rows_for(self.snap())
        self.assertFalse(any("Sideboard" in r[0] or "↔" in r[0] for r in rows))

    def test_english(self):
        self.live.set_side({"Test Hasty": 1})
        snap = self.snap()
        with english():
            rows = overlay.rows_for(snap)
        self.assertIn(("Sideboard: 1 card(s), not part of the plan", "sub"), rows)
        self.assertIn(("↔ Switch possible: Rotweiss (RW) with sideboard 4 pts, without 2 pts", "color"), rows)


class ServerTests(SideboardTestCase):
    def setUp(self):
        super().setUp()
        cards, basics, sig = load()
        self.app = {"pool": cards, "basics": basics, "signature": sig, "args": args_for(["--drafthelper"]),
                    "simulate": None, "save": None, "job": dh.Job(), "options": [1000], "file": "pool.txt",
                    "ratings": pathlib.Path(self.dir.name) / "kartenbewertung.json",
                    "cardarch": pathlib.Path(self.dir.name) / "kartenarchetypen.json", "live": self.live}
        self.server = dh.LocalServer(("127.0.0.1", 0), dh.make_handler(self.app))
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def post(self, body):
        req = urllib.request.Request(self.base + "/api/live/side", data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    def test_set_sideboard(self):
        status, data = self.post({"side": {"Test Hasty": 1}})
        self.assertEqual((status, data["ok"]), (200, True))
        self.assertEqual(self.live.snapshot({}, {}, None)["side"], {"Test Hasty": 1})

    def test_bad_body(self):
        self.assertEqual(self.post({"side": ["x"]})[0], 400)

    def test_without_live_mode(self):
        self.app["live"] = None
        self.assertEqual(self.post({"side": {}})[0], 400)


class PageTests(unittest.TestCase):
    def test_page_sends_off_marks_as_sideboard(self):
        self.assertIn('api("/api/live/side"', dh.PAGE)
        self.assertIn("function liveSide(", dh.PAGE)


if __name__ == "__main__":
    unittest.main()
