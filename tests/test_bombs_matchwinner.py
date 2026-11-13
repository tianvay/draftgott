"""Bomben sind nur noch Karten der Kategorie Matchwinner (nicht mehr Splashworthy): Deck-Uebersicht im Seitenfenster
und auf der Seite, Hilfe."""
import unittest

from components import livedraft as ld


def card(name):
    return {"name": name, "mv": 3, "qty": 1, "colors": ["W"]}


class BombTests(unittest.TestCase):
    def test_only_matchwinner(self):
        r = {"A": "splashworthy", "B": "matchwinner", "C": "mustplay"}
        self.assertEqual(ld.deck_summary([card("A"), card("B"), card("C")], r, "arena")["top"], ["B"])

    def test_splashworthy_alone_is_no_bomb(self):
        self.assertEqual(ld.deck_summary([card("A")], {"A": "splashworthy"}, "arena")["top"], [])

    def test_at_most_three_by_name(self):
        names = ["D", "B", "A", "C"]
        r = {n: "matchwinner" for n in names}
        self.assertEqual(ld.deck_summary([card(n) for n in names], r, "arena")["top"], ["A", "B", "C"])

    def test_help_text(self):
        from components.howitworks import render_help_page
        page = render_help_page()
        self.assertIn("Bomben (eigene Bewertung Matchwinner;", page)
        self.assertNotIn("Bewertung Matchwinner oder Splashworthy; Must-Play zählt nicht", page)


if __name__ == "__main__":
    unittest.main()
