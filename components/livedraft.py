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
from components import draftstats
from components import gamestate
from components import signals
from components import tricks
from components.cardkinds import FLOW_ORDER, flow_kinds
from components.cards import land_produced
from components.removal import removal_info
from components.deckfile import parse_pool
from components.scryfall import CACHE_FILE, card_image_url, fetch_cards_cached

DRAFT_PICKS = 42  # 3 Packs zu 14 Karten: danach ist der Draft fertig (auch ohne Deck aus Arena)
DECK_MATCH = 0.8  # so viel des Arena-Decks (ohne Standardlaender) muss aus den Picks stammen

DETAILED_LOGS = ("In Arena unter Optionen → Konto „Detailed Logs (Plugin Support)“ einschalten und Arena neu "
                 "starten.")


def card_summary(sc, name, set_code="", number=""):
    """Kartendaten fuer Pack, Picks und Set-Ansicht aus einer Scryfall-Karte (fehlt sie: nur der Name)."""
    sc = sc or {}
    faces = sc.get("card_faces") or []
    type_line = sc.get("type_line") or ""
    image = card_image_url(sc) if sc else None
    front = type_line.split(" // ")[0].split("—")[0]
    land = "Land" in front
    return {"name": name, "set": (set_code or sc.get("set") or "").upper(),
            "number": number or sc.get("collector_number") or "",
            "image": image, "large": image.replace("/normal/", "/large/") if image else None,
            "colors": sc.get("colors") or (faces[0].get("colors") if faces else None) or [],
            "cost": sc.get("mana_cost") or (faces[0].get("mana_cost") if faces else "") or "",
            "mv": sc.get("cmc") or 0, "type": type_line, "rarity": sc.get("rarity") or "",
            "land": land, "found": bool(sc), "creature": "Creature" in front,
            "removal": (removal_info(sc) or {}).get("points", 0) if sc else 0,
            "flow": [k for k in FLOW_ORDER if k in set(flow_kinds(sc))] if sc else [],
            "produces": land_produced(sc) if sc and land else []}


def pool_info(cards, main):
    """Kennzahlen der Picks: Karten, Kreaturen, Removal (Karten und Punkte wie im Bericht), Kartenfluss (Karten und
    je Art). "arch": dieselben Zahlen nur fuer Karten in den Farben des Archetyps main (farblose zaehlen mit)."""
    def count(cs):
        kinds = {}
        for c in cs:
            for k in c.get("flow") or []:
                kinds[k] = kinds.get(k, 0) + 1
        return {"cards": len(cs), "creatures": sum(1 for c in cs if c.get("creature")),
                "removal": sum(1 for c in cs if c.get("removal")),
                "removal_points": round(sum(c.get("removal") or 0 for c in cs), 2),
                "flow": sum(1 for c in cs if c.get("flow")), "flow_kinds": kinds}
    out = count(cards)
    out["arch"] = count([c for c in cards if set(c.get("colors") or []) <= set(main)]) if main else None
    return out


TOP_RATINGS = ("matchwinner",)  # Bomben: nur Matchwinner


def deck_summary(cards, ratings, source):
    """Kurze Deck-Uebersicht nach dem Draft (wie auf der Drafthelper-Seite). cards: Kartenangaben mit "qty";
    source: "arena" (in Arena abgegebenes Hauptdeck) oder "picks" (noch kein Deck, alle Picks). curve: Zauber je
    Manawert <=1, 2, 3, 4, 5, 6+; colors: Zauber je Farbe (mehrfarbige zaehlen fuer jede); top: die Bomben (eigene
    Bewertung Matchwinner), hoechstens drei."""
    ratings = ratings or {}
    spells = [c for c in cards if not c.get("land")]
    n = sum(c.get("qty", 1) for c in spells)
    curve = [0] * 6
    colors = {}
    for c in spells:
        q = c.get("qty", 1)
        curve[min(5, max(0, int(c.get("mv") or 0) - 1))] += q
        for col in c.get("colors") or []:
            colors[col] = colors.get(col, 0) + q
    top = sorted({c["name"] for c in spells if ratings.get(c["name"]) in TOP_RATINGS},
                 key=lambda name: (TOP_RATINGS.index(ratings[name]), name))[:3]
    return {"source": source, "cards": sum(c.get("qty", 1) for c in cards), "lands": sum(c.get("qty", 1) for c in cards if c.get("land")), "spells": n,
            "avg_mv": round(sum((c.get("mv") or 0) * c.get("qty", 1) for c in spells) / n, 2) if n else 0,
            "curve": curve,
            "creatures": sum(c.get("qty", 1) for c in spells if c.get("creature")),
            "removal": sum(c.get("qty", 1) for c in spells if c.get("removal")),
            "removal_points": round(sum((c.get("removal") or 0) * c.get("qty", 1) for c in spells), 2),
            "flow": sum(c.get("qty", 1) for c in spells if c.get("flow")),
            "colors": dict(sorted(colors.items(), key=lambda kv: (-kv[1], "WUBRG".find(kv[0])))),
            "top": top}


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


def rebuild_stats(args):
    """--statistik-neu: Draft-Statistik aus Player-prev.log und Player.log neu aufbauen (Sicherung der alten Datei)."""
    root = pathlib.Path(__file__).resolve().parent.parent
    path = pathlib.Path(args.statistik)
    path = path if path.is_absolute() else root / path
    log = pathlib.Path(args.arena_log) if args.arena_log else arenalog.default_log_path()
    names = default_names(log)

    def lookup(grp):
        return (names.get(grp) or {}).get("name")

    def set_lookup(grp):
        return (names.get(grp) or {}).get("set")

    backup = draftstats.rebuild(path, [log.with_name("Player-prev.log"), log], lookup, set_lookup)
    data = draftstats.load_stats(path)
    print(f"Draft-Statistik neu aufgebaut: {path} ({len(data['drafts'])} Drafts)"
          + (f", alte Datei gesichert als {backup.name}" if backup else ""), file=sys.stderr)


class LiveDraft:
    def __init__(self, log_path, pool_file, names=None, fetch=fetch_cards_cached, stats=None, enemy_dir=None,
                 fetch_set=None):
        """stats: Pfad der Draft-Statistik (components/draftstats.py) oder None (keine Statistik); enemy_dir: Ordner
        fuer Decks mit 4 Siegen (Gegnerdecks); fetch_set: alle Karten eines Sets fuer die Tricks im Spiel (z. B.
        scryfall.fetch_set_cards; None: keine Tricks)."""
        self.log_path, self.pool_file = pathlib.Path(log_path), pathlib.Path(pool_file)
        self.tracker = draftstats.Tracker(stats, self._lookup, self._set_lookup, enemy_dir=enemy_dir,
                                          card_info=self._card_info) if stats else None
        self._names, self.fetch = names, fetch
        self.follower = arenalog.LogFollower(log_path)
        self.state = arenalog.DraftState()
        self.cards = {}  # Name -> card_summary
        self.version = 0  # steigt mit jedem Schreiben der Pool-Datei
        self.lock = threading.Lock()
        self._written = None
        self.game = gamestate.GameState()  # laufendes Spiel (Ziehchancen)
        self.deck = None  # zuletzt in Arena abgegebenes Deck eines Draft-Events {"main", "side"} (GrpId -> Anzahl)
        self.seen = set()  # Arena-Nummern aller Karten, die in Packs dieses Programmlaufs zu sehen waren
        self.fetch_set = fetch_set
        self.tricks = {}  # Setcode -> Tricks des Sets (components/tricks.py)

    def _card_info(self, grp):
        """Name, Set, Nummer und Farben (Scryfall, sonst ohne Farben) fuer die Gegnerdeck-Datei."""
        info = self.names().get(grp)
        if not info:
            return None
        if info["name"] not in self.cards:
            self._load_cards([grp])
        card = self.cards.get(info["name"]) or {}
        return dict(info, colors=card.get("colors") or [], cost=card.get("cost") if card.get("found") else None)

    def _set_lookup(self, grp):
        info = self.names().get(grp)
        return info["set"] if info else None

    def _lookup(self, grp):
        info = self.names().get(grp)
        return info["name"] if info else None

    def read_previous(self, path):
        """Statistik: die vorherige Protokolldatei (Player-prev.log) einmal nachlesen, damit Matches aus der
        letzten Arena-Sitzung nicht fehlen. Der Live-Stand (Pack, Pool-Datei) bleibt davon unberuehrt."""
        if not self.tracker:
            return
        try:
            text = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        own_state, self.tracker.state = self.tracker.state, arenalog.DraftState()
        for line in text.split("\n"):
            self.tracker.feed_line(line)
        self.tracker.state = own_state

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

    def _lines(self, counts):
        """Zeilen "Anzahl Name (SET) Nummer" fuer [(GrpId, Anzahl)] in dieser Reihenfolge, gleiche Drucke zusammen."""
        count, first = Counter(), {}
        for grp, qty in counts:
            info = self.names().get(grp)
            if not info:
                continue
            key = (info["name"], info["set"], info["number"])
            count[key] += qty
            first.setdefault(key, len(first))
        return [f"{count[k]} {k[0]}" + (f" ({k[1]}) {k[2]}" if k[1] and k[2] else "") for k in sorted(count, key=first.get)]

    def _save(self, text):
        tmp = self.pool_file.with_name(self.pool_file.name + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(self.pool_file)
        self.version += 1

    def _same_cards(self):
        """Enthaelt die Pool-Datei schon genau die Picks (z. B. als uebernommenes Deck mit Sideboard)?"""
        try:
            rows = parse_pool(self.pool_file.read_text(encoding="utf-8"))
        except OSError:
            return False
        have = Counter()
        for r in rows:
            if r["name"] not in draftstats.BASICS:
                have[r["name"]] += r["qty"]
        want = Counter(c["name"] for c in (self._card(g) for g in self.state.picks) if c)
        return bool(want) and have == want

    def _write_pool(self):
        if self._same_cards():  # nicht mit der einfachen Pick-Liste ueberschreiben
            return
        self._save("\n".join(["Deck"] + self._lines((g, 1) for g in self.state.picks)) + "\n")

    def _deck_valid(self):
        """Gehoert das zuletzt abgegebene Deck zum laufenden Draft? Ohne mitgelesene Picks: ja, ausser es liegt schon
        ein Pack an (erster Pick eines neuen Drafts, das Deck ist dann vom vorigen)."""
        if not self.deck:
            return False
        names = Counter()
        for part in ("main", "side"):
            for grp, qty in self.deck[part].items():
                info = self.names().get(grp)
                if info and info["name"] not in draftstats.BASICS:
                    names[info["name"]] += qty
        if not self.state.picks:
            return bool(names) and not self.state.pack
        picks = Counter(c["name"] for c in (self._card(g) for g in self.state.picks) if c)
        total = sum(names.values())
        return total > 0 and sum((names & picks).values()) >= DECK_MATCH * total

    def _deck_text(self):
        return ("\n".join(["Deck"] + self._lines(self.deck["main"].items()) + ["", "Sideboard"]
                          + self._lines(self.deck["side"].items())) + "\n")

    def _deck_info(self):
        if not self._deck_valid():
            return {"ready": False, "main": 0, "side": 0, "applied": False}
        try:
            applied = self.pool_file.read_text(encoding="utf-8") == self._deck_text()
        except OSError:
            applied = False
        return {"ready": True, "main": sum(self.deck["main"].values()), "side": sum(self.deck["side"].values()),
                "applied": applied}

    def apply_deck(self):
        """Schreibt das in Arena abgegebene Deck (Abschnitte Deck und Sideboard) in die Pool-Datei; ValueError, wenn
        es noch keines gibt (in Arena den Deckbau mit "Fertig" abschliessen)."""
        with self.lock:
            if not self._deck_valid():
                raise ValueError("Noch kein Deck aus Arena: In Arena den Deckbau mit „Fertig“ abschließen, dann "
                                 "erscheint es hier.")
            self._save(self._deck_text())

    def step(self):
        """Liest neue Protokollzeilen; True, wenn sich Pack oder Picks geaendert haben."""
        changed = game_changed = False
        for line in self.follower.poll():
            if self.game.feed_line(line):
                game_changed = True
                continue
            if self.tracker:
                try:
                    self.tracker.feed_line(line)
                except OSError as e:  # Statistik nicht speicherbar: Live-Draft laeuft weiter
                    print(f"Draft-Statistik nicht gespeichert: {e}", file=sys.stderr)
            for ev in arenalog.scan_line(line):
                with self.lock:
                    changed = self.state.feed(ev) or changed
                    if ev["kind"] == "pack":
                        self.seen.update(ev["cards"])
            for ev in arenalog.scan_match_line(line):
                if ev["kind"] == "deck" and draftstats.is_limited(ev["event"]):
                    deck = {"main": ev["main"], "side": ev["side"]}
                    if deck != self.deck:
                        with self.lock:
                            self.deck = deck
                        changed = True
        if game_changed:
            self._load_cards(list(self.game.deck) + [x["grp"] for x in self.game.opponent_lands()])
            if self.game.active:
                self._load_tricks()
        if not changed:
            return game_changed
        self._load_cards(self.state.pack + self.state.picks + list((self.deck or {}).get("main", {}))
                         + list((self.deck or {}).get("side", {})))
        with self.lock:
            if (self.state.draft or self.state.event) and self.state.picks != self._written:
                self._write_pool()
                self._written = list(self.state.picks)
        return True

    def _game_set(self):
        """Setcode fuer die Tricks: aus dem Event, sonst das haeufigste Set des eigenen Decks; klein geschrieben."""
        code = self._set_code([c for c in (self._card(g) for g in self.game.deck) if c])
        return code.lower() if code else None

    def _load_tricks(self):
        """Tricks des Sets einmal laden (Scryfall-Set-Cache, sonst Netz); ohne Daten bleibt die Liste leer."""
        code = self._game_set()
        if not code or code in self.tricks or self.fetch_set is None:
            return
        try:
            cards = self.fetch_set(code) or []
        except (urllib.error.URLError, OSError, ValueError) as e:
            print(f"Set {code.upper()} fuer die Tricks nicht geladen: {e}", file=sys.stderr)
            cards = []
        with self.lock:
            self.tricks[code] = tricks.trick_cards(cards)

    def _tricks_view(self, ratings):
        if not self.game.active:
            return None
        code = self._game_set()
        if code not in self.tricks:
            return None
        view = tricks.tricks_view(self.game, self._card, self.tricks[code])
        for part in ("now", "next"):
            view[part] = [dict(t, rating=(ratings or {}).get(t["name"], "")) for t in view[part]]
        return view

    def start(self, interval=1.0):
        def loop():
            while True:
                try:
                    self.step()
                except Exception:  # weiterlesen; Details ins Terminal
                    traceback.print_exc()
                time.sleep(interval)
        threading.Thread(target=loop, daemon=True).start()

    def _saved(self):
        return self.tracker.last_saved if self.tracker else None

    def known_names(self):
        with self.lock:
            return {c["name"] for c in (self._card(g) for g in self.seen | set(self.state.picks)) if c}

    def _set_code(self, cards):
        code = arenalog.set_from_event(self.state.event)
        if code:
            return code
        count = Counter(c["set"] for c in cards if c.get("set"))
        return count.most_common(1)[0][0] if count else None

    def snapshot(self, ratings, assign, manual, cardstats=None):
        """Stand fuer die Seite und das Seitenfenster (siehe Modulbeschreibung); cardstats: Zahlen je Karte aus der
        Draft-Statistik, sie kommen als "stats" an die Pack-Karten."""
        with self.lock:
            game = gamestate.game_view(self.game, {g: self._card(g) for g in self.game.deck if self._card(g)})
            if game.get("active"):
                game["tricks"] = self._tricks_view(ratings)
            if not self.log_path.exists():
                return {"status": "nolog", "version": self.version,
                        "message": f"Arena-Protokoll nicht gefunden: {self.log_path}. {DETAILED_LOGS}"}
            if not (self.state.draft or self.state.event):
                return {"status": "idle", "version": self.version, "game": game, "enemy_saved": self._saved(),
                        "message": "Noch kein Draft im Protokoll – starte einen Draft in Arena. Erscheint auch dann "
                                   "nichts: " + DETAILED_LOGS}
            pack = [c for c in (self._card(g) for g in self.state.pack) if c]
            picks = [c for c in (self._card(g) for g in self.state.picks) if c]
            unknown = [g for g in self.state.pack + self.state.picks if g not in self.names()]
            waiting, n_picks, event = self.state.waiting, len(self.state.picks), self.state.event
            deck = self._deck_info()
            main_deck = [(g, q) for g, q in self.deck["main"].items()] if deck["ready"] else None
            draft_id = self.state.draft
            sig = signals.analyze([dict(h) for h in self.state.history], self._card, ratings, event)
        code = self._set_code(pack + picks)
        found = set_archetypes.for_set(code)
        detect = cardarchetypes.detect([dict(c, qty=1) for c in picks], assign, ratings, found, manual)
        draftinfo = pool_info(picks, detect["main"])
        archmap = cardarchetypes.archetype_map(found, assign, [c["name"] for c in picks],
                                               [c["name"] for c in cardarchetypes.rank(pack, ratings, assign,
                                                                                      detect["main"])])
        ranked = cardarchetypes.rank(pack, ratings, assign, detect["main"])
        for c in ranked:
            c["stats"] = (cardstats or {}).get(c["name"])
        names = {c["name"] for c in pack + picks}
        complete = deck["ready"] or n_picks >= DRAFT_PICKS
        deckinfo = None
        if complete:
            if main_deck is not None:
                cards = [dict(c, qty=q) for c, q in ((self._card(g), q) for g, q in main_deck) if c]
                deckinfo = deck_summary(cards, ratings, "arena")
            else:
                deckinfo = deck_summary([dict(c, qty=1) for c in picks], ratings, "picks")
            deckinfo["record"] = self.tracker.record(draft_id, event) if self.tracker else None
            names |= {c["name"] for c in (self._card(g) for g, _ in main_deck or []) if c}
        return {"status": "waiting" if waiting or not pack else "pack", "version": self.version, "message": "",
                "event": event or "", "set": code or "", "pick": n_picks + 1, "pack": ranked,
                "picks": [c["name"] for c in picks], "unknown": unknown, "detect": detect,
                "deck": deck, "complete": complete, "deckinfo": deckinfo, "game": game,
                "draftinfo": draftinfo, "archmap": archmap, "enemy_saved": self._saved(), "signals": sig,
                "archetypes": found,
                "cardarch": {n: v for n, v in (assign or {}).items() if n in names},
                "ratings": {n: v for n, v in (ratings or {}).items() if n in names}}
