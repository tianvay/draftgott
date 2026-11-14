"""Seitenfenster fuer den Live-Draft (--overlay URL): ein kleines Fenster, das immer im Vordergrund bleibt und das
aktuelle Pack als Rangliste zeigt (Stand von /api/live des Drafthelpers, jede Sekunde neu).

Holt ein Deck die hoechste Zahl an Siegen seines Formats (Gegnerdeck gespeichert, Pick Two 4, normaler Draft 7), feiert das Fenster kurz mit Pokal und Konfetti
(celebrate) und meldet die Aufnahme in die "Hall of Fame" der Gegnerdecks.

Der Knopf oben rechts (oder ein Doppelklick ins Fenster) minimiert es zu einem kleinen Kasten (mini_rows): im Spiel
nur die Chancen auf Removal, Land und Kreatur, im Draft Pick, Archetyp und beste Karte, nach dem Draft Bilanz,
Kreaturen, Removal und die Bomben.

Top-Pick (hint_rows): Karten ab MustPlay, deren bester Archetyp unserer ist oder nahe dran (snap["hints"]), stehen
lila und blinkend oben; im Pack steht vor ihnen ◆. Noch einmal klicken klappt es
wieder auf. Arena muss dafuer im Fenster oder im randlosen Vollbild laufen; ueber exklusivem Vollbild liegt kein Fenster.
Nur Standardbibliothek (tkinter). Das Fenster schliesst sich, wenn der Drafthelper beendet wurde.
"""
import json
import math
import re
import random
import urllib.error
import urllib.request

from components.i18n import dec, t

RATING_ABBR = {"matchwinner": "♛", "splashworthy": "★", "mustplay": "MP", "playable": "Pl", "filler": "Fi", "neverplay": "NP"}
MARK = {"best": "◆", "arch": "●", "color": "○", "": "  "}
COLORS = {"bg": "#161b24", "ink": "#e8ecf3", "muted": "#8d97a8", "arch": "#1f7a45", "color": "#2c3a52",
          "head": "#ffd166", "never": "#6b7280", "best": "#6d28b8", "hint": "#8e2bd6", "hint2": "#5b1d99",
          "warn": "#b4462a", "warnsub": "#ffb59e"}
HINT_STATE = {"in": "dein Archetyp", "near": "nahe dran"}


def hint_rows(snap):
    """Top-Picks im Pack: Karten ab MustPlay in ihrem besten Archetyp (oder nahe dran)."""
    return [(f"{MARK['best']} " + t("Top-Pick: {name} ({rating}) – am besten in {arch} ({state})",
                                    name=h['name'], rating=RATING_ABBR.get(h.get('rating'), h.get('rating') or ''),
                                    arch=h.get('best_name') or h.get('best'),
                                    state=t(HINT_STATE.get(h.get('state'), ''))), "hint")
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


def saved_wins(name):
    """Zahl der Siege aus dem Dateinamen des Gegnerdecks (drafted_TRK_7wins_...), sonst 4."""
    m = re.search(r"_(\d+)wins_", name or "")
    return int(m.group(1)) if m else 4


def celebration_lines(name):
    """Texte der Feier (nur Zeichen, die tkinter darstellen kann: keine Emoji)."""
    short = name[:-4] if name.endswith(".txt") else name
    return [t("{n} Siege!", n=saved_wins(name)), t("Aufgenommen in die Hall of Fame"), t("der Gegnerdecks"), short]


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
    return dec(f"{x:g}")


def _pct(p):
    if p <= 0:
        return t("{p} %", p=0)
    return t("< 1 %") if p < 0.005 else t("{p} %", p=round(p * 100))


def _trick_text(tk):
    text = f"{tk['name']}  {tk['cost'] or '{0}'}"
    if tk.get("rating"):
        text += "  " + RATING_ABBR.get(tk["rating"], tk["rating"])
    if tk.get("removal"):
        text += f"  R{_num(tk['removal'])}"
    return text


def trick_rows(tr):
    """Tricks bei offenem Mana des Gegners (components/tricks.py): nur, was er jetzt wirken koennte (der naechste
    Gegnerzug wird berechnet, aber nicht gezeigt)."""
    if not tr:
        return []
    colors = " ".join(f"{c}×{n}" for c, n in (tr.get("colors") or {}).items())
    head = (t("Gegner offen {open}", open=tr['open']) + (f" ({colors})" if colors else "") +
            t(" von {lands} Ländern", lands=tr['lands']))
    if tr.get("spell_colors"):
        head += t(" · zeigt ") + "".join(tr["spell_colors"])
    if tr.get("hand") is not None:
        head += " · " + t("Hand {n}", n=tr["hand"])
    rows = [(head, "head2")]
    if tr.get("hand") == 0:  # ohne Handkarten keine Tricks (Nutzer 14.11.2026)
        rows.append((t("Gegner hat keine Handkarten: keine Tricks"), "sub"))
    elif not tr["open"]:
        rows.append((t("Kein Mana offen: jetzt keine Tricks"), "sub"))
    elif not tr["now"]:
        rows.append((t("Keine Instants/Flash-Karten mit diesem Mana"), "sub"))
    for label, cards in _trick_groups(tr["now"]):
        rows.append((t(label, n=len(cards)), "group"))
        rows += [("• " + _trick_text(c), "arch" if c.get("removal") else "color") for c in cards]
    hidden = tr.get("hidden") or {}
    parts = []
    if hidden.get("none"):
        parts.append(t("{n} ohne Kampfwirkung", n=hidden["none"]))
    if hidden.get("own"):
        parts.append(t("1 braucht eigene Kreatur (Gegner hat keine)") if hidden["own"] == 1 else
                     t("{n} brauchen eigene Kreatur (Gegner hat keine)", n=hidden["own"]))
    if parts and tr.get("hand") != 0:  # Nutzer 14.11.2026: nur Tricks, die zaehlen
        rows.append((t("Ausgeblendet: ") + " · ".join(parts), "sub"))
    return rows


TRICK_GROUPS = ("Instants ({n})", "Flash-Kreaturen ({n})", "Andere mit Flash ({n})")


def _trick_groups(cards):
    """Tricks in Instants, Flash-Kreaturen und andere Karten mit Flash (Nutzer 14.11.2026); leere Gruppen fehlen.
    Aeltere Daten ohne "flash" zaehlen als Instant."""
    groups = ([], [], [])
    for c in cards:
        if not c.get("flash"):
            groups[0].append(c)
        elif "Creature" in (c.get("type") or ""):
            groups[1].append(c)
        else:
            groups[2].append(c)
    return [(label, g) for label, g in zip(TRICK_GROUPS, groups) if g]


def trick_tip(c):
    """Kartentext fuer das Mausfenster im Trick-Warner: Name und Kosten, Typzeile (mit Staerke/Widerstand), Text."""
    lines = [f"{c['name']}  {c.get('cost') or '{0}'}"]
    if c.get("type"):
        lines.append(c["type"] + (f" · {c['pt']}" if c.get("pt") else ""))
    lines += ["", c.get("text") or t("Kein Kartentext gespeichert (Drafthelper neu starten).")]
    if c.get("removal"):
        lines += ["", t("Removal {n} P.", n=_num(c['removal']))]
    return "\n".join(lines)


def trick_tips(snap):
    """Mausfenster-Texte der jetzt moeglichen Tricks, nach Kartenname."""
    g = (snap or {}).get("game") or {}
    tr = g.get("tricks") if g.get("active") else None
    return {c["name"]: trick_tip(c) for c in (tr or {}).get("now") or []}


def tip_for_line(line, tips):
    """Text fuer eine Zeile des Trick-Warners ("• Name  {Kosten} ..."), sonst None."""
    if not line.startswith("• "):
        return None
    name = line[2:].split("  ")[0]
    return tips.get(name)


class _Tooltip:
    """Kleines randloses Fenster am Mauszeiger, das den Kartentext zeigt."""

    def __init__(self, master):
        import tkinter as tk
        self.win = tk.Toplevel(master)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.label = tk.Label(self.win, bg="#232b38", fg=COLORS["ink"], font=("Segoe UI", 10), justify="left",
                              wraplength=300, padx=10, pady=8, highlightthickness=1,
                              highlightbackground=COLORS["hint"])
        self.label.pack()
        self.text = None

    def show(self, text, x, y):
        if text != self.text:
            self.label.configure(text=text)
            self.text = text
        self.win.update_idletasks()
        w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        sw, sh = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
        px = x + 16 if x + 16 + w <= sw else max(0, x - w - 16)
        py = min(y + 12, max(0, sh - h))
        self.win.geometry(f"+{px}+{py}")
        self.win.deiconify()
        self.win.lift()

    def hide(self, _e=None):
        if self.text is not None:
            self.win.withdraw()
            self.text = None


def _bind_trick_tips(text, get_tips):
    """Maus ueber einer Trick-Zeile zeigt deren Kartentext; get_tips() liefert die aktuellen Texte."""
    tip = _Tooltip(text)

    def motion(e):
        idx = text.index(f"@{e.x},{e.y}")
        line = text.get(f"{idx} linestart", f"{idx} lineend")
        bbox = text.dlineinfo(idx)
        inside = bbox is not None and bbox[1] <= e.y <= bbox[1] + bbox[3]
        found = tip_for_line(line, get_tips()) if inside else None
        if found:
            tip.show(found, e.x_root, e.y_root)
        else:
            tip.hide()

    text.bind("<Motion>", motion)
    text.bind("<Leave>", tip.hide)
    return tip


def trick_window_rows(snap):
    """Zeilen des Trick-Warners (eigenes Fenster): Zug und die Tricks bei offenem Mana des Gegners."""
    g = (snap or {}).get("game") or {}
    if not g.get("active"):
        return [(t("Trick-Warner"), "head"), (t("Erscheint im Spiel"), "msg")]
    rows = [(t("Trick-Warner · Zug {n}", n=g.get('turn', 0)), "head")]
    return rows + (trick_rows(g.get("tricks")) or [(t("Noch keine Daten zum Gegner"), "msg")])


def game_rows(g):
    """Zeilen im Spiel: Bibliothek, Chancen je Gruppe (naechste Karte / in 3 Zuegen), Removal, Karten der Bibliothek
    (die Tricks des Gegners stehen im Trick-Warner, trick_window_rows)."""
    rows = [(t("Im Spiel · Zug {turn} · Bibliothek {library} · Hand {hand}", turn=g.get('turn', 0),
               library=g['library'], hand=g.get('hand', 0)), "head")]
    mana = g.get("mana") or {}
    colors = " ".join(f"{c}×{n}" for c, n in sorted((mana.get("colors") or {}).items(),
                                                     key=lambda kv: "WUBRGC".find(kv[0])))
    rows.append((f"Mana {mana.get('lands', 0)}" + (f" ({colors})" if colors else "") +
                 t(" · Spielbar = mit diesen Ländern bezahlbar"), "sub"))
    rows.append((t("Chance nächste Karte · in den nächsten 3 Karten"), "sub"))
    for grp in g.get("groups") or []:
        tag = {"land": "color", "removal": "arch", "castable": "head2"}.get(grp["key"], "plain")
        rows.append((t("{label}: {n} übrig  ·  {next}  ·  {in3}", label=grp['label'], n=grp['n'],
                       next=_pct(grp['next']), in3=_pct(grp['in3'])), tag))
    rem = g.get("removal") or {}
    if rem.get("total"):
        rows.append((t("Removal übrig {left} von {total} (Punkte {pl} von {pt})", left=rem['left'],
                       total=rem['total'], pl=_num(rem['points_left']), pt=_num(rem['points_total'])), "sub"))
    if not g.get("consistent", True):
        rows.append((t("Bibliothek passt nicht genau zum Deck (z. B. Token oder Sideboard), Werte ungefähr."),
                     "msg"))
    cards = g.get("cards") or []
    spells = [c for c in cards if not c["land"]]
    if spells:
        rows.append((t("Noch in der Bibliothek:"), "sub"))
    for c in spells:
        text = ("✓ " if c.get("castable") else "   ") + f"{c['n']}× {c['name']}  {_pct(c['next'])}"
        if c.get("removal"):
            text += f"  R{_num(c['removal'])}"
        rows.append((text, "arch" if c.get("removal") else "plain"))
    lands = [c for c in cards if c["land"]]
    if lands:
        rows.append((t("Länder: ") + ", ".join(f"{c['n']}× {c['name']}" for c in lands), "color"))
    return rows


def _record(info):
    r = info.get("record")
    return t("Bilanz {w}–{l}", w=r['wins'], l=r['losses']) if r and r.get("matches") else ""


def deck_rows(snap):
    """Deck-Uebersicht nach dem Draft und zwischen den Spielen (statt "Pick 43"): Archetyp und Bilanz, Karten,
    Kurve, Kreaturen, Removal, Kartenfluss, Farben, Bomben."""
    info = snap["deckinfo"]
    main = (snap.get("detect") or {}).get("main")
    head = t("Dein Deck") + (f" · {_arch_name(snap, main)} ({main})" if main else "")
    if _record(info):
        head += " · " + _record(info)
    rows = [(head, "head")]
    if info.get("source") == "picks":
        rows.append((t("Noch kein Deck in Arena abgegeben: Zahlen über alle Picks"), "msg"))
    rows.append((t("{cards} Karten · {lands} Länder · {spells} Zauber · Ø Manawert {mv}", cards=info['cards'],
                   lands=info['lands'], spells=info['spells'], mv=dec(f"{info['avg_mv']:.2f}")), "sub"))
    labels = ("≤1", "2", "3", "4", "5", "6+")
    rows.append((t("Kurve") + " " + " ".join(f"{lab}:{n}" for lab, n in zip(labels, info["curve"])), "curve"))
    rows.append((t("Kreaturen {c} · Removal {r} ({p} P.) · Kartenfluss {f}", c=info['creatures'], r=info['removal'],
                   p=_num(info['removal_points']), f=info['flow']), "arch"))
    if info.get("colors"):
        rows.append((t("Farben") + " " + " · ".join(f"{c} {n}" for c, n in info["colors"].items()), "colors"))
    if info.get("top"):
        rows.append((t("Bomben: ") + ", ".join(info["top"]), "head2"))
    return rows + summary_rows(snap.get("summary"))


def summary_rows(s):
    """Draft-Bilanz aus den gelesenen Spielen: Bilanz, Karten gezogen, Zauber, Schaden, besiegte Kreaturen."""
    if not s or not s.get("games"):
        return []
    rows = [(t("Draft-Bilanz {w}–{l} (Ziel {m} Siege)", w=s["wins"], l=s["losses"], m=s["max_wins"]), "head2"),
            (t("{g} Spiele · {t} Züge · Karten gezogen {d}", g=s["games"], t=s["turns"], d=s["drawn"]), "sub"),
            (t("Zauber gewirkt {s} · Länder gelegt {l}", s=s["spells"], l=s["lands"]), "sub"),
            (t("Schaden am Gegner {d} (größter Treffer {b}) · erlitten {x}", d=s["damage_dealt"], b=s["biggest_hit"],
               x=s["damage_taken"]), "arch"),
            (t("Kreaturen besiegt {k} · Schaden an Kreaturen {c}", k=s["kills"], c=s["damage_creatures"]), "arch")]
    if s["games"]:
        rows.append((t("Ø je Spiel: {d} Schaden · {c} Karten gezogen", d=dec(f"{s['damage_dealt'] / s['games']:.1f}"),
                       c=dec(f"{s['drawn'] / s['games']:.1f}")), "sub"))
    return rows


MINI_KEYS = (("removal", "Removal"), ("land", "Land"), ("creature", "Kreatur"))
MINI_TAGS = ("arch", "color", "best", "hint", "plain", "head", "warn")  # Stile mit eigener Kasten-Form (mini_*)


def mini_rows(snap, slim=False):
    """Kleiner Kasten (minimiert): im Spiel die Chancen auf Removal, Land und Kreatur fuer die naechste Karte, im Draft
    Pick, Archetyp und die beste Karte des Packs (slim: Karten-Overlay zeigt das Pack, dann ohne Top-Pick und beste
    Karte)."""
    if not snap:
        return [("draftgott", "msg")]
    g = snap.get("game") or {}
    if g.get("active"):
        by = {r["key"]: r for r in g.get("groups") or []}
        rows = [(f"{t(label)} {_pct(by[key]['next'])}", {"land": "color", "removal": "arch"}.get(key, "plain"))
                for key, label in MINI_KEYS if key in by]
        tr = g.get("tricks")
        if tr and tr.get("hand") == 0:
            rows.append((t("Gegner ohne Handkarten"), "head"))
        elif tr:
            rows.append((t("Tricks {n} · offen {open}", n=len(tr['now']), open=tr['open']), "head"))
        return rows
    if snap.get("complete") and snap.get("deckinfo"):
        info = snap["deckinfo"]
        return [(_record(info) or t("Dein Deck"), "head"),
                (t("Kreaturen {c} · Removal {r}", c=info['creatures'], r=info['removal']), "arch")] + \
            [(f"{RATING_ABBR['matchwinner']} {name}", "hint") for name in info.get("top") or []]
    if snap.get("status") in ("pack", "waiting"):
        main = (snap.get("detect") or {}).get("main")
        head = f"Pick {snap.get('pick', 1)} · " + (_arch_name(snap, main) if main else t("offen"))
        rows = [(head, "head")]
        if not (slim and snap.get("pack")):
            rows += [(f"{MARK['best']} {h['name']}", "hint") for h in snap.get("hints") or []][:1]
        if snap.get("curve_warning"):
            rows.append(("⚠ " + t("Kurve zu hoch"), "warn"))
        if snap.get("pack"):
            if not slim:
                best = snap["pack"][0]
                rows.append((f"1. {best['name']}", best.get("level") or "plain"))
        else:
            rows.append((t("Warte auf Pack …"), "msg"))
        return rows
    return [("draftgott Live", "msg")]


def info_rows(info, main_name):
    """Kennzahlen der Picks (und im Archetyp) als kurze Zeilen."""
    def line(i):
        return t("Kreaturen {c} · Removal {r} ({p} P.) · Kartenfluss {f}", c=i['creatures'], r=i['removal'],
                 p=_num(i['removal_points']), f=i['flow'])
    rows = [(t("Picks {n}: ", n=info['cards']) + line(info), "sub")]
    if info.get("arch") and main_name:
        rows.append((t("In {name}: {n} Karten · ", name=main_name, n=info['arch']['cards']) + line(info["arch"]),
                     "sub"))
    return rows


def rows_for(snap, slim=False):
    """Zeilen [(Text, Stil)] fuer einen Stand von /api/live; Stile: head, sub, arch, color, never, plain, msg.
    slim (Karten-Overlay angeschaltet und kalibriert, packoverlay.covers_pack): Pack-Liste und Top-Pick-Zeilen stehen
    auf den Karten und fallen weg; Signale, Archetyp-Tracker und Tipps bleiben (Nutzer 14.11.2026)."""
    if not snap:
        return [("draftgott Live", "head"), (t("Drafthelper nicht erreichbar …"), "msg")]
    if (snap.get("game") or {}).get("active"):
        return game_rows(snap["game"])
    if snap.get("enemy_saved"):
        return ([(t("★ {n} Siege: aufgenommen in die Hall of Fame der Gegnerdecks",
                    n=saved_wins(snap["enemy_saved"])), "head2"),
                 (t("Gegnerdeck gespeichert: {name}", name=snap['enemy_saved']), "arch")]
                + rows_for(dict(snap, enemy_saved=None), slim))
    status = snap.get("status")
    if status in ("nolog", "idle", "off"):
        return [("draftgott Live", "head"), (snap.get("message") or t("Kein Live-Draft."), "msg")]
    if snap.get("complete") and snap.get("deckinfo"):
        return deck_rows(snap)
    detect = snap.get("detect") or {}
    main = detect.get("main")
    head = f"Pick {snap.get('pick', 1)} · " + (
        t("Archetyp: {name} ({main})", name=_arch_name(snap, main), main=main) +
        (t(" – eigene Wahl") if detect.get("manual") else "")
        if main else t("Archetyp: noch offen"))
    rows = [(head, "head")] + curve_rows(snap.get("curve_warning"), _arch_name(snap, main) if main else None)
    slim = slim and status != "waiting" and bool(snap.get("pack"))
    if status != "waiting" and not slim:
        rows += hint_rows(snap)
    scores =[s for s in detect.get("scores") or [] if s["score"]][:3]
    if scores:
        rows.append((" · ".join(f"{s['name']} {s['score']:g}" for s in scores), "sub"))
    rows += signal_rows(snap.get("signals"))
    if snap.get("draftinfo") and snap["draftinfo"].get("cards"):
        rows += info_rows(snap["draftinfo"], _arch_name(snap, main) if main else None)
    for a in snap.get("archmap") or []:
        text = f"{a['name']}: {a['count']} Pick{'s' if a['count'] != 1 else ''}"
        if a["pack"]:
            text += t(" · im Pack: ") + ", ".join(a["pack"])
        rows.append((text, "arch" if a["pack"] and a["colors"] == main else ("color" if a["pack"] else "sub")))
    if status == "waiting" or not snap.get("pack"):
        rows.append((t("Warte auf das nächste Pack …"), "msg"))
        return rows + tip_rows(snap, main)
    if slim:
        rows.append((t("Bewertungen stehen auf den Karten (Karten-Overlay)"), "msg"))
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
            parts.append(t("{p} % ({g} G.)", p=round(100 * stats['wins'] / stats['games']), g=stats['games']))
        rows.append(("  ".join(parts), tag))
    return rows + tip_rows(snap, main)


def curve_rows(w, arch_name):
    """Warnung "Mana-Kurve zu hoch" (livedraft.curve_warning) mit den Gruenden und einem Tipp; leer ohne Warnung."""
    if not w:
        return []
    from components import livedraft as ld
    head = ("⚠ " + t("Mana-Kurve zu hoch") + " · " +
            (t("{n} Zauber in {arch}", n=w["cards"], arch=arch_name) if arch_name else
             t("{n} Zauber", n=w["cards"])))
    rows = [(head, "warn")]
    if "avg" in w["reasons"]:
        rows.append((t("Ø Manawert {mv} (gut: bis {max})", mv=dec(f"{w['avg_mv']:g}"),
                       max=dec(f"{ld.CURVE_AVG_MAX:g}")), "warnsub"))
    if "heavy" in w["reasons"]:
        rows.append((t("{n} Karten mit 5+ Mana, auf 23 Zauber {x} (gut: höchstens {max})", n=w["heavy"],
                       x=w["heavy23"], max=ld.CURVE_HEAVY_MAX), "warnsub"))
    if "cheap" in w["reasons"]:
        rows.append(((t("Nur 1 Karte bis 2 Mana") if w["cheap"] == 1 else
                      t("Nur {n} Karten bis 2 Mana", n=w["cheap"])) +
                     t(", auf 23 Zauber {x} (gut: mindestens {min})", x=w["cheap23"], min=ld.CURVE_CHEAP_MIN),
                     "warnsub"))
    rows.append((t("Tipp: jetzt günstige Karten (bis 2–3 Mana) bevorzugen"), "warnsub"))
    return rows


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
    text = t("Signale ({fmt}): ", fmt=sig.get('format', 'Draft')) + " · ".join(
        f"{c} {t(SIGNAL_LABEL[v['level']])} {_signed(v['score'])}" for c, v in marked)
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
    return [(t("Tipps zu {name}", name=a['name']), "head2")] + [(f"• {tp}", "tip") for tp in a["tips"]]


def deck_button(snap):
    """(Beschriftung, klickbar?) des Knopfs "Deck uebernehmen" nach dem Draft, sonst None."""
    if not snap or not snap.get("complete") or (snap.get("game") or {}).get("active"):
        return None  # im Spiel stoert der Knopf nur
    deck = snap.get("deck") or {}
    if deck.get("applied"):
        return (t("Deck übernommen ✓"), False)
    if deck.get("ready"):
        return (t("Deck + Sideboard übernehmen ({main} + {side})", main=deck.get('main', 0),
                  side=deck.get('side', 0)), True)
    return (t("Nach „Fertig“ in Arena: Deck + Sideboard übernehmen"), False)


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
CONTROL_SIZE = (200, 156)  # Platz fuer Seitenfenster, Trick-Warner und Karten-Overlay mit "Kalibrieren"
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


FIT_MIN_HEIGHT = 120  # kleinste Hoehe eines angepassten Fensters
FIT_MARGIN = 48  # Platz unten fuer die Taskleiste


def fit_geometry(need, y, screen_height, min_height=FIT_MIN_HEIGHT, margin=FIT_MARGIN):
    """(Hoehe, y) eines Fensters, das need Pixel Inhalt braucht (Nutzer 14.11.2026: keine Zeilen abschneiden): so hoch
    wie noetig, mindestens min_height; reicht der Platz bis zum unteren Rand nicht, rutscht es nach oben, hoechstens
    bis Bildschirmhoehe ohne margin."""
    usable = max(min_height, screen_height - margin)
    h = min(max(need, min_height), usable)
    return h, max(0, min(y, usable - h))


def _content_height(text):
    """Pixel, die der Inhalt des Textfelds bei seiner jetzigen Breite braucht (mit Rand und eingebetteten Grafiken)."""
    text.update_idletasks()
    try:
        n = text.count("1.0", "end", "update", "ypixels")
    except Exception:  # noqa: BLE001 - aeltere Tk-Versionen ohne "update"
        n = text.count("1.0", "end", "ypixels")
    if isinstance(n, (tuple, list)):
        n = n[-1]
    return int(n or 0) + 2 * int(text.cget("pady")) + 2 * int(text.cget("bd")) + 4


def fit_window(win, text):
    """Passt die Hoehe des Fensters an den Inhalt seines Textfelds an (Breite bleibt, wie der Nutzer sie gezogen hat);
    unsichtbare oder noch nicht gezeichnete Fenster bleiben, wie sie sind."""
    if win.state() == "withdrawn":
        return
    win.update_idletasks()
    if text.winfo_width() < 50:
        return
    cur_y = win.winfo_y()
    if getattr(win, "_fit_last", None) != cur_y:  # vom Nutzer verschoben (oder neu): das ist die Wunschlage
        win._fit_home = cur_y
    extra = max(0, win.winfo_height() - text.winfo_height())  # Knopfleiste und Deck-Knopf
    deco = max(0, win.winfo_rooty() - cur_y)  # Titelleiste
    h, y = fit_geometry(_content_height(text) + extra, win._fit_home, win.winfo_screenheight() - deco)
    if (h, y) != (win.winfo_height(), cur_y):
        win.geometry(f"{win.winfo_width()}x{h}+{win.winfo_x()}+{y}")
        win.update_idletasks()
    win._fit_last = win.winfo_y()
    text.yview_moveto(0)


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
    return [(c, int(n)) for c, n in (part.split() for part in line.split(" ", 1)[1].split(" · "))]


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
    text.tag_configure("group", foreground=COLORS["muted"], font=("Segoe UI", 10, "bold"), spacing1=6, spacing3=1)
    text.tag_configure("warn", background=COLORS["warn"], foreground="#ffffff", font=("Segoe UI", 11, "bold"),
                       spacing1=3, spacing3=2)
    text.tag_configure("warnsub", foreground=COLORS["warnsub"], font=("Segoe UI", 9), lmargin1=6, lmargin2=6,
                       spacing3=1)
    for tag in ("arch", "color", "best", "hint", "plain", "head", "msg", "warn"):  # Kasten: groessere Schrift
        text.tag_configure("mini_" + tag, font=("Segoe UI", 13, "bold"), spacing1=3, spacing3=3,
                           background=COLORS[tag] if tag in ("arch", "color", "best", "hint", "warn") else COLORS["bg"],
                           foreground=COLORS["head"] if tag == "head" else (
                               "#ffffff" if tag == "warn" else COLORS["ink"]))


def run(url, interval_ms=1000):
    """Drei Fenster: das Steuerfenster (Hauptfenster, links) schaltet Seitenfenster und Trick-Warner an und ab;
    schliesst man es, ist alles zu. Dazu das Karten-Overlay ueber Arena (components/packoverlay.py) mit Schalter und
    Knopf "Kalibrieren" im Steuerfenster."""
    import os
    import tkinter as tk
    from components import packoverlay

    control = tk.Tk()
    control.title("draftgott")
    _float_window(control)
    control.geometry(control_geometry())
    tk.Label(control, text=t("draftgott Fenster"), bg=COLORS["bg"], fg=COLORS["head"],
             font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=8, pady=(4, 2))
    enabled = {key: tk.BooleanVar(value=on) for key, on in default_enabled().items()}

    root = tk.Toplevel(control)  # Seitenfenster: Draft, Deck und im Spiel die Bibliothek
    root.title("draftgott Live")
    _float_window(root)
    root.geometry(main_geometry(root.winfo_screenwidth()))
    tricks = tk.Toplevel(control)
    tricks.title(t("draftgott Tricks"))
    _float_window(tricks)
    tricks.geometry(trick_geometry())
    trick_text = tk.Text(tricks, bg=COLORS["bg"], fg=COLORS["ink"], bd=0, highlightthickness=0, wrap="word",
                         font=("Segoe UI", 11), padx=10, pady=4, cursor="arrow")
    trick_text.pack(fill="both", expand=True)
    windows = {"main": root, "tricks": tricks}
    for key, label in WINDOWS:
        tk.Checkbutton(control, text=t(label), variable=enabled[key], bg=COLORS["bg"], fg=COLORS["ink"],
                       selectcolor="#2c3a52", activebackground=COLORS["bg"], activeforeground=COLORS["ink"],
                       font=("Segoe UI", 10), anchor="w", command=lambda: show_windows()).pack(fill="x", padx=6)
        windows[key].protocol("WM_DELETE_WINDOW", lambda k=key: (enabled[k].set(False), show_windows()))

    cards_on = tk.BooleanVar(value=True)  # Karten-Overlay ueber Arena
    cards_row = tk.Frame(control, bg=COLORS["bg"])
    cards_row.pack(fill="x", padx=6)
    tk.Checkbutton(cards_row, text=t("Karten-Overlay"), variable=cards_on, bg=COLORS["bg"], fg=COLORS["ink"],
                   selectcolor="#2c3a52", activebackground=COLORS["bg"], activeforeground=COLORS["ink"],
                   font=("Segoe UI", 10), anchor="w").pack(side="left")
    tk.Button(cards_row, text=t("Kalibrieren"), font=("Segoe UI", 8), bg="#2c3a52", fg=COLORS["ink"], relief="flat",
              activebackground="#3b4d6b", padx=4, pady=0, cursor="hand2",
              command=lambda: start_calibration()).pack(side="right")
    cards_hint = tk.Label(control, text="", bg=COLORS["bg"], fg=COLORS["muted"], font=("Segoe UI", 8),
                          anchor="w", justify="left", wraplength=CONTROL_SIZE[0] - 12)
    cards_hint.pack(fill="x", padx=8)
    cards = packoverlay.PackOverlay(control)
    cards_state = {"cal": packoverlay.load_calibration(), "arena": {"found": False}, "busy": False}

    def start_calibration():
        arena = packoverlay.arena_window(os.getpid())
        if not arena.get("found") or arena.get("minimized"):
            cards_hint.configure(text=t("Arena nicht gefunden"))
            return
        cards_state["busy"] = True
        cards.hide()

        def done(cal):
            packoverlay.save_calibration(packoverlay.CAL_FILE, cal)
            cards_state["cal"] = cal

        cal_win = packoverlay.Calibrator(control, arena, done)
        cal_win.win.bind("<Destroy>", lambda e: cards_state.update(busy=False), add="+")

    def cards_tick():
        arena = packoverlay.arena_window(os.getpid())
        cards_state["arena"] = arena
        cal = cards_state["cal"]
        hint = packoverlay.status_text(cal, arena)
        if cards_hint.cget("text") != hint:
            cards_hint.configure(text=hint)
        snap = state["snap"]
        slim = packoverlay.covers_pack(cards_on.get(), snap, cal, arena)
        if slim != state["slim"]:
            state["slim"] = slim
            render()
        if not cards_state["busy"] and packoverlay.should_show(cards_on.get(), snap, cal, arena):
            try:
                views = packoverlay.pack_views(snap)
                hidden = packoverlay.hover_hidden(cal, len(views), arena["origin"], arena["size"],
                                                  packoverlay.cursor_pos())
                cards.show(views, cal, arena, hidden)
            except tk.TclError:
                pass
        else:
            cards.hide()
        control.after(100, cards_tick)  # schnell genug fuer das Hovern ueber Karten

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
    for tw in (text, trick_text):
        _styles(tw)
    state = {"last": None, "tricks": None, "seen": False, "misses": 0, "mini": False, "big": None, "snap": None,
             "party": None, "first": True, "blink": False, "slim": False}
    trick_tip_win = _bind_trick_tips(trick_text, lambda: trick_tips(state["snap"]))

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
            rows = [(line, "mini_" + (tag if tag in MINI_TAGS else "msg"))
                    for line, tag in mini_rows(snap, state["slim"])]
        else:
            rows = rows_for(snap, state["slim"])
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
            state["fit_main"] = True
        trows = trick_window_rows(snap)
        if trows != state["tricks"]:
            state["tricks"] = trows
            trick_tip_win.hide()
            _fill(trick_text, trows)
            state["fit_tricks"] = True
        show_windows()
        fit_all()

    def fit_all():
        """Fenster an den Inhalt anpassen, wenn er sich geaendert hat oder ein Fenster breiter/schmaler wurde."""
        for key, win, tw in (("main", root, text), ("tricks", tricks, trick_text)):
            width = tw.winfo_width()
            if state.get("fit_" + key) or state.get("width_" + key) != width:
                try:
                    fit_window(win, tw)
                except tk.TclError:
                    continue
                if win.state() != "withdrawn" and width >= 50:
                    state["fit_" + key], state["width_" + key] = False, width

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
    cards_tick()
    control.mainloop()
