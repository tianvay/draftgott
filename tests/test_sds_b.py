"""Stardates (SDS, Bonusblatt in TRK-Boostern), Paket B (Nutzer 2026-11-22): Statik und Ausloeser - Sheoldred, the
Apocalypse, Torbran, Thane of Red Fell, Rishkar, Peema Renegade, Bristly Bill, Spine Sower, Mikaeus, the Lunarch,
Ertai Resurrected, Decree of Pain, Mogis, God of Slaughter, dazu Jhoira (historic, 700.6). Nur Kampfmodell.
Kartentexte aus SDS (Scryfall)."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from components.mana import cost_alternatives
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]
FOREST = card_info(_card("Forest", f"Basic Land {DASH} Forest", text="({T}: Add {G}.)", produced=["G"]))[0]

RAW = {
    "sheoldred": _card("Sheoldred, the Apocalypse", f"Legendary Creature {DASH} Phyrexian Praetor", "{2}{B}{B}", 4, "B",
                       "Deathtouch\nWhenever you draw a card, you gain 2 life.\nWhenever an opponent draws a card, they "
                       "lose 2 life.", ["Deathtouch"], "4", "5"),
    "torbran": _card("Torbran, Thane of Red Fell", f"Legendary Creature {DASH} Dwarf Noble", "{1}{R}{R}{R}", 4, "R",
                     "If a red source you control would deal damage to an opponent or a permanent an opponent controls, "
                     "it deals that much damage plus 2 instead.", [], "2", "4"),
    "rishkar": _card("Rishkar, Peema Renegade", f"Legendary Creature {DASH} Elf Druid", "{2}{G}", 3, "G",
                     "When Rishkar enters, put a +1/+1 counter on each of up to two target creatures.\nEach creature "
                     "you control with a counter on it has \"{T}: Add {G}.\"", [], "2", "2"),
    "bill": _card("Bristly Bill, Spine Sower", f"Legendary Creature {DASH} Plant Druid", "{1}{G}", 2, "G",
                  f"Landfall {DASH} Whenever a land you control enters, put a +1/+1 counter on target creature.\n"
                  "{3}{G}{G}: Double the number of +1/+1 counters on each creature you control.", ["Landfall"], "2",
                  "2"),
    "mikaeus": _card("Mikaeus, the Lunarch", f"Legendary Creature {DASH} Human Cleric", "{X}{W}", 1, "W",
                     "Mikaeus enters with X +1/+1 counters on it.\n{T}: Put a +1/+1 counter on Mikaeus.\n{T}, Remove a "
                     "+1/+1 counter from Mikaeus: Put a +1/+1 counter on each other creature you control.", [], "0",
                     "0"),
    "ertai": _card("Ertai Resurrected", f"Legendary Creature {DASH} Phyrexian Human Wizard", "{2}{U}{B}", 4, "UB",
                   f"Flash\nWhen Ertai Resurrected enters, choose up to one {DASH}\n• Counter target spell, activated "
                   "ability, or triggered ability. Its controller draws a card.\n• Destroy another target creature or "
                   "planeswalker. Its controller draws a card.", ["Flash"], "3", "2"),
    "decree": _card("Decree of Pain", "Sorcery", "{6}{B}{B}", 8, "B",
                    "Destroy all creatures. They can't be regenerated. Draw a card for each creature destroyed this "
                    "way.\nCycling {3}{B}{B} ({3}{B}{B}, Discard this card: Draw a card.)\nWhen you cycle this card, "
                    "all creatures get -2/-2 until end of turn.", ["Cycling"]),
    "mogis": _card("Mogis, God of Slaughter", f"Legendary Enchantment Creature {DASH} God", "{2}{B}{R}", 4, "BR",
                   "Indestructible\nAs long as your devotion to black and red is less than seven, Mogis isn't a "
                   "creature.\nAt the beginning of each opponent's upkeep, Mogis deals 2 damage to that player unless "
                   "they sacrifice a creature of their choice.", ["Indestructible"], "7", "5"),
    "jhoira": _card("Jhoira, Weatherlight Captain", f"Legendary Creature {DASH} Human Artificer", "{2}{U}{R}", 4, "UR",
                    "Whenever you cast a historic spell, draw a card. (Artifacts, legendaries, and Sagas are "
                    "historic.)", [], "3", "3"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}


def make(name, cost, cmc, text="", power=None, toughness=None, type_line=f"Creature {DASH} Test", colors="G"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, [], power, toughness))[0]


BEAR = make("Bear", "{1}{G}", 2, "", "2", "2")
OGRE = make("Ogre", "{2}{R}", 3, "", "3", "3", colors="R")
GIANT = make("Giant", "{4}{G}", 5, "", "4", "4")
SHOCK = make("Shock", "{R}", 1, "Shock deals 2 damage to any target.", type_line="Instant", colors="R")
DEMON = make("Blood Demon", "{B}{B}{R}{R}{R}", 5, "", "5", "5", colors="BR")
GOLEM = make("Golem", "{3}", 3, "", "3", "3", f"Artifact Creature {DASH} Golem", "")
HERO = make("Hero", "{2}{W}", 3, "", "3", "3", f"Legendary Creature {DASH} Human", "W")


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
        self.assertEqual((C["sheoldred"].draw_life, C["sheoldred"].opp_draw_loss), (2, 2))
        self.assertTrue(C["torbran"].red_plus_two)
        self.assertEqual(C["rishkar"].team_counter_mana, (("G",),))
        self.assertEqual(C["rishkar"].modes, ((("counter", 1, 2),),))
        self.assertEqual(C["bill"].landfall, (("target_counter", 1),))
        self.assertIn((("double", "all"),), [ab[4] for ab in C["bill"].abilities])
        self.assertIn((("uncounter", 1, "self"), ("counter", 1, "others")), [ab[4] for ab in C["mikaeus"].abilities])
        self.assertEqual(C["ertai"].removal, ("destroy", 0, (), False, "etb", False))  # Ziele nur beim Gegner
        self.assertTrue(C["ertai"].removal_draw and C["ertai"].countered_draw)
        self.assertEqual(C["ertai"].counter, ("any", (), 0))
        self.assertTrue(C["decree"].sweep_draw)
        self.assertEqual(C["decree"].cycling, cost_alternatives("{3}{B}{B}"))
        self.assertEqual(C["decree"].cycle_sweep, 2)
        self.assertEqual(C["mogis"].upkeep_punish, 2)
        self.assertEqual(C["mogis"].god_devotion, ("BR", 7))
        self.assertFalse(C["mogis"].is_creature)

    def test_coverage(self):
        for key in RAW:
            self.assertEqual(open_lines(key), [], key)


class SheoldredTests(unittest.TestCase):
    def test_own_draws_gain_life(self):
        me, _opp = pair()
        put(me, C["sheoldred"])
        bt._draw(me, 2)
        self.assertEqual(me.life, 24)

    def test_opponent_draws_lose_life(self):
        me, opp = pair()
        put(me, C["sheoldred"])
        bt._draw(opp)
        self.assertEqual((opp.life, me.life), (18, 20))

    def test_dead_sheoldred_does_nothing(self):
        me, opp = pair()
        put(me, C["sheoldred"]).dead = True
        bt._draw(opp)
        self.assertEqual(opp.life, 20)


class TorbranTests(unittest.TestCase):
    def test_red_creature_combat_damage(self):
        me, _opp = pair()
        put(me, C["torbran"])
        ogre, bear = put(me, OGRE), put(me, BEAR)
        self.assertEqual((ogre.dmg, bear.dmg), (5, 2))
        out = bt.resolve_combat([(ogre, [])])
        self.assertEqual(out["player"], 5)

    def test_red_blocker_hits_attacker(self):
        me, opp = pair()
        put(me, C["torbran"])
        ogre = put(me, OGRE)
        giant = put(opp, GIANT)
        bt.resolve_combat([(giant, [ogre])])
        self.assertTrue(giant.dead)  # 3 + 2 Schaden an der 4/4

    def test_red_spell_damage(self):
        me, opp = pair()
        put(me, C["torbran"])
        giant = put(opp, GIANT)
        bt.cast_removal(SHOCK, me, opp, entry(), 3, target=giant)
        self.assertTrue(giant.damage >= 4)

    def test_only_against_opponent(self):
        me, _opp = pair()
        put(me, C["torbran"])
        self.assertEqual(bt.red_bonus(me, SHOCK), 2)
        self.assertEqual(bt.red_bonus(me, SHOCK, foe=False), 0)
        self.assertEqual(bt.red_bonus(me, BEAR), 0)


class RishkarTests(unittest.TestCase):
    def test_creatures_with_counters_tap_for_green(self):
        me, _opp = pair()
        put(me, C["rishkar"])
        bear = put(me, BEAR)
        ogre = put(me, OGRE)
        bear.bonus = 1
        _pool, units = bt._mana(me, 3)
        self.assertEqual(units, [(("G",), 1)])
        ogre.stun = 1  # auch eine andere Marke zaehlt
        _pool, units = bt._mana(me, 3)
        self.assertIn((("G",), 2), units)

    def test_without_rishkar_nothing(self):
        me, _opp = pair()
        put(me, BEAR).bonus = 1
        self.assertEqual(bt._mana(me, 3)[1], [])


class BillTests(unittest.TestCase):
    def test_landfall_counter(self):
        me, opp = pair()
        put(me, C["bill"])
        giant = put(me, GIANT)
        bt.on_land(me, opp, FOREST, 3, entry())
        self.assertEqual(giant.bonus, 1)

    def test_double(self):
        me, _opp = pair()
        bill = put(me, C["bill"])
        a, b = put(me, BEAR), put(me, GIANT)
        a.bonus, b.bonus = 2, 1
        ab = next(ab for ab in C["bill"].abilities if ab[4] == (("double", "all"),))
        self.assertTrue(bt.apply_ability(me, bill, ab, None, entry()))
        self.assertEqual((a.bonus, b.bonus, bill.bonus), (4, 2, 0))

    def test_double_without_counters_does_nothing(self):
        me, _opp = pair()
        bill = put(me, C["bill"])
        ab = next(ab for ab in C["bill"].abilities if ab[4] == (("double", "all"),))
        self.assertFalse(bt.apply_ability(me, bill, ab, None, entry()))


class MikaeusTests(unittest.TestCase):
    def ability(self):
        return next(ab for ab in C["mikaeus"].abilities if ab[4][0][0] == "uncounter")

    def test_spread(self):
        me, _opp = pair()
        mik = put(me, C["mikaeus"])
        mik.bonus = 2
        bear, giant = put(me, BEAR), put(me, GIANT)
        self.assertTrue(bt.apply_ability(me, mik, self.ability(), None, entry()))
        self.assertEqual((mik.bonus, bear.bonus, giant.bonus), (1, 1, 1))

    def test_needs_counter(self):
        me, _opp = pair()
        me.turn_start = 3
        mik = put(me, C["mikaeus"])
        put(me, BEAR)
        sources = [ab for c, ab in bt.ability_sources(me, 3, True, True) if c is mik]
        self.assertNotIn(self.ability(), sources)
        mik.bonus = 1
        sources = [ab for c, ab in bt.ability_sources(me, 3, True, True) if c is mik]
        self.assertIn(self.ability(), sources)


class ErtaiTests(unittest.TestCase):
    def test_destroy_mode_controller_draws(self):
        me, opp = pair()
        ogre = put(opp, OGRE)
        bt._resolve(me, opp, C["ertai"], 3, entry())
        self.assertTrue(ogre.dead)
        self.assertEqual(len(opp.hand), 1)
        self.assertTrue(any(c.card.name == "Ertai Resurrected" for c in me.creatures))

    def test_counter_mode(self):
        me, opp = pair()
        me.hand = [C["ertai"]]
        me.open = [("U",), ("B",), ("U",), ("B",)]
        bear = put(opp, BEAR)
        self.assertTrue(bt.try_counter(opp, GIANT, 3, entry()))
        self.assertEqual(len(opp.hand), 1)  # der Zaubernde zieht
        self.assertEqual(me.hand, [])
        self.assertTrue(any(c.card.name == "Ertai Resurrected" for c in me.creatures))
        self.assertFalse(bear.dead)  # nur ein Modus
        self.assertNotIn(C["ertai"], me.graveyard)


class DecreeTests(unittest.TestCase):
    def test_hard_cast_draws_per_destroyed(self):
        me, opp = pair()
        put(opp, BEAR), put(opp, OGRE), put(me, GIANT)
        put(opp, C["mogis"]._replace(is_creature=True, power=7, toughness=5, kw=("indestructible",)))  # unzerstoerbar: zaehlt nicht
        bt.cast_removal(C["decree"], me, opp, entry(), 3)
        self.assertEqual(len(me.hand), 3)

    def test_cycle_sweep(self):
        me, opp = pair()
        me.hand = [C["decree"]]
        me.open = [("B",)] * 5
        b1, b2, giant = put(opp, BEAR), put(opp, BEAR), put(opp, GIANT)
        mine = put(me, GIANT)
        self.assertTrue(bt.decree_cycle(me, opp, 3, entry()))
        self.assertEqual([c.card.name for c in opp.creatures], ["Giant"])  # beide Baeren im Friedhof
        self.assertEqual(len(opp.graveyard), 2)
        self.assertFalse(giant.dead or mine.dead)
        self.assertEqual(giant.power, 2)  # -2/-2 bis Rundenende
        self.assertEqual((me.graveyard, len(me.hand)), ([C["decree"]], 1))  # abgeworfen, eine Karte gezogen

    def test_no_cycle_for_single_creature(self):
        me, opp = pair()
        me.hand = [C["decree"]]
        me.open = [("B",)] * 5
        put(opp, OGRE._replace(toughness=2))
        self.assertFalse(bt.decree_cycle(me, opp, 3, entry()))

    def test_no_cycle_when_we_lose_more(self):
        me, opp = pair()
        me.hand = [C["decree"]]
        me.open = [("B",)] * 5
        put(opp, BEAR)
        put(me, BEAR), put(me, BEAR._replace(name="Bear Two"))
        self.assertFalse(bt.decree_cycle(me, opp, 3, entry()))
        self.assertEqual(me.hand, [C["decree"]])


class MogisTests(unittest.TestCase):
    def test_upkeep_damage(self):
        me, opp = pair()
        opp.perms.append(C["mogis"])
        put(me, BEAR)
        bt.mogis_upkeep(me, opp, entry())
        self.assertEqual(me.life, 18)

    def test_sacrifice_against_lethal(self):
        me, opp = pair()
        opp.perms.append(C["mogis"])
        me.life = 2
        bear, giant = put(me, BEAR), put(me, GIANT)
        bt.mogis_upkeep(me, opp, entry())
        self.assertEqual((me.life, bear.dead, giant.dead), (2, True, False))

    def test_torbran_adds_two(self):
        me, opp = pair()
        opp.perms.append(C["mogis"])
        put(opp, C["torbran"])
        bt.mogis_upkeep(me, opp, entry())
        self.assertEqual(me.life, 16)

    def test_devotion_makes_creature(self):
        me, _opp = pair()
        me.perms.append(C["mogis"])
        demon = put(me, DEMON)
        bt.god_sync(me, 3, entry())
        gods = [c for c in me.creatures if c.card.name == "Mogis, God of Slaughter"]
        self.assertEqual((len(gods), C["mogis"] in me.perms), (1, False))
        self.assertEqual((gods[0].power, gods[0].toughness), (7, 5))
        demon.dead = True
        bt.god_sync(me, 4, entry())
        self.assertEqual(([c for c in me.creatures if c.card.name == "Mogis, God of Slaughter" and not c.dead],
                          any(x.name == "Mogis, God of Slaughter" for x in me.perms)), ([], True))


class JhoiraTests(unittest.TestCase):
    def test_historic(self):
        kind = C["jhoira"].cast_trig[0][0]
        self.assertTrue(bt.cast_matches(kind, HERO))
        self.assertTrue(bt.cast_matches(kind, GOLEM))
        self.assertFalse(bt.cast_matches(kind, BEAR))


if __name__ == "__main__":
    unittest.main()
