import contextlib
import io
import unittest

from components.cli import parse_args


class CliTests(unittest.TestCase):
    def test_deck_file_is_positional(self):
        args = parse_args(["deck.txt", "--sims", "5"])
        self.assertEqual(args.deckfile, ["deck.txt"])
        self.assertEqual(args.sims, 5)
        self.assertIsNone(args.drafthelper)

    def test_drafthelper_without_value_uses_default_pool_file(self):
        self.assertEqual(parse_args(["--drafthelper"]).drafthelper, "_draftedcardpool.txt")

    def test_drafthelper_with_file(self):
        self.assertEqual(parse_args(["--drafthelper", "pool.txt"]).drafthelper, "pool.txt")

    def test_neither_deck_nor_drafthelper_is_an_error(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            parse_args([])


if __name__ == "__main__":
    unittest.main()
