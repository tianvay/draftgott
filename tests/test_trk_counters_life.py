"""Star Trek (TRK), Pakete R1 und R2 (Nutzer 2026-11-02): Marken und Landfall (Xindi Surveyors, Syndicate
Liquidators, Captain Michael Burnham, Deanna Troi, Academy Instructor, Dominion Supervisor, Pure Energy, Culber and
Stamets, General Chang, Jadzia Dax, Sickbay, Picard, Leading by Example) sowie Schaden, Leben und Mana (Tea, Earl
Grey, Hot, Khan, Despot by Design, Crystalline Entity, Armus, A Good Day to Die, Savvy Profiteer, Quark, Rok-Tahk,
Gul Dukat). Nur Kampfmodell. Kartentexte aus TRK."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from components.mana import cost_alternatives
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]
FOREST = card_info(_card("Forest", f"Basic Land {DASH} Forest", text="({T}: Add {G}.)", produced=["G"]))[0]

RAW = {
    "xindi": _card("Xindi Surveyors", f"Creature {DASH} Xindi Scientist", "{2}{G}", 3, "G", f"Landfall {DASH} Whenever "
                   "a land you control enters, put a +1/+1 counter on this creature.", ["Landfall"], "3", "2"),
    "syndicate": _card("Syndicate Liquidators", f"Creature {DASH} Orion Pirate", "{4}{G}", 5, "G", f"Trample\nLandfall "
                       f"{DASH} Whenever a land you control enters, put two +1/+1 counters on target creature you "
                       "control.", ["Trample", "Landfall"], "4", "4"),
    "burnham": _card("Captain Michael Burnham", f"Legendary Creature {DASH} Human Officer", "{2}{R}", 3, "R",
                     f"Trample\nLandfall {DASH} Whenever a land you control enters, Captain Burnham deals 1 damage to "
                     "each opponent. If this is the second time this ability has resolved this turn, put a +1/+1 "
                     "counter on Captain Burnham.", ["Trample", "Landfall"], "3", "3"),
    "deanna": _card("Deanna Troi, Psychic Counsel", f"Legendary Creature {DASH} Betazoid Human Advisor", "{1}{W}", 2,
                    "W", "Other creatures you control enter with an additional +1/+1 counter on them.", [], "2", "2"),
    "instructor": _card("Academy Instructor", f"Creature {DASH} Bolian Officer", "{2}{R}", 3, "R", "This creature gets "
                        "+1/+0 for each Officer token you control.\nWhenever you cast a noncreature spell, create a 1/1 "
                        "red Officer creature token.", [], "0", "3"),
    "supervisor": _card("Dominion Supervisor", f"Creature {DASH} Vorta Doctor", "{2}{G}", 3, "G", "When this creature "
                        "enters, put a +1/+1 counter on target creature.\nCreatures you control with counters on them "
                        "have trample.", [], "3", "1"),
    "pure": _card("Pure Energy", "Sorcery", "{1}{W}", 2, "W", "Distribute two +1/+1 counters among one or two target "
                  "creatures.\nBeam me up {2}{W} (You may cast this card from your graveyard for {2}{W} if you also "
                  "return a creature you control to its owner's hand. Then exile this spell.)"),
    "culber": _card("Culber and Stamets, Star-Crossed", f"Legendary Creature {DASH} Human Doctor Artificer", "{3}{G}",
                    4, "G", f"When Culber and Stamets enter, choose one {DASH}\n• Put a +1/+1 counter on target "
                    "creature.\n• Add two mana of any one color.", [], "3", "4"),
    "chang": _card("General Chang, Cold Warrior", f"Legendary Creature {DASH} Klingon Warrior Officer", "{B}", 1, "B",
                   "{1}, Sacrifice a creature: Put a +1/+1 counter on each Klingon you control.", [], "1", "2"),
    "jadzia": _card("Jadzia Dax, Living Legacy", f"Legendary Creature {DASH} Trill Scientist", "{1}{G}", 2, "G",
                    "At the beginning of your first main phase, put a +1/+1 counter on Jadzia Dax, then add an amount "
                    f"of {{G}} equal to the number of counters on her.\nTransfer Symbiont {DASH} {{2}}{{G}}, Discard "
                    "this card: Put two +1/+1 counters on target creature.", ["Transfer Symbiont"], "0", "1"),
    "sickbay": _card("Sickbay", "Artifact", "{5}", 5, "", "Whenever a creature you control enters, you gain 1 life.\n"
                     "At the beginning of combat on your turn, put X +1/+1 counters on target creature you control, "
                     "where X is one plus the amount of life you gained this turn."),
    "lead": _card("Picard, Leading by Example", f"Legendary Creature {DASH} Human Officer", "{1}{W}", 2, "W", "{1}, {T}: "
                  "Another target creature gets +X/+X until end of turn, where X is Picard's power. Activate only as "
                  "a sorcery.", [], "2", "2"),
    "tea": _card("Tea, Earl Grey, Hot", f"Artifact {DASH} Food", "{2}", 2, "", "When this artifact enters, draw a card."
                 f"\n{{2}}, {{T}}, Sacrifice this artifact: Choose one {DASH}\n• This artifact deals 2 damage to target "
                 "opponent.\n• You gain 3 life."),
    "khan": _card("Khan, Despot by Design", f"Legendary Creature {DASH} Human Rogue", "{4}{R}", 5, "R", "Trample\nWhen "
                  "Khan enters, he deals 1 damage to each opponent and each creature your opponents control.",
                  ["Trample"], "5", "4"),
    "crystal": _card("Crystalline Entity", f"Artifact Creature {DASH} Elemental", "{8}", 8, "", "Flying\nWhen this "
                     "creature enters, if you cast it, destroy all nonartifact creatures.", ["Flying"], "7", "7"),
    "armus": _card("Armus, Skin of Evil", f"Legendary Creature {DASH} Ooze Horror", "{5}{B}{B}", 7, "B", "Menace\nAt "
                   "the beginning of your end step, target opponent discards two cards.\n{2}{B}, Discard this card: "
                   "Target creature gets -4/-4 until end of turn.", ["Menace"], "6", "6"),
    "gdtd": _card("A Good Day to Die", "Instant", "{B}", 1, "B", "Target creature gets +2/+0 until end of turn. When "
                  "that creature dies this turn, you draw a card."),
    "savvy": _card("Savvy Profiteer", f"Creature {DASH} Ferengi Rogue", "{1}{R}", 2, "R", "{T}: Add {R}.\n{3}, {T}: "
                   "Create a Treasure token. (It's an artifact with \"{T}, Sacrifice this token: Add one mana of any "
                   "color.\")", ["Treasure"], "2", "1"),
    "quark": _card("Quark, Humble Proprietor", f"Legendary Creature {DASH} Ferengi Rogue", "{2}{R}", 3, "R", "You can't "
                   "sacrifice Treasure tokens.\nAt the beginning of each upkeep, create a Treasure token. (It's an "
                   "artifact with \"{T}, Sacrifice this token: Add one mana of any color.\")", ["Treasure"], "1", "2"),
    "roktahk": _card("Rok-Tahk, Budding Scientist", f"Legendary Creature {DASH} Brikar Scientist", "{4}{G}{G}", 6, "G",
                     "Creatures you control have \"{T}: Add {G}{G}.\"\nWhen Rok-Tahk enters, create Murf, a legendary 0/1 "
                     "green Ooze Slug creature token with indestructible.", [], "5", "5"),
    "dukat": _card("Gul Dukat, Colonial Prefect", f"Legendary Creature {DASH} Cardassian Rogue", "{4}{B}{B}{B}", 7, "B",
                   "Menace\nAt the beginning of each end step, each opponent loses life equal to the life that player "
                   "lost this turn. You gain life equal to the life lost this way. (Damage causes loss of life.)",
                   ["Menace"], "6", "6"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}


def make(name, cost, cmc, text="", power=None, toughness=None, type_line=f"Creature {DASH} Test", colors="G"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, [], power, toughness))[0]


BEAR = make("Bear", "{1}{G}", 2, "", "2", "2")
OGRE = make("Ogre", "{2}{R}", 3, "", "3", "3", colors="R")
GIANT = make("Giant", "{4}{R}", 5, "", "4", "4", colors="R")
KLINGON = make("Klingon Brute", "{1}{B}", 2, "", "2", "2", f"Creature {DASH} Klingon Warrior", "B")
GOLEM = make("Golem", "{3}", 3, "", "3", "3", f"Artifact Creature {DASH} Golem", "")
OFFICER = make("Officer", "", 0, "", "1", "1", f"Creature {DASH} Officer", "R")._replace(is_token=True)


def player(name="Wir"):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], [PLAINS] * 20
    return p


def pair():
    me, opp = player(), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": [], "land": ""}


def put(p, card, entered=0):
    c = bt.Creature(card, entered)
    c.gy, c.ctl = p.graveyard, p
    p.creatures.append(c)
    return c


def open_lines(key):
    return [l for _c, _m, l in analyze_card(RAW[key])]


class ParseTests(unittest.TestCase):
    def test_r1_fields(self):
        self.assertEqual(C["xindi"].landfall, (("self_counter", 1),))
        self.assertEqual(C["syndicate"].landfall, (("target_counter", 2),))
        self.assertEqual(C["burnham"].landfall, (("face", 1), ("second_counter", 1)))
        self.assertEqual(C["deanna"].ally_enter_counter, 1)
        self.assertEqual(C["instructor"].officer_token_power, 1)
        self.assertEqual(C["supervisor"].counter_kw, ("trample",))
        self.assertEqual(C["pure"].modes, ((("counter", 2, 1),),))
        self.assertEqual(len(C["culber"].choices[1]), 2)
        self.assertEqual(C["culber"].choices[1][1].etb_mana, 2)
        self.assertEqual(C["chang"].sac_klingon, cost_alternatives("{1}"))
        self.assertTrue(C["jadzia"].main1_counter_mana)
        self.assertEqual(C["jadzia"].channel_counter, (cost_alternatives("{2}{G}"), 2))
        self.assertEqual(C["sickbay"].creature_enter_life, 1)
        self.assertEqual(C["sickbay"].combat_counter, (-1, ()))
        self.assertEqual(C["lead"].lead_pump, cost_alternatives("{1}"))

    def test_r2_fields(self):
        self.assertEqual(C["tea"].tea_ability, (cost_alternatives("{2}"), 2, 3))
        self.assertEqual(C["khan"].removal, ("sweep_damage", 1, (("opponents",),), False, "etb", False))
        self.assertEqual(C["khan"].modes, ((("face", 1),),))
        self.assertEqual(C["crystal"].removal, ("sweep", 0, (("nonartifact",),), False, "etb", False))
        self.assertEqual(C["armus"].end_discard, 2)
        self.assertTrue(C["gdtd"].pump_death_draw)
        self.assertEqual(C["savvy"].treasure_ability, cost_alternatives("{3}"))
        self.assertTrue(C["quark"].quark)
        self.assertEqual(C["roktahk"].team_mana, (("G",), ("G",)))
        self.assertTrue(C["dukat"].dukat)

    def test_coverage(self):
        for key in RAW:
            self.assertEqual(open_lines(key), [], key)


class LandfallTests(unittest.TestCase):
    def test_xindi_and_syndicate(self):
        me, opp = pair()
        x = put(me, C["xindi"])
        s = put(me, C["syndicate"])
        bt.on_land(me, opp, FOREST, 3, entry())
        self.assertEqual(x.bonus, 1)
        self.assertEqual(s.bonus, 2)  # die gefaehrlichste eigene Kreatur

    def test_burnham_second_time(self):
        me, opp = pair()
        b = put(me, C["burnham"])
        for _ in range(3):
            bt.on_land(me, opp, FOREST, 3, entry())
        self.assertEqual((opp.life, b.bonus), (17, 1))
        me.now = opp.now = 5  # naechster Zug: wieder ab eins
        bt.on_land(me, opp, FOREST, 5, entry())
        bt.on_land(me, opp, FOREST, 5, entry())
        self.assertEqual(b.bonus, 2)


class CounterTests(unittest.TestCase):
    def test_deanna(self):
        me, opp = pair()
        d = put(me, C["deanna"])
        bt.creature_enters(me, d, 3, entry(), opp, cast=False)
        bear = put(me, BEAR, 3)
        bt.creature_enters(me, bear, 3, entry(), opp, cast=False)
        self.assertEqual((d.bonus, bear.bonus), (0, 1))

    def test_instructor(self):
        me, _opp = pair()
        inst = put(me, C["instructor"])
        put(me, OFFICER)
        put(me, OFFICER)
        put(me, C["lead"])  # Officer, aber kein Token
        self.assertEqual(inst.power, 2)

    def test_supervisor_trample(self):
        me, _opp = pair()
        put(me, C["supervisor"])
        bear, ogre = put(me, BEAR), put(me, OGRE)
        bear.bonus = 1
        self.assertEqual((bear.has("trample"), ogre.has("trample")), (True, False))

    def test_pure_energy(self):
        me, opp = pair()
        bear = put(me, BEAR)
        bt.card_effects(me, opp, C["pure"], 3, entry())
        self.assertEqual(bear.bonus, 2)

    def test_culber_counter_mode(self):
        me, opp = pair()
        c = put(me, C["culber"], 3)
        bt.card_effects(me, opp, C["culber"], 3, entry())
        self.assertEqual(c.bonus, 1)

    def test_culber_mana_mode(self):
        me, opp = pair()
        bt.card_effects(me, opp, C["culber"].choices[1][1], 3, entry())
        self.assertEqual(len(me.open), 2)

    def test_chang(self):
        me, _opp = pair()
        chang = put(me, C["chang"])
        k = put(me, KLINGON)
        victim = put(me, BEAR)
        me.open = [("B",)]
        self.assertTrue(bt.sacrifice_for(me, victim, entry()))
        self.assertEqual((victim.dead, chang.bonus, k.bonus), (True, 1, 1))

    def test_jadzia_main1(self):
        me, _opp = pair()
        j = put(me, C["jadzia"])
        self.assertEqual(bt.jadzia_mana(me, entry()), [("G",)])
        self.assertEqual(bt.jadzia_mana(me, entry()), [("G",), ("G",)])
        self.assertEqual(j.bonus, 2)

    def test_transfer_symbiont_trick(self):
        me, opp = pair()
        att = put(me, BEAR)
        blk = put(opp, OGRE)
        me.hand, me.open = [C["jadzia"]], [("G",)] * 3
        bt.combat_tricks(me, [(att, [blk])], opp, entry(), 3, attacking=True)
        self.assertEqual((att.bonus, me.hand, me.graveyard, me.open), (2, [], [C["jadzia"]], []))

    def test_sickbay(self):
        me, opp = pair()
        me.perms.append(C["sickbay"])
        bear = put(me, BEAR, 3)
        bt.creature_enters(me, bear, 3, entry(), opp, cast=False)
        self.assertEqual((me.life, me.gained), (21, 1))
        bt.combat_counters(me, 3, entry())
        self.assertEqual(bear.bonus, 2)

    def test_picard_leading(self):
        me, opp = pair()
        me.turn_start = 3
        lead = put(me, C["lead"])
        ogre = put(me, OGRE)
        me.open = [("W",)]
        bt.lead_pump(me, opp, 3, entry())
        self.assertEqual((lead.tapped, ogre.power, ogre.toughness, me.open), (True, 5, 5, []))


class DamageLifeManaTests(unittest.TestCase):
    def test_tea(self):
        me, opp = pair()
        me.perms.append(C["tea"])
        me.open = [("W",)] * 2
        opp.life = 2
        bt.use_tea(me, entry())
        self.assertEqual((opp.life, me.perms), (0, []))
        me.perms.append(C["tea"])
        me.open, me.life, opp.life = [("W",)] * 2, 8, 20
        bt.use_tea(me, entry())
        self.assertEqual((me.life, opp.life), (11, 20))
        me.perms.append(C["tea"])
        me.open, me.life = [("W",)] * 2, 15
        bt.use_tea(me, entry())
        self.assertEqual((me.life, opp.life), (15, 18))

    def test_tea_lethal_before_life(self):
        me, opp = pair()
        me.perms.append(C["tea"])
        me.open, me.life, opp.life = [("W",)] * 2, 5, 2
        bt.use_tea(me, entry())
        self.assertEqual((me.life, opp.life), (5, 0))

    def test_khan(self):
        me, opp = pair()
        small, big = put(opp, OFFICER), put(opp, BEAR)
        mine = put(me, OFFICER)
        bt.card_effects(me, opp, C["khan"], 3, entry())
        self.assertEqual((opp.life, [c.card.name for c in opp.creatures], mine.dead), (19, ["Bear"], False))
        self.assertEqual(big.damage, 1)
        self.assertNotIn(small, opp.creatures)

    def test_crystalline_entity(self):
        me, opp = pair()
        golem, bear = put(me, GOLEM), put(me, BEAR)
        put(opp, OGRE)
        bt.cast_removal(C["crystal"], me, opp, entry(), 3)
        self.assertEqual(([c.card.name for c in me.creatures], opp.creatures), (["Golem"], []))
        self.assertFalse(bear in me.creatures)
        del golem

    def test_crystalline_only_if_worth_it(self):
        me, opp = pair()
        me.hand = [C["crystal"]]
        put(me, GIANT)
        put(opp, BEAR)
        self.assertEqual(bt.main_phase_spells(me, opp), [])
        put(opp, GIANT)
        self.assertEqual(bt.main_phase_spells(me, opp), [C["crystal"]])

    def test_armus_and_dukat_end_step(self):
        me, opp = pair()
        put(me, C["armus"])
        put(me, C["dukat"])
        opp.hand = [PLAINS] * 3
        opp.life_mark, opp.life = 20, 17
        e = entry()
        bt.end_step_triggers(me, opp, e)
        self.assertEqual((len(opp.hand), opp.life, me.life), (1, 14, 23))

    def test_dukat_in_opponents_end_step(self):
        me, opp = pair()
        put(me, C["dukat"])
        put(me, C["armus"])
        opp.hand = [PLAINS] * 3
        opp.life_mark, opp.life = 20, 18
        bt.end_step_triggers(opp, me, entry())  # Zug des Gegners: Armus nicht, Gul Dukat schon
        self.assertEqual((len(opp.hand), opp.life, me.life), (3, 16, 22))

    def test_good_day_to_die(self):
        me, opp = pair()
        att = put(me, BEAR)
        blk = put(opp, GIANT)
        me.hand, me.open = [C["gdtd"]], [("B",)]
        bt.combat_tricks(me, [(att, [blk])], opp, entry(), 3, attacking=True)
        self.assertEqual(att.power, 4)
        att.dead = True
        before = len(me.hand)
        bt.bury((me,), entry())
        self.assertEqual(len(me.hand), before + 1)

    def test_savvy(self):
        me, _opp = pair()
        me.turn_start = 3
        s = put(me, C["savvy"])
        me.open = [("R",)] * 3
        bt.savvy_treasures(me, entry())
        self.assertEqual((me.treasures, s.tapped, me.open), (1, True, []))

    def test_quark(self):
        me, opp = pair()
        put(me, C["quark"])
        bt.upkeep_triggers(me, opp, 3, entry())
        bt.upkeep_triggers(opp, me, 4, entry())
        self.assertEqual((me.treasures, bt.treasure_count(me)), (2, 0))

    def test_roktahk(self):
        me, _opp = pair()
        put(me, C["roktahk"])
        put(me, BEAR)
        put(me, BEAR, 5)  # gerade gekommen: kein {T}
        _pool, units = bt._mana(me, 5)
        self.assertEqual(len(units), 4)


if __name__ == "__main__":
    unittest.main()
