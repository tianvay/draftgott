"""Synergiewert eines Decks aus den geparsten Kartenfeldern (components/cards.Card).

Jede Karte bekommt Tags: was sie dem Deck GIBT (Geber, z. B. Lebensgewinn, +1/+1-Marken, Nichtkreatur-Zauber) und
wovon sie PROFITIERT (Nehmer, z. B. "Whenever you gain life", Prowess, Auren brauchen gute Traeger). Aktive Synergie
(Marken verteilen, buffen, Schutz verteilen, Auren) steht als Nehmer "Kreaturen" bzw. "gute Traeger" drin, passive
(Ausloeser unter Bedingungen) als Nehmer der passenden Ressource.

Deckwert (deck_synergy): Fuer jede Kopie eines Nehmers zaehlen die Geber-Einheiten k der Ressource im Deck (ohne die
eigene Kopie). Erfuellung = 1 - (1 - p)^k (abnehmender Grenznutzen, p je Ressource in RESOURCES). Punkte = Gewicht
des Nehmers x Erfuellung. Der Deckwert ist die Summe. Nehmer mit Erfuellung unter ORPHAN gelten als "ohne Partner".
Laender zaehlen nicht (Landfall ist in jedem Deck erfuellt und sagt nichts ueber die Passung).

Pick (pick_bonus): Zuwachs des Deckwerts, wenn die Pack-Karte zum Pool kommt, mal PICK_WEIGHT, hoechstens PICK_MAX.
"""
from components.cards import Card
from components.i18n import t

ORPHAN = 0.35
GREEN, YELLOW = 6.0, 3.5  # Ampel fuer den Deckwert je 40 Karten (Bericht)
PICK_WEIGHT = 2.0
PICK_MAX = 2.0

RESOURCES = {  # Schluessel: (Anzeige, p je Geber-Einheit)
    "counters": ("+1/+1-Marken", 0.2),
    "buff": ("Buffs, Auren, Ausrüstung", 0.2),
    "protection": ("Schutz (Hexproof, Indestructible)", 0.3),
    "carrier": ("Gute Träger (Ausweichen, Schutz)", 0.15),
    "creature": ("Kreaturen", 0.08),
    "lifegain": ("Lebensgewinn", 0.2),
    "spells": ("Nichtkreatur-Zauber", 0.12),
    "surveil": ("Surveil", 0.2),
    "tokens": ("Kreatur-Token", 0.2),
    "sac_outlet": ("Opfer-Möglichkeiten", 0.3),
    "fodder": ("Opferbares (Token, Sterbe-Ausloeser)", 0.2),
    "graveyard": ("Friedhof füllen", 0.15),
    "artifacts": ("Artefakte", 0.15),
    "enchantments": ("Verzauberungen", 0.2),
    "legendary": ("Legendäre Karten", 0.2),
    "planeswalker": ("Planeswalker", 0.3),
    "jace": ("Jace", 0.35),
    "noncombat": ("Schaden außerhalb des Kampfs", 0.25),
    "discard": ("Abwerfen", 0.25),
    "defender": ("Defender / Toughness > Power", 0.15),
    "small": ("Kleine Kreaturen (P oder T ≤ 1)", 0.15),
    "targets_opp": ("Zauber mit Ziel beim Gegner", 0.2),
}
TYPE_P = 0.15  # Ressource "type:<Kreaturtyp>"

CARRIER_KW = ("flying", "menace", "trample", "double strike", "hexproof", "indestructible", "shroud")
PROTECT_KW = ("hexproof", "indestructible", "shroud")

# Einfache Felder: belegt -> Ressource (Geber: Menge je Kopie, Nehmer: Gewicht)
GIVES = {
    # +1/+1-Marken
    "enters_counters": (("counters", 1),), "x_counters": (("counters", 1),), "combat_buff": (("counters", 1),),
    "enter_counter": (("counters", 1),), "combat_counter": (("counters", 1),),
    "surveil_counter_all": (("counters", 2),), "surveil_pay": (("counters", 1),),
    "ally_enter_counter": (("counters", 2),), "death_ally_counter": (("counters", 1),),
    "cast_counter": (("counters", 1),), "target_cast_counter": (("counters", 1),), "sac_counter": (("counters", 1),),
    "protect_counter": (("counters", 1),), "land_sac_counters": (("counters", 1),), "hydra_spread": (("counters", 2),),
    "data_counter": (("counters", 1),), "draw_counter": (("counters", 1),), "endstep_counters": (("counters", 1),),
    "death_watch_counter": (("counters", 1),), "sac_klingon": (("counters", 1),),
    "main1_counter_mana": (("counters", 1),), "channel_counter": (("counters", 1),), "tap2_counter": (("counters", 1),),
    "yoshi_counter": (("counters", 1),), "wizard_token_counters": (("counters", 1),),
    "artifact_sac_counter": (("counters", 1),), "combat_exile_counter": (("counters", 1),),
    "loyalty_counter": (("counters", 1),), "noncombat_counter": (("counters", 1),),
    "counter_plus_one": (("counters", 1),), "mbenga": (("counters", 1),),
    # Buffs, Auren, Ausruestung
    "aura_pump": (("buff", 1),), "equip_kw": (("buff", 1),), "team_kw": (("buff", 1),),
    "team_kw_all": (("buff", 1),), "cast_team_pump": (("buff", 1),), "lead_pump": (("buff", 1),),
    "fed_pump": (("buff", 1),), "kira_pump": (("buff", 1),), "attack_target": (("buff", 1),),
    "artifact_pump": (("buff", 1),), "token_pump": (("buff", 1),), "token_kw": (("buff", 1),),
    "surveil_team_pump": (("buff", 1),), "noncombat_team_pump": (("buff", 1),), "combat_pump_power": (("buff", 1),),
    "pump_tough": (("buff", 1),), "aura_etb_kw": (("buff", 1),), "grant_ward": (("buff", 1), ("protection", 1)),
    "equip_token": (("buff", 1),), "equip_etb": (("buff", 1),),
    # Schutz
    "liliana_hexproof": (("protection", 1),), "needs_many": (("protection", 1),),
    "bones_protect": (("protection", 1),), "mccoy_save": (("protection", 1),),
    # Lebensgewinn
    "etb_life": (("lifegain", 1),), "death_life": (("lifegain", 1),), "spell_life": (("lifegain", 1),),
    "landfall_life": (("lifegain", 2),), "attack_drain": (("lifegain", 2),), "ally_enter_life": (("lifegain", 2),),
    "creature_enter_life": (("lifegain", 2),), "ally_death_life": (("lifegain", 1),), "food": (("lifegain", 1),),
    "equip_attack_life": (("lifegain", 2),), "gy_bottom_life": (("lifegain", 1),), "discard_life": (("lifegain", 1),),
    "tell_me": (("lifegain", 1), ("surveil", 1)), "georgiou": (("lifegain", 1),), "tea_ability": (("lifegain", 1),),
    # Surveil
    "surveil": (("surveil", 1), ("graveyard", 0.5)), "upkeep_surveil": (("surveil", 2), ("graveyard", 1)),
    "enter_surveil": (("surveil", 2),), "sac_surveil": (("surveil", 1),), "equip_attack_surveil": (("surveil", 2),),
    # Token
    "death_tokens": (("tokens", 1), ("creature", 1), ("fodder", 1)), "upkeep_token": (("tokens", 2), ("creature", 2)),
    "life_tokens": (("tokens", 1), ("creature", 1)), "cast_token": (("tokens", 2), ("creature", 2)),
    "surveil_tokens": (("tokens", 1), ("creature", 1)), "combat_token": (("tokens", 1), ("creature", 1)),
    "stage_token": (("tokens", 1), ("creature", 1)), "equip_carrier": (("tokens", 1), ("creature", 1)),
    "activation_tokens": (("tokens", 1), ("creature", 1)), "land_to_tokens": (("tokens", 1), ("creature", 1)),
    "tribble_copy": (("tokens", 2), ("creature", 2)), "token_copy": (("tokens", 1), ("creature", 1)),
    "station_combat_token": (("tokens", 1), ("creature", 1)), "end_dilemma_tokens": (("tokens", 1),),
    "kobayashi": (("tokens", 1), ("creature", 1)), "death_token_copy": (("tokens", 1), ("fodder", 1)),
    # Opfern
    "sac_draw": (("sac_outlet", 1),), "sac_trample_draw": (("sac_outlet", 1),), "edict_cost": (("sac_outlet", 1),),
    "kicker_sac": (("sac_outlet", 0.5),), "sac_creature_cost": (("sac_outlet", 1),), "dahar_sac": (("sac_outlet", 1),),
    "targ_sac": (("sac_outlet", 0.5),),
    "death_draw": (("fodder", 1),), "death_bolt": (("fodder", 1), ("noncombat", 1)),
    "death_heartwood": (("fodder", 1), ("artifacts", 1)), "death_counters_move": (("fodder", 1),),
    "end_sacrifice": (("fodder", 1),),
    # Friedhof
    "mill_self": (("graveyard", 2),), "mill_land": (("graveyard", 2),), "etb_mill_land": (("graveyard", 2),),
    "ally_enter_mill": (("graveyard", 3),), "loot": (("graveyard", 1), ("discard", 1)),
    "rummage_spell": (("graveyard", 1), ("discard", 1)), "attack_loot": (("graveyard", 2), ("discard", 2)),
    "alone_loot": (("graveyard", 1), ("discard", 1)), "discard_first": (("graveyard", 1), ("discard", 1)),
    "land_to_graveyard": (("graveyard", 1),), "main1_loot_lands": (("graveyard", 1), ("discard", 1)),
    "etb_loot_stun": (("graveyard", 2), ("discard", 2)), "draw_abilities": (("graveyard", 1), ("discard", 1)),
    "hand_removal": (("graveyard", 1), ("discard", 1)), "etb_discard_enchant": (("discard", 1),),
    "etb_tutor_any": (("discard", 1),), "flashback_discard": (("discard", 1),),
    "legend_discard_draw": (("discard", 1),),
    # Artefakte
    "is_artifact": (("artifacts", 1),), "treasure": (("artifacts", 1),), "heartwood": (("artifacts", 1),),
    "etb_clue": (("artifacts", 1),), "planet_tokens": (("artifacts", 1),), "attack_planet": (("artifacts", 2),),
    "planet_ability": (("artifacts", 1),), "treasure_ability": (("artifacts", 2),), "quark": (("artifacts", 2),),
    "death_watch_treasure": (("artifacts", 1),), "lifegain_lotus": (("artifacts", 1),),
    # Verzauberungen
    "is_enchantment": (("enchantments", 1),),
    # Planeswalker und Jace
    "is_planeswalker": (("planeswalker", 1),), "is_jace": (("jace", 1),), "pw_tutor": (("planeswalker", 1),),
    "entrust": (("planeswalker", 0.5),),
    # Schaden ausserhalb des Kampfs
    "attack_ping": (("noncombat", 2),), "tap_ping": (("noncombat", 2),), "ally_death_ping": (("noncombat", 1),),
    "discard_ping": (("noncombat", 1),), "opp_enter_ping": (("noncombat", 1),),
    "opp_loyalty_ping": (("noncombat", 1),), "enchant_cast_draw": (("noncombat", 1),),
    # Sonstiges
    "legendary": (("legendary", 1),), "targets_opp": (("targets_opp", 1),),
}

WANTS = {
    # +1/+1-Marken
    "counter_vigilance": (("counters", 1),), "counter_haste": (("counters", 1),), "counter_kw": (("counters", 1),),
    "death_counters_move": (("counters", 0.5),), "counter_hit_draw": (("counters", 1.5),),
    "mccoy_save": (("counters", 1),), "counter_plus_one": (("counters", 1),), "data_draw": (("counters", 0.5),),
    "mbenga": (("counters", 1),),
    # Kreaturen als Ziel aktiver Synergie (verteilen, buffen, schuetzen)
    "combat_buff": (("creature", 0.5),), "hydra_spread": (("creature", 1),), "surveil_counter_all": (("creature", 1),),
    "ally_enter_counter": (("creature", 1),), "lead_pump": (("creature", 0.5),), "fed_pump": (("creature", 0.5),),
    "team_kw": (("creature", 1),), "cast_team_pump": (("creature", 1), ("spells", 1)),
    "surveil_team_pump": (("creature", 0.5), ("surveil", 1)), "token_pump": (("tokens", 1),),
    "token_kw": (("tokens", 1),), "attack_target": (("creature", 0.5),), "combat_pump_power": (("creature", 0.5),),
    "liliana_hexproof": (("creature", 0.5),), "needs_many": (("creature", 0.5),),
    # Kreatur kommt ins Spiel
    "ally_enter_life": (("creature", 1),), "ally_enter_pump": (("creature", 1),), "ally_untap": (("creature", 0.5),),
    "enter_counter": (("creature", 1),), "ally_enter_mill": (("creature", 0.5),), "enter_surveil": (("creature", 0.5),),
    "creature_enter_life": (("creature", 1),), "kira_pump": (("creature", 1),), "explore_enter": (("creature", 1),),
    "cast_blink": (("creature", 1),), "omni_free": (("creature", 1),),
    # Auren und Ausruestung: gute Traeger und Schutz
    "aura_pump": (("carrier", 1), ("protection", 0.5)), "aura_kw": (("carrier", 0.5), ("protection", 0.5)),
    "aura_return": (("carrier", 0.5),), "equip": (("carrier", 1),), "equip_kw": (("carrier", 0.5),),
    "equipped_attack_kw": (("buff", 1),), "own_target_draw": (("buff", 1),), "twin": (("carrier", 0.5),),
    "grant_ward": (("carrier", 0.5),),
    # Lebensgewinn
    "lifegain_counter": (("lifegain", 1.5),), "lifegain_draw": (("lifegain", 1.5),),
    "lifegain_loyalty": (("lifegain", 1),), "confidant": (("lifegain", 1.5),), "lifegain_lotus": (("lifegain", 1),),
    "lifegain_perpetual": (("lifegain", 1),), "double_life_draw": (("lifegain", 1),), "life_tokens": (("lifegain", 1),),
    "lifegain_double": (("lifegain", 1.5),),
    # Nichtkreatur-Zauber
    "prowess": (("spells", 1),), "cast_counter": (("spells", 1.5),), "cast_token": (("spells", 1.5),),
    "spell_discount": (("spells", 1),), "data_counter": (("spells", 1),), "cast_untap": (("spells", 0.5),),
    "cast_charge": (("spells", 1),), "verse": (("spells", 1.5),), "split_second": (("spells", 0.5),),
    "gray_copy": (("spells", 1),), "codie_copy": (("spells", 0.5),),
    # Surveil
    "surveil_tokens": (("surveil", 1.5),), "surveil_pay": (("surveil", 1),), "surveil_attack": (("surveil", 1),),
    "surveil_self_pump": (("surveil", 1),),
    # Token
    "end_untap_tokens": (("tokens", 1),), "wizard_token_counters": (("tokens", 1),), "token_copy": (("tokens", 1),),
    "holo_tokens": (("tokens", 1),), "officer_token_power": (("tokens", 1),),
    # Sterben und Opfern
    "ally_death_ping": (("fodder", 1), ("sac_outlet", 0.5)), "ally_death_life": (("fodder", 1),),
    "death_loyalty": (("fodder", 1),), "phoenix": (("fodder", 1), ("sac_outlet", 0.5)),
    "death_ally_counter": (("fodder", 1),), "death_watch_counter": (("fodder", 1),),
    "death_watch_treasure": (("fodder", 1),), "charge_on_death": (("fodder", 1),),
    "sac_counter": (("fodder", 1),), "sac_draw": (("fodder", 1),), "sac_trample_draw": (("fodder", 1),),
    "sac_surveil": (("fodder", 1),), "sac_klingon": (("fodder", 1),), "edict_cost": (("fodder", 0.5),),
    "death_draw": (("sac_outlet", 0.5),), "death_tokens": (("sac_outlet", 0.5),), "death_bolt": (("sac_outlet", 0.5),),
    "death_token_copy": (("sac_outlet", 0.5),), "death_heartwood": (("sac_outlet", 0.5),),
    "death_life": (("sac_outlet", 0.5),),
    # Friedhof
    "gy_power": (("graveyard", 1),), "gy_step_power": (("graveyard", 1),), "threshold_bonus": (("graveyard", 1),),
    "threshold_power": (("graveyard", 1),), "threshold_kw": (("graveyard", 1),), "gy_x": (("graveyard", 1),),
    "cast_threshold": (("graveyard", 1.5),), "flashback": (("graveyard", 0.5),), "gy_ability": (("discard", 0.5),),
    "gy_draw": (("discard", 0.5),), "gy_return": (("discard", 0.5),), "reanimate": (("graveyard", 1),),
    "goyf": (("graveyard", 1),), "eye_threshold": (("graveyard", 1),), "uldaros_cast": (("graveyard", 1),),
    "fed_copy": (("graveyard", 0.5),), "gy_leave": (("graveyard", 1),), "threshold_exile": (("graveyard", 1),),
    "threshold_sac_minus": (("graveyard", 0.5),), "exhaust_reanimate": (("graveyard", 1),),
    "holodeck": (("graveyard", 1),), "gy_cast": (("discard", 0.5),), "beam": (("graveyard", 0.5),),
    "scotty": (("graveyard", 1),), "combat_exile_counter": (("graveyard", 1),), "null_summoner": (("graveyard", 1),),
    # Abwerfen
    "discard_life": (("discard", 1),), "channel_counter": (("discard", 0.5),), "discard_ping": (("discard", 1),),
    # Artefakte
    "artifact_pump": (("artifacts", 1.5),), "tap_artifacts": (("artifacts", 1),), "artifact_vigilance": (("artifacts", 1),),
    "artifact_count_power": (("artifacts", 1.5),), "artifact_hit_draw": (("artifacts", 1),),
    "artifact_hit_token": (("artifacts", 1),), "artifact_kw_ability": (("artifacts", 1),),
    "tap3_draw": (("artifacts", 1),), "etb_artifact_colors_draw": (("artifacts", 1),),
    "artifact_sac_counter": (("artifacts", 1),), "treasure_pump": (("artifacts", 1),),
    "artifact_tokens_dragons": (("artifacts", 1),), "overflow_cast": (("artifacts", 1),),
    "untap_on_cast": (("artifacts", 0.5),), "aerid_pump": (("artifacts", 1),), "artifact_mana": (("artifacts", 1),),
    "zefram_top": (("artifacts", 1),), "charge_double": (("artifacts", 1),), "tap2_counter": (("creature", 0.5),),
    "animate_artifact": (("artifacts", 1),),
    # Verzauberungen
    "enchant_cast_draw": (("enchantments", 1.5),), "dathon_counter": (("enchantments", 1),),
    # Planeswalker und Jace
    "walker_grants": (("planeswalker", 1),), "walker_no_death": (("planeswalker", 1),),
    "loyalty_draw": (("planeswalker", 1),), "loyalty_paradox": (("planeswalker", 1),),
    "kiora_attack": (("planeswalker", 1),), "pw_discount": (("planeswalker", 1),),
    "memorial_pw_mana": (("planeswalker", 1),), "next_pw_discount": (("planeswalker", 1),),
    "loyalty_counter": (("planeswalker", 1),), "tomik_guard": (("planeswalker", 0.5),),
    "copy_grant": (("planeswalker", 0.5),), "entrust": (("planeswalker", 1),),
    "behold_jace": (("jace", 1),), "jace_vigilance": (("jace", 1),), "jace_instant": (("jace", 1),),
    "empower": (("jace", 0.5),),  # Empower ist ein Zusatz, ohne Jace bleibt die Karte spielbar
    # Schaden ausserhalb des Kampfs
    "noncombat_kw": (("noncombat", 1),), "noncombat_counter": (("noncombat", 1),),
    "noncombat_team_pump": (("noncombat", 1.5),), "noncombat_seek": (("noncombat", 1),),
    "noncombat_recur": (("noncombat", 1),),
    # Sonstiges
    "defender_attack": (("defender", 1.5),), "toughness_damage": (("defender", 1.5),),
    "small_unblockable": (("small", 1.5),), "target_cast_counter": (("targets_opp", 1),),
    "yoshi_counter": (("legendary", 1),), "legend_discard_draw": (("legendary", 1),),
}

# Felder mit eigener Auswertung in card_tags
SPECIAL = ("is_land", "is_creature", "is_aura", "power", "toughness", "kw", "modes", "grant_kw", "aura_kw",
           "protect_spell", "etb_grant", "etb_grant_plain", "team_grant", "creature_types", "creates_tokens",
           "cond_static", "mission", "type_haste", "equip_typed", "defender", "self_discount", "cast_trig",
           "became_tapped", "pw_tags", "is_instant_sorcery", "lifegain_counter", "counter_kw")

# Felder ohne Synergie-Bezug (Kosten, Landlogik, eigenstaendige Effekte, interne Marker). Neue Card-Felder muessen
# in GIVES, WANTS, SPECIAL oder hier stehen (Test test_every_card_field_is_classified).
NEUTRAL = (
    "mv", "alts", "land_colors", "haste", "tap_mode", "tap_arg", "land_types", "name", "is_basic", "cycle_alts",
    "cycle_target", "cycle_mv", "empower_text", "draws", "prepared", "is_copy", "mana_src", "landfall",
    "self_damage", "is_instant", "flash", "removal", "discard", "abilities", "combat_draw", "gy_ability_sorcery",
    "is_token", "sac_mana", "opp_spell_tax", "extra_cost", "hexproof_until_damage", "alt_draws",
    "finality", "combat_land_return", "domain_power", "x_search_basics", "choices", "is_mode", "removal_exile",
    "removal_points", "hand_pick", "attack_exile_gy", "own_turn_kw", "debuff", "impulse",
    "impulse_mark", "combat_draw_ability", "counter", "uncounterable", "ward", "life_loss",
    "exile_until", "sac_perm_removal", "sac_perm_draw", "perm_destroy", "tuck_top_damage", "etb_lands_needed",
    "victim_treasure", "sac_removal", "sweep_ability", "loyalty_start", "pw_abilities", "pw_static", "hits_walkers",
    "enter_pw_too", "etb_remove_counters", "etb_stun_opp", "opp_cheap_cast_life",
    "etb_basic_tapped", "unprepare", "opp_exile_instead", "alone_double_strike", "combat_lock", "nexus_mana",
    "abs_damage", "no_untap", "no_enter_triggers", "equip_attack_choice", "hand_combat_bolt", "identity_echo",
    "arena_prepare", "codie_prepare", "rescue_bounce", "hall_copy", "damage_ramp", "cast_untap_lands",
    "hand_exile_land", "fblthp_lost", "untap_target", "empower_x", "restricted_mana", "hapatra_untap", "alone_kw",
    "attack_self", "vehicle", "attack_tap", "equip_attack_tap", "conjured", "lib_creature_minus", "debuff_perpetual",
    "gy_conjure", "hand_pick_gift", "etb_conjure", "red_plus_one", "opp_etb_life", "station", "modes_untapped",
    "gy_top_creature", "cant_block", "cant_attack_alone", "evade_power", "evade_artifact", "attack_choices",
    "land_swap", "land_sac_ability", "mill_take", "opp_loss", "basic_type", "basic_planet", "etb_basic_hand",
    "attack_power", "end_assimilate", "cube_assimilate", "death_charge", "from_gy", "reliant_return", "gy_draw_loss",
    "gy_bottom_ability", "etb_tap_opp", "spacecraft_hexproof", "untap_ability", "artifact_shroud", "target_token",
    "fed_dig", "fed_draw", "fed_mana", "top_dig", "reveal_lands", "tutor", "draw_double", "landfall_mana", "kicker",
    "counter_mv", "mirror_copy", "officer_tutor", "kira_attack", "nog_levels", "nog_officer", "etb_mana",
    "end_discard", "pump_death_draw", "team_mana", "dukat", "modes_all_empty_hand", "self_sac_destroy",
    "bones_return", "gy_hate", "lorca_return", "dilemma_bounce_self", "cast_from_exile", "exile_removal",
    "opp_minus_power", "hand_exile", "kai_name", "uhura_number", "bluff", "caretaker", "threaten_mv",
    "sunburst_bomb", "peace", "infiltrate", "zefram_charge", "cloak_hexproof", "charge_impulse", "warp_charge",
    "cast_copy", "communicator_unblock", "seven_79", "ghost_blink", "miles_bounce", "returned_draw", "q_stack",
    "riker_lands", "extra_land", "top_lands", "genesis_swap", "discover", "ds9_reveal", "saboteur_copy",
    "phase_lock", "sisko_dig", "gwyndala_copy", "lwaxana_echo", "dilemma_trig", "snw", "saga", "forest_pump",
    "targeted_draw", "draw3_token",
)

CLASSIFIED = set(GIVES) | set(WANTS) | set(SPECIAL) | set(NEUTRAL)


def _add(d, key, value):
    if value:
        d[key] = round(d.get(key, 0) + value, 2)


def card_tags(card):
    """{"gives": {Ressource: Menge je Kopie}, "wants": {Ressource: Gewicht}} einer Card (JSON-tauglich).
    Laender bekommen keine Tags."""
    gives, wants = {}, {}
    if card is None or card.is_land:
        return {"gives": gives, "wants": wants}
    defaults = _DEFAULTS
    for field, pairs in GIVES.items():
        if getattr(card, field, None) not in (None, getattr(defaults, field, None)):
            for res, n in pairs:
                _add(gives, res, n)
    for field, pairs in WANTS.items():
        if getattr(card, field, None) not in (None, getattr(defaults, field, None)):
            for res, w in pairs:
                wants[res] = max(wants.get(res, 0), w)
    if card.is_creature:
        _add(gives, "creature", 1)
        for t in card.creature_types:
            _add(gives, "type:" + t, 1)
        if card.defender or card.toughness > card.power:
            _add(gives, "defender", 1)
        if card.power <= 1 or card.toughness <= 1:
            _add(gives, "small", 1)
        if any(k in CARRIER_KW for k in card.kw) or card.small_unblockable or card.evade_power or card.ward:
            _add(gives, "carrier", 1)
    elif not card.is_land:
        _add(gives, "spells", 1)
    if "lifelink" in card.kw:
        _add(gives, "lifegain", 1)
    for mode in card.modes:
        for eff in mode:
            if eff[0] in ("counter", "counter_all"):
                _add(gives, "counters", 1)
                wants["creature"] = max(wants.get("creature", 0), 1 if eff[0] == "counter_all" else 0.5)
            elif eff[0] in ("pump", "pump_all"):
                _add(gives, "buff", 1)
                wants["carrier"] = max(wants.get("carrier", 0), 0.5)
    for field in ("grant_kw", "aura_kw", "protect_spell", "etb_grant", "team_grant"):
        words = getattr(card, field)
        if words:
            _add(gives, "buff", 1)
            if any(w in PROTECT_KW for w in words):
                _add(gives, "protection", 1)
                wants["creature"] = max(wants.get("creature", 0), 0.5)
    if card.etb_grant_plain:
        _add(gives, "protection", 1)
    if card.is_aura:
        wants["carrier"] = max(wants.get("carrier", 0), 1)
        wants["protection"] = max(wants.get("protection", 0), 0.5)
    for n, _token in card.creates_tokens:
        _add(gives, "tokens", n)
        _add(gives, "creature", n)
        _add(gives, "fodder", n)
    if card.counter_kw:
        wants["counters"] = max(wants.get("counters", 0), 1)
    if card.lifegain_counter:
        _n, typ = card.lifegain_counter  # (Marken, Typ) - "self": nur auf sich (Dr. Beverly Crusher)
        _add(gives, "counters", 1)
        if typ != "self":
            wants["type:" + typ] = 1
    for cond, *_rest in card.cond_static:
        if cond[0] == "gained":
            wants["lifegain"] = max(wants.get("lifegain", 0), 1)
        elif cond[0] == "another" and len(cond) > 1:
            wants["type:" + str(cond[1])] = 1
        elif cond[0] == "gy_creatures":
            wants["graveyard"] = max(wants.get("graveyard", 0), 1)
    if card.mission:
        res = {"artifact_enters": "artifacts", "noncreature_cast": "spells", "creature_dies": "fodder",
               "creature_enters": "creature"}.get(card.mission[0])
        if res:
            wants[res] = max(wants.get(res, 0), 1)
    if card.type_haste:
        wants["type:" + card.type_haste] = 1
    if card.equip_typed:
        wants["type:" + card.equip_typed[0]] = 1
        wants["carrier"] = max(wants.get("carrier", 0), 1)
    for disc in card.self_discount:
        res = {"legendary": "legendary", "noncreature": "spells"}.get(disc)
        if res:
            wants[res] = max(wants.get(res, 0), 1)
    for filt, *_rest in card.cast_trig:
        if filt == "noncreature":
            wants["spells"] = max(wants.get("spells", 0), 1.5)
        elif str(filt).startswith("type:"):
            wants[filt] = 1
    tapped = card.became_tapped[:1]  # ein Effekt, z. B. ("life", 2)
    if tapped == ("life",):
        _add(gives, "lifegain", 1)
    elif tapped == ("loot",):
        _add(gives, "discard", 1)
    if "pw_help" in card.pw_tags:
        wants["planeswalker"] = max(wants.get("planeswalker", 0), 1)
    if card.equip and len(card.equip) > 3 and card.equip[3]:
        wants["counters"] = max(wants.get("counters", 0), 1)
    if card.equip:
        _add(gives, "buff", 1)
    return {"gives": gives, "wants": wants}


_DEFAULTS = Card(False, 0, (), (), False, False, 0, 0)


def _p(res):
    return TYPE_P if res.startswith("type:") else RESOURCES.get(res, ("", 0.2))[1]


def label(res):
    if res.startswith("type:"):
        return t("Kreaturtyp {typ}", typ=res[5:].title())
    return t(RESOURCES.get(res, (res,))[0])


def deck_synergy(entries):
    """entries: [{"name", "qty", "syn": card_tags}]. Gibt {"score", "rows", "orphans"} zurueck; rows: je Nehmer und
    Ressource {"name", "qty", "resource", "label", "weight", "givers" (Einheiten ohne eigene Kopie), "fill",
    "points" (alle Kopien), "partners": [{"name", "n"}]}, nach Punkten absteigend."""
    totals, by_res = {}, {}
    for e in entries:
        for res, n in ((e.get("syn") or {}).get("gives") or {}).items():
            totals[res] = totals.get(res, 0) + n * e.get("qty", 1)
            by_res.setdefault(res, []).append((e["name"], n * e.get("qty", 1)))
    rows = []
    for e in entries:
        syn = e.get("syn") or {}
        qty = e.get("qty", 1)
        for res, w in (syn.get("wants") or {}).items():
            k = totals.get(res, 0) - (syn.get("gives") or {}).get(res, 0)
            fill = 1 - (1 - _p(res)) ** max(k, 0)
            partners = sorted(({"name": n, "n": round(v - ((syn.get("gives") or {}).get(res, 0) if n == e["name"]
                                                         else 0), 2)} for n, v in by_res.get(res, [])),
                              key=lambda p: (-p["n"], p["name"]))
            rows.append({"name": e["name"], "qty": qty, "resource": res, "label": label(res), "weight": w,
                         "givers": round(max(k, 0), 2), "fill": round(fill, 3), "points": round(w * fill * qty, 3),
                         "partners": [p for p in partners if p["n"] > 0]})
    rows.sort(key=lambda r: (-r["points"], r["name"], r["resource"]))
    score = round(sum(r["points"] for r in rows), 2)
    orphans = [r for r in rows if r["fill"] < ORPHAN and r["weight"] >= 1]
    return {"score": score, "rows": rows, "orphans": orphans}


def pick_bonus(pool, card):
    """(Bonus, Partner-Namen) fuer eine Pack-Karte {"name", "syn"} zum Pool [{"name", "qty", "syn"}]."""
    base = deck_synergy(pool)["score"]
    new = dict(card, qty=1)
    delta = deck_synergy(list(pool) + [new])["score"] - base
    bonus = round(min(PICK_MAX, max(0.0, delta * PICK_WEIGHT)), 1)
    if bonus <= 0:
        return 0, []
    syn = card.get("syn") or {}
    gives, wants = syn.get("gives") or {}, syn.get("wants") or {}
    partners = []
    for e in pool:
        other = e.get("syn") or {}
        if e["name"] == card["name"] or e["name"] in partners:
            continue
        if set(wants) & set(other.get("gives") or {}) or set(gives) & set(other.get("wants") or {}):
            partners.append(e["name"])
    return bonus, partners


def level(score, deck_size):
    """Ampel fuer den Deckwert: "green" ab GREEN, "yellow" ab YELLOW (je 40 Karten), sonst "red"."""
    s = (deck_size or 40) / 40
    return "green" if score + 1e-9 >= GREEN * s else ("yellow" if score + 1e-9 >= YELLOW * s else "red")


def variant_synergy(pool, marks, basics=None):
    """Drafthelper: Synergiewert je Variante. pool: Kartenangaben mit "name", "qty", "land", "syn"; marks: je Karte
    die Markierung jeder Kopie (core/splash/nosplash/off); basics: {Landname: {core, splash, nosplash}}. Gibt
    {"splash"|"nosplash": {"score", "level", "cards", "orphans": ["Name (Ressource, ...)"]}} zurueck."""
    out = {}
    for g in ("splash", "nosplash"):
        entries, cards = [], 0
        for c, ms in zip(pool, marks):
            n = sum(1 for m in ms if m in ("core", g))
            cards += n
            if n and not c.get("land"):
                entries.append({"name": c["name"], "qty": n, "syn": c.get("syn") or {}})
        cards += sum(int((b or {}).get("core") or 0) + int((b or {}).get(g) or 0) for b in (basics or {}).values())
        res = deck_synergy(entries)
        missing = {}
        for r in res["orphans"]:
            missing.setdefault(r["name"], []).append(r["label"])
        out[g] = {"score": res["score"], "level": level(res["score"], cards), "cards": cards,
                  "orphans": [f"{n} ({', '.join(ls)})" for n, ls in sorted(missing.items())]}
    return out


def entries_from_rows(rows):
    """Bericht: ctx["rows"] (Name, Anzahl, Card, Text) -> Eintraege fuer deck_synergy."""
    return [{"name": n, "qty": q, "syn": card_tags(c)} for n, q, c, _s in rows]
