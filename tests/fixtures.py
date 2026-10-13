"""Kleine, erfundene Scryfall-Kartendaten fuer die Tests (kein Netzwerkzugriff noetig)."""
import argparse

DASH = "—"


def _land(name, color, subtype):
    return {"name": name, "type_line": f"Basic Land {DASH} {subtype}", "mana_cost": "", "cmc": 0.0, "colors": [],
            "oracle_text": f"({{T}}: Add {{{color}}}.)", "keywords": [], "layout": "normal",
            "produced_mana": [color], "image_uris": {"normal": f"https://img.test/normal/{name}.jpg"}}


def _spell(name, cost, cmc, colors, type_line="Creature " + DASH + " Test", power=None, toughness=None,
           keywords=(), text=""):
    return {"name": name, "type_line": type_line, "mana_cost": cost, "cmc": float(cmc), "colors": list(colors),
            "oracle_text": text, "keywords": list(keywords), "layout": "normal", "power": power,
            "toughness": toughness, "image_uris": {"normal": f"https://img.test/normal/{name}.jpg"}}


CARDS = {c["name"]: c for c in [
    _land("Plains", "W", "Plains"), _land("Island", "U", "Island"), _land("Swamp", "B", "Swamp"),
    _land("Mountain", "R", "Mountain"), _land("Forest", "G", "Forest"),
    _spell("Test Bear", "{W}", 1, "W", power="2", toughness="2"),
    _spell("Test Hasty", "{R}", 1, "R", power="3", toughness="1", keywords=["Haste"]),
    _spell("Test Defender", "{W}", 1, "W", power="3", toughness="3", keywords=["Defender"]),
    _spell("Test Big", "{3}{W}{W}", 5, "W", power="5", toughness="5"),
    _spell("Test Gold", "{W}{B}", 2, "WB", power="2", toughness="2"),
    _spell("Test Spell", "{W}", 1, "W", type_line="Instant", text="Draw a card."),
]}

# 17 Laender + 23 Zauber: gemischtes Testdeck fuer die Simulation
MIXED_DECK = {"Plains": 9, "Mountain": 6, "Swamp": 2, "Test Bear": 6, "Test Hasty": 4, "Test Defender": 2,
              "Test Big": 3, "Test Spell": 4, "Test Gold": 4}

POOL_TEXT = """Deck
4 Plains (TST) 1
2 Mountain (TST) 4
3 Test Bear (TST) 10
2 Test Hasty (TST) 11
1 Test Big (TST) 13
1 Test Gold (TST) 14

Sideboard
2 Test Defender (TST) 12
1 Swamp (TST) 3
1 Test Spell (TST) 15
"""


def args_for(argv=None):
    """Kommandozeilen-Argumente wie im echten Programm, mit kleinen Standardwerten fuer schnelle Tests."""
    from components.cli import parse_args
    return parse_args(list(argv if argv is not None else ["deck.txt"]) + ["--sims", "200", "--seed", "7",
                                                                           "--nicht-oeffnen"])


def namespace(**kw):
    return argparse.Namespace(**kw)
