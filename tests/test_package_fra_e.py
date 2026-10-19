"""FRA-Paket E: Emrakul, the Exigent Doom (Wirken enttappt die Laender; {3}, aus der Hand exilieren: ein Land liefert
{C}{C}, Emrakul bleibt aus dem Exil spielbar; Ward "drei bleibende Karten opfern" nur gegen drohendes Lethal),
Omnipresence (Handkarten bis zur Zahl der eigenen Kreaturen kostenlos), Uldaros Theorix (Kopien aus dem Friedhof bis
Manawert 6), Codie (prepared-Zauber wird kopiert), Fblthp, Impossibly Lost (Kampfschaden im eigenen Zug: zwei ziehen,
leere Bibliothek gewinnt, Fblthp kommt in die Bibliothek)."""
import unittest

from components import battle as bt
from components import simulation as sim
from tests.test_package_fra_d import (BOLT, CODIE, DRAWER, FOREST, HAWK, ISLAND, OGRE, PLAINS, SCHOLAR, SWAMP, TITAN,
                                      CRE, DASH, entry, make, on_board, pair)

EMRAKUL = make("Emrakul, the Exigent Doom", f"Legendary Creature {DASH} Eldrazi", "{10}", 10, "When you cast this "
               "spell, untap all lands you control.\nFlying, trample\nWard—Sacrifice three permanents.\n{3}, Exile this "
               "card from your hand: Target land gains \"{T}: Add {C}{C}\" until this card is cast from exile. You may "
               "cast this card for as long as it remains exiled.", "12", "12", ["Flying", "Trample", "Ward"],
               colors="")
OMNI = make("Omnipresence", "Enchantment", "{5}{G}{G}{G}", 8, "You may cast spells with mana value less than or equal "
            "to the number of creatures you control from your hand without paying their mana costs.", colors="G")
ULDAROS = make("Uldaros Theorix", f"Legendary Creature {DASH} Elder Sphinx", "{3}{U}{B}{B}", 6, "Flying\nWhen Uldaros "
               "Theorix enters, if you cast him, exile up to one target nonland card of each card type from your "
               "graveyard. Copy those cards. You may cast any number of spells with total mana value 6 or less from "
               "among the copies without paying their mana costs. (Permanent spells cast this way become tokens.)",
               "5", "5", ["Flying"], colors="UB")
FBLTHP = make("Fblthp, Impossibly Lost", f"Legendary Creature {DASH} Homunculus", "{1}{U}", 2, "When one or more of "
              "your opponents are dealt combat damage during your turn, draw two cards. If your library has no cards "
              "in it, you win the game. Fblthp's owner shuffles him into their library. (If you draw from an empty "
              "library this way, you still win the game.)", "1", "1", colors="U")
STUDY = make("Study", "Sorcery", "{1}{U}", 2, "Draw two cards.", colors="U")
DOOM = make("Doom", "Instant", "{1}{B}", 2, "Destroy target creature.", colors="B")
BEAR = make("Bear", CRE, "{1}{G}", 2, "", "2", "2", colors="G")
SPIRIT = make("Spirit", CRE, "", 0, "", "1", "1")._replace(is_token=True)


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertTrue(EMRAKUL.cast_untap_lands)
        self.assertTrue(EMRAKUL.hand_exile_land)
        self.assertEqual(EMRAKUL.ward, ("sac", 3))
        self.assertTrue(OMNI.omni_free)
        self.assertEqual(ULDAROS.uldaros_cast, 6)
        self.assertTrue(CODIE.codie_copy)
        self.assertEqual(FBLTHP.fblthp_lost, 2)


class FreeSpellTests(unittest.TestCase):
    def test_emrakul_free_when_lands_pay(self):
        hand = sim.free_spells([EMRAKUL], 0, [("G",)] * 10, False)
        self.assertEqual((hand[0].alts, sim.original(hand[0])), (((0, ()),), EMRAKUL))

    def test_emrakul_not_free_without_ten_lands(self):
        self.assertEqual(sim.free_spells([EMRAKUL], 0, [("G",)] * 9, False), [EMRAKUL])

    def test_omnipresence_chain(self):  # zwei Kreaturen: Drawer (2) frei, danach drei Kreaturen: Hawk (3) frei
        hand = sim.free_spells([HAWK, DRAWER, TITAN], 2, [], True)
        self.assertEqual([c.alts for c in hand[:2]], [((0, ()),)] * 2)
        self.assertEqual(hand[2], TITAN)

    def test_omnipresence_cast_rule(self):
        self.assertFalse(sim.omni_ok(OMNI, [OMNI, OGRE], 1))
        self.assertTrue(sim.omni_ok(OMNI, [OMNI, DRAWER], 2))
        self.assertFalse(sim.omni_ok(OMNI, [OMNI, TITAN], 2))  # nichts wird kostenlos
        self.assertTrue(sim.omni_ok(OMNI, [OMNI, FOREST], 0))  # letzte Nicht-Landkarte


class EmrakulTests(unittest.TestCase):
    def test_cast_untaps_the_lands(self):
        me, opp = pair()
        me.lands, me.hand = [FOREST] * 10, [EMRAKUL, TITAN]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(sorted(c.card.name for c in me.creatures), ["Emrakul, the Exigent Doom", "Titan"])

    def test_exile_from_hand_in_main2(self):
        me, opp = pair()
        me.lands, me.hand = [FOREST, FOREST, FOREST, ISLAND], [EMRAKUL]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((me.hand, [c for c, _l in me.impulse], me.cc_land), ([], [EMRAKUL], FOREST))

    def test_keeps_it_when_castable_soon(self):
        me, opp = pair()
        me.lands, me.hand = [FOREST] * 8, [EMRAKUL]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(me.hand, [EMRAKUL])

    def test_cc_land_and_cast_from_exile(self):
        me, opp = pair()
        me.lands, me.cc_land, me.impulse = [FOREST] * 9, FOREST, [(EMRAKUL, 10 ** 9)]
        self.assertEqual(sorted(bt._mana(me, 5)[0]), [("C",)] * 2 + [("G",)] * 8)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(([c.card.name for c in me.creatures], me.impulse, me.cc_land),
                         (["Emrakul, the Exigent Doom"], [], None))


class WardSacrificeTests(unittest.TestCase):
    def test_pays_against_lethal(self):
        me, opp = pair()
        emrakul = on_board(me, EMRAKUL)
        token = on_board(opp, SPIRIT)
        bear = on_board(opp, BEAR)
        opp.life, opp.lands, opp.open = 10, [PLAINS] * 5 + [SWAMP], [SWAMP.land_colors, PLAINS.land_colors]
        opp.hand = [DOOM]
        bt.cast_removal(DOOM, opp, me, entry(), 6)
        self.assertTrue(emrakul.dead and token.dead)
        self.assertFalse(bear.dead)
        self.assertEqual(len(opp.lands), 4)  # Token, dann zwei ueberzaehlige Laender

    def test_not_without_lethal(self):
        me, opp = pair()
        emrakul = on_board(me, EMRAKUL)
        on_board(opp, SPIRIT)
        opp.lands, opp.open = [PLAINS] * 5 + [SWAMP], [SWAMP.land_colors, PLAINS.land_colors]
        bt.cast_removal(DOOM, opp, me, entry(), 6)
        self.assertFalse(emrakul.dead)


class OmnipresenceTests(unittest.TestCase):
    def test_free_chain_in_battle(self):
        me, opp = pair()
        me.perms = [OMNI]
        on_board(me, BEAR)
        on_board(me, BEAR)
        me.hand = [HAWK, DRAWER]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        names = [c.card.name for c in me.creatures]
        self.assertIn("Hawk", names)
        self.assertIn("Card Drawer", names)

    def test_not_cast_with_one_creature(self):
        me, opp = pair()
        on_board(me, BEAR)
        me.lands, me.hand = [FOREST] * 8, [OMNI, OGRE]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertIn(OMNI, me.hand)

    def test_cast_as_last_card(self):
        me, opp = pair()
        me.lands, me.hand = [FOREST] * 8, [OMNI]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(me.perms, [OMNI])


class UldarosTests(unittest.TestCase):
    def test_copies_removal_first_then_most_mana_value(self):
        me, opp = pair()
        hawk = on_board(opp, HAWK)
        me.graveyard = [BOLT, OGRE, DRAWER, STUDY]
        me.lands, me.hand = [ISLAND, SWAMP, SWAMP, PLAINS, PLAINS, PLAINS], [ULDAROS]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertNotIn(hawk, opp.creatures)
        self.assertEqual(me.graveyard, [DRAWER])  # Bolt (1) + Ogre (3) + Study (2) = 6
        ogre = next(c for c in me.creatures if c.card.name == "Ogre")
        self.assertTrue(ogre.card.is_token)
        self.assertEqual(len(me.library), 18)

    def test_removal_before_mana_value(self):
        me, opp = pair()
        on_board(opp, HAWK)
        big = make("Big Draw", "Instant", "{4}{U}{U}", 6, "Draw three cards.", colors="U")
        me.graveyard = [BOLT, big]
        self.assertEqual(bt.uldaros_pick(me, opp, 6), [BOLT])

    def test_not_when_not_cast(self):
        me, opp = pair()
        me.graveyard = [OGRE]
        c = bt.Creature(ULDAROS, 5)
        me.creatures.append(c)
        bt.creature_enters(me, c, 5, entry(), opp, cast=False)
        self.assertEqual(me.graveyard, [OGRE])


class CodieCopyTests(unittest.TestCase):
    def test_prepared_spell_is_copied(self):
        me, opp = pair()
        scholar = on_board(me, SCHOLAR)
        on_board(me, CODIE)
        bt._resolve(me, opp, SCHOLAR.prepared[1], 5, entry())
        self.assertEqual((len(me.library), scholar.prepared), (18, False))

    def test_without_codie_once(self):
        me, opp = pair()
        on_board(me, SCHOLAR)
        bt._resolve(me, opp, SCHOLAR.prepared[1], 5, entry())
        self.assertEqual(len(me.library), 19)


class FblthpTests(unittest.TestCase):
    def test_draws_and_shuffles_back(self):
        me, opp = pair()
        on_board(me, OGRE)
        on_board(me, FBLTHP)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertNotIn("Fblthp, Impossibly Lost", [c.card.name for c in me.creatures])
        self.assertIn(FBLTHP, me.library)
        self.assertEqual(len(me.library), 19)

    def test_empty_library_wins(self):
        me, opp = pair()
        on_board(me, OGRE)
        on_board(me, FBLTHP)
        me.library = [PLAINS, PLAINS]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertTrue(opp.lost)


if __name__ == "__main__":
    unittest.main()
