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
from components.cards import card_info
from components.coverage import analyze_card
from components.deckfile import parse_deck, parse_deck_name, split_label
from components.jace import analyze_jace
from components.mana import required_colors
from components.report import render_html
from components.simulation import simulate


def build_deck(entry, data, args):
    """Wertet eine Deckliste mit den Scryfall-Daten aus."""
    cards, rows, missing, coverage = [], [], [], {}
    for name, qty in entry["deck"].items():
        sc = data.get(name) or data.get(name.split(" // ")[0])
        if not sc:
            missing.append(name)
            print(f"Uebersprungen (nicht gefunden) in {entry['name']}: {name}", file=sys.stderr)
            continue
        card, shown = card_info(sc)
        rows.append((name, qty, card, shown))
        coverage[name] = analyze_card(sc)
        cards += [card] * qty
    if len(cards) < 7 + args.turns:
        sys.exit(f"Zu wenige Karten im Deck {entry['name']}.")
    nonlands = [c for c in cards if not c.is_land]
    castable = [c for c in nonlands if c.alts]
    top_mv = max((c.mv for c in castable), default=None)
    deck_colors = sorted(set().union(*(required_colors(c) for c in nonlands)))
    return dict(
        name=entry["name"], deck=entry["deck"], parts=entry.get("parts", []), rows=rows, cards=cards, missing=missing,
        cats=entry.get("cats", {}), role=entry.get("role"), coverage=coverage,
        n_lands=len(cards) - len(nonlands),
        avg_mv=sum(c.mv for c in nonlands) / len(nonlands) if nonlands else 0,
        unsure=sorted({n for n, _, c, _ in rows if c.is_land and c.tap_mode == "tapped?"}),
        deck_colors=deck_colors, multicolor=len(deck_colors) >= 2, top_mv=top_mv,
        top_names=sorted({n for n, _, c, _ in rows if not c.is_land and c.alts and c.mv == top_mv}),
        cyc_names=sorted({n for n, _, c, _ in rows if c.cycle_alts}))


def _stderr(msg):
    print(msg, file=sys.stderr)


def simulate_deck(dd, args, idx, horizon, progress=_stderr):
    """Simuliert On the Play und On the Draw. Mit --seed bekommt jedes Deck einen eigenen, festen Zufallsstrom."""
    if args.seed is not None:
        random.seed(args.seed + 7919 * idx)
    progress(f"Simuliere {dd['name']}: {args.sims} Spiele pro Modus ...")
    results = {}
    for label, on_draw in (("On the Play", False), ("On the Draw", True)):
        try:
            results[label] = simulate(dd["cards"], args.sims, on_draw, args.turns, horizon,
                                      not args.auras_ohne_kreatur, dd["multicolor"], dd["top_mv"], args.flood,
                                      args.schaden, args.curve_runden, not args.ohne_landcycling,
                                      args.landcycling_runden, args.landcycling_max_laender,
                                      args.landcycling_letzte_karte, not args.ohne_mulligan, args.min_handkarten,
                                      not args.ohne_jace)
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
    if args.drafthelper is not None:
        from components.drafthelper import serve
        serve(args, simulate_entries, save_report)
        return
    html = simulate_entries(entries_from_files(args), args)
    out_path = save_report(html, args)
    if not args.nicht_oeffnen:
        try:
            webbrowser.open(out_path.resolve().as_uri())
        except Exception:
            pass


def main():
    run(parse_args())


if __name__ == "__main__":
    main()
