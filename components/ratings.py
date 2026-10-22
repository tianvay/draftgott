"""Kartenbewertung fuer den Drafthelper: je Kartenname eine Kategorie (Splashworthy, MustPlay, Filler, NeverPlay) in
einer eigenen JSON-Datei (Standard kartenbewertung.json, nicht im Git). Sie gilt fuer jeden Kartenpool."""
import json
import os
import pathlib

CATEGORIES = ("splashworthy", "mustplay", "filler", "neverplay")


def load_ratings(path):
    """{Kartenname: Kategorie}; fehlende oder kaputte Datei und unbekannte Kategorien zaehlen nicht."""
    try:
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(name): cat for name, cat in data.items() if cat in CATEGORIES}


def save_ratings(path, data):
    """Schreibt die Bewertung alphabetisch sortiert und lesbar (erst in eine Hilfsdatei, dann ersetzen)."""
    path = pathlib.Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(dict(sorted(data.items(), key=lambda kv: kv[0].lower())), ensure_ascii=False,
                              indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def set_rating(path, name, cat):
    """Setzt die Kategorie einer Karte; leere Kategorie entfernt sie. Gibt die ganze Bewertung zurueck."""
    if cat and cat not in CATEGORIES:
        raise ValueError("Unbekannte Kategorie")
    data = load_ratings(path)
    if cat:
        data[name] = cat
    else:
        data.pop(name, None)
    save_ratings(path, data)
    return data


def merge_ratings(path, cats):
    """Uebernimmt Kategorien (z. B. aus alten Browser-Speicherstaenden), aber nur fuer Karten ohne Bewertung."""
    data = load_ratings(path)
    new = {str(n): c for n, c in (cats or {}).items() if c in CATEGORIES and str(n) not in data}
    if new:
        data.update(new)
        save_ratings(path, data)
    return data
