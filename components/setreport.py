"""Setauswertung (--setauswertung [SET], Menue 4 in draftgott.bat): die gesammelte Draft-Statistik eines Sets
(draftstatistik.json, components/draftstats.py) als HTML-Seite setauswertung_<set>.html.

Abschnitte: Ueberblick (Bilanz, Siegquote, Verlauf), Archetypen (erkannt wie im Live-Draft aus Hauptdeck bzw. Picks),
beste und schwaechste Karten (Kartenbilder), alle Karten (Tabelle mit Suche, Farbfilter und Sortierung nach jeder
Spalte), eigene Bewertung gegen Ergebnis, Liste der Drafts mit Match-Verlauf.
Siegquoten aus weniger als MIN_GAMES Games sind grau: dafuer ist die Zahl der Spiele zu klein.
"""
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
GOOD, BAD = 0.55, 0.45  # Siegquote: gruen ab 55 %, rot unter 45 %
CAT_LABEL = {"matchwinner": "♛ Matchwinner", "splashworthy": "★ Splashworthy", "mustplay": "MustPlay", "filler": "Filler", "neverplay": "NeverPlay",
             "": "ohne Kategorie"}
CAT_CLASS = {"matchwinner": "c-mw", "splashworthy": "c-sw", "mustplay": "c-mp", "filler": "c-fi", "neverplay": "c-np", "": "c-no"}
RARITY = {"common": "C", "uncommon": "U", "rare": "R", "mythic": "M"}
CSS = """
main{padding-bottom:40px}
.hero{background:linear-gradient(135deg,#1e3a70 0%,#2f6fd6 60%,#4f8ef0 100%);color:#fff;border-radius:16px;
  padding:20px 24px;margin:18px 0 6px;box-shadow:0 6px 20px rgba(31,58,112,.25)}
.hero h2{margin:0 0 2px;font-size:24px;border:0;padding:0;color:#fff}
.hero .per{opacity:.85;font-size:13.5px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-top:16px}
.kpi{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.22);border-radius:12px;padding:10px 14px;
  display:flex;align-items:center;gap:12px}
.kpi b{display:block;font-size:22px;line-height:1.15}
.kpi span{font-size:12.5px;opacity:.85}
.donut{--p:0;width:54px;height:54px;flex:none;border-radius:50%;display:grid;place-items:center;
  background:conic-gradient(#5be39a calc(var(--p)*1%),rgba(255,255,255,.25) 0)}
.donut::before{content:attr(data-t);width:40px;height:40px;border-radius:50%;background:#2a5bb5;display:grid;
  place-items:center;font-size:12px;font-weight:700}
.wl{display:inline-flex;gap:3px;flex-wrap:wrap;vertical-align:middle}
.wl i{width:14px;height:14px;border-radius:4px;display:inline-block;font-style:normal;font-size:9px;line-height:14px;
  text-align:center;color:#fff;font-weight:700}
.wl i.w{background:#2e9e5b}.wl i.l{background:#d6453b}.wl i.o{background:#b7bcc6}
.hero .wl i{box-shadow:0 0 0 1px rgba(255,255,255,.35)}
.cardbox{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.archs{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:12px}
.arch{background:#fff;border:1px solid var(--line);border-radius:14px;padding:12px 14px;position:relative;overflow:hidden}
.arch::before{content:"";position:absolute;left:0;top:0;bottom:0;width:5px;background:var(--ac,#b7bcc6)}
.arch .ah{font-weight:700;font-size:15px;display:flex;align-items:center;gap:6px}
.arch .am{color:var(--muted);font-size:12.5px;margin:2px 0 8px}
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
td.rate .rv{display:flex;align-items:center;gap:8px}
td.rate .rv b{min-width:38px;text-align:right}
td.rate .meter{flex:1;margin:0}
td.rate.good b{color:var(--good)}td.rate.good .meter i{background:#2e9e5b}
td.rate.bad b{color:var(--bad)}td.rate.bad .meter i{background:#d6453b}
td.rate.mid .meter i{background:#6b7d99}
.few{color:var(--muted);font-style:italic}
.few .meter i{background:#c3c8d2}
.cats{display:grid;gap:10px}
.catrow{display:grid;grid-template-columns:150px 1fr 190px;gap:12px;align-items:center;font-size:13.5px}
.drafts{display:grid;gap:10px}
.draft{background:#fff;border:1px solid var(--line);border-radius:14px;padding:12px 16px;display:grid;
  grid-template-columns:110px 1fr auto;gap:6px 16px;align-items:center}
.draft .dd{font-weight:700}.draft .de{color:var(--muted);font-size:12.5px}
.draft .rec{font-size:20px;font-weight:800;text-align:right}
.draft .rec small{display:block;font-size:11.5px;font-weight:400;color:var(--muted)}
.hint2{font-size:12.5px;color:var(--muted);margin-top:6px}
@media(max-width:700px){.catrow{grid-template-columns:1fr}.draft{grid-template-columns:1fr}.draft .rec{text-align:left}}
"""
JS = """<script>
document.querySelectorAll("table.cards").forEach(t=>{t.querySelectorAll("th").forEach((th,i)=>{
 if(th.dataset.nosort!==undefined)return;th.title="Sortieren";
 th.onclick=()=>{const b=t.tBodies[0],rows=[...b.rows],up=th.dataset.dir!=="down";
  t.querySelectorAll("th").forEach(x=>delete x.dataset.dir);th.dataset.dir=up?"down":"up";
  const v=r=>{const c=r.cells[i],s=c.dataset.v!==undefined?c.dataset.v:c.textContent.trim();const n=parseFloat(s);
   return isNaN(n)?s.toLowerCase():n};
  rows.sort((a,b)=>{const x=v(a),y=v(b);return (x<y?-1:x>y?1:0)*(up?-1:1)});rows.forEach(r=>b.appendChild(r))}})});
const tbl=document.getElementById("cardtable");
if(tbl){const q=document.getElementById("cq"),only=document.getElementById("conly"),cnt=document.getElementById("ccount");
 let col="";
 const apply=()=>{const s=q.value.trim().toLowerCase();let n=0;
  for(const r of tbl.tBodies[0].rows){const cs=r.dataset.colors||"";
   const ok=(!s||r.dataset.name.includes(s))&&(!only.checked||+r.dataset.games>0)&&
    (!col||(col==="M"?cs.length>1:col==="C"?cs==="":cs===col));
   r.style.display=ok?"":"none";if(ok)n++}
  cnt.textContent=n+" von "+tbl.tBodies[0].rows.length+" Karten"};
 q.oninput=apply;only.onchange=apply;
 document.querySelectorAll(".cf button").forEach(b=>b.onclick=()=>{col=col===b.dataset.c?"":b.dataset.c;
  document.querySelectorAll(".cf button").forEach(x=>x.classList.toggle("on",x.dataset.c===col));apply()});
 apply()}
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


def _event_label(event):
    """"PickTwoDraft_TRK_20261110" -> "Pick Two Draft"."""
    head = (event or "").split("_")[0]
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", head) or "Draft"


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


ACCENT = {"W": "#d8c77a", "U": "#2a74c4", "B": "#3a3340", "R": "#d0453a", "G": "#2e9560"}


def _overview(data, code, records):
    s = ds.summary(data, code)
    drafts = s["drafts"]
    losses, glosses = s["matches"] - s["match_wins"], s["games"] - s["wins"]
    rate = round(100 * s["match_wins"] / s["matches"]) if s["matches"] else 0
    dates = sorted(r.get("started") or "" for r in records if r.get("started"))
    period = (t("{a} bis {b}", a=dates[0], b=dates[-1]) if dates and dates[0] != dates[-1] else (dates[0] if dates else ""))
    timeline = "".join(_wl(r) for r in sorted(records, key=lambda r: r.get("started") or ""))
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
    return (f'<div class="hero"><h2>{t("Setauswertung {code}", code=esc(code))}</h2>'
            f'<div class="per">{esc(period)} · {t("alle mitgelesenen Drafts des Sets")}</div>'
            f'<div class="kpis">{kpis}</div>'
            f'<div style="margin-top:14px;font-size:12.5px;opacity:.9">'
            + t("Match-Verlauf (älteste zuerst): {timeline}", timeline=timeline) + '</div>'
            f'</div>')


def _archetypes(records, code, colors, assign, ratings):
    found = set_archetypes.for_set(code) or []
    by = {}
    for rec in records:
        key = ds.record_archetype(rec, colors, assign, ratings) or ""
        b = by.setdefault(key, {"drafts": 0, "matches": 0, "mw": 0, "games": 0, "gw": 0})
        b["drafts"] += 1
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
        out.append(f'<div class="arch" style="--ac:{accent}"><div class="ah">{title}</div>'
                   f'<div class="am">{b["drafts"]} Draft{"s" if b["drafts"] != 1 else ""} · Matches '
                   f'{b["mw"]}-{b["matches"] - b["mw"]}</div>'
                   f'<div class="mrow"><span>{t("Matches gewonnen")}</span><b>{_pct(b["mw"], b["matches"])}</b></div>'
                   f'{_meter(b["mw"], b["matches"], color)}'
                   f'<div class="mrow"><span>{t("Games gewonnen")}</span><b>{_pct(b["gw"], b["games"])}</b></div>'
                   f'{_meter(b["gw"], b["games"], color)}</div>')
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


CARD_HEAD = ["", "Karte", "Kosten", "Selt.", "Kategorie", "Archetypen", "Gedraftet", "Ø Pick", "Im Deck", "Games",
             "Games gewonnen", "Matches"]


def _card_table(stats, cards, assign, ratings, arch_names):
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
    filters = (f'<div class="filters"><input type="search" id="cq" placeholder="{t("Karte suchen")}">'
               '<div class="cf">' + "".join(f'<button type="button" data-c="{c}" title="{t(cn)}">'
                                            f'{_mana(c) if c in "WUBRG" else t(cn)}'
                                            '</button>' for c, cn in (("W", "Weiß"), ("U", "Blau"), ("B", "Schwarz"),
                                                                      ("R", "Rot"), ("G", "Grün"), ("M", "Mehrfarbig"),
                                                                      ("C", "Farblos")))
               + f'</div><label><input type="checkbox" id="conly"> {t("nur gespielte Karten")}</label>'
               '<span class="count" id="ccount"></span></div>')
    return (filters + f'<div class="cardbox" style="padding:0;overflow:auto"><table class="cards" id="cardtable">'
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
        out.append(f'<div class="draft"><div><div class="dd">{esc(rec.get("started") or "")}</div>'
                   f'<div class="de">{esc(_event_label(rec.get("event")))}</div></div>'
                   f'<div><div style="font-weight:600">{arch}</div><div class="de">{esc(info)}</div>'
                   f'<div style="margin-top:4px">{_wl(rec)}</div></div>'
                   f'<div class="rec">{mw}-{len(ms) - mw}<small>{t("Games {a}-{b}", a=gw, b=games - gw)}</small></div></div>')
    return f'<div class="drafts">{"".join(out)}</div>'


def render_set_report(data, set_code, cards, assign, ratings):
    """HTML der Setauswertung; cards: Scryfall-Daten je Name (fuer Farben, Kosten, Seltenheit, Bilder)."""
    symbols.reset_used()
    code = (set_code or "").upper()
    records = [r for r in data.get("drafts", []) if (r.get("set") or "").upper() == code]
    stats = ds.card_stats(data, code)
    colors = _colors(cards)
    arch_names = {a["colors"]: a["name"] for a in set_archetypes.for_set(code) or []}
    if not records:
        sections = [h_section("ueberblick", t("Überblick"), "", "<p>" + t(
            "Noch keine Drafts für dieses Set in der Statistik. "
            "Starte den Live-Draft (Menüpunkt 3), dann werden Drafts und Matches gesammelt.") + "</p>")]
    else:
        sections = [
            f'<section id="ueberblick">{_overview(data, code, records)}</section>',
            h_section("archetypen", t("Archetypen"),
                      t("Je Draft erkannt wie im Live-Draft: aus dem Hauptdeck (sonst den Picks), mit deiner "
                        "Archetyp-Zuordnung und Kategorie."), _archetypes(records, code, colors, assign, ratings)),
            h_section("beste", t("Beste und schwächste Karten"),
                      t("Karten mit mindestens {n} Games im Hauptdeck, nach Siegquote der Games.", n=TOP_GAMES),
                      _best(stats, cards)),
            h_section("karten", t("Karten"),
                      t("Gedraftet: Kopien. Ø Pick: Pick-Nummer im Pack (1 = erster Pick aus einem vollen Pack; bei "
                        "Pick Two zählen Picks, nicht Karten). Im Deck: Drafts, in deren Hauptdeck die Karte war. "
                        "Games und Matches: mit der Karte im Hauptdeck; grün ab {good} %, rot unter {bad} %, grau "
                        "unter {min} Games (nur ein Hinweis). Klick auf eine Spalte sortiert.",
                        good=round(GOOD * 100), bad=round(BAD * 100), min=MIN_GAMES), _card_table(stats, cards, assign, ratings, arch_names)),
            h_section("bewertung", t("Bewertung gegen Ergebnis"),
                      t("Deine Kategorien (kartenbewertung.json) und wie Karten jeder Kategorie im Deck "
                        "abgeschnitten haben (Games je Karte gezählt). Liegt Filler über MustPlay, lohnt ein "
                        "zweiter Blick auf die Bewertung."), _ratings_vs_results(stats, ratings)),
            h_section("drafts", t("Drafts"), t("Neueste zuerst; S = Sieg, N = Niederlage, grau = läuft noch."),
                      _drafts(records, colors, assign, ratings, arch_names)),
        ]
    nav = "".join(f'<a href="#{sid}">{esc(t(label))}</a>' for sid, label in
                  (("ueberblick", "Überblick"), ("archetypen", "Archetypen"), ("beste", "Beste und schwächste"),
                   ("karten", "Karten"), ("bewertung", "Bewertung"), ("drafts", "Drafts")))
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
