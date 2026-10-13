"""Karten-Kennzeichen aus Scryfall-Daten: Typen, Kartenfluss (Draw/Search/Surveil/Scry/Explore/Mill) und Farben.
Gemeinsam genutzt vom Drafthelper (Seitenleiste) und vom Bericht."""
import re


def type_kinds(type_line):
    """Typ-Kennzeichen einer Karte fuer die Uebersicht links (nur die Vorderseite zaehlt). Artefakte und
    Verzauberungen zaehlen ohne Kreaturen und Laender; ein Nicht-Standardland ist 'land' und 'nonbasic_land'."""
    types = (type_line or "").split(" // ")[0].split("\u2014")[0]
    creature, land = "Creature" in types, "Land" in types
    kinds = []
    if creature:
        kinds.append("creature")
    for word in ("Instant", "Sorcery"):
        if word in types:
            kinds.append(word.lower())
    if land:
        kinds.append("land")
        if "Basic" not in types:
            kinds.append("nonbasic_land")
    if "Artifact" in types and not creature and not land:
        kinds.append("artifact")
    if "Enchantment" in types and not creature and not land:
        kinds.append("enchantment")
    if "Planeswalker" in types:
        kinds.append("planeswalker")
    return kinds


FLOW_ORDER = ("draw", "search", "surveil", "scry", "explore", "mill_self", "mill_opp")
# Auslöser, die nur auf Ziehen/Scry/Surveil/Mill reagieren, sind selbst kein Kartenfluss
_FLOW_TRIGGERS = re.compile(
    r"\b(whenever|each time|when) (you|a player|an opponent|each player) "
    r"(scry|surveil|draw|mill|scries|surveils|draws|mills)[^,.\n]*|\bif you would (draw|mill)[^,.\n]*|"
    r"\b(if|as long as) you('ve| have) (scried|surveilled|drawn|milled)[^,.\n]*")
# Mill: "mill 3" (ohne Subjekt) trifft den eigenen Spieler; "target player/each player" kann beide treffen
_MILL_SELF = re.compile(r"(?<!opponent )(?<!player )\bmill (\d+|x|a|an|one|two|three|four|five|six|seven|eight|"
                        r"that many|half|cards?)\b|\byou mill\b|\bput the top [^.]*? of your library into your "
                        r"graveyard")
_MILL_OPP = re.compile(r"\b(target|each|an) opponent mills\b|\btarget opponent puts the top\b")
_MILL_BOTH = re.compile(r"\b(target|each) player mills\b|\b(target|each) player puts the top [^.]*? of their "
                        r"library into their graveyard")
_FLOW_PATTERNS = {
    "draw": re.compile(r"(?<!opponent )\bdraws? (a|an|one|two|three|four|five|six|seven|x|\d+|that many|up to|cards?)\b"),
    "search": re.compile(r"\bsearch your library\b"),
    "surveil": re.compile(r"\bsurveil\b"),
    "scry": re.compile(r"\bscry\b"),
    "explore": re.compile(r"\bexplores?\b"),
}


def flow_kinds(card):
    """Arten von Kartenfluss, die eine Karte liefert (nach FLOW_ORDER): draw, search, surveil, scry, explore.
    Erkannt wird aus dem Kartentext (ohne Erinnerungstext); Cycling und Landcycling ueber die Schluesselwoerter."""
    faces = card.get("card_faces") or [card]
    text = " ".join(re.sub(r"\([^)]*\)", " ", f.get("oracle_text") or "") for f in faces).lower()
    text = _FLOW_TRIGGERS.sub(" ", text)
    found = {k for k, pattern in _FLOW_PATTERNS.items() if pattern.search(text)}
    if _MILL_SELF.search(text):
        found.add("mill_self")
    if _MILL_OPP.search(text):
        found.add("mill_opp")
    if _MILL_BOTH.search(text):
        found |= {"mill_self", "mill_opp"}
    keywords = {k.lower() for k in card.get("keywords") or []}
    if any("landcycling" in k or "typecycling" in k for k in keywords):
        found.add("search")
    elif "cycling" in keywords:
        found.add("draw")
    return [k for k in FLOW_ORDER if k in found]


WUBRG = "WUBRG"


def card_colors(card):
    """Farben einer Scryfall-Karte (bei zweiseitigen Karten die Vorderseite)."""
    faces = card.get("card_faces") or []
    return list(card.get("colors") or (faces[0].get("colors") if faces else None) or [])


def empower_points(effects):
    """Loyalty, die Empower Jace beim Wirken oder Betreten sofort bringt (ohne X und ohne wiederkehrende Ausloeser)."""
    return sum(e[2] for e in effects if e[1] in ("spell", "etb") and not e[6])


def color_curve(items, mode, buckets=8):
    """Mana-Kurve nach Farben. items: [{colors, mv, land, qty}] (nur Nichtland-Karten zaehlen).
    mode 'stacked': mehrfarbige Karten bilden ein eigenes Segment 'M' (jede Karte einmal);
    mode 'percolor': eine mehrfarbige Karte zaehlt bei jeder ihrer Farben.
    Gibt {buckets, keys, pairs, total, multi, colorless, max} zurueck (wie colorCurve in der Seite)."""
    keys = ["W", "U", "B", "R", "G", "M", "C"] if mode == "stacked" else ["W", "U", "B", "R", "G", "C"]
    out = [{k: 0 for k in keys} for _ in range(buckets)]
    pairs, total, multi, colorless = {}, 0, 0, 0
    for it in items:
        if it.get("land"):
            continue
        qty = it.get("qty", 1)
        i = min(int((it.get("mv") or 0) + 0.5), buckets - 1)  # wie Math.round (halbe Werte aufrunden)
        cols = sorted((c for c in it.get("colors") or [] if c in WUBRG), key=WUBRG.index)
        total += qty
        if not cols:
            out[i]["C"] += qty
            colorless += qty
        elif len(cols) == 1:
            out[i][cols[0]] += qty
        else:
            multi += qty
            key = "/".join(cols)
            pairs[key] = pairs.get(key, 0) + qty
            if mode == "stacked":
                out[i]["M"] += qty
            else:
                for c in cols:
                    out[i][c] += qty
    height = (lambda b: sum(b.values())) if mode == "stacked" else (lambda b: max(b.values()))
    return {"buckets": out, "keys": keys, "pairs": pairs, "total": total, "multi": multi, "colorless": colorless,
            "max": max([1] + [height(b) for b in out])}
