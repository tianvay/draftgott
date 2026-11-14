"""Daten fuer das Stream-Overlay (/api/stream): dieselben Zeilen wie Seitenfenster und Trick-Warner, dazu Bilanz,
Farben und Kurve als Werte, abrufbar auch aus einer Browserquelle von OBS (CORS)."""
import json
import threading
import unittest
import urllib.request

from components import drafthelper as dh
from components import overlay
from components.streamdata import payload
from tests.i18n_check import english

GAME = {"game": {"active": True, "turn": 3, "library": 30, "hand": 5, "groups": [], "cards": [],
                 "tricks": {"open": 2, "lands": 3, "colors": {"U": 2}, "now": []}}}
DECK = {"status": "done", "complete": True, "detect": {"main": "RB"},
        "deckinfo": {"cards": 40, "lands": 17, "spells": 23, "avg_mv": 2.9, "curve": [1, 6, 5, 4, 2, 1],
                     "creatures": 15, "removal": 4, "removal_points": 9, "flow": 2, "colors": {"R": 12, "B": 11},
                     "record": {"wins": 3, "losses": 1, "matches": 4}},
        "summary": {"games": 6, "wins": 5, "losses": 2, "max_wins": 7, "turns": 50, "drawn": 60, "spells": 40,
                    "lands": 30, "damage_dealt": 100, "biggest_hit": 9, "damage_taken": 60, "kills": 12,
                    "damage_creatures": 40},
        "signals": {"format": "Premier Draft", "colors": {}}}


def _lists(rows):
    return [list(r) for r in rows]


class PayloadTests(unittest.TestCase):
    def test_without_snapshot(self):
        p = payload(None)
        self.assertEqual(p["mode"], "off")
        self.assertEqual(p["main"], _lists(overlay.rows_for(None)))
        self.assertEqual(p["tricks"], _lists(overlay.trick_window_rows(None)))
        self.assertIsNone(p["record"])

    def test_game_uses_the_rows_of_both_windows(self):
        p = payload(GAME)
        self.assertEqual(p["mode"], "game")
        self.assertEqual(p["main"], _lists(overlay.rows_for(GAME)))
        self.assertEqual(p["tricks"], _lists(overlay.trick_window_rows(GAME)))

    def test_deck_has_record_colors_curve_and_format(self):
        p = payload(DECK)
        self.assertEqual(p["mode"], "deck")
        self.assertEqual(p["record"], {"wins": 5, "losses": 2})  # Draft-Bilanz geht vor der Deck-Bilanz
        self.assertEqual(p["colors"], ["R", "B"])
        self.assertEqual(p["curve"], [1, 6, 5, 4, 2, 1])
        self.assertEqual(p["format"], "Premier Draft")

    def test_record_from_deck_without_summary(self):
        self.assertEqual(payload(dict(DECK, summary=None))["record"], {"wins": 3, "losses": 1})

    def test_draft_mode(self):
        p = payload({"status": "pack", "pick": 4, "pack": [], "detect": {"main": None}})
        self.assertEqual(p["mode"], "draft")
        self.assertEqual(p["colors"], [])
        self.assertIsNone(p["curve"])


class LanguageTests(unittest.TestCase):
    """Startet draftgott auf Englisch, zeigt auch das Stream-Overlay Englisch (Nutzer 14.11.2026)."""

    def test_german_by_default(self):
        self.assertEqual(payload(None)["lang"], "de")
        self.assertEqual(payload(DECK)["lang"], "de")

    def test_english_rows_and_language(self):
        with english():
            p = payload(GAME)
            off = payload(None)
        self.assertEqual((p["lang"], off["lang"]), ("en", "en"))
        self.assertIn("Turn 3", p["main"][0][0])
        self.assertIn("Trick Warner", p["tricks"][0][0])


class StreamApiTests(unittest.TestCase):
    def test_stream_api_allows_browser_sources(self):
        server = dh.LocalServer(("127.0.0.1", 0), dh.make_handler({}))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            url = f"http://127.0.0.1:{server.server_address[1]}/api/stream"
            with urllib.request.urlopen(url, timeout=5) as r:
                self.assertEqual(r.headers["Access-Control-Allow-Origin"], "*")
                data = json.loads(r.read().decode("utf-8"))
            self.assertEqual(data["mode"], "off")
            self.assertTrue(data["main"])
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
