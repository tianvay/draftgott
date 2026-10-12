#!/usr/bin/env python3
"""
MTG Starthand-Simulator -> erzeugt einen HTML-Bericht

Aufruf:  python mtg_sim.py deck.txt [--sims 100] [--turns 3] [--max-runden 15]
                                    [--ausgabe bericht.html] [--nicht-oeffnen]

Ablauf pro Runde: ziehen (Play: nicht in Runde 1) -> Land legen -> Zaubern.
Die genaue Spiellogik steht im Bericht (Abschnitt "Spiellogik").
"""
import argparse
import datetime
import html as html_lib
import itertools
import random
import re
import pathlib
import statistics
import sys
import urllib.error
import webbrowser
from collections import Counter
from functools import lru_cache
from typing import NamedTuple

from scryfall import fetch_cards_cached

SECTIONS = {"about", "deck", "sideboard", "commander", "companion"}
COLORS = set("WUBRGC")

# ---------------------------------------------------------------- Ampel
# Ampel fuer "mindestens einen Zauber gespielt" je Runde: (gruen ab, gelb ueber)
# Wert >= gruen -> gruen, Wert > gelb -> gelb, sonst rot. Gerechnet wird mit der angezeigten ganzen Prozentzahl.
TRAFFIC = {
    False: {1: (20, 0), 2: (90, 80), 3: (95, 90)},   # On the Play
    True:  {1: (22, 0), 2: (92, 83), 3: (96, 85)},   # On the Draw
}


def traffic_level(pct, on_draw, turn):
    """Gibt 'green', 'yellow' oder 'red' fuer Runde 1-3 zurueck, sonst None."""
    limits = TRAFFIC[on_draw].get(turn)
    if limits is None:
        return None
    green, yellow = limits
    if pct >= green:
        return "green"
    if pct > yellow:
        return "yellow"
    return "red"


class Card(NamedTuple):
    is_land: bool
    mv: int             # Manawert
    alts: tuple         # Zahlungswege: ((generisch, ((Farbe, Anzahl), ...)), ...)
    land_colors: tuple  # Farben, die ein Land erzeugen kann
    is_creature: bool
    is_aura: bool
    power: int          # Basiswerte; '*' wird als 0 gezaehlt
    toughness: int
    haste: bool = False
    tap_mode: str = "no"      # Landlogik: no / tapped / tapped? / fast / slow / check
    tap_arg: tuple = ()        # bei 'check': Landtypen, die das Land untapped machen
    land_types: tuple = ()     # Landtypen (plains, island, ...) fuer Check-Lands
    name: str = ""
    is_basic: bool = False     # Basic Land?
    cycle_alts: tuple = ()     # Kosten des (Basic-)Landcyclings als Zahlungswege
    cycle_target: str = ""     # "basic", "land" oder Landtyp (plains, island, ...)
    cycle_mv: int = 0          # Manawert der Cycling-Kosten
    is_instant_sorcery: bool = False
    is_planeswalker: bool = False
    empower: tuple = ()        # Effekte: (Seite, Art, Wert, Ausloeser, Kosten, Tap, nicht_modelliert, X)
    empower_text: str = ""     # erkannte Textzeilen (zur Kontrolle im Bericht)
    pw_tags: tuple = ()        # jace / pw_help / pw_removal / is_pw


# ---------------------------------------------------------------- Deck einlesen
def parse_deck_name(text, fallback):
    """Liest die Zeile 'Name ...' aus dem Abschnitt About."""
    m = re.search(r"^\s*Name[ \t]+(.+?)\s*$", text, re.M | re.I)
    return m.group(1) if m else fallback


def parse_deck(text):
    """Liest 'N Kartenname' im Abschnitt 'Deck'. Gibt {name: anzahl} zurueck."""
    deck, section = {}, None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.lower() in SECTIONS:
            section = line.lower()
            continue
        if section not in (None, "deck"):
            continue
        m = re.match(r"^(\d+)x?\s+(.+?)(?:\s+\([A-Za-z0-9]+\)\s*\S*)?$", line)
        if m:
            name = m.group(2).strip()
            deck[name] = deck.get(name, 0) + int(m.group(1))
    return deck


# ---------------------------------------------------------------- Kosten
def mana_value(mana_cost):
    total = 0
    for sym in re.findall(r"\{([^}]+)\}", mana_cost or ""):
        if sym.isdigit():
            total += int(sym)
        elif sym.upper() == "X":
            pass
        elif "/" in sym and sym.split("/")[0].isdigit():
            total += int(sym.split("/")[0])  # {2/W}
        else:
            total += 1
    return total


def symbol_options(sym):
    """Zahlungsoptionen eines Manasymbols als [(generisch, farbe|None)]."""
    if sym.isdigit():
        return [(int(sym), None)]
    if sym.upper() == "X":
        return [(0, None)]
    if sym in COLORS:
        return [(0, sym)]
    if sym == "S":  # Snow: vereinfacht als 1 generisches Mana
        return [(1, None)]
    if "/" in sym:
        parts = sym.split("/")
        if parts[-1] == "P":  # Phyrexian: Farbe ODER 2 Leben (= 0 Mana)
            return [(0, p) for p in parts[:-1] if p in COLORS] + [(0, None)]
        opts = []
        for p in parts:
            if p.isdigit():
                opts.append((int(p), None))
            elif p in COLORS:
                opts.append((0, p))
        return opts or [(1, None)]
    return [(1, None)]


def cost_alternatives(mana_cost):
    """Wandelt '{1}{W/U}{B}' in alle moeglichen Zahlungswege um."""
    if not mana_cost:
        return ()  # keine Manakosten -> nicht normal castbar
    alts = [(0, Counter())]
    for sym in re.findall(r"\{([^}]+)\}", mana_cost):
        new = []
        for g, cnt in alts:
            for og, oc in symbol_options(sym):
                c2 = Counter(cnt)
                if oc:
                    c2[oc] += 1
                new.append((g + og, c2))
        alts = new
    return tuple(sorted({(g, tuple(sorted(c.items()))) for g, c in alts}))


def can_pay(producing, generic, req):
    """Koennen die Laender (jeweils 1 Mana einer ihrer Farben) generic + req bezahlen?
    Farbanforderungen werden per Matching auf verschiedene Laender verteilt."""
    units = [c for c, n in req.items() for _ in range(n)]
    if len(producing) < generic + len(units):
        return False
    match = [-1] * len(producing)

    def assign(u, seen):
        for j, lc in enumerate(producing):
            if units[u] in lc and j not in seen:
                seen.add(j)
                if match[j] == -1 or assign(match[j], seen):
                    match[j] = u
                    return True
        return False

    return all(assign(u, set()) for u in range(len(units)))


@lru_cache(maxsize=None)
def can_cast_all(alts_list, lands_key):
    """Koennen alle diese Zauber gleichzeitig bezahlt werden? (alle Hybrid-Wege werden probiert)"""
    if any(not a for a in alts_list):
        return False
    producing = [lc for lc in lands_key if lc]
    for combo in itertools.product(*alts_list):
        generic = sum(g for g, _ in combo)
        req = Counter()
        for _, r in combo:
            for c, n in r:
                req[c] += n
        if can_pay(producing, generic, req):
            return True
    return False


@lru_cache(maxsize=None)
def has_two_colors(lands_key):
    """Koennen zwei verschiedene Laender zwei verschiedene Farben erzeugen? Farblos (C) zaehlt nicht."""
    cols = [tuple(c for c in lc if c != "C") for lc in lands_key]
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            if any(a != b for a in cols[i] for b in cols[j]):
                return True
    return False


def required_colors(card):
    """Farben, die die Karte in JEDEM Zahlungsweg braucht (Hybrid wie {R/G} verlangt keine bestimmte Farbe)."""
    sets = [{col for col, _ in req if col != "C"} for _, req in card.alts]
    return set.intersection(*sets) if sets else set()


LANDCYCLE_RE = re.compile(
    r"(basic land|plains|island|swamp|mountain|forest|land)cycling\s*((?:\{[^}]+\})+)", re.I)
TAPPED_RE = re.compile(r"enters( the battlefield)? tapped")


def land_tap_info(card, front):
    """Liest aus dem Kartentext, ob/wann ein Land getappt ins Spiel kommt.
    Modi: no (nie), tapped (immer), tapped? (Bedingung nicht modelliert -> wie 'tapped' gezaehlt),
          fast (untapped, wenn hoechstens 2 andere Laender), slow (untapped ab 2 anderen Laendern),
          check (untapped, wenn du einen der genannten Landtypen kontrollierst)."""
    text = (front.get("oracle_text") or card.get("oracle_text") or "").lower()
    if not TAPPED_RE.search(text):
        return "no", ()
    if "pay 2 life" in text:        # Shock-Land: Leben wird bezahlt
        return "no", ()
    if "two or fewer other lands" in text:
        return "fast", ()
    if "two or more other lands" in text:
        return "slow", ()
    m = re.search(r"unless you control ((?:an? [a-z]+(?:,? or |, | or )?)+)", text)
    if m:
        types = tuple(sorted(set(re.findall(r"an? ([a-z]+)", m.group(1)))))
        if types:
            return "check", types
    return ("tapped?" if "unless" in text else "tapped"), ()


def enters_tapped(land, battlefield):
    """Kommt dieses Land mit den bereits liegenden Laendern getappt ins Spiel?"""
    mode = land.tap_mode
    if mode == "no":
        return False
    if mode == "fast":
        return len(battlefield) > 2
    if mode == "slow":
        return len(battlefield) < 2
    if mode == "check":
        return not any(set(l.land_types) & set(land.tap_arg) for l in battlefield)
    return True  # tapped / tapped?


def tap_tag(mode, arg):
    return {
        "no": "",
        "tapped": "   [getappt]",
        "tapped?": "   [getappt (Bedingung nicht modelliert)]",
        "fast": "   [getappt ab dem 4. Land]",
        "slow": "   [getappt, solange weniger als 2 andere Laender]",
        "check": "   [getappt, ausser du kontrollierst: " + "/".join(arg) + "]",
    }[mode]


EMPOWER_RE = re.compile(r"empower jace (\d+|x)\b", re.I)
EMPOWER_KIND_LABEL = {"spell": "Zauber", "etb": "beim Betreten", "other_once": "einmaliger Sonderfall",
                      "trigger": "Auslöser", "activated": "bezahlbar", "unknown": "nicht erkannt"}
EMPOWER_ONCE = ("spell", "etb", "other_once")
EMPOWER_RECURRING = ("trigger", "activated")


def classify_empower_line(line, spell_face):
    """Ordnet eine Textzeile mit 'empower Jace' ein. Gibt Liste (Art, Ausloeser, Kosten, Tap, unmodelliert) zurueck."""
    low = line.lower()
    m = re.match(r"^([^:]+):\s*(.*empower jace.*)$", low)
    if m and "{" in m.group(1) and not re.match(r"^(when|whenever|at )", m.group(1).strip()):
        cost_txt = line.split(":", 1)[0]
        tap = "{T}" in cost_txt
        mana = "".join(re.findall(r"\{[^}]+\}", cost_txt.replace("{T}", "")))
        rest = re.sub(r"\{[^}]+\}", "", cost_txt)
        rest = re.sub(r"[\s,]+", " ", rest).strip()
        return [("activated", "", cost_alternatives(mana) if mana else ((0, ()),), tap, bool(rest))]
    if re.match(r"^(when|whenever|at the beginning)\b", low):
        head = low.split(",", 1)[0]
        if low.startswith("when "):
            if "enters" in head:
                out = [("etb", "", (), False, False)]
                if " or attacks" in head:
                    out.append(("trigger", "attack", (), False, False))
                return out
            if "cast this spell" in head:
                return [("spell", "", (), False, False)]
            if any(w in head for w in ("dies", "leaves", "sacrificed", "graveyard", "is exiled")):
                return [("other_once", "", (), False, True)]
            return [("unknown", "", (), False, True)]
        if low.startswith("at the beginning"):
            trig = "turn"
        elif "attack" in head:
            trig = "attack"
        elif re.search(r"\bcasts?\b", head):
            if "noncreature" in head:
                trig = "cast:noncreature"
            elif "instant or sorcery" in head:
                trig = "cast:instant_sorcery"
            elif "creature spell" in head:
                trig = "cast:creature"
            elif "spell" in head:
                trig = "cast:any"
            else:
                trig = "?"
        elif "enters" in head:
            trig = "enter:land" if "land" in head else "enter:creature" if "creature" in head else "enter:any"
        else:
            trig = "?"
        return [("trigger", trig, (), False, trig == "?")]
    if spell_face:
        return [("spell", "", (), False, False)]
    return [("unknown", "", (), False, True)]


def parse_empower(card):
    """Liest alle 'empower Jace'-Effekte einer Karte (alle Seiten). Gibt (Effekte, Textzeilen) zurueck."""
    faces = card.get("card_faces") or [card]
    effects, texts = [], []
    for fi, face in enumerate(faces):
        text = face.get("oracle_text")
        if text is None and len(faces) == 1:
            text = card.get("oracle_text", "")
        tl = (face.get("type_line") or card.get("type_line") or "").split(" // ")[0]
        spell_face = "Instant" in tl or "Sorcery" in tl
        for raw in (text or "").split("\n"):
            line = re.sub(r"\([^)]*\)", "", raw).strip()  # Erinnerungstext entfernen
            found = EMPOWER_RE.findall(line)
            if not found:
                continue
            n = sum(int(v) for v in found if v.lower() != "x")
            xval = any(v.lower() == "x" for v in found)
            texts.append(raw.strip())
            for kind, trig, cost, tap, unmod in classify_empower_line(line, spell_face):
                effects.append((fi, kind, n, trig, cost, tap, unmod, xval))
    return tuple(effects), " / ".join(texts)[:240]


def pw_tags_for(card, front_type):
    """Weitere Jace-/Planeswalker-Bezuege (ohne Empower): jace, pw_help, pw_removal, is_pw."""
    faces = card.get("card_faces") or [card]
    text = " ".join((f.get("oracle_text") or "") for f in faces) if card.get("card_faces") else card.get("oracle_text", "")
    low = re.sub(r"\([^)]*\)", " ", text.lower())  # Erinnerungstext ignorieren
    for nm in {card.get("name", "")} | {f.get("name", "") for f in faces}:
        if nm:
            low = low.replace(nm.lower(), " ")
    low = EMPOWER_RE.sub(" ", low)
    low = re.sub(r"\bempower jace\b", " ", low)
    tags = []
    if "Planeswalker" in front_type:
        tags.append("is_pw")
    if re.search(r"\bjace\b", low):
        tags.append("jace")
    if "planeswalker" in low or "loyalty counter" in low or "proliferate" in low:
        harm = re.sub(r"loyalty counters?", " ", low)
        if (re.search(r"\b(destroys?|exiles?|fights?|deals? [^.\n]*damage|damage to)\b[^.\n]*planeswalker", harm)
                or re.search(r"planeswalker (an opponent controls|you don't control)", harm)):
            tags.append("pw_removal")
        else:
            tags.append("pw_help")
    return tuple(tags)


def empower_tags_text(effects):
    out = []
    for fi, kind, n, trig, cost, tap, unmod, xval in effects:
        label = EMPOWER_KIND_LABEL[kind]
        out.append(f"   [Empower Jace {'X' if xval and not n else n}{'+X' if xval and n else ''} · {label}]")
    return "".join(dict.fromkeys(out))


def card_info(card):
    """Wandelt eine Scryfall-Karte in (Card, Anzeigetext) um."""
    faces = card.get("card_faces") or [card]
    front = faces[0]
    type_line = (front.get("type_line") or card.get("type_line", "")).split(" // ")[0]
    if "Land" in type_line:
        produced = card.get("produced_mana") or front.get("produced_mana") or []
        colors = tuple(sorted(set(produced)))
        tap_mode, tap_arg = land_tap_info(card, front)
        subtypes = tuple(sorted(t.lower() for t in type_line.split("—", 1)[1].split())) \
            if "—" in type_line else ()
        ordered = sorted(colors, key="WUBRGC".find)
        shown = "Land " + ("".join("{%s}" % c for c in ordered) or "(-)") + tap_tag(tap_mode, tap_arg)
        eff, etext = parse_empower(card)
        shown += empower_tags_text(eff)
        return (Card(True, 0, (), colors, False, False, 0, 0, False, tap_mode, tap_arg, subtypes,
                     card["name"], is_basic="Basic" in type_line, empower=eff, empower_text=etext,
                     pw_tags=pw_tags_for(card, type_line)), shown)

    if card.get("layout") in ("split", "room", "adventure", "flip") and len(faces) > 1:
        used = [f for f in faces if f.get("mana_cost")]  # jede Haelfte ist spielbar
    else:
        used = [front]
    costs = [f.get("mana_cost") or card.get("mana_cost") or "" for f in used]
    alts = tuple(sorted({a for c in costs for a in cost_alternatives(c)}))
    mv = min((mana_value(c) for c in costs), default=0)

    is_creature = "Creature" in type_line
    is_aura = "Aura" in type_line
    pw = front.get("power") or card.get("power") or "0"
    tg = front.get("toughness") or card.get("toughness") or "0"
    power = int(pw) if re.fullmatch(r"-?\d+", pw) else 0
    tough = int(tg) if re.fullmatch(r"-?\d+", tg) else 0
    cycle_alts, cycle_target, cycle_mv, cycle_tag = (), "", 0, ""
    cm = LANDCYCLE_RE.search(front.get("oracle_text") or card.get("oracle_text") or "")
    if cm:
        kind = cm.group(1).lower()
        cycle_target = {"basic land": "basic", "land": "land"}.get(kind, kind)
        cycle_alts = cost_alternatives(cm.group(2))
        cycle_mv = mana_value(cm.group(2))
        label = {"basic": "Basic Landcycling", "land": "Landcycling"}.get(cycle_target, kind.capitalize() + "cycling")
        cycle_tag = f"   [{label} {cm.group(2)}]"
    keywords = set(card.get("keywords") or []) | set(front.get("keywords") or [])
    haste = is_creature and "Haste" in keywords
    shown = " // ".join(costs) or "-"
    if is_creature:
        shown += f"   [Kreatur {pw}/{tg}" + (", Haste]" if haste else "]")
    elif is_aura:
        shown += "   [Aura]"
    shown += cycle_tag
    eff, etext = parse_empower(card)
    shown += empower_tags_text(eff)
    return Card(False, mv, alts, (), is_creature, is_aura,
                power if is_creature else 0, tough if is_creature else 0, haste,
                name=card["name"], cycle_alts=cycle_alts, cycle_target=cycle_target,
                cycle_mv=cycle_mv, is_instant_sorcery=("Instant" in type_line or "Sorcery" in type_line),
                is_planeswalker="Planeswalker" in type_line, empower=eff, empower_text=etext,
                pw_tags=pw_tags_for(card, type_line)), shown


# ---------------------------------------------------------------- Simulation
def land_key(lands):
    return tuple(sorted(lands))


def aura_ok(chosen, has_creature, auras_need_creature):
    if not auras_need_creature or has_creature:
        return True
    return not (any(c.is_aura for c in chosen) and not any(c.is_creature for c in chosen))


def play_score(chosen):
    """Bewertung einer Zauber-Kombination (hoeher ist besser, in dieser Reihenfolge):
    1. ausgegebenes Mana  2. Zahl der Kreaturen  3. Power + Toughness  4. Zahl der Karten."""
    return (sum(c.mv for c in chosen),
            sum(c.is_creature for c in chosen),
            sum(c.power + c.toughness for c in chosen),
            len(chosen))


def best_cast(spells, key, has_creature, auras_need_creature):
    """Waehlt die Zauber, die in dieser Runde zusammen gespielt werden:
    maximal ausgegebenes Mana, dann mehr Kreaturen, dann mehr Power+Toughness."""
    spells = sorted(spells)
    n = len(spells)

    # Abkuerzung: passt die komplette Hand, wird alles gespielt
    if n and can_cast_all(tuple(sorted(c.alts for c in spells)), key) \
            and aura_ok(spells, has_creature, auras_need_creature):
        return play_score(spells), list(spells)

    best = [(-1, 0, 0, 0), []]

    def dfs(i, chosen):
        if i == n:
            if aura_ok(chosen, has_creature, auras_need_creature):
                s = play_score(chosen)
                if s > best[0]:
                    best[0], best[1] = s, chosen
            return
        cand = chosen + [spells[i]]
        if can_cast_all(tuple(sorted(c.alts for c in cand)), key):
            dfs(i + 1, cand)
        j = i + 1
        while j < n and spells[j] == spells[i]:  # gleiche Karten nicht doppelt durchprobieren
            j += 1
        dfs(j, chosen)

    dfs(0, [])
    return best[0], best[1]


def top_card_playable(card, spells, key, has_creature, auras_need_creature):
    """Ist die Top Card mit den aktuellen Laendern spielbar (Aura-Regel beachtet)?"""
    if not can_cast_all((card.alts,), key):
        return False
    if card.is_aura and auras_need_creature and not has_creature:
        return any(c.is_creature and can_cast_all(tuple(sorted((card.alts, c.alts))), key)
                   for c in spells)
    return True


def pay_subsets(pool, alts):
    """Alle Moeglichkeiten, die Kosten aus den Laendern zu bezahlen. Gibt die uebrig bleibenden
    Laender (Liste von Farbtupeln) zurueck, ohne doppelte Restmengen."""
    seen, out = set(), []
    for generic, req in alts:
        req_c = Counter(dict(req))
        need = generic + sum(req_c.values())
        if need > len(pool):
            continue
        for idx in itertools.combinations(range(len(pool)), need):
            if not can_pay([pool[k] for k in idx if pool[k]], generic, req_c):
                continue
            rest = [pool[k] for k in range(len(pool)) if k not in idx]
            sig = tuple(sorted(rest))
            if sig not in seen:
                seen.add(sig)
                out.append(rest)
    return out


def fits_target(land, target):
    if target == "basic":
        return land.is_basic
    if target == "land":
        return True
    return target in land.land_types


def without_many(items, remove):
    out = list(items)
    for r_ in remove:
        out.remove(r_)
    return out


def value_next(spells_next, bf_cols, bf_cards, lands_hand, has_creature, auras_need_creature):
    """Bestes Ergebnis der naechsten Runde: welches der Haendelaender man legt und was man damit spielen kann."""
    options = sorted(set(lands_hand))
    if not options:
        return best_cast(spells_next, land_key(bf_cols), has_creature, auras_need_creature)[0]
    best = None
    for land in options:
        cols = bf_cols + ([] if enters_tapped(land, bf_cards) else [land.land_colors])
        sc, _ = best_cast(spells_next, land_key(cols), has_creature, auras_need_creature)
        if best is None or sc > best:
            best = sc
    return best


def plan_cycle(cycler, pool, spells, battlefield, library, hand_lands, land_open, has_creature,
               auras_need_creature, base=None):
    """Plant das Landcycling: womit bezahlt wird und welches Land geholt wird.
    Bewertet wird mit Vorausschau: Mana-Nutzung in DIESER Runde, was man in der NAECHSTEN Runde
    spielen kann (inkl. Farben) und wie viele Landdrops gesichert sind.
    base=(Score, gewaehlte Zauber) ohne Cycling: dann wird nur gecycelt, wenn es sich lohnt,
    die geplanten Zauber dieser Runde nicht schlechter werden und die Karte nicht naechste Runde
    ohnehin spielbar waere. base=None (Regel 'Land fehlt'): Cycling ist Pflicht, nur das Land wird gewaehlt."""
    spells_wo = without_one(spells, cycler)
    cands = sorted({c for c in library if c.is_land and fits_target(c, cycler.cycle_target)})
    if not cands:
        return None
    rems = pay_subsets(pool, cycler.cycle_alts)
    if not rems:
        return None
    bf_cols = [c.land_colors for c in battlefield]
    have_colors = set().union(*bf_cols) if bf_cols else set()

    base_key = None
    if base is not None:
        s0, ch0 = base
        hc0 = has_creature or any(c.is_creature for c in ch0)
        nxt0 = value_next(without_many(spells, ch0), bf_cols, battlefield, hand_lands, hc0, auras_need_creature)
        base_key = (s0, nxt0, min(2, len(hand_lands)))

    best = None
    for rem in rems:
        for cand in cands:
            tapped = land_open and enters_tapped(cand, battlefield)
            avail = rem + ([cand.land_colors] if land_open and not tapped else [])
            sc, ch = best_cast(spells_wo, land_key(avail), has_creature, auras_need_creature)
            if base is not None and sc < base[0]:
                continue  # geplante Zauber duerfen nicht schlechter werden
            bf_after = battlefield + ([cand] if land_open else [])
            cols_after = bf_cols + ([cand.land_colors] if land_open else [])
            lands_next = [] if land_open else hand_lands + [cand]
            hc = has_creature or any(c.is_creature for c in ch)
            nxt = value_next(without_many(spells_wo, ch), cols_after, bf_after, lands_next, hc, auras_need_creature)
            cover = (1 if land_open else 0) + min(2, len(lands_next))
            demand = sum(1 for sp in spells_wo
                         if any(col in (set(cand.land_colors) - have_colors)
                                for _, req in sp.alts for col, _ in req))
            ncol = len(set().union(*(bf_cols + [cand.land_colors])))
            deficit = -sum(1 for lc in bf_cols if set(lc) & set(cand.land_colors))
            k = (sc, nxt, cover, demand, ncol, deficit)
            if best is None or k > best[0]:
                best = (k, rem, cand)
    if best is None:
        return None
    if base_key is not None and best[0][:3] <= base_key:
        return None  # Cycling bringt nichts -> Karte behalten
    return best[1], best[2]


def do_cycle(hand, library, cycler, cand):
    """Fuehrt das Landcycling aus: Karte weg, Land aus dem Deck auf die Hand, Deck mischen.
    Gibt die Chance auf ein Nicht-Land im naechsten Zug vor und nach dem Cycling zurueck."""
    n = len(library)
    lands = sum(c.is_land for c in library)
    p_before = (n - lands) / n if n else 0.0
    hand.remove(cycler)
    library.remove(cand)
    random.shuffle(library)
    hand.append(cand)
    n2 = n - 1
    p_after = (n2 - (lands - 1)) / n2 if n2 > 0 else p_before
    return p_before, p_after


def without_one(items, item):
    out = list(items)
    out.remove(item)
    return out


class JaceState:
    """Jace-Planeswalker-Token: nur eine Zahl (Loyalty). Bei 0 Loyalty gibt es keinen Token mehr,
    ein weiterer Empower erstellt einen neuen. Aktiviert wird (-3: Karte ziehen) hoechstens 1x pro Runde."""
    __slots__ = ("loyalty", "used", "acts", "gained", "first")

    def __init__(self):
        self.loyalty = 0
        self.used = False
        self.acts = 0
        self.gained = 0
        self.first = None

    def add(self, n):
        if n > 0:
            self.loyalty += n
            self.gained += n

    def try_activate(self, hand, library, turn):
        if self.used or self.loyalty < 3 or not library:
            return False
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


def deal_opening(cards, mulligan, min_hand):
    """Zieht die Starthand. Bei Mulligan: Deck neu mischen, eine Karte weniger.
    Faellt die Hand unter min_hand Karten, ist das Spiel verloren (hand = None).
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
            return None, None, mulls + 1, first
        size -= 1
        mulls += 1


def simulate(cards, sims, on_draw, max_turn, horizon, auras_need_creature, multicolor, top_mv,
             flood_lands=11, dmg_target=20, curve_turns=6,
             cycle_on=True, cycle_turns=3, cycle_cap=6, cycle_last=False, mulligan=True, min_hand=5,
             jace_on=True):
    cast_in_turn = {t: 0 for t in range(1, max_turn + 1)}
    opener_lands = n_creatures = power = toughness = 0
    land_screw = color_screw = any_screw = 0
    empty_hand, empty_spells, top_turns = [], [], []
    flooded = lands_drawn_total = 0
    dmg_turns = []
    best_lethal = None
    curve_avail = {t: 0 for t in range(1, curve_turns + 1)}  # verfuegbares Mana (Summe ueber alle Spiele)
    curve_spent = {t: 0 for t in range(1, curve_turns + 1)}  # ausgegebenes Mana
    curve_full = {t: 0 for t in range(1, curve_turns + 1)}   # Spiele, in denen alles Mana genutzt wurde
    curve_games = {t: 0 for t in range(1, curve_turns + 1)}  # Spiele mit mindestens 1 Mana
    cyc = {"games": 0, "events": 0, "reason": Counter(), "card": Counter(),
           "p_before": 0.0, "p_after": 0.0, "first": []}
    has_cyclers = cycle_on and any(c.cycle_alts for c in cards)
    mull = {"on": mulligan, "min_hand": min_hand, "deals": 0, "lost": 0, "sizes": Counter(),
            "first_any": 0, "first": Counter()}
    played, max_deals = 0, sims * 50 + 1000
    has_jace = jace_on and any(once_effects(c) or recurring_effects(c) for c in cards)
    samples = {"creatures": [], "power": [], "toughness": [], "util": [], "jace": []}  # je gespieltes Spiel
    jc = {"on": has_jace, "games_any": 0, "acts_win": 0, "gained_win": 0, "dist_win": Counter(),
          "acts_all": 0, "gained_all": 0, "dist_all": Counter(), "first": [], "empty_reached": 0}

    while played < sims:
        mull["deals"] += 1
        if mull["deals"] > max_deals:
            raise RuntimeError(f"Fast jede Starthand fuehrt zum Mulligan: nur {played} von {sims} Spielen "
                               f"wurden gespielt. Das Deck ist mit diesen Mulligan-Regeln praktisch unspielbar.")
        hand, library, mulls, first_reasons = deal_opening(cards, mulligan, min_hand)
        if first_reasons:
            mull["first_any"] += 1
            for r_ in set(first_reasons):
                mull["first"][r_] += 1
        if hand is None:
            mull["lost"] += 1
            continue  # Spiel durch Mulligan verloren: wird nicht gespielt
        played += 1
        mull["sizes"][len(hand)] += 1
        opening = hand[:]
        opener_lands += sum(c.is_land for c in hand)
        battlefield, board = [], []  # gelegte Laender / gespielte Kreaturen (Karte, Runde)
        hand_done = spells_done = top_done = dmg_done = False
        dmg_total = 0
        log = []
        game_events = []
        jst = JaceState()
        perms = []  # Permanents mit wiederkehrendem Empower: (Karte, Runde des Eintritts)
        acts_empty = gained_empty = None
        snap = (0, 0, 0)
        g_avail = g_spent = 0

        for turn in range(1, horizon + 1):
            drew = None
            if turn > 1 or on_draw:
                if not library:
                    break
                drew = library.pop(0)
                hand.append(drew)
            jst.used = False
            turn_acts0, turn_gain0 = jst.acts, jst.gained
            if has_jace:
                for pc, t_in in perms:
                    if t_in < turn:
                        for e in recurring_effects(pc):
                            if e[1] == "trigger" and e[3] == "turn":
                                jst.add(e[2])
                jst.try_activate(hand, library, turn)  # Loyalty aus frueheren Runden: Karte vor dem Landdrop ziehen
            pool = [c.land_colors for c in battlefield]      # zu Rundenbeginn sind alle Laender untapped
            avail_total = sum(1 for lc in pool if lc)         # Mana dieser Runde (inkl. neu gelegter Laender)
            cycle_spent = 0
            cycled_log = []
            spells = [c for c in hand if not c.is_land]
            has_creature = bool(board)

            # Landcycling Regel 2: kein Land auf der Hand -> Land per Landcycling sichern
            if has_cyclers and turn <= cycle_turns and not any(c.is_land for c in hand):
                for cycler in sorted({c for c in spells if c.cycle_alts}, key=lambda c: (c.cycle_mv, c)):
                    if not cycle_last and len(spells) <= 1:
                        continue  # letzte Karte auf der Hand: nicht wegwerfen
                    plan = plan_cycle(cycler, pool, spells, battlefield, library, [],
                                      True, has_creature, auras_need_creature)
                    if plan:
                        rem, cand = plan
                        pb, pa = do_cycle(hand, library, cycler, cand)
                        game_events.append((turn, "Land fehlt", cycler.name, pb, pa))
                        cycled_log.append((cycler, "Land fehlt"))
                        cycle_spent += cycler.cycle_mv
                        pool = rem
                        spells = [c for c in hand if not c.is_land]
                        break

            # Land legen (getappte Laender liefern in dieser Runde kein Mana)
            land_played, tapped_now = None, False
            land_options = sorted({c for c in hand if c.is_land})
            if land_options:
                bf_cols = [c.land_colors for c in battlefield]

                def score(land):
                    tapped = enters_tapped(land, battlefield)
                    avail = pool + ([] if tapped else [land.land_colors])
                    s_, _ = best_cast(spells, land_key(avail), has_creature, auras_need_creature)
                    # gleich viel Mana ausgegeben -> getapptes Land bevorzugt jetzt legen
                    return (s_, tapped, len(set().union(*(bf_cols + [land.land_colors]))))

                land_played = max(land_options, key=score)
                tapped_now = enters_tapped(land_played, battlefield)
                hand.remove(land_played)
                battlefield.append(land_played)
                if not tapped_now:
                    pool = pool + [land_played.land_colors]
                    if land_played.land_colors:
                        avail_total += 1
            key = land_key(pool)
            full_key = land_key([c.land_colors for c in battlefield])

            # Top Card gezogen und spielbar?
            if not top_done and top_mv is not None:
                for c in set(x for x in spells if x.mv == top_mv and x.alts):
                    if top_card_playable(c, spells, key, has_creature, auras_need_creature):
                        top_turns.append(turn)
                        top_done = True
                        break

            s_chosen, chosen = best_cast(spells, key, has_creature, auras_need_creature)

            # Landcycling Regel 1: Karte ist diesmal nicht spielbar -> mit uebrigem Mana cyceln
            if has_cyclers:
                for _round in range(3):
                    if len(battlefield) + sum(c.is_land for c in hand) >= cycle_cap:
                        break
                    left = Counter(spells)
                    left.subtract(Counter(chosen))
                    cands = sorted((c for c, k in left.items() if k > 0 and c.cycle_alts),
                                   key=lambda c: (c.cycle_mv, c))
                    done = False
                    for cycler in cands:
                        if not cycle_last:
                            rest = left.copy()
                            rest[cycler] -= 1
                            if not any(k > 0 for k in rest.values()):
                                continue  # waere die letzte Karte auf der Hand: nicht wegwerfen
                        plan = plan_cycle(cycler, pool, spells, battlefield, library,
                                          [c for c in hand if c.is_land], land_played is None,
                                          has_creature, auras_need_creature, base=(s_chosen, chosen))
                        if not plan:
                            continue
                        rem, cand = plan
                        pb, pa = do_cycle(hand, library, cycler, cand)
                        game_events.append((turn, "Karte nicht spielbar", cycler.name, pb, pa))
                        cycled_log.append((cycler, "Karte nicht spielbar"))
                        cycle_spent += cycler.cycle_mv
                        pool = rem
                        if land_played is None:  # Landdrop noch frei -> geholtes Land sofort legen
                            land_played = cand
                            tapped_now = enters_tapped(cand, battlefield)
                            hand.remove(cand)
                            battlefield.append(cand)
                            if not tapped_now:
                                pool = pool + [cand.land_colors]
                                if cand.land_colors:
                                    avail_total += 1
                        spells = [c for c in hand if not c.is_land]
                        key = land_key(pool)
                        full_key = land_key([c.land_colors for c in battlefield])
                        s_chosen, chosen = best_cast(spells, key, has_creature, auras_need_creature)
                        done = True
                        break
                    if not done:
                        break

            if has_jace and land_played is not None:
                for e in once_effects(land_played):
                    if e[1] == "etb":
                        jst.add(e[2])
                for pc, _t in perms:
                    for e in recurring_effects(pc):
                        if e[1] == "trigger" and e[3].startswith("enter:") and enter_filter_matches(e[3][6:], land_played):
                            jst.add(e[2])
                if recurring_effects(land_played):
                    perms.append((land_played, turn))

            for c in chosen:
                hand.remove(c)
                if c.is_creature:
                    board.append((c, turn))
            if has_jace:
                for c in sorted(chosen, key=lambda x: (not recurring_effects(x), x.mv)):
                    for pc, _t in perms:
                        for e in recurring_effects(pc):
                            if e[1] == "trigger" and e[3].startswith("cast:") and cast_filter_matches(e[3][5:], c):
                                jst.add(e[2])
                    for e in once_effects(c):
                        jst.add(e[2])
                    if not c.is_instant_sorcery:
                        for pc, _t in perms:
                            for e in recurring_effects(pc):
                                if e[1] == "trigger" and e[3].startswith("enter:") and enter_filter_matches(e[3][6:], c):
                                    jst.add(e[2])
                        if recurring_effects(c):
                            perms.append((c, turn))
            if turn <= max_turn and chosen:
                cast_in_turn[turn] += 1
            if turn <= curve_turns:
                spent = min(sum(c.mv for c in chosen) + cycle_spent, avail_total)
                curve_avail[turn] += avail_total
                curve_spent[turn] += spent
                g_avail += avail_total
                g_spent += spent
                if avail_total > 0:
                    curve_games[turn] += 1
                    curve_full[turn] += (spent == avail_total)

            if has_jace:
                # Angriffs-Ausloeser (Kreaturen vom Vorzug oder mit Haste)
                for pc, t_in in perms:
                    for e in recurring_effects(pc):
                        if e[1] == "trigger" and e[3] == "attack" and pc.is_creature and (t_in < turn or pc.haste):
                            jst.add(e[2])
                # bezahlbare Faehigkeiten mit dem uebrigen Mana
                paid = [c.alts for c in chosen]
                for pc, t_in in perms:
                    for e in recurring_effects(pc):
                        if e[1] != "activated" or (e[5] and pc.is_creature and not (t_in < turn or pc.haste)):
                            continue
                        for _k in range(1 if e[5] else 10):
                            if not can_cast_all(tuple(sorted(paid + [e[4]])), key):
                                break
                            paid.append(e[4])
                            jst.add(e[2])
                jst.try_activate(hand, library, turn)  # Loyalty aus dieser Runde

            # Angriff: Kreaturen vom Vorzug greifen an, neue nur mit Haste (keine Blocker, kein Removal)
            turn_dmg = sum(c.power for c, t in board if t < turn or c.haste) if board else 0
            dmg_total += turn_dmg
            log.append((turn, drew, land_played, tapped_now, chosen, turn_dmg, dmg_total, cycled_log,
                        (jst.gained - turn_gain0, jst.acts - turn_acts0, jst.loyalty)))
            if not dmg_done and dmg_total >= dmg_target:
                dmg_turns.append(turn)
                dmg_done = True
                cand_key = (turn, -dmg_total)  # frueher ist besser, bei Gleichstand mehr Schaden
                if best_lethal is None or cand_key < best_lethal["key"]:
                    best_lethal = {"key": cand_key, "opening": opening, "log": list(log), "mulls": mulls}

            # Hand aufgebraucht?
            if not hand_done and not hand:
                empty_hand.append(turn)
                hand_done = True
                acts_empty, gained_empty = jst.acts, jst.gained
            if not spells_done and all(c.is_land for c in hand):
                empty_spells.append(turn)
                spells_done = True

            if turn == max_turn:  # Momentaufnahme fuer Kreaturen und Screw
                short = len(battlefield) < max_turn
                no_colors = multicolor and not has_two_colors(full_key)
                land_screw += short
                color_screw += no_colors
                any_screw += (short or no_colors)
                n_creatures += len(board)
                power += sum(c.power for c, _ in board)
                toughness += sum(c.toughness for c, _ in board)
                snap = (len(board), sum(c.power for c, _ in board), sum(c.toughness for c, _ in board))

        if has_jace:
            a_win = acts_empty if acts_empty is not None else jst.acts
            g_win = gained_empty if gained_empty is not None else jst.gained
            jc["acts_win"] += a_win
            jc["gained_win"] += g_win
            jc["dist_win"][min(a_win, 6)] += 1
            jc["games_any"] += a_win > 0
            jc["acts_all"] += jst.acts
            jc["gained_all"] += jst.gained
            jc["dist_all"][min(jst.acts, 6)] += 1
            samples["jace"].append(a_win)
            jc["empty_reached"] += acts_empty is not None
            if jst.first is not None:
                jc["first"].append(jst.first)

        samples["creatures"].append(snap[0])
        samples["power"].append(snap[1])
        samples["toughness"].append(snap[2])
        if g_avail:
            samples["util"].append(g_spent / g_avail)

        # Flood: Laender, die bis zum Ende gezogen wurden (Starthand + Zuege) = Hand + Feld
        lands_drawn = sum(c.is_land for c in hand) + len(battlefield)
        lands_drawn_total += lands_drawn
        flooded += lands_drawn >= flood_lands

        if game_events:
            cyc["games"] += 1
            cyc["first"].append(min(e[0] for e in game_events))
            for _t, reason, name, pb, pa in game_events:
                cyc["events"] += 1
                cyc["reason"][reason] += 1
                cyc["card"][name] += 1
                cyc["p_before"] += pb
                cyc["p_after"] += pa

    return {
        "cast": cast_in_turn,
        "opener_lands": opener_lands / sims,
        "creatures": n_creatures / sims,
        "power": power / sims,
        "toughness": toughness / sims,
        "land_screw": land_screw / sims,
        "color_screw": color_screw / sims,
        "any_screw": any_screw / sims,
        "dmg": dmg_turns,
        "best_lethal": best_lethal,
        "mulligan": mull,
        "jace": jc,
        "samples": samples,
        "curve": {"avail": curve_avail, "spent": curve_spent, "full": curve_full, "games": curve_games},
        "landcycle": cyc,
        "flood": flooded / sims,
        "lands_drawn": lands_drawn_total / sims,
        "empty_hand": empty_hand,
        "empty_spells": empty_spells,
        "top": top_turns,
    }


def card_label(c):
    if c.is_creature:
        return f"{c.name} ({c.power}/{c.toughness}{', Haste' if c.haste else ''})"
    return c.name


def lethal_level(turn):
    """Runde <= 5 gruen, 6-7 gelb, ab 8 rot."""
    return "green" if turn <= 5 else "yellow" if turn <= 7 else "red"


# ---------------------------------------------------------------- HTML-Bericht
HTML_CSS = """
:root{
 --bg:#f3f4f8; --panel:#ffffff; --text:#1b2230; --muted:#677085; --line:#e2e5ee; --accent:#4b5bdc;
 --good:#146c3d; --goodbg:#d9f3e4; --warn:#7a5200; --warnbg:#ffedc2; --bad:#a82a2a; --badbg:#fde0e0;
 --play:#4b5bdc; --draw:#e07a1f; --track:#e6e9f2; --chip:#eef0f7;
}
@media (prefers-color-scheme: dark){
 :root{ --bg:#0e1117; --panel:#161b25; --text:#e7eaf1; --muted:#98a2b5; --line:#262d3b; --accent:#8e9bff;
  --good:#6fe0a0; --goodbg:#143a29; --warn:#f5c964; --warnbg:#3b3110; --bad:#ff9090; --badbg:#401a1a;
  --play:#8e9bff; --draw:#f5a45c; --track:#2a3347; --chip:#222a3a; }
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
header.top{padding:28px 20px 18px;max-width:1120px;margin:0 auto}
header.top h1{margin:0 0 4px;font-size:28px;letter-spacing:-.02em}
header.top .sub{color:var(--muted)}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.chip{background:var(--chip);border:1px solid var(--line);border-radius:999px;padding:2px 10px;font-size:12.5px;color:var(--muted)}
nav{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line)}
nav .in{max-width:1120px;margin:0 auto;padding:8px 20px;display:flex;gap:4px;overflow-x:auto;white-space:nowrap}
nav a{color:var(--muted);text-decoration:none;padding:4px 10px;border-radius:8px;font-size:13.5px}
nav a:hover{background:var(--chip);color:var(--text)}
main{max-width:1120px;margin:0 auto;padding:8px 20px 60px}
section{margin-top:22px;scroll-margin-top:56px}
section>h2{font-size:19px;margin:0 0 4px;letter-spacing:-.01em}
section>.hint{color:var(--muted);font-size:13.5px;margin:0 0 10px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px;box-shadow:0 1px 2px rgba(0,0,0,.03)}
.grid{display:grid;gap:14px}
.grid>*{min-width:0}
.g2{grid-template-columns:repeat(auto-fit,minmax(420px,1fr))}
.g4{grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}
.g3{grid-template-columns:repeat(3,1fr)}
@media(max-width:760px){.g3{grid-template-columns:1fr 1fr}}
.kpi{padding:14px 16px}
.kpi .l{color:var(--muted);font-size:12.5px;text-transform:uppercase;letter-spacing:.05em}
.kpi .v{font-size:26px;font-weight:650;letter-spacing:-.02em;margin-top:2px}
.kpi .s{color:var(--muted);font-size:13px}
table{border-collapse:collapse;width:100%}
th,td{padding:7px 10px;text-align:right;border-bottom:1px solid var(--line);vertical-align:middle}
th{font-weight:600;color:var(--muted);font-size:12.5px;text-transform:uppercase;letter-spacing:.04em}
th:first-child,td:first-child{text-align:left}
tr:last-child td{border-bottom:0}
td.l,th.l{text-align:left}
.tw{overflow-x:auto}
td.good,td.warn,td.bad{font-weight:650;border-radius:0}
td.good{background:var(--goodbg);color:var(--good)}
td.warn{background:var(--warnbg);color:var(--warn)}
td.bad{background:var(--badbg);color:var(--bad)}
.pill{display:inline-block;padding:1px 9px;border-radius:999px;font-weight:650;font-size:13px}
.pill.good{background:var(--goodbg);color:var(--good)}
.pill.warn{background:var(--warnbg);color:var(--warn)}
.pill.bad{background:var(--badbg);color:var(--bad)}
.m{display:inline-flex;align-items:center;justify-content:center;min-width:22px;height:22px;padding:0 5px;margin:0 1px;
   border-radius:999px;font-size:12px;font-weight:700;border:1px solid rgba(0,0,0,.25);vertical-align:middle;line-height:1}
.m-h{text-shadow:0 0 3px #fff,0 0 3px #fff;color:#111;min-width:38px;padding:0 8px}
.tag.add{background:var(--goodbg);color:var(--good);border-color:transparent}
.tag.rem{background:var(--badbg);color:var(--bad);border-color:transparent}
.tag{display:inline-block;background:var(--chip);border:1px solid var(--line);border-radius:6px;padding:0 7px;margin:1px 3px 1px 0;font-size:12px;color:var(--muted)}
.bar{background:var(--track);border-radius:999px;height:9px;min-width:70px;overflow:hidden}
.bar i{display:block;height:100%;background:var(--accent);border-radius:999px}
.bar.draw i{background:var(--draw)} .bar.play i{background:var(--play)}
.bc{display:flex;align-items:center;gap:8px;justify-content:flex-end}
.bc .bar{flex:1;max-width:110px;min-width:50px}
.bc b{min-width:40px;text-align:right}
.mode{font-weight:650;white-space:nowrap}
th{white-space:nowrap}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}
.dot.play{background:var(--play)} .dot.draw{background:var(--draw)}
svg.chart{width:100%;height:auto;max-height:300px}
svg .grid{stroke:var(--line);stroke-width:1}
svg .axis{fill:var(--muted);font-size:11px}
svg .lbl{fill:var(--text);font-size:10.5px;font-weight:600}
svg .ln{fill:none;stroke-width:2.6;stroke-linejoin:round;stroke-linecap:round}
svg .ln.play{stroke:var(--play)} svg .ln.draw{stroke:var(--draw)}
svg .pt.play,svg .rb.play{fill:var(--play)} svg .pt.draw,svg .rb.draw{fill:var(--draw)}
svg .pt,svg .rb{stroke:none}
.legend{display:flex;gap:16px;font-size:13px;color:var(--muted);margin:2px 0 6px}
.lethal .head{display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap}
.lethal .head .big{font-size:20px;font-weight:700}
.hand{display:flex;flex-wrap:wrap;gap:5px;margin:4px 0 10px}
.card{border:1px solid var(--line);background:var(--chip);border-radius:7px;padding:2px 8px;font-size:12.5px}
.card.land{opacity:.75}
.tl td,.tl th{font-size:13.5px}
.tl td.dmg{white-space:nowrap}
.muted{color:var(--muted)}
.note{color:var(--muted);font-size:12.5px;margin-top:8px}
.warnbox{background:var(--warnbg);color:var(--warn);border-radius:10px;padding:8px 12px;font-size:13.5px;margin-bottom:10px}
ul.ass,ol.ass{margin:6px 0 0;padding-left:22px;color:var(--muted);font-size:13.5px}
ol.ass li,ul.ass li{margin-bottom:4px}
ol.ass b,ul.ass b{color:var(--text)}
tr.win td{background:var(--goodbg);color:var(--good);font-weight:650}
footer{max-width:1120px;margin:0 auto;padding:0 20px 40px;color:var(--muted);font-size:12.5px}
@media print{nav{display:none}body{background:#fff}.panel{box-shadow:none}}
"""

MANA_BG = {"W": "#f6efc4", "U": "#2a74c4", "B": "#3a3340", "R": "#d0453a", "G": "#2e9560", "C": "#c3c9d1"}
MANA_FG = {"W": "#2a2a2a", "U": "#ffffff", "B": "#ffffff", "R": "#ffffff", "G": "#ffffff", "C": "#222222"}
MANA_NEUTRAL = "#d9dde3"
LABEL_CLASS = {"On the Play": "play", "On the Draw": "draw"}


def esc(x):
    return html_lib.escape(str(x), quote=True)


def html_mana(sym):
    if "/" in sym:
        cols = [MANA_BG.get(p, MANA_NEUTRAL) for p in sym.split("/")[:2]]
        if len(cols) == 1:
            cols = cols * 2
        return (f'<span class="m m-h" style="background:linear-gradient(135deg,{cols[0]} 50%,{cols[1]} 50%)">'
                f'{esc(sym)}</span>')
    return (f'<span class="m" style="background:{MANA_BG.get(sym, MANA_NEUTRAL)};'
            f'color:{MANA_FG.get(sym, "#222222")}">{esc(sym)}</span>')


def html_cost(text):
    out, last = [], 0
    for mm in re.finditer(r"\{([^}]+)\}", text):
        out.append(esc(text[last:mm.start()]))
        out.append(html_mana(mm.group(1)))
        last = mm.end()
    out.append(esc(text[last:]))
    return "".join(out)


def h_pct(x, digits=0):
    return f"{x * 100:.{digits}f}%"


def h_bar(frac, cls=""):
    frac = max(0.0, min(1.0, frac))
    return f'<div class="bar {cls}"><i style="width:{frac * 100:.1f}%"></i></div>'


def h_bar_cell(frac, text=None, cls=""):
    text = h_pct(frac) if text is None else text
    return f'<td><div class="bc"><b>{esc(text)}</b>{h_bar(frac, cls)}</div></td>'


def h_level_td(level, text):
    cls = {"green": "good", "yellow": "warn", "red": "bad"}.get(level, "")
    return f'<td class="{cls}">{esc(text)}</td>'


def h_level_pill(level, text):
    cls = {"green": "good", "yellow": "warn", "red": "bad"}.get(level, "")
    return f'<span class="pill {cls}">{esc(text)}</span>'


def h_mode(label):
    return f'<td class="l mode"><span class="dot {LABEL_CLASS.get(label, "")}"></span>{esc(label)}</td>'


def h_table(headers, rows, extra="", left=(0,)):
    head = "".join(f'<th class="{"l" if i in left else ""}">{h}</th>' for i, h in enumerate(headers))
    body = "".join("<tr>" + "".join(r) + "</tr>" for r in rows)
    return f'<div class="tw"><table {extra}><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


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


def timing_stats(turns, sims):
    if not turns:
        return None
    return statistics.mean(turns), statistics.median(turns), len(turns) / sims


def svg_lines(xs, series, ymax=1.0, w=640, h=250):
    ml, mr, mt, mb = 46, 16, 14, 30
    pw, ph = w - ml - mr, h - mt - mb

    def X(i):
        return ml + (pw * i / (len(xs) - 1) if len(xs) > 1 else pw / 2)

    def Y(v):
        return mt + ph * (1 - min(v, ymax) / ymax)

    out = [f'<svg viewBox="0 0 {w} {h}" class="chart" role="img">']
    for g in (0, .25, .5, .75, 1):
        y = Y(g * ymax)
        out.append(f'<line x1="{ml}" x2="{w - mr}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
        out.append(f'<text x="{ml - 7}" y="{y + 4:.1f}" class="axis" text-anchor="end">{g:.0%}</text>')
    for i, x in enumerate(xs):
        out.append(f'<text x="{X(i):.1f}" y="{h - 9}" class="axis" text-anchor="middle">{esc(x)}</text>')
    for name, vals in series.items():
        cls = LABEL_CLASS.get(name, "play")
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
        out.append(f'<polyline points="{pts}" class="ln {cls}"/>')
        for i, v in enumerate(vals):
            out.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="3.3" class="pt {cls}">'
                       f'<title>{esc(name)}, Runde {esc(xs[i])}: {v:.0%}</title></circle>')
    out.append("</svg>")
    return "".join(out)


def svg_bars(labels, series, vmax, fmt, w=640, h=250):
    ml, mr, mt, mb = 40, 12, 22, 30
    pw, ph = w - ml - mr, h - mt - mb
    n, k = len(labels), len(series)
    gw = pw / max(n, 1)
    bw = min(34, gw * 0.8 / max(k, 1))
    out = [f'<svg viewBox="0 0 {w} {h}" class="chart" role="img">']
    for g in (0, .5, 1):
        y = mt + ph * (1 - g)
        out.append(f'<line x1="{ml}" x2="{w - mr}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
        out.append(f'<text x="{ml - 6}" y="{y + 4:.1f}" class="axis" text-anchor="end">{fmt(g * vmax)}</text>')
    for i, lab in enumerate(labels):
        cx = ml + gw * (i + 0.5)
        out.append(f'<text x="{cx:.1f}" y="{h - 9}" class="axis" text-anchor="middle">{esc(lab)}</text>')
        for j, (name, vals) in enumerate(series.items()):
            v = vals[i]
            bh = ph * min(v, vmax) / vmax if vmax else 0
            x = cx - bw * k / 2 + bw * j
            cls = LABEL_CLASS.get(name, "play")
            out.append(f'<rect x="{x:.1f}" y="{mt + ph - bh:.1f}" width="{bw - 3:.1f}" height="{bh:.1f}" rx="3" '
                       f'class="rb {cls}"><title>{esc(name)}, {esc(lab)}: {fmt(v)}</title></rect>')
            if v > 0:
                out.append(f'<text x="{x + (bw - 3) / 2:.1f}" y="{mt + ph - bh - 4:.1f}" class="lbl" '
                           f'text-anchor="middle">{fmt(v)}</text>')
    out.append("</svg>")
    return "".join(out)


def h_legend(labels):
    return '<div class="legend">' + "".join(
        f'<span><span class="dot {LABEL_CLASS.get(l, "")}"></span>{esc(l)}</span>' for l in labels) + "</div>"


def h_section(sid, title, hint, body):
    hint_html = f'<p class="hint">{hint}</p>' if hint else ""
    return f'<section id="{sid}"><h2>{esc(title)}</h2>{hint_html}{body}</section>'


def _example_card(mv, creature):
    return Card(False, mv, cost_alternatives("{%d}" % mv), (), creature, False,
                mv if creature else 0, mv if creature else 0, name=f"{mv}-Mana-Karte")


def _combo_label(chosen):
    return " + ".join(str(c.mv) for c in sorted(chosen, key=lambda c: c.mv)) or "nichts"


def logic_example():
    """Beispiel aus der Praxis, berechnet mit der echten Auswahlfunktion:
    Hand = 1x 2-Mana, 1x 3-Mana, 4x 1-Mana (+ 1 Land), Runde 2 mit 2 Laendern."""
    tables = []
    for creature in (True, False):
        hand = [_example_card(2, creature), _example_card(3, creature)] + [_example_card(1, creature)] * 4
        key = land_key([("W",)] * 2)
        counts = Counter(hand)
        kinds = sorted(counts)
        combos = []
        for amounts in itertools.product(*(range(counts[k] + 1) for k in kinds)):
            chosen = [k for k, n in zip(kinds, amounts) for _ in range(n)]
            if chosen and can_cast_all(tuple(sorted(c.alts for c in chosen)), key):
                combos.append((play_score(chosen), chosen))
        combos.sort(key=lambda x: x[0], reverse=True)
        _, picked = best_cast(hand, key, False, True)
        tables.append((creature, combos, _combo_label(picked)))
    # Beispielverlauf Runde 2-4 (Kreaturen), jede Runde ein weiteres Land
    hand = [_example_card(2, True), _example_card(3, True)] + [_example_card(1, True)] * 4
    flow = []
    for turn in (2, 3, 4):
        key = land_key([("W",)] * turn)
        _, ch = best_cast(hand, key, False, True)
        for c in ch:
            hand.remove(c)
        flow.append((turn, _combo_label(ch), sum(c.mv for c in ch), _combo_label(hand)))
    return tables, flow


def render_logic_section(has_jace=False):
    tables, flow = logic_example()
    steps = [
        "<b>Starthand:</b> 7 Karten, bei Bedarf Mulligan mit einer Karte weniger (Regeln im Abschnitt Mulligan).",
        "<b>Ziehen:</b> Auf dem Play entfällt die Karte in Runde 1, auf dem Draw wird jede Runde gezogen.",
        "<b>Landcycling (Pflicht):</b> Fehlt in den ersten Runden ein Land auf der Hand, wird ein Landcycler "
        "gecycelt, damit der Landdrop klappt.",
        "<b>Land legen:</b> Es wird das Land gelegt, mit dem in dieser Runde am meisten Mana in Zauber fließen kann. "
        "Bei Gleichstand kommt ein getapptes Land zuerst, danach zählt, welches Land mehr verschiedene Farben bringt.",
        "<b>Zauber wählen:</b> Aus allen Kombinationen, die zusammen bezahlt werden können (Farben beachtet), "
        "wird die beste nach den vier Auswahlregeln gespielt.",
        "<b>Landcycling (nur wenn es sich lohnt):</b> Eine nicht spielbare Karte wird mit übrigem Mana gecycelt, "
        "wenn das diese oder nächste Runde etwas verbessert.",
        "<b>Angriff:</b> Kreaturen vom Vorzug greifen an, neue nur mit Haste.",
    ]
    if has_jace:
        steps.insert(2, "<b>Jace (Empower):</b> Hat der Jace-Token mindestens 3 Loyalty, wird er zu Rundenbeginn aktiviert (Karte ziehen), "
                        "sonst nach dem Zaubern, höchstens einmal pro Runde. Details im Abschnitt Jace & Planeswalker.")
    rules = [
        "<b>Möglichst viel Mana ausgeben.</b> Die Kombination mit der größten Summe der Manawerte gewinnt.",
        "<b>Bei Gleichstand mehr Kreaturen,</b> weil sie den Schaden machen.",
        "<b>Dann höhere Summe aus Power und Toughness.</b>",
        "<b>Dann mehr Karten</b> (also lieber zwei billige als eine teure Karte).",
    ]
    ex_tables = []
    for creature, combos, picked in tables:
        rows = []
        for sc, chosen in combos:
            win = _combo_label(chosen) == picked
            rows.append([f'<td class="l">{esc(_combo_label(chosen))}</td>', f"<td>{sc[0]}</td>", f"<td>{sc[1]}</td>",
                         f"<td>{sc[2]}</td>", f"<td>{sc[3]}</td>", f'<td class="l">{"✔ gewählt" if win else ""}</td>'])
        html_rows = "".join(
            f'<tr class="{"win" if r[-1].endswith("gewählt</td>") else ""}">' + "".join(r) + "</tr>" for r in rows)
        head = "".join(f'<th class="{"l" if i in (0, 5) else ""}">{h}</th>' for i, h in enumerate(
            ["Kombination (Manawerte)", "Mana", "Kreaturen", "Power + Toughness", "Karten", ""]))
        title = "Alles Kreaturen (Power und Toughness = Manawert)" if creature else "Keine Kreaturen (z. B. Zauber)"
        ex_tables.append(f'<div class="panel"><b>{title}</b><div class="tw"><table><thead><tr>{head}</tr></thead>'
                         f'<tbody>{html_rows}</tbody></table></div></div>')
    flow_rows = [[f'<td class="l">Runde {t}</td>', f"<td>{t}</td>", f'<td class="l">{esc(c)}</td>',
                  f"<td>{m_}</td>", f'<td class="l">{esc(rest)}</td>'] for t, c, m_, rest in flow]
    total_spent = sum(f[2] for f in flow)
    total_avail = sum(f[0] for f in flow)
    body = (
        '<div class="grid g2"><div class="panel"><b>Ablauf einer Runde</b><ol class="ass">'
        + "".join(f"<li>{x}</li>" for x in steps) + '</ol></div>'
        '<div class="panel"><b>So wird aus mehreren spielbaren Karten ausgewählt</b><ol class="ass">'
        + "".join(f"<li>{x}</li>" for x in rules)
        + '</ol><div class="note">Die Regeln gelten der Reihe nach: Erst wenn zwei Kombinationen bei Regel 1 gleichauf '
          'sind, entscheidet Regel 2, und so weiter. Die Wahl gilt nur für die aktuelle Runde, es gibt keine '
          'Vorausschau auf spätere Runden (außer beim Landcycling). Was spielbar ist, wird auch gespielt, '
          'Karten werden nicht absichtlich zurückgehalten.</div></div></div>'
        '<div class="panel" style="margin-top:14px"><b>Beispiel: Runde 2 mit zwei Ländern</b>'
        '<div class="note" style="margin:2px 0 10px">Hand: eine 2-Mana-Karte, eine 3-Mana-Karte, vier 1-Mana-Karten und '
        'ein Land. Ein Land liegt schon, das zweite wird jetzt gelegt, es stehen also 2 Mana zur Verfügung. '
        'Die 3-Mana-Karte ist nicht bezahlbar. Die Tabellen listen alle bezahlbaren Kombinationen, '
        'berechnet mit der echten Auswahlfunktion.</div>'
        f'<div class="grid">{"".join(ex_tables)}</div>'
        '<div style="margin-top:14px"><b>Weiterer Verlauf</b> <span class="muted">(Annahme: jede Runde kommt ein weiteres Land)</span>'
        + h_table(["", "Mana", "Gespielt (Manawerte)", "Ausgegeben", "Rest auf der Hand"], flow_rows, left=(0, 2, 4))
        + f'<div class="note">Hier werden {total_spent} von {total_avail} verfügbaren Mana genutzt, also '
          f'{total_spent / total_avail:.0%} Auslastung. Bei den Prozentwerten der Curve-Auslastung zählt das '
          f'ausgegebene Mana (Summe der Manawerte, bei Landcycling die Cycling-Kosten) geteilt durch das '
          f'Mana der Länder, die in dieser Runde Mana liefern.</div></div></div>')
    return body


# ---------------------------------------------------------------- Deck-Vergleich
Z95 = 1.96


def wilson_halfwidth(k, n):
    if n <= 0:
        return 0.0
    p = k / n
    den = 1 + Z95 ** 2 / n
    return Z95 * ((p * (1 - p) / n + Z95 ** 2 / (4 * n * n)) ** 0.5) / den


def mean_var_of_mean(values):
    """Mittelwert und Varianz des Mittelwerts (Standardfehler im Quadrat)."""
    n = len(values)
    if n == 0:
        return None
    m_ = sum(values) / n
    if n == 1:
        return m_, 0.0
    var = sum((v - m_) ** 2 for v in values) / (n - 1)
    return m_, var / n


def compare_metrics(decks, args, label):
    """Liste der Vergleichs-Kennzahlen fuer einen Modus. Jede Zeile: (Name, Art, hoeher_ist_besser, [Zelle je Deck]).
    Zelle: (Wert, Halbbreite 95%, Varianz des Werts) oder None."""
    sims, T, C = args.sims, args.turns, args.curve_runden

    def prop(k, n):
        if n <= 0:
            return None
        p = k / n
        return p, wilson_halfwidth(k, n), p * (1 - p) / n

    def mean(values):
        r = mean_var_of_mean(values)
        return None if r is None else (r[0], Z95 * r[1] ** 0.5, r[1])

    rows = []
    mull_on = decks[0]["results"][label]["mulligan"]["on"]
    if mull_on:
        rows.append(("Mulligan auf der ersten Hand", "prop", False, [
            prop(d["results"][label]["mulligan"]["first_any"], d["results"][label]["mulligan"]["deals"]) for d in decks]))
        rows.append(("Spiel verloren (Mulligan)", "prop", False, [
            prop(d["results"][label]["mulligan"]["lost"], d["results"][label]["mulligan"]["deals"]) for d in decks]))
    for t in range(1, T + 1):
        rows.append((f"Zauber gespielt in Runde {t}", "prop", True, [
            prop(d["results"][label]["cast"][t], sims) for d in decks]))
    rows.append((f"Mana Screw nach Runde {T}", "prop", False, [
        prop(round(d["results"][label]["any_screw"] * sims), sims) for d in decks]))
    rows.append((f"Flood ({args.flood}+ Länder bis Runde {max(args.max_runden, T, C)})",
                 "prop", False, [prop(round(d["results"][label]["flood"] * sims), sims) for d in decks]))
    rows.append((f"Kreaturen auf dem Feld nach Runde {T}", "mean", True, [
        mean(d["results"][label]["samples"]["creatures"]) for d in decks]))
    rows.append((f"Gesamt-Power nach Runde {T}", "mean", True, [
        mean(d["results"][label]["samples"]["power"]) for d in decks]))
    rows.append((f"Curve-Auslastung Runde 1–{C} (Mana genutzt)", "prop", True, [
        None if not d["results"][label]["samples"]["util"] else
        (lambda r: (r[0], Z95 * r[1] ** 0.5, r[1]))(mean_var_of_mean(d["results"][label]["samples"]["util"])) for d in decks]))
    for x in (5, 7):
        rows.append((f"{args.schaden} Schaden bis Runde {x}", "prop", True, [
            prop(sum(1 for v in d["results"][label]["dmg"] if v <= x), sims) for d in decks]))
    rows.append((f"Ø Runde für {args.schaden} Schaden", "mean", False, [
        mean(d["results"][label]["dmg"]) if d["results"][label]["dmg"] else None for d in decks]))
    if any(d["results"][label]["jace"]["on"] for d in decks):
        rows.append(("Jace-Aktivierungen bis Hand leer (Ø)", "mean", True, [
            mean(d["results"][label]["samples"]["jace"]) if d["results"][label]["jace"]["on"] else None for d in decks]))
    return rows


def deck_diff_chips(main_deck, alt_deck):
    names = sorted(set(main_deck["deck"]) | set(alt_deck["deck"]))
    out = []
    for n in names:
        d = alt_deck["deck"].get(n, 0) - main_deck["deck"].get(n, 0)
        if d > 0:
            out.append(f'<span class="tag add">+{d} {esc(n)}</span>')
        elif d < 0:
            out.append(f'<span class="tag rem">−{-d} {esc(n)}</span>')
    return "".join(out) or '<span class="muted">identisch</span>'


def render_compare_section(ctx):
    a = ctx["args"]
    main_deck = ctx
    decks = [main_deck] + ctx["alts"]
    labels = list(main_deck["results"].keys())
    sims = a.sims

    # ---- Uebersicht der Decks
    ov = []
    for i, d in enumerate(decks):
        cols = "".join(html_mana(c) for c in sorted(d["deck_colors"], key="WUBRGC".find)) or "–"
        diff = '<span class="muted">Hauptdeck</span>' if i == 0 else deck_diff_chips(main_deck, d)
        ov.append([f'<td class="l"><b>{esc(d["name"])}</b></td>', f"<td>{len(d['cards'])}</td>", f"<td>{d['n_lands']}</td>",
                   f"<td>{d['avg_mv']:.2f}</td>", f'<td class="l">{cols}</td>', f'<td class="l">{diff}</td>'])
    overview = h_table(["Deck", "Karten", "Länder", "Ø Manakosten", "Farben", "Unterschiede zum Hauptdeck"], ov,
                       left=(0, 4, 5))
    warn = ""
    for d in decks:
        if d["missing"]:
            warn += (f'<div class="warnbox">{esc(d["name"])}: nicht bei Scryfall gefunden (nicht simuliert): '
                     f'{esc(", ".join(d["missing"]))}</div>')
    if len({len(d["cards"]) for d in decks}) > 1:
        warn += '<div class="warnbox">Die Decks haben unterschiedlich viele Karten, das beeinflusst Mana- und Kartenwerte.</div>'

    # ---- Detailtabellen je Modus + Zaehler fuer das Fazit
    tally = {i: {"good": 0, "bad": 0, "same": 0} for i in range(1, len(decks))}
    panels = []
    for label in labels:
        rows_html = []
        for name, kind, higher, cells in compare_metrics(decks, a, label):
            base = cells[0]

            def fmt(c):
                if c is None:
                    return "–"
                v, hw, _ = c
                if kind == "prop":
                    return f'{v * 100:.1f}% <span class="muted">±{hw * 100:.1f}</span>'
                return f'{v:.2f} <span class="muted">±{hw:.2f}</span>'

            tds = [f'<td class="l">{esc(name)}</td>', f"<td>{fmt(base)}</td>"]
            for i in range(1, len(decks)):
                c = cells[i]
                if c is None or base is None:
                    tds += [f"<td>{fmt(c)}</td>", '<td class="muted">–</td>']
                    continue
                diff = c[0] - base[0]
                se = (c[2] + base[2]) ** 0.5
                sig = abs(diff) > Z95 * se if se > 0 else diff != 0
                good = (diff > 0) == higher
                cls = ("good" if good else "bad") if sig else ""
                tally[i]["good" if sig and good else "bad" if sig else "same"] += 1
                if kind == "prop":
                    txt = f"{diff * 100:+.1f} PP"
                    err = f"±{Z95 * se * 100:.1f}"
                else:
                    txt = f"{diff:+.2f}"
                    err = f"±{Z95 * se:.2f}"
                tds.append(f"<td>{fmt(c)}</td>")
                tds.append(f'<td class="{cls}">{txt} <span style="font-weight:400;opacity:.75">{err}</span></td>'
                           if sig else f'<td class="muted">{txt} <span style="opacity:.75">{err}</span> ≈</td>')
            rows_html.append(tds)
        heads = ["Kennzahl", esc(decks[0]["name"]) + " (Haupt)"]
        for d in decks[1:]:
            heads += [esc(d["name"]), "Δ"]
        panels.append(f'<div class="panel"><b>{esc(label)}</b>{h_table(heads, rows_html)}</div>')

    fazit_rows = []
    for i in range(1, len(decks)):
        t = tally[i]
        fazit_rows.append([f'<td class="l"><b>{esc(decks[i]["name"])}</b></td>',
                           f'<td class="good">{t["good"]}</td>', f'<td class="bad">{t["bad"]}</td>',
                           f'<td>{t["same"]}</td>'])
    fazit = h_table(["Alternative gegen Hauptdeck", "Klar besser", "Klar schlechter", "Kein klarer Unterschied"], fazit_rows)

    note = (f"Jedes Deck wird unabhängig mit {sims} gespielten Spielen pro Modus simuliert. Hinter den Werten steht das 95-%-"
            "Konfidenzintervall (±). Ein Unterschied (Δ) ist farbig, wenn er größer ist als der zufällige Fehler "
            "(|Δ| > 1,96 × Standardfehler), grün bei besser und rot bei schlechter. Mit ≈ markierte Unterschiede sind nicht "
            "von Zufall zu trennen. PP = Prozentpunkte. Bei so vielen Kennzahlen sind einzelne zufällige Ausreißer zu erwarten, "
            "achte deshalb auf das Gesamtbild. Für eine höhere Genauigkeit hilft eine größere --sims-Zahl.")
    return (f'<div class="panel">{overview}{warn}</div>'
            f'<div class="panel" style="margin-top:14px"><b>Fazit über alle Kennzahlen (Play und Draw zusammen)</b>{fazit}'
            f'<div class="note">{esc(note)}</div></div>'
            f'<div class="grid" style="margin-top:14px">{"".join(panels)}</div>')


JACE_TAG_LABEL = {"jace": "erwähnt Jace", "pw_help": "Planeswalker (hilft)", "pw_removal": "gegen Planeswalker",
                  "is_pw": "ist Planeswalker"}


def render_jace_section(ctx):
    ja, res, a = ctx["jace"], ctx["results"], ctx["args"]
    labels = list(res.keys())
    sims, H = a.sims, ctx["horizon"]
    cat, tg = ja["cat"], ja["tags"]
    helps = sum(r["qty"] for r in ja["cards"] if {"jace", "pw_help"} & set(r["tags"]))
    kpis = [
        ("Karten mit Empower Jace", str(ja["empower_copies"]), f"{ja['empower_cards']} verschiedene"),
        ("Einmalig", str(ja["once_copies"]), f"Σ Empower {ja['once_sum']}"),
        ("Wiederkehrend", str(ja["rec_copies"]), f"Σ {ja['rec_sum']} je Auslösung"),
        ("Erwähnen Jace / Planeswalker", str(helps), "ohne Empower, helfend"),
        ("Gegen Planeswalker", str(tg["pw_removal"]["copies"]), "z. B. zerstören, Schaden"),
        ("Planeswalker-Karten", str(tg["is_pw"]["copies"]), "selbst Planeswalker"),
    ]
    kpi_html = "".join(f'<div class="panel kpi"><div class="l">{esc(l)}</div><div class="v">{v}</div>'
                       f'<div class="s">{esc(s_)}</div></div>' for l, v, s_ in kpis)

    kind_rows = []
    for k, label in (("spell", "Einmalig: Zauber (Instant, Sorcery)"), ("etb", "Einmalig: beim Betreten"),
                     ("other_once", "Einmalig: Sonderfall (z. B. beim Sterben)"),
                     ("trigger", "Wiederkehrend: Auslöser („whenever“, „at the beginning“)"),
                     ("activated", "Wiederkehrend: bezahlbare Fähigkeit"), ("unknown", "Nicht erkannt")):
        c = cat[k]
        if c["copies"]:
            kind_rows.append([f'<td class="l">{esc(label)}</td>', f'<td>{c["copies"]}</td>', f'<td>{c["cards"]}</td>',
                              f'<td>{c["sum"]}</td>'])
    kind_rows.append([f'<td class="l"><b>Einmalig gesamt</b></td>', f'<td><b>{ja["once_copies"]}</b></td>', "<td></td>",
                      f'<td><b>{ja["once_sum"]}</b></td>'])
    kind_rows.append([f'<td class="l"><b>Wiederkehrend gesamt</b></td>', f'<td><b>{ja["rec_copies"]}</b></td>', "<td></td>",
                      f'<td><b>{ja["rec_sum"]}</b></td>'])
    kind_table = h_table(["Kategorie", "Karten (Kopien)", "Verschiedene Karten", "Σ Empower"], kind_rows)

    sim_html = ""
    if a.ohne_jace:
        sim_html = '<div class="note">Die Simulation von Jace ist mit --ohne-jace abgeschaltet, es wird nur gezählt.</div>'
    elif not any(res[l]["jace"]["on"] for l in labels):
        sim_html = ('<div class="note">Keine modellierbaren Empower-Effekte im Deck, deshalb gibt es keine Simulationswerte '
                    '(siehe Hinweise unten).</div>')
    else:
        def ge(dist, k):
            return sum(v for key, v in dist.items() if key >= k) / sims

        rows_a, rows_b = [], []
        for l in labels:
            jc = res[l]["jace"]
            cls = LABEL_CLASS.get(l, "")
            rows_a.append([h_mode(l), h_bar_cell(ge(jc["dist_win"], 1), cls=cls), f'<td>{h_pct(ge(jc["dist_win"], 2))}</td>',
                           f'<td>{h_pct(ge(jc["dist_win"], 3))}</td>',
                           f'<td><b>{jc["acts_win"] / sims:.2f}</b></td>', f'<td>{jc["gained_win"] / sims:.2f}</td>',
                           f'<td>{h_pct(jc["empty_reached"] / sims)}</td>'])
            first = sum(jc["first"]) / len(jc["first"]) if jc["first"] else None
            rows_b.append([h_mode(l), h_bar_cell(ge(jc["dist_all"], 1), cls=cls), f'<td>{h_pct(ge(jc["dist_all"], 2))}</td>',
                           f'<td>{h_pct(ge(jc["dist_all"], 3))}</td>',
                           f'<td><b>{jc["acts_all"] / sims:.2f}</b></td>', f'<td>{jc["gained_all"] / sims:.2f}</td>',
                           f'<td>{f"{first:.1f}" if first else "–"}</td>'])
        heads_a = ["", "≥ 1 Aktivierung", "≥ 2", "≥ 3", "Ø Aktivierungen", "Ø Empower", "Hand leer erreicht"]
        heads_b = heads_a[:-1] + ["Erste Aktivierung (Ø Runde)"]
        sim_html = (
            '<div class="panel" style="margin-top:14px"><b>Bis die Hand leer ist</b>'
            + h_table(heads_a, rows_a)
            + '<div class="note">Gezählt wird bis zum ersten Rundenende ohne Karten auf der Hand (nach dem Zaubern und '
              'einer möglichen Jace-Aktivierung). Wird die Hand nie leer, zählt der ganze Beobachtungszeitraum. '
              'Jede Aktivierung (−3) zieht genau eine Karte: Ø Aktivierungen ist deshalb zugleich die Zahl der durch Jace gezogenen Karten. '
              '„Ø Empower“ ist die erhaltene Loyalty insgesamt, „Hand leer erreicht“ der Anteil der Spiele, in denen die Hand innerhalb des '
              'Beobachtungszeitraums leer wurde.</div></div>'
            f'<div class="panel" style="margin-top:14px"><b>Im ganzen Beobachtungszeitraum (bis Runde {H})</b>'
            + h_table(heads_b, rows_b) + '</div>')

    card_rows = []
    for r in sorted(ja["cards"], key=lambda r: (not r["kinds"], r["name"])):
        tags = "".join(f'<span class="tag">{esc(EMPOWER_KIND_LABEL[k])}</span>' for k in r["kinds"]) + "".join(
            f'<span class="tag">{esc(JACE_TAG_LABEL[t])}</span>' for t in r["tags"])
        card_rows.append([f'<td class="l">{esc(r["name"])}</td>', f'<td>{r["qty"]}</td>', f'<td class="l">{tags}</td>',
                          f'<td>{esc(" + ".join(r["values"])) if r["values"] else "–"}</td>',
                          f'<td class="l"><span class="muted" style="font-size:12px">{esc(r["text"])}</span></td>'])
    card_table = h_table(["Karte", "Anz.", "Einordnung", "Empower", "Erkannter Text"], card_rows, left=(0, 2, 4))

    notes = []
    if ja["x_cards"]:
        notes.append("Variabler Wert (X) wird in der Simulation als 0 gezählt: " + ", ".join(ja["x_cards"]))
    if ja["unmodeled"]:
        notes.append("Wirkt in der Simulation nicht (Auslöser oder Kosten nicht modelliert, zählt aber in der Statistik): "
                     + ", ".join(ja["unmodeled"]))
    warn = "".join(f'<div class="warnbox">{esc(n)}</div>' for n in notes)
    rules = [
        "Der Jace-Token startet mit 0 Loyalty und hat die Fähigkeit −3: eine Karte ziehen. Empower legt Loyalty auf den Token, "
        "ohne Token wird ein neuer erstellt. Bei 0 Loyalty verschwindet er, der nächste Empower erstellt einen neuen.",
        "Jace wird aktiviert, sobald er mindestens 3 Loyalty hat und die Bibliothek nicht leer ist, höchstens einmal pro Runde: "
        "zu Rundenbeginn mit Loyalty aus früheren Runden (die Karte kann dann noch gespielt werden), sonst nach dem Zaubern.",
        "Einmalig: Zauber (Instant, Sorcery) und „beim Betreten“-Effekte wirken sofort beim Ausspielen, auch bei Ländern.",
        "Wiederkehrend, modelliert: „whenever you cast …“ (alle, Kreatur, Nichtkreatur, Instant oder Sorcery), „whenever … enters“ "
        "(Kreatur, Land, Permanent), „whenever … attacks“ (ab der Runde nach dem Ausspielen, mit Haste sofort) und „at the beginning of …“ "
        "(einmal pro Runde ab der Folgerunde). Karten reagieren nur auf Ereignisse, nachdem sie im Spiel sind.",
        "Bezahlbare Fähigkeiten werden mit dem Mana benutzt, das nach dem Zaubern übrig ist, so oft es reicht (höchstens 10-mal pro Runde). "
        "Mit {T} im Preis nur einmal pro Runde und bei Kreaturen erst ab der Folgerunde. Andere Kosten (Opfern, Ablegen) sind nicht modelliert.",
        "Modale Zauber zählen ihren Empower immer. Es wird nur die Vorderseite einer Karte simuliert, die Zählung berücksichtigt alle Seiten.",
        "Die Einordnung stammt aus dem Kartentext von Scryfall und ist unten zur Kontrolle neben jeder Karte aufgeführt. "
        "Karten mit weiteren Planeswalker-Bezügen werden nur gezählt und nicht simuliert.",
    ]
    return (f'<div class="grid g3">{kpi_html}</div>'
            f'<div class="panel" style="margin-top:14px"><b>Empower Jace nach Art</b>{kind_table}'
            f'<div class="note">Bei wiederkehrenden Karten ist Σ Empower der Wert je Auslösung beziehungsweise je Aktivierung. '
            f'Eine Karte kann in mehreren Kategorien stehen, deshalb ist die Summe der Zeilen größer als „gesamt“.</div></div>'
            f'{sim_html}'
            f'<div class="panel" style="margin-top:14px">{warn}<b>Karten</b>{card_table}</div>'
            f'<div class="panel" style="margin-top:14px"><b>Modellregeln</b><ul class="ass">'
            + "".join(f"<li>{esc(r)}</li>" for r in rules) + "</ul></div>")


def render_html(ctx):
    a, res, rows = ctx["args"], ctx["results"], ctx["rows"]
    sims, T, C, H = a.sims, a.turns, a.curve_runden, ctx["horizon"]
    labels = list(res.keys())
    sections, nav = [], []

    def add(sid, title, hint, body):
        sections.append(h_section(sid, title, hint, body))
        nav.append((sid, title))

    if ctx.get("alts"):
        add("vergleich", "Deck-Vergleich", f"Hauptdeck gegen {len(ctx['alts'])} Alternative(n), mit statistischer Einordnung der Unterschiede.",
            render_compare_section(ctx))

    # ---------------- Auf einen Blick
    rows_v = []
    for t in range(1, T + 1):
        cells = [f'<td class="l">Zauber gespielt in Runde {t}</td>']
        for lab in labels:
            pct = round(res[lab]["cast"][t] / sims * 100)
            cells.append(h_level_td(traffic_level(pct, lab == "On the Draw", t), f"{pct}%"))
        rows_v.append(cells)
    scr = [f'<td class="l">Mana Screw nach Runde {T}</td>'] + [
        f'<td>{h_pct(res[l]["any_screw"])}</td>' for l in labels]
    fl = [f'<td class="l">Flood ({a.flood}+ Länder bis Runde {H})</td>'] + [
        f'<td>{h_pct(res[l]["flood"])}</td>' for l in labels]
    lt = [f'<td class="l">Schnellster Lethal ({a.schaden} Schaden)</td>']
    for l in labels:
        b = res[l]["best_lethal"]
        lt.append(h_level_td(lethal_level(b["key"][0]) if b else "red",
                             f'Runde {b["key"][0]}' if b else "kein Lethal"))
    avg = [f'<td class="l">Ø Runde für {a.schaden} Schaden</td>']
    for l in labels:
        st = timing_stats(res[l]["dmg"], sims)
        avg.append(f'<td>{st[0]:.1f} <span class="muted">({st[2]:.0%} der Spiele)</span></td>' if st
                   else '<td class="muted">-</td>')
    mu0 = res[labels[0]]["mulligan"]
    mull_rows = []
    if mu0["on"]:
        mull_rows = [
            ['<td class="l">Mulligan auf der ersten Hand</td>'] + [
                f'<td>{h_pct(res[l]["mulligan"]["first_any"] / res[l]["mulligan"]["deals"], 1)}</td>' for l in labels],
            [f'<td class="l">Spiel verloren (Hand unter {mu0["min_hand"]} Karten)</td>'] + [
                f'<td>{h_pct(res[l]["mulligan"]["lost"] / res[l]["mulligan"]["deals"], 1)}</td>' for l in labels],
        ]
    jace_row = []
    if any(res[l]["jace"]["on"] for l in labels):
        jace_row = [['<td class="l">Jace-Aktivierungen bis die Hand leer ist (Ø)</td>'] + [
            f'<td>{res[l]["jace"]["acts_win"] / sims:.2f}</td>' for l in labels]]
    rows_v = mull_rows + rows_v + jace_row + [scr, fl, avg, lt]
    legend = ("Ampel Zauber pro Runde – grün / gelb ab: " + "; ".join(
        f'{("Draw" if d else "Play")} R{t}: ≥{g}% / >{y}%'
        for d, tt in TRAFFIC.items() for t, (g, y) in tt.items()))
    body = (f'<div class="panel">{h_table(["Kennzahl"] + [esc(l) for l in labels], rows_v)}'
            f'<div class="note">{esc(legend)}. Lethal: grün ≤ Runde 5, gelb 6–7, rot ab 8.</div></div>')
    add("blick", "Auf einen Blick", "Die wichtigsten Kennzahlen im Vergleich Play gegen Draw.", body)

    # ---------------- Deck
    cards, nonlands = ctx["cards"], [c for c in ctx["cards"] if not c.is_land]
    kpis = [
        ("Karten", str(len(cards)), f"{len(rows)} verschiedene"),
        ("Länder", str(ctx["n_lands"]), f"{ctx['n_lands'] / len(cards):.0%} des Decks"),
        ("Ø Manakosten", f"{ctx['avg_mv']:.2f}", "ohne Länder"),
        ("Farben", "".join(html_mana(c) for c in sorted(ctx["deck_colors"], key="WUBRGC".find)) or "–",
         "mehrfarbig" if ctx["multicolor"] else "einfarbig"),
    ]
    if ctx["top_mv"] is not None:
        kpis.append(("Top Card", f"{ctx['top_mv']} Mana", ", ".join(ctx["top_names"])))
    kpi_html = "".join(f'<div class="panel kpi"><div class="l">{esc(l)}</div><div class="v">{v}</div>'
                       f'<div class="s">{esc(s_)}</div></div>' for l, v, s_ in kpis)

    mv_counts = Counter(min(c.mv, 7) for c in nonlands)
    mv_labels = [str(i) if i < 7 else "7+" for i in range(0, 8)]
    curve_svg = svg_bars(mv_labels, {"Karten": [mv_counts.get(i, 0) for i in range(8)]},
                         max(max(mv_counts.values(), default=1), 1), lambda v: f"{v:.0f}")
    need = {col: sum(q for _, q, c, _ in rows if not c.is_land and col in required_colors(c)) for col in "WUBRG"}
    srcs = {col: sum(q for _, q, c, _ in rows if c.is_land and col in c.land_colors) for col in "WUBRGC"}
    col_rows = []
    for col in "WUBRGC":
        if need.get(col, 0) or srcs[col]:
            col_rows.append([f'<td class="l">{html_mana(col)}</td>', f'<td>{need.get(col, 0)}</td>',
                             f'<td>{srcs[col]}</td>',
                             h_bar_cell(srcs[col] / max(ctx["n_lands"], 1), f"{srcs[col] / max(ctx['n_lands'], 1):.0%}")])
    col_table = h_table(["Farbe", "Karten", "Quellen", "Anteil der Länder"], col_rows)

    deck_rows = []
    for name, qty, card, shown in sorted(rows, key=lambda r: (r[2].is_land, r[2].mv, r[0])):
        cost = shown.split("   [")[0]
        tags = "".join(f'<span class="tag">{html_cost(t)}</span>' for t in re.findall(r"\[([^\]]*)\]", shown))
        deck_rows.append([f'<td class="l">{esc(name)}</td>', f"<td>{qty}</td>",
                          f'<td class="l">{html_cost(cost)}</td>', f'<td class="l">{tags}</td>'])
    unsure = ""
    if ctx["unsure"]:
        unsure = ('<div class="warnbox">Getappt-Bedingung nicht modelliert (als immer getappt gezählt): '
                  + esc(", ".join(ctx["unsure"])) + "</div>")
    body = (f'<div class="grid g4">{kpi_html}</div>'
            f'<div class="grid g2" style="margin-top:14px">'
            f'<div class="panel"><b>Mana-Kurve</b><div class="note" style="margin:0 0 4px">Anzahl Nichtland-Karten je Manawert</div>{curve_svg}</div>'
            f'<div class="panel"><b>Farbverteilung</b><div class="note" style="margin:0 0 4px">Karten = Nichtland-Karten, die die Farbe brauchen · Quellen = Länder, die sie erzeugen</div>{col_table}</div></div>'
            f'<div class="panel" style="margin-top:14px">{unsure}'
            f'{h_table(["Karte", "Anz.", "Kosten", "Eigenschaften"], deck_rows, left=(0, 2, 3))}</div>')
    add("deck", "Deck", "Kartendaten von Scryfall.", body)

    # ---------------- Mulligan
    if mu0["on"]:
        mh = mu0["min_hand"]
        sizes = list(range(7, mh - 1, -1))
        rows_m = []
        for l in labels:
            mu = res[l]["mulligan"]
            d = mu["deals"]
            cls = LABEL_CLASS.get(l, "")
            rows_m.append([h_mode(l)] + [h_bar_cell(mu["sizes"][k] / d, h_pct(mu["sizes"][k] / d, 1), cls) for k in sizes]
                           + [h_bar_cell(mu["lost"] / d, h_pct(mu["lost"] / d, 1), cls),
                              f'<td>{sims} / {mu["lost"]}</td>'])
        heads = [""] + [f"{k} Karten" for k in sizes] + [f"Verloren (< {mh})", "Gespielt / verloren"]
        reasons = [(MULL_COLORS, "Farben passen nicht"), (MULL_LANDS_HIGH, "6+ Länder"),
                   (MULL_LANDS_LOW, "≤ 2 Länder, < 3 spielbar")]
        rows_r = []
        for l in labels:
            mu = res[l]["mulligan"]
            d = mu["deals"]
            rows_r.append([h_mode(l), f'<td><b>{h_pct(mu["first_any"] / d, 1)}</b></td>']
                          + [f'<td>{h_pct(mu["first"][key] / d, 1)}</td>' for key, _ in reasons])
        rules = [
            "<b>Farben:</b> Mit den Farben der Länder auf der Starthand ist keine Karte spielbar "
            "(nur die Farben zählen, nicht die Manamenge).",
            "<b>Zu viele Länder:</b> 6 oder mehr Länder auf der Starthand.",
            "<b>Zu wenige Länder:</b> Höchstens 2 Länder und weniger als 3 Karten, die sich mit diesen Ländern bezahlen "
            "lassen (Manawert und Farben). Zwei Länder plus lauter 1- und 2-Mana-Karten werden also behalten.",
        ]
        body = (
            '<div class="grid"><div class="panel"><b>Wann es einen Mulligan gibt</b><ul class="ass">'
            + "".join(f"<li>{x}</li>" for x in rules) + '</ul>'
            f'<div class="note">Bei einem Mulligan wird das Deck neu gemischt und eine neue Starthand mit einer Karte weniger '
            f'gezogen. Dieselben Regeln gelten für jede neue Hand. Fällt die Hand unter {mh} Karten, gilt das Spiel als '
            f'verloren. Auch eine {mh}-Karten-Hand, die einen Mulligan auslösen würde, zählt deshalb als verloren.</div></div>'
            '<div class="panel"><b>Erste 7-Karten-Hand: Gründe für einen Mulligan</b>'
            + h_table(["", "Mulligan gesamt"] + [r for _, r in reasons], rows_r)
            + '<div class="note">Anteil aller Starthände. Die Gründe können zusammen auftreten, ihre Summe kann deshalb '
              'über dem Gesamtwert liegen.</div></div></div>'
            '<div class="panel" style="margin-top:14px"><b>Mit wie vielen Karten startet das Spiel?</b> <span class="muted">(Behalten mit … Karten)</span>'
            + h_table(heads, rows_m)
            + f'<div class="note">Prozent aller ausgeteilten Starthände. Verlorene Spiele werden nicht gespielt und fließen '
              f'<b>nicht</b> in die übrigen Zahlen des Berichts ein: Alle anderen Auswertungen beruhen auf {sims} gespielten '
              f'Spielen pro Modus nach dem Mulligan.</div></div>')
        add("mulligan", "Mulligan", "Wie oft die Starthand getauscht werden muss und wie oft das Spiel dadurch verloren geht.", body)

    if ctx["jace"]["any"]:
        add("jace", "Jace & Planeswalker", "Karten mit Empower Jace oder anderen Planeswalker-Bezügen und deren Wirkung in der Simulation.",
            render_jace_section(ctx))

    # ---------------- Zauber pro Runde
    rows_c = []
    for lab in labels:
        r = res[lab]
        cells = [h_mode(lab)]
        for t in range(1, T + 1):
            pct = round(r["cast"][t] / sims * 100)
            cells.append(h_level_td(traffic_level(pct, lab == "On the Draw", t), f"{pct}%"))
        cells.append(f'<td>{r["opener_lands"]:.2f}</td>')
        rows_c.append(cells)
    body = (f'<div class="panel">{h_table([""] + [f"Runde {t}" for t in range(1, T + 1)] + ["Ø Länder in Starthand (nach Mulligan)"], rows_c)}'
            f'<div class="note">Anteil der Spiele, in denen in dieser Runde mindestens ein Zauber gespielt wird (Farben beachtet, '
            f'gespielte Karten sind weg).</div></div>')
    add("zauber", "Zauber pro Runde", f"{sims} Simulationen pro Modus.", body)

    # ---------------- Kreaturen
    rows_k = [[h_mode(l), f'<td>{res[l]["creatures"]:.2f}</td>', f'<td>{res[l]["power"]:.2f}</td>',
               f'<td>{res[l]["toughness"]:.2f}</td>'] for l in labels]
    body = (f'<div class="panel">{h_table(["", "Kreaturen", "Gesamt-Power", "Gesamt-Toughness"], rows_k)}'
            f'<div class="note">Durchschnitt auf dem Feld nach Runde {T}, aufgedruckte Werte ohne Auras und Boni.</div></div>')
    add("kreaturen", f"Kreaturen nach Runde {T}", "", body)

    # ---------------- Screw & Flood
    rule = f"weniger als {T} Länder auf dem Feld" + (" oder keine zwei Farben" if ctx["multicolor"] else "")
    rows_s = []
    for l in labels:
        r = res[l]
        cls = LABEL_CLASS.get(l, "")
        rows_s.append([h_mode(l), h_bar_cell(r["land_screw"], cls=cls),
                       h_bar_cell(r["color_screw"], cls=cls) if ctx["multicolor"] else '<td class="muted">–</td>',
                       h_bar_cell(r["any_screw"], cls=cls)])
    rows_f = [[h_mode(l), h_bar_cell(res[l]["flood"], cls=LABEL_CLASS.get(l, "")),
               f'<td>{res[l]["lands_drawn"]:.1f}</td>'] for l in labels]
    body = (f'<div class="grid"><div class="panel"><b>Mana Screw nach Runde {T}</b>'
            f'<div class="note" style="margin:0 0 6px">{esc(rule)}</div>'
            f'{h_table(["", "Zu wenig Länder", "Farben fehlen", "Gesamt"], rows_s)}</div>'
            f'<div class="panel"><b>Flood</b><div class="note" style="margin:0 0 6px">'
            f'mindestens {a.flood} Länder gezogen bis Runde {H} (inkl. Starthand)</div>'
            f'{h_table(["", "Flooded", "Ø Länder gezogen"], rows_f)}</div></div>')
    add("screw", "Mana Screw & Flood", "", body)

    # ---------------- Curve-Auslastung
    panels = []
    for l in labels:
        cv = res[l]["curve"]
        tot_a, tot_s = sum(cv["avail"].values()), sum(cv["spent"].values())
        tot_g, tot_f = sum(cv["games"].values()), sum(cv["full"].values())
        ts = range(1, C + 1)
        ratio = lambda t: cv["spent"][t] / cv["avail"][t] if cv["avail"][t] else 0
        full = lambda t: cv["full"][t] / cv["games"][t] if cv["games"][t] else 0
        rws = [
            [f'<td class="l">Ø Mana verfügbar</td>'] + [f'<td>{cv["avail"][t] / sims:.2f}</td>' for t in ts]
            + [f'<td><b>{tot_a / sims / C:.2f}</b></td>'],
            [f'<td class="l">Ø Mana ausgegeben</td>'] + [f'<td>{cv["spent"][t] / sims:.2f}</td>' for t in ts]
            + [f'<td><b>{tot_s / sims / C:.2f}</b></td>'],
            [f'<td class="l">Auslastung</td>'] + [f'<td>{h_pct(ratio(t))}</td>' for t in ts]
            + [f'<td><b>{h_pct(tot_s / tot_a if tot_a else 0)}</b></td>'],
            [f'<td class="l">Alles Mana genutzt</td>'] + [f'<td>{h_pct(full(t))}</td>' for t in ts]
            + [f'<td><b>{h_pct(tot_f / tot_g if tot_g else 0)}</b></td>'],
        ]
        panels.append(f'<div class="panel"><b>{esc(l)}</b>'
                      f'{h_table([""] + [f"Runde {t}" for t in ts] + ["Gesamt"], rws)}</div>')
    util = {l: [(res[l]["curve"]["spent"][t] / res[l]["curve"]["avail"][t]) if res[l]["curve"]["avail"][t] else 0
                for t in range(1, C + 1)] for l in labels}
    chart = (f'<div class="panel" style="margin-top:14px"><b>Auslastung je Runde</b>{h_legend(labels)}'
             f'{svg_bars([f"R{t}" for t in range(1, C + 1)], util, 1.0, lambda v: f"{v:.0%}")}'
             f'<div class="note">Ausgegebenes geteilt durch verfügbares Mana. Nur Mana aus Ländern, '
             f'Manakreaturen und Artefakte sind nicht modelliert.</div></div>')
    add("curve", "Curve-Auslastung", f"Runde 1–{C}: wie gut wird das Mana genutzt?",
        f'<div class="grid">{"".join(panels)}</div>{chart}')

    add("logik", "Spiellogik", "Nach welchen Regeln der Simulator Länder und Zauber auswählt.", render_logic_section(any(res[l]["jace"]["on"] for l in labels)))

    # ---------------- Schaden & Lethal
    rows_d = []
    for l in labels:
        st = timing_stats(res[l]["dmg"], sims)
        rows_d.append([h_mode(l)] + ([f"<td>{st[0]:.1f}</td>", f"<td>{st[1]:.1f}</td>", h_bar_cell(st[2], cls=LABEL_CLASS.get(l, ""))] if st
                                     else ['<td class="muted">–</td>'] * 2 + [h_bar_cell(0)]))
    xs = list(range(1, H + 1))
    cum = {l: [sum(1 for v in res[l]["dmg"] if v <= t) / sims for t in xs] for l in labels}
    chart = (f'<div class="panel"><b>Wahrscheinlichkeit, bis Runde X mindestens {a.schaden} Schaden verursacht zu haben</b>'
             f'{h_legend(labels)}{svg_lines(xs, cum)}</div>')
    table = (f'<div class="panel"><b>Erste Runde mit {a.schaden} Schaden</b>'
             f'{h_table(["", "Ø Runde", "Median", "Eintritt"], rows_d)}'
             f'<div class="note">Ø und Median nur über Spiele, in denen es bis Runde {H} eintritt. '
             f'Alle Kreaturen greifen jede Runde an, Einsatzverzögerung außer Haste, keine Blocker oder Removal, '
             f'nur aufgedruckte Power.</div></div>')
    add("schaden", "Schaden durch Kreaturen", "", f'<div class="grid g2">{table}{chart}</div>')

    lethals = []
    for l in labels:
        b = res[l]["best_lethal"]
        if not b:
            lethals.append(f'<div class="panel lethal"><div class="head"><b>{esc(l)}</b>'
                           f'{h_level_pill("red", "kein Lethal")}</div></div>')
            continue
        turn, neg = b["key"]
        hand = "".join(f'<span class="card {"land" if c.is_land else ""}">{esc(c.name)}</span>'
                       for c in sorted(b["opening"], key=lambda c: (c.is_land, c.mv, c.name)))
        trs = []
        for t, drew, land, tapped, cast, tdmg, total, cycled, jinfo in b["log"]:
            land_txt = "–" if land is None else esc(land.name) + (' <span class="tag">getappt</span>' if tapped else "")
            cast_txt = ", ".join(esc(card_label(c)) for c in cast) or "–"
            cyc_txt = "".join(f'<span class="tag">Landcycling: {esc(c.name)}</span>' for c, _ in cycled)
            if jinfo[0]:
                cyc_txt += f'<span class="tag">Jace +{jinfo[0]} → {jinfo[2]} Loyalty</span>'
            if jinfo[1]:
                cyc_txt += '<span class="tag">Jace aktiviert (+1 Karte)</span>'
            trs.append([f'<td class="l">Runde {t}</td>', f'<td class="l">{esc(drew.name) if drew else "–"}</td>',
                        f'<td class="l">{land_txt}</td>', f'<td class="l">{cast_txt} {cyc_txt}</td>',
                        f'<td class="dmg">+{tdmg}</td>',
                        h_bar_cell(min(total / a.schaden, 1), f"{total}", LABEL_CLASS.get(l, ""))])
        lethals.append(
            f'<div class="panel lethal"><div class="head"><span class="dot {LABEL_CLASS.get(l, "")}"></span>'
            f'<b>{esc(l)}</b>{h_level_pill(lethal_level(turn), f"Runde {turn}")}'
            f'<span class="muted">{-neg} Schaden</span>'
            + (f'<span class="tag">Mulligan: Starthand mit {len(b["opening"])} Karten</span>' if b.get("mulls") else "")
            + '</div>'
            f'<div class="muted" style="font-size:12.5px">Starthand</div><div class="hand">{hand}</div>'
            f'{h_table(["", "Zieht", "Land", "Zauber", "Schaden", "Gesamt"], trs, "class=tl", left=(0, 1, 2, 3))}</div>')
    add("lethal", "Schnellster Lethal",
        f"Das schnellste von {sims} simulierten Spielen (bei gleicher Runde das mit mehr Schaden) – "
        f"ein Glücksfall, kein Erwartungswert.", f'<div class="grid">{"".join(lethals)}</div>')

    # ---------------- Landcycling
    if ctx["cyc_names"] and not a.ohne_landcycling:
        panels = []
        for l in labels:
            lc = res[l]["landcycle"]
            ev = lc["events"]
            if not ev:
                panels.append(f'<div class="panel"><b>{esc(l)}</b><p class="muted">in {sims} Simulationen nie nötig oder möglich</p></div>')
                continue
            pb, pa = lc["p_before"] / ev, lc["p_after"] / ev
            first = sum(lc["first"]) / len(lc["first"])
            reasons = "".join(f'<tr><td class="l">{esc(k)}</td>{h_bar_cell(v / ev, cls=LABEL_CLASS.get(l, ""))}</tr>'
                              for k, v in lc["reason"].most_common())
            cards_ = "".join(f'<tr><td class="l">{esc(n)}</td><td>{v}×</td>{h_bar_cell(v / ev, cls=LABEL_CLASS.get(l, ""))}</tr>'
                             for n, v in lc["card"].most_common())
            panels.append(
                f'<div class="panel"><b>{esc(l)}</b>'
                f'<div class="grid g4" style="margin:10px 0">'
                f'<div class="kpi"><div class="l">Spiele mit Cycling</div><div class="v">{h_pct(lc["games"] / sims)}</div></div>'
                f'<div class="kpi"><div class="l">Ø pro Spiel</div><div class="v">{ev / sims:.2f}</div></div>'
                f'<div class="kpi"><div class="l">Erstmals Ø in</div><div class="v">Runde {first:.1f}</div></div>'
                f'<div class="kpi"><div class="l">Nicht-Land-Chance</div><div class="v">+{(pa - pb) * 100:.1f} PP</div>'
                f'<div class="s">{pb:.1%} → {pa:.1%} (relativ +{(pa / pb - 1) if pb else 0:.1%})</div></div></div>'
                f'<div class="grid g2"><div><b class="muted">Grund</b><table>{reasons}</table></div>'
                f'<div><b class="muted">Meistgenutzte Karte</b><table>{cards_}</table></div></div></div>')
        add("landcycling", "Landcycling", "Karten im Deck: " + esc(", ".join(ctx["cyc_names"])),
            f'<div class="grid">{"".join(panels)}</div>')

    # ---------------- Tempo
    rows_t = []
    for l in labels:
        r = res[l]
        for title, key in (("Hand komplett leer", "empty_hand"), ("Keine Zauber mehr auf der Hand", "empty_spells"),
                           ("Top Card spielbar", "top")):
            if key == "top" and ctx["top_mv"] is None:
                continue
            st = timing_stats(r[key], sims)
            rows_t.append([h_mode(l), f'<td class="l">{esc(title)}</td>'] +
                          ([f"<td>{st[0]:.1f}</td>", f"<td>{st[1]:.1f}</td>", h_bar_cell(st[2], cls=LABEL_CLASS.get(l, ""))] if st
                           else ['<td class="muted">–</td>'] * 2 + [h_bar_cell(0)]))
    body = (f'<div class="panel">{h_table(["", "Ereignis", "Ø Runde", "Median", "Eintritt"], rows_t, left=(0, 1))}'
            f'<div class="note">Beobachtung bis Runde {H}; Ø und Median nur über Spiele, in denen das Ereignis eintritt. '
            + (f'Top Card: {esc(", ".join(ctx["top_names"]))} (Manawert {ctx["top_mv"]}).' if ctx["top_mv"] is not None else "")
            + '</div></div>')
    add("tempo", "Tempo", "", body)

    # ---------------- Annahmen
    ass = [
        ("Starthand 7 Karten mit Mulligan-Regeln (siehe Abschnitt Mulligan); jede Runde ziehen (On the Play erst ab Runde 2), "
         "ein Land legen, zaubern." if mu0["on"] else
         "Starthand 7 Karten ohne Mulligans; jede Runde ziehen (On the Play erst ab Runde 2), ein Land legen, zaubern."),
        "Jede Nichtland-Karte wird gespielt, sobald sie bezahlbar ist; pro Runde wird möglichst viel Mana ausgegeben.",
        "Farben, Hybrid- und Phyrexian-Mana werden beachtet; Manakreaturen und Artefakte sind nicht modelliert.",
        "Länder, die getappt ins Spiel kommen, werden aus dem Kartentext erkannt; Shock-Länder zahlen die 2 Leben.",
        "Auras werden nur mit eigener Kreatur gespielt" if not a.auras_ohne_kreatur else "Auras dürfen ohne eigene Kreatur gespielt werden.",
        "Kreaturen: aufgedruckte Power/Toughness, Einsatzverzögerung außer Haste, keine Blocker oder Removal.",
    ]
    if ctx["cyc_names"]:
        ass.append("Landcycling ist deaktiviert." if a.ohne_landcycling else
                   f"Landcycling mit Vorausschau (nur wenn es sich lohnt); fehlender Landdrop wird bis Runde {a.landcycling_runden} "
                   f"gesichert; Cycling nicht spielbarer Karten nur unter {a.landcycling_max_laender} Ländern; "
                   + ("auch die letzte Karte darf gecycelt werden." if a.landcycling_letzte_karte
                      else "die letzte Karte auf der Hand wird nicht gecycelt."))
    if any(res[l]["jace"]["on"] for l in labels):
        ass.append("Empower Jace: Jace-Token mit −3 (Karte ziehen), aktiviert ab 3 Loyalty, höchstens einmal pro Runde; "
                   "Regeln im Abschnitt Jace & Planeswalker.")
    add("annahmen", "Modellannahmen", "", '<div class="panel"><ul class="ass">' + "".join(f"<li>{esc(x)}</li>" for x in ass) + "</ul></div>")

    chips = ([f"Vergleich mit {len(ctx['alts'])} Alternative(n)"] if ctx.get("alts") else []) + (
        [f"Seed {a.seed}"] if a.seed is not None else []) + [f"{sims} gespielte Spiele pro Modus", "Mulligan an" if mu0["on"] else "ohne Mulligan", f"Auswertung Runde {T}", f"Beobachtung bis Runde {H}",
             f"{a.schaden} Schaden", f"Flood ab {a.flood} Ländern"]
    nav_html = "".join(f'<a href="#{i}">{esc(t)}</a>' for i, t in nav)
    missing_html = ('<div class="warnbox" style="margin-top:14px"><b>Nicht bei Scryfall gefunden (nicht simuliert):</b> '
                    + esc(", ".join(ctx["missing"])) + "</div>") if ctx.get("missing") else ""
    stamp = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    return (f'<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(ctx["name"])} – MTG Simulation</title><style>{HTML_CSS}</style></head><body>'
            f'<header class="top"><h1>{esc(ctx["name"])}</h1>'
            f'<div class="sub">Starthand-Simulation · erstellt am {stamp}</div>'
            f'<div class="chips">{"".join(f"<span class=chip>{esc(c)}</span>" for c in chips)}</div></header>'
            f'<nav><div class="in">{nav_html}</div></nav><main>{missing_html}{"".join(sections)}</main>'
            f'<footer>Erzeugt mit mtg_sim.py · Kartendaten von Scryfall</footer></body></html>')



def main():
    ap = argparse.ArgumentParser(description="MTG Starthand-Simulator: erzeugt einen HTML-Bericht")
    ap.add_argument("deckfile", nargs="+",
                    help="Deckliste(n). Mit --core: die Varianten, die zum Kern hinzukommen; die erste ist die Basis, "
                         "alle weiteren werden mit ihr verglichen")
    ap.add_argument("--core", metavar="DATEI", default=None,
                    help="Kern-Deckliste, die zu jeder Variante (deckfile / --deckalt) hinzugefuegt wird")
    ap.add_argument("--neu-laden", action="store_true",
                    help="Kartendaten neu von Scryfall laden und den lokalen Cache (scryfall_cache.json) ueberschreiben")
    ap.add_argument("--sims", type=int, default=10000)
    ap.add_argument("--turns", type=int, default=3)
    ap.add_argument("--max-runden", type=int, default=15,
                    help="Bis zu welcher Runde fuer Handleer/Top-Card-Statistik simuliert wird")
    ap.add_argument("--deckalt", action="append", metavar="DATEI", default=None,
                    help="Alternative Deckliste zum Vergleich mit dem Hauptdeck (mehrfach angeben moeglich)")
    ap.add_argument("--seed", type=int, default=None,
                    help="Fester Zufallswert fuer reproduzierbare Ergebnisse (Standard: zufaellig)")
    ap.add_argument("--auras-ohne-kreatur", action="store_true",
                    help="Auras duerfen auch ohne eigene Kreatur auf dem Feld gespielt werden")
    ap.add_argument("--ohne-landcycling", action="store_true",
                    help="Landcycling nicht benutzen (Karten werden nur normal gespielt)")
    ap.add_argument("--landcycling-letzte-karte", action="store_true",
                    help="Landcycling auch dann, wenn die Karte die letzte Karte auf der Hand waere")
    ap.add_argument("--landcycling-runden", type=int, default=3,
                    help="Bis zu welcher Runde ein fehlender Landdrop per Landcycling gesichert wird")
    ap.add_argument("--landcycling-max-laender", type=int, default=6,
                    help="Cycling einer nicht spielbaren Karte nur bei weniger Laendern (Feld + Hand)")
    ap.add_argument("--ohne-mulligan", action="store_true",
                    help="Keine Mulligans: jede Starthand mit 7 Karten wird gespielt")
    ap.add_argument("--min-handkarten", type=int, default=5,
                    help="Faellt die Starthand durch Mulligans darunter, gilt das Spiel als verloren (Standard 5)")
    ap.add_argument("--ohne-jace", action="store_true",
                    help="Empower Jace nicht simulieren (die Zaehlung der Karten bleibt)")
    ap.add_argument("--curve-runden", type=int, default=6,
                    help="Bis zu welcher Runde die Curve-Auslastung berechnet wird")
    ap.add_argument("--schaden", type=int, default=20,
                    help="Gesamtschaden der Kreaturen, dessen erste Runde gemessen wird")
    ap.add_argument("--flood", type=int, default=11,
                    help="Ab wie vielen gezogenen Laendern (bis zur Maximalrunde) gilt man als geflutet")
    ap.add_argument("--ausgabe", "--html", dest="ausgabe", default="mtg_bericht.html", metavar="DATEI",
                    help="Name des HTML-Berichts (Standard: mtg_bericht.html)")
    ap.add_argument("--nicht-oeffnen", action="store_true",
                    help="HTML-Bericht nicht automatisch im Browser oeffnen")
    run(ap.parse_args())


def build_deck(entry, data, args):
    """Wertet eine Deckliste mit den Scryfall-Daten aus."""
    cards, rows, missing = [], [], []
    for name, qty in entry["deck"].items():
        sc = data.get(name) or data.get(name.split(" // ")[0])
        if not sc:
            missing.append(name)
            print(f"Uebersprungen (nicht gefunden) in {entry['name']}: {name}", file=sys.stderr)
            continue
        card, shown = card_info(sc)
        rows.append((name, qty, card, shown))
        cards += [card] * qty
    if len(cards) < 7 + args.turns:
        sys.exit(f"Zu wenige Karten im Deck {entry['name']}.")
    nonlands = [c for c in cards if not c.is_land]
    castable = [c for c in nonlands if c.alts]
    top_mv = max((c.mv for c in castable), default=None)
    deck_colors = sorted(set().union(*(required_colors(c) for c in nonlands)))
    return dict(
        name=entry["name"], deck=entry["deck"], rows=rows, cards=cards, missing=missing,
        n_lands=len(cards) - len(nonlands),
        avg_mv=sum(c.mv for c in nonlands) / len(nonlands) if nonlands else 0,
        unsure=sorted({n for n, _, c, _ in rows if c.is_land and c.tap_mode == "tapped?"}),
        deck_colors=deck_colors, multicolor=len(deck_colors) >= 2, top_mv=top_mv,
        top_names=sorted({n for n, _, c, _ in rows if not c.is_land and c.alts and c.mv == top_mv}),
        cyc_names=sorted({n for n, _, c, _ in rows if c.cycle_alts}))


def simulate_deck(dd, args, idx, horizon):
    """Simuliert On the Play und On the Draw. Mit --seed bekommt jedes Deck einen eigenen, festen Zufallsstrom."""
    if args.seed is not None:
        random.seed(args.seed + 7919 * idx)
    print(f"Simuliere {dd['name']}: {args.sims} Spiele pro Modus ...", file=sys.stderr)
    results = {}
    for label, on_draw in (("On the Play", False), ("On the Draw", True)):
        try:
            results[label] = simulate(dd["cards"], args.sims, on_draw, args.turns, horizon,
                                      not args.auras_ohne_kreatur, dd["multicolor"], dd["top_mv"], args.flood,
                                      args.schaden, args.curve_runden, not args.ohne_landcycling,
                                      args.landcycling_runden, args.landcycling_max_laender,
                                      args.landcycling_letzte_karte, not args.ohne_mulligan, args.min_handkarten,
                                      not args.ohne_jace)
        except RuntimeError as e:
            sys.exit(f"{dd['name']}: {e}")
    dd["results"] = results


def run(args):
    entries, used = [], Counter()
    core = {}
    if args.core:
        with open(args.core, encoding="utf-8") as f:
            core = parse_deck(f.read())
        print(f"Kern: {sum(core.values())} Karten aus {args.core}", file=sys.stderr)
    for path in list(args.deckfile) + (args.deckalt or []):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        name = parse_deck_name(text, pathlib.Path(path).stem)
        used[name] += 1
        if used[name] > 1:
            name = f"{name} ({used[name]})"
        deck = Counter(core)
        deck.update(parse_deck(text))
        entries.append({"path": path, "name": name, "deck": dict(deck)})

    print("Lade Kartendaten von Scryfall ...", file=sys.stderr)
    try:
        data = fetch_cards_cached(sorted(set().union(*(e["deck"].keys() for e in entries))), args.neu_laden)
    except urllib.error.URLError as e:
        sys.exit(f"Scryfall nicht erreichbar: {e}")

    horizon = max(args.max_runden, args.turns, args.curve_runden)
    decks = [build_deck(e, data, args) for e in entries]
    for idx, dd in enumerate(decks):
        simulate_deck(dd, args, idx, horizon)

    main_deck = decks[0]
    ctx = dict(main_deck, args=args, horizon=horizon, jace=analyze_jace(main_deck["rows"]), alts=decks[1:])
    out_path = pathlib.Path(args.ausgabe)
    out_path.write_text(render_html(ctx), encoding="utf-8")
    print(f"Bericht gespeichert: {out_path.resolve()}", file=sys.stderr)
    if not args.nicht_oeffnen:
        try:
            webbrowser.open(out_path.resolve().as_uri())
        except Exception:
            pass


if __name__ == "__main__":
    main()
