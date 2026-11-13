"""Konsolenmeldungen und Seitentexte (mtg_sim, livedraft, report_server, scryfall, symbols) auf Englisch."""
import contextlib
import io
import json
import pathlib
import tempfile
import unittest
import urllib.error
from unittest import mock

import mtg_sim
from components import livedraft as ld
from components import report_server as rs
from components import scryfall, symbols
from components.cli import parse_args
from components.i18n_en.console import EN
from tests.i18n_check import english, german_leftovers
from tests.test_livedraft import NAMES, LiveTestCase, fake_fetch


def captured(fn, *a, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        try:
            fn(*a, **kw)
        except SystemExit as e:
            buf.write(str(e.code))
        except ValueError as e:
            buf.write(str(e))
    return buf.getvalue()


class ConsoleEnglish(LiveTestCase):
    def snaps(self):
        out = []
        out.append(self.live.snapshot({}, {}, None)["message"])  # nolog
        self.write("[UnityCrossThreadLogger]Client.SceneChange {}")
        self.live.step()
        out.append(self.live.snapshot({}, {}, None)["message"])  # idle
        try:
            self.live.apply_deck()
        except ValueError as e:
            out.append(str(e))
        return out

    def test_live_messages(self):
        de = self.snaps()
        self.log.unlink()
        self.live = ld.LiveDraft(self.log, self.pool, names=NAMES, fetch=fake_fetch)
        with english():
            en = self.snaps()
        self.assertEqual(len(en), 3)
        for text in en:
            self.assertEqual(german_leftovers(text.replace(str(self.log), "")), [], text)
        self.assertNotEqual(de, en)
        self.assertIn("Arena log not found", en[0])
        self.assertIn("Detailed Logs", en[1])

    def test_print_messages(self):
        calls = [
            lambda: scryfall.post_collection and print(ld.t("WARNUNG: Karte nicht gefunden: {name}", name="X")),
            lambda: ld.default_names(self.log),
        ]
        with english():
            text = captured(calls[1])
            self.assertIn("Arena card database", text)
            self.assertEqual(german_leftovers(text.replace(str(self.log), "")), [], text)

    def test_scryfall_and_symbols_errors(self):
        err = urllib.error.URLError("x")
        with english():
            with mock.patch.object(scryfall, "post_collection", side_effect=err):
                text = captured(scryfall.fetch_printing_images, [("zzz", "1")])
            self.assertIn("Could not load card images", text)
            with mock.patch.object(symbols, "_get", side_effect=err):
                text += captured(symbols.fetch_symbols, True)
            self.assertEqual(german_leftovers(text), [], text)

    def test_mtg_sim_exits(self):
        args = parse_args(["deck.txt"])
        with english():
            text = captured(mtg_sim.load_enemy, "nicht_da_xyz.txt")
            text += captured(mtg_sim.build_deck, {"name": "D", "deck": {}}, {}, args)
            msgs = []
            with mock.patch.object(mtg_sim, "fetch_cards_cached", side_effect=urllib.error.URLError("e")):
                text += captured(mtg_sim.simulate_entries, [{"deck": {"A": 1}}], args, msgs.append)
            text += " ".join(msgs)
            with tempfile.TemporaryDirectory() as d:
                args.ausgabe = str(pathlib.Path(d) / "r.html")
                text += captured(mtg_sim.save_report, "<html>", args)
        self.assertIn("Opponent deck not found", text)
        self.assertIn("Too few cards", text)
        self.assertIn("Scryfall not reachable", text)
        self.assertIn("Report saved", text)
        self.assertEqual(german_leftovers(text), [], text)

    def test_report_server_pages(self):
        app = rs.make_app("<html></html>", [], None, None, None)
        server = rs.start(app, 0)
        try:
            import urllib.request
            base = f"http://127.0.0.1:{server.server_address[1]}"
            with english():
                body = urllib.request.urlopen(base + "/battle").read().decode("utf-8")
                try:
                    urllib.request.urlopen(base + "/nix")
                except urllib.error.HTTPError as e:
                    nf = e.read().decode("utf-8")
            de = urllib.request.urlopen(base + "/battle").read().decode("utf-8")
        finally:
            server.shutdown()
            server.server_close()
        self.assertIn("No battle report yet", body)
        self.assertEqual(nf, "Not found")
        self.assertIn("Noch kein Kampfbericht", de)

    def test_german_unchanged(self):
        self.assertIn("Arena-Protokoll nicht gefunden", self.live.snapshot({}, {}, None)["message"])

    def test_every_key_has_placeholders_matching(self):
        import re
        for de, en in EN.items():
            self.assertEqual(sorted(re.findall(r"\{\w+\}", de)), sorted(re.findall(r"\{\w+\}", en)), de)


if __name__ == "__main__":
    unittest.main()
