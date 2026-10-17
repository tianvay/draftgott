"""Kampf aus dem Bericht heraus: Leiste im Bericht, Rueckweg im Kampfbericht, Berichts-Server fuer die Analyse."""
import io
import json
import pathlib
import re
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.request
from unittest import mock

import mtg_sim
from components import report_server as rs
from components.battle_report import render_battle_html
from components.cli import parse_args
from components.report import FIGHT_JS
from tests.fixtures import CARDS, args_for


def report_html():
    args = args_for(["deck.txt", "--sims", "100"])
    entries = [{"path": "", "name": "Wir", "deck": {"Plains": 17, "Test Bear": 23}, "parts": []}]
    with mock.patch.object(mtg_sim, "fetch_cards_cached", lambda n, refresh=False: CARDS):
        return mtg_sim.simulate_entries(entries, args, progress=lambda m: None)


class ReportBarTests(unittest.TestCase):
    def test_report_has_the_fight_bar(self):
        html = report_html()
        self.assertIn('id="fightbar"', html)
        self.assertIn('id="fbenemy"', html)
        self.assertIn('id="fbgo"', html)
        self.assertIn("nur möglich, solange draftgott läuft", html)  # Hinweis bei direkt geoeffneter Datei
        self.assertIn("api/enemies", FIGHT_JS)

    @unittest.skipUnless(shutil.which("node"), "Node.js nicht installiert")
    def test_script_syntax(self):
        code = re.sub(r"</?script>", "", FIGHT_JS)
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(code)
        out = subprocess.run(["node", "--check", f.name], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_battle_report_links_back(self):
        html = render_battle_html([{"name": "Wir", "battles": []}], args_for(["deck.txt"]))
        self.assertIn('id="backlink"', html)
        self.assertIn('href="report"', html)


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        folder = pathlib.Path(self.tmp.name)
        (folder / "_enemydeck_walls.txt").write_text("Deck\n17 Plains\n", encoding="utf-8")
        self.calls = []

        def fake_battle(entries, enemy_path, args, progress):
            self.calls.append((entries, pathlib.Path(enemy_path).name))
            return "<p>KAMPFBERICHT</p>"

        self._err = mock.patch("sys.stderr", io.StringIO())
        self._err.start()
        self.app = rs.make_app("<p>BERICHT</p>", [{"name": "Wir", "deck": {"Plains": 17}}], args_for(["deck.txt"]),
                               fake_battle, lambda html, args: None, folder)
        self.server = rs.start(self.app, port=0)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self._err.stop()
        self.tmp.cleanup()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=10) as r:
            return r.read().decode("utf-8")

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    def test_report_and_enemies(self):
        self.assertIn("BERICHT", self.get("/"))
        self.assertIn("BERICHT", self.get("/report"))
        answer = json.loads(self.get("/api/enemies"))
        self.assertEqual([e["file"] for e in answer["enemies"]], ["_enemydeck_walls.txt"])
        self.assertTrue(answer["quit"])  # Analyse-Server: Knopf "Beenden" im Bericht

    def test_battle(self):
        self.assertTrue(self.post("/api/battle", {"enemy": "_enemydeck_walls.txt"})["ok"])
        for _ in range(100):
            if json.loads(self.get("/api/status"))["state"] != "running":
                break
            time.sleep(0.05)
        self.assertIn("KAMPFBERICHT", self.get("/battle"))
        self.assertEqual(self.calls[0][1], "_enemydeck_walls.txt")


class CliAndLauncherTests(unittest.TestCase):
    def test_option(self):
        self.assertTrue(parse_args(["deck.txt", "--bericht-server"]).bericht_server)
        self.assertFalse(parse_args(["deck.txt"]).bericht_server)

    def test_launcher_keeps_the_analysis_open(self):
        bat = (pathlib.Path(__file__).resolve().parent.parent / "draftgott.bat").read_text(encoding="utf-8")
        analyse = bat[bat.index(":analyse"):bat.index(":drafthelper")]
        self.assertIn("--bericht-server", analyse)


if __name__ == "__main__":
    unittest.main()
