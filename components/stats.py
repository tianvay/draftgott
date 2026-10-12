"""Statistik: Ampel-Schwellen, Zeitkennzahlen und Signifikanz-Rechnung fuer den Deck-Vergleich."""
import statistics


# Ampel fuer "mindestens einen Zauber gespielt" je Runde: (gruen ab, gelb ueber)
# Wert >= gruen -> gruen, Wert > gelb -> gelb, sonst rot. Gerechnet wird mit der angezeigten ganzen Prozentzahl.
TRAFFIC = {
    False: {1: (20, 0), 2: (90, 80), 3: (95, 90)},   # On the Play
    True:  {1: (22, 0), 2: (92, 83), 3: (96, 85)},   # On the Draw
}


def traffic_level(pct, on_draw, turn):
    """Gibt 'green', 'yellow' oder 'red' fuer Runde 1-3 zurueck, sonst None."""
    limits = TRAFFIC[on_draw].get(turn)
    if limits is None:
        return None
    green, yellow = limits
    if pct >= green:
        return "green"
    if pct > yellow:
        return "yellow"
    return "red"


def lethal_level(turn):
    """Runde <= 5 gruen, 6-7 gelb, ab 8 rot."""
    return "green" if turn <= 5 else "yellow" if turn <= 7 else "red"


def timing_stats(turns, sims):
    if not turns:
        return None
    return statistics.mean(turns), statistics.median(turns), len(turns) / sims


Z95 = 1.96


def wilson_halfwidth(k, n):
    if n <= 0:
        return 0.0
    p = k / n
    den = 1 + Z95 ** 2 / n
    return Z95 * ((p * (1 - p) / n + Z95 ** 2 / (4 * n * n)) ** 0.5) / den


def mean_var_of_mean(values):
    """Mittelwert und Varianz des Mittelwerts (Standardfehler im Quadrat)."""
    n = len(values)
    if n == 0:
        return None
    m_ = sum(values) / n
    if n == 1:
        return m_, 0.0
    var = sum((v - m_) ** 2 for v in values) / (n - 1)
    return m_, var / n


def compare_metrics(decks, args, label):
    """Liste der Vergleichs-Kennzahlen fuer einen Modus. Jede Zeile: (Name, Art, hoeher_ist_besser, [Zelle je Deck]).
    Zelle: (Wert, Halbbreite 95%, Varianz des Werts) oder None."""
    sims, T, C = args.sims, args.turns, args.curve_runden

    def prop(k, n):
        if n <= 0:
            return None
        p = k / n
        return p, wilson_halfwidth(k, n), p * (1 - p) / n

    def mean(values):
        r = mean_var_of_mean(values)
        return None if r is None else (r[0], Z95 * r[1] ** 0.5, r[1])

    rows = []
    mull_on = decks[0]["results"][label]["mulligan"]["on"]
    if mull_on:
        rows.append(("Mulligan auf der ersten Hand", "prop", False, [
            prop(d["results"][label]["mulligan"]["first_any"], d["results"][label]["mulligan"]["deals"]) for d in decks]))
        rows.append(("Spiel verloren (Mulligan)", "prop", False, [
            prop(d["results"][label]["mulligan"]["lost"], d["results"][label]["mulligan"]["deals"]) for d in decks]))
    for t in range(1, T + 1):
        rows.append((f"Zauber gespielt in Runde {t}", "prop", True, [
            prop(d["results"][label]["cast"][t], sims) for d in decks]))
    rows.append((f"Mana Screw nach Runde {T}", "prop", False, [
        prop(round(d["results"][label]["any_screw"] * sims), sims) for d in decks]))
    rows.append((f"Flood ({args.flood}+ Länder bis Runde {max(args.max_runden, T, C)})",
                 "prop", False, [prop(round(d["results"][label]["flood"] * sims), sims) for d in decks]))
    rows.append((f"Kreaturen auf dem Feld nach Runde {T}", "mean", True, [
        mean(d["results"][label]["samples"]["creatures"]) for d in decks]))
    rows.append((f"Gesamt-Power nach Runde {T}", "mean", True, [
        mean(d["results"][label]["samples"]["power"]) for d in decks]))
    rows.append((f"Curve-Auslastung Runde 1–{C} (Mana genutzt)", "prop", True, [
        None if not d["results"][label]["samples"]["util"] else
        (lambda r: (r[0], Z95 * r[1] ** 0.5, r[1]))(mean_var_of_mean(d["results"][label]["samples"]["util"])) for d in decks]))
    for x in (5, 7):
        rows.append((f"{args.schaden} Schaden bis Runde {x}", "prop", True, [
            prop(sum(1 for v in d["results"][label]["dmg"] if v <= x), sims) for d in decks]))
    rows.append((f"Ø Runde für {args.schaden} Schaden", "mean", False, [
        mean(d["results"][label]["dmg"]) if d["results"][label]["dmg"] else None for d in decks]))
    if any(d["results"][label]["jace"]["on"] for d in decks):
        rows.append(("Jace-Aktivierungen bis Hand leer (Ø)", "mean", True, [
            mean(d["results"][label]["samples"]["jace"]) if d["results"][label]["jace"]["on"] else None for d in decks]))
    return rows
