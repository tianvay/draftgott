"""Absturz aus dem Kampfbericht (Splash gegen bad creatures): Mana fuer ein Flash-Removal bzw. einen Counterspell wird
nur aus Laendern und Artefakten offen gehalten, nie aus Mana-Kreaturen (deren Mana zaehlt im gegnerischen Zug ohnehin
nicht zum offenen Mana). Vorher konnte die Mana-Einheit einer Kreatur im offen gehaltenen Mana landen; das Tappen der
Mana-Kreaturen fuer die Zauber fand sie dann nicht mehr (ValueError)."""
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS, BEAR = W["Plains"], W["Test Bear"]


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="G"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


DORK = make("Greenhouse Dork", CRE, "{G}", 1, "{T}: Add {G}.", "1", "1")
KILL = make("Quick Kill", "Instant", "{G}", 1, "Destroy target creature.")
OGRE = make("Ogre", CRE, "{2}{R}", 3, "", "3", "3", colors="R")


def pair():
    me = bt.Player("Wir", [PLAINS] * 30, mulligan=False)
    opp = bt.Player("Gegner", [PLAINS] * 30, mulligan=False)
    for p in (me, opp):
        p.hand, p.library = [], [PLAINS] * 20
    me.opponent, opp.opponent = opp, me
    return me, opp


class HeldManaTests(unittest.TestCase):
    def test_no_crash_and_no_creature_mana_held(self):
        me, opp = pair()
        dork = bt.Creature(DORK, 0)
        dork.gy, dork.ctl = me.graveyard, me
        me.creatures.append(dork)
        foe = bt.Creature(OGRE, 0)
        foe.gy, foe.ctl = opp.graveyard, opp
        opp.creatures.append(foe)
        me.lands, me.hand = [PLAINS], [KILL, BEAR]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)  # vorher: ValueError
        self.assertIn("Test Bear", [c.card.name for c in me.creatures])
        self.assertFalse(any(ev.startswith("Wir: hält") for ev in e["events"]))  # {G} nur von der Kreatur


if __name__ == "__main__":
    unittest.main()
