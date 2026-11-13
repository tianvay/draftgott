"""Turniermodus: die Gegnerdecks eines Unterordners von enemydecks (z. B. wc32) spielen gegeneinander.

Je Paarung viele Spiele (Standard 500). Spiel 1 beginnt per Zufall, danach geht der Verlierer des vorigen Spiels
zuerst (103.1: der Verlierer waehlt; im Limited waehlt man praktisch immer, zuerst zu spielen). Nach einem
Unentschieden waehlt wieder, wer zuletzt gewaehlt hat, also beginnt derselbe Spieler. Beide Decks spielen nach
denselben Regeln des Kampfmodells und geben beim Mulligan nie auf (behalten notfalls die Hand mit 5 Karten).
Paarungen: jeder gegen jeden oder gezielt (z. B. die Paarungen einer Swiss-Runde).
"""
import math
import pathlib
import random
import re
import sys
import urllib.error
import webbrowser

from components.battle import play_game
from components.battle_server import ENEMY_DIR
from components.deckfile import parse_deck, parse_deck_name
from components.html_base import HTML_CSS, esc, h_section
from components.i18n import dec, html_lang, t

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent.parent
Z95 = 1.959964  # 95-%-Bereich (Wilson)


# ---------------------------------------------------------------- Ablauf eines Matches

def next_starter(starter, winner):
    """Wer das naechste Spiel beginnt: der Verlierer; nach einem Unentschieden (winner None) derselbe wie zuletzt."""
    if winner is None:
        return starter
    return "y" if winner == "x" else "x"


def play_match(cards_x, cards_y, games, max_turns=20, game=play_game, rng=random):
    """Spielt games Spiele Deck x gegen Deck y. Gibt Siege, Unentschieden und die Siege je Beginnendem zurueck."""
    m = {"games": games, "wins_x": 0, "wins_y": 0, "draws": 0, "rounds": [],
         "start_x": {"games": 0, "wins": 0}, "start_y": {"games": 0, "wins": 0}}
    starter = rng.choice(["x", "y"])
    for _ in range(games):
        r = game(cards_x, cards_y, starter == "x", max_turns, True, 5, a_never_concede=True)
        winner = {"a": "x", "b": "y"}.get(r["winner"])
        rec = m["start_" + starter]
        rec["games"] += 1
        if winner is None:
            m["draws"] += 1
        else:
            m["wins_" + winner] += 1
            rec["wins"] += winner == starter
            m["rounds"].append(r.get("round", 0))
        starter = next_starter(starter, winner)
    return m


def favourite(wins_x, wins_y):
    """Statistischer Favorit ohne Unentschieden: ("x"/"y"/None, untere, obere Grenze des 95-%-Bereichs der Siegquote
    von x). None, wenn der Bereich 50 % enthaelt (zu knapp)."""
    n = wins_x + wins_y
    if not n:
        return None, 0.0, 1.0
    p = wins_x / n
    z2 = Z95 * Z95
    mid = (p + z2 / (2 * n)) / (1 + z2 / n)
    half = Z95 * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / (1 + z2 / n)
    lo, hi = mid - half, mid + half
    return ("x" if lo > 0.5 else "y" if hi < 0.5 else None), lo, hi


# ---------------------------------------------------------------- Paarungen

def round_robin(n):
    return [(i, j) for i in range(n) for j in range(i + 1, n)]


def _index(token, n, names):
    if token.isdigit():
        i = int(token) - 1
        if not 0 <= i < n:
            raise ValueError(t("Kein Deck mit Nummer {n}.", n=token))
        return i
    hits = [i for i, name in enumerate(names or []) if token.lower() in name.lower()]
    if len(hits) != 1:
        raise ValueError(t("'{w}' passt nicht auf genau ein Deck.", w=token))
    return hits[0]


def parse_pairings(text, n, names=None):
    """Paarungen aus Text wie "1-3 2-4" (auch 1:3, Kommas, Namensteile); leer = jeder gegen jeden. Liste von
    (Index, Index); ValueError bei ungueltiger Eingabe."""
    text = (text or "").strip()
    if not text:
        return round_robin(n)
    pairs = []
    text = re.sub(r"\s*([-:])\s*", r"\1", text)
    for part in re.split(r"[,;\s]+", text):
        if not part:
            continue
        sides = [s.strip() for s in re.split(r"[-:]", part)]
        if len(sides) != 2 or not all(sides):
            raise ValueError(t("Paarung '{p}' bitte als A-B angeben.", p=part))
        a, b = (_index(s, n, names) for s in sides)
        if a == b:
            raise ValueError(t("Ein Deck kann nicht gegen sich selbst spielen ({p}).", p=part))
        pairs.append((a, b))
    return pairs


# ---------------------------------------------------------------- Ordner, Decks, Namen

def list_folders(root):
    """Unterordner von root mit mindestens einem Deck (*.txt)."""
    root = pathlib.Path(root)
    return sorted(p.name for p in root.iterdir() if p.is_dir() and any(p.glob("*.txt"))) if root.is_dir() else []


def list_decks(folder):
    return sorted(pathlib.Path(folder).glob("*.txt"))


def player_name(path, folder):
    """Anzeigename: 'Name' aus der Datei, sonst der Dateiname ohne Ordner-Praefix (wc32_seth_manfield -> Seth
    Manfield)."""
    path = pathlib.Path(path)
    stem = path.stem
    if folder and stem.lower().startswith(folder.lower() + "_"):
        stem = stem[len(folder) + 1:]
    fallback = " ".join(w[:1].upper() + w[1:] for w in stem.replace("_", " ").split()) or path.stem
    return parse_deck_name(path.read_text(encoding="utf-8"), fallback)


def choose_folder(folders, ask=input, out=sys.stderr):
    if len(folders) == 1:
        return folders[0]
    for i, f in enumerate(folders, 1):
        print(f"  {i} = {f}", file=out)
    while True:
        a = ask(t("Turnier-Ordner (Nummer): ")).strip()
        if a.isdigit() and 1 <= int(a) <= len(folders):
            return folders[int(a) - 1]
        if a in folders:
            return a


def ask_pairings(names, ask=input, out=sys.stderr):
    print(t("Decks:"), file=out)
    for i, name in enumerate(names, 1):
        print(f"  {i} = {name}", file=out)
    while True:
        try:
            return parse_pairings(ask(t("Paarungen, z. B. 1-3 2-4 (Enter = jeder gegen jeden): ")), len(names), names)
        except ValueError as e:
            print(e, file=out)


# ---------------------------------------------------------------- Tabelle

def standings(names, matches):
    """Tabelle: Match-Siege (mehr gewonnene Spiele), dann Spielquote. Liste von Zeilen, Beste zuerst."""
    rows = [{"name": n, "idx": i, "matches": 0, "match_wins": 0, "match_losses": 0, "match_draws": 0,
             "game_wins": 0, "game_losses": 0, "game_draws": 0} for i, n in enumerate(names)]
    for m in matches:
        for side, other in (("x", "y"), ("y", "x")):
            r = rows[m[side]]
            r["matches"] += 1
            w, l = m["wins_" + side], m["wins_" + other]
            r["game_wins"] += w
            r["game_losses"] += l
            r["game_draws"] += m["draws"]
            r["match_wins" if w > l else "match_losses" if w < l else "match_draws"] += 1
    played = [r for r in rows if r["matches"]]

    def rate(r):
        n = r["game_wins"] + r["game_losses"]
        return r["game_wins"] / n if n else 0.0
    return sorted(played, key=lambda r: (-(r["match_wins"] + 0.5 * r["match_draws"]), -rate(r), r["name"]))


# ---------------------------------------------------------------- Bericht

CSS = """
footer{max-width:1500px;margin:0 auto;padding:20px;color:var(--muted);font-size:12px}
.verdict{font-weight:650}
.verdict.close{color:var(--muted);font-weight:500}
.bar2{display:flex;height:10px;border-radius:5px;overflow:hidden;background:var(--track);min-width:120px}
.bar2 i{display:block;height:100%}
.bar2 .bx{background:var(--play)} .bar2 .bd{background:#c4c9d4} .bar2 .by{background:var(--draw)}
td.win{font-weight:700}
"""


def _th(text, left):
    return f'<th class="l">{esc(text)}</th>' if left else f"<th>{esc(text)}</th>"


def _pct(a, n):
    return dec(f"{100 * a / n:.1f}") + " %" if n else "–"


def _match_row(names, m):
    x, y = names[m["x"]], names[m["y"]]
    fav, lo, hi = favourite(m["wins_x"], m["wins_y"])
    n = m["games"] or 1
    bar = (f'<div class="bar2"><i class="bx" style="width:{100 * m["wins_x"] / n:.1f}%"></i>'
           f'<i class="bd" style="width:{100 * m["draws"] / n:.1f}%"></i>'
           f'<i class="by" style="width:{100 * m["wins_y"] / n:.1f}%"></i></div>')
    if fav:
        verdict = f'<span class="verdict">{esc(t("{p} hätte gewinnen sollen", p=x if fav == "x" else y))}</span>'
    else:
        verdict = f'<span class="verdict close">{esc(t("zu knapp, kein klarer Favorit"))}</span>'
    sx, sy = m["start_x"], m["start_y"]
    starts = (f'{_pct(sx["wins"], sx["games"])} / {_pct(sy["wins"], sy["games"])}')
    return (f'<tr><td class="l{" win" if fav == "x" else ""}">{esc(x)}</td>'
            f'<td>{m["wins_x"]}</td><td>{m["draws"]}</td><td>{m["wins_y"]}</td>'
            f'<td class="l{" win" if fav == "y" else ""}">{esc(y)}</td><td>{bar}</td>'
            f'<td>{_pct(m["wins_x"], m["wins_x"] + m["wins_y"])}</td>'
            f'<td>{dec(f"{100 * lo:.1f}")}–{dec(f"{100 * hi:.1f}")} %</td>'
            f'<td title="{esc(t("Siegquote des Beginnenden: wenn {x} beginnt / wenn {y} beginnt", x=x, y=y))}">'
            f'{starts}</td><td class="l">{verdict}</td></tr>')


def _matches_table(names, matches):
    head = "".join(_th(h, c in (0, 4, 9)) for c, h in enumerate((
        t("Deck A"), t("Siege A"), t("Unent."), t("Siege B"), t("Deck B"), "", t("Quote A"), t("95-%-Bereich"),
        t("Beginnender gewinnt"), t("Ergebnis"))))
    rows = "".join(_match_row(names, m) for m in matches)
    return f'<div class="panel tw"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'


def _standings_table(names, matches):
    head = "".join(_th(h, c == 1) for c, h in enumerate((
        "#", t("Deck"), t("Matches"), t("Match-Bilanz (S-N-U)"), t("Spiele gewonnen"), t("Spiele verloren"),
        t("Unent."), t("Spielquote"))))
    rows = []
    for pos, r in enumerate(standings(names, matches), 1):
        rows.append(f'<tr><td>{pos}</td><td class="l{" win" if pos == 1 else ""}">{esc(r["name"])}</td>'
                    f'<td>{r["matches"]}</td><td>{r["match_wins"]}-{r["match_losses"]}-{r["match_draws"]}</td>'
                    f'<td>{r["game_wins"]}</td><td>{r["game_losses"]}</td><td>{r["game_draws"]}</td>'
                    f'<td>{_pct(r["game_wins"], r["game_wins"] + r["game_losses"])}</td></tr>')
    return (f'<div class="panel tw"><table><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>'
            f'</div>')


def render_tournament_html(folder, names, matches, games=None, max_turns=20):
    games = games or (matches[0]["games"] if matches else 0)
    title = t("Turnier {f}", f=folder)
    rules = t("Je Paarung {n} Spiele. Spiel 1 beginnt per Zufall, danach geht der Verlierer des vorigen Spiels "
              "zuerst (Regel 103.1: der Verlierer wählt, im Limited fast immer zuerst spielen); nach einem "
              "Unentschieden beginnt wieder derselbe. Beide Decks spielen nach den Regeln des Kampfmodells und "
              "geben beim Mulligan nie auf. Nach Runde {r} gilt ein Spiel als unentschieden.", n=games, r=max_turns)
    verdict_hint = t("Favorit: Liegt der 95-%-Bereich der Siegquote (ohne Unentschieden) ganz über 50 %, hätte das "
                     "Deck statistisch gewinnen sollen; enthält er 50 %, ist das Matchup zu knapp für eine Aussage.")
    sections = [h_section("paarungen", t("Paarungen"), esc(rules) + "<br>" + esc(verdict_hint),
                          _matches_table(names, matches))]
    if len({i for m in matches for i in (m["x"], m["y"])}) > 2:
        sections.append(h_section("tabelle", t("Tabelle"),
                                  esc(t("Sortiert nach Match-Siegen (mehr gewonnene Spiele der Paarung), dann "
                                        "nach Spielquote.")), _standings_table(names, matches)))
    nav = "".join(f'<a href="#{sid}">{esc(label)}</a>' for sid, label in
                  (("paarungen", t("Paarungen")), ("tabelle", t("Tabelle"))) if f'id="{sid}"' in "".join(sections))
    return (f'<!DOCTYPE html><html lang="{html_lang()}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)}</title><style>{HTML_CSS + CSS}</style></head><body>'
            f'<header class="top" id="top"><h1>{esc(title)}</h1>'
            f'<span class="sub">{esc(t("{n} Decks, {m} Paarungen", n=len(names), m=len(matches)))}</span></header>'
            f'<div class="layout"><nav><h3>{esc(t("Abschnitte"))}</h3><div class="in">{nav}</div></nav>'
            f'<main>{"".join(sections)}</main></div>'
            f'<footer>{esc(t("Erzeugt mit mtg_sim.py · Kartendaten von Scryfall"))}</footer></body></html>')


# ---------------------------------------------------------------- Programm

def run(args, build_deck, fetch_cards, ask=input):
    """Modus 5: Ordner und Paarungen waehlen, Matches spielen, Bericht schreiben und oeffnen."""
    root = SCRIPT_DIR / ENEMY_DIR
    folders = list_folders(root)
    if not folders:
        sys.exit(t("Kein Unterordner mit Decks in {path}.", path=root))
    folder = args.turnier or choose_folder(folders, ask)
    if folder not in folders:
        sys.exit(t("Turnier-Ordner nicht gefunden: {f} (vorhanden: {all})", f=folder, all=", ".join(folders)))
    paths = list_decks(root / folder)
    names = [player_name(p, folder) for p in paths]
    if len(paths) < 2:
        sys.exit(t("Für ein Turnier braucht der Ordner mindestens zwei Decks."))
    if args.paarung:
        try:
            pairs = parse_pairings(" ".join(args.paarung), len(names), names)
        except ValueError as e:
            sys.exit(str(e))
    else:
        pairs = ask_pairings(names, ask)
    decks = [parse_deck(p.read_text(encoding="utf-8")) for p in paths]
    print(t("Lade Kartendaten von Scryfall ..."), file=sys.stderr)
    try:
        data = fetch_cards(sorted(set().union(*(d.keys() for d in decks))), args.neu_laden)
    except urllib.error.URLError as e:
        sys.exit(t("Scryfall nicht erreichbar: {err}", err=e))
    built = {}
    for i in sorted({i for p in pairs for i in p}):
        built[i] = build_deck({"name": names[i], "deck": decks[i], "parts": []}, data, args)["cards"]
    rng = random.Random(args.seed) if args.seed is not None else random
    if args.seed is not None:
        random.seed(args.seed)
    matches = []
    for a, b in pairs:
        print(t("{a} gegen {b}: {n} Spiele ...", a=names[a], b=names[b], n=args.turnier_spiele), file=sys.stderr)
        m = play_match(built[a], built[b], args.turnier_spiele, args.kampf_runden, rng=rng)
        m.update(x=a, y=b)
        matches.append(m)
        fav, _, _ = favourite(m["wins_x"], m["wins_y"])
        print(f"  {m['wins_x']} : {m['wins_y']} ({t('Unentschieden')} {m['draws']}) -> "
              + (t("{p} hätte gewinnen sollen", p=names[a] if fav == "x" else names[b]) if fav
                 else t("zu knapp, kein klarer Favorit")), file=sys.stderr)
    out = pathlib.Path(args.turnier_ausgabe or SCRIPT_DIR / f"turnier_{folder}.html")
    out.write_text(render_tournament_html(folder, names, matches, args.turnier_spiele, args.kampf_runden),
                   encoding="utf-8")
    print(t("Turnierbericht gespeichert: {path}", path=out.resolve()), file=sys.stderr)
    if not args.nicht_oeffnen:
        try:
            webbrowser.open(out.resolve().as_uri())
        except Exception:
            pass
    return matches
