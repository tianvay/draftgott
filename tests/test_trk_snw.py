"""Star Trek (TRK): Strange new worlds - X ist die Zahl der Laender mit verschiedenen Namen, die wir kontrollieren,
immer zum Zeitpunkt der Wirkung gezaehlt (Stärke/Widerstand laufend). Nur Kampfmodell. Ensign Pavel Chekov und
Branching Timeline bewusst nicht (Nutzer 2026-10-30). Dazu Warp Speed (Laender kommen ungetappt, Basic Land suchen,
Opfern: zwei Karten ziehen). Kartentexte aus TRK."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
SNW = "Strange new worlds — "
WHERE = ", where X is the number of differently named lands you control"
PLAINS, BEAR = W["Plains"], W["Test Bear"]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)", produced=[color]))[0]


ISLAND, FOREST, MOUNTAIN, SWAMP = land("Island", "U"), land("Forest", "G"), land("Mountain", "R"), land("Swamp", "B")
WASTE = [card_info(_card(f"Planet {i}", f"Land {DASH} Planet", text="{T}: Add {C}.", produced=["C"]))[0]
         for i in range(6)]


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="G"):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords) + ["Strange new worlds"], power, toughness)


RAW = {
    "traveler": raw("The Traveler", f"Legendary Creature {DASH} Scout", "{G}{U}", 2, "Reach, vigilance\n" + SNW
                    + "The Traveler's power is equal to the number of differently named lands you control.", "*", "3",
                    ["Reach", "Vigilance"], "GU"),
    "pike": raw("Captain Pike, Fullness of Time", f"Legendary Creature {DASH} Human Officer Scout", "{1}{G}{G}", 3,
                SNW + "Captain Pike's power and toughness are each equal to the number of differently named lands you "
                "control.", "*", "*"),
    "excalbian": raw("Excalbian Gamemaster", f"Creature {DASH} Excalbian", "{5}{W}", 6, SNW + "When this creature "
                     "enters, create X 1/1 red Officer creature tokens" + WHERE + ".", "6", "6", colors="W"),
    "species": raw("Species 8472", f"Creature {DASH} Insect Beast", "{4}{G}{G}", 6, SNW + "When this creature enters, "
                   "you gain life equal to the number of differently named lands you control.", "6", "5"),
    "scan": raw("Deep Space Scan", "Sorcery", "{4}{U}{U}", 6, SNW + "Draw X cards" + WHERE + ". You have no maximum "
                "hand size until your next turn.", colors="U"),
    "cloak": raw("Cloak and Phaser", "Sorcery", "{8}{U}", 9, SNW + "This spell costs {X} less to cast" + WHERE
                 + ".\nCreate two 2/2 black Romulan creature tokens. Draw two cards, then discard a card.", colors="U"),
    "praxis": raw("The Destruction of Praxis", "Sorcery", "{3}{B}{B}", 5, SNW + "All creatures get -X/-X until end of "
                  "turn" + WHERE + ". If X is 6 or more, create two 2/1 red Klingon Warrior creature tokens with "
                  "haste.", colors="B"),
    "wraith": raw("Pah-Wraith", f"Creature {DASH} Wraith", "{5}{R}{R}", 7, "First strike, haste\n" + SNW + "Whenever "
                  "this creature attacks, creatures you control get +X/+0 until end of turn" + WHERE + ".", "5", "5",
                  ["First strike", "Haste"], "R"),
    "terraformer": raw("Astute Terraformer", f"Creature {DASH} Vulcan Scientist", "{1}{G}", 2, SNW + "{6}: This "
                       "creature gets +2/+2 until end of turn. This ability costs {X} less to activate" + WHERE
                       + ". Activate only once each turn.", "2", "2"),
    "suus": raw("Suus Mahna Practitioner", f"Creature {DASH} Vulcan Officer", "{2}{U}", 3, SNW + "{4}{U}, {T}: Tap "
                "target creature. This ability costs {X} less to activate" + WHERE + ".", "2", "3", colors="U"),
    "warp": raw("Warp Speed", "Enchantment", "{2}{G}", 3, "Lands you control enter untapped.\nWhen this enchantment "
                "enters, search your library for a basic land card or Planet card, reveal it, put it into your hand, "
                "then shuffle.\n" + SNW + "{7}{U}{U}, Sacrifice this enchantment: Draw two cards. This ability costs "
                "{X} less to activate" + WHERE + "."),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}
OGRE = card_info(_card("Ogre", f"Creature {DASH} Ogre", "{2}{R}", 3, "R", "", [], "3", "3"))[0]
GIANT = card_info(_card("Giant", f"Creature {DASH} Giant", "{4}{R}", 5, "R", "", [], "5", "5"))[0]


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def pair(library=None, lands=()):
    me, opp = player(library=library), player("Gegner")
    me.opponent, opp.opponent = opp, me
    me.lands = list(lands)
    return me, opp


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


THREE = [PLAINS, PLAINS, ISLAND, FOREST]  # drei verschiedene Namen


class ParseTests(unittest.TestCase):
    def test_power_and_toughness(self):
        self.assertEqual(C["traveler"].snw, (("pt", 1, 0),))
        self.assertEqual(C["pike"].snw, (("pt", 1, 1),))

    def test_enter_effects(self):
        kind, token = C["excalbian"].snw[0]
        self.assertEqual((kind, token.name, token.power, token.toughness), ("etb_tokens", "Officer", 1, 1))
        self.assertEqual(C["species"].snw, (("etb_life",),))

    def test_spells(self):
        self.assertEqual(C["scan"].snw, (("draw",),))
        self.assertEqual(C["cloak"].snw, (("discount",),))
        self.assertEqual(C["cloak"].creates_tokens[0][0], 2)  # der Rest der Karte bleibt erhalten
        kind, at, tokens = C["praxis"].snw[0]
        self.assertEqual((kind, at, tokens[0][0], tokens[0][1].name, tokens[0][1].haste),
                         ("sweep", 6, 2, "Klingon Warrior", True))
        self.assertEqual(C["praxis"].creates_tokens, ())  # Token nur ab X = 6

    def test_attack_and_abilities(self):
        self.assertEqual(C["wraith"].snw, (("attack_team",),))
        self.assertEqual(C["terraformer"].snw, (("ability_discount", True),))
        self.assertEqual(C["terraformer"].abilities[0][0], ((6, ()),))
        kind, costs = C["suus"].snw[0]
        self.assertEqual((kind, costs), ("tap_ability", ((4, (("U", 1),)),)))

    def test_warp_speed(self):
        kinds = [a[0] for a in C["warp"].snw]
        self.assertEqual(sorted(kinds), ["etb_basic", "lands_untapped", "sac_draw"])
        sac = next(a for a in C["warp"].snw if a[0] == "sac_draw")
        self.assertEqual(sac[1:], (((7, (("U", 2),)),), 2))

    def test_other_cards_unchanged(self):
        self.assertEqual((BEAR.snw, OGRE.snw), ((), ()))

    def test_coverage(self):
        for key, r in RAW.items():
            open_lines = [l for _c, _m, l in analyze_card(r)]
            self.assertFalse([l for l in open_lines if "differently named" in l or "enter untapped" in l
                              or "Planet card" in l], key)


class CountTests(unittest.TestCase):
    def test_differently_named(self):
        me, _opp = pair(lands=THREE)
        self.assertEqual(bt.snw_x(me), 3)
        me.lands += WASTE[:2]
        self.assertEqual(bt.snw_x(me), 5)

    def test_power_follows_lands(self):
        me, _opp = pair(lands=THREE)
        trav, pike = bt.Creature(C["traveler"], 0), bt.Creature(C["pike"], 0)
        me.creatures = [trav, pike]
        trav.ctl = pike.ctl = me
        self.assertEqual((trav.power, trav.toughness, pike.power, pike.toughness), (3, 3, 3, 3))
        me.lands.append(MOUNTAIN)
        self.assertEqual((trav.power, pike.toughness), (4, 4))


class EnterTests(unittest.TestCase):
    def test_excalbian_tokens(self):
        me, opp = pair(lands=THREE)
        bt._resolve(me, opp, C["excalbian"], 5, entry())
        names = sorted(c.card.name for c in me.creatures)
        self.assertEqual(names, ["Excalbian Gamemaster", "Officer", "Officer", "Officer"])

    def test_species_life(self):
        me, opp = pair(lands=THREE)
        bt._resolve(me, opp, C["species"], 5, entry())
        self.assertEqual(me.life, 23)


class SpellTests(unittest.TestCase):
    def test_scan_draws_and_no_hand_limit_this_turn(self):
        me, opp = pair(library=[BEAR] * 20, lands=THREE)
        me.hand = [BEAR] * 6
        bt._resolve(me, opp, C["scan"], 5, entry())
        self.assertEqual(len(me.hand), 9)
        bt.hand_limit(me, entry())
        self.assertEqual(len(me.hand), 9)  # kein Handlimit bis zu unserem naechsten Zug
        bt.hand_limit(me, entry())
        self.assertEqual(len(me.hand), 7)

    def test_cloak_costs_less(self):
        me, _opp = pair(lands=THREE)
        self.assertEqual(bt._alts(me, C["cloak"]), ((5, (("U", 1),)),))

    def test_praxis_kills_small_creatures(self):
        me, opp = pair(lands=[PLAINS, ISLAND])
        mine, theirs = bt.Creature(OGRE, 0), [bt.Creature(BEAR, 0), bt.Creature(BEAR, 0)]
        me.creatures, opp.creatures = [mine], theirs
        bt._resolve(me, opp, C["praxis"], 5, entry())
        self.assertEqual((opp.creatures, me.creatures), ([], [mine]))
        self.assertEqual((mine.power, mine.toughness), (1, 1))  # -2/-2 bis Rundenende

    def test_praxis_tokens_from_six(self):
        me, opp = pair(lands=WASTE)
        bt._resolve(me, opp, C["praxis"], 5, entry())
        self.assertEqual([(c.card.name, c.card.haste) for c in me.creatures],
                         [("Klingon Warrior", True), ("Klingon Warrior", True)])

    def test_praxis_cast_only_when_it_pays_off(self):
        me, opp = pair(lands=[PLAINS, ISLAND])
        me.hand = [C["praxis"]]
        opp.creatures = [bt.Creature(BEAR, 0)]
        self.assertIn(C["praxis"], bt.main_phase_spells(me, opp))
        me.creatures = [bt.Creature(BEAR, 0), bt.Creature(BEAR, 0)]  # mehr eigene Verluste
        self.assertNotIn(C["praxis"], bt.main_phase_spells(me, opp))
        me.creatures, opp.creatures = [], [bt.Creature(GIANT, 0)]  # toetet nichts
        self.assertNotIn(C["praxis"], bt.main_phase_spells(me, opp))


class AbilityTests(unittest.TestCase):
    def test_wraith_pumps_the_team(self):
        me, _opp = pair(lands=THREE)
        wraith, bear = bt.Creature(C["wraith"], 0), bt.Creature(BEAR, 0)
        me.creatures = [wraith, bear]
        bt.attack_keywords(me, [wraith, bear], None, entry())
        self.assertEqual((wraith.power, bear.power), (8, 5))

    def test_terraformer_cheaper_and_once(self):
        me, _opp = pair(lands=THREE)
        terra = bt.Creature(C["terraformer"], 0)
        me.creatures = [terra]
        me.now = 5
        srcs = bt.ability_sources(me, 5, True)
        self.assertEqual([ab[0] for _c, ab in srcs], [((3, ()),)])
        me.open = [("G",)] * 3
        self.assertTrue(bt._activate(me, terra, srcs[0][1], None, entry(), "rest"))
        self.assertEqual((terra.power, bt.ability_sources(me, 5, True)), (4, []))

    def test_suus_taps_the_blocker(self):
        me, opp = pair(lands=THREE)
        suus, att = bt.Creature(C["suus"], 0), bt.Creature(OGRE, 0)
        blocker = bt.Creature(BEAR, 0)
        me.creatures, opp.creatures = [suus, att], [blocker]
        me.open, me.turn_start = [("U",), ("U",)], 5
        bt.snw_tap_blocker(me, opp, 5, entry())
        self.assertEqual((blocker.tapped, suus.tapped, me.open), (True, True, []))

    def test_suus_without_mana(self):
        me, opp = pair(lands=THREE)
        suus, att, blocker = bt.Creature(C["suus"], 0), bt.Creature(OGRE, 0), bt.Creature(BEAR, 0)
        me.creatures, opp.creatures, me.open, me.turn_start = [suus, att], [blocker], [("U",)], 5
        bt.snw_tap_blocker(me, opp, 5, entry())
        self.assertFalse(blocker.tapped)


class WarpSpeedTests(unittest.TestCase):
    def test_lands_enter_untapped(self):
        me, _opp = pair()
        self.assertTrue(bt.land_tapped(me, True))
        me.perms = [C["warp"]]
        self.assertFalse(bt.land_tapped(me, True))

    def test_enter_searches_a_basic(self):
        me, opp = pair(library=[BEAR] * 5 + [FOREST])
        bt._resolve(me, opp, C["warp"], 5, entry())
        self.assertEqual(me.hand, [FOREST])

    def test_sacrifice_draws_two(self):
        me, opp = pair(library=[BEAR] * 5, lands=THREE + [MOUNTAIN, SWAMP])  # X = 5: {2}{U}{U}
        me.perms = [C["warp"]]
        me.open = [("U",)] * 4
        bt.snw_sac_draw(me, entry())
        self.assertEqual((len(me.hand), me.perms, me.graveyard, me.open), (2, [], [C["warp"]], []))

    def test_sacrifice_needs_mana(self):
        me, opp = pair(library=[BEAR] * 5, lands=THREE)
        me.perms, me.open = [C["warp"]], [("U",)] * 4  # X = 3: {4}{U}{U}
        bt.snw_sac_draw(me, entry())
        self.assertEqual((me.hand, me.perms), ([], [C["warp"]]))


if __name__ == "__main__":
    unittest.main()
