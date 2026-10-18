"""L2a+: Way of the Cryomancer und Jace's Machinations.

Cryomancer gibt allen eigenen Planeswalkern "[−3]: When you next cast an instant or sorcery spell this turn, copy that
spell." Die Kopie wird nicht gewirkt (707.10: kein Prowess, kein "whenever you cast") und darf neue Ziele haben
(707.10c). Aktiviert nur in Main 1 vor dem Zaubern, wenn der erste geplante Instant/Sorcery sich lohnt: Lethal 8,
Removal mit einem zweiten gueltigen Ziel 6, Ziehen 4, sonst 2. Echte Planeswalker nur fuer Lethal oder Removal. Der
Jace-Token zieht dann nicht schon zu Beginn des Zugs. Goldfish: nur Schaden.

Machinations: am Ende des gegnerischen Zugs gewirkt (Empower 8), danach je eine zusaetzliche Aktivierung des
Jace-Tokens und jedes echten Jace-Planeswalkers (606.3 zaehlt je Zug); andere Planeswalker nicht. Goldfish gleich."""
import unittest
from unittest import mock

from components import battle as bt
from components import simulation as sim
from components.cards import card_info
from components.jace import JaceState
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
ENCH = "Legendary Enchantment"
PLAINS = W["Plains"]


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="R"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


def walker(name, cost, cmc, loyalty, text, sub, colors="U"):
    d = _card(name, f"Legendary Planeswalker {DASH} {sub}", cost, cmc, colors, text)
    d["loyalty"] = str(loyalty)
    return card_info(d)[0]


ISLAND, MOUNTAIN = land("Island", "U"), land("Mountain", "R")
OGRE = make("Ogre", CRE, "{2}{R}", 3, "", "3", "3")
MONK = make("Monk", CRE, "{1}{R}", 2, "Prowess", "1", "1", ["Prowess"])
CRYO = make("Way of the Cryomancer", ENCH, "{2}{U}", 3, "When Way of the Cryomancer enters, empower Jace 5.\n"
            "Planeswalkers you control have \"[−3]: When you next cast an instant or sorcery spell this turn, copy "
            "that spell. You may choose new targets for the copy.\"", colors="U")
MACH = make("Jace's Machinations", "Instant", "{2}{U}", 3, "Until end of turn, you may activate loyalty abilities of "
            "Jace planeswalkers you control on any player's turn any time you could cast an instant.\nEmpower Jace 8.",
            colors="U")
SHOCK = make("Searing Shock", "Sorcery", "{1}{R}", 2, "Searing Shock deals 3 damage to target creature.")
FIRE = make("Fire Rain", "Sorcery", "{1}{R}", 2, "Fire Rain deals 2 damage to each opponent.")
FIRE4 = make("Fire Storm", "Sorcery", "{3}{R}", 4, "Fire Storm deals 2 damage to each opponent.")
FIRE5 = make("Fire Wave", "Sorcery", "{4}{R}", 5, "Fire Wave deals 2 damage to each opponent.")
STUDY = make("Study", "Sorcery", "{1}{U}", 2, "Draw a card.", colors="U")
THEORIST = walker("The Theorist, Jace Beleren", "{2}{U}{U}", 4, 3, "At the beginning of each opponent's draw step, you "
                  "draw a card.\n+1: Create a 1/1 blue Illusion creature token.\n−2: For each opponent, return up to "
                  "one target artifact or creature that player controls to its owner's hand.\n−6: Draw three cards. "
                  "Then put X +1/+1 counters on each creature you control, where X is the number of cards in your hand.",
                  "Jace")
GARRUK = walker("Garruk, Curse Breaker", "{3}{G}{G}", 5, 5, "Whenever a creature you control with power 4 or greater "
                "enters, draw a card.\n+2: Untap up to two target lands.\n−3: Create a 4/4 green Beast creature token "
                "with trample.\n−4: Until your next turn, whenever one or more creatures attack one of your opponents, "
                "those creatures get +2/+2 and gain trample until end of turn.", "Garruk", "G")
SCULPT = walker("Jace, Reality Sculptor", "{3}{U}{U}", 5, 5, "+1: Empower Jace X, where X is the number of Islands "
                "you control.\n−3: Until your next turn, whenever a creature attacks you or a planeswalker you "
                "control, it gets -5/-0 until end of turn.", "Jace")
HUGE = make("Huge", CRE, "{9}{R}", 10, "", "9", "9")
AWAKEN = make("Awakening", "Sorcery", "{1}{U}", 2, "Empower Jace 2.", colors="U")
TRINKET = make("Trinket", "Artifact", "{1}", 1, "")
TORCH = walker("Chandra, Torch of Defiance", "{2}{R}{R}", 4, 4, "+1: Exile the top card of your library. You may cast "
               "that card. If you don't, Chandra deals 2 damage to each opponent.\n+1: Add {R}{R}.\n−3: Chandra deals 4 "
               "damage to target creature.\n−7: You get an emblem with \"Whenever you cast a spell, this emblem deals 5 "
               "damage to any target.\"", "Chandra", "R")


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
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


def put(p, card, loyalty=None):
    w = bt.Walker(card, 0)
    if loyalty is not None:
        w.loyalty = loyalty
    p.walkers.append(w)
    return w


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertEqual((CRYO.copy_grant, CRYO.walker_grants), (-3, ()))
        self.assertTrue(MACH.jace_instant)
        self.assertFalse(STUDY.jace_instant)


class CopyTests(unittest.TestCase):
    def test_copy_is_not_cast(self):
        me, opp = pair()
        monk = on_board(me, MONK)
        me.copy_next = 3
        bt._resolve(me, opp, FIRE, 3, entry())
        self.assertEqual((opp.life, monk.pump, me.copy_next), (16, 1, None))  # Prowess nur einmal

    def test_copy_only_this_turn(self):
        me, opp = pair()
        me.copy_next = 3
        bt._resolve(me, opp, FIRE, 5, entry())
        self.assertEqual(opp.life, 18)

    def test_copy_gets_a_new_target(self):
        me, opp = pair()
        on_board(opp, OGRE)
        on_board(opp, OGRE)
        me.copy_next = 3
        bt._resolve(me, opp, SHOCK, 3, entry())
        self.assertEqual(opp.creatures, [])

    def test_copy_empowers_too(self):
        me, opp = pair()
        me.copy_next = 3
        bt._resolve(me, opp, AWAKEN, 3, entry())
        self.assertEqual(me.jace.loyalty, 4)  # Empower ist Teil des Effekts, nicht des Wirkens

    def test_copy_draws_again(self):
        me, opp = pair()
        me.copy_next = 3
        bt._resolve(me, opp, STUDY, 3, entry())
        self.assertEqual(len(me.library), 18)


class TokenChoiceTests(unittest.TestCase):
    def test_token_copies_removal_instead_of_drawing_at_turn_start(self):
        me, opp = pair()
        me.perms, me.jace.loyalty = [CRYO], 4
        me.lands, me.hand = [MOUNTAIN] * 2, [SHOCK]
        on_board(opp, OGRE)
        on_board(opp, OGRE)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((opp.creatures, me.jace.loyalty), ([], 1))

    def test_token_copy_for_lethal(self):
        me, opp = pair()
        me.perms, me.jace.loyalty, opp.life = [CRYO], 3, 4
        me.lands, me.hand = [MOUNTAIN] * 2, [FIRE]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertLessEqual(opp.life, 0)

    def test_token_rank_for_a_draw_spell(self):
        me, opp = pair()
        me.perms, me.jace.loyalty = [CRYO], 3
        me.hand = [STUDY]
        opts = bt.walker_options(me, opp, 5, "main1", [("U",), ("U",)], [STUDY])
        copy = [o for o in opts if o[3] == (("copy_next",),)]
        self.assertEqual(copy[0][0], 4)
        self.assertEqual(bt.walker_options(me, opp, 5, "after", [("U",), ("U",)], [STUDY])[0][3][0][0], "draw")

    def test_no_copy_without_a_spell(self):
        me, opp = pair()
        me.perms, me.jace.loyalty = [CRYO], 3
        bt.take_turn(me, opp, 5, 3, skip_draw=True)  # zieht wie bisher zu Beginn des Zugs und legt das Land
        self.assertEqual((me.jace.loyalty, len(me.lands)), (0, 1))

    def test_no_copy_with_only_one_target(self):
        me, opp = pair()
        me.perms, me.jace.loyalty = [CRYO], 4
        me.lands, me.hand = [MOUNTAIN] * 2, [SHOCK]
        on_board(opp, OGRE)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((opp.creatures, len(me.library)), ([], 19))  # Jace zieht nach Main 2 statt zu kopieren

    def test_copies_the_first_instant_or_sorcery(self):
        me, opp = pair()
        me.perms, me.jace.loyalty = [CRYO], 4
        me.lands, me.hand = [MOUNTAIN] * 3, [TRINKET, SHOCK]  # das Artefakt kommt in der Planung zuerst
        on_board(opp, OGRE)
        on_board(opp, OGRE)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(opp.creatures, [])

    def test_token_copies_a_planned_draw_spell(self):
        me, opp = pair()
        me.perms, me.jace.loyalty = [CRYO], 3
        me.lands, me.hand = [ISLAND] * 2, [STUDY]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertIn("Wir: Kopie von Study", e["events"])
        self.assertEqual(len(me.library), 18)  # Study und Kopie ziehen je eine Karte


class RealWalkerTests(unittest.TestCase):
    def test_real_walker_copies_removal(self):
        me, opp = pair()
        me.perms = [CRYO]
        me.lands, me.hand = [MOUNTAIN] * 2, [SHOCK]
        on_board(opp, OGRE)
        on_board(opp, OGRE)
        put(me, TORCH, 4)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((opp.creatures, me.walkers[0].loyalty), ([], 1))

    def test_real_walker_prefers_the_copy(self):
        me, opp = pair()
        me.perms = [CRYO]
        me.lands, me.hand = [MOUNTAIN] * 2, [SHOCK]
        on_board(opp, OGRE)
        on_board(opp, OGRE)
        w = put(me, GARRUK, 5)  # Kopie (Removal) vor dem Beast
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((opp.creatures, me.creatures, w.loyalty), ([], [], 2))

    def test_real_walker_not_for_a_draw_spell(self):
        me, opp = pair()
        me.perms = [CRYO]
        me.lands, me.hand = [ISLAND] * 2, [STUDY]
        w = put(me, TORCH, 4)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(w.loyalty, 5)


class MachinationsTests(unittest.TestCase):
    def _cast(self, me, opp, step=6):
        me.hand = [MACH]
        me.open = [ISLAND.land_colors] * 3
        bt.end_step_instants(me, opp, entry(), step)

    def test_extra_jace_activation(self):
        me, opp = pair()
        me.jace.used = True
        self._cast(me, opp)
        self.assertEqual((me.jace.loyalty, len(me.library)), (5, 19))  # Empower 8, dann -3 Ziehen

    def test_real_jace_but_not_other_walkers(self):
        me, opp = pair()
        jace = put(me, THEORIST, 3)
        torch = put(me, TORCH, 4)
        jace.used = torch.used = True
        self._cast(me, opp)
        self.assertEqual((jace.loyalty, torch.loyalty), (4, 4))

    def test_no_extra_activation_in_own_turn(self):
        me, opp = pair()
        me.turn_start, me.jace.used = 6, True
        bt._resolve(me, opp, MACH, 6, entry())
        self.assertEqual(me.jace.loyalty, 8)


class GoldfishTests(unittest.TestCase):
    def _run(self, order, horizon, dmg_target=20):
        with mock.patch("components.mulligan.random.shuffle", lambda x: None):
            return sim.simulate(order, 1, False, 3, horizon, True, False, None, 11, dmg_target, 6, True, 3, 6, False,
                                False, 5, True)

    def test_copy_choice_only_damage(self):
        self.assertEqual(sim.walker_choice(5, [CRYO], 4, 3, copy_face=2)[1], (("copy_next",),))
        self.assertEqual(sim.walker_choice(5, [CRYO], 20, 3, copy_face=2)[1], (("draw", 1),))  # Ziehen vor Schaden
        self.assertEqual(sim.walker_choice(5, [CRYO], 20, 3, copy_face=0)[1], (("draw", 1),))
        self.assertEqual(sim.pw_choice(TORCH, 4, sources=[CRYO], face_need=4, copy_face=2)[0], -3)
        self.assertNotEqual(sim.pw_choice(TORCH, 4, sources=[CRYO], face_need=20, copy_face=2)[0], -3)

    def test_goldfish_token_waits_and_copies(self):
        jst = JaceState()
        jst.loyalty = 5
        args = ([CRYO], [FIRE4], [PLAINS] * 5, [MOUNTAIN] * 4, [], [], {}, 5, 4)
        sim.goldfish_walker(jst, "start", *args)
        self.assertEqual(jst.loyalty, 5)  # wartet mit dem Ziehen bis Main 1
        out = sim.goldfish_walker(jst, "main1", *args, copy_face=2)
        self.assertEqual((out["copy"], jst.loyalty), (True, 2))
        jst = JaceState()
        jst.loyalty = 5
        sim.goldfish_walker(jst, "start", [CRYO], [PLAINS], [PLAINS] * 5, [MOUNTAIN] * 4, [], [], {}, 5, 4)
        self.assertEqual(jst.loyalty, 2)  # ohne Instant/Sorcery auf der Hand zieht er wie bisher

    def test_goldfish_real_walker_copies_for_lethal(self):
        hand = [ISLAND, ISLAND, ISLAND, MOUNTAIN, CRYO, THEORIST, FIRE5]
        order = hand + [MOUNTAIN] + [PLAINS] * 20
        r = self._run(order, 5, dmg_target=4)  # R3 Cryomancer, R4 Theorist, R5 Fire Wave kopiert: 2 + 2
        self.assertEqual(r["effects"]["face"], 4)
        r = self._run(order, 5, dmg_target=20)  # kein Lethal: keine Kopie
        self.assertEqual(r["effects"]["face"], 2)

    def test_goldfish_real_walker_pays_loyalty_for_the_copy(self):
        hand = [ISLAND, ISLAND, ISLAND, MOUNTAIN, CRYO, THEORIST, FIRE5]
        order = hand + [MOUNTAIN, FIRE5] + [PLAINS] * 20
        r = self._run(order, 6, dmg_target=4)  # R5 Kopie (Theorist 4 -> 1), R6 nur Fire Wave
        self.assertEqual(r["effects"]["face"], 6)

    def test_goldfish_copy_costs_loyalty(self):
        order = [ISLAND, MOUNTAIN, MOUNTAIN, MOUNTAIN, CRYO, TORCH, FIRE5] + [MOUNTAIN] * 3 + [HUGE] + [MOUNTAIN] * 20
        r = self._run(order, 8, dmg_target=6)  # R5 Kopie (Loyalty 5 -> 2), danach +1 bis 5: kein Ultimate
        self.assertEqual(r["effects"]["face"], 12)

    def test_goldfish_machinations_for_a_real_jace(self):
        order = [ISLAND] * 6 + [SCULPT] + [ISLAND] * 4 + [MACH] + [ISLAND] * 20
        r = self._run(order, 7)  # R6: Jace, Reality Sculptor +1 zweimal
        self.assertEqual(r["jace"]["gained_all"], 32)

    def test_goldfish_machinations(self):
        hand = [ISLAND] * 6 + [MACH]
        order = hand + [ISLAND] * 20
        r = self._run(order, 3)
        self.assertEqual(r["jace"]["acts_all"], 2)  # R3: Empower 8, -3 Ziehen, zusaetzlich nochmal -3 Ziehen


if __name__ == "__main__":
    unittest.main()
