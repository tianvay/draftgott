"""Star Trek (TRK), Paket R4 (Nutzer 2026-11-04): Opfern und Friedhof - Gowron und Kirk, Commanding Officer (opfern,
wenn eine Kreatur ohnehin stirbt), Dahar Master, Targ Wrangler, Dr. McCoy, Surly Surgeon (Marken statt Zerstoeren),
Dr. Leonard "Bones" McCoy, Commander Raffi Musiker, Gabriel Lorca, The Needs of the Many (gegen Lethal und Sweeper),
De-evolve, Tell Me What You See (der Gegner verliert 4 Leben, ausser knapp), Khan, Vengeful Heart (Wirken aus dem
eigenen Exil: Removal mit Exil, Finality, verfallene Impulse). Nur Kampfmodell. Kartentexte aus TRK."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from components.mana import cost_alternatives
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
PLAINS = W["Plains"]

RAW = {
    "gowron": _card("Gowron, Eager for Battle", f"Legendary Creature {DASH} Klingon Warrior", "{2}{B}{R}", 4, "BR",
                    "Whenever another creature dies, put a +1/+1 counter on Gowron.\nSacrifice another creature: Gowron "
                    "gains trample until end of turn. If you sacrificed a Klingon this way, you draw a card and lose 1 "
                    "life.", [], "3", "3"),
    "kirk": _card("Kirk, Commanding Officer", f"Legendary Creature {DASH} Human Officer", "{1}{R}{W}", 3, "RW",
                  "Whenever you attack while creatures you control have total power 8 or greater, exile the top card "
                  "of your library. You may play that card this turn.\n{2}, Sacrifice Kirk: Destroy target artifact or "
                  "enchantment.", [], "3", "3"),
    "dahar": _card("Dahar Master", f"Creature {DASH} Klingon Warrior", "{3}{R}", 4, "R", "When this creature enters, you "
                   "may sacrifice another nonland permanent. When you do, this creature deals 2 damage to any target.",
                   [], "4", "3"),
    "targ": _card("Targ Wrangler", f"Creature {DASH} Klingon Warrior", "{2}{R}", 3, "R", "Menace (This creature can't be "
                  "blocked except by two or more creatures.)\nAt the beginning of your end step, if this creature "
                  "attacked this turn, sacrifice a nonland permanent.", ["Menace"], "5", "3"),
    "mccoy": _card("Dr. McCoy, Surly Surgeon", f"Legendary Creature {DASH} Human Doctor", "{2}{W}{W}", 4, "W", "When Dr. "
                   "McCoy enters, put a +1/+1 counter on another target creature you control.\nIf another creature you "
                   "control with a +1/+1 counter on it would be destroyed, instead remove all +1/+1 counters from it "
                   "and all damage already dealt to it is healed.", [], "2", "2"),
    "bones": _card("Dr. Leonard \"Bones\" McCoy", f"Legendary Creature {DASH} Human Doctor", "{1}{G}{G}", 3, "G", "Flash\n"
                   f"When Dr. McCoy enters, choose one {DASH}\n• Return target non-Doctor permanent card from your "
                   "graveyard to your hand.\n• Choose up to one other target creature. When it dies this turn, return "
                   "that card to the battlefield under its owner's control with a +1/+1 counter on it at the beginning "
                   "of the next end step.", ["Flash"], "3", "2"),
    "raffi": _card("Commander Raffi Musiker", f"Legendary Creature {DASH} Human Officer", "{2}{B}", 3, "B", "When "
                   f"Commander Musiker enters, choose one {DASH}\n• Exile up to one target card from a graveyard. You "
                   "gain 2 life.\n• Investigate. You lose 2 life. (Create a Clue token. It's an artifact with \"{2}, "
                   "Sacrifice this token: Draw a card.\")", [], "3", "2"),
    "lorca": _card("Gabriel Lorca, Mirror Menace", f"Legendary Creature {DASH} Human Rogue Officer", "{4}{B}", 5, "B",
                   "Menace\nWhenever you face a dilemma, you may pay {B}. If you do, return this card from your graveyard "
                   "to your hand. (You face a dilemma as you choose one or more modes for a spell or ability.)",
                   ["Menace"], "5", "4"),
    "needs": _card("The Needs of the Many", "Instant", "{1}{W}", 2, "W", "As an additional cost to cast this spell, "
                   "sacrifice a creature.\nCreatures you control gain hexproof and indestructible until end of turn. You "
                   "gain hexproof until end of turn. Prevent all damage that would be dealt to you this turn. Exile The "
                   "Needs of the Many."),
    "deevolve": _card("De-evolve", f"Enchantment {DASH} Aura", "{1}{B}", 2, "B", "Enchant creature\nEnchanted creature "
                      "gets -4/-0, can't block, and is a Salamander. (It loses all other creature types.)\nThreshold "
                      f"{DASH} At the beginning of each upkeep, if there are seven or more cards in your graveyard, "
                      "exile enchanted creature."),
    "tellme": _card("Tell Me What You See", "Enchantment", "{1}{B}", 2, "B", "When this enchantment enters, target "
                    "opponent may have you draw a card. If they don't, they lose 4 life and you surveil 1.\nWhenever you "
                    "face a dilemma, you may return this enchantment to its owner's hand. (You face a dilemma as you "
                    "choose one or more modes for a spell or ability.)"),
    "khan": _card("Khan, Vengeful Heart", f"Legendary Creature {DASH} Human Warrior", "{2}{B}{B}", 4, "B", "When Khan "
                  "enters, you may sacrifice another creature or artifact. If you do, draw two cards.\nYou may cast "
                  "this card from exile.", [], "5", "3"),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}


def make(name, cost, cmc, text="", power=None, toughness=None, type_line=f"Creature {DASH} Test", colors="R"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, [], power, toughness))[0]


BEAR = make("Bear", "{1}{G}", 2, "", "2", "2", colors="G")
OGRE = make("Ogre", "{2}{R}", 3, "", "3", "3")
GIANT = make("Giant", "{4}{R}", 5, "", "5", "5")
KLINGON = make("Klingon Brute", "{1}{B}", 2, "", "2", "2", f"Creature {DASH} Klingon Warrior", "B")
RELIC = make("Relic", "{3}", 3, "{T}: You gain 1 life.", type_line="Artifact", colors="")
MURDER = make("Murder", "{1}{B}{B}", 3, "Destroy target creature.", type_line="Instant", colors="B")
EXILE = make("Banish", "{1}{W}{W}", 3, "Exile target creature.", type_line="Instant", colors="W")
WIPE = make("Wipe", "{3}{W}", 4, "Destroy all creatures.", type_line="Sorcery", colors="W")
TOKEN = make("Officer", "", 0, "", "1", "1", f"Creature {DASH} Officer")._replace(is_token=True)


def player(name="Wir"):
    p = bt.Player(name, [PLAINS] * 30, mulligan=False)
    p.hand, p.library = [], [PLAINS] * 20
    return p


def pair():
    me, opp = player(), player("Gegner")
    me.opponent, opp.opponent = opp, me
    return me, opp


def entry():
    return {"face": 0, "events": [], "deaths": [], "main1": [], "main2": [], "land": ""}


def put(p, card, entered=0):
    c = bt.Creature(card, entered)
    c.gy, c.ctl = p.graveyard, p
    p.creatures.append(c)
    return c


def open_lines(key):
    return [l for _c, _m, l in analyze_card(RAW[key])]


class ParseTests(unittest.TestCase):
    def test_fields(self):
        self.assertTrue(C["gowron"].sac_trample_draw)
        self.assertEqual(C["kirk"].self_sac_destroy, cost_alternatives("{2}"))
        self.assertTrue(C["dahar"].dahar_sac)
        self.assertTrue(C["targ"].targ_sac)
        self.assertTrue(C["mccoy"].mccoy_save)
        self.assertEqual([bool(s.bones_return) for s in C["bones"].choices[1]], [True, False])
        self.assertEqual([bool(s.bones_protect) for s in C["bones"].choices[1]], [False, True])
        self.assertEqual([s.etb_clue for s in C["raffi"].choices[1]], [0, 1])
        self.assertTrue(C["raffi"].choices[1][0].gy_hate)
        self.assertEqual(C["lorca"].lorca_return, cost_alternatives("{B}"))
        self.assertTrue(C["needs"].needs_many)
        self.assertTrue(C["deevolve"].threshold_exile)
        self.assertEqual(C["tellme"].tell_me, (4, 1))
        self.assertTrue(C["tellme"].dilemma_bounce_self)
        self.assertTrue(C["khan"].cast_from_exile)
        self.assertTrue(EXILE.exile_removal)
        self.assertFalse(MURDER.exile_removal)

    def test_coverage(self):
        for key in RAW:
            self.assertEqual(open_lines(key), [], key)


class SacrificeTests(unittest.TestCase):
    def test_gowron_klingon_draws(self):
        me, _opp = pair()
        gowron = put(me, C["gowron"])
        k = put(me, KLINGON)
        self.assertTrue(bt.sacrifice_for(me, k, entry()))
        self.assertEqual((k.dead, gowron.has("trample"), len(me.hand), me.life), (True, True, 1, 19))
        bear = put(me, BEAR)
        self.assertTrue(bt.sacrifice_for(me, bear, entry()))
        self.assertEqual((len(me.hand), me.life), (1, 19))

    def test_kirk_dies_anyway(self):
        me, opp = pair()
        kirk = put(me, C["kirk"])
        me.open = [("R",)] * 2
        self.assertFalse(bt.sacrifice_for(me, kirk, entry()))  # kein Ziel beim Gegner
        opp.perms.append(RELIC)
        self.assertTrue(bt.sacrifice_for(me, kirk, entry()))
        self.assertEqual((kirk.dead, opp.perms, opp.graveyard, me.open), (True, [], [RELIC], []))

    def test_dahar_master(self):
        me, opp = pair()
        me.clues = 1
        bear = put(opp, BEAR)
        put(me, C["dahar"], 3)
        bt.card_effects(me, opp, C["dahar"], 3, entry())
        bt.bury((me, opp), entry())
        self.assertEqual((me.clues, bear in opp.creatures), (0, False))

    def test_dahar_without_fodder_or_target(self):
        me, opp = pair()
        put(opp, BEAR)
        bt.card_effects(me, opp, C["dahar"], 3, entry())
        self.assertEqual((opp.creatures[0].damage, opp.life), (0, 20))
        opp.creatures[:] = [bt.Creature(GIANT, 0)]
        me.clues = 1
        bt.card_effects(me, opp, C["dahar"], 3, entry())
        self.assertEqual((me.clues, opp.life), (1, 20))  # nichts zu toeten, kein Lethal: nicht opfern

    def test_targ_wrangler(self):
        me, opp = pair()
        targ = put(me, C["targ"])
        me.clues = 1
        bt.end_step_triggers(me, opp, entry())
        self.assertEqual(me.clues, 1)
        targ.attacked = me.now
        bt.end_step_triggers(me, opp, entry())
        self.assertEqual(me.clues, 0)


class McCoyTests(unittest.TestCase):
    def test_surly_saves_from_damage_and_destroy(self):
        me, opp = pair()
        put(me, C["mccoy"])
        bear, ogre = put(me, BEAR), put(me, OGRE)
        bear.bonus, bear.damage = 1, 5
        ogre.damage = 3
        bt.bury((me,), entry())
        self.assertIn(bear, me.creatures)
        self.assertEqual((bear.bonus, bear.damage, ogre in me.creatures), (0, 0, False))
        bear.bonus = 1
        bt.cast_removal(MURDER, opp, me, entry(), 3, target=bear)
        self.assertEqual((bear in me.creatures, bear.bonus), (True, 0))

    def test_bones_return_mode(self):
        me, opp = pair()
        me.graveyard = [OGRE, C["mccoy"]]  # Doctor nicht
        put(me, C["bones"], 3)
        bt.card_effects(me, opp, C["bones"], 3, entry())
        self.assertEqual((me.hand, me.graveyard), ([OGRE], [C["mccoy"]]))

    def test_bones_protect_mode(self):
        me, opp = pair()
        put(me, C["bones"], 3)
        ogre = put(me, OGRE)
        bt.card_effects(me, opp, C["bones"].choices[1][1], 3, entry())
        ogre.dead = True
        bt.bury((me,), entry())
        self.assertEqual(me.graveyard, [OGRE])
        bt.end_step_triggers(me, opp, entry())
        back = [c for c in me.creatures if c.card == OGRE]
        self.assertEqual((len(back), back[0].bonus if back else None, me.graveyard), (1, 1, []))


class RaffiLorcaTests(unittest.TestCase):
    def test_raffi_investigates(self):
        me, opp = pair()
        put(me, C["raffi"], 3)
        bt.card_effects(me, opp, C["raffi"], 3, entry())
        self.assertEqual((me.clues, me.life), (1, 18))

    def test_raffi_low_life(self):
        me, opp = pair()
        put(me, C["raffi"], 3)
        me.life = 3
        opp.graveyard = [PLAINS, GIANT]
        bt.card_effects(me, opp, C["raffi"], 3, entry())
        self.assertEqual((me.clues, me.life, opp.graveyard), (0, 5, [PLAINS]))

    def test_lorca_returns_on_dilemma(self):
        me, _opp = pair()
        me.graveyard = [C["lorca"]]
        me.open = [("B",)]
        bt.face_dilemma(me, 3, entry())
        self.assertEqual((me.hand, me.graveyard, me.open), ([C["lorca"]], [], []))


class NeedsTests(unittest.TestCase):
    def test_against_sweeper(self):
        me, opp = pair()
        tok, ogre = put(me, TOKEN), put(me, OGRE)
        me.hand, me.open = [C["needs"]], [("W",)] * 2
        bt.cast_removal(WIPE, opp, me, entry(), 3)
        self.assertEqual(([c.card.name for c in me.creatures], me.hand, me.graveyard), (["Ogre"], [], []))
        self.assertTrue(tok.dead)

    def test_against_lethal_attack(self):
        me, opp = pair()
        put(me, BEAR)
        attackers = [put(opp, GIANT), put(opp, GIANT)]
        me.life = 5
        me.hand, me.open = [C["needs"]], [("W",)] * 2
        bt.respond_to_attack(me, opp, attackers, entry(), 3)
        bt.deal_noncombat(opp, me, 3, entry())
        self.assertEqual((me.life, me.hand, me.creatures), (5, [], []))

    def test_not_without_reason(self):
        me, opp = pair()
        put(me, BEAR)
        attackers = [put(opp, OGRE)]
        me.hand, me.open = [C["needs"]], [("W",)] * 2
        bt.respond_to_attack(me, opp, attackers, entry(), 3)
        self.assertEqual(me.hand, [C["needs"]])


class TellMeDeevolveTests(unittest.TestCase):
    def test_tell_me(self):
        me, opp = pair()
        bt.card_effects(me, opp, C["tellme"], 3, entry())
        self.assertEqual((opp.life, len(me.hand)), (16, 0))
        opp.life = 8
        bt.card_effects(me, opp, C["tellme"], 3, entry())
        self.assertEqual((opp.life, len(me.hand)), (8, 1))

    def test_tell_me_returns_on_dilemma(self):
        me, _opp = pair()
        me.perms.append(C["tellme"])
        bt.face_dilemma(me, 3, entry())
        self.assertEqual((me.perms, me.hand), ([], [C["tellme"]]))

    def test_deevolve_threshold(self):
        me, opp = pair()
        giant = put(opp, GIANT)
        me.perms.append(C["deevolve"])
        bt.cast_removal(C["deevolve"], me, opp, entry(), 3, target=giant)
        self.assertTrue(giant.locked)
        bt.upkeep_triggers(me, opp, 5, entry())
        self.assertIn(giant, opp.creatures)
        me.graveyard = [PLAINS] * 7
        bt.upkeep_triggers(opp, me, 6, entry())  # "each upkeep": auch im Zug des Gegners
        self.assertNotIn(giant, opp.creatures)
        self.assertEqual((opp.graveyard, me.perms, C["deevolve"] in me.graveyard), ([], [], True))


class KhanExileTests(unittest.TestCase):
    def test_exile_removal_puts_khan_into_exile_castable(self):
        me, opp = pair()
        khan = put(me, C["khan"])
        bt.cast_removal(EXILE, opp, me, entry(), 3, target=khan)
        self.assertEqual((khan in me.creatures, me.graveyard), (False, []))
        self.assertIn(C["khan"], [c for c, _last in me.impulse])
        me.own_turns = 50
        bt.expire_impulse(me)
        self.assertIn(C["khan"], [c for c, _last in me.impulse])

    def test_exile_removal_other_creature(self):
        me, opp = pair()
        bear = put(me, BEAR)
        bt.cast_removal(EXILE, opp, me, entry(), 3, target=bear)
        self.assertEqual((me.creatures, me.graveyard, me.impulse), ([], [], []))

    def test_finality_and_expired_impulse(self):
        me, _opp = pair()
        khan = put(me, C["khan"])
        khan.finality, khan.dead = True, True
        bt.bury((me,), entry())
        self.assertEqual([c for c, _l in me.impulse], [C["khan"]])
        me.impulse = [(C["khan"], 1), (BEAR, 1)]
        me.own_turns = 2
        bt.expire_impulse(me)
        self.assertEqual([c for c, _l in me.impulse], [C["khan"]])


if __name__ == "__main__":
    unittest.main()
