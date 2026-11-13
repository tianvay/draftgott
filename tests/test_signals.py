"""Im Draft: offene Farben. Hauptsignal: eine starke Karte (eigene Bewertung Must Play oder hoeher) kommt mit dem
Pack zurueck (Wheel). Daneben: starke Karten, die noch spaet im Pack liegen (mindestens drei andere Spieler haben das
Pack schon gesehen), und starke Karten, die andere zwischen zwei Besuchen eines Packs genommen haben (umkaempft).
Pick Two und klassischer Draft werden an der Zahl der Karten je Pick erkannt; das Wheel daran, dass ein Pack eine
Teilmenge eines frueheren Packs derselben Runde ist (gilt fuer jede Spielerzahl)."""
import json
import pathlib
import unittest

from components import arenalog as al
from components import overlay
from components import signals

COLORS = {1: "W", 2: "W", 3: "R", 4: "G", 5: "G", 6: "U", 7: "B", 8: "RG"}
for i in range(10, 60):
    COLORS.setdefault(i, "U")
NAMES = {i: f"Karte {i}" for i in range(1, 60)}


def card_of(grp):
    return {"name": NAMES[grp], "colors": list(COLORS.get(grp, ""))}


def h(cards, picked, pick):
    return {"cards": list(cards), "picked": list(picked), "pick": pick}


class WheelTests(unittest.TestCase):
    def setUp(self):
        # Runde mit 3 Spielern, Packs zu 6 Karten: Pack A kommt nach 3 Picks zurueck
        self.history = [h([1, 2, 3, 4, 5, 6], [1], 1), h([11, 12, 13, 14, 15], [11], 2), h([21, 22, 23, 24], [21], 3),
                        h([2, 3, 4], [2], 4)]

    def test_wheeled_strong_card_opens_its_color(self):
        ratings = {"Karte 3": "mustplay", "Karte 4": "filler", "Karte 5": "matchwinner", "Karte 6": "splashworthy"}
        s = signals.analyze(self.history, card_of, ratings)
        self.assertEqual(s["format"], "Draft")
        self.assertEqual(s["wheels"], 1)
        self.assertEqual(s["colors"]["R"]["open"], 2)  # Karte 3 kam zurueck
        self.assertEqual(s["colors"]["G"]["contested"], 1)  # Karte 5 von anderen genommen
        self.assertEqual(s["colors"]["U"]["contested"], 1)  # Karte 6 (Splashworthy) ebenso
        self.assertEqual(s["colors"]["G"]["open"], 0)  # Filler zaehlt nicht
        self.assertTrue(any("Karte 3" in n and "zurück" in n for n in s["notes"]))
        self.assertTrue(any("Karte 5" in n and "genommen" in n for n in s["notes"]))

    def test_nothing_strong_no_signal(self):
        s = signals.analyze(self.history, card_of, {})
        self.assertTrue(all(c["score"] == 0 for c in s["colors"].values()))
        self.assertEqual(s["notes"], [])

    def test_multicolor_counts_for_each_color(self):
        history = [h([8, 1, 2, 3], [1], 1), h([12, 13, 14], [12], 2), h([8, 3], [8], 3)]
        s = signals.analyze(history, card_of, {"Karte 8": "mustplay"})
        self.assertEqual((s["colors"]["R"]["open"], s["colors"]["G"]["open"]), (2, 2))

    def test_new_round_is_not_a_wheel(self):
        # Runde 1 endet mit einer Karte; das groessere Pack danach ist Runde 2, auch wenn es zu Pack A passt
        history = [h([1, 2, 3, 4, 5, 6], [1], 1), h([12], [12], 2), h([2, 3, 4, 5], [2], 3)]
        s = signals.analyze(history, card_of, {"Karte 3": "mustplay"})
        self.assertEqual(s["wheels"], 0)


class PickTwoTests(unittest.TestCase):
    def test_pick_two_wheel(self):
        history = [h([1, 2, 3, 4, 5, 6, 7, 30], [1, 2], 1), h([11, 12, 13, 14, 15, 16], [11, 12], 3),
                   h([21, 22, 23, 24], [21, 22], 5), h([3, 4], [3, 4], 7)]
        s = signals.analyze(history, card_of, {"Karte 3": "mustplay", "Karte 6": "mustplay"})
        self.assertEqual(s["format"], "Pick Two")
        self.assertEqual(s["colors"]["R"]["open"], 2)
        self.assertEqual(s["colors"]["U"]["contested"], 1)

    def test_late_strong_card_counts_by_players_not_cards(self):
        full = list(range(10, 24))  # 14 Karten
        # Pick Two: Pack mit 8 Karten = 3 andere Spieler haben je 2 genommen -> spaet
        late = [h(full, [10, 11], 1), h([3] + list(range(30, 37)), [30, 31], 3)]
        s = signals.analyze(late, card_of, {"Karte 3": "mustplay"})
        self.assertEqual(s["colors"]["R"]["open"], 1)
        # Pack mit 10 Karten = erst 2 andere Spieler -> noch nicht spaet
        early = [h(full, [10, 11], 1), h([3] + list(range(30, 39)), [30, 31], 3)]
        self.assertEqual(signals.analyze(early, card_of, {"Karte 3": "mustplay"})["colors"]["R"]["open"], 0)
        # klassischer Draft: 8 Karten = 6 andere Spieler -> spaet; 12 Karten = 2 -> nicht
        classic = [h(full, [10], 1), h([3] + list(range(30, 37)), [30], 2)]
        self.assertEqual(signals.analyze(classic, card_of, {"Karte 3": "mustplay"})["colors"]["R"]["open"], 1)
        classic = [h(full, [10], 1), h([3] + list(range(30, 41)), [30], 2)]
        self.assertEqual(signals.analyze(classic, card_of, {"Karte 3": "mustplay"})["colors"]["R"]["open"], 0)

    def test_event_name_says_pick_two(self):
        s = signals.analyze([h([1, 2, 3], [], 1)], card_of, {}, event="PickTwoDraft_TRK_20261110")
        self.assertEqual(s["format"], "Pick Two")


class LevelTests(unittest.TestCase):
    def test_levels(self):
        self.assertEqual(signals.level(3), "open")
        self.assertEqual(signals.level(1), "maybe")
        self.assertEqual(signals.level(0), "")
        self.assertEqual(signals.level(-2), "contested")


def notify(n, cards):
    return ('[UnityCrossThreadLogger]Draft.Notify {"draftId":"d1","SelfPick":%d,"SelfPack":1,"PackCards":"%s"}'
            % (n, ",".join(map(str, cards))))


def pick(cards):
    return "[UnityCrossThreadLogger]==> Event_PlayerDraftMakePick " + json.dumps(
        {"id": "x", "request": json.dumps({"DraftId": "d1", "GrpIds": cards, "Pack": 1, "Pick": 1})})


class StateHistoryTests(unittest.TestCase):
    def test_draft_state_records_packs_and_own_picks(self):
        s = al.DraftState()
        for line in [notify(1, [1, 2, 3]), pick([1]), notify(2, [11, 12]), pick([12]), notify(3, [2])]:
            for ev in al.scan_line(line):
                s.feed(ev)
        self.assertEqual(s.history, [{"cards": [1, 2, 3], "picked": [1], "pick": 1},
                                     {"cards": [11, 12], "picked": [12], "pick": 2},
                                     {"cards": [2], "picked": [], "pick": 3}])
        for ev in al.scan_line(notify(1, [40, 41]).replace('"d1"', '"d2"')):
            s.feed(ev)
        self.assertEqual(len(s.history), 1)  # neuer Draft


class OverlayTests(unittest.TestCase):
    def test_signal_row(self):
        sig = {"format": "Pick Two", "wheels": 1, "notes": ["Pick 7: Karte 3 (MP) kam zurück"],
               "colors": {c: {"open": 0, "contested": 0, "score": 0, "level": ""} for c in "WUBRG"}}
        sig["colors"]["R"] = {"open": 3, "contested": 0, "score": 3, "level": "open"}
        sig["colors"]["G"] = {"open": 0, "contested": 2, "score": -2, "level": "contested"}
        snap = {"status": "pack", "pick": 8, "detect": {"main": None, "scores": []}, "pack": [], "signals": sig}
        text = "\n".join(r[0] for r in overlay.rows_for(snap))
        self.assertIn("Signale (Pick Two): R offen +3 · G umkämpft −2", text)
        self.assertIn("Karte 3 (MP) kam zurück", text)

    def test_no_row_without_signal(self):
        sig = {"format": "Draft", "wheels": 0, "notes": [],
               "colors": {c: {"open": 0, "contested": 0, "score": 0, "level": ""} for c in "WUBRG"}}
        snap = {"status": "pack", "pick": 2, "detect": {"main": None, "scores": []}, "pack": [], "signals": sig}
        self.assertNotIn("Signale", "\n".join(r[0] for r in overlay.rows_for(snap)))


class PageTests(unittest.TestCase):
    def test_page_and_help(self):
        from components.drafthelper import render_page
        from components.howitworks import render_help_page
        self.assertIn('id="lsignals"', render_page())
        self.assertIn("Offene Farben", render_help_page())
        readme = (pathlib.Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
        self.assertIn("Offene Farben", readme)


if __name__ == "__main__":
    unittest.main()
