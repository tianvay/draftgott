"""Kampfmodell Paket M, Teil 1: Ausloeser bei Scry/Surveil (Prudent Fateseer, Saheeli Consul, Proft, Desperate
Futurescribe), Jace-Surveil vor dem Kampf, Tod und Opfern (Way of the Necromancer, Edgar Ancient Bloodlord, Jace-Token
stirbt)."""
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS = W["Plains"]
B, U = ("B",), ("U",)


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="U"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


SWAMP, ISLAND = land("Swamp", "B"), land("Island", "U")
BEAR = W["Test Bear"]
TOKEN = BEAR._replace(name="Cadet", power=1, toughness=1, is_token=True)
TITAN = make("Titan", CRE, "{4}{G}", 5, "", "5", "5", colors="G")
WURM = make("Wurm", CRE, "{4}{G}", 5, "Trample", "5", "5", ["Trample"], "G")
WALL = make("Wall", CRE, "{1}{W}", 2, "", "2", "2", colors="W")
STUDY = make("Peek", "Sorcery", "{U}", 1, "Surveil 1.")
QUICK = make("Quick Trick", "Instant", "{1}{U}", 2, "Draw a card.")
KILL = make("Murder", "Instant", "{1}{B}", 2, "Destroy target creature.", colors="B")
SEND = make("Send Home", "Instant", "{U}", 1, "Return target creature to its owner's hand.")
OWL = make("Seer Owl", CRE, "{1}{U}", 2, "{1}: Surveil 1.", "1", "1")

FATESEER = make("Prudent Fateseer", f"Creature {DASH} Dwarf Wizard", "{1}{W/U}{W/U}", 3,
                "Whenever you scry or surveil, creatures you control get +1/+0 until end of turn. This ability "
                "triggers only once each turn.", "2", "2")
CONSUL = make("Saheeli, Consul of Oversight", f"Legendary Creature {DASH} Human Advisor", "{3}{W}{W}", 5,
              "Flying\nWhenever you scry or surveil, create a 1/1 colorless Thopter artifact creature token with "
              "flying. This ability triggers only once each turn.", "3", "3", ["Flying"], "W")
PROFT = make("Proft, Consulting Detective", f"Legendary Creature {DASH} Human Detective", "{1}{U}", 2,
             "Whenever you scry or surveil, you may pay {2}. If you do, put a +1/+1 counter on Proft and draw a "
             "card. (Draw after you scry or surveil.)", "1", "2")
FUTURE = make("Desperate Futurescribe", f"Creature {DASH} Kor Scout", "{2}{W}{U}", 4,
              "Flying\nAt the beginning of combat on your turn, another target creature you control gets +1/+1 "
              "until end of turn. If you've scried or surveilled this turn, put a +1/+1 counter on that creature "
              "instead.", "2", "2", ["Flying"])
NECRO = make("Way of the Necromancer", "Legendary Enchantment", "{1}{B}", 2, "When Way of the Necromancer enters, "
             "empower Jace 2.\nWhenever a creature you control dies, put a loyalty counter on each planeswalker you "
             "control.", colors="B")
EDGAR = make("Edgar, Ancient Bloodlord", f"Legendary Creature {DASH} Vampire Noble", "{W}{B}", 2,
             "Whenever another creature or planeswalker you control dies, you gain 1 life.\n{2}, Sacrifice another "
             "creature or planeswalker: Put a +1/+1 counter on Edgar. He gains menace until end of turn. (He can't "
             "be blocked except by two or more creatures.)", "2", "2", colors="B")
MASSACRE = make("Massacre Girl, Most Wanted", f"Legendary Creature {DASH} Human Assassin", "{4}{B}", 5,
                "Whenever another creature or planeswalker you control dies, Massacre Girl deals 1 damage to target "
                "opponent and you gain 1 life.\nWhenever an opponent is dealt noncombat damage, put a +1/+1 counter "
                "on Massacre Girl.", "2", "2", colors="B")


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
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


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertEqual(FATESEER.surveil_team_pump, 1)
        self.assertEqual(CONSUL.surveil_tokens[0][1].name, "Thopter")
        self.assertEqual(CONSUL.surveil_tokens[0][1].kw, ("flying",))
        self.assertEqual(PROFT.surveil_pay, 2)
        self.assertEqual(FUTURE.combat_buff, 1)
        self.assertEqual(NECRO.death_loyalty, 1)
        self.assertEqual(EDGAR.ally_death_life, 1)
        self.assertEqual(EDGAR.sac_counter, (((2, ()),), 1, ("menace",)))
        self.assertEqual(EDGAR.abilities, ())


class SurveilTriggerTests(unittest.TestCase):
    def test_fateseer_once_per_turn(self):
        me, _opp = pair()
        f, bear = on_board(me, FATESEER), on_board(me, BEAR)
        me.now = 5
        bt.surveil_cards(me, [1], entry(), "Test")
        bt.surveil_cards(me, [1], entry(), "Test")
        self.assertEqual((f.power, bear.power, bear.toughness), (3, 3, 2))
        me.now = 6
        bt.surveil_cards(me, [1], entry(), "Test")
        self.assertEqual(bear.power, 4)

    def test_consul_thopter_once_per_turn(self):
        me, _opp = pair()
        on_board(me, CONSUL)
        me.now = 5
        bt.surveil_cards(me, [1], entry(), "Test")
        bt.surveil_cards(me, [1], entry(), "Test")
        thopters = [c for c in me.creatures if c.card.name == "Thopter"]
        self.assertEqual(len(thopters), 1)
        self.assertTrue(thopters[0].has("flying"))

    def test_proft_pays_with_free_mana_each_time(self):
        me, _opp = pair()
        p = on_board(me, PROFT)
        me.open = [B] * 4
        bt.surveil_cards(me, [1], entry(), "Test")
        bt.surveil_cards(me, [1], entry(), "Test")
        self.assertEqual((p.power, len(me.hand), me.open), (3, 2, []))

    def test_proft_twice_for_two_surveils_at_once(self):
        me, _opp = pair()
        p = on_board(me, PROFT)
        me.open = [B] * 4
        bt.surveil_cards(me, [1, 1], entry(), "Test")
        self.assertEqual((p.power, len(me.hand)), (3, 2))

    def test_proft_keeps_mana_for_instant(self):
        me, _opp = pair()
        p = on_board(me, PROFT)
        me.open, me.hand = [U] * 3, [QUICK]
        bt.surveil_cards(me, [1], entry(), "Test")
        self.assertEqual((p.power, me.hand), (1, [QUICK]))

    def test_futurescribe_pump_without_surveil(self):
        me, opp = pair()
        on_board(me, FUTURE)
        bear = on_board(me, BEAR)
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 5)
        self.assertEqual(bear.power, 2)  # nur bis Rundenende

    def test_futurescribe_counter_after_surveil(self):
        me, opp = pair()
        on_board(me, FUTURE)
        bear = on_board(me, BEAR)
        me.lands, me.hand = [ISLAND], [STUDY]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["damage"], bear.power, bear.toughness), (5, 3, 3))

    def test_jace_surveils_before_combat_for_fateseer(self):
        me, opp = pair()
        on_board(me, FATESEER)
        on_board(me, BEAR)
        me.jace.loyalty = 2
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["damage"], me.jace.loyalty), (6, 1))

    def test_jace_surveils_after_main_two_without_benefit(self):
        me, opp = pair()
        on_board(me, BEAR)
        me.jace.loyalty = 2
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["damage"], me.jace.loyalty), (2, 1))

    def test_surveil_ability_before_attack_for_fateseer(self):
        me, opp = pair()
        on_board(me, FATESEER)
        on_board(me, BEAR)
        on_board(me, OWL)
        me.lands = [ISLAND]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 8)


class DeathTests(unittest.TestCase):
    def test_necromancer_loyalty_only_for_existing_jace(self):
        me, _opp = pair()
        me.perms = [NECRO]
        on_board(me, BEAR).dead = True
        bt.bury((me,), entry())
        self.assertEqual(me.jace.loyalty, 0)
        me.jace.loyalty = 2
        on_board(me, BEAR).dead = True
        bt.bury((me,), entry())
        self.assertEqual(me.jace.loyalty, 3)

    def test_edgar_life_for_other_deaths(self):
        me, _opp = pair()
        edgar = on_board(me, EDGAR)
        on_board(me, BEAR).dead = True
        bt.bury((me,), entry())
        self.assertEqual(me.life, 21)
        edgar.dead = True
        bt.bury((me,), entry())
        self.assertEqual(me.life, 21)

    def test_jace_dying_triggers_edgar_and_massacre_girl(self):
        me, opp = pair()
        on_board(me, EDGAR)
        on_board(me, MASSACRE)
        me.jace.loyalty = 1
        bt._jace_activate(me, 5, entry(), True)  # -1: Surveil, Jace stirbt
        self.assertEqual((me.jace.loyalty, me.life, opp.life), (0, 22, 19))

    def test_jace_killed_in_combat(self):
        me, opp = pair()
        on_board(me, EDGAR).tapped = True
        me.jace.loyalty = 2
        on_board(opp, BEAR)
        bt.take_turn(opp, me, 6, 3, skip_draw=True)
        self.assertEqual((me.jace.loyalty, me.life), (0, 21))


class EdgarSacrificeTests(unittest.TestCase):
    def _chump(self, attacker, mana, life=3):
        me, opp = pair()
        edgar = on_board(me, EDGAR)
        edgar.tapped = True
        on_board(me, TOKEN)
        me.life, me.open = life, [B] * mana
        on_board(opp, attacker)
        e = bt.take_turn(opp, me, 6, 3, skip_draw=True)
        return me, edgar, e

    def test_sacrifices_chump_blocker(self):
        me, edgar, _e = self._chump(TITAN, 2)
        self.assertEqual((me.life, edgar.power), (4, 3))

    def test_without_mana_the_chump_just_dies(self):
        me, edgar, _e = self._chump(TITAN, 1)
        self.assertEqual((me.life, edgar.power), (4, 2))

    def test_no_sacrifice_against_trample(self):
        me, edgar, _e = self._chump(WURM, 2, life=5)  # Opfern liesse alle 5 Trample-Schaden durch
        self.assertEqual((edgar.power, me.life), (2, 5 - 4 + 1))

    def test_no_sacrifice_when_blocker_trades_or_survives(self):
        me, opp = pair()
        edgar = on_board(me, EDGAR)
        bear, wall = on_board(me, BEAR), on_board(me, make("Big Wall", CRE, "{2}", 2, "", "0", "6", colors=""))
        me.open = [B] * 4
        pairs = [(on_board(opp, BEAR), [bear]), (on_board(opp, TITAN), [wall])]
        bt.sacrifice_blockers(me, pairs, entry())
        self.assertEqual((edgar.power, bear.dead, wall.dead), (2, False, False))

    def test_edgar_never_sacrifices_himself(self):
        me, _opp = pair()
        edgar = on_board(me, EDGAR)
        me.open = [B] * 2
        self.assertFalse(bt.sacrifice_for(me, edgar, entry()))
        self.assertEqual(me.open, [B] * 2)

    def test_sacrifice_in_response_to_removal(self):
        me, opp = pair()
        edgar = on_board(me, EDGAR)
        bear = on_board(me, BEAR)
        me.open = [B] * 2
        e = entry()
        bt.cast_removal(KILL, opp, me, e, 5, target=bear)
        self.assertEqual((edgar.power, me.life, bear in me.creatures), (3, 21, False))
        self.assertIn(BEAR, me.graveyard)
        self.assertTrue(any("ohne Ziel" in ev for ev in e["events"]))

    def test_no_sacrifice_against_bounce_or_for_edgar_himself(self):
        me, opp = pair()
        edgar = on_board(me, EDGAR)
        bear = on_board(me, BEAR)
        me.open = [B] * 2
        bt.cast_removal(SEND, opp, me, entry(), 5, target=bear)
        self.assertEqual((edgar.power, me.hand), (2, [BEAR]))
        on_board(me, BEAR)
        bt.cast_removal(KILL, opp, me, entry(), 5, target=edgar)
        self.assertNotIn(edgar, me.creatures)
        self.assertEqual(len(me.creatures), 1)

    def test_sacrifice_for_lethal(self):
        me, opp = pair()
        on_board(me, EDGAR)
        on_board(me, TOKEN)
        on_board(opp, WALL)
        me.lands, opp.life = [SWAMP] * 2, 3
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertLessEqual(opp.life, 0)

    def test_no_sacrifice_when_not_lethal(self):
        me, opp = pair()
        on_board(me, EDGAR)
        token = on_board(me, TOKEN)
        on_board(opp, WALL)
        me.lands, opp.life = [SWAMP] * 2, 4
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertIn(token, me.creatures)

    def test_no_sacrifice_when_already_lethal(self):
        me, opp = pair()
        on_board(me, EDGAR)
        token = on_board(me, TOKEN)
        me.lands, opp.life = [SWAMP] * 2, 3
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertIn(token, me.creatures)
        self.assertLessEqual(opp.life, 0)

    def test_lost_damage_counts(self):
        me, opp = pair()
        on_board(me, EDGAR)
        bear = on_board(me, BEAR)
        me.lands, opp.life = [SWAMP] * 2, 5
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertIn(bear, me.creatures)  # Opfern gaebe 3 statt 4 Schaden
        self.assertEqual(opp.life, 1)


if __name__ == "__main__":
    unittest.main()
