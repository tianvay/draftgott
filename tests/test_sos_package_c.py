"""SOS Paket C: Leben und Infusion (Witherbloom) - Pest-Token mit Lebensgewinn beim Angriff, Leben beim Betreten
eigener Kreaturen, Lebensgewinn-Ausloeser (Wachstumsmarken, Marken je Kreaturtyp), Lebensentzug beim Tod eigener
Kreaturen, Ziehen nach eigenem Tod im Endsegment, Infusion (Removal mit Lebensverlust, -4/-4 beim Betreten, Marken,
Schluesselwoerter, Opfern im Endsegment, Rueckholen nach Lebensgewinn, oberste vier Karten) und Stream of Life.
Kartentexte aus Secrets of Strixhaven (SOS)."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]
BEAR = W["Test Bear"]
NOTE = " (While it's prepared, you may cast a copy of its spell. Doing so unprepares it.)"
PEST_TEXT = "create a 1/1 black and green Pest creature token with \"Whenever this token attacks, you gain 1 life.\""


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="B"):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)


RAW = {
    "moseo": raw("Moseo, Vein's New Dean", f"Legendary Creature {DASH} Bird Skeleton Warlock", "{2}{B}", 3,
                 "Flying\nWhen Moseo enters, " + PEST_TEXT + "\nInfusion — At the beginning of your end step, if you "
                 "gained life this turn, return up to one target creature card with mana value X or less from your "
                 "graveyard to the battlefield, where X is the amount of life you gained this turn.", "2", "1",
                 ["Infusion", "Flying"]),
    "scholar": raw("Essenceknit Scholar", f"Creature {DASH} Dryad Warlock", "{B}{B/G}{G}", 3,
                   "When this creature enters, " + PEST_TEXT + "\nAt the beginning of your end step, if a creature "
                   "died under your control this turn, draw a card.", "3", "1", colors="BG"),
    "sloth": raw("Pestbrood Sloth", f"Creature {DASH} Plant Sloth", "{3}{G}", 4,
                 "Reach\nWhen this creature dies, create two 1/1 black and green Pest creature tokens with \"Whenever "
                 "this token attacks, you gain 1 life.\"", "4", "4", ["Reach"], "G"),
    "pest_friend": raw("Pest Friend", "Sorcery", "{B/G}", 1, PEST_TEXT[0].upper() + PEST_TEXT[1:],
                       colors="BG"),
    "bogwater": raw("Bogwater Lumaret", f"Creature {DASH} Spirit Frog", "{B}{G}", 2,
                    "Whenever this creature or another creature you control enters, you gain 1 life.", "2", "2",
                    colors="BG"),
    "counsel": raw("Comforting Counsel", "Enchantment", "{1}{G}", 2,
                   "Whenever you gain life, put a growth counter on this enchantment.\nAs long as there are five or "
                   "more growth counters on this enchantment, creatures you control get +3/+3.", colors="G"),
    "blech": raw("Blech, Loafing Pest", f"Legendary Creature {DASH} Pest", "{1}{B}{G}", 3,
                 "Whenever you gain life, put a +1/+1 counter on each Pest, Bat, Insect, Snake, and Spider you "
                 "control.", "3", "4", colors="BG"),
    "arnyn": raw("Arnyn, Deathbloom Botanist", f"Legendary Creature {DASH} Vampire Druid", "{2}{B}", 3,
                 "Deathtouch\nWhenever a creature you control with power or toughness 1 or less dies, target "
                 "opponent loses 2 life and you gain 2 life.", "2", "2", ["Deathtouch"]),
    "cauldron": raw("Cauldron of Essence", "Artifact", "{1}{B}{G}", 3,
                    "Whenever a creature you control dies, each opponent loses 1 life and you gain 1 life.\n{1}{B}{G}, "
                    "{T}, Sacrifice a creature: Return target creature card from your graveyard to the battlefield. "
                    "Activate only as a sorcery.", colors="BG"),
    "fate": raw("Foolish Fate", "Instant", "{2}{B}", 3,
                "Destroy target creature.\nInfusion — If you gained life this turn, that creature's controller loses 3 "
                "life.", keywords=["Infusion"]),
    "apprentice": raw("Poisoner's Apprentice", f"Creature {DASH} Orc Warlock", "{2}{B}", 3,
                      "Infusion — When this creature enters, target creature an opponent controls gets -4/-4 until end "
                      "of turn if you gained life this turn.", "2", "2", ["Infusion"]),
    "educator": raw("Old-Growth Educator", f"Creature {DASH} Treefolk Druid", "{2}{B}{G}", 4,
                    "Reach, vigilance\nInfusion — When this creature enters, put two +1/+1 counters on it if you "
                    "gained life this turn.", "4", "4", ["Infusion", "Reach", "Vigilance"], "BG"),
    "efflorescence": raw("Efflorescence", "Instant", "{2}{G}", 3,
                         "Put two +1/+1 counters on target creature.\nInfusion — If you gained life this turn, that "
                         "creature also gains trample and indestructible until end of turn.", keywords=["Infusion"],
                         colors="G"),
    "feaster": raw("Tragedy Feaster", f"Creature {DASH} Demon", "{2}{B}{B}", 4,
                   "Trample\nWard—Discard a card.\nInfusion — At the beginning of your end step, sacrifice a permanent "
                   "unless you gained life this turn.", "7", "6", ["Infusion", "Trample", "Ward"]),
    "lumarets": raw("Follow the Lumarets", "Sorcery", "{1}{G}", 2,
                    "Infusion — Look at the top four cards of your library. You may reveal a creature or land card "
                    "from among them and put it into your hand. If you gained life this turn, you may instead reveal "
                    "two creature and/or land cards from among them and put them into your hand. Put the rest on the "
                    "bottom of your library in a random order.", keywords=["Infusion"], colors="G"),
    "stream": raw("Stream of Life", "Sorcery", "{X}{G}", 1, "Target player gains X life.", colors="G"),
}
RAW["healer"] = {"name": "Infirmary Healer // Stream of Life", "layout": "prepare", "type_line": f"Creature {DASH} Cat Cleric",
                 "mana_cost": "{1}{G}", "cmc": 2.0, "colors": ["G"], "keywords": ["Prepared"],
                 "card_faces": [raw("Infirmary Healer", f"Creature {DASH} Cat Cleric", "{1}{G}", 2,
                                    "This creature enters prepared." + NOTE, "2", "3", colors="G"), RAW["stream"]]}
C = {k: card_info(v)[0] for k, v in RAW.items()}

TITAN = card_info(raw("Titan", "Creature — Giant", "{4}{G}", 5, "", "5", "5", colors="G"))[0]
OGRE = card_info(raw("Ogre", "Creature — Ogre", "{2}{R}", 3, "", "3", "3", colors="R"))[0]
SPIDER = card_info(raw("Web Spider", "Creature — Spider", "{1}{G}", 2, "", "1", "3", colors="G"))[0]
MOUSE = card_info(raw("Mouse", "Creature — Mouse", "{W}", 1, "", "1", "1", colors="W"))[0]
THOUGHT = card_info(raw("Quick Thought", "Sorcery", "{U}", 1, "Draw a card.", colors="U"))[0]


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
    def test_pest_tokens(self):
        for key, field in (("moseo", "creates_tokens"), ("scholar", "creates_tokens"), ("pest_friend", "creates_tokens"),
                           ("sloth", "death_tokens")):
            tokens = getattr(C[key], field)
            self.assertEqual(len(tokens), 1, key)
            n, pest = tokens[0]
            self.assertEqual((n, pest.power, pest.toughness, pest.attack_life, pest.creature_types),
                             (2 if key == "sloth" else 1, 1, 1, (0, 1), ("pest",)), key)

    def test_bogwater(self):
        self.assertEqual((C["bogwater"].etb_life, C["bogwater"].ally_enter_life), (1, 1))

    def test_counsel(self):
        self.assertTrue(C["counsel"].growth_counter)
        self.assertEqual(C["counsel"].cond_static, ((("growth", 5, "Comforting Counsel"), "team", 3, 3, ()),))

    def test_blech(self):
        self.assertEqual(C["blech"].lifegain_counter_types, (1, ("pest", "bat", "insect", "snake", "spider")))

    def test_death_drains(self):
        self.assertEqual(C["arnyn"].death_drain, (2, 2, True))
        self.assertEqual(C["cauldron"].death_drain, (1, 1, False))

    def test_end_death_draw(self):
        self.assertEqual(C["scholar"].end_death_draw, 1)

    def test_infusion(self):
        self.assertEqual(C["fate"].infusion_loss, 3)
        self.assertTrue(C["fate"].removal)
        self.assertEqual(C["apprentice"].infusion_debuff, 4)
        self.assertEqual(C["educator"].infusion_counters, 2)
        self.assertEqual(C["efflorescence"].infusion_kw, ("trample", "indestructible"))
        self.assertTrue(C["feaster"].infusion_sacrifice)
        self.assertTrue(C["moseo"].infusion_reanimate)
        self.assertEqual((C["lumarets"].top_dig, C["lumarets"].dig_infusion), ((4, "creature_land", False), True))

    def test_stream_of_life(self):
        self.assertTrue(C["stream"].x_life)


class CoverageTests(unittest.TestCase):
    def test_cards_fully_modelled(self):
        for key in RAW:
            if key == "cauldron":  # Faehigkeit "Sacrifice a creature: Return ...": Paket D
                continue
            self.assertEqual(analyze_card(RAW[key]), [], key)

    def test_cauldron_death_line(self):
        lines = [line for _c, _m, line in analyze_card(RAW["cauldron"])]
        self.assertFalse([line for line in lines if line.startswith("Whenever a creature you control dies")])


class PestTests(unittest.TestCase):
    def test_pest_on_enter_gains_life_when_attacking(self):
        me, opp = pair()
        bt._resolve(me, opp, C["scholar"], 3, entry())
        pest = next(c for c in me.creatures if c.card.name == "Pest")
        self.assertEqual(pest.card.attack_life, (0, 1))
        for c in me.creatures:
            c.entered = 0
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertGreaterEqual(me.life, 21)

    def test_sloth_dies_into_two_pests(self):
        me, opp = pair()
        sloth = on_board(me, C["sloth"])
        sloth.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual(sum(1 for c in me.creatures if c.card.name == "Pest"), 2)


class LifeTests(unittest.TestCase):
    def test_bogwater_self_and_others(self):
        me, opp = pair()
        bt._resolve(me, opp, C["bogwater"], 3, entry())
        self.assertEqual(me.life, 21)
        bt._resolve(me, opp, BEAR, 3, entry())
        self.assertEqual(me.life, 22)

    def test_counsel_needs_five_life_gains(self):
        me, opp = pair()
        me.perms.append(C["counsel"])
        me.statics = None
        bear = on_board(me, BEAR)
        for k in range(4):
            bt.gain_life(me, 1)
        self.assertEqual(bear.power, 2)
        bt.gain_life(me, 1)
        self.assertEqual((bear.power, bear.toughness), (5, 5))

    def test_blech_counters_on_listed_types(self):
        me, opp = pair()
        on_board(me, C["blech"])
        spider = on_board(me, SPIDER)
        bear = on_board(me, BEAR)
        bt.gain_life(me, 2)
        self.assertEqual((spider.bonus, bear.bonus), (1, 0))
        self.assertEqual(me.creatures[0].bonus, 1)  # Blech ist selbst ein Pest

    def test_arnyn_small_creature_dies(self):
        me, opp = pair()
        on_board(me, C["arnyn"])
        mouse = on_board(me, MOUSE)
        mouse.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual((me.life, opp.life), (22, 18))

    def test_arnyn_ignores_big_creature(self):
        me, opp = pair()
        on_board(me, C["arnyn"])
        ogre = on_board(me, OGRE)
        ogre.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual((me.life, opp.life), (20, 20))

    def test_cauldron_any_creature(self):
        me, opp = pair()
        me.perms.append(C["cauldron"])
        ogre = on_board(me, OGRE)
        ogre.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual((me.life, opp.life), (21, 19))

    def test_scholar_draws_after_own_death(self):
        me, opp = pair()
        on_board(me, C["scholar"])
        bt.sos_end_own(me, opp, 3, entry())
        self.assertEqual(len(me.hand), 0)
        me.deaths = me.deaths_mark + 1
        bt.sos_end_own(me, opp, 3, entry())
        self.assertEqual(len(me.hand), 1)

    def test_stream_of_life_x(self):
        me, opp = pair()
        me.next_x = 3
        bt._resolve(me, opp, C["stream"], 3, entry())
        self.assertEqual((me.life, me.next_x), (23, 0))


class InfusionTests(unittest.TestCase):
    def test_foolish_fate_with_life_gained(self):
        me, opp = pair()
        me.gained = 1
        me.open, me.hand = [("B",)] * 3, [C["fate"]]
        titan = on_board(opp, TITAN)
        self.assertTrue(bt._use_removal(me, C["fate"], C["fate"].alts, True, 3, entry(), other=opp))
        bt.cast_removal(C["fate"], me, opp, entry(), 3, target=titan)
        self.assertEqual(opp.life, 17)
        self.assertNotIn(titan, opp.creatures)

    def test_foolish_fate_without_life_gained(self):
        me, opp = pair()
        me.open, me.hand = [("B",)] * 3, [C["fate"]]
        on_board(opp, TITAN)
        bt._use_removal(me, C["fate"], C["fate"].alts, True, 3, entry(), other=opp)
        self.assertEqual(opp.life, 20)

    def test_apprentice_kills_with_life_gained(self):
        me, opp = pair()
        ogre = on_board(opp, OGRE)
        me.gained = 2
        bt._resolve(me, opp, C["apprentice"], 3, entry())
        self.assertNotIn(ogre, opp.creatures)

    def test_apprentice_nothing_without_life(self):
        me, opp = pair()
        ogre = on_board(opp, OGRE)
        bt._resolve(me, opp, C["apprentice"], 3, entry())
        self.assertIn(ogre, opp.creatures)

    def test_educator_counters(self):
        me, opp = pair()
        me.gained = 1
        bt._resolve(me, opp, C["educator"], 3, entry())
        self.assertEqual(me.creatures[0].bonus, 2)

    def test_efflorescence_trick_grants_with_life(self):
        me, opp = pair()
        me.gained = 1
        me.open, me.hand = [("G",)] * 3, [C["efflorescence"]]
        bear = on_board(me, BEAR)
        titan = on_board(opp, TITAN)
        bt.combat_tricks(me, [(bear, [titan])], opp, entry(), 3, True)
        self.assertEqual(bear.bonus, 2)
        self.assertIn("indestructible", bear.extra)

    def test_feaster_sacrifices_without_life(self):
        me, opp = pair()
        on_board(me, C["feaster"])
        token = on_board(me, bt.INKLING)
        bt.sos_end_own(me, opp, 3, entry())
        bt.bury((me, opp), entry())
        self.assertNotIn(token, me.creatures)
        self.assertEqual(len(me.creatures), 1)

    def test_feaster_keeps_all_with_life(self):
        me, opp = pair()
        on_board(me, C["feaster"])
        on_board(me, bt.INKLING)
        me.gained = 1
        bt.sos_end_own(me, opp, 3, entry())
        bt.bury((me, opp), entry())
        self.assertEqual(len(me.creatures), 2)

    def test_moseo_returns_creature_up_to_life_gained(self):
        me, opp = pair()
        on_board(me, C["moseo"])
        me.graveyard.extend([TITAN, OGRE])
        me.gained = 3
        bt.sos_end_own(me, opp, 3, entry())
        self.assertTrue(any(c.card is OGRE for c in me.creatures))
        self.assertIn(TITAN, me.graveyard)

    def test_lumarets_one_or_two(self):
        me, opp = pair()
        me.library = [THOUGHT, BEAR, TITAN, PLAINS] + [THOUGHT] * 5
        bt._resolve(me, opp, C["lumarets"], 3, entry())
        self.assertEqual(len(me.hand), 1)
        me, opp = pair()
        me.library = [THOUGHT, BEAR, TITAN, PLAINS] + [THOUGHT] * 5
        me.gained = 1
        bt._resolve(me, opp, C["lumarets"], 3, entry())
        self.assertEqual(len(me.hand), 2)
        self.assertNotIn(THOUGHT, me.hand)


if __name__ == "__main__":
    unittest.main()
