"""Live-Draft fuer den Drafthelper (--live): liest das Arena-Protokoll mit (components/arenalog.py), schreibt die
Picks in die Pool-Datei (Format wie der Deck-Export von Arena) und bewertet das aktuelle Pack nach Kartenbewertung
und Archetyp (components/cardarchetypes.py). Der Drafthelper zeigt den Stand auf seiner Seite und im Seitenfenster
(components/overlay.py)."""
import json
import pathlib
import sys
import threading
import time
import traceback
import urllib.error
from collections import Counter

from components import arenalog
from components import archetypes as set_archetypes
from components import cardarchetypes
from components.scryfall import CACHE_FILE, card_image_url, fetch_cards_cached

DETAILED_LOGS = ("In Arena unter Optionen → Konto „Detailed Logs (Plugin Support)“ einschalten und Arena neu "
                 "starten.")


def card_summary(sc, name, set_code="", number=""):
    """Kartendaten fuer Pack, Picks und Set-Ansicht aus einer Scryfall-Karte (fehlt sie: nur der Name)."""
    sc = sc or {}
    faces = sc.get("card_faces") or []
    type_line = sc.get("type_line") or ""
    image = card_image_url(sc) if sc else None
    return {"name": name, "set": (set_code or sc.get("set") or "").upper(),
            "number": number or sc.get("collector_number") or "",
            "image": image, "large": image.replace("/normal/", "/large/") if image else None,
            "colors": sc.get("colors") or (faces[0].get("colors") if faces else None) or [],
            "cost": sc.get("mana_cost") or (faces[0].get("mana_cost") if faces else "") or "",
            "mv": sc.get("cmc") or 0, "type": type_line, "rarity": sc.get("rarity") or "",
            "land": "Land" in type_line.split("—")[0], "found": bool(sc)}


def default_names(log_path):
    """{GrpId: Name, Set, Nummer}: Arenas Kartendatenbank (Ordner aus dem Protokoll), ergaenzt um die arena_id aus
    dem Scryfall-Cache."""
    head = ""
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
            head = fh.read(200000)
    except OSError:
        pass
    names = {}
    try:
        names.update(arenalog.scryfall_names(json.loads(CACHE_FILE.read_text(encoding="utf-8"))))
    except (OSError, ValueError):
        pass
    db = arenalog.find_card_db(arenalog.install_dirs(head))
    if db:
        names.update(arenalog.load_card_db(db))
    print(f"Arena-Kartendatenbank: {db or 'nicht gefunden'} ({len(names)} Karten bekannt)", file=sys.stderr)
    return names


class LiveDraft:
    def __init__(self, log_path, pool_file, names=None, fetch=fetch_cards_cached):
        self.log_path, self.pool_file = pathlib.Path(log_path), pathlib.Path(pool_file)
        self._names, self.fetch = names, fetch
        self.follower = arenalog.LogFollower(log_path)
        self.state = arenalog.DraftState()
        self.cards = {}  # Name -> card_summary
        self.version = 0  # steigt mit jedem Schreiben der Pool-Datei
        self.lock = threading.Lock()
        self._written = None
        self.seen = set()  # Arena-Nummern aller Karten, die in Packs dieses Programmlaufs zu sehen waren

    def names(self):
        if self._names is None:
            self._names = default_names(self.log_path)
        return self._names

    def _card(self, grp):
        info = self.names().get(grp)
        if not info:
            return None
        return self.cards.get(info["name"]) or card_summary(None, info["name"], info["set"], info["number"])

    def _load_cards(self, ids):
        """Scryfall-Daten fuer neue Karten (Cache, sonst Netz); ohne Netz bleiben Name, Set und Nummer."""
        todo = {}
        for grp in ids:
            info = self.names().get(grp)
            if info and info["name"] not in self.cards:
                todo[info["name"]] = info
        if not todo:
            return
        try:
            data = self.fetch(sorted(todo))
        except (urllib.error.URLError, OSError, ValueError) as e:
            print(f"Scryfall nicht erreichbar: {e}", file=sys.stderr)
            data = None
        for name, info in todo.items():
            sc = None if data is None else (data.get(name) or data.get(name.split(" // ")[0]))
            if data is not None or name not in self.cards:
                self.cards[name] = card_summary(sc, name, info["set"], info["number"])

    def _write_pool(self):
        count, first = Counter(), {}
        for grp in self.state.picks:
            info = self.names().get(grp)
            if not info:
                continue
            key = (info["name"], info["set"], info["number"])
            count[key] += 1
            first.setdefault(key, len(first))
        lines = ["Deck"]
        for key in sorted(count, key=first.get):
            name, code, number = key
            lines.append(f"{count[key]} {name}" + (f" ({code}) {number}" if code and number else ""))
        tmp = self.pool_file.with_name(self.pool_file.name + ".tmp")
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        tmp.replace(self.pool_file)
        self.version += 1

    def step(self):
        """Liest neue Protokollzeilen; True, wenn sich Pack oder Picks geaendert haben."""
        changed = False
        for line in self.follower.poll():
            for ev in arenalog.scan_line(line):
                with self.lock:
                    changed = self.state.feed(ev) or changed
                    if ev["kind"] == "pack":
                        self.seen.update(ev["cards"])
        if not changed:
            return False
        self._load_cards(self.state.pack + self.state.picks)
        with self.lock:
            if (self.state.draft or self.state.event) and self.state.picks != self._written:
                self._write_pool()
                self._written = list(self.state.picks)
        return True

    def start(self, interval=1.0):
        def loop():
            while True:
                try:
                    self.step()
                except Exception:  # weiterlesen; Details ins Terminal
                    traceback.print_exc()
                time.sleep(interval)
        threading.Thread(target=loop, daemon=True).start()

    def known_names(self):
        with self.lock:
            return {c["name"] for c in (self._card(g) for g in self.seen | set(self.state.picks)) if c}

    def _set_code(self, cards):
        code = arenalog.set_from_event(self.state.event)
        if code:
            return code
        count = Counter(c["set"] for c in cards if c.get("set"))
        return count.most_common(1)[0][0] if count else None

    def snapshot(self, ratings, assign, manual):
        """Stand fuer die Seite und das Seitenfenster (siehe Modulbeschreibung)."""
        with self.lock:
            if not self.log_path.exists():
                return {"status": "nolog", "version": self.version,
                        "message": f"Arena-Protokoll nicht gefunden: {self.log_path}. {DETAILED_LOGS}"}
            if not (self.state.draft or self.state.event):
                return {"status": "idle", "version": self.version,
                        "message": "Noch kein Draft im Protokoll – starte einen Draft in Arena. Erscheint auch dann "
                                   "nichts: " + DETAILED_LOGS}
            pack = [c for c in (self._card(g) for g in self.state.pack) if c]
            picks = [c for c in (self._card(g) for g in self.state.picks) if c]
            unknown = [g for g in self.state.pack + self.state.picks if g not in self.names()]
            waiting, n_picks, event = self.state.waiting, len(self.state.picks), self.state.event
        code = self._set_code(pack + picks)
        found = set_archetypes.for_set(code)
        detect = cardarchetypes.detect([dict(c, qty=1) for c in picks], assign, ratings, found, manual)
        ranked = cardarchetypes.rank(pack, ratings, assign, detect["main"])
        names = {c["name"] for c in pack + picks}
        return {"status": "waiting" if waiting or not pack else "pack", "version": self.version, "message": "",
                "event": event or "", "set": code or "", "pick": n_picks + 1, "pack": ranked,
                "picks": [c["name"] for c in picks], "unknown": unknown, "detect": detect,
                "archetypes": found,
                "cardarch": {n: v for n, v in (assign or {}).items() if n in names},
                "ratings": {n: v for n, v in (ratings or {}).items() if n in names}}
