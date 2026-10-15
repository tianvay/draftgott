"""Flash, Deathtouch und Removal-Score: Erkennung, Zaehlung (Seite und Bericht), Ampel und Bericht."""
import shutil
import unittest

from components.removal import keyword_flags, removal_info, removal_level

DASH = "—"


def card(text, type_line="Instant", name="Test Card", keywords=(), faces=None, layout="normal"):
    d = {"name": name, "type_line": type_line, "oracle_text": text, "keywords": list(keywords), "layout": layout,
         "mana_cost": "{1}"}
    if faces:
        d["card_faces"] = faces
    return d


def points(text, **kw):
    info = removal_info(card(text, **kw))
    return info["points"] if info else 0.0


def kind(text, **kw):
    info = removal_info(card(text, **kw))
    return info["kind"] if info else None


CREATURE = f"Creature {DASH} Test"


class KeywordTests(unittest.TestCase):
    def test_flash_on_a_permanent(self):
        self.assertEqual(keyword_flags(card("Flash\nWhen this creature enters, draw a card.", CREATURE,
                                            keywords=["Flash"])), ["flash"])

    def test_flash_on_an_instant_does_not_count(self):
        self.assertEqual(keyword_flags(card("Flash", "Instant", keywords=["Flash"])), [])

    def test_deathtouch(self):
        self.assertEqual(keyword_flags(card("Deathtouch", CREATURE, keywords=["Deathtouch"])), ["deathtouch"])
        self.assertEqual(keyword_flags(card("Flash, deathtouch", CREATURE, keywords=["Flash", "Deathtouch"])),
                         ["flash", "deathtouch"])

    def test_granting_deathtouch_does_not_count(self):
        self.assertEqual(keyword_flags(card("Creatures you control have deathtouch.", "Enchantment",
                                            keywords=["Deathtouch"])), [])

    def test_front_face_of_a_prepared_card(self):
        faces = [{"name": "Front", "type_line": CREATURE, "oracle_text": "Deathtouch\nThis creature enters prepared."},
                 {"name": "Back", "type_line": "Sorcery", "oracle_text": "Flash"}]
        self.assertEqual(keyword_flags(card("", f"{CREATURE} // Sorcery", faces=faces, layout="prepare",
                                            keywords=["Deathtouch", "Prepared"])), ["deathtouch"])


class HardRemovalTests(unittest.TestCase):
    def test_destroy_and_exile(self):
        self.assertEqual(points("Destroy target creature or planeswalker."), 1.0)
        self.assertEqual(points("Destroy target creature, enchantment, or planeswalker. Its controller creates two "
                                "Map tokens."), 1.0)
        self.assertEqual(points("Exile target creature or planeswalker. Test Card deals 1 damage to each opponent and "
                                "you gain 1 life."), 1.0)
        self.assertEqual(kind("Destroy target creature. If it wasn't attacking, its controller draws a card."), "Hart")

    def test_additional_cost_still_hard(self):
        self.assertEqual(points("As an additional cost to cast this spell, sacrifice a creature or planeswalker or pay "
                                "{3}.\nDestroy target creature or planeswalker.", type_line="Sorcery"), 1.0)

    def test_exile_until_leaves(self):
        self.assertEqual(points("When this enchantment enters, exile target nonland permanent an opponent controls "
                                "until this enchantment leaves the battlefield.", type_line="Enchantment"), 0.9)
        self.assertEqual(kind("When this Aura enters, exile target nonland permanent an opponent controls until this "
                              "Aura leaves the battlefield.", type_line=f"Enchantment {DASH} Aura"), "Exil bis verlassen")

    def test_sweeper(self):
        self.assertEqual(points("Choose a creature type. Destroy all creatures that aren't of the chosen type.",
                                type_line="Sorcery"), 1.0)
        self.assertEqual(kind("Destroy all creatures.", type_line="Sorcery"), "Massenremoval")


class ConditionalTests(unittest.TestCase):
    def test_conditions_on_the_target(self):
        for text in ("Destroy target creature with mana value 2 or less.",
                     "Exile target creature or planeswalker that's green or blue. Surveil 1.",
                     "Destroy target creature with toughness 4 or greater. You gain 1 life.",
                     "Destroy target creature with flying."):
            with self.subTest(text=text):
                self.assertEqual(points(text), 0.5)
                self.assertEqual(kind(text), "Bedingt")

    def test_conditional_exile_until_leaves(self):
        self.assertEqual(points("When this enchantment enters, exile target nonland permanent an opponent controls "
                                "with mana value 2 or less until this enchantment leaves the battlefield.",
                                type_line="Enchantment"), 0.5)

    def test_damage_with_condition_is_capped(self):
        self.assertEqual(points("Test Card deals 6 damage to target creature with flying."), 0.5)


class DamageTests(unittest.TestCase):
    def test_scale(self):
        for n, p in ((1, 0.2), (2, 0.4), (3, 0.6), (4, 0.8), (5, 0.9), (6, 0.9)):
            with self.subTest(n=n):
                self.assertEqual(points(f"Test Card deals {n} damage to target creature or planeswalker."), p)

    def test_any_target(self):
        self.assertEqual(points("Test Card deals 3 damage to any target.", type_line="Sorcery"), 0.6)
        self.assertEqual(kind("Test Card deals 3 damage to any target."), "Schaden")

    def test_minus_toughness(self):
        self.assertEqual(points("Target creature gets -3/-3 until end of turn."), 0.6)
        self.assertEqual(points("When this enchantment enters, target creature an opponent controls gets -3/-3 until "
                                "end of turn.", type_line="Enchantment"), 0.6)
        self.assertEqual(kind("Target creature gets -2/-2 until end of turn."), "−X/−X")

    def test_minus_power_only_is_no_removal(self):
        self.assertEqual(points("Target creature gets -5/-0 until end of turn."), 0.0)

    def test_variable_damage(self):
        self.assertEqual(points("Test Card deals X damage to target creature.", type_line="Sorcery"), 0.5)

    def test_etb_damage_of_a_creature(self):
        self.assertEqual(points("When this creature enters, it deals 4 damage to target creature an opponent "
                                "controls.", type_line=CREATURE), 0.8)


class OtherKindsTests(unittest.TestCase):
    def test_edict(self):
        self.assertEqual(points("Target opponent sacrifices a creature of their choice."), 0.7)
        self.assertEqual(points("Target opponent sacrifices a creature or planeswalker with the greatest mana value "
                                "among creatures and planeswalkers they control. You gain 2 life."), 0.9)
        self.assertEqual(points("Target opponent exiles a creature they control and their graveyard.",
                                type_line="Sorcery"), 0.7)
        self.assertEqual(kind("Target opponent sacrifices a creature of their choice."), "Edikt")

    def test_edict_with_own_sacrifice_is_conditional(self):
        self.assertEqual(points("When Winter enters, you may sacrifice a creature or planeswalker. When you do, each "
                                "opponent sacrifices a creature of their choice.", type_line=CREATURE, name="Winter"),
                         0.5)

    def test_fight(self):
        self.assertEqual(points("When Yoshi enters, another target creature you control fights up to one target "
                                "creature an opponent controls.", type_line=CREATURE, name="Yoshi"), 0.5)
        self.assertEqual(kind("Target creature you control fights target creature you don't control.",
                              type_line="Sorcery"), "Fight")

    def test_bounce(self):
        self.assertEqual(points("Return target creature to its owner's hand."), 0.3)
        self.assertEqual(kind("Return target creature to its owner's hand."), "Bounce")

    def test_lock_aura(self):
        self.assertEqual(points("Enchant creature\nEnchanted creature loses all abilities and doesn't untap during its "
                                "controller's untap step.", type_line=f"Enchantment {DASH} Aura"), 0.7)
        self.assertEqual(points("Enchant creature\nEnchanted creature can't attack or block.",
                                type_line=f"Enchantment {DASH} Aura"), 0.7)

    def test_modal_card_takes_the_best_mode(self):
        text = ("Choose one —\n• Counter target spell.\n• Test Card deals 5 damage to target creature or planeswalker."
                "\n• Return target creature to its owner's hand.")
        self.assertEqual(points(text), 0.9)

    def test_activated_ability_is_halved(self):
        self.assertEqual(points("{3}{G}, Discard this card: Destroy target creature with flying.", type_line=CREATURE),
                         0.25)
        self.assertEqual(points("{2}, {T}: Test Card deals 2 damage to target creature.", type_line=CREATURE), 0.2)
        self.assertEqual(kind("{2}, {T}: Test Card deals 2 damage to target creature.", type_line=CREATURE),
                         "Fähigkeit")

    def test_planeswalker_ability_is_halved(self):
        self.assertEqual(points("+1: Draw a card.\n−3: Test Card deals 4 damage to target creature.",
                                type_line=f"Legendary Planeswalker {DASH} Test"), 0.4)

    def test_other_triggers_are_halved(self):
        self.assertEqual(points("When Test Card dies, destroy up to one target nonland permanent.", type_line=CREATURE),
                         0.5)


class ToughnessZeroTests(unittest.TestCase):
    """Toughness 0 toetet die Kreatur (zustandsbasierte Aktion): 0,7 Punkte."""

    def test_multiply_by_zero(self):
        text = "Target creature has base power and toughness 0/0 until end of turn."
        self.assertEqual(points(text, type_line="Sorcery"), 0.7)
        self.assertEqual(kind(text, type_line="Sorcery"), "Toughness 0")

    def test_other_wordings(self):
        for text in ("Target creature becomes a 0/0 until end of turn.",
                     "Until end of turn, target creature an opponent controls has base toughness 0.",
                     "Target creature loses all abilities and has base power and toughness 3/0 until end of turn."):
            with self.subTest(text=text):
                self.assertEqual(points(text), 0.7)

    def test_toughness_above_zero_is_no_removal(self):
        self.assertIsNone(removal_info(card("Target creature loses all abilities and has base power and toughness "
                                            "0/1 until end of turn.")))
        self.assertIsNone(removal_info(card("Target creature you control has base power and toughness 0/0 until end "
                                            "of turn.")))

    def test_condition_and_ability(self):
        self.assertEqual(points("Target creature with flying has base power and toughness 0/0 until end of turn."), 0.5)
        self.assertEqual(points("{2}, {T}: Target creature has base power and toughness 0/0 until end of turn.",
                                type_line=CREATURE), 0.35)


class NoRemovalTests(unittest.TestCase):
    def test_not_removal(self):
        for text, type_line in (
                ("Counter target spell.", "Instant"),
                ("Return target spell to its owner's hand.", "Instant"),
                ("Test Card deals 1 damage to target opponent.", "Sorcery"),
                ("Whenever a creature you control attacks, that creature deals 1 damage to each opponent.", CREATURE),
                ("Exile up to one target card from a graveyard.", CREATURE),
                ("Exile the top card of your library. Until the end of your next turn, you may play that card.",
                 "Instant"),
                ("Destroy target artifact.", "Sorcery"),
                ("Target creature you control gets +2/+2 until end of turn.", "Instant"),
                ("Planeswalkers you control have \"[−4]: This planeswalker deals 2 damage to up to one target creature "
                 "and 2 damage to target player.\"", "Enchantment"),
                ("Sacrifice another creature or artifact: Put a +1/+1 counter on Test Card.", CREATURE),
        ):
            with self.subTest(text=text):
                self.assertIsNone(removal_info(card(text, type_line=type_line)))

    def test_text_is_kept_for_checking(self):
        info = removal_info(card("Destroy target creature or planeswalker."))
        self.assertEqual(info["text"], "Destroy target creature or planeswalker.")


class LevelTests(unittest.TestCase):
    def test_thresholds_for_forty_cards(self):
        self.assertEqual(removal_level(4.0, 40), "green")
        self.assertEqual(removal_level(3.9, 40), "yellow")
        self.assertEqual(removal_level(2.5, 40), "yellow")
        self.assertEqual(removal_level(2.4, 40), "red")

    def test_scaled_with_deck_size(self):
        self.assertEqual(removal_level(6.0, 60), "green")
        self.assertEqual(removal_level(5.0, 60), "yellow")


# ---------------- Zaehlung in Seite und Bericht

from tests.test_type_overview import run_js  # noqa: E402
from components.report_cards import render_type_table, type_counts  # noqa: E402


def copy(mark="core", **flags):
    d = {"kinds": ["creature"], "mark": mark, "empower": False, "points": 0, "flow": []}
    d.update(flags)
    return d


@unittest.skipUnless(shutil.which("node"), "Node.js nicht installiert")
class PageCountsTests(unittest.TestCase):
    def test_counts_per_variant(self):
        r = run_js([copy(flash=True), copy("splash", deathtouch=True), copy(removal=1.0), copy("nosplash", removal=0.6),
                    copy()], [])
        self.assertEqual((r["splash"]["flash"], r["nosplash"]["flash"]), (1, 1))
        self.assertEqual((r["splash"]["deathtouch"], r["nosplash"]["deathtouch"]), (1, 0))
        self.assertEqual((r["splash"]["removal"], r["nosplash"]["removal"]), (1, 2))
        self.assertAlmostEqual(r["nosplash"]["removal_points"], 1.6)

    def test_same_count_as_the_report(self):
        copies = [copy(flash=True), copy(flash=True, removal=0.5), copy(deathtouch=True, removal=1.0)]
        js = run_js(copies, [])["splash"]
        ctx = {"rows": [("A", 2, None, ""), ("B", 1, None, "")],
               "info": {"A": {"kinds": ["creature"], "flash": True, "removal": {"points": 0.5}},
                        "B": {"kinds": ["creature"], "deathtouch": True, "removal": {"points": 1.0}}}}
        # A zaehlt 2 Kopien: einmal ohne, einmal mit Removal ist in der Seite moeglich; hier gleiche Karte -> 2x
        py = type_counts(ctx)
        self.assertEqual((py["flash"], py["deathtouch"]), (js["flash"], js["deathtouch"]))
        self.assertEqual(py["removal"], 3)
        self.assertAlmostEqual(py["removal_points"], 2.0)

    def test_page_level_matches_python(self):
        import json
        import subprocess
        from components import drafthelper as dh
        page = dh.PAGE
        code = page[page.index("// BEGIN typeCounts"):page.index("// END typeCounts")]
        cases = [(4.0, 40), (3.9, 40), (2.5, 40), (2.4, 40), (6.0, 60), (5.0, 60), (0.0, 0)]
        script = code + chr(10) + "console.log(JSON.stringify(JSON.parse(process.argv[1]).map(c=>removalLevel(c[0],c[1]))));"
        out = subprocess.run(["node", "-e", script, json.dumps(cases)], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        css = {"green": "good", "yellow": "warn", "red": "bad"}
        self.assertEqual(json.loads(out.stdout), [css[removal_level(p, n)] for p, n in cases])

    def test_page_passes_the_fields(self):
        from tests.test_card_flow import run_copies_of
        out = run_copies_of([{"mark": "core", "card": {"kinds": ["creature"], "flash": True, "deathtouch": True,
                                                       "removal_points": 0.6}},
                             {"mark": "core", "card": {"kinds": ["creature"]}}])
        self.assertEqual((out[0]["flash"], out[0]["deathtouch"], out[0]["removal"]), (True, True, 0.6))
        self.assertEqual(set(out[1]), {"kinds", "mark", "empower", "points", "flow"})


class ReportTests(unittest.TestCase):
    def ctx(self):
        return {"rows": [("Kill", 4, None, ""), ("Bear", 19, None, "")],
                "info": {"Kill": {"kinds": ["instant"], "removal": {"points": 1.0, "kind": "Hart",
                                                                    "text": "Destroy target creature."}},
                         "Bear": {"kinds": ["creature"], "flash": True, "deathtouch": True}}}

    def test_type_table_rows(self):
        html = render_type_table(self.ctx())
        for label in ("Flash", "Deathtouch", "Removal (Karten)", "Σ Removal-Punkte"):
            self.assertIn(label, html)
        self.assertIn('class="good"', html)  # 4,0 Punkte bei 23 Karten -> gruen

    def test_removal_table(self):
        from components.report_cards import render_removal_table
        html = render_removal_table(self.ctx())
        self.assertIn("Kill", html)
        self.assertIn("Hart", html)
        self.assertIn("Destroy target creature.", html)
        self.assertEqual(render_removal_table({"rows": [("Bear", 1, None, "")], "info": {"Bear": {}}}), "")


class RemovalSectionTests(unittest.TestCase):
    RAW = {
        "Test Kill": {"name": "Test Kill", "type_line": "Instant", "mana_cost": "{1}{W}", "cmc": 2.0, "colors": ["W"],
                      "oracle_text": "Destroy target creature.", "keywords": [], "layout": "normal"},
        "Test Bolt": {"name": "Test Bolt", "type_line": "Instant", "mana_cost": "{W}", "cmc": 1.0, "colors": ["W"],
                      "oracle_text": "Test Bolt deals 3 damage to any target.", "keywords": [], "layout": "normal"},
    }

    def build(self, deck):
        from unittest import mock
        import mtg_sim
        from tests.fixtures import CARDS, args_for
        data = {**CARDS, **self.RAW}
        entries = [{"path": "", "name": "A", "deck": deck, "parts": []}]
        with mock.patch.object(mtg_sim, "fetch_cards_cached", lambda n, refresh=False: data):
            return mtg_sim.simulate_entries(entries, args_for(["deck.txt", "--sims", "100"]), progress=lambda m: None)

    def test_own_section_after_the_deck(self):
        html = self.build({"Plains": 17, "Test Bear": 19, "Test Kill": 2, "Test Bolt": 2})
        report, help_view = html[:html.index('id="view-help"')], html[html.index('id="view-help"'):]
        self.assertIn('id="removal"', report)
        self.assertLess(report.index('id="deck"'), report.index('id="removal"'))
        section = report[report.index('id="removal"'):report.index("</section>", report.index('id="removal"'))]
        for text in ("Test Kill", "Test Bolt", "Hart", "Schaden", "1.00", "0.60", "3.2", "Destroy target creature."):
            self.assertIn(text, section)
        deck = report[report.index('id="deck"'):report.index("</section>", report.index('id="deck"'))]
        self.assertNotIn("Erkannte Textstelle", deck)  # Tabelle steht nicht mehr im Abschnitt Deck
        self.assertIn('id="hiw-removal"', help_view)

    def test_no_section_without_removal(self):
        html = self.build({"Plains": 17, "Test Bear": 23})
        self.assertNotIn('id="removal"', html)
        self.assertNotIn('id="hiw-removal"', html)


if __name__ == "__main__":
    unittest.main()
