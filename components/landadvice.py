"""Land-Empfehlung: Standardlaender je Farbe (Hypergeometrie) und passende Nicht-Standardlaender aus dem Pool.

Grundlagen
    Farben des Decks: jede Farbe, deren Symbol auf irgendeiner Nichtland-Karte steht (eine Karte reicht, Hybrid zaehlt
    fuer beide Farben). Ein Nicht-Standardland passt, wenn es mindestens eine Farbe erzeugt und alle seine Farben im
    Deck vorkommen (R/G-Land in R/G/W: passt; in G/W: passt nicht).
    Puenktlich: Wahrscheinlichkeit, dass bis zur Runde = Manawert (mindestens 1) auf dem Play genug Quellen jeder Farbe
    gezogen sind (Symbole, die die Karte in jedem Zahlungsweg verlangt; Hybrid verlangt keine bestimmte Farbe).
    Gerechnet wird je Farbe hypergeometrisch, bei mehreren Farben als Produkt. Die Gesamtzahl der Laender spielt dabei
    keine Rolle (nur die Farbe).
    Verteilung: Zuerst bekommt jede Farbe, die eine Karte zwingend verlangt, mindestens 3 Quellen (Faustregel fuer
    einen Splash, wie beim Deckvorschlag; Nicht-Standardlaender zaehlen mit). Die uebrigen Standardlaender werden
    einzeln vergeben, jedes an die Farbe, die die Summe der Puenktlich-Werte aller Karten am staerksten erhoeht.
"""
from functools import lru_cache
from math import comb

from components.mana import cost_alternatives

WUBRG = "WUBRG"
BASIC_FOR_COLOR = {"W": "Plains", "U": "Island", "B": "Swamp", "R": "Mountain", "G": "Forest"}
GOOD, OK = 0.90, 0.80  # Ampel wie bei der Farbverfuegbarkeit
MIN_SOURCES = 3        # Mindestquellen je verlangter Farbe (wie SPLASH_SOURCES im Deckvorschlag)


def colors_of_alts(alts):
    """Alle Farben, deren Symbol in irgendeinem Zahlungsweg vorkommt (Hybrid: beide Farben)."""
    return {col for _g, req in alts for col, _n in req if col in WUBRG}


def needs_of_alts(alts):
    """{Farbe: Anzahl}, die die Karte in jedem Zahlungsweg mindestens verlangt (Hybrid verlangt nichts)."""
    if not alts:
        return {}
    out = {}
    for col in WUBRG:
        k = min(dict(req).get(col, 0) for _g, req in alts)
        if k:
            out[col] = k
    return out


def land_fits(land_colors, deck_colors):
    """Passt ein Nicht-Standardland zu den Deckfarben? Alle erzeugten Farben muessen im Deck vorkommen."""
    produced = {c for c in land_colors if c in WUBRG}
    return bool(produced) and produced <= set(deck_colors)


@lru_cache(maxsize=None)
def p_at_least(deck, sources, seen, k):
    """Hypergeometrie: Wahrscheinlichkeit, unter 'seen' Karten aus 'deck' Karten mindestens k von 'sources' zu haben."""
    if k <= 0:
        return 1.0
    seen = min(seen, deck)
    sources = min(sources, deck)
    if sources < k:
        return 0.0
    total = comb(deck, seen)
    miss = sum(comb(sources, i) * comb(deck - sources, seen - i) for i in range(0, min(k, seen + 1)))
    return max(0.0, 1.0 - miss / total)


def seen_by_turn(mv):
    """Gesehene Karten bis zur Runde = Manawert (mindestens 1) auf dem Play: 7 + Runde - 1."""
    return 6 + max(1, int(round(mv or 0)))


def on_time(item, sources, deck):
    """Puenktlich-Wahrscheinlichkeit einer Karte. item: {needs, mv}; sources: {Farbe: Quellen}."""
    p = 1.0
    for col, k in item["needs"].items():
        p *= p_at_least(deck, sources.get(col, 0), seen_by_turn(item["mv"]), k)
    return p


def distribute(items, fixed_sources, n_basics, deck, colors):
    """Vergibt n_basics Standardlaender auf die Farben (nur Farben aus 'colors').
    items: [{needs, mv, qty}]; fixed_sources: Quellen aus Nicht-Standardlaendern. Gibt {Farbe: Anzahl} zurueck."""
    alloc = {c: 0 for c in WUBRG if c in colors}
    if not alloc:
        return {}
    pips = {c: sum(it["qty"] * it["needs"].get(c, 0) for it in items) for c in alloc}
    relevant = [it for it in items if it["needs"]]

    def score(src):
        return sum(it["qty"] * on_time(it, src, deck) for it in relevant)

    left = max(0, n_basics)
    for c in sorted((c for c in alloc if pips[c]), key=lambda c: (-pips[c], WUBRG.index(c))):
        add = min(left, max(0, MIN_SOURCES - fixed_sources.get(c, 0)))
        alloc[c] += add
        left -= add
    for _ in range(left):
        src = {c: fixed_sources.get(c, 0) + alloc.get(c, 0) for c in WUBRG}
        base = score(src)
        best = None
        for c in alloc:
            gain = score({**src, c: src[c] + 1}) - base
            key = (round(gain, 9), pips[c], -WUBRG.index(c))
            if best is None or key > best[0]:
                best = (key, c)
        alloc[best[1]] += 1
    return {c: k for c, k in alloc.items() if k}


def color_report(items, sources, deck):
    """Je Farbe: Karten mit Symbol, Quellen, Durchschnitt puenktlich und die schwaechste Karte."""
    out = {}
    for col in WUBRG:
        mine = [it for it in items if col in it["needs"]]
        if not mine and not sources.get(col):
            continue
        copies = sum(it["qty"] for it in mine)
        ps = [(on_time(it, sources, deck), it) for it in mine]
        avg = sum(p * it["qty"] for p, it in ps) / copies if copies else None
        worst = min(ps, key=lambda x: (x[0], x[1].get("name", ""))) if ps else None
        out[col] = {"cards": copies, "sources": sources.get(col, 0), "avg": avg,
                    "worst": {"name": worst[1].get("name", ""), "p": worst[0]} if worst else None}
    return out


def level(p):
    return "green" if p >= GOOD else "yellow" if p >= OK else "red"


GROUP_LABEL = {"core": "Core", "splash": "Splash", "nosplash": "NoSplash"}


def _variants(marks):
    used = {m for ms in marks for m in ms}
    if used & {"splash", "nosplash"}:
        return [("splash", ("core", "splash")), ("nosplash", ("core", "nosplash"))]
    return [("core", ("core",))]


def recommend(pool, marks, target=40):
    """Land-Empfehlung fuer die Zuordnung der Seite.
    pool: Pool-Karten des Drafthelpers (name, qty, cost, mv, land, produces); marks: je Karte eine Markierung je Kopie.
    Nicht-Standardlaender: passt zu allen Varianten -> Core, nur zu einer -> deren Gruppe, sonst Aus.
    Laender je Variante: Zielgroesse minus Zauber, begrenzt auf die Faustregel. Standardlaender je Variante nach
    distribute; in Core steht, was beide Varianten brauchen, der Rest in Splash bzw. NoSplash.
    Gibt {marks, basics, lands, variants, warnings} zurueck; die Eingaben werden nicht veraendert."""
    from components.suggest import land_range

    variants = _variants(marks)
    low, high, rec = land_range(target)
    info = {}
    for key, groups in variants:
        items, colors = [], set()
        for card, ms in zip(pool, marks):
            n = sum(m in groups for m in ms)
            if not n or card.get("land"):
                continue
            alts = cost_alternatives(card.get("cost") or "")
            colors |= colors_of_alts(alts)
            items.append({"name": card["name"], "needs": needs_of_alts(alts), "mv": card.get("mv") or 0, "qty": n})
        info[key] = {"items": items, "colors": colors, "spells": sum(it["qty"] for it in items)}

    new_marks = [list(ms) for ms in marks]
    lands_out = []
    for ci, card in enumerate(pool):
        if not card.get("land"):
            continue
        produces = [c for c in WUBRG if c in (card.get("produces") or [])]
        fits = {key: land_fits(produces, info[key]["colors"]) for key, _ in variants}
        if all(fits.values()):
            group = "core"
        elif any(fits.values()):
            group = next(k for k, ok in fits.items() if ok)
        else:
            group = "off"
        new_marks[ci] = [group] * card["qty"]
        missing = sorted({c for c in produces} - set().union(*(info[k]["colors"] for k, _ in variants)),
                         key=WUBRG.index)
        lands_out.append({"name": card["name"], "qty": card["qty"], "colors": produces, "group": group,
                          "missing": missing})

    warnings, out_variants, per_variant = [], [], {}
    for key, groups in variants:
        v = info[key]
        nonbasic = [(l, l["qty"]) for l in lands_out if l["group"] in groups]
        n_nonbasic = sum(q for _, q in nonbasic)
        lands = min(max(target - v["spells"], low), high) if v["spells"] else rec
        n_basics = max(0, lands - n_nonbasic)
        if n_nonbasic > lands:
            lands = n_nonbasic
            warnings.append(f"{GROUP_LABEL[key]}: mehr passende Nicht-Standardländer ({n_nonbasic}) als Länder "
                            "nach der Faustregel.")
        fixed = {c: sum(q for l, q in nonbasic if c in l["colors"]) for c in WUBRG}
        deck = v["spells"] + lands
        needed = {c for it in v["items"] for c in it["needs"]}
        alloc = distribute(v["items"], fixed, n_basics, deck, needed)
        if not needed and n_basics:
            warnings.append(f"{GROUP_LABEL[key]}: keine Karte verlangt eine bestimmte Farbe, deshalb werden keine "
                            "Standardländer empfohlen.")
        sources = {c: fixed[c] + alloc.get(c, 0) for c in WUBRG}
        if deck != target:
            warnings.append(f"{GROUP_LABEL[key]}: {v['spells']} Zauber + {lands} Länder = {deck} Karten "
                            f"(Ziel {target}; Faustregel {low} bis {high} Länder).")
        per_variant[key] = alloc
        out_variants.append({"key": key, "label": GROUP_LABEL[key], "spells": v["spells"],
                             "lands": n_nonbasic + sum(alloc.values()), "nonbasic": n_nonbasic, "size": deck,
                             "colors": [c for c in WUBRG if c in v["colors"]], "basics": alloc,
                             "sources": {c: k for c, k in sources.items() if k},
                             "report": color_report(v["items"], sources, deck)})

    basics = {BASIC_FOR_COLOR[c]: {"core": 0, "splash": 0, "nosplash": 0} for c in WUBRG}
    keys = [k for k, _ in variants]
    for c in WUBRG:
        counts = {k: per_variant[k].get(c, 0) for k in keys}
        if keys == ["core"]:
            basics[BASIC_FOR_COLOR[c]]["core"] = counts["core"]
            continue
        shared = min(counts.values())
        basics[BASIC_FOR_COLOR[c]]["core"] = shared
        for k in keys:
            basics[BASIC_FOR_COLOR[c]][k] = counts[k] - shared
    return {"marks": new_marks, "basics": basics, "lands": lands_out, "variants": out_variants,
            "warnings": warnings}


def color_overview(pool, marks, basics):
    """Farben und Quellen je Variante fuer die Seitenleiste des Drafthelpers (aktueller Stand, keine Empfehlung).
    basics: {Landname: {core, splash, nosplash}}. Je Farbe: Symbole (zwingend verlangte Farbsymbole mal Kopien),
    Karten, Quellen (Standardlaender der Variante plus zugeordnete Nicht-Standardlaender, davon nonbasic) und
    Ø puenktlich mit der knappsten Karte wie im Bericht. Gibt {variants: [{key, label, deck, rows}]} zurueck."""
    basics = {n: {g: int((v or {}).get(g) or 0) for g in GROUP_LABEL} for n, v in (basics or {}).items()}
    two = any(m in ("splash", "nosplash") for ms in marks for m in ms) or \
        any(v["splash"] or v["nosplash"] for v in basics.values())
    variants = [("splash", ("core", "splash")), ("nosplash", ("core", "nosplash"))] if two else [("core", ("core",))]
    color_of_basic = {name: c for c, name in BASIC_FOR_COLOR.items()}
    out = []
    for key, groups in variants:
        items, nonbasic, n_lands = [], {c: 0 for c in WUBRG}, 0
        for card, ms in zip(pool, marks):
            n = sum(m in groups for m in ms)
            if not n:
                continue
            if card.get("land"):
                n_lands += n
                for c in set(card.get("produces") or []) & set(WUBRG):
                    nonbasic[c] += n
                continue
            items.append({"name": card["name"], "needs": needs_of_alts(cost_alternatives(card.get("cost") or "")),
                          "mv": card.get("mv") or 0, "qty": n})
        basic_src = {c: 0 for c in WUBRG}
        for name, v in basics.items():
            k = sum(v[g] for g in groups)
            n_lands += k
            if name in color_of_basic:
                basic_src[color_of_basic[name]] += k
        sources = {c: basic_src[c] + nonbasic[c] for c in WUBRG}
        deck = sum(it["qty"] for it in items) + n_lands
        rep = color_report(items, sources, deck) if deck else {}
        rows = []
        for c in WUBRG:
            pips = sum(it["qty"] * it["needs"].get(c, 0) for it in items)
            if c not in rep and not pips:
                continue
            r = rep.get(c) or {"cards": 0, "avg": None, "worst": None}
            rows.append({"color": c, "pips": pips, "cards": r["cards"], "sources": sources[c], "nonbasic": nonbasic[c],
                         "avg": r["avg"], "worst": r["worst"]})
        out.append({"key": key, "label": GROUP_LABEL[key], "deck": deck, "rows": rows})
    return {"variants": out}
