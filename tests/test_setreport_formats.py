"""Setauswertung nach Format: Pick Two (4 Siege / 2 Niederlagen) und Pick One (Premier, Quick: 7 / 3) getrennt,
Run-Stand, Verteilung der Siege, Siegquote je Match-Nummer, Spieltempo, Pick-Two-Duos, Formatvorteil je Karte,
Format-Schalter und Run-Leiter in der HTML-Seite."""
import unittest

from components import draftstats as ds
from components import setreport
from tests.i18n_check import english, german_leftovers

P2, P1 = "PickTwoDraft_TRK_20261110", "PremierDraft_TRK_20261110"


def match(i, win, deck, games=None, stats=None):
    m = {"id": str(i), "deck": deck, "games": games if games is not None else ([win] if win is not None else []),
         "win": win}
    if stats:
        m["game_stats"] = stats
    return m


def two_formats():
    """Pick Two: 4-1 (Trophaee, mit Duo A+B) und 0-2; Premier: 3-3 (laeuft noch, A ohne B) und 7-0."""
    deck = {"A": 1, "B": 1, "Plains": 8}
    p2a = {"event": P2, "set": "TRK", "started": "2026-11-10", "picks": ["A", "B", "C", "D"],
           "pick_sizes": [14, 14, 12, 12], "deck": {"main": deck, "side": {}},
           "matches": [match(1, True, deck, stats={"1": {"turns": 10, "spells": 6, "kills": 2, "damage_dealt": 20}}),
                       match(2, False, deck, stats={"1": {"turns": 16, "spells": 8, "kills": 1, "damage_dealt": 9}}),
                       match(3, True, deck), match(4, True, deck), match(5, True, deck)]}
    p2b = {"event": P2, "set": "TRK", "started": "2026-11-11", "picks": ["A", "C"], "pick_sizes": [14, 14],
           "deck": {"main": {"C": 1}, "side": {}},
           "matches": [match(6, False, {"C": 1}), match(7, False, {"C": 1})]}
    p1a = {"event": P1, "set": "TRK", "started": "2026-11-12", "picks": ["A", "B"], "pick_sizes": [14, 13],
           "deck": {"main": {"A": 1}, "side": {}},
           "matches": [match(10 + i, w, {"A": 1}) for i, w in enumerate([True, False, True, False, True, False])]
           + [match(20, None, {"A": 1})]}
    p1b = {"event": "QuickDraft_TRK_1", "set": "TRK", "started": "2026-11-13", "picks": [], "pick_sizes": [],
           "deck": {"main": {"A": 1}, "side": {}}, "matches": [match(30 + i, True, {"A": 1}) for i in range(7)]}
    return {"version": 1, "drafts": [p2a, p2b, p1a, p1b]}


class FormatStatsTests(unittest.TestCase):
    def test_event_format(self):
        self.assertEqual(ds.event_format(P2), "picktwo")
        self.assertEqual(ds.event_format(P1), "pickone")
        self.assertEqual(ds.event_format("QuickDraft_TRK_1"), "pickone")
        self.assertEqual(ds.event_format("TradDraft_TRK_1"), "trad")
        self.assertEqual(ds.event_format("Sealed_TRK_1"), "sealed")
        self.assertEqual(ds.event_format(None), "pickone")
        self.assertEqual((ds.FORMATS["picktwo"]["wins"], ds.FORMATS["picktwo"]["losses"]), (4, 2))
        self.assertEqual((ds.FORMATS["pickone"]["wins"], ds.FORMATS["pickone"]["losses"]), (7, 3))

    def test_run_state(self):
        p2a, p2b, p1a, p1b = two_formats()["drafts"]
        self.assertEqual(ds.run_state(p2a), {"format": "picktwo", "wins": 4, "losses": 1, "open": 0, "done": True,
                                             "trophy": True})
        self.assertTrue(ds.run_state(p2b)["done"])  # 2 Niederlagen: raus
        self.assertFalse(ds.run_state(p2b)["trophy"])
        s = ds.run_state(p1a)
        self.assertEqual((s["wins"], s["losses"], s["open"], s["done"]), (3, 3, 1, True))  # 3 Niederlagen bei Pick One
        p1a["matches"] = p1a["matches"][:5]
        self.assertFalse(ds.run_state(p1a)["done"])  # 3-2: laeuft noch
        self.assertTrue(ds.run_state(p1b)["trophy"])
        trad = {"event": "TradDraft_TRK_1", "matches": [match(1, True, {}), match(2, False, {}), match(3, True, {})]}
        self.assertTrue(ds.run_state(trad)["done"])  # Traditional: 3 Matches

    def test_formats_in(self):
        self.assertEqual(ds.formats_in(two_formats(), "TRK"), ["picktwo", "pickone"])
        self.assertEqual(ds.formats_in(two_formats(), "FRA"), [])

    def test_format_summary(self):
        s = ds.format_summary(two_formats(), "TRK")
        p2, p1 = s["picktwo"], s["pickone"]
        self.assertEqual((p2["runs"], p2["done"], p2["trophies"]), (2, 2, 1))
        self.assertEqual(p2["dist"], [1, 0, 0, 0, 1])
        self.assertEqual(p2["avg_wins"], 2)
        self.assertEqual((p2["matches"], p2["match_wins"]), (7, 4))
        self.assertEqual(p2["by_match"][0], [1, 2])  # Match 1: 1 von 2 gewonnen
        self.assertEqual(p2["by_match"][1], [0, 2])
        self.assertEqual(len(p1["dist"]), 8)
        self.assertEqual(p1["dist"][3] + p1["dist"][7], 2)
        self.assertEqual(p1["avg_wins"], 5)
        self.assertEqual(p2["tempo"]["win"], {"games": 1, "turns": 10, "spells": 6, "kills": 2, "damage_dealt": 20})
        self.assertEqual(p2["tempo"]["loss"]["turns"], 16)
        self.assertEqual(p1["tempo"]["win"], {"games": 0})

    def test_card_stats_by_format(self):
        p2 = ds.card_stats(two_formats(), "TRK", fmt="picktwo")
        p1 = ds.card_stats(two_formats(), "TRK", fmt="pickone")
        self.assertEqual((p2["A"]["games"], p2["A"]["wins"]), (5, 4))
        self.assertEqual((p1["A"]["games"], p1["A"]["wins"]), (13, 10))
        self.assertNotIn("C", p1)
        self.assertEqual(ds.card_stats(two_formats(), "TRK")["A"]["games"], 18)

    def test_pick_pairs(self):
        p2a, p2b, p1a, _ = two_formats()["drafts"]
        self.assertEqual(ds.pick_pairs(p2a), [("A", "B"), ("C", "D")])
        self.assertEqual(ds.pick_pairs(p2b), [("A", "C")])
        self.assertEqual(ds.pick_pairs(p1a), [])  # Pick One: keine Paare
        odd = dict(p2a, picks=["A", "B", "Z", "C", "D"], pick_sizes=[14, 14, 13, 12, 12])
        self.assertEqual(ds.pick_pairs(odd), [("A", "B"), ("C", "D")])
        self.assertEqual(ds.pick_pairs(dict(p2a, picks=["A", "Plains", "C", "C"])), [])

    def test_pair_stats(self):
        pairs = ds.pair_stats(two_formats(), "TRK")
        ab = pairs[("A", "B")]
        self.assertEqual((ab["count"], ab["decks"], ab["games"], ab["wins"]), (1, 1, 5, 4))
        self.assertEqual(pairs[("A", "C")]["decks"], 0)
        self.assertNotIn(("A", "B"), {k for k, v in pairs.items() if v["count"] > 1})


CARDS = {n: {"name": n, "colors": ["W"], "mana_cost": "{W}", "rarity": "common", "type_line": "Creature"}
         for n in "ABCD"}


def render(data=None, cards=CARDS):
    return setreport.render_set_report(data or two_formats(), "TRK", cards, {"A": ["WU"]}, {"A": "mustplay"})


class FormatReportTests(unittest.TestCase):
    def test_format_switch_and_views(self):
        html = render()
        self.assertIn('class="fswitch"', html)
        for key in ("all", "picktwo", "pickone"):
            self.assertIn(f'data-view="{key}"', html)
        self.assertEqual(html.count('class="cards"'), 3)  # je Ansicht eine Kartentabelle
        self.assertIn("Pick Two", html)
        self.assertIn("Pick One", html)

    def test_no_switch_with_one_format(self):
        data = two_formats()
        data["drafts"] = data["drafts"][:2]
        html = render(data)
        self.assertNotIn('class="fswitch"', html)
        self.assertEqual(html.count('class="cards"'), 1)

    def test_format_panels(self):
        html = render()
        self.assertIn('class="fpanel f-picktwo"', html)
        self.assertIn('class="fpanel f-pickone"', html)
        self.assertIn("4 Siege / 2 Niederlagen", html)
        self.assertIn("7 Siege / 3 Niederlagen", html)
        self.assertIn("1 Trophäe", html)

    def test_run_ladder(self):
        html = render()
        self.assertEqual(html.count('class="run f-'), 4 + 2 + 2)  # 4 Runs in Alle, je 2 im Format
        self.assertIn('class="trophy on"', html)  # 4-1 bei Pick Two
        self.assertIn("ausgeschieden", html)
        # Pick Two hat 2 Leben, Pick One 3
        runs = html.split('<div class="run ')[1:]
        p2 = next(r for r in runs if r.startswith("f-picktwo"))
        p1 = next(r for r in runs if r.startswith("f-pickone"))
        self.assertEqual(p2.count('class="life'), 2)
        self.assertEqual(p1.count('class="life'), 3)
        self.assertEqual(p2.count('class="stp'), 4)  # 4 Siege bis zur Trophaee
        self.assertEqual(p1.count('class="stp'), 7)

    def test_distribution_and_by_match(self):
        html = render()
        self.assertIn('id="formate"', html)
        self.assertIn('class="dist"', html)
        self.assertIn('class="bymatch"', html)
        self.assertIn("Spieltempo", html)

    def test_duos(self):
        html = render()
        self.assertIn('id="duos"', html)
        self.assertIn("A + B", html)

    def test_format_edge_section(self):
        data = two_formats()
        html = render(data)
        self.assertIn('id="formatvorteil"', html)

    def test_scatter(self):
        self.assertNotIn('class="scatter"', render())  # nur A hat genug Games
        data = two_formats()
        for m in data["drafts"][3]["matches"]:
            m["deck"] = {"A": 1, "B": 1, "C": 1, "D": 1}
        html = render(data)
        self.assertIn('class="scatter"', html)
        self.assertEqual(html.count("<circle"), 4)  # nur Alle: A-D; in den Formaten zu wenige mit Pick und 6 Games

    def test_english(self):
        with english():
            html = render()
            self.assertEqual(german_leftovers(html, allow=["Spacecraft"]), [])
            self.assertIn("4 wins / 2 losses", html)

    def test_german_unchanged_after_english(self):
        before = render()
        with english():
            render()
        self.assertEqual(render(), before)


if __name__ == "__main__":
    unittest.main()
