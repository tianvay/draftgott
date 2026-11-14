"""Secrets of Strixhaven (SOS): Wortlaute, die das Modell in anderer Form schon kennt, und neue Felder.

Paket A (Nutzer 2026-11-14): Lebensentzug beim Betreten und Angriff, Loot/Rummage, Tappen mit Stun, Kontern von
Kreaturzaubern, Schluesselwort nach Wahl, Abwerfen als Zusatzkosten, Ziehen mit Treasure bzw. Leben.

sos_traits(card, type_line, base) -> dict mit Card-Feldern, die card_info per _replace uebernimmt (base: die bisher
gelesene Card, damit Ziehen und Leben dazugezaehlt statt ersetzt werden).
"""
import re

from components.cards import GRANTABLE, _clean_lines, _count

_ETB = r"^when (?:~|this [a-z]+) enters, "
_SELF = r"(?:~|this creature)"
_RES = {
    "etb_drain": re.compile(_ETB + r"each opponent loses (\d+) life and you gain (\d+) life\.$"),
    "attack_life": re.compile(rf"^whenever {_SELF} attacks, (?:each opponent loses (\d+) life and )?you gain (\d+) "
                              r"life\.$"),
    "etb_each_lose": re.compile(_ETB + r"draw a card\. each player loses (\d+) life\.$"),
    "you_draw_life": re.compile(r"(?:^|\. )you draw (a|an|one|two|three) cards? and gain (\d+) life\.$"),
    "loot_n": re.compile(r"^(?:when (?:~|this [a-z]+) enters, )?draw (two|three) cards, then discard (two|three) "
                         r"cards\.$"),
    "etb_rummage": re.compile(_ETB + r"you may discard a card\. if you do, draw a card\.$"),
    "enter_attack_loot": re.compile(rf"^whenever {_SELF} enters or attacks, you may draw a card\. if you do, discard a "
                                    r"card\.$"),
    "combat_draw_loss": re.compile(rf"^whenever {_SELF} deals combat damage to a player, you draw (a|one|two) cards? "
                                   r"and lose (\d+) life\.$"),
    "tap_own_stun": re.compile(r"^tap target creature\. if it's your turn, put a stun counter on it\.$"),
    "tap_x_stun": re.compile(r"^tap target creature\. put twice x stun counters on it\.$"),
    "tap_or_untap": re.compile(r"^you may tap or untap target creature\.$"),
    "tap_up_to": re.compile(r"(?:^|\. )tap up to one target creature\.$"),
    "etb_tap_stun": re.compile(_ETB + r"tap target creature an opponent controls\. put a stun counter on it\.$"),
    "counter_creature": re.compile(r"^counter target creature spell\.$"),
    "kw_choice": re.compile(r"\btarget creature gains your choice of ([a-z ]+?) or ([a-z ]+?) until end of turn\.$"),
    "discard_cost": re.compile(r"^as an additional cost to cast this spell, discard (a|one|two) cards?\.$"),
    "draw_treasure": re.compile(r"^draw (a|one|two|three) cards? and create a treasure token\.$"),
}


def sos_traits(card, type_line, base):
    """Card-Felder aus den SOS-Wortlauten (nur Felder, die sich aendern)."""
    spell = "Instant" in type_line or "Sorcery" in type_line
    res, out = _RES, {}
    for _raw, low in _clean_lines(card):
        trigger = bool(re.match(r"^(when|whenever|at the beginning)\b", low))
        if not spell:
            m = res["etb_drain"].match(low)
            if m:  # Lebensverlust ist kein Schaden (120.3 gegen 119.3)
                out["opp_loss"], out["etb_life"] = int(m.group(1)), int(m.group(2))
            m = res["attack_life"].match(low)
            if m:
                out["attack_life"] = (int(m.group(1) or 0), int(m.group(2)))
            m = res["etb_each_lose"].match(low)
            if m:
                out["draws"] = base.draws or 1
                out["opp_loss"], out["life_loss"] = int(m.group(1)), int(m.group(1))
            if res["etb_rummage"].match(low):
                out["etb_rummage"] = True
            if res["enter_attack_loot"].match(low):
                out["loot"], out["attack_loot"] = 1, True
            m = res["combat_draw_loss"].match(low)
            if m:
                out["combat_draw"], out["combat_draw_loss"] = _count(m.group(1)), int(m.group(2))
            if res["etb_tap_stun"].match(low):
                out["etb_tap_opp"] = 2
        m = res["loot_n"].match(low)
        if m and m.group(1) == m.group(2) and (spell or low.startswith("when")):
            out["loot"] = _count({"two": "2", "three": "3"}[m.group(1)])
        if not spell or trigger:
            continue
        m = res["you_draw_life"].search(low)
        if m:
            out["draws"] = base.draws + _count(m.group(1))
            out["spell_life"] = base.spell_life + int(m.group(2))
        if res["tap_own_stun"].match(low):
            out["tap_spell"] = (1, 0, 0)
        elif res["tap_x_stun"].match(low):
            out["tap_spell"] = (0, 0, 2)
        elif res["tap_or_untap"].match(low) or res["tap_up_to"].search(low):
            out["tap_spell"] = (0, 0, 0)
        if res["counter_creature"].match(low):
            out["counter"] = ("creature", (), 0)
        m = res["kw_choice"].search(low)
        if m and m.group(1) in GRANTABLE and m.group(2) in GRANTABLE:
            out["kw_choice"] = (m.group(1), m.group(2))
        m = res["discard_cost"].match(low)
        if m:
            out["discard_cost"] = _count(m.group(1))
        m = res["draw_treasure"].match(low)
        if m:
            out["draws"], out["treasure"] = _count(m.group(1)), base.treasure + 1
    return out
