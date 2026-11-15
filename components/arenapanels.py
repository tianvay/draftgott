"""Zwei Saeulen ueber Arena beim Draften (Nutzer 15.11.2026, Entwurf B "Zwei Saeulen"): Arenas Draft-Bildschirm
bleibt unveraendert, die Saeulen nutzen den freien Platz.

- Links neben dem Pack (deck_column): die Zahlen deines Decks - Kreaturen und Removal-Punkte gross mit Ziel-Balken
  (Kreaturen CREATURE_TARGET, Removal die gruene Schwelle des Berichts, 4 Punkte), Kurve, Farben, Kartenfluss und
  Spacecraft; alle Picks ausser Sideboard, ein Splash zaehlt also mit. Unten der Knopf "Picks & Sideboard".
- Zwischen Pack und Arenas Deckliste (pick_column): alles zum Pick - oben die Signale offener Farben als Manakreise,
  Warnung zur Kurve, Top-Pick (nur ohne Karten-Overlay, sonst steht er lila auf den Karten), Archetyp-Rangliste,
  Wechsel mit Sideboard und Tipps.
- Picks-Fenster (PicksPanel, ueber dem Pack, auf Klick): alle Picks nach Farbe und Manawert; ein Klick legt eine
  Karte ins Sideboard oder zurueck (POST /api/live/side wie "Aus" auf der Seite; die Seite uebernimmt den Stand).

Lage (column_rects) in Anteilen am Arena-Fenster, gemessen an Arenas Draft-Bildschirm bei 2000x1125; mit
Kalibrierung des Karten-Overlays richten sich die Saeulen nach dem Kartenraster. Passt das nicht (andere Aufloesung
oder anderes Seitenverhaeltnis), lassen sie sich selbst kalibrieren (ColumnCalibrator, vier Klicks: je Saeule oben
links und unten rechts; gespeichert in saeulen.json, nicht im Git). Die Saeulen lassen Klicks durch;
zeigt die Maus auf eine Karte, werden sie fast durchsichtig, damit Arenas grosse Kartenansicht frei bleibt.
Solange sie da sind und das Karten-Overlay das Pack zeigt, tritt das Seitenfenster "draftgott Live" zur Seite.
"""
import json
import pathlib

from components.i18n import dec, t
from components.removal import GREEN_PER_40, YELLOW_PER_40

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent.parent

CREATURE_TARGET = 15  # Kreaturen in einem Limited-Deck (40 Karten)
BASE_W = 2000  # Breite, an der die Lage gemessen ist (Screenshot des Nutzers)
DEFAULT_GRID = (0.144, 0.6465)  # linke und rechte Kante des Kartenrasters ohne Kalibrierung
TOP, DECK_BOTTOM, PICK_BOTTOM = 0.165, 0.905, 0.89  # unter den Nachbar-Bannern, ueber "Select" und Timer
EDGE, GAP, DECKLIST = 0.009, 0.006, 0.762  # Abstand zum Rand, zu den Karten, linke Kante von Arenas Deckliste
MIN_W = 0.06
SIGNAL_LABEL = {"open": "offen", "maybe": "evtl. offen", "contested": "umkämpft"}


def sections():
    """Abschnitts-Ueberschriften der Saeulen in der aktuellen Sprache."""
    return {"curve": t("KURVE"), "colors": t("FARBEN"), "more": t("WEITERES"), "archs": t("ARCHETYPEN"),
            "signals": t("SIGNALE"), "tips": t("TIPP"), "pack": t("PACK")}


def _num(x):
    return dec(f"{x:g}")


def _arch_name(snap, colors):
    for s in ((snap.get("detect") or {}).get("scores") or []) + (snap.get("archetypes") or []):
        if s["colors"] == colors:
            return s["name"]
    return colors


def bar_fraction(value, target):
    """Fuellung eines Ziel-Balkens (0 bis 1)."""
    if not target:
        return 0.0
    return max(0.0, min(1.0, value / target))


def _level(value, target, yellow=None):
    if value + 1e-9 >= target:
        return "green"
    if yellow is not None and value + 1e-9 >= yellow:
        return "yellow"
    return "progress"


def deck_column(snap):
    """Inhalt der linken Saeule oder None (noch kein Pick)."""
    info = (snap or {}).get("draftinfo") or {}
    if not info.get("cards"):
        return None
    main = (snap.get("detect") or {}).get("main")
    basis = info  # alle Picks ausser Sideboard: ein Splash zaehlt mit (Nutzer 15.11.2026)
    n_rem = basis.get("removal", 0)
    tiles = [{"key": "creatures", "label": t("KREATUREN"), "value": basis.get("creatures", 0),
              "target": CREATURE_TARGET, "big": str(basis.get("creatures", 0)),
              "unit": t("/ {n}", n=CREATURE_TARGET),
              "sub": t("{n} Karten im Plan", n=basis.get("cards", 0)),
              "level": _level(basis.get("creatures", 0), CREATURE_TARGET)},
             {"key": "removal", "label": t("REMOVAL"), "value": basis.get("removal_points", 0),
              "target": GREEN_PER_40, "big": _num(basis.get("removal_points", 0)),
              "unit": t("/ {n} P.", n=_num(GREEN_PER_40)),
              "sub": t("1 Karte") if n_rem == 1 else t("{n} Karten", n=n_rem),
              "level": _level(basis.get("removal_points", 0), GREEN_PER_40, YELLOW_PER_40)}]
    more = [(t("Kartenfluss"), str(basis.get("flow", 0)))]
    if basis.get("spacecraft"):
        more.append(("Spacecraft", str(basis["spacecraft"])))
    return {"title": t("DEIN DECK") + (f" · {_arch_name(snap, main)}" if main else ""), "tiles": tiles,
            "curve": list(basis.get("curve") or [0] * 6), "colors": list((basis.get("colors") or {}).items()),
            "more": more}


def _signed(n):
    return f"+{_num(n)}" if n > 0 else (f"−{_num(-n)}" if n < 0 else "0")


PACK_ROWS = 8  # Rangliste des Packs in der rechten Saeule (nur ohne Karten-Overlay)
RATING_ABBR = {"matchwinner": "♛", "splashworthy": "★", "mustplay": "MP", "playable": "Pl", "filler": "Fi",
               "neverplay": "NP"}


def _pack_row(i, c):
    text = f"{i}. {c['name']}"
    if c.get("rating"):
        text += "  " + RATING_ABBR.get(c["rating"], c["rating"])
    if c.get("removal"):
        text += f"  R{_num(c['removal'])}"
    level = "never" if c.get("rating") == "neverplay" else (c.get("level") or "plain")
    return {"name": c["name"], "text": text, "level": level}


def pick_column(snap, slim=False):
    """Inhalt der rechten Saeule (zwischen Pack und Deckliste). slim: Karten-Overlay zeigt das Pack (Top-Pick steht
    dann auf den Karten)."""
    from components import overlay
    snap = snap or {}
    detect = snap.get("detect") or {}
    main = detect.get("main")
    name = _arch_name(snap, main) if main else None
    note = (f"{name} ({main})" + (t(" – eigene Wahl") if detect.get("manual") else "") if main
            else t("Archetyp: noch offen"))
    waiting = snap.get("status") == "waiting" or not snap.get("pack")
    hints = [] if waiting or slim else [h["name"] for h in snap.get("hints") or []]
    archs = [(s["name"], _num(s["score"]), s["colors"] == main)
             for s in detect.get("scores") or [] if s.get("score")][:3]
    sig = (snap.get("signals") or {}).get("colors") or {}
    marked = sorted(((c, v) for c, v in sig.items() if v.get("level")),
                    key=lambda cv: (-cv[1]["score"], "WUBRG".find(cv[0])))
    signals = [(f"{c} {t(SIGNAL_LABEL[v['level']])} {_signed(v['score'])}", v["level"]) for c, v in marked]
    dots = [(c, v["level"], _signed(v["score"])) for c, v in marked]
    sw = detect.get("switch")
    n_side = sum((snap.get("side") or {}).values())
    switch = ("↔ " + t("{name} · Sideboard {n} Karte(n)", name=sw["name"], n=n_side)) if sw else None
    arch = next((a for a in snap.get("archetypes") or [] if main and a["colors"] == main), None)
    pack = [] if waiting or slim else [_pack_row(i, c) for i, c in enumerate(snap["pack"][:PACK_ROWS], 1)]
    return {"head": f"Pick {snap.get('pick', 1)}", "arch_note": note, "pack": pack,
            "warn": [line for line, _ in overlay.curve_rows(snap.get("curve_warning"), name)],
            "hints": hints, "archs": archs, "signals": signals, "dots": dots, "switch": switch,
            "state": t("Warte auf das nächste Pack …") if waiting else None,
            "tips": list((arch or {}).get("tips") or [])}


PICK_GROUPS = ("W", "U", "B", "R", "G", "Mehrfarbig", "Farblos", "Länder")


def _group(c):
    if c.get("land"):
        return "Länder"
    cols = c.get("colors") or []
    return "Farblos" if not cols else (cols[0] if len(cols) == 1 else "Mehrfarbig")


def picks_groups(snap):
    """Picks fuer das Picks-Fenster: [(Gruppe, [{"name", "mv", "creature", "removal", "sb"}])] nach Farbe (leere
    Gruppen fehlen), je Gruppe nach Manawert und Name. Von mehreren Kopien liegen die letzten im Sideboard (wie
    livedraft._split_picks)."""
    cards = (snap or {}).get("pickcards") or []
    side = (snap or {}).get("side") or {}
    total, seen, groups = {}, {}, {g: [] for g in PICK_GROUPS}
    for c in cards:
        total[c["name"]] = total.get(c["name"], 0) + 1
    for c in cards:
        i = seen[c["name"]] = seen.get(c["name"], 0) + 1
        groups[_group(c)].append({"name": c["name"], "mv": int(c.get("mv") or 0), "creature": bool(c.get("creature")),
                                  "removal": c.get("removal") or 0,
                                  "sb": i > total[c["name"]] - side.get(c["name"], 0)})
    out = []
    for g in PICK_GROUPS:
        if groups[g]:  # sortiert stabil: Kopien eines Namens behalten ihre Reihenfolge (Sideboard zuletzt)
            out.append((t(g) if len(g) > 1 else g, sorted(groups[g], key=lambda e: (e["mv"], e["name"]))))
    return out


def toggle_side(side, name, sb):
    """Neues Sideboard nach einem Klick: Karte aus dem Sideboard zurueck ins Deck (sb) oder ins Sideboard."""
    out = dict(side or {})
    out[name] = out.get(name, 0) + (-1 if sb else 1)
    return {n: v for n, v in out.items() if v > 0}


def picks_head(snap):
    n = len((snap or {}).get("pickcards") or [])
    s = sum(((snap or {}).get("side") or {}).values())
    return t("Picks {n} · im Deck {d} · Sideboard {s}", n=n, d=n - s, s=s)


def picks_button(snap, is_open):
    """Text des Knopfs unten in der linken Saeule, None ohne Picks."""
    n = len((snap or {}).get("pickcards") or [])
    if not n:
        return None
    s = sum(((snap or {}).get("side") or {}).values())
    return ("▾ " if is_open else "▸ ") + t("Picks & Sideboard") + f" ({n} · " + t("Sideboard {s}", s=s) + ")"


def picks_help():
    return t("Klick auf eine Karte: ins Sideboard oder zurück ins Deck")


def picks_rect(size, cal, colcal=None):
    """Picks-Fenster ueber dem Pack: zwischen linker Saeule und rechter Kante der rechten Saeule, so hoch wie die linke."""
    r = column_rects(size, cal, colcal)
    dx, dy, dw, dh = r["deck"]
    px, _, pw, _ = r["pick"]
    x = dx + dw + round(GAP * size[0])
    return x, dy, max(200, px + pw - x), dh


def send_side(url, side, timeout=3):
    """Sideboard an den Drafthelper (wie "Aus" auf der Seite); Antwort oder None."""
    import urllib.error
    import urllib.request
    req = urllib.request.Request(url.rstrip("/") + "/api/live/side", data=json.dumps({"side": side}).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None


def active(enabled, snap, arena):
    """Saeulen gehoeren auf den Bildschirm: beim Draften (Pack oder Warten, nicht fertig, nicht im Spiel) mit Arena
    offen; ohne Vordergrund, damit das Seitenfenster beim Alt-Tab nicht springt."""
    if not (enabled and snap and (arena or {}).get("found")) or arena.get("minimized"):
        return False
    if snap.get("status") not in ("pack", "waiting") or snap.get("complete"):
        return False
    return not (snap.get("game") or {}).get("active")


def should_draw(enabled, snap, arena):
    """Saeulen zeichnen: aktiv und Arena (oder ein eigenes Fenster) im Vordergrund."""
    return active(enabled, snap, arena) and bool(arena.get("foreground"))


def _grid(cal):
    """Linke und rechte Kante des Kartenrasters (Anteile); unplausible Kalibrierung: Standardlage."""
    if not cal:
        return DEFAULT_GRID
    try:
        left = cal["x"]
        right = cal["x"] + (cal["cols"] - 1) * cal["dx"] + cal["w"]
    except (KeyError, TypeError):
        return DEFAULT_GRID
    if left - GAP - EDGE < MIN_W or DECKLIST - right - GAP < MIN_W or right <= left:
        return DEFAULT_GRID
    return left, right


COL_FILE = SCRIPT_DIR / "saeulen.json"
MIN_COL_W = 0.03  # schmaler als 3 % der Fensterbreite: wohl verklickt
CAL_STEPS = ("Linke Säule (dein Deck): Ecke oben links anklicken",
             "Linke Säule (dein Deck): Ecke unten rechts anklicken",
             "Rechte Säule (der Pick): Ecke oben links anklicken",
             "Rechte Säule (der Pick): Ecke unten rechts anklicken")


def calibrate_columns(clicks, size):
    """Lage der Saeulen aus vier Klicks (Pixel im Arena-Fenster): je Saeule oben links und unten rechts. Ergebnis in
    Anteilen am Fenster {"deck": [x, y, w, h], "pick": [...], "size": [w, h]}; ValueError bei unpassenden Klicks."""
    if len(clicks) != 4:
        raise ValueError(t("Für die Säulen braucht es genau vier Klicks."))
    cw, ch = size
    out = {"size": [cw, ch]}
    for key, ((x1, y1), (x2, y2)) in zip(("deck", "pick"), (clicks[:2], clicks[2:])):
        if x2 <= x1 or y2 <= y1:
            raise ValueError(t("Die Ecke unten rechts muss rechts unter der Ecke oben links liegen."))
        if (x2 - x1) / cw < MIN_COL_W or (y2 - y1) / ch < MIN_COL_W:
            raise ValueError(t("Die Säule ist zu klein."))
        out[key] = [x1 / cw, y1 / ch, (x2 - x1) / cw, (y2 - y1) / ch]
    return out


def load_column_calibration(path=COL_FILE):
    try:
        cal = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    ok = isinstance(cal, dict) and all(isinstance(cal.get(k), list) and len(cal[k]) == n
                                       for k, n in (("deck", 4), ("pick", 4), ("size", 2)))
    return cal if ok else None


def save_column_calibration(path, cal):
    """Speichert die Kalibrierung; None: zurueck zur Standardlage (Datei geloescht)."""
    path = pathlib.Path(path)
    if cal is None:
        path.unlink(missing_ok=True)
        return
    path.write_text(json.dumps(cal, indent=1) + "\n", encoding="utf-8")


def _col_cal_fits(colcal, size):
    from components.packoverlay import size_changed
    return bool(colcal) and not size_changed(colcal, size)


def column_status(colcal, arena):
    """Hinweis zur Lage der Saeulen fuer das Steuerfenster ("" = eigene Kalibrierung passt)."""
    if not (arena or {}).get("found"):
        return ""
    if not colcal:
        return t("Säulen: Standardlage")
    if not _col_cal_fits(colcal, arena["size"]):
        return t("Arena-Fenster anders proportioniert: Säulen neu kalibrieren")
    return ""


def calibration_title(step):
    return t("Säulen kalibrieren ({n}/4): ", n=step + 1) + t(CAL_STEPS[step])


def calibration_help():
    return t("Gestrichelt: jetzige Lage. Esc bricht ab, Entf stellt die Standardlage wieder her.")


def column_rects(size, cal, colcal=None):
    """Rechtecke (x, y, Breite, Hoehe) der Saeulen im Arena-Fenster: "deck" links, "pick" rechts (Hoehe ist die
    groesste; das Fenster passt sich dem Inhalt an). Vorrang: eigene Kalibrierung der Saeulen (colcal, nur bei
    gleichem Seitenverhaeltnis), dann das Kartenraster (cal), sonst die Standardlage."""
    w, h = size
    if _col_cal_fits(colcal, size):
        return {key: (round(colcal[key][0] * w), round(colcal[key][1] * h), round(colcal[key][2] * w),
                      round(colcal[key][3] * h)) for key in ("deck", "pick")}
    left, right = _grid(cal)
    deck = (round(EDGE * w), round(TOP * h), round((left - GAP - EDGE) * w), round((DECK_BOTTOM - TOP) * h))
    px = right + GAP / 2 + 0.0005
    pick = (round(px * w), round(TOP * h), round((DECKLIST - px) * w), round((PICK_BOTTOM - TOP) * h))
    return {"deck": deck, "pick": pick}


# ---------------------------------------------------------------- Zeichnen (tkinter)

PANEL, TILE, LINE = "#12161f", "#1c2330", "#2c3a52"
INK, MUTED, HEAD = "#e8ecf3", "#8d97a8", "#ffd166"
LEVEL = {"progress": "#4f8cc9", "yellow": "#e0b93a", "green": "#2fae66"}
PILL = {"warn": "#b4462a", "hint": "#8e2bd6", "open": "#1f7a45", "maybe": "#2c3a52", "contested": "#6b3a2a",
        "switch": "#2c3a52"}
MANA_FILL = {"W": "#f3ecd2", "U": "#4a90d9", "B": "#6b5f7a", "R": "#e0533d", "G": "#3f9b5a"}
MANA_INK = {"W": "#161b24"}
ALPHA, FADED = 0.93, 0.18
BASE_COL_W = {"deck": 250, "pick": 215}  # Breite der Saeulen bei BASE_W, fuer die die Schrift gemacht ist


class _Pen:
    """Zeichnet von oben nach unten auf ein Canvas (y waechst mit)."""

    def __init__(self, cv, width, s):
        self.cv, self.s = cv, s
        self.pad = round(12 * s)
        self.x0, self.x1 = self.pad, width - self.pad
        self.y = self.pad

    def font(self, px, bold=False):
        return ("Segoe UI", -max(9, round(px * self.s)), "bold" if bold else "normal")

    def px(self, n):
        return round(n * self.s)

    def text(self, text, px=17, color=INK, bold=False, gap=4, x=None):
        tid = self.cv.create_text(x if x is not None else self.x0, self.y, text=text, fill=color,
                                  font=self.font(px, bold), anchor="nw", width=self.x1 - (x or self.x0))
        self.y = self.cv.bbox(tid)[3] + self.px(gap)

    def section(self, label):
        self.y += self.px(8)
        self.text(label, 13, MUTED, True, 3)

    def tile(self, tile):
        cv, top = self.cv, self.y
        inner = self.x0 + self.px(10)
        self.y += self.px(6)
        self.text(tile["label"], 13, MUTED, True, 0, x=inner)
        color = LEVEL[tile["level"]]
        big = cv.create_text(inner, self.y, text=tile["big"], fill=color, font=self.font(46, True), anchor="nw")
        bx = cv.bbox(big)
        cv.create_text(bx[2] + self.px(6), bx[3] - self.px(10), text=tile["unit"], fill=MUTED,
                       font=self.font(20, True), anchor="sw")
        self.y = bx[3] + self.px(2)
        bar_h = self.px(8)
        cv.create_rectangle(inner, self.y, self.x1 - self.px(10), self.y + bar_h, fill=LINE, width=0)
        frac = bar_fraction(tile["value"], tile["target"])
        if frac:
            cv.create_rectangle(inner, self.y, inner + (self.x1 - self.px(10) - inner) * frac, self.y + bar_h,
                                fill=color, width=0)
        self.y += bar_h + self.px(4)
        self.text(tile["sub"], 14, MUTED, gap=6, x=inner)
        rect = cv.create_rectangle(self.x0, top, self.x1, self.y, fill=TILE, width=0)
        cv.tag_lower(rect)
        self.y += self.px(8)

    def curve(self, counts):
        cv = self.cv
        height, label = self.px(62), self.px(18)
        top, base = self.y + self.px(16), self.y + self.px(16) + height
        n = len(counts)
        slot = (self.x1 - self.x0) / n
        peak = max(counts) or 1
        for i, (lab, c) in enumerate(zip(("≤1", "2", "3", "4", "5", "6+"), counts)):
            x0, x1 = self.x0 + i * slot + slot * 0.12, self.x0 + (i + 1) * slot - slot * 0.12
            y0 = base - height * c / peak
            if c:
                cv.create_rectangle(x0, y0, x1, base, width=0, fill=HEAD if c == peak else LEVEL["progress"])
            cv.create_text((x0 + x1) / 2, y0 - 2, text=str(c), fill=INK, font=self.font(13, True), anchor="s")
            cv.create_text((x0 + x1) / 2, base + 2, text=lab, fill=MUTED, font=self.font(13), anchor="n")
        cv.create_line(self.x0, base, self.x1, base, fill=LINE)
        self.y = base + label + self.px(4)

    def colors(self, parts):
        total = sum(n for _, n in parts)
        if not total:
            return
        h, x, width = self.px(22), self.x0, self.x1 - self.x0
        for c, n in parts:
            x2 = x + width * n / total
            self.cv.create_rectangle(x, self.y, x2, self.y + h, width=0, fill=MANA_FILL.get(c, "#8d97a8"))
            if x2 - x >= self.px(34):
                self.cv.create_text((x + x2) / 2, self.y + h / 2, text=f"{c} {n}", fill=MANA_INK.get(c, "#ffffff"),
                                    font=self.font(13, True))
            x = x2
        self.y += h + self.px(6)

    def row(self, label, value, me=False):
        color = HEAD if me else INK
        lid = self.cv.create_text(self.x0, self.y, text=label, fill=color, font=self.font(17, me), anchor="nw",
                                  width=(self.x1 - self.x0) * 0.75)
        self.cv.create_text(self.x1, self.y, text=value, fill=color, font=self.font(17, me), anchor="ne")
        self.y = self.cv.bbox(lid)[3] + self.px(3)

    def dots(self, dots):
        """Signale offener Farben als Manakreise mit Zahl: offen gross mit hellem Ring, evtl. offen normal,
        umkaempft klein und grau."""
        x = self.x0
        big = self.px(30)
        top = self.y + self.px(2)
        for color, level, score in dots:
            r = big / 2 if level == "open" else (big * 0.4 if level == "maybe" else big * 0.3)
            cx, cy = x + big / 2, top + big / 2
            fill = MANA_FILL.get(color, "#8d97a8") if level != "contested" else "#4a5060"
            ring = {"open": "#7dffb0", "maybe": "#c8d3e0"}.get(level, "#4a5060")
            self.cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill=fill, outline=ring,
                                width=self.px(3) if level == "open" else 1)
            self.cv.create_text(cx, cy, text=color, fill=MANA_INK.get(color, "#ffffff") if level != "contested"
                                else "#c8d3e0", font=self.font(15 if level == "open" else 12, True))
            sid = self.cv.create_text(x + big + self.px(3), cy, text=score, anchor="w",
                                      fill="#7dffb0" if level == "open" else MUTED,
                                      font=self.font(16 if level == "open" else 13, True))
            x = self.cv.bbox(sid)[2] + self.px(10)
            if x > self.x1 - big:  # Zeile voll
                x, top = self.x0, top + big + self.px(4)
        self.y = top + big + self.px(8)

    def pack_row(self, row):
        """Zeile der Rangliste: Hintergrund nach Passung (lila beste, gruen Archetyp, blau Farben), NeverPlay grau."""
        fill = {"best": "#6d28b8", "arch": "#1f7a45", "color": "#2c3a52"}.get(row["level"])
        tid = self.cv.create_text(self.x0 + self.px(6), self.y + self.px(2), text=row["text"], anchor="nw",
                                  fill="#6b7280" if row["level"] == "never" else INK,
                                  font=self.font(15, row["level"] in ("best", "arch")),
                                  width=self.x1 - self.x0 - self.px(10))
        bottom = self.cv.bbox(tid)[3] + self.px(2)
        if fill:
            self.cv.tag_lower(self.cv.create_rectangle(self.x0, self.y, self.x1, bottom, fill=fill, width=0), tid)
        self.y = bottom + self.px(3)

    def button(self, text, tag):
        """Klickbarer Knopf ueber die ganze Breite (Canvas-Tag tag)."""
        pad = self.px(8)
        tid = self.cv.create_text(self.x0 + pad, self.y + pad, text=text, fill=INK, anchor="nw",
                                  font=self.font(15, True), width=self.x1 - self.x0 - 2 * pad, tags=(tag,))
        bottom = self.cv.bbox(tid)[3] + pad
        rect = self.cv.create_rectangle(self.x0, self.y, self.x1, bottom, fill="#2c3a52", outline="#4f8cc9",
                                        tags=(tag,))
        self.cv.tag_lower(rect, tid)
        self.y = bottom + self.px(4)

    def pills(self, items):
        """Schilder nebeneinander, Umbruch, wenn die Zeile voll ist; zu lange brechen selbst um."""
        x, line_h = self.x0, 0
        for text, kind in items:
            pad = self.px(7)
            tid = self.cv.create_text(x + pad, self.y + self.px(3), text=text, fill="#ffffff", anchor="nw",
                                      font=self.font(15, kind in ("warn", "hint")),
                                      width=self.x1 - self.x0 - 2 * pad)
            bx = self.cv.bbox(tid)
            if bx[2] + pad > self.x1 and x > self.x0:  # neue Zeile
                self.y += line_h + self.px(4)
                x, line_h = self.x0, 0
                self.cv.coords(tid, x + pad, self.y + self.px(3))
                bx = self.cv.bbox(tid)
            rect = self.cv.create_rectangle(x, self.y, bx[2] + pad, bx[3] + self.px(3), fill=PILL[kind], width=0)
            self.cv.tag_lower(rect, tid)
            line_h = max(line_h, bx[3] + self.px(3) - self.y)
            x = bx[2] + pad + self.px(5)
        if items:
            self.y += line_h + self.px(6)


def draw_deck(pen, col):
    sec = sections()
    pen.text(col["title"], 14, MUTED, True, 6)
    for tile in col["tiles"]:
        pen.tile(tile)
    pen.section(sec["curve"])
    pen.curve(col["curve"])
    if col["colors"]:
        pen.section(sec["colors"])
        pen.colors(col["colors"])
    pen.section(sec["more"])
    for label, value in col["more"]:
        pen.row(label, value)
    if col.get("button"):
        pen.y += pen.px(10)
        pen.button(col["button"], "picks")


def draw_pick(pen, col):
    sec = sections()
    pen.text(col["head"], 22, HEAD, True, 0)
    pen.text(col["arch_note"], 15, MUTED, gap=6)
    if col["dots"]:
        pen.dots(col["dots"])
    if col["warn"]:
        pen.pills([(col["warn"][0], "warn")])
        for line in col["warn"][1:]:
            pen.text(line, 13, "#ffb59e", gap=1)
        pen.y += pen.px(4)
    if col["hints"]:
        pen.pills([("◆ " + t("Top-Pick: {name}", name=n), "hint") for n in col["hints"]])
    if col["state"]:
        pen.text(col["state"], 15, MUTED, gap=4)
    if col["pack"]:
        pen.section(sec["pack"])
        for row in col["pack"]:
            pen.pack_row(row)
    if col["archs"]:
        pen.section(sec["archs"])
        for name, score, me in col["archs"]:
            pen.row(name, score, me)
    if col["switch"]:
        pen.y += pen.px(6)
        pen.pills([(col["switch"], "switch")])
    if col["tips"]:
        pen.section(sec["tips"])
        for tip in col["tips"]:
            pen.text("• " + tip, 15, INK, gap=3)


def _no_activate(win):
    """Fenster nimmt Klicks an, aber keinen Fokus (Arena bleibt aktiv) und erscheint nicht in der Taskleiste
    (Windows; sonst ohne Wirkung)."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetParent(win.winfo_id()) or win.winfo_id()
        style = user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
        user32.SetWindowLongW(hwnd, -20, style | 0x8000000 | 0x80)  # WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW
    except (ImportError, AttributeError, OSError):
        pass


class ArenaColumns:
    """Die zwei Saeulen als randlose Fenster ueber Arena. Die rechte laesst Klicks durch; die linke liegt auf freiem
    Platz und nimmt Klicks fuer den Knopf "Picks & Sideboard" an (on_picks)."""

    def __init__(self, master, on_picks=None):
        import tkinter as tk
        from components.packoverlay import _click_through
        self.wins, self.canvases, self.last = {}, {}, {}
        self.picks_open = False
        for key in ("deck", "pick"):
            win = tk.Toplevel(master)
            win.overrideredirect(True)
            win.attributes("-topmost", True)
            try:
                win.attributes("-alpha", ALPHA)
            except tk.TclError:
                pass
            win.configure(bg=PANEL)
            cv = tk.Canvas(win, bg=PANEL, highlightthickness=1, highlightbackground="#3a4558", bd=0)
            cv.pack(fill="both", expand=True)
            win.withdraw()
            win.update_idletasks()
            if key == "deck":
                _no_activate(win)
                cv.tag_bind("picks", "<Button-1>", lambda e: on_picks and on_picks())
                cv.tag_bind("picks", "<Enter>", lambda e, c=cv: c.configure(cursor="hand2"))
                cv.tag_bind("picks", "<Leave>", lambda e, c=cv: c.configure(cursor=""))
            else:
                _click_through(win)
            self.wins[key], self.canvases[key] = win, cv
        self.faded = None

    def hide(self):
        for win in self.wins.values():
            if win.state() != "withdrawn":
                win.withdraw()
        self.last = {}

    def show(self, snap, cal, arena, slim=False, faded=False, colcal=None):
        (ox, oy), size = arena["origin"], arena["size"]
        s = size[0] / BASE_W
        rects = column_rects(size, cal, colcal)
        contents = {"deck": deck_column(snap), "pick": pick_column(snap, slim)}
        if contents["deck"] is not None:
            contents["deck"]["button"] = picks_button(snap, self.picks_open)
        for key, win in self.wins.items():
            col = contents[key]
            if col is None:
                if win.state() != "withdrawn":
                    win.withdraw()
                self.last.pop(key, None)
                continue
            x, y, w, h = rects[key]
            sig = (repr(col), x, y, w, h, ox, oy)
            if win.state() == "withdrawn":
                win.deiconify()
                win.attributes("-topmost", True)
            if self.last.get(key) == sig:
                continue
            self.last[key] = sig
            cv = self.canvases[key]
            cv.delete("all")
            cv.configure(width=w)
            pen = _Pen(cv, w, min(s, w / BASE_COL_W[key]))  # schmal kalibriert: Schrift kleiner
            (draw_deck if key == "deck" else draw_pick)(pen, col)
            need = min(h, pen.y + pen.pad)
            win.geometry(f"{w}x{need}+{ox + x}+{oy + y}")
        if faded != self.faded:
            self.faded = faded
            for win in self.wins.values():
                try:
                    win.attributes("-alpha", FADED if faded else ALPHA)
                except Exception:  # noqa: BLE001 - ohne Durchsichtigkeit bleibt es einfach sichtbar
                    pass


class PicksPanel:
    """Picks-Fenster ueber dem Pack (auf Klick "Picks & Sideboard"): alle Picks nach Farbe in Spalten, je nach
    Manawert; ein Klick auf eine Karte ruft on_toggle(Name, im Sideboard?) auf. Nimmt Klicks an, aber keinen Fokus."""

    def __init__(self, master, on_toggle, on_close):
        import tkinter as tk
        self.on_toggle, self.on_close, self.entries, self.last = on_toggle, on_close, {}, None
        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        try:
            self.win.attributes("-alpha", 0.97)
        except tk.TclError:
            pass
        self.win.configure(bg=PANEL)
        self.cv = tk.Canvas(self.win, bg=PANEL, highlightthickness=2, highlightbackground="#4f8cc9", bd=0)
        self.cv.pack(fill="both", expand=True)
        self.win.withdraw()
        self.win.update_idletasks()
        _no_activate(self.win)
        self.cv.tag_bind("entry", "<Button-1>", self._click)
        self.cv.tag_bind("entry", "<Enter>", lambda e: self.cv.configure(cursor="hand2"))
        self.cv.tag_bind("entry", "<Leave>", lambda e: self.cv.configure(cursor=""))
        self.cv.tag_bind("close", "<Button-1>", lambda e: on_close())

    def hide(self):
        if self.win.state() != "withdrawn":
            self.win.withdraw()
        self.last = None

    def _click(self, _e):
        cur = self.cv.find_withtag("current")
        for tag in self.cv.gettags(cur[0]) if cur else ():
            if tag in self.entries:
                self.on_toggle(*self.entries[tag])
                return

    def show(self, snap, rect, origin, s):
        (ox, oy), (x, y, w, h) = origin, rect
        groups = picks_groups(snap)
        sig = (repr(groups), picks_head(snap), x, y, w, h, ox, oy)
        if self.win.state() == "withdrawn":
            self.win.deiconify()
            self.win.attributes("-topmost", True)
        if sig == self.last:
            return
        self.last = sig
        for scale in (1.0, 0.85, 0.72, 0.6):  # viele Picks: kleiner, bis es passt
            need = self._draw(groups, snap, w, s * scale)
            if need <= h:
                break
        self.win.geometry(f"{w}x{min(h, need)}+{ox + x}+{oy + y}")

    def _draw(self, groups, snap, w, s):
        cv = self.cv
        cv.delete("all")
        self.entries = {}
        pen = _Pen(cv, w, s)
        cid = cv.create_text(pen.x1, pen.y, text="✕", fill=INK, font=pen.font(22, True), anchor="ne",
                             tags=("close",))
        bx = cv.bbox(cid)
        cv.tag_lower(cv.create_rectangle(bx[0] - pen.px(6), bx[1] - pen.px(2), bx[2] + pen.px(6), bx[3] + pen.px(2),
                                         fill="#2c3a52", width=0, tags=("close",)), cid)
        pen.x1 = bx[0] - pen.px(12)
        pen.text(picks_head(snap), 20, HEAD, True, 2)
        pen.text(picks_help(), 14, MUTED, gap=10)
        pen.x1 = w - pen.pad
        if not groups:
            return pen.y + pen.pad
        gap = pen.px(12)
        n = len(groups)
        colw = (pen.x1 - pen.x0 - gap * (n - 1)) / n
        top, bottom, i = pen.y, pen.y, 0
        for k, (label, entries) in enumerate(groups):
            x0 = pen.x0 + k * (colw + gap)
            y = top
            fill = MANA_FILL.get(label, "#3a4558")
            lid = cv.create_text(x0 + pen.px(8), y + pen.px(3), text=f"{label} · {len(entries)}", anchor="nw",
                                 fill=MANA_INK.get(label, "#ffffff"), font=pen.font(15, True))
            lb = cv.bbox(lid)
            cv.tag_lower(cv.create_rectangle(x0, y, x0 + colw, lb[3] + pen.px(3), fill=fill, width=0), lid)
            y = lb[3] + pen.px(8)
            for e in entries:
                tag = f"e{i}"
                i += 1
                self.entries[tag] = (e["name"], e["sb"])
                text = f"{e['mv']}  {e['name']}" + ("  ●" if e["creature"] else "")
                font = pen.font(15)
                if e["sb"]:
                    text = "SB  " + text
                    font = font + ("overstrike",)
                tid = cv.create_text(x0 + pen.px(6), y + pen.px(2), text=text, anchor="nw", width=colw - pen.px(10),
                                     fill=MUTED if e["sb"] else INK, font=font, tags=("entry", tag))
                eb = cv.bbox(tid)
                cv.tag_lower(cv.create_rectangle(x0, y, x0 + colw, eb[3] + pen.px(2),
                                                 fill="#161a22" if e["sb"] else TILE, width=0, tags=("entry", tag)),
                             tid)
                y = eb[3] + pen.px(5)
            bottom = max(bottom, y)
        return bottom + pen.pad


class ColumnCalibrator:
    """Kalibrierung der Saeulen: halbdurchsichtiges Fenster ueber Arena faengt vier Klicks und zeigt gestrichelt die
    jetzige Lage; Esc bricht ab, Entf stellt die Standardlage wieder her. done(colcal oder None) danach."""

    def __init__(self, master, arena, current, done):
        import tkinter as tk
        (ox, oy), (cw, ch) = arena["origin"], arena["size"]
        self.arena, self.current, self.done, self.clicks = arena, current, done, []
        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        try:
            self.win.attributes("-alpha", 0.45)
        except tk.TclError:
            pass
        self.win.geometry(f"{cw}x{ch}+{ox}+{oy}")
        self.canvas = tk.Canvas(self.win, bg="#000000", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.click)
        self.win.bind("<Escape>", lambda e: self.close())
        self.win.bind("<Delete>", lambda e: self.finish(None))
        self.win.focus_force()
        self.draw()

    def draw(self, error=""):
        c = self.canvas
        c.delete("all")
        w = int(self.arena["size"][0])
        for x, y, rw, rh in self.current.values():  # jetzige Lage
            c.create_rectangle(x, y, x + rw, y + rh, outline="#ffd166", width=2, dash=(6, 4))
        if len(self.clicks) >= 2:  # linke Saeule schon fertig
            (x1, y1), (x2, y2) = self.clicks[:2]
            c.create_rectangle(x1, y1, x2, y2, outline="#2fae66", width=3)
        c.create_rectangle(0, 0, w, 70, fill="#161b24", outline="")
        c.create_text(w // 2, 22, fill="#ffd166", font=("Segoe UI", 16, "bold"),
                      text=calibration_title(len(self.clicks)))
        c.create_text(w // 2, 50, fill="#ff8a8a" if error else "#e8ecf3", font=("Segoe UI", 11),
                      text=error or calibration_help())
        for x, y in self.clicks:
            c.create_oval(x - 6, y - 6, x + 6, y + 6, outline="#ffd166", width=3)

    def click(self, e):
        self.clicks.append((e.x, e.y))
        if len(self.clicks) < 4:
            self.draw()
            return
        try:
            cal = calibrate_columns(self.clicks, self.arena["size"])
        except ValueError as err:
            self.clicks = []
            self.draw(str(err) + " " + t("Bitte noch einmal von vorn."))
            return
        self.finish(cal)

    def finish(self, cal):
        self.close()
        self.done(cal)

    def close(self):
        try:
            self.win.destroy()
        except Exception:  # noqa: BLE001 - schon geschlossen
            pass
