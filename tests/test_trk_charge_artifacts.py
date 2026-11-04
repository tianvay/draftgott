"""Star Trek (TRK), Paket R6 (Nutzer 2026-11-05): Charge-Marken und Artefakte - Geordi La Forge (Charge-Marken doppelt),
Zefram Cochrane (Raumschiffe mit zwei Marken mehr, einmal je Zug ein Artefakt von oben), Romulan Bird-of-Prey,
U.S.S. Enterprise-D, Warp Core, Isolinear Processor, Combadge, Lieutenant Commander Data (erst Stun-Marken, dann
eigene Marken, Data bleibt mindestens 3/3), Dathon (Mission, Peace, Saga), Seven of Nine (7/9); Gwyndalas
Kopier-Faehigkeit bewusst nicht. Nur Kampfmodell. Kartentexte aus TRK."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from components.mana import cost_alternatives
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]
STATION = ("Station (Tap another creature you control: Put charge counters equal to its power on this Spacecraft. Station "
           "only as a sorcery. It's an artifact creature at 8+.)")

RAW = {
    "geordi": _card("Lt. Cmdr. Geordi La Forge", f"Legendary Creature {DASH} Human Artificer", "{2}{U}", 3, "U", "If you "
                    "would put one or more charge counters on an artifact you control, put twice that many charge "
                    "counters on that artifact instead.", [], "3", "2"),
    "zefram": _card("Zefram Cochrane, Warp Pioneer", f"Legendary Creature {DASH} Human Pilot", "{2}{U}", 3, "U", "You may "
                    "look at the top card of your library any time.\nOnce during each of your turns, you may cast an "
                    "artifact spell from the top of your library.\nSpacecraft you control enter with two additional "
                    "charge counters on them.", [], "2", "3"),
    "bird": _card("Romulan Bird-of-Prey", f"Artifact {DASH} Spacecraft", "{1}{U}", 2, "U", f"Cloaking Device {DASH} As "
                  "long as this Spacecraft isn't a creature, it has hexproof.\nWhenever you cast a noncreature spell, if "
                  f"this Spacecraft isn't a creature, put two charge counters on it.\n{STATION}\n8+ | Flying", [], "4",
                  "4"),
    "enterprise": _card("U.S.S. Enterprise-D, Galaxy-Class", f"Legendary Artifact {DASH} Spacecraft", "{3}", 3, "",
                        "Whenever one or more charge counters are put on U.S.S. Enterprise-D for the first time each "
                        "turn, exile the top card of your library. You may play that card this turn.\n"
                        + STATION.replace("8+", "7+") + "\n7+ | Flying, vigilance", [], "4", "5"),
    "warpcore": _card("Warp Core", "Artifact", "{2}", 2, "", "When this artifact enters, you may search your library for a "
                      "basic land card, reveal it, put it into your hand, then shuffle.\n{1}, {T}: Put two charge "
                      "counters on target Spacecraft. Activate only as a sorcery."),
    "isolinear": _card("Isolinear Processor", "Artifact", "{2}", 2, "", "{T}: Add {C}. Spend this mana only to cast an "
                       "artifact spell or activate an ability of an artifact source.\n{2}, {T}: Draw a card, then "
                       "discard a card."),
    "combadge": _card("Combadge", f"Artifact {DASH} Communicator Equipment", "{3}", 3, "", "When you cast this spell, copy "
                      "it. (The copy becomes a token.)\nEquipped creature has \"Whenever this creature attacks while you "
                      "control another creature with a Communicator attached to it, this creature can't be blocked this "
                      "turn.\"\nEquip {2} ({2}: Attach to target creature you control. Equip only as a sorcery.)",
                      ["Equip"]),
    "data": _card("Lieutenant Commander Data", f"Legendary Artifact Creature {DASH} Android Scientist", "{2}{U}", 3, "U",
                  "Whenever a player casts a noncreature spell, put a +1/+1 counter on Lieutenant Commander Data.\n{1}, "
                  "Remove three counters from among creatures you control: Draw a card.", [], "2", "2"),
    "dathon": _card("Dathon, His Heart Open", f"Legendary Creature {DASH} Tamarian Officer", "{G}{U}{R}", 3, "GUR",
                    "Whenever you cast an enchantment spell, draw a card. If it's a Saga spell, Dathon deals 2 damage "
                    "to each opponent.\n{2}: Choose a counter on target enchantment you control. Put another counter of "
                    "that kind on it. Activate only as a sorcery.", [], "3", "3"),
    "seven": _card("Seven of Nine, Unassimilated", f"Legendary Artifact Creature {DASH} Human Officer", "{1}{U}", 2, "U",
                   "At the beginning of your first main phase, draw a card. Then discard a card unless you control five "
                   "or more differently named lands.\n{6}{U}: Seven of Nine's base power and toughness become 7/9. "
                   "Activate only if you control seven or more differently named lands.", [], "0", "4"),
    "gwyndala": _card("Gwyndala, the Progeny", f"Legendary Creature {DASH} Vau-N'Akat Advisor", "{1}{U}", 2, "U", "When "
                      "Gwyndala enters, create a colorless Equipment artifact token named Neuroflux Heirloom with "
                      "\"Equipped creature gets +1/+1\" and equip {2}. Attach it to Gwyndala.\n{2}: Each Equipment token "
                      "you control becomes a copy of target Equipment you control until end of turn.", [], "1", "1"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}


def make(name, cost, cmc, text="", power=None, toughness=None, type_line=f"Creature {DASH} Test", colors="U"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, [], power, toughness))[0]


BEAR = make("Bear", "{1}{G}", 2, "", "2", "2", colors="G")
OGRE = make("Ogre", "{2}{R}", 3, "", "3", "3", colors="R")
SHIP = make("Test Cruiser", "{4}", 4, STATION + "\n8+ | Flying", "5", "5", f"Artifact {DASH} Spacecraft", "")
SPELL = make("Insight", "{1}{U}", 2, "Draw a card.", type_line="Sorcery")
RELIC = make("Relic", "{3}", 3, "{T}: You gain 1 life.", type_line="Artifact", colors="")
MISSION = card_info(_card("Support Mission", "Enchantment", "{2}{G}", 3, "G", "Whenever a creature you control enters, put "
                          "a quest counter on this enchantment. Put a +1/+1 counter on that creature. If this "
                          "enchantment has five or more quest counters on it, instead put two +1/+1 counters on "
                          "that creature."))[0]
ISLANDS = [card_info(_card(f"Isle {i}", f"Land {DASH} Island", text="({T}: Add {U}.)", produced=["U"]))[0]
           for i in range(7)]


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


def ship_in_play(p, opp, card=SHIP):
    p.perms.append(card)
    bt.permanent_enters(p, opp, card, 1, entry())
    return p.stations[-1]


def open_lines(key):
    return [l for _c, _m, l in analyze_card(RAW[key])]


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertTrue(C["geordi"].charge_double)
        self.assertTrue(C["zefram"].zefram_top)
        self.assertEqual(C["zefram"].zefram_charge, 2)
        self.assertTrue(C["bird"].cloak_hexproof)
        self.assertEqual(C["bird"].cast_charge, 2)
        self.assertTrue(C["enterprise"].charge_impulse)
        self.assertEqual(C["warpcore"].warp_charge, (cost_alternatives("{1}"), 2))
        self.assertEqual(C["isolinear"].artifact_mana, (("C",),))
        self.assertEqual(C["isolinear"].draw_abilities, ((cost_alternatives("{2}"), True, "loot"),))
        self.assertTrue(C["combadge"].cast_copy)
        self.assertTrue(C["combadge"].communicator_unblock)
        self.assertEqual(C["combadge"].equip[0], cost_alternatives("{2}"))
        self.assertTrue(C["data"].data_counter)
        self.assertEqual(C["data"].data_draw, (cost_alternatives("{1}"), 3))
        self.assertEqual(C["dathon"].dathon_counter, cost_alternatives("{2}"))
        self.assertEqual(C["seven"].seven_79, cost_alternatives("{6}{U}"))

    def test_coverage(self):
        for key in RAW:
            self.assertEqual(open_lines(key), [], key)  # Gwyndala: Kopier-Faehigkeit in ON_PURPOSE


class ChargeTests(unittest.TestCase):
    def test_geordi_and_zefram(self):
        me, opp = pair()
        put(me, C["geordi"])
        put(me, C["zefram"])
        st = ship_in_play(me, opp)
        self.assertEqual(st["charge"], 4)  # Zefram 2, Geordi verdoppelt
        bt.add_charge(me, st, 3)
        self.assertEqual(st["charge"], 10)

    def test_bird_of_prey(self):
        me, opp = pair()
        st = ship_in_play(me, opp, C["bird"])
        bt.on_cast(me, SPELL, 3, entry())
        bt.on_cast(me, OGRE, 3, entry())
        self.assertEqual(st["charge"], 2)
        relic_targets = [t for _r, _k, t in bt.noncreature_targets(opp, me, "artifact_enchantment")]
        self.assertEqual(relic_targets, [])  # Cloaking Device

    def test_enterprise_impulse_once_per_turn(self):
        me, opp = pair()
        me.library = [OGRE, BEAR, PLAINS]
        st = ship_in_play(me, opp, C["enterprise"])
        bt.add_charge(me, st, 2)
        bt.add_charge(me, st, 2)
        self.assertEqual([c for c, _l in me.impulse], [OGRE])
        me.now = 5
        bt.add_charge(me, st, 1)
        self.assertEqual([c for c, _l in me.impulse], [OGRE, BEAR])

    def test_warp_core(self):
        me, opp = pair()
        me.perms.append(C["warpcore"])
        st = ship_in_play(me, opp)
        me.open = [("U",)] * 3
        bt.warp_core_phase(me, 3, entry())
        bt.warp_core_phase(me, 3, entry())  # einmal je Zug ({T})
        self.assertEqual((st["charge"], len(me.open)), (2, 2))


class ArtifactTests(unittest.TestCase):
    def test_isolinear_loot(self):
        me, _opp = pair()
        me.perms.append(C["isolinear"])
        me.hand, me.open = [PLAINS], [("U",)] * 2
        bt.draw_abilities(me, entry())
        self.assertEqual((len(me.hand), len(me.library), me.open), (1, 19, []))

    def test_combadge_copy_and_unblockable(self):
        me, opp = pair()
        bt.on_cast(me, C["combadge"], 3, entry())
        tokens = [x for x in me.perms if x.is_token and x.communicator_unblock]
        self.assertEqual(len(tokens), 1)
        me.perms.append(C["combadge"])
        a, b = put(me, OGRE), put(me, BEAR)
        me.open = [("U",)] * 4
        bt.equip_gear(me, 3, entry())
        self.assertEqual((len(a.gear), len(b.gear)), (1, 1))
        bt.attack_keywords(me, [a], None, entry())
        self.assertTrue(a.has("unblockable"))

    def test_data(self):
        me, opp = pair()
        data = put(me, C["data"])
        bt.on_cast(me, SPELL, 3, entry())
        bt.on_cast(opp, SPELL, 3, entry())
        bt.on_cast(opp, OGRE, 3, entry())
        self.assertEqual(data.bonus, 2)
        bear = put(me, BEAR)
        bear.stun = 2
        me.open = [("U",)]
        bt.data_draw(me, entry())
        self.assertEqual((len(me.hand), bear.stun, data.bonus), (1, 0, 1))  # 2 Stun + 1 von Data, Data bleibt 3/3

    def test_data_keeps_three(self):
        me, _opp = pair()
        data = put(me, C["data"])
        data.bonus = 3
        me.open = [("U",)] * 2
        bt.data_draw(me, entry())
        self.assertEqual((len(me.hand), data.bonus), (0, 3))

    def test_dathon_priorities(self):
        me, opp = pair()
        put(me, C["dathon"])
        me.perms.append(MISSION)
        bt.permanent_enters(me, opp, MISSION, 1, entry())
        me.open = [("U",)] * 2
        bt.dathon_counters(me, opp, 3, entry())
        self.assertEqual(me.missions[0]["quest"], 0)  # noch keine Quest-Marke: keine passende Marke
        me.missions[0]["quest"] = 1
        bt.dathon_counters(me, opp, 3, entry())
        self.assertEqual((me.missions[0]["quest"], me.open), (2, []))

    def test_seven_of_nine(self):
        me, opp = pair()
        seven = put(me, C["seven"])
        me.lands = list(ISLANDS)
        me.open = [("U",)] * 7
        bt.seven_upgrade(me, 3, entry())
        self.assertEqual((seven.power, seven.toughness, seven.base_card), (7, 9, C["seven"]))

    def test_seven_needs_seven_names(self):
        me, _opp = pair()
        seven = put(me, C["seven"])
        me.lands = list(ISLANDS[:6]) + [ISLANDS[0]]
        me.open = [("U",)] * 7
        bt.seven_upgrade(me, 3, entry())
        self.assertEqual((seven.power, len(me.open)), (0, 7))


if __name__ == "__main__":
    unittest.main()
