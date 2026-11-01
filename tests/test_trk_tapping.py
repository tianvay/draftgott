"""Star Trek (TRK), Paket D (Nutzer 2026-11-02): Tappen als Kosten und Ausloeser - Brad Boimler (getappt: diesen Zug
eine Marke mehr, nur nebenbei getappt), Captain Jean-Luc Picard (Officer-Token beim Wirken von Kreaturen und
Raumschiffen; sieben Officers tappen in Main 2 wie Station: Raumschiff mit sieben Charge-Marken), Worf, Honor-Bound
Warrior (zwei Artefakte/Kreaturen tappen in Main 2 wie Station: +1/+1-Marke), Kira Nerys (Kreaturen kommen waehrend
unseres Angriffs angreifend ins Spiel, +1/+1 bis Rundenende), Nog (Scout, Officer: Laender aus dem Friedhof, ein
zusaetzlicher Landdrop), I'm a Doctor, Not a . . . Lwaxana Troi steht auf der To-do-Liste. Nur Kampfmodell.
Kartentexte aus TRK."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]

RAW = {
    "brad": _card("Brad Boimler, Eager Ensign", f"Legendary Creature {DASH} Human Officer", "{1}{W}", 2, "W",
                  "Lifelink\nWhenever Brad Boimler becomes tapped, until end of turn, if one or more counters would be "
                  "put on a permanent you control, that many plus one of each of those kinds of counters are put on "
                  "that permanent instead.", ["Lifelink"], "2", "2"),
    "picard": _card("Captain Jean-Luc Picard", f"Legendary Creature {DASH} Human Officer", "{2}{W}", 3, "W",
                    "Other creatures you control get +1/+1.\nWhenever you cast a creature or Spacecraft spell, create a "
                    "1/1 red Officer creature token.\nTap seven untapped Officers you control: Search your library for "
                    "a Spacecraft card, put it onto the battlefield with seven charge counters on it, then shuffle.",
                    [], "2", "3"),
    "worf": _card("Worf, Honor-Bound Warrior", f"Legendary Creature {DASH} Klingon Warrior Officer", "{R/W}{R/W}", 2,
                  "RW", "Whenever you attack while creatures you control have total power 8 or greater, double Worf's "
                  "power until end of turn.\nTap two untapped artifacts and/or creatures you control: Put a +1/+1 "
                  "counter on Worf. Activate only as a sorcery.", [], "1", "1"),
    "kira": _card("Kira Nerys, Firebrand", f"Legendary Creature {DASH} Bajoran Soldier", "{1}{R}{W}", 3, "RW",
                  "Trample\nIf a creature you control would enter while you control an attacking creature, instead it "
                  "enters tapped and attacking.\nWhenever another creature you control enters, it gets +1/+1 until end "
                  "of turn.", ["Trample"], "4", "3"),
    "nog": _card("Nog, Ambitious Cadet", f"Legendary Creature {DASH} Ferengi Rogue", "{B}{G}", 2, "BG", "Menace\n{1}: "
                 "If Nog is a Rogue, he becomes a Ferengi Scout with base power and toughness 3/4 and gains \"Whenever "
                 "Nog becomes tapped, surveil 2.\"\n{3}: If Nog is a Scout, he becomes a Ferengi Officer and gains "
                 "\"You may play lands from your graveyard\" and \"You may play an additional land on each of your "
                 "turns.\"", ["Menace"], "2", "2"),
    "doctor": _card("I'm a Doctor, Not a . . .", "Instant", "{G}", 1, "G", "Put a +1/+1 counter on target creature you "
                    "control. Untap it. Until end of turn, it gets +1/+1 and becomes a Doctor. (It loses all other "
                    "creature types.)"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}


def make(name, cost, cmc, text="", power=None, toughness=None, type_line=f"Creature {DASH} Test", colors="W"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, [], power, toughness))[0]


BEAR = make("Bear", "{1}{W}", 2, "", "2", "2")
GIANT = make("Giant", "{4}{R}", 5, "", "6", "6", colors="R")
SHIP = make("Test Cruiser", "{4}", 4, "Station (Tap another creature you control: Put charge counters equal to its "
            "power on this Spacecraft. Station only as a sorcery. It's an artifact creature at 7+.)\n7+ | Flying",
            "5", "5", f"Artifact {DASH} Spacecraft", "")
SWAMP = card_info(_card("Swamp", f"Basic Land {DASH} Swamp", text="({T}: Add {B}.)", produced=["B"]))[0]
OFFICER = C["picard"].cast_trig[0][1][0][2] if C["picard"].cast_trig else None


def player(name="Wir"):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], [PLAINS] * 20
    return p


def pair():
    me, opp = player(), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": [], "land": ""}


def put(p, card, entered=0):
    c = bt.Creature(card, entered)
    c.gy, c.ctl = p.graveyard, p
    p.creatures.append(c)
    return c


def open_lines(key):
    return [l for _c, _m, l in analyze_card(RAW[key])]


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertEqual(C["brad"].became_tapped, ("counter_boost",))
        self.assertEqual(C["picard"].cast_trig[0][0], "creature_spacecraft")
        self.assertEqual(C["picard"].officer_tutor, (7, 7))
        self.assertIn("officer", OFFICER.creature_types)
        self.assertTrue(C["worf"].tap2_counter)
        self.assertEqual((C["kira"].kira_attack, C["kira"].kira_pump), (True, 1))
        self.assertTrue(C["nog"].nog_levels)
        self.assertEqual(C["doctor"].modes, ((("counter", 1, 1), ("pump", 1)),))
        self.assertTrue(C["doctor"].untap_target)
        self.assertEqual((BEAR.officer_tutor, BEAR.tap2_counter, BEAR.kira_attack, BEAR.nog_levels), ((), False, False,
                                                                                                     False))

    def test_coverage(self):
        for key in RAW:
            self.assertEqual(open_lines(key), [], key)


class BradTests(unittest.TestCase):
    def test_tapped_gives_one_more(self):
        me, _opp = pair()
        brad, bear = put(me, C["brad"]), put(me, BEAR)
        bear.bonus += 1
        self.assertEqual(bear.bonus, 1)
        brad.tapped = True
        bear.bonus += 2
        self.assertEqual(bear.bonus, 4)
        me.now += 1  # naechster Zug: vorbei
        bear.bonus += 1
        self.assertEqual(bear.bonus, 5)

    def test_charge_and_quest_counters(self):
        me, _opp = pair()
        put(me, C["brad"]).tapped = True
        st = {"card": SHIP, "live": SHIP, "since": 0, "charge": 0, "creature": None}
        bt.add_charge(me, st, 3)
        self.assertEqual(st["charge"], 4)
        m = {"card": SHIP, "quest": 0}
        bt.add_quest(me, m)
        self.assertEqual(m["quest"], 2)


class PicardTests(unittest.TestCase):
    def test_officer_on_creature_and_spacecraft(self):
        me, _opp = pair()
        put(me, C["picard"])
        bt.on_cast(me, BEAR, 3, entry())
        bt.on_cast(me, SHIP, 3, entry())
        bt.on_cast(me, C["doctor"], 3, entry())
        self.assertEqual([c.card.name for c in me.creatures].count(OFFICER.name), 2)

    def test_seven_officers_fetch_spacecraft(self):
        me, opp = pair()
        put(me, C["picard"])
        for _ in range(6):
            put(me, OFFICER)
        me.library = [PLAINS, SHIP, PLAINS]
        bt.picard_tutor(me, opp, 5, entry())
        self.assertNotIn(SHIP, me.library)
        st = next(s for s in me.stations if s["card"] == SHIP)
        self.assertEqual(st["charge"], 7)
        self.assertIsNotNone(st["creature"])  # ab 7 Marken eine Kreatur
        self.assertEqual(sum(c.tapped for c in me.creatures), 7)

    def test_not_against_lethal_counterattack(self):
        me, opp = pair()
        put(me, C["picard"])
        for _ in range(6):
            put(me, OFFICER)
        me.library = [SHIP]
        me.life = 5
        put(opp, GIANT)
        bt.picard_tutor(me, opp, 5, entry())
        self.assertEqual(me.library, [SHIP])

    def test_attacked_officers_do_not_count(self):
        me, opp = pair()
        put(me, C["picard"])
        for _ in range(6):
            put(me, OFFICER).attacked = me.now
        me.library = [SHIP]
        bt.picard_tutor(me, opp, 5, entry())
        self.assertEqual(me.library, [SHIP])


class WorfTests(unittest.TestCase):
    def test_taps_weakest_two(self):
        me, opp = pair()
        worf = put(me, C["worf"])
        put(me, BEAR)
        put(me, BEAR)
        put(me, GIANT)
        bt.worf_counters(me, opp, 5, entry())
        self.assertEqual(worf.bonus, 1)  # Worf selbst und der Riese bleiben ungetappt: 2 Baeren, dann nur noch einer
        self.assertEqual([c.card.name for c in me.creatures if c.tapped], ["Bear", "Bear"])

    def test_clues_first(self):
        me, opp = pair()
        worf = put(me, C["worf"])
        bear = put(me, BEAR)
        me.clues = 2
        bt.worf_counters(me, opp, 5, entry())
        self.assertEqual((worf.bonus, bear.tapped), (1, False))

    def test_keeps_blockers_against_lethal(self):
        me, opp = pair()
        worf = put(me, C["worf"])
        put(me, BEAR)
        put(me, BEAR)
        me.life = 6
        put(opp, GIANT)
        put(opp, GIANT)  # Worf und ein Baer halten nur einen auf: hoechstens ein Baer darf tappen
        bt.worf_counters(me, opp, 5, entry())
        self.assertEqual(worf.bonus, 0)


class KiraTests(unittest.TestCase):
    def test_pump_on_enter(self):
        me, opp = pair()
        put(me, C["kira"])
        bear = put(me, BEAR, 3)
        bt.creature_enters(me, bear, 3, entry(), opp, cast=False)
        self.assertEqual((bear.power, bear.toughness, bear.tapped), (3, 3, False))

    def test_enters_attacking(self):
        me, opp = pair()
        kira = put(me, C["kira"])
        kira.attacked = me.now
        me.kira_join = []
        tok = put(me, OFFICER, me.now)
        bt.creature_enters(me, tok, me.now, entry(), opp, cast=False)
        self.assertTrue(tok.tapped)
        self.assertEqual((tok.attacked, me.kira_join), (me.now, [tok]))


class NogTests(unittest.TestCase):
    def test_levels(self):
        me, opp = pair()
        nog = put(me, C["nog"])
        me.open = [("B",)]
        bt.nog_levels(me, opp, 5, entry())
        self.assertEqual((nog.power, nog.toughness, nog.card.became_tapped), (3, 4, ("surveil", 2)))
        self.assertIn("scout", nog.card.creature_types)
        self.assertEqual(nog.base_card, C["nog"])
        me.open = [("B",)] * 3
        bt.nog_levels(me, opp, 5, entry())
        self.assertIn("officer", nog.card.creature_types)
        self.assertEqual(me.open, [])

    def test_scout_surveils_when_tapped(self):
        me, opp = pair()
        nog = put(me, C["nog"])
        me.open = [("B",)]
        bt.nog_levels(me, opp, 5, entry())
        me.library = [PLAINS] * 5
        nog.tapped = True
        e = entry()
        bt.tap_check((me,), e)
        self.assertTrue(any("Surveil" in ev or "surveil" in ev.lower() for ev in e["events"]), e["events"])

    def test_officer_plays_lands_from_graveyard(self):
        me, opp = pair()
        nog = put(me, C["nog"])
        nog.card = nog.card._replace(creature_types=("ferengi", "officer"), nog_levels=False, nog_officer=True)
        nog.base_card = C["nog"]
        me.lands = [SWAMP] * 2
        me.hand, me.graveyard, me.library = [SWAMP], [SWAMP], [PLAINS] * 10
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((len(me.lands), me.graveyard, me.hand), (4, [], []))

    def test_officer_land_drop_only_from_graveyard(self):
        me, opp = pair()
        nog = put(me, C["nog"])
        nog.card = nog.card._replace(creature_types=("ferengi", "officer"), nog_levels=False, nog_officer=True)
        me.lands = [SWAMP] * 2
        me.hand, me.graveyard, me.library = [], [SWAMP], [PLAINS] * 10
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((len(me.lands), me.graveyard, me.hand), (3, [], []))


if __name__ == "__main__":
    unittest.main()
