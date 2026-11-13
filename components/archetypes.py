"""Archetypen je Set (Farbpaare mit Spielhinweisen), eingeblendet im Drafthelper und im Bericht.

Neues Set: einen Eintrag in ARCHETYPES mit dem Setcode (klein) ergaenzen. Je Archetyp: "colors" (zwei Farben in
WUBRG-Reihenfolge wie WU, UB, ..., GW, RW, UG), "name" (englischer Originaltitel) und "tips"
(deutsch, Keywords auf Englisch).
"""
from collections import Counter

from components.i18n import t

WUBRG = "WUBRG"
PAIRS = ("WU", "UB", "BR", "RG", "GW", "WB", "UR", "BG", "RW", "UG")  # uebliche Schreibweise der Farbpaare
COLOR_NAME = {"W": "Weiß", "U": "Blau", "B": "Schwarz", "R": "Rot", "G": "Grün"}


def _a(colors, name, *tips):
    return {"colors": colors, "name": name, "tips": list(tips)}


_RAW = {
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
    "fra": [
        _a("WU", "Fatehold Surveil Aggro",
           "Aufs Board spielen.",
           "Mit Surveil die starken Karten finden.",
           "Empower Jace für Surveil-Synergien."),
        _a("UB", "Theorix Self-Mill",
           "Aufs lange Spiel spielen.",
           "Flexible Karten bevorzugen."),
        _a("BR", "Stingerquill Burn",
           "Billige Kreaturen spielen.",
           "Spiele mit Direct Damage schnell beenden."),
        _a("RG", "Konstrari Artifact Ramp",
           "Ramp und teure Zauber im Gleichgewicht halten.",
           "Frühe Spielzüge zählen trotzdem.",
           "Removal und Blocker bevorzugen."),
        _a("GW", "Vigorbloom Lifegain",
           "Aggressiv spielen.",
           "Mit Lifegain das Damage-Race gewinnen."),
        _a("WB", "Liliana's Graveyard",
           "Spiele durch 1-gegen-1-Tausche in die Länge ziehen.",
           "Mit Recursion den Gegner im Kartenwert ausspielen.",
           "Auf Zermürbung (Attrition) ausgelegt."),
        _a("UR", "Chandra's Prowess",
           "Prowess-Kreaturen sind der Schlüssel zum Sieg.",
           "Kartenziehen ist wichtig, damit die Hand voll bleibt."),
        _a("BG", "Garruk's Stompy",
           "Gutes Removal spielen.",
           "Große Kreaturen spielen.",
           "Wenig Synergie, hohe Kartenqualität."),
        _a("RW", "Ajani's Go-wide Aggro",
           "So schnell wie möglich spielen.",
           "So viele Kreaturen wie möglich.",
           "Kämpfe mit Removal und Tricks gewinnen."),
        _a("UG", "Empower Jace",
           "Aufs späte Spiel auslegen.",
           "Defensive Karten bevorzugen."),
    ],
}


def _tr_list(lst):
    """Archetypen mit uebersetzten Spielhinweisen (Englisch); im Deutschen unveraendert."""
    return [dict(a, tips=[t(x) for x in a["tips"]]) for a in lst]


class _Archetypes(dict):
    """ARCHETYPES: gibt die Spielhinweise beim Abruf in der aktuellen Sprache heraus."""

    def __getitem__(self, key):
        return _tr_list(dict.__getitem__(self, key))

    def get(self, key, default=None):
        return _tr_list(dict.get(self, key)) if key in self else default

    def items(self):
        return [(k, _tr_list(v)) for k, v in dict.items(self)]

    def values(self):
        return [_tr_list(v) for v in dict.values(self)]


ARCHETYPES = _Archetypes(_RAW)


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
    return "/".join(t(COLOR_NAME[c]) for c in colors)
