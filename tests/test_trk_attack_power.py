"""Star Trek (TRK), Paket C (Nutzer 2026-11-01): "Whenever you attack while creatures you control have total power 8
or greater, ..." loest einmal aus, wenn wir mit mindestens einer Kreatur angreifen (508.1m); die Gesamtstaerke aller
eigenen Kreaturen zaehlt nach dem Erklaeren der Angreifer. Cantankerous Captain prueft sie zu Beginn des Kampfs nach
seinem Pump. Nur Kampfmodell. Kartentexte aus TRK."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
WHILE = "Whenever you attack while creatures you control have total power 8 or greater, "
PLAINS = W["Plains"]


def raw(name, type_line, cost, cmc, text, power, toughness, colors="W"):
    return _card(name, type_line, cost, cmc, colors, text, [], power, toughness)


RAW = {
    "janeway": raw("Hologram Janeway", f"Legendary Artifact Creature {DASH} Illusion Officer", "{2}{W}", 3,
                   WHILE + "put a +1/+1 counter on target creature.", "3", "3"),
    "tactical": raw("Tactical Officer", f"Creature {DASH} Human Officer", "{1}{W}", 2,
                    WHILE + "put a +1/+1 counter on this creature. Untap it.", "2", "1"),
    "una": raw("Una Chin-Riley, Number One", f"Legendary Creature {DASH} Illyrian Officer", "{4}{W}", 5,
               WHILE + "target attacking creature gets +2/+0 and gains first strike until end of turn.", "4", "5"),
    "captain": raw("Cantankerous Captain", f"Creature {DASH} Tellarite Officer", "{2}{R}", 3, "At the beginning of "
                   "combat on your turn, target creature you control gets +1/+0 until end of turn. Then that creature "
                   "gains menace until end of turn if creatures you control have total power 8 or greater. (It can't "
                   "be blocked except by two or more creatures.)", "2", "3", "R"),
    "laan": raw("La'An Noonien-Singh, Security", f"Legendary Creature {DASH} Human Soldier", "{2}{R}{R}", 4,
                WHILE + "target creature can't block this turn.", "4", "3", "R"),
    "kirk": raw("Kirk, Commanding Officer", f"Legendary Creature {DASH} Human Officer", "{1}{R}{W}", 3,
                WHILE + "exile the top card of your library. You may play that card this turn.\n{2}, Sacrifice Kirk: "
                "Destroy target artifact or enchantment.", "3", "3", "RW"),
    "worf": raw("Worf, Honor-Bound Warrior", f"Legendary Creature {DASH} Klingon Warrior Officer", "{R/W}{R/W}", 2,
                WHILE + "double Worf's power until end of turn.\nTap two untapped artifacts and/or creatures you "
                "control: Put a +1/+1 counter on Worf. Activate only as a sorcery.", "1", "1", "RW"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}
OGRE = card_info(_card("Ogre", f"Creature {DASH} Ogre", "{2}{R}", 3, "R", "", [], "3", "3"))[0]
GIANT = card_info(_card("Giant", f"Creature {DASH} Giant", "{4}{R}", 5, "R", "", [], "5", "5"))[0]
WALL = card_info(_card("Wall", f"Creature {DASH} Wall", "{2}{W}", 3, "W", "", [], "0", "6"))[0]
ELF = card_info(_card("Elf", f"Creature {DASH} Elf", "{G}", 1, "G", "", [], "1", "1"))[0]
PEEK = card_info(_card("Test Peek", "Sorcery", "{1}{W}", 2, "W", "Draw a card."))[0]


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


def put(p, card, entered=0):
    c = bt.Creature(card, entered)
    c.gy, c.ctl = p.graveyard, p
    p.creatures.append(c)
    return c


class ParseTests(unittest.TestCase):
    def test_triggers(self):
        self.assertEqual(C["janeway"].attack_power, (8, (("counter_target", 1),)))
        self.assertEqual(C["tactical"].attack_power, (8, (("counter_self", 1), ("untap_self",))))
        self.assertEqual(C["una"].attack_power, (8, (("attacker_pump", 2, 0, ("first strike",)),)))
        self.assertEqual(C["laan"].attack_power, (8, (("no_block",),)))
        self.assertEqual(C["kirk"].attack_power, (8, (("impulse",),)))
        self.assertEqual(C["worf"].attack_power, (8, (("double_power",),)))
        self.assertEqual(C["captain"].combat_pump_power, (1, ("menace",), 8))
        self.assertEqual((OGRE.attack_power, OGRE.combat_pump_power), ((), ()))

    def test_coverage(self):
        for key, r in RAW.items():
            open_lines = [l for _c, _m, l in analyze_card(r)]
            self.assertFalse([l for l in open_lines if "total power 8" in l], key)


class TriggerTests(unittest.TestCase):
    def test_total_power(self):
        me, _opp = pair()
        put(me, OGRE), put(me, GIANT)
        self.assertEqual(bt.total_power(me), 8)

    def test_janeway_needs_eight(self):
        me, opp = pair()
        jane, ogre = put(me, C["janeway"]), put(me, OGRE)
        bt.attack_power_triggers(me, opp, [jane, ogre], 5, entry())
        self.assertEqual((jane.bonus, ogre.bonus), (0, 0))  # nur 6
        giant = put(me, GIANT)
        bt.attack_power_triggers(me, opp, [jane, ogre, giant], 5, entry())
        self.assertEqual(giant.bonus, 1)  # gefaehrlichster Angreifer

    def test_counts_creatures_at_home(self):
        me, opp = pair()
        jane, giant = put(me, C["janeway"]), put(me, GIANT)
        bt.attack_power_triggers(me, opp, [jane], 5, entry())  # 3 + 5 = 8, auch der Riese zu Hause
        self.assertEqual(jane.bonus, 1)

    def test_no_attack_no_trigger(self):
        me, opp = pair()
        jane = put(me, C["janeway"])
        giant = put(me, GIANT)
        bt.attack_power_triggers(me, opp, [], 5, entry())
        self.assertEqual((jane.bonus, giant.bonus), (0, 0))

    def test_tactical_officer_untaps(self):
        me, opp = pair()
        tac, giant = put(me, C["tactical"]), put(me, GIANT)
        put(me, ELF)  # 2 + 5 + 1 = 8
        tac.tapped = True
        bt.attack_power_triggers(me, opp, [tac, giant], 5, entry())
        self.assertEqual((tac.bonus, tac.tapped), (1, False))

    def test_una_pumps_strongest_attacker(self):
        me, opp = pair()
        una, ogre = put(me, C["una"]), put(me, OGRE)
        bt.attack_power_triggers(me, opp, [ogre], 5, entry())  # 4 + 3 = 7
        self.assertEqual(ogre.power, 3)
        giant = put(me, GIANT)
        bt.attack_power_triggers(me, opp, [ogre, giant], 5, entry())
        self.assertEqual((giant.power, giant.has("first strike"), una.power), (7, True, 4))

    def test_laan_blocker_cant_block(self):
        me, opp = pair()
        put(me, C["laan"])
        giant = put(me, GIANT)
        wall, elf = put(opp, WALL), put(opp, ELF)
        bt.attack_power_triggers(me, opp, [giant], 5, entry())
        self.assertFalse(bt.can_block(wall, giant))  # der Blocker, der den Riesen aufhaelt
        self.assertTrue(bt.can_block(elf, giant))
        bt.cleanup((me, opp))
        self.assertTrue(bt.can_block(wall, giant))

    def test_worf_doubles(self):
        me, opp = pair()
        worf, giant = put(me, C["worf"]), put(me, GIANT)
        worf.bonus = 2
        bt.attack_power_triggers(me, opp, [worf, giant], 5, entry())
        self.assertEqual((worf.power, worf.toughness), (6, 3))

    def test_kirk_card_playable_in_main_two(self):
        me, opp = pair(library=[PEEK, PLAINS, PLAINS])
        kirk, giant = put(me, C["kirk"]), put(me, GIANT)
        bt.attack_power_triggers(me, opp, [kirk, giant], 5, entry())
        self.assertEqual([c.name for c, _l in me.impulse], ["Test Peek"])
        me.open = [("W",), ("W",)]
        bt.combat_impulse_main2(me, opp, 5, entry())
        self.assertEqual((me.impulse, len(me.hand)), ([], 1))  # gewirkt, eine Karte gezogen
        self.assertIn(PEEK, me.graveyard)

    def test_kirk_land_if_no_land_this_turn(self):
        me, opp = pair(library=[PLAINS, PLAINS])
        kirk, giant = put(me, C["kirk"]), put(me, GIANT)
        bt.attack_power_triggers(me, opp, [kirk, giant], 5, entry())
        bt.combat_impulse_main2(me, opp, 5, entry())
        self.assertEqual(len(me.lands), 1)
        me.land_now = PLAINS
        bt.attack_power_triggers(me, opp, [kirk, giant], 5, entry())
        bt.combat_impulse_main2(me, opp, 5, entry())
        self.assertEqual(len(me.lands), 1)  # schon ein Land in diesem Zug

    def test_kirk_card_expires(self):
        me, opp = pair(library=[GIANT, PLAINS])
        kirk, giant = put(me, C["kirk"]), put(me, GIANT)
        bt.attack_power_triggers(me, opp, [kirk, giant], 5, entry())
        me.open = []
        bt.combat_impulse_main2(me, opp, 5, entry())
        bt.expire_impulse(me)
        self.assertEqual(me.impulse, [])

    def test_captain_menace_from_eight(self):
        me, opp = pair()
        put(me, C["captain"])
        ogre = put(me, OGRE)
        bt.combat_buffs(me, 5, entry())
        self.assertEqual((ogre.power, ogre.has("menace")), (4, False))  # 2 + 4 = 6
        bt.cleanup((me, opp))
        giant = put(me, GIANT)
        bt.combat_buffs(me, 5, entry())
        self.assertEqual((giant.power, giant.has("menace")), (6, True))  # 2 + 3 + 6 = 11


if __name__ == "__main__":
    unittest.main()
