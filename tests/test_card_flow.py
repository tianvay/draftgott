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


def sc(text="", keywords=(), type_line=f"Creature {DASH} Test", faces=None):
    d = {"name": "T", "type_line": type_line, "oracle_text": text, "keywords": list(keywords), "layout": "normal",
         "mana_cost": "{1}", "cmc": 1.0, "colors": []}
    if faces:
        d["card_faces"] = faces
        d["layout"] = "prepare"
    return d


class FlowKindsTests(unittest.TestCase):
    def kinds(self, *a, **kw):
        return dh.flow_kinds(sc(*a, **kw))

    def test_plain_draw(self):
        self.assertEqual(self.kinds("Draw two cards.", type_line="Sorcery"), ["draw"])

    def test_draw_in_an_activated_ability(self):
        self.assertEqual(self.kinds("{2}, {T}, Sacrifice an artifact or land: Draw a card."), ["draw"])

    def test_draw_next_to_damage(self):
        self.assertEqual(self.kinds("Test Spell deals 2 damage to each player. Draw two cards.", type_line="Sorcery"),
                         ["draw"])

    def test_you_draw_at_the_opponents_draw_step(self):
        self.assertEqual(self.kinds("At the beginning of each opponent's draw step, you draw a card."), ["draw"])

    def test_surveil_as_text_and_as_keyword(self):
        self.assertEqual(self.kinds("When this creature enters, surveil 1."), ["surveil"])
        self.assertEqual(self.kinds("Surveil 2.", keywords=["Surveil"], type_line="Sorcery"), ["surveil"])

    def test_scry(self):
        self.assertEqual(self.kinds("Scry 2.", type_line="Sorcery"), ["scry"])

    def test_search_your_library(self):
        self.assertEqual(self.kinds("Search your library for a basic land card, put it onto the battlefield tapped, "
                                    "then shuffle.", type_line="Sorcery"), ["search"])

    def test_landcycling_keyword_is_a_search(self):
        text = "Basic landcycling {2} ({2}, Discard this card: Search your library for a basic land card.)"
        self.assertEqual(self.kinds(text, keywords=["Basic landcycling", "Landcycling", "Cycling"]), ["search"])

    def test_plain_cycling_is_a_draw(self):
        self.assertEqual(self.kinds("Cycling {2}", keywords=["Cycling"], type_line="Instant"), ["draw"])

    def test_explore(self):
        self.assertEqual(self.kinds("When this creature enters, it explores."), ["explore"])

    def test_several_kinds_in_a_fixed_order(self):
        self.assertEqual(self.kinds("Surveil 1. Draw a card. Search your library for a land card.",
                                    type_line="Sorcery"), ["draw", "search", "surveil"])

    def test_triggers_on_drawing_or_scrying_are_not_card_flow(self):
        for text in ("Whenever you draw a card, this creature gets +1/+1.",
                     "If you would draw a card, exile the top card instead.",
                     "Whenever you scry or surveil, this creature gets +1/+1 until end of turn.",
                     "As long as you've scried or surveilled this turn, this creature can attack."):
            self.assertEqual(self.kinds(text), [], text)

    def test_the_opponent_drawing_is_not_card_flow(self):
        self.assertEqual(self.kinds("Each opponent draws a card.", type_line="Sorcery"), [])
        self.assertEqual(self.kinds("Target opponent draws two cards.", type_line="Sorcery"), [])

    def test_reminder_text_is_ignored(self):
        self.assertEqual(self.kinds("Flying (Look at the top card of your library. Draw a card, search your library.)",
                                    keywords=["Flying"]), [])

    def test_empower_jace_alone_is_not_card_flow(self):
        self.assertEqual(self.kinds("Empower Jace 2.", keywords=["Empower Jace"], type_line="Sorcery"), [])

    def test_both_faces_are_considered(self):
        faces = [{"name": "A", "type_line": f"Creature {DASH} Test", "oracle_text": "Flying"},
                 {"name": "B", "type_line": "Sorcery", "oracle_text": "Surveil 1."}]
        self.assertEqual(dh.flow_kinds(sc(faces=faces)), ["surveil"])

    def test_vanilla(self):
        self.assertEqual(self.kinds(), [])

    def test_draw_step_alone_is_not_a_draw(self):
        self.assertEqual(self.kinds("Skip your draw step."), [])


def _data(name, text, keywords=()):
    return {"name": name, "type_line": f"Creature {DASH} Test", "mana_cost": "{1}", "cmc": 1.0, "colors": [],
            "oracle_text": text, "keywords": list(keywords), "layout": "normal", "power": "1", "toughness": "1"}


class PoolCardTests(unittest.TestCase):
    def test_pool_cards_carry_flow(self):
        data = {"Drawer": _data("Drawer", "When this creature enters, draw a card."),
                "Plain": _data("Plain", "")}
        text = "Deck\n1 Drawer (TST) 1\n1 Plain (TST) 2\n"
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "pool.txt"
            path.write_text(text, encoding="utf-8")
            with mock.patch.object(dh, "fetch_cards_cached", lambda n, refresh=False: data), \
                    mock.patch.object(dh, "fetch_printing_images", lambda specs: {}), \
                    contextlib.redirect_stderr(io.StringIO()):
                cards, _b, _s = dh.load_pool(str(path))
        by = {c["name"]: c for c in cards}
        self.assertEqual(by["Drawer"]["flow"], ["draw"])
        self.assertEqual(by["Plain"]["flow"], [])


def run_js(copies, basics=()):
    page = dh.PAGE
    code = page[page.index("// BEGIN typeCounts"):page.index("// END typeCounts")]
    script = code + "\nconst i = JSON.parse(process.argv[1]);\nconsole.log(JSON.stringify(typeCounts(i.c, i.b)));\n"
    out = subprocess.run(["node", "-e", script, json.dumps({"c": copies, "b": list(basics)})],
                         capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise RuntimeError(out.stderr)
    return json.loads(out.stdout)


def copy(flow, mark="core", kinds=("creature",)):
    return {"kinds": list(kinds), "mark": mark, "empower": False, "points": 0, "flow": flow}


@unittest.skipUnless(shutil.which("node"), "Node.js nicht installiert")
class FlowCountsInThePageTests(unittest.TestCase):
    def test_card_with_several_kinds_counts_once_in_total_and_in_each_kind(self):
        r = run_js([copy(["draw", "surveil"])])
        for g in ("splash", "nosplash"):
            self.assertEqual((r[g]["flow"], r[g]["flow_draw"], r[g]["flow_surveil"], r[g]["flow_scry"]), (1, 1, 1, 0))

    def test_cards_without_flow_do_not_count(self):
        r = run_js([copy([]), copy([])])
        self.assertEqual(r["splash"]["flow"], 0)

    def test_variants_are_counted_separately(self):
        r = run_js([copy(["search"], "splash"), copy(["draw"], "nosplash"), copy(["draw"], "core")])
        self.assertEqual((r["splash"]["flow_search"], r["nosplash"]["flow_search"]), (1, 0))
        self.assertEqual((r["splash"]["flow_draw"], r["nosplash"]["flow_draw"]), (1, 2))
        self.assertEqual((r["splash"]["flow"], r["nosplash"]["flow"]), (2, 2))

    def test_off_cards_are_ignored(self):
        r = run_js([copy(["draw"], "off")])
        self.assertEqual(r["splash"]["flow"], 0)

    def test_missing_flow_field_is_tolerated(self):
        r = run_js([{"kinds": ["creature"], "mark": "core", "empower": False, "points": 0}])
        self.assertEqual(r["splash"]["flow"], 0)

    def test_unknown_flow_kind_counts_in_total_only(self):
        r = run_js([copy(["mill"])])
        self.assertEqual(r["splash"]["flow"], 1)


def run_copies_of(state):
    """copiesOf wandelt die Kacheln der Seite in die Eingabe von typeCounts um (Funktion im selben Block)."""
    page = dh.PAGE
    code = page[page.index("// BEGIN typeCounts"):page.index("// END typeCounts")]
    script = code + chr(10) + "console.log(JSON.stringify(copiesOf(JSON.parse(process.argv[1]))));" + chr(10)
    out = subprocess.run(["node", "-e", script, json.dumps(state)], capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise RuntimeError(out.stderr)
    return json.loads(out.stdout)


@unittest.skipUnless(shutil.which("node"), "Node.js nicht installiert")
class PageStateToCountsTests(unittest.TestCase):
    """Die Seite muss alle Felder, die gezaehlt werden, aus der Kachel weitergeben (Fehler aus dem Browser-Test)."""

    def test_card_fields_reach_the_counting_function(self):
        state = [{"mark": "splash", "card": {"kinds": ["creature"], "empower": True, "empower_points": 3,
                                              "flow": ["draw", "search"]}}]
        out = run_copies_of(state)
        self.assertEqual(out, [{"kinds": ["creature"], "mark": "splash", "empower": True, "points": 3,
                                "flow": ["draw", "search"]}])

    def test_missing_fields_get_defaults(self):
        out = run_copies_of([{"mark": "core", "card": {}}])
        self.assertEqual(out, [{"kinds": [], "mark": "core", "empower": False, "points": 0, "flow": []}])


if __name__ == "__main__":
    unittest.main()
