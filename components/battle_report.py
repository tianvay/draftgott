"""Kampfbericht: eigene HTML-Seite fuer die Kaempfe gegen ein Gegnerdeck (Uebersicht und Protokolle).

render_battle_html(decks, args): decks wie im Goldfish (build_deck), jeweils mit "battles" (mtg_sim.simulate_battles).
Inhalt: Uebersicht (Siege/Niederlagen je Deck und Modus), je Deck der schnellste Sieg und die schnellste Niederlage als
Zugprotokoll beider Spieler, Regeln des Kampfs. Bei mehreren Decks (Splash/NoSplash) Umschalter an jeder Ueberschrift.
"""
import datetime

from components.html_base import HTML_CSS, LABEL_CLASS, esc, h_bar_cell, h_mode, h_section, h_table

MODES = ("On the Play", "On the Draw")

RULES = [
    "Beide Spieler starten mit 20 Lebenspunkten und sind abwechselnd dran. Ein Zug: Untap, Draw (entfällt im "
    "allerersten Zug), Main 1, Kampf, Main 2, End Phase. Bei „On the Play“ beginnen wir, bei „On the Draw“ der Gegner.",
    "Mulligan wie im Goldfish. Fällt unsere Hand unter die Mindestzahl, geben wir auf (Niederlage durch Mulligan). Der "
    "Gegner gibt nie auf: Er behält dann seine Hand mit der Mindestzahl an Karten.",
    "Gespielt wird mit derselben Auswahl wie im Goldfish. Main 1: das Land und alle Zauber außer Kreaturen ohne Haste; "
    "Main 2: Kreaturen ohne Haste.",
    "<b>Angriff:</b> Alles greift an, wenn selbst bei bestem Blocken genug Schaden für Lethal durchkommt. Sonst greift "
    "eine Kreatur an, solange kein ungetappter Blocker sie tötet und dabei überlebt (ein Tausch ist in Ordnung). Wäre "
    "sonst der Gegenangriff im nächsten Zug Lethal, bleiben die schwächsten Angreifer zu Hause.",
    "<b>Block:</b> Ein Blocker, der den Angreifer tötet und überlebt; sonst ein Tausch, wenn der Angreifer mindestens so "
    "viel Manawert hat; sonst ein Doppel-Block, bei dem einer der Blocker überlebt. Chump-Blocks nur gegen Lethal.",
    "<b>Schaden:</b> First Strike zuerst, Double Strike in beiden Schritten, Deathtouch (1 Schaden reicht, auch mit "
    "Trample), Trample, Lifelink. Flying kann nur von Flying oder Reach geblockt werden, Menace nur von zwei Kreaturen. "
    "Getappte Kreaturen greifen nicht an und blocken nicht (auch nicht, wenn sie für Mana getappt wurden); Vigilance "
    "tappt beim Angriff nicht.",
    "Beide Seiten spielen nach denselben Regeln und kennen die Handkarten des anderen nicht. Gestorbene Kreaturen kommen "
    "in den Friedhof; „damage to each player“ trifft auch den Spieler selbst.",
    "Spielende: 0 Lebenspunkte, Ziehen aus leerer Bibliothek oder Aufgabe durch Mulligan. Nach der Rundengrenze "
    "(<code>--kampf-runden</code>, Standard 20 eigene Züge) ist es unentschieden.",
    "Noch nicht im Kampf: Removal auf Kreaturen, Kampftricks, Flash und Instants im Zug des Gegners, Jace, Prepared, "
    "Landcycling, Surveil und Treasure. Solche Karten werden gewirkt, wirken aber nur mit den schon modellierten Effekten.",
]

CSS = """
.proto td{vertical-align:top;font-size:13px}
.proto tr.p-Wir td:first-child,.proto tr.p-Wir td:nth-child(2){border-left:3px solid var(--play)}
.proto tr.p-Gegner td:first-child,.proto tr.p-Gegner td:nth-child(2){border-left:3px solid var(--draw)}
.proto .dead{color:var(--bad);font-weight:600}
.proto .small{font-size:12px;color:var(--muted)}
.hands{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px;margin:8px 0 12px}
"""


def _avg(xs):
    return f"{sum(xs) / len(xs):.1f}" if xs else "–"


def _fastest(results, key):
    """(Spiel, Modus) mit der kleinsten Runde ueber beide Modi oder (None, None)."""
    best = None
    for mode in MODES:
        g = results[mode][key]
        if g and (best is None or g["round"] < best[0]["round"]):
            best = (g, mode)
    return best or (None, None)


def _attacks_html(attacks):
    out = []
    for at in attacks:
        att = esc(at["attacker"]) + (' <span class="dead">†</span>' if at["attacker_dies"] else "")
        if not at["blockers"]:
            out.append(f"{att} → ungeblockt")
        else:
            bl = ", ".join(esc(b) + (' <span class="dead">†</span>' if d else "")
                           for b, d in zip(at["blockers"], at["blockers_die"]))
            out.append(f"{att} ✕ {bl}")
    return "<br>".join(out) or "–"


def _protocol(game, mode, title):
    """Zugprotokoll eines Spiels."""
    hands = "".join(
        f'<div class="panel"><b>Starthand {esc(who)}</b>'
        f'{" <span class=small>(" + str(game["mulligans"][who]) + " Mulligan)</span>" if game["mulligans"][who] else ""}'
        f'<div class="small" style="margin-top:4px">{esc(", ".join(game["opening"][who]))}</div></div>'
        for who in ("Wir", "Gegner"))
    rows = []
    for e in game["log"]:
        life = e.get("life") or {}
        board = e.get("board") or {}
        dmg = str(e["damage"]) + (f' + {e["face"]} direkt' if e["face"] else "")
        cls = f'p-{e["player"]}'
        cells = [f'<td>{e["round"]}</td>', f'<td class="l"><b>{esc(e["player"])}</b></td>',
                 f'<td class="l">{esc(e["drew"] or "–")}</td>', f'<td class="l">{esc(e["land"] or "–")}</td>',
                 f'<td class="l">{esc(", ".join(e["main1"]) or "–")}</td>',
                 f'<td class="l">{_attacks_html(e["attacks"])}</td>',
                 f'<td class="l">{esc(", ".join(e["main2"]) or "–")}</td>',
                 f'<td>{dmg}</td>',
                 f'<td>{life.get("Wir", "–")} / {life.get("Gegner", "–")}</td>',
                 f'<td class="l small">Wir: {esc(", ".join(board.get("Wir", [])) or "–")}<br>'
                 f'Gegner: {esc(", ".join(board.get("Gegner", [])) or "–")}'
                 + (f'<br><b>{esc(e["note"])}</b>' if e.get("note") else "") + '</td>']
        rows.append(f'<tr class="{cls}">' + "".join(cells) + "</tr>")
    head = "".join(f'<th class="{"l" if i in (1, 2, 3, 4, 5, 6, 9) else ""}">{h}</th>' for i, h in enumerate(
        ["Runde", "Spieler", "Zieht", "Land", "Main 1", "Kampf († = stirbt)", "Main 2", "Schaden", "Leben Wir / Gegner",
         "Feld danach"]))
    return (f'<div class="note" style="margin:0 0 6px"><b>{esc(title)}</b> in Runde {game["round"]} '
            f'({esc(mode)})</div><div class="hands">{hands}</div>'
            f'<div class="panel"><div class="tw"><table class="proto"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div></div>')


SWITCH_JS = """<script>
document.documentElement.classList.add('js');
function showGroup(g){
  document.querySelectorAll('[data-g]').forEach(function(e){e.classList.toggle('on',e.getAttribute('data-g')===g)});
}
document.querySelectorAll('.gsw button').forEach(function(b){b.addEventListener('click',function(){
  var g=b.getAttribute('data-g'),sec=b.getAttribute('data-sec');
  var top=b.closest('section').getBoundingClientRect().top;
  showGroup(g);
  var target=document.getElementById(g==='0'?sec:sec+'-'+g);
  if(target)window.scrollTo({top:window.scrollY+target.getBoundingClientRect().top-top,behavior:'instant'});});});
</script>"""


def render_battle_html(decks, args):
    enemies = []
    for dd in decks:
        for b in dd.get("battles") or []:
            if b["enemy"] not in enemies:
                enemies.append(b["enemy"])
    title = "Kampf gegen " + ", ".join(enemies)
    multi = len(decks) > 1
    names = [d["name"] for d in decks]

    # Uebersicht
    rows = []
    for dd in decks:
        for b in dd.get("battles") or []:
            for mode in MODES:
                r = b["results"][mode]
                n = r["games"] or 1
                rows.append([f'<td class="l"><b>{esc(dd["name"])}</b></td>', f'<td class="l">{esc(b["enemy"])}</td>',
                             h_mode(mode), h_bar_cell(r["wins"] / n, f'{r["wins"] / n:.0%}', LABEL_CLASS.get(mode, "")),
                             f'<td>{r["losses"] / n:.0%}</td>', f'<td>{r["draws"] / n:.0%}</td>',
                             f'<td>{_avg(r["win_rounds"])}</td>', f'<td>{_avg(r["loss_rounds"])}</td>',
                             f'<td>{r["mull_losses"]}</td>'])
    games = next((b["results"][MODES[0]]["games"] for dd in decks for b in dd.get("battles") or []), 0)
    overview = ('<div class="panel">' + h_table(["Deck", "Gegner", "", "Siege", "Niederlagen", "Unentschieden",
                                                 "Ø Runde Sieg", "Ø Runde Niederlage", "Aufgabe (Mulligan)"],
                                                rows, left=(0, 1, 2))
                + f'<div class="note">{games} Spiele je Deck und Modus. Runde = Zahl der eigenen Züge. „Aufgabe '
                  f'(Mulligan)“: Spiele, die wir verloren haben, weil unsere Hand unter die Mindestzahl fiel; sie zählen '
                  f'als Niederlage, aber nicht bei den Runden.</div></div>')
    sections = [h_section("uebersicht", "Übersicht", "Wie oft gewinnen wir?", overview)]
    nav = [("uebersicht", "Übersicht")]

    # Protokolle je Deck
    groups, navs = [], []
    for i, dd in enumerate(decks):
        suffix = "" if i == 0 else f"-{i}"
        secs, nv = [], []
        for e_idx, b in enumerate(dd.get("battles") or []):
            for key, sid, label in (("fastest_win", "sieg", "Schnellster Sieg"),
                                    ("fastest_loss", "niederlage", "Schnellste Niederlage")):
                base = sid if e_idx == 0 else f"{sid}{e_idx}"
                game, mode = _fastest(b["results"], key)
                body = (_protocol(game, mode, label) if game else
                        f'<div class="panel"><p class="muted">In keinem Spiel gegen {esc(b["enemy"])} '
                        f'({"kein Sieg" if key == "fastest_win" else "keine Niederlage"}).</p></div>')
                html = h_section(base + suffix, f'{label} gegen {b["enemy"]}', "", body)
                if multi:
                    buttons = "".join(f'<button type="button" data-g="{k}" data-sec="{base}" '
                                      f'class="{"on" if k == i else ""}">{esc(n)}</button>' for k, n in enumerate(names))
                    html = html.replace("</h2>", f'<span class="gsw">{buttons}</span></h2>', 1)
                secs.append(html)
                nv.append((base + suffix, f"{label} ({b['enemy']})"))
        if multi:
            groups.append(f'<div class="grp{" on" if i == 0 else ""}" data-g="{i}">'
                          f'<h2 class="gh">Protokolle: {esc(dd["name"])}</h2>{"".join(secs)}</div>')
            navs.append(f'<div class="in grpnav{" on" if i == 0 else ""}" data-g="{i}">'
                        + "".join(f'<a href="#{k}">{esc(t)}</a>' for k, t in nav + nv) + "</div>")
        else:
            groups += secs
            nav += nv
    rules = h_section("regeln", "So funktioniert der Kampf", "",
                      '<div class="panel"><ul class="ass">' + "".join(f"<li>{r}</li>" for r in RULES) + "</ul></div>")
    if multi:
        nav_html = "".join(navs)
    else:
        nav_html = '<div class="in">' + "".join(f'<a href="#{k}">{esc(t)}</a>' for k, t in nav) + "</div>"
    nav_html += '<div class="in"><a href="#regeln">So funktioniert der Kampf</a></div>'
    stamp = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    chips = [f"{games} Spiele je Modus", f"Rundengrenze {getattr(args, 'kampf_runden', 20)}",
             "Varianten: " + ", ".join(names)] + ([f"Seed {args.seed}"] if getattr(args, "seed", None) is not None else [])
    return (f'<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)} – MTG Simulation</title><style>{HTML_CSS}{CSS}</style></head><body>'
            f'<header class="top" id="top"><h1>{esc(title)}</h1>'
            f'<div class="sub">Kampf-Simulation · erstellt am {stamp}</div>'
            f'<div class="chips">{"".join(f"<span class=chip>{esc(c)}</span>" for c in chips)}</div>'
            '<a id="backlink" href="report" style="display:none;margin-top:10px">← Zurück zum Bericht</a></header>'
            f'<div class="layout"><nav>{nav_html}</nav><main>{"".join(sections)}{"".join(groups)}{rules}</main></div>'
            f'<footer>Erzeugt mit mtg_sim.py · Kartendaten von Scryfall</footer>'
            + (SWITCH_JS if multi else "")
            + "<script>if(location.protocol.indexOf('http')===0)document.getElementById('backlink').style.display="
              "'inline-block'</script></body></html>")
