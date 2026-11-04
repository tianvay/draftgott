"""Star Trek (TRK), Paket R3 (Nutzer 2026-11-03): Kampfbeginn und Modi - D-7 Battle Cruiser (ab 3 Marken) und L'Rell
(2/1-Token mit Haste zu Kampfbeginn, im Endsegment geopfert; L'Rell opfert ihn vorher fuer Surveil), Captain James
T. Kirk (choose one, ohne Handkarten alle), Kobayashi Maru Scenario (nur kurz vor dem Sieg; Hail, Sensors,
Transport, dann verloren), Captain Benjamin Sisko (Officer je Dilemma; die Fuenffarben-Faehigkeit bewusst nicht),
The Naked Time (II: Marke und Haste fuer jede Kreatur, die in diesem Zug kommt; III: ein Land opfern). Nur
Kampfmodell. Kartentexte aus TRK."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]
MOUNTAIN = card_info(_card("Mountain", f"Basic Land {DASH} Mountain", text="({T}: Add {R}.)", produced=["R"]))[0]

RAW = {
    "d7": _card("D-7 Battle Cruiser", f"Artifact {DASH} Spacecraft", "{1}{R}", 2, "R", "Station (Tap another creature "
                "you control: Put charge counters equal to its power on this Spacecraft. Station only as a sorcery. "
                "It's an artifact creature at 8+.)\n3+ | At the beginning of combat on your turn, create a 2/1 red "
                "Klingon Warrior creature token with haste. Sacrifice it at the beginning of the next end step.\n8+ | "
                "Flying", [], "3", "3"),
    "lrell": _card("L'Rell, Fierce Visionary", f"Legendary Creature {DASH} Klingon Warrior", "{1}{B}{R}", 3, "BR",
                   "At the beginning of combat on your turn, create a 2/1 red Klingon Warrior creature token with "
                   "haste. Sacrifice it at the beginning of the next end step.\n{2}, Sacrifice another creature or "
                   "artifact: Surveil 1. (Look at the top card of your library. You may put it into your graveyard.)",
                   [], "1", "4"),
    "kirk": _card("Captain James T. Kirk", f"Legendary Creature {DASH} Human Officer", "{2}{R}", 3, "R", "Whenever "
                  "Captain Kirk enters or attacks, choose one. If you have no cards in hand, choose one or more "
                  "instead.\n• Discard a card, then draw a card.\n• Create a 1/1 red Officer creature token.\n• "
                  "Creatures you control get +1/+0 until end of turn.", [], "2", "2"),
    "kobayashi": _card("Kobayashi Maru Scenario", "Enchantment", "{1}{U}{U}", 3, "U", "At the beginning of your upkeep, "
                       f"choose one that hasn't been chosen {DASH}\n• Hail {DASH} Return up to one target creature an "
                       f"opponent controls with mana value 3 or less to its owner's hand.\n• Sensors {DASH} Draw two "
                       f"cards.\n• Transport {DASH} Create two 1/1 red Officer creature tokens.\n• Abandon Ship {DASH} "
                       "You lose the game."),
    "sisko": _card("Captain Benjamin Sisko", f"Legendary Creature {DASH} Human Officer", "{1}{W}", 2, "W", "At the "
                   "beginning of your end step, create a 1/1 red Officer creature token for each dilemma you've faced "
                   "this turn.\n{2}{W}{U}{B}{R}{G}, {T}: Exile the top five cards of your library. You may cast any "
                   "number of spells with mana value less than or equal to the number of Officers you control from "
                   "among those cards without paying their mana costs.", [], "2", "2"),
    "naked": _card("The Naked Time", f"Enchantment {DASH} Saga", "{1}{R}", 2, "R", "(As this Saga enters and after your "
                   f"draw step, add a lore counter. Sacrifice after III.)\nI {DASH} Search your library for a basic "
                   f"Mountain card, put it onto the battlefield tapped, then shuffle.\nII {DASH} Whenever a creature you "
                   "control enters this turn, put a +1/+1 counter on it and it gains haste until end of turn.\nIII "
                   f"{DASH} Sacrifice a land."),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}


def make(name, cost, cmc, text="", power=None, toughness=None, type_line=f"Creature {DASH} Test", colors="R"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, [], power, toughness))[0]


BEAR = make("Bear", "{1}{G}", 2, "", "2", "2", colors="G")
OGRE = make("Ogre", "{2}{R}", 3, "", "3", "3")
GIANT = make("Giant", "{4}{R}", 5, "", "5", "5")


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


def names(p):
    return sorted(c.card.name for c in p.creatures)


class ParseTests(unittest.TestCase):
    def test_fields(self):
        n, tok = C["d7"].station_combat_token
        self.assertEqual((n, tok.power, tok.toughness, tok.haste, tok.end_sacrifice), (3, 2, 1, True, True))
        self.assertEqual(C["lrell"].combat_token.creature_types, ("klingon", "warrior"))
        self.assertEqual(C["lrell"].sac_surveil[1], 1)
        self.assertEqual(len(C["kirk"].choices[1]), 3)
        self.assertEqual(C["kirk"].attack_choices, C["kirk"].choices)
        self.assertTrue(C["kirk"].modes_all_empty_hand)
        self.assertTrue(C["kirk"].choices[1][0].discard_first)
        self.assertTrue(C["kobayashi"].kobayashi)
        self.assertEqual(C["sisko"].end_dilemma_tokens.name, "Officer")
        chapters = {nums: atoms for nums, _sub, atoms in C["naked"].saga[1]}
        self.assertEqual((chapters[(2,)], chapters[(3,)]), ((("naked_turn",),), (("sac_land",),)))

    def test_coverage(self):
        for key in RAW:
            self.assertEqual(open_lines(key), [], key)  # Sisko: Fuenffarben-Faehigkeit in ON_PURPOSE


class CombatTokenTests(unittest.TestCase):
    def test_d7_from_three_counters(self):
        me, opp = pair()
        me.perms.append(C["d7"])
        bt.permanent_enters(me, opp, C["d7"], 1, entry())
        bt.add_charge(me, me.stations[0], 2)
        bt.combat_tokens(me, opp, 3, entry())
        self.assertEqual(me.creatures, [])
        bt.add_charge(me, me.stations[0], 1)
        bt.combat_tokens(me, opp, 3, entry())
        tok = me.creatures[0]
        self.assertTrue(bt.can_attack(tok, 3))
        self.assertTrue(tok.card.end_sacrifice)

    def test_lrell_sacrifices_for_surveil(self):
        me, opp = pair()
        put(me, C["lrell"])
        bt.combat_tokens(me, opp, 3, entry())
        self.assertEqual(len(me.creatures), 2)
        me.open = [("R",)] * 2
        e = entry()
        bt.lrell_surveil(me, e)
        self.assertEqual((len([c for c in me.creatures if not c.dead]), me.open), (1, []))
        self.assertTrue(any("Surveil" in ev for ev in e["events"]), e["events"])

    def test_lrell_keeps_real_creatures(self):
        me, _opp = pair()
        put(me, C["lrell"])
        put(me, BEAR)
        me.open = [("R",)] * 2
        bt.lrell_surveil(me, entry())
        self.assertFalse(any(c.dead for c in me.creatures))


class KirkTests(unittest.TestCase):
    def test_one_mode_with_cards_in_hand(self):
        me, opp = pair()
        put(me, C["kirk"], 3)
        me.hand = [PLAINS, PLAINS]
        bt.card_effects(me, opp, C["kirk"], 3, entry())
        self.assertEqual((len(me.creatures), len(me.hand), len(me.library)), (1, 2, 19))  # Loot: ab, dann ziehen

    def test_all_modes_without_hand(self):
        me, opp = pair()
        bear = put(me, BEAR)  # Team-Pump zaehlt nur fuer Kreaturen, die in diesem Zug angreifen koennen
        put(me, C["kirk"], 3)
        bt.card_effects(me, opp, C["kirk"], 3, entry())
        self.assertEqual((names(me), len(me.hand), bear.power), (["Bear", "Captain James T. Kirk", "Officer"], 1, 3))

    def test_attack_without_hand(self):
        me, opp = pair()
        kirk = put(me, C["kirk"])
        bt.attack_choice_triggers(me, opp, [kirk], 3, entry())
        self.assertEqual((len(me.creatures), len(me.hand), kirk.power), (2, 1, 3))


class KobayashiTests(unittest.TestCase):
    def test_modes_in_order_then_lose(self):
        me, opp = pair()
        me.perms.append(C["kobayashi"])
        bt.permanent_enters(me, opp, C["kobayashi"], 1, entry())
        put(opp, OGRE)
        bt.upkeep_triggers(me, opp, 3, entry())
        self.assertEqual((opp.creatures, opp.hand), ([], [OGRE]))
        bt.upkeep_triggers(me, opp, 5, entry())
        self.assertEqual(len(me.hand), 2)
        bt.upkeep_triggers(me, opp, 7, entry())
        self.assertEqual(names(me), ["Officer", "Officer"])
        self.assertGreater(me.life, 0)
        bt.upkeep_triggers(me, opp, 9, entry())
        self.assertLessEqual(me.life, 0)

    def test_sensors_first_without_target(self):
        me, opp = pair()
        me.perms.append(C["kobayashi"])
        bt.permanent_enters(me, opp, C["kobayashi"], 1, entry())
        put(opp, GIANT)  # Manawert 5: kein Ziel fuer Hail
        bt.upkeep_triggers(me, opp, 3, entry())
        self.assertEqual((len(me.hand), len(opp.creatures)), (2, 1))

    def test_only_cast_close_to_winning(self):
        me, opp = pair()
        me.hand = [C["kobayashi"]]
        put(me, OGRE)
        self.assertEqual(bt.main_phase_spells(me, opp), [])
        opp.life = 9
        self.assertEqual(bt.main_phase_spells(me, opp), [C["kobayashi"]])


class SiskoNakedTimeTests(unittest.TestCase):
    def test_sisko_officer_per_dilemma(self):
        me, opp = pair()
        put(me, C["sisko"])
        bt.face_dilemma(me, 3, entry())
        bt.face_dilemma(me, 3, entry())
        bt.end_step_triggers(me, opp, entry())
        self.assertEqual(names(me), ["Captain Benjamin Sisko", "Officer", "Officer"])

    def test_naked_time(self):
        me, opp = pair()
        st = {"card": C["naked"], "lore": 2, "exiled": [], "temp": None}
        bt.saga_atom(me, opp, st, ("naked_turn",), 3, entry())
        bear = put(me, BEAR, 3)
        bt.creature_enters(me, bear, 3, entry(), opp, cast=False)
        self.assertEqual((bear.bonus, bt.can_attack(bear, 3)), (1, True))
        me.lands = [MOUNTAIN, MOUNTAIN, PLAINS]
        bt.saga_atom(me, opp, st, ("sac_land",), 5, entry())
        self.assertEqual((sorted(l.name for l in me.lands), me.graveyard), (["Mountain", "Plains"], [MOUNTAIN]))


if __name__ == "__main__":
    unittest.main()
