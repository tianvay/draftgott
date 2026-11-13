"""Live-Draft: offene Farben (Signale) aus den Packs, die man gesehen hat.

Stark = eigene Bewertung Must Play oder hoeher (Matchwinner, Splashworthy, MustPlay). Je Farbe der Karte (mehrfarbige
zaehlen fuer jede Farbe, farblose nicht):
  - Wheel (+2 offen): ein Pack kommt zurueck und eine starke Karte liegt noch drin. Ein Pack gilt als zurueckgekommen,
    wenn es (mit Kopien) eine Teilmenge eines frueheren Packs derselben Runde ohne die eigenen Picks daraus ist.
    Das gilt fuer jede Spielerzahl und fuer Pick Two wie fuer den klassischen Draft.
  - Umkaempft (+1): eine starke Karte, die zwischen den beiden Besuchen eines Packs von anderen genommen wurde.
  - Spaet (+1 offen): eine starke Karte beim ersten Besuch eines Packs, das schon mindestens LATE_PLAYERS andere
    Spieler gesehen haben. Gezaehlt werden Spieler, nicht Karten: (Groesse des vollen Packs - Groesse jetzt) / Karten
    je Pick. Pick Two nimmt 2 Karten je Pick, ein Pack mit 8 von 14 Karten haben also 3 Spieler gesehen (klassisch 6).
Eine Runde beginnt, wenn ein Pack groesser ist als das vorige. Karten je Pick: die haeufigste Zahl eigener Picks je
Pack; ohne Picks aus dem Eventnamen (PickTwo -> 2), sonst 1.
Wert je Farbe = offen - umkaempft; Stufe: ab 3 "open" (offen), ab 1 "maybe" (vielleicht offen), ab -2 abwaerts
"contested" (umkaempft).
"""
from collections import Counter

STRONG = ("matchwinner", "splashworthy", "mustplay")
SHORT = {"matchwinner": "♛", "splashworthy": "★", "mustplay": "MP"}
WHEEL_POINTS, LATE_POINTS, TAKEN_POINTS = 2, 1, 1
LATE_PLAYERS = 3
COLORS = "WUBRG"
MAX_NOTES = 6


def level(score):
    if score >= 3:
        return "open"
    if score >= 1:
        return "maybe"
    if score <= -2:
        return "contested"
    return ""


def _per_pick(history, event):
    counts = Counter(len(h["picked"]) for h in history if h.get("picked"))
    if counts:
        return max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]
    return 2 if "picktwo" in (event or "").lower() else 1


def _rounds(history):
    """Runde je Eintrag (0, 1, 2 ...): neue Runde, wenn das Pack groesser ist als das vorige."""
    out, r = [], 0
    for i, h in enumerate(history):
        if i and len(h["cards"]) > len(history[i - 1]["cards"]):
            r += 1
        out.append(r)
    return out


def analyze(history, card_of, ratings, event=None):
    """history: [{"cards": [GrpId], "picked": [GrpId], "pick": Nummer}] in Reihenfolge; card_of(grp): Kartenangaben
    mit "name" und "colors" oder None; ratings: {Name: Kategorie}."""
    ratings = ratings or {}
    per_pick = _per_pick(history, event)
    rounds = _rounds(history)
    start = {}
    for h, r in zip(history, rounds):
        start[r] = max(start.get(r, 0), len(h["cards"]))
    opened, contested = Counter(), Counter()
    notes, wheels = [], 0

    def strong(grp):
        c = card_of(grp)
        if not c or ratings.get(c["name"]) not in STRONG:
            return None
        return c

    def label(c):
        return f"{c['name']} ({SHORT[ratings[c['name']]]})"

    for i, h in enumerate(history):
        here = Counter(h["cards"])
        source = None
        for j in range(i - 1, -1, -1):
            if rounds[j] != rounds[i]:
                break
            before = Counter(history[j]["cards"]) - Counter(history[j]["picked"])
            if len(history[j]["cards"]) > len(h["cards"]) and not (here - before):
                source = j
                break
        if source is not None:
            wheels += 1
            for grp in sorted(set(here)):
                c = strong(grp)
                if c:
                    for col in c["colors"]:
                        opened[col] += WHEEL_POINTS
                    notes.append(f"Pick {h['pick']}: {label(c)} kam zurück")
            taken = Counter(history[source]["cards"]) - Counter(history[source]["picked"]) - here
            for grp in sorted(set(taken)):
                c = strong(grp)
                if c:
                    for col in c["colors"]:
                        contested[col] += TAKEN_POINTS
                    notes.append(f"Pick {h['pick']}: {label(c)} von anderen genommen")
            continue
        players = (start[rounds[i]] - len(h["cards"])) / per_pick
        if players >= LATE_PLAYERS:
            for grp in sorted(set(here)):
                c = strong(grp)
                if c:
                    for col in c["colors"]:
                        opened[col] += LATE_POINTS
                    notes.append(f"Pick {h['pick']}: {label(c)} noch spät im Pack")
    colors = {}
    for col in COLORS:
        score = opened[col] - contested[col]
        colors[col] = {"open": opened[col], "contested": contested[col], "score": score, "level": level(score)}
    return {"format": "Pick Two" if per_pick == 2 else "Draft", "per_pick": per_pick, "wheels": wheels,
            "colors": colors, "notes": list(reversed(notes))[:MAX_NOTES]}
