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
from components.i18n import t

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent.parent
Z95 = 1.959964  # 95-%-Bereich (Wilson)


# ---------------------------------------------------------------- Ablauf eines Matches

def next_starter(starter, winner):
    """Wer das naechste Spiel beginnt: der Verlierer; nach einem Unentschieden (winner None) derselbe wie zuletzt."""
    if winner is None:
        return starter
    return "y" if winner == "x" else "x"


BASICS = {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"}
WHO = {"x": "Wir", "y": "Gegner"}  # Namen der Seiten in play_game


def _new_side():
    return {"win_rounds": {}, "combat": 0, "direct": 0, "deaths": 0, "mull_games": 0, "mull_wins": 0,
            "end_life_win": 0, "cards": {}}


def _life_by_round(r):
    """Leben beider Seiten am Ende jeder Runde: [(Leben x, Leben y), ...]."""
    by_round = {}
    for e in r.get("log") or []:
        if e.get("life"):
            by_round[e["round"]] = (e["life"][WHO["x"]], e["life"][WHO["y"]])
    out, last = [], (20, 20)
    for i in range(1, max(by_round, default=0) + 1):
        last = by_round.get(i, last)
        out.append(last)
    return out


def _collect(m, r, winner):
    """Kennzahlen eines Spiels in die Seiten des Matches einrechnen (fehlende Angaben werden uebersprungen)."""
    life = _life_by_round(r)
    if life:
        m["_life"].append(life)
    for side, other in (("x", "y"), ("y", "x")):
        s, who, won = m["sides"][side], WHO[side], winner == side
        if won:
            s["win_rounds"][r.get("round", 0)] = s["win_rounds"].get(r.get("round", 0), 0) + 1
            if life:
                s["end_life_win"] += life[-1][0 if side == "x" else 1]
        stats = r.get("stats") or {}
        for key in ("combat", "direct", "deaths"):
            s[key] += (stats.get(key) or {}).get(who, 0)
        if (r.get("mulligans") or {}).get(who, 0):
            s["mull_games"] += 1
            s["mull_wins"] += won
        opening = set((r.get("opening") or {}).get(who) or [])
        seen = opening | {e["drew"] for e in r.get("log") or [] if e.get("player") == who and e.get("drew")}
        for name in seen - BASICS:
            c = s["cards"].setdefault(name, {"seen": 0, "seen_wins": 0, "open": 0, "open_wins": 0})
            c["seen"] += 1
            c["seen_wins"] += won
            if name in opening:
                c["open"] += 1
                c["open_wins"] += won


def _life_curve(lives):
    """Durchschnittliche Leben je Runde; nach Spielende zaehlt der letzte Stand."""
    rounds = max((len(v) for v in lives), default=0)
    curve = {"x": [], "y": []}
    for i in range(rounds):
        vals = [v[min(i, len(v) - 1)] for v in lives]
        curve["x"].append(sum(a for a, _ in vals) / len(vals))
        curve["y"].append(sum(b for _, b in vals) / len(vals))
    return curve


def play_match(cards_x, cards_y, games, max_turns=20, game=play_game, rng=random):
    """Spielt games Spiele Deck x gegen Deck y. Gibt Siege, Unentschieden, die Siege je Beginnendem und Kennzahlen je
    Seite zurueck (sides: Siege nach Runde, Schaden, gestorbene Kreaturen, Mulligans, Karten; life_curve)."""
    m = {"games": games, "wins_x": 0, "wins_y": 0, "draws": 0, "rounds": [],
         "start_x": {"games": 0, "wins": 0}, "start_y": {"games": 0, "wins": 0},
         "sides": {"x": _new_side(), "y": _new_side()}, "_life": []}
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
        _collect(m, r, winner)
        starter = next_starter(starter, winner)
    m["life_curve"] = _life_curve(m.pop("_life"))
    return m


def deck_card_stats(matches, idx):
    """Kartenstatistik eines Decks ueber alle seine Matches zusammengefasst."""
    out = {}
    for m in matches:
        for side in ("x", "y"):
            if m.get(side) != idx or "sides" not in m:
                continue
            for name, c in m["sides"][side]["cards"].items():
                o = out.setdefault(name, {"seen": 0, "seen_wins": 0, "open": 0, "open_wins": 0})
                for k in o:
                    o[k] += c[k]
    return out


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


def choose_folder(folders, ask=input, out=None):
    out = out or sys.stderr
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


def ask_pairings(names, ask=input, out=None):
    out = out or sys.stderr
    print(t("Decks:"), file=out)
    for i, name in enumerate(names, 1):
        print(f"  {i} = {name}", file=out)
    while True:
        try:
            return parse_pairings(ask(t("Paarungen, z. B. 1-3 2-4 (Enter = jeder gegen jeden): ")), len(names), names)
        except ValueError as e:
            print(e, file=out)


# ---------------------------------------------------------------- Decks aufbauen (auch unvollstaendige)

DECK_SIZE = 40
MIN_CARDS = 10  # darunter laesst sich kein Spiel simulieren (build_deck bricht ab)


def size_note(n):
    return t("{n} Karten statt {m}", n=n, m=DECK_SIZE)


def missing_note(card):
    return t("Karte nicht gefunden, fehlt im Deck: {c}", c=card)


def unplayable_note():
    return t("zu wenige Karten, nicht spielbar")


def build_all(names, decks, data, args, build_deck):
    """Baut alle Decks. Unvollstaendige Decklisten (z. B. 39 Karten) werden trotzdem gespielt und nur gekennzeichnet;
    nur ein Deck, das sich gar nicht bauen laesst, faellt heraus. Gibt ({Index: Karten}, [Info je Deck]) zurueck;
    Info: name, size (simulierte Karten), playable, notes."""
    built, info = {}, []
    for i, (name, deck) in enumerate(zip(names, decks)):
        rec = {"name": name, "size": sum(deck.values()), "playable": True, "notes": []}
        try:
            dd = build_deck({"name": name, "deck": deck, "parts": []}, data, args)
        except SystemExit:
            rec.update(playable=False, notes=[unplayable_note()])
            info.append(rec)
            continue
        built[i] = dd["cards"]
        rec["size"] = len(dd["cards"])
        if rec["size"] != DECK_SIZE:
            rec["notes"].append(size_note(rec["size"]))
        rec["notes"] += [missing_note(c) for c in dd.get("missing") or []]
        info.append(rec)
    return built, info


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

def render_tournament_html(folder, names, matches, games=None, max_turns=20, decks=None):
    """HTML des Turnierberichts (components/tournament_report.py)."""
    from components.tournament_report import render
    return render(folder, names, matches, games, max_turns, decks)


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
    built, info = build_all(names, decks, data, args, build_deck)
    for d in info:
        if d["notes"]:
            print(f"  {d['name']}: {'; '.join(d['notes'])}", file=sys.stderr)
    skipped = [p for p in pairs if p[0] not in built or p[1] not in built]
    for a, b in skipped:
        print(t("Paarung fällt aus (Deck nicht spielbar): {a} gegen {b}", a=names[a], b=names[b]), file=sys.stderr)
    pairs = [p for p in pairs if p not in skipped]
    used = {i for p in pairs + skipped for i in p}
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
    out.write_text(render_tournament_html(folder, names, matches, args.turnier_spiele, args.kampf_runden,
                                          decks=[d for i, d in enumerate(info) if i in used]), encoding="utf-8")
    print(t("Turnierbericht gespeichert: {path}", path=out.resolve()), file=sys.stderr)
    if not args.nicht_oeffnen:
        try:
            webbrowser.open(out.resolve().as_uri())
        except Exception:
            pass
    return matches
