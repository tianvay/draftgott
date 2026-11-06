"""Star Trek (TRK), Restpaket (Nutzer 2026-11-06): die bisher bewusst ausgelassenen Zeilen. The Wrath of Khan I
(ueberlebt das Ziel die 4 Schaden, wird es bis Rundenende uebernommen, enttappt, mit Haste), The City on the Edge of
Forever I (Phasing 702.26 aller Artefakte und Kreaturen, solange der Human-Token lebt; nur, wenn der Gegner klar vorne
liegt), The Inner Light II (Ziehen in Hoehe des Kampfschadens), Those Old Scientists III (gegnerische Karten mit
Friedhofs-Nutzen in die Bibliothek), Ensign Pavel Chekov (Gegner exiliert X, ein Land davon spielbar), Branching
Timeline (Permanents von oben getappt ins Spiel), Captain Benjamin Sisko (Gratiszauber aus den obersten fuenf),
Gwyndala (Equipment-Token wird Kopie einer besseren Ausruestung), Lwaxana Troi (Angriffs- und Kampfschaden-Ausloeser
einer anderen Kreatur doppelt, bleibt getappt). Nur Kampfmodell. Kartentexte aus TRK."""
import unittest

from components import battle as bt
from components.cards import card_info, cost_alternatives
from components.coverage import ON_PURPOSE, analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
SAGA = f"Enchantment {DASH} Saga"
PLAINS, ISLAND, BEAR, BIG = W["Plains"], W["Island"], W["Test Bear"], W["Test Big"]
LORE = "(As this Saga enters and after your draw step, add a lore counter. Sacrifice after III.)\n"


def saga(name, cost, cmc, chapters, colors="W"):
    return _card(name, SAGA, cost, cmc, colors, LORE + chapters)


RAW = {
    "khan": saga("The Wrath of Khan", "{2}{R}", 3, "I — This Saga deals 4 damage to target creature an opponent "
                 "controls. At the beginning of the next combat this turn, gain control of that creature until end of "
                 "turn. Untap it. It gains haste until end of turn.\nII — You may exile a card from your hand. If you "
                 "do, draw a card.\nIII — Each opponent sacrifices a nontoken permanent of their choice.", "R"),
    "city": saga("The City on the Edge of Forever", "{3}{W}{B}", 5, "I — All artifacts and creatures phase out. Create "
                 "a 0/1 white Human creature token with \"Permanents can't phase in.\" (Treat phased-out permanents and "
                 "anything attached to them as though they don't exist.)\nII — You draw two cards and each player loses "
                 "2 life.\nIII — Sacrifice a creature token. If you do, you gain 5 life.", "WB"),
    "innerlight": saga("The Inner Light", "{3}{G}{W}", 5, "I — Return target green or white creature card from your "
                       "graveyard to the battlefield.\nII — Choose target creature. Whenever it deals combat damage to "
                       "a player this turn, you draw that many cards.\nIII — You gain life equal to the greatest power "
                       "among creatures you control. Create a Treasure token.", "GW"),
    "scientists": saga("Those Old Scientists", "{2}{U}", 3, "I — Draw two cards, then discard two cards.\nII — Return "
                       "up to one target artifact, instant, or sorcery card from your graveyard to your hand.\nIII — "
                       "Choose up to two target cards in graveyards. The owners of those cards shuffle them into their "
                       "libraries.", "U"),
    "chekov": _card("Ensign Pavel Chekov", f"Legendary Creature {DASH} Human Pilot", "{3}{U}", 4, "U", "Strange new "
                    "worlds — When Ensign Chekov enters, each opponent exiles the top X cards of their library, where X "
                    "is the number of differently named lands you control. For each opponent, choose a land card that "
                    "player owns exiled this way. You may play the chosen cards for as long as they remain exiled.", [],
                    "1", "5"),
    "branching": _card("Branching Timeline", "Sorcery", "{6}{G}{G}", 8, "G", "Strange new worlds — Reveal the top X "
                       "cards of your library, where X is the number of differently named lands you control. Put all "
                       "permanent cards revealed this way onto the battlefield tapped and the rest on the bottom of your "
                       "library in a random order."),
    "sisko": _card("Captain Benjamin Sisko", f"Legendary Creature {DASH} Human Officer", "{1}{W}", 2, "W", "At the "
                   "beginning of your end step, create a 1/1 red Officer creature token for each dilemma you've faced "
                   "this turn.\n{2}{W}{U}{B}{R}{G}, {T}: Exile the top five cards of your library. You may cast any "
                   "number of spells with mana value less than or equal to the number of Officers you control from "
                   "among those cards without paying their mana costs.", [], "2", "2"),
    "gwyndala": _card("Gwyndala, the Progeny", f"Legendary Creature {DASH} Vau-N'Akat Advisor", "{1}{U}", 2, "U", "When "
                      "Gwyndala enters, create a colorless Equipment artifact token named Neuroflux Heirloom with "
                      "\"Equipped creature gets +1/+1\" and equip {2}. Attach it to Gwyndala.\n{2}: Each Equipment token "
                      "you control becomes a copy of target Equipment you control until end of turn.", [], "1", "1"),
    "lwaxana": _card("Lwaxana Troi, Charming Guest", f"Legendary Creature {DASH} Betazoid Advisor", "{1}{R}", 2, "R",
                     "You may choose not to untap Lwaxana Troi during your untap step.\n{2}, {T}: Choose another target "
                     "creature you control. For as long as Lwaxana Troi remains tapped, if a triggered ability of that "
                     "creature triggers, that ability triggers an additional time.", [], "2", "2"),
    "axe": _card("Test Axe", f"Artifact {DASH} Equipment", "{2}", 2, "", "Equipped creature gets +3/+0.\nEquip {3}"),
    "dagger": _card("Test Dagger", f"Artifact {DASH} Equipment", "{1}", 1, "", "Equipped creature gets +1/+0.\nEquip {1}"),
    "scout": _card("Test Scout", f"Creature {DASH} Human Scout", "{1}{U}", 2, "U", "Whenever this creature deals combat "
                   "damage to a player, draw a card.", [], "1", "1"),
    "officer": _card("Test Officer", f"Creature {DASH} Human Officer", "{R}", 1, "R", "", [], "1", "1"),
    "relic": _card("Test Relic", "Artifact", "{2}", 2, "", "{T}: You gain 1 life."),
    "rerun": _card("Test Rerun", "Sorcery", "{1}{W}", 2, "W", "Draw a card.\nFlashback {3}{W}"),
    "peek": _card("Test Peek", "Sorcery", "{1}{U}", 2, "U", "Draw a card."),
    "ogre": _card("Ogre", f"Creature {DASH} Ogre", "{2}{R}", 3, "R", "", [], "3", "3"),
    "elf": _card("Elf", f"Creature {DASH} Elf", "{3}{G}", 4, "G", "", [], "4", "4"),
    "wall": _card("Test Wall", f"Creature {DASH} Wall", "{1}{W}", 2, "W", "", [], "0", "6"),
    "giant": _card("Test Giant", f"Creature {DASH} Giant", "{4}{R}", 5, "R", "", [], "5", "5"),
    "bird": _card("Test Bird", f"Creature {DASH} Bird", "{1}{W}", 2, "W", "Flying", ["Flying"], "1", "1"),
    "mountain": _card("Mountain", f"Basic Land {DASH} Mountain", text="({T}: Add {R}.)", produced=["R"]),
    "forest": _card("Forest", f"Basic Land {DASH} Forest", text="({T}: Add {G}.)", produced=["G"]),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}
ANY = ("W", "U", "B", "R", "G")


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [BEAR] * 20)
    return p


def pair(library=None, opp_library=None):
    me, opp = player(library=library), player("Gegner", opp_library)
    me.opponent, opp.opponent = opp, me
    return me, opp


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": [], "land": ""}


def on_board(p, card, step=0):
    c = bt.Creature(card, step)
    c.ctl, c.gy = p, p.graveyard
    p.creatures.append(c)
    return c


def enter(me, opp, key, step=5):
    bt._resolve(me, opp, C[key], step, entry())


def lore(me, opp, step=6):
    bt.saga_after_draw(me, opp, step, entry())


def names(p):
    return sorted(c.card.name for c in p.creatures if not c.dead)


class ParseTests(unittest.TestCase):
    def test_saga_chapters_complete(self):
        self.assertEqual([ch for ch, _s, _a in C["city"].saga[1]], [(1,), (2,), (3,)])
        self.assertEqual([ch for ch, _s, _a in C["innerlight"].saga[1]], [(1,), (2,), (3,)])
        self.assertEqual([ch for ch, _s, _a in C["scientists"].saga[1]], [(1,), (2,), (3,)])

    def test_khan_keeps_damage_and_steals(self):
        nums, sub, atoms = C["khan"].saga[1][0]
        self.assertEqual((nums, sub.removal[:2], atoms), ((1,), ("damage", 4), (("steal",),)))

    def test_snw(self):
        self.assertIn(("chekov",), C["chekov"].snw)
        self.assertIn(("branching",), C["branching"].snw)

    def test_abilities(self):
        self.assertEqual(C["sisko"].sisko_dig, cost_alternatives("{2}{W}{U}{B}{R}{G}"))
        self.assertEqual(C["gwyndala"].gwyndala_copy, ((2, ()),))
        self.assertEqual(C["lwaxana"].lwaxana_echo, ((2, ()),))
        self.assertEqual(C["scout"].combat_draw, 1)

    def test_coverage(self):
        for key in ("khan", "city", "innerlight", "scientists", "chekov", "branching", "sisko", "gwyndala", "lwaxana"):
            self.assertEqual([l for _c, _m, l in analyze_card(RAW[key])], [], key)

    def test_no_longer_on_purpose(self):
        for name in ("Lwaxana Troi, Charming Guest", "Gwyndala, the Progeny", "Captain Benjamin Sisko",
                     "Ensign Pavel Chekov", "Branching Timeline", "The City on the Edge of Forever", "The Inner Light",
                     "Those Old Scientists"):
            self.assertNotIn(name, ON_PURPOSE)


class KhanTests(unittest.TestCase):
    def test_kills_when_possible(self):
        me, opp = pair()
        on_board(opp, C["ogre"])
        enter(me, opp, "khan")
        self.assertEqual((opp.creatures, me.stolen), ([], []))

    def test_steals_survivor(self):
        me, opp = pair()
        giant = on_board(opp, C["giant"])
        giant.tapped = True
        enter(me, opp, "khan")
        self.assertIn(giant, me.creatures)
        self.assertNotIn(giant, opp.creatures)
        self.assertEqual((giant.damage, giant.tapped, giant.has("haste"), me.stolen), (4, False, True, [giant]))
        bt.end_step_triggers(me, opp, entry())  # Rundenende: zurueck
        self.assertIn(giant, opp.creatures)
        self.assertNotIn(giant, me.creatures)


class CityTests(unittest.TestCase):
    def setUp(self):
        self.me, self.opp = pair()
        self.bear = on_board(self.me, BEAR)
        self.ogre = on_board(self.opp, C["ogre"])
        self.giant = on_board(self.opp, C["giant"])
        self.opp.perms.append(C["relic"])

    def test_phase_out(self):
        enter(self.me, self.opp, "city")
        self.assertEqual((names(self.me), names(self.opp), self.opp.perms), (["Human"], [], []))
        human = self.me.creatures[0]
        self.assertTrue(human.card.phase_lock)
        self.assertFalse(bt.can_block(human, self.ogre))

    def test_phase_in_when_token_dies(self):
        enter(self.me, self.opp, "city")
        self.bear.bonus = 1
        self.me.creatures[0].dead = True
        bt.bury((self.me, self.opp), entry())
        self.assertEqual(self.me.creatures, [self.bear])  # dasselbe Objekt (702.26d), kein neues Betreten
        self.assertEqual(self.opp.creatures, [self.ogre, self.giant])
        self.assertEqual(self.opp.perms, [C["relic"]])

    def test_cast_only_when_behind(self):
        self.me.hand = [C["city"]]
        self.assertIn(C["city"], bt.main_phase_spells(self.me, self.opp))
        on_board(self.me, C["elf"])
        on_board(self.me, C["giant"])
        self.assertNotIn(C["city"], bt.main_phase_spells(self.me, self.opp))

    def test_chapter_three_keeps_lock_with_other_token(self):
        enter(self.me, self.opp, "city")
        lore(self.me, self.opp)
        bt.make_tokens(self.me, [(1, BEAR._replace(name="Romulan", is_token=True))], 6, entry())
        lore(self.me, self.opp, 7)  # III: opfert den Romulan, der Gegner bleibt ausgephast
        self.assertEqual(names(self.me), ["Human"])
        self.assertEqual(self.opp.creatures, [])

    def test_chapter_three_only_lock_token(self):
        enter(self.me, self.opp, "city")
        lore(self.me, self.opp)
        lore(self.me, self.opp, 7)  # III: der Human ist der einzige Token: Pflicht, alles phast ein
        self.assertEqual(self.me.creatures, [self.bear])
        self.assertEqual(len(self.opp.creatures), 2)


class InnerLightTests(unittest.TestCase):
    def test_target_prefers_unblockable(self):
        me, opp = pair()
        on_board(me, C["elf"])
        bird = on_board(me, C["bird"])
        on_board(opp, C["wall"])
        st = {"card": C["innerlight"], "lore": 1, "exiled": [], "temp": None}
        me.perms.append(C["innerlight"])
        me.sagas.append(st)
        lore(me, opp, 7)
        self.assertEqual(bird.light, 7)

    def test_draws_combat_damage(self):
        me, opp = pair()
        on_board(me, BIG)
        st = {"card": C["innerlight"], "lore": 1, "exiled": [], "temp": None}
        me.perms.append(C["innerlight"])
        me.sagas.append(st)
        bt.take_turn(me, opp, 7, 2, skip_draw=True)
        self.assertEqual((opp.life, len(me.hand)), (15, 5))


class ScientistsTests(unittest.TestCase):
    def test_shuffles_graveyard_value(self):
        me, opp = pair()
        opp.graveyard = [BEAR, C["rerun"]]
        st = {"card": C["scientists"], "lore": 2, "exiled": [], "temp": None}
        me.perms.append(C["scientists"])
        me.sagas.append(st)
        lore(me, opp)
        self.assertEqual(opp.graveyard, [BEAR])
        self.assertEqual((len(opp.library), opp.library.count(C["rerun"])), (21, 1))

    def test_nothing_worth_it(self):
        me, opp = pair()
        opp.graveyard = [BEAR]
        me.graveyard = [C["ogre"]]
        st = {"card": C["scientists"], "lore": 2, "exiled": [], "temp": None}
        me.perms.append(C["scientists"])
        me.sagas.append(st)
        lore(me, opp)
        self.assertEqual((opp.graveyard, me.graveyard[0], len(opp.library)), ([BEAR], C["ogre"], 20))


class ChekovTests(unittest.TestCase):
    def test_exile_and_play_land(self):
        me, opp = pair(opp_library=[BEAR, ISLAND, C["mountain"], BEAR] + [BEAR] * 10)
        me.lands = [PLAINS, ISLAND, C["forest"]]  # X = 3
        new = on_board(me, C["chekov"], 5)
        bt.creature_enters(me, new, 5, entry(), opp, cast=True)
        self.assertEqual(len(opp.library), 11)
        self.assertEqual([c for c, _l in me.impulse], [C["mountain"]])  # neue Farbe vor bekanntem Namen
        bt.take_turn(me, opp, 7, 2, skip_draw=True)
        self.assertIn(C["mountain"], me.lands)
        self.assertEqual(me.impulse, [])

    def test_stays_playable(self):
        me, opp = pair(opp_library=[C["mountain"]] + [BEAR] * 10)
        me.lands = [PLAINS]
        new = on_board(me, C["chekov"], 5)
        bt.creature_enters(me, new, 5, entry(), opp, cast=True)
        bt.expire_impulse(me)
        me.own_turns += 5
        bt.expire_impulse(me)
        self.assertEqual([c for c, _l in me.impulse], [C["mountain"]])


class BranchingTests(unittest.TestCase):
    def test_permanents_tapped(self):
        me, opp = pair(library=[BEAR, C["peek"], C["forest"], C["ogre"]] + [ISLAND] * 5)
        me.lands = [PLAINS, ISLAND, C["mountain"]]  # X = 3
        enter(me, opp, "branching")
        self.assertEqual(names(me), ["Test Bear"])
        self.assertTrue(me.creatures[0].tapped)
        self.assertIn(C["forest"], me.lands)
        self.assertEqual(me.library[0], C["ogre"])
        self.assertEqual(me.library[-1], C["peek"])


class SiskoTests(unittest.TestCase):
    def setUp(self):
        self.me, self.opp = pair(library=[C["ogre"], BEAR, C["peek"], PLAINS, C["elf"], C["giant"]])
        self.sisko = on_board(self.me, C["sisko"])
        self.me.open = [ANY] * 7
        self.me.turn_start = 5  # Sisko seit Beginn des Zugs unter unserer Kontrolle (302.6)

    def test_free_spells(self):
        on_board(self.me, C["officer"])
        bt.sisko_dig(self.me, self.opp, 5, entry())
        self.assertTrue(self.sisko.tapped)
        self.assertEqual(names(self.me), ["Captain Benjamin Sisko", "Test Bear", "Test Officer"])
        self.assertEqual(self.me.hand, [C["giant"]])  # Test Peek zieht den Giant
        self.assertIn(C["peek"], self.me.graveyard)
        self.assertEqual(self.me.library, [])
        self.assertEqual(self.me.open, [])

    def test_needs_two_officers(self):
        bt.sisko_dig(self.me, self.opp, 5, entry())
        self.assertFalse(self.sisko.tapped)
        self.assertEqual(len(self.me.library), 6)

    def test_needs_five_colors(self):
        on_board(self.me, C["officer"])
        self.me.open = [("W",)] * 7
        bt.sisko_dig(self.me, self.opp, 5, entry())
        self.assertFalse(self.sisko.tapped)


class GwyndalaTests(unittest.TestCase):
    def setUp(self):
        self.me, self.opp = pair()
        on_board(self.me, C["gwyndala"])
        self.bear = on_board(self.me, BEAR)
        self.heirloom = C["gwyndala"].equip_token[0]
        self.me.perms.append(self.heirloom)
        self.bear.gear.append(self.heirloom)
        self.me.open = [("U",)] * 2

    def test_copies_better_equipment(self):
        self.me.perms.append(C["axe"])
        bt.gwyndala_copy(self.me, 5, entry())
        self.assertEqual((self.bear.power, self.bear.toughness, self.me.open), (5, 2, []))
        bt.cleanup((self.me, self.opp))
        self.assertEqual((self.bear.power, self.bear.toughness), (3, 3))
        self.assertIn(self.heirloom, self.me.perms)

    def test_keeps_better_token(self):
        self.me.perms.append(C["dagger"])
        bt.gwyndala_copy(self.me, 5, entry())
        self.assertEqual((self.bear.power, len(self.me.open)), (3, 2))


class LwaxanaTests(unittest.TestCase):
    def test_doubles_combat_draw(self):
        me, opp = pair(library=[BIG] * 20)
        me.lands = [PLAINS] * 2
        lwax = on_board(me, C["lwaxana"])
        scout = on_board(me, C["scout"])
        bt.take_turn(me, opp, 7, 2, skip_draw=True)
        self.assertTrue(lwax.tapped)
        self.assertTrue(scout.echo)
        self.assertEqual(len(me.hand), 2)

    def test_stays_tapped_while_target_lives(self):
        me, opp = pair(library=[BIG] * 20)
        me.lands = [PLAINS] * 2
        lwax = on_board(me, C["lwaxana"])
        scout = on_board(me, C["scout"])
        bt.take_turn(me, opp, 7, 2, skip_draw=True)
        bt.take_turn(me, opp, 9, 3, skip_draw=True)
        self.assertTrue(lwax.tapped)
        self.assertEqual(len(me.hand), 4)
        scout.dead = True
        bt.bury((me, opp), entry())
        on_board(opp, BIG)  # damit Lwaxana nicht angreift
        bt.take_turn(me, opp, 11, 4, skip_draw=True)  # Ziel tot: enttappt und sucht ein neues Ziel (keins da)
        self.assertFalse(lwax.tapped)
        self.assertEqual(me.lwax, [])

    def test_no_target_no_activation(self):
        me, opp = pair()
        me.lands = [PLAINS] * 2
        lwax = on_board(me, C["lwaxana"])
        on_board(me, BEAR)
        bt.lwaxana_echo(me, 7, entry())
        self.assertFalse(lwax.tapped)


if __name__ == "__main__":
    unittest.main()
