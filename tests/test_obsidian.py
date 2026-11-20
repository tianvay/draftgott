"""Obsidian-Export (components/obsidian.py): Drafts der Draft-Statistik als verlinkte Markdown-Notizen."""
import json
import pathlib
import re
import subprocess
import tempfile
import unittest

from components import obsidian
from components.cli import parse_args
from tests.i18n_check import english, german_leftovers

ROOT = pathlib.Path(__file__).resolve().parent.parent

LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]*)?\]\]")


def _rec(event="PickTwoDraft_TRK_20261110", started="2026-11-10", picks=None, deck=None, matches=None):
    return {"event": event, "set": "TRK", "draft_id": None, "started": started,
            "picks": picks if picks is not None else ["Kirk: Captain", "Spock?", "Plains", "#123", "Spock?"],
            "pick_sizes": [14, 14, 13, 13, 12],
            "deck": deck if deck is not None else {"main": {"Kirk: Captain": 1, "Spock?": 2, "Plains": 9},
                                                     "side": {"Tribble": 1}},
            "matches": matches if matches is not None else [
                {"id": "m1", "team": 1, "deck": {"Kirk: Captain": 1, "Spock?": 2}, "games": [True, False, True],
                 "win": True},
                {"id": "m2", "team": 1, "deck": {"Kirk: Captain": 1, "Spock?": 2}, "games": [False, False],
                 "win": False},
                {"id": "m3", "team": 1, "deck": {}, "games": [], "win": None}]}


DATA = {"version": 1, "drafts": [_rec(), _rec(event="QuickDraft_TRK_20261119", started="2026-11-10",
                                               picks=["Tribble"], deck={"main": {"Tribble": 1}, "side": {}},
                                               matches=[])]}
CARDS = {
    "Kirk: Captain": {"name": "Kirk: Captain", "set": "trk", "colors": ["W", "U"], "mana_cost": "{1}{W}{U}",
                      "type_line": "Legendary Creature — Human", "rarity": "rare", "oracle_text": "Vigilance"},
    "Spock?": {"name": "Spock?", "set": "trk", "colors": ["U"], "mana_cost": "{2}{U}", "type_line": "Creature",
               "rarity": "uncommon", "oracle_text": "Flying"},
}
ASSIGN = {"Kirk: Captain": ["WU"], "Spock?": ["WU", "UB"]}
RATINGS = {"Kirk: Captain": "matchwinner", "Spock?": "playable"}


def notes(data=DATA):
    return obsidian.build_notes(data, CARDS, ASSIGN, RATINGS)


class SafeNameTests(unittest.TestCase):
    def test_windows_and_link_characters_replaced(self):
        self.assertEqual(obsidian.safe_name("Kirk: Captain"), "Kirk - Captain")
        self.assertEqual(obsidian.safe_name("Spock?"), "Spock")
        self.assertEqual(obsidian.safe_name('A/B\\C*D"E<F>G|H#I^J[K]L'), "A-B-C-D-E-F-G-H-I-J-K-L")
        self.assertEqual(obsidian.safe_name("Fire // Ice"), "Fire - Ice")
        self.assertEqual(obsidian.safe_name("Name. "), "Name")

    def test_link_uses_alias_when_name_changes(self):
        self.assertEqual(obsidian.link("Tribble"), "[[Tribble]]")
        self.assertEqual(obsidian.link("Kirk: Captain"), "[[Kirk - Captain|Kirk: Captain]]")


class BuildNotesTests(unittest.TestCase):
    def setUp(self):
        self.notes = notes()

    def test_folders_and_files(self):
        paths = set(self.notes)
        self.assertIn("Sets/TRK.md", paths)
        self.assertIn("Cards/Kirk - Captain.md", paths)
        self.assertIn("Cards/Spock.md", paths)
        self.assertIn("Cards/Tribble.md", paths)
        self.assertIn("Archetypes/TRK WU Spacecraft.md", paths)
        drafts = sorted(p for p in paths if p.startswith("Drafts/"))
        self.assertEqual(drafts, ["Drafts/2026-11-10 TRK Pick One.md", "Drafts/2026-11-10 TRK Pick Two.md"])

    def test_no_notes_for_basics_and_unknown_cards(self):
        self.assertFalse(any("Plains" in p or "#123" in p or "123" in p for p in self.notes))

    def test_every_link_resolves(self):
        targets = {pathlib.PurePosixPath(p).stem for p in self.notes}
        for path, text in self.notes.items():
            for target in LINK_RE.findall(text):
                self.assertIn(target, targets, f"{path}: [[{target}]] ohne Notiz")

    def test_draft_note(self):
        text = self.notes["Drafts/2026-11-10 TRK Pick Two.md"]
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("draftgott: generated", text)
        self.assertIn("wins: 1", text)
        self.assertIn("losses: 1", text)
        self.assertIn("archetype: WU", text)
        self.assertIn("[[TRK]]", text)
        self.assertIn("[[TRK WU Spacecraft]]", text)
        self.assertIn("2 [[Spock|Spock?]]", text)
        self.assertIn("9 Plains", text)
        self.assertIn("1 [[Tribble]]", text)  # Sideboard
        self.assertIn("Sieg 2-1", text)
        self.assertIn("Niederlage 0-2", text)
        self.assertIn("läuft", text)
        self.assertIn(obsidian.MARKER, text)

    def test_picks_grouped_by_pack(self):
        rec = _rec(picks=["Spock?", "Kirk: Captain", "Spock?"])
        rec["pick_sizes"] = [14, 13, 14]
        text = obsidian.build_notes({"drafts": [rec]}, CARDS, ASSIGN, RATINGS)["Drafts/2026-11-10 TRK Pick Two.md"]
        self.assertIn("Pack 1: [[Spock|Spock?]], [[Kirk - Captain|Kirk: Captain]]", text)
        self.assertIn("Pack 2: [[Spock|Spock?]]", text)

    def test_card_note(self):
        text = self.notes["Cards/Kirk - Captain.md"]
        self.assertIn("aliases: [\"Kirk: Captain\"]", text)
        self.assertIn("rating: Matchwinner", text)
        self.assertIn("[[TRK WU Spacecraft]]", text)
        self.assertIn("{1}{W}{U}", text)
        self.assertIn("Vigilance", text)
        self.assertIn("Games 2-3", text)  # 2-1 und 0-2

    def test_card_note_with_unknown_pair_shows_pair_text(self):
        text = self.notes["Cards/Spock.md"]
        self.assertIn("[[TRK WU Spacecraft]]", text)
        self.assertIn("[[TRK UB Dilemmas]]", text)

    def test_set_and_archetype_notes(self):
        st = self.notes["Sets/TRK.md"]
        self.assertIn("Drafts: 2", st)
        self.assertIn("[[TRK WU Spacecraft]]", st)
        arch = self.notes["Archetypes/TRK WU Spacecraft.md"]
        self.assertIn("[[TRK]]", arch)
        self.assertIn("[[Kirk - Captain|Kirk: Captain]]", arch)

    def test_same_day_same_format_numbered(self):
        data = {"drafts": [_rec(), _rec()]}
        drafts = sorted(p for p in obsidian.build_notes(data, CARDS, ASSIGN, RATINGS) if p.startswith("Drafts/"))
        self.assertEqual(drafts, ["Drafts/2026-11-10 TRK Pick Two (2).md", "Drafts/2026-11-10 TRK Pick Two.md"])

    def test_guest_card_belongs_to_draft_set(self):
        cards = dict(CARDS, Tribble={"name": "Tribble", "set": "mh3", "colors": ["W"], "rarity": "common"})
        out = obsidian.build_notes(DATA, cards, ASSIGN, RATINGS)
        text = out["Cards/Tribble.md"]
        self.assertIn("set: TRK", text)
        self.assertIn("[[TRK]]", text)
        self.assertNotIn("[[MH3]]", text)
        self.assertIn("MH3", text)  # Druck aus einem anderen Set als Text
        self.assertNotIn("Sets/MH3.md", out)

    def test_without_card_data_and_archetypes(self):
        rec = _rec(event="PremierDraft_XYZ_20261101")
        rec["set"] = "XYZ"
        out = obsidian.build_notes({"drafts": [rec]}, {}, {}, {})
        self.assertIn("Cards/Spock.md", out)
        self.assertFalse(any(p.startswith("Archetypes/") for p in out))
        self.assertIn("Sets/XYZ.md", out)


class WriteVaultTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = pathlib.Path(self.tmp.name) / "vault"

    def tearDown(self):
        self.tmp.cleanup()

    def test_second_run_writes_nothing(self):
        first = obsidian.write_vault(self.vault, notes())
        self.assertEqual(first["written"], len(notes()))
        second = obsidian.write_vault(self.vault, notes())
        self.assertEqual(second["written"], 0)

    def test_own_notes_below_marker_survive(self):
        obsidian.write_vault(self.vault, notes())
        f = self.vault / "Cards" / "Spock.md"
        f.write_text(f.read_text(encoding="utf-8") + "Meine Idee: immer nehmen.\n", encoding="utf-8")
        data = json.loads(json.dumps(DATA))
        data["drafts"].append(_rec(started="2026-11-12"))
        obsidian.write_vault(self.vault, notes(data))
        text = f.read_text(encoding="utf-8")
        self.assertIn("Meine Idee: immer nehmen.", text)
        self.assertEqual(text.count(obsidian.MARKER), 1)

    def test_foreign_files_untouched(self):
        own = self.vault / "Cards" / "Spock.md"
        own.parent.mkdir(parents=True)
        own.write_text("# Meine eigene Notiz\n", encoding="utf-8")
        res = obsidian.write_vault(self.vault, notes())
        self.assertEqual(own.read_text(encoding="utf-8"), "# Meine eigene Notiz\n")
        self.assertEqual(res["skipped"], 1)

    def test_graph_settings_only_when_missing(self):
        obsidian.export(DATA, self.vault, CARDS, ASSIGN, RATINGS)
        graph = self.vault / ".obsidian" / "graph.json"
        self.assertTrue(json.loads(graph.read_text(encoding="utf-8"))["colorGroups"])
        graph.write_text("{}", encoding="utf-8")
        obsidian.export(DATA, self.vault, CARDS, ASSIGN, RATINGS)
        self.assertEqual(graph.read_text(encoding="utf-8"), "{}")

    def test_export_reports_counts(self):
        res = obsidian.export(DATA, self.vault, CARDS, ASSIGN, RATINGS)
        self.assertEqual(res["notes"], len(notes()))
        self.assertEqual(res["written"], len(notes()))


class AutoExportTests(unittest.TestCase):
    def test_run_now_reads_files_and_writes_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            (tmp / "stats.json").write_text(json.dumps(DATA), encoding="utf-8")
            (tmp / "ratings.json").write_text(json.dumps(RATINGS), encoding="utf-8")
            (tmp / "arch.json").write_text(json.dumps(ASSIGN), encoding="utf-8")
            auto = obsidian.AutoExport(tmp / "stats.json", tmp / "ratings.json", tmp / "arch.json", tmp / "vault",
                                       cards=lambda names: CARDS)
            res = auto.run_now()
            self.assertGreater(res["written"], 0)
            self.assertTrue((tmp / "vault" / "Sets" / "TRK.md").is_file())
            self.assertIn("rating: Matchwinner", (tmp / "vault" / "Cards" / "Kirk - Captain.md").read_text(
                encoding="utf-8"))

    def test_errors_do_not_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            blocker = tmp / "vault"
            blocker.write_text("keine Mappe", encoding="utf-8")  # Datei statt Ordner
            (tmp / "stats.json").write_text(json.dumps(DATA), encoding="utf-8")
            auto = obsidian.AutoExport(tmp / "stats.json", tmp / "r.json", tmp / "a.json", blocker,
                                       cards=lambda names: {})
            self.assertIsNone(auto.run_now())


class LiveHookTests(unittest.TestCase):
    def test_live_draft_calls_on_stats_when_statistics_change(self):
        from components import livedraft as ld
        from tests.fixtures import CARDS
        from tests.test_draftstats import auth_line
        from tests.test_enemy_autosave import DECK, DRAFT, INFO
        names = {g: {k: v for k, v in i.items() if k != "colors"} for g, i in INFO.items()}
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            log = d / "Player.log"
            log.write_text("\n".join([auth_line(), *DRAFT, DECK]) + "\n", encoding="utf-8")
            live = ld.LiveDraft(log, d / "pool.txt", names=names, fetch=lambda n, refresh=False: CARDS,
                                stats=d / "s.json")
            calls = []
            live.on_stats = lambda: calls.append(1)
            live.step()
            self.assertEqual(len(calls), 1)  # einmal je Durchgang, nicht je Zeile
            live.step()  # nichts Neues im Protokoll
            self.assertEqual(len(calls), 1)

    def test_drafthelper_wires_auto_export(self):
        src = (ROOT / "components" / "drafthelper.py").read_text(encoding="utf-8")
        self.assertIn("obsidian.AutoExport(", src)
        self.assertIn("live.on_stats = ", src)


class CliAndGitTests(unittest.TestCase):
    def test_cli_option(self):
        args = parse_args(["--obsidian"])
        self.assertEqual(args.obsidian, "obsidian")
        self.assertEqual(parse_args(["--obsidian", "D:/Vault"]).obsidian, "D:/Vault")
        self.assertIsNone(parse_args(["--drafthelper"]).obsidian)

    def test_default_vault_is_in_private_data_folder(self):
        vault = obsidian.vault_path("obsidian")
        self.assertEqual(vault.parent.name, "daten")
        res = subprocess.run(["git", "check-ignore", "-q", str(vault / "Cards" / "X.md")], cwd=ROOT)
        self.assertEqual(res.returncode, 0, "Vault muss von git ignoriert werden")

    def test_vault_folder_name_ignored_anywhere(self):
        res = subprocess.run(["git", "check-ignore", "-q", "obsidian/Cards/X.md"], cwd=ROOT)
        self.assertEqual(res.returncode, 0)


class EnglishTests(unittest.TestCase):
    def test_english_notes_without_german(self):
        with english():
            out = notes()
        allow = ["Kirk: Captain", "Kirk - Captain", "Spock", "Tribble", "Spacecraft", "Dilemmas", "Sacrifice",
                 obsidian.MARKER, "draftgott", "Plains"]
        for path, text in out.items():
            body = text.split("\n---\n", 1)[1]  # Frontmatter-Schluessel sind fest
            self.assertEqual(german_leftovers(body, allow), [], path)
        self.assertIn("Win 2-1", out["Drafts/2026-11-10 TRK Pick Two.md"])


if __name__ == "__main__":
    unittest.main()
