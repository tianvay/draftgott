"""FRA-Paket F: Abdeckung (schon modellierte Zeilen, bewusst nicht modellierte Zeilen) und leichte Regeln: "It gains
<Schluesselwort>" nach Marken (Konstrari Charm, Tam's Resistance), "Untap it" (Tethermage's Advantage), Empower X nach
exilierten Kreaturen (Overwrite the Multiverse) bzw. ueberschuessigem Schaden (Violent Echoes), Landfall-Empower
(Avatar of Burgeoning Echoes), Mana nur fuer Kopien (Heartwood Crafter) und nur fuer Planeswalker (Gideon's Memorial)."""
import unittest

from components import battle as bt
from components import simulation as sim
from components.coverage import analyze_card
from tests.test_package_fra_d import CRE, DASH, FOREST, HAWK, OGRE, TITAN, entry, make, on_board, pair
from tests.test_package_fra_e import BEAR


def sc(name, type_line, text, cost="{1}{W}", power="2", toughness="2", keywords=(), layout="normal", faces=None):
    d = {"name": name, "type_line": type_line, "mana_cost": cost, "oracle_text": text, "keywords": list(keywords),
         "layout": layout, "power": power, "toughness": toughness, "cmc": 2.0, "colors": ["W"]}
    if faces:
        d["card_faces"] = faces
    return d


ENFORCER = sc("Repurposed Enforcer", f"Creature {DASH} Human Soldier", "Whenever this creature attacks, empower Jace X, "
              "where X is the number of creatures you control. (Put that many loyalty counters on a Jace token you "
              "control. If you don't control one, first create a blue Jace planeswalker token with \"[−1]: Surveil 1\" "
              "and \"[−3]: Draw a card.\")")
CRIER = sc("Campus Crier", f"Creature {DASH} Human Advisor", "{1}, Exile this card from your graveyard: Empower Jace 2. "
           "(Put two loyalty counters on a Jace token you control.)")
SCULPTOR = sc("Jace, Reality Sculptor", f"Legendary Planeswalker {DASH} Jace", "+1: Empower Jace X, where X is the "
              "number of Islands you control.\n−3: Until your next turn, whenever a creature attacks you or a "
              "planeswalker you control, it gets -5/-0 until end of turn.\n0: Exile all but the bottom card of each "
              "opponent's library. Activate only if there are twenty-five or more loyalty counters among Jaces you "
              "control.", cost="{3}{U}{U}")
ARENA_SC = {"name": "Hexhaven Dueling Arena", "type_line": "Land", "mana_cost": "", "keywords": [], "layout": "normal",
            "oracle_text": "{T}: Add {C}.\n{2}, {T}: Target creature that attacked this turn becomes prepared. Activate "
            "only as a sorcery.\n{4}, {T}: Target creature becomes prepared.", "produced_mana": ["C"]}
BLADES = sc("Warrior's Blades", f"Artifact {DASH} Equipment", "When this Equipment enters, it deals 3 damage to any "
            "target and you gain 3 life.\nEquipped creature gets +2/+1.\nEquip {3}. This ability costs {1} less to "
            "activate for each +1/+1 counter on the creature it targets.", cost="{2}{R}{W}", power=None,
            toughness=None)
RELIC = sc("Lich's Relic", f"Artifact {DASH} Equipment", "When this Equipment enters, you may pay {2}. When you do, for "
           "each opponent, destroy up to one target creature or planeswalker that player controls.\nEquipped creature "
           "gets +2/+1.\nEquip {2}", cost="{B}", power=None, toughness=None)
SUMMONER = sc("Null Summoner", f"Creature {DASH} Human Warlock", "When this creature enters, if you cast it, target "
              "opponent reveals their hand. You choose a nonland card from it. Exile that card.\nThreshold — As long "
              "as there are seven or more cards in your graveyard, you may cast the exiled card, and mana of any type "
              "can be spent to cast that spell.", cost="{2}{U}{B}")
TECHNICIAN = sc("Tether Technician", f"Creature {DASH} Minotaur Artificer", "Reach\nWhen this creature enters, you may "
                "discard a card. When you do, this creature deals 2 damage to any target.", cost="{4}{R}",
                keywords=["Reach"])
PROXY = sc("Theorist's Proxy", f"Creature {DASH} Illusion", "{U}, Sacrifice this creature: The next spell you cast this "
           "turn can't be countered.", cost="{1}{U}")
MARWYN = sc("Marwyn, the Preserver", f"Legendary Creature {DASH} Elf Druid", "Lands you control have hexproof.\n{2}: "
            "Return target land card from your graveyard to your hand.", cost="{1}{G}")
SHAPER = sc("Paradox Shaper", f"Creature {DASH} Octopus Wizard", "{2}: Put target card from your graveyard on the "
            "bottom of your library.", cost="{1}{U/B}")  # Prepare-Zeile: siehe echte Karte (Layout prepare)
APPROACH = sc("Sphinx's Approach", "Instant", "Draw two cards. Then you may exile this spell and four cards named "
              "Sphinx's Approach from your graveyard. If you do, search your library for a Sphinx creature card, put "
              "it onto the battlefield, then shuffle.", cost="{1}{U}{U}", power=None, toughness=None)
OVERWRITE_SC = sc("Overwrite the Multiverse", "Sorcery", "Exile all creatures. Empower Jace X, where X is the number of "
                  "creatures exiled this way.", cost="{4}{B}{B}", power=None, toughness=None)
ECHOES_SC = sc("Violent Echoes", "Instant", "Violent Echoes deals 6 damage to target creature or planeswalker. If excess "
               "damage was dealt to that permanent this way, empower Jace X, where X is that excess damage.",
               cost="{2}{R}{R}", power=None, toughness=None)
AVATAR_SC = sc("Avatar of Burgeoning Echoes", f"Creature {DASH} Avatar", "Landfall — Whenever a land you control "
               "enters, empower Jace 2.\nPlaneswalkers you control have \"[−10]: Put a +1/+1 counter on target creature "
               "for each land you control.\"", cost="{G}{U}")
CHARM_SC = sc("Konstrari Charm", "Instant", "Choose one —\n• Konstrari Charm deals 6 damage to target creature with "
              "flying.\n• Put two +1/+1 counters on target creature. It gains trample until end of turn.\n• Add "
              "{C}{C}{C}.", cost="{R}{G}", power=None, toughness=None)
RESIST_SC = sc("Tam's Resistance", "Sorcery", "Put a +1/+1 counter on up to one target creature. It gains vigilance "
               "until end of turn.\nEmpower Jace 4.", cost="{1}{G/U}", power=None, toughness=None)
ADVANTAGE_SC = sc("Tethermage's Advantage", "Instant", "Target creature gets +2/+2 and gains reach until end of turn. "
                  "Untap it.", cost="{G}", power=None, toughness=None)
MEMORIAL_SC = sc("Gideon's Memorial", "Legendary Artifact", "Creature tokens you control get +1/+0 and have vigilance.\n"
                 "{T}: Add one mana of any color. Spend this mana only to cast a planeswalker spell.\n{1}{W}, Discard "
                 "this card: It deals 4 damage to target attacking or blocking creature.", power=None, toughness=None)
CRAFTER_SC = sc("Heartwood Crafter // Soul Tether", f"Creature {DASH} Elf Artificer // Sorcery", "", cost="",
                layout="prepare", faces=[
                    {"name": "Heartwood Crafter", "type_line": f"Creature {DASH} Elf Artificer", "mana_cost": "{G}",
                     "power": "1", "toughness": "1", "oracle_text": "This creature enters prepared.\n{T}: Add {C}. "
                     "This mana can't be spent to cast spells from your hand."},
                    {"name": "Soul Tether", "type_line": "Sorcery", "mana_cost": "{2}{R/G}",
                     "oracle_text": "Create a Heartwood token."}])


def lines(card):
    return [line for _c, _m, line in analyze_card(card)]


class CoverageTests(unittest.TestCase):
    def test_modelled_lines_are_not_flagged(self):
        for card in (ENFORCER, CRIER, ARENA_SC, BLADES, RELIC, SUMMONER, TECHNICIAN):
            self.assertEqual(lines(card), [], card["name"])

    def test_sculptor_only_the_zero_ability(self):
        self.assertEqual(lines(SCULPTOR), [])  # die 0-Faehigkeit ist seit Paket G modelliert

    def test_on_purpose_not_modelled(self):
        for card in (PROXY, MARWYN, SHAPER, APPROACH):
            self.assertEqual(lines(card), [], card["name"])

    def test_new_rules_are_modelled(self):
        for card in (OVERWRITE_SC, ECHOES_SC, AVATAR_SC, CHARM_SC, RESIST_SC, ADVANTAGE_SC, MEMORIAL_SC, CRAFTER_SC):
            self.assertEqual(lines(card), [], card["name"])

    def test_unrelated_hexproof_line_still_flagged(self):
        card = sc("Other Druid", f"Creature {DASH} Elf", "Lands you control have hexproof.")
        self.assertNotEqual(lines(card), [])


def info(d):
    from components.cards import card_info
    return card_info(d)[0]


CHARM, RESIST, ADVANTAGE = info(CHARM_SC), info(RESIST_SC), info(ADVANTAGE_SC)
OVERWRITE, ECHOES, AVATAR = info(OVERWRITE_SC), info(ECHOES_SC), info(AVATAR_SC)
MEMORIAL, CRAFTER = info(MEMORIAL_SC), info(CRAFTER_SC)
WALKER = make("Test Walker", f"Legendary Planeswalker {DASH} Test", "{2}{W}", 3, "+1: You gain 1 life.", colors="W")


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertEqual(CHARM.choices[1][1].grant_kw, ("trample",))
        self.assertEqual(RESIST.grant_kw, ("vigilance",))
        self.assertTrue(ADVANTAGE.untap_target)
        self.assertEqual((OVERWRITE.empower_x, ECHOES.empower_x), ("exiled", "excess"))
        self.assertEqual(MEMORIAL.memorial_pw_mana, 1)
        self.assertEqual(CRAFTER.restricted_mana, (("C",),))
        self.assertFalse(CRAFTER.mana_src)


class GrantTests(unittest.TestCase):
    def test_resistance_gives_vigilance_to_the_counter_target(self):
        me, opp = pair()
        ogre = on_board(me, OGRE)
        bt.card_effects(me, opp, RESIST, 5, entry())
        self.assertEqual((ogre.bonus, ogre.has("vigilance")), (1, True))

    def test_advantage_untaps_outside_combat(self):
        me, opp = pair()
        ogre = on_board(me, OGRE)
        ogre.tapped = True
        bt.card_effects(me, opp, ADVANTAGE, 5, entry())
        self.assertFalse(ogre.tapped)

    def test_advantage_untaps_the_attacker(self):
        me, opp = pair()
        ogre = on_board(me, OGRE)
        ogre.tapped = True
        wall = on_board(opp, make("Wall", CRE, "{2}{W}", 3, "", "3", "4"))
        me.hand, me.open = [ADVANTAGE], [FOREST.land_colors]
        bt.combat_tricks(me, [(ogre, [wall])], opp, entry(), 5, attacking=True)
        self.assertFalse(ogre.tapped)
        self.assertEqual(ogre.pump, 2)


class EmpowerXTests(unittest.TestCase):
    def test_overwrite_counts_all_exiled_creatures(self):
        me, opp = pair()
        on_board(me, OGRE)
        on_board(opp, HAWK)
        on_board(opp, TITAN)
        bt.cast_removal(OVERWRITE, me, opp, entry(), 5)
        self.assertEqual(me.jace.loyalty, 3)

    def test_echoes_excess_damage(self):
        me, opp = pair()
        on_board(opp, HAWK)  # 3/3: 3 Schaden zu viel
        bt.cast_removal(ECHOES, me, opp, entry(), 5)
        self.assertEqual(me.jace.loyalty, 3)

    def test_echoes_no_excess(self):
        me, opp = pair()
        on_board(opp, make("Giant", CRE, "{5}", 5, "", "6", "6"))
        bt.cast_removal(ECHOES, me, opp, entry(), 5)
        self.assertEqual(me.jace.loyalty, 0)


class LandfallEmpowerTests(unittest.TestCase):
    def test_battle_landfall(self):
        me, opp = pair()
        on_board(me, AVATAR)
        me.jace_perms.append((AVATAR, 0))  # beim Betreten registriert
        me.lands.append(FOREST)
        bt.on_land(me, opp, FOREST, 5, entry())
        self.assertEqual(me.jace.loyalty, 2)

    def test_opponent_land_does_not_count(self):
        me, opp = pair()
        on_board(me, AVATAR)
        me.jace_perms.append((AVATAR, 0))
        opp.lands.append(FOREST)
        bt.on_land(opp, me, FOREST, 5, entry())
        self.assertEqual(me.jace.loyalty, 0)


class MemorialTests(unittest.TestCase):
    def test_walker_costs_one_less(self):
        me, opp = pair()
        me.perms = [MEMORIAL]
        cheap = bt._discounted(WALKER, bt.discount(me), me)
        self.assertEqual(sim.paid_mv(cheap), 2)

    def test_goldfish_walker_costs_one_less(self):
        hand, _back = sim.discounted_hand([WALKER, OGRE], [], {}, perms=[MEMORIAL])
        self.assertEqual((sim.paid_mv(hand[0]), hand[1]), (2, OGRE))


class CrafterTests(unittest.TestCase):
    def test_restricted_mana_pays_for_the_copy(self):
        me, opp = pair()
        crafter = on_board(me, CRAFTER)
        on_board(opp, TITAN)  # der Crafter greift nicht an (sonst waere er ohnehin getappt)
        me.lands = [FOREST, FOREST]  # Soul Tether {2}{R/G}: zwei Forests und das {C} des Crafters
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertFalse(crafter.prepared)
        self.assertTrue(crafter.tapped)

    def test_not_for_hand_spells(self):
        me, opp = pair()
        crafter = on_board(me, CRAFTER)
        crafter.prepared = False
        me.lands, me.hand = [FOREST], [BEAR]  # Bear {1}{G}: das {C} darf nicht helfen
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(me.hand, [BEAR])


if __name__ == "__main__":
    unittest.main()
