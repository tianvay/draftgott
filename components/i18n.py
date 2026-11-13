"""Sprache der Ausgabe (Deutsch oder Englisch) fuer Bericht, Drafthelper, Setauswertung, Overlay und Konsole.

Deutsch ist der Standard: ohne set_lang("en") gibt t() jeden Text unveraendert zurueck, die Ausgabe bleibt also
Zeichen fuer Zeichen wie bisher.

Zwei Werkzeuge:
- t("Deutscher Text {n}", n=3): sucht den deutschen Text im englischen Woerterbuch (components/i18n_en/*.py, je Modul
  eine Datei mit EN = {"Deutsch": "English"}) und setzt danach die Platzhalter {name} ein. Fehlt ein Eintrag, bleibt
  der deutsche Text stehen. Nur Platzhalter, die als Schluesselwort uebergeben werden, werden ersetzt; andere
  geschweifte Klammern (CSS, JavaScript) bleiben unberuehrt.
  t() erst beim Erzeugen der Ausgabe aufrufen, nie beim Import eines Moduls (dann ist die Sprache noch nicht gesetzt).
- tr_block(text, table): fuer grosse feste Vorlagen (z. B. die Drafthelper-Seite mit JavaScript) ersetzt es im
  Englischen jedes Stueck aus table (laengste zuerst) woertlich. Im Deutschen bleibt der Text unveraendert.

dec(text): Dezimalzahl-Text; im Deutschen mit Komma ("2,5"), im Englischen mit Punkt ("2.5").
"""
import importlib
import pkgutil

LANGS = ("de", "en")
LANG = "de"
_EN = None


def set_lang(lang):
    """Setzt die Sprache ("de" oder "en") fuer den ganzen Prozess."""
    global LANG
    if lang not in LANGS:
        raise ValueError(f"Unbekannte Sprache: {lang}")
    LANG = lang


def get_lang():
    return LANG


def is_en():
    return LANG == "en"


def html_lang():
    """Wert fuer <html lang="...">."""
    return LANG


def en_table():
    """Das englische Woerterbuch aller Module (einmal geladen)."""
    global _EN
    if _EN is None:
        from components import i18n_en
        table = {}
        for mod in sorted(m.name for m in pkgutil.iter_modules(i18n_en.__path__)):
            table.update(getattr(importlib.import_module(f"components.i18n_en.{mod}"), "EN", {}))
        _EN = table
    return _EN


def t(text, **kw):
    """Text in der aktuellen Sprache, Platzhalter {name} durch kw ersetzt."""
    if LANG == "en":
        text = en_table().get(text, text)
    for k, v in kw.items():
        text = text.replace("{" + k + "}", str(v))
    return text


def tr_block(text, table):
    """Feste Vorlage in der aktuellen Sprache: im Englischen jedes Stueck aus table woertlich ersetzt (laengste
    zuerst, damit kuerzere Stuecke keine laengeren zerschneiden)."""
    if LANG != "en":
        return text
    for de in sorted(table, key=len, reverse=True):
        text = text.replace(de, table[de])
    return text


def dec(text):
    """Dezimalzahl-Text in der Schreibweise der Sprache."""
    text = str(text)
    return text.replace(".", ",") if LANG == "de" else text
