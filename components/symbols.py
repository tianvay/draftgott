"""Original-Manasymbole von Scryfall (SVG) fuer Bericht und Drafthelper.

fetch_symbols(refresh=False) -> {Symbol: SVG-Text}, z. B. {"R": "<svg ...>", "2/W": ...}. Liest scryfall_symbols.json
    neben mtg_sim.py; fehlt die Datei (oder refresh), werden alle Symbole aus Manakosten einmal von Scryfall geladen
    (api.scryfall.com/symbology, Bilder von svgs.scryfall.io). Ohne Netz bleibt es beim Rueckfall (farbige Kreise).
Die Symbole werden als CSS-Klassen mit eingebetteten Bildern in die HTML-Seiten geschrieben (symbol_css), damit
gespeicherte Berichte auch offline die Originalsymbole zeigen. Die Symbole gehoeren Wizards of the Coast.
"""
import base64
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

SYMBOL_FILE = pathlib.Path(__file__).resolve().parent.parent / "scryfall_symbols.json"
SYMBOLOGY_URL = "https://api.scryfall.com/symbology"
HEADERS = {"User-Agent": "mtg-sim/4.0", "Accept": "*/*"}
PAUSE = 0.06  # Scryfall bittet um kurze Pausen zwischen Anfragen

_active = None   # {Symbol: SVG}; None = noch nicht aus der Datei gelesen
_used = set()    # in dieser Seite benutzte Symbole (fuer das CSS des Berichts)


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=20) as r:
        return r.read()


def _read_file():
    try:
        data = json.loads(SYMBOL_FILE.read_text(encoding="utf-8"))
        return {k: v for k, v in data.items() if isinstance(v, str) and v.lstrip().startswith("<")}
    except (OSError, ValueError, AttributeError):
        return {}


def fetch_symbols(refresh=False):
    """Laedt die Symbole (Cache oder Scryfall), setzt sie als aktiv und gibt sie zurueck."""
    have = {} if refresh else _read_file()
    if have:
        use(have)
        return have
    try:
        listing = json.loads(_get(SYMBOLOGY_URL))
        out = {}
        for s in listing.get("data", []):
            if not s.get("appears_in_mana_costs") or s.get("funny") or not s.get("svg_uri"):
                continue
            key = s["symbol"].strip("{}")
            time.sleep(PAUSE)
            out[key] = _get(s["svg_uri"]).decode("utf-8")
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"Manasymbole konnten nicht geladen werden ({e}); es werden einfache Symbole gezeigt.", file=sys.stderr)
        old = _read_file()
        use(old)
        return old
    try:
        SYMBOL_FILE.write_text(json.dumps(out), encoding="utf-8")
    except OSError as e:
        print(f"Symbol-Cache konnte nicht gespeichert werden: {e}", file=sys.stderr)
    use(out)
    return out


def use(symbols):
    global _active
    _active = dict(symbols or {})


def active():
    global _active
    if _active is None:
        _active = _read_file()
    return dict(_active)


def has(sym):
    return sym in active()


def css_class(sym):
    return "ms-" + re.sub(r"[^A-Za-z0-9]", "_", sym)


def mark_used(sym):
    _used.add(sym)


def used():
    return set(_used)


def reset_used():
    _used.clear()


def symbol_css(keys):
    """CSS mit eingebetteten Bildern fuer die gewuenschten Symbole (nur vorhandene)."""
    syms = active()
    rules = []
    for key in sorted(k for k in keys if k in syms):
        data = base64.b64encode(syms[key].encode("utf-8")).decode("ascii")
        rules.append(f'.{css_class(key)}{{background-image:url("data:image/svg+xml;base64,{data}")}}')
    if not rules:
        return ""
    return ("\n.m.ms{display:inline-block;background-color:transparent;background-size:contain;background-repeat:no-repeat;"
            "background-position:center;min-width:0;width:18px;height:18px;padding:0;border:0;box-shadow:none;"
            "border-radius:50%;vertical-align:-3px;color:transparent;text-shadow:none;font-size:0}\n"
            + "\n".join(rules) + "\n")
