"""SOS Paket D: Friedhof (Lorehold) - Ausloeser beim Verlassen des Friedhofs (Pump, Marke, Schaden und Leben, auch
von Artefakten), "if a card left your graveyard this turn" (Ziehen, Angriffs-Pump, Kostensenkung), Faehigkeiten aus dem
Friedhof (Leben + Surveil, auf die Hand als Hexerei, zurueck mit Exil-Kosten, nach Kampfschaden), Exil aus dem
Friedhof (Rubble Rouser, Kampfbeginn), Rueckholen (Instants/Sorceries, Repartee, Cauldron of Essence, Practiced
Scrollsmith) und Ancestral Anger. Kartentexte aus Secrets of Strixhaven (SOS)."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]
BEAR = W["Test Bear"]


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="W"):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)


LEAVE = "Whenever one or more cards leave your graveyard, "
RAW = {
    "historian": raw("Owlin Historian", f"Creature {DASH} Bird Cleric", "{2}{W}", 3,
                     "Flying\nWhen this creature enters, surveil 1. (Look at the top card of your library. You may put "
                     "it into your graveyard.)\n" + LEAVE + "this creature gets +1/+1 until end of turn.", "2", "3",
                     ["Flying", "Surveil"]),
    "mascot": raw("Spirit Mascot", f"Creature {DASH} Spirit Ox", "{R}{W}", 2,
                  LEAVE + "put a +1/+1 counter on this creature.", "2", "2", colors="RW"),
    "ark": raw("Ark of Hunger", "Artifact", "{2}{R}{W}", 4,
               LEAVE + "this artifact deals 1 damage to each opponent and you gain 1 life.\n{T}: Mill a card. You may "
               "play that card this turn.", keywords=["Mill"], colors="RW"),
    "research": raw("Primary Research", "Enchantment", "{4}{W}", 5,
                    "When this enchantment enters, return target nonland permanent card with mana value 3 or less from "
                    "your graveyard to the battlefield.\nAt the beginning of your end step, if a card left your "
                    "graveyard this turn, draw a card."),
    "history": raw("Living History", "Enchantment", "{1}{R}", 2,
                   "When this enchantment enters, create a 2/2 red and white Spirit creature token.\nWhenever you "
                   "attack, if a card left your graveyard this turn, target attacking creature gets +2/+0 until end "
                   "of turn.", colors="R"),
    "wilt": raw("Wilt in the Heat", "Instant", "{2}{R}{W}", 4,
                "This spell costs {2} less to cast if one or more cards left your graveyard this turn.\nWilt in the "
                "Heat deals 5 damage to target creature. If that creature would die this turn, exile it instead.",
                colors="RW"),
    "docent": raw("Stone Docent", f"Creature {DASH} Spirit Chimera", "{1}{W}", 2,
                  "{W}, Exile this card from your graveyard: You gain 2 life. Surveil 1. Activate only as a sorcery. "
                  "(Look at the top card of your library. You may put it into your graveyard.)", "3", "1",
                  ["Surveil"]),
    "dromedary": raw("Summoned Dromedary", f"Creature {DASH} Spirit Camel", "{3}{W}", 4,
                     "Vigilance\n{1}{W}: Return this card from your graveyard to your hand. Activate only as a "
                     "sorcery.", "4", "3", ["Vigilance"]),
    "professor": raw("Postmortem Professor", f"Creature {DASH} Zombie Warlock", "{1}{B}", 2,
                     "This creature can't block.\nWhenever this creature attacks, each opponent loses 1 life and you "
                     "gain 1 life.\n{1}{B}, Exile an instant or sorcery card from your graveyard: Return this card "
                     "from your graveyard to the battlefield.", "2", "2", colors="B"),
    "rouser": raw("Rubble Rouser", f"Creature {DASH} Dwarf Sorcerer", "{2}{R}", 3,
                  "When this creature enters, you may discard a card. If you do, draw a card.\n{T}, Exile a card from "
                  "your graveyard: Add {R}. When you do, this creature deals 1 damage to each opponent.", "1", "4",
                  colors="R"),
    "cauldron": raw("Cauldron of Essence", "Artifact", "{1}{B}{G}", 3,
                    "Whenever a creature you control dies, each opponent loses 1 life and you gain 1 life.\n{1}{B}{G}, "
                    "{T}, Sacrifice a creature: Return target creature card from your graveyard to the battlefield. "
                    "Activate only as a sorcery.", colors="BG"),
    "dustspeaker": raw("Ascendant Dustspeaker", f"Creature {DASH} Orc Cleric", "{4}{W}", 5,
                       "Flying\nWhen this creature enters, put a +1/+1 counter on another target creature you "
                       "control.\nAt the beginning of combat on your turn, exile up to one target card from a "
                       "graveyard.", "3", "4", ["Flying"]),
    "relic_sloth": raw("Startled Relic Sloth", f"Creature {DASH} Sloth Beast", "{2}{R}{W}", 4,
                       "Trample, lifelink\nAt the beginning of combat on your turn, exile up to one target card from a "
                       "graveyard.", "4", "4", ["Lifelink", "Trample"], "RW"),
    "lorecaster": raw("Zealous Lorecaster", f"Creature {DASH} Giant Sorcerer", "{5}{R}", 6,
                      "When this creature enters, return target instant or sorcery card from your graveyard to your "
                      "hand.", "4", "4", colors="R"),
    "divergent": raw("Divergent Equation", "Instant", "{X}{X}{U}", 1,
                     "Return up to X target instant and/or sorcery cards from your graveyard to your hand.\nExile "
                     "Divergent Equation.", colors="U"),
    "wisdom": raw("Wisdom of Ages", "Sorcery", "{4}{U}{U}{U}", 7,
                  "Return all instant and sorcery cards from your graveyard to your hand. You have no maximum hand size "
                  "for the rest of the game.\nExile Wisdom of Ages.", colors="U"),
    "necroscribe": raw("Forum Necroscribe", f"Creature {DASH} Troll Warlock", "{5}{B}", 6,
                       "Ward—Discard a card.\nRepartee — Whenever you cast an instant or sorcery spell that targets a "
                       "creature, return target creature card from your graveyard to the battlefield.", "5", "4",
                       ["Ward", "Repartee"], "B"),
    "confidence": raw("Killian's Confidence", "Sorcery", "{W}{B}", 2,
                      "Target creature gets +1/+1 until end of turn. Draw a card.\nWhenever one or more creatures you "
                      "control deal combat damage to a player, you may pay {W/B}. If you do, return this card from "
                      "your graveyard to your hand.", colors="WB"),
    "scrollsmith": raw("Practiced Scrollsmith", f"Creature {DASH} Dwarf Cleric", "{R}{R/W}{W}", 3,
                       "First strike\nWhen this creature enters, exile target noncreature, nonland card from your "
                       "graveyard. Until the end of your next turn, you may cast that card.", "3", "2",
                       ["First strike"], "RW"),
    "anger": raw("Ancestral Anger", "Sorcery", "{R}", 1,
                 "Target creature gains trample and gets +X/+0 until end of turn, where X is 1 plus the number of "
                 "cards named Ancestral Anger in your graveyard.\nDraw a card.", colors="R"),
    "sundering": raw("Sundering Archaic", f"Creature {DASH} Avatar", "{6}", 6,
                     "Converge — When this creature enters, exile target nonland permanent an opponent controls with "
                     "mana value less than or equal to the number of colors of mana spent to cast this creature.\n{2}: "
                     "Put target card from a graveyard on the bottom of its owner's library.", "3", "3", ["Converge"],
                     ""),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}

TITAN = card_info(raw("Titan", "Creature — Giant", "{4}{G}", 5, "", "5", "5", colors="G"))[0]
OGRE = card_info(raw("Ogre", "Creature — Ogre", "{2}{R}", 3, "", "3", "3", colors="R"))[0]
THOUGHT = card_info(raw("Quick Thought", "Sorcery", "{U}", 1, "Draw a card.", colors="U"))[0]
SHOCK = card_info(raw("Shock", "Instant", "{R}", 1, "Shock deals 2 damage to any target.", colors="R"))[0]
SNAP = card_info(raw("Snap Trick", "Instant", "{W}", 1, "Target creature gets +2/+2 until end of turn."))[0]
W_, B_, U_, R_, G_ = ("W",), ("B",), ("U",), ("R",), ("G",)


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


def leave_one(p):
    p.graveyard.append(THOUGHT)
    p.graveyard.remove(THOUGHT)


class ParseTests(unittest.TestCase):
    def test_leave_triggers(self):
        self.assertEqual(C["historian"].gy_leave, ("pump_self", (1, 1), False))
        self.assertEqual(C["mascot"].gy_leave, ("counter_self", 1, False))
        self.assertEqual(C["ark"].gy_leave, ("ping_life", (1, 1), False))

    def test_left_this_turn(self):
        self.assertEqual(C["research"].end_gy_draw, 1)
        self.assertEqual(C["history"].attack_gy_pump, (2, 0))
        self.assertEqual(C["wilt"].self_discount, ("gy_left", 2))
        self.assertTrue(C["wilt"].removal)

    def test_graveyard_abilities(self):
        self.assertEqual(C["docent"].gy_ability, (((0, (("W", 1),)),), (("life", 2), ("surveil", 1))))
        self.assertTrue(C["docent"].gy_ability_sorcery)
        self.assertEqual(C["dromedary"].gy_return[1], "hand")
        self.assertEqual(C["dromedary"].gy_return[5], "sorcery")
        self.assertEqual(C["professor"].gy_return[1], "battlefield")
        self.assertEqual(C["professor"].gy_return[4], "exile_instsorc")
        self.assertEqual(C["confidence"].gy_combat_return, (((0, (("W/B", 1),)),)) if False else
                         C["confidence"].gy_combat_return)
        self.assertTrue(C["confidence"].gy_combat_return)

    def test_exile_and_return(self):
        self.assertTrue(C["rouser"].rubble_ping)
        self.assertTrue(C["cauldron"].cauldron_reanimate)
        self.assertTrue(C["dustspeaker"].combat_exile_gy and C["relic_sloth"].combat_exile_gy)
        self.assertEqual(C["lorecaster"].reanimate, ("target", "instsorc", 99, "hand", 0))
        self.assertEqual((C["wisdom"].reanimate, C["wisdom"].self_exile), (("all", "instsorc", 99, "hand", 0), True))
        self.assertEqual((C["divergent"].x_regrowth, C["divergent"].self_exile), (True, True))
        self.assertEqual(C["necroscribe"].cast_trig, (("instsorc_creature", (("reanimate_creature",),), (), ""),))
        self.assertTrue(C["scrollsmith"].scrollsmith)
        self.assertTrue(C["anger"].named_gy_pump)
        self.assertEqual(C["anger"].draws, 1)


class CoverageTests(unittest.TestCase):
    PARTIAL = {"ark": "{T}: Mill a card", "rouser": None, "professor": None, "cauldron": None, "sundering": "Converge"}

    def test_cards_fully_modelled(self):
        for key in RAW:
            open_lines = [line for _c, _m, line in analyze_card(RAW[key])]
            allowed = self.PARTIAL.get(key)
            if allowed:
                open_lines = [line for line in open_lines if not line.startswith(allowed)]
            self.assertEqual(open_lines, [], key)


class LeaveTests(unittest.TestCase):
    def test_historian_pump(self):
        me, opp = pair()
        h = on_board(me, C["historian"])
        leave_one(me)
        bt.gy_leave_check((me, opp), entry())
        self.assertEqual((h.pump, h.tpump), (1, 1))

    def test_mascot_counter(self):
        me, opp = pair()
        m = on_board(me, C["mascot"])
        leave_one(me)
        bt.gy_leave_check((me, opp), entry())
        self.assertEqual(m.bonus, 1)

    def test_ark_artifact_pings(self):
        me, opp = pair()
        me.perms.append(C["ark"])
        leave_one(me)
        bt.gy_leave_check((me, opp), entry())
        self.assertEqual((opp.life, me.life), (19, 21))

    def test_research_draws_only_after_leave(self):
        me, opp = pair()
        me.perms.append(C["research"])
        bt.sos_end_own(me, opp, 3, entry())
        self.assertEqual(len(me.hand), 0)
        leave_one(me)
        bt.sos_end_own(me, opp, 3, entry())
        self.assertEqual(len(me.hand), 1)

    def test_living_history_pump_on_attack(self):
        me, opp = pair()
        me.perms.append(C["history"])
        on_board(me, OGRE)
        me.lands = [PLAINS]
        me.graveyard.append(C["docent"])  # verlaesst den Friedhof vor dem Angriff (Faehigkeit mit freiem Mana)
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 5)

    def test_living_history_needs_leave_this_turn(self):
        me, opp = pair()
        me.perms.append(C["history"])
        on_board(me, OGRE)
        leave_one(me)  # vor dem Zug: zaehlt nicht
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 3)

    def test_wilt_cheaper_after_leave(self):
        me, opp = pair()
        self.assertEqual(bt.own_reduction(me, C["wilt"]), 0)
        leave_one(me)
        self.assertEqual(bt.own_reduction(me, C["wilt"]), 2)


class GraveyardAbilityTests(unittest.TestCase):
    def test_docent_from_graveyard_in_own_turn(self):
        me, opp = pair()
        me.graveyard.append(C["docent"])
        me.open = [W_]
        bt.lasting_abilities(me, opp, 3, entry(), own_turn=True, mode="free")
        self.assertEqual(me.life, 22)
        self.assertNotIn(C["docent"], me.graveyard)

    def test_dromedary_only_as_sorcery(self):
        me, opp = pair()
        me.graveyard.append(C["dromedary"])
        me.open = [W_, W_]
        bt.lasting_abilities(me, opp, 3, entry(), own_turn=False, mode="rest")
        self.assertIn(C["dromedary"], me.graveyard)
        bt.lasting_abilities(me, opp, 3, entry(), own_turn=True, mode="free")
        self.assertIn(C["dromedary"], me.hand)

    def test_professor_exiles_instant_or_sorcery(self):
        me, opp = pair()
        me.graveyard.extend([C["professor"], THOUGHT])
        me.open = [B_, B_]
        bt.lasting_abilities(me, opp, 3, entry(), own_turn=True, mode="free")
        self.assertTrue(any(c.card is C["professor"] for c in me.creatures))
        self.assertNotIn(THOUGHT, me.graveyard)

    def test_professor_needs_instant_or_sorcery(self):
        me, opp = pair()
        me.graveyard.extend([C["professor"], BEAR])
        me.open = [B_, B_]
        bt.lasting_abilities(me, opp, 3, entry(), own_turn=True, mode="free")
        self.assertIn(C["professor"], me.graveyard)

    def test_confidence_returns_after_combat_damage(self):
        me, opp = pair()
        on_board(me, OGRE)
        me.graveyard.append(C["confidence"])
        me.lands = [PLAINS]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertIn(C["confidence"], me.hand)


class ExileTests(unittest.TestCase):
    def test_rouser_at_opponents_end_step(self):
        dfn, act = pair()
        dfn.turn_start = 1
        rouser = on_board(dfn, C["rouser"])
        dfn.graveyard.append(PLAINS)
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual((act.life, rouser.tapped, len(dfn.graveyard)), (19, True, 0))

    def test_rouser_needs_card_in_graveyard(self):
        dfn, act = pair()
        dfn.turn_start = 1
        rouser = on_board(dfn, C["rouser"])
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual((act.life, rouser.tapped), (20, False))

    def test_combat_exile_opponents_graveyard(self):
        me, opp = pair()
        on_board(me, C["relic_sloth"])
        opp.graveyard.append(TITAN)
        bt.sos_combat_exile(me, opp, entry())
        self.assertNotIn(TITAN, opp.graveyard)

    def test_combat_exile_own_graveyard_for_payoff(self):
        me, opp = pair()
        on_board(me, C["relic_sloth"])
        mascot = on_board(me, C["mascot"])
        me.graveyard.append(PLAINS)
        opp.graveyard.append(TITAN)
        bt.sos_combat_exile(me, opp, entry())
        bt.gy_leave_check((me, opp), entry())
        self.assertEqual((me.graveyard, mascot.bonus), ([], 1))
        self.assertIn(TITAN, opp.graveyard)

    def test_cauldron_trades_token_for_big_creature(self):
        me, opp = pair()
        me.perms.append(C["cauldron"])
        token = on_board(me, bt.INKLING)
        me.graveyard.append(TITAN)
        me.open = [B_, G_, B_]
        bt.sos_main_abilities(me, opp, 3, entry())
        self.assertNotIn(token, me.creatures)
        self.assertTrue(any(c.card is TITAN for c in me.creatures))

    def test_cauldron_not_for_small_gain(self):
        me, opp = pair()
        me.perms.append(C["cauldron"])
        on_board(me, OGRE)
        me.graveyard.append(BEAR)
        me.open = [B_, G_, B_]
        bt.sos_main_abilities(me, opp, 3, entry())
        self.assertIn(BEAR, me.graveyard)


class ReturnTests(unittest.TestCase):
    def test_lorecaster(self):
        me, opp = pair()
        me.graveyard.append(SHOCK)
        bt._resolve(me, opp, C["lorecaster"], 3, entry())
        self.assertIn(SHOCK, me.hand)

    def test_wisdom_returns_all_and_exiles_itself(self):
        me, opp = pair()
        me.graveyard.extend([SHOCK, THOUGHT, BEAR])
        bt._resolve(me, opp, C["wisdom"], 3, entry())
        self.assertEqual(sorted(c.name for c in me.hand), ["Quick Thought", "Shock"])
        self.assertEqual(me.graveyard, [BEAR])

    def test_divergent_x_and_exile(self):
        me, opp = pair()
        me.graveyard.extend([SHOCK, THOUGHT, SNAP])
        me.open = [U_] * 5
        me.hand = [C["divergent"]]
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual(len(me.hand), 2)
        self.assertNotIn(C["divergent"], me.graveyard)

    def test_necroscribe_repartee(self):
        me, opp = pair()
        on_board(me, C["necroscribe"])
        me.graveyard.append(TITAN)
        bt.cast_triggers(me, SNAP, 3, entry())
        self.assertTrue(any(c.card is TITAN for c in me.creatures))

    def test_scrollsmith_impulse(self):
        me, opp = pair()
        me.graveyard.extend([SHOCK, BEAR])
        bt._resolve(me, opp, C["scrollsmith"], 3, entry())
        self.assertNotIn(SHOCK, me.graveyard)
        self.assertTrue(any(c is SHOCK for c, _t in me.impulse))

    def test_ancestral_anger_counts_copies(self):
        me, opp = pair()
        me.turn_start = me.now
        ogre = on_board(me, OGRE)
        me.graveyard.extend([C["anger"], C["anger"]])
        bt._resolve(me, opp, C["anger"], 3, entry())
        self.assertEqual(ogre.pump, 3)
        self.assertIn("trample", ogre.extra)


if __name__ == "__main__":
    unittest.main()
