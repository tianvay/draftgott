"""Star Trek (TRK): "Whenever you face a dilemma, ..." - man steht vor einem Dilemma, wenn man fuer einen Zauber oder
eine Faehigkeit einen oder mehrere Modi waehlt (Erinnerungstext; 700.2a: modaler Zauber beim Wirken, 700.2b: modaler
ausgeloester Effekt beim Auf-den-Stapel-Legen). Je Zauber bzw. Faehigkeit ein Dilemma, egal wie viele Modi. Nur das
Kampfmodell waehlt Modi (Card.choices), daher loest das Dilemma auch nur dort aus. Kartentexte aus TRK."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]
BEAR = W["Test Bear"]
B, R, WH = ("B",), ("R",), ("W",)
REMINDER = " (You face a dilemma as you choose one or more modes for a spell or ability.)"


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="B"):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)


RAW = {
    "elim": raw("Elim Garak, Simple Tailor", f"Legendary Creature {DASH} Cardassian Rogue", "{2}{B}", 3,
                "Menace\nWhenever you face a dilemma, each opponent loses 2 life and you gain 2 life." + REMINDER,
                "3", "3", ["Menace"]),
    "operative": raw("Obsidian Order Operative", f"Creature {DASH} Cardassian Officer Spy", "{3}{B}", 4,
                     "Whenever you face a dilemma, each opponent loses 1 life and you gain 1 life." + REMINDER,
                     "2", "5"),
    "seven": raw("Seven of Nine", f"Legendary Artifact Creature {DASH} Human Scientist", "{2}{U}{B}", 4,
                 "Whenever you face a dilemma, draw a card." + REMINDER, "2", "4", colors="UB"),
    "decision": raw("Command Decision", "Sorcery", "{1}{W}", 2, "Choose one —\n• Destroy target creature with power "
                    "4 or greater.\n• Draw a card.", colors="W"),
    "crusher": raw("Craftwork Crusher", f"Artifact Creature {DASH} Boar Construct", "{3}{R}{R}{G}{G}", 7,
                   "Trample\nWhen this creature enters, choose two —\n• This creature deals 4 damage to target "
                   "creature or planeswalker.\n• Create a 2/2 colorless Wizard Soldier creature token named Cadet.\n"
                   "• Draw a card.", "7", "5", ["Trample"], "RG"),
    "charm": raw("Stingerquill Charm", "Instant", "{B}{R}", 2, "Choose one —\n• Stingerquill Charm deals 3 damage to "
                 "any target.\n• Target creature gains first strike and deathtouch until end of turn.\n• Create a 2/2 "
                 "colorless Wizard Soldier creature token named Cadet. It gains haste until end of turn.", colors="BR"),
    "bolt": raw("Test Bolt", "Sorcery", "{R}", 1, "Test Bolt deals 3 damage to target creature.", colors="R"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}
OGRE = card_info(raw("Ogre", f"Creature {DASH} Ogre", "{2}{R}", 3, "", "3", "3", colors="R"))[0]


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


class ParseTests(unittest.TestCase):
    def test_drain(self):
        self.assertEqual(C["elim"].dilemma_trig, (("drain", 2, 2),))
        self.assertEqual(C["operative"].dilemma_trig, (("drain", 1, 1),))

    def test_draw(self):
        self.assertEqual(C["seven"].dilemma_trig, (("draw", 1),))

    def test_reminder_is_no_modal_card(self):
        self.assertEqual((C["elim"].choices, C["seven"].choices), ((), ()))

    def test_other_cards_without_dilemma(self):
        self.assertEqual((BEAR.dilemma_trig, C["decision"].dilemma_trig), ((), ()))

    def test_coverage_complete(self):
        for key in ("elim", "operative", "seven"):
            self.assertEqual(analyze_card(RAW[key]), [], key)


class BattleTests(unittest.TestCase):
    def test_modal_sorcery(self):
        me, opp = pair(library=[BEAR] * 3)
        me.creatures = [bt.Creature(C["elim"], 0)]
        bt._resolve(me, opp, C["decision"], 5, entry())
        self.assertEqual((opp.life, me.life, me.hand), (18, 22, [BEAR]))

    def test_non_modal_spell_no_dilemma(self):
        me, opp = pair()
        me.creatures = [bt.Creature(C["elim"], 0)]
        opp.creatures = [bt.Creature(OGRE, 0)]
        bt._resolve(me, opp, C["bolt"], 5, entry())
        self.assertEqual((opp.creatures, opp.life, me.life), ([], 20, 20))

    def test_choose_two_is_one_dilemma(self):
        me, opp = pair(library=[BEAR] * 3)
        me.creatures = [bt.Creature(C["operative"], 0)]
        bt._resolve(me, opp, C["crusher"], 5, entry())
        self.assertEqual((opp.life, me.life), (19, 21))

    def test_modal_enter_trigger_draws(self):
        me, opp = pair(library=[BEAR] * 3)
        me.creatures = [bt.Creature(C["seven"], 0)]
        bt._resolve(me, opp, C["crusher"], 5, entry())
        self.assertEqual(me.hand, [BEAR, BEAR])  # Modus "Draw a card" und Seven of Nine

    def test_modal_enter_again_on_blink(self):
        me, opp = pair()
        me.creatures = [bt.Creature(C["operative"], 0)]
        bt._resolve(me, opp, C["crusher"], 5, entry())
        crusher = next(c for c in me.creatures if c.card.name == "Craftwork Crusher")
        bt.blink(me, crusher, 6, entry(), "Test")
        self.assertEqual(opp.life, 18)  # 603.6a: jedes Betreten waehlt neu

    def test_all_sources_trigger(self):
        me, opp = pair(library=[BEAR] * 3)
        me.creatures = [bt.Creature(C["elim"], 0), bt.Creature(C["operative"], 0)]
        bt._resolve(me, opp, C["decision"], 5, entry())
        self.assertEqual((opp.life, me.life), (17, 23))

    def test_opponents_modal_spell_no_trigger(self):
        me, opp = pair()
        me.creatures = [bt.Creature(C["elim"], 0)]
        bt._resolve(opp, me, C["decision"], 5, entry())
        self.assertEqual((opp.life, me.life), (20, 20))

    def test_modal_instant_removal_at_end_step(self):
        me, opp = pair()
        me.creatures = [bt.Creature(C["elim"], 0)]
        opp.creatures = [bt.Creature(BEAR, 0)]
        me.hand, me.open = [C["charm"]], [B, R]
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual((opp.creatures, opp.life, me.life), ([], 18, 22))

    def test_modal_combat_trick(self):
        me, opp = pair()
        att, blk = bt.Creature(BEAR, 0), bt.Creature(OGRE, 0)
        me.creatures, opp.creatures = [att, bt.Creature(C["elim"], 0)], [blk]
        me.hand, me.open = [C["charm"]], [B, R]
        bt.combat_tricks(me, [(att, [blk])], opp, entry(), 5, attacking=True)
        self.assertEqual((me.hand, att.has("deathtouch"), opp.life, me.life), ([], True, 18, 22))

    def test_event_logged(self):
        me, opp = pair(library=[BEAR] * 3)
        me.creatures = [bt.Creature(C["elim"], 0)]
        e = entry()
        bt._resolve(me, opp, C["decision"], 5, e)
        self.assertTrue(any("Dilemma" in ev and "Elim Garak" in ev for ev in e["events"]), e["events"])


if __name__ == "__main__":
    unittest.main()
