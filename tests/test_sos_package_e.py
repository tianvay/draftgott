"""SOS Paket E: Increment und Fractals (Quandrix) - Increment (Marke, wenn das ausgegebene Mana groesser ist als Power
oder Toughness), Ausloeser fuer Marken (Ziehen, Mana), Fractal-Token mit X Marken (gezogene Karten, X-Zauber,
Faehigkeiten, Endsegment, Tod), Marken weitergeben, X-Zauber-Ausloeser und Homesickness. Kartentexte aus Secrets of
Strixhaven (SOS)."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]
BEAR = W["Test Bear"]
INC = ("Increment (Whenever you cast a spell, if the amount of mana you spent is greater than this creature's power or "
       "toughness, put a +1/+1 counter on this creature.)")
NOTE = " (While it's prepared, you may cast a copy of its spell. Doing so unprepares it.)"


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="U"):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)


RAW = {
    "tabulator": raw("Textbook Tabulator", f"Creature {DASH} Frog Wizard", "{2}{U}", 3,
                     INC + "\nWhen this creature enters, surveil 2. (Look at the top two cards of your library, then "
                     "put any number of them into your graveyard and the rest on top of your library in any order.)",
                     "0", "3", ["Surveil", "Increment"]),
    "graffalon": raw("Hungry Graffalon", f"Creature {DASH} Giraffe", "{3}{G}", 4, "Reach\n" + INC, "3", "4",
                     ["Reach", "Increment"], "G"),
    "colony": raw("Cuboid Colony", f"Creature {DASH} Insect", "{G}{U}", 2, "Flash\nFlying, trample\n" + INC, "1", "1",
                  ["Flying", "Trample", "Flash", "Increment"], "GU"),
    "tender": raw("Fractal Tender", f"Creature {DASH} Elf Wizard", "{3}{G}{U}", 5,
                  "Ward {2}\n" + INC + "\nAt the beginning of each end step, if you put a counter on this creature this "
                  "turn, create a 0/0 green and blue Fractal creature token and put three +1/+1 counters on it.", "3",
                  "3", ["Ward", "Increment"], "GU"),
    "tester": raw("Tester of the Tangential", f"Creature {DASH} Djinn Wizard", "{1}{U}", 2,
                  INC + "\nAt the beginning of combat on your turn, you may pay {X}. When you do, move X +1/+1 counters "
                  "from this creature onto another target creature.", "1", "1", ["Increment"]),
    "pensive": raw("Pensive Professor", f"Creature {DASH} Human Wizard", "{1}{U}{U}", 3,
                   INC + "\nWhenever one or more +1/+1 counters are put on this creature, draw a card.", "0", "2",
                   ["Increment"]),
    "augmenter": raw("Ambitious Augmenter", f"Creature {DASH} Turtle Wizard", "{G}", 1,
                     INC + "\nWhen this creature dies, if it had one or more counters on it, create a 0/0 green and "
                     "blue Fractal creature token, then put this creature's counters on that token.", "1", "1",
                     ["Increment"], "G"),
    "berta": raw("Berta, Wise Extrapolator", f"Legendary Creature {DASH} Frog Druid", "{2}{G}{U}", 4,
                 INC + "\nWhenever one or more +1/+1 counters are put on Berta, add one mana of any color.\n{X}, {T}: "
                 "Create a 0/0 green and blue Fractal creature token and put X +1/+1 counters on it.", "1", "4",
                 ["Increment"], "GU"),
    "scolding": raw("Scolding Administrator", f"Creature {DASH} Dwarf Cleric", "{W}{B}", 2,
                    "Menace (This creature can't be blocked except by two or more creatures.)\nRepartee — Whenever you "
                    "cast an instant or sorcery spell that targets a creature, put a +1/+1 counter on this creature.\n"
                    "When this creature dies, if it had counters on it, put those counters on up to one target "
                    "creature.", "2", "2", ["Menace", "Repartee"], "WB"),
    "anomaly": raw("Fractal Anomaly", "Instant", "{U}", 1,
                   "Create a 0/0 green and blue Fractal creature token and put X +1/+1 counters on it, where X is the "
                   "number of cards you've drawn this turn."),
    "gift": raw("Oracle's Gift", "Sorcery", "{X}{X}{U}", 1,
                "Create X 0/0 green and blue Fractal creature tokens, then put X +1/+1 counters on each Fractal you "
                "control."),
    "emil": raw("Emil, Vastlands Roamer", f"Legendary Creature {DASH} Elf Druid", "{2}{G}", 3,
                "Creatures you control with +1/+1 counters on them have trample.\n{4}{G}, {T}: Create a 0/0 green and "
                "blue Fractal creature token. Put X +1/+1 counters on it, where X is the number of differently named "
                "lands you control.", "3", "3", colors="G"),
    "matterbending": raw("Matterbending Mage", f"Creature {DASH} Human Wizard", "{2}{U}", 3,
                         "When this creature enters, return up to one other target creature to its owner's hand.\n"
                         "Whenever you cast a spell with {X} in its mana cost, this creature can't be blocked this "
                         "turn.", "2", "2"),
    "homesickness": raw("Homesickness", "Instant", "{4}{U}{U}", 6,
                        "Target player draws two cards. Tap up to two target creatures. Put a stun counter on each of "
                        "them. (If a permanent with a stun counter would become untapped, remove one from it "
                        "instead.)"),
}
RAW["jadzi"] = {"name": "Jadzi, Steward of Fate // Oracle's Gift", "layout": "prepare",
                "type_line": f"Legendary Creature {DASH} Human Wizard", "mana_cost": "{2}{U}", "cmc": 3.0,
                "colors": ["U"], "keywords": ["Prepared"],
                "card_faces": [raw("Jadzi, Steward of Fate", f"Legendary Creature {DASH} Human Wizard", "{2}{U}", 3,
                                   "Jadzi enters prepared." + NOTE + "\nWhen Jadzi enters, draw two cards, then "
                                   "discard two cards.", "2", "4"), RAW["gift"]]}
C = {k: card_info(v)[0] for k, v in RAW.items()}

TITAN = card_info(raw("Titan", "Creature — Giant", "{4}{G}", 5, "", "5", "5", colors="G"))[0]
WALL = card_info(raw("Wall", "Creature — Wall", "{1}{W}", 2, "", "0", "6", colors="W"))[0]
CHEAP = card_info(raw("Quick Thought", "Sorcery", "{U}", 1, "Draw a card."))[0]
BIG = card_info(raw("Big Thought", "Sorcery", "{3}{U}", 4, "Draw two cards."))[0]
XSPELL = card_info(raw("X Thought", "Sorcery", "{X}{U}", 1, "Target player gains X life."))[0]
FOREST, ISLAND = W.get("Forest", PLAINS), W["Island"]


def player(name="Wir"):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], [PLAINS] * 20
    return p


def pair():
    me, opp = player(), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


def entry():
    return {"face": 0, "damage": 0, "events": [], "deaths": [], "main1": [], "main2": []}


def on_board(p, card, entered=0):
    c = bt.Creature(card, entered)
    c.gy, c.ctl = p.graveyard, p
    p.creatures.append(c)
    return c


def fractals(p):
    return [c for c in p.creatures if c.card.name == "Fractal" and not c.dead]


class ParseTests(unittest.TestCase):
    def test_increment(self):
        for key in ("tabulator", "graffalon", "colony", "tender", "tester", "pensive", "augmenter", "berta"):
            self.assertTrue(C[key].increment, key)

    def test_counter_triggers(self):
        self.assertEqual(C["pensive"].counter_draw, 1)
        self.assertTrue(C["berta"].counter_mana)

    def test_fractals(self):
        self.assertTrue(C["tender"].fractal_tender)
        self.assertTrue(C["augmenter"].death_fractal)
        self.assertTrue(C["scolding"].death_counters_move)
        self.assertTrue(C["tester"].tester_move)
        self.assertTrue(C["anomaly"].fractal_drawn)
        self.assertTrue(C["gift"].fractal_gift)
        self.assertEqual(C["gift"].x_cost, True)
        self.assertEqual(C["emil"].fractal_ability[1], "snw")
        self.assertEqual(C["berta"].fractal_ability[1], "x")

    def test_x_trigger_and_homesickness(self):
        self.assertTrue(C["matterbending"].x_cast_unblockable)
        h = C["homesickness"]
        self.assertEqual((h.draws, h.tap_spell, h.tap_targets), (2, (1, 1, 0), 2))


class CoverageTests(unittest.TestCase):
    PARTIAL = {"topiary": None, "matterbending": "When this creature enters"}

    def test_cards_fully_modelled(self):
        for key in RAW:
            lines = [line for _c, _m, line in analyze_card(RAW[key])]
            skip = self.PARTIAL.get(key)
            if skip:
                lines = [line for line in lines if not line.startswith(skip)]
            self.assertEqual(lines, [], key)


class IncrementTests(unittest.TestCase):
    def test_counter_when_spent_exceeds_power_or_toughness(self):
        me, opp = pair()
        graffalon = on_board(me, C["graffalon"])  # 3/4: ab 4 Mana
        bt.on_cast(me, CHEAP, 3, entry())
        self.assertEqual(graffalon.bonus, 0)
        bt.on_cast(me, BIG, 3, entry())
        self.assertEqual(graffalon.bonus, 1)

    def test_zero_power_grows_from_any_spell(self):
        me, opp = pair()
        tab = on_board(me, C["tabulator"])  # 0/3
        bt.on_cast(me, CHEAP, 3, entry())
        self.assertEqual(tab.bonus, 1)

    def test_not_from_itself(self):
        me, opp = pair()
        bt._resolve(me, opp, C["graffalon"], 3, entry())
        self.assertEqual(me.creatures[0].bonus, 0)

    def test_x_spell_counts_x(self):
        me, opp = pair()
        graffalon = on_board(me, C["graffalon"])
        me.next_x = 3
        bt.on_cast(me, C["gift"], 3, entry())  # X=3: {3}{3}{U} = 7 Mana
        self.assertEqual(graffalon.bonus, 1)

    def test_pensive_draws(self):
        me, opp = pair()
        on_board(me, C["pensive"])
        bt.on_cast(me, CHEAP, 3, entry())
        self.assertEqual(len(me.hand), 1)

    def test_berta_adds_mana(self):
        me, opp = pair()
        on_board(me, C["berta"])  # 1/4: ab 2 Mana
        bt.on_cast(me, BIG, 3, entry())
        self.assertEqual(len(me.open), 1)


class FractalTests(unittest.TestCase):
    def test_tender_at_end_step_after_counter(self):
        me, opp = pair()
        on_board(me, C["tender"])
        bt.sos_end_own(me, opp, 3, entry())
        self.assertEqual(fractals(me), [])
        bt.on_cast(me, BIG, 3, entry())  # 4 Mana > 3
        bt.sos_end_own(me, opp, 3, entry())
        self.assertEqual([f.bonus for f in fractals(me)], [3])

    def test_augmenter_dies_into_fractal(self):
        me, opp = pair()
        aug = on_board(me, C["augmenter"])
        aug.bonus = 2
        aug.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual([f.bonus for f in fractals(me)], [2])

    def test_scolding_moves_counters(self):
        me, opp = pair()
        s = on_board(me, C["scolding"])
        bear = on_board(me, BEAR)
        s.bonus = 2
        s.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual(bear.bonus, 2)

    def test_tester_moves_counters_when_it_cannot_attack(self):
        me, opp = pair()
        tester = on_board(me, C["tester"], entered=3)  # frisch: greift nicht an
        tester.bonus = 2
        bear = on_board(me, BEAR)
        me.open = [("U",), ("U",)]
        bt.sos_combat_start(me, opp, 3, entry())
        self.assertEqual((tester.bonus, bear.bonus), (0, 2))

    def test_anomaly_in_main2_with_cards_drawn(self):
        me, opp = pair()
        me.hand, me.open = [C["anomaly"]], [("U",)]
        me.drawn, me.drawn_mark = 2, 0
        bt.sos_main2(me, entry())
        self.assertEqual([f.bonus for f in fractals(me)], [2])

    def test_anomaly_not_at_end_step_without_draws(self):
        dfn, act = pair()
        dfn.hand, dfn.open = [C["anomaly"]], [("U",)]
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertIn(C["anomaly"], dfn.hand)

    def test_oracles_gift(self):
        me, opp = pair()
        old = on_board(me, bt.FRACTAL)
        old.bonus = 1
        me.next_x = 2
        bt._resolve(me, opp, C["gift"], 3, entry())
        self.assertEqual(sorted(f.bonus for f in fractals(me)), [2, 2, 3])
        self.assertEqual(me.next_x, 0)

    def test_emil_at_end_step(self):
        dfn, act = pair()
        dfn.turn_start = 1
        on_board(dfn, C["emil"])
        dfn.lands = [PLAINS, ISLAND, FOREST]
        dfn.open = [("G",)] * 5
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual([f.bonus for f in fractals(dfn)], [len({l.name for l in dfn.lands})])

    def test_berta_x_at_end_step(self):
        dfn, act = pair()
        dfn.turn_start = 1
        on_board(dfn, C["berta"])
        dfn.open = [("G",)] * 3
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual([f.bonus for f in fractals(dfn)], [3])


class OtherTests(unittest.TestCase):
    def test_matterbending_unblockable_after_x_spell(self):
        me, opp = pair()
        mage = on_board(me, C["matterbending"])
        bt.on_cast(me, CHEAP, 3, entry())
        self.assertNotIn("unblockable", mage.extra)
        bt.on_cast(me, XSPELL, 3, entry())
        self.assertIn("unblockable", mage.extra)

    def test_homesickness_taps_two_with_stun(self):
        dfn, act = pair()
        a, b = on_board(act, TITAN), on_board(act, WALL)
        dfn.open, dfn.hand = [("U",)] * 6, [C["homesickness"]]
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual((a.tapped, b.tapped, a.stun, b.stun, len(dfn.hand)), (True, True, 1, 1, 2))


if __name__ == "__main__":
    unittest.main()
