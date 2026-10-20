"""Alchemy: benannte Karten fuer "conjure" (eine neue Karte entsteht, nicht aus dem Deck). Die Texte stammen von
Scryfall; jede Beschwoerung ist ein neues Objekt mit Card.conjured (fuer "nicht aus dem Startdeck", Actualize)."""
from components.cards import card_info

DASH = "—"


def _raw(name, type_line, cost, cmc, text, colors, power=None, toughness=None, produced=None):
    d = {"name": name, "type_line": type_line, "mana_cost": cost, "cmc": float(cmc), "colors": list(colors),
         "oracle_text": text, "keywords": [], "layout": "normal", "power": power, "toughness": toughness}
    if produced:
        d["produced_mana"] = list(produced)
    return d


CONJURE = {r["name"]: r for r in (
    _raw("Kraken Hatchling", f"Creature {DASH} Kraken", "{U}", 1, "", "U", "0", "4"),
    _raw("Mind Stone", "Artifact", "{2}", 2, "{T}: Add {C}.\n{1}, {T}, Sacrifice this artifact: Draw a card.", "",
         produced=["C"]),
    _raw("Aria of Flame", "Enchantment", "{2}{R}", 3,
         "When this enchantment enters, each opponent gains 10 life.\nWhenever you cast an instant or sorcery spell, "
         "put a verse counter on this enchantment, then it deals damage equal to the number of verse counters on it "
         "to target player or planeswalker.", "R"),
    _raw("Seed of Hope", "Instant", "{G}", 1,
         "Mill two cards. You may put a permanent card from among the milled cards into your hand. You gain 2 life.",
         "G"),
    _raw("Jace's Sentinel", f"Creature {DASH} Merfolk Warrior", "{1}{U}", 2,
         "As long as you control a Jace planeswalker, this creature gets +1/+0 and can't be blocked.", "U", "1", "3"),
)}
_CACHE = {}


def conjure(name):
    """Neue Karte mit diesem Namen (jedes Mal ein eigenes Objekt) oder None, wenn der Name unbekannt ist."""
    if name not in CONJURE:
        return None
    if name not in _CACHE:
        _CACHE[name] = card_info(CONJURE[name])[0]._replace(conjured=True)
    return _CACHE[name]._replace()
