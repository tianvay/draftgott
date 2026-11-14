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
import re
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


# Was ein Trick braucht, um zu zaehlen (Nutzer 14.11.2026), je Satz des Kartentexts (ohne Erinnerungstext):
#   "own": braucht eine eigene Kreatur des Gegners (Pump, Schutz, Auren, Blinken, Beissen)
#   "always": wirkt auf Kampf oder Spielfeld (Schaden, Zerstoeren, Tappen, Kontern, -X/-X, Zurueckschicken ...)
#   "none": ohne Kampfwirkung (Karten ziehen, abwerfen, Surveil, Scry, Mill, Lebenspunkte, Friedhof, Bibliothek oben)
# Unbekannte Saetze zaehlen als "always", damit nichts Wichtiges verschwindet. Flash-Kreaturen sind immer "always"
# (ueberraschender Blocker). Opfern einer Kreatur als Zusatzkosten macht die ganze Karte "own".
_IGNORE_RE = re.compile(r"^(kicker\b|this spell costs\b|flash$|choose (one|two|three|up to)\b.*—$|"
                        r"as an additional cost\b|exile cardname$)")
_OWN_RE = re.compile(r"creatures? you control|gets \+|gains? (first strike|double strike|trample|hexproof|"
                     r"indestructible|flying|lifelink|vigilance|deathtouch|menace|reach|protection)|"
                     r"\+1/\+1 counter on (it|target creature)|^untap it$|enchant creature|enchanted creature|"
                     r"return that card to the battlefield|can't be blocked")
_ALWAYS_RE = re.compile(r"damage|destroy|counter target|\btap\b|-\d+/-\d+|-x/-x|return target|exile target "
                        r"(creature|artifact|enchantment|permanent|nonland|attacking|blocking)|sacrifices?\b|"
                        r"can't (block|attack)|of their library|of its owner's library|their choice of the top|"
                        r"phases? out|fights?\b|create")
_NONE_RE = re.compile(r"\bdraws?\b|\bdiscards?\b|\bsurveil\b|\bscry\b|\bmill\b|exile the top|play those cards|"
                      r"gains? \d+ life|loses? \d+ life|into (your|their) hand|exile target card from a graveyard|"
                      r"first spell you've cast|look at the top")
_SAC_COST_RE = re.compile(r"as an additional cost to cast this spell, sacrifice an? (creature|artifact or creature)")


def _sentences(text, name):
    text = re.sub(r"\([^)]*\)", "", text or "")
    for short in {name, name.split(",")[0]} - {""}:
        text = text.replace(short, "CARDNAME")
    for line in text.split("\n"):
        line = re.sub(r"^•\s*(?:[^—.•]{1,40}—\s*)?", "", line.strip())
        for part in re.split(r"(?<=[.!])\s+", line):
            part = part.strip().rstrip(".").strip().lower()
            if part:
                yield part


def trick_need(sc):
    """"always", "own" oder "none" fuer eine Scryfall-Karte (siehe oben)."""
    front = _front(sc)
    type_line = (front.get("type_line") or sc.get("type_line") or "").split(" // ")[0]
    if "Creature" in type_line.split("—")[0]:
        return "always"
    text = front.get("oracle_text") or sc.get("oracle_text") or ""
    if _SAC_COST_RE.search(text.lower()):
        return "own"
    kinds = set()
    for s in _sentences(text, sc.get("name") or ""):
        if _IGNORE_RE.search(s):
            continue
        kinds.add("own" if _OWN_RE.search(s) else "always" if _ALWAYS_RE.search(s) else
                  "none" if _NONE_RE.search(s) else "always")
    if not kinds:
        return "always"
    return "always" if "always" in kinds else ("own" if "own" in kinds else "none")


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
        type_line = (front.get("type_line") or sc.get("type_line") or "").split(" // ")[0]
        power, tough = front.get("power", sc.get("power")), front.get("toughness", sc.get("toughness"))
        out.append({"name": sc["name"], "cost": cost, "mv": int(mv), "colors": [c for c in ORDER if c in colors],
                    "flash": "Instant" not in (front.get("type_line") or sc.get("type_line") or ""),
                    "removal": (removal_info(sc) or {}).get("points", 0),
                    "type": type_line, "text": front.get("oracle_text") or sc.get("oracle_text") or "",
                    "pt": f"{power}/{tough}" if power is not None and tough is not None else "",
                    "need": trick_need(sc)})
    return out


def _land_colors(land, card_of):
    basics = {BASIC_TYPES[s] for s in land["subtypes"] if s in BASIC_TYPES}
    if basics:
        return basics
    card = card_of(land["grp"]) or {}
    return set(card.get("produces") or []) or {"C"}


def _sort(cards):
    return sorted(cards, key=lambda c: (c["mv"], c["name"]))


def tricks_view(game, card_of, tricks, relevant_only=False):
    """Anzeige fuer Seite und Seitenfenster (siehe Modulbeschreibung); card_of(grp): Kartenangaben (card_summary)
    oder None. relevant_only (Live-Draft): "now" ohne Tricks ohne Kampfwirkung und, solange der Gegner keine Kreatur
    hat, ohne Tricks, die eine eigene Kreatur brauchen; "next" nur ohne Tricks ohne Kampfwirkung; "hidden" zaehlt,
    was in "now" deshalb fehlt."""
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
    hand = game.opponent_hand_size()
    if hand == 0:  # ohne Handkarten keine Tricks (Nutzer 14.11.2026)
        now, nxt = [], []
    creatures = game.opponent_creatures()
    extra = {"creatures": creatures}
    if relevant_only:  # Nutzer 14.11.2026: nur Tricks, die zaehlen
        hidden = {"none": sum(1 for t in now if t.get("need") == "none"),
                  "own": sum(1 for t in now if t.get("need") == "own") if not creatures else 0}
        now = [t for t in now if t.get("need") != "none" and (creatures or t.get("need") != "own")]
        nxt = [t for t in nxt if t.get("need") != "none"]
        extra["hidden"] = hidden
    return {**extra, "open": len(untapped), "lands": len(lands), "hand": hand,
            "colors": {c: colors_open[c] for c in ORDER if colors_open[c]},
            "spell_colors": [c for c in ORDER if c in spell_colors],
            "now": _sort(now), "next": _sort(nxt)}
