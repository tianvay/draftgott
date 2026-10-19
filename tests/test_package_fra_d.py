"""FRA-Paket D (Spielentscheidungen nach den Vorgaben des Nutzers).
A Kampf: Hunter's Axe (Deathtouch, wenn ein Blocker sonst ueberlebt, sonst Trample); Gideon's Memorial aus der Hand
(4 Schaden an einen Angreifer/Blocker, der sonst eine unserer Kreaturen toetet); Loot, the Anomaly opfert nur fuer
Lethal; Ferocity of the Hunt (in Main 1 auf die gefaehrlichste eigene Kreatur, +1/+0, Deathtouch, kommt nach dem Tod
getappt zurueck). B Faehigkeiten: Proctor of Potential (nach Surveil aus dem Friedhof), Hungering Puppetbeast (opfert
Token-Artefakte, deren Mana offen ist: Haste vor dem ersten Angriff, sonst Trample), Identity Echo (Kreatur bis
Manawert 2 gegen die naechste Kreatur der Bibliothek), Hexhaven Dueling Arena und Codie (prepared machen). C Betreten
wiederholen: Flickering Hound (wertvollster Betreten-Effekt), Rescue Girl (nur mit Neuwirken im selben Zug), Hall of
Echoes (Kopie der staerksten Kreatur, greift an). D Hexhaven Invigorator (Laender bei Schaden), Puppet Crafting
(Token-Artefakt wird 5/5)."""
import unittest

from components import battle as bt
from components.cards import HEARTWOOD, card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS, BEAR = W["Plains"], W["Test Bear"]


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="W"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


def prep(name, cost, cmc, text, spell_name, spell_cost, spell_text, power, toughness, colors="U"):
    d = {"name": f"{name} // {spell_name}", "layout": "prepare", "type_line": f"Creature {DASH} Test // Sorcery",
         "mana_cost": "", "cmc": float(cmc), "colors": list(colors), "keywords": ["Prepared"],
         "card_faces": [{"name": name, "type_line": f"Creature {DASH} Test", "mana_cost": cost, "power": power,
                         "toughness": toughness, "oracle_text": text},
                        {"name": spell_name, "type_line": "Sorcery", "mana_cost": spell_cost, "oracle_text": spell_text}]}
    return card_info(d)[0]


ISLAND, MOUNTAIN, FOREST, SWAMP = land("Island", "U"), land("Mountain", "R"), land("Forest", "G"), land("Swamp", "B")
OGRE = make("Ogre", CRE, "{2}{R}", 3, "", "3", "3", colors="R")
WALL = make("Wall", CRE, "{2}{W}", 3, "", "0", "6")
TITAN = make("Titan", CRE, "{4}{G}", 5, "", "5", "5", colors="G")
AXE = make("Hunter's Axe", f"Artifact {DASH} Equipment", "{G}", 1, "Equipped creature gets +2/+0 and has \"Whenever "
           "this creature attacks, it gains your choice of trample or deathtouch until end of turn.\"\nEquip {2}",
           colors="G")
MEMORIAL = make("Gideon's Memorial", "Legendary Artifact", "{1}{W}", 2, "Creature tokens you control get +1/+0 and "
                "have vigilance.\n{T}: Add one mana of any color. Spend this mana only to cast a planeswalker spell.\n"
                "{1}{W}, Discard this card: It deals 4 damage to target attacking or blocking creature.")
ANOMALY = card_info(dict(_card("Loot, the Anomaly", f"Legendary Creature {DASH} Beast Horror", "{2}{B}", 3, "B",
                               "If Loot's power is negative, he assigns combat damage as though his power were "
                               "positive.\nThreshold — Sacrifice another creature or planeswalker: Loot gets -2/-0 "
                               "until end of turn. Activate only if there are seven or more cards in your graveyard."),
                         power="-2", toughness="4"))[0]
FEROCITY = make("Ferocity of the Hunt", f"Enchantment {DASH} Aura", "{1}{G}", 2, "Flash\nEnchant creature\nEnchanted "
                "creature gets +1/+0 and has deathtouch.\nWhen enchanted creature dies, return that card to the "
                "battlefield tapped under its owner's control.", keywords=["Flash", "Enchant"], colors="G")
PROCTOR = make("Proctor of Potential", f"Creature {DASH} Human Cleric", "{W}{U}", 2, "Whenever this creature or another "
               "creature you control enters, surveil 1.\n{W}{U}: Return this card from your graveyard to the "
               "battlefield with a finality counter on it. Activate only if you've scried or surveilled this turn.",
               "3", "1", colors="WU")
PUPPETBEAST = make("Hungering Puppetbeast", f"Artifact Creature {DASH} Beast Construct", "{3}{G}{G}", 5, "When this "
                   "creature enters, create a Heartwood token.\n{1}, Sacrifice another artifact: Put a +1/+1 counter "
                   "on this creature. It gains your choice of trample, hexproof, or haste until end of turn.", "5", "5",
                   colors="G")
ECHO = make("Identity Echo", "Enchantment", "{2}{R}", 3, "{3}{R}: Exile target creature or planeswalker you control. "
            "Reveal cards from the top of your library until you reveal a creature or planeswalker card. Put that card "
            "onto the battlefield and the rest on the bottom of your library in a random order. Activate only as a "
            "sorcery.", colors="R")
ARENA = card_info(_card("Hexhaven Dueling Arena", "Land", text="{T}: Add {C}.\n{2}, {T}: Target creature that attacked "
                        "this turn becomes prepared. Activate only as a sorcery.\n{4}, {T}: Target creature becomes "
                        "prepared.", produced=["C"]))[0]
CODIE = make("Codie, Ravenous Codex", f"Legendary Artifact Creature {DASH} Book Construct", "{3}", 3, "Whenever you cast "
             "a prepared spell, copy it. You may choose new targets for the copy.\n{W}{U}{B}{R}{G}, {T}: Each creature "
             "you control becomes prepared.", "1", "4", colors="")
SCHOLAR = prep("Theorix Scholar", "{1}{U}", 2, "This creature enters prepared.", "Quick Study", "{U}", "Draw a card.",
               "2", "2")
HOUND = make("Flickering Hound", f"Creature {DASH} Dog", "{3}{W}", 4, "Whenever you cast a creature spell, exile up to "
             "one other target creature you control, then return that card to the battlefield under its owner's "
             "control.", "2", "2")
DRAWER = make("Card Drawer", CRE, "{1}{U}", 2, "When this creature enters, draw a card.", "1", "1", colors="U")
RESCUE = make("Rescue Girl, First Responder", f"Legendary Creature {DASH} Human Cleric", "{2}{W}", 3, "Flying\n{T}: "
              "Return another target permanent you control to its owner's hand. Activate only during your turn.", "1",
              "3", ["Flying"])
HALL = card_info(_card("Hall of Echoes", "Land", text="{T}: Add {C}.\n{5}: This land becomes a copy of target creature "
                       "you control until end of turn. The \"legend rule\" doesn't apply to permanents you control this "
                       "turn.", produced=["C"]))[0]
INVIGORATOR = make("Hexhaven Invigorator", f"Creature {DASH} Chimera Horror", "{G}{G}{G}{G}", 4, "Vigilance\nWhenever "
                   "this creature is dealt damage, you may search your library for up to that many land cards, put "
                   "them onto the battlefield tapped, then shuffle.", "6", "6", ["Vigilance"], colors="G")
CRAFTING = make("Puppet Crafting", f"Enchantment {DASH} Aura", "{1}{G}", 2, "Enchant artifact or non-Aura enchantment\n"
                "Enchanted permanent is a Construct creature with base power and toughness 5/5 in addition to its "
                "other types.\n{4}{G}: Return this card from your graveyard to your hand.", keywords=["Enchant"],
                colors="G")
HAWK = make("Hawk", CRE, "{2}{W}", 3, "Flying", "3", "3", ["Flying"])
BOLT = make("Bolt", "Instant", "{R}", 1, "Bolt deals 3 damage to target creature.", colors="R")


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def pair():
    me, opp = player(), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


def on_board(p, card, entered=0):
    c = bt.Creature(card, entered)
    c.gy, c.ctl = p.graveyard, p
    p.creatures.append(c)
    return c


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertEqual(AXE.equip_attack_choice, ("trample", "deathtouch"))
        self.assertEqual(MEMORIAL.hand_combat_bolt[1], 4)
        self.assertTrue(ANOMALY.threshold_sac_minus)
        self.assertEqual((FEROCITY.aura_pump, FEROCITY.aura_kw, FEROCITY.aura_return), ((1, 0), ("deathtouch",), True))
        self.assertEqual(PROCTOR.gy_return[5], "surveilled")
        self.assertTrue(PUPPETBEAST.artifact_sac_counter)
        self.assertTrue(ECHO.identity_echo)
        self.assertTrue(ARENA.arena_prepare and CODIE.codie_prepare)
        self.assertTrue(HOUND.cast_blink and RESCUE.rescue_bounce)
        self.assertTrue(HALL.hall_copy)
        self.assertTrue(INVIGORATOR.damage_ramp)
        self.assertTrue(CRAFTING.animate_artifact)


class AxeTests(unittest.TestCase):
    def test_deathtouch_against_a_big_blocker(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        me.perms = [AXE]
        bear.gear.append(AXE)
        on_board(opp, WALL)  # 0/6: wuerde 4 Schaden ueberleben
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertTrue(any("deathtouch" in ev for ev in e["events"]))
        self.assertEqual(opp.life, 16)  # gegen Deathtouch blockt die Wall nicht

    def test_trample_without_a_surviving_blocker(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        me.perms = [AXE]
        bear.gear.append(AXE)
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((e["damage"], bear.has("trample")), (4, False))  # Trample bis Rundenende, danach weg


class MemorialTests(unittest.TestCase):
    def test_kills_a_blocker_that_would_kill_ours(self):
        me, opp = pair()
        ogre = on_board(me, OGRE)
        foe = on_board(opp, OGRE)  # Tausch-Block
        me.hand, me.open = [MEMORIAL], [PLAINS.land_colors] * 2
        bt.hand_bolt_tricks(me, [(ogre, [foe])], opp, entry(), 5, attacking=True)
        self.assertEqual((MEMORIAL in me.graveyard, foe.damage, me.open), (True, 4, []))

    def test_not_when_four_damage_does_not_kill(self):
        me, opp = pair()
        ogre = on_board(me, OGRE)
        foe = on_board(opp, TITAN)
        me.hand, me.open = [MEMORIAL], [PLAINS.land_colors] * 2
        bt.hand_bolt_tricks(me, [(ogre, [foe])], opp, entry(), 5, attacking=True)
        self.assertIn(MEMORIAL, me.hand)

    def test_not_when_ours_survives(self):
        me, opp = pair()
        titan = on_board(me, TITAN)
        foe = on_board(opp, BEAR)
        me.hand, me.open = [MEMORIAL], [PLAINS.land_colors] * 2
        bt.hand_bolt_tricks(me, [(titan, [foe])], opp, entry(), 5, attacking=True)
        self.assertIn(MEMORIAL, me.hand)


class AnomalyTests(unittest.TestCase):
    def test_sacrifice_only_for_lethal(self):
        me, opp = pair()
        loot = on_board(me, ANOMALY)
        on_board(me, BEAR, entered=5)  # frisch, greift nicht an
        me.graveyard = [PLAINS] * 7
        opp.life = 4
        bt.take_turn(me, opp, 5, 3, skip_draw=True)  # -2/-0: 4 Schaden statt 2
        self.assertEqual((opp.life <= 0, len(me.creatures)), (True, 1))
        self.assertIs(me.creatures[0], loot)

    def test_no_sacrifice_without_lethal(self):
        me, opp = pair()
        on_board(me, ANOMALY)
        on_board(me, BEAR, entered=5)
        me.graveyard = [PLAINS] * 7
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(len(me.creatures), 2)


class FerocityTests(unittest.TestCase):
    def test_main1_on_the_best_attacker_and_return(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        on_board(me, OGRE, entered=5)  # kann nicht angreifen
        me.lands, me.hand = [FOREST, FOREST], [FEROCITY]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((FEROCITY in bear.auras, bear.power, bear.has("deathtouch")), (True, 3, True))
        bear.dead = True
        bt.bury((me, opp), entry())
        back = [c for c in me.creatures if c.card.name == "Test Bear"]
        self.assertEqual((len(back), back[0].tapped if back else None, FEROCITY in me.graveyard), (1, True, True))


class CryomancerGraveyardTests(unittest.TestCase):
    CRYO = make("Seasoned Cryomancer", f"Creature {DASH} Human Wizard", "{1}{U}{U}", 3, "When this creature enters, "
                "draw two cards, then discard two cards. When you discard one or more nonland cards this way, tap up to "
                "that many target creatures and put a stun counter on each of them.\n{3}{U}{U}, Exile this card from "
                "your graveyard: Draw two cards.", "2", "2", colors="U")

    def test_parse(self):
        self.assertEqual(self.CRYO.gy_draw[1], 2)

    def test_end_of_opponent_turn_with_free_mana(self):
        me, opp = pair()
        me.graveyard = [self.CRYO]
        me.open = [ISLAND.land_colors] * 5
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual((me.graveyard, len(me.library)), ([], 18))  # exiliert, zwei gezogen

    def test_not_without_enough_mana(self):
        me, opp = pair()
        me.graveyard = [self.CRYO]
        me.open = [ISLAND.land_colors] * 4
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual((me.graveyard, len(me.library)), ([self.CRYO], 20))


class ProctorTests(unittest.TestCase):
    def test_returns_after_surveil(self):
        me, opp = pair()
        me.graveyard = [PROCTOR]
        me.lands = [PLAINS, ISLAND]
        me.surveilled = True
        me.open = [PLAINS.land_colors, ISLAND.land_colors]
        bt.lasting_abilities(me, opp, 5, entry(), own_turn=True, mode="free")
        self.assertEqual(([c.card.name for c in me.creatures], me.creatures[0].finality), (["Proctor of Potential"], True))

    def test_not_without_surveil(self):
        me, opp = pair()
        me.graveyard = [PROCTOR]
        me.open = [PLAINS.land_colors, ISLAND.land_colors]
        bt.lasting_abilities(me, opp, 5, entry(), own_turn=True, mode="free")
        self.assertEqual(me.creatures, [])


class PuppetbeastTests(unittest.TestCase):
    def test_sacrifices_open_heartwood_and_gains_haste(self):
        me, opp = pair()
        beast = on_board(me, PUPPETBEAST, entered=5)  # frisch: Haste
        me.perms = [HEARTWOOD]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((beast.bonus, me.perms, opp.life), (1, [], 14))


class PuppetbeastManaTests(unittest.TestCase):
    def test_keeps_a_heartwood_whose_mana_is_used(self):
        me, opp = pair()
        beast = on_board(me, PUPPETBEAST, entered=5)
        me.perms, me.hand = [HEARTWOOD], [make("Spark", CRE, "{R}", 1, "", "1", "1", colors="R")]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((beast.bonus, me.perms), (0, [HEARTWOOD]))


class EchoTests(unittest.TestCase):
    def test_swaps_a_small_creature(self):
        me, opp = pair()
        me.perms = [ECHO]
        bear = on_board(me, BEAR)
        me.lands = [MOUNTAIN] * 4
        me.library = [PLAINS, PLAINS, TITAN, PLAINS]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((bear in me.creatures, [c.card.name for c in me.creatures]), (False, ["Titan"]))
        self.assertEqual(me.library[-2:], [PLAINS, PLAINS])

    def test_not_for_bigger_creatures(self):
        me, opp = pair()
        me.perms = [ECHO]
        on_board(me, OGRE)
        me.lands = [MOUNTAIN] * 4
        me.library = [TITAN]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual([c.card.name for c in me.creatures], ["Ogre"])


class PrepareTests(unittest.TestCase):
    def test_arena_prepares_an_attacker_cheaply(self):
        me, opp = pair()
        scholar = on_board(me, SCHOLAR)
        scholar.prepared = False
        me.lands = [ARENA, PLAINS, PLAINS]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)  # Scholar greift an: {2}, {T}
        self.assertTrue(scholar.prepared)

    def test_codie_prepares_all(self):
        me, opp = pair()
        scholar = on_board(me, SCHOLAR)
        scholar.prepared = False
        on_board(me, CODIE)
        on_board(opp, TITAN)  # haelt Codie und Scholar vom Angriff ab
        me.lands = [PLAINS, ISLAND, SWAMP, MOUNTAIN, FOREST]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertTrue(scholar.prepared)


class BlinkTests(unittest.TestCase):
    def test_hound_blinks_the_best_enter_effect(self):
        me, opp = pair()
        on_board(me, HOUND)
        drawer = on_board(me, DRAWER)
        bt._resolve(me, opp, BEAR, 3, entry())
        self.assertEqual((drawer in me.creatures, len(me.library)), (False, 19))
        self.assertIn("Card Drawer", [c.card.name for c in me.creatures])

    def test_hound_without_a_target(self):
        me, opp = pair()
        on_board(me, HOUND)
        bear = on_board(me, BEAR)
        bt._resolve(me, opp, OGRE, 3, entry())
        self.assertIn(bear, me.creatures)

    def test_rescue_girl_recasts(self):
        me, opp = pair()
        on_board(me, RESCUE)
        on_board(me, DRAWER)
        on_board(opp, HAWK)  # haelt Rescue Girl und Drawer vom Angriff ab
        me.lands = [ISLAND, ISLAND]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((len(me.library), "Card Drawer" in [c.card.name for c in me.creatures]), (19, True))

    def test_rescue_girl_not_without_mana(self):
        me, opp = pair()
        on_board(me, RESCUE)
        drawer = on_board(me, DRAWER)
        on_board(opp, HAWK)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertIn(drawer, me.creatures)


class HallTests(unittest.TestCase):
    def test_hall_copies_the_strongest_and_attacks(self):
        me, opp = pair()
        on_board(me, TITAN)
        me.lands = [HALL] + [FOREST] * 5
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 10)
        self.assertEqual(len(me.creatures), 1)  # die Kopie ist am Rundenende wieder ein Land
        self.assertIn(HALL, me.lands)


class HallLandDropTests(unittest.TestCase):
    def test_not_in_the_turn_it_is_played(self):
        me, opp = pair()
        on_board(me, TITAN)
        me.lands, me.hand = [FOREST] * 5, [HALL]
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 5)


class InvigoratorTests(unittest.TestCase):
    def test_new_colors_first(self):
        me, opp = pair()
        inv = on_board(me, INVIGORATOR)
        me.lands = [FOREST]
        me.library = [FOREST, FOREST, FOREST, ISLAND]
        bt.cast_removal(BOLT, opp, me, entry(), 5, target=inv)
        self.assertEqual((ISLAND in me.library, len(me.library)), (False, 1))

    def test_lands_when_dealt_damage(self):
        me, opp = pair()
        inv = on_board(me, INVIGORATOR)
        me.library = [FOREST, ISLAND, PLAINS, OGRE]
        opp.open = [MOUNTAIN.land_colors]
        bt.cast_removal(BOLT, opp, me, entry(), 5, target=inv)
        self.assertEqual((sorted(c.name for c in me.lands), OGRE in me.library), (["Forest", "Island", "Plains"], True))


class CraftingTests(unittest.TestCase):
    def test_animated_artifact_card_goes_to_the_graveyard(self):
        me, opp = pair()
        gear = make("Old Gear", "Artifact", "{1}", 1, "", colors="")
        me.perms = [gear]
        me.lands, me.hand = [FOREST, FOREST], [CRAFTING]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        golem = next(c for c in me.creatures if c.card.name == "Old Gear")
        golem.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual(sorted(c.name for c in me.graveyard), ["Old Gear", "Puppet Crafting"])
        self.assertFalse(next(c for c in me.graveyard if c.name == "Old Gear").is_creature)

    def test_animates_a_heartwood(self):
        me, opp = pair()
        me.perms = [HEARTWOOD]
        me.lands, me.hand = [FOREST, FOREST], [CRAFTING]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        animated = [c for c in me.creatures if c.card.name == "Heartwood"]
        self.assertEqual((len(animated), animated[0].power if animated else 0, HEARTWOOD in me.perms), (1, 5, False))


if __name__ == "__main__":
    unittest.main()
