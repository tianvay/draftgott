"""Star Trek (TRK), Paket K (Nutzer 2026-11-01): Kicker (702.33) und Counterspells - Highly Illogical (ohne Kicker
nur Manawert 2 oder weniger, mit Kicker {1}{U} jeder Zauber), Eject the Warp Core (Kicker: ein Artefakt oder eine
Kreatur opfern, dann -6/-6 statt -2/-2), Mirror Universe Intrusion (Kopie mit Menace, mit Kicker {4}{U}{B} von jeder
gegnerischen Kreatur), Consider the Prime Directive (Moduswoerter wie "Interfere —" vor dem Modustext). Nur
Kampfmodell. Kartentexte aus TRK."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from components.mana import cost_alternatives
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]
CRE = f"Creature {DASH} Test"
U, B = ("U",), ("B",)

RAW = {
    "illogical": _card("Highly Illogical", "Instant", "{1}{U}", 2, "U", "Kicker {1}{U} (You may pay an additional "
                       "{1}{U} as you cast this spell.)\nCounter target spell with mana value 2 or less. If this spell "
                       "was kicked, instead counter target spell."),
    "eject": _card("Eject the Warp Core", "Instant", "{1}{B}", 2, "B", f"Kicker{DASH}Sacrifice an artifact or creature. "
                   "(You may sacrifice an artifact or creature in addition to any other costs as you cast this "
                   "spell.)\nTarget creature gets -2/-2 until end of turn. If this spell was kicked, that creature gets "
                   "-6/-6 until end of turn instead."),
    "mirror": _card("Mirror Universe Intrusion", "Sorcery", "{1}{U}{B}", 3, "UB", "Kicker {4}{U}{B} (You may pay an "
                    "additional {4}{U}{B} as you cast this spell.)\nCreate a token that's a copy of target creature an "
                    "opponent controls, except it has menace. If this spell was kicked, instead for each creature "
                    "target opponent controls, create a token that's a copy of that creature, except it has menace."),
    "prime": _card("Consider the Prime Directive", "Instant", "{2}{U}", 3, "U", f"Choose one {DASH}\n• Interfere {DASH} "
                   "Counter target spell unless its controller pays {3}.\n• Observe — Tap up to one target creature "
                   "and put a stun counter on it. Draw a card. (If a permanent with a stun counter would become "
                   "untapped, remove one from it instead.)"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}


def make(name, cost, cmc, text="", power=None, toughness=None, type_line=CRE, colors="R", keywords=()):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


BEAR = make("Bear", "{1}{R}", 2, "", "2", "2")
OGRE = make("Ogre", "{2}{R}", 3, "", "3", "3")
GIANT = make("Giant", "{3}{R}", 4, "", "4", "4")
FLYER = make("Flyer", "{2}{R}", 3, "Flying", "2", "2", keywords=["Flying"])
BOLT = make("Bolt", "{R}", 1, "Bolt deals 3 damage to any target.", type_line="Instant")
TOKEN = make("Officer", "", 0, "", "1", "1")._replace(is_token=True)


def player(name="Wir"):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], [PLAINS] * 20
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


def open_lines(key):
    return [l for _c, _m, l in analyze_card(RAW[key])]


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertEqual(C["illogical"].counter, ("any", (), 0))
        self.assertEqual(C["illogical"].counter_mv, 2)
        self.assertEqual(C["illogical"].kicker, cost_alternatives("{1}{U}"))
        self.assertEqual(C["eject"].removal, ("minus", 2, (("kicked_sac", 6),), False, "spell", False))
        self.assertTrue(C["eject"].kicker_sac)
        self.assertTrue(C["mirror"].mirror_copy)
        self.assertEqual(C["mirror"].kicker, cost_alternatives("{4}{U}{B}"))
        self.assertEqual(C["prime"].choices[1][0].counter, ("any", (), 3))
        self.assertEqual((OGRE.counter_mv, OGRE.kicker, OGRE.kicker_sac, OGRE.mirror_copy), (0, (), False, False))

    def test_coverage(self):
        for key in RAW:
            self.assertEqual(open_lines(key), [], key)


class HighlyIllogicalTests(unittest.TestCase):
    def test_small_spell_without_kicker(self):
        me, opp = pair()
        opp.hand, opp.open, opp.life = [C["illogical"]], [U] * 2, 3
        bt._resolve(me, opp, BOLT, 3, entry())
        self.assertEqual((opp.life, opp.hand, opp.open), (3, [], []))

    def test_bigger_spell_needs_kicker(self):
        me, opp = pair()
        opp.hand, opp.open = [C["illogical"]], [U] * 3
        bt._resolve(me, opp, OGRE, 3, entry())
        self.assertEqual((len(me.creatures), opp.hand), (1, [C["illogical"]]))
        opp.open = [U] * 4
        bt._resolve(me, opp, GIANT, 3, entry())
        self.assertEqual((len(me.creatures), GIANT in me.graveyard, opp.open), (1, True, []))


class EjectTests(unittest.TestCase):
    def test_small_target_no_kicker(self):
        me, opp = pair()
        me.clues = 1
        on_board(opp, BEAR)
        bt.cast_removal(C["eject"], me, opp, entry(), 3)
        self.assertEqual((opp.creatures, me.clues), ([], 1))

    def test_kicked_with_clue(self):
        me, opp = pair()
        me.clues = 1
        on_board(opp, BEAR)
        on_board(opp, GIANT)
        bt.cast_removal(C["eject"], me, opp, entry(), 3)
        self.assertEqual(([c.card for c in opp.creatures], me.clues), ([BEAR], 0))

    def test_kicked_with_small_token(self):
        me, opp = pair()
        tok = on_board(me, TOKEN)
        on_board(opp, GIANT)
        bt.cast_removal(C["eject"], me, opp, entry(), 3)
        self.assertEqual((opp.creatures, tok in me.creatures), ([], False))

    def test_no_fodder_no_big_target(self):
        me, opp = pair()
        on_board(me, OGRE)  # echte Kreatur: wird nie geopfert
        on_board(opp, GIANT)
        self.assertFalse(bt.has_target(C["eject"], me, opp))
        on_board(opp, BEAR)
        self.assertTrue(bt.has_target(C["eject"], me, opp))


class MirrorTests(unittest.TestCase):
    def test_one_copy_with_menace(self):
        me, opp = pair()
        on_board(opp, BEAR)
        on_board(opp, GIANT)
        me.open = [U, B, U]
        bt.card_effects(me, opp, C["mirror"], 3, entry())
        self.assertEqual([c.card.name for c in me.creatures], ["Giant"])
        tok = me.creatures[0]
        self.assertTrue(tok.card.is_token and tok.has("menace"))
        self.assertEqual((len(opp.creatures), me.open), (2, [U, B, U]))

    def test_kicked_copies_all(self):
        me, opp = pair()
        on_board(opp, BEAR)
        on_board(opp, FLYER)
        me.open = [U, B] + [U] * 4
        bt.card_effects(me, opp, C["mirror"], 3, entry())
        self.assertEqual(sorted(c.card.name for c in me.creatures), ["Bear", "Flyer"])
        self.assertTrue(all(c.has("menace") and c.card.is_token for c in me.creatures))
        self.assertTrue(me.creatures[1].has("flying") or me.creatures[0].has("flying"))
        self.assertEqual(me.open, [])

    def test_needs_opposing_creature(self):
        me, opp = pair()
        me.hand = [C["mirror"]]
        self.assertEqual(bt.main_phase_spells(me, opp), [])
        on_board(opp, BEAR)
        self.assertEqual(bt.main_phase_spells(me, opp), [C["mirror"]])


class PrimeDirectiveTests(unittest.TestCase):
    def test_interfere_counters(self):
        me, opp = pair()
        opp.hand, opp.open = [C["prime"]], [U] * 3
        bt._resolve(me, opp, OGRE, 3, entry())
        self.assertEqual((me.creatures, OGRE in me.graveyard, opp.open), ([], True, []))


BUFFER = card_info(_card("Pattern Buffer Preservation", "Sorcery", "{1}{B}", 2, "B", "Look at the top two cards of "
                         "your library. Put one of them into your hand and the other into your graveyard.\nBeam me up "
                         "{1}{B} (You may cast this card from your graveyard for {1}{B} if you also return a creature you "
                         "control to its owner's hand. Then exile this spell.)"))[0]
SWAMP = card_info(_card("Swamp", f"Basic Land {DASH} Swamp", text="({T}: Add {B}.)", produced=["B"]))[0]


class GraveyardVersionTests(unittest.TestCase):
    """Gefunden im Absturztest zu Paket K: kostet Beam me up so viel wie die Karte selbst, war die Friedhofs-Version
    gleich der Handkarte (NamedTuple) und wurde mit ihr verwechselt."""

    def test_beam_version_differs_from_hand_card(self):
        me, opp = pair()
        on_board(me, BEAR)
        me.graveyard = [BUFFER]
        (cheap, orig), = bt.beam_versions(me, opp)
        self.assertEqual(orig, BUFFER)
        self.assertNotEqual(cheap, BUFFER)

    def test_same_card_in_hand_and_graveyard(self):
        me, opp = pair()
        on_board(me, BEAR)
        me.lands = [SWAMP] * 4
        me.hand, me.graveyard = [BUFFER], [BUFFER]
        me.library = [SWAMP] * 10
        bt.take_turn(me, opp, 5, 3, skip_draw=False)
        self.assertEqual(sum(c == BUFFER for c in me.hand + me.graveyard), 1)  # die andere ist im Exil


if __name__ == "__main__":
    unittest.main()
