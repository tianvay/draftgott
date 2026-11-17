"""Ordner des Projekts (Nutzer 17.11.2026): JSON-Dateien (Bewertung, Archetypen, Statistik, Scryfall-Caches,
Fensterlagen, Kalibrierungen) liegen in daten, erzeugte HTML-Berichte in berichte; beide nicht im Git.

Ein blosser Dateiname landet im passenden Ordner, ein Pfad mit Ordner oder ein absoluter Pfad gilt wie angegeben.
tidy_up() zieht beim Start vorhandene Dateien aus dem Projektordner einmalig um (nichts wird ueberschrieben)."""
import pathlib
import sys

from components.i18n import t

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "daten"
REPORT_DIR = ROOT / "berichte"
DECK_DIR = ROOT / "decks"  # eigene Decklisten (z. B. _normaldeck.txt), im Git
POOL_FILES = ("_livedraft.txt", "_draftedcardpool.txt")  # Kartenpools des Drafthelpers, liegen in daten


def deck_file(path):
    """Deckliste: der Pfad wie angegeben, sonst ein blosser Name im Ordner decks; fehlt beides, bleibt der Pfad."""
    p = pathlib.Path(path)
    if not p.exists() and p.parent == pathlib.Path(".") and (DECK_DIR / p).is_file():
        return DECK_DIR / p
    return path


def move_pools():
    """Verschiebt die Kartenpools (POOL_FILES) aus dem Projektordner nach daten, wenn es dort noch keine gibt.
    Gibt die Zahl der verschobenen Dateien zurueck."""
    moved = 0
    for name in POOL_FILES:
        src, target = ROOT / name, DATA_DIR / name
        if not src.is_file() or target.exists():
            continue
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            src.replace(target)
        except OSError:
            continue
        moved += 1
    return moved


def _in(folder, name):
    p = pathlib.Path(name)
    if p.is_absolute() or p.parent != pathlib.Path("."):
        return p
    folder.mkdir(parents=True, exist_ok=True)
    return folder / p


def data_file(name):
    """JSON-Datei: ein blosser Name liegt in daten (Ordner wird bei Bedarf angelegt)."""
    return _in(DATA_DIR, name)


def report_file(name):
    """HTML-Bericht: ein blosser Name liegt in berichte (Ordner wird bei Bedarf angelegt)."""
    return _in(REPORT_DIR, name)


def beside(pool_file, suffix):
    """Begleitdatei einer Pool-Datei (z. B. _sideboard.json): liegt der Pool im Projektordner, kommt sie nach daten,
    sonst neben den Pool."""
    pool_file = pathlib.Path(pool_file)
    name = pool_file.stem + suffix
    if pool_file.resolve().parent == ROOT:
        return data_file(name)
    return pool_file.with_name(name)


def tidy_up():
    """Verschiebt *.json nach daten und *.html nach berichte, soweit sie noch im Projektordner liegen und es im
    Zielordner keine gleichnamige Datei gibt. Gibt die Zahl der verschobenen Dateien zurueck."""
    moved = 0
    for pattern, folder in (("*.json", DATA_DIR), ("*.html", REPORT_DIR)):
        for f in sorted(ROOT.glob(pattern)):
            target = folder / f.name
            if not f.is_file() or target.exists():
                continue
            folder.mkdir(parents=True, exist_ok=True)
            try:
                f.replace(target)
            except OSError:
                continue
            moved += 1
    if moved:
        print(t("{n} Dateien aufgeräumt: JSON-Dateien liegen jetzt im Ordner daten, HTML-Berichte im Ordner "
                "berichte.", n=moved), file=sys.stderr)
    return moved
