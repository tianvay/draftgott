"""Turnierbericht (HTML) fuer components/tournament.py: Ueberblick, Matrix, Tabelle, Paarungen mit Diagrammen und
Kartenstatistik, Decks. Eigenstaendige Seite mit hellem und dunklem Farbschema; Diagramme als SVG, Werte zusaetzlich
in Tabellen, Tooltips nur als Ergaenzung."""
from components.html_base import esc
from components.i18n import dec, html_lang, is_en, t
from components import tournament as tm

MIN_CARD_GAMES = 30  # darunter ist die Kartenquote nur ein Hinweis (grau)
TOP_CARDS = 3

CSS = """
:root{
 color-scheme:light;
 --page:#f6f6f3; --surface:#fcfcfb; --raised:#ffffff; --ink:#0b0b0b; --ink2:#52514e; --muted:#7a7873;
 --grid:#e1e0d9; --axis:#c3c2b7; --ring:rgba(11,11,11,.10); --soft:#efeee9;
 --a:#2a78d6; --b:#eb6834; --drawc:#c3c2b7; --mid:#f0efec;
 --good:#006300; --goodbg:#e3f3e3; --warn:#7a5200; --warnbg:#fff1cc; --accent:#2a78d6;
}
@media (prefers-color-scheme: dark){
 :root:not([data-theme="light"]){
  color-scheme:dark;
  --page:#0d0d0d; --surface:#1a1a19; --raised:#222220; --ink:#f0efec; --ink2:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --axis:#383835; --ring:rgba(255,255,255,.10); --soft:#262624;
  --a:#3987e5; --b:#d95926; --drawc:#55544f; --mid:#383835;
  --good:#0ca30c; --goodbg:#16301a; --warn:#fab219; --warnbg:#3a2f12; --accent:#3987e5;
 }
}
:root[data-theme="dark"]{
  color-scheme:dark;
  --page:#0d0d0d; --surface:#1a1a19; --raised:#222220; --ink:#f0efec; --ink2:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --axis:#383835; --ring:rgba(255,255,255,.10); --soft:#262624;
  --a:#3987e5; --b:#d95926; --drawc:#55544f; --mid:#383835;
  --good:#0ca30c; --goodbg:#16301a; --warn:#fab219; --warnbg:#3a2f12; --accent:#3987e5;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--page);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
header.top{position:sticky;top:0;z-index:10;background:var(--surface);border-bottom:1px solid var(--ring);
  padding:12px 24px;display:flex;flex-wrap:wrap;align-items:center;gap:6px 22px}
header.top h1{margin:0;font-size:19px;letter-spacing:-.01em}
header.top .sub{color:var(--muted);font-size:13px}
header.top nav{display:flex;flex-wrap:wrap;gap:4px;margin-left:auto}
header.top nav a{color:var(--ink2);text-decoration:none;font-size:13px;padding:4px 10px;border-radius:999px}
header.top nav a:hover{background:var(--soft);color:var(--ink)}
main{max-width:1180px;margin:0 auto;padding:22px 24px 60px}
section{margin-top:40px;scroll-margin-top:70px}
section:first-child{margin-top:0}
section>h2{font-size:20px;margin:0 0 4px;letter-spacing:-.01em}
section>.hint{color:var(--ink2);font-size:13.5px;margin:0 0 14px;max-width:880px}
.card{background:var(--surface);border:1px solid var(--ring);border-radius:14px;padding:18px 20px}
.grid{display:grid;gap:14px}
.g2{grid-template-columns:repeat(auto-fit,minmax(380px,1fr))}
.tiles{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}
.tile{background:var(--surface);border:1px solid var(--ring);border-radius:12px;padding:12px 14px}
.tile .l{color:var(--muted);font-size:12.5px;font-weight:600}
.tile .v{font-size:24px;font-weight:700;margin-top:2px}
.tile .s{color:var(--ink2);font-size:12.5px}
.hero{display:grid;grid-template-columns:minmax(260px,1.2fr) 2fr;gap:14px;align-items:stretch}
.hero .champ{background:var(--surface);border:1px solid var(--ring);border-radius:14px;padding:18px 20px;
  border-left:4px solid var(--accent)}
.champ .l{color:var(--muted);font-size:12.5px;font-weight:600;text-transform:uppercase;letter-spacing:.04em}
.champ .name{font-size:28px;font-weight:750;letter-spacing:-.02em;margin:4px 0 2px}
.champ .s{color:var(--ink2);font-size:14px}
@media(max-width:820px){.hero{grid-template-columns:1fr}}
table{border-collapse:collapse;width:100%}
th,td{padding:7px 10px;text-align:right;border-bottom:1px solid var(--grid);vertical-align:middle}
th{font-weight:650;color:var(--muted);font-size:12px;white-space:nowrap}
td{font-variant-numeric:tabular-nums}
th.l,td.l{text-align:left}
tr:last-child td{border-bottom:0}
.tw{overflow-x:auto}
.muted{color:var(--muted)}
.pill{display:inline-flex;align-items:center;gap:6px;padding:2px 10px;border-radius:999px;font-size:13px;font-weight:650}
.pill.fav{background:var(--goodbg);color:var(--good)}
.pill.close{background:var(--soft);color:var(--ink2);font-weight:550}
.pill.warn{background:var(--warnbg);color:var(--warn)}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;flex:none}
.dot.a{background:var(--a)} .dot.b{background:var(--b)} .dot.d{background:var(--drawc)}
.hbar{display:flex;align-items:center;gap:8px;justify-content:flex-end}
.hbar .t{flex:1;max-width:140px;height:8px;background:var(--soft);border-radius:4px;overflow:hidden}
.hbar .t i{display:block;height:100%;background:var(--a);border-radius:0 4px 4px 0}
/* Matrix */
.matrix td.c{text-align:center;font-weight:650;border:2px solid var(--surface);border-radius:8px;min-width:92px;padding:10px 6px}
.matrix td.c small{display:block;font-weight:500;font-size:11px;opacity:.85}
.matrix td.self{background:var(--soft)}
.matrix th.col{text-align:center;white-space:normal;max-width:110px}
.scale{display:flex;align-items:center;gap:10px;font-size:12.5px;color:var(--ink2);margin-top:12px;flex-wrap:wrap}
.scale .ramp{width:220px;height:10px;border-radius:5px}
/* Paarung */
.match{margin-top:16px}
.mhead{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:14px}
.mhead .side{display:flex;align-items:center;gap:8px;font-size:17px;font-weight:700}
.mhead .side.r{justify-content:flex-end;text-align:right}
.mhead .score{font-size:30px;font-weight:750;letter-spacing:-.02em;text-align:center;white-space:nowrap}
.mhead .score .sep{color:var(--muted);font-weight:500;margin:0 6px}
.verdict{display:flex;justify-content:center;margin:8px 0 12px}
.stack{display:flex;gap:2px;height:14px;margin:6px 0 4px}
.stack i{display:block;height:100%}
.stack i:first-child{border-radius:7px 0 0 7px} .stack i:last-child{border-radius:0 7px 7px 0}
.stack .sa{background:var(--a)} .stack .sd{background:var(--drawc)} .stack .sb{background:var(--b)}
.stackl{display:flex;justify-content:space-between;font-size:12.5px;color:var(--ink2)}
.ci{display:flex;align-items:center;gap:12px;font-size:13px;color:var(--ink2);margin:10px 0 16px;flex-wrap:wrap}
.ci svg{width:260px;height:26px}
.sub-h{font-size:13.5px;font-weight:700;margin:18px 0 8px}
.chart{background:var(--surface);border:1px solid var(--ring);border-radius:12px;padding:12px 14px}
.chart h4{margin:0 0 2px;font-size:13.5px}
.legend{display:flex;gap:14px;font-size:12.5px;color:var(--ink2);margin:2px 0 6px;flex-wrap:wrap}
.legend span{display:inline-flex;align-items:center;gap:6px}
.legend .k{display:inline-block;width:12px;height:10px;border-radius:2px}
.legend .k.ln{height:3px;border-radius:2px}
svg.plot{width:100%;height:auto;display:block;overflow:visible}
svg .gl{stroke:var(--grid);stroke-width:1}
svg .ax{stroke:var(--axis);stroke-width:1}
svg .tk{fill:var(--muted);font-size:11px}
svg .ba{fill:var(--a)} svg .bb{fill:var(--b)}
svg .la{stroke:var(--a)} svg .lb{stroke:var(--b)}
svg .ln{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
svg .pa{fill:var(--a);stroke:var(--surface);stroke-width:2} svg .pb{fill:var(--b);stroke:var(--surface);stroke-width:2}
svg .ch{stroke:var(--ink2);stroke-width:1;opacity:0}
svg .col:hover .ch,svg .col:focus .ch{opacity:.6}
svg .hit{fill:transparent}
svg [data-tip]{cursor:default;outline:none}
svg rect.ba:hover,svg rect.bb:hover,svg rect.ba:focus,svg rect.bb:focus{opacity:.8}
svg .cib{fill:var(--a);opacity:.28} svg .cip{fill:var(--a)} svg .cim{stroke:var(--ink2);stroke-width:1}
details.more{margin-top:14px}
details.more>summary{cursor:pointer;font-weight:650;font-size:13.5px;color:var(--accent);list-style:none}
details.more>summary::-webkit-details-marker{display:none}
details.more>summary::before{content:"\\25B8  "}
details.more[open]>summary::before{content:"\\25BE  "}
td.few{color:var(--muted)}
.cmp td:nth-child(2){color:var(--ink)} .cmp th .dot{margin-right:6px;vertical-align:-1px}
.tt{position:fixed;z-index:50;pointer-events:none;background:var(--raised);color:var(--ink);border:1px solid var(--ring);
  box-shadow:0 6px 24px rgba(0,0,0,.14);border-radius:8px;padding:7px 10px;font-size:12.5px;line-height:1.45;
  white-space:pre;display:none;font-variant-numeric:tabular-nums}
.tt b{display:block;font-size:13.5px}
footer{max-width:1180px;margin:0 auto;padding:0 24px 40px;color:var(--muted);font-size:12px}
@media(max-width:600px){header.top{padding:10px 16px}main{padding:16px 16px 50px}.mhead{grid-template-columns:1fr}
  .mhead .side.r{justify-content:flex-start;text-align:left}.mhead .score{text-align:left}.g2{grid-template-columns:1fr}}
@media print{header.top{position:static}body{background:#fff}.tt{display:none!important}}
"""

JS = """
(function(){
  var tt=document.createElement('div');tt.className='tt';document.body.appendChild(tt);
  function show(el,x,y){
    var lines=(el.getAttribute('data-tip')||'').split('\\n');tt.textContent='';
    lines.forEach(function(s,i){var n=document.createElement(i===0?'b':'div');n.textContent=s;tt.appendChild(n);});
    tt.style.display='block';
    var w=tt.offsetWidth,h=tt.offsetHeight,px=x+14,py=y+14;
    if(px+w>window.innerWidth-8)px=x-w-14; if(py+h>window.innerHeight-8)py=y-h-14;
    tt.style.left=px+'px';tt.style.top=py+'px';
  }
  document.addEventListener('pointermove',function(e){
    var el=e.target.closest&&e.target.closest('[data-tip]');
    if(el)show(el,e.clientX,e.clientY);else tt.style.display='none';
  });
  document.addEventListener('focusin',function(e){
    var el=e.target.closest&&e.target.closest('[data-tip]');if(!el)return;
    var r=el.getBoundingClientRect();show(el,r.left+r.width/2,r.top);
  });
  document.addEventListener('focusout',function(){tt.style.display='none';});
})();
"""


# ---------------------------------------------------------------- Zahlen

def _num(n):
    """Ganze Zahl mit Tausendertrennzeichen (de: 3.000, en: 3,000)."""
    s = f"{int(n):,}"
    return s if is_en() else s.replace(",", ".")


def _f1(x):
    return dec(f"{x:.1f}")


def _pct(a, n, digits=1):
    return dec(f"{100 * a / n:.{digits}f}") + " %" if n else "–"


def _rate(a, n):
    return a / n if n else 0.0


# ---------------------------------------------------------------- Farben (Matrix: divergierend blau <-> rot)

_MID = (240, 239, 236)
_BLUE = (28, 92, 171)
_RED = (176, 40, 40)


def _mix(c1, c2, f):
    return "#%02x%02x%02x" % tuple(round(a + (b - a) * f) for a, b in zip(c1, c2))


def _heat(rate):
    """Zellfarbe fuer eine Siegquote: 50 % grau, darueber blau, darunter rot (ab 25 Punkten Abstand voll)."""
    d = max(-1.0, min(1.0, (rate - 0.5) / 0.25))
    bg = _mix(_MID, _BLUE if d >= 0 else _RED, abs(d))
    return bg, ("#ffffff" if abs(d) > 0.55 else "#0b0b0b")


# ---------------------------------------------------------------- Bausteine

def _tile(label, value, sub=""):
    return (f'<div class="tile"><div class="l">{esc(label)}</div><div class="v">{value}</div>'
            f'<div class="s">{sub}</div></div>')


def _section(sid, title, hint, body):
    hint_html = f'<p class="hint">{hint}</p>' if hint else ""
    return f'<section id="{sid}"><h2>{esc(title)}</h2>{hint_html}{body}</section>'


def _verdict_pill(fav, x, y):
    if fav:
        name = x if fav == "x" else y
        return f'<span class="pill fav">✓ {esc(t("{p} hätte gewinnen sollen", p=name))}</span>'
    return f'<span class="pill close">≈ {esc(t("zu knapp, kein klarer Favorit"))}</span>'


def _ci_svg(lo, hi, p):
    """Kleiner Streifen 0-100 %: 95-%-Bereich als Band, Punkt fuer die Siegquote, Linie bei 50 %."""
    w, h, pad = 260, 26, 4

    def X(v):
        return pad + v * (w - 2 * pad)
    return (f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{esc(t("95-%-Bereich"))}">'
            f'<rect x="{pad}" y="11" width="{w - 2 * pad}" height="4" rx="2" fill="var(--soft)"/>'
            f'<line class="cim" x1="{X(.5):.1f}" x2="{X(.5):.1f}" y1="3" y2="23"/>'
            f'<rect class="cib" x="{X(lo):.1f}" y="7" width="{max(2, X(hi) - X(lo)):.1f}" height="12" rx="4"/>'
            f'<circle class="cip" cx="{X(p):.1f}" cy="13" r="5"/></svg>')


def _axis_y(top, h, x0, x1, y0, vmax, ticks, fmt):
    out = []
    for v in ticks:
        y = y0 - (v / vmax) * h if vmax else y0
        cls = "ax" if v == 0 else "gl"
        out.append(f'<line class="{cls}" x1="{x0}" x2="{x1}" y1="{y:.1f}" y2="{y:.1f}"/>'
                   f'<text class="tk" x="{x0 - 6}" y="{y + 4:.1f}" text-anchor="end">{fmt(v)}</text>')
    return "".join(out)


def _nice_ticks(vmax, n=4):
    if vmax <= 0:
        return [0], 1
    raw = vmax / n
    mag = 10 ** len(str(int(raw))) / 10 if raw >= 1 else 1
    step = next(s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw)
    step = max(1, int(round(step)))
    top = step * (int(vmax // step) + (1 if vmax % step else 0))
    return list(range(0, top + 1, step)), top


def _win_round_chart(m, x, y):
    """Gruppierte Balken: Siege je Runde fuer beide Decks."""
    wa, wb = m["sides"]["x"]["win_rounds"], m["sides"]["y"]["win_rounds"]
    rounds = sorted(set(wa) | set(wb))
    if not rounds:
        return ""
    lo, hi = rounds[0], rounds[-1]
    rr = list(range(lo, hi + 1))
    vmax = max(list(wa.values()) + list(wb.values()) + [1])
    ticks, top = _nice_ticks(vmax)
    W, H, L, R, T, B = 520, 210, 36, 8, 10, 26
    ph, pw = H - T - B, W - L - R
    slot = pw / len(rr)
    bw = max(3.0, min(16.0, (slot - 6) / 2))
    parts = [_axis_y(T, ph, L, W - R, T + ph, top, ticks, _num)]
    for i, r in enumerate(rr):
        cx = L + slot * (i + .5)
        for k, (cls, val, name) in enumerate((("ba", wa.get(r, 0), x), ("bb", wb.get(r, 0), y))):
            if not val:
                continue
            bh = ph * val / top
            bx = cx - bw - 1 + k * (bw + 2)
            tip = t("Runde {r}", r=r) + "\n" + t("{p}: {n} Siege", p=name, n=_num(val))
            parts.append(f'<rect class="{cls}" x="{bx:.1f}" y="{T + ph - bh:.1f}" width="{bw:.1f}" '
                         f'height="{bh:.1f}" rx="2" tabindex="0" data-tip="{esc(tip)}"/>')
        if len(rr) <= 14 or r % 2 == 0:
            parts.append(f'<text class="tk" x="{cx:.1f}" y="{H - 8}" text-anchor="middle">{r}</text>')
    return (f'<div class="chart"><h4>{esc(t("Siege nach Runde"))}</h4>'
            f'<div class="legend"><span><i class="k" style="background:var(--a)"></i>{esc(x)}</span>'
            f'<span><i class="k" style="background:var(--b)"></i>{esc(y)}</span></div>'
            f'<svg class="plot" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(t("Siege nach Runde"))}">'
            f'{"".join(parts)}</svg></div>')


def _life_chart(m, x, y):
    """Linien: durchschnittliche Lebenspunkte beider Decks am Ende jeder Runde."""
    ca, cb = m["life_curve"]["x"], m["life_curve"]["y"]
    n = len(ca)
    if n < 2:
        return ""
    vmax = max(20, max(ca + cb))
    ticks, top = _nice_ticks(vmax)
    W, H, L, R, T, B = 520, 210, 36, 8, 10, 26
    ph, pw = H - T - B, W - L - R

    def X(i):
        return L + pw * i / (n - 1)

    def Y(v):
        return T + ph - ph * v / top
    parts = [_axis_y(T, ph, L, W - R, T + ph, top, ticks, _num)]
    for cls, curve in (("la", ca), ("lb", cb)):
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(curve))
        parts.append(f'<polyline class="ln {cls}" points="{pts}"/>')
    slot = pw / (n - 1)
    for i in range(n):
        tip = (t("Runde {r}", r=i + 1) + "\n" + t("{p}: {v} Leben", p=x, v=_f1(ca[i])) + "\n"
               + t("{p}: {v} Leben", p=y, v=_f1(cb[i])))
        parts.append(f'<g class="col" tabindex="0" data-tip="{esc(tip)}">'
                     f'<rect class="hit" x="{X(i) - slot / 2:.1f}" y="{T}" width="{slot:.1f}" height="{ph}"/>'
                     f'<line class="ch" x1="{X(i):.1f}" x2="{X(i):.1f}" y1="{T}" y2="{T + ph}"/></g>')
        if n <= 14 or (i + 1) % 2 == 0:
            parts.append(f'<text class="tk" x="{X(i):.1f}" y="{H - 8}" text-anchor="middle">{i + 1}</text>')
    for cls, curve in (("pa", ca), ("pb", cb)):
        parts.append(f'<circle class="{cls}" cx="{X(n - 1):.1f}" cy="{Y(curve[-1]):.1f}" r="4"/>')
    return (f'<div class="chart"><h4>{esc(t("Ø Lebenspunkte je Runde"))}</h4>'
            f'<div class="legend"><span><i class="k ln" style="background:var(--a)"></i>{esc(x)}</span>'
            f'<span><i class="k ln" style="background:var(--b)"></i>{esc(y)}</span></div>'
            f'<svg class="plot" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(t("Ø Lebenspunkte je Runde"))}">'
            f'{"".join(parts)}</svg></div>')


def _compare_table(m, x, y):
    sx, sy = m["sides"]["x"], m["sides"]["y"]
    n = m["games"] or 1
    stx, sty = m["start_x"], m["start_y"]
    rows = [
        (t("Siegquote als Beginnender"), _pct(stx["wins"], stx["games"]), _pct(sty["wins"], sty["games"])),
        (t("Siegquote, wenn der Gegner beginnt"), _pct(m["wins_x"] - stx["wins"], sty["games"]),
         _pct(m["wins_y"] - sty["wins"], stx["games"])),
        (t("Ø Kampfschaden je Spiel"), _f1(sx["combat"] / n), _f1(sy["combat"] / n)),
        (t("Ø direkter Schaden je Spiel"), _f1(sx["direct"] / n), _f1(sy["direct"] / n)),
        (t("Ø gestorbene Kreaturen je Spiel"), _f1(sx["deaths"] / n), _f1(sy["deaths"] / n)),
        (t("Ø Restleben bei Sieg"), _f1(_rate(sx["end_life_win"], m["wins_x"])) if m["wins_x"] else "–",
         _f1(_rate(sy["end_life_win"], m["wins_y"])) if m["wins_y"] else "–"),
        (t("Spiele mit Mulligan"), _pct(sx["mull_games"], n), _pct(sy["mull_games"], n)),
        (t("Siegquote nach Mulligan"), _pct(sx["mull_wins"], sx["mull_games"]),
         _pct(sy["mull_wins"], sy["mull_games"])),
    ]
    body = "".join(f'<tr><td class="l">{esc(label)}</td><td>{a}</td><td>{b}</td></tr>' for label, a, b in rows)
    return (f'<div class="chart tw"><table class="cmp"><thead><tr><th class="l">{esc(t("Kennzahl"))}</th>'
            f'<th><i class="dot a"></i>{esc(x)}</th><th><i class="dot b"></i>{esc(y)}</th></tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


def _card_rows(cards, base):
    """Zeilen der Kartentabelle, nach Siegquote auf der Hand sortiert (zu wenige Spiele ans Ende)."""
    def key(item):
        c = item[1]
        return (c["seen"] < MIN_CARD_GAMES, -_rate(c["seen_wins"], c["seen"]), -c["seen"])
    rows = []
    for name, c in sorted(cards.items(), key=key):
        few = c["seen"] < MIN_CARD_GAMES
        gih = _rate(c["seen_wins"], c["seen"])
        delta = (gih - base) * 100
        sign = "+" if delta >= 0.05 else ("−" if delta <= -0.05 else "±")
        cls = ' class="few"' if few else ""
        rows.append(f'<tr><td class="l">{esc(name)}</td><td{cls}>{_num(c["seen"])}</td>'
                    f'<td{cls}>{_pct(c["seen_wins"], c["seen"])}</td>'
                    f'<td{cls}>{sign}{dec(f"{abs(delta):.1f}")}</td>'
                    f'<td{cls}>{_num(c["open"])}</td><td{cls}>{_pct(c["open_wins"], c["open"])}</td></tr>')
    return "".join(rows)


def _card_table(name, dot, cards, base):
    if not cards:
        return ""
    head = (f'<tr><th class="l"><i class="dot {dot}"></i> {esc(name)}</th>'
            f'<th title="{esc(t("Spiele, in denen die Karte in der Starthand war oder im Zugschritt gezogen wurde"))}">'
            f'{esc(t("Auf der Hand"))}</th><th>{esc(t("Siegquote"))}</th>'
            f'<th title="{esc(t("Punkte über oder unter der Siegquote des Decks in diesem Match"))}">'
            f'{esc(t("± Deck"))}</th><th>{esc(t("Starthand"))}</th><th>{esc(t("Siegquote"))}</th></tr>')
    return (f'<div class="chart tw"><table><thead>{head}</thead><tbody>{_card_rows(cards, base)}</tbody>'
            f'</table></div>')


def _match_card(names, m):
    x, y = names[m["x"]], names[m["y"]]
    fav, lo, hi = tm.favourite(m["wins_x"], m["wins_y"])
    n = m["games"] or 1
    decided = m["wins_x"] + m["wins_y"]
    p = _rate(m["wins_x"], decided) if decided else 0.5
    seg = []
    for cls, v in (("sa", m["wins_x"]), ("sd", m["draws"]), ("sb", m["wins_y"])):
        if v:
            seg.append(f'<i class="{cls}" style="flex:{v}" data-tip="{esc(_num(v))}"></i>')
    head = (f'<div class="mhead"><div class="side"><i class="dot a"></i>{esc(x)}</div>'
            f'<div class="score">{_num(m["wins_x"])}<span class="sep">:</span>{_num(m["wins_y"])}</div>'
            f'<div class="side r">{esc(y)}<i class="dot b"></i></div></div>'
            f'<div class="verdict">{_verdict_pill(fav, x, y)}</div>'
            f'<div class="stack">{"".join(seg)}</div>'
            f'<div class="stackl"><span>{esc(t("{p}: {v}", p=x, v=_pct(m["wins_x"], n)))}</span>'
            f'<span>{esc(t("Unentschieden: {n}", n=_num(m["draws"])))}</span>'
            f'<span>{esc(t("{p}: {v}", p=y, v=_pct(m["wins_y"], n)))}</span></div>'
            f'<div class="ci">{_ci_svg(lo, hi, p)}<span>'
            f'{esc(t("Siegquote {p} ohne Unentschieden: {v} (95-%-Bereich {lo}–{hi} %)", p=x, v=_pct(m["wins_x"], decided), lo=_f1(100 * lo), hi=_f1(100 * hi)))}'
            f'</span></div>')
    if "sides" not in m:  # alte Ergebnisse ohne Kennzahlen
        return f'<div class="card match">{head}</div>'
    sx, sy = m["sides"]["x"], m["sides"]["y"]
    st = m["start_x"]["wins"] + m["start_y"]["wins"]
    stg = m["start_x"]["games"] + m["start_y"]["games"]
    avg_len = sum(m["rounds"]) / len(m["rounds"]) if m["rounds"] else 0
    win_life = (sx["end_life_win"] + sy["end_life_win"]) / decided if decided else 0
    tiles = (f'<div class="tiles">'
             f'{_tile(t("Ø Spieldauer"), _f1(avg_len), esc(t("Runden bis zur Entscheidung")))}'
             f'{_tile(t("Beginnender gewinnt"), _pct(st, stg), esc(t("Vorteil, zuerst zu spielen")))}'
             f'{_tile(t("Ø Restleben des Siegers"), _f1(win_life), esc(t("knappe Spiele: niedriger Wert")))}'
             f'{_tile(t("Unentschieden"), _num(m["draws"]), esc(t("Rundengrenze erreicht")))}</div>')
    charts = (f'<div class="grid g2" style="margin-top:14px">{_win_round_chart(m, x, y)}{_life_chart(m, x, y)}</div>'
              f'<div class="sub-h">{esc(t("Direkter Vergleich"))}</div>{_compare_table(m, x, y)}')
    cards = (f'<details class="more"><summary>{esc(t("Kartenstatistik: Siegquote, wenn die Karte auf der Hand war"))}'
             f'</summary><p class="hint muted" style="font-size:12.5px">'
             f'{esc(t("Auf der Hand = in der Starthand oder im Zugschritt gezogen; Basic Lands ausgelassen. Unter {n} Spielen grau (nur ein Hinweis).", n=MIN_CARD_GAMES))}'
             f'</p><div class="grid g2">'
             f'{_card_table(x, "a", sx["cards"], _rate(m["wins_x"], n))}'
             f'{_card_table(y, "b", sy["cards"], _rate(m["wins_y"], n))}</div></details>')
    return f'<div class="card match">{head}{tiles}{charts}{cards}</div>'


# ---------------------------------------------------------------- Abschnitte

def _overview(names, matches, games, decks):
    rows = tm.standings(names, matches)
    total = sum(m["games"] for m in matches)
    rounds = [r for m in matches for r in m.get("rounds", [])]
    st = sum(m["start_x"]["wins"] + m["start_y"]["wins"] for m in matches)
    stg = sum(m["start_x"]["games"] + m["start_y"]["games"] for m in matches)
    favs = sum(1 for m in matches if tm.favourite(m["wins_x"], m["wins_y"])[0])
    draws = sum(m["draws"] for m in matches)
    if rows:
        lead = rows[0]
        rec = f'{lead["match_wins"]}-{lead["match_losses"]}-{lead["match_draws"]}'
        champ = (f'<div class="champ"><div class="l">{esc(t("Statistischer Spitzenreiter"))}</div>'
                 f'<div class="name">{esc(lead["name"])}</div>'
                 f'<div class="s">{esc(t("Match-Bilanz {r} · Spielquote {p}", r=rec, p=_pct(lead["game_wins"], lead["game_wins"] + lead["game_losses"])))}</div></div>')
    else:
        champ = ""
    tiles = (f'<div class="tiles">'
             f'{_tile(t("Simulierte Spiele"), _num(total), esc(t("{n} je Paarung", n=_num(games))))}'
             f'{_tile(t("Ø Spieldauer"), _f1(sum(rounds) / len(rounds)) if rounds else "–", esc(t("Runden bis zur Entscheidung")))}'
             f'{_tile(t("Beginnender gewinnt"), _pct(st, stg), esc(t("über alle Paarungen")))}'
             f'{_tile(t("Klare Favoriten"), f"{favs} / {len(matches)}", esc(t("Paarungen mit statistischem Sieger")))}'
             f'{_tile(t("Unentschieden"), _num(draws), esc(t("Rundengrenze erreicht")))}</div>')
    return f'<div class="hero">{champ}{tiles}</div>'


def _matrix(names, matches):
    idx = sorted({i for m in matches for i in (m["x"], m["y"])})
    cell = {}
    for m in matches:
        cell[(m["x"], m["y"])] = (m["wins_x"], m["wins_y"], m)
        cell[(m["y"], m["x"])] = (m["wins_y"], m["wins_x"], m)
    head = "".join(f'<th class="col">{esc(names[j])}</th>' for j in idx)
    body = []
    for i in idx:
        tds = []
        for j in idx:
            if i == j:
                tds.append('<td class="c self"></td>')
                continue
            if (i, j) not in cell:
                tds.append('<td class="c muted">–</td>')
                continue
            w, l, m = cell[(i, j)]
            rate = _rate(w, w + l) if w + l else 0.5
            bg, fg = _heat(rate)
            fav = tm.favourite(w, l)[0]
            mark = t("klar") if fav == "x" else (t("klar unterlegen") if fav == "y" else t("knapp"))
            tip = t("{a} gegen {b}", a=names[i], b=names[j]) + "\n" + f"{_num(w)} : {_num(l)} · {_pct(w, w + l)}"
            tds.append(f'<td class="c" style="background:{bg};color:{fg}" tabindex="0" data-tip="{esc(tip)}">'
                       f'{_pct(w, w + l, 0)}<small>{esc(mark)}</small></td>')
        body.append(f'<tr><th class="l">{esc(names[i])}</th>{"".join(tds)}</tr>')
    ramp = f"linear-gradient(90deg,{_heat(.25)[0]},{_heat(.5)[0]},{_heat(.75)[0]})"
    return (f'<div class="card tw"><table class="matrix"><thead><tr><th class="l">{esc(t("Zeile gegen Spalte"))}</th>'
            f'{head}</tr></thead><tbody>{"".join(body)}</tbody></table>'
            f'<div class="scale"><span>{esc(t("Zeile verliert"))}</span><span class="ramp" style="background:{ramp}"></span>'
            f'<span>{esc(t("Zeile gewinnt"))}</span><span class="muted">'
            f'{esc(t("Siegquote ohne Unentschieden; 50 % grau"))}</span></div></div>')


def _standings(names, matches, decks):
    notes = {d["name"]: d["notes"] for d in decks or []}
    head = "".join(f'<th class="{"l" if c in (1,) else ""}">{esc(h)}</th>' for c, h in enumerate((
        "#", t("Deck"), t("Matches"), t("Match-Bilanz (S-N-U)"), t("Spiele gewonnen"), t("Spiele verloren"),
        t("Unent."), t("Spielquote"))))
    rows = []
    for pos, r in enumerate(tm.standings(names, matches), 1):
        gw, gl = r["game_wins"], r["game_losses"]
        rate = _rate(gw, gw + gl)
        chip = (f' <span class="pill warn" title="{esc("; ".join(notes[r["name"]]))}">!</span>'
                if notes.get(r["name"]) else "")
        rows.append(f'<tr><td>{pos}</td><td class="l"><b>{esc(r["name"])}</b>{chip}</td><td>{r["matches"]}</td>'
                    f'<td>{r["match_wins"]}-{r["match_losses"]}-{r["match_draws"]}</td><td>{_num(gw)}</td>'
                    f'<td>{_num(gl)}</td><td>{_num(r["game_draws"])}</td>'
                    f'<td><div class="hbar"><b>{_pct(gw, gw + gl)}</b><span class="t"><i style="width:{100 * rate:.1f}%">'
                    f'</i></span></div></td></tr>')
    return (f'<div class="card tw"><table><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>'
            f'</div>')


def _best_worst(stats, best=True):
    ok = [(n, c) for n, c in stats.items() if c["seen"] >= MIN_CARD_GAMES]
    ok.sort(key=lambda it: _rate(it[1]["seen_wins"], it[1]["seen"]), reverse=best)
    return ", ".join(f'{esc(n)} <span class="muted">{_pct(c["seen_wins"], c["seen"], 0)}</span>'
                     for n, c in ok[:TOP_CARDS]) or '<span class="muted">–</span>'


def _decks_section(decks, names, matches):
    rows = tm.standings(names, matches)
    by_name = {r["name"]: r for r in rows}
    head = (f'<th class="l">{esc(t("Deck"))}</th><th>{esc(t("Karten"))}</th><th>{esc(t("Spielquote"))}</th>'
            f'<th class="l">{esc(t("Stärkste Karten"))}</th><th class="l">{esc(t("Schwächste Karten"))}</th>'
            f'<th class="l">{esc(t("Hinweis"))}</th>')
    body = []
    for d in decks:
        i = names.index(d["name"]) if d["name"] in names else -1
        stats = tm.deck_card_stats(matches, i)
        r = by_name.get(d["name"])
        rate = _pct(r["game_wins"], r["game_wins"] + r["game_losses"]) if r else "–"
        note = "; ".join(d["notes"])
        note_html = f'<span class="pill warn">{esc(note)}</span>' if note else '<span class="muted">–</span>'
        body.append(f'<tr><td class="l"><b>{esc(d["name"])}</b></td><td>{d["size"]}</td><td>{rate}</td>'
                    f'<td class="l">{_best_worst(stats, True)}</td><td class="l">{_best_worst(stats, False)}</td>'
                    f'<td class="l">{note_html}</td></tr>')
    return (f'<div class="card tw"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table>'
            f'</div>')


# ---------------------------------------------------------------- Seite

def render(folder, names, matches, games=None, max_turns=20, decks=None):
    games = games or (matches[0]["games"] if matches else 0)
    title = t("Turnier {f}", f=folder)
    played = {i for m in matches for i in (m["x"], m["y"])}
    total = sum(m["games"] for m in matches)
    rules = t("Je Paarung {n} Spiele. Spiel 1 beginnt per Zufall, danach geht der Verlierer des vorigen Spiels "
              "zuerst (Regel 103.1: der Verlierer wählt, im Limited fast immer zuerst spielen); nach einem "
              "Unentschieden beginnt wieder derselbe. Beide Decks spielen nach den Regeln des Kampfmodells und "
              "geben beim Mulligan nie auf. Nach Runde {r} gilt ein Spiel als unentschieden.", n=games, r=max_turns)
    verdict_hint = t("Favorit: Liegt der 95-%-Bereich der Siegquote (ohne Unentschieden) ganz über 50 %, hätte das "
                     "Deck statistisch gewinnen sollen; enthält er 50 %, ist das Matchup zu knapp für eine Aussage.")
    sections = []
    nav = []
    if matches:
        sections.append(_section("ueberblick", t("Überblick"), "", _overview(names, matches, games, decks)))
        nav.append(("ueberblick", t("Überblick")))
    if len(played) > 2:
        sections.append(_section("matrix", t("Matrix"),
                                 esc(t("Siegquote jedes Decks (Zeile) gegen jeden Gegner (Spalte). Blau: die Zeile "
                                       "gewinnt das Matchup, rot: sie verliert es; „klar“ heißt statistisch "
                                       "abgesichert.")), _matrix(names, matches)))
        sections.append(_section("tabelle", t("Tabelle"),
                                 esc(t("Sortiert nach Match-Siegen (mehr gewonnene Spiele der Paarung), dann "
                                       "nach Spielquote.")), _standings(names, matches, decks)))
        nav += [("matrix", t("Matrix")), ("tabelle", t("Tabelle"))]
    sections.append(_section("paarungen", t("Paarungen"), esc(rules) + "<br>" + esc(verdict_hint),
                             "".join(_match_card(names, m) for m in matches)))
    nav.append(("paarungen", t("Paarungen")))
    if decks:
        sections.append(_section("decks", t("Decks"),
                                 esc(t("Unvollständige Decklisten werden trotzdem gespielt und hier gekennzeichnet; "
                                       "ein Deck mit weniger als {n} Karten lässt sich nicht simulieren, seine "
                                       "Paarungen fallen aus.", n=tm.MIN_CARDS)) + " "
                                 + esc(t("Stärkste und schwächste Karten: Siegquote auf der Hand über alle Paarungen, "
                                         "ab {n} Spielen.", n=MIN_CARD_GAMES)),
                                 _decks_section(decks, names, matches)))
        nav.append(("decks", t("Decks")))
    nav_html = "".join(f'<a href="#{sid}">{esc(label)}</a>' for sid, label in nav)
    sub = t("{n} Decks, {m} Paarungen", n=len(played) or len(names), m=len(matches)) + " · " + \
        t("{g} Spiele", g=_num(total))
    return (f'<!DOCTYPE html><html lang="{html_lang()}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)}</title><style>{CSS}</style></head><body>'
            f'<header class="top"><h1>{esc(title)}</h1><span class="sub">{esc(sub)}</span>'
            f'<nav>{nav_html}</nav></header>'
            f'<main>{"".join(sections)}</main>'
            f'<footer>{esc(t("Erzeugt mit mtg_sim.py · Kartendaten von Scryfall"))}</footer>'
            f'<script>{JS}</script></body></html>')
