"""Star Trek (TRK), Paket R5 (Nutzer 2026-11-05): Gegnerhand und Interaktion - V'Ger, Salt Vampire, Zero, Kai Winn und
Nyota Uhura (Wahl nur nach Gesehenem: Feld und Friedhof des Gegners), Brazen Bluff (wie ein Counterspell), The
Caretaker, Worf, Intelligence Contractor, Engineered Explosives, Peace in Our Time (ziehen nur, wenn ohnehin kein
Angriff), Dominion Infiltration. Nur Kampfmodell. Kartentexte aus TRK."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]

RAW = {
    "vger": _card("V'Ger, the Intruder", f"Legendary Artifact Creature {DASH} Construct", "{6}{U}", 7, "U", "Flying\n"
                  f"Whenever V'Ger enters or attacks, choose one {DASH}\n• Look at target opponent's hand, then draw a "
                  "card.\n• Creatures your opponents control get -1/-0 until your next turn.", ["Flying"], "5", "7"),
    "salt": _card("Salt Vampire", f"Creature {DASH} Vampire Shapeshifter", "{1}{B}", 2, "B", "Lifelink\nWhen this "
                  "creature enters, look at target opponent's hand. You may choose a nonland card from it. If you do, "
                  "that player exiles that card, then draws a card.", ["Lifelink"], "2", "2"),
    "zero": _card("Zero, Incorporeal Sensate", f"Legendary Artifact Creature {DASH} Medusan Scientist", "{1}{W/B}{W/B}",
                  3, "WB", "Lifelink\nWhen Zero enters, look at target opponent's hand. You may exile a nonland card "
                  "from it. For as long as that card remains exiled, its owner may play it. A spell cast this way costs "
                  "{2} more to cast.", ["Lifelink"], "2", "2"),
    "kai": _card("Kai Winn, Faithless Leader", f"Legendary Creature {DASH} Bajoran Cleric", "{1}{B}", 2, "B", "As Kai "
                 "Winn enters, choose a nonland card name.\nWhenever an opponent casts a spell with the chosen name or "
                 "activates an ability of a source with the chosen name, that player loses 3 life.", [], "3", "1"),
    "uhura": _card("Nyota Uhura, Communications", f"Legendary Creature {DASH} Human Officer", "{2}{U}", 3, "U",
                   f"Hailing Frequencies {DASH} As Nyota Uhura enters, choose a number between 0 and 10.\nOpen a Channel "
                   f"{DASH} Whenever an opponent casts a spell with mana value equal to the chosen number, you draw a "
                   "card.", [], "2", "4"),
    "bluff": _card("Brazen Bluff", "Instant", "{R}{R}", 2, "R", "Choose target noncreature spell an opponent controls. "
                   "That player may exile it. If they don't, you may cast a noncreature spell from your hand without "
                   "paying its mana cost."),
    "caretaker": _card("The Caretaker", f"Legendary Creature {DASH} Elemental", "{5}{U}", 6, "U", "Vigilance, ward {2}\n"
                       "At the beginning of each end step, if you faced a dilemma this turn, target opponent exiles "
                       "cards from the top of their library until they exile a nonland card. You may cast that card "
                       "without paying its mana cost. (You face a dilemma as you choose one or more modes for a spell or "
                       "ability.)", ["Vigilance", "Ward"], "5", "6"),
    "worf": _card("Worf, Intelligence Contractor", f"Legendary Creature {DASH} Klingon Warrior Spy", "{2}{R}", 3, "R",
                  "When Worf enters, for each opponent, gain control of up to one target creature that player controls "
                  "with mana value 3 or less until end of turn. Untap those creatures. Until end of turn, they become "
                  "Warriors in addition to their other types and gain haste.", [], "3", "2"),
    "explosives": _card("Engineered Explosives", "Artifact", "{X}", 0, "", "Sunburst (This artifact enters with a "
                        "charge counter on it for each color of mana spent to cast it.)\n{2}, Sacrifice this artifact: "
                        "Destroy each nonland permanent with mana value equal to the number of charge counters on this "
                        "artifact.", ["Sunburst"]),
    "peace": _card("Peace in Our Time", "Enchantment", "{3}{W}", 4, "W", "At the beginning of combat on each player's "
                   "turn, that player may draw a card. If they do, they can't attack this turn and you put a peace "
                   "counter on this enchantment.\nAt the beginning of your upkeep, if this enchantment has twelve or "
                   "more peace counters on it, you win the game."),
    "infiltration": _card("Dominion Infiltration", "Sorcery", "{X}{R}{R}{R}", 3, "R", "Choose X target creatures your "
                          "opponents control. For each of them, create a token that's a copy of that creature, except "
                          "it has changeling. Those tokens gain haste. Exile those tokens at the beginning of the next "
                          "end step. (They're every creature type.)"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}


def make(name, cost, cmc, text="", power=None, toughness=None, type_line=f"Creature {DASH} Test", colors="R"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, [], power, toughness))[0]


BEAR = make("Bear", "{1}{G}", 2, "", "2", "2", colors="G")
OGRE = make("Ogre", "{2}{R}", 3, "", "3", "3")
GIANT = make("Giant", "{4}{R}", 5, "", "5", "5")
BOLT = make("Bolt", "{R}", 1, "Bolt deals 3 damage to any target.", type_line="Instant")
MURDER = make("Murder", "{1}{B}{B}", 3, "Destroy target creature.", type_line="Instant", colors="B")
GROWTH = make("Growth", "{G}", 1, "Draw a card.", type_line="Sorcery", colors="G")
RELIC = make("Relic", "{2}", 2, "{T}: You gain 1 life.", type_line="Artifact", colors="")
TOKEN = make("Officer", "", 0, "", "1", "1", f"Creature {DASH} Officer")._replace(is_token=True)


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
    def test_fields(self):
        self.assertEqual(len(C["vger"].choices[1]), 2)
        self.assertEqual(C["vger"].attack_choices, C["vger"].choices)
        self.assertEqual((C["vger"].choices[1][0].draws, C["vger"].choices[1][1].opp_minus_power), (1, 1))
        self.assertEqual(C["salt"].hand_exile, "draw")
        self.assertEqual(C["zero"].hand_exile, "tax")
        self.assertTrue(C["kai"].kai_name)
        self.assertTrue(C["uhura"].uhura_number)
        self.assertTrue(C["bluff"].bluff)
        self.assertTrue(C["caretaker"].caretaker)
        self.assertEqual(C["worf"].threaten_mv, 3)
        self.assertTrue(C["explosives"].sunburst_bomb)
        self.assertTrue(C["peace"].peace)
        self.assertTrue(C["infiltration"].infiltrate)

    def test_coverage(self):
        for key in RAW:
            self.assertEqual(open_lines(key), [], key)


class HandTests(unittest.TestCase):
    def test_salt_vampire(self):
        me, opp = pair()
        opp.hand = [PLAINS, BOLT, GIANT]
        bt.card_effects(me, opp, C["salt"], 3, entry())
        self.assertEqual(sorted(c.name for c in opp.hand), ["Giant", "Plains", "Plains"])  # Removal zuerst, eine gezogen

    def test_salt_vampire_removal_first(self):
        me, opp = pair()
        opp.hand = [MURDER, GIANT]
        bt.card_effects(me, opp, C["salt"], 3, entry())
        self.assertNotIn(MURDER, opp.hand)

    def test_zero_taxed_in_exile(self):
        me, opp = pair()
        opp.hand = [GIANT, PLAINS]
        bt.card_effects(me, opp, C["zero"], 3, entry())
        self.assertEqual(opp.hand, [PLAINS])
        (card, _last), = opp.impulse
        self.assertEqual((card.name, min(g for g, _c in card.alts)), ("Giant", 6))

    def test_vger_modes(self):
        me, opp = pair()
        vger = put(me, C["vger"])
        bt.card_effects(me, opp, C["vger"], 3, entry())
        self.assertEqual(len(me.hand), 1)  # Ziehen, der Gegner hat keine Kreaturen
        a, b = put(opp, OGRE), put(opp, BEAR)
        bt.attack_choice_triggers(me, opp, [vger], 3, entry())
        self.assertEqual((a.power, b.power, len(me.hand)), (2, 1, 1))
        bt.expire_until_next_turn(me, 5)
        self.assertEqual(a.power, 3)


class ChoiceTests(unittest.TestCase):
    def test_uhura_seen_mana_value(self):
        me, opp = pair()
        opp.graveyard = [BOLT, GROWTH, GIANT, PLAINS]
        uh = put(me, C["uhura"], 3)
        bt.creature_enters(me, uh, 3, entry(), opp, cast=False)
        bt.on_cast(opp, BOLT, 3, entry())
        self.assertEqual(len(me.hand), 1)
        bt.on_cast(opp, OGRE, 3, entry())
        self.assertEqual(len(me.hand), 1)

    def test_uhura_default_three(self):
        me, opp = pair()
        uh = put(me, C["uhura"], 3)
        bt.creature_enters(me, uh, 3, entry(), opp, cast=False)
        bt.on_cast(opp, OGRE, 3, entry())
        self.assertEqual(len(me.hand), 1)

    def test_kai_winn(self):
        me, opp = pair()
        put(opp, BEAR)
        put(opp, BEAR)  # das Feld zaehlt mit: Bear zweimal gesehen
        opp.graveyard = [OGRE]
        kai = put(me, C["kai"], 3)
        bt.creature_enters(me, kai, 3, entry(), opp, cast=False)
        bt.on_cast(opp, BEAR, 3, entry())
        self.assertEqual(opp.life, 17)
        bt.on_cast(opp, OGRE, 3, entry())
        self.assertEqual(opp.life, 17)

    def test_kai_winn_without_seen_cards(self):
        me, opp = pair()
        kai = put(me, C["kai"], 3)
        bt.creature_enters(me, kai, 3, entry(), opp, cast=False)
        bt.on_cast(opp, OGRE, 3, entry())
        self.assertEqual(opp.life, 20)


class BluffTests(unittest.TestCase):
    def test_opponent_gives_up_spell(self):
        me, opp = pair()
        put(opp, GIANT)
        opp.hand, opp.open = [C["bluff"], RELIC], [("R",)] * 2
        bt._resolve(me, opp, MURDER, 3, entry())  # Removal auf den Riesen; wir haben Relic (MW 2) - er gibt nicht auf
        self.assertEqual((opp.creatures, opp.perms, opp.hand), ([], [RELIC], []))

    def test_opponent_exiles_when_our_card_is_bigger(self):
        me, opp = pair()
        giant = put(opp, GIANT)
        big = make("Big Relic", "{5}", 5, "{T}: You gain 1 life.", type_line="Artifact", colors="")
        opp.hand, opp.open = [C["bluff"], big], [("R",)] * 2
        bt._resolve(me, opp, MURDER, 3, entry())
        self.assertEqual((giant in opp.creatures, opp.hand), (True, [big]))

    def test_needs_noncreature_card_in_hand(self):
        me, opp = pair()
        put(opp, GIANT)
        opp.hand, opp.open = [C["bluff"], OGRE], [("R",)] * 2
        bt._resolve(me, opp, MURDER, 3, entry())
        self.assertIn(C["bluff"], opp.hand)


class BoardTests(unittest.TestCase):
    def test_caretaker(self):
        me, opp = pair()
        put(me, C["caretaker"])
        opp.library = [PLAINS, PLAINS, OGRE, BEAR]
        bt.end_step_triggers(me, opp, entry())
        self.assertEqual(len(me.creatures), 1)
        me.dilemmas_turn = 1
        bt.end_step_triggers(me, opp, entry())
        self.assertEqual(sorted(c.card.name for c in me.creatures), ["Ogre", "The Caretaker"])
        self.assertEqual(opp.library, [BEAR])

    def test_worf_steals_until_end_step(self):
        me, opp = pair()
        ogre, _giant = put(opp, OGRE), put(opp, GIANT)
        ogre.tapped = True
        put(me, C["worf"], 3)
        bt.card_effects(me, opp, C["worf"], 3, entry())
        self.assertIn(ogre, me.creatures)
        self.assertTrue(bt.can_attack(ogre, 3))
        bt.end_step_triggers(me, opp, entry())
        self.assertIn(ogre, opp.creatures)
        self.assertNotIn(ogre, me.creatures)

    def test_infiltration(self):
        me, opp = pair()
        put(opp, OGRE)
        put(opp, BEAR)
        put(opp, GIANT)
        me.open = [("R",)] * 2
        bt.card_effects(me, opp, C["infiltration"], 3, entry())
        self.assertEqual(sorted(c.card.name for c in me.creatures), ["Giant", "Ogre"])
        self.assertTrue(all(bt.can_attack(c, 3) and c.exile_step == 3 for c in me.creatures))

    def test_explosives(self):
        me, opp = pair()
        me.turn_start = 3
        put(opp, TOKEN)
        put(opp, TOKEN)
        put(me, BEAR)
        me.hand, me.open = [C["explosives"]], [("R",), ("G",)]
        bt.explosives_phase(me, opp, 3, entry())  # Marken 0: zwei gegnerische Token
        self.assertEqual(me.hand, [])
        self.assertEqual(me.explosives[0]["charge"], 0)
        bt.explosives_phase(me, opp, 3, entry())  # erst ab dem naechsten Zug
        self.assertEqual(len(opp.creatures), 2)
        me.turn_start, me.open = 5, [("R",)] * 2
        bt.explosives_phase(me, opp, 5, entry())
        bt.bury((me, opp), entry())
        self.assertEqual((opp.creatures, len(me.creatures), me.perms), ([], 1, []))

    def test_explosives_counts_our_losses(self):
        me, opp = pair()
        put(opp, TOKEN)
        for _ in range(3):
            put(me, TOKEN)
        me.hand, me.open = [C["explosives"]], [("R",), ("G",)]
        bt.explosives_phase(me, opp, 3, entry())
        self.assertEqual(me.hand, [C["explosives"]])

    def test_peace_in_our_time(self):
        me, opp = pair()
        me.perms.append(C["peace"])
        bt.permanent_enters(me, opp, C["peace"], 1, entry())
        self.assertTrue(bt.peace_combat(opp, me, 3, entry()))  # keine Kreatur: zieht
        self.assertEqual((len(opp.hand), me.peace[0]["count"]), (1, 1))
        put(opp, OGRE)
        self.assertFalse(bt.peace_combat(opp, me, 5, entry()))  # greift an
        me.peace[0]["count"] = 11
        opp.creatures.clear()
        self.assertFalse(bt.peace_combat(opp, me, 7, entry()))  # sonst gewinnt der Besitzer
        self.assertTrue(bt.peace_combat(me, opp, 8, entry()))
        bt.upkeep_triggers(me, opp, 9, entry())
        self.assertLessEqual(opp.life, 0)


if __name__ == "__main__":
    unittest.main()
