import unittest

from components.deckfile import parse_deck, parse_deck_name, parse_pool, split_label


class ParseDeckTests(unittest.TestCase):
    def test_reads_deck_section_and_ignores_sideboard(self):
        text = "Deck\n4 Plains (TST) 1\n2x Test Bear\n\nSideboard\n3 Test Big (TST) 5\n"
        self.assertEqual(parse_deck(text), {"Plains": 4, "Test Bear": 2})

    def test_without_section_header_counts_everything(self):
        self.assertEqual(parse_deck("3 Plains\n1 Island"), {"Plains": 3, "Island": 1})

    def test_same_card_on_several_lines_is_summed(self):
        self.assertEqual(parse_deck("Deck\n2 Plains (A) 1\n3 Plains (B) 2"), {"Plains": 5})

    def test_deck_name_from_about_section(self):
        self.assertEqual(parse_deck_name("About\nName Mein Deck\nDeck\n1 Plains", "x"), "Mein Deck")
        self.assertEqual(parse_deck_name("Deck\n1 Plains", "fallback"), "fallback")


class ParsePoolTests(unittest.TestCase):
    def test_deck_and_sideboard_with_set_and_number(self):
        rows = parse_pool("Deck\n4 Plains (SPM) 194\nSideboard\n1 Test Big (TST) 5\n")
        self.assertEqual(rows, [
            {"name": "Plains", "qty": 4, "section": "deck", "set": "spm", "number": "194"},
            {"name": "Test Big", "qty": 1, "section": "sideboard", "set": "tst", "number": "5"}])

    def test_line_without_set_has_empty_set_and_number(self):
        rows = parse_pool("Deck\n2 Test Bear\n")
        self.assertEqual((rows[0]["set"], rows[0]["number"]), ("", ""))

    def test_lines_before_a_section_header_are_ignored(self):
        self.assertEqual(parse_pool("1 Plains\nDeck\n1 Island"), [
            {"name": "Island", "qty": 1, "section": "deck", "set": "", "number": ""}])

    def test_x_after_quantity_is_accepted(self):
        self.assertEqual(parse_pool("Deck\n3x Test Bear")[0]["qty"], 3)


class SplitLabelTests(unittest.TestCase):
    def test_explicit_label(self):
        self.assertEqual(split_label("datei.txt=Mein Label"), ("datei.txt", "Mein Label"))

    def test_label_from_filename_without_leading_underscore(self):
        self.assertEqual(split_label("_nosplash.txt"), ("_nosplash.txt", "Nosplash"))


if __name__ == "__main__":
    unittest.main()
