"""Chandra, Torch of Defiance +1 (Nutzer-Entscheidung): die exilierte Karte wird gewirkt, wenn sie kein Land und mit dem
freien Mana bezahlbar ist; die 2 Schaden nur, wenn sie Lethal sind oder die Karte nicht gewirkt wird. Die Faehigkeit
kommt erst nach den Zaubern aus Main 1 (dann steht das freie Mana fest)."""
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import _card
from tests.test_package_fra_d import DASH, MOUNTAIN, OGRE, entry, pair

CHANDRA = card_info(dict(_card("Chandra, Torch of Defiance", f"Legendary Planeswalker {DASH} Chandra", "{2}{R}{R}", 4,
                               "R", "+1: Exile the top card of your library. You may cast that card. If you don't, "
                               "Chandra deals 2 damage to each opponent.\n+1: Add {R}{R}.\n−3: Chandra deals 4 damage "
                               "to target creature.\n−7: You get an emblem with \"Whenever you cast a spell, this "
                               "emblem deals 5 damage to any target.\""), loyalty="4"))[0]
PLUS = next(a for a in CHANDRA.pw_abilities if ("mill_top",) in a[1])


def chandra(me):
    w = bt.Walker(CHANDRA, 0)
    me.walkers = [w]
    return w


class ChandraTests(unittest.TestCase):
    def test_casts_a_payable_spell(self):
        me, opp = pair()
        w = chandra(me)
        me.library, me.open = [OGRE], [MOUNTAIN.land_colors] * 3
        bt.activate_pw(me, opp, w, PLUS, 5, entry())
        self.assertEqual(([c.card.name for c in me.creatures], opp.life, me.open), (["Ogre"], 20, []))

    def test_land_means_damage(self):
        me, opp = pair()
        w = chandra(me)
        me.library, me.open = [MOUNTAIN], [MOUNTAIN.land_colors] * 3
        bt.activate_pw(me, opp, w, PLUS, 5, entry())
        self.assertEqual((me.creatures, opp.life, me.library), ([], 18, []))

    def test_not_payable_means_damage(self):
        me, opp = pair()
        w = chandra(me)
        me.library, me.open = [OGRE], [MOUNTAIN.land_colors] * 2
        bt.activate_pw(me, opp, w, PLUS, 5, entry())
        self.assertEqual((me.creatures, opp.life), ([], 18))

    def test_lethal_damage_first(self):
        me, opp = pair()
        w = chandra(me)
        opp.life = 2
        me.library, me.open = [OGRE], [MOUNTAIN.land_colors] * 3
        bt.activate_pw(me, opp, w, PLUS, 5, entry())
        self.assertEqual((me.creatures, opp.life), ([], 0))

    def test_waits_until_after_main1(self):
        me, opp = pair()
        w = chandra(me)
        bt.pw_phase(me, opp, 5, entry(), "main1")
        self.assertFalse(w.used)


class GoneTargetTests(unittest.TestCase):
    """608.2b: ist das Ziel schon weg (z. B. durch das Emblem von Chandra beim Wirken), loest das Removal nicht auf."""

    def test_removal_without_its_target_does_nothing(self):
        from tests.test_package_fra_e import DOOM
        from tests.test_package_fra_d import on_board
        me, opp = pair()
        ogre = on_board(opp, OGRE)
        opp.creatures.remove(ogre)  # schon gestorben und begraben
        e = entry()
        bt.cast_removal(DOOM, me, opp, e, 5, target=ogre)
        self.assertIn("ohne Ziel", e["events"][-1])

    def test_exile_without_its_target_does_not_crash(self):
        from tests.test_package_fra_d import make, on_board
        exile = make("Banish", "Instant", "{1}{W}", 2, "Exile target creature.")
        me, opp = pair()
        ogre = on_board(opp, OGRE)
        opp.creatures.remove(ogre)
        bt.cast_removal(exile, me, opp, entry(), 5, target=ogre)
        self.assertEqual(opp.creatures, [])


if __name__ == "__main__":
    unittest.main()
