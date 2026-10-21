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
from components.cards import HEARTWOOD, Card, token_card
from components.conjure import conjure
from components.simulation import (ANY_COLOR, apply_effects, apply_surveils, best_cast_reduced, choose_land,
                                   cost_reduction, do_cycle, enter_value, enters_prepared, free_spells, hand_form,
                                   omni_ok,
                                   landfall_effects, pay_subsets,
                                   plan_cycle, reduced, resolve_draws, tapped_for_mana, usable_now, use_treasures)
from components.landadvice import colors_of_alts

LIFE = 20
LOTUS = token_card("Lotus")  # Kwia Vigorbloom: {T}, Sacrifice: drei Mana einer Farbe
DRAGON = token_card("Dragon", True, 5, 5, False, kw=("flying",), types=("dragon",))  # Draconic Visitor
CYCLE_TURNS = 3  # eigener Zug: fehlt bis Runde 3 ein Land fuer den Landdrop, wird sofort gecycelt
CYCLE_CAP = 6    # Ende des gegnerischen Zugs: nur cyceln, solange Laender auf Feld und Hand unter 6 liegen


BASIC_TYPES = {"plains", "island", "swamp", "mountain", "forest"}
_GY_TYPES = {"creature": "is_creature", "planeswalker": "is_planeswalker", "artifact": "is_artifact",
             "land": "is_land", "instant": "is_instant", "sorcery": "is_instant_sorcery"}


class Creature:
    """Eine Kreatur auf dem Feld (Karte, Schritt des Eintritts, getappt, Schaden, Marken, Pump)."""
    __slots__ = ("card", "entered", "tapped", "_damage", "_bonus", "pump", "land_source", "attacked", "ramp_pending",
                 "base_card", "dead", "touched", "locked", "prepared",
                 "tpump", "extra", "lifted", "owner", "at_jace", "gy", "dealt", "finality", "ctl", "once", "stun", "gear",
                 "tdraw", "auras", "exile_step", "at_pw", "lasting", "crew")

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
        self.land_source = None  # Hall of Echoes: das Land, das bis Rundenende diese Kopie ist
        self.attacked = None  # Schritt, in dem sie zuletzt angegriffen hat (Hexhaven Dueling Arena)
        self.ramp_pending = 0  # Hexhaven Invigorator: erhaltener Schaden, fuer den noch Laender gesucht werden
        self.base_card = None  # Puppet Crafting: die Artefakt-Karte hinter der belebten Kreatur
        self.at_pw = None     # greift in diesem Kampf diesen echten Planeswalker (Walker) an
        self.lasting = []     # -P/-T bis zum naechsten Zug des Verursachers: (P, T, Verursacher, Schritt)
        self.crew = []        # gecrewtes Fahrzeug: die Kreaturen, die dafuer getappt wurden

    @property
    def damage(self):
        """Markierter Schaden."""
        return self._damage

    @damage.setter
    def damage(self, value):
        """Hexhaven Invigorator: erhaltener Schaden wird gemerkt, bury sucht dafuer Laender."""
        old = getattr(self, "_damage", 0)
        if value > old and self.card.damage_ramp:
            self.ramp_pending = getattr(self, "ramp_pending", 0) + value - old
        self._damage = value

    @property
    def bonus(self):
        """+1/+1-Marken."""
        return self._bonus

    @bonus.setter
    def bonus(self, value):
        """Yoshimaru, Beloved Companion (614.1, auch "enters with", 122.6): kommen Marken auf eine eigene Kreatur,
        kommt eine mehr dazu."""
        old = getattr(self, "_bonus", 0)
        ctl = getattr(self, "ctl", None)
        if value > old and ctl is not None and any(c.card.counter_plus_one and not c.dead for c in ctl.creatures):
            value += 1
        self._bonus = value

    @property
    def power(self):
        base = self.card.power + self.bonus + self.pump
        if self.card.gy_power and self.gy is not None:
            base += sum(1 for g in self.gy if any(getattr(g, _GY_TYPES[t], False) for t in self.card.gy_power))
        if self.card.domain_power and self.ctl is not None:
            base += len({t for land in self.ctl.lands for t in land.land_types} & BASIC_TYPES)
        base += self._threshold() + sum(g.equip[1] for g in self.gear) + self._emblem(1) \
            - sum(d[0] for d in self.lasting) + self._gy_power() + self._token_bonus() + self._goyf() \
            + sum(a.aura_pump[0] for a in self.auras if a.aura_pump)
        p = self.ctl
        if p is not None and (self.card.cond_static or (p.statics or _statics(p))[0]):  # selten: nur dann rechnen
            base += sum(s[2] for s in self._cond())
        if self.card.lib_creature_minus and p is not None:  # Avoided Stairwurm
            base -= sum(1 for c in p.library if c.is_creature)
        return base

    @property
    def toughness(self):
        out = self.card.toughness + self.bonus + self.tpump + self._threshold() + sum(g.equip[2] for g in self.gear) \
            + self._emblem(2) - sum(d[1] for d in self.lasting) + (self._goyf() + 1 if self.card.goyf else 0) \
            + sum(a.aura_pump[1] for a in self.auras if a.aura_pump)
        p = self.ctl
        if p is not None and (self.card.cond_static or (p.statics or _statics(p))[0]):
            out += sum(s[3] for s in self._cond())
        if self.card.lib_creature_minus and p is not None:
            out -= sum(1 for c in p.library if c.is_creature)
        return out

    def _cond(self):
        """Bedingte statische Faehigkeiten, die gerade fuer diese Kreatur gelten: eigene ("self") und von eigenen
        Kreaturen und Permanents ("team", Thornfist Striker), z. B. Infusion oder "as long as you control another
        Goblin"."""
        p = getattr(self, "ctl", None)
        if p is None:
            return ()
        own = self.card.cond_static
        team = (p.statics or _statics(p))[0]
        if not own and not team:
            return ()
        out = [s for s in own if s[1] == "self" and _cond_met(p, s[0], self)]
        for src, card in team:
            if src is None or not src.dead:
                out += [s for s in card.cond_static if (s[1] == "team" or (s[1] == "others" and src is not self))
                        and _cond_met(p, s[0], src)]
        return out

    def _gy_power(self):
        """Threshold +N/+0 (Theorix Metamage) und +N/+0 je volle 7 Karten im Friedhof (Dark Matter Manipulator)."""
        if self.ctl is None:
            return 0
        n = len(self.ctl.graveyard)
        out = self.card.threshold_power if n >= 7 else 0
        if self.card.gy_step_power:
            step, k = self.card.gy_step_power
            out += (n // step) * k
        return out

    def _goyf(self):
        """Tarmogoyf: Kartentypen unter den Karten in allen Friedhoefen (Toughness eins mehr)."""
        if not self.card.goyf or self.ctl is None:
            return 0
        cards = list(self.ctl.graveyard) + (list(self.ctl.opponent.graveyard) if self.ctl.opponent is not None else [])
        types = set()
        for c in cards:
            types |= {t for t, flag in (("artifact", c.is_artifact), ("creature", c.is_creature),
                                         ("enchantment", c.is_enchantment), ("instant", c.is_instant),
                                         ("sorcery", c.is_instant_sorcery and not c.is_instant),
                                         ("land", c.is_land), ("planeswalker", c.is_planeswalker)) if flag}
        return len(types)

    def _token_bonus(self):
        """Gideon's Memorial: eigene Kreatur-Token +N/+0."""
        if not self.card.is_token or self.ctl is None:
            return 0
        return sum(c.token_pump for c in self.ctl.perms) + sum(c.card.token_pump for c in self.ctl.creatures
                                                             if not c.dead)

    def _emblem(self, i):
        """Emblem "Creatures you control get +N/+N" (Ajani Resolute, 114.4)."""
        if self.ctl is None:
            return 0
        return sum(em[i] for em in self.ctl.emblems if em[0] == "team")

    @property
    def dmg(self):
        """Kampfschaden, den die Kreatur zuweist (510.1a): Power, mit Ghalta the Immovable beim Kontrolleur die
        Toughness, wenn sie groesser ist."""
        power, tough = self.power, self.toughness
        if power < 0 and self.card.abs_damage:  # Loot, the Anomaly
            power = -power
        if tough > power and self.ctl is not None and any(c.card.toughness_damage and not c.dead
                                                          for c in self.ctl.creatures):
            power = tough
        if power > 0 and self.ctl is not None and red_bonus(self.ctl, self.card):  # Searing Soloist
            power += 1
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
        if any(keyword in g.equip_kw for g in self.gear):  # Medic's Kitesail
            return True
        if any(keyword in a.aura_kw for a in self.auras):  # eigene Aura (Ferocity of the Hunt)
            return True
        if keyword in card.threshold_kw and len(p.graveyard) >= 7:  # Theorix Metamage
            return True
        if keyword == "vigilance" and card.jace_vigilance and (  # Mind Meanderer
                jace_present(p) or any(w.card.is_jace for w in p.walkers)):
            return True
        if card.is_token and (any(keyword in c.token_kw for c in p.perms)  # Gideon's Memorial
                              or any(keyword in c.card.token_kw for c in p.creatures if not c.dead)):
            return True
        if keyword in card.noncombat_kw and p.dealt_direct > p.direct_mark:
            return True
        st = p.statics or _statics(p)
        if (card.cond_static or st[0]) and any(keyword in s[4] for s in self._cond()):  # Bolg's Company, Thornfist
            return True
        if self.bonus > 0 and st[1] and any(keyword in kws for src, kws in st[1]
                                            if src is None or not src.dead):  # Training Regimen
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
        c.at_pw, c.lasting = self.at_pw, list(self.lasting)
        c.land_source, c.attacked, c.base_card = self.land_source, self.attacked, self.base_card
        return c

    def label(self):
        return f"{self.card.name} ({self.power}/{self.toughness})"


class TrackedList(list):
    """Liste, die bei jeder Aenderung den Zwischenspeicher ihres Spielers (Player.statics) loescht."""
    __slots__ = ("owner",)

    def __init__(self, items=(), owner=None):
        super().__init__(items)
        self.owner = owner


def _tracked(name):
    base = getattr(list, name)

    def method(self, *args):
        if self.owner is not None:
            self.owner.statics = None
        return base(self, *args)
    method.__name__ = name
    return method


for _name in ("append", "extend", "insert", "remove", "pop", "clear", "sort", "reverse", "__setitem__",
              "__delitem__", "__iadd__", "__imul__"):
    setattr(TrackedList, _name, _tracked(_name))


def _statics(p):
    """Zwischengespeichert in p.statics, bis sich Kreaturen oder Permanents aendern (TrackedList): (Quellen mit
    Team-Statik [(Kreatur oder None, Karte)], Quellen mit Schluesselwoertern fuer Kreaturen mit Marke
    [(Kreatur oder None, kw)])."""
    cards = [(c, c.card) for c in p.creatures] + [(None, x) for x in p.perms if isinstance(x, Card)]
    p.statics = ([(c, card) for c, card in cards if any(st[1] in ("team", "others") for st in card.cond_static)],
                 [(c, card.counter_kw) for c, card in cards if card.counter_kw])
    return p.statics


def red_bonus(p, card):
    """Searing Soloist (614.1a): eine rote Quelle von p macht 1 Schaden mehr."""
    return "R" in colors_of_alts(card.alts) and any(c.card.red_plus_one and not c.dead for c in p.creatures)


def perpetual_pump(c, pw, tw):
    """Perpetuell +P/+T (Alchemy): die Karte selbst aendert sich, auch in Friedhof und Hand."""
    c.card = c.card._replace(power=c.card.power + pw, toughness=c.card.toughness + tw)


def library_to_graveyard(p):
    """Karten kamen aus der Bibliothek in den Friedhof (Mill, Surveil): Zimone wird prepared."""
    for c in p.creatures:
        if not c.dead and c.card.prepared and c.card.prepared[0] == "mill":
            c.prepared = True


def end_step_discards(players, e):
    """Beginn des Endsegments: mit Seek geholte Karten (Killian) werden abgeworfen, wenn sie noch auf der Hand sind."""
    for p in players:
        gone = []
        for card in p.seek_discard:
            if any(h is card for h in p.hand):
                p.hand.remove(card)
                p.graveyard.append(card)
                gone.append(card)
        p.seek_discard = []
        if gone:
            e["events"].append(f"{p.name}: wirft ab (Seek): {', '.join(c.name for c in gone)}")
            discarded(p, e, gone)


def static_sources(p):
    """(Kreatur oder None, Karte) fuer alle lebenden eigenen Kreaturen und Nichtkreatur-Permanents mit Karte."""
    out = [(c, c.card) for c in p.creatures if not c.dead]
    return out + [(None, x) for x in p.perms if isinstance(x, Card)]


def _cond_met(p, cond, src):
    """Bedingung einer bedingten Statik fuer die Quelle src (Kreatur oder None)."""
    kind = cond[0]
    if kind == "gained":  # Infusion: in diesem Zug Leben gewonnen
        return p.gained > 0
    if kind == "always":  # Station-Stufe erreicht (Lumen-Class Frigate)
        return True
    if kind == "another":  # "as long as you control another Goblin"
        return any(c is not src and not c.dead and cond[1] in c.card.creature_types for c in p.creatures)
    if kind == "gy_creatures":
        return sum(1 for c in p.graveyard if c.is_creature) >= cond[1]
    return False


def ward_of(c):
    """Ward der Kreatur (702.21): eigenes oder von Ausruestung/Aura verliehenes ("has ward {N}")."""
    if c.card.ward:
        return c.card.ward
    n = max([g.grant_ward for g in c.gear] + [a.grant_ward for a in c.auras] + [0])
    return ("mana", n) if n else ()


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
           "lifelink_events_attacker": 0, "lifelink_events_defender": 0, "pw": {}}
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
                if not c.dead and (c.damage >= c.toughness or (c.touched and c.damage > 0)) \
                        and not c.has("indestructible"):  # 702.12b
                    c.dead = True
    return out


def _hit_player(out, att, amount):
    if att.at_pw is not None:  # 120.3c: Schaden an einem Planeswalker nimmt Loyalty
        slot = out["pw"].setdefault(id(att.at_pw), [att.at_pw, 0])
        slot[1] += amount
    elif att.at_jace:
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
    if tomik(defender):  # hoechstens ein Angreifer: der schwaechste, der reicht, sonst keiner
        single = [a for a in attackers if max_through([a], blockers) >= need]
        return [min(single, key=lambda a: (a.dmg, a.toughness, a.card.mv))] if single else []
    picked = []
    for a in sorted(attackers, key=lambda a: (a.dmg, a.toughness, a.card.mv)):
        picked.append(a)
        if max_through(picked, blockers) >= need:
            return picked
    return []


def choose_walker_attackers(attackers, defender, blockers):
    """Echte Planeswalker des Verteidigers greifen wir immer an, mit so wenig Schaden wie noetig: je Planeswalker
    (hoechster Manawert zuerst) der kleinste einzelne Angreifer, der ihn sicher toetet, sonst die schwaechsten, bis es
    reicht; toetet ihn nicht einmal alles Uebrige, greift alles Uebrige ihn an. Nicht bei Lethal auf den Spieler.
    Gibt [(Angreifer, Walker)] zurueck."""
    walkers = [w for w in defender.walkers if w.loyalty > 0]
    if not walkers or not attackers or max_through(attackers, blockers) >= defender.life:
        return []
    free, out = list(attackers), []
    for w in sorted(walkers, key=lambda w: (-w.card.mv, -w.loyalty)):
        if not free:
            break
        order = sorted(free, key=lambda a: (a.dmg, a.toughness, a.card.mv))
        single = next((a for a in order if max_through([a], blockers) >= w.loyalty), None)
        if single is not None:
            picked = [single]
        elif tomik(defender):  # Tomik: nur einer, dann der staerkste
            picked = [order[-1]]
        else:
            picked = []
            for a in order:
                picked.append(a)
                if max_through(picked, blockers) >= w.loyalty:
                    break
        for a in picked:
            free.remove(a)
            out.append((a, w))
    return out


def tomik(p):
    """Tomik, Orzhov Lawmage: hoechstens eine Kreatur greift jeden Planeswalker von p an."""
    return any(c.card.tomik_guard and not c.dead for c in p.creatures) or any(c.tomik_guard for c in p.perms)


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

class Walker:
    """Ein echter Planeswalker auf dem Feld: kommt mit seiner aufgedruckten Loyalty (306.5b), eine Loyalty-Faehigkeit
    pro Zug (606.3)."""
    __slots__ = ("card", "entered", "loyalty", "used")

    def __init__(self, card, entered=0):
        self.card = card
        self.entered = entered
        self.loyalty = card.loyalty_start
        self.used = False

    def label(self):
        return f"{self.card.name} (Loyalty {self.loyalty})"


class Graveyard(list):
    """Friedhof eines Spielers: kommt eine Karte wie Paradox Kraken hinein (egal woher), beschwoert sie ihre Karte
    auf die Hand des Besitzers."""
    __slots__ = ("owner",)

    def __init__(self, items=(), owner=None):
        super().__init__(items)
        self.owner = owner

    def _arrived(self, cards):
        if self.owner is None:
            return
        for c in cards:
            if getattr(c, "gy_conjure", ""):
                new = conjure(c.gy_conjure)
                if new is not None:
                    self.owner.hand.append(new)

    def append(self, card):
        super().append(card)
        self._arrived([card])

    def extend(self, cards):
        cards = list(cards)
        super().extend(cards)
        self._arrived(cards)

    def insert(self, i, card):
        super().insert(i, card)
        self._arrived([card])

    def __iadd__(self, cards):
        self.extend(cards)
        return self


def _set_graveyard(self, value):
    self._graveyard = Graveyard(value, self)


def _set_tracked(attr):
    def setter(self, value):
        self.statics = None
        setattr(self, attr, TrackedList(value, self))
    return setter


class Player:
    creatures = property(lambda self: self._creatures, _set_tracked("_creatures"))
    perms = property(lambda self: self._perms, _set_tracked("_perms"))
    statics = None  # Zwischenspeicher fuer _statics
    graveyard = property(lambda self: self._graveyard, _set_graveyard)

    def __init__(self, name, cards, mulligan=True, min_hand=5, never_concede=False):
        self.name = name
        hand, library, mulls, _reasons = deal_opening(cards, mulligan, min_hand, keep_at_min=never_concede)
        self.lost = hand is None
        self.hand, self.library = (hand or []), (library or [])
        self.opening = list(self.hand)
        self.mulls = mulls
        self.lands, self.creatures, self.perms, self.graveyard = [], [], [], []
        self.vehicles = []  # Fahrzeuge: {"card", "since" (Schritt), "crewed" (Creature oder None), "tapped"}
        self.stations = []  # Station-Karten: {"card", "live" (Karte im Spiel), "since", "charge", "creature"}
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
        self.next_pw = 0      # der naechste Planeswalker-Zauber kostet {N} weniger (Sparks Ablaze)
        self.seek_discard = []  # mit Seek geholte Karten, die im naechsten Endsegment abgeworfen werden (Killian)
        self.verse = {}       # Vers-Marken je Aria of Flame (id der Karte)
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
        self.trap_links = []  # Exil bis zum Verlassen (610.3): {"trap", "card", "owner", "creature"}
        self.lock_links = []  # Lock-Auras dieses Spielers: {"aura", "creature"}
        self.predrawn = Counter()  # Main Phase: Karten, deren "draw N" die Planung (resolve_draws) schon gezogen hat
        self.walkers = []     # echte Planeswalker (Walker) auf dem Feld
        self.emblems = []     # Embleme (114): ("team", P, T), ("cast_draw",), ("cast_damage", N)
        self.attack_buff = None  # bis zum naechsten Zug: (P, T, Schritt) fuer Angriffe auf den Gegner (Garruk)
        self.shield = None    # bis zum naechsten Zug: (-N, Schritt) fuer Angreifer auf uns (Jace, Reality Sculptor)
        self.copy_next = None  # Way of the Cryomancer: in diesem Schritt wird der naechste Instant/Sorcery kopiert
        self.charges = 0      # Charge-Marken auf Gardenize
        self.discards_turn = 0  # in diesem Zug abgeworfene Karten (Jiang Yanggu, Alone)
        self.no_legend_step = None  # Hall of Echoes: in diesem Schritt gilt die Legend-Regel nicht
        self.land_now = None  # in diesem Zug gelegtes Land (Hall of Echoes: noch nicht angriffsbereit)
        self.cc_land = None   # Land mit "{T}: Add {C}{C}", bis Emrakul aus dem Exil gewirkt wird
        self.grant_target = None  # Teyo: Ziel des Betreten-Effekts (Kreatur oder "done": schon angewendet)
        self.x_values = []    # X gewirkter Kreaturen mit "enters with X counters": [(Karte, X)] (Guiding Hydra)
        self.max_deck_mv = max((c.mv for c in cards if not c.is_land), default=0)  # teuerste Karte des Decks (Pia)
        self.noncombat_step = None  # Schritt, in dem dieser Spieler zuletzt Schaden ausserhalb des Kampfs bekam

    def board(self):
        return [(c.card, c.entered) for c in self.creatures], [c.bonus for c in self.creatures], \
            {i: c.pump for i, c in enumerate(self.creatures) if c.pump}

    def write_back(self, bonus, pump):
        for i, c in enumerate(self.creatures):
            c.bonus = bonus[i]
            c.pump = pump.get(i, 0)


def _mana(me, step):
    """Mana zu Rundenbeginn: Laender, Manaquellen-Permanents, Kreaturen mit Mana-Faehigkeit (nicht frisch, ungetappt)."""
    pool, cc = [], me.cc_land
    for land in me.lands:  # Emrakul: ein Land liefert {C}{C} statt seiner Farbe
        if cc is not None and land == cc:
            pool += [("C",), ("C",)]
            cc = None
        else:
            pool.append(land.land_colors)
    pool += [u for card in me.perms for u in card.mana_src]
    creature_units = [(u, i) for i, c in enumerate(me.creatures)
                      if c.card.mana_src and not c.tapped and (c.entered < step or c.card.haste or c.has("haste"))
                      for u in c.card.mana_src]
    powers = len({c.power for c in me.creatures if not c.dead})
    creature_units += [(ANY_COLOR, i) for i, c in enumerate(me.creatures)  # Loot, the Nexus
                       if c.card.nexus_mana and not c.tapped and not c.dead
                       and (c.entered < step or c.card.haste or c.has("haste")) for _k in range(powers)]
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
    if card.is_planeswalker and p is not None:  # Tam, the Possibility
        change += sum(c.card.pw_discount for c in p.creatures if not c.dead) + sum(c.pw_discount + c.memorial_pw_mana
                                                                                    for c in p.perms) + p.next_pw
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
    w = ward_of(c)
    if not w:
        return True
    if w[0] == "discard":
        return bool(caster.hand)
    if w[0] == "sac":  # nur gegen drohendes Lethal und mit genug bleibenden Karten
        return c.power >= caster.life and len(sac_order(caster)) >= w[1]
    have = len(caster.ward_pool) if caster.ward_pool is not None else len(caster.open) + caster.ward_budget
    return w[1] <= have


def pay_ward(caster, c, e):
    """Zahlt die Ward-Kosten von c (vorher mit ward_ok geprueft)."""
    w = ward_of(c)
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
    if w[0] == "sac":
        gone = sacrifice_permanents(caster, w[1], e)
        e["events"].append(f"{caster.name}: opfert {', '.join(gone)} (Ward von {c.card.name})")
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
        w = ward_of(t)
        if not w:
            return 0
        if w[0] == "discard":
            if len(me.hand) > 1:
                return 0
            continue
        if w[0] == "sac":
            if ward_ok(me, t):
                return 0
            continue
        if w[1] <= len(rest):
            return w[1]
    return 0 if spec[3] else 99


def protect_response(p, target, caster, e, step):
    """p antwortet auf Removal gegen target mit Hexproof (der Zauber hat dann kein legales Ziel, 608.2b): Teyo,
    Lightshield Expert (Flash) fuer eine Kreatur ab Manawert 3 oder unsere gefaehrlichste; Liliana the Faultless fuer
    eine andere Kreatur ab Manawert 3, abgeworfen wird nur eine ueberzaehlige Karte (zuerst ein Land)."""
    if hexproof(target) or target.dead:
        return False
    alive = [c for c in p.creatures if not c.dead]
    if target.card.mv >= 3 or target is max(alive, key=danger):
        for card in [c for c in p.hand if c.flash and c.is_creature and "hexproof" in c.etb_grant]:
            if not affordable(p, card) or not legend_ok(p, card):
                continue
            _cast_from_open(p, card)
            if try_counter(p, card, step, e):
                p.graveyard.append(card)
                on_cast(p, card, step, e)
                continue
            new = Creature(card, step)
            p.creatures.append(new)
            p.grant_target = target
            e["events"].append(f"{p.name}: {card.name} mit Flash als Antwort")
            on_cast(p, card, step, e)
            creature_enters(p, new, step, e, caster)
            return True
    if target.card.mv < 3:
        return False
    for lili in [c for c in alive if c.card.liliana_hexproof and c is not target and tap_ready(p, c)]:
        gone = surplus_land(p) or max((c for c in p.hand if not c.is_land and c.mv > len(p.lands) + 2),
                                      key=lambda c: c.mv, default=None)
        if gone is None or not _pay_open(p, lili.card.liliana_hexproof, treasure=False):
            continue
        lili.tapped = True
        p.hand.remove(gone)
        p.graveyard.append(gone)
        discarded(p, e)
        target.extra.add("hexproof")
        e["events"].append(f"{p.name}: {lili.card.name} wirft {gone.name} ab – {target.card.name} bekommt Hexproof")
        return True
    return False


def sac_order(p):
    """Reihenfolge beim Opfern bleibender Karten (Ward von Emrakul): Token, ueberzaehlige Laender (mehr als der hoechste
    Manawert der Hand), die schwaechsten Kreaturen, dann der Rest."""
    out = [("c", c) for c in sorted((c for c in p.creatures if not c.dead and c.card.is_token), key=danger)]
    out += [("p", c) for c in p.perms if c.is_token]
    need = max((c.mv for c in p.hand if not c.is_land), default=0)
    lands = list(p.lands)
    while len(lands) > need:
        land = _redundant_land(p, lands)
        lands.remove(land)
        out.append(("l", land))
    out += [("c", c) for c in sorted((c for c in p.creatures if not c.dead and not c.card.is_token), key=danger)]
    out += [("l", land) for land in lands]
    out += [("p", c) for c in p.perms if not c.is_token] + [("w", w) for w in p.walkers]
    return out


def sacrifice_permanents(p, n, e):
    """p opfert n bleibende Karten nach sac_order. Gibt die Namen zurueck."""
    gone = []
    for kind, obj in sac_order(p)[:n]:
        if kind == "c":
            obj.dead = True
            gone.append(obj.card.name)
            continue
        if kind == "l":
            if not _tapped_lands(p)[obj.land_colors] and obj.land_colors in p.open:
                p.open.remove(obj.land_colors)  # ungetapptes Land: sein Mana fehlt jetzt
            p.lands.remove(obj)
            p.graveyard.append(obj)
        elif kind == "p":
            p.perms.remove(obj)
            if not obj.is_token:
                p.graveyard.append(obj)
        else:
            p.walkers.remove(obj)
            p.graveyard.append(obj.card)
        gone.append(obj.name if kind != "w" else obj.card.name)
    return gone


def valid_targets(spec, caster, victim, ward=True):
    kind = spec[0]
    out = [c for c in victim.creatures if not c.dead and (kind != "lock" or not c.locked) and _matches(spec[2], c)
           and not hexproof(c) and (not ward or ward_ok(caster, c))]
    if kind in ("destroy", "damage", "fight"):  # 702.12b: zerstoeren und toedlicher Schaden wirken nicht
        out = [c for c in out if not c.has("indestructible")]
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
    target = choose_target(spec, caster, victim)
    return target is not None or pw_target(card, caster, victim, target) is not None


def _jace_add(p, n, e=None):
    """Loyalty fuer Jace; Kreaturen mit "whenever you put loyalty counters" (Tethermage) bekommen sofort ihre Marken."""
    if n <= 0:
        return
    created = not jace_present(p)  # Empower ohne Jace erschafft den Token: er kommt ins Spiel
    before = p.jace.events
    p.jace.add(n)
    if created:
        ally_walker_enters(p, e)
    delta = p.jace.events - before
    for c in p.creatures:
        if c.card.loyalty_counter and not c.dead:
            c.bonus += c.card.loyalty_counter * delta
    if e is not None:
        e["events"].append(f"{p.name}: Jace +{n} (Loyalty {p.jace.loyalty})")


def _mill(p, n, e=None, source=""):
    milled = p.library[:n]
    del p.library[:n]
    p.graveyard.extend(milled)
    if milled:
        library_to_graveyard(p)
    if e is not None and milled:
        e["events"].append(f"{p.name}: {source} – Mill {len(milled)}")


def ally_walker_enters(p, e=None):
    """Ein Planeswalker (Karte oder Jace-Token) kommt bei p ins Spiel: Ausloeser "another creature or planeswalker you
    control enters" (Liliana the Faultless: Leben, Liliana the Repentant: Mill)."""
    for c in p.creatures:
        if c.dead or not c.card.enter_pw_too:
            continue
        gain_life(p, c.card.ally_enter_life)
        if c.card.ally_enter_mill:
            _mill(p, c.card.ally_enter_mill, e, c.card.name)


def remove_counters(p, opp, n, src, e):
    """Mabel, Bitter Recluse: bis zu n Marken von einem anderen Ziel. Reihenfolge: gegnerischer Planeswalker oder
    Jace-Token mit hoechstens n Loyalty (stirbt) > gegnerische Kreatur mit den meisten +1/+1-Marken > gegnerischer
    Planeswalker mit der meisten Loyalty > eigene Kreatur mit Stun-Marken."""
    if opp is not None:
        small = [w for w in opp.walkers if 0 < w.loyalty <= n]
        if small:
            w = max(small, key=lambda w: (w.card.mv, w.loyalty))
            w.loyalty = 0
            e["events"].append(f"{p.name}: {src} – {w.card.name} verliert seine Loyalty")
            bury((p, opp), e)
            return
        if jace_present(opp) and 0 < opp.jace.loyalty <= n:
            before = opp.jace.loyalty
            opp.jace.loyalty = 0
            e["events"].append(f"{p.name}: {src} – Jace von {opp.name} verliert seine Loyalty")
            _jace_zero(opp, before, e)
            return
        marked = [c for c in opp.creatures if not c.dead and c.bonus > 0 and not hexproof(c) and ward_ok(p, c)]
        if marked:
            c = max(marked, key=lambda c: (c.bonus, danger(c)))
            pay_ward(p, c, e)
            k = min(n, c.bonus)
            c.bonus -= k
            e["events"].append(f"{p.name}: {src} – {k} Marken von {c.card.name}")
            return
        big = [(w.loyalty, w) for w in opp.walkers if w.loyalty > 0]
        if jace_present(opp) and opp.jace.loyalty > 0:
            big.append((opp.jace.loyalty, "jace"))
        if big:
            _l, w = max(big, key=lambda t: (t[0], t[1] != "jace"))
            if w == "jace":
                opp.jace.loyalty -= n
                e["events"].append(f"{p.name}: {src} – Jace von {opp.name} -{n} Loyalty")
            else:
                w.loyalty -= n
                e["events"].append(f"{p.name}: {src} – {w.card.name} -{n} Loyalty")
            return
    stunned = [c for c in p.creatures if not c.dead and c.stun > 0 and c.card.name != src]
    if stunned:
        c = max(stunned, key=danger)
        c.stun = max(0, c.stun - n)
        e["events"].append(f"{p.name}: {src} – Stun-Marken von {c.card.name} entfernt")


def exhaust_abilities(p, opp, step, e):
    """Exhaust (702.177, einmal je Objekt), Sorcery-Zeit in Main 2 mit uebrigem Mana: Liliana the Repentant holt die
    Kreatur oder den Planeswalker mit dem hoechsten Manawert (mindestens 4) zurueck und bekommt eine Marke."""
    for c in list(p.creatures):
        ex = c.card.exhaust_reanimate
        if c.dead or not ex or c.once.get("exhaust") is not None:
            continue
        cands = [g for g in gy_candidates(p, ex[1]) if g.mv >= 4]
        if not cands or not _pay_ability(p, ex[0], "free"):
            continue
        c.once["exhaust"] = step
        pick = _best_from_gy(p, cands)
        p.graveyard.remove(pick)
        e["events"].append(f"{p.name}: {c.card.name} – Exhaust: {pick.name}")
        put_back(p, pick, "battlefield", step, e, opp)
        c.bonus += 1


def eye_upkeep(p, opp, e):
    """Eye of Jace zu Beginn des Upkeeps: Surveil 1, danach ab 7 Karten im Friedhof opfern, Schaden und Leben."""
    for card in list(p.perms):
        if not card.upkeep_surveil:
            continue
        surveil_cards(p, [card.upkeep_surveil], e, card.name)
        if card.eye_threshold and len(p.graveyard) >= 7 and card in p.perms:
            dmg, life = card.eye_threshold
            p.perms.remove(card)
            if not card.is_token:
                p.graveyard.append(card)
            e["events"].append(f"{p.name}: opfert {card.name}")
            deal_noncombat(p, opp, dmg, e)
            gain_life(p, life)


def life_token_instants(p, opp, step, e):
    """Germinate Recruits im eigenen Zug nach dem Kampf, wenn wir mindestens 2 Leben gewonnen haben."""
    for card in [c for c in p.hand if c.life_tokens is not None and c.is_instant]:
        if p.gained >= 2 and card in p.hand and _cast_from_open(p, card):
            e["events"].append(f"{p.name}: {card.name} in Main 2 (X = {p.gained})")
            p.cast_count += 1
            _resolve(p, opp, card, step, e)


def room_of_refuge(p, step, e):
    """Room of Refuge in Main 2: opfern, wenn danach noch mindestens 6 Laender bleiben, keine Handkarte mehr Laender
    braucht und das Mana uebrig ist; zwei Marken auf die gefaehrlichste eigene Kreatur."""
    for land in list(p.lands):
        if not land.land_sac_counters:
            continue
        alts, n = land.land_sac_counters
        alive = [c for c in p.creatures if not c.dead]
        rest = len(p.lands) - 1
        if not alive or rest < 6 or any(c.mv > rest for c in p.hand if not c.is_land):
            continue
        if land.land_colors not in p.open:
            continue
        p.open.remove(land.land_colors)  # {T}: das Land selbst
        if not _pay_open(p, alts, treasure=False):
            p.open.append(land.land_colors)
            continue
        p.lands.remove(land)
        p.graveyard.append(land)
        pick = max(alive, key=danger)
        pick.bonus += n
        e["events"].append(f"{p.name}: opfert {land.name} – {n} Marken auf {pick.card.name}")


def legend_discard_draw(p, e):
    """Solitary Cell am Ende des gegnerischen Zugs: eine nutzlose legendaere Karte abwerfen und ziehen (Namensvetter
    liegt schon, Legend-Regel; oder mindestens 3 Mana teurer als unsere Laender)."""
    for card in list(p.perms):
        if not card.legend_discard_draw:
            continue
        dead = [c for c in p.hand if c.legendary and not c.is_land and not legend_ok(p, c)]
        dear = [c for c in p.hand if c.legendary and not c.is_land and c.mv >= len(p.lands) + 3]
        pick = (dead or dear or [None])[0]
        if pick is None or not _pay_open(p, card.legend_discard_draw, treasure=False):
            continue
        p.hand.remove(pick)
        p.graveyard.append(pick)
        e["events"].append(f"{p.name}: {card.name} – wirft {pick.name} ab, zieht")
        discarded(p, e, [pick])
        _draw(p)


def etb_rank(card):
    """Wert eines Betreten-Effekts zum Wiederholen: 3 Removal, 2 Ziehen, 1 Token oder sonst etwas, 0 nichts."""
    if card.removal and card.removal[4] == "etb":
        return 3
    if card.draws or card.etb_loot_stun:
        return 2
    return 1 if enter_value(card) else 0


def blink(p, c, step, e, source):
    """Eine eigene Kreatur exilieren und als neues Objekt zurueck (400.7): Marken, Schaden, Auras weg, Betreten-
    Effekte wirken erneut, Einsatzverzoegerung."""
    p.creatures.remove(c)
    _leave(p, c.card)
    check_auras(p, e)
    new = Creature(c.card, step)
    p.creatures.append(new)
    e["events"].append(f"{p.name}: {source} blinkt {c.card.name}")
    creature_enters(p, new, step, e, p.opponent, cast=False)


def animate_target(p):
    """Puppet Crafting: Token-Artefakt zuerst, sonst das Nichtkreatur-Artefakt mit dem niedrigsten Manawert."""
    arts = [c for c in p.perms if c.is_artifact and not c.is_creature and not c.equip]
    return min(arts, key=lambda c: (not c.is_token, c.mv, c.name)) if arts else None


def damage_ramp(p, n, e):
    """Hexhaven Invigorator: bis zu n Laender getappt aufs Feld, neue Farben zuerst."""
    for _k in range(n):
        lands = [c for c in p.library if c.is_land]
        if not lands:
            break
        have = set().union(*(c.land_colors for c in p.lands)) if p.lands else set()
        count = Counter(c.name for c in lands)
        pick = max(lands, key=lambda c: (len(set(c.land_colors) - have), count[c.name], c.name))
        p.library.remove(pick)
        p.lands.append(pick)
        e["events"].append(f"{p.name}: sucht {pick.name} (getappt)")
        if p.opponent is not None:
            on_land(p, p.opponent, pick, p.now, e, with_mana=False)
    random.shuffle(p.library)


def hand_bolt_tricks(p, pairs, opp, e, step, attacking):
    """Gideon's Memorial aus der Hand: 4 Schaden an einen Angreifer oder Blocker des Gegners, der sonst eine unserer
    Kreaturen toetet (und daran stirbt)."""
    for card in [c for c in p.hand if c.hand_combat_bolt]:
        alts, n = card.hand_combat_bolt
        for att, blockers in pairs:
            if not blockers:
                continue
            a_dead, b_deads = outcome(att, blockers)
            if attacking:
                foes = [b for b in blockers if not b.dead] if a_dead else []
            else:
                foes = [att] if any(b_deads) and not att.dead else []
            foes = [x for x in foes if x.toughness - x.damage <= n]
            if not foes or not _payable(p, alts):
                continue
            x = max(foes, key=danger)
            _pay_open(p, alts)
            p.hand.remove(card)
            p.graveyard.append(card)
            discarded(p, e, [card])
            x.damage += n
            x.dead = True
            e["events"].append(f"{p.name}: {card.name} – {n} Schaden an {x.card.name}")
            break


def anomaly_for_lethal(me, opp, step, e):
    """Loot, the Anomaly (Threshold): andere Kreaturen opfern (-2/-0 je Opfer, also mehr Schaden) nur fuer Lethal."""
    if len(me.graveyard) < 7:
        return
    for loot in [c for c in me.creatures if c.card.threshold_sac_minus and not c.dead and can_attack(c, step)]:
        if _attack_value(me, opp, step) >= opp.life:
            return
        others = sorted((c for c in me.creatures if c is not loot and not c.dead),
                        key=lambda c: (can_attack(c, step), not c.card.is_token, c.power, c.card.mv))
        for k in range(1, len(others) + 1):
            picked = others[:k]
            for c in picked:
                c.dead = True
            loot.pump -= 2 * k
            value = _attack_value(me, opp, step)
            for c in picked:
                c.dead = False
            loot.pump += 2 * k
            if value >= opp.life:
                for c in picked:
                    c.dead = True
                    e["events"].append(f"{me.name}: opfert {c.card.name} für {loot.card.name}")
                loot.pump -= 2 * k
                bury((me,), e)
                return


def puppetbeast_sac(p, step, e):
    """Hungering Puppetbeast vor dem Angriff: Heartwood-Token opfern, deren Mana noch offen ist (sie bezahlen das {1}
    selbst); Haste, wenn sie sonst nicht angreifen kann, sonst Trample."""
    for beast in [c for c in p.creatures if c.card.artifact_sac_counter and not c.dead]:
        for token in [c for c in p.perms if c.is_token and c.is_artifact and c.mana_src]:
            unit = token.mana_src[0]
            if unit not in p.open:
                continue
            p.open.remove(unit)  # das Token bezahlt das {1}, dann wird es geopfert
            p.perms.remove(token)
            beast.bonus += 1
            kw = "haste" if not can_attack(beast, step) and not beast.has("haste") else "trample"
            beast.extra.add(kw)
            e["events"].append(f"{p.name}: {beast.card.name} opfert {token.name}: Marke, {kw}")


def hall_of_echoes(p, step, e):
    """Hall of Echoes vor dem Angriff: mit 5 freiem Mana eine Kopie der staerksten eigenen Kreatur, die angreift
    (das Land muss seit Zugbeginn liegen und ungetappt sein)."""
    for hall in [c for c in p.lands if c.hall_copy]:
        if hall is p.land_now or hall.land_colors not in p.open:
            continue
        alive = [c for c in p.creatures if not c.dead and c.land_source is None]
        if not alive:
            continue
        p.open.remove(hall.land_colors)
        if not _pay_open(p, hall.hall_copy, treasure=False):
            p.open.append(hall.land_colors)
            continue
        model = max(alive, key=lambda c: (c.card.power + c.card.toughness, c.card.mv))
        copy = Creature(model.card, 0)
        copy.gy, copy.ctl, copy.land_source = p.graveyard, p, hall
        p.creatures.append(copy)
        p.no_legend_step = p.now
        e["events"].append(f"{p.name}: {hall.name} wird eine Kopie von {model.card.name}")


def rescue_girl(p, opp, step, e):
    """Rescue Girl in Main 2: eine eigene Kreatur mit wertvollem Betreten-Effekt auf die Hand und sofort neu wirken."""
    for girl in [c for c in p.creatures if c.card.rescue_bounce and not c.dead and not c.tapped
                 and (c.entered < step or c.has("haste"))]:
        cands = [c for c in p.creatures if c is not girl and not c.dead and not c.card.is_token
                 and etb_rank(c.card) > 0 and pay(list(p.open), _alts(p, c.card)) is not None]
        if not cands:
            continue
        t = max(cands, key=lambda c: (etb_rank(c.card), c.card.mv))
        girl.tapped = True
        p.creatures.remove(t)
        _leave(p, t.card)
        check_auras(p, e)
        p.hand.append(t.card)
        e["events"].append(f"{p.name}: {girl.card.name} – {t.card.name} auf die Hand, neu gewirkt")
        if _cast_from_open(p, t.card):
            p.cast_count += 1
            _resolve(p, opp, t.card, step, e)


def identity_echo(p, opp, step, e):
    """Identity Echo in Main 2 mit freiem Mana: eigene Kreatur mit Manawert hoechstens 2 (die billigste) gegen die
    naechste Kreatur oder den naechsten Planeswalker der Bibliothek; der Rest kommt gemischt nach unten."""
    for echo in [c for c in p.perms if c.identity_echo]:
        small = [c for c in p.creatures if not c.dead and c.card.mv <= 2 and c.land_source is None]
        if not small or not any(c.is_creature or c.is_planeswalker for c in p.library):
            continue
        if not _pay_ability(p, echo.identity_echo, "free"):
            continue
        t = min(small, key=lambda c: (c.card.mv, c.power + c.toughness))
        p.creatures.remove(t)
        _leave(p, t.card)
        check_auras(p, e)
        revealed = []
        while p.library:
            top = p.library.pop(0)
            if top.is_creature or top.is_planeswalker:
                random.shuffle(revealed)
                p.library.extend(revealed)
                e["events"].append(f"{p.name}: {echo.name} – {t.card.name} ins Exil, {top.name} aufs Feld")
                put_back(p, top, "battlefield", step, e, opp)
                break
            revealed.append(top)


def prepare_abilities(p, step, e):
    """Main 2: Hexhaven Dueling Arena macht eine Kreatur mit Zauberhaelfte prepared ({2} nach ihrem Angriff, sonst
    {4}); Codie macht alle eigenen Kreaturen prepared."""
    for arena in [c for c in p.lands if c.arena_prepare]:
        if arena.land_colors not in p.open:
            continue
        cands = [c for c in p.creatures if not c.dead and c.card.prepared and not c.prepared]
        if not cands:
            continue
        t = max(cands, key=lambda c: (c.attacked == step, c.card.prepared[1].mv))
        n = arena.arena_prepare[0] if t.attacked == step else arena.arena_prepare[1]
        p.open.remove(arena.land_colors)
        if not _pay_open(p, ((n, ()),), treasure=False):
            p.open.append(arena.land_colors)
            continue
        t.prepared = True
        e["events"].append(f"{p.name}: {arena.name} – {t.card.name} wird prepared")
    for codie in [c for c in p.creatures if c.card.codie_prepare and not c.dead and not c.tapped
                  and (c.entered < step or c.has("haste"))]:
        cands = [c for c in p.creatures if not c.dead and c.card.prepared and not c.prepared]
        if not cands or not _pay_open(p, codie.card.codie_prepare, treasure=False):
            continue
        codie.tapped = True
        for c in cands:
            c.prepared = True
        e["events"].append(f"{p.name}: {codie.card.name} – alle Kreaturen prepared")


def emrakul_exile(p, step, e):
    """Main 2: Emrakul fuer {3} aus der Hand exilieren, wenn das Mana sonst ungenutzt bliebe und wir sie auch mit zwei
    weiteren Landdrops nicht normal wirken koennten. Das Land, das am wenigsten fehlt, liefert {C}{C}, bis Emrakul aus
    dem Exil gewirkt wird; Emrakul ist so lange aus dem Exil spielbar."""
    if p.cc_land is not None or not p.lands:
        return
    for card in [c for c in p.hand if c.hand_exile_land]:
        pool, units = _mana(p, step)
        if len(pool) + len(units) + 2 >= card.mv or not _pay_open(p, card.hand_exile_land, treasure=False):
            continue
        p.hand.remove(card)
        p.impulse.append((card, 10 ** 9))
        p.cc_land = _redundant_land(p)
        e["events"].append(f"{p.name}: exiliert {card.name} – {p.cc_land.name} liefert {{C}}{{C}}")
        return


def _artifacts(p):
    return sum(c.is_artifact for c in p.perms) + sum(1 for c in p.creatures if c.card.is_artifact and not c.dead)


def aerid_pump(me, opp, step, e):
    """Vor dem Angriff: Aerid Konstrari {6} (Heartwood-Token, +X/+0), wenn das Lethal bringt oder einen Blocker
    besiegt, der Aerid sonst aufhaelt."""
    for c in [c for c in me.creatures if c.card.aerid_pump and not c.dead and can_attack(c, step)]:
        if not _payable(me, c.card.aerid_pump):
            continue
        x = _artifacts(me) + 1
        before = _attack_value(me, opp, step)
        c.pump += x
        lethal = _attack_value(me, opp, step) >= opp.life > before
        c.pump -= x
        wall = any(not b.tapped and not b.dead and can_block(b, c) and c.power < b.toughness - b.damage <= c.power + x
                   for b in opp.creatures)
        if (lethal or wall) and _pay_ability(me, c.card.aerid_pump, "free"):
            artifact_tokens(me, HEARTWOOD, 1, step, e)
            n = _artifacts(me)
            c.pump += n
            e["events"].append(f"{me.name}: {c.card.name} – Heartwood-Token, +{n}/+0")


def end_step_abilities(p, e, step):
    """Am Ende des gegnerischen Zugs mit freiem Mana: Aerid Konstrari nur fuer den Heartwood-Token, Yoshimaru eine Marke
    auf die gefaehrlichste legendaere Kreatur."""
    for c in [c for c in p.creatures if c.card.aerid_pump and not c.dead]:
        if _pay_open(p, c.card.aerid_pump, treasure=False):
            artifact_tokens(p, HEARTWOOD, 1, step, e)
            e["events"].append(f"{p.name}: {c.card.name} – Heartwood-Token")
    for y in [c for c in p.creatures if c.card.yoshi_counter and not c.dead]:
        legends = [c for c in p.creatures if c.card.legendary and not c.dead]
        while legends and _pay_open(p, y.card.yoshi_counter, treasure=False):
            t = max(legends, key=danger)
            t.bonus += 1
            e["events"].append(f"{p.name}: {y.card.name} – Marke auf {t.card.name}")


def _through(pairs):
    return resolve_combat([(a.copy(), [b.copy() for b in bs]) for a, bs in pairs])["player"]


def yoshimaru_combat(p, pairs, opp, e, step, attacking):
    """Im Kampf (nach den Blockern): Yoshimaru {6} auf eine legendaere Kampfkreatur, wenn das Lethal bringt, den Kampf
    verbessert oder gegnerisches Lethal verhindert."""
    sources = [c for c in p.creatures if c.card.yoshi_counter and not c.dead]
    own = [a for a, _bs in pairs] if attacking else [b for _a, bs in pairs for b in bs]
    legends = [c for c in own if c.card.legendary and not c.dead]
    for y in sources:
        for _k in range(3):
            if not legends or not _payable(p, y.card.yoshi_counter):
                return
            base = _score(pairs, attacking, opp.life)
            dying = not attacking and _through(pairs) >= p.life
            best = None
            for t in legends:
                old = t.bonus
                t.bonus += 1
                gain = _score(pairs, attacking, opp.life) - base
                if dying and _through(pairs) < p.life:
                    gain += 1000
                t.bonus = old
                if gain > 0 and (best is None or gain > best[0]):
                    best = (gain, t)
            if best is None or not _pay_open(p, y.card.yoshi_counter, treasure=False):
                break
            best[1].bonus += 1
            e["events"].append(f"{p.name}: {y.card.name} – Marke auf {best[1].card.name}")


def hapatra_untap(p, step, e):
    """Main 2: Hapatra {2}{U} enttappt den staerksten eigenen Angreifer dieses Zugs (kann dann blocken)."""
    for h in [c for c in p.creatures if c.card.hapatra_untap and not c.dead]:
        while True:
            cands = [c for c in p.creatures if not c.dead and c.tapped and c.attacked == step]
            if not cands or not _pay_ability(p, h.card.hapatra_untap, "free"):
                break
            t = max(cands, key=danger)
            t.tapped = False
            e["events"].append(f"{p.name}: {h.card.name} enttappt {t.card.name}")


def fblthp_lost(p, opp, e):
    """Fblthp, Impossibly Lost: der Gegner bekam in unserem Zug Kampfschaden -> N ziehen; ist die Bibliothek dann
    leer, gewinnen wir; Fblthp wird in die Bibliothek gemischt."""
    for f in [c for c in p.creatures if c.card.fblthp_lost]:
        _draw(p, f.card.fblthp_lost)
        e["events"].append(f"{p.name}: {f.card.name} zieht {f.card.fblthp_lost}")
        if not p.library:
            opp.lost = True
            e["events"].append(f"{p.name}: gewinnt durch {f.card.name} (Bibliothek leer)")
        if not f.dead:
            p.creatures.remove(f)
            p.library.insert(random.randrange(len(p.library) + 1), f.card)


CARD_TYPES = (("artifact", lambda c: c.is_artifact), ("creature", lambda c: c.is_creature),
              ("enchantment", lambda c: c.is_enchantment), ("instant", lambda c: c.is_instant),
              ("sorcery", lambda c: c.is_instant_sorcery and not c.is_instant),
              ("planeswalker", lambda c: c.is_planeswalker))


def uldaros_pick(p, opp, budget):
    """Uldaros Theorix: je Kartentyp hoechstens eine Nichtland-Karte aus dem Friedhof, zusammen Manawert <= budget.
    Zuerst Removal mit lohnendem Ziel, dann der hoechste Gesamt-Manawert, dann die meisten Kreaturen."""
    alive = any(not c.dead for c in p.creatures)
    cands = [c for c in dict.fromkeys(p.graveyard) if not c.is_land and c.mv <= budget and c.alts
             and not c.x_counters and not c.x_search_basics and legend_ok(p, c)
             and (not c.removal or c.removal[4] == "etb" or has_target(c, p, opp))
             and (not c.is_aura or c.removal or alive)]
    best = ((0, 0, 0), [])

    def search(k, chosen, mv):
        nonlocal best
        if k == len(CARD_TYPES):
            score = (sum(1 for c in chosen if c.removal and c.removal[4] != "etb"), mv,
                     sum(c.is_creature for c in chosen))
            if score > best[0]:
                best = (score, list(chosen))
            return
        search(k + 1, chosen, mv)
        for c in cands:
            if CARD_TYPES[k][1](c) and c not in chosen and mv + c.mv <= budget:
                chosen.append(c)
                search(k + 1, chosen, mv + c.mv)
                chosen.pop()
    search(0, [], 0)
    return sorted(best[1], key=lambda c: (not c.removal, -c.mv))


def uldaros_copies(p, opp, card, step, e):
    """Uldaros Theorix (nur gewirkt): die gewaehlten Karten werden exiliert, ihre Kopien kostenlos gewirkt; bleibende
    Karten werden Token, Instants und Sorceries verschwinden danach."""
    for c in uldaros_pick(p, opp, card.uldaros_cast):
        if c not in p.graveyard:
            continue
        p.graveyard.remove(c)
        e["events"].append(f"{p.name}: {card.name} wirkt eine Kopie von {c.name}")
        p.cast_count += 1
        if c.is_instant_sorcery:
            _resolve(p, opp, c, step, e, to_exile=True)
        else:
            _resolve(p, opp, c._replace(is_token=True), step, e)


def combat_locked(me, opp):
    """Yuriko, Blade of the Mighty: waehrend des Kampfs keine Zauber und keine Faehigkeiten ausser Mana."""
    return any(c.card.combat_lock and not c.dead for c in me.creatures + opp.creatures)


def no_enter_triggers(p):
    """Karn, Argent Defender (bei einem der beiden Spieler): Artefakte und Kreaturen loesen beim Betreten nichts aus."""
    return any(c.card.no_enter_triggers and not c.dead for q in (p, p.opponent) if q is not None
               for c in q.creatures)


def artifact_tokens(p, kind, n, step, e):
    """Artefakt-Token erschaffen (Treasure, Heartwood, Lotus). Draconic Visitor: stattdessen 5/5-Dragons mit Flying
    (614.1). Gibt True zurueck, wenn die Artefakte wirklich entstanden sind."""
    if n <= 0:
        return False
    if any(c.card.artifact_tokens_dragons and not c.dead for c in p.creatures):
        make_tokens(p, [(n, DRAGON)], step, e, p.opponent, "Draconic Visitor")
        return False
    if kind == "treasure":
        p.treasures += n
    else:
        p.perms += [kind] * n
    return True


def hydra_spread(p, e):
    """Guiding Hydra zu Kampfbeginn: eine Marke von ihr auf jede andere eigene Kreatur, wenn mindestens 2 davon
    profitieren."""
    for h in list(p.creatures):
        if not h.card.hydra_spread or h.dead or h.bonus < 1:
            continue
        others = [c for c in p.creatures if c is not h and not c.dead]
        if len(others) < 2:
            continue
        h.bonus -= 1
        for c in others:
            c.bonus += 1
        e["events"].append(f"{p.name}: {h.card.name} verteilt Marken")
    bury((p,) if p.opponent is None else (p, p.opponent), e)


def upkeep_triggers(me, opp, step, e):
    """Zu Beginn jedes Upkeeps (beider Spieler): Verdant Kraken erschafft ein Tentacle fuer seinen Kontrolleur; Command
    the Stage kommt auf die Hand, wenn ein Gegner seines Besitzers im letzten Zug Schaden ausserhalb des Kampfs
    bekam."""
    for p in (me, opp):
        for c in list(p.creatures):
            if c.card.upkeep_token is not None and not c.dead:
                make_tokens(p, [(1, c.card.upkeep_token)], step, e, p.opponent, c.card.name)
                if p.opponent is not None:  # das Token ist ein Land (Forest): Landfall
                    on_land(p, p.opponent, c.card.upkeep_token, step, e, with_mana=False)
        foe = p.opponent
        if foe is not None and foe.noncombat_step == step - 1:
            for card in [g for g in p.graveyard if g.noncombat_recur]:
                p.graveyard.remove(card)
                p.hand.append(card)
                e["events"].append(f"{p.name}: {card.name} aus dem Friedhof auf die Hand")


def end_step_prepare(players, e):
    """Zu Beginn jedes Endsegments: Bloodline Recollector wird prepared, wenn in diesem Zug 3 oder mehr Kreaturen
    gestorben sind (beide Spieler)."""
    died = sum(p.deaths - p.deaths_mark for p in players)
    if died < 3:
        return
    for p in players:
        for c in p.creatures:
            if c.card.prepared and c.card.prepared[0] == "deaths3" and not c.dead and not c.prepared:
                c.prepared = True
                e["events"].append(f"{p.name}: {c.card.name} wird prepared")


def jace_died(p, e):
    """Der Jace-Token faellt auf 0 Loyalty und kommt in den Friedhof (704.5i), er stirbt also (700.4): Ausloeser
    "another creature or planeswalker you control dies" (Edgar, Ancient Bloodlord; Massacre Girl)."""
    walker_died(p, "Jace", e)


def walker_died(p, name, e):
    """Ein Planeswalker von p stirbt (704.5i, 700.4): Ausloeser "another creature or planeswalker you control dies"."""
    e["events"].append(f"{p.name}: {name} stirbt")
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
                                    or c.kiora_attack or c.copy_grant for c in grant_sources(p))


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
    out += _copy_abilities(p)
    return out


def _copy_abilities(p):
    """Way of the Cryomancer: eine verliehene Kopier-Faehigkeit (mehrere Quellen geben dieselbe Faehigkeit)."""
    costs = sorted({card.copy_grant for card in grant_sources(p) if card.copy_grant}, reverse=True)
    return [(costs[0], (("copy_next",),), "Cryomancer")] if costs else []


def copy_rank(p, opp, pool, spells):
    """(Rang, Gleichstand) der Kopie des ersten Instants/Sorcery, den die Main Phase wirken wuerde: 8 Lethal (der
    Schaden doppelt reicht), 6 Removal mit einem zweiten gueltigen Ziel, 4 Ziehen, 2 sonst etwas (Token, Marken,
    Schaden); 0 nichts."""
    if pool is None or spells is None or opp is None:
        return 0, 0
    chosen = best_cast_reduced(spells, land_key(pool), any(not c.dead for c in p.creatures), True)[1]
    first = next((c for c in chosen if c.is_instant_sorcery), None)
    if first is None:
        return 0, 0
    face = max((sum(a[1] for a in m if a[0] == "face") for m in first.modes), default=0)
    if face and 2 * face >= opp.life:
        return 8, face
    spec = first.removal
    if spec:
        if spec[0] == "edict":
            n = sum(1 for c in opp.creatures if not c.dead)
        elif spec[0] in ("sweep", "sweep_damage"):
            n = 0
        else:
            n = len(valid_targets(spec, p, opp))
        if n >= 2:
            return 6, n
    if first.draws:
        return 4, first.draws
    if first.modes or first.creates_tokens or face:
        return 2, face
    return 0, 0


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
            kill = [c for c in alive_opp if not hexproof(c) and ward_ok(p, c) and c.toughness - c.damage <= cdmg
                    and not c.has("indestructible")]
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
        if "copy_next" in kinds:
            if phase != "main1":
                continue
            rank, tie = copy_rank(p, opp, pool, spells)
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
    activation_tokens(p, step, e)
    mana = _grant_atoms(p, opp, atoms, step, e, target, jace=True)
    loyalty_triggers(p, cost, e)
    _jace_zero(p, before, e)
    return mana


def _grant_atoms(p, opp, atoms, step, e, target, jace=False):
    """Effekte der Jace-Faehigkeiten und der verliehenen Faehigkeiten (auch auf echten Planeswalkern). Gibt Mana
    zurueck."""
    mana = []
    for a in atoms:
        kind = a[0]
        if kind == "surveil":
            binned = surveil(p.library, a[1], p.hand, p.lands)
            p.graveyard.extend(binned)
            if binned:
                library_to_graveyard(p)
            if jace:
                p.jace.surveils += 1
                p.jace.surveil_lands += len(binned)
            mark_surveil(p, e)
        elif kind == "draw":
            _draw(p, a[1])
            if jace:
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
        elif kind == "copy_next":
            p.copy_next = step
            e["events"].append(f"{p.name}: der nächste Instant/Sorcery wird kopiert")
    return mana


def loyalty_triggers(p, cost, e):
    """Ausloeser einer Loyalty-Aktivierung (Jace-Token oder echter Planeswalker): Gideon the Oathless, Way of the Mind
    Sculptor (2+ Marken entfernt), Way of the Paradox."""
    if p.opponent is not None:  # Gideon the Oathless
        for g in p.opponent.creatures:
            if g.card.opp_loyalty_ping and not g.dead:
                deal_noncombat(p.opponent, p, g.card.opp_loyalty_ping, e)
    for card in grant_sources(p):
        if card.loyalty_draw and cost != "X" and cost <= -2:  # Way of the Mind Sculptor
            _draw(p, card.loyalty_draw)
        if card.loyalty_paradox:  # Way of the Paradox
            gain_life(p, 1)
            p.extra_lands += 1


def activation_tokens(p, step, e):
    """"Whenever you activate a loyalty ability, create ..." (Ajani Unrelenting): der Ausloeser kommt ueber die
    Faehigkeit und loest vorher auf (405.2)."""
    for w in list(p.walkers):
        if w.card.activation_tokens:
            make_tokens(p, w.card.activation_tokens, step, e, p.opponent, w.card.name)


# ---------------------------------------------------------------------------------------------------------------------
# Echte Planeswalker (L2)
# ---------------------------------------------------------------------------------------------------------------------

PW_DEFER = {"team_pump", "attack_buff", "mill_top"}  # erst nach den Zaubern aus Main 1 (Chandra: freies Mana steht fest)


def pw_abilities(p, w):
    """Eigene Loyalty-Faehigkeiten und verliehene ("Planeswalkers you control have ...")."""
    return list(w.card.pw_abilities) + [(cost, atoms) for card in grant_sources(p) for cost, atoms in card.walker_grants] \
        + [(cost, atoms) for cost, atoms, _src in _copy_abilities(p)]


def _x_cost(w, cost):
    """-X: so viel wie moeglich, ohne dass der Planeswalker stirbt (X = Loyalty - 1)."""
    return -(w.loyalty - 1) if cost == "X" else cost


def _bounce_target(p, opp):
    cands = [c for c in opp.creatures if not c.dead and not hexproof(c) and ward_ok(p, c)]
    return max(cands, key=danger) if cands else None


def _kill_target(p, opp, toughness_hit):
    """Gefaehrlichste gegnerische Kreatur, die toughness_hit Schaden (bzw. -T) toetet."""
    cands = [c for c in opp.creatures if not c.dead and not hexproof(c) and ward_ok(p, c)
             and (c.toughness - c.damage <= toughness_hit or (c.touched and toughness_hit > 0))]
    return max(cands, key=danger) if cands else None


def _buffed_lethal(p, opp, step, pw, tw, kw):
    """Waere der Angriff mit +pw/+tw und Schluesselwoertern fuer alle eigenen Kreaturen Lethal?"""
    alive = [c for c in p.creatures if not c.dead]
    saved = [(c.pump, c.tpump, set(c.extra)) for c in alive]
    for c in alive:
        c.pump += pw
        c.tpump += tw
        c.extra |= set(kw)
    lethal = _attack_value(p, opp, step) >= opp.life
    for c, (pu, tp, ex) in zip(alive, saved):
        c.pump, c.tpump, c.extra = pu, tp, ex
    return lethal


def pw_rank(p, opp, w, cost, atoms, step, phase, pool=None, spells=None):
    """(Rang, Gleichstand, Ziel) einer Loyalty-Faehigkeit eines echten Planeswalkers; Rang 0 = nicht nutzen.
    8 Lethal, 7 Ultimate (Kosten -6 oder weniger) oder Emblem, 6 Removal, 5 grosses Token, 4 Ziehen, 3 kleines Token,
    2 Plus mit Wert, 1 Plus ohne Wert. Verliehene Faehigkeiten wie beim Jace-Token (walker_rank, Lethal = 8)."""
    kinds = {a[0] for a in atoms}
    if "library_exile" in kinds:  # Jace, Reality Sculptor: ab 25 Loyalty auf unseren Jaces immer
        need = next(a[1] for a in atoms if a[0] == "library_exile")
        total = p.jace.loyalty + sum(x.loyalty for x in p.walkers if x.card.is_jace)
        return (7, 0, None) if total >= need and opp is not None and len(opp.library) > 1 else (0, 0, None)
    if "copy_next" in kinds:  # echte Planeswalker kopieren nur fuer Lethal oder Removal
        rank, tie = copy_rank(p, opp, pool, spells) if phase == "main1" else (0, 0)
        return (rank, tie, None) if rank >= 6 else (0, 0, None)
    life = opp.life if opp is not None else 99
    face = sum(a[1] for a in atoms if a[0] == "face")
    if face and face >= life:
        return 8, face, None
    if any(a[0] == "emblem" for a in atoms) or (cost != "X" and cost <= -6):
        cast_only = all(a[1] in ("cast_draw", "cast_damage") for a in atoms if a[0] == "emblem")             and any(a[0] == "emblem" for a in atoms)
        if not (cast_only and not any(not c.is_land for c in p.hand)):  # Emblem beim Wirken: nur mit Zauber auf der Hand
            return 7, 0, None
        return 0, 0, None
    if kinds & {"surveil", "draw", "token", "sac_token", "bolt", "face", "life", "counter_lands", "mana"} \
            and atoms in [g[1] for card in grant_sources(p) for g in card.walker_grants]:
        return _grant_rank(p, opp, cost, atoms, step, phase, pool, spells)
    alive = [c for c in p.creatures if not c.dead]
    theirs = [c for c in opp.creatures if not c.dead] if opp is not None else []
    if "team_pump" in kinds:
        pw_, tw = next(a[1:3] for a in atoms if a[0] == "team_pump")
        kw = next(a[3] for a in atoms if a[0] == "team_pump")
        if alive and _buffed_lethal(p, opp, step, pw_, tw, kw):
            return 8, 0, None
        return (2, 0, None) if any(not c.tapped for c in alive) else (1, 0, None)
    if "attack_buff" in kinds:
        pw_, tw = next(a[1:3] for a in atoms if a[0] == "attack_buff")
        return (8, 0, None) if alive and _buffed_lethal(p, opp, step, pw_, tw, ("trample",)) else (0, 0, None)
    if "bounce" in kinds:
        t = _bounce_target(p, opp)
        return (6,) + (danger(t), t) if t is not None else (0, 0, None)
    if "bolt_creature" in kinds:
        n = next(a[1] for a in atoms if a[0] == "bolt_creature")
        t = _kill_target(p, opp, n)
        return (6, danger(t), t) if t is not None else (0, 0, None)
    if "lasting_debuff" in kinds:
        _pw, tw = next(a[1:3] for a in atoms if a[0] == "lasting_debuff")
        t = _kill_target(p, opp, tw)
        if t is not None:
            return 6, danger(t), t
        cands = [c for c in theirs if not hexproof(c) and ward_ok(p, c) and c.power > 0]
        return (2, 0, max(cands, key=danger)) if cands else (1, 0, None)
    if "stun_x" in kinds:
        cands = [c for c in theirs if not hexproof(c) and ward_ok(p, c)]
        t = max(cands, key=danger) if cands else None
        if t is None or w.loyalty < 2:
            return 0, 0, None
        return (6, danger(t), t) if t.dmg >= 3 and w.loyalty >= 3 else (2, 0, t)
    if "sweep_except_tokens" in kinds:
        n = next(a[1] for a in atoms if a[0] == "sweep_except_tokens")
        dead_theirs = sum(c.card.mv + c.power for c in theirs if c.toughness - c.damage <= n)
        dead_ours = sum(c.card.mv + c.power for c in alive if not c.card.is_token and c.toughness - c.damage <= n)
        return (6, dead_theirs - dead_ours, None) if dead_theirs > dead_ours else (0, 0, None)
    if "edict_both" in kinds:
        if not theirs:
            return 0, 0, None
        if not alive or min(_value(c) for c in alive) <= min(_value(c) for c in theirs):
            return 6, 0, None
        return 0, 0, None
    if "token" in kinds:
        tok = next(a for a in atoms if a[0] == "token")
        stats = tok[1] * (tok[2].power + tok[2].toughness)
        return (5, stats, None) if stats >= 8 else (3, stats, None)
    if "draw" in kinds:
        return 4, next(a[1] for a in atoms if a[0] == "draw"), None
    if "opp_discard" in kinds:
        return (4, 0, None) if opp is not None and opp.hand else (0, 0, None)
    if "wheel_creatures" in kinds:
        n = len(alive) + sum(k for x in p.walkers for k, _t in x.card.activation_tokens)
        return (4, n - len(p.hand), None) if n > len(p.hand) else (0, 0, None)
    if "mana" in kinds:
        if phase == "main1" and pool is not None and spells is not None:
            extra = [a[1] for a in atoms if a[0] == "mana"]
            if best_cast_reduced(spells, land_key(pool + extra), True, True)[0] > \
                    best_cast_reduced(spells, land_key(pool), True, True)[0]:
                return 2, 3, None
        return (1, 0, None) if cost != "X" and cost >= 0 else (0, 0, None)
    if "face" in kinds:
        return 2, face, None
    if "surveil" in kinds:
        return (2, 0, None) if p.library else (1, 0, None)
    if "empower_islands" in kinds:
        n = sum("island" in land.land_types for land in p.lands)
        return (2, n, None) if n else (1, 0, None)
    if "shield" in kinds:
        return (2, 0, None) if sum(c.dmg for c in theirs) >= 3 else (0, 0, None)
    return (1, 0, None) if cost != "X" and cost >= 0 else (0, 0, None)


def _grant_rank(p, opp, cost, atoms, step, phase, pool, spells):
    """Verliehene Faehigkeit auf einem echten Planeswalker: Bewertung wie beim Jace-Token (walker_options)."""
    kinds = {a[0] for a in atoms}
    alive_opp = [c for c in opp.creatures if not c.dead] if opp is not None else []
    rank, tie = walker_rank(atoms, opp.life if opp is not None else 99, len(p.lands),
                            any(not c.dead for c in p.creatures), tokens=True)
    target = None
    if "bolt" in kinds and opp is not None:
        cdmg = next(a[1] for a in atoms if a[0] == "bolt")
        t = _kill_target(p, opp, cdmg)
        if rank < 7 and t is not None and t is max(alive_opp, key=danger):
            rank, target = 6, t
        elif rank == 7:
            target = t
    if "sac_token" in kinds:
        small = [c for c in p.creatures if not c.dead and c.power + c.toughness < 8]
        if not small:
            return 0, 0, None
        target = min(small, key=lambda c: (not c.card.is_token, c.power + c.toughness, c.card.mv))
        rank, tie = 5, 8
    if "mana" in kinds:
        if phase != "main1" or pool is None or spells is None:
            return (1, 0, None) if cost >= 0 else (0, 0, None)
        extra = [a[1] for a in atoms if a[0] == "mana"]
        if not best_cast_reduced(spells, land_key(pool + extra), True, True)[0] > \
                best_cast_reduced(spells, land_key(pool), True, True)[0]:
            return (1, 0, None) if cost >= 0 else (0, 0, None)
        rank, tie = 2, 3
    if rank == 7:
        rank = 8
    if rank <= 0 and cost >= 0:
        rank = 1
    return rank, tie, target


def pw_options(p, opp, w, step, phase, pool=None, spells=None):
    """Bewertete Faehigkeiten eines Planeswalkers, beste zuerst: (Rang, Gleichstand, Kosten, Effekte, Ziel).
    606.6: Minus-Kosten nur mit genug Loyalty; eine Minus-Faehigkeit, die ihn auf 0 bringt, nur fuer Lethal, Ultimate
    oder Removal (mit Sanctum Lurker stirbt er bei 0 nicht)."""
    if w.used or w not in p.walkers:
        return []
    no_death = any(c.walker_no_death for c in grant_sources(p))
    opts = []
    for cost, atoms in pw_abilities(p, w):
        real = _x_cost(w, cost)
        if real < 0 and w.loyalty < -real or (cost == "X" and real >= 0):
            continue
        rank, tie, target = pw_rank(p, opp, w, cost, atoms, step, phase, pool, spells)
        if rank <= 0:
            continue
        if w.loyalty + real <= 0 and rank < 6 and not no_death:
            continue
        opts.append((rank, (tie if isinstance(tie, tuple) else (tie,), real), cost, atoms, target))
    return sorted(opts, key=lambda o: (o[0], o[1]), reverse=True)


def pw_loyalty(p, w, n, e=None):
    """Loyalty-Marken auf einen echten Planeswalker; Inspired Tethermage bekommt ihre Marke."""
    if n <= 0:
        return
    w.loyalty += n
    for c in p.creatures:
        if c.card.loyalty_counter and not c.dead:
            c.bonus += c.card.loyalty_counter
    if e is not None:
        e["events"].append(f"{p.name}: {w.card.name} +{n} (Loyalty {w.loyalty})")


def activate_pw(p, opp, w, ability, step, e, target=None):
    """Fuehrt eine Loyalty-Faehigkeit eines echten Planeswalkers aus (Kosten zuerst, 606.4). Gibt Mana zurueck."""
    cost, atoms = ability
    real = _x_cost(w, cost)
    if target is None:
        target = pw_rank(p, opp, w, cost, atoms, step, "after")[2]
    if real > 0:
        pw_loyalty(p, w, real)
    else:
        w.loyalty += real
    w.used = True
    e["events"].append(f"{p.name}: {w.card.name} {'+' if real > 0 else ''}{real} (Loyalty {w.loyalty})")
    activation_tokens(p, step, e)
    alive_opp = (lambda: [c for c in opp.creatures if not c.dead]) if opp is not None else (lambda: [])
    if atoms in [g[1] for card in grant_sources(p) for g in card.walker_grants]:
        mana = _grant_atoms(p, opp, atoms, step, e, target)
        loyalty_triggers(p, real, e)
        bury((p, opp) if opp is not None else (p,), e)
        return mana
    mana, cast_top = [], False
    for a in atoms:
        kind = a[0]
        if kind == "token":
            make_tokens(p, [(a[1], a[2])], step, e, opp, w.card.name)
        elif kind == "bounce":
            if target is not None and target in alive_opp():
                pay_ward(p, target, e)
                opp.creatures.remove(target)
                if not target.card.is_token:
                    (target.owner or opp).hand.append(target.base_card or target.card)
                _leave(opp, target.card)
                check_auras(opp, e)
                e["events"].append(f"{p.name}: {w.card.name} – {target.label()} zurück auf die Hand")
        elif kind == "draw":
            _draw(p, a[1])
        elif kind == "counters_hand":
            for c in p.creatures:
                if not c.dead:
                    c.bonus += len(p.hand)
        elif kind == "attack_buff":
            p.attack_buff = (a[1], a[2], step)
        elif kind == "lasting_debuff":
            if target is not None and target in alive_opp():
                pay_ward(p, target, e)
                target.lasting.append((a[1], a[2], p, step))
                e["events"].append(f"{p.name}: {w.card.name} – {target.card.name} -{a[1]}/-{a[2]}")
        elif kind == "edict_both":
            mine = [c for c in p.creatures if not c.dead]
            theirs = alive_opp()
            if mine:
                min(mine, key=_value).dead = True
            if theirs:
                min(theirs, key=_value).dead = True
            bury((p, opp), e)
            if mine:
                make_tokens(p, [(1, a[1])], step, e, opp, w.card.name)
        elif kind == "opp_discard":
            if opp is not None:
                before = [c for c in opp.hand]
                discard(opp, a[1], e)
                gone = [c for c in before if c not in opp.hand]
                if sum(not c.is_land for c in gone) < 2:
                    _draw(p)
        elif kind == "life":
            gain_life(p, a[1])
        elif kind == "emblem":
            p.emblems.append(a[1:])
            e["events"].append(f"{p.name}: Emblem von {w.card.name}")
        elif kind == "team_pump":
            for c in p.creatures:
                if not c.dead:
                    c.pump += a[1]
                    c.tpump += a[2]
                    c.extra |= set(a[3])
        elif kind == "wheel_creatures":
            n = sum(1 for c in p.creatures if not c.dead)
            gone = list(p.hand)
            p.graveyard.extend(gone)
            p.hand.clear()
            if gone:
                discarded(p, e, gone)
            _draw(p, n)
        elif kind == "sweep_except_tokens":
            for c in p.creatures + (opp.creatures if opp is not None else []):
                if c.dead or (c in p.creatures and c.card.is_token):
                    continue
                c.damage += a[1]
            e["events"].append(f"{p.name}: {w.card.name} – {a[1]} Schaden an jeder Kreatur außer eigenen Token")
        elif kind == "surveil":
            surveil_cards(p, [a[1]], e, w.card.name)
        elif kind == "mana":
            mana.append(a[1])
        elif kind == "stun_x":
            if target is not None and target in alive_opp():
                pay_ward(p, target, e)
                target.tapped = True
                target.stun += -real
                e["events"].append(f"{p.name}: {w.card.name} – {target.card.name} getappt, {-real} Stun-Marken")
        elif kind == "mill_top":  # Chandra, Torch of Defiance: wirken statt Schaden
            cast_top = chandra_top(p, opp, w, step, e, sum(x[1] for x in atoms if x[0] == "face"))
        elif kind == "face":
            if not cast_top:
                deal_noncombat(p, opp, a[1], e)
        elif kind == "bolt_creature":
            if target is not None and target in alive_opp():
                pay_ward(p, target, e)
                target.damage += a[1]
        elif kind == "empower_islands":
            _jace_add(p, sum("island" in land.land_types for land in p.lands), e)
        elif kind == "shield":
            p.shield = (a[1], step)
        elif kind == "library_exile" and opp is not None:  # alle Karten bis auf die unterste ins Exil
            e["events"].append(f"{p.name}: {w.card.name} exiliert {len(opp.library) - 1} Karten der Bibliothek")
            opp.library = opp.library[-1:]
        elif kind == "copy_next":
            p.copy_next = step
            e["events"].append(f"{p.name}: der nächste Instant/Sorcery wird kopiert")
    loyalty_triggers(p, real, e)
    bury((p, opp) if opp is not None else (p,), e)
    return mana


def pw_phase(p, opp, step, e, phase, pool=None, spells=None):
    """Loyalty-Faehigkeiten echter Planeswalker: "main1" (vor den Zaubern, ausser Pumps fuer den Kampf), "combat"
    (nach den Zaubern aus Main 1, auch frisch gewirkte), "after" (nach Main 2). Gibt Mana zurueck."""
    mana = []
    for w in list(p.walkers):
        opts = pw_options(p, opp, w, step, phase, pool, spells)
        if not opts:
            continue
        best = opts[0]
        if phase == "main1" and {a[0] for a in best[3]} & PW_DEFER:
            continue
        mana += activate_pw(p, opp, w, (best[2], best[3]), step, e, best[4])
        if opp is not None and opp.life <= 0:
            break
    return mana


def walker_check(p, e):
    """704.5i: ein Planeswalker mit 0 Loyalty kommt in den Friedhof (mit Sanctum Lurker nicht)."""
    if not p.walkers or any(c.walker_no_death for c in grant_sources(p)):
        return
    for w in list(p.walkers):
        if w.loyalty <= 0:
            w.loyalty = 0
            p.walkers.remove(w)
            if not w.card.is_token:
                p.graveyard.append(w.card)
            walker_died(p, w.card.name, e)


def chandra_top(p, opp, w, step, e, face):
    """Chandra, Torch of Defiance +1: die oberste Karte ins Exil. Wir wirken sie mit dem freien Mana, wenn sie kein Land
    ist (und ein Ziel hat) - ausser der Schaden (face) ist Lethal. Gibt True zurueck, wenn sie gewirkt wurde (dann kein
    Schaden)."""
    if not p.library:
        return False
    top = p.library.pop(0)
    e["events"].append(f"{p.name}: {w.card.name} exiliert {top.name}")
    if opp is None or opp.life <= face or top.is_land or not legend_ok(p, top) or not reanimate_ok(p, top)             or (top.removal and top.removal[4] != "etb" and not has_target(top, p, opp)):
        return False
    if not _pay_open(p, _alts(p, top), treasure=False):
        return False
    e["events"].append(f"{p.name}: wirkt {top.name} aus dem Exil ({w.card.name})")
    p.cast_count += 1
    _resolve(p, opp, top, step, e)
    return True


def pw_target(card, caster, victim, creature_target):
    """Removal "creature or planeswalker": ein echter Planeswalker, wenn es ihn toetet und der Gegner keine Kreatur mit
    Power 4+ hat (hoechster Manawert zuerst); der Jace-Token nur ab 5 Loyalty und ohne Kreatur als Ziel. Gibt einen
    Walker, "jace" oder None zurueck."""
    spec = card.removal
    if not card.hits_walkers or not spec or spec[0] not in ("destroy", "damage"):
        return None
    amount = _amount(spec, caster)
    kill = [w for w in victim.walkers if w.loyalty > 0 and (spec[0] == "destroy" or amount >= w.loyalty)]
    if kill and not any(c.power >= 4 for c in victim.creatures if not c.dead):
        return max(kill, key=lambda w: (w.card.mv, w.loyalty))
    if creature_target is None and jace_present(victim) and victim.jace.loyalty >= 5:
        return "jace"
    return None


def entrust_pick(p):
    """Entrust the Spark: Planeswalker-Karte aus der Bibliothek mit dem hoechsten Manawert, die nicht an der
    Legend-Regel scheitert; None, wenn es keine gibt oder kein Jace-Token zum Opfern da ist."""
    if not jace_present(p):
        return None
    cands = [c for c in p.library if c.is_planeswalker and legend_ok(p, c)]
    return max(cands, key=lambda c: (c.mv, c.loyalty_start, c.name)) if cands else None


def tutor_pick(p):
    """Loyal Tutor: ohne Planeswalker auf der Hand der teuerste Planeswalker der Bibliothek, den wir naechste Runde
    bezahlen koennen (Manawert hoechstens Laender + 1), sonst der billigste; None ohne Planeswalker in der Bibliothek."""
    if any(c.is_planeswalker for c in p.hand):
        return None
    cands = [c for c in p.library if c.is_planeswalker]
    if not cands:
        return None
    ok = [c for c in cands if c.mv <= len(p.lands) + 1]
    return max(ok, key=lambda c: (c.mv, c.name)) if ok else min(cands, key=lambda c: (c.mv, c.name))


def entrust_spark(p, opp, step, e):
    """Opfert den Jace-Token (er stirbt, 700.4) und bringt den gewaehlten Planeswalker aufs Feld, dann mischen."""
    pick = entrust_pick(p)
    if pick is None:
        return
    p.jace.loyalty, p.jace.zero_alive = 0, False
    e["events"].append(f"{p.name}: opfert den Jace-Token")
    jace_died(p, e)
    p.library.remove(pick)
    random.shuffle(p.library)
    e["events"].append(f"{p.name}: Entrust the Spark – {pick.name} aufs Feld")
    if pick.loyalty_start > 0:
        p.walkers.append(Walker(pick, step))
    else:
        p.perms.append(pick)
    permanent_enters(p, opp, pick, step, e)


def loyal_tutor(p, e):
    pick = tutor_pick(p)
    if pick is None:
        return
    p.library.remove(pick)
    random.shuffle(p.library)
    p.library.insert(0, pick)
    e["events"].append(f"{p.name}: Loyal Tutor – {pick.name} oben auf die Bibliothek")


def hit_walker(caster, victim, card, target, e):
    """Removal trifft einen Planeswalker: Zerstoeren oder Schaden (120.3c)."""
    spec = card.removal
    if target == "jace":
        before = victim.jace.loyalty
        victim.jace.loyalty = 0 if spec[0] == "destroy" else max(0, before - _amount(spec, caster))
        e["events"].append(f"{caster.name}: {card.name} trifft Jace von {victim.name} (Loyalty {victim.jace.loyalty})")
        _jace_zero(victim, before, e)
        return
    if spec[0] == "destroy":
        target.loyalty = 0
    else:
        target.loyalty = max(0, target.loyalty - _amount(spec, caster))
    e["events"].append(f"{caster.name}: {card.name} trifft {target.card.name} von {victim.name} "
                       f"(Loyalty {target.loyalty})")
    bury((caster, victim), e)


def expire_until_next_turn(p, step):
    """Zu Beginn des eigenen Zugs enden "until your next turn"-Effekte von p (611.2b)."""
    if p.attack_buff is not None and step > p.attack_buff[2]:
        p.attack_buff = None
    if p.shield is not None and step > p.shield[1]:
        p.shield = None
    if p.opponent is not None:
        for c in p.opponent.creatures:
            c.lasting = [d for d in c.lasting if d[2] is not p or step <= d[3]]


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
        if go and copy_waits(p):
            go = False
    elif phase == "main1":
        go = best[0] >= 6 or bool(kinds & {"mana", "counter_lands", "copy_next"}) or any(c.kiora_attack
                                                                                       for c in sources)
    else:
        go = True
    return activate_walker(p, opp, step, e, best) if go else []


def copy_waits(p):
    """Mit Way of the Cryomancer und einem Instant/Sorcery auf der Hand wartet der Jace-Token bis Main 1 (dort wird
    zwischen Ziehen und Kopieren gewaehlt)."""
    return bool(_copy_abilities(p)) and any(c.is_instant_sorcery for c in p.hand)


def _jace_activate(p, step, e, allow_surveil):
    loyalty, lands = p.jace.loyalty, p.jace.surveil_lands
    if p.jace.try_activate(p.hand, p.library, step, battlefield=p.lands, allow_surveil=allow_surveil):
        activation_tokens(p, step, e)
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
    victim.noncombat_step = victim.now
    src.dealt_direct += amount
    for c in src.creatures:  # Killian: Seek eine Karte mit Manawert = Schaden, im naechsten Endsegment abwerfen
        if c.card.noncombat_seek and not c.dead:
            cands = [x for x in src.library if x.mv == amount]
            if cands:
                pick = random.choice(cands)
                src.library.remove(pick)
                src.hand.append(pick)
                src.seek_discard.append(pick)
                e["events"].append(f"{src.name}: {c.card.name} – Seek {pick.name}")
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
        for c in p.creatures:  # Dina, Flesh Sower
            if c.card.lifegain_perpetual and not c.dead:
                perpetual_pump(c, c.card.lifegain_perpetual, c.card.lifegain_perpetual)
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
            if c.card.lifegain_lotus and not c.dead and c.once.get("lotus") != p.now:  # Kwia: einmal pro Zug
                c.once["lotus"] = p.now
                artifact_tokens(p, LOTUS, 1, p.now, {"events": []})
            if c.card.lifegain_draw and c.once.get("lifegain") != p.now:  # Bloombrute: einmal pro Zug
                c.once["lifegain"] = p.now
                _draw(p, c.card.lifegain_draw)
        loyalty = sum(c.lifegain_loyalty for c in p.perms) + sum(c.card.lifegain_loyalty for c in p.creatures)
        if loyalty and jace_present(p):  # Way of the Mentor: nur auf einen vorhandenen Jace
            _jace_add(p, loyalty)
        for w in list(p.walkers):  # Way of the Mentor auf jeden Planeswalker, Ajani Resolute auf sich selbst
            pw_loyalty(p, w, loyalty + ("lifegain_loyalty" in w.card.pw_static))


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


def emblem_cast(p, step, e):
    """Embleme "whenever you cast a spell": eine Karte ziehen (Chandra, Chill of Compliance) bzw. 5 Schaden an ein
    beliebiges Ziel (Chandra, Torch of Defiance): Lethal an den Gegner, sonst die gefaehrlichste Kreatur, die stirbt,
    sonst an den Gegner."""
    opp = p.opponent
    for em in list(p.emblems):
        if em[0] == "cast_draw":
            _draw(p)
        elif em[0] == "cast_damage" and opp is not None:
            n = em[1]
            t = None if opp.life <= n else _kill_target(p, opp, n)
            if t is None:
                deal_noncombat(p, opp, n, e)
            else:
                t.damage += n
                e["events"].append(f"{p.name}: Emblem – {n} Schaden an {t.card.name}")
                bury((p, opp), e)


def on_cast(p, card, step, e):
    """Ein Zauber wurde gewirkt: Jace-Ausloeser, Marken fuer Zauber mit Ziel beim Gegner (Danitha)."""
    _jace_on_cast(p, card, step, e)
    if card.is_planeswalker:  # Sparks Ablaze: der Rabatt gilt nur fuer den naechsten Planeswalker
        p.next_pw = 0
    if card.hand_exile_land and p.cc_land is not None and not any(c == card for c, _l in p.impulse):
        p.cc_land = None  # aus dem Exil gewirkt: das Land liefert wieder nur sein Mana
    if p.emblems:
        emblem_cast(p, step, e)
    if card.is_creature:  # Flickering Hound: eine andere eigene Kreatur blinken (wertvollster Betreten-Effekt)
        for h in list(p.creatures):
            if h.card.cast_blink and not h.dead:
                cands = [c for c in p.creatures if c is not h and not c.dead and not c.card.is_token
                         and not (c.entered == step and c.card == card) and etb_rank(c.card) > 0]
                if cands:
                    t = max(cands, key=lambda c: (etb_rank(c.card), c.card.mv))
                    blink(p, t, step, e, h.card.name)
    if card.is_artifact or card.is_creature:  # Traxos
        for c in p.creatures:
            if c.card.untap_on_cast and not c.dead:
                c.tapped = False
    if card.equip or (not card.removal and (card.is_instant_sorcery or card.is_aura) and any(
            a[0] in ("pump", "counter") for m in card.modes for a in m)):
        for c in p.creatures:  # Danitha, Sword of Hope: einmal pro Zug
            if c.card.own_target_draw and not c.dead and c.once.get("own_target") != p.now:
                c.once["own_target"] = p.now
                _draw(p)
                e["events"].append(f"{p.name}: {c.card.name} zieht")
    foe = p.opponent
    if foe is not None:
        for c in foe.creatures:  # Solarium Sentry
            if c.card.opp_cheap_cast_life and not c.dead and card.mv <= c.card.opp_cheap_cast_life[0]:
                gain_life(foe, c.card.opp_cheap_cast_life[1])
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
    cast_triggers(p, card, step, e)


def targets_creature(card):
    """Hat der Zauber eine Kreatur als Ziel (Repartee)? Removal mit Kreatur-Ziel (nicht "any target", kein Edikt
    oder Massenremoval), Pumps, Marken, -N/-0 und verliehene Schluesselwoerter auf "target creature"."""
    spec = card.removal
    if spec and spec[0] not in ("sweep", "sweep_damage", "edict") and not spec[3]:
        return True
    return targets_own_creature(card) or bool(card.debuff)


def targets_own_creature(card):
    """Zauber, den wir auf eine eigene Kreatur wirken: Pump, Marke oder Schluesselwort auf "target creature"."""
    if card.removal or not (card.is_instant_sorcery or card.is_aura):
        return False
    return bool(card.grant_kw) or any(a[0] in ("pump", "counter") for m in card.modes for a in m)


_COLOR_WORDS = {"white": "W", "blue": "U", "black": "B", "red": "R", "green": "G"}
_TYPE_FLAGS = {"artifact": "is_artifact", "enchantment": "is_enchantment", "instant": "is_instant",
               "planeswalker": "is_planeswalker", "legendary": "legendary", "creature": "is_creature"}


def cast_matches(kind, card):
    """Passt der gewirkte Zauber zum Filter eines Ausloesers? "type:<Wort>": Farbe, Kartentyp oder Kreaturtyp
    ("Whenever you cast a Villain spell")."""
    if kind.startswith("type:"):
        word = kind[5:]
        if word in _COLOR_WORDS:
            return _COLOR_WORDS[word] in colors_of_alts(card.alts)
        if word in _TYPE_FLAGS:
            return bool(getattr(card, _TYPE_FLAGS[word]))
        return word in card.creature_types
    return _CAST_FILTERS[kind](card)


_CAST_FILTERS = {
    "instsorc": lambda c: c.is_instant_sorcery,
    "instsorc_creature": lambda c: c.is_instant_sorcery and targets_creature(c),
    "noncreature": lambda c: not c.is_creature,
    "creature": lambda c: c.is_creature,
    "own_creature": targets_own_creature,
    "multicolor": lambda c: len(colors_of_alts(c.alts)) >= 2,
    "spell": lambda c: True,
}


def mana_spent(p, card):
    """Fuer den Zauber ausgegebenes Mana (Opus): die billigste Bezahlung nach Kostensenkung."""
    alts = _alts(p, card) or card.alts
    return min((g + sum(n for _c, n in cols) for g, cols in alts), default=0)


def cast_triggers(p, card, step, e):
    """Ausloeser "Whenever you cast ..." eigener Kreaturen und Permanents (Card.cast_trig). Opus: ab 5 ausgegebenem
    Mana die grossen Effekte statt ("instead") bzw. zusaetzlich ("also")."""
    spent = None
    if card.is_instant_sorcery:
        for x in p.perms:  # Aria of Flame: Vers-Marke, dann Schaden in Hoehe der Marken an den Gegner
            if isinstance(x, Card) and x.verse and p.opponent is not None:
                p.verse[id(x)] = p.verse.get(id(x), 0) + 1
                deal_noncombat(p, p.opponent, p.verse[id(x)] + (1 if red_bonus(p, x) else 0), e)
    for src, source in static_sources(p):
        for kind, atoms, big, mode in source.cast_trig:
            if not cast_matches(kind, card):
                continue
            if big or any("spent" in a for a in atoms):
                spent = mana_spent(p, card) if spent is None else spent
            if big and spent >= 5:
                atoms = big if mode == "instead" else atoms + big
            atoms = tuple(tuple(spent if x == "spent" else card.mv if x == "mv" else x for x in a) for a in atoms)
            cast_effects(p, src, source, atoms, step, e)


def cast_effects(p, src, source, atoms, step, e):
    """Effekte eines Ausloesers beim Wirken; src: die ausloesende Kreatur (None bei Nichtkreatur-Permanents)."""
    opp = p.opponent
    alive = [c for c in p.creatures if not c.dead]
    for atom in atoms:
        kind = atom[0]
        if kind in ("pump", "kw", "counter", "unblockable") and src is None:
            continue
        if kind == "pump":
            src.pump += atom[1]
            src.tpump += atom[2]
        elif kind == "kw":
            src.extra |= set(atom[1])
        elif kind == "unblockable":
            src.extra.add("unblockable")
        elif kind == "counter":
            src.bonus += atom[1]
        elif kind == "counter_all":
            for c in alive:
                c.bonus += atom[1]
        elif kind == "counter_others":
            for c in alive:
                if c is not src:
                    c.bonus += atom[1]
        elif kind == "target_counter":
            pick = buff_target(p, step)
            if pick is not None:
                pick.bonus += atom[1]
        elif kind == "team_pump":
            for c in alive:
                c.pump += atom[1]
                c.tpump += atom[2]
        elif kind == "face" and opp is not None:
            deal_noncombat(p, opp, atom[1], e)
        elif kind == "bolt" and opp is not None and atom[1] > 0:  # "any target": Regel wie bei Removal-Schaden
            cast_removal(source._replace(removal=("damage", atom[1], (), True, "spell", False), empower_x=""),
                         p, opp, e, step)
        elif kind == "drain" and opp is not None:
            opp.life -= atom[1]
            gain_life(p, atom[2])
        elif kind == "draw":
            _draw(p, atom[1])
        elif kind == "discard":
            for _k in range(atom[1]):
                gone = choose_discard(p)
                if gone is not None:
                    p.hand.remove(gone)
                    p.graveyard.append(gone)
                    discarded(p, e, [gone])
        elif kind == "token":
            make_tokens(p, [(atom[1], atom[2])], step, e, opp, source.name)
        elif kind == "surveil":
            surveil_cards(p, [atom[1]], e, source.name)
        elif kind == "base_power":  # Asymmetry Sage: die eigene Kreatur, die am meisten gewinnt (Angreifer zuerst)
            gain = [c for c in alive if c.card.power < atom[1]]
            ready = lambda c: not c.tapped and not c.card.defender and (c.entered < step or c.has("haste"))
            pick = (max(gain, key=lambda c: (ready(c), atom[1] - c.card.power)) if gain
                    else max(alive, key=lambda c: atom[1] - c.card.power, default=None))
            if pick is not None:
                pick.pump += atom[1] - pick.card.power
    e["events"].append(f"{p.name}: {source.name} – Auslöser beim Wirken")


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


def _redundant_land(p, lands=None):
    """Land, das am wenigsten fehlt: farblos zuerst, sonst das Land, dessen Farben am haeufigsten vorkommen; bei
    Gleichstand ein getapptes Land, dann ein Basic Land."""
    lands = p.lands if lands is None else lands
    count = Counter(col for land in lands for col in set(land.land_colors))
    tapped = _tapped_lands(p)
    return max(lands, key=lambda land: (min((count[c] for c in land.land_colors), default=99),
                                          tapped[land.land_colors] > 0, land.is_basic))


def creature_enters(p, new, step, e, opp=None, cast=True):
    """Eine Kreatur kam ins Spiel (schon in p.creatures): Leben (Greenhouse Propagator), Marken auf eine Kreatur, die
    in diesem Zug kam (Mabel), Team-Pump nach Artefakten (Craterclaw Colossus), Land gegen Token (Tenured
    Tethermage), Mill und Land zurueck (Primal Witchstalker), Exil aus der Hand des Gegners (Null Summoner, nur wenn
    gewirkt)."""
    card = new.card
    new.gy, new.ctl = p.graveyard, p
    new.bonus += card.enters_counters  # "enters with N +1/+1 counters" (614.1c)
    if card.x_counters:  # "enters with X +1/+1 counters" (Guiding Hydra), X beim Wirken festgelegt
        for i, (xc, xv) in enumerate(p.x_values):
            if xc == card:
                new.bonus += xv
                del p.x_values[i]
                break
    x, p.next_x = p.next_x, 0  # X des gewirkten Zaubers (107.3m); sonst 0
    if no_enter_triggers(p):  # Karn, Argent Defender: keine Ausloeser beim Betreten (Ersatzeffekte gelten)
        new.lifted = p.surveilled and new.card.surveil_attack
        return
    if card.x_search_basics and x:
        search_basics(p, x, e, card.name)
    if card.uldaros_cast and cast and opp is not None:
        uldaros_copies(p, opp, card, step, e)
    if card.etb_conjure:  # Searing Soloist: Aria of Flame aufs Feld
        made = conjure(card.etb_conjure)
        if made is not None:
            e["events"].append(f"{p.name}: {card.name} – {made.name} beschworen")
            if made.is_creature:
                fresh = Creature(made, step)
                p.creatures.append(fresh)
                creature_enters(p, fresh, step, e, opp, cast=False)
            else:
                p.perms.append(made)
                permanent_enters(p, opp if opp is not None else p.opponent, made, step, e)
    if card.equip_token:  # Equipment-Token (Iron Hills Blacksmith, U.S.Agent, Dain Ironfoot)
        token, attach = card.equip_token
        p.perms.append(token)
        e["events"].append(f"{p.name}: {card.name} – Equipment-Token {token.name}")
        host = new if attach == "self" else gear_host(p, step) if attach == "target" else None
        if host is not None and not host.dead:
            attach_gear(p, token, host, e)
    if card.etb_grant:  # Teyo: Ziel vorgegeben (Antwort, Kampf) oder die gefaehrlichste eigene Kreatur, auch er selbst
        t, p.grant_target = p.grant_target, None
        if t != "done":
            alive = [c for c in p.creatures if not c.dead]
            t = t if t is not None and t in alive else max(alive, key=danger)
            t.extra |= set(card.etb_grant)
            t.bonus += 1
            e["events"].append(f"{p.name}: {card.name} – {t.card.name} bekommt {', '.join(card.etb_grant)} und eine Marke")
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
        if c is not new and c.card.ally_enter_mill:  # Liliana the Repentant
            _mill(p, c.card.ally_enter_mill, e, c.card.name)
    if card.etb_loot_stun:  # Seasoned Cryomancer: 2 ziehen, 2 abwerfen, Stun je Nichtland-Karte
        _draw(p, 2)
        gone = []
        for _k in range(2):
            pick = choose_discard(p)
            if pick is None:
                break
            p.hand.remove(pick)
            p.graveyard.append(pick)
            gone.append(pick)
        if gone:
            discarded(p, e, gone)
        foe = opp if opp is not None else p.opponent
        n = sum(not c.is_land for c in gone)
        cands = sorted((c for c in (foe.creatures if foe is not None else []) if not c.dead and not hexproof(c)
                        and ward_ok(p, c)), key=danger, reverse=True)[:n]
        for t in cands:
            pay_ward(p, t, e)
            t.tapped = True
            t.stun += 1
        e["events"].append(f"{p.name}: {card.name} wirft {len(gone)} ab, Stun auf {len(cands)}")
    if card.etb_tutor_any and p.library:  # Curse-Marred Demon: nie ein Land; dann zufaellig abwerfen
        spells = [c for c in p.library if not c.is_land]
        ok = [c for c in spells if c.mv <= len(p.lands) + 1]
        pick = max(ok, key=lambda c: (c.mv, c.name)) if ok else (min(spells, key=lambda c: (c.mv, c.name))
                                                                  if spells else None)
        if pick is not None:
            p.library.remove(pick)
            random.shuffle(p.library)
            p.hand.append(pick)
            e["events"].append(f"{p.name}: {card.name} sucht {pick.name}")
        if p.hand:
            gone = random.choice(p.hand)
            p.hand.remove(gone)
            p.graveyard.append(gone)
            e["events"].append(f"{p.name}: wirft zufällig {gone.name} ab")
            discarded(p, e, [gone])
    if card.etb_discard_enchant:  # Pia: ein Land abwerfen, eine Verzauberung fuer den naechsten Zug suchen
        lands = [c for c in p.hand if c.is_land]
        ench = [c for c in p.library if c.is_enchantment and c.mv <= len(p.lands) + 1]
        if lands and ench and len(p.lands) > p.max_deck_mv:
            gone = lands[0]
            p.hand.remove(gone)
            p.graveyard.append(gone)
            discarded(p, e, [gone])
            pick = max(ench, key=lambda c: (c.mv, c.name))
            p.library.remove(pick)
            random.shuffle(p.library)
            p.hand.append(pick)
            e["events"].append(f"{p.name}: {card.name} wirft {gone.name} ab, sucht {pick.name}")
    if card.etb_basic_tapped:  # Simulacrum Shaper: Basic Land getappt aufs Feld (Auswahl wie search_basics)
        have = set().union(*(c.land_colors for c in p.lands)) if p.lands else set()
        basics = [c for c in p.library if c.is_basic]
        if basics:
            count = Counter(c.name for c in basics)
            pick = max(basics, key=lambda c: (len(set(c.land_colors) - have), count[c.name], c.name))
            p.library.remove(pick)
            random.shuffle(p.library)
            p.lands.append(pick)
            e["events"].append(f"{p.name}: {card.name} sucht {pick.name} (getappt)")
            if opp is not None or p.opponent is not None:
                on_land(p, opp if opp is not None else p.opponent, pick, step, e, with_mana=False)
    if card.etb_artifact_colors_draw:  # Karn, Gilded Guardian
        arts = [c for c in p.perms if c.is_artifact] + [c.card for c in p.creatures if c is not new and not c.dead
                                                         and c.card.is_artifact]
        n = len(set().union(*(colors_of_alts(c.alts) for c in arts))) if arts else 0
        if n:
            _draw(p, n)
            e["events"].append(f"{p.name}: {card.name} zieht {n}")
    if card.etb_stun_opp:  # Hapatra, the Desert Frost
        foe = opp if opp is not None else p.opponent
        cands = [c for c in (foe.creatures if foe is not None else []) if not c.dead and not hexproof(c)
                 and ward_ok(p, c)]
        if cands:
            t = max(cands, key=danger)
            pay_ward(p, t, e)
            t.tapped = True
            t.stun += 1
            e["events"].append(f"{p.name}: {card.name} tappt {t.card.name} (Stun-Marke)")
    if card.etb_remove_counters:  # Mabel, Bitter Recluse
        remove_counters(p, opp if opp is not None else p.opponent, card.etb_remove_counters, card.name, e)
    if new.power >= 4 and not new.dead:  # Garruk, Curse Breaker
        for w in p.walkers:
            if "big_enter_draw" in w.card.pw_static:
                _draw(p)
                e["events"].append(f"{p.name}: {w.card.name} – zieht für {new.card.name}")
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
    walkers = [c for c in p.perms if c.is_planeswalker] + [w.card for w in p.walkers]
    return jace_present(p) or bool(walkers), jace_present(p) or any(c.is_jace for c in walkers)


def surveil_cards(p, amounts, e, source):
    amounts = [a for a in amounts if a]
    if not amounts:
        return
    before = len(p.graveyard)
    events, _lands = apply_surveils(amounts, p.library, p.hand, p.lands, graveyard=p.graveyard)
    binned = len(p.graveyard) - before
    if binned:
        library_to_graveyard(p)
    e["events"].append(f"{p.name}: {source} – Surveil {sum(amounts)}" + (f" ({binned} abgelegt)" if binned else ""))
    mark_surveil(p, e, max(1, events))


def on_land(me, opp, land, step, e, with_mana=True):
    """Ein Land kommt ins Spiel: Landfall, Surveil des Landes, Jace-Ausloeser. Gibt zusaetzliches Mana zurueck."""
    mana = []
    if "forest" in land.land_types:  # Roiling Canopy: mindestens 5 andere Forests
        others = sum("forest" in x.land_types for x in me.lands) - (1 if land in me.lands else 0)
        alive = [c for c in me.creatures if not c.dead]
        for src in me.lands:
            if src.forest_pump and others >= 5 and alive:
                pick = max(alive, key=lambda c: (can_attack(c, step), danger(c)))
                pick.pump += src.forest_pump
                pick.tpump += src.forest_pump
                e["events"].append(f"{me.name}: {src.name} – {pick.card.name} +{src.forest_pump}/+{src.forest_pump}")
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
    if p.no_legend_step == p.now:  # Hall of Echoes: "The legend rule doesn't apply ... this turn"
        return
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
    names = {}
    for w in p.walkers:
        names.setdefault(w.card.name, []).append(w)
    for same in names.values():
        if len(same) > 1:
            keep = max(same, key=lambda w: (w.loyalty, -w.entered))
            for w in same:
                if w is not keep:
                    p.walkers.remove(w)
                    p.graveyard.append(w.card)
                    e["events"].append(f"{p.name}: Legend-Regel – {w.card.name} in den Friedhof")
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
                or any(c.name == card.name for c in p.perms) or any(w.card.name == card.name for w in p.walkers))


def is_dying(c):
    """Stirbt die Kreatur (704.5f/g/h)? Indestructible (702.12b): toedlicher Schaden und Deathtouch zerstoeren sie
    nicht; Toughness 0 oder weniger, Opfern und Zerstoeren-Effekte, die sie schon markiert haben, schon."""
    if c.dead or c.toughness <= 0:
        return True
    return (c.damage >= c.toughness or (c.touched and c.damage > 0)) and not c.has("indestructible")


def bury(players, e):
    """Gestorbene Kreaturen in den Friedhof (Schaden, Deathtouch, Toughness 0) und Legend-Regel. Danach Ausloeser fuer
    gestorbene eigene Kreaturen (Massacre Girl; sie sieht auch Tode im selben Moment wie ihren eigenen, 603.10a)."""
    for p in players:
        legend_rule(p, e)
    triggers = []  # erst alle gleichzeitig sterben lassen (704.3), dann die Ausloeser
    copies_made, returns = [], []
    for p in players:  # Invigorator, der in diesem Moment stirbt, loest trotzdem aus
        for c in p.creatures:
            if c.ramp_pending and (c.dead or c.damage >= c.toughness):
                damage_ramp(p, c.ramp_pending, e)
                c.ramp_pending = 0
    for p in players:
        if p.opponent is not None and any(w.card.opp_exile_instead for w in p.opponent.walkers):
            continue  # Garruk, Veiled Butcher: nichts stirbt
        watchers = [c for c in p.creatures if c.card.ally_death_ping or c.card.ally_death_life]
        dying = [c for c in p.creatures
                 if is_dying(c)]
        triggers += [(p, w.card.ally_death_ping or (0, 0), w.card.ally_death_life) for w in watchers for d in dying
                     if d is not w]
        loyalty = sum(c.death_loyalty for c in p.perms) + sum(c.card.death_loyalty for c in p.creatures)
        if loyalty:  # Way of the Necromancer: je gestorbene eigene Kreatur Loyalty auf einen vorhandenen Jace
            triggers += [(p, "loyalty", loyalty)] * len(dying)
    moves = []  # Graft Surgeon: Marken auf eine eigene Kreatur, die ueberlebt
    for p in players:
        exile_instead = p.opponent is not None and any(w.card.opp_exile_instead for w in p.opponent.walkers)
        for c in list(p.creatures):
            if exile_instead and is_dying(c):
                p.creatures.remove(c)  # Garruk, Veiled Butcher: exiliert statt zu sterben, kein "dies" (614.6)
                _leave(p, c.card)
                e["events"].append(f"{p.name}: {c.card.name} ins Exil (statt zu sterben)")
                continue
            if is_dying(c):
                if c.card.death_counters_move and c.bonus > 0:
                    moves.append((p, c.bonus, c.card.name))
                p.deaths += 1
                p.creatures.remove(c)
                if c.land_source is not None:  # Hall of Echoes: das Land stirbt
                    if c.land_source in p.lands:
                        p.lands.remove(c.land_source)
                    p.graveyard.append(c.land_source)
                elif c.base_card is not None:  # Puppet Crafting: die Artefakt-Karte (Token verschwinden)
                    if not c.base_card.is_token:
                        p.graveyard.append(c.base_card)
                elif not c.card.is_token and not c.finality:
                    (c.owner or p).graveyard.append(c.card)
                if any(a.aura_return for a in c.auras) and not c.card.is_token and c.land_source is None:
                    returns.append((c.owner or p, c.card))  # Ferocity of the Hunt
                if c.card.death_draw:  # Simulacrum Shaper
                    _draw(p, c.card.death_draw)
                if any(x.charge_on_death for x in p.perms):  # Gardenize
                    p.charges += sum(1 for x in p.perms if x.charge_on_death)
                if c.card.death_token_copy and not c.card.is_token:  # Sphinx of False Conclusions (707.2, 111.10)
                    copies_made.append((p, c.card._replace(is_token=True)))
                if c.card.death_heartwood:  # Aerid Konstrari: ungetappt, sofort offenes Mana (kein 302.6)
                    if artifact_tokens(p, HEARTWOOD, c.card.death_heartwood, p.now, e):
                        p.open += list(HEARTWOOD.mana_src) * c.card.death_heartwood
                _leave(p, c.card)
                gain_life(p, c.card.death_life)
                e["deaths"].append(f"{c.card.name} ({p.name})")
    for owner, card in returns:  # Ferocity of the Hunt: getappt zurueck (neues Objekt)
        if card in owner.graveyard:
            owner.graveyard.remove(card)
            put_back(owner, card, "battlefield", owner.now, e, owner.opponent, tapped=True)
    for p in players:  # Hexhaven Invigorator: Laender fuer erhaltenen Schaden
        for c in list(p.creatures):
            if c.ramp_pending:
                damage_ramp(p, c.ramp_pending, e)
                c.ramp_pending = 0
    for p, card in copies_made:
        new = Creature(card, p.now)
        p.creatures.append(new)
        creature_enters(p, new, p.now, e, p.opponent, cast=False)
        e["events"].append(f"{p.name}: Token-Kopie von {card.name}")
    for p, ping, extra in triggers:  # Massacre Girl, Edgar, Way of the Necromancer
        if ping == "loyalty":
            if jace_present(p):
                _jace_add(p, extra, e)
            for w in p.walkers:  # "each planeswalker you control"
                pw_loyalty(p, w, extra, e)
            continue
        dmg, life = ping
        deal_noncombat(p, p.opponent, dmg, e)
        gain_life(p, life + extra)
    for p in players:
        check_auras(p, e)
        walker_check(p, e)
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
    """704.5m: eine eigene Aura (Splinter Twin), deren Kreatur nicht mehr da ist, kommt in den Friedhof; ebenso eine
    Lock-Aura (eigene oder des Gegners), deren Kreatur das Spielfeld verlassen hat."""
    for q in (p, p.opponent):
        if q is None:
            continue
        for link in list(q.lock_links):
            holder = link["creature"].ctl
            if holder is None or link["creature"] not in holder.creatures or link["creature"].dead:
                q.lock_links.remove(link)
                if link["aura"] in q.perms:
                    q.perms.remove(link["aura"])
                    q.graveyard.append(link["aura"])
                    if e is not None:
                        e["events"].append(f"{q.name}: {link['aura'].name} in den Friedhof (keine Kreatur mehr)")
    attached = Counter(a for c in p.creatures for a in c.auras)
    for card in list(p.perms):
        if not (card.twin or ((card.aura_pump or card.aura_kw or card.animate_artifact) and card.is_aura)):
            continue
        if attached[card] > 0:
            attached[card] -= 1
            continue
        p.perms.remove(card)
        p.graveyard.append(card)
        if e is not None:
            e["events"].append(f"{p.name}: {card.name} in den Friedhof (keine Kreatur mehr)")


def noncreature_targets(caster, victim, allowed):
    """Nichtkreatur-Permanents von victim als Ziel, beste zuerst: [(Rang, Gleichstand, Ziel)]. Ziel ist ein Eintrag
    aus trap_links (Falle) oder die Karte. Rang 1: Falle mit einer unserer Karten, 2: Lock-Aura auf unserer Kreatur,
    3: Splinter Twin oder Ausruestung an seiner Kreatur, 4: sonstige Verzauberungen/Artefakte (Way of ... vor anderen,
    dann Manawert). Token nie. allowed: "artifact_enchantment" (ohne Planeswalker) oder "noncreature"/"nonland"."""
    out, used = [], Counter()

    def ok(card):
        return not card.is_token and (allowed != "artifact_enchantment" or not card.is_planeswalker)

    for link in victim.trap_links:
        if link["owner"] is caster and ok(link["trap"]) and not link["card"].is_token:
            out.append((1, (link["card"].mv,), link))
            used[link["trap"]] += 1
    for link in victim.lock_links:
        if link["creature"] in caster.creatures and ok(link["aura"]):
            out.append((2, (link["creature"].card.mv,), link["aura"]))
            used[link["aura"]] += 1
    for c in victim.creatures:
        for a in list(c.auras) + list(c.gear):
            if ok(a):
                out.append((3, danger(c), a))
                used[a] += 1
    rest = Counter(victim.perms)
    rest.subtract(used)
    for card, n in rest.items():
        if n > 0 and ok(card) and not card.is_planeswalker:
            out.append((4, (card.name.startswith("Way of the"), card.mv), card))
    return sorted(out, key=lambda o: (o[0], tuple(-x if isinstance(x, int) else -int(x) for x in o[1])))


def _return_linked(link, e):
    """610.3: die exilierte Karte kehrt unter der Kontrolle ihres Besitzers zurueck (610.3c), als neues Objekt (400.7);
    ein Token nicht (111.8)."""
    owner, card = link["owner"], link["card"]
    if card.is_token:
        return
    e["events"].append(f"{owner.name}: {card.name} kehrt aus dem Exil zurück")
    if link["creature"]:
        new = Creature(card, owner.now)
        owner.creatures.append(new)
        creature_enters(owner, new, owner.now, e, owner.opponent, cast=False)
    else:
        owner.perms.append(card)
        permanent_enters(owner, owner.opponent, card, owner.now, e)


def destroy_permanent(p, target, e, exile=False):
    """Ein Nichtkreatur-Permanent von p verlaesst das Spielfeld (zerstoert, bei exile ins Exil). target: Karte oder
    Eintrag aus trap_links. Folgen: Falle gibt ihre Karte zurueck, Lock-Aura gibt die Kreatur frei, Aura/Ausruestung
    loesen sich."""
    link = target if isinstance(target, dict) else None
    card = link["trap"] if link else target
    if card not in p.perms:
        return False
    p.perms.remove(card)
    if not card.is_token and not exile:
        p.graveyard.append(card)
    e["events"].append(f"{p.name}: {card.name} " + ("ins Exil" if exile else "zerstört"))
    if link is None:
        link = next((l for l in p.trap_links if l["trap"] == card), None)
    if link is not None and link in p.trap_links:
        p.trap_links.remove(link)
        _return_linked(link, e)
    for lock in list(p.lock_links):
        if lock["aura"] == card:
            p.lock_links.remove(lock)
            lock["creature"].locked = False
            break
    for c in p.creatures:
        if card in c.auras:
            c.auras.remove(card)
            break
        if card in c.gear:
            c.gear.remove(card)
            break
    bury((p, p.opponent) if p.opponent is not None else (p,), e)
    return True


def perm_abilities(me, opp, step, e):
    """Eigene Main Phase (Sorcery-Zeit): Budding Insurgent opfert sich fuer ein Ziel aus Rang 1-3 (Karte, wenn es
    eine legendaere Verzauberung war); The Echoverse Fulcrum, wenn die gegnerischen Kreaturen (Manawert + Power)
    mindestens doppelt so viel wert sind wie unsere."""
    for c in list(me.creatures):
        if c.dead or not c.card.sac_perm_removal:
            continue
        targets = [t for t in noncreature_targets(me, opp, c.card.sac_perm_removal) if t[0] <= 3]
        if not targets:
            continue
        target = targets[0][2]
        card = target["trap"] if isinstance(target, dict) else target
        c.dead = True
        e["events"].append(f"{me.name}: opfert {c.card.name}")
        bury((me,), e)
        destroy_permanent(opp, target, e)
        if c.card.sac_perm_draw and card.legendary and not card.is_artifact and not card.is_planeswalker:
            _draw(me)
    for card in list(me.perms):
        if not card.sweep_ability:
            continue
        theirs = sum(c.card.mv + c.power for c in opp.creatures if not c.dead)
        ours = sum(c.card.mv + c.power for c in me.creatures if not c.dead)
        if theirs <= 0 or theirs < 2 * ours or not _pay_ability(me, card.sweep_ability, "free"):
            continue
        destroy_permanent(me, card, e, exile=True)
        for c in me.creatures + opp.creatures:
            c.dead = c.dead or not c.has("indestructible")  # 702.12b
        e["events"].append(f"{me.name}: {card.name} – alle Kreaturen zerstört")
        bury((me, opp), e)


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


def discarded(p, e, cards=None):
    """p hat eine oder mehrere Karten abgeworfen (701.9): Tinybones beider Spieler schaedigt die Gegner seines
    Kontrolleurs; Titanbones gibt beim Abwerfen Leben. cards: die abgeworfenen Karten (sonst die zuletzt in den
    Friedhof gelegte)."""
    gone = cards if cards is not None else p.graveyard[-1:]
    p.discards_turn += len(gone)
    for c in gone:
        gain_life(p, c.discard_life)
    for q in (p, p.opponent):
        if q is None:
            continue
        for c in q.creatures:
            if c.card.discard_ping and not c.dead:
                deal_noncombat(q, q.opponent, c.card.discard_ping, e)


def discard(p, n, e):
    done = 0
    gone = []
    for _ in range(n):
        card = choose_discard(p)
        if card is None:
            break
        p.hand.remove(card)
        p.graveyard.append(card)
        e["events"].append(f"{p.name} wirft ab: {card.name}")
        done += 1
        gone.append(card)
    if done:
        discarded(p, e, gone)


def cast_removal(card, caster, victim, e, step, target=None):
    """Wirkung des Removals von card (Card.removal) gegen victim. Gestorbene Kreaturen kommen in den Friedhof.
    Empower X: Overwrite the Multiverse zaehlt die exilierten Kreaturen beider Seiten, Violent Echoes den Schaden
    ueber die restliche Toughness bzw. Loyalty hinaus (120.4a)."""
    if not card.empower_x:
        return _cast_removal(card, caster, victim, e, step, target)
    sides = (caster, victim)
    alive = [c for p in sides for c in p.creatures if not c.dead]
    left = {id(c): (c.toughness - c.damage, c.damage) for c in victim.creatures if not c.dead}
    loyal = {id(w): w.loyalty for w in victim.walkers}
    out = _cast_removal(card, caster, victim, e, step, target)
    gone = [c for c in alive if c.dead or not any(c is x for p in sides for x in p.creatures)]
    if card.empower_x == "exiled":
        x = len(gone)
    else:
        amount = _amount(card.removal, caster)
        x = max([amount - left[id(c)][0] for c in victim.creatures + gone
                 if id(c) in left and (c.damage != left[id(c)][1] or c in gone)]
                + [amount - loyal[id(w)] for w in victim.walkers if id(w) in loyal and w.loyalty != loyal[id(w)]]
                + [0])
    _jace_add(caster, x, e)
    return out


def _cast_removal(card, caster, victim, e, step, target=None):
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
    if kind in ("damage", "sweep_damage") and amount > 0 and red_bonus(caster, card):  # Searing Soloist
        amount += 1
    if kind in ("sweep", "sweep_damage"):
        hit = list(victim.creatures)
        if not ("chosen_type",) in spec[2] and not ("opponents",) in spec[2]:
            hit += caster.creatures
        for c in hit:
            if kind == "sweep":
                c.dead = c.dead or not c.has("indestructible")  # 702.12b
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
        lethal_face = kind == "damage" and any_target and victim.life <= amount
        pw = None if lethal_face else pw_target(card, caster, victim, target)
        if pw is not None:
            hit_walker(caster, victim, card, pw, e)
            return
    if kind == "damage" and any_target and (target is None or victim.life <= amount):
        deal_noncombat(caster, victim, amount, e)
        e["events"].append(f"{caster.name}: {card.name} – {amount} Schaden an {victim.name}")
        return
    if target is None and card.exile_until:  # Memory Trap: sonst ein Nichtkreatur-Permanent
        nc = [t for t in noncreature_targets(caster, victim, "nonland") if t[0] <= 4]
        if nc:
            item = nc[0][2]
            gone = item["trap"] if isinstance(item, dict) else item
            caster.trap_links.append({"trap": card, "card": gone, "owner": victim, "creature": False})
            destroy_permanent(victim, item, e, exile=True)
            return
    if target is None:
        e["events"].append(f"{caster.name}: {card.name} ohne Ziel")
        return
    if target.dead or not any(target is c for c in victim.creatures):  # 608.2b: Ziel schon weg (z. B. Emblem)
        e["events"].append(f"{caster.name}: {card.name} ohne Ziel ({target.card.name} ist nicht mehr da)")
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
    if protect_response(victim, target, caster, e, step):
        bury((caster, victim), e)
        e["events"].append(f"{caster.name}: {card.name} ohne Ziel ({target.card.name} hat Hexproof)")
        return
    _draw(victim, target.card.targeted_draw)  # Ruric Thar, Biomagus: Ziel eines gegnerischen Zaubers
    if kind in ("destroy", "damage", "minus", "counters", "lock") and sacrifice_for(victim, target, e):
        bury((caster, victim), e)  # als Antwort geopfert: der Zauber hat kein Ziel mehr (608.2b)
        e["events"].append(f"{caster.name}: {card.name} ohne Ziel ({target.card.name} geopfert)")
        return
    if kind == "destroy" and card.exile_until:  # 610.3: Exil, bis die Falle das Spielfeld verlaesst
        victim.creatures.remove(target)
        _leave(victim, target.card)
        if not target.card.is_token:
            caster.trap_links.append({"trap": card, "card": target.card, "owner": target.owner or victim,
                                      "creature": True})
        e["events"].append(f"{caster.name}: {card.name} – {label} ins Exil")
        bury((caster, victim), e)
        return
    if kind == "destroy":
        if target.has("indestructible"):  # 702.12b
            e["events"].append(f"{caster.name}: {card.name} – {label} ist unzerstörbar")
        else:
            target.dead = True
    elif kind == "minus" and target.has("indestructible"):  # -X/-X wirkt: Toughness 0 (704.5f)
        target.pump -= amount
        target.tpump -= amount
    elif kind == "shuffle":  # Living Library: in die Bibliothek mischen
        victim.creatures.remove(target)
        _leave(victim, target.card)
        if not target.card.is_token:
            owner = target.owner or victim
            owner.library.insert(random.randint(0, len(owner.library)), target.card)
        e["events"].append(f"{caster.name}: {card.name} – {label} in die Bibliothek gemischt")
        bury((caster, victim), e)
        return
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
            (target.owner or victim).hand.append(target.base_card or target.card)
        _leave(victim, target.card)
        check_auras(victim, e)
        e["events"].append(f"{caster.name}: {card.name} – {label} zurück auf die Hand")
        return
    elif kind == "lock":
        target.locked = True
        if card.unprepare:  # Infinite Coursework: tappen, unprepared
            target.tapped = True
            target.prepared = False
        if card in caster.perms:
            caster.lock_links.append({"aura": card, "creature": target})
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
            if card.tuck_top_damage:  # Clash of Elements: oben kostet 2 Schaden
                deal_noncombat(caster, owner, card.tuck_top_damage, e)
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
    if spell.is_instant_sorcery and any(c.card.split_second and not c.dead for c in caster.creatures):
        return False  # Samut: Split Second (702.61), niemand kann antworten
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
    Gegner kontern: dann nur die Ausloeser beim Wirken, die Karte geht in den Friedhof (Flashback: Exil, Kopie: weg).
    Way of the Cryomancer: der erste Instant/Sorcery des Schritts wird kopiert; die Kopie loest zuerst auf, wird nicht
    gewirkt (707.10) und waehlt neue Ziele (707.10c). Jace's Machinations: im Zug des Gegners eine weitere
    Aktivierung der Jaces."""
    copy = card.is_instant_sorcery and not card.is_copy and me.copy_next == step
    if copy:
        me.copy_next = None
    if try_counter(me, card, step, entry, effects=modes):
        if card.is_copy:
            src = next((c for c in me.creatures if c.prepared and c.card.prepared[1] == card), None)
            if src is not None:
                src.prepared = False
        elif not to_exile:
            (owner or me).graveyard.append(card)
        on_cast(me, card, step, entry)
        if copy:
            _resolve_copy(me, opp, card, step, entry, modes)
        codie_copies(me, opp, card, step, entry, modes)
        bury((me, opp), entry)
        return
    if card.is_copy:  # Prepared-Kopie: eine passende Kreatur ist nicht mehr prepared, kein Friedhof
        src = next((c for c in me.creatures if c.prepared and c.card.prepared[1] == card), None)
        if src is not None:
            src.prepared = False
    elif card.is_creature:
        fresh = Creature(card, step)
        fresh.owner = owner
        me.creatures.append(fresh)
    elif card.is_instant_sorcery:
        if not to_exile:  # Flashback: danach ins Exil
            (owner or me).graveyard.append(card)
    elif card.is_planeswalker and card.loyalty_start > 0:
        me.walkers.append(Walker(card, step))
    else:
        me.perms.append(card)
    on_cast(me, card, step, entry)
    if card.is_creature and not card.is_copy:
        creature_enters(me, fresh, step, entry, opp)  # nicht creatures[-1]: Wirk-Ausloeser koennen Kreaturen anhaengen
    elif card.is_instant_sorcery or card.is_copy:
        if copy:
            _resolve_copy(me, opp, card, step, entry, modes)
        codie_copies(me, opp, card, step, entry, modes)
        card_effects(me, opp, card, step, entry, modes)
    else:
        permanent_enters(me, opp, card, step, entry)
    if card.jace_instant and me.turn_start != step:
        jace_instant_turn(me, opp, step, entry)
    bury((me, opp), entry)


def codie_copies(me, opp, card, step, entry, modes):
    """Codie: ein gewirkter prepared-Zauber wird kopiert (je Codie eine Kopie, neue Ziele, 707.10c)."""
    if not (card.is_copy and card.is_instant_sorcery):
        return
    for c in [c for c in me.creatures if c.card.codie_copy and not c.dead]:
        _resolve_copy(me, opp, card, step, entry, modes)


def _resolve_copy(me, opp, card, step, entry, modes):
    """Kopie eines Instants/Sorcery (Way of the Cryomancer): nur die Effekte, kein Wirken."""
    entry["events"].append(f"{me.name}: Kopie von {card.name}")
    for ef in once_effects(card) if not card.choices else ():  # Empower gehoert zum Effekt (sonst beim Wirken)
        if ef[1] == "spell":
            _jace_add(me, ef[2], entry)
    card_effects(me, opp, card, step, entry, modes)  # zieht die Planung schon, zieht danach das Original selbst
    bury((me, opp), entry)


def jace_instant_turn(p, opp, step, e):
    """Jace's Machinations im Zug des Gegners: der Jace-Token und jeder echte Jace-Planeswalker duerfen dort noch
    einmal aktivieren (606.3 zaehlt je Zug); gewaehlt wird wie nach Main 2."""
    if jace_present(p):
        p.jace.used = False
        if walker_engine(p):
            walker_phase(p, opp, step, e, "after")
        else:
            _jace_activate(p, step, e, True)
    for w in list(p.walkers):
        if w.card.is_jace and w in p.walkers:
            w.used = False
            opts = pw_options(p, opp, w, step, "after")
            if opts:
                activate_pw(p, opp, w, (opts[0][2], opts[0][3]), step, e, opts[0][4])


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
    if sub.perm_destroy and opp is not None and any(t[0] <= 4 for t in noncreature_targets(p, opp, sub.perm_destroy)):
        return (5, 0, False, 0)
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
    """Ein Nichtkreatur-Permanent kam ins Spiel: Jace-Ausloeser und Betreten-Effekte. Ein echter Planeswalker hat keine
    Betreten-Effekte (seine Texte sind Loyalty-Faehigkeiten und Ausloeser)."""
    if card.is_planeswalker and card.loyalty_start > 0:
        _jace_on_enter(p, card, step, e)
        ally_walker_enters(p, e)
        return
    if card.is_aura and (card.aura_pump or card.aura_kw) and not card.removal:  # eigene Aura auf die beste Kreatur
        alive = [c for c in p.creatures if not c.dead]
        if alive:
            pick = max(alive, key=lambda c: (can_attack(c, step), danger(c)))
            pick.auras.append(card)
            e["events"].append(f"{p.name}: {card.name} an {pick.card.name}")
    if card.station:  # Station-Karte: eigenes Objekt im Spiel, Charge-Marken bleiben, bis sie das Spielfeld verlaesst
        live = card._replace()
        for i in range(len(p.perms) - 1, -1, -1):
            if p.perms[i] is card:
                p.perms[i] = live
                break
        p.stations.append({"card": card, "live": live, "since": step, "charge": 0, "creature": None})
    if card.vehicle:  # Fahrzeug: seit wann unter unserer Kontrolle (fuer den Angriff, 302.6)
        p.vehicles.append({"card": card, "since": step, "crewed": None, "tapped": False})
    if card.equip_etb and card in p.perms:  # Ausruestung: beim Betreten anlegen
        kws, untap, kind = card.equip_etb
        host = None
        if kind == "token" and card.equip_carrier is not None:  # Dwarven Shortsword: erst das Token
            before = len(p.creatures)
            make_tokens(p, [(1, card.equip_carrier)], step, e, opp, card.name)
            host = p.creatures[-1] if len(p.creatures) > before else None
        elif kind != "token":
            host = gear_host(p, step, kind)
        if host is not None:
            attach_gear(p, card, host, e)
            host.extra |= set(kws)
            if untap:
                host.tapped = False
    if card.animate_artifact:  # Puppet Crafting: Artefakt wird 5/5-Construct
        target = animate_target(p)
        if target is not None:
            p.perms.remove(target)
            pw, tw = card.animate_artifact
            new = Creature(target._replace(is_creature=True, power=pw, toughness=tw, creature_types=("construct",)),
                           step - 1)  # lag schon auf dem Feld
            new.base_card = target
            new.auras.append(card)
            new.gy, new.ctl = p.graveyard, p
            p.creatures.append(new)
            e["events"].append(f"{p.name}: {card.name} belebt {target.name}")
    if card.is_artifact and no_enter_triggers(p):  # Karn, Argent Defender
        return
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
        gain_life(me, card.etb_life)  # Modus beim Betreten: "you gain N life" (z. B. Archive Arbiter)
    if card.treasure:
        artifact_tokens(me, "treasure", card.treasure, step, entry)
    if card.heartwood:  # 111.10x: Heartwood-Token
        artifact_tokens(me, HEARTWOOD, card.heartwood, step, entry)
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
    effects = card._replace(modes=()) if card.etb_grant else card  # Teyo: Marke mit dem Schluesselwort (creature_enters)
    if card.removal and opp is not None and len(me.lands) >= card.etb_lands_needed \
            and _edict_paid(me, opp, card, entry):
        cast_removal(card, me, opp, entry, step)
        opp.treasures += card.victim_treasure  # Vraska, the Cutting Glare
        if card.removal[3]:  # any target: der Schaden ist schon verteilt
            effects = card._replace(modes=tuple(tuple(a for a in m if a[0] != "face") for m in card.modes))
    if card.stage_token is not None:  # Command the Stage: Cadet, dann Marke auf jedes andere Wizard-Token
        others = [c for c in me.creatures if c.card.is_token and "wizard" in c.card.creature_types and not c.dead]
        make_tokens(me, [(1, card.stage_token)], step, entry, opp, card.name)
        for c in others:
            c.bonus += card.wizard_token_counters
    me.next_pw += card.next_pw_discount  # Sparks Ablaze
    if card.opp_etb_life and opp is not None:  # Aria of Flame
        gain_life(opp, card.opp_etb_life)
    if card.mill_self:  # Dark Matter Manipulator, Omit Variables
        _mill(me, card.mill_self, entry, card.name)
    if card.team_grant:  # Artifist Acumen
        for c in me.creatures:
            if not c.dead:
                c.extra |= set(card.team_grant)
    if card.land_to_graveyard:  # Enroot: das haeufigste Land der Bibliothek
        lands = Counter(c.name for c in me.library if c.is_land)
        if lands:
            name = max(lands, key=lambda n: (lands[n], n))
            pick = next(c for c in me.library if c.name == name)
            me.library.remove(pick)
            random.shuffle(me.library)
            me.graveyard.append(pick)
            entry["events"].append(f"{me.name}: {card.name} – {pick.name} in den Friedhof")
    if card.life_tokens is not None and me.gained > 0:  # Germinate Recruits: X = Leben in diesem Zug
        make_tokens(me, [(me.gained, card.life_tokens)], step, entry, opp, card.name)
    if card.entrust:  # Entrust the Spark (nur mit Jace-Token)
        entrust_spark(me, opp, step, entry)
    if card.pw_tutor:  # Loyal Tutor
        loyal_tutor(me, entry)
    if card.perm_destroy and opp is not None:  # Archive Arbiter
        targets = [t for t in noncreature_targets(me, opp, card.perm_destroy) if t[0] <= 4]
        if targets:
            destroy_permanent(opp, targets[0][2], entry)
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
    if card.hand_pick and card.hand_pick_gift and opp is not None:  # Boisterous Clique: Exil, dafuer Mind Stone
        pick = choose_from_hand(opp, card.hand_pick)
        gift = conjure(card.hand_pick_gift)
        if pick is not None and gift is not None:
            opp.hand.remove(pick)
            opp.hand.append(gift)
            entry["events"].append(f"{me.name}: {card.name} – {pick.name} ins Exil, {opp.name} bekommt {gift.name}")
    elif card.hand_pick and opp is not None:
        pick = choose_from_hand(opp, card.hand_pick)
        if pick is not None:
            opp.hand.remove(pick)
            opp.graveyard.append(pick)
            discarded(opp, entry)
            entry["events"].append(f"{me.name}: {card.name} – {opp.name} wirft {pick.name} ab")
    if effects.modes:
        board, bonus, pump = me.board()
        before = [c.pump for c in me.creatures]
        marks = [c.bonus for c in me.creatures]
        gain = apply_effects(effects, board, bonus, pump, step)
        me.write_back(bonus, pump)
        if card.grant_kw or card.untap_target:  # "It gains ... / Untap it": die Kreatur mit Marken bzw. Pump
            hit = next((c for c, p_, b_ in zip(me.creatures, before, marks) if c.pump > p_ or c.bonus > b_), None)
            if hit is not None:
                hit.extra |= set(card.grant_kw)
                hit.tapped = hit.tapped and not card.untap_target
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
    elif filt == "creature_pw":
        ok = card.is_creature or card.is_planeswalker
    elif filt == "nonland_permanent":
        ok = not card.is_land and not card.is_instant_sorcery
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
    elif card.is_planeswalker and card.loyalty_start > 0:  # neues Objekt mit voller Loyalty (400.7, 306.5b)
        p.walkers.append(Walker(card, step))
        permanent_enters(p, opp, card, step, e)
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
    return [c for c in cards if not c.is_instant and (not c.flash or (c.is_aura and (c.aura_pump or c.aura_kw)))
            and legend_ok(me, c) and reanimate_ok(me, c)
            and (not c.animate_artifact or animate_target(me) is not None)
            and (not c.rummage_spell or surplus_land(me) is not None)
            and (not c.twin or twin_host(me, opp) is not None)
            and (not c.cast_threshold or threshold(me))
            and (not c.entrust or entrust_pick(me) is not None)
            and (not c.x_counters or sum(1 for x in me.creatures if not x.dead) >= 2)
            and omni_ok(c, me.hand, sum(1 for x in me.creatures if not x.dead))
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
    out = [(m, tough[i] if i < len(tough) else (), card.grant_kw or card.etb_grant) for i, m in enumerate(card.modes)
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
        if card.untap_target:  # Tethermage's Advantage: "Untap it"
            own[best[2]].tapped = False
        if card.is_creature:
            if card.etb_grant:
                p.grant_target = "done"  # Teyo: Marke und Schluesselwort schon auf der Kampfkreatur
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
    for c in p.creatures:  # "{N}, Sacrifice this creature: Removal" (Living Library)
        if c.card.sac_removal and not c.dead:
            out.append((c.card, c.card.sac_removal[0], c.card._replace(removal=c.card.sac_removal[1]), False, "board"))
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
    if zone == "board":
        return [c.card for c in p.creatures if not c.dead]
    return {"exile": p.exiled, "flashback": p.graveyard}.get(zone, p.hand)


def _use_removal(p, card, alts, is_spell, step, e, zone="hand", other=None, fx=None, target=None):
    """Bezahlt und legt die Karte in den Friedhof (gewirkt oder abgeworfen); aus dem Exil in den Friedhof des
    Besitzers (other: der Gegner, falls der Besitzer nicht gespeichert ist). Gibt False zurueck, wenn der Zauber
    gekontert wurde (dann kein Removal)."""
    if not _pay_open(p, alts):
        return False
    if zone == "flashback":  # aus dem Friedhof, danach ins Exil
        p.graveyard.remove(card)
    elif zone == "board":  # die Kreatur opfert sich als Kosten
        src = next(c for c in p.creatures if c.card == card and not c.dead)
        src.dead = True
        e["events"].append(f"{p.name}: opfert {card.name}")
        bury((p,), e)
        return True
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
        if card.etb_grant:  # Teyo, Diamondblade Mage: Marke und Deathtouch auf sich selbst
            new.gy, new.ctl = dfn.graveyard, dfn
            new.extra |= set(card.etb_grant)
            new.bonus += 1
        blockers = [b for b in dfn.creatures if not b.tapped and not b.dead]
        lethal = max_through(alive, blockers) >= dfn.life and max_through(alive, blockers + [new]) < dfn.life
        good = any(can_block(new, a) and outcome(a, [new]) == (True, [False]) for a in alive)
        if card.etb_grant and "deathtouch" in card.etb_grant:  # auch ein Tausch gegen einen gefaehrlicheren Angreifer
            good = good or any(can_block(new, a) and outcome(a, [new])[0] and danger(a) > danger(new) for a in alive)
        if lethal or good:
            if card.etb_grant:
                dfn.grant_target = "done"
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
        if card.pw_tutor and tutor_pick(dfn) is None:
            continue
        if card.life_tokens is not None and dfn.gained < 2:  # Germinate Recruits erst ab X = 2
            continue
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
    gy_draws(dfn, e)
    end_step_abilities(dfn, e, step)
    legend_discard_draw(dfn, e)
    twin_activate(dfn, act, step, e, end_step=True)


def gy_draws(p, e):
    """Am Ende des gegnerischen Zugs: Ziehen aus dem Friedhof mit freiem Mana (Seasoned Cryomancer: {3}{U}{U},
    Karte exilieren, zwei ziehen)."""
    for card in list(dict.fromkeys(p.graveyard)):
        if card.gy_draw and card in p.graveyard and _pay_open(p, card.gy_draw[0]):
            p.graveyard.remove(card)
            _draw(p, card.gy_draw[1])
            e["events"].append(f"{p.name}: exiliert {card.name} aus dem Friedhof und zieht {card.gy_draw[1]}")


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
    if cond == "surveilled" and not p.surveilled:  # Proctor of Potential
        return False
    if cond == "gy_gt_lib" and not len(p.graveyard) > len(p.library):  # Paradox Kraken
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


def _may_equip(g, c):
    """Darf die Ausruestung g an c? Nur "Equip <Typ>" (ohne allgemeines Equip): nur Kreaturen dieses Typs."""
    return not (g.equip_typed and len(g.equip_typed) > 2) or g.equip_typed[0] in c.card.creature_types


def gear_host(p, step, kind=""):
    """Kreatur fuer kostenloses Anlegen (beim Betreten), Regel wie beim Equip: der staerkste Angreifer, sonst die
    gefaehrlichste eigene Kreatur. kind: nur Kreaturen dieses Typs ("target Dwarf you control")."""
    alive = [c for c in p.creatures if not c.dead and (not kind or kind in c.card.creature_types)]
    attackers = [c for c in alive if can_attack(c, step)]
    if attackers:
        return max(attackers, key=lambda c: (c.dmg, c.bonus))
    return max(alive, key=danger) if alive else None


def attach_gear(p, g, host, e):
    """Legt die Ausruestung g an host an (vorher von einer anderen Kreatur ab)."""
    for c in p.creatures:
        if g in c.gear:
            c.gear.remove(g)
    host.gear.append(g)
    e["events"].append(f"{p.name}: {g.name} an {host.card.name}")


def equip_gear(me, step, e):
    """Ausruestung anlegen (Sorcery-Zeit, freies Mana): an den staerksten Angreifer (bei Gleichstand der mit den meisten
    Marken, das macht Warrior's Blades billiger); umgehaengt nur, wenn die bisherige Kreatur nicht angreifen kann."""
    for g in [c for c in me.perms if c.equip]:
        host = next((c for c in me.creatures if g in c.gear and not c.dead), None)
        if host is not None and can_attack(host, step):
            continue
        cands = [c for c in me.creatures if can_attack(c, step) and c is not host and _may_equip(g, c)]
        if not cands:
            continue
        pick = max(cands, key=lambda c: (c.dmg, c.bonus))
        alts, _p, _t, per_counter = g.equip
        if g.equip_typed and g.equip_typed[0] in pick.card.creature_types:  # "Equip Wizard {1}"
            alts = g.equip_typed[1]
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
        if _debuff_card(card).debuff_perpetual:  # Simple Subtraction
            perpetual_pump(target, -n, 0)
        else:
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


def buff_target(p, step, others_of=None):
    """Ziel fuer "target creature you control" bei Marken und Pumps (Regel wie combat_buffs): die eigene Kreatur, die
    angreifen kann, davon die gefaehrlichste. others_of: diese Kreatur ausnehmen ("another target creature")."""
    alive = [x for x in p.creatures if not x.dead and x is not others_of]
    return max(alive, key=lambda x: (can_attack(x, step), danger(x))) if alive else None


def combat_counters(me, step, e):
    """Zu Beginn des eigenen Kampfs: N +1/+1-Marken auf eine eigene Kreatur, dazu Schluesselwoerter bis Rundenende
    (Training Regimen, Additive Evolution)."""
    for _src, card in static_sources(me):
        if not card.combat_counter:
            continue
        pick = buff_target(me, step)
        if pick is None:
            continue
        n, kws = card.combat_counter
        pick.bonus += n
        pick.extra |= set(kws)
        e["events"].append(f"{me.name}: {card.name} – {n} Marke(n) auf {pick.card.name}"
                           + (f", {', '.join(kws)}" if kws else ""))


def attack_keywords(me, attackers, alone, e):
    """Angriffs-Ausloeser mit Pump und Schluesselwoertern bis Rundenende: die Kreatur selbst ("Whenever ~ attacks
    [alone], ~ gets +P/+T and gains ..."), jede eigene Kreatur, die allein angreift (Black Widow), und jede
    ausgeruestete Angreiferin (Dain Ironfoot)."""
    for a in attackers:
        if a.card.attack_self and (not a.card.attack_self[3] or a is alone):
            pw, tw, kws, _alone = a.card.attack_self
            a.pump += pw
            a.tpump += tw
            a.extra |= set(kws)
            e["events"].append(f"{me.name}: {a.card.name} greift an: +{pw}/+{tw}" + (f", {', '.join(kws)}" if kws else ""))
        if a.card.attack_target:  # Nori: Ziel nach der Regel fuer Buffs, der gefaehrlichste Angreifer
            pw, tw, kws = a.card.attack_target
            pick = max((b for b in attackers if not b.dead), key=danger)
            pick.pump += pw
            pick.tpump += tw
            pick.extra |= set(kws)
            e["events"].append(f"{me.name}: {a.card.name} – {pick.card.name}" + (f" +{pw}/+{tw}" if pw or tw else "")
                               + (f" {', '.join(kws)}" if kws else ""))
        if a.card.equipped_attack_kw:
            for b in attackers:
                if b.gear:
                    b.extra |= set(a.card.equipped_attack_kw)
    if alone is not None:
        for _src, card in static_sources(me):
            if card.alone_kw:
                alone.extra |= set(card.alone_kw)
                e["events"].append(f"{me.name}: {card.name} – {alone.card.name} greift allein an: "
                                   f"{', '.join(card.alone_kw)}")


def _station_ready(p):
    """Station-Karten, die noch im Spiel sind (als Permanent oder als Kreatur); weggefallene werden entfernt."""
    out = []
    for st in list(p.stations):
        st.setdefault("live", st["card"])
        car = st["creature"]
        here = (any(c is car for c in p.creatures) if car is not None
                else any(x is st["live"] for x in p.perms))
        if here:
            out.append(st)
        else:
            p.stations.remove(st)
    return out


def update_stations(p, step, e):
    """721.2: Stufen nach Charge-Marken. Erreichte Schluesselwoerter und Team-Pumps gelten; ab der Stufe mit P/T-Box
    ist die Karte eine Artefaktkreatur (seit ihrem Betreten unter unserer Kontrolle, 302.6)."""
    for st in _station_ready(p):
        card = st["card"]
        at, pw, tw, tiers = card.station
        reached = [t for t in tiers if st["charge"] >= t[0]]
        kws = tuple(dict.fromkeys(k for t in reached for k in t[1]))
        conds = tuple((("always",), t[2][2] if t[2][2] == "others" else "team", t[2][0], t[2][1], ())
                      for t in reached if t[2])
        if at and st["charge"] >= at:
            if st["creature"] is None:
                p.perms.remove(st["live"])
                car = Creature(card._replace(is_creature=True, power=pw, toughness=tw, kw=card.kw + kws,
                                             cond_static=card.cond_static + conds), st["since"])
                car.base_card = card
                car.gy, car.ctl = p.graveyard, p
                p.creatures.append(car)
                st["creature"] = car
                e["events"].append(f"{p.name}: {card.name} ist ab {at} Marken eine {pw}/{tw}-Kreatur")
            else:
                car = st["creature"]
                new = car.card._replace(kw=card.kw + kws, cond_static=card.cond_static + conds)
                if new != car.card:
                    car.card = new
        elif st["creature"] is None:
            new = card._replace(cond_static=card.cond_static + conds)
            if new != st["live"]:
                i = next(i for i, x in enumerate(p.perms) if x is st["live"])
                p.perms[i] = new
                st["live"] = new


def station_phase(me, opp, step, e):
    """Station in Main 2 (Nutzer 2026-10-21, wie Crew): Kreaturen tappen, die nicht gegen einen toedlichen
    Gegenangriff fehlen, die staerksten zuerst, bis die hoechste Stufe erreicht ist; zuerst das Raumschiff, das seiner
    naechsten Stufe am naechsten ist. Auch frische Kreaturen (702.184a: Tappen ist keine {T}-Kosten der Kreatur)."""
    ready = _station_ready(me)
    if not ready:
        return
    their = [t for t in opp.creatures if not t.dead and (not t.card.defender or _defender_ok(t)) and t.dmg > 0]

    def top(st):
        at, _pw, _tw, tiers = st["card"].station
        return max([at] + [t[0] for t in tiers])

    def gap(st):
        steps = sorted({st["card"].station[0]} | {t[0] for t in st["card"].station[3]} - {0})
        return min((n - st["charge"] for n in steps if n > st["charge"]), default=99)

    for st in sorted(ready, key=gap):
        while st["charge"] < top(st):
            ships = {id(s["creature"]) for s in me.stations if s["creature"] is not None}
            cands = sorted((c for c in me.creatures if not c.dead and not c.tapped and c.power > 0
                            and id(c) not in ships), key=lambda c: -c.power)
            pick = None
            for c in cands:
                home = [h for h in me.creatures if not h.dead and not h.tapped and h is not c]
                if max_through(their, home) < me.life:
                    pick = c
                    break
            if pick is None:
                break
            pick.tapped = True
            st["charge"] += pick.power
            e["events"].append(f"{me.name}: Station – {pick.card.name} tappt, {st['card'].name} hat {st['charge']} "
                               f"Marken")
            update_stations(me, step, e)


def _crew_ready(p):
    """Fahrzeuge, die noch nicht gecrewt sind und noch auf dem Feld liegen (je Karte hoechstens so viele Eintraege wie
    Exemplare in p.perms; zerstoerte fallen weg)."""
    seen = Counter()
    out = []
    for v in list(p.vehicles):
        if v["crewed"] is not None:
            continue
        seen[v["card"]] += 1
        if seen[v["card"]] > sum(1 for x in p.perms if x == v["card"]):
            p.vehicles.remove(v)
            continue
        out.append(v)
    return out


def _crew_sets(p, need, members):
    """Moegliche Crews: Teilmengen von members mit Power zusammen mindestens need (702.122a: auch Kreaturen ohne
    Einsatzverzoegerung-Pause, Tappen ist keine {T}-Kosten)."""
    members = sorted(members, key=lambda c: -c.power)[:10]
    out = []
    for k in range(1, len(members) + 1):
        for combo in itertools.combinations(members, k):
            if sum(max(0, c.power) for c in combo) >= need:
                out.append(combo)
    return out


def crew(p, v, members, step, e):
    """Crew: members tappen, das Fahrzeug wird bis Rundenende zur Artefaktkreatur (Creature mit base_card)."""
    n, pw, tw, kws = v["card"].vehicle
    for c in members:
        c.tapped = True
    p.perms.remove(v["card"])
    car = Creature(v["card"]._replace(is_creature=True, power=pw, toughness=tw, kw=kws), v["since"])
    car.base_card = v["card"]
    car.gy, car.ctl = p.graveyard, p
    car.crew = list(members)
    p.creatures.append(car)
    v["crewed"] = car
    if e is not None:
        e["events"].append(f"{p.name}: Crew {n} – {v['card'].name} mit {', '.join(c.card.name for c in members)}")


def uncrew(p, v, e, untap=True):
    """Crew zuruecknehmen (Fahrzeug greift doch nicht an bzw. blockt nicht) oder am Rundenende beenden."""
    car = v["crewed"]
    v["crewed"] = None
    if car in p.creatures:
        p.creatures.remove(car)
        p.perms.append(v["card"])
    if e is not None and untap:  # nur beim Zuruecknehmen: die Crew war nie wirklich getappt
        for c in car.crew:
            c.tapped = False


def crew_to_attack(me, opp, step, e):
    """Crew fuer den Angriff (Nutzer 2026-10-20): mit Kreaturen, die in diesem Zug nicht angreifen koennen, oder wenn
    das Fahrzeug mehr Schaden macht als die Kreaturen, die dafuer tappen. Nur Fahrzeuge, die seit Beginn des Zugs
    da sind. Gibt die gecrewten Eintraege zurueck."""
    done = []
    for v in sorted(_crew_ready(me), key=lambda v: -v["card"].vehicle[1]):
        if v["tapped"] or v["since"] >= step:
            continue
        n, pw, _tw, _kws = v["card"].vehicle
        members = [c for c in me.creatures if not c.dead and not c.tapped and c.base_card is None]
        best = None
        for combo in _crew_sets(me, n, members):
            lost = sum(c.dmg for c in combo if can_attack(c, step))
            key = (lost, len(combo), sorted(_value(c) for c in combo))
            if best is None or key < best[0]:
                best = (key, combo)
        if best is None or not (best[0][0] == 0 or pw > best[0][0]):
            continue
        crew(me, v, best[1], step, e)
        done.append(v)
    return done


def crew_to_block(p, attackers, step, e):
    """Crew im Zug des Gegners zum Blocken (Nutzer 2026-10-20): mit Kreaturen, die nach den normalen Block-Regeln
    nicht blocken; das Fahrzeug bleibt gecrewt, wenn es nach denselben Regeln blockt (toetet und ueberlebt, Tausch,
    Chump gegen Lethal), sonst wird die Crew zurueckgenommen. Gibt die Blocks zurueck."""
    blocks = choose_blocks(attackers, p.creatures, p.life)
    for v in _crew_ready(p):
        if v["tapped"]:
            continue
        used = {id(b) for _a, bs in blocks for b in bs}
        members = [c for c in p.creatures if not c.dead and not c.tapped and id(c) not in used and c.base_card is None]
        sets = _crew_sets(p, v["card"].vehicle[0], members)
        if not sets:
            continue
        combo = min(sets, key=lambda s: (len(s), sorted(_value(c) for c in s)))
        crew(p, v, combo, step, None)
        trial = choose_blocks(attackers, p.creatures, p.life)
        if any(b is v["crewed"] for _a, bs in trial for b in bs):
            blocks = trial
            e["events"].append(f"{p.name}: Crew {v['card'].vehicle[0]} – {v['card'].name} blockt")
        else:
            uncrew(p, v, e)
    return blocks


def attack_taps(me, opp, attackers, e):
    """"Whenever ~ / equipped creature attacks, tap target creature defending player controls" (Nutzer 2026-10-20):
    der gefaehrlichste Blocker, der unseren staerksten Angreifer aufhalten wuerde; kann ihn keiner blocken, der
    naechststaerkere Angreifer. Kein Ziel mit Hexproof; Ward nur, wenn wir zahlen koennen."""
    n = sum(1 for a in attackers if a.card.attack_tap) + sum(1 for a in attackers for g in a.gear if g.equip_attack_tap)
    for _k in range(n):
        target = None
        for a in sorted(attackers, key=danger, reverse=True):
            cands = [b for b in opp.creatures if not b.dead and not b.tapped and can_block(b, a) and not hexproof(b)
                     and ward_ok(me, b)]
            if cands:  # zuerst Blocker, die ihn wirklich aufhalten (toeten oder ueberleben)
                stop = [b for b in cands if outcome(a, [b])[0] or not outcome(a, [b])[1][0]]
                target = max(stop or cands, key=danger)
                break
        if target is None or not pay_ward(me, target, e):
            return
        target.tapped = True
        e["events"].append(f"{me.name}: Angriffs-Auslöser tappt {target.card.name}")


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


def _hold(pool, alts, creature_units):
    """Mana fuer einen Instant im Zug des Gegners freihalten: nur aus Laendern und Artefakten, nie aus Mana-Kreaturen
    (ihr Mana zaehlt nicht zum offenen Mana). Gibt (uebriger Vorrat mit Kreaturen-Mana, freigehaltene Einheiten) oder
    None zurueck."""
    base = list(pool)
    for u, _i in creature_units:
        if u in base:
            base.remove(u)
    left = pay(base, alts)
    if left is None:
        return None
    used = list(base)
    for u in left:
        used.remove(u)
    return left + [u for u, _i in creature_units], used


def take_turn(me, opp, step, rnd, skip_draw):
    """Ein Zug von me. Gibt den Protokolleintrag zurueck."""
    e = {"player": me.name, "round": rnd, "drew": None, "land": None, "main1": [], "main2": [], "attacks": [],
         "damage": 0, "face": 0, "deaths": [], "events": [], "note": ""}
    me.cast_count = 0
    me.discards_turn = 0
    me.land_now = None
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
    expire_until_next_turn(me, step)
    for w in me.walkers:
        w.used = False
    for v in me.vehicles:  # Fahrzeuge enttappen
        v["tapped"] = False
    for c in me.creatures:  # Untap (gesperrte Kreaturen bleiben gesperrt; Stun-Marke statt Enttappen, 122.1g)
        if c.stun and c.tapped:
            c.stun -= 1
            continue
        if c.card.no_untap:  # Traxos
            continue
        c.tapped = False
    upkeep(me)
    upkeep_triggers(me, opp, step, e)
    eye_upkeep(me, opp, e)
    if not skip_draw:  # Draw
        if not me.library:
            me.lost = True
            e["note"] = "muss aus leerer Bibliothek ziehen"
            return e
        card = me.library.pop(0)
        me.hand.append(card)
        me.drawn += 1
        e["drew"] = card.name
        for w in opp.walkers:  # The Theorist: zu Beginn des Draw Steps des Gegners
            if "opp_draw" in w.card.pw_static:
                _draw(opp)
                e["events"].append(f"{opp.name}: {w.card.name} – zieht eine Karte")
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
    if me.charges and any(c.charge_on_death for c in me.perms):  # Gardenize: {G} je Charge-Marke in der ersten Main
        pool = pool + [("G",)] * me.charges
    elif not any(c.charge_on_death for c in me.perms):
        me.charges = 0
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
        me.land_now = land
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
    if me.walkers:  # L2: echte Planeswalker vor dem Zaubern (Removal, Ziehen, Mana, ...)
        mana = pw_phase(me, opp, step, e, "main1", pool_all, spells)
        pool_all = pool_all + mana
        spells = phase_spells()
        if opp.life <= 0:
            return e
    omni = any(c.omni_free for c in me.perms)
    if omni or any(c.cast_untap_lands for c in me.hand):  # Omnipresence, Emrakul mit den Laendern bezahlt
        lands_now = _mana(me, step)[0][:len(me.lands) + (me.cc_land is not None)]
        if land is not None and tapped and land.land_colors in lands_now:
            lands_now.remove(land.land_colors)
        temp = set(ex_map) | set(fb_map)
        real = [c for c in me.hand if c not in temp]
        free = free_spells(real, sum(1 for c in me.creatures if not c.dead), lands_now, omni)
        free = iter(free)
        for i, c in enumerate(me.hand):
            if c in temp:
                continue
            f = next(free)
            if f != c:
                orig[f] = orig.get(c, c)
                me.hand[i] = f
        spells = phase_spells()
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
        left = _hold(pool_all, held[1], creature_units)
        if left is not None:
            pool_all, kept = left
            if held[0] in spells:
                spells.remove(held[0])
            e["events"].append(f"{me.name}: hält {len(kept)} Mana für {held[0].name} offen")
    hc = held_counter(me, orig) if rnd >= 5 and forced is None else None  # Counterspell ab Runde 5 freihalten
    if hc is not None:
        left = _hold(pool_all, hc[1], creature_units)
        if left is None and kept:  # beides geht nicht: nur der Counterspell
            pool_all = pool_all + kept
            kept = []
            e["events"] = [ev for ev in e["events"] if not ev.startswith(f"{me.name}: hält ")]
            if held is not None and held[0] in me.hand and held[0] not in spells and not held[0].is_instant:
                spells.append(held[0])
            left = _hold(pool_all, hc[1], creature_units)
        if left is not None:
            pool_all, used = left
            kept += used
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
    lotus = [c for c in me.perms if c.name == "Lotus" and c.is_token]
    if lotus and forced is None:  # Lotus wie Treasure: nur, wenn er diese Runde mehr ermoeglicht
        base = best_cast_reduced(spells, land_key(pool_all), has_creature, True)
        for k in range(1, len(lotus) + 1):
            trial = best_cast_reduced(spells, land_key(pool_all + [ANY_COLOR] * 3 * k), has_creature, True)
            if trial[0] > base[0]:
                for _ in range(k):
                    me.perms.remove(lotus[0])
                pool_all = pool_all + [ANY_COLOR] * 3 * k
                _score_, chosen = trial
                e["events"].append(f"{me.name}: {k} Lotus geopfert")
                break
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
    crafters = [c for c in me.creatures if c.card.restricted_mana and not c.tapped and not c.dead
                and (c.entered < step or c.has("haste"))]
    if crafters:  # Heartwood Crafter: sein {C} nur fuer Kopien (nicht fuer Zauber aus der Hand)
        left = Counter(cost(c) for c in copies(me)) - Counter(c for c in chosen if c.is_copy)
        for cp in left.elements():
            for k in range(1, len(crafters) + 1):
                paid = pay(rest + [u for c in crafters[:k] for u in c.card.restricted_mana], cp.alts)
                if paid is not None:
                    for c in crafters[:k]:
                        c.tapped = True
                    crafters = crafters[k:]
                    rest = paid  # k ist minimal: das Crafter-Mana ist verbraucht
                    chosen.append(cp)
                    e["events"].append(f"{me.name}: {cp.name} mit dem Mana von Heartwood Crafter")
                    break
            if not crafters:
                break
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
    for c in list(chosen):  # Guiding Hydra: X = alles freie Mana, mindestens 1 (sonst stirbt sie als 1/0)
        if c.x_counters:
            x = free_units(me)
            if x < 1:
                chosen.remove(c)
                me.hand.append(c)
                continue
            for _ in range(x):
                me.open.pop()
            me.x_values.append((c, x))
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
    if me.walkers:  # auch frisch gewirkte Planeswalker, Pumps fuer den Kampf
        pw_phase(me, opp, step, e, "combat")
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
    aerid_pump(me, opp, step, e)
    perm_abilities(me, opp, step, e)
    equip_gear(me, step, e)
    puppetbeast_sac(me, step, e)
    hall_of_echoes(me, step, e)
    # Faehigkeiten vor dem Angriff: Marken und Empower mit freiem Mana, Flying/Menace fuer den Angriff
    pre_attack_abilities(me, opp, step, e)
    combat_draw_abilities(me, opp, step, e)
    # Kampf: zu Beginn Darklight Phoenix und Desperate Futurescribe
    phoenix_check(me, opp, step, e)
    hydra_spread(me, e)
    combat_buffs(me, step, e)
    combat_counters(me, step, e)
    twin_for_lethal(me, opp, step, e)
    sacrifice_for_lethal(me, opp, step, e)
    anomaly_for_lethal(me, opp, step, e)
    crewed = crew_to_attack(me, opp, step, e)
    attackers = choose_attackers(me.creatures, opp.creatures, opp.life, me.life, step)
    if any(v["crewed"] not in attackers for v in crewed):  # Fahrzeug greift doch nicht an: Crew zuruecknehmen
        for v in crewed:
            if v["crewed"] not in attackers:
                uncrew(me, v, e)
        attackers = choose_attackers(me.creatures, opp.creatures, opp.life, me.life, step)
    art_vigilance = any(c.card.artifact_vigilance for c in me.creatures if not c.dead)
    for a in attackers:
        if not (a.has("vigilance") or (art_vigilance and a.card.is_artifact)):
            a.tapped = True
        for ef in recurring_effects(a.card):  # Angriffs-Ausloeser (Empower)
            if ef[1] == "trigger" and ef[3] == "attack" and any(pc == a.card for pc, _t in me.jace_perms):
                n = sum(1 for c in me.creatures if not c.dead) if ef[7] else ef[2]  # X = eigene Kreaturen
                _jace_add(me, n, e)
    free_blockers = [b for b in opp.creatures if not b.tapped and not b.dead]
    at_pw = choose_walker_attackers(attackers, opp, free_blockers)
    for a, w in at_pw:
        a.at_pw = w
    rest = [a for a in attackers if a.at_pw is None]
    for a in choose_jace_attackers(rest, opp, free_blockers) if rest else ():
        a.at_jace = True
    if me.attack_buff is not None:  # Garruk: Angreifer auf den Gegner +P/+T und Trample bis Rundenende
        pw_, tw, _s = me.attack_buff
        for a in attackers:
            if a.at_pw is None and not a.at_jace:
                a.pump += pw_
                a.tpump += tw
                a.extra.add("trample")
    if opp.shield is not None:  # Jace, Reality Sculptor: jeder Angreifer -N/-0
        for a in attackers:
            a.pump -= opp.shield[0]
    if attackers and (me.jace.used or any(w.used for w in me.walkers)) and any(c.card.kiora_attack and not c.dead for c in me.creatures):
        pick = max(attackers, key=danger)  # Kiora: enttappt und unblockbar
        pick.tapped = False
        pick.extra.add("unblockable")
        e["events"].append(f"{me.name}: Kiora – {pick.card.name} enttappt und unblockbar")
    alone = attackers[0] if len(attackers) == 1 and attackers[0].at_pw is None and not attackers[0].at_jace \
        else None  # 506.5: allein angreifen (einen Spieler)
    if alone is not None:
        for c in list(me.creatures):
            if c.dead:
                continue
            if c.card.alone_double_strike:  # Yuriko
                alone.extra.add("double strike")
            if c.card.alone_loot:  # Jiang Yanggu, Alone: abwerfen, ziehen, Marken je Abwurf in diesem Zug
                gone = choose_discard(me)
                if gone is not None:
                    me.hand.remove(gone)
                    me.graveyard.append(gone)
                    discarded(me, e, [gone])
                _draw(me)
                if me.discards_turn:
                    alone.bonus += me.discards_turn
                e["events"].append(f"{me.name}: {c.card.name} – {alone.card.name} greift allein an")
    attack_keywords(me, attackers, alone, e)
    attack_taps(me, opp, attackers, e)
    for a in attackers:  # Angriffs-Ausloeser der Kreatur selbst
        a.attacked = step
        for g in a.gear:  # Medic's Kitesail
            gain_life(me, g.equip_attack_life)
            if g.equip_attack_choice:  # Hunter's Axe: Deathtouch, wenn ein Blocker sonst ueberlebt, sonst Trample
                tough = [b for b in opp.creatures if not b.tapped and not b.dead and can_block(b, a)
                         and b.toughness - b.damage > a.dmg]
                kw = "deathtouch" if tough else "trample"
                a.extra.add(kw)
                e["events"].append(f"{me.name}: {a.card.name} – {g.name}: {kw}")
        if a.card.attack_loot:  # Sphinx of False Conclusions: ziehen, dann abwerfen
            _draw(me)
            gone = choose_discard(me)
            if gone is not None:
                me.hand.remove(gone)
                me.graveyard.append(gone)
                e["events"].append(f"{me.name}: {a.card.name} – Loot, wirft {gone.name} ab")
                discarded(me, e, [gone])
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
    locked = combat_locked(me, opp)  # Yuriko: im Kampf keine Zauber und keine Faehigkeiten (ausser Mana)
    if not locked:
        attackers = respond_to_attack(opp, me, attackers, e, step)
        pre_block_abilities(opp, me, attackers, e, step)
    blocks = crew_to_block(opp, attackers, step, e)
    if not locked:
        combat_abilities(me, blocks, opp, e, step, attacking=True)
        combat_abilities(opp, blocks, me, e, step, attacking=False)
        n_events = len(e["events"])
        combat_tricks(me, blocks, opp, e, step, attacking=True)
        me.cast_count += len(e["events"]) - n_events
        combat_tricks(opp, blocks, me, e, step, attacking=False)
        debuff_tricks(me, blocks, opp, e, step, attacking=True)
        debuff_tricks(opp, blocks, me, e, step, attacking=False)
        hand_bolt_tricks(me, blocks, opp, e, step, attacking=True)
        hand_bolt_tricks(opp, blocks, me, e, step, attacking=False)
        yoshimaru_combat(me, blocks, opp, e, step, attacking=True)
        yoshimaru_combat(opp, blocks, me, e, step, attacking=False)
        sacrifice_blockers(opp, blocks, e)
    before = [(a.label(), [b.label() for b in bs]) for a, bs in blocks]
    res = resolve_combat(blocks)
    if res["jace"]:
        alive_before = opp.jace.loyalty > 0
        opp.jace.loyalty = max(0, opp.jace.loyalty - res["jace"])
        e["events"].append(f"{me.name}: {res['jace']} Schaden an Jace von {opp.name} (Loyalty {opp.jace.loyalty})")
        if alive_before and opp.jace.loyalty == 0:
            _jace_zero(opp, 1, e)
    for w, n in res["pw"].values():  # 120.3c
        w.loyalty = max(0, w.loyalty - n)
        e["events"].append(f"{me.name}: {n} Schaden an {w.card.name} von {opp.name} (Loyalty {w.loyalty})")
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
    if res["player"] > 0:
        fblthp_lost(me, opp, e)
    e["attacks"] = [{"attacker": lab, "blockers": blabs, "attacker_dies": a.dead, "blockers_die": [b.dead for b in bs],
                     "jace": a.at_jace, "walker": a.at_pw.card.name if a.at_pw is not None else None}
                    for (lab, blabs), (a, bs) in zip(before, blocks)]
    bury((me, opp), e)
    if opp.life <= 0 or opp.lost:
        return e
    # Main 2
    for c in main2:
        resolve(c)
    e["main2"] = [c.name for c in main2]
    lasting_abilities(me, opp, step, e, own_turn=True, mode="free")  # z. B. Grim Repriser nach dem Angriffs-Schaden
    exhaust_abilities(me, opp, step, e)
    life_token_instants(me, opp, step, e)
    room_of_refuge(me, step, e)
    rescue_girl(me, opp, step, e)
    identity_echo(me, opp, step, e)
    prepare_abilities(me, step, e)
    emrakul_exile(me, step, e)
    hapatra_untap(me, step, e)
    station_phase(me, opp, step, e)
    if me.walkers:
        pw_phase(me, opp, step, e, "after")
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
    end_step_prepare((me, opp), e)
    for p_ in (me, opp):  # Splinter Twin: Kopien zu Beginn des Endsegments exilieren (kein Sterben)
        for c in list(p_.creatures):
            if c.exile_step is not None and c.exile_step <= step:
                p_.creatures.remove(c)
                e["events"].append(f"{p_.name}: Kopie von {c.card.name} exiliert")
    end_step_discards((me, opp), e)
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
    gone = []
    while len(p.hand) > size:
        card = choose_discard(p)
        p.hand.remove(card)
        p.graveyard.append(card)
        gone.append(card)
        e["events"].append(f"{p.name}: Handlimit – wirft {card.name} ab")
    if over:
        discarded(p, e, gone)


def cleanup(players):
    """Rundenende: Schaden, Pumps und verliehene Schluesselwoerter verfallen."""
    for p in players:
        for v in list(p.vehicles):  # Crew endet: wieder ein Artefakt (gestorbene Fahrzeuge sind weg)
            if v["crewed"] is not None:
                if any(c is v["crewed"] for c in p.creatures):
                    v["tapped"] = v["crewed"].tapped
                    uncrew(p, v, None)
                else:
                    p.vehicles.remove(v)
        p.creatures[:] = [c for c in p.creatures if c.land_source is None]  # Hall of Echoes: wieder ein Land
        for c in p.creatures:
            c.damage, c.pump, c.tpump, c.touched, c.lifted, c.at_jace = 0, 0, 0, False, False, False
            c.at_pw = None
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
            if me.lost or opp.lost or opp.life <= 0 or me.life <= 0:
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
    Leben am Ende), gedrehter Sieg (groesster Rueckstand zwischendurch), gedrehte Niederlage (groesster Vorsprung),
    laengstes Spiel (die meisten Runden, egal wie es ausging; bei Gleichstand die meisten Halbzuege)."""
    wins = [r for r in results if r["winner"] == "a"]
    losses = [r for r in results if r["winner"] == "b"]
    return {
        "closest_win": min(wins, key=lambda r: (_end_life(r, "Wir"), r["round"])) if wins else None,
        "closest_loss": min(losses, key=lambda r: (_end_life(r, "Gegner"), -r["round"])) if losses else None,
        "comeback_win": max(wins, key=lambda r: (_max_gap(r, "Wir"), -r["round"])) if wins else None,
        "comeback_loss": max(losses, key=lambda r: (_max_gap(r, "Gegner"), -r["round"])) if losses else None,
        "longest_game": max(results, key=lambda r: (r["round"], len(r["log"]))) if results else None,
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
