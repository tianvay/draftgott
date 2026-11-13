"""Seitenfenster fuer den Live-Draft (--overlay URL): ein kleines Fenster, das immer im Vordergrund bleibt und das
aktuelle Pack als Rangliste zeigt (Stand von /api/live des Drafthelpers, jede Sekunde neu).

Holt ein Deck seinen 4. Sieg (Gegnerdeck gespeichert), feiert das Fenster kurz mit Pokal und Konfetti
(celebrate) und meldet die Aufnahme in die "Hall of Game" der Gegnerdecks.

Der Knopf oben rechts (oder ein Doppelklick ins Fenster) minimiert es zu einem kleinen Kasten (mini_rows): im Spiel
nur die Chancen auf Removal, Land und Kreatur, im Draft Pick, Archetyp und beste Karte.

Top-Pick (hint_rows): Karten ab MustPlay, deren bester Archetyp unserer ist oder nahe dran (snap["hints"]), stehen
lila und blinkend oben; im Pack steht vor ihnen ◆. Noch einmal klicken klappt es
wieder auf. Arena muss dafuer im Fenster oder im randlosen Vollbild laufen; ueber exklusivem Vollbild liegt kein Fenster.
Nur Standardbibliothek (tkinter). Das Fenster schliesst sich, wenn der Drafthelper beendet wurde.
"""
import json
import math
import random
import urllib.error
import urllib.request

RATING_ABBR = {"matchwinner": "♛", "splashworthy": "★", "mustplay": "MP", "filler": "Fi", "neverplay": "NP"}
MARK = {"best": "◆", "arch": "●", "color": "○", "": "  "}
COLORS = {"bg": "#161b24", "ink": "#e8ecf3", "muted": "#8d97a8", "arch": "#1f7a45", "color": "#2c3a52",
          "head": "#ffd166", "never": "#6b7280", "best": "#6d28b8", "hint": "#8e2bd6", "hint2": "#5b1d99"}
HINT_STATE = {"in": "dein Archetyp", "near": "nahe dran"}


def hint_rows(snap):
    """Top-Picks im Pack: Karten ab MustPlay in ihrem besten Archetyp (oder nahe dran)."""
    return [(f"{MARK['best']} Top-Pick: {h['name']} ({RATING_ABBR.get(h.get('rating'), h.get('rating') or '')}) – "
             f"am besten in {h.get('best_name') or h.get('best')} ({HINT_STATE.get(h.get('state'), '')})", "hint")
            for h in (snap or {}).get("hints") or []]


def _arch_name(snap, colors):
    for s in ((snap.get("detect") or {}).get("scores") or []) + (snap.get("archetypes") or []):
        if s["colors"] == colors:
            return s["name"]
    return colors


CONFETTI_COLORS = ("#ffd166", "#ef476f", "#06d6a0", "#118ab2", "#f78c6b", "#c77dff", "#ffffff")
GRAVITY = 260.0  # Pixel je Sekunde^2
PARTY_SECONDS = 7


def new_celebration(last, snap):
    """Name des Gegnerdecks, das neu gefeiert werden soll (anders als das zuletzt gefeierte), sonst None."""
    name = (snap or {}).get("enemy_saved")
    return name if name and name != last else None


def celebration_lines(name):
    """Texte der Feier (nur Zeichen, die tkinter darstellen kann: keine Emoji)."""
    short = name[:-4] if name.endswith(".txt") else name
    return ["4 Siege!", "Aufgenommen in die Hall of Game", "der Gegnerdecks", short]


def make_confetti(n, width, height, rng):
    """n Konfetti-Teile oberhalb des Fensters: Lage, Geschwindigkeit, Groesse, Farbe, Drehung."""
    return [{"x": rng.uniform(0, width), "y": rng.uniform(-height, -5), "vx": rng.uniform(-40, 40),
             "vy": rng.uniform(20, 90), "w": rng.uniform(5, 10), "h": rng.uniform(3, 6),
             "color": rng.choice(CONFETTI_COLORS), "angle": rng.uniform(0, 6.28), "spin": rng.uniform(-6, 6)}
            for _ in range(n)]


def step_confetti(parts, dt):
    """Bewegt die Teile um dt Sekunden (Schwerkraft, leichtes Flattern, Drehung)."""
    for p in parts:
        p["vy"] += GRAVITY * dt * 0.35
        p["x"] += (p["vx"] + 25 * math.sin(p["angle"])) * dt
        p["y"] += p["vy"] * dt
        p["angle"] += p["spin"] * dt
    return parts


def celebrate(root, name, seconds=PARTY_SECONDS):
    """Kleines Fenster ueber dem Seitenfenster: Pokal, fallendes Konfetti und die Nachricht; schliesst sich nach
    einigen Sekunden oder per Klick."""
    import tkinter as tk
    w, h = 380, 330
    top = tk.Toplevel(root)
    top.overrideredirect(True)
    top.attributes("-topmost", True)
    x = max(0, root.winfo_rootx() + root.winfo_width() - w)
    top.geometry(f"{w}x{h}+{x}+{max(0, root.winfo_rooty())}")
    cv = tk.Canvas(top, width=w, height=h, bg="#161b24", highlightthickness=2, highlightbackground="#ffd166")
    cv.pack()
    gold, dark = "#f4c430", "#b8860b"
    cx, cy = w // 2, 120

    def trophy(dy):
        cv.delete("trophy")
        t = ("trophy",)
        cv.create_arc(cx - 70, cy - 55 + dy, cx - 20, cy + 5 + dy, start=90, extent=180, style="arc", width=7,
                      outline=dark, tags=t)
        cv.create_arc(cx + 20, cy - 55 + dy, cx + 70, cy + 5 + dy, start=270, extent=180, style="arc", width=7,
                      outline=dark, tags=t)
        cv.create_polygon(cx - 45, cy - 60 + dy, cx + 45, cy - 60 + dy, cx + 32, cy + 5 + dy, cx + 10, cy + 22 + dy,
                          cx - 10, cy + 22 + dy, cx - 32, cy + 5 + dy, fill=gold, outline=dark, width=2, tags=t)
        cv.create_oval(cx - 45, cy - 68 + dy, cx + 45, cy - 52 + dy, fill="#ffe08a", outline=dark, width=2, tags=t)
        cv.create_rectangle(cx - 7, cy + 22 + dy, cx + 7, cy + 42 + dy, fill=gold, outline=dark, tags=t)
        cv.create_rectangle(cx - 30, cy + 42 + dy, cx + 30, cy + 54 + dy, fill=dark, outline=dark, tags=t)
        cv.create_text(cx, cy - 22 + dy, text="4", font=("Segoe UI", 26, "bold"), fill="#7a5200", tags=t)

    lines = celebration_lines(name)
    cv.create_text(cx, 210, text=lines[0], font=("Segoe UI", 20, "bold"), fill="#ffd166")
    cv.create_text(cx, 245, text=lines[1], font=("Segoe UI", 13, "bold"), fill="#e8ecf3")
    cv.create_text(cx, 267, text=lines[2], font=("Segoe UI", 13, "bold"), fill="#e8ecf3")
    cv.create_text(cx, 298, text=lines[3], font=("Segoe UI", 9), fill="#8d97a8", width=w - 20)
    parts = make_confetti(70, w, h, random.Random())
    import time
    state = {"t": 0.0, "alive": True, "start": time.monotonic(), "last": time.monotonic()}

    def close(_e=None):
        if state["alive"]:
            state["alive"] = False
            top.destroy()

    def frame():
        if not state["alive"]:
            return
        now = time.monotonic()  # echte Zeit: das Zeichnen darf dauern, die Feier endet trotzdem puenktlich
        dt, state["last"], state["t"] = min(0.1, now - state["last"]), now, now - state["start"]
        trophy(-6 * abs(math.sin(state["t"] * 3)))
        step_confetti(parts, dt)
        cv.delete("confetti")
        for p in parts:
            if p["y"] > h + 10:  # unten raus: oben neu, solange gefeiert wird
                if state["t"] < seconds - 2:
                    p["y"], p["vy"] = -10, 40
                continue
            dx, dy = math.cos(p["angle"]) * p["w"] / 2, math.sin(p["angle"]) * p["w"] / 2
            cv.create_line(p["x"] - dx, p["y"] - dy, p["x"] + dx, p["y"] + dy, width=p["h"], fill=p["color"],
                           tags=("confetti",))
        if state["t"] >= seconds:
            close()
            return
        top.after(33, frame)

    cv.bind("<Button-1>", close)
    frame()
    return top


def _num(x):
    return f"{x:g}".replace(".", ",")


def _pct(p):
    if p <= 0:
        return "0 %"
    return "< 1 %" if p < 0.005 else f"{round(p * 100)} %"


def _trick_text(t):
    text = f"{t['name']}  {t['cost'] or '{0}'}"
    if t.get("rating"):
        text += "  " + RATING_ABBR.get(t["rating"], t["rating"])
    if t.get("removal"):
        text += f"  R{_num(t['removal'])}"
    return text


def trick_rows(t):
    """Tricks bei offenem Mana des Gegners (components/tricks.py): nur, was er jetzt wirken koennte (der naechste
    Gegnerzug wird berechnet, aber nicht gezeigt)."""
    if not t:
        return []
    colors = " ".join(f"{c}×{n}" for c, n in (t.get("colors") or {}).items())
    head = f"Gegner offen {t['open']}" + (f" ({colors})" if colors else "") + f" von {t['lands']} Ländern"
    if t.get("spell_colors"):
        head += " · zeigt " + "".join(t["spell_colors"])
    rows = [(head, "head2")]
    if not t["open"]:
        rows.append(("Kein Mana offen: jetzt keine Tricks", "sub"))
    elif not t["now"]:
        rows.append(("Keine Instants/Flash-Karten mit diesem Mana", "sub"))
    for c in t["now"]:
        rows.append(("• " + _trick_text(c), "arch" if c.get("removal") else "color"))
    return rows


def trick_window_rows(snap):
    """Zeilen des Trick-Warners (eigenes Fenster): Zug und die Tricks bei offenem Mana des Gegners."""
    g = (snap or {}).get("game") or {}
    if not g.get("active"):
        return [("Trick-Warner", "head"), ("Erscheint im Spiel", "msg")]
    rows = [(f"Trick-Warner · Zug {g.get('turn', 0)}", "head")]
    return rows + (trick_rows(g.get("tricks")) or [("Noch keine Daten zum Gegner", "msg")])


def game_rows(g):
    """Zeilen im Spiel: Bibliothek, Chancen je Gruppe (naechste Karte / in 3 Zuegen), Removal, Karten der Bibliothek
    (die Tricks des Gegners stehen im Trick-Warner, trick_window_rows)."""
    rows = [(f"Im Spiel · Zug {g.get('turn', 0)} · Bibliothek {g['library']} · Hand {g.get('hand', 0)}", "head")]
    mana = g.get("mana") or {}
    colors = " ".join(f"{c}×{n}" for c, n in sorted((mana.get("colors") or {}).items(),
                                                     key=lambda kv: "WUBRGC".find(kv[0])))
    rows.append((f"Mana {mana.get('lands', 0)}" + (f" ({colors})" if colors else "") +
                 " · Spielbar = mit diesen Ländern bezahlbar", "sub"))
    rows.append(("Chance nächste Karte · in den nächsten 3 Karten", "sub"))
    for grp in g.get("groups") or []:
        tag = {"land": "color", "removal": "arch", "castable": "head2"}.get(grp["key"], "plain")
        rows.append((f"{grp['label']}: {grp['n']} übrig  ·  {_pct(grp['next'])}  ·  {_pct(grp['in3'])}", tag))
    rem = g.get("removal") or {}
    if rem.get("total"):
        rows.append((f"Removal übrig {rem['left']} von {rem['total']} (Punkte {_num(rem['points_left'])} von "
                     f"{_num(rem['points_total'])})", "sub"))
    if not g.get("consistent", True):
        rows.append(("Bibliothek passt nicht genau zum Deck (z. B. Token oder Sideboard), Werte ungefähr.", "msg"))
    cards = g.get("cards") or []
    spells = [c for c in cards if not c["land"]]
    if spells:
        rows.append(("Noch in der Bibliothek:", "sub"))
    for c in spells:
        text = ("✓ " if c.get("castable") else "   ") + f"{c['n']}× {c['name']}  {_pct(c['next'])}"
        if c.get("removal"):
            text += f"  R{_num(c['removal'])}"
        rows.append((text, "arch" if c.get("removal") else "plain"))
    lands = [c for c in cards if c["land"]]
    if lands:
        rows.append(("Länder: " + ", ".join(f"{c['n']}× {c['name']}" for c in lands), "color"))
    return rows


def _record(info):
    r = info.get("record")
    return f"Bilanz {r['wins']}–{r['losses']}" if r and r.get("matches") else ""


def deck_rows(snap):
    """Deck-Uebersicht nach dem Draft und zwischen den Spielen (statt "Pick 43"): Archetyp und Bilanz, Karten,
    Kurve, Kreaturen, Removal, Kartenfluss, Farben, Bomben."""
    info = snap["deckinfo"]
    main = (snap.get("detect") or {}).get("main")
    head = "Dein Deck" + (f" · {_arch_name(snap, main)} ({main})" if main else "")
    if _record(info):
        head += " · " + _record(info)
    rows = [(head, "head")]
    if info.get("source") == "picks":
        rows.append(("Noch kein Deck in Arena abgegeben: Zahlen über alle Picks", "msg"))
    rows.append((f"{info['cards']} Karten · {info['lands']} Länder · {info['spells']} Zauber · Ø Manawert "
                 f"{info['avg_mv']:.2f}".replace(".", ","), "sub"))
    labels = ("≤1", "2", "3", "4", "5", "6+")
    rows.append(("Kurve " + " ".join(f"{lab}:{n}" for lab, n in zip(labels, info["curve"])), "curve"))
    rows.append((f"Kreaturen {info['creatures']} · Removal {info['removal']} ({_num(info['removal_points'])} P.) · "
                 f"Kartenfluss {info['flow']}", "arch"))
    if info.get("colors"):
        rows.append(("Farben " + " · ".join(f"{c} {n}" for c, n in info["colors"].items()), "colors"))
    if info.get("top"):
        rows.append(("Bomben: " + ", ".join(info["top"]), "head2"))
    return rows


MINI_KEYS = (("removal", "Removal"), ("land", "Land"), ("creature", "Kreatur"))


def mini_rows(snap):
    """Kleiner Kasten (minimiert): im Spiel die Chancen auf Removal, Land und Kreatur fuer die naechste Karte, im Draft
    Pick, Archetyp und die beste Karte des Packs."""
    if not snap:
        return [("draftgott", "msg")]
    g = snap.get("game") or {}
    if g.get("active"):
        by = {r["key"]: r for r in g.get("groups") or []}
        rows = [(f"{label} {_pct(by[key]['next'])}", {"land": "color", "removal": "arch"}.get(key, "plain"))
                for key, label in MINI_KEYS if key in by]
        t = g.get("tricks")
        if t:
            rows.append((f"Tricks {len(t['now'])} · offen {t['open']}", "head"))
        return rows
    if snap.get("complete") and snap.get("deckinfo"):
        info = snap["deckinfo"]
        return [(_record(info) or "Dein Deck", "head"),
                (f"Kreaturen {info['creatures']} · Removal {info['removal']}", "arch")]
    if snap.get("status") in ("pack", "waiting"):
        main = (snap.get("detect") or {}).get("main")
        head = f"Pick {snap.get('pick', 1)} · " + (_arch_name(snap, main) if main else "offen")
        rows = [(head, "head")] + [(f"{MARK['best']} {h['name']}", "hint") for h in snap.get("hints") or []][:1]
        if snap.get("pack"):
            best = snap["pack"][0]
            rows.append((f"1. {best['name']}", best.get("level") or "plain"))
        else:
            rows.append(("Warte auf Pack …", "msg"))
        return rows
    return [("draftgott Live", "msg")]


def info_rows(info, main_name):
    """Kennzahlen der Picks (und im Archetyp) als kurze Zeilen."""
    def line(i):
        return (f"Kreaturen {i['creatures']} · Removal {i['removal']} ({_num(i['removal_points'])} P.) · "
                f"Kartenfluss {i['flow']}")
    rows = [(f"Picks {info['cards']}: " + line(info), "sub")]
    if info.get("arch") and main_name:
        rows.append((f"In {main_name}: {info['arch']['cards']} Karten · " + line(info["arch"]), "sub"))
    return rows


def rows_for(snap):
    """Zeilen [(Text, Stil)] fuer einen Stand von /api/live; Stile: head, sub, arch, color, never, plain, msg."""
    if not snap:
        return [("draftgott Live", "head"), ("Drafthelper nicht erreichbar …", "msg")]
    if (snap.get("game") or {}).get("active"):
        return game_rows(snap["game"])
    if snap.get("enemy_saved"):
        return ([("★ 4 Siege: aufgenommen in die Hall of Game der Gegnerdecks", "head2"),
                 (f"Gegnerdeck gespeichert: {snap['enemy_saved']}", "arch")]
                + rows_for(dict(snap, enemy_saved=None)))
    status = snap.get("status")
    if status in ("nolog", "idle", "off"):
        return [("draftgott Live", "head"), (snap.get("message") or "Kein Live-Draft.", "msg")]
    if snap.get("complete") and snap.get("deckinfo"):
        return deck_rows(snap)
    detect = snap.get("detect") or {}
    main = detect.get("main")
    head = f"Pick {snap.get('pick', 1)} · " + (
        f"Archetyp: {_arch_name(snap, main)} ({main})" + (" – eigene Wahl" if detect.get("manual") else "")
        if main else "Archetyp: noch offen")
    rows = [(head, "head")]
    if status != "waiting":
        rows += hint_rows(snap)
    scores = [s for s in detect.get("scores") or [] if s["score"]][:3]
    if scores:
        rows.append((" · ".join(f"{s['name']} {s['score']:g}" for s in scores), "sub"))
    rows += signal_rows(snap.get("signals"))
    if snap.get("draftinfo") and snap["draftinfo"].get("cards"):
        rows += info_rows(snap["draftinfo"], _arch_name(snap, main) if main else None)
    for a in snap.get("archmap") or []:
        text = f"{a['name']}: {a['count']} Pick{'s' if a['count'] != 1 else ''}"
        if a["pack"]:
            text += " · im Pack: " + ", ".join(a["pack"])
        rows.append((text, "arch" if a["pack"] and a["colors"] == main else ("color" if a["pack"] else "sub")))
    if status == "waiting" or not snap.get("pack"):
        rows.append(("Warte auf das nächste Pack …", "msg"))
        return rows + tip_rows(snap, main)
    for c in snap["pack"]:
        tag = "never" if c.get("rating") == "neverplay" else (c.get("level") or "plain")
        parts = [MARK.get(c.get("level") or "", "  "), c["name"], "".join(c.get("colors") or []) or "C"]
        if c.get("rating"):
            parts.append(RATING_ABBR.get(c["rating"], c["rating"]))
        if c.get("arch"):
            parts.append("[" + ", ".join(_arch_name(snap, a) for a in c["arch"]) + "]")
        if c.get("removal"):
            parts.append(f"R{_num(c['removal'])}")
        if c.get("synergy"):
            parts.append(f"Syn+{_num(c['synergy'])}")
        stats = c.get("stats") or {}
        if stats.get("games"):
            parts.append(f"{round(100 * stats['wins'] / stats['games'])} % ({stats['games']} G.)")
        rows.append(("  ".join(parts), tag))
    return rows + tip_rows(snap, main)


SIGNAL_LABEL = {"open": "offen", "maybe": "evtl. offen", "contested": "umkämpft"}


def _signed(n):
    return f"+{n}" if n > 0 else (f"−{-n}" if n < 0 else "0")


def signal_rows(sig):
    """Offene Farben (components/signals.py): eine Zeile mit den Farben, die ein Signal haben, und die letzten zwei
    Hinweise; nichts, solange keine Farbe ein Signal hat."""
    if not sig:
        return []
    marked = sorted(((c, v) for c, v in (sig.get("colors") or {}).items() if v.get("level")),
                    key=lambda cv: (-cv[1]["score"], "WUBRG".find(cv[0])))
    if not marked:
        return []
    text = f"Signale ({sig.get('format', 'Draft')}): " + " · ".join(
        f"{c} {SIGNAL_LABEL[v['level']]} {_signed(v['score'])}" for c, v in marked)
    best = marked[0][1]["level"]
    rows = [(text, "arch" if best == "open" else "color")]
    rows += [(f"• {n}", "sub") for n in (sig.get("notes") or [])[:2]]
    return rows


def tip_rows(snap, main):
    """Hinweise zum erkannten Archetyp (components/archetypes.py) als letzte Zeilen; leer ohne Archetyp oder ohne
    hinterlegte Archetypen fuer das Set."""
    a = next((a for a in snap.get("archetypes") or [] if main and a["colors"] == main), None)
    if not a or not a.get("tips"):
        return []
    return [(f"Tipps zu {a['name']}", "head2")] + [(f"• {t}", "tip") for t in a["tips"]]


def deck_button(snap):
    """(Beschriftung, klickbar?) des Knopfs "Deck uebernehmen" nach dem Draft, sonst None."""
    if not snap or not snap.get("complete") or (snap.get("game") or {}).get("active"):
        return None  # im Spiel stoert der Knopf nur
    deck = snap.get("deck") or {}
    if deck.get("applied"):
        return ("Deck übernommen ✓", False)
    if deck.get("ready"):
        return (f"Deck + Sideboard übernehmen ({deck.get('main', 0)} + {deck.get('side', 0)})", True)
    return ("Nach „Fertig“ in Arena: Deck + Sideboard übernehmen", False)


def send_deck(url, timeout=3):
    req = urllib.request.Request(url.rstrip("/") + "/api/live/deck", data=b"{}",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None


def fetch(url, timeout=0.8):
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/api/live", timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None


WINDOWS = (("main", "Draft / Bibliothek"), ("tricks", "Trick-Warner"))
CONTROL_SIZE = (200, 96)
TOP = 80


def default_enabled():
    """Alle Fenster sind beim Start angeschaltet."""
    return {key: True for key, _ in WINDOWS}


def visible_windows(enabled, snap):
    """Fenster, die gerade zu sehen sind: das Seitenfenster, wenn angeschaltet; der Trick-Warner nur im Spiel."""
    shown = set()
    if enabled.get("main"):
        shown.add("main")
    if enabled.get("tricks") and ((snap or {}).get("game") or {}).get("active"):
        shown.add("tricks")
    return shown


def control_geometry():
    """Steuerfenster am linken Bildschirmrand."""
    w, h = CONTROL_SIZE
    return f"{w}x{h}+0+{TOP}"


def trick_geometry():
    """Trick-Warner links unter dem Steuerfenster."""
    return f"340x300+0+{TOP + CONTROL_SIZE[1] + 40}"


def main_geometry(screen_width):
    """Seitenfenster am rechten Bildschirmrand."""
    return f"360x560+{max(0, screen_width - 380)}+{TOP}"


def _float_window(win):
    """Immer im Vordergrund, leicht durchsichtig, schmaler Rahmen ohne Eintrag in der Taskleiste (Windows)."""
    import tkinter as tk
    win.attributes("-topmost", True)
    try:
        win.attributes("-alpha", 0.92)
        win.attributes("-toolwindow", True)
    except tk.TclError:
        pass
    win.configure(bg=COLORS["bg"])


MANA_FILL = {"W": "#f3ecd2", "U": "#4a90d9", "B": "#6b5f7a", "R": "#e0533d", "G": "#3f9b5a"}
MANA_INK = {"W": "#161b24"}
CURVE_FILL, CURVE_PEAK = "#4f8cc9", "#ffd166"
CHART_TAGS = ("curve", "colors")


def curve_bars(line):
    """Balken der Kurve aus der Zeile "Kurve ≤1:0 2:9 ..." als [(Beschriftung, Anzahl)]."""
    return [(lab, int(n)) for lab, n in (part.rsplit(":", 1) for part in line.split()[1:])]


def color_parts(line):
    """Farben aus der Zeile "Farben W 14 · R 9" als [(Farbe, Anzahl)]."""
    return [(c, int(n)) for c, n in (part.split() for part in line[len("Farben "):].split(" · "))]


def curve_layout(bars, width, height, top=14, bottom=16):
    """Rechtecke der Kurve: gleiche Breite, gemeinsame Grundlinie, Hoehe nach Anzahl (oben Platz fuer die Zahl,
    unten fuer die Beschriftung)."""
    if not bars:
        return []
    slot = width / len(bars)
    gap = min(8.0, slot * 0.25)
    base = height - bottom
    peak = max(n for _, n in bars) or 1
    return [{"label": lab, "n": n, "x0": round(i * slot + gap / 2), "x1": round((i + 1) * slot - gap / 2),
             "y0": round(base - (base - top) * n / peak), "y1": base} for i, (lab, n) in enumerate(bars)]


def color_layout(parts, width):
    """Abschnitte des Farbbalkens: Breite nach Anteil, lueckenlos von 0 bis width."""
    total = sum(n for _, n in parts)
    if not total:
        return []
    segs, done = [], 0
    for c, n in parts:
        x0 = round(width * done / total)
        done += n
        segs.append({"color": c, "n": n, "x0": x0, "x1": round(width * done / total),
                     "fill": MANA_FILL.get(c, "#8d97a8"), "ink": MANA_INK.get(c, "#ffffff")})
    return segs


def _chart(text, line, tag):
    """Kleine Grafik (Canvas) fuer eine Zeile mit Tag curve (Balken je Manawert, hoechster gelb) oder colors
    (geteilter Balken in Manafarben)."""
    import tkinter as tk
    width = max(200, text.winfo_width() - 2 * int(text.cget("padx")) - 4)
    if tag == "curve":
        height = 74
        cv = tk.Canvas(text, width=width, height=height, bg=COLORS["bg"], highlightthickness=0)
        bars = curve_layout(curve_bars(line), width, height)
        peak = max((b["n"] for b in bars), default=0)
        cv.create_line(0, height - 16, width, height - 16, fill="#2c3a52")
        for b in bars:
            mid = (b["x0"] + b["x1"]) / 2
            if b["n"]:
                cv.create_rectangle(b["x0"], b["y0"], b["x1"], b["y1"], width=0,
                                    fill=CURVE_PEAK if b["n"] == peak else CURVE_FILL)
            cv.create_text(mid, b["y0"] - 2, text=str(b["n"]), anchor="s", fill=COLORS["ink"],
                           font=("Segoe UI", 9, "bold"))
            cv.create_text(mid, height - 1, text=b["label"], anchor="s", fill=COLORS["muted"], font=("Segoe UI", 9))
        return cv
    height = 22
    cv = tk.Canvas(text, width=width, height=height, bg=COLORS["bg"], highlightthickness=0)
    for s in color_layout(color_parts(line), width):
        cv.create_rectangle(s["x0"], 0, s["x1"], height, width=0, fill=s["fill"])
        if s["x1"] - s["x0"] >= 28:
            cv.create_text((s["x0"] + s["x1"]) / 2, height / 2, text=f"{s['color']} {s['n']}", fill=s["ink"],
                           font=("Segoe UI", 10, "bold"))
    return cv


def _fill(text, rows):
    """Schreibt die Zeilen ins Textfeld; Zeilen mit Tag curve/colors werden als kleine Grafik eingesetzt."""
    text.configure(state="normal")
    for old in getattr(text, "_charts", []):
        old.destroy()
    text._charts = []
    text.delete("1.0", "end")
    for line, tag in rows:
        if tag in CHART_TAGS:
            cv = _chart(text, line, tag)
            text._charts.append(cv)
            text.window_create("end", window=cv, pady=3)
            text.insert("end", "\n")
        else:
            text.insert("end", line + "\n", tag)
    text.configure(state="disabled")


def _styles(text):
    """Zeilenstile eines Textfelds (head, sub, arch, ... und groessere mini_* fuer den Kasten)."""
    text.tag_configure("head", foreground=COLORS["head"], font=("Segoe UI", 12, "bold"), spacing3=2)
    text.tag_configure("sub", foreground=COLORS["muted"], font=("Segoe UI", 9), spacing3=6)
    text.tag_configure("arch", background=COLORS["arch"], font=("Segoe UI", 11, "bold"), spacing1=2, spacing3=2)
    text.tag_configure("color", background=COLORS["color"], spacing1=2, spacing3=2)
    text.tag_configure("best", background=COLORS["best"], font=("Segoe UI", 11, "bold"), spacing1=2, spacing3=2)
    text.tag_configure("hint", background=COLORS["hint"], foreground="#ffffff", font=("Segoe UI", 12, "bold"),
                       spacing1=4, spacing3=4)
    text.tag_configure("plain", spacing1=2, spacing3=2)
    text.tag_configure("never", foreground=COLORS["never"], spacing1=2, spacing3=2)
    text.tag_configure("msg", foreground=COLORS["muted"], font=("Segoe UI", 10, "italic"))
    text.tag_configure("head2", foreground=COLORS["head"], font=("Segoe UI", 11, "bold"), spacing1=2, spacing3=4)
    text.tag_configure("tip", foreground=COLORS["ink"], font=("Segoe UI", 10), lmargin1=6, lmargin2=18,
                       spacing3=2)
    for tag in ("arch", "color", "best", "hint", "plain", "head", "msg"):  # Kasten: groessere Schrift
        text.tag_configure("mini_" + tag, font=("Segoe UI", 13, "bold"), spacing1=3, spacing3=3,
                           background=COLORS[tag] if tag in ("arch", "color", "best", "hint") else COLORS["bg"],
                           foreground=COLORS["head"] if tag == "head" else COLORS["ink"])


def run(url, interval_ms=1000):
    """Drei Fenster: das Steuerfenster (Hauptfenster, links) schaltet Seitenfenster und Trick-Warner an und ab;
    schliesst man es, ist alles zu."""
    import tkinter as tk

    control = tk.Tk()
    control.title("draftgott")
    _float_window(control)
    control.geometry(control_geometry())
    tk.Label(control, text="draftgott Fenster", bg=COLORS["bg"], fg=COLORS["head"],
             font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=8, pady=(4, 2))
    enabled = {key: tk.BooleanVar(value=on) for key, on in default_enabled().items()}

    root = tk.Toplevel(control)  # Seitenfenster: Draft, Deck und im Spiel die Bibliothek
    root.title("draftgott Live")
    _float_window(root)
    root.geometry(main_geometry(root.winfo_screenwidth()))
    tricks = tk.Toplevel(control)
    tricks.title("draftgott Tricks")
    _float_window(tricks)
    tricks.geometry(trick_geometry())
    trick_text = tk.Text(tricks, bg=COLORS["bg"], fg=COLORS["ink"], bd=0, highlightthickness=0, wrap="word",
                         font=("Segoe UI", 11), padx=10, pady=4, cursor="arrow")
    trick_text.pack(fill="both", expand=True)
    windows = {"main": root, "tricks": tricks}
    for key, label in WINDOWS:
        tk.Checkbutton(control, text=label, variable=enabled[key], bg=COLORS["bg"], fg=COLORS["ink"],
                       selectcolor="#2c3a52", activebackground=COLORS["bg"], activeforeground=COLORS["ink"],
                       font=("Segoe UI", 10), anchor="w", command=lambda: show_windows()).pack(fill="x", padx=6)
        windows[key].protocol("WM_DELETE_WINDOW", lambda k=key: (enabled[k].set(False), show_windows()))

    def show_windows():
        shown = visible_windows({k: v.get() for k, v in enabled.items()}, state["snap"])
        for key, win in windows.items():
            if key in shown and win.state() == "withdrawn":
                win.deiconify()
                win.attributes("-topmost", True)
            elif key not in shown and win.state() != "withdrawn":
                win.withdraw()

    bar = tk.Frame(root, bg=COLORS["bg"])
    bar.pack(fill="x", side="top")
    toggle = tk.Button(bar, text="▁", font=("Segoe UI", 9, "bold"), bg="#2c3a52", fg=COLORS["ink"], relief="flat",
                       activebackground="#3b4d6b", padx=8, pady=0, cursor="hand2")
    toggle.pack(side="right", padx=4, pady=2)
    text = tk.Text(root, bg=COLORS["bg"], fg=COLORS["ink"], bd=0, highlightthickness=0, wrap="word",
                   font=("Segoe UI", 11), padx=10, pady=4, cursor="arrow")
    button = tk.Button(root, font=("Segoe UI", 11, "bold"), bg="#1f7a45", fg="#ffffff", activebackground="#2e9e5b",
                       disabledforeground="#c8d3cc", relief="flat", padx=10, pady=6,
                       command=lambda: send_deck(url))
    text.pack(fill="both", expand=True)
    for t in (text, trick_text):
        _styles(t)
    state = {"last": None, "tricks": None, "seen": False, "misses": 0, "mini": False, "big": None, "snap": None,
             "party": None, "first": True, "blink": False}

    def set_mini(mini):
        x, y = root.winfo_x(), root.winfo_y()
        if mini:
            state["big"] = root.geometry()
            right = x + root.winfo_width()
            root.geometry(f"210x180+{max(0, right - 210)}+{y}")
            toggle.configure(text="▢")
            button.pack_forget()
        else:
            w, h = (state["big"] or "360x560").split("+")[0].split("x")
            right = x + root.winfo_width()
            root.geometry(f"{w}x{h}+{max(0, right - int(w))}+{y}")
            toggle.configure(text="▁")
        state["mini"], state["last"] = mini, None
        render()

    toggle.configure(command=lambda: set_mini(not state["mini"]))
    text.bind("<Double-Button-1>", lambda e: set_mini(not state["mini"]))

    def render():
        snap = state["snap"]
        if state["mini"]:
            rows = [(line, "mini_" + (tag if tag in ("arch", "color", "best", "hint", "plain", "head") else "msg"))
                    for line, tag in mini_rows(snap)]
        else:
            rows = rows_for(snap)
            btn = deck_button(snap)
            if btn is None:
                button.pack_forget()
            else:
                button.configure(text=btn[0], state="normal" if btn[1] else "disabled")
                if not button.winfo_ismapped():
                    button.pack(fill="x", side="bottom", before=text)
        if rows != state["last"]:
            state["last"] = rows
            _fill(text, rows)
        trows = trick_window_rows(snap)
        if trows != state["tricks"]:
            state["tricks"] = trows
            _fill(trick_text, trows)
        show_windows()

    def tick():
        snap = fetch(url)
        if snap is None:
            state["misses"] += 1
            if state["seen"] and state["misses"] * interval_ms >= 8000:  # Drafthelper beendet
                control.destroy()
                return
        else:
            state["seen"], state["misses"] = True, 0
        state["snap"] = snap
        render()
        state["blink"] = not state["blink"]  # Top-Pick blinkt
        for tag in ("hint", "mini_hint"):
            text.tag_configure(tag, background=COLORS["hint2" if state["blink"] else "hint"])
        party = new_celebration(state["party"], snap)
        if party:
            state["party"] = party
            if not state["first"]:  # beim Start nicht fuer ein schon gespeichertes Deck feiern
                try:
                    celebrate(root if root.state() != "withdrawn" else control, party)
                except tk.TclError:
                    pass
        if snap is not None:
            state["first"] = False
        control.after(interval_ms, tick)

    tick()
    control.mainloop()
