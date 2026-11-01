"""Star Trek (TRK), Paket G (Nutzer 2026-11-01): Quest-Missionen - jede Mission zaehlt ihre eigenen Quest-Marken (ein
neues Objekt je Mission im Spiel, 400.7); erst die Marke, dann der Effekt, ab der Schwelle der staerkere. Conquest
(nicht-Token-Artefakt kommt: Borg-Token), Anthropological (Nichtkreatur-Zauber: ziehen, abwerfen bis 3 Marken),
Vengeance (eine Kreatur stirbt: Gegner verliert 1, ab 7 Marken 2), Exploratory (Landfall: bis zur ersten
Nichtland-Karte exilieren, in Main 2 spielbar; ab 5 Marken {R}{R}), Support (eigene Kreatur kommt: Marke, ab 5 zwei).
Nur Kampfmodell. Kartentexte aus TRK."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]


def raw(name, cost, cmc, text, colors):
    return _card(name, "Enchantment", cost, cmc, colors, text, [], None, None)


RAW = {
    "conquest": raw("Conquest Mission", "{2}{W}", 3, "Whenever a nontoken artifact you control enters, put a quest "
                    "counter on this enchantment. Create a 1/1 colorless Borg artifact creature token. If this "
                    "enchantment has six or more quest counters on it, create two of those tokens instead.", "W"),
    "anthro": raw("Anthropological Mission", "{2}{U}", 3, "Whenever you cast a noncreature spell, put a quest counter "
                  "on this enchantment. Draw a card. Then discard a card unless this enchantment has three or more "
                  "quest counters on it.", "U"),
    "vengeance": raw("Vengeance Mission", "{2}{B}", 3, "Whenever a creature dies, put a quest counter on this "
                     "enchantment. Target opponent loses 1 life. That player loses 2 life instead if there are seven or "
                     "more quest counters on this enchantment.", "B"),
    "explore": raw("Exploratory Mission", "{2}{R}{R}", 4, "Landfall — Whenever a land you control enters, put a quest "
                   "counter on this enchantment. Then exile cards from the top of your library until you exile a "
                   "nonland card. You may play that card this turn. If this enchantment has five or more quest "
                   "counters on it, add {R}{R}.", "R"),
    "support": raw("Support Mission", "{2}{G}", 3, "Whenever a creature you control enters, put a quest counter on this "
                   "enchantment. Put a +1/+1 counter on that creature. If this enchantment has five or more quest "
                   "counters on it, instead put two +1/+1 counters on that creature.", "G"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}
OGRE = card_info(_card("Ogre", f"Creature {DASH} Ogre", "{2}{R}", 3, "R", "", [], "3", "3"))[0]
ELF = card_info(_card("Elf", f"Creature {DASH} Elf", "{G}", 1, "G", "", [], "1", "1"))[0]
ROCK = card_info(_card("Test Rock", "Artifact", "{2}", 2, "", ""))[0]
PEEK = card_info(_card("Test Peek", "Sorcery", "{1}{U}", 2, "U", "Draw a card."))[0]


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def pair(library=None):
    me, opp = player(library=library), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


def put(p, card, entered=0):
    c = bt.Creature(card, entered)
    c.gy, c.ctl = p.graveyard, p
    p.creatures.append(c)
    return c


def enter(p, opp, card):
    p.perms.append(card)
    bt.permanent_enters(p, opp, card, p.now, entry())


def quest(p):
    return [m["quest"] for m in p.missions]


class ParseTests(unittest.TestCase):
    def test_missions(self):
        self.assertEqual(C["conquest"].mission[0::2], ("artifact_enters", 6))
        self.assertEqual(C["anthro"].mission, ("noncreature_cast", None, 3))
        self.assertEqual(C["vengeance"].mission, ("creature_dies", None, 7))
        self.assertEqual(C["explore"].mission, ("landfall", None, 5))
        self.assertEqual(C["support"].mission, ("creature_enters", None, 5))
        self.assertEqual(C["conquest"].mission[1].name, "Borg")

    def test_coverage(self):
        for key, r in RAW.items():
            self.assertEqual([l for _c, _m, l in analyze_card(r)], [], key)


class MissionTests(unittest.TestCase):
    def test_conquest_tokens(self):
        me, opp = pair()
        enter(me, opp, C["conquest"])
        enter(me, opp, ROCK)
        self.assertEqual((quest(me), [c.card.name for c in me.creatures]), ([1], ["Borg"]))  # Token zaehlt nicht
        me.missions[0]["quest"] = 5
        enter(me, opp, ROCK)
        self.assertEqual([c.card.name for c in me.creatures].count("Borg"), 3)

    def test_two_missions_count_apart(self):
        me, opp = pair()
        enter(me, opp, C["conquest"])
        enter(me, opp, ROCK)
        enter(me, opp, C["conquest"])
        enter(me, opp, ROCK)
        self.assertEqual(quest(me), [2, 1])

    def test_one_of_two_same_missions_leaves(self):
        me, opp = pair()
        enter(me, opp, C["conquest"])
        enter(me, opp, C["conquest"])
        me.perms.remove(me.missions[0]["card"])
        enter(me, opp, ROCK)
        self.assertEqual(len(me.creatures), 1)

    def test_mission_leaves(self):
        me, opp = pair()
        enter(me, opp, C["conquest"])
        me.perms.remove(me.missions[0]["card"])
        enter(me, opp, ROCK)
        self.assertEqual(me.creatures, [])

    def test_anthropological_loot_then_draw(self):
        me, opp = pair(library=[PLAINS] * 5)
        enter(me, opp, C["anthro"])
        me.hand = [OGRE]
        bt.on_cast(me, PEEK, 3, entry())
        self.assertEqual(len(me.hand), 1)  # gezogen, abgeworfen
        bt.on_cast(me, OGRE, 3, entry())  # Kreatur: nichts
        me.missions[0]["quest"] = 2
        bt.on_cast(me, PEEK, 3, entry())
        self.assertEqual((len(me.hand), quest(me)), (2, [3]))

    def test_vengeance(self):
        me, opp = pair()
        enter(me, opp, C["vengeance"])
        a, b = put(opp, ELF), put(me, ELF)
        a.dead = b.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual((opp.life, quest(me)), (18, [2]))
        me.missions[0]["quest"] = 6
        c = put(opp, ELF)
        c.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual(opp.life, 16)

    def test_exploratory(self):
        me, opp = pair(library=[PLAINS, PLAINS, OGRE, ELF])
        enter(me, opp, C["explore"])
        mana = bt.on_land(me, opp, PLAINS, 3, entry())
        self.assertEqual((mana, [c.name for c, _l in me.impulse], me.library), ([], ["Ogre"], [ELF]))
        me.open = [("R",)] * 3
        bt.combat_impulse_main2(me, opp, 3, entry())
        self.assertTrue(any(c.card is OGRE for c in me.creatures))
        me.missions[0]["quest"] = 4
        me.library = [ELF]
        mana = bt.on_land(me, opp, PLAINS, 3, entry())
        self.assertEqual(mana, [("R",), ("R",)])

    def test_exploratory_no_mana_outside_main(self):
        me, opp = pair(library=[ELF])
        enter(me, opp, C["explore"])
        me.missions[0]["quest"] = 4
        self.assertEqual(bt.on_land(me, opp, PLAINS, 3, entry(), with_mana=False), [])

    def test_support(self):
        me, opp = pair()
        enter(me, opp, C["support"])
        ogre = put(me, OGRE)
        bt.creature_enters(me, ogre, 3, entry(), opp)
        self.assertEqual((ogre.bonus, quest(me)), (1, [1]))
        me.missions[0]["quest"] = 4
        elf = put(me, ELF)
        bt.creature_enters(me, elf, 3, entry(), opp)
        self.assertEqual(elf.bonus, 2)


if __name__ == "__main__":
    unittest.main()
