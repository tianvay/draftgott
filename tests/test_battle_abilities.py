"""Kampfmodell: aktivierbare Faehigkeiten (Pumps, Marken, Schluesselwoerter, Empower) und ihr Zeitpunkt."""
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
LEG = f"Legendary Creature {DASH} Test"
PLAINS = W["Plains"]


def make(name, cost, cmc, text, power="2", toughness="2", type_line=CRE):
    return card_info(_card(name, type_line, cost, cmc, "G", text, [], power, toughness))[0]


def effects(card):
    return [ab[4] for ab in card.abilities]


GECKO = make("Wrecking Gecko", "{4}{G}", 5, "{6}{G}{G}: This creature gets +4/+4 and gains trample until end of turn.",
             "5", "4")
PEGASUS = make("Shatterwing Pegasus", "{3}{W}", 4, "Flying\n{4}{W}: Creatures you control get +1/+1 until end of turn.",
               "3", "3")
SENTRY = make("Afterthought Sentry", "{1}{U}", 2, "{2}: This creature gains flying until end of turn.")
BLOOM = make("Bloombrute", "{3}{G}{W}", 5, "{4}{G}{W}: Target creature gains trample and lifelink until end of turn.",
             "4", "5")
EDGAR = make("Edgar, Moonlit Sovereign", "{3}{G}", 4,
             "{4}{G}: Put a +1/+1 counter on each creature you control with a +1/+1 counter on it.", "3", "3", LEG)
YOSHI = make("Yoshimaru, Scrappy Stray", "{1}{W}", 2, "{6}: Put a +1/+1 counter on target nonlegendary creature.",
             "2", "1", LEG)
TETH = make("Inspired Tethermage", "{2}{U}", 3, "Whenever you put one or more loyalty counters on a planeswalker, put "
            "a +1/+1 counter on this creature.\n{6}: Empower Jace 2.", "1", "3")
ANCIENT = make("Edgar, Ancient Bloodlord", "{2}{B}", 3, "{2}, Sacrifice another creature or planeswalker: Put a "
               "+1/+1 counter on Edgar. He gains menace until end of turn.", "3", "3", LEG)
SOWER = make("Sureshot Sower", "{2}{G}", 3, "Reach\n{3}{G}, Discard this card: Destroy target creature with flying.")
SLOW = make("Slow Grower", "{1}{G}", 2, "{2}: This creature gets +2/+2 until end of turn. Activate only as a sorcery.")
PUMPER = make("Pumper", "{1}{G}", 2, "{2}: This creature gets +2/+2 until end of turn.")
REACHER = make("Reacher", "{2}{G}", 3, "{1}: This creature gains reach until end of turn.", "3", "3")
BEAR = W["Test Bear"]
OGRE = make("Ogre", "{2}{R}", 3, "", "3", "3")
FLIER = card_info(_card("Bird", CRE, "{1}{W}", 2, "W", "Flying", ["Flying"], "2", "2"))[0]
INSTANT2 = make("Quick Draw", "{1}{G}", 2, "Draw a card.", type_line="Instant")
G = ("G",)


def player(name="Wir"):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], [PLAINS] * 20
    return p


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


class ParseTests(unittest.TestCase):
    def test_pump_and_keyword_on_self(self):
        self.assertEqual(effects(GECKO), [(("pump", 4, 4, "self"), ("grant", ("trample",), "self"))])
        self.assertEqual(GECKO.abilities[0][1:4], (8, False, "instant"))

    def test_pump_all(self):
        self.assertEqual(effects(PEGASUS), [(("pump", 1, 1, "all"),)])

    def test_keyword_grants(self):
        self.assertEqual(effects(SENTRY), [(("grant", ("flying",), "self"),)])
        self.assertEqual(effects(BLOOM), [(("grant", ("trample", "lifelink"), "target"),)])

    def test_counters(self):
        self.assertEqual(effects(EDGAR), [(("counter", 1, "countered"),)])
        self.assertEqual(effects(YOSHI), [(("counter", 1, "nonlegendary"),)])

    def test_empower(self):
        self.assertEqual(effects(TETH), [(("empower", 2),)])

    def test_extra_costs_are_not_modelled(self):
        self.assertEqual(ANCIENT.abilities, ())
        self.assertEqual(SOWER.abilities, ())

    def test_sorcery_speed(self):
        self.assertEqual(SLOW.abilities[0][3], "sorcery")


class AfterBlockTests(unittest.TestCase):
    def test_pump_for_lethal_even_if_mana_is_needed(self):
        me, opp = player(), player("Gegner")
        att = bt.Creature(PUMPER, 0)
        me.creatures, me.hand, me.open, opp.life = [att], [INSTANT2], [G, G], 4
        bt.combat_abilities(me, [(att, [])], opp, entry(), 5, attacking=True)
        self.assertEqual((att.power, att.toughness), (4, 4))

    def test_no_pump_for_damage_if_mana_is_needed(self):
        me, opp = player(), player("Gegner")
        att = bt.Creature(PUMPER, 0)
        me.creatures, me.hand, me.open = [att], [INSTANT2], [G, G]
        bt.combat_abilities(me, [(att, [])], opp, entry(), 5, attacking=True)
        self.assertEqual(att.power, 2)

    def test_pump_for_damage_with_free_mana(self):
        me, opp = player(), player("Gegner")
        att = bt.Creature(PUMPER, 0)
        me.creatures, me.open = [att], [G, G, G, G, G]
        bt.combat_abilities(me, [(att, [])], opp, entry(), 5, attacking=True)
        self.assertEqual(att.power, 6)  # zweimal aktiviert, ein Mana bleibt uebrig
        self.assertEqual(me.open, [G])

    def test_blocker_pumps_for_a_better_block(self):
        dfn, act = player("Gegner"), player()
        att, blk = bt.Creature(OGRE, 0), bt.Creature(PUMPER, 0)
        act.creatures, dfn.creatures, dfn.hand, dfn.open = [att], [blk], [INSTANT2], [G, G]
        bt.combat_abilities(dfn, [(att, [blk])], act, entry(), 6, attacking=False)
        self.assertEqual(bt.outcome(att, [blk]), (True, [False]))

    def test_sorcery_speed_not_in_combat_of_opponent(self):
        dfn, act = player("Gegner"), player()
        att, blk = bt.Creature(OGRE, 0), bt.Creature(SLOW, 0)
        act.creatures, dfn.creatures, dfn.open = [att], [blk], [G, G]
        bt.combat_abilities(dfn, [(att, [blk])], act, entry(), 6, attacking=False)
        self.assertEqual(blk.power, 2)

    def test_trample_after_block(self):
        me, opp = player(), player("Gegner")
        att, blk = bt.Creature(OGRE._replace(power=6, toughness=6), 0), bt.Creature(BEAR, 0)
        src = bt.Creature(BLOOM, 0)
        me.creatures, opp.creatures, me.open = [att, src], [blk], [G] * 5 + [("W",)]
        bt.combat_abilities(me, [(att, [blk])], opp, entry(), 5, attacking=True)
        self.assertTrue(att.has("trample") and att.has("lifelink"))


class BeforeBlockTests(unittest.TestCase):
    def test_flying_to_get_past_a_blocker(self):
        me, opp = player(), player("Gegner")
        sentry = bt.Creature(SENTRY, 0)
        me.creatures, opp.creatures, me.open = [sentry], [bt.Creature(OGRE, 0)], [G, G]
        self.assertEqual(bt.choose_attackers(me.creatures, opp.creatures, 20, 20, 5), [])
        bt.pre_attack_abilities(me, opp, 5, entry())
        self.assertTrue(sentry.has("flying"))
        self.assertEqual(bt.choose_attackers(me.creatures, opp.creatures, 20, 20, 5), [sentry])

    def test_no_flying_if_mana_is_needed(self):
        me, opp = player(), player("Gegner")
        sentry = bt.Creature(SENTRY, 0)
        me.creatures, opp.creatures, me.hand, me.open = [sentry], [bt.Creature(OGRE, 0)], [INSTANT2], [G, G]
        bt.pre_attack_abilities(me, opp, 5, entry())
        self.assertFalse(sentry.has("flying"))

    def test_reach_to_block_a_flier(self):
        dfn, act = player("Gegner"), player()
        bird, reacher = bt.Creature(FLIER, 0), bt.Creature(REACHER, 0)
        act.creatures, dfn.creatures, dfn.open = [bird], [reacher], [G]
        bt.pre_block_abilities(dfn, act, [bird], entry(), 6)
        self.assertTrue(reacher.has("reach"))
        self.assertEqual(bt.choose_blocks([bird], dfn.creatures, dfn.life), [(bird, [reacher])])

    def test_keywords_and_pumps_end_with_the_turn(self):
        p = player()
        c = bt.Creature(SENTRY, 0)
        c.extra, c.pump, c.tpump = {"flying"}, 2, 2
        p.creatures = [c]
        bt.cleanup((p,))
        self.assertEqual((c.has("flying"), c.power, c.toughness), (False, 2, 2))


class CounterAndEmpowerTests(unittest.TestCase):
    def test_counters_at_end_of_opponents_turn(self):
        dfn, act = player("Gegner"), player()
        edgar, bear = bt.Creature(EDGAR, 0), bt.Creature(BEAR, 0)
        bear.bonus = 1
        dfn.creatures, dfn.open = [edgar, bear], [G] * 5
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual((edgar.bonus, bear.bonus), (0, 2))

    def test_no_counters_without_target(self):
        dfn, act = player("Gegner"), player()
        dfn.creatures, dfn.open = [bt.Creature(EDGAR, 0)], [G] * 5
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual(dfn.open, [G] * 5)

    def test_nonlegendary_target_is_not_the_source(self):
        dfn, act = player("Gegner"), player()
        yoshi, bear = bt.Creature(YOSHI, 0), bt.Creature(BEAR, 0)
        dfn.creatures, dfn.open = [yoshi, bear], [G] * 6
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual((yoshi.bonus, bear.bonus), (0, 1))

    def test_empower_at_end_of_opponents_turn(self):
        dfn, act = player("Gegner"), player()
        teth = bt.Creature(TETH, 0)
        dfn.creatures, dfn.open = [teth], [G] * 6
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual((dfn.jace.loyalty, teth.bonus), (2, 1))

    def test_empower_in_own_turn_only_with_free_mana(self):
        me, opp = player(), player("Gegner")
        me.creatures, me.hand, me.open = [bt.Creature(TETH, 0)], [INSTANT2], [G] * 6
        bt.pre_attack_abilities(me, opp, 5, entry())
        self.assertEqual(me.jace.loyalty, 0)
        me.hand = []
        bt.pre_attack_abilities(me, opp, 5, entry())
        self.assertEqual(me.jace.loyalty, 2)

    def test_tap_ability_needs_untapped_creature(self):
        tapper = make("Tapper", "{1}{G}", 2, "{T}: Put a +1/+1 counter on target nonlegendary creature.", "1", "1")
        dfn, act = player("Gegner"), player()
        src, bear = bt.Creature(tapper, 0), bt.Creature(BEAR, 0)
        src.tapped = True
        dfn.creatures = [src, bear]
        dfn.turn_start = 1  # 302.6: seit Beginn des letzten eigenen Zugs da
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual(bear.bonus, 0)
        src.tapped = False
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual((bear.bonus, src.tapped), (1, True))


class TurnTests(unittest.TestCase):
    def test_flying_in_a_real_turn(self):
        me, opp = player(), player("Gegner")
        me.lands = [W["Island"]] * 2
        me.creatures, opp.creatures = [bt.Creature(SENTRY, 0)], [bt.Creature(OGRE, 0)]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["damage"], opp.life), (2, 18))
        self.assertFalse(me.creatures[0].has("flying"))  # verfaellt am Rundenende

    def test_pump_with_free_mana_in_a_real_turn(self):
        me, opp = player(), player("Gegner")
        me.lands = [PLAINS] * 4
        me.creatures = [bt.Creature(PUMPER, 0)]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 6)

    def test_defender_gives_reach_in_a_real_turn(self):
        me, opp = player(), player("Gegner")
        me.creatures, opp.creatures, opp.open = [bt.Creature(FLIER, 0)], [bt.Creature(REACHER, 0)], [G]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((me.creatures, opp.life), ([], 20))

    def test_defender_pumps_to_block_in_a_real_turn(self):
        me, opp = player(), player("Gegner")
        me.creatures, opp.creatures, opp.open = [bt.Creature(OGRE, 0)], [bt.Creature(PUMPER, 0)], [G, G]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((me.creatures, len(opp.creatures), opp.life), ([], 1, 20))

    def test_games_with_abilities(self):
        import random
        deck = [W["Plains"]] * 9 + [W["Island"]] * 8 + [SENTRY, PUMPER, REACHER, TETH, YOSHI, PEGASUS] * 4
        enemy = [W["Plains"]] * 17 + [OGRE, FLIER, PUMPER, EDGAR] * 6
        random.seed(5)
        r = bt.battle(deck, enemy, 60, on_draw=True)
        self.assertEqual(r["wins"] + r["losses"] + r["draws"], 60)
        events = [x for g in r["results_all"] for e in g["log"] for x in e.get("events", [])]
        self.assertTrue(any("Fähigkeit von" in x for x in events))


if __name__ == "__main__":
    unittest.main()
