"""Star Trek (TRK), Paket I (Nutzer 2026-11-01): Kartenfluss - oberste Karten ansehen und eine nehmen (Rutherford,
There's Coffee in that Nebula, Spock, Pattern Buffer Preservation), Laender von oben aufs Feld (U.S.S. Voyager, Hit
It!), Suchen nach Kartentyp (Federation Resupply, H.M.S. Bounty), Impulse (Reckless Impulse, Silicate Surveyor),
Opfern und ziehen (Khan, Automated Warfare System), Ersatz beim Ziehen (Mr. Spock, 614.1) und Ausloeser beim Ziehen
(Data), Phlox, Tricorder, Seven of Nine, Live Long and Prosper, Dathon, Dal R'El. Nur Kampfmodell. Kartentexte aus
TRK."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS, ISLAND = W["Plains"], W["Island"]

RAW = {
    "rutherford": _card("Rutherford, Upgraded Ensign", f"Legendary Creature {DASH} Human Artificer", "{2}{W}", 3, "W",
                        "When Rutherford enters, look at the top six cards of your library. You may reveal an artifact "
                        "card from among them and put it into your hand. Put the rest on the bottom of your library in "
                        "a random order.\nWhenever you cast a Spacecraft spell, put a +1/+1 counter on target "
                        "creature.", [], "2", "2"),
    "coffee": _card("There's Coffee in that Nebula", "Sorcery", "{1}{W}", 2, "W", "Look at the top five cards of your "
                    "library. You may reveal a Plains card or nonland permanent card with mana value 3 or less from "
                    "among them and put it into your hand. Put the rest on the bottom in a random order.\nBeam me up "
                    "{2}{W} (You may cast this card from your graveyard for {2}{W} if you also return a creature you "
                    "control to its owner's hand. Then exile this spell.)"),
    "spock": _card("Spock, Always Your Friend", f"Legendary Creature {DASH} Vulcan Human Scientist", "{U}{R}", 2, "UR",
                   "When Spock enters, look at the top four cards of your library. You may reveal a noncreature, "
                   "nonland card from among them and put it into your hand. Put the rest on the bottom of your library "
                   "in any order.", [], "2", "2"),
    "buffer": _card("Pattern Buffer Preservation", "Sorcery", "{1}{B}", 2, "B", "Look at the top two cards of your "
                    "library. Put one of them into your hand and the other into your graveyard.\nBeam me up {1}{B} (You "
                    "may cast this card from your graveyard for {1}{B} if you also return a creature you control to its "
                    "owner's hand. Then exile this spell.)"),
    "hit_it": _card("Hit It!", "Enchantment", "{1}{R}{G}", 3, "RG", "Creatures you control have haste.\nWhen this "
                    "enchantment enters, reveal the top five cards of your library. Put a land card from among them "
                    "onto the battlefield tapped and the rest into your graveyard."),
    "voyager": _card("U.S.S. Voyager, Lone Wanderer", f"Legendary Artifact {DASH} Spacecraft", "{3}{G}", 4, "G",
                     "When U.S.S. Voyager enters, reveal cards from the top of your library until you reveal two land "
                     "cards. Put those land cards onto the battlefield tapped and the rest on the bottom of your "
                     "library in a random order.\nStation (Tap another creature you control: Put charge counters equal "
                     "to its power on this Spacecraft. Station only as a sorcery. It's an artifact creature at 8+.)\n"
                     "8+ | Flying, vigilance", [], "3", "3"),
    "resupply": _card("Federation Resupply", "Sorcery", "{1}{W}", 2, "W", "Search your library for an Aura, Equipment, "
                      "or Spacecraft card, reveal it, put it into your hand, then shuffle.\nBeam me up {3}{W} (You may "
                      "cast this card from your graveyard for {3}{W} if you also return a creature you control to its "
                      "owner's hand. Then exile this spell.)"),
    "bounty": _card("H.M.S. Bounty, Unlikely Timeship", f"Legendary Artifact {DASH} Spacecraft", "{4}{U}", 5, "U",
                    "When H.M.S. Bounty enters, you may search your library for a Whale card, reveal it, put it into "
                    "your hand, then shuffle.\nStation\n8+ | Flying\nWhenever H.M.S. Bounty deals combat damage to a "
                    "player, draw a card. If you control a Whale and haven't begun an extra turn this game, take an "
                    "extra turn after this one.", [], "3", "4"),
    "reckless": _card("Reckless Impulse", "Sorcery", "{1}{R}", 2, "R", "Exile the top two cards of your library. Until "
                      "the end of your next turn, you may play those cards."),
    "silicate": _card("Silicate Surveyor", f"Creature {DASH} Tholian Scout", "{4}{R}", 5, "R", "Reach\nWhen this "
                      "creature enters, exile the top card of your library. Until the end of your next turn, you may "
                      "play that card.", ["Reach"], "4", "4"),
    "khan": _card("Khan, Vengeful Heart", f"Legendary Creature {DASH} Human Warrior", "{2}{B}{B}", 4, "B", "When Khan "
                  "enters, you may sacrifice another creature or artifact. If you do, draw two cards.\nYou may cast "
                  "this card from exile.", [], "5", "3"),
    "aws": _card("Automated Warfare System", f"Artifact Creature {DASH} Construct", "{2}{B}", 3, "B", "Flying\nWhenever "
                 "this creature attacks, you may sacrifice another creature or artifact. If you do, draw a card.",
                 ["Flying"], "2", "2"),
    "mr_spock": _card("Mr. Spock, Science Officer", f"Legendary Creature {DASH} Vulcan Human Scientist", "{2}{U}{U}", 4,
                      "U", "If you would draw a card, draw two cards instead.", [], "2", "4"),
    "data": _card("Data, New Life", f"Legendary Artifact Creature {DASH} Android Scientist", "{1}{U}", 2, "U",
                  "Whenever you draw a card, put a +1/+1 counter on Data.", [], "0", "1"),
    "phlox": _card("Phlox, Unorthodox Doctor", f"Legendary Creature {DASH} Denobulan Doctor", "{2}{G}{W}", 4, "GW",
                   "Trample\nWhenever a creature you control with a counter on it deals combat damage to a player, draw "
                   "a card.", ["Trample"], "3", "4"),
    "tricorder": _card("Tricorder", f"Artifact {DASH} Equipment", "{1}", 1, "", "Equipped creature gets +1/+1.\n"
                       "Whenever equipped creature attacks, surveil 1. (Look at the top card of your library. You may "
                       "put it into your graveyard.)\nEquip {1} ({1}: Attach to target creature you control. Equip only "
                       "as a sorcery.)", ["Equip"]),
    "seven": _card("Seven of Nine, Unassimilated", f"Legendary Artifact Creature {DASH} Human Officer", "{1}{U}", 2, "U",
                   "At the beginning of your first main phase, draw a card. Then discard a card unless you control five "
                   "or more differently named lands.\n{6}{U}: Seven of Nine's base power and toughness become 7/9. "
                   "Activate only if you control seven or more differently named lands.", [], "0", "4"),
    "prosper": _card("Live Long and Prosper", "Sorcery", "{5}{W}{U}", 7, "WU", "This spell can't be countered.\nDouble "
                     "your life total. Draw cards equal to the number of cards in your hand. You have no maximum hand "
                     "size until your next turn."),
    "dathon": _card("Dathon, His Heart Open", f"Legendary Creature {DASH} Tamarian Officer", "{G}{U}{R}", 3, "GUR",
                    "Whenever you cast an enchantment spell, draw a card. If it's a Saga spell, Dathon deals 2 damage "
                    "to each opponent.\n{2}: Choose a counter on target enchantment you control. Put another counter "
                    "of that kind on it. Activate only as a sorcery.", [], "3", "3"),
    "dal": _card("Dal R'El, Augment Orphan", f"Legendary Creature {DASH} Human Mutant Rogue", "{1}{R}{G}", 3, "RG",
                 "Landfall — Whenever a land you control enters, add {R} or {G}.\n{3}, Sacrifice a land: Draw a card.",
                 [], "3", "3"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}
OGRE = card_info(_card("Ogre", f"Creature {DASH} Ogre", "{2}{R}", 3, "R", "", [], "3", "3"))[0]
BIG = card_info(_card("Giant", f"Creature {DASH} Giant", "{4}{R}", 5, "R", "", [], "5", "5"))[0]
ELF = card_info(_card("Elf", f"Creature {DASH} Elf", "{G}", 1, "G", "", [], "1", "1"))[0]
ROCK = card_info(_card("Test Rock", "Artifact", "{2}", 2, "", ""))[0]
PEEK = card_info(_card("Test Peek", "Sorcery", "{1}{U}", 2, "U", "Draw a card."))[0]
WHALE = card_info(_card("Test Whale", f"Creature {DASH} Whale", "{3}{U}", 4, "U", "", [], "4", "4"))[0]
TOKEN = card_info(_card("Officer", f"Token Creature {DASH} Human Officer", "", 0, "R", "", [], "1", "1"))[0]._replace(
    is_token=True)
ENCH = card_info(_card("Test Charm", "Enchantment", "{1}{G}", 2, "G", ""))[0]
SAGA = ENCH._replace(name="Test Saga", saga=(3, ()))
LIFE_LANDFALL = card_info(_card("Test Grazer", f"Creature {DASH} Beast", "{1}{G}", 2, "G", "Landfall — Whenever a "
                                "land you control enters, you gain 1 life.", [], "2", "2"))[0]
NAMED = [card_info(_card(f"Land {i}", "Land", text="{T}: Add {C}.", produced=["C"]))[0] for i in range(5)]


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


def open_lines(key):
    return [l for _c, _m, l in analyze_card(RAW[key])]


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertEqual(C["rutherford"].top_dig, (6, "artifact", False))
        self.assertEqual(C["coffee"].top_dig, (5, "plains_perm3", False))
        self.assertEqual(C["spock"].top_dig, (4, "noncreature_nonland", False))
        self.assertEqual(C["buffer"].top_dig, (2, "any", True))
        self.assertEqual(C["hit_it"].reveal_lands, ("top", 5))
        self.assertEqual(C["voyager"].reveal_lands, ("until", 2))
        self.assertEqual(C["resupply"].tutor, ("aura", "equipment", "spacecraft"))
        self.assertEqual(C["bounty"].tutor, ("whale",))
        self.assertEqual((C["reckless"].impulse, C["silicate"].impulse), (2, 1))
        self.assertEqual((C["khan"].sac_draw, C["aws"].sac_draw), (("etb", 2), ("attack", 1)))
        self.assertTrue(C["mr_spock"].draw_double and C["data"].draw_counter and C["phlox"].counter_hit_draw)
        self.assertEqual(C["tricorder"].equip_attack_surveil, 1)
        self.assertEqual(C["seven"].main1_loot_lands, 5)
        self.assertTrue(C["prosper"].double_life_draw and C["dathon"].enchant_cast_draw)
        self.assertEqual(C["dal"].landfall_mana, ("R", "G"))
        self.assertEqual(C["dal"].draw_abilities[0][1:], (False, "sac_land"))

    def test_coverage(self):
        for key in RAW:
            # Khan seit TRK R4, Seven of Nine (7/9) und Dathon (Marke) seit R6 modelliert (Nutzer 2026-11-05)
            self.assertEqual(open_lines(key), [], key)


class DigTests(unittest.TestCase):
    def test_rutherford_takes_artifact(self):
        lib = [OGRE, PLAINS, ROCK, ELF, PEEK, ISLAND, BIG]
        me, opp = pair(library=lib)
        bt.card_effects(me, opp, C["rutherford"], 3, entry())
        self.assertEqual(me.hand, [ROCK])
        self.assertEqual((me.library[0], len(me.library)), (BIG, 6))
        self.assertEqual(sorted(c.name for c in me.library[1:]), sorted(c.name for c in lib[:6] if c is not ROCK))

    def test_rutherford_no_artifact(self):
        me, opp = pair(library=[OGRE, PLAINS])
        bt.card_effects(me, opp, C["rutherford"], 3, entry())
        self.assertEqual((me.hand, len(me.library)), ([], 2))

    def test_spock_noncreature_nonland(self):
        me, opp = pair(library=[OGRE, PLAINS, PEEK, ELF])
        bt.card_effects(me, opp, C["spock"], 3, entry())
        self.assertEqual(me.hand, [PEEK])

    def test_coffee_filter(self):
        me, opp = pair(library=[BIG, OGRE, PEEK, ELF, ISLAND, PLAINS])
        me.lands, me.hand = [PLAINS] * 3, [PLAINS]
        bt.card_effects(me, opp, C["coffee"], 3, entry())
        self.assertEqual(me.hand, [PLAINS, OGRE])  # Giant zu teuer, Peek keine bleibende Karte
        me, opp = pair(library=[BIG, ISLAND, PLAINS])
        bt.card_effects(me, opp, C["coffee"], 3, entry())
        self.assertEqual(me.hand, [PLAINS])  # Plains-Karte ja, Island nein

    def test_pattern_buffer(self):
        me, opp = pair(library=[OGRE, PEEK, ELF])
        me.lands = [PLAINS] * 3
        bt.card_effects(me, opp, C["buffer"], 3, entry())
        self.assertEqual((me.hand, me.graveyard[-1:], me.library), ([OGRE], [PEEK], [ELF]))


class LandTests(unittest.TestCase):
    def test_hit_it(self):
        me, opp = pair(library=[OGRE, PLAINS, ELF, PEEK, ISLAND, BIG])
        bt.card_effects(me, opp, C["hit_it"], 3, entry())
        self.assertEqual((len(me.lands), me.library), (1, [BIG]))
        self.assertEqual(len([c for c in me.graveyard if c is not C["hit_it"]]), 4)

    def test_voyager(self):
        me, opp = pair(library=[OGRE, PLAINS, ELF, ISLAND, PEEK])
        bt.card_effects(me, opp, C["voyager"], 3, entry())
        self.assertEqual(sorted(l.name for l in me.lands), ["Island", "Plains"])
        self.assertEqual((me.library[0], sorted(c.name for c in me.library[1:])), (PEEK, ["Elf", "Ogre"]))

    def test_revealed_lands_trigger_landfall(self):
        me, opp = pair(library=[OGRE, PLAINS, ISLAND])
        put(me, LIFE_LANDFALL)
        bt.card_effects(me, opp, C["voyager"], 3, entry())
        self.assertEqual(me.life, 22)

    def test_voyager_one_land(self):
        me, opp = pair(library=[OGRE, PLAINS, ELF])
        bt.card_effects(me, opp, C["voyager"], 3, entry())
        self.assertEqual((len(me.lands), len(me.library)), (1, 2))


class TutorImpulseTests(unittest.TestCase):
    def test_resupply(self):
        me, opp = pair(library=[OGRE, C["tricorder"], PLAINS])
        bt.card_effects(me, opp, C["resupply"], 3, entry())
        self.assertEqual((me.hand, len(me.library)), ([C["tricorder"]], 2))

    def test_resupply_spacecraft(self):
        me, opp = pair(library=[OGRE, C["voyager"]])
        bt.card_effects(me, opp, C["resupply"], 3, entry())
        self.assertEqual(me.hand, [C["voyager"]])

    def test_bounty_whale(self):
        me, opp = pair(library=[OGRE, WHALE])
        bt.card_effects(me, opp, C["bounty"], 3, entry())
        self.assertEqual(me.hand, [WHALE])

    def test_impulse(self):
        me, opp = pair(library=[OGRE, ELF, PEEK])
        bt.card_effects(me, opp, C["reckless"], 3, entry())
        self.assertEqual(me.impulse, [(OGRE, me.own_turns + 1), (ELF, me.own_turns + 1)])
        bt.card_effects(me, opp, C["silicate"], 3, entry())
        self.assertEqual(me.impulse[-1], (PEEK, me.own_turns + 1))


class SacrificeTests(unittest.TestCase):
    def test_khan_token(self):
        me, opp = pair()
        tok = put(me, TOKEN)
        put(me, C["khan"])
        bt.card_effects(me, opp, C["khan"], 3, entry())
        self.assertEqual((tok.dead, len(me.hand)), (True, 2))

    def test_khan_keeps_real_creature(self):
        me, opp = pair()
        ogre = put(me, OGRE)
        bt.card_effects(me, opp, C["khan"], 3, entry())
        self.assertEqual((ogre.dead, me.hand), (False, []))

    def test_khan_clue_first(self):
        me, opp = pair()
        tok = put(me, TOKEN)
        me.clues = 1
        bt.card_effects(me, opp, C["khan"], 3, entry())
        self.assertEqual((me.clues, tok.dead, len(me.hand)), (0, False, 2))

    def test_aws_attack(self):
        me, opp = pair()
        aws, tok = put(me, C["aws"]), put(me, TOKEN)
        bt.attack_flow(me, opp, [aws], 3, entry())
        self.assertEqual((tok.dead, len(me.hand)), (True, 1))

    def test_aws_not_attacking_token(self):
        me, opp = pair()
        aws, tok = put(me, C["aws"]), put(me, TOKEN)
        bt.attack_flow(me, opp, [aws, tok], 3, entry())
        self.assertEqual((tok.dead, me.hand), (False, []))


class DrawTests(unittest.TestCase):
    def test_mr_spock(self):
        me, _opp = pair()
        put(me, C["mr_spock"])
        bt._draw(me)
        self.assertEqual(len(me.hand), 2)
        put(me, C["mr_spock"])
        bt._draw(me)
        self.assertEqual(len(me.hand), 6)

    def test_data(self):
        me, _opp = pair()
        data = put(me, C["data"])
        bt._draw(me, 2)
        self.assertEqual(data.bonus, 2)
        put(me, C["mr_spock"])
        bt._draw(me)
        self.assertEqual(data.bonus, 4)

    def test_draw_step(self):
        me, opp = pair(library=[OGRE, ELF, PEEK, PLAINS])
        put(me, C["mr_spock"])
        data = put(me, C["data"])
        e = bt.take_turn(me, opp, 5, 3, skip_draw=False)
        self.assertEqual((e["drew"], data.bonus), ("Ogre", 2))

    def test_data_empty_library(self):
        me, _opp = pair(library=[])
        data = put(me, C["data"])
        bt._draw(me)
        self.assertEqual(data.bonus, 0)

    def test_phlox(self):
        me, _opp = pair()
        put(me, C["phlox"])
        a, b = put(me, OGRE), put(me, ELF)
        a.bonus = 1
        bt.counter_hit_draws(me, [a, b], entry())
        self.assertEqual(len(me.hand), 1)

    def test_tricorder(self):
        me, opp = pair()
        ogre = put(me, OGRE)
        ogre.gear.append(C["tricorder"])
        e = entry()
        bt.attack_flow(me, opp, [ogre], 3, e)
        self.assertTrue(any("Surveil 1" in ev for ev in e["events"]))

    def test_seven(self):
        me, _opp = pair()
        put(me, C["seven"])
        me.hand = [OGRE]
        bt.main1_loot(me, entry())
        self.assertEqual((len(me.hand), len(me.graveyard)), (1, 1))
        me.lands = list(NAMED)
        bt.main1_loot(me, entry())
        self.assertEqual((len(me.hand), len(me.graveyard)), (2, 1))

    def test_prosper(self):
        me, opp = pair()
        me.life, me.hand = 15, [OGRE, ELF, PEEK]
        bt.card_effects(me, opp, C["prosper"], 3, entry())
        self.assertEqual((me.life, len(me.hand), me.no_hand_limit), (30, 6, True))

    def test_dathon(self):
        me, opp = pair()
        put(me, C["dathon"])
        bt.on_cast(me, ENCH, 3, entry())
        self.assertEqual((len(me.hand), opp.life), (1, 20))
        bt.on_cast(me, SAGA, 3, entry())
        self.assertEqual((len(me.hand), opp.life), (2, 18))
        bt.on_cast(me, OGRE, 3, entry())
        self.assertEqual(len(me.hand), 2)

    def test_dal_landfall_mana(self):
        me, opp = pair()
        put(me, C["dal"])
        self.assertEqual(bt.on_land(me, opp, PLAINS, 3, entry()), [("R", "G")])
        self.assertEqual(bt.on_land(me, opp, PLAINS, 3, entry(), with_mana=False), [])

    def test_rutherford_spacecraft_cast(self):
        me, _opp = pair()
        put(me, C["rutherford"])
        ogre = put(me, OGRE)
        bt.on_cast(me, C["voyager"], 3, entry())
        self.assertEqual(sum(c.bonus for c in me.creatures), 1)
        bt.on_cast(me, ROCK, 3, entry())
        self.assertEqual(sum(c.bonus for c in me.creatures), 1)
        self.assertIsNotNone(ogre)


if __name__ == "__main__":
    unittest.main()
