"""Draft-Statistik: sammelt waehrend des Live-Drafts je Draft die Picks, das abgegebene Deck und die Ergebnisse der
Matches (aus dem Arena-Protokoll, components/arenalog.py) in draftstatistik.json (nicht im Git) und wertet sie je
Karte, Archetyp und Set aus (Drafthelper, Seitenfenster, Bericht, Setauswertung).

Datei: {"version": 1, "drafts": [{"event", "set", "draft_id", "started", "picks": [Name], "pick_sizes": [Packgroesse],
"deck": {"main": {Name: Anzahl}, "side": {...}} oder None, "matches": [{"id", "team", "deck": {Name: Anzahl},
"games": [gewonnen?], "win": gewonnen? oder None}]}]}

Zuordnung: Bei Pick Two und Drafts mit Menschen steht beim Draften nur eine Draft-Kennung im Protokoll, kein
Eventname; das Set kommt dann aus den Karten (set_lookup). Das erste Deck eines Events nach so einem Draft gehoert zu
ihm (wenn mindestens DECK_MATCH seiner Karten aus den Picks stammen), der Draft bekommt dabei den Eventnamen. Matches
und spaetere Decks gehoeren zum letzten Draft desselben Events (Eventname wie "PickTwoDraft_TRK_20261110"). Fehlt der
Draft (nicht mitgelesen), entsteht ein Eintrag ohne Picks. Leere Decks (Event ohne Deck) zaehlen nicht. Dasselbe Protokoll ein zweites Mal gelesen
(draftgott neu gestartet) aendert nichts: Matches zaehlen je Match-Kennung, Picks nur, wenn sie die bekannten
fortsetzen.

Gegnerdeck (enemy_dir): Holt ein Draft seinen 4. Match-Sieg, wird das Deck dieses Matches (mit dem Sideboard des
Drafts) einmal als enemydecks/drafted_<SET>_4wins_<Farben>_<JJJJ-MM-TT>_<hhmm>.txt gespeichert (Zeit des 4. Siegs aus
dem Protokoll). Farben (color_name): aus den Nicht-Land-Karten des Hauptdecks, nach den Farben, die ihre Manakosten
verlangen (cost_colors; zweifarbige Hybridsymbole zaehlen fuer eine Farbe, die das Deck ohnehin spielt, {2/W} und
Phyrexian gar nicht), die mit den meisten Karten zuerst (Gleichstand: WUBRG); eine Farbe mit hoechstens SPLASH_MAX Karten heisst "splash<farbe>", wenn es eine staerkere gibt.
Eine vorhandene Datei wird nie ueberschrieben; der Draft merkt sich den Namen ("enemy_deck").

Zahlen je Karte (card_stats): gedraftet (Kopien), Drafts, Decks (im Hauptdeck), Games/Siege und Matches/Siege mit der
Karte im Hauptdeck des Matches, Durchschnitt der Pick-Nummer im Pack (1 = erster Pick aus einem vollen Pack; bei Pick
Two zaehlen Picks, nicht Karten).
Standardlaender zaehlen nicht.
"""
import datetime
import json
import os
import pathlib
import re
import sys

from components import arenalog
from components import archetypes as set_archetypes
from components import cardarchetypes
from components.i18n import t

BASICS = {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"}
DECK_MATCH = 0.8
ENEMY_WINS = 4
SPLASH_MAX = 2
COLOR_WORD = {"W": "white", "U": "blue", "B": "black", "R": "red", "G": "green"}
_DATE_DE = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4}) (\d{1,2}):(\d{2})")
_DATE_EN = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4}) (\d{1,2}):(\d{2}):\d{2}(?: ?([AP]M))?")


def log_stamp(line):
    """"JJJJ-MM-TT hh:mm" aus dem Zeitstempel einer Protokollzeile (deutsch 12.11.2026 20:47:13 oder englisch
    11/12/2026 8:47:13 PM) oder None."""
    head = (line or "")[:90]
    m = _DATE_DE.search(head)
    if m:
        d, mo, y, h, mi = m.groups()
    else:
        m = _DATE_EN.search(head)
        if not m:
            return None
        mo, d, y, h, mi, ampm = m.groups()
        h = int(h) % 12 + (12 if ampm == "PM" else 0) if ampm else int(h)
    return f"{y}-{int(mo):02d}-{int(d):02d} {int(h):02d}:{mi}"


def cost_colors(cost):
    """Farben, die Manakosten verlangen: ["W", "U"] fuer {W}{U}; zweifarbiges Hybrid als "G/W"; {2/W} und Phyrexian
    ({W/P}) sind auch ohne die Farbe bezahlbar und fehlen."""
    out = []
    for sym in re.findall(r"\{([^}]+)\}", cost or ""):
        parts = sym.upper().split("/")
        colored = [p for p in parts if p in COLOR_WORD]
        if len(parts) == 1 and colored:
            token = colored[0]
        elif len(parts) == 2 and len(colored) == 2:
            token = "/".join(colored)
        else:
            continue
        if token not in out:
            out.append(token)
    return out


def color_name(main, colors):
    """Farben eines Hauptdecks ({Name: Anzahl}) fuer den Dateinamen, z. B. "redwhite", "whitesplashred", "red".
    colors: je Name die Farben (Hybrid als "G/W", siehe cost_colors)."""
    count, hybrid = {}, []
    for name, qty in main.items():
        cs = colors.get(name) or []
        plain = [c for c in cs if c in COLOR_WORD]
        for c in plain:
            count[c] = count.get(c, 0) + qty
        if not plain:
            options = [c for token in cs if "/" in token for c in token.split("/") if c in COLOR_WORD]
            if options:
                hybrid.append((options, qty))
    for options, qty in hybrid:  # Hybrid: fuer die staerkste Farbe, die das Deck schon spielt, sonst die erste
        known = [c for c in options if c in count]
        c = max(known, key=lambda x: count[x]) if known else options[0]
        count[c] = count.get(c, 0) + qty
    if not count:
        return "colorless"
    order = sorted(count, key=lambda c: (-count[c], "WUBRG".index(c)))
    top = count[order[0]]
    main_colors = [c for c in order if count[c] > SPLASH_MAX or top <= SPLASH_MAX]
    splash = [c for c in order if c not in main_colors]
    return "".join(COLOR_WORD[c] for c in main_colors) + "".join("splash" + COLOR_WORD[c] for c in splash)


def enemy_file_name(set_code, colors, stamp):
    """drafted_<SET>_4wins_<Farben>_<JJJJ-MM-TT>_<hhmm>.txt"""
    day, _, clock = stamp.partition(" ")
    return f"drafted_{set_code.upper()}_{ENEMY_WINS}wins_{colors}_{day}_{clock.replace(':', '')}.txt"


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

    def __init__(self, path, lookup, set_lookup=None, enemy_dir=None, card_info=None):
        """lookup(GrpId) -> Name, set_lookup(GrpId) -> Setcode (fuer Drafts ohne Eventnamen); enemy_dir: Ordner fuer
        Decks mit 4 Siegen (None: nichts speichern), card_info(GrpId) -> {"name", "set", "number", "colors"}."""
        self.path, self.lookup, self.set_lookup = pathlib.Path(path), lookup, set_lookup
        self.enemy_dir, self.card_info = (pathlib.Path(enemy_dir) if enemy_dir else None), card_info
        self.prints, self.colors = {}, {}  # Name -> (Set, Nummer) bzw. Farben, aus den Decks
        self.stamp = None
        self.last_saved = None
        self.data = load_stats(path)
        self.state = arenalog.DraftState()
        self.user = None
        self.decks = {}  # Event -> zuletzt gesehenes Deck {"main", "side"} (Namen)
        self.date = None

    def _name(self, grp):
        return self.lookup(grp) or f"#{grp}"

    def _new(self, event, draft_id=None):
        rec = {"event": event, "set": arenalog.set_from_event(event) or "", "draft_id": draft_id,
               "started": (self.stamp or "")[:10] or datetime.date.today().isoformat(), "picks": [],
               "pick_sizes": [],
               "deck": None, "matches": []}
        self.data["drafts"].append(rec)
        return rec

    def _latest(self, event):
        return next((r for r in reversed(self.data["drafts"]) if r.get("event") == event), None)

    def record(self, draft_id, event):
        """Bilanz des Drafts {"wins", "losses", "matches"} (laufende Matches zaehlen nur bei "matches"): der Eintrag mit
        dieser draft_id, sonst der juengste des Events; None, wenn es keinen gibt."""
        rec = next((r for r in reversed(self.data["drafts"]) if draft_id and r.get("draft_id") == draft_id), None)
        if rec is None and not draft_id and event:
            rec = self._latest(event)
        if rec is None:
            return None
        ms = rec.get("matches") or []
        return {"wins": sum(1 for m in ms if m.get("win") is True),
                "losses": sum(1 for m in ms if m.get("win") is False), "matches": len(ms)}

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
        if not rec.get("set") and self.set_lookup:
            sets = {}
            for g in st.picks:
                code = (self.set_lookup(g) or "").upper()
                if code:
                    sets[code] = sets.get(code, 0) + 1
            if sets:
                rec["set"], changed = max(sets, key=sets.get), True
        return changed

    def _fits(self, rec, deck):
        """Stammen mindestens DECK_MATCH der Deckkarten (ohne Standardlaender) aus den Picks des Drafts?"""
        names = {}
        for part in ("main", "side"):
            for n, q in deck[part].items():
                if n not in BASICS:
                    names[n] = names.get(n, 0) + q
        if not rec["picks"]:
            return True
        picks = {}
        for n in rec["picks"]:
            picks[n] = picks.get(n, 0) + 1
        total = sum(names.values())
        return total > 0 and sum(min(q, picks.get(n, 0)) for n, q in names.items()) >= DECK_MATCH * total

    def _deck(self, ev):
        if not is_limited(ev["event"]):
            return False
        deck = {"main": {self._name(g): q for g, q in ev["main"].items()},
                "side": {self._name(g): q for g, q in ev["side"].items()}}
        if self.card_info:
            for g in list(ev["main"]) + list(ev["side"]):
                info = self.card_info(g)
                if info:
                    self.prints[info["name"]] = (info.get("set") or "", info.get("number") or "")
                    self.colors[info["name"]] = (cost_colors(info["cost"]) if info.get("cost") is not None
                                                 else list(info.get("colors") or []))
        if not deck["main"]:
            return False
        self.decks[ev["event"]] = deck
        last = self.data["drafts"][-1] if self.data["drafts"] else None
        if last and not last.get("event") and not last.get("deck") and self._fits(last, deck):
            last["event"] = ev["event"]  # Draft ohne Eventnamen: das Deck nennt ihn
            last["set"] = arenalog.set_from_event(ev["event"]) or last.get("set") or ""
            rec = last
        else:
            rec = self._latest(ev["event"])
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
                    if m["win"]:
                        self._save_enemy(r, m)
                    return True
        return False

    def _line(self, name, qty):
        code, number = self.prints.get(name, ("", ""))
        return f"{qty} {name}" + (f" ({code}) {number}" if code and number else "")

    def _save_enemy(self, rec, match):
        """Beim 4. Sieg das Deck des Matches einmal als Gegnerdeck speichern (siehe Modulbeschreibung)."""
        wins = sum(1 for m in rec["matches"] if m.get("win"))
        if not self.enemy_dir or wins != ENEMY_WINS or rec.get("enemy_deck") or not match.get("deck"):
            return
        main = match["deck"]
        side = (rec.get("deck") or {}).get("side") or {}
        colors = color_name({n: q for n, q in main.items() if n not in BASICS}, self.colors)
        stamp = self.stamp or datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        name = enemy_file_name(rec.get("set") or "XXX", colors, stamp)
        rec["enemy_deck"] = name
        path = self.enemy_dir / name
        if path.exists():
            return
        lines = ["Deck"] + [self._line(n, q) for n, q in main.items()]
        if side:
            lines += ["", "Sideboard"] + [self._line(n, q) for n, q in side.items()]
        try:
            self.enemy_dir.mkdir(exist_ok=True)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError as e:
            print(t("Gegnerdeck nicht gespeichert: {e}", e=e), file=sys.stderr)
            return
        self.last_saved = name
        print(t("Gegnerdeck gespeichert: {path}", path=path), file=sys.stderr)

    def feed_line(self, line):
        """Verarbeitet eine Protokollzeile; True (und Datei geschrieben), wenn sich die Statistik geaendert hat."""
        stamp = log_stamp(line)
        if stamp:
            self.stamp = stamp
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


def rebuild(path, logs, lookup, set_lookup=None):
    """Baut die Statistik aus Protokolldateien neu auf (aelteste zuerst; fehlende werden uebersprungen). Die alte
    Datei bleibt als <Name>.backup.json erhalten. Gibt den Pfad der Sicherung zurueck (None ohne alte Datei)."""
    path = pathlib.Path(path)
    backup = None
    if path.exists():
        backup = path.with_name(path.stem + ".backup.json")
        backup.write_bytes(path.read_bytes())
    save_stats(path, empty())
    tracker = Tracker(path, lookup, set_lookup)
    for log in logs:
        try:
            text = pathlib.Path(log).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.split("\n"):
            tracker.feed_line(line)
    save_stats(path, tracker.data)
    return backup


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
        per_pick = 1  # Karten je Pick (Pick Two: 2): so viele Picks am Anfang kommen aus dem vollen Pack
        while full and per_pick < len(all_sizes) and all_sizes[per_pick] == full:
            per_pick += 1
        seen = set()
        for i, name in enumerate(rec.get("picks") or []):
            if name in BASICS or name.startswith("#"):
                continue
            st = get(name)
            st["drafted"] += 1
            seen.add(name)
            size = all_sizes[i] if i < len(all_sizes) else None
            if full and size:
                st["_picks"].append((full - size) / per_pick + 1)
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
