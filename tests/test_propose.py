import unittest

from components.suggest import land_range, propose

BASICS = ("Plains", "Island", "Swamp", "Mountain", "Forest")


def card(name, qty=1, colors="", mv=1, land=False, cost=None):
    colors = list(colors)
    if cost is None:
        cost = "" if land else "".join("{%s}" % c for c in colors)
    return {"name": name, "qty": qty, "section": "deck", "colors": colors, "mv": float(mv), "land": land,
            "cost": cost}


def run(cards, cats, colors="WB", target=40, sort="mv", marks=None):
    marks = marks if marks is not None else [["off"] * c["qty"] for c in cards]
    return propose(cards, marks, cats, list(colors), target, sort)


def basics_in(deck):
    return {n: q for n, q in deck.items() if n in BASICS}


def total(deck):
    return sum(deck.values())


class LandRangeTests(unittest.TestCase):
    def test_rule_of_thumb_for_40_and_60_cards(self):
        self.assertEqual(land_range(40), (15, 17, 17))
        self.assertEqual(land_range(60), (20, 24, 22))

    def test_range_is_ordered_for_odd_sizes(self):
        for size in (10, 25, 80, 100, 200):
            low, high, rec = land_range(size)
            self.assertTrue(low <= rec <= high, (size, low, rec, high))


class ColorRuleTests(unittest.TestCase):
    def setUp(self):
        self.cards = [
            card("WhiteMust", 1, "W", 2), card("RedMust", 1, "R", 2), card("GrayMust", 1, "", 2),
            card("GoldMust", 1, "WB", 3), card("GoldOff", 1, "WR", 3),
            card("WhiteFill", 1, "W", 1), card("RedFill", 1, "R", 1),
        ]
        self.cats = {"WhiteMust": "mustplay", "RedMust": "mustplay", "GrayMust": "mustplay",
                     "GoldMust": "mustplay", "GoldOff": "mustplay", "WhiteFill": "filler", "RedFill": "filler"}

    def test_mustplay_and_filler_only_in_chosen_colors(self):
        deck = run(self.cards, self.cats, "WB", target=40)["deck"]
        for name in ("WhiteMust", "GrayMust", "GoldMust", "WhiteFill"):
            self.assertEqual(deck.get(name), 1, name)
        for name in ("RedMust", "GoldOff", "RedFill"):
            self.assertNotIn(name, deck)

    def test_no_chosen_color_leaves_only_colorless_cards(self):
        deck = run(self.cards, self.cats, "", target=40)["deck"]
        self.assertEqual({n for n in deck if n not in BASICS}, {"GrayMust"})


class CategoryRuleTests(unittest.TestCase):
    def setUp(self):
        self.cards = [card("InColorWorthy", 1, "W", 3), card("OffColorWorthy", 2, "R", 3), card("Never", 1, "W", 1),
                      card("Plain", 1, "W", 1), card("Must", 2, "W", 2)]
        self.cats = {"InColorWorthy": "splashworthy", "OffColorWorthy": "splashworthy", "Never": "neverplay",
                     "Must": "mustplay"}
        self.result = run(self.cards, self.cats, "WB")

    def test_splashworthy_in_chosen_colors_is_a_normal_card(self):
        self.assertEqual(self.result["deck"]["InColorWorthy"], 1)
        self.assertNotIn("InColorWorthy", self.result["summary"]["splash_cards"])

    def test_splashworthy_outside_chosen_colors_is_splashed(self):
        self.assertEqual(self.result["deck"]["OffColorWorthy"], 2)
        self.assertEqual(self.result["summary"]["splash_cards"], {"OffColorWorthy": 2})

    def test_neverplay_and_uncategorized_cards_are_not_included(self):
        self.assertNotIn("Never", self.result["deck"])
        self.assertNotIn("Plain", self.result["deck"])

    def test_number_of_ignored_copies_is_reported(self):
        self.assertEqual(self.result["summary"]["ignored"], 1)


class LandTests(unittest.TestCase):
    def spells(self, n, color="W"):
        return [card(f"S{i}", 1, color, 1 + i % 4) for i in range(n)]

    def test_basic_lands_fill_up_to_recommended_count(self):
        cards = self.spells(30)
        cats = {c["name"]: "filler" for c in cards}
        r = run(cards, cats, "W", target=40)
        self.assertEqual(sum(basics_in(r["deck"]).values()), 17)
        self.assertEqual(total(r["deck"]), 40)
        self.assertEqual(r["summary"]["lands"], 17)
        self.assertEqual(r["summary"]["hints"], [])

    def test_nonbasic_lands_count_as_lands(self):
        cards = self.spells(30) + [card("Annex", 2, "", 0, land=True)]
        cats = {c["name"]: "filler" for c in cards}
        cats["Annex"] = "mustplay"
        r = run(cards, cats, "W", target=40)
        self.assertEqual(r["deck"]["Annex"], 2)
        self.assertEqual(sum(basics_in(r["deck"]).values()), 15)
        self.assertEqual(r["summary"]["lands"], 17)
        self.assertEqual(total(r["deck"]), 40)

    def test_sixty_card_deck_uses_22_lands(self):
        cards = self.spells(60)
        r = run(cards, {c["name"]: "filler" for c in cards}, "W", target=60)
        self.assertEqual(r["summary"]["lands"], 22)
        self.assertEqual(total(r["deck"]), 60)

    def test_hint_when_nonbasic_lands_exceed_the_range(self):
        cards = self.spells(30) + [card("Annex", 20, "", 0, land=True)]
        cats = {"Annex": "mustplay"}
        r = run(cards, cats, "W", target=40)
        self.assertEqual(r["summary"]["lands"], 20)
        self.assertTrue(any("Länder" in h and "15 bis 17" in h for h in r["summary"]["hints"]))

    def test_lands_are_filled_even_when_there_are_too_few_spells(self):
        # nur 1 Zauber und kein Filler: Laender werden trotzdem aufgefuellt, das Deck bleibt aber klein
        cards = [card("A", 1, "W", 1)]
        r = run(cards, {"A": "mustplay"}, "W", target=40)
        self.assertEqual(r["summary"]["lands"], 17)
        self.assertTrue(any("Nicht genug Filler" in w for w in r["summary"]["warnings"]))
        self.assertEqual(total(r["deck"]), 18)

    def test_no_basic_land_is_added_for_a_deck_of_only_nonbasic_lands_over_target(self):
        cards = [card("Annex", 30, "", 0, land=True)]
        r = run(cards, {"Annex": "mustplay"}, "W", target=40)
        self.assertEqual(basics_in(r["deck"]), {})


class BasicDistributionTests(unittest.TestCase):
    def test_basics_follow_color_weights(self):
        cards = [card(f"W{i}", 1, "W", 2, cost="{1}{W}{W}") for i in range(10)] + \
                [card(f"B{i}", 1, "B", 2, cost="{1}{B}") for i in range(5)]
        r = run(cards, {c["name"]: "filler" for c in cards}, "WB", target=30)
        b = basics_in(r["deck"])
        self.assertGreater(b.get("Plains", 0), b.get("Swamp", 0))
        self.assertEqual(set(b), {"Plains", "Swamp"})  # nur gewaehlte Farben mit Karten

    def test_unchosen_colors_get_no_basic_lands(self):
        cards = [card(f"W{i}", 1, "W", 2) for i in range(20)]
        r = run(cards, {c["name"]: "filler" for c in cards}, "WU", target=40)
        self.assertEqual(set(basics_in(r["deck"])), {"Plains"})

    def test_splash_color_gets_a_few_sources(self):
        cards = [card(f"W{i}", 1, "W", 2) for i in range(25)] + [card("RedBomb", 1, "R", 4)]
        cats = {c["name"]: "filler" for c in cards}
        cats["RedBomb"] = "splashworthy"
        r = run(cards, cats, "W", target=40)
        b = basics_in(r["deck"])
        self.assertIn(b.get("Mountain", 0), (2, 3, 4))
        self.assertEqual(sum(b.values()), 17)

    def test_distribution_sums_to_requested_basics(self):
        cards = [card(f"A{i}", 1, "WU", 2) for i in range(12)] + [card(f"B{i}", 1, "B", 2) for i in range(12)]
        r = run(cards, {c["name"]: "filler" for c in cards}, "WUB", target=40)
        self.assertEqual(sum(basics_in(r["deck"]).values()), 17)


class FillOrderAndSizeTests(unittest.TestCase):
    def _pool(self):
        cards = [card("Must", 1, "W", 2)] + [card(f"F{i:02d}", 1, "W", 1 + i % 6) for i in range(30)]
        cats = {"Must": "mustplay", **{c["name"]: "filler" for c in cards[1:]}}
        return cards, cats

    def test_filler_order_follows_sort_then_mana_value(self):
        cards, cats = self._pool()
        r = run(cards, cats, "W", target=40)  # 17 Laender + Must + 22 Filler
        inc = [c for c in cards[1:] if c["name"] in r["deck"]]
        exc = [c for c in cards[1:] if c["name"] not in r["deck"]]
        self.assertEqual(len(inc), 22)
        self.assertLessEqual(max(c["mv"] for c in inc), min(c["mv"] for c in exc))

    def test_filler_follows_name_sort(self):
        cards, cats = self._pool()
        r = run(cards, cats, "W", target=40, sort="name")
        chosen = {n for n in r["deck"] if n.startswith("F")}
        self.assertEqual(chosen, {f"F{i:02d}" for i in range(22)})

    def test_deck_has_target_size_when_enough_filler(self):
        cards = [card(f"S{i}", 1, "W", 1 + i % 5) for i in range(40)]
        r = run(cards, {c["name"]: "filler" for c in cards}, "W", target=40)
        self.assertEqual(total(r["deck"]), 40)
        self.assertEqual(r["summary"]["warnings"], [])

    def test_inputs_are_not_modified_and_result_is_deterministic(self):
        cards = [card(f"S{i}", 2, "W", 1 + i % 3) for i in range(10)]
        cats = {c["name"]: "filler" for c in cards}
        marks = [["off", "off"] for _ in cards]
        first = propose(cards, marks, cats, ["W"], 40, "mv")
        second = propose(cards, marks, cats, ["W"], 40, "mv")
        self.assertEqual(first, second)
        self.assertEqual(marks, [["off", "off"] for _ in cards])
        self.assertEqual(cats, {c["name"]: "filler" for c in cards})


if __name__ == "__main__":
    unittest.main()
