import contextlib
import io
import json
import pathlib
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest import mock

from components import drafthelper as dh
from tests.fixtures import CARDS, POOL_TEXT, args_for


def load(text=POOL_TEXT):
    """load_pool mit Testkarten statt Scryfall."""
    with tempfile.TemporaryDirectory() as d:
        path = pathlib.Path(d) / "pool.txt"
        path.write_text(text, encoding="utf-8")
        with mock.patch.object(dh, "fetch_cards_cached", lambda names, refresh=False: CARDS), \
                mock.patch.object(dh, "fetch_printing_images", lambda specs: {}):
            return dh.load_pool(str(path))


class LoadPoolTests(unittest.TestCase):
    def test_basic_lands_are_not_card_tiles(self):
        cards, basics, _ = load()
        self.assertFalse({c["name"] for c in cards} & set(dh.BASIC_LANDS))
        self.assertEqual([b["name"] for b in basics], list(dh.BASIC_LANDS))

    def test_basics_start_with_deck_quantity_as_core(self):
        _, basics, _ = load()
        by = {b["name"]: b for b in basics}
        self.assertEqual((by["Plains"]["core"], by["Plains"]["pool"]), (4, 4))
        self.assertEqual((by["Mountain"]["core"], by["Mountain"]["pool"]), (2, 2))
        # nur im Sideboard: im Pool vorhanden, aber nicht im Deck
        self.assertEqual((by["Swamp"]["core"], by["Swamp"]["pool"]), (0, 1))
        # nicht im Pool: trotzdem vorhanden und auf 0
        self.assertEqual((by["Island"]["core"], by["Island"]["pool"]), (0, 0))

    def test_basic_keeps_printing_of_the_pool(self):
        _, basics, _ = load()
        plains = next(b for b in basics if b["name"] == "Plains")
        self.assertEqual((plains["set"], plains["number"]), ("tst", "1"))

    def test_cards_carry_color_type_set_and_section(self):
        cards, _, _ = load()
        big = next(c for c in cards if c["name"] == "Test Big")
        self.assertEqual(big["colors"], ["W"])
        self.assertEqual(big["section"], "deck")
        self.assertEqual((big["set"], big["number"]), ("tst", "13"))
        self.assertIn("Creature", big["type"])
        self.assertFalse(big["land"])

    def test_deck_comes_before_sideboard_and_cheap_before_expensive(self):
        cards, _, _ = load()
        sections = [c["section"] for c in cards]
        self.assertEqual(sections, sorted(sections, key=lambda s: s != "deck"))
        deck_mv = [c["mv"] for c in cards if c["section"] == "deck"]
        self.assertEqual(deck_mv, sorted(deck_mv))

    def test_signature_is_stable_and_follows_content(self):
        sig = load()[2]
        self.assertEqual(load()[2], sig)
        self.assertNotEqual(load(POOL_TEXT.replace("3 Test Bear", "2 Test Bear"))[2], sig)

    def test_missing_file_exits_with_message(self):
        with self.assertRaises(SystemExit):
            dh.load_pool("gibt_es_nicht.txt")


class EntriesFromMarksTests(unittest.TestCase):
    def setUp(self):
        self.cards, self.basics, _ = load()
        self.names = [c["name"] for c in self.cards]

    def marks(self, **by_name):
        return [by_name.get(c["name"].replace(" ", "_"), ["core"] * c["qty"]) for c in self.cards]

    def test_variants_are_core_plus_group(self):
        marks = self.marks(Test_Defender=["splash", "splash"], Test_Spell=["nosplash"])
        entries = dh.entries_from_marks(self.cards, marks)
        splash, nosplash = entries
        self.assertEqual((splash["name"], splash["role"]), ("Splash", "splash"))
        self.assertEqual((nosplash["name"], nosplash["role"]), ("NoSplash", "nosplash"))
        self.assertEqual(splash["deck"]["Test Defender"], 2)
        self.assertNotIn("Test Spell", splash["deck"])
        self.assertEqual(nosplash["deck"]["Test Spell"], 1)
        self.assertNotIn("Test Defender", nosplash["deck"])
        self.assertEqual(splash["deck"]["Test Bear"], 3)  # Core in beiden

    def test_off_cards_are_in_no_variant(self):
        marks = self.marks(Test_Big=["off"], Test_Spell=["splash"])
        for entry in dh.entries_from_marks(self.cards, marks):
            self.assertNotIn("Test Big", entry["deck"])

    def test_parts_keep_origin_of_each_card(self):
        marks = self.marks(Test_Spell=["splash"])
        splash = dh.entries_from_marks(self.cards, marks)[0]
        self.assertEqual([lab for lab, _ in splash["parts"]], ["Core", "Splash"])
        self.assertEqual(splash["parts"][1][1], {"Test Spell": 1})

    def test_no_splash_or_nosplash_gives_single_core_deck(self):
        entries = dh.entries_from_marks(self.cards, self.marks())
        self.assertEqual(len(entries), 1)
        self.assertEqual((entries[0]["name"], entries[0]["role"]), ("Core", "core"))

    def test_basic_lands_are_added_per_group(self):
        basics = {"Plains": {"core": 3, "splash": 0, "nosplash": 2}, "Swamp": {"core": 0, "splash": 1, "nosplash": 0}}
        marks = self.marks(Test_Spell=["splash"])
        splash, nosplash = dh.entries_from_marks(self.cards, marks, basics)
        self.assertEqual(splash["deck"]["Plains"], 3)
        self.assertEqual(splash["deck"]["Swamp"], 1)
        self.assertEqual(nosplash["deck"]["Plains"], 5)
        self.assertNotIn("Swamp", nosplash["deck"])

    def test_categories_are_passed_to_entries(self):
        marks = self.marks(Test_Spell=["splash"])
        for entry in dh.entries_from_marks(self.cards, marks, None, {"Test Spell": "splashworthy"}):
            self.assertEqual(entry["cats"], {"Test Spell": "splashworthy"})


class JobTests(unittest.TestCase):
    def test_idle_job_reports_zero_elapsed(self):
        s = dh.Job().status()
        self.assertEqual((s["state"], s["elapsed"]), ("idle", 0.0))

    def test_finished_job_keeps_report(self):
        job = dh.Job()
        job.start(lambda progress: "<html>ok</html>")
        for _ in range(100):
            if job.status()["state"] != "running":
                break
            time.sleep(0.02)
        self.assertEqual(job.status()["state"], "done")
        self.assertEqual(job.report, "<html>ok</html>")

    def test_sys_exit_message_becomes_error_state(self):
        job = dh.Job()
        job.start(lambda progress: (_ for _ in ()).throw(SystemExit("Zu wenige Karten")))
        for _ in range(100):
            if job.status()["state"] != "running":
                break
            time.sleep(0.02)
        s = job.status()
        self.assertEqual((s["state"], s["message"]), ("error", "Zu wenige Karten"))


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cards, basics, sig = load()
        cls.calls = []
        cls._stderr = mock.patch("sys.stderr", io.StringIO())  # Fortschrittsmeldungen des Jobs nicht ausgeben
        cls._stderr.start()

        def fake_simulate(entries, args, progress):
            cls.calls.append((entries, args))
            progress("simuliere ...")
            return "<html>Bericht</html>"

        cls.app = {"pool": cards, "basics": basics, "signature": sig, "args": args_for(["--drafthelper"]),
                   "simulate": fake_simulate, "save": lambda html, args: None, "job": dh.Job(),
                   "options": [1000, 10000], "file": "pool.txt"}
        cls.server = dh.LocalServer(("127.0.0.1", 0), dh.make_handler(cls.app))
        cls.app["server"] = cls.server
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls._stderr.stop()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=10) as r:
            return r.status, r.read().decode("utf-8")

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def valid_body(self, **extra):
        marks = [["core"] * c["qty"] for c in self.app["pool"]]
        body = {"marks": marks, "basics": {"Plains": {"core": 4, "splash": 0, "nosplash": 0}}, "sims": 500}
        body.update(extra)
        return body

    def wait_done(self):
        for _ in range(200):
            status = json.loads(self.get("/api/status")[1])
            if status["state"] != "running":
                return status
            time.sleep(0.02)
        self.fail("Simulation wurde nicht fertig")

    def test_page_is_served(self):
        status, body = self.get("/")
        self.assertEqual(status, 200)
        for marker in ('id="catfilter"', 'id="overview"', 'id="export"', 'id="search"', "Draft-Helper"):
            self.assertIn(marker, body)

    def test_pool_api(self):
        status, body = self.get("/api/pool")
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(data["signature"], self.app["signature"])
        self.assertEqual(len(data["cards"]), len(self.app["pool"]))
        self.assertEqual([b["name"] for b in data["basics"]], list(dh.BASIC_LANDS))

    def test_simulation_roundtrip_passes_categories_and_settings(self):
        body = self.valid_body(cats={"Test Big": "mustplay", "Gibt Es Nicht": "mustplay", "Test Bear": "unsinn"})
        body["marks"][[c["name"] for c in self.app["pool"]].index("Test Spell")] = ["splash"]
        status, answer = self.post("/api/simulate", body)
        self.assertEqual((status, answer), (200, {"ok": True}))
        self.assertEqual(self.wait_done()["state"], "done")
        self.assertEqual(self.get("/report")[1], "<html>Bericht</html>")
        entries, args = self.calls[-1]
        self.assertEqual(args.sims, 500)
        self.assertEqual(entries[0]["cats"], {"Test Big": "mustplay"})  # unbekannte Karte/Kategorie verworfen
        self.assertEqual(entries[0]["deck"]["Plains"], 4)

    def test_wrong_number_of_marks_is_rejected(self):
        status, answer = self.post("/api/simulate", self.valid_body(marks=[["core"]]))
        self.assertEqual(status, 400)
        self.assertFalse(answer["ok"])

    def test_unknown_mark_is_rejected(self):
        body = self.valid_body()
        body["marks"][0][0] = "irgendwas"
        self.assertEqual(self.post("/api/simulate", body)[0], 400)

    def test_basic_land_out_of_range_is_rejected(self):
        body = self.valid_body(basics={"Plains": {"core": 999, "splash": 0, "nosplash": 0}})
        self.assertEqual(self.post("/api/simulate", body)[0], 400)

    def test_sims_out_of_range_is_rejected(self):
        self.assertEqual(self.post("/api/simulate", self.valid_body(sims=5))[0], 400)

    def test_unknown_path_is_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/gibt/es/nicht")
        self.assertEqual(ctx.exception.code, 404)


class PortTests(unittest.TestCase):
    def test_port_cannot_be_shared_with_another_instance(self):
        """Regression: unter Windows landete der Browser sonst bei einer alten Instanz auf demselben Port."""
        first = dh.LocalServer(("127.0.0.1", 0), dh.make_handler({}))
        try:
            port = first.server_address[1]
            with self.assertRaises(OSError):
                dh.LocalServer(("127.0.0.1", port), dh.make_handler({}))
        finally:
            first.server_close()


if __name__ == "__main__":
    unittest.main()
