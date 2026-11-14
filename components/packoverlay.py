"""Karten-Overlay: legt beim Draften die Zahlen zu jeder Karte direkt auf die Karten im Arena-Fenster.

Das Arena-Protokoll nennt die Karten des Packs, aber nicht, wo sie auf dem Bildschirm liegen. Deshalb wird das
Raster einmal kalibriert (calibrate): bei vollem Pack fuenf Klicks im Arena-Fenster - Karte 1 oben links, Karte 1
unten rechts, Karte 2 oben links, letzte Karte der ersten Reihe oben links, erste Karte der zweiten Reihe oben links.
Gespeichert werden Anteile an der Groesse des Arena-Fensters (kartenoverlay.json, nicht im Git), so passt das Raster
auch, wenn das Fenster gleich proportioniert groesser oder kleiner wird; bei anderem Seitenverhaeltnis
(size_changed) besser neu kalibrieren.

Reihenfolge: Arena zeigt das Pack nach Seltenheit (mythic, rare, uncommon, common) und dann nach Sammlernummer, nicht
in der Reihenfolge des Protokolls ("order" im Live-Stand). So werden die Karten zeilenweise auf das Raster gelegt;
fehlen Seltenheit oder Nummer, bleibt die Reihenfolge des Protokolls. Jede Karte zeigt zur Kontrolle klein ihren
Namen. Stimmt er nicht mit der Karte darunter, sortiert Arena in diesem Fall anders.

Inhalt je Karte (pack_views): oben links der Rang im Pack (nach Punkten wie im Drafthelper), oben rechts die
Bewertung (♛ MW, ★ SW, MP, Fi, NP), unten eine Leiste mit Punkten, den Farben des besten Archetyps, der Passung
(dein Archetyp / nahe dran / Farben passen / fremde Farben), Chips (Removal mit Punkten, Kartenfluss, Synergie,
Kreatur) und der eigenen Siegquote mit der Karte aus der Draft-Statistik. Rahmen: lila Top-Pick, gruen passt,
grau fremd, dunkel NeverPlay.

Sichtbar (should_show) nur beim Picken (Pack liegt an, nicht im Spiel, Draft nicht fertig), wenn Arena gefunden,
nicht minimiert und im Vordergrund ist und eine Kalibrierung vorliegt. Das Fenster ist durchsichtig und laesst Klicks
zu Arena durch (Windows). Liegt die Maus auf einer Karte, verschwinden die Infos rechts davon, wo Arena die grosse
Kartenansicht oeffnet (hover_hidden, Mausposition alle 100 ms).
"""
import json
import pathlib

from components.i18n import dec, t

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent.parent
CAL_FILE = SCRIPT_DIR / "kartenoverlay.json"
CAL_KEYS = ("x", "y", "w", "h", "dx", "dy", "cols", "size")
RATING_LABEL = {"matchwinner": "♛ MW", "splashworthy": "★ SW", "mustplay": "MP", "filler": "Fi", "neverplay": "NP"}
ASPECT_TOLERANCE = 0.03
RARITY_ORDER = {"mythic": 0, "rare": 1, "uncommon": 2, "common": 3}


# ---------------------------------------------------------------- Kalibrierung und Raster

def calibrate(clicks, client):
    """Kalibrierung aus fuenf Klicks (Pixel im Arena-Fenster, siehe Modulbeschreibung); ValueError bei unpassenden
    Klicks."""
    if len(clicks) != 5:
        raise ValueError(t("Für die Kalibrierung braucht es genau fünf Klicks."))
    (x1, y1), (x2, y2), (x3, _y3), (x4, _y4), (_x5, y5) = clicks
    w, h, dx, dy = x2 - x1, y2 - y1, x3 - x1, y5 - y1
    if w <= 0 or h <= 0:
        raise ValueError(t("Die Ecke unten rechts muss rechts unter der Ecke oben links liegen."))
    if dx <= 0:
        raise ValueError(t("Karte 2 muss rechts neben Karte 1 liegen."))
    if dy <= 0:
        raise ValueError(t("Die zweite Reihe muss unter der ersten liegen."))
    cols = max(2, round((x4 - x1) / dx) + 1)
    cw, ch = client
    return {"x": x1 / cw, "y": y1 / ch, "w": w / cw, "h": h / ch, "dx": dx / cw, "dy": dy / ch, "cols": cols,
            "size": [cw, ch]}


def load_calibration(path=CAL_FILE):
    try:
        cal = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return cal if isinstance(cal, dict) and all(k in cal for k in CAL_KEYS) else None


def save_calibration(path, cal):
    pathlib.Path(path).write_text(json.dumps(cal, indent=1) + "\n", encoding="utf-8")


def card_rects(cal, n, origin, client):
    """Bildschirm-Rechtecke (links, oben, rechts, unten) der ersten n Karten, zeilenweise."""
    ox, oy = origin
    cw, ch = client
    out = []
    for i in range(n):
        row, col = divmod(i, cal["cols"])
        left = ox + round((cal["x"] + col * cal["dx"]) * cw)
        top = oy + round((cal["y"] + row * cal["dy"]) * ch)
        out.append((left, top, left + round(cal["w"] * cw), top + round(cal["h"] * ch)))
    return out


def hover_hidden(cal, n, origin, client, cursor):
    """Indizes der Karten, deren Infos verschwinden, weil die Maus auf einer Karte liegt: Arena oeffnet rechts daneben
    die grosse Ansicht (in Arena so eingestellt, Nutzer 14.11.2026), ausgeblendet werden alle Karten rechts davon (alle
    Reihen). Ohne Maus auf einer Karte: leer."""
    if not cursor:
        return set()
    mx, my = cursor
    rects = card_rects(cal, n, origin, client)
    hit = next((i for i, (l, t_, r, b) in enumerate(rects) if l <= mx < r and t_ <= my < b), None)
    if hit is None:
        return set()
    cols = cal["cols"]
    return {i for i in range(n) if i % cols > hit % cols}


def cursor_pos():
    """Mausposition auf dem Bildschirm (Windows), sonst None."""
    try:
        import ctypes
        from ctypes import wintypes
        pt = wintypes.POINT()
        if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
            return pt.x, pt.y
    except (ImportError, AttributeError, OSError):
        pass
    return None


def size_changed(cal, client):
    """Hat das Arena-Fenster ein anderes Seitenverhaeltnis als bei der Kalibrierung?"""
    cw, ch = cal["size"]
    w, h = client
    return not (h and ch) or abs((w / h) / (cw / ch) - 1) > ASPECT_TOLERANCE


# ---------------------------------------------------------------- Inhalt je Karte

def _fit(c, main):
    if not main:
        return t("Archetyp noch offen")
    if c.get("hint") == "in" or c.get("level") in ("best", "arch"):
        return "✓ " + t("dein Archetyp")
    if c.get("hint") == "near":
        return "≈ " + t("nahe dran")
    if c.get("level") == "color":
        return "○ " + t("Farben passen")
    return "– " + t("fremde Farben")


def _frame(c):
    if c.get("rating") == "neverplay":
        return "never"
    if c.get("hint"):
        return "top"
    if c.get("level"):
        return "fit"
    return "off"


def _chips(c):
    chips = []
    if c.get("removal"):
        chips.append(t("Removal {p} P.", p=dec(f"{c['removal']:g}")))
    if c.get("flow"):
        chips.append(t("Kartenfluss"))
    if c.get("synergy"):
        chips.append(t("Syn +{n}", n=dec(f"{c['synergy']:g}")))
    if c.get("creature"):
        chips.append(t("Kreatur"))
    return chips


def _stats(c):
    st = c.get("stats") or {}
    if not st.get("games"):
        return t("Deine Decks: –")
    return t("Deine Decks: {p} · {g} G.", p=f"{round(100 * st['wins'] / st['games'])} %", g=st["games"])


def card_view(c, rank, main):
    colors = list(c.get("best") or "") or list(c.get("colors") or [])
    return {"name": c["name"], "rank": rank, "rating": RATING_LABEL.get(c.get("rating"), ""),
            "points": dec(f"{c.get('points', 0):.1f}"), "colors": colors, "fit": _fit(c, main),
            "frame": _frame(c), "chips": _chips(c), "stats": _stats(c)}


def _color_key(c):
    """Farbgruppe wie in Arena: einfarbig (WUBRG), mehrfarbig (Farben in WUBRG-Folge), farblos, Laender."""
    if c.get("land"):
        return (3, ())
    idx = tuple(sorted("WUBRG".index(col) for col in c.get("colors") or [] if col in "WUBRG"))
    return (0 if len(idx) == 1 else 1 if idx else 2, idx)


def _arena_key(c):
    """Sortierschluessel wie in Arena: Seltenheit (mythic zuerst), Farbe (_color_key; Screenshot 14.11.2026: Spock UR
    Nr. 253 vor L'Rell BR Nr. 247), dann Sammlernummer; Unbekanntes ans Ende."""
    digits = "".join(ch for ch in str(c.get("number") or "").split("/")[0] if ch.isdigit())
    known = c.get("rarity") in RARITY_ORDER  # ohne Scryfall-Daten: Reihenfolge des Protokolls
    return (RARITY_ORDER.get(c.get("rarity"), len(RARITY_ORDER)), _color_key(c) if known else (4, ()),
            int(digits) if digits else float("inf"))


def pack_views(snap):
    """Inhalt je Karte in der Reihenfolge, in der Arena das Pack zeigt (Seltenheit, dann Sammlernummer; bei gleichem
    Schluessel wie im Protokoll); Rang nach Punkten (gleiche Karten nacheinander)."""
    ranks = {}
    for i, c in enumerate(snap.get("pack") or []):
        ranks.setdefault(c["name"], []).append((i + 1, c))
    main = (snap.get("detect") or {}).get("main")
    cards = []
    for name in snap.get("order") or []:
        queue = ranks.get(name)
        if not queue:
            continue
        cards.append(queue.pop(0) if len(queue) > 1 else queue[0])
    return [card_view(c, rank, main) for rank, c in sorted(cards, key=lambda rc: _arena_key(rc[1]))]


def status_text(cal, arena):
    """Hinweis fuer das Steuerfenster ("" = alles bereit)."""
    if not (arena or {}).get("found"):
        return t("Arena nicht gefunden")
    if not cal:
        return t("nicht kalibriert – bei vollem Pack „Kalibrieren“")
    if size_changed(cal, arena["size"]):
        return t("Arena-Fenster anders proportioniert: neu kalibrieren")
    return ""


def should_show(enabled, snap, cal, arena):
    """Overlay zeigen? Nur beim Picken, mit Kalibrierung und sichtbarem Arena-Fenster im Vordergrund."""
    if not (enabled and snap and cal and arena):
        return False
    if snap.get("status") != "pack" or snap.get("complete") or (snap.get("game") or {}).get("active"):
        return False
    if not snap.get("order"):
        return False
    return bool(arena.get("found") and not arena.get("minimized") and arena.get("foreground"))


def covers_pack(enabled, snap, cal, arena):
    """Steht das Pack auf den Karten (Seitenfenster schlank, overlay.rows_for slim)? Schalter an, kalibriert, Arena da und
    passend proportioniert, Pack mit Reihenfolge; anders als should_show ohne Vordergrund, damit das Seitenfenster beim
    Alt-Tab nicht springt."""
    if not (enabled and snap and cal and (arena or {}).get("found")) or arena.get("minimized"):
        return False
    if size_changed(cal, arena["size"]):
        return False
    if snap.get("status") != "pack" or snap.get("complete") or (snap.get("game") or {}).get("active"):
        return False
    return bool(snap.get("order") and snap.get("pack"))


# ---------------------------------------------------------------- Arena-Fenster (Windows)

def arena_window(own_pid=None):
    """Lage des Arena-Fensters: {"found", "minimized", "foreground", "origin", "size"} (Innenbereich, Pixel). Ohne
    Windows oder ohne Arena: {"found": False}."""
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
    except (ImportError, AttributeError, OSError):
        return {"found": False}
    hwnd = user32.FindWindowW(None, "MTGA")
    if not hwnd:
        return {"found": False}
    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    pt = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    fg = user32.GetForegroundWindow()
    foreground = fg == hwnd
    if not foreground and fg and own_pid is not None:  # eigene Fenster (Steuerfenster, Kalibrierung) zaehlen mit
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(fg, ctypes.byref(pid))
        foreground = pid.value == own_pid
    return {"found": True, "minimized": bool(user32.IsIconic(hwnd)), "foreground": foreground,
            "origin": (pt.x, pt.y), "size": (rect.right - rect.left, rect.bottom - rect.top)}


def _click_through(win):
    """Fenster laesst Mausklicks durch und nimmt keinen Fokus (Windows; sonst ohne Wirkung)."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetParent(win.winfo_id()) or win.winfo_id()
        GWL_EXSTYLE, WS_EX_LAYERED, WS_EX_TRANSPARENT, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW = \
            -20, 0x80000, 0x20, 0x8000000, 0x80
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                              style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
    except (ImportError, AttributeError, OSError):
        pass


KEY = "#010203"  # durchsichtige Farbe des Fensters
FRAME = {"top": "#8e2bd6", "fit": "#1d9e75", "off": "#6b7280", "never": "#3a3f4a"}
MANA_FILL = {"W": "#f3ecd2", "U": "#4a90d9", "B": "#6b5f7a", "R": "#e0533d", "G": "#3f9b5a"}
MANA_INK = {"W": "#161b24"}
RANK_FILL = {1: "#8e2bd6", 2: "#1d9e75", 3: "#2c6fb5"}


class PackOverlay:
    """Durchsichtiges Fenster ueber Arena, das die Karten-Infos zeichnet (update je Live-Stand)."""

    def __init__(self, master):
        import tkinter as tk
        self.tk = tk
        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        try:
            self.win.attributes("-transparentcolor", KEY)
        except tk.TclError:
            pass
        self.win.configure(bg=KEY)
        self.canvas = tk.Canvas(self.win, bg=KEY, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.win.withdraw()
        self.win.update_idletasks()
        _click_through(self.win)
        self.last = None

    def hide(self):
        if self.win.state() != "withdrawn":
            self.win.withdraw()
        self.last = None

    def show(self, views, cal, arena, hidden=()):
        """Infos auf die Karten legen; hidden: Indizes ohne Infos (Maus auf einer Karte, hover_hidden)."""
        (ox, oy), (cw, ch) = arena["origin"], arena["size"]
        key = (json.dumps(views, ensure_ascii=False), ox, oy, cw, ch, tuple(sorted(hidden)))
        if self.win.state() == "withdrawn":
            self.win.deiconify()
            self.win.attributes("-topmost", True)
        if key == self.last:
            return
        self.last = key
        self.win.geometry(f"{cw}x{ch}+{ox}+{oy}")
        self.canvas.delete("all")
        for i, (v, rect) in enumerate(zip(views, card_rects(cal, len(views), (0, 0), (cw, ch)))):
            if i not in hidden:
                self._card(v, rect)

    def _card(self, v, rect):
        c = self.canvas
        x1, y1, x2, y2 = rect
        w, h = x2 - x1, y2 - y1
        s = max(0.6, min(1.6, w / 190))  # Schriftgroesse waechst mit der Karte
        f = lambda size, bold=False: ("Segoe UI", max(7, round(size * s)), "bold" if bold else "normal")  # noqa: E731
        c.create_rectangle(x1 + 1, y1 + 1, x2 - 1, y2 - 1, outline=FRAME[v["frame"]], width=max(2, round(3 * s)))
        if v["frame"] == "never":
            c.create_rectangle(x1 + 3, y1 + 3, x2 - 3, y2 - 3, fill="#000000", stipple="gray50", outline="")
        # oben links: Rang, oben rechts: Bewertung (unter der Namenszeile, auf dem Bild)
        r = round(13 * s)
        cy = y1 + round(h * 0.12) + r
        c.create_oval(x1 + 6, cy - r, x1 + 6 + 2 * r, cy + r, fill=RANK_FILL.get(v["rank"], "#3a3f4a"),
                      outline="#ffffff", width=1)
        c.create_text(x1 + 6 + r, cy, text=str(v["rank"]), fill="#ffffff", font=f(12, True))
        if v["rating"]:
            tid = c.create_text(x2 - 10, cy, text=v["rating"], fill="#161b24", font=f(10, True), anchor="e")
            bx1, by1, bx2, by2 = c.bbox(tid)
            pill = c.create_rectangle(bx1 - 6, by1 - 2, bx2 + 6, by2 + 2, fill="#ffd166", outline="")
            c.tag_lower(pill, tid)
        # unten: Leiste mit Punkten, Farben, Passung, Chips, eigener Quote und Kontrollname
        band = y2 - round(h * 0.36)
        c.create_rectangle(x1 + 3, band, x2 - 3, y2 - 3, fill="#161b24", outline="")
        y = band + round(5 * s)
        c.create_text(x1 + 9, y, text=v["points"], fill="#ffffff", font=f(16, True), anchor="nw")
        px = x1 + 9 + round(44 * s)
        pr = round(7 * s)
        for col in v["colors"][:3]:
            c.create_oval(px, y + 4, px + 2 * pr, y + 4 + 2 * pr, fill=MANA_FILL.get(col, "#8d97a8"), outline="")
            c.create_text(px + pr, y + 4 + pr, text=col, fill=MANA_INK.get(col, "#ffffff"), font=f(8, True))
            px += 2 * pr + 3
        c.create_text(x2 - 9, y + 4, text=v["fit"], fill="#e8ecf3", font=f(9), anchor="ne")
        y += round(26 * s)
        if v["chips"]:  # darf umbrechen: die naechste Zeile beginnt unter der tatsaechlichen Hoehe
            cid = c.create_text(x1 + 9, y, text=" · ".join(ch.replace(" ", "\u00a0") for ch in v["chips"]),
                                fill="#c8d3e0", font=f(9), anchor="nw", width=w - 18)
            y = c.bbox(cid)[3] + round(2 * s)
        c.create_text(x1 + 9, y, text=v["stats"], fill="#8d97a8", font=f(9), anchor="nw")
        c.create_text(x1 + 9, y2 - 6, text=v["name"], fill="#6b7280", font=f(7), anchor="sw", width=w - 18)


class Calibrator:
    """Kalibrierung: halbdurchsichtiges Fenster ueber Arena faengt fuenf Klicks; Esc bricht ab. done(cal) danach."""
    STEPS = ("Karte 1: Ecke oben links anklicken", "Karte 1: Ecke unten rechts anklicken",
             "Karte 2 (rechts daneben): Ecke oben links anklicken",
             "Letzte Karte der ersten Reihe: Ecke oben links anklicken",
             "Erste Karte der zweiten Reihe: Ecke oben links anklicken")

    def __init__(self, master, arena, done):
        import tkinter as tk
        (ox, oy), (cw, ch) = arena["origin"], arena["size"]
        self.arena, self.done, self.clicks = arena, done, []
        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        try:
            self.win.attributes("-alpha", 0.35)
        except tk.TclError:
            pass
        self.win.geometry(f"{cw}x{ch}+{ox}+{oy}")
        self.canvas = tk.Canvas(self.win, bg="#000000", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.click)
        self.win.bind("<Escape>", lambda e: self.close())
        self.win.focus_force()
        self.draw()

    def draw(self, error=""):
        c = self.canvas
        c.delete("all")
        w = int(self.arena["size"][0])
        step = len(self.clicks)
        c.create_rectangle(0, 0, w, 70, fill="#161b24", outline="")
        c.create_text(w // 2, 22, fill="#ffd166", font=("Segoe UI", 16, "bold"),
                      text=t("Karten-Overlay kalibrieren ({n}/5): ", n=step + 1) + t(self.STEPS[step]))
        c.create_text(w // 2, 50, fill="#ff8a8a" if error else "#e8ecf3", font=("Segoe UI", 11),
                      text=error or t("Bei vollem Pack in Arena. Esc bricht ab."))
        for x, y in self.clicks:
            c.create_oval(x - 6, y - 6, x + 6, y + 6, outline="#ffd166", width=3)

    def click(self, e):
        self.clicks.append((e.x, e.y))
        if len(self.clicks) < 5:
            self.draw()
            return
        try:
            cal = calibrate(self.clicks, self.arena["size"])
        except ValueError as err:
            self.clicks = []
            self.draw(str(err) + " " + t("Bitte noch einmal von vorn."))
            return
        self.close()
        self.done(cal)

    def close(self):
        try:
            self.win.destroy()
        except Exception:  # schon geschlossen
            pass
