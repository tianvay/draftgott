"""Kartenmodell: Card und die Auswertung der Scryfall-Daten (Laender, Landcycling, Empower Jace, Planeswalker-Tags)."""
import re
from typing import NamedTuple

from components.mana import cost_alternatives, mana_value


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
    defender: bool = False     # Kreatur mit Defender: kann nicht angreifen
    is_jace: bool = False      # Planeswalker mit Untertyp Jace (fuer "behold a Jace")
    draws: int = 0             # Karten, die der Zauber (bzw. die Kreatur beim Betreten) sofort zieht
    surveil: int = 0           # Surveil N beim Wirken bzw. Betreten (auch Laender)


LANDCYCLE_RE = re.compile(
    r"(basic land|plains|island|swamp|mountain|forest|land)cycling\s*((?:\{[^}]+\})+)", re.I)
TAPPED_RE = re.compile(r"enters( the battlefield)? tapped")


def land_tap_info(card, front):
    """Liest aus dem Kartentext, ob/wann ein Land getappt ins Spiel kommt.
    Modi: no (nie), tapped (immer), tapped? (Bedingung nicht modelliert -> wie 'tapped' gezaehlt),
          fast (untapped, wenn hoechstens 2 andere Laender), slow (untapped ab 2 anderen Laendern),
          check (untapped, wenn du einen der genannten Landtypen kontrollierst),
          planeswalker (untapped, wenn du einen Planeswalker kontrollierst),
          jace (untapped, wenn du einen Jace kontrollierst oder eine Jace-Karte von der Hand zeigst)."""
    text = (front.get("oracle_text") or card.get("oracle_text") or "").lower()
    if not TAPPED_RE.search(text):
        return "no", ()
    if "pay 2 life" in text:        # Shock-Land: Leben wird bezahlt
        return "no", ()
    if "two or fewer other lands" in text:
        return "fast", ()
    if "two or more other lands" in text:
        return "slow", ()
    if re.search(r"unless you control an? planeswalker", text):
        return "planeswalker", ()
    if "behold a jace" in text:
        return "jace", ()
    m = re.search(r"unless you control ((?:an? [a-z]+(?:,? or |, | or )?)+)", text)
    if m:
        types = tuple(sorted(set(re.findall(r"an? ([a-z]+)", m.group(1)))))
        if types:
            return "check", types
    return ("tapped?" if "unless" in text else "tapped"), ()


def enters_tapped(land, battlefield, walker=False, jace=False):
    """Kommt dieses Land mit den bereits liegenden Laendern getappt ins Spiel?
    walker: ein Planeswalker liegt auf dem Tisch; jace: ein Jace liegt auf dem Tisch oder eine Jace-Karte ist auf der
    Hand (nur fuer Laender mit Planeswalker- bzw. Jace-Bedingung von Bedeutung)."""
    mode = land.tap_mode
    if mode == "no":
        return False
    if mode == "fast":
        return len(battlefield) > 2
    if mode == "slow":
        return len(battlefield) < 2
    if mode == "check":
        return not any(set(l.land_types) & set(land.tap_arg) for l in battlefield)
    if mode == "planeswalker":
        return not walker
    if mode == "jace":
        return not jace
    return True  # tapped / tapped?


def tap_tag(mode, arg):
    return {
        "no": "",
        "tapped": "   [getappt]",
        "tapped?": "   [getappt (Bedingung nicht modelliert)]",
        "fast": "   [getappt ab dem 4. Land]",
        "slow": "   [getappt, solange weniger als 2 andere Laender]",
        "check": "   [getappt, ausser du kontrollierst: " + "/".join(arg) + "]",
        "planeswalker": "   [getappt, ausser du kontrollierst einen Planeswalker]",
        "jace": "   [getappt, ausser du kontrollierst oder zeigst einen Jace]",
    }[mode]


_DRAW_NUM = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7}
_DRAW_N = r"(a|an|one|two|three|four|five|six|seven|\d+) cards?\."
# Zauber: "Draw N cards." am Zeilenanfang (Twinned Vision: nicht von der Hand gewirkt kommt nie vor)
DRAW_SPELL_RE = re.compile(r"^draw " + _DRAW_N +
                           r"(\s*if this spell wasn't cast from your hand, draw [^.]* instead\.)?(?=\s|$)")
# Bleibende Karte: "When this creature enters, draw N cards."
DRAW_ETB_RE = re.compile(r"^when (this [a-z]+|~) enters, draw " + _DRAW_N + r"(?=\s|$)")


def draw_line(line, spell_face, name=""):
    """Erkennt Ziehen mit fester Zahl am Anfang einer Textzeile (ohne Erinnerungstext). Gibt (Anzahl, Resttext in
    Kleinbuchstaben) zurueck; (0, Zeile) wenn nichts Modelliertes darin steht."""
    low = line.lower().strip()
    if name:
        low = low.replace(name.lower(), "~")
    m = (DRAW_SPELL_RE if spell_face else DRAW_ETB_RE).match(low)
    if not m:
        return 0, low
    word = m.group(1) if spell_face else m.group(2)
    return _DRAW_NUM.get(word) or int(word), low[m.end():].strip()


def parse_draws(card, type_line):
    """Summe der modellierten Draw-Effekte der Vorderseite."""
    front = (card.get("card_faces") or [card])[0]
    text = front.get("oracle_text") or card.get("oracle_text") or ""
    spell_face = "Instant" in type_line or "Sorcery" in type_line
    total = 0
    for raw in text.split("\n"):
        total += draw_line(re.sub(r"\([^)]*\)", "", raw), spell_face, card.get("name", ""))[0]
    return total


# Surveil N: im Zauber als eigener Satz, bei bleibenden Karten (auch Laendern) beim Betreten
SURVEIL_SPELL_RE = re.compile(r"(?:^|(?<=\. ))surveil (\d+)\.(?=\s|$)")
SURVEIL_ETB_RE = re.compile(r"^when (this [a-z]+|~) enters, surveil (\d+)\.(?=\s|$)")


def surveil_line(line, spell_face, name=""):
    """Erkennt Surveil mit fester Zahl in einer Textzeile (ohne Erinnerungstext). Gibt (Anzahl, Resttext in
    Kleinbuchstaben) zurueck; (0, Zeile) wenn nichts Modelliertes darin steht."""
    low = line.lower().strip()
    if name:
        low = low.replace(name.lower(), "~")
    m = SURVEIL_SPELL_RE.search(low) if spell_face else SURVEIL_ETB_RE.match(low)
    if not m:
        return 0, low
    return int(m.group(1 if spell_face else 2)), (low[:m.start()] + low[m.end():]).strip()


def parse_surveil(card, type_line):
    """Summe der modellierten Surveil-Effekte der Vorderseite."""
    front = (card.get("card_faces") or [card])[0]
    text = front.get("oracle_text") or card.get("oracle_text") or ""
    spell_face = "Instant" in type_line or "Sorcery" in type_line
    return sum(surveil_line(re.sub(r"\([^)]*\)", "", raw), spell_face, card.get("name", ""))[0]
               for raw in text.split("\n"))


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
        surveil = parse_surveil(card, type_line)
        if surveil:
            shown += f"   [Surveil {surveil}]"
        return (Card(True, 0, (), colors, False, False, 0, 0, False, tap_mode, tap_arg, subtypes,
                     card["name"], is_basic="Basic" in type_line, empower=eff, empower_text=etext,
                     pw_tags=pw_tags_for(card, type_line), surveil=surveil), shown)

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
    defender = is_creature and "Defender" in keywords
    shown = " // ".join(costs) or "-"
    if is_creature:
        shown += f"   [Kreatur {pw}/{tg}" + (", Haste" if haste else "") + (", Defender]" if defender else "]")
    elif is_aura:
        shown += "   [Aura]"
    shown += cycle_tag
    eff, etext = parse_empower(card)
    shown += empower_tags_text(eff)
    draws = parse_draws(card, type_line)
    if draws:
        shown += f"   [Zieht {draws}]"
    surveil = parse_surveil(card, type_line)
    if surveil:
        shown += f"   [Surveil {surveil}]"
    return Card(False, mv, alts, (), is_creature, is_aura,
                power if is_creature else 0, tough if is_creature else 0, haste,
                name=card["name"], cycle_alts=cycle_alts, cycle_target=cycle_target,
                cycle_mv=cycle_mv, is_instant_sorcery=("Instant" in type_line or "Sorcery" in type_line),
                is_planeswalker="Planeswalker" in type_line, empower=eff, empower_text=etext,
                pw_tags=pw_tags_for(card, type_line), defender=defender,
                is_jace=("Planeswalker" in type_line and "Jace" in type_line.split("—")[-1].split()),
                draws=draws, surveil=surveil), shown
