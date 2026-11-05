"""Star Trek (TRK), Paket R8 (Nutzer 2026-11-05): Kopien und Verdoppler - Dr. Beverly Crusher (Lebensgewinn-Ausloeser
doppelt), Troubling Tribbles, Dominion Saboteur, Georgiou, Dr. M'Benga (Marken doppelt, Hexproof mit Marken),
Holo-Engineer (Token werden 3/3-Illusionen), Gray and Adira, Replicator; Lwaxana Troi bewusst nicht. Nur Kampfmodell.
Kartentexte aus TRK."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]

RAW = {
    "crusher": _card("Dr. Beverly Crusher", f"Legendary Creature {DASH} Human Doctor", "{2}{W}", 3, "W", "If you gaining "
                     "life causes a triggered ability of a permanent you control to trigger, that ability triggers an "
                     "additional time.\nWhenever you gain life, put a +1/+1 counter on Dr. Crusher.", [], "2", "2"),
    "tribbles": _card("Troubling Tribbles", f"Creature {DASH} Tribble", "{2}{W}", 3, "W", "This creature can't block.\nAt "
                      "the beginning of your upkeep, create a token that's a copy of this creature.", [], "0", "1"),
    "saboteur": _card("Dominion Saboteur", f"Creature {DASH} Shapeshifter", "{4}{U}", 5, "U", "You may have this creature "
                      "enter as a copy of any artifact or creature on the battlefield, except it isn't legendary. If you "
                      "do, it enters with additional counters on it equal to the same number and kinds of counters the "
                      "copied permanent has on it.", [], "3", "3"),
    "georgiou": _card("Georgiou, Terran Emperor", f"Legendary Creature {DASH} Human Rogue Noble", "{4}{B}{B}", 6, "B",
                      "You don't lose the game for having 0 or less life.\nAt the beginning of your end step, you lose 3 "
                      "life and draw a card. Then if your life total is 0 or less, create ten 1/1 red Officer creature "
                      "tokens.", [], "4", "6"),
    "lwaxana": _card("Lwaxana Troi, Charming Guest", f"Legendary Creature {DASH} Betazoid Advisor", "{1}{R}", 2, "R",
                     "You may choose not to untap Lwaxana Troi during your untap step.\n{2}, {T}: Choose another target "
                     "creature you control. For as long as Lwaxana Troi remains tapped, if a triggered ability of that "
                     "creature triggers, that ability triggers an additional time.", [], "2", "2"),
    "mbenga": _card("Dr. Joseph M'Benga", f"Legendary Creature {DASH} Human Doctor", "{2}{G}{G}", 4, "G", "Other "
                    "creatures you control with counters on them have hexproof.\nIf you would put one or more counters "
                    "on a creature you control, put twice that many of each of those kinds of counters on that creature "
                    "instead.", [], "3", "3"),
    "holo": _card("Holo-Engineer", f"Creature {DASH} Human Artificer", "{2}{G}{G}", 4, "G", "When this creature enters, "
                  "create a 3/3 colorless Illusion artifact creature token.\nIf one or more tokens would be created under "
                  "your control, that many 3/3 colorless Illusion artifact creature tokens are created instead.", [], "3",
                  "3"),
    "gray": _card("Gray and Adira, Forever Joined", f"Legendary Creature {DASH} Trill Human Officer", "{2}{U/R}{U/R}", 4,
                  "UR", "At the beginning of combat on your turn, if you've cast a noncreature spell this turn, create a "
                  "token that's a copy of target creature you control, except it isn't legendary. It gains haste until "
                  "end of turn. Sacrifice it at the beginning of the next end step.", [], "2", "3"),
    "replicator": _card("Replicator", "Artifact", "{2}", 2, "", "When this artifact enters, create a Food token. (It's an "
                        "artifact with \"{2}, {T}, Sacrifice this token: You gain 3 life.\")\n{2}, {T}: Create a tapped "
                        "token that's a copy of target token you control."),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}


def make(name, cost, cmc, text="", power=None, toughness=None, type_line=f"Creature {DASH} Test", colors="G"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, [], power, toughness))[0]


BEAR = make("Bear", "{1}{G}", 2, "", "2", "2")
OGRE = make("Ogre", "{2}{R}", 3, "", "3", "3", colors="R")
SEER = make("Seer", "{1}{G}", 2, "When this creature enters, draw a card.", "1", "1")
LEGEND = make("Hero", "{3}{W}", 4, "", "4", "4", f"Legendary Creature {DASH} Human", "W")
TOKEN = make("Officer", "", 0, "", "1", "1", f"Creature {DASH} Officer", "R")._replace(is_token=True)
MURDER = make("Murder", "{1}{B}{B}", 3, "Destroy target creature.", type_line="Instant", colors="B")


def player(name="Wir"):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], [PLAINS] * 20
    return p


def pair():
    me, opp = player(), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": [], "land": ""}


def put(p, card, entered=0):
    c = bt.Creature(card, entered)
    c.gy, c.ctl = p.graveyard, p
    p.creatures.append(c)
    return c


def names(p):
    return sorted(c.card.name for c in p.creatures)


def open_lines(key):
    return [l for _c, _m, l in analyze_card(RAW[key])]


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertTrue(C["crusher"].lifegain_double)
        self.assertTrue(C["tribbles"].tribble_copy)
        self.assertTrue(C["saboteur"].saboteur_copy)
        self.assertTrue(C["georgiou"].georgiou)
        self.assertTrue(C["mbenga"].mbenga)
        self.assertEqual((C["holo"].holo_tokens.power, C["holo"].holo_tokens.is_artifact), (3, True))
        self.assertTrue(C["gray"].gray_copy)
        self.assertTrue(C["replicator"].token_copy)

    def test_coverage(self):
        for key in RAW:
            self.assertEqual(open_lines(key), [], key)  # Lwaxana in ON_PURPOSE


class DoublerTests(unittest.TestCase):
    def test_crusher(self):
        me, _opp = pair()
        crusher = put(me, C["crusher"])
        bt.gain_life(me, 2)
        self.assertEqual((me.life, crusher.bonus), (22, 2))  # Ausloeser doppelt, die Menge nicht

    def test_mbenga(self):
        me, opp = pair()
        put(me, C["mbenga"])
        bear = put(me, BEAR)
        bear.bonus += 1
        self.assertEqual(bear.bonus, 2)
        self.assertTrue(bt.hexproof(bear))
        ogre = put(me, OGRE)
        self.assertFalse(bt.hexproof(ogre))
        self.assertNotIn(bear, bt.valid_targets(MURDER.removal, opp, me))

    def test_holo_engineer(self):
        me, opp = pair()
        put(me, C["holo"])
        bt.make_tokens(me, [(2, TOKEN)], 3, entry(), opp, "Test")
        bt.artifact_tokens(me, "treasure", 1, 3, entry())
        self.assertEqual((names(me).count("Illusion"), me.treasures), (3, 0))


class CopyTests(unittest.TestCase):
    def test_tribbles(self):
        me, opp = pair()
        put(me, C["tribbles"])
        bt.upkeep_triggers(me, opp, 3, entry())
        bt.upkeep_triggers(me, opp, 5, entry())
        self.assertEqual(names(me).count("Troubling Tribbles"), 4)

    def test_tribbles_cap(self):  # Nutzer 2026-11-05: hoechstens 20 Tribbles
        me, opp = pair()
        for _ in range(19):
            put(me, C["tribbles"])
        bt.upkeep_triggers(me, opp, 3, entry())
        self.assertEqual(names(me).count("Troubling Tribbles"), 20)
        bt.upkeep_triggers(me, opp, 5, entry())
        self.assertEqual(names(me).count("Troubling Tribbles"), 20)

    def test_saboteur_copies_best_with_counters(self):
        me, opp = pair()
        hero = put(opp, LEGEND)
        hero.bonus = 2
        put(me, BEAR)
        sab = put(me, C["saboteur"], 3)
        bt.creature_enters(me, sab, 3, entry(), opp)
        self.assertEqual((sab.card.name, sab.card.legendary, sab.bonus, sab.base_card), ("Hero", False, 2, C["saboteur"]))

    def test_saboteur_copies_etb(self):
        me, opp = pair()
        put(me, SEER)
        sab = put(me, C["saboteur"], 3)
        bt.creature_enters(me, sab, 3, entry(), opp)
        self.assertEqual((sab.card.name, len(me.hand)), ("Seer", 1))

    def test_gray_and_adira(self):
        me, opp = pair()
        put(me, C["gray"])
        hero = put(me, LEGEND)
        bt.combat_tokens(me, opp, 3, entry())
        self.assertEqual(len(me.creatures), 2)
        me.noncreature_cast = True
        bt.combat_tokens(me, opp, 3, entry())
        tok = me.creatures[-1]
        self.assertEqual((tok.card.name, tok.card.legendary, tok.card.end_sacrifice), ("Hero", False, True))
        self.assertTrue(bt.can_attack(tok, 3))
        del hero

    def test_replicator(self):
        me, _opp = pair()
        me.perms.append(C["replicator"])
        put(me, TOKEN)
        me.open = [("G",)] * 4
        bt.replicator_phase(me, 3, entry())
        bt.replicator_phase(me, 3, entry())  # einmal je Zug ({T})
        self.assertEqual(names(me), ["Officer", "Officer"])
        self.assertTrue(me.creatures[-1].tapped)

    def test_replicator_treasure(self):
        me, _opp = pair()
        me.perms.append(C["replicator"])
        me.treasures = 1
        me.open = [("G",)] * 2
        bt.replicator_phase(me, 3, entry())
        self.assertEqual(me.treasures, 2)


class GeorgiouTests(unittest.TestCase):
    def test_end_step_and_survival(self):
        me, opp = pair()
        put(me, C["georgiou"])
        me.life = 2
        bt.end_step_triggers(me, opp, entry())
        self.assertEqual((me.life, len(me.hand), names(me).count("Officer")), (-1, 1, 10))
        self.assertFalse(bt.game_lost(me))
        me.creatures = [c for c in me.creatures if c.card.name != "Georgiou, Terran Emperor"]
        self.assertTrue(bt.game_lost(me))

    def test_lose_effects_still_lose(self):
        me, _opp = pair()
        put(me, C["georgiou"])
        me.lost = True
        self.assertTrue(bt.game_lost(me))


if __name__ == "__main__":
    unittest.main()
