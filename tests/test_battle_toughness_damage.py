"""Kampfmodell: Ghalta the Immovable - eigene Kreaturen mit mehr Toughness als Power machen Kampfschaden in Hoehe
ihrer Toughness (510.1a), als Angreifer und als Blocker. Das gilt fuer Schaden, Lifelink, Trample, Angriffswahl,
Blocks und Lethal. Fight bleibt bei Power (kein Kampfschaden)."""
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS = W["Plains"]


def make(name, cost, cmc, text, power, toughness, keywords=(), type_line=CRE):
    return card_info(_card(name, type_line, cost, cmc, "W", text, list(keywords), power, toughness))[0]


IMMOV = make("Ghalta the Immovable", "{8}{W}", 9,
             "This spell costs {X} less to cast, where X is the greatest toughness among creatures you control.\n"
             "Creatures you control can attack as though they didn't have defender.\nEach creature you control with "
             "toughness greater than its power assigns combat damage equal to its toughness rather than its power.",
             "4", "12", type_line=f"Legendary Creature {DASH} Elder Dinosaur")
WALL = make("Wall", "{1}{W}", 2, "Defender", "0", "6", ["Defender"])
TANK = make("Tank", "{1}{W}", 2, "", "1", "4")
LINK = make("Healer", "{1}{W}", 2, "Lifelink", "1", "4", ["Lifelink"])
TRAMPLER = make("Rhino", "{1}{W}", 2, "Trample", "1", "5", ["Trample"])
BRUTE = make("Brute", "{3}{R}", 4, "", "4", "1")
OGRE = make("Ogre", "{2}{R}", 3, "", "3", "3")
BIG = make("Big", "{3}{G}", 4, "", "4", "4")
BEAR = W["Test Bear"]


def player(name="Wir"):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], [PLAINS] * 20
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


class DamageValueTests(unittest.TestCase):
    def test_parse(self):
        self.assertTrue(IMMOV.toughness_damage)
        self.assertFalse(TANK.toughness_damage)

    def test_value(self):
        me, opp = pair()
        tank, brute = on_board(me, TANK), on_board(me, BRUTE)
        self.assertEqual((tank.dmg, brute.dmg), (1, 4))
        ghalta = on_board(me, IMMOV)
        self.assertEqual((tank.dmg, brute.dmg, ghalta.dmg), (4, 4, 12))
        tank.tpump += 2
        self.assertEqual(tank.dmg, 6)
        ghalta.dead = True
        self.assertEqual(tank.dmg, 1)

    def test_only_for_the_controller(self):
        me, opp = pair()
        on_board(opp, IMMOV)
        self.assertEqual(on_board(me, TANK).dmg, 1)


class CombatTests(unittest.TestCase):
    def test_unblocked_attacker(self):
        me, _opp = pair()
        on_board(me, IMMOV)
        tank = on_board(me, TANK)
        res = bt.resolve_combat([(tank, [])])
        self.assertEqual(res["player"], 4)

    def test_attacker_kills_blocker(self):
        me, opp = pair()
        on_board(me, IMMOV)
        self.assertEqual(bt.outcome(on_board(me, TANK), [on_board(opp, OGRE)]), (False, [True]))

    def test_blocker_kills_attacker(self):
        me, opp = pair()
        on_board(me, IMMOV)
        wall = on_board(me, WALL)
        self.assertEqual(bt.outcome(on_board(opp, BIG), [wall]), (True, [False]))

    def test_lifelink_gains_the_damage(self):
        me, _opp = pair()
        on_board(me, IMMOV)
        res = bt.resolve_combat([(on_board(me, LINK), [])])
        self.assertEqual((res["player"], res["lifelink_attacker"]), (4, 4))

    def test_lifelink_of_a_blocker(self):
        me, opp = pair()
        on_board(me, IMMOV)
        res = bt.resolve_combat([(on_board(opp, BIG), [on_board(me, LINK)])])
        self.assertEqual(res["lifelink_defender"], 4)

    def test_trample_over_a_blocker(self):
        me, opp = pair()
        on_board(me, IMMOV)
        res = bt.resolve_combat([(on_board(me, TRAMPLER), [on_board(opp, BEAR)])])
        self.assertEqual(res["player"], 3)

    def test_max_through(self):
        me, _opp = pair()
        tank = on_board(me, TANK)
        self.assertEqual(bt.max_through([tank], []), 1)
        on_board(me, IMMOV)
        self.assertEqual(bt.max_through([tank], []), 4)

    def test_wall_attacks(self):
        me, opp = pair()
        on_board(me, IMMOV, entered=5)  # frisch, greift selbst nicht an
        on_board(me, WALL)
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 6)

    def test_zero_power_wall_without_ghalta_stays_home(self):
        me, opp = pair()
        wall = on_board(me, WALL)
        self.assertFalse(bt.can_attack(wall, 5))

    def test_lethal_with_toughness(self):
        me, opp = pair()
        on_board(me, IMMOV, entered=5)
        on_board(me, TANK)
        on_board(me, TANK)
        on_board(opp, BEAR).tapped = True
        opp.life = 8
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertLessEqual(opp.life, 0)

    def test_opponent_does_not_attack_into_the_wall(self):
        me, opp = pair()
        on_board(me, IMMOV).tapped = True
        on_board(me, WALL)
        on_board(opp, BIG)
        e = bt.take_turn(opp, me, 6, 3, skip_draw=True)
        self.assertEqual(e["attacks"], [])  # die Mauer wuerde den 4/4 mit 6 Schaden toeten und ueberleben

    def test_opponent_attacks_the_wall_without_ghalta(self):
        me, opp = pair()
        on_board(me, WALL)
        on_board(opp, BIG)
        e = bt.take_turn(opp, me, 6, 3, skip_draw=True)
        self.assertEqual(len(e["attacks"]), 1)

    def test_danger_uses_combat_damage(self):
        me, _opp = pair()
        on_board(me, IMMOV)
        self.assertGreater(bt.danger(on_board(me, TANK)), bt.danger(on_board(me, OGRE)))

    def test_power_itself_is_unchanged(self):
        me, _opp = pair()
        on_board(me, IMMOV)
        tank = on_board(me, TANK)
        self.assertEqual((tank.power, tank.dmg), (1, 4))  # Fight und "damage equal to its power" nutzen Power


class GoldfishTests(unittest.TestCase):
    """Im Goldfish gelten "Defender greift an" und Schaden nach Toughness genauso."""

    def test_defender_attacks_with_ghalta(self):
        from components import simulation as sim
        self.assertFalse(sim._attacks((WALL, 1), 3, [(WALL, 1)]))
        self.assertTrue(sim._attacks((WALL, 1), 3, [(WALL, 1), (IMMOV, 2)]))
        self.assertFalse(sim._attacks((WALL, 1), 3))

    def test_damage_by_toughness(self):
        from components import simulation as sim
        board = [(TANK, 1), (BRUTE, 1)]
        self.assertEqual([sim.combat_damage(board, [0, 0], {}, i) for i in range(2)], [1, 4])
        board.append((IMMOV, 1))
        self.assertEqual([sim.combat_damage(board, [1, 0, 0], {}, i) for i in range(3)], [5, 4, 12])
        self.assertEqual(sim.combat_damage(board, [0, 0, 0], {0: 5}, 0), 6)  # Pump +5/+0: Power 6 > Toughness 4

    def test_goldfish_game_counts_toughness(self):
        import random
        from components import simulation as sim
        plains = card_info(_card("Plains", f"Basic Land {DASH} Plains", text="({T}: Add {W}.)", produced=["W"]))[0]
        cheap = IMMOV._replace(alts=((0, (("W", 1),)),), mv=1)  # sofort spielbar, damit der Effekt frueh greift
        plain = cheap._replace(toughness_damage=False, defender_attack=False)

        def total(big):
            deck = [plains] * 17 + [WALL] * 12 + [big] * 11
            random.seed(3)
            r = sim.simulate(deck, 40, False, 3, 6, True, False, None, 11, 20, 6, True, 3, 6, False, False, 5, False)
            return sum(r["dmg"]) / max(1, len(r["dmg"])), len(r["dmg"])

        with_ghalta, without = total(cheap), total(plain)
        self.assertGreater(with_ghalta[1], without[1])  # mehr Spiele erreichen den Schaden
        walls_home = total(cheap._replace(defender_attack=False))
        self.assertGreater(with_ghalta[1], walls_home[1])  # die Mauern greifen mit an


if __name__ == "__main__":
    unittest.main()
