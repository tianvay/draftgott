import unittest

from components.coverage import (M_FLOW, M_LETHAL, M_MANA, M_NONE, M_UNKNOWN, STATUS_TEXT, _classify, analyze_card,
                                 line_modelled, metrics_of, summarize)

DASH = "—"


def sc(name="Test", type_line=f"Creature {DASH} Test", text="", cost="{1}{W}", keywords=(), layout="normal",
       faces=None, power="2", toughness="2"):
    d = {"name": name, "type_line": type_line, "mana_cost": cost, "oracle_text": text, "keywords": list(keywords),
         "layout": layout, "power": power, "toughness": toughness}
    if faces:
        d["card_faces"] = faces
    return d


def cats(card):
    return {c for c, _m, _l in analyze_card(card)}


class NothingToFlagTests(unittest.TestCase):
    def test_vanilla_creature(self):
        self.assertEqual(analyze_card(sc()), [])

    def test_combat_keywords_without_an_opponent_are_not_flagged(self):
        card = sc(text="Flying, trample\nVigilance\nMenace\nDeathtouch, lifelink\nWard {2}",
                  keywords=["Flying", "Trample", "Vigilance", "Menace", "Deathtouch", "Lifelink", "Ward"])
        self.assertEqual(analyze_card(card), [])

    def test_reminder_text_is_ignored(self):
        card = sc(text="Flying (This creature can't be blocked except by creatures with flying.)", keywords=["Flying"])
        self.assertEqual(analyze_card(card), [])

    def test_modeled_keywords_haste_and_defender(self):
        self.assertEqual(analyze_card(sc(text="Haste", keywords=["Haste"])), [])
        self.assertEqual(analyze_card(sc(text="Defender", keywords=["Defender"])), [])

    def test_basic_land(self):
        land = sc("Plains", f"Basic Land {DASH} Plains", "({T}: Add {W}.)", cost="")
        self.assertEqual(analyze_card(land), [])

    def test_planeswalker_condition_land_is_modeled(self):
        land = sc("Commons", "Land", "This land enters tapped unless you control a planeswalker.\n{T}: Add {W} or {U}.",
                  cost="")
        self.assertEqual(analyze_card(land), [])

    def test_behold_a_jace_land_is_modeled(self):
        land = sc("Sanctum", f"Land {DASH} Island",
                  "({T}: Add {U}.)\nAs this land enters, you may behold a Jace. If you don't, this land enters tapped.",
                  cost="")
        self.assertEqual(analyze_card(land), [])

    def test_empower_jace_lines_are_modeled(self):
        self.assertEqual(analyze_card(sc(type_line="Sorcery", text="Empower Jace 1.", keywords=["Empower Jace"])), [])
        creature = sc(text="When this creature enters, empower Jace 2.", keywords=["Empower Jace"])
        self.assertEqual(analyze_card(creature), [])

    def test_landcycling_is_modeled(self):
        card = sc(text="Basic landcycling {2} ({2}, Discard this card: Search your library for a basic land card.)",
                  keywords=["Landcycling", "Basic landcycling", "Cycling", "Typecycling"])
        self.assertEqual(analyze_card(card), [])

    def test_aura_enchant_line_is_modeled(self):
        card = sc(type_line=f"Enchantment {DASH} Aura", text="Enchant creature", keywords=["Enchant"])
        self.assertEqual(analyze_card(card), [])


class CategoryTests(unittest.TestCase):
    def check(self, text, category, metric, **kw):
        found = analyze_card(sc(text=text, **kw))
        self.assertIn((category, metric), {(c, m) for c, m, _l in found}, found)

    def test_tokens(self):
        self.check("Whenever you roll a die, create a 1/1 black Rat creature token.", "Tokens erzeugen", M_LETHAL)  # erfunden: Wuerfeln gibt es nicht
        self.assertEqual(analyze_card(sc(text="When this creature enters, create a 2/2 colorless Wizard Soldier "
                                               "creature token named Cadet.")), [])  # modelliert

    def test_direct_damage(self):
        self.check("At the beginning of your upkeep, Test Spell deals 1 damage to each opponent.", "Direkter Schaden",
                   M_LETHAL)
        self.check("Whenever an opponent casts a spell with mana value 2 or less, Test deals 1 damage to each "
                   "opponent.", "Direkter Schaden", M_LETHAL)
        self.assertEqual(analyze_card(sc(text="Whenever this creature attacks, it deals 1 damage to each opponent and "
                                               "you gain 1 life.")), [])  # modelliert (Screeching Soulbreaker)

    def test_haste_for_others(self):
        self.check("Creature tokens you control have haste.", "Haste verleihen", M_LETHAL)
        self.assertEqual(analyze_card(sc(text="Creatures you control have haste.")), [])  # modelliert (Samut)

    def test_mana_outside_lands(self):
        self.check("{1}, {T}: Add {R}{G}.", "Mana außer Ländern", M_MANA)
        self.check("Sacrifice this creature: Add {C}.", "Mana außer Ländern", M_MANA)

    def test_card_flow(self):
        self.check("Whenever you gain life, draw a card.", "Kartenfluss", M_FLOW)
        self.check("Whenever another creature you control enters, surveil 1.", "Kartenfluss", M_FLOW)
        self.check("Search your library for a basic land card, put it onto the battlefield tapped.", "Kartenfluss",
                   M_FLOW, type_line="Sorcery")

    def test_cost_reduction(self):
        # Kostensenkung wie bei Traxos, Ghalta, Wrath of the Bloodmane und Geist ist modelliert, Convoke nicht
        for text in ("This spell costs {2} less to cast if you've cast a noncreature spell this turn.",
                     "This spell costs {X} less to cast, where X is the greatest power among creatures you control.",
                     "This spell costs {1} less to cast if you control a legendary creature.",
                     "Noncreature spells you cast cost {1} less to cast."):
            self.assertEqual(analyze_card(sc(text=text)), [], text)
        self.check("Convoke", "Kostensenkung / Convoke", M_MANA, keywords=("Convoke",))

    def test_counters_and_bonuses(self):
        self.check("Whenever this creature attacks, put a +1/+1 counter on target creature.", "Zählmarken / Stärkebonus",
                   M_LETHAL)
        self.check("Equipped creature gets +2/+1.", "Zählmarken / Stärkebonus", M_LETHAL,
                   type_line=f"Artifact {DASH} Equipment")

    def test_interaction_with_the_opponent_has_no_metric(self):
        self.check("Exile target card from an opponent's graveyard.", "Interaktion mit dem Gegner", M_NONE,
                   type_line="Sorcery")
        self.check("Tap target creature an opponent controls. It doesn't untap during its controller's next untap "
                   "step.", "Interaktion mit dem Gegner", M_NONE, type_line="Sorcery")
        for text in ("Destroy target creature.", "Exile target creature or planeswalker."):  # Removal ist modelliert
            self.assertEqual(analyze_card(sc(text=text, type_line="Instant")), [], text)

    def test_life_gain_has_no_metric(self):
        self.check("Whenever a creature an opponent controls dies, you gain 1 life.", "Lebensgewinn", M_NONE)
        self.assertEqual(analyze_card(sc(text="You gain 3 life.", type_line="Instant")), [])  # modelliert
        self.assertEqual(analyze_card(sc(text="Whenever an opponent casts a spell with mana value 2 or less, you gain 2 "
                                               "life.")), [])  # modelliert (Solarium Sentry)

    def test_flashback_keyword_and_line(self):
        self.check("Flashback—{2}, Sacrifice a creature.", "Zweitverwertung (Friedhof)", M_MANA, type_line="Sorcery",
                   keywords=["Flashback"])
        self.assertEqual(analyze_card(sc(text="Flashback {4}{W}", type_line="Sorcery", keywords=["Flashback"])), [])

    def test_prowess_and_flash_keywords_are_modelled(self):
        self.assertEqual(analyze_card(sc(text="Prowess", keywords=["Prowess"])), [])
        self.assertEqual(analyze_card(sc(text="Flash", keywords=["Flash"])), [])

    def test_plain_cycling_is_card_flow(self):
        self.check("Cycling {2}", "Kartenfluss", M_FLOW, type_line="Instant", keywords=["Cycling"])

    def test_unknown_text_is_reported_as_unknown(self):
        found = analyze_card(sc(text="Whenever you sacrifice a permanent, put a bounty counter on it."))
        self.assertEqual({(c, m) for c, m, _l in found}, {("Unbekannter Effekt", M_UNKNOWN)})

    def test_one_card_can_have_several_categories_and_keeps_the_line(self):
        card = sc("Mixed", text=("Flying\nWhenever an opponent casts a spell with mana value 2 or less, Mixed deals 1 "
                                 "damage to each opponent.\nWhenever you roll a die, create a 1/1 black Rat creature token.\nCreature tokens you control have "
                                 "haste."), keywords=["Flying"])
        found = analyze_card(card)
        self.assertEqual(cats(card), {"Direkter Schaden", "Tokens erzeugen", "Haste verleihen"})
        self.assertTrue(all(isinstance(line, str) and line for _c, _m, line in found))
        self.assertEqual(metrics_of(found), {M_LETHAL})

    def test_empower_with_variable_amount_is_flagged(self):
        card = sc(text="Whenever this creature attacks, empower Jace X, where X is the number of cards in your hand.",
                  keywords=["Empower Jace"])  # X nach eigenen Kreaturen (Repurposed Enforcer) ist modelliert
        self.assertIn("Empower Jace (Wert nicht modelliert)", cats(card))

    def test_conditional_land_with_unparsed_condition_is_flagged(self):
        land = sc("Odd Land", "Land",
                  "This land enters tapped unless you reveal a Forest card from your hand.\n{T}: Add {G}.", cost="")
        self.assertIn("Land: Bedingung nicht modelliert", cats(land))


class SpecialCardTests(unittest.TestCase):
    def test_prepare_layout_adds_the_prepared_category(self):
        faces = [
            {"name": "Foreseer", "type_line": f"Creature {DASH} Wizard", "mana_cost": "{3}{U}",
             "oracle_text": "This creature enters prepared. (While it's prepared, you may cast a copy of its spell.)"},
            {"name": "Peer Review", "type_line": "Sorcery", "mana_cost": "{2}{U}",
             "oracle_text": "Create a 1/1 black Rat creature token for each creature that died this turn. Surveil 1."}]
        card = sc("Foreseer // Peer Review", f"Creature {DASH} Wizard // Sorcery", layout="prepare", faces=faces,
                  keywords=["Prepared"])
        self.assertEqual(cats(card), {"Tokens erzeugen"})  # Kopie modelliert (Mana, Surveil 1), Token nicht
        self.assertEqual(metrics_of(analyze_card(card)), {M_LETHAL})

    def test_planeswalker_ability_without_other_category(self):
        card = sc("Walker", f"Legendary Planeswalker {DASH} Ajani", "0: Put a loyalty counter on target planeswalker.",
                  cost="{2}{W}", power=None, toughness=None)
        self.assertIn("Planeswalker-Fähigkeit", cats(card))

    def test_planeswalker_ability_with_a_known_effect_uses_that_category(self):
        card = sc("Walker", f"Legendary Planeswalker {DASH} Ajani",
                  "+1: Create a 1/1 blue Illusion creature token for each opponent.", cost="{2}{U}", power=None,
                  toughness=None)
        self.assertIn("Tokens erzeugen", cats(card))

    def test_aura_bonus_is_flagged(self):
        card = sc(type_line=f"Enchantment {DASH} Aura", text="Enchant creature\nWhenever you roll a die, enchanted "
                  "creature gets +1/+1 until end of turn.", keywords=["Enchant"])
        self.assertEqual(cats(card), {"Zählmarken / Stärkebonus"})  # erfunden: Wuerfeln gibt es nicht
        card = sc(type_line=f"Enchantment {DASH} Aura", text="Enchant creature\nEnchanted creature gets +2/+2.",
                  keywords=["Enchant"])
        self.assertEqual(analyze_card(card), [])  # eigene Aura mit Bonus ist modelliert


class FoundByReviewTests(unittest.TestCase):
    """Faelle aus der Durchsicht der FRA-Karten."""

    def test_token_creation_next_to_empower_on_one_line_is_not_swallowed(self):
        card = sc(type_line="Sorcery", keywords=["Empower Jace"],
                  text="Create a 1/1 black Rat creature token for each creature that died this turn. Empower Jace 2. "
                       "(Put two loyalty counters on a Jace token you control.)")
        self.assertEqual(cats(card), {"Tokens erzeugen"})

    def test_modal_header_after_a_trigger_is_not_an_effect(self):
        self.assertEqual(analyze_card(sc(text="When this creature enters, choose one —")), [])

    def test_granting_combat_keywords_has_no_metric(self):
        found = analyze_card(sc(type_line="Enchantment", text="Creature tokens you control have vigilance."))
        self.assertEqual({(c, m) for c, m, _l in found}, {("Schlüsselwort verleihen", M_NONE)})

    def test_tapping_the_enchanted_creature_is_interaction(self):
        self.assertIn("Interaktion mit dem Gegner",
                      cats(sc(type_line=f"Enchantment {DASH} Aura", keywords=["Enchant"],
                              text="Enchant creature" + chr(10) + "When this Aura enters, tap enchanted creature.")))

    def test_base_power_and_toughness_change_is_a_bonus(self):
        self.assertIn("Zählmarken / Stärkebonus", cats(sc(
            type_line="Instant", text="Target creature has base power and toughness 1/1 until end of turn.")))

    def test_additional_cost_is_flagged_as_cost_condition(self):
        found = analyze_card(sc(type_line="Instant",
                                text="As an additional cost to cast this spell, exile two cards from your graveyard."))
        self.assertIn(("Zusatzkosten", M_MANA), {(c, m) for c, m, _l in found})

    def test_deckbuilding_rule_text_is_ignored(self):
        self.assertEqual(analyze_card(sc(type_line="Instant",
                                         text="A deck can have any number of cards named Test Spell.")), [])

    def test_ability_word_line_is_classified_by_its_text_not_as_a_keyword(self):
        card = sc(text="Threshold — Creatures you control get +1/+0 as long as there are seven or more cards in your "
                       "graveyard.", keywords=["Threshold"])
        self.assertIn("Zählmarken / Stärkebonus", cats(card))
        self.assertNotIn("Unbekannter Effekt", cats(card))
        self.assertEqual(analyze_card(sc(text="Threshold — This creature gets +1/+0 and has flying as long as there are "
                                               "seven or more cards in your graveyard.", keywords=["Threshold"])), [])

    def test_defender_exception_is_its_own_category(self):
        line = "as long as you've scried or surveilled this turn, this creature can attack as though it didn't have " \
            "defender."
        self.assertIn(("Defender-Ausnahme", M_LETHAL), set(_classify(line, False)))  # Einordnung, wenn offen
        self.assertEqual(analyze_card(sc(text=line, keywords=["Defender"])), [])  # Surveillance Phantasm: modelliert


class MoreInteractionPatternsTests(unittest.TestCase):
    def test_damage_to_creatures_in_all_phrasings_is_interaction(self):
        for text in ("test spell deals 5 damage to target black or green creature or planeswalker.",
                     "test spell deals 1 damage to each creature and planeswalker your opponents control.",
                     "target creature you control deals damage equal to its power to target creature.",
                     "destroy all creatures that aren't of the chosen type.",
                     "target opponent reveals their hand. you choose a nonland card from it.",
                     "when this creature attacks, exile up to one target card from a graveyard."):
            self.assertIn(("Interaktion mit dem Gegner", M_NONE), set(_classify(text, False)), text)
        found = {(c, m) for c, m, _l in analyze_card(sc(
            type_line="Sorcery", text="When this creature attacks, exile up to one target card from a graveyard."))}
        self.assertIn(("Interaktion mit dem Gegner", M_NONE), found)  # weiterhin offen

    def test_unblockable_is_a_granted_combat_property(self):
        found = {(c, m) for c, m, _l in analyze_card(sc(
            text="Another target creature you control can't be blocked this turn."))}
        self.assertIn(("Schlüsselwort verleihen", M_NONE), found)

    def test_damage_to_the_opponent_stays_direct_damage_not_interaction(self):
        found = {c for c, _m, _l in analyze_card(sc(text="Whenever an opponent casts a spell with mana value 2 or "
                                                         "less, Test Spell deals 2 damage to target opponent."))}
        self.assertEqual(found, {"Direkter Schaden"})


class ModelFilterTests(unittest.TestCase):
    """Zeilen, die das Kartenmodell erkennt (Goldfish und/oder Kampfmodell), stehen nicht mehr in der Abdeckung;
    teilweise erkannte Zeilen behalten ihren offenen Rest."""

    def test_line_modelled(self):
        card = sc(type_line="Sorcery")
        self.assertTrue(line_modelled(card, card, "Destroy target creature."))
        self.assertFalse(line_modelled(card, card, "Exile target card from an opponent's graveyard."))

    def test_recognised_line_is_not_flagged_but_the_open_rest_stays(self):
        self.assertEqual(analyze_card(sc(type_line="Sorcery", text="Destroy target creature.")), [])
        self.assertEqual(analyze_card(sc(type_line="Sorcery", text="Draw a card. Destroy target creature.")), [])
        found = cats(sc(type_line="Sorcery", text="Draw a card. Exile target card from an opponent's graveyard."))
        self.assertEqual(found, {"Interaktion mit dem Gegner"})
        found = cats(sc(type_line="Sorcery", keywords=["Empower Jace"],
                        text="Create a 1/1 black Rat creature token for each creature that died this turn. Empower "
                             "Jace 2."))
        self.assertEqual(found, {"Tokens erzeugen"})


class SummaryTests(unittest.TestCase):
    def test_summary_counts_cards_not_copies_per_metric(self):
        data = {
            "Token": analyze_card(sc(text="Whenever you roll a die, create a 1/1 black Rat creature token.")),
            "Burn": analyze_card(sc(text="At the beginning of your upkeep, Burn deals 1 damage to each opponent.")),
            "Removal": analyze_card(sc(type_line="Sorcery", text="Exile target card from an opponent's graveyard.")),
            "Odd": analyze_card(sc(text="Whenever you sacrifice a permanent, put a bounty counter on it.")),
            "Vanilla": analyze_card(sc()),
        }
        qty = {"Token": 4, "Burn": 2, "Removal": 1, "Odd": 1, "Vanilla": 10}
        s = summarize(data, qty)
        self.assertEqual(s["flagged_cards"], 4)
        self.assertEqual(s["flagged_copies"], 8)
        self.assertEqual(s["by_metric"][M_LETHAL], 2)
        self.assertEqual(s["by_metric"][M_NONE], 1)
        self.assertEqual(s["by_metric"][M_UNKNOWN], 1)
        self.assertEqual(s["by_metric"][M_MANA], 0)

    def test_status_text_is_the_one_the_user_asked_for(self):
        self.assertEqual(STATUS_TEXT, "To Do: Noch nicht implementiert")


if __name__ == "__main__":
    unittest.main()
