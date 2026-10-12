"""
Scryfall-Zugriff fuer mtg_sim.py: Kartendaten holen und lokal zwischenspeichern.

Oeffentliche Funktionen:
    fetch_cards(names)                       -> {name: scryfall_card}, direkt von der API (75 Karten pro Anfrage)
    fetch_cards_cached(names, refresh=False) -> wie fetch_cards, laedt aber nur Karten nach, die noch nicht im
                                                Cache (scryfall_cache.json neben mtg_sim.py) stehen
    fetch_printing_images(specs)             -> {"set/nummer": Bild-URL} fuer bestimmte Drucke (Draft-Helper),
                                                Cache: scryfall_images_cache.json
"""
import json
import pathlib
import sys
import urllib.error
import urllib.request

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "mtg-sim/4.0",
    "Accept": "application/json",
}


def post_collection(identifiers):
    req = urllib.request.Request(
        "https://api.scryfall.com/cards/collection",
        data=json.dumps({"identifiers": identifiers}).encode(),
        headers=HEADERS,
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def fetch_cards(names):
    """Holt Kartendaten (75 pro Anfrage). Gibt {name: scryfall_card} zurueck."""
    found = {}

    def store(card):
        found[card["name"]] = card
        found[card["name"].split(" // ")[0]] = card

    names = list(names)
    for i in range(0, len(names), 75):
        data = post_collection([{"name": n} for n in names[i:i + 75]])
        for card in data["data"]:
            store(card)
        missing = [d["name"] for d in data.get("not_found", [])]
        if missing:  # Fallback: nur Vorderseite
            retry = post_collection([{"name": n.split(" // ")[0]} for n in missing])
            for card in retry["data"]:
                store(card)
            for d in retry.get("not_found", []):
                print(f"WARNUNG: Karte nicht gefunden: {d['name']}", file=sys.stderr)
    return found


CACHE_FILE = pathlib.Path(__file__).resolve().parent.parent / "scryfall_cache.json"


def fetch_cards_cached(names, refresh=False):
    """Wie fetch_cards, merkt sich aber alle Karten in scryfall_cache.json neben dem Script.
    Es werden nur Karten nachgeladen, die noch nicht im Cache stehen."""
    cache = {}
    if not refresh and CACHE_FILE.exists():
        try:
            cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cache = {}
    todo = [n for n in names if n not in cache and n.split(" // ")[0] not in cache]
    if todo:
        fresh = fetch_cards(todo)
        cache.update(fresh)
        try:
            CACHE_FILE.write_text(json.dumps(cache), encoding="utf-8")
        except OSError as e:
            print(f"Cache konnte nicht gespeichert werden: {e}", file=sys.stderr)
    else:
        print("Alle Karten aus dem Cache.", file=sys.stderr)
    return cache


IMAGE_CACHE_FILE = pathlib.Path(__file__).resolve().parent.parent / "scryfall_images_cache.json"


def card_image_url(card):
    """Bild-URL (Format 'normal') einer Scryfall-Karte, bei zweiseitigen Karten die Vorderseite."""
    uris = card.get("image_uris") or ((card.get("card_faces") or [{}])[0].get("image_uris")) or {}
    return uris.get("normal")


def fetch_printing_images(specs):
    """specs: [(set, sammlernummer)]. Gibt {"set/nummer": Bild-URL} zurueck (nicht gefundene fehlen).
    Merkt sich die URLs in scryfall_images_cache.json; Netzwerkfehler brechen nicht ab, dann fehlen die Bilder."""
    cache = {}
    if IMAGE_CACHE_FILE.exists():
        try:
            cache = json.loads(IMAGE_CACHE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cache = {}
    todo = [(s_, n) for s_, n in dict.fromkeys(specs) if f"{s_}/{n}" not in cache]
    for i in range(0, len(todo), 75):
        try:
            data = post_collection([{"set": s_, "collector_number": n} for s_, n in todo[i:i + 75]])
        except urllib.error.URLError as e:
            print(f"Kartenbilder konnten nicht geladen werden: {e}", file=sys.stderr)
            break
        for card in data.get("data", []):
            url = card_image_url(card)
            if url:
                cache[f"{card['set']}/{card['collector_number']}"] = url
    if todo:
        try:
            IMAGE_CACHE_FILE.write_text(json.dumps(cache), encoding="utf-8")
        except OSError as e:
            print(f"Bild-Cache konnte nicht gespeichert werden: {e}", file=sys.stderr)
    return {k: v for k, v in cache.items() if k in {f"{s_}/{n}" for s_, n in specs}}
