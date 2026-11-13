"""Sprachschalter: Deutsch bleibt unveraendert, Englisch kommt aus den Woerterbuechern in components/i18n_en."""
import ast
import pathlib
import unittest

from components import i18n
from components.cli import parse_args
from tests.i18n_check import english, german_leftovers

ROOT = pathlib.Path(__file__).resolve().parent.parent


def literal_t_keys():
    """Alle t("...")-Aufrufe mit festem Text in components/*.py und mtg_sim.py: [(Datei, Zeile, Text)]."""
    out = []
    for path in sorted((ROOT / "components").glob("*.py")) + [ROOT / "mtg_sim.py"]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            f = node.func
            name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
            if name == "t" and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                out.append((path.name, node.lineno, node.args[0].value))
    return out


class TestI18n(unittest.TestCase):
    def test_default_is_german_and_unchanged(self):
        self.assertEqual(i18n.get_lang(), "de")
        self.assertEqual(i18n.t("Karten {n}", n=3), "Karten 3")
        self.assertEqual(i18n.tr_block("Hallo Welt", {"Hallo": "Hello"}), "Hallo Welt")
        self.assertEqual(i18n.dec("2.5"), "2,5")

    def test_english_lookup_and_placeholders(self):
        with english():
            i18n.en_table()["__test {n} Karten"] = "__test {n} cards"
            try:
                self.assertEqual(i18n.t("__test {n} Karten", n=4), "__test 4 cards")
                self.assertEqual(i18n.t("__fehlt"), "__fehlt")  # ohne Eintrag bleibt der Text
                self.assertEqual(i18n.t("a{b{x}}c", x=1), "a{b1}c")  # nur benannte Platzhalter
            finally:
                del i18n.en_table()["__test {n} Karten"]
            self.assertEqual(i18n.dec("2.5"), "2.5")
            self.assertEqual(i18n.html_lang(), "en")
        self.assertEqual(i18n.get_lang(), "de")

    def test_tr_block_longest_first(self):
        with english():
            self.assertEqual(i18n.tr_block("Karten und Karte", {"Karte": "card", "Karten": "cards", "und": "and"}),
                             "cards and card")

    def test_unknown_language(self):
        with self.assertRaises(ValueError):
            i18n.set_lang("fr")

    def test_cli_lang(self):
        self.assertEqual(parse_args(["deck.txt"]).lang, "de")
        self.assertEqual(parse_args(["deck.txt", "--lang", "en"]).lang, "en")

    def test_every_literal_t_key_has_english(self):
        table = i18n.en_table()
        missing = [(f, ln, k) for f, ln, k in literal_t_keys() if k not in table]
        self.assertEqual(missing, [])

    def test_english_values_have_same_placeholders(self):
        import re
        rx = re.compile(r"\{([A-Za-z_]\w*)\}")
        bad = [(k, v) for k, v in i18n.en_table().items() if set(rx.findall(k)) != set(rx.findall(v))]
        self.assertEqual(bad, [])

    def test_leftover_helper(self):
        self.assertTrue(german_leftovers("Die Karte ist gut"))
        self.assertEqual(german_leftovers("The card is good /* Karte */"), [])


if __name__ == "__main__":
    unittest.main()
