import json
import re
import shutil
import subprocess
import unittest

from components import drafthelper as dh

DASH = "—"


def sc(text="", keywords=(), type_line=f"Creature {DASH} Test"):
    return {"name": "T", "type_line": type_line, "oracle_text": text, "keywords": list(keywords), "layout": "normal",
            "mana_cost": "{1}", "cmc": 1.0, "colors": []}


class MillKindsTests(unittest.TestCase):
    def kinds(self, text, **kw):
        return dh.flow_kinds(sc(text, **kw))

    def test_imperative_mill_is_self_mill(self):
        self.assertEqual(self.kinds("When this creature enters, mill three cards."), ["mill_self"])
        self.assertEqual(self.kinds("Mill three cards.", type_line="Sorcery"), ["mill_self"])

    def test_mill_keyword_with_number(self):
        self.assertEqual(self.kinds("Mill 3.", keywords=["Mill"], type_line="Sorcery"), ["mill_self"])

    def test_you_mill(self):
        self.assertEqual(self.kinds("You may mill two cards."), ["mill_self"])

    def test_putting_your_own_cards_into_the_graveyard(self):
        self.assertEqual(self.kinds("Put the top three cards of your library into your graveyard.",
                                    type_line="Sorcery"), ["mill_self"])

    def test_target_opponent_mills(self):
        self.assertEqual(self.kinds("Target opponent mills three cards.", type_line="Sorcery"), ["mill_opp"])

    def test_each_opponent_mills(self):
        self.assertEqual(self.kinds("Each opponent mills two cards.", type_line="Sorcery"), ["mill_opp"])

    def test_target_player_mills_can_be_both(self):
        self.assertEqual(self.kinds("Target player mills three cards.", type_line="Sorcery"),
                         ["mill_self", "mill_opp"])

    def test_each_player_mills_is_both(self):
        self.assertEqual(self.kinds("Each player mills two cards.", type_line="Sorcery"), ["mill_self", "mill_opp"])

    def test_target_player_puts_cards_into_the_graveyard_is_both(self):
        self.assertEqual(self.kinds("Target player puts the top three cards of their library into their graveyard.",
                                    type_line="Sorcery"), ["mill_self", "mill_opp"])

    def test_triggers_on_milling_are_not_mill(self):
        self.assertEqual(self.kinds("Whenever you mill one or more cards, put a +1/+1 counter on this creature."), [])

    def test_graveyard_count_is_not_mill(self):
        self.assertEqual(self.kinds("This creature gets +2/+0 for every seven cards in your graveyard."), [])

    def test_reminder_text_is_ignored(self):
        self.assertEqual(self.kinds("Flying (To mill a card, put the top card of your library into your graveyard.)",
                                    keywords=["Flying"]), [])

    def test_word_containing_mill_is_not_mill(self):
        self.assertEqual(self.kinds("Create a Windmill token."), [])

    def test_mill_combines_with_other_flow_in_a_fixed_order(self):
        self.assertEqual(self.kinds("Mill three cards, then draw a card.", type_line="Sorcery"),
                         ["draw", "mill_self"])

    def test_surveil_next_to_target_player_mill(self):
        self.assertEqual(self.kinds("Surveil 1. Target player mills two cards.", type_line="Sorcery"),
                         ["surveil", "mill_self", "mill_opp"])


def page_block():
    page = dh.PAGE
    return page[page.index("// BEGIN typeCounts"):page.index("// END typeCounts")]


@unittest.skipUnless(shutil.which("node"), "Node.js nicht installiert")
class MillInThePageTests(unittest.TestCase):
    def run_js(self, copies):
        script = page_block() + "\nconst i = JSON.parse(process.argv[1]);\n" \
                                "console.log(JSON.stringify(typeCounts(i, [])));\n"
        out = subprocess.run(["node", "-e", script, json.dumps(copies)], capture_output=True, text=True, timeout=30)
        if out.returncode != 0:
            raise RuntimeError(out.stderr)
        return json.loads(out.stdout)

    def test_self_and_opponent_mill_are_counted_separately(self):
        copies = [{"kinds": ["sorcery"], "mark": "core", "empower": False, "points": 0, "flow": ["mill_self"]},
                  {"kinds": ["sorcery"], "mark": "core", "empower": False, "points": 0,
                   "flow": ["mill_self", "mill_opp"]},
                  {"kinds": ["sorcery"], "mark": "splash", "empower": False, "points": 0, "flow": ["mill_opp"]}]
        r = self.run_js(copies)
        self.assertEqual((r["splash"]["flow_mill_self"], r["splash"]["flow_mill_opp"], r["splash"]["flow"]), (2, 2, 3))
        self.assertEqual((r["nosplash"]["flow_mill_self"], r["nosplash"]["flow_mill_opp"], r["nosplash"]["flow"]),
                         (2, 1, 2))

    def test_every_flow_kind_has_a_label_in_the_page(self):
        kinds = re.search(r"const FLOW_KINDS=\[([^\]]*)\]", dh.PAGE).group(1)
        names = re.findall(r'"([a-z_]+)"', kinds)
        labels = re.search(r"const FLOW_LABELS=\{([^}]*)\}", dh.PAGE).group(1)
        for name in names:
            self.assertIn(name + ":", labels, name)
        self.assertIn("mill_self", names)
        self.assertIn("mill_opp", names)

    def test_server_and_page_agree_on_the_kinds(self):
        kinds = re.search(r"const FLOW_KINDS=\[([^\]]*)\]", dh.PAGE).group(1)
        self.assertEqual(re.findall(r'"([a-z_]+)"', kinds), list(dh.FLOW_ORDER))


if __name__ == "__main__":
    unittest.main()
