"""MTG Arena: Packs und Picks eines Drafts aus dem Protokoll Player.log lesen (wie 17Lands oder Untapped).

Arena schreibt mit "Detailed Logs (Plugin Support)" (Arena-Einstellungen, Konto) alle Nachrichten an den Server in
die Datei. Gelesen wird nur diese Datei; das Spiel selbst wird nicht beruehrt.

Die Formate unterscheiden sich je Draft-Art und Arena-Version; erkannt werden daher die Felder, nicht die Zeilen:
  - Pack:   "PackCards" (Text "1,2,3", Draft mit Menschen), "DraftPack" (Quick Draft / Pick Two)
  - Pick:   "GrpIds", "GrpId", "CardIds", "CardId" oder "PickGrpId" zusammen mit einer Pack- oder Pick-Nummer,
            in einer Zeile mit "Pick" (Event_PlayerDraftMakePick, BotDraft_DraftPick, LogBusinessEvents); so
            zaehlen Deck-Skins ("GrpId") und Spielnachrichten ("CardId") nicht
  - Bisher gewaehlt: "PickedCards" (Quick Draft / Pick Two, gilt dann als vollstaendige Liste)
  - Draft-Kennung "draftId"/"DraftId", Event "EventName"/"EventId"/"InternalEventName"
Fuer die Draft-Statistik (scan_match_line):
  - eigene Kennung: "authenticateResponse" -> "clientId" bzw. Zeilen "Match to <Kennung>:"
  - Deck eines Events: "Deck" oder "CourseDeck" mit "MainDeck"/"Sideboard" ([{cardId, quantity}]) und Eventname
  - Match-Beginn: "reservedPlayers" (userId, teamId, eventId) mit "matchId"
  - Match-Ende: "finalMatchResult" mit "resultList" (je Game und fuer das Match das Siegerteam)
Eingebettetes JSON in Textfeldern ("request", "Payload") wird mit gelesen. Karten stehen als Arena-Nummern (GrpId)
drin; die Namen kommen aus Arenas Kartendatenbank (Raw_CardDatabase_*.mtga, SQLite) oder aus den arena_id von
Scryfall.
"""
import json
import os
import pathlib
import re
import sqlite3

PACK_KEYS = ("PackCards", "DraftPack")
PICK_KEYS = ("GrpIds", "GrpId", "CardIds", "CardId", "PickGrpId")
PICKED_KEYS = ("PickedCards",)
NUMBER_KEYS = ("Pick", "PickNumber", "SelfPick", "Pack", "PackNumber")  # ein Pick nennt immer Pack/Pick
DRAFT_KEYS = ("draftId", "DraftId")
EVENT_KEYS = ("EventName", "EventId", "InternalEventName")
_HINTS = ("Pack", "Pick", "Draft")  # schnelle Vorauswahl: nur solche Zeilen werden als JSON gelesen
_MATCH_HINTS = ("authenticateResponse", "MainDeck", "reservedPlayers", "finalMatchResult")
_MATCH_TO = re.compile(r"Match to ([A-Z0-9]{16,}):")
_DECODER = json.JSONDecoder()
INSTALL_DIRS = (  # uebliche Installationsorte (Rueckfall, wenn das Protokoll keinen Pfad nennt)
    "C:/Program Files/Wizards of the Coast/MTGA/MTGA_Data",
    "C:/Program Files (x86)/Wizards of the Coast/MTGA/MTGA_Data",
    "C:/Program Files (x86)/Steam/steamapps/common/MTGA/MTGA_Data",
    "C:/Program Files/Steam/steamapps/common/MTGA/MTGA_Data",
    "C:/Program Files/Epic Games/MagicTheGathering/MTGA_Data",
)


def default_log_path(home=None):
    """Pfad von Player.log unter Windows."""
    home = pathlib.Path(home) if home else pathlib.Path(os.path.expanduser("~"))
    return home / "AppData" / "LocalLow" / "Wizards Of The Coast" / "MTGA" / "Player.log"


def _ids(value):
    """Arena-Nummern aus einer Liste, einer Zahl oder einem Text "1,2,3"; [] wenn nichts Brauchbares drin ist."""
    if isinstance(value, bool):
        return []
    if isinstance(value, int):
        return [value]
    if isinstance(value, str):
        value = [v for v in value.split(",") if v.strip()]
    if not isinstance(value, list):
        return []
    out = []
    for v in value:
        if isinstance(v, bool):
            return []
        if isinstance(v, int):
            out.append(v)
        elif isinstance(v, str) and v.strip().isdigit():
            out.append(int(v.strip()))
        else:
            return []
    return out


def _json_values(line):
    """Alle JSON-Objekte einer Zeile (ab der ersten Klammer)."""
    i = line.find("{")
    if i < 0:
        return []
    try:
        obj, _ = _DECODER.raw_decode(line[i:])
    except ValueError:
        return []
    return [obj]


def _walk(obj):
    """Alle Woerterbuecher in obj, auch in eingebettetem JSON-Text."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)
    elif isinstance(obj, str) and obj[:1] in "{[":
        try:
            inner = json.loads(obj)
        except ValueError:
            return
        yield from _walk(inner)


def _first(dicts, keys):
    for d in dicts:
        for k in keys:
            v = d.get(k)
            if isinstance(v, str) and v:
                return v
    return None


def scan_line(line):
    """Draft-Ereignisse einer Protokollzeile: [{"kind": "pack"|"pick"|"picked", "cards", "draft", "event"}]."""
    if not line or not any(h in line for h in _HINTS):
        return []
    dicts = [d for obj in _json_values(line) for d in _walk(obj)]
    if not dicts:
        return []
    draft, event = _first(dicts, DRAFT_KEYS), _first(dicts, EVENT_KEYS)
    pick_line = "Pick" in line
    events = []
    for d in dicts:
        picked = None
        if pick_line and any(k in d for k in NUMBER_KEYS):
            for k in PICK_KEYS:
                if k in d and _ids(d[k]):
                    picked = _ids(d[k])
                    break
        if picked:  # ein Pick nennt oft auch das Pack, aus dem gewaehlt wurde: das ist kein neues Pack
            events.append({"kind": "pick", "cards": picked, "draft": draft, "event": event})
            continue
        for k in PACK_KEYS:
            if k in d and _ids(d[k]):
                events.append({"kind": "pack", "cards": _ids(d[k]), "draft": draft, "event": event})
                break
        for k in PICKED_KEYS:
            if k in d and isinstance(d[k], list) and (not d[k] or _ids(d[k])):
                events.append({"kind": "picked", "cards": _ids(d[k]), "draft": draft, "event": event})
                break
    return events


def _deck_counts(value):
    """{GrpId: Anzahl} aus [{"cardId", "quantity"}] oder None, wenn es keine solche Liste ist."""
    if not isinstance(value, list):
        return None
    out = {}
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("cardId"), int):
            return None
        q = item.get("quantity", 1)
        out[item["cardId"]] = out.get(item["cardId"], 0) + (q if isinstance(q, int) else 1)
    return out


def scan_match_line(line):
    """Ereignisse fuer die Draft-Statistik: [{"kind": "user"|"deck"|"match_start"|"match_end", ...}]
    (siehe Modulbeschreibung)."""
    if not line:
        return []
    m = _MATCH_TO.search(line)
    if m:
        return [{"kind": "user", "id": m.group(1)}]
    if not any(h in line for h in _MATCH_HINTS):
        return []
    dicts = [d for obj in _json_values(line) for d in _walk(obj)]
    if not dicts:
        return []
    events = []
    event = _first(dicts, EVENT_KEYS)
    for d in dicts:
        auth = d.get("authenticateResponse")
        if isinstance(auth, dict) and isinstance(auth.get("clientId"), str):
            events.append({"kind": "user", "id": auth["clientId"]})
        for key in ("Deck", "CourseDeck"):
            deck = d.get(key)
            if isinstance(deck, dict) and event:
                main = _deck_counts(deck.get("MainDeck"))
                if main is not None:
                    events.append({"kind": "deck", "event": event, "main": main,
                                   "side": _deck_counts(deck.get("Sideboard")) or {}})
        players = d.get("reservedPlayers")
        if isinstance(players, list) and isinstance(d.get("matchId"), str):
            found = [{"user": p.get("userId"), "team": p.get("teamId")} for p in players if isinstance(p, dict)]
            ev = next((p.get("eventId") for p in players if isinstance(p, dict) and p.get("eventId")), None)
            events.append({"kind": "match_start", "match": d["matchId"], "event": ev, "players": found})
        result = d.get("finalMatchResult")
        if isinstance(result, dict) and isinstance(result.get("matchId"), str):
            games, winner = [], None
            for r in result.get("resultList") or []:
                if not isinstance(r, dict):
                    continue
                if r.get("scope") == "MatchScope_Game":
                    games.append(r.get("winningTeamId"))
                elif r.get("scope") == "MatchScope_Match":
                    winner = r.get("winningTeamId")
            events.append({"kind": "match_end", "match": result["matchId"], "games": games, "winner": winner})
    return events


def set_from_event(name):
    """Setcode aus einem Eventnamen wie "PickTwoDraft_TRK_20261110" oder None."""
    m = re.search(r"_([A-Z0-9]{3})_", name or "")
    return m.group(1) if m else None


class DraftState:
    """Stand des laufenden Drafts: aktuelles Pack, alle Picks; ein neuer Draft (andere Kennung bzw. anderes Event)
    beginnt von vorn. Derselbe Pick aus zwei Zeilen (Anfrage und LogBusinessEvents) zaehlt einmal."""

    def __init__(self):
        self.draft = self.event = None
        self.pack, self.picks = [], []
        self.pick_sizes = []  # je Pick: Groesse des Packs, aus dem gewaehlt wurde (None: unbekannt)
        self.waiting = False
        self._packs = []  # [(Kartenmenge, schon gewaehlt?)] der gesehenen Packs, neueste zuletzt

    def _reset(self):
        self.pack, self.picks, self.pick_sizes, self.waiting, self._packs = [], [], [], False, []

    def feed(self, ev):
        """Verarbeitet ein Ereignis aus scan_line; True, wenn sich etwas geaendert hat."""
        before = (self.draft, self.event, list(self.pack), list(self.picks), self.waiting)
        if ev.get("draft") and self.draft and ev["draft"] != self.draft:
            self._reset()
        elif ev.get("event") and self.event and ev["event"] != self.event and not ev.get("draft"):
            self._reset()
        self.draft = ev.get("draft") or self.draft
        self.event = ev.get("event") or self.event
        cards = list(ev["cards"])
        if ev["kind"] == "pack":
            if cards != self.pack or self.waiting:
                self.pack, self.waiting = cards, False
                self._packs.append([set(cards), False])
        elif ev["kind"] == "picked":
            if cards[:len(self.picks)] == self.picks:
                self.pick_sizes = self.pick_sizes[:len(self.picks)] + [None] * (len(cards) - len(self.picks))
            else:
                self.pick_sizes = [None] * len(cards)
            self.picks = cards
        elif ev["kind"] == "pick":
            source = next((p for p in reversed(self._packs) if set(cards) <= p[0]), None)
            if source is not None:
                if not source[1]:
                    source[1] = True
                    self.picks += cards
                    self.pick_sizes += [len(source[0])] * len(cards)
                if source is self._packs[-1]:
                    self.pack, self.waiting = [], True
            else:  # Pack nicht gesehen (Protokoll erst mitten im Draft): Pick trotzdem merken
                self.picks += cards
                self.pick_sizes += [None] * len(cards)
                self.pack, self.waiting = [], True
        return before != (self.draft, self.event, self.pack, self.picks, self.waiting)


class LogFollower:
    """Liest neue, vollstaendige Zeilen einer wachsenden Datei; wird die Datei kuerzer (Arena neu gestartet), geht es
    von vorn los (restarted = True)."""

    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.offset, self.rest, self.restarted = 0, "", False

    def poll(self):
        try:
            size = self.path.stat().st_size
        except OSError:
            return []
        if size < self.offset:
            self.offset, self.rest, self.restarted = 0, "", True
        if size == self.offset:
            return []
        with self.path.open("rb") as fh:
            fh.seek(self.offset)
            data = fh.read(size - self.offset)
        self.offset += len(data)
        lines = (self.rest + data.decode("utf-8", errors="replace")).split("\n")
        self.rest = lines.pop()
        return [line.rstrip("\r") for line in lines]


def install_dirs(text):
    """MTGA_Data-Ordner: zuerst die im Protokoll genannten, dann die ueblichen Installationsorte."""
    found = []
    for m in re.finditer(r"([A-Za-z]:[/\\][^'\"\n]*?MTGA_Data)", text or ""):
        p = pathlib.Path(m.group(1).replace("\\", "/"))
        if p not in found:
            found.append(p)
    return found + [pathlib.Path(p) for p in INSTALL_DIRS if pathlib.Path(p) not in found]


def find_card_db(dirs):
    """Neueste Kartendatenbank (Downloads/Raw/Raw_CardDatabase_*.mtga) im ersten passenden Ordner oder None."""
    for d in dirs:
        files = sorted(pathlib.Path(d).glob("Downloads/Raw/Raw_CardDatabase_*.mtga"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        if files:
            return files[0]
    return None


def load_card_db(path):
    """{GrpId: {"name", "set", "number"}} aus Arenas Kartendatenbank (nur lesen, ohne Token); {} bei Fehlern."""
    try:
        con = sqlite3.connect(f"file:{pathlib.Path(path).as_posix()}?mode=ro", uri=True)
    except sqlite3.Error:
        return {}
    try:
        rows = con.execute(
            "SELECT c.GrpId, l.Loc, c.ExpansionCode, c.CollectorNumber FROM Cards c "
            "JOIN Localizations_enUS l ON l.LocId = c.TitleId "
            "WHERE c.IsToken = 0 ORDER BY l.Formatted").fetchall()
    except sqlite3.Error:
        return {}
    finally:
        con.close()
    out = {}
    for grp, name, code, number in rows:
        if grp not in out and name:
            out[grp] = {"name": re.sub(r"<[^>]+>", "", name).strip(), "set": (code or "").upper(),
                        "number": number or ""}
    return out


def scryfall_names(cache):
    """{GrpId: {"name", "set", "number"}} aus den arena_id der Scryfall-Daten (Rueckfall ohne Arena-Datenbank)."""
    out = {}
    for card in (cache or {}).values():
        grp = card.get("arena_id")
        if isinstance(grp, int) and card.get("name"):
            out[grp] = {"name": card["name"], "set": (card.get("set") or "").upper(),
                        "number": card.get("collector_number") or ""}
    return out
