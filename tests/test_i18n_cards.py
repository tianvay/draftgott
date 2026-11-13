import unittest

from components import cards
from components.cards import card_info, tap_tag
from tests.fixtures import CARDS
from tests.i18n_check import english, german_leftovers

TAP_MODES = (("no", ()), ("tapped", ()), ("tapped?", ()), ("fast", ()), ("slow", ()),
             ("check", ("Plains", "Island")), ("planeswalker", ()), ("jace", ()))


def shown_all():
    out = [card_info(c)[1] for c in CARDS.values()]
    out += [tap_tag(m, a) for m, a in TAP_MODES]
    out += [cards.empower_tags_text([(0, k, 1, None, None, False, False, False)]) for k in cards.EMPOWER_KIND_LABEL]
    out += [cards.empower_tags_text([(0, "spell", 1, None, None, False, False, True)])]
    return out


class CardsEnglishTests(unittest.TestCase):
    def test_german_unchanged_and_english_clean(self):
        de = shown_all()
        with english():
            en = shown_all()
        self.assertEqual(de, shown_all())
        self.assertNotEqual(de, en)
        names = [c["name"] for c in CARDS.values()]
        for text in en:
            self.assertEqual(german_leftovers(text, allow=names), [], text)

    def test_creature_tag(self):
        with english():
            self.assertIn("[Creature 3/1, Haste]", card_info(CARDS["Test Hasty"])[1])
        self.assertIn("[Kreatur 3/1, Haste]", card_info(CARDS["Test Hasty"])[1])


if __name__ == "__main__":
    unittest.main()
