"""Paket A (Analyse des ganzen Sets): Parserfehler Archive Arbiter, Heartwood-Token (111.10x), statische Team-Effekte,
Scry/Surveil- und Betreten-Ausloeser, Abwerfen-Varianten, Kleinkram (Mowu, Threshold-Zauber, Lebensverlust, +1/-1)."""
import random
import unittest
from unittest import mock

from components import battle as bt
from components import simulation as sim
from components.cards import card_info
from components.removal import removal_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS = W["Plains"]


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="R"):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)


def make(*a, **k):
    return card_info(raw(*a, **k))[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


MOUNTAIN, ISLAND = land("Mountain", "R"), land("Island", "U")
BEAR = W["Test Bear"]
OGRE = make("Ogre", CRE, "{2}{R}", 3, "", "3", "3")
WALL = make("Wall", CRE, "{2}{W}", 3, "", "3", "3", colors="W")
TINY = make("Tiny", CRE, "{R}", 1, "", "1", "3")
DRAW = make("Study", "Sorcery", "{1}{U}", 2, "Draw a card.", colors="U")
PEEK = make("Peek", "Sorcery", "{U}", 1, "Surveil 1.", colors="U")

ARBITER_RAW = raw("Archive Arbiter", f"Artifact Creature {DASH} Sphinx", "{6}", 6, "Flying\nWhen this creature enters, "
                  "choose one —\n• Destroy target noncreature, nonland permanent.\n• You gain 4 life.", "4", "4",
                  ["Flying"], "")
ARBITER = card_info(ARBITER_RAW)[0]
TETHER = make("Soul Tether", "Sorcery", "{2}{R/G}", 3, "Create a Heartwood token.")
AERID = make("Aerid Konstrari", f"Legendary Creature {DASH} Elder Sphinx", "{1}{R}{G}{G}", 4, "Flying\nWhen Aerid "
             "Konstrari enters or dies, create a Heartwood token.\n{6}: Create a Heartwood token. Then Aerid Konstrari "
             "gets +X/+0 until end of turn, where X is the number of artifacts you control.", "3", "3", ["Flying"])
SAMUT = make("Samut, Hazoret's Champion", f"Legendary Creature {DASH} Human Warrior Cleric", "{1}{R}", 2,
             "Creatures you control have haste.", "2", "1")
TETSUKO = make("Tetsuko Umezawa, Fugitive", f"Legendary Creature {DASH} Human Rogue", "{1}{U}", 2,
               "Creatures you control with power or toughness 1 or less can't be blocked.", "1", "3", colors="U")
GALLIA = make("Gallia, the Merrymaker", f"Legendary Creature {DASH} Satyr", "{1}{R}", 2, "Haste\nEach other creature "
              "you control with a +1/+1 counter on it has haste.\n{1}{R}, {T}: Put a +1/+1 counter on target creature "
              "that entered this turn.", "2", "1", ["Haste"])
ANGUISH = make("Ajani's Anguish", "Enchantment", "{X}{R}", 1, "When this enchantment enters, it deals X damage to any "
               "target.\nCreatures you control have trample.")
BARBS = make("Master of Barbs", f"Creature {DASH} Lizard Bard", "{1}{R}", 2, "Menace\nWhenever one or more opponents "
             "are dealt noncombat damage, creatures you control get +1/+0 until end of turn.", "2", "2", ["Menace"])
DENZILORE = make("Denzilore Fatehold", f"Legendary Creature {DASH} Elder Sphinx", "{1}{W}{U}{U}", 4, "Flash\nFlying\n"
                 "Whenever you scry or surveil, put a +1/+1 counter on each creature you control.", "3", "3",
                 ["Flash", "Flying"], "U")
DIVINER = make("Diviner of Victory", f"Creature {DASH} Dwarf Wizard", "{U}", 1, "Whenever you scry or surveil, this "
               "creature gets +1/+1 until end of turn.", "1", "1", colors="U")
PROCTOR = make("Proctor of Potential", f"Creature {DASH} Human Cleric", "{W}{U}", 2, "Whenever this creature or "
               "another creature you control enters, surveil 1.\n{W}{U}: Return this card from your graveyard to the "
               "battlefield with a finality counter on it. Activate only if you've scried or surveilled this turn.",
               "2", "2", colors="U")
VITRIOL = make("Stinging Vitriol", "Sorcery", "{B}{R}", 2, "Stinging Vitriol deals 2 damage to target opponent. That "
               "player reveals their hand. You choose a nonland card from it. They discard that card.")
TINYBONES = make("Tinybones, Pocket Nuisance", f"Legendary Creature {DASH} Skeleton Rogue", "{2}{B}", 3,
                 "When Tinybones enters, each opponent discards a card.\nWhenever a player discards one or more cards, "
                 "Tinybones deals 1 damage to each opponent.", "1", "1", colors="B")
VOLUME = make("Murmuring Volume", f"Artifact {DASH} Book", "{3}", 3, "{T}: Add one mana of any color.\n{2}, {T}, "
              "Discard a card: Draw a card.", colors="")
DUELIST = make("Divining Duelist", f"Creature {DASH} Merfolk Wizard", "{2}{U}", 3, "Flash\nWhen this creature enters, "
               "choose one —\n• Tap target creature.\n• Untap target creature.\n• Draw a card, then discard a card.",
               "2", "2", ["Flash"], "U")
JIANG = make("Jiang Yanggu, Never Alone", f"Legendary Creature {DASH} Human Druid", "{3}{G}", 4, "When Jiang Yanggu "
             "enters, create Mowu, a legendary 3/3 green Dog creature token.\nAt the beginning of your end step, untap "
             "all tokens you control.", "3", "3", colors="G")
PROFT = make("Proft, Sinister Mastermind", f"Legendary Creature {DASH} Human Rogue", "{2}{B}", 3, "Threshold — You "
             "can't cast this spell unless there are seven or more cards in your graveyard.\nMenace\n{B}, Discard this "
             "card: Target creature gets -3/-1 until end of turn.", "4", "4", ["Menace"], "B")
MERCY = make("Vraska's Final Mercy", "Sorcery", "{B}{B}", 2, "Choose one —\n• You lose 2 life. Destroy target creature "
             "or planeswalker.\n• You lose 2 life. Empower Jace 6.", colors="B")
WITNESS = make("Undulating Witness", f"Creature {DASH} Serpent", "{4}{U}", 5, "Flying\n{2}: This creature gets +1/-1 "
               "until end of turn.\nBasic landcycling {2}", "3", "4", ["Flying"], "U")


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


class ArbiterTests(unittest.TestCase):
    def test_noncreature_permanent_is_no_creature_removal(self):
        self.assertEqual(ARBITER.choices[1][0].removal, ())
        self.assertIsNone(removal_info(ARBITER_RAW))

    def test_arbiter_does_not_kill_a_creature(self):
        me, opp = pair()
        bear = on_board(opp, BEAR)
        bt._resolve(me, opp, ARBITER, 3, entry())
        self.assertIn(bear, opp.creatures)


class HeartwoodTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual((TETHER.heartwood, AERID.heartwood, AERID.death_heartwood), (1, 1, 1))

    def test_spell_creates_an_artifact_mana_source(self):
        me, opp = pair()
        bt._resolve(me, opp, TETHER, 3, entry())
        self.assertEqual([c.name for c in me.perms], ["Heartwood"])
        self.assertTrue(me.perms[0].is_artifact and me.perms[0].is_token)
        pool, _units = bt._mana(me, 5)
        self.assertIn(("G", "R"), pool)

    def test_enter_and_die(self):
        me, opp = pair()
        bt._resolve(me, opp, AERID, 3, entry())
        me.creatures[0].dead = True
        bt.bury((me,), entry())
        self.assertEqual([c.name for c in me.perms], ["Heartwood", "Heartwood"])

    def test_goldfish_heartwood_gives_mana_next_turn(self):
        hand = [MOUNTAIN, MOUNTAIN, TETHER, OGRE, OGRE, OGRE, OGRE]
        order = hand + [OGRE] * 20

        def ramp(card):
            with mock.patch("components.mulligan.random.shuffle", lambda x: None):
                r = sim.simulate(hand[:2] + [card] + order[3:], 1, False, 3, 6, True, False, None, 11, 20, 6, True,
                                 3, 6, False, False, 5, True)
            return r["ramp"]

        self.assertTrue(ramp(TETHER)["on"])


class StaticTests(unittest.TestCase):
    def test_samut_haste_for_all(self):
        me, _opp = pair()
        samut = on_board(me, SAMUT, entered=5)
        ogre = on_board(me, OGRE, entered=5)
        self.assertTrue(bt.can_attack(ogre, 5) and bt.can_attack(samut, 5))

    def test_samut_in_the_goldfish(self):
        board = [(SAMUT, 3), (OGRE, 3)]
        self.assertTrue(sim._attacks((OGRE, 3), 3, board))
        self.assertFalse(sim._attacks((OGRE, 3), 3, [(OGRE, 3)]))

    def test_tetsuko_small_creatures_unblockable(self):
        me, opp = pair()
        on_board(me, TETSUKO)
        tiny, ogre = on_board(me, TINY), on_board(me, OGRE)
        wall = on_board(opp, WALL)
        self.assertEqual((bt.can_block(wall, tiny), bt.can_block(wall, ogre)), (False, True))

    def test_gallia_haste_with_counter(self):
        me, _opp = pair()
        on_board(me, GALLIA)
        ogre = on_board(me, OGRE, entered=5)
        self.assertFalse(bt.can_attack(ogre, 5))
        ogre.bonus = 1
        self.assertTrue(bt.can_attack(ogre, 5))

    def test_anguish_gives_trample_from_an_enchantment(self):
        me, _opp = pair()
        me.perms = [ANGUISH]
        self.assertTrue(on_board(me, OGRE).has("trample"))

    def test_master_of_barbs(self):
        me, opp = pair()
        barbs, ogre = on_board(me, BARBS), on_board(me, OGRE)
        bt.deal_noncombat(me, opp, 1, entry())
        self.assertEqual((barbs.power, ogre.power), (3, 4))
        bt.cleanup((me,))
        self.assertEqual(ogre.power, 3)


class SurveilEnterTests(unittest.TestCase):
    def test_denzilore_counter_on_each_creature_per_surveil(self):
        me, _opp = pair()
        den, bear = on_board(me, DENZILORE), on_board(me, BEAR)
        bt.surveil_cards(me, [1, 1], entry(), "Test")
        self.assertEqual((den.power, bear.power), (5, 4))

    def test_diviner_pump_per_surveil(self):
        me, _opp = pair()
        div = on_board(me, DIVINER)
        bt.surveil_cards(me, [1, 1], entry(), "Test")  # zwei Surveils auf einmal
        self.assertEqual((div.power, div.toughness), (3, 3))

    def test_proctor_surveils_when_creatures_enter(self):
        me, opp = pair()
        bt._resolve(me, opp, PROCTOR, 3, entry())
        self.assertTrue(me.surveilled)
        me.surveilled = False
        bt._resolve(me, opp, BEAR, 3, entry())
        self.assertTrue(me.surveilled)


class DiscardTests(unittest.TestCase):
    def test_vitriol_picks_a_card(self):
        me, opp = pair()
        opp.hand = [OGRE, PLAINS]
        bt._resolve(me, opp, VITRIOL, 3, entry())
        self.assertEqual((opp.life, opp.hand, opp.graveyard), (18, [PLAINS], [OGRE]))

    def test_tinybones_pings_on_each_discard(self):
        me, opp = pair()
        opp.hand = [OGRE, OGRE]
        bt._resolve(me, opp, TINYBONES, 3, entry())  # Gegner wirft ab: 1 Schaden
        self.assertEqual(opp.life, 19)
        me.hand = [PLAINS, PLAINS, PLAINS]
        bt.discard(me, 1, entry())  # auch eigenes Abwerfen
        self.assertEqual(opp.life, 18)

    def test_volume_rummages_with_a_surplus_land(self):
        me, opp = pair()
        me.perms, me.open = [VOLUME], [ISLAND.land_colors] * 2
        me.lands, me.hand = [ISLAND] * 3, [BEAR, PLAINS]
        bt.end_step_instants(me, opp, entry(), 2)
        self.assertEqual((PLAINS in me.graveyard, len(me.hand), me.open), (True, 2, []))

    def test_duelist_loot_mode(self):
        me, opp = pair()
        me.lands, me.hand = [ISLAND] * 3, [PLAINS]
        bt._resolve(me, opp, DUELIST, 3, entry())
        self.assertEqual((len(me.graveyard), len(me.library)), (1, 19))


class SmallTests(unittest.TestCase):
    def test_jiang_creates_legendary_mowu(self):
        me, opp = pair()
        bt._resolve(me, opp, JIANG, 3, entry())
        mowu = [c for c in me.creatures if c.card.name == "Mowu"]
        self.assertEqual((len(mowu), mowu[0].card.legendary, mowu[0].power), (1, True, 3))

    def test_jiang_untaps_tokens_at_end_of_turn(self):
        me, opp = pair()
        on_board(me, JIANG)
        token = on_board(me, BEAR._replace(name="Cadet", is_token=True))
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["damage"] > 0, token.tapped), (True, False))

    def test_proft_needs_threshold(self):
        me, opp = pair()
        me.lands, me.hand = [land("Swamp", "B")] * 3, [PROFT]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["main2"], [])
        me.graveyard[:] = [PLAINS] * 7
        e = bt.take_turn(me, opp, 7, 4, skip_draw=True)
        self.assertEqual(e["main2"], [PROFT.name])

    def test_proft_threshold_in_the_goldfish(self):
        self.assertFalse(sim.cast_allowed(PROFT, 6))
        self.assertTrue(sim.cast_allowed(PROFT, 7))
        self.assertTrue(sim.cast_allowed(OGRE, 0))

    def test_mercy_life_loss(self):
        me, opp = pair()
        on_board(opp, OGRE)
        bt._resolve(me, opp, MERCY, 3, entry())
        self.assertEqual((me.life, opp.creatures), (18, []))

    def test_witness_pump_lowers_toughness(self):
        self.assertEqual(WITNESS.abilities[0][4], (("pump", 1, -1, "self"),))


if __name__ == "__main__":
    unittest.main()
