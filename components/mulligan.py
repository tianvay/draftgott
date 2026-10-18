"""Mulligan-Regeln: Gruende fuer einen Mulligan und das Austeilen der Starthand (London-Mulligan, 103.5)."""
import itertools
import random

from components.mana import can_cast_all, land_key


MULL_COLORS = "Keine Karte nach Farben spielbar"
MULL_LANDS_HIGH = "6 oder mehr Länder"
MULL_LANDS_LOW = "Höchstens 2 Länder und weniger als 3 spielbare Karten"


def color_castable(card, colors):
    """Ist die Karte allein nach den Farben spielbar (Manamenge egal)?"""
    return any(all(c in colors for c, _ in req) for _, req in card.alts)


def mulligan_reasons(hand):
    """Gruende fuer einen Mulligan (leere Liste = Hand behalten)."""
    lands = [c for c in hand if c.is_land]
    spells = [c for c in hand if not c.is_land]
    colors = set().union(*(c.land_colors for c in lands)) if lands else set()
    reasons = []
    if not any(color_castable(c, colors) for c in spells):
        reasons.append(MULL_COLORS)
    if len(lands) >= 6:
        reasons.append(MULL_LANDS_HIGH)
    if len(lands) <= 2:
        key = land_key([c.land_colors for c in lands])
        playable = sum(1 for c in spells if can_cast_all((c.alts,), key))
        if playable < 3:
            reasons.append(MULL_LANDS_LOW)
    if reasons and landcycle_keep(hand):  # Runde 2 Landcycling, Runde 3 etwas spielen
        reasons = [r for r in reasons if r == MULL_LANDS_HIGH]
    return reasons


def landcycle_keep(hand):
    """Hand mit 6 oder 7 Karten, mindestens 2 Laendern (fuer {2} in Runde 2), einer Karte mit Basic Landcycling und
    einer anderen Nichtland-Karte mit Manawert hoechstens 3: wird trotz zu weniger Laender bzw. fehlender Farben
    behalten (das geholte Basic Land bringt die Farbe)."""
    if len(hand) < 6 or sum(c.is_land for c in hand) < 2:
        return False
    spells = [c for c in hand if not c.is_land]
    for i, c in enumerate(spells):
        if c.cycle_alts and c.cycle_target == "basic":
            if any(o.mv <= 3 for j, o in enumerate(spells) if j != i):
                return True
    return False


def choose_keep(hand, k, land_share):
    """London-Mulligan: welche k Karten der 7 unter die Bibliothek? Behalten wird die Auswahl ohne Mulligan-Grund,
    dann mit dem Laenderanteil am naechsten am Deck (land_share; bei Gleichstand ein Land mehr), dann mit den meisten
    mit den behaltenen Laendern bezahlbaren Karten, dann mit den geringsten Manakosten. Gibt (behalten, unten) zurueck."""
    if k <= 0:
        return list(hand), []
    best = None
    seen = set()
    n = len(hand)
    for bottom in itertools.combinations(range(n), k):
        kept = [hand[i] for i in range(n) if i not in bottom]
        names = tuple(sorted(c.name for c in kept))
        if names in seen:
            continue
        seen.add(names)
        lands = [c for c in kept if c.is_land]
        lkey = land_key([c.land_colors for c in lands])
        castable = sum(1 for c in kept if not c.is_land and can_cast_all((c.alts,), lkey))
        score = (not mulligan_reasons(kept), -abs(len(lands) - land_share * len(kept)), len(lands), castable,
                 -sum(c.mv for c in kept if not c.is_land))
        if best is None or score > best[0]:
            best = (score, kept, [hand[i] for i in bottom])
    return best[1], best[2]


def deal_opening(cards, mulligan, min_hand, keep_at_min=False):
    """Zieht die Starthand. Bei Mulligan: Deck neu mischen, wieder 7 Karten, je Mulligan eine unter die Bibliothek.
    Faellt die Hand unter min_hand Karten, ist das Spiel verloren (hand = None); mit keep_at_min wird stattdessen die
    Hand mit min_hand Karten behalten (der Gegner im Kampf gibt nie auf).
    London-Mulligan (103.5): immer 7 Karten ziehen, nach k Mulligans k davon unter die Bibliothek (choose_keep).
    Gibt (Hand, Bibliothek, Anzahl Mulligans, Gruende der ersten 7er-Hand) zurueck."""
    mulls, first = 0, None
    share = sum(c.is_land for c in cards) / len(cards) if cards else 0
    while True:
        deck = cards[:]
        random.shuffle(deck)
        drawn, library = deck[:7], deck[7:]
        hand, bottom = choose_keep(drawn, mulls, share)
        reasons = mulligan_reasons(hand)
        if first is None:
            first = reasons
        if not mulligan or not reasons:
            return hand, library + bottom, mulls, first
        if len(hand) - 1 < min_hand:
            if keep_at_min:
                return hand, library + bottom, mulls, first
            return None, None, mulls + 1, first
        mulls += 1
