"""Kampfmodell: Karten aus unserem Deck - Ingris (Schaden beim Angriff), Leben (Apex Witchstalker, Extended Absence),
Zusatzkosten (Silence the Echo), Prowess (Grim Repriser)."""
import random
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS = W["Plains"]
B = ("B",)


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=()):
    return card_info(_card(name, type_line, cost, cmc, "B", text, list(keywords), power, toughness))[0]


SWAMP = card_info(_card("Swamp", f"Basic Land {DASH} Swamp", text="({T}: Add {B}.)", produced=["B"]))[0]
INGRIS = make("Ingris Stingerquill", f"Legendary Creature {DASH} Elder Sphinx", "{B}{R}{R}", 3,
              "Flying\nWhenever a creature you control attacks, that creature deals 1 damage to each opponent.",
              "1", "4", ["Flying"])
APEX = make("Apex Witchstalker", f"Creature {DASH} Wolf", "{4}{B}{B}", 6, "Menace\nWhen this creature enters or "
            "dies, you gain 2 life.", "6", "4", ["Menace"])
ABSENCE = make("Extended Absence", "Instant", "{3}{B}", 4, "Exile target creature or planeswalker. Extended Absence "
               "deals 1 damage to each opponent and you gain 1 life.")
SILENCE = make("Silence the Echo", "Sorcery", "{1}{B}", 2, "As an additional cost to cast this spell, sacrifice a "
               "creature or planeswalker or pay {3}.\nDestroy target creature or planeswalker.")
REPRISER = make("Grim Repriser", f"Creature {DASH} Zombie Bard", "{B}{R}", 2, "Prowess (Whenever you cast a "
                "noncreature spell, this creature gets +1/+1 until end of turn.)", "2", "2", ["Prowess"])
DRAW = make("Night's Whisper", "Sorcery", "{1}{B}", 2, "Draw two cards.")
BEAR = W["Test Bear"]


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertEqual(INGRIS.attack_ping, 1)
        self.assertEqual((APEX.etb_life, APEX.death_life), (2, 2))
        self.assertEqual(ABSENCE.spell_life, 1)
        self.assertEqual(SILENCE.extra_cost, 3)
        self.assertTrue(REPRISER.prowess)
        self.assertEqual(SILENCE.mv, 2)  # Zusatzkosten aendern den Manawert nicht


class IngrisTests(unittest.TestCase):
    def test_each_attacker_pings(self):
        me, opp = player(), player("Gegner")
        me.creatures = [bt.Creature(INGRIS, 0), bt.Creature(BEAR, 0)]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["damage"], opp.life, me.dealt_direct), (3, 15, 2))

    def test_ping_also_when_attacking_jace(self):
        me, opp = player(), player("Gegner")
        me.creatures = [bt.Creature(INGRIS, 5), bt.Creature(BEAR, 0)]  # Ingris frisch, greift nicht an
        opp.jace.loyalty = 3
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((opp.jace.loyalty, opp.life), (1, 19))


class LifeTests(unittest.TestCase):
    def test_apex_enters_and_dies(self):
        me, opp = player(), player("Gegner")
        bt._resolve(me, opp, APEX, 3, entry())
        self.assertEqual(me.life, 22)
        me.creatures[0].dead = True
        bt.bury((me,), entry())
        self.assertEqual(me.life, 24)

    def test_extended_absence_in_the_opponents_turn(self):
        me, opp = player(), player("Gegner")
        opp.creatures = [bt.Creature(BEAR, 0)]
        me.hand, me.open = [ABSENCE], [B] * 4
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual((opp.creatures, opp.life, me.life, me.dealt_direct), ([], 19, 21, 1))

    def test_extended_absence_as_blocker_answer(self):
        dfn, act = player("Gegner"), player()
        attacker = bt.Creature(BEAR, 0)
        act.creatures = [attacker]
        dfn.hand, dfn.open = [ABSENCE], [B] * 4
        bt.respond_to_attack(dfn, act, [attacker], entry(), 5)
        self.assertEqual((act.creatures, act.life, dfn.life), ([], 19, 21))

    def test_extended_absence_in_the_main_phase(self):
        me, opp = player(), player("Gegner")
        opp.creatures = [bt.Creature(BEAR, 0)]
        bt._resolve(me, opp, ABSENCE, 3, entry())
        self.assertEqual((opp.life, me.life), (19, 21))


class ExtraCostTests(unittest.TestCase):
    def test_silence_costs_three_more(self):
        me = player()
        me.hand, me.open = [SILENCE], [B] * 4
        self.assertFalse(bt.affordable(me, SILENCE))
        me.open = [B] * 5
        self.assertTrue(bt.affordable(me, SILENCE))

    def test_silence_in_the_main_phase(self):
        me, opp = player(), player("Gegner")
        opp.creatures = [bt.Creature(BEAR, 0)]
        me.lands, me.hand = [SWAMP] * 4, [SILENCE]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["main1"], me.hand), ([], [SILENCE]))
        me.lands.append(SWAMP)
        e = bt.take_turn(me, opp, 7, 4, skip_draw=True)
        self.assertEqual((e["main1"], opp.creatures), (["Silence the Echo"], []))
        self.assertIn(SILENCE, me.graveyard)  # die Originalkarte


class ProwessTests(unittest.TestCase):
    def test_noncreature_spell_pumps(self):
        me, opp = player(), player("Gegner")
        rep = bt.Creature(REPRISER, 0)
        me.creatures = [rep]
        bt._resolve(me, opp, DRAW, 3, entry())
        self.assertEqual((rep.power, rep.toughness), (3, 3))
        bt._resolve(me, opp, BEAR, 3, entry())
        self.assertEqual(rep.power, 3)
        bt.cleanup((me,))
        self.assertEqual(rep.power, 2)

    def test_prowess_in_a_real_turn(self):
        me, opp = player(library=[PLAINS] * 5), player("Gegner")
        me.lands, me.hand = [SWAMP] * 2, [DRAW]
        me.creatures = [bt.Creature(REPRISER, 0)]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 3)

    def test_prowess_on_instants_in_the_opponents_turn(self):
        me, opp = player(), player("Gegner")
        rep = bt.Creature(REPRISER, 0)
        me.creatures, opp.creatures = [rep], [bt.Creature(BEAR, 0)]
        me.hand, me.open = [ABSENCE], [B] * 4
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual(rep.power, 3)


class GameTests(unittest.TestCase):
    def test_games(self):
        deck = [SWAMP] * 17 + [INGRIS, APEX, ABSENCE, SILENCE, REPRISER, DRAW, BEAR] * 3
        random.seed(23)
        r = bt.battle(deck, deck, 60, on_draw=False)
        self.assertEqual(r["wins"] + r["losses"] + r["draws"], 60)


if __name__ == "__main__":
    unittest.main()
