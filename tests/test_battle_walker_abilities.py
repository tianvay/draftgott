"""L2a: Loyalty-Faehigkeiten, die Karten allen unseren Planeswalkern geben (Way of the ..., Sanctum Lurker, Kiora,
Avatar), und Ausloeser bei Aktivierung (Way of the Mind Sculptor, Way of the Paradox, Kiora). Eine Aktivierung pro Zug
(606.3), Minus-Kosten nur mit genug Loyalty (606.6), Tod bei 0 (704.5i) ausser mit Sanctum Lurker.
Wahl: Lethal > Removal > grosses Token > Ziehen > Cadet + Surveil > Plus-Faehigkeit > Surveil. Zeitpunkt: Ziehen zu
Beginn des Zugs (wie bisher), zeitkritisches in Main 1 (Lethal, Removal, Mana, Avatar, mit Kiora), sonst nach Main 2.
Ohne solche Karten bleibt alles wie bisher. Goldfish: dieselbe Wahl ohne Token (die kennt er nicht)."""
import unittest
from unittest import mock

from components import battle as bt
from components import simulation as sim
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS = W["Plains"]
ENCH = "Legendary Enchantment"


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="U"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


MOUNTAIN, SWAMP = land("Mountain", "R"), land("Swamp", "B")
BEAR = W["Test Bear"]
TOKEN = BEAR._replace(name="Cadet", is_token=True)
OGRE = make("Ogre", CRE, "{2}{R}", 3, "", "3", "3", colors="R")
TITAN = make("Titan", CRE, "{4}{G}", 5, "", "5", "5", colors="G")
WALL = make("Wall", CRE, "{2}{W}", 3, "", "3", "3", colors="W")

E = "When {n} enters, empower Jace 5."
HEALER = make("Way of the Healer", ENCH, "{3}{W}", 4, E.format(n="Way of the Healer") + "\nPlaneswalkers you control "
              "have \"[−2]: Create a 2/2 colorless Wizard Soldier creature token named Cadet. Surveil 1.\"")
WILD = make("Way of the Wildspeaker", ENCH, "{4}{G}", 5, E.format(n="Way of the Wildspeaker") + "\nPlaneswalkers you "
            "control have \"[−4]: Create a 4/4 green Beast creature token with trample.\"")
DEATH = make("Way of the Deathbringer", ENCH, "{2}{B}", 3, E.format(n="Way of the Deathbringer") + "\nPlaneswalkers "
             "you control have \"[−2]: You may sacrifice a creature. If you do, create a 4/4 green Beast creature "
             "token with trample.\"")
WARLORD = make("Way of the Warlord", ENCH, "{2}{R}", 3, E.format(n="Way of the Warlord") + "\nPlaneswalkers you "
               "control have \"[−4]: This planeswalker deals 2 damage to up to one target creature or planeswalker and "
               "2 damage to target player.\"")
PYRO = make("Way of the Pyromancer", ENCH, "{1}{R}", 2, "When Way of the Pyromancer enters, empower Jace 2.\n"
            "Planeswalkers you control have \"[+1]: Add {R}.\"")
CRYO = make("Way of the Cryomancer", ENCH, "{2}{U}", 3, E.format(n="Way of the Cryomancer") + "\nPlaneswalkers you "
            "control have \"[−3]: When you next cast an instant or sorcery spell this turn, copy that spell. You may "
            "choose new targets for the copy.\"")
SCULPTOR = make("Way of the Mind Sculptor", ENCH, "{4}{U}", 5, E.format(n="Way of the Mind Sculptor") + "\nWhenever "
                "you activate a loyalty ability, if you removed two or more loyalty counters to activate it, draw a "
                "card.")
PARADOX = make("Way of the Paradox", ENCH, "{2}{G}", 3, E.format(n="Way of the Paradox") + "\nWhenever you activate a "
               "loyalty ability, you gain 1 life. You may play an additional land this turn.")
LURKER = make("Sanctum Lurker", f"Creature {DASH} Horror", "{2}{B}", 3, "When this creature enters, empower Jace 1.\n"
              "Planeswalkers you control aren't put into their owners' graveyards for having 0 loyalty.\n"
              "Planeswalkers you control have \"[+2]: This planeswalker deals 1 damage to each opponent and you gain 1 "
              "life.\"", "3", "2", colors="B")
KIORA = make("Kiora of Salt and Sand", f"Legendary Creature {DASH} Merfolk Noble", "{1}{G}{U}", 3,
             "Whenever you attack, if you've activated a loyalty ability this turn, untap target attacking creature. "
             "It can't be blocked this turn.\nPlaneswalkers you control have \"[−8]: Create an 8/8 blue Leviathan "
             "creature token with hexproof.\"", "2", "4")
AVATAR = make("Avatar of Burgeoning Echoes", f"Creature {DASH} Avatar", "{G}{U}", 2, "Landfall — Whenever a land you "
              "control enters, empower Jace 2.\nPlaneswalkers you control have \"[−10]: Put a +1/+1 counter on target "
              "creature for each land you control.\"", "2", "3")
GIDEON = make("Gideon the Oathless", f"Legendary Creature {DASH} Human Mercenary", "{2}{B}", 3, "Whenever an opponent "
              "activates a loyalty ability, Gideon deals 1 damage to that player.", "3", "3", colors="B")


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def pair():
    me, opp = player(), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


def on_board(p, card, entered=0):
    c = bt.Creature(card, entered)
    c.gy, c.ctl = p.graveyard, p
    p.creatures.append(c)
    return c


def names(p):
    return sorted(c.card.name for c in p.creatures)


class ParseTests(unittest.TestCase):
    def test_grants(self):
        cost, atoms = HEALER.walker_grants[0]
        self.assertEqual((cost, [a[0] for a in atoms]), (-2, ["token", "surveil"]))
        self.assertEqual(atoms[0][2].name, "Cadet")
        cost, atoms = WILD.walker_grants[0]
        self.assertEqual((cost, atoms[0][0], atoms[0][2].power, atoms[0][2].kw), (-4, "token", 4, ("trample",)))
        self.assertEqual((DEATH.walker_grants[0][0], DEATH.walker_grants[0][1][0][0]), (-2, "sac_token"))
        self.assertEqual(WARLORD.walker_grants, ((-4, (("bolt", 2, 2),)),))
        self.assertEqual(PYRO.walker_grants, ((1, (("mana", ("R",)),)),))
        self.assertEqual(LURKER.walker_grants, ((2, (("face", 1), ("life", 1))),))
        self.assertEqual(KIORA.walker_grants[0][0], -8)
        self.assertEqual(AVATAR.walker_grants, ((-10, (("counter_lands",),)),))
        self.assertEqual(CRYO.walker_grants, ())  # eigener Schritt

    def test_triggers(self):
        self.assertTrue(LURKER.walker_no_death)
        self.assertTrue(SCULPTOR.loyalty_draw)
        self.assertTrue(PARADOX.loyalty_paradox)
        self.assertTrue(KIORA.kiora_attack)


class ChoiceTests(unittest.TestCase):
    def test_warlord_for_lethal(self):
        me, opp = pair()
        me.perms, me.jace.loyalty, opp.life = [WARLORD], 4, 2
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertLessEqual(opp.life, 0)

    def test_warlord_kills_the_most_dangerous_creature(self):
        me, opp = pair()
        bear = on_board(opp, BEAR)
        me.perms, me.jace.loyalty = [WARLORD], 4
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((bear in opp.creatures, opp.life, me.jace.loyalty), (False, 18, 0))

    def test_warlord_only_against_the_biggest_threat(self):
        me, opp = pair()
        on_board(opp, TITAN)
        bear = on_board(opp, BEAR)
        me.perms, me.jace.loyalty = [WARLORD], 4
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((bear in opp.creatures, opp.life, len(me.library)), (True, 20, 19))

    def test_warlord_kills_the_blocker_for_lethal(self):
        me, opp = pair()
        on_board(opp, TITAN).tapped = True
        on_board(opp, BEAR)
        on_board(me, OGRE)
        me.perms, me.jace.loyalty, opp.life = [WARLORD], 4, 5
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertLessEqual(opp.life, 0)

    def test_warlord_not_without_a_kill(self):
        me, opp = pair()
        on_board(opp, OGRE)
        me.perms, me.jace.loyalty = [WARLORD], 4
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((opp.life, me.jace.loyalty, len(me.library)), (20, 1, 19))  # gezogen

    def test_big_token_before_drawing(self):
        me, opp = pair()
        me.perms, me.jace.loyalty = [WILD], 4
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((names(me), len(me.library)), (["Beast"], 20))

    def test_leviathan_before_beast(self):
        me, opp = pair()
        on_board(me, KIORA, entered=5)
        me.perms, me.jace.loyalty = [WILD], 8
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertIn("Leviathan", names(me))

    def test_minus_needs_enough_loyalty(self):
        me, opp = pair()
        me.perms, me.jace.loyalty = [WILD], 3
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((names(me), len(me.library)), ([], 19))

    def test_deathbringer_sacrifices_a_small_creature(self):
        me, opp = pair()
        on_board(me, TOKEN, entered=5)
        me.perms, me.jace.loyalty = [DEATH], 2
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(names(me), ["Beast"])

    def test_deathbringer_keeps_a_big_creature(self):
        me, opp = pair()
        on_board(me, TITAN, entered=5)
        me.perms, me.jace.loyalty = [DEATH], 2
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(names(me), ["Titan"])

    def test_avatar_counters_with_four_lands(self):
        me, opp = pair()
        on_board(me, AVATAR, entered=5)
        bear = on_board(me, BEAR)
        me.jace.loyalty, me.lands = 10, [MOUNTAIN] * 5
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((bear.bonus, e["damage"]), (5, 7))

    def test_avatar_not_below_four_lands(self):
        me, opp = pair()
        on_board(me, AVATAR, entered=5)
        bear = on_board(me, BEAR)
        me.jace.loyalty, me.lands = 10, [MOUNTAIN] * 3
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((bear.bonus, len(me.library)), (0, 19))

    def test_draw_before_healer(self):
        me, opp = pair()
        me.perms, me.jace.loyalty = [HEALER], 3
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((names(me), len(me.library)), ([], 19))

    def test_healer_with_two_loyalty(self):
        me, opp = pair()
        me.perms, me.jace.loyalty = [HEALER], 2
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((names(me), me.jace.loyalty), (["Cadet"], 0))

    def test_lurker_plus_before_surveil(self):
        me, opp = pair()
        on_board(me, LURKER, entered=5)
        me.jace.loyalty = 1
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((me.jace.loyalty, opp.life, me.life), (3, 19, 21))

    def test_lurker_keeps_jace_at_zero(self):
        me, opp = pair()
        lurker = on_board(me, LURKER, entered=5)
        me.jace.loyalty = 3
        bt.take_turn(me, opp, 5, 3, skip_draw=True)  # zieht: 0, bleibt
        self.assertEqual((me.jace.loyalty, bt.jace_present(me)), (0, True))
        bt.take_turn(me, opp, 7, 4, skip_draw=True)  # +2
        self.assertEqual(me.jace.loyalty, 2)
        me.jace.loyalty = 0
        lurker.dead = True
        bt.bury((me,), {"events": [], "deaths": []})
        self.assertFalse(bt.jace_present(me))

    def test_pyromancer_only_when_the_mana_helps(self):
        me, opp = pair()
        me.perms, me.jace.loyalty, me.lands, me.hand = [PYRO], 1, [MOUNTAIN] * 2, [OGRE]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["main2"], me.jace.loyalty), (["Ogre"], 2))

    def test_pyromancer_without_use_surveils(self):
        me, opp = pair()
        me.perms, me.jace.loyalty = [PYRO], 1
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(me.jace.loyalty, 0)

    def test_mind_sculptor_draws(self):
        me, opp = pair()
        me.perms, me.jace.loyalty = [WILD, SCULPTOR], 4
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((names(me), len(me.library)), (["Beast"], 19))

    def test_paradox_extra_land_and_life(self):
        me, opp = pair()
        me.perms, me.jace.loyalty, me.hand = [PARADOX], 3, [MOUNTAIN, MOUNTAIN]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((len(me.lands), me.life), (2, 21))

    def test_paradox_also_activates_other_abilities_early(self):
        me, opp = pair()
        on_board(me, LURKER, entered=5)
        me.perms, me.jace.loyalty, me.hand = [PARADOX], 1, [MOUNTAIN, MOUNTAIN]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((len(me.lands), me.life, opp.life), (2, 22, 19))

    def test_kiora_untaps_an_attacker(self):
        me, opp = pair()
        on_board(me, KIORA, entered=5)
        bear = on_board(me, BEAR)
        me.jace.loyalty = 1
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["damage"], bear.tapped, me.jace.loyalty), (2, False, 0))

    def test_gideon_pings_new_abilities(self):
        me, opp = pair()
        on_board(opp, GIDEON)
        me.perms, me.jace.loyalty = [WILD], 4
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(me.life, 19)

    def test_without_grants_nothing_changes(self):
        me, opp = pair()
        me.jace.loyalty = 2
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(me.jace.loyalty, 1)


class GoldfishTests(unittest.TestCase):
    def test_choice_without_tokens(self):
        self.assertEqual(sim.walker_choice(4, [WILD], face_need=99, lands=3)[0], -3)  # Beast gibt es nicht: ziehen
        self.assertEqual(sim.walker_choice(4, [WARLORD], face_need=2, lands=3)[0], -4)  # Lethal
        self.assertEqual(sim.walker_choice(1, [LURKER], face_need=99, lands=3)[0], 2)
        self.assertEqual(sim.walker_choice(10, [AVATAR], face_need=99, lands=4)[0], -10)
        self.assertIsNone(sim.walker_choice(0, [WILD], face_need=99, lands=3))

    def test_goldfish_lurker_pings(self):
        hand = [SWAMP] * 6 + [LURKER]
        order = hand + [SWAMP] * 20

        def face(card):
            with mock.patch("components.mulligan.random.shuffle", lambda x: None):
                r = sim.simulate(hand[:6] + [card] + order[7:], 1, False, 3, 8, True, False, None, 11, 20, 6, True, 3,
                                 6, False, False, 5, True)
            return r["effects"]["face"]

        plain = LURKER._replace(walker_grants=(), walker_no_death=False, name="Plain Lurker")
        self.assertGreater(face(LURKER), face(plain))
        self.assertGreaterEqual(face(LURKER), 3)  # Jace bleibt bei 0 liegen und pingt weiter


if __name__ == "__main__":
    unittest.main()
