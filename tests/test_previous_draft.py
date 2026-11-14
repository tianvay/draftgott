"""Live-Draft nach einem Neustart von draftgott, wenn Arena zwischendurch neu gestartet wurde: der Draft steht dann nur
noch in Player-prev.log, Deck und Matches in Player.log. Deck und Draft-Bilanz sollen trotzdem erscheinen statt
"Noch kein Draft im Protokoll" (Nutzer 14.11.2026)."""
import pathlib
import tempfile
import unittest

from components import livedraft as ld
from tests.test_draftstats import auth_line, deck_line, end_line, start_line
from tests.test_livedraft import NAMES, fake_fetch, notify, pick

DRAFT = [notify(1, [101, 102, 103]), pick([101]), notify(2, [102, 103]), pick([102]), notify(3, [103]),
         pick([103])]
DECK = deck_line([(101, 1), (102, 1), (103, 1)], [])


class PreviousDraftTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        d = pathlib.Path(self.dir.name)
        self.log, self.prev, self.pool = d / "Player.log", d / "Player-prev.log", d / "_livedraft.txt"
        self.stats = d / "draftstatistik.json"

    def tearDown(self):
        self.dir.cleanup()

    def start(self, prev_lines, cur_lines):
        """Wie der Drafthelper beim Start: vorheriges Protokoll fuer die Statistik, aktuelles lesen, dann den Draft
        aus dem vorherigen Protokoll uebernehmen, falls das aktuelle keinen hat."""
        self.prev.write_text("".join(x + "\n" for x in prev_lines), encoding="utf-8")
        self.log.write_text("".join(x + "\n" for x in cur_lines), encoding="utf-8")
        live = ld.LiveDraft(self.log, self.pool, names=NAMES, fetch=fake_fetch, stats=self.stats)
        live.read_previous(self.prev)
        live.step()
        live.restore_previous(self.prev)
        return live

    def test_deck_and_record_after_restart(self):
        live = self.start([auth_line(), *DRAFT],
                          [auth_line(), DECK, start_line("m1"), end_line("m1", [2, 2], 2),
                           start_line("m2"), end_line("m2", [1, 1], 1)])
        snap = live.snapshot({}, {}, None)
        self.assertNotEqual(snap["status"], "idle")
        self.assertEqual(snap["picks"], ["Test Bear", "Test Hasty", "Test Spell"])
        self.assertTrue(snap["deck"]["ready"])
        self.assertEqual(snap["deckinfo"]["source"], "arena")
        self.assertEqual((snap["deckinfo"]["record"]["wins"], snap["deckinfo"]["record"]["losses"]), (1, 1))

    def test_current_draft_wins(self):
        live = self.start(DRAFT, [notify(1, [201, 202], draft="d2")])
        snap = live.snapshot({}, {}, None)
        self.assertEqual(snap["status"], "pack")
        self.assertEqual(snap["picks"], [])
        self.assertEqual({c["name"] for c in snap["pack"]}, {"Test Gold", "Test Big"})

    def test_pool_file_is_not_rewritten(self):
        self.pool.write_text("Deck\n1 Test Bear\n\nSideboard\n1 Test Hasty\n", encoding="utf-8")
        self.start(DRAFT, ["nichts"])
        self.assertEqual(self.pool.read_text(encoding="utf-8"), "Deck\n1 Test Bear\n\nSideboard\n1 Test Hasty\n")

    def test_no_previous_log(self):
        self.log.write_text("nichts\n", encoding="utf-8")
        live = ld.LiveDraft(self.log, self.pool, names=NAMES, fetch=fake_fetch)
        live.step()
        self.assertFalse(live.restore_previous(self.prev))
        self.assertEqual(live.snapshot({}, {}, None)["status"], "idle")

    def test_previous_log_without_draft(self):
        live = self.start(["nichts"], ["nichts"])
        self.assertEqual(live.snapshot({}, {}, None)["status"], "idle")

    def test_new_draft_after_restore_starts_fresh(self):
        live = self.start(DRAFT, ["nichts"])
        with self.log.open("a", encoding="utf-8") as fh:
            fh.write(notify(1, [201, 202], draft="d2") + "\n")
        live.step()
        snap = live.snapshot({}, {}, None)
        self.assertEqual(snap["picks"], [])
        self.assertEqual(snap["status"], "pack")


if __name__ == "__main__":
    unittest.main()
