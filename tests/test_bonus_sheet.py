"""Bonusblaetter: Stardates (SDS) liegt selten in TRK-Boostern und gehoert zur Kartenliste von TRK (Set-Ansicht,
Set bewerten, Trick-Warner); jedes Set wird fuer sich in scryfall_set_cache.json gemerkt."""
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from components import scryfall, setrating


def card(name, code, number):
    return {"name": name, "set": code, "collector_number": number, "type_line": "Creature — Test", "mana_cost": "{1}",
            "cmc": 1, "colors": []}


class BonusSheetTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.file = pathlib.Path(tmp.name) / "scryfall_set_cache.json"
        patcher = mock.patch.object(scryfall, "SET_CACHE_FILE", self.file)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.asked = []

    def fake_one(self, code, refresh=False):
        self.asked.append(code)
        return {"trk": [card("Test Officer", "trk", "1")], "sds": [card("Sheoldred, the Apocalypse", "sds", "11")],
                "fra": [card("Test Bear", "fra", "2")]}.get(code, [])

    def test_trk_contains_stardates(self):
        self.assertEqual(scryfall.BONUS_SHEETS["trk"], ("sds",))
        with mock.patch.object(scryfall, "_fetch_one", self.fake_one):
            names = [c["name"] for c in scryfall.fetch_set_cards("TRK")]
        self.assertEqual(names, ["Test Officer", "Sheoldred, the Apocalypse"])  # Hauptset zuerst
        self.assertEqual(self.asked, ["trk", "sds"])

    def test_other_sets_unchanged(self):
        with mock.patch.object(scryfall, "_fetch_one", self.fake_one):
            self.assertEqual([c["name"] for c in scryfall.fetch_set_cards("fra")], ["Test Bear"])
            self.assertEqual([c["name"] for c in scryfall.fetch_set_cards("sds")], ["Sheoldred, the Apocalypse"])

    def test_cache_per_set_code(self):
        self.file.write_text(json.dumps({"trk": [card("Test Officer", "trk", "1")],
                                         "sds": [card("Phyrexian Tower", "sds", "29")]}), encoding="utf-8")
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("kein Netz erwartet")):
            names = [c["name"] for c in scryfall.fetch_set_cards("trk")]
        self.assertEqual(names, ["Test Officer", "Phyrexian Tower"])

    def test_set_rating_lists_bonus_cards_under_main_set(self):
        with mock.patch.object(scryfall, "_fetch_one", self.fake_one):
            cards = setrating.set_cards("TRK", scryfall.fetch_set_cards)
        self.assertEqual([c["name"] for c in cards], ["Test Officer", "Sheoldred, the Apocalypse"])
        self.assertEqual({c["set"] for c in cards}, {"TRK"})  # Gastkarte gehoert zum Set des Drafts


if __name__ == "__main__":
    unittest.main()
