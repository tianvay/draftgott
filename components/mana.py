"""Mana-Modell: Kosten lesen, Zahlungswege (Hybrid/Phyrexian) und die Frage, ob ein Satz Laender eine Karte bezahlen kann."""
import itertools
import re
from collections import Counter
from functools import lru_cache


COLORS = set("WUBRGC")


def mana_value(mana_cost):
    total = 0
    for sym in re.findall(r"\{([^}]+)\}", mana_cost or ""):
        if sym.isdigit():
            total += int(sym)
        elif sym.upper() == "X":
            pass
        elif "/" in sym and sym.split("/")[0].isdigit():
            total += int(sym.split("/")[0])  # {2/W}
        else:
            total += 1
    return total


def symbol_options(sym):
    """Zahlungsoptionen eines Manasymbols als [(generisch, farbe|None)]."""
    if sym.isdigit():
        return [(int(sym), None)]
    if sym.upper() == "X":
        return [(0, None)]
    if sym in COLORS:
        return [(0, sym)]
    if sym == "S":  # Snow: vereinfacht als 1 generisches Mana
        return [(1, None)]
    if "/" in sym:
        parts = sym.split("/")
        if parts[-1] == "P":  # Phyrexian: Farbe ODER 2 Leben (= 0 Mana)
            return [(0, p) for p in parts[:-1] if p in COLORS] + [(0, None)]
        opts = []
        for p in parts:
            if p.isdigit():
                opts.append((int(p), None))
            elif p in COLORS:
                opts.append((0, p))
        return opts or [(1, None)]
    return [(1, None)]


def cost_alternatives(mana_cost):
    """Wandelt '{1}{W/U}{B}' in alle moeglichen Zahlungswege um."""
    if not mana_cost:
        return ()  # keine Manakosten -> nicht normal castbar
    alts = [(0, Counter())]
    for sym in re.findall(r"\{([^}]+)\}", mana_cost):
        new = []
        for g, cnt in alts:
            for og, oc in symbol_options(sym):
                c2 = Counter(cnt)
                if oc:
                    c2[oc] += 1
                new.append((g + og, c2))
        alts = new
    return tuple(sorted({(g, tuple(sorted(c.items()))) for g, c in alts}))


def can_pay(producing, generic, req):
    """Koennen die Laender (jeweils 1 Mana einer ihrer Farben) generic + req bezahlen?
    Farbanforderungen werden per Matching auf verschiedene Laender verteilt."""
    units = [c for c, n in req.items() for _ in range(n)]
    if len(producing) < generic + len(units):
        return False
    match = [-1] * len(producing)

    def assign(u, seen):
        for j, lc in enumerate(producing):
            if units[u] in lc and j not in seen:
                seen.add(j)
                if match[j] == -1 or assign(match[j], seen):
                    match[j] = u
                    return True
        return False

    return all(assign(u, set()) for u in range(len(units)))


@lru_cache(maxsize=None)
def can_cast_all(alts_list, lands_key):
    """Koennen alle diese Zauber gleichzeitig bezahlt werden? (alle Hybrid-Wege werden probiert)"""
    if any(not a for a in alts_list):
        return False
    producing = [lc for lc in lands_key if lc]
    for combo in itertools.product(*alts_list):
        generic = sum(g for g, _ in combo)
        req = Counter()
        for _, r in combo:
            for c, n in r:
                req[c] += n
        if can_pay(producing, generic, req):
            return True
    return False


@lru_cache(maxsize=None)
def has_two_colors(lands_key):
    """Koennen zwei verschiedene Laender zwei verschiedene Farben erzeugen? Farblos (C) zaehlt nicht."""
    cols = [tuple(c for c in lc if c != "C") for lc in lands_key]
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            if any(a != b for a in cols[i] for b in cols[j]):
                return True
    return False


def required_colors(card):
    """Farben, die die Karte in JEDEM Zahlungsweg braucht (Hybrid wie {R/G} verlangt keine bestimmte Farbe)."""
    sets = [{col for col, _ in req if col != "C"} for _, req in card.alts]
    return set.intersection(*sets) if sets else set()


def land_key(lands):
    return tuple(sorted(lands))


def double_pip_colors(cards):
    """Farben, die eine Nichtland-Karte in JEDEM Zahlungsweg mindestens zweimal verlangt (z. B. {2}{R}{R}).
    Hybrid wie {R/G}{R/G} zaehlt nicht. Gibt {Farbe: [Kartennamen, sortiert]} zurueck."""
    out = {}
    for card in cards:
        if card.is_land or not card.alts:
            continue
        for col in "WUBRG":
            if min(dict(req).get(col, 0) for _, req in card.alts) >= 2:
                out.setdefault(col, set()).add(card.name)
    return {col: sorted(names) for col, names in out.items()}
