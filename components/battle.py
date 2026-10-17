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
from collections import Counter

from components.mana import land_key
from components.mulligan import deal_opening
from components.jace import (JaceState, cast_filter_matches, enter_filter_matches, once_effects,
                             recurring_effects, surveil)
from components.simulation import (ANY_COLOR, apply_effects, apply_surveils, best_cast, choose_land, do_cycle,
                                   enters_prepared, landfall_effects, pay_subsets, plan_cycle, resolve_draws,
                                   tapped_for_mana, usable_now, use_treasures)
from components.landadvice import colors_of_alts

LIFE = 20
CYCLE_TURNS = 3  # eigener Zug: fehlt bis Runde 3 ein Land fuer den Landdrop, wird sofort gecycelt
CYCLE_CAP = 6    # Ende des gegnerischen Zugs: nur cyceln, solange Laender auf Feld und Hand unter 6 liegen


class Creature:
    """Eine Kreatur auf dem Feld (Karte, Schritt des Eintritts, getappt, Schaden, Marken, Pump)."""
    __slots__ = ("card", "entered", "tapped", "damage", "bonus", "pump", "dead", "touched", "locked", "prepared",
                 "tpump", "extra", "lifted", "owner")

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
        self.prepared = bool(card.prepared) and card.prepared[0] in ("enters", "both")
        self.tpump = 0        # Toughness-Pump bis Rundenende (Faehigkeiten)
        self.extra = set()    # verliehene Schluesselwoerter bis Rundenende
        self.lifted = False   # Defender gilt in diesem Zug nicht (Surveillance Phantasm nach einem Surveil)
        self.owner = None     # Besitzer, wenn nicht der Kontrolleur (aus dem Exil gewirkt, Null Summoner)

    @property
    def power(self):
        return self.card.power + self.bonus + self.pump

    @property
    def toughness(self):
        return self.card.toughness + self.bonus + self.tpump

    def has(self, keyword):
        return keyword in self.card.kw or keyword in self.extra

    def copy(self):
        c = Creature(self.card, self.entered)
        for attr in ("tapped", "damage", "bonus", "pump", "dead", "touched", "locked", "prepared", "tpump",
                     "lifted"):
            setattr(c, attr, getattr(self, attr))
        c.extra = set(self.extra)
        c.owner = self.owner
        return c

    def label(self):
        return f"{self.card.name} ({self.power}/{self.toughness})"


def can_attack(c, step):
    return (not c.tapped and not c.dead and not c.locked and (not c.card.defender or c.lifted) and c.power > 0
            and (c.entered < step or c.card.haste or "haste" in c.extra))


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
    out = {"player": 0, "lifelink_attacker": 0, "lifelink_defender": 0, "to_player": {},
           "lifelink_events_attacker": 0, "lifelink_events_defender": 0}
    for first_step in (True, False):
        hits = []  # (Ziel-Kreatur, Schaden, Deathtouch)
        for att, blockers in pairs:
            if not att.dead and _deals_in(att, first_step) and att.power > 0:
                power, dt = att.power, att.has("deathtouch")
                if not blockers:
                    out["player"] += power
                    out["to_player"][id(att)] = out["to_player"].get(id(att), 0) + power
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
                                out["to_player"][id(att)] = out["to_player"].get(id(att), 0) + rest
                        else:
                            hits.append((alive[-1], rest, dt))
                if att.has("lifelink"):
                    out["lifelink_attacker"] += power
                    out["lifelink_events_attacker"] += 1
            for b in blockers:
                if not b.dead and not att.dead and _deals_in(b, first_step) and b.power > 0:
                    hits.append((att, b.power, b.has("deathtouch")))
                    if b.has("lifelink"):
                        out["lifelink_defender"] += b.power
                        out["lifelink_events_defender"] += 1
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
        self.dealt_combat = 0  # Kampfschaden am Gegner
        self.dealt_direct = 0  # direkter Schaden am Gegner (Burn, Landfall, "any target")
        self.deaths = 0        # gestorbene eigene Kreaturen
        self.cast_count = 0   # im eigenen Zug gewirkte Zauber (fuer Edgar)
        self.treasures = 0    # Treasure-Token
        self.jace = JaceState()  # Jace-Token (Empower Jace), unangreifbar
        self.jace.graveyard = self.graveyard
        self.jace_perms = []  # Permanents mit wiederkehrendem Empower: (Karte, Schritt des Eintritts)
        self.surveilled = False  # in diesem Zug gesurveilt (Surveillance Phantasm)
        self.gained = 0       # in diesem Zug gewonnenes Leben (Enlightened Confidant)
        self.exiled = []      # vom Gegner exilierte Karten, die wir ab Threshold wirken duerfen (Null Summoner)
        self.exiled_from = None  # Besitzer dieser Karten (der Gegner)
        self.opponent = None  # der andere Spieler (Thalia: Steuer auf unsere Zauber)
        self.now = 0          # aktueller Schritt (fuer Token aus Faehigkeiten)
        self.turn_start = 0   # Schritt, in dem unser letzter Zug begann (Token mit {T} erst danach nutzbar)

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


def discount(p):
    """Nichtkreatur-Zauber kosten so viel generisches Mana weniger (Geist of Saint Thalia, eigene Karten) bzw. mehr
    (negativ: Thalia, the Survivor beim Gegner)."""
    own = sum(c.card.spell_discount for c in p.creatures if not c.dead) + sum(c.spell_discount for c in p.perms)
    opp = p.opponent
    tax = 0 if opp is None else (sum(c.card.opp_spell_tax for c in opp.creatures if not c.dead)
                                  + sum(c.opp_spell_tax for c in opp.perms))
    return own - tax


def _discounted(card, d):
    if not d or card.is_creature or card.is_land or not card.alts:
        return card
    return card._replace(alts=tuple(sorted({(max(0, g - d), cols) for g, cols in card.alts})))


def _alts(p, card):
    return _discounted(card, discount(p)).alts


def _sculptures(p):
    """Token mit "{T}, Sacrifice: Add one mana of any color", die schon seit Beginn unseres Zugs da sind."""
    return [c for c in p.creatures if c.card.sac_mana and not c.dead and not c.tapped and c.entered < p.turn_start]


def treasure_count(p):
    return p.treasures + len(_sculptures(p))


def _spend_treasures(p, k, remove=True):
    """k Mana aus Treasure: erst Treasure-Token, dann Sculpture-Token (geopfert; remove=False: nur als tot markiert,
    damit Indizes der Kreaturen in der Main Phase gueltig bleiben)."""
    use = min(k, p.treasures)
    p.treasures -= use
    for c in _sculptures(p)[:k - use]:
        if remove:
            p.creatures.remove(c)
        else:
            c.dead = True


def _payable(p, alts):
    if pay(p.open, alts) is not None:
        return True
    n = treasure_count(p)
    return n > 0 and pay(list(p.open) + [ANY_COLOR] * n, alts) is not None


def _pay_open(p, alts, treasure=True):
    """Bezahlt alts aus p.open; Treasure nur, wenn es ohne nicht reicht (so wenige wie moeglich)."""
    rest = pay(p.open, alts)
    k = 0
    while rest is None and treasure and k < treasure_count(p):
        k += 1
        rest = pay(list(p.open) + [ANY_COLOR] * k, alts)
    if rest is None:
        return False
    if k:  # nicht genutzte Treasure bleiben Token
        unused = sum(1 for u in rest if u == ANY_COLOR)
        rest = [u for u in rest if u != ANY_COLOR]
        _spend_treasures(p, k - unused)
    p.open = rest
    return True


def affordable(p, card):
    """Kann p die Karte mit offenem Mana (notfalls mit Treasure) bezahlen?"""
    return _payable(p, _alts(p, card))


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


def _jace_add(p, n, e=None):
    """Loyalty fuer Jace; Kreaturen mit "whenever you put loyalty counters" (Tethermage) bekommen sofort ihre Marken."""
    if n <= 0:
        return
    before = p.jace.events
    p.jace.add(n)
    delta = p.jace.events - before
    for c in p.creatures:
        if c.card.loyalty_counter and not c.dead:
            c.bonus += c.card.loyalty_counter * delta
    if e is not None:
        e["events"].append(f"{p.name}: Jace +{n} (Loyalty {p.jace.loyalty})")


def _jace_activate(p, step, e, allow_surveil):
    loyalty, lands = p.jace.loyalty, p.jace.surveil_lands
    if p.jace.try_activate(p.hand, p.library, step, battlefield=p.lands, allow_surveil=allow_surveil):
        if p.jace.loyalty == loyalty - 3:
            e["events"].append(f"{p.name}: Jace −3, zieht eine Karte (Loyalty {p.jace.loyalty})")
        else:
            mark_surveil(p)
            binned = p.jace.surveil_lands - lands
            e["events"].append(f"{p.name}: Jace −1, Surveil 1" + (" (Land abgelegt)" if binned else "")
                               + f" (Loyalty {p.jace.loyalty})")


def jace_turn_start(p, step, e=None):
    """Rundenbeginn: Ausloeser "zu Beginn deines Zugs", danach ab 3 Loyalty eine Karte ziehen."""
    p.jace.used = False
    for pc, t_in in list(p.jace_perms):
        if t_in < step:
            for ef in recurring_effects(pc):
                if ef[1] == "trigger" and ef[3] == "turn":
                    _jace_add(p, ef[2], e)
    _jace_activate(p, step, e if e is not None else {"events": []}, False)


def gain_life(p, n, events=1):
    """Lebensgewinn; events: Zahl der einzelnen Lebensgewinne (Lyra: jeder loest einmal aus, die Menge zaehlt nicht).
    Marken nur fuer Kreaturen, die noch leben (nach dem Kampfschaden); die Quelle selbst darf dabei gestorben sein."""
    if n <= 0:
        return
    p.life += n
    p.gained += n
    for _ in range(events):
        for c in p.creatures:  # auch eine im selben Kampf gestorbene Lyra loest aus (gleichzeitig mit dem Schaden)
            if c.card.lifegain_counter:
                k, typ = c.card.lifegain_counter
                for x in p.creatures:
                    if not x.dead and typ in x.card.creature_types:
                        x.bonus += k


def combat_life(att, dfn, res):
    """Lifelink nach dem Kampfschaden (vor dem Aufraeumen der gestorbenen Kreaturen)."""
    gain_life(att, res["lifelink_attacker"], res["lifelink_events_attacker"])
    gain_life(dfn, res["lifelink_defender"], res["lifelink_events_defender"])


def mark_surveil(p):
    p.surveilled = True
    for c in p.creatures:
        if c.card.surveil_attack:
            c.lifted = True


def on_cast(p, card, step, e):
    """Ein Zauber wurde gewirkt: Jace-Ausloeser, Marken fuer Zauber mit Ziel beim Gegner (Danitha)."""
    _jace_on_cast(p, card, step, e)
    if not card.is_creature:
        for c in list(p.creatures):
            if c.card.cast_token is not None and not c.dead:
                token = Creature(c.card.cast_token, step)
                p.creatures.append(token)
                e["events"].append(f"{p.name}: {c.card.name} – Token {token.card.name}")
                creature_enters(p, token, step, e, cast=False)
    if card.targets_opp:
        for c in p.creatures:
            if c.card.target_cast_counter and not c.dead:
                c.bonus += c.card.target_cast_counter
                e["events"].append(f"{p.name}: {c.card.name} +{c.card.target_cast_counter}/+"
                                   f"{c.card.target_cast_counter}")


def _tapped_lands(p):
    """Laender einer Art (gleiche Farben), die getappt sind: mehr Laender dieser Art als offenes Mana davon."""
    lands = Counter(land.land_colors for land in p.lands)
    units = Counter(p.open)
    return {cols: n - min(n, units[cols]) for cols, n in lands.items()}


def _redundant_land(p):
    """Land, das am wenigsten fehlt: farblos zuerst, sonst das Land, dessen Farben am haeufigsten vorkommen; bei
    Gleichstand ein getapptes Land, dann ein Basic Land."""
    count = Counter(col for land in p.lands for col in set(land.land_colors))
    tapped = _tapped_lands(p)
    return max(p.lands, key=lambda land: (min((count[c] for c in land.land_colors), default=99),
                                          tapped[land.land_colors] > 0, land.is_basic))


def creature_enters(p, new, step, e, opp=None, cast=True):
    """Eine Kreatur kam ins Spiel (schon in p.creatures): Leben (Greenhouse Propagator), Marken auf eine Kreatur, die
    in diesem Zug kam (Mabel), Team-Pump nach Artefakten (Craterclaw Colossus), Land gegen Token (Tenured
    Tethermage), Mill und Land zurueck (Primal Witchstalker), Exil aus der Hand des Gegners (Null Summoner, nur wenn
    gewirkt)."""
    card = new.card
    if card.land_to_tokens and p.lands:
        n, token = card.land_to_tokens
        sac = _redundant_land(p)
        if not _tapped_lands(p)[sac.land_colors] and sac.land_colors in p.open:
            p.open.remove(sac.land_colors)  # ungetapptes Land: sein Mana fehlt jetzt
        p.lands.remove(sac)
        p.graveyard.append(sac)
        p.perms += [token] * n
        e["events"].append(f"{p.name}: {card.name} opfert {sac.name}, {n} {token.name}-Token")
    if card.mill_land:
        milled = p.library[:card.mill_land]
        del p.library[:card.mill_land]
        p.graveyard.extend(milled)
        lands = [c for c in p.graveyard if c.is_land]
        if lands:
            have = set().union(*(land.land_colors for land in p.lands)) if p.lands else set()
            pick = max(lands, key=lambda land: (len(set(land.land_colors) - have), -lands.index(land)))
            p.graveyard.remove(pick)
            p.lands.append(pick)
            e["events"].append(f"{p.name}: {card.name} – Mill {len(milled)}, {pick.name} aus dem Friedhof")
            if opp is not None:
                on_land(p, opp, pick, step, e, with_mana=False)
    if card.null_summoner and cast and opp is not None:
        pool = [c for c in opp.hand if not c.is_land]
        if pool:
            removal = [c for c in pool if c.removal or c.hand_removal]
            pick = max(removal or pool, key=lambda c: (c.mv, c.name))
            opp.hand.remove(pick)
            p.exiled.append(pick)
            p.exiled_from = opp
            e["events"].append(f"{p.name}: {card.name} exiliert {pick.name} aus der Hand von {opp.name}")
    new.lifted = p.surveilled and new.card.surveil_attack
    alive = [c for c in p.creatures if not c.dead]
    for c in alive:
        if c is not new and c.card.ally_enter_life:
            gain_life(p, c.card.ally_enter_life)
    for c in alive:
        if c.card.enter_counter:
            fresh = [x for x in alive if x.entered == step]
            if fresh:
                pick = max(fresh, key=danger)
                pick.bonus += c.card.enter_counter
                e["events"].append(f"{p.name}: {c.card.name} – Marke auf {pick.card.name}")
    if new.card.artifact_pump:
        x = sum(c.card.is_artifact for c in alive) + sum(c.is_artifact for c in p.perms)
        for c in alive:
            c.pump += x
            c.extra |= set(new.card.artifact_pump)
        e["events"].append(f"{p.name}: {new.card.name} – alle +{x}/+0 und {', '.join(new.card.artifact_pump)}")


def _jace_on_cast(p, card, step, e):
    if not p.jace_perms and not once_effects(card) and not recurring_effects(card):
        return
    for pc, _t in list(p.jace_perms):
        for ef in recurring_effects(pc):
            if ef[1] == "trigger" and ef[3].startswith("cast:") and cast_filter_matches(ef[3][5:], card):
                _jace_add(p, ef[2], e)
    for ef in once_effects(card):
        _jace_add(p, ef[2], e)
    if not card.is_instant_sorcery:
        _jace_on_enter(p, card, step, e)


def _jace_on_enter(p, card, step, e):
    for pc, _t in list(p.jace_perms):
        for ef in recurring_effects(pc):
            if ef[1] == "trigger" and ef[3].startswith("enter:") and enter_filter_matches(ef[3][6:], card):
                _jace_add(p, ef[2], e)
    if recurring_effects(card):
        p.jace_perms.append((card, step))


def _leave(p, card):
    """Eine Kreatur verlaesst das Feld: ihre Empower-Faehigkeiten gelten nicht mehr."""
    for i, (pc, _t) in enumerate(p.jace_perms):
        if pc == card:
            del p.jace_perms[i]
            return


def walker_flags(p):
    """(Planeswalker auf dem Feld, Jace auf dem Feld) fuer Laender wie im Goldfish."""
    walkers = [c for c in p.perms if c.is_planeswalker]
    return p.jace.loyalty > 0 or bool(walkers), p.jace.loyalty > 0 or any(c.is_jace for c in walkers)


def surveil_cards(p, amounts, e, source):
    amounts = [a for a in amounts if a]
    if not amounts:
        return
    before = len(p.graveyard)
    mark_surveil(p)
    apply_surveils(amounts, p.library, p.hand, p.lands, graveyard=p.graveyard)
    binned = len(p.graveyard) - before
    e["events"].append(f"{p.name}: {source} – Surveil {sum(amounts)}" + (f" ({binned} abgelegt)" if binned else ""))


def on_land(me, opp, land, step, e, with_mana=True):
    """Ein Land kommt ins Spiel: Landfall, Surveil des Landes, Jace-Ausloeser. Gibt zusaetzliches Mana zurueck."""
    mana = []
    if me.creatures:
        board, bonus, pump = me.board()
        face, mana, _cnt = landfall_effects(land, board, bonus, step, with_mana=with_mana)
        me.write_back(bonus, pump)
        for c in list(me.creatures):
            if c.card.landfall_life and not c.dead:
                gain_life(me, c.card.landfall_life)
        opp.life -= face
        me.dealt_direct += face
        e["face"] += face
    if land.surveil:
        surveil_cards(me, [land.surveil], e, land.name)
    for ef in once_effects(land):
        if ef[1] == "etb":
            _jace_add(me, ef[2], e)
    _jace_on_enter(me, land, step, e)
    return mana


def upkeep(p):
    """Upkeep: "if this creature isn't prepared, it becomes prepared"."""
    for c in p.creatures:
        if c.card.prepared and c.card.prepared[0] in ("upkeep", "both"):
            c.prepared = True


def _cycle_event(p, cycler, cand, e, when):
    e["events"].append(f"{p.name}: Landcycling {cycler.name} → {cand.name} ({when})")


def bury(players, e):
    """Gestorbene Kreaturen in den Friedhof (Schaden, Deathtouch, Toughness 0)."""
    for p in players:
        for c in list(p.creatures):
            if c.dead or c.toughness <= 0 or c.damage >= c.toughness or (c.touched and c.damage > 0):
                p.deaths += 1
                p.creatures.remove(c)
                if not c.card.is_token:
                    (c.owner or p).graveyard.append(c.card)
                _leave(p, c.card)
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
        caster.dealt_direct += amount
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
        if not target.card.is_token:
            (target.owner or victim).hand.append(target.card)
        _leave(victim, target.card)
        e["events"].append(f"{caster.name}: {card.name} – {label} zurück auf die Hand")
        return
    elif kind == "lock":
        target.locked = True
        e["events"].append(f"{caster.name}: {card.name} – {label} gesperrt")
        return
    e["events"].append(f"{caster.name}: {card.name} – {label}")
    bury((caster, victim), e)


def _resolve(me, opp, card, step, entry, owner=None):
    """Eine gewirkte Karte kommt ins Spiel bzw. wirkt: Kreatur aufs Feld, Permanents, Instants/Sorceries in den
    Friedhof; Removal, Abwerfen und Effekte (Schaden an den Gegner, Marken, Pumps) wie im Goldfish."""
    if card.is_copy:  # Prepared-Kopie: eine passende Kreatur ist nicht mehr prepared, kein Friedhof
        src = next((c for c in me.creatures if c.prepared and c.card.prepared[1] == card), None)
        if src is not None:
            src.prepared = False
    elif card.is_creature:
        me.creatures.append(Creature(card, step))
        me.creatures[-1].owner = owner
    elif card.is_instant_sorcery:
        (owner or me).graveyard.append(card)
    else:
        me.perms.append(card)
    if card.treasure:
        me.treasures += card.treasure
    on_cast(me, card, step, entry)
    if card.is_creature and not card.is_copy:
        creature_enters(me, me.creatures[-1], step, entry, opp)
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
        before = [c.pump for c in me.creatures]
        gain = apply_effects(effects, board, bonus, pump, step)
        me.write_back(bonus, pump)
        ratio = _tough_ratio(card)
        for c, old in zip(me.creatures, before):  # Pumps +P/+T: Toughness im Verhaeltnis T/P
            if c.pump > old:
                c.tpump += round((c.pump - old) * ratio)
        if gain["face"]:
            opp.life -= gain["face"]
            me.dealt_direct += gain["face"]
            entry["face"] += gain["face"]
    if card.draws:
        for _ in range(card.draws):
            if me.library:
                me.hand.append(me.library.pop(0))
    if card.surveil:
        surveil_cards(me, [card.surveil], entry, card.name)
    make_tokens(me, card.creates_tokens, step, entry, opp, card.name)
    bury((me, opp), entry)


def make_tokens(p, tokens, step, e, opp=None, source=""):
    """Kreatur-Token ins Spiel (kommen nicht in den Friedhof, verschwinden beim Bounce)."""
    for n, token in tokens:
        for _ in range(n):
            c = Creature(token, step)
            p.creatures.append(c)
            creature_enters(p, c, step, e, opp, cast=False)
        e["events"].append(f"{p.name}: {source} – {n} {token.name}-Token")


def _tough_ratio(card):
    """Verhaeltnis Toughness/Power des ersten Pumps einer Karte (+2/+2 -> 1, +3/+1 -> 1/3)."""
    for mode, tough in zip(card.modes, card.pump_tough or ()):
        pumps = [a for a in mode if a[0] in ("pump", "pump_all")]
        if pumps and tough and pumps[0][1]:
            return tough[0] / pumps[0][1]
    return 1.0


def main_phase_spells(me, opp):
    """Karten fuer die Main Phases: keine Instants, keine Flash-Karten, Removal nur mit gueltigem Ziel; dazu die
    Kopien der Prepared-Kreaturen."""
    cards = [c for c in me.hand if not c.is_land] + copies(me)
    return [c for c in cards if not c.is_instant and not c.flash
            and (not c.removal or c.removal[4] == "etb" or has_target(c, me, opp))]


def copies(p):
    return [c.card.prepared[1] for c in p.creatures if c.prepared and not c.dead]


def _cast_from_open(p, card):
    if not _pay_open(p, _alts(p, card)):
        return False
    p.hand.remove(card)
    return True


def _trick_atoms(card):
    return [m for m in card.modes if any(a[0] in ("pump", "counter", "pump_all", "counter_all") for a in m)]


def _trick_modes(card):
    """[(Modus, Toughness der Pumps)] der Kampftrick-Modi einer Karte."""
    tough = card.pump_tough or ()
    return [(m, tough[i] if i < len(tough) else ()) for i, m in enumerate(card.modes)
            if any(a[0] in ("pump", "counter", "pump_all", "counter_all") for a in m)]


def _apply_trick(mode, target, own, tough=()):
    k = 0
    for atom in mode:
        if atom[0] in ("pump", "pump_all"):
            t = tough[k] if k < len(tough) else atom[1]
            k += 1
            for c in ([target] if atom[0] == "pump" else own):
                c.pump += atom[1]
                c.tpump += t
        elif atom[0] == "counter":
            target.bonus += atom[1]
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
        if not affordable(p, card):
            continue
        base = _score(pairs, attacking, opp.life)
        best = None
        for mode, tough in _trick_modes(card):
            for i, target in enumerate(own):
                saved = [(c.pump, c.bonus, c.tpump) for c in own]
                _apply_trick(mode, target, own, tough)
                gain = _score(pairs, attacking, opp.life) - base
                for c, (pu, bo, tp) in zip(own, saved):
                    c.pump, c.bonus, c.tpump = pu, bo, tp
                if gain > 0 and (best is None or gain > best[0]):
                    best = (gain, mode, i, tough)
        if best is None:
            continue
        _cast_from_open(p, card)
        _apply_trick(best[1], own[best[2]], own, best[3])
        if card.is_creature:
            p.creatures.append(Creature(card, step))
            creature_enters(p, p.creatures[-1], step, e, opp)
        elif card.is_instant_sorcery:
            p.graveyard.append(card)
        on_cast(p, card, step, e)
        e["events"].append(f"{p.name}: Kampftrick {card.name} auf {own[best[2]].card.name}")


def instant_removals(p):
    """Removal, das p jederzeit einsetzen kann: [(Karte, Kosten, Karte mit Removal-Spec, ist Zauber, Zone)].
    Instants mit Removal, Faehigkeiten "Kosten, Discard this card: Removal" (Sureshot Sower, kein Zauber) und ab
    Threshold exilierte Removal-Instants (Null Summoner, Mana jeder Art)."""
    out = []
    for card in p.hand:
        if card.is_instant and card.removal and card.removal[4] == "spell":
            out.append((card, _alts(p, card), card, True, "hand"))
        elif card.hand_removal:
            out.append((card, card.hand_removal[0], card._replace(removal=card.hand_removal[1]), False, "hand"))
    if threshold(p):
        for card in p.exiled:
            if card.is_instant and card.removal and card.removal[4] == "spell":
                out.append((card, _discounted(_any_mana(card), discount(p)).alts, card, True, "exile"))
    return out


def threshold(p):
    return len(p.graveyard) >= 7


def _any_mana(card):
    """Kosten mit Mana jeder Art (nur noch der Manawert zaehlt)."""
    return card._replace(alts=((card.mv, ()),)) if card.alts else card


def _use_removal(p, card, alts, is_spell, step, e, zone="hand", other=None):
    """Bezahlt und legt die Karte in den Friedhof (gewirkt oder abgeworfen); aus dem Exil in den Friedhof des
    Besitzers (other: der Gegner, falls der Besitzer nicht gespeichert ist)."""
    if not _pay_open(p, alts):
        return False
    (p.exiled if zone == "exile" else p.hand).remove(card)
    ((p.exiled_from or other or p) if zone == "exile" else p).graveyard.append(card)
    if is_spell:
        on_cast(p, card, step, e)
    else:
        e["events"].append(f"{p.name}: wirft {card.name} ab (Fähigkeit)")
    return True


def respond_to_attack(dfn, att, attackers, e, step):
    """Der Verteidiger reagiert auf die Angreifer: Removal-Instants auf den gefaehrlichsten Angreifer, Flash-Kreaturen
    fuer einen guten Block oder gegen Lethal. Gibt die verbleibenden Angreifer zurueck."""
    while True:
        alive = [a for a in attackers if a in att.creatures and not a.dead and not a.locked]
        options = []
        for card, alts, rc, is_spell, zone in instant_removals(dfn):
            if not _payable(dfn, alts):
                continue
            spec = rc.removal
            if spec[0] in ("sweep", "sweep_damage", "edict"):
                continue
            targets = [a for a in valid_targets(spec, dfn, att) if a in alive]
            if targets:
                options.append((danger(max(targets, key=danger)), card, max(targets, key=danger), alts, rc, is_spell,
                                zone))
        if not options:
            break
        _d, card, target, alts, rc, is_spell, zone = max(options, key=lambda o: (o[0], -o[1].mv))
        _use_removal(dfn, card, alts, is_spell, step, e, zone, att)
        cast_removal(rc, dfn, att, e, step, target=target)
    alive = [a for a in attackers if a in att.creatures and not a.dead and not a.locked]
    for card in sorted([c for c in dfn.hand if c.flash and c.is_creature], key=lambda c: -c.mv):
        if not affordable(dfn, card):
            continue
        new = Creature(card, step)
        blockers = [b for b in dfn.creatures if not b.tapped and not b.dead]
        lethal = max_through(alive, blockers) >= dfn.life and max_through(alive, blockers + [new]) < dfn.life
        good = any(can_block(new, a) and outcome(a, [new]) == (True, [False]) for a in alive)
        if lethal or good:
            _cast_from_open(dfn, card)
            dfn.creatures.append(new)
            e["events"].append(f"{dfn.name}: {card.name} mit Flash als Blocker")
            if card.treasure:
                dfn.treasures += card.treasure
            on_cast(dfn, card, step, e)
            creature_enters(dfn, new, step, e, att)
    return alive


def end_step_instants(dfn, act, e, step):
    """Am Ende des Zugs von act nutzt dfn sein offenes Mana: Removal auf die gefaehrlichste Kreatur, Flash-Kreaturen,
    sonstige Instants (z. B. Ziehen), danach Landcycling mit dem Rest. Kampftricks bleiben auf der Hand."""
    for card, alts, rc, is_spell, zone in sorted(instant_removals(dfn), key=lambda o: o[0].mv):
        if card not in (dfn.exiled if zone == "exile" else dfn.hand) or not _payable(dfn, alts) \
                or not has_target(rc, dfn, act):
            continue
        if rc.removal[3] and choose_target(rc.removal, dfn, act) is None and act.life > _amount(rc.removal, dfn):
            continue  # "any target" am Endstep nur gegen eine Kreatur oder als Lethal
        _use_removal(dfn, card, alts, is_spell, step, e, zone, act)
        cast_removal(rc, dfn, act, e, step)
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
    end_step_cycling(dfn, e)
    lasting_abilities(dfn, act, step, e, own_turn=False, mode="rest")
    tap_artifact_abilities(dfn, e)


def confidant_end_step(p, e):
    """Enlightened Confidant: nach Lebensgewinn in diesem Zug Surveil 1; eine abgelegte Karte mit Manawert hoechstens
    dem gewonnenen Leben kommt auf die Hand."""
    for c in p.creatures:
        if not c.card.confidant or c.dead or p.gained <= 0 or not p.library:
            continue
        mark_surveil(p)
        for card in surveil(p.library, 1, p.hand, p.lands):
            if card.mv <= p.gained:
                p.hand.append(card)
                e["events"].append(f"{p.name}: {c.card.name} – Surveil 1, {card.name} auf die Hand")
            else:
                p.graveyard.append(card)


def tap_artifact_abilities(p, e):
    """Am Ende des gegnerischen Zugs: "Tap N untapped artifacts you control" (Tenured Tethermage) mit Artefakten, die
    nicht mehr gebraucht werden: offenes Mana von Artefakt-Token und ungetappte Artefaktkreaturen."""
    artifact_units = [u for card in p.perms if card.is_artifact for u in card.mana_src]
    for c in list(p.creatures):
        if not c.card.tap_artifacts or c.dead:
            continue
        n, atoms = c.card.tap_artifacts
        for _round in range(10):
            units = [u for u in p.open if u in artifact_units]
            free_units = min(len(units), len(artifact_units))
            creatures = [x for x in p.creatures if x.card.is_artifact and not x.tapped and not x.dead]
            if free_units + len(creatures) < n:
                break
            take = min(free_units, n)
            for u in units[:take]:
                p.open.remove(u)
                artifact_units.remove(u)
            for x in creatures[:n - take]:
                x.tapped = True
            apply_ability(p, c, ((), 0, False, "instant", atoms), None, e)
            e["events"].append(f"{p.name}: {c.card.name} tappt {n} Artefakte")


def end_step_cycling(p, e):
    """Landcycling am Ende des gegnerischen Zugs mit uebrigem offenem Mana (ohne Treasure): solange Laender auf Feld
    und Hand unter CYCLE_CAP liegen, die Karte naechste Runde nicht ohnehin spielbar ist und es nicht die letzte
    Karte auf der Hand ist."""
    while True:
        hand_lands = [c for c in p.hand if c.is_land]
        if len(p.lands) + len(hand_lands) >= CYCLE_CAP:
            return
        next_pool = [c.land_colors for c in p.lands] + ([hand_lands[0].land_colors] if hand_lands else [])
        spells = [c for c in p.hand if not c.is_land]
        done = False
        for cycler in sorted({c for c in spells if c.cycle_alts}, key=lambda c: (c.cycle_mv, c.name)):
            if len(p.hand) <= 1 or pay(next_pool, cycler.alts) is not None:
                continue
            plan = plan_cycle(cycler, list(p.open), spells, p.lands, p.library, hand_lands, False,
                              bool(p.creatures), True)
            if not plan:
                continue
            rem, cand = plan
            do_cycle(p.hand, p.library, cycler, cand, graveyard=p.graveyard)
            p.open = rem
            _cycle_event(p, cycler, cand, e, "Ende des gegnerischen Zugs")
            done = True
            break
        if not done:
            return


# ---------------------------------------------------------------------------------------------------------------------
# Aktivierbare Faehigkeiten (Card.abilities): Pumps, Schluesselwoerter, Marken, Empower
# ---------------------------------------------------------------------------------------------------------------------

def _speed_ok(ab, own_turn, main):
    if ab[3] == "sorcery":
        return own_turn and main
    if ab[3] == "own_turn":
        return own_turn
    return True


def ability_sources(p, step, own_turn, main=False):
    """Aktivierbare Faehigkeiten von p: [(Kreatur oder None, Faehigkeit)]. Tap-Faehigkeiten nur von ungetappten
    Kreaturen, die seit Beginn des eigenen Zugs da sind (oder Haste)."""
    out = []
    for c in p.creatures:
        if c.dead:
            continue
        for ab in c.card.abilities:
            if not _speed_ok(ab, own_turn, main):
                continue
            if ab[2] and (c.tapped or not (c.entered < step or c.card.haste)):
                continue
            out.append((c, ab))
    for card in p.perms:
        for ab in card.abilities:
            if _speed_ok(ab, own_turn, main) and not ab[2] and not any(a[-1] == "self" for a in ab[4]):
                out.append((None, ab))
    return out


def _kinds(ab):
    return {a[0] for a in ab[4]}


def _needs_target(ab):
    return any(len(a) > 2 and a[-1] in ("target", "nonlegendary") for a in ab[4])


def _targets(p, src, ab, pool=None):
    if not _needs_target(ab):
        return [None]
    cands = [c for c in (pool if pool is not None else p.creatures) if not c.dead and c in p.creatures]
    if any(a[-1] == "nonlegendary" for a in ab[4] if len(a) > 2):
        cands = [c for c in cands if not c.card.legendary]
    return cands


def _snapshot(p):
    return [(c, c.pump, c.tpump, c.bonus, set(c.extra)) for c in p.creatures]


def _restore(snap):
    for c, pu, tp, bo, ex in snap:
        c.pump, c.tpump, c.bonus, c.extra = pu, tp, bo, ex


def apply_ability(p, src, ab, target, e=None):
    """Wirkung einer Faehigkeit (src: Quelle, target: gewaehltes Ziel). Gibt False zurueck, wenn sie nichts bewirkt."""
    did = False
    for atom in ab[4]:
        kind = atom[0]
        if kind == "empower":
            if e is not None:
                _jace_add(p, atom[1], e)
            else:
                p.jace.add(atom[1])
            did = True
            continue
        if kind == "surveil":
            if e is not None:
                surveil_cards(p, [atom[1]], e, "Fähigkeit")
            did = True
            continue
        if kind == "token":
            if e is not None:
                make_tokens(p, [atom[1:]], p.now, e, p.opponent, src.card.name if src is not None else "Fähigkeit")
            did = True
            continue
        scope = atom[-1]
        if scope == "all":
            hit = [c for c in p.creatures if not c.dead]
        elif scope == "countered":
            hit = [c for c in p.creatures if not c.dead and c.bonus > 0]
        elif scope == "self":
            hit = [src] if src is not None and not src.dead else []
        else:
            hit = [target] if target is not None else []
        for c in hit:
            if kind == "pump":
                c.pump += atom[1]
                c.tpump += atom[2]
            elif kind == "grant":
                c.extra |= set(atom[1])
            elif kind == "counter":
                c.bonus += atom[1]
            did = True
    return did


def _reserved(p):
    """Karten der Hand, die mit dem offenen Mana bis zum naechsten eigenen Zug noch gespielt werden koennten:
    Instants, Flash-Karten und Landcycling (solange Laender fehlen) - je Karte die Kosten."""
    out = []
    lands = len(p.lands) + sum(c.is_land for c in p.hand)
    for c in p.hand:
        if (c.is_instant or c.flash) and c.alts and pay(p.open, c.alts) is not None:
            out.append(c.alts)
        elif c.cycle_alts and lands < CYCLE_CAP and pay(p.open, c.cycle_alts) is not None:
            out.append(c.cycle_alts)
    return out


def _pay_ability(p, alts, mode):
    """mode: "free" - nur freies Mana (danach bleibt jede vorher bezahlbare Instant-/Flash-/Cycling-Karte bezahlbar),
    "any" - offenes Mana und notfalls Treasure (Lethal, besserer Block), "rest" - offenes Mana ohne Treasure."""
    if mode == "free":
        rest = pay(p.open, alts)
        if rest is None or any(pay(rest, need) is None for need in _reserved(p)):
            return False
        p.open = rest
        return True
    return _pay_open(p, alts, treasure=(mode == "any"))


def _activate(p, src, ab, target, e, mode, gy=None):
    """Bezahlt und wirkt eine Faehigkeit; gy: Karte im Friedhof, die dafuer exiliert wird (Campus Crier)."""
    if not _pay_ability(p, ab[0], mode):
        return False
    if ab[2] and src is not None:
        src.tapped = True
    if gy is not None:
        p.graveyard.remove(gy)
    who = src.card.name if src is not None else (f"{gy.name} (aus dem Friedhof)" if gy is not None else "Permanent")
    e["events"].append(f"{p.name}: Fähigkeit von {who}" + (f" auf {target.card.name}" if target is not None else ""))
    apply_ability(p, src, ab, target, e)
    return True


def _ab_score(pairs, attacking, defender_life):
    """Bewertung eines Kampfs fuer Faehigkeiten: Kreaturen wie bei Kampftricks, dazu Schaden am Verteidiger
    (Angreifer: mehr ist besser, Verteidiger: weniger), Lifelink und Lethal."""
    copies = [(a.copy(), [b.copy() for b in bs]) for a, bs in pairs]
    res = resolve_combat(copies)
    score = 0
    for a, bs in copies:
        own, other = ([a], bs) if attacking else (bs, [a])
        score -= sum(10 * c.card.mv + c.power + c.toughness for c in own if c.dead)
        score += sum(10 * c.card.mv + c.power + c.toughness for c in other if c.dead)
    lethal = res["player"] >= defender_life
    if attacking:
        score += res["player"] + res["lifelink_attacker"] + (1000 if lethal else 0)
    else:
        score += -res["player"] + res["lifelink_defender"] - (1000 if lethal else 0)
    return score, lethal


def combat_abilities(p, pairs, opp, e, step, attacking):
    """Pumps und Schluesselwoerter nach den Blockern. Angreifer: bei Lethal (auch mit Mana fuer Instants und Treasure),
    sonst nur mit freiem Mana, wenn es den Kampf verbessert (mehr Schaden, Kreatur ueberlebt, Blocker stirbt).
    Verteidiger: wenn der Block besser wird."""
    own = [a for a, _bs in pairs if not a.dead] if attacking else [b for _a, bs in pairs for b in bs if not b.dead]
    if not own:
        return
    defender_life = opp.life if attacking else p.life
    for _round in range(20):
        base, base_lethal = _ab_score(pairs, attacking, defender_life)
        options = []
        for src, ab in ability_sources(p, step, own_turn=attacking):
            if not _kinds(ab) & {"pump", "grant"}:
                continue
            if any(a[-1] == "self" for a in ab[4]) and src not in own:
                continue
            for target in _targets(p, src, ab, own):
                snap = _snapshot(p)
                apply_ability(p, src, ab, target)
                score, lethal = _ab_score(pairs, attacking, defender_life)
                _restore(snap)
                if score > base:
                    options.append((score - base, lethal and not base_lethal, src, ab, target))
        done = False
        for _gain, lethal, src, ab, target in sorted(options, key=lambda o: -o[0]):
            mode = "any" if (lethal or not attacking) else "free"
            if _activate(p, src, ab, target, e, mode):
                done = True
                break
        if not done:
            return


def _attack_value(me, opp, step):
    attackers = choose_attackers(me.creatures, opp.creatures, opp.life, me.life, step)
    return max_through(attackers, [b for b in opp.creatures if not b.tapped and not b.dead])


def lasting_abilities(p, opp, step, e, own_turn, mode):
    """Marken, Empower und Surveil (nur am Ende des gegnerischen Zugs): Marken zuerst (auf die gefaehrlichste passende
    Kreatur), dann Empower, dann Surveil. Dazu Faehigkeiten aus dem Friedhof (Campus Crier)."""
    rank = {"counter": 0, "token": 1, "empower": 2, "surveil": 3}
    for _round in range(10):
        sources = [(src, ab, None) for src, ab in ability_sources(p, step, own_turn, main=own_turn)]
        sources += [(None, (card.gy_ability[0], 0, False, "instant", card.gy_ability[1]), card)
                    for card in dict.fromkeys(p.graveyard) if card.gy_ability]
        options = []
        for src, ab, gy in sources:
            kinds = _kinds(ab)
            if "grant" in kinds and "token" in kinds:  # Token und danach Haste fuer alle (Ingris)
                kinds = kinds - {"grant"}
            if not kinds or not kinds <= set(rank):
                continue
            if "surveil" in kinds and (own_turn or not p.library):
                continue
            for target in _targets(p, src, ab):
                if "counter" in kinds:
                    snap = _snapshot(p)
                    useful = apply_ability(p, src, ab, target)
                    _restore(snap)
                    if not useful:
                        continue
                options.append((min(rank[k] for k in kinds),
                                -(danger(target) if target is not None else (0, False, 0))[0], src, ab, target, gy))
        done = False
        for _r, _d, src, ab, target, gy in sorted(options, key=lambda o: (o[0], o[1])):
            if _activate(p, src, ab, target, e, mode, gy):
                done = True
                break
        if not done:
            return


def pre_attack_abilities(me, opp, step, e):
    """Eigene Main Phase vor dem Angriff: Marken und Empower mit freiem Mana, danach Flying/Menace verleihen, wenn
    dadurch mehr Schaden durchkommt (bei Lethal auch mit Mana fuer Instants und Treasure, sonst mit freiem Mana)."""
    lasting_abilities(me, opp, step, e, own_turn=True, mode="free")
    _surveil_to_attack(me, opp, step, e)
    for _round in range(10):
        base = _attack_value(me, opp, step)
        options = []
        for src, ab in ability_sources(me, step, own_turn=True, main=True):
            grants = {k for a in ab[4] if a[0] == "grant" for k in a[1]}
            if ab[2] or not grants & {"flying", "menace"} or not _kinds(ab) <= {"pump", "grant"}:
                continue
            pool = [c for c in me.creatures if can_attack(c, step)]
            if any(a[-1] == "self" for a in ab[4]) and src not in pool:
                continue
            for target in _targets(me, src, ab, pool):
                snap = _snapshot(me)
                apply_ability(me, src, ab, target)
                value = _attack_value(me, opp, step)
                _restore(snap)
                if value > base:
                    options.append((value, value >= opp.life > base, src, ab, target))
        done = False
        for _v, lethal, src, ab, target in sorted(options, key=lambda o: -o[0]):
            if _activate(me, src, ab, target, e, "any" if lethal else "free"):
                done = True
                break
        if not done:
            return


def _surveil_to_attack(me, opp, step, e):
    """Surveil-Faehigkeit, damit eine Kreatur trotz Defender angreifen darf (Surveillance Phantasm), wenn dadurch
    mehr Schaden durchkommt (bei Lethal auch mit Mana fuer Instants und Treasure, sonst mit freiem Mana)."""
    waiting = [c for c in me.creatures if c.card.surveil_attack and not c.lifted and not c.dead]
    if me.surveilled or not waiting or not me.library:
        return
    base = _attack_value(me, opp, step)
    for c in waiting:
        c.lifted = True
    value = _attack_value(me, opp, step)
    for c in waiting:
        c.lifted = False
    if value <= base:
        return
    for src, ab in ability_sources(me, step, own_turn=True, main=True):
        if _kinds(ab) == {"surveil"} and not (ab[2] and src in waiting):
            if _activate(me, src, ab, None, e, "any" if value >= opp.life > base else "free"):
                return


def pre_block_abilities(dfn, att, attackers, e, step):
    """Vor den Blockern (die Angreifer stehen fest): der Verteidiger pumpt oder verleiht Schluesselwoerter wie Flying
    oder Reach, wenn der Block dadurch besser wird."""
    alive = [a for a in attackers if a in att.creatures and not a.dead]
    if not alive:
        return
    for _round in range(10):
        base = _ab_score(choose_blocks(alive, dfn.creatures, dfn.life), False, dfn.life)[0]
        options = []
        for src, ab in ability_sources(dfn, step, own_turn=False):
            if ab[2] or not _kinds(ab) or not _kinds(ab) <= {"pump", "grant"}:
                continue
            pool = [c for c in dfn.creatures if not c.tapped and not c.dead]
            if any(a[-1] == "self" for a in ab[4]) and src not in pool:
                continue
            for target in _targets(dfn, src, ab, pool):
                snap = _snapshot(dfn)
                apply_ability(dfn, src, ab, target)
                score = _ab_score(choose_blocks(alive, dfn.creatures, dfn.life), False, dfn.life)[0]
                _restore(snap)
                if score > base:
                    options.append((score - base, src, ab, target))
        done = False
        for _g, src, ab, target in sorted(options, key=lambda o: -o[0]):
            if _activate(dfn, src, ab, target, e, "any"):
                done = True
                break
        if not done:
            return


def _desc(cs):
    return [c.label() + (" (getappt)" if c.tapped else "") + (" (gesperrt)" if c.locked else "") for c in cs]


def take_turn(me, opp, step, rnd, skip_draw):
    """Ein Zug von me. Gibt den Protokolleintrag zurueck."""
    e = {"player": me.name, "round": rnd, "drew": None, "land": None, "main1": [], "main2": [], "attacks": [],
         "damage": 0, "face": 0, "deaths": [], "events": [], "note": ""}
    me.cast_count = 0
    me.turn_start = step
    me.opponent, opp.opponent = opp, me
    me.now = opp.now = step
    for c in me.creatures:  # Untap (gesperrte Kreaturen bleiben gesperrt)
        c.tapped = False
    upkeep(me)
    if not skip_draw:  # Draw
        if not me.library:
            me.lost = True
            e["note"] = "muss aus leerer Bibliothek ziehen"
            return e
        card = me.library.pop(0)
        me.hand.append(card)
        e["drew"] = card.name
    jace_turn_start(me, step, e)
    disc, orig = discount(me), {}  # Kostensenkung: verbilligte Handkarten fuer die Main Phase
    if disc:
        for i, c in enumerate(me.hand):
            cheap = _discounted(c, disc)
            if cheap != c:
                orig[cheap] = c
                me.hand[i] = cheap
    ex_map = {}  # ab Threshold: exilierte Karten (Null Summoner) mit Mana jeder Art, voruebergehend auf der Hand
    if me.exiled and threshold(me):
        for c in me.exiled:
            if not c.is_instant and not c.flash and not c.is_land:
                cheap = _discounted(_any_mana(c), disc)
                ex_map[cheap] = c
                me.hand.append(cheap)

    def cost(c):  # Prepared-Kopien mit Kostensenkung bzw. Steuer (Handkarten sind schon angepasst)
        if c.is_copy and disc:
            cheap = _discounted(c, disc)
            if cheap != c:
                orig[cheap] = c
                return cheap
        return c

    def phase_spells():
        return [cost(c) for c in main_phase_spells(me, opp)]
    # Main 1: Landcycling, wenn ein Land fuer den Landdrop fehlt
    pool, creature_units = _mana(me, step)
    spells = phase_spells()
    has_creature = bool(me.creatures)
    if rnd <= CYCLE_TURNS and not any(c.is_land for c in me.hand):
        for cycler in sorted({c for c in spells if c.cycle_alts}, key=lambda c: (c.cycle_mv, c.name)):
            if len(me.hand) <= 1:
                continue  # letzte Karte auf der Hand: nicht wegwerfen
            plan = plan_cycle(cycler, pool, spells, me.lands, me.library, [], True, has_creature, True)
            if plan:
                rem, cand = plan
                do_cycle(me.hand, me.library, cycler, cand, graveyard=me.graveyard)
                _cycle_event(me, cycler, cand, e, "Land fehlt")
                me.cast_count += 1
                pool = rem
                spells = phase_spells()
                break
    pool_all = pool + [u for u, _i in creature_units]
    # Land
    walker_bf, jace_bf = walker_flags(me)
    land, tapped, forced = choose_land(me.hand, spells, pool_all, me.lands, walker_bf, jace_bf, has_creature, True)
    if land is not None:
        me.hand.remove(land)
        me.lands.append(land)
        e["land"] = land.name + (" (getappt)" if tapped else "")
        if not tapped:
            pool_all = pool_all + [land.land_colors]
        pool_all = pool_all + on_land(me, opp, land, step, e)
    _score_, chosen = best_cast(spells, land_key(pool_all), has_creature, True, must=forced)
    if treasure_count(me) and forced is None:  # Treasure nur, wenn er diese Runde mehr ermoeglicht
        k_t, _ch = use_treasures(spells, pool_all, treasure_count(me), has_creature, True)
        if k_t:
            _spend_treasures(me, k_t, remove=False)
            pool_all = pool_all + [ANY_COLOR] * k_t
            e["events"].append(f"{me.name}: {k_t} Treasure geopfert")
            _score_, chosen = best_cast(spells, land_key(pool_all), has_creature, True)
    if any(c.draws for c in chosen) or enters_prepared(chosen) or any(usable_now(c) for c in chosen):
        walker_bf, jace_bf = walker_flags(me)
        rd = resolve_draws(me.hand, me.library, chosen, pool_all, me.lands, land, has_creature, True, walker_bf,
                           jace_bf, copies=[cost(c) for c in copies(me)])
        chosen = [c for c in rd["chosen"] if not c.is_instant and not c.flash]
        pool_all = rd["pool"]
        if rd["land"] is not None:
            e["land"] = rd["land"].name
            on_land(me, opp, rd["land"], step, e, with_mana=False)
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
        if not c.is_copy:
            me.hand.remove(c)
    if orig:  # wieder die Originalkarten
        me.hand[:] = [orig.get(c, c) for c in me.hand]
        chosen = [orig.get(c, c) for c in chosen]
    from_exile = Counter()  # aus dem Exil gewirkt: Besitzer ist der Gegner
    if ex_map:  # gewirkte exilierte Karten verlassen das Exil, die anderen bleiben dort
        for c in chosen:
            if c in ex_map:
                me.exiled.remove(ex_map[c])
                from_exile[ex_map[c]] += 1
        me.hand[:] = [c for c in me.hand if c not in ex_map]
        chosen = [ex_map.get(c, c) for c in chosen]
    owner_of = me.exiled_from or opp

    def resolve(c):
        owner = None
        if from_exile[c]:
            from_exile[c] -= 1
            owner = owner_of
        _resolve(me, opp, c, step, e, owner)
    me.cast_count += len(chosen)
    main1 = [c for c in chosen if not (c.is_creature and not c.haste)]
    main2 = [c for c in chosen if c.is_creature and not c.haste]
    done1 = []
    for c in main1:
        if c.is_copy and not any(x.prepared and x.card.prepared[1] == c for x in me.creatures):
            main2.append(c)  # Kopie einer Kreatur, die erst in Main 2 ins Spiel kommt
            continue
        resolve(c)
        done1.append(c)
    main1 = done1
    e["main1"] = [c.name for c in main1]
    if opp.life <= 0:
        return e
    # Removal-Instants vor dem Angriff: Blocker entfernen, die einen unserer Angreifer fressen wuerden
    candidates = [c for c in me.creatures if can_attack(c, step)]
    for card, alts, rc, is_spell, zone in sorted(instant_removals(me), key=lambda o: o[0].mv):
        if card not in (me.exiled if zone == "exile" else me.hand) or not _payable(me, alts):
            continue
        eaters = [t for t in valid_targets(rc.removal, me, opp) if any(_eats(t, a) for a in candidates)]
        if eaters:
            _use_removal(me, card, alts, is_spell, step, e, zone, opp)
            me.cast_count += 1 if is_spell else 0
            cast_removal(rc, me, opp, e, step, target=max(eaters, key=danger))
    # Faehigkeiten vor dem Angriff: Marken und Empower mit freiem Mana, Flying/Menace fuer den Angriff
    pre_attack_abilities(me, opp, step, e)
    # Kampf
    attackers = choose_attackers(me.creatures, opp.creatures, opp.life, me.life, step)
    art_vigilance = any(c.card.artifact_vigilance for c in me.creatures if not c.dead)
    for a in attackers:
        if not (a.has("vigilance") or (art_vigilance and a.card.is_artifact)):
            a.tapped = True
        for ef in recurring_effects(a.card):  # Angriffs-Ausloeser (Empower)
            if ef[1] == "trigger" and ef[3] == "attack" and any(pc == a.card for pc, _t in me.jace_perms):
                n = sum(1 for c in me.creatures if not c.dead) if ef[7] else ef[2]  # X = eigene Kreaturen
                _jace_add(me, n, e)
    attackers = respond_to_attack(opp, me, attackers, e, step)
    pre_block_abilities(opp, me, attackers, e, step)
    blocks = choose_blocks(attackers, opp.creatures, opp.life)
    combat_abilities(me, blocks, opp, e, step, attacking=True)
    combat_abilities(opp, blocks, me, e, step, attacking=False)
    n_events = len(e["events"])
    combat_tricks(me, blocks, opp, e, step, attacking=True)
    me.cast_count += len(e["events"]) - n_events
    combat_tricks(opp, blocks, me, e, step, attacking=False)
    before = [(a.label(), [b.label() for b in bs]) for a, bs in blocks]
    res = resolve_combat(blocks)
    opp.life -= res["player"]
    me.dealt_combat += res["player"]
    combat_life(me, opp, res)
    e["damage"] = res["player"]
    for a, _bs in blocks:  # "deals combat damage to a player, draw ..." (Frostbite Pyromental)
        if a.card.combat_draw and res["to_player"].get(id(a)):
            for _ in range(a.card.combat_draw):
                if me.library:
                    me.hand.append(me.library.pop(0))
            e["events"].append(f"{me.name}: {a.card.name} zieht {a.card.combat_draw}")
    e["attacks"] = [{"attacker": lab, "blockers": blabs, "attacker_dies": a.dead,
                     "blockers_die": [b.dead for b in bs]} for (lab, blabs), (a, bs) in zip(before, blocks)]
    bury((me, opp), e)
    if opp.life <= 0:
        return e
    # Main 2
    for c in main2:
        resolve(c)
    e["main2"] = [c.name for c in main2]
    _jace_activate(me, step, e, True)
    # End Phase: Edgar ("if you didn't cast a spell this turn"), danach Instants und Flash des Gegners
    if not me.cast_count:
        for c in me.creatures:
            if c.card.endstep_counters:
                c.bonus += c.card.endstep_counters
    confidant_end_step(me, e)
    for p_ in (me, opp):  # "At the beginning of the end step, sacrifice this creature"
        for c in p_.creatures:
            if c.card.end_sacrifice:
                c.dead = True
                e["events"].append(f"{p_.name}: opfert {c.card.name}")
    bury((me, opp), e)
    end_step_instants(opp, me, e, step)
    cleanup((me, opp))
    return e


def cleanup(players):
    """Rundenende: Schaden, Pumps und verliehene Schluesselwoerter verfallen."""
    for p in players:
        for c in p.creatures:
            c.damage, c.pump, c.tpump, c.touched, c.lifted = 0, 0, 0, False, False
            c.extra = set()
        p.surveilled = False
        p.gained = 0


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
                break
        else:
            continue
        break
    result["stats"] = {key: {"Wir": getattr(a, attr), "Gegner": getattr(b, attr)}
                       for key, attr in (("combat", "dealt_combat"), ("direct", "dealt_direct"), ("deaths", "deaths"))}
    return result


def _end_life(game, who):
    log = game.get("log") or []
    return log[-1]["life"][who] if log and log[-1].get("life") else 20


def _max_gap(game, behind):
    """Groesster Rueckstand von 'behind' waehrend des Spiels (Leben des anderen minus eigene Leben)."""
    other = "Gegner" if behind == "Wir" else "Wir"
    return max((e["life"][other] - e["life"][behind] for e in game.get("log") or [] if e.get("life")), default=0)


def special_games(results):
    """Besondere Spiele: knappster Sieg (wenigste eigene Leben am Ende), knappste Niederlage (Gegner mit den wenigsten
    Leben am Ende), gedrehter Sieg (groesster Rueckstand zwischendurch), gedrehte Niederlage (groesster Vorsprung)."""
    wins = [r for r in results if r["winner"] == "a"]
    losses = [r for r in results if r["winner"] == "b"]
    return {
        "closest_win": min(wins, key=lambda r: (_end_life(r, "Wir"), r["round"])) if wins else None,
        "closest_loss": min(losses, key=lambda r: (_end_life(r, "Gegner"), -r["round"])) if losses else None,
        "comeback_win": max(wins, key=lambda r: (_max_gap(r, "Wir"), -r["round"])) if wins else None,
        "comeback_loss": max(losses, key=lambda r: (_max_gap(r, "Gegner"), -r["round"])) if losses else None,
    }


def battle(cards_a, cards_b, games, on_draw, max_turns=20, mulligan=True, min_hand=5):
    """Spielt games Spiele; on_draw: der Gegner beginnt. Gibt Siege, Niederlagen, Unentschieden, Kennzahlen, besondere
    Spiele (mit Protokoll), eine Liste aller Spiele und alle Spiele mit Protokoll (results_all) zurueck."""
    from collections import Counter
    out = {"games": games, "wins": 0, "losses": 0, "draws": 0, "win_rounds": [], "loss_rounds": [],
           "fastest_win": None, "fastest_loss": None, "mull_wins": 0, "mull_losses": 0, "win_by_round": Counter(),
           "end_life_win": [], "end_life_loss": [], "games_list": [], "results_all": []}
    played = []
    for n in range(games):
        r = play_game(cards_a, cards_b, not on_draw, max_turns, mulligan, min_hand)
        out["results_all"].append(r)
        mull = r.get("note") == "Spiel durch Mulligan verloren"
        out["games_list"].append({"n": n, "winner": r["winner"], "round": r["round"], "mulligans": r["mulligans"],
                                  "mulligan_loss": mull,
                                  "life": {"Wir": _end_life(r, "Wir"), "Gegner": _end_life(r, "Gegner")}})
        if r["winner"] == "a":
            out["wins"] += 1
        elif r["winner"] == "b":
            out["losses"] += 1
        else:
            out["draws"] += 1
        if mull:  # zaehlt, aber nicht fuer Runden, Kennzahlen und besondere Spiele
            out["mull_wins" if r["winner"] == "a" else "mull_losses"] += 1 if r["winner"] else 0
            continue
        played.append(r)
        if r["winner"] == "a":
            out["win_rounds"].append(r["round"])
            out["win_by_round"][r["round"]] += 1
            out["end_life_win"].append(_end_life(r, "Wir"))
            if out["fastest_win"] is None or r["round"] < out["fastest_win"]["round"]:
                out["fastest_win"] = r
        elif r["winner"] == "b":
            out["loss_rounds"].append(r["round"])
            out["end_life_loss"].append(_end_life(r, "Gegner"))
            if out["fastest_loss"] is None or r["round"] < out["fastest_loss"]["round"]:
                out["fastest_loss"] = r
    out.update(special_games(played))
    # Lebenspunkte nach jeder Runde (nach Spielende gilt der letzte Stand)
    rounds = max((r["round"] for r in played), default=0)
    curve = {"Wir": [0.0] * rounds, "Gegner": [0.0] * rounds}
    for r in played:
        last = {"Wir": 20, "Gegner": 20}
        by_round = {}
        for e in r["log"]:
            if e.get("life"):
                by_round[e["round"]] = dict(e["life"])
        for i in range(rounds):
            last = by_round.get(i + 1, last)
            for who in curve:
                curve[who][i] += last[who]
    n_played = len(played) or 1
    out["life_curve"] = {who: [v / n_played for v in vals] for who, vals in curve.items()}
    for key in ("combat", "direct", "deaths"):
        name = {"combat": "combat_damage", "direct": "direct_damage", "deaths": "deaths"}[key]
        out[name] = {who: sum(r["stats"][key][who] for r in played) / n_played for who in ("Wir", "Gegner")}
    return out
