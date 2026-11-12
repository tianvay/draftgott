"""Setauswertung (--setauswertung [SET], Menue 4 in draftgott.bat): die gesammelte Draft-Statistik eines Sets
(draftstatistik.json, components/draftstats.py) als HTML-Seite setauswertung_<set>.html.

Abschnitte: Ueberblick, Archetypen (erkannt wie im Live-Draft aus Hauptdeck bzw. Picks), beste und schwaechste
Karten, alle Karten (Tabelle, nach jeder Spalte sortierbar), eigene Bewertung gegen Ergebnis, Liste der Drafts.
Siegquoten aus weniger als MIN_GAMES Games sind grau: dafuer ist die Zahl der Spiele zu klein.
"""
import pathlib
import sys
import urllib.error
import webbrowser

from components import archetypes as set_archetypes
from components import cardarchetypes
from components import draftstats as ds
from components import ratings as card_ratings
from components import symbols
from components.html_base import HTML_CSS, esc, h_section, h_table, html_cost
from components.scryfall import fetch_cards_cached

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = SCRIPT_DIR
MIN_GAMES = 20  # darunter gilt eine Siegquote nur als Hinweis
TOP_GAMES = 10  # Mindestzahl Games fuer "beste und schwaechste Karten"
CAT_LABEL = {"splashworthy": "★ Splashworthy", "mustplay": "MustPlay", "filler": "Filler", "neverplay": "NeverPlay",
             "": "ohne Kategorie"}
RARITY = {"common": "C", "uncommon": "U", "rare": "R", "mythic": "M"}
CSS = """
.few{color:var(--muted);font-style:italic}
table.sort td:first-child{white-space:nowrap}
table.sort th{cursor:pointer;user-select:none}
table.sort th:hover{color:var(--accent)}
.kpis{display:flex;flex-wrap:wrap;gap:12px;margin:6px 0 4px}
.kpi{background:#fff;border:1px solid var(--line);border-radius:10px;padding:8px 14px;min-width:150px}
.kpi b{display:block;font-size:20px}
.kpi span{color:var(--muted);font-size:12.5px}
"""
SORT_JS = """<script>
document.querySelectorAll("table.sort").forEach(t=>{t.querySelectorAll("th").forEach((th,i)=>{th.title="Sortieren";
 th.onclick=()=>{const b=t.tBodies[0],rows=[...b.rows],up=th.dataset.dir!=="down";
  t.querySelectorAll("th").forEach(x=>delete x.dataset.dir);th.dataset.dir=up?"down":"up";
  const v=r=>{const c=r.cells[i],s=c.dataset.v!==undefined?c.dataset.v:c.textContent.trim();const n=parseFloat(s);
   return isNaN(n)?s.toLowerCase():n};
  rows.sort((a,b)=>{const x=v(a),y=v(b);return (x<y?-1:x>y?1:0)*(up?-1:1)});rows.forEach(r=>b.appendChild(r))}})});
</script>"""


def output_name(code):
    return f"setauswertung_{code.lower()}.html"


def _pct(wins, games):
    return f"{round(100 * wins / games)} %" if games else "–"


def _rate_td(wins, games):
    if not games:
        return '<td data-v="-1">–</td>'
    cls = ' class="few" title="Weniger als %d Games: nur ein Hinweis"' % MIN_GAMES if games < MIN_GAMES else ""
    return f'<td data-v="{wins / games:.4f}"{cls}>{_pct(wins, games)}</td>'


def _colors(cards):
    out = {}
    for name, sc in cards.items():
        faces = sc.get("card_faces") or []
        out[name] = sc.get("colors") or (faces[0].get("colors") if faces else None) or []
    return out


def _kpi(value, label):
    return f'<div class="kpi"><b>{esc(value)}</b><span>{esc(label)}</span></div>'


def _overview(data, code):
    s = ds.summary(data, code)
    drafts = s["drafts"]
    losses, glosses = s["matches"] - s["match_wins"], s["games"] - s["wins"]
    kpis = (_kpi(f"{drafts} Draft{'s' if drafts != 1 else ''}", "mitgelesen")
            + _kpi(f"{s['match_wins']}-{losses}", f"Matches, {_pct(s['match_wins'], s['matches'])} gewonnen")
            + _kpi(f"{s['wins']}-{glosses}", f"Games, {_pct(s['wins'], s['games'])} gewonnen")
            + _kpi(f"{s['match_wins'] / drafts:.1f}".replace(".", ",") if drafts else "–", "Siege je Draft"))
    return f'<div class="kpis">{kpis}</div>'


def _archetypes(records, code, colors, assign, ratings):
    found = set_archetypes.for_set(code) or []
    rows, by = [], {}
    for rec in records:
        key = ds.record_archetype(rec, colors, assign, ratings) or ""
        b = by.setdefault(key, {"drafts": 0, "matches": 0, "mw": 0, "games": 0, "gw": 0})
        b["drafts"] += 1
        for m in rec.get("matches") or []:
            if m.get("win") is None:
                continue
            b["matches"] += 1
            b["mw"] += 1 if m["win"] else 0
            b["games"] += len(m["games"])
            b["gw"] += sum(1 for g in m["games"] if g)
    names = {a["colors"]: a["name"] for a in found}
    for key in sorted(by, key=lambda k: (-by[k]["drafts"], k)):
        b = by[key]
        label = (f'{html_cost("".join("{" + c + "}" for c in key))} {esc(names.get(key, key))}' if key
                 else "noch offen (kein Archetyp erkannt)")
        rows.append([f'<td class="l">{label}</td>', f'<td>{b["drafts"]}</td>',
                     f'<td>{b["mw"]}-{b["matches"] - b["mw"]}</td>', _rate_td(b["mw"], b["matches"]),
                     _rate_td(b["gw"], b["games"])])
    if not rows:
        return '<p class="hint">Keine Drafts.</p>'
    return h_table(["Archetyp", "Drafts", "Matches", "Matches gewonnen", "Games gewonnen"], rows, 'class="sort"')


def _card_rows(stats, cards, assign, ratings, arch_names):
    rows = []
    for name, st in sorted(stats.items(), key=lambda kv: (-kv[1]["games"], -kv[1]["drafted"], kv[0])):
        sc = cards.get(name) or {}
        faces = sc.get("card_faces") or []
        cost = sc.get("mana_cost") or (faces[0].get("mana_cost") if faces else "") or ""
        cat = ratings.get(name, "")
        arch = ", ".join(arch_names.get(a, a) for a in assign.get(name, []))
        avg = st["avg_pick"]
        rows.append([f'<td class="l">{esc(name)}</td>', f'<td class="l">{html_cost(cost)}</td>',
                     f'<td>{esc(RARITY.get(sc.get("rarity"), ""))}</td>',
                     f'<td class="l">{esc(CAT_LABEL[cat]) if cat else ""}</td>', f'<td class="l">{esc(arch)}</td>',
                     f'<td>{st["drafted"]}</td>',
                     f'<td data-v="{avg if avg is not None else 99}">{str(avg).replace(".", ",") if avg else "–"}</td>',
                     f'<td>{st["decks"]}</td>', f'<td>{st["games"]}</td>', _rate_td(st["wins"], st["games"]),
                     f'<td data-v="{st["match_wins"]}">{st["match_wins"]}-{st["matches"] - st["match_wins"]}</td>'])
    return rows


CARD_HEAD = ["Karte", "Kosten", "Selt.", "Kategorie", "Archetypen", "Gedraftet", "Ø Pick", "Im Deck", "Games",
             "Games gewonnen", "Matches"]


def _best(stats, cards, assign, ratings, arch_names):
    enough = {n: s for n, s in stats.items() if s["games"] >= TOP_GAMES}
    if not enough:
        return f'<p class="hint">Noch keine Karte mit mindestens {TOP_GAMES} Games im Deck.</p>'
    order = sorted(enough, key=lambda n: (-enough[n]["wins"] / enough[n]["games"], -enough[n]["games"]))
    top = {n: enough[n] for n in order[:5]}
    low = {n: enough[n] for n in order[::-1][:5] if n not in top}
    out = "<h3>Am stärksten</h3>" + h_table(CARD_HEAD, _card_rows(top, cards, assign, ratings, arch_names),
                                             'class="sort"', left=(0, 1, 3, 4))
    if low:
        out += "<h3>Am schwächsten</h3>" + h_table(CARD_HEAD, _card_rows(low, cards, assign, ratings, arch_names),
                                                    'class="sort"', left=(0, 1, 3, 4))
    return out


def _ratings_vs_results(stats, ratings):
    rows = []
    for cat in ("splashworthy", "mustplay", "filler", "neverplay", ""):
        names = [n for n in stats if ratings.get(n, "") == cat]
        played = [n for n in names if stats[n]["games"]]
        games = sum(stats[n]["games"] for n in names)
        wins = sum(stats[n]["wins"] for n in names)
        rows.append([f'<td class="l">{esc(CAT_LABEL[cat])}</td>', f'<td>{len(names)}</td>', f'<td>{len(played)}</td>',
                     f'<td>{games}</td>', _rate_td(wins, games)])
    return h_table(["Kategorie", "Karten", "davon gespielt", "Games (je Karte gezählt)", "Games gewonnen"], rows)


def _drafts(records, colors, assign, ratings, arch_names):
    rows = []
    for rec in sorted(records, key=lambda r: r.get("started") or "", reverse=True):
        ms = [m for m in rec.get("matches") or [] if m.get("win") is not None]
        mw = sum(1 for m in ms if m["win"])
        games = sum(len(m["games"]) for m in ms)
        gw = sum(1 for m in ms for g in m["games"] if g)
        key = ds.record_archetype(rec, colors, assign, ratings)
        deck = (rec.get("deck") or {}).get("main") or {}
        rows.append([f'<td class="l">{esc(rec.get("started") or "")}</td>', f'<td class="l">{esc(rec.get("event") or "")}</td>',
                     f'<td class="l">{esc(arch_names.get(key, key or "offen"))}</td>',
                     f'<td>{len(rec.get("picks") or [])}</td>', f'<td>{sum(deck.values()) if deck else "–"}</td>',
                     f'<td data-v="{mw}">{mw}-{len(ms) - mw}</td>', f'<td data-v="{gw}">{gw}-{games - gw}</td>'])
    return h_table(["Datum", "Event", "Archetyp", "Picks", "Deck", "Matches", "Games"], rows, 'class="sort"',
                   left=(0, 1, 2))


def render_set_report(data, set_code, cards, assign, ratings):
    """HTML der Setauswertung; cards: Scryfall-Daten je Name (fuer Farben, Kosten, Seltenheit)."""
    symbols.reset_used()
    code = (set_code or "").upper()
    records = [r for r in data.get("drafts", []) if (r.get("set") or "").upper() == code]
    stats = ds.card_stats(data, code)
    colors = _colors(cards)
    arch_names = {a["colors"]: a["name"] for a in set_archetypes.for_set(code) or []}
    if not records:
        sections = [h_section("ueberblick", "Überblick", "", "<p>Noch keine Drafts für dieses Set in der Statistik. "
                              "Starte den Live-Draft (Menüpunkt 3), dann werden Drafts und Matches gesammelt.</p>")]
    else:
        sections = [
            h_section("ueberblick", "Überblick", "Alle mitgelesenen Drafts des Sets.", _overview(data, code)),
            h_section("archetypen", "Archetypen",
                      "Je Draft erkannt wie im Live-Draft: aus dem Hauptdeck (sonst den Picks), mit deiner "
                      "Archetyp-Zuordnung und Kategorie. Grau: weniger als %d Spiele." % MIN_GAMES,
                      _archetypes(records, code, colors, assign, ratings)),
            h_section("beste", "Beste und schwächste Karten",
                      f"Karten mit mindestens {TOP_GAMES} Games im Hauptdeck, nach Siegquote der Games.",
                      _best(stats, cards, assign, ratings, arch_names)),
            h_section("karten", "Karten",
                      "Gedraftet: Kopien. Ø Pick: Pick-Nummer im Pack (1 = aus einem vollen Pack). Im Deck: Drafts, "
                      "in deren Hauptdeck die Karte war. Games und Matches: mit der Karte im Hauptdeck. Klick auf "
                      "eine Spalte sortiert.",
                      h_table(CARD_HEAD, _card_rows(stats, cards, assign, ratings, arch_names), 'class="sort"',
                              left=(0, 1, 3, 4))),
            h_section("bewertung", "Bewertung gegen Ergebnis",
                      "Deine Kategorien (kartenbewertung.json) und wie Karten jeder Kategorie im Deck abgeschnitten "
                      "haben. Liegt Filler über MustPlay, lohnt ein zweiter Blick auf die Bewertung.",
                      _ratings_vs_results(stats, ratings)),
            h_section("drafts", "Drafts", "Neueste zuerst.", _drafts(records, colors, assign, ratings, arch_names)),
        ]
    nav = "".join(f'<a href="#{sid}">{esc(t)}</a>' for sid, t in
                  (("ueberblick", "Überblick"), ("archetypen", "Archetypen"), ("beste", "Beste und schwächste"),
                   ("karten", "Karten"), ("bewertung", "Bewertung"), ("drafts", "Drafts")))
    css = HTML_CSS + CSS + symbols.symbol_css(symbols.used())
    return (f'<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Setauswertung {esc(code)}</title><style>{css}</style></head><body>'
            f'<header class="top" id="top"><h1>Setauswertung {esc(code)}</h1>'
            f'<span class="sub">aus der Draft-Statistik des Live-Drafts</span></header>'
            f'<div class="layout"><nav><h3>Abschnitte</h3><div class="in">{nav}</div></nav>'
            f'<main>{"".join(sections)}</main></div>'
            f'<footer>Erzeugt mit mtg_sim.py · Kartendaten von Scryfall</footer>{SORT_JS}</body></html>')


def _path(name):
    p = pathlib.Path(name)
    return p if p.is_absolute() else SCRIPT_DIR / p


def run(args):
    """Schreibt die Setauswertung (Set wie angegeben, sonst das haeufigste der Statistik) und oeffnet sie."""
    data = ds.load_stats(_path(args.statistik))
    code = (args.setauswertung or "").upper() or next(iter(ds.sets_in(data)), "")
    if not code:
        sys.exit(f"Noch keine Drafts in {_path(args.statistik)}. Starte den Live-Draft (Menüpunkt 3), dann werden "
                 "Drafts und Matches gesammelt.")
    names = sorted(ds.card_stats(data, code))
    try:
        cards = fetch_cards_cached(names) if names else {}
    except (urllib.error.URLError, OSError) as e:
        print(f"Scryfall nicht erreichbar, Auswertung ohne Kartendaten: {e}", file=sys.stderr)
        cards = {}
    assign = cardarchetypes.load_assign(_path(args.archetypen))
    ratings = card_ratings.load_ratings(_path(args.bewertung))
    out = OUT_DIR / output_name(code)
    out.write_text(render_set_report(data, code, cards, assign, ratings), encoding="utf-8")
    print(f"Setauswertung gespeichert: {out}", file=sys.stderr)
    if not args.nicht_oeffnen:
        try:
            webbrowser.open(out.resolve().as_uri())
        except Exception:
            pass
    return out
