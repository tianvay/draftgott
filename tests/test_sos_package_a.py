"""SOS Paket A: Set anbinden (Archetypen der fuenf Colleges) und bekannte Effekte in neuem Wortlaut - Lebensentzug
beim Betreten und Angriff, Loot/Rummage, Tappen mit Stun, Kontern von Kreaturzaubern, Schluesselwort nach Wahl,
Abwerfen als Zusatzkosten, Landsuche. Kartentexte aus Secrets of Strixhaven (SOS)."""
import unittest

from components import archetypes as arch
from components import battle as bt
from components import setrating
from components.cards import card_info
from components.coverage import analyze_card
from components.report_cards import render_archetype_panel
from tests.fixtures_walkers import CARDS as W, _card
from tests.test_archetypes import _deck

DASH = "—"
PLAINS = W["Plains"]
BEAR = W["Test Bear"]
STUN_NOTE = " (If a permanent with a stun counter would become untapped, remove one from it instead.)"
PREP_NOTE = " (While it's prepared, you may cast a copy of its spell. Doing so unprepares it.)"


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="W"):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)


def prepare(front, spell, keywords=()):
    """Karte im Layout "prepare" (Vorderseite Kreatur, Rueckseite Zauber) wie bei Scryfall."""
    return {"name": front["name"] + " // " + spell["name"], "layout": "prepare", "type_line": front["type_line"],
            "mana_cost": front["mana_cost"], "cmc": front["cmc"], "colors": front["colors"],
            "keywords": list(keywords), "card_faces": [front, spell]}


RAW = {
    "shadewriter": raw("Sneering Shadewriter", f"Creature {DASH} Vampire Warlock", "{4}{B}", 5,
                       "Flying\nWhen this creature enters, each opponent loses 2 life and you gain 2 life.", "3", "3",
                       ["Flying"], "B"),
    "bane": raw("Shopkeeper's Bane", f"Creature {DASH} Badger Pest", "{2}{G}", 3,
                "Trample\nWhenever this creature attacks, you gain 2 life.", "4", "2", ["Trample"], "G"),
    "pest": raw("Teacher's Pest", f"Creature {DASH} Skeleton Pest", "{B}{G}", 2,
                "Menace (This creature can't be blocked except by two or more creatures.)\nWhenever this creature "
                "attacks, you gain 1 life.\n{B}{G}: Return this card from your graveyard to the battlefield tapped.",
                "1", "1", ["Menace"], "BG"),
    "professor": raw("Postmortem Professor", f"Creature {DASH} Zombie Warlock", "{1}{B}", 2,
                     "This creature can't block.\nWhenever this creature attacks, each opponent loses 1 life and you "
                     "gain 1 life.\n{1}{B}, Exile an instant or sorcery card from your graveyard: Return this card "
                     "from your graveyard to the battlefield.", "2", "2", colors="B"),
    "duelist": raw("Conciliator's Duelist", f"Creature {DASH} Kor Warlock", "{W}{W}{B}{B}", 4,
                   "When this creature enters, draw a card. Each player loses 1 life.\nRepartee — Whenever you cast an "
                   "instant or sorcery spell that targets a creature, exile up to one target creature. Return that "
                   "card to the battlefield under its owner's control at the beginning of the next end step.", "4", "3",
                   ["Repartee"], "WB"),
    "restoration": raw("Oracle's Restoration", "Sorcery", "{G}", 1,
                       "Target creature you control gets +1/+1 until end of turn. You draw a card and gain 1 life.",
                       colors="G"),
    "study": raw("Careful Study", "Sorcery", "{U}", 1, "Draw two cards, then discard two cards.", colors="U"),
    "jadzi": raw("Jadzi, Steward of Fate", f"Legendary Creature {DASH} Human Wizard", "{2}{U}", 3,
                 "When Jadzi enters, draw two cards, then discard two cards.", "2", "4", colors="U"),
    "rouser": raw("Rubble Rouser", f"Creature {DASH} Dwarf Sorcerer", "{2}{R}", 3,
                  "When this creature enters, you may discard a card. If you do, draw a card.", "1", "4", colors="R"),
    "tidalmage": raw("Stadium Tidalmage", f"Creature {DASH} Djinn Sorcerer", "{2}{U}{R}", 4,
                     "Whenever this creature enters or attacks, you may draw a card. If you do, discard a card.", "4",
                     "4", colors="UR"),
    "page": raw("Snooping Page", f"Creature {DASH} Human Cleric", "{1}{W}{B}", 3,
                "Repartee — Whenever you cast an instant or sorcery spell that targets a creature, this creature can't "
                "be blocked this turn.\nWhenever this creature deals combat damage to a player, you draw a card and "
                "lose 1 life.", "2", "3", ["Repartee"], "WB"),
    "rapier": raw("Rapier Wit", "Instant", "{1}{W}", 2,
                  "Tap target creature. If it's your turn, put a stun counter on it." + STUN_NOTE + "\nDraw a card."),
    "procrastinate": raw("Procrastinate", "Sorcery", "{X}{U}", 1,
                         "Tap target creature. Put twice X stun counters on it." + STUN_NOTE, colors="U"),
    "rejoinder": raw("Rejoinder", "Sorcery", "{1}{W}", 2, "You may tap or untap target creature.\nDraw a card."),
    "outburst": raw("Vibrant Outburst", "Instant", "{U}{R}", 2,
                    "Vibrant Outburst deals 3 damage to any target. Tap up to one target creature.", colors="UR"),
    "mascot": raw("Fractal Mascot", f"Creature {DASH} Fractal Elk", "{4}{G}{U}", 6,
                  "Trample\nWhen this creature enters, tap target creature an opponent controls. Put a stun counter on "
                  "it." + STUN_NOTE, "6", "6", ["Trample"], "GU"),
    "scatter": raw("Essence Scatter", "Instant", "{1}{U}", 2, "Counter target creature spell.", colors="U"),
    "offense": raw("Practiced Offense", "Sorcery", "{2}{W}", 3,
                   "Put a +1/+1 counter on each creature target player controls. Target creature gains your choice of "
                   "double strike or lifelink until end of turn.\nFlashback {1}{W} (You may cast this card from your "
                   "graveyard for its flashback cost. Then exile it.)", keywords=["Flashback"]),
    "spoils": raw("Seize the Spoils", "Sorcery", "{2}{R}", 3,
                  "As an additional cost to cast this spell, discard a card.\nDraw two cards and create a Treasure "
                  "token. (It's an artifact with \"{T}, Sacrifice this token: Add one mana of any color.\")",
                  keywords=["Treasure"], colors="R"),
    "growth": raw("Rampant Growth", "Sorcery", "{1}{G}", 2,
                  "Search your library for a basic land card, put that card onto the battlefield tapped, then "
                  "shuffle.", colors="G"),
}
RAW["seeker"] = prepare(raw("Spellbook Seeker", f"Creature {DASH} Bird Wizard", "{3}{U}", 4,
                            "Flying\nThis creature enters prepared." + PREP_NOTE, "3", "3", ["Flying"], "U"),
                        RAW["study"], ["Flying", "Prepared"])
RAW["first_year"] = prepare(raw("Studious First-Year", f"Creature {DASH} Bear Wizard", "{G}", 1,
                                "This creature enters prepared." + PREP_NOTE, "1", "1", colors="G"),
                            RAW["growth"], ["Prepared"])
RAW["interceptor"] = prepare(raw("Elite Interceptor", f"Creature {DASH} Human Wizard", "{W}", 1,
                                 "This creature enters prepared." + PREP_NOTE, "1", "2"), RAW["rejoinder"],
                             ["Prepared"])
C = {k: card_info(v)[0] for k, v in RAW.items()}

TITAN = card_info(raw("Titan", "Creature — Giant", "{4}{G}", 5, "", "5", "5", colors="G"))[0]
WALL = card_info(raw("Wall", "Creature — Wall", "{1}{W}", 2, "", "0", "6"))[0]
RANGER = card_info(raw("Ranger", "Creature — Elf", "{1}{G}", 2, "", "3", "3", colors="G"))[0]
SPELL = card_info(raw("Quick Thought", "Sorcery", "{U}", 1, "Draw a card.", colors="U"))[0]


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


class ArchetypeTests(unittest.TestCase):
    def test_five_colleges(self):
        sos = arch.for_set("SOS")
        self.assertEqual({a["colors"] for a in sos}, {"WB", "UR", "BG", "RW", "UG"})
        by = {a["colors"]: a["name"] for a in sos}
        self.assertEqual(by["WB"], "Silverquill Repartee")
        self.assertEqual(by["UR"], "Prismari Opus")
        self.assertEqual(by["BG"], "Witherbloom Infusion")
        self.assertEqual(by["RW"], "Lorehold Graveyard")
        self.assertEqual(by["UG"], "Quandrix Increment")
        self.assertTrue(all(a["tips"] for a in sos))

    def test_set_rating_offers_sos(self):
        self.assertIn("SOS", [s["code"] for s in setrating.implemented_sets()])
        self.assertEqual(setrating.start_set("sos"), "SOS")

    def test_report_names_pair_without_archetype(self):
        html = render_archetype_panel(_deck({"White Bear": 6, "Jace Spell": 4, "Plains": 9}, "sos"))
        self.assertIn("keinen eigenen Archetyp", html)
        self.assertIn("Weiß/Blau", html)
        self.assertNotIn("kein Farbpaar", html)


class ParseTests(unittest.TestCase):
    def test_etb_drain(self):
        self.assertEqual((C["shadewriter"].opp_loss, C["shadewriter"].etb_life), (2, 2))

    def test_attack_life(self):
        self.assertEqual(C["bane"].attack_life, (0, 2))
        self.assertEqual(C["pest"].attack_life, (0, 1))
        self.assertEqual(C["professor"].attack_life, (1, 1))

    def test_etb_draw_each_player_loses(self):
        d = C["duelist"]
        self.assertEqual((d.draws, d.opp_loss, d.life_loss), (1, 1, 1))

    def test_you_draw_and_gain_after_pump(self):
        r = C["restoration"]
        self.assertEqual((r.draws, r.spell_life), (1, 1))
        self.assertTrue(any(a[0] == "pump" for m in r.modes for a in m))

    def test_loot_two(self):
        self.assertEqual(C["study"].loot, 2)
        self.assertEqual(C["jadzi"].loot, 2)
        self.assertEqual(C["study"].draws, 0)

    def test_etb_rummage(self):
        self.assertTrue(C["rouser"].etb_rummage)
        self.assertFalse(C["rouser"].rummage_spell)

    def test_enter_or_attack_loot(self):
        self.assertEqual((C["tidalmage"].loot, C["tidalmage"].attack_loot), (1, True))

    def test_combat_draw_with_life_loss(self):
        self.assertEqual((C["page"].combat_draw, C["page"].combat_draw_loss), (1, 1))

    def test_tap_spells(self):
        self.assertEqual(C["rapier"].tap_spell, (1, 0, 0))
        self.assertEqual(C["rapier"].draws, 1)
        self.assertEqual(C["procrastinate"].tap_spell, (0, 0, 2))
        self.assertEqual(C["rejoinder"].tap_spell, (0, 0, 0))
        self.assertEqual(C["outburst"].tap_spell, (0, 0, 0))
        self.assertTrue(C["outburst"].removal)

    def test_etb_tap_and_stun_in_two_sentences(self):
        self.assertEqual(C["mascot"].etb_tap_opp, 2)

    def test_counter_creature_spell(self):
        self.assertEqual(C["scatter"].counter, ("creature", (), 0))

    def test_keyword_choice(self):
        self.assertEqual(C["offense"].kw_choice, ("double strike", "lifelink"))

    def test_discard_cost_draw_and_treasure(self):
        s = C["spoils"]
        self.assertEqual((s.discard_cost, s.draws, s.treasure), (1, 2, 1))

    def test_basic_search_that_card(self):
        self.assertTrue(C["growth"].etb_basic_tapped)


class CoverageTests(unittest.TestCase):
    FULL = ("shadewriter", "bane", "pest", "restoration", "tidalmage", "page", "rapier", "procrastinate", "outburst",
            "mascot", "scatter", "offense", "spoils", "seeker", "first_year", "interceptor")

    def test_cards_fully_modelled(self):
        for key in self.FULL:
            self.assertEqual(analyze_card(RAW[key]), [], key)

    def test_package_a_lines_modelled(self):
        for key, start in (("professor", "Whenever this creature attacks"), ("duelist", "When this creature enters"),
                           ("jadzi", "When Jadzi enters"), ("rouser", "When this creature enters")):
            lines = [line for _c, _m, line in analyze_card(RAW[key])]
            self.assertFalse([line for line in lines if line.startswith(start)], key)


class EnterTests(unittest.TestCase):
    def test_drain_on_enter(self):
        me, opp = pair()
        bt._resolve(me, opp, C["shadewriter"], 3, entry())
        self.assertEqual((me.life, opp.life), (22, 18))

    def test_draw_and_each_player_loses(self):
        me, opp = pair()
        bt._resolve(me, opp, C["duelist"], 3, entry())
        self.assertEqual((me.life, opp.life, len(me.hand)), (19, 19, 1))

    def test_loot_two_on_enter(self):
        me, opp = pair()
        me.hand = [SPELL, SPELL]
        bt._resolve(me, opp, C["jadzi"], 3, entry())
        self.assertEqual((len(me.hand), len(me.graveyard)), (2, 2))

    def test_rummage_on_enter(self):
        me, opp = pair()
        me.lands = [PLAINS] * 5
        me.hand = [PLAINS]
        bt._resolve(me, opp, C["rouser"], 3, entry())
        self.assertEqual((me.graveyard, len(me.hand)), ([PLAINS], 1))

    def test_tap_and_stun_on_enter(self):
        me, opp = pair()
        wall = on_board(opp, WALL)
        bt._resolve(me, opp, C["mascot"], 3, entry())
        self.assertEqual((wall.tapped, wall.stun), (True, 1))

    def test_rampant_growth(self):
        me, opp = pair()
        bt._resolve(me, opp, C["growth"], 3, entry())
        self.assertEqual(len(me.lands), 1)


class SpellTests(unittest.TestCase):
    def test_draw_and_gain_life(self):
        me, opp = pair()
        on_board(me, BEAR)
        bt._resolve(me, opp, C["restoration"], 3, entry())
        self.assertEqual((me.life, len(me.hand)), (21, 1))

    def test_careful_study(self):
        me, opp = pair()
        me.hand = [SPELL]
        bt._resolve(me, opp, C["study"], 3, entry())
        self.assertEqual(len(me.hand), 1)
        self.assertEqual(len([c for c in me.graveyard if c is not C["study"]]), 2)

    def test_rapier_wit_in_own_turn_taps_blocker_with_stun(self):
        me, opp = pair()
        me.turn_start = me.now
        on_board(me, RANGER)
        wall = on_board(opp, WALL)
        bt._resolve(me, opp, C["rapier"], 3, entry())
        self.assertEqual((wall.tapped, wall.stun, len(me.hand)), (True, 1, 1))

    def test_rapier_wit_in_opponents_turn_no_stun(self):
        me, opp = pair()
        me.turn_start, me.now = 1, 4  # nicht unser Zug
        titan = on_board(opp, TITAN)
        bt._resolve(me, opp, C["rapier"], 3, entry())
        self.assertEqual((titan.tapped, titan.stun), (True, 0))

    def test_rapier_wit_before_attack(self):
        me, opp = pair()
        me.turn_start = me.now
        me.open, me.hand = [("W",)] * 2, [C["rapier"]]
        on_board(me, RANGER)
        wall = on_board(opp, WALL)
        bt.sos_tap_instants(me, opp, 3, entry())
        self.assertEqual((wall.tapped, wall.stun), (True, 1))
        self.assertNotIn(C["rapier"], me.hand)

    def test_rapier_wit_held_without_blocker_to_tap(self):
        me, opp = pair()
        me.turn_start = me.now
        me.open, me.hand = [("W",)] * 2, [C["rapier"]]
        bt.sos_tap_instants(me, opp, 3, entry())
        self.assertIn(C["rapier"], me.hand)

    def test_procrastinate_twice_x(self):
        me, opp = pair()
        titan = on_board(opp, TITAN)
        me.next_x = 2
        bt._resolve(me, opp, C["procrastinate"], 3, entry())
        self.assertEqual((titan.tapped, titan.stun, me.next_x), (True, 4, 0))

    def test_rejoinder_taps_without_stun(self):
        me, opp = pair()
        me.turn_start = me.now
        on_board(me, RANGER)
        wall = on_board(opp, WALL)
        bt._resolve(me, opp, C["rejoinder"], 3, entry())
        self.assertEqual((wall.tapped, wall.stun, len(me.hand)), (True, 0, 1))

    def test_outburst_kills_and_taps(self):
        me, opp = pair()
        me.open = [("U",), ("R",)]
        me.hand = [C["outburst"]]
        bear = on_board(opp, BEAR)
        titan = on_board(opp, TITAN)
        self.assertTrue(bt._use_removal(me, C["outburst"], C["outburst"].alts, True, 3, entry(), other=opp))
        bt.cast_removal(C["outburst"], me, opp, entry(), 3, target=bear)
        self.assertTrue(titan.tapped)

    def test_counter_creature_spell_only(self):
        self.assertTrue(bt.counter_fits(C["scatter"], TITAN))
        self.assertFalse(bt.counter_fits(C["scatter"], SPELL))

    def test_keyword_choice_double_strike_on_best_attacker(self):
        me, opp = pair()
        me.turn_start = me.now
        bear = on_board(me, BEAR)
        titan = on_board(me, TITAN)
        bt._resolve(me, opp, C["offense"], 3, entry())
        self.assertIn("double strike", titan.extra)
        self.assertNotIn("double strike", bear.extra)
        self.assertEqual((bear.bonus, titan.bonus), (1, 1))

    def test_seize_the_spoils_discards_then_draws(self):
        me, opp = pair()
        me.hand = [PLAINS]
        bt._resolve(me, opp, C["spoils"], 3, entry())
        self.assertIn(PLAINS, me.graveyard)
        self.assertEqual(len(me.hand), 2)

    def test_seize_the_spoils_needs_another_card(self):
        me, opp = pair()
        me.hand = [C["spoils"]]
        self.assertNotIn(C["spoils"], bt.main_phase_spells(me, opp))
        me.hand = [C["spoils"], SPELL]
        self.assertIn(C["spoils"], bt.main_phase_spells(me, opp))


class TurnTests(unittest.TestCase):
    def test_attack_gains_life(self):
        me, opp = pair()
        on_board(me, C["bane"])
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((me.life, e["damage"]), (22, 4))

    def test_attack_drains(self):
        me, opp = pair()
        on_board(me, C["professor"])
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((me.life, opp.life), (21, 17))

    def test_attack_loot(self):
        me, opp = pair()
        on_board(me, C["tidalmage"])
        me.hand = [SPELL]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(len(me.graveyard), 1)

    def test_combat_damage_draw_and_lose_life(self):
        me, opp = pair()
        on_board(me, C["page"])
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((me.life, opp.life), (19, 18))
        self.assertEqual(len(me.hand), 1)


if __name__ == "__main__":
    unittest.main()
