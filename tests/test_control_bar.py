"""Steuerleiste oben mittig mit Symbolen (Nutzer 15.11.2026) und Fenster, die nur erscheinen, wenn man sie braucht:
im Draft uebernehmen die Saeulen, das Seitenfenster (Deck / Bibliothek) bleibt dann weg."""
import unittest

from components import arenapanels as ap
from components import overlay
from tests.i18n_check import english, german_leftovers

ON = {"main": True, "tricks": True}
DRAFT = {"status": "pack", "pick": 4, "detect": {"main": None, "scores": []},
         "pack": [{"name": "Test Bolt", "colors": ["R"], "rating": "mustplay", "level": "best", "arch": [],
                   "removal": 2.5},
                  {"name": "Test Bear", "colors": ["W"], "rating": "", "level": "", "arch": []},
                  {"name": "Test Never", "colors": ["U"], "rating": "neverplay", "level": "", "arch": []}]}
GAME = {"status": "waiting", "game": {"active": True, "turn": 2, "library": 30, "hand": 5, "groups": [], "cards": []}}
DECK = {"status": "waiting", "complete": True, "deckinfo": {"cards": 40}}


class SmartWindowTests(unittest.TestCase):
    def test_side_window_not_needed_while_drafting_with_columns(self):
        self.assertNotIn("main", overlay.visible_windows(ON, DRAFT, columns=True))
        self.assertNotIn("main", overlay.visible_windows(ON, dict(DRAFT, status="waiting"), columns=True))
        self.assertIn("main", overlay.visible_windows(ON, DRAFT, columns=False))  # Saeulen aus oder Arena weg

    def test_side_window_in_game_and_after_the_draft(self):
        self.assertIn("main", overlay.visible_windows(ON, GAME))
        self.assertIn("main", overlay.visible_windows(ON, DECK))
        self.assertIn("main", overlay.visible_windows(ON, {"status": "idle", "enemy_saved": "x.txt"}))

    def test_nothing_to_show_without_draft_or_game(self):
        for status in ("idle", "nolog", "off"):
            self.assertNotIn("main", overlay.visible_windows(ON, {"status": status, "message": "x"}), msg=status)

    def test_needed(self):
        self.assertTrue(overlay.main_needed(None))  # Drafthelper nicht erreichbar: Meldung zeigen
        self.assertTrue(overlay.main_needed(GAME))
        self.assertFalse(overlay.main_needed({"status": "idle"}))


class BarTests(unittest.TestCase):
    def test_items_with_symbols(self):
        keys = [item["key"] for item in overlay.BAR_ITEMS]
        self.assertEqual(keys, ["main", "tricks", "cards", "cols"])
        for item in overlay.BAR_ITEMS:
            self.assertTrue(item["icon"].strip())
            self.assertTrue(item["label"])
            self.assertTrue(item["tip"])
        self.assertTrue([i for i in overlay.BAR_ITEMS if i.get("calibrate")])

    def test_states(self):
        self.assertEqual(overlay.bar_state(False, False), "off")
        self.assertEqual(overlay.bar_state(True, True), "on")
        self.assertEqual(overlay.bar_state(True, False), "waiting")  # an, gerade nicht gebraucht

    def test_tip_explains_the_state(self):
        item = next(i for i in overlay.BAR_ITEMS if i["key"] == "tricks")
        self.assertIn("Spiel", overlay.bar_tip(item, "waiting"))
        self.assertIn("aus", overlay.bar_tip(item, "off"))
        self.assertIn("Fehlt", overlay.bar_tip(item, "on", "Fehlt was"))

    def test_status_joins_hints(self):
        self.assertEqual(overlay.bar_status(["", "a", "", "b"]), "a · b")
        self.assertEqual(overlay.bar_status(["", ""]), "")

    def test_english(self):
        with english():
            out = []
            for item in overlay.BAR_ITEMS:
                out.append(overlay.t(item["label"]))
                out += [overlay.bar_tip(item, s) for s in ("off", "on", "waiting")]
            out.append(overlay.t("Kalibrieren"))
        self.assertEqual(german_leftovers("\n".join(out)), [])


class PackInColumnTests(unittest.TestCase):
    """Ohne Karten-Overlay steht die Rangliste des Packs in der rechten Saeule (das Seitenfenster ist im Draft weg)."""

    def test_ranking_without_card_overlay(self):
        col = ap.pick_column(DRAFT, slim=False)
        self.assertEqual([p["name"] for p in col["pack"]], ["Test Bolt", "Test Bear", "Test Never"])
        self.assertEqual(col["pack"][0]["level"], "best")
        self.assertIn("MP", col["pack"][0]["text"])
        self.assertIn("R2,5", col["pack"][0]["text"])
        self.assertEqual(col["pack"][2]["level"], "never")

    def test_no_ranking_with_card_overlay_or_while_waiting(self):
        self.assertEqual(ap.pick_column(DRAFT, slim=True)["pack"], [])
        self.assertEqual(ap.pick_column(dict(DRAFT, status="waiting"))["pack"], [])

    def test_at_most_eight(self):
        snap = dict(DRAFT, pack=[dict(DRAFT["pack"][1], name=f"Card {i}") for i in range(14)])
        self.assertEqual(len(ap.pick_column(snap)["pack"]), ap.PACK_ROWS)


if __name__ == "__main__":
    unittest.main()


class CloseQuitsTests(unittest.TestCase):
    """✕ an der Steuerleiste beendet auch den Drafthelper und damit die draftgott-Konsole (Nutzer 15.11.2026)."""

    def test_send_quit_posts_to_the_drafthelper(self):
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer
        seen = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                seen.append(self.path)
                body = b'{"ok": true}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.handle_request, daemon=True).start()
        try:
            self.assertTrue(overlay.send_quit(f"http://127.0.0.1:{server.server_port}/"))
        finally:
            server.server_close()
        self.assertEqual(seen, ["/api/quit"])

    def test_send_quit_without_drafthelper(self):
        self.assertFalse(overlay.send_quit("http://127.0.0.1:9/", timeout=0.5))

    def test_close_tip_says_it_quits(self):
        self.assertIn("beendet", overlay.CLOSE_TIP)
        with english():
            self.assertEqual(german_leftovers(overlay.t(overlay.CLOSE_TIP)), [])
