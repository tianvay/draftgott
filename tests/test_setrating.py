"""Funktion 5 "Set bewerten" (components/setrating.py): ein fertig umgesetztes Set waehlen und je Karte Kategorie
und Archetypen einmal festlegen (gleiche Dateien wie Drafthelper und Live-Draft)."""
import json
import pathlib
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock

from components import archetypes as arch
from components import setrating
from components.cli import parse_args
from tests.i18n_check import english, german_leftovers

ROOT = pathlib.Path(__file__).resolve().parent.parent

TST = {"tst": [{"colors": "WB", "name": "Testgilde", "tips": ["Tipp"]},
               {"colors": "RW", "name": "Testangriff", "tips": []}]}


def sc(name, colors, number, type_line="Creature — Bear", rarity="common", cost="{1}{W}"):
    return {"name": name, "colors": colors, "collector_number": number, "type_line": type_line,
            "rarity": rarity, "mana_cost": cost, "cmc": 2, "set": "tst", "set_name": "Testset",
            "image_uris": {"normal": f"https://img/normal/{number}.jpg"}}


SET = [sc("Test Defender", ["W"], "1"), sc("Test Raider", ["R"], "2", rarity="uncommon"),
       sc("Test Gold", ["W", "B"], "3", rarity="rare"), sc("Test Defender", ["W"], "1a"),  # zweiter Druck
       sc("Plains", [], "250", type_line="Basic Land — Plains")]


class SetListTests(unittest.TestCase):
    def test_implemented_sets_are_the_sets_with_archetypes(self):
        codes = [s["code"] for s in setrating.implemented_sets()]
        self.assertEqual(codes, [c.upper() for c in arch.ARCHETYPES])
        self.assertIn("TRK", codes)
        self.assertIn("FRA", codes)
        trk = setrating.implemented_sets()[0]
        self.assertEqual(len(trk["archetypes"]), 10)
        self.assertEqual(set(trk["archetypes"][0]), {"colors", "name"})

    def test_set_cards_without_basics_and_duplicates(self):
        cards = setrating.set_cards("tst", lambda code: SET)
        self.assertEqual([c["name"] for c in cards], ["Test Defender", "Test Raider", "Test Gold"])
        self.assertEqual(cards[2]["colors"], ["W", "B"])
        self.assertEqual(cards[1]["rarity"], "uncommon")
        self.assertEqual(cards[0]["set"], "TST")

    def test_double_faced_cards_use_the_front_name_like_arena(self):
        prep = dict(sc("Pyre Rhymer // Molten Tide", ["R"], "9"), layout="prepare")
        split = dict(sc("Fire // Ice", ["U", "R"], "10"), layout="split")
        cards = setrating.set_cards("tst", lambda code: [prep, split])
        self.assertEqual([c["name"] for c in cards], ["Pyre Rhymer", "Fire // Ice"])
        self.assertEqual(setrating.rating_name(prep), "Pyre Rhymer")

    def test_drafthelper_set_view_uses_the_same_names(self):
        from components import drafthelper
        self.assertIs(drafthelper.rating_name, setrating.rating_name)

    def test_progress_neverplay_needs_no_archetype(self):
        cards = setrating.set_cards("tst", lambda code: SET)
        self.assertEqual(setrating.progress(cards, {"Test Raider": "neverplay"}, {})["done"], 1)

    def test_progress(self):
        cards = setrating.set_cards("tst", lambda code: SET)
        p = setrating.progress(cards, {"Test Defender": "mustplay", "Test Gold": "matchwinner", "Fremd": "filler"},
                               {"Test Gold": ["WB"], "Test Raider": ["RW"], "Fremd": ["WB"]})
        self.assertEqual(p, {"total": 3, "rated": 2, "assigned": 2, "done": 1,
                             "cats": {"matchwinner": 1, "splashworthy": 0, "mustplay": 1, "playable": 0,
                                      "filler": 0, "neverplay": 0}})

    def test_start_set(self):
        self.assertEqual(setrating.start_set("trk"), "TRK")
        self.assertEqual(setrating.start_set("FRA"), "FRA")
        self.assertEqual(setrating.start_set(""), "")
        self.assertEqual(setrating.start_set("xyz"), "")


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = pathlib.Path(self.tmp.name)
        self.ratings, self.assign = d / "bew.json", d / "arch.json"
        self.patch = mock.patch.dict(arch.ARCHETYPES, TST)
        self.patch.start()
        self.app = {"ratings": self.ratings, "cardarch": self.assign, "fetch_set": lambda code: SET,
                    "start": "TST"}
        self.server = setrating.LocalServer(("127.0.0.1", 0), setrating.make_handler(self.app))
        self.app["server"] = self.server
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.patch.stop()
        self.tmp.cleanup()

    def get(self, path):
        try:
            with urllib.request.urlopen(self.base + path, timeout=10) as r:
                return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    def test_sets(self):
        status, body = self.get("/api/sets")
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertIn("TST", [s["code"] for s in data["sets"]])
        self.assertEqual(data["start"], "TST")

    def test_set_cards_with_ratings_and_archetypes(self):
        self.ratings.write_text(json.dumps({"Test Gold": "matchwinner", "Fremd": "filler"}), encoding="utf-8")
        self.assign.write_text(json.dumps({"Test Gold": {"arch": ["WB"], "best": "WB"}}), encoding="utf-8")
        status, body = self.get("/api/setcards?set=tst")
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(data["set"], "TST")
        self.assertEqual(len(data["cards"]), 3)
        self.assertEqual(data["ratings"], {"Test Gold": "matchwinner"})
        self.assertEqual(data["cardarch"], {"Test Gold": ["WB"]})
        self.assertEqual(data["cardbest"], {"Test Gold": "WB"})
        self.assertEqual([a["colors"] for a in data["archetypes"]], ["WB", "RW"])
        self.assertEqual(data["progress"]["rated"], 1)

    def test_only_implemented_sets(self):
        self.assertEqual(self.get("/api/setcards?set=xyz")[0], 400)
        self.assertEqual(self.get("/api/setcards?set=../x")[0], 400)

    def test_rating_is_saved(self):
        self.get("/api/setcards?set=tst")
        status, data = self.post("/api/rating", {"name": "Test Raider", "cat": "neverplay"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(self.ratings.read_text(encoding="utf-8")), {"Test Raider": "neverplay"})
        self.assertEqual(data["progress"]["rated"], 1)
        self.assertEqual(self.post("/api/rating", {"name": "Test Raider", "cat": ""})[0], 200)
        self.assertEqual(json.loads(self.ratings.read_text(encoding="utf-8")), {})

    def test_rating_rejects_unknown_cards_and_categories(self):
        self.assertEqual(self.post("/api/rating", {"name": "Test Raider", "cat": "mustplay"})[0], 400)  # Set nicht geladen
        self.get("/api/setcards?set=tst")
        self.assertEqual(self.post("/api/rating", {"name": "Fremd", "cat": "mustplay"})[0], 400)
        self.assertEqual(self.post("/api/rating", {"name": "Test Raider", "cat": "super"})[0], 400)
        self.assertFalse(self.ratings.exists())

    def test_archetypes_are_saved_with_best(self):
        self.get("/api/setcards?set=tst")
        status, data = self.post("/api/cardarch", {"name": "Test Gold", "arch": ["WB", "RW"], "best": "WB"})
        self.assertEqual(status, 200)
        self.assertEqual(data["cardarch"], {"Test Gold": ["WB", "RW"]})
        self.assertEqual(data["cardbest"], {"Test Gold": "WB"})
        self.assertEqual(data["progress"]["assigned"], 1)
        self.assertEqual(json.loads(self.assign.read_text(encoding="utf-8")),
                         {"Test Gold": {"arch": ["WB", "RW"], "best": "WB"}})
        self.assertEqual(self.post("/api/cardarch", {"name": "Test Gold", "arch": ["QQ"]})[0], 400)
        self.assertEqual(self.post("/api/cardarch", {"name": "Fremd", "arch": ["WB"]})[0], 400)

    def test_page(self):
        status, page = self.get("/")
        self.assertEqual(status, 200)
        for part in ('id="sets"', 'id="grid"', 'id="progress"', 'id="quit"', "Set bewerten", "Matchwinner",
                     "NeverPlay"):
            self.assertIn(part, page)

    def test_page_has_detail_view_with_arrows(self):
        status, page = self.get("/")
        for part in ('id="detail"', 'id="dprev"', 'id="dnext"', 'id="dimg"', 'id="dcats"', 'id="darchs"',
                     '"ArrowLeft"', '"ArrowRight"'):
            self.assertIn(part, page)

    def test_page_in_english_has_no_german_leftovers(self):
        with english():
            page = setrating.render_page()
        self.assertIn('<html lang="en">', page)
        self.assertIn("Rate a set", page)
        self.assertEqual(german_leftovers(page), [])

    def test_quit(self):
        self.assertEqual(self.post("/api/quit", {})[0], 200)


class LauncherTests(unittest.TestCase):
    def test_cli(self):
        self.assertEqual(parse_args(["--set-bewerten"]).set_bewerten, "")
        self.assertEqual(parse_args(["--set-bewerten", "FRA"]).set_bewerten, "FRA")
        self.assertIsNone(parse_args(["deck.txt"]).set_bewerten)

    def test_batch_menu_5(self):
        # Nutzer 17.11.2026: draftgott.bat entfernt, Start ueber den Launcher
        from components import launcher
        self.assertIn("--set-bewerten", launcher.command("setrate", "de"))
        self.assertFalse((ROOT / "draftgott.bat").exists())


if __name__ == "__main__":
    unittest.main()
