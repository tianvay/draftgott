"""Ein Planeswalker, der aus dem Friedhof aufs Feld kommt, ist ein neues Objekt (400.7) und hat so viel Loyalty, als ob
er gewirkt worden waere (306.5b); er darf im selben Zug aktivieren."""
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]


def make(name, type_line, cost, cmc, text, colors="B"):
    return card_info(_card(name, type_line, cost, cmc, colors, text))[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


SWAMP = land("Swamp", "B")
TORCH = card_info(dict(_card("Chandra, Torch of Defiance", f"Legendary Planeswalker {DASH} Chandra", "{2}{R}{R}", 4, "R",
                             "+1: Exile the top card of your library. You may cast that card. If you don't, Chandra "
                             "deals 2 damage to each opponent.\n+1: Add {R}{R}.\n−3: Chandra deals 4 damage to target "
                             "creature.\n−7: You get an emblem with \"Whenever you cast a spell, this emblem deals 5 "
                             "damage to any target.\""), loyalty="4"))[0]
REVIVE = make("Grave Return", "Sorcery", "{2}{B}", 3, "Return target permanent card from your graveyard to the "
              "battlefield.")


def pair():
    me = bt.Player("Wir", [PLAINS] * 30, mulligan=False)
    opp = bt.Player("Gegner", [PLAINS] * 30, mulligan=False)
    for p in (me, opp):
        p.hand, p.library = [], [PLAINS] * 20
    me.opponent, opp.opponent = opp, me
    return me, opp


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


class GraveyardWalkerTests(unittest.TestCase):
    def test_put_back_is_a_real_walker(self):
        me, opp = pair()
        bt.put_back(me, TORCH, "battlefield", 5, entry(), opp)
        self.assertEqual(([w.card.name for w in me.walkers], me.walkers[0].loyalty, me.perms),
                         ([TORCH.name], 4, []))

    def test_reanimate_spell(self):
        self.assertEqual(REVIVE.reanimate[1:4], ("permanent", 99, "battlefield"))
        me, opp = pair()
        me.graveyard = [TORCH]
        me.lands, me.hand = [SWAMP] * 3, [REVIVE]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((TORCH in me.graveyard, [w.card.name for w in me.walkers]), (False, [TORCH.name]))
        self.assertEqual((me.walkers[0].loyalty, opp.life), (5, 18))  # aktiviert im selben Zug (+1)


if __name__ == "__main__":
    unittest.main()
