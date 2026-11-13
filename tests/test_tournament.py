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
