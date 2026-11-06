"""Star Trek (TRK): Sagas (714). Beim Betreten eine Lore-Marke (Kapitel I), nach jedem eigenen Draw Step eine weitere
(714.3b); nach dem letzten Kapitel wird die Saga geopfert (714.4). Jedes Kapitel wird wie ein kleiner Zauber gelesen
(Removal, Ziehen, Leben, Token, Zurueckholen ...), dazu eigene Bausteine fuer TRK: Investigate (Clue-Token: {2},
opfern: ziehen - am Ende des gegnerischen Zugs mit offenem Mana), Edikte "nontoken", Exil von der Hand, "each player
draws/loses", Opfern fuer Token. City I, Inner Light II, Scientists III und die Kontrollübernahme von The Wrath of
Khan I seit 2026-11-06 modelliert (tests/test_trk_rest.py). Nur Kampfmodell. Kartentexte aus TRK."""
import unittest

from components import battle as bt
from components.cards import card_info, token_card
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
SAGA = f"Enchantment {DASH} Saga"
PLAINS, BEAR = W["Plains"], W["Test Bear"]
LORE = "(As this Saga enters and after your draw step, add a lore counter. Sacrifice after {n}.)\n"


def raw(name, cost, cmc, chapters, final="III", colors="W"):
    return _card(name, SAGA, cost, cmc, colors, LORE.format(n=final) + chapters)


RAW = {
    "measure": raw("The Measure of a Man", "{2}{W}", 3, "I — Exile up to one target nontoken artifact or creature.\n"
                   "II — Investigate. (Create a Clue token. It's an artifact with \"{2}, Sacrifice this token: Draw a "
                   "card.\")\nIII — Return the exiled card to the battlefield under its owner's control. You gain 2 "
                   "life."),
    "scientists": raw("Those Old Scientists", "{2}{U}", 3, "I — Draw two cards, then discard two cards.\nII — Return up "
                      "to one target artifact, instant, or sorcery card from your graveyard to your hand.\nIII — Choose "
                      "up to two target cards in graveyards. The owners of those cards shuffle them into their "
                      "libraries.", colors="U"),
    "moonlight": raw("In the Pale Moonlight", "{3}{B}{B}", 5, "I — Each opponent sacrifices a nontoken creature of their "
                     "choice.\nII — Investigate. (Create a Clue token. It's an artifact with \"{2}, Sacrifice this "
                     "token: Draw a card.\")\nIII — You may sacrifice an artifact or creature. If you do, create two 2/2 "
                     "black Romulan creature tokens.", colors="B"),
    "khan": raw("The Wrath of Khan", "{2}{R}", 3, "I — This Saga deals 4 damage to target creature an opponent controls. "
                "At the beginning of the next combat this turn, gain control of that creature until end of turn. Untap "
                "it. It gains haste until end of turn.\nII — You may exile a card from your hand. If you do, draw a "
                "card.\nIII — Each opponent sacrifices a nontoken permanent of their choice.", colors="R"),
    "amok": raw("Amok Time", "{2}{G}", 3, "I — Target creature you control fights up to one target creature an opponent "
                "controls.\nII — You gain 3 life.\nIII — Return target creature card from your graveyard to your hand.",
                colors="G"),
    "goodthings": raw("All Good Things...", "{3}{G}{U}", 5, "I, II, III — Draw two cards, then exile a card from your "
                      "hand.\nIV — If all cards exiled with this Saga share a card type, you gain 10 life.", "IV", "GU"),
    "city": raw("The City on the Edge of Forever", "{3}{W}{B}", 5, "I — All artifacts and creatures phase out. Create a "
                "0/1 white Human creature token with \"Permanents can't phase in.\" (Treat phased-out permanents and "
                "anything attached to them as though they don't exist.)\nII — You draw two cards and each player loses "
                "2 life.\nIII — Sacrifice a creature token. If you do, you gain 5 life.", colors="WB"),
    "innerlight": raw("The Inner Light", "{3}{G}{W}", 5, "I — Return target green or white creature card from your "
                      "graveyard to the battlefield.\nII — Choose target creature. Whenever it deals combat damage to a "
                      "player this turn, you draw that many cards.\nIII — You gain life equal to the greatest power "
                      "among creatures you control. Create a Treasure token.", colors="GW"),
    "hell": raw("Year of Hell", "{1}{U}{R}", 3, "I, II, III — Each player draws a card. This Saga deals 2 damage to each "
                "player.", colors="UR"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}
OGRE = card_info(_card("Ogre", f"Creature {DASH} Ogre", "{2}{R}", 3, "R", "", [], "3", "3"))[0]
ELF = card_info(_card("Elf", f"Creature {DASH} Elf", "{3}{G}", 4, "G", "", [], "4", "4"))[0]
PEEK = card_info(_card("Test Peek", "Sorcery", "{1}{U}", 2, "U", "Draw a card."))[0]
CADET = token_card("Cadet", True, 1, 1, False)


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [BEAR] * 20)
    return p


def pair(library=None):
    me, opp = player(library=library), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": [], "land": ""}


def on_board(p, card, step=0):
    c = bt.Creature(card, step)
    c.ctl, c.gy = p, p.graveyard
    p.creatures.append(c)
    return c


def enter(me, opp, key):
    bt._resolve(me, opp, C[key], 5, entry())


def lore(me, opp, step=6):
    bt.saga_after_draw(me, opp, step, entry())


class ParseTests(unittest.TestCase):
    def test_final_chapter(self):
        self.assertEqual(C["hell"].saga[0], 3)
        self.assertEqual(C["goodthings"].saga[0], 4)
        self.assertEqual([ch for ch, _s, _a in C["hell"].saga[1]], [(1, 2, 3)])

    def test_chapter_as_spell(self):
        sub = C["khan"].saga[1][0][1]
        self.assertEqual(sub.removal[:2], ("damage", 4))

    def test_on_purpose_chapters_missing(self):
        self.assertEqual([ch for ch, _s, _a in C["city"].saga[1]], [(1,), (2,), (3,)])  # Nutzer 2026-11-06
        self.assertEqual([ch for ch, _s, _a in C["innerlight"].saga[1]], [(1,), (2,), (3,)])

    def test_not_a_saga(self):
        self.assertEqual((BEAR.saga, PEEK.saga), ((), ()))

    def test_coverage(self):
        open_ = {k: [l for _c, _m, l in analyze_card(r)] for k, r in RAW.items()}
        for key in ("measure", "moonlight", "amok", "goodthings", "hell", "khan", "city", "innerlight", "scientists"):
            self.assertEqual(open_[key], [], key)  # City I, Inner Light II, Scientists III: coverage.ON_PURPOSE

    def test_coverage_reminder_with_line_break(self):
        broken = dict(RAW["scientists"], oracle_text=RAW["scientists"]["oracle_text"].replace(
            "after your draw step", "after your draw\nstep"))  # so steht es bei Scryfall
        self.assertEqual(analyze_card(broken), [])
        self.assertEqual(card_info(broken)[0].saga, C["scientists"].saga)


class LoreTests(unittest.TestCase):
    def test_chapters_and_sacrifice(self):
        me, opp = pair()
        enter(me, opp, "hell")
        self.assertEqual((len(me.hand), len(opp.hand), me.life, opp.life), (1, 1, 18, 18))
        lore(me, opp)
        lore(me, opp)
        self.assertEqual((me.life, opp.life, len(me.hand)), (14, 14, 3))
        self.assertNotIn(C["hell"], me.perms)
        self.assertIn(C["hell"], me.graveyard)
        lore(me, opp)  # geopfert: kein weiteres Kapitel
        self.assertEqual(me.life, 14)

    def test_lore_in_the_turn(self):
        me, opp = pair()
        enter(me, opp, "hell")
        bt.take_turn(me, opp, 7, 2, skip_draw=True)  # nach dem Draw Step: Kapitel II
        self.assertEqual((me.life, opp.life), (16, 16))

    def test_destroyed_saga_stops(self):
        me, opp = pair()
        enter(me, opp, "hell")
        me.perms.remove(C["hell"])
        lore(me, opp)
        self.assertEqual(me.life, 18)


class ChapterTests(unittest.TestCase):
    def test_moonlight(self):
        me, opp = pair()
        on_board(opp, CADET)
        on_board(opp, OGRE)
        bear = on_board(opp, BEAR)
        enter(me, opp, "moonlight")
        self.assertNotIn(bear, opp.creatures)  # schwaechste Nicht-Token-Kreatur
        self.assertEqual(len(opp.creatures), 2)
        lore(me, opp)
        self.assertEqual(me.clues, 1)
        lore(me, opp)  # III: opfert den Clue fuer zwei Romulans
        self.assertEqual((me.clues, [c.card.name for c in me.creatures]), (0, ["Romulan", "Romulan"]))

    def test_moonlight_keeps_a_big_creature(self):
        me, opp = pair()
        elf = on_board(me, ELF)
        enter(me, opp, "moonlight")
        lore(me, opp)
        me.clues = 0
        lore(me, opp)
        self.assertEqual([c.card.name for c in me.creatures], ["Elf"])
        self.assertIs(me.creatures[0], elf)

    def test_clue_at_end_step(self):
        me, _opp = pair()
        me.clues, me.open = 2, [("W",)] * 3
        bt.use_clues(me, entry())
        self.assertEqual((me.clues, len(me.hand), len(me.open)), (1, 1, 1))

    def test_clue_is_an_artifact(self):
        me, _opp = pair()
        me.clues = 2
        self.assertEqual(bt.artifact_count(me), 2)

    def test_khan(self):
        me, opp = pair()
        on_board(opp, OGRE)
        enter(me, opp, "khan")
        self.assertEqual(opp.creatures, [])
        me.hand = [PLAINS] * 5 + [OGRE]
        me.lands = [PLAINS] * 4
        lore(me, opp)  # II: ueberzaehliges Land ins Exil, ziehen
        self.assertEqual((me.hand.count(PLAINS), len(me.hand)), (4, 6))
        bear = on_board(opp, BEAR)
        lore(me, opp)  # III: Gegner opfert sein schwaechstes Nicht-Token-Permanent
        self.assertNotIn(bear, opp.creatures)

    def test_khan_edict_land_when_rich(self):
        me, opp = pair()
        enter(me, opp, "khan")
        lore(me, opp)
        opp.lands = [PLAINS] * 6
        bear = on_board(opp, BEAR)
        lore(me, opp)
        self.assertEqual((len(opp.lands), bear in opp.creatures), (5, True))

    def test_amok(self):
        me, opp = pair()
        on_board(me, OGRE)
        bear = on_board(opp, BEAR)
        enter(me, opp, "amok")
        self.assertNotIn(bear, opp.creatures)
        lore(me, opp)
        self.assertEqual(me.life, 23)
        me.graveyard.append(ELF)
        lore(me, opp)
        self.assertIn(ELF, me.hand)

    def test_good_things(self):
        me, opp = pair(library=[PLAINS] * 20)
        enter(me, opp, "goodthings")
        lore(me, opp)
        lore(me, opp)
        self.assertEqual(len(me.hand), 3)  # dreimal zwei gezogen, eine ins Exil
        lore(me, opp)  # IV: alle exilierten Karten sind Laender
        self.assertEqual(me.life, 30)
        self.assertIn(C["goodthings"], me.graveyard)

    def test_good_things_mixed_types(self):
        me, opp = pair()
        st = {"card": C["goodthings"], "lore": 3, "exiled": [PLAINS, BEAR], "temp": None}
        bt.saga_atom(me, opp, st, ("share_life", 10), 5, entry())
        self.assertEqual(me.life, 20)
        st["exiled"] = [OGRE, BEAR]  # beide Kreaturen
        bt.saga_atom(me, opp, st, ("share_life", 10), 5, entry())
        self.assertEqual(me.life, 30)

    def test_city(self):
        me, opp = pair()
        enter(me, opp, "city")
        self.assertEqual([c.card.name for c in me.creatures], ["Human"])  # Kapitel I: Phasing (Nutzer 2026-11-06)
        self.assertTrue(me.creatures[0].card.phase_lock)
        lore(me, opp)
        self.assertEqual((len(me.hand), me.life, opp.life), (2, 18, 18))
        on_board(me, CADET)
        lore(me, opp)
        self.assertEqual(([c.card.name for c in me.creatures], me.life), (["Cadet"], 23))  # der Human geht

    def test_inner_light(self):
        me, opp = pair()
        me.graveyard = [ELF, OGRE]
        enter(me, opp, "innerlight")
        self.assertEqual([c.card.name for c in me.creatures], ["Elf"])  # nur gruen oder weiss
        lore(me, opp)
        lore(me, opp)
        self.assertEqual((me.life, me.treasures), (24, 1))

    def test_scientists(self):
        me, opp = pair(library=[PLAINS] * 20)
        me.hand = [BEAR]
        enter(me, opp, "scientists")
        self.assertEqual(len(me.hand), 1)
        me.graveyard.append(PEEK)
        lore(me, opp)
        self.assertIn(PEEK, me.hand)

    def test_measure(self):
        me, opp = pair()
        ogre = on_board(opp, OGRE)
        enter(me, opp, "measure")
        self.assertEqual(opp.creatures, [])
        lore(me, opp)
        self.assertEqual(me.clues, 1)
        lore(me, opp)
        self.assertEqual(([c.card for c in opp.creatures], me.life), ([OGRE], 22))
        self.assertIsNot(opp.creatures[0], ogre)  # neues Objekt (400.7)


if __name__ == "__main__":
    unittest.main()
