"""SOS Paket G: Kartenfluss und Suche - oberste Karten ansehen (Flow State, Zimone's Experiment, Paradox Surveyor,
Stirring Honormancer, Visionary's Dance aus der Hand, Geometer's Arthropod), Suchen (Dina's Guidance, Planar
Engineering), Ziehen (Embrace the Paradox, Mind into Matter, Mathemagics, Colossus of the Blood Age beim Tod, Tenured
Concocter), Mill und in diesem Zug spielen (Tablet of Discovery, Ark of Hunger), Bind to Life und Mind Roots.
Kartentexte aus Secrets of Strixhaven (SOS)."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS, ISLAND = W["Plains"], W["Island"]
BEAR = W["Test Bear"]


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="U"):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)


RAW = {
    "flow": raw("Flow State", "Sorcery", "{1}{U}", 2,
                "Look at the top three cards of your library. Put one of them into your hand and the rest on the bottom "
                "of your library in any order. If there is an instant card and a sorcery card in your graveyard, "
                "instead put two of them into your hand and the rest on the bottom of your library in any order."),
    "zimone": raw("Zimone's Experiment", "Sorcery", "{3}{G}", 4,
                  "Look at the top five cards of your library. You may reveal up to two creature and/or land cards from "
                  "among them, then put the rest on the bottom of your library in a random order. Put all land cards "
                  "revealed this way onto the battlefield tapped and put all creature cards revealed this way into "
                  "your hand.", colors="G"),
    "surveyor": raw("Paradox Surveyor", f"Creature {DASH} Elf Druid", "{G}{G/U}{U}", 3,
                    "Reach\nWhen this creature enters, look at the top five cards of your library. You may reveal a "
                    "land card or a card with {X} in its mana cost from among them and put it into your hand. Put the "
                    "rest on the bottom of your library in a random order.", "3", "3", ["Reach"], "GU"),
    "honormancer": raw("Stirring Honormancer", f"Creature {DASH} Rhino Bard", "{2}{W}{W/B}{B}", 5,
                       "When this creature enters, look at the top X cards of your library, where X is the number of "
                       "creatures you control. Put one of those cards into your hand and the rest into your "
                       "graveyard.", "4", "5", colors="WB"),
    "dance": raw("Visionary's Dance", "Sorcery", "{5}{U}{R}", 7,
                 "Create two 3/3 blue and red Elemental creature tokens with flying.\n{2}, Discard this card: Look at "
                 "the top two cards of your library. Put one of them into your hand and the other into your "
                 "graveyard.", colors="UR"),
    "dina": raw("Dina's Guidance", "Instant", "{1}{B}{G}", 3,
                "Search your library for a creature card, reveal it, put it into your hand or graveyard, then shuffle.",
                colors="BG"),
    "embrace": raw("Embrace the Paradox", "Instant", "{3}{G}{U}", 5,
                   "Draw three cards. You may put a land card from your hand onto the battlefield tapped.",
                   colors="GU"),
    "mind": raw("Mind into Matter", "Sorcery", "{X}{G}{U}", 2,
                "Draw X cards. Then you may put a permanent card with mana value X or less from your hand onto the "
                "battlefield tapped.", colors="GU"),
    "planar": raw("Planar Engineering", "Sorcery", "{3}{G}", 4,
                  "Sacrifice two lands. Search your library for four basic land cards, put them onto the battlefield "
                  "tapped, then shuffle.", colors="G"),
    "colossus": raw("Colossus of the Blood Age", f"Artifact Creature {DASH} Construct", "{4}{R}{W}", 6,
                    "When this creature enters, it deals 3 damage to each opponent and you gain 3 life.\nWhen this "
                    "creature dies, discard any number of cards, then draw that many cards plus one.", "6", "6",
                    colors="RW"),
    "concocter": raw("Tenured Concocter", f"Creature {DASH} Troll Druid", "{4}{G}", 5,
                     "Vigilance\nWhenever this creature becomes the target of a spell or ability an opponent controls, "
                     "you may draw a card.\nInfusion — This creature gets +2/+0 as long as you gained life this turn.",
                     "4", "5", ["Infusion", "Vigilance"], "G"),
    "tablet": raw("Tablet of Discovery", "Artifact", "{2}{R}", 3,
                  "When this artifact enters, mill a card. You may play that card this turn. (To mill a card, put the "
                  "top card of your library into your graveyard.)\n{T}: Add {R}.\n{T}: Add {R}{R}. Spend this mana "
                  "only to cast instant and sorcery spells.", keywords=["Mill"], colors="R"),
    "ark": raw("Ark of Hunger", "Artifact", "{2}{R}{W}", 4,
               "Whenever one or more cards leave your graveyard, this artifact deals 1 damage to each opponent and you "
               "gain 1 life.\n{T}: Mill a card. You may play that card this turn.", keywords=["Mill"], colors="RW"),
    "arthropod": raw("Geometer's Arthropod", f"Creature {DASH} Fractal Crab", "{G}{U}", 2,
                     "Whenever you cast a spell with {X} in its mana cost, look at the top X cards of your library. Put "
                     "one of them into your hand and the rest on the bottom of your library in a random order.", "1",
                     "4", colors="GU"),
    "mathemagics": raw("Mathemagics", "Sorcery", "{X}{X}{U}{U}", 2,
                       "Target player draws 2ˣ cards. (2⁰ = 1, 2¹ = 2, 2² = 4, 2³ = 8, 2⁴ = 16, 2⁵ = 32, and so on.)"),
    "bind": raw("Bind to Life", "Instant", "{4}{G}", 5,
                "Mill seven cards. Then put a creature card from among them onto the battlefield.", colors="G"),
    "roots": raw("Mind Roots", "Sorcery", "{1}{B}{G}", 3,
                 "Target player discards two cards. Put up to one land card discarded this way onto the battlefield "
                 "tapped under your control.", colors="BG"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}

TITAN = card_info(raw("Titan", "Creature — Giant", "{4}{G}", 5, "", "5", "5", colors="G"))[0]
OGRE = card_info(raw("Ogre", "Creature — Ogre", "{2}{R}", 3, "", "3", "3", colors="R"))[0]
CHEAP = card_info(raw("Quick Thought", "Sorcery", "{U}", 1, "Draw a card."))[0]
ZAP = card_info(raw("Zap", "Instant", "{R}", 1, "Zap deals 1 damage to any target.", colors="R"))[0]
XSPELL = card_info(raw("X Thought", "Sorcery", "{X}{U}", 1, "Target player gains X life."))[0]


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
    def test_digs(self):
        self.assertEqual((C["flow"].top_dig, C["flow"].dig_two_gy), ((3, "any", False), True))
        self.assertTrue(C["zimone"].zimone)
        self.assertEqual(C["surveyor"].top_dig, (5, "land_x", False))
        self.assertEqual((C["honormancer"].top_dig, C["honormancer"].dig_creatures), ((0, "any", True), True))
        self.assertTrue(C["dance"].hand_dig)
        self.assertTrue(C["arthropod"].x_dig)

    def test_search_and_draw(self):
        self.assertEqual(C["dina"].tutor, ("creature",))
        self.assertEqual((C["embrace"].draws, C["embrace"].land_from_hand), (3, True))
        self.assertTrue(C["mind"].mind_matter and C["mind"].x_cost)
        self.assertTrue(C["planar"].planar)
        self.assertTrue(C["colossus"].colossus_death)
        self.assertEqual(C["concocter"].targeted_draw, 1)
        self.assertTrue(C["mathemagics"].mathemagics)

    def test_mill_play_and_others(self):
        self.assertEqual(C["tablet"].mill_play, 1)
        self.assertTrue(C["ark"].mill_play_ability)
        self.assertTrue(C["bind"].bind_life)
        self.assertTrue(C["roots"].mind_roots)


class CoverageTests(unittest.TestCase):
    def test_cards_fully_modelled(self):
        for key in RAW:
            self.assertEqual([line for _c, _m, line in analyze_card(RAW[key])], [], key)


class DigTests(unittest.TestCase):
    def test_flow_state_one_or_two(self):
        me, opp = pair()
        me.library = [CHEAP, TITAN, OGRE] + [PLAINS] * 5
        bt._resolve(me, opp, C["flow"], 3, entry())
        self.assertEqual(len(me.hand), 1)
        me, opp = pair()
        me.graveyard.extend([CHEAP, ZAP])
        me.library = [CHEAP, TITAN, OGRE] + [PLAINS] * 5
        bt._resolve(me, opp, C["flow"], 3, entry())
        self.assertEqual(len(me.hand), 2)
        self.assertEqual(len(me.library), 6)

    def test_zimone_lands_to_battlefield_creatures_to_hand(self):
        me, opp = pair()
        me.library = [CHEAP, TITAN, PLAINS, CHEAP, CHEAP] + [CHEAP] * 3
        bt._resolve(me, opp, C["zimone"], 3, entry())
        self.assertEqual((me.hand, len(me.lands)), ([TITAN], 1))

    def test_surveyor_land_or_x(self):
        me, opp = pair()
        me.library = [CHEAP, TITAN, XSPELL, CHEAP, CHEAP] + [CHEAP] * 3
        bt._resolve(me, opp, C["surveyor"], 3, entry())
        self.assertEqual(me.hand, [XSPELL])

    def test_honormancer_x_creatures(self):
        me, opp = pair()
        on_board(me, BEAR)
        me.library = [CHEAP, TITAN, OGRE, CHEAP] + [PLAINS] * 4
        bt._resolve(me, opp, C["honormancer"], 3, entry())
        self.assertEqual(len(me.hand), 1)
        self.assertEqual(len(me.graveyard), 1)  # X = 2 (Bear und Honormancer)

    def test_dance_from_hand_far_from_casting(self):
        dfn, act = pair()
        dfn.lands = [PLAINS] * 3
        dfn.hand, dfn.open = [C["dance"]], [("U",), ("U",)]
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertNotIn(C["dance"], dfn.hand)
        self.assertEqual(len(dfn.hand), 1)

    def test_arthropod_x_spell(self):
        me, opp = pair()
        on_board(me, C["arthropod"])
        me.hand = [ISLAND]  # mit Land auf der Hand nimmt dig_pick die Nichtland-Karte
        me.library = [PLAINS, TITAN, PLAINS] + [PLAINS] * 5
        me.next_x = 3
        bt.on_cast(me, XSPELL, 3, entry())
        self.assertEqual(me.hand, [ISLAND, TITAN])


class SearchDrawTests(unittest.TestCase):
    def test_dina_creature(self):
        me, opp = pair()
        me.library = [PLAINS] * 5 + [TITAN]
        me.lands = [PLAINS] * 4
        bt._resolve(me, opp, C["dina"], 3, entry())
        self.assertIn(TITAN, me.hand)

    def test_embrace_land_from_hand(self):
        me, opp = pair()
        me.hand = [ISLAND]
        bt._resolve(me, opp, C["embrace"], 3, entry())
        self.assertEqual(len(me.lands), 1)
        self.assertEqual(len(me.hand), 3)

    def test_mind_into_matter(self):
        me, opp = pair()
        me.library = [OGRE, PLAINS, PLAINS] + [PLAINS] * 5
        me.next_x = 3
        bt._resolve(me, opp, C["mind"], 3, entry())
        self.assertTrue(any(c.card is OGRE and c.tapped for c in me.creatures))
        self.assertEqual(me.next_x, 0)

    def test_planar_engineering(self):
        me, opp = pair()
        me.lands = [ISLAND, ISLAND, ISLAND]
        bt._resolve(me, opp, C["planar"], 3, entry())
        self.assertEqual(len(me.lands), 5)

    def test_planar_needs_two_lands_and_basics(self):
        me, opp = pair()
        me.hand = [C["planar"]]
        me.lands = [ISLAND]
        self.assertNotIn(C["planar"], bt.main_phase_spells(me, opp))
        me.lands = [ISLAND, ISLAND]
        self.assertIn(C["planar"], bt.main_phase_spells(me, opp))

    def test_colossus_death_rummage(self):
        me, opp = pair()
        me.lands = [PLAINS] * 6
        me.hand = [PLAINS, PLAINS, CHEAP]
        col = on_board(me, C["colossus"])
        col.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual(len(me.hand), 4)  # zwei Laender ab, drei gezogen
        self.assertIn(CHEAP, me.hand)

    def test_mathemagics(self):
        me, opp = pair()
        me.next_x = 2
        bt._resolve(me, opp, C["mathemagics"], 3, entry())
        self.assertEqual(len(me.hand), 4)


class MillPlayTests(unittest.TestCase):
    def test_tablet_mills_and_allows_play(self):
        me, opp = pair()
        me.library = [CHEAP] + [PLAINS] * 5
        bt._resolve(me, opp, C["tablet"], 3, entry())
        self.assertTrue(any(c is CHEAP for c, _t in me.impulse))

    def test_ark_once_per_turn_in_main1(self):
        me, opp = pair()
        me.perms.append(C["ark"])
        me.library = [CHEAP, CHEAP] + [PLAINS] * 5
        bt.sos_main1(me, opp, 3, entry())
        bt.sos_main1(me, opp, 3, entry())
        self.assertEqual(len(me.impulse), 1)

    def test_bind_to_life(self):
        me, opp = pair()
        me.library = [PLAINS, OGRE, TITAN, PLAINS, PLAINS, PLAINS, PLAINS, PLAINS]
        bt._resolve(me, opp, C["bind"], 3, entry())
        self.assertTrue(any(c.card is TITAN for c in me.creatures))
        self.assertIn(OGRE, me.graveyard)

    def test_mind_roots_steals_land(self):
        me, opp = pair()
        opp.hand = [PLAINS, CHEAP]
        bt._resolve(me, opp, C["roots"], 3, entry())
        self.assertEqual((len(opp.hand), len(me.lands)), (0, 1))


if __name__ == "__main__":
    unittest.main()
