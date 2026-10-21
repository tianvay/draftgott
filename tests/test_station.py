"""Station (702.184) und Station-Karten (721): Charge-Marken durch Tappen einer anderen eigenen Kreatur (ihre Power),
nur zur Sorcery-Zeit; ab {N+} gelten die Faehigkeiten der Stufe, mit P/T-Box wird die Karte zur Artefaktkreatur.
Spielregeln (2026-10-21, wie Crew): in Main 2 mit Kreaturen, die nicht gegen einen toedlichen Gegenangriff fehlen,
die staerksten zuerst, bis die hoechste Stufe erreicht ist; zuerst das Raumschiff, das seiner naechsten Stufe am
naechsten ist. Kartentexte aus EOE und TRK."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
SHIP = f"Artifact {DASH} Spacecraft"
PLAINS = W["Plains"]
BEAR = W["Test Bear"]
REMINDER = ("Station (Tap another creature you control: Put charge counters equal to its power on this Spacecraft. "
            "Station only as a sorcery. It's an artifact creature at {n}+.)")


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors=""):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)


def make(*args, **kwargs):
    return card_info(raw(*args, **kwargs))[0]


RAW = {
    "sweeper": raw("Wurmwall Sweeper", SHIP, "{2}", 2, "When this Spacecraft enters, surveil 2.\n"
                   + REMINDER.format(n=4) + "\n4+ | Flying", "2", "2", ["Station", "Surveil"]),
    "frigate": raw("Lumen-Class Frigate", SHIP, "{1}{W}", 2, REMINDER.format(n=12) + "\n2+ | Other creatures you "
                   "control get +1/+1.\n12+ | Flying, lifelink", "3", "5", ["Station"], "W"),
    "sawship": raw("Galvanizing Sawship", SHIP, "{5}{R}", 6, REMINDER.format(n=3) + "\n3+ | Flying, haste", "6", "5",
                   ["Station"], "R"),
    "ds9": raw("Deep Space 9", f"Legendary Artifact {DASH} Spacecraft", "{9}", 9,
               "Station (Tap another creature you control: Put charge counters equal to its power on this Spacecraft. "
               "Station only as a sorcery.)\n9+ | Creatures you control get +3/+3.", keywords=["Station"]),
    "d7": raw("D-7 Battle Cruiser", SHIP, "{1}{R}", 2, REMINDER.format(n=8) + "\n3+ | At the beginning of combat on "
              "your turn, create a 2/1 red Klingon Warrior creature token with haste. Sacrifice it at the beginning of "
              "the next end step.\n8+ | Flying", "3", "3", ["Station"], "R"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}

OGRE = make("Ogre", f"Creature {DASH} Ogre", "{2}{R}", 3, "", "3", "3", colors="R")
GIANT = make("Giant", f"Creature {DASH} Giant", "{4}", 4, "", "4", "4")


def player(name="Wir"):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], [PLAINS] * 20
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


def ship(p, card, since=0, charge=0):
    p.perms.append(card)
    p.stations.append({"card": card, "since": since, "charge": charge, "creature": None})
    return p.stations[-1]


def ship_creature(p, name):
    return next((c for c in p.creatures if c.card.name == name), None)


class ParseTests(unittest.TestCase):
    def test_creature_threshold_and_keywords(self):
        self.assertEqual(C["sweeper"].station, (4, 2, 2, ((4, ("flying",), None),)))
        self.assertFalse(C["sweeper"].is_creature)

    def test_team_pump_threshold(self):
        self.assertEqual(C["frigate"].station, (12, 3, 5, ((2, (), (1, 1, "others")), (12, ("flying", "lifelink"),
                                                                                      None))))
        self.assertEqual(C["ds9"].station, (0, 0, 0, ((9, (), (3, 3, "all")),)))

    def test_unknown_threshold_text(self):
        self.assertEqual(C["d7"].station, (8, 3, 3, ((8, ("flying",), None),)))

    def test_coverage(self):
        for key in ("sweeper", "frigate", "sawship", "ds9"):
            self.assertEqual([line for _c, _m, line in analyze_card(RAW[key])], [], key)
        open_lines = {line for _c, _m, line in analyze_card(RAW["d7"])}
        self.assertEqual(len(open_lines), 1)
        self.assertTrue(open_lines.pop().startswith("3+"))


class EnterTests(unittest.TestCase):
    def test_registered_on_enter(self):
        me, opp = pair()
        bt._resolve(me, opp, C["sweeper"], 3, entry())
        self.assertEqual([(s["card"].name, s["since"], s["charge"]) for s in me.stations],
                         [("Wurmwall Sweeper", 3, 0)])


class StationTests(unittest.TestCase):
    def test_fresh_creature_stations(self):
        me, opp = pair()
        st = ship(me, C["sweeper"])
        bear = on_board(me, BEAR, entered=5)
        bt.station_phase(me, opp, 5, entry())
        self.assertEqual((st["charge"], bear.tapped), (2, True))
        self.assertIsNone(ship_creature(me, "Wurmwall Sweeper"))

    def test_becomes_a_creature(self):
        me, opp = pair()
        st = ship(me, C["sweeper"], charge=2)
        on_board(me, BEAR)
        bt.station_phase(me, opp, 5, entry())
        car = ship_creature(me, "Wurmwall Sweeper")
        self.assertEqual((car.power, car.toughness, car.has("flying")), (2, 2, True))
        self.assertNotIn(C["sweeper"], me.perms)
        self.assertIs(st["creature"], car)

    def test_ship_attacks_next_turn(self):
        me, opp = pair()
        ship(me, C["sweeper"], since=1, charge=4)
        bt.station_phase(me, opp, 3, entry())  # keine Kreatur zum Tappen, die Stufe ist schon erreicht
        bt.update_stations(me, 3, entry())
        bt.cleanup((me, opp))
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 2)

    def test_stops_at_the_highest_threshold(self):
        me, opp = pair()
        st = ship(me, C["sweeper"])
        giant = on_board(me, GIANT)
        bear = on_board(me, BEAR)
        bt.station_phase(me, opp, 5, entry())
        self.assertEqual((st["charge"], giant.tapped, bear.tapped), (4, True, False))

    def test_not_when_counterattack_is_lethal(self):
        me, opp = pair()
        me.life = 3
        st = ship(me, C["sweeper"])
        bear = on_board(me, BEAR)
        on_board(opp, OGRE)
        bt.station_phase(me, opp, 5, entry())
        self.assertEqual((st["charge"], bear.tapped), (0, False))

    def test_others_pump_from_noncreature_ship(self):
        me, opp = pair()
        ship(me, C["frigate"])
        bear = on_board(me, BEAR)
        giant = on_board(me, GIANT, entered=5)
        bt.station_phase(me, opp, 5, entry())
        self.assertTrue(giant.tapped)
        self.assertEqual((bear.power, bear.toughness), (3, 3))

    def test_others_pump_not_on_the_ship_itself(self):
        me, _opp = pair()
        ship(me, C["frigate"], charge=12)
        bear = on_board(me, BEAR)
        bt.update_stations(me, 5, entry())
        car = ship_creature(me, "Lumen-Class Frigate")
        self.assertEqual((car.power, car.toughness, car.has("lifelink")), (3, 5, True))
        self.assertEqual(bear.power, 3)

    def test_team_pump_from_ds9(self):
        me, opp = pair()
        ship(me, C["ds9"], charge=9)
        bt.update_stations(me, 5, entry())
        bear = on_board(me, BEAR)
        self.assertEqual(bear.power, 5)

    def test_closest_ship_first(self):
        me, opp = pair()
        far = ship(me, C["frigate"])
        near = ship(me, C["sweeper"], charge=3)  # 1 bis zur Stufe 4, die Frigate braucht 2
        on_board(me, BEAR)
        bt.station_phase(me, opp, 5, entry())
        self.assertEqual((near["charge"], far["charge"]), (5, 0))

    def test_charge_stays_over_turns(self):
        me, opp = pair()
        st = ship(me, C["frigate"])
        on_board(me, BEAR)
        bt.station_phase(me, opp, 5, entry())
        bt.cleanup((me, opp))
        self.assertEqual(st["charge"], 2)

    def test_destroyed_ship_is_gone(self):
        me, opp = pair()
        ship(me, C["frigate"], charge=2)
        bt.destroy_permanent(me, C["frigate"], entry())
        on_board(me, BEAR)
        bt.station_phase(me, opp, 5, entry())
        self.assertEqual(me.stations, [])

    def test_ship_creature_dies(self):
        me, opp = pair()
        ship(me, C["sweeper"], charge=4)
        bt.update_stations(me, 5, entry())
        car = ship_creature(me, "Wurmwall Sweeper")
        car.dead = True
        bt.bury((me, opp), entry())
        self.assertIn(C["sweeper"], me.graveyard)
        bt.station_phase(me, opp, 7, entry())
        self.assertEqual(me.stations, [])

    def test_take_turn_stations_in_main_2(self):
        me, opp = pair()
        st = ship(me, C["sawship"])
        on_board(me, BEAR, entered=5)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(st["charge"], 2)


if __name__ == "__main__":
    unittest.main()
