"""SOS Paket J: die schwersten Einzelkarten - Paradigm (Lessons nach dem ersten Aufloesen jede erste Main Phase
kostenlos), Elder Dragons (Prismari: Storm, Quandrix: Cascade, Silverquill: Casualty 1, Witherbloom: Affinity fuer
Kreaturen), Zaffai, Improvisation Capstone, Fix What's Broken, Moment of Reckoning, Pox Plague, Page, Loose Leaf und
Fractalize. Kartentexte aus Secrets of Strixhaven (SOS)."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]
BEAR = W["Test Bear"]
PARADIGM = ("Paradigm (Then exile this spell. After you first resolve a spell with this name, you may cast a copy of it "
            "from exile without paying its mana cost at the beginning of each of your first main phases.)")


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="U"):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)


RAW = {
    "seminar": raw("Restoration Seminar", f"Sorcery {DASH} Lesson", "{5}{W}{W}", 7,
                   "Return target nonland permanent card from your graveyard to the battlefield.\n" + PARADIGM,
                   keywords=["Paradigm"], colors="W"),
    "symposium": raw("Echocasting Symposium", f"Sorcery {DASH} Lesson", "{4}{U}{U}", 6,
                     "Target player creates a token that's a copy of target creature you control.\n" + PARADIGM,
                     keywords=["Paradigm"]),
    "dissertation": raw("Decorum Dissertation", f"Sorcery {DASH} Lesson", "{3}{B}{B}", 5,
                        "Target player draws two cards and loses 2 life.\n" + PARADIGM, keywords=["Paradigm"],
                        colors="B"),
    "practicum": raw("Germination Practicum", f"Sorcery {DASH} Lesson", "{3}{G}{G}", 5,
                     "Put two +1/+1 counters on each creature you control.\n" + PARADIGM, keywords=["Paradigm"],
                     colors="G"),
    "capstone": raw("Improvisation Capstone", f"Sorcery {DASH} Lesson", "{5}{R}{R}", 7,
                    "Exile cards from the top of your library until you exile cards with total mana value 4 or greater. "
                    "You may cast any number of spells from among them without paying their mana costs.\n" + PARADIGM,
                    keywords=["Paradigm"], colors="R"),
    "fractalize": raw("Fractalize", "Instant", "{X}{U}", 1,
                      "Until end of turn, target creature becomes a green and blue Fractal with base power and toughness "
                      "each equal to X plus 1. (It loses all other colors and creature types.)"),
    "pox": raw("Pox Plague", "Sorcery", "{B}{B}{B}{B}{B}", 5,
               "Each player loses half their life, then discards half the cards in their hand, then sacrifices half the "
               "permanents they control of their choice. Round down each time.", colors="B"),
    "fix": raw("Fix What's Broken", "Sorcery", "{2}{W}{B}", 4,
               "As an additional cost to cast this spell, pay X life.\nReturn each artifact and creature card with mana "
               "value X from your graveyard to the battlefield.", colors="WB"),
    "reckoning": raw("Moment of Reckoning", "Sorcery", "{3}{W}{W}{B}{B}", 7,
                     "Choose up to four. You may choose the same mode more than once.\n• Destroy target nonland "
                     "permanent.\n• Return target nonland permanent card from your graveyard to the battlefield.",
                     colors="WB"),
    "prismari": raw("Prismari, the Inspiration", f"Legendary Creature {DASH} Elder Dragon", "{5}{U}{R}", 7,
                    "Flying\nWard—Pay 5 life.\nInstant and sorcery spells you cast have storm. (Whenever you cast an "
                    "instant or sorcery spell, copy it for each spell cast before it this turn. You may choose new "
                    "targets for the copies.)", "7", "7", ["Flying", "Ward"], "UR"),
    "quandrix": raw("Quandrix, the Proof", f"Legendary Creature {DASH} Elder Dragon", "{4}{G}{U}", 6,
                    "Flying, trample\nCascade (When you cast this spell, exile cards from the top of your library until "
                    "you exile a nonland card that costs less. You may cast it without paying its mana cost. Put the "
                    "exiled cards on the bottom in a random order.)\nInstant and sorcery spells you cast from your hand "
                    "have cascade.", "6", "6", ["Flying", "Trample", "Cascade"], "GU"),
    "silverquill": raw("Silverquill, the Disputant", f"Legendary Creature {DASH} Elder Dragon", "{2}{W}{B}", 4,
                       "Flying, vigilance\nEach instant and sorcery spell you cast has casualty 1. (As you cast that "
                       "spell, you may sacrifice a creature with power 1 or greater. When you do, copy the spell and "
                       "you may choose new targets for the copy.)", "4", "4", ["Flying", "Vigilance"], "WB"),
    "witherbloom": raw("Witherbloom, the Balancer", f"Legendary Creature {DASH} Elder Dragon", "{6}{B}{G}", 8,
                       "Affinity for creatures (This spell costs {1} less to cast for each creature you control.)\n"
                       "Flying, deathtouch\nInstant and sorcery spells you cast have affinity for creatures.", "5", "5",
                       ["Affinity", "Flying", "Deathtouch"], "BG"),
    "zaffai": raw("Zaffai and the Tempests", f"Legendary Creature {DASH} Human Bard Sorcerer", "{5}{U}{R}", 7,
                  "Once during each of your turns, you may cast an instant or sorcery spell from your hand without "
                  "paying its mana cost.", "5", "7", colors="UR"),
    "page": raw("Page, Loose Leaf", f"Legendary Artifact Creature {DASH} Construct", "{2}", 2,
                "{T}: Add {C}.\nGrandeur — Discard another card named Page, Loose Leaf: Reveal cards from the top of "
                "your library until you reveal an instant or sorcery card. Put that card into your hand and the rest on "
                "the bottom of your library in a random order.", "0", "2", ["Grandeur"], ""),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}

TITAN = card_info(raw("Titan", "Creature — Giant", "{4}{G}", 5, "", "5", "5", colors="G"))[0]
OGRE = card_info(raw("Ogre", "Creature — Ogre", "{2}{R}", 3, "", "3", "3", colors="R"))[0]
MOUSE = card_info(raw("Mouse", "Creature — Mouse", "{W}", 1, "", "1", "1", colors="W"))[0]
THOUGHT = card_info(raw("Quick Thought", "Sorcery", "{U}", 1, "Draw a card."))[0]
BIG = card_info(raw("Big Thought", "Sorcery", "{4}{U}", 5, "Draw two cards."))[0]
BOLT = card_info(raw("Bolt", "Instant", "{R}", 1, "Bolt deals 3 damage to target creature.", colors="R"))[0]


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


class ParseTests(unittest.TestCase):
    def test_paradigm(self):
        for key in ("seminar", "symposium", "dissertation", "practicum", "capstone"):
            self.assertTrue(C[key].paradigm, key)
        self.assertTrue(C["capstone"].capstone)

    def test_dragons(self):
        self.assertTrue(C["prismari"].storm_grant)
        self.assertEqual((C["quandrix"].cascade, C["quandrix"].cascade_grant), (True, True))
        self.assertTrue(C["silverquill"].casualty_grant)
        self.assertEqual((C["witherbloom"].self_discount, C["witherbloom"].affinity_grant), (("creatures",), True))

    def test_others(self):
        self.assertTrue(C["zaffai"].zaffai)
        self.assertTrue(C["page"].grandeur)
        self.assertTrue(C["fractalize"].fractalize)
        self.assertTrue(C["pox"].pox)
        self.assertTrue(C["fix"].fix_broken)
        self.assertEqual((C["reckoning"].reckoning, C["reckoning"].removal), (True, ()))


class CoverageTests(unittest.TestCase):
    def test_cards_fully_modelled(self):
        for key in RAW:
            self.assertEqual([line for _c, _m, line in analyze_card(RAW[key])], [], key)


class ParadigmTests(unittest.TestCase):
    def test_lesson_exiled_and_recast_each_main1(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        bt._resolve(me, opp, C["practicum"], 3, entry())
        self.assertEqual(bear.bonus, 2)
        self.assertNotIn(C["practicum"], me.graveyard)
        bt.sos_main1(me, opp, 5, entry())
        self.assertEqual(bear.bonus, 4)

    def test_dissertation_only_with_enough_life(self):
        me, opp = pair()
        bt._resolve(me, opp, C["dissertation"], 3, entry())
        self.assertEqual((len(me.hand), me.life), (2, 18))
        me.life = 5
        bt.sos_main1(me, opp, 5, entry())
        self.assertEqual(len(me.hand), 2)

    def test_capstone_casts_free(self):
        me, opp = pair()
        me.library = [PLAINS, OGRE, MOUSE] + [PLAINS] * 5
        bt._resolve(me, opp, C["capstone"], 3, entry())
        self.assertTrue(any(c.card is OGRE for c in me.creatures))
        self.assertTrue(any(c.card is MOUSE for c in me.creatures))


class DragonTests(unittest.TestCase):
    def test_prismari_storm(self):
        me, opp = pair()
        on_board(me, C["prismari"])
        bt._resolve(me, opp, THOUGHT, 3, entry())
        bt._resolve(me, opp, THOUGHT, 3, entry())  # zweiter Zauber: eine Storm-Kopie
        self.assertEqual(len(me.hand), 3)

    def test_quandrix_cascade_on_instsorc(self):
        me, opp = pair()
        on_board(me, C["quandrix"])
        me.library = [PLAINS, OGRE] + [PLAINS] * 5
        bt._resolve(me, opp, BIG, 3, entry())  # Manawert 5: kaskadiert in den Ogre
        self.assertTrue(any(c.card is OGRE for c in me.creatures))

    def test_quandrix_own_cascade(self):
        me, opp = pair()
        me.library = [PLAINS, TITAN, OGRE] + [PLAINS] * 5
        bt._resolve(me, opp, C["quandrix"], 3, entry())
        self.assertTrue(any(c.card is TITAN for c in me.creatures))

    def test_silverquill_casualty_token(self):
        me, opp = pair()
        on_board(me, C["silverquill"])
        token = on_board(me, bt.INKLING)
        bt._resolve(me, opp, THOUGHT, 3, entry())
        self.assertNotIn(token, me.creatures)
        self.assertEqual(len(me.hand), 2)

    def test_witherbloom_affinity(self):
        me, opp = pair()
        for _ in range(3):
            on_board(me, MOUSE)
        self.assertEqual(bt.own_reduction(me, C["witherbloom"]), 3)
        on_board(me, C["witherbloom"])
        self.assertEqual(bt._alts(me, BIG), ((0, (("U", 1),)),))


class OtherTests(unittest.TestCase):
    def test_zaffai_free_spell_once(self):
        me, opp = pair()
        on_board(me, C["zaffai"])
        me.hand = [BIG, THOUGHT]
        bt.sos_main1(me, opp, 3, entry())
        self.assertNotIn(BIG, me.hand)
        bt.sos_main1(me, opp, 3, entry())
        self.assertIn(THOUGHT, me.hand)

    def test_fix_whats_broken(self):
        me, opp = pair()
        me.graveyard.extend([OGRE, OGRE, MOUSE])
        bt._resolve(me, opp, C["fix"], 3, entry())
        self.assertEqual(sum(1 for c in me.creatures if c.card is OGRE), 2)
        self.assertEqual(me.life, 17)

    def test_reckoning_destroys_and_returns(self):
        me, opp = pair()
        on_board(opp, TITAN)
        on_board(opp, OGRE)
        me.graveyard.append(BEAR)
        bt._resolve(me, opp, C["reckoning"], 3, entry())
        self.assertEqual(opp.creatures, [])
        self.assertTrue(any(c.card is BEAR for c in me.creatures))

    def test_pox_plague_halves(self):
        me, opp = pair()
        me.life, opp.life = 20, 15
        opp.hand = [THOUGHT] * 4
        for _ in range(4):
            on_board(opp, MOUSE)
        bt._resolve(me, opp, C["pox"], 3, entry())
        self.assertEqual((me.life, opp.life, len(opp.hand), len(opp.creatures)), (10, 8, 2, 2))

    def test_pox_only_when_behind_on_board(self):
        me, opp = pair()
        me.hand = [C["pox"]]
        on_board(me, TITAN)
        self.assertNotIn(C["pox"], bt.main_phase_spells(me, opp))
        for _ in range(4):
            on_board(opp, OGRE)
        self.assertIn(C["pox"], bt.main_phase_spells(me, opp))

    def test_page_grandeur(self):
        dfn, act = pair()
        on_board(dfn, C["page"])
        dfn.hand = [C["page"]]
        dfn.library = [PLAINS, PLAINS, BOLT] + [PLAINS] * 5
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual(dfn.hand, [BOLT])

    def test_fractalize_shrinks_blocker(self):
        me, opp = pair()
        me.open, me.hand = [("U",)], [C["fractalize"]]
        ogre = on_board(me, OGRE)
        titan = on_board(opp, TITAN)
        bt.combat_tricks(me, [(ogre, [titan])], opp, entry(), 3, True)
        self.assertNotIn(C["fractalize"], me.hand)
        self.assertEqual((titan.power, titan.toughness), (1, 1))


if __name__ == "__main__":
    unittest.main()
