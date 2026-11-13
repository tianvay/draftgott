"""Englische Ausgabe von components/report_sections.py und components/report_cards.py."""
import unittest

import mtg_sim
from components import archetypes as arch
from components import report_cards as rc
from components import report_sections as rs
from components import synergy
from components.cards import EMPOWER_KIND_LABEL
from components.i18n_en import report_parts
from tests.fixtures import args_for
from tests.i18n_check import english, german_leftovers
from tests.test_archetypes import _deck as arch_deck
from tests.test_report_cards import DATA, DECK


def sim_ctx():
    """Zwei kleine Decks, simuliert wie in mtg_sim.simulate_entries (ohne Scryfall)."""
    args = args_for(["deck.txt", "--sims", "40"])
    alt = dict(DECK, **{"White Bear": 2, "Black Bear": 3})
    entries = [{"name": "Main", "deck": dict(DECK), "parts": [("Main", dict(DECK))]},
               {"name": "Alt", "deck": alt, "parts": [("Alt", dict(alt))]}]
    horizon = max(args.max_runden, args.turns, args.curve_runden)
    decks = [mtg_sim.build_deck(e, DATA, args) for e in entries]
    for i, dd in enumerate(decks):
        mtg_sim.simulate_deck(dd, args, i, horizon, lambda m: None)
    ctx = dict(decks[0], args=args, horizon=horizon, jace=mtg_sim.analyze_jace(decks[0]["rows"]), alts=decks[1:],
               all_decks=decks)
    return ctx, decks


class ReportPartsEnglishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx, cls.decks = sim_ctx()

    def both(self, fn, *args, allow=()):
        """Deutsch zweimal gleich, Englisch ohne deutsche Reste."""
        de1 = fn(*args)
        with english():
            en = fn(*args)
        de2 = fn(*args)
        self.assertEqual(de1, de2)
        self.assertNotEqual(de1, en)
        self.assertEqual(german_leftovers(en, allow=allow), [], fn.__name__)
        return de1, en

    def test_logic_section(self):
        for jace in (False, True):
            de, en = self.both(rs.render_logic_section, jace)
            self.assertIn("✔ gewählt", de)
            self.assertIn("✔ chosen", en)
            self.assertIn('<tr class="win">', en)

    def test_compare_section(self):
        _de, en = self.both(rs.render_compare_section, self.ctx, allow=["Main", "Alt"])
        self.assertIn("Summary across all metrics", en)

    def test_jace_section(self):
        self.both(rs.render_jace_section, self.ctx, allow=["Jace Spell"])

    def test_color_curves_type_tables(self):
        self.both(rc.render_color_curves, self.ctx)
        self.both(rc.render_type_table, self.ctx)
        self.both(rc.render_types_compare, self.decks, allow=["Main", "Alt"])
        self.both(rc.render_color_availability, self.ctx, allow=["Main", "Alt"])

    def test_archetype_panel_and_stats(self):
        names = {"White Bear": 6, "Quick Spell": 4, "Black Bear": 3, "Jace Spell": 1, "Plains": 9, "Swamp": 7}
        ctx = arch_deck(names, "trk")
        ctx["cardarch"] = {"Black Bear": ["BR"], "White Bear": ["WB", "RW"]}
        ctx["cardbest"] = {"White Bear": "WB"}
        _de, en = self.both(rc.render_archetype_panel, ctx, allow=["White Bear"])
        self.assertIn("White/Black", en)
        self.assertIn("Your assignment:", en)
        ctx["cardstats"] = {"White Bear": {"drafted": 3, "drafts": 2, "decks": 2, "games": 5, "wins": 4}}
        self.both(rc.render_stats_panel, ctx, allow=["White Bear"])
        mono = arch_deck({"White Bear": 8, "Quick Spell": 4, "Plains": 17}, "trk")
        self.both(rc.render_archetype_panel, mono)

    def test_removal_graveyard_synergy(self):
        ctx = {"rows": [("Kill", 4, None, ""), ("Ghoul", 2, None, ""), ("Bear", 19, None, "")],
               "info": {"Kill": {"kinds": ["instant"], "removal": {"points": 1.0, "kind": "Bedingt",
                                                                   "text": "Destroy target creature."}},
                        "Ghoul": {"kinds": ["creature"], "gy": {"points": 1.0, "kind": "Zweitverwertung",
                                                                "text": "Return this card from your graveyard."}},
                        "Bear": {"kinds": ["creature"], "flash": True, "deathtouch": True, "gy_enabler": True}}}
        allow = ["Kill", "Ghoul", "Bear"]
        for fn in (rc.render_removal_table, rc.render_graveyard_table, rc.render_type_table):
            _de, en = self.both(fn, ctx, allow=allow)
        self.assertIn("Conditional", self.both(rc.render_removal_table, ctx, allow=allow)[1])
        self.assertIn("Recast", self.both(rc.render_graveyard_table, ctx, allow=allow)[1])

    def test_synergy_table(self):
        from tests.test_synergy import BEAR, LIFE, PAYOFF, PROWESS
        ctx = {"rows": [(c.name, q, c, "") for c, q in [(PAYOFF, 1), (LIFE, 3), (PROWESS, 2), (BEAR, 4)]]}
        self.both(rc.render_synergy_table, ctx, allow=["Bloombrute", "Healer", "Monk", "Bear"])

    def test_pair_and_checks(self):
        with english():
            self.assertEqual(rc.pip_check_label({"k": 2, "color": "W", "turn": 4}), "≥ 2 sources of White by turn 4")
            self.assertEqual(rc.all_colors_label(["W", "B"]), "All colors by turn 3 (White, Black)")

    def test_german_unchanged_samples(self):
        self.assertEqual(rc.pip_check_label({"k": 2, "color": "W", "turn": 4}), "≥ 2 Quellen Weiß bis Runde 4")
        self.assertEqual(rc.all_colors_label(["W", "B"]), "Alle Farben bis Runde 3 (Weiß, Schwarz)")


class DictionaryTests(unittest.TestCase):
    def test_data_texts_have_english(self):
        local = report_parts.LOCAL
        texts = list(rc.COLOR_NAME.values()) + list(rc.FLOW_LABELS.values()) + [lab for _k, lab, _c in rc.TYPE_ROWS]
        texts += list(EMPOWER_KIND_LABEL.values()) + list(rs.JACE_TAG_LABEL.values())
        texts += [v[0] for v in synergy.RESOURCES.values()]
        texts += [tip for lst in arch.ARCHETYPES.values() for a in lst for tip in a["tips"]]
        texts += list(arch.COLOR_NAME.values())
        for kind in ("Massenremoval", "Exil bis verlassen", "Hart", "Bedingt", "Bibliothek", "Edikt", "Schaden",
                     "−X/−X", "Fight", "Bounce", "Toughness 0", "Lock", "−1/−1-Marken", "Fähigkeit", "Auslöser",
                     "Zweitverwertung", "Zurückholen", "Ressource", "Karten", "Länder", "Farben", "Art", "Deck",
                     "Karte", "Kreaturen", "Mana"):
            texts.append(kind)
        self.assertEqual([x for x in texts if x not in local], [])

    def test_constant_sentences_have_english(self):
        en = report_parts.EN
        texts = list(rs.JACE_RULES) + [rc.TYPE_NOTE, rc.FLOW_NOTE]
        self.assertEqual([x for x in texts if x not in en], [])

    def test_german_function_L_is_identity(self):
        self.assertEqual(report_parts.L("Hart"), "Hart")
        with english():
            self.assertEqual(report_parts.L("Hart"), "Hard")


if __name__ == "__main__":
    unittest.main()
