"""Umschalter Splash/NoSplash an jeder Detail-Ueberschrift des Berichts (nur bei mehreren Varianten)."""
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

import mtg_sim
from components.report import SWITCH_JS
from tests.fixtures import CARDS, args_for

CORE = {"Plains": 14, "Mountain": 3, "Test Bear": 21}


def build(entries):
    with mock.patch.object(mtg_sim, "fetch_cards_cached", lambda n, refresh=False: CARDS):
        return mtg_sim.simulate_entries(entries, args_for(["deck.txt", "--sims", "100"]), progress=lambda m: None)


def two_variants():
    splash, nosplash = dict(CORE, **{"Test Hasty": 2}), dict(CORE, **{"Test Bear": 23})
    return [{"path": "", "name": "Splash", "deck": splash, "parts": [("Core", dict(CORE)), ("Splash", {"Test Hasty": 2})],
             "cats": {}, "role": "splash"},
            {"path": "", "name": "NoSplash", "deck": nosplash,
             "parts": [("Core", dict(CORE)), ("NoSplash", {"Test Bear": 2})], "cats": {}, "role": "nosplash"}]


class SwitchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = build(two_variants())
        cls.report = cls.html[:cls.html.index('id="view-help"')]

    def sections(self):
        return re.findall(r'<section id="([^"]+)"><h2>(.*?)</h2>', self.report, re.S)

    def test_every_detail_heading_has_a_switch(self):
        details = [(sid, h2) for sid, h2 in self.sections() if sid != "vergleich"]
        self.assertGreater(len(details), 10)
        for sid, h2 in details:
            with self.subTest(section=sid):
                self.assertIn('class="gsw"', h2)
                self.assertIn(">Splash</button>", h2)
                self.assertIn(">NoSplash</button>", h2)

    def test_switch_knows_its_section_and_marks_the_own_variant(self):
        h2 = dict(self.sections())["deck-1"]  # Abschnitt Deck der zweiten Variante
        self.assertIn('data-sec="deck"', h2)
        self.assertRegex(h2, r'<button type="button" data-g="1" data-sec="deck" class="on">NoSplash</button>')

    def test_comparison_has_no_switch(self):
        self.assertNotIn('class="gsw"', dict(self.sections())["vergleich"])

    def test_single_deck_has_no_switch(self):
        html = build([{"path": "", "name": "A", "deck": dict(CORE, **{"Test Bear": 23}), "parts": []}])
        self.assertNotIn('class="gsw"', html)


@unittest.skipUnless(shutil.which("node"), "Node.js nicht installiert")
class ScriptTests(unittest.TestCase):
    def test_script_syntax(self):
        code = re.sub(r"</?script>", "", SWITCH_JS)
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(code)
        out = subprocess.run(["node", "--check", f.name], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn(".gsw button", SWITCH_JS)


if __name__ == "__main__":
    unittest.main()
