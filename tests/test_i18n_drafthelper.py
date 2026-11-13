"""Englische Ausgabe des Python-Teils von components/drafthelper.py (Konsole und Meldungen an die Seite)."""
import contextlib
import io
import pathlib
import tempfile
import unittest
from unittest import mock

from components import drafthelper as dh
from components.i18n_en.drafthelper import EN
from tests.i18n_check import english, german_leftovers
from tests.test_drafthelper import load


def exit_text(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except SystemExit as e:
        return str(e.code)
    raise AssertionError("kein sys.exit")


def error_text(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except ValueError as e:
        return str(e)
    raise AssertionError("kein ValueError")


class DrafthelperPythonEnglish(unittest.TestCase):
    def test_dictionary_placeholders_match(self):
        import re
        for de, en in EN.items():
            self.assertEqual(sorted(re.findall(r"\{\w+\}", de)), sorted(re.findall(r"\{\w+\}", en)), de)

    def test_pool_missing(self):
        de = exit_text(dh.pool_path, "gibt_es_nicht_xyz.txt")
        with english():
            en = exit_text(dh.pool_path, "gibt_es_nicht_xyz.txt")
        self.assertIn("Kartenpool-Datei nicht gefunden", de)
        self.assertIn("Card pool file not found: gibt_es_nicht_xyz.txt", en)
        self.assertEqual(german_leftovers(en, allow=["Curse-Marred Demon"]), [])

    def test_load_pool_messages(self):
        def run():
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                load()
            return err.getvalue()
        de = run()
        with english():
            en = run()
        self.assertIn("Kartenpool:", de)
        self.assertIn("Card pool:", en)
        self.assertEqual(german_leftovers(en), [])

    def test_validation_errors(self):
        de = error_text(dh.parse_proposal_spec, {"colors": ["X"]})
        with english():
            en = error_text(dh.parse_proposal_spec, {"colors": ["X"]})
            en2 = error_text(dh.parse_proposal_spec, {"target": 5})
            en3 = error_text(dh.parse_proposal_spec, {"sort": "x"})
        self.assertEqual(de, "Unbekannte Farbe (erlaubt: W, U, B, R, G)")
        self.assertEqual(en, "Unknown color (allowed: W, U, B, R, G)")
        self.assertEqual(en2, "The target size must be between 10 and 200 cards")
        self.assertEqual(en3, "Unknown sort order")

    def test_parse_state_errors(self):
        cards, basics, _ = load()
        body = {"marks": []}
        de = error_text(dh.parse_state, body, cards)
        with english():
            en = error_text(dh.parse_state, body, cards)
        self.assertEqual(de, "Markierungen passen nicht zum Kartenpool")
        self.assertEqual(en, "Marks do not match the card pool")

    def test_job_messages(self):
        job = dh.Job()
        with english():
            job.start(lambda progress: "x")
            for _ in range(200):
                if job.status()["state"] == "done":
                    break
                import time
                time.sleep(0.01)
            self.assertEqual(job.status()["message"], "Done")
            job2 = dh.Job()
            job2.state = "idle"
            job2.start(lambda progress: (_ for _ in ()).throw(SystemExit()))
            for _ in range(200):
                if job2.status()["state"] == "error":
                    break
                import time
                time.sleep(0.01)
            self.assertEqual(job2.status()["message"], "Aborted")
        job3 = dh.Job()
        job3.start(lambda progress: "x")
        self.assertIn(job3.status()["state"], ("running", "done"))

    def test_render_page_options_and_lang(self):
        de = dh.render_page()
        with english():
            en = dh.render_page()
        self.assertIn('<html lang="de">', de)
        self.assertIn(">500 Kämpfe</option>", de)
        self.assertIn('<html lang="en">', en)
        self.assertIn(">500 battles</option>", en)
        self.assertNotIn("Kämpfe</option>", en)
        self.assertEqual(de, dh.render_page())

    def test_overlay_start_message(self):
        def run():
            err = io.StringIO()
            with mock.patch("subprocess.Popen", side_effect=OSError("boom")), contextlib.redirect_stderr(err):
                dh.start_overlay("http://x/")
            return err.getvalue()
        with english():
            self.assertEqual(run(), "Overlay could not be started: boom\n")
        self.assertEqual(run(), "Seitenfenster konnte nicht gestartet werden: boom\n")


if __name__ == "__main__":
    unittest.main()
