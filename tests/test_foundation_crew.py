"""Grundlagen fuer kommende Sets, Teil 4: Fahrzeuge mit Crew (702.122) und "tap target creature defending player
controls" beim Angriff. Spielentscheidungen (Nutzer 2026-10-20): fuer den Angriff crewen wir mit Kreaturen, die in
diesem Zug nicht angreifen koennen, oder wenn das Fahrzeug mehr Schaden macht als die Kreaturen, die dafuer tappen;
im Zug des Gegners crewen wir zum Blocken nach den normalen Block-Regeln; getappt wird der gefaehrlichste Blocker,
der unseren staerksten Angreifer aufhalten wuerde. Kartentexte aus MSH und SOS."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
VEH = f"Artifact {DASH} Vehicle"
PLAINS = W["Plains"]
BEAR = W["Test Bear"]


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="W"):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)


def make(*args, **kwargs):
    return card_info(raw(*args, **kwargs))[0]


RAW = {
    "skycoach": raw("Test Skycoach", VEH, "{3}", 3, "Flying\nCrew 2 (Tap any number of creatures you control with "
                    "total power 2 or more: This Vehicle becomes an artifact creature until end of turn.)", "3", "2",
                    ["Flying", "Crew"], ""),
    "boat": raw("Test Boat", VEH, "{2}{U}", 3, "Crew 2 (Tap any number of creatures you control with total power 2 or "
                "more: This Vehicle becomes an artifact creature until end of turn.)", "4", "4", ["Crew"], "U"),
    "shield": raw("Captain America's Shield", f"Legendary Artifact {DASH} Equipment", "{2}", 2,
                  "Indestructible\nEquipped creature gets +0/+8 and has vigilance.\nWhenever equipped creature "
                  "attacks, tap target creature defending player controls.\nEquip {2}",
                  keywords=["Indestructible", "Equip"], colors=""),
    "tapper": raw("Test Tapper", f"Creature {DASH} Soldier", "{2}{W}", 3, "Whenever this creature attacks, tap target "
                  "creature defending player controls.", "2", "2"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}

OGRE = make("Ogre", f"Creature {DASH} Ogre", "{2}{R}", 3, "", "3", "3", colors="R")
TITAN = make("Titan", f"Creature {DASH} Giant", "{4}{G}", 5, "", "5", "5", colors="G")
WALL = make("Wall", f"Creature {DASH} Wall", "{1}{W}", 2, "Defender", "0", "4", ["Defender"])
BIRD = make("Bird", f"Creature {DASH} Bird", "{1}{W}", 2, "Flying", "1", "1", ["Flying"])


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


def vehicle(p, card, since=0):
    p.perms.append(card)
    p.vehicles.append({"card": card, "since": since, "crewed": None, "tapped": False})


class ParseTests(unittest.TestCase):
    def test_vehicle(self):
        self.assertEqual(C["skycoach"].vehicle, (2, 3, 2, ("flying",)))
        self.assertFalse(C["skycoach"].is_creature)

    def test_tap_triggers(self):
        self.assertTrue(C["shield"].equip_attack_tap)
        self.assertEqual(C["shield"].equip_kw, ("vigilance",))
        self.assertTrue(C["tapper"].attack_tap)

    def test_coverage(self):
        for key in RAW:
            self.assertEqual([line for _c, _m, line in analyze_card(RAW[key])], [], key)


class EnterTests(unittest.TestCase):
    def test_vehicle_is_registered(self):
        me, opp = pair()
        bt._resolve(me, opp, C["boat"], 3, entry())
        self.assertEqual([v["since"] for v in me.vehicles], [3])
        self.assertIn(C["boat"], me.perms)


class CrewAttackTests(unittest.TestCase):
    def test_fresh_creature_crews(self):
        me, opp = pair()
        vehicle(me, C["boat"])
        on_board(me, BEAR, entered=5)  # frisch: greift nicht an
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 4)

    def test_defender_crews(self):
        me, opp = pair()
        vehicle(me, C["boat"])
        on_board(me, make("Big Wall", f"Creature {DASH} Wall", "{2}", 2, "Defender", "2", "5", ["Defender"]))
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 4)

    def test_crew_when_vehicle_hits_harder(self):
        me, opp = pair()
        vehicle(me, C["boat"])
        on_board(me, BEAR)  # 2 Schaden, das Fahrzeug macht 4
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 4)

    def test_no_crew_when_creatures_hit_harder(self):
        me, opp = pair()
        vehicle(me, C["skycoach"])
        on_board(me, OGRE)  # 3 Schaden, das Fahrzeug auch nur 3
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 3)
        self.assertFalse(any("crew" in ev.lower() for ev in e["events"]))

    def test_not_too_weak_to_crew(self):
        me, opp = pair()
        vehicle(me, C["boat"])
        on_board(me, make("Mouse", f"Creature {DASH} Mouse", "{W}", 1, "", "1", "1"), entered=5)
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 0)

    def test_vehicle_entered_this_turn_cannot_attack(self):
        me, opp = pair()
        vehicle(me, C["boat"], since=5)
        on_board(me, BEAR, entered=5)
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 0)

    def test_back_to_artifact_after_the_turn(self):
        me, opp = pair()
        vehicle(me, C["boat"])
        on_board(me, BEAR, entered=5)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual([c.card.name for c in me.creatures], ["Test Bear"])
        self.assertIn(C["boat"], me.perms)
        self.assertTrue(me.vehicles[0]["tapped"])

    def test_crewed_vehicle_dies(self):
        me, opp = pair()
        vehicle(me, C["skycoach"])
        crew = on_board(me, BEAR, entered=5)
        e = entry()
        me.turn_start = 5
        bt.crew_to_attack(me, opp, 5, e)
        car = next(c for c in me.creatures if c.card.name == "Test Skycoach")
        self.assertTrue(crew.tapped)
        self.assertTrue(car.has("flying"))
        car.dead = True
        bt.bury((me, opp), e)
        self.assertIn(C["skycoach"], me.graveyard)
        self.assertNotIn(C["skycoach"], me.perms)
        bt.cleanup((me, opp))
        self.assertEqual(me.vehicles, [])


class CrewBlockTests(unittest.TestCase):
    def test_crew_to_block_and_kill(self):
        me, opp = pair()
        vehicle(opp, C["boat"])
        on_board(opp, BEAR)
        ogre = on_board(me, OGRE)
        blocks = bt.crew_to_block(opp, [ogre], 6, entry())
        self.assertEqual([b.card.name for b in dict((id(a), bs) for a, bs in blocks)[id(ogre)]], ["Test Boat"])

    def test_no_crew_without_a_good_block(self):
        me, opp = pair()
        vehicle(opp, C["boat"])
        on_board(opp, BEAR)
        titan = on_board(me, TITAN)
        bt.crew_to_block(opp, [titan], 6, entry())
        self.assertFalse(any(c.card.name == "Test Boat" for c in opp.creatures))
        self.assertFalse(opp.creatures[0].tapped)

    def test_tapped_vehicle_cannot_block(self):
        me, opp = pair()
        vehicle(opp, C["boat"])
        opp.vehicles[0]["tapped"] = True
        on_board(opp, BEAR)
        ogre = on_board(me, OGRE)
        bt.crew_to_block(opp, [ogre], 6, entry())
        self.assertFalse(any(c.card.name == "Test Boat" for c in opp.creatures))

    def test_blocker_in_use_does_not_crew(self):
        me, opp = pair()
        vehicle(opp, C["boat"])
        titan = on_board(opp, TITAN)  # blockt die Ogre selbst (toetet und ueberlebt), crewt deshalb nicht
        ogre = on_board(me, OGRE)
        blocks = bt.crew_to_block(opp, [ogre], 6, entry())
        self.assertEqual(dict((id(a), bs) for a, bs in blocks)[id(ogre)], [titan])
        self.assertFalse(any(c.card.name == "Test Boat" for c in opp.creatures))


class TapTests(unittest.TestCase):
    def test_tap_the_blocker_of_the_strongest(self):
        me, opp = pair()
        tapper = on_board(me, C["tapper"])
        titan = on_board(me, TITAN)
        wall = on_board(opp, make("Big Wall", f"Creature {DASH} Wall", "{3}", 3, "Defender", "0", "6", ["Defender"]))
        bear = on_board(opp, BEAR)  # gefaehrlicher, haelt den Titan aber nicht auf
        bt.attack_taps(me, opp, [tapper, titan], entry())
        self.assertEqual((wall.tapped, bear.tapped), (True, False))

    def test_most_dangerous_when_none_stops_it(self):
        me, opp = pair()
        titan = on_board(me, TITAN)
        wall = on_board(opp, WALL)
        bear = on_board(opp, BEAR)
        bt.attack_taps(me, opp, [titan, on_board(me, C["tapper"])], entry())
        self.assertEqual((wall.tapped, bear.tapped), (False, True))

    def test_flyer_blocker_for_a_flyer(self):
        me, opp = pair()
        tapper = on_board(me, C["tapper"])
        flyer = on_board(me, make("Drake", f"Creature {DASH} Drake", "{3}{U}", 4, "Flying", "4", "4", ["Flying"],
                                  "U"))
        bird = on_board(opp, BIRD)
        ogre = on_board(opp, OGRE)
        bt.attack_taps(me, opp, [tapper, flyer], entry())
        self.assertEqual((bird.tapped, ogre.tapped), (True, False))

    def test_equipped_attacker_taps(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        bear.gear.append(C["shield"])
        ogre = on_board(opp, OGRE)
        bt.attack_taps(me, opp, [bear], entry())
        self.assertTrue(ogre.tapped)

    def test_hexproof_is_skipped(self):
        me, opp = pair()
        tapper = on_board(me, C["tapper"])
        hex_ogre = on_board(opp, make("Hex Ogre", f"Creature {DASH} Ogre", "{2}{G}", 3, "Hexproof", "3", "3",
                                      ["Hexproof"], "G"))
        bear = on_board(opp, BEAR)
        bt.attack_taps(me, opp, [tapper], entry())
        self.assertEqual((hex_ogre.tapped, bear.tapped), (False, True))

    def test_tapped_blocker_lets_damage_through(self):
        me, opp = pair()
        on_board(me, C["tapper"])
        on_board(opp, WALL)
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 2)


if __name__ == "__main__":
    unittest.main()
