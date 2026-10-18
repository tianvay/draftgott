"""Kampfmodell Paket M, Teil 3: Icy Reception (-5/-0 als Kampftrick), Cryotheory Adept (Stun aus dem Friedhof),
Blazing Crescendo (Karte aus dem Exil bis Ende des naechsten Zugs spielbar), Lyra, Tolarian Archangel (Engel nach 3
gezogenen Karten, Ziehen bei Kampfschaden) und Warrior's Blades (Ausruestung)."""
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS = W["Plains"]
U = ("U",)


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="U"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


ISLAND, MOUNTAIN = land("Island", "U"), land("Mountain", "R")
BEAR = W["Test Bear"]
TITAN = make("Titan", CRE, "{4}{G}", 5, "", "5", "5", colors="G")
OGRE = make("Ogre", CRE, "{2}{R}", 3, "", "3", "3", colors="R")
BIRD = make("Bird", CRE, "{1}{W}", 2, "Flying", "1", "1", ["Flying"], "W")
DRAW3 = make("Big Study", "Sorcery", "{2}{U}", 3, "Draw three cards.")
DRAW2 = make("Study", "Sorcery", "{1}{U}", 2, "Draw two cards.")

ICY = make("Icy Reception", "Instant", "{1}{U}", 2, "Choose one —\n• Counter target creature or legendary spell unless "
           "its controller pays {3}.\n• Target creature gets -5/-0 until end of turn.")
CRYO = make("Cryotheory Adept", f"Creature {DASH} Human Wizard", "{1}{U}", 2, "Prowess (Whenever you cast a "
            "noncreature spell, this creature gets +1/+1 until end of turn.)\n{3}{U}, Exile this card from your "
            "graveyard: Tap target creature and put a stun counter on it. Activate only as a sorcery. (If a permanent "
            "with a stun counter would become untapped, remove one from it instead.)", "1", "2", ["Prowess"])
BLAZING = make("Blazing Crescendo", "Instant", "{1}{R}", 2, "Target creature gets +3/+1 until end of turn.\nExile the "
               "top card of your library. Until the end of your next turn, you may play that card.", colors="R")
LYRA = make("Lyra, Tolarian Archangel", f"Legendary Creature {DASH} Angel Wizard", "{1}{U}{U}", 3,
            "Flying\nAt the beginning of each end step, if you've drawn three or more cards this turn, create a 3/3 "
            "blue Angel creature token with flying.\n{3}{U}{U}: Until end of turn, whenever Lyra deals combat damage "
            "to a player, draw two cards.", "2", "2", ["Flying"])
BLADES = make("Warrior's Blades", f"Artifact {DASH} Equipment", "{2}{R}{W}", 4, "When this Equipment enters, it deals "
              "3 damage to any target and you gain 3 life.\nEquipped creature gets +2/+1.\nEquip {3}. This ability "
              "costs {1} less to activate for each +1/+1 counter on the creature it targets.", colors="R")


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


def on_board(p, card, entered=0):
    c = bt.Creature(card, entered)
    c.gy, c.ctl = p.graveyard, p
    p.creatures.append(c)
    return c


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertEqual(ICY.choices[1][1].debuff, 5)
        self.assertEqual(CRYO.gy_ability, (((3, (("U", 1),)),), (("stun", 1),)))
        self.assertEqual(BLAZING.impulse, 1)
        self.assertEqual(BLAZING.modes, ((("pump", 3),),))
        self.assertTrue(LYRA.draw3_token)
        self.assertEqual(LYRA.draw3_token.name, "Angel")
        self.assertEqual(LYRA.combat_draw_ability, (((3, (("U", 2),)),), 2))
        self.assertEqual(BLADES.equip, (((3, ()),), 2, 1, True))
        self.assertEqual(BLADES.etb_life, 3)


class IcyTests(unittest.TestCase):
    def _attack(self, life, ours=(), attacker=TITAN, mana=2):
        me, opp = pair()
        mine = [on_board(me, c) for c in ours]
        on_board(opp, attacker)
        me.life, me.hand, me.open = life, [ICY], [U] * mana
        bt.take_turn(opp, me, 6, 3, skip_draw=True)
        return me, mine

    def test_saves_a_chump_blocker(self):
        me, (bear,) = self._attack(5, [BEAR])
        self.assertEqual((bear in me.creatures, me.life, ICY in me.graveyard), (True, 5, True))

    def test_prevents_lethal(self):
        me, _ = self._attack(4)
        self.assertEqual(me.life, 4)

    def test_prevents_four_or_more(self):
        me, _ = self._attack(20)
        self.assertEqual(me.life, 20)

    def test_prevents_lethal_below_four(self):
        me, _ = self._attack(3, attacker=OGRE)
        self.assertEqual(me.life, 3)

    def test_not_for_small_damage(self):
        me, _ = self._attack(20, attacker=BEAR)
        self.assertEqual((me.life, me.hand), (18, [ICY]))

    def test_as_attacker_on_a_blocker(self):
        me, opp = pair()
        bear, ogre = on_board(me, BEAR), on_board(opp, OGRE)
        me.hand, me.open = [ICY], [U] * 2
        bt.debuff_tricks(me, [(bear, [ogre])], opp, entry(), 5, attacking=True)
        self.assertEqual((ogre.power, me.hand), (-2, []))
        self.assertEqual(bt.outcome(bear, [ogre]), (False, [False]))

    def test_not_when_a_second_blocker_still_kills(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        blockers = [on_board(opp, OGRE), on_board(opp, OGRE)]
        me.hand, me.open = [ICY], [U] * 2
        bt.debuff_tricks(me, [(bear, blockers)], opp, entry(), 5, attacking=True)
        self.assertEqual(me.hand, [ICY])


class CryoTests(unittest.TestCase):
    def test_stuns_the_blocker(self):
        me, opp = pair()
        on_board(me, BEAR)
        ogre = on_board(opp, OGRE)
        me.graveyard[:] = [CRYO]
        me.lands = [ISLAND] * 4
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["damage"], ogre.tapped, ogre.stun, CRYO in me.graveyard), (2, True, 1, False))
        bt.take_turn(opp, me, 6, 3, skip_draw=True)  # Untap: Marke weg, bleibt getappt
        self.assertEqual((ogre.tapped, ogre.stun), (True, 0))
        bt.take_turn(opp, me, 8, 4, skip_draw=True)
        self.assertFalse(ogre.tapped and ogre.stun)

    def test_not_without_a_relevant_creature(self):
        me, opp = pair()
        on_board(opp, BEAR).tapped = True
        me.graveyard[:] = [CRYO]
        me.lands = [ISLAND] * 4
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertIn(CRYO, me.graveyard)

    def test_big_tapped_creature_is_stunned(self):
        me, opp = pair()
        ogre = on_board(opp, OGRE)
        ogre.tapped = True
        me.graveyard[:] = [CRYO]
        me.lands = [ISLAND] * 4
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(ogre.stun, 1)


class BlazingTests(unittest.TestCase):
    def test_exiled_card_cast_next_turn(self):
        me, opp = pair(library=[OGRE] + [PLAINS] * 10)
        on_board(me, BEAR)
        bt._resolve(me, opp, BLAZING, 3, entry())
        self.assertEqual(([c for c, _x in me.impulse], OGRE in me.library), ([OGRE], False))
        me.lands = [MOUNTAIN] * 3
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["main2"], me.impulse), (["Ogre"], []))

    def test_cast_in_our_turn_lasts_through_the_next(self):
        me, opp = pair(library=[OGRE] + [PLAINS] * 10)
        on_board(me, BEAR)
        me.own_turns = 1
        bt._resolve(me, opp, BLAZING, 3, entry())
        bt.expire_impulse(me)  # Ende dieses Zugs: noch spielbar
        self.assertEqual(len(me.impulse), 1)
        me.own_turns = 2
        bt.expire_impulse(me)  # Ende des naechsten Zugs: verfallen
        self.assertEqual(me.impulse, [])

    def test_played_cards_leave_the_exile(self):
        me, opp = pair()
        cub = make("Red Cub", CRE, "{R}", 1, "", "1", "1", colors="R")
        me.impulse = [(MOUNTAIN, 9), (cub, 9)]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(me.impulse, [])
        self.assertIn(MOUNTAIN, me.lands)

    def test_exiled_land_as_land_drop(self):
        me, opp = pair(library=[MOUNTAIN] + [PLAINS] * 10)
        on_board(me, BEAR)
        bt._resolve(me, opp, BLAZING, 3, entry())
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["land"], me.impulse, MOUNTAIN in me.lands), ("Mountain", [], True))

    def test_expires_after_the_next_turn(self):
        me, opp = pair(library=[TITAN] + [PLAINS] * 10)
        on_board(me, BEAR)
        me.own_turns = 2
        bt._resolve(me, opp, BLAZING, 3, entry())
        self.assertEqual(len(me.impulse), 1)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)  # naechster Zug: kein Mana fuer den Titan, danach verfallen
        self.assertEqual((me.impulse, TITAN in me.hand, TITAN in me.library), ([], False, False))


class LyraTests(unittest.TestCase):
    def test_angel_after_three_draws(self):
        me, opp = pair()
        on_board(me, LYRA, entered=5)
        me.lands, me.hand = [ISLAND] * 3, [DRAW3]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        angels = [c for c in me.creatures if c.card.name == "Angel"]
        self.assertEqual(len(angels), 1)
        self.assertTrue(angels[0].has("flying"))

    def test_no_angel_after_two_draws(self):
        me, opp = pair()
        on_board(me, LYRA, entered=5)
        me.lands, me.hand = [ISLAND] * 2, [DRAW2]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertFalse(any(c.card.name == "Angel" for c in me.creatures))

    def test_draw_step_counts(self):
        me, opp = pair()
        on_board(me, LYRA, entered=5)
        me.lands, me.hand = [ISLAND] * 2, [DRAW2]
        bt.take_turn(me, opp, 5, 3, skip_draw=False)
        self.assertTrue(any(c.card.name == "Angel" for c in me.creatures))

    def test_ability_draws_two_on_combat_damage(self):
        me, opp = pair()
        on_board(me, LYRA)
        me.lands = [ISLAND] * 5
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["damage"], len(me.hand)), (2, 2))
        self.assertEqual(me.creatures[0].tdraw, 0)  # nur bis Rundenende

    def test_ability_not_used_against_a_flyer(self):
        me, opp = pair()
        on_board(me, LYRA)
        on_board(opp, BIRD)
        me.lands = [ISLAND] * 5
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(me.hand, [])


class DrawOnceTests(unittest.TestCase):
    def test_draw_spell_draws_once(self):
        me, opp = pair()
        me.lands, me.hand = [ISLAND] * 2, [DRAW2]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((len(me.library), me.drawn), (18, 2))

    def test_enter_draw_creature_draws_once(self):
        me, opp = pair()
        seer = make("Seer", CRE, "{1}{U}", 2, "When this creature enters, draw a card.", "1", "1")
        me.lands, me.hand = [ISLAND] * 2, [seer]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(len(me.library), 19)

    def test_draw_outside_the_main_phase_still_draws(self):
        me, opp = pair()
        bt._resolve(me, opp, DRAW2, 3, entry())
        self.assertEqual(len(me.library), 18)


class BladesTests(unittest.TestCase):
    def test_enters_with_damage_and_life(self):
        me, opp = pair()
        on_board(opp, OGRE)
        bt._resolve(me, opp, BLADES, 3, entry())
        self.assertEqual((opp.creatures, me.life), ([], 23))

    def test_equip_before_attack(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        me.perms, me.lands = [BLADES], [MOUNTAIN] * 3
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["damage"], bear.power, bear.toughness), (4, 4, 3))

    def test_equip_cheaper_with_counters(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        bear.bonus = 1
        me.perms, me.lands = [BLADES], [MOUNTAIN] * 2
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 5)

    def test_gear_stays_when_host_dies(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        me.perms, me.lands = [BLADES], [MOUNTAIN] * 3
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        bear.dead = True
        bt.bury((me,), entry())
        self.assertIn(BLADES, me.perms)
        ogre = on_board(me, OGRE)
        bt.take_turn(me, opp, 7, 4, skip_draw=True)
        self.assertEqual(ogre.power, 5)

    def test_moves_when_host_cannot_attack(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        me.perms, me.lands = [BLADES], [MOUNTAIN] * 3
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        bear.locked = True
        ogre = on_board(me, OGRE)
        bt.take_turn(me, opp, 7, 4, skip_draw=True)
        self.assertEqual((bear.power, ogre.power), (2, 5))

    def test_no_move_while_host_can_attack(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        ogre = on_board(me, OGRE)
        me.perms, me.lands = [BLADES], [MOUNTAIN] * 3
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        host = bear if bear.power > 2 else ogre
        other = ogre if host is bear else bear
        bt.take_turn(me, opp, 7, 4, skip_draw=True)
        self.assertEqual((other.power, host.power), (other.card.power, host.card.power + 2))


if __name__ == "__main__":
    unittest.main()
