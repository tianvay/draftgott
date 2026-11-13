"""Englische Drafthelper-Seite und englische Berichte: JavaScript bleibt gueltig, keine deutschen Reste."""
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

from components import drafthelper as dh
from tests.i18n_check import english, german_leftovers


def node_check(html):
    scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
    with tempfile.TemporaryDirectory() as d:
        path = pathlib.Path(d) / "page.js"
        path.write_text("\n".join(scripts), encoding="utf-8")
        return subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=30)


class EnglishPageTests(unittest.TestCase):
    def setUp(self):
        with english():
            self.page = dh.render_page()

    @unittest.skipUnless(shutil.which("node"), "Node.js nicht installiert")
    def test_english_page_script_is_valid_javascript(self):
        out = node_check(self.page)
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_english_page_keeps_the_element_ids(self):
        script = "\n".join(re.findall(r"<script>(.*?)</script>", self.page, re.S))
        wanted = set(re.findall(r'\$\("([A-Za-z0-9_]+)"\)', script))
        present = set(re.findall(r'id="([A-Za-z0-9_]+)"', self.page))
        self.assertEqual(wanted - present, set())

    def test_whole_english_page_has_no_german(self):
        # "im" ist hier die JavaScript-Variable fuer Kartenbilder
        page = re.sub(r"\bim\b(?=[.=;])|const im\b|\(im\)", " ", self.page)
        self.assertEqual(german_leftovers(page), [])
        self.assertIn('<html lang="en">', self.page)

    def test_german_page_unchanged(self):
        self.assertEqual(dh.render_page(), dh.render_page())
        self.assertIn('<html lang="de">', dh.render_page())

    def test_proposal_variant_name(self):
        pool = []
        proposal = {"deck": {"Plains": 8}}
        with english():
            en = dh.variant_entries(pool, {}, {}, {}, proposal=proposal)
        de = dh.variant_entries(pool, {}, {}, {}, proposal=proposal)
        self.assertEqual(en[-1]["name"], "Proposal")
        self.assertEqual(de[-1]["name"], "Vorschlag")


if __name__ == "__main__":
    unittest.main()
