"""Star Trek (TRK), Paket F (Nutzer 2026-11-01): Federation - X ist die Zahl der Kreaturtypen unter den eigenen
Nicht-Borg-Kreaturen, immer im Moment der Wirkung gezaehlt. Saavik (Flash, Schaden an einem Angreifer), Hoshi Sato
(oberste X Karten, eine auf die Hand), Captain Archer (Porthos, Pump +X/+X), Sarek (je fuenf Typen eine Karte),
Infinite Diversity (Instant/Sorcery aus dem Friedhof X-mal kopieren), Starfleet Academy (beim Bilden des Manas zu
Zugbeginn, wenn X mehr als die eingesetzten Laender bringt). Nur Kampfmodell."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
FED = "Federation — "
WHERE = ", where X is the number of creature types among non-Borg creatures you control"
PLAINS = W["Plains"]


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="W"):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)


RAW = {
    "saavik": raw("Saavik, Stoic Student", f"Legendary Creature {DASH} Vulcan Advisor", "{4}{W}", 5, "Flash\n" + FED
                  + "When Saavik enters, she deals X damage to target attacking or blocking creature an opponent "
                  "controls" + WHERE + ".", "2", "2", ["Flash"]),
    "hoshi": raw("Hoshi Sato, Exolinguist", f"Legendary Creature {DASH} Human Scientist", "{4}{U}", 5, FED + "When "
                 "Hoshi Sato enters, look at the top X cards of your library" + WHERE + ". Put one of them into your "
                 "hand and the rest on the bottom of your library in a random order.", "3", "3", colors="U"),
    "archer": raw("Captain Jonathan Archer", f"Legendary Creature {DASH} Human Officer", "{2}{G}", 3, "When Captain "
                  "Archer enters, create Porthos, a legendary 1/1 green Dog creature token.\n" + FED + "{G}, {T}: "
                  "Target creature you control gets +X/+X until end of turn" + WHERE + ". Activate only as a "
                  "sorcery.", "3", "3", colors="G"),
    "sarek": raw("Sarek, Federation Ambassador", f"Legendary Creature {DASH} Vulcan Advisor", "{1}{G}{W}{U}", 4, FED
                 + "At the beginning of combat on your turn, draw a card for every five creature types among non-Borg "
                 "creatures you control. If you draw three or more cards this way, put two +1/+1 counters on each "
                 "creature you control.", "0", "5", colors="GWU"),
    "diversity": raw("Infinite Diversity", "Sorcery", "{7}{R}{R}", 9, FED + "Exile target instant or sorcery card from "
                     "your graveyard. Copy that card X times" + WHERE + ". You may cast the copies without paying "
                     "their mana costs. Exile Infinite Diversity.", colors="R"),
    "academy": _card("Starfleet Academy", "Legendary Land", text="{T}: Add {C}.\n" + FED + "{5}, {T}: Choose a "
                     "color. Add an amount of mana of that color equal to the number of creature types among non-Borg "
                     "creatures you control.", produced=["C"]),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}


def creature(name, types, power="2", toughness="2", artifact=False):
    kind = ("Artifact Creature" if artifact else "Creature") + f" {DASH} " + types
    return card_info(_card(name, kind, "{2}", 2, "", "", [], power, toughness))[0]


ELF_WARRIOR = creature("Elf Warrior", "Elf Warrior")
BORG = creature("Drone", "Borg Human", artifact=True)
GIANT = creature("Giant", "Giant", "5", "5")
OGRE = creature("Ogre", "Ogre", "3", "3")
SHOCK = card_info(_card("Test Shock", "Sorcery", "{R}", 1, "R", "Test Shock deals 2 damage to each opponent."))[0]
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


class ParseTests(unittest.TestCase):
    def test_fields(self):
        spec = C["saavik"].removal
        self.assertEqual((spec[0], spec[1], spec[4]), ("damage", -4, "etb"))
        self.assertIn(("attacking",), spec[2])
        self.assertTrue(C["hoshi"].fed_dig)
        self.assertEqual(C["archer"].fed_pump, ((0, (("G", 1),)),))
        self.assertEqual(C["archer"].creates_tokens[0][1].name, "Porthos")
        self.assertTrue(C["sarek"].fed_draw)
        self.assertTrue(C["diversity"].fed_copy)

    def test_coverage(self):
        for key, r in RAW.items():
            self.assertEqual([l for _c, _m, l in analyze_card(r)], [], key)


class CountTests(unittest.TestCase):
    def test_federation_x(self):
        me, _opp = pair()
        put(me, ELF_WARRIOR), put(me, BORG), put(me, creature("Elf", "Elf"))
        self.assertEqual(bt.federation_x(me), 2)  # Elf, Warrior; Borg zaehlt nicht (auch nicht "Human")
        self.assertEqual(bt.federation_x(me, ("vulcan", "advisor")), 4)


class AcademyTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual((C["academy"].fed_mana, C["academy"].land_colors), (5, ("C",)))

    def test_academy_when_it_pays(self):
        me, _opp = pair()
        me.lands = [C["academy"]] + [PLAINS] * 5
        for name, types in (("A", "Elf Warrior"), ("B", "Human Wizard"), ("C", "Goblin Rogue"), ("D", "Bird Cat")):
            put(me, creature(name, types))
        me.hand = [card_info(_card("Big", f"Creature {DASH} Wurm", "{6}{G}{G}", 8, "G", "", [], "8", "8"))[0]]
        pool = bt.academy_mana(me, [("C",)] + [("W",)] * 5)
        self.assertEqual(sorted(pool), [("G",)] * 8)  # 8 Typen statt 6 Mana, Farbe nach der Hand

    def test_academy_in_turn(self):
        me, opp = pair()
        me.lands = [C["academy"]] + [PLAINS] * 5
        for name, types in (("A", "Elf Warrior"), ("B", "Human Wizard"), ("C", "Goblin Rogue"), ("D", "Bird Cat")):
            put(me, creature(name, types))
        wurm = card_info(_card("Big", f"Creature {DASH} Wurm", "{6}{G}{G}", 8, "G", "", [], "8", "8"))[0]
        me.hand = [wurm]
        bt.take_turn(me, opp, 5, 3, True)
        self.assertTrue(any(c.card is wurm for c in me.creatures))

    def test_academy_not_without_gain(self):
        me, _opp = pair()
        me.lands = [C["academy"]] + [PLAINS] * 5
        put(me, ELF_WARRIOR)
        pool = [("C",)] + [("W",)] * 5
        self.assertEqual(bt.academy_mana(me, list(pool)), pool)

    def test_academy_keeps_needed_colors(self):
        me, _opp = pair()
        me.lands = [C["academy"]] + [PLAINS] * 5 + [card_info(_card("Island", f"Basic Land {DASH} Island",
                                                                     text="({T}: Add {U}.)", produced=["U"]))[0]]
        for name, types in (("A", "Elf Warrior"), ("B", "Human Wizard"), ("C", "Goblin Rogue"), ("D", "Bird Cat")):
            put(me, creature(name, types))
        me.hand = [card_info(_card("Big", f"Creature {DASH} Wurm", "{6}{G}{G}", 8, "G", "", [], "8", "8"))[0],
                   card_info(_card("Wisp", f"Creature {DASH} Spirit", "{U}", 1, "U", "", [], "1", "1"))[0]]
        pool = bt.academy_mana(me, [("C",)] + [("W",)] * 5 + [("U",)])
        self.assertIn(("U",), pool)
        self.assertEqual(pool.count(("G",)), 8)


class SaavikTests(unittest.TestCase):
    def test_saavik_kills_attacker(self):
        me, opp = pair()
        put(me, ELF_WARRIOR)
        me.hand = [C["saavik"]]
        me.open = [("W",)] * 5
        ogre = put(opp, OGRE)
        opp.now = me.now = 4
        ogre.attacked = 4
        left = bt.respond_to_attack(me, opp, [ogre], entry(), 4)
        self.assertEqual(left, [])  # 4 Typen: 4 Schaden an der 3/3
        self.assertTrue(any(c.card.name.startswith("Saavik") for c in me.creatures))

    def test_saavik_hits_only_attackers(self):
        me, opp = pair()
        put(me, ELF_WARRIOR)
        me.hand = [C["saavik"]]
        me.open = [("W",)] * 5
        home = put(opp, OGRE)
        elf = put(opp, creature("Elf", "Elf", "1", "1"))
        opp.now = me.now = 4
        elf.attacked = 4
        bt.respond_to_attack(me, opp, [elf], entry(), 4)
        self.assertEqual((elf in opp.creatures, home in opp.creatures), (False, True))

    def test_saavik_waits_without_kill(self):
        me, opp = pair()
        me.hand = [C["saavik"]]
        me.open = [("W",)] * 5
        giant = put(opp, GIANT)
        opp.now = me.now = 4
        giant.attacked = 4
        bt.respond_to_attack(me, opp, [giant], entry(), 4)
        self.assertEqual(me.hand, [C["saavik"]])  # 2 Typen reichen nicht fuer die 5/5

    def test_saavik_held_at_end_step(self):
        me, opp = pair()
        me.hand = [C["saavik"]]
        me.open = [("W",)] * 5
        bt.end_step_instants(me, opp, entry(), 5)
        self.assertEqual(me.hand, [C["saavik"]])


class OtherTests(unittest.TestCase):
    def test_hoshi_digs(self):
        me, opp = pair(library=[PLAINS, PEEK, GIANT, OGRE, ELF_WARRIOR])
        me.lands = [PLAINS] * 5
        hoshi = put(me, C["hoshi"], 3)
        bt.creature_enters(me, hoshi, 3, entry(), opp)
        self.assertEqual(me.hand, [PEEK])  # X = 2 (Human, Scientist): aus Plains und Peek die Nichtland-Karte
        self.assertEqual(me.library, [GIANT, OGRE, ELF_WARRIOR, PLAINS])  # der Rest unter die Bibliothek

    def test_hoshi_takes_land_when_needed(self):
        me, opp = pair(library=[PEEK, PLAINS, GIANT])
        me.lands = [PLAINS]
        hoshi = put(me, C["hoshi"], 3)
        bt.creature_enters(me, hoshi, 3, entry(), opp)
        self.assertEqual(me.hand, [PLAINS])

    def test_archer_pumps_attacker(self):
        me, opp = pair()
        archer, ogre = put(me, C["archer"]), put(me, OGRE)
        me.turn_start = me.now = 3
        me.open = [("G",)]
        put(opp, OGRE)
        bt.federation_pumps(me, opp, 3, entry())
        self.assertEqual((ogre.power, ogre.toughness, archer.tapped), (6, 6, True))  # Human, Officer, Ogre

    def test_archer_not_without_free_mana(self):
        me, opp = pair()
        archer, ogre = put(me, C["archer"]), put(me, OGRE)
        me.turn_start = me.now = 3
        me.open = []
        bt.federation_pumps(me, opp, 3, entry())
        self.assertEqual((ogre.power, archer.tapped), (3, False))

    def test_sarek_draws_per_five_types(self):
        me, opp = pair(library=[PLAINS] * 5)
        put(me, C["sarek"])
        put(me, ELF_WARRIOR), put(me, creature("Wizard Rogue", "Human Wizard Rogue"))
        bt.federation_draws(me, 3, entry())
        self.assertEqual(len(me.hand), 1)  # 7 Typen

    def test_diversity_copies(self):
        me, opp = pair()
        put(me, ELF_WARRIOR), put(me, creature("Wizard", "Wizard"))
        me.graveyard.extend([SHOCK, OGRE])
        bt._resolve(me, opp, C["diversity"], 5, entry())
        self.assertEqual(opp.life, 14)  # 3 Typen: drei Kopien von 2 Schaden
        self.assertNotIn(SHOCK, me.graveyard)
        self.assertNotIn(C["diversity"], me.graveyard)

    def test_diversity_prefers_draw_over_damage(self):
        me, opp = pair(library=[PLAINS] * 5)
        put(me, ELF_WARRIOR)
        me.graveyard.extend([SHOCK, PEEK])
        bt._resolve(me, opp, C["diversity"], 5, entry())
        self.assertEqual((len(me.hand), opp.life), (2, 20))  # Rang wie bei Modi: Ziehen vor Schaden

    def test_diversity_needs_a_target(self):
        me, opp = pair()
        me.hand = [C["diversity"]]
        self.assertNotIn(C["diversity"], bt.main_phase_spells(me, opp))
        me.graveyard.append(SHOCK)
        self.assertIn(C["diversity"], bt.main_phase_spells(me, opp))


if __name__ == "__main__":
    unittest.main()
