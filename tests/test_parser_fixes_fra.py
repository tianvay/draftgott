"""Parser-Fehler aus der FRA-Analyse: Schluesselwortzeile mit "ward {N}" (Kwia Vigorbloom) und Kurzname einer
legendaeren Karte ohne Komma im Namen (201.5c: "When Kiora enters" bei Kiora of Fire and Ashes)."""
import unittest

from components.cards import card_info
from tests.fixtures_walkers import _card

DASH = "—"


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="G"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


KWIA = make("Kwia Vigorbloom", f"Legendary Creature {DASH} Elder Sphinx", "{3}{G}{W}{W}", 6, "Flying, vigilance, "
            "lifelink, ward {2}\nWhenever you gain life, create a colorless artifact token named Lotus with \"{T}, "
            "Sacrifice this token: Add three mana of any one color.\" This ability triggers only once each turn.", "6",
            "6", ["Flying", "Lifelink", "Vigilance", "Ward"])
KIORA = make("Kiora of Fire and Ashes", f"Legendary Creature {DASH} Merfolk Noble", "{4}{R}{R}", 6, "When Kiora "
             "enters, create a 5/5 red Dragon creature token with flying.\n{8}: Create a 5/5 red Dragon creature token "
             "with flying.", "2", "2", colors="R")
COMMON_KIORA = make("Kiora Scout", f"Creature {DASH} Merfolk", "{1}{U}", 2, "When Kiora enters, draw a card.", "1", "1",
                    colors="U")
FULCRUM = make("The Echoverse Fulcrum", "Legendary Artifact", "{2}", 2, "When The Echoverse Fulcrum enters, draw a "
               "card, then discard a card.\n{5}, {T}, Exile The Echoverse Fulcrum: Destroy all creatures. Activate only as "
               "a sorcery.", colors="")


class KeywordLineTests(unittest.TestCase):
    def test_ward_in_the_keyword_line(self):
        self.assertEqual(set(KWIA.kw), {"flying", "vigilance", "lifelink"})
        self.assertEqual(KWIA.ward, ("mana", 2))


class ShortNameTests(unittest.TestCase):
    def test_legendary_short_name(self):
        self.assertEqual([(n, t.name, t.power, t.toughness, t.kw) for n, t in KIORA.creates_tokens],
                         [(1, "Dragon", 5, 5, ("flying",))])

    def test_not_for_nonlegendary_cards(self):
        self.assertEqual(COMMON_KIORA.draws, 0)  # "Kiora" ist hier nicht der Name der Karte

    def test_articles_are_no_short_names(self):
        self.assertTrue(FULCRUM.sweep_ability and FULCRUM.loot)


if __name__ == "__main__":
    unittest.main()
