"""Im Spiel: Bibliothek aus dem Arena-Protokoll (Deck beim Spielstart minus bekannte eigene Karten), Ziehchancen,
Removal im Deck; im Draft: Kennzahlen der Picks (Kreaturen, Removal, Kartenfluss); Anzeige im Seitenfenster."""
import json
import math
import pathlib
import tempfile
import unittest

from components import gamestate as gs
from components import livedraft as ld
from components import overlay
from tests.fixtures import CARDS

BOLT = {"name": "Test Bolt", "type_line": "Instant", "colors": ["R"], "mana_cost": "{R}", "cmc": 1,
        "oracle_text": "Test Bolt deals 3 damage to any target."}
DRAW = dict(CARDS["Test Spell"])
ALL = dict(CARDS, **{"Test Bolt": BOLT})
NAMES = {101: {"name": "Test Bear", "set": "TST", "number": "10"},
         102: {"name": "Test Hasty", "set": "TST", "number": "11"},
         103: {"name": "Test Spell", "set": "TST", "number": "15"},
         104: {"name": "Test Bolt", "set": "TST", "number": "16"},
         301: {"name": "Plains", "set": "TST", "number": "1"},
         302: {"name": "Mountain", "set": "TST", "number": "4"}}
# 20 Karten: 4 Bear, 2 Hasty, 2 Spell, 2 Bolt, 6 Plains, 4 Mountain
DECK = [101] * 4 + [102] * 2 + [103] * 2 + [104] * 2 + [301] * 6 + [302] * 4


def gre(*messages):
    return "[UnityCrossThreadLogger]1.1.2026 10:00:00: Match to ME: GreToClientEvent\n" + json.dumps(
        {"transactionId": "t", "greToClientEvent": {"greToClientMessages": list(messages)}})


def connect(seat=2, deck=DECK):
    return {"type": "GREMessageType_ConnectResp", "systemSeatIds": [seat],
            "connectResp": {"status": "ConnectionStatus_Success", "deckMessage": {"deckCards": list(deck)}}}


def state(kind="GameStateType_Diff", zones=(), objects=(), deleted=(), stage=None, turn=None, seat=2):
    g = {"type": kind, "gameStateId": 1, "zones": list(zones), "gameObjects": list(objects)}
    if deleted:
        g["diffDeletedInstanceIds"] = list(deleted)
    if stage:
        g["gameInfo"] = {"matchID": "m1", "gameNumber": 1, "stage": stage}
    if turn:
        g["turnInfo"] = {"turnNumber": turn}
    return {"type": "GREMessageType_GameStateMessage", "systemSeatIds": [seat], "gameStateMessage": g}


def zone(zid, ztype, owner=None, ids=()):
    z = {"zoneId": zid, "type": ztype, "visibility": "Visibility_Public"}
    if owner:
        z["ownerSeatId"] = owner
    if ids:
        z["objectInstanceIds"] = list(ids)
    return z


def obj(iid, grp, zid, owner=2):
    return {"instanceId": iid, "grpId": grp, "type": "GameObjectType_Card", "zoneId": zid, "ownerSeatId": owner}


HAND = [(1, 101), (2, 101), (3, 104), (4, 301), (5, 301), (6, 302), (7, 103)]
START = [gre(connect()),
         gre(state("GameStateType_Full", stage="GameStage_Play", turn=1, zones=[
             zone(28, "ZoneType_Battlefield"), zone(30, "ZoneType_Limbo"),
             zone(35, "ZoneType_Hand", 2, [i for i, _ in HAND]), zone(36, "ZoneType_Library", 2, range(100, 113)),
             zone(37, "ZoneType_Graveyard", 2), zone(31, "ZoneType_Hand", 1, [50, 51]),
             zone(32, "ZoneType_Library", 1, range(200, 230))],
             objects=[obj(i, g, 35) for i, g in HAND] + [obj(50, 999, 31, owner=1)]))]
# Land gespielt (neue Kennung 8 auf dem Feld, 4 geloescht), Bolt in den Friedhof (Kennung 9), eine Karte gezogen
PLAY = gre(state(turn=3, zones=[zone(28, "ZoneType_Battlefield", None, [8]),
                                zone(35, "ZoneType_Hand", 2, [1, 2, 5, 6, 7, 10]),
                                zone(36, "ZoneType_Library", 2, range(101, 113)),
                                zone(37, "ZoneType_Graveyard", 2, [9]), zone(30, "ZoneType_Limbo", None, [3, 4])],
                   objects=[obj(8, 301, 28), obj(9, 104, 37), obj(10, 102, 35), obj(3, 104, 30), obj(4, 301, 30)],
                   deleted=[3, 4]))


def feed(game, *lines):
    for chunk in lines:
        for line in chunk.split("\n"):
            game.feed_line(line)
    return game


class OddsTests(unittest.TestCase):
    def test_at_least_one(self):
        self.assertAlmostEqual(gs.at_least_one(11, 33, 1), 1 / 3)
        self.assertAlmostEqual(gs.at_least_one(11, 33, 3), 1 - math.comb(22, 3) / math.comb(33, 3))
        self.assertEqual(gs.at_least_one(0, 33, 3), 0)
        self.assertEqual(gs.at_least_one(5, 0, 1), 0)
        self.assertEqual(gs.at_least_one(5, 3, 9), 1)  # mehr Zuege als Karten

    def test_percent_text(self):
        self.assertEqual(gs.pct(0.4149), "41 %")
        self.assertEqual(gs.pct(0.004), "< 1 %")
        self.assertEqual(gs.pct(0), "0 %")


class StateTests(unittest.TestCase):
    def test_start_of_game(self):
        g = feed(gs.GameState(), *START)
        self.assertTrue(g.active)
        self.assertEqual(g.seat, 2)
        lib, remaining = g.library()
        self.assertEqual(lib, 13)
        self.assertEqual(remaining, {101: 2, 102: 2, 103: 1, 104: 1, 301: 4, 302: 3})  # 20 - 7 auf der Hand

    def test_cards_move_and_old_ids_are_dropped(self):
        g = feed(gs.GameState(), *START, PLAY)
        lib, remaining = g.library()
        self.assertEqual(lib, 12)
        self.assertEqual(remaining, {101: 2, 102: 1, 103: 1, 104: 1, 301: 4, 302: 3})  # Limbo zaehlt nicht
        self.assertEqual(g.turn, 3)

    def test_doubles_deleted_objects_and_opponent_cards_do_not_count(self):
        extra = gre(state(zones=[zone(30, "ZoneType_Limbo", None, [11]),  # Doppel im Limbo
                                 zone(28, "ZoneType_Battlefield", None, [12]),  # gleiche Karte beim Gegner
                                 zone(37, "ZoneType_Graveyard", 2, [13])],
                          objects=[obj(11, 101, 30), obj(12, 101, 28, owner=1), obj(13, 102, 37)], deleted=[13]))
        g = feed(gs.GameState(), *START, extra)
        self.assertEqual(g.library()[1], {101: 2, 102: 2, 103: 1, 104: 1, 301: 4, 302: 3})

    def test_full_state_replaces_everything(self):
        g = feed(gs.GameState(), *START, PLAY)
        again = gre(state("GameStateType_Full", zones=[zone(35, "ZoneType_Hand", 2, [1]),
                                                       zone(36, "ZoneType_Library", 2, range(100, 119))],
                          objects=[obj(1, 101, 35)]))
        feed(g, again)
        self.assertEqual(g.library(), (19, {101: 3, 102: 2, 103: 2, 104: 2, 301: 6, 302: 4}))

    def test_game_over_and_next_game(self):
        g = feed(gs.GameState(), *START, gre(state(stage="GameStage_GameOver")))
        self.assertFalse(g.active)
        feed(g, *START)
        self.assertTrue(g.active)
        self.assertEqual(g.library()[0], 13)

    def test_other_lines_and_unknown_deck(self):
        g = feed(gs.GameState(), "nichts", '{"greToClientEvent": "kaputt"}')
        self.assertFalse(g.active)
        g = feed(gs.GameState(), START[1])  # Zustand ohne Deck (Protokoll erst mitten im Spiel)
        self.assertEqual(g.library(), (13, {}))


def info():
    return {grp: ld.card_summary(ALL.get(i["name"]), i["name"], i["set"], i["number"]) for grp, i in NAMES.items()}


class ViewTests(unittest.TestCase):
    def test_view_of_the_library(self):
        v = gs.game_view(feed(gs.GameState(), *START), info())
        self.assertEqual((v["library"], v["hand"], v["deck"], v["turn"]), (13, 7, 20, 1))
        by = {r["key"]: r for r in v["groups"]}
        self.assertEqual(by["land"]["n"], 7)
        self.assertAlmostEqual(by["land"]["next"], 7 / 13)
        self.assertAlmostEqual(by["land"]["in3"], gs.at_least_one(7, 13, 3))
        self.assertEqual(by["creature"]["n"], 4)
        self.assertEqual(by["removal"]["n"], 1)
        self.assertEqual(by["src_W"]["n"], 4)
        self.assertEqual(by["src_R"]["n"], 3)
        self.assertNotIn("src_U", by)
        self.assertEqual(v["removal"]["left"], 1)
        self.assertEqual(v["removal"]["total"], 2)
        self.assertGreater(v["removal"]["points_total"], v["removal"]["points_left"])
        bear = next(c for c in v["cards"] if c["name"] == "Test Bear")
        self.assertEqual((bear["n"], bear["deck"]), (2, 4))
        self.assertAlmostEqual(bear["next"], 2 / 13)
        self.assertEqual([c["name"] for c in v["cards"]],  # Nichtlaender nach Anzahl, Removal, Name; dann Laender
                         ["Test Bear", "Test Hasty", "Test Bolt", "Test Spell", "Plains", "Mountain"])
        self.assertTrue(v["consistent"])

    def test_inactive(self):
        self.assertEqual(gs.game_view(gs.GameState(), info()), {"active": False})


class DraftInfoTests(unittest.TestCase):
    def test_pool_numbers(self):
        cards = [ld.card_summary(ALL[n], n) for n in ("Test Bear", "Test Bear", "Test Hasty", "Test Spell",
                                                      "Test Bolt", "Plains")]
        i = ld.pool_info(cards, None)
        self.assertEqual((i["cards"], i["creatures"], i["removal"], i["flow"]), (6, 3, 1, 1))
        self.assertGreater(i["removal_points"], 0)
        self.assertEqual(i["flow_kinds"], {"draw": 1})
        self.assertIsNone(i["arch"])
        i = ld.pool_info(cards, "RW")
        self.assertEqual((i["arch"]["cards"], i["arch"]["creatures"]), (6, 3))
        i = ld.pool_info(cards, "UB")  # nur farblose bzw. passende Karten
        self.assertEqual((i["arch"]["cards"], i["arch"]["creatures"], i["arch"]["removal"]), (1, 0, 0))

    def test_card_summary_has_removal_and_flow(self):
        bolt = ld.card_summary(BOLT, "Test Bolt")
        self.assertGreater(bolt["removal"], 0)
        self.assertFalse(bolt["creature"])
        self.assertEqual(ld.card_summary(DRAW, "Test Spell")["flow"], ["draw"])
        self.assertEqual(ld.card_summary(CARDS["Plains"], "Plains")["produces"], ["W"])
        self.assertTrue(ld.card_summary(CARDS["Test Bear"], "Test Bear")["creature"])


class LiveTests(unittest.TestCase):
    def test_snapshot_has_game_and_draft_info(self):
        with tempfile.TemporaryDirectory() as d:
            log = pathlib.Path(d) / "Player.log"
            pack = '[UnityCrossThreadLogger]Draft.Notify {"draftId":"d1","SelfPick":1,"SelfPack":1,"PackCards":"104,101"}'
            pick = "[UnityCrossThreadLogger]==> Event_PlayerDraftMakePick " + json.dumps(
                {"id": "x", "request": json.dumps({"DraftId": "d1", "GrpIds": [104], "Pack": 1, "Pick": 1})})
            log.write_text("\n".join([pack, pick] + START) + "\n", encoding="utf-8")
            live = ld.LiveDraft(log, pathlib.Path(d) / "pool.txt", names=NAMES, fetch=lambda n, refresh=False: ALL)
            live.step()
            snap = live.snapshot({}, {}, None)
            self.assertTrue(snap["game"]["active"])
            self.assertEqual(snap["game"]["library"], 13)
            self.assertEqual(snap["draftinfo"]["removal"], 1)
            self.assertEqual(snap["draftinfo"]["cards"], 1)


class OverlayTests(unittest.TestCase):
    def test_game_rows(self):
        snap = {"status": "waiting", "game": gs.game_view(feed(gs.GameState(), *START), info())}
        rows = overlay.rows_for(snap)
        text = "\n".join(r[0] for r in rows)
        self.assertIn("Bibliothek 13", text)
        self.assertIn("Land", text)
        self.assertIn("54 %", text)  # 7 von 13 Laendern im naechsten Zug
        self.assertIn("Removal", text)
        self.assertIn("Test Bolt", text)

    def test_draft_info_row(self):
        snap = {"status": "pack", "pick": 2, "detect": {"main": None, "scores": []}, "pack": [],
                "draftinfo": {"cards": 6, "creatures": 3, "removal": 1, "removal_points": 1.5, "flow": 1,
                              "flow_kinds": {"draw": 1}, "arch": None}}
        text = "\n".join(r[0] for r in overlay.rows_for(snap))
        self.assertIn("Kreaturen 3", text)
        self.assertIn("Removal 1", text)
        self.assertIn("Kartenfluss 1", text)

    def test_removal_points_in_pack_rows(self):
        snap = {"status": "pack", "pick": 1, "detect": {"main": None, "scores": []},
                "pack": [{"name": "Test Bolt", "level": "", "rating": "", "colors": ["R"], "arch": [], "points": 1.5,
                          "removal": 2.0}]}
        self.assertIn("R2", overlay.rows_for(snap)[-1][0])


class TextTests(unittest.TestCase):
    def test_help_and_readme(self):
        from components.howitworks import render_help_page
        page = render_help_page()
        self.assertIn("Ziehchancen", page)
        self.assertIn("Kennzahlen der Picks", page)
        readme = (pathlib.Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
        self.assertIn("Ziehchancen", readme)


class PageTests(unittest.TestCase):
    def test_page_has_game_and_info_panels(self):
        from components.drafthelper import render_page
        page = render_page()
        self.assertIn('id="lgame"', page)
        self.assertIn('id="linfo"', page)


if __name__ == "__main__":
    unittest.main()
