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
from components.simulation import (apply_effects, best_cast, choose_land, landfall_effects, pay_subsets,
                                   resolve_draws, tapped_for_mana)
from components.landadvice import colors_of_alts

LIFE = 20


class Creature:
    """Eine Kreatur auf dem Feld (Karte, Schritt des Eintritts, getappt, Schaden, Marken, Pump)."""
    __slots__ = ("card", "entered", "tapped", "damage", "bonus", "pump", "dead", "touched", "locked")

    def __init__(self, card, entered=0):
        self.card = card
        self.entered = entered
        self.tapped = False
        self.damage = 0
        self.bonus = 0
        self.pump = 0
        self.dead = False
        self.touched = False  # Schaden durch Deathtouch erhalten
        self.locked = False   # Lock-Aura: greift nicht an, blockt nicht

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
        for attr in ("tapped", "damage", "bonus", "pump", "dead", "touched", "locked"):
            setattr(c, attr, getattr(self, attr))
        return c

    def label(self):
        return f"{self.card.name} ({self.power}/{self.toughness})"


def can_attack(c, step):
    return (not c.tapped and not c.dead and not c.locked and not c.card.defender and c.power > 0
            and (c.entered < step or c.card.haste))


def can_block(blocker, attacker):
    if blocker.tapped or blocker.dead or blocker.locked:
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
        self.open = []        # ungetapptes Mana nach dem eigenen Zug (fuer Instants und Flash im Zug des Gegners)
        self.cast_count = 0   # im eigenen Zug gewirkte Zauber (fuer Edgar)

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


# ---------------------------------------------------------------------------------------------------------------------
# Mana, Ziele, Removal, Abwerfen
# ---------------------------------------------------------------------------------------------------------------------

def pay(pool, alts):
    """Bezahlt Kosten aus pool (Farbtupel). Gibt den Rest zurueck (moeglichst viele Farben uebrig) oder None."""
    rems = pay_subsets(list(pool), alts) if alts else [list(pool)]
    if not rems:
        return None
    return max(rems, key=lambda r: (len(set().union(*r)) if r else 0, len(r)))


def danger(c):
    """Gefaehrlichste Kreatur: hoechste Power, dann Flying/Trample/Deathtouch, dann Manawert."""
    return (c.power, any(c.has(k) for k in ("flying", "trample", "deathtouch")), c.card.mv)


def _amount(spec, caster):
    amount = spec[1]
    if amount == -2:  # "damage equal to its power": unsere staerkste Kreatur
        return max((c.power for c in caster.creatures if not c.dead), default=0)
    if amount == -3:  # hoechster Manawert im eigenen Friedhof (Hapatra)
        return max((card.mv for card in caster.graveyard), default=0)
    if amount == -1:  # X: so viel wie Laender
        return len(caster.lands)
    return amount


def _matches(cond, c):
    for item in cond:
        kind = item[0]
        if kind == "flying" and not c.has("flying"):
            return False
        if kind == "mv_le" and c.card.mv > item[1]:
            return False
        if kind == "tough_ge" and c.toughness < item[1]:
            return False
        if kind == "pow_ge" and c.power < item[1]:
            return False
        if kind == "color" and not (colors_of_alts(c.card.alts) & set(item[1:])):
            return False
    return True


def valid_targets(spec, caster, victim):
    kind = spec[0]
    out = [c for c in victim.creatures if not c.dead and (kind != "lock" or not c.locked) and _matches(spec[2], c)]
    if kind in ("damage", "minus", "counters"):
        amount = _amount(spec, caster)
        out = [c for c in out if c.toughness - c.damage <= amount or (c.touched and amount > 0)]
    if kind == "fight":
        ours = max((c.power for c in caster.creatures if not c.dead), default=0)
        out = [c for c in out if c.toughness - c.damage <= ours]
    if spec[3]:  # "any target": nur Kreaturen, die Schaden machen koennen (sonst lieber an den Gegner)
        out = [c for c in out if c.power > 0]
    return out


def choose_target(spec, caster, victim):
    targets = valid_targets(spec, caster, victim)
    return max(targets, key=danger) if targets else None


def has_target(card, caster, victim):
    spec = card.removal
    if not spec:
        return True
    if spec[3]:  # any target: notfalls an den Gegner
        return True
    if spec[0] in ("sweep", "sweep_damage", "edict"):
        return any(not c.dead for c in victim.creatures)
    return choose_target(spec, caster, victim) is not None


def bury(players, e):
    """Gestorbene Kreaturen in den Friedhof (Schaden, Deathtouch, Toughness 0)."""
    for p in players:
        for c in list(p.creatures):
            if c.dead or c.toughness <= 0 or c.damage >= c.toughness or (c.touched and c.damage > 0):
                p.creatures.remove(c)
                p.graveyard.append(c.card)
                e["deaths"].append(f"{c.card.name} ({p.name})")


def choose_discard(p):
    """Abwerfen: ueberzaehliges Land (Feld + Hand >= hoechster Manawert der Hand), sonst die guenstigste Karte."""
    if not p.hand:
        return None
    lands = [c for c in p.hand if c.is_land]
    spells = [c for c in p.hand if not c.is_land]
    need = max((c.mv for c in spells), default=0)
    if lands and (not spells or len(p.lands) + len(lands) >= need):
        return lands[0]
    return min(spells, key=lambda c: (c.mv, c.name))


def discard(p, n, e):
    for _ in range(n):
        card = choose_discard(p)
        if card is None:
            return
        p.hand.remove(card)
        p.graveyard.append(card)
        e["events"].append(f"{p.name} wirft ab: {card.name}")


def cast_removal(card, caster, victim, e, step, target=None):
    """Wirkung des Removals von card (Card.removal) gegen victim. Gestorbene Kreaturen kommen in den Friedhof."""
    spec = card.removal
    if not spec:
        return
    kind, any_target, self_discard = spec[0], spec[3], spec[5]
    if self_discard:  # "you may discard a card. When you do, ..."
        choice = choose_discard(caster)
        if choice is None:
            return
        caster.hand.remove(choice)
        caster.graveyard.append(choice)
        e["events"].append(f"{caster.name} wirft ab: {choice.name}")
    amount = _amount(spec, caster)
    if kind in ("sweep", "sweep_damage"):
        hit = list(victim.creatures)
        if not ("chosen_type",) in spec[2] and not ("opponents",) in spec[2]:
            hit += caster.creatures
        for c in hit:
            if kind == "sweep":
                c.dead = True
            else:
                c.damage += amount
        e["events"].append(f"{caster.name}: {card.name} trifft alle Kreaturen")
        bury((caster, victim), e)
        return
    if kind == "edict":
        alive = [c for c in victim.creatures if not c.dead]
        if alive:
            pick = (max(alive, key=lambda c: (c.card.mv, c.power)) if ("greatest",) in spec[2]
                    else min(alive, key=_value))
            pick.dead = True
            e["events"].append(f"{caster.name}: {card.name} – {victim.name} opfert {pick.card.name}")
        bury((victim,), e)
        return
    if target is None:
        target = choose_target(spec, caster, victim)
    if kind == "damage" and any_target and (target is None or victim.life <= amount):
        victim.life -= amount
        e["face"] += amount
        e["events"].append(f"{caster.name}: {card.name} – {amount} Schaden an {victim.name}")
        return
    if target is None:
        e["events"].append(f"{caster.name}: {card.name} ohne Ziel")
        return
    label = target.label()
    if kind == "destroy":
        target.dead = True
    elif kind in ("damage", "minus"):
        target.damage += amount
    elif kind == "counters":
        target.bonus -= amount
    elif kind == "fight":
        ours = max((c for c in caster.creatures if not c.dead), key=lambda c: c.power, default=None)
        if ours is None:
            return
        target.damage += ours.power
        ours.damage += target.power
        label += f" (Fight mit {ours.card.name})"
    elif kind == "bounce":
        victim.creatures.remove(target)
        victim.hand.append(target.card)
        e["events"].append(f"{caster.name}: {card.name} – {label} zurück auf die Hand")
        return
    elif kind == "lock":
        target.locked = True
        e["events"].append(f"{caster.name}: {card.name} – {label} gesperrt")
        return
    e["events"].append(f"{caster.name}: {card.name} – {label}")
    bury((caster, victim), e)


def _resolve(me, opp, card, step, entry):
    """Eine gewirkte Karte kommt ins Spiel bzw. wirkt: Kreatur aufs Feld, Permanents, Instants/Sorceries in den
    Friedhof; Removal, Abwerfen und Effekte (Schaden an den Gegner, Marken, Pumps) wie im Goldfish."""
    if card.is_creature:
        me.creatures.append(Creature(card, step))
    elif card.is_instant_sorcery:
        me.graveyard.append(card)
    else:
        me.perms.append(card)
    if card.self_damage:  # "damage to each player" trifft auch uns
        me.life -= card.self_damage
    effects = card
    if card.removal:
        cast_removal(card, me, opp, entry, step)
        if card.removal[3]:  # any target: der Schaden ist schon verteilt
            effects = card._replace(modes=tuple(tuple(a for a in m if a[0] != "face") for m in card.modes))
    if card.discard:
        discard(opp, card.discard, entry)
    if effects.modes:
        board, bonus, pump = me.board()
        gain = apply_effects(effects, board, bonus, pump, step)
        me.write_back(bonus, pump)
        if gain["face"]:
            opp.life -= gain["face"]
            entry["face"] += gain["face"]
    if card.draws:
        for _ in range(card.draws):
            if me.library:
                me.hand.append(me.library.pop(0))
    bury((me, opp), entry)


def main_phase_spells(me, opp):
    """Karten fuer die Main Phases: keine Instants, keine Flash-Karten, Removal nur mit gueltigem Ziel."""
    return [c for c in me.hand if not c.is_land and not c.is_instant and not c.flash
            and (not c.removal or c.removal[4] == "etb" or has_target(c, me, opp))]


def _cast_from_open(p, card):
    rest = pay(p.open, card.alts)
    if rest is None:
        return False
    p.open = rest
    p.hand.remove(card)
    return True


def _trick_atoms(card):
    return [m for m in card.modes if any(a[0] in ("pump", "counter", "pump_all", "counter_all") for a in m)]


def _apply_trick(mode, target, own):
    for atom in mode:
        if atom[0] == "pump":
            target.pump += atom[1]
        elif atom[0] == "counter":
            target.bonus += atom[1]
        elif atom[0] == "pump_all":
            for c in own:
                c.pump += atom[1]
        elif atom[0] == "counter_all":
            for c in own:
                c.bonus += atom[1]


def _score(pairs, attacking, defender_life):
    """Bewertung eines Kampfs aus Sicht der Seite (attacking: wir greifen an)."""
    copies = [(a.copy(), [b.copy() for b in bs]) for a, bs in pairs]
    res = resolve_combat(copies)
    mine, theirs = 0, 0
    for a, bs in copies:
        own, other = ([a], bs) if attacking else (bs, [a])
        mine -= sum(10 * c.card.mv + c.power + c.toughness for c in own if c.dead)
        theirs += sum(10 * c.card.mv + c.power + c.toughness for c in other if c.dead)
    lethal = 1000 if attacking and res["player"] >= defender_life else 0
    return mine + theirs + lethal


def combat_tricks(p, pairs, opp, e, step, attacking):
    """Kampftricks (Instants und Flash-Karten mit Pump/Marken) nach den Blockern, wenn sie den Kampf verbessern:
    eigene Kreatur ueberlebt, gegnerische stirbt oder Lethal."""
    own = [a for a, _bs in pairs] if attacking else [b for _a, bs in pairs for b in bs]
    if not own:
        return
    for card in sorted([c for c in p.hand if (c.is_instant or c.flash) and _trick_atoms(c)], key=lambda c: c.mv):
        if pay(p.open, card.alts) is None:
            continue
        base = _score(pairs, attacking, opp.life)
        best = None
        for mode in _trick_atoms(card):
            for i, target in enumerate(own):
                saved = [(c.pump, c.bonus) for c in own]
                _apply_trick(mode, target, own)
                gain = _score(pairs, attacking, opp.life) - base
                for c, (pu, bo) in zip(own, saved):
                    c.pump, c.bonus = pu, bo
                if gain > 0 and (best is None or gain > best[0]):
                    best = (gain, mode, i)
        if best is None:
            continue
        _cast_from_open(p, card)
        _apply_trick(best[1], own[best[2]], own)
        if card.is_creature:
            p.creatures.append(Creature(card, step))
        elif card.is_instant_sorcery:
            p.graveyard.append(card)
        e["events"].append(f"{p.name}: Kampftrick {card.name} auf {own[best[2]].card.name}")


def respond_to_attack(dfn, att, attackers, e, step):
    """Der Verteidiger reagiert auf die Angreifer: Removal-Instants auf den gefaehrlichsten Angreifer, Flash-Kreaturen
    fuer einen guten Block oder gegen Lethal. Gibt die verbleibenden Angreifer zurueck."""
    while True:
        alive = [a for a in attackers if a in att.creatures and not a.dead and not a.locked]
        options = []
        for card in dfn.hand:
            if card.is_instant and card.removal and card.removal[4] == "spell" and pay(dfn.open, card.alts) is not None:
                spec = card.removal
                if spec[0] in ("sweep", "sweep_damage", "edict"):
                    continue
                targets = [a for a in valid_targets(spec, dfn, att) if a in alive]
                if targets:
                    options.append((danger(max(targets, key=danger)), card, max(targets, key=danger)))
        if not options:
            break
        _d, card, target = max(options, key=lambda o: (o[0], -o[1].mv))
        _cast_from_open(dfn, card)
        dfn.graveyard.append(card)
        cast_removal(card, dfn, att, e, step, target=target)
    alive = [a for a in attackers if a in att.creatures and not a.dead and not a.locked]
    for card in sorted([c for c in dfn.hand if c.flash and c.is_creature], key=lambda c: -c.mv):
        if pay(dfn.open, card.alts) is None:
            continue
        new = Creature(card, step)
        blockers = [b for b in dfn.creatures if not b.tapped and not b.dead]
        lethal = max_through(alive, blockers) >= dfn.life and max_through(alive, blockers + [new]) < dfn.life
        good = any(can_block(new, a) and outcome(a, [new]) == (True, [False]) for a in alive)
        if lethal or good:
            _cast_from_open(dfn, card)
            dfn.creatures.append(new)
            e["events"].append(f"{dfn.name}: {card.name} mit Flash als Blocker")
    return alive


def end_step_instants(dfn, act, e, step):
    """Am Ende des Zugs von act nutzt dfn sein offenes Mana: Removal auf die gefaehrlichste Kreatur, Flash-Kreaturen,
    sonstige Instants (z. B. Ziehen). Kampftricks bleiben auf der Hand."""
    for card in sorted([c for c in dfn.hand if c.is_instant and c.removal and c.removal[4] == "spell"],
                       key=lambda c: c.mv):
        if card not in dfn.hand or pay(dfn.open, card.alts) is None or not has_target(card, dfn, act):
            continue
        if card.removal[3] and choose_target(card.removal, dfn, act) is None and act.life > _amount(card.removal, dfn):
            continue  # "any target" am Endstep nur gegen eine Kreatur oder als Lethal
        _cast_from_open(dfn, card)
        dfn.graveyard.append(card)
        cast_removal(card, dfn, act, e, step)
    for card in sorted([c for c in dfn.hand if c.flash], key=lambda c: -c.mv):
        if card in dfn.hand and _cast_from_open(dfn, card):
            e["events"].append(f"{dfn.name}: {card.name} mit Flash am Ende des Zugs")
            _resolve(dfn, act, card, step, e)
            if card in dfn.graveyard and not card.is_instant_sorcery:
                dfn.graveyard.remove(card)
    for card in sorted([c for c in dfn.hand if c.is_instant and not c.removal and not _trick_atoms(c)],
                       key=lambda c: -c.mv):
        if card in dfn.hand and _cast_from_open(dfn, card):
            e["events"].append(f"{dfn.name}: {card.name} am Ende des Zugs")
            _resolve(dfn, act, card, step, e)


def _desc(cs):
    return [c.label() + (" (getappt)" if c.tapped else "") + (" (gesperrt)" if c.locked else "") for c in cs]


def take_turn(me, opp, step, rnd, skip_draw):
    """Ein Zug von me. Gibt den Protokolleintrag zurueck."""
    e = {"player": me.name, "round": rnd, "drew": None, "land": None, "main1": [], "main2": [], "attacks": [],
         "damage": 0, "face": 0, "deaths": [], "events": [], "note": ""}
    me.cast_count = 0
    for c in me.creatures:  # Untap (gesperrte Kreaturen bleiben gesperrt)
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
    spells = main_phase_spells(me, opp)
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
    _score_, chosen = best_cast(spells, land_key(pool_all), has_creature, True, must=forced)
    if any(c.draws for c in chosen):
        rd = resolve_draws(me.hand, me.library, chosen, pool_all, me.lands, land, has_creature, True, False, False)
        chosen = [c for c in rd["chosen"] if not c.is_instant and not c.flash]
        pool_all = rd["pool"]
        if rd["land"] is not None:
            e["land"] = rd["land"].name
    if creature_units and chosen:  # Kreaturen, deren Mana gebraucht wird, sind getappt
        other = list(pool_all)
        for u, _i in creature_units:
            other.remove(u)
        for i in tapped_for_mana([c.alts for c in chosen if c.alts], other, creature_units,
                                 [c.card for c in me.creatures]):
            me.creatures[i].tapped = True
    rest = list(pool_all)  # offenes Mana nach dem Bezahlen (Kreaturen-Mana zaehlt nicht dazu)
    for c in chosen:
        rest = pay(rest, c.alts) or rest
    for u, _i in creature_units:
        if u in rest:
            rest.remove(u)
    me.open = rest
    for c in chosen:
        me.hand.remove(c)
    me.cast_count += len(chosen)
    main1 = [c for c in chosen if not (c.is_creature and not c.haste)]
    main2 = [c for c in chosen if c.is_creature and not c.haste]
    for c in main1:
        _resolve(me, opp, c, step, e)
    e["main1"] = [c.name for c in main1]
    if opp.life <= 0:
        return e
    # Removal-Instants vor dem Angriff: Blocker entfernen, die einen unserer Angreifer fressen wuerden
    candidates = [c for c in me.creatures if can_attack(c, step)]
    for card in sorted([c for c in me.hand if c.is_instant and c.removal and c.removal[4] == "spell"],
                       key=lambda c: c.mv):
        if card not in me.hand or pay(me.open, card.alts) is None:
            continue
        eaters = [t for t in valid_targets(card.removal, me, opp) if any(_eats(t, a) for a in candidates)]
        if eaters:
            _cast_from_open(me, card)
            me.graveyard.append(card)
            me.cast_count += 1
            cast_removal(card, me, opp, e, step, target=max(eaters, key=danger))
    # Kampf
    attackers = choose_attackers(me.creatures, opp.creatures, opp.life, me.life, step)
    for a in attackers:
        if not a.has("vigilance"):
            a.tapped = True
    attackers = respond_to_attack(opp, me, attackers, e, step)
    blocks = choose_blocks(attackers, opp.creatures, opp.life)
    n_events = len(e["events"])
    combat_tricks(me, blocks, opp, e, step, attacking=True)
    me.cast_count += len(e["events"]) - n_events
    combat_tricks(opp, blocks, me, e, step, attacking=False)
    before = [(a.label(), [b.label() for b in bs]) for a, bs in blocks]
    res = resolve_combat(blocks)
    opp.life -= res["player"]
    me.life += res["lifelink_attacker"]
    opp.life += res["lifelink_defender"]
    e["damage"] = res["player"]
    e["attacks"] = [{"attacker": lab, "blockers": blabs, "attacker_dies": a.dead,
                     "blockers_die": [b.dead for b in bs]} for (lab, blabs), (a, bs) in zip(before, blocks)]
    bury((me, opp), e)
    if opp.life <= 0:
        return e
    # Main 2
    for c in main2:
        _resolve(me, opp, c, step, e)
    e["main2"] = [c.name for c in main2]
    # End Phase: Edgar ("if you didn't cast a spell this turn"), danach Instants und Flash des Gegners
    if not me.cast_count:
        for c in me.creatures:
            if c.card.endstep_counters:
                c.bonus += c.card.endstep_counters
    end_step_instants(opp, me, e, step)
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
