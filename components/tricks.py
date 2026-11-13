"""Im Spiel (Live-Draft): Tricks bei offenem Mana des Gegners.

Aus dem Spielzustand (components/gamestate.py) kommen die Laender des Gegners mit ihrem Zustand (getappt oder nicht).
Die ungetappten Laender ergeben sein offenes Mana; je Land die Farben, die es erzeugt (Standardland-Typen aus dem
Spielzustand, sonst Scryfall ueber land_produced). Andere Manaquellen (Kreaturen, Treasure) zaehlen nicht, ebenso
wenig aktivierbare Faehigkeiten auf dem Feld.

Tricks = alle Instants und Karten mit Flash des Sets (keine Laender), die mit diesem Mana bezahlbar sind (Hybrid und
Phyrexian ueber components/mana.py, X = 0):
  - "now": mit den ungetappten Laendern jetzt
  - "next": zusaetzlich im naechsten Zug des Gegners: alle seine Laender ungetappt und ein weiteres Land in einer
    seiner Farben
Gegnerfarben: Farben der Nichtland-Karten, die er offen gezeigt hat. Sind mindestens zwei bekannt, kommen nur Tricks
in diesen Farben und den Farben seiner Standardlaender in Frage (z. B. zeigt ein Tri-Land sonst Farben, die er gar
nicht spielt). Farblose Tricks gehen immer.
"""
from collections import Counter

from components.gamestate import can_cast
from components.removal import removal_info

BASIC_TYPES = {"SubType_Plains": "W", "SubType_Island": "U", "SubType_Swamp": "B", "SubType_Mountain": "R",
               "SubType_Forest": "G"}
ORDER = "WUBRGC"


def _front(sc):
    faces = sc.get("card_faces") or []
    return faces[0] if faces else sc


def is_trick(sc):
    """Instant oder Flash auf der Vorderseite, kein Land."""
    front = _front(sc)
    type_line = (front.get("type_line") or sc.get("type_line") or "").split(" // ")[0]
    if "Land" in type_line.split("—")[0]:
        return False
    flash = "Flash" in (sc.get("keywords") or []) or "Flash" in (front.get("keywords") or [])
    return "Instant" in type_line or flash


def trick_cards(set_cards):
    """Kurzangaben aller Tricks eines Sets (Scryfall-Karten)."""
    out = []
    for sc in set_cards or []:
        if not sc.get("name") or not is_trick(sc):
            continue
        front = _front(sc)
        cost = sc.get("mana_cost") or front.get("mana_cost") or ""
        colors = sc.get("colors") or front.get("colors") or []
        mv = sc.get("cmc") or 0
        out.append({"name": sc["name"], "cost": cost, "mv": int(mv), "colors": [c for c in ORDER if c in colors],
                    "flash": "Instant" not in (front.get("type_line") or sc.get("type_line") or ""),
                    "removal": (removal_info(sc) or {}).get("points", 0)})
    return out


def _land_colors(land, card_of):
    basics = {BASIC_TYPES[s] for s in land["subtypes"] if s in BASIC_TYPES}
    if basics:
        return basics
    card = card_of(land["grp"]) or {}
    return set(card.get("produces") or []) or {"C"}


def _sort(cards):
    return sorted(cards, key=lambda c: (c["mv"], c["name"]))


def tricks_view(game, card_of, tricks):
    """Anzeige fuer Seite und Seitenfenster (siehe Modulbeschreibung); card_of(grp): Kartenangaben (card_summary)
    oder None."""
    lands = game.opponent_lands()
    sets = [(_land_colors(x, card_of), x) for x in lands]
    untapped = [s for s, x in sets if not x["tapped"]]
    spell_colors = game.opponent_spell_colors()
    allowed = None
    if len(spell_colors) >= 2:
        basics = {BASIC_TYPES[t] for x in lands for t in x["subtypes"] if t in BASIC_TYPES}
        allowed = spell_colors | basics
    colors_open = Counter()
    for s in untapped:
        for c in s:
            colors_open[c] += 1
    known = {c for s, _ in sets for c in s if c != "C"} | spell_colors
    if allowed is not None:
        known &= allowed
    possible = [t for t in tricks if allowed is None or set(t["colors"]) <= allowed]
    now = [t for t in possible if untapped and can_cast(t["cost"], untapped)]
    names = {t["name"] for t in now}
    nxt = []
    if known:
        all_lands = [s for s, _ in sets] + [known]
        nxt = [t for t in possible if t["name"] not in names and can_cast(t["cost"], all_lands)]
    return {"open": len(untapped), "lands": len(lands),
            "colors": {c: colors_open[c] for c in ORDER if colors_open[c]},
            "spell_colors": [c for c in ORDER if c in spell_colors],
            "now": _sort(now), "next": _sort(nxt)}
