"""Empower Jace: Zustand von Jace in der Simulation, Filter fuer Effekte und die statische Analyse eines Decks."""
from functools import lru_cache

from components.cards import EMPOWER_ONCE, EMPOWER_RECURRING


def surveil(library, n, hand, battlefield):
    """Surveil n: die obersten n Karten ansehen. Ein Land bleibt oben, solange die teuerste Karte auf der Hand nicht
    bezahlbar ist, weil Laender fehlen (Laender auf dem Feld und auf der Hand < ihr Manawert); sonst kommt es in den
    Friedhof. Zauber bleiben immer oben. Die Reihenfolge der behaltenen Karten bleibt gleich.
    Veraendert library und gibt die abgelegten Karten zurueck."""
    top, rest = library[:n], library[n:]
    spells = [c for c in hand if not c.is_land]
    need = max((c.mv for c in spells), default=None)
    have = len(battlefield) + sum(1 for c in hand if c.is_land)
    keep, binned = [], []
    for card in top:
        if card.is_land:
            if need is not None and have < need:
                keep.append(card)
                have += 1
            else:
                binned.append(card)
        else:
            keep.append(card)
    library[:] = keep + rest
    return binned


class JaceState:
    """Jace-Planeswalker-Token: nur eine Zahl (Loyalty). Bei 0 Loyalty gibt es keinen Token mehr,
    ein weiterer Empower erstellt einen neuen. Hoechstens eine Aktivierung pro Runde:
    ab 3 Loyalty -3 (Karte ziehen), sonst -1 (Surveil 1, nur wenn erlaubt; auch bis 0)."""
    __slots__ = ("loyalty", "used", "acts", "gained", "first", "surveils", "surveil_lands", "events", "graveyard",
                 "zero_alive")

    def __init__(self):
        self.loyalty = 0
        self.used = False
        self.acts = 0
        self.gained = 0
        self.first = None
        self.surveils = 0
        self.surveil_lands = 0
        self.events = 0          # wie oft Loyalty dazukam (fuer "whenever you put loyalty counters", Tethermage)
        self.graveyard = None    # Friedhof der Simulation (abgelegte Laender beim Surveil)
        self.zero_alive = False  # liegt mit 0 Loyalty weiter (Sanctum Lurker)

    def add(self, n):
        if n > 0:
            self.loyalty += n
            self.gained += n
            self.events += 1

    def try_activate(self, hand, library, turn, battlefield=None, allow_surveil=False):
        """Ab 3 Loyalty: -3, eine Karte ziehen. Darunter (wenn allow_surveil, also nach dem Zaubern): -1, Surveil 1.
        acts zaehlt nur das Ziehen, surveils das Surveil."""
        if self.used or not library or self.loyalty <= 0:
            return False
        if self.loyalty < 3:
            if not allow_surveil:
                return False
            self.loyalty -= 1
            self.used = True
            self.surveils += 1
            binned = surveil(library, 1, hand, battlefield or [])
            self.surveil_lands += len(binned)
            if self.graveyard is not None:
                self.graveyard.extend(binned)
            return True
        self.loyalty -= 3
        self.used = True
        self.acts += 1
        if self.first is None:
            self.first = turn
        hand.append(library.pop(0))
        return True


@lru_cache(maxsize=None)
def recurring_effects(card):
    """Wiederkehrende, modellierbare Empower-Effekte der Vorderseite (Ausloeser, bezahlbare Faehigkeiten)."""
    return tuple(e for e in card.empower if e[0] == 0 and e[1] in EMPOWER_RECURRING and not e[6])


@lru_cache(maxsize=None)
def once_effects(card):
    """Einmalige Empower-Effekte der Vorderseite (Zauber, beim Betreten)."""
    return tuple(e for e in card.empower if e[0] == 0 and e[1] in ("spell", "etb") and not e[6])


def creates_walker(card):
    """Erschafft das Wirken dieser Karte einen Planeswalker (Planeswalker-Karte oder Empower Jace, das den
    Jace-Token erschafft)?"""
    return card.is_planeswalker or creates_jace(card)


def creates_jace(card):
    """Liegt nach dem Wirken ein Jace auf dem Tisch (Jace-Karte oder Empower Jace mit mindestens 1 Loyalty)?"""
    return card.is_jace or any(e[2] > 0 for e in once_effects(card))


def cast_filter_matches(filt, card):
    if filt == "noncreature":
        return not card.is_creature
    if filt == "creature":
        return card.is_creature
    if filt == "instant_sorcery":
        return card.is_instant_sorcery
    return True


def enter_filter_matches(filt, card):
    if filt == "creature":
        return card.is_creature
    if filt == "land":
        return card.is_land
    return True


def analyze_jace(rows):
    """Zaehlt Empower-Jace-Karten und weitere Jace-/Planeswalker-Bezuege (aus den Kartentexten)."""
    kinds = ["spell", "etb", "other_once", "trigger", "activated", "unknown"]
    cat = {k: {"copies": 0, "cards": 0, "sum": 0} for k in kinds}
    out = {"cat": cat, "cards": [], "empower_copies": 0, "empower_cards": 0, "once_copies": 0, "once_sum": 0,
           "rec_copies": 0, "rec_sum": 0, "x_cards": [], "unmodeled": [],
           "tags": {t: {"copies": 0, "cards": 0} for t in ("jace", "pw_help", "pw_removal", "is_pw")}}
    for name, qty, card, shown in rows:
        eff, tags = card.empower, card.pw_tags
        if not eff and not tags:
            continue
        rec = {"name": name, "qty": qty, "kinds": [], "values": [], "tags": list(tags), "text": card.empower_text}
        seen = set()
        once_n = rec_n = 0
        for fi, kind, n, trig, cost, tap, unmod, xval in eff:
            seen.add(kind)
            cat[kind]["sum"] += qty * n
            if kind in EMPOWER_ONCE:
                once_n += n
            elif kind in EMPOWER_RECURRING:
                rec_n += n
            rec["values"].append(f"{n}{'+X' if xval and n else ''}" if (n or not xval) else "X")
            if xval and name not in out["x_cards"]:
                out["x_cards"].append(name)
            if unmod and name not in out["unmodeled"]:
                out["unmodeled"].append(name)
        for k in seen:
            cat[k]["copies"] += qty
            cat[k]["cards"] += 1
        rec["kinds"] = sorted(seen, key=kinds.index)
        if eff:
            out["empower_copies"] += qty
            out["empower_cards"] += 1
        if seen & set(EMPOWER_ONCE):
            out["once_copies"] += qty
            out["once_sum"] += qty * once_n
        if seen & set(EMPOWER_RECURRING):
            out["rec_copies"] += qty
            out["rec_sum"] += qty * rec_n
        for t in tags:
            out["tags"][t]["copies"] += qty
            out["tags"][t]["cards"] += 1
        out["cards"].append(rec)
    out["any"] = bool(out["cards"])
    return out
