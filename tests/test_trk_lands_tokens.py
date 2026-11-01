"""Star Trek (TRK), Pakete A und B (Nutzer 2026-11-01): kleine Luecken beim Einlesen (Planeten-Laender mit Leben,
Laender mit Modus beim Betreten ohne Tappen, Landfall-Pump, Anthems auch nur fuer Artefaktkreaturen, Food, "can't
block", "can't attack alone", Ausweichen, Schutz-Zauber, Angriffs-Modus, Kostensenkung gegen Angreifer, Sterbe-
Ausloeser) und New-Planet-Token, Anomalie-Laender und Landsuche. Nur Kampfmodell, ausser der Landsuche aufs Feld (auch
Goldfish wie Simulacrum Shaper). Kartentexte aus TRK."""
import unittest

from components import battle as bt
from components.cards import ANY_COLOR, NEW_PLANET, card_info, land_produced
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
LF = "Landfall — Whenever a land you control enters, "
CHOOSE = "This land enters tapped unless you control two or more other lands.\nWhen this land enters untapped, " \
         "choose one —\n"
PLANET_TOKEN = 'Create a tapped Planet land token named New Planet with "{T}: Add one mana of any color."'
FOOD = ' (It\'s an artifact with "{2}, {T}, Sacrifice this token: You gain 3 life.")'
PLAINS = W["Plains"]


def land(name, color, basic=True):
    kind = f"Basic Land {DASH} {name}" if basic else "Land"
    return card_info(_card(name, kind, text=f"({{T}}: Add {{{color}}}.)", produced=[color]))[0]


ISLAND, FOREST, MOUNTAIN, SWAMP = land("Island", "U"), land("Forest", "G"), land("Mountain", "R"), land("Swamp", "B")
WASTE = card_info(_card("Wastes", f"Basic Land {DASH}", text="{T}: Add {C}.", produced=["C"]))[0]


def raw(name, type_line, cost="", cmc=0, text="", power=None, toughness=None, keywords=(), colors="", produced=None):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness, produced)


def anomaly(name, cost, effect):
    return raw(name, "Land", text="{T}: Add {C}.\n" + cost + ", {T}, Sacrifice this land: " + effect + " "
               + PLANET_TOKEN, produced=["B", "C", "G", "R", "U", "W"])


RAW = {
    "andoria": raw("Andoria", f"Land {DASH} Planet", text="This land enters tapped.\nWhen this land enters, you gain 1 "
                   "life.\n{T}: Add {U} or {R}.", produced=["U", "R"]),
    "outpost": raw("Federation Outpost", "Land", text=CHOOSE + "• You gain 2 life.\n• Surveil 1.\n{T}: Add {W}.",
                   keywords=["Surveil"], produced=["W"]),
    "nivar": raw("Ni'Var Science Academy", "Land", text=CHOOSE + "• Target creature gains flying until end of turn.\n"
                 "• Surveil 1.\n{T}: Add {U}.", keywords=["Surveil"], produced=["U"]),
    "continuum": raw("Q Continuum", "Land", text=CHOOSE + "• Target creature gets +1/+1 and gains vigilance until end "
                     "of turn.\n• Surveil 1.\n{T}: Add {G}.", keywords=["Surveil"], produced=["G"]),
    "quark": raw("Quark's Bar", "Land", text=CHOOSE + "• This land deals 1 damage to each opponent.\n• Surveil 1.\n{T}: "
                 "Add {R}.", keywords=["Surveil"], produced=["R"]),
    "unicomplex": raw("The Unicomplex", "Land", text=CHOOSE + "• Put target creature card from your graveyard on top of "
                      "your library.\n• Surveil 1.\n{T}: Add {B}.", keywords=["Surveil"], produced=["B"]),
    "patrol": raw("Planetary Patrol", f"Creature {DASH} Scout", "{1}{R}", 2, LF + "this creature gets +1/+1 until end "
                  "of turn.", "2", "2", ["Landfall"], "R"),
    "saurian": raw("Saurian Explorer", f"Creature {DASH} Dinosaur Scout", "{3}{G}", 4, LF + "this creature gets +2/+2 "
                   "until end of turn.\n{6}: " + PLANET_TOKEN + " Activate only as a sorcery.", "4", "3", ["Landfall"],
                   "G"),
    "picard": raw("Captain Jean-Luc Picard", f"Legendary Creature {DASH} Human Officer", "{2}{W}", 3, "Other creatures "
                  "you control get +1/+1.\nWhenever you cast a creature or Spacecraft spell, create a 1/1 red Officer "
                  "creature token.\nTap seven untapped Officers you control: Search your library for a Spacecraft "
                  "card, put it onto the battlefield with seven charge counters on it, then shuffle.", "2", "3",
                  colors="W"),
    "sarcophagus": raw("Sarcophagus, Ship of the Dead", f"Legendary Artifact {DASH} Spacecraft", "{2}{R}", 3, "Other "
                       "creatures you control get +1/+0.\nWhenever a creature dies, if Sarcophagus isn't a creature, "
                       "put a charge counter on it.\nStation (Tap another creature you control: Put charge counters "
                       "equal to its power on this Spacecraft. Station only as a sorcery. It's an artifact creature "
                       "at 10+.)\n10+ | Flying", "4", "4", ["Station"], "R"),
    "assault": raw("Assault Drone", f"Artifact Creature {DASH} Borg", "{3}{B}", 4, "Artifact creatures you control get "
                   "+1/+0.", "2", "4", colors="B"),
    "locutus": raw("Locutus, the One Who Speaks", f"Legendary Artifact Creature {DASH} Borg", "{W}{B}", 2, "Artifact "
                   "creatures you control get +1/+1.\n{W}{B}, Discard this card: It deals 2 damage to target creature. "
                   "You gain 2 life.", "1", "1", colors="WB"),
    "neelix": raw("Neelix, Moral Support", f"Legendary Creature {DASH} Talaxian Advisor", "{1}{G}", 2, "When Neelix "
                  "enters, create a Food token." + FOOD + "\nWhenever you gain life, put a +1/+1 counter on Neelix.",
                  "1", "1", ["Food"], "G"),
    "replicator": raw("Replicator", "Artifact", "{2}", 2, "When this artifact enters, create a Food token." + FOOD
                      + "\n{2}, {T}: Create a tapped token that's a copy of target token you control.", keywords=["Food"]),
    "tribbles": raw("Troubling Tribbles", f"Creature {DASH} Tribble", "{2}{W}", 3, "This creature can't block.\nAt the "
                    "beginning of your upkeep, create a token that's a copy of this creature.", "0", "1", colors="W"),
    "veteran": raw("Storied Veteran", f"Creature {DASH} Klingon Advisor", "{B}", 1, "This creature can't block.\nYou "
                   "may cast this card from your graveyard. If you do, it enters with a finality counter on it.", "2",
                   "1", colors="B"),
    "sehlat": raw("Pet Sehlat", f"Creature {DASH} Bear", "{2}{W}", 3, "This creature can't attack alone.", "4", "3",
                  colors="W"),
    "booker": raw("Cleveland Booker, Empath", f"Legendary Creature {DASH} Kwejian Rogue", "{2}{R/G}{R/G}", 4, LF
                  + "create a 2/2 red and green Worm creature token with \"This token can't block.\"\n{8}: Creatures "
                  "you control get +2/+0 until end of turn.", "2", "2", ["Landfall"], "RG"),
    "crew": raw("Cold-Blooded Crew", f"Creature {DASH} Gorn Warrior", "{4}{G}{G}", 6, "When this creature enters, put "
                "two +1/+1 counters on target creature.\nThis creature can't be blocked by creatures with power 2 or "
                "less.\nBasic landcycling {2} ({2}, Discard this card: Search your library for a basic land card, "
                "reveal it, put it into your hand, then shuffle.)", "4", "4",
                ["Landcycling", "Basic landcycling", "Typecycling", "Cycling"], "G"),
    "species": raw("Species 8472", f"Creature {DASH} Insect Beast", "{4}{G}{G}", 6, "Strange new worlds — When this "
                   "creature enters, you gain life equal to the number of differently named lands you control.\nThis "
                   "creature can't be blocked by artifact creatures.\nThis creature can't be the target of abilities "
                   "from artifact sources your opponents control.", "7", "5", ["Strange new worlds"], "G"),
    "shields": raw("Shields Up!", "Instant", "{1}{W}", 2, "Target artifact or creature you control gains hexproof and "
                   "indestructible until end of turn. If it's a creature, put a +1/+1 counter on it. (It can't be the "
                   "target of spells or abilities your opponents control. Damage and effects that say \"destroy\" "
                   "don't destroy it.)", colors="W"),
    "saru": raw("Saru, Unthreatened", f"Legendary Creature {DASH} Kelpien Officer", "{2}{G}", 3, "Flash\nWhen Saru "
                "enters, another target creature you control gains hexproof until end of turn. (It can't be the target "
                "of spells or abilities your opponents control.)", "3", "2", ["Flash"], "G"),
    "tutelage": raw("Captain's Tutelage", f"Enchantment {DASH} Aura", "{1}{R}", 2, "Flash\nEnchant creature\nWhen this "
                    "Aura enters, enchanted creature gains first strike until end of turn.\nEnchanted creature gets "
                    "+2/+0.", keywords=["Enchant", "Flash"], colors="R"),
    "operative": raw("Tal Shiar Operative", f"Creature {DASH} Romulan Officer Spy", "{1}{B}", 2, "Whenever this "
                     "creature attacks, choose one —\n• Target creature you control gains deathtouch until end of "
                     "turn.\n• Surveil 1. (Look at the top card of your library. You may put it into your graveyard.)",
                     "2", "2", ["Surveil"], "B"),
    "alert": raw("Red Alert!", "Instant", "{2}{R}", 3, "This spell costs {2} less to cast if a creature is attacking "
                 "you.\nCreatures you control get +2/+0 until end of turn.", colors="R"),
    "guidance": raw("Guidance Failure", "Instant", "{3}{U}", 4, "This spell costs {1} less to cast if it targets an "
                    "attacking creature.\nTarget creature or Spacecraft's owner puts it on their choice of the top or "
                    "bottom of their library.", colors="U"),
    "munitions": raw("Munitions Enthusiast", f"Creature {DASH} Klingon Warrior", "{1}{R}", 2, "Trample\nWhen this "
                     "creature dies, it deals 1 damage to any target.", "3", "2", ["Trample"], "R"),
    "duras": raw("The Duras Sisters", f"Legendary Creature {DASH} Klingon Warrior", "{B/R}{B/R}", 2, "When The Duras "
                 "Sisters die, create a 2/1 red Klingon Warrior creature token with haste.", "3", "2", colors="BR"),
    "drone": raw("Tenacious Drone", f"Artifact Creature {DASH} Borg", "{1}{B}", 2, "When this creature dies, create a "
                 "1/1 colorless Borg artifact creature token.", "2", "1", colors="B"),
    # Paket B
    "genesis_effect": raw("Genesis Effect", "Instant", "{4}{R}", 5, "Genesis Effect deals 6 damage to target creature. "
                          "Destroy target land you control. " + PLANET_TOKEN, colors="R"),
    "marcus": raw("David and Carol Marcus, Creators", f"Legendary Creature {DASH} Human Scientist", "{2}{G}", 3,
                  "When David and Carol Marcus enter, " + PLANET_TOKEN[0].lower() + PLANET_TOKEN[1:], "1", "3",
                  colors="G"),
    "wormhole": raw("Stable Wormhole", "Enchantment", "{2}{G}", 3, "Whenever you attack, " + PLANET_TOKEN[0].lower()
                    + PLANET_TOKEN[1:], colors="G"),
    "spatial": anomaly("Spatial Anomaly", "{4}{R}", "It deals 2 damage to target creature."),
    "gaseous": anomaly("Gaseous Anomaly", "{5}{U}", "Draw two cards."),
    "subspace": anomaly("Subspace Anomaly", "{4}{W}", "Create two 1/1 red Officer creature tokens."),
    "temporal": anomaly("Temporal Anomaly", "{3}{G}", "Mill four cards. You may put a permanent card from among them "
                        "into your hand."),
    "artificial": anomaly("Artificial Anomaly", "{3}{B}", "Each opponent loses 2 life and you gain 2 life."),
    "frontier": raw("Final Frontier", "Sorcery", "{2}{G}", 3, "Search your library for a basic land card or Planet "
                    "card, put it onto the battlefield tapped, then shuffle.\nBeam me up {1}{G} (You may cast this card "
                    "from your graveyard for {1}{G} if you also return a creature you control to its owner's hand. "
                    "Then exile this spell.)", colors="G"),
    "device": raw("Genesis Device", "Legendary Artifact", "{2}{G}", 3, "When Genesis Device enters, search your library "
                  "for a basic land card or Planet card, put it onto the battlefield tapped, then shuffle.\n{3}{G}{G}, "
                  "{T}, Sacrifice Genesis Device: Sacrifice any number of lands you control, then search your library "
                  "for up to that many land cards, put them onto the battlefield tapped, then shuffle. Activate only "
                  "as a sorcery.", colors="G"),
    "naked": raw("The Naked Time", f"Enchantment {DASH} Saga", "{1}{R}", 2, "(As this Saga enters and after your draw "
                 "step, add a lore counter. Sacrifice after III.)\nI — Search your library for a basic Mountain card, "
                 "put it onto the battlefield tapped, then shuffle.\nII — Whenever a creature you control enters this "
                 "turn, put a +1/+1 counter on it and it gains haste until end of turn.\nIII — Sacrifice a land.",
                 colors="R"),
    "warp_core": raw("Warp Core", "Artifact", "{2}", 2, "When this artifact enters, you may search your library for a "
                     "basic land card, reveal it, put it into your hand, then shuffle.\n{1}, {T}: Put two charge "
                     "counters on target Spacecraft. Activate only as a sorcery."),
    "oberth": raw("Oberth-Class Starship", f"Artifact {DASH} Spacecraft", "{1}{W}", 2, "When this Spacecraft enters, "
                  "search your library for a basic Plains card, reveal it, put it into your hand, then shuffle.\n"
                  "Station (Tap another creature you control: Put charge counters equal to its power on this "
                  "Spacecraft. Station only as a sorcery. It's an artifact creature at 6+.)\n6+ | Flying", "2", "2",
                  ["Station"], "W"),
    "territory": raw("Unexplored Territory", "Land", text="{T}: Add {C}.\n{1}, {T}, Sacrifice this land: Search your "
                     "library for a basic land card, put it onto the battlefield tapped, then shuffle.", produced=["C"]),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}
BEAR = W["Test Bear"]
OGRE = card_info(_card("Ogre", f"Creature {DASH} Ogre", "{2}{R}", 3, "R", "", [], "3", "3"))[0]
GIANT = card_info(_card("Giant", f"Creature {DASH} Giant", "{4}{R}", 5, "R", "", [], "5", "5"))[0]
ELF = card_info(_card("Elf", f"Creature {DASH} Elf", "{G}", 1, "G", "", [], "1", "1"))[0]
GOLEM = card_info(_card("Golem", f"Artifact Creature {DASH} Golem", "{3}", 3, "", "", [], "3", "3"))[0]
GROWTH = card_info(_card("Test Growth", "Instant", "{G}", 1, "G", "Target creature gets +3/+3 until end of turn."))[0]
KILL = card_info(_card("Test Kill", "Instant", "{1}{B}", 2, "B", "Destroy target creature."))[0]
ANDORIA_LAND = card_info(_card("Bajor", f"Land {DASH} Planet", text="This land enters tapped.\nWhen this land enters, "
                               "you gain 1 life.\n{T}: Add {W} or {R}.", produced=["W", "R"]))[0]


def player(name="Wir", library=None):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], list(library if library is not None else [PLAINS] * 20)
    return p


def pair(library=None, lands=()):
    me, opp = player(library=library), player("Gegner")
    me.opponent, opp.opponent = opp, me
    me.lands = list(lands)
    return me, opp


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": []}


def put(p, card, entered=0):
    c = bt.Creature(card, entered)
    c.gy, c.ctl = p.graveyard, p
    p.creatures.append(c)
    return c


class LandParseTests(unittest.TestCase):
    def test_planet_land_gains_life(self):
        self.assertEqual(C["andoria"].etb_life, 1)
        self.assertIn("planet", C["andoria"].land_types)

    def test_modal_lands(self):
        n, subs = C["outpost"].choices
        self.assertEqual((n, C["outpost"].modes_untapped), (1, True))
        self.assertEqual([(s.etb_life, s.surveil) for s in subs], [(2, 0), (0, 1)])
        self.assertEqual(C["quark"].choices[1][0].modes, ((("face", 1),),))
        self.assertEqual(C["unicomplex"].choices[1][0].gy_top_creature, True)
        self.assertEqual(C["outpost"].surveil, 0)  # Surveil nur als Modus

    def test_anomaly_colors_only_from_own_mana(self):
        self.assertEqual(C["spatial"].land_colors, ("C",))
        self.assertEqual(land_produced(RAW["spatial"]), ["C"])
        self.assertEqual(land_produced(RAW["andoria"]), ["U", "R"])  # sonst wie Scryfall

    def test_anomaly_abilities(self):
        alts, sub, planet = C["gaseous"].land_sac_ability
        self.assertEqual((alts, sub.draws, planet), (((5, (("U", 1),)),), 2, True))
        self.assertEqual(C["spatial"].land_sac_ability[1].removal[:2], ("damage", 2))
        self.assertEqual(C["subspace"].land_sac_ability[1].creates_tokens[0][0], 2)
        temporal = C["temporal"].land_sac_ability[1]
        self.assertEqual((temporal.mill_self, temporal.mill_take), (4, "permanent"))
        artificial = C["artificial"].land_sac_ability[1]
        self.assertEqual((artificial.opp_loss, artificial.spell_life), (2, 2))
        alts, sub, planet = C["territory"].land_sac_ability
        self.assertEqual((alts, sub.etb_basic_tapped, planet), (((1, ()),), True, False))


class ParseTests(unittest.TestCase):
    def test_landfall_pump(self):
        self.assertEqual(C["patrol"].landfall, (("self_pump", 1, 1),))
        self.assertEqual(C["saurian"].landfall, (("self_pump", 2, 2),))
        kind, tokens = C["booker"].landfall[0]
        self.assertEqual((kind, tokens[0][0], tokens[0][1].name, tokens[0][1].cant_block), ("tokens", 1, "Worm", True))

    def test_anthems(self):
        self.assertEqual(C["picard"].cond_static, ((("always",), "others", 1, 1, ()),))
        self.assertEqual(C["sarcophagus"].cond_static, ((("always",), "others", 1, 0, ()),))
        self.assertEqual(C["assault"].cond_static, ((("always",), "artifact", 1, 0, ()),))
        self.assertEqual(C["locutus"].cond_static, ((("always",), "artifact", 1, 1, ()),))

    def test_food_and_restrictions(self):
        self.assertEqual((C["neelix"].food, C["replicator"].food), (1, 1))
        self.assertEqual((C["tribbles"].cant_block, C["veteran"].cant_block, BEAR.cant_block), (True, True, False))
        self.assertTrue(C["sehlat"].cant_attack_alone)
        self.assertEqual((C["crew"].evade_power, C["species"].evade_artifact), (2, True))

    def test_protection(self):
        self.assertEqual((C["saru"].etb_grant, C["saru"].etb_grant_plain), (("hexproof",), True))
        self.assertEqual((C["shields"].protect_spell, C["shields"].protect_counter), (("hexproof", "indestructible"), 1))
        self.assertEqual(C["tutelage"].aura_etb_kw, ("first strike",))

    def test_attack_choice_and_discounts(self):
        n, subs = C["operative"].attack_choices
        self.assertEqual((n, subs[0].grant_kw, subs[1].surveil), (1, ("deathtouch",), 1))
        self.assertEqual(C["alert"].self_discount, ("attacked", 2))
        self.assertEqual(C["guidance"].self_discount, ("attacked", 1))
        self.assertEqual(C["guidance"].removal[0], "tuck")

    def test_death_triggers(self):
        self.assertEqual(C["munitions"].death_bolt, 1)
        (n, token), = C["duras"].death_tokens
        self.assertEqual((n, token.name, token.power, token.toughness, token.haste), (1, "Klingon Warrior", 2, 1, True))
        (n, token), = C["drone"].death_tokens
        self.assertEqual((token.name, token.is_artifact), ("Borg", True))

    def test_planets_and_searches(self):
        self.assertEqual(C["marcus"].planet_tokens, 1)
        self.assertEqual(C["wormhole"].attack_planet, True)
        self.assertEqual(C["saurian"].planet_ability, ((6, ()),))
        self.assertEqual((C["genesis_effect"].removal[:2], C["genesis_effect"].land_swap,
                          C["genesis_effect"].planet_tokens), (("damage", 6), True, 1))
        self.assertEqual((C["frontier"].etb_basic_tapped, C["frontier"].basic_planet), (True, True))
        self.assertEqual((C["device"].etb_basic_tapped, C["device"].basic_planet), (True, True))
        chapter = C["naked"].saga[1][0][1]
        self.assertEqual((chapter.etb_basic_tapped, chapter.basic_type), (True, "mountain"))
        self.assertEqual((C["warp_core"].etb_basic_hand, C["oberth"].etb_basic_hand), ("basic", "plains"))
        self.assertEqual((NEW_PLANET.is_land, NEW_PLANET.is_token, NEW_PLANET.land_colors, NEW_PLANET.name),
                         (True, True, ANY_COLOR, "New Planet"))

    def test_other_cards_unchanged(self):
        for card in (BEAR, OGRE, KILL, PLAINS):
            self.assertEqual((card.cant_block, card.food, card.death_bolt, card.planet_tokens, card.land_sac_ability,
                              card.cond_static, card.basic_type), (False, 0, 0, 0, (), (), ""))


OPEN_MARKERS = ("enters, you gain 1 life", "choose one", "You gain 2 life.", "Surveil 1.", "Target creature gains",
                "Target creature gets", "This land deals", "Put target creature card", "this creature gets",
                "Other creatures", "Artifact creatures you control get", "Food", "can't block", "attack alone",
                "power 2 or less", "blocked by artifact", "hexproof", "first strike", "deathtouch", "costs {",
                "top or bottom", "dies, it deals", "dies, create", "die, create", "New Planet", "basic land card", "basic Mountain", "basic Plains",
                "Worm", "Destroy target land")


class CoverageTests(unittest.TestCase):
    def test_lines_modelled(self):
        for key, r in RAW.items():
            open_lines = [l for _c, _m, l in analyze_card(r)]
            self.assertFalse([l for l in open_lines if any(m in l for m in OPEN_MARKERS)], key)


class LandTests(unittest.TestCase):
    def test_planet_land_life(self):
        me, opp = pair()
        me.lands.append(C["andoria"])
        bt.on_land(me, opp, C["andoria"], 3, entry())
        self.assertEqual(me.life, 21)

    def test_modal_land_only_untapped(self):
        me, opp = pair()
        me.lands.append(C["outpost"])
        bt.on_land(me, opp, C["outpost"], 3, entry())  # getappt (Standard)
        self.assertEqual(me.life, 20)
        bt.on_land(me, opp, C["outpost"], 3, entry(), untapped=True)
        self.assertEqual(me.life, 22)  # Leben vor Surveil (Modus-Rang)

    def test_quark_deals_damage(self):
        me, opp = pair()
        bt.on_land(me, opp, C["quark"], 3, entry(), untapped=True)
        self.assertEqual(opp.life, 19)

    def test_unicomplex_creature_on_top(self):
        me, opp = pair(library=[PLAINS] * 5)
        me.graveyard = [ELF, GIANT]
        bt.on_land(me, opp, C["unicomplex"], 3, entry(), untapped=True)
        self.assertEqual((me.library[0], me.graveyard), (GIANT, [ELF]))  # die teuerste Kreatur

    def test_unicomplex_surveils_without_creature(self):
        me, opp = pair(library=[PLAINS] * 5)
        e = entry()
        bt.on_land(me, opp, C["unicomplex"], 3, e, untapped=True)
        self.assertEqual([c.name for c in me.library if c.is_creature], [])
        self.assertTrue(any("Surveil" in ev for ev in e["events"]))

    def test_nivar_flying_for_an_attacker(self):
        me, opp = pair()
        ogre = put(me, OGRE)
        bt.on_land(me, opp, C["nivar"], 3, entry(), untapped=True)
        self.assertTrue(ogre.has("flying"))

    def test_continuum_pumps_an_attacker(self):
        me, opp = pair()
        ogre = put(me, OGRE)
        bt.on_land(me, opp, C["continuum"], 3, entry(), untapped=True)
        self.assertEqual((ogre.power, ogre.toughness, ogre.has("vigilance")), (4, 4, True))

    def test_main_phase_land_drop_untapped(self):
        me, opp = pair(lands=[PLAINS, PLAINS])
        me.hand = [C["outpost"]]
        bt.take_turn(me, opp, 3, 3, True)
        self.assertEqual(me.life, 22)  # zwei andere Laender: ungetappt, Modus "2 Leben"


class LandfallAndAnthemTests(unittest.TestCase):
    def test_landfall_pump_until_end_of_turn(self):
        me, opp = pair()
        patrol = put(me, C["patrol"])
        bt.on_land(me, opp, PLAINS, 3, entry())
        self.assertEqual((patrol.power, patrol.toughness), (3, 3))
        bt.cleanup((me, opp))
        self.assertEqual((patrol.power, patrol.toughness), (2, 2))

    def test_booker_worm_cant_block(self):
        me, opp = pair()
        put(me, C["booker"])
        bt.on_land(me, opp, PLAINS, 3, entry())
        worm = next(c for c in me.creatures if c.card.name == "Worm")
        self.assertFalse(bt.can_block(worm, bt.Creature(BEAR, 0)))

    def test_picard_others(self):
        me, _opp = pair()
        picard, bear = put(me, C["picard"]), put(me, BEAR)
        self.assertEqual((picard.power, picard.toughness), (2, 3))
        self.assertEqual((bear.power, bear.toughness), (BEAR.power + 1, BEAR.toughness + 1))

    def test_sarcophagus_as_permanent(self):
        me, _opp = pair()
        me.perms.append(C["sarcophagus"])
        ogre = put(me, OGRE)
        self.assertEqual((ogre.power, ogre.toughness), (4, 3))

    def test_artifact_anthem(self):
        me, _opp = pair()
        put(me, C["locutus"])
        golem, ogre = put(me, GOLEM), put(me, OGRE)
        self.assertEqual((golem.power, golem.toughness, ogre.power), (4, 4, 3))
        locutus = me.creatures[0]
        self.assertEqual((locutus.power, locutus.toughness), (2, 2))  # gilt auch fuer sich selbst


class FoodAndRestrictionTests(unittest.TestCase):
    def test_neelix_food_at_end_of_opponents_turn(self):
        me, opp = pair()
        neelix = put(me, C["neelix"])
        bt.card_effects(me, opp, C["neelix"], 3, entry())
        self.assertEqual(me.foods, 1)
        me.open = [("G",), ("G",)]
        bt.use_food(me, entry())
        self.assertEqual((me.foods, me.life, neelix.bonus), (0, 23, 1))

    def test_food_needs_two_mana(self):
        me, _opp = pair()
        me.foods, me.open = 1, [("G",)]
        bt.use_food(me, entry())
        self.assertEqual((me.foods, me.life), (1, 20))

    def test_cant_block(self):
        tribbles = bt.Creature(C["tribbles"], 0)
        self.assertFalse(bt.can_block(tribbles, bt.Creature(BEAR, 0)))

    def test_sehlat_not_alone(self):
        sehlat = bt.Creature(C["sehlat"], 0)
        self.assertEqual(bt.choose_attackers([sehlat], [], 20, 20, 5), [])
        bear = bt.Creature(BEAR, 0)
        self.assertEqual(len(bt.choose_attackers([sehlat, bear], [], 20, 20, 5)), 2)

    def test_cold_blooded_crew_evasion(self):
        crew = bt.Creature(C["crew"], 0)
        self.assertFalse(bt.can_block(bt.Creature(card_info(_card("Two", f"Creature {DASH} X", "{1}", 1, "", "", [],
                                                                    "2", "5"))[0], 0), crew))
        self.assertTrue(bt.can_block(bt.Creature(OGRE, 0), crew))

    def test_species_not_blocked_by_artifacts(self):
        species = bt.Creature(C["species"], 0)
        self.assertFalse(bt.can_block(bt.Creature(GOLEM, 0), species))
        self.assertTrue(bt.can_block(bt.Creature(OGRE, 0), species))


class ProtectionTests(unittest.TestCase):
    def test_saru_answers_removal_without_counter(self):
        me, opp = pair(lands=[FOREST] * 3)
        giant = put(me, GIANT)
        me.hand, me.open = [C["saru"]], [("G",)] * 3
        self.assertTrue(bt.protect_response(me, giant, opp, entry(), 5))
        self.assertEqual((giant.has("hexproof"), giant.bonus), (True, 0))
        saru = next(c for c in me.creatures if c.card.name.startswith("Saru"))
        self.assertFalse(saru.has("hexproof"))

    def test_saru_alone_gets_nothing(self):
        me, opp = pair()
        saru = put(me, C["saru"])
        bt.creature_enters(me, saru, 3, entry(), opp)
        self.assertFalse(saru.has("hexproof"))

    def test_shields_up(self):
        me, opp = pair(lands=[PLAINS] * 2)
        giant = put(me, GIANT)
        me.hand, me.open = [C["shields"]], [("W",)] * 2
        self.assertTrue(bt.protect_response(me, giant, opp, entry(), 5))
        self.assertEqual((giant.has("hexproof"), giant.has("indestructible"), giant.bonus), (True, True, 1))
        self.assertEqual(me.hand, [])

    def test_shields_up_not_wasted_at_end_step(self):
        me, opp = pair(lands=[PLAINS] * 2)
        put(me, GIANT)
        me.hand, me.open = [C["shields"]], [("W",)] * 2
        bt.end_step_instants(me, opp, entry(), 5)
        self.assertEqual(me.hand, [C["shields"]])

    def test_tutelage_first_strike(self):
        me, opp = pair()
        ogre = put(me, OGRE)
        me.perms.append(C["tutelage"])
        bt.permanent_enters(me, opp, C["tutelage"], 3, entry())
        self.assertEqual((ogre.power, ogre.has("first strike")), (5, True))


class AttackAndCostTests(unittest.TestCase):
    def test_operative_deathtouch_against_blockers(self):
        me, opp = pair()
        operative, giant = put(me, C["operative"]), put(me, GIANT)
        put(opp, OGRE)
        bt.attack_choice_triggers(me, opp, [operative, giant], 5, entry())
        self.assertTrue(giant.has("deathtouch"))

    def test_operative_surveils_without_blockers(self):
        me, opp = pair(library=[PLAINS] * 5)
        operative = put(me, C["operative"])
        e = entry()
        bt.attack_choice_triggers(me, opp, [operative], 5, e)
        self.assertFalse(operative.has("deathtouch"))
        self.assertTrue(any("Surveil" in ev for ev in e["events"]))

    def test_red_alert_cheaper_when_attacked(self):
        me, _opp = pair()
        self.assertEqual(bt._alts(me, C["alert"]), ((2, (("R", 1),)),))
        me.under_attack = True
        self.assertEqual(bt._alts(me, C["alert"]), ((0, (("R", 1),)),))

    def test_guidance_failure_on_attacker(self):
        me, opp = pair()
        me.under_attack = True
        self.assertEqual(bt._alts(me, C["guidance"]), ((2, (("U", 1),)),))


class DeathTests(unittest.TestCase):
    def test_munitions_kills_a_creature(self):
        me, opp = pair()
        munitions = put(me, C["munitions"])
        elf = put(opp, ELF)
        munitions.dead = True
        bt.bury((me, opp), entry())
        self.assertNotIn(elf, opp.creatures)
        self.assertEqual(opp.life, 20)

    def test_munitions_face_otherwise(self):
        me, opp = pair()
        munitions = put(me, C["munitions"])
        put(opp, OGRE)
        munitions.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual(opp.life, 19)

    def test_munitions_lethal_goes_face(self):
        me, opp = pair()
        munitions = put(me, C["munitions"])
        elf = put(opp, ELF)
        opp.life = 1
        munitions.dead = True
        bt.bury((me, opp), entry())
        self.assertIn(elf, opp.creatures)
        self.assertEqual(opp.life, 0)

    def test_death_tokens(self):
        me, opp = pair()
        duras, drone = put(me, C["duras"]), put(me, C["drone"])
        duras.dead = drone.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual(sorted(c.card.name for c in me.creatures), ["Borg", "Klingon Warrior"])


class PlanetTests(unittest.TestCase):
    def test_marcus_planet_tapped(self):
        me, opp = pair(lands=[FOREST] * 3)
        me.open = []
        bt.card_effects(me, opp, C["marcus"], 3, entry())
        self.assertEqual([l.name for l in me.lands], ["Forest"] * 3 + ["New Planet"])
        self.assertEqual(me.open, [])  # getappt
        self.assertIn(ANY_COLOR, bt._mana(me, 4)[0])

    def test_planet_triggers_landfall(self):
        me, opp = pair()
        patrol = put(me, C["patrol"])
        bt.planet_tokens(me, opp, 1, 3, entry(), "Test")
        self.assertEqual(patrol.power, 3)

    def test_genesis_effect(self):
        me, opp = pair(lands=[WASTE, FOREST, FOREST, MOUNTAIN, MOUNTAIN])
        giant = put(opp, GIANT)
        bt._resolve(me, opp, C["genesis_effect"], 5, entry())
        self.assertNotIn(giant, opp.creatures)
        self.assertEqual(sorted(l.name for l in me.lands), ["Forest", "Forest", "Mountain", "Mountain", "New Planet"])

    def test_wormhole_on_attack(self):
        me, opp = pair(lands=[FOREST] * 3)
        me.perms.append(C["wormhole"])
        bt.attack_planets(me, opp, 5, entry())
        self.assertEqual(len(me.lands), 4)

    def test_saurian_ability_in_main_two(self):
        me, opp = pair(lands=[FOREST] * 6)
        put(me, C["saurian"])
        me.open = [("G",)] * 6
        bt.planet_abilities(me, opp, 5, entry())
        self.assertEqual((len(me.lands), me.open), (7, []))

    def test_saurian_ability_needs_free_mana(self):
        me, opp = pair(lands=[FOREST] * 6)
        put(me, C["saurian"])
        me.open = [("G",)] * 5
        bt.planet_abilities(me, opp, 5, entry())
        self.assertEqual(len(me.lands), 6)

    def test_saurian_keeps_mana_for_instants(self):
        me, opp = pair(lands=[FOREST] * 6)
        put(me, C["saurian"])
        me.hand = [GROWTH]
        me.open = [("G",)] * 6
        bt.planet_abilities(me, opp, 5, entry())
        self.assertEqual((len(me.lands), len(me.open)), (6, 6))


class AnomalyTests(unittest.TestCase):
    def setUp(self):
        self.me, self.opp = pair(library=[BEAR] * 10)

    def ready(self, land, others, color):
        self.me.lands = [land] + [others] * 6
        self.me.open = [land.land_colors] + [(color,)] * 6

    def test_gaseous_draws(self):
        self.ready(C["gaseous"], ISLAND, "U")
        bt.land_sac_abilities(self.me, self.opp, 5, entry())
        self.assertEqual((len(self.me.hand), len(self.me.lands)), (2, 7))
        self.assertIn("New Planet", [l.name for l in self.me.lands])
        self.assertIn(C["gaseous"], self.me.graveyard)

    def test_gaseous_needs_its_own_tap(self):
        self.ready(C["gaseous"], ISLAND, "U")
        self.me.open.remove(C["gaseous"].land_colors)  # schon getappt
        bt.land_sac_abilities(self.me, self.opp, 5, entry())
        self.assertEqual(len(self.me.hand), 0)

    def test_spatial_only_with_a_kill(self):
        self.ready(C["spatial"], MOUNTAIN, "R")
        put(self.opp, OGRE)
        bt.land_sac_abilities(self.me, self.opp, 5, entry())
        self.assertIn(C["spatial"], self.me.lands)
        elf = put(self.opp, ELF)
        bt.land_sac_abilities(self.me, self.opp, 5, entry())
        self.assertNotIn(elf, self.opp.creatures)

    def test_subspace_tokens(self):
        self.ready(C["subspace"], PLAINS, "W")
        bt.land_sac_abilities(self.me, self.opp, 5, entry())
        self.assertEqual([c.card.name for c in self.me.creatures], ["Officer", "Officer"])

    def test_temporal_mill_takes_permanent(self):
        self.me.library = [KILL, GIANT, PLAINS, ELF, BEAR]
        self.ready(C["temporal"], FOREST, "G")
        bt.land_sac_abilities(self.me, self.opp, 5, entry())
        self.assertEqual(self.me.hand, [GIANT])
        self.assertEqual(sorted(c.name for c in self.me.graveyard),
                         sorted([KILL.name, PLAINS.name, ELF.name, "Temporal Anomaly"]))

    def test_artificial_drain(self):
        self.ready(C["artificial"], SWAMP, "B")
        bt.land_sac_abilities(self.me, self.opp, 5, entry())
        self.assertEqual((self.me.life, self.opp.life), (22, 18))

    def test_territory_fetches_basic(self):
        self.me.library = [PLAINS, ISLAND, ISLAND]
        self.me.lands = [C["territory"], ISLAND]
        self.me.open = [("C",), ("U",)]
        bt.land_sac_abilities(self.me, self.opp, 5, entry())
        self.assertEqual(sorted(l.name for l in self.me.lands), ["Island", "Plains"])  # neue Farbe zuerst


class SearchTests(unittest.TestCase):
    def test_frontier_basic_onto_battlefield(self):
        me, opp = pair(library=[PLAINS, FOREST, FOREST], lands=[FOREST])
        bt._resolve(me, opp, C["frontier"], 5, entry())
        self.assertEqual(sorted(l.name for l in me.lands), ["Forest", "Plains"])
        self.assertEqual(len(me.library), 2)

    def test_frontier_prefers_planet_with_new_colors(self):
        me, opp = pair(library=[PLAINS, ANDORIA_LAND, FOREST], lands=[FOREST])
        bt._resolve(me, opp, C["frontier"], 5, entry())
        self.assertIn(ANDORIA_LAND, me.lands)
        self.assertEqual(me.life, 21)  # das Planeten-Land loest beim Betreten aus

    def test_device_on_enter(self):
        me, opp = pair(library=[ISLAND], lands=[FOREST])
        me.perms.append(C["device"])
        bt.permanent_enters(me, opp, C["device"], 5, entry())
        self.assertIn(ISLAND, me.lands)

    def test_naked_time_mountain(self):
        me, opp = pair(library=[PLAINS, MOUNTAIN], lands=[FOREST])
        chapter = C["naked"].saga[1][0][1]
        bt.card_effects(me, opp, chapter, 5, entry())
        self.assertIn(MOUNTAIN, me.lands)
        self.assertNotIn(PLAINS, me.lands)

    def test_warp_core_and_oberth_to_hand(self):
        me, opp = pair(library=[ISLAND, PLAINS, FOREST], lands=[FOREST])
        bt.permanent_enters(me, opp, C["oberth"], 5, entry())
        self.assertEqual(me.hand, [PLAINS])
        bt.permanent_enters(me, opp, C["warp_core"], 5, entry())
        self.assertEqual(me.hand, [PLAINS, ISLAND])

    def test_goldfish_search_type(self):
        from components import simulation as sim
        lib = [PLAINS, MOUNTAIN, FOREST]
        bf = []
        sim.fetch_basic_tapped(C["naked"].saga[1][0][1], lib, bf)
        self.assertEqual((bf, len(lib)), ([MOUNTAIN], 2))


if __name__ == "__main__":
    unittest.main()
