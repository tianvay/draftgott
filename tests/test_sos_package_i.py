"""SOS Paket I: Zauber kopieren und aus dem Friedhof wirken - Lumaret's Favor (Infusion), Social Snub, Striking
Palette, Mica (Treasure opfern), Aziza (drei Kreaturen tappen), Choreographed Sparks (Instant/Sorcery und
Kreaturzauber), Flashback (die Karte), The Dawning Archaic beim Angriff, Group Project (Flashback durch Tappen), Nita,
Applied Geometry und die Token-Kopie von Echocasting Symposium. Kartentexte aus Secrets of Strixhaven (SOS)."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]
BEAR = W["Test Bear"]
NOTE = " (While it's prepared, you may cast a copy of its spell. Doing so unprepares it.)"


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="R"):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)


RAW = {
    "sparks": raw("Choreographed Sparks", "Instant", "{R}{R}", 2,
                  "This spell can't be copied.\nChoose one or both —\n• Copy target instant or sorcery spell you "
                  "control. You may choose new targets for the copy.\n• Copy target creature spell you control. The "
                  "copy gains haste and \"At the beginning of the end step, sacrifice this token.\""),
    "mica": raw("Mica, Reader of Ruins", f"Legendary Creature {DASH} Human Artificer", "{3}{R}", 4,
                "Ward—Pay 3 life. (Whenever this creature becomes the target of a spell or ability an opponent "
                "controls, counter it unless that player pays 3 life.)\nWhenever you cast an instant or sorcery spell, "
                "you may sacrifice an artifact. If you do, copy that spell and you may choose new targets for the "
                "copy.", "4", "4", ["Ward"]),
    "palette": raw("Striking Palette", "Sorcery", "{R}", 1,
                   "When you next cast an instant or sorcery spell this turn, copy that spell. You may choose new "
                   "targets for the copy."),
    "favor": raw("Lumaret's Favor", "Instant", "{1}{G}", 2,
                 "Infusion — When you cast this spell, copy it if you gained life this turn. You may choose new "
                 "targets for the copy.\nTarget creature gets +2/+4 until end of turn.", keywords=["Infusion"],
                 colors="G"),
    "aziza": raw("Aziza, Mage Tower Captain", f"Legendary Creature {DASH} Djinn Sorcerer", "{R}{W}", 2,
                 "Whenever you cast an instant or sorcery spell, you may tap three untapped creatures you control. If "
                 "you do, copy that spell. You may choose new targets for the copy.", "2", "2", colors="RW"),
    "snub": raw("Social Snub", "Sorcery", "{1}{W}{B}", 3,
                "When you cast this spell while you control a creature, you may copy this spell.\nEach player "
                "sacrifices a creature of their choice. Each opponent loses 1 life and you gain 1 life.", colors="WB"),
    "flashback": raw("Flashback", "Instant", "{R}", 1,
                     "Target instant or sorcery card in your graveyard gains flashback until end of turn. The flashback "
                     "cost is equal to its mana cost. (You may cast that card from your graveyard for its flashback "
                     "cost. Then exile it.)"),
    "dawning": raw("The Dawning Archaic", f"Legendary Creature {DASH} Avatar", "{10}", 10,
                   "This spell costs {1} less to cast for each instant and sorcery card in your graveyard.\nReach\n"
                   "Whenever The Dawning Archaic attacks, you may cast target instant or sorcery card from your "
                   "graveyard without paying its mana cost. If that spell would be put into your graveyard, exile it "
                   "instead.", "7", "7", ["Reach"], ""),
    "project": raw("Group Project", "Sorcery", "{1}{W}", 2,
                   "Create a 2/2 red and white Spirit creature token.\nFlashback—Tap three untapped creatures you "
                   "control. (You may cast this card from your graveyard for its flashback cost. Then exile it.)",
                   keywords=["Flashback"], colors="W"),
    "nita": raw("Nita, Forum Conciliator", f"Legendary Creature {DASH} Human Advisor", "{1}{W}{B}", 3,
                "Whenever you cast a spell you don't own, put a +1/+1 counter on each creature you control.\n{2}, "
                "Sacrifice another creature: Exile target instant or sorcery card from an opponent's graveyard. You "
                "may cast it this turn, and mana of any type can be spent to cast that spell. If that spell would be "
                "put into a graveyard, exile it instead. Activate only as a sorcery.", "2", "3", colors="WB"),
    "geometry": raw("Applied Geometry", "Sorcery", "{2}{G}{U}", 4,
                    "Create a token that's a copy of target non-Aura permanent you control, except it's a 0/0 Fractal "
                    "creature in addition to its other types. Put six +1/+1 counters on it.", colors="GU"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}

TITAN = card_info(raw("Titan", "Creature — Giant", "{4}{G}", 5, "", "5", "5", colors="G"))[0]
OGRE = card_info(raw("Ogre", "Creature — Ogre", "{2}{R}", 3, "", "3", "3"))[0]
MOUSE = card_info(raw("Mouse", "Creature — Mouse", "{W}", 1, "", "1", "1", colors="W"))[0]
THOUGHT = card_info(raw("Quick Thought", "Sorcery", "{U}", 1, "Draw a card.", colors="U"))[0]
BOLT = card_info(raw("Bolt", "Instant", "{R}", 1, "Bolt deals 3 damage to target creature."))[0]
SHOCKS = card_info(raw("Burn Up", "Sorcery", "{1}{R}", 2, "Burn Up deals 3 damage to target creature."))[0]


def player(name="Wir"):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], [PLAINS] * 20
    return p


def pair():
    me, opp = player(), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


def entry():
    return {"face": 0, "damage": 0, "events": [], "deaths": [], "main1": [], "main2": []}


def on_board(p, card, entered=0):
    c = bt.Creature(card, entered)
    c.gy, c.ctl = p.graveyard, p
    p.creatures.append(c)
    return c


class ParseTests(unittest.TestCase):
    def test_copy_fields(self):
        self.assertTrue(C["sparks"].sparks and C["sparks"].uncopyable)
        self.assertTrue(C["mica"].mica_copy)
        self.assertTrue(C["palette"].copy_next_spell)
        self.assertTrue(C["favor"].self_copy_infusion)
        self.assertTrue(C["aziza"].aziza_copy)
        self.assertTrue(C["snub"].self_copy_creature)

    def test_graveyard_fields(self):
        self.assertTrue(C["flashback"].flashback_grant)
        self.assertTrue(C["dawning"].dawning_attack)
        self.assertTrue(C["project"].flashback_tap3)
        self.assertTrue(C["nita"].nita)
        self.assertTrue(C["geometry"].applied_geometry)


class CoverageTests(unittest.TestCase):
    def test_cards_fully_modelled(self):
        for key in RAW:
            self.assertEqual([line for _c, _m, line in analyze_card(RAW[key])], [], key)


class CopyTests(unittest.TestCase):
    def test_favor_copies_with_life(self):
        me, opp = pair()
        me.gained = 1
        bt.on_cast(me, C["favor"], 3, entry())
        self.assertEqual(bt.pending_copies(me, C["favor"]), 1)
        me2, _opp2 = pair()
        bt.on_cast(me2, C["favor"], 3, entry())
        self.assertEqual(bt.pending_copies(me2, C["favor"]), 0)

    def test_palette_copies_next_draw_spell(self):
        me, opp = pair()
        bt._resolve(me, opp, C["palette"], 3, entry())
        bt._resolve(me, opp, THOUGHT, 3, entry())
        self.assertEqual(len(me.hand), 2)

    def test_mica_sacrifices_treasure(self):
        me, opp = pair()
        on_board(me, C["mica"])
        me.treasures = 1
        bt._resolve(me, opp, THOUGHT, 3, entry())
        self.assertEqual((len(me.hand), me.treasures), (2, 0))

    def test_aziza_taps_three_outside_own_turn(self):
        me, opp = pair()
        me.turn_start, me.now = 1, 4  # Zug des Gegners
        on_board(me, C["aziza"])
        a, b = on_board(me, BEAR), on_board(me, MOUSE)
        bt._resolve(me, opp, THOUGHT, 3, entry())
        self.assertEqual(len(me.hand), 2)
        self.assertTrue(a.tapped and b.tapped)

    def test_sparks_copies_removal(self):
        me, opp = pair()
        me.open, me.hand = [("R",)] * 3, [BOLT, C["sparks"]]
        bear, ogre = on_board(opp, BEAR), on_board(opp, OGRE)
        self.assertTrue(bt._use_removal(me, BOLT, BOLT.alts, True, 3, entry(), other=opp))
        self.assertNotIn(ogre, opp.creatures)  # die Kopie nimmt die gefaehrlichste Kreatur
        bt.cast_removal(BOLT, me, opp, entry(), 3, target=bear)
        bt.bury((me, opp), entry())
        self.assertEqual(opp.creatures, [])
        self.assertNotIn(C["sparks"], me.hand)

    def test_sparks_haste_copy_of_creature(self):
        me, opp = pair()
        me.turn_start = me.now
        me.open, me.hand = [("R",)] * 2, [C["sparks"]]
        bt._resolve(me, opp, TITAN, 3, entry())
        copies = [c for c in me.creatures if c.card.is_token and c.card.name == "Titan"]
        self.assertEqual(len(copies), 1)
        self.assertTrue(copies[0].card.haste and copies[0].card.end_sacrifice)

    def test_snub_copies_when_opponent_has_more(self):
        me, opp = pair()
        on_board(me, MOUSE)
        on_board(opp, OGRE)
        on_board(opp, TITAN)
        bt._resolve(me, opp, C["snub"], 3, entry())
        self.assertEqual((len(opp.creatures), opp.life), (0, 18))


class GraveyardCastTests(unittest.TestCase):
    def test_flashback_card_recasts_instant_at_end_step(self):
        dfn, act = pair()
        dfn.graveyard.append(BOLT)
        dfn.open, dfn.hand = [("R",)] * 3, [C["flashback"]]
        ogre = on_board(act, OGRE)
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertNotIn(ogre, act.creatures)
        self.assertNotIn(BOLT, dfn.graveyard)

    def test_flashback_card_sorcery_only_in_own_main_phase(self):
        dfn, act = pair()
        dfn.graveyard.append(SHOCKS)
        dfn.open, dfn.hand = [("R",)] * 3, [C["flashback"]]
        on_board(act, OGRE)
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertIn(C["flashback"], dfn.hand)  # Sorcery nur mit Sorcery-Timing
        me, opp = dfn, act
        me.turn_start = me.now
        bt.sos_main_abilities(me, opp, 3, entry())
        self.assertEqual(opp.creatures, [])
        self.assertNotIn(SHOCKS, me.graveyard)

    def test_flashback_needs_target_card(self):
        dfn, act = pair()
        dfn.open, dfn.hand = [("R",)] * 3, [C["flashback"]]
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertIn(C["flashback"], dfn.hand)

    def test_dawning_casts_free_on_attack(self):
        me, opp = pair()
        on_board(me, C["dawning"])
        me.graveyard.append(THOUGHT)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertNotIn(THOUGHT, me.graveyard)
        self.assertGreaterEqual(len(me.hand), 1)

    def test_group_project_flashback_in_main2(self):
        me, opp = pair()
        me.graveyard.append(C["project"])
        for _ in range(3):
            on_board(me, MOUSE, entered=5)  # frisch: greifen nicht an
        bt.sos_main2(me, entry())
        self.assertNotIn(C["project"], me.graveyard)
        self.assertEqual(sum(1 for c in me.creatures if c.card.is_token), 1)

    def test_nita_casts_opponents_spell(self):
        me, opp = pair()
        on_board(me, C["nita"])
        token = on_board(me, bt.INKLING)
        bear = on_board(me, BEAR)
        opp.graveyard.append(SHOCKS)
        ogre = on_board(opp, OGRE)
        me.open = [("W",)] * 4
        bt.sos_main_abilities(me, opp, 3, entry())
        self.assertNotIn(token, me.creatures)
        self.assertNotIn(ogre, opp.creatures)
        self.assertEqual(bear.bonus, 1)


class TokenCopyTests(unittest.TestCase):
    def test_applied_geometry(self):
        me, opp = pair()
        on_board(me, OGRE)
        bt._resolve(me, opp, C["geometry"], 3, entry())
        tok = next(c for c in me.creatures if c.card.is_token)
        self.assertEqual((tok.card.name, tok.power, tok.toughness), ("Ogre", 6, 6))
        self.assertIn("fractal", tok.card.creature_types)


if __name__ == "__main__":
    unittest.main()
