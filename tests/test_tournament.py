"""Turniermodus (components/tournament.py): Gegnerdecks eines Ordners spielen gegeneinander, je Paarung viele Spiele."""
import io
import pathlib
import random
import tempfile
import unittest
from unittest import mock

from components import battle as battle_mod
from components import tournament as tm
from components.cards import card_info
from tests.fixtures import CARDS
from tests.i18n_check import english, german_leftovers


def lands(n=40):  # nur Laender: jede Hand ist ein Mulligan
    return [card_info(CARDS["Plains"])[0]] * n


class StarterTests(unittest.TestCase):
    def test_loser_starts_next_game(self):  # 103.1: der Verlierer waehlt und geht zuerst
        self.assertEqual(tm.next_starter("x", "x"), "y")
        self.assertEqual(tm.next_starter("x", "y"), "x")
        self.assertEqual(tm.next_starter("y", "y"), "x")
        self.assertEqual(tm.next_starter("y", "x"), "y")

    def test_draw_keeps_starter(self):  # Unentschieden: wer gewaehlt hat, waehlt wieder
        self.assertEqual(tm.next_starter("x", None), "x")
        self.assertEqual(tm.next_starter("y", None), "y")


class MatchTests(unittest.TestCase):
    def test_counts_and_starters(self):
        winners = iter(["a", "a", "b", None, "b"])  # a = Deck x
        calls = []

        def fake(cards_a, cards_b, a_starts, max_turns, mulligan, min_hand, a_never_concede=False):
            calls.append((a_starts, a_never_concede))
            return {"winner": next(winners), "round": 7}

        rng = random.Random(0)
        with mock.patch.object(rng, "choice", return_value="x"):
            m = tm.play_match(["X"], ["Y"], 5, game=fake, rng=rng)
        # Spiel 1 x beginnt (Zufall), x gewinnt -> y beginnt, x gewinnt -> y beginnt, y gewinnt -> x beginnt,
        # unentschieden -> x beginnt wieder, y gewinnt
        self.assertEqual([c[0] for c in calls], [True, False, False, True, True])
        self.assertTrue(all(c[1] for c in calls))  # beide geben beim Mulligan nie auf
        self.assertEqual((m["wins_x"], m["wins_y"], m["draws"], m["games"]), (2, 2, 1, 5))
        self.assertEqual(m["start_x"], {"games": 3, "wins": 1})  # x beginnt in Spiel 1, 4, 5
        self.assertEqual(m["start_y"], {"games": 2, "wins": 1})  # y beginnt in Spiel 2 (verliert) und 3 (gewinnt)

    def test_first_starter_random(self):
        seen = set()
        for seed in range(20):
            calls = []

            def fake(cards_a, cards_b, a_starts, *a, **kw):
                calls.append(a_starts)
                return {"winner": None, "round": 20}
            tm.play_match([], [], 1, game=fake, rng=random.Random(seed))
            seen.add(calls[0])
        self.assertEqual(seen, {True, False})

    def test_real_games_never_concede(self):
        random.seed(3)
        r = battle_mod.play_game(lands(), lands(), True, 3, True, 5, a_never_concede=True)
        self.assertNotIn("note", r)
        self.assertEqual(r["mulligans"]["Wir"], 2)  # 7 -> 6 -> 5 Karten, dann behalten

    def test_old_default_still_concedes(self):
        random.seed(3)
        r = battle_mod.play_game(lands(), lands(), True, 3, True, 5)
        self.assertEqual(r["winner"], "b")


class PairingTests(unittest.TestCase):
    def test_round_robin(self):
        self.assertEqual(tm.round_robin(4), [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)])
        self.assertEqual(tm.round_robin(1), [])

    def test_empty_means_round_robin(self):
        self.assertEqual(tm.parse_pairings("", 3), [(0, 1), (0, 2), (1, 2)])
        self.assertEqual(tm.parse_pairings("   ", 3), [(0, 1), (0, 2), (1, 2)])

    def test_numbers(self):
        self.assertEqual(tm.parse_pairings("1-3 2-4", 4), [(0, 2), (1, 3)])
        self.assertEqual(tm.parse_pairings("1:3, 4 - 2", 4), [(0, 2), (3, 1)])

    def test_invalid(self):
        for bad in ("1-5", "1-1", "1", "a-b", "0-2", "1-2-3"):
            with self.assertRaises(ValueError, msg=bad):
                tm.parse_pairings(bad, 4)

    def test_names(self):
        names = ["Javier Dominguez", "Seth Manfield", "Samuel Chang"]
        self.assertEqual(tm.parse_pairings("manfield-chang", 3, names), [(1, 2)])
        with self.assertRaises(ValueError):
            tm.parse_pairings("s-chang", 3, names)  # "s" passt auf zwei Decks


class NameTests(unittest.TestCase):
    def test_player_name_from_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "wc32_seth_manfield.txt"
            p.write_text("Deck\n17 Plains\n", encoding="utf-8")
            self.assertEqual(tm.player_name(p, "wc32"), "Seth Manfield")
            q = pathlib.Path(tmp) / "x.txt"
            q.write_text("Name Mein Deck\nDeck\n17 Plains\n", encoding="utf-8")
            self.assertEqual(tm.player_name(q, "wc32"), "Mein Deck")

    def test_folders_and_decks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "wc32").mkdir()
            (root / "wc32" / "b.txt").write_text("Deck\n", encoding="utf-8")
            (root / "wc32" / "a.txt").write_text("Deck\n", encoding="utf-8")
            (root / "leer").mkdir()
            (root / "top.txt").write_text("Deck\n", encoding="utf-8")
            self.assertEqual(tm.list_folders(root), ["wc32"])
            self.assertEqual([p.name for p in tm.list_decks(root / "wc32")], ["a.txt", "b.txt"])


class VerdictTests(unittest.TestCase):
    def test_clear_favourite(self):
        self.assertEqual(tm.favourite(300, 200)[0], "x")
        self.assertEqual(tm.favourite(200, 300)[0], "y")

    def test_too_close(self):
        self.assertIsNone(tm.favourite(260, 240)[0])
        self.assertIsNone(tm.favourite(0, 0)[0])

    def test_interval(self):
        _, lo, hi = tm.favourite(250, 250)
        self.assertLess(lo, 0.5)
        self.assertGreater(hi, 0.5)
        self.assertAlmostEqual((lo + hi) / 2, 0.5, places=6)


def match(x, y, wx, wy, d=0):
    return {"x": x, "y": y, "wins_x": wx, "wins_y": wy, "draws": d, "games": wx + wy + d,
            "start_x": {"games": 0, "wins": 0}, "start_y": {"games": 0, "wins": 0}}


class StandingsTests(unittest.TestCase):
    def test_order(self):
        names = ["A", "B", "C"]
        rows = tm.standings(names, [match(0, 1, 300, 200), match(0, 2, 100, 400), match(1, 2, 260, 240)])
        # A 1-1 (400:600), B 1-1 (460:540), C 1-1 (640:360) -> nach Spielquote: C, B, A
        self.assertEqual([r["name"] for r in rows], ["C", "B", "A"])
        self.assertEqual((rows[0]["match_wins"], rows[0]["match_losses"]), (1, 1))
        self.assertEqual((rows[0]["game_wins"], rows[0]["game_losses"]), (640, 360))

    def test_match_tie(self):
        rows = tm.standings(["A", "B"], [match(0, 1, 250, 250)])
        self.assertEqual([r["match_draws"] for r in rows], [1, 1])


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.names = ["Javier Dominguez", "Seth Manfield"]
        m = match(0, 1, 290, 205, 5)
        m["start_x"] = {"games": 250, "wins": 160}
        m["start_y"] = {"games": 250, "wins": 120}
        self.matches = [m]

    def test_german(self):
        page = tm.render_tournament_html("wc32", self.names, self.matches)
        self.assertIn("Javier Dominguez", page)
        self.assertIn("290", page)
        self.assertIn("hätte gewinnen sollen", page)
        self.assertIn("103.1", page)

    def test_english(self):
        with english():
            page = tm.render_tournament_html("wc32", self.names, self.matches)
        self.assertIn("should have won", page)
        self.assertEqual(german_leftovers(page, allow=self.names), [])


class IncompleteDeckTests(unittest.TestCase):
    """Die Decklisten koennen unvollstaendig sein: trotzdem alles durchsimulieren, im Bericht kennzeichnen."""

    def build(self, entry, data, args):
        n = sum(entry["deck"].values())
        if n < 10:
            raise SystemExit("Zu wenige Karten")
        return {"cards": lands(n), "missing": [k for k in entry["deck"] if k not in data]}

    def test_build_all_notes(self):
        decks = [{"Plains": 39}, {"Plains": 40}, {"Plains": 3}, {"Plains": 39, "Unbekannt": 1}]
        data = {"Plains": {}}
        built, info = tm.build_all(["A", "B", "C", "D"], decks, data, None, self.build)
        self.assertEqual(sorted(built), [0, 1, 3])
        self.assertEqual(info[0]["size"], 39)
        self.assertTrue(info[0]["notes"])  # 39 statt 40
        self.assertEqual(info[1]["notes"], [])
        self.assertFalse(info[2]["playable"])
        self.assertTrue(any("Unbekannt" in n for n in info[3]["notes"]))

    def test_run_skips_unplayable_and_finishes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "enemydecks" / "wc").mkdir(parents=True)
            for name, n in (("a", 39), ("b", 40), ("c", 2)):
                (root / "enemydecks" / "wc" / f"{name}.txt").write_text(f"Deck\n{n} Plains\n", encoding="utf-8")
            from tests.fixtures import args_for
            args = args_for(["--turnier", "wc", "--turnier-spiele", "4", "--turnier-ausgabe",
                             str(root / "out.html")])
            with mock.patch.object(tm, "SCRIPT_DIR", root), mock.patch("sys.stderr", io.StringIO()):
                matches = tm.run(args, self.build, lambda names, reload: {"Plains": {}}, ask=lambda p: "")
            self.assertEqual([(m["x"], m["y"]) for m in matches], [(0, 1)])
            page = (root / "out.html").read_text(encoding="utf-8")
            self.assertIn("39", page)
            self.assertIn("nicht spielbar", page)

    def test_report_marks_size(self):
        info = [{"name": "A", "size": 39, "playable": True, "notes": ["39 Karten statt 40"]},
                {"name": "B", "size": 40, "playable": True, "notes": []}]
        page = tm.render_tournament_html("wc", ["A", "B"], [match(0, 1, 260, 240)], decks=info)
        self.assertIn("39 Karten statt 40", page)
        with english():
            page = tm.render_tournament_html("wc", ["A", "B"], [match(0, 1, 260, 240)], decks=[
                {"name": "A", "size": 39, "playable": True, "notes": [tm.size_note(39)]},
                {"name": "B", "size": 3, "playable": False, "notes": [tm.unplayable_note()]}])
        self.assertEqual(german_leftovers(page, allow=["A", "B"]), [])


def rich_game(winner, rnd, mull_x=0, opening_x=("Bear", "Plains"), drew_x="Giant"):
    """Ein erfundenes Spielergebnis wie aus play_game (Wir = Deck x, Gegner = Deck y)."""
    log = []
    for r in range(1, rnd + 1):
        log.append({"player": "Wir", "round": r, "drew": drew_x if r == 2 else None,
                    "life": {"Wir": 20, "Gegner": 20 - 4 * r}})
        log.append({"player": "Gegner", "round": r, "drew": "Elf" if r == 1 else None,
                    "life": {"Gegner": 20 - 4 * r, "Wir": 20 - r}})
    return {"winner": winner, "round": rnd, "log": log,
            "opening": {"Wir": list(opening_x), "Gegner": ["Wolf", "Forest"]},
            "mulligans": {"Wir": mull_x, "Gegner": 0},
            "stats": {"combat": {"Wir": 20, "Gegner": 3}, "direct": {"Wir": 2, "Gegner": 0},
                      "deaths": {"Wir": 1, "Gegner": 2}}}


class MatchStatsTests(unittest.TestCase):
    def setUp(self):
        games = iter([rich_game("a", 5, mull_x=1), rich_game("a", 3, opening_x=("Plains",), drew_x=None),
                      rich_game("b", 4)])
        self.m = tm.play_match([], [], 3, game=lambda *a, **kw: next(games), rng=random.Random(1))

    def test_win_rounds(self):
        self.assertEqual(self.m["sides"]["x"]["win_rounds"], {5: 1, 3: 1})
        self.assertEqual(self.m["sides"]["y"]["win_rounds"], {4: 1})

    def test_damage_and_deaths(self):
        x, y = self.m["sides"]["x"], self.m["sides"]["y"]
        self.assertEqual((x["combat"], x["direct"], x["deaths"]), (60, 6, 3))
        self.assertEqual((y["combat"], y["direct"], y["deaths"]), (9, 0, 6))

    def test_mulligans(self):
        x = self.m["sides"]["x"]
        self.assertEqual((x["mull_games"], x["mull_wins"]), (1, 1))
        self.assertEqual((self.m["sides"]["y"]["mull_games"]), 0)

    def test_card_stats(self):
        cards = self.m["sides"]["x"]["cards"]
        # Bear: Starthand in Spiel 1 (Sieg) und 3 (Niederlage); Giant gezogen in Spiel 1 und 3; Plains (Basic) nicht
        self.assertEqual(cards["Bear"], {"seen": 2, "seen_wins": 1, "open": 2, "open_wins": 1})
        self.assertEqual(cards["Giant"], {"seen": 2, "seen_wins": 1, "open": 0, "open_wins": 0})
        self.assertNotIn("Plains", cards)
        self.assertEqual(self.m["sides"]["y"]["cards"]["Wolf"]["seen"], 3)
        self.assertEqual(self.m["sides"]["y"]["cards"]["Elf"], {"seen": 3, "seen_wins": 1, "open": 0, "open_wins": 0})

    def test_life_curve_carries_last_value(self):
        curve = self.m["life_curve"]
        self.assertEqual(len(curve["x"]), 5)
        # Runde 1: alle Spiele 19 Leben fuer x; Runde 5: Spiel 1 = 15, Spiel 2 bleibt bei 17, Spiel 3 bei 16
        self.assertAlmostEqual(curve["x"][0], 19)
        self.assertAlmostEqual(curve["x"][4], (15 + 17 + 16) / 3)
        self.assertAlmostEqual(curve["y"][0], 16)

    def test_winner_end_life(self):
        # Sieger-Restleben: x in Spiel 1 (15) und 2 (17), y in Spiel 3 (20 - 16 = 4)
        self.assertEqual(self.m["sides"]["x"]["end_life_win"], 32)
        self.assertEqual(self.m["sides"]["y"]["end_life_win"], 4)

    def test_deck_card_stats_merge(self):
        m2 = dict(self.m, x=0, y=1)
        m3 = tm.play_match([], [], 1, game=lambda *a, **kw: rich_game("b", 2), rng=random.Random(1))
        m3.update(x=2, y=0)  # Deck 0 diesmal als y
        stats = tm.deck_card_stats([m2, m3], 0)
        self.assertEqual(stats["Bear"]["seen"], 2)
        self.assertEqual(stats["Wolf"], {"seen": 1, "seen_wins": 1, "open": 1, "open_wins": 1})


class RichReportTests(unittest.TestCase):
    def setUp(self):
        games = iter([rich_game("a", 5, mull_x=1), rich_game("b", 4)] * 50)
        names = ["Javier Dominguez", "Seth Manfield", "Samuel Chang"]
        ms = []
        for x, y in ((0, 1), (0, 2), (1, 2)):
            m = tm.play_match([], [], 30, game=lambda *a, **kw: next(games), rng=random.Random(2))
            m.update(x=x, y=y)
            ms.append(m)
        self.names, self.ms = names, ms
        self.decks = [{"name": n, "size": 40, "playable": True, "notes": []} for n in names]

    def test_sections(self):
        page = tm.render_tournament_html("wc32", self.names, self.ms, decks=self.decks)
        for sid in ("ueberblick", "matrix", "tabelle", "paarungen", "decks"):
            self.assertIn(f'id="{sid}"', page)
        self.assertIn("Giant", page)  # Kartenstatistik
        self.assertIn("<svg", page)  # Diagramme
        self.assertIn("prefers-color-scheme: dark", page)

    def test_english_rich(self):
        with english():
            page = tm.render_tournament_html("wc32", self.names, self.ms, decks=self.decks)
        allow = self.names + ["Giant", "Bear", "Wolf", "Elf"]
        self.assertEqual(german_leftovers(page, allow=allow), [])


class CliTests(unittest.TestCase):
    def test_args(self):
        from components.cli import parse_args
        a = parse_args(["--turnier", "wc32", "--paarung", "1-3", "--paarung", "2-4"])
        self.assertEqual(a.turnier, "wc32")
        self.assertEqual(a.paarung, ["1-3", "2-4"])
        self.assertEqual(a.turnier_spiele, 500)
        self.assertEqual(parse_args(["--turnier"]).turnier, "")

    def test_ask_pairings_retries(self):
        answers = iter(["9-9", "1-2"])
        out = io.StringIO()
        pairs = tm.ask_pairings(["A", "B", "C"], ask=lambda prompt: next(answers), out=out)
        self.assertEqual(pairs, [(0, 1)])
        self.assertIn("A", out.getvalue())

    def test_launcher_mode_5(self):
        bat = (pathlib.Path(__file__).resolve().parent.parent / "draftgott.bat").read_text(encoding="utf-8")
        self.assertIn("5 = Turnier", bat)
        self.assertIn("5 = Tournament", bat)
        self.assertIn("--turnier", bat)
        self.assertEqual(bat.count("choice /c 12345"), 2)

    def test_choose_folder(self):
        self.assertEqual(tm.choose_folder(["wc32"], ask=lambda p: self.fail("nicht fragen")), "wc32")
        self.assertEqual(tm.choose_folder(["a", "b"], ask=lambda p: "2", out=io.StringIO()), "b")


if __name__ == "__main__":
    unittest.main()
