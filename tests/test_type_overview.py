import contextlib
import io
import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from components import drafthelper as dh

DASH = "—"


class TypeKindsTests(unittest.TestCase):
    def kinds(self, type_line):
        return set(dh.type_kinds(type_line))

    def test_plain_types(self):
        self.assertEqual(self.kinds(f"Creature {DASH} Elf"), {"creature"})
        self.assertEqual(self.kinds("Instant"), {"instant"})
        self.assertEqual(self.kinds("Sorcery"), {"sorcery"})
        self.assertEqual(self.kinds(f"Legendary Planeswalker {DASH} Jace"), {"planeswalker"})

    def test_artifact_creature_counts_only_as_creature(self):
        self.assertEqual(self.kinds(f"Artifact Creature {DASH} Construct"), {"creature"})

    def test_noncreature_artifact(self):
        self.assertEqual(self.kinds(f"Artifact {DASH} Equipment"), {"artifact"})
        self.assertEqual(self.kinds("Legendary Artifact"), {"artifact"})

    def test_enchantment_without_creature(self):
        self.assertEqual(self.kinds(f"Enchantment {DASH} Aura"), {"enchantment"})
        self.assertEqual(self.kinds("Legendary Enchantment"), {"enchantment"})

    def test_enchantment_creature_counts_as_creature(self):
        self.assertEqual(self.kinds(f"Enchantment Creature {DASH} Nymph"), {"creature"})

    def test_artifact_enchantment_is_in_both_rows(self):
        self.assertEqual(self.kinds("Artifact Enchantment"), {"artifact", "enchantment"})

    def test_nonbasic_land_is_a_land_and_a_nonbasic_land(self):
        self.assertEqual(self.kinds("Land"), {"land", "nonbasic_land"})
        self.assertEqual(self.kinds(f"Land {DASH} Island"), {"land", "nonbasic_land"})

    def test_artifact_land_counts_as_land_only(self):
        self.assertEqual(self.kinds("Artifact Land"), {"land", "nonbasic_land"})

    def test_basic_land(self):
        self.assertEqual(self.kinds(f"Basic Land {DASH} Plains"), {"land"})

    def test_double_faced_card_uses_the_front(self):
        self.assertEqual(self.kinds(f"Creature {DASH} Wizard // Sorcery"), {"creature"})

    def test_empty_type_line(self):
        self.assertEqual(self.kinds(""), set())


def _card(name, type_line, text="", cost="{1}", keywords=()):
    return {"name": name, "type_line": type_line, "mana_cost": cost, "cmc": 1.0, "colors": [], "oracle_text": text,
            "keywords": list(keywords), "layout": "normal", "power": "1" if "Creature" in type_line else None,
            "toughness": "1" if "Creature" in type_line else None}


DATA = {c["name"]: c for c in [
    _card("Spell Empower", "Sorcery", "Empower Jace 2.", keywords=["Empower Jace"]),
    _card("Creature Empower", f"Creature {DASH} Test", "When this creature enters, empower Jace 4.",
          keywords=["Empower Jace"]),
    _card("Attack Empower", f"Creature {DASH} Test",
          "Whenever this creature attacks, empower Jace 1.", keywords=["Empower Jace"]),
    _card("X Empower", f"Creature {DASH} Test",
          "Whenever this creature attacks, empower Jace X, where X is the number of creatures you control.",
          keywords=["Empower Jace"]),
    _card("Plain", f"Creature {DASH} Test"),
]}


def load_cards(names):
    text = "Deck\n" + "\n".join(f"1 {n} (TST) {i}" for i, n in enumerate(names, 1)) + "\n"
    with tempfile.TemporaryDirectory() as d:
        path = pathlib.Path(d) / "pool.txt"
        path.write_text(text, encoding="utf-8")
        with mock.patch.object(dh, "fetch_cards_cached", lambda n, refresh=False: DATA), \
                mock.patch.object(dh, "fetch_printing_images", lambda specs: {}), \
                contextlib.redirect_stderr(io.StringIO()):
            cards, _basics, _sig = dh.load_pool(str(path))
    return {c["name"]: c for c in cards}


class PoolCardTypeInfoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cards = load_cards(list(DATA))

    def test_cards_carry_kinds(self):
        self.assertEqual(self.cards["Spell Empower"]["kinds"], ["sorcery"])
        self.assertEqual(self.cards["Plain"]["kinds"], ["creature"])

    def test_empower_card_with_immediate_points_from_a_spell(self):
        c = self.cards["Spell Empower"]
        self.assertTrue(c["empower"])
        self.assertEqual(c["empower_points"], 2)

    def test_empower_points_on_entering(self):
        c = self.cards["Creature Empower"]
        self.assertTrue(c["empower"])
        self.assertEqual(c["empower_points"], 4)

    def test_recurring_empower_gives_no_immediate_points(self):
        c = self.cards["Attack Empower"]
        self.assertTrue(c["empower"])
        self.assertEqual(c["empower_points"], 0)

    def test_variable_empower_counts_as_card_without_points(self):
        c = self.cards["X Empower"]
        self.assertTrue(c["empower"])
        self.assertEqual(c["empower_points"], 0)

    def test_card_without_empower(self):
        c = self.cards["Plain"]
        self.assertFalse(c["empower"])
        self.assertEqual(c["empower_points"], 0)


def run_js(copies, basics):
    """Fuehrt typeCounts aus der Seite mit Node aus (die Funktion steht zwischen zwei Markierungen)."""
    page = dh.PAGE
    begin = page.index("// BEGIN typeCounts")
    end = page.index("// END typeCounts")
    code = page[begin:end]
    script = code + "\nconst input = JSON.parse(process.argv[1]);\n" \
                    "console.log(JSON.stringify(typeCounts(input.copies, input.basics)));\n"
    out = subprocess.run(["node", "-e", script, json.dumps({"copies": copies, "basics": basics})],
                         capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise RuntimeError(out.stderr)
    return json.loads(out.stdout)


def copy(kinds, mark="core", empower=False, points=0):
    return {"kinds": kinds, "mark": mark, "empower": empower, "points": points}


@unittest.skipUnless(shutil.which("node"), "Node.js nicht installiert")
class TypeCountsInThePageTests(unittest.TestCase):
    def test_core_cards_count_in_both_variants(self):
        r = run_js([copy(["creature"]), copy(["creature"]), copy(["instant"])], [])
        self.assertEqual((r["splash"]["creature"], r["nosplash"]["creature"]), (2, 2))
        self.assertEqual((r["splash"]["instant"], r["nosplash"]["instant"]), (1, 1))

    def test_group_cards_count_only_in_their_variant(self):
        r = run_js([copy(["creature"], "splash"), copy(["sorcery"], "nosplash"), copy(["sorcery"], "nosplash")], [])
        self.assertEqual((r["splash"]["creature"], r["nosplash"]["creature"]), (1, 0))
        self.assertEqual((r["splash"]["sorcery"], r["nosplash"]["sorcery"]), (0, 2))

    def test_off_cards_count_nowhere(self):
        r = run_js([copy(["creature"], "off")], [])
        self.assertEqual((r["splash"]["creature"], r["nosplash"]["creature"]), (0, 0))
        self.assertEqual((r["splash"]["cards"], r["nosplash"]["cards"]), (0, 0))

    def test_basic_lands_add_to_lands_and_cards_but_not_to_nonbasic(self):
        basics = [{"core": 3, "splash": 1, "nosplash": 0}, {"core": 2, "splash": 0, "nosplash": 2}]
        r = run_js([copy(["land", "nonbasic_land"])], basics)
        self.assertEqual((r["splash"]["land"], r["nosplash"]["land"]), (1 + 3 + 1 + 2, 1 + 3 + 2 + 2))
        self.assertEqual((r["splash"]["nonbasic_land"], r["nosplash"]["nonbasic_land"]), (1, 1))
        self.assertEqual((r["splash"]["cards"], r["nosplash"]["cards"]), (7, 8))

    def test_empower_cards_and_points(self):
        copies = [copy(["sorcery"], "core", True, 2), copy(["creature"], "splash", True, 4),
                  copy(["creature"], "nosplash", True, 0), copy(["creature"], "core")]
        r = run_js(copies, [])
        self.assertEqual((r["splash"]["empower"], r["splash"]["points"]), (2, 6))
        self.assertEqual((r["nosplash"]["empower"], r["nosplash"]["points"]), (2, 2))

    def test_unknown_kind_is_ignored(self):
        r = run_js([copy(["battle"])], [])
        self.assertEqual(r["splash"]["cards"], 1)

    def test_multi_kind_card_counts_in_each_row(self):
        r = run_js([copy(["artifact", "enchantment"])], [])
        self.assertEqual((r["splash"]["artifact"], r["splash"]["enchantment"]), (1, 1))
        self.assertEqual(r["splash"]["cards"], 1)

    def test_empty_input(self):
        r = run_js([], [])
        self.assertEqual(r["splash"]["cards"], 0)
        self.assertEqual(r["splash"]["creature"], 0)


if __name__ == "__main__":
    unittest.main()
