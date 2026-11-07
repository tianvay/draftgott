"""Archetypen je Set (Farbpaare mit Spielhinweisen), eingeblendet im Drafthelper und im Bericht.

Neues Set: einen Eintrag in ARCHETYPES mit dem Setcode (klein) ergaenzen. Je Archetyp: "colors" (zwei Farben in
WUBRG-Reihenfolge wie WU, UB, ..., GW, RW, UG), "name" (englischer Originaltitel) und "tips"
(deutsch, Keywords auf Englisch).
"""
from collections import Counter

WUBRG = "WUBRG"
PAIRS = ("WU", "UB", "BR", "RG", "GW", "WB", "UR", "BG", "RW", "UG")  # uebliche Schreibweise der Farbpaare
COLOR_NAME = {"W": "Weiß", "U": "Blau", "B": "Schwarz", "R": "Rot", "G": "Grün"}


def _a(colors, name, *tips):
    return {"colors": colors, "name": name, "tips": list(tips)}


ARCHETYPES = {
    "trk": [
        _a("WU", "Spacecraft",
           "Sehr wichtig: die Zahl der Spacecraft und der Payoffs im Gleichgewicht halten.",
           "Spacecraft sind erst im mittleren bis späten Spiel Kreaturen – das Deck entsprechend bauen.",
           "Vigilance ist wichtig für Station."),
        _a("UB", "Dilemmas",
           "Sehr flexibel.",
           "Kann mit Synergien das Spiel übernehmen."),
        _a("BR", "Sacrifice",
           "Aggressiv: will den Gegner mit Sacrifice-Fodder und dem Wert daraus überrennen.",
           "Jede Karte, die mehrere Körper bringt, ist stark."),
        _a("RG", "Landfall",
           "Ramp + Stompy.",
           "Landfall-Trigger."),
        _a("GW", "Counters",
           "Synergien sind sehr wichtig: Karten, die sich um +1/+1 counters kümmern."),
        _a("WB", "Artifact Creatures",
           "Aggro-Deck: auf Synergien und Artifact Creatures setzen.",
           "Kleine Kreaturen zählen, weil das Removal flexibel ist."),
        _a("UR", "Spells",
           "Removal + Kartenziehen = Control.",
           "Darauf achten, genug Kreaturen zu spielen."),
        _a("BG", "Leaves the graveyard",
           "Zäh und aufs späte Spiel ausgelegt: den Gegner mit Kartenvorteil ausspielen.",
           "Graveyard-Synergien machen aus 1-gegen-1-Tauschen Wert im späten Spiel."),
        _a("RW", "8 Power/Go wide",
           "8 Power zu erreichen ist leichter als gedacht, wenn man genug Kreaturen spielt.",
           "Aggressive 2-Drops sind der Schlüssel, um früh 8 Power zu erreichen."),
        _a("UG", "Strange New Worlds",
           "Splash-freundlich, weil man viele verschieden benannte Länder will.",
           "Spielt gern Off-Color-Bomben."),
    ],
}


def for_set(code):
    """Archetypen eines Sets (Setcode in beliebiger Schreibweise) oder None."""
    return ARCHETYPES.get((code or "").lower())


def main_set(rows):
    """Haeufigstes Set nach Kopien in [{"set", "qty"}] (Zeilen ohne Set zaehlen nicht) oder None."""
    count = Counter()
    for r in rows:
        if r.get("set"):
            count[r["set"].lower()] += r.get("qty", 1)
    return count.most_common(1)[0][0] if count else None


def info(rows):
    """{"set": "TRK", "list": [...]} fuer einen Pool bzw. ein Deck ({"set", "qty", "land"}); Laender entscheiden das
    Set nicht (Standardlaender kommen oft aus anderen Sets). None, wenn fuer das Set keine Archetypen definiert sind."""
    code = main_set([r for r in rows if not r.get("land")])
    found = for_set(code)
    return {"set": code.upper(), "list": found} if found else None


def main_pair(counts):
    """Hauptfarbpaar aus Kopien je Farbe ({"W": 7, ...}): die zwei haeufigsten Farben (Gleichstand: WUBRG), in
    WUBRG-Reihenfolge der Archetypen-Schluessel (z. B. "GW", "RW", "UG"). None bei weniger als zwei Farben."""
    top = sorted((c for c in WUBRG if counts.get(c, 0) > 0), key=lambda c: (-counts[c], WUBRG.index(c)))[:2]
    if len(top) < 2:
        return None
    a, b = sorted(top, key=WUBRG.index)
    return a + b if a + b in PAIRS else b + a


def pair_label(colors):
    """"Weiß/Blau" fuer "WU"."""
    return "/".join(COLOR_NAME[c] for c in colors)
