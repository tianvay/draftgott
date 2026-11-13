"""Ende eines Drafts: Gegnerdeck erst beim Hoechststand an Siegen (Pick Two 4, normaler Draft 7, Traditional 3),
Meldung nur im eigenen Draft (der naechste Draft beginnt ohne Reste), Spielstatistik aus dem Arena-Protokoll
(Karten gezogen, Schaden, Zauber, ...) als Draft-Bilanz."""
import json
import pathlib
import tempfile
import unittest

from components import draftstats as ds
from components import overlay
from tests.test_draftstats import auth_line, deck_line, end_line, lookup, notify, pick, start_line
from tests.test_enemy_autosave import DECK, DRAFT, INFO, stamp

QUICK = "QuickDraft_TRK_20261113"


def played(results, start=1, event=QUICK):
    lines = []
    for i, win in enumerate(results, start):
        lines += [start_line(f"m{i}", event=event), stamp(),
                  end_line(f"m{i}", [2 if win else 1], 2 if win else 1)]
    return lines


def quick_draft():
    """Normaler Draft (Bots): Picks mit Draft-Kennung, Deck im Event QuickDraft."""
    return DRAFT + [deck_line([(101, 1), (103, 1), (105, 1), (102, 1), (201, 9)], [(104, 1)], event=QUICK)]


class MaxWinsTests(unittest.TestCase):
    def test_by_event(self):
        self.assertEqual(ds.max_wins("PickTwoDraft_TRK_20261110"), 4)
        self.assertEqual(ds.max_wins("QuickDraft_TRK_20261113"), 7)
        self.assertEqual(ds.max_wins("PremierDraft_TRK_20261113"), 7)
        self.assertEqual(ds.max_wins("TradDraft_TRK_20261113"), 3)
        self.assertEqual(ds.max_wins("Sealed_TRK_20261113"), 7)
        self.assertEqual(ds.max_wins(""), 4)  # ohne Event wie bisher
        self.assertEqual(ds.max_wins(None), 4)

    def test_file_name_with_wins(self):
        self.assertEqual(ds.enemy_file_name("TRK", "redwhite", "2026-11-12 20:47", 7),
                         "drafted_TRK_7wins_redwhite_2026-11-12_2047.txt")


class NormalDraftSaveTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        d = pathlib.Path(self.dir.name)
        self.path, self.enemies = d / "s.json", d / "enemydecks"
        self.enemies.mkdir()

    def tearDown(self):
        self.dir.cleanup()

    def feed(self, *lines):
        t = ds.Tracker(self.path, lookup, lambda g: "TRK", enemy_dir=self.enemies, card_info=INFO.get)
        for line in lines:
            t.feed_line(line)
        return t, sorted(p.name for p in self.enemies.iterdir())

    def test_four_wins_save_nothing_in_normal_draft(self):
        _, files = self.feed(auth_line(), *quick_draft(), *played([True] * 4))
        self.assertEqual(files, [])

    def test_seven_wins_save(self):
        t, files = self.feed(auth_line(), *quick_draft(), *played([True, False, True, True, True, True, True, True]))
        self.assertEqual(files, ["drafted_TRK_7wins_whitesplashred_2026-11-12_2047.txt"])
        self.assertEqual(t.last_saved, files[0])


class SnapshotResetTests(unittest.TestCase):
    """Die Meldung "Gegnerdeck gespeichert" gehoert zu ihrem Draft; ein neuer Draft beginnt ohne Reste."""

    def live(self, d, lines):
        from components import livedraft as ld
        from tests.fixtures import CARDS
        names = {g: {k: v for k, v in i.items() if k != "colors"} for g, i in INFO.items()}
        log = d / "Player.log"
        log.write_text("\n".join(lines) + "\n", encoding="utf-8")
        live = ld.LiveDraft(log, d / "pool.txt", names=names, fetch=lambda n, refresh=False: CARDS,
                            stats=d / "s.json", enemy_dir=d / "enemydecks")
        live.step()
        return live, log

    def test_message_gone_in_next_draft(self):
        from tests.test_enemy_autosave import matches as pt_matches
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            (d / "enemydecks").mkdir()
            live, log = self.live(d, [auth_line(), *DRAFT, DECK, *pt_matches([True] * 4)])
            self.assertTrue(live.snapshot({}, {}, None)["enemy_saved"])
            with log.open("a", encoding="utf-8") as f:  # naechster Draft: erstes Pack liegt an
                f.write(notify(1, [101, 102, 201], draft="d2") + "\n")
            live.step()
            snap = live.snapshot({}, {}, None)
            self.assertIsNone(snap["enemy_saved"])
            self.assertFalse(snap["complete"])
            self.assertIsNone(snap["deckinfo"])
            self.assertIsNone(snap.get("summary"))
            rows = "\n".join(r[0] for r in overlay.rows_for(snap))
            self.assertNotIn("Gegnerdeck gespeichert", rows)


class HallOfFameTests(unittest.TestCase):
    def test_celebration_text(self):
        lines = overlay.celebration_lines("drafted_TRK_7wins_red_2026-11-13_2200.txt")
        self.assertEqual(lines[0], "7 Siege!")
        self.assertIn("Hall of Fame", "\n".join(lines))
        self.assertEqual(overlay.celebration_lines("drafted_TRK_4wins_red_2026-11-13_2200.txt")[0], "4 Siege!")
        rows = overlay.rows_for({"status": "idle", "message": "x",
                                 "enemy_saved": "drafted_TRK_7wins_red_2026-11-13_2200.txt"})
        self.assertIn("7 Siege", rows[0][0])
        self.assertIn("Hall of Fame", rows[0][0])

    def test_no_hall_of_game_left(self):
        root = pathlib.Path(__file__).resolve().parent.parent
        for p in list((root / "components").rglob("*.py")) + [root / "README.md", root / "README.en.md"]:
            self.assertNotIn("Hall of Game", p.read_text(encoding="utf-8"), p.name)


class GuestCardArchetypeTests(unittest.TestCase):
    """Karten aus anderen Sets im Draft (z. B. Flare of Fortitude aus MH3 im TRK-Draft) bekommen die Archetyp-Knoepfe
    des Drafts bzw. des Pools."""

    def test_chips_fall_back_to_draft_set(self):
        from components.drafthelper import render_page
        page = render_page()
        self.assertIn("function chipSet(card)", page)
        self.assertIn("archsets[chipSet(card)]", page)


# ---------------------------------------------------------------- Spielstatistik aus dem Arena-Protokoll

def gre(*messages):
    return "[UnityCrossThreadLogger]greToClientEvent " + json.dumps(
        {"transactionId": "t", "greToClientEvent": {"greToClientMessages": list(messages)}})


def connect(seat=2):
    return {"type": "GREMessageType_ConnectResp", "systemSeatIds": [seat],
            "connectResp": {"deckMessage": {"deckCards": [101, 102]}}}


def state(match="m1", game=1, objects=(), annotations=(), turn=None, stage="GameStage_Play", seat=2, players=None,
          info=True):
    """Spielnachricht; info=False: ohne gameInfo (so schickt Arena die meisten Diffs, es gilt das laufende Spiel)."""
    g = {"type": "GameStateType_Diff", "gameObjects": list(objects), "annotations": list(annotations)}
    if info:
        g["gameInfo"] = {"matchID": match, "gameNumber": game, "stage": stage}
    if turn:
        g["turnInfo"] = {"turnNumber": turn, "activePlayer": 1}
    if players:
        g["players"] = players
    return {"type": "GREMessageType_GameStateMessage", "systemSeatIds": [seat], "gameStateMessage": g}


def obj(iid, controller, creature=False, grp=101):
    return {"instanceId": iid, "grpId": grp, "ownerSeatId": controller, "controllerSeatId": controller,
            "cardTypes": ["CardType_Creature"] if creature else ["CardType_Instant"]}


def zone(aid, iid, category):
    return {"id": aid, "affectedIds": [iid], "type": ["AnnotationType_ZoneTransfer"],
            "details": [{"key": "category", "type": "KeyValuePairValueType_string", "valueString": [category]}]}


def damage(aid, source, target, n):
    return {"id": aid, "affectorId": source, "affectedIds": [target], "type": ["AnnotationType_DamageDealt"],
            "details": [{"key": "damage", "type": "KeyValuePairValueType_int32", "valueInt32": [n]}]}


def one_game(match="m1", game=1):
    """Ein Spiel: wir (Platz 2) ziehen 2 Karten, wirken 1 Zauber, legen 1 Land, machen 3 + 4 Schaden am Gegner und 2 an
    einer Kreatur, die stirbt; der Gegner macht uns 5 Schaden; Runde 6. Die Annotation 13 kommt doppelt."""
    return [
        gre(connect()),
        gre(state(match, game, [obj(50, 2, True), obj(51, 2), obj(52, 2), obj(53, 2), obj(70, 1, True)],
                  [zone(10, 51, "Draw"), zone(11, 52, "Draw"), zone(12, 51, "CastSpell"), zone(13, 53, "PlayLand"),
                   damage(14, 50, 1, 3), damage(15, 50, 70, 2), damage(16, 70, 2, 5)], turn=3)),
        gre(state(match, game, [obj(53, 2), obj(71, 1, True)],
                  [zone(13, 53, "PlayLand"), zone(17, 71, "SBA_Damage"), damage(18, 50, 1, 4)], turn=6, info=False)),
        gre(state(match, game, [], [], stage="GameStage_GameOver")),
    ]


class GameStatsTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = pathlib.Path(self.dir.name) / "s.json"
        self.lines = [auth_line(), *quick_draft(), start_line("m1", event=QUICK), *one_game(), stamp(),
                      end_line("m1", [2], 2)]

    def tearDown(self):
        self.dir.cleanup()

    def tracker(self, lines):
        t = ds.Tracker(self.path, lookup, lambda g: "TRK")
        for line in lines:
            t.feed_line(line)
        return t

    def test_summary(self):
        t = self.tracker(self.lines)
        s = t.summary("d1", QUICK)
        self.assertEqual(s["games"], 1)
        self.assertEqual(s["drawn"], 2)
        self.assertEqual(s["spells"], 1)
        self.assertEqual(s["lands"], 1)  # Annotation 13 doppelt: einmal gezaehlt
        self.assertEqual(s["damage_dealt"], 7)
        self.assertEqual(s["damage_creatures"], 2)
        self.assertEqual(s["damage_taken"], 5)
        self.assertEqual(s["biggest_hit"], 4)
        self.assertEqual(s["kills"], 1)
        self.assertEqual(s["turns"], 6)
        self.assertEqual((s["wins"], s["losses"], s["max_wins"]), (1, 0, 7))

    def test_restart_does_not_double(self):
        self.tracker(self.lines)
        t = self.tracker(self.lines)  # draftgott neu gestartet: Protokoll von vorn
        self.assertEqual(t.summary("d1", QUICK)["drawn"], 2)
        self.assertEqual(t.summary("d1", QUICK)["games"], 1)

    def test_two_games(self):
        lines = [auth_line(), *quick_draft(), start_line("m1", event=QUICK), *one_game("m1", 1), *one_game("m1", 2),
                 stamp(), end_line("m1", [2, 2], 2), start_line("m2", event=QUICK), *one_game("m2", 1), stamp(),
                 end_line("m2", [1], 1)]
        s = self.tracker(lines).summary("d1", QUICK)
        self.assertEqual(s["games"], 3)
        self.assertEqual(s["drawn"], 6)
        self.assertEqual((s["wins"], s["losses"]), (1, 1))

    def test_no_games(self):
        t = self.tracker([auth_line(), *quick_draft()])
        self.assertEqual(t.summary("d1", QUICK)["games"], 0)
        self.assertIsNone(t.summary("unbekannt", "x"))

    def test_snapshot_and_overlay_show_summary(self):
        from components import livedraft as ld
        from tests.fixtures import CARDS
        names = {g: {k: v for k, v in i.items() if k != "colors"} for g, i in INFO.items()}
        d = pathlib.Path(self.dir.name)
        log = d / "Player.log"
        log.write_text("\n".join(self.lines) + "\n", encoding="utf-8")
        live = ld.LiveDraft(log, d / "pool.txt", names=names, fetch=lambda n, refresh=False: CARDS, stats=self.path)
        live.step()
        snap = live.snapshot({}, {}, None)
        self.assertEqual(snap["summary"]["drawn"], 2)
        rows = "\n".join(r[0] for r in overlay.rows_for(snap))
        self.assertIn("Draft-Bilanz", rows)
        self.assertIn("7", rows)  # Schaden am Gegner


if __name__ == "__main__":
    unittest.main()
