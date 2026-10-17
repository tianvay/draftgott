"""Kampfmodell: Karten aus dem Friedhof zurueckholen (Zauber, Faehigkeiten aus dem Friedhof, Phoenix, Laender) und
Flashback mit Abwerfen (Twinned Vision)."""
import random
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS, ISLAND = W["Plains"], W["Island"]
B, U, WH = ("B",), ("U",), ("W",)


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=()):
    return card_info(_card(name, type_line, cost, cmc, "W", text, list(keywords), power, toughness))[0]


SWAMP = card_info(_card("Swamp", f"Basic Land {DASH} Swamp", text="({T}: Add {B}.)", produced=["B"]))[0]
REVIVAL = make("Generous Revival", "Sorcery", "{2}{W}", 3, "Return target creature card with mana value 3 or less "
               "from your graveyard to the battlefield with an additional +1/+1 counter on it.\nFlashback {4}{W}",
               keywords=["Flashback"])
RAISE = make("Raise the Past", "Sorcery", "{2}{W}", 3, "Return all creature cards with mana value 2 or less from your "
             "graveyard to the battlefield.")
RESTORE = make("Restore with Empathy", "Instant", "{3}{W}", 4, "Return target permanent card from your graveyard to "
               "your hand. You gain 4 life.")
GHOUL = make("Blessed Ghoul", f"Creature {DASH} Zombie Cleric", "{1}{W}", 2,
             "{2}{W/B}: Return this card from your graveyard to your hand.", "2", "2")
NECRO = make("Theoretical Necromancer", f"Creature {DASH} Vampire Warlock", "{2}{B}", 3,
             "{3}{B}, Exile this card from your graveyard: Return another target creature card from your graveyard to "
             "your hand.", "2", "3")
GALLIA = make("Gallia, Tragic Host", f"Legendary Creature {DASH} Zombie Satyr", "{2}{B}", 3,
              "{4}{B}, Exile another creature card from your graveyard: Return this card from your graveyard to the "
              "battlefield tapped with a +1/+1 counter on her.", "3", "3")
REPRISER = make("Grim Repriser", f"Creature {DASH} Zombie Bard", "{B}{R}", 2, "Prowess\n{B}{R}: Return this card from "
                "your graveyard to the battlefield with a finality counter on it. Activate only if an opponent has "
                "been dealt noncombat damage this turn.", "2", "2", ["Prowess"])
PHOENIX = make("Darklight Phoenix", f"Creature {DASH} Phoenix", "{2}{R}", 3, "Flying, haste\nAt the beginning of combat "
               "on your turn, if two or more creatures died this turn, return this card from your graveyard to the "
               "battlefield.", "3", "2", ["Flying", "Haste"])
MARWYN = make("Marwyn, the Preserver", f"Legendary Creature {DASH} Elf Druid", "{1}{G}", 2,
              "Lands you control have hexproof.\n{2}: Return target land card from your graveyard to your hand.",
              "2", "2")
CULTIVATOR = make("Carnivorous Cultivator", f"Creature {DASH} Elf Warlock", "{2}{G}", 3, "Whenever this creature "
                  "deals combat damage to a player, return target land card from your graveyard to your hand.",
                  "2", "2")
TWINNED = make("Twinned Vision", "Instant", "{1}{U/R}", 2, "Draw a card. If this spell wasn't cast from your hand, draw "
               "two cards instead.\nFlashback—{1}{U/R}{U/R}, Discard a card.", keywords=["Flashback"])
JAB = make("Jab", "Instant", "{R}", 1, "Jab deals 1 damage to target opponent.")
BEAR = W["Test Bear"]
CUB = make("Cub", CRE, "{W}", 1, "", "1", "1")
OGRE = make("Ogre", CRE, "{2}{W}", 3, "", "3", "3")
GIANT = make("Giant", CRE, "{4}{W}", 5, "", "5", "5")


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


class ParseTests(unittest.TestCase):
    def test_spells(self):
        self.assertEqual(REVIVAL.reanimate, ("target", "creature", 3, "battlefield", 1))
        self.assertEqual(RAISE.reanimate, ("all", "creature", 2, "battlefield", 0))
        self.assertEqual((RESTORE.reanimate, RESTORE.spell_life), (("target", "permanent", 99, "hand", 0), 4))

    def test_graveyard_abilities(self):
        self.assertEqual(GHOUL.gy_return[1:], ("hand", False, 0, "", ""))
        self.assertEqual(GALLIA.gy_return[1:], ("battlefield", True, 1, "exile_creature", ""))
        self.assertEqual(REPRISER.gy_return[1:], ("battlefield", False, 0, "", "noncombat"))
        self.assertTrue(REPRISER.finality)
        self.assertEqual(NECRO.gy_ability[1], (("return", "creature", "hand", True),))

    def test_others(self):
        self.assertTrue(PHOENIX.phoenix)
        self.assertEqual([ab[4] for ab in MARWYN.abilities], [(("return", "land", "hand", False),)])
        self.assertTrue(CULTIVATOR.combat_land_return)
        self.assertTrue(TWINNED.flashback)
        self.assertEqual((TWINNED.flashback_discard, TWINNED.alt_draws, TWINNED.draws), (True, 2, 1))


class SpellTests(unittest.TestCase):
    def test_revival_returns_the_best_creature_with_counter(self):
        me, opp = player(), player("Gegner")
        me.graveyard[:] = [CUB, OGRE, GIANT]
        bt._resolve(me, opp, REVIVAL, 3, entry())
        self.assertEqual([(c.card.name, c.bonus) for c in me.creatures], [("Ogre", 1)])
        self.assertEqual(sorted(c.name for c in me.graveyard), ["Cub", "Generous Revival", "Giant"])

    def test_raise_the_past_returns_all_small(self):
        me, opp = player(), player("Gegner")
        me.graveyard[:] = [CUB, BEAR, OGRE]
        bt._resolve(me, opp, RAISE, 3, entry())
        self.assertEqual(sorted(c.card.name for c in me.creatures), ["Cub", "Test Bear"])

    def test_restore_to_hand_and_life(self):
        me, opp = player(), player("Gegner")
        me.graveyard[:] = [CUB, GIANT, JAB]
        bt._resolve(me, opp, RESTORE, 3, entry())
        self.assertEqual((me.hand, me.life), ([GIANT], 24))

    def test_no_target_no_cast(self):
        me, opp = player(), player("Gegner")
        me.lands, me.hand = [PLAINS] * 3, [REVIVAL]
        me.graveyard[:] = [GIANT]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["main1"], me.hand), ([], [REVIVAL]))

    def test_revival_per_flashback(self):
        me, opp = player(), player("Gegner")
        me.lands = [PLAINS] * 5
        me.graveyard[:] = [REVIVAL, BEAR]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["main1"], ["Generous Revival"])
        self.assertEqual(([c.card.name for c in me.creatures], me.graveyard), (["Test Bear"], []))


class GraveyardAbilityTests(unittest.TestCase):
    def test_ghoul_back_to_hand_at_end_of_opponents_turn(self):
        dfn, act = player("Gegner"), player()
        dfn.graveyard[:], dfn.open = [GHOUL], [WH] * 3
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual((dfn.hand, dfn.graveyard), ([GHOUL], []))

    def test_necromancer_exiles_itself_for_another(self):
        dfn, act = player("Gegner"), player()
        dfn.graveyard[:], dfn.open = [NECRO, BEAR, OGRE], [B] * 4
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual((dfn.hand, dfn.graveyard), ([OGRE], [BEAR]))

    def test_necromancer_needs_another_creature(self):
        dfn, act = player("Gegner"), player()
        dfn.graveyard[:], dfn.open = [NECRO, PLAINS], [B] * 4
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual(dfn.graveyard, [NECRO, PLAINS])

    def test_gallia_returns_tapped_with_counter(self):
        dfn, act = player("Gegner"), player()
        dfn.graveyard[:], dfn.open = [GALLIA, CUB, OGRE], [B] * 5
        bt.end_step_instants(dfn, act, entry(), 6)
        gallia = dfn.creatures[0]
        self.assertEqual((gallia.card.name, gallia.tapped, gallia.bonus), ("Gallia, Tragic Host", True, 1))
        self.assertEqual(dfn.graveyard, [OGRE])  # die schwaechste andere Kreaturkarte wurde exiliert

    def test_repriser_needs_noncombat_damage(self):
        dfn, act = player("Gegner"), player()
        dfn.graveyard[:], dfn.open = [REPRISER], [B, ("R",)]
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual(dfn.graveyard, [REPRISER])
        dfn.dealt_direct += 1  # in diesem Zug Schaden ausserhalb des Kampfs
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual((dfn.graveyard, dfn.creatures[0].finality), ([], True))

    def test_finality_exiles_instead_of_dying(self):
        me = player()
        rep = bt.Creature(REPRISER, 0)
        rep.finality, rep.dead = True, True
        me.creatures = [rep]
        bt.bury((me,), entry())
        self.assertEqual((me.creatures, me.graveyard), ([], []))

    def test_repriser_after_ingris_ping_in_own_turn(self):
        ingris = make("Ingris", f"Creature {DASH} Sphinx", "{B}{R}{R}", 3, "Flying\nWhenever a creature you control "
                      "attacks, that creature deals 1 damage to each opponent.", "1", "4", ["Flying"])
        me, opp = player(), player("Gegner")
        me.lands = [SWAMP, card_info(_card("Mountain", f"Basic Land {DASH} Mountain", text="({T}: Add {R}.)",
                                           produced=["R"]))[0]]
        me.creatures, me.graveyard[:] = [bt.Creature(ingris, 0)], [REPRISER]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual([c.card.name for c in me.creatures], ["Ingris", "Grim Repriser"])


class PhoenixAndLandTests(unittest.TestCase):
    def test_phoenix_returns_after_two_deaths(self):
        me, opp = player(), player("Gegner")
        me.graveyard[:] = [PHOENIX]
        me.deaths, opp.deaths = 1, 1  # zwei Kreaturen in diesem Zug gestorben
        me.deaths_mark = opp.deaths_mark = 0
        bt.phoenix_check(me, opp, 5, entry())
        self.assertEqual((me.creatures[0].card.name, me.graveyard), ("Darklight Phoenix", []))

    def test_phoenix_stays_after_one_death(self):
        me, opp = player(), player("Gegner")
        me.graveyard[:] = [PHOENIX]
        me.deaths = 1
        bt.phoenix_check(me, opp, 5, entry())
        self.assertEqual(me.graveyard, [PHOENIX])

    def test_phoenix_in_a_real_turn(self):
        me, opp = player(), player("Gegner")
        sweep = make("Pyroclasm", "Sorcery", "{1}{W}", 2, "Pyroclasm deals 2 damage to each creature.")
        me.lands, me.hand, me.graveyard[:] = [PLAINS] * 2, [sweep], [PHOENIX]
        opp.creatures = [bt.Creature(BEAR, 0), bt.Creature(CUB, 0)]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["damage"], opp.life), (3, 17))

    def test_deaths_from_earlier_turns_do_not_count(self):
        me, opp = player(), player("Gegner")
        me.graveyard[:], me.deaths = [PHOENIX], 2  # in frueheren Zuegen gestorben
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(me.graveyard, [PHOENIX])

    def test_marwyn_not_with_enough_lands(self):
        dfn, act = player("Gegner"), player()
        dfn.lands = [PLAINS] * 6
        dfn.creatures, dfn.graveyard[:], dfn.open = [bt.Creature(MARWYN, 0)], [SWAMP], [WH] * 2
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual(dfn.graveyard, [SWAMP])

    def test_marwyn_returns_a_land_if_needed(self):
        dfn, act = player("Gegner"), player()
        dfn.creatures, dfn.graveyard[:], dfn.open = [bt.Creature(MARWYN, 0)], [SWAMP], [WH] * 2
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual((dfn.hand, dfn.graveyard), ([SWAMP], []))

    def test_cultivator_returns_a_land_on_combat_damage(self):
        me, opp = player(), player("Gegner")
        me.creatures, me.graveyard[:] = [bt.Creature(CULTIVATOR, 0)], [SWAMP]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(me.hand, [SWAMP])


class TwinnedVisionTests(unittest.TestCase):
    def test_flashback_discards_and_draws_two(self):
        dfn, act = player("Gegner", library=[BEAR] * 5), player()
        dfn.lands = [ISLAND] * 6
        dfn.graveyard[:], dfn.hand, dfn.open = [TWINNED], [PLAINS], [U] * 3
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual((dfn.hand, dfn.graveyard), ([BEAR, BEAR], [PLAINS]))

    def test_no_flashback_without_a_card_to_discard(self):
        dfn, act = player("Gegner", library=[BEAR] * 5), player()
        dfn.graveyard[:], dfn.open = [TWINNED], [U] * 3
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual(dfn.graveyard, [TWINNED])

    def test_from_hand_draws_one(self):
        dfn, act = player("Gegner", library=[BEAR] * 5), player()
        dfn.hand, dfn.open = [TWINNED], [U] * 2
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual((dfn.hand, dfn.graveyard), ([BEAR], [TWINNED]))


class GameTests(unittest.TestCase):
    def test_games(self):
        deck = [PLAINS] * 9 + [SWAMP] * 8 + [REVIVAL, RAISE, RESTORE, GHOUL, NECRO, GALLIA, PHOENIX, MARWYN,
                                             CULTIVATOR, BEAR, CUB, OGRE] * 2
        random.seed(37)
        r = bt.battle(deck, deck, 60, on_draw=False)
        self.assertEqual(r["wins"] + r["losses"] + r["draws"], 60)


if __name__ == "__main__":
    unittest.main()
