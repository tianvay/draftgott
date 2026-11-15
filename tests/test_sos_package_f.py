"""SOS Paket F (Prismari): Opus ab 5 Mana (Mill, Mana in Hoehe der Power, Impulse), Converge (Farben des ausgegebenen
Manas: Marken, Team-Pump, Marken fuer Kreaturzauber, Ziehen, Exil, Abwerfen), Mana nur fuer Instants und Sorceries
(als Kostensenkung), Topiary Lecturer, bedingte Kostensenkungen, Diary of Dreams, Potioner's Trove, Sanar und Rapturous
Moment. Kartentexte aus Secrets of Strixhaven (SOS)."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS, ISLAND = W["Plains"], W["Island"]
BEAR = W["Test Bear"]
OPUS = "Opus — Whenever you cast an instant or sorcery spell, "
CONV = "Converge — "


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="U"):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)", produced=[color]))[0]


SWAMP, MOUNTAIN, FOREST = land("Swamp", "B"), land("Mountain", "R"), land("Forest", "G")
RAW = {
    "tidecaller": raw("Exhibition Tidecaller", f"Creature {DASH} Djinn Wizard", "{U}", 1,
                      OPUS + "target player mills three cards. If five or more mana was spent to cast that spell, that "
                      "player mills ten cards instead.", "0", "2", ["Mill", "Opus"]),
    "maestro": raw("Molten-Core Maestro", f"Creature {DASH} Goblin Bard", "{1}{R}", 2,
                   "Menace\n" + OPUS + "put a +1/+1 counter on this creature. If five or more mana was spent to cast "
                   "that spell, add an amount of {R} equal to this creature's power.", "2", "2", ["Menace", "Opus"], "R"),
    "mascot": raw("Elemental Mascot", f"Creature {DASH} Elemental Bird", "{1}{U}{R}", 3,
                  "Flying, vigilance\n" + OPUS + "this creature gets +1/+0 until end of turn. If five or more mana was "
                  "spent to cast that spell, exile the top card of your library. You may play that card until the end "
                  "of your next turn.", "1", "4", ["Flying", "Vigilance", "Opus"], "UR"),
    "rancorous": raw("Rancorous Archaic", f"Creature {DASH} Avatar", "{5}", 5,
                     "Reach, trample\n" + CONV + "This creature enters with a +1/+1 counter on it for each color of "
                     "mana spent to cast it.", "2", "2", ["Reach", "Converge", "Trample"], ""),
    "magmablood": raw("Magmablood Archaic", f"Creature {DASH} Avatar", "{2/R}{2/R}{2/R}", 6,
                      "Reach, trample\n" + CONV + "This creature enters with a +1/+1 counter on it for each color of "
                      "mana spent to cast it.\nWhenever you cast an instant or sorcery spell, creatures you control get "
                      "+1/+0 until end of turn for each color of mana spent to cast that spell.", "2", "2",
                      ["Reach", "Converge", "Trample"], "R"),
    "wildgrowth": raw("Wildgrowth Archaic", f"Creature {DASH} Avatar", "{2/G}{2/G}", 4,
                      "Reach, trample\n" + CONV + "This creature enters with a +1/+1 counter on it for each color of "
                      "mana spent to cast it.\nWhenever you cast a creature spell, that creature enters with X "
                      "additional +1/+1 counters on it, where X is the number of colors of mana spent to cast it.",
                      "0", "0", ["Reach", "Converge", "Trample"], "G"),
    "transcendent": raw("Transcendent Archaic", f"Creature {DASH} Avatar", "{7}", 7,
                        "Vigilance\n" + CONV + "When this creature enters, you may draw X cards, where X is the number "
                        "of colors of mana spent to cast this spell. If you draw one or more cards this way, discard "
                        "two cards.", "6", "6", ["Vigilance", "Converge"], ""),
    "sundering": raw("Sundering Archaic", f"Creature {DASH} Avatar", "{6}", 6,
                     CONV + "When this creature enters, exile target nonland permanent an opponent controls with mana "
                     "value less than or equal to the number of colors of mana spent to cast this creature.\n{2}: Put "
                     "target card from a graveyard on the bottom of its owner's library.", "3", "3", ["Converge"], ""),
    "omens": raw("Arcane Omens", "Sorcery", "{4}{B}", 5,
                 CONV + "Target player discards X cards, where X is the number of colors of mana spent to cast this "
                 "spell.", keywords=["Converge"], colors="B"),
    "channeler": raw("Hydro-Channeler", f"Creature {DASH} Merfolk Wizard", "{1}{U}", 2,
                     "{T}: Add {U}. Spend this mana only to cast an instant or sorcery spell.\n{1}, {T}: Add one mana of "
                     "any color. Spend this mana only to cast an instant or sorcery spell.", "1", "3"),
    "tablet": raw("Tablet of Discovery", "Artifact", "{2}{R}", 3,
                  "When this artifact enters, mill a card. You may play that card this turn. (To mill a card, put the "
                  "top card of your library into your graveyard.)\n{T}: Add {R}.\n{T}: Add {R}{R}. Spend this mana "
                  "only to cast instant and sorcery spells.", keywords=["Mill"], colors="R"),
    "paintmage": raw("Abstract Paintmage", f"Creature {DASH} Djinn Sorcerer", "{U}{U/R}{R}", 3,
                     "At the beginning of your first main phase, add {U}{R}. Spend this mana only to cast instant and "
                     "sorcery spells.", "2", "2", colors="UR"),
    "lute": raw("Resonating Lute", "Artifact", "{2}{U}{R}", 4,
                "Lands you control have \"{T}: Add two mana of any one color. Spend this mana only to cast instant "
                "and sorcery spells.\"\n{T}: Draw a card. Activate only if you have seven or more cards in your hand.",
                colors="UR"),
    "topiary": raw("Topiary Lecturer", f"Creature {DASH} Elf Druid", "{2}{G}", 3,
                   "Increment (Whenever you cast a spell, if the amount of mana you spent is greater than this "
                   "creature's power or toughness, put a +1/+1 counter on this creature.)\n{T}: Add an amount of {G} "
                   "equal to this creature's power.", "1", "2", ["Increment"], "G"),
    "response": raw("Ajani's Response", "Instant", "{4}{W}", 5,
                    "This spell costs {3} less to cast if it targets a tapped creature.\nDestroy target creature.",
                    colors="W"),
    "brush": raw("Brush Off", "Instant", "{2}{U}{U}", 4,
                 "This spell costs {1}{U} less to cast if it targets an instant or sorcery spell.\nCounter target "
                 "spell."),
    "orysa": raw("Orysa, Tide Choreographer", f"Legendary Creature {DASH} Merfolk Bard", "{4}{U}", 5,
                 "This spell costs {3} less to cast if creatures you control have total toughness 10 or greater.\nWhen "
                 "Orysa enters, draw two cards.", "2", "2"),
    "dawning": raw("The Dawning Archaic", f"Legendary Creature {DASH} Avatar", "{10}", 10,
                   "This spell costs {1} less to cast for each instant and sorcery card in your graveyard.\nReach\n"
                   "Whenever The Dawning Archaic attacks, you may cast target instant or sorcery card from your "
                   "graveyard without paying its mana cost. If that spell would be put into your graveyard, exile it "
                   "instead.", "7", "7", ["Reach"], ""),
    "diary": raw("Diary of Dreams", f"Artifact {DASH} Book", "{2}", 2,
                 "Whenever you cast an instant or sorcery spell, put a page counter on this artifact.\n{5}, {T}: Draw a "
                 "card. This ability costs {1} less to activate for each page counter on this artifact.", colors=""),
    "trove": raw("Potioner's Trove", "Artifact", "{3}", 3,
                 "{T}: Add one mana of any color.\n{T}: You gain 2 life. Activate only if you've cast an instant or "
                 "sorcery spell this turn.", colors=""),
    "sanar": raw("Sanar, Unfinished Genius", f"Legendary Creature {DASH} Goblin Sorcerer", "{U}{R}", 2,
                 "{T}: Create a Treasure token. Activate only if you've cast an instant or sorcery spell this turn.",
                 "0", "4", colors="UR"),
    "rapturous": raw("Rapturous Moment", "Sorcery", "{4}{U}{R}", 6,
                     "Draw three cards, then discard two cards. Add {U}{U}{R}{R}{R}.", colors="UR"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}

TITAN = card_info(raw("Titan", "Creature — Giant", "{4}{G}", 5, "", "5", "5", colors="G"))[0]
WALL = card_info(raw("Wall", "Creature — Wall", "{1}{W}", 2, "", "0", "6", colors="W"))[0]
CHEAP = card_info(raw("Quick Thought", "Sorcery", "{U}", 1, "Draw a card."))[0]
BIG = card_info(raw("Big Thought", "Sorcery", "{3}{U}{R}", 5, "Draw two cards.", colors="UR"))[0]
STRIKE = card_info(raw("Strike", "Instant", "{1}{R}", 2, "Strike deals 2 damage to any target.", colors="R"))[0]


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
    def test_opus(self):
        self.assertEqual(C["tidecaller"].cast_trig, (("instsorc", (("mill_opp", 3),), (("mill_opp", 10),), "instead"),))
        self.assertEqual(C["maestro"].cast_trig, (("instsorc", (("counter", 1),), (("mana_power", "R"),), "also"),))
        self.assertEqual(C["mascot"].cast_trig, (("instsorc", (("pump", 1, 0),), (("impulse_next",),), "also"),))

    def test_converge(self):
        for key in ("rancorous", "magmablood", "wildgrowth"):
            self.assertTrue(C[key].converge_counters, key)
        self.assertEqual(C["magmablood"].cast_trig, (("instsorc", (("converge_team_pump",),), (), ""),))
        self.assertTrue(C["wildgrowth"].converge_creature_counters)
        self.assertEqual(C["transcendent"].converge_draw, 2)
        self.assertTrue(C["sundering"].converge_exile)
        self.assertTrue(C["omens"].converge_discard)

    def test_mana(self):
        self.assertEqual(C["channeler"].instsorc_mana, 1)
        self.assertEqual(C["tablet"].instsorc_mana, 1)  # {R}{R} statt {R}: eins mehr
        self.assertEqual(C["paintmage"].instsorc_mana, 2)
        self.assertEqual(C["lute"].instsorc_mana, "lands")
        self.assertEqual(C["lute"].hand7_draw, True)
        self.assertTrue(C["topiary"].power_mana)

    def test_discounts(self):
        self.assertEqual(C["response"].self_discount, ("tapped_target", 3))
        self.assertTrue(C["brush"].counter_alts_instsorc)
        self.assertEqual(C["orysa"].self_discount, ("toughness_total", 10, 3))
        self.assertEqual(C["dawning"].self_discount, ("gy_instsorc", 1))

    def test_others(self):
        self.assertTrue(C["diary"].diary)
        self.assertEqual(C["trove"].instsorc_life, 2)
        self.assertTrue(C["sanar"].instsorc_treasure)
        r = C["rapturous"]
        self.assertEqual((r.draws, r.discard_after, len(r.add_mana)), (3, 2, 5))


class CoverageTests(unittest.TestCase):
    PARTIAL = {"tablet": "When this artifact enters", "dawning": "Whenever The Dawning Archaic attacks",
               "sundering": "{2}"}

    def test_cards_fully_modelled(self):
        for key in RAW:
            lines = [line for _c, _m, line in analyze_card(RAW[key])]
            skip = self.PARTIAL.get(key)
            if skip:
                lines = [line for line in lines if not line.startswith(skip)]
            self.assertEqual(lines, [], key)


class OpusTests(unittest.TestCase):
    def test_tidecaller_mills_opponent(self):
        me, opp = pair()
        on_board(me, C["tidecaller"])
        bt.cast_triggers(me, CHEAP, 3, entry())
        self.assertEqual(len(opp.library), 17)
        bt.cast_triggers(me, BIG, 3, entry())
        self.assertEqual(len(opp.library), 7)

    def test_maestro_mana_with_big_spell(self):
        me, opp = pair()
        m = on_board(me, C["maestro"])
        bt.cast_triggers(me, BIG, 3, entry())
        self.assertEqual((m.bonus, len(me.open)), (1, 3))

    def test_mascot_impulse(self):
        me, opp = pair()
        on_board(me, C["mascot"])
        bt.cast_triggers(me, BIG, 3, entry())
        self.assertEqual(len(me.impulse), 1)


class ConvergeTests(unittest.TestCase):
    def test_colors_from_lands(self):
        me, opp = pair()
        me.lands = [PLAINS, ISLAND, SWAMP, SWAMP]
        self.assertEqual(bt.converge_colors(me, C["rancorous"]), 3)
        self.assertEqual(bt.converge_colors(me, CHEAP), 1)  # Manawert 1

    def test_rancorous_counters(self):
        me, opp = pair()
        me.lands = [PLAINS, ISLAND, SWAMP, MOUNTAIN, FOREST]
        bt._resolve(me, opp, C["rancorous"], 3, entry())
        self.assertEqual(me.creatures[0].bonus, 5)

    def test_magmablood_team_pump(self):
        me, opp = pair()
        me.lands = [ISLAND, MOUNTAIN, SWAMP]
        on_board(me, C["magmablood"])
        bear = on_board(me, BEAR)
        bt.cast_triggers(me, BIG, 3, entry())
        self.assertEqual(bear.pump, 3)

    def test_wildgrowth_counters_on_creature_spell(self):
        me, opp = pair()
        me.lands = [PLAINS, FOREST]
        on_board(me, C["wildgrowth"])
        bt._resolve(me, opp, TITAN, 3, entry())
        titan = next(c for c in me.creatures if c.card is TITAN)
        self.assertEqual(titan.bonus, 2)

    def test_transcendent_draws_then_discards(self):
        me, opp = pair()
        me.lands = [PLAINS, ISLAND, SWAMP]
        bt._resolve(me, opp, C["transcendent"], 3, entry())
        self.assertEqual((len(me.hand), len(me.graveyard)), (1, 2))

    def test_sundering_exiles_up_to_colors(self):
        me, opp = pair()
        me.lands = [PLAINS, ISLAND]
        bear, titan = on_board(opp, BEAR), on_board(opp, TITAN)
        bt._resolve(me, opp, C["sundering"], 3, entry())
        self.assertNotIn(bear, opp.creatures)
        self.assertIn(titan, opp.creatures)

    def test_omens_discard(self):
        me, opp = pair()
        me.lands = [SWAMP, ISLAND, MOUNTAIN]
        opp.hand = [CHEAP] * 5
        bt._resolve(me, opp, C["omens"], 3, entry())
        self.assertEqual(len(opp.hand), 2)


class ManaTests(unittest.TestCase):
    def test_instsorc_discount(self):
        me, opp = pair()
        on_board(me, C["channeler"])
        me.perms.append(C["tablet"])
        self.assertEqual(bt._alts(me, BIG), ((1, (("R", 1), ("U", 1))),))
        self.assertEqual(bt._alts(me, TITAN), TITAN.alts)

    def test_lute_counts_lands(self):
        me, opp = pair()
        me.perms.append(C["lute"])
        me.lands = [ISLAND, MOUNTAIN]
        self.assertEqual(bt._alts(me, BIG), ((1, (("R", 1), ("U", 1))),))

    def test_opus_counts_restricted_mana(self):
        me, opp = pair()
        me.perms.append(C["lute"])
        me.lands = [ISLAND, MOUNTAIN, ISLAND]
        self.assertEqual(bt.mana_spent(me, BIG), 5)

    def test_topiary_mana_units(self):
        me, opp = pair()
        t = on_board(me, C["topiary"])
        t.bonus = 2
        _pool, units = bt._mana(me, 3)
        self.assertEqual(sum(1 for u, i in units if u == ("G",)), 3)

    def test_lute_draw_with_full_hand(self):
        dfn, act = pair()
        dfn.perms.append(C["lute"])
        dfn.hand = [CHEAP] * 7
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual(len(dfn.hand), 8)


class DiscountTests(unittest.TestCase):
    def test_response_cheaper_against_tapped(self):
        me, opp = pair()
        self.assertEqual(bt.own_reduction(me, C["response"]), 0)
        on_board(opp, TITAN).tapped = True
        self.assertEqual(bt.own_reduction(me, C["response"]), 3)

    def test_orysa_with_total_toughness(self):
        me, opp = pair()
        on_board(me, WALL)
        self.assertEqual(bt.own_reduction(me, C["orysa"]), 0)
        on_board(me, TITAN)
        self.assertEqual(bt.own_reduction(me, C["orysa"]), 3)

    def test_dawning_per_instant_or_sorcery(self):
        me, opp = pair()
        me.graveyard.extend([CHEAP, STRIKE, BEAR])
        self.assertEqual(bt.own_reduction(me, C["dawning"]), 2)

    def test_brush_off_cheap_against_instant(self):
        dfn, act = pair()
        dfn.hand, dfn.open = [C["brush"]], [("U",), ("U",)]
        act.creatures = []
        self.assertTrue(bt.try_counter(act, BIG, 3, entry(), threat="lethal"))


class OtherTests(unittest.TestCase):
    def test_diary_pages_and_draw(self):
        dfn, act = pair()
        dfn.perms.append(C["diary"])
        for _ in range(3):
            bt.on_cast(dfn, CHEAP, 3, entry())
        dfn.open = [("U",), ("U",)]
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual(len(dfn.hand), 1)

    def test_trove_and_sanar_after_instant_or_sorcery(self):
        me, opp = pair()
        me.turn_start = 1
        me.perms.append(C["trove"])
        on_board(me, C["sanar"])
        bt.sos_end_own(me, opp, 3, entry())
        self.assertEqual((me.life, me.treasures), (20, 0))
        bt.on_cast(me, CHEAP, 3, entry())
        bt.sos_end_own(me, opp, 3, entry())
        self.assertEqual((me.life, me.treasures), (22, 1))

    def test_rapturous_moment(self):
        me, opp = pair()
        me.hand = [CHEAP]
        bt._resolve(me, opp, C["rapturous"], 3, entry())
        self.assertEqual((len(me.hand), len(me.open)), (2, 5))


if __name__ == "__main__":
    unittest.main()
