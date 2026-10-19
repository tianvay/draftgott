"""FRA-Paket C (Punkte 32-47, Pflicht-Ausloeser, statische Effekte und Regeln): Medic's Kitesail (Flying, 1 Leben beim
Angriff), Hunter's Axe (+2/+0), Jiang Yanggu, Alone und Yuriko (506.5: "attacks alone"), Yuriko (im Kampf keine Zauber
und keine Faehigkeiten ausser Mana), Seasoned Cryomancer (zwei ziehen, zwei abwerfen, Stun je Nichtland-Karte),
Draconic Visitor (Artefakt-Token werden zu 5/5 Dragons, 614.1), Kwia Vigorbloom (Lotus bei Lebensgewinn, einmal pro
Zug), Loot, the Nexus (Mana je verschiedener Power), Tarmogoyf, Loot, the Anomaly (negative Power macht Schaden),
Traxos (enttappt nicht, nur beim Wirken), Samut, Tyrant of Naktamun (Split Second, 702.61), Karn, Argent Defender
(keine Betreten-Ausloeser), Return to the Light Realms."""
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS, BEAR = W["Plains"], W["Test Bear"]


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="W"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


ISLAND, MOUNTAIN, FOREST = land("Island", "U"), land("Mountain", "R"), land("Forest", "G")
KITESAIL = make("Medic's Kitesail", f"Artifact {DASH} Equipment", "{2}", 2, "Equipped creature gets +1/+0 and has flying "
                "and \"Whenever this creature attacks, you gain 1 life.\"\nEquip {2}", colors="")
AXE = make("Hunter's Axe", f"Artifact {DASH} Equipment", "{G}", 1, "Equipped creature gets +2/+0 and has \"Whenever "
           "this creature attacks, it gains your choice of trample or deathtouch until end of turn.\"\nEquip {2}",
           colors="G")
JIANG = make("Jiang Yanggu, Alone", f"Legendary Creature {DASH} Human Berserker", "{4}{R}", 5, "Menace\nWhenever a "
             "creature you control attacks a player alone, discard a card, then draw a card. Then put a +1/+1 counter "
             "on that creature for each card you've discarded this turn.", "4", "4", ["Menace"], colors="R")
YURIKO = make("Yuriko, Blade of the Mighty", f"Legendary Creature {DASH} Human Samurai", "{3}{W}", 4, "During combat, "
              "players can't cast spells or activate abilities that aren't mana abilities.\nWhenever a creature you "
              "control attacks a player alone, it gains double strike until end of turn.", "2", "3")
CRYOMANCER = make("Seasoned Cryomancer", f"Creature {DASH} Human Wizard", "{1}{U}{U}", 3, "When this creature enters, "
                  "draw two cards, then discard two cards. When you discard one or more nonland cards this way, tap up "
                  "to that many target creatures and put a stun counter on each of them.\n{3}{U}{U}, Exile this card "
                  "from your graveyard: Draw two cards.", "2", "2", colors="U")
VISITOR = make("Draconic Visitor", f"Creature {DASH} Dragon", "{3}{R}{R}", 5, "Flying\nIf one or more artifact tokens "
               "would be created under your control, that many 5/5 red Dragon creature tokens with flying are created "
               "instead.", "5", "5", ["Flying"], colors="R")
SEED = make("Ember Seed", "Sorcery", "{R}", 1, "Create a Heartwood token.", colors="R")
KWIA = make("Kwia Vigorbloom", f"Legendary Creature {DASH} Elder Sphinx", "{3}{G}{W}{W}", 6, "Flying, vigilance, "
            "lifelink, ward {2}\nWhenever you gain life, create a colorless artifact token named Lotus with \"{T}, "
            "Sacrifice this token: Add three mana of any one color.\" This ability triggers only once each turn.", "6",
            "6", ["Flying", "Lifelink", "Vigilance", "Ward"], colors="GW")
NEXUS = make("Loot, the Nexus", f"Legendary Creature {DASH} Beast Noble", "{2}{G}", 3, "{T}: Choose a color. Add one "
             "mana of that color for each different power among creatures you control.", "2", "1", colors="G")
GOYF = card_info(dict(_card("Tarmogoyf", f"Creature {DASH} Lhurgoyf", "{1}{G}", 2, "G", "Tarmogoyf's power is equal "
                            "to the number of card types among cards in all graveyards and its toughness is equal to "
                            "that number plus 1."), power="*", toughness="1+*"))[0]
ANOMALY = card_info(dict(_card("Loot, the Anomaly", f"Legendary Creature {DASH} Beast Horror", "{2}{B}", 3, "B",
                               "If Loot's power is negative, he assigns combat damage as though his power were "
                               "positive."), power="-2", toughness="4"))[0]
TRAXOS = make("Traxos, Scourge Eternal", f"Legendary Artifact Creature {DASH} Dragon Construct", "{4}", 4, "Trample\n"
              "Traxos doesn't untap during your untap step.\nWhenever you cast an artifact or creature spell, untap "
              "Traxos.", "5", "4", ["Trample"], colors="")
SAMUT = make("Samut, Tyrant of Naktamun", f"Legendary Creature {DASH} Human Wizard", "{1}{U}", 2, "Instant and sorcery "
             "spells you control have split second.", "2", "1", colors="U")
KARN = make("Karn, Argent Defender", f"Legendary Artifact Creature {DASH} Golem", "{2}", 2, "Artifacts and creatures "
            "entering the battlefield don't cause abilities to trigger.", "1", "3", colors="")
REALMS = make("Return to the Light Realms", "Sorcery", "{7}{W}{W}", 9, "Return all nonland permanent cards from your "
              "graveyard to the battlefield.")
LIFELINKER = make("Lifelinker", CRE, "{1}{W}", 2, "Lifelink", "3", "3", ["Lifelink"])
DRAWER = make("Card Drawer", CRE, "{1}{U}", 2, "When this creature enters, draw a card.", "1", "1", colors="U")
COUNTER = make("Cancel", "Instant", "{1}{U}", 2, "Counter target spell.", colors="U")
BIGSPELL = make("Mind Burst", "Sorcery", "{3}{U}", 4, "Draw three cards.", colors="U")
SPELL = make("Small Spell", "Sorcery", "{U}", 1, "Draw a card.", colors="U")
OGRE = make("Ogre", CRE, "{2}{R}", 3, "", "3", "3", colors="R")
ENCH = make("Old Charm", "Enchantment", "{1}{W}", 2, "")
KILL = make("Doom Blade", "Sorcery", "{1}{B}", 2, "Destroy target creature.", colors="B")
INSTANT = make("Quick Shock", "Instant", "{R}", 1, "Quick Shock deals 2 damage to target creature.", colors="R")


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
        self.assertEqual((KITESAIL.equip[1:3], KITESAIL.equip_kw, KITESAIL.equip_attack_life), ((1, 0), ("flying",), 1))
        self.assertEqual(AXE.equip[1:3], (2, 0))
        self.assertTrue(JIANG.alone_loot and YURIKO.alone_double_strike and YURIKO.combat_lock)
        self.assertTrue(CRYOMANCER.etb_loot_stun)
        self.assertTrue(VISITOR.artifact_tokens_dragons)
        self.assertTrue(KWIA.lifegain_lotus)
        self.assertTrue(NEXUS.nexus_mana)
        self.assertTrue(GOYF.goyf)
        self.assertTrue(ANOMALY.abs_damage)
        self.assertTrue(TRAXOS.no_untap and TRAXOS.untap_on_cast)
        self.assertTrue(SAMUT.split_second)
        self.assertTrue(KARN.no_enter_triggers)
        self.assertEqual(REALMS.reanimate[:2], ("all", "nonland_permanent"))


class EquipmentTests(unittest.TestCase):
    def test_kitesail_flying_and_life_on_attack(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        me.perms = [KITESAIL]
        bear.gear.append(KITESAIL)
        self.assertTrue(bear.has("flying"))
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((me.life, opp.life), (21, 17))


class AloneTests(unittest.TestCase):
    def test_jiang_loots_and_counts_discards(self):
        me, opp = pair()
        jiang = on_board(me, JIANG)
        me.hand = [PLAINS]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)  # Plains wird gelegt, Hand leer: Abwerfen geht nicht
        self.assertEqual((jiang.bonus, len(me.library)), (0, 19))
        me.hand = [OGRE]
        bt.take_turn(me, opp, 7, 4, skip_draw=True)
        self.assertEqual((jiang.bonus, OGRE in me.graveyard), (1, True))

    def test_not_when_two_attack(self):
        me, opp = pair()
        jiang = on_board(me, JIANG)
        on_board(me, BEAR)
        me.hand = [OGRE]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((jiang.bonus, OGRE in me.hand), (0, True))

    def test_yuriko_double_strike_alone(self):
        me, opp = pair()
        on_board(me, YURIKO)
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 4)

    def test_yuriko_stops_combat_spells(self):
        me, opp = pair()
        on_board(opp, YURIKO).tapped = True  # blockt nicht
        on_board(me, BEAR)
        opp.hand, opp.open = [INSTANT], [MOUNTAIN.land_colors]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(opp.life, 18)  # kein Removal-Instant im Kampf: der Bear trifft


class CryomancerTests(unittest.TestCase):
    def test_loot_two_and_stun(self):
        me, opp = pair()
        me.hand = [OGRE]
        me.library = [OGRE, PLAINS] + [PLAINS] * 5
        foe = on_board(opp, OGRE)
        bt._resolve(me, opp, CRYOMANCER, 3, entry())
        self.assertEqual(len(me.graveyard), 2)
        nonland = sum(not c.is_land for c in me.graveyard)
        self.assertEqual((foe.tapped, foe.stun), (nonland > 0, min(nonland, 1)))


class ArtifactTokenTests(unittest.TestCase):
    def test_visitor_turns_heartwood_into_dragons(self):
        me, opp = pair()
        on_board(me, VISITOR)
        bt._resolve(me, opp, SEED, 3, entry())
        self.assertEqual((me.perms, [c.card.name for c in me.creatures].count("Dragon")), ([], 1))

    def test_kwia_creates_one_lotus_each_turn(self):
        me, opp = pair()
        on_board(me, KWIA)
        me.now = 3
        bt.gain_life(me, 2)
        bt.gain_life(me, 2)
        self.assertEqual([c.name for c in me.perms], ["Lotus"])

    def test_lotus_is_used_only_when_it_helps(self):
        me, opp = pair()
        me.perms = [bt.LOTUS]
        me.lands, me.hand = [PLAINS] * 2, [make("Five", CRE, "{4}{W}", 5, "", "5", "5")]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((me.perms, [c.card.name for c in me.creatures]), ([], ["Five"]))
        me, opp = pair()
        me.perms = [bt.LOTUS]
        me.lands, me.hand = [PLAINS] * 2, [BEAR]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual([c.name for c in me.perms], ["Lotus"])


class StatTests(unittest.TestCase):
    def test_nexus_mana(self):
        me, opp = pair()
        on_board(me, NEXUS)
        on_board(me, OGRE)
        on_board(me, make("Rat", CRE, "{B}", 1, "", "1", "1", colors="B"))
        me.lands, me.hand = [FOREST], [make("Four", CRE, "{3}{G}", 4, "", "4", "4", colors="G")]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)  # 3 verschiedene Power: 3 Mana + Forest
        self.assertIn("Four", [c.card.name for c in me.creatures])

    def test_tarmogoyf(self):
        me, opp = pair()
        goyf = on_board(me, GOYF)
        me.graveyard = [PLAINS, BEAR]
        opp.graveyard = [SPELL, INSTANT, ENCH]
        self.assertEqual((goyf.power, goyf.toughness), (5, 6))  # Land, Kreatur, Sorcery, Instant, Verzauberung

    def test_anomaly_deals_damage_with_negative_power(self):
        me, opp = pair()
        on_board(me, ANOMALY)
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 2)

    def test_traxos_untaps_only_on_cast(self):
        me, opp = pair()
        traxos = on_board(me, TRAXOS)
        traxos.tapped = True
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((traxos.tapped, opp.life), (True, 20))  # kein Enttappen, kein Angriff
        me.lands, me.hand = [PLAINS], [BEAR]
        bt.take_turn(me, opp, 7, 4, skip_draw=True)  # Bear in Main 2: Traxos wird enttappt
        self.assertFalse(traxos.tapped)

    def test_samut_split_second(self):
        me, opp = pair()
        on_board(me, SAMUT)
        ogre = on_board(opp, OGRE)
        opp.hand, opp.open = [COUNTER], [ISLAND.land_colors] * 2
        bt._resolve(me, opp, KILL, 5, entry())  # Removal auf seine Kreatur: ohne Samut wuerde er kontern
        self.assertEqual((COUNTER in opp.hand, ogre in opp.creatures), (True, False))

    def test_without_samut_it_is_countered(self):
        me, opp = pair()
        ogre = on_board(opp, OGRE)
        opp.hand, opp.open = [COUNTER], [ISLAND.land_colors] * 2
        bt._resolve(me, opp, KILL, 5, entry())
        self.assertEqual((COUNTER in opp.hand, ogre in opp.creatures), (False, True))

    def test_karn_stops_enter_triggers(self):
        me, opp = pair()
        on_board(opp, KARN)
        bt._resolve(me, opp, DRAWER, 3, entry())
        self.assertEqual(len(me.library), 20)
        drawer = next(c for c in me.creatures if c.card.name == "Card Drawer")
        self.assertIsNotNone(drawer)


class RealmsTests(unittest.TestCase):
    def test_returns_all_nonland_permanents(self):
        me, opp = pair()
        me.graveyard = [BEAR, OGRE, ENCH, PLAINS, SPELL]
        bt._resolve(me, opp, REALMS, 9, entry())
        self.assertEqual((sorted(c.card.name for c in me.creatures), [c.name for c in me.perms]),
                         (["Ogre", "Test Bear"], ["Old Charm"]))
        self.assertEqual(sorted(c.name for c in me.graveyard), ["Plains", "Return to the Light Realms", "Small Spell"])


if __name__ == "__main__":
    unittest.main()
