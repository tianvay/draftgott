"""Setauswertung (--setauswertung [SET], Menue 4 in draftgott.bat): die gesammelte Draft-Statistik eines Sets
(draftstatistik.json, components/draftstats.py) als HTML-Seite setauswertung_<set>.html.

Formate (draftstats.FORMATS) haben eigene Farben: Pick Two (4 Siege / 2 Niederlagen) violett, Pick One (Premier und
Quick Draft, 7 / 3) bernstein, Traditional tuerkis, Sealed blau. Gibt es mehr als ein Format, schaltet ein
Format-Schalter oben alle Abschnitte, die von den Drafts abhaengen (Archetypen, beste Karten, Pick-Wert, Karten,
Bewertung, Runs), zwischen "Alle" und je einem Format um; jede Ansicht ist fertig gerechnet in der Seite.

Abschnitte: Ueberblick (Bilanz, Siegquote, Verlauf, je Format eine Tafel mit Ø Siegen je Run und Trophaeen), Formate im
Vergleich (wie weit Runs kommen, Siegquote je Match-Nummer, Spieltempo in gewonnenen und verlorenen Games),
Archetypen, beste und schwaechste Karten, Formatvorteil (Karten mit deutlich anderer Siegquote in zwei Formaten,
mindestens EDGE_GAMES Games in jedem), Pick-Two-Duos (zusammen genommene Karten, beide im Deck, mit Synergie-Hinweis
aus components/synergy.py), Pick-Wert (Streudiagramm Ø Pick gegen Siegquote: spaet genommene Karten mit hoher Quote
sind "spaete Perlen"), alle Karten (Tabelle mit Suche, Farbfilter und Sortierung), eigene Bewertung gegen Ergebnis,
Runs als Leiter (Siege bis zur Trophaee, Leben = erlaubte Niederlagen).
Siegquoten aus weniger als MIN_GAMES Games sind grau: dafuer ist die Zahl der Spiele zu klein.
"""
import math
import pathlib
import re
import sys
import urllib.error
import webbrowser

from components import archetypes as set_archetypes
from components import cardarchetypes
from components import draftstats as ds
from components import ratings as card_ratings
from components import symbols
from components.html_base import HTML_CSS, esc, h_section, html_cost
from components.i18n import dec, html_lang, is_en, t, tr_block
from components.scryfall import fetch_cards_cached

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = SCRIPT_DIR
MIN_GAMES = 20  # darunter gilt eine Siegquote nur als Hinweis
TOP_GAMES = 10  # Mindestzahl Games fuer "beste und schwaechste Karten"
EDGE_GAMES = 5  # Formatvorteil: Mindestzahl Games in jedem der beiden Formate
EDGE_MIN = 0.10  # Formatvorteil: mindestens 10 Prozentpunkte Unterschied
SCATTER_GAMES = 6  # Pick-Wert: Mindestzahl Games einer Karte
DUO_ROWS = 20
GOOD, BAD = 0.55, 0.45  # Siegquote: gruen ab 55 %, rot unter 45 %
FORMAT_COLOR = {"picktwo": "#7c4dde", "pickone": "#c97700", "trad": "#1a9a8c", "sealed": "#3d6fd1"}
GOLD = "#d4a72c"
CAT_LABEL = {"matchwinner": "♛ Matchwinner", "splashworthy": "★ Splashworthy", "mustplay": "MustPlay", "filler": "Filler", "neverplay": "NeverPlay",
             "": "ohne Kategorie"}
CAT_CLASS = {"matchwinner": "c-mw", "splashworthy": "c-sw", "mustplay": "c-mp", "filler": "c-fi", "neverplay": "c-np", "": "c-no"}
RARITY = {"common": "C", "uncommon": "U", "rare": "R", "mythic": "M"}
CSS = """
main{padding-bottom:40px}
""" + "".join(f".f-{k}{{--fc:{c}}}" for k, c in FORMAT_COLOR.items()) + """
.hero{background:radial-gradient(120% 140% at 0% 0%,#2b4c8f 0%,#17264a 55%,#101a33 100%);color:#fff;
  border-radius:18px;padding:22px 24px;margin:18px 0 6px;box-shadow:0 10px 30px rgba(16,26,51,.28);position:relative;
  overflow:hidden}
.hero::after{content:"";position:absolute;right:-60px;top:-60px;width:260px;height:260px;border-radius:50%;
  background:radial-gradient(circle,rgba(124,77,222,.35),transparent 70%)}
.hero h2{margin:0 0 2px;font-size:25px;border:0;padding:0;color:#fff;position:relative}
.hero .per{opacity:.8;font-size:13.5px;position:relative}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-top:16px;position:relative}
.kpi{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.16);border-radius:12px;padding:10px 14px;
  display:flex;align-items:center;gap:12px}
.kpi b{display:block;font-size:22px;line-height:1.15}
.kpi span{font-size:12.5px;opacity:.8}
.donut{--p:0;--dc:#5be39a;width:54px;height:54px;flex:none;border-radius:50%;display:grid;place-items:center;
  background:conic-gradient(var(--dc) calc(var(--p)*1%),rgba(255,255,255,.18) 0)}
.donut::before{content:attr(data-t);width:40px;height:40px;border-radius:50%;background:#1b2c55;display:grid;
  place-items:center;font-size:12px;font-weight:700}
.fpanels{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px;margin-top:14px;
  position:relative}
.fpanel{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.14);border-top:4px solid var(--fc);
  border-radius:12px;padding:12px 14px;display:grid;grid-template-columns:auto 1fr;gap:4px 14px;align-items:center}
.fpanel .fh{grid-column:1/-1;display:flex;align-items:baseline;gap:8px;margin-bottom:4px}
.fpanel .fh b{font-size:16px}
.fpanel .fh span{font-size:12px;opacity:.75}
.fpanel .donut{--dc:var(--fc)}
.fpanel .big{font-size:26px;font-weight:800;line-height:1}
.fpanel .big small{font-size:12px;font-weight:400;opacity:.8;display:block;margin-top:3px}
.fpanel .fl{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12.5px;opacity:.9;margin-top:6px}
.fpanel .fl b{font-weight:700}
.wl{display:inline-flex;gap:3px;flex-wrap:wrap;vertical-align:middle}
.wl i{width:14px;height:14px;border-radius:4px;display:inline-block;font-style:normal;font-size:9px;line-height:14px;
  text-align:center;color:#fff;font-weight:700}
.wl i.w{background:#2e9e5b}.wl i.l{background:#d6453b}.wl i.o{background:#b7bcc6}
.hero .wl i{box-shadow:0 0 0 1px rgba(255,255,255,.35)}
.tl{margin-top:14px;font-size:12.5px;opacity:.92;position:relative}
.tl .wl{gap:6px}
.tl .wl .tr{display:inline-flex;gap:2px;padding:2px 4px;border-radius:6px;border-bottom:3px solid var(--fc)}
.fswitch{position:sticky;top:calc(var(--hbar) + 6px);z-index:5;display:flex;align-items:center;gap:6px;
  flex-wrap:wrap;background:rgba(244,246,249,.92);backdrop-filter:blur(6px);padding:8px 10px;margin:12px 0 0;
  border:1px solid var(--line);border-radius:99px;width:max-content;max-width:100%}
.fswitch span{font-size:12.5px;color:var(--muted);margin:0 4px 0 6px}
.fswitch button{border:1px solid var(--line);background:#fff;border-radius:99px;padding:5px 14px;cursor:pointer;
  font:inherit;font-size:13px;display:flex;align-items:center;gap:6px}
.fswitch button i{width:10px;height:10px;border-radius:50%;background:var(--fc,#1d2430)}
.fswitch button.on{background:var(--fc,#1d2430);border-color:var(--fc,#1d2430);color:#fff;font-weight:700}
.fswitch button.on i{background:#fff}
.fchip{display:inline-flex;align-items:center;gap:5px;border-radius:99px;padding:1px 8px;font-size:11.5px;
  font-weight:700;color:var(--fc);background:color-mix(in srgb,var(--fc) 12%,#fff);
  border:1px solid color-mix(in srgb,var(--fc) 35%,#fff);white-space:nowrap}
.fchip::before{content:"";width:7px;height:7px;border-radius:50%;background:var(--fc)}
.cardbox{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.fcompare{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}
.fcard{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px;border-top:4px solid var(--fc)}
.fcard h3{margin:0 0 2px;font-size:16px;display:flex;align-items:center;gap:8px}
.fcard .fs{color:var(--muted);font-size:12.5px;margin-bottom:10px}
.fcard h4{margin:14px 0 6px;font-size:13px;color:var(--muted);font-weight:600}
.dist,.bymatch{display:flex;align-items:flex-end;gap:4px;height:120px;padding-top:18px;border-bottom:1px solid var(--line)}
.dist div,.bymatch div{flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;
  height:100%;position:relative;cursor:default}
.dist b,.bymatch b{display:block;width:100%;max-width:38px;background:var(--fc);border-radius:4px 4px 0 0;min-height:2px}
.dist .gold b{background:repeating-linear-gradient(45deg,#d4a72c 0 6px,#e6c35a 6px 12px)}
.bymatch b.few{opacity:.35}
.dist em,.bymatch em{font-style:normal;font-size:11.5px;font-weight:700;margin-bottom:2px}
.axis{display:flex;gap:4px;font-size:11px;color:var(--muted);margin-top:3px}
.axis span{flex:1;text-align:center}
.tempo{width:100%;border-collapse:collapse;font-size:12.5px}
.tempo td,.tempo th{padding:3px 6px;text-align:right;border-bottom:1px solid var(--soft)}
.tempo th{font-weight:600;color:var(--muted)}
.tempo td:first-child,.tempo th:first-child{text-align:left}
.archs{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:12px}
.arch{background:#fff;border:1px solid var(--line);border-radius:14px;padding:12px 14px;position:relative;overflow:hidden}
.arch::before{content:"";position:absolute;left:0;top:0;bottom:0;width:5px;background:var(--ac,#b7bcc6)}
.arch .ah{font-weight:700;font-size:15px;display:flex;align-items:center;gap:6px}
.arch .am{color:var(--muted);font-size:12.5px;margin:2px 0 8px}
.arch .af{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px}
.meter{height:10px;border-radius:99px;background:#eef0f4;overflow:hidden;margin:4px 0 2px}
.meter i{display:block;height:100%;border-radius:99px;background:var(--mc,#2f6fd6)}
.mrow{display:flex;justify-content:space-between;font-size:12.5px;color:var(--muted)}
.mrow b{color:var(--text)}
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:14px;margin:8px 0 18px}
.tile{background:#fff;border:1px solid var(--line);border-radius:12px;padding:6px;position:relative;text-align:center}
.tile img{width:100%;border-radius:8px;display:block;aspect-ratio:488/680;object-fit:cover;background:#e9edf3}
.tile .ph{aspect-ratio:488/680;border-radius:8px;background:#e9edf3;display:grid;place-items:center;padding:8px;
  color:var(--muted);font-size:13px}
.tile .rb{position:absolute;top:10px;right:10px;border-radius:99px;padding:2px 10px;font-weight:800;font-size:13px;
  color:#fff;box-shadow:0 1px 4px rgba(0,0,0,.35)}
.tile .tn{font-weight:700;font-size:13px;margin-top:6px}
.tile .ts{font-size:12px;color:var(--muted)}
.rb.good{background:#2e9e5b}.rb.bad{background:#d6453b}.rb.mid{background:#6b7d99}
h3.sub{font-size:15px;margin:14px 0 2px}
.edge{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px}
.erow{display:grid;grid-template-columns:44px minmax(90px,150px) 1fr 52px;gap:10px;align-items:center;
  padding:5px 0;border-bottom:1px solid var(--soft);font-size:13px}
.erow img,.erow span.ph{width:44px;height:32px;object-fit:cover;border-radius:6px;display:block;background:#e9edf3}
.erow .en{font-weight:600}
.erow .dd2{text-align:right;font-weight:800}
.dumb{position:relative;height:18px}
.dumb::before{content:"";position:absolute;left:0;right:0;top:8px;height:2px;background:var(--soft)}
.dumb .ln{position:absolute;top:8px;height:2px;background:#9aa3b2}
.dumb .dt{position:absolute;top:3px;width:12px;height:12px;margin-left:-6px;border-radius:50%;background:var(--fc);
  box-shadow:0 0 0 2px #fff}
.legend{display:flex;gap:12px;flex-wrap:wrap;font-size:12.5px;color:var(--muted);margin:2px 0 8px}
.duohead{display:flex;flex-wrap:wrap;gap:8px 18px;font-size:13px;margin-bottom:10px}
.duohead b{font-size:18px;display:block}
.duo{display:flex;align-items:center;gap:6px}
.duo img,.duo span.ph{width:34px;height:25px;object-fit:cover;border-radius:5px;display:block;background:#e9edf3}
.duo .plus{color:var(--muted);font-weight:700}
.syn{border-radius:99px;padding:1px 7px;font-size:11px;font-weight:700;background:#e3f4ee;color:#146c52;white-space:nowrap}
.scatter{width:100%;height:auto;display:block}
.scatter .grid{stroke:#e6e9f2;stroke-width:1}
.scatter .avg{stroke:#9aa3b2;stroke-width:1;stroke-dasharray:4 4}
.scatter text{font-size:11px;fill:#667085}
.scatter text.q{font-size:12px;font-weight:700;fill:#b0b7c3}
.scatter text.lb{fill:#1d2430;font-weight:600}
.scatter circle{fill:var(--fc,#2f6fd6);fill-opacity:.75;stroke:#fff;stroke-width:2}
.scatter circle:hover{fill-opacity:1;stroke:#1d2430}
.filters{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center;margin:4px 0 10px}
.filters input[type=search]{flex:1;min-width:200px;font:inherit;padding:7px 10px;border:1px solid var(--line);
  border-radius:8px}
.cf{display:flex;gap:4px}
.cf button{border:1px solid var(--line);background:#fff;border-radius:99px;padding:3px 8px;cursor:pointer;
  font:inherit;font-size:12.5px;display:flex;align-items:center;gap:3px}
.cf button.on{background:#e8f0fd;border-color:var(--accent);font-weight:700}
.filters label{font-size:13px;display:flex;align-items:center;gap:5px}
.count{font-size:12.5px;color:var(--muted)}
table.cards{width:100%;border-collapse:separate;border-spacing:0;font-size:13.5px}
table.cards thead th{background:#f7f8fb}
table.cards th{cursor:pointer;user-select:none;font-size:12px;line-height:1.25;padding:7px 6px}
table.cards td{padding:4px 6px}
table.cards th:hover{color:var(--accent)}
table.cards td{vertical-align:middle}
table.cards tbody tr:hover td{background:#f5f8ff}
td.img{width:48px;padding:3px 4px}
td.img img{width:44px;height:32px;object-fit:cover;border-radius:6px;display:block}
td.img span{display:block;width:44px;height:32px;border-radius:6px;background:#e9edf3}
table.cards td:nth-child(2){font-weight:600;min-width:130px;max-width:170px}
.rar{display:inline-block;width:10px;height:10px;border-radius:50%;border:1px solid rgba(0,0,0,.2)}
.rar.common{background:#2b2b2b}.rar.uncommon{background:#9fb2c2}.rar.rare{background:#d4a72c}
.rar.mythic{background:#e2531f}
.cat{border-radius:99px;padding:1px 7px;font-size:11px;font-weight:700;white-space:nowrap}
.cat.c-mw{background:#ead7fb;color:#5b1a8f}.cat.c-sw{background:#ffe7a3;color:#5a4100}.cat.c-mp{background:#d9f3e4;color:#146c3d}
.cat.c-fi{background:#e6ebf3;color:#4a5a73}.cat.c-np{background:#f6dcdc;color:#8b2f2f}
td.cost{white-space:nowrap}
td.cost .m.ms{width:16px;height:16px}
td.aps{white-space:nowrap}
.ap{display:inline-flex;gap:0;margin-right:5px;padding:1px 3px;border:1px solid var(--line);border-radius:6px;
  background:#fafbfc;cursor:help}
.ap .m.ms{width:13px;height:13px;margin:0}
td.rate,td.few{min-width:90px}
td.rate .rv,td.few .rv{display:flex;align-items:center;gap:8px}
td.rate .rv b,td.few .rv b{min-width:38px;text-align:right}
td.rate .meter,td.few .meter{flex:1;margin:0}
table.duos{width:100%;border-collapse:separate;border-spacing:0;font-size:13.5px}
table.duos thead th{background:#f7f8fb;font-size:12px;padding:7px 6px}
table.duos td{padding:4px 6px;vertical-align:middle}
table.duos tbody tr:hover td{background:#f5f8ff}
td.rate.good b{color:var(--good)}td.rate.good .meter i{background:#2e9e5b}
td.rate.bad b{color:var(--bad)}td.rate.bad .meter i{background:#d6453b}
td.rate.mid .meter i{background:#6b7d99}
.few{color:var(--muted);font-style:italic}
.few .meter i{background:#c3c8d2}
.cats{display:grid;gap:10px}
.catrow{display:grid;grid-template-columns:150px 1fr 190px;gap:12px;align-items:center;font-size:13.5px}
.runs{display:grid;gap:10px}
.run{background:#fff;border:1px solid var(--line);border-left:6px solid var(--fc);border-radius:14px;
  padding:12px 16px;display:grid;grid-template-columns:150px 1fr minmax(180px,260px) 70px;gap:6px 16px;
  align-items:center}
.run.trophy{background:linear-gradient(90deg,#fff 60%,#fff8e1)}
.run .dd{font-weight:700}.run .de{color:var(--muted);font-size:12.5px;margin-top:2px}
.run .rec{font-size:22px;font-weight:800;text-align:right}
.run .rec small{display:block;font-size:11.5px;font-weight:400;color:var(--muted)}
.ladder{display:flex;align-items:center;gap:3px}
.ladder .stp{flex:1;height:10px;border-radius:3px;background:var(--soft)}
.ladder .stp.on{background:var(--fc)}
.ladder .trophy{font-size:18px;line-height:1;margin-left:4px;filter:grayscale(1);opacity:.3}
.ladder .trophy.on{filter:none;opacity:1}
.lives{display:flex;align-items:center;gap:3px;margin-top:5px;font-size:12px;color:var(--muted)}
.lives .life{font-style:normal;font-size:14px;line-height:1;color:#d6453b}
.lives .life.off{color:#c9ced8}
.lives .stt{margin-left:6px}
.hint2{font-size:12.5px;color:var(--muted);margin-top:6px}
@media(max-width:760px){.catrow{grid-template-columns:1fr}.run{grid-template-columns:1fr}.run .rec{text-align:left}
  .erow{grid-template-columns:44px 1fr 52px}.erow .dumb{grid-column:1/-1}.fswitch{border-radius:14px;position:static}}
"""
JS = """<script>
document.querySelectorAll("table.cards").forEach(t=>{t.querySelectorAll("th").forEach((th,i)=>{
 if(th.dataset.nosort!==undefined)return;th.title="Sortieren";
 th.onclick=()=>{const b=t.tBodies[0],rows=[...b.rows],up=th.dataset.dir!=="down";
  t.querySelectorAll("th").forEach(x=>delete x.dataset.dir);th.dataset.dir=up?"down":"up";
  const v=r=>{const c=r.cells[i],s=c.dataset.v!==undefined?c.dataset.v:c.textContent.trim();const n=parseFloat(s);
   return isNaN(n)?s.toLowerCase():n};
  rows.sort((a,b)=>{const x=v(a),y=v(b);return (x<y?-1:x>y?1:0)*(up?-1:1)});rows.forEach(r=>b.appendChild(r))}})});
const tbls=[...document.querySelectorAll("table.cards")];let apply=()=>{};
if(tbls.length){const q=document.getElementById("cq"),only=document.getElementById("conly"),cnt=document.getElementById("ccount");
 let col="";
 apply=()=>{const s=q.value.trim().toLowerCase();
  for(const tbl of tbls){let n=0;
   for(const r of tbl.tBodies[0].rows){const cs=r.dataset.colors||"";
    const ok=(!s||r.dataset.name.includes(s))&&(!only.checked||+r.dataset.games>0)&&
     (!col||(col==="M"?cs.length>1:col==="C"?cs==="":cs===col));
    r.style.display=ok?"":"none";if(ok)n++}
   if(!tbl.closest("[hidden]"))cnt.textContent=n+" von "+tbl.tBodies[0].rows.length+" Karten"}};
 q.oninput=apply;only.onchange=apply;
 document.querySelectorAll(".cf button").forEach(b=>b.onclick=()=>{col=col===b.dataset.c?"":b.dataset.c;
  document.querySelectorAll(".cf button").forEach(x=>x.classList.toggle("on",x.dataset.c===col));apply()});
 apply()}
const setView=v=>{document.querySelectorAll(".vw").forEach(e=>e.hidden=e.dataset.view!==v);
 document.querySelectorAll(".fswitch button").forEach(b=>b.classList.toggle("on",b.dataset.v===v));
 try{localStorage.setItem("setauswertung-view",v)}catch(e){}apply()};
document.querySelectorAll(".fswitch button").forEach(b=>b.onclick=()=>setView(b.dataset.v));
try{const v=localStorage.getItem("setauswertung-view");if(v&&document.querySelector('.fswitch button[data-v="'+v+'"]'))setView(v)}catch(e){}
</script>"""
JS_EN = {'th.title="Sortieren"': 'th.title="Sort"', '" von "': '" of "', '" Karten"': '" cards"'}


def output_name(code):
    return f"setauswertung_{code.lower()}.html"


def _pct(wins, games):
    return f"{round(100 * wins / games)} %" if games else "–"


def _level(wins, games):
    if not games:
        return ""
    r = wins / games
    return "good" if r >= GOOD else "bad" if r < BAD else "mid"


def _rate_td(wins, games):
    """Siegquote als Zelle mit Balken; unter MIN_GAMES grau (nur ein Hinweis)."""
    if not games:
        return '<td data-v="-1">–</td>'
    if games < MIN_GAMES:
        attr = ' class="few" title="%s"' % t("Weniger als {n} Games: nur ein Hinweis", n=MIN_GAMES)
    else:
        attr = f' class="rate {_level(wins, games)}"'
    return (f'<td data-v="{wins / games:.4f}"{attr}><div class="rv"><b>{_pct(wins, games)}</b>'
            f'<div class="meter"><i style="width:{100 * wins / games:.0f}%"></i></div></div></td>')


def _meter(wins, games, color=None):
    style = f' style="width:{100 * wins / games:.0f}%' + (f';background:{color}"' if color else '"') if games else \
        ' style="width:0"'
    return f'<div class="meter"><i{style}></i></div>'


def _colors(cards):
    out = {}
    for name, sc in cards.items():
        faces = sc.get("card_faces") or []
        out[name] = sc.get("colors") or (faces[0].get("colors") if faces else None) or []
    return out


def _image(sc, kind):
    uris = sc.get("image_uris") or ((sc.get("card_faces") or [{}])[0].get("image_uris")) or {}
    return uris.get(kind) or ""


def _thumb(sc, cls=""):
    art = _image(sc or {}, "art_crop")
    return f'<img src="{esc(art)}" alt="" loading="lazy">' if art else '<span class="ph"></span>'


def _event_label(event):
    """"PickTwoDraft_TRK_20261110" -> "Pick Two Draft"."""
    head = (event or "").split("_")[0]
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", head) or "Draft"


def _event_extra(event, key):
    """Eventname neben dem Formatabzeichen, wenn er mehr sagt als das Format ("Premier Draft" ja, "Pick Two Draft" nein)."""
    label = _event_label(event)
    return "" if label.replace(" ", "").lower().startswith(_fmt_label(key).replace(" ", "").lower()) else esc(label)


def _results(rec):
    return [m for m in rec.get("matches") or [] if m.get("win") is not None]


def _wl(rec):
    win_ch, loss_ch, win_t, loss_t = ("W", "L", "win", "loss") if is_en() else ("S", "N", "Sieg", "Niederlage")
    pills = "".join(f'<i class="w" title="{win_t}">{win_ch}</i>' if m["win"]
                    else f'<i class="l" title="{loss_t}">{loss_ch}</i>' for m in _results(rec))
    pills += "".join(f'<i class="o" title="{t("läuft noch")}">·</i>' for m in rec.get("matches") or []
                     if m.get("win") is None)
    return f'<span class="wl">{pills}</span>'


def _mana(colors):
    return html_cost("".join("{" + c + "}" for c in colors))


def _fmt_label(key):
    return ds.FORMATS[key]["label"]


def _fmt_rule(key):
    f = ds.FORMATS[key]
    if "matches" in f:
        return t("{n} Matches", n=f["matches"])
    return t("{w} Siege / {l} Niederlagen", w=f["wins"], l=f["losses"])


def _fchip(key, text=None):
    return f'<span class="fchip f-{key}">{esc(text if text is not None else _fmt_label(key))}</span>'


ACCENT = {"W": "#d8c77a", "U": "#2a74c4", "B": "#3a3340", "R": "#d0453a", "G": "#2e9560"}


def _format_panel(key, s):
    rate = round(100 * s["match_wins"] / s["matches"]) if s["matches"] else 0
    avg = dec(f'{s["avg_wins"]:.1f}') if s["avg_wins"] is not None else "–"
    trophies = (t("1 Trophäe") if s["trophies"] == 1 else t("{n} Trophäen", n=s["trophies"]))
    trophy_rate = f' ({_pct(s["trophies"], s["done"])})' if s["done"] else ""
    runs = t("{n} Runs, {d} abgeschlossen", n=s["runs"], d=s["done"]) if s["runs"] != 1 else \
        t("1 Run, {d} abgeschlossen", d=s["done"])
    return (f'<div class="fpanel f-{key}"><div class="fh"><b>{esc(_fmt_label(key))}</b>'
            f'<span>{esc(_fmt_rule(key))}</span></div>'
            f'<div class="donut" style="--p:{rate}" data-t="{rate} %" title="{t("Matches gewonnen")}"></div>'
            f'<div class="big">Ø {avg}<small>{t("Siege je abgeschlossenem Run")}</small></div>'
            f'<div class="fl"><span>🏆 <b>{trophies}</b>{trophy_rate}</span><span>{esc(runs)}</span>'
            f'<span>Matches <b>{s["match_wins"]}-{s["matches"] - s["match_wins"]}</b></span>'
            f'<span>Games <b>{s["wins"]}-{s["games"] - s["wins"]}</b></span></div></div>')


def _overview(data, code, records):
    s = ds.summary(data, code)
    drafts = s["drafts"]
    losses, glosses = s["matches"] - s["match_wins"], s["games"] - s["wins"]
    rate = round(100 * s["match_wins"] / s["matches"]) if s["matches"] else 0
    dates = sorted(r.get("started") or "" for r in records if r.get("started"))
    period = (t("{a} bis {b}", a=dates[0], b=dates[-1]) if dates and dates[0] != dates[-1] else (dates[0] if dates else ""))
    timeline = "".join(f'<span class="tr f-{ds.event_format(r.get("event"))}" title="{esc(_fmt_label(ds.event_format(r.get("event"))))}">'
                       f'{_wl(r)}</span>' for r in sorted(records, key=lambda r: r.get("started") or ""))
    per_draft = dec(f"{(s['match_wins'] / drafts if drafts else 0):.1f}")
    kpis = (f'<div class="kpi"><div class="donut" style="--p:{rate}" data-t="{rate} %"></div><div>'
            f'<b>{s["match_wins"]}-{losses}</b><span>Matches</span></div></div>'
            f'<div class="kpi"><div><b>{drafts} Draft{"s" if drafts != 1 else ""}</b><span>{t("mitgelesen")}</span>'
            f'</div></div>'
            f'<div class="kpi"><div><b>{s["wins"]}-{glosses}</b><span>'
            + t("Games, {p} gewonnen", p=_pct(s["wins"], s["games"])) +
            f'</span></div></div>'
            f'<div class="kpi"><div><b>{per_draft}</b>'
            f'<span>{t("Siege je Draft")}</span></div></div>')
    fs = ds.format_summary(data, code)
    panels = "".join(_format_panel(k, fs[k]) for k in ds.FORMATS if k in fs)
    return (f'<div class="hero"><h2>{t("Setauswertung {code}", code=esc(code))}</h2>'
            f'<div class="per">{esc(period)} · {t("alle mitgelesenen Drafts des Sets")}</div>'
            f'<div class="kpis">{kpis}</div><div class="fpanels">{panels}</div>'
            f'<div class="tl"><span class="wl">'
            + t("Match-Verlauf (älteste zuerst): {timeline}", timeline=timeline) + '</span></div>'
            f'</div>')


def _switch(fmts):
    buttons = f'<button type="button" class="on" data-v="all"><i></i>{t("Alle Formate")}</button>' + "".join(
        f'<button type="button" class="f-{k}" data-v="{k}"><i></i>{esc(_fmt_label(k))}</button>' for k in fmts)
    return f'<div class="fswitch"><span>{t("Ansicht")}</span>{buttons}</div>'


def _bars(values, labels, titles, cls, fewer=None, gold=None):
    """Saeulen (Hoehe 0..1) mit Zahl darueber und Achse darunter."""
    cols = []
    for i, (v, lab, tip) in enumerate(zip(values, labels, titles)):
        extra = ' class="gold"' if gold == i else ""
        few = ' class="few"' if fewer and fewer[i] else ""
        cols.append(f'<div{extra} title="{esc(tip)}"><em>{esc(lab)}</em><b{few} style="height:{max(v, 0) * 100:.0f}%">'
                    f'</b></div>')
    return f'<div class="{cls}">{"".join(cols)}</div>'


def _formats_compare(fs):
    out = []
    for key in ds.FORMATS:
        if key not in fs:
            continue
        s, f = fs[key], ds.FORMATS[key]
        top = max(s["dist"]) or 1
        runs_t = [t("{w} Siege: 1 Run", w=w) if n == 1 else t("{w} Siege: {n} Runs", w=w, n=n)
                  for w, n in enumerate(s["dist"])]
        dist = _bars([n / top for n in s["dist"]], [str(n) if n else "" for n in s["dist"]], runs_t, "dist",
                     gold=f["wins"])
        axis = '<div class="axis">' + "".join(f"<span>{w}{' 🏆' if w == f['wins'] else ''}</span>"
                                              for w in range(f["wins"] + 1)) + "</div>"
        bm = s["by_match"]
        bym = _bars([w / n if n else 0 for w, n in bm], [_pct(w, n) for w, n in bm],
                    [t("Match {i}: {w} von {n} gewonnen", i=i + 1, w=w, n=n) for i, (w, n) in enumerate(bm)],
                    "bymatch", fewer=[n < 3 for _w, n in bm])
        bm_axis = '<div class="axis">' + "".join(f"<span>{i + 1}</span>" for i in range(len(bm))) + "</div>"
        tempo = s["tempo"]
        if tempo["win"]["games"] or tempo["loss"]["games"]:
            def cells(d):
                return "".join(f"<td>{dec(f'{d[k]:.1f}') if d['games'] else '–'}</td>" for k in ds.TEMPO)
            tempo_html = (f'<h4>{t("Spieltempo (Ø je Game)")}</h4><table class="tempo"><tr><th></th>'
                          f'<th>{t("Züge")}</th><th>{t("Zauber")}</th><th>{t("Besiegt")}</th><th>{t("Schaden")}</th></tr>'
                          f'<tr><td>{t("Gewonnen")} ({tempo["win"]["games"]})</td>{cells(tempo["win"])}</tr>'
                          f'<tr><td>{t("Verloren")} ({tempo["loss"]["games"]})</td>{cells(tempo["loss"])}</tr></table>')
        else:
            tempo_html = ""
        out.append(f'<div class="fcard f-{key}"><h3>{_fchip(key)} <span>{esc(_fmt_rule(key))}</span></h3>'
                   f'<div class="fs">{t("{d} abgeschlossene Runs von {n}", d=s["done"], n=s["runs"])}</div>'
                   f'<h4>{t("Wie weit kommen deine Runs? (Siege am Ende)")}</h4>{dist}{axis}'
                   + (f'<h4>{t("Siegquote je Match-Nummer")}</h4>{bym}{bm_axis}' if bm else "")
                   + tempo_html + '</div>')
    return f'<div class="fcompare">{"".join(out)}</div>'


def _archetypes(records, code, colors, assign, ratings, show_formats=False):
    found = set_archetypes.for_set(code) or []
    by = {}
    for rec in records:
        key = ds.record_archetype(rec, colors, assign, ratings) or ""
        b = by.setdefault(key, {"drafts": 0, "matches": 0, "mw": 0, "games": 0, "gw": 0, "fmt": {}})
        b["drafts"] += 1
        st = ds.run_state(rec)
        fb = b["fmt"].setdefault(st["format"], [0, 0, 0])  # Drafts, Siege, Trophaeen
        fb[0] += 1
        fb[1] += st["wins"]
        fb[2] += 1 if st["trophy"] else 0
        for m in _results(rec):
            b["matches"] += 1
            b["mw"] += 1 if m["win"] else 0
            b["games"] += len(m["games"])
            b["gw"] += sum(1 for g in m["games"] if g)
    if not by:
        return f'<p class="hint">{t("Keine Drafts.")}</p>'
    names = {a["colors"]: a["name"] for a in found}
    out = []
    for key in sorted(by, key=lambda k: (-by[k]["drafts"], -by[k]["mw"], k)):
        b = by[key]
        accent = (f"linear-gradient({ACCENT[key[0]]} 50%,{ACCENT[key[1]]} 50%)" if len(key) == 2 else "#b7bcc6")
        title = f'{_mana(key)} {esc(names.get(key, key))}' if key else t("noch offen")
        lvl = _level(b["mw"], b["matches"])
        color = {"good": "#2e9e5b", "bad": "#d6453b"}.get(lvl, "#6b7d99")
        chips = ""
        if show_formats:
            chips = '<div class="af">' + "".join(
                _fchip(k, f'{_fmt_label(k)} · ' + t("{n}× · Ø {w} Siege", n=v[0], w=dec(f"{v[1] / v[0]:.1f}"))
                       + (f" · {v[2]}🏆" if v[2] else ""))
                for k, v in sorted(b["fmt"].items(), key=lambda kv: list(ds.FORMATS).index(kv[0]))) + "</div>"
        out.append(f'<div class="arch" style="--ac:{accent}"><div class="ah">{title}</div>'
                   f'<div class="am">{b["drafts"]} Draft{"s" if b["drafts"] != 1 else ""} · Matches '
                   f'{b["mw"]}-{b["matches"] - b["mw"]}</div>'
                   f'<div class="mrow"><span>{t("Matches gewonnen")}</span><b>{_pct(b["mw"], b["matches"])}</b></div>'
                   f'{_meter(b["mw"], b["matches"], color)}'
                   f'<div class="mrow"><span>{t("Games gewonnen")}</span><b>{_pct(b["gw"], b["games"])}</b></div>'
                   f'{_meter(b["gw"], b["games"], color)}{chips}</div>')
    return f'<div class="archs">{"".join(out)}</div>'


def _tile(name, st, sc):
    img = _image(sc, "normal")
    pic = f'<img src="{esc(img)}" alt="{esc(name)}" loading="lazy">' if img else f'<div class="ph">{esc(name)}</div>'
    lvl = _level(st["wins"], st["games"]) or "mid"
    return (f'<div class="tile">{pic}<span class="rb {lvl}">{_pct(st["wins"], st["games"])}</span>'
            f'<div class="tn">{esc(name)}</div><div class="ts">{st["games"]} Games · {st["decks"]} '
            f'Deck{"s" if st["decks"] != 1 else ""} · ' + t("{n}× gedraftet", n=st["drafted"]) + '</div></div>')


def _best(stats, cards):
    enough = {n: s for n, s in stats.items() if s["games"] >= TOP_GAMES}
    if not enough:
        return ('<p class="hint">' + t("Noch keine Karte mit mindestens {n} Games im Hauptdeck – je mehr Drafts "
                                       "mitgelesen werden, desto aussagekräftiger wird diese Liste.", n=TOP_GAMES)
                + '</p>')
    order = sorted(enough, key=lambda n: (-enough[n]["wins"] / enough[n]["games"], -enough[n]["games"]))
    top = order[:6]
    low = [n for n in order[::-1][:6] if n not in top]
    out = f'<h3 class="sub">{t("Am stärksten")}</h3><div class="tiles">' + "".join(
        _tile(n, enough[n], cards.get(n) or {}) for n in top) + "</div>"
    if low:
        out += f'<h3 class="sub">{t("Am schwächsten")}</h3><div class="tiles">' + "".join(
            _tile(n, enough[n], cards.get(n) or {}) for n in low) + "</div>"
    return out


def _edge(by_fmt, fmts, cards):
    """Formatvorteil: Karten mit mindestens EDGE_GAMES Games in beiden Formaten und EDGE_MIN Unterschied."""
    a, b = fmts[:2]
    sa, sb = by_fmt[a], by_fmt[b]
    rows = []
    for name in sa:
        x, y = sa[name], sb.get(name)
        if not y or x["games"] < EDGE_GAMES or y["games"] < EDGE_GAMES:
            continue
        ra, rb = x["wins"] / x["games"], y["wins"] / y["games"]
        if abs(ra - rb) >= EDGE_MIN - 1e-9:
            rows.append((ra - rb, name, ra, rb, x["games"], y["games"]))
    legend = (f'<div class="legend">{_fchip(a)} {_fchip(b)} <span>'
              + t("Punkt = Siegquote der Games mit der Karte im Deck; Linie = Unterschied.") + '</span></div>')
    if not rows:
        return legend + '<p class="hint">' + t(
            "Noch keine Karte mit mindestens {n} Games in beiden Formaten und {d} Prozentpunkten Unterschied.",
            n=EDGE_GAMES, d=round(EDGE_MIN * 100)) + '</p>'

    def row(d, name, ra, rb, ga, gb):
        lo, hi = sorted((ra, rb))
        tip = t("{a}: {ra} in {ga} Games · {b}: {rb} in {gb} Games", a=_fmt_label(a), ra=f"{round(ra * 100)} %", ga=ga,
                b=_fmt_label(b), rb=f"{round(rb * 100)} %", gb=gb)
        return (f'<div class="erow" title="{esc(tip)}">{_thumb(cards.get(name))}<div class="en">{esc(name)}</div>'
                f'<div class="dumb"><i class="ln" style="left:{lo * 100:.0f}%;width:{(hi - lo) * 100:.0f}%"></i>'
                f'<i class="dt f-{a}" style="left:{ra * 100:.0f}%"></i><i class="dt f-{b}" style="left:{rb * 100:.0f}%">'
                f'</i></div><div class="dd2">{"+" if d > 0 else "−"}{abs(round(d * 100))}</div></div>')

    plus = sorted((r for r in rows if r[0] > 0), key=lambda r: -r[0])[:8]
    minus = sorted((r for r in rows if r[0] < 0), key=lambda r: r[0])[:8]
    cols = []
    for key, lst in ((a, plus), (b, minus)):
        body = "".join(row(*r) for r in lst) or f'<p class="hint">{t("Keine.")}</p>'
        cols.append(f'<div class="cardbox"><h3 class="sub" style="margin-top:0">'
                    f'{t("Stärker in {f}", f=esc(_fmt_label(key)))}</h3>{body}</div>')
    return legend + f'<div class="edge">{"".join(cols)}</div>'


def _syn_partner(sa, sb):
    """Synergie zweier Scryfall-Karten (components/synergy.py): Name der Ressource oder ""."""
    if not sa or not sb:
        return ""
    try:
        from components import livedraft, synergy
        ta, tb = livedraft._syn_tags(sa), livedraft._syn_tags(sb)
    except Exception:  # noqa: BLE001 - eine Karte, die der Parser nicht kennt, hat eben keine Synergie
        return ""
    for x, y in ((ta, tb), (tb, ta)):
        common = set(x.get("wants") or {}) & set(y.get("gives") or {})
        if common:
            return synergy.label(sorted(common)[0])
    return ""


def _duos(data, code, cards):
    pairs = ds.pair_stats(data, code)
    drafts = sum(1 for r in data.get("drafts", []) if ds._in_set(r, code) and ds.pick_pairs(r))
    in_deck = {p: v for p, v in pairs.items() if v["decks"]}
    syn = {p: _syn_partner(cards.get(p[0]), cards.get(p[1])) for p in in_deck}
    sw = [sum(in_deck[p]["wins"] for p in in_deck if bool(syn[p]) == flag) for flag in (True, False)]
    sg = [sum(in_deck[p]["games"] for p in in_deck if bool(syn[p]) == flag) for flag in (True, False)]
    head = (f'<div class="duohead"><div><b>{len(pairs)}</b>{t("Duos in {n} Pick-Two-Drafts", n=drafts)}</div>'
            f'<div><b>{len(in_deck)}</b>{t("beide im Hauptdeck")}</div>'
            f'<div><b>{_pct(sw[0], sg[0])}</b>' + t("Games gewonnen mit Synergie-Duo ({n} Games)", n=sg[0]) + '</div>'
            f'<div><b>{_pct(sw[1], sg[1])}</b>' + t("ohne Synergie ({n} Games)", n=sg[1]) + '</div></div>')
    if not in_deck:
        return head + '<p class="hint">' + t("Noch kein Duo, bei dem beide Karten im Hauptdeck gelandet sind.") + '</p>'
    order = sorted(in_deck, key=lambda p: (-in_deck[p]["games"], -in_deck[p]["count"], p))[:DUO_ROWS]
    rows = []
    for p in order:
        v = in_deck[p]
        duo = (f'<div class="duo">{_thumb(cards.get(p[0]))}<span class="plus">+</span>{_thumb(cards.get(p[1]))}'
               f'<span>{esc(p[0])} + {esc(p[1])}</span></div>')
        rows.append(f'<tr data-name="{esc((p[0] + " " + p[1]).lower())}"><td class="l">{duo}</td>'
                    f'<td>{v["count"]}</td><td>{v["decks"]}</td><td>{v["games"]}</td>{_rate_td(v["wins"], v["games"])}'
                    f'<td class="l">' + (f'<span class="syn" title="{t("Synergie")}">🔗 {esc(syn[p])}</span>'
                                         if syn[p] else "") + '</td></tr>')
    th = "".join(f'<th class="{"l" if i in (0, 5) else ""}">{t(h)}</th>' for i, h in enumerate(
        ("Duo", "Zusammen gepickt", "Beide im Deck", "Games", "Games gewonnen", "Synergie")))
    return (head + '<div class="cardbox" style="padding:0;overflow:auto"><table class="duos cards2">'
            f'<thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def _scatter(stats, cards, key):
    """Pick-Wert: Ø Pick (x) gegen Siegquote der Games (y), Groesse = Games."""
    pts = [(n, s) for n, s in stats.items() if s["games"] >= SCATTER_GAMES and s["avg_pick"]]
    if len(pts) < 3:
        return '<p class="hint">' + t("Noch zu wenige Karten mit mindestens {n} Games und bekanntem Pick.",
                                      n=SCATTER_GAMES) + '</p>'
    w, h, ml, mr, mt, mb = 760, 340, 44, 16, 14, 34
    xmax = max(2, math.ceil(max(s["avg_pick"] for _n, s in pts)))
    games = sum(s["games"] for _n, s in pts)
    avg = sum(s["wins"] for _n, s in pts) / games
    gmax = max(s["games"] for _n, s in pts)

    def x(v):
        return ml + (v - 1) / (xmax - 1) * (w - ml - mr)

    def y(r):
        return mt + (1 - r) * (h - mt - mb)

    grid = "".join(f'<line class="grid" x1="{ml}" x2="{w - mr}" y1="{y(r):.1f}" y2="{y(r):.1f}"/>'
                   f'<text x="{ml - 6}" y="{y(r) + 4:.1f}" text-anchor="end">{round(r * 100)} %</text>'
                   for r in (0, .25, .5, .75, 1))
    grid += "".join(f'<text x="{x(v):.1f}" y="{h - mb + 16}" text-anchor="middle">{v}</text>'
                    for v in range(1, xmax + 1))
    grid += (f'<text x="{(ml + w - mr) / 2:.0f}" y="{h - 4}" text-anchor="middle">'
             f'{t("Ø Pick (rechts = später genommen)")}</text>')
    grid += f'<line class="avg" x1="{ml}" x2="{w - mr}" y1="{y(avg):.1f}" y2="{y(avg):.1f}"/>'
    grid += (f'<text class="q" x="{w - mr - 6}" y="{mt + 14}" text-anchor="end">{t("Späte Perlen")}</text>'
             f'<text class="q" x="{ml + 6}" y="{mt + 14}">{t("Früh und stark")}</text>'
             f'<text class="q" x="{ml + 6}" y="{h - mb - 8}">{t("Überschätzt?")}</text>'
             f'<text class="q" x="{w - mr - 6}" y="{h - mb - 8}" text-anchor="end">{t("Zu Recht spät")}</text>')
    dots, labels = [], []
    order = sorted(pts, key=lambda p: -p[1]["games"])
    pearls = sorted(pts, key=lambda p: -((p[1]["wins"] / p[1]["games"] - avg) * (p[1]["avg_pick"] - 1)))[:4]
    for n, s in order:
        r = s["wins"] / s["games"]
        rad = 4 + 7 * math.sqrt(s["games"] / gmax)
        tip = t("{name}: {p} in {g} Games, Ø Pick {pick}", name=n, p=_pct(s["wins"], s["games"]), g=s["games"],
                pick=dec(f'{s["avg_pick"]:.1f}'))
        dots.append(f'<circle cx="{x(s["avg_pick"]):.1f}" cy="{y(r):.1f}" r="{rad:.1f}"><title>{esc(tip)}</title>'
                    f'</circle>')
    placed = []
    for n, s in pearls:
        r = s["wins"] / s["games"]
        if r <= avg:
            continue
        cx = x(s["avg_pick"])
        anchor = "end" if cx > w * .7 else "start"
        span = (cx - 12 - 7 * len(n), cx) if anchor == "end" else (cx, cx + 12 + 7 * len(n))
        if any(abs(y(r) - py) < 16 and span[0] < b and a < span[1] for a, b, py in placed):
            continue  # Beschriftungen ueberlappen nicht: der Punkt bleibt, der Name steht im Tooltip
        placed.append((span[0], span[1], y(r)))
        labels.append(f'<text class="lb" x="{cx + (-12 if anchor == "end" else 12):.1f}" y="{y(r) + 4:.1f}" '
                      f'text-anchor="{anchor}">{esc(n)}</text>')
    cls = f' f-{key}' if key != "all" else ""
    return (f'<div class="cardbox{cls}"><svg class="scatter" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="{t("Pick-Wert")}">{grid}{"".join(dots)}{"".join(labels)}</svg>'
            f'<div class="hint2">' + t("Gestrichelt: Ø Siegquote dieser Karten ({p}). Kreisgröße = Games; mit der Maus "
                                       "auf einen Punkt zeigen für Name und Zahlen.", p=f"{round(avg * 100)} %")
            + '</div></div>')


CARD_HEAD = ["", "Karte", "Kosten", "Selt.", "Kategorie", "Archetypen", "Gedraftet", "Ø Pick", "Im Deck", "Games",
             "Games gewonnen", "Matches"]


def _filters():
    return (f'<div class="filters"><input type="search" id="cq" placeholder="{t("Karte suchen")}">'
            '<div class="cf">' + "".join(f'<button type="button" data-c="{c}" title="{t(cn)}">'
                                         f'{_mana(c) if c in "WUBRG" else t(cn)}'
                                         '</button>' for c, cn in (("W", "Weiß"), ("U", "Blau"), ("B", "Schwarz"),
                                                                   ("R", "Rot"), ("G", "Grün"), ("M", "Mehrfarbig"),
                                                                   ("C", "Farblos")))
            + f'</div><label><input type="checkbox" id="conly"> {t("nur gespielte Karten")}</label>'
            '<span class="count" id="ccount"></span></div>')


def _card_table(stats, cards, assign, ratings, arch_names, view="all"):
    rows = []
    for name, st in sorted(stats.items(), key=lambda kv: (-kv[1]["games"], -kv[1]["drafted"], kv[0])):
        sc = cards.get(name) or {}
        faces = sc.get("card_faces") or []
        cost = sc.get("mana_cost") or (faces[0].get("mana_cost") if faces else "") or ""
        colors = "".join(c for c in "WUBRG" if c in (sc.get("colors") or (faces[0].get("colors") if faces else [])
                                                    or []))
        cat = ratings.get(name, "")
        mine = assign.get(name, [])
        arch = "".join(f'<span class="ap" title="{esc(arch_names.get(a, a))}">{_mana(a)}</span>' for a in mine)
        arch_sort = ", ".join(arch_names.get(a, a) for a in mine)
        avg = st["avg_pick"]
        art = _image(sc, "art_crop")
        rarity = sc.get("rarity") or ""
        rows.append(
            f'<tr data-name="{esc(name.lower())}" data-colors="{colors}" data-games="{st["games"]}">'
            + (f'<td class="img"><img src="{esc(art)}" alt="" loading="lazy"></td>' if art
               else '<td class="img"><span></span></td>')
            + f'<td class="l">{esc(name)}</td><td class="l cost">{html_cost(cost)}</td>'
            f'<td data-v="{"CURM".find(RARITY.get(rarity, "-"))}">'
            + (f'<span class="rar {rarity}" title="{esc(rarity)}"></span>' if rarity else "") + '</td>'
            f'<td class="l" data-v="{list(CAT_LABEL).index(cat)}">'
            + (f'<span class="cat {CAT_CLASS[cat]}">{esc(t(CAT_LABEL[cat]))}</span>' if cat else "") + '</td>'
            f'<td class="l aps" data-v="{esc(arch_sort.lower())}">{arch}</td><td>{st["drafted"]}</td>'
            f'<td data-v="{avg if avg is not None else 99}">{dec(f"{avg:g}") if avg else "–"}</td>'
            f'<td>{st["decks"]}</td><td>{st["games"]}</td>{_rate_td(st["wins"], st["games"])}'
            f'<td data-v="{st["match_wins"]}">{st["match_wins"]}-{st["matches"] - st["match_wins"]}</td></tr>')
    head = "".join(f'<th class="{"l" if i in (1, 2, 4, 5) else ""}"{" data-nosort" if i == 0 else ""}>{t(h)}</th>'
                   for i, h in enumerate(CARD_HEAD))
    return (f'<div class="cardbox" style="padding:0;overflow:auto"><table class="cards" id="cardtable-{view}">'
            f'<thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def _ratings_vs_results(stats, ratings):
    rows = []
    for cat in ("matchwinner", "splashworthy", "mustplay", "filler", "neverplay", ""):
        names = [n for n in stats if ratings.get(n, "") == cat]
        played = [n for n in names if stats[n]["games"]]
        games = sum(stats[n]["games"] for n in names)
        wins = sum(stats[n]["wins"] for n in names)
        lvl = _level(wins, games)
        color = {"good": "#2e9e5b", "bad": "#d6453b"}.get(lvl, "#6b7d99") if games >= MIN_GAMES else "#c3c8d2"
        label = (f'<span class="cat {CAT_CLASS[cat]}">{esc(t(CAT_LABEL[cat]))}</span>' if cat
                 else esc(t(CAT_LABEL[cat])))
        rows.append(f'<div class="catrow"><span>{label}</span>'
                    f'<div>{_meter(wins, games, color)}</div>'
                    f'<span><b>{_pct(wins, games)}</b> '
                    + t("in {games} Games · {played} von {total} Karten gespielt", games=games, played=len(played),
                        total=len(names)) + '</span></div>')
    return f'<div class="cardbox cats">{"".join(rows)}</div>'


def _ladder(st):
    f = ds.FORMATS[st["format"]]
    steps = "".join(f'<i class="stp{" on" if i < st["wins"] else ""}"></i>' for i in range(f["wins"]))
    lives = "".join(f'<i class="life{" off" if i < st["losses"] else " on"}">♥</i>' for i in range(f["losses"]))
    status = (t("Trophäe") if st["trophy"] else t("ausgeschieden") if st["done"] else t("läuft"))
    return (f'<div><div class="ladder" title="{esc(_fmt_rule(st["format"]))}">{steps}'
            f'<span class="trophy{" on" if st["trophy"] else ""}">🏆</span></div>'
            f'<div class="lives">{lives}<span class="stt">{esc(status)}</span></div></div>')


def _drafts(records, colors, assign, ratings, arch_names):
    out = []
    order = sorted(enumerate(records), key=lambda ir: (ir[1].get("started") or "", ir[0]), reverse=True)
    for _i, rec in order:  # neueste zuerst; am selben Tag der spaeter gesammelte
        ms = _results(rec)
        mw = sum(1 for m in ms if m["win"])
        games = sum(len(m["games"]) for m in ms)
        gw = sum(1 for m in ms for g in m["games"] if g)
        key = ds.record_archetype(rec, colors, assign, ratings)
        deck = (rec.get("deck") or {}).get("main") or {}
        picks = len(rec.get("picks") or [])
        arch = f'{_mana(key)} {esc(arch_names.get(key, key))}' if key else t("Archetyp offen")
        info = (f'{picks} Picks' if picks else t("Draft nicht mitgelesen")) + (
            t(" · Deck {n} Karten", n=sum(deck.values())) if deck else "")
        st = ds.run_state(rec)
        state = " trophy" if st["trophy"] else " out" if st["done"] else " live"
        out.append(f'<div class="run f-{st["format"]}{state}"><div><div class="dd">{esc(rec.get("started") or "")}</div>'
                   f'<div class="de">{_fchip(st["format"])} {_event_extra(rec.get("event"), st["format"])}</div></div>'
                   f'<div><div style="font-weight:600">{arch}</div><div class="de">{esc(info)}</div>'
                   f'<div style="margin-top:4px">{_wl(rec)}</div></div>'
                   f'{_ladder(st)}'
                   f'<div class="rec">{mw}-{len(ms) - mw}<small>{t("Games {a}-{b}", a=gw, b=games - gw)}</small></div></div>')
    return f'<div class="runs">{"".join(out)}</div>'


def _views(views, render):
    """Je Ansicht ein Block; ausser "Alle" versteckt (Format-Schalter)."""
    if len(views) == 1:
        return render(views[0])
    return "".join(f'<div class="vw" data-view="{v}"{"" if v == "all" else " hidden"}>{render(v)}</div>'
                   for v in views)


def render_set_report(data, set_code, cards, assign, ratings):
    """HTML der Setauswertung; cards: Scryfall-Daten je Name (fuer Farben, Kosten, Seltenheit, Bilder)."""
    symbols.reset_used()
    code = (set_code or "").upper()
    records = [r for r in data.get("drafts", []) if (r.get("set") or "").upper() == code]
    colors = _colors(cards)
    arch_names = {a["colors"]: a["name"] for a in set_archetypes.for_set(code) or []}
    fmts = ds.formats_in(data, code)
    multi = len(fmts) > 1
    views = ["all"] + fmts if multi else ["all"]
    stats = {v: ds.card_stats(data, code, fmt=None if v == "all" else v) for v in views}
    recs = {v: [r for r in records if v == "all" or ds.event_format(r.get("event")) == v] for v in views}
    nav_items = [("ueberblick", "Überblick")]
    if not records:
        sections = [h_section("ueberblick", t("Überblick"), "", "<p>" + t(
            "Noch keine Drafts für dieses Set in der Statistik. "
            "Starte den Live-Draft (Menüpunkt 3), dann werden Drafts und Matches gesammelt.") + "</p>")]
    else:
        fs = ds.format_summary(data, code)
        sections = [f'<section id="ueberblick">{_overview(data, code, records)}</section>']
        if multi:
            sections.append(_switch(fmts))
        sections.append(h_section("formate", t("Formate im Vergleich"), t(
            "Je Format: wie viele Siege deine Runs am Ende hatten (Gold = Trophäe), wie oft du das 1., 2., 3. … "
            "Match gewinnst (später triffst du auf Gegner mit ähnlicher Bilanz; blass = weniger als 3 Matches) und "
            "wie lange gewonnene und verlorene Games dauern (Spielstatistik, Züge beider Spieler)."),
            _formats_compare(fs)))
        nav_items.append(("formate", "Formate"))
        sections.append(h_section("archetypen", t("Archetypen"),
                                  t("Je Draft erkannt wie im Live-Draft: aus dem Hauptdeck (sonst den Picks), mit deiner "
                                    "Archetyp-Zuordnung und Kategorie."),
                                  _views(views, lambda v: _archetypes(recs[v], code, colors, assign, ratings,
                                                                      show_formats=multi and v == "all"))))
        nav_items.append(("archetypen", "Archetypen"))
        sections.append(h_section("beste", t("Beste und schwächste Karten"),
                                  t("Karten mit mindestens {n} Games im Hauptdeck, nach Siegquote der Games.", n=TOP_GAMES),
                                  _views(views, lambda v: _best(stats[v], cards))))
        nav_items.append(("beste", "Beste und schwächste"))
        if multi:
            sections.append(h_section("formatvorteil", t("Formatvorteil"), t(
                "Karten, die in einem Format deutlich besser abschneiden als im anderen (mindestens {n} Games in "
                "jedem). Bei Pick Two kommt der Synergie-Partner oft im selben Pick mit – solche Karten steigen hier "
                "nach oben.", n=EDGE_GAMES), _edge(stats, fmts, cards)))
            nav_items.append(("formatvorteil", "Formatvorteil"))
        if "picktwo" in fmts:
            sections.append(h_section("duos", t("Pick-Two-Duos"), t(
                "Paare, die du im selben Pick zusammen genommen hast und die beide im Hauptdeck gelandet sind, nach "
                "Games mit beiden im Deck. 🔗 = die Karten haben Synergie (Geber und Nehmer wie im Drafthelper)."),
                _duos(data, code, cards)))
            nav_items.append(("duos", "Duos"))
        sections.append(h_section("pickwert", t("Pick-Wert"), t(
            "Wann du eine Karte genommen hast gegen wie gut sie lief (mindestens {n} Games). Rechts oben stehen "
            "späte Picks mit hoher Siegquote – die lohnt es sich früher zu nehmen; links unten frühe Picks, die "
            "enttäuscht haben.", n=SCATTER_GAMES), _views(views, lambda v: _scatter(stats[v], cards, v))))
        nav_items.append(("pickwert", "Pick-Wert"))
        sections.append(h_section("karten", t("Karten"),
                                  t("Gedraftet: Kopien. Ø Pick: Pick-Nummer im Pack (1 = erster Pick aus einem vollen Pack; bei "
                                    "Pick Two zählen Picks, nicht Karten). Im Deck: Drafts, in deren Hauptdeck die Karte war. "
                                    "Games und Matches: mit der Karte im Hauptdeck; grün ab {good} %, rot unter {bad} %, grau "
                                    "unter {min} Games (nur ein Hinweis). Klick auf eine Spalte sortiert.",
                                    good=round(GOOD * 100), bad=round(BAD * 100), min=MIN_GAMES),
                                  _filters() + _views(views, lambda v: _card_table(stats[v], cards, assign, ratings,
                                                                                   arch_names, v))))
        nav_items.append(("karten", "Karten"))
        sections.append(h_section("bewertung", t("Bewertung gegen Ergebnis"),
                                  t("Deine Kategorien (kartenbewertung.json) und wie Karten jeder Kategorie im Deck "
                                    "abgeschnitten haben (Games je Karte gezählt). Liegt Filler über MustPlay, lohnt ein "
                                    "zweiter Blick auf die Bewertung."),
                                  _views(views, lambda v: _ratings_vs_results(stats[v], ratings))))
        nav_items.append(("bewertung", "Bewertung"))
        sections.append(h_section("drafts", t("Drafts"), t(
            "Neueste zuerst; S = Sieg, N = Niederlage, grau = läuft noch. Die Leiter zeigt die Siege bis zur "
            "Trophäe, die Herzen die Niederlagen, die das Format erlaubt."),
            _views(views, lambda v: _drafts(recs[v], colors, assign, ratings, arch_names))))
        nav_items.append(("drafts", "Drafts"))
    nav = "".join(f'<a href="#{sid}">{esc(t(label))}</a>' for sid, label in nav_items)
    css = HTML_CSS + CSS + symbols.symbol_css(symbols.used())
    return (f'<!DOCTYPE html><html lang="{html_lang()}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{t("Setauswertung {code}", code=esc(code))}</title><style>{css}</style></head><body>'
            f'<header class="top" id="top"><h1>{t("Setauswertung {code}", code=esc(code))}</h1>'
            f'<span class="sub">{t("aus der Draft-Statistik des Live-Drafts")}</span></header>'
            f'<div class="layout"><nav><h3>{t("Abschnitte")}</h3><div class="in">{nav}</div></nav>'
            f'<main>{"".join(sections)}</main></div>'
            f'<footer>{t("Erzeugt mit mtg_sim.py · Kartendaten und Bilder von Scryfall")}</footer>'
            f'{tr_block(JS, JS_EN)}</body></html>')


def _path(name):
    p = pathlib.Path(name)
    return p if p.is_absolute() else SCRIPT_DIR / p


def run(args):
    """Schreibt die Setauswertung (Set wie angegeben, sonst das haeufigste der Statistik) und oeffnet sie."""
    data = ds.load_stats(_path(args.statistik))
    code = (args.setauswertung or "").upper() or next(iter(ds.sets_in(data)), "")
    if not code:
        sys.exit(t("Noch keine Drafts in {path}. Starte den Live-Draft (Menüpunkt 3), dann werden "
                   "Drafts und Matches gesammelt.", path=_path(args.statistik)))
    names = sorted(ds.card_stats(data, code))
    try:
        cards = fetch_cards_cached(names) if names else {}
    except (urllib.error.URLError, OSError) as e:
        print(t("Scryfall nicht erreichbar, Auswertung ohne Kartendaten: {e}", e=e), file=sys.stderr)
        cards = {}
    assign = cardarchetypes.load_assign(_path(args.archetypen))
    ratings = card_ratings.load_ratings(_path(args.bewertung))
    out = OUT_DIR / output_name(code)
    out.write_text(render_set_report(data, code, cards, assign, ratings), encoding="utf-8")
    print(t("Setauswertung gespeichert: {path}", path=out), file=sys.stderr)
    if not args.nicht_oeffnen:
        try:
            webbrowser.open(out.resolve().as_uri())
        except Exception:
            pass
    return out
