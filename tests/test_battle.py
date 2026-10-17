"""Kampfmodell Stufe 1: Schaden, Blocken, Angriffs- und Blockentscheidungen, Spielablauf gegen ein Gegnerdeck."""
import random
import unittest
from unittest import mock

import mtg_sim
from components import battle as bt
from components.cards import card_info
from tests.fixtures import args_for
from tests.fixtures_walkers import _card

DASH = "—"


def creature(name, power, toughness, keywords=(), cost=None, cmc=2, text=None):
    text = text if text is not None else ", ".join(k.capitalize() for k in keywords)
    cost = cost or "{%d}" % cmc  # der Manawert kommt aus den Manakosten
    return card_info(_card(name, f"Creature {DASH} Test", cost, cmc, "", text, [k.title() for k in keywords],
                           str(power), str(toughness)))[0]


def cr(card, entered=0):
    return bt.Creature(card, entered)


class KeywordTests(unittest.TestCase):
    def test_combat_keywords_are_read(self):
        c = creature("Bird", 2, 2, ("flying", "first strike"))
        self.assertEqual(set(c.kw), {"flying", "first strike"})

    def test_granted_keywords_do_not_count(self):
        c = card_info(_card("Lord", f"Creature {DASH} Test", "{2}", 2, "", "Creatures you control have flying.",
                            ["Flying"], "1", "1"))[0]
        self.assertEqual(c.kw, ())


class BlockRuleTests(unittest.TestCase):
    def test_flying_needs_flying_or_reach(self):
        bird, bear = cr(creature("Bird", 2, 2, ("flying",))), cr(creature("Bear", 2, 2))
        spider = cr(creature("Spider", 1, 3, ("reach",)))
        self.assertFalse(bt.can_block(bear, bird))
        self.assertTrue(bt.can_block(spider, bird))
        self.assertTrue(bt.can_block(cr(creature("Bird2", 1, 1, ("flying",))), bird))
        self.assertTrue(bt.can_block(bird, bear))  # Flieger duerfen auch Bodenkreaturen blocken

    def test_tapped_creatures_cannot_block(self):
        bear = cr(creature("Bear", 2, 2))
        bear.tapped = True
        self.assertFalse(bt.can_block(bear, cr(creature("X", 1, 1))))


class DamageTests(unittest.TestCase):
    def fight(self, attacker, blockers):
        a, bs = cr(attacker), [cr(b) for b in blockers]
        res = bt.resolve_combat([(a, bs)])
        return res, a, bs

    def test_unblocked_damage(self):
        res, _a, _b = self.fight(creature("Bear", 2, 2), [])
        self.assertEqual(res["player"], 2)

    def test_trade(self):
        res, a, bs = self.fight(creature("Bear", 2, 2), [creature("Bear2", 2, 2)])
        self.assertEqual((a.dead, bs[0].dead, res["player"]), (True, True, 0))

    def test_first_strike_kills_before_damage(self):
        _res, a, bs = self.fight(creature("Knight", 2, 2, ("first strike",)), [creature("Bear", 2, 2)])
        self.assertEqual((a.dead, bs[0].dead), (False, True))

    def test_double_strike_hits_twice(self):
        res, _a, _b = self.fight(creature("Twin", 2, 2, ("double strike",)), [])
        self.assertEqual(res["player"], 4)
        _res, a, bs = self.fight(creature("Twin", 2, 2, ("double strike",)), [creature("Wall", 0, 4)])
        self.assertTrue(bs[0].dead)  # 2 + 2

    def test_deathtouch(self):
        _res, a, bs = self.fight(creature("Snake", 1, 1, ("deathtouch",)), [creature("Giant", 5, 5)])
        self.assertEqual((a.dead, bs[0].dead), (True, True))

    def test_trample(self):
        res, _a, bs = self.fight(creature("Rhino", 5, 5, ("trample",)), [creature("Bear", 2, 2)])
        self.assertEqual((res["player"], bs[0].dead), (3, True))

    def test_trample_with_deathtouch(self):
        res, _a, bs = self.fight(creature("Wurm", 5, 5, ("trample", "deathtouch")), [creature("Giant", 4, 4)])
        self.assertEqual((res["player"], bs[0].dead), (4, True))  # 1 Schaden reicht dem Blocker

    def test_lifelink(self):
        res, _a, _b = self.fight(creature("Cleric", 3, 3, ("lifelink",)), [])
        self.assertEqual(res["lifelink_attacker"], 3)

    def test_double_block_kills_as_many_as_possible(self):
        _res, a, bs = self.fight(creature("Ogre", 3, 5), [creature("Elf", 1, 1), creature("Bear", 3, 3)])
        self.assertFalse(a.dead)  # 1 + 3 Schaden < 5
        self.assertEqual((bs[0].dead, bs[1].dead), (True, False))  # 3 Schaden: Elf stirbt, fuer den Bear reicht der Rest nicht


class AttackDecisionTests(unittest.TestCase):
    def test_users_example_two_3_2_against_a_2_1(self):
        mine = [cr(creature("A", 3, 2)), cr(creature("B", 3, 2))]
        theirs = [cr(creature("C", 2, 1))]
        self.assertEqual(len(bt.choose_attackers(mine, theirs, 20, 20, step=5)), 2)

    def test_creature_that_would_be_eaten_stays_home(self):
        mine = [cr(creature("Bear", 2, 2))]
        theirs = [cr(creature("Ogre", 3, 3))]
        self.assertEqual(bt.choose_attackers(mine, theirs, 20, 20, step=5), [])

    def test_two_2_2_against_a_3_3_stay_home(self):
        mine = [cr(creature("A", 2, 2)), cr(creature("B", 2, 2))]
        self.assertEqual(bt.choose_attackers(mine, [cr(creature("Ogre", 3, 3))], 20, 20, step=5), [])

    def test_all_in_when_lethal_is_sure(self):
        mine = [cr(creature("A", 2, 2)), cr(creature("B", 2, 2)), cr(creature("C", 2, 2))]
        att = bt.choose_attackers(mine, [cr(creature("Ogre", 3, 3))], 4, 20, step=5)
        self.assertEqual(len(att), 3)  # einer wird geblockt, 4 Schaden kommen sicher durch

    def test_flyer_attacks_past_ground_blockers(self):
        mine = [cr(creature("Bird", 2, 2, ("flying",)))]
        self.assertEqual(len(bt.choose_attackers(mine, [cr(creature("Ogre", 5, 5))], 20, 20, step=5)), 1)

    def test_hold_back_against_lethal_crack_back(self):
        mine = [cr(creature("A", 3, 3)), cr(creature("B", 3, 3))]
        theirs = [cr(creature("X", 4, 1)), cr(creature("Y", 4, 1))]
        # wir haben 8 Leben, ihre zwei 4/1 waeren ohne Blocker toedlich
        att = bt.choose_attackers(mine, theirs, 20, 8, step=5)
        self.assertLess(len(att), 2)

    def test_sick_tapped_and_defender_do_not_attack(self):
        sick = cr(creature("New", 3, 3), entered=5)
        tapped = cr(creature("Tapped", 3, 3))
        tapped.tapped = True
        wall = cr(card_info(_card("Wall", f"Creature {DASH} Wall", "{1}", 1, "", "Defender", ["Defender"], "0",
                                  "4"))[0])
        hasty = cr(card_info(_card("Hasty", f"Creature {DASH} Test", "{1}", 1, "", "Haste", ["Haste"], "2", "1"))[0],
                   entered=5)
        att = bt.choose_attackers([sick, tapped, wall, hasty], [], 20, 20, step=5)
        self.assertEqual([a.card.name for a in att], ["Hasty"])


class BlockDecisionTests(unittest.TestCase):
    def test_good_block(self):
        att = cr(creature("Bear", 2, 2))
        blocks = bt.choose_blocks([att], [cr(creature("Ogre", 3, 3))], 20)
        self.assertEqual([b.card.name for b in blocks[0][1]], ["Ogre"])

    def test_trade_only_if_attacker_is_worth_it(self):
        big = cr(creature("Big", 4, 2, cmc=4))
        self.assertEqual(len(bt.choose_blocks([big], [cr(creature("Cheap", 2, 2, cmc=1))], 20)[0][1]), 1)
        cheap = cr(creature("Cheap", 2, 2, cmc=1))
        self.assertEqual(bt.choose_blocks([cheap], [cr(creature("Big", 2, 2, cmc=4))], 20)[0][1], [])

    def test_double_block_if_one_survives(self):
        att = cr(creature("Giant", 5, 5, cmc=5))
        blocks = bt.choose_blocks([att], [cr(creature("A", 3, 3, cmc=3)), cr(creature("B", 3, 3, cmc=3))], 20)
        self.assertEqual(len(blocks[0][1]), 2)

    def test_chump_only_against_lethal(self):
        att = cr(creature("Giant", 6, 6, cmc=6))
        self.assertEqual(bt.choose_blocks([att], [cr(creature("Elf", 1, 1, cmc=1))], 20)[0][1], [])
        self.assertEqual(len(bt.choose_blocks([att], [cr(creature("Elf", 1, 1, cmc=1))], 6)[0][1]), 1)

    def test_menace_needs_two_blockers(self):
        att = cr(creature("Rogue", 2, 2, ("menace",)))
        self.assertEqual(bt.choose_blocks([att], [cr(creature("Ogre", 3, 3))], 20)[0][1], [])

    def test_ground_creature_cannot_block_a_flyer(self):
        att = cr(creature("Bird", 2, 2, ("flying",)))
        self.assertEqual(bt.choose_blocks([att], [cr(creature("Ogre", 3, 3))], 2)[0][1], [])


RAW = {c["name"]: c for c in [
    _card("Plains", f"Basic Land {DASH} Plains", text="({T}: Add {W}.)", produced=["W"]),
    _card("Test Bear", f"Creature {DASH} Bear", "{W}", 1, "W", power="2", toughness="2"),
    _card("Test Giant", f"Creature {DASH} Giant", "{3}{W}", 4, "W", power="5", toughness="5"),
    _card("Test Wall", f"Creature {DASH} Wall", "{W}", 1, "W", "Defender", ["Defender"], "0", "1"),
    _card("Test Bolt", "Sorcery", "{W}", 1, "W", "Test Bolt deals 3 damage to any target."),
]}
C = {n: card_info(r)[0] for n, r in RAW.items()}


def deck(counts):
    return [C[n] for n, k in counts.items() for _ in range(k)]


class GameTests(unittest.TestCase):
    def test_strong_deck_beats_weak_deck(self):
        random.seed(3)
        res = bt.battle(deck({"Plains": 17, "Test Giant": 12, "Test Bear": 11}),
                        deck({"Plains": 17, "Test Wall": 23}), 60, on_draw=False)
        self.assertEqual(res["games"], 60)
        self.assertGreater(res["wins"], 50)
        self.assertEqual(res["wins"] + res["losses"] + res["draws"], 60)
        self.assertIsNotNone(res["fastest_win"])

    def test_mirror_is_balanced_on_both_sides(self):
        random.seed(5)
        d = deck({"Plains": 17, "Test Bear": 23})
        res = bt.battle(d, list(d), 200, on_draw=False)
        self.assertGreater(res["wins"], 40)
        self.assertGreater(res["losses"], 40)

    def test_burn_goes_face(self):
        random.seed(7)
        res = bt.battle(deck({"Plains": 17, "Test Bolt": 23}), deck({"Plains": 17, "Test Wall": 23}), 40,
                        on_draw=False)
        self.assertGreater(res["wins"], 35)

    def test_play_skips_first_draw(self):
        random.seed(1)
        res = bt.battle(deck({"Plains": 17, "Test Bear": 23}), deck({"Plains": 17, "Test Bear": 23}), 1,
                        on_draw=False)
        log = res["fastest_win"] or res["fastest_loss"]
        self.assertIsNone(log["log"][0]["drew"])     # unser erster Zug: kein Ziehen
        self.assertIsNotNone(log["log"][1]["drew"])  # erster Zug des Gegners: Ziehen

    def test_our_mulligan_loss_is_counted_but_not_as_fastest(self):
        real = bt.deal_opening
        calls = {"n": 0}

        def deal(cards, mulligan, min_hand, keep_at_min=False):  # unser erster Deal geht durch Mulligan verloren
            calls["n"] += 1
            if calls["n"] == 1:
                return None, None, 3, []
            return real(cards, mulligan, min_hand, keep_at_min=keep_at_min)

        random.seed(4)
        with mock.patch.object(bt, "deal_opening", deal):
            res = bt.battle(deck({"Plains": 17, "Test Bear": 23}), deck({"Plains": 17, "Test Wall": 23}), 3,
                            on_draw=False)
        self.assertEqual(res["mull_losses"], 1)
        self.assertNotIn(0, res["loss_rounds"])

    def test_the_enemy_never_concedes(self):
        with mock.patch("components.mulligan.mulligan_reasons", lambda hand: ["immer Mulligan"]):
            enemy = bt.Player("Gegner", deck({"Plains": 17, "Test Bear": 23}), never_concede=True)
            us = bt.Player("Wir", deck({"Plains": 17, "Test Bear": 23}))
        self.assertFalse(enemy.lost)
        self.assertEqual((len(enemy.hand), enemy.mulls), (5, 2))  # behaelt die 5er-Hand
        self.assertTrue(us.lost)

    def test_turn_limit_gives_a_draw(self):
        random.seed(2)
        walls = deck({"Plains": 17, "Test Wall": 23})
        res = bt.battle(walls, list(walls), 10, on_draw=False, max_turns=8)
        self.assertEqual(res["draws"], 10)


class SelfDamageTests(unittest.TestCase):
    def test_each_player_also_hits_us(self):
        doubt = card_info(_card("Test Doubt", "Sorcery", "{W}", 1, "W",
                                "Draw two cards. Test Doubt deals 2 damage to each player."))[0]
        self.assertEqual(doubt.self_damage, 2)
        self.assertEqual(C["Test Bolt"].self_damage, 0)
        me, opp = bt.Player("Wir", deck({"Plains": 20})), bt.Player("Gegner", deck({"Plains": 20}))
        bt._resolve(me, opp, doubt, 1, {"face": 0})
        self.assertEqual((me.life, opp.life), (18, 18))


class BattleReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        args = args_for(["deck.txt", "--sims", "100", "--kaempfe", "30"])
        entries = [{"path": "", "name": "Splash", "deck": {"Plains": 17, "Test Giant": 12, "Test Bear": 11},
                    "parts": []},
                   {"path": "", "name": "NoSplash", "deck": {"Plains": 17, "Test Bear": 23}, "parts": []}]
        with mock.patch.object(mtg_sim, "fetch_cards_cached", lambda n, refresh=False: RAW), \
                mock.patch.object(mtg_sim, "load_enemy", lambda path: {"name": "Mauern",
                                                                       "deck": {"Plains": 17, "Test Wall": 23}}):
            cls.html = mtg_sim.battle_entries(entries, "enemy.txt", args, progress=lambda m: None)

    def test_overview_for_both_variants(self):
        self.assertIn("Kampf gegen Mauern", self.html)
        self.assertIn('id="uebersicht"', self.html)
        overview = self.html[self.html.index('id="uebersicht"'):self.html.index("</section>",
                                                                                self.html.index('id="uebersicht"'))]
        for text in ("Splash", "NoSplash", "On the Play", "On the Draw", "Siege", "Niederlagen"):
            self.assertIn(text, overview)

    def test_protocols_with_switch(self):
        self.assertIn('id="sieg"', self.html)
        self.assertIn('id="niederlage"', self.html)  # auch ohne Niederlage gibt es den Abschnitt (mit Hinweis)
        self.assertIn('id="sieg-1"', self.html)      # zweite Variante
        sec = self.html[self.html.index('id="sieg"'):self.html.index("</section>", self.html.index('id="sieg"'))]
        for text in ("Starthand", "Main 1", "Kampf", "Main 2", "Leben", "Feld"):
            self.assertIn(text, sec)
        self.assertIn('class="gsw"', sec)

    def test_rules_are_explained(self):
        self.assertIn("So funktioniert der Kampf", self.html)


class MainReportTests(unittest.TestCase):
    def test_goldfish_report_has_no_battle(self):
        args = args_for(["deck.txt", "--sims", "100"])
        entries = [{"path": "", "name": "Wir", "deck": {"Plains": 17, "Test Bear": 23}, "parts": []}]
        with mock.patch.object(mtg_sim, "fetch_cards_cached", lambda n, refresh=False: RAW):
            html = mtg_sim.simulate_entries(entries, args, progress=lambda m: None)
        self.assertNotIn('id="kampf"', html)       # kein Kampfabschnitt im Goldfish-Bericht
        self.assertNotIn("Schnellster Sieg", html)

    def test_cli_option(self):
        args = args_for(["deck.txt", "--gegner", "a.txt", "--gegner", "b.txt", "--kaempfe", "40"])
        self.assertEqual((args.gegner, args.kaempfe, args.kampf_runden), (["a.txt", "b.txt"], 40, 20))
        self.assertEqual(args.kampf_ausgabe, "mtg_kampf.html")


if __name__ == "__main__":
    unittest.main()
