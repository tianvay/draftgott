"""Berichtsabschnitte mit viel eigener Logik: Spiellogik, Deck-Vergleich und Jace & Planeswalker."""
import itertools
from collections import Counter

from components.cards import Card, EMPOWER_KIND_LABEL
from components.html_base import LABEL_CLASS, esc, h_bar_cell, h_mode, h_pct, h_table, html_mana
from components.mana import can_cast_all, cost_alternatives, land_key
from components.simulation import best_cast, play_score
from components.stats import Z95, compare_metrics
from components.report_cards import render_types_compare


def _example_card(mv, creature):
    return Card(False, mv, cost_alternatives("{%d}" % mv), (), creature, False,
                mv if creature else 0, mv if creature else 0, name=f"{mv}-Mana-Karte")


def _combo_label(chosen):
    return " + ".join(str(c.mv) for c in sorted(chosen, key=lambda c: c.mv)) or "nichts"


def logic_example():
    """Beispiel aus der Praxis, berechnet mit der echten Auswahlfunktion:
    Hand = 1x 2-Mana, 1x 3-Mana, 4x 1-Mana (+ 1 Land), Runde 2 mit 2 Laendern."""
    tables = []
    for creature in (True, False):
        hand = [_example_card(2, creature), _example_card(3, creature)] + [_example_card(1, creature)] * 4
        key = land_key([("W",)] * 2)
        counts = Counter(hand)
        kinds = sorted(counts)
        combos = []
        for amounts in itertools.product(*(range(counts[k] + 1) for k in kinds)):
            chosen = [k for k, n in zip(kinds, amounts) for _ in range(n)]
            if chosen and can_cast_all(tuple(sorted(c.alts for c in chosen)), key):
                combos.append((play_score(chosen), chosen))
        combos.sort(key=lambda x: x[0], reverse=True)
        _, picked = best_cast(hand, key, False, True)
        tables.append((creature, combos, _combo_label(picked)))
    # Beispielverlauf Runde 2-4 (Kreaturen), jede Runde ein weiteres Land
    hand = [_example_card(2, True), _example_card(3, True)] + [_example_card(1, True)] * 4
    flow = []
    for turn in (2, 3, 4):
        key = land_key([("W",)] * turn)
        _, ch = best_cast(hand, key, False, True)
        for c in ch:
            hand.remove(c)
        flow.append((turn, _combo_label(ch), sum(c.mv for c in ch), _combo_label(hand)))
    return tables, flow


def render_logic_section(has_jace=False):
    tables, flow = logic_example()
    steps = [
        "<b>Starthand:</b> 7 Karten, bei Bedarf London-Mulligan: wieder 7 ziehen, je Mulligan eine Karte unter die "
        "Bibliothek (Regeln im Abschnitt Mulligan).",
        "<b>Ziehen:</b> Auf dem Play entfällt die Karte in Runde 1, auf dem Draw wird jede Runde gezogen.",
        "<b>Landcycling (Pflicht):</b> Fehlt in den ersten Runden ein Land auf der Hand, wird ein Landcycler "
        "gecycelt, damit der Landdrop klappt.",
        "<b>Land legen:</b> Es wird das Land gelegt, mit dem in dieser Runde am meisten Mana in Zauber fließen kann. "
        "Bei Gleichstand kommt ein getapptes Land zuerst, danach zählt, welches Land mehr verschiedene Farben bringt. "
        "Länder, die getappt kommen, außer man kontrolliert einen Planeswalker (oder zeigt bzw. kontrolliert einen Jace), "
        "kommen untapped, wenn ein Planeswalker (Jace-Token oder Karte) auf dem Tisch liegt; sonst wird, wenn möglich, "
        "zuerst ein Zauber gewirkt, der einen Planeswalker erschafft, und danach das Land gelegt.",
        "<b>Zauber wählen:</b> Aus allen Kombinationen, die zusammen bezahlt werden können (Farben beachtet), "
        "wird die beste nach den vier Auswahlregeln gespielt.",
        "<b>Draw-Zauber:</b> Gezogene Karten kommen sofort auf die Hand. Ein gezogenes Land wird gelegt, wenn der "
        "Landdrop noch frei ist, und mit dem übrigen Mana wird weiter gezaubert.",
        "<b>Surveil durch Karten:</b> Nach dem Zaubern surveilen das gelegte Land und die gewirkten Karten (Land oben "
        "lassen, wenn Länder fehlen, sonst in den Friedhof).",
        "<b>Prepared:</b> Kopien der Zauberhälften prepared Kreaturen stehen wie Handkarten zur Auswahl (bei "
        "Gleichstand zuerst die Handkarte); eine Kreatur, die gerade prepared ins Spiel kam, erlaubt die Kopie noch in "
        "derselben Runde.",
        "<b>Landcycling (nur wenn es sich lohnt):</b> Eine nicht spielbare Karte wird mit übrigem Mana gecycelt, "
        "wenn das diese oder nächste Runde etwas verbessert.",
        "<b>Angriff:</b> Kreaturen vom Vorzug greifen an, neue nur mit Haste, Kreaturen mit Defender nie.",
    ]
    if has_jace:
        steps.insert(2, "<b>Jace (Empower):</b> Hat der Jace-Token mindestens 3 Loyalty, wird er zu Rundenbeginn aktiviert (Karte ziehen), "
                        "sonst nach dem Zaubern, höchstens einmal pro Runde. Details im Abschnitt Jace & Planeswalker.")
    rules = [
        "<b>Möglichst viel Mana ausgeben.</b> Die Kombination mit der größten Summe der Manawerte gewinnt.",
        "<b>Bei Gleichstand mehr Kreaturen,</b> weil sie den Schaden machen.",
        "<b>Dann höhere Summe aus Power und Toughness.</b>",
        "<b>Dann mehr Karten</b> (also lieber zwei billige als eine teure Karte).",
    ]
    ex_tables = []
    for creature, combos, picked in tables:
        rows = []
        for sc, chosen in combos:
            win = _combo_label(chosen) == picked
            rows.append([f'<td class="l">{esc(_combo_label(chosen))}</td>', f"<td>{sc[0]}</td>", f"<td>{sc[1]}</td>",
                         f"<td>{sc[2]}</td>", f"<td>{sc[3]}</td>", f'<td class="l">{"✔ gewählt" if win else ""}</td>'])
        html_rows = "".join(
            f'<tr class="{"win" if r[-1].endswith("gewählt</td>") else ""}">' + "".join(r) + "</tr>" for r in rows)
        head = "".join(f'<th class="{"l" if i in (0, 5) else ""}">{h}</th>' for i, h in enumerate(
            ["Kombination (Manawerte)", "Mana", "Kreaturen", "Power + Toughness", "Karten", ""]))
        title = "Alles Kreaturen (Power und Toughness = Manawert)" if creature else "Keine Kreaturen (z. B. Zauber)"
        ex_tables.append(f'<div class="panel"><b>{title}</b><div class="tw"><table><thead><tr>{head}</tr></thead>'
                         f'<tbody>{html_rows}</tbody></table></div></div>')
    flow_rows = [[f'<td class="l">Runde {t}</td>', f"<td>{t}</td>", f'<td class="l">{esc(c)}</td>',
                  f"<td>{m_}</td>", f'<td class="l">{esc(rest)}</td>'] for t, c, m_, rest in flow]
    total_spent = sum(f[2] for f in flow)
    total_avail = sum(f[0] for f in flow)
    body = (
        '<div class="grid g2"><div class="panel"><b>Ablauf einer Runde</b><ol class="ass">'
        + "".join(f"<li>{x}</li>" for x in steps) + '</ol></div>'
        '<div class="panel"><b>So wird aus mehreren spielbaren Karten ausgewählt</b><ol class="ass">'
        + "".join(f"<li>{x}</li>" for x in rules)
        + '</ol><div class="note">Die Regeln gelten der Reihe nach: Erst wenn zwei Kombinationen bei Regel 1 gleichauf '
          'sind, entscheidet Regel 2, und so weiter. Die Wahl gilt nur für die aktuelle Runde, es gibt keine '
          'Vorausschau auf spätere Runden (außer beim Landcycling). Was spielbar ist, wird auch gespielt, '
          'Karten werden nicht absichtlich zurückgehalten.</div></div></div>'
        '<div class="panel" style="margin-top:14px"><b>Beispiel: Runde 2 mit zwei Ländern</b>'
        '<div class="note" style="margin:2px 0 10px">Hand: eine 2-Mana-Karte, eine 3-Mana-Karte, vier 1-Mana-Karten und '
        'ein Land. Ein Land liegt schon, das zweite wird jetzt gelegt, es stehen also 2 Mana zur Verfügung. '
        'Die 3-Mana-Karte ist nicht bezahlbar. Die Tabellen listen alle bezahlbaren Kombinationen, '
        'berechnet mit der echten Auswahlfunktion.</div>'
        f'<div class="grid">{"".join(ex_tables)}</div>'
        '<div style="margin-top:14px"><b>Weiterer Verlauf</b> <span class="muted">(Annahme: jede Runde kommt ein weiteres Land)</span>'
        + h_table(["", "Mana", "Gespielt (Manawerte)", "Ausgegeben", "Rest auf der Hand"], flow_rows, left=(0, 2, 4))
        + f'<div class="note">Hier werden {total_spent} von {total_avail} verfügbaren Mana genutzt, also '
          f'{total_spent / total_avail:.0%} Auslastung. Bei den Prozentwerten der Curve-Auslastung zählt das '
          f'ausgegebene Mana (Summe der Manawerte, bei Landcycling die Cycling-Kosten) geteilt durch das '
          f'Mana der Länder, die in dieser Runde Mana liefern.</div></div></div>')
    return body


def deck_diff_chips(main_deck, alt_deck):
    names = sorted(set(main_deck["deck"]) | set(alt_deck["deck"]))
    out = []
    for n in names:
        d = alt_deck["deck"].get(n, 0) - main_deck["deck"].get(n, 0)
        if d > 0:
            out.append(f'<span class="tag add">+{d} {esc(n)}</span>')
        elif d < 0:
            out.append(f'<span class="tag rem">−{-d} {esc(n)}</span>')
    return "".join(out) or '<span class="muted">identisch</span>'


JACE_RULES = [
    "Der Jace-Token startet mit 0 Loyalty und hat die Fähigkeiten −1: Surveil 1 und −3: eine Karte ziehen. Empower legt "
    "Loyalty auf den Token, ohne Token wird ein neuer erstellt. Bei 0 Loyalty verschwindet er, der nächste Empower "
    "erstellt einen neuen.",
    "Jace wird höchstens einmal pro Runde aktiviert und nur, wenn die Bibliothek nicht leer ist. Zu Rundenbeginn mit "
    "Loyalty aus früheren Runden nur zum Ziehen (ab 3 Loyalty, die Karte kann dann noch gespielt werden). Nach dem "
    "Zaubern: ab 3 Loyalty ziehen, sonst −1: Surveil 1, auch wenn er dadurch auf 0 sinkt und verschwindet.",
    "Surveil: Ein Land bleibt oben, wenn die teuerste Karte auf der Hand noch nicht gespielt werden kann, weil Länder "
    "fehlen (Länder auf dem Feld und auf der Hand weniger als ihr Manawert). Sonst kommt das Land in den Friedhof. "
    "Zauber bleiben immer oben.",
    "Einmalig: Zauber (Instant, Sorcery) und „beim Betreten“-Effekte wirken sofort beim Ausspielen, auch bei Ländern.",
    "Wiederkehrend, modelliert: „whenever you cast …“ (alle, Kreatur, Nichtkreatur, Instant oder Sorcery), „whenever … "
    "enters“ (Kreatur, Land, Permanent), „whenever … attacks“ (ab der Runde nach dem Ausspielen, mit Haste sofort, nie "
    "bei Defender) und „at the beginning of …“ (einmal pro Runde ab der Folgerunde). Karten reagieren nur auf "
    "Ereignisse, nachdem sie im Spiel sind.",
    "Bezahlbare Fähigkeiten werden mit dem Mana benutzt, das nach dem Zaubern übrig ist, so oft es reicht (höchstens "
    "10-mal pro Runde). Mit {T} im Preis nur einmal pro Runde und bei Kreaturen erst ab der Folgerunde. Exil aus dem "
    "Friedhof (Campus Crier) ist modelliert, andere Kosten (Opfern, Ablegen) nicht.",
    "Modale Zauber zählen ihren Empower immer. Es wird nur die Vorderseite einer Karte simuliert, die Zählung "
    "berücksichtigt alle Seiten.",
    "Die Einordnung stammt aus dem Kartentext von Scryfall und ist unten zur Kontrolle neben jeder Karte aufgeführt. "
    "Karten mit weiteren Planeswalker-Bezügen werden nur gezählt und nicht simuliert.",
]


def render_compare_section(ctx):
    a = ctx["args"]
    main_deck = ctx
    decks = [main_deck] + ctx["alts"]
    labels = list(main_deck["results"].keys())
    sims = a.sims

    # ---- Uebersicht der Decks
    ov = []
    for i, d in enumerate(decks):
        cols = "".join(html_mana(c) for c in sorted(d["deck_colors"], key="WUBRGC".find)) or "–"
        diff = '<span class="muted">Hauptdeck</span>' if i == 0 else deck_diff_chips(main_deck, d)
        ov.append([f'<td class="l"><b>{esc(d["name"])}</b></td>', f"<td>{len(d['cards'])}</td>", f"<td>{d['n_lands']}</td>",
                   f"<td>{d['avg_mv']:.2f}</td>", f'<td class="l">{cols}</td>', f'<td class="l">{diff}</td>'])
    overview = h_table(["Deck", "Karten", "Länder", "Ø Manakosten", "Farben", "Unterschiede zum Hauptdeck"], ov,
                       left=(0, 4, 5))
    warn = ""
    for d in decks:
        if d["missing"]:
            warn += (f'<div class="warnbox">{esc(d["name"])}: nicht bei Scryfall gefunden (nicht simuliert): '
                     f'{esc(", ".join(d["missing"]))}</div>')
    if len({len(d["cards"]) for d in decks}) > 1:
        warn += '<div class="warnbox">Die Decks haben unterschiedlich viele Karten, das beeinflusst Mana- und Kartenwerte.</div>'

    # ---- Detailtabellen je Modus + Zaehler fuer das Fazit
    tally = {i: {"good": 0, "bad": 0, "same": 0} for i in range(1, len(decks))}
    panels = []
    for label in labels:
        rows_html = []
        for name, kind, higher, cells in compare_metrics(decks, a, label):
            base = cells[0]

            def fmt(c):
                if c is None:
                    return "–"
                v, hw, _ = c
                if kind == "prop":
                    return f'{v * 100:.1f}% <span class="muted">±{hw * 100:.1f}</span>'
                return f'{v:.2f} <span class="muted">±{hw:.2f}</span>'

            tds = [f'<td class="l">{esc(name)}</td>', f"<td>{fmt(base)}</td>"]
            for i in range(1, len(decks)):
                c = cells[i]
                if c is None or base is None:
                    tds += [f"<td>{fmt(c)}</td>", '<td class="muted">–</td>']
                    continue
                diff = c[0] - base[0]
                se = (c[2] + base[2]) ** 0.5
                sig = abs(diff) > Z95 * se if se > 0 else diff != 0
                good = (diff > 0) == higher
                cls = ("good" if good else "bad") if sig else ""
                tally[i]["good" if sig and good else "bad" if sig else "same"] += 1
                if kind == "prop":
                    txt = f"{diff * 100:+.1f} PP"
                    err = f"±{Z95 * se * 100:.1f}"
                else:
                    txt = f"{diff:+.2f}"
                    err = f"±{Z95 * se:.2f}"
                tds.append(f"<td>{fmt(c)}</td>")
                tds.append(f'<td class="{cls}">{txt} <span style="font-weight:400;opacity:.75">{err}</span></td>'
                           if sig else f'<td class="muted">{txt} <span style="opacity:.75">{err}</span> ≈</td>')
            rows_html.append(tds)
        heads = ["Kennzahl", esc(decks[0]["name"]) + " (Haupt)"]
        for d in decks[1:]:
            heads += [esc(d["name"]), "Δ"]
        panels.append(f'<div class="panel"><b>{esc(label)}</b>{h_table(heads, rows_html)}</div>')

    fazit_rows = []
    for i in range(1, len(decks)):
        t = tally[i]
        fazit_rows.append([f'<td class="l"><b>{esc(decks[i]["name"])}</b></td>',
                           f'<td class="good">{t["good"]}</td>', f'<td class="bad">{t["bad"]}</td>',
                           f'<td>{t["same"]}</td>'])
    fazit = h_table(["Alternative gegen Hauptdeck", "Klar besser", "Klar schlechter", "Kein klarer Unterschied"], fazit_rows)

    types_compare = render_types_compare(decks)
    return (f'<div class="panel">{overview}{warn}</div>'
            f'<div style="margin-top:14px">{types_compare}</div>'
            f'<div class="panel" style="margin-top:14px"><b>Fazit über alle Kennzahlen (Play und Draw zusammen)</b>{fazit}'
            '</div>'
            f'<div class="grid" style="margin-top:14px">{"".join(panels)}</div>')


JACE_TAG_LABEL = {"jace": "erwähnt Jace", "pw_help": "Planeswalker (hilft)", "pw_removal": "gegen Planeswalker",
                  "is_pw": "ist Planeswalker"}


def render_jace_section(ctx):
    ja, res, a = ctx["jace"], ctx["results"], ctx["args"]
    labels = list(res.keys())
    sims, H = a.sims, ctx["horizon"]
    cat, tg = ja["cat"], ja["tags"]
    helps = sum(r["qty"] for r in ja["cards"] if {"jace", "pw_help"} & set(r["tags"]))
    kpis = [
        ("Karten mit Empower Jace", str(ja["empower_copies"]), f"{ja['empower_cards']} verschiedene"),
        ("Einmalig", str(ja["once_copies"]), f"Σ Empower {ja['once_sum']}"),
        ("Wiederkehrend", str(ja["rec_copies"]), f"Σ {ja['rec_sum']} je Auslösung"),
        ("Erwähnen Jace / Planeswalker", str(helps), "ohne Empower, helfend"),
        ("Gegen Planeswalker", str(tg["pw_removal"]["copies"]), "z. B. zerstören, Schaden"),
        ("Planeswalker-Karten", str(tg["is_pw"]["copies"]), "selbst Planeswalker"),
    ]
    kpi_html = "".join(f'<div class="panel kpi"><div class="l">{esc(l)}</div><div class="v">{v}</div>'
                       f'<div class="s">{esc(s_)}</div></div>' for l, v, s_ in kpis)

    kind_rows = []
    for k, label in (("spell", "Einmalig: Zauber (Instant, Sorcery)"), ("etb", "Einmalig: beim Betreten"),
                     ("other_once", "Einmalig: Sonderfall (z. B. beim Sterben)"),
                     ("trigger", "Wiederkehrend: Auslöser („whenever“, „at the beginning“)"),
                     ("activated", "Wiederkehrend: bezahlbare Fähigkeit"), ("unknown", "Nicht erkannt")):
        c = cat[k]
        if c["copies"]:
            kind_rows.append([f'<td class="l">{esc(label)}</td>', f'<td>{c["copies"]}</td>', f'<td>{c["cards"]}</td>',
                              f'<td>{c["sum"]}</td>'])
    kind_rows.append([f'<td class="l"><b>Einmalig gesamt</b></td>', f'<td><b>{ja["once_copies"]}</b></td>', "<td></td>",
                      f'<td><b>{ja["once_sum"]}</b></td>'])
    kind_rows.append([f'<td class="l"><b>Wiederkehrend gesamt</b></td>', f'<td><b>{ja["rec_copies"]}</b></td>', "<td></td>",
                      f'<td><b>{ja["rec_sum"]}</b></td>'])
    kind_table = h_table(["Kategorie", "Karten (Kopien)", "Verschiedene Karten", "Σ Empower"], kind_rows)

    sim_html = ""
    if a.ohne_jace:
        sim_html = '<div class="note">Die Simulation von Jace ist mit --ohne-jace abgeschaltet, es wird nur gezählt.</div>'
    elif not any(res[l]["jace"]["on"] for l in labels):
        sim_html = ('<div class="note">Keine modellierbaren Empower-Effekte im Deck, deshalb gibt es keine Simulationswerte '
                    '(siehe Hinweise unten).</div>')
    else:
        def ge(dist, k):
            return sum(v for key, v in dist.items() if key >= k) / sims

        rows_a, rows_b = [], []
        for l in labels:
            jc = res[l]["jace"]
            cls = LABEL_CLASS.get(l, "")
            rows_a.append([h_mode(l), h_bar_cell(ge(jc["dist_win"], 1), cls=cls), f'<td>{h_pct(ge(jc["dist_win"], 2))}</td>',
                           f'<td>{h_pct(ge(jc["dist_win"], 3))}</td>',
                           f'<td><b>{jc["acts_win"] / sims:.2f}</b></td>', f'<td>{jc["gained_win"] / sims:.2f}</td>',
                           f'<td>{h_pct(jc["empty_reached"] / sims)}</td>'])
            first = sum(jc["first"]) / len(jc["first"]) if jc["first"] else None
            rows_b.append([h_mode(l), h_bar_cell(ge(jc["dist_all"], 1), cls=cls), f'<td>{h_pct(ge(jc["dist_all"], 2))}</td>',
                           f'<td>{h_pct(ge(jc["dist_all"], 3))}</td>',
                           f'<td><b>{jc["acts_all"] / sims:.2f}</b></td>', f'<td>{jc["gained_all"] / sims:.2f}</td>',
                           f'<td>{f"{first:.1f}" if first else "–"}</td>',
                           f'<td>{jc.get("surveil_all", 0) / sims:.2f}</td>',
                           f'<td>{jc.get("surveil_lands_all", 0) / sims:.2f}</td>'])
        heads_a = ["", "≥ 1 Aktivierung", "≥ 2", "≥ 3", "Ø Aktivierungen", "Ø Empower", "Hand leer erreicht"]
        heads_b = heads_a[:-1] + ["Erste Aktivierung (Ø Runde)", "Ø Surveil (−1)", "Ø Länder in den Friedhof"]
        sim_html = (
            '<div class="panel" style="margin-top:14px"><b>Bis die Hand leer ist</b>'
            + h_table(heads_a, rows_a)
            + '</div>'
            f'<div class="panel" style="margin-top:14px"><b>Im ganzen Beobachtungszeitraum (bis Runde {H})</b>'
            + h_table(heads_b, rows_b)
+ '</div>')

    card_rows = []
    for r in sorted(ja["cards"], key=lambda r: (not r["kinds"], r["name"])):
        tags = "".join(f'<span class="tag">{esc(EMPOWER_KIND_LABEL[k])}</span>' for k in r["kinds"]) + "".join(
            f'<span class="tag">{esc(JACE_TAG_LABEL[t])}</span>' for t in r["tags"])
        card_rows.append([f'<td class="l">{esc(r["name"])}</td>', f'<td>{r["qty"]}</td>', f'<td class="l">{tags}</td>',
                          f'<td>{esc(" + ".join(r["values"])) if r["values"] else "–"}</td>',
                          f'<td class="l"><span class="muted" style="font-size:12px">{esc(r["text"])}</span></td>'])
    card_table = h_table(["Karte", "Anz.", "Einordnung", "Empower", "Erkannter Text"], card_rows, left=(0, 2, 4))

    notes = []
    if ja["x_cards"]:
        notes.append("Variabler Wert (X) wird nicht berechnet und zählt als 0: " + ", ".join(ja["x_cards"]))
    if ja["unmodeled"]:
        notes.append("Wirkt in der Simulation nicht (Auslöser oder Kosten nicht modelliert, zählt aber in der Statistik): "
                     + ", ".join(ja["unmodeled"]))
    warn = "".join(f'<div class="warnbox">{esc(n)}</div>' for n in notes)
    return (f'<div class="grid g3">{kpi_html}</div>'
            f'<div class="panel" style="margin-top:14px"><b>Empower Jace nach Art</b>{kind_table}'
            '</div>'
            f'{sim_html}'
            f'<div class="panel" style="margin-top:14px">{warn}<b>Karten</b>{card_table}</div>')
