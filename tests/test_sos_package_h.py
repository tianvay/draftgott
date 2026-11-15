"""SOS Paket H: Interaktion - Bounce beim Betreten, Run Behind, Shattered Acolyte, Withering Curse (Infusion: Wrath),
Vicious Rivalry, Blinken (Ennis, Conciliator's Duelist), Planeswalker (Professor Dellian Fel, Ral Zarek), Rabid Attack,
Slumbering Trudge, Molten Note, Steal the Show und Rocket Volley. Kartentexte aus Secrets of Strixhaven (SOS)."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS, ISLAND = W["Plains"], W["Island"]
BEAR = W["Test Bear"]


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="U", loyalty=None):
    d = _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)
    if loyalty is not None:
        d["loyalty"] = loyalty
    return d


RAW = {
    "mage": raw("Matterbending Mage", f"Creature {DASH} Human Wizard", "{2}{U}", 3,
                "When this creature enters, return up to one other target creature to its owner's hand.\nWhenever you "
                "cast a spell with {X} in its mana cost, this creature can't be blocked this turn.", "2", "2"),
    "run": raw("Run Behind", "Instant", "{3}{U}", 4,
               "This spell costs {1} less to cast if it targets an attacking creature.\nTarget creature's owner puts it "
               "on their choice of the top or bottom of their library."),
    "acolyte": raw("Shattered Acolyte", f"Creature {DASH} Dwarf Warlock", "{1}{W}", 2,
                   "Lifelink\n{1}, Sacrifice this creature: Destroy target artifact or enchantment.", "2", "2",
                   ["Lifelink"], "W"),
    "curse": raw("Withering Curse", "Sorcery", "{1}{B}{B}", 3,
                 "All creatures get -2/-2 until end of turn.\nInfusion — If you gained life this turn, destroy all "
                 "creatures instead.", keywords=["Infusion"], colors="B"),
    "rivalry": raw("Vicious Rivalry", "Sorcery", "{2}{B}{G}", 4,
                   "As an additional cost to cast this spell, pay X life.\nDestroy all artifacts and creatures with mana "
                   "value X or less.", colors="BG"),
    "ennis": raw("Ennis, Debate Moderator", f"Legendary Creature {DASH} Human Cleric", "{1}{W}", 2,
                 "When Ennis enters, exile up to one other target creature you control. Return that card to the "
                 "battlefield under its owner's control at the beginning of the next end step.\nAt the beginning of "
                 "your end step, if one or more cards were put into exile this turn, put a +1/+1 counter on Ennis.",
                 "1", "1", colors="W"),
    "duelist": raw("Conciliator's Duelist", f"Creature {DASH} Kor Warlock", "{W}{W}{B}{B}", 4,
                   "When this creature enters, draw a card. Each player loses 1 life.\nRepartee — Whenever you cast an "
                   "instant or sorcery spell that targets a creature, exile up to one target creature. Return that "
                   "card to the battlefield under its owner's control at the beginning of the next end step.", "4",
                   "3", ["Repartee"], "WB"),
    "dellian": raw("Professor Dellian Fel", f"Legendary Planeswalker {DASH} Dellian", "{2}{B}{G}", 4,
                   "+2: You gain 3 life.\n0: You draw a card and lose 1 life.\n−3: Destroy target creature.\n−6: You get "
                   "an emblem with \"Whenever you gain life, target opponent loses that much life.\"", colors="BG",
                   loyalty="5"),
    "ral": raw("Ral Zarek, Guest Lecturer", f"Legendary Planeswalker {DASH} Ral", "{1}{B}{B}", 3,
               "+1: Surveil 2.\n−1: Any number of target players each discard a card.\n−2: Return target creature card "
               "with mana value 3 or less from your graveyard to the battlefield.\n−7: Flip five coins. Target opponent "
               "skips their next X turns, where X is the number of coins that came up heads.", colors="B",
               loyalty="3"),
    "rabid": raw("Rabid Attack", "Instant", "{1}{B}", 2,
                 "Until end of turn, any number of target creatures you control each get +1/+0 and gain \"When this "
                 "creature dies, draw a card.\"", colors="B"),
    "trudge": raw("Slumbering Trudge", f"Creature {DASH} Plant Beast", "{X}{G}", 1,
                  "This creature enters with a number of stun counters on it equal to three minus X. If X is 2 or less, "
                  "it enters tapped. (If a permanent with a stun counter would become untapped, remove one from it "
                  "instead.)", "6", "6", colors="G"),
    "note": raw("Molten Note", "Sorcery", "{X}{R}{W}", 2,
                "Molten Note deals damage to target creature equal to the amount of mana spent to cast this spell. "
                "Untap all creatures you control.\nFlashback {6}{R}{W} (You may cast this card from your graveyard for "
                "its flashback cost. Then exile it.)", keywords=["Flashback"], colors="RW"),
    "steal": raw("Steal the Show", "Sorcery", "{2}{R}", 3,
                 "Choose one or both —\n• Target player discards any number of cards, then draws that many cards.\n• "
                 "Steal the Show deals damage equal to the number of instant and sorcery cards in your graveyard to "
                 "target creature or planeswalker.", colors="R"),
    "volley": raw("Rocket Volley", "Sorcery", "{1}{R}", 2, "Destroy target nonbasic land.", colors="R"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}

TITAN = card_info(raw("Titan", "Creature — Giant", "{4}{G}", 5, "", "5", "5", colors="G"))[0]
OGRE = card_info(raw("Ogre", "Creature — Ogre", "{2}{R}", 3, "", "3", "3", colors="R"))[0]
BRUTE = card_info(raw("Brute", "Creature — Ogre", "{3}{R}", 4, "", "4", "4", colors="R"))[0]
MOUSE = card_info(raw("Mouse", "Creature — Mouse", "{W}", 1, "", "1", "1", colors="W"))[0]
CHEAP = card_info(raw("Quick Thought", "Sorcery", "{U}", 1, "Draw a card."))[0]
SNAP = card_info(raw("Snap Trick", "Instant", "{W}", 1, "Target creature gets +2/+2 until end of turn.", colors="W"))[0]
SCOUT = card_info(raw("Scout", "Creature — Elf", "{G}", 1, "When this creature enters, draw a card.", "1", "1",
                      colors="G"))[0]
DUAL = card_info(_card("Dual Land", "Land", text="{T}: Add {W} or {U}.", produced=["W", "U"]))[0]


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
    def test_removal(self):
        self.assertEqual(C["mage"].removal[:1] + C["mage"].removal[4:5], ("bounce", "etb"))
        self.assertEqual((C["run"].removal[0], C["run"].self_discount), ("tuck", ("attacked", 1)))
        self.assertEqual(C["acolyte"].sac_perm_removal, "artifact_enchantment")
        self.assertEqual((C["curse"].removal[:2], C["curse"].infusion_wrath), (("sweep_damage", 2), True))
        self.assertTrue(C["rivalry"].rivalry)

    def test_blink(self):
        self.assertTrue(C["ennis"].ennis_blink)
        self.assertTrue(C["ennis"].exile_counter)
        self.assertEqual(C["duelist"].cast_trig, (("instsorc_creature", (("flicker_opp",),), (), ""),))

    def test_walkers(self):
        costs = [cost for cost, _a in C["dellian"].pw_abilities]
        self.assertEqual(costs, [2, 0, -3, -6])
        self.assertEqual([cost for cost, _a in C["ral"].pw_abilities], [1, -1, -2, -7])

    def test_others(self):
        self.assertEqual(C["rabid"].modes, ((("pump_all", 1),),))
        self.assertTrue(C["rabid"].trick_death_draw)
        self.assertTrue(C["trudge"].trudge)
        self.assertTrue(C["note"].molten_note)
        self.assertTrue(C["note"].flashback)
        self.assertTrue(C["steal"].steal_show)
        self.assertEqual(C["steal"].removal, ())
        self.assertTrue(C["volley"].land_destroy)


class CoverageTests(unittest.TestCase):
    def test_cards_fully_modelled(self):
        for key in RAW:
            self.assertEqual([line for _c, _m, line in analyze_card(RAW[key])], [], key)


class RemovalTests(unittest.TestCase):
    def test_mage_bounces_on_enter(self):
        me, opp = pair()
        titan = on_board(opp, TITAN)
        bt._resolve(me, opp, C["mage"], 3, entry())
        self.assertNotIn(titan, opp.creatures)
        self.assertIn(TITAN, opp.hand)

    def test_curse_minus_two_and_infusion(self):
        me, opp = pair()
        ogre, mouse = on_board(opp, OGRE), on_board(opp, MOUSE)
        bt._resolve(me, opp, C["curse"], 3, entry())
        self.assertIn(ogre, opp.creatures)
        self.assertNotIn(mouse, opp.creatures)
        me, opp = pair()
        on_board(opp, TITAN)
        me.gained = 1
        bt._resolve(me, opp, C["curse"], 3, entry())
        self.assertEqual(opp.creatures, [])

    def test_rivalry_picks_x(self):
        me, opp = pair()
        on_board(me, MOUSE)
        ogre, titan = on_board(opp, OGRE), on_board(opp, TITAN)
        bt._resolve(me, opp, C["rivalry"], 3, entry())
        self.assertEqual(opp.creatures, [])
        self.assertEqual(me.life, 15)  # X = 5

    def test_rivalry_only_when_worth(self):
        me, opp = pair()
        me.hand = [C["rivalry"]]
        on_board(me, TITAN)
        on_board(opp, MOUSE)
        self.assertNotIn(C["rivalry"], bt.main_phase_spells(me, opp))
        on_board(opp, OGRE)
        self.assertIn(C["rivalry"], bt.main_phase_spells(me, opp))

    def test_volley_destroys_nonbasic(self):
        me, opp = pair()
        opp.lands = [PLAINS, DUAL]
        me.hand = [C["volley"]]
        self.assertIn(C["volley"], bt.main_phase_spells(me, opp))
        bt._resolve(me, opp, C["volley"], 3, entry())
        self.assertEqual(opp.lands, [PLAINS])

    def test_volley_needs_nonbasic(self):
        me, opp = pair()
        opp.lands = [PLAINS]
        me.hand = [C["volley"]]
        self.assertNotIn(C["volley"], bt.main_phase_spells(me, opp))

    def test_molten_note_x_plus_two(self):
        me, opp = pair()
        titan, mouse = on_board(opp, TITAN), on_board(opp, MOUSE)
        me.next_x = 3
        bt._resolve(me, opp, C["note"], 3, entry())
        self.assertNotIn(titan, opp.creatures)
        self.assertIn(mouse, opp.creatures)

    def test_steal_the_show(self):
        me, opp = pair()
        me.lands = [PLAINS] * 6
        me.graveyard.extend([CHEAP, SNAP])
        me.hand = [PLAINS]
        mouse, ogre = on_board(opp, MOUSE), on_board(opp, OGRE)
        bt._resolve(me, opp, C["steal"], 3, entry())
        self.assertNotIn(mouse, opp.creatures)  # 2 Schaden (Steal the Show selbst zaehlt nicht)
        self.assertIn(ogre, opp.creatures)
        self.assertEqual(len(me.hand), 1)
        self.assertIn(PLAINS, me.graveyard)  # ueberzaehliges Land abgeworfen und neu gezogen


class BlinkTests(unittest.TestCase):
    def test_ennis_blinks_etb_creature_and_grows(self):
        me, opp = pair()
        scout = on_board(me, SCOUT)
        bt._resolve(me, opp, C["ennis"], 3, entry())
        self.assertNotIn(scout, me.creatures)
        bt.end_step_prepare((me, opp), entry())
        self.assertTrue(any(c.card is SCOUT for c in me.creatures))
        self.assertEqual(len(me.hand), 1)  # Scout zieht erneut
        bt.sos_end_own(me, opp, 3, entry())
        ennis = next(c for c in me.creatures if c.card is C["ennis"])
        self.assertEqual(ennis.bonus, 1)

    def test_duelist_flickers_blocker_in_own_turn(self):
        me, opp = pair()
        me.turn_start = me.now
        on_board(me, C["duelist"])
        titan = on_board(opp, TITAN)
        bt.cast_triggers(me, SNAP, 3, entry())
        self.assertNotIn(titan, opp.creatures)
        bt.end_step_prepare((me, opp), entry())
        self.assertTrue(any(c.card is TITAN for c in opp.creatures))


class WalkerTests(unittest.TestCase):
    def test_dellian_destroys_creature(self):
        me, opp = pair()
        w = bt.Walker(C["dellian"], 0)
        me.walkers.append(w)
        titan = on_board(opp, TITAN)
        ability = next(a for a in C["dellian"].pw_abilities if a[0] == -3)
        bt.activate_pw(me, opp, w, ability, 3, entry())
        bt.bury((me, opp), entry())
        self.assertNotIn(titan, opp.creatures)

    def test_dellian_zero_draws_and_loses(self):
        me, opp = pair()
        w = bt.Walker(C["dellian"], 0)
        me.walkers.append(w)
        ability = next(a for a in C["dellian"].pw_abilities if a[0] == 0)
        bt.activate_pw(me, opp, w, ability, 3, entry())
        self.assertEqual((len(me.hand), me.life), (1, 19))

    def test_dellian_emblem_drains_on_lifegain(self):
        me, opp = pair()
        w = bt.Walker(C["dellian"], 0)
        w.loyalty = 6
        me.walkers.append(w)
        ability = next(a for a in C["dellian"].pw_abilities if a[0] == -6)
        bt.activate_pw(me, opp, w, ability, 3, entry())
        bt.gain_life(me, 3)
        self.assertEqual(opp.life, 17)

    def test_ral_discard_and_reanimate(self):
        me, opp = pair()
        w = bt.Walker(C["ral"], 0)
        me.walkers.append(w)
        opp.hand = [CHEAP, CHEAP]
        bt.activate_pw(me, opp, w, next(a for a in C["ral"].pw_abilities if a[0] == -1), 3, entry())
        self.assertEqual(len(opp.hand), 1)
        me.graveyard.extend([OGRE, TITAN])
        w.loyalty = 3
        bt.activate_pw(me, opp, w, next(a for a in C["ral"].pw_abilities if a[0] == -2), 3, entry())
        self.assertTrue(any(c.card is OGRE for c in me.creatures))

    def test_ral_ultimate_skips_turns(self):
        me, opp = pair()
        w = bt.Walker(C["ral"], 0)
        w.loyalty = 7
        me.walkers.append(w)
        bt.random.seed(1)
        bt.activate_pw(me, opp, w, next(a for a in C["ral"].pw_abilities if a[0] == -7), 3, entry())
        skips = opp.skip_turns
        self.assertGreaterEqual(skips, 0)
        if skips:
            e = bt.take_turn(opp, me, 6, 4, skip_draw=False)
            self.assertEqual(opp.skip_turns, skips - 1)
            self.assertEqual(e.get("drew"), None)


class OtherTests(unittest.TestCase):
    def test_rabid_attack_death_draw(self):
        me, opp = pair()
        me.open, me.hand = [("B",), ("B",)], [C["rabid"]]
        ogre = on_board(me, OGRE)
        brute = on_board(opp, BRUTE)  # 4/4: mit +1/+0 tauscht der Ogre
        bt.combat_tricks(me, [(ogre, [brute])], opp, entry(), 3, True)
        self.assertNotIn(C["rabid"], me.hand)
        self.assertEqual((ogre.pump, ogre.once.get("death_draw")), (1, me.now))
        bt.resolve_combat([(ogre, [brute])])
        bt.bury((me, opp), entry())
        self.assertEqual(len(me.hand), 1)  # der Ogre stirbt und zieht

    def test_trudge_stun_by_x(self):
        me, opp = pair()
        me.next_x = 1
        bt._resolve(me, opp, C["trudge"], 3, entry())
        t = me.creatures[0]
        self.assertEqual((t.stun, t.tapped), (2, True))
        me, opp = pair()
        me.next_x = 3
        bt._resolve(me, opp, C["trudge"], 3, entry())
        t = me.creatures[0]
        self.assertEqual((t.stun, t.tapped), (0, False))


if __name__ == "__main__":
    unittest.main()
