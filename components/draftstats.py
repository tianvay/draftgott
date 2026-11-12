"""Draft-Statistik: sammelt waehrend des Live-Drafts je Draft die Picks, das abgegebene Deck und die Ergebnisse der
Matches (aus dem Arena-Protokoll, components/arenalog.py) in draftstatistik.json (nicht im Git) und wertet sie je
Karte, Archetyp und Set aus (Drafthelper, Seitenfenster, Bericht, Setauswertung).

Datei: {"version": 1, "drafts": [{"event", "set", "draft_id", "started", "picks": [Name], "pick_sizes": [Packgroesse],
"deck": {"main": {Name: Anzahl}, "side": {...}} oder None, "matches": [{"id", "team", "deck": {Name: Anzahl},
"games": [gewonnen?], "win": gewonnen? oder None}]}]}

Zuordnung: Matches und Decks gehoeren zum letzten Draft desselben Events (Eventname wie "PickTwoDraft_TRK_20261110").
Fehlt der Draft (nicht mitgelesen), entsteht ein Eintrag ohne Picks. Dasselbe Protokoll ein zweites Mal gelesen
(draftgott neu gestartet) aendert nichts: Matches zaehlen je Match-Kennung, Picks nur, wenn sie die bekannten
fortsetzen.

Zahlen je Karte (card_stats): gedraftet (Kopien), Drafts, Decks (im Hauptdeck), Games/Siege und Matches/Siege mit der
Karte im Hauptdeck des Matches, Durchschnitt der Pick-Nummer im Pack (1 = erster Pick aus einem vollen Pack).
Standardlaender zaehlen nicht.
"""
import datetime
import json
import os
import pathlib
import re

from components import arenalog
from components import archetypes as set_archetypes
from components import cardarchetypes

BASICS = {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"}
_DATE = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4}) \d{1,2}:\d{2}")


def empty():
    return {"version": 1, "drafts": []}


def is_limited(event):
    """Draft- und Sealed-Events (die Statistik zaehlt nur diese)."""
    return bool(event) and ("Draft" in event or "Sealed" in event)


def load_stats(path):
    try:
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return empty()
    if not isinstance(data, dict) or not isinstance(data.get("drafts"), list):
        return empty()
    return data


def save_stats(path, data):
    path = pathlib.Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _prefix(a, b):
    n = min(len(a), len(b))
    return a[:n] == b[:n]


class Tracker:
    """Liest Protokollzeilen (feed_line) und schreibt Aenderungen sofort in die Datei. lookup(GrpId) -> Name."""

    def __init__(self, path, lookup):
        self.path, self.lookup = pathlib.Path(path), lookup
        self.data = load_stats(path)
        self.state = arenalog.DraftState()
        self.user = None
        self.decks = {}  # Event -> zuletzt gesehenes Deck {"main", "side"} (Namen)
        self.date = None

    def _name(self, grp):
        return self.lookup(grp) or f"#{grp}"

    def _new(self, event, draft_id=None):
        rec = {"event": event, "set": arenalog.set_from_event(event) or "", "draft_id": draft_id,
               "started": self.date or datetime.date.today().isoformat(), "picks": [], "pick_sizes": [],
               "deck": None, "matches": []}
        self.data["drafts"].append(rec)
        return rec

    def _latest(self, event):
        return next((r for r in reversed(self.data["drafts"]) if r.get("event") == event), None)

    def _draft_update(self):
        st = self.state
        event = st.event if is_limited(st.event) else None
        if not st.picks or not (event or st.draft):
            return False
        picks = [self._name(g) for g in st.picks]
        rec = None
        for r in reversed(self.data["drafts"]):
            if st.draft and r.get("draft_id") == st.draft:
                rec = r
                break
            if not st.draft and event and r.get("event") == event and _prefix(r["picks"], picks):
                rec = r
                break
        if rec is None:
            rec = self._new(event, st.draft)
        changed = False
        if event and not rec.get("event"):
            rec["event"], rec["set"], changed = event, arenalog.set_from_event(event) or "", True
        if len(picks) > len(rec["picks"]):
            rec["picks"], rec["pick_sizes"], changed = picks, list(st.pick_sizes), True
        return changed

    def _deck(self, ev):
        if not is_limited(ev["event"]):
            return False
        deck = {"main": {self._name(g): q for g, q in ev["main"].items()},
                "side": {self._name(g): q for g, q in ev["side"].items()}}
        self.decks[ev["event"]] = deck
        rec = self._latest(ev["event"])
        if rec is None:  # Draft mit Menschen: Eventname kommt erst mit dem Deck
            rec = next((r for r in reversed(self.data["drafts"]) if not r.get("event") and not r.get("deck")), None)
            if rec is not None:
                rec["event"], rec["set"] = ev["event"], arenalog.set_from_event(ev["event"]) or ""
        if rec is None:
            rec = self._new(ev["event"])
        if rec.get("deck") == deck:
            return False
        rec["deck"] = deck
        return True

    def _match_start(self, ev):
        if not is_limited(ev["event"]) or not self.user:
            return False
        team = next((p["team"] for p in ev["players"] if p["user"] == self.user), None)
        if team is None or any(m["id"] == ev["match"] for r in self.data["drafts"] for m in r["matches"]):
            return False
        rec = self._latest(ev["event"]) or self._new(ev["event"])
        deck = rec.get("deck") or self.decks.get(ev["event"]) or {"main": {}}
        rec["matches"].append({"id": ev["match"], "team": team, "deck": dict(deck["main"]), "games": [],
                               "win": None})
        return True

    def _match_end(self, ev):
        for r in self.data["drafts"]:
            for m in r["matches"]:
                if m["id"] == ev["match"] and m["win"] is None and ev["winner"] is not None:
                    m["games"] = [w == m["team"] for w in ev["games"]] or [ev["winner"] == m["team"]]
                    m["win"] = ev["winner"] == m["team"]
                    return True
        return False

    def feed_line(self, line):
        """Verarbeitet eine Protokollzeile; True (und Datei geschrieben), wenn sich die Statistik geaendert hat."""
        m = _DATE.search(line[:80]) if line else None
        if m:
            self.date = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
        changed = False
        for ev in arenalog.scan_line(line):
            if self.state.feed(ev):
                changed = self._draft_update() or changed
        for ev in arenalog.scan_match_line(line):
            if ev["kind"] == "user":
                self.user = ev["id"]
            elif ev["kind"] == "deck":
                changed = self._deck(ev) or changed
            elif ev["kind"] == "match_start":
                changed = self._match_start(ev) or changed
            elif ev["kind"] == "match_end":
                changed = self._match_end(ev) or changed
        if changed:
            save_stats(self.path, self.data)
        return changed


def _in_set(rec, set_code):
    return not set_code or (rec.get("set") or "").lower() == set_code.lower()


def _blank():
    return {"drafted": 0, "drafts": 0, "decks": 0, "games": 0, "wins": 0, "matches": 0, "match_wins": 0,
            "avg_pick": None, "_picks": []}


def card_stats(data, set_code=None):
    """{Name: Zahlen} (siehe Modulbeschreibung), nur Drafts des Sets (ohne Set: alle)."""
    out = {}

    def get(name):
        return out.setdefault(name, _blank())

    for rec in data.get("drafts", []):
        if not _in_set(rec, set_code):
            continue
        all_sizes = list(rec.get("pick_sizes") or [])
        sizes = [s for s in all_sizes if s]
        full = max(sizes) if sizes else None
        seen = set()
        for i, name in enumerate(rec.get("picks") or []):
            if name in BASICS or name.startswith("#"):
                continue
            st = get(name)
            st["drafted"] += 1
            seen.add(name)
            size = all_sizes[i] if i < len(all_sizes) else None
            if full and size:
                st["_picks"].append(full - size + 1)
        for name in seen:
            out[name]["drafts"] += 1
        for name in ((rec.get("deck") or {}).get("main") or {}):
            if name not in BASICS and not name.startswith("#"):
                get(name)["decks"] += 1
        for m in rec.get("matches") or []:
            if m.get("win") is None:
                continue
            deck = m.get("deck") or (rec.get("deck") or {}).get("main") or {}
            for name in deck:
                if name in BASICS or name.startswith("#"):
                    continue
                st = get(name)
                st["games"] += len(m["games"])
                st["wins"] += sum(1 for g in m["games"] if g)
                st["matches"] += 1
                st["match_wins"] += 1 if m["win"] else 0
    for st in out.values():
        picks = st.pop("_picks")
        st["avg_pick"] = round(sum(picks) / len(picks), 2) if picks else None
    return out


def summary(data, set_code=None):
    """Drafts, Matches (mit Ergebnis), Siege, Games und Game-Siege der Drafts eines Sets."""
    s = {"drafts": 0, "matches": 0, "match_wins": 0, "games": 0, "wins": 0}
    for rec in data.get("drafts", []):
        if not _in_set(rec, set_code):
            continue
        s["drafts"] += 1
        for m in rec.get("matches") or []:
            if m.get("win") is None:
                continue
            s["matches"] += 1
            s["match_wins"] += 1 if m["win"] else 0
            s["games"] += len(m["games"])
            s["wins"] += sum(1 for g in m["games"] if g)
    return s


def sets_in(data):
    """Setcodes der Drafts, das haeufigste zuerst (Gleichstand: das mit dem neuesten Draft)."""
    count, latest = {}, {}
    for rec in data.get("drafts", []):
        code = (rec.get("set") or "").upper()
        if code:
            count[code] = count.get(code, 0) + 1
            latest[code] = max(latest.get(code, ""), rec.get("started") or "")
    return sorted(count, key=lambda c: (-count[c], tuple(-ord(ch) for ch in latest[c])))


def rate_text(st):
    """"75 % in 4 Games" oder "" ohne Games."""
    g = (st or {}).get("games", 0)
    if not g:
        return ""
    return f"{round(100 * st['wins'] / g)} % in {g} Game{'s' if g != 1 else ''}"


def record_cards(rec, colors):
    """Karten eines Drafts fuer die Archetyp-Erkennung: Hauptdeck (ohne Standardlaender), sonst die Picks."""
    deck = (rec.get("deck") or {}).get("main") or {}
    names = {n: q for n, q in deck.items() if n not in BASICS} or {}
    if not names:
        for n in rec.get("picks") or []:
            names[n] = names.get(n, 0) + 1
    return [{"name": n, "qty": q, "colors": colors.get(n, []), "land": False} for n, q in names.items()]


def record_archetype(rec, colors, assign, ratings):
    """Archetyp eines Drafts (wie im Live-Draft erkannt, aus Hauptdeck bzw. Picks) oder None."""
    found = set_archetypes.for_set(rec.get("set"))
    return cardarchetypes.detect(record_cards(rec, colors), assign, ratings, found)["main"]
