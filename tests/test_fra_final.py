"""FRA-Abschluss: keine Karte des Sets erscheint mehr als "nicht modelliert". Winter, Tam und Extrapolate the
Impossible sind bewusst nicht vollstaendig modelliert (Nutzer-Entscheidung); Campus Crier (Empower aus dem Friedhof,
jetzt auch im Goldfish) und Jace, Reality Sculptor (+1 nach Islands) wirken; Empower X von Repurposed Enforcer (auch im
Goldfish), Overwrite the Multiverse, Violent Echoes und Jace, Reality Sculptor wird berechnet."""
import unittest

from components import simulation as sim
from components.cards import card_info
from components.coverage import analyze_card
from components.jace import JaceState, analyze_jace
from components.mana import land_key
from tests.test_package_fra_f import CRIER, ECHOES_SC, ENFORCER, OVERWRITE_SC, SCULPTOR, sc

DASH = "—"
WINTER = sc("Winter, Team Player", f"Legendary Creature {DASH} Human Warrior", "Convoke\nWhenever you cast a "
            "noncreature spell, creatures you control get +1/+0 until end of turn.", cost="{4}{R}", keywords=["Convoke"])
TAM = sc("Tam, the Possibility", f"Legendary Creature {DASH} Gorgon Wizard", "Planeswalker spells you cast cost {1} "
         "less to cast.\n{W}{U}{B}{R}{G}, {T}: Proliferate X times, where X is the number of planeswalker types among "
         "planeswalkers you control.", cost="{1}{G}{U}")
EXTRAPOLATE = sc("Extrapolate the Impossible", "Sorcery", "You may reveal exactly two cards you own with different names "
                 "from outside the game. An opponent chooses one of them. You put that card into your hand.",
                 cost="{1}{B}", power=None, toughness=None)
X_OTHER = sc("Odd Scholar", f"Creature {DASH} Human", "Whenever this creature attacks, empower Jace X, where X is the "
             "number of cards in your hand.")


def rows(*dicts):
    return [(d["name"], 1, card_info(d)[0], d["name"]) for d in dicts]


class CoverageTests(unittest.TestCase):
    def test_on_purpose(self):
        for card in (WINTER, TAM, EXTRAPOLATE):
            self.assertEqual(analyze_card(card), [], card["name"])


class JaceSectionTests(unittest.TestCase):
    def test_no_unmodelled_jace_cards(self):
        ja = analyze_jace(rows(CRIER, SCULPTOR, ENFORCER, OVERWRITE_SC, ECHOES_SC))
        self.assertEqual(ja["unmodeled"], [])

    def test_x_only_when_not_computed(self):
        ja = analyze_jace(rows(SCULPTOR, ENFORCER, OVERWRITE_SC, ECHOES_SC, X_OTHER))
        self.assertEqual(ja["x_cards"], ["Odd Scholar"])


class GoldfishTests(unittest.TestCase):
    def test_crier_from_the_graveyard(self):
        crier = card_info(CRIER)[0]
        gy, jst = [crier], JaceState()
        paid = sim.goldfish_gy_empower(gy, [], land_key([("G",)]), jst)
        self.assertEqual((gy, jst.loyalty, len(paid)), ([], 2, 1))

    def test_crier_needs_mana(self):
        crier = card_info(CRIER)[0]
        gy, jst = [crier], JaceState()
        sim.goldfish_gy_empower(gy, [], land_key([]), jst)
        self.assertEqual((gy, jst.loyalty), ([crier], 0))

    def test_enforcer_x_is_our_creatures(self):
        enforcer = card_info(ENFORCER)[0]
        ef = next(e for e in enforcer.empower if e[1] == "trigger")
        self.assertEqual(sim.attack_empower(ef, 3), 3)
        self.assertEqual(sim.attack_empower((0, "trigger", 2, "attack", (), False, False, False), 3), 2)


if __name__ == "__main__":
    unittest.main()
