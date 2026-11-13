"""Archetyp-Zuordnung je Karte (Drafthelper) und Erkennung des Archetyps aus den gedrafteten Karten.

Die Zuordnung steht je Kartenname in einer eigenen JSON-Datei (Standard kartenarchetypen.json, nicht im Git): eine
Liste von Archetyp-Schluesseln, das sind die Farbpaare aus components/archetypes.py (z. B. ["BR", "RW"]). Eine Karte
kann zu mehreren Archetypen passen. Ist einer davon der beste Archetyp der Karte, steht statt der Liste
{"arch": [...], "best": "BR"} da (Knoepfe im Drafthelper: neutral -> gruen = gut -> lila = best).

Erkennung (detect): Jede Nichtland-Karte zaehlt mit dem Gewicht ihrer Bewertung (Matchwinner 3, Splashworthy und MustPlay 2,
unbewertet und Filler 1, NeverPlay 0) je Kopie
  - fuer jeden Archetyp, in dessen Farben alle ihre Farben liegen (farblose Karten zaehlen hier nicht), und
  - noch einmal fuer jeden Archetyp, dem sie zugeordnet ist.
Erkannt ist der Archetyp mit den meisten Punkten, wenn er mindestens MIN_POINTS hat und allein vorn liegt; sonst ist
der Archetyp noch offen. Eine eigene Wahl (manual) geht vor.

Hinweis (hint): Karten ab MustPlay mit bestem Archetyp, wenn wir in ihm sind ("in": erkannt oder selbst gewaehlt) oder
nahe dran ("near": er hat Punkte und liegt hoechstens NEAR_POINTS hinter dem besten Archetyp).

Pack (rank): Punkte je Karte = Bewertung (Matchwinner 5, Splashworthy 4, MustPlay 3, unbewertet 1,5, Filler 1) + 3, wenn sie dem
erkannten Archetyp zugeordnet ist (+ 4, wenn er ihr bester ist), sonst + 1, wenn ihre Farben in dessen Farben liegen. NeverPlay hat immer 0.
Mit pool (bisherige Picks) kommt der Synergie-Zuwachs der Karte zum Pool dazu (components/synergy.pick_bonus, bis
+2); mit erkanntem Archetyp zaehlen nur Picks in dessen Farben (farblose immer).
"""
import json
import os
import pathlib

from components import synergy
from components.archetypes import PAIRS

WEIGHT = {"matchwinner": 3, "splashworthy": 2, "mustplay": 2, "filler": 1, "neverplay": 0}  # unbewertet: 1
POINTS = {"matchwinner": 5, "splashworthy": 4, "mustplay": 3, "filler": 1, "neverplay": 0}  # unbewertet: 1.5
RATING_ORDER = {"matchwinner": -1, "splashworthy": 0, "mustplay": 1, "": 2, "filler": 3, "neverplay": 4}
LEVEL_POINTS = {"best": 4, "arch": 3, "color": 1, "": 0}
MIN_POINTS = 3
NEAR_POINTS = 3
HINT_RATINGS = ("matchwinner", "splashworthy", "mustplay")


def _clean(pairs):
    """Gueltige Archetyp-Schluessel in der Reihenfolge von PAIRS, ohne Doppelte."""
    if not isinstance(pairs, list):
        return []
    return [p for p in PAIRS if p in pairs]


def _entry(value):
    """(Archetypen, bester Archetyp oder "") eines Eintrags: Liste oder {"arch": [...], "best": "BR"}; der beste
    Archetyp gehoert immer mit zur Zuordnung."""
    if isinstance(value, dict):
        best = value.get("best") if value.get("best") in PAIRS else ""
        pairs = value.get("arch") if isinstance(value.get("arch"), list) else []
        return _clean(pairs + ([best] if best else [])), best
    return _clean(value), ""


def _load(path):
    try:
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    out = {}
    for name, value in data.items():
        pairs, best = _entry(value)
        if pairs:
            out[str(name)] = (pairs, best)
    return out


def load_assign(path):
    """{Kartenname: [Archetyp-Schluessel]}; fehlende oder kaputte Datei, unbekannte Schluessel und leere Listen
    zaehlen nicht."""
    return {n: pairs for n, (pairs, _best) in _load(path).items()}


def load_best(path):
    """{Kartenname: bester Archetyp} (nur Karten, bei denen einer gesetzt ist)."""
    return {n: best for n, (_pairs, best) in _load(path).items() if best}


def save_assign(path, data, best=None):
    """Schreibt die Zuordnung alphabetisch sortiert und lesbar (erst in eine Hilfsdatei, dann ersetzen); Karten mit
    bestem Archetyp (best: {Name: Schluessel}) als {"arch", "best"}, sonst als Liste."""
    path = pathlib.Path(path)
    best = best or {}
    out = {n: ({"arch": pairs, "best": best[n]} if best.get(n) in pairs else pairs)
           for n, pairs in sorted(data.items(), key=lambda kv: kv[0].lower())}
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def set_assign(path, name, pairs, best=None):
    """Setzt die Archetypen einer Karte; eine leere Liste entfernt sie. best: bester Archetyp (kommt mit in die
    Zuordnung), "" entfernt ihn, None laesst ihn, solange er zugeordnet bleibt. Gibt die ganze Zuordnung zurueck."""
    if not name or not isinstance(name, str):
        raise ValueError("Kartenname fehlt")
    if not isinstance(pairs, list) or any(p not in PAIRS for p in pairs):
        raise ValueError("Unbekannter Archetyp")
    if best not in (None, "") and best not in PAIRS:
        raise ValueError("Unbekannter Archetyp")
    loaded = _load(path)
    data = {n: p for n, (p, _b) in loaded.items()}
    bests = {n: b for n, (_p, b) in loaded.items() if b}
    if best is not None:
        bests.pop(name, None)
        if best:
            bests[name] = best
            pairs = pairs + [best]
    clean = _clean(pairs)
    if clean:
        data[name] = clean
    else:
        data.pop(name, None)
    save_assign(path, data, bests)
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


def level(card, assign, main, best=None):
    """"best" (sein bester Archetyp), "arch" (dem Archetyp zugeordnet), "color" (Farben passen) oder "" fuer eine
    Karte im Pack."""
    if not main:
        return ""
    if (best or {}).get(card["name"]) == main:
        return "best"
    if main in (assign or {}).get(card["name"], []):
        return "arch"
    return "color" if _fits(card.get("colors"), main) else ""


def near(detect, pair):
    """"in", wenn pair der erkannte (oder selbst gewaehlte) Archetyp ist, "near", wenn er Punkte hat und hoechstens
    NEAR_POINTS hinter dem besten liegt, sonst ""."""
    if not detect or not pair:
        return ""
    if detect.get("main") == pair:
        return "in"
    scores = detect.get("scores") or []
    mine = next((s["score"] for s in scores if s["colors"] == pair), 0)
    top = max((s["score"] for s in scores), default=0)
    return "near" if mine > 0 and mine >= top - NEAR_POINTS else ""


def rank(pack, ratings, assign, main, best=None, detect=None, pool=None):
    """Pack-Karten mit "rating", "arch", "best", "level", "hint" und "points", nach Punkten sortiert (Gleichstand:
    Bewertung, Name). hint nur mit detect (siehe Modulbeschreibung). Mit pool zusaetzlich "synergy" (Bonus) und
    "syn_with" (Partner im Pool)."""
    if pool is not None:
        mine = [dict(c, qty=c.get("qty", 1)) for c in pool
                if not c.get("land") and (not main or set(c.get("colors") or []) <= set(main))]
    out = []
    for c in pack:
        r = (ratings or {}).get(c["name"], "")
        lv = level(c, assign, main, best)
        top = (best or {}).get(c["name"], "")
        points = 0 if r == "neverplay" else POINTS.get(r, 1.5) + LEVEL_POINTS[lv]
        extra = {}
        if pool is not None:
            bonus, partners = synergy.pick_bonus(mine, c) if c.get("syn") else (0, [])
            extra = {"synergy": bonus, "syn_with": partners}
            if r != "neverplay":
                points = round(points + bonus, 1)
        out.append(dict(c, rating=r, arch=list((assign or {}).get(c["name"], [])), best=top, level=lv, points=points,
                        hint=near(detect, top) if r in HINT_RATINGS else "", **extra))
    out.sort(key=lambda c: (-c["points"], RATING_ORDER.get(c["rating"], 2), c["name"]))
    return out
