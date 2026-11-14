"""SOS Paket B: Prepared erweitern - neue Ausloeser fuer "becomes prepared" (Angriff, Landfall, Kreaturzauber, Token,
erstes Leben im Zug, erste/zweite Main Phase, dritter Zauber, Friedhof verlassen, Endsegment, Upkeep, Tap-Faehigkeit,
Betreten), Instant-Haelften als Kopie (Removal, Ende des gegnerischen Zugs, Jump vor dem Angriff), offene
Zauberhaelften und Biblioplex Tomekeeper. Kartentexte aus Secrets of Strixhaven (SOS)."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]
BEAR = W["Test Bear"]
NOTE = " (While it's prepared, you may cast a copy of its spell. Doing so unprepares it.)"


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="W"):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)


def prepare(front, spell, keywords=("Prepared",)):
    return {"name": front["name"] + " // " + spell["name"], "layout": "prepare", "type_line": front["type_line"],
            "mana_cost": front["mana_cost"], "cmc": front["cmc"], "colors": front["colors"],
            "keywords": list(keywords), "card_faces": [front, spell]}


def cre(name, sub, cost, cmc, text, pt, colors, keywords=()):
    p, t = pt.split("/")
    return raw(name, f"Creature {DASH} {sub}", cost, cmc, text, p, t, keywords, colors)


SPELLS = {
    "swords": raw("Swords to Plowshares", "Instant", "{W}", 1,
                  "Exile target creature. Its controller gains life equal to its power."),
    "rendezvous": raw("Secret Rendezvous", "Sorcery", "{1}{W}{W}", 3, "You and target opponent each draw three cards."),
    "scrollboost": raw("Scrollboost", "Sorcery", "{1}{W}", 2,
                       "One or two target creatures each get +2/+2 until end of turn."),
    "jump": raw("Jump", "Instant", "{U}", 1, "Target creature gains flying until end of turn.", colors="U"),
    "brainstorm": raw("Brainstorm", "Instant", "{U}", 1,
                      "Draw three cards, then put two cards from your hand on top of your library in any order.",
                      colors="U"),
    "tutor": raw("Demonic Tutor", "Sorcery", "{1}{B}", 2,
                 "Search your library for a card, put that card into your hand, then shuffle.", colors="B"),
    "reanimate": raw("Reanimate", "Sorcery", "{B}", 1,
                     "Put target creature card from a graveyard onto the battlefield under your control. You lose "
                     "life equal to that card's mana value.", colors="B"),
    "bloodletting": raw("Bloodletting", "Sorcery", "{B}", 1, "Each opponent loses 2 life.", colors="B"),
    "venomous": raw("Venomous Words", "Sorcery", "{B}", 1,
                    "Target creature you control gets +2/+0 and gains deathtouch until end of turn.", colors="B"),
    "sign": raw("Sign in Blood", "Sorcery", "{B}{B}", 2, "Target player draws two cards and loses 2 life.",
                colors="B"),
    "bolt": raw("Lightning Bolt", "Instant", "{R}", 1, "Lightning Bolt deals 3 damage to any target.", colors="R"),
    "stanza": raw("Heroic Stanza", "Sorcery", "{1}{W/B}", 2, "Put a +1/+1 counter on target creature.", colors="WB"),
    "punch": raw("Pack a Punch", "Sorcery", "{1}{R}{W}", 3,
                 "Mill a card. Put two +1/+1 counters on target creature. It gains trample until end of turn.",
                 keywords=["Mill"], colors="RW"),
    "deep_sight": raw("Deep Sight", "Sorcery", "{G}{U}", 2, "You draw a card and gain 1 life.", colors="GU"),
    "recall": raw("Ancestral Recall", "Instant", "{U}", 1, "Target player draws three cards.", colors="U"),
    "regrowth": raw("Regrowth", "Sorcery", "{1}{G}", 2, "Return target card from your graveyard to your hand.",
                    colors="G"),
    "pest_friend": raw("Pest Friend", "Sorcery", "{B/G}", 1,
                       "Create a 1/1 black and green Pest creature token with \"Whenever this token attacks, you gain "
                       "1 life.\"", colors="BG"),
    "wild_idea": raw("Wild Idea", "Sorcery", "{3}{U}{R}", 5,
                     "Search your library for an instant or sorcery card, reveal it, put it into your hand, then "
                     "shuffle.", colors="UR"),
}
RAW = {
    "truce": prepare(cre("Emeritus of Truce", "Cat Cleric", "{1}{W}{W}", 3,
                         "When this creature enters, target player creates a 1/1 white and black Inkling creature "
                         "token with flying. Then if an opponent controls more creatures than you, this creature "
                         "becomes prepared." + NOTE, "3/3", "W"), SPELLS["swords"]),
    "joined": prepare(cre("Joined Researchers", "Human Cleric Wizard", "{1}{W}", 2,
                          "First strike\nAt the beginning of each end step, if an opponent has more cards in hand "
                          "than you, this creature becomes prepared." + NOTE, "2/2", "W", ["First strike"]),
                      SPELLS["rendezvous"], ["First strike", "Prepared"]),
    "spiritcall": prepare(cre("Spiritcall Enthusiast", "Cat Cleric", "{2}{W}", 3,
                              "Whenever one or more tokens you control enter, this creature becomes prepared." + NOTE,
                              "3/3", "W"), SPELLS["scrollboost"]),
    "aviator": prepare(cre("Encouraging Aviator", "Bird Wizard", "{2}{U}", 3,
                           "Flying\nWhenever this creature attacks, it becomes prepared." + NOTE, "2/3", "U",
                           ["Flying"]), SPELLS["jump"], ["Flying", "Prepared"]),
    "trio": prepare(cre("Harmonized Trio", "Merfolk Bard Wizard", "{U}", 1,
                        "{T}, Tap two untapped creatures you control: This creature becomes prepared." + NOTE, "1/1",
                        "U"), SPELLS["brainstorm"]),
    "woe": prepare(cre("Emeritus of Woe", "Vampire Warlock", "{3}{B}", 4,
                       "This creature enters prepared." + NOTE + "\nAt the beginning of your end step, if two or more "
                       "creatures died this turn, this creature becomes prepared.", "5/4", "B"), SPELLS["tutor"]),
    "grave": prepare(cre("Grave Researcher", "Troll Warlock", "{2}{B}", 3,
                         "At the beginning of your upkeep, surveil 1. Then if there are three or more creature cards "
                         "in your graveyard, this creature becomes prepared." + NOTE, "3/3", "B"),
                     SPELLS["reanimate"], ["Surveil", "Prepared"]),
    "leech": prepare(cre("Leech Collector", "Human Warlock", "{1}{B}", 2,
                         "Whenever you gain life for the first time each turn, this creature becomes prepared." + NOTE,
                         "2/2", "B"), SPELLS["bloodletting"]),
    "shadelock": prepare(cre("Scathing Shadelock", "Snake Warlock", "{4}{B}", 5,
                             "At the beginning of your first main phase, this creature becomes prepared." + NOTE,
                             "4/6", "B"), SPELLS["venomous"]),
    "silvertongue": prepare(cre("Scheming Silvertongue", "Vampire Warlock", "{1}{B}", 2,
                                "Flying, lifelink\nAt the beginning of your second main phase, if you gained 2 or "
                                "more life this turn, this creature becomes prepared." + NOTE, "1/3", "B",
                                ["Flying", "Lifelink"]), SPELLS["sign"], ["Flying", "Lifelink", "Prepared"]),
    "conflict": prepare(cre("Emeritus of Conflict", "Human Wizard", "{1}{R}", 2,
                            "First strike\nWhenever you cast your third spell each turn, this creature becomes "
                            "prepared." + NOTE, "2/2", "R", ["First strike"]), SPELLS["bolt"],
                        ["First strike", "Prepared"]),
    "abigale": prepare(raw("Abigale, Poet Laureate", f"Legendary Creature {DASH} Bird Bard", "{1}{W}{B}", 3,
                           "Flying\nWhenever you cast a creature spell, Abigale becomes prepared." + NOTE, "2", "3",
                           ["Flying"], "WB"), SPELLS["stanza"], ["Flying", "Prepared"]),
    "kirol": prepare(raw("Kirol, History Buff", f"Legendary Creature {DASH} Vampire Cleric", "{R}{W}", 2,
                         "Whenever one or more cards leave your graveyard, Kirol becomes prepared." + NOTE, "2", "3",
                         colors="RW"), SPELLS["punch"], ["Prepared", "Mill"]),
    "tam": prepare(raw("Tam, Observant Sequencer", f"Legendary Creature {DASH} Gorgon Wizard", "{2}{G}{U}", 4,
                       "Landfall — Whenever a land you control enters, Tam becomes prepared." + NOTE, "4", "3",
                       colors="GU"), SPELLS["deep_sight"], ["Prepared", "Landfall"]),
    "ideation": prepare(cre("Emeritus of Ideation", "Human Wizard", "{3}{U}{U}", 5,
                            "Flying, ward {2}\nThis creature enters prepared.\nWhenever this creature attacks, you may "
                            "exile eight cards from your graveyard. If you do, this creature becomes prepared.", "5/5",
                            "U", ["Flying", "Ward"]), SPELLS["recall"], ["Flying", "Prepared", "Ward"]),
    "abundance": prepare(cre("Emeritus of Abundance", "Elf Druid", "{2}{G}", 3,
                             "Vigilance\nThis creature enters prepared.\nWhenever this creature attacks, if you "
                             "control eight or more lands, this creature becomes prepared.", "3/4", "G",
                             ["Vigilance"]), SPELLS["regrowth"], ["Vigilance", "Prepared"]),
    "lluwen": prepare(raw("Lluwen, Exchange Student", f"Legendary Creature {DASH} Elf Druid", "{2}{B}{G}", 4,
                          "Lluwen enters prepared." + NOTE + "\nExile a creature card from your graveyard: Lluwen "
                          "becomes prepared. Activate only as a sorcery.", "3", "4", colors="BG"),
                      SPELLS["pest_friend"]),
    "sanar": prepare(raw("Sanar, Unfinished Genius", f"Legendary Creature {DASH} Goblin Sorcerer", "{U}{R}", 2,
                         "Sanar enters prepared." + NOTE + "\n{T}: Create a Treasure token. Activate only if you've "
                         "cast an instant or sorcery spell this turn.", "0", "3", colors="UR"), SPELLS["wild_idea"]),
    "tomekeeper": raw("Biblioplex Tomekeeper", f"Artifact Creature {DASH} Construct", "{4}", 4,
                      "When this creature enters, choose up to one —\n• Target creature becomes prepared. (Only "
                      "creatures with prepare spells can become prepared.)\n• Target creature becomes unprepared.",
                      "3", "4", ["Prepared"], ""),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}
S = {k: card_info(v)[0] for k, v in SPELLS.items()}

TITAN = card_info(raw("Titan", "Creature — Giant", "{4}{G}", 5, "", "5", "5", colors="G"))[0]
WALL = card_info(raw("Wall", "Creature — Wall", "{1}{W}", 2, "", "0", "6"))[0]
RANGER = card_info(raw("Ranger", "Creature — Elf", "{1}{G}", 2, "", "3", "3", colors="G"))[0]
THOUGHT = card_info(raw("Quick Thought", "Sorcery", "{U}", 1, "Draw a card.", colors="U"))[0]
U, R = ("U",), ("R",)


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


def on_board(p, card, entered=0, prepared=None):
    c = bt.Creature(card, entered)
    c.gy, c.ctl = p.graveyard, p
    if prepared is not None:
        c.prepared = prepared
    p.creatures.append(c)
    return c


class ParseTests(unittest.TestCase):
    TRIGGERS = {"truce": "etb_inkling", "joined": "end_opp_hand", "spiritcall": "tokens", "aviator": "attack",
                "trio": "tap3", "grave": "upkeep_gy3", "leech": "first_life", "shadelock": "main1",
                "silvertongue": "main2_life2", "conflict": "third_spell", "abigale": "creature_cast",
                "kirol": "gy_leave", "tam": "landfall"}
    EXTRA = {"woe": "end_deaths2", "ideation": "attack_exile8", "abundance": "attack_lands8", "lluwen": "gy_creature"}

    def test_trigger_cards_have_spell_and_trigger(self):
        for key, kind in self.TRIGGERS.items():
            self.assertEqual(C[key].prepared[0], "trigger", key)
            self.assertEqual(C[key].prepare_on, (kind,), key)
            self.assertTrue(C[key].prepared[1].is_copy, key)

    def test_enters_prepared_with_extra_trigger(self):
        for key, kind in self.EXTRA.items():
            self.assertEqual(C[key].prepared[0], "enters", key)
            self.assertEqual(C[key].prepare_on, (kind,), key)

    def test_grave_researcher_surveils_in_upkeep(self):
        self.assertEqual(C["grave"].upkeep_surveil, 1)

    def test_spell_halves(self):
        self.assertEqual(S["scrollboost"].modes, ((("pump_each", 2, 2),),))
        self.assertEqual((S["brainstorm"].draws, S["brainstorm"].brainstorm), (3, 2))
        self.assertEqual(S["tutor"].tutor, ("any",))
        self.assertEqual(S["wild_idea"].tutor, ("instant_sorcery",))
        self.assertEqual(S["regrowth"].reanimate, ("target", "card", 99, "hand", 0))
        self.assertTrue(S["reanimate"].reanimate_any)
        self.assertEqual((S["punch"].mill_self, S["punch"].grant_kw), (1, ("trample",)))
        self.assertTrue(C["tomekeeper"].tomekeeper)

    def test_target_player_draws(self):
        self.assertEqual(S["recall"].draws, 3)
        self.assertEqual((S["sign"].draws, S["sign"].life_loss), (2, 2))
        self.assertEqual((S["rendezvous"].draws, S["rendezvous"].opp_draws), (3, 3))


class CoverageTests(unittest.TestCase):
    def test_cards_fully_modelled(self):
        for key in RAW:
            if key == "sanar":  # Treasure-Faehigkeit: Paket F
                continue
            self.assertEqual(analyze_card(RAW[key]), [], key)

    def test_spell_halves_modelled(self):
        for key in ("scrollboost", "brainstorm", "tutor", "reanimate", "regrowth", "punch", "wild_idea"):
            self.assertEqual(analyze_card(SPELLS[key]), [], key)


class TriggerTests(unittest.TestCase):
    def test_truce_gives_token_to_opponent_for_swords(self):
        me, opp = pair()
        on_board(opp, TITAN)
        bt._resolve(me, opp, C["truce"], 3, entry())
        truce = next(c for c in me.creatures if c.card is C["truce"])
        self.assertEqual((len(opp.creatures), len(me.creatures), truce.prepared), (2, 1, True))

    def test_truce_keeps_token_without_target_for_swords(self):
        me, opp = pair()
        bt._resolve(me, opp, C["truce"], 3, entry())
        truce = next(c for c in me.creatures if c.card is C["truce"])
        self.assertEqual((len(opp.creatures), len(me.creatures), truce.prepared), (0, 2, False))

    def test_joined_researchers_at_each_end_step(self):
        me, opp = pair()
        joined = on_board(me, C["joined"])
        opp.hand = [THOUGHT, THOUGHT]
        bt.end_step_prepare((opp, me), entry())
        self.assertTrue(joined.prepared)

    def test_spiritcall_tokens(self):
        me, opp = pair()
        spirit = on_board(me, C["spiritcall"])
        bt.make_tokens(me, [(1, BEAR)], 3, entry(), opp)
        self.assertTrue(spirit.prepared)

    def test_aviator_attack(self):
        me, opp = pair()
        aviator = on_board(me, C["aviator"])
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertTrue(aviator.prepared)

    def test_trio_taps_three_and_casts_brainstorm(self):
        dfn, act = pair()
        dfn.turn_start = 1
        trio = on_board(dfn, C["trio"])
        others = [on_board(dfn, BEAR), on_board(dfn, BEAR)]
        dfn.open = [U]
        dfn.hand = [PLAINS]
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertTrue(trio.tapped and all(c.tapped for c in others))
        self.assertFalse(trio.prepared)  # Brainstorm gleich gewirkt
        self.assertEqual(len(dfn.hand), 2)
        self.assertEqual(len(dfn.library), 19)

    def test_trio_needs_two_other_untapped(self):
        dfn, act = pair()
        dfn.turn_start = 1
        trio = on_board(dfn, C["trio"])
        on_board(dfn, BEAR)
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertFalse(trio.tapped or trio.prepared)

    def test_woe_two_deaths_in_own_end_step(self):
        me, opp = pair()
        woe = on_board(me, C["woe"], prepared=False)
        me.deaths, me.deaths_mark = 2, 0
        bt.end_step_prepare((me, opp), entry())
        self.assertTrue(woe.prepared)

    def test_woe_not_in_opponents_end_step(self):
        me, opp = pair()
        woe = on_board(me, C["woe"], prepared=False)
        me.deaths, me.deaths_mark = 2, 0
        bt.end_step_prepare((opp, me), entry())
        self.assertFalse(woe.prepared)

    def test_grave_researcher_upkeep(self):
        me, opp = pair()
        grave = on_board(me, C["grave"])
        me.graveyard.extend([BEAR, BEAR, BEAR])
        bt.sos_upkeep(me, entry())
        self.assertTrue(grave.prepared)

    def test_grave_researcher_needs_three_creatures(self):
        me, opp = pair()
        grave = on_board(me, C["grave"])
        me.graveyard.extend([BEAR, BEAR])
        me.library = [PLAINS] * 5  # Surveil legt ein Land nicht in den Friedhof als Kreatur
        bt.sos_upkeep(me, entry())
        self.assertFalse(grave.prepared)

    def test_leech_first_life(self):
        me, opp = pair()
        leech = on_board(me, C["leech"])
        bt.gain_life(me, 1)
        self.assertTrue(leech.prepared)

    def test_shadelock_and_lluwen_in_main1(self):
        me, opp = pair()
        shade = on_board(me, C["shadelock"])
        lluwen = on_board(me, C["lluwen"], prepared=False)
        me.graveyard.append(BEAR)
        bt.sos_main1(me, opp, 3, entry())
        self.assertTrue(shade.prepared and lluwen.prepared)
        self.assertNotIn(BEAR, me.graveyard)

    def test_silvertongue_main2(self):
        me, opp = pair()
        silver = on_board(me, C["silvertongue"])
        me.gained = 1
        bt.sos_main2(me, entry())
        self.assertFalse(silver.prepared)
        me.gained = 2
        bt.sos_main2(me, entry())
        self.assertTrue(silver.prepared)

    def test_conflict_third_spell(self):
        me, opp = pair()
        conflict = on_board(me, C["conflict"])
        for k in range(3):
            self.assertFalse(conflict.prepared, k)
            bt.on_cast(me, THOUGHT, 4, entry())
        self.assertTrue(conflict.prepared)

    def test_conflict_counts_per_turn(self):
        me, opp = pair()
        conflict = on_board(me, C["conflict"])
        bt.on_cast(me, THOUGHT, 4, entry())
        bt.on_cast(me, THOUGHT, 4, entry())
        bt.on_cast(me, THOUGHT, 5, entry())
        self.assertFalse(conflict.prepared)

    def test_abigale_creature_spell_not_itself(self):
        me, opp = pair()
        bt._resolve(me, opp, C["abigale"], 3, entry())
        abigale = next(c for c in me.creatures if c.card is C["abigale"])
        self.assertFalse(abigale.prepared)
        bt._resolve(me, opp, BEAR, 3, entry())
        self.assertTrue(abigale.prepared)

    def test_kirol_cards_leave_graveyard(self):
        me, opp = pair()
        kirol = on_board(me, C["kirol"])
        me.graveyard.append(BEAR)
        me.graveyard.remove(BEAR)
        bt.gy_leave_check((me, opp), entry())
        self.assertTrue(kirol.prepared)

    def test_tam_landfall(self):
        me, opp = pair()
        tam = on_board(me, C["tam"])
        bt.on_land(me, opp, PLAINS, 3, entry())
        self.assertTrue(tam.prepared)

    def test_abundance_attack_with_eight_lands(self):
        me, opp = pair()
        me.lands = [PLAINS] * 8
        abundance = on_board(me, C["abundance"], prepared=False)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertTrue(abundance.prepared or any(c.name == "Regrowth" for c in me.graveyard))

    def test_tomekeeper_prepares_own_creature(self):
        me, opp = pair()
        aviator = on_board(me, C["aviator"])
        bt._resolve(me, opp, C["tomekeeper"], 3, entry())
        self.assertTrue(aviator.prepared)

    def test_tomekeeper_unprepares_opponent(self):
        me, opp = pair()
        woe = on_board(opp, C["woe"])
        bt._resolve(me, opp, C["tomekeeper"], 3, entry())
        self.assertFalse(woe.prepared)


class InstantCopyTests(unittest.TestCase):
    def test_bolt_copy_as_removal_at_end_step(self):
        dfn, act = pair()
        conflict = on_board(dfn, C["conflict"], prepared=True)
        bear = on_board(act, BEAR)
        dfn.open = [R]
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertNotIn(bear, act.creatures)
        self.assertFalse(conflict.prepared)
        self.assertFalse(any(c.name == "Lightning Bolt" for c in dfn.graveyard))

    def test_swords_copy_before_attack(self):
        me, opp = pair()
        truce = on_board(me, C["truce"], prepared=True)
        on_board(me, RANGER)
        titan = on_board(opp, TITAN)  # wuerde unseren Angreifer fressen
        me.lands = [PLAINS]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertNotIn(titan, opp.creatures)
        self.assertFalse(truce.prepared)

    def test_draw_copy_at_end_step(self):
        dfn, act = pair()
        ideation = on_board(dfn, C["ideation"], prepared=True)
        dfn.open = [U]
        bt.end_step_instants(dfn, act, entry(), 6)
        self.assertEqual((len(dfn.hand), ideation.prepared), (3, False))

    def test_jump_before_attack(self):
        me, opp = pair()
        on_board(me, C["aviator"], prepared=True)
        ranger = on_board(me, RANGER)
        on_board(opp, WALL)
        me.open = [U]
        bt.sos_pre_attack_grants(me, opp, 3, entry())
        self.assertIn("flying", ranger.extra)


class SpellTests(unittest.TestCase):
    def test_scrollboost_two_creatures(self):
        me, opp = pair()
        a, b = on_board(me, BEAR), on_board(me, RANGER)
        bt._resolve(me, opp, S["scrollboost"], 3, entry())
        self.assertEqual((a.pump, b.pump), (2, 2))
        self.assertEqual((a.tpump, b.tpump), (2, 2))

    def test_brainstorm(self):
        me, opp = pair()
        me.library = [THOUGHT, THOUGHT, BEAR] + [PLAINS] * 5
        me.hand = [PLAINS, PLAINS]
        bt._resolve(me, opp, S["brainstorm"], 3, entry())
        self.assertEqual(len(me.hand), 3)
        self.assertEqual(len(me.library), 7)
        self.assertEqual(me.library[:2], [PLAINS, PLAINS])

    def test_demonic_tutor(self):
        me, opp = pair()
        me.library = [PLAINS] * 5 + [TITAN]
        me.lands = [PLAINS] * 4
        bt._resolve(me, opp, S["tutor"], 3, entry())
        self.assertIn(TITAN, me.hand)

    def test_wild_idea_finds_instant_or_sorcery(self):
        me, opp = pair()
        me.library = [TITAN] * 3 + [THOUGHT]
        bt._resolve(me, opp, S["wild_idea"], 3, entry())
        self.assertEqual(me.hand, [THOUGHT])

    def test_regrowth_any_card(self):
        me, opp = pair()
        me.graveyard.append(THOUGHT)
        bt._resolve(me, opp, S["regrowth"], 3, entry())
        self.assertIn(THOUGHT, me.hand)

    def test_reanimate_from_opponents_graveyard(self):
        me, opp = pair()
        opp.graveyard.append(TITAN)
        me.graveyard.append(BEAR)
        bt._resolve(me, opp, S["reanimate"], 3, entry())
        self.assertTrue(any(c.card is TITAN for c in me.creatures))
        self.assertEqual(me.life, 15)

    def test_reanimate_needs_target(self):
        me, opp = pair()
        me.hand = [S["reanimate"]]
        self.assertNotIn(S["reanimate"], bt.main_phase_spells(me, opp))
        opp.graveyard.append(TITAN)
        self.assertIn(S["reanimate"], bt.main_phase_spells(me, opp))

    def test_sign_in_blood(self):
        me, opp = pair()
        bt._resolve(me, opp, S["sign"], 3, entry())
        self.assertEqual((len(me.hand), me.life), (2, 18))

    def test_secret_rendezvous_both_draw(self):
        me, opp = pair()
        bt._resolve(me, opp, S["rendezvous"], 3, entry())
        self.assertEqual((len(me.hand), len(opp.hand)), (3, 3))

    def test_secret_rendezvous_only_with_small_hand(self):
        me, opp = pair()
        me.hand = [S["rendezvous"], THOUGHT, THOUGHT]
        self.assertIn(S["rendezvous"], bt.main_phase_spells(me, opp))
        me.hand.append(THOUGHT)  # drei andere Handkarten
        self.assertNotIn(S["rendezvous"], bt.main_phase_spells(me, opp))

    def test_pack_a_punch(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        bt._resolve(me, opp, S["punch"], 3, entry())
        self.assertEqual(bear.bonus, 2)
        self.assertIn("trample", bear.extra)
        self.assertEqual(len([c for c in me.graveyard if c is PLAINS]), 1)


if __name__ == "__main__":
    unittest.main()
