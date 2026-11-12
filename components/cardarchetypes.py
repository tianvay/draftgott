"""Archetyp-Zuordnung je Karte (Drafthelper) und Erkennung des Archetyps aus den gedrafteten Karten.

Die Zuordnung steht je Kartenname in einer eigenen JSON-Datei (Standard kartenarchetypen.json, nicht im Git): eine
Liste von Archetyp-Schluesseln, das sind die Farbpaare aus components/archetypes.py (z. B. ["BR", "RW"]). Eine Karte
kann zu mehreren Archetypen passen.

Erkennung (detect): Jede Nichtland-Karte zaehlt mit dem Gewicht ihrer Bewertung (Splashworthy und MustPlay 2,
unbewertet und Filler 1, NeverPlay 0) je Kopie
  - fuer jeden Archetyp, in dessen Farben alle ihre Farben liegen (farblose Karten zaehlen hier nicht), und
  - noch einmal fuer jeden Archetyp, dem sie zugeordnet ist.
Erkannt ist der Archetyp mit den meisten Punkten, wenn er mindestens MIN_POINTS hat und allein vorn liegt; sonst ist
der Archetyp noch offen. Eine eigene Wahl (manual) geht vor.

Pack (rank): Punkte je Karte = Bewertung (Splashworthy 4, MustPlay 3, unbewertet 1,5, Filler 1) + 3, wenn sie dem
erkannten Archetyp zugeordnet ist, sonst + 1, wenn ihre Farben in dessen Farben liegen. NeverPlay hat immer 0.
"""
import json
import os
import pathlib

from components.archetypes import PAIRS

WEIGHT = {"splashworthy": 2, "mustplay": 2, "filler": 1, "neverplay": 0}  # unbewertet: 1
POINTS = {"splashworthy": 4, "mustplay": 3, "filler": 1, "neverplay": 0}  # unbewertet: 1.5
RATING_ORDER = {"splashworthy": 0, "mustplay": 1, "": 2, "filler": 3, "neverplay": 4}
LEVEL_POINTS = {"arch": 3, "color": 1, "": 0}
MIN_POINTS = 3


def _clean(pairs):
    """Gueltige Archetyp-Schluessel in der Reihenfolge von PAIRS, ohne Doppelte."""
    if not isinstance(pairs, list):
        return []
    return [p for p in PAIRS if p in pairs]


def load_assign(path):
    """{Kartenname: [Archetyp-Schluessel]}; fehlende oder kaputte Datei, unbekannte Schluessel und leere Listen
    zaehlen nicht."""
    try:
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    out = {}
    for name, pairs in data.items():
        clean = _clean(pairs)
        if clean:
            out[str(name)] = clean
    return out


def save_assign(path, data):
    """Schreibt die Zuordnung alphabetisch sortiert und lesbar (erst in eine Hilfsdatei, dann ersetzen)."""
    path = pathlib.Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(dict(sorted(data.items(), key=lambda kv: kv[0].lower())), ensure_ascii=False,
                              indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def set_assign(path, name, pairs):
    """Setzt die Archetypen einer Karte; eine leere Liste entfernt sie. Gibt die ganze Zuordnung zurueck."""
    if not name or not isinstance(name, str):
        raise ValueError("Kartenname fehlt")
    if not isinstance(pairs, list) or any(p not in PAIRS for p in pairs):
        raise ValueError("Unbekannter Archetyp")
    data = load_assign(path)
    clean = _clean(pairs)
    if clean:
        data[name] = clean
    else:
        data.pop(name, None)
    save_assign(path, data)
    return data


def _fits(colors, pair):
    return bool(colors) and set(colors) <= set(pair)


def detect(cards, assign, ratings, archetypes, manual=None):
    """Archetyp aus Karten [{"name", "qty", "colors", "land"}] (siehe Modulbeschreibung).
    Gibt {"main": Schluessel oder None, "manual": bool, "scores": [{"colors", "name", "score", "assigned"}]}
    zurueck, die Liste nach Punkten absteigend (Gleichstand: Reihenfolge des Sets)."""
    if not archetypes:
        return {"main": None, "manual": False, "scores": []}
    scores = [{"colors": a["colors"], "name": a["name"], "score": 0, "assigned": 0} for a in archetypes]
    for c in cards:
        if c.get("land"):
            continue
        qty = c.get("qty", 1)
        w = WEIGHT.get((ratings or {}).get(c["name"], ""), 1) * qty
        mine = (assign or {}).get(c["name"], [])
        for s in scores:
            if _fits(c.get("colors"), s["colors"]):
                s["score"] += w
            if s["colors"] in mine:
                s["score"] += w
                s["assigned"] += qty
    scores.sort(key=lambda s: -s["score"])
    keys = [s["colors"] for s in scores]
    if manual in keys:
        return {"main": manual, "manual": True, "scores": scores}
    top = scores[0]
    sure = top["score"] >= MIN_POINTS and (len(scores) < 2 or top["score"] > scores[1]["score"])
    return {"main": top["colors"] if sure else None, "manual": False, "scores": scores}


def archetype_map(archetypes, assign, picks, pack):
    """Je Archetyp des Sets die zugeordneten Picks ([{"name", "n"}] in Pick-Reihenfolge, "count" = Kopien) und
    Pack-Karten (Namen in Pack-Reihenfolge). Nur die eigene Zuordnung zaehlt: Karten ohne Zuordnung gehoeren keinem
    Archetyp an, eine Karte kann mehreren angehoeren. Archetypen ohne Karten fehlen."""
    out = []
    for a in archetypes or []:
        counts = {}
        for name in picks:
            if a["colors"] in (assign or {}).get(name, []):
                counts[name] = counts.get(name, 0) + 1
        in_pack = [n for n in pack if a["colors"] in (assign or {}).get(n, [])]
        if counts or in_pack:
            out.append({"colors": a["colors"], "name": a["name"], "count": sum(counts.values()),
                        "picks": [{"name": n, "n": k} for n, k in counts.items()], "pack": in_pack})
    return out


def level(card, assign, main):
    """"arch" (dem Archetyp zugeordnet), "color" (Farben passen) oder "" fuer eine Karte im Pack."""
    if not main:
        return ""
    if main in (assign or {}).get(card["name"], []):
        return "arch"
    return "color" if _fits(card.get("colors"), main) else ""


def rank(pack, ratings, assign, main):
    """Pack-Karten mit "rating", "arch", "level" und "points", nach Punkten sortiert (Gleichstand: Bewertung, Name)."""
    out = []
    for c in pack:
        r = (ratings or {}).get(c["name"], "")
        lv = level(c, assign, main)
        points = 0 if r == "neverplay" else POINTS.get(r, 1.5) + LEVEL_POINTS[lv]
        out.append(dict(c, rating=r, arch=list((assign or {}).get(c["name"], [])), level=lv, points=points))
    out.sort(key=lambda c: (-c["points"], RATING_ORDER.get(c["rating"], 2), c["name"]))
    return out
