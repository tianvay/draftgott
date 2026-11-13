"""Bester Archetyp je Karte: dreistufige Zuordnung (neutral, gut, best), Hervorhebung im Pack, Hinweis im
Live-Draft (Seite und Seitenfenster) und im Bericht."""
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from components import archetypes as arch
from components import cardarchetypes as ca
from components import overlay
from tests.test_cardarchetypes import TRK, card
from tests import test_livedraft as tl
from tests.test_livedraft import LiveTestCase, TST, notify, pick


class BestFileTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.dir.name) / "kartenarchetypen.json"

    def tearDown(self):
        self.dir.cleanup()

    def test_best_is_stored_with_the_card(self):
        data = ca.set_assign(self.path, "Card", ["WU", "BR"], best="BR")
        self.assertEqual(data, {"Card": ["WU", "BR"]})  # Zuordnung wie bisher
        self.assertEqual(ca.load_assign(self.path), {"Card": ["WU", "BR"]})
        self.assertEqual(ca.load_best(self.path), {"Card": "BR"})

    def test_best_joins_the_assignment(self):
        ca.set_assign(self.path, "Card", ["WU"], best="BR")
        self.assertEqual(ca.load_assign(self.path), {"Card": ["WU", "BR"]})

    def test_without_best_the_file_keeps_plain_lists(self):
        ca.set_assign(self.path, "Card", ["WU"])
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), {"Card": ["WU"]})
        self.assertEqual(ca.load_best(self.path), {})

    def test_best_stays_while_still_assigned_and_can_be_cleared(self):
        ca.set_assign(self.path, "Card", ["WU", "BR"], best="BR")
        ca.set_assign(self.path, "Card", ["BR", "RW"])  # ohne Angabe: bleibt, solange zugeordnet
        self.assertEqual(ca.load_best(self.path), {"Card": "BR"})
        ca.set_assign(self.path, "Card", ["RW"])  # nicht mehr zugeordnet: weg
        self.assertEqual(ca.load_best(self.path), {})
        ca.set_assign(self.path, "Card", ["RW"], best="RW")
        ca.set_assign(self.path, "Card", ["RW"], best="")  # leer: bewusst entfernt
        self.assertEqual(ca.load_best(self.path), {})
        self.assertEqual(ca.load_assign(self.path), {"Card": ["RW"]})

    def test_empty_assignment_removes_best_too(self):
        ca.set_assign(self.path, "Card", ["BR"], best="BR")
        self.assertEqual(ca.set_assign(self.path, "Card", [], best=""), {})
        self.assertEqual(ca.load_best(self.path), {})

    def test_unknown_best_is_rejected(self):
        with self.assertRaises(ValueError):
            ca.set_assign(self.path, "Card", ["BR"], best="XX")

    def test_broken_entries_are_ignored(self):
        self.path.write_text(json.dumps({"A": {"arch": ["BR"], "best": "XX"}, "B": {"arch": "BR", "best": "XX"},
                                         "C": {"best": "RW"}, "D": {"arch": ["WU"], "best": "BR"}}),
                             encoding="utf-8")
        self.assertEqual(ca.load_assign(self.path), {"A": ["BR"], "C": ["RW"], "D": ["WU", "BR"]})
        self.assertEqual(ca.load_best(self.path), {"C": "RW", "D": "BR"})


def scores(**pts):
    """detect-Ergebnis mit Punkten je Archetyp (Reihenfolge wie angegeben), main = allein vorn ab 3."""
    s = [{"colors": k, "name": k, "score": v, "assigned": 0} for k, v in pts.items()]
    s.sort(key=lambda x: -x["score"])
    sure = s[0]["score"] >= 3 and (len(s) < 2 or s[0]["score"] > s[1]["score"])
    return {"main": s[0]["colors"] if sure else None, "manual": False, "scores": s}


class BestPackTests(unittest.TestCase):
    def test_level_best_only_in_the_best_archetype(self):
        assign, best = {"Gem": ["BR", "RW"]}, {"Gem": "BR"}
        self.assertEqual(ca.level(card("Gem", "R"), assign, "BR", best), "best")
        self.assertEqual(ca.level(card("Gem", "R"), assign, "RW", best), "arch")
        self.assertEqual(ca.level(card("Gem", "R"), assign, "BR"), "arch")  # ohne Angabe wie bisher

    def test_best_scores_above_a_plain_assignment(self):
        pack = [card("Good", "B"), card("Gem", "R")]
        assign = {"Good": ["BR"], "Gem": ["BR"]}
        ranked = ca.rank(pack, {"Good": "mustplay", "Gem": "mustplay"}, assign, "BR", best={"Gem": "BR"})
        self.assertEqual([c["name"] for c in ranked], ["Gem", "Good"])
        self.assertEqual((ranked[0]["level"], ranked[0]["points"]), ("best", 7))
        self.assertEqual(ranked[0]["best"], "BR")
        self.assertEqual(ranked[1]["best"], "")

    def test_near(self):
        d = scores(BR=6, RW=4, WU=1)
        self.assertEqual(ca.near(d, "BR"), "in")
        self.assertEqual(ca.near(d, "RW"), "near")  # hoechstens 3 Punkte hinter dem besten
        self.assertEqual(ca.near(d, "WU"), "")
        self.assertEqual(ca.near(scores(BR=2, RW=2), "RW"), "near")  # noch offen, gleichauf vorn
        self.assertEqual(ca.near(scores(BR=0, RW=0), "BR"), "")  # ohne Picks kein Hinweis
        self.assertEqual(ca.near(dict(scores(BR=6, RW=1), main="RW", manual=True), "RW"), "in")  # eigene Wahl
        self.assertEqual(ca.near(None, "BR"), "")

    def test_hint_needs_mustplay_or_better_and_the_best_archetype(self):
        pack = [card("MP", "B"), card("Bomb", "R"), card("Filler", "B"), card("Off", "W"), card("Plain", "B")]
        ratings = {"MP": "mustplay", "Bomb": "matchwinner", "Filler": "filler", "Off": "splashworthy",
                   "Plain": "mustplay"}
        assign = {"MP": ["BR"], "Bomb": ["RW"], "Filler": ["BR"], "Off": ["WU"], "Plain": ["BR"]}
        best = {"MP": "BR", "Bomb": "RW", "Filler": "BR", "Off": "WU"}
        d = scores(BR=6, RW=4, WU=0)
        ranked = {c["name"]: c for c in ca.rank(pack, ratings, assign, d["main"], best, d)}
        self.assertEqual(ranked["MP"]["hint"], "in")
        self.assertEqual(ranked["Bomb"]["hint"], "near")
        self.assertEqual(ranked["Filler"]["hint"], "")  # unter MustPlay
        self.assertEqual(ranked["Off"]["hint"], "")  # bester Archetyp weit weg
        self.assertEqual(ranked["Plain"]["hint"], "")  # kein bester Archetyp gesetzt

    def test_rank_without_detect_has_no_hint(self):
        ranked = ca.rank([card("MP", "B")], {"MP": "mustplay"}, {"MP": ["BR"]}, "BR", {"MP": "BR"})
        self.assertEqual(ranked[0]["hint"], "")


class BestLiveTests(LiveTestCase):
    def snap(self, ratings, assign, best):
        with mock.patch.dict(arch.ARCHETYPES, TST):
            return self.live.snapshot(ratings, assign, None, None, best)

    def test_hint_in_the_snapshot(self):
        self.write(notify(1, [201]), pick([201]), notify(2, [202]), pick([202]), notify(3, [101, 102, 103]))
        self.live.step()
        assign = {"Test Gold": ["WB"], "Test Spell": ["WB"], "Test Hasty": ["RW"]}
        best = {"Test Spell": "WB", "Test Hasty": "RW", "Test Gold": "WB"}
        snap = self.snap({"Test Spell": "mustplay", "Test Hasty": "filler"}, assign, best)
        self.assertEqual(snap["detect"]["main"], "WB")
        spell = next(c for c in snap["pack"] if c["name"] == "Test Spell")
        self.assertEqual((spell["level"], spell["best"], spell["hint"]), ("best", "WB", "in"))
        self.assertEqual(snap["hints"], [{"name": "Test Spell", "rating": "mustplay", "best": "WB",
                                          "best_name": "Testgilde", "state": "in"}])
        self.assertEqual(snap["cardbest"], {"Test Spell": "WB", "Test Hasty": "RW", "Test Gold": "WB"})

    def test_no_hint_without_best(self):
        self.write(notify(1, [201]), pick([201]), notify(2, [101, 103]))
        self.live.step()
        snap = self.snap({"Test Spell": "mustplay"}, {"Test Spell": ["WB"]}, {})
        self.assertEqual(snap["hints"], [])
        self.assertEqual(self.live.snapshot({}, {}, None)["hints"], [])  # alter Aufruf ohne best


class BestOverlayTests(unittest.TestCase):
    SNAP = {"status": "pack", "pick": 5, "detect": {"main": "WB", "scores": []},
            "archetypes": [{"colors": "WB", "name": "Testgilde"}, {"colors": "RW", "name": "Rotweiss"}],
            "pack": [{"name": "Test Spell", "colors": ["W"], "rating": "mustplay", "level": "best", "best": "WB",
                      "hint": "in", "arch": ["WB"]},
                     {"name": "Test Bear", "colors": ["W"], "level": "color", "arch": []}],
            "hints": [{"name": "Test Spell", "rating": "mustplay", "best": "WB", "best_name": "Testgilde",
                       "state": "in"}]}

    def test_rows_show_the_top_pick(self):
        rows = overlay.rows_for(self.SNAP)
        hint = [r for r in rows if r[1] == "hint"]
        self.assertTrue(hint)
        self.assertIn("Test Spell", hint[0][0])
        self.assertIn("Testgilde", hint[0][0])
        packrow = next(r for r in rows if r[1] == "best")  # Pack-Zeile der Karte: lila mit ◆
        self.assertTrue(packrow[0].strip().startswith(overlay.MARK["best"]))
        self.assertLess(rows.index(hint[0]), rows.index(packrow))  # Hinweis vor der Pack-Liste

    def test_near_is_named(self):
        snap = dict(self.SNAP, hints=[dict(self.SNAP["hints"][0], state="near")])
        self.assertIn("nahe dran", next(r[0] for r in overlay.rows_for(snap) if r[1] == "hint"))

    def test_mini_rows_show_the_top_pick(self):
        rows = overlay.mini_rows(self.SNAP)
        self.assertTrue(any("Test Spell" in r[0] and r[1] == "hint" for r in rows))

    def test_without_hints_as_before(self):
        snap = dict(self.SNAP, hints=[])
        self.assertFalse([r for r in overlay.rows_for(snap) if r[1] == "hint"])


class BestServerTests(tl.ServerTests):
    """Server wie in test_livedraft; deren Tests laufen dort, nicht hier noch einmal."""
    locals().update({n: None for n in dir(tl.ServerTests) if n.startswith("test_")})

    def test_best_via_api(self):
        status, data = self.post("/api/cardarch", {"name": "Test Bear", "arch": ["WB"], "best": "WB"})
        self.assertEqual(status, 200)
        self.assertEqual(data["cardbest"], {"Test Bear": "WB"})
        self.assertEqual(self.get("/api/pool")["cardbest"], {"Test Bear": "WB"})
        self.assertEqual(self.post("/api/cardarch", {"name": "Test Bear", "arch": ["WB"], "best": "QQ"})[0], 400)
        status, data = self.post("/api/cardarch", {"name": "Test Bear", "arch": ["WB"], "best": ""})
        self.assertEqual(data["cardbest"], {})

    def test_live_carries_best(self):
        self.write(notify(1, [101, 102]))
        self.live.step()
        self.post("/api/cardarch", {"name": "Test Bear", "arch": ["WB"], "best": "WB"})
        self.assertEqual(self.get("/api/live")["cardbest"], {"Test Bear": "WB"})


class BestReportTests(unittest.TestCase):
    NAMES = {"White Bear": 6, "Quick Spell": 4, "Black Bear": 3, "Plains": 9, "Swamp": 7}

    def test_panel_names_the_best_archetype(self):
        from components.report_cards import render_archetype_panel
        from tests.test_archetypes import _deck
        ctx = _deck(self.NAMES, "trk")
        ctx["cardarch"] = {"Black Bear": ["BR"], "White Bear": ["WB", "RW"]}
        self.assertNotIn("Am besten", render_archetype_panel(ctx))
        ctx["cardbest"] = {"White Bear": "WB", "Not In Deck": "BR"}
        html = render_archetype_panel(ctx)
        self.assertIn("Am besten in", html)
        self.assertIn("White Bear", html)
        self.assertNotIn("Not In Deck", html)

    def test_entries_and_build_deck_carry_best(self):
        import mtg_sim
        from components import drafthelper as dh
        from tests.fixtures import args_for
        from tests.test_report_cards import DATA
        pool = [{"name": "A", "qty": 1}, {"name": "B", "qty": 1}]
        entries = dh.variant_entries(pool, [["core"], ["off"]], {}, {}, cardbest={"A": "BR", "Z": "WU"})
        self.assertEqual(entries[0]["cardbest"], {"A": "BR"})
        data = {n: dict(c, set="trk") for n, c in DATA.items()}
        entry = {"name": "T", "deck": dict(self.NAMES), "cardbest": {"Black Bear": "BR"}}
        self.assertEqual(mtg_sim.build_deck(entry, data, args_for(["deck.txt"]))["cardbest"], {"Black Bear": "BR"})


if __name__ == "__main__":
    unittest.main()
