"""Archetyp-Zuordnung je Karte (kartenarchetypen.json), Erkennung des Archetyps und Hervorhebung im Pack."""
import json
import pathlib
import tempfile
import unittest

from components import cardarchetypes as ca

TRK = [{"colors": "WU", "name": "Spacecraft"}, {"colors": "BR", "name": "Sacrifice"},
       {"colors": "RW", "name": "8 Power/Go wide"}, {"colors": "WB", "name": "Artifact Creatures"}]


def card(name, colors, qty=1, land=False):
    return {"name": name, "colors": list(colors), "qty": qty, "land": land}


class FileTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.dir.name) / "kartenarchetypen.json"

    def tearDown(self):
        self.dir.cleanup()

    def test_missing_or_broken_file_is_empty(self):
        self.assertEqual(ca.load_assign(self.path), {})
        self.path.write_text("kaputt", encoding="utf-8")
        self.assertEqual(ca.load_assign(self.path), {})
        self.path.write_text("[1, 2]", encoding="utf-8")
        self.assertEqual(ca.load_assign(self.path), {})

    def test_unknown_pairs_and_empty_lists_are_dropped(self):
        self.path.write_text(json.dumps({"A": ["BR", "XX", "BR"], "B": [], "C": "BR", "D": ["RB"]}),
                             encoding="utf-8")
        self.assertEqual(ca.load_assign(self.path), {"A": ["BR"]})

    def test_set_keeps_several_archetypes_in_pair_order(self):
        data = ca.set_assign(self.path, "Card", ["RW", "WU", "RW"])
        self.assertEqual(data, {"Card": ["WU", "RW"]})
        self.assertEqual(ca.load_assign(self.path), {"Card": ["WU", "RW"]})

    def test_empty_list_removes_the_card(self):
        ca.set_assign(self.path, "Card", ["BR"])
        self.assertEqual(ca.set_assign(self.path, "Card", []), {})

    def test_unknown_pair_is_rejected(self):
        with self.assertRaises(ValueError):
            ca.set_assign(self.path, "Card", ["BX"])
        with self.assertRaises(ValueError):
            ca.set_assign(self.path, "", ["BR"])

    def test_file_is_sorted_and_readable(self):
        ca.set_assign(self.path, "b card", ["BR"])
        ca.set_assign(self.path, "A card", ["WU"])
        text = self.path.read_text(encoding="utf-8")
        self.assertLess(text.index("A card"), text.index("b card"))
        self.assertIn("\n", text)

    def test_not_in_git(self):
        ignore = (pathlib.Path(__file__).resolve().parent.parent / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("kartenarchetypen*.json", ignore)


class DetectTests(unittest.TestCase):
    def test_colors_alone_decide(self):
        cards = [card("a", "B"), card("b", "R"), card("c", "BR"), card("d", "W")]
        r = ca.detect(cards, {}, {}, TRK)
        self.assertEqual(r["main"], "BR")
        self.assertEqual(r["scores"][0]["colors"], "BR")
        self.assertEqual(r["scores"][0]["score"], 3)

    def test_assignment_counts_twice(self):
        cards = [card("a", "W"), card("b", "W"), card("c", "R")]
        # ohne Zuordnung: RW 3, WU 2, WB 2; mit Zuordnung zu WU: WU 2 + 2 = 4
        r = ca.detect(cards, {"a": ["WU"], "b": ["WU"]}, {}, TRK)
        self.assertEqual(r["main"], "WU")
        by = {s["colors"]: s for s in r["scores"]}
        self.assertEqual(by["WU"]["score"], 4)
        self.assertEqual(by["WU"]["assigned"], 2)

    def test_ratings_weight_the_cards(self):
        cards = [card("bomb", "B"), card("x", "W"), card("y", "U")]
        ratings = {"bomb": "splashworthy", "x": "neverplay"}
        by = {s["colors"]: s["score"] for s in ca.detect(cards, {}, ratings, TRK)["scores"]}
        self.assertEqual(by["BR"], 2)   # Splashworthy zaehlt 2
        self.assertEqual(by["WB"], 2)   # NeverPlay zaehlt 0
        self.assertEqual(by["WU"], 1)   # unbewertet zaehlt 1

    def test_copies_lands_and_colorless_cards(self):
        cards = [card("a", "B", qty=2), card("land", "", land=True), card("rock", ""), card("b", "R")]
        by = {s["colors"]: s["score"] for s in ca.detect(cards, {"land": ["BR"], "rock": ["BR"]}, {}, TRK)["scores"]}
        self.assertEqual(by["BR"], 4)  # 2 Kopien + 1 + farblose Karte nur ueber die Zuordnung (Land zaehlt nicht)

    def test_too_few_points_or_tie_is_open(self):
        self.assertIsNone(ca.detect([card("a", "B"), card("b", "R")], {}, {}, TRK)["main"])  # 2 < 3 Punkte
        tie = [card("a", "W"), card("b", "W"), card("c", "W")]
        self.assertIsNone(ca.detect(tie, {}, {}, TRK)["main"])  # WU, RW, WB gleichauf

    def test_manual_choice_wins(self):
        cards = [card("a", "B"), card("b", "R"), card("c", "BR")]
        r = ca.detect(cards, {}, {}, TRK, manual="WU")
        self.assertEqual(r["main"], "WU")
        self.assertTrue(r["manual"])
        self.assertFalse(ca.detect(cards, {}, {}, TRK, manual="GX")["manual"])  # unbekannt: automatisch

    def test_without_archetypes(self):
        r = ca.detect([card("a", "B")], {}, {}, None)
        self.assertEqual(r, {"main": None, "manual": False, "scores": []})

    def test_names_come_along(self):
        r = ca.detect([card("a", "B"), card("b", "R"), card("c", "BR")], {}, {}, TRK)
        self.assertEqual(r["scores"][0]["name"], "Sacrifice")


class PackTests(unittest.TestCase):
    def test_levels(self):
        assign = {"Fodder": ["BR"], "Other": ["WU"]}
        self.assertEqual(ca.level(card("Fodder", "B"), assign, "BR"), "arch")
        self.assertEqual(ca.level(card("Bolt", "R"), assign, "BR"), "color")
        self.assertEqual(ca.level(card("Other", "W"), assign, "BR"), "")
        self.assertEqual(ca.level(card("Gold", "BRG"), assign, "BR"), "")
        self.assertEqual(ca.level(card("Rock", ""), assign, "BR"), "")  # farblos: nur ueber die Zuordnung
        self.assertEqual(ca.level(card("Fodder", "B"), assign, None), "")  # ohne Archetyp nichts hervorheben

    def test_rank_orders_by_rating_archetype_and_color(self):
        pack = [card("Filler off", "W"), card("Bomb off", "U"), card("MP arch", "B"), card("Unrated color", "R"),
                card("Never arch", "B"), card("Filler arch", "R")]
        ratings = {"Filler off": "filler", "Bomb off": "splashworthy", "MP arch": "mustplay", "Never arch": "neverplay",
                   "Filler arch": "filler"}
        assign = {"MP arch": ["BR"], "Never arch": ["BR"], "Filler arch": ["BR"]}
        ranked = ca.rank(pack, ratings, assign, "BR")
        self.assertEqual([c["name"] for c in ranked],
                         ["MP arch", "Bomb off", "Filler arch", "Unrated color", "Filler off", "Never arch"])
        self.assertEqual(ranked[-1]["points"], 0)  # NeverPlay bleibt unten, auch im Archetyp
        top = ranked[0]
        self.assertEqual((top["level"], top["rating"], top["points"]), ("arch", "mustplay", 6))
        self.assertEqual(top["arch"], ["BR"])

    def test_rank_without_archetype_uses_ratings(self):
        pack = [card("a", "W"), card("b", "U")]
        ranked = ca.rank(pack, {"b": "mustplay"}, {}, None)
        self.assertEqual([c["name"] for c in ranked], ["b", "a"])
        self.assertEqual(ranked[1]["points"], 1.5)

    def test_rank_keeps_card_fields(self):
        ranked = ca.rank([dict(card("a", "W"), image="x.jpg")], {}, {}, None)
        self.assertEqual(ranked[0]["image"], "x.jpg")


class ReportTests(unittest.TestCase):
    """Bericht: erkannter Archetyp aus der eigenen Zuordnung im Archetyp-Kasten."""
    NAMES = {"White Bear": 6, "Quick Spell": 4, "Black Bear": 3, "Plains": 9, "Swamp": 7}

    def test_panel_shows_assignment_and_detection(self):
        from components.report_cards import render_archetype_panel
        from tests.test_archetypes import _deck
        ctx = _deck(self.NAMES, "trk")
        self.assertNotIn("Deine Zuordnung", render_archetype_panel(ctx))  # ohne Zuordnung wie bisher
        ctx["cardarch"] = {"Black Bear": ["BR"], "White Bear": ["WB", "RW"]}
        html = render_archetype_panel(ctx)
        self.assertIn("Deine Zuordnung", html)
        self.assertIn("Artifact Creatures: 6 Karten", html)
        self.assertIn("Sacrifice: 3 Karten", html)
        self.assertIn("Erkannt", html)

    def test_entries_carry_the_assignment(self):
        from components import drafthelper as dh
        pool = [{"name": "A", "qty": 1}, {"name": "B", "qty": 1}]
        entries = dh.variant_entries(pool, [["core"], ["off"]], {}, {}, cardarch={"A": ["BR"], "Z": ["WU"]})
        self.assertEqual(entries[0]["cardarch"], {"A": ["BR"]})

    def test_build_deck_passes_the_assignment(self):
        import mtg_sim
        from tests.fixtures import args_for
        from tests.test_report_cards import DATA
        data = {n: dict(c, set="trk") for n, c in DATA.items()}
        entry = {"name": "T", "deck": dict(self.NAMES), "cardarch": {"Black Bear": ["BR"]}}
        self.assertEqual(mtg_sim.build_deck(entry, data, args_for(["deck.txt"]))["cardarch"], {"Black Bear": ["BR"]})


if __name__ == "__main__":
    unittest.main()
