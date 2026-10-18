"""L2: echte Planeswalker (306.5: Start-Loyalty; 606.3/606.6: eine Aktivierung pro Zug; 704.5i: Tod bei 0;
120.3c: Schaden nimmt Loyalty). Wahl: Lethal > Ultimate/Emblem > Removal > grosses Token > Ziehen > kleines Token >
Plus mit Wert > Plus ohne Wert; eine Minus-Faehigkeit, die auf 0 bringt, nur fuer Lethal, Ultimate oder Removal.
Angriff: echte Planeswalker immer, mit so wenig Schaden wie noetig (eigenes Lethal geht vor). Removal "creature or
planeswalker": einen echten Planeswalker, wenn es ihn toetet und der Gegner keine Kreatur mit Power 4+ hat; den
Jace-Token nur ab 5 Loyalty und ohne Kreatur als Ziel. Goldfish ohne Token und Removal."""
import unittest
from unittest import mock

from components import battle as bt
from components import simulation as sim
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS = W["Plains"]


def walker(name, cost, cmc, loyalty, text, sub, colors="U"):
    d = _card(name, f"Legendary Planeswalker {DASH} {sub}", cost, cmc, colors, text)
    d["loyalty"] = str(loyalty)
    return card_info(d)[0]


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="R"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


ISLAND, MOUNTAIN, FOREST = land("Island", "U"), land("Mountain", "R"), land("Forest", "G")
BEAR = W["Test Bear"]
OGRE = make("Ogre", CRE, "{2}{R}", 3, "", "3", "3")
TITAN = make("Titan", CRE, "{4}{G}", 5, "", "5", "5", colors="G")
BIRD = make("Bird", CRE, "{1}{W}", 2, "Flying", "1", "1", ["Flying"], "W")
DRAW = make("Study", "Sorcery", "{1}{U}", 2, "Draw a card.", colors="U")
WRATH = make("Wrath of the Bloodmane", "Instant", "{2}{R}", 3, "Wrath of the Bloodmane deals 4 damage to target creature "
             "or planeswalker.")
UNSUMMON = make("Unsummon", "Instant", "{U}", 1, "Return target creature to its owner's hand.", colors="U")

THEORIST = walker("The Theorist, Jace Beleren", "{2}{U}{U}", 4, 3, "At the beginning of each opponent's draw step, you "
                  "draw a card.\n+1: Create a 1/1 blue Illusion creature token.\n−2: For each opponent, return up to "
                  "one target artifact or creature that player controls to its owner's hand.\n−6: Draw three cards. "
                  "Then put X +1/+1 counters on each creature you control, where X is the number of cards in your hand.",
                  "Jace")
GARRUK = walker("Garruk, Curse Breaker", "{3}{G}{G}", 5, 5, "Whenever a creature you control with power 4 or greater "
                "enters, draw a card.\n+2: Untap up to two target lands.\n−3: Create a 4/4 green Beast creature token "
                "with trample.\n−4: Until your next turn, whenever one or more creatures attack one of your opponents, "
                "those creatures get +2/+2 and gain trample until end of turn.", "Garruk", "G")
BUTCHER = walker("Garruk, Veiled Butcher", "{3}{B}{B}", 5, 5, "If a creature an opponent controls would die, exile it "
                 "instead.\n+2: Up to one target creature gets -4/-1 until your next turn.\n−2: Each player sacrifices "
                 "a creature of their choice. If you sacrificed a creature this way, create a 4/4 green Beast creature "
                 "token with trample.\n−3: Each opponent discards two cards. For each opponent who didn't discard two "
                 "nonland cards this way, you draw a card.", "Garruk", "B")
RESOLUTE = walker("Ajani Resolute", "{1}{W}", 2, 2, "Whenever you gain life, put a loyalty counter on Ajani.\n0: You "
                  "gain 1 life.\n−4: Create a 2/2 white Cat Soldier creature token named Ajani's Pridemate with "
                  "\"Whenever you gain life, put a +1/+1 counter on this token.\"\n−10: You get an emblem with "
                  "\"Creatures you control get +2/+2.\"", "Ajani", "W")
UNRELENTING = walker("Ajani Unrelenting", "{4}{R}{R}", 6, 5, "Whenever you activate a loyalty ability, create a 2/2 "
                     "colorless Wizard Soldier creature token named Cadet.\n+1: Creatures you control get +1/+0 and gain "
                     "haste until end of turn.\n−2: Discard your hand, then draw a card for each creature you control.\n"
                     "−3: Ajani deals 4 damage to each creature except for tokens you control.", "Ajani", "R")
CHILL = walker("Chandra, Chill of Compliance", "{1}{U}{U}", 3, 3, "+1: Surveil 1. If you put a noncreature, nonland "
               "card into your graveyard this way, put that card into your hand.\n+1: Add {U}. Spend this mana only to "
               "cast a noncreature spell.\n−X: Tap target artifact or creature. Put X stun counters on it.\n−6: You get "
               "an emblem with \"Whenever you cast a spell, draw a card.\"", "Chandra")
TORCH = walker("Chandra, Torch of Defiance", "{2}{R}{R}", 4, 4, "+1: Exile the top card of your library. You may cast "
               "that card. If you don't, Chandra deals 2 damage to each opponent.\n+1: Add {R}{R}.\n−3: Chandra deals 4 "
               "damage to target creature.\n−7: You get an emblem with \"Whenever you cast a spell, this emblem deals 5 "
               "damage to any target.\"", "Chandra", "R")
SCULPTOR = walker("Jace, Reality Sculptor", "{3}{U}{U}", 5, 5, "+1: Empower Jace X, where X is the number of Islands "
                  "you control.\n−3: Until your next turn, whenever a creature attacks you or a planeswalker you "
                  "control, it gets -5/-0 until end of turn.\n0: Exile all but the bottom card of each opponent's "
                  "library. Activate only if there are twenty-five or more loyalty counters among Jaces you control.",
                  "Jace")
ENCH = "Legendary Enchantment"
MENTOR = make("Way of the Mentor", ENCH, "{2}{W}", 3, "When Way of the Mentor enters, empower Jace 5.\nWhenever you "
              "gain life, put a loyalty counter on each planeswalker you control.", colors="W")
NECRO = make("Way of the Necromancer", ENCH, "{1}{B}", 2, "When Way of the Necromancer enters, empower Jace 2.\n"
             "Whenever a creature you control dies, put a loyalty counter on each planeswalker you control.", colors="B")
WILD = make("Way of the Wildspeaker", ENCH, "{4}{G}", 5, "When Way of the Wildspeaker enters, empower Jace 7.\n"
            "Planeswalkers you control have \"[−4]: Create a 4/4 green Beast creature token with trample.\"", colors="G")
MIND = make("Way of the Mind Sculptor", ENCH, "{4}{U}", 5, "When Way of the Mind Sculptor enters, empower Jace 5.\n"
            "Whenever you activate a loyalty ability, if you removed two or more loyalty counters to activate it, draw "
            "a card.", colors="U")
LURKER = make("Sanctum Lurker", f"Creature {DASH} Horror", "{2}{B}", 3, "When this creature enters, empower Jace 1.\n"
              "Planeswalkers you control aren't put into their owners' graveyards for having 0 loyalty.\n"
              "Planeswalkers you control have \"[+2]: This planeswalker deals 1 damage to each opponent and you gain 1 "
              "life.\"", "3", "2", colors="B")
TETH = make("Inspired Tethermage", f"Creature {DASH} Human Wizard", "{2}{U}", 3, "Whenever you put one or more "
            "loyalty counters on a planeswalker, put a +1/+1 counter on this creature.\n{6}: Empower Jace 2.", "1", "3",
            colors="U")
WARLORD = make("Way of the Warlord", ENCH, "{2}{R}", 3, "When Way of the Warlord enters, empower Jace 5.\n"
               "Planeswalkers you control have \"[−4]: This planeswalker deals 2 damage to up to one target creature "
               "or planeswalker and 2 damage to target player.\"")
GOBLIN = make("Goblin", CRE, "{1}{R}", 2, "Haste", "2", "2", ["Haste"])
BOLT = make("Bolt of the Bloodmane", "Sorcery", "{2}{R}", 3, "Bolt of the Bloodmane deals 4 damage to target creature "
            "or planeswalker.")
HUGE = make("Huge", CRE, "{9}{R}", 10, "", "9", "9")
BIG8 = make("Big Eight", "Sorcery", "{8}", 8, "Big Eight deals 1 damage to each opponent.")
GIDEON = make("Gideon the Oathless", f"Legendary Creature {DASH} Human Mercenary", "{2}{B}", 3, "Whenever an opponent "
              "activates a loyalty ability, Gideon deals 1 damage to that player.", "3", "3", colors="B")


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


def put(p, card, loyalty=None, entered=0):
    w = bt.Walker(card, entered)
    if loyalty is not None:
        w.loyalty = loyalty
    p.walkers.append(w)
    return w


def names(p):
    return sorted(c.card.name for c in p.creatures)


class ParseTests(unittest.TestCase):
    def test_loyalty_and_costs(self):
        self.assertEqual((THEORIST.loyalty_start, [a[0] for a in THEORIST.pw_abilities]), (3, [1, -2, -6]))
        self.assertEqual([a[0] for a in CHILL.pw_abilities], [1, 1, "X", -6])
        self.assertEqual([a[0] for a in SCULPTOR.pw_abilities], [1, -3])  # Sonderwin (0) ausgelassen
        for card, n in ((GARRUK, 3), (BUTCHER, 3), (RESOLUTE, 3), (UNRELENTING, 3), (TORCH, 4)):
            self.assertEqual(len(card.pw_abilities), n, card.name)

    def test_statics(self):
        self.assertIn("opp_draw", THEORIST.pw_static)
        self.assertIn("big_enter_draw", GARRUK.pw_static)
        self.assertIn("lifegain_loyalty", RESOLUTE.pw_static)
        self.assertTrue(UNRELENTING.activation_tokens)

    def test_hits_walkers(self):
        self.assertTrue(WRATH.hits_walkers)
        self.assertFalse(UNSUMMON.hits_walkers)


class CastAndChoiceTests(unittest.TestCase):
    def test_cast_and_activate_in_the_same_turn(self):
        me, opp = pair()
        me.lands, me.hand = [ISLAND] * 4, [THEORIST]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(len(me.walkers), 1)
        self.assertEqual((me.walkers[0].loyalty, names(me)), (4, ["Illusion"]))

    def test_bounce_is_removal(self):
        me, opp = pair()
        put(me, THEORIST, 3)
        titan = on_board(opp, TITAN)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((titan in opp.creatures, TITAN in opp.hand, me.walkers[0].loyalty), (False, True, 1))

    def test_protection_prefers_plus_over_dying(self):
        me, opp = pair()
        put(me, GARRUK, 3)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((names(me), me.walkers[0].loyalty), ([], 5))

    def test_big_token_when_it_survives(self):
        me, opp = pair()
        put(me, GARRUK, 5)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((names(me), me.walkers[0].loyalty), (["Beast"], 2))

    def test_ultimate_emblem(self):
        me, opp = pair()
        put(me, RESOLUTE, 10)
        bear = on_board(me, BEAR)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((bear.power, bear.toughness, me.walkers), (4, 4, []))

    def test_walker_dies_at_zero(self):
        me, opp = pair()
        w = put(me, THEORIST, 2)
        on_board(opp, TITAN)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)  # -2 Bounce (Removal) bis 0
        self.assertEqual((me.walkers, THEORIST in me.graveyard), ([], True))
        self.assertEqual(w.loyalty, 0)


class StaticTests(unittest.TestCase):
    def test_theorist_draws_in_the_opponents_draw_step(self):
        me, opp = pair()
        put(me, THEORIST, 3)
        bt.take_turn(opp, me, 6, 3, skip_draw=False)
        self.assertEqual(len(me.library), 19)

    def test_garruk_draws_for_big_creatures(self):
        me, opp = pair()
        put(me, GARRUK, 5)
        bt._resolve(me, opp, TITAN, 3, entry())
        bt._resolve(me, opp, BEAR, 3, entry())
        self.assertEqual(len(me.library), 19)

    def test_resolute_grows_with_lifegain(self):
        me, _opp = pair()
        w = put(me, RESOLUTE, 2)
        bt.gain_life(me, 3, events=2)
        self.assertEqual(w.loyalty, 4)

    def test_unrelenting_cadet_on_any_activation(self):
        me, opp = pair()
        put(me, UNRELENTING, 5)
        me.jace.loyalty = 2  # der Jace-Token surveilt nach Main 2
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(names(me).count("Cadet"), 2)

    def test_cadet_for_granted_jace_activation(self):
        me, opp = pair()
        me.perms = [WILD]  # erweiterter Jace (L2a)
        me.jace.loyalty = 5
        put(me, UNRELENTING, 1)  # +1 ohne Kreaturen: Cadet, aber kein Wheel
        me.hand = [PLAINS, PLAINS]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(names(me).count("Cadet"), 2)

    def test_emblem_damage_on_cast(self):
        me, opp = pair()
        me.emblems.append(("cast_damage", 5))
        ogre = on_board(opp, OGRE)
        bt._resolve(me, opp, DRAW, 3, entry())
        self.assertEqual((ogre in opp.creatures, opp.life), (False, 20))
        opp.life = 5
        on_board(opp, OGRE)
        bt._resolve(me, opp, DRAW, 3, entry())
        self.assertEqual(opp.life, 0)  # Lethal geht vor

    def test_emblem_draws_on_cast(self):
        me, opp = pair()
        me.emblems.append(("cast_draw",))
        bt._resolve(me, opp, DRAW, 3, entry())
        self.assertEqual(len(me.library), 18)


class AbilityTests(unittest.TestCase):
    def _use(self, card, idx, loyalty=None, me=None, opp=None):
        if me is None:
            me, opp = pair()
        w = put(me, card, loyalty)
        bt.activate_pw(me, opp, w, card.pw_abilities[idx], 5, entry())
        return me, opp, w

    def test_sculptor_shield_on_their_attack(self):
        me, opp = pair()
        on_board(opp, TITAN)
        _m, _o, w = self._use(SCULPTOR, 1, me=me, opp=opp)
        bt.take_turn(opp, me, 6, 3, skip_draw=True)  # Titan greift den Planeswalker an, -5/-0
        self.assertEqual((me.life, w.loyalty), (20, 2))

    def test_butcher_debuff_kills_toughness_one(self):
        me, opp = pair()
        bird = on_board(opp, BIRD)
        self._use(BUTCHER, 0, me=me, opp=opp)
        self.assertNotIn(bird, opp.creatures)

    def test_butcher_edict_and_beast(self):
        me, opp = pair()
        on_board(me, BEAR._replace(name="Cadet", is_token=True))
        on_board(opp, OGRE)
        self._use(BUTCHER, 1, me=me, opp=opp)
        self.assertEqual((names(me), opp.creatures), (["Beast"], []))

    def test_unrelenting_sweep_spares_our_tokens(self):
        me, opp = pair()
        on_board(me, BEAR._replace(name="Cadet", is_token=True))
        on_board(opp, OGRE)
        on_board(opp, BEAR)
        self._use(UNRELENTING, 2, me=me, opp=opp)
        self.assertEqual((names(me), opp.creatures), (["Cadet", "Cadet"], []))

    def test_unrelenting_wheel(self):
        me, opp = pair()
        on_board(me, BEAR)
        on_board(me, OGRE)
        on_board(me, TITAN)
        me.hand = [PLAINS]
        self._use(UNRELENTING, 1, me=me, opp=opp)
        self.assertEqual((len(me.hand), PLAINS in me.graveyard), (4, True))  # Cadet aus dem Ausloeser zaehlt mit

    def test_torch_plus_and_minus(self):
        me, opp, _w = self._use(TORCH, 0)
        self.assertEqual((opp.life, len(me.library)), (18, 19))
        me, opp = pair()
        ogre = on_board(opp, OGRE)
        self._use(TORCH, 2, me=me, opp=opp)
        self.assertNotIn(ogre, opp.creatures)

    def test_chill_stun_x(self):
        me, opp = pair()
        titan = on_board(opp, TITAN)
        _m, _o, w = self._use(CHILL, 2, me=me, opp=opp)
        self.assertEqual((titan.tapped, titan.stun, w.loyalty), (True, 2, 1))

    def test_garruk_attack_buff(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        self._use(GARRUK, 2, me=me, opp=opp)
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["damage"], bear.has("trample")), (4, False))  # Pump bis Rundenende

    def test_theorist_ultimate(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        me.hand = [PLAINS]
        self._use(THEORIST, 2, loyalty=6, me=me, opp=opp)
        self.assertEqual((len(me.hand), bear.bonus), (4, 4))


class CombatTests(unittest.TestCase):
    def test_attack_walker_with_just_enough(self):
        me, opp = pair()
        w = put(opp, THEORIST, 3)
        on_board(me, BEAR)
        on_board(me, OGRE)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((opp.walkers, opp.life), ([], 18))
        self.assertEqual(w.loyalty, 0)

    def test_attack_walker_with_all_when_it_cannot_die(self):
        me, opp = pair()
        w = put(opp, GARRUK, 10)
        on_board(me, BEAR)
        on_board(me, OGRE)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((w.loyalty, opp.life), (5, 20))

    def test_lethal_on_the_player_first(self):
        me, opp = pair()
        w = put(opp, THEORIST, 3)
        on_board(me, OGRE)
        on_board(me, BEAR)
        opp.life = 5
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertLessEqual(opp.life, 0)
        self.assertEqual(w.loyalty, 3)

    def test_removal_kills_a_walker(self):
        me, opp = pair()
        put(opp, THEORIST, 4)
        bear = on_board(opp, BEAR)
        bt.cast_removal(WRATH, me, opp, entry(), 5)
        self.assertEqual((opp.walkers, bear in opp.creatures), ([], True))

    def test_removal_prefers_creature_when_a_big_one_is_there(self):
        me, opp = pair()
        put(opp, THEORIST, 4)
        on_board(opp, TITAN)
        bear = on_board(opp, BEAR)
        bt.cast_removal(WRATH, me, opp, entry(), 5)
        self.assertEqual((len(opp.walkers), bear in opp.creatures), (1, False))

    def test_removal_on_a_big_jace_token(self):
        me, opp = pair()
        opp.jace.loyalty = 5
        bt.cast_removal(WRATH, me, opp, entry(), 5)
        self.assertEqual(opp.jace.loyalty, 1)
        opp.jace.loyalty = 4
        bt.cast_removal(WRATH, me, opp, entry(), 5)
        self.assertEqual(opp.jace.loyalty, 4)


class EnvironmentTests(unittest.TestCase):
    """Karten fuer "each planeswalker you control" und Ausloeser bei Aktivierungen gelten auch fuer echte Planeswalker."""

    def test_cast_emblem_needs_a_spell_in_hand(self):
        me, opp = pair()
        w = put(me, TORCH, 7)
        self.assertEqual(bt.pw_options(me, opp, w, 5, "after")[0][2], 1)
        me.hand = [DRAW]
        self.assertEqual(bt.pw_options(me, opp, w, 5, "after")[0][2], -7)

    def test_mentor_and_necromancer(self):
        me, _opp = pair()
        me.perms = [MENTOR, NECRO]
        w = put(me, THEORIST, 3)
        bt.gain_life(me, 2)
        bear = on_board(me, BEAR)
        bear.dead = True
        bt.bury((me,), entry())
        self.assertEqual(w.loyalty, 5)

    def test_lurker_keeps_a_walker_at_zero(self):
        me, opp = pair()
        on_board(me, LURKER)
        on_board(opp, TITAN)
        w = put(me, THEORIST, 2)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((me.walkers, w.loyalty), ([w], 0))

    def test_granted_ability(self):
        me, opp = pair()
        me.perms = [WILD]
        put(me, BUTCHER, 5)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((names(me), me.walkers[0].loyalty), (["Beast"], 1))

    def test_tethermage_gideon_and_mind_sculptor(self):
        me, opp = pair()
        teth = on_board(me, TETH)
        on_board(opp, GIDEON)
        put(me, GARRUK, 3)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)  # +2
        self.assertEqual((teth.bonus, me.life), (1, 19))
        me, opp = pair()
        me.perms = [MIND]
        on_board(opp, TITAN)
        put(me, THEORIST, 3)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)  # -2 Bounce
        self.assertEqual(len(me.library), 19)


class MoreChoiceTests(unittest.TestCase):
    def test_ranks(self):
        me, opp = pair()
        rank = lambda card, i: bt.pw_rank(me, opp, bt.Walker(card), *card.pw_abilities[i], 5, "after")[0]
        self.assertEqual((rank(GARRUK, 1), rank(THEORIST, 0), rank(TORCH, 0), rank(GARRUK, 0)), (5, 3, 2, 1))
        opp.life = 2
        self.assertEqual(rank(TORCH, 0), 8)

    def test_lethal_before_removal(self):
        me, opp = pair()
        ogre = on_board(opp, OGRE)
        opp.life = 2
        put(me, TORCH, 4)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((opp.life <= 0, ogre in opp.creatures), (True, True))

    def test_wheel_counts_the_cadet(self):
        me, opp = pair()
        w = put(me, UNRELENTING, 5)
        self.assertEqual(bt.pw_options(me, opp, w, 5, "after")[0][2], -2)  # leere Hand, der Cadet zieht eine Karte
        me.hand = [PLAINS]
        self.assertNotEqual(bt.pw_options(me, opp, w, 5, "after")[0][2], -2)

    def test_mana_before_casting(self):
        me, opp = pair()
        me.lands, me.hand = [MOUNTAIN], [OGRE]
        put(me, TORCH, 4)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(names(me), ["Ogre"])

    def test_fresh_walker_removes_a_blocker_before_combat(self):
        me, opp = pair()
        me.lands, me.hand = [ISLAND] * 4, [THEORIST]
        on_board(me, BEAR)
        on_board(opp, OGRE)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((OGRE in opp.hand, opp.life), (True, 18))

    def test_team_pump_waits_for_the_haste_creature(self):
        me, opp = pair()
        me.lands, me.hand = [MOUNTAIN] * 2, [GOBLIN, OGRE, TITAN]  # volle Hand: kein Wheel
        put(me, UNRELENTING, 5)
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 6)  # Goblin und Cadet je 3

    def test_granted_bolt(self):
        me, opp = pair()
        me.perms = [WARLORD]
        bear = on_board(opp, BEAR)
        put(me, GARRUK, 5)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((bear in opp.creatures, opp.life), (False, 18))

    def test_no_enter_effects(self):
        me, opp = pair()
        opp.hand = [PLAINS, PLAINS]
        bt._resolve(me, opp, BUTCHER, 3, entry())
        self.assertEqual((len(opp.hand), len(me.walkers)), (2, 1))

    def test_one_activation_each_turn(self):
        me, opp = pair()
        w = put(me, TORCH, 4)
        w.used = True
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(w.loyalty, 5)

    def test_debuff_until_my_next_turn(self):
        me, opp = pair()
        ogre = on_board(opp, OGRE)
        put(me, BUTCHER, 5)
        w = me.walkers[0]
        bt.activate_pw(me, opp, w, BUTCHER.pw_abilities[0], 5, entry())
        self.assertEqual((ogre.power, ogre.toughness), (-1, 2))
        bt.expire_until_next_turn(me, 5)
        self.assertEqual(ogre.power, -1)
        bt.expire_until_next_turn(me, 7)
        self.assertEqual((ogre.power, ogre.toughness), (3, 3))

    def test_removal_has_a_walker_as_target(self):
        me, opp = pair()
        put(opp, THEORIST, 3)
        self.assertTrue(bt.has_target(BOLT, me, opp))
        opp.walkers = []
        self.assertFalse(bt.has_target(BOLT, me, opp))


class GoldfishTests(unittest.TestCase):
    def _run(self, hand, rest):
        with mock.patch("components.mulligan.random.shuffle", lambda x: None):
            return sim.simulate(hand + rest, 1, False, 3, 8, True, False, None, 11, 20, 6, True, 3, 6, False, False, 5,
                                True)

    def test_goldfish_emblems(self):
        r = self._run([MOUNTAIN] * 4 + [TORCH, BIG8, HUGE], [MOUNTAIN] * 20)
        self.assertEqual(r["effects"]["face"], 12)  # 3 x 2, Ultimate in Runde 7, Runde 8: Big Eight 1 + Emblem 5
        r = self._run([ISLAND] * 4 + [CHILL, BIG8, HUGE], [ISLAND] * 20)
        self.assertEqual(r["lands_drawn"], 12)  # Ultimate in Runde 6, Big Eight zieht in Runde 8 ein Land

    def test_goldfish_loyalty_counts(self):
        hand = [MOUNTAIN] * 5 + [TORCH, HUGE]
        order = hand + [MOUNTAIN] * 20
        with mock.patch("components.mulligan.random.shuffle", lambda x: None):
            r = sim.simulate(order, 1, False, 3, 8, True, False, None, 11, 20, 6, True, 3, 6, False, False, 5, True)
        self.assertEqual(r["effects"]["face"], 6)  # Runden 4-6 je 2 Schaden, in Runde 7 das Ultimate

    def test_cast_emblem_needs_a_spell(self):
        self.assertEqual(sim.pw_choice(TORCH, 7, spells=0)[0], 1)
        self.assertEqual(sim.pw_choice(TORCH, 7, spells=1)[0], -7)

    def test_choice_without_tokens(self):
        self.assertEqual(sim.pw_choice(THEORIST, 3, lands=4, creatures=0, hand=2)[0], 1)
        self.assertEqual(sim.pw_choice(GARRUK, 5, lands=4, creatures=0, hand=2)[0], 2)  # Beast gibt es nicht
        self.assertEqual(sim.pw_choice(RESOLUTE, 10, lands=4, creatures=1, hand=2)[0], -10)

    def test_goldfish_torch_pings(self):
        hand = [MOUNTAIN] * 6 + [TORCH]
        order = hand + [MOUNTAIN] * 20
        with mock.patch("components.mulligan.random.shuffle", lambda x: None):
            r = sim.simulate(order, 1, False, 3, 8, True, False, None, 11, 20, 6, True, 3, 6, False, False, 5, True)
        self.assertGreaterEqual(r["effects"]["face"], 8)  # ab Runde 4 jede Runde 2 Schaden


if __name__ == "__main__":
    unittest.main()
