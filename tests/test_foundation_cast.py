"""Grundlagen fuer kommende Sets, Teil 3: allgemeine Ausloeser "Whenever you cast ..." (Nichtkreatur-, Instant/
Sorcery-, mehrfarbige Zauber, Zauber mit Kreatur als Ziel bzw. mit eigener Kreatur als Ziel) mit Pump,
Schluesselwoertern, Marken, Schaden, Leben, Ziehen, Token und Unblockbarkeit; Opus ("If five or more mana was spent")
mit "instead" und "also". Kartentexte aus SOS, HOB und MSH."""
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


def make(*args, **kwargs):
    return card_info(raw(*args, **kwargs))[0]


def cre(name, types, cost, cmc, text, pt, keywords=(), colors="W"):
    return raw(name, f"Creature {DASH} {types}", cost, cmc, text, pt[0], pt[1], keywords, colors)


RAW = {
    "scornmage": cre("Lecturing Scornmage", "Human Warlock", "{B}", 1, "Repartee — Whenever you cast an instant or "
                     "sorcery spell that targets a creature, put a +1/+1 counter on this creature.", "11",
                     ["Repartee"], "B"),
    "thunderdrum": cre("Thunderdrum Soloist", "Dwarf Bard", "{1}{R}", 2, "Reach\nOpus — Whenever you cast an instant "
                       "or sorcery spell, this creature deals 1 damage to each opponent. If five or more mana was "
                       "spent to cast that spell, this creature deals 3 damage to each opponent instead.", "13",
                       ["Reach", "Opus"], "R"),
    "tackle": cre("Tackle Artist", "Orc Sorcerer", "{3}{R}", 4, "Trample\nOpus — Whenever you cast an instant or "
                  "sorcery spell, put a +1/+1 counter on this creature. If five or more mana was spent to cast that "
                  "spell, put two +1/+1 counters on this creature instead.", "43", ["Trample", "Opus"], "R"),
    "firedancer": cre("Expressive Firedancer", "Human Sorcerer", "{1}{R}", 2, "Opus — Whenever you cast an instant "
                      "or sorcery spell, this creature gets +1/+1 until end of turn. If five or more mana was spent to "
                      "cast that spell, this creature also gains double strike until end of turn.", "22", ["Opus"],
                      "R"),
    "deluge": cre("Deluge Virtuoso", "Human Wizard", "{2}{U}", 3, "Opus — Whenever you cast an instant or sorcery "
                  "spell, this creature gets +1/+1 until end of turn. If five or more mana was spent to cast that "
                  "spell, this creature gets +2/+2 until end of turn instead.", "22", ["Opus"], "U"),
    "skywhale": cre("Spectacular Skywhale", "Elemental Whale", "{2}{U}{R}", 4, "Flying\nOpus — Whenever you cast an "
                    "instant or sorcery spell, this creature gets +3/+0 until end of turn. If five or more mana was "
                    "spent to cast that spell, put three +1/+1 counters on this creature instead.", "14",
                    ["Flying", "Opus"], "UR"),
    "poet": cre("Melancholic Poet", "Elf Bard", "{1}{B}", 2, "Repartee — Whenever you cast an instant or sorcery "
                "spell that targets a creature, each opponent loses 1 life and you gain 1 life.", "22", ["Repartee"],
                "B"),
    "inkwright": cre("Informed Inkwright", "Human Wizard", "{1}{W}", 2, "Vigilance\nRepartee — Whenever you cast an "
                     "instant or sorcery spell that targets a creature, create a 1/1 white and black Inkling creature "
                     "token with flying.", "22", ["Vigilance", "Repartee"]),
    "hopesinger": cre("Stirring Hopesinger", "Bird Bard", "{2}{W}", 3, "Flying, lifelink\nRepartee — Whenever you "
                      "cast an instant or sorcery spell that targets a creature, put a +1/+1 counter on each creature "
                      "you control.", "13", ["Flying", "Lifelink", "Repartee"]),
    "gandalf": cre("Gandalf, Goblins' Bane", "Avatar Wizard", "{2}{R}", 3, "Whenever you cast a noncreature spell, "
                   "Gandalf gets +1/+1 until end of turn and deals 1 damage to each opponent.", "23", colors="R"),
    "mockingbird": cre("Mockingbird, Ace Agent", "Human Spy Hero", "{3}{W}", 4, "Double strike\nWhenever you cast a "
                       "spell that targets a creature you control, put a +1/+1 counter on Mockingbird.", "22",
                       ["Double strike"]),
    "referee": raw("Mage Tower Referee", f"Artifact Creature {DASH} Construct", "{2}", 2, "Whenever you cast a "
                   "multicolored spell, put a +1/+1 counter on this creature.", "2", "1", colors=""),
    "snooping": cre("Snooping Page", "Human Cleric", "{1}{W}{B}", 3, "Repartee — Whenever you cast an instant or "
                    "sorcery spell that targets a creature, this creature can't be blocked this turn.", "23",
                    ["Repartee"], "WB"),
    "muse": cre("Muse Seeker", "Elf Wizard", "{1}{U}", 2, "Opus — Whenever you cast an instant or sorcery spell, draw "
                "a card. Then discard a card unless five or more mana was spent to cast that spell.", "12", ["Opus"],
                "U"),
    "graduation": raw("Graduation Day", "Enchantment", "{W}", 1, "Repartee — Whenever you cast an instant or sorcery "
                      "spell that targets a creature, put a +1/+1 counter on target creature you control.",
                      keywords=["Repartee"]),
    "mascot": cre("Inkling Mascot", "Inkling Cat", "{W}{B}", 2, "Repartee — Whenever you cast an instant or sorcery "
                  "spell that targets a creature, this creature gains flying until end of turn. Surveil 1. (Look at "
                  "the top card of your library. You may put it into your graveyard.)", "22", ["Surveil", "Repartee"],
                  "WB"),
    "debater": cre("Rehearsed Debater", "Djinn Bard", "{2}{W}", 3, "Vigilance\nRepartee — Whenever you cast an "
                   "instant or sorcery spell that targets a creature, this creature gets +1/+1 until end of turn.",
                   "33", ["Vigilance", "Repartee"]),
    "demonstrator": cre("Inkshape Demonstrator", "Elephant Cleric", "{3}{W}", 4, "Repartee — Whenever you cast an "
                        "instant or sorcery spell that targets a creature, this creature gets +1/+0 and gains "
                        "lifelink until end of turn.", "34", ["Repartee"]),
    "rally": raw("Test Rally Totem", "Artifact", "{3}", 3, "Whenever you cast a noncreature spell, put a +1/+1 counter "
                 "on each other creature you control.", colors=""),
    "thor": cre("Thor, God of Thunder", "God Hero", "{3}{R}{R}", 5, "Whenever you cast a noncreature spell, Thor deals "
                "damage equal to that spell's mana value to any target.", "55", colors="R"),
    "pinger": cre("Test Pinger", "Wizard", "{1}{R}", 2, "Whenever you cast a noncreature spell, this creature deals 2 "
                  "damage to any target.", "12", colors="R"),
    "manawurm": cre("Aberrant Manawurm", "Wurm", "{3}{U}", 4, "Trample\nWhenever you cast an instant or sorcery spell, "
                    "this creature gets +X/+0 until end of turn, where X is the amount of mana spent to cast that "
                    "spell.", "25", ["Trample"], "U"),
    "dancing": raw("Dancing from Dark to Dawn", "Enchantment", "{2}{G}", 3, "Whenever you cast a creature spell, put X "
                   "+1/+1 counters on target creature you control, where X is that spell's mana value.", colors="G"),
    "hydra": cre("Madame Hydra", "Human Villain", "{2}{B}", 3, "Whenever you cast a Villain spell, create a 2/1 black "
                 "Villain creature token with menace.", "23", colors="B"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}

KILL = make("Murder", "Instant", "{1}{B}{B}", 3, "Destroy target creature.", colors="B")
BIG_KILL = make("Big Murder", "Sorcery", "{4}{B}", 5, "Destroy target creature.", colors="B")
PUMP = make("Giant Growth", "Instant", "{G}", 1, "Target creature gets +3/+3 until end of turn.", colors="G")
FACE = make("Shock", "Instant", "{R}", 1, "Shock deals 2 damage to any target.", colors="R")
DRAW = make("Divination", "Sorcery", "{2}{U}", 3, "Draw two cards.", colors="U")
BIG_DRAW = make("Big Study", "Sorcery", "{4}{U}", 5, "Draw two cards.", colors="U")
RELIC = make("Relic", "Artifact", "{2}", 2, "", colors="")
OGRE = make("Ogre", f"Creature {DASH} Ogre", "{2}{R}", 3, "", "3", "3", colors="R")
GOLD = make("Gold Bolt", "Instant", "{R}{W}", 2, "Gold Bolt deals 2 damage to any target.", colors="RW")


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


class ParseTests(unittest.TestCase):
    def trig(self, key):
        self.assertEqual(len(C[key].cast_trig), 1, key)
        return C[key].cast_trig[0]

    def test_repartee_counter(self):
        self.assertEqual(self.trig("scornmage"), ("instsorc_creature", (("counter", 1),), (), ""))

    def test_opus_instead(self):
        self.assertEqual(self.trig("thunderdrum"), ("instsorc", (("face", 1),), (("face", 3),), "instead"))
        self.assertEqual(self.trig("tackle"), ("instsorc", (("counter", 1),), (("counter", 2),), "instead"))
        self.assertEqual(self.trig("deluge"), ("instsorc", (("pump", 1, 1),), (("pump", 2, 2),), "instead"))
        self.assertEqual(self.trig("skywhale"), ("instsorc", (("pump", 3, 0),), (("counter", 3),), "instead"))

    def test_opus_also(self):
        self.assertEqual(self.trig("firedancer"),
                         ("instsorc", (("pump", 1, 1),), (("kw", ("double strike",)),), "also"))

    def test_drain_and_team(self):
        self.assertEqual(self.trig("poet"), ("instsorc_creature", (("drain", 1, 1),), (), ""))
        self.assertEqual(self.trig("hopesinger"), ("instsorc_creature", (("counter_all", 1),), (), ""))
        self.assertEqual(self.trig("rally"), ("noncreature", (("counter_others", 1),), (), ""))

    def test_token(self):
        kind, atoms, big, mode = self.trig("inkwright")
        self.assertEqual((kind, atoms[0][0], atoms[0][1], atoms[0][2].name, atoms[0][2].kw),
                         ("instsorc_creature", "token", 1, "Inkling", ("flying",)))

    def test_noncreature_two_effects(self):
        self.assertEqual(self.trig("gandalf"), ("noncreature", (("pump", 1, 1), ("face", 1)), (), ""))

    def test_own_creature_and_multicolor(self):
        self.assertEqual(self.trig("mockingbird"), ("own_creature", (("counter", 1),), (), ""))
        self.assertEqual(self.trig("referee"), ("multicolor", (("counter", 1),), (), ""))

    def test_unblockable_loot_target(self):
        self.assertEqual(self.trig("snooping"), ("instsorc_creature", (("unblockable",),), (), ""))
        self.assertEqual(self.trig("muse"), ("instsorc", (("draw", 1), ("discard", 1)), (("draw", 1),), "instead"))
        self.assertEqual(self.trig("graduation"), ("instsorc_creature", (("target_counter", 1),), (), ""))

    def test_any_target_and_x(self):
        self.assertEqual(self.trig("thor"), ("noncreature", (("bolt", "mv"),), (), ""))
        self.assertEqual(self.trig("pinger"), ("noncreature", (("bolt", 2),), (), ""))
        self.assertEqual(self.trig("manawurm"), ("instsorc", (("pump", "spent", 0),), (), ""))
        self.assertEqual(self.trig("dancing"), ("creature", (("target_counter", "mv"),), (), ""))

    def test_type_filter(self):
        kind, atoms, _big, _mode = self.trig("hydra")
        self.assertEqual((kind, atoms[0][2].name, atoms[0][2].power), ("type:villain", "Villain", 2))

    def test_keywords_and_surveil(self):
        self.assertEqual(self.trig("mascot"), ("instsorc_creature", (("kw", ("flying",)), ("surveil", 1)), (), ""))
        self.assertEqual(self.trig("debater"), ("instsorc_creature", (("pump", 1, 1),), (), ""))
        self.assertEqual(self.trig("demonstrator"),
                         ("instsorc_creature", (("pump", 1, 0), ("kw", ("lifelink",))), (), ""))


class RepartreeTests(unittest.TestCase):
    def test_removal_targets_a_creature(self):
        me, _opp = pair()
        sm = on_board(me, C["scornmage"])
        bt.on_cast(me, KILL, 5, entry())
        self.assertEqual(sm.bonus, 1)

    def test_pump_targets_a_creature(self):
        me, _opp = pair()
        sm = on_board(me, C["scornmage"])
        bt.on_cast(me, PUMP, 5, entry())
        self.assertEqual(sm.bonus, 1)

    def test_not_for_other_spells(self):
        me, _opp = pair()
        sm = on_board(me, C["scornmage"])
        for card in (FACE, DRAW, OGRE, RELIC):
            bt.on_cast(me, card, 5, entry())
        self.assertEqual(sm.bonus, 0)

    def test_drain(self):
        me, opp = pair()
        on_board(me, C["poet"])
        bt.on_cast(me, KILL, 5, entry())
        self.assertEqual((me.life, opp.life), (21, 19))

    def test_token(self):
        me, _opp = pair()
        on_board(me, C["inkwright"])
        bt.on_cast(me, KILL, 5, entry())
        token = next(c for c in me.creatures if c.card.is_token)
        self.assertEqual((token.card.name, token.power, token.has("flying")), ("Inkling", 1, True))

    def test_counter_on_each(self):
        me, _opp = pair()
        hs = on_board(me, C["hopesinger"])
        bear = on_board(me, BEAR)
        bt.on_cast(me, KILL, 5, entry())
        self.assertEqual((hs.bonus, bear.bonus), (1, 1))

    def test_unblockable(self):
        me, opp = pair()
        page = on_board(me, C["snooping"])
        bt.on_cast(me, KILL, 5, entry())
        self.assertFalse(bt.can_block(on_board(opp, OGRE), page))

    def test_keyword_and_pump(self):
        me, _opp = pair()
        mascot = on_board(me, C["mascot"])
        demo = on_board(me, C["demonstrator"])
        debater = on_board(me, C["debater"])
        bt.on_cast(me, KILL, 5, entry())
        self.assertTrue(mascot.has("flying"))
        self.assertEqual((demo.power, demo.has("lifelink")), (4, True))
        self.assertEqual((debater.power, debater.toughness), (4, 4))

    def test_target_counter_from_enchantment(self):
        me, _opp = pair()
        me.perms = [C["graduation"]]
        bear = on_board(me, BEAR)
        bt.on_cast(me, KILL, 5, entry())
        self.assertEqual(bear.bonus, 1)

    def test_dead_source_does_nothing(self):
        me, _opp = pair()
        sm = on_board(me, C["scornmage"])
        sm.dead = True
        bt.on_cast(me, KILL, 5, entry())
        self.assertEqual(sm.bonus, 0)


class OpusTests(unittest.TestCase):
    def test_small_and_big_damage(self):
        me, opp = pair()
        on_board(me, C["thunderdrum"])
        bt.on_cast(me, KILL, 5, entry())
        self.assertEqual(opp.life, 19)
        bt.on_cast(me, BIG_KILL, 5, entry())
        self.assertEqual(opp.life, 16)

    def test_counters_instead(self):
        me, _opp = pair()
        ta = on_board(me, C["tackle"])
        bt.on_cast(me, DRAW, 5, entry())
        bt.on_cast(me, BIG_DRAW, 5, entry())
        self.assertEqual(ta.bonus, 3)

    def test_also_double_strike(self):
        me, _opp = pair()
        fd = on_board(me, C["firedancer"])
        bt.on_cast(me, DRAW, 5, entry())
        self.assertFalse(fd.has("double strike"))
        bt.on_cast(me, BIG_DRAW, 5, entry())
        self.assertEqual((fd.power, fd.has("double strike")), (4, True))

    def test_pump_instead(self):
        me, _opp = pair()
        dv = on_board(me, C["deluge"])
        bt.on_cast(me, BIG_DRAW, 5, entry())
        self.assertEqual((dv.power, dv.toughness), (4, 4))

    def test_counters_instead_of_pump(self):
        me, _opp = pair()
        sw = on_board(me, C["skywhale"])
        bt.on_cast(me, BIG_DRAW, 5, entry())
        self.assertEqual((sw.power, sw.bonus), (4, 3))

    def test_loot_unless_big(self):
        me, _opp = pair()
        on_board(me, C["muse"])
        me.hand = [RELIC, OGRE]
        bt.on_cast(me, DRAW, 5, entry())
        self.assertEqual((len(me.hand), len(me.graveyard)), (2, 1))
        bt.on_cast(me, BIG_DRAW, 5, entry())
        self.assertEqual(len(me.hand), 3)


class OtherFilterTests(unittest.TestCase):
    def test_noncreature(self):
        me, opp = pair()
        g = on_board(me, C["gandalf"])
        bt.on_cast(me, RELIC, 5, entry())
        self.assertEqual((g.power, g.toughness, opp.life), (3, 4, 19))
        bt.on_cast(me, OGRE, 5, entry())
        self.assertEqual(opp.life, 19)

    def test_own_creature_target(self):
        me, _opp = pair()
        mb = on_board(me, C["mockingbird"])
        bt.on_cast(me, KILL, 5, entry())
        self.assertEqual(mb.bonus, 0)
        bt.on_cast(me, PUMP, 5, entry())
        self.assertEqual(mb.bonus, 1)

    def test_multicolor(self):
        me, _opp = pair()
        ref = on_board(me, C["referee"])
        bt.on_cast(me, FACE, 5, entry())
        self.assertEqual(ref.bonus, 0)
        bt.on_cast(me, GOLD, 5, entry())
        self.assertEqual(ref.bonus, 1)

    def test_counter_on_others_from_artifact(self):
        me, _opp = pair()
        me.perms = [C["rally"]]
        bear = on_board(me, BEAR)
        bt.on_cast(me, DRAW, 5, entry())
        self.assertEqual(bear.bonus, 1)


class VariableTests(unittest.TestCase):
    def test_bolt_goes_face_without_a_kill(self):
        me, opp = pair()
        on_board(me, C["pinger"])
        on_board(opp, OGRE)
        bt.on_cast(me, DRAW, 5, entry())
        self.assertEqual(opp.life, 18)

    def test_bolt_kills_a_creature(self):
        me, opp = pair()
        on_board(me, C["pinger"])
        bear = on_board(opp, BEAR)
        bt.on_cast(me, DRAW, 5, entry())
        self.assertNotIn(bear, opp.creatures)

    def test_bolt_by_mana_value(self):
        me, opp = pair()
        on_board(me, C["thor"])
        on_board(opp, make("Wall", f"Creature {DASH} Wall", "{3}", 3, "", "0", "9", colors=""))
        bt.on_cast(me, BIG_DRAW, 5, entry())
        self.assertEqual(opp.life, 15)

    def test_pump_by_mana_spent(self):
        me, _opp = pair()
        wurm = on_board(me, C["manawurm"])
        bt.on_cast(me, DRAW, 5, entry())
        self.assertEqual((wurm.power, wurm.toughness), (5, 5))

    def test_counters_by_mana_value(self):
        me, _opp = pair()
        me.perms = [C["dancing"]]
        bear = on_board(me, BEAR)
        bt.on_cast(me, OGRE, 5, entry())
        self.assertEqual(bear.bonus, 3)

    def test_type_spell(self):
        me, _opp = pair()
        on_board(me, C["hydra"])
        bt.on_cast(me, OGRE, 5, entry())
        self.assertEqual(len(me.creatures), 1)
        bt.on_cast(me, C["hydra"], 5, entry())
        self.assertEqual([c.card.name for c in me.creatures if c.card.is_token], ["Villain"])


class CoverageTests(unittest.TestCase):
    def test_lines_are_modelled(self):
        for key in RAW:
            self.assertEqual([line for _c, _m, line in analyze_card(RAW[key])], [], key)


if __name__ == "__main__":
    unittest.main()
