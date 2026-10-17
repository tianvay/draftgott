"""Friedhof-Score (Graveyard Interaction): Erkennung, Zaehlung in Seite und Bericht, Abschnitt im Bericht."""
import shutil
import unittest

from components.graveyard import gy_enabler, gy_info

DASH = "—"
CREATURE = f"Creature {DASH} Test"


def card(text, type_line="Sorcery", keywords=(), name="Test Card", faces=None, layout="normal"):
    d = {"name": name, "type_line": type_line, "oracle_text": text, "keywords": list(keywords), "layout": layout,
         "mana_cost": "{1}"}
    if faces:
        d["card_faces"] = faces
    return d


def info(text, **kw):
    r = gy_info(card(text, **kw))
    return (r["points"], r["kind"]) if r else None


class RecastTests(unittest.TestCase):
    def test_flashback(self):
        self.assertEqual(info("Put a +1/+1 counter on each of one or two target creatures.\nFlashback {3}{W}",
                              keywords=["Flashback"]), (1.0, "Zweitverwertung"))

    def test_other_recast_keywords(self):
        for kw in ("Escape", "Unearth", "Disturb", "Jump-start", "Retrace", "Embalm", "Eternalize"):
            with self.subTest(kw=kw):
                self.assertEqual(info(f"{kw} {{2}}", type_line=CREATURE, keywords=[kw]), (1.0, "Zweitverwertung"))

    def test_return_this_card(self):
        self.assertEqual(info("{2}{W/B}: Return this card from your graveyard to your hand.", type_line=CREATURE),
                         (1.0, "Zweitverwertung"))
        self.assertEqual(info("{4}{B}, Exile another creature card from your graveyard: Return this card from your "
                              "graveyard to the battlefield tapped.", type_line=CREATURE), (1.0, "Zweitverwertung"))

    def test_ability_from_the_graveyard(self):
        self.assertEqual(info("{1}, Exile this card from your graveyard: Empower Jace 2.", type_line=CREATURE),
                         (1.0, "Zweitverwertung"))


class ReturnOtherTests(unittest.TestCase):
    def test_return_other_cards(self):
        for text in ("{2}: Return target land card from your graveyard to your hand.",
                     "{3}{B}, Exile this card from your graveyard: Return another target creature card from your "
                     "graveyard to your hand.",
                     "When this creature enters, mill four cards. When you do, return target land card from your "
                     "graveyard to the battlefield tapped."):
            with self.subTest(text=text):
                self.assertEqual(info(text, type_line=CREATURE)[1] in ("Zurückholen", "Zweitverwertung"), True)
        self.assertEqual(info("{2}: Return target land card from your graveyard to your hand.", type_line=CREATURE),
                         (0.7, "Zurückholen"))

    def test_combat_damage_trigger(self):
        self.assertEqual(info("Whenever this creature deals combat damage to a player, return target land card from "
                              "your graveyard to your hand.", type_line=CREATURE), (0.7, "Zurückholen"))


class ResourceTests(unittest.TestCase):
    def test_graveyard_as_resource(self):
        for text, kws in (("When Test Card enters, put X -1/-1 counters on up to one target creature, where X is the "
                           "greatest mana value among cards in your graveyard.", ()),
                          ("Threshold — This creature gets +1/+1 as long as there are seven or more cards in your "
                           "graveyard.", ("Threshold",)),
                          ("Delve\nDraw two cards.", ("Delve",))):
            with self.subTest(text=text):
                self.assertEqual(info(text, type_line=CREATURE, keywords=kws), (0.5, "Ressource"))


class NotGraveyardTests(unittest.TestCase):
    def test_no_graveyard_interaction(self):
        for text in ("Draw a card.", "Exile up to one target card from a graveyard.",
                     "Target opponent exiles a creature they control and their graveyard.",
                     "Destroy target creature."):
            with self.subTest(text=text):
                self.assertIsNone(gy_info(card(text)))


class EnablerTests(unittest.TestCase):
    def test_enablers(self):
        for text, tl, kws in (("Mill three cards.", "Sorcery", ()), ("Surveil 1.", "Sorcery", ()),
                              ("Draw a card, then discard a card.", "Sorcery", ()),
                              ("Plainscycling {2}", CREATURE, ("Plainscycling",)),
                              ("Search your library for a land card, put it into your graveyard, then shuffle.",
                               "Sorcery", ())):
            with self.subTest(text=text):
                self.assertTrue(gy_enabler(card(text, type_line=tl, keywords=kws)))

    def test_not_enablers(self):
        self.assertFalse(gy_enabler(card("Draw a card.")))
        self.assertFalse(gy_enabler(card("Target opponent mills three cards.")))
        self.assertFalse(gy_enabler(card("Whenever you surveil, draw a card.", type_line=CREATURE)))


# ---------------- Zaehlung und Bericht

from tests.test_type_overview import run_js  # noqa: E402
from components.report_cards import render_graveyard_table, render_type_table, type_counts  # noqa: E402


def copy(mark="core", **flags):
    d = {"kinds": ["creature"], "mark": mark, "empower": False, "points": 0, "flow": []}
    d.update(flags)
    return d


@unittest.skipUnless(shutil.which("node"), "Node.js nicht installiert")
class PageCountsTests(unittest.TestCase):
    def test_counts_and_parity(self):
        copies = [copy(gy=1.0), copy("splash", gy=0.5, gy_enabler=True), copy(gy_enabler=True), copy()]
        r = run_js(copies, [])
        self.assertEqual((r["splash"]["gy"], r["nosplash"]["gy"]), (2, 1))
        self.assertAlmostEqual(r["splash"]["gy_points"], 1.5)
        self.assertEqual((r["splash"]["gy_enabler"], r["nosplash"]["gy_enabler"]), (2, 1))
        ctx = {"rows": [("A", 1, None, ""), ("B", 1, None, ""), ("C", 1, None, "")],
               "info": {"A": {"kinds": ["creature"], "gy": {"points": 1.0}},
                        "B": {"kinds": ["creature"], "gy": {"points": 0.5}, "gy_enabler": True},
                        "C": {"kinds": ["creature"], "gy_enabler": True}}}
        t = type_counts(ctx)
        self.assertEqual((t["gy"], t["gy_points"], t["gy_enabler"]), (r["splash"]["gy"], 1.5, r["splash"]["gy_enabler"]))

    def test_page_passes_the_fields(self):
        from tests.test_card_flow import run_copies_of
        out = run_copies_of([{"mark": "core", "card": {"kinds": ["creature"], "gy_points": 0.7, "gy_enabler": True}},
                             {"mark": "core", "card": {}}])
        self.assertEqual((out[0]["gy"], out[0]["gy_enabler"]), (0.7, True))
        self.assertEqual(set(out[1]), {"kinds", "mark", "empower", "points", "flow"})


class ReportTableTests(unittest.TestCase):
    def ctx(self):
        return {"rows": [("Ghoul", 2, None, ""), ("Bear", 21, None, "")],
                "info": {"Ghoul": {"kinds": ["creature"], "gy": {"points": 1.0, "kind": "Zweitverwertung",
                                                                 "text": "Return this card from your graveyard."}},
                         "Bear": {"kinds": ["creature"]}}}

    def test_type_rows_only_when_present(self):
        html = render_type_table(self.ctx())
        self.assertIn("Friedhof-Interaktion (Karten)", html)
        self.assertIn("Σ Friedhof-Punkte", html)
        self.assertNotIn("Friedhof", render_type_table({"rows": [("Bear", 1, None, "")], "info": {"Bear": {}}}))

    def test_table(self):
        html = render_graveyard_table(self.ctx())
        for text in ("Ghoul", "Zweitverwertung", "1.00", "2.00", "Return this card from your graveyard."):
            self.assertIn(text, html)
        self.assertEqual(render_graveyard_table({"rows": [("Bear", 1, None, "")], "info": {"Bear": {}}}), "")


if __name__ == "__main__":
    unittest.main()
