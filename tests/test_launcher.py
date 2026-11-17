"""Launcher (draftgott.pyw, Nutzer 17.11.2026): Fenster statt draftgott.bat, nur Live-Draft, Setauswertung und Set
bewerten als Startoptionen; Drafthelper und Analyse laufen nur noch aus dem Live-Draft heraus."""
import json
import pathlib
import tempfile
import threading
import unittest
import urllib.request

from components import i18n, launcher
from components.i18n import t
from tests.i18n_check import english

PY = "/usr/bin/python3"


class Modes(unittest.TestCase):
    def test_only_live_and_set_pages(self):
        self.assertEqual(launcher.MODES, ("live", "setreport", "setrate"))

    def test_live_command(self):
        cmd = launcher.command("live", "de", python=PY)
        self.assertEqual(cmd[0], PY)
        self.assertTrue(cmd[1].endswith("mtg_sim.py"))
        self.assertEqual(cmd[2:], ["--drafthelper", "_livedraft.txt", "--live", "--lang", "de"])

    def test_live_with_other_arena_log(self):
        cmd = launcher.command("live", "en", python=PY, arena_log="/home/x/Player.log")
        self.assertEqual(cmd[-4:], ["--lang", "en", "--arena-log", "/home/x/Player.log"])

    def test_set_report_with_and_without_set(self):
        self.assertEqual(launcher.command("setreport", "de", python=PY)[2:], ["--setauswertung", "--lang", "de"])
        self.assertEqual(launcher.command("setreport", "de", python=PY, set_code="trk")[2:],
                         ["--setauswertung", "TRK", "--lang", "de"])

    def test_set_rating(self):
        self.assertEqual(launcher.command("setrate", "en", python=PY)[2:], ["--set-bewerten", "--lang", "en"])

    def test_draft_helper_and_analysis_are_no_start_options(self):
        for mode in ("drafthelper", "analyse", "turnier", ""):
            with self.assertRaises(ValueError):
                launcher.command(mode, "de", python=PY)

    def test_bad_set_code_is_refused(self):
        with self.assertRaises(ValueError):
            launcher.command("setreport", "de", python=PY, set_code="TR K; rm")


class ArenaLog(unittest.TestCase):
    def test_candidates_windows(self):
        c = launcher.arena_log_candidates("C:/Users/a", "win32")
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0].parts[-4:], ("LocalLow", "Wizards Of The Coast", "MTGA", "Player.log"))

    def test_candidates_linux_include_steam_proton(self):
        c = [str(p).replace("\\", "/") for p in launcher.arena_log_candidates("/home/a", "linux")]
        self.assertTrue(any("compatdata/2141910" in p for p in c))
        self.assertTrue(all(p.endswith("MTGA/Player.log") for p in c))

    def test_find_first_existing(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(launcher.find_arena_log(d, "linux"))
            p = launcher.arena_log_candidates(d, "linux")[1]
            p.parent.mkdir(parents=True)
            p.write_text("x", encoding="utf-8")
            self.assertEqual(launcher.find_arena_log(d, "linux"), p)

    def test_detailed_logs(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "Player.log"
            p.write_text("Mono path\nDETAILED LOGS: ENABLED\nmore\n", encoding="utf-8")
            self.assertIs(launcher.detailed_logs(p), True)
            p.write_text("DETAILED LOGS: DISABLED\n", encoding="utf-8")
            self.assertIs(launcher.detailed_logs(p), False)
            p.write_text("nothing here\n", encoding="utf-8")
            self.assertIsNone(launcher.detailed_logs(p))
            self.assertIsNone(launcher.detailed_logs(pathlib.Path(d) / "fehlt.log"))


class Stats(unittest.TestCase):
    def test_draft_counts_most_first(self):
        data = {"drafts": [{"set": "TRK"}, {"set": "fra"}, {"set": "TRK"}, {"set": ""}, {}]}
        self.assertEqual(launcher.draft_counts(data), [("TRK", 2), ("FRA", 1)])

    def test_enemy_deck_count(self):
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "wc32").mkdir()
            for name in ("a.txt", "wc32/b.txt", "c.json"):
                (pathlib.Path(d) / name).write_text("x", encoding="utf-8")
            self.assertEqual(launcher.enemy_deck_count(d), 2)
            self.assertEqual(launcher.enemy_deck_count(pathlib.Path(d) / "fehlt"), 0)


class Browser(unittest.TestCase):
    def test_app_window_with_edge_on_windows(self):
        exe = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
        cmd = launcher.browser_command("http://127.0.0.1:8770/", "P", "win32", which=lambda n: None,
                                       exists=lambda p: str(p).replace("\\", "/") == exe)
        self.assertEqual(cmd[0].replace("\\", "/"), exe)
        self.assertIn("--app=http://127.0.0.1:8770/", cmd)
        self.assertIn("--user-data-dir=P", cmd)
        self.assertTrue(any(a.startswith("--window-size=") for a in cmd))

    def test_chromium_on_linux(self):
        cmd = launcher.browser_command("http://x/", "P", "linux",
                                       which=lambda n: "/usr/bin/chromium" if n == "chromium" else None,
                                       exists=lambda p: False)
        self.assertEqual(cmd[0], "/usr/bin/chromium")

    def test_no_app_browser(self):
        self.assertIsNone(launcher.browser_command("http://x/", "P", "linux", which=lambda n: None,
                                                   exists=lambda p: False))


class Idle(unittest.TestCase):
    def test_stays_while_pinged(self):
        self.assertFalse(launcher.should_exit(now=100, started=0, last=90, bye=None))

    def test_exits_after_long_silence(self):
        self.assertTrue(launcher.should_exit(now=1000, started=0, last=100, bye=None))

    def test_exits_soon_after_goodbye_unless_reloaded(self):
        self.assertFalse(launcher.should_exit(now=101, started=0, last=99, bye=100))
        self.assertTrue(launcher.should_exit(now=110, started=0, last=99, bye=100))
        self.assertFalse(launcher.should_exit(now=110, started=0, last=105, bye=100))  # Seite neu geladen

    def test_waits_for_first_window(self):
        self.assertFalse(launcher.should_exit(now=60, started=0, last=None, bye=None))
        self.assertTrue(launcher.should_exit(now=400, started=0, last=None, bye=None))


class Desktop(unittest.TestCase):
    def test_desktop_entry(self):
        text = launcher.desktop_entry("/opt/draftgott", "/usr/bin/python3")
        self.assertIn("[Desktop Entry]", text)
        self.assertIn('Exec="/usr/bin/python3" "/opt/draftgott/draftgott.pyw"', text)
        self.assertIn("Icon=/opt/draftgott/assets/draftgott.svg", text)
        self.assertIn("Type=Application", text)

    def test_install_desktop_entry(self):
        with tempfile.TemporaryDirectory() as d:
            p = launcher.install_desktop_entry(home=d, root="/opt/draftgott", python="/usr/bin/python3")
            self.assertEqual(p.name, "draftgott.desktop")
            self.assertIn(".local", p.parts)
            self.assertIn("draftgott.pyw", p.read_text(encoding="utf-8"))

    def test_icon_exists(self):
        self.assertTrue((launcher.ROOT / "assets" / "draftgott.svg").is_file())
        self.assertTrue((launcher.ROOT / "draftgott.pyw").is_file())


STATUS = {"python": "3.11.4", "system": "Windows", "arena_log": "C:/x/Player.log", "arena_age": 120,
          "detailed": False, "drafts": [("TRK", 42), ("FRA", 15)], "enemy_decks": 31, "jobs": {},
          "linux": False}


class Page(unittest.TestCase):
    def test_german_page(self):
        page = launcher.render_page(STATUS)
        self.assertIn("Live-Draft", page)
        self.assertIn("Setauswertung", page)
        self.assertIn("Set bewerten", page)
        self.assertIn(t("Goldfish"), page)
        self.assertNotIn('data-mode="drafthelper"', page)
        self.assertNotIn('data-mode="analyse"', page)
        self.assertIn('data-mode="live"', page)
        self.assertIn("TRK", page)
        self.assertIn("Detailed Logs", page)
        self.assertIn("--dg-accent", page)  # gemeinsames Aussehen aus components/theme.py

    def test_set_choice_for_report(self):
        page = launcher.render_page(STATUS)
        self.assertIn('<option value="TRK"', page)
        self.assertIn('<option value="FRA"', page)

    def test_linux_offers_menu_entry(self):
        self.assertNotIn('id="desktop"', launcher.render_page(STATUS))
        self.assertIn('id="desktop"', launcher.render_page(dict(STATUS, linux=True, system="Linux")))

    def test_english_page(self):
        with english():
            page = launcher.render_page(STATUS)
        self.assertIn('lang="en"', page)
        self.assertIn("Set report", page)
        self.assertIn("Rate a set", page)
        self.assertNotIn("Setauswertung", page)


class Server(unittest.TestCase):
    def setUp(self):
        self.started = []
        self.tmp = tempfile.TemporaryDirectory()
        state = launcher.State(settings=pathlib.Path(self.tmp.name) / "launcher.json",
                               spawn=lambda cmd, mode: self.started.append((mode, cmd)) or launcher.FakeJob())
        self.server = launcher.make_server(state, port=0)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()
        i18n.set_lang("de")  # State waehlt die Sprache des Systems

    def get(self, path):
        with urllib.request.urlopen(self.url + path, timeout=5) as r:
            return r.read().decode("utf-8")

    def post(self, path, body):
        req = urllib.request.Request(self.url + path, data=json.dumps(body).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode("utf-8"))

    def test_page_and_status(self):
        self.assertIn('data-mode="live"', self.get("/"))
        st = json.loads(self.get("/api/status"))
        self.assertIn("python", st)
        self.assertIn("jobs", st)
        self.assertEqual(json.loads(self.get("/api/ping"))["app"], "draftgott")

    def test_start_live(self):
        r = self.post("/api/start", {"mode": "live"})
        self.assertTrue(r["ok"])
        self.assertEqual(self.started[0][0], "live")
        self.assertIn("--live", self.started[0][1])

    def test_refuses_draft_helper(self):
        r = self.post("/api/start", {"mode": "drafthelper"})
        self.assertFalse(r["ok"])
        self.assertEqual(self.started, [])

    def test_no_second_live_while_running(self):
        self.post("/api/start", {"mode": "live"})
        r = self.post("/api/start", {"mode": "live"})
        self.assertFalse(r["ok"])
        self.assertEqual(len(self.started), 1)

    def test_language_is_saved(self):
        self.assertTrue(self.post("/api/lang", {"lang": "en"})["ok"])
        try:
            saved = json.loads((pathlib.Path(self.tmp.name) / "launcher.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["lang"], "en")
            self.assertIn('lang="en"', self.get("/"))
            self.post("/api/start", {"mode": "setrate"})
            self.assertEqual(self.started[-1][1][-2:], ["--lang", "en"])
        finally:
            self.post("/api/lang", {"lang": "de"})


if __name__ == "__main__":
    unittest.main()
