"""Original-Manasymbole (Scryfall-SVGs): Cache, Rueckfall ohne Netz, Einbettung in Bericht und Drafthelper."""
import io
import json
import pathlib
import tempfile
import unittest
import urllib.error
from unittest import mock

from components import html_base, symbols

SVG_R = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="50" fill="#f00"/></svg>'
SVG_W = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="50" fill="#ff0"/></svg>'
FAKE = {"R": SVG_R, "W": SVG_W, "2/W": SVG_W}


class WithSymbols(unittest.TestCase):
    def setUp(self):
        self._old = symbols.active()
        symbols.use(dict(FAKE))

    def tearDown(self):
        symbols.use(self._old)


class HtmlManaTests(WithSymbols):
    def test_known_symbol_uses_the_original_image(self):
        html = html_base.html_mana("R")
        self.assertIn("ms-R", html)
        self.assertIn('title="{R}"', html)
        self.assertNotIn(">R<", html)  # kein sichtbarer Buchstabe

    def test_hybrid_symbol_class(self):
        self.assertIn(symbols.css_class("2/W"), html_base.html_mana("2/W"))

    def test_unknown_symbol_falls_back_to_the_circle(self):
        self.assertIn(">G<", html_base.html_mana("G"))

    def test_costs_record_the_used_symbols(self):
        symbols.reset_used()
        html_base.html_cost("{2}{R}{R}")
        self.assertEqual(symbols.used(), {"2", "R"})

    def test_css_only_for_requested_symbols(self):
        css = symbols.symbol_css({"R"})
        self.assertIn(".ms-R{", css)
        self.assertIn("data:image/svg+xml;base64,", css)
        self.assertNotIn(".ms-W{", css)
        self.assertEqual(symbols.symbol_css({"G"}), "")


class WithoutSymbolsTests(unittest.TestCase):
    def setUp(self):
        self._old = symbols.active()
        symbols.use({})

    def tearDown(self):
        symbols.use(self._old)

    def test_fallback_is_the_old_circle(self):
        self.assertIn(">R<", html_base.html_mana("R"))
        self.assertNotIn("ms-", html_base.html_mana("R"))
        self.assertEqual(symbols.symbol_css({"R"}), "")


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.file = pathlib.Path(self.tmp.name) / "scryfall_symbols.json"
        self._old = symbols.active()
        self._err = mock.patch("sys.stderr", io.StringIO())
        self._err.start()

    def tearDown(self):
        self._err.stop()
        symbols.use(self._old)
        self.tmp.cleanup()

    def test_cache_is_used_without_network(self):
        self.file.write_text(json.dumps(FAKE), encoding="utf-8")
        with mock.patch.object(symbols, "SYMBOL_FILE", self.file), \
                mock.patch("urllib.request.urlopen", side_effect=AssertionError("kein Netz erwartet")):
            got = symbols.fetch_symbols()
        self.assertEqual(got, FAKE)
        self.assertEqual(symbols.active(), FAKE)

    def test_download_filters_mana_symbols_and_saves(self):
        listing = {"data": [
            {"symbol": "{R}", "svg_uri": "https://svgs.test/R.svg", "appears_in_mana_costs": True},
            {"symbol": "{T}", "svg_uri": "https://svgs.test/T.svg", "appears_in_mana_costs": False},
            {"symbol": "{HW}", "svg_uri": "https://svgs.test/HW.svg", "appears_in_mana_costs": True, "funny": True},
        ]}

        def fake_get(url):
            return json.dumps(listing).encode() if url.endswith("/symbology") else SVG_R.encode()

        with mock.patch.object(symbols, "SYMBOL_FILE", self.file), mock.patch.object(symbols, "_get", fake_get), \
                mock.patch.object(symbols, "PAUSE", 0):
            got = symbols.fetch_symbols()
        self.assertEqual(got, {"R": SVG_R})
        self.assertEqual(json.loads(self.file.read_text(encoding="utf-8")), {"R": SVG_R})

    def test_network_error_keeps_the_fallback(self):
        def broken(url):
            raise urllib.error.URLError("offline")

        with mock.patch.object(symbols, "SYMBOL_FILE", self.file), mock.patch.object(symbols, "_get", broken):
            got = symbols.fetch_symbols()
        self.assertEqual(got, {})
        self.assertFalse(self.file.exists())

    def test_refresh_downloads_again(self):
        self.file.write_text(json.dumps({"W": SVG_W}), encoding="utf-8")
        listing = {"data": [{"symbol": "{R}", "svg_uri": "https://svgs.test/R.svg", "appears_in_mana_costs": True}]}
        with mock.patch.object(symbols, "SYMBOL_FILE", self.file), mock.patch.object(
                symbols, "_get", lambda u: json.dumps(listing).encode() if u.endswith("/symbology") else SVG_R.encode()), \
                mock.patch.object(symbols, "PAUSE", 0):
            self.assertEqual(symbols.fetch_symbols(refresh=True), {"R": SVG_R})


class EmbeddingTests(WithSymbols):
    def test_report_embeds_only_used_symbols(self):
        import mtg_sim
        from tests.fixtures import CARDS, args_for
        entries = [{"path": "", "name": "A", "deck": {"Mountain": 17, "Test Hasty": 23}, "parts": []}]
        with mock.patch.object(mtg_sim, "fetch_cards_cached", lambda n, refresh=False: CARDS), \
                mock.patch.object(symbols, "fetch_symbols", lambda refresh=False: symbols.active()):
            html = mtg_sim.simulate_entries(entries, args_for(["deck.txt", "--sims", "100"]), progress=lambda m: None)
        self.assertIn(".ms-R{", html)
        self.assertNotIn(".ms-2_W{", html)
        self.assertIn('class="m ms ms-R"', html)

    def test_drafthelper_page_contains_color_symbols(self):
        from components import drafthelper as dh
        page = dh.render_page()
        self.assertIn(".ms-R{", page)
        self.assertIn(".ms-W{", page)
        self.assertIn('const SYMBOLS=["W","R"]', page)


if __name__ == "__main__":
    unittest.main()
