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
import random
from collections import Counter

from components.mana import land_key
from components.mulligan import deal_opening
from components.jace import (JaceState, cast_filter_matches, enter_filter_matches, once_effects,
                             recurring_effects, surveil)
from components.simulation import walker_rank
from components.cards import HEARTWOOD
from components.simulation import (ANY_COLOR, apply_effects, apply_surveils, best_cast_reduced, choose_land,
                                   cost_reduction, do_cycle, enter_value, enters_prepared, hand_form,
                                   landfall_effects, pay_subsets,
                                   plan_cycle, reduced, resolve_draws, tapped_for_mana, usable_now, use_treasures)
from components.landadvice import colors_of_alts

LIFE = 20
CYCLE_TURNS = 3  # eigener Zug: fehlt bis Runde 3 ein Land fuer den Landdrop, wird sofort gecycelt
CYCLE_CAP = 6    # Ende des gegnerischen Zugs: nur cyceln, solange Laender auf Feld und Hand unter 6 liegen


BASIC_TYPES = {"plains", "island", "swamp", "mountain", "forest"}
_GY_TYPES = {"creature": "is_creature", "planeswalker": "is_planeswalker", "artifact": "is_artifact",
             "land": "is_land", "instant": "is_instant", "sorcery": "is_instant_sorcery"}


class Creature:
    """Eine Kreatur auf dem Feld (Karte, Schritt des Eintritts, getappt, Schaden, Marken, Pump)."""
    __slots__ = ("card", "entered", "tapped", "damage", "bonus", "pump", "dead", "touched", "locked", "prepared",
                 "tpump", "extra", "lifted", "owner", "at_jace", "gy", "dealt", "finality", "ctl", "once", "stun", "gear",
                 "tdraw", "auras", "exile_step")

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
        self.at_jace = False  # greift in diesem Kampf den Jace-Token an statt den Spieler
        self.gy = None        # Friedhof des Kontrolleurs (Power nach Karten im Friedhof, Winter)
        self.dealt = False    # hat schon Kampfschaden zugefuegt (Ruric Thar verliert dann Hexproof)
        self.finality = False  # Finality-Marke: stirbt sie, wird sie exiliert
        self.ctl = None       # Kontrolleur (Player), fuer Power nach Domain (Fblthp)
        self.once = {}        # Ausloeser "only once each turn": Name -> Schritt, in dem er zuletzt ausgeloest hat
        self.stun = 0         # Stun-Marken (122.1g): statt zu enttappen wird eine entfernt
        self.gear = []        # angelegte Ausruestung (Karten aus p.perms)
        self.tdraw = 0        # bis Rundenende: zieht so viele Karten bei Kampfschaden am Spieler (Lyra, Tolarian)
        self.auras = []       # eigene Auras auf dieser Kreatur (Splinter Twin; Karten aus p.perms)
        self.exile_step = None  # Token-Kopie von Splinter Twin: wird im Endsegment dieses Schritts exiliert

    @property
    def power(self):
        base = self.card.power + self.bonus + self.pump
        if self.card.gy_power and self.gy is not None:
            base += sum(1 for g in self.gy if any(getattr(g, _GY_TYPES[t], False) for t in self.card.gy_power))
        if self.card.domain_power and self.ctl is not None:
            base += len({t for land in self.ctl.lands for t in land.land_types} & BASIC_TYPES)
        return base + self._threshold() + sum(g.equip[1] for g in self.gear)

    @property
    def toughness(self):
        return self.card.toughness + self.bonus + self.tpump + self._threshold() + sum(g.equip[2] for g in self.gear)

    @property
    def dmg(self):
        """Kampfschaden, den die Kreatur zuweist (510.1a): Power, mit Ghalta the Immovable beim Kontrolleur die
        Toughness, wenn sie groesser ist."""
        power, tough = self.power, self.toughness
        if tough > power and self.ctl is not None and any(c.card.toughness_damage and not c.dead
                                                          for c in self.ctl.creatures):
            return tough
        return power

    def _threshold(self):
        """Threshold: +N/+N ab 7 Karten im Friedhof des Kontrolleurs (Void Extrapolator)."""
        if self.card.threshold_bonus and self.ctl is not None and len(self.ctl.graveyard) >= 7:
            return self.card.threshold_bonus
        return 0

    def has(self, keyword):
        """Eigene und verliehene Schluesselwoerter, dazu bedingte: nur im eigenen Zug (Skilled Battlecarver), nach
        Schaden ausserhalb des Kampfs am Gegner (Whiplash Wordsmith) und von anderen eigenen Kreaturen verliehene
        (Ghalta: Trample, Saheeli: Haste fuer Thopter, Vigorbloom Vanguard: Vigilance mit +1/+1-Marke)."""
        if keyword in self.card.kw or keyword in self.extra:
            return True
        p = self.ctl
        if p is None:
            return False
        card = self.card
        if keyword in card.own_turn_kw and p.turn_start == p.now:
            return True
        if keyword in card.noncombat_kw and p.dealt_direct > p.direct_mark:
            return True
        if any(keyword in card.team_kw_all for card in p.perms):  # Ajani's Anguish
            return True
        for c in p.creatures:
            if c.dead:
                continue
            other = c.card
            if keyword in other.team_kw_all:  # Samut: "Creatures you control have haste" (auch sie selbst)
                return True
            if c is not self and keyword in other.team_kw:
                return True
            if keyword == "unblockable" and other.small_unblockable and (self.power <= 1 or self.toughness <= 1):
                return True  # Tetsuko Umezawa, Fugitive
            if keyword == "haste" and other.counter_haste and c is not self and self.bonus > 0:
                return True  # Gallia
            if keyword == "haste" and other.type_haste and other.type_haste in card.creature_types:
                return True
            if keyword == "vigilance" and other.counter_vigilance and self.bonus > 0:
                return True
        return False

    def copy(self):
        c = Creature(self.card, self.entered)
        for attr in ("tapped", "damage", "bonus", "pump", "dead", "touched", "locked", "prepared", "tpump",
                     "lifted", "at_jace"):
            setattr(c, attr, getattr(self, attr))
        c.extra = set(self.extra)
        c.owner = self.owner
        c.gy = self.gy
        c.ctl = self.ctl
        c.dealt = self.dealt
        c.once = dict(self.once)
        c.stun, c.gear, c.tdraw = self.stun, list(self.gear), self.tdraw
        c.auras, c.exile_step = list(self.auras), self.exile_step
        return c

    def label(self):
        return f"{self.card.name} ({self.power}/{self.toughness})"


def _defender_ok(c):
    """Defender gilt nicht: nach einem Surveil (Surveillance Phantasm) oder mit Ghalta the Immovable auf dem Feld."""
    return c.lifted or (c.ctl is not None and any(x.card.defender_attack and not x.dead for x in c.ctl.creatures))


def can_attack(c, step):
    return (not c.tapped and not c.dead and not c.locked and (not c.card.defender or _defender_ok(c)) and c.dmg > 0
            and (c.entered < step or c.card.haste or c.has("haste")))


def can_block(blocker, attacker):
    if blocker.tapped or blocker.dead or blocker.locked or attacker.has("unblockable"):
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
    Gibt {"player": Schaden am Verteidiger, "jace": Schaden am Jace-Token (Angreifer mit at_jace), "lifelink_attacker",
    "lifelink_defender", ...} zurueck."""
    out = {"player": 0, "jace": 0, "lifelink_attacker": 0, "lifelink_defender": 0, "to_player": {},
           "lifelink_events_attacker": 0, "lifelink_events_defender": 0}
    for first_step in (True, False):
        hits = []  # (Ziel-Kreatur, Schaden, Deathtouch)
        for att, blockers in pairs:
            if not att.dead and _deals_in(att, first_step) and att.dmg > 0:
                if not blockers or any(not b.dead for b in blockers) or att.has("trample"):
                    att.dealt = True
                power, dt = att.dmg, att.has("deathtouch")
                if not blockers:
                    _hit_player(out, att, power)
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
                                _hit_player(out, att, rest)
                        else:
                            hits.append((alive[-1], rest, dt))
                if att.has("lifelink"):
                    out["lifelink_attacker"] += power
                    out["lifelink_events_attacker"] += 1
            for b in blockers:
                if not b.dead and not att.dead and _deals_in(b, first_step) and b.dmg > 0:
                    b.dealt = True
                    hits.append((att, b.dmg, b.has("deathtouch")))
                    if b.has("lifelink"):
                        out["lifelink_defender"] += b.dmg
                        out["lifelink_events_defender"] += 1
        for target, amount, dt in hits:
            target.damage += amount
            target.touched = target.touched or dt
        for att, blockers in pairs:
            for c in [att] + list(blockers):
                if not c.dead and (c.damage >= c.toughness or (c.touched and c.damage > 0)):
                    c.dead = True
    return out


def _hit_player(out, att, amount):
    if att.at_jace:
        out["jace"] += amount
    else:
        out["player"] += amount
        out["to_player"][id(att)] = out["to_player"].get(id(att), 0) + amount


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

def choose_jace_attackers(attackers, defender, blockers):
    """Angreifer auf den Jace-Token des Verteidigers: nicht bei Lethal auf den Spieler; sonst die schwaechsten
    Angreifer, gerade so viele, dass Jace (auch nach bestmoeglichem Block) unter 3 Loyalty faellt bzw. stirbt.
    Reicht das nicht, greifen alle den Spieler an."""
    loyalty = defender.jace.loyalty
    if loyalty <= 0 or not attackers or max_through(attackers, blockers) >= defender.life:
        return []
    need = loyalty if loyalty < 3 else loyalty - 2
    picked = []
    for a in sorted(attackers, key=lambda a: (a.dmg, a.toughness, a.card.mv)):
        picked.append(a)
        if max_through(picked, blockers) >= need:
            return picked
    return []


def max_through(attackers, blockers):
    """Schaden, der bei bestmoeglichem Blocken mindestens durchkommt (gierige Naeherung, ohne Kampftricks)."""
    free = [b for b in blockers if not b.tapped and not b.dead]
    total = 0
    for a in sorted(attackers, key=lambda a: -a.dmg * (2 if a.has("double strike") else 1)):
        dmg = a.dmg * (2 if a.has("double strike") else 1)
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
    their_attackers = [t for t in theirs if not t.dead and (not t.card.defender or _defender_ok(t)) and t.dmg > 0]

    def crack_back(attack_set):
        home = [c for c in mine if not c.dead and not c.tapped and (c not in attack_set or c.has("vigilance"))]
        return max_through(their_attackers, home)

    if crack_back([]) < my_life:  # nur zurueckhalten, wenn es den Gegenangriff wirklich aufhaelt
        while attack and crack_back(attack) >= my_life:
            attack.remove(min(attack, key=lambda c: (c.dmg, c.toughness)))
    return attack


def choose_blocks(attackers, defenders, life):
    """Blocker je Angreifer: [(Angreifer, [Blocker])] in der Reihenfolge der Angreifer."""
    free = [d for d in defenders if not d.tapped and not d.dead]
    plan = {id(a): [] for a in attackers}
    order = sorted(attackers, key=lambda a: (-a.dmg, -a.toughness))
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
        self.next_x = 0       # X der naechsten Kreatur, die gewirkt ins Spiel kommt (Fblthp)
        self.now = 0          # aktueller Schritt (fuer Token aus Faehigkeiten)
        self.turn_start = 0   # Schritt, in dem unser letzter Zug begann (Token mit {T} erst danach nutzbar)
        self.direct_mark = 0  # dealt_direct zu Beginn des aktuellen Zugs ("noncombat damage this turn")
        self.deaths_mark = 0  # deaths zu Beginn des aktuellen Zugs ("creatures died this turn")
        self.noncreature_cast = False  # in diesem Zug schon einen Nichtkreatur-Zauber gewirkt (Traxos)
        self.ward_budget = 0  # in der Main Phase fuer Ward eingeplantes Mana (mit dem Zauber bezahlt)
        self.ward_pool = None  # beim Planen der Main Phase: Mana des Zugs fuer die Ward-Pruefung
        self.impulse = []     # Karten im Exil, die wir spielen duerfen: (Karte, letzter eigener Zug)
        self.own_turns = 0    # Zahl der eigenen Zuege bisher
        self.drawn = 0        # gezogene Karten insgesamt (Lyra, Tolarian Archangel)
        self.drawn_mark = 0   # drawn zu Beginn des aktuellen Zugs
        self.extra_lands = 0  # zusaetzliche Landdrops in diesem Zug (Way of the Paradox)
        self.predrawn = Counter()  # Main Phase: Karten, deren "draw N" die Planung (resolve_draws) schon gezogen hat

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
                      if c.card.mana_src and not c.tapped and (c.entered < step or c.card.haste or c.has("haste"))
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


def own_reduction(p, card):
    """Eigene Kostensenkung der Karte nach dem Feld von p (Ghalta, Wrath of the Bloodmane, Traxos), siehe
    simulation.cost_reduction."""
    if p is None or not card.self_discount:
        return 0
    alive = [c for c in p.creatures if not c.dead]
    return cost_reduction(card, [c.power for c in alive], [c.toughness for c in alive],
                          any(c.card.legendary for c in alive), p.noncreature_cast)


def _discounted(card, d, p=None):
    """Kosten mit Kostensenkung bzw. Steuer d (nur Nichtkreatur-Zauber), eigener Kostensenkung (mit p) und
    Zusatzkosten (Silence the Echo)."""
    if card.is_land or not card.alts:
        return card
    own = own_reduction(p, card)
    if own:
        card = reduced(card, own)
    extra = 0 if card.behold_jace and has_jace(p) else card.extra_cost  # Countersculpt: "behold a Jace or pay {1}"
    change = (0 if card.is_creature else d) - extra
    if not change:
        return card
    if change > 0:
        return reduced(card, change)
    return card._replace(alts=tuple(sorted({(max(0, g - change), cols) for g, cols in card.alts})))


def has_jace(p):
    """Behold a Jace: ein Jace unter unserer Kontrolle (auch der Jace-Token) oder eine Jace-Karte auf der Hand."""
    if p is None:
        return False
    return jace_present(p) or any(c.is_jace for c in p.hand) or any(c.is_jace for c in p.perms)


def _alts(p, card):
    return _discounted(card, discount(p), p).alts


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
    return (c.dmg, any(c.has(k) for k in ("flying", "trample", "deathtouch")), c.card.mv)


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


def hexproof(c):
    """702.11b: kann nicht Ziel von Zaubern und Faehigkeiten der Gegner sein (Ruric Thar: bis zum ersten
    Kampfschaden). Effekte ohne Ziel (Schaden an allen, Edikt) treffen die Kreatur trotzdem."""
    return c.has("hexproof") or (c.card.hexproof_until_damage and not c.dealt)


def ward_ok(caster, c):
    """Kann caster die Ward-Kosten von c zahlen (702.21)? Mana aus dem offenen Mana (plus eingeplantem Ward-Mana)
    bzw. beim Planen aus dem Mana des Zugs; "Discard a card" mit einer Handkarte."""
    w = c.card.ward
    if not w:
        return True
    if w[0] == "discard":
        return bool(caster.hand)
    have = len(caster.ward_pool) if caster.ward_pool is not None else len(caster.open) + caster.ward_budget
    return w[1] <= have


def pay_ward(caster, c, e):
    """Zahlt die Ward-Kosten von c (vorher mit ward_ok geprueft)."""
    w = c.card.ward
    if not w:
        return True
    if w[0] == "discard":
        gone = choose_discard(caster)
        if gone is None:
            return False
        caster.hand.remove(gone)
        caster.graveyard.append(gone)
        e["events"].append(f"{caster.name}: wirft {gone.name} ab (Ward von {c.card.name})")
        discarded(caster, e)
        return True
    n = w[1]
    use = min(n, caster.ward_budget)
    if n - use and not _pay_open(caster, ((n - use, ()),), treasure=False):
        return False
    caster.ward_budget -= use
    e["events"].append(f"{caster.name}: zahlt Ward {{{n}}} für {c.card.name}")
    return True


def ward_plan(me, opp, card, pool):
    """Main Phase: Ward-Mana, das zum Zauber dazukommt. Ziel ist die gefaehrlichste Kreatur, deren Ward wir mit dem
    Mana des Zugs zusaetzlich zahlen koennen, sonst die naechstbeste; gibt es keine, ist der Zauber in diesem Zug zu
    teuer (99). "Any target" geht dann an den Gegner (0)."""
    spec = card.removal
    if not spec or spec[0] in ("sweep", "sweep_damage", "edict") or spec[4] not in ("spell", "aura"):
        return 0
    cands = sorted(valid_targets(spec, me, opp, ward=False), key=danger, reverse=True)
    if not cands:
        return 0
    rest = pay(pool, card.alts)
    if rest is None:
        return 0
    for t in cands:
        w = t.card.ward
        if not w:
            return 0
        if w[0] == "discard":
            if len(me.hand) > 1:
                return 0
            continue
        if w[1] <= len(rest):
            return w[1]
    return 0 if spec[3] else 99


def valid_targets(spec, caster, victim, ward=True):
    kind = spec[0]
    out = [c for c in victim.creatures if not c.dead and (kind != "lock" or not c.locked) and _matches(spec[2], c)
           and not hexproof(c) and (not ward or ward_ok(caster, c))]
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


def jace_died(p, e):
    """Der Jace-Token faellt auf 0 Loyalty und kommt in den Friedhof (704.5i), er stirbt also (700.4): Ausloeser
    "another creature or planeswalker you control dies" (Edgar, Ancient Bloodlord; Massacre Girl)."""
    e["events"].append(f"{p.name}: Jace stirbt")
    for c in p.creatures:
        if c.dead:
            continue
        gain_life(p, c.card.ally_death_life)
        if c.card.ally_death_ping:
            dmg, life = c.card.ally_death_ping
            deal_noncombat(p, p.opponent, dmg, e)
            gain_life(p, life)


def jace_present(p):
    """Liegt ein Jace-Token? Mit Sanctum Lurker auch mit 0 Loyalty."""
    return p.jace.loyalty > 0 or p.jace.zero_alive


def grant_sources(p):
    """Karten, die Planeswalkern Faehigkeiten geben oder bei Aktivierungen ausloesen (Permanents und Kreaturen)."""
    return list(p.perms) + [c.card for c in p.creatures if not c.dead]


def walker_engine(p):
    """Gibt es Karten fuer den erweiterten Jace (L2a)? Sonst bleibt alles wie bisher."""
    return p.jace.zero_alive or any(c.walker_grants or c.walker_no_death or c.loyalty_draw or c.loyalty_paradox
                                    or c.kiora_attack for c in grant_sources(p))


def _jace_zero(p, before, e):
    """Jace ist auf 0 gefallen: mit Sanctum Lurker bleibt er liegen, sonst stirbt er (704.5i)."""
    if p.jace.loyalty > 0:
        return
    p.jace.loyalty = 0  # nie negativ
    if any(c.walker_no_death for c in grant_sources(p)):
        p.jace.zero_alive = True
        return
    if before > 0 or p.jace.zero_alive:
        p.jace.zero_alive = False
        jace_died(p, e)


def walker_abilities(p):
    """Loyalty-Faehigkeiten des Jace-Tokens: eigene (-1 Surveil, -3 Ziehen) und verliehene."""
    out = [(-1, (("surveil", 1),), "Jace"), (-3, (("draw", 1),), "Jace")]
    for card in grant_sources(p):
        out += [(cost, atoms, card.name) for cost, atoms in card.walker_grants]
    return out


def walker_options(p, opp, step, phase, pool=None, spells=None):
    """Bewertete Faehigkeiten, beste zuerst: (Rang, Gleichstand, Kosten, Effekte, Quelle, Ziel). Rang wie
    simulation.walker_rank; Warlord als Removal nur gegen die gefaehrlichste Kreatur, die 2 Schaden toeten; Mana nur in
    Main 1, wenn es einen weiteren Zauber ermoeglicht (606.6: Minus-Kosten nur mit genug Loyalty)."""
    if not jace_present(p) or p.jace.used:
        return []
    sources = grant_sources(p)
    sculptor = any(c.loyalty_draw for c in sources)
    alive_opp = [c for c in opp.creatures if not c.dead] if opp is not None else []
    best_threat = max(alive_opp, key=danger) if alive_opp else None
    opts = []
    for cost, atoms, src in walker_abilities(p):
        if cost < 0 and p.jace.loyalty < -cost:
            continue
        kinds = {a[0] for a in atoms}
        target = None
        rank, tie = walker_rank(atoms, opp.life if opp is not None else 99, len(p.lands),
                                any(not c.dead for c in p.creatures), tokens=True)
        if "bolt" in kinds and opp is not None:
            cdmg, fdmg = next(a[1:] for a in atoms if a[0] == "bolt")
            kill = [c for c in alive_opp if not hexproof(c) and ward_ok(p, c) and c.toughness - c.damage <= cdmg]
            if rank < 7 and phase in ("start", "main1"):  # vor dem Kampf (Feld wie in Main 1)
                for t in kill:  # tötet den Blocker, der Lethal verhindert
                    t.dead = True
                    v = _attack_value(p, opp, step)
                    t.dead = False
                    if v + fdmg >= opp.life:
                        rank, target = 7, t
                        break
            if rank < 7 and best_threat is not None and best_threat in kill:
                rank, target = 6, best_threat
            if rank == 7 and target is None and kill:
                target = max(kill, key=danger)
        if "sac_token" in kinds:
            small = [c for c in p.creatures if not c.dead and c.power + c.toughness < 8]
            if not small:
                continue
            target = min(small, key=lambda c: (not c.card.is_token, c.power + c.toughness, c.card.mv))
            rank, tie = 5, 8
        if "mana" in kinds:
            if phase != "main1" or pool is None or spells is None:
                continue
            extra = [a[1] for a in atoms if a[0] == "mana"]
            if not best_cast_reduced(spells, land_key(pool + extra), True, True)[0] > \
                    best_cast_reduced(spells, land_key(pool), True, True)[0]:
                continue
            rank, tie = 2, 0
        if kinds == {"surveil"} and not p.library:
            continue
        if rank <= 0:
            continue
        opts.append((rank, (1 if sculptor and cost <= -2 else 0, tie), cost, atoms, src, target))
    return sorted(opts, key=lambda o: (o[0], o[1]), reverse=True)


def activate_walker(p, opp, step, e, opt):
    """Fuehrt eine Loyalty-Faehigkeit des Jace-Tokens aus. Gibt Mana zurueck (Way of the Pyromancer)."""
    _rank, _tie, cost, atoms, src, target = opt
    before = p.jace.loyalty
    if cost < 0:
        p.jace.loyalty = max(0, p.jace.loyalty + cost)
    elif cost > 0:
        _jace_add(p, cost, e)
    p.jace.used = True
    e["events"].append(f"{p.name}: Jace {'+' if cost > 0 else ''}{cost} ({src}) (Loyalty {p.jace.loyalty})")
    mana = []
    for a in atoms:
        kind = a[0]
        if kind == "surveil":
            binned = surveil(p.library, a[1], p.hand, p.lands)
            p.graveyard.extend(binned)
            p.jace.surveils += 1
            p.jace.surveil_lands += len(binned)
            mark_surveil(p, e)
        elif kind == "draw":
            _draw(p, a[1])
            p.jace.acts += 1
            if p.jace.first is None:
                p.jace.first = step
        elif kind == "token":
            make_tokens(p, [(a[1], a[2])], step, e, opp, "Jace")
        elif kind == "sac_token":
            if target is not None and target in p.creatures:
                target.dead = True
                e["events"].append(f"{p.name}: opfert {target.card.name}")
                bury((p,), e)
            make_tokens(p, [(1, a[1])], step, e, opp, "Jace")
        elif kind == "bolt":
            if target is not None and target in (opp.creatures if opp is not None else []):
                pay_ward(p, target, e)
                target.damage += a[1]
            deal_noncombat(p, opp, a[2], e)
            bury((p, opp), e)
        elif kind == "face":
            deal_noncombat(p, opp, a[1], e)
        elif kind == "life":
            gain_life(p, a[1])
        elif kind == "counter_lands":
            alive = [c for c in p.creatures if not c.dead]
            if alive:
                pick = max(alive, key=lambda c: (can_attack(c, step), danger(c)))
                pick.bonus += len(p.lands)
        elif kind == "mana":
            mana.append(a[1])
    if p.opponent is not None:  # Gideon the Oathless
        for g in p.opponent.creatures:
            if g.card.opp_loyalty_ping and not g.dead:
                deal_noncombat(p.opponent, p, g.card.opp_loyalty_ping, e)
    for card in grant_sources(p):
        if card.loyalty_draw and cost <= -2:  # Way of the Mind Sculptor
            _draw(p, card.loyalty_draw)
        if card.loyalty_paradox:  # Way of the Paradox
            gain_life(p, 1)
            p.extra_lands += 1
    _jace_zero(p, before, e)
    return mana


def walker_phase(p, opp, step, e, phase, pool=None, spells=None):
    """Entscheidung zu einem Zeitpunkt: "start" (vor dem Landdrop: nur Ziehen, mit Way of the Paradox alles ausser
    Mana), "main1" (zeitkritisch: Lethal, Removal, Mana, Marken nach Laendern; mit Kiora jede Faehigkeit), "after"
    (nach Main 2: die beste). Gibt Mana zurueck."""
    opts = walker_options(p, opp, step, phase, pool, spells)
    if not opts:
        return []
    best = opts[0]
    kinds = {a[0] for a in best[3]}
    sources = grant_sources(p)
    if phase == "start":
        go = kinds == {"draw"} or (any(c.loyalty_paradox for c in sources) and "mana" not in kinds)
    elif phase == "main1":
        go = best[0] >= 6 or bool(kinds & {"mana", "counter_lands"}) or any(c.kiora_attack for c in sources)
    else:
        go = True
    return activate_walker(p, opp, step, e, best) if go else []


def _jace_activate(p, step, e, allow_surveil):
    loyalty, lands = p.jace.loyalty, p.jace.surveil_lands
    if p.jace.try_activate(p.hand, p.library, step, battlefield=p.lands, allow_surveil=allow_surveil):
        if p.opponent is not None:  # Gideon the Oathless: Schaden fuer jede Loyalty-Aktivierung
            for g in p.opponent.creatures:
                if g.card.opp_loyalty_ping and not g.dead:
                    deal_noncombat(p.opponent, p, g.card.opp_loyalty_ping, e)
        if loyalty > 0 and p.jace.loyalty <= 0:
            _jace_zero(p, loyalty, e)
        if p.jace.loyalty == loyalty - 3:
            p.drawn += 1
            e["events"].append(f"{p.name}: Jace −3, zieht eine Karte (Loyalty {p.jace.loyalty})")
        else:
            mark_surveil(p, e)
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
    e = e if e is not None else {"events": []}
    if walker_engine(p):
        walker_phase(p, p.opponent, step, e, "start")
    else:
        _jace_activate(p, step, e, False)


def deal_noncombat(src, victim, amount, e):
    """Schaden ausserhalb des Kampfs von src an den Spieler victim (direkter Schaden). Jedes Ereignis gibt Kreaturen
    wie Massacre Girl ("whenever an opponent is dealt noncombat damage") ihre Marken."""
    if amount <= 0 or victim is None:
        return
    victim.life -= amount
    src.dealt_direct += amount
    e["face"] = e.get("face", 0) + amount
    for c in src.creatures:
        if c.card.noncombat_counter and not c.dead:
            c.bonus += c.card.noncombat_counter
    team = sum(c.card.noncombat_team_pump for c in src.creatures if not c.dead)
    if team:  # Master of Barbs
        for c in src.creatures:
            if not c.dead:
                c.pump += team


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
                if typ == "self":  # Unflinching Hortimancer
                    if not c.dead:
                        c.bonus += k
                    continue
                for x in p.creatures:
                    if not x.dead and typ in x.card.creature_types:
                        x.bonus += k
            if c.card.lifegain_draw and c.once.get("lifegain") != p.now:  # Bloombrute: einmal pro Zug
                c.once["lifegain"] = p.now
                _draw(p, c.card.lifegain_draw)
        loyalty = sum(c.lifegain_loyalty for c in p.perms) + sum(c.card.lifegain_loyalty for c in p.creatures)
        if loyalty and jace_present(p):  # Way of the Mentor: nur auf einen vorhandenen Jace
            _jace_add(p, loyalty)


def combat_life(att, dfn, res):
    """Lifelink nach dem Kampfschaden (vor dem Aufraeumen der gestorbenen Kreaturen)."""
    gain_life(att, res["lifelink_attacker"], res["lifelink_events_attacker"])
    gain_life(dfn, res["lifelink_defender"], res["lifelink_events_defender"])


def mark_surveil(p, e=None, events=1):
    """Wir haben gesurveilt (events: Zahl der einzelnen Surveils). Ausloeser "whenever you scry or surveil": Prudent
    Fateseer (alle +N/+0, einmal pro Zug), Saheeli, Consul of Oversight (Token, einmal pro Zug), Proft ({2} mit freiem
    Mana: Marke und eine Karte, bei jedem Surveil)."""
    p.surveilled = True
    for c in p.creatures:
        if c.card.surveil_attack:
            c.lifted = True
    if e is None:
        e = {"events": []}
    for c in list(p.creatures):
        card = c.card
        if c.dead:
            continue
        if card.surveil_counter_all:  # Denzilore Fatehold: bei jedem Surveil
            for x in p.creatures:
                if not x.dead:
                    x.bonus += card.surveil_counter_all * events
        if card.surveil_self_pump:  # Diviner of Victory
            c.pump += card.surveil_self_pump[0] * events
            c.tpump += card.surveil_self_pump[1] * events
        if card.surveil_team_pump and c.once.get("surveil_pump") != p.now:
            c.once["surveil_pump"] = p.now
            for x in p.creatures:
                if not x.dead:
                    x.pump += card.surveil_team_pump
            e["events"].append(f"{p.name}: {card.name} – alle +{card.surveil_team_pump}/+0")
        if card.surveil_tokens and c.once.get("surveil_token") != p.now:
            c.once["surveil_token"] = p.now
            make_tokens(p, card.surveil_tokens, p.now, e, p.opponent, card.name)
        if card.surveil_pay:
            for _ in range(events):
                if not _pay_ability(p, ((card.surveil_pay, ()),), "free"):
                    break
                c.bonus += 1
                _draw(p)
                e["events"].append(f"{p.name}: {card.name} zahlt {{{card.surveil_pay}}}: Marke und eine Karte")


def on_cast(p, card, step, e):
    """Ein Zauber wurde gewirkt: Jace-Ausloeser, Marken fuer Zauber mit Ziel beim Gegner (Danitha)."""
    _jace_on_cast(p, card, step, e)
    if not card.is_creature:
        p.noncreature_cast = True
        for c in p.creatures:
            if c.card.prowess and not c.dead:  # mehrfaches Prowess loest mehrfach aus (702.108b)
                c.pump += int(c.card.prowess)
                c.tpump += int(c.card.prowess)
            if c.card.cast_counter and not c.dead:  # Chandra's Emberling
                c.bonus += c.card.cast_counter
        team = sum(c.card.cast_team_pump for c in p.creatures if not c.dead)
        if team:  # Winter, Team Player
            for c in p.creatures:
                if not c.dead:
                    c.pump += team
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


def basic_names_in_library(p):
    return {c.name for c in p.library if c.is_basic}


def search_basics(p, x, e, source=""):
    """Bis zu x Basic Lands mit verschiedenen Namen aus der Bibliothek auf die Hand, danach mischen. Zuerst Laender mit
    neuen Farben (nicht auf dem Feld oder der Hand), dann die haeufigsten in der Bibliothek."""
    have = set().union(*(c.land_colors for c in p.lands + [h for h in p.hand if h.is_land])) if p.lands or p.hand \
        else set()
    count = Counter(c.name for c in p.library if c.is_basic)
    first = {c.name: c for c in p.library if c.is_basic}
    names = sorted(count, key=lambda n: (-len(set(first[n].land_colors) - have), -count[n], n))[:x]
    for name in names:
        card = first[name]
        p.library.remove(card)
        p.hand.append(card)
    random.shuffle(p.library)
    if names:
        e["events"].append(f"{p.name}: {source} sucht {', '.join(names)}")


def free_units(p):
    """Wie viel offenes Mana frei ist: danach bleibt jede vorher bezahlbare Instant-/Flash-/Cycling-Karte bezahlbar."""
    n = 0
    while n < len(p.open):
        rest = list(p.open)
        for _ in range(n + 1):
            rest.pop()
        if any(pay(rest, need) is None for need in _reserved(p)):
            break
        n += 1
    return n


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
    new.gy, new.ctl = p.graveyard, p
    new.bonus += card.enters_counters  # "enters with N +1/+1 counters" (614.1c)
    x, p.next_x = p.next_x, 0  # X des gewirkten Zaubers (107.3m); sonst 0
    if card.x_search_basics and x:
        search_basics(p, x, e, card.name)
    gain_life(p, card.etb_life)
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
    _jace_etb(p, card, step, e)
    card_effects(p, opp, card, step, e)
    new.lifted = p.surveilled and new.card.surveil_attack
    alive = [c for c in p.creatures if not c.dead]
    for c in alive:
        if c is new:
            continue
        if c.card.ally_untap and not card.is_token:  # Arni, Humble Scribe
            c.tapped = False
        if c.card.ally_enter_pump:  # Arni, Renowned Champion
            c.pump += max(0, new.power)
    for c in alive:  # Proctor of Potential: sie oder eine andere eigene Kreatur kommt ins Spiel
        if c.card.enter_surveil:
            surveil_cards(p, [c.card.enter_surveil], e, c.card.name)
    other = opp if opp is not None else p.opponent
    if other is not None:  # Gideon the Oathless: Schaden, wenn bei uns eine Kreatur ins Spiel kommt
        for g in other.creatures:
            if g.card.opp_enter_ping and not g.dead:
                deal_noncombat(other, p, g.card.opp_enter_ping, e)
    for c in alive:
        if c is not new and c.card.ally_enter_life:
            gain_life(p, c.card.ally_enter_life)
    for c in alive:
        if c.card.enter_counter:
            fresh = [x for x in alive if x.entered == step]
            if fresh:
                pick = max(fresh, key=lambda x: (can_attack(x, step), danger(x)))  # Angreifer zuerst
                pick.bonus += c.card.enter_counter
                e["events"].append(f"{p.name}: {c.card.name} – Marke auf {pick.card.name}")
    if new.card.artifact_pump:
        x = sum(c.card.is_artifact for c in alive) + sum(c.is_artifact for c in p.perms)
        for c in alive:
            c.pump += x
            c.extra |= set(new.card.artifact_pump)
        e["events"].append(f"{p.name}: {new.card.name} – alle +{x}/+0 und {', '.join(new.card.artifact_pump)}")


def _mode_label(sub):
    if sub.removal:
        return "Removal"
    if sub.draws:
        return "Karte ziehen"
    if sub.creates_tokens:
        return "Token"
    if sub.grant_kw or sub.modes:
        return "Marken/Pumps"
    return "Sonstiges"


def _jace_on_cast(p, card, step, e):
    if not p.jace_perms and not once_effects(card) and not recurring_effects(card):
        return
    for pc, _t in list(p.jace_perms):
        for ef in recurring_effects(pc):
            if ef[1] == "trigger" and ef[3].startswith("cast:") and cast_filter_matches(ef[3][5:], card):
                _jace_add(p, ef[2], e)
    for ef in once_effects(card) if not card.choices else ():  # modale Karten: Empower nur im gewaehlten Modus
        if ef[1] == "spell":
            _jace_add(p, ef[2], e)


def _jace_etb(p, card, step, e):
    """Betreten: Empower beim Betreten, Ausloeser "whenever ... enters" anderer Permanents, eigene Ausloeser merken."""
    for ef in once_effects(card):
        if ef[1] == "etb":
            _jace_add(p, ef[2], e)
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
    return jace_present(p) or bool(walkers), jace_present(p) or any(c.is_jace for c in walkers)


def surveil_cards(p, amounts, e, source):
    amounts = [a for a in amounts if a]
    if not amounts:
        return
    before = len(p.graveyard)
    events, _lands = apply_surveils(amounts, p.library, p.hand, p.lands, graveyard=p.graveyard)
    binned = len(p.graveyard) - before
    e["events"].append(f"{p.name}: {source} – Surveil {sum(amounts)}" + (f" ({binned} abgelegt)" if binned else ""))
    mark_surveil(p, e, max(1, events))


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
        deal_noncombat(me, opp, face, e)
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


def legend_rule(p, e):
    """704.5j: je Spieler nur ein legendaeres Permanent gleichen Namens. Behalten wird die staerkere Kreatur (bei
    Gleichstand die aeltere) bzw. das erste Permanent; die anderen kommen in den Friedhof."""
    groups = {}
    for c in p.creatures:
        if c.card.legendary and not c.dead:
            groups.setdefault(c.card.name, []).append(c)
    for same in groups.values():
        if len(same) > 1:
            keep = max(same, key=lambda c: (c.power + c.toughness - c.damage, -c.entered))
            for c in same:
                if c is not keep:
                    c.dead = True
                    e["events"].append(f"{p.name}: Legend-Regel – {c.card.name} in den Friedhof")
    seen = set()
    for card in list(p.perms):
        if card.legendary:
            if card.name in seen:
                p.perms.remove(card)
                if not card.is_token:
                    p.graveyard.append(card)
                e["events"].append(f"{p.name}: Legend-Regel – {card.name} in den Friedhof")
            seen.add(card.name)


def legend_ok(p, card):
    """Ein weiteres legendaeres Permanent gleichen Namens wuerde sofort wieder sterben: dann nicht wirken."""
    if not card.legendary or card.is_instant_sorcery:
        return True
    return not (any(c.card.name == card.name and not c.dead for c in p.creatures)
                or any(c.name == card.name for c in p.perms))


def bury(players, e):
    """Gestorbene Kreaturen in den Friedhof (Schaden, Deathtouch, Toughness 0) und Legend-Regel. Danach Ausloeser fuer
    gestorbene eigene Kreaturen (Massacre Girl; sie sieht auch Tode im selben Moment wie ihren eigenen, 603.10a)."""
    for p in players:
        legend_rule(p, e)
    triggers = []  # erst alle gleichzeitig sterben lassen (704.3), dann die Ausloeser
    for p in players:
        watchers = [c for c in p.creatures if c.card.ally_death_ping or c.card.ally_death_life]
        dying = [c for c in p.creatures
                 if c.dead or c.toughness <= 0 or c.damage >= c.toughness or (c.touched and c.damage > 0)]
        triggers += [(p, w.card.ally_death_ping or (0, 0), w.card.ally_death_life) for w in watchers for d in dying
                     if d is not w]
        loyalty = sum(c.death_loyalty for c in p.perms) + sum(c.card.death_loyalty for c in p.creatures)
        if loyalty:  # Way of the Necromancer: je gestorbene eigene Kreatur Loyalty auf einen vorhandenen Jace
            triggers += [(p, "loyalty", loyalty)] * len(dying)
    moves = []  # Graft Surgeon: Marken auf eine eigene Kreatur, die ueberlebt
    for p in players:
        for c in list(p.creatures):
            if c.dead or c.toughness <= 0 or c.damage >= c.toughness or (c.touched and c.damage > 0):
                if c.card.death_counters_move and c.bonus > 0:
                    moves.append((p, c.bonus, c.card.name))
                p.deaths += 1
                p.creatures.remove(c)
                if not c.card.is_token and not c.finality:
                    (c.owner or p).graveyard.append(c.card)
                if c.card.death_heartwood:  # Aerid Konstrari
                    p.perms += [HEARTWOOD] * c.card.death_heartwood
                _leave(p, c.card)
                gain_life(p, c.card.death_life)
                e["deaths"].append(f"{c.card.name} ({p.name})")
    for p, ping, extra in triggers:  # Massacre Girl, Edgar, Way of the Necromancer
        if ping == "loyalty":
            if jace_present(p):
                _jace_add(p, extra, e)
            continue
        dmg, life = ping
        deal_noncombat(p, p.opponent, dmg, e)
        gain_life(p, life + extra)
    for p in players:
        check_auras(p, e)
        if p.jace.zero_alive and p.jace.loyalty <= 0 and not any(c.walker_no_death for c in grant_sources(p)):
            p.jace.zero_alive = False
            jace_died(p, e)
    for p, n, name in moves:
        alive = [c for c in p.creatures if not c.dead]
        if alive:
            pick = max(alive, key=lambda x: (can_attack(x, p.now + 1), danger(x)))
            pick.bonus += n
            e["events"].append(f"{p.name}: {name} – {n} Marke(n) auf {pick.card.name}")


def check_auras(p, e=None):
    """704.5m: eine eigene Aura (Splinter Twin), deren Kreatur nicht mehr da ist, kommt in den Friedhof."""
    attached = Counter(a for c in p.creatures for a in c.auras)
    for card in list(p.perms):
        if not card.twin:
            continue
        if attached[card] > 0:
            attached[card] -= 1
            continue
        p.perms.remove(card)
        p.graveyard.append(card)
        if e is not None:
            e["events"].append(f"{p.name}: {card.name} in den Friedhof (keine Kreatur mehr)")


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


def _sacrificer(p):
    """Eigene Kreatur mit "{N}, Sacrifice another creature: Marke auf sich" (Edgar, Ancient Bloodlord)."""
    return next((c for c in p.creatures if c.card.sac_counter and not c.dead), None)


def sacrifice_for(p, victim, e, mode="rest"):
    """Opfert victim fuer die Faehigkeit von Edgar (bezahlt mit mode, siehe _pay_ability). victim stirbt (bury
    danach), Edgar bekommt seine Marke und die Schluesselwoerter bis Rundenende."""
    ed = _sacrificer(p)
    if ed is None or victim is ed or victim.dead:
        return False
    alts, n, kws = ed.card.sac_counter
    if not _pay_ability(p, alts, mode):
        return False
    victim.dead = True
    ed.bonus += n
    ed.extra |= set(kws)
    e["events"].append(f"{p.name}: {ed.card.name} opfert {victim.card.name} (+{n}/+{n}"
                       + (", " + ", ".join(kws) if kws else "") + ")")
    return True


def sacrifice_blockers(dfn, pairs, e):
    """Nach den Blocks: ein eigener Blocker, der stirbt, ohne den Angreifer zu toeten, wird fuer Edgar geopfert. Der
    Angreifer bleibt geblockt (509.1h) und macht keinen Schaden; nicht gegen Trample (702.19e: alles ginge an uns)."""
    if _sacrificer(dfn) is None:
        return
    done = False
    for att, bs in pairs:
        if att.has("trample") or not bs:
            continue
        att_dies, die = outcome(att, bs)
        if att_dies:
            continue
        for b, dies in zip(bs, die):
            if dies and sacrifice_for(dfn, b, e):
                done = True
    if done:
        bury((dfn,), e)


def sacrifice_for_lethal(me, opp, step, e):
    """Vor dem eigenen Angriff: opfert die schwaechsten anderen Kreaturen (Token zuerst) fuer Edgar, wenn Marken und
    Menace Lethal ergeben. Gerechnet wird ohne den Schaden der Geopferten."""
    ed = _sacrificer(me)
    if ed is None or not can_attack(ed, step) or _attack_value(me, opp, step) >= opp.life:
        return
    alts, n, kws = ed.card.sac_counter
    others = sorted((c for c in me.creatures if c is not ed and not c.dead),
                    key=lambda c: (not c.card.is_token, c.power, c.toughness, c.card.mv))
    pool = list(me.open) + [ANY_COLOR] * treasure_count(me)
    for k in range(1, min(3, len(others)) + 1):
        pool = pay(pool, alts)
        if pool is None:
            return
        picked, extra = others[:k], set(ed.extra)
        for c in picked:
            c.dead = True
        ed.bonus += n * k
        ed.extra |= set(kws)
        value = _attack_value(me, opp, step)
        for c in picked:
            c.dead = False
        ed.bonus -= n * k
        ed.extra = extra
        if value >= opp.life:
            for c in picked:
                sacrifice_for(me, c, e, "any")
            bury((me,), e)
            return


def surplus_land(p):
    """Ueberzaehliges Land auf der Hand (Laender auf Feld und Hand reichen schon fuer die teuerste Handkarte)."""
    lands = [c for c in p.hand if c.is_land]
    need = max((c.mv for c in p.hand if not c.is_land), default=0)
    if lands and len(p.lands) + len(lands) >= need:
        return lands[0]
    return None


def _draw(p, n=1):
    for _ in range(n):
        if p.library:
            p.hand.append(p.library.pop(0))
            p.drawn += 1


def tap_ready(p, c):
    """{T}-Faehigkeit erlaubt (302.6): seit Beginn des letzten eigenen Zugs unter unserer Kontrolle oder Haste."""
    return not c.tapped and not c.dead and (c.entered < p.turn_start or c.has("haste"))


def use_draw_ability(p, c, ab, e):
    """Eine Faehigkeit zum Ziehen: Loot (ziehen, dann abwerfen) immer; Rummage (erst abwerfen) nur mit
    ueberzaehligem Land; Land opfern (Marwyn, the Clearcutter) nur bei mindestens 6 Laendern auf dem Feld und mehr
    Laendern als der hoechste Manawert der Hand."""
    alts, tap, kind = ab
    if tap and not tap_ready(p, c):
        return False
    if kind == "rummage":
        gone = surplus_land(p)
        if gone is None or not _pay_ability(p, alts, "rest"):
            return False
    elif kind == "sac_land":
        need = max((x.mv for x in p.hand if not x.is_land), default=0)
        if len(p.lands) < 6 or len(p.lands) <= need or not _pay_ability(p, alts, "rest"):
            return False
    c.tapped = c.tapped or tap
    if kind == "loot":
        _draw(p)
        gone = choose_discard(p)
        if gone is not None:
            p.hand.remove(gone)
            p.graveyard.append(gone)
            discarded(p, e)
        e["events"].append(f"{p.name}: {c.card.name} lootet" + (f" (wirft {gone.name} ab)" if gone else ""))
    elif kind == "rummage":
        p.hand.remove(gone)
        p.graveyard.append(gone)
        discarded(p, e)
        _draw(p)
        e["events"].append(f"{p.name}: {c.card.name} wirft {gone.name} ab und zieht")
    else:
        sac = _redundant_land(p)
        p.lands.remove(sac)
        p.graveyard.append(sac)
        _draw(p)
        e["events"].append(f"{p.name}: {c.card.name} opfert {sac.name} und zieht")
    return True


def draw_abilities(p, e):
    """Am Ende des gegnerischen Zugs: alle Faehigkeiten zum Ziehen der eigenen Kreaturen und Artefakte (Murmuring
    Volume; Artefakte fallen nicht unter 302.6)."""
    for c in list(p.creatures):
        for ab in c.card.draw_abilities:
            use_draw_ability(p, c, ab, e)
    for card in list(p.perms):
        for ab in card.draw_abilities:
            use_draw_ability(p, Creature(card, -99), ab, e)


def choose_from_hand(victim, kind):
    """Wir waehlen aus der Hand des Gegners: eine bleibende Karte ("permanent") bzw. eine Nichtland-Karte, zuerst
    eine, die er naechste Runde wirken koennte (Manawert <= Laender + 1), dann der hoechste Manawert, bei Gleichstand
    der hoechste Removal-Score."""
    pool = [c for c in victim.hand if not c.is_land and (kind != "permanent" or not c.is_instant_sorcery)]
    if not pool:
        return None
    soon = [c for c in pool if c.mv <= len(victim.lands) + 1]
    return max(soon or pool, key=lambda c: (c.mv, c.removal_points, c.name))


def discarded(p, e):
    """p hat eine oder mehrere Karten abgeworfen (701.9): Tinybones beider Spieler schaedigt die Gegner seines
    Kontrolleurs."""
    for q in (p, p.opponent):
        if q is None:
            continue
        for c in q.creatures:
            if c.card.discard_ping and not c.dead:
                deal_noncombat(q, q.opponent, c.card.discard_ping, e)


def discard(p, n, e):
    done = 0
    for _ in range(n):
        card = choose_discard(p)
        if card is None:
            break
        p.hand.remove(card)
        p.graveyard.append(card)
        e["events"].append(f"{p.name} wirft ab: {card.name}")
        done += 1
    if done:
        discarded(p, e)


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
        discarded(caster, e)
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
        deal_noncombat(caster, victim, amount, e)
        e["events"].append(f"{caster.name}: {card.name} – {amount} Schaden an {victim.name}")
        return
    if target is None:
        e["events"].append(f"{caster.name}: {card.name} ohne Ziel")
        return
    if not ward_ok(caster, target):  # Ward nicht bezahlbar: anderes Ziel
        target = choose_target(spec, caster, victim)
        if target is None:
            e["events"].append(f"{caster.name}: {card.name} ohne Ziel (Ward)")
            return
    if not pay_ward(caster, target, e):
        e["events"].append(f"{caster.name}: {card.name} ohne Ziel (Ward)")
        return
    label = target.label()
    _draw(victim, target.card.targeted_draw)  # Ruric Thar, Biomagus: Ziel eines gegnerischen Zaubers
    if kind in ("destroy", "damage", "minus", "counters", "lock") and sacrifice_for(victim, target, e):
        bury((caster, victim), e)  # als Antwort geopfert: der Zauber hat kein Ziel mehr (608.2b)
        e["events"].append(f"{caster.name}: {card.name} ohne Ziel ({target.card.name} geopfert)")
        return
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
        check_auras(victim, e)
        e["events"].append(f"{caster.name}: {card.name} – {label} zurück auf die Hand")
        return
    elif kind == "lock":
        target.locked = True
        e["events"].append(f"{caster.name}: {card.name} – {label} gesperrt")
        return
    elif kind == "tuck":
        victim.creatures.remove(target)
        _leave(victim, target.card)
        check_auras(victim, e)
        if target.card.is_token:  # Token ausserhalb des Spielfelds hoert auf zu existieren (111.7)
            e["events"].append(f"{caster.name}: {card.name} – {label} verschwindet")
            return
        owner = target.owner or victim
        if target.card.mv <= len(owner.lands) + 1:  # wieder spielbar: oben, sonst unten
            owner.library.insert(0, target.card)
            where = "oben"
        else:
            owner.library.append(target.card)
            where = "unten"
        e["events"].append(f"{caster.name}: {card.name} – {label} {where} auf die Bibliothek")
        return
    e["events"].append(f"{caster.name}: {card.name} – {label}")
    before = target.finality
    if card.removal_exile:  # "If that permanent would die this turn, exile it instead"
        target.finality = True
    bury((caster, victim), e)
    target.finality = before


def _counter_mode(card):
    """Die Counter-Wirkung einer Karte (sie selbst oder ihr Modus), sonst None."""
    if not card.is_instant:
        return None
    if card.counter:
        return card
    if card.choices:
        return next((sub for sub in card.choices[1] if sub.counter), None)
    return None


def counter_fits(mode, spell):
    """Darf dieser Counter den Zauber treffen (Art und Farbe des Zaubers)?"""
    kind, colors, _n = mode.counter
    if kind == "creature_or_legendary" and not (spell.is_creature or spell.legendary):
        return False
    if kind == "noncreature" and spell.is_creature:
        return False
    return not colors or bool(colors_of_alts(spell.alts) & set(colors))


def counter_reason(holder, caster, spell, threat=None):
    """Kontern wir (holder) den Zauber von caster? 1. er bringt Lethal (Schaden am Spieler; Kampftrick oder Kreatur mit
    Haste, mit denen der Angriff Lethal wird), 2. Removal auf unsere gefaehrlichste Kreatur (auch Massenremoval, das sie
    toetet; keine Edikte), 3. Kreatur ab Manawert 3. threat: "lethal" oder das Ziel des Removals."""
    if threat == "lethal":
        return True
    face = sum(a[1] for m in spell.modes[:1] for a in m if a[0] == "face")
    spec = spell.removal
    if spec and spec[0] == "damage" and spec[3]:
        face = max(face, _amount(spec, caster))
    if face and face >= holder.life:
        return True
    alive = [c for c in holder.creatures if not c.dead]
    if spec and alive:
        best = max(alive, key=danger)
        if spec[0] == "sweep":
            return True
        if spec[0] == "sweep_damage":
            if best.toughness - best.damage <= spec[1]:
                return True
        elif spec[0] != "edict":
            target = threat if isinstance(threat, Creature) else choose_target(spec, caster, holder)
            if target is best:
                return True
    if spell.is_creature and spell.mv >= 3:
        return True
    if spell.is_creature and spell.haste and caster.turn_start == caster.now:  # Haste vor dem Kampf
        new = Creature(spell, caster.now)
        new.ctl = caster
        mine = [c for c in caster.creatures if can_attack(c, caster.now)]
        blockers = [b for b in holder.creatures if not b.tapped and not b.dead]
        if max_through(mine + [new], blockers) >= holder.life > max_through(mine, blockers):
            return True
    return False


def try_counter(caster, spell, step, e, threat=None, effects=None):
    """Antwortfenster: der Gegner von caster darf den Zauber kontern (701.6). Er nutzt den billigsten passenden
    Counterspell mit offenem Mana; weiche Counter ("unless its controller pays {N}") nur, wenn caster nicht zahlen kann.
    Ein Counterspell ist selbst keiner der Gruende, also gibt es keine Gegenkonter. Gibt True zurueck, wenn gekontert."""
    holder = caster.opponent
    if holder is None or spell.uncounterable:
        return False
    if not any(counter_reason(holder, caster, fx, threat) for fx in [spell] + list(effects or ())):
        return False
    options = []
    for c in holder.hand:
        mode = _counter_mode(c)
        if mode is None or not counter_fits(mode, spell):
            continue
        n = mode.counter[2]
        if n and _payable(caster, ((n, ()),)):
            continue  # weicher Counter: der Gegner wuerde zahlen
        alts = _alts(holder, c)
        if _payable(holder, alts):
            options.append((min(g + sum(k for _c, k in cols) for g, cols in alts), c.name, c, alts))
    if not options:
        return False
    _cost, _name, card, alts = min(options, key=lambda o: (o[0], o[1]))
    _pay_open(holder, alts)
    holder.hand.remove(card)
    holder.graveyard.append(card)
    on_cast(holder, card, step, e)
    e["events"].append(f"{holder.name}: {card.name} kontert {spell.name}")
    return True


def held_counter(p, orig=None):
    """Billigster Counterspell der Hand (Kosten nach Behold a Jace) zum Freihalten: (Karte, Kosten) oder None.
    orig: Handkarte -> Originalkarte (siehe held_removal)."""
    orig = orig or {}
    opts = [(c, _alts(p, orig.get(c, c))) for c in p.hand if _counter_mode(c) is not None]
    if not opts:
        return None
    return min(opts, key=lambda o: (min(g + sum(n for _c, n in cols) for g, cols in o[1]), o[0].name))


def _resolve(me, opp, card, step, entry, owner=None, to_exile=False, modes=None):
    """Eine gewirkte Karte kommt ins Spiel bzw. wirkt: Kreatur aufs Feld, Permanents, Instants/Sorceries in den
    Friedhof. Erst die Ausloeser beim Wirken (on_cast), dann bei Permanents die Betreten-Effekte (wie bei jedem
    anderen Weg ins Spiel), bei Instants/Sorceries und Prepared-Kopien ihre Effekte (card_effects). Vorher darf der
    Gegner kontern: dann nur die Ausloeser beim Wirken, die Karte geht in den Friedhof (Flashback: Exil, Kopie: weg)."""
    if try_counter(me, card, step, entry, effects=modes):
        if card.is_copy:
            src = next((c for c in me.creatures if c.prepared and c.card.prepared[1] == card), None)
            if src is not None:
                src.prepared = False
        elif not to_exile:
            (owner or me).graveyard.append(card)
        on_cast(me, card, step, entry)
        bury((me, opp), entry)
        return
    if card.is_copy:  # Prepared-Kopie: eine passende Kreatur ist nicht mehr prepared, kein Friedhof
        src = next((c for c in me.creatures if c.prepared and c.card.prepared[1] == card), None)
        if src is not None:
            src.prepared = False
    elif card.is_creature:
        me.creatures.append(Creature(card, step))
        me.creatures[-1].owner = owner
    elif card.is_instant_sorcery:
        if not to_exile:  # Flashback: danach ins Exil
            (owner or me).graveyard.append(card)
    else:
        me.perms.append(card)
    on_cast(me, card, step, entry)
    if card.is_creature and not card.is_copy:
        creature_enters(me, me.creatures[-1], step, entry, opp)
    elif card.is_instant_sorcery or card.is_copy:
        card_effects(me, opp, card, step, entry, modes)
    else:
        permanent_enters(me, opp, card, step, entry)
    bury((me, opp), entry)


def mode_value(p, opp, sub, step, end_step=False):
    """Wert eines Modus: Lethal > Removal (toetet) > Karte ziehen > Token > Marken/Pumps > Schaden > Leben.
    end_step: am Ende des gegnerischen Zugs zaehlen Pumps bis Rundenende nicht."""
    spec = sub.removal
    atoms = [a for m in sub.modes[:1] for a in m]
    face = sum(a[1] for a in atoms if a[0] == "face")
    any_dmg = _amount(spec, p) if spec and spec[3] and spec[0] == "damage" else 0
    if opp is not None and (face or any_dmg) and face + any_dmg >= opp.life:
        return (6, face + any_dmg)
    if spec and opp is not None:
        if spec[0] in ("sweep", "sweep_damage", "edict"):
            if any(not c.dead for c in opp.creatures):
                return (5, 0, False, 0)
        else:
            target = choose_target(spec, p, opp)
            if target is not None:
                return (5,) + danger(target)
    if sub.draws:
        return (4, sub.draws)
    if sub.loot:
        return (3.5,)
    if sub.creates_tokens:
        return (3, sum(n * (t.power + t.toughness) for n, t in sub.creates_tokens))
    alive = [c for c in p.creatures if not c.dead]
    if any(a[0] in ("counter", "counter_all") for a in atoms) and alive:
        return (2, 1)
    if not end_step and any(a[0] in ("pump", "pump_all") for a in atoms) and any(can_attack(c, step) for c in alive):
        return (2, 0)
    if face or any_dmg:
        return (1.5, face + any_dmg)
    if sub.spell_life or sub.etb_life:
        return (1, sub.spell_life + sub.etb_life)
    if sub.surveil:
        return (0.5,)
    return (0,)


def choose_modes(p, opp, card, step, end_step=False):
    """So viele verschiedene Modi wie verlangt, die wertvollsten zuerst."""
    n, subs = card.choices
    return sorted(subs, key=lambda s: mode_value(p, opp, s, step, end_step), reverse=True)[:n]


def permanent_enters(p, opp, card, step, e):
    """Ein Nichtkreatur-Permanent kam ins Spiel: Jace-Ausloeser und Betreten-Effekte."""
    if card.twin:
        attach_twin(p, opp, card, e)
    _jace_etb(p, card, step, e)
    gain_life(p, card.etb_life)
    card_effects(p, opp, card, step, e)


def card_effects(me, opp, card, step, entry, modes=None):
    """Effekte einer Karte: bei Instants/Sorceries beim Auflösen, bei Permanents beim Betreten (603.6a, egal wie sie
    ins Spiel kommen). Treasure, Schaden an uns, Removal, Abwerfen, Schaden/Marken/Pumps, Ziehen, Surveil, Leben,
    Zurueckholen aus dem Friedhof, Token."""
    if opp is None:
        opp = me.opponent
    if card.choices:  # modale Karte: nur die gewaehlten Modi wirken
        for sub in (modes if modes is not None else choose_modes(me, opp, card, step)):
            entry["events"].append(f"{me.name}: {card.name} – Modus: {_mode_label(sub)}")
            card_effects(me, opp, sub, step, entry)
        return
    if card.is_mode:
        for ef in once_effects(card):
            if ef[1] == "spell":
                _jace_add(me, ef[2], entry)
    if card.treasure:
        me.treasures += card.treasure
    if card.heartwood:  # 111.10x: Heartwood-Token (Mana ab dem naechsten Zug)
        me.perms += [HEARTWOOD] * card.heartwood
        entry["events"].append(f"{me.name}: {card.name} – {card.heartwood} Heartwood-Token")
    me.life -= card.life_loss  # "You lose N life"
    if card.loot:  # "Draw a card, then discard a card"
        _draw(me)
        gone = choose_discard(me)
        if gone is not None:
            me.hand.remove(gone)
            me.graveyard.append(gone)
            discarded(me, entry)
    if card.self_damage:  # "damage to each player" trifft auch uns
        me.life -= card.self_damage
    effects = card
    if card.removal and opp is not None and _edict_paid(me, opp, card, entry):
        cast_removal(card, me, opp, entry, step)
        if card.removal[3]:  # any target: der Schaden ist schon verteilt
            effects = card._replace(modes=tuple(tuple(a for a in m if a[0] != "face") for m in card.modes))
    if card.discard and opp is not None:
        discard(opp, card.discard, entry)
    for _k in range(card.impulse):  # Blazing Crescendo: bis Ende des naechsten eigenen Zugs spielbar
        if me.library:
            top = me.library.pop(0)
            me.impulse.append((top, me.own_turns + 1))
            entry["events"].append(f"{me.name}: {card.name} – {top.name} ins Exil (spielbar)")
    if card.rummage_spell:  # "You may discard a card. If you do, draw a card."
        gone = surplus_land(me)
        if gone is not None:
            me.hand.remove(gone)
            me.graveyard.append(gone)
            discarded(me, entry)
            _draw(me)
            entry["events"].append(f"{me.name}: {card.name} – wirft {gone.name} ab und zieht")
    if card.hand_pick and opp is not None:
        pick = choose_from_hand(opp, card.hand_pick)
        if pick is not None:
            opp.hand.remove(pick)
            opp.graveyard.append(pick)
            discarded(opp, entry)
            entry["events"].append(f"{me.name}: {card.name} – {opp.name} wirft {pick.name} ab")
    if effects.modes:
        board, bonus, pump = me.board()
        before = [c.pump for c in me.creatures]
        gain = apply_effects(effects, board, bonus, pump, step)
        me.write_back(bonus, pump)
        ratio = _tough_ratio(card)
        for c, old in zip(me.creatures, before):  # Pumps +P/+T: Toughness im Verhaeltnis T/P
            if c.pump > old:
                c.tpump += round((c.pump - old) * ratio)
        if gain["face"] and opp is not None:
            deal_noncombat(me, opp, gain["face"], entry)
    if card.draws:
        if me.predrawn[card] > 0:  # schon bei der Planung der Main Phase gezogen
            me.predrawn[card] -= 1
        else:
            _draw(me, card.draws)
    if card.surveil:
        surveil_cards(me, [card.surveil], entry, card.name)
    gain_life(me, card.spell_life)
    if card.reanimate:
        reanimate(me, opp, card.reanimate, step, entry)
    make_tokens(me, card.creates_tokens, step, entry, opp, card.name)


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


def _edict_paid(me, opp, card, e):
    """Winter: "you may sacrifice a creature ... When you do, each opponent sacrifices". Wir opfern unsere schwaechste
    andere Kreatur, aber nur, wenn der Gegner eine Kreatur hat; sonst entfaellt das Edikt."""
    if not card.edict_cost:
        return True
    source = me.creatures[-1] if card.is_creature and me.creatures and me.creatures[-1].card == card else None
    others = [c for c in me.creatures if not c.dead and c is not source]
    if not others or not any(not c.dead for c in opp.creatures):
        return False
    pick = min(others, key=_value)
    pick.dead = True
    e["events"].append(f"{me.name}: opfert {pick.card.name} für {card.name}")
    bury((me,), e)
    return True


def _gy_matches(card, filt, mv_max):
    if filt == "creature":
        ok = card.is_creature
    elif filt == "land":
        ok = card.is_land
    else:
        ok = not card.is_instant_sorcery
    return ok and card.mv <= mv_max


def gy_candidates(p, filt, mv_max=99, exclude=None):
    out = [c for c in p.graveyard if _gy_matches(c, filt, mv_max)]
    if exclude is not None and exclude in out:
        out.remove(exclude)
    return out


def _best_from_gy(p, cands):
    """Staerkste Karte: Laender mit den meisten neuen Farben, sonst hoechster Manawert, dann Power."""
    if all(c.is_land for c in cands):
        have = set().union(*(land.land_colors for land in p.lands)) if p.lands else set()
        return max(cands, key=lambda land: (len(set(land.land_colors) - have), -cands.index(land)))
    return max(cands, key=lambda c: (not c.is_land, c.mv, c.power, c.name))


def put_back(p, card, dest, step, e, opp=None, tapped=False, counters=0, finality=False):
    """Eine Karte aus dem Friedhof (schon entfernt) aufs Feld bzw. auf die Hand."""
    if dest == "hand":
        p.hand.append(card)
        e["events"].append(f"{p.name}: {card.name} aus dem Friedhof auf die Hand")
        return
    if card.is_creature:
        c = Creature(card, step)
        c.tapped, c.bonus, c.finality = tapped, counters, finality
        p.creatures.append(c)
        creature_enters(p, c, step, e, opp, cast=False)
    elif card.is_land:
        p.lands.append(card)
        if opp is not None:
            on_land(p, opp, card, step, e, with_mana=False)
    else:
        p.perms.append(card)
        permanent_enters(p, opp, card, step, e)
    e["events"].append(f"{p.name}: {card.name} aus dem Friedhof ins Spiel")


def reanimate(p, opp, spec, step, e):
    """Zauber "Return target/all ... from your graveyard to the battlefield/your hand" (Card.reanimate)."""
    count, filt, mv_max, dest, counters = spec
    cands = gy_candidates(p, filt, mv_max)
    if not cands:
        return
    picks = cands if count == "all" else [_best_from_gy(p, cands)]
    for card in picks:
        p.graveyard.remove(card)
        put_back(p, card, dest, step, e, opp, counters=counters)


def reanimate_ok(p, card):
    return not card.reanimate or bool(gy_candidates(p, card.reanimate[1], card.reanimate[2]))


def main_phase_spells(me, opp):
    """Karten fuer die Main Phases: keine Instants, keine Flash-Karten, Removal nur mit gueltigem Ziel; dazu die
    Kopien der Prepared-Kreaturen."""
    cards = [c for c in me.hand if not c.is_land] + copies(me)
    return [c for c in cards if not c.is_instant and not c.flash and legend_ok(me, c) and reanimate_ok(me, c)
            and (not c.rummage_spell or surplus_land(me) is not None)
            and (not c.twin or twin_host(me, opp) is not None)
            and (not c.cast_threshold or threshold(me))
            and (any(mode_value(me, opp, s, 0) > (0,) for s in c.choices[1]) if c.choices and not c.is_creature
                 else not c.removal or c.removal[4] == "etb" or has_target(c, me, opp))]


def copies(p):
    return [c.card.prepared[1] for c in p.creatures if c.prepared and not c.dead]


def _cast_from_open(p, card):
    if not _pay_open(p, _alts(p, card)):
        return False
    p.hand.remove(card)
    return True


_TRICK_KINDS = ("pump", "counter", "pump_all", "counter_all")


def _trick_atoms(card):
    return _trick_modes(card)


def _trick_modes(card):
    """[(Modus, Toughness der Pumps, verliehene Schluesselwoerter)] der Kampftrick-Modi einer Karte; bei modalen
    Karten je Modus mit Pumps/Marken oder Schluesselwoertern."""
    if card.choices:
        out = []
        for sub in card.choices[1]:
            atoms = sub.modes[0] if sub.modes else ()
            if any(a[0] in _TRICK_KINDS for a in atoms) or sub.grant_kw:
                out.append((atoms, sub.pump_tough[0] if sub.pump_tough else (), sub.grant_kw))
        return out
    tough = card.pump_tough or ()
    out = [(m, tough[i] if i < len(tough) else (), card.grant_kw) for i, m in enumerate(card.modes)
           if any(a[0] in _TRICK_KINDS for a in m)]
    if not out and card.grant_kw:
        out = [((), (), card.grant_kw)]
    return out


def _apply_trick(mode, target, own, tough=(), grants=()):
    if grants:
        target.extra |= set(grants)
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
        for mode, tough, grants in _trick_modes(card):
            for i, target in enumerate(own):
                saved = [(c.pump, c.bonus, c.tpump, set(c.extra)) for c in own]
                _apply_trick(mode, target, own, tough, grants)
                gain = _score(pairs, attacking, opp.life) - base
                for c, (pu, bo, tp, ex) in zip(own, saved):
                    c.pump, c.bonus, c.tpump, c.extra = pu, bo, tp, ex
                if gain > 0 and (best is None or gain > best[0]):
                    best = (gain, mode, i, tough, grants, base < 1000 <= base + gain)
        if best is None:
            continue
        _cast_from_open(p, card)
        if try_counter(p, card, step, e, threat="lethal" if best[5] else None):
            p.graveyard.append(card)
            on_cast(p, card, step, e)
            continue
        _apply_trick(best[1], own[best[2]], own, best[3], best[4])
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
        if card.is_instant and card.choices:
            for sub in card.choices[1]:
                if sub.removal and sub.removal[4] == "spell":
                    out.append((card, _alts(p, card), sub, True, "hand"))
        elif card.is_instant and card.removal and card.removal[4] == "spell":
            out.append((card, _alts(p, card), card, True, "hand"))
        elif card.hand_removal:
            out.append((card, card.hand_removal[0], card._replace(removal=card.hand_removal[1]), False, "hand"))
    if threshold(p):
        for card in p.exiled:
            if card.is_instant and card.removal and card.removal[4] == "spell":
                out.append((card, _discounted(_any_mana(card), discount(p), p).alts, card, True, "exile"))
    for card in p.graveyard:
        if card.flashback and card.is_instant and card.removal and card.removal[4] == "spell":
            out.append((card, _flashback_version(p, card).alts, card, True, "flashback"))
    return out


def held_removal(me, opp, orig=None):
    """Mana freihalten (Variante B): das billigste Removal, das wir im Zug des Gegners mit offenem Mana nutzen koennen
    (Instants, Removal per Abwerfen von der Hand, Flash-Kreaturen mit Removal beim Betreten), wenn der Gegner jetzt
    eine Kreatur hat, die es toetet. Gibt (Karte, Kosten) oder None zurueck. orig: Handkarte -> Originalkarte (in der
    Main Phase sind die Kosten der Handkarten schon angepasst; nicht doppelt rechnen)."""
    orig = orig or {}
    opts = [(card, _alts(me, orig.get(card, card)) if not card.hand_removal else alts, rc)
            for card, alts, rc, _spell, zone in instant_removals(me) if zone == "hand"]
    opts += [(c, _alts(me, orig.get(c, c)), c) for c in me.hand
             if c.flash and c.is_creature and c.removal and c.removal[4] == "etb" and legend_ok(me, c)]
    alive = [c for c in opp.creatures if not c.dead]
    ok = []
    for card, alts, rc in opts:
        spec = rc.removal
        if spec[0] in ("sweep", "sweep_damage", "edict"):
            if alive:
                ok.append((card, alts))
        elif choose_target(spec, me, opp) is not None:
            ok.append((card, alts))
    if not ok:
        return None
    return min(ok, key=lambda o: (min(g + sum(n for _c, n in cols) for g, cols in o[1]), o[0].name))


def _flashback_version(p, card):
    """Die Karte mit ihren Flashback-Kosten (inkl. Kostensenkung bzw. Steuer)."""
    return _discounted(card._replace(alts=card.flashback), discount(p), p)


def threshold(p):
    return len(p.graveyard) >= 7


def _any_mana(card):
    """Kosten mit Mana jeder Art (nur noch der Manawert zaehlt)."""
    return card._replace(alts=((card.mv, ()),)) if card.alts else card


def _zone(p, zone):
    return {"exile": p.exiled, "flashback": p.graveyard}.get(zone, p.hand)


def _use_removal(p, card, alts, is_spell, step, e, zone="hand", other=None, fx=None, target=None):
    """Bezahlt und legt die Karte in den Friedhof (gewirkt oder abgeworfen); aus dem Exil in den Friedhof des
    Besitzers (other: der Gegner, falls der Besitzer nicht gespeichert ist). Gibt False zurueck, wenn der Zauber
    gekontert wurde (dann kein Removal)."""
    if not _pay_open(p, alts):
        return False
    if zone == "flashback":  # aus dem Friedhof, danach ins Exil
        p.graveyard.remove(card)
    else:
        (p.exiled if zone == "exile" else p.hand).remove(card)
        ((p.exiled_from or other or p) if zone == "exile" else p).graveyard.append(card)
    if is_spell and try_counter(p, card, step, e, threat=target, effects=[fx] if fx is not None else None):
        on_cast(p, card, step, e)
        return False
    if is_spell:
        on_cast(p, card, step, e)
        fx = fx or card  # Effekte: bei modalen Karten der gewaehlte Modus
        face = sum(a[1] for a in fx.modes[0] if a[0] == "face") if fx.modes and not fx.removal[3] else 0
        if face and other is not None:  # z. B. Extended Absence: "deals 1 damage to each opponent"
            deal_noncombat(p, other, face, e)
        gain_life(p, fx.spell_life)
    else:
        e["events"].append(f"{p.name}: wirft {card.name} ab (Fähigkeit)")
        discarded(p, e)
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
        if _use_removal(dfn, card, alts, is_spell, step, e, zone, att, rc, target=target):
            cast_removal(rc, dfn, att, e, step, target=target)
    alive = [a for a in attackers if a in att.creatures and not a.dead and not a.locked]
    for card in sorted([c for c in dfn.hand if c.flash and c.is_creature], key=lambda c: -c.mv):
        if not affordable(dfn, card) or not legend_ok(dfn, card):
            continue
        new = Creature(card, step)
        blockers = [b for b in dfn.creatures if not b.tapped and not b.dead]
        lethal = max_through(alive, blockers) >= dfn.life and max_through(alive, blockers + [new]) < dfn.life
        good = any(can_block(new, a) and outcome(a, [new]) == (True, [False]) for a in alive)
        if lethal or good:
            _cast_from_open(dfn, card)
            if try_counter(dfn, card, step, e):
                dfn.graveyard.append(card)
                on_cast(dfn, card, step, e)
                continue
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
        if card not in _zone(dfn, zone) or not _payable(dfn, alts) \
                or not has_target(rc, dfn, act):
            continue
        if rc.removal[3] and choose_target(rc.removal, dfn, act) is None and act.life > _amount(rc.removal, dfn):
            continue  # "any target" am Endstep nur gegen eine Kreatur oder als Lethal
        if _use_removal(dfn, card, alts, is_spell, step, e, zone, act, rc):
            cast_removal(rc, dfn, act, e, step)
    for card in sorted([c for c in dfn.hand if c.flash], key=lambda c: -c.mv):
        if card in dfn.hand and legend_ok(dfn, card) and _cast_from_open(dfn, card):
            e["events"].append(f"{dfn.name}: {card.name} mit Flash am Ende des Zugs")
            _resolve(dfn, act, card, step, e)
            if card in dfn.graveyard and not card.is_instant_sorcery:
                dfn.graveyard.remove(card)
    flashbacks = [c for c in dfn.graveyard if c.flashback and c.is_instant and not c.removal and not _trick_atoms(c)]
    for card in sorted([c for c in dfn.hand if c.is_instant and c.choices], key=lambda c: -c.mv):
        if card not in dfn.hand:
            continue
        values = [(mode_value(dfn, act, sub, step, end_step=True), i) for i, sub in enumerate(card.choices[1])]
        best = max(values) if values else ((0,), 0)
        if best[0] <= (0,) or best[0][0] >= 5:  # Removal und Lethal laufen ueber die Removal-Wege
            continue
        if _cast_from_open(dfn, card):
            e["events"].append(f"{dfn.name}: {card.name} am Ende des Zugs")
            _resolve(dfn, act, card, step, e, modes=[card.choices[1][best[1]]])
    for card in sorted([c for c in dfn.hand if c.is_instant and not c.removal and not _trick_atoms(c)
                        and not c.choices and not c.counter], key=lambda c: -c.mv):
        if card in dfn.hand and reanimate_ok(dfn, card) and _cast_from_open(dfn, card):
            e["events"].append(f"{dfn.name}: {card.name} am Ende des Zugs")
            _resolve(dfn, act, card, step, e)
    for card in sorted(flashbacks, key=lambda c: -c.mv):  # nur Karten, die schon vorher im Friedhof lagen
        if card not in dfn.graveyard or not reanimate_ok(dfn, card):
            continue
        if card.flashback_discard and not [c for c in dfn.hand]:
            continue  # Zusatzkosten: eine Karte abwerfen
        if not _pay_open(dfn, _flashback_version(dfn, card).alts):
            continue
        dfn.graveyard.remove(card)
        if card.flashback_discard:
            gone = choose_discard(dfn)
            dfn.hand.remove(gone)
            dfn.graveyard.append(gone)
            e["events"].append(f"{dfn.name}: wirft {gone.name} ab (Flashback)")
            discarded(dfn, e)
        e["events"].append(f"{dfn.name}: {card.name} per Flashback am Ende des Zugs")
        _resolve(dfn, act, card._replace(draws=card.alt_draws) if card.alt_draws else card, step, e, to_exile=True)
    end_step_cycling(dfn, e)
    lasting_abilities(dfn, act, step, e, own_turn=False, mode="rest")
    tap_artifact_abilities(dfn, e)
    draw_abilities(dfn, e)
    twin_activate(dfn, act, step, e, end_step=True)


def confidant_end_step(p, e):
    """Enlightened Confidant: nach Lebensgewinn in diesem Zug Surveil 1; eine abgelegte Karte mit Manawert hoechstens
    dem gewonnenen Leben kommt auf die Hand."""
    for c in p.creatures:
        if not c.card.confidant or c.dead or p.gained <= 0 or not p.library:
            continue
        mark_surveil(p, e)
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
    Kreaturen, die seit Beginn des letzten eigenen Zugs da sind (oder Haste, 302.6)."""
    out = []
    for c in p.creatures:
        if c.dead:
            continue
        for ab in c.card.abilities:
            if not _speed_ok(ab, own_turn, main):
                continue
            if ab[2] and not tap_ready(p, c):  # 302.6
                continue
            out.append((c, ab))
    for card in p.perms:
        for ab in card.abilities:
            if _speed_ok(ab, own_turn, main) and not ab[2] and not any(a[-1] == "self" for a in ab[4]):
                out.append((None, ab))
    return out


def _kinds(ab):
    return {a[0] for a in ab[4]}


def _is_target_scope(scope):
    return scope in ("target", "nonlegendary", "target_counter") or str(scope).startswith("pow_le_")


def _needs_target(ab):
    return any(len(a) > 2 and _is_target_scope(a[-1]) for a in ab[4])


def _targets(p, src, ab, pool=None):
    if not _needs_target(ab):
        return [None]
    cands = [c for c in (pool if pool is not None else p.creatures) if not c.dead and c in p.creatures]
    scopes = [a[-1] for a in ab[4] if len(a) > 2]
    if "nonlegendary" in scopes:
        cands = [c for c in cands if not c.card.legendary]
    if "target_counter" in scopes:  # Tomik: Kreatur mit +1/+1-Marke
        cands = [c for c in cands if c.bonus > 0]
    for sc in scopes:
        if str(sc).startswith("pow_le_"):  # Eardrum Rattler: eine andere Kreatur mit Power hoechstens N
            cands = [c for c in cands if c is not src and c.power <= int(sc[7:])]
    return cands


def artifact_count(p):
    """Artefakte unter unserer Kontrolle: Artefaktkreaturen, Artefakt-Permanents (Heartwood ...) und Treasure."""
    return (sum(1 for c in p.creatures if c.card.is_artifact and not c.dead)
            + sum(1 for c in p.perms if c.is_artifact) + p.treasures)


def _snapshot(p):
    return [(c, c.pump, c.tpump, c.bonus, set(c.extra)) for c in p.creatures]


def _restore(snap):
    for c, pu, tp, bo, ex in snap:
        c.pump, c.tpump, c.bonus, c.extra = pu, tp, bo, ex


def apply_ability(p, src, ab, target, e=None, gy=None):
    """Wirkung einer Faehigkeit (src: Quelle, target: gewaehltes Ziel, gy: Karte aus dem Friedhof). Gibt False zurueck,
    wenn sie nichts bewirkt."""
    did = False
    for atom in ab[4]:
        kind = atom[0]
        if kind == "return":  # Karte aus dem Friedhof auf die Hand (Marwyn, Theoretical Necromancer)
            cands = gy_candidates(p, atom[1], exclude=gy if atom[3] else None)
            if not cands:
                continue
            if e is not None:
                pick = _best_from_gy(p, cands)
                p.graveyard.remove(pick)
                put_back(p, pick, atom[2], p.now, e, p.opponent)
            did = True
            continue
        if kind == "return_self":  # die Karte selbst aus dem Friedhof (Blessed Ghoul, Gallia, Grim Repriser)
            if e is not None and gy is not None:
                if atom[4] == "exile_creature":
                    others = gy_candidates(p, "creature")
                    p.graveyard.remove(min(others, key=lambda c: (c.mv, c.power, c.name)))
                put_back(p, gy, atom[1], p.now, e, p.opponent, tapped=atom[2], counters=atom[3],
                         finality=gy.finality)
            did = True
            continue
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
                c.pump += artifact_count(p) if atom[1] == "artifacts" else atom[1]  # Pia: X = Artefakte
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
    apply_ability(p, src, ab, target, e, gy)
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
        score += res["player"] + res["jace"] + res["lifelink_attacker"] + (1000 if lethal else 0)
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
    rank = {"counter": 0, "return_self": 1, "return": 1, "token": 1, "empower": 2, "surveil": 3}
    for _round in range(10):
        sources = [(src, ab, None) for src, ab in ability_sources(p, step, own_turn, main=own_turn)]
        sources += [(None, (card.gy_ability[0], 0, False, "instant", card.gy_ability[1]), card)
                    for card in dict.fromkeys(p.graveyard) if card.gy_ability]
        for card in dict.fromkeys(p.graveyard):
            if card.gy_return and _gy_return_ok(p, card):
                ret = card.gy_return
                sources.append((None, (ret[0], 0, False, "instant", (("return_self",) + ret[1:],)), card))
        options = []
        for src, ab, gy in sources:
            kinds = _kinds(ab)
            if "grant" in kinds and "token" in kinds:  # Token und danach Haste fuer alle (Ingris)
                kinds = kinds - {"grant"}
            if not kinds or not kinds <= set(rank):
                continue
            if "surveil" in kinds and (own_turn or not p.library):
                continue
            if "return" in kinds and not apply_ability(p, src, ab, None, None, gy):
                continue  # nichts Passendes im Friedhof
            if "return" in kinds and any(a[1] == "land" for a in ab[4] if a[0] == "return") \
                    and len(p.lands) + sum(c.is_land for c in p.hand) >= CYCLE_CAP:
                continue  # Laender nur zurueck, solange welche fehlen
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


def _gy_return_ok(p, card):
    """Bedingungen und Zusatzkosten einer Faehigkeit "Return this card from your graveyard"."""
    _alts, _dest, _tapped, _counters, extra, cond = card.gy_return
    if cond == "noncombat" and not p.dealt_direct > p.direct_mark:
        return False
    if extra == "exile_creature" and not gy_candidates(p, "creature", exclude=card):
        return False
    return legend_ok(p, card) if _dest == "battlefield" else True


def phoenix_check(me, opp, step, e):
    """Zu Beginn des eigenen Kampfs: sind in diesem Zug zwei oder mehr Kreaturen gestorben, kommen Karten wie
    Darklight Phoenix aus dem Friedhof ins Spiel."""
    died = (me.deaths - me.deaths_mark) + (opp.deaths - opp.deaths_mark)
    if died < 2:
        return
    for card in [c for c in me.graveyard if c.phoenix]:
        me.graveyard.remove(card)
        put_back(me, card, "battlefield", step, e, opp)


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
            if not grants & {"flying", "menace", "unblockable"} or not _kinds(ab) <= {"pump", "grant"}:
                continue
            if ab[2] and (src is None or any(a[-1] == "self" for a in ab[4])):
                continue  # mit {T}: nur fuer eine andere Kreatur; die Quelle greift dann nicht an
            pool = [c for c in me.creatures if can_attack(c, step) and not (ab[2] and c is src)]
            if any(a[-1] == "self" for a in ab[4]) and src not in pool:
                continue
            for target in _targets(me, src, ab, pool):
                snap = _snapshot(me)
                was_tapped = src.tapped if src is not None else False
                if ab[2]:
                    src.tapped = True
                apply_ability(me, src, ab, target)
                value = _attack_value(me, opp, step)
                _restore(snap)
                if ab[2]:
                    src.tapped = was_tapped
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
    pumpers = [c for c in me.creatures if c.card.surveil_team_pump and not c.dead]  # Prudent Fateseer
    if me.surveilled or not (waiting or pumpers) or not me.library:
        return
    base = _attack_value(me, opp, step)
    snap = _snapshot(me)
    for c in waiting:
        c.lifted = True
    for c in me.creatures:
        if not c.dead:
            c.pump += sum(x.card.surveil_team_pump for x in pumpers)
    value = _attack_value(me, opp, step)
    _restore(snap)
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


def _hits_face(card):
    """Macht der Zauber Schaden am Gegner (Vicious Verse, Burn mit "any target")?"""
    return (any(a[0] == "face" for m in card.modes for a in m)
            or bool(card.removal and card.removal[0] == "damage" and card.removal[3]))


def combat_etb(me, opp, card, step, chosen=()):
    """Verbessert das Betreten dieser Kreatur den Kampf in diesem Zug? Dann kommt sie in Main 1:
    Surveil, waehrend eine Kreatur auf ein Surveil wartet (Surveillance Phantasm); Removal, das einen Blocker entfernt,
    der einen unserer Angreifer fressen wuerde; Pumps/Marken, wenn Kreaturen angreifen koennen (auch Mabel fuer eine
    Kreatur mit Haste aus diesem Zug, auch eine, die in diesem Zug noch gewirkt wird); Lebensgewinn, der angreifende Engel wachsen laesst (Lyra)."""
    if card.choices:
        return any(combat_etb(me, opp, sub, step, chosen) for sub in card.choices[1])
    alive = [c for c in me.creatures if not c.dead]
    attackers = [c for c in alive if can_attack(c, step)]
    waiting = [c for c in alive if c.card.surveil_attack and not c.lifted and not c.tapped and c.dmg > 0
               and (c.entered < step or c.card.haste)]
    if card.surveil and waiting and not me.surveilled:
        return True
    if card.removal and card.removal[4] == "etb" and attackers:
        if any(any(_eats(t, a) for a in attackers) for t in valid_targets(card.removal, me, opp)):
            return True
    if attackers and (card.artifact_pump or any(a[0] in ("counter", "counter_all", "pump", "pump_all")
                                                 for m in card.modes for a in m)):
        return True
    if card.enter_counter or any(c.card.enter_counter for c in alive):
        if any(c.entered == step for c in attackers) or any(c.is_creature and c.haste for c in chosen):
            return True
    if card.is_creature and any(c.card.ally_enter_pump and can_attack(c, step) for c in alive):
        return True  # Arni, Renowned Champion waechst vor dem Angriff
    if "haste" in card.noncombat_kw:  # Whiplash Wordsmith: Haste nach Schaden ausserhalb des Kampfs am Gegner
        if me.dealt_direct > me.direct_mark or any(_hits_face(c) for c in chosen if not c.is_creature):
            return True
    if any(c.card.ally_enter_life for c in alive):
        angels = {c.card.lifegain_counter[1] for c in alive if c.card.lifegain_counter}
        if any(t in a.card.creature_types for a in attackers for t in angels):
            return True
    return False


def stun_from_graveyard(me, opp, step, e):
    """Cryotheory Adept aus dem Friedhof (nur zur Sorcery-Zeit): tappt die gefaehrlichste Kreatur des Gegners, die
    blocken koennte (ungetappt) oder uns gefaehrlich wird (Kampfschaden 3 oder mehr), mit freiem Mana; die Stun-Marke
    haelt sie auch beim naechsten Untap getappt."""
    for card in list(dict.fromkeys(me.graveyard)):
        if not card.gy_ability or _kinds((0, 0, False, "", card.gy_ability[1])) != {"stun"}:
            continue
        cands = [c for c in opp.creatures if not c.dead and not hexproof(c) and ward_ok(me, c) and not c.stun
                 and (not c.tapped or c.dmg >= 3)]
        if not cands:
            return
        pick = max(cands, key=danger)
        if not _pay_ability(me, card.gy_ability[0], "free"):
            continue
        me.graveyard.remove(card)
        pay_ward(me, pick, e)
        pick.tapped = True
        pick.stun += 1
        e["events"].append(f"{me.name}: {card.name} (aus dem Friedhof) – {pick.card.name} getappt mit Stun-Marke")


def equip_gear(me, step, e):
    """Ausruestung anlegen (Sorcery-Zeit, freies Mana): an den staerksten Angreifer (bei Gleichstand der mit den meisten
    Marken, das macht Warrior's Blades billiger); umgehaengt nur, wenn die bisherige Kreatur nicht angreifen kann."""
    for g in [c for c in me.perms if c.equip]:
        host = next((c for c in me.creatures if g in c.gear and not c.dead), None)
        if host is not None and can_attack(host, step):
            continue
        cands = [c for c in me.creatures if can_attack(c, step) and c is not host]
        if not cands:
            continue
        pick = max(cands, key=lambda c: (c.dmg, c.bonus))
        alts, _p, _t, per_counter = g.equip
        cut = pick.bonus if per_counter else 0
        cost = tuple(sorted({(max(0, gen - cut), cols) for gen, cols in alts}))
        if not _pay_ability(me, cost, "free"):
            continue
        if host is not None:
            host.gear.remove(g)
        pick.gear.append(g)
        e["events"].append(f"{me.name}: {g.name} an {pick.card.name}")


def combat_draw_abilities(me, opp, step, e):
    """Lyra, Tolarian Archangel: Faehigkeit "zieht bei Kampfschaden" vor dem Angriff mit freiem Mana, wenn sie
    angreifen kann und kein Blocker des Gegners sie aufhalten kann."""
    for c in me.creatures:
        if not c.card.combat_draw_ability or c.tdraw or not can_attack(c, step):
            continue
        if any(can_block(b, c) for b in opp.creatures):
            continue
        alts, n = c.card.combat_draw_ability
        if _pay_ability(me, alts, "free"):
            c.tdraw += n
            e["events"].append(f"{me.name}: Fähigkeit von {c.card.name} (zieht {n} bei Kampfschaden)")


def _debuff_card(card):
    """(Karte, Modus mit -N/-0) fuer Instants wie Icy Reception, sonst None."""
    if not card.is_instant:
        return None
    if card.debuff:
        return card
    if card.choices:
        return next((sub for sub in card.choices[1] if sub.debuff), None)
    return None


def debuff_tricks(p, pairs, opp, e, step, attacking):
    """-N/-0 bis Rundenende als Kampftrick nach den Blocks. Als Verteidiger auf einen Angreifer: zuerst, wenn dadurch
    ein eigener Blocker ueberlebt, dann gegen Lethal, dann gegen einen ungeblockten Angreifer, wenn mindestens 4
    Schaden weniger durchkommen. Als Angreifer auf einen Blocker, wenn dadurch unser Angreifer ueberlebt."""
    for card in sorted([c for c in p.hand if _debuff_card(c)], key=lambda c: c.mv):
        if card not in p.hand or not _payable(p, _alts(p, card)):
            continue
        n = _debuff_card(card).debuff
        target = None
        if attacking:
            for a, bs in pairs:
                if a.dead or a not in p.creatures or not outcome(a, bs)[0]:
                    continue
                for b in bs:
                    if b.dead or not ward_ok(p, b):
                        continue
                    b.pump -= n
                    saved = not outcome(a, bs)[0]
                    b.pump += n
                    if saved:
                        target = b
                        break
                if target is not None:
                    break
        else:
            live = [(a, bs) for a, bs in pairs if not a.dead and a in opp.creatures and ward_ok(p, a)]
            for a, bs in live:  # eigener Blocker ueberlebt
                if not bs:
                    continue
                before = outcome(a, bs)[1]
                a.pump -= n
                after = outcome(a, bs)[1]
                a.pump += n
                if any(d and not d2 for d, d2 in zip(before, after)):
                    target = a
                    break
            unblocked = [a for a, bs in live if not bs]
            if target is None and unblocked:
                big = max(unblocked, key=lambda a: a.dmg)
                through = sum(a.dmg for a, bs in pairs if not bs and not a.dead and not a.at_jace)
                saved = min(max(0, big.dmg), n)
                if (through >= p.life > through - saved) or saved >= 4:
                    target = big
        if target is None or not _pay_open(p, _alts(p, card)):
            continue
        p.hand.remove(card)
        p.graveyard.append(card)
        on_cast(p, card, step, e)
        if try_counter(p, card, step, e):
            continue
        pay_ward(p, target, e)
        target.pump -= n
        e["events"].append(f"{p.name}: {card.name} – {target.card.name} −{n}/−0")


def combat_buffs(me, step, e):
    """Zu Beginn des eigenen Kampfs: eine andere eigene Kreatur (der staerkste Angreifer) bekommt +N/+N bis
    Rundenende, nach einem Surveil in diesem Zug stattdessen N +1/+1-Marken (Desperate Futurescribe)."""
    for c in list(me.creatures):
        if c.dead or not c.card.combat_buff:
            continue
        others = [x for x in me.creatures if x is not c and not x.dead]
        if not others:
            continue
        pick = max(others, key=lambda x: (can_attack(x, step), danger(x)))
        n = c.card.combat_buff
        if me.surveilled:
            pick.bonus += n
            e["events"].append(f"{me.name}: {c.card.name} – Marke auf {pick.card.name}")
        else:
            pick.pump += n
            pick.tpump += n
            e["events"].append(f"{me.name}: {c.card.name} – {pick.card.name} +{n}/+{n}")


def expire_impulse(p):
    """Ende des eigenen Zugs: Karten im Exil, deren Frist ("until the end of your next turn") abgelaufen ist, bleiben
    dort und sind nicht mehr spielbar."""
    p.impulse = [(c, last) for c, last in p.impulse if last > p.own_turns]


def _take_impulse(p, card):
    for i, (c, _last) in enumerate(p.impulse):
        if c == card:
            del p.impulse[i]
            return


def etb_value(card):
    """Bringt das Betreten der Karte etwas (fuer eine Kopie durch Splinter Twin)? Wie im Goldfish."""
    return enter_value(card)


def etb_face(card, p):
    """Schaden am Gegner durch das Betreten (fuer Lethal)."""
    face = sum(a[1] for m in card.modes[:1] for a in m if a[0] == "face")
    spec = card.removal
    if spec and spec[4] == "etb" and spec[0] == "damage" and spec[3]:
        face = max(face, _amount(spec, p))
    return face


def twin_host(p, opp):
    """Kreatur fuer Splinter Twin: mit Betreten-Effekt (hoechster Removal-Score, dann Manawert), sonst die
    gefaehrlichste nicht legendaere; legendaere nur, wenn ihr Betreten-Effekt Lethal bringt (Legend-Regel 704.5j)."""
    alive = [c for c in p.creatures if not c.dead and not c.card.is_token and not c.exile_step]
    life = opp.life if opp is not None else 99
    useful = [c for c in alive if etb_value(c.card) and (not c.card.legendary or etb_face(c.card, p) >= life)]
    if useful:
        return max(useful, key=lambda c: (c.card.removal_points, c.card.mv))
    plain = [c for c in alive if not c.card.legendary]
    return max(plain, key=danger) if plain else None


def attach_twin(p, opp, card, e):
    host = twin_host(p, opp)
    if host is None:  # keine passende Kreatur: die Aura geht in den Friedhof (704.5m)
        p.perms.remove(card)
        p.graveyard.append(card)
        return
    host.auras.append(card)
    e["events"].append(f"{p.name}: {card.name} auf {host.card.name}")


def _twin_token(p, host, step, end_step):
    """Kopie mit Haste (707.2: nur aufgedruckte Werte); Exil im naechsten Endsegment (im Endsegment aktiviert: erst
    im Endsegment des naechsten Zugs, 513.2)."""
    token = Creature(host.card._replace(is_token=True, haste=True), step)
    token.gy, token.ctl = p.graveyard, p
    token.exile_step = step + 1 if end_step else step
    return token


def twin_activate(p, opp, step, e, end_step=True, hosts=None):
    """{T}: Kopie von jeder verzauberten Kreatur, die tappen darf (302.6)."""
    for host in list(hosts if hosts is not None else p.creatures):
        if host.dead or not any(a.twin for a in host.auras) or not tap_ready(p, host):
            continue
        host.tapped = True
        token = _twin_token(p, host, step, end_step)
        p.creatures.append(token)
        e["events"].append(f"{p.name}: Splinter Twin – Kopie von {host.card.name}")
        creature_enters(p, token, step, e, opp, cast=False)
        bury((p, opp), e)


def twin_for_lethal(me, opp, step, e):
    """Im eigenen Zug nur, wenn die Kopie (Betreten-Effekt plus Angriff mit Haste) Lethal bringt."""
    base = _attack_value(me, opp, step)
    for host in list(me.creatures):
        if host.dead or not any(a.twin for a in host.auras) or not tap_ready(me, host):
            continue
        token = _twin_token(me, host, step, False)
        host.tapped = True
        me.creatures.append(token)
        value = _attack_value(me, opp, step) + etb_face(host.card, me)
        me.creatures.remove(token)
        host.tapped = False
        if value >= opp.life > base:
            twin_activate(me, opp, step, e, end_step=False, hosts=[host])
            return


def gy_exile_target(victim):
    """Karte aus dem Friedhof des Gegners zum Exilieren: zuerst eine, die sich selbst nutzt (zurueckholen, Phoenix,
    Flashback, Faehigkeit aus dem Friedhof), sonst seine teuerste Kreatur, sonst keine."""
    own = [c for c in victim.graveyard if c.gy_return or c.phoenix or c.flashback or c.gy_ability]
    if own:
        return max(own, key=lambda c: (c.mv, c.name))
    creatures = [c for c in victim.graveyard if c.is_creature]
    return max(creatures, key=lambda c: (c.mv, c.name)) if creatures else None


def take_turn(me, opp, step, rnd, skip_draw):
    """Ein Zug von me. Gibt den Protokolleintrag zurueck."""
    e = {"player": me.name, "round": rnd, "drew": None, "land": None, "main1": [], "main2": [], "attacks": [],
         "damage": 0, "face": 0, "deaths": [], "events": [], "note": ""}
    me.cast_count = 0
    me.noncreature_cast = opp.noncreature_cast = False
    me.ward_budget, me.ward_pool = 0, None
    me.extra_lands = 0
    me.turn_start = step
    me.own_turns += 1
    me.drawn_mark, opp.drawn_mark = me.drawn, opp.drawn
    for p_ in (me, opp):
        p_.direct_mark, p_.deaths_mark = p_.dealt_direct, p_.deaths
    me.opponent, opp.opponent = opp, me
    me.now = opp.now = step
    for c in me.creatures:  # Untap (gesperrte Kreaturen bleiben gesperrt; Stun-Marke statt Enttappen, 122.1g)
        if c.stun and c.tapped:
            c.stun -= 1
            continue
        c.tapped = False
    upkeep(me)
    if not skip_draw:  # Draw
        if not me.library:
            me.lost = True
            e["note"] = "muss aus leerer Bibliothek ziehen"
            return e
        card = me.library.pop(0)
        me.hand.append(card)
        me.drawn += 1
        e["drew"] = card.name
    jace_turn_start(me, step, e)
    disc, orig = discount(me), {}  # Kostensenkung, Steuer, Zusatzkosten: angepasste Handkarten fuer die Main Phase
    for i, c in enumerate(me.hand):
        cheap = _discounted(c, disc, me)
        if cheap != c:
            orig[cheap] = c
            me.hand[i] = cheap
    ex_map = {}  # ab Threshold: exilierte Karten (Null Summoner) mit Mana jeder Art, voruebergehend auf der Hand
    if me.exiled and threshold(me):
        for c in me.exiled:
            if not c.is_instant and not c.flash and not c.is_land:
                cheap = _discounted(_any_mana(c), disc, me)
                ex_map[cheap] = c
                me.hand.append(cheap)

    im_map = {}  # Exil spielbar (Blazing Crescendo): voruebergehend auf der Hand, markiert
    for c, _last in me.impulse:
        mark = _discounted(c._replace(impulse_mark=True), disc, me)
        im_map[mark] = c
        me.hand.append(mark)

    fb_map = {}  # Flashback: Sorceries aus dem Friedhof mit Flashback-Kosten, voruebergehend auf der Hand
    for c in me.graveyard:
        if c.flashback and not c.is_instant and not c.flashback_discard:
            cheap = _flashback_version(me, c)
            fb_map[cheap] = c
            me.hand.append(cheap)

    def cost(c):  # Prepared-Kopien mit Kostensenkung bzw. Steuer (Handkarten sind schon angepasst)
        if c.is_copy:
            cheap = _discounted(c, disc, me)
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
        if land in im_map:  # Land aus dem Exil (Blazing Crescendo)
            _take_impulse(me, im_map[land])
            land = im_map[land]
        me.lands.append(land)
        e["land"] = land.name + (" (getappt)" if tapped else "")
        if not tapped:
            pool_all = pool_all + [land.land_colors]
        pool_all = pool_all + on_land(me, opp, land, step, e)
    while me.extra_lands > 0 and any(c.is_land for c in me.hand):  # Way of the Paradox: weiterer Landdrop
        me.extra_lands -= 1
        land2, tapped2, _f = choose_land(me.hand, spells, pool_all, me.lands, *walker_flags(me), has_creature, True)
        if land2 is None:
            break
        me.hand.remove(land2)
        me.lands.append(land2)
        e["land"] = (e["land"] + ", " if e["land"] else "") + land2.name
        if not tapped2:
            pool_all = pool_all + [land2.land_colors]
        pool_all = pool_all + on_land(me, opp, land2, step, e)
    if walker_engine(me) and not me.jace.used:  # L2a: zeitkritische Loyalty-Faehigkeiten vor dem Zaubern
        mana = walker_phase(me, opp, step, e, "main1", pool_all, spells)
        if mana:
            pool_all = pool_all + mana
            spells = phase_spells()
        if opp.life <= 0:
            return e
    ward_of = {}  # Ward-Kosten wie Zusatzkosten einplanen (702.21)
    me.ward_pool = pool_all
    for i, c in enumerate(me.hand):
        n = ward_plan(me, opp, c, pool_all)
        if n:
            dear = c._replace(alts=tuple(sorted({(g + n, cols) for g, cols in c.alts})))
            orig[dear] = orig.get(c, c)
            me.hand[i] = dear
            ward_of[dear] = n
    spells = phase_spells()
    # Mana fuer Removal im Zug des Gegners freihalten, wenn er jetzt ein passendes Ziel hat (Variante B)
    held, kept = held_removal(me, opp, orig) if forced is None else None, []
    if held is not None:
        left = pay(pool_all, held[1])
        if left is not None:
            kept = list(pool_all)
            for u in left:
                kept.remove(u)
            pool_all = left
            if held[0] in spells:
                spells.remove(held[0])
            e["events"].append(f"{me.name}: hält {len(kept)} Mana für {held[0].name} offen")
    hc = held_counter(me, orig) if rnd >= 5 and forced is None else None  # Counterspell ab Runde 5 freihalten
    if hc is not None:
        left = pay(pool_all, hc[1])
        if left is None and kept:  # beides geht nicht: nur der Counterspell
            pool_all = pool_all + kept
            kept = []
            e["events"] = [ev for ev in e["events"] if not ev.startswith(f"{me.name}: hält ")]
            if held is not None and held[0] in me.hand and held[0] not in spells and not held[0].is_instant:
                spells.append(held[0])
            left = pay(pool_all, hc[1])
        if left is not None:
            used = list(pool_all)
            for u in left:
                used.remove(u)
            kept += used
            pool_all = left
            e["events"].append(f"{me.name}: hält {len(used)} Mana für {hc[0].name} offen")
    me.ward_pool = None
    _score_, chosen = best_cast_reduced(spells, land_key(pool_all), has_creature, True, must=forced)
    if treasure_count(me) and forced is None:  # Treasure nur, wenn er diese Runde mehr ermoeglicht
        k_t, _ch = use_treasures(spells, pool_all, treasure_count(me), has_creature, True)
        if k_t:
            _spend_treasures(me, k_t, remove=False)
            pool_all = pool_all + [ANY_COLOR] * k_t
            e["events"].append(f"{me.name}: {k_t} Treasure geopfert")
            _score_, chosen = best_cast_reduced(spells, land_key(pool_all), has_creature, True)
    if any(c.draws for c in chosen) or enters_prepared(chosen) or any(usable_now(c) for c in chosen):
        walker_bf, jace_bf = walker_flags(me)
        rd = resolve_draws(me.hand, me.library, chosen, pool_all, me.lands, land, has_creature, True, walker_bf,
                           jace_bf, copies=[cost(c) for c in copies(me)])
        me.drawn += rd["drawn"]
        chosen = [c for c in rd["chosen"] if not c.is_instant and not c.flash and c is not (held or (None,))[0]]
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
    pool_all = pool_all + kept  # das freigehaltene Mana bleibt offen
    rest = list(pool_all)  # offenes Mana nach dem Bezahlen (Kreaturen-Mana zaehlt nicht dazu)
    for c in chosen:
        paid = pay(rest, c.alts)  # [] heisst: alles ausgegeben (nicht mit None verwechseln)
        rest = paid if paid is not None else rest
    for u, _i in creature_units:
        if u in rest:
            rest.remove(u)
    me.open = rest
    me.ward_budget = sum(ward_of.get(c, 0) for c in chosen if ward_of.get(c, 0) < 99)
    chosen = [c if c.is_copy else hand_form(c, me.hand) if c not in me.hand else c for c in chosen]
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
    if im_map:  # gewirkte Karten aus dem Exil verlassen es, die anderen bleiben dort
        for c in chosen:
            if c in im_map:
                _take_impulse(me, im_map[c])
        me.hand[:] = [c for c in me.hand if c not in im_map]
        chosen = [im_map.get(c, c) for c in chosen]
    owner_of = me.exiled_from or opp
    if any(c.is_creature and not c.is_token and not c.is_copy for c in chosen):  # Arni, Humble Scribe enttappt dann
        for c in list(me.creatures):
            if c.card.ally_untap:
                for ab in c.card.draw_abilities:
                    use_draw_ability(me, c, ab, e)
    from_graveyard = Counter()  # per Flashback gewirkt: danach ins Exil
    if fb_map:
        for c in chosen:
            if c in fb_map:
                me.graveyard.remove(fb_map[c])
                from_graveyard[fb_map[c]] += 1
        me.hand[:] = [c for c in me.hand if c not in fb_map]
        chosen = [fb_map.get(c, c) for c in chosen]

    me.predrawn = Counter(c for c in chosen if c.draws)  # resolve_draws hat sie schon gezogen

    def resolve(c):
        owner, exile = None, False
        if from_exile[c]:
            from_exile[c] -= 1
            owner = owner_of
        elif from_graveyard[c]:
            from_graveyard[c] -= 1
            exile = True
        _resolve(me, opp, c, step, e, owner, exile)
    me.cast_count += len(chosen)
    for c in chosen:  # X-Kosten (Fblthp): freies Mana, hoechstens so viel, wie es nutzt
        if c.x_search_basics:
            x = min(free_units(me), len(basic_names_in_library(me)))
            for _ in range(x):
                me.open.pop()
            me.next_x = x
    early = [c for c in chosen if c.is_creature and not c.haste and combat_etb(me, opp, c, step, chosen)]
    main1 = [c for c in chosen if not (c.is_creature and not c.haste) or c in early]
    main2 = [c for c in chosen if c.is_creature and not c.haste and c not in early]
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
        if card not in _zone(me, zone) or not _payable(me, alts):
            continue
        eaters = [t for t in valid_targets(rc.removal, me, opp) if any(_eats(t, a) for a in candidates)]
        if eaters:
            me.cast_count += 1 if is_spell else 0
            if _use_removal(me, card, alts, is_spell, step, e, zone, opp, rc, target=max(eaters, key=danger)):
                cast_removal(rc, me, opp, e, step, target=max(eaters, key=danger))
    # Jace surveilt schon vor dem Kampf, wenn das in diesem Kampf etwas bringt (Prudent Fateseer, Futurescribe)
    alive = [c for c in me.creatures if not c.dead]
    if 0 < me.jace.loyalty < 3 and not me.surveilled and not walker_engine(me) and any(
            c.card.surveil_team_pump or c.card.combat_buff for c in alive):
        _jace_activate(me, step, e, True)
    stun_from_graveyard(me, opp, step, e)
    equip_gear(me, step, e)
    # Faehigkeiten vor dem Angriff: Marken und Empower mit freiem Mana, Flying/Menace fuer den Angriff
    pre_attack_abilities(me, opp, step, e)
    combat_draw_abilities(me, opp, step, e)
    # Kampf: zu Beginn Darklight Phoenix und Desperate Futurescribe
    phoenix_check(me, opp, step, e)
    combat_buffs(me, step, e)
    twin_for_lethal(me, opp, step, e)
    sacrifice_for_lethal(me, opp, step, e)
    attackers = choose_attackers(me.creatures, opp.creatures, opp.life, me.life, step)
    art_vigilance = any(c.card.artifact_vigilance for c in me.creatures if not c.dead)
    for a in attackers:
        if not (a.has("vigilance") or (art_vigilance and a.card.is_artifact)):
            a.tapped = True
        for ef in recurring_effects(a.card):  # Angriffs-Ausloeser (Empower)
            if ef[1] == "trigger" and ef[3] == "attack" and any(pc == a.card for pc, _t in me.jace_perms):
                n = sum(1 for c in me.creatures if not c.dead) if ef[7] else ef[2]  # X = eigene Kreaturen
                _jace_add(me, n, e)
    for a in choose_jace_attackers(attackers, opp, [b for b in opp.creatures if not b.tapped and not b.dead]):
        a.at_jace = True
    if attackers and me.jace.used and any(c.card.kiora_attack and not c.dead for c in me.creatures):
        pick = max(attackers, key=danger)  # Kiora: enttappt und unblockbar
        pick.tapped = False
        pick.extra.add("unblockable")
        e["events"].append(f"{me.name}: Kiora – {pick.card.name} enttappt und unblockbar")
    for a in attackers:  # Angriffs-Ausloeser der Kreatur selbst
        if a.card.attack_drain:  # Screeching Soulbreaker
            dmg, life = a.card.attack_drain
            deal_noncombat(me, opp, dmg, e)
            gain_life(me, life)
            e["events"].append(f"{me.name}: {a.card.name} – {dmg} Schaden, {life} Leben")
        if a.card.attack_exile_gy:  # Afterthought Sentry
            pick = gy_exile_target(opp)
            if pick is not None:
                opp.graveyard.remove(pick)
                e["events"].append(f"{me.name}: {a.card.name} exiliert {pick.name} aus dem Friedhof von {opp.name}")
    ping = sum(c.card.attack_ping for c in me.creatures if not c.dead) * len(attackers)
    if ping:  # "Whenever a creature you control attacks, that creature deals 1 damage to each opponent"
        for a in attackers:  # je Angreifer ein Schadensereignis
            for _ in range(sum(c.card.attack_ping for c in me.creatures if not c.dead)):
                deal_noncombat(me, opp, 1, e)
        e["events"].append(f"{me.name}: {ping} Schaden durch Angriffs-Auslöser")
    attackers = respond_to_attack(opp, me, attackers, e, step)
    pre_block_abilities(opp, me, attackers, e, step)
    blocks = choose_blocks(attackers, opp.creatures, opp.life)
    combat_abilities(me, blocks, opp, e, step, attacking=True)
    combat_abilities(opp, blocks, me, e, step, attacking=False)
    n_events = len(e["events"])
    combat_tricks(me, blocks, opp, e, step, attacking=True)
    me.cast_count += len(e["events"]) - n_events
    combat_tricks(opp, blocks, me, e, step, attacking=False)
    debuff_tricks(me, blocks, opp, e, step, attacking=True)
    debuff_tricks(opp, blocks, me, e, step, attacking=False)
    sacrifice_blockers(opp, blocks, e)
    before = [(a.label(), [b.label() for b in bs]) for a, bs in blocks]
    res = resolve_combat(blocks)
    if res["jace"]:
        alive_before = opp.jace.loyalty > 0
        opp.jace.loyalty = max(0, opp.jace.loyalty - res["jace"])
        e["events"].append(f"{me.name}: {res['jace']} Schaden an Jace von {opp.name} (Loyalty {opp.jace.loyalty})")
        if alive_before and opp.jace.loyalty == 0:
            _jace_zero(opp, 1, e)
    opp.life -= res["player"]
    me.dealt_combat += res["player"]
    combat_life(me, opp, res)
    e["damage"] = res["player"]
    for a, _bs in blocks:  # "deals combat damage to a player, draw ..." (Frostbite Pyromental)
        if (a.card.combat_draw or a.tdraw) and res["to_player"].get(id(a)):
            _draw(me, a.card.combat_draw + a.tdraw)
            e["events"].append(f"{me.name}: {a.card.name} zieht {a.card.combat_draw + a.tdraw}")
        if a.card.combat_land_return and res["to_player"].get(id(a)):  # Carnivorous Cultivator
            lands = gy_candidates(me, "land")
            if lands:
                pick = _best_from_gy(me, lands)
                me.graveyard.remove(pick)
                put_back(me, pick, "hand", step, e)
    e["attacks"] = [{"attacker": lab, "blockers": blabs, "attacker_dies": a.dead, "blockers_die": [b.dead for b in bs],
                     "jace": a.at_jace} for (lab, blabs), (a, bs) in zip(before, blocks)]
    bury((me, opp), e)
    if opp.life <= 0:
        return e
    # Main 2
    for c in main2:
        resolve(c)
    e["main2"] = [c.name for c in main2]
    lasting_abilities(me, opp, step, e, own_turn=True, mode="free")  # z. B. Grim Repriser nach dem Angriffs-Schaden
    if walker_engine(me):
        walker_phase(me, opp, step, e, "after")
    else:
        _jace_activate(me, step, e, True)
    me.predrawn = Counter()
    # End Phase: Edgar ("if you didn't cast a spell this turn"), danach Instants und Flash des Gegners
    if not me.cast_count:
        for c in me.creatures:
            if c.card.endstep_counters:
                c.bonus += c.card.endstep_counters
    confidant_end_step(me, e)
    for p_ in (me, opp):  # Lyra, Tolarian Archangel: 3 oder mehr Karten in diesem Zug gezogen
        if p_.drawn - p_.drawn_mark >= 3:
            for c in list(p_.creatures):
                if c.card.draw3_token is not None and not c.dead:
                    make_tokens(p_, [(1, c.card.draw3_token)], step, e, p_.opponent, c.card.name)
    if any(c.card.end_untap_tokens and not c.dead for c in me.creatures):  # Jiang Yanggu, Never Alone
        for c in me.creatures:
            if c.card.is_token:
                c.tapped = False
    for p_ in (me, opp):  # Splinter Twin: Kopien zu Beginn des Endsegments exilieren (kein Sterben)
        for c in list(p_.creatures):
            if c.exile_step is not None and c.exile_step <= step:
                p_.creatures.remove(c)
                e["events"].append(f"{p_.name}: Kopie von {c.card.name} exiliert")
    for p_ in (me, opp):  # "At the beginning of the end step, sacrifice this creature"
        for c in p_.creatures:
            if c.card.end_sacrifice:
                c.dead = True
                e["events"].append(f"{p_.name}: opfert {c.card.name}")
    bury((me, opp), e)
    end_step_instants(opp, me, e, step)
    hand_limit(me, e)
    expire_impulse(me)
    cleanup((me, opp))
    return e


def hand_limit(p, e, size=7):
    """514.1: am Ende des eigenen Zugs auf die Handgroesse abwerfen (Auswahl wie beim Abwerfen)."""
    over = len(p.hand) > size
    while len(p.hand) > size:
        card = choose_discard(p)
        p.hand.remove(card)
        p.graveyard.append(card)
        e["events"].append(f"{p.name}: Handlimit – wirft {card.name} ab")
    if over:
        discarded(p, e)


def cleanup(players):
    """Rundenende: Schaden, Pumps und verliehene Schluesselwoerter verfallen."""
    for p in players:
        for c in p.creatures:
            c.damage, c.pump, c.tpump, c.touched, c.lifted, c.at_jace = 0, 0, 0, False, False, False
            c.extra = set()
            c.tdraw = 0
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
