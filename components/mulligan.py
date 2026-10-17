"""Mulligan-Regeln: Gruende fuer einen Mulligan und das Austeilen der Starthand."""
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
    return reasons


def deal_opening(cards, mulligan, min_hand, keep_at_min=False):
    """Zieht die Starthand. Bei Mulligan: Deck neu mischen, eine Karte weniger.
    Faellt die Hand unter min_hand Karten, ist das Spiel verloren (hand = None); mit keep_at_min wird stattdessen die
    Hand mit min_hand Karten behalten (der Gegner im Kampf gibt nie auf).
    Gibt (Hand, Bibliothek, Anzahl Mulligans, Gruende der ersten 7er-Hand) zurueck."""
    size, mulls, first = 7, 0, None
    while True:
        deck = cards[:]
        random.shuffle(deck)
        hand, library = deck[:size], deck[size:]
        reasons = mulligan_reasons(hand)
        if first is None:
            first = reasons
        if not mulligan or not reasons:
            return hand, library, mulls, first
        if size - 1 < min_hand:
            if keep_at_min:
                return hand, library, mulls, first
            return None, None, mulls + 1, first
        size -= 1
        mulls += 1
