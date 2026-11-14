"""Secrets of Strixhaven (SOS): Wortlaute, die das Modell in anderer Form schon kennt, und neue Felder.

Paket A (Nutzer 2026-11-14): Lebensentzug beim Betreten und Angriff, Loot/Rummage, Tappen mit Stun, Kontern von
Kreaturzaubern, Schluesselwort nach Wahl, Abwerfen als Zusatzkosten, Ziehen mit Treasure bzw. Leben.

sos_traits(card, type_line, base) -> dict mit Card-Feldern, die card_info per _replace uebernimmt (base: die bisher
gelesene Card, damit Ziehen und Leben dazugezaehlt statt ersetzt werden).
"""
import re

from components.cards import GRANTABLE, _clean_lines, _count, cost_alternatives, grant_list, token_card

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


PEST = token_card("Pest", creature=True, power=1, toughness=1, artifact=False, types=("pest",))._replace(
    attack_life=(0, 1))
_PEST = (r"create (a|two|three) 1/1 black and green pest creature tokens? with \"whenever this token attacks, you gain "
         r"1 life\.\"")
_INF = r"^infusion — "
# Paket C: Leben und Infusion
_LIFE_RES = {
    "pest_etb": re.compile(_ETB + _PEST + "$"),
    "pest_dies": re.compile(r"^when (?:~|this creature) dies, " + _PEST + "$"),
    "pest_spell": re.compile("^" + _PEST + "$"),
    "self_or_ally_life": re.compile(rf"^whenever {_SELF} or another creature you control enters, you gain (\d+) "
                                    r"life\.$"),
    "growth_counter": re.compile(r"^whenever you gain life, put a growth counter on this enchantment\.$"),
    "growth_anthem": re.compile(r"^as long as there are (two|three|four|five|six|seven|\d+) or more growth counters on "
                                r"this enchantment, creatures you control get \+(\d+)/\+(\d+)\.$"),
    "lifegain_types": re.compile(r"^whenever you gain life, put (a|one|two) \+1/\+1 counters? on each ([a-z, ]+) you "
                                 r"control\.$"),
    "death_drain": re.compile(r"^whenever a creature you control (with power or toughness 1 or less )?dies, "
                              r"(?:target|each) opponent loses (\d+) life and you gain (\d+) life\.$"),
    "end_death_draw": re.compile(r"^at the beginning of your end step, if a creature died under your control this "
                                 r"turn, draw (a|one|two) cards?\.$"),
    "infusion_loss": re.compile(_INF + r"if you gained life this turn, that creature's controller loses (\d+) life\.$"),
    "infusion_debuff": re.compile(_INF + r"when (?:~|this creature) enters, target creature an opponent controls gets "
                                  r"-(\d+)/-\1 until end of turn if you gained life this turn\.$"),
    "infusion_counters": re.compile(_INF + r"when (?:~|this creature) enters, put (a|one|two|three) \+1/\+1 counters? "
                                    r"on it if you gained life this turn\.$"),
    "infusion_kw": re.compile(_INF + r"if you gained life this turn, that creature also gains ([a-z ,]+?) until end of "
                              r"turn\.$"),
    "infusion_sacrifice": re.compile(_INF + r"at the beginning of your end step, sacrifice a permanent unless you "
                                     r"gained life this turn\.$"),
    "infusion_reanimate": re.compile(_INF + r"at the beginning of your end step, if you gained life this turn, return "
                                     r"up to one target creature card with mana value x or less from your graveyard to "
                                     r"the battlefield, where x is the amount of life you gained this turn\.$"),
    "dig_infusion": re.compile(_INF + r"look at the top four cards of your library\. you may reveal a creature or land "
                               r"card from among them and put it into your hand\. if you gained life this turn, you "
                               r"may instead reveal two creature and/or land cards from among them and put them into "
                               r"your hand\. put the rest on the bottom of your library in a random order\.$"),
    "x_life": re.compile(r"^target player gains x life\.$"),
}
_PLURAL = {"pests": "pest", "bats": "bat", "insects": "insect", "snakes": "snake", "spiders": "spider"}


def _life_traits(card, low, spell):
    """Paket C: Leben und Infusion (eine Zeile)."""
    res, out = _LIFE_RES, {}
    m = res["pest_spell" if spell else "pest_etb"].match(low)
    if m:
        out["creates_tokens"] = ((_count(m.group(1)), PEST),)
    m = res["pest_dies"].match(low)
    if m and not spell:
        out["death_tokens"] = ((_count(m.group(1)), PEST),)
    m = res["self_or_ally_life"].match(low)
    if m and not spell:  # Bogwater Lumaret: sie selbst und jede andere eigene Kreatur
        out["etb_life"] = out["ally_enter_life"] = int(m.group(1))
    if res["growth_counter"].match(low):
        out["growth_counter"] = True
    m = res["growth_anthem"].match(low)
    if m:
        n = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7}.get(m.group(1)) or int(m.group(1))
        out["cond_static"] = ((("growth", n, card.get("name", "")), "team", int(m.group(2)), int(m.group(3)), ()),)
    m = res["lifegain_types"].match(low)
    if m and "," in m.group(2):  # nur Listen (Blech); ein Typ allein ist lifegain_counter (Lyra)
        words = [w.strip() for w in re.split(r",|\band\b", m.group(2)) if w.strip()]
        types = tuple(_PLURAL.get(w, w.rstrip("s")) for w in words)
        out["lifegain_counter_types"] = (_count(m.group(1)), types)
    m = res["death_drain"].match(low)
    if m:
        out["death_drain"] = (int(m.group(2)), int(m.group(3)), bool(m.group(1)))
    m = res["end_death_draw"].match(low)
    if m:
        out["end_death_draw"] = _count(m.group(1))
    m = res["infusion_loss"].match(low)
    if m:
        out["infusion_loss"] = int(m.group(1))
    m = res["infusion_debuff"].match(low)
    if m:
        out["infusion_debuff"] = int(m.group(1))
    m = res["infusion_counters"].match(low)
    if m:
        out["infusion_counters"] = _count(m.group(1))
    m = res["infusion_kw"].match(low)
    if m and grant_list(m.group(1)) and not grant_list(m.group(1))[1]:
        out["infusion_kw"] = grant_list(m.group(1))[0]
    if res["infusion_sacrifice"].match(low):
        out["infusion_sacrifice"] = True
    if res["infusion_reanimate"].match(low):
        out["infusion_reanimate"] = True
    if res["dig_infusion"].match(low) and spell:
        out["top_dig"], out["dig_infusion"] = (4, "creature_land", False), True
    if res["x_life"].match(low) and spell:
        out["x_life"] = True
    return out


_COST = r"((?:\{[^}]+\})+)"
_LEAVE = r"^whenever one or more cards leave your graveyard, "
# Paket D: Friedhof
_GY_RES = {
    "leave_pump": re.compile(_LEAVE + rf"{_SELF} gets \+(\d+)/\+(\d+) until end of turn\.$"),
    "leave_counter": re.compile(_LEAVE + rf"put (a|one|two) \+1/\+1 counters? on {_SELF}\.$"),
    "leave_ping": re.compile(_LEAVE + r"(?:~|this artifact|this creature|this enchantment) deals (\d+) damage to each "
                             r"opponent and you gain (\d+) life\.$"),
    "end_gy_draw": re.compile(r"^at the beginning of your end step, if a card left your graveyard this turn, draw "
                              r"(a|one|two) cards?\.$"),
    "attack_gy_pump": re.compile(r"^whenever you attack, if a card left your graveyard this turn, target attacking "
                                 r"creature gets \+(\d+)/\+(\d+) until end of turn\.$"),
    "gy_left_discount": re.compile(r"^this spell costs \{(\d+)\} less to cast if one or more cards left your graveyard "
                                   r"this turn\.$"),
    "gy_life_surveil": re.compile("^" + _COST + r", exile this card from your graveyard: you gain (\d+) life\. surveil "
                                  r"(\d+)\. activate only as a sorcery\.$"),
    "gy_hand_sorcery": re.compile("^" + _COST + r": return this card from your graveyard to your hand\. activate only "
                                  r"as a sorcery\.$"),
    "gy_return_exile_instsorc": re.compile("^" + _COST + r", exile an instant or sorcery card from your graveyard: "
                                           r"return this card from your graveyard to the battlefield\.$"),
    "gy_combat_return": re.compile(r"^whenever one or more creatures you control deal combat damage to a player, you may "
                                   r"pay " + _COST + r"\. if you do, return this card from your graveyard to your "
                                   r"hand\.$"),
    "rubble_ping": re.compile(r"^\{t\}, exile a card from your graveyard: add \{r\}\. when you do, (?:~|this creature) "
                              r"deals 1 damage to each opponent\.$"),
    "cauldron": re.compile("^" + _COST + r", \{t\}, sacrifice a creature: return target creature card from your "
                           r"graveyard to the battlefield\. activate only as a sorcery\.$"),
    "combat_exile_gy": re.compile(r"^at the beginning of combat on your turn, exile up to one target card from a "
                                  r"graveyard\.$"),
    "etb_instsorc": re.compile(_ETB + r"return target instant or sorcery card from your graveyard to your hand\.$"),
    "x_regrowth": re.compile(r"^return up to x target instant and/or sorcery cards from your graveyard to your hand\.$"),
    "all_instsorc": re.compile(r"^return all instant and sorcery cards from your graveyard to your hand\. you have no "
                               r"maximum hand size for the rest of the game\.$"),
    "self_exile": re.compile(r"^exile ~\.$"),
    "repartee_reanimate": re.compile(r"^repartee — whenever you cast an instant or sorcery spell that targets a "
                                     r"creature, return target creature card from your graveyard to the "
                                     r"battlefield\.$"),
    "scrollsmith": re.compile(_ETB + r"exile target noncreature, nonland card from your graveyard\. until the end of "
                              r"your next turn, you may cast that card\.$"),
    "named_gy_pump": re.compile(r"^target creature gains trample and gets \+x/\+0 until end of turn, where x is 1 plus "
                                r"the number of cards named ~ in your graveyard\.$"),
}


def _gy_traits(low, spell):
    """Paket D: Friedhof (eine Zeile)."""
    res, out = _GY_RES, {}

    def alts(m):
        return cost_alternatives(m.group(1).upper())
    m = res["leave_pump"].match(low)
    if m:
        out["gy_leave"] = ("pump_self", (int(m.group(1)), int(m.group(2))), False)
    m = res["leave_counter"].match(low)
    if m:
        out["gy_leave"] = ("counter_self", _count(m.group(1)), False)
    m = res["leave_ping"].match(low)
    if m:
        out["gy_leave"] = ("ping_life", (int(m.group(1)), int(m.group(2))), False)
    m = res["end_gy_draw"].match(low)
    if m:
        out["end_gy_draw"] = _count(m.group(1))
    m = res["attack_gy_pump"].match(low)
    if m:
        out["attack_gy_pump"] = (int(m.group(1)), int(m.group(2)))
    m = res["gy_left_discount"].match(low)
    if m and spell:
        out["self_discount"] = ("gy_left", int(m.group(1)))
    m = res["gy_life_surveil"].match(low)
    if m:  # Stone Docent
        out["gy_ability"] = (alts(m), (("life", int(m.group(2))), ("surveil", int(m.group(3)))))
        out["gy_ability_sorcery"] = True
    m = res["gy_hand_sorcery"].match(low)
    if m:  # Summoned Dromedary
        out["gy_return"] = (alts(m), "hand", False, 0, "", "sorcery")
    m = res["gy_return_exile_instsorc"].match(low)
    if m:  # Postmortem Professor
        out["gy_return"] = (alts(m), "battlefield", False, 0, "exile_instsorc", "")
    m = res["gy_combat_return"].match(low)
    if m:
        out["gy_combat_return"] = alts(m)
    if res["rubble_ping"].match(low):
        out["rubble_ping"] = True
    m = res["cauldron"].match(low)
    if m:
        out["cauldron_reanimate"] = alts(m)
    if res["combat_exile_gy"].match(low):
        out["combat_exile_gy"] = True
    if res["etb_instsorc"].match(low) and not spell:
        out["reanimate"] = ("target", "instsorc", 99, "hand", 0)
    if spell and res["x_regrowth"].match(low):
        out["x_regrowth"] = True
    if spell and res["all_instsorc"].match(low):  # das Modell kennt kein Handkartenlimit
        out["reanimate"] = ("all", "instsorc", 99, "hand", 0)
    if spell and res["self_exile"].match(low):
        out["self_exile"] = True
    if res["repartee_reanimate"].match(low):
        out["cast_trig"] = (("instsorc_creature", (("reanimate_creature",),), (), ""),)
    if res["scrollsmith"].match(low):
        out["scrollsmith"] = True
    if spell and res["named_gy_pump"].match(low):
        out["named_gy_pump"] = True
    return out


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
        out.update(_life_traits(card, low, spell))
        out.update(_gy_traits(low, spell))
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
