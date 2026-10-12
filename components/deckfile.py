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


def parse_pool(text):
    """Liest Deck und Sideboard einer Kartenpool-Datei ('N Kartenname (SET) Nummer').
    Gibt eine Liste von {name, qty, section, set, number} in Dateireihenfolge zurueck (section: deck/sideboard)."""
    rows, section = [], None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.lower() in SECTIONS:
            section = line.lower()
            continue
        if section not in ("deck", "sideboard"):
            continue
        m = re.match(r"^(\d+)x?\s+(.+?)(?:\s+\(([A-Za-z0-9]+)\)\s*(\S*))?$", line)
        if m:
            rows.append({"name": m.group(2).strip(), "qty": int(m.group(1)), "section": section,
                         "set": (m.group(3) or "").lower(), "number": m.group(4) or ""})
    return rows


def split_label(spec):
    """'datei.txt=Label' -> (datei.txt, Label). Ohne Label wird der Dateiname genommen (ohne fuehrende '_')."""
    path, label = spec, None
    if "=" in spec:
        path, label = spec.rsplit("=", 1)
    if not label:
        stem = pathlib.Path(path).stem.strip("_- ")
        label = stem[:1].upper() + stem[1:]
    return path, label
