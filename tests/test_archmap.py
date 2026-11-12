"""Live-Draft: welche Picks und Pack-Karten zu welchem Archetyp gehoeren (nur eigene Zuordnung; eine Karte kann
mehreren Archetypen angehoeren, Karten ohne Zuordnung gehoeren keinem an)."""
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from components import archetypes as arch
from components import cardarchetypes as ca
from components import livedraft as ld
from components import overlay
from tests.fixtures import CARDS

TRK = [{"colors": "WU", "name": "Spacecraft"}, {"colors": "BR", "name": "Sacrifice"},
       {"colors": "RW", "name": "Go wide"}]


class MapTests(unittest.TestCase):
    def test_map(self):
        assign = {"A": ["BR"], "B": ["BR", "RW"], "C": ["WU"], "P": ["RW"]}
        m = ca.archetype_map(TRK, assign, ["A", "B", "A", "X"], ["P", "B", "Y"])
        by = {r["colors"]: r for r in m}
        self.assertEqual(by["BR"]["picks"], [{"name": "A", "n": 2}, {"name": "B", "n": 1}])
        self.assertEqual(by["BR"]["pack"], ["B"])
        self.assertEqual(by["RW"]["picks"], [{"name": "B", "n": 1}])
        self.assertEqual(by["RW"]["pack"], ["P", "B"])
        self.assertNotIn("WU", by)  # nichts in Picks und Pack: weg
        self.assertEqual([r["colors"] for r in m], ["BR", "RW"])  # Reihenfolge des Sets
        self.assertEqual(by["BR"]["name"], "Sacrifice")
        self.assertEqual(by["BR"]["count"], 3)  # Kopien in den Picks
        names = {n for r in m for n in [p["name"] for p in r["picks"]] + r["pack"]}
        self.assertNotIn("X", names)  # ohne Zuordnung: kein Archetyp
        self.assertNotIn("Y", names)

    def test_without_archetypes(self):
        self.assertEqual(ca.archetype_map(None, {"A": ["BR"]}, ["A"], []), [])


class LiveTests(unittest.TestCase):
    def test_snapshot_has_the_map(self):
        names = {101: {"name": "Test Bear", "set": "TST", "number": "10"},
                 102: {"name": "Test Hasty", "set": "TST", "number": "11"}}
        with tempfile.TemporaryDirectory() as d:
            log = pathlib.Path(d) / "Player.log"
            pack = ('[UnityCrossThreadLogger]Draft.Notify {"draftId":"d1","SelfPick":%d,"SelfPack":1,'
                    '"PackCards":"%s"}')
            pick = "[UnityCrossThreadLogger]==> Event_PlayerDraftMakePick " + json.dumps(
                {"id": "x", "request": json.dumps({"DraftId": "d1", "GrpIds": [101], "Pack": 1, "Pick": 1})})
            log.write_text("\n".join([pack % (1, "101,102"), pick, pack % (2, "102")]) + "\n", encoding="utf-8")
            live = ld.LiveDraft(log, pathlib.Path(d) / "pool.txt", names=names,
                                fetch=lambda n, refresh=False: CARDS)
            live.step()
            fake = {"tst": [{"colors": "RW", "name": "Go wide", "tips": []}]}
            with mock.patch.dict(arch.ARCHETYPES, fake):
                snap = live.snapshot({}, {"Test Bear": ["RW"], "Test Hasty": ["RW"]}, None)
        self.assertEqual(snap["archmap"], [{"colors": "RW", "name": "Go wide", "count": 1,
                                            "picks": [{"name": "Test Bear", "n": 1}], "pack": ["Test Hasty"]}])


class OverlayTests(unittest.TestCase):
    def test_rows(self):
        snap = {"status": "pack", "pick": 2, "detect": {"main": None, "scores": []}, "pack": [],
                "archmap": [{"colors": "BR", "name": "Sacrifice", "count": 3,
                             "picks": [{"name": "A", "n": 2}, {"name": "B", "n": 1}], "pack": ["P"]}]}
        text = "\n".join(r[0] for r in overlay.rows_for(snap))
        self.assertIn("Sacrifice: 3 Picks", text)
        self.assertIn("im Pack: P", text)

    def test_page_has_the_map(self):
        from components.drafthelper import render_page
        self.assertIn('id="lmap"', render_page())

    def test_help(self):
        from components.howitworks import render_help_page
        self.assertIn("Archetypen im Draft", render_help_page())


if __name__ == "__main__":
    unittest.main()
