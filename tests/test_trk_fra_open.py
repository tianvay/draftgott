"""Nachtraege TRK/FRA (Nutzer 2026-11-15): Hit It! mit dem aktuellen Scryfall-Wortlaut ("look at the top five" statt
"reveal the top five") und Face Yourself (FRA): Token-Kopien aller Kreaturen eines Spielers mit Haste, die zu Beginn
jedes Endsegments geopfert werden, wenn ihr Beherrscher keinen Planeswalker hat. Gewirkt wird nur fuer Lethal oder mit
eigenem Planeswalker (Nutzer). Nur Kampfmodell. Kartentexte aus TRK und FRA."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]

RAW = {
    "hit_it": _card("Hit It!", "Enchantment", "{1}{R}{G}", 3, "RG", "Creatures you control have haste.\nWhen this "
                    "enchantment enters, look at the top five cards of your library. Put a land card from among them "
                    "onto the battlefield tapped and the rest into your graveyard."),
    "face": _card("Face Yourself", "Sorcery", "{5}{R}{R}", 7, "R", "For each creature target player controls, create a "
                  "token that's a copy of that creature, except it has haste and \"At the beginning of the end step, "
                  "if you don't control a planeswalker, sacrifice this token.\""),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}
OGRE = card_info(_card("Ogre", f"Creature {DASH} Ogre", "{2}{R}", 3, "R", "", [], "3", "3"))[0]
BIG = card_info(_card("Giant", f"Creature {DASH} Giant", "{4}{R}", 5, "R", "", [], "5", "5"))[0]
ELF = card_info(_card("Elf", f"Creature {DASH} Elf", "{G}", 1, "G", "", [], "1", "1"))[0]
LEGEND = card_info(_card("Test Legend", f"Legendary Creature {DASH} Human", "{3}{R}", 4, "R", "", [], "4", "4"))[0]
DRAINER = card_info(_card("Test Drainer", f"Creature {DASH} Vampire", "{2}{B}", 3, "B", "When this creature enters, "
                          "it deals 2 damage to each opponent.", [], "2", "2"))[0]


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    p.now = 3
    return p


def pair(library=None):
    me, opp = player(library=library), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


def put(p, card, entered=0, tapped=False):
    c = bt.Creature(card, entered)
    c.gy, c.ctl, c.tapped = p.graveyard, p, tapped
    p.creatures.append(c)
    return c


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertEqual(C["hit_it"].reveal_lands, ("top", 5))
        self.assertTrue(C["face"].face_copy)
        self.assertEqual((OGRE.face_copy, OGRE.end_sacrifice_pw, C["face"].end_sacrifice_pw), (False, False, False))

    def test_coverage(self):
        for key in RAW:
            self.assertEqual([l for _c, _m, l in analyze_card(RAW[key])], [], key)


class HitItTests(unittest.TestCase):
    def test_new_wording_puts_land(self):
        me, opp = pair(library=[OGRE, PLAINS, ELF, BIG, OGRE, BIG])
        bt.card_effects(me, opp, C["hit_it"], 3, entry())
        self.assertEqual(([l.name for l in me.lands], me.library), (["Plains"], [BIG]))
        self.assertEqual(len([c for c in me.graveyard if c is not C["hit_it"]]), 4)


class FaceYourselfEffectTests(unittest.TestCase):
    def test_copies_stronger_side_with_haste(self):
        me, opp = pair()
        put(me, ELF)
        put(opp, BIG)
        put(opp, OGRE)
        bt.card_effects(me, opp, C["face"], 3, entry())
        toks = [c for c in me.creatures if c.card.is_token]
        self.assertEqual(sorted(c.card.name for c in toks), ["Giant", "Ogre"])
        self.assertTrue(all(c.has("haste") and c.card.end_sacrifice_pw for c in toks))
        self.assertTrue(all(bt.can_attack(c, 3) for c in toks))
        self.assertEqual(len(opp.creatures), 2)

    def test_copies_own_side_when_stronger(self):
        me, opp = pair()
        put(me, BIG)
        put(opp, ELF)
        bt.card_effects(me, opp, C["face"], 3, entry())
        self.assertEqual(sorted(c.card.name for c in me.creatures), ["Giant", "Giant"])

    def test_own_legend_not_copied(self):
        me, opp = pair()
        put(me, LEGEND)
        put(me, OGRE)
        put(opp, ELF)
        bt.card_effects(me, opp, C["face"], 3, entry())
        self.assertEqual(sorted(c.card.name for c in me.creatures), ["Ogre", "Ogre", "Test Legend"])

    def test_copies_enter_with_triggers(self):
        me, opp = pair()
        put(opp, DRAINER)
        bt.card_effects(me, opp, C["face"], 3, entry())
        self.assertEqual(opp.life, 18)


class FaceYourselfEndStepTests(unittest.TestCase):
    def _token(self, p):
        return put(p, BIG._replace(is_token=True, haste=True, end_sacrifice_pw=True), 3)

    def test_sacrificed_without_planeswalker(self):
        me, opp = pair()
        tok = self._token(me)
        bt.end_step_sacrifices((me, opp), entry())
        self.assertTrue(tok.dead)

    def test_kept_with_jace(self):
        me, opp = pair()
        tok = self._token(me)
        me.jace.loyalty = 2
        bt.end_step_sacrifices((me, opp), entry())
        self.assertFalse(tok.dead)

    def test_plain_end_sacrifice_unchanged(self):
        me, opp = pair()
        tok = put(me, BIG._replace(is_token=True, end_sacrifice=True), 3)
        me.jace.loyalty = 2
        bt.end_step_sacrifices((me, opp), entry())
        self.assertTrue(tok.dead)


class FaceYourselfCastTests(unittest.TestCase):
    def test_cast_for_lethal(self):
        me, opp = pair()
        put(opp, BIG, tapped=True)
        opp.life = 5
        self.assertTrue(bt.face_ok(me, opp))
        me.hand = [C["face"]]
        self.assertIn(C["face"], bt.main_phase_spells(me, opp))

    def test_not_without_lethal(self):
        me, opp = pair()
        put(opp, BIG, tapped=True)
        me.hand = [C["face"]]
        self.assertFalse(bt.face_ok(me, opp))
        self.assertNotIn(C["face"], bt.main_phase_spells(me, opp))

    def test_cast_with_planeswalker(self):
        me, opp = pair()
        put(opp, BIG)
        me.jace.loyalty = 3
        self.assertTrue(bt.face_ok(me, opp))

    def test_not_without_creatures(self):
        me, opp = pair()
        me.jace.loyalty = 3
        self.assertFalse(bt.face_ok(me, opp))


if __name__ == "__main__":
    unittest.main()
