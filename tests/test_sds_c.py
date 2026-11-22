"""Stardates (SDS, Bonusblatt in TRK-Boostern), Paket C (Nutzer 2026-11-22): legendaere Laender und Gate - Minamo,
School at Water's Edge, Shizo, Death's Storehouse, Phyrexian Tower, Talon Gates of Madara. Kampfmodell, der Filter von
Talon Gates auch im Goldfish. Kartentexte aus SDS (Scryfall)."""
import unittest

from components import battle as bt
from components import simulation as sim
from components.cards import card_info
from components.coverage import analyze_card
from components.mana import cost_alternatives
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]

RAW = {
    "minamo": _card("Minamo, School at Water's Edge", "Legendary Land", text="{T}: Add {U}.\n{U}, {T}: Untap target "
                    "legendary permanent.", produced=["U"]),
    "shizo": _card("Shizo, Death's Storehouse", "Legendary Land", text="{T}: Add {B}.\n{B}, {T}: Target legendary "
                   "creature gains fear until end of turn. (It can't be blocked except by artifact creatures and/or "
                   "black creatures.)", produced=["B"]),
    "tower": _card("Phyrexian Tower", "Legendary Land", text="{T}: Add {C}.\n{T}, Sacrifice a creature: Add {B}{B}.",
                   produced=["B", "C"]),
    "gates": _card("Talon Gates of Madara", f"Land {DASH} Gate", text="When this land enters, up to one target "
                   "creature phases out.\n{T}: Add {C}.\n{1}, {T}: Add one mana of any color.\n{4}: Put this card from "
                   "your hand onto the battlefield.", produced=["B", "C", "G", "R", "U", "W"]),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}


def make(name, cost, cmc, text="", power=None, toughness=None, type_line=f"Creature {DASH} Test", colors="G"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, [], power, toughness))[0]


BEAR = make("Bear", "{1}{G}", 2, "", "2", "2")
OGRE = make("Ogre", "{2}{R}", 3, "", "3", "3", colors="R")
ZOMBIE = make("Zombie", "{1}{B}", 2, "", "2", "2", colors="B")
GOLEM = make("Golem", "{3}", 3, "", "3", "3", f"Artifact Creature {DASH} Golem", "")
HERO = make("Hero", "{2}{W}", 3, "", "3", "3", f"Legendary Creature {DASH} Human", "W")
THOPTER = make("Thopter", "", 0, "", "1", "1", f"Artifact Creature {DASH} Thopter", "")._replace(is_token=True)
TWIN = make("Twin Spell", "{W}{U}", 2, "Draw a card.", type_line="Sorcery", colors="WU")
DARK = make("Dark Ritualist", "{B}{B}{B}", 3, "", "3", "3", colors="B")


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


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertEqual((C["minamo"].land_colors, C["minamo"].untap_legendary), (("U",), cost_alternatives("{U}")))
        self.assertEqual((C["shizo"].land_colors, C["shizo"].fear_legendary), (("B",), cost_alternatives("{B}")))
        self.assertEqual((C["tower"].land_colors, C["tower"].tower_sac_mana), (("C",), (("B",), ("B",))))
        self.assertEqual(C["gates"].land_colors, ("C",))  # frei nur {C}, Farbe nur ueber den Filter
        self.assertTrue(C["gates"].filter_any and C["gates"].etb_phase_out)
        self.assertEqual(C["gates"].hand_land, cost_alternatives("{4}"))

    def test_coverage(self):
        for key, raw in RAW.items():
            self.assertEqual([l for _c, _m, l in analyze_card(raw)], [], key)


class FearTests(unittest.TestCase):
    def test_fear_blocks(self):
        me, opp = pair()
        hero = put(me, HERO)
        hero.extra.add("fear")
        self.assertFalse(bt.can_block(put(opp, BEAR), hero))
        self.assertTrue(bt.can_block(put(opp, ZOMBIE), hero))
        self.assertTrue(bt.can_block(put(opp, GOLEM), hero))

    def test_shizo_before_attack(self):
        me, opp = pair()
        me.turn_start = 3
        hero = put(me, HERO)
        put(opp, BEAR)
        me.lands, me.open = [C["shizo"]], [("B",), ("B",)]
        bt.shizo_fear(me, opp, 3, entry())
        self.assertTrue(hero.has("fear"))
        self.assertEqual(me.open, [])

    def test_shizo_not_against_black_blocker(self):
        me, opp = pair()
        me.turn_start = 3
        hero = put(me, HERO)
        put(opp, ZOMBIE)
        me.lands, me.open = [C["shizo"]], [("B",), ("B",)]
        bt.shizo_fear(me, opp, 3, entry())
        self.assertFalse(hero.has("fear"))
        self.assertEqual(len(me.open), 2)

    def test_shizo_needs_legendary(self):
        me, opp = pair()
        me.turn_start = 3
        ogre = put(me, OGRE)
        put(opp, BEAR)
        me.lands, me.open = [C["shizo"]], [("B",), ("B",)]
        bt.shizo_fear(me, opp, 3, entry())
        self.assertFalse(ogre.has("fear"))


class MinamoTests(unittest.TestCase):
    def test_untap_attacker_as_blocker(self):
        me, opp = pair()
        hero = put(me, HERO)
        hero.tapped = True
        put(opp, OGRE)
        me.lands, me.open = [C["minamo"]], [("U",), ("U",)]
        bt.minamo_untap(me, opp, entry())
        self.assertFalse(hero.tapped)
        self.assertEqual(me.open, [])

    def test_no_untap_without_threat(self):
        me, opp = pair()
        hero = put(me, HERO)
        hero.tapped = True
        me.lands, me.open = [C["minamo"]], [("U",), ("U",)]
        bt.minamo_untap(me, opp, entry())
        self.assertTrue(hero.tapped)


class GatesTests(unittest.TestCase):
    def test_etb_phases_out_best_blocker(self):
        me, opp = pair()
        bear, ogre = put(opp, BEAR), put(opp, OGRE)
        bt.on_land(me, opp, C["gates"], 3, entry())
        self.assertEqual(opp.creatures, [bear])
        self.assertEqual(opp.phased_single, [ogre])
        bt.phase_in(opp, entry())  # Untap des Kontrolleurs (702.26a)
        self.assertIn(ogre, opp.creatures)
        self.assertEqual((opp.phased_single, ogre.entered), ([], 0))

    def test_phases_in_during_own_turn(self):
        me, opp = pair()
        ogre = put(opp, OGRE)
        opp.creatures.remove(ogre)
        opp.phased_single.append(ogre)
        bt.take_turn(opp, me, 5, 3, skip_draw=True)
        self.assertIn(ogre, opp.creatures)
        self.assertEqual(opp.phased_single, [])

    def test_from_hand_at_end_of_opponents_turn(self):
        me, opp = pair()
        ogre = put(opp, OGRE)
        me.hand, me.open = [C["gates"]], [("W",)] * 4
        bt.gates_from_hand(me, opp, 4, entry())
        self.assertEqual((me.hand, me.lands, me.open), ([], [C["gates"]], []))
        self.assertNotIn(ogre, opp.creatures)

    def test_filter_only_when_it_helps(self):
        pool = [("W",), ("C",), ("B",)]
        better = sim.filter_pool([TWIN], pool, 1, False, True)
        self.assertEqual(sorted(better), sorted([("W",), sim.ANY_COLOR]))
        self.assertIsNone(sim.filter_pool([TWIN], [("W",), ("C",), ("U",)], 1, False, True))


class TowerTests(unittest.TestCase):
    def test_sacrifices_small_token_for_more(self):
        me, _opp = pair()
        me.lands = [C["tower"]]
        thopter = put(me, THOPTER)
        pool = bt.tower_mana(me, [DARK], [("B",), ("C",)], False, entry())
        self.assertEqual(sorted(pool), [("B",), ("B",), ("B",)])
        self.assertNotIn(thopter, [c for c in me.creatures if not c.dead])

    def test_no_real_creature_sacrificed(self):
        me, _opp = pair()
        me.lands = [C["tower"]]
        bear = put(me, BEAR)
        pool = bt.tower_mana(me, [DARK], [("B",), ("C",)], False, entry())
        self.assertEqual(pool, [("B",), ("C",)])
        self.assertFalse(bear.dead)


if __name__ == "__main__":
    unittest.main()
