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


_PREP = r"(?:~|this creature) becomes prepared\."
# Paket B: Ausloeser, die eine Kreatur prepared machen (Art -> Muster der Zeile der Vorderseite)
_PREPARE_RES = {
    "etb_inkling": re.compile(r"^when (?:~|this creature) enters, target player creates a 1/1 white and black inkling "
                              r"creature token with flying\. then if an opponent controls more creatures than you, "
                              + _PREP + "$"),
    "end_opp_hand": re.compile(r"^at the beginning of each end step, if an opponent has more cards in hand than you, "
                               + _PREP + "$"),
    "tokens": re.compile(r"^whenever one or more tokens you control enter, " + _PREP + "$"),
    "attack": re.compile(r"^whenever (?:~|this creature) attacks, it becomes prepared\.$"),
    "tap3": re.compile(r"^\{t\}, tap two untapped creatures you control: " + _PREP + "$"),
    "end_deaths2": re.compile(r"^at the beginning of your end step, if two or more creatures died this turn, "
                              + _PREP + "$"),
    "upkeep_gy3": re.compile(r"^at the beginning of your upkeep, surveil 1\. then if there are three or more creature "
                             r"cards in your graveyard, " + _PREP + "$"),
    "first_life": re.compile(r"^whenever you gain life for the first time each turn, " + _PREP + "$"),
    "main1": re.compile(r"^at the beginning of your first main phase, " + _PREP + "$"),
    "main2_life2": re.compile(r"^at the beginning of your second main phase, if you gained 2 or more life this turn, "
                              + _PREP + "$"),
    "third_spell": re.compile(r"^whenever you cast your third spell each turn, " + _PREP + "$"),
    "creature_cast": re.compile(r"^whenever you cast a creature spell, " + _PREP + "$"),
    "gy_leave": re.compile(r"^whenever one or more cards leave your graveyard, " + _PREP + "$"),
    "landfall": re.compile(r"^landfall — whenever a land you control enters, " + _PREP + "$"),
    "attack_exile8": re.compile(r"^whenever (?:~|this creature) attacks, you may exile eight cards from your "
                                r"graveyard\. if you do, " + _PREP + "$"),
    "attack_lands8": re.compile(r"^whenever (?:~|this creature) attacks, if you control eight or more lands, "
                                + _PREP + "$"),
    "gy_creature": re.compile(r"^exile a creature card from your graveyard: " + _PREP + r" activate only as a "
                              r"sorcery\.$"),
}
_SPELL_RES = {
    "pump_each": re.compile(r"^one or two target creatures each get \+(\d+)/\+(\d+) until end of turn\.$"),
    "brainstorm": re.compile(r"^draw three cards, then put two cards from your hand on top of your library in any "
                             r"order\.$"),
    "tutor_any": re.compile(r"^search your library for a card, put that card into your hand, then shuffle\.$"),
    "tutor_instsorc": re.compile(r"^search your library for an instant or sorcery card, reveal it, put it into your "
                                 r"hand, then shuffle\.$"),
    "regrowth": re.compile(r"^return target card from your graveyard to your hand\.$"),
    "reanimate_any": re.compile(r"^put target creature card from a graveyard onto the battlefield under your control\. "
                                r"you lose life equal to that card's mana value\.$"),
    # Pack a Punch (auch der Rest, den die Modell-Abdeckung nach den Marken prueft)
    # "target player": wir waehlen uns selbst (Ancestral Recall, Sign in Blood, FRA Ancestral Craving)
    "target_draws": re.compile(r"^target player draws (a|one|two|three) cards?(?: and loses (\d+) life)?\.$"),
    "each_draw": re.compile(r"^you and target opponent each draw (a|one|two|three) cards?\.$"),
    "mill_counters_kw": re.compile(r"^mill a card\. (?:put two \+1/\+1 counters on target creature\. )?it gains "
                                   r"([a-z ]+?) until end of turn\.$"),
}
_TOMEKEEPER_HEAD = re.compile(r"^when (?:~|this creature) enters, choose up to one —$")
_TOMEKEEPER_BULLETS = ("target creature becomes prepared.", "target creature becomes unprepared.")


def prepare_triggers(card):
    """Paket B: Arten der Ausloeser, die die Vorderseite prepared machen (Reihenfolge wie im Text)."""
    if card.get("layout") != "prepare":
        return ()
    found = []
    for _raw, low in _clean_lines(card):
        for kind, rx in _PREPARE_RES.items():
            if rx.match(low):
                found.append(kind)
    return tuple(found)


def _spell_traits(low, base):
    """Paket B: offene Zauberhaelften (auch als eigene Karten)."""
    res, out = _SPELL_RES, {}
    m = res["pump_each"].match(low)
    if m:  # Scrollboost: zwei Ziele
        out["modes"] = ((("pump_each", int(m.group(1)), 2),),)
        out["pump_tough"] = ((int(m.group(2)),),)
    if res["brainstorm"].match(low):
        out["draws"], out["brainstorm"] = 3, 2
    if res["tutor_any"].match(low):
        out["tutor"] = ("any",)
    if res["tutor_instsorc"].match(low):
        out["tutor"] = ("instant_sorcery",)
    if res["regrowth"].match(low):
        out["reanimate"] = ("target", "card", 99, "hand", 0)
    if res["reanimate_any"].match(low):
        out["reanimate_any"] = True
    m = res["target_draws"].match(low)
    if m:  # wir waehlen uns selbst (Nutzer 2026-11-14: zaehlt als Ziehen, auch im Goldfish)
        out["draws"] = _count(m.group(1))
        if m.group(2):
            out["life_loss"] = int(m.group(2))
    m = res["each_draw"].match(low)
    if m:  # Secret Rendezvous: der Gegner zieht genauso viele
        out["draws"] = out["opp_draws"] = _count(m.group(1))
    m = res["mill_counters_kw"].match(low)
    if m and m.group(1) in GRANTABLE:
        out["mill_self"], out["grant_kw"] = 1, (m.group(1),)
    return out


def sos_traits(card, type_line, base):
    """Card-Felder aus den SOS-Wortlauten (nur Felder, die sich aendern)."""
    spell = "Instant" in type_line or "Sorcery" in type_line
    res, out = _RES, {}
    if base.prepared:
        kinds = prepare_triggers(card)
        if kinds:
            out["prepare_on"] = kinds
            if "upkeep_gy3" in kinds:
                out["upkeep_surveil"] = 1  # Grave Researcher: Surveil vor der Pruefung
    lines = list(_clean_lines(card))
    if not spell and lines and any(_TOMEKEEPER_HEAD.match(low) for _r, low in lines):
        bullets = [low.lstrip("•").strip() for r, low in lines if r.strip().startswith("•")]
        if all(b in _TOMEKEEPER_BULLETS for b in bullets):
            out["tomekeeper"] = True
    for _raw, low in lines:
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
        out.update(_spell_traits(low, base))
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
