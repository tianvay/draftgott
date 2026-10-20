#!/usr/bin/env python3
"""
MTG Starthand-Simulator -> erzeugt einen HTML-Bericht

Aufruf:  python mtg_sim.py deck.txt [--sims 10000] [--turns 3] [--max-runden 15]
                                    [--ausgabe bericht.html] [--nicht-oeffnen]
         python mtg_sim.py --drafthelper [kartenpool.txt]   (Kartenseite im Browser, siehe README)

Ablauf pro Runde: ziehen (Play: nicht in Runde 1) -> Land legen -> Zaubern.
Die genaue Spiellogik steht im Bericht (Abschnitt "Spiellogik").

Dieses Script steuert nur den Ablauf; die Bausteine liegen im Ordner components/.
"""
import pathlib
import random
import sys
import urllib.error
import webbrowser
from collections import Counter

from components.cli import parse_args
from components.scryfall import fetch_cards_cached
from components.graveyard import gy_enabler, gy_info
from components.removal import keyword_flags, removal_info
from components.symbols import fetch_symbols
from components.cards import card_info
from components.cardkinds import card_colors, empower_points, flow_kinds, type_kinds
from components.coverage import analyze_card
from components.battle_server import ENEMY_DIR
from components.deckfile import parse_deck, parse_deck_name, split_label
from components.jace import analyze_jace
from components.mana import double_pip_colors, pip_checks, required_colors
from components.report import render_html
from components.simulation import simulate
from components.battle import battle
from components.battle_report import render_battle_html


def build_deck(entry, data, args):
    """Wertet eine Deckliste mit den Scryfall-Daten aus."""
    cards, rows, missing, coverage, info = [], [], [], {}, {}
    for name, qty in entry["deck"].items():
        sc = data.get(name) or data.get(name.split(" // ")[0])
        if not sc:
            missing.append(name)
            print(f"Uebersprungen (nicht gefunden) in {entry['name']}: {name}", file=sys.stderr)
            continue
        card, shown = card_info(sc)
        rows.append((name, qty, card, shown))
        coverage[name] = analyze_card(sc)
        front_type = ((sc.get("card_faces") or [sc])[0].get("type_line") or sc.get("type_line") or "")
        info[name] = {"kinds": type_kinds(front_type), "flow": flow_kinds(sc), "colors": card_colors(sc),
                      "empower": bool(card.empower), "points": empower_points(card.empower),
                      "prepared": bool(card.prepared), **{k: True for k in keyword_flags(sc)},
                      "removal": removal_info(sc), "ramp": bool(card.mana_src or card.treasure),
                      "gy": gy_info(sc), "gy_enabler": gy_enabler(sc)}
        cards += [card] * qty
    if len(cards) < 7 + args.turns:
        sys.exit(f"Zu wenige Karten im Deck {entry['name']}.")
    nonlands = [c for c in cards if not c.is_land]
    castable = [c for c in nonlands if c.alts]
    top_mv = max((c.mv for c in castable), default=None)
    deck_colors = sorted(set().union(*(required_colors(c) for c in nonlands)))
    return dict(
        double_pips=double_pip_colors(nonlands), pip_checks=pip_checks(nonlands),
        name=entry["name"], deck=entry["deck"], parts=entry.get("parts", []), rows=rows, cards=cards, missing=missing,
        cats=entry.get("cats", {}), role=entry.get("role"), coverage=coverage, info=info,
        n_lands=len(cards) - len(nonlands),
        avg_mv=sum(c.mv for c in nonlands) / len(nonlands) if nonlands else 0,
        unsure=sorted({n for n, _, c, _ in rows if c.is_land and c.tap_mode == "tapped?"}),
        deck_colors=deck_colors, multicolor=len(deck_colors) >= 2, top_mv=top_mv,
        top_names=sorted({n for n, _, c, _ in rows if not c.is_land and c.alts and c.mv == top_mv}),
        cyc_names=sorted({n for n, _, c, _ in rows if c.cycle_alts}),
        draw_names=sorted({n for n, _, c, _ in rows if c.draws}),
        surveil_names=sorted({n for n, _, c, _ in rows if c.surveil}),
        prepared_names=sorted({n for n, _, c, _ in rows if c.prepared}),
        ramp_names=sorted({n for n, _, c, _ in rows if c.mana_src or c.treasure}),
        gy_x_names=sorted({n for n, _, c, _ in rows if c.gy_x}))


def _stderr(msg):
    print(msg, file=sys.stderr)


def simulate_deck(dd, args, idx, horizon, progress=_stderr):
    """Simuliert On the Play und On the Draw. Mit --seed bekommt jedes Deck einen eigenen, festen Zufallsstrom."""
    if args.seed is not None:
        random.seed(args.seed + 7919 * idx)
    progress(f"Simuliere {dd['name']}: {args.sims} Spiele pro Modus ...")
    # Splash-Variante aus dem Drafthelper: Spielbarkeit der Nichtland-Karten der Splash-Gruppe messen
    # (Name im Deck, Name im Kartenmodell): zweiteilige Karten heissen im Deck oft nur nach der Vorderseite
    pairs = []
    if dd.get("role") == "splash" and dd.get("parts"):
        pairs = [(n, c.name) for n, _, c, _ in dd["rows"] if not c.is_land and n in dd["parts"][-1][1]]
    dd["splash_track"] = pairs
    track = {model for _, model in pairs}
    results = {}
    for label, on_draw in (("On the Play", False), ("On the Draw", True)):
        try:
            results[label] = simulate(dd["cards"], args.sims, on_draw, args.turns, horizon,
                                      not args.auras_ohne_kreatur, dd["multicolor"], dd["top_mv"], args.flood,
                                      args.schaden, args.curve_runden, not args.ohne_landcycling,
                                      args.landcycling_runden, args.landcycling_max_laender,
                                      args.landcycling_letzte_karte, not args.ohne_mulligan, args.min_handkarten,
                                      not args.ohne_jace,
                                      color_check={"colors": sorted(dd["deck_colors"], key="WUBRG".index),
                                                   "checks": dd["pip_checks"]},
                                      track=track)
        except RuntimeError as e:
            sys.exit(f"{dd['name']}: {e}")
    dd["results"] = results


def entries_from_files(args):
    """Deck-Eintraege aus den Dateien der Kommandozeile (mit optionalem Kern)."""
    entries, used = [], Counter()
    core, core_label = {}, None
    if args.core:
        core_path, core_label = split_label(args.core)
        with open(core_path, encoding="utf-8") as f:
            core = parse_deck(f.read())
        print(f"Kern: {sum(core.values())} Karten aus {core_path}", file=sys.stderr)
    for spec in list(args.deckfile) + (args.deckalt or []):
        path, label = split_label(spec)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        name = parse_deck_name(text, pathlib.Path(path).stem)
        used[name] += 1
        if used[name] > 1:
            name = f"{name} ({used[name]})"
        part = parse_deck(text)
        deck = Counter(core)
        deck.update(part)
        # Herkunft jeder Karte: Mengen je Bereich getrennt halten (eine Karte kann in mehreren Bereichen stehen)
        parts = ([(core_label, dict(core))] if args.core else []) + [(label, part)]
        entries.append({"path": path, "name": name, "deck": dict(deck), "parts": parts})
    return entries


def enemy_name(path):
    """Anzeigename eines Gegnerdecks: 'Name' aus der Datei, sonst der Dateiname."""
    p = pathlib.Path(path)
    fallback = p.stem.replace("_", " ").strip() or p.stem
    return parse_deck_name(p.read_text(encoding="utf-8"), fallback)


def load_enemy(path):
    """Ein Gegnerdeck: {"name", "deck"}. Gesucht wird der Pfad wie angegeben, dann im Projektordner und im Ordner
    enemydecks (dort reicht der Dateiname, auch ohne .txt)."""
    p = pathlib.Path(path)
    here = pathlib.Path(__file__).resolve().parent
    for cand in (here / p, here / ENEMY_DIR / p, here / ENEMY_DIR / (p.name + ".txt")):
        if not p.exists() and cand.exists():
            p = cand
    if not p.exists():
        sys.exit(f"Gegnerdeck nicht gefunden: {path}")
    return {"name": enemy_name(p), "deck": parse_deck(p.read_text(encoding="utf-8"))}


def battle_entries(entries, enemy_paths, args, progress=_stderr):
    """Kampf der Decks (entries, z. B. Splash und NoSplash) gegen ein oder mehrere Gegnerdecks. Gibt den Kampfbericht
    (HTML) zurueck. Der Goldfish wird dafuer nicht simuliert."""
    return battle_entries_games(entries, enemy_paths, args, progress)[0]


def battle_entries_games(entries, enemy_paths, args, progress=_stderr):
    """Wie battle_entries, gibt aber (HTML, Spiele) zurueck; Spiele: {(Deck, Gegner, "play"/"draw"): [Spiel mit
    Protokoll, ...]} fuer die Spieleliste im Kampfbericht (nur solange draftgott laeuft)."""
    if isinstance(enemy_paths, (str, pathlib.Path)):
        enemy_paths = [enemy_paths]
    enemies = [load_enemy(p) for p in enemy_paths]
    progress("Lade Kartendaten von Scryfall ...")
    try:
        names = set().union(*(e["deck"].keys() for e in entries), *(e["deck"].keys() for e in enemies))
        data = fetch_cards_cached(sorted(names), args.neu_laden)
    except urllib.error.URLError as e:
        sys.exit(f"Scryfall nicht erreichbar: {e}")
    decks = [build_deck(e, data, args) for e in entries]
    simulate_battles(decks, enemies, data, args, progress)
    games = {}
    for d_idx, dd in enumerate(decks):
        for e_idx, b in enumerate(dd.get("battles") or []):
            for label, key in (("On the Play", "play"), ("On the Draw", "draw")):
                games[(d_idx, e_idx, key)] = b["results"][label].pop("results_all", [])
    return render_battle_html(decks, args), games


def save_battle_report(html, args):
    out_path = pathlib.Path(getattr(args, "kampf_ausgabe", None) or "mtg_kampf.html")
    out_path.write_text(html, encoding="utf-8")
    print(f"Kampfbericht gespeichert: {out_path.resolve()}", file=sys.stderr)
    return out_path


def simulate_battles(decks, enemies, data, args, progress=_stderr):
    """Kampf jedes Decks gegen jedes Gegnerdeck, getrennt nach On the Play / On the Draw."""
    for e_idx, enemy in enumerate(enemies):
        edd = build_deck({"name": enemy["name"], "deck": enemy["deck"], "parts": []}, data, args)
        for idx, dd in enumerate(decks):
            if args.seed is not None:
                random.seed(args.seed + 104729 * (idx + 1) + 7907 * e_idx)
            progress(f"Kampf {dd['name']} gegen {enemy['name']}: {args.kaempfe} Spiele pro Modus ...")
            results = {}
            for label, on_draw in (("On the Play", False), ("On the Draw", True)):
                results[label] = battle(dd["cards"], edd["cards"], args.kaempfe, on_draw, args.kampf_runden,
                                        not args.ohne_mulligan, args.min_handkarten)
            dd.setdefault("battles", []).append({"enemy": enemy["name"], "results": results})


def simulate_entries(entries, args, progress=_stderr):
    """Laedt die Kartendaten, simuliert alle Decks und gibt den HTML-Bericht als Text zurueck.
    Bei Fehlern (zu wenige Karten, Scryfall nicht erreichbar, ...) endet das Programm mit sys.exit(Meldung)."""
    progress("Lade Kartendaten von Scryfall ...")
    try:
        data = fetch_cards_cached(sorted(set().union(*(e["deck"].keys() for e in entries))), args.neu_laden)
    except urllib.error.URLError as e:
        sys.exit(f"Scryfall nicht erreichbar: {e}")

    horizon = max(args.max_runden, args.turns, args.curve_runden)
    decks = [build_deck(e, data, args) for e in entries]
    for idx, dd in enumerate(decks):
        simulate_deck(dd, args, idx, horizon, progress)

    main_deck = decks[0]
    ctx = dict(main_deck, args=args, horizon=horizon, jace=analyze_jace(main_deck["rows"]), alts=decks[1:],
               all_decks=decks)
    return render_html(ctx)


def save_report(html, args):
    out_path = pathlib.Path(args.ausgabe)
    out_path.write_text(html, encoding="utf-8")
    print(f"Bericht gespeichert: {out_path.resolve()}", file=sys.stderr)
    return out_path


def run(args):
    fetch_symbols(args.neu_laden)  # Original-Manasymbole (einmalig von Scryfall, danach aus dem Cache)
    if args.drafthelper is not None:
        from components.drafthelper import serve
        serve(args, simulate_entries, save_report, battle=battle_entries_games, save_battle=save_battle_report)
        return
    entries = entries_from_files(args)
    html = simulate_entries(entries, args)
    if args.bericht_server:  # Bericht ueber den lokalen Server: "Kampf simulieren" im Bericht
        from components.report_server import serve_report
        save_report(html, args)
        serve_report(html, entries, args, battle_entries_games, save_battle_report,
                     open_browser=not args.nicht_oeffnen)
        return
    paths = [save_report(html, args)]
    if args.gegner:  # Kampf in einen eigenen Bericht
        paths.append(save_battle_report(battle_entries(entries, args.gegner, args), args))
    if not args.nicht_oeffnen:
        for out_path in paths:
            try:
                webbrowser.open(out_path.resolve().as_uri())
            except Exception:
                pass


def main():
    run(parse_args())


if __name__ == "__main__":
    main()
