"""Seitenfenster fuer den Live-Draft (--overlay URL): ein kleines Fenster, das immer im Vordergrund bleibt und das
aktuelle Pack als Rangliste zeigt (Stand von /api/live des Drafthelpers, jede Sekunde neu).

Der Knopf oben rechts (oder ein Doppelklick ins Fenster) minimiert es zu einem kleinen Kasten (mini_rows): im Spiel
nur die Chancen auf Removal, Land und Kreatur, im Draft Pick, Archetyp und beste Karte. Noch einmal klicken klappt es
wieder auf. Arena muss dafuer im Fenster oder im randlosen Vollbild laufen; ueber exklusivem Vollbild liegt kein Fenster.
Nur Standardbibliothek (tkinter). Das Fenster schliesst sich, wenn der Drafthelper beendet wurde.
"""
import json
import urllib.error
import urllib.request

RATING_ABBR = {"splashworthy": "★", "mustplay": "MP", "filler": "Fi", "neverplay": "NP"}
MARK = {"arch": "●", "color": "○", "": "  "}
COLORS = {"bg": "#161b24", "ink": "#e8ecf3", "muted": "#8d97a8", "arch": "#1f7a45", "color": "#2c3a52",
          "head": "#ffd166", "never": "#6b7280"}


def _arch_name(snap, colors):
    for s in (snap.get("detect") or {}).get("scores") or []:
        if s["colors"] == colors:
            return s["name"]
    return colors


def _num(x):
    return f"{x:g}".replace(".", ",")


def _pct(p):
    if p <= 0:
        return "0 %"
    return "< 1 %" if p < 0.005 else f"{round(p * 100)} %"


def game_rows(g):
    """Zeilen im Spiel: Bibliothek, Chancen je Gruppe (naechste Karte / in 3 Zuegen), Removal, Karten der Bibliothek."""
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


MINI_KEYS = (("removal", "Removal"), ("land", "Land"), ("creature", "Kreatur"))


def mini_rows(snap):
    """Kleiner Kasten (minimiert): im Spiel die Chancen auf Removal, Land und Kreatur fuer die naechste Karte, im Draft
    Pick, Archetyp und die beste Karte des Packs."""
    if not snap:
        return [("draftgott", "msg")]
    g = snap.get("game") or {}
    if g.get("active"):
        by = {r["key"]: r for r in g.get("groups") or []}
        return [(f"{label} {_pct(by[key]['next'])}", {"land": "color", "removal": "arch"}.get(key, "plain"))
                for key, label in MINI_KEYS if key in by]
    if snap.get("status") in ("pack", "waiting"):
        main = (snap.get("detect") or {}).get("main")
        head = f"Pick {snap.get('pick', 1)} · " + (_arch_name(snap, main) if main else "offen")
        rows = [(head, "head")]
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
    status = snap.get("status")
    if status in ("nolog", "idle", "off"):
        return [("draftgott Live", "head"), (snap.get("message") or "Kein Live-Draft.", "msg")]
    detect = snap.get("detect") or {}
    main = detect.get("main")
    head = f"Pick {snap.get('pick', 1)} · " + (
        f"Archetyp: {_arch_name(snap, main)} ({main})" + (" – eigene Wahl" if detect.get("manual") else "")
        if main else "Archetyp: noch offen")
    rows = [(head, "head")]
    scores = [s for s in detect.get("scores") or [] if s["score"]][:3]
    if scores:
        rows.append((" · ".join(f"{s['name']} {s['score']:g}" for s in scores), "sub"))
    if snap.get("draftinfo") and snap["draftinfo"].get("cards"):
        rows += info_rows(snap["draftinfo"], _arch_name(snap, main) if main else None)
    for a in snap.get("archmap") or []:
        text = f"{a['name']}: {a['count']} Pick{'s' if a['count'] != 1 else ''}"
        if a["pack"]:
            text += " · im Pack: " + ", ".join(a["pack"])
        rows.append((text, "arch" if a["pack"] and a["colors"] == main else ("color" if a["pack"] else "sub")))
    if status == "waiting" or not snap.get("pack"):
        rows.append(("Warte auf das nächste Pack …", "msg"))
        return rows
    for c in snap["pack"]:
        tag = "never" if c.get("rating") == "neverplay" else (c.get("level") or "plain")
        parts = [MARK.get(c.get("level") or "", "  "), c["name"], "".join(c.get("colors") or []) or "C"]
        if c.get("rating"):
            parts.append(RATING_ABBR.get(c["rating"], c["rating"]))
        if c.get("arch"):
            parts.append("[" + ", ".join(_arch_name(snap, a) for a in c["arch"]) + "]")
        if c.get("removal"):
            parts.append(f"R{_num(c['removal'])}")
        stats = c.get("stats") or {}
        if stats.get("games"):
            parts.append(f"{round(100 * stats['wins'] / stats['games'])} % ({stats['games']} G.)")
        rows.append(("  ".join(parts), tag))
    return rows


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


def run(url, interval_ms=1000):
    import tkinter as tk

    root = tk.Tk()
    root.title("draftgott Live")
    root.attributes("-topmost", True)
    try:
        root.attributes("-alpha", 0.92)
        root.attributes("-toolwindow", True)  # schmaler Rahmen, kein Eintrag in der Taskleiste (Windows)
    except tk.TclError:
        pass
    root.configure(bg=COLORS["bg"])
    root.geometry(f"360x560+{max(0, root.winfo_screenwidth() - 380)}+80")
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
    text.tag_configure("head", foreground=COLORS["head"], font=("Segoe UI", 12, "bold"), spacing3=2)
    text.tag_configure("sub", foreground=COLORS["muted"], font=("Segoe UI", 9), spacing3=6)
    text.tag_configure("arch", background=COLORS["arch"], font=("Segoe UI", 11, "bold"), spacing1=2, spacing3=2)
    text.tag_configure("color", background=COLORS["color"], spacing1=2, spacing3=2)
    text.tag_configure("plain", spacing1=2, spacing3=2)
    text.tag_configure("never", foreground=COLORS["never"], spacing1=2, spacing3=2)
    text.tag_configure("msg", foreground=COLORS["muted"], font=("Segoe UI", 10, "italic"))
    text.tag_configure("head2", foreground=COLORS["head"], font=("Segoe UI", 11, "bold"), spacing1=2, spacing3=4)
    for tag in ("arch", "color", "plain", "head", "msg"):  # Kasten: groessere Schrift
        text.tag_configure("mini_" + tag, font=("Segoe UI", 13, "bold"), spacing1=3, spacing3=3,
                           background=COLORS.get(tag, COLORS["bg"]) if tag in ("arch", "color") else COLORS["bg"],
                           foreground=COLORS["head"] if tag == "head" else COLORS["ink"])
    state = {"last": None, "seen": False, "misses": 0, "mini": False, "big": None, "snap": None}

    def set_mini(mini):
        x, y = root.winfo_x(), root.winfo_y()
        if mini:
            state["big"] = root.geometry()
            right = x + root.winfo_width()
            root.geometry(f"210x150+{max(0, right - 210)}+{y}")
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
            rows = [(line, "mini_" + (tag if tag in ("arch", "color", "plain", "head") else "msg"))
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
            text.configure(state="normal")
            text.delete("1.0", "end")
            for line, tag in rows:
                text.insert("end", line + "\n", tag)
            text.configure(state="disabled")

    def tick():
        snap = fetch(url)
        if snap is None:
            state["misses"] += 1
            if state["seen"] and state["misses"] * interval_ms >= 8000:  # Drafthelper beendet
                root.destroy()
                return
        else:
            state["seen"], state["misses"] = True, 0
        state["snap"] = snap
        render()
        root.after(interval_ms, tick)

    tick()
    root.mainloop()
