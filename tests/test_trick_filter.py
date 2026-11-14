"""Trick-Warner zeigt nur Tricks, die zaehlen (Nutzer 14.11.2026): Tricks ohne Wirkung auf Kampf oder Spielfeld
(Karten ziehen, Surveil, Mill, Lebenspunkte, Friedhof) fallen weg; Tricks, die eine eigene Kreatur des Gegners
brauchen (Pump, Schutz, Auren, Opfern als Zusatzkosten), nur wenn er Kreaturen auf dem Feld hat."""
import pathlib
import tempfile
import unittest

from components import gamestate as gs
from components import livedraft as ld
from components import overlay
from components import tricks
from tests.i18n_check import english, german_leftovers
from tests.test_gamestate import ALL, NAMES, START, feed, gre, state, zone
from tests.test_tricks import BOARD, land, sc, spell

# Texte nach Karten aus TRK (gekuerzt, wo es nicht darauf ankommt)
CARDS = {
    "Draw": sc("Draw", "Instant", "{1}{G}", "G", "Mill four cards. You may put a permanent card from among them into "
               "your hand. If this spell is the first spell you've cast this game, you gain 2 life. (To mill four "
               "cards, put the top four cards of your library into your graveyard.)"),
    "Pump": sc("Pump", "Instant", "{B}", "B", "Target creature gets +2/+0 until end of turn. When that creature dies "
               "this turn, you draw a card."),
    "Shield": sc("Shield", "Instant", "{1}{W}", "W", "Target artifact or creature you control gains hexproof and "
                 "indestructible until end of turn. If it's a creature, put a +1/+1 counter on it. (It can't be the "
                 "target of spells or abilities your opponents control.)"),
    "Team": sc("Team", "Instant", "{2}{R}", "R", "This spell costs {2} less to cast if a creature is attacking you.\n"
               "Creatures you control get +2/+0 until end of turn."),
    "Doctor": sc("Doctor", "Instant", "{G}", "G", "Put a +1/+1 counter on target creature you control. Untap it. Until "
                 "end of turn, it gets +1/+1 and becomes a Doctor. (It loses all other creature types.)"),
    "Blink": sc("Blink", "Instant", "{1}{U}", "U", "Choose one —\n• Power to Engines — Surveil 2, then draw a card.\n"
                "• Power to Life Support — Exile target creature you control. Return that card to the battlefield "
                "under its owner's control at the beginning of the next end step."),
    "Klingon": sc("Klingon", "Instant", "{1}{R}", "R", "Choose one —\n• I Am Klingon — Target Klingon gets +1/+1 and "
                  "gains double strike until end of turn.\n• I Am Starfleet — Discard a card. If you do, draw two "
                  "cards."),
    "Sac": sc("Sac", "Instant", "{1}{W}", "W", "As an additional cost to cast this spell, sacrifice a creature.\n"
              "Creatures you control gain hexproof and indestructible until end of turn. You gain hexproof until end "
              "of turn. Prevent all damage that would be dealt to you this turn. Exile Sac."),
    "Aura": sc("Aura", "Enchantment — Aura", "{1}{R}", "R", "Flash\nEnchant creature\nWhen this Aura enters, enchanted "
               "creature gains first strike until end of turn.\nEnchanted creature gets +2/+0.", ["Flash"]),
    "Kill": sc("Kill", "Instant", "{3}{B}", "B", "Destroy target creature. Surveil 1. (Look at the top card of your "
               "library. You may put it into your graveyard.)"),
    "Stun": sc("Stun", "Instant", "{W}", "W", "Choose one —\n• Stun — Tap target creature and put a stun counter on it."
               " (If a permanent with a stun counter would become untapped, remove one from it instead.)\n• Kill — "
               "This spell deals 3 damage to target attacking creature."),
    "Counter": sc("Counter", "Instant", "{1}{U}", "U", "Kicker {1}{U} (You may pay an additional {1}{U} as you cast "
                  "this spell.)\nCounter target spell with mana value 2 or less. If this spell was kicked, instead "
                  "counter target spell."),
    "Shrink": sc("Shrink", "Instant", "{1}{B}", "B", "Kicker—Sacrifice an artifact or creature. (You may sacrifice an "
                 "artifact or creature in addition to any other costs as you cast this spell.)\nTarget creature gets "
                 "-2/-2 until end of turn. If this spell was kicked, that creature gets -6/-6 until end of turn "
                 "instead."),
    "Choice": sc("Choice", "Instant", "{2}{B}", "B", "Choose one —\n• Surgical Separation — Destroy target creature. Its "
                 "controller creates two 1/1 red Officer creature tokens.\n• Remain Fused — You draw two cards and "
                 "each player loses 2 life."),
    "Relic": sc("Relic", "Instant", "{1}{R}", "R", "Choose one —\n• Use the Relic — Target creature gets +3/+2 until end "
                "of turn.\n• Destroy the Relic — Destroy target artifact."),
    "Loot Bear": sc("Loot Bear", "Creature — Talosian Advisor", "{1}{U}", "U", "Flash\nWhen this creature enters, draw a "
                    "card, then discard a card.", ["Flash"]),
    "Bite": sc("Bite", "Instant", "{1}{G}", "G", "Target creature you control deals damage equal to its power to target "
               "creature you don't control."),
    "Plain": sc("Plain", "Instant", "{W}", "W", ""),
}
NEED = {"Draw": "none", "Pump": "own", "Shield": "own", "Team": "own", "Doctor": "own", "Blink": "own",
        "Klingon": "own", "Sac": "own", "Aura": "own", "Kill": "always", "Stun": "always", "Counter": "always",
        "Shrink": "always", "Choice": "always", "Relic": "always", "Loot Bear": "always", "Bite": "own",
        "Plain": "always"}


class NeedTests(unittest.TestCase):
    def test_need_of_each_trick(self):
        for name, card in CARDS.items():
            with self.subTest(name):
                self.assertEqual(tricks.trick_need(card), NEED[name])

    def test_trick_cards_carry_the_need(self):
        by = {c["name"]: c for c in tricks.trick_cards(list(CARDS.values()))}
        self.assertEqual(by["Draw"]["need"], "none")
        self.assertEqual(by["Kill"]["need"], "always")


CREATURE = gre(state(zones=[zone(28, "ZoneType_Battlefield", None, [61, 62, 63, 64, 80])],
                     objects=[land(61, 501, "SubType_Plains", False), land(62, 502, "SubType_Mountain", True),
                              land(63, 503, "SubType_Forest", False), land(64, 301, "SubType_Plains", False, owner=2),
                              spell(80, 905, "Green", zid=28)]))
MINE = gre(state(zones=[zone(28, "ZoneType_Battlefield", None, [61, 62, 63, 64, 81])],
                 objects=[dict(spell(81, 906, "White", zid=28, owner=2), controllerSeatId=2)]))
SET = [sc("W1", "Instant", "{W}", "W", "Target creature gets +2/+2 until end of turn."),
       sc("W2", "Instant", "{W}", "W", "Destroy target attacking creature."),
       sc("W3", "Instant", "{W}", "W", "You gain 4 life. Draw a card.")]


def view(*lines):
    return tricks.tricks_view(feed(gs.GameState(), *START, *lines), lambda grp: None, tricks.trick_cards(SET),
                              relevant_only=True)


class OpponentCreatureTests(unittest.TestCase):
    def test_counts_only_opponent_creatures_on_the_battlefield(self):
        self.assertEqual(feed(gs.GameState(), *START, BOARD).opponent_creatures(), 0)
        self.assertEqual(feed(gs.GameState(), *START, CREATURE).opponent_creatures(), 1)
        self.assertEqual(feed(gs.GameState(), *START, BOARD, MINE).opponent_creatures(), 0)  # eigene zaehlt nicht


class FilterTests(unittest.TestCase):
    def test_without_opponent_creatures_only_tricks_that_need_none(self):
        v = view(BOARD)
        self.assertEqual([c["name"] for c in v["now"]], ["W2"])
        self.assertEqual(v["creatures"], 0)
        self.assertEqual(v["hidden"], {"none": 1, "own": 1})

    def test_with_opponent_creature_pumps_are_back(self):
        v = view(CREATURE)
        self.assertEqual([c["name"] for c in v["now"]], ["W1", "W2"])
        self.assertEqual(v["hidden"], {"none": 1, "own": 0})

    def test_without_filter_everything_as_before(self):
        v = tricks.tricks_view(feed(gs.GameState(), *START, BOARD), lambda grp: None, tricks.trick_cards(SET))
        self.assertEqual([c["name"] for c in v["now"]], ["W1", "W2", "W3"])

    def test_next_turn_drops_only_irrelevant_tricks(self):
        sets = [sc("W1", "Instant", "{1}{W}", "W", "Target creature gets +2/+2 until end of turn."),
                sc("W3", "Instant", "{1}{W}", "W", "You gain 4 life.")]
        g = feed(gs.GameState(), *START, BOARD)
        v = tricks.tricks_view(g, lambda grp: None, tricks.trick_cards(sets), relevant_only=True)
        self.assertEqual([c["name"] for c in v["now"]], [])
        self.assertEqual([c["name"] for c in v["next"]], [])  # +2/+2 kostet 2, ist aber jetzt schon bezahlbar
        self.assertEqual(v["hidden"], {"none": 1, "own": 1})


class LiveTests(unittest.TestCase):
    def test_snapshot_filters_tricks(self):
        with tempfile.TemporaryDirectory() as d:
            log = pathlib.Path(d) / "Player.log"
            log.write_text("\n".join(START + [BOARD]) + "\n", encoding="utf-8")
            live = ld.LiveDraft(log, pathlib.Path(d) / "pool.txt", names=NAMES, fetch=lambda n, refresh=False: ALL,
                                fetch_set=lambda code: SET)
            live.step()
            tr = live.snapshot({}, {}, None)["game"]["tricks"]
            self.assertEqual([c["name"] for c in tr["now"]], ["W2"])


TR = {"open": 2, "lands": 3, "colors": {"W": 2}, "spell_colors": [], "hand": 3, "creatures": 0,
      "hidden": {"none": 2, "own": 1}, "now": [{"name": "W2", "cost": "{W}", "removal": 2.0}], "next": []}


class OverlayTests(unittest.TestCase):
    def test_hidden_line(self):
        rows = overlay.trick_rows(TR)
        self.assertEqual(rows[-1], ("Ausgeblendet: 2 ohne Kampfwirkung · 1 braucht eigene Kreatur (Gegner hat keine)",
                                    "sub"))

    def test_hidden_line_plural_and_parts(self):
        self.assertEqual(overlay.trick_rows(dict(TR, hidden={"none": 0, "own": 3}))[-1][0],
                         "Ausgeblendet: 3 brauchen eigene Kreatur (Gegner hat keine)")
        self.assertEqual(overlay.trick_rows(dict(TR, hidden={"none": 1, "own": 0}))[-1][0],
                         "Ausgeblendet: 1 ohne Kampfwirkung")

    def test_no_hidden_line_without_hidden_tricks(self):
        for tr in (dict(TR, hidden={"none": 0, "own": 0}), {k: v for k, v in TR.items() if k != "hidden"}):
            self.assertFalse(any(line.startswith("Ausgeblendet") for line, _ in overlay.trick_rows(tr)))

    def test_no_hidden_line_without_hand_cards(self):
        self.assertFalse(any(line.startswith("Ausgeblendet") for line, _ in overlay.trick_rows(dict(TR, hand=0))))

    def test_english(self):
        with english():
            text = "\n".join(r[0] for r in overlay.trick_rows(TR) + overlay.trick_rows(
                dict(TR, hidden={"none": 1, "own": 3})))
        self.assertEqual(german_leftovers(text), [])
        self.assertIn("Hidden: 2 without combat effect · 1 needs own creature (opponent has none)", text)


class HelpTests(unittest.TestCase):
    def test_help_explains_the_filter(self):
        from components.howitworks import render_help_page
        self.assertIn("ohne Kampfwirkung", render_help_page())


if __name__ == "__main__":
    unittest.main()
