"""FRA-Paket G (Spielentscheidungen des Nutzers): Aerid Konstrari {6} (vor dem Angriff fuer Lethal oder gegen einen
Blocker, sonst am Ende des gegnerischen Zugs fuer den Token), Yoshimaru {6} (Ende des gegnerischen Zugs; im Kampf fuer
Lethal, einen besseren Block oder gegen Lethal), Hapatra {2}{U} (Main 2: staerksten Angreifer enttappen), Teyo,
Diamondblade Mage (Kampftrick; Flash-Blocker mit Deathtouch und Marke auf sich selbst; sonst Ende des gegnerischen Zugs),
Teyo, Lightshield Expert und Liliana the Faultless (Hexproof als Antwort auf Removal), Jace, Reality Sculptor 0 (ab 25
Loyalty: Bibliothek des Gegners bis auf eine Karte ins Exil)."""
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import _card
from tests.test_package_fra_d import (ANOMALY, CRE, DASH, FOREST, ISLAND, OGRE, PLAINS, SWAMP, TITAN, entry, make,
                                      on_board, pair)
from tests.test_package_fra_e import BEAR, DOOM

AERID = make("Aerid Konstrari", f"Legendary Creature {DASH} Elder Sphinx", "{1}{R}{G}{G}", 4, "Flying\nWhen Aerid "
             "Konstrari enters or dies, create a Heartwood token.\n{6}: Create a Heartwood token. Then Aerid Konstrari "
             "gets +X/+0 until end of turn, where X is the number of artifacts you control.", "5", "4", ["Flying"],
             colors="RG")
YOSHI = make("Yoshimaru, Beloved Companion", f"Legendary Creature {DASH} Dog", "{2}{W}", 3, "If one or more +1/+1 "
             "counters would be put on a creature you control, that many plus one +1/+1 counters are put on it "
             "instead.\n{6}: Put a +1/+1 counter on target legendary creature.", "2", "2")
HAPATRA = make("Hapatra, the Desert Frost", f"Legendary Creature {DASH} Human Wizard", "{3}{U}", 4, "When Hapatra "
               "enters, for each opponent, tap up to one target creature that player controls. Put a stun counter on "
               "each of those creatures.\n{2}{U}: Untap target creature.", "4", "3", colors="U")
TEYO_D = make("Teyo, Diamondblade Mage", f"Legendary Creature {DASH} Human Warlock", "{3}{B}", 4, "Flash\nWhen Teyo "
              "enters, target permanent you control gains deathtouch until end of turn. Put a +1/+1 counter on it if "
              "it's a creature. Put a loyalty counter on it if it's a planeswalker.", "3", "1", ["Flash"], colors="B")
TEYO_L = make("Teyo, Lightshield Expert", f"Legendary Creature {DASH} Human Cleric", "{1}{W}", 2, "Flash\nWhen Teyo "
              "enters, target permanent you control gains hexproof until end of turn. Put a +1/+1 counter on it if "
              "it's a creature. Put a loyalty counter on it if it's a planeswalker.", "1", "1", ["Flash"])
LILIANA = make("Liliana the Faultless", f"Legendary Creature {DASH} Human Cleric", "{W}", 1, "Whenever another "
               "creature or planeswalker you control enters, you gain 1 life.\n{1}, {T}, Discard a card: Another "
               "target creature or planeswalker you control gains hexproof until end of turn.", "1", "1")
SCULPTOR = card_info(dict(_card("Jace, Reality Sculptor", f"Legendary Planeswalker {DASH} Jace", "{3}{U}{U}", 5, "U",
                                "+1: Empower Jace X, where X is the number of Islands you control.\n−3: Until your "
                                "next turn, whenever a creature attacks you or a planeswalker you control, it gets "
                                "-5/-0 until end of turn.\n0: Exile all but the bottom card of each opponent's "
                                "library. Activate only if there are twenty-five or more loyalty counters among "
                                "Jaces you control."), loyalty="4"))[0]
SKY_WALL = make("Sky Wall", CRE, "{3}{W}", 4, "Flying", "0", "6", ["Flying"])


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertTrue(AERID.aerid_pump and YOSHI.yoshi_counter and HAPATRA.hapatra_untap and LILIANA.liliana_hexproof)
        self.assertEqual((TEYO_D.etb_grant, TEYO_L.etb_grant), (("deathtouch",), ("hexproof",)))
        self.assertIn((0, (("library_exile", 25),)), SCULPTOR.pw_abilities)


class CoverageTests(unittest.TestCase):
    def test_teyo_lines_are_modelled(self):
        from components.coverage import analyze_card
        for name, kw, cost in (("Teyo, Diamondblade Mage", "deathtouch", "{3}{B}"),
                               ("Teyo, Lightshield Expert", "hexproof", "{1}{W}")):
            d = {"name": name, "type_line": f"Legendary Creature {DASH} Human", "mana_cost": cost, "cmc": 2.0,
                 "keywords": ["Flash"], "layout": "normal", "power": "1", "toughness": "1", "colors": ["W"],
                 "oracle_text": f"Flash\nWhen Teyo enters, target permanent you control gains {kw} until end of "
                                "turn. Put a +1/+1 counter on it if it's a creature. Put a loyalty counter on it if "
                                "it's a planeswalker."}
            self.assertEqual(analyze_card(d), [], name)


class AeridTests(unittest.TestCase):
    def test_pump_for_lethal(self):
        me, opp = pair()
        on_board(me, AERID)
        opp.life, me.lands = 6, [FOREST] * 6
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 6)  # 5 + 1 Artefakt (der neue Heartwood-Token)

    def test_pump_against_a_blocker(self):
        me, opp = pair()
        on_board(me, AERID)
        on_board(opp, SKY_WALL)
        me.lands = [FOREST] * 6
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertIn("Heartwood", [c.name for c in me.perms])

    def test_no_pump_without_benefit(self):
        me, opp = pair()
        on_board(me, AERID)
        me.lands = [FOREST] * 6
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertNotIn("Heartwood", [c.name for c in me.perms])

    def test_token_at_end_of_opponent_turn(self):
        me, opp = pair()
        on_board(me, AERID)
        me.open = [FOREST.land_colors] * 6
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual([c.name for c in me.perms], ["Heartwood"])


class YoshimaruTests(unittest.TestCase):
    def test_end_of_opponent_turn(self):
        me, opp = pair()
        on_board(me, YOSHI)
        legend = on_board(me, ANOMALY._replace(power=3))
        me.open = [PLAINS.land_colors] * 6
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual(legend.bonus, 2)  # eine Marke, durch Yoshimaru eine mehr

    def test_not_without_mana(self):
        me, opp = pair()
        on_board(me, YOSHI)
        me.open = [PLAINS.land_colors] * 5
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual(me.creatures[0].bonus, 0)

    def test_better_block(self):
        me, opp = pair()
        on_board(me, YOSHI)
        legend = on_board(me, make("Old Guard", f"Legendary Creature {DASH} Test", "{2}{W}", 3, "", "2", "2"))
        ogre = on_board(opp, OGRE)
        me.open = [PLAINS.land_colors] * 6
        bt.yoshimaru_combat(me, [(ogre, [legend])], opp, entry(), 6, attacking=False)
        self.assertEqual(legend.bonus, 2)

    def test_lethal_attack(self):
        me, opp = pair()
        on_board(me, YOSHI, entered=5)
        legend = on_board(me, make("Old Guard", f"Legendary Creature {DASH} Test", "{2}{W}", 3, "", "4", "4"))
        opp.life, me.open = 5, [PLAINS.land_colors] * 6
        bt.yoshimaru_combat(me, [(legend, [])], opp, entry(), 5, attacking=True)
        self.assertEqual(legend.bonus, 2)

    def test_no_use_without_effect(self):
        me, opp = pair()
        on_board(me, YOSHI)
        legend = on_board(me, make("Old Guard", f"Legendary Creature {DASH} Test", "{2}{W}", 3, "", "6", "6"))
        ogre = on_board(opp, OGRE)
        me.open = [PLAINS.land_colors] * 6
        bt.yoshimaru_combat(me, [(ogre, [legend])], opp, entry(), 6, attacking=False)
        self.assertEqual(legend.bonus, 0)


class HapatraTests(unittest.TestCase):
    def test_untaps_the_attacker_in_main2(self):
        me, opp = pair()
        on_board(me, HAPATRA, entered=5)
        ogre = on_board(me, OGRE)
        me.lands = [ISLAND] * 3
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertFalse(ogre.tapped)
        self.assertEqual(ogre.attacked, 5)


class TeyoDiamondbladeTests(unittest.TestCase):
    def test_flash_blocker_with_deathtouch_on_himself(self):
        me, opp = pair()
        titan = on_board(opp, TITAN)
        me.hand, me.open = [TEYO_D], [SWAMP.land_colors] * 4
        bt.respond_to_attack(me, opp, [titan], entry(), 6)
        teyo = next(c for c in me.creatures if c.card.name == TEYO_D.name)
        self.assertEqual((teyo.bonus, teyo.has("deathtouch")), (1, True))

    def test_combat_trick(self):
        me, opp = pair()
        ogre = on_board(me, OGRE)
        titan = on_board(opp, TITAN)
        me.hand, me.open = [TEYO_D], [SWAMP.land_colors] * 4
        bt.combat_tricks(me, [(ogre, [titan])], opp, entry(), 5, attacking=True)
        teyo = next(c for c in me.creatures if c.card.name == TEYO_D.name)
        self.assertEqual((ogre.bonus, ogre.has("deathtouch"), teyo.bonus), (1, True, 0))

    def test_end_of_turn_counter_on_the_most_dangerous(self):
        me, opp = pair()
        titan = on_board(me, TITAN)
        me.hand, me.open = [TEYO_D], [SWAMP.land_colors] * 4
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual(titan.bonus, 1)


class HexproofResponseTests(unittest.TestCase):
    def test_teyo_saves_a_big_creature(self):
        me, opp = pair()
        titan = on_board(me, TITAN)
        me.hand, me.open = [TEYO_L], [PLAINS.land_colors] * 2
        bt.cast_removal(DOOM, opp, me, entry(), 6, target=titan)
        self.assertFalse(titan.dead)
        self.assertEqual(titan.bonus, 1)

    def test_teyo_saves_the_most_dangerous_even_if_cheap(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        me.hand, me.open = [TEYO_L], [PLAINS.land_colors] * 2
        bt.cast_removal(DOOM, opp, me, entry(), 6, target=bear)
        self.assertFalse(bear.dead)

    def test_teyo_not_for_a_cheap_minor_creature(self):
        me, opp = pair()
        on_board(me, TITAN)
        bear = on_board(me, BEAR)
        me.hand, me.open = [TEYO_L], [PLAINS.land_colors] * 2
        bt.cast_removal(DOOM, opp, me, entry(), 6, target=bear)
        self.assertTrue(bear.dead)
        self.assertEqual(me.hand, [TEYO_L])

    def test_liliana_saves_with_a_surplus_land(self):
        me, opp = pair()
        lili = on_board(me, LILIANA)
        me.turn_start = 4  # Liliana liegt seit Beginn unseres Zugs (302.6)
        titan = on_board(me, TITAN)
        me.lands, me.hand, me.open = [PLAINS] * 6, [FOREST], [PLAINS.land_colors]
        bt.cast_removal(DOOM, opp, me, entry(), 6, target=titan)
        self.assertFalse(titan.dead)
        self.assertTrue(titan.has("hexproof"))
        self.assertEqual((lili.tapped, me.hand), (True, []))

    def test_liliana_not_without_surplus_card(self):
        me, opp = pair()
        on_board(me, LILIANA)
        me.turn_start = 4
        titan = on_board(me, TITAN)
        me.lands, me.hand, me.open = [PLAINS] * 2, [], [PLAINS.land_colors]
        bt.cast_removal(DOOM, opp, me, entry(), 6, target=titan)
        self.assertTrue(titan.dead)

    def test_liliana_not_for_cheap_creatures(self):
        me, opp = pair()
        on_board(me, LILIANA)
        me.turn_start = 4
        bear = on_board(me, BEAR)
        me.lands, me.hand, me.open = [PLAINS] * 6, [FOREST], [PLAINS.land_colors]
        bt.cast_removal(DOOM, opp, me, entry(), 6, target=bear)
        self.assertTrue(bear.dead)


class SculptorTests(unittest.TestCase):
    def test_zero_ability_from_25(self):
        me, opp = pair()
        w = bt.Walker(SCULPTOR, 0)
        w.loyalty = 5
        me.walkers = [w]
        me.jace.add(20)
        opts = bt.pw_options(me, opp, w, 5, "main1")
        self.assertEqual(opts[0][3], (("library_exile", 25),))
        bt.activate_pw(me, opp, w, (opts[0][2], opts[0][3]), 5, entry())
        self.assertEqual(len(opp.library), 1)

    def test_not_below_25(self):
        me, opp = pair()
        w = bt.Walker(SCULPTOR, 0)
        w.loyalty = 5
        me.walkers = [w]
        me.jace.add(19)
        opts = bt.pw_options(me, opp, w, 5, "main1")
        self.assertNotIn((("library_exile", 25),), [o[3] for o in opts])


if __name__ == "__main__":
    unittest.main()
