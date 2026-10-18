"""Kampfmodell Paket S: Removal mit Bedingungen (Essence Burn, Flourishing Grapple, Plan for All Outcomes, Solve for
Disappointment), Ausloeser bei Nichtkreatur-Zaubern, bei Lebensgewinn und beim Angriff, kleine statische Effekte und
Kostensenkung (auch im Goldfish)."""
import random
import unittest

from components import battle as bt
from components import simulation as sim
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS = W["Plains"]
B, R, G, U = ("B",), ("R",), ("G",), ("U",)


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="R"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


SWAMP, MOUNTAIN, FOREST, ISLAND = land("Swamp", "B"), land("Mountain", "R"), land("Forest", "G"), land("Island", "U")

BEAR = W["Test Bear"]
OGRE = make("Ogre", CRE, "{2}{R}", 3, "", "3", "3")
TITAN = make("Titan", CRE, "{4}{G}", 5, "", "5", "5", colors="G")
ELF = make("Green Elf", CRE, "{1}{G}", 2, "", "3", "3", colors="G")
BRUTE = make("Red Brute", CRE, "{1}{R}", 2, "", "3", "3")
DRAW = make("Night's Whisper", "Sorcery", "{1}{B}", 2, "Draw two cards.", colors="B")
SHOCKER = make("Arc Shocker", CRE, "{2}{R}", 3, "When this creature enters, it deals 3 damage to target creature.", "2",
               "2")
GHOUL = make("Blessed Ghoul", f"Creature {DASH} Zombie Cleric", "{W/B}", 1,
             "Lifelink\n{2}{W/B}: Return this card from your graveyard to your hand.", "1", "1", ["Lifelink"], "B")

ESSENCE = make("Essence Burn", "Instant", "{1}{R}", 2, "Essence Burn deals 5 damage to target black or green creature "
               "or planeswalker. If that permanent would die this turn, exile it instead.")
GRAPPLE = make("Flourishing Grapple", "Instant", "{G}", 1, "Target creature or planeswalker an opponent controls that's "
               "red or white loses all abilities until end of turn. Target creature you control deals damage equal to "
               "its power to that permanent.", colors="G")
PLAN = make("Plan for All Outcomes", "Enchantment", "{3}{U}", 4, "When this enchantment enters, the owner of up to one "
            "other target nonland permanent puts it on their choice of the top or bottom of their library.\nWhenever "
            "you cast your first noncreature spell each turn, empower Jace 1.", colors="U")
SOLVE = make("Solve for Disappointment", "Sorcery", "{1}{B}", 2, "Target opponent reveals their hand. You choose a "
             "nonland permanent card from it. That player discards that card.\nEmpower Jace 1.", colors="B")

EMBERLING = make("Chandra's Emberling", f"Creature {DASH} Gremlin Elemental", "{2}{R}", 3,
                 "Haste\nWhenever you cast a noncreature spell, put a +1/+1 counter on this creature.", "2", "2",
                 ["Haste"])
WINTER = make("Winter, Team Player", f"Legendary Creature {DASH} Human Warrior", "{4}{R}", 5,
              "Convoke\nWhenever you cast a noncreature spell, creatures you control get +1/+0 until end of turn.",
              "4", "4", ["Convoke"])
SAHEELI = make("Saheeli, Jewel of Avishkar", f"Legendary Creature {DASH} Human Artificer", "{2}{U}{R}", 4,
               "Thopters you control have haste.\nWhenever you cast a noncreature spell, create a 1/1 colorless "
               "Thopter artifact creature token with flying.", "3", "3")

HORTI = make("Unflinching Hortimancer", f"Creature {DASH} Human Cleric", "{1}{W}", 2, "Ward {1}\nWhenever you gain "
             "life, put a +1/+1 counter on this creature.", "2", "2", ["Ward"], "W")
BLOOM = make("Bloombrute", f"Creature {DASH} Plant Elemental", "{2}{G}{W}", 4, "Whenever you gain life, draw a card. "
             "This ability triggers only once each turn.\n{4}{G}{W}: Target creature gains trample and lifelink until "
             "end of turn.", "4", "4", colors="G")
MENTOR = make("Way of the Mentor", f"Legendary Enchantment", "{2}{W}", 3, "When Way of the Mentor enters, empower Jace "
              "5.\nWhenever you gain life, put a loyalty counter on each planeswalker you control.", colors="W")

SOUL = make("Screeching Soulbreaker", f"Creature {DASH} Siren Bard", "{2}{B}", 3, "Flying\nWhenever this creature "
            "attacks, it deals 1 damage to each opponent and you gain 1 life.", "2", "1", ["Flying"], "B")
SENTRY = make("Afterthought Sentry", f"Artifact Creature {DASH} Gargoyle", "{2}", 2, "{2}: This creature gains "
              "flying until end of turn.\nWhenever this creature attacks, exile up to one target card from a "
              "graveyard.", "2", "2", colors="")

CARVER = make("Skilled Battlecarver", f"Creature {DASH} Human Warrior", "{1}{R}", 2, "During your turn, this "
              "creature has first strike.\n{1}{R}: This creature gets +1/+0 until end of turn.", "2", "2")
VOID = make("Void Extrapolator", f"Creature {DASH} Aetherborn Warlock", "{1}{B}", 2, "Threshold — This creature "
            "gets +1/+1 as long as there are seven or more cards in your graveyard.", "2", "1", colors="B")
VANGUARD = make("Vigorbloom Vanguard", f"Creature {DASH} Troll Druid", "{1}{G/W}", 2, "Each creature you control "
                "with a +1/+1 counter on it has vigilance.", "2", "2", colors="G")
GRAFT = make("Graft Surgeon", f"Creature {DASH} Human Cleric", "{2}{W}", 3, "This creature enters with a +1/+1 "
             "counter on it.\nWhen this creature dies, put its counters on up to one target creature you control.",
             "2", "2", colors="W")
RURIC = make("Ruric Thar, Biomagus", f"Legendary Creature {DASH} Ogre Crab Wizard", "{4}{U}{U}", 6,
             "Flying\nProwess, prowess (Whenever you cast a noncreature spell, this creature gets +1/+1 until end of "
             "turn twice.)\nWhenever Ruric Thar becomes the target of a spell or ability an opponent controls, draw a "
             "card.", "4", "4", ["Flying", "Prowess"], "U")

WRATH = make("Wrath of the Bloodmane", "Instant", "{2}{R}", 3, "This spell costs {1} less to cast if you control a "
             "legendary creature.\nWrath of the Bloodmane deals 4 damage to target creature or planeswalker.")
TRAXOS = make("Traxos, Academy Guardian", f"Legendary Artifact Creature {DASH} Dragon Construct", "{3}{U}", 4,
              "This spell costs {2} less to cast if you've cast a noncreature spell this turn.\nFlying, vigilance\n"
              "Prowess", "2", "2", ["Flying", "Vigilance", "Prowess"], "U")
OPT = make("Blue Study", "Sorcery", "{1}{U}", 2, "Draw a card.", colors="U")
UNSTOP = make("Ghalta the Unstoppable", f"Legendary Creature {DASH} Elder Dinosaur", "{8}{G}", 9,
              "This spell costs {X} less to cast, where X is the greatest power among creatures you control.\n"
              "Trample\nOther creatures you control have trample.", "10", "10", ["Trample"], "G")
IMMOV = make("Ghalta the Immovable", f"Legendary Creature {DASH} Elder Dinosaur", "{8}{W}", 9,
             "This spell costs {X} less to cast, where X is the greatest toughness among creatures you control.\n"
             "Creatures you control can attack as though they didn't have defender.\nEach creature you control with "
             "toughness greater than its power assigns combat damage equal to its toughness rather than its power.",
             "4", "12", colors="W")
WALL = make("Wall", CRE, "{1}{W}", 2, "Defender", "1", "6", ["Defender"], "W")
GEIST = make("Geist of Saint Thalia", f"Legendary Creature {DASH} Spirit Cleric", "{1}{U}", 2,
             "Flying\nNoncreature spells you cast cost {1} less to cast.", "1", "2", ["Flying"], "U")
WORDSMITH = card_info({
    "name": "Whiplash Wordsmith // Vicious Verse", "layout": "prepare", "mana_cost": "{3}{B/R} // {B/R}", "cmc": 4.0,
    "type_line": f"Creature {DASH} Vampire Sorcerer // Sorcery", "colors": ["B", "R"], "keywords": [],
    "card_faces": [
        {"name": "Whiplash Wordsmith", "mana_cost": "{3}{B/R}", "type_line": f"Creature {DASH} Vampire Sorcerer",
         "oracle_text": "This creature enters prepared. (While it's prepared, you may cast a copy of its spell. Doing "
                        "so unprepares it.)\nAs long as an opponent was dealt noncombat damage this turn, this "
                        "creature has flying and haste.", "power": "3", "toughness": "3"},
        {"name": "Vicious Verse", "mana_cost": "{B/R}", "type_line": "Sorcery",
         "oracle_text": "Vicious Verse deals 1 damage to target opponent."}]})[0]


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def pair(library=None):
    me, opp = player(library=library), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


def on_board(p, card, entered=0):
    c = bt.Creature(card, entered)
    c.gy, c.ctl = p.graveyard, p
    p.creatures.append(c)
    return c


class ParseTests(unittest.TestCase):
    def test_removal(self):
        self.assertEqual(ESSENCE.removal[:3], ("damage", 5, (("color", "B", "G"),)))
        self.assertTrue(ESSENCE.removal_exile)
        self.assertEqual(GRAPPLE.removal[:4], ("damage", -2, (("color", "R", "W"),), False))
        self.assertEqual((PLAN.removal[0], PLAN.removal[4]), ("tuck", "etb"))
        self.assertEqual(SOLVE.hand_pick, "permanent")
        self.assertGreater(SHOCKER.removal_points, 0)
        self.assertEqual(OGRE.removal_points, 0)

    def test_triggers(self):
        self.assertEqual((EMBERLING.cast_counter, WINTER.cast_team_pump, SAHEELI.type_haste), (1, 1, "thopter"))
        self.assertEqual(HORTI.lifegain_counter, (1, "self"))
        self.assertEqual((BLOOM.lifegain_draw, MENTOR.lifegain_loyalty), (1, 1))
        self.assertEqual(SOUL.attack_drain, (1, 1))
        self.assertTrue(SENTRY.attack_exile_gy)

    def test_statics(self):
        self.assertEqual(CARVER.own_turn_kw, ("first strike",))
        self.assertEqual(VOID.threshold_bonus, 1)
        self.assertEqual(WORDSMITH.noncombat_kw, ("flying", "haste"))
        self.assertTrue(VANGUARD.counter_vigilance)
        self.assertEqual((GRAFT.enters_counters, GRAFT.death_counters_move), (1, True))
        self.assertEqual((RURIC.prowess, RURIC.targeted_draw), (2, 1))
        self.assertTrue(TRAXOS.prowess)

    def test_costs(self):
        self.assertEqual(WRATH.self_discount, ("legendary", 1))
        self.assertEqual(TRAXOS.self_discount, ("noncreature", 2))
        self.assertEqual(UNSTOP.self_discount, ("power",))
        self.assertEqual(IMMOV.self_discount, ("toughness",))
        self.assertEqual(UNSTOP.team_kw, ("trample",))
        self.assertTrue(IMMOV.defender_attack)
        self.assertEqual((UNSTOP.mv, WRATH.mv), (9, 3))  # Kostensenkung aendert den Manawert nicht


class RemovalTests(unittest.TestCase):
    def test_essence_burn_only_black_or_green_and_exiles(self):
        me, opp = pair()
        on_board(opp, BRUTE)
        self.assertFalse(bt.has_target(ESSENCE, me, opp))
        on_board(opp, TITAN)
        bt.cast_removal(ESSENCE, me, opp, entry(), 3)
        self.assertEqual([c.card.name for c in opp.creatures], ["Red Brute"])
        self.assertEqual(opp.graveyard, [])  # exiliert statt Friedhof

    def test_grapple_bites_red_creature(self):
        me, opp = pair()
        on_board(opp, ELF)
        self.assertFalse(bt.has_target(GRAPPLE, me, opp))  # keine eigene Kreatur
        mine = on_board(me, OGRE)
        self.assertFalse(bt.has_target(GRAPPLE, me, opp))  # gruen: kein Ziel
        on_board(opp, BRUTE)
        bt.cast_removal(GRAPPLE, me, opp, entry(), 3)
        self.assertEqual([c.card.name for c in opp.creatures], ["Green Elf"])
        self.assertEqual(mine.damage, 0)  # kein Rueckschlag

    def test_plan_puts_castable_card_on_top(self):
        me, opp = pair()
        opp.lands = [PLAINS] * 2
        on_board(opp, OGRE)
        bt._resolve(me, opp, PLAN, 3, entry())
        self.assertEqual((opp.creatures, opp.library[0]), ([], OGRE))

    def test_plan_puts_expensive_card_at_the_bottom(self):
        me, opp = pair()
        on_board(opp, TITAN)
        bt._resolve(me, opp, PLAN, 3, entry())
        self.assertEqual((opp.creatures, opp.library[-1], opp.library[0]), ([], TITAN, PLAINS))

    def test_plan_removes_token(self):
        me, opp = pair()
        token = BEAR._replace(is_token=True, name="Cadet")
        on_board(opp, token)
        n = len(opp.library)
        bt._resolve(me, opp, PLAN, 3, entry())
        self.assertEqual((opp.creatures, len(opp.library)), ([], n))

    def test_solve_picks_castable_permanent(self):
        me, opp = pair()
        opp.lands = [PLAINS] * 2
        opp.hand = [TITAN, OGRE, BEAR, DRAW, PLAINS]
        bt._resolve(me, opp, SOLVE, 3, entry())
        self.assertNotIn(OGRE, opp.hand)
        self.assertIn(OGRE, opp.graveyard)

    def test_solve_tie_prefers_removal(self):
        me, opp = pair()
        opp.lands = [PLAINS] * 2
        opp.hand = [OGRE, SHOCKER]
        bt._resolve(me, opp, SOLVE, 3, entry())
        self.assertEqual(opp.hand, [OGRE])

    def test_solve_falls_back_to_highest_mana_value(self):
        me, opp = pair()
        opp.hand = [OGRE, TITAN, DRAW]  # ohne Laender: nichts naechste Runde spielbar
        bt._resolve(me, opp, SOLVE, 3, entry())
        self.assertEqual(opp.hand, [OGRE, DRAW])

    def test_solve_without_permanent(self):
        me, opp = pair()
        opp.hand = [DRAW, PLAINS]
        bt._resolve(me, opp, SOLVE, 3, entry())
        self.assertEqual(opp.hand, [DRAW, PLAINS])
        self.assertEqual(me.jace.loyalty, 1)


class CastTriggerTests(unittest.TestCase):
    def test_emberling_counter(self):
        me, opp = pair()
        c = on_board(me, EMBERLING)
        bt._resolve(me, opp, DRAW, 3, entry())
        bt._resolve(me, opp, BEAR, 3, entry())
        bt.cleanup((me,))
        self.assertEqual((c.power, c.toughness), (3, 3))

    def test_winter_team_pump(self):
        me, opp = pair()
        w, bear = on_board(me, WINTER), on_board(me, BEAR)
        bt._resolve(me, opp, DRAW, 3, entry())
        self.assertEqual((w.power, bear.power, bear.toughness), (5, 3, 2))
        bt.cleanup((me,))
        self.assertEqual(bear.power, 2)

    def test_saheeli_thopters_have_haste(self):
        me, opp = pair()
        on_board(me, SAHEELI)
        bt._resolve(me, opp, DRAW, 3, entry())
        token = me.creatures[-1]
        self.assertEqual(token.card.name, "Thopter")
        self.assertTrue(bt.can_attack(token, 3))
        me.creatures = [token]
        self.assertFalse(bt.can_attack(token, 3))


class LifeTriggerTests(unittest.TestCase):
    def test_hortimancer_counter_per_gain(self):
        me, _opp = pair()
        h = on_board(me, HORTI)
        bt.gain_life(me, 2, events=2)
        self.assertEqual(h.power, 4)

    def test_bloombrute_once_per_turn(self):
        me, _opp = pair()
        on_board(me, BLOOM)
        me.now = 5
        bt.gain_life(me, 1)
        bt.gain_life(me, 1)
        self.assertEqual(len(me.hand), 1)
        me.now = 6
        bt.gain_life(me, 1)
        self.assertEqual(len(me.hand), 2)

    def test_mentor_adds_loyalty_only_to_existing_jace(self):
        me, _opp = pair()
        me.perms = [MENTOR]
        bt.gain_life(me, 1)
        self.assertEqual(me.jace.loyalty, 0)
        me.jace.loyalty = 2
        bt.gain_life(me, 2, events=2)
        self.assertEqual(me.jace.loyalty, 4)


class AttackTriggerTests(unittest.TestCase):
    def test_soulbreaker_drains(self):
        me, opp = pair()
        on_board(me, SOUL)
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((opp.life, me.life, me.dealt_direct, e["damage"]), (17, 21, 1, 2))

    def test_sentry_exiles_self_returning_card(self):
        me, opp = pair()
        on_board(me, SENTRY)
        opp.graveyard[:] = [TITAN, GHOUL]
        me.graveyard[:] = [GHOUL]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((opp.graveyard, me.graveyard), ([TITAN], [GHOUL]))

    def test_sentry_exiles_biggest_creature(self):
        me, opp = pair()
        on_board(me, SENTRY)
        opp.graveyard[:] = [BEAR, TITAN, DRAW]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(opp.graveyard, [BEAR, DRAW])

    def test_sentry_leaves_spells(self):
        me, opp = pair()
        on_board(me, SENTRY)
        opp.graveyard[:] = [DRAW]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(opp.graveyard, [DRAW])


class StaticTests(unittest.TestCase):
    def test_battlecarver_first_strike_on_own_turn(self):
        me, _opp = pair()
        c = on_board(me, CARVER)
        me.turn_start = me.now = 5
        self.assertTrue(c.has("first strike"))
        me.now = 6
        self.assertFalse(c.has("first strike"))

    def test_void_threshold(self):
        me, _opp = pair()
        c = on_board(me, VOID)
        me.graveyard[:] = [PLAINS] * 6
        self.assertEqual((c.power, c.toughness), (2, 1))
        me.graveyard.append(PLAINS)
        self.assertEqual((c.power, c.toughness), (3, 2))

    def test_wordsmith_after_noncombat_damage(self):
        me, opp = pair()
        c = on_board(me, WORDSMITH, entered=5)
        me.direct_mark = me.dealt_direct = 0
        self.assertFalse(c.has("flying") or bt.can_attack(c, 5))
        bt.deal_noncombat(me, opp, 1, entry())
        self.assertTrue(c.has("flying") and bt.can_attack(c, 5))

    def test_wordsmith_cast_in_main_one_with_its_verse(self):
        me, opp = pair()
        me.lands, me.hand = [SWAMP] * 5, [WORDSMITH]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["main1"], [WORDSMITH.name, "Vicious Verse"])
        self.assertEqual((opp.life, e["damage"]), (16, 3))

    def test_vanguard_vigilance_with_counter(self):
        me, _opp = pair()
        on_board(me, VANGUARD)
        bear = on_board(me, BEAR)
        self.assertFalse(bear.has("vigilance"))
        bear.bonus = 1
        self.assertTrue(bear.has("vigilance"))

    def test_graft_surgeon(self):
        me, opp = pair()
        bt._resolve(me, opp, GRAFT, 3, entry())
        surgeon = me.creatures[0]
        self.assertEqual(surgeon.power, 3)
        bear = on_board(me, BEAR)
        surgeon.bonus += 1
        surgeon.dead = True
        bt.bury((me,), entry())
        self.assertEqual(bear.power, 4)

    def test_ruric_double_prowess_and_draw_when_targeted(self):
        me, opp = pair()
        c = on_board(me, RURIC)
        bt._resolve(me, opp, DRAW, 3, entry())
        self.assertEqual((c.power, c.toughness), (6, 6))
        hand = len(me.hand)
        bt.cast_removal(ESSENCE._replace(removal=("destroy", 0, (), False, "spell", False)), opp, me, entry(), 3)
        self.assertEqual(len(me.hand), hand + 1)


class CostTests(unittest.TestCase):
    def test_wrath_cheaper_with_legend(self):
        me, _opp = pair()
        me.hand, me.open = [WRATH], [R] * 2
        self.assertFalse(bt.affordable(me, WRATH))
        on_board(me, WINTER)
        self.assertTrue(bt.affordable(me, WRATH))

    def test_ghalta_unstoppable_by_power(self):
        me, _opp = pair()
        me.hand, me.open = [UNSTOP], [G] * 4
        self.assertFalse(bt.affordable(me, UNSTOP))
        on_board(me, TITAN)
        self.assertTrue(bt.affordable(me, UNSTOP))

    def test_ghalta_immovable_by_toughness(self):
        me, _opp = pair()
        me.hand, me.open = [IMMOV], [("W",)] * 3
        on_board(me, WALL)
        self.assertTrue(bt.affordable(me, IMMOV))

    def test_traxos_after_noncreature_spell_in_the_same_turn(self):
        me, opp = pair()
        me.lands, me.hand = [ISLAND] * 4, [OPT, TRAXOS]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["main1"], e["main2"]), (["Blue Study"], ["Traxos, Academy Guardian"]))

    def test_ghalta_team_trample_and_defender_attack(self):
        me, _opp = pair()
        bear, wall = on_board(me, BEAR), on_board(me, WALL)
        self.assertFalse(bear.has("trample") or bt.can_attack(wall, 5))
        on_board(me, UNSTOP)
        on_board(me, IMMOV)
        self.assertTrue(bear.has("trample") and bt.can_attack(wall, 5))


class GoldfishCostTests(unittest.TestCase):
    def test_reduction(self):
        self.assertEqual(sim.cost_reduction(UNSTOP, powers=[5, 2], toughs=[5, 2]), 5)
        self.assertEqual(sim.cost_reduction(IMMOV, powers=[1], toughs=[6]), 6)
        self.assertEqual(sim.cost_reduction(WRATH, legendary=True), 1)
        self.assertEqual(sim.cost_reduction(WRATH), 0)
        self.assertEqual(sim.cost_reduction(TRAXOS, noncreature=True), 2)
        self.assertEqual(sim.cost_reduction(DRAW, spell_discount=1), 1)
        self.assertEqual(sim.cost_reduction(BEAR, spell_discount=1), 0)  # nur Nichtkreatur-Zauber

    def test_reduced_card_keeps_mana_value(self):
        cheap = sim.reduced(UNSTOP, 5)
        self.assertEqual((cheap.alts, cheap.mv), (((3, (("G", 1),)),), 9))
        self.assertIs(sim.reduced(UNSTOP, 0), UNSTOP)

    def test_traxos_cast_after_noncreature_spell(self):
        key = sim.land_key([U] * 4)
        _score, chosen = sim.best_cast_reduced([OPT, TRAXOS], key, False, True)
        self.assertEqual(sorted(c.name for c in chosen), ["Blue Study", "Traxos, Academy Guardian"])

    def test_goldfish_casts_ghalta_early(self):
        plain = make("Plain Ghalta", f"Creature {DASH} Elder Dinosaur", "{8}{G}", 9, "Trample", "10", "10",
                     ["Trample"], "G")

        def lethal_turns(big):
            deck = [FOREST] * 17 + [TITAN] * 12 + [big] * 11
            random.seed(5)
            r = sim.simulate(deck, 60, False, 3, 9, True, False, None, 11, 20, 6, True, 3, 6, False, False, 5,
                             False)
            return sum(r["dmg"]) / max(1, len(r["dmg"])), len(r["dmg"])

        with_discount, without = lethal_turns(UNSTOP), lethal_turns(plain)
        self.assertLess(with_discount[0], without[0])

    def test_goldfish_geist_discount(self):
        hand, board = [DRAW, BEAR], [(GEIST, 1)]
        new, orig = sim.discounted_hand(hand, board, [0])
        self.assertEqual(new[0].alts, ((0, (("B", 1),)),))
        self.assertIs(new[1], BEAR)
        self.assertEqual(orig[new[0]], DRAW)


if __name__ == "__main__":
    unittest.main()
