"""Deck-Vorschlag des Drafthelpers: ordnet Karten anhand ihrer Kategorie den Gruppen zu und fuellt mit Filler auf.

Regeln:
    MustPlay    -> Core
    Splashworthy-> Splash
    NeverPlay   -> Aus
    Filler      -> fuellt auf die Zielgroesse (alle Laender zaehlen mit):
                   zuerst Core, damit beide Varianten gleich gross werden, dann die NoSplash-Gruppe als Ersatz
                   fuer die Splash-Karten; uebrige Filler -> Aus
    ohne Kategorie bleibt die Zuordnung unveraendert.

Reihenfolge der Filler: nach der gewaehlten Sortierung der Seite, dann Farben, die schon im Deck sind (Farblos zaehlt
als vorhanden), dann Manawert aufsteigend.
"""

GROUPS = ("core", "splash", "nosplash")
MARK_ORDER = ("core", "splash", "nosplash", "off")
COLOR_ORDER = ("W", "U", "B", "R", "G", "M", "C", "L")


def _row_key(card):
    if card.get("land"):
        return "L"
    colors = card.get("colors") or []
    return "C" if not colors else ("M" if len(colors) > 1 else colors[0])


def _primary(card, prev_mark, sort):
    if sort == "name":
        return (card["name"].lower(),)
    if sort == "color":
        return (COLOR_ORDER.index(_row_key(card)),)
    if sort == "mark":
        return (MARK_ORDER.index(prev_mark) if prev_mark in MARK_ORDER else len(MARK_ORDER),)
    if sort == "cat":
        return (0,)
    return (1 if card.get("land") else 0, card.get("mv") or 0)  # "mv" und unbekannte Werte


def suggest(cards, marks, basics, cats, target=40, sort="mv"):
    """cards: Pool-Karten (name, qty, colors, mv, land); marks: je Karte eine Liste mit einer Markierung je Kopie;
    basics: {Landname: {core, splash, nosplash}}; cats: {Kartenname: Kategorie}.
    Gibt {"marks": neue Markierungen, "summary": {...}} zurueck. Die Eingaben werden nicht veraendert."""
    new = [list(ms) for ms in marks]
    fillers = []  # (Kartenindex, Kopie, bisherige Markierung)
    assigned = {"core": 0, "splash": 0, "off": 0}
    for ci, card in enumerate(cards):
        cat = cats.get(card["name"])
        qty = card["qty"]
        if cat == "mustplay":
            new[ci], assigned["core"] = ["core"] * qty, assigned["core"] + qty
        elif cat == "splashworthy":
            new[ci], assigned["splash"] = ["splash"] * qty, assigned["splash"] + qty
        elif cat == "neverplay":
            new[ci], assigned["off"] = ["off"] * qty, assigned["off"] + qty
        elif cat == "filler":
            for k in range(qty):
                fillers.append((ci, k, marks[ci][k]))
                new[ci][k] = "off"

    def sizes():
        total = {g: sum(ms.count(g) for ms in new) + sum((b or {}).get(g, 0) for b in basics.values())
                 for g in GROUPS}
        return total, total["core"] + total["splash"], total["core"] + total["nosplash"]

    _, size_s0, size_n0 = sizes()
    present = set()
    for ci, card in enumerate(cards):
        if not card.get("land") and "core" in new[ci]:
            present |= set(card.get("colors") or [])

    pool = list(fillers)
    taken = {"core": 0, "nosplash": 0}

    def take(n, group):
        nonlocal present
        for _ in range(min(n, len(pool))):
            def key(f):
                ci, k, prev = f
                c = cards[ci]
                missing = 0 if c.get("land") else len(set(c.get("colors") or []) - present)
                return (_primary(c, prev, sort), missing, c.get("mv") or 0, c["name"].lower(), k)
            best = min(pool, key=key)
            pool.remove(best)
            ci, k, _ = best
            new[ci][k] = group
            taken[group] += 1
            if group == "core" and not cards[ci].get("land"):
                present |= set(cards[ci].get("colors") or [])

    take(max(0, target - max(size_s0, size_n0)), "core")
    _, size_s1, size_n1 = sizes()
    take(max(0, target - size_n1), "nosplash")
    total, size_s, size_n = sizes()

    warnings = []
    if max(size_s0, size_n0) > target:
        warnings.append(f"Eine Variante hat schon {max(size_s0, size_n0)} Karten und liegt über dem Ziel von {target}.")
    if size_s < target or size_n < target:
        warnings.append(f"Nicht genug Filler: Splash-Variante {size_s} und NoSplash-Variante {size_n} Karten, "
                        f"Ziel {target}.")
    return {"marks": new, "summary": {
        "target": target, "sizes": {"splash": size_s, "nosplash": size_n}, "assigned": assigned,
        "filler": {"core": taken["core"], "nosplash": taken["nosplash"], "off": len(pool)},
        "warnings": warnings}}


# ----------------------------------------------------------------------------------------------------------------
# Deckvorschlag als eigenes Deck (unabhaengig von der Zuordnung Core/Splash/NoSplash)
# ----------------------------------------------------------------------------------------------------------------
import math
import re

WUBRG = "WUBRG"
BASIC_FOR_COLOR = {"W": "Plains", "U": "Island", "B": "Swamp", "R": "Mountain", "G": "Forest"}
SPLASH_SOURCES = 3  # Standardlaender je Splash-Farbe


def land_range(target):
    """Faustregel fuer die Laenderzahl: 40 Karten 15 bis 17, 60 Karten 20 bis 24 (dazwischen und darueber linear).
    Gibt (niedrig, hoch, empfohlen) zurueck; empfohlen ist 17 bei 40 und 22 bei 60 Karten."""
    low = round(15 + 0.25 * (target - 40))
    high = max(low, round(17 + 0.35 * (target - 40)))
    rec = min(max(round(17 + 0.25 * (target - 40)), low), high)
    return low, high, rec


def _pips(card):
    """Farbsymbole der Karte je Farbe (Hybrid zaehlt anteilig); ohne Kostenangabe zaehlt jede Farbe einmal."""
    out = {}
    for sym in re.findall(r"\{([^}]+)\}", card.get("cost") or ""):
        parts = sym.split("/")
        letters = [p for p in parts if p in WUBRG]
        weight = 0.5 if parts[-1] == "P" else 1.0
        for letter in letters:
            out[letter] = out.get(letter, 0.0) + weight / len(letters)
    if not out:
        for c in card.get("colors") or []:
            if c in WUBRG:
                out[c] = out.get(c, 0.0) + 1.0
    return out


def _distribute(n, weights, chosen, splash_colors):
    """Verteilt n Standardlaender: je Splash-Farbe bis zu 3 (hoechstens ein Drittel), der Rest nach Farbgewicht."""
    alloc = {}
    if n <= 0:
        return alloc
    sc = [c for c in WUBRG if c in splash_colors]
    if sc:
        for j in range(min(SPLASH_SOURCES * len(sc), n // 3)):
            c = sc[j % len(sc)]
            alloc[c] = alloc.get(c, 0) + 1
    rest = n - sum(alloc.values())
    w = {c: weights.get(c, 0.0) for c in WUBRG if c in chosen and weights.get(c, 0.0) > 0}
    if not w:  # keine Farbsymbole: gleichmaessig auf die gewaehlten Farben
        w = {c: 1.0 for c in WUBRG if c in chosen}
    total = sum(w.values())
    if rest <= 0 or total <= 0:
        return alloc
    quota = {c: rest * v / total for c, v in w.items()}
    base = {c: int(math.floor(q)) for c, q in quota.items()}
    left = rest - sum(base.values())
    order = sorted(quota, key=lambda c: (-(quota[c] - base[c]), WUBRG.index(c)))
    for c in order[:left]:
        base[c] += 1
    for c, k in base.items():
        if k:
            alloc[c] = alloc.get(c, 0) + k
    return alloc


def propose(cards, marks, cats, colors, target=40, sort="mv"):
    """Baut ein eigenes Deck aus den Kategorien: MustPlay und Filler nur in den gewaehlten Farben, Splashworthy auch
    ausserhalb (dann als Splash), NeverPlay und Karten ohne Kategorie nicht. Standardlaender werden passend zur
    Faustregel ergaenzt und nach Farbsymbolen verteilt, Nicht-Standardlaender zaehlen als Laender.
    Gibt {"deck": {Name: Anzahl}, "summary": {...}} zurueck; die Eingaben werden nicht veraendert."""
    chosen = {c for c in colors if c in WUBRG}
    by_name = {c["name"]: c for c in cards}

    def in_colors(card):
        return set(card.get("colors") or []) <= chosen

    deck, splash_cards, fillers, ignored = {}, {}, [], 0
    for ci, card in enumerate(cards):
        cat, qty, name = cats.get(card["name"]), card["qty"], card["name"]
        if cat is None:
            ignored += qty
        elif cat == "mustplay" and in_colors(card):
            deck[name] = deck.get(name, 0) + qty
        elif cat == "splashworthy":
            deck[name] = deck.get(name, 0) + qty
            if not in_colors(card):
                splash_cards[name] = splash_cards.get(name, 0) + qty
        elif cat == "filler" and in_colors(card):
            fillers += [(ci, k, marks[ci][k]) for k in range(qty)]

    low, high, rec = land_range(target)
    nonbasic = sum(q for n, q in deck.items() if by_name[n].get("land"))
    basics_needed = max(0, rec - nonbasic)
    free = target - sum(deck.values()) - basics_needed
    present = set()
    for n in deck:
        if n not in splash_cards and not by_name[n].get("land"):
            present |= set(by_name[n].get("colors") or [])

    pool, taken = list(fillers), 0
    while pool:
        def key(f):
            ci, k, prev = f
            c = cards[ci]
            missing = 0 if c.get("land") else len(set(c.get("colors") or []) - present)
            return (_primary(c, prev, sort), missing, c.get("mv") or 0, c["name"].lower(), k)
        best = min(pool, key=key)
        ci = best[0]
        c = cards[ci]
        if c.get("land") and basics_needed > 0:
            basics_needed -= 1  # Nicht-Standardland ersetzt ein Standardland
        elif free > 0:
            free -= 1
        else:
            break
        pool.remove(best)
        taken += 1
        deck[c["name"]] = deck.get(c["name"], 0) + 1
        if c.get("land"):
            nonbasic += 1
        else:
            present |= set(c.get("colors") or [])

    weights = {}
    for n in deck:
        card = by_name[n]
        if n in splash_cards or card.get("land"):
            continue
        for letter, w in _pips(card).items():
            if letter in chosen:
                weights[letter] = weights.get(letter, 0.0) + w * deck[n]
    splash_colors = set()
    for n in splash_cards:
        splash_colors |= {c for c in by_name[n].get("colors") or [] if c in WUBRG} - chosen
    alloc = _distribute(basics_needed, weights, chosen, splash_colors)
    basics = {BASIC_FOR_COLOR[c]: k for c, k in alloc.items() if k}
    deck.update(basics)

    lands = nonbasic + sum(basics.values())
    size = sum(deck.values())
    hints, warnings = [], []
    if lands < low or lands > high:
        hints.append(f"Länder: {lands} (Faustregel bei {target} Karten: {low} bis {high}).")
    if size < target:
        warnings.append(f"Nicht genug Filler: Der Deckvorschlag hat {size} statt {target} Karten.")
    return {"deck": deck, "summary": {
        "target": target, "size": size, "lands": lands, "land_range": [low, high], "splash_cards": splash_cards,
        "ignored": ignored, "fillers": taken, "basics": basics, "colors": sorted(chosen), "hints": hints,
        "warnings": warnings}}
