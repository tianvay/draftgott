"""Grundlagen fuer kommende Sets, Teil 2: Ausruestung. "Equipped creature has ..." auch ohne +P/+T (Hexproof,
Unblockbar, Ward), Anlegen beim Betreten (auch an ein neues Token), Equipment-Token beim Betreten einer Kreatur,
Equip nur fuer einen Kreaturtyp und Schluesselwoerter fuer ausgeruestete Angreifer. Kartentexte aus HOB und MSH."""
import unittest

from components import battle as bt
from components.cards import card_info
from components.coverage import analyze_card
from tests.fixtures_walkers import CARDS as W, _card

DASH = "—"
EQ = f"Artifact {DASH} Equipment"
PLAINS = W["Plains"]
BEAR = W["Test Bear"]


def raw(name, type_line, cost, cmc, text, power=None, toughness=None, keywords=(), colors="W"):
    return _card(name, type_line, cost, cmc, colors, text, list(keywords), power, toughness)


def make(*args, **kwargs):
    return card_info(raw(*args, **kwargs))[0]


def land(name, color):
    return card_info(_card(name, f"Basic Land {DASH} {name}", text=f"({{T}}: Add {{{color}}}.)",
                           produced=[color]))[0]


MOUNTAIN = land("Mountain", "R")

RAW = {
    "mattock": raw("Dwarven Mattock", EQ, "{2}", 2,
                   "When this Equipment enters, attach it to target Dwarf you control.\nEquipped creature gets +2/+2 "
                   "and has ward {1}. (Whenever equipped creature becomes the target of a spell or ability an opponent "
                   "controls, counter it unless that player pays {1}.)\nEquip {3} ({3}: Attach to target creature you "
                   "control. Equip only as a sorcery.)", keywords=["Equip"], colors=""),
    "harness": raw("Falcon's Wing Harness", EQ, "{1}{U}", 2,
                   "When this Equipment enters, attach it to target creature you control.\nEquipped creature gets "
                   "+1/+1 and has flying and ward {1}. (Whenever equipped creature becomes the target of a spell or "
                   "ability an opponent controls, counter it unless that player pays {1}.)\nEquip {2}{U} ({2}{U}: "
                   "Attach to target creature you control. Equip only as a sorcery.)", keywords=["Equip"], colors="U"),
    "suit": raw("Super Suit", EQ, "{1}{U}", 2,
                "Flash\nWhen this Equipment enters, attach it to target creature you control. Untap that creature.\n"
                "Equipped creature gets +1/+2.\nEquip {2} ({2}: Attach to target creature you control. Equip only as "
                "a sorcery.)", keywords=["Equip", "Flash"], colors="U"),
    "stark": raw("Stolen Stark Tech", EQ, "{1}{B}", 2,
                 "Flash\nWhen this Equipment enters, attach it to target creature you control. That creature gains "
                 "indestructible until end of turn. (Damage and effects that say \"destroy\" don't destroy it.)\n"
                 "Equipped creature gets +1/+0.\nEquip {1} ({1}: Attach to target creature you control. Equip only "
                 "as a sorcery.)", keywords=["Equip", "Flash"], colors="B"),
    "blacksmith": raw("Iron Hills Blacksmith", f"Creature {DASH} Dwarf Artificer", "{1}{W}", 2,
                      "Double strike\nWhen this creature enters, create a colorless Equipment artifact token named Axe "
                      "with \"Equipped creature gets +1/+0\" and equip {2}.", "1", "1", ["Double strike"]),
    "agent": raw("U.S.Agent, John Walker", f"Legendary Creature {DASH} Human Soldier Hero", "{3}{W/B}", 4,
                 "When U.S.Agent enters, create a colorless Equipment artifact token named Sturdy Shield with "
                 "\"Equipped creature gets +1/+2\" and equip {2}. Attach it to U.S.Agent.", "3", "2", colors="WB"),
    "dain": raw("Dáin Ironfoot", f"Legendary Creature {DASH} Dwarf Warrior", "{2}{R}", 3,
                "When Dáin enters, create a colorless Equipment artifact token named Axe with \"Equipped creature "
                "gets +1/+0\" and equip {2}. When you do, attach it to target creature you control.\nWhenever Dáin "
                "attacks, each equipped attacking creature gains double strike until end of turn.", "1", "4",
                colors="R"),
    "shortsword": raw("Dwarven Shortsword", EQ, "{3}{W}", 4,
                      "When this Equipment enters, create a 2/2 red Dwarf creature token, then attach this Equipment "
                      "to it.\nEquipped creature gets +1/+2.\nEquip {2} ({2}: Attach to target creature you control. "
                      "Equip only as a sorcery.)", keywords=["Equip"]),
    "staff": raw("Test Staff", EQ, "{1}{U}", 2, "Equipped creature gets +1/+1.\nEquip Wizard {1}\nEquip {3}",
                 keywords=["Equip"], colors="U"),
    "lance": raw("Test Lance", EQ, "{1}{W}", 2, "Equipped creature gets +2/+0.\nEquip Knight {1}",
                 keywords=["Equip"]),
    "cloak": raw("Test Cloak", EQ, "{2}", 2, "Equipped creature has hexproof and can't be blocked.\nEquip {2}",
                 keywords=["Equip"], colors=""),
}
C = {k: card_info(v)[0] for k, v in RAW.items()}

DWARF = make("Dwarf Pal", f"Creature {DASH} Dwarf", "{R}", 1, "", "2", "2", colors="R")
WIZARD = make("Wizard Pal", f"Creature {DASH} Human Wizard", "{U}", 1, "", "1", "1", colors="U")
OGRE = make("Ogre", f"Creature {DASH} Ogre", "{2}{R}", 3, "", "3", "3", colors="R")
KILL = make("Murder", "Instant", "{1}{B}{B}", 3, "Destroy target creature.", colors="B")


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


class ParseTests(unittest.TestCase):
    def test_mattock(self):
        m = C["mattock"]
        self.assertEqual((m.equip, m.grant_ward, m.equip_etb), ((((3, ()),), 2, 2, False), 1, ((), False, "dwarf")))

    def test_harness(self):
        h = C["harness"]
        self.assertEqual((h.equip[1:], h.equip_kw, h.grant_ward, h.equip_etb),
                         ((1, 1, False), ("flying",), 1, ((), False, "")))

    def test_enter_riders(self):
        self.assertEqual(C["suit"].equip_etb, ((), True, ""))
        self.assertEqual(C["stark"].equip_etb, (("indestructible",), False, ""))

    def test_equipment_tokens(self):
        token, attach = C["blacksmith"].equip_token
        self.assertEqual((token.name, token.is_token, token.is_artifact, token.equip, attach),
                         ("Axe", True, True, (((2, ()),), 1, 0, False), ""))
        self.assertEqual(C["agent"].equip_token[0].equip[1:3], (1, 2))
        self.assertEqual(C["agent"].equip_token[1], "self")
        self.assertEqual(C["dain"].equip_token[1], "target")

    def test_equipped_attackers_gain(self):
        self.assertEqual(C["dain"].equipped_attack_kw, ("double strike",))

    def test_attach_to_new_token(self):
        self.assertEqual(C["shortsword"].equip_etb, ((), False, "token"))
        carrier = C["shortsword"].equip_carrier
        self.assertEqual((carrier.name, carrier.power, carrier.toughness), ("Dwarf", 2, 2))

    def test_typed_equip(self):
        s = C["staff"]
        self.assertEqual((s.equip, s.equip_typed), ((((3, ()),), 1, 1, False), ("wizard", ((1, ()),))))

    def test_has_only(self):
        c = C["cloak"]
        self.assertEqual((c.equip, c.equip_kw), ((((2, ()),), 0, 0, False), ("hexproof", "unblockable")))


class AttachTests(unittest.TestCase):
    def test_attach_on_enter_with_ward(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        bt._resolve(me, opp, C["harness"], 3, entry())
        self.assertIn(C["harness"], bear.gear)
        self.assertTrue(bear.has("flying"))
        self.assertEqual(bt.ward_of(bear), ("mana", 1))
        opp.open = []
        self.assertIsNone(bt.choose_target(KILL.removal, opp, me))

    def test_attach_untaps(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        bear.tapped = True
        bt._resolve(me, opp, C["suit"], 3, entry())
        self.assertEqual((bear.tapped, bear.toughness), (False, 4))

    def test_attach_grants_indestructible(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        bt._resolve(me, opp, C["stark"], 3, entry())
        self.assertTrue(bear.has("indestructible"))

    def test_attach_only_to_dwarf(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        bt._resolve(me, opp, C["mattock"], 3, entry())
        self.assertEqual(bear.gear, [])
        dwarf = on_board(me, DWARF)
        mattock2 = C["mattock"]._replace(name="Mattock 2")
        bt._resolve(me, opp, mattock2, 3, entry())
        self.assertIn(mattock2, dwarf.gear)

    def test_token_then_attach(self):
        me, opp = pair()
        bt._resolve(me, opp, C["shortsword"], 3, entry())
        token = next(c for c in me.creatures if c.card.is_token)
        self.assertEqual((token.gear, token.power, token.toughness), ([C["shortsword"]], 3, 4))

    def test_cloak_unblockable(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        bear.gear.append(C["cloak"])
        ogre = on_board(opp, OGRE)
        self.assertFalse(bt.can_block(ogre, bear))
        self.assertTrue(bt.hexproof(bear))


class TokenTests(unittest.TestCase):
    def test_axe_token_is_equipped_later(self):
        me, opp = pair()
        bt._resolve(me, opp, C["blacksmith"], 3, entry())
        axe = next(p for p in me.perms if p.name == "Axe")
        self.assertTrue(axe.is_token)
        smith = me.creatures[0]
        self.assertEqual(smith.gear, [])
        me.lands = [MOUNTAIN] * 2
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(smith.gear, [axe])

    def test_attach_to_itself(self):
        me, opp = pair()
        bt._resolve(me, opp, C["agent"], 3, entry())
        agent = me.creatures[0]
        self.assertEqual((agent.power, agent.toughness), (4, 4))

    def test_attach_to_target(self):
        me, opp = pair()
        ogre = on_board(me, OGRE)
        bt._resolve(me, opp, C["dain"], 3, entry())
        self.assertEqual(ogre.power, 4)

    def test_equipped_attackers_double_strike(self):
        me, opp = pair()
        bt._resolve(me, opp, C["dain"], 3, entry())
        e = bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(e["damage"], 4)  # Dain 2/4 mit Axe und Double Strike

    def test_token_equipment_vanishes(self):
        me, opp = pair()
        bt._resolve(me, opp, C["blacksmith"], 3, entry())
        axe = next(p for p in me.perms if p.name == "Axe")
        bt.destroy_permanent(me, axe, entry())
        self.assertNotIn(axe, me.graveyard)


class TypedEquipTests(unittest.TestCase):
    def test_cheap_equip_for_wizard(self):
        me, opp = pair()
        wiz = on_board(me, WIZARD)
        me.perms, me.lands = [C["staff"]], [MOUNTAIN]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(wiz.gear, [C["staff"]])

    def test_typed_only_parse(self):
        lance = C["lance"]
        self.assertEqual((lance.equip, lance.equip_typed), ((((1, ()),), 2, 0, False), ("knight", ((1, ()),), True)))

    def test_typed_only_not_for_others(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        me.perms, me.lands = [C["lance"]], [MOUNTAIN] * 3
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(bear.gear, [])

    def test_typed_only_for_its_type(self):
        me, opp = pair()
        knight = on_board(me, make("Knight Pal", f"Creature {DASH} Human Knight", "{W}", 1, "", "2", "2"))
        me.perms, me.lands = [C["lance"]], [MOUNTAIN]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(knight.gear, [C["lance"]])

    def test_no_cheap_equip_for_others(self):
        me, opp = pair()
        bear = on_board(me, BEAR)
        me.perms, me.lands = [C["staff"]], [MOUNTAIN]
        bt.take_turn(me, opp, 5, 3, skip_draw=True)
        self.assertEqual(bear.gear, [])


class CoverageTests(unittest.TestCase):
    def test_lines_are_modelled(self):
        for key in RAW:
            self.assertEqual([line for _c, _m, line in analyze_card(RAW[key])], [], key)


if __name__ == "__main__":
    unittest.main()
