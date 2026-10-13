"""Testkarten fuer Planeswalker-Laender, Jace und Empower (erfundene Scryfall-Daten, kein Netzwerk)."""
from components.cards import card_info

DASH = "—"


def _card(name, type_line, cost="", cmc=0, colors=(), text="", keywords=(), power=None, toughness=None, produced=None):
    d = {"name": name, "type_line": type_line, "mana_cost": cost, "cmc": float(cmc), "colors": list(colors),
         "oracle_text": text, "keywords": list(keywords), "layout": "normal", "power": power,
         "toughness": toughness}
    if produced:
        d["produced_mana"] = list(produced)
    return d


DATA = {c["name"]: c for c in [
    _card("Plains", f"Basic Land {DASH} Plains", text="({T}: Add {W}.)", produced=["W"]),
    _card("Island", f"Basic Land {DASH} Island", text="({T}: Add {U}.)", produced=["U"]),
    _card("Test Commons", "Land", text="This land enters tapped unless you control a planeswalker.\n{T}: Add {W} or {U}.",
          produced=["W", "U"]),
    _card("Test Sanctum", f"Land {DASH} Island",
          text="({T}: Add {U}.)\nAs this land enters, you may behold a Jace. If you don't, this land enters tapped.",
          produced=["U"]),
    _card("Test Empower", "Sorcery", "{W}", 1, "W", "Empower Jace 1.", ["Empower Jace"]),
    _card("Test Empower Big", "Sorcery", "{3}{W}", 4, "W", "Empower Jace 3.", ["Empower Jace"]),
    _card("Test Empower Creature", f"Creature {DASH} Test", "{1}{W}", 2, "W",
          "When this creature enters, empower Jace 2.", ["Empower Jace"], "1", "1"),
    _card("Test Bear", f"Creature {DASH} Bear", "{W}", 1, "W", power="2", toughness="2"),
    _card("Test Big", f"Creature {DASH} Test", "{3}{W}", 4, "W", power="5", toughness="5"),
    _card("Test Walker", f"Legendary Planeswalker {DASH} Ajani", "{2}{W}", 3, "W", "+1: You gain 1 life."),
    _card("Test Jace", f"Legendary Planeswalker {DASH} Jace", "{2}{U}", 3, "U", "+1: Draw a card."),
]}

CARDS = {name: card_info(raw)[0] for name, raw in DATA.items()}
