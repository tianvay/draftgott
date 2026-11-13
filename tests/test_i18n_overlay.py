"""Englische Texte des Seitenfensters: keine deutschen Reste, Deutsch unveraendert."""
import unittest

from components import overlay
from tests.i18n_check import english, german_leftovers

ALLOW = ["draftgott", "Hall of Game", "Test Bear", "Test Bolt", "Plains"]

GAME = {"active": True, "turn": 3, "library": 30, "hand": 4, "consistent": False,
        "mana": {"lands": 2, "colors": {"W": 1, "R": 1}},
        "groups": [{"key": "land", "label": "Land", "n": 10, "next": 0.4, "in3": 0.8},
                   {"key": "removal", "label": "Removal", "n": 3, "next": 0.001, "in3": 0.0},
                   {"key": "creature", "label": "Creature", "n": 5, "next": 0.2, "in3": 0.5}],
        "removal": {"total": 4, "left": 3, "points_total": 6.5, "points_left": 4.5},
        "cards": [{"name": "Test Bear", "n": 2, "land": False, "next": 0.1, "castable": True, "removal": 0},
                  {"name": "Test Bolt", "n": 1, "land": False, "next": 0.05, "castable": False, "removal": 2.5},
                  {"name": "Plains", "n": 3, "land": True, "next": 0.1}],
        "tricks": {"open": 2, "lands": 4, "colors": {"U": 2}, "spell_colors": ["U"],
                   "now": [{"name": "Test Bolt", "cost": "{R}", "rating": "mustplay", "removal": 2.5,
                            "type": "Instant", "pt": None, "text": None}]}}
INFO = {"cards": 40, "lands": 17, "spells": 23, "avg_mv": 2.5, "curve": [1, 2, 3, 4, 5, 6], "creatures": 14,
        "removal": 4, "removal_points": 5.5, "flow": 3, "colors": {"W": 10, "R": 8}, "top": ["Test Bolt"],
        "record": {"wins": 2, "losses": 1, "matches": 3}}
DRAFT = {"status": "pack", "pick": 5, "detect": {"main": "WR", "manual": True, "scores": [
             {"colors": "WR", "name": "Boros", "score": 3.5}]},
         "hints": [{"name": "Test Bolt", "rating": "mustplay", "best": "WR", "best_name": "Boros", "state": "near"}],
         "signals": {"format": "Draft", "colors": {"W": {"level": "maybe", "score": 2}}, "notes": []},
         "draftinfo": {"cards": 4, "creatures": 2, "removal": 1, "removal_points": 1.5, "flow": 0,
                       "arch": {"cards": 3, "creatures": 1, "removal": 1, "removal_points": 1.5, "flow": 0}},
         "archmap": [{"name": "Boros", "count": 2, "pack": ["Test Bolt"], "colors": "WR"}],
         "pack": [{"name": "Test Bolt", "colors": ["R"], "rating": "mustplay", "level": "best", "arch": ["WR"],
                   "removal": 2.5, "synergy": 1.5, "stats": {"games": 10, "wins": 6}}],
         "archetypes": [{"colors": "WR", "name": "Boros", "tips": ["Tip"]}]}


def all_rows():
    snaps = [None, DRAFT, dict(DRAFT, status="waiting"), {"status": "idle"}, {"game": GAME},
             {"complete": True, "deckinfo": INFO, "detect": {"main": "WR"}, "enemy_saved": "x.txt"}]
    rows = []
    for s in snaps:
        rows += overlay.rows_for(s) + overlay.mini_rows(s)
    rows += overlay.trick_window_rows({"game": GAME}) + overlay.trick_window_rows({}) + overlay.trick_rows(
        dict(GAME["tricks"], open=0, now=[]))
    rows += overlay.trick_rows(dict(GAME["tricks"], now=[]))
    rows += overlay.mini_rows({"complete": True, "deckinfo": INFO}) + overlay.mini_rows({"status": "pack"})
    rows += overlay.mini_rows({"status": "pack", "pick": 2})
    return rows


def texts():
    out = [line for line, _ in all_rows()]
    out += overlay.celebration_lines("Deck.txt")
    out += list(overlay.trick_tips({"game": GAME}).values())
    out += [overlay.trick_tip({"name": "Test Bear", "cost": "{W}", "removal": 1})]
    for snap in (None, {"complete": True}, {"complete": True, "deck": {"applied": True}},
                 {"complete": True, "deck": {"ready": True, "main": 40, "side": 10}}):
        btn = overlay.deck_button(snap)
        if btn:
            out.append(btn[0])
    return out


class OverlayEnglishTests(unittest.TestCase):
    def test_no_german_leftovers(self):
        with english():
            out = "\n".join(texts())
        self.assertEqual(german_leftovers(out, allow=ALLOW), [])
        self.assertIn("4 wins!", out)
        self.assertIn("Trick Warner", out)
        self.assertIn("avg mana value 2.50", out)

    def test_german_unchanged(self):
        de = "\n".join(texts())
        with english():
            texts()
        self.assertEqual("\n".join(texts()), de)
        self.assertIn("Ø Manawert 2,50", de)
        self.assertEqual(overlay.celebration_lines("a.txt")[0], "4 Siege!")

    def test_charts_parse_english_rows(self):
        with english():
            rows = dict((tag, line) for line, tag in overlay.rows_for({"complete": True, "deckinfo": INFO}))
            self.assertEqual(overlay.curve_bars(rows["curve"])[0], ("≤1", 1))
            self.assertEqual(overlay.color_parts(rows["colors"]), [("W", 10), ("R", 8)])

    def test_windows_labels_in_dictionary(self):
        from components.i18n_en.overlay import EN
        for _, label in overlay.WINDOWS:
            self.assertIn(label, EN)
        for v in overlay.HINT_STATE.values():
            self.assertIn(v, EN)
        for v in overlay.SIGNAL_LABEL.values():
            self.assertIn(v, EN)


if __name__ == "__main__":
    unittest.main()
