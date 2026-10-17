"""Kampfmodell (Stufe 1): zwei Spieler mit 20 Leben spielen abwechselnd gegeneinander.

Ablauf eines Zugs: Untap (eigene Kreaturen enttappen), Draw (entfaellt im allerersten Zug des Spiels), Main 1 (Land,
Zauber ausser Kreaturen ohne Haste), Kampf, Main 2 (Kreaturen ohne Haste), End Phase (z. B. Edgar), danach verfaellt
Schaden an Kreaturen und Pumps bis Rundenende. Welche Zauber gespielt werden, entscheidet dieselbe Auswahl wie im
Goldfish (simulation.best_cast).

Angriff (choose_attackers): alles, wenn sicher Lethal; sonst greift eine Kreatur an, solange kein ungetappter Blocker
sie toetet und ueberlebt; zurueckgehalten wird, wenn sonst der Gegenangriff Lethal waere.
Block (choose_blocks): Blocker toetet und ueberlebt -> Tausch, wenn der Angreifer mindestens so viel Manawert hat ->
Doppel-Block, wenn einer der Blocker ueberlebt -> Chump nur gegen Lethal. Niemand kennt die Handkarten des anderen.
Schaden (resolve_combat): First Strike zuerst, Double Strike in beiden Schritten, Deathtouch (1 Schaden reicht, auch
mit Trample), Trample, Lifelink; ein Angreifer verteilt seinen Schaden so, dass moeglichst viele Blocker sterben.
Flying kann nur von Flying oder Reach geblockt werden, Menace nur von zwei oder mehr Kreaturen.
"""
import itertools

from components.mana import land_key
from components.mulligan import deal_opening
from components.simulation import (apply_effects, best_cast, choose_land, landfall_effects, resolve_draws,
                                   tapped_for_mana)

LIFE = 20


class Creature:
    """Eine Kreatur auf dem Feld (Karte, Schritt des Eintritts, getappt, Schaden, Marken, Pump)."""
    __slots__ = ("card", "entered", "tapped", "damage", "bonus", "pump", "dead", "touched")

    def __init__(self, card, entered=0):
        self.card = card
        self.entered = entered
        self.tapped = False
        self.damage = 0
        self.bonus = 0
        self.pump = 0
        self.dead = False
        self.touched = False  # Schaden durch Deathtouch erhalten

    @property
    def power(self):
        return self.card.power + self.bonus + self.pump

    @property
    def toughness(self):
        return self.card.toughness + self.bonus

    def has(self, keyword):
        return keyword in self.card.kw

    def copy(self):
        c = Creature(self.card, self.entered)
        for attr in ("tapped", "damage", "bonus", "pump", "dead", "touched"):
            setattr(c, attr, getattr(self, attr))
        return c

    def label(self):
        return f"{self.card.name} ({self.power}/{self.toughness})"


def can_attack(c, step):
    return not c.tapped and not c.dead and not c.card.defender and c.power > 0 and (c.entered < step or c.card.haste)


def can_block(blocker, attacker):
    if blocker.tapped or blocker.dead:
        return False
    return not attacker.has("flying") or blocker.has("flying") or blocker.has("reach")


# ---------------------------------------------------------------------------------------------------------------------
# Schaden
# ---------------------------------------------------------------------------------------------------------------------

def _deals_in(c, first_step):
    fs = c.has("first strike") or c.has("double strike")
    return (fs or c.has("double strike")) if first_step else (not c.has("first strike") or c.has("double strike"))


def _lethal_need(blocker, deathtouch):
    left = blocker.toughness - blocker.damage
    return min(1, left) if deathtouch else max(0, left)


def resolve_combat(pairs):
    """Kampfschaden fuer [(Angreifer, [Blocker])]. Veraendert Schaden und dead der Kreaturen.
    Gibt {"player": Schaden am Verteidiger, "lifelink_attacker", "lifelink_defender"} zurueck."""
    out = {"player": 0, "lifelink_attacker": 0, "lifelink_defender": 0}
    for first_step in (True, False):
        hits = []  # (Ziel-Kreatur, Schaden, Deathtouch)
        for att, blockers in pairs:
            if not att.dead and _deals_in(att, first_step) and att.power > 0:
                power, dt = att.power, att.has("deathtouch")
                if not blockers:
                    out["player"] += power
                else:
                    alive = sorted((b for b in blockers if not b.dead), key=lambda b: (b.toughness - b.damage,))
                    rest = power
                    for b in alive:
                        give = min(rest, _lethal_need(b, dt))
                        if give > 0:
                            hits.append((b, give, dt))
                            rest -= give
                    if rest > 0:
                        if att.has("trample") or not alive:
                            if att.has("trample"):
                                out["player"] += rest
                        else:
                            hits.append((alive[-1], rest, dt))
                if att.has("lifelink"):
                    out["lifelink_attacker"] += power
            for b in blockers:
                if not b.dead and not att.dead and _deals_in(b, first_step) and b.power > 0:
                    hits.append((att, b.power, b.has("deathtouch")))
                    if b.has("lifelink"):
                        out["lifelink_defender"] += b.power
        for target, amount, dt in hits:
            target.damage += amount
            target.touched = target.touched or dt
        for att, blockers in pairs:
            for c in [att] + list(blockers):
                if not c.dead and (c.damage >= c.toughness or (c.touched and c.damage > 0)):
                    c.dead = True
    return out


def outcome(attacker, blockers):
    """(Angreifer stirbt, [Blocker sterben]) fuer einen Kampf, ohne die Kreaturen zu veraendern."""
    a, bs = attacker.copy(), [b.copy() for b in blockers]
    resolve_combat([(a, bs)])
    return a.dead, [b.dead for b in bs]


def _value(c):
    return (c.card.mv, c.power + c.toughness)


# ---------------------------------------------------------------------------------------------------------------------
# Entscheidungen
# ---------------------------------------------------------------------------------------------------------------------

def max_through(attackers, blockers):
    """Schaden, der bei bestmoeglichem Blocken mindestens durchkommt (gierige Naeherung, ohne Kampftricks)."""
    free = [b for b in blockers if not b.tapped and not b.dead]
    total = 0
    for a in sorted(attackers, key=lambda a: -a.power * (2 if a.has("double strike") else 1)):
        dmg = a.power * (2 if a.has("double strike") else 1)
        cands = sorted((b for b in free if can_block(b, a)),
                       key=lambda b: (b.has("flying") or b.has("reach"), -b.toughness))
        need = 2 if a.has("menace") else 1
        if len(cands) < need:
            total += dmg
            continue
        used = cands[:need]
        for b in used:
            free.remove(b)
        if a.has("trample"):
            absorb = sum(1 if a.has("deathtouch") else max(0, b.toughness - b.damage) for b in used)
            total += max(0, dmg - absorb)
    return total


def _eats(blocker, attacker):
    if not can_block(blocker, attacker) or attacker.has("menace"):
        return False
    a_dead, b_dead = outcome(attacker, [blocker])
    return a_dead and not b_dead[0]


def choose_attackers(mine, theirs, their_life, my_life, step):
    """Angreifer nach den Regeln oben (Lethal, keine Kreatur ohne Not opfern, Gegenangriff beachten)."""
    cand = [c for c in mine if can_attack(c, step)]
    if not cand:
        return []
    blockers = [b for b in theirs if not b.tapped and not b.dead]
    if max_through(cand, blockers) >= their_life:
        return cand
    attack = [c for c in cand if not any(_eats(b, c) for b in blockers)]
    their_attackers = [t for t in theirs if not t.dead and not t.card.defender and t.power > 0]

    def crack_back(attack_set):
        home = [c for c in mine if not c.dead and not c.tapped and (c not in attack_set or c.has("vigilance"))]
        return max_through(their_attackers, home)

    if crack_back([]) < my_life:  # nur zurueckhalten, wenn es den Gegenangriff wirklich aufhaelt
        while attack and crack_back(attack) >= my_life:
            attack.remove(min(attack, key=lambda c: (c.power, c.toughness)))
    return attack


def choose_blocks(attackers, defenders, life):
    """Blocker je Angreifer: [(Angreifer, [Blocker])] in der Reihenfolge der Angreifer."""
    free = [d for d in defenders if not d.tapped and not d.dead]
    plan = {id(a): [] for a in attackers}
    order = sorted(attackers, key=lambda a: (-a.power, -a.toughness))
    for a in order:
        cands = [b for b in free if can_block(b, a)]
        if not a.has("menace"):
            good = [b for b in cands if outcome(a, [b]) == (True, [False])]
            if good:
                pick = min(good, key=_value)
                plan[id(a)] = [pick]
                free.remove(pick)
                continue
            trade = [b for b in cands if outcome(a, [b]) == (True, [True]) and a.card.mv >= b.card.mv]
            if trade:
                pick = min(trade, key=_value)
                plan[id(a)] = [pick]
                free.remove(pick)
                continue
        pairs = []
        for b1, b2 in itertools.combinations(cands, 2):
            a_dead, deads = outcome(a, [b1, b2])
            if a_dead and not all(deads):
                pairs.append((sum(x.card.mv for x in (b1, b2)), b1, b2))
        if pairs:
            _v, b1, b2 = min(pairs, key=lambda p: (p[0], _value(p[1]), _value(p[2])))
            plan[id(a)] = [b1, b2]
            free.remove(b1)
            free.remove(b2)

    def incoming():
        copies = [(a.copy(), [b.copy() for b in plan[id(a)]]) for a in attackers]
        return resolve_combat(copies)["player"]

    while incoming() >= life:  # Chump-Block nur gegen Lethal
        open_ = [a for a in order if not plan[id(a)]]
        done = False
        for a in open_:
            cands = sorted((b for b in free if can_block(b, a)), key=_value)
            need = 2 if a.has("menace") else 1
            if len(cands) >= need:
                plan[id(a)] = cands[:need]
                for b in cands[:need]:
                    free.remove(b)
                done = True
                break
        if not done:
            break
    return [(a, plan[id(a)]) for a in attackers]


# ---------------------------------------------------------------------------------------------------------------------
# Spieler und Spiel
# ---------------------------------------------------------------------------------------------------------------------

class Player:
    def __init__(self, name, cards, mulligan=True, min_hand=5, never_concede=False):
        self.name = name
        hand, library, mulls, _reasons = deal_opening(cards, mulligan, min_hand, keep_at_min=never_concede)
        self.lost = hand is None
        self.hand, self.library = (hand or []), (library or [])
        self.opening = list(self.hand)
        self.mulls = mulls
        self.lands, self.creatures, self.perms, self.graveyard = [], [], [], []
        self.life = LIFE

    def board(self):
        return [(c.card, c.entered) for c in self.creatures], [c.bonus for c in self.creatures], \
            {i: c.pump for i, c in enumerate(self.creatures) if c.pump}

    def write_back(self, bonus, pump):
        for i, c in enumerate(self.creatures):
            c.bonus = bonus[i]
            c.pump = pump.get(i, 0)


def _mana(me, step):
    """Mana zu Rundenbeginn: Laender, Manaquellen-Permanents, Kreaturen mit Mana-Faehigkeit (nicht frisch, ungetappt)."""
    pool = [land.land_colors for land in me.lands]
    pool += [u for card in me.perms for u in card.mana_src]
    creature_units = [(u, i) for i, c in enumerate(me.creatures)
                      if c.card.mana_src and not c.tapped and (c.entered < step or c.card.haste)
                      for u in c.card.mana_src]
    return pool, creature_units


def _resolve(me, opp, card, step, entry):
    """Eine gewirkte Karte kommt ins Spiel bzw. wirkt: Kreatur aufs Feld, Permanents, Instants/Sorceries in den
    Friedhof; Effekte (Schaden an den Gegner, Marken, Pumps) wie im Goldfish."""
    if card.is_creature:
        me.creatures.append(Creature(card, step))
    elif card.is_instant_sorcery:
        me.graveyard.append(card)
    else:
        me.perms.append(card)
    if card.self_damage:  # "damage to each player" trifft auch uns
        me.life -= card.self_damage
    if card.modes:
        board, bonus, pump = me.board()
        gain = apply_effects(card, board, bonus, pump, step)
        me.write_back(bonus, pump)
        if gain["face"]:
            opp.life -= gain["face"]
            entry["face"] += gain["face"]


def _desc(cs):
    return [c.label() + (" (getappt)" if c.tapped else "") for c in cs]


def take_turn(me, opp, step, rnd, skip_draw):
    """Ein Zug von me. Gibt den Protokolleintrag zurueck."""
    e = {"player": me.name, "round": rnd, "drew": None, "land": None, "main1": [], "main2": [], "attacks": [],
         "damage": 0, "face": 0, "deaths": [], "note": ""}
    for c in me.creatures:  # Untap
        c.tapped = False
    if not skip_draw:  # Draw
        if not me.library:
            me.lost = True
            e["note"] = "muss aus leerer Bibliothek ziehen"
            return e
        card = me.library.pop(0)
        me.hand.append(card)
        e["drew"] = card.name
    # Main 1: Land
    pool, creature_units = _mana(me, step)
    pool_all = pool + [u for u, _i in creature_units]
    spells = [c for c in me.hand if not c.is_land]
    has_creature = bool(me.creatures)
    land, tapped, forced = choose_land(me.hand, spells, pool_all, me.lands, False, False, has_creature, True)
    if land is not None:
        me.hand.remove(land)
        me.lands.append(land)
        e["land"] = land.name + (" (getappt)" if tapped else "")
        if not tapped:
            pool_all = pool_all + [land.land_colors]
        if me.creatures:
            board, bonus, pump = me.board()
            face, mana, _cnt = landfall_effects(land, board, bonus, step)
            me.write_back(bonus, pump)
            opp.life -= face
            e["face"] += face
            pool_all = pool_all + mana
    _score, chosen = best_cast(spells, land_key(pool_all), has_creature, True, must=forced)
    if any(c.draws for c in chosen):
        rd = resolve_draws(me.hand, me.library, chosen, pool_all, me.lands, land, has_creature, True, False, False)
        chosen, pool_all = rd["chosen"], rd["pool"]
        if rd["land"] is not None:
            e["land"] = rd["land"].name
    if creature_units and chosen:  # Kreaturen, deren Mana gebraucht wird, sind getappt
        other = list(pool_all)
        for u, _i in creature_units:
            other.remove(u)
        for i in tapped_for_mana([c.alts for c in chosen if c.alts], other, creature_units,
                                 [c.card for c in me.creatures]):
            me.creatures[i].tapped = True
    for c in chosen:
        me.hand.remove(c)
    main1 = [c for c in chosen if not (c.is_creature and not c.haste)]
    main2 = [c for c in chosen if c.is_creature and not c.haste]
    for c in main1:
        _resolve(me, opp, c, step, e)
    e["main1"] = [c.name for c in main1]
    if opp.life <= 0:
        return e
    # Kampf
    attackers = choose_attackers(me.creatures, opp.creatures, opp.life, me.life, step)
    blocks = choose_blocks(attackers, opp.creatures, opp.life)
    for a in attackers:
        if not a.has("vigilance"):
            a.tapped = True
    before = [(a.label(), [b.label() for b in bs]) for a, bs in blocks]
    res = resolve_combat(blocks)
    opp.life -= res["player"]
    me.life += res["lifelink_attacker"]
    opp.life += res["lifelink_defender"]
    e["damage"] = res["player"]
    e["attacks"] = [{"attacker": lab, "blockers": blabs, "attacker_dies": a.dead,
                     "blockers_die": [b.dead for b in bs]} for (lab, blabs), (a, bs) in zip(before, blocks)]
    for p in (me, opp):
        for c in [c for c in p.creatures if c.dead]:
            p.creatures.remove(c)
            p.graveyard.append(c.card)
            e["deaths"].append(f"{c.card.name} ({p.name})")
    if opp.life <= 0:
        return e
    # Main 2
    for c in main2:
        _resolve(me, opp, c, step, e)
    e["main2"] = [c.name for c in main2]
    # End Phase: Edgar ("if you didn't cast a spell this turn")
    if not chosen:
        for c in me.creatures:
            if c.card.endstep_counters:
                c.bonus += c.card.endstep_counters
    for p in (me, opp):  # Schaden und Pumps verfallen
        for c in p.creatures:
            c.damage, c.pump, c.touched = 0, 0, False
    return e


def _finish(entry, me, opp):
    entry["life"] = {me.name: me.life, opp.name: opp.life}
    entry["board"] = {me.name: _desc(me.creatures), opp.name: _desc(opp.creatures)}
    entry["lands"] = {me.name: len(me.lands), opp.name: len(opp.lands)}
    entry["hand"] = {me.name: len(me.hand), opp.name: len(opp.hand)}


def play_game(cards_a, cards_b, a_starts, max_turns=20, mulligan=True, min_hand=5):
    """Ein Spiel 'Wir' (cards_a) gegen 'Gegner' (cards_b). Gibt {winner: 'a'/'b'/None, round, log, opening} zurueck."""
    # Wir geben auf, wenn die Hand durch Mulligan unter min_hand faellt; der Gegner gibt nie auf
    a, b = Player("Wir", cards_a, mulligan, min_hand), Player("Gegner", cards_b, mulligan, min_hand, never_concede=True)
    result = {"winner": None, "round": 0, "log": [], "opening": {"Wir": [c.name for c in a.opening],
                                                                 "Gegner": [c.name for c in b.opening]},
              "mulligans": {"Wir": a.mulls, "Gegner": b.mulls}}
    if a.lost or b.lost:
        result["winner"] = None if a.lost and b.lost else ("b" if a.lost else "a")
        result["note"] = "Spiel durch Mulligan verloren"
        return result
    order = [(a, b), (b, a)] if a_starts else [(b, a), (a, b)]
    step = 0
    for rnd in range(1, max_turns + 1):
        for me, opp in order:
            step += 1
            entry = take_turn(me, opp, step, rnd, skip_draw=(step == 1))
            _finish(entry, me, opp)
            result["log"].append(entry)
            result["round"] = rnd
            if me.lost or opp.life <= 0 or me.life <= 0:
                loser = me if (me.lost or me.life <= 0) else opp
                result["winner"] = "b" if loser is a else "a"
                return result
    return result


def battle(cards_a, cards_b, games, on_draw, max_turns=20, mulligan=True, min_hand=5):
    """Spielt games Spiele; on_draw: der Gegner beginnt. Gibt Siege, Niederlagen, Unentschieden, Runden und die
    schnellsten Siege bzw. Niederlagen (mit Protokoll) zurueck."""
    out = {"games": games, "wins": 0, "losses": 0, "draws": 0, "win_rounds": [], "loss_rounds": [],
           "fastest_win": None, "fastest_loss": None, "mull_wins": 0, "mull_losses": 0}
    for _ in range(games):
        r = play_game(cards_a, cards_b, not on_draw, max_turns, mulligan, min_hand)
        if r.get("note") == "Spiel durch Mulligan verloren":  # zaehlt, aber nicht fuer Runden und schnellste Spiele
            if r["winner"] == "a":
                out["wins"] += 1
                out["mull_wins"] += 1
            elif r["winner"] == "b":
                out["losses"] += 1
                out["mull_losses"] += 1
            else:
                out["draws"] += 1
            continue
        if r["winner"] == "a":
            out["wins"] += 1
            out["win_rounds"].append(r["round"])
            if out["fastest_win"] is None or r["round"] < out["fastest_win"]["round"]:
                out["fastest_win"] = r
        elif r["winner"] == "b":
            out["losses"] += 1
            out["loss_rounds"].append(r["round"])
            if out["fastest_loss"] is None or r["round"] < out["fastest_loss"]["round"]:
                out["fastest_loss"] = r
        else:
            out["draws"] += 1
    return out
