"""Berichtsteile zu Kartentypen und Farben: Mana-Kurve nach Farben, Typ-Tabelle und Typ-Vergleich der Decks.
Die Zaehllogik ist dieselbe wie in der Seitenleiste des Drafthelpers (components/cardkinds.py)."""
import math

from components.cardkinds import FLOW_ORDER, color_curve
from components.html_base import esc, h_table

COLOR_HEX = {"W": "#f1e7b8", "U": "#3b82d6", "B": "#4a4a4a", "R": "#d6453b", "G": "#3f9b4f", "M": "#d9a400",
             "C": "#b7bcc6"}
COLOR_NAME = {"W": "Weiß", "U": "Blau", "B": "Schwarz", "R": "Rot", "G": "Grün", "M": "Mehrfarbig", "C": "Farblos"}
BUCKETS = 8  # 0 bis 6 und 7+

FLOW_LABELS = {"draw": "Ziehen (Draw)", "search": "Suchen (Search)", "surveil": "Surveil", "scry": "Scry",
               "explore": "Explore", "mill_self": "Mill: sich selbst",
               "mill_opp": "Mill: Gegner möglich (auch „target player“)"}


def curve_items(ctx):
    info = ctx.get("info") or {}
    return [{"colors": (info.get(name) or {}).get("colors", []), "mv": card.mv, "land": card.is_land, "qty": qty}
            for name, qty, card, _shown in ctx["rows"]]


def _svg(curve, mode, w=520, h=250):
    ml, mr, mt, mb = 34, 10, 22, 30
    pw, ph = w - ml - mr, h - mt - mb
    gw = pw / BUCKETS
    keys, vmax = curve["keys"], max(curve["max"], 1)
    out = [f'<svg viewBox="0 0 {w} {h}" class="chart" role="img">']
    for g in (0, .5, 1):
        y = mt + ph * (1 - g)
        out.append(f'<line x1="{ml}" x2="{w - mr}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
        out.append(f'<text x="{ml - 6}" y="{y + 4:.1f}" class="axis" text-anchor="end">{math.ceil(g * vmax)}</text>')
    for i in range(BUCKETS):
        cx = ml + gw * (i + 0.5)
        label = str(i) if i < BUCKETS - 1 else f"{BUCKETS - 1}+"
        out.append(f'<text x="{cx:.1f}" y="{h - 9}" class="axis" text-anchor="middle">{label}</text>')
        bucket = curve["buckets"][i]
        if mode == "stacked":
            bw, y = min(40, gw * 0.7), mt + ph
            for k in keys:
                v = bucket[k]
                if not v:
                    continue
                bh = ph * v / vmax
                y -= bh
                out.append(f'<rect x="{cx - bw / 2:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" '
                           f'fill="{COLOR_HEX[k]}" stroke="rgba(0,0,0,.25)" stroke-width="1">'
                           f'<title>{COLOR_NAME[k]}, Manawert {label}: {v}</title></rect>')
            total = sum(bucket.values())
            if total:
                out.append(f'<text x="{cx:.1f}" y="{y - 4:.1f}" class="lbl" text-anchor="middle">{total}</text>')
        else:
            bw = min(13, gw * 0.85 / len(keys))
            for j, k in enumerate(keys):
                v = bucket[k]
                if not v:
                    continue
                bh = ph * v / vmax
                x = cx - bw * len(keys) / 2 + bw * j
                out.append(f'<rect x="{x:.1f}" y="{mt + ph - bh:.1f}" width="{bw - 1:.1f}" height="{bh:.1f}" '
                           f'fill="{COLOR_HEX[k]}" stroke="rgba(0,0,0,.25)" stroke-width="1">'
                           f'<title>{COLOR_NAME[k]}, Manawert {label}: {v}</title></rect>')
                out.append(f'<text x="{x + (bw - 1) / 2:.1f}" y="{mt + ph - bh - 3:.1f}" class="lbl" '
                           f'text-anchor="middle">{v}</text>')
    out.append("</svg>")
    return "".join(out)


def _legend(keys):
    items = "".join(
        f'<span><i style="background:{COLOR_HEX[k]}"></i>{COLOR_NAME[k]}{" (mehrere Farben)" if k == "M" else ""}</span>'
        for k in keys)
    return f'<div class="cc-legend">{items}</div>'


def render_color_curves(ctx):
    """Panel 'Mana-Kurve nach Farben' mit beiden Ansichten (mehrfarbige Karten gesondert / je Farbe)."""
    items = curve_items(ctx)
    stacked, percolor = color_curve(items, "stacked", BUCKETS), color_curve(items, "percolor", BUCKETS)
    pairs = sorted(stacked["pairs"].items(), key=lambda kv: (-kv[1], kv[0]))
    pair_text = " · ".join("/".join(COLOR_NAME[c] for c in k.split("/")) + f" {n}" for k, n in pairs)
    info = (f'{stacked["total"]} Nichtland-Karten, davon {stacked["multi"]} mehrfarbig und {stacked["colorless"]} '
            "farblos." + (f" Mehrfarbig: {esc(pair_text)}." if pairs else ""))
    left = (f'<div><b>Mehrfarbige gesondert</b>{_svg(stacked, "stacked")}{_legend(stacked["keys"])}'
            '<div class="cc-note">Jede Karte steht genau einmal im Diagramm (Balkenhöhe = Kartenzahl). Karten mit '
            "mehreren Farben bilden das goldene Segment „Mehrfarbig“.</div></div>")
    right = (f'<div><b>Je Farbe</b>{_svg(percolor, "percolor")}{_legend(percolor["keys"])}'
             '<div class="cc-note">Eine mehrfarbige Karte zählt bei jeder ihrer Farben, z. B. eine Karte Grün/Weiß bei '
             "Grün und bei Weiß. Die Balken ergeben deshalb zusammen mehr als die Kartenzahl.</div></div>")
    return ('<div class="panel"><b>Mana-Kurve nach Farben</b>'
            '<div class="note" style="margin:0 0 6px">Nichtland-Karten je Manawert, nach Farben aufgeteilt</div>'
            f'<div class="grid g2">{left}{right}</div><div class="cc-note">{info}</div></div>')


def type_counts(ctx):
    """Zaehlt Kopien je Typ, Empower Jace und Kartenfluss eines Decks (gleiche Regeln wie typeCounts der Seite)."""
    info = ctx.get("info") or {}
    t = {"cards": 0, "creature": 0, "instant": 0, "sorcery": 0, "artifact": 0, "enchantment": 0, "planeswalker": 0,
         "land": 0, "nonbasic_land": 0, "empower": 0, "points": 0, "flow": 0}
    t.update({f"flow_{k}": 0 for k in FLOW_ORDER})
    for name, qty, card, _shown in ctx["rows"]:
        i = info.get(name) or {}
        t["cards"] += qty
        for k in i.get("kinds", []):
            if k in t:
                t[k] += qty
        if i.get("empower"):
            t["empower"] += qty
            t["points"] += qty * i.get("points", 0)
        flow = i.get("flow", [])
        if flow:
            t["flow"] += qty
            for k in flow:
                if f"flow_{k}" in t:
                    t[f"flow_{k}"] += qty
    return t


TYPE_ROWS = [("cards", "Karten gesamt", ""), ("creature", "Kreaturen", ""), ("instant", "Instants", ""),
             ("sorcery", "Sorceries", ""), ("artifact", "Artefakte (ohne Kreaturen)", ""),
             ("enchantment", "Verzauberungen", ""), ("planeswalker", "Planeswalker", ""),
             ("land", "Länder gesamt", ""), ("nonbasic_land", "davon Nicht-Standard-Länder", "sub"),
             ("empower", "Empower Jace (Karten)", ""), ("points", "Σ Loyalty beim Wirken/Betreten", "sub")]

TYPE_NOTE = ("Gezählt werden Kopien. Artefakte und Verzauberungen ohne Kreaturen und Länder; eine Karte kann in mehreren "
             "Zeilen stehen. Σ Loyalty: Zahlenwerte von Empower Jace beim Zauber oder Betreten (ohne X, ohne Auslöser).")
FLOW_NOTE = (" Kartenfluss: Karten, die ziehen, suchen oder Karten aus der Bibliothek betrachten bzw. in den Friedhof "
             "legen; es erscheinen nur Arten, die im Deck vorkommen. Empower Jace zählt nicht dazu.")


def _note(rows):
    return TYPE_NOTE + (FLOW_NOTE if any(label.startswith("Kartenfluss") for label, _c, _v in rows) else "")


def _rows(decks):
    """Zeilen (Label, Klasse, [Werte je Deck]); Kartenfluss-Arten nur, wenn eines der Decks sie hat."""
    counts = [type_counts(d) for d in decks]
    spec = list(TYPE_ROWS)
    present = [k for k in FLOW_ORDER if any(c[f"flow_{k}"] for c in counts)]
    if present:
        spec.append(("flow", "Kartenfluss (Karten)", ""))
        spec += [(f"flow_{k}", FLOW_LABELS[k], "sub") for k in present]
    return [(label, cls, [c[key] for c in counts]) for key, label, cls in spec]


def _label_cell(label, cls):
    style = ' style="padding-left:22px;color:var(--muted)"' if cls == "sub" else ""
    return f'<td class="l"{style}>{esc(label)}</td>'


def render_type_table(ctx):
    spec = _rows([ctx])
    rows = [[_label_cell(label, cls), f"<td>{vals[0]}</td>"] for label, cls, vals in spec]
    return (f'<div class="panel"><b>Kartentypen</b>{h_table(["Art", "Karten"], rows)}'
            f'<div class="note">{esc(_note(spec))}</div></div>')


def render_types_compare(decks):
    """Tabelle mit einer Spalte je Deck; Zeilen mit Unterschieden sind fett."""
    heads = ["Art"] + [esc(d["name"]) for d in decks]
    rows, spec = [], _rows(decks)
    for label, cls, vals in spec:
        cell_cls = ' class="diff"' if len(set(vals)) > 1 else ""
        rows.append([_label_cell(label, cls)] + [f"<td{cell_cls}>{v}</td>" for v in vals])
    return (f'<div class="panel"><b>Kartentypen im Vergleich</b>{h_table(heads, rows)}'
            f'<div class="note">{esc(_note(spec))} Fett: Unterschied zwischen den Decks.</div></div>')
