"""Kampfbericht: eigene HTML-Seite fuer die Kaempfe gegen ein Gegnerdeck (Uebersicht und Protokolle).

render_battle_html(decks, args): decks wie im Goldfish (build_deck), jeweils mit "battles" (mtg_sim.simulate_battles).
Inhalt: Uebersicht (Siege/Niederlagen je Deck und Modus), je Deck der schnellste Sieg und die schnellste Niederlage als
Zugprotokoll beider Spieler, Regeln des Kampfs. Bei mehreren Decks (Splash/NoSplash) Umschalter an jeder Ueberschrift.
"""
import datetime

from components.battle import _end_life, _max_gap
from components.html_base import HTML_CSS, LABEL_CLASS, esc, h_bar_cell, h_mode, h_section, h_table, svg_lines

MODES = ("On the Play", "On the Draw")

RULES = [
    "Beide Spieler starten mit 20 Lebenspunkten und sind abwechselnd dran. Ein Zug: Untap, Draw (entfällt im "
    "allerersten Zug), Main 1, Kampf, Main 2, End Phase. Bei „On the Play“ beginnen wir, bei „On the Draw“ der Gegner.",
    "Mulligan wie im Goldfish. Fällt unsere Hand unter die Mindestzahl, geben wir auf (Niederlage durch Mulligan). Der "
    "Gegner gibt nie auf: Er behält dann seine Hand mit der Mindestzahl an Karten.",
    "Gespielt wird mit derselben Auswahl wie im Goldfish, in den Main Phases aber nur Sorcery-Speed (Permanents, "
    "Sorceries, Sorcery-Removal mit gültigem Ziel). Main 1: das Land und alle Zauber außer Kreaturen ohne Haste; Main 2: "
    "Kreaturen ohne Haste. Übriges Mana bleibt offen für Instants und Flash, auch im Zug des Gegners.",
    "<b>Removal</b> trifft die gefährlichste passende Kreatur (höchste Power, dann Flying/Trample/Deathtouch, dann "
    "Manawert): Destroy/Exile, Schaden und −X/−X nur, wenn sie tötet, Edikt (der Gegner opfert seine schwächste "
    "Kreatur, bei „greatest mana value“ die teuerste), Fight, Bounce (zurück auf die Hand), Lock-Aura (greift nicht an, "
    "blockt nicht), Massenremoval (alle Kreaturen). Removal-Instants: vor dem eigenen Angriff gegen einen Blocker, der "
    "einen Angreifer fressen würde; im Zug des Gegners gegen den gefährlichsten Angreifer; sonst am Ende des "
    "gegnerischen Zugs.",
    "<b>„Any target“-Schaden</b> trifft die gefährlichste Kreatur, die er tötet (nur Kreaturen mit Power über 0); ist "
    "Schaden am Gegner tödlich oder gibt es keine solche Kreatur, geht er an den Gegner.",
    "<b>Kampftricks</b> (Instants und Flash-Karten mit Pump oder Marken) nach den Blockern, wenn danach eine eigene "
    "Kreatur überlebt, eine gegnerische stirbt oder es Lethal ist. <b>Flash-Kreaturen</b> blocken, wenn das einen "
    "guten Block ergibt oder Lethal verhindert, sonst kommen sie am Ende des gegnerischen Zugs. <b>Sonstige "
    "Instants</b> (z. B. Ziehen) am Ende des gegnerischen Zugs.",
    "<b>Abwerfen</b> (z. B. Rank Rat): ein überzähliges Land (Feld + Hand reichen für die teuerste Handkarte), sonst "
    "die günstigste Karte.",
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
    "Surveil durch Karten und Länder wie im Goldfish (Land bleibt oben, solange Länder für die teuerste Handkarte "
    "fehlen). Prepared: Die Kopie ist wie eine Handkarte nur in der eigenen Main Phase spielbar; Upkeep-Karten werden "
    "zu Beginn des Zugs wieder prepared.",
    "Treasure: im eigenen Zug nur, wenn er mehr Zauber ermöglicht; im Zug des Gegners für Instants und Flash nur, wenn "
    "das offene Mana nicht reicht.",
    "Jace (Empower): Loyalty aus Zaubern, Betreten, Auslösern und Fähigkeiten (siehe unten). Zu Beginn des Zugs ab 3 "
    "Loyalty −3: Karte ziehen; nach Main 2 ab 3 ziehen, sonst −1: Surveil 1. Jace wird nicht angegriffen.",
    "Fähigkeiten mit Kosten (nur Mana und {T}): „Activate only as a sorcery“ nur in der eigenen Main Phase, „only "
    "during your turn“ nur im eigenen Zug, sonst jederzeit. Freies Mana: Mana, nach dessen Einsatz jede bezahlbare "
    "Instant-, Flash- oder Landcycling-Karte der Hand bezahlbar bleibt.",
    "Pumps und verliehene Schlüsselwörter bis Rundenende: als Angreifer nach den Blockern bei Lethal (auch mit Treasure), "
    "sonst mit freiem Mana, wenn der Kampf besser wird (mehr Schaden, Kreatur überlebt, Blocker stirbt); Flying und "
    "Menace schon vor dem Angriff, wenn dadurch mehr durchkommt. Als Verteidiger vor und nach den Blockern, wenn der "
    "Block besser wird (z. B. Reach gegen einen Flieger).",
    "+1/+1-Marken und Empower durch Fähigkeiten: im eigenen Zug vor dem Angriff mit freiem Mana, sonst mit dem Rest am "
    "Ende des gegnerischen Zugs (nach Instants, Flash und Landcycling, ohne Treasure); Marken vor Empower, auf die "
    "stärkste passende Kreatur.",
    "Landcycling: Fehlt bis Runde 3 im eigenen Zug ein Land für den Landdrop, wird sofort gecycelt. Sonst am Ende des "
    "gegnerischen Zugs mit dem offenen Mana, das Instants und Flash übrig lassen (bis 6 Länder auf Feld und Hand, nicht "
    "die letzte Handkarte, nicht wenn die Karte nächste Runde spielbar ist).",
    "Weitere Auslöser: Kampfschaden am Spieler zieht Karten (Frostbite Pyromental), Opfern zu Beginn des Endsegments, "
    "Leben und Marken, wenn eigene Kreaturen ins Spiel kommen (Greenhouse Propagator, Mabel: auf die stärkste Kreatur, "
    "die in diesem Zug kam), Team-Pump nach Artefakten (Craterclaw Colossus), Kostensenkung für Nichtkreatur-Zauber "
    "(Geist of Saint Thalia), Marken bei Zaubern mit Ziel beim Gegner (Danitha), Empower X beim Angriff "
    "(X = eigene Kreaturen).",
    "Fähigkeiten mit Sonderkosten: „Discard this card“ als Removal von der Hand wie ein Instant (Sureshot Sower, kein "
    "Zauber); „Exile this card from your graveyard“ wie Marken und Empower (Campus Crier). Surveil-Fähigkeiten am Ende "
    "des gegnerischen Zugs; im eigenen Zug nur, wenn eine Kreatur dadurch trotz Defender angreifen darf "
    "(Surveillance Phantasm, auch nach Surveil durch Karten oder Jace).",
    "Noch nicht im Kampf: Token (Tenured Tethermage, Vraska), Mill und Länder aus dem Friedhof (Primal Witchstalker), "
    "Enlightened Confidant, Null Summoner, Fähigkeiten mit Opfern als Kosten und weitere Auslöser. Solche Karten werden "
    "gewirkt, wirken aber nur mit den schon modellierten Effekten.",
]

CSS = """
.proto td{vertical-align:top;font-size:13px}
.proto tr.p-Wir td:first-child,.proto tr.p-Wir td:nth-child(2){border-left:3px solid var(--play)}
.proto tr.p-Gegner td:first-child,.proto tr.p-Gegner td:nth-child(2){border-left:3px solid var(--draw)}
.proto .dead{color:var(--bad);font-weight:600}
.proto .small{font-size:12px;color:var(--muted)}
.gfilter{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:8px;font-size:13px}
.gfilter select{font:inherit;padding:3px 8px;border-radius:8px;border:1px solid var(--line);background:var(--panel);color:var(--text)}
.glist{max-height:340px;overflow:auto}
.glist tr.game{cursor:pointer}
.glist tr.game:hover td{background:var(--chip)}
.glist tr.game.sel td{background:var(--chip);font-weight:600}
.res-win{color:var(--good);font-weight:600}.res-loss{color:var(--bad);font-weight:600}
.mull{color:var(--bad);font-weight:700}
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
                 f'<td class="l small">{"<br>".join(esc(x) for x in e.get("events", [])) or "–"}</td>',
                 f'<td>{dmg}</td>',
                 f'<td>{life.get("Wir", "–")} / {life.get("Gegner", "–")}</td>',
                 f'<td class="l small">Wir: {esc(", ".join(board.get("Wir", [])) or "–")}<br>'
                 f'Gegner: {esc(", ".join(board.get("Gegner", [])) or "–")}'
                 + (f'<br><b>{esc(e["note"])}</b>' if e.get("note") else "") + '</td>']
        rows.append(f'<tr class="{cls}">' + "".join(cells) + "</tr>")
    head = "".join(f'<th class="{"l" if i in (1, 2, 3, 4, 5, 6, 7, 10) else ""}">{h}</th>' for i, h in enumerate(
        ["Runde", "Spieler", "Zieht", "Land", "Main 1", "Kampf († = stirbt)", "Main 2",
         "Removal, Instants, Flash", "Schaden", "Leben Wir / Gegner", "Feld danach"]))
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


MULL_WARN = 0.05  # Hinweis, wenn mehr als 5 % der Spiele durch Mulligan-Aufgabe verloren gehen

SPECIALS = [  # (Schluessel, Abschnitt, Titel, Auswahl ueber beide Modi)
    ("fastest_win", "sieg", "Schnellster Sieg", lambda g: g["round"]),
    ("fastest_loss", "niederlage", "Schnellste Niederlage", lambda g: g["round"]),
    ("closest_win", "knapp-sieg", "Knappster Sieg", lambda g: (_end_life(g, "Wir"), g["round"])),
    ("closest_loss", "knapp-niederlage", "Knappste Niederlage", lambda g: (_end_life(g, "Gegner"), -g["round"])),
    ("comeback_win", "gedreht-sieg", "Gedrehter Sieg", lambda g: (-_max_gap(g, "Wir"), g["round"])),
    ("comeback_loss", "gedreht-niederlage", "Gedrehte Niederlage", lambda g: (-_max_gap(g, "Gegner"), g["round"])),
]
SPECIAL_NOTE = {
    "closest_win": "Sieg mit den wenigsten eigenen Lebenspunkten am Ende",
    "closest_loss": "Niederlage, bei der der Gegner am Ende die wenigsten Lebenspunkte hatte",
    "comeback_win": "Sieg nach dem größten Rückstand an Lebenspunkten",
    "comeback_loss": "Niederlage nach dem größten Vorsprung an Lebenspunkten",
}
MODE_KEY = {"On the Play": "play", "On the Draw": "draw"}

GAMES_JS = """<script>
(function(){
  var served=location.protocol.indexOf('http')===0;
  document.querySelectorAll('.gamesbox').forEach(function(box){
    var view=box.querySelector('.gameview');
    function filter(){
      var m=box.querySelector('.fmode').value,r=box.querySelector('.fres').value;
      box.querySelectorAll('tr.game').forEach(function(tr){
        var ok=(m===''||tr.getAttribute('data-m')===m)&&(r===''||tr.getAttribute('data-r')===r);
        tr.style.display=ok?'':'none'});
    }
    box.querySelector('.fmode').addEventListener('change',filter);
    box.querySelector('.fres').addEventListener('change',filter);
    box.querySelectorAll('tr.game').forEach(function(tr){tr.addEventListener('click',function(){
      box.querySelectorAll('tr.game.sel').forEach(function(x){x.classList.remove('sel')});tr.classList.add('sel');
      if(!served){view.innerHTML='<p class="muted">Das Protokoll einzelner Spiele gibt es nur, solange draftgott läuft '+
        '(Drafthelper oder Analyse). Die besonderen Spiele stehen oben.</p>';return}
      view.innerHTML='<p class="muted">Lade Protokoll …</p>';
      fetch('game?d='+tr.getAttribute('data-d')+'&e='+tr.getAttribute('data-e')+'&m='+tr.getAttribute('data-m')+
        '&n='+tr.getAttribute('data-n')).then(function(r){return r.text()}).then(function(h){view.innerHTML=h;
        view.scrollIntoView({block:'nearest'})}).catch(function(){view.innerHTML='<p class="muted">Fehler beim Laden.</p>'});
    })});
  });
})();
</script>"""


def protocol_html(game, mode, title):
    """Protokoll eines einzelnen Spiels (fuer die Spieleliste auf Abruf)."""
    return _protocol(game, mode, title)


def _pct(n, d):
    return f"{n / d:.0%}" if d else "–"


def _overview(decks):
    rows, warnings = [], []
    for dd in decks:
        for b in dd.get("battles") or []:
            for mode in MODES:
                r = b["results"][mode]
                n = r["games"] or 1
                played = n - r["mull_losses"]
                mull = (f'<td class="bad">{r["mull_losses"]} ({_pct(r["mull_losses"], n)})</td>'
                        if r["mull_losses"] else '<td class="muted">0</td>')
                rows.append([f'<td class="l"><b>{esc(dd["name"])}</b></td>', f'<td class="l">{esc(b["enemy"])}</td>',
                             h_mode(mode), h_bar_cell(r["wins"] / n, f'{r["wins"] / n:.0%}', LABEL_CLASS.get(mode, "")),
                             f'<td>{r["losses"] / n:.0%}</td>', mull, f'<td>{r["draws"] / n:.0%}</td>',
                             f'<td>{_pct(r["wins"], played)}</td>',
                             f'<td>{_avg(r["win_rounds"])}</td>', f'<td>{_avg(r["loss_rounds"])}</td>'])
                if r["mull_losses"] / n > MULL_WARN:
                    warnings.append(f'{esc(dd["name"])} ({esc(mode)}): {r["mull_losses"]} von {n} Spielen '
                                    f'({r["mull_losses"] / n:.0%}) geben wir schon beim Mulligan auf')
    games = next((b["results"][MODES[0]]["games"] for dd in decks for b in dd.get("battles") or []), 0)
    warn = ('<div class="warnbox"><b>Mulligan-Aufgaben:</b> ' + "; ".join(warnings) + '. Die Hand fiel dabei unter '
            'die Mindestzahl an Karten (<code>--min-handkarten</code>).</div>') if warnings else ""
    return (warn + '<div class="panel">' + h_table(
        ["Deck", "Gegner", "", "Siege", "Niederlagen", "davon durch Mulligan", "Unentschieden",
         "Siege ohne Mulligan-Aufgaben", "Ø Runde Sieg", "Ø Runde Niederlage"], rows, left=(0, 1, 2))
        + f'<div class="note">{games} Spiele je Deck und Modus. Runde = Zahl der eigenen Züge. „davon durch Mulligan“: '
          f'Niederlagen, weil unsere Hand unter die Mindestzahl fiel (der Gegner gibt nie auf). „Siege ohne '
          f'Mulligan-Aufgaben“: Siege unter den Spielen, die wirklich gespielt wurden. Mulligan-Aufgaben zählen nicht '
          f'bei Runden, Kennzahlen und besonderen Spielen.</div></div>')


def _verlauf(b):
    res = b["results"]
    rounds = max([max(r["win_by_round"], default=0) for r in res.values()] + [6])
    xs = list(range(1, rounds + 1))
    cum = {}
    for mode in MODES:
        r = res[mode]
        total, acc, vals = r["games"] or 1, 0, []
        for t in xs:
            acc += r["win_by_round"].get(t, 0)
            vals.append(acc / total)
        cum[mode] = vals
    charts = [f'<div class="panel"><b>Siege bis Runde N</b> <span class="muted">(Anteil aller Spiele)</span>'
              f'{svg_lines(xs, cum)}</div>']
    for mode in MODES:
        curve = res[mode]["life_curve"]
        n = len(curve["Wir"])
        if not n:
            charts.append(f'<div class="panel"><b>Lebenspunkte {esc(mode)}</b><p class="muted">keine Spiele</p></div>')
            continue
        top = max(20, max(curve["Wir"] + curve["Gegner"]))
        charts.append(f'<div class="panel"><b>Lebenspunkte je Runde – {esc(mode)}</b> '
                      f'<span class="muted">(Ø über alle gespielten Spiele, nach Spielende der letzte Stand)</span>'
                      + svg_lines(list(range(1, n + 1)), curve, ymax=top, fmt=lambda v: f"{v:.0f}",
                                  classes={"Wir": "play", "Gegner": "draw"})
                      + '<div class="legend"><span><span class="dot play"></span>Wir</span>'
                        '<span><span class="dot draw"></span>Gegner</span></div></div>')
    rows = []
    for mode in MODES:
        r = res[mode]
        rows.append([h_mode(mode), f'<td>{_avg(r["end_life_win"])}</td>', f'<td>{_avg(r["end_life_loss"])}</td>',
                     f'<td>{r["combat_damage"]["Wir"]:.1f} / {r["combat_damage"]["Gegner"]:.1f}</td>',
                     f'<td>{r["direct_damage"]["Wir"]:.1f} / {r["direct_damage"]["Gegner"]:.1f}</td>',
                     f'<td>{r["deaths"]["Wir"]:.1f} / {r["deaths"]["Gegner"]:.1f}</td>'])
    table = ('<div class="panel"><b>Kennzahlen je Spiel</b>' + h_table(
        ["", "Ø Leben am Ende (Sieg, unsere)", "Ø Leben am Ende (Niederlage, Gegner)", "Ø Kampfschaden Wir / Gegner",
         "Ø direkter Schaden Wir / Gegner", "Ø gestorbene Kreaturen Wir / Gegner"], rows)
             + '<div class="note">Direkter Schaden: Burn, Landfall, „any target“ an den Gegner. Ohne Spiele, die durch '
               'Mulligan entschieden wurden.</div></div>')
    return f'<div class="grid g2">{"".join(charts)}</div>{table}'


def _games_list(d_idx, e_idx, b):
    rows = []
    for mode in MODES:
        for g in b["results"][mode]["games_list"]:
            if g["mulligan_loss"]:
                res, cls, rkey = "Aufgabe (Mulligan)", "mull", "mull"
            elif g["winner"] == "a":
                res, cls, rkey = "Sieg", "res-win", "win"
            elif g["winner"] == "b":
                res, cls, rkey = "Niederlage", "res-loss", "loss"
            else:
                res, cls, rkey = "Unentschieden", "muted", "draw"
            mull = f'{g["mulligans"]["Wir"]} / {g["mulligans"]["Gegner"]}'
            rows.append(f'<tr class="game" data-d="{d_idx}" data-e="{e_idx}" data-m="{MODE_KEY[mode]}" '
                        f'data-n="{g["n"]}" data-r="{rkey}"><td>{g["n"] + 1}</td>{h_mode(mode)}'
                        f'<td class="l {cls}">{res}</td><td>{g["round"] or "–"}</td>'
                        f'<td>{g["life"]["Wir"]} / {g["life"]["Gegner"]}</td><td>{mull}</td></tr>')
    head = "".join(f'<th class="{"l" if i == 2 else ""}">{h}</th>' for i, h in enumerate(
        ["Nr.", "Modus", "Ergebnis", "Runde", "Leben Wir / Gegner", "Mulligans Wir / Gegner"]))
    filters = ('<div class="gfilter">Modus <select class="fmode"><option value="">alle</option>'
               '<option value="play">On the Play</option><option value="draw">On the Draw</option></select>'
               'Ergebnis <select class="fres"><option value="">alle</option><option value="win">Siege</option>'
               '<option value="loss">Niederlagen</option><option value="mull">Aufgabe (Mulligan)</option>'
               '<option value="draw">Unentschieden</option></select>'
               '<span class="muted">Klick auf ein Spiel zeigt sein Protokoll (solange draftgott läuft).</span></div>')
    return (f'<div class="panel gamesbox">{filters}<div class="glist tw"><table><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div><div class="gameview" id="gameview"></div></div>')


def render_battle_html(decks, args):
    enemies = []
    for dd in decks:
        for b in dd.get("battles") or []:
            if b["enemy"] not in enemies:
                enemies.append(b["enemy"])
    title = "Kampf gegen " + ", ".join(enemies)
    multi = len(decks) > 1
    names = [d["name"] for d in decks]
    games = next((b["results"][MODES[0]]["games"] for dd in decks for b in dd.get("battles") or []), 0)
    sections = [h_section("uebersicht", "Übersicht", "Wie oft gewinnen wir?", _overview(decks))]
    nav = [("uebersicht", "Übersicht")]

    groups, navs = [], []
    for i, dd in enumerate(decks):
        suffix = "" if i == 0 else f"-{i}"
        secs, nv = [], []

        def add(base, heading, body, hint=""):
            html = h_section(base + suffix, heading, hint, body)
            if multi:
                buttons = "".join(f'<button type="button" data-g="{k}" data-sec="{base}" '
                                  f'class="{"on" if k == i else ""}">{esc(n)}</button>' for k, n in enumerate(names))
                html = html.replace("</h2>", f'<span class="gsw">{buttons}</span></h2>', 1)
            secs.append(html)
            nv.append((base + suffix, heading))

        for e_idx, b in enumerate(dd.get("battles") or []):
            tag = "" if e_idx == 0 else str(e_idx)
            vs = f" gegen {b['enemy']}" if len(enemies) > 1 else ""
            add("verlauf" + tag, "Verlauf und Kennzahlen" + vs, _verlauf(b))
            for key, sid, label, order in SPECIALS:
                cands = [(b["results"][m][key], m) for m in MODES if b["results"][m].get(key)]
                if cands:
                    game, mode = min(cands, key=lambda gm: order(gm[0]))
                    body = _protocol(game, mode, label)
                else:
                    body = (f'<div class="panel"><p class="muted">In keinem Spiel gegen {esc(b["enemy"])} '
                            f'({"kein Sieg" if "win" in key else "keine Niederlage"}).</p></div>')
                add(sid + tag, label + vs, body, SPECIAL_NOTE.get(key, ""))
            add("spiele" + tag, "Alle Spiele" + vs, _games_list(i, e_idx, b))
        if multi:
            groups.append(f'<div class="grp{" on" if i == 0 else ""}" data-g="{i}">'
                          f'<h2 class="gh">Details: {esc(dd["name"])}</h2>{"".join(secs)}</div>')
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
            + (SWITCH_JS if multi else "") + GAMES_JS
            + "<script>if(location.protocol.indexOf('http')===0)document.getElementById('backlink').style.display="
              "'inline-block'</script></body></html>")
