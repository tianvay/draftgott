"""Paket leichte FRA-Mechaniken (Punkte 3-20 der Analyse): Mill, Threshold-Boni, Ziehen beim Sterben bzw. Betreten,
Loot beim Angriff, Team-First-Strike, Vigilance mit Jace, Token-Bonus, Landfall eines Landes, Stun beim Betreten,
Leben bei billigen Zaubern des Gegners und beim Abwerfen, Germinate Recruits (Main 2 bzw. Ende des gegnerischen Zugs ab
X = 2), Room of Refuge (ab 6 uebrigen Laendern, nichts Teureres auf der Hand), Solitary Cell (nur nutzlose legendaere
Karten abwerfen), Eye of Jace, Enroot. Theorist's Proxy opfert sich nie (bleibt Blocker)."""
import unittest
from unittest import mock

from components import battle as bt
from components import simulation as sim
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS, BEAR = W["Plains"], W["Test Bear"]


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="B", **extra):
    d = _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)
    d.update(extra)
    return card_info(d)[0]


def land(name, color, sub=None):
    return card_info(_card(name, f"Basic Land {DASH} {sub or name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


def prep(name, cost, cmc, text, spell_name, spell_cost, spell_text, power, toughness, colors="UB"):
    d = {"name": f"{name} // {spell_name}", "layout": "prepare", "type_line": f"Creature {DASH} Test // Sorcery",
         "mana_cost": "", "cmc": float(cmc), "colors": list(colors), "keywords": ["Prepared"],
         "card_faces": [{"name": name, "type_line": f"Creature {DASH} Test", "mana_cost": cost, "power": power,
                         "toughness": toughness, "oracle_text": text},
                        {"name": spell_name, "type_line": "Sorcery", "mana_cost": spell_cost, "oracle_text": spell_text}]}
    return card_info(d)[0]


SWAMP, ISLAND, FOREST, MOUNTAIN = land("Swamp", "B"), land("Island", "U"), land("Forest", "G"), land("Mountain", "R")
DARK = make("Dark Matter Manipulator", f"Creature {DASH} Human Warlock", "{B}", 1, "When this creature enters, mill "
            "three cards.\nThis creature gets +2/+0 for every seven cards in your graveyard.", "1", "1")
THEORIX = prep("Theorix Metamage", "{2}{U}", 3, "This creature enters prepared.\nThreshold — This creature gets +1/+0 "
               "and has flying as long as there are seven or more cards in your graveyard.", "Omit Variables", "{U}",
               "Mill three cards.", "2", "3")
SIMULACRUM = make("Simulacrum Shaper", f"Creature {DASH} Elf Druid", "{1}{G}{G}", 3, "When this creature dies, draw a "
                  "card.", "2", "2", colors="G")
KARN = make("Karn, Gilded Guardian", f"Legendary Artifact Creature {DASH} Golem", "{4}", 4, "Vigilance, trample\nWhen "
            "Karn enters, draw a card for each color among other artifacts you control.", "4", "4",
            ["Vigilance", "Trample"], colors="")
RED_ART = make("Red Relic", "Artifact", "{R}", 1, "", colors="R")
BLUE_ART = make("Blue Relic", "Artifact", "{U}", 1, "", colors="U")
GRAY_ART = make("Gray Relic", "Artifact", "{1}", 1, "", colors="")
SPHINX = make("Sphinx of False Conclusions", f"Creature {DASH} Sphinx Illusion", "{2}{U}{U}", 4, "Flash\nFlying\n"
              "Whenever this creature attacks, draw a card, then discard a card.\nWhen this creature dies, if it isn't a "
              "token, create a token that's a copy of it.", "4", "2", ["Flash", "Flying"], colors="U")
ACUMEN = make("Artifist Acumen", "Sorcery", "{R}", 1, "Creatures you control gain first strike until end of turn.\nDraw "
              "a card.", colors="R")
MEANDERER = make("Mind Meanderer", f"Creature {DASH} Bird Fish Illusion", "{3}{G}{U}{U}", 6, "Flying\nThis creature "
                 "has vigilance as long as you control a Jace planeswalker.", "4", "4", ["Flying"], colors="GU")
MEMORIAL = make("Gideon's Memorial", "Legendary Artifact", "{1}{W}", 2, "Creature tokens you control get +1/+0 and "
                "have vigilance.\n{T}: Add one mana of any color. Spend this mana only to cast a planeswalker spell.",
                colors="W")
CANOPY = card_info(_card("Roiling Canopy", "Land", text="This land enters tapped.\nWhenever a Forest you control enters, "
                         "if you control at least five other Forests, target creature you control gets +3/+3 until end "
                         "of turn.\n{T}: Add {G}.", produced=["G"]))[0]
HAPATRA = make("Hapatra, the Desert Frost", f"Legendary Creature {DASH} Human Wizard", "{3}{U}", 4, "When Hapatra "
               "enters, for each opponent, tap up to one target creature that player controls. Put a stun counter on "
               "each of those creatures.\n{2}{U}: Untap target creature.", "3", "3", colors="U")
SENTRY = make("Solarium Sentry", f"Creature {DASH} Cat Soldier", "{G}{W}", 2, "Whenever an opponent casts a spell with "
              "mana value 2 or less, you gain 2 life.", "3", "3", colors="GW")
TITANBONES = make("Titanbones, Towering Heart", f"Legendary Creature {DASH} Skeleton Druid", "{3}{G}", 4, "Reach\n"
                  "Whenever you gain life, put two +1/+1 counters on Titanbones.\nWhen you discard this card, you gain "
                  "3 life.", "4", "3", ["Reach"], colors="G")
EYE = make("Eye of Jace", "Artifact", "{1}", 1, "At the beginning of your upkeep, surveil 1. Then if there are seven or "
           "more cards in your graveyard, sacrifice this artifact, it deals 2 damage to each opponent, and you gain 2 "
           "life.", colors="")
CULTIVATOR = prep("Carnivorous Cultivator", "{1}{G}", 2, "Deathtouch\nThis creature enters prepared.\nWhenever this "
                  "creature deals combat damage to a player, return target land card from your graveyard to your hand.",
                  "Enroot", "{G}", "Search your library for a land card, put it into your graveyard, then shuffle.",
                  "1", "1", colors="G")
GERMINATE = make("Germinate Recruits", "Instant", "{2}{W}", 3, "Create X 2/2 colorless Wizard Soldier creature tokens "
                 "named Cadet, where X is the amount of life you gained this turn.", colors="W")
ROOM = card_info(_card("Room of Refuge", "Land", text="This land enters tapped. As it enters, choose a color.\n{T}: Add "
                       "one mana of the chosen color.\n{5}, {T}, Sacrifice this land: Put two +1/+1 counters on target "
                       "creature. Activate only as a sorcery.", produced=["W"]))[0]
CELL = make("Solitary Cell", "Artifact", "{R}{W}", 2, "When this artifact enters, exile target nonland permanent an "
            "opponent controls with mana value 3 or less until this artifact leaves the battlefield.\n{1}, {T}, Discard "
            "a legendary card: Draw a card.", colors="RW")
PROXY = make("Theorist's Proxy", f"Creature {DASH} Illusion", "{1}{U}", 2, "Flash\nWhen this creature enters, empower "
             "Jace 3.\n{U}, Sacrifice this creature: The next spell you cast this turn can't be countered.", "1", "3",
             ["Flash"], colors="U")
LIFELINKER = make("Lifelinker", CRE, "{1}{W}", 2, "Lifelink", "3", "3", ["Lifelink"], colors="W")
OGRE = make("Ogre", CRE, "{2}{B}", 3, "", "3", "3")
CHEAP = make("Cheap Trick", "Sorcery", "{1}", 1, "Draw a card.", colors="")
TOKEN = BEAR._replace(name="Cadet", is_token=True)
LEGEND = make("Legend Lord", f"Legendary Creature {DASH} Test", "{8}", 8, "", "8", "8")
JACE_WALKER = card_info(dict(_card("Test Jace Walker", f"Legendary Planeswalker {DASH} Jace", "{2}{U}", 3, "U",
                                   "+1: Create a 1/1 blue Illusion creature token."), loyalty="3"))[0]


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def pair():
    me, opp = player(), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


def on_board(p, card, entered=0):
    c = bt.Creature(card, entered)
    c.gy, c.ctl = p.graveyard, p
    p.creatures.append(c)
    return c


def goldfish(order, horizon=6, dmg_target=20):
    with mock.patch("components.mulligan.random.shuffle", lambda x: None):
        return sim.simulate(order, 1, False, 3, horizon, True, False, None, 11, dmg_target, 6, True, 3, 6, False,
                            False, 5, True)


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertEqual((DARK.mill_self, DARK.gy_step_power), (3, (7, 2)))
        self.assertEqual(THEORIX.prepared[1].mill_self, 3)
        self.assertEqual((THEORIX.threshold_power, THEORIX.threshold_kw), (1, ("flying",)))
        self.assertEqual(SIMULACRUM.death_draw, 1)
        self.assertTrue(KARN.etb_artifact_colors_draw)
        self.assertTrue(SPHINX.attack_loot)
        self.assertEqual(ACUMEN.team_grant, ("first strike",))
        self.assertTrue(MEANDERER.jace_vigilance)
        self.assertEqual((MEMORIAL.token_pump, MEMORIAL.token_kw), (1, ("vigilance",)))
        self.assertEqual(CANOPY.forest_pump, 3)
        self.assertTrue(HAPATRA.etb_stun_opp)
        self.assertEqual(SENTRY.opp_cheap_cast_life, (2, 2))
        self.assertEqual(TITANBONES.discard_life, 3)
        self.assertEqual((EYE.upkeep_surveil, EYE.eye_threshold), (1, (2, 2)))
        self.assertTrue(CULTIVATOR.prepared[1].land_to_graveyard)
        self.assertEqual(GERMINATE.life_tokens.name, "Cadet")
        self.assertEqual(ROOM.land_sac_counters[1], 2)
        self.assertTrue(CELL.legend_discard_draw)
        self.assertFalse(BEAR.mill_self or BEAR.attack_loot or BEAR.death_draw or BEAR.team_grant)


class MillAndThresholdTests(unittest.TestCase):
    def test_dark_matter_mills_and_grows(self):
        me, opp = pair()
        me.graveyard = [PLAINS] * 4
        bt._resolve(me, opp, DARK, 3, entry())
        dark = me.creatures[0]
        self.assertEqual((len(me.graveyard), dark.power), (7, 3))  # 7 Karten: +2/+0
        me.graveyard += [PLAINS] * 7
        self.assertEqual(dark.power, 5)

    def test_omit_variables_copy_mills(self):
        me, opp = pair()
        bt._resolve(me, opp, THEORIX.prepared[1], 3, entry())
        self.assertEqual(len(me.graveyard), 3)

    def test_theorix_threshold(self):
        me, _opp = pair()
        t = on_board(me, THEORIX)
        self.assertEqual((t.power, t.has("flying")), (2, False))
        me.graveyard = [PLAINS] * 7
        self.assertEqual((t.power, t.has("flying")), (3, True))

    def test_goldfish_mill(self):
        hand = [SWAMP, DARK, PLAINS, PLAINS, PLAINS, PLAINS, PLAINS]
        r = goldfish(hand + [PLAINS] * 20, 3)
        self.assertEqual(r["graveyard"]["size"][3], 3)


class DrawTests(unittest.TestCase):
    def test_simulacrum_draws_when_it_dies(self):
        me, _opp = pair()
        on_board(me, SIMULACRUM).dead = True
        bt.bury((me,), entry())
        self.assertEqual(len(me.library), 19)

    def test_karn_counts_colors_of_other_artifacts(self):
        me, opp = pair()
        me.perms = [RED_ART, BLUE_ART, GRAY_ART, RED_ART]
        bt._resolve(me, opp, KARN, 3, entry())
        self.assertEqual(len(me.library), 18)

    def test_sphinx_loots_on_attack(self):
        me, opp = pair()
        on_board(me, SPHINX)
        me.hand = [PLAINS]
        me.library = [OGRE] + [PLAINS] * 10
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((len(me.library), len(me.graveyard)), (10, 1))

    def test_goldfish_sphinx_loot_draws_first(self):
        hand = [ISLAND] * 4 + [SPHINX] + [PLAINS] * 2
        r = goldfish(hand + [PLAINS] * 20, 6)  # R5 und R6: ziehen, dann ein Land abwerfen
        self.assertEqual((r["lands_drawn"], r["graveyard"]["size"][5]), (11, 1))

    def test_goldfish_karn_and_sphinx(self):
        hand = [MOUNTAIN, ISLAND, PLAINS, PLAINS, RED_ART, BLUE_ART, KARN]
        r = goldfish(hand + [PLAINS] * 20, 5)
        self.assertEqual(r["lands_drawn"], 10)  # Runde 4: Karn zieht 2 Laender zusaetzlich (sonst 8)


class CombatTests(unittest.TestCase):
    def test_acumen_gives_first_strike(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        me.lands, me.hand = [MOUNTAIN], [ACUMEN]
        bt._resolve(me, opp, ACUMEN, 5, entry())
        self.assertTrue(bear.has("first strike"))
        bt.cleanup((me, opp))
        self.assertFalse(bear.has("first strike"))

    def test_meanderer_vigilance_with_jace(self):
        me, _opp = pair()
        m = on_board(me, MEANDERER)
        self.assertFalse(m.has("vigilance"))
        me.jace.loyalty = 1
        self.assertTrue(m.has("vigilance"))
        me.jace.loyalty = 0
        me.walkers.append(bt.Walker(JACE_WALKER, 0))
        self.assertTrue(m.has("vigilance"))

    def test_memorial_pumps_tokens(self):
        me, _opp = pair()
        me.perms = [MEMORIAL]
        token, bear = on_board(me, TOKEN), on_board(me, BEAR)
        self.assertEqual((token.power, token.has("vigilance"), bear.power, bear.has("vigilance")), (3, True, 2, False))

    def test_canopy_pumps_with_five_other_forests(self):
        me, opp = pair()
        me.lands = [CANOPY] + [FOREST] * 4
        bear = on_board(me, BEAR)
        bt.on_land(me, opp, FOREST, 5, entry())  # nur 4 andere Forests
        self.assertEqual(bear.power, 2)
        me.lands.append(FOREST)
        me.lands.append(FOREST)
        bt.on_land(me, opp, FOREST, 5, entry())  # jetzt 5 andere
        self.assertEqual((bear.power, bear.toughness), (5, 5))

    def test_hapatra_stuns_the_most_dangerous(self):
        me, opp = pair()
        small, big = on_board(opp, BEAR), on_board(opp, OGRE)
        bt._resolve(me, opp, HAPATRA, 3, entry())
        self.assertEqual((big.tapped, big.stun, small.tapped), (True, 1, False))

    def test_goldfish_canopy(self):
        hand = [CANOPY, FOREST, FOREST, FOREST, FOREST, FOREST, BEAR._replace(alts=((0, (("G", 1),)),))]
        r = goldfish(hand + [FOREST] * 20, 7)
        self.assertGreater(r["effects"]["pump"], 0)


class LifeTests(unittest.TestCase):
    def test_sentry_on_cheap_opponent_spells(self):
        me, opp = pair()
        on_board(me, SENTRY)
        bt._resolve(opp, me, CHEAP, 3, entry())
        bt._resolve(opp, me, OGRE, 3, entry())
        self.assertEqual(me.life, 22)

    def test_titanbones_life_on_discard(self):
        me, opp = pair()
        me.hand = [TITANBONES]
        bt.discard(me, 1, entry())
        self.assertEqual(me.life, 23)
        me.hand = [PLAINS] * 9 + [TITANBONES]
        me.library = [PLAINS] * 5
        bt.hand_limit(me, entry())
        self.assertEqual(me.life, 23)  # das Handlimit wirft Laender ab

    def test_titanbones_dying_is_no_discard(self):
        me, _opp = pair()
        on_board(me, TITANBONES).dead = True
        bt.bury((me,), entry())
        self.assertEqual(me.life, 20)


class GerminateTests(unittest.TestCase):
    def test_main2_after_lifelink(self):
        me, opp = pair()
        on_board(me, LIFELINKER)
        me.lands, me.hand = [PLAINS] * 3, [GERMINATE]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)  # 3 Leben durch Lifelink
        self.assertEqual(sorted(c.card.name for c in me.creatures), ["Cadet", "Cadet", "Cadet", "Lifelinker"])

    def test_not_below_two(self):
        me, opp = pair()
        me.lands, me.hand = [PLAINS] * 3, [GERMINATE]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertIn(GERMINATE, me.hand)

    def test_end_of_opponent_turn_needs_two(self):
        me, opp = pair()
        me.hand, me.open, me.gained = [GERMINATE], [PLAINS.land_colors] * 3, 1
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertIn(GERMINATE, me.hand)

    def test_end_of_opponent_turn(self):
        me, opp = pair()
        me.hand, me.open, me.gained = [GERMINATE], [PLAINS.land_colors] * 3, 2
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual([c.card.name for c in me.creatures], ["Cadet", "Cadet"])


class RoomTests(unittest.TestCase):
    def test_sacrifice_late(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        me.lands = [ROOM] + [PLAINS] * 6
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((bear.bonus, ROOM in me.lands, len(me.lands)), (2, False, 6))

    def test_not_with_too_few_lands_or_a_big_spell(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        me.lands = [ROOM] + [PLAINS] * 5
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(bear.bonus, 0)
        me.lands = [ROOM] + [PLAINS] * 6
        me.hand = [LEGEND]  # braucht 8 Laender
        bt.take_turn(me, opp, 7, 4, skip_draw=True)
        self.assertEqual(bear.bonus, 0)

    def test_goldfish_room(self):
        hand = [ROOM] + [PLAINS] * 5 + [BEAR]
        r = goldfish(hand + [PLAINS] * 20, 8)
        self.assertEqual(r["effects"]["counters"], 2)


class CellTests(unittest.TestCase):
    def test_discards_a_dead_legend(self):
        me, opp = pair()
        me.perms = [CELL]
        on_board(me, TITANBONES)
        me.hand, me.open = [TITANBONES, LEGEND, OGRE], [PLAINS.land_colors]
        me.lands = [PLAINS] * 3
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual((TITANBONES in me.graveyard, LEGEND in me.hand, len(me.library), me.life), (True, True, 19, 23))

    def test_discards_an_expensive_legend(self):
        me, opp = pair()
        me.perms = [CELL]
        me.hand, me.open, me.lands = [LEGEND], [PLAINS.land_colors], [PLAINS] * 4  # 8 > 4 + 2
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual((LEGEND in me.graveyard, len(me.library)), (True, 19))

    def test_keeps_a_castable_legend(self):
        me, opp = pair()
        me.perms = [CELL]
        me.hand, me.open, me.lands = [LEGEND], [PLAINS.land_colors], [PLAINS] * 6
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertIn(LEGEND, me.hand)


class EyeTests(unittest.TestCase):
    def test_upkeep_surveil_then_sacrifice(self):
        me, opp = pair()
        me.perms = [EYE]
        me.graveyard = [PLAINS] * 7
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((EYE in me.perms, EYE in me.graveyard, opp.life, me.life), (False, True, 18, 22))

    def test_surveil_only_below_seven(self):
        me, opp = pair()
        me.perms = [EYE]
        me.library = [OGRE] + [PLAINS] * 10
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((EYE in me.perms, opp.life), (True, 20))

    def test_goldfish_eye(self):
        hand = [PLAINS, EYE] + [PLAINS] * 5
        r = goldfish(hand + [PLAINS] * 20, 10)
        self.assertEqual(r["effects"]["face"], 2)


class EnrootTests(unittest.TestCase):
    def test_land_into_the_graveyard(self):
        me, opp = pair()
        me.library = [OGRE, FOREST, FOREST, PLAINS]
        bt._resolve(me, opp, CULTIVATOR.prepared[1], 3, entry())
        self.assertEqual((me.graveyard, len(me.library)), ([FOREST], 3))


class ProxyTests(unittest.TestCase):
    def test_never_sacrificed(self):
        me, opp = pair()
        on_board(me, PROXY)
        me.lands, me.hand = [ISLAND] * 6, [OGRE._replace(alts=((5, (("U", 1),)),), mv=6)]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertIn("Theorist's Proxy", [c.card.name for c in me.creatures])


if __name__ == "__main__":
    unittest.main()
