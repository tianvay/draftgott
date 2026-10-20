"""HTML-Bericht zusammensetzen: Detailabschnitte je Deck und die komplette Seite."""
import datetime
import re
from collections import Counter

from components.battle_server import FIGHT_COUNTS
from components.howitworks import render_help_view
from components.html_base import HTML_CSS, LAYOUT_JS, LABEL_CLASS, esc, h_bar_cell, h_legend, h_level_pill, h_level_td, h_mode, h_pct, h_section, h_table, html_cost, html_mana, svg_bars, svg_lines
from components import symbols
from components.jace import analyze_jace
from components.landadvice import color_report, level, needs_of_alts
from components.mana import required_colors
from components.mulligan import MULL_COLORS, MULL_LANDS_HIGH, MULL_LANDS_LOW
from components.report_sections import render_compare_section, render_jace_section, render_logic_section
from components.coverage import METRIC_ORDER, STATUS_TEXT, metrics_of, summarize
from components.report_cards import (all_colors_row, avail_level, render_color_availability, render_color_curves,
                                     render_graveyard_table, render_removal_table, render_type_table)
from components.simulation import card_label
from components.stats import TRAFFIC, lethal_level, timing_stats, traffic_level


VIEW_JS = """<script>
(function(){
  document.documentElement.classList.add('js');
  var back='';
  function show(view){
    document.querySelectorAll('.view').forEach(function(v){v.classList.toggle('on',v.id==='view-'+view);});
    document.querySelectorAll('.views a').forEach(function(a){a.classList.toggle('on',a.getAttribute('data-view')===view);});
  }
  function route(){
    var h=decodeURIComponent(location.hash.slice(1));
    var el=h?document.getElementById(h):null;
    show(h.indexOf('hiw-')===0?'help':'report');
    if(el){el.scrollIntoView({behavior:'instant',block:'start'});}else{window.scrollTo({top:0,behavior:'instant'});}
  }
  document.addEventListener('click',function(e){
    var a=e.target.closest('a.hiw');
    if(a){back=a.getAttribute('data-back')||'';}
    var b=e.target.closest('a.back');
    if(b&&b.getAttribute('href')==='#top'){e.preventDefault();location.hash=back||'top';}
  });
  window.addEventListener('hashchange',route);
  route();
})();
</script>"""

FIGHT_JS = """<script>
(function(){
  var bar=document.getElementById('fightbar');if(!bar)return;
  function $(id){return document.getElementById(id)}
  function json(url,body){return fetch(url,body?{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(body)}:undefined).then(function(r){return r.json()})}
  if(location.protocol.indexOf('http')!==0)return;  // direkt geoeffnete Datei: nur der Hinweis
  json('api/enemies').then(function(d){
    var list=d.enemies||[];
    if(!list.length){$('fbnote').textContent='Kein Gegnerdeck gefunden (Dateien _enemydeck*.txt im Projektordner).';return}
    list.forEach(function(e){var o=document.createElement('option');o.value=e.file;o.textContent=e.name;$('fbenemy').appendChild(o)});
    try{var n=localStorage.getItem('fbcount');if(n&&$('fbcount').querySelector('option[value="'+n+'"]'))$('fbcount').value=n}
    catch(e){}
    $('fbnote').style.display='none';$('fbctl').style.display='inline-flex';
    if(d.quit)$('fbquit').style.display='';
  }).catch(function(){});
  function poll(){json('api/status').then(function(s){
    if(s.state==='running'){$('fbstatus').textContent=s.message+' ('+Math.round(s.elapsed)+' s)';setTimeout(poll,1000);return}
    $('fbgo').disabled=false;
    if(s.state==='done'){location.href='battle?'+Date.now()}else{$('fbstatus').textContent=s.message}
  }).catch(function(){setTimeout(poll,1500)})}
  $('fbgo').addEventListener('click',function(){
    $('fbgo').disabled=true;$('fbstatus').textContent='Kampf startet ...';
    try{localStorage.setItem('fbcount',$('fbcount').value)}catch(e){}
    json('api/battle',{enemy:$('fbenemy').value,games:parseInt($('fbcount').value,10)}).then(function(r){
      if(!r.ok){$('fbgo').disabled=false;$('fbstatus').textContent=r.error||'Fehler';return}
      poll()});
  });
  $('fbquit').addEventListener('click',function(){json('api/quit',{}).then(function(){
    document.body.innerHTML='<p style="padding:30px">draftgott wurde beendet. Dieses Fenster kann geschlossen werden.</p>'})});
})();
</script>"""
FIGHT_BAR = ('<div class="fightbar" id="fightbar"><span id="fbnote" class="muted" title="Kampf gegen ein Gegnerdeck ist '
             'nur möglich, solange draftgott läuft (Analyse oder Drafthelper).">Kampf: nur solange draftgott läuft</span>'
             '<span id="fbctl" style="display:none;gap:8px;align-items:center">Kampf gegen '
             '<select id="fbenemy" title="Gegnerdecks im Projektordner (_enemydeck*.txt)"></select>'
             '<select id="fbcount" title="Kämpfe je Deck und Modus (On the Play und On the Draw); mehr Kämpfe sind '
             'genauer, dauern aber länger">'
             + "".join(f'<option value="{n}"' + (" selected" if n == 500 else "") + f'>{n} Kämpfe</option>'
                       for n in FIGHT_COUNTS) + '</select>'
             '<button type="button" id="fbgo">Kampf simulieren</button><span id="fbstatus" class="muted"></span>'
             '<button type="button" id="fbquit" style="display:none">Beenden</button></span></div>')

SWITCH_JS = """<script>
document.documentElement.classList.add('js');
document.querySelectorAll('.grpbar button,.gsw button').forEach(function(b){
  var t=b.textContent.trim().toLowerCase();
  if(t==='splash')b.classList.add('v-splash');else if(t==='nosplash')b.classList.add('v-nosplash');});
function showGroup(g){
  document.querySelectorAll('[data-g]').forEach(function(e){e.classList.toggle('on',e.getAttribute('data-g')===g)});
}
document.querySelectorAll('.grpbar button').forEach(function(b){b.addEventListener('click',function(){
  showGroup(b.getAttribute('data-g'));
  window.scrollTo(0,document.querySelector('.grpbar').offsetTop-60);});});
// Umschalter an jeder Ueberschrift: gleiche Stelle in der anderen Variante, Ueberschrift bleibt im Fenster stehen
document.querySelectorAll('.gsw button').forEach(function(b){b.addEventListener('click',function(){
  var g=b.getAttribute('data-g'),sec=b.getAttribute('data-sec');
  var top=b.closest('section').getBoundingClientRect().top;
  showGroup(g);
  var target=document.getElementById(g==='0'?sec:sec+'-'+g);
  if(!target){var grp=document.querySelector('.grp[data-g="'+g+'"]');target=grp&&grp.querySelector('h2.gh');top=60}
  if(target)window.scrollTo({top:window.scrollY+target.getBoundingClientRect().top-top,behavior:'instant'});});});
</script>"""


def sidebar_kpis(ctx):
    """Kernzahlen fuer die Seitenleiste (Play / Draw): Mulligan, Zauber bis zur Auswertungsrunde, schnellster Lethal,
    Durchschnittsrunde fuer den Schaden."""
    a, res = ctx["args"], ctx["results"]
    labels = list(res.keys())
    short = {"On the Play": "Play", "On the Draw": "Draw"}
    rows = []
    mu0 = res[labels[0]]["mulligan"]
    if mu0["on"]:
        rows.append(['<td class="l">Mulligan</td>'] + [
            f'<td>{h_pct(res[l]["mulligan"]["first_any"] / res[l]["mulligan"]["deals"])}</td>' for l in labels])
    t = a.turns
    rows.append([f'<td class="l">Zauber R{t}</td>'] + [
        h_level_td(traffic_level(round(res[l]["cast"][t] / a.sims * 100), l == "On the Draw", t),
                   f'{round(res[l]["cast"][t] / a.sims * 100)}%') for l in labels])
    lethal = ['<td class="l">Lethal ab</td>']
    for l in labels:
        b = res[l]["best_lethal"]
        lethal.append(h_level_td(lethal_level(b["key"][0]) if b else "red", f'R{b["key"][0]}' if b else "–"))
    rows.append(lethal)
    avg = [f'<td class="l">Ø {a.schaden} Schaden</td>']
    for l in labels:
        st = timing_stats(res[l]["dmg"], a.sims)
        avg.append(f'<td>R{st[0]:.1f}</td>' if st else '<td class="muted">–</td>')
    rows.append(avg)
    return h_table([""] + [esc(short.get(l, l)) for l in labels], rows)


CAT_LABEL = {"splashworthy": "★ Splashworthy", "mustplay": "MustPlay", "filler": "Filler", "neverplay": "NeverPlay"}


def render_great(ctx):
    """Abschnitt 'Great in this deck!': Splashworthy- und MustPlay-Karten des Decks, dazu Hinweise, was fehlt.
    Gibt '' zurueck, wenn keine Kategorien gesetzt sind (z. B. ohne Draft-Helper)."""
    cats = ctx.get("cats") or {}
    great = {n: c for n, c in cats.items() if c in ("splashworthy", "mustplay")}
    never_in_deck = sorted(n for n, c in cats.items() if c == "neverplay" and n in ctx["deck"])
    if not great and not never_in_deck:
        return ""
    order = []
    for dd in ctx.get("all_decks") or [ctx]:
        for lab, _ in dd["parts"]:
            if lab not in order:
                order.append(lab)
    lab_of = {}
    for lab, part in ctx["parts"]:
        for n in part:
            lab_of.setdefault(n, []).append(lab)
    rows_g = []
    for name, qty, card, shown in sorted((r for r in ctx["rows"] if r[0] in great),
                                         key=lambda r: (great[r[0]] != "splashworthy", r[2].is_land, r[2].mv, r[0])):
        tags = "".join(f'<span class="tag t{min(order.index(l), 2) if l in order else 0}">{esc(l)}</span> '
                       for l in lab_of.get(name, []))
        props = "".join(f'<span class="tag">{html_cost(t)}</span>' for t in re.findall(r"\[([^\]]*)\]", shown))
        rows_g.append([f'<td class="l">{esc(name)}</td>', f'<td class="l"><b>{esc(CAT_LABEL[great[name]])}</b></td>',
                       f"<td>{qty}</td>", f'<td class="l">{tags}</td>',
                       f'<td class="l">{html_cost(shown.split("   [")[0])}</td>', f'<td class="l">{props}</td>'])
    parts = []
    if rows_g:
        parts.append(h_table(["Karte", "Kategorie", "Anz.", "Bereich", "Kosten", "Eigenschaften"], rows_g,
                             left=(0, 1, 3, 4, 5)))
    else:
        parts.append('<p class="muted">Keine Splashworthy- oder MustPlay-Karten in diesem Deck.</p>')
    expected = [] if ctx.get("role") == "proposal" else [
        n for n, c in great.items() if c == "mustplay" or (c == "splashworthy" and ctx.get("role") == "splash")]
    missing = sorted(n for n in expected if n not in ctx["deck"])
    if missing:
        parts.append('<div class="warnbox" style="margin-top:12px"><b>Fehlt in diesem Deck:</b> '
                     + esc(", ".join(f"{n} ({CAT_LABEL[great[n]]})" for n in missing)) + "</div>")
    if never_in_deck:
        parts.append('<div class="warnbox" style="margin-top:12px"><b>NeverPlay-Karten im Deck:</b> '
                     + esc(", ".join(never_in_deck)) + "</div>")
    return '<div class="panel">' + "".join(parts) + "</div>"


def render_coverage(ctx):
    """Abschnitt 'Modell-Abdeckung': Karten mit Effekten, die die Simulation noch nicht abbildet (Status, grobe
    Kategorie, betroffene Kennzahl)."""
    coverage = ctx.get("coverage") or {}
    qty = {name: q for name, q, _c, _s in ctx["rows"]}
    summary = summarize(coverage, qty)
    if not summary["flagged_cards"]:
        return '<div class="panel"><p class="muted">Keine Karte mit nicht implementierten Effekten gefunden.</p></div>'
    kpis = "".join(
        f'<div class="kpi"><div class="l">{esc(m)}</div><div class="v">{summary["by_metric"][m]}</div>'
        f'<div class="s">Karten</div></div>' for m in METRIC_ORDER if summary["by_metric"][m])
    flagged = [n for n, items in coverage.items() if items]

    def order(name):
        ms = metrics_of(coverage[name])
        return (min(METRIC_ORDER.index(m) for m in ms), name)

    rows = []
    for name in sorted(flagged, key=order):
        items = coverage[name]
        cats = list(dict.fromkeys(c for c, _m, _l in items))
        metrics = [m for m in METRIC_ORDER if m in metrics_of(items)]
        evidence = " | ".join(dict.fromkeys(l for _c, _m, l in items))
        rows.append([f'<td class="l">{esc(name)}</td>', f"<td>{qty.get(name, 1)}</td>",
                     f'<td class="l"><span class="tag off">{esc(STATUS_TEXT)}</span></td>',
                     f'<td class="l" title="{esc(evidence)}">{esc(", ".join(cats))}</td>',
                     f'<td class="l">{esc(", ".join(metrics))}</td>'])
    note = (f'<div class="note" style="margin:0 0 10px"><b>{summary["flagged_cards"]} Karten</b> '
            f'({summary["flagged_copies"]} Kopien) haben Effekte, die die Simulation noch nicht abbildet. Die Zahlen in '
            'diesem Bericht berücksichtigen sie nicht.</div>')
    table = h_table(["Karte", "Anz.", "Status", "Kategorie", "Betroffene Kennzahl"], rows, left=(0, 2, 3, 4))
    return f'<div class="panel">{note}<div class="grid g4" style="margin-bottom:12px">{kpis}</div>{table}</div>'


def render_details(ctx, suffix="", switch=None):
    """Alle Detailabschnitte (Auf einen Blick ... Modellannahmen) fuer EIN Deck. Gibt (sections, nav) zurueck."""
    a, res, rows = ctx["args"], ctx["results"], ctx["rows"]
    sims, T, C, H = a.sims, a.turns, a.curve_runden, ctx["horizon"]
    labels = list(res.keys())
    sections, nav = [], []

    def add(sid, title, hint, body):
        html = h_section(sid + suffix, title, hint, body, "hiw-" + sid)
        if switch:  # Umschalter zwischen den Varianten an der Ueberschrift
            group, names = switch
            buttons = "".join(f'<button type="button" data-g="{i}" data-sec="{sid}" class="{"on" if i == group else ""}">'
                              f'{esc(n)}</button>' for i, n in enumerate(names))
            html = html.replace("</h2>", f'<span class="gsw">{buttons}</span></h2>', 1)
        sections.append(html)
        nav.append((sid + suffix, title))

    # ---------------- Auf einen Blick
    rows_v = []
    for t in range(1, T + 1):
        cells = [f'<td class="l">Zauber gespielt in Runde {t}</td>']
        for lab in labels:
            pct = round(res[lab]["cast"][t] / sims * 100)
            cells.append(h_level_td(traffic_level(pct, lab == "On the Draw", t), f"{pct}%"))
        rows_v.append(cells)
    scr = [f'<td class="l">Mana Screw nach Runde {T}</td>'] + [
        f'<td>{h_pct(res[l]["any_screw"])}</td>' for l in labels]
    fl = [f'<td class="l">Flood ({a.flood}+ Länder bis Runde {H})</td>'] + [
        f'<td>{h_pct(res[l]["flood"])}</td>' for l in labels]
    lt = [f'<td class="l">Schnellster Lethal ({a.schaden} Schaden)</td>']
    for l in labels:
        b = res[l]["best_lethal"]
        lt.append(h_level_td(lethal_level(b["key"][0]) if b else "red",
                             f'Runde {b["key"][0]}' if b else "kein Lethal"))
    avg = [f'<td class="l">Ø Runde für {a.schaden} Schaden</td>']
    for l in labels:
        st = timing_stats(res[l]["dmg"], sims)
        avg.append(f'<td>{st[0]:.1f} <span class="muted">({st[2]:.0%} der Spiele)</span></td>' if st
                   else '<td class="muted">-</td>')
    mu0 = res[labels[0]]["mulligan"]
    mull_rows = []
    if mu0["on"]:
        mull_rows = [
            ['<td class="l">Mulligan auf der ersten Hand</td>'] + [
                f'<td>{h_pct(res[l]["mulligan"]["first_any"] / res[l]["mulligan"]["deals"], 1)}</td>' for l in labels],
            [f'<td class="l">Spiel verloren (Hand unter {mu0["min_hand"]} Karten)</td>'] + [
                f'<td>{h_pct(res[l]["mulligan"]["lost"] / res[l]["mulligan"]["deals"], 1)}</td>' for l in labels],
        ]
    jace_row = []
    if any(res[l]["jace"]["on"] for l in labels):
        jace_row = [['<td class="l">Jace-Aktivierungen bis die Hand leer ist (Ø)</td>'] + [
            f'<td>{res[l]["jace"]["acts_win"] / sims:.2f}</td>' for l in labels]]
    colors_row = all_colors_row(ctx)
    rows_v = mull_rows + rows_v + jace_row + ([colors_row] if colors_row else []) + [scr, fl, avg, lt]
    body = f'<div class="panel">{h_table(["Kennzahl"] + [esc(l) for l in labels], rows_v)}</div>'
    add("blick", "Auf einen Blick", "Die wichtigsten Kennzahlen im Vergleich Play gegen Draw.", body)

    # ---------------- Deck
    cards, nonlands = ctx["cards"], [c for c in ctx["cards"] if not c.is_land]
    kpis = [
        ("Karten", str(len(cards)), f"{len(rows)} verschiedene"),
        ("Länder", str(ctx["n_lands"]), f"{ctx['n_lands'] / len(cards):.0%} des Decks"),
        ("Ø Manakosten", f"{ctx['avg_mv']:.2f}", "ohne Länder"),
        ("Farben", "".join(html_mana(c) for c in sorted(ctx["deck_colors"], key="WUBRGC".find)) or "–",
         "mehrfarbig" if ctx["multicolor"] else "einfarbig"),
    ]
    if ctx["top_mv"] is not None:
        kpis.append(("Top Card", f"{ctx['top_mv']} Mana", ", ".join(ctx["top_names"])))
    kpi_html = "".join(f'<div class="panel kpi"><div class="l">{esc(l)}</div><div class="v">{v}</div>'
                       f'<div class="s">{esc(s_)}</div></div>' for l, v, s_ in kpis)

    need = {col: sum(q for _, q, c, _ in rows if not c.is_land and col in required_colors(c)) for col in "WUBRG"}
    srcs = {col: sum(q for _, q, c, _ in rows if c.is_land and col in c.land_colors) for col in "WUBRGC"}
    spell_items = [{"name": n, "needs": needs_of_alts(c.alts), "mv": c.mv, "qty": q}
                   for n, q, c, _ in rows if not c.is_land]
    on_time = color_report(spell_items, srcs, len(cards))
    pips = {col: sum(it["qty"] * it["needs"].get(col, 0) for it in spell_items) for col in "WUBRG"}
    col_rows = []
    for col in "WUBRGC":
        if need.get(col, 0) or srcs[col]:
            ot = on_time.get(col) or {}
            worst = ot.get("worst")
            col_rows.append([f'<td class="l">{html_mana(col)}</td>', f'<td>{pips.get(col, 0)}</td>',
                             f'<td>{need.get(col, 0)}</td>',
                             f'<td>{srcs[col]}</td>',
                             h_bar_cell(srcs[col] / max(ctx["n_lands"], 1), f"{srcs[col] / max(ctx['n_lands'], 1):.0%}"),
                             h_level_td(level(ot["avg"]), f'{ot["avg"]:.0%}') if ot.get("avg") is not None
                             else '<td class="muted">–</td>',
                             f'<td class="l">{esc(worst["name"])} ({worst["p"]:.0%})</td>' if worst
                             else '<td class="muted">–</td>'])
    col_table = h_table(["Farbe", "Symbole", "Karten", "Quellen", "Anteil der Länder", "Ø pünktlich", "Am knappsten"], col_rows)

    deck_rows, origin_note, head = [], "", ["Karte", "Anz.", "Kosten", "Eigenschaften"]
    cost_tags = lambda shown: ("".join(f'<span class="tag">{html_cost(t)}</span>'
                                       for t in re.findall(r"\[([^\]]*)\]", shown)))
    if ctx["parts"] and ctx["args"].core:
        # Tabelle mit allen Dateien: je Bereich eine Zeile pro Karte, mit der Menge dieses Bereichs
        all_decks = ctx.get("all_decks") or [ctx]
        info = {n: (c, sh) for dd in all_decks for n, _, c, sh in dd["rows"]}
        base_labels = [lab for lab, _ in ctx["parts"]]
        order, seen = [], set()
        for dd in all_decks:
            for lab, d in dd["parts"]:
                if (lab, id(d)) not in seen and not any(lab == o[0] for o in order):
                    order.append((lab, d))
                seen.add((lab, id(d)))
        flat = [(n, q, lab, i) for i, (lab, d) in enumerate(order) for n, q in d.items() if n in info]
        totals = {lab: sum(d.values()) for lab, d in order}
        for n, q, lab, i in sorted(flat, key=lambda r: (info[r[0]][0].is_land, info[r[0]][0].mv, r[0], r[3])):
            card, shown = info[n]
            in_base = lab in base_labels
            tag = f'<span class="tag t{min(i, 2)}{"" if in_base else " off"}">{esc(lab)}</span>'
            deck_rows.append([f'<td class="l">{esc(n)}</td>', f"<td>{q}</td>", f'<td class="l">{tag}</td>',
                              f'<td class="l">{html_cost(shown.split("   [")[0])}</td>', f'<td class="l">{cost_tags(shown)}</td>'])
        head = ["Karte", "Anz.", "Bereich", "Kosten", "Eigenschaften"]
        origin_note = ('<div class="note" style="margin:0 0 8px">Alle Dateien: '
                       + " · ".join(f"<b>{esc(l)}</b> {totals[l]} Karten" for l, _ in order)
                       + f'. Dieses Deck besteht aus {" + ".join(esc(l) for l in base_labels)}; '
                       'blass dargestellte Bereiche gehören nur zu einer anderen Variante. Eine Karte steht mit der Menge je Bereich, '
                       'ihre Gesamtmenge im Deck ist die Summe der Bereiche des Decks.</div>')
    else:
        for name, qty, card, shown in sorted(rows, key=lambda r: (r[2].is_land, r[2].mv, r[0])):
            deck_rows.append([f'<td class="l">{esc(name)}</td>', f"<td>{qty}</td>",
                              f'<td class="l">{html_cost(shown.split("   [")[0])}</td>', f'<td class="l">{cost_tags(shown)}</td>'])
    unsure = ""
    if ctx["unsure"]:
        unsure = ('<div class="warnbox">Getappt-Bedingung nicht modelliert (als immer getappt gezählt): '
                  + esc(", ".join(ctx["unsure"])) + "</div>")
    body = (f'<div class="grid g4">{kpi_html}</div>'
            f'<div style="margin-top:14px">{render_color_curves(ctx)}</div>'
            f'<div class="grid g2" style="margin-top:14px">'
            f'{render_type_table(ctx)}'
            f'<div class="panel"><b>Farbverteilung</b>{col_table}</div></div>'
            f'<div class="panel" style="margin-top:14px">{unsure}'
            f'{origin_note}{h_table(head, deck_rows, left=(0, 2, 3, 4) if len(head) == 5 else (0, 2, 3))}</div>')
    add("deck", "Deck", "Kartendaten von Scryfall.", body)

    # ---------------- Removal (Bewertung aus dem Kartentext)
    removal_html = render_removal_table(ctx)
    if removal_html:
        add("removal", "Removal", "Wie viel Removal hat das Deck? Bewertung je Karte aus dem Kartentext.", removal_html)

    # ---------------- Friedhof (Score aus dem Kartentext und Messung in der Simulation)
    gy_html = render_graveyard_table(ctx)
    if gy_html or ctx.get("gy_x_names"):
        sim_rows = []
        for l in labels:
            g_ = res[l]["graveyard"]
            turns = sorted(g_["size"])
            sim_rows.append([h_mode(l), '<td class="l">Ø Karten im Friedhof</td>']
                            + [f'<td>{g_["size"][t]:.1f}</td>' for t in turns])
            sim_rows.append([h_mode(l), '<td class="l">Ø höchster Manawert im Friedhof</td>']
                            + [f'<td>{g_["max_mv"][t]:.1f}</td>' for t in turns])
        turns = sorted(res[labels[0]]["graveyard"]["size"])
        sim_html = ('<div class="panel" style="margin-top:14px"><b>Simulation</b>'
                    + h_table(["", "Kennzahl"] + [f"nach Runde {t}" for t in turns], sim_rows, left=(0, 1)))
        if ctx.get("gy_x_names"):
            hp = []
            for l in labels:
                g_ = res[l]["graveyard"]
                hp.append([h_mode(l), f'<td>{g_["hapatra_x_avg"]:.1f}</td>', f'<td>{h_pct(g_["x_ge3"])}</td>',
                           f'<td>{h_pct(g_["x_ge5"])}</td>', f'<td>{g_["hapatra_n"]}</td>'])
            sim_html += (f'<div style="margin-top:10px"><b class="muted">{esc(", ".join(ctx["gy_x_names"]))}: X = '
                         f'höchster Manawert im Friedhof beim Betreten</b>'
                         + h_table(["", "Ø X", "X ≥ 3", "X ≥ 5", "gewirkt (Anzahl)"], hp) + '</div>')
        sim_html += '</div>'
        add("friedhof", "Friedhof", "Wie stark nutzt das Deck den Friedhof, und was liegt in der Simulation darin?",
            gy_html + sim_html)

    # ---------------- Great in this deck! (Kategorien aus dem Draft-Helper)
    great_html = render_great(ctx)
    if great_html:
        add("great", "Great in this deck!",
            "Als Splashworthy oder MustPlay gekennzeichnete Karten dieses Decks (Draft-Helper).", great_html)

    # ---------------- Modell-Abdeckung (Karten mit Effekten, die noch nicht simuliert werden)
    if ctx.get("coverage") is not None:
        add("abdeckung", "Modell-Abdeckung",
            "Welche Karten dieses Decks Effekte haben, die die Simulation noch nicht abbildet.", render_coverage(ctx))

    # ---------------- Mulligan
    if mu0["on"]:
        mh = mu0["min_hand"]
        sizes = list(range(7, mh - 1, -1))
        rows_m = []
        for l in labels:
            mu = res[l]["mulligan"]
            d = mu["deals"]
            cls = LABEL_CLASS.get(l, "")
            rows_m.append([h_mode(l)] + [h_bar_cell(mu["sizes"][k] / d, h_pct(mu["sizes"][k] / d, 1), cls) for k in sizes]
                           + [h_bar_cell(mu["lost"] / d, h_pct(mu["lost"] / d, 1), cls),
                              f'<td>{sims} / {mu["lost"]}</td>'])
        heads = [""] + [f"{k} Karten" for k in sizes] + [f"Verloren (< {mh})", "Gespielt / verloren"]
        reasons = [(MULL_COLORS, "Farben passen nicht"), (MULL_LANDS_HIGH, "6+ Länder"),
                   (MULL_LANDS_LOW, "≤ 2 Länder, < 3 spielbar")]
        rows_r = []
        for l in labels:
            mu = res[l]["mulligan"]
            d = mu["deals"]
            rows_r.append([h_mode(l), f'<td><b>{h_pct(mu["first_any"] / d, 1)}</b></td>']
                          + [f'<td>{h_pct(mu["first"][key] / d, 1)}</td>' for key, _ in reasons])
        body = (
            '<div class="panel"><b>Erste 7-Karten-Hand: Gründe für einen Mulligan</b>'
            + h_table(["", "Mulligan gesamt"] + [r for _, r in reasons], rows_r) + '</div>'
            '<div class="panel" style="margin-top:14px"><b>Mit wie vielen Karten startet das Spiel?</b> '
            '<span class="muted">(Behalten mit … Karten)</span>' + h_table(heads, rows_m) + '</div>')
        add("mulligan", "Mulligan", "Wie oft die Starthand getauscht werden muss und wie oft das Spiel dadurch verloren geht.", body)

    if ctx["jace"]["any"]:
        add("jace", "Jace & Planeswalker", "Karten mit Empower Jace oder anderen Planeswalker-Bezügen und deren Wirkung in der Simulation.",
            render_jace_section(ctx))

    # ---------------- Zauber pro Runde
    rows_c = []
    for lab in labels:
        r = res[lab]
        cells = [h_mode(lab)]
        for t in range(1, T + 1):
            pct = round(r["cast"][t] / sims * 100)
            cells.append(h_level_td(traffic_level(pct, lab == "On the Draw", t), f"{pct}%"))
        cells.append(f'<td>{r["opener_lands"]:.2f}</td>')
        rows_c.append(cells)
    body = (f'<div class="panel">{h_table([""] + [f"Runde {t}" for t in range(1, T + 1)] + ["Ø Länder in Starthand (nach Mulligan)"], rows_c)}'
'</div>')
    add("zauber", "Zauber pro Runde", f"{sims} Simulationen pro Modus.", body)

    # ---------------- Kreaturen
    rows_k = [[h_mode(l), f'<td>{res[l]["creatures"]:.2f}</td>', f'<td>{res[l]["power"]:.2f}</td>',
               f'<td>{res[l]["toughness"]:.2f}</td>'] for l in labels]
    body = (f'<div class="panel">{h_table(["", "Kreaturen", "Gesamt-Power", "Gesamt-Toughness"], rows_k)}'
'</div>')
    add("kreaturen", f"Kreaturen nach Runde {T}", "", body)

    # ---------------- Screw & Flood
    rows_s = []
    for l in labels:
        r = res[l]
        cls = LABEL_CLASS.get(l, "")
        rows_s.append([h_mode(l), h_bar_cell(r["land_screw"], cls=cls),
                       h_bar_cell(r["color_screw"], cls=cls) if ctx["multicolor"] else '<td class="muted">–</td>',
                       h_bar_cell(r["any_screw"], cls=cls)])
    rows_f = [[h_mode(l), h_bar_cell(res[l]["flood"], cls=LABEL_CLASS.get(l, "")),
               f'<td>{res[l]["lands_drawn"]:.1f}</td>'] for l in labels]
    body = (f'<div class="grid"><div class="panel"><b>Mana Screw nach Runde {T}</b>'

            f'{h_table(["", "Zu wenig Länder", "Farben fehlen", "Gesamt"], rows_s)}</div>'
            f'<div class="panel"><b>Flood ({a.flood}+ Länder bis Runde {H})</b>'
            f'{h_table(["", "Flooded", "Ø Länder gezogen"], rows_f)}</div></div>')
    add("screw", "Mana Screw & Flood", "", body)

    # ---------------- Farbverfuegbarkeit
    avail = render_color_availability(ctx)
    if avail:
        add("farben", "Farbverfügbarkeit",
            "Wie oft liegen bis Runde 3 alle Farben, und wie oft genug Quellen für Mehrfach-Symbole (z. B. WW, GGGG) "
            "bis zur Runde, in der die günstigste solche Karte spielbar wäre?", avail)

    # ---------------- Splash-Karten (nur Splash-Variante aus dem Drafthelper)
    if ctx.get("splash_track"):
        info = {n: (c, sh) for n, _, c, sh in rows}
        trs = []
        for name, model in ctx["splash_track"]:
            card, shown = info[name]
            for i, l in enumerate(labels):
                s_ = res[l].get("splash_cards", {}).get(model)
                if not s_:
                    continue
                drawn = s_["drawn"]
                first = (f'<td class="l" rowspan="{len(labels)}"><b>{esc(name)}</b> '
                         f'{html_cost(shown.split("   [")[0])}</td>') if i == 0 else ""
                cells = ([first] if first else []) + [h_mode(l), f'<td>{h_pct(drawn / s_["games"])}</td>']
                if drawn:
                    ok = s_["castable"] / drawn
                    cells += [h_level_td(avail_level(round(ok * 100)), f"{ok:.0%}"),
                              f'<td>{s_["on_time"] / drawn:.0%}</td>',
                              f'<td>{s_["wait_sum"] / s_["castable"]:.1f}</td>' if s_["castable"]
                              else '<td class="muted">–</td>',
                              f'<td>{s_["cast"] / drawn:.0%}</td>']
                else:
                    cells += ['<td class="muted">–</td>'] * 4
                trs.append(cells)
        body = ('<div class="panel">'
                + h_table(["Karte", "", "Gezogen", "Spielbar", "Pünktlich", "Ø Wartezeit", "Gewirkt"], trs,
                          left=(0, 1))
                + '<div class="note">Gezogen: Anteil aller Spiele. Die übrigen Spalten beziehen sich auf die Spiele, in '
                  'denen die Karte auf die Hand kam: Spielbar, wenn gezogen · Pünktlich (bis Runde = Manawert) · '
                  'Ø Wartezeit in Runden bis erstmals bezahlbar · Gewirkt, wenn gezogen.</div></div>')
        add("splashkarten", "Splash-Karten",
            "Wie oft werden die Karten der Splash-Gruppe spielbar, wenn man sie zieht?", body)

    # ---------------- Curve-Auslastung
    panels = []
    for l in labels:
        cv = res[l]["curve"]
        tot_a, tot_s = sum(cv["avail"].values()), sum(cv["spent"].values())
        tot_g, tot_f = sum(cv["games"].values()), sum(cv["full"].values())
        ts = range(1, C + 1)
        ratio = lambda t: cv["spent"][t] / cv["avail"][t] if cv["avail"][t] else 0
        full = lambda t: cv["full"][t] / cv["games"][t] if cv["games"][t] else 0
        rws = [
            [f'<td class="l">Ø Mana verfügbar</td>'] + [f'<td>{cv["avail"][t] / sims:.2f}</td>' for t in ts]
            + [f'<td><b>{tot_a / sims / C:.2f}</b></td>'],
            [f'<td class="l">Ø Mana ausgegeben</td>'] + [f'<td>{cv["spent"][t] / sims:.2f}</td>' for t in ts]
            + [f'<td><b>{tot_s / sims / C:.2f}</b></td>'],
            [f'<td class="l">Auslastung</td>'] + [f'<td>{h_pct(ratio(t))}</td>' for t in ts]
            + [f'<td><b>{h_pct(tot_s / tot_a if tot_a else 0)}</b></td>'],
            [f'<td class="l">Alles Mana genutzt</td>'] + [f'<td>{h_pct(full(t))}</td>' for t in ts]
            + [f'<td><b>{h_pct(tot_f / tot_g if tot_g else 0)}</b></td>'],
        ]
        panels.append(f'<div class="panel"><b>{esc(l)}</b>'
                      f'{h_table([""] + [f"Runde {t}" for t in ts] + ["Gesamt"], rws)}</div>')
    util = {l: [(res[l]["curve"]["spent"][t] / res[l]["curve"]["avail"][t]) if res[l]["curve"]["avail"][t] else 0
                for t in range(1, C + 1)] for l in labels}
    chart = (f'<div class="panel" style="margin-top:14px"><b>Auslastung je Runde</b>{h_legend(labels)}'
             f'{svg_bars([f"R{t}" for t in range(1, C + 1)], util, 1.0, lambda v: f"{v:.0%}")}'
'</div>')
    add("curve", "Curve-Auslastung", f"Runde 1–{C}: wie gut wird das Mana genutzt?",
        f'<div class="grid">{"".join(panels)}</div>{chart}')


    # ---------------- Schaden & Lethal
    rows_d = []
    for l in labels:
        st = timing_stats(res[l]["dmg"], sims)
        rows_d.append([h_mode(l)] + ([f"<td>{st[0]:.1f}</td>", f"<td>{st[1]:.1f}</td>", h_bar_cell(st[2], cls=LABEL_CLASS.get(l, ""))] if st
                                     else ['<td class="muted">–</td>'] * 2 + [h_bar_cell(0)]))
    xs = list(range(1, H + 1))
    cum = {l: [sum(1 for v in res[l]["dmg"] if v <= t) / sims for t in xs] for l in labels}
    chart = (f'<div class="panel"><b>Wahrscheinlichkeit, bis Runde X mindestens {a.schaden} Schaden verursacht zu haben</b>'
             f'{h_legend(labels)}{svg_lines(xs, cum)}</div>')
    effect_note = ""
    if any(res[l]["effects"]["face"] or res[l]["effects"]["counters"] for l in labels):
        effect_note = ('<div class="note">Pro Spiel aus Karten: '
                       + " · ".join(f'{esc(l)}: Ø {res[l]["effects"]["face"]:.1f} Schaden an den Gegner, '
                                    f'Ø {res[l]["effects"]["counters"]:.1f} +1/+1-Marken' for l in labels)
                       + '</div>')
    table = (f'<div class="panel"><b>Erste Runde mit {a.schaden} Schaden</b>'
             f'{h_table(["", "Ø Runde", "Median", "Eintritt"], rows_d)}{effect_note}</div>')
    add("schaden", "Schaden durch Kreaturen", "", f'<div class="grid g2">{table}{chart}</div>')

    lethals = []
    for l in labels:
        b = res[l]["best_lethal"]
        if not b:
            lethals.append(f'<div class="panel lethal"><div class="head"><b>{esc(l)}</b>'
                           f'{h_level_pill("red", "kein Lethal")}</div></div>')
            continue
        turn, neg = b["key"]
        hand = "".join(f'<span class="card {"land" if c.is_land else ""}">{esc(c.name)}</span>'
                       for c in sorted(b["opening"], key=lambda c: (c.is_land, c.mv, c.name)))
        trs = []
        for t, drew, land, tapped, cast, tdmg, total, cycled, jinfo in b["log"]:
            land_txt = "–" if land is None else esc(land.name) + (' <span class="tag">getappt</span>' if tapped else "")
            cast_txt = ", ".join(esc(card_label(c)) for c in cast) or "–"
            cyc_txt = "".join(f'<span class="tag">Landcycling: {esc(c.name)}</span>' for c, _ in cycled)
            if jinfo[0]:
                cyc_txt += f'<span class="tag">Jace +{jinfo[0]} → {jinfo[2]} Loyalty</span>'
            if jinfo[1]:
                cyc_txt += '<span class="tag">Jace aktiviert (+1 Karte)</span>'
            if len(jinfo) > 3 and jinfo[3]:
                cyc_txt += f'<span class="tag">Draw-Zauber: +{jinfo[3]} Karte{"n" if jinfo[3] > 1 else ""}</span>'
            trs.append([f'<td class="l">Runde {t}</td>', f'<td class="l">{esc(drew.name) if drew else "–"}</td>',
                        f'<td class="l">{land_txt}</td>', f'<td class="l">{cast_txt} {cyc_txt}</td>',
                        f'<td class="dmg">+{tdmg}</td>',
                        h_bar_cell(min(total / a.schaden, 1), f"{total}", LABEL_CLASS.get(l, ""))])
        lethals.append(
            f'<div class="panel lethal"><div class="head"><span class="dot {LABEL_CLASS.get(l, "")}"></span>'
            f'<b>{esc(l)}</b>{h_level_pill(lethal_level(turn), f"Runde {turn}")}'
            f'<span class="muted">{-neg} Schaden</span>'
            + (f'<span class="tag">Mulligan: Starthand mit {len(b["opening"])} Karten</span>' if b.get("mulls") else "")
            + '</div>'
            f'<div class="muted" style="font-size:12.5px">Starthand</div><div class="hand">{hand}</div>'
            f'{h_table(["", "Zieht", "Land", "Zauber", "Schaden", "Gesamt"], trs, "class=tl", left=(0, 1, 2, 3))}</div>')
    add("lethal", "Schnellster Lethal",
        f"Das schnellste von {sims} simulierten Spielen (bei gleicher Runde das mit mehr Schaden) – "
        f"ein Glücksfall, kein Erwartungswert.", f'<div class="grid">{"".join(lethals)}</div>')


    # ---------------- Landcycling
    if ctx["cyc_names"] and not a.ohne_landcycling:
        panels = []
        for l in labels:
            lc = res[l]["landcycle"]
            ev = lc["events"]
            if not ev:
                panels.append(f'<div class="panel"><b>{esc(l)}</b><p class="muted">in {sims} Simulationen nie nötig oder möglich</p></div>')
                continue
            pb, pa = lc["p_before"] / ev, lc["p_after"] / ev
            first = sum(lc["first"]) / len(lc["first"])
            reasons = "".join(f'<tr><td class="l">{esc(k)}</td>{h_bar_cell(v / ev, cls=LABEL_CLASS.get(l, ""))}</tr>'
                              for k, v in lc["reason"].most_common())
            cards_ = "".join(f'<tr><td class="l">{esc(n)}</td><td>{v}×</td>{h_bar_cell(v / ev, cls=LABEL_CLASS.get(l, ""))}</tr>'
                             for n, v in lc["card"].most_common())
            panels.append(
                f'<div class="panel"><b>{esc(l)}</b>'
                f'<div class="grid g4" style="margin:10px 0">'
                f'<div class="kpi"><div class="l">Spiele mit Cycling</div><div class="v">{h_pct(lc["games"] / sims)}</div></div>'
                f'<div class="kpi"><div class="l">Ø pro Spiel</div><div class="v">{ev / sims:.2f}</div></div>'
                f'<div class="kpi"><div class="l">Erstmals Ø in</div><div class="v">Runde {first:.1f}</div></div>'
                f'<div class="kpi"><div class="l">Nicht-Land-Chance</div><div class="v">+{(pa - pb) * 100:.1f} PP</div>'
                f'<div class="s">{pb:.1%} → {pa:.1%} (relativ +{(pa / pb - 1) if pb else 0:.1%})</div></div></div>'
                f'<div class="grid g2"><div><b class="muted">Grund</b><table>{reasons}</table></div>'
                f'<div><b class="muted">Meistgenutzte Karte</b><table>{cards_}</table></div></div></div>')
        add("landcycling", "Landcycling", "Karten im Deck: " + esc(", ".join(ctx["cyc_names"])),
            f'<div class="grid">{"".join(panels)}</div>')

    # ---------------- Draw-Zauber
    if ctx.get("draw_names"):
        panels = []
        for l in labels:
            d = res[l]["draws"]
            panels.append(
                f'<div class="panel"><b>{esc(l)}</b><div class="grid g4" style="margin:10px 0">'
                f'<div class="kpi"><div class="l">Spiele mit Draw-Zauber</div><div class="v">{h_pct(d["games"])}</div></div>'
                f'<div class="kpi"><div class="l">Ø zusätzlich gezogen</div><div class="v">{d["cards"]:.2f}</div>'
                f'<div class="s">Karten pro Spiel bis Runde {H}</div></div>'
                f'<div class="kpi"><div class="l">Ø gleich genutzt</div><div class="v">{d["used"]:.2f}</div>'
                f'<div class="s">Länder und Zauber im selben Zug</div></div></div></div>')
        add("ziehen", "Draw-Zauber", "Karten im Deck: " + esc(", ".join(ctx["draw_names"])),
            f'<div class="grid">{"".join(panels)}</div>')

    # ---------------- Surveil durch Karten
    if ctx.get("surveil_names"):
        panels = []
        for l in labels:
            s_ = res[l]["card_surveil"]
            panels.append(
                f'<div class="panel"><b>{esc(l)}</b><div class="grid g4" style="margin:10px 0">'
                f'<div class="kpi"><div class="l">Spiele mit Surveil</div><div class="v">{h_pct(s_["games"])}</div></div>'
                f'<div class="kpi"><div class="l">Ø Surveils</div><div class="v">{s_["events"]:.2f}</div>'
                f'<div class="s">pro Spiel bis Runde {H}</div></div>'
                f'<div class="kpi"><div class="l">Ø Länder in den Friedhof</div><div class="v">{s_["lands"]:.2f}</div>'
                f'<div class="s">pro Spiel</div></div></div></div>')
        add("surveil", "Surveil durch Karten", "Karten im Deck: " + esc(", ".join(ctx["surveil_names"])),
            f'<div class="grid">{"".join(panels)}</div>')

    # ---------------- Prepared
    if ctx.get("prepared_names"):
        panels = []
        for l in labels:
            p_ = res[l]["prepared"]
            panels.append(
                f'<div class="panel"><b>{esc(l)}</b><div class="grid g4" style="margin:10px 0">'
                f'<div class="kpi"><div class="l">Spiele mit Kopie</div><div class="v">{h_pct(p_["games"])}</div></div>'
                f'<div class="kpi"><div class="l">Ø Kopien</div><div class="v">{p_["copies"]:.2f}</div>'
                f'<div class="s">pro Spiel bis Runde {H}</div></div>'
                f'<div class="kpi"><div class="l">Ø Mana für Kopien</div><div class="v">{p_["mana"]:.2f}</div>'
                f'<div class="s">pro Spiel</div></div></div></div>')
        add("prepared", "Prepared", "Karten im Deck: " + esc(", ".join(ctx["prepared_names"])),
            f'<div class="grid">{"".join(panels)}</div>')

    # ---------------- Ramp (Mana ausser Laendern)
    if ctx.get("ramp_names"):
        panels = []
        for l in labels:
            rp_ = res[l]["ramp"]
            first = f'Runde {rp_["first_avg"]:.1f}' if rp_["first_avg"] is not None else "–"
            kpi = (f'<div class="kpi"><div class="l">Spiele mit Ramp</div><div class="v">{h_pct(rp_["games"])}</div>'
                   f'<div class="s">mehr Mana als Länder</div></div>'
                   f'<div class="kpi"><div class="l">Erstmals Ø in</div><div class="v">{first}</div></div>'
                   f'<div class="kpi"><div class="l">Ø Angriffe ausgelassen</div><div class="v">{rp_["held_back"]:.2f}</div>'
                   f'<div class="s">Kreatur für Mana getappt</div></div>')
            if rp_["treasure_made"]:
                kpi += (f'<div class="kpi"><div class="l">Treasure Ø</div>'
                        f'<div class="v">{rp_["treasure_used"]:.2f} / {rp_["treasure_made"]:.2f}</div>'
                        f'<div class="s">genutzt / erzeugt pro Spiel</div></div>')
            turns = sorted(rp_["extra"])
            table = h_table(["Runde"] + [str(t) for t in turns],
                            [['<td class="l">Ø zusätzliches Mana</td>'] + [f'<td>{rp_["extra"][t]:.2f}</td>' for t in turns]])
            panels.append(f'<div class="panel"><b>{esc(l)}</b><div class="grid g4" style="margin:10px 0">{kpi}</div>'
                          f'{table}</div>')
        add("ramp", "Ramp", "Mana außer Ländern – Karten im Deck: " + esc(", ".join(ctx["ramp_names"])),
            f'<div class="grid">{"".join(panels)}</div>')

    # ---------------- Tempo
    rows_t = []
    for l in labels:
        r = res[l]
        for title, key in (("Hand komplett leer", "empty_hand"), ("Keine Zauber mehr auf der Hand", "empty_spells"),
                           ("Top Card spielbar", "top")):
            if key == "top" and ctx["top_mv"] is None:
                continue
            st = timing_stats(r[key], sims)
            rows_t.append([h_mode(l), f'<td class="l">{esc(title)}</td>'] +
                          ([f"<td>{st[0]:.1f}</td>", f"<td>{st[1]:.1f}</td>", h_bar_cell(st[2], cls=LABEL_CLASS.get(l, ""))] if st
                           else ['<td class="muted">–</td>'] * 2 + [h_bar_cell(0)]))
    body = (f'<div class="panel">{h_table(["", "Ereignis", "Ø Runde", "Median", "Eintritt"], rows_t, left=(0, 1))}'
            + (f'<div class="note">Top Card: {esc(", ".join(ctx["top_names"]))} (Manawert {ctx["top_mv"]}).</div>' if ctx["top_mv"] is not None else "")
            + '</div>')
    add("tempo", "Tempo", "", body)


    return sections, nav


def render_html(ctx):
    symbols.reset_used()  # Symbole, die diese Seite zeigt, werden eingebettet
    a, res = ctx["args"], ctx["results"]
    sims, T, H = a.sims, a.turns, ctx["horizon"]
    mu0 = res[list(res.keys())[0]]["mulligan"]
    decks = [ctx] + [dict(d, args=a, horizon=ctx["horizon"], jace=analyze_jace(d["rows"]), alts=[],
                          all_decks=ctx["all_decks"]) for d in ctx.get("alts", [])]
    multi = len(decks) > 1
    sections, nav_parts = [], []
    if multi:
        cmp_body = h_section("vergleich", "Deck-Vergleich",
                             f"Hauptdeck gegen {len(ctx['alts'])} Alternative(n), mit statistischer Einordnung der Unterschiede.",
                             render_compare_section(ctx), "hiw-vergleich")
        sections.append(cmp_body)
        cmp_nav = [("vergleich", "Deck-Vergleich")]
        btns = "".join(f'<button type="button" data-g="{i}" class="{"on" if i == 0 else ""}">{esc(d["name"])}</button>'
                       for i, d in enumerate(decks))
        sections.append(f'<div class="grpbar"><b>Details für:</b> {btns}</div>')
        for i, d in enumerate(decks):
            sec, nv = render_details(d, "" if i == 0 else f"-{i}", switch=(i, [x["name"] for x in decks]))
            sections.append(f'<div class="grp{" on" if i == 0 else ""}" data-g="{i}">'
                            f'<h2 class="gh">Details: {esc(d["name"])}</h2>{"".join(sec)}</div>')
            nav_parts.append(f'<div class="in grpnav{" on" if i == 0 else ""}" data-g="{i}">'
                             + "".join(f'<a href="#{k}">{esc(t)}</a>' for k, t in cmp_nav + nv) + "</div>")
        nav_html = "".join(nav_parts)
    else:
        sec, nv = render_details(ctx)
        sections += sec
        nav_html = '<div class="in">' + "".join(f'<a href="#{k}">{esc(t)}</a>' for k, t in nv) + "</div>"

    present = {re.sub(r"-\d+$", "", sid) for sid in re.findall(r'<section id="([^"]+)"', "".join(sections))}
    chips = ([f"Vergleich mit {len(ctx['alts'])} Alternative(n)"] if ctx.get("alts") else []) + (
        [f"Seed {a.seed}"] if a.seed is not None else []) + [f"{sims} gespielte Spiele pro Modus", "Mulligan an" if mu0["on"] else "ohne Mulligan", f"Auswertung Runde {T}", f"Beobachtung bis Runde {H}",
             f"{a.schaden} Schaden", f"Flood ab {a.flood} Ländern"]
    missing_html = ('<div class="warnbox" style="margin-top:14px"><b>Nicht bei Scryfall gefunden (nicht simuliert):</b> '
                    + esc(", ".join(ctx["missing"])) + "</div>") if ctx.get("missing") else ""
    stamp = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    help_html = render_help_view(present=present)
    if multi:
        kpi_html = "".join(f'<div class="sidekpi grpkpi{" on" if i == 0 else ""}" data-g="{i}">'
                           f'<div class="kvar">{esc(d["name"])}</div>{sidebar_kpis(d)}</div>'
                           for i, d in enumerate(decks))
    else:
        kpi_html = f'<div class="sidekpi">{sidebar_kpis(ctx)}</div>'
    side_html = (f'<h3>Kernzahlen</h3>{kpi_html}<div class="navsep"></div><h3>Abschnitte</h3>{nav_html}'
                 f'<div class="navsep"></div><h3>Einstellungen</h3>'
                 f'<div class="chips">{"".join(f"<span class=chip>{esc(c)}</span>" for c in chips)}</div>')
    css = HTML_CSS + symbols.symbol_css(symbols.used())
    return (f'<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(ctx["name"])} – MTG Simulation</title><style>{css}</style></head><body>'
            f'<header class="top" id="top"><h1>{esc(ctx["name"])}</h1>'
            f'<span class="sub">Starthand-Simulation · erstellt am {stamp}</span>'
            '<div class="views"><a href="#top" data-view="report" class="on">Bericht</a>'
            '<a href="#hiw-start" data-view="help">So funktioniert es</a></div>' + FIGHT_BAR + '</header>'
            f'<div class="view on" id="view-report"><div class="layout"><nav>{side_html}</nav>'
            f'<main>{missing_html}{"".join(sections)}</main></div></div>'
            f'{help_html}'
            f'<footer>Erzeugt mit mtg_sim.py · Kartendaten von Scryfall</footer>'
            + LAYOUT_JS + (SWITCH_JS if multi else "") + VIEW_JS + FIGHT_JS + '</body></html>')
