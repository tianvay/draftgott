"""B1: Removal gegen Nichtkreatur-Permanents und Exil "until this leaves the battlefield" (610.3).
Memory Trap / Solitary Cell: die gefaehrlichste Kreatur, sonst ein Nichtkreatur-Permanent; verlaesst die Falle das
Spielfeld, kommt die Karte unter der Kontrolle ihres Besitzers zurueck (610.3c) als neues Objekt (400.7), ein Token
nicht (111.8). Nichtkreatur-Ziele: 1. Falle mit unserer Karte, 2. Lock-Aura auf unserer Kreatur, 3. Splinter Twin
oder Ausruestung an einer gegnerischen Kreatur, 4. sonstige Verzauberungen/Artefakte (Way of ... vor anderen, dann
Manawert), nie Token. Budding Insurgent opfert sich nur fuer Rang 1-3; Archive Arbiter zerstoert bei Rang 1-4, sonst
4 Leben; Clash of Elements wie Plan for All Outcomes (oben mit 2 Schaden); Vraska ab 6 Laendern; Living Library mit 6
offenem Mana; Echoverse Fulcrum, wenn die gegnerischen Kreaturen mindestens doppelt so viel wert sind."""
import unittest

from components import battle as bt
from components.cards import card_info
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
CRE = f"Creature {DASH} Test"
PLAINS = W["Plains"]


def make(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="W"):
    return card_info(_card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness))[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


FOREST = land("Forest", "G")
BEAR = W["Test Bear"]
OGRE = make("Ogre", CRE, "{2}{R}", 3, "", "3", "3", colors="R")
TITAN = make("Titan", CRE, "{4}{G}", 5, "", "5", "5", colors="G")
CADET = BEAR._replace(name="Cadet", is_token=True)

TRAP = make("Memory Trap", "Enchantment", "{2}{W}", 3, "When this enchantment enters, exile target nonland permanent "
            "an opponent controls until this enchantment leaves the battlefield.")
CELL = make("Solitary Cell", "Artifact", "{R}{W}", 2, "When this artifact enters, exile target nonland permanent an "
            "opponent controls with mana value 3 or less until this artifact leaves the battlefield.\n{1}, {T}, "
            "Discard a legendary card: Draw a card.")
INSURGENT = make("Budding Insurgent", f"Creature {DASH} Dryad Scout", "{2}{G}", 3, "Vigilance\nSacrifice this "
                 "creature: Destroy target artifact or enchantment. If that permanent was a legendary enchantment, "
                 "draw a card. Activate only as a sorcery.", "3", "3", ["Vigilance"], "G")
ARBITER = make("Archive Arbiter", f"Artifact Creature {DASH} Sphinx", "{6}", 6, "Flying\nWhen this creature enters, "
               "choose one —\n• Destroy target noncreature, nonland permanent.\n• You gain 4 life.", "4", "4",
               ["Flying"], "")
CLASH = make("Clash of Elements", "Instant", "{1}{U}{R}", 3, "Choose target nonland permanent. Its owner may put it on "
             "top of their library. If they do, Clash of Elements deals 2 damage to them. If they didn't put the card "
             "on top of their library, they put it on the bottom.", colors="U")
VRASKA = make("Vraska, the Cutting Glare", f"Legendary Creature {DASH} Gorgon Assassin", "{B}{B}{G}", 3, "Deathtouch\n"
              "When Vraska enters, if you control six or more lands, destroy target permanent an opponent controls. "
              "They create a Treasure token.", "3", "3", ["Deathtouch"], "B")
LIBRARY = make("Living Library", f"Artifact Creature {DASH} Book Illusion", "{2}", 2, "{6}, Sacrifice this creature: "
               "Choose target creature or planeswalker an opponent controls. Its owner shuffles it into their library.",
               "1", "1", colors="")
FULCRUM = make("The Echoverse Fulcrum", "Legendary Artifact", "{2}", 2, "When The Echoverse Fulcrum enters, draw a "
               "card, then discard a card.\n{5}, {T}, Exile The Echoverse Fulcrum: Destroy all creatures. Activate only "
               "as a sorcery.", colors="")
WAY = make("Way of the Healer", "Legendary Enchantment", "{3}{W}", 4, "When Way of the Healer enters, empower Jace 5.\n"
           "Planeswalkers you control have \"[−2]: Create a 2/2 colorless Wizard Soldier creature token named Cadet. "
           "Surveil 1.\"")
SHACKLE = make("Royal Shackle", f"Legendary Enchantment {DASH} Aura", "{1}{W}", 2, "Enchant creature\nEnchanted "
               "creature can't attack or block.")
TWIN = make("Splinter Twin", f"Enchantment {DASH} Aura", "{2}{R}{R}", 4, "Enchant creature\nEnchanted creature has "
            "\"{T}: Create a token that's a copy of this creature, except it has haste. Exile that token at the "
            "beginning of the next end step.\"", colors="R")
HEART = card_info(_card("Heartwood", "Token Artifact", text="{T}: Add {R} or {G}."))[0]._replace(is_token=True)


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
        self.assertTrue(TRAP.exile_until and CELL.exile_until)
        self.assertEqual(CELL.removal[2], (("mv_le", 3),))
        self.assertEqual(INSURGENT.sac_perm_removal, "artifact_enchantment")
        self.assertEqual(ARBITER.choices[1][0].perm_destroy, "noncreature")
        self.assertEqual((CLASH.removal[0], CLASH.tuck_top_damage), ("tuck", 2))
        self.assertEqual((VRASKA.etb_lands_needed, VRASKA.victim_treasure), (6, 1))
        self.assertEqual((LIBRARY.sac_removal[1][0], LIBRARY.sac_removal[0]), ("shuffle", ((6, ()),)))
        self.assertEqual(FULCRUM.sweep_ability, ((5, ()),))


class TrapTests(unittest.TestCase):
    def test_exile_and_return(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        bear.bonus = 2
        bt._resolve(opp, me, TRAP, 3, entry())
        self.assertEqual((me.creatures, me.graveyard, me.deaths), ([], [], 0))
        on_board(me, INSURGENT)
        me.lands = [FOREST]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((TRAP in opp.perms, TRAP in opp.graveyard), (False, True))
        back = [c for c in me.creatures if c.card.name == "Test Bear"]
        self.assertEqual(len(back), 1)
        self.assertEqual((back[0].bonus, back[0].entered), (0, 5))  # neues Objekt (400.7)

    def test_returning_creature_enters_again(self):
        me, opp = pair()
        oculus = make("Oculus", CRE, "{2}{U}", 3, "When this creature enters, empower Jace 2.", "2", "2", colors="U")
        on_board(me, oculus)
        bt._resolve(opp, me, TRAP, 3, entry())
        bt.destroy_permanent(opp, TRAP, entry())
        self.assertEqual(me.jace.loyalty, 2)  # 400.7: neues Objekt, Betreten-Effekt wirkt

    def test_exiled_token_does_not_return(self):
        me, opp = pair()
        on_board(me, CADET)
        bt._resolve(opp, me, TRAP, 3, entry())
        self.assertEqual(opp.trap_links, [])  # 111.8: das Token existiert nicht mehr
        bt.destroy_permanent(opp, TRAP, entry())
        self.assertEqual(me.creatures, [])

    def test_noncreature_target_when_no_creature(self):
        me, opp = pair()
        me.perms = [WAY]
        bt._resolve(opp, me, TRAP, 3, entry())
        self.assertEqual(me.perms, [])
        bt.destroy_permanent(opp, opp.trap_links[0], entry())
        self.assertEqual((me.perms, me.jace.loyalty), ([WAY], 5))  # kommt zurueck und loest erneut aus

    def test_cell_only_small_creatures(self):
        me, opp = pair()
        titan, ogre = on_board(me, TITAN), on_board(me, OGRE)
        bt._resolve(opp, me, CELL, 3, entry())
        self.assertEqual((titan in me.creatures, ogre in me.creatures), (True, False))


class TargetOrderTests(unittest.TestCase):
    def test_insurgent_frees_our_creature_first(self):
        me, opp = pair()
        on_board(me, BEAR)
        bt._resolve(opp, me, TRAP, 3, entry())
        opp.perms.append(WAY)
        on_board(me, INSURGENT)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((TRAP in opp.perms, WAY in opp.perms), (False, True))

    def test_insurgent_destroys_lock_aura_and_draws_for_legendary(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        opp.hand, opp.lands = [SHACKLE], [PLAINS] * 2
        bt._resolve(opp, me, SHACKLE, 3, entry())
        self.assertTrue(bear.locked)
        on_board(me, INSURGENT)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((bear.locked, SHACKLE in opp.graveyard, len(me.library)), (False, True, 19))

    def test_insurgent_destroys_twin_on_their_creature(self):
        me, opp = pair()
        ogre = on_board(opp, OGRE)
        opp.perms.append(TWIN)
        ogre.auras.append(TWIN)
        on_board(me, INSURGENT)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((ogre.auras, TWIN in opp.perms), ([], False))

    def test_insurgent_keeps_itself_for_a_plain_enchantment(self):
        me, opp = pair()
        opp.perms = [WAY, HEART]
        ins = on_board(me, INSURGENT)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((ins in me.creatures, opp.perms), (True, [WAY, HEART]))

    def test_arbiter_destroys_a_way_otherwise_gains_life(self):
        me, opp = pair()
        opp.perms = [WAY, HEART]
        bt._resolve(me, opp, ARBITER, 3, entry())
        self.assertEqual((opp.perms, me.life), ([HEART], 20))
        me2, opp2 = pair()
        opp2.perms = [HEART]
        bt._resolve(me2, opp2, ARBITER, 3, entry())
        self.assertEqual((opp2.perms, me2.life), ([HEART], 24))

    def test_way_before_a_more_expensive_enchantment(self):
        me, opp = pair()
        big = make("Grand Enchantment", "Enchantment", "{4}{W}{W}", 6, "")
        opp.perms = [big, WAY]
        bt._resolve(me, opp, ARBITER, 3, entry())
        self.assertEqual(opp.perms, [big])

    def test_lock_aura_goes_when_its_creature_leaves(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        bt._resolve(opp, me, SHACKLE, 3, entry())
        bear.dead = True
        bt.bury((me, opp), entry())
        self.assertEqual((SHACKLE in opp.perms, SHACKLE in opp.graveyard), (False, True))


class OtherRemovalTests(unittest.TestCase):
    def test_clash_top_with_damage_or_bottom(self):
        me, opp = pair()
        on_board(opp, OGRE)
        opp.lands = [PLAINS] * 2
        bt._resolve(me, opp, CLASH, 3, entry())
        self.assertEqual((opp.library[0], opp.life), (OGRE, 18))
        me, opp = pair()
        on_board(opp, TITAN)
        bt._resolve(me, opp, CLASH, 3, entry())
        self.assertEqual((opp.library[-1], opp.life), (TITAN, 20))

    def test_vraska_needs_six_lands(self):
        me, opp = pair()
        titan = on_board(opp, TITAN)
        me.lands = [FOREST] * 5
        bt._resolve(me, opp, VRASKA, 3, entry())
        self.assertIn(titan, opp.creatures)
        me, opp = pair()
        titan = on_board(opp, TITAN)
        me.lands = [FOREST] * 6
        bt._resolve(me, opp, VRASKA, 3, entry())
        self.assertEqual((titan in opp.creatures, opp.treasures), (False, 1))

    def test_living_library_shuffles_away(self):
        me, opp = pair()
        on_board(me, LIBRARY)
        titan = on_board(opp, TITAN)
        me.open = [("G",)] * 6
        bt.end_step_instants(me, opp, entry(), 6)
        self.assertEqual((titan in opp.creatures, TITAN in opp.library, LIBRARY in me.graveyard), (False, True, True))

    def test_fulcrum_when_they_are_much_stronger(self):
        me, opp = pair()
        me.perms, me.lands = [FULCRUM], [FOREST] * 5
        on_board(me, BEAR)
        on_board(opp, TITAN)
        on_board(opp, OGRE)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual((me.creatures, opp.creatures, FULCRUM in me.perms, FULCRUM in me.graveyard),
                         ([], [], False, False))

    def test_no_fulcrum_when_even(self):
        me, opp = pair()
        me.perms, me.lands = [FULCRUM], [FOREST] * 5
        on_board(me, OGRE)
        on_board(opp, OGRE)
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertIn(FULCRUM, me.perms)


if __name__ == "__main__":
    unittest.main()
