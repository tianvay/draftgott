"""FRA-Paket B (Punkte 21-31 ohne Spielentscheidungen): Simulacrum Shaper sucht ein Basic Land getappt aufs Feld,
Gardenize (Charge-Marken bei Toden, {G} je Marke in der ersten Main Phase), Sphinx of False Conclusions (Token-Kopie
beim Sterben, 707.2/111.10), Command the Stage (Cadet und Marken auf andere Wizard-Token; Rueckkehr auf die Hand nach
nichtkampfschaden am Gegner im letzten Zug), Verdant Kraken (in jedem Upkeep ein 3/3 Tentacle mit {T}: {G}), Danitha,
Sword of Hope (Ziehen bei Equipment oder Zauber auf eigene Kreatur, einmal pro Zug), Yoshimaru (eine Marke mehr,
614.1/122.6), Bloodline Recollector (prepared nach 3 Toden), Infinite Coursework (unprepared), Garruk, Veiled Butcher
(gegnerische Kreaturen werden exiliert statt zu sterben, 614.6: kein "dies")."""
import unittest
from unittest import mock

from components import battle as bt
from components import simulation as sim
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS, BEAR = W["Plains"], W["Test Bear"]


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="G", **extra):
    d = _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)
    d.update(extra)
    return card_info(d)[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


def prep(name, cost, cmc, text, spell_name, spell_cost, spell_text, power, toughness, colors="B", spell_type="Instant"):
    d = {"name": f"{name} // {spell_name}", "layout": "prepare", "type_line": f"Creature {DASH} Test // {spell_type}",
         "mana_cost": "", "cmc": float(cmc), "colors": list(colors), "keywords": ["Prepared"],
         "card_faces": [{"name": name, "type_line": f"Creature {DASH} Test", "mana_cost": cost, "power": power,
                         "toughness": toughness, "oracle_text": text},
                        {"name": spell_name, "type_line": spell_type, "mana_cost": spell_cost,
                         "oracle_text": spell_text}]}
    return card_info(d)[0]


FOREST, ISLAND, SWAMP = land("Forest", "G"), land("Island", "U"), land("Swamp", "B")
SIMULACRUM = make("Simulacrum Shaper", f"Creature {DASH} Elf Druid", "{1}{G}{G}", 3, "When this creature enters, you "
                  "may search your library for a basic land card, put that card onto the battlefield tapped, then "
                  "shuffle.\nWhen this creature dies, draw a card.", "2", "2")
GARDENIZE = make("Gardenize", "Enchantment", "{1}{G}{G}", 3, "Whenever a creature you control dies, put a charge "
                 "counter on this enchantment.\nAt the beginning of your first main phase, add {G} for each charge "
                 "counter on this enchantment.")
SPHINX = make("Sphinx of False Conclusions", f"Creature {DASH} Sphinx Illusion", "{2}{U}{U}", 4, "Flash\nFlying\n"
              "Whenever this creature attacks, draw a card, then discard a card.\nWhen this creature dies, if it isn't a "
              "token, create a token that's a copy of it.", "4", "2", ["Flash", "Flying"], colors="U")
COMMAND = make("Command the Stage", "Sorcery", "{2}{R}", 3, "Create a 2/2 colorless Wizard Soldier creature token named "
               "Cadet, then put a +1/+1 counter on each other Wizard token you control.\nAt the beginning of each "
               "upkeep, if an opponent was dealt noncombat damage last turn, return this card from your graveyard to "
               "your hand.", colors="R")
KRAKEN = make("Verdant Kraken", f"Creature {DASH} Plant Kraken", "{4}{G}{G}{G}", 7, "At the beginning of each player's "
              "upkeep, you create a 3/3 green Forest Tentacle land creature token. (It has \"{T}: Add {G}.\" It's "
              "affected by summoning sickness until your next turn.)", "6", "6")
DANITHA = make("Danitha, Sword of Hope", f"Legendary Creature {DASH} Human Knight", "{2}{W}", 3, "First strike\n"
               "Whenever you cast an Equipment spell or a spell that targets a creature you control, draw a card. This "
               "ability triggers only once each turn.", "2", "2", ["First strike"], colors="W")
YOSHIMARU = make("Yoshimaru, Beloved Companion", f"Legendary Creature {DASH} Dog", "{2}{W}", 3, "If one or more +1/+1 "
                 "counters would be put on a creature you control, that many plus one +1/+1 counters are put on it "
                 "instead.\n{6}: Put a +1/+1 counter on target legendary creature.", "2", "2", colors="W")
RECOLLECTOR = prep("Bloodline Recollector", "{1}{B}", 2, "At the beginning of each end step, if three or more creatures "
                   "died this turn, this creature becomes prepared.", "Ancestral Craving", "{B}",
                   "Target player draws three cards and loses 3 life.", "2", "2")
COURSEWORK = make("Infinite Coursework", f"Enchantment {DASH} Aura", "{2}{U}", 3, "Enchant creature\nWhen this Aura "
                  "enters, tap enchanted creature. It becomes unprepared.\nEnchanted creature loses all abilities and "
                  "doesn't untap during its controller's untap step.", keywords=["Enchant"], colors="U")
BUTCHER = card_info(dict(_card("Garruk, Veiled Butcher", f"Legendary Planeswalker {DASH} Garruk", "{3}{B}{B}", 5, "B",
                               "If a creature an opponent controls would die, exile it instead.\n+2: Up to one target "
                               "creature gets -4/-1 until your next turn."), loyalty="5"))[0]
PREPARED_FOE = prep("Theorix Scholar", "{1}{U}", 2, "This creature enters prepared.", "Quick Study", "{U}",
                    "Draw a card.", "2", "2", colors="U", spell_type="Sorcery")
BOLT = make("Searing Bolt", "Sorcery", "{R}", 1, "Searing Bolt deals 1 damage to each opponent.", colors="R")
PUMP = make("Giant Growth", "Instant", "{G}", 1, "Target creature gets +3/+3 until end of turn.")
AXE = make("Simple Axe", f"Artifact {DASH} Equipment", "{1}", 1, "Equipped creature gets +1/+0.\nEquip {1}", colors="")
GROWTH = make("Rampant Growth", "Sorcery", "{1}{G}", 2, "Put a +1/+1 counter on target creature.")
EDGAR = make("Edgar Watcher", CRE, "{1}{B}", 2, "Whenever another creature or planeswalker you control dies, you gain 1 "
             "life.", "1", "1", colors="B")
WAVE = make("Pyro Wave", "Sorcery", "{1}{R}", 2, "Pyro Wave deals 2 damage to each creature your opponents control.",
            colors="R")


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
        self.assertTrue(SIMULACRUM.etb_basic_tapped)
        self.assertTrue(GARDENIZE.charge_on_death)
        self.assertTrue(SPHINX.death_token_copy)
        self.assertTrue(COMMAND.wizard_token_counters and COMMAND.noncombat_recur)
        self.assertEqual(KRAKEN.upkeep_token.name, "Forest Tentacle")
        self.assertTrue(DANITHA.own_target_draw)
        self.assertTrue(YOSHIMARU.counter_plus_one)
        self.assertEqual(RECOLLECTOR.prepared[0], "deaths3")
        self.assertTrue(COURSEWORK.unprepare)
        self.assertTrue(BUTCHER.opp_exile_instead)
        self.assertFalse(BEAR.etb_basic_tapped or BEAR.death_token_copy or BEAR.counter_plus_one)


class SimulacrumTests(unittest.TestCase):
    def test_basic_land_tapped_onto_the_battlefield(self):
        me, opp = pair()
        me.lands = [FOREST, FOREST]
        me.library = [FOREST, ISLAND] + [FOREST] * 5  # Island bringt als einziges eine neue Farbe
        bt._resolve(me, opp, SIMULACRUM, 3, entry())
        self.assertEqual(([c.name for c in me.lands], ISLAND in me.library), (["Forest", "Forest", "Island"], False))
        self.assertEqual(me.open, [])  # getappt: kein Mana

    def test_goldfish_ramp(self):
        hand = [FOREST, FOREST, FOREST, SIMULACRUM, PLAINS, PLAINS, PLAINS]
        with mock.patch("components.mulligan.random.shuffle", lambda x: None):
            r = sim.simulate(hand + [ISLAND] + [PLAINS] * 20, 1, False, 3, 4, True, False, None, 11, 20, 6, True, 3,
                             6, False, False, 5, True)
        self.assertEqual(r["curve"]["avail"][4], 5)  # Runde 4: 4 Laender + das gesuchte


class GardenizeTests(unittest.TestCase):
    def test_charge_counters_give_green_mana(self):
        me, opp = pair()
        me.perms = [GARDENIZE]
        on_board(me, BEAR).dead = True
        on_board(me, BEAR).dead = True
        bt.bury((me,), entry())
        self.assertEqual(me.charges, 2)
        big = make("Big Green", CRE, "{2}{G}", 3, "", "4", "4")
        me.lands, me.hand = [FOREST], [big]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertIn("Big Green", [c.card.name for c in me.creatures])


class SphinxTests(unittest.TestCase):
    def test_token_copy_when_it_dies(self):
        me, _opp = pair()
        on_board(me, SPHINX).dead = True
        bt.bury((me,), entry())
        self.assertEqual([(c.card.name, c.card.is_token) for c in me.creatures], [("Sphinx of False Conclusions", True)])
        me.creatures[0].dead = True
        bt.bury((me,), entry())
        self.assertEqual(me.creatures, [])  # die Kopie ist ein Token


class CommandTests(unittest.TestCase):
    def test_cadet_and_counters_on_other_wizard_tokens(self):
        me, opp = pair()
        other = on_board(me, BEAR._replace(name="Cadet", is_token=True, creature_types=("wizard", "soldier")))
        bear = on_board(me, BEAR)
        bt._resolve(me, opp, COMMAND, 3, entry())
        new = [c for c in me.creatures if c is not other and c is not bear][0]
        self.assertEqual((other.bonus, bear.bonus, new.bonus, new.card.name), (1, 0, 0, "Cadet"))

    def test_returns_after_noncombat_damage(self):
        me, opp = pair()
        me.graveyard = [COMMAND]
        me.hand = [BOLT]
        me.lands = [land("Mountain", "R")]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)  # Bolt: 1 Schaden am Gegner
        bt.take_turn(opp, me, 6, 3, skip_draw=True)  # Upkeep des Gegners: Gegner bekam im letzten Zug Schaden
        self.assertEqual((COMMAND in me.hand, COMMAND in me.graveyard), (True, False))

    def test_stays_without_damage(self):
        me, opp = pair()
        me.graveyard = [COMMAND]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        bt.take_turn(opp, me, 6, 3, skip_draw=True)
        self.assertIn(COMMAND, me.graveyard)


class KrakenTests(unittest.TestCase):
    def test_tentacle_every_upkeep(self):
        me, opp = pair()
        on_board(me, KRAKEN)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        bt.take_turn(opp, me, 6, 3, skip_draw=True)
        tentacles = [c for c in me.creatures if c.card.name == "Forest Tentacle"]
        self.assertEqual(len(tentacles), 2)
        self.assertEqual((tentacles[0].power, tentacles[0].card.mana_src, tentacles[0].card.is_token), (3, (("G",),),
                                                                                                         True))


class DanithaTests(unittest.TestCase):
    def test_draw_once_each_turn(self):
        me, opp = pair()
        on_board(me, DANITHA)
        on_board(me, BEAR)
        bt._resolve(me, opp, PUMP, 3, entry())
        bt._resolve(me, opp, AXE, 3, entry())
        self.assertEqual(len(me.library), 19)  # nur einmal pro Zug
        me.now = 5
        bt._resolve(me, opp, AXE, 5, entry())
        self.assertEqual(len(me.library), 18)

    def test_not_for_other_spells(self):
        me, opp = pair()
        on_board(me, DANITHA)
        bt._resolve(me, opp, BOLT, 3, entry())
        self.assertEqual(len(me.library), 20)


class YoshimaruTests(unittest.TestCase):
    def test_one_more_counter(self):
        me, opp = pair()
        on_board(me, YOSHIMARU)
        bear = on_board(me, BEAR)
        bt._resolve(me, opp, GROWTH, 3, entry())
        self.assertEqual(bear.bonus + [c for c in me.creatures if c.card is YOSHIMARU][0].bonus, 2)

    def test_not_for_the_opponent(self):
        me, opp = pair()
        on_board(me, YOSHIMARU)
        foe = on_board(opp, BEAR)
        foe.bonus += 1
        self.assertEqual(foe.bonus, 1)

    def test_removing_counters_is_not_affected(self):
        me, _opp = pair()
        on_board(me, YOSHIMARU)
        bear = on_board(me, BEAR)
        bear.bonus += 2
        bear.bonus -= 1
        self.assertEqual(bear.bonus, 2)


class RecollectorTests(unittest.TestCase):
    def test_prepared_after_three_deaths(self):
        me, opp = pair()
        rec = on_board(me, RECOLLECTOR)
        self.assertFalse(rec.prepared)
        for _ in range(3):
            on_board(opp, BEAR).dead = True
        bt.bury((opp,), entry())
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertFalse(rec.prepared)  # die Tode waren vor diesem Zug
        for _ in range(3):
            on_board(opp, BEAR).dead = True
        opp.deaths_mark = opp.deaths - 2
        bt.end_step_prepare((me, opp), {"events": []})
        self.assertFalse(rec.prepared)  # nur 2 Tode
        opp.deaths_mark = opp.deaths - 3
        bt.end_step_prepare((me, opp), {"events": []})
        self.assertTrue(rec.prepared)

    def test_prepared_in_a_real_turn(self):
        me, opp = pair()
        rec = on_board(me, RECOLLECTOR)
        for _ in range(3):
            on_board(opp, BEAR)
        me.lands, me.hand = [land("Mountain", "R")] * 2, [WAVE]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((opp.creatures, rec.prepared), ([], True))


class CourseworkTests(unittest.TestCase):
    def test_unprepares(self):
        me, opp = pair()
        foe = on_board(opp, PREPARED_FOE)
        foe.prepared = True
        me.lands, me.hand = [ISLAND] * 3, [COURSEWORK]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((foe.prepared, foe.locked), (False, True))


class ButcherTests(unittest.TestCase):
    def test_opponent_creatures_are_exiled(self):
        me, opp = pair()
        me.walkers.append(bt.Walker(BUTCHER, 0))
        on_board(opp, EDGAR)
        on_board(opp, BEAR).dead = True
        bt.bury((me, opp), entry())
        self.assertEqual((opp.graveyard, opp.life, opp.deaths), ([], 20, 0))  # kein "dies"-Ausloeser

    def test_own_creatures_still_die(self):
        me, opp = pair()
        me.walkers.append(bt.Walker(BUTCHER, 0))
        on_board(me, BEAR).dead = True
        bt.bury((me, opp), entry())
        self.assertEqual(me.graveyard, [BEAR])


if __name__ == "__main__":
    unittest.main()
