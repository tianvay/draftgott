"""Kampfmodell: Fblthp (Domain, X beim Wirken, Basic Lands suchen) und Massacre Girl (Tode, Schaden ausserhalb des
Kampfs)."""
import random
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS, ISLAND = W["Plains"], W["Island"]
G = ("G",)


def land(name, color, types=None):
    return card_info(_card(name, f"Basic Land {DASH} {types or name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=()):
    return card_info(_card(name, type_line, cost, cmc, "G", text, list(keywords), power, toughness))[0]


FOREST, SWAMP = land("Forest", "G"), land("Swamp", "B")
DUAL = card_info(_card("Wooded Bay", f"Land {DASH} Forest Island", text="({T}: Add {G} or {U}.)",
                       produced=["G", "U"]))[0]
FBLTHP = make("Fblthp, Knows the Way", f"Legendary Creature {DASH} Homunculus Scout", "{X}{G}{G}", 2,
              "Domain — Fblthp's power is equal to the number of basic land types among lands you control.\nWhen "
              "Fblthp enters, search your library for up to X basic land cards with different names, reveal them, "
              "put them into your hand, then shuffle.", "*", "2")
GIRL = make("Massacre Girl, Most Wanted", f"Legendary Creature {DASH} Human Assassin", "{4}{B}", 5,
            "Whenever another creature or planeswalker you control dies, Massacre Girl deals 1 damage to target "
            "opponent and you gain 1 life.\nWhenever an opponent is dealt noncombat damage, put a +1/+1 counter on "
            "Massacre Girl.", "4", "4")
GROWTH = make("Giant Growth", "Instant", "{1}{G}", 2, "Target creature gets +3/+3 until end of turn.")
JAB = make("Jab", "Sorcery", "{R}", 1, "Jab deals 2 damage to target opponent.")
SWEEP = make("Pyroclasm", "Sorcery", "{1}{R}", 2, "Pyroclasm deals 5 damage to each creature.")
REVIVAL = make("Generous Revival", "Sorcery", "{2}{W}", 3, "Return target creature card with mana value 3 or less "
               "from your graveyard to the battlefield with an additional +1/+1 counter on it.")
BEAR = W["Test Bear"]


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


class FblthpTests(unittest.TestCase):
    def test_parse(self):
        self.assertTrue(FBLTHP.domain_power and FBLTHP.x_search_basics)
        self.assertEqual((FBLTHP.mv, FBLTHP.alts), (2, ((0, (("G", 2),)),)))

    def test_domain_power(self):
        me, opp = pair()
        me.lands = [FOREST, DUAL, PLAINS, FOREST]
        bt._resolve(me, opp, FBLTHP, 3, entry())
        self.assertEqual(me.creatures[0].power, 3)  # Forest, Island, Plains
        me.lands.append(SWAMP)
        self.assertEqual(me.creatures[0].power, 4)
        me.lands.append(card_info(_card("Gate", f"Land {DASH} Gate", text="({T}: Add {R}.)", produced=["R"]))[0])
        self.assertEqual(me.creatures[0].power, 4)  # Gate ist kein Basic-Land-Typ

    def test_x_from_free_mana_searches_basics(self):
        me, opp = pair(library=[BEAR, ISLAND, ISLAND, PLAINS, SWAMP, BEAR])
        me.lands, me.hand = [FOREST] * 4, [FBLTHP]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["main2"], ["Fblthp, Knows the Way"])
        self.assertEqual(sorted(c.name for c in me.hand), ["Island", "Plains"])
        self.assertEqual((me.open, sorted(c.name for c in me.library).count("Island")), ([], 1))
        self.assertEqual(me.next_x, 0)  # X gilt nur fuer dieses Betreten

    def test_new_colors_first(self):
        me, opp = pair(library=[ISLAND, ISLAND, PLAINS, SWAMP])
        me.lands, me.hand = [FOREST, FOREST, ISLAND, FOREST], [FBLTHP]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(sorted(c.name for c in me.hand), ["Plains", "Swamp"])  # Island ist keine neue Farbe

    def test_x_keeps_mana_for_an_instant(self):
        me, opp = pair(library=[ISLAND, PLAINS])
        me.lands, me.hand = [FOREST] * 4, [FBLTHP, GROWTH]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((me.hand, len(me.open)), ([GROWTH], 2))

    def test_x_limited_by_different_names(self):
        me, opp = pair(library=[ISLAND, ISLAND, ISLAND])
        me.lands, me.hand = [FOREST] * 6, [FBLTHP]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((me.hand, len(me.open)), ([ISLAND], 3))  # nur ein Name, X = 1

    def test_returned_from_graveyard_has_x_zero(self):
        me, opp = pair(library=[ISLAND, PLAINS])
        me.graveyard[:] = [FBLTHP]
        bt._resolve(me, opp, REVIVAL, 3, entry())
        self.assertEqual((me.creatures[0].card.name, me.hand), ("Fblthp, Knows the Way", []))


class MassacreGirlTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual((GIRL.ally_death_ping, GIRL.noncombat_counter), ((1, 1), 1))

    def test_another_creature_dies(self):
        me, opp = pair()
        girl, bear = bt.Creature(GIRL, 0), bt.Creature(BEAR, 0)
        me.creatures = [girl, bear]
        bear.dead = True
        bt.bury((me,), entry())
        self.assertEqual((opp.life, me.life, girl.bonus, me.dealt_direct), (19, 21, 1, 1))

    def test_own_death_does_not_trigger(self):
        me, opp = pair()
        girl = bt.Creature(GIRL, 0)
        me.creatures, girl.dead = [girl], True
        bt.bury((me,), entry())
        self.assertEqual((opp.life, me.life), (20, 20))

    def test_dying_together_still_triggers(self):
        me, opp = pair()
        me.creatures = [bt.Creature(GIRL, 0), bt.Creature(BEAR, 0), bt.Creature(BEAR, 0)]
        bt._resolve(opp, me, SWEEP, 4, entry())
        self.assertEqual((me.creatures, opp.life, me.life), ([], 18, 22))

    def test_tokens_count(self):
        me, opp = pair()
        token = bt.Creature(card_info(_card("Recruit", CRE, "", 0, "W", "", [], "1", "1"))[0]._replace(is_token=True), 0)
        girl = bt.Creature(GIRL, 0)
        me.creatures, token.dead = [girl, token], True
        bt.bury((me,), entry())
        self.assertEqual(opp.life, 19)

    def test_noncombat_damage_from_a_spell(self):
        me, opp = pair()
        girl = bt.Creature(GIRL, 0)
        me.creatures = [girl]
        bt._resolve(me, opp, JAB, 3, entry())
        self.assertEqual((opp.life, girl.bonus), (18, 1))  # ein Schadensereignis, eine Marke

    def test_combat_damage_does_not_count(self):
        me, opp = pair()
        girl = bt.Creature(GIRL, 0)
        me.creatures = [girl]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((opp.life, girl.bonus), (16, 0))

    def test_opponents_girl_counts_our_damage_to_them(self):
        me, opp = pair()
        girl = bt.Creature(GIRL, 0)
        opp.creatures = [girl]
        bt._resolve(me, opp, JAB, 3, entry())
        self.assertEqual(girl.bonus, 0)  # "an opponent" aus Sicht des Gegners: das sind wir


class GameTests(unittest.TestCase):
    def test_games(self):
        deck = [FOREST] * 8 + [ISLAND] * 3 + [PLAINS] * 3 + [SWAMP] * 3 + [FBLTHP, GIRL, JAB, SWEEP, BEAR] * 4
        random.seed(41)
        r = bt.battle(deck, deck, 60, on_draw=False)
        self.assertEqual(r["wins"] + r["losses"] + r["draws"], 60)


if __name__ == "__main__":
    unittest.main()
