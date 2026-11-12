"""Arena-Protokoll (Player.log): Packs und Picks erkennen, Draft-Zustand, Datei mitlesen, Kartendatenbank."""
import json
import pathlib
import sqlite3
import tempfile
import unittest

from components import arenalog as al


def req(prefix, payload):
    """Zeile wie im Protokoll: JSON mit dem eigentlichen Inhalt als Text im Feld "request"."""
    return prefix + " " + json.dumps({"id": "x", "request": json.dumps(payload)})


NOTIFY = '[UnityCrossThreadLogger]Draft.Notify {"draftId":"d1","SelfPick":1,"SelfPack":1,"PackCards":"101,102,103"}'
NOTIFY2 = '[UnityCrossThreadLogger]Draft.Notify {"draftId":"d1","SelfPick":2,"SelfPack":1,"PackCards":"201,202"}'
MAKE_PICK = req("[UnityCrossThreadLogger]==> Event_PlayerDraftMakePick",
                {"DraftId": "d1", "GrpIds": [101], "Pack": 1, "Pick": 1})
BUSINESS = req("[UnityCrossThreadLogger]==> LogBusinessEvents",
               {"DraftId": "d1", "EventId": "PremierDraft_TRK_20261110", "PackNumber": 1, "PickNumber": 1,
                "PickGrpId": 101, "CardsInPack": [101, 102, 103], "AutoPick": False})
BOT_STATUS = json.dumps({"CurrentModule": "BotDraft", "Payload": json.dumps(
    {"Result": "Success", "EventName": "QuickDraft_TRK_20261110", "DraftStatus": "PickNext", "PackNumber": 0,
     "PickNumber": 1, "DraftPack": ["301", "302", "303"], "PickedCards": ["300"]})})
BOT_PICK = req("[UnityCrossThreadLogger]==> BotDraft_DraftPick",
               {"EventName": "QuickDraft_TRK_20261110",
                "PickInfo": {"EventName": "QuickDraft_TRK_20261110", "CardIds": ["302"], "PackNumber": 0,
                             "PickNumber": 1}})
PICK_TWO = req("[UnityCrossThreadLogger]==> BotDraft_DraftPick",
               {"EventName": "PickTwoDraft_TRK_20261110",
                "PickInfo": {"EventName": "PickTwoDraft_TRK_20261110", "CardIds": ["401", "402"],
                             "PackNumber": 0, "PickNumber": 0}})


class ScanTests(unittest.TestCase):
    def test_human_draft_pack(self):
        self.assertEqual(al.scan_line(NOTIFY), [{"kind": "pack", "cards": [101, 102, 103], "draft": "d1",
                                                 "event": None}])

    def test_human_draft_pick(self):
        self.assertEqual(al.scan_line(MAKE_PICK), [{"kind": "pick", "cards": [101], "draft": "d1", "event": None}])

    def test_business_event_is_a_pick_not_a_pack(self):
        self.assertEqual(al.scan_line(BUSINESS), [{"kind": "pick", "cards": [101], "draft": "d1",
                                                   "event": "PremierDraft_TRK_20261110"}])

    def test_bot_draft_status_gives_pack_and_picked_cards(self):
        events = al.scan_line(BOT_STATUS)
        self.assertIn({"kind": "pack", "cards": [301, 302, 303], "draft": None, "event": "QuickDraft_TRK_20261110"},
                      events)
        self.assertIn({"kind": "picked", "cards": [300], "draft": None, "event": "QuickDraft_TRK_20261110"}, events)

    def test_bot_and_pick_two_picks(self):
        self.assertEqual(al.scan_line(BOT_PICK)[0]["cards"], [302])
        self.assertEqual(al.scan_line(PICK_TWO)[0]["cards"], [401, 402])
        self.assertEqual(al.scan_line(PICK_TWO)[0]["event"], "PickTwoDraft_TRK_20261110")

    def test_other_lines_are_ignored(self):
        for line in ["", "[UnityCrossThreadLogger]Client.SceneChange {\"toSceneName\":\"Home\"}",
                     '{"Deck":{"MainDeck":[{"GrpId":5,"quantity":2}]}}',  # GrpId ohne Pick
                     '{"grpId": 77, "zoneId": 3}', "Pick something {kaputt", '{"PackCards": ""}',
                     '{"InternalEventName":"PickTwoDraft_TRK","CardSkins":[{"GrpId":"105088","CCV":"DA"}]}',
                     '{"Pick":1,"prompt":{"CardId":7}}']:  # Nummer und Karte muessen im selben Objekt stehen
            self.assertEqual(al.scan_line(line), [], line)

    def test_set_code_from_event_name(self):
        self.assertEqual(al.set_from_event("PickTwoDraft_TRK_20261110"), "TRK")
        self.assertEqual(al.set_from_event("QuickDraft_FRA_20261001"), "FRA")
        self.assertIsNone(al.set_from_event("Ladder"))
        self.assertIsNone(al.set_from_event(None))


def feed(state, *lines):
    for line in lines:
        for ev in al.scan_line(line):
            state.feed(ev)
    return state


class StateTests(unittest.TestCase):
    def test_pack_then_pick_waits_for_the_next_pack(self):
        s = feed(al.DraftState(), NOTIFY)
        self.assertEqual(s.pack, [101, 102, 103])
        self.assertFalse(s.waiting)
        feed(s, MAKE_PICK)
        self.assertEqual(s.picks, [101])
        self.assertEqual(s.pack, [])
        self.assertTrue(s.waiting)
        feed(s, NOTIFY2)
        self.assertEqual(s.pack, [201, 202])
        self.assertFalse(s.waiting)

    def test_same_pick_from_two_lines_counts_once(self):
        s = feed(al.DraftState(), NOTIFY, MAKE_PICK, BUSINESS)
        self.assertEqual(s.picks, [101])
        s = feed(al.DraftState(), NOTIFY, MAKE_PICK, NOTIFY2, BUSINESS)  # Doppel kommt erst nach dem neuen Pack
        self.assertEqual(s.picks, [101])

    def test_picked_cards_are_authoritative(self):
        s = feed(al.DraftState(), BOT_STATUS)
        self.assertEqual(s.picks, [300])
        feed(s, BOT_PICK)
        self.assertEqual(s.picks, [300, 302])

    def test_new_draft_resets(self):
        s = feed(al.DraftState(), NOTIFY, MAKE_PICK)
        other = '[UnityCrossThreadLogger]Draft.Notify {"draftId":"d2","SelfPick":1,"SelfPack":1,"PackCards":"9,8"}'
        feed(s, other)
        self.assertEqual((s.draft, s.picks, s.pack), ("d2", [], [9, 8]))
        feed(s, BOT_STATUS)  # anderes Event ohne Draft-Kennung: Wechsel nur ueber den Eventnamen
        self.assertEqual(s.event, "QuickDraft_TRK_20261110")
        s2 = feed(al.DraftState(), BOT_STATUS, PICK_TWO)
        self.assertEqual(s2.picks, [401, 402])

    def test_feed_reports_changes(self):
        s = al.DraftState()
        ev = al.scan_line(NOTIFY)[0]
        self.assertTrue(s.feed(ev))
        self.assertFalse(s.feed(ev))

    def test_pick_two_takes_both_cards(self):
        pack = json.dumps({"Payload": json.dumps({"EventName": "PickTwoDraft_TRK_20261110",
                                                  "DraftPack": ["401", "402", "403"], "PickedCards": []})})
        s = feed(al.DraftState(), pack, PICK_TWO)
        self.assertEqual(s.picks, [401, 402])
        self.assertTrue(s.waiting)


class FollowerTests(unittest.TestCase):
    def test_reads_new_lines_and_restarts_after_truncation(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "Player.log"
            f = al.LogFollower(path)
            self.assertEqual(f.poll(), [])  # Datei fehlt noch
            path.write_text("eins\nzwei\ndr", encoding="utf-8")
            self.assertEqual(f.poll(), ["eins", "zwei"])
            with path.open("a", encoding="utf-8") as fh:
                fh.write("ei\nvier\n")
            self.assertEqual(f.poll(), ["drei", "vier"])
            self.assertEqual(f.poll(), [])
            path.write_text("neu\n", encoding="utf-8")  # Arena neu gestartet: Datei kuerzer
            self.assertEqual(f.poll(), ["neu"])
            self.assertTrue(f.restarted)


class CardDbTests(unittest.TestCase):
    def test_names_from_the_arena_database(self):
        with tempfile.TemporaryDirectory() as d:
            raw = pathlib.Path(d) / "MTGA_Data" / "Downloads" / "Raw"
            raw.mkdir(parents=True)
            db = raw / "Raw_CardDatabase_abc.mtga"
            con = sqlite3.connect(db)
            con.execute("CREATE TABLE Cards(GrpId INT, TitleId INT, ExpansionCode TEXT, CollectorNumber TEXT, "
                        "IsToken BOOLEAN)")
            con.execute("CREATE TABLE Localizations_enUS(LocId INT, Formatted INT, Loc TEXT)")
            con.executemany("INSERT INTO Cards VALUES (?,?,?,?,?)",
                            [(101, 1, "TRK", "5", 0), (102, 2, "TRK", "6", 0), (103, 3, "TRK", "", 1)])
            con.executemany("INSERT INTO Localizations_enUS VALUES (?,?,?)",
                            [(1, 1, "Test Bear"), (1, 0, "Test Bear"), (2, 0, "<i>Test</i> Spell"),
                             (3, 0, "Token")])
            con.commit()
            con.close()
            self.assertEqual(al.find_card_db([pathlib.Path(d) / "MTGA_Data", pathlib.Path(d) / "fehlt"]), db)
            names = al.load_card_db(db)
            self.assertEqual(names[101], {"name": "Test Bear", "set": "TRK", "number": "5"})
            self.assertEqual(names[102]["name"], "Test Spell")  # Formatierung entfernt
            self.assertNotIn(103, names)  # Token
        self.assertEqual(al.load_card_db(pathlib.Path(d) / "fehlt.mtga"), {})

    def test_install_dir_from_the_log(self):
        text = "x\nMono path[0] = 'C:/Program Files (x86)/Steam/steamapps/common/MTGA/MTGA_Data/Managed'\n"
        self.assertEqual(al.install_dirs(text)[0],
                         pathlib.Path("C:/Program Files (x86)/Steam/steamapps/common/MTGA/MTGA_Data"))
        self.assertTrue(al.install_dirs(""))  # bekannte Installationsorte als Rueckfall

    def test_default_log_path(self):
        p = al.default_log_path(pathlib.Path("C:/Users/X"))
        self.assertEqual(p, pathlib.Path("C:/Users/X/AppData/LocalLow/Wizards Of The Coast/MTGA/Player.log"))

    def test_names_from_scryfall_arena_ids(self):
        cache = {"Test Bear": {"name": "Test Bear", "arena_id": 101, "set": "trk", "collector_number": "5"},
                 "Other": {"name": "Other"}}
        self.assertEqual(al.scryfall_names(cache), {101: {"name": "Test Bear", "set": "TRK", "number": "5"}})


if __name__ == "__main__":
    unittest.main()
