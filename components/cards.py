"""Kartenmodell: Card und die Auswertung der Scryfall-Daten (Laender, Landcycling, Empower Jace, Planeswalker-Tags)."""
import re
from typing import NamedTuple

from components.mana import cost_alternatives, mana_value
from components.removal import discard_count, has_flash, removal_spec


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
    prepared: tuple = ()       # Prepared: (Modus "enters"/"upkeep"/"both", Card der Zauberhaelfte)
    is_copy: bool = False      # Kopie einer Prepared-Zauberhaelfte (verbraucht keine Handkarte)
    mana_src: tuple = ()       # Mana-Faehigkeit "{T}: Add ...": je Mana ein Farbtupel (wie land_colors)
    treasure: int = 0          # Treasure-Token beim Wirken bzw. Betreten
    modes: tuple = ()          # Effekte beim Wirken/Betreten je Modus: ("face", n), ("counter", n, Ziele),
    #                            ("counter_all", n), ("pump", n), ("pump_all", n)  (siehe effect_modes)
    landfall: tuple = ()       # bei jedem eigenen Land: ("face", n), ("mountain_mana", "R"), ("type_counter", Typ, n)
    endstep_counters: int = 0  # Marken am Rundenende, wenn in der Runde kein Zauber gewirkt wurde (Edgar)
    loyalty_counter: int = 0   # Marken, wenn Loyalty auf einen Planeswalker kommt (Inspired Tethermage)
    gy_x: bool = False         # Wert haengt vom hoechsten Manawert im Friedhof ab (Hapatra)
    kw: tuple = ()             # Kampf-Schluesselwoerter der Karte selbst (flying, reach, first strike, ...)
    self_damage: int = 0       # Schaden an uns selbst beim Wirken/Betreten ("damage to each player"), nur im Kampf
    is_instant: bool = False   # Instant (im Kampf ausserhalb der eigenen Main Phase spielbar)
    flash: bool = False        # bleibende Karte mit Flash
    removal: tuple = ()        # Removal im Kampf (removal.removal_spec)
    discard: int = 0           # der Gegner wirft beim Wirken/Betreten Karten ab


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


def _name_to_tilde(low, name):
    """Ersetzt den Kartennamen (als ganzes Wort) durch "~", damit Texte wie "When <Name> enters" erkannt werden."""
    if not name:
        return low
    return re.sub(r"(?<![a-z])" + re.escape(name.lower()) + r"(?![a-z])", "~", low)


def draw_line(line, spell_face, name=""):
    """Erkennt Ziehen mit fester Zahl am Anfang einer Textzeile (ohne Erinnerungstext). Gibt (Anzahl, Resttext in
    Kleinbuchstaben) zurueck; (0, Zeile) wenn nichts Modelliertes darin steht."""
    low = _name_to_tilde(line.lower().strip(), name)
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
    low = _name_to_tilde(line.lower().strip(), name)
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


ANY_COLOR = ("B", "G", "R", "U", "W")
_MANA_ABILITY_RE = re.compile(r"^\{t\}: add (.+?)\.?$")
_NUMBER = {"one": 1, "two": 2, "three": 3}


def mana_ability_units(line):
    """Mana-Faehigkeit ohne Zusatzkosten ("{T}: Add {G}.", "{T}: Add {R} or {G}.", "{T}: Add one mana of any color.",
    "{T}: Add {C}{C}."). Gibt je Mana ein Farbtupel zurueck, sonst ()."""
    m = _MANA_ABILITY_RE.match(line.lower().strip())
    if not m:
        return ()
    what = m.group(1).strip()
    if re.fullmatch(r"(\{[wubrgc]\})+", what):
        return tuple((sym.upper(),) for sym in re.findall(r"\{([wubrgc])\}", what))
    if re.fullmatch(r"\{[wubrg]\}(, \{[wubrg]\})*,? or \{[wubrg]\}", what):
        return (tuple(sorted({sym.upper() for sym in re.findall(r"\{([wubrg])\}", what)})),)
    m = re.fullmatch(r"(one|two|three) mana of any (?:one )?color", what)
    if m:
        return (ANY_COLOR,) * _NUMBER[m.group(1)]
    return ()


_TREASURE_ETB_RE = re.compile(r"^when (this [a-z]+|~) enters, create (a|an|one|two|three) treasure tokens?\.")
_TREASURE_SPELL_RE = re.compile(r"(?:^|(?<=\. ))create (a|an|one|two|three) treasure tokens?\.")


def treasure_line(line, spell_face, name=""):
    """Treasure-Token beim Betreten bzw. als Satz eines Zaubers (fester Wert); sonst 0."""
    low = _name_to_tilde(line.lower().strip(), name)
    m = (_TREASURE_SPELL_RE.search(low) if spell_face else _TREASURE_ETB_RE.match(low))
    if not m:
        return 0
    word = m.group(1 if spell_face else 2)
    return {"a": 1, "an": 1}.get(word) or _NUMBER[word]


def parse_mana(card, type_line):
    """(Manaquellen-Tupel, Treasure) der Vorderseite."""
    front = (card.get("card_faces") or [card])[0]
    text = front.get("oracle_text") or card.get("oracle_text") or ""
    spell_face = "Instant" in type_line or "Sorcery" in type_line
    units, treasures = (), 0
    for raw in text.split("\n"):
        line = re.sub(r"\([^)]*\)", "", raw).strip()
        if not spell_face:
            units += mana_ability_units(line)
        treasures += treasure_line(line, spell_face, card.get("name", ""))
    return units, treasures


_EFFECT_NUM = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4}
_FACE_RE = re.compile(r"(?<![a-z])(?:~|it|this [a-z]+) deals (\d+) damage to (?:each opponent|target opponent|target player|"
                      r"each player|any target|target player or planeswalker|target opponent or planeswalker)\b")
_COUNTER_ALL_RE = re.compile(r"\bput (a|an|one|two|three|\d+) \+1/\+1 counters? on each creature "
                             r"(?:you control|target player controls)\b")
_COUNTER_RE = re.compile(r"\bput (a|an|one|two|three|\d+) \+1/\+1 counters? on (up to one target creature|"
                         r"another target creature|target creature(?: you control)?|each of (?:one or two|up to two) "
                         r"target creatures|it)\b")
_PUMP_RE = re.compile(r"\b(?:up to one |another )?target creature(?: you control)? gets \+(\d+)/\+(\d+)[^.]*?"
                      r"until end of turn")
_PUMP_ALL_RE = re.compile(r"\bcreatures you control get \+(\d+)/\+(\d+)[^.]*?until end of turn")
_ETB_EFFECT_RE = re.compile(r"^when (?:this [a-z]+|~) enters,\s*(.*)$")
_LANDFALL_FACE_RE = re.compile(r"^(?:landfall — )?whenever a land you control enters, ~ deals (\d+) damage to each "
                               r"opponent\.")
_LANDFALL_MANA_RE = re.compile(r"\bif that land is a mountain, add \{r\}\.")
_TYPE_COUNTER_RE = re.compile(r"^whenever an? (plains|island|swamp|mountain|forest) you control enters, put a \+1/\+1 "
                              r"counter on target creature\.$")
_ENDSTEP_RE = re.compile(r"^at the beginning of your end step, if you didn't cast a spell this turn, put "
                         r"(a|an|one|two|three|\d+) \+1/\+1 counters? on (?:~|this creature)\.$")
_LOYALTY_COUNTER_RE = re.compile(r"^whenever you put one or more loyalty counters on a planeswalker, put "
                                 r"(a|an|one|two|\d+) \+1/\+1 counters? on (?:~|this creature)\.$")


def _count(word):
    return _EFFECT_NUM.get(word) or int(word)


def _effect_atoms(text):
    """Modellierte Effekte in einem Text (Reihenfolge wie im Text)."""
    found = []
    for m in _FACE_RE.finditer(text):
        found.append((m.start(), ("face", int(m.group(1)))))
    for m in _COUNTER_ALL_RE.finditer(text):
        found.append((m.start(), ("counter_all", _count(m.group(1)))))
    rest = _COUNTER_ALL_RE.sub(lambda m: " " * len(m.group(0)), text)
    for m in _COUNTER_RE.finditer(rest):
        targets = 2 if ("one or two" in m.group(2) or "up to two" in m.group(2)) else 1
        found.append((m.start(), ("counter", _count(m.group(1)), targets)))
    for m in _PUMP_ALL_RE.finditer(text):
        found.append((m.start(), ("pump_all", int(m.group(1)))))
    for m in _PUMP_RE.finditer(text):
        found.append((m.start(), ("pump", int(m.group(1)))))
    return [a for _pos, a in sorted(found, key=lambda f: f[0])]


def _clean_lines(card):
    """(Rohzeile, kleingeschrieben mit ~ fuer den Namen) der Vorderseite, ohne Erinnerungstext."""
    front = (card.get("card_faces") or [card])[0]
    text = front.get("oracle_text") or card.get("oracle_text") or ""
    name = front.get("name") or card.get("name") or ""
    for raw in text.split("\n"):
        low = re.sub(r"\([^)]*\)", "", raw).strip().lower()
        for nm in (name, name.split(",")[0], name.split(" // ")[0]):
            low = _name_to_tilde(low, nm)
        yield raw, low


def effect_modes(card, type_line):
    """Effekte beim Wirken (Instant/Sorcery) bzw. beim Betreten ("When this ... enters,") je Modus.
    Modale Karten ("Choose one" mit Aufzaehlung): ein Modus je Aufzaehlungspunkt mit modellierten Effekten."""
    spell_face = "Instant" in type_line or "Sorcery" in type_line
    common, bullets, in_etb = [], [], False
    for raw, low in _clean_lines(card):
        bullet = raw.strip().startswith("•")
        body = low.lstrip("•").strip()
        if bullet:
            if spell_face or in_etb:
                atoms = _effect_atoms(body)
                if atoms:
                    bullets.append(atoms)
            continue
        in_etb = False
        if spell_face:
            if re.match(r"^(when|whenever|at the beginning)\b", body):
                continue
            common += _effect_atoms(body)
        else:
            m = _ETB_EFFECT_RE.match(body)
            if m:
                in_etb = True
                common += _effect_atoms(m.group(1))
    if bullets:
        return tuple(tuple(common + b) for b in bullets)
    return (tuple(common),) if common else ()


_SELF_DAMAGE_RE = re.compile(r"(?<![a-z])(?:~|it|this [a-z]+) deals (\d+) damage to each player\b")


def self_damage(card, type_line):
    """Schaden, den eine Karte beim Wirken bzw. Betreten auch uns selbst zufuegt ("deals N damage to each player")."""
    spell_face = "Instant" in type_line or "Sorcery" in type_line
    total = 0
    for _raw, low in _clean_lines(card):
        body = low
        if not spell_face:
            m = _ETB_EFFECT_RE.match(low)
            if not m:
                continue
            body = m.group(1)
        elif re.match(r"^(when|whenever|at the beginning)\b", low):
            continue
        total += sum(int(m.group(1)) for m in _SELF_DAMAGE_RE.finditer(body))
    return total


def board_triggers(card):
    """(Landfall-Effekte, Marken am Rundenende, Marken bei Loyalty, Friedhof-X) der Vorderseite."""
    landfall, endstep, loyalty, gy_x = [], 0, 0, False
    for _raw, low in _clean_lines(card):
        m = _LANDFALL_FACE_RE.match(low)
        if m:
            landfall.append(("face", int(m.group(1))))
            if _LANDFALL_MANA_RE.search(low):
                landfall.append(("mountain_mana", "R"))
        m = _TYPE_COUNTER_RE.match(low)
        if m:
            landfall.append(("type_counter", m.group(1), 1))
        m = _ENDSTEP_RE.match(low)
        if m:
            endstep += _count(m.group(1))
        m = _LOYALTY_COUNTER_RE.match(low)
        if m:
            loyalty += _count(m.group(1))
        if "greatest mana value among cards in your graveyard" in low:
            gy_x = True
    return tuple(landfall), endstep, loyalty, gy_x


def modelled_effect_rest(line, spell_face, name=""):
    """Fuer die Modell-Abdeckung: (gefunden, Resttext) - Saetze mit modellierten Effekten (Schaden an den Gegner,
    Marken, Pumps, Landfall, Rundenende, Loyalty) werden entfernt."""
    low = re.sub(r"\([^)]*\)", "", line).strip().lower().lstrip("•").strip()
    for nm in (name, name.split(",")[0], name.split(" // ")[0]):
        low = _name_to_tilde(low, nm)
    if (_LANDFALL_FACE_RE.match(low) or _TYPE_COUNTER_RE.match(low) or _ENDSTEP_RE.match(low)
            or _LOYALTY_COUNTER_RE.match(low)):
        return True, ""
    prefix, body = "", low
    if not spell_face:
        m = _ETB_EFFECT_RE.match(low)
        if not m:
            return False, low
        prefix, body = low[:m.start(1)], m.group(1)
    elif re.match(r"^(when|whenever|at the beginning)\b", low):
        return False, low
    sentences = re.split(r"(?<=\.)\s+", body)
    kept = [s_ for s_ in sentences if not _effect_atoms(s_)]
    if len(kept) == len(sentences):
        return False, low
    rest = " ".join(kept).strip()
    return True, (prefix + rest) if rest else ""


COMBAT_KEYWORDS = ("flying", "reach", "first strike", "double strike", "deathtouch", "trample", "menace",
                   "lifelink", "vigilance")


def combat_keywords(card):
    """Kampf-Schluesselwoerter, die die Vorderseite selbst als Schluesselwort-Zeile hat (Verleihen zaehlt nicht)."""
    found = set()
    for raw, _low in _clean_lines(card):
        line = re.sub(r"\([^)]*\)", "", raw).strip()
        tokens = [t.strip().lower() for t in line.split(",") if t.strip()]
        if tokens and all(re.fullmatch(r"[a-z ]{2,20}", t) for t in tokens):
            found |= set(tokens) & set(COMBAT_KEYWORDS)
    return tuple(k for k in COMBAT_KEYWORDS if k in found)


def prepared_mode(card):
    """Prepared-Karten (Layout "prepare"): "enters prepared" -> "enters", "... becomes prepared" (im Upkeep) ->
    "upkeep", beides -> "both"; sonst "" (Wortlaut unbekannt, nicht modelliert)."""
    faces = card.get("card_faces") or []
    if card.get("layout") != "prepare" or len(faces) < 2:
        return ""
    low = re.sub(r"\([^)]*\)", " ", faces[0].get("oracle_text") or "").lower()
    enters = bool(re.search(r"\benters prepared\b", low))
    upkeep = bool(re.search(r"\bupkeep\b[^.]*\bbecomes prepared\b", low))
    return "both" if enters and upkeep else "enters" if enters else "upkeep" if upkeep else ""


def prepared_spell(card):
    """Die Zauberhaelfte einer Prepared-Karte als eigene Karte (Kopie, die keine Handkarte verbraucht)."""
    face = (card.get("card_faces") or [{}, {}])[1]
    raw = {"name": face.get("name", ""), "type_line": face.get("type_line", ""), "mana_cost": face.get("mana_cost", ""),
           "oracle_text": face.get("oracle_text", ""), "colors": face.get("colors") or card.get("colors") or [],
           "keywords": [], "layout": "normal"}
    return card_info(raw)[0]._replace(is_copy=True)


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
    mana_src, treasure = parse_mana(card, type_line)
    if mana_src:
        shown += "   [Mana: " + " ".join("{" + "/".join(u) + "}" if len(u) < 5 else "{beliebig}" for u in mana_src) + "]"
    if treasure:
        shown += f"   [Treasure {treasure}]"
    modes = effect_modes(card, type_line)
    landfall, endstep, loyalty, gy_x = board_triggers(card)
    prepared = ()
    mode = prepared_mode(card)
    if mode:
        spell = prepared_spell(card)
        prepared = (mode, spell)
        shown += f"   [Prepared: {spell.name} {faces[1].get('mana_cost', '')}]"
    return Card(False, mv, alts, (), is_creature, is_aura,
                power if is_creature else 0, tough if is_creature else 0, haste,
                name=card["name"], cycle_alts=cycle_alts, cycle_target=cycle_target,
                cycle_mv=cycle_mv, is_instant_sorcery=("Instant" in type_line or "Sorcery" in type_line),
                is_planeswalker="Planeswalker" in type_line, empower=eff, empower_text=etext,
                pw_tags=pw_tags_for(card, type_line), defender=defender,
                is_jace=("Planeswalker" in type_line and "Jace" in type_line.split("—")[-1].split()),
                draws=draws, surveil=surveil, prepared=prepared, mana_src=mana_src, treasure=treasure,
                modes=modes, landfall=landfall, endstep_counters=endstep, loyalty_counter=loyalty, gy_x=gy_x,
                kw=combat_keywords(card) if is_creature else (), self_damage=self_damage(card, type_line),
                is_instant="Instant" in type_line, flash="Instant" not in type_line and has_flash(card),
                removal=removal_spec(card), discard=discard_count(card)), shown
