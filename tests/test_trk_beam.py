"""Star Trek (TRK): Beam me up {Kosten} - die Sorcery aus dem Friedhof fuer diese Kosten wirken, wenn man zusaetzlich
eine eigene Kreatur auf die Hand zurueckgibt; danach ins Exil (wie Flashback, in der eigenen Main Phase). Welche
Kreatur (Nutzer 2026-10-30): die mit dem wertvollsten Betreten-Effekt, sonst die billigste; Token nur zuletzt (sie
verschwinden); nie eine, ohne die ein toedlicher Gegenangriff moeglich wird. Scotty, Miracle Worker: in der eigenen
Main Phase hat jede Sorcery im Friedhof Beam me up zu ihren Manakosten, Scotty selbst wird dafuer nicht
zurueckgegeben. Nur Kampfmodell. Kartentexte aus TRK."""
import unittest

from components import battle as bt
from components.cards import card_info, token_card
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS, BEAR = W["Plains"], W["Test Bear"]
REMINDER = (" (You may cast this card from your graveyard for {cost} if you also return a creature you control to its "
            "owner's hand. Then exile this spell.)")


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)", produced=[color]))[0]


ISLAND = land("Island", "U")


def make(name, type_line, cost, cmc, text, power=None, toughness=None, colors="U"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, [], power, toughness))[0]


RAW_OPEN = _card("Open Communications", "Sorcery", "{U}", 1, "U", "Draw a card.\nBeam me up {2}{U}"
                 + REMINDER.format(cost="{2}{U}"))
OPEN = card_info(RAW_OPEN)[0]
RAW_SCOTTY = _card("Scotty, Miracle Worker", f"Legendary Creature {DASH} Human Artificer", "{1}{U}{U}", 3, "U",
                   "During your main phase, each card in your graveyard has beam me up. The beam me up cost is equal "
                   "to that spell's mana cost. Scotty can't be beamed up to cast a spell this way. (Only instant and "
                   "sorcery spells can be cast this way. You may cast a card from your graveyard for its beam me up "
                   "cost if you also return another creature you control to its owner's hand. Then exile that "
                   "spell.)", [], "2", "3")
SCOTTY = card_info(RAW_SCOTTY)[0]
PEEK = make("Test Peek", "Sorcery", "{1}{U}", 2, "Draw a card.")
SEER = make("Test Seer", f"Creature {DASH} Human", "{2}{U}", 3, "When this creature enters, draw a card.", "1", "1")
OGRE = make("Ogre", f"Creature {DASH} Ogre", "{2}{R}", 3, "", "3", "3", "R")
GIANT = make("Giant", f"Creature {DASH} Giant", "{5}{R}", 6, "", "8", "8", "R")
CADET = token_card("Cadet", True, 1, 1, False)


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def pair(library=None):
    me, opp = player(library=library), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": [], "land": ""}


def on_board(p, card, step=0):
    c = bt.Creature(card, step)
    c.ctl, c.gy = p, p.graveyard
    p.creatures.append(c)
    return c


class ParseTests(unittest.TestCase):
    def test_beam_cost(self):
        self.assertEqual(OPEN.beam, ((2, (("U", 1),)),))
        self.assertEqual(OPEN.draws, 1)

    def test_scotty(self):
        self.assertTrue(SCOTTY.scotty)
        self.assertEqual((BEAR.beam, BEAR.scotty), ((), False))

    def test_coverage(self):
        for r in (RAW_OPEN, RAW_SCOTTY):
            self.assertFalse([l for _c, _m, l in analyze_card(r) if "eam me up" in l], r["name"])


class PickTests(unittest.TestCase):
    def test_enter_effect_first(self):
        me, opp = pair()
        on_board(me, BEAR)
        seer = on_board(me, SEER)
        self.assertIs(bt.beam_pick(me, opp), seer)

    def test_cheapest_otherwise(self):
        me, opp = pair()
        on_board(me, OGRE)
        bear = on_board(me, BEAR)
        self.assertIs(bt.beam_pick(me, opp), bear)

    def test_token_last(self):
        me, opp = pair()
        on_board(me, CADET)
        ogre = on_board(me, OGRE)
        self.assertIs(bt.beam_pick(me, opp), ogre)
        me.creatures.remove(ogre)
        self.assertIs(bt.beam_pick(me, opp), me.creatures[0])

    def test_never_into_lethal(self):
        me, opp = pair()
        me.life = 8
        on_board(me, BEAR)
        on_board(opp, GIANT)  # 8 Schaden, wenn der Bear nicht mehr blockt
        self.assertIsNone(bt.beam_pick(me, opp))

    def test_not_scotty_himself(self):
        me, opp = pair()
        on_board(me, SCOTTY)
        self.assertIsNone(bt.beam_pick(me, opp, scotty=True))
        self.assertIsNotNone(bt.beam_pick(me, opp))  # mit eigenem Beam me up darf Scotty zurueck


class GraveyardTests(unittest.TestCase):
    def test_beam_versions(self):
        me, opp = pair()
        on_board(me, BEAR)
        me.graveyard = [OPEN, PEEK]
        got = bt.beam_versions(me, opp)
        self.assertEqual([(c.name, c.alts, orig) for c, orig in got], [("Open Communications", OPEN.beam, OPEN)])

    def test_without_creature_nothing(self):
        me, opp = pair()
        me.graveyard = [OPEN]
        self.assertEqual(bt.beam_versions(me, opp), [])

    def test_scotty_gives_mana_cost(self):
        me, opp = pair()
        on_board(me, SCOTTY)
        on_board(me, BEAR)
        me.graveyard = [PEEK, OPEN]
        got = {c.name: c.alts for c, _o in bt.beam_versions(me, opp)}
        self.assertEqual(got, {"Test Peek": PEEK.alts, "Open Communications": OPEN.beam})


class TurnTests(unittest.TestCase):
    def test_cast_from_graveyard_returns_a_creature(self):
        me, opp = pair(library=[OGRE] * 10)  # gezogen wird ein Ogre (kein Landdrop)
        me.lands = [ISLAND] * 3
        bear = on_board(me, BEAR)
        me.graveyard = [OPEN]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertNotIn(OPEN, me.graveyard)  # danach im Exil
        self.assertNotIn(bear, me.creatures)
        self.assertIn(BEAR, me.hand)
        self.assertEqual(len(me.hand), 2, e["events"])  # Bear und die gezogene Karte


if __name__ == "__main__":
    unittest.main()
