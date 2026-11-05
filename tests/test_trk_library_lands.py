"""Star Trek (TRK), Paket R7 (Nutzer 2026-11-05): Bibliothek, Laender, Blink - Ghost of Illyria, Miles O'Brien, Q,
Stacking the Deck (Kopien in Main 2 mit sonst ungenutztem Mana), Will Riker, Captain Janeway (zusaetzlicher Landdrop,
Explore), Captain Pike (Laender von oben), Genesis Device (Laender tauschen, wenn eine Farbe fehlt; duennt die
Bibliothek aus), U.S.S. Discovery (Discover 5), Deep Space 9, The Holodeck. Nur Kampfmodell. Kartentexte aus TRK."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from components.mana import cost_alternatives
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)", produced=[color]))[0]


FOREST, MOUNTAIN, ISLAND = land("Forest", "G"), land("Mountain", "R"), land("Island", "U")

RAW = {
    "ghost": _card("Ghost of Illyria", f"Creature {DASH} Elemental Spirit", "{3}{W}", 4, "W", "Flying\nWhen this creature "
                   "enters, exile up to one other target nonland permanent you control. Return that card to the "
                   "battlefield under its owner's control at the beginning of the next end step.", ["Flying"], "3", "3"),
    "miles": _card("Miles O'Brien, Transporter Ops", f"Legendary Creature {DASH} Human Artificer", "{2}{W}", 3, "W",
                   "When Miles O'Brien enters, return up to one other target creature or artifact you control to its "
                   "owner's hand.\nAt the beginning of each end step, if a permanent was returned to your hand from the "
                   "battlefield this turn, draw a card.", [], "3", "3"),
    "q": _card("Q, Stacking the Deck", f"Legendary Creature {DASH} Q", "{2}{R}{R}", 4, "R", "When Q enters, shuffle your "
               "library, then exile cards from the top of your library until you exile a nonland card. That nonland card "
               "gains \"Exile a card from your hand: Create a copy of this card. You may cast the copy. Activate only "
               "during your turn and only if this card is exiled.\"", [], "4", "4"),
    "riker": _card("Will Riker, First in the Field", f"Legendary Creature {DASH} Human Officer", "{3}{R}", 4, "R", "At "
                   "the beginning of combat on your turn, reveal cards from the top of your library until you reveal two "
                   "land cards. Put those land cards onto the battlefield and the rest on the bottom of your library in "
                   "a random order. Sacrifice those lands at the beginning of your next end step.", [], "4", "3"),
    "janeway": _card("Captain Kathryn Janeway", f"Legendary Creature {DASH} Human Officer", "{3}{G}", 4, "G", "You may "
                     "play an additional land on each of your turns.\nWhenever Captain Janeway or another creature you "
                     "control enters, that creature explores. (Reveal the top card of your library. Put that card into "
                     "your hand if it's a land. Otherwise, put a +1/+1 counter on the creature, then put the card back "
                     "or put it into your graveyard.)", [], "2", "3"),
    "pike": _card("Captain Pike, Fullness of Time", f"Legendary Creature {DASH} Human Officer Scout", "{1}{G}{G}", 3, "G",
                  f"Strange new worlds {DASH} Captain Pike's power and toughness are each equal to the number of "
                  "differently named lands you control.\nYou may look at the top card of your library any time.\nYou may "
                  "play lands from the top of your library.", [], "*", "*"),
    "genesis": _card("Genesis Device", "Legendary Artifact", "{2}{G}", 3, "G", "When Genesis Device enters, search your "
                     "library for a basic land card or Planet card, put it onto the battlefield tapped, then shuffle.\n"
                     "{3}{G}{G}, {T}, Sacrifice Genesis Device: Sacrifice any number of lands you control, then search "
                     "your library for up to that many land cards, put them onto the battlefield tapped, then shuffle. "
                     "Activate only as a sorcery."),
    "discovery": _card("U.S.S. Discovery, at Black Alert", f"Legendary Artifact {DASH} Spacecraft", "{3}{G}{G}", 5, "G",
                       "Whenever U.S.S. Discovery enters or attacks, discover 5. (Exile cards from the top of your "
                       "library until you exile a nonland card with mana value 5 or less. Cast it without paying its "
                       "mana cost or put it into your hand. Put the rest on the bottom in a random order.)\nStation\n6+ | "
                       "Flying", [], "5", "5"),
    "ds9": _card("Deep Space 9", f"Legendary Artifact {DASH} Spacecraft", "{9}", 9, "", "When Deep Space 9 enters and at "
                 "the beginning of your upkeep, exile the top four cards of your library. Put all permanent cards "
                 "exiled this way onto the battlefield.\nStation (Tap another creature you control: Put charge counters "
                 "equal to its power on this Spacecraft. Station only as a sorcery.)\n9+ | Creatures you control get "
                 "+3/+3."),
    "holodeck": _card("The Holodeck", "Legendary Artifact", "{7}", 7, "", "Once during each of your turns, you may play a "
                      "permanent card you own from outside the game or from your graveyard."),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}


def make(name, cost, cmc, text="", power=None, toughness=None, type_line=f"Creature {DASH} Test", colors="G"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, [], power, toughness))[0]


BEAR = make("Bear", "{1}{G}", 2, "", "2", "2")
OGRE = make("Ogre", "{2}{R}", 3, "", "3", "3", colors="R")
SEER = make("Seer", "{1}{G}", 2, "When this creature enters, draw a card.", "1", "1")
BOLT = make("Bolt", "{R}", 1, "Bolt deals 3 damage to any target.", type_line="Instant", colors="R")
GIANT = make("Giant", "{5}{G}", 6, "", "6", "6")
WHITE = make("Knight", "{1}{W}", 2, "", "2", "2", colors="W")


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


def names(p):
    return sorted(c.card.name for c in p.creatures)


def open_lines(key):
    return [l for _c, _m, l in analyze_card(RAW[key])]


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertTrue(C["ghost"].ghost_blink)
        self.assertTrue(C["miles"].miles_bounce)
        self.assertTrue(C["miles"].returned_draw)
        self.assertTrue(C["q"].q_stack)
        self.assertEqual(C["riker"].riker_lands, 2)
        self.assertEqual(C["janeway"].extra_land, 1)
        self.assertTrue(C["janeway"].explore_enter)
        self.assertTrue(C["pike"].top_lands)
        self.assertEqual(C["genesis"].genesis_swap, cost_alternatives("{3}{G}{G}"))
        self.assertEqual(C["discovery"].discover, 5)
        self.assertEqual(C["ds9"].ds9_reveal, 4)
        self.assertTrue(C["holodeck"].holodeck)

    def test_coverage(self):
        for key in RAW:
            self.assertEqual(open_lines(key), [], key)


class BlinkBounceTests(unittest.TestCase):
    def test_ghost_blinks_etb_creature(self):
        me, opp = pair()
        put(me, SEER, 3)
        put(me, C["ghost"], 3)
        bt.card_effects(me, opp, C["ghost"], 3, entry())
        self.assertEqual(names(me), ["Ghost of Illyria"])
        bt.end_step_triggers(me, opp, entry())
        self.assertEqual((names(me), len(me.hand)), (["Ghost of Illyria", "Seer"], 1))

    def test_ghost_without_etb_target(self):
        me, opp = pair()
        put(me, BEAR)
        put(me, C["ghost"], 3)
        bt.card_effects(me, opp, C["ghost"], 3, entry())
        self.assertEqual(names(me), ["Bear", "Ghost of Illyria"])

    def test_miles(self):
        me, opp = pair()
        put(me, SEER)
        put(me, C["miles"], 3)
        bt.card_effects(me, opp, C["miles"], 3, entry())
        self.assertEqual((names(me), me.hand), (["Miles O'Brien, Transporter Ops"], [SEER]))
        bt.end_step_triggers(me, opp, entry())
        self.assertEqual(len(me.hand), 2)

    def test_miles_without_etb_creature(self):
        me, opp = pair()
        put(me, BEAR)
        put(me, C["miles"], 3)
        bt.card_effects(me, opp, C["miles"], 3, entry())
        self.assertEqual((names(me), me.hand), (["Bear", "Miles O'Brien, Transporter Ops"], []))

    def test_miles_draws_after_opponent_bounce(self):
        me, opp = pair()
        put(me, C["miles"])
        bear = put(me, BEAR)
        bounce = make("Unsummon", "{U}", 1, "Return target creature to its owner's hand.", type_line="Instant", colors="U")
        bt.cast_removal(bounce, opp, me, entry(), 3, target=bear)
        bt.end_step_triggers(opp, me, entry())  # "each end step": auch im Zug des Gegners
        self.assertEqual(len(me.hand), 2)


class LibraryTests(unittest.TestCase):
    def test_q_exiles_and_copies(self):
        me, opp = pair()
        me.library = [PLAINS, PLAINS, OGRE, PLAINS]
        put(me, C["q"], 3)
        bt.card_effects(me, opp, C["q"], 3, entry())
        self.assertEqual(me.q_cards, [OGRE])
        self.assertNotIn(OGRE, me.library)
        me.lands = [MOUNTAIN] * 3
        me.hand, me.open = [MOUNTAIN, BEAR], [("R",)] * 3
        bt.q_copies(me, opp, 5, entry())
        self.assertEqual((names(me).count("Ogre"), me.hand), (1, [BEAR]))
        tok = next(c for c in me.creatures if c.card.name == "Ogre")
        self.assertTrue(tok.card.is_token)

    def test_q_keeps_last_castable_card(self):
        me, opp = pair()
        me.q_cards = [OGRE]
        me.lands = [MOUNTAIN] * 2
        me.hand, me.open = [BEAR], [("R",)] * 3
        bt.q_copies(me, opp, 5, entry())
        self.assertEqual((me.hand, me.creatures), ([BEAR], []))

    def test_riker(self):
        me, opp = pair()
        put(me, C["riker"])
        me.library = [BEAR, FOREST, OGRE, MOUNTAIN, ISLAND]
        bt.combat_tokens(me, opp, 3, entry())
        self.assertEqual((sorted(l.name for l in me.lands), len(me.open)), (["Forest", "Mountain"], 2))
        self.assertEqual(me.library[0], ISLAND)
        bt.end_step_triggers(me, opp, entry())
        self.assertEqual(me.lands, [])

    def test_janeway_explore(self):
        me, opp = pair()
        put(me, C["janeway"])
        me.library = [FOREST, OGRE]
        bear = put(me, BEAR, 3)
        bt.creature_enters(me, bear, 3, entry(), opp, cast=False)
        self.assertEqual((me.hand, bear.bonus), ([FOREST], 0))
        bear2 = put(me, BEAR, 3)
        bt.creature_enters(me, bear2, 3, entry(), opp, cast=False)
        self.assertEqual(bear2.bonus, 1)

    def test_janeway_extra_land_and_pike_top(self):
        me, opp = pair()
        put(me, C["janeway"])
        put(me, C["pike"])
        me.lands = [FOREST] * 2
        me.hand = [FOREST]
        me.library = [MOUNTAIN, PLAINS, PLAINS, PLAINS]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((len(me.lands), me.hand), (4, []))  # Hand-Land und Mountain von oben
        self.assertEqual(me.library, [PLAINS] * 3)

    def test_genesis_swap(self):
        me, opp = pair()
        me.perms.append(C["genesis"])
        me.lands = [FOREST] * 6
        me.hand = [WHITE]
        me.library = [BEAR, PLAINS, FOREST, OGRE, FOREST]
        me.open = [("G",)] * 5
        bt.genesis_swap(me, opp, 5, entry())
        self.assertEqual(sorted(l.name for l in me.lands), ["Forest"] * 5 + ["Plains"])
        self.assertEqual(([c for c in me.library if c.is_land], me.perms, me.open), ([], [], []))
        self.assertIn(C["genesis"], me.graveyard)

    def test_genesis_missing_color_first(self):
        me, opp = pair()
        me.perms.append(C["genesis"])
        me.lands = [FOREST] * 3
        me.hand = [WHITE]
        me.library = [FOREST, FOREST, FOREST, PLAINS]
        me.open = [("G",)] * 5
        bt.genesis_swap(me, opp, 5, entry())
        self.assertIn(PLAINS, me.lands)
        self.assertEqual(len(me.lands), 3)

    def test_genesis_not_without_missing_color(self):
        me, opp = pair()
        me.perms.append(C["genesis"])
        me.lands = [FOREST] * 6
        me.hand = [BEAR]
        me.library = [PLAINS, FOREST]
        me.open = [("G",)] * 5
        bt.genesis_swap(me, opp, 5, entry())
        self.assertEqual(me.perms, [C["genesis"]])

    def test_discover(self):
        me, opp = pair()
        me.library = [PLAINS, GIANT, OGRE, BEAR]
        bt.discover(me, opp, 5, 3, entry())
        self.assertEqual(names(me), ["Ogre"])
        self.assertEqual(me.library[0], BEAR)

    def test_ds9(self):
        me, opp = pair()
        me.library = [BEAR, FOREST, BOLT, OGRE, PLAINS]
        bt.ds9_reveal(me, opp, 4, 3, entry())
        self.assertEqual((names(me), [l.name for l in me.lands], me.library), (["Bear", "Ogre"], ["Forest"], [PLAINS]))
        self.assertEqual(me.perms, [])  # Bolt bleibt im Exil

    def test_holodeck_once_per_turn(self):
        me, opp = pair()
        me.perms.append(C["holodeck"])
        me.lands = [MOUNTAIN] * 3
        me.graveyard = [OGRE, BEAR]
        me.hand, me.library = [], [PLAINS] * 10
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((names(me), me.graveyard), (["Ogre"], [BEAR]))
        me.graveyard, me.open = [OGRE], []
        bt.take_turn(me, opp, 5, 3, skip_draw=True)  # derselbe Zug: nicht noch einmal
        self.assertEqual(names(me), ["Ogre"])


if __name__ == "__main__":
    unittest.main()
