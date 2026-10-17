"""Simulation eines Spiels: Zauber- und Landauswahl, Landcycling, Spielablauf und Statistik-Sammlung."""
import itertools
import random
from collections import Counter

from components.cards import enters_tapped
from components.jace import (JaceState, cast_filter_matches, creates_jace, creates_walker, enter_filter_matches,
                             once_effects, recurring_effects, surveil)
from components.mana import can_cast_all, can_pay, has_two_colors, land_key
from components.mulligan import deal_opening


def aura_ok(chosen, has_creature, auras_need_creature):
    if not auras_need_creature or has_creature:
        return True
    return not (any(c.is_aura for c in chosen) and not any(c.is_creature for c in chosen))


def play_score(chosen):
    """Bewertung einer Zauber-Kombination (hoeher ist besser, in dieser Reihenfolge):
    1. ausgegebenes Mana  2. Zahl der Kreaturen  3. Power + Toughness  4. Zahl der Karten
    5. weniger Prepared-Kopien (bei Gleichstand zuerst Handkarten, die Kopie bleibt verfuegbar)."""
    return (sum(c.mv for c in chosen),
            sum(c.is_creature for c in chosen),
            sum(c.power + c.toughness for c in chosen),
            len(chosen),
            -sum(c.is_copy for c in chosen))


def best_cast(spells, key, has_creature, auras_need_creature, must=None, fixed=()):
    """Waehlt die Zauber, die in dieser Runde zusammen gespielt werden:
    maximal ausgegebenes Mana, dann mehr Kreaturen, dann mehr Power+Toughness.
    must: Karte, die auf jeden Fall dabei sein muss (z. B. ein Zauber, der vor dem Land einen Planeswalker
    erschafft). Ist sie nicht bezahlbar, kommt (-1, 0, 0, 0), [] zurueck.
    fixed: in dieser Runde schon gewirkte Zauber (nicht in spells). Sie belegen Mana und zaehlen im Score mit,
    stehen aber nicht in der zurueckgegebenen Liste."""
    spells = sorted(spells)
    base = list(fixed)
    if must is not None:
        if must not in spells or not can_cast_all((must.alts,), key):
            return (-1, 0, 0, 0), []
        spells.remove(must)
        base.append(must)
    n = len(spells)
    allcards = base + spells

    # Abkuerzung: passt die komplette Hand, wird alles gespielt
    if allcards and can_cast_all(tuple(sorted(c.alts for c in allcards)), key) \
            and aura_ok(allcards, has_creature, auras_need_creature):
        return play_score(allcards), allcards[len(fixed):]

    best = [(-1, 0, 0, 0), []]

    def dfs(i, chosen):
        if i == n:
            if aura_ok(chosen, has_creature, auras_need_creature):
                s = play_score(chosen)
                if s > best[0]:
                    best[0], best[1] = s, chosen
            return
        cand = chosen + [spells[i]]
        if can_cast_all(tuple(sorted(c.alts for c in cand)), key):
            dfs(i + 1, cand)
        j = i + 1
        while j < n and spells[j] == spells[i]:  # gleiche Karten nicht doppelt durchprobieren
            j += 1
        dfs(j, chosen)

    dfs(0, list(base))
    return best[0], best[1][len(fixed):]


ANY_COLOR = ("B", "G", "R", "U", "W")


def usable_now(card):
    """Liefert eine Manaquelle schon in der Runde, in der sie ins Spiel kommt (Nichtkreatur oder Haste)?"""
    return bool(card.mana_src) and (not card.is_creature or card.haste)


def mana_units(perms, turn):
    """Mana aus Manaquellen in dieser Runde: [(Farbtupel, Index in perms oder None)].
    Kreaturen erst ab der Runde nach dem Wirken (ausser Haste); der Index ist nur bei Kreaturen gesetzt."""
    out = []
    for i, (card, t_in) in enumerate(perms):
        if card.is_creature and not (t_in < turn or card.haste):
            continue
        out += [(u, i if card.is_creature else None) for u in card.mana_src]
    return out


def tapped_for_mana(alts_list, other_pool, creature_units, creatures):
    """Welche Kreaturen muessen fuer Mana getappt werden, damit alle Zauber (alts_list) bezahlt sind?
    other_pool: Mana aus Laendern, Artefakten und Treasure; creature_units: [(Farbtupel, Index)]; creatures[Index]:
    die Kreatur. Zuerst wird auf die staerksten Kreaturen verzichtet (sie sollen angreifen). Gibt {Index} zurueck."""
    if not alts_list or not creature_units:
        return set()
    need = tuple(sorted(alts_list))
    keep = {i for _u, i in creature_units}
    for i in sorted(keep, key=lambda i: (-creatures[i].power, i)):
        trial = keep - {i}
        pool = list(other_pool) + [u for u, j in creature_units if j in trial]
        if can_cast_all(need, land_key(pool)):
            keep = trial
    return keep


def use_treasures(spells, pool, treasures, has_creature, auras_need_creature):
    """Treasure nur einsetzen, wenn er in dieser Runde mehr ermoeglicht: kleinste Zahl k, mit der die beste
    Kombination erreicht wird. Gibt (k, gewaehlte Zauber) zurueck; k = 0, wenn Treasure nichts bringt."""
    base_score, base = best_cast(spells, land_key(pool), has_creature, auras_need_creature)
    best = (base_score, 0, base)
    for k in range(1, treasures + 1):
        sc, ch = best_cast(spells, land_key(list(pool) + [ANY_COLOR] * k), has_creature, auras_need_creature)
        if sc > best[0]:
            best = (sc, k, ch)
    return best[1], best[2]


def enters_prepared(cards):
    """Kopien der Zauberhaelften von Kreaturen, die prepared ins Spiel kommen."""
    return [c.prepared[1] for c in cards if c.prepared and c.prepared[0] in ("enters", "both")]


def resolve_draws(hand, library, chosen, pool, battlefield, land_played, has_creature, auras_need_creature,
                  walker_bf, jace_bf, copies=()):
    """Draw-Zauber (und Kreaturen, die beim Betreten ziehen) nach dem Zaubern abhandeln: die Karten kommen sofort auf
    die Hand. Ist der Landdrop noch frei, wird ein gezogenes Land gelegt (wie choose_land: meistes Mana in Zauber,
    dann getappt zuerst, dann mehr Farben). Mit dem uebrigen Mana wird weiter gezaubert, auch weitere Draw-Zauber.
    hand enthaelt die gewirkten Karten noch (sie werden spaeter entfernt); pool: untappte Laender vor dem Zaubern.
    Veraendert hand, library und battlefield. Gibt {chosen, land, tapped, pool, drawn, used} zurueck:
    chosen = alle gewirkten Zauber der Runde, land = nachgeholter Landdrop (sonst None), drawn = gezogene Karten,
    used = danach zusaetzlich gelegte Laender und gewirkte Zauber.
    Prepared: Kommt eine Kreatur prepared ins Spiel, kann ihre Kopie mit dem uebrigen Mana noch in dieser Runde
    gewirkt werden. copies: Kopien, die schon zu Rundenbeginn verfuegbar waren."""
    cast, pool = list(chosen), list(pool)
    land, tapped = None, False
    drawn = used = 0
    pending = sum(c.draws for c in cast)
    fresh = enters_prepared(cast)
    new_mana = [u for c in cast if usable_now(c) for u in c.mana_src]
    mana_added = 0
    while pending or fresh or new_mana:
        pool += new_mana
        mana_added += len(new_mana)
        for _ in range(pending):
            if not library:
                break
            hand.append(library.pop(0))
            drawn += 1
        left = Counter(c for c in hand if not c.is_land)
        left.subtract(Counter(c for c in cast if not c.is_copy))
        avail = Counter(copies) + Counter(enters_prepared(cast))
        avail.subtract(Counter(c for c in cast if c.is_copy))
        spells_left = sorted((+left + +avail).elements())
        hc = has_creature or any(c.is_creature for c in cast)
        options = sorted({c for c in hand if c.is_land})
        if land_played is None and land is None and options:
            walker = walker_bf or any(creates_walker(c) for c in cast)
            jace = jace_bf or any(creates_jace(c) for c in cast) or any(c.is_jace for c in hand)
            bf_cols = [c.land_colors for c in battlefield]

            def score(option):
                t = enters_tapped(option, battlefield, walker=walker, jace=jace)
                sc = best_cast(spells_left, land_key(pool + ([] if t else [option.land_colors])), hc,
                               auras_need_creature, fixed=cast)[0]
                return sc, t, len(set().union(*(bf_cols + [option.land_colors])))

            land = max(options, key=score)
            tapped = enters_tapped(land, battlefield, walker=walker, jace=jace)
            hand.remove(land)
            battlefield.append(land)
            used += 1
            if not tapped:
                pool.append(land.land_colors)
        _, extra = best_cast(spells_left, land_key(pool), hc, auras_need_creature, fixed=cast)
        cast += extra
        used += len(extra)
        pending = sum(c.draws for c in extra)
        fresh = enters_prepared(extra)
        new_mana = [u for c in extra if usable_now(c) for u in c.mana_src]
    return {"chosen": cast, "land": land, "tapped": tapped, "pool": pool, "drawn": drawn, "used": used,
            "mana_added": mana_added}


def apply_surveils(amounts, library, hand, battlefield, graveyard=None):
    """Surveil durch Karten: je Quelle Surveil N nacheinander (Entscheidung wie bei Jace, siehe jace.surveil).
    Gibt (Zahl der Surveils, abgelegte Laender) zurueck; ein Surveil mit leerer Bibliothek zaehlt nicht.
    graveyard: Liste, in die die abgelegten Karten kommen (Friedhof der Simulation)."""
    events = lands = 0
    for n in amounts:
        if not library or n <= 0:
            continue
        events += 1
        binned = surveil(library, n, hand, battlefield)
        lands += sum(c.is_land for c in binned)
        if graveyard is not None:
            graveyard.extend(binned)
    return events, lands


def _attacks(entry, turn):
    card, t_in = entry
    return not card.defender and (t_in < turn or card.haste)


def _power(board, bonus, pump, i):
    return board[i][0].power + bonus[i] + pump.get(i, 0)


def _ranked(board, bonus, pump, turn, attackers_only):
    """Indizes der Kreaturen, staerkste zuerst; Angreifer dieser Runde vor den uebrigen."""
    idx = [i for i in range(len(board)) if not attackers_only or _attacks(board[i], turn)]
    return sorted(idx, key=lambda i: (not _attacks(board[i], turn), -_power(board, bonus, pump, i), i))


def _run_mode(mode, board, bonus, pump, turn):
    """Wendet einen Modus an (veraendert bonus und pump). Gibt (Schaden in dieser Runde, Schaden an den Gegner,
    gelegte Marken) zurueck."""
    gain = face = counters = 0
    for atom in mode:
        kind = atom[0]
        if kind == "face":
            face += atom[1]
        elif kind == "counter":
            for i in _ranked(board, bonus, pump, turn, False)[:atom[2]]:
                bonus[i] += atom[1]
                counters += atom[1]
                gain += atom[1] if _attacks(board[i], turn) else 0
        elif kind == "counter_all":
            for i in range(len(board)):
                bonus[i] += atom[1]
                counters += atom[1]
                gain += atom[1] if _attacks(board[i], turn) else 0
        elif kind == "pump":
            best = _ranked(board, bonus, pump, turn, True)[:1]
            for i in best:
                pump[i] = pump.get(i, 0) + atom[1]
                gain += atom[1]
        elif kind == "pump_all":
            for i in _ranked(board, bonus, pump, turn, True):
                pump[i] = pump.get(i, 0) + atom[1]
                gain += atom[1]
    return gain, face, counters


def apply_effects(card, board, bonus, pump, turn):
    """Effekte einer gewirkten Karte (Card.modes): Schaden an den Gegner, +1/+1-Marken (dauerhaft, bonus) und
    Pumps bis Rundenende (pump). Ziel ist die staerkste Kreatur, die in dieser Runde angreift; dauerhafte Marken ohne
    Angreifer gehen an die staerkste Kreatur, Pumps ohne Angreifer verpuffen. Modale Karten: der Modus mit dem meisten
    Schaden in dieser Runde, bei Gleichstand der mit dauerhaften Marken.
    Gibt {"damage": zusaetzlicher Angriffsschaden, "face": Schaden an den Gegner, "counters": gelegte Marken} zurueck."""
    if not card.modes:
        return {"damage": 0, "face": 0, "counters": 0}
    best = None
    for k, mode in enumerate(card.modes):
        b, p = list(bonus), dict(pump)
        gain, face, counters = _run_mode(mode, board, b, p, turn)
        key = (gain + face, counters, -k)
        if best is None or key > best[0]:
            best = (key, mode)
    gain, face, counters = _run_mode(best[1], board, bonus, pump, turn)
    return {"damage": gain, "face": face, "counters": counters}


def landfall_effects(land, board, bonus, turn, with_mana=True):
    """Landfall der Kreaturen auf dem Feld (Card.landfall): Schaden an den Gegner, Mana (Mountain, nur wenn with_mana)
    und Marken bei bestimmten Landtypen. Gibt (Schaden an den Gegner, [Farbtupel], Marken) zurueck."""
    face, mana, counters = 0, [], 0
    for c, _t in list(board):
        for atom in c.landfall:
            if atom[0] == "face":
                face += atom[1]
            elif atom[0] == "mountain_mana" and with_mana and "mountain" in land.land_types:
                mana.append((atom[1],))
            elif atom[0] == "type_counter" and atom[1] in land.land_types:
                for i in _ranked(board, bonus, {}, turn, False)[:1]:
                    bonus[i] += atom[2]
                    counters += atom[2]
    return face, mana, counters


def choose_land(hand, spells, pool, battlefield, walker_bf, jace_bf, has_creature, auras_need_creature):
    """Waehlt das Land dieser Runde. Gibt (Land, getappt, vorab) zurueck.
    Laender mit Planeswalker- oder Jace-Bedingung kommen untapped, wenn die Bedingung erfuellt ist. Ist sie es nicht,
    wird zuerst ein Zauber gewirkt, der einen Planeswalker (bzw. Jace) erschafft, und danach das Land gelegt:
    'vorab' ist dieser Zauber (bezahlt mit den schon liegenden Laendern), sonst None.
    walker_bf / jace_bf: Planeswalker bzw. Jace liegt auf dem Tisch (Token oder Karte; Tokens nie auf der Hand).
    Eine Jace-Karte auf der Hand genuegt fuer 'behold a Jace' (sie wird nur gezeigt, nicht gewirkt)."""
    options = sorted({c for c in hand if c.is_land})
    if not options:
        return None, False, None
    jace_hand = any(c.is_jace for c in hand)
    key_now = land_key(pool)
    enablers = sorted({c for c in spells if creates_walker(c) and can_cast_all((c.alts,), key_now)})
    jace_enablers = [c for c in enablers if creates_jace(c)]
    bf_cols = [c.land_colors for c in battlefield]

    def status(land):
        """(getappt, moegliche Vorab-Zauber)"""
        if land.tap_mode == "planeswalker":
            if walker_bf:
                return False, []
            return (False, enablers) if enablers else (True, [])
        if land.tap_mode == "jace":
            if jace_bf or jace_hand:
                return False, []
            return (False, jace_enablers) if jace_enablers else (True, [])
        return enters_tapped(land, battlefield), []

    def best_with(land, tapped, musts):
        """(Score, Index des besten Vorab-Zaubers) fuer dieses Land."""
        key = land_key(pool + ([] if tapped else [land.land_colors]))
        if not musts:
            return best_cast(spells, key, has_creature, auras_need_creature)[0], 0
        scored = [(best_cast(spells, key, has_creature, auras_need_creature, must=m)[0], -i)
                  for i, m in enumerate(musts)]
        score_, neg_i = max(scored)
        return score_, -neg_i

    def score(land):
        tapped, musts = status(land)
        spent, _ = best_with(land, tapped, musts)
        # gleich viel Mana ausgegeben -> getapptes Land bevorzugt jetzt legen
        return (spent, tapped, len(set().union(*(bf_cols + [land.land_colors]))))

    land = max(options, key=score)
    tapped, musts = status(land)
    forced = None
    if musts:
        _, idx = best_with(land, tapped, musts)
        forced = musts[idx]
    return land, tapped, forced


def top_card_playable(card, spells, key, has_creature, auras_need_creature):
    """Ist die Top Card mit den aktuellen Laendern spielbar (Aura-Regel beachtet)?"""
    if not can_cast_all((card.alts,), key):
        return False
    if card.is_aura and auras_need_creature and not has_creature:
        return any(c.is_creature and can_cast_all(tuple(sorted((card.alts, c.alts))), key)
                   for c in spells)
    return True


def pay_subsets(pool, alts):
    """Alle Moeglichkeiten, die Kosten aus den Laendern zu bezahlen. Gibt die uebrig bleibenden
    Laender (Liste von Farbtupeln) zurueck, ohne doppelte Restmengen."""
    seen, out = set(), []
    for generic, req in alts:
        req_c = Counter(dict(req))
        need = generic + sum(req_c.values())
        if need > len(pool):
            continue
        for idx in itertools.combinations(range(len(pool)), need):
            if not can_pay([pool[k] for k in idx if pool[k]], generic, req_c):
                continue
            rest = [pool[k] for k in range(len(pool)) if k not in idx]
            sig = tuple(sorted(rest))
            if sig not in seen:
                seen.add(sig)
                out.append(rest)
    return out


def fits_target(land, target):
    if target == "basic":
        return land.is_basic
    if target == "land":
        return True
    return target in land.land_types


def without_many(items, remove):
    out = list(items)
    for r_ in remove:
        out.remove(r_)
    return out


def value_next(spells_next, bf_cols, bf_cards, lands_hand, has_creature, auras_need_creature):
    """Bestes Ergebnis der naechsten Runde: welches der Haendelaender man legt und was man damit spielen kann."""
    options = sorted(set(lands_hand))
    if not options:
        return best_cast(spells_next, land_key(bf_cols), has_creature, auras_need_creature)[0]
    best = None
    for land in options:
        cols = bf_cols + ([] if enters_tapped(land, bf_cards) else [land.land_colors])
        sc, _ = best_cast(spells_next, land_key(cols), has_creature, auras_need_creature)
        if best is None or sc > best:
            best = sc
    return best


def plan_cycle(cycler, pool, spells, battlefield, library, hand_lands, land_open, has_creature,
               auras_need_creature, base=None):
    """Plant das Landcycling: womit bezahlt wird und welches Land geholt wird.
    Bewertet wird mit Vorausschau: Mana-Nutzung in DIESER Runde, was man in der NAECHSTEN Runde
    spielen kann (inkl. Farben) und wie viele Landdrops gesichert sind.
    base=(Score, gewaehlte Zauber) ohne Cycling: dann wird nur gecycelt, wenn es sich lohnt,
    die geplanten Zauber dieser Runde nicht schlechter werden und die Karte nicht naechste Runde
    ohnehin spielbar waere. base=None (Regel 'Land fehlt'): Cycling ist Pflicht, nur das Land wird gewaehlt."""
    spells_wo = without_one(spells, cycler)
    cands = sorted({c for c in library if c.is_land and fits_target(c, cycler.cycle_target)})
    if not cands:
        return None
    rems = pay_subsets(pool, cycler.cycle_alts)
    if not rems:
        return None
    bf_cols = [c.land_colors for c in battlefield]
    have_colors = set().union(*bf_cols) if bf_cols else set()

    base_key = None
    if base is not None:
        s0, ch0 = base
        hc0 = has_creature or any(c.is_creature for c in ch0)
        nxt0 = value_next(without_many(spells, ch0), bf_cols, battlefield, hand_lands, hc0, auras_need_creature)
        base_key = (s0, nxt0, min(2, len(hand_lands)))

    best = None
    for rem in rems:
        for cand in cands:
            tapped = land_open and enters_tapped(cand, battlefield)
            avail = rem + ([cand.land_colors] if land_open and not tapped else [])
            sc, ch = best_cast(spells_wo, land_key(avail), has_creature, auras_need_creature)
            if base is not None and sc < base[0]:
                continue  # geplante Zauber duerfen nicht schlechter werden
            bf_after = battlefield + ([cand] if land_open else [])
            cols_after = bf_cols + ([cand.land_colors] if land_open else [])
            lands_next = [] if land_open else hand_lands + [cand]
            hc = has_creature or any(c.is_creature for c in ch)
            nxt = value_next(without_many(spells_wo, ch), cols_after, bf_after, lands_next, hc, auras_need_creature)
            cover = (1 if land_open else 0) + min(2, len(lands_next))
            demand = sum(1 for sp in spells_wo
                         if any(col in (set(cand.land_colors) - have_colors)
                                for _, req in sp.alts for col, _ in req))
            ncol = len(set().union(*(bf_cols + [cand.land_colors])))
            deficit = -sum(1 for lc in bf_cols if set(lc) & set(cand.land_colors))
            k = (sc, nxt, cover, demand, ncol, deficit)
            if best is None or k > best[0]:
                best = (k, rem, cand)
    if best is None:
        return None
    if base_key is not None and best[0][:3] <= base_key:
        return None  # Cycling bringt nichts -> Karte behalten
    return best[1], best[2]


def do_cycle(hand, library, cycler, cand, graveyard=None):
    """Fuehrt das Landcycling aus: Karte weg (in den Friedhof, falls graveyard), Land aus dem Deck auf die Hand, Deck
    mischen. Gibt die Chance auf ein Nicht-Land im naechsten Zug vor und nach dem Cycling zurueck."""
    if graveyard is not None:
        graveyard.append(cycler)
    n = len(library)
    lands = sum(c.is_land for c in library)
    p_before = (n - lands) / n if n else 0.0
    hand.remove(cycler)
    library.remove(cand)
    random.shuffle(library)
    hand.append(cand)
    n2 = n - 1
    p_after = (n2 - (lands - 1)) / n2 if n2 > 0 else p_before
    return p_before, p_after


def without_one(items, item):
    out = list(items)
    out.remove(item)
    return out


def simulate(cards, sims, on_draw, max_turn, horizon, auras_need_creature, multicolor, top_mv,
             flood_lands=11, dmg_target=20, curve_turns=6,
             cycle_on=True, cycle_turns=3, cycle_cap=6, cycle_last=False, mulligan=True, min_hand=5,
             jace_on=True, color_check=None, track=None):
    """track: Kartennamen, deren Spielbarkeit gemessen wird (Splash-Karten): erstmals auf der Hand, erstmals bezahlbar
    (nach dem Landdrop), gewirkt. Die Messung veraendert den Spielablauf nicht.
    color_check: {"colors": [...], "checks": [{"color", "k", "turn", "cards"}]} misst, wie oft bis Runde 3 jede
    Deckfarbe mindestens eine Quelle hat und fuer jede Pruefung (siehe mana.pip_checks) bis zu ihrer Runde mindestens k
    Quellen der Farbe. Quellen: Laender auf dem Feld (auch getappt) und Manaquellen, die in der Runde Mana liefern
    (Kreaturen ab der Folgerunde, Artefakte sofort); Treasure zaehlen nicht. Die Messung veraendert den Spielablauf
    nicht."""
    cast_in_turn = {t: 0 for t in range(1, max_turn + 1)}
    cc_colors = list(color_check["colors"]) if color_check else []
    cc_checks = [dict(ch, ok=0) for ch in (color_check.get("checks") or [])] if color_check else []
    cc_turns = {3} | {ch["turn"] for ch in cc_checks}
    cc_t3 = {c: 0 for c in cc_colors}
    cc_all = 0
    opener_lands = n_creatures = power = toughness = 0
    land_screw = color_screw = any_screw = 0
    empty_hand, empty_spells, top_turns = [], [], []
    flooded = lands_drawn_total = 0
    dmg_turns = []
    best_lethal = None
    curve_avail = {t: 0 for t in range(1, curve_turns + 1)}  # verfuegbares Mana (Summe ueber alle Spiele)
    curve_spent = {t: 0 for t in range(1, curve_turns + 1)}  # ausgegebenes Mana
    curve_full = {t: 0 for t in range(1, curve_turns + 1)}   # Spiele, in denen alles Mana genutzt wurde
    curve_games = {t: 0 for t in range(1, curve_turns + 1)}  # Spiele mit mindestens 1 Mana
    cyc = {"games": 0, "events": 0, "reason": Counter(), "card": Counter(),
           "p_before": 0.0, "p_after": 0.0, "first": []}
    has_cyclers = cycle_on and any(c.cycle_alts for c in cards)
    mull = {"on": mulligan, "min_hand": min_hand, "deals": 0, "lost": 0, "sizes": Counter(),
            "first_any": 0, "first": Counter()}
    played, max_deals = 0, sims * 50 + 1000
    has_jace = jace_on and any(once_effects(c) or recurring_effects(c) for c in cards)
    samples = {"creatures": [], "power": [], "toughness": [], "util": [], "jace": []}  # je gespieltes Spiel
    has_draws = any(c.draws for c in cards)
    has_surveil = any(c.surveil for c in cards)
    has_prepared = any(c.prepared for c in cards)
    has_ramp = any(c.mana_src or c.treasure for c in cards)
    ef = {"face": 0, "counters": 0, "pump": 0}
    GY_TURNS = (3, 5, 8)
    gys = {"size": {t: 0 for t in GY_TURNS}, "max_mv": {t: 0 for t in GY_TURNS}, "n": {t: 0 for t in GY_TURNS},
           "x": []}
    rp = {"games": 0, "first": [], "extra": {t: 0 for t in range(1, curve_turns + 1)}, "held": 0, "made": 0,
          "used": 0}
    track = set(track or ())
    track_mv = {c.name: c.mv for c in cards if c.name in track}
    sc_stats = {n: {"games": 0, "drawn": 0, "castable": 0, "on_time": 0, "cast": 0, "wait_sum": 0} for n in track}
    pr = {"copies": 0, "games": 0, "mana": 0}
    sv = {"events": 0, "games": 0, "lands": 0}
    dr = {"cards": 0, "games": 0, "used": 0}
    jc = {"on": has_jace, "games_any": 0, "acts_win": 0, "gained_win": 0, "dist_win": Counter(),
          "acts_all": 0, "surveil_all": 0, "surveil_lands_all": 0, "gained_all": 0, "dist_all": Counter(), "first": [], "empty_reached": 0}

    while played < sims:
        mull["deals"] += 1
        if mull["deals"] > max_deals:
            raise RuntimeError(f"Fast jede Starthand fuehrt zum Mulligan: nur {played} von {sims} Spielen "
                               f"wurden gespielt. Das Deck ist mit diesen Mulligan-Regeln praktisch unspielbar.")
        hand, library, mulls, first_reasons = deal_opening(cards, mulligan, min_hand)
        if first_reasons:
            mull["first_any"] += 1
            for r_ in set(first_reasons):
                mull["first"][r_] += 1
        if hand is None:
            mull["lost"] += 1
            continue  # Spiel durch Mulligan verloren: wird nicht gespielt
        played += 1
        mull["sizes"][len(hand)] += 1
        opening = hand[:]
        opener_lands += sum(c.is_land for c in hand)
        battlefield, board = [], []  # gelegte Laender / gespielte Kreaturen (Karte, Runde)
        hand_done = spells_done = top_done = dmg_done = False
        dmg_total = 0
        log = []
        game_events = []
        jst = JaceState()
        perms = []  # Permanents mit wiederkehrendem Empower: (Karte, Runde des Eintritts)
        walkers = []  # gewirkte Planeswalker-Karten (liegen auf dem Tisch)
        acts_empty = gained_empty = None
        snap = (0, 0, 0)
        g_avail = g_spent = 0
        g_drawn = g_surveils = g_copies = 0
        mana_perms, treasures, ramp_first = [], 0, None  # Manaquellen auf dem Feld (Karte, Runde), Treasure-Token
        prep = []  # Prepared-Kreaturen auf dem Feld: [Karte, prepared?]
        bonus = []  # dauerhafte +1/+1-Marken je Kreatur auf dem Feld (gleiche Reihenfolge wie board)
        gy = []     # Friedhof: gewirkte Instants/Sorceries, gelandcycelte Karten, durch Surveil abgelegte Karten
        jst.graveyard = gy
        t_hand, t_ok, t_cast = {}, {}, set()  # Splash-Karten: erste Runde auf der Hand / bezahlbar, gewirkt

        for turn in range(1, horizon + 1):
            drew = None
            if turn > 1 or on_draw:
                if not library:
                    break
                drew = library.pop(0)
                hand.append(drew)
            jst.used = False
            events0 = jst.events
            pump, face_now, landfall_done = {}, 0, False
            for p_ in prep:  # Upkeep: "if this creature isn't prepared, it becomes prepared"
                if p_[0].prepared[0] in ("upkeep", "both"):
                    p_[1] = True
            turn_acts0, turn_gain0 = jst.acts, jst.gained
            if has_jace:
                for pc, t_in in perms:
                    if t_in < turn:
                        for e in recurring_effects(pc):
                            if e[1] == "trigger" and e[3] == "turn":
                                jst.add(e[2])
                jst.try_activate(hand, library, turn)  # Loyalty aus frueheren Runden: Karte vor dem Landdrop ziehen
            pool = [c.land_colors for c in battlefield]      # zu Rundenbeginn sind alle Laender untapped
            avail_total = sum(1 for lc in pool if lc)         # Mana dieser Runde (inkl. neu gelegter Laender)
            units = mana_units(mana_perms, turn) if has_ramp else []
            creature_units = [(u, i) for u, i in units if i is not None]
            pool = pool + [u for u, _i in units]              # Manaquellen wie zusaetzliche Laender
            avail_total += len(units)
            extra_now = len(units)
            cycle_spent = 0
            cycled_log = []
            def castable():  # Handkarten und verfuegbare Prepared-Kopien
                return [c for c in hand if not c.is_land] + [p_[0].prepared[1] for p_ in prep if p_[1]]

            spells = castable()
            has_creature = bool(board)

            # Landcycling Regel 2: kein Land auf der Hand -> Land per Landcycling sichern
            if has_cyclers and turn <= cycle_turns and not any(c.is_land for c in hand):
                for cycler in sorted({c for c in spells if c.cycle_alts}, key=lambda c: (c.cycle_mv, c)):
                    if not cycle_last and len(spells) <= 1:
                        continue  # letzte Karte auf der Hand: nicht wegwerfen
                    plan = plan_cycle(cycler, pool, spells, battlefield, library, [],
                                      True, has_creature, auras_need_creature)
                    if plan:
                        rem, cand = plan
                        pb, pa = do_cycle(hand, library, cycler, cand, graveyard=gy)
                        game_events.append((turn, "Land fehlt", cycler.name, pb, pa))
                        cycled_log.append((cycler, "Land fehlt"))
                        cycle_spent += cycler.cycle_mv
                        pool = rem
                        spells = castable()
                        break

            # Land legen (getappte Laender liefern in dieser Runde kein Mana). Planeswalker-/Jace-Laender: erst ein
            # Zauber, der einen Planeswalker erschafft (falls moeglich), dann das Land (siehe choose_land)
            walker_bf = jst.loyalty > 0 or bool(walkers)
            jace_bf = jst.loyalty > 0 or any(c.is_jace for c in walkers)
            land_played, tapped_now, forced = choose_land(hand, spells, pool, battlefield, walker_bf, jace_bf,
                                                          has_creature, auras_need_creature)
            if land_played is not None:
                hand.remove(land_played)
                battlefield.append(land_played)
                if not tapped_now:
                    pool = pool + [land_played.land_colors]
                    if land_played.land_colors:
                        avail_total += 1
                if board:  # Landfall (z. B. Koth): Schaden, Mana bei Mountain, Marken
                    f_, mana_, c_ = landfall_effects(land_played, board, bonus, turn)
                    face_now += f_
                    ef["counters"] += c_
                    pool = pool + mana_
                    avail_total += len(mana_)
                landfall_done = True
            key = land_key(pool)
            full_key = land_key([c.land_colors for c in battlefield])

            if track:  # Splash-Karten: auf der Hand und mit den Laendern dieser Runde bezahlbar?
                for c in hand:
                    if c.name in track:
                        t_hand.setdefault(c.name, turn)
                        if c.name not in t_ok and can_cast_all((c.alts,), key):
                            t_ok[c.name] = turn

            # Top Card gezogen und spielbar?
            if not top_done and top_mv is not None:
                for c in set(x for x in spells if x.mv == top_mv and x.alts and not x.is_copy):
                    if top_card_playable(c, spells, key, has_creature, auras_need_creature):
                        top_turns.append(turn)
                        top_done = True
                        break

            s_chosen, chosen = best_cast(spells, key, has_creature, auras_need_creature, must=forced)
            if treasures and forced is None:  # Treasure nur, wenn er diese Runde mehr ermoeglicht
                k_t, ch_t = use_treasures(spells, pool, treasures, has_creature, auras_need_creature)
                if k_t:
                    treasures -= k_t
                    rp["used"] += k_t
                    pool = pool + [ANY_COLOR] * k_t
                    avail_total += k_t
                    extra_now += k_t
                    key = land_key(pool)
                    s_chosen, chosen = best_cast(spells, key, has_creature, auras_need_creature)

            # Landcycling Regel 1: Karte ist diesmal nicht spielbar -> mit uebrigem Mana cyceln.
            # Entfaellt in Runden, in denen ein Zauber vor dem Land gewirkt wurde (Bezahlung sonst nicht gesichert).
            if has_cyclers and forced is None:
                for _round in range(3):
                    if len(battlefield) + sum(c.is_land for c in hand) >= cycle_cap:
                        break
                    left = Counter(spells)
                    left.subtract(Counter(chosen))
                    cands = sorted((c for c, k in left.items() if k > 0 and c.cycle_alts),
                                   key=lambda c: (c.cycle_mv, c))
                    done = False
                    for cycler in cands:
                        if not cycle_last:
                            rest = left.copy()
                            rest[cycler] -= 1
                            if not any(k > 0 for k in rest.values()):
                                continue  # waere die letzte Karte auf der Hand: nicht wegwerfen
                        plan = plan_cycle(cycler, pool, spells, battlefield, library,
                                          [c for c in hand if c.is_land], land_played is None,
                                          has_creature, auras_need_creature, base=(s_chosen, chosen))
                        if not plan:
                            continue
                        rem, cand = plan
                        pb, pa = do_cycle(hand, library, cycler, cand, graveyard=gy)
                        game_events.append((turn, "Karte nicht spielbar", cycler.name, pb, pa))
                        cycled_log.append((cycler, "Karte nicht spielbar"))
                        cycle_spent += cycler.cycle_mv
                        pool = rem
                        if land_played is None:  # Landdrop noch frei -> geholtes Land sofort legen
                            land_played = cand
                            tapped_now = enters_tapped(cand, battlefield)
                            hand.remove(cand)
                            battlefield.append(cand)
                            if not tapped_now:
                                pool = pool + [cand.land_colors]
                                if cand.land_colors:
                                    avail_total += 1
                        spells = castable()
                        key = land_key(pool)
                        full_key = land_key([c.land_colors for c in battlefield])
                        s_chosen, chosen = best_cast(spells, key, has_creature, auras_need_creature)
                        done = True
                        break
                    if not done:
                        break

            drawn_now = 0
            if (has_draws or has_prepared or has_ramp) and (any(c.draws for c in chosen) or enters_prepared(chosen)
                                                             or any(usable_now(c) for c in chosen)):
                rd = resolve_draws(hand, library, chosen, pool, battlefield, land_played, has_creature,
                                   auras_need_creature, jst.loyalty > 0 or bool(walkers),
                                   jst.loyalty > 0 or any(c.is_jace for c in walkers),
                                   copies=[p_[0].prepared[1] for p_ in prep if p_[1]])
                chosen, pool, drawn_now = rd["chosen"], rd["pool"], rd["drawn"]
                avail_total += rd["mana_added"]
                extra_now += rd["mana_added"]
                if rd["land"] is not None:
                    land_played, tapped_now = rd["land"], rd["tapped"]
                    if not tapped_now and land_played.land_colors:
                        avail_total += 1
                key = land_key(pool)
                full_key = land_key([c.land_colors for c in battlefield])
                g_drawn += drawn_now
                dr["used"] += rd["used"]

            if has_jace and land_played is not None:
                for e in once_effects(land_played):
                    if e[1] == "etb":
                        jst.add(e[2])
                for pc, _t in perms:
                    for e in recurring_effects(pc):
                        if e[1] == "trigger" and e[3].startswith("enter:") and enter_filter_matches(e[3][6:], land_played):
                            jst.add(e[2])
                if recurring_effects(land_played):
                    perms.append((land_played, turn))

            for c in chosen:
                if c.is_copy:
                    continue
                hand.remove(c)
                if c.is_creature:
                    board.append((c, turn))
                    bonus.append(0)
                if c.is_instant_sorcery:
                    gy.append(c)  # gewirkte Instants und Sorceries kommen in den Friedhof
                if c.gy_x:  # Hapatra: hoechster Manawert im Friedhof
                    gys["x"].append(max((g.mv for g in gy), default=0))
                if c.is_planeswalker:
                    walkers.append(c)
                if c.prepared:
                    prep.append([c, c.prepared[0] in ("enters", "both")])
                if c.mana_src:
                    mana_perms.append((c, turn))
                if c.treasure:
                    treasures += c.treasure
                    rp["made"] += c.treasure
            for c in chosen:
                if c.is_copy:  # Kopie gewirkt: eine passende Kreatur ist nicht mehr prepared
                    p_ = next(p_ for p_ in prep if p_[1] and p_[0].prepared[1] == c)
                    p_[1] = False
                    g_copies += 1
                    pr["copies"] += 1
                    pr["mana"] += c.mv
            for c in chosen:
                if c.name in track and not c.is_copy:
                    t_hand.setdefault(c.name, turn)
                    t_ok.setdefault(c.name, turn)
                    t_cast.add(c.name)
            if has_surveil:  # nach dem Zaubern: erst das Land, dann die Zauber in der Reihenfolge des Wirkens
                amounts = ([land_played.surveil] if land_played is not None else []) + [c.surveil for c in chosen]
                if any(amounts):
                    ev, binned = apply_surveils([a for a in amounts if a], library, hand, battlefield, graveyard=gy)
                    g_surveils += ev
                    sv["events"] += ev
                    sv["lands"] += binned
            if land_played is not None and not landfall_done and board:  # Land aus Landcycling oder Draw
                f_, _mana, c_ = landfall_effects(land_played, board, bonus, turn, with_mana=False)
                face_now += f_
                ef["counters"] += c_
            for c in chosen:  # Schaden an den Gegner, Marken und Pumps beim Wirken bzw. Betreten
                if c.modes:
                    g_ = apply_effects(c, board, bonus, pump, turn)
                    face_now += g_["face"]
                    ef["counters"] += g_["counters"]
            if has_jace:
                for c in sorted(chosen, key=lambda x: (not recurring_effects(x), x.mv)):
                    for pc, _t in perms:
                        for e in recurring_effects(pc):
                            if e[1] == "trigger" and e[3].startswith("cast:") and cast_filter_matches(e[3][5:], c):
                                jst.add(e[2])
                    for e in once_effects(c):
                        jst.add(e[2])
                    if not c.is_instant_sorcery:
                        for pc, _t in perms:
                            for e in recurring_effects(pc):
                                if e[1] == "trigger" and e[3].startswith("enter:") and enter_filter_matches(e[3][6:], c):
                                    jst.add(e[2])
                        if recurring_effects(c):
                            perms.append((c, turn))
            if turn <= max_turn and chosen:
                cast_in_turn[turn] += 1
            if has_ramp and extra_now:
                if ramp_first is None:
                    ramp_first = turn
                if turn <= curve_turns:
                    rp["extra"][turn] += extra_now
            if turn <= curve_turns:
                spent = min(sum(c.mv for c in chosen) + cycle_spent, avail_total)
                curve_avail[turn] += avail_total
                curve_spent[turn] += spent
                g_avail += avail_total
                g_spent += spent
                if avail_total > 0:
                    curve_games[turn] += 1
                    curve_full[turn] += (spent == avail_total)

            if has_jace:
                # Angriffs-Ausloeser (Kreaturen vom Vorzug oder mit Haste, nie Defender)
                for pc, t_in in perms:
                    for e in recurring_effects(pc):
                        if e[1] == "trigger" and e[3] == "attack" and pc.is_creature and (t_in < turn or pc.haste):
                            jst.add(e[2])
                # bezahlbare Faehigkeiten mit dem uebrigen Mana
                paid = [c.alts for c in chosen]
                for pc, t_in in perms:
                    for e in recurring_effects(pc):
                        if e[1] != "activated" or (e[5] and pc.is_creature and not (t_in < turn or pc.haste)):
                            continue
                        for _k in range(1 if e[5] else 10):
                            if not can_cast_all(tuple(sorted(paid + [e[4]])), key):
                                break
                            paid.append(e[4])
                            jst.add(e[2])
                # Loyalty aus dieser Runde: ab 3 ziehen, sonst Surveil 1 (auch bis 0)
                jst.try_activate(hand, library, turn, battlefield=battlefield, allow_surveil=True)

            # Angriff: Kreaturen vom Vorzug greifen an, neue nur mit Haste, Defender nie (keine Blocker, kein Removal)
            held = Counter()  # Kreaturen, die fuer Mana getappt wurden, greifen nicht an
            if creature_units and chosen:
                other = list(pool)
                for u, _i in creature_units:
                    other.remove(u)
                for i in tapped_for_mana([c.alts for c in chosen if c.alts], other, creature_units,
                                         [card for card, _t in mana_perms]):
                    held[mana_perms[i]] += 1
                    if not mana_perms[i][0].defender and mana_perms[i][0].power > 0:
                        rp["held"] += 1
            for i, (c, _t) in enumerate(board):  # Marken bei Loyalty (Inspired Tethermage)
                if c.loyalty_counter and jst.events > events0:
                    bonus[i] += c.loyalty_counter * (jst.events - events0)
                    ef["counters"] += c.loyalty_counter * (jst.events - events0)
            turn_dmg = face_now
            ef["face"] += face_now
            for i, (c, t) in enumerate(board):
                if not _attacks((c, t), turn):
                    continue
                if held[(c, t)]:
                    held[(c, t)] -= 1
                    continue
                turn_dmg += max(0, _power(board, bonus, pump, i))
                ef["pump"] += pump.get(i, 0)
            if not chosen:  # Rundenende ohne Zauber: Marken (Edgar)
                for i, (c, _t) in enumerate(board):
                    if c.endstep_counters:
                        bonus[i] += c.endstep_counters
                        ef["counters"] += c.endstep_counters
            dmg_total += turn_dmg
            log.append((turn, drew, land_played, tapped_now, chosen, turn_dmg, dmg_total, cycled_log,
                        (jst.gained - turn_gain0, jst.acts - turn_acts0, jst.loyalty, drawn_now)))
            if not dmg_done and dmg_total >= dmg_target:
                dmg_turns.append(turn)
                dmg_done = True
                cand_key = (turn, -dmg_total)  # frueher ist besser, bei Gleichstand mehr Schaden
                if best_lethal is None or cand_key < best_lethal["key"]:
                    best_lethal = {"key": cand_key, "opening": opening, "log": list(log), "mulls": mulls}

            # Hand aufgebraucht?
            if not hand_done and not hand:
                empty_hand.append(turn)
                hand_done = True
                acts_empty, gained_empty = jst.acts, jst.gained
            if not spells_done and all(c.is_land for c in hand):
                empty_spells.append(turn)
                spells_done = True

            if color_check and turn in cc_turns:  # Farbverfuegbarkeit: Laender und Manaquellen dieser Runde
                sources = Counter(col for land in battlefield for col in set(land.land_colors))
                for u, _i in (mana_units(mana_perms, turn) if has_ramp else []):
                    for col in set(u):
                        sources[col] += 1
                if turn == 3:
                    ok = [c for c in cc_colors if sources[c] >= 1]
                    for c in ok:
                        cc_t3[c] += 1
                    cc_all += len(ok) == len(cc_colors)
                for ch in cc_checks:
                    if ch["turn"] == turn:
                        ch["ok"] += sources[ch["color"]] >= ch["k"]

            if turn == max_turn:  # Momentaufnahme fuer Kreaturen und Screw
                short = len(battlefield) < max_turn
                no_colors = multicolor and not has_two_colors(full_key)
                land_screw += short
                color_screw += no_colors
                any_screw += (short or no_colors)
                n_creatures += len(board)  # Power/Toughness mit dauerhaften +1/+1-Marken
                power += sum(c.power for c, _ in board) + sum(bonus)
                toughness += sum(c.toughness for c, _ in board) + sum(bonus)
                snap = (len(board), sum(c.power for c, _ in board) + sum(bonus),
                        sum(c.toughness for c, _ in board) + sum(bonus))
            if turn in GY_TURNS:
                gys["n"][turn] += 1
                gys["size"][turn] += len(gy)
                gys["max_mv"][turn] += max((g.mv for g in gy), default=0)

        if has_jace:
            a_win = acts_empty if acts_empty is not None else jst.acts
            g_win = gained_empty if gained_empty is not None else jst.gained
            jc["acts_win"] += a_win
            jc["gained_win"] += g_win
            jc["dist_win"][min(a_win, 6)] += 1
            jc["games_any"] += a_win > 0
            jc["acts_all"] += jst.acts
            jc["surveil_all"] += jst.surveils
            jc["surveil_lands_all"] += jst.surveil_lands
            jc["gained_all"] += jst.gained
            jc["dist_all"][min(jst.acts, 6)] += 1
            samples["jace"].append(a_win)
            jc["empty_reached"] += acts_empty is not None
            if jst.first is not None:
                jc["first"].append(jst.first)

        dr["cards"] += g_drawn
        dr["games"] += g_drawn > 0
        sv["games"] += g_surveils > 0
        pr["games"] += g_copies > 0
        if ramp_first is not None:
            rp["games"] += 1
            rp["first"].append(ramp_first)
        for n, st in sc_stats.items():
            st["games"] += 1
            if n in t_hand:
                st["drawn"] += 1
                st["cast"] += n in t_cast
                if n in t_ok:
                    st["castable"] += 1
                    st["wait_sum"] += t_ok[n] - t_hand[n]
                    st["on_time"] += t_ok[n] <= max(track_mv[n], t_hand[n])
        samples["creatures"].append(snap[0])
        samples["power"].append(snap[1])
        samples["toughness"].append(snap[2])
        if g_avail:
            samples["util"].append(g_spent / g_avail)

        # Flood: Laender, die bis zum Ende gezogen wurden (Starthand + Zuege) = Hand + Feld
        lands_drawn = sum(c.is_land for c in hand) + len(battlefield)
        lands_drawn_total += lands_drawn
        flooded += lands_drawn >= flood_lands

        if game_events:
            cyc["games"] += 1
            cyc["first"].append(min(e[0] for e in game_events))
            for _t, reason, name, pb, pa in game_events:
                cyc["events"] += 1
                cyc["reason"][reason] += 1
                cyc["card"][name] += 1
                cyc["p_before"] += pb
                cyc["p_after"] += pa

    extra = {}
    if color_check:
        extra["color_avail"] = {"colors": cc_colors, "t3": cc_t3, "t3_all": cc_all, "games": sims,
                                "checks": [dict(ch, measured=horizon >= ch["turn"]) for ch in cc_checks]}
    return {
        **extra,
        "cast": cast_in_turn,
        "opener_lands": opener_lands / sims,
        "creatures": n_creatures / sims,
        "power": power / sims,
        "toughness": toughness / sims,
        "land_screw": land_screw / sims,
        "color_screw": color_screw / sims,
        "any_screw": any_screw / sims,
        "dmg": dmg_turns,
        "best_lethal": best_lethal,
        "mulligan": mull,
        "jace": jc,
        "splash_cards": sc_stats,
        "effects": {k: v / sims for k, v in ef.items()},
        "graveyard": {"size": {t: gys["size"][t] / gys["n"][t] if gys["n"][t] else 0.0 for t in GY_TURNS},
                      "max_mv": {t: gys["max_mv"][t] / gys["n"][t] if gys["n"][t] else 0.0 for t in GY_TURNS},
                      "hapatra_n": len(gys["x"]),
                      "hapatra_x_avg": sum(gys["x"]) / len(gys["x"]) if gys["x"] else 0.0,
                      "x_ge3": sum(x >= 3 for x in gys["x"]) / len(gys["x"]) if gys["x"] else 0.0,
                      "x_ge5": sum(x >= 5 for x in gys["x"]) / len(gys["x"]) if gys["x"] else 0.0},
        "ramp": {"on": has_ramp, "games": rp["games"] / sims,
                 "first_avg": sum(rp["first"]) / len(rp["first"]) if rp["first"] else None,
                 "extra": {t: v / sims for t, v in rp["extra"].items()}, "held_back": rp["held"] / sims,
                 "treasure_made": rp["made"] / sims, "treasure_used": rp["used"] / sims},
        "prepared": {"on": has_prepared, "copies": pr["copies"] / sims, "games": pr["games"] / sims,
                     "mana": pr["mana"] / sims},
        "card_surveil": {"on": has_surveil, "events": sv["events"] / sims, "games": sv["games"] / sims,
                         "lands": sv["lands"] / sims},
        "draws": {"on": has_draws, "cards": dr["cards"] / sims, "games": dr["games"] / sims, "used": dr["used"] / sims},
        "samples": samples,
        "curve": {"avail": curve_avail, "spent": curve_spent, "full": curve_full, "games": curve_games},
        "landcycle": cyc,
        "flood": flooded / sims,
        "lands_drawn": lands_drawn_total / sims,
        "empty_hand": empty_hand,
        "empty_spells": empty_spells,
        "top": top_turns,
    }


def card_label(c):
    if c.is_creature:
        return f"{c.name} ({c.power}/{c.toughness}{', Haste' if c.haste else ''})"
    return c.name
