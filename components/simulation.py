"""Simulation eines Spiels: Zauber- und Landauswahl, Landcycling, Spielablauf und Statistik-Sammlung."""
import itertools
import random
from collections import Counter

from components.cards import HEARTWOOD, enters_tapped
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


_REDUCED = {}  # verbilligte Karte -> (Originalkarte, Senkung)


def cost_reduction(card, powers=(), toughs=(), legendary=False, noncreature=False, spell_discount=0):
    """Generisches Mana, um das die Karte billiger ist (601.2f): eigene Senkung (Ghalta: hoechste Power bzw. Toughness
    eigener Kreaturen; Wrath of the Bloodmane mit legendaerer Kreatur; Traxos nach einem Nichtkreatur-Zauber in diesem
    Zug) plus spell_discount fuer Nichtkreatur-Zauber (Geist of Saint Thalia). Der Manawert bleibt gleich."""
    n = 0 if card.is_creature or card.is_land else spell_discount
    sd = card.self_discount
    if sd:
        if sd[0] == "power":
            n += max(powers, default=0)
        elif sd[0] == "toughness":
            n += max(toughs, default=0)
        elif sd[0] == "legendary" and legendary:
            n += sd[1]
        elif sd[0] == "noncreature" and noncreature:
            n += sd[1]
    return max(0, n)


def reduced(card, n):
    """Die Karte mit um n gesenktem generischem Mana (n <= 0: die Karte selbst)."""
    if n <= 0 or not card.alts:
        return card
    base, before = _REDUCED[card][:2] if card in _REDUCED else (card, 0)
    cheap = card._replace(alts=tuple(sorted({(max(0, g - n), cols) for g, cols in card.alts})))
    if cheap != card:
        _REDUCED[cheap] = (base, before + n, card)
    return cheap


def original(card):
    """Originalkarte zu einer verbilligten Karte."""
    return _REDUCED.get(card, (card,))[0]


def paid_mv(card):
    """Tatsaechlich bezahltes Mana: Manawert minus Kostensenkung."""
    return max(0, card.mv - (_REDUCED[card][1] if card in _REDUCED else 0))


def hand_form(card, cards):
    """Die Fassung von card (verbilligt oder weniger verbilligt), die in cards liegt."""
    while card not in cards and card in _REDUCED:
        card = _REDUCED[card][2]
    return card


def take_from(cards, card):
    """Entfernt card aus cards; liegt dort eine weniger verbilligte Fassung, wird diese entfernt. Gibt sie zurueck."""
    card = hand_form(card, cards)
    cards.remove(card)
    return card


def discounted_hand(hand, board, bonus):
    """Goldfish: Handkarten mit Kostensenkung nach den Kreaturen auf dem Feld (board: (Karte, Runde), bonus: Marken).
    Gibt (neue Hand, {verbilligte Karte: Original}) zurueck."""
    powers = [c.power + bonus[i] for i, (c, _t) in enumerate(board)]
    toughs = [c.toughness + bonus[i] for i, (c, _t) in enumerate(board)]
    legendary = any(c.legendary for c, _t in board)
    spell_discount = sum(c.spell_discount for c, _t in board)
    out, back = [], {}
    for c in hand:
        cheap = reduced(c, cost_reduction(c, powers, toughs, legendary, False, spell_discount)) if not c.is_land else c
        if cheap is not c:
            back[cheap] = c
        out.append(cheap)
    return out, back


def best_cast_reduced(spells, key, has_creature, auras_need_creature, must=None):
    """best_cast, dazu Traxos-Senkung "if you've cast a noncreature spell this turn": eine Kombination, in der ein
    Nichtkreatur-Zauber zuerst gewirkt wird, darf die Karte verbilligt enthalten."""
    best = best_cast(spells, key, has_creature, auras_need_creature, must=must)
    waiting = [c for c in spells if c.self_discount and c.self_discount[0] == "noncreature"]
    if not waiting:
        return best
    firsts = [c for c in spells if not c.is_creature and not c.self_discount]
    for w in set(waiting):
        cheap = reduced(w, w.self_discount[1])
        trial = list(spells)
        trial[trial.index(w)] = cheap
        for f in sorted(set(firsts)):
            if must is not None and must != f:
                continue
            res = best_cast(trial, key, has_creature, auras_need_creature, must=f)
            if res[0] > best[0]:
                best = res
    return best


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
        left.subtract(Counter(hand_form(c, left) for c in cast if not c.is_copy))
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


def _attacks(entry, turn, board=None, counters=0):
    """Greift die Kreatur an? Defender nur, wenn auf dem Feld (board) eine Karte wie Ghalta the Immovable liegt; Haste
    auch von Samut ("Creatures you control have haste") und Gallia (Kreaturen mit Marke, counters)."""
    card, t_in = entry
    free = board is not None and any(c.defender_attack for c, _t in board)
    haste = card.haste or (board is not None and any(
        "haste" in c.team_kw_all or (c.counter_haste and counters > 0 and c is not card) for c, _t in board))
    return (not card.defender or free) and (t_in < turn or haste)


def cast_allowed(card, graveyard_size):
    """601.3: Zauber mit "can't cast unless ... seven or more cards in your graveyard" erst ab Threshold."""
    return not card.cast_threshold or graveyard_size >= 7


def _power(board, bonus, pump, i):
    return board[i][0].power + bonus[i] + pump.get(i, 0)


def walker_rank(atoms, opp_life, lands, have_creature, tokens=True):
    """(Rang, Gleichstand) einer Loyalty-Faehigkeit (L2a): 7 Lethal (Schaden am Gegner reicht), 5 grosses Token
    (mindestens 4/4) oder Marken je Land (ab 4 Laendern), 4 Ziehen, 3 kleines Token mit Surveil (Way of the Healer),
    2 Plus-Faehigkeit mit Schaden (Sanctum Lurker), 1 Surveil; 0 = nicht nutzen. Removal (Warlord), Opfern und Mana
    bewertet der Aufrufer. tokens=False: Goldfish (kennt keine Token)."""
    kinds = {a[0] for a in atoms}
    face = sum(a[1] for a in atoms if a[0] == "face") + sum(a[2] for a in atoms if a[0] == "bolt")
    if face and face >= opp_life:
        return 7, face
    if "token" in kinds:
        if not tokens:
            return 0, 0
        tok = next(a for a in atoms if a[0] == "token")
        stats = tok[1] * (tok[2].power + tok[2].toughness)
        return (5, stats) if stats >= 8 and "surveil" not in kinds else (3, stats)
    if "counter_lands" in kinds:
        return (5, 2 * lands) if lands >= 4 and have_creature else (0, 0)
    if "draw" in kinds:
        return 4, 0
    if "face" in kinds:
        return 2, face
    if kinds == {"surveil"}:
        return 1, 0
    return 0, 0


def copy_abilities(sources):
    """Way of the Cryomancer: die verliehene Kopier-Faehigkeit (Kosten, Effekte), hoechstens einmal."""
    costs = sorted({c.copy_grant for c in sources if c.copy_grant}, reverse=True)
    return [(costs[0], (("copy_next",),))] if costs else []


def spell_face(card):
    """Schaden am Gegner, den ein Instant/Sorcery macht (bester Modus), z. B. fuer seine Kopie."""
    return max((sum(a[1] for a in m if a[0] == "face") for m in card.modes), default=0)


def copy_face_of(spells, pool, has_creature, auras_need_creature):
    """Schaden des ersten Instants/Sorcery, den die Runde wirken wuerde (Kopie durch Way of the Cryomancer)."""
    chosen = best_cast_reduced(spells, land_key(pool), has_creature, auras_need_creature)[1]
    first = next((c for c in chosen if c.is_instant_sorcery), None)
    return spell_face(first) if first is not None else 0


def walker_choice(loyalty, sources, face_need, lands, creatures=True, alive=False, helps_mana=False, copy_face=0):
    """Goldfish: beste Loyalty-Faehigkeit des Jace-Tokens (Kosten, Effekte) oder None. Wie im Kampf, aber ohne Token,
    Opfern und Removal (kein Gegner); Mana nur, wenn es einen weiteren Zauber ermoeglicht (helps_mana). Kopie (Way of
    the Cryomancer) nur fuer Schaden (copy_face): Lethal 8, sonst 2."""
    if not (loyalty > 0 or alive):
        return None
    sculptor = any(c.loyalty_draw for c in sources)
    abilities = [(-1, (("surveil", 1),)), (-3, (("draw", 1),))] + [g for c in sources for g in c.walker_grants] \
        + copy_abilities(sources)
    best = None
    for cost, atoms in abilities:
        if cost < 0 and loyalty < -cost:
            continue  # 606.6
        rank, tie = walker_rank(atoms, face_need, lands, creatures, tokens=False)
        if atoms == (("copy_next",),):
            rank, tie = ((8 if 2 * copy_face >= face_need else 2), copy_face) if copy_face else (0, 0)
        if any(a[0] == "mana" for a in atoms):
            rank, tie = (2, 0) if helps_mana else (0, 0)
        if rank <= 0:
            continue
        key = (rank, 1 if sculptor and cost <= -2 else 0, tie)
        if best is None or key > best[0]:
            best = (key, (cost, atoms))
    return best[1] if best else None


def goldfish_walker(jst, phase, sources, hand, library, battlefield, board, bonus, pump, turn, face_need,
                    helps_mana=False, copy_face=0):
    """Goldfish-Aktivierung (L2a) zu einem Zeitpunkt wie im Kampf: "start" (nur Ziehen; mit Way of the Paradox alles
    ausser Mana), "main1" (Mana, Marken je Land), "after" (die beste). Gibt {"face", "mana", "lands"} zurueck."""
    out = {"face": 0, "mana": [], "lands": 0, "copy": False}
    if jst.used:
        return out
    choice = walker_choice(jst.loyalty, sources, face_need, len(battlefield), bool(board), jst.zero_alive, helps_mana,
                           copy_face)
    if choice is None:
        return out
    cost, atoms = choice
    kinds = {a[0] for a in atoms}
    paradox = any(c.loyalty_paradox for c in sources)
    if phase == "start" and not (kinds == {"draw"} or (paradox and "mana" not in kinds)):
        return out
    if phase == "start" and copy_abilities(sources) and any(c.is_instant_sorcery for c in hand):
        return out  # mit Way of the Cryomancer und Instant/Sorcery auf der Hand: erst in Main 1 entscheiden
    if phase == "main1" and not kinds & {"mana", "counter_lands", "copy_next"}:
        return out
    if cost < 0:
        jst.loyalty = max(0, jst.loyalty + cost)
    else:
        jst.add(cost)
    jst.used = True
    for a in atoms:
        if a[0] == "surveil":
            binned = surveil(library, a[1], hand, battlefield)
            jst.surveils += 1
            jst.surveil_lands += len(binned)
            if jst.graveyard is not None:
                jst.graveyard.extend(binned)
        elif a[0] == "draw" and library:
            hand.append(library.pop(0))
            jst.acts += 1
            if jst.first is None:
                jst.first = turn
        elif a[0] == "face":
            out["face"] += a[1]
        elif a[0] == "bolt":
            out["face"] += a[2]
        elif a[0] == "counter_lands" and board:
            order = _ranked(board, bonus, pump, turn, False)
            bonus[order[0]] += len(battlefield)
        elif a[0] == "mana":
            out["mana"].append(a[1])
        elif a[0] == "copy_next":
            out["copy"] = True
    for c in sources:
        if c.loyalty_draw and cost <= -2 and library:  # Way of the Mind Sculptor
            hand.append(library.pop(0))
    if paradox:
        out["lands"] += 1
    if jst.loyalty <= 0:
        jst.zero_alive = any(c.walker_no_death for c in sources)
    return out


def pw_choice(card, loyalty, lands=0, creatures=0, hand=0, face_need=99, helps_mana=False, sources=(), spells=None,
              copy_face=0):
    """Goldfish (L2): beste Loyalty-Faehigkeit eines echten Planeswalkers (Kosten, Effekte) oder None. Rangfolge wie im
    Kampf, aber ohne Token und Removal (kein Gegner): 8 Lethal, 7 Ultimate/Emblem, 4 Ziehen, 2 Plus mit Wert (Schaden,
    Surveil, Empower, Mana nur wenn es einen weiteren Zauber ermoeglicht, Team-Pump mit Kreaturen), 1 Plus ohne Wert.
    Eine Minus-Faehigkeit, die auf 0 bringt, nur fuer Lethal oder Ultimate. Ein Emblem "whenever you cast a spell" nur
    mit mindestens einem Zauber auf der Hand (spells: Zahl der Nichtland-Karten, None = unbekannt)."""
    best = None
    grants = [g for c in sources for g in c.walker_grants]
    for cost, atoms in list(card.pw_abilities) + grants + copy_abilities(sources):
        if cost == "X" or (cost < 0 and loyalty < -cost):
            continue  # 606.6; -X (Stun) ohne Gegner wertlos
        kinds = {a[0] for a in atoms}
        face = sum(a[1] for a in atoms if a[0] == "face")
        if atoms == (("copy_next",),):  # echte Planeswalker kopieren nur fuer Lethal
            rank, tie = (8, copy_face) if copy_face and 2 * copy_face >= face_need else (0, 0)
        elif (cost, atoms) in grants:
            rank, tie = walker_rank(atoms, face_need, lands, creatures > 0, tokens=False)
            if rank == 7:
                rank = 8
            if "mana" in kinds:
                rank, tie = (2, 3) if helps_mana else (0, 0)
        elif face and face >= face_need:
            rank, tie = 8, face
        elif "emblem" in kinds or cost <= -6:
            cast_only = all(a[1] in ("cast_draw", "cast_damage") for a in atoms if a[0] == "emblem")                 and "emblem" in kinds
            rank, tie = (0, 0) if cast_only and spells == 0 else (7, 0)
        elif "draw" in kinds:
            rank, tie = 4, 0
        elif "wheel_creatures" in kinds:
            rank, tie = (4, 0) if creatures > hand else (0, 0)
        elif "mana" in kinds:
            rank, tie = (2, 3) if helps_mana else (0, 0)
        elif "face" in kinds:
            rank, tie = 2, face
        elif kinds & {"surveil", "empower_islands"}:
            rank, tie = 2, 0
        elif "team_pump" in kinds:
            rank, tie = (2, 0) if creatures else (0, 0)
        else:
            rank, tie = 0, 0
        if rank <= 0 and cost >= 0:
            rank, tie = 1, 0
        if rank <= 0 or (loyalty + cost <= 0 and rank < 6):
            continue
        key = (rank, tie, cost)
        if best is None or key > best[0]:
            best = (key, (cost, atoms))
    return best[1] if best else None


def goldfish_entrust_pick(library, walkers, jst):
    """Wie battle.entrust_pick: nur mit Jace-Token; Planeswalker mit dem hoechsten Manawert, ohne Legend-Konflikt."""
    if not (jst.loyalty > 0 or jst.zero_alive):
        return None
    names = {w.name for w in walkers}
    cands = [c for c in library if c.is_planeswalker and not (c.legendary and c.name in names)]
    return max(cands, key=lambda c: (c.mv, c.loyalty_start, c.name)) if cands else None


def goldfish_tutor_pick(library, hand, battlefield):
    """Wie battle.tutor_pick (Laender + 1 fuer die naechste Runde)."""
    if any(c.is_planeswalker for c in hand):
        return None
    cands = [c for c in library if c.is_planeswalker]
    if not cands:
        return None
    ok = [c for c in cands if c.mv <= len(battlefield) + 1]
    return max(ok, key=lambda c: (c.mv, c.name)) if ok else min(cands, key=lambda c: (c.mv, c.name))


def enter_value(card):
    """Bringt das Betreten der Karte etwas (fuer eine Kopie durch Splinter Twin)? Removal, Token, Ziehen, Surveil,
    Treasure, Leben, Mill und Land, Abwerfen, modale Effekte, Schaden/Marken/Pumps, Empower."""
    return bool((card.removal and card.removal[4] == "etb") or card.creates_tokens or card.draws or card.surveil
                or card.treasure or card.etb_life or card.mill_land or card.discard or card.choices or card.modes
                or card.hand_pick or card.artifact_pump or any(ef[1] == "etb" for ef in once_effects(card)))


def enter_face(card):
    """Schaden am Gegner beim Betreten (feste Zahl)."""
    face = sum(a[1] for m in card.modes[:1] for a in m if a[0] == "face")
    spec = card.removal
    if spec and spec[4] == "etb" and spec[0] == "damage" and spec[3] and spec[1] > 0:
        face = max(face, spec[1])
    return face


def twin_host_index(board, bonus, need):
    """Kreatur fuer Splinter Twin (wie im Kampf): mit Betreten-Effekt (hoechster Removal-Score, dann Manawert), sonst
    die staerkste nicht legendaere; legendaere nur, wenn ihr Betreten-Schaden mindestens need ist (Lethal)."""
    idx = range(len(board))
    useful = [i for i in idx if enter_value(board[i][0]) and (not board[i][0].legendary
                                                             or enter_face(board[i][0]) >= need)]
    if useful:
        return max(useful, key=lambda i: (board[i][0].removal_points, board[i][0].mv, -i))
    plain = [i for i in idx if not board[i][0].legendary]
    return max(plain, key=lambda i: (board[i][0].power + bonus[i], -i)) if plain else None


def _copy_damage(card, board):
    """Kampfschaden einer Kopie (nur aufgedruckte Werte, 707.2)."""
    if card.toughness > card.power and any(c.toughness_damage for c, _t in board):
        return card.toughness
    return max(0, card.power)


def combat_damage(board, bonus, pump, i):
    """Kampfschaden der Kreatur i: Power, mit Ghalta the Immovable auf dem Feld die Toughness, wenn sie groesser ist
    (510.1a; Pumps im Goldfish sind nur +X/+0)."""
    power = _power(board, bonus, pump, i)
    tough = board[i][0].toughness + bonus[i]
    if tough > power and any(c.toughness_damage for c, _t in board):
        return tough
    return power


def _ranked(board, bonus, pump, turn, attackers_only):
    """Indizes der Kreaturen, staerkste zuerst; Angreifer dieser Runde vor den uebrigen."""
    idx = [i for i in range(len(board)) if not attackers_only or _attacks(board[i], turn, board)]
    return sorted(idx, key=lambda i: (not _attacks(board[i], turn, board), -_power(board, bonus, pump, i), i))


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
                gain += atom[1] if _attacks(board[i], turn, board) else 0
        elif kind == "counter_all":
            for i in range(len(board)):
                bonus[i] += atom[1]
                counters += atom[1]
                gain += atom[1] if _attacks(board[i], turn, board) else 0
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


def cards_left(spells, chosen):
    """Zaehlung der Zauber, die nach chosen noch auf der Hand sind (verbilligte Fassungen zaehlen fuer ihre Karte)."""
    left = Counter(spells)
    left.subtract(Counter(hand_form(c, left) for c in chosen))
    return left


def without_many(items, remove):
    """items ohne die Karten aus remove; eine verbilligte Fassung (Kostensenkung) entfernt ihre Handkarte."""
    out = list(items)
    for r_ in remove:
        out.remove(hand_form(r_, out))
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
    has_ramp = any(c.mana_src or c.treasure or c.heartwood for c in cards)
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
        pws = []      # echte Planeswalker mit Loyalty-Faehigkeiten: [Karte, Loyalty] (L2)
        emblems = []  # Embleme: ("team", P, T), ("cast_draw",), ("cast_damage", N)
        acts_empty = gained_empty = None
        snap = (0, 0, 0)
        g_avail = g_spent = 0
        g_drawn = g_surveils = g_copies = 0
        mana_perms, treasures, ramp_first = [], 0, None  # Manaquellen auf dem Feld (Karte, Runde), Treasure-Token
        prep = []  # Prepared-Kreaturen auf dem Feld: [Karte, prepared?]
        bonus = []  # dauerhafte +1/+1-Marken je Kreatur auf dem Feld (gleiche Reihenfolge wie board)
        twins = []  # Splinter Twin: [Index in board, Runde des Wirkens]
        nperms = []  # Nichtkreatur-Permanents (Way of the ... fuer Loyalty-Faehigkeiten)
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
            extra_lands = 0
            pump, face_now, landfall_done = {}, 0, False
            copy_pending = mach_now = False  # Way of the Cryomancer / Jace's Machinations in dieser Runde
            for p_ in prep:  # Upkeep: "if this creature isn't prepared, it becomes prepared"
                if p_[0].prepared[0] in ("upkeep", "both"):
                    p_[1] = True
            turn_acts0, turn_gain0 = jst.acts, jst.gained
            # Splinter Twin: Kopie am Ende des gegnerischen Zugs (513.2), Betreten-Effekte, greift in diesem Zug mit an
            twin_copies = []
            for idx, t_cast in twins:
                hc, t_in = board[idx]
                if t_cast <= turn - 1 and t_in <= turn - 2:  # 302.6: seit Beginn unseres letzten Zugs da
                    twin_copies.append(idx)
                    g_ = apply_effects(hc, board, bonus, {}, turn)  # Pumps verfallen im Zug des Gegners
                    face_now += g_["face"]
                    ef["counters"] += g_["counters"]
                    for _k in range(hc.draws):
                        if library:
                            hand.append(library.pop(0))
                            g_drawn += 1
                    if hc.surveil:
                        apply_surveils([hc.surveil], library, hand, battlefield, graveyard=gy)
                    treasures += hc.treasure
                    if has_jace:
                        for e in once_effects(hc):
                            if e[1] == "etb":
                                jst.add(e[2])
            if has_jace:
                for pc, t_in in perms:
                    if t_in < turn:
                        for e in recurring_effects(pc):
                            if e[1] == "trigger" and e[3] == "turn":
                                jst.add(e[2])
                sources = nperms + [c for c, _t in board]
                if jst.zero_alive or any(c.walker_grants or c.walker_no_death or c.loyalty_draw or c.loyalty_paradox
                                         or c.copy_grant for c in sources):
                    wo = goldfish_walker(jst, "start", sources, hand, library, battlefield, board, bonus, pump, turn,
                                         dmg_target - dmg_total)
                    face_now += wo["face"]
                    extra_lands = wo["lands"]
                else:
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
            # Kostensenkung nach den Kreaturen auf dem Feld (Geist, Ghalta, Wrath of the Bloodmane)
            hand[:] = discounted_hand([original(c) for c in hand], board, bonus)[0]

            def copies_now():
                return discounted_hand([p_[0].prepared[1] for p_ in prep if p_[1]], board, bonus)[0]

            def castable():  # Handkarten und verfuegbare Prepared-Kopien (Splinter Twin nur mit passender Kreatur)
                return [c for c in hand if not c.is_land and cast_allowed(c, len(gy))
                        and (not c.twin or twin_host_index(board, bonus, dmg_target - dmg_total) is not None)
                        and (not c.entrust or goldfish_entrust_pick(library, walkers, jst) is not None)
                        and (not c.pw_tutor or goldfish_tutor_pick(library, hand, battlefield) is not None)] \
                    + copies_now()

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
            while extra_lands > 0 and any(c.is_land for c in hand):  # Way of the Paradox: weiterer Landdrop
                extra_lands -= 1
                land2, tapped2, _f = choose_land(hand, spells, pool, battlefield, walker_bf, jace_bf, has_creature,
                                                 auras_need_creature)
                if land2 is None:
                    break
                hand.remove(land2)
                battlefield.append(land2)
                if not tapped2:
                    pool = pool + [land2.land_colors]
                    if land2.land_colors:
                        avail_total += 1
            sources = nperms + [c for c, _t in board]
            cf = copy_face_of(castable(), pool, has_creature, auras_need_creature) if copy_abilities(sources) else 0
            for slot in list(pws) if cf else ():  # echte Planeswalker: Kopie nur fuer Lethal, vor dem Zaubern
                choice = pw_choice(slot[0], slot[1], sources=sources, face_need=dmg_target - dmg_total - face_now,
                                   copy_face=cf)
                if choice is not None and choice[1] == (("copy_next",),) and not copy_pending:
                    slot[1] += choice[0]
                    slot[2] = turn
                    copy_pending = True
                    if slot[1] <= 0:
                        pws.remove(slot)
                        if slot[0] in walkers:
                            walkers.remove(slot[0])
            if has_jace and any(c.walker_grants or c.copy_grant for c in sources):  # Mana, Marken, Kopie vor dem Zaubern
                spells = castable()
                plus_r = [a[1] for c in sources for cost, atoms in c.walker_grants for a in atoms if a[0] == "mana"]
                helps = bool(plus_r) and best_cast_reduced(spells, land_key(pool + plus_r[:1]), has_creature,
                                                           auras_need_creature)[0] > best_cast_reduced(
                    spells, land_key(pool), has_creature, auras_need_creature)[0]
                wo = goldfish_walker(jst, "main1", sources, hand, library, battlefield, board, bonus, pump, turn,
                                     dmg_target - dmg_total, helps, 0 if copy_pending else cf)
                face_now += wo["face"]
                copy_pending = copy_pending or wo["copy"]
                pool = pool + wo["mana"]
                avail_total += len(wo["mana"])
                spells = castable()
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

            s_chosen, chosen = best_cast_reduced(spells, key, has_creature, auras_need_creature, must=forced)
            if treasures and forced is None:  # Treasure nur, wenn er diese Runde mehr ermoeglicht
                k_t, ch_t = use_treasures(spells, pool, treasures, has_creature, auras_need_creature)
                if k_t:
                    treasures -= k_t
                    rp["used"] += k_t
                    pool = pool + [ANY_COLOR] * k_t
                    avail_total += k_t
                    extra_now += k_t
                    key = land_key(pool)
                    s_chosen, chosen = best_cast_reduced(spells, key, has_creature, auras_need_creature)

            # Landcycling Regel 1: Karte ist diesmal nicht spielbar -> mit uebrigem Mana cyceln.
            # Entfaellt in Runden, in denen ein Zauber vor dem Land gewirkt wurde (Bezahlung sonst nicht gesichert).
            if has_cyclers and forced is None:
                for _round in range(3):
                    if len(battlefield) + sum(c.is_land for c in hand) >= cycle_cap:
                        break
                    left = cards_left(spells, chosen)
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
                        s_chosen, chosen = best_cast_reduced(spells, key, has_creature, auras_need_creature)
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
                                   copies=copies_now())
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
                take_from(hand, c)
                if c.is_creature:
                    board.append((c, turn))
                    bonus.append(0)
                if c.is_instant_sorcery:
                    gy.append(c)  # gewirkte Instants und Sorceries kommen in den Friedhof
                if c.gy_x:  # Hapatra: hoechster Manawert im Friedhof
                    gys["x"].append(max((g.mv for g in gy), default=0))
                if c.is_planeswalker:
                    walkers.append(c)
                    if c.loyalty_start > 0:
                        pws.append([c, c.loyalty_start, 0])  # [Karte, Loyalty, Runde der letzten Aktivierung]
                if c.jace_instant:
                    mach_now = True
                if c.entrust:  # Entrust the Spark: Jace-Token opfern, Planeswalker aus der Bibliothek aufs Feld
                    pick = goldfish_entrust_pick(library, walkers, jst)
                    if pick is not None:
                        jst.loyalty, jst.zero_alive = 0, False
                        library.remove(pick)
                        random.shuffle(library)
                        walkers.append(pick)
                        if pick.loyalty_start > 0:
                            pws.append([pick, pick.loyalty_start, 0])
                if c.pw_tutor:  # Loyal Tutor: Planeswalker oben auf die Bibliothek
                    pick = goldfish_tutor_pick(library, hand, battlefield)
                    if pick is not None:
                        library.remove(pick)
                        random.shuffle(library)
                        library.insert(0, pick)
                for em in emblems:  # Embleme beim Wirken
                    if em[0] == "cast_draw" and library:
                        hand.append(library.pop(0))
                    elif em[0] == "cast_damage":
                        face_now += em[1]
                if c.prepared:
                    prep.append([c, c.prepared[0] in ("enters", "both")])
                if c.mana_src:
                    mana_perms.append((c, turn))
                if not c.is_creature and not c.is_instant_sorcery and not c.is_land and not c.is_copy:
                    nperms.append(c)
                for _k in range(c.heartwood):  # Heartwood-Token: Mana ab der naechsten Runde
                    mana_perms.append((HEARTWOOD, turn))
                if c.treasure:
                    treasures += c.treasure
                    rp["made"] += c.treasure
            for c in chosen:  # Splinter Twin auf die passende Kreatur (auch eine aus dieser Runde)
                if c.twin:
                    idx = twin_host_index(board, bonus, dmg_target - dmg_total)
                    if idx is not None:
                        twins.append([idx, turn])
            for c in chosen:
                if c.is_copy:  # Kopie gewirkt: eine passende Kreatur ist nicht mehr prepared
                    p_ = next(p_ for p_ in prep if p_[1] and p_[0].prepared[1] == original(c))
                    p_[1] = False
                    g_copies += 1
                    pr["copies"] += 1
                    pr["mana"] += paid_mv(c)
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
                if copy_pending and c.is_instant_sorcery:  # Kopie (Way of the Cryomancer): im Goldfish nur Schaden
                    face_now += spell_face(c)
                    copy_pending = False
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
                spent = min(sum(paid_mv(c) for c in chosen) + cycle_spent, avail_total)
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
                # Loyalty aus dieser Runde: ab 3 ziehen, sonst Surveil 1 (auch bis 0); mit Way of the ... (L2a)
                sources = nperms + [c for c, _t in board]
                if jst.zero_alive or any(c.walker_grants or c.walker_no_death or c.loyalty_draw or c.loyalty_paradox
                                         or c.copy_grant for c in sources):
                    face_now += goldfish_walker(jst, "after", sources, hand, library, battlefield, board, bonus, pump,
                                                turn, dmg_target - dmg_total)["face"]
                else:
                    jst.try_activate(hand, library, turn, battlefield=battlefield, allow_surveil=True)
                if mach_now and (jst.loyalty > 0 or jst.zero_alive):  # Jace's Machinations: noch eine Aktivierung
                    jst.used = False
                    if any(c.walker_grants or c.walker_no_death or c.loyalty_draw or c.loyalty_paradox or c.copy_grant
                           for c in sources):
                        face_now += goldfish_walker(jst, "after", sources, hand, library, battlefield, board, bonus,
                                                    pump, turn, dmg_target - dmg_total)["face"]
                    else:
                        jst.try_activate(hand, library, turn, battlefield=battlefield, allow_surveil=True)

            passes = [(s_, False) for s_ in pws] + [(s_, True) for s_ in pws if mach_now and s_[0].is_jace]
            for slot, extra in passes:  # L2: echte Planeswalker, eine Faehigkeit pro Runde (606.3); Machinations
                if slot not in pws or (slot[2] == turn and not extra):
                    continue
                slot[2] = turn
                pwc, loy = slot[0], slot[1]
                choice = pw_choice(pwc, loy, len(battlefield), len(board), len(hand), dmg_target - dmg_total - face_now,
                                   sources=nperms + [c for c, _t in board], spells=sum(not h.is_land for h in hand))
                if choice is None:
                    continue
                cost, atoms = choice
                slot[1] = loy + cost
                for a in atoms:
                    kind = a[0]
                    if kind == "face":
                        face_now += a[1]
                    elif kind == "bolt":
                        face_now += a[2]
                    elif kind == "draw":
                        for _k in range(a[1]):
                            if library:
                                hand.append(library.pop(0))
                    elif kind == "counters_hand":
                        for i in range(len(board)):
                            bonus[i] += len(hand)
                            ef["counters"] += len(hand)
                    elif kind == "emblem":
                        emblems.append(a[1:])
                    elif kind == "team_pump":
                        for i in range(len(board)):
                            pump[i] = pump.get(i, 0) + a[1]
                    elif kind == "wheel_creatures":
                        gy.extend(hand)
                        hand.clear()
                        for _k in range(len(board)):
                            if library:
                                hand.append(library.pop(0))
                    elif kind == "surveil":
                        apply_surveils([a[1]], library, hand, battlefield, graveyard=gy)
                    elif kind == "mill_top" and library:
                        library.pop(0)
                    elif kind == "empower_islands":
                        jst.add(sum("island" in land.land_types for land in battlefield))
                if slot[1] <= 0:  # 704.5i
                    pws.remove(slot)
                    if pwc in walkers:
                        walkers.remove(pwc)
            team = sum(em[1] for em in emblems if em[0] == "team")
            for i in range(len(board)) if team else ():  # Emblem "Creatures you control get +N/+N"
                pump[i] = pump.get(i, 0) + team
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
                if not _attacks((c, t), turn, board, bonus[i]):
                    continue
                if held[(c, t)]:
                    held[(c, t)] -= 1
                    continue
                turn_dmg += max(0, combat_damage(board, bonus, pump, i))
                ef["pump"] += pump.get(i, 0)
            for idx in twin_copies:  # die Kopie mit Haste greift neben dem enttappten Original an
                turn_dmg += _copy_damage(board[idx][0], board)
            for idx, t_cast in twins:  # im eigenen Zug nur fuer Lethal: Original tappt, Kopie greift an
                hc, t_in = board[idx]
                if idx in twin_copies or t_in >= turn:
                    continue
                host = max(0, combat_damage(board, bonus, pump, idx)) if _attacks(board[idx], turn, board) else 0
                alt = turn_dmg - host + _copy_damage(hc, board) + enter_face(hc)
                if dmg_total + alt >= dmg_target > dmg_total + turn_dmg:
                    turn_dmg = alt
                    break
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
