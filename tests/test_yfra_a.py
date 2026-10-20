"""Alchemy: Reality Fracture (YFRA), Paket A (ohne neue Spielentscheidungen): Avoided Stairwurm, Zimone (Schaden wie
positive Power, prepared bei Karten aus der Bibliothek in den Friedhof, Simple Subtraction perpetuell -3/-0), Dina
(perpetuell +1/+1 bei Lebensgewinn), Asymmetry Sage (Magecraft: Grund-Power 3), Sparks Ablaze (naechster
Planeswalker {1} billiger), Conjure benannter Karten (Paradox Kraken, Boisterous Clique, Searing Soloist mit Aria of
Flame) und Killian (Seek nach Schaden ausserhalb des Kampfs)."""
import random
import unittest

from components import battle as bt
from components.cards import card_info
from components.conjure import conjure
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]
BEAR = W["Test Bear"]


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="W"):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)


def make(*args, **kwargs):
    return card_info(raw(*args, **kwargs))[0]


def prepare_raw(name, type_line, cost, cmc, text, pt, colors, spell_name, spell_type, spell_cost, spell_text):
    front = {"name": name, "type_line": type_line, "mana_cost": cost, "oracle_text": text, "power": pt[0],
             "toughness": pt[1], "colors": list(colors)}
    back = {"name": spell_name, "type_line": spell_type, "mana_cost": spell_cost, "oracle_text": spell_text,
            "colors": list(colors)}
    return {"name": f"{name} // {spell_name}", "layout": "prepare", "cmc": float(cmc), "colors": list(colors),
            "keywords": [], "type_line": f"{type_line} // {spell_type}", "card_faces": [front, back]}


RAW = {
    "stairwurm": raw("Avoided Stairwurm", f"Artifact Creature {DASH} Wurm", "{B}", 1,
                     "Menace\nThis creature gets -1/-1 for each creature card in your library.", "5", "5", ["Menace"],
                     "B"),
    "zimone": prepare_raw("Zimone the Calculating", f"Legendary Creature {DASH} Human Warlock", "{U}{B}", 2,
                          "Zimone assigns combat damage as though her power were positive.\nWhenever one or more cards "
                          "are put into your graveyard from your library, Zimone becomes prepared.", ("-1", "4"), "UB",
                          "Simple Subtraction", "Instant", "{1}{U}", "Target creature perpetually gets -3/-0."),
    "dina": raw("Dina, Flesh Sower", f"Legendary Creature {DASH} Dryad Cleric", "{G}{W}", 2,
                "Lifelink\nWhenever you gain life, Dina perpetually gets +1/+1.", "1", "1", ["Lifelink"], "GW"),
    "sage": raw("Asymmetry Sage", f"Creature {DASH} Human Wizard", "{U}", 1,
                "Flying\nMagecraft — Whenever you cast or copy an instant or sorcery spell, target creature you "
                "control has base power 3 until end of turn.", "0", "2", ["Flying", "Magecraft"], "U"),
    "sparks": raw("Sparks Ablaze", "Instant", "{R}", 1,
                  "Sparks Ablaze deals 2 damage to target creature or planeswalker. If that creature or planeswalker "
                  "would die this turn, exile it instead.\nThe next planeswalker spell you cast costs {1} less to "
                  "cast.", colors="R"),
    "kraken": raw("Paradox Kraken", f"Creature {DASH} Kraken", "{4}{U}{U}", 6,
                  "When this card is put into your graveyard from anywhere, conjure a card named Kraken Hatchling into "
                  "your hand.\n{1}{U}: Return this card from your graveyard to the battlefield. Activate only if "
                  "there are more cards in your graveyard than your library and only as a sorcery.", "7", "7",
                  colors="U"),
    "clique": raw("Boisterous Clique", f"Creature {DASH} Faerie Warlock", "{1}{B}{B}", 3,
                  "Flash\nFlying\nWhen this creature enters, look at all nonland cards in target player's hand. You "
                  "may exile one of those cards. If you do, that player conjures a card named Mind Stone into their "
                  "hand.", "3", "1", ["Flash", "Flying"], "B"),
    "soloist": raw("Searing Soloist", f"Creature {DASH} Orc Bard", "{2}{R}{R}", 4,
                   "When this creature enters, conjure a card named Aria of Flame onto the battlefield.\nIf a red "
                   "source you control would deal damage to a permanent or player, it deals that much damage plus 1 "
                   "instead.", "3", "3", colors="R"),
    "killian": raw("Killian, Spotlight Chaser", f"Legendary Creature {DASH} Human Bard", "{B}{R}", 2,
                   "Whenever a source you control deals noncombat damage to an opponent, seek a card with mana value "
                   "equal to the damage dealt. Discard that card at the beginning of the next end step.", "2", "2",
                   colors="BR"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}

OGRE = make("Ogre", f"Creature {DASH} Ogre", "{2}{R}", 3, "", "3", "3", colors="R")
GOBLIN = make("Red Goblin", f"Creature {DASH} Goblin", "{R}", 1, "", "2", "1", colors="R")
DRAW = make("Divination", "Sorcery", "{2}{U}", 3, "Draw two cards.", colors="U")
SHOCK = make("Shock", "Instant", "{R}", 1, "Shock deals 2 damage to any target.", colors="R")
WALKER = make("Test Walker", f"Legendary Planeswalker {DASH} Ajani", "{2}{W}", 3, "+1: You gain 1 life.")
MILLER = make("Mill Spell", "Sorcery", "{U}", 1, "Mill three cards.", colors="U")


def player(name="Wir"):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], [PLAINS] * 20
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


class ConjureTests(unittest.TestCase):
    def test_named_cards(self):
        for name in ("Kraken Hatchling", "Mind Stone", "Aria of Flame", "Seed of Hope", "Jace's Sentinel"):
            card = conjure(name)
            self.assertEqual((card.name, card.conjured), (name, True))
        self.assertEqual((conjure("Kraken Hatchling").power, conjure("Kraken Hatchling").toughness), (0, 4))
        self.assertTrue(conjure("Mind Stone").mana_src)

    def test_unknown_name(self):
        self.assertIsNone(conjure("Kein Name"))

    def test_each_conjure_is_a_new_object(self):
        self.assertIsNot(conjure("Aria of Flame"), conjure("Aria of Flame"))


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertTrue(C["stairwurm"].lib_creature_minus)
        self.assertTrue(C["zimone"].abs_damage)
        self.assertEqual(C["zimone"].prepared[0], "mill")
        self.assertEqual((C["zimone"].prepared[1].debuff, C["zimone"].prepared[1].debuff_perpetual), (3, True))
        self.assertEqual(C["dina"].lifegain_perpetual, 1)
        self.assertEqual(C["sage"].cast_trig, (("instsorc", (("base_power", 3),), (), ""),))
        self.assertEqual(C["sparks"].next_pw_discount, 1)
        self.assertEqual(C["kraken"].gy_conjure, "Kraken Hatchling")
        self.assertEqual(C["kraken"].gy_return[5], "gy_gt_lib")
        self.assertEqual((C["clique"].hand_pick, C["clique"].hand_pick_gift), ("nonland", "Mind Stone"))
        self.assertEqual(C["soloist"].etb_conjure, "Aria of Flame")
        self.assertTrue(C["soloist"].red_plus_one)
        self.assertTrue(C["killian"].noncombat_seek)

    def test_aria(self):
        aria = conjure("Aria of Flame")
        self.assertEqual((aria.opp_etb_life, aria.verse), (10, True))

    def test_coverage(self):
        for key in RAW:
            self.assertEqual([line for _c, _m, line in analyze_card(RAW[key])], [], key)


class StaticTests(unittest.TestCase):
    def test_stairwurm_shrinks(self):
        me, _opp = pair()
        wurm = on_board(me, C["stairwurm"])
        me.library = [BEAR, BEAR, PLAINS]
        self.assertEqual((wurm.power, wurm.toughness), (3, 3))

    def test_stairwurm_dies_with_many_creatures(self):
        me, opp = pair()
        on_board(me, C["stairwurm"])
        me.library = [BEAR] * 6
        bt.bury((me, opp), entry())
        self.assertEqual(me.creatures, [])

    def test_zimone_deals_damage(self):
        me, _opp = pair()
        zimone = on_board(me, C["zimone"])
        self.assertEqual(zimone.dmg, 1)


class ZimoneTests(unittest.TestCase):
    def test_prepared_after_mill(self):
        me, opp = pair()
        zimone = on_board(me, C["zimone"])
        zimone.prepared = False
        bt._resolve(me, opp, MILLER, 3, entry())
        self.assertTrue(zimone.prepared)

    def test_prepared_after_surveil_to_graveyard(self):
        me, _opp = pair()
        zimone = on_board(me, C["zimone"])
        zimone.prepared = False
        me.library = [PLAINS] * 20
        me.lands = [PLAINS] * 8  # genug Laender: Surveil legt Laender ab
        bt.surveil_cards(me, [2], entry(), "Test")
        self.assertEqual(zimone.prepared, len(me.graveyard) > 0)

    def test_perpetual_minus_stays(self):
        me, opp = pair()
        ogre = on_board(opp, OGRE)
        bt.perpetual_pump(ogre, -3, 0)
        bt.cleanup((me, opp))
        self.assertEqual(ogre.power, 0)
        self.assertEqual(ogre.card.power, 0)


class DinaTests(unittest.TestCase):
    def test_grows_with_lifegain(self):
        me, _opp = pair()
        dina = on_board(me, C["dina"])
        bt.gain_life(me, 3)
        bt.gain_life(me, 1)
        bt.cleanup((me,))
        self.assertEqual((dina.power, dina.toughness), (3, 3))

    def test_perpetual_card_goes_to_graveyard(self):
        me, opp = pair()
        dina = on_board(me, C["dina"])
        bt.gain_life(me, 1)
        dina.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual((me.graveyard[-1].name, me.graveyard[-1].power), ("Dina, Flesh Sower", 2))


class SageTests(unittest.TestCase):
    def test_base_power_on_the_best_gain(self):
        me, _opp = pair()
        sage = on_board(me, C["sage"])
        bear = on_board(me, BEAR)
        bt.on_cast(me, DRAW, 5, entry())
        self.assertEqual((sage.power, bear.power), (3, 2))

    def test_no_loss_for_strong_creatures(self):
        me, _opp = pair()
        sage = on_board(me, C["sage"], entered=5)  # kann nicht angreifen
        ogre = on_board(me, make("Big", f"Creature {DASH} Giant", "{4}", 4, "", "5", "5", colors=""))
        bt.on_cast(me, DRAW, 5, entry())
        self.assertEqual((sage.power, ogre.power), (3, 5))


class SparksTests(unittest.TestCase):
    def test_next_walker_cheaper_once(self):
        me, opp = pair()
        bt._resolve(me, opp, C["sparks"], 3, entry())
        self.assertEqual(min(g + sum(n for _c, n in cols) for g, cols in bt._alts(me, WALKER)), 2)
        bt.on_cast(me, WALKER, 3, entry())
        self.assertEqual(min(g + sum(n for _c, n in cols) for g, cols in bt._alts(me, WALKER)), 3)


class KrakenTests(unittest.TestCase):
    def test_hatchling_when_it_dies(self):
        me, opp = pair()
        kraken = on_board(me, C["kraken"])
        kraken.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual([c.name for c in me.hand], ["Kraken Hatchling"])

    def test_hatchling_when_milled(self):
        me, _opp = pair()
        me.library = [C["kraken"], PLAINS]
        bt._mill(me, 2)
        self.assertEqual([c.name for c in me.hand], ["Kraken Hatchling"])

    def test_hatchling_when_discarded(self):
        me, opp = pair()
        me.hand = [C["kraken"]]
        bt.discard(me, 1, entry())
        self.assertEqual([c.name for c in me.hand], ["Kraken Hatchling"])

    def test_return_needs_bigger_graveyard(self):
        me, _opp = pair()
        me.graveyard.append(C["kraken"])
        me.library = [PLAINS] * 5
        self.assertFalse(bt._gy_return_ok(me, C["kraken"]))
        me.graveyard.extend([PLAINS] * 6)
        self.assertTrue(bt._gy_return_ok(me, C["kraken"]))


class CliqueTests(unittest.TestCase):
    def test_exile_and_mind_stone(self):
        me, opp = pair()
        opp.hand = [OGRE, PLAINS]
        opp.lands = [PLAINS] * 2
        bt._resolve(me, opp, C["clique"], 3, entry())
        self.assertEqual(sorted(c.name for c in opp.hand), ["Mind Stone", "Plains"])
        self.assertNotIn(OGRE, opp.graveyard)


class SoloistTests(unittest.TestCase):
    def test_aria_enters_and_opponent_gains(self):
        me, opp = pair()
        bt._resolve(me, opp, C["soloist"], 3, entry())
        self.assertIn("Aria of Flame", [c.name for c in me.perms])
        self.assertEqual(opp.life, 30)

    def test_aria_verse_counters_with_plus_one(self):
        me, opp = pair()
        bt._resolve(me, opp, C["soloist"], 3, entry())
        bt.on_cast(me, DRAW, 5, entry())
        self.assertEqual(opp.life, 28)  # 1 Vers + 1 (roter Quelle)
        bt.on_cast(me, DRAW, 5, entry())
        self.assertEqual(opp.life, 25)  # 2 Verse + 1

    def test_red_creature_deals_one_more(self):
        me, opp = pair()
        on_board(me, C["soloist"])
        goblin = on_board(me, GOBLIN)
        bear = on_board(me, BEAR)
        self.assertEqual((goblin.dmg, bear.dmg), (3, 2))
        self.assertEqual(opp.creatures, [])

    def test_red_burn_deals_one_more(self):
        me, opp = pair()
        on_board(me, C["soloist"])
        bt.cast_removal(SHOCK, me, opp, entry(), 3)
        self.assertEqual(opp.life, 17)

    def test_not_for_the_opponent(self):
        me, opp = pair()
        on_board(me, C["soloist"])
        goblin = on_board(opp, GOBLIN)
        self.assertEqual(goblin.dmg, 2)


class KillianTests(unittest.TestCase):
    def test_seek_by_damage_and_discard_at_end(self):
        me, opp = pair()
        on_board(me, C["killian"])
        me.library = [OGRE, BEAR, PLAINS, DRAW]
        random.seed(1)
        e = entry()
        bt.deal_noncombat(me, opp, 3, e)
        self.assertEqual(len(me.hand), 1)
        self.assertIn(me.hand[0].name, ("Ogre", "Divination"))
        self.assertEqual(len(me.library), 3)
        bt.end_step_discards((me, opp), e)
        self.assertEqual(me.hand, [])

    def test_no_card_with_that_value(self):
        me, opp = pair()
        on_board(me, C["killian"])
        me.library = [BEAR, PLAINS]
        bt.deal_noncombat(me, opp, 5, entry())
        self.assertEqual(me.hand, [])

    def test_cast_before_the_end_step_is_kept(self):
        me, opp = pair()
        on_board(me, C["killian"])
        me.library = [OGRE]
        e = entry()
        bt.deal_noncombat(me, opp, 3, e)
        me.hand.remove(OGRE)  # gewirkt
        bt.end_step_discards((me, opp), e)
        self.assertEqual(me.graveyard, [])


if __name__ == "__main__":
    unittest.main()
