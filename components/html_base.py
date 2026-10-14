"""HTML-Grundlagen: CSS, Mana-Symbole, Tabellen, Balken und SVG-Diagramme."""
import html as html_lib
import re


HTML_CSS = """
:root{
 --bg:#f3f4f8; --panel:#ffffff; --text:#1b2230; --muted:#677085; --line:#e2e5ee; --accent:#4b5bdc;
 --good:#146c3d; --goodbg:#d9f3e4; --warn:#7a5200; --warnbg:#ffedc2; --bad:#a82a2a; --badbg:#fde0e0;
 --play:#4b5bdc; --draw:#e07a1f; --track:#e6e9f2; --chip:#eef0f7;
}
@media (prefers-color-scheme: dark){
 :root{ --bg:#0e1117; --panel:#161b25; --text:#e7eaf1; --muted:#98a2b5; --line:#262d3b; --accent:#8e9bff;
  --good:#6fe0a0; --goodbg:#143a29; --warn:#f5c964; --warnbg:#3b3110; --bad:#ff9090; --badbg:#401a1a;
  --play:#8e9bff; --draw:#f5a45c; --track:#2a3347; --chip:#222a3a; }
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
header.top{padding:28px 20px 18px;max-width:1380px;margin:0 auto}
header.top h1{margin:0 0 4px;font-size:28px;letter-spacing:-.02em}
header.top .sub{color:var(--muted)}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.chip{background:var(--chip);border:1px solid var(--line);border-radius:999px;padding:2px 10px;font-size:12.5px;color:var(--muted)}
.layout{display:grid;grid-template-columns:220px minmax(0,1fr);gap:24px;max-width:1380px;margin:0 auto;padding:0 20px}
nav{position:sticky;top:12px;align-self:start;max-height:calc(100vh - 24px);overflow-y:auto;padding:14px 0}
nav .in{display:flex;flex-direction:column;gap:2px}
nav a{display:block;color:var(--muted);text-decoration:none;padding:5px 10px;border-radius:8px;font-size:13.5px}
nav a:hover{background:var(--chip);color:var(--text)}
main{min-width:0;padding:8px 0 60px}
section{margin-top:22px;scroll-margin-top:56px}
section>h2{font-size:19px;margin:0 0 4px;letter-spacing:-.01em}
section>.hint{color:var(--muted);font-size:13.5px;margin:0 0 10px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;box-shadow:0 1px 2px rgba(0,0,0,.03)}
.grid{display:grid;gap:14px}
.grid>*{min-width:0}
.g2{grid-template-columns:repeat(auto-fit,minmax(420px,1fr))}
.g4{grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}
.g3{grid-template-columns:repeat(3,1fr)}
@media(max-width:760px){.g3{grid-template-columns:1fr 1fr}}
.kpi{padding:14px 16px}
.kpi .l{color:var(--muted);font-size:12.5px;text-transform:uppercase;letter-spacing:.05em}
.kpi .v{font-size:26px;font-weight:650;letter-spacing:-.02em;margin-top:2px}
.kpi .s{color:var(--muted);font-size:13px}
table{border-collapse:collapse;width:100%}
th,td{padding:7px 10px;text-align:right;border-bottom:1px solid var(--line);vertical-align:middle}
th{font-weight:600;color:var(--muted);font-size:12.5px;text-transform:uppercase;letter-spacing:.04em}
th:first-child,td:first-child{text-align:left}
tr:last-child td{border-bottom:0}
td.l,th.l{text-align:left}
.tw{overflow-x:auto}
td.good,td.warn,td.bad{font-weight:650;border-radius:0}
td.good{background:var(--goodbg);color:var(--good)}
td.warn{background:var(--warnbg);color:var(--warn)}
td.bad{background:var(--badbg);color:var(--bad)}
.pill{display:inline-block;padding:1px 9px;border-radius:999px;font-weight:650;font-size:13px}
.pill.good{background:var(--goodbg);color:var(--good)}
.pill.warn{background:var(--warnbg);color:var(--warn)}
.pill.bad{background:var(--badbg);color:var(--bad)}
.m{display:inline-flex;align-items:center;justify-content:center;min-width:22px;height:22px;padding:0 5px;margin:0 1px;
   border-radius:999px;font-size:12px;font-weight:700;border:1px solid rgba(0,0,0,.25);vertical-align:middle;line-height:1}
.m-h{text-shadow:0 0 3px #fff,0 0 3px #fff;color:#111;min-width:38px;padding:0 8px}
.tag.add{background:var(--goodbg);color:var(--good);border-color:transparent}
.tag.rem{background:var(--badbg);color:var(--bad);border-color:transparent}
.tag.t0{background:#dbe9ff;color:#1b4a9c;border-color:transparent;font-weight:650}
.tag.t1{background:#fde0e0;color:#a82a2a;border-color:transparent;font-weight:650}
.tag.t2{background:#fff0b3;color:#7a5a00;border-color:transparent;font-weight:650}
.tag.off{opacity:.55}
.diff{font-weight:700}
.cc-legend{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:13px;color:var(--muted);margin:8px 0 4px}
.cc-legend i{display:inline-block;width:11px;height:11px;border:1px solid rgba(0,0,0,.25);border-radius:3px;margin-right:5px;vertical-align:-1px}
.cc-note{font-size:12.5px;color:var(--muted);margin-top:6px;line-height:1.45}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .tag.t0{background:#17305c;color:#9fc4ff}
:root:not([data-theme="light"]) .tag.t1{background:#401a1a;color:#ff9090}
:root:not([data-theme="light"]) .tag.t2{background:#3b3110;color:#f5d56a}}
:root[data-theme="dark"] .tag.t0{background:#17305c;color:#9fc4ff}
:root[data-theme="dark"] .tag.t1{background:#401a1a;color:#ff9090}
:root[data-theme="dark"] .tag.t2{background:#3b3110;color:#f5d56a}
.grpbar{margin:18px 0 0;padding:0;display:none;align-items:center;gap:8px;flex-wrap:wrap}
.js .grpbar{display:flex}
.grpbar button{font:inherit;font-size:13.5px;padding:5px 14px;border-radius:999px;border:1px solid var(--line);
  background:var(--chip);color:var(--text);cursor:pointer}
.grpbar button.on{background:var(--text);color:var(--bg);border-color:var(--text)}
.js .grp:not(.on),.js .grpnav:not(.on){display:none}
.grp>h2.gh{margin:22px 0 0;padding:0;font-size:20px}
.tag{display:inline-block;background:var(--chip);border:1px solid var(--line);border-radius:6px;padding:0 7px;margin:1px 3px 1px 0;font-size:12px;color:var(--muted)}
.bar{background:var(--track);border-radius:999px;height:9px;min-width:70px;overflow:hidden}
.bar i{display:block;height:100%;background:var(--accent);border-radius:999px}
.bar.draw i{background:var(--draw)} .bar.play i{background:var(--play)}
.bc{display:flex;align-items:center;gap:8px;justify-content:flex-end}
.bc .bar{flex:1;max-width:110px;min-width:50px}
.bc b{min-width:40px;text-align:right}
.mode{font-weight:650;white-space:nowrap}
th{white-space:nowrap}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}
.dot.play{background:var(--play)} .dot.draw{background:var(--draw)}
svg.chart{width:100%;height:auto;max-height:300px}
svg .grid{stroke:var(--line);stroke-width:1}
svg .axis{fill:var(--muted);font-size:11px}
svg .lbl{fill:var(--text);font-size:10.5px;font-weight:600}
svg .ln{fill:none;stroke-width:2.6;stroke-linejoin:round;stroke-linecap:round}
svg .ln.play{stroke:var(--play)} svg .ln.draw{stroke:var(--draw)}
svg .pt.play,svg .rb.play{fill:var(--play)} svg .pt.draw,svg .rb.draw{fill:var(--draw)}
svg .pt,svg .rb{stroke:none}
.legend{display:flex;gap:16px;font-size:13px;color:var(--muted);margin:2px 0 6px}
.lethal .head{display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap}
.lethal .head .big{font-size:20px;font-weight:700}
.hand{display:flex;flex-wrap:wrap;gap:5px;margin:4px 0 10px}
.card{border:1px solid var(--line);background:var(--chip);border-radius:7px;padding:2px 8px;font-size:12.5px}
.card.land{opacity:.75}
.tl td,.tl th{font-size:13.5px}
.tl td.dmg{white-space:nowrap}
.muted{color:var(--muted)}
.note{color:var(--muted);font-size:12.5px;margin-top:8px}
.warnbox{background:var(--warnbg);color:var(--warn);border-radius:10px;padding:8px 12px;font-size:13.5px;margin-bottom:10px}
ul.ass,ol.ass{margin:6px 0 0;padding-left:22px;color:var(--muted);font-size:13.5px}
ol.ass li,ul.ass li{margin-bottom:4px}
ol.ass b,ul.ass b{color:var(--text)}
tr.win td{background:var(--goodbg);color:var(--good);font-weight:650}
footer{max-width:1380px;margin:0 auto;padding:0 20px 40px;color:var(--muted);font-size:12.5px}
@media (max-width:900px){.layout{grid-template-columns:1fr;padding:0}nav{top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);max-height:none;padding:0}nav .in{flex-direction:row;overflow-x:auto;white-space:nowrap;padding:8px 20px}main{padding:8px 20px 60px}}
@media print{nav{display:none}.layout{display:block}body{background:#fff}.panel{box-shadow:none}}
"""


MANA_BG = {"W": "#f6efc4", "U": "#2a74c4", "B": "#3a3340", "R": "#d0453a", "G": "#2e9560", "C": "#c3c9d1"}
MANA_FG = {"W": "#2a2a2a", "U": "#ffffff", "B": "#ffffff", "R": "#ffffff", "G": "#ffffff", "C": "#222222"}
MANA_NEUTRAL = "#d9dde3"
LABEL_CLASS = {"On the Play": "play", "On the Draw": "draw"}


def esc(x):
    return html_lib.escape(str(x), quote=True)


def html_mana(sym):
    if "/" in sym:
        cols = [MANA_BG.get(p, MANA_NEUTRAL) for p in sym.split("/")[:2]]
        if len(cols) == 1:
            cols = cols * 2
        return (f'<span class="m m-h" style="background:linear-gradient(135deg,{cols[0]} 50%,{cols[1]} 50%)">'
                f'{esc(sym)}</span>')
    return (f'<span class="m" style="background:{MANA_BG.get(sym, MANA_NEUTRAL)};'
            f'color:{MANA_FG.get(sym, "#222222")}">{esc(sym)}</span>')


def html_cost(text):
    out, last = [], 0
    for mm in re.finditer(r"\{([^}]+)\}", text):
        out.append(esc(text[last:mm.start()]))
        out.append(html_mana(mm.group(1)))
        last = mm.end()
    out.append(esc(text[last:]))
    return "".join(out)


def h_pct(x, digits=0):
    return f"{x * 100:.{digits}f}%"


def h_bar(frac, cls=""):
    frac = max(0.0, min(1.0, frac))
    return f'<div class="bar {cls}"><i style="width:{frac * 100:.1f}%"></i></div>'


def h_bar_cell(frac, text=None, cls=""):
    text = h_pct(frac) if text is None else text
    return f'<td><div class="bc"><b>{esc(text)}</b>{h_bar(frac, cls)}</div></td>'


def h_level_td(level, text):
    cls = {"green": "good", "yellow": "warn", "red": "bad"}.get(level, "")
    return f'<td class="{cls}">{esc(text)}</td>'


def h_level_pill(level, text):
    cls = {"green": "good", "yellow": "warn", "red": "bad"}.get(level, "")
    return f'<span class="pill {cls}">{esc(text)}</span>'


def h_mode(label):
    return f'<td class="l mode"><span class="dot {LABEL_CLASS.get(label, "")}"></span>{esc(label)}</td>'


def h_table(headers, rows, extra="", left=(0,)):
    head = "".join(f'<th class="{"l" if i in left else ""}">{h}</th>' for i, h in enumerate(headers))
    body = "".join("<tr>" + "".join(r) + "</tr>" for r in rows)
    return f'<div class="tw"><table {extra}><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def svg_lines(xs, series, ymax=1.0, w=640, h=250):
    ml, mr, mt, mb = 46, 16, 14, 30
    pw, ph = w - ml - mr, h - mt - mb

    def X(i):
        return ml + (pw * i / (len(xs) - 1) if len(xs) > 1 else pw / 2)

    def Y(v):
        return mt + ph * (1 - min(v, ymax) / ymax)

    out = [f'<svg viewBox="0 0 {w} {h}" class="chart" role="img">']
    for g in (0, .25, .5, .75, 1):
        y = Y(g * ymax)
        out.append(f'<line x1="{ml}" x2="{w - mr}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
        out.append(f'<text x="{ml - 7}" y="{y + 4:.1f}" class="axis" text-anchor="end">{g:.0%}</text>')
    for i, x in enumerate(xs):
        out.append(f'<text x="{X(i):.1f}" y="{h - 9}" class="axis" text-anchor="middle">{esc(x)}</text>')
    for name, vals in series.items():
        cls = LABEL_CLASS.get(name, "play")
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
        out.append(f'<polyline points="{pts}" class="ln {cls}"/>')
        for i, v in enumerate(vals):
            out.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="3.3" class="pt {cls}">'
                       f'<title>{esc(name)}, Runde {esc(xs[i])}: {v:.0%}</title></circle>')
    out.append("</svg>")
    return "".join(out)


def svg_bars(labels, series, vmax, fmt, w=640, h=250):
    ml, mr, mt, mb = 40, 12, 22, 30
    pw, ph = w - ml - mr, h - mt - mb
    n, k = len(labels), len(series)
    gw = pw / max(n, 1)
    bw = min(34, gw * 0.8 / max(k, 1))
    out = [f'<svg viewBox="0 0 {w} {h}" class="chart" role="img">']
    for g in (0, .5, 1):
        y = mt + ph * (1 - g)
        out.append(f'<line x1="{ml}" x2="{w - mr}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
        out.append(f'<text x="{ml - 6}" y="{y + 4:.1f}" class="axis" text-anchor="end">{fmt(g * vmax)}</text>')
    for i, lab in enumerate(labels):
        cx = ml + gw * (i + 0.5)
        out.append(f'<text x="{cx:.1f}" y="{h - 9}" class="axis" text-anchor="middle">{esc(lab)}</text>')
        for j, (name, vals) in enumerate(series.items()):
            v = vals[i]
            bh = ph * min(v, vmax) / vmax if vmax else 0
            x = cx - bw * k / 2 + bw * j
            cls = LABEL_CLASS.get(name, "play")
            out.append(f'<rect x="{x:.1f}" y="{mt + ph - bh:.1f}" width="{bw - 3:.1f}" height="{bh:.1f}" rx="3" '
                       f'class="rb {cls}"><title>{esc(name)}, {esc(lab)}: {fmt(v)}</title></rect>')
            if v > 0:
                out.append(f'<text x="{x + (bw - 3) / 2:.1f}" y="{mt + ph - bh - 4:.1f}" class="lbl" '
                           f'text-anchor="middle">{fmt(v)}</text>')
    out.append("</svg>")
    return "".join(out)


def h_legend(labels):
    return '<div class="legend">' + "".join(
        f'<span><span class="dot {LABEL_CLASS.get(l, "")}"></span>{esc(l)}</span>' for l in labels) + "</div>"


def h_section(sid, title, hint, body):
    hint_html = f'<p class="hint">{hint}</p>' if hint else ""
    return f'<section id="{sid}"><h2>{esc(title)}</h2>{hint_html}{body}</section>'
