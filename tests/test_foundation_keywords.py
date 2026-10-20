"""Grundlagen fuer kommende Sets, Teil 1: Indestructible (702.12b), verliehene Schluesselwoerter mit Bedingung
("as long as you control another ...", Infusion, Kreaturenkarten im Friedhof), Schluesselwoerter fuer Kreaturen mit
+1/+1-Marke, Marken zu Beginn des Kampfs und Angriffs-Ausloeser mit Schluesselwoertern. Kartentexte aus SOS, HOB und
MSH."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS = W["Plains"]
BEAR = W["Test Bear"]


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="W"):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)


def make(*args, **kwargs):
    return card_info(raw(*args, **kwargs))[0]


RAW = {
    "god": raw("Test God", CRE, "{3}{W}", 4, "Indestructible", "4", "4", ["Indestructible"]),
    "bolg": raw("Bolg's Company", f"Creature {DASH} Goblin Soldier", "{B}{R}", 2,
                "This creature has haste as long as you control another Goblin.\n{T}, Sacrifice another Goblin: Add "
                "{B}{R}.", "2", "2", colors="BR"),
    "ulna": raw("Ulna Alley Shopkeep", f"Creature {DASH} Goblin Warlock", "{2}{B}", 3,
                "Menace (This creature can't be blocked except by two or more creatures.)\nInfusion — This creature "
                "gets +2/+0 as long as you gained life this turn.", "2", "3", ["Infusion", "Menace"], "B"),
    "thornfist": raw("Thornfist Striker", f"Creature {DASH} Elf Druid", "{2}{G}", 3,
                     "Ward {1} (Whenever this creature becomes the target of a spell or ability an opponent controls, "
                     "counter it unless that player pays {1}.)\nInfusion — Creatures you control get +1/+0 and have "
                     "trample as long as you gained life this turn.", "3", "3", ["Infusion", "Ward"], "G"),
    "killmonger": raw("Killmonger, Scourge of Wakanda", f"Legendary Creature {DASH} Human Mercenary Villain",
                      "{2}{B}{G}", 4, "As long as there are two or more creature cards in your graveyard, Killmonger "
                      "gets +2/+1.", "3", "3", colors="BG"),
    "regimen": raw("Training Regimen", "Enchantment", "{3}{G}", 4,
                   "Creatures you control with +1/+1 counters on them have trample.\nAt the beginning of combat on "
                   "your turn, put a +1/+1 counter on target creature you control.", colors="G"),
    "ugly": raw("Great Ugly-Looking Goblin", f"Creature {DASH} Goblin Soldier", "{5}{B}", 6,
                "Each creature you control with a +1/+1 counter on it has menace. (It can't be blocked except by two "
                "or more creatures.)", "4", "4", colors="B"),
    "additive": raw("Additive Evolution", "Enchantment", "{3}{G}{G}", 5,
                    "At the beginning of combat on your turn, put a +1/+1 counter on target creature you control. It "
                    "gains vigilance until end of turn.", colors="G"),
    "luke": raw("Luke Cage, Power Man", f"Legendary Creature {DASH} Human Hero", "{3}{W}", 4,
                "Unbreakable Skin — Whenever Luke Cage attacks alone, he gets +2/+0 and gains indestructible until "
                "end of turn. (Damage and effects that say \"destroy\" don't destroy him.)", "2", "5",
                ["Unbreakable Skin"]),
    "widow": raw("Black Widow, Double Agent", f"Legendary Creature {DASH} Human Hero Villain", "{1}{W}{B}", 3,
                 "Deathtouch\nWhenever a creature you control attacks alone, it gains first strike and menace until "
                 "end of turn. (It can't be blocked except by two or more creatures.)", "3", "2", ["Deathtouch"],
                 "WB"),
    "nori": raw("Nori, Teller of Tales", f"Legendary Creature {DASH} Dwarf Bard", "{1}{R/W}", 2,
                "Whenever Nori attacks, target attacking creature gains first strike until end of turn.", "2", "2",
                colors="RW"),
    "strength": raw("Super Strength", f"Enchantment {DASH} Aura", "{4}{G}", 5,
                    "Enchant creature\nEnchanted creature gets +4/+4 and has trample and ward {1}. (Whenever enchanted "
                    "creature becomes the target of a spell or ability an opponent controls, counter it unless that "
                    "player pays {1}.)", keywords=["Enchant"], colors="G"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}

TITAN = make("Titan", CRE, "{4}{G}", 5, "", "5", "5", colors="G")
VIPER = make("Viper", CRE, "{B}", 1, "Deathtouch", "1", "1", ["Deathtouch"], "B")
KILL = make("Murder", "Instant", "{1}{B}{B}", 3, "Destroy target creature.", colors="B")
WRATH = make("Wrath", "Sorcery", "{2}{W}{W}", 4, "Destroy all creatures.")
SHRINK = make("Shrink", "Instant", "{1}{B}", 2, "Target creature gets -5/-5 until end of turn.", colors="B")
BOLT = make("Big Bolt", "Instant", "{2}{R}", 3, "Big Bolt deals 5 damage to target creature.", colors="R")
GOBLIN = make("Goblin Pal", f"Creature {DASH} Goblin", "{R}", 1, "", "1", "1", colors="R")


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
    def test_indestructible_keyword(self):
        self.assertIn("indestructible", C["god"].kw)

    def test_another_type(self):
        self.assertEqual(C["bolg"].cond_static, ((("another", "goblin"), "self", 0, 0, ("haste",)),))

    def test_infusion_self(self):
        self.assertEqual(C["ulna"].cond_static, ((("gained",), "self", 2, 0, ()),))

    def test_infusion_team(self):
        self.assertEqual(C["thornfist"].cond_static, ((("gained",), "team", 1, 0, ("trample",)),))

    def test_graveyard_creatures(self):
        self.assertEqual(C["killmonger"].cond_static, ((("gy_creatures", 2), "self", 2, 1, ()),))

    def test_counter_keywords(self):
        self.assertEqual(C["regimen"].counter_kw, ("trample",))
        self.assertEqual(C["ugly"].counter_kw, ("menace",))

    def test_combat_counter(self):
        self.assertEqual(C["regimen"].combat_counter, (1, ()))
        self.assertEqual(C["additive"].combat_counter, (1, ("vigilance",)))

    def test_attack_alone_self(self):
        self.assertEqual(C["luke"].attack_self, (2, 0, ("indestructible",), True))

    def test_attack_target(self):
        self.assertEqual(C["nori"].attack_target, (0, 0, ("first strike",)))

    def test_attack_alone_any(self):
        self.assertEqual(C["widow"].alone_kw, ("first strike", "menace"))

    def test_aura_ward(self):
        self.assertEqual((C["strength"].aura_pump, C["strength"].aura_kw, C["strength"].grant_ward),
                         ((4, 4), ("trample",), 1))

    def test_grant_spell_with_indestructible(self):
        card = make("Shield Up", "Instant", "{W}", 1, "Target creature you control gains indestructible until end of "
                    "turn.")
        self.assertEqual(card.grant_kw, ("indestructible",))


class IndestructibleTests(unittest.TestCase):
    def test_survives_lethal_combat_damage(self):
        me, opp = pair()
        god = on_board(me, C["god"])
        titan = on_board(opp, TITAN)
        bt.resolve_combat([(titan, [god])])
        bt.bury((me, opp), entry())
        self.assertIn(god, me.creatures)
        self.assertFalse(god.dead)

    def test_survives_deathtouch(self):
        me, opp = pair()
        god = on_board(me, C["god"])
        viper = on_board(opp, VIPER)
        bt.resolve_combat([(viper, [god])])
        bt.bury((me, opp), entry())
        self.assertIn(god, me.creatures)

    def test_destroy_has_no_target(self):
        me, opp = pair()
        on_board(opp, C["god"])
        self.assertIsNone(bt.choose_target(KILL.removal, me, opp))

    def test_destroy_does_nothing(self):
        me, opp = pair()
        god = on_board(opp, C["god"])
        bt.cast_removal(KILL, me, opp, entry(), 3, target=god)
        self.assertIn(god, opp.creatures)

    def test_wrath_spares_it(self):
        me, opp = pair()
        god = on_board(opp, C["god"])
        bear = on_board(opp, BEAR)
        bt.cast_removal(WRATH, me, opp, entry(), 3)
        self.assertEqual(opp.creatures, [god])
        self.assertNotIn(bear, opp.creatures)

    def test_damage_removal_skips_it(self):
        me, opp = pair()
        on_board(opp, C["god"])
        self.assertIsNone(bt.choose_target(BOLT.removal, me, opp))

    def test_minus_toughness_kills(self):
        me, opp = pair()
        god = on_board(opp, C["god"])
        bt.cast_removal(SHRINK, me, opp, entry(), 3, target=god)
        self.assertNotIn(god, opp.creatures)

    def test_granted_until_end_of_turn(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        bear.extra.add("indestructible")
        titan = on_board(opp, TITAN)
        bt.resolve_combat([(titan, [bear])])
        bt.bury((me, opp), entry())
        self.assertIn(bear, me.creatures)


class ConditionalStaticTests(unittest.TestCase):
    def test_haste_only_with_another_goblin(self):
        me, _opp = pair()
        bolg = on_board(me, C["bolg"])
        self.assertFalse(bolg.has("haste"))
        on_board(me, GOBLIN)
        self.assertTrue(bolg.has("haste"))

    def test_infusion_self_pump(self):
        me, _opp = pair()
        ulna = on_board(me, C["ulna"])
        self.assertEqual(ulna.power, 2)
        bt.gain_life(me, 1)
        self.assertEqual((ulna.power, ulna.toughness), (4, 3))

    def test_infusion_team(self):
        me, _opp = pair()
        on_board(me, C["thornfist"])
        bear = on_board(me, BEAR)
        self.assertEqual((bear.power, bear.has("trample")), (2, False))
        bt.gain_life(me, 2)
        self.assertEqual((bear.power, bear.has("trample")), (3, True))

    def test_graveyard_creatures(self):
        me, _opp = pair()
        km = on_board(me, C["killmonger"])
        me.graveyard += [BEAR]
        self.assertEqual(km.power, 3)
        me.graveyard += [TITAN]
        self.assertEqual((km.power, km.toughness), (5, 4))

    def test_counter_keyword_from_enchantment(self):
        me, _opp = pair()
        me.perms = [C["regimen"]]
        bear = on_board(me, BEAR)
        self.assertFalse(bear.has("trample"))
        bear.bonus = 1
        self.assertTrue(bear.has("trample"))

    def test_counter_keyword_from_creature(self):
        me, _opp = pair()
        ugly = on_board(me, C["ugly"])
        bear = on_board(me, BEAR)
        bear.bonus = 1
        self.assertTrue(bear.has("menace"))
        self.assertFalse(ugly.has("menace"))

    def test_aura_ward_on_creature(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        bt.permanent_enters(me, opp, C["strength"], 3, entry())
        self.assertEqual(bt.ward_of(bear), ("mana", 1))
        self.assertEqual((bear.power, bear.has("trample")), (6, True))
        opp.open = []
        self.assertFalse(bt.ward_ok(opp, bear))


class CombatTriggerTests(unittest.TestCase):
    def test_counter_at_beginning_of_combat(self):
        me, opp = pair()
        me.perms = [C["regimen"]]
        bear = on_board(me, BEAR)
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(bear.bonus, 1)
        self.assertEqual(e["damage"], 3)  # 3/3 mit Trample

    def test_counter_and_vigilance(self):
        me, opp = pair()
        me.perms = [C["additive"]]
        bear = on_board(me, BEAR)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((bear.bonus, bear.tapped), (1, False))

    def test_attacks_alone_pump(self):
        me, opp = pair()
        on_board(me, C["luke"])
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 4)

    def test_attacks_alone_indestructible(self):
        me, _opp = pair()
        luke = on_board(me, C["luke"])
        bt.attack_keywords(me, [luke], luke, entry())
        self.assertEqual((luke.power, luke.has("indestructible")), (4, True))

    def test_no_pump_when_not_alone(self):
        me, opp = pair()
        on_board(me, C["luke"])
        on_board(me, BEAR)
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 4)

    def test_alone_attacker_gains_keywords(self):
        me, _opp = pair()
        on_board(me, C["widow"])
        bear = on_board(me, BEAR)
        bt.attack_keywords(me, [bear], bear, entry())
        self.assertTrue(bear.has("first strike") and bear.has("menace"))

    def test_target_attacker_is_the_strongest(self):
        me, _opp = pair()
        nori = on_board(me, C["nori"])
        titan = on_board(me, TITAN)
        bt.attack_keywords(me, [nori, titan], None, entry())
        self.assertEqual((titan.has("first strike"), nori.has("first strike")), (True, False))

    def test_no_keywords_when_not_alone(self):
        me, _opp = pair()
        widow = on_board(me, C["widow"])
        bear = on_board(me, BEAR)
        bt.attack_keywords(me, [bear, widow], None, entry())
        self.assertFalse(bear.has("menace"))


class CoverageTests(unittest.TestCase):
    def test_lines_are_modelled(self):
        for key in ("god", "bolg", "ulna", "thornfist", "killmonger", "regimen", "ugly", "additive", "luke", "widow",
                    "strength", "nori"):
            lines = [line for _c, _m, line in analyze_card(RAW[key])]
            if key == "bolg":  # Mana durch Opfern bleibt offen
                lines = [line for line in lines if "as long as" in line.lower()]
            self.assertEqual(lines, [], key)


if __name__ == "__main__":
    unittest.main()
