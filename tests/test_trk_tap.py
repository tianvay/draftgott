"""Star Trek (TRK), Paket J (Nutzer 2026-11-01): Tappen und Stun - Tappen (und Stun-Marke) beim Betreten (Vexing Drone,
Enterprise NX-01, Type-2 Phaser), "Whenever ~ becomes tapped" bei jedem Tappen (Shuttle Ace, Sulu, Jett Reno, Beckett
Mariner, Hemmer), Enttappen (DOT-7 Repair Squad, D'Vana Tendi), Tal Shiar Analyst, Marooned, Hemmer (Hexproof fuer
Raumschiffe im eigenen Zug), Species 8472 gegen Faehigkeiten von Artefakten, MACO Strike Team. Nur Kampfmodell."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]
STUN = " (If a permanent with a stun counter would become untapped, remove one from it instead.)"
STATION = ("Station (Tap another creature you control: Put charge counters equal to its power on this Spacecraft. "
           "Station only as a sorcery. It's an artifact creature at 6+.)\n6+ | Flying, vigilance")


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="W"):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)


RAW = {
    "vexing": raw("Vexing Drone", f"Artifact Creature {DASH} Borg", "{1}{W}", 2, "When this creature enters, tap target "
                  "creature an opponent controls.", "2", "2"),
    "nx01": raw("Enterprise NX-01", f"Legendary Artifact {DASH} Spacecraft", "{3}{U}", 4, "When Enterprise NX-01 enters, "
                "tap target creature an opponent controls and put a stun counter on it." + STUN + "\n" + STATION, "4",
                "3", ["Station"], "U"),
    "phaser": raw("Type-2 Phaser", f"Artifact {DASH} Equipment", "{2}", 2, "When this Equipment enters, tap target "
                  "creature an opponent controls and put a stun counter on it." + STUN + "\nEquipped creature gets "
                  "+3/+0.\nEquip {3} ({3}: Attach to target creature you control. Equip only as a sorcery.)",
                  colors=""),
    "ace": raw("Shuttle Ace", f"Creature {DASH} Kelpien Pilot", "{4}{W}", 5, "During your turn, this creature has "
               "flying.\nWhenever this creature becomes tapped, you gain 2 life.", "4", "4"),
    "sulu": raw("Sulu, Space Swashbuckler", f"Legendary Creature {DASH} Human Pilot", "{1}{W}", 2, "First strike\n"
                "Whenever Sulu becomes tapped, if an Equipment or Spacecraft entered the battlefield under your "
                "control this turn, draw a card.", "2", "2", ["First strike"]),
    "jett": raw("Jett Reno, Problem Solver", f"Legendary Creature {DASH} Human Artificer", "{1}{U}", 2, "Whenever Jett "
                "Reno becomes tapped, surveil 1. If her power is 4 or greater, instead draw a card.\nWhenever you face "
                "a dilemma, put a +1/1 counter on Jett Reno. (You face a dilemma as you choose one or more modes for a "
                "spell or ability.)", "1", "2", colors="U"),
    "beckett": raw("Beckett Mariner, Impetuous Ensign", f"Legendary Creature {DASH} Human Officer", "{1}{R}", 2,
                   "First strike\nReckless Behavior — Whenever Beckett Mariner becomes tapped, put a promotion counter "
                   "on her. Then if there are three or more promotion counters on her, remove those counters and she "
                   "deals 2 damage to each opponent.", "2", "1", ["First strike"], "R"),
    "hemmer": raw("Hemmer, Fixing What Is Broken", f"Legendary Creature {DASH} Aenar Artificer", "{W}{U}", 2, "During "
                  "your turn, Spacecraft you control have hexproof. (They can't be the targets of spells or abilities "
                  "your opponents control.)\nWhenever Hemmer becomes tapped, draw a card, then discard a card.", "2",
                  "3", colors="WU"),
    "dot7": raw("DOT-7 Repair Squad", f"Artifact Creature {DASH} Robot", "{3}{W}", 4, "Flying\n{1}{W}: Untap target "
                "creature. Activate only as a sorcery and only once each turn.", "3", "3", ["Flying"]),
    "tendi": raw("D'Vana Tendi, Optimistic Ensign", f"Legendary Creature {DASH} Orion Scientist", "{1}{G/U}{G/U}", 3,
                 "{T}: Untap another target permanent.\n{3}: Surveil 1. (Look at the top card of your library. You may "
                 "put it into your graveyard.)", "2", "4", colors="GU"),
    "analyst": raw("Tal Shiar Analyst", f"Creature {DASH} Romulan Scientist", "{2}{R}", 3, "{T}: This creature deals 1 "
                   "damage to each opponent.\nWhenever you cast a noncreature spell, untap this creature.", "3", "2",
                   colors="R"),
    "marooned": raw("Marooned", f"Enchantment {DASH} Aura", "{U}", 1, "Enchant artifact or creature\nWhen this Aura "
                    "enters, you may pay {3}. If you do, tap enchanted permanent.\nEnchanted permanent doesn't untap "
                    "during its controller's untap step and can't be beamed up.", keywords=["Enchant"], colors="U"),
    "species": raw("Species 8472", f"Creature {DASH} Insect Beast", "{4}{G}{G}", 6, "This creature can't be blocked by "
                   "artifact creatures.\nThis creature can't be the target of abilities from artifact sources your "
                   "opponents control.", "7", "5", colors="G"),
    "maco": raw("MACO Strike Team", f"Creature {DASH} Human Soldier", "{G}", 1, "Whenever a creature you control "
                "becomes the target of a spell or ability an opponent controls, create a tapped 1/1 red Officer "
                "creature token.", "2", "1", colors="G"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}
OGRE = card_info(_card("Ogre", f"Creature {DASH} Ogre", "{2}{R}", 3, "R", "", [], "3", "3"))[0]
GIANT = card_info(_card("Giant", f"Creature {DASH} Giant", "{4}{R}", 5, "R", "", [], "5", "5"))[0]
ELF = card_info(_card("Elf", f"Creature {DASH} Elf", "{G}", 1, "G", "", [], "1", "1"))[0]
GEAR = card_info(_card("Test Blade", f"Artifact {DASH} Equipment", "{1}", 1, "", "Equipped creature gets +1/+0.\n"
                       "Equip {1}"))[0]
KILL = card_info(_card("Test Kill", "Instant", "{1}{B}", 2, "B", "Destroy target creature."))[0]
PEEK = card_info(_card("Test Peek", "Sorcery", "{1}{R}", 2, "R", "Draw a card."))[0]


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
        self.assertEqual((C["vexing"].etb_tap_opp, C["nx01"].etb_tap_opp, C["phaser"].etb_tap_opp), (1, 2, 2))
        self.assertEqual(C["ace"].became_tapped, ("life", 2))
        self.assertEqual(C["sulu"].became_tapped, ("draw_if_gear", 1))
        self.assertEqual(C["jett"].became_tapped, ("surveil_or_draw", 1, 4))
        self.assertEqual(C["jett"].dilemma_trig, (("counter", 1),))
        self.assertEqual(C["beckett"].became_tapped, ("promotion", 3, 2))
        self.assertEqual(C["hemmer"].became_tapped, ("loot",))
        self.assertTrue(C["hemmer"].spacecraft_hexproof)
        self.assertEqual(C["dot7"].untap_ability, (((1, (("W", 1),)),), False))
        self.assertEqual(C["tendi"].untap_ability, (((0, ()),), True))
        self.assertEqual((C["analyst"].tap_ping, C["analyst"].cast_untap), (1, True))
        self.assertEqual((C["marooned"].removal[0], C["marooned"].extra_cost), ("lock", 3))
        self.assertTrue(C["species"].artifact_shroud)
        self.assertEqual(C["maco"].target_token.name, "Officer")

    def test_coverage(self):
        for key, r in RAW.items():
            self.assertEqual([l for _c, _m, l in analyze_card(r)], [], key)


class EnterTapTests(unittest.TestCase):
    def test_vexing_taps_the_blocker(self):
        me, opp = pair()
        giant = put(me, GIANT)
        wall, elf = put(opp, OGRE), put(opp, ELF)
        drone = put(me, C["vexing"], 3)
        bt.creature_enters(me, drone, 3, entry(), opp)
        self.assertTrue(wall.tapped)  # stoppt (ueberlebt nicht, tauscht aber nicht): der gefaehrlichste Blocker
        self.assertEqual((wall.stun, elf.tapped), (0, False))

    def test_vexing_prefers_blocker_over_most_dangerous(self):
        me, opp = pair()
        put(me, GIANT)
        wall = put(opp, card_info(_card("Wall", f"Creature {DASH} Wall", "{1}{W}", 2, "W", "", [], "1", "6"))[0])
        brute = put(opp, card_info(_card("Brute", f"Creature {DASH} Brute", "{3}{R}", 4, "R", "", [], "4", "1"))[0])
        me.now = me.turn_start = 3  # unser Zug, der Riese ist schon laenger da
        drone = put(me, C["vexing"], 3)
        bt.creature_enters(me, drone, 3, entry(), opp)
        self.assertEqual((wall.tapped, brute.tapped), (True, False))  # die Mauer haelt den Riesen auf

    def test_phaser_stuns(self):
        me, opp = pair()
        ogre = put(opp, OGRE)
        me.perms.append(C["phaser"])
        bt.permanent_enters(me, opp, C["phaser"], 3, entry())
        self.assertEqual((ogre.tapped, ogre.stun), (True, 1))

    def test_species_ignores_artifact_sources(self):
        me, opp = pair()
        species, ogre = put(opp, C["species"]), put(opp, OGRE)
        me.perms.append(C["phaser"])
        bt.permanent_enters(me, opp, C["phaser"], 3, entry())
        self.assertEqual((species.tapped, ogre.tapped), (False, True))

    def test_vexing_comes_in_main_one(self):
        me, opp = pair()
        put(me, GIANT)
        put(opp, OGRE)
        self.assertTrue(bt.combat_etb(me, opp, C["vexing"], 3))
        me2, opp2 = pair()
        put(opp2, OGRE)
        self.assertFalse(bt.combat_etb(me2, opp2, C["vexing"], 3))  # kein Angreifer


class BecameTappedTests(unittest.TestCase):
    def test_ace_gains_life_on_attack_tap(self):
        me, opp = pair()
        ace = put(me, C["ace"])
        ace.tapped = True
        bt.bury((me, opp), entry())
        self.assertEqual(me.life, 22)
        ace.tapped = True  # schon getappt: kein neuer Ausloeser
        bt.bury((me, opp), entry())
        self.assertEqual(me.life, 22)

    def test_sulu_needs_gear_this_turn(self):
        me, opp = pair(library=[PLAINS] * 5)
        sulu = put(me, C["sulu"])
        sulu.tapped = True
        bt.bury((me, opp), entry())
        self.assertEqual(len(me.hand), 0)
        sulu.tapped = False
        me.perms.append(GEAR)
        bt.permanent_enters(me, opp, GEAR, me.now, entry())
        sulu.tapped = True
        bt.bury((me, opp), entry())
        self.assertEqual(len(me.hand), 1)

    def test_jett_surveil_or_draw(self):
        me, opp = pair(library=[PLAINS] * 5)
        jett = put(me, C["jett"])
        e = entry()
        jett.tapped = True
        bt.bury((me, opp), e)
        self.assertTrue(any("Surveil" in ev for ev in e["events"]))
        jett.tapped, jett.bonus = False, 3
        jett.tapped = True
        bt.bury((me, opp), entry())
        self.assertEqual(len(me.hand), 1)

    def test_beckett_every_third_tap(self):
        me, opp = pair()
        beckett = put(me, C["beckett"])
        for _ in range(3):
            beckett.tapped = True
            bt.bury((me, opp), entry())
            beckett.tapped = False
        self.assertEqual(opp.life, 18)

    def test_hemmer_loots(self):
        me, opp = pair(library=[PLAINS] * 5)
        me.hand = [GIANT]
        hemmer = put(me, C["hemmer"])
        hemmer.tapped = True
        bt.bury((me, opp), entry())
        self.assertEqual(len(me.hand), 1)
        self.assertEqual(len(me.graveyard), 1)

    def test_attack_taps_trigger(self):
        me, opp = pair()
        put(me, C["ace"], 0)
        bt.take_turn(me, opp, 5, 3, True)
        self.assertGreaterEqual(me.life, 22)


class SpacecraftHexproofTests(unittest.TestCase):
    def test_hemmer_own_turn_only(self):
        me, _opp = pair()
        put(me, C["hemmer"])
        ship = put(me, C["nx01"]._replace(is_creature=True, power=4, toughness=3))
        me.turn_start = me.now
        self.assertTrue(bt.hexproof(ship))
        me.turn_start = me.now - 1
        self.assertFalse(bt.hexproof(ship))


class UntapTests(unittest.TestCase):
    def test_dot7_untaps_best_attacker_in_main_two(self):
        me, opp = pair()
        put(me, C["dot7"])
        giant = put(me, GIANT)
        giant.tapped = True
        put(opp, OGRE)
        me.open = [("W",), ("W",)]
        bt.untap_abilities(me, opp, 5, entry())
        self.assertEqual((giant.tapped, me.open), (False, []))
        giant.tapped = True
        me.open = [("W",), ("W",)]
        bt.untap_abilities(me, opp, 5, entry())
        self.assertTrue(giant.tapped)  # nur einmal je Zug

    def test_tendi_taps_herself(self):
        me, opp = pair()
        tendi, giant = put(me, C["tendi"]), put(me, GIANT)
        me.turn_start = 3  # seit dem letzten eigenen Zug da (302.6)
        giant.tapped = True
        put(opp, OGRE)
        bt.untap_abilities(me, opp, 5, entry())
        self.assertEqual((giant.tapped, tendi.tapped), (False, True))

    def test_no_untap_without_attackers_on_their_side(self):
        me, opp = pair()
        put(me, C["tendi"])
        giant = put(me, GIANT)
        giant.tapped = True
        me.turn_start = 3
        bt.untap_abilities(me, opp, 5, entry())
        self.assertTrue(giant.tapped)


class AnalystTests(unittest.TestCase):
    def test_ping_at_end_of_opponents_turn(self):
        me, opp = pair()
        analyst = put(me, C["analyst"])
        me.turn_start = 3
        bt.tap_pings(me, opp, 5, entry(), own_turn=False)
        self.assertEqual((opp.life, analyst.tapped), (19, True))

    def test_own_turn_only_lethal(self):
        me, opp = pair()
        put(me, C["analyst"])
        me.turn_start = 3
        bt.tap_pings(me, opp, 5, entry(), own_turn=True)
        self.assertEqual(opp.life, 20)
        opp.life = 1
        bt.tap_pings(me, opp, 5, entry(), own_turn=True)
        self.assertEqual(opp.life, 0)

    def test_untap_on_noncreature_spell(self):
        me, opp = pair(library=[PLAINS] * 5)
        analyst = put(me, C["analyst"])
        analyst.tapped = True
        bt.on_cast(me, PEEK, 5, entry())
        self.assertFalse(analyst.tapped)


class MaroonedAndMacoTests(unittest.TestCase):
    def test_marooned_locks(self):
        me, opp = pair()
        ogre = put(opp, OGRE)
        bt.cast_removal(C["marooned"], me, opp, entry(), 5)
        self.assertTrue(ogre.locked)

    def test_maco_token_when_targeted(self):
        me, opp = pair()
        put(me, C["maco"])
        ogre = put(me, OGRE)
        bt.cast_removal(KILL, opp, me, entry(), 5, target=ogre)
        token = next(c for c in me.creatures if c.card.name == "Officer")
        self.assertTrue(token.tapped)


if __name__ == "__main__":
    unittest.main()
