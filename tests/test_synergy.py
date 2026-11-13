"""Synergiewert eines Decks (components/synergy.py): Geber/Nehmer-Tags je Karte, Deckwert mit Saettigung,
Synergie-Zuwachs einer Pack-Karte zum Pool und Einfluss auf die Pick-Reihenfolge im Live-Draft."""
import json
import unittest

from components import cardarchetypes, synergy
from components.cards import Card
from components.livedraft import card_summary
from tests.fixtures import CARDS


def mk(name="X", creature=True, power=2, toughness=2, **kw):
    return Card(False, 2, (), (), creature, kw.pop("is_aura", False), power, toughness, name=name, **kw)


def entry(card, qty=1):
    return {"name": card.name, "qty": qty, "syn": synergy.card_tags(card)}


INSTANT = mk("Shock", creature=False, power=0, toughness=0, is_instant_sorcery=True, is_instant=True)
PROWESS = mk("Monk", prowess=True)
LIFE = mk("Healer", etb_life=2)
PAYOFF = mk("Bloombrute", lifegain_draw=1)
BEAR = mk("Bear")


class CardTagsTest(unittest.TestCase):
    def test_noncreature_spell_gives_spells_and_prowess_wants_them(self):
        self.assertIn("spells", synergy.card_tags(INSTANT)["gives"])
        self.assertIn("spells", synergy.card_tags(PROWESS)["wants"])
        self.assertNotIn("spells", synergy.card_tags(BEAR)["gives"])

    def test_lifegain_giver_and_payoff(self):
        self.assertIn("lifegain", synergy.card_tags(LIFE)["gives"])
        self.assertIn("lifegain", synergy.card_tags(PAYOFF)["wants"])
        self.assertIn("lifegain", synergy.card_tags(mk("Vamp", kw=("lifelink",)))["gives"])

    def test_counter_distributor_gives_counters_and_wants_creatures(self):
        tags = synergy.card_tags(mk("Mentor", modes=((("counter", 1, 1),),)))
        self.assertIn("counters", tags["gives"])
        self.assertIn("creature", tags["wants"])
        self.assertIn("counters", synergy.card_tags(mk("Gallia", counter_haste=True))["wants"])

    def test_aura_wants_carriers_and_protection(self):
        aura = synergy.card_tags(mk("Pump Aura", creature=False, is_aura=True, aura_pump=(2, 2)))
        self.assertIn("buff", aura["gives"])
        self.assertIn("carrier", aura["wants"])
        self.assertIn("protection", aura["wants"])
        self.assertIn("carrier", synergy.card_tags(mk("Bird", kw=("flying",)))["gives"])
        shield = synergy.card_tags(mk("Shield", creature=False, is_instant_sorcery=True, grant_kw=("hexproof",)))
        self.assertIn("protection", shield["gives"])

    def test_creature_type_payoff(self):
        self.assertIn("type:thopter", synergy.card_tags(mk("Saheeli", type_haste="thopter"))["wants"])
        self.assertIn("type:thopter", synergy.card_tags(mk("Thopter", creature_types=("thopter",)))["gives"])

    def test_tags_are_json(self):
        tags = synergy.card_tags(mk("Mentor", modes=((("counter", 1, 1),),), creature_types=("human",)))
        self.assertEqual(json.loads(json.dumps(tags)), tags)

    def test_every_card_field_is_classified(self):
        missing = [f for f in Card._fields if f not in synergy.CLASSIFIED]
        self.assertEqual(missing, [], "neue Card-Felder in synergy.py als Geber, Nehmer oder NEUTRAL eintragen")

    def test_card_summary_carries_tags(self):
        self.assertIn("spells", card_summary(CARDS["Test Spell"], "Test Spell")["syn"]["gives"])
        self.assertEqual(card_summary(None, "Unbekannt")["syn"], {"gives": {}, "wants": {}})


class DeckSynergyTest(unittest.TestCase):
    def test_more_givers_more_synergy(self):
        none = synergy.deck_synergy([entry(PROWESS, 2), entry(BEAR, 6)])
        some = synergy.deck_synergy([entry(PROWESS, 2), entry(INSTANT, 6)])
        self.assertEqual(none["score"], 0)
        self.assertGreater(some["score"], 0)

    def test_saturation(self):
        six = synergy.deck_synergy([entry(PROWESS), entry(INSTANT, 6)])["score"]
        twelve = synergy.deck_synergy([entry(PROWESS), entry(INSTANT, 12)])["score"]
        self.assertGreater(twelve, six)
        self.assertLess(twelve, 2 * six)

    def test_own_copy_does_not_satisfy_itself(self):
        solo = mk("Graft", enters_counters=1, counter_vigilance=True)
        self.assertEqual(synergy.deck_synergy([entry(solo)])["score"], 0)
        self.assertGreater(synergy.deck_synergy([entry(solo, 2)])["score"], 0)

    def test_rows_name_partners_and_orphans(self):
        res = synergy.deck_synergy([entry(PAYOFF), entry(LIFE, 3), entry(PROWESS)])
        row = next(r for r in res["rows"] if r["name"] == "Bloombrute")
        self.assertEqual(row["resource"], "lifegain")
        self.assertEqual(row["givers"], 3)
        self.assertEqual([p["name"] for p in row["partners"]], ["Healer"])
        self.assertIn("Monk", [r["name"] for r in res["orphans"]])
        self.assertNotIn("Bloombrute", [r["name"] for r in res["orphans"]])

    def test_lands_are_ignored(self):
        land = Card(True, 0, (), ("W",), False, False, 0, 0, name="Plains", is_basic=True)
        self.assertEqual(synergy.deck_synergy([entry(land, 17)])["score"], 0)


class PickBonusTest(unittest.TestCase):
    def test_bonus_for_payoff_with_givers_in_pool(self):
        pool = [entry(INSTANT), entry(INSTANT), entry(BEAR)]
        bonus, partners = synergy.pick_bonus(pool, entry(PROWESS))
        self.assertGreater(bonus, 0)
        self.assertEqual(partners, ["Shock"])
        self.assertEqual(synergy.pick_bonus([entry(BEAR)], entry(PROWESS))[0], 0)

    def test_bonus_for_giver_with_payoffs_in_pool(self):
        bonus, partners = synergy.pick_bonus([entry(PROWESS), entry(PROWESS)], entry(INSTANT))
        self.assertGreater(bonus, 0)
        self.assertEqual(partners, ["Monk"])

    def test_bonus_is_capped(self):
        pool = [entry(mk(f"Monk {i}", prowess=True)) for i in range(15)]
        self.assertLessEqual(synergy.pick_bonus(pool, entry(INSTANT))[0], synergy.PICK_MAX)


class RankTest(unittest.TestCase):
    def pack_card(self, card):
        return {"name": card.name, "colors": ["R"], "syn": synergy.card_tags(card)}

    def test_synergy_moves_card_up(self):
        pack = [self.pack_card(BEAR), self.pack_card(PROWESS)]
        pool = [self.pack_card(INSTANT) for _ in range(4)]
        plain = cardarchetypes.rank(pack, {}, {}, None)
        self.assertEqual([c["name"] for c in plain], ["Bear", "Monk"])
        ranked = cardarchetypes.rank(pack, {}, {}, None, pool=pool)
        self.assertEqual([c["name"] for c in ranked], ["Monk", "Bear"])
        monk = ranked[0]
        self.assertGreater(monk["synergy"], 0)
        self.assertEqual(monk["syn_with"], ["Shock"])
        self.assertEqual(monk["points"], 1.5 + monk["synergy"])
        self.assertEqual(ranked[1]["synergy"], 0)

    def test_neverplay_stays_zero(self):
        ranked = cardarchetypes.rank([self.pack_card(PROWESS)], {"Monk": "neverplay"}, {}, None,
                                     pool=[self.pack_card(INSTANT)] * 4)
        self.assertEqual(ranked[0]["points"], 0)

    def test_pool_outside_archetype_colors_does_not_count(self):
        blue = dict(self.pack_card(INSTANT), colors=["U"])
        ranked = cardarchetypes.rank([self.pack_card(PROWESS)], {}, {}, "RW", pool=[blue] * 4)
        self.assertEqual(ranked[0]["synergy"], 0)


class ReportTest(unittest.TestCase):
    def ctx(self, cards):
        return {"rows": [(c.name, q, c, "") for c, q in cards]}

    def test_section_lists_payoffs_and_orphans(self):
        from components.report_cards import render_synergy_table
        html = render_synergy_table(self.ctx([(PAYOFF, 1), (LIFE, 3), (PROWESS, 2)]))
        self.assertIn("Synergie-Punkte", html)
        self.assertIn("Bloombrute", html)
        self.assertIn("Healer", html)
        self.assertIn("Ohne Partner", html)
        self.assertIn("Monk", html)

    def test_no_section_without_payoffs(self):
        from components.report_cards import render_synergy_table
        self.assertEqual(render_synergy_table(self.ctx([(BEAR, 10)])), "")


if __name__ == "__main__":
    unittest.main()
