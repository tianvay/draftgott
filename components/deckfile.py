"""Deckdateien einlesen (Format "N Kartenname") und Datei-Angaben der Kommandozeile auswerten."""
import pathlib
import re


SECTIONS = {"about", "deck", "sideboard", "commander", "companion"}


def parse_deck_name(text, fallback):
    """Liest die Zeile 'Name ...' aus dem Abschnitt About."""
    m = re.search(r"^\s*Name[ \t]+(.+?)\s*$", text, re.M | re.I)
    return m.group(1) if m else fallback


def parse_deck(text):
    """Liest 'N Kartenname' im Abschnitt 'Deck'. Gibt {name: anzahl} zurueck."""
    deck, section = {}, None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.lower() in SECTIONS:
            section = line.lower()
            continue
        if section not in (None, "deck"):
            continue
        m = re.match(r"^(\d+)x?\s+(.+?)(?:\s+\([A-Za-z0-9]+\)\s*\S*)?$", line)
        if m:
            name = m.group(2).strip()
            deck[name] = deck.get(name, 0) + int(m.group(1))
    return deck


def split_label(spec):
    """'datei.txt=Label' -> (datei.txt, Label). Ohne Label wird der Dateiname genommen (ohne fuehrende '_')."""
    path, label = spec, None
    if "=" in spec:
        path, label = spec.rsplit("=", 1)
    if not label:
        stem = pathlib.Path(path).stem.strip("_- ")
        label = stem[:1].upper() + stem[1:]
    return path, label
