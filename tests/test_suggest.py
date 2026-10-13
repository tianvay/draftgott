import unittest

from components.suggest import suggest


def card(name, qty=1, colors=(), mv=0, land=False, section="deck"):
    return {"name": name, "qty": qty, "section": section, "colors": list(colors), "mv": float(mv), "land": land}


def run(cards, marks=None, basics=None, cats=None, target=40, sort="mv"):
    marks = marks if marks is not None else [["off"] * c["qty"] for c in cards]
    return suggest(cards, marks, basics or {}, cats or {}, target, sort)


def marks_of(result, cards, name):
    return result["marks"][[c["name"] for c in cards].index(name)]


class CategoryRulesTests(unittest.TestCase):
    def setUp(self):
        self.cards = [card("Must", 2, "W", 2), card("Worthy", 1, "B", 3), card("Never", 1, "W", 1),
                      card("Plain", 2, "W", 2)]
        self.cats = {"Must": "mustplay", "Worthy": "splashworthy", "Never": "neverplay"}
        self.marks = [["off", "off"], ["off"], ["core"], ["splash", "nosplash"]]
        self.result = run(self.cards, self.marks, cats=self.cats)

    def test_mustplay_goes_to_core(self):
        self.assertEqual(marks_of(self.result, self.cards, "Must"), ["core", "core"])

    def test_splashworthy_goes_to_splash(self):
        self.assertEqual(marks_of(self.result, self.cards, "Worthy"), ["splash"])

    def test_neverplay_goes_to_off(self):
        self.assertEqual(marks_of(self.result, self.cards, "Never"), ["off"])

    def test_cards_without_category_keep_their_marks(self):
        self.assertEqual(marks_of(self.result, self.cards, "Plain"), ["splash", "nosplash"])

    def test_input_marks_are_not_modified(self):
        self.assertEqual(self.marks, [["off", "off"], ["off"], ["core"], ["splash", "nosplash"]])


class FillTests(unittest.TestCase):
    def test_filler_fills_core_up_to_target_counting_basic_lands(self):
        cards = [card("Must", 2, "W", 2)] + [card(f"F{i}", 1, "W", i) for i in range(1, 6)]
        cats = {"Must": "mustplay", **{f"F{i}": "filler" for i in range(1, 6)}}
        # Core: 2 MustPlay + 3 Standardlaender = 5, Ziel 8 -> 3 Filler
        r = run(cards, basics={"Plains": {"core": 3, "splash": 0, "nosplash": 0}}, cats=cats, target=8)
        chosen = [n for n in ("F1", "F2", "F3", "F4", "F5") if marks_of(r, cards, n) == ["core"]]
        self.assertEqual(chosen, ["F1", "F2", "F3"])  # Sortierung Manawert: guenstigste zuerst
        self.assertEqual(marks_of(r, cards, "F4"), ["off"])
        self.assertEqual(marks_of(r, cards, "F5"), ["off"])
        self.assertEqual(r["summary"]["sizes"], {"splash": 8, "nosplash": 8})

    def test_unused_filler_is_set_to_off(self):
        cards = [card("F1", 2, "W", 1)]
        r = run(cards, marks=[["core", "core"]], cats={"F1": "filler"}, target=0 + 1)
        self.assertEqual(sorted(marks_of(r, cards, "F1")), ["core", "off"])

    def test_splash_group_is_matched_by_filler_in_nosplash_group(self):
        # Core: 3 MustPlay + 3 Basics = 6; Splash-Gruppe 2 -> Splash-Variante 8, NoSplash-Variante 6, Ziel 10
        cards = [card("Must", 3, "W", 2), card("Worthy", 2, "B", 3)] + [card(f"F{i}", 1, "W", i) for i in range(1, 7)]
        cats = {"Must": "mustplay", "Worthy": "splashworthy", **{f"F{i}": "filler" for i in range(1, 7)}}
        r = run(cards, basics={"Plains": {"core": 3, "splash": 0, "nosplash": 0}}, cats=cats, target=10)
        in_core = [n for n in ("F1", "F2", "F3", "F4", "F5", "F6") if marks_of(r, cards, n) == ["core"]]
        in_nosplash = [n for n in ("F1", "F2", "F3", "F4", "F5", "F6") if marks_of(r, cards, n) == ["nosplash"]]
        self.assertEqual(in_core, ["F1", "F2"])        # Core zuerst: in beiden Varianten noetig
        self.assertEqual(in_nosplash, ["F3", "F4"])    # Ersatz fuer die Splash-Karten
        self.assertEqual(r["summary"]["sizes"], {"splash": 10, "nosplash": 10})
        self.assertEqual(r["summary"]["warnings"], [])

    def test_not_enough_filler_reports_shortfall(self):
        cards = [card("Must", 2, "W", 2), card("F1", 1, "W", 1)]
        r = run(cards, cats={"Must": "mustplay", "F1": "filler"}, target=10)
        self.assertEqual(r["summary"]["sizes"], {"splash": 3, "nosplash": 3})
        self.assertTrue(any("Nicht genug Filler" in w for w in r["summary"]["warnings"]))

    def test_core_over_target_fills_nothing_and_warns(self):
        cards = [card("Must", 4, "W", 2), card("F1", 1, "W", 1)]
        r = run(cards, cats={"Must": "mustplay", "F1": "filler"}, target=3)
        self.assertEqual(marks_of(r, cards, "F1"), ["off"])
        self.assertTrue(any("über dem Ziel" in w for w in r["summary"]["warnings"]))

    def test_second_run_gives_same_result(self):
        cards = [card("Must", 2, "W", 2), card("Worthy", 1, "B", 3)] + [card(f"F{i}", 1, "W", i) for i in range(1, 5)]
        cats = {"Must": "mustplay", "Worthy": "splashworthy", **{f"F{i}": "filler" for i in range(1, 5)}}
        first = run(cards, cats=cats, target=6)
        second = run(cards, marks=first["marks"], cats=cats, target=6)
        self.assertEqual(first["marks"], second["marks"])

    def test_no_categories_changes_nothing(self):
        cards = [card("A", 2, "W", 2)]
        marks = [["core", "off"]]
        r = run(cards, marks=marks)
        self.assertEqual(r["marks"], marks)


class FillerOrderTests(unittest.TestCase):
    def setUp(self):
        self.base = [card("Must", 1, "W", 2)]
        self.cats = {"Must": "mustplay"}

    def pick(self, extra, target, sort, marks_extra=None, basics=None):
        cards = self.base + extra
        cats = dict(self.cats, **{c["name"]: "filler" for c in extra})
        marks = [["off"]] + (marks_extra or [["off"] * c["qty"] for c in extra])
        r = run(cards, marks=marks, basics=basics, cats=cats, target=target, sort=sort)
        return [c["name"] for c in extra if marks_of(r, cards, c["name"]) != ["off"] * c["qty"]]

    def test_sort_by_mana_value_cheapest_first(self):
        extra = [card("C3", 1, "W", 3), card("C1", 1, "W", 1), card("C2", 1, "W", 2)]
        self.assertEqual(self.pick(extra, 3, "mv"), ["C1", "C2"])

    def test_sort_by_name(self):
        extra = [card("Zeta", 1, "W", 1), card("Alpha", 1, "W", 5), card("Mike", 1, "W", 2)]
        self.assertEqual(self.pick(extra, 3, "name"), ["Alpha", "Mike"])

    def test_sort_by_color_follows_color_order(self):
        extra = [card("Red", 1, "R", 1), card("Blue", 1, "U", 1), card("White", 1, "W", 4)]
        self.assertEqual(self.pick(extra, 3, "color"), ["Blue", "White"])  # W U B R G: Weiss und Blau vor Rot

    def test_ties_prefer_colors_already_in_the_deck(self):
        # Sortierung "Kategorie": alle gleich -> Farbe schlaegt Manawert; Core enthaelt Weiss
        extra = [card("BlueCheap", 1, "U", 1), card("WhitePricey", 1, "W", 4)]
        self.assertEqual(self.pick(extra, 2, "cat"), ["WhitePricey"])

    def test_then_mana_value_ascending(self):
        extra = [card("W4", 1, "W", 4), card("W2", 1, "W", 2), card("W3", 1, "W", 3)]
        self.assertEqual(self.pick(extra, 3, "cat"), ["W2", "W3"])

    def test_colorless_counts_as_present(self):
        extra = [card("Blue1", 1, "U", 1), card("Gray3", 1, "", 3)]
        self.assertEqual(self.pick(extra, 2, "cat"), ["Gray3"])

    def test_sort_by_current_mark_prefers_cards_already_in_core(self):
        extra = [card("A", 1, "W", 1), card("B", 1, "W", 1)]
        self.assertEqual(self.pick(extra, 2, "mark", marks_extra=[["off"], ["core"]]), ["B"])

    def test_lands_come_after_spells_when_sorting_by_mana_value(self):
        extra = [card("Annex", 1, "", 0, land=True), card("Spell", 1, "W", 4)]
        self.assertEqual(self.pick(extra, 2, "mv"), ["Spell"])

    def test_nonbasic_land_counts_toward_size(self):
        extra = [card("Annex", 1, "", 0, land=True)]
        cards = self.base + extra
        r = run(cards, cats={"Must": "mustplay", "Annex": "filler"}, target=2)
        self.assertEqual(marks_of(r, cards, "Annex"), ["core"])


class MultiCopyTests(unittest.TestCase):
    def test_copies_of_one_card_can_be_split_between_core_and_nosplash(self):
        cards = [card("Worthy", 1, "B", 3), card("Must", 1, "W", 2), card("F", 3, "W", 1)]
        cats = {"Worthy": "splashworthy", "Must": "mustplay", "F": "filler"}
        r = run(cards, cats=cats, target=3)
        # Core: Must (1); Splash: Worthy (1) -> Splash 2, NoSplash 1, Ziel 3: 1 Filler in Core, 1 in NoSplash
        self.assertEqual(sorted(marks_of(r, cards, "F")), ["core", "nosplash", "off"])
        self.assertEqual(r["summary"]["sizes"], {"splash": 3, "nosplash": 3})


if __name__ == "__main__":
    unittest.main()
