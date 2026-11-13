"""Hilfen fuer die Tests der englischen Ausgabe: findet deutsche Reste in einem Text (HTML, JavaScript, Konsole)."""
import contextlib
import re

from components import i18n

# Deutsche Woerter, die im Englischen nicht vorkommen (Gross-/Kleinschreibung zaehlt)
GERMAN_WORDS = (
    "und", "oder", "nicht", "der", "die", "das", "dem", "den", "des", "mit", "fuer", "ein", "eine", "einen", "kein",
    "keine", "wird", "werden", "ist", "sind", "auch", "bei", "nach", "noch", "nur", "wenn", "aus", "sich", "zum",
    "zur", "vom", "im", "beim", "ueber", "Karte", "Karten", "Gegner", "Zug", "Runde", "Runden", "Spiel", "Spiele",
    "Bericht", "Kreatur", "Kreaturen", "Farbe", "Farben", "Sieg", "Siege", "Beenden", "Seite", "Fenster", "Zauber",
    "Bewertung", "Kampf", "Gegnerdeck", "Starthand", "Friedhof", "Bibliothek", "Lebenspunkte", "Schaden",
)
_WORD_RE = re.compile(r"(?<![\w-])(" + "|".join(GERMAN_WORDS) + r")(?![\w-])")
_UMLAUT_RE = re.compile(r"[äöüÄÖÜß]")
_COMMENT_RES = (re.compile(r"/\*.*?\*/", re.S), re.compile(r"<!--.*?-->", re.S), re.compile(r"(^|\s)//[^\n]*"))


def german_leftovers(text, allow=()):
    """Deutsche Reste im Text: Liste von (Fundstelle, Umgebung). Kommentare in CSS, HTML und JavaScript zaehlen nicht.
    allow: Woerter oder Textstuecke, die erlaubt sind (z. B. Kartennamen); sie werden vorher entfernt."""
    for rx in _COMMENT_RES:
        text = rx.sub(" ", text)
    for a in allow:
        text = text.replace(a, " ")
    found = []
    for rx in (_UMLAUT_RE, _WORD_RE):
        for m in rx.finditer(text):
            found.append((m.group(0), text[max(0, m.start() - 40):m.end() + 40].replace("\n", " ")))
    return found


@contextlib.contextmanager
def english():
    """Im with-Block ist die Sprache Englisch, danach wieder wie vorher."""
    old = i18n.get_lang()
    i18n.set_lang("en")
    try:
        yield
    finally:
        i18n.set_lang(old)
