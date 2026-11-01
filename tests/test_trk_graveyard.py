"""Star Trek (TRK), Paket H (Nutzer 2026-11-01): Sterben und Friedhof - Ausloeser, wenn Kreaturen sterben (Excalbian
Gamemaster, Battle-Scarred Survivalist, Gowron, Grand Nagus Zek, Sarcophagus), wenn Karten den eigenen Friedhof
verlassen (Blastoneuron, Sela, Hologram Stalker, Vash), Wirken aus dem Friedhof mit Finality-Marke (Storied Veteran,
Overflow Submatrix), U.S.S. Reliant, Faehigkeiten aus dem Friedhof (Relentless Drednok, Photosynthetic Physician,
Daniels), Cybernetic Specialist, Sylvia Tilly, Temporal Conqueror. Nur Kampfmodell. Kartentexte aus TRK."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]
SWAMP = card_info(_card("Swamp", f"Basic Land {DASH} Swamp", text="({T}: Add {B}.)", produced=["B"]))[0]
FINALITY = " (If a creature with a finality counter on it would die, exile it instead.)"


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="B"):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)


RAW = {
    "excalbian": raw("Excalbian Gamemaster", f"Creature {DASH} Excalbian", "{5}{W}", 6, "Whenever this creature or "
                     "another creature you control dies, put a +1/+1 counter on target creature you control.", "6", "6",
                     colors="W"),
    "survivalist": raw("Battle-Scarred Survivalist", f"Creature {DASH} Klingon Scout", "{1}{B}", 2, "Menace\nWhenever "
                       "another creature dies, put a +1/+1 counter on this creature. This ability triggers only once "
                       "each turn.", "1", "1", ["Menace"]),
    "gowron": raw("Gowron, Eager for Battle", f"Legendary Creature {DASH} Klingon Warrior", "{2}{B}{R}", 4, "Whenever "
                  "another creature dies, put a +1/+1 counter on Gowron.\nSacrifice another creature: Gowron gains "
                  "trample until end of turn. If you sacrificed a Klingon this way, you draw a card and lose 1 life.",
                  "3", "3", colors="BR"),
    "zek": raw("Grand Nagus Zek", f"Legendary Creature {DASH} Ferengi Noble", "{2}{B}", 3, "Grand Nagus Zek gets +1/+1 "
               "for each Treasure you control.\nWhenever another creature dies, create a Treasure token. This ability "
               "triggers only once each turn. (It's an artifact with \"{T}, Sacrifice this token: Add one mana of any "
               "color.\")", "1", "1"),
    "sarcophagus": raw("Sarcophagus, Ship of the Dead", f"Legendary Artifact {DASH} Spacecraft", "{2}{R}", 3, "Other "
                       "creatures you control get +1/+0.\nWhenever a creature dies, if Sarcophagus isn't a creature, "
                       "put a charge counter on it.\nStation (Tap another creature you control: Put charge counters "
                       "equal to its power on this Spacecraft. Station only as a sorcery. It's an artifact creature "
                       "at 10+.)\n10+ | Flying", "4", "4", ["Station"], "R"),
    "blastoneuron": raw("Blastoneuron", f"Creature {DASH} Jellyfish Leech", "{3}{B}", 4, "Flying\nWhenever one or more "
                        "cards leave your graveyard, each opponent loses 1 life and you gain 1 life.", "2", "2",
                        ["Flying"]),
    "sela": raw("Sela, Tal Shiar Paradox", f"Legendary Creature {DASH} Romulan Human Rogue", "{3}{B}", 4, "Whenever one "
                "or more cards leave your graveyard, create a tapped 2/2 black Romulan creature token.", "3", "3"),
    "stalker": raw("Hologram Stalker", f"Creature {DASH} Hirogen Warrior", "{4}{G}{G}", 6, "Whenever a card leaves your "
                   "graveyard, create a 3/3 colorless Illusion artifact creature token. This ability triggers only "
                   "once each turn.", "2", "2", colors="G"),
    "vash": raw("Vash, Freelance Archaeologist", f"Legendary Creature {DASH} Human Rogue Scientist", "{1}{B}{G}", 3,
                "At the beginning of your upkeep, surveil 1. (Look at the top card of your library. You may put it "
                "into your graveyard.)\nWhenever a card leaves your graveyard, draw a card. This ability triggers only "
                "once each turn.", "2", "4", colors="BG"),
    "veteran": raw("Storied Veteran", f"Creature {DASH} Klingon Advisor", "{B}", 1, "This creature can't block.\nYou may "
                   "cast this card from your graveyard. If you do, it enters with a finality counter on it.", "2", "1"),
    "overflow": raw("Overflow Submatrix", f"Artifact Creature {DASH} Borg", "{2}{B}", 3, "Once during each of your "
                    "turns, you may cast an artifact creature spell from your graveyard. If you cast a spell this way, "
                    "that artifact creature enters with a finality counter on it." + FINALITY, "3", "3"),
    "reliant": raw("U.S.S. Reliant, From Hell's Heart", f"Legendary Artifact {DASH} Spacecraft", "{2}{B}{B}", 4,
                   "Whenever U.S.S. Reliant enters or deals combat damage to a player, return target creature card "
                   "with mana value 4 or less from your graveyard to the battlefield with a finality counter on it.\n"
                   "Station (Tap another creature you control: Put charge counters equal to its power on this "
                   "Spacecraft. Station only as a sorcery. It's an artifact creature at 10+.)\n10+ | Flying", "4", "3",
                   ["Station"]),
    "drednok": raw("Relentless Drednok", f"Artifact Creature {DASH} Robot", "{B}", 1, "Lifelink\n{2}{B}, Exile this "
                   "card from your graveyard: You draw a card and lose 1 life.", "1", "1", ["Lifelink"]),
    "physician": raw("Photosynthetic Physician", f"Creature {DASH} Plant Doctor", "{4}{G}", 5, "Reach\n{G}, Exile this "
                     "card from your graveyard: Create a 1/1 red Officer creature token. Activate only as a sorcery.",
                     "5", "5", ["Reach"], "G"),
    "daniels": raw("Daniels, Temporal Agent", f"Legendary Creature {DASH} Human Advisor", "{2}{B/G}{B/G}", 4, "When "
                   "Daniels enters, return target creature card from your graveyard to your hand.\n{2}, Put this card "
                   "from your graveyard on the bottom of your library: You gain 2 life.", "3", "1", colors="BG"),
    "specialist": raw("Cybernetic Specialist", f"Artifact Creature {DASH} Human Scientist", "{2}", 2, "When this "
                      "creature enters, surveil 1. (Look at the top card of your library. You may put it into your "
                      "graveyard.)\n{1}, {T}: Put target card from your graveyard on the bottom of your library.", "2",
                      "1", ["Surveil"], ""),
    "tilly": raw("Sylvia Tilly, Joy of Discovery", f"Legendary Creature {DASH} Human Scientist Artificer", "{2}{G}", 3,
                 "When Sylvia Tilly enters, surveil 2. (Look at the top two cards of your library, then put any number "
                 "of them into your graveyard and the rest on top of your library in any order.)\nAt the beginning of "
                 "combat on your turn, you may pay {1} and exile a card from your graveyard. When you do, put a +1/+1 "
                 "counter on target creature.", "2", "2", colors="G"),
    "conqueror": raw("Temporal Conqueror", f"Creature {DASH} Na'kuhl Warrior", "{2}{G}", 3, "When this creature enters, "
                     "mill three cards. Then return a land card from your graveyard to your hand. If you can't, create "
                     "a Treasure token. (To mill three cards, put the top three cards from your library into your "
                     "graveyard.)", "2", "3", colors="G"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}
OGRE = card_info(_card("Ogre", f"Creature {DASH} Ogre", "{2}{R}", 3, "R", "", [], "3", "3"))[0]
ELF = card_info(_card("Elf", f"Creature {DASH} Elf", "{G}", 1, "G", "", [], "1", "1"))[0]
GOLEM = card_info(_card("Golem", f"Artifact Creature {DASH} Golem", "{3}", 3, "", "", [], "3", "3"))[0]
BIG_GOLEM = card_info(_card("Big Golem", f"Artifact Creature {DASH} Golem", "{6}", 6, "", "", [], "6", "6"))[0]
PEEK = card_info(_card("Test Peek", "Sorcery", "{1}{B}", 2, "B", "Draw a card."))[0]


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
    def test_death_watchers(self):
        self.assertEqual(C["excalbian"].death_ally_counter, 1)
        self.assertEqual(C["survivalist"].death_watch_counter, (1, True))
        self.assertEqual(C["gowron"].death_watch_counter, (1, False))
        self.assertEqual((C["zek"].death_watch_treasure, C["zek"].treasure_pump), (True, True))
        self.assertTrue(C["sarcophagus"].death_charge)

    def test_graveyard_leave(self):
        self.assertEqual(C["blastoneuron"].gy_leave, ("drain", 1, False))
        kind, token, once = C["sela"].gy_leave
        self.assertEqual((kind, token.name, token.power, once), ("tapped_token", "Romulan", 2, False))
        kind, token, once = C["stalker"].gy_leave
        self.assertEqual((kind, token.name, token.is_artifact, once), ("token", "Illusion", True, True))
        self.assertEqual(C["vash"].gy_leave, ("draw", 1, True))
        self.assertEqual(C["vash"].upkeep_surveil, 1)

    def test_graveyard_casting_and_abilities(self):
        self.assertTrue(C["veteran"].gy_cast)
        self.assertTrue(C["overflow"].overflow_cast)
        self.assertEqual(C["reliant"].reliant_return, 4)
        self.assertEqual((C["drednok"].gy_draw, C["drednok"].gy_draw_loss), ((((2, (("B", 1),)),), 1), 1))
        self.assertTrue(C["physician"].gy_ability_sorcery)
        self.assertEqual(C["physician"].gy_ability[1][0][0], "token")
        self.assertEqual(C["daniels"].gy_bottom_life, (((2, ()),), 2))
        self.assertEqual(C["specialist"].gy_bottom_ability, ((1, ()),))
        self.assertEqual((C["tilly"].surveil, C["tilly"].combat_exile_counter), (2, ((1, ()),)))
        self.assertEqual(C["conqueror"].etb_mill_land, 3)

    def test_coverage(self):
        for key, r in RAW.items():
            open_lines = [l for _c, _m, l in analyze_card(r)]
            if key == "gowron":
                open_lines = [l for l in open_lines if not l.startswith("Sacrifice another creature")]
            self.assertEqual(open_lines, [], key)


class DeathTests(unittest.TestCase):
    def test_excalbian_counts_itself(self):
        me, opp = pair()
        ex, ogre, elf = put(me, C["excalbian"]), put(me, OGRE), put(me, ELF)
        ex.dead = elf.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual(ogre.bonus, 2)

    def test_survivalist_once_per_turn(self):
        me, opp = pair()
        sv = put(me, C["survivalist"])
        a, b = put(opp, ELF), put(opp, ELF)
        a.dead = b.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual(sv.bonus, 1)
        c = put(opp, ELF)
        c.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual(sv.bonus, 1)  # schon in diesem Zug
        me.now = opp.now = 1
        d = put(opp, ELF)
        d.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual(sv.bonus, 2)

    def test_gowron_each_death(self):
        me, opp = pair()
        gow = put(me, C["gowron"])
        a, b = put(opp, ELF), put(me, ELF)
        a.dead = b.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual(gow.bonus, 2)

    def test_zek_treasure_and_size(self):
        me, opp = pair()
        zek = put(me, C["zek"])
        a, b = put(opp, ELF), put(opp, ELF)
        a.dead = b.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual((me.treasures, zek.power, zek.toughness), (1, 2, 2))
        c = put(opp, ELF)
        c.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual(me.treasures, 1)  # einmal je Zug

    def test_sarcophagus_charge(self):
        me, opp = pair()
        me.perms.append(C["sarcophagus"])
        bt.permanent_enters(me, opp, C["sarcophagus"], 3, entry())
        a = put(opp, ELF)
        a.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual(me.stations[0]["charge"], 1)


class LeaveGraveyardTests(unittest.TestCase):
    def test_blastoneuron_once_per_event(self):
        me, opp = pair()
        put(me, C["blastoneuron"])
        me.graveyard.extend([ELF, OGRE])
        me.graveyard.remove(ELF)
        me.graveyard.remove(OGRE)
        bt.bury((me, opp), entry())
        self.assertEqual((me.life, opp.life), (21, 19))
        bt.bury((me, opp), entry())
        self.assertEqual(opp.life, 19)  # nichts Neues

    def test_opponents_graveyard_does_not_count(self):
        me, opp = pair()
        put(me, C["blastoneuron"])
        opp.graveyard.append(ELF)
        opp.graveyard.remove(ELF)
        bt.bury((me, opp), entry())
        self.assertEqual(opp.life, 20)

    def test_sela_tapped_token(self):
        me, opp = pair()
        put(me, C["sela"])
        me.graveyard.append(ELF)
        me.graveyard.pop()
        bt.bury((me, opp), entry())
        token = next(c for c in me.creatures if c.card.name == "Romulan")
        self.assertTrue(token.tapped)

    def test_stalker_and_vash_once_per_turn(self):
        me, opp = pair(library=[PLAINS] * 5)
        put(me, C["stalker"]), put(me, C["vash"])
        for _ in range(2):
            me.graveyard.append(ELF)
            me.graveyard.remove(ELF)
            bt.bury((me, opp), entry())
        self.assertEqual(([c.card.name for c in me.creatures].count("Illusion"), len(me.hand)), (1, 1))

    def test_vash_upkeep_surveil(self):
        me, opp = pair(library=[PLAINS] * 5)
        put(me, C["vash"])
        e = entry()
        bt.upkeep_triggers(me, opp, 3, e)
        self.assertTrue(any("Surveil" in ev for ev in e["events"]))


class GraveyardCastTests(unittest.TestCase):
    def test_veteran_from_graveyard_with_finality(self):
        me, opp = pair()
        me.graveyard.append(C["veteran"])
        cands = bt.graveyard_casts(me)
        self.assertEqual(len(cands), 1)
        cheap, orig = cands[0]
        self.assertTrue(cheap.from_gy)
        self.assertIs(orig, C["veteran"])
        me.graveyard.remove(orig)
        bt._resolve(me, opp, orig, 3, entry(), to_exile=True)
        vet = me.creatures[0]
        self.assertTrue(vet.finality)
        vet.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual(me.graveyard, [])  # exiliert statt zu sterben

    def test_overflow_one_artifact_creature(self):
        me, opp = pair()
        put(me, C["overflow"])
        me.graveyard.extend([GOLEM, BIG_GOLEM, OGRE])
        cands = bt.graveyard_casts(me)
        self.assertEqual([o.name for _c, o in cands], ["Big Golem"])
        me.overflow_used = me.now
        self.assertEqual(bt.graveyard_casts(me), [])

    def test_veteran_cast_in_turn(self):
        me, opp = pair()
        me.lands = [SWAMP, SWAMP]
        me.graveyard.append(C["veteran"])
        bt.take_turn(me, opp, 3, 3, True)
        self.assertTrue(any(c.card.name == "Storied Veteran" and c.finality for c in me.creatures))

    def test_reliant_returns_with_finality(self):
        me, opp = pair()
        me.graveyard.extend([ELF, OGRE, BIG_GOLEM])
        me.perms.append(C["reliant"])
        bt.permanent_enters(me, opp, C["reliant"], 3, entry())
        back = next(c for c in me.creatures if c.card.name == "Ogre")  # teuerste mit Manawert <= 4
        self.assertTrue(back.finality)


class GraveyardAbilityTests(unittest.TestCase):
    def test_drednok_draws_at_end_of_opponents_turn(self):
        me, opp = pair(library=[PLAINS] * 5)
        me.graveyard.append(C["drednok"])
        me.open = [("B",)] * 3
        bt.gy_draws(me, entry())
        self.assertEqual((len(me.hand), me.life, me.graveyard), (1, 19, []))

    def test_drednok_not_at_low_life(self):
        me, opp = pair(library=[PLAINS] * 5)
        me.graveyard.append(C["drednok"])
        me.open = [("B",)] * 3
        me.life = 6
        bt.gy_draws(me, entry())
        self.assertEqual((len(me.hand), me.life), (0, 6))

    def test_daniels_to_bottom(self):
        me, opp = pair(library=[PLAINS] * 5)
        me.graveyard.append(C["daniels"])
        me.open = [("B",)] * 2
        bt.gy_bottom_abilities(me, opp, entry())
        self.assertEqual((me.life, me.library[-1], me.graveyard), (22, C["daniels"], []))

    def test_specialist_only_with_leave_trigger(self):
        me, opp = pair(library=[PLAINS] * 5)
        spec = put(me, C["specialist"])
        me.graveyard.append(ELF)
        me.open = [("B",)]
        bt.gy_bottom_abilities(me, opp, entry())
        self.assertEqual(me.graveyard, [ELF])
        put(me, C["vash"])
        bt.gy_bottom_abilities(me, opp, entry())
        bt.bury((me, opp), entry())
        self.assertEqual((me.graveyard, spec.tapped, len(me.hand)), ([], True, 1))

    def test_tilly_exiles_least_useful_card(self):
        me, opp = pair()
        put(me, C["tilly"])
        ogre = put(me, OGRE)
        me.graveyard.extend([C["drednok"], PLAINS])
        me.open = [("G",)]
        bt.combat_exile_counters(me, 3, entry())
        self.assertEqual((me.graveyard, ogre.bonus), ([C["drednok"]], 1))

    def test_conqueror_land_or_treasure(self):
        me, opp = pair(library=[OGRE, PLAINS, ELF, PLAINS])
        bt.creature_enters(me, put(me, C["conqueror"]), 3, entry(), opp)
        self.assertEqual((me.hand, me.treasures), ([PLAINS], 0))
        me2, opp2 = pair(library=[OGRE, ELF, OGRE])
        bt.creature_enters(me2, put(me2, C["conqueror"]), 3, entry(), opp2)
        self.assertEqual((me2.hand, me2.treasures), ([], 1))


if __name__ == "__main__":
    unittest.main()
