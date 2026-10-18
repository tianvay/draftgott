"""Kartenmodell: Card und die Auswertung der Scryfall-Daten (Laender, Landcycling, Empower Jace, Planeswalker-Tags)."""
import re
from typing import NamedTuple

from components.mana import cost_alternatives, mana_value
from components.removal import _classify, _spec_from, discard_count, has_flash, removal_info, removal_spec


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
    abilities: tuple = ()      # aktivierbare Faehigkeiten im Kampf (parse_abilities)
    pump_tough: tuple = ()     # je Modus: Toughness der Pumps ("pump"/"pump_all") in ihrer Reihenfolge (+P/+T)
    legendary: bool = False    # Legendary im Typ
    is_artifact: bool = False  # Artifact im Typ
    combat_draw: int = 0       # zieht N Karten, wenn die Kreatur einem Spieler Kampfschaden zufuegt
    end_sacrifice: bool = False  # wird zu Beginn des Endsegments geopfert
    ally_enter_life: int = 0   # Leben, wenn eine andere eigene Kreatur ins Spiel kommt
    enter_counter: int = 0     # Marken auf eine Kreatur, die in diesem Zug kam, wenn sie oder eine andere kommt (Mabel)
    artifact_pump: tuple = ()  # beim Betreten: eigene Kreaturen +X/+0 (X = Artefakte) und diese Schluesselwoerter
    spell_discount: int = 0    # Nichtkreatur-Zauber kosten {N} weniger
    target_cast_counter: int = 0  # Marken auf sich, wenn man einen Zauber mit Ziel beim Gegner wirkt (Danitha)
    targets_opp: bool = False  # Zauber mit Ziel beim Gegner (Spieler oder seine Kreatur)
    hand_removal: tuple = ()   # "Kosten, Discard this card: Removal" - (Zahlungswege, Removal-Spec)
    gy_ability: tuple = ()     # "Kosten, Exile this card from your graveyard: Effekt" - (Zahlungswege, Effekte)
    surveil_attack: bool = False  # Defender gilt nicht, wenn man in diesem Zug gesurveilt hat
    is_token: bool = False     # Token (kommt nicht in den Friedhof)
    sac_mana: bool = False     # "{T}, Sacrifice this token: Add one mana of any color" (Sculpture: wie Treasure)
    land_to_tokens: tuple = ()  # beim Betreten Land opfern, dafuer Token: (Anzahl, Token-Card) (Tenured Tethermage)
    tap_artifacts: tuple = ()  # "Tap N untapped artifacts you control: Effekt" - (N, Effekte)
    cast_token: object = None  # bei jedem Nichtkreatur-Zauber ein Token (Card) (Vraska)
    artifact_vigilance: bool = False  # eigene Artefaktkreaturen haben Vigilance
    mill_land: int = 0         # beim Betreten Mill N, dann ein Land aus dem Friedhof getappt ins Spiel
    confidant: bool = False    # Endsegment: nach Lebensgewinn Surveil 1, abgelegte Karte mit MW <= Gewinn auf die Hand
    null_summoner: bool = False  # beim Wirken: Nichtland-Karte aus der Hand des Gegners exilen, ab Threshold wirken
    creature_types: tuple = ()  # Kreaturtypen (klein geschrieben, z. B. ("angel", "knight"))
    creates_tokens: tuple = ()  # Kreatur-Token beim Wirken bzw. Betreten: ((Anzahl, Token-Card), ...)
    lifegain_counter: tuple = ()  # bei jedem Lebensgewinn Marken auf jede eigene Kreatur eines Typs: (n, Typ) (Lyra)
    opp_spell_tax: int = 0     # Nichtkreatur-Zauber der Gegner kosten {N} mehr (Thalia, the Survivor)
    landfall_life: int = 0     # Landfall: N Leben (Koth of the Homestead)
    attack_ping: int = 0       # jede eigene angreifende Kreatur macht N Schaden an jedem Gegner (Ingris Stingerquill)
    etb_life: int = 0          # N Leben beim Betreten
    death_life: int = 0        # N Leben, wenn die Kreatur stirbt
    spell_life: int = 0        # N Leben beim Wirken (Instant/Sorcery)
    extra_cost: int = 0        # Zusatzkosten {N} ("sacrifice ... or pay {N}": wir zahlen immer)
    prowess: bool = False      # +1/+1 bis Rundenende bei jedem eigenen Nichtkreatur-Zauber
    edict_cost: bool = False   # Edikt nur, wenn wir selbst eine Kreatur opfern (Winter, Tormented Loner)
    gy_power: tuple = ()       # +1/+0 je Karte dieser Typen im eigenen Friedhof, z. B. ("creature", "planeswalker")
    hexproof_until_damage: bool = False  # Hexproof, solange die Kreatur keinen Kampfschaden zugefuegt hat (Ruric Thar)
    flashback: tuple = ()      # Flashback-Kosten (Mana) als Zahlungswege
    flashback_discard: bool = False  # Flashback verlangt zusaetzlich, eine Karte abzuwerfen (Twinned Vision)
    alt_draws: int = 0         # zieht so viele statt draws, wenn nicht aus der Hand gewirkt
    reanimate: tuple = ()      # Zauber holt aus dem Friedhof: (target/all, creature/permanent/land, max. MW, Ziel, Marken)
    gy_return: tuple = ()      # "Kosten: Return this card from your graveyard to ...": (Zahlungswege, Ziel, getappt,
    #                            Marken, Zusatzkosten "exile_creature", Bedingung "noncombat")
    finality: bool = False     # kommt mit Finality-Marke zurueck: stirbt sie, wird sie exiliert
    phoenix: bool = False      # zu Beginn des eigenen Kampfs zurueck, wenn in diesem Zug 2+ Kreaturen starben
    combat_land_return: bool = False  # Kampfschaden am Spieler: Land aus dem Friedhof auf die Hand
    domain_power: bool = False  # Power = Zahl der Basic-Land-Typen unter den eigenen Laendern (Fblthp)
    x_search_basics: bool = False  # beim Betreten bis zu X Basic Lands mit verschiedenen Namen auf die Hand (Fblthp)
    ally_death_ping: tuple = ()  # stirbt eine andere eigene Kreatur: (Schaden am Gegner, Leben) (Massacre Girl)
    noncombat_counter: int = 0   # Marken, wenn ein Gegner Schaden ausserhalb des Kampfs bekommt (Massacre Girl)
    choices: tuple = ()        # modale Karte ("Choose one/two —"): (Anzahl, (Modus als Card, ...)) - nur im Kampf
    is_mode: bool = False      # diese Card ist ein Modus einer modalen Karte
    grant_kw: tuple = ()       # Zauber: "target creature ... gains <Schluesselwoerter> until end of turn" (Kampftrick)
    removal_exile: bool = False  # Removal: stirbt das Ziel in diesem Zug, wird es exiliert (Essence Burn)
    removal_points: float = 0.0  # Removal-Score der Karte (removal.removal_info), z. B. fuer die Auswahl beim Abwerfen
    hand_pick: str = ""        # wir waehlen eine Karte aus der Hand des Gegners, er wirft sie ab: "permanent"/"nonland"
    cast_counter: int = 0      # Nichtkreatur-Zauber: +1/+1-Marken auf sich (Chandra's Emberling)
    cast_team_pump: int = 0    # Nichtkreatur-Zauber: eigene Kreaturen +N/+0 bis Rundenende (Winter, Team Player)
    type_haste: str = ""       # eigene Kreaturen dieses Typs haben Haste (Saheeli: "thopter")
    lifegain_draw: int = 0     # Lebensgewinn: N Karten ziehen, einmal pro Zug (Bloombrute)
    lifegain_loyalty: int = 0  # Lebensgewinn: Loyalty auf jeden eigenen Planeswalker (Way of the Mentor)
    attack_drain: tuple = ()   # greift sie an: (Schaden an jedem Gegner, Leben) (Screeching Soulbreaker)
    attack_exile_gy: bool = False  # greift sie an: bis zu eine Karte aus einem Friedhof exilen (Afterthought Sentry)
    own_turn_kw: tuple = ()    # Schluesselwoerter nur im eigenen Zug (Skilled Battlecarver)
    threshold_bonus: int = 0   # +N/+N ab 7 Karten im eigenen Friedhof (Void Extrapolator)
    noncombat_kw: tuple = ()   # Schluesselwoerter, solange ein Gegner in diesem Zug Schaden ausserhalb des Kampfs bekam
    counter_vigilance: bool = False  # eigene Kreaturen mit +1/+1-Marke haben Vigilance (Vigorbloom Vanguard)
    enters_counters: int = 0   # kommt mit N +1/+1-Marken ins Spiel (Graft Surgeon)
    death_counters_move: bool = False  # stirbt sie, gehen ihre Marken auf eine eigene Kreatur (Graft Surgeon)
    targeted_draw: int = 0     # wird sie Ziel eines gegnerischen Zaubers: N Karten ziehen (Ruric Thar, Biomagus)
    self_discount: tuple = ()  # eigene Kostensenkung: ("legendary", n), ("noncreature", n), ("power",), ("toughness",)
    team_kw: tuple = ()        # andere eigene Kreaturen haben diese Schluesselwoerter (Ghalta the Unstoppable)
    defender_attack: bool = False  # eigene Kreaturen greifen trotz Defender an (Ghalta the Immovable)


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
_LANDFALL_LIFE_RE = re.compile(r"^(?:landfall — )?whenever a land you control enters, you gain (a|one|two|three|\d+) "
                               r"life")
_TYPE_COUNTER_RE = re.compile(r"^whenever an? (plains|island|swamp|mountain|forest) you control enters, put a \+1/\+1 "
                              r"counter on target creature\.$")
_ENDSTEP_RE = re.compile(r"^at the beginning of your end step, if you didn't cast a spell this turn, put "
                         r"(a|an|one|two|three|\d+) \+1/\+1 counters? on (?:~|this creature)\.$")
_LOYALTY_COUNTER_RE = re.compile(r"^whenever you put one or more loyalty counters on a planeswalker, put "
                                 r"(a|an|one|two|\d+) \+1/\+1 counters? on (?:~|this creature)\.$")


def _count(word):
    return _EFFECT_NUM.get(word) or int(word)


def _effect_atoms(text, full=False):
    """Modellierte Effekte in einem Text (Reihenfolge wie im Text). full: Pumps mit Toughness ("pump", P, T)."""
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
        found.append((m.start(), ("pump_all", int(m.group(1))) + ((int(m.group(2)),) if full else ())))
    for m in _PUMP_RE.finditer(text):
        found.append((m.start(), ("pump", int(m.group(1))) + ((int(m.group(2)),) if full else ())))
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


def pump_toughness(card, type_line):
    """Toughness der Pumps je Modus (gleiche Reihenfolge wie effect_modes), () ohne Pumps."""
    out = tuple(tuple(a[2] for a in m if a[0] in ("pump", "pump_all")) for m in effect_modes(card, type_line, True))
    return out if any(out) else ()


def effect_modes(card, type_line, full=False):
    """Effekte beim Wirken (Instant/Sorcery) bzw. beim Betreten ("When this ... enters,") je Modus.
    Modale Karten ("Choose one" mit Aufzaehlung): ein Modus je Aufzaehlungspunkt mit modellierten Effekten."""
    spell_face = "Instant" in type_line or "Sorcery" in type_line
    common, bullets, in_etb = [], [], False
    for raw, low in _clean_lines(card):
        bullet = raw.strip().startswith("•")
        body = low.lstrip("•").strip()
        if bullet:
            if spell_face or in_etb:
                atoms = _effect_atoms(body, full)
                if atoms:
                    bullets.append(atoms)
            continue
        in_etb = False
        if spell_face:
            if re.match(r"^(when|whenever|at the beginning)\b", body):
                continue
            common += _effect_atoms(body, full)
        else:
            m = _ETB_EFFECT_RE.match(body)
            if m:
                in_etb = True
                common += _effect_atoms(m.group(1), full)
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
                   "lifelink", "vigilance", "hexproof")


def combat_keywords(card):
    """Kampf-Schluesselwoerter, die die Vorderseite selbst als Schluesselwort-Zeile hat (Verleihen zaehlt nicht)."""
    found = set()
    for raw, _low in _clean_lines(card):
        line = re.sub(r"\([^)]*\)", "", raw).strip()
        tokens = [t.strip().lower() for t in line.split(",") if t.strip()]
        if tokens and all(re.fullmatch(r"[a-z ]{2,20}", t) for t in tokens):
            found |= set(tokens) & set(COMBAT_KEYWORDS)
    return tuple(k for k in COMBAT_KEYWORDS if k in found)


_ABILITY_RE = re.compile(r"^((?:\{[^}]+\}|,|\s)+):\s*(.+)$")
_SELF = r"(?:~|this creature|it)"
_ABILITY_SUBJECTS = ((re.compile(rf"^{_SELF} "), "self"),
                     (re.compile(r"^target creature(?: you control)? "), "target"),
                     (re.compile(r"^creatures you control "), "all"))
_ABILITY_PUMP_RE = re.compile(r"^(?:gets? \+(\d+)/\+(\d+))?(?:,? and )?(?:gains? ([a-z ,]+?))? until end of turn\.?$")
_ABILITY_COUNTER_RE = re.compile(r"^put (a|an|one|two|three|\d+) \+1/\+1 counters? on (~|this creature|target creature"
                                 r"(?: you control)?|target nonlegendary creature|each creature you control with a "
                                 r"\+1/\+1 counter on it)\.?$")
_ABILITY_COUNTER_SCOPE = {"~": "self", "this creature": "self", "target creature": "target",
                          "target creature you control": "target", "target nonlegendary creature": "nonlegendary"}
_ABILITY_EMPOWER_RE = re.compile(r"^empower jace (\d+)\.?$")
_ABILITY_SURVEIL_RE = re.compile(r"^surveil (\d+)\.?$")
_ABILITY_RETURN_RE = re.compile(r"^return (another )?target (creature|land|permanent) card from your graveyard to your "
                                r"hand\.?$")


def _ability_atoms(body):
    """Effekte einer aktivierbaren Faehigkeit: ("pump", +P, +T, Ziel), ("grant", Schluesselwoerter, Ziel),
    ("counter", n, Ziel), ("empower", n). Ziel: self / target / all / nonlegendary / countered. None, wenn der Text
    nicht vollstaendig modelliert ist."""
    m = _ABILITY_EMPOWER_RE.match(body)
    if m:
        return (("empower", int(m.group(1))),)
    m = _ABILITY_SURVEIL_RE.match(body)
    if m:
        return (("surveil", int(m.group(1))),)
    m = _ABILITY_RETURN_RE.match(body)
    if m:
        return (("return", m.group(2), "hand", bool(m.group(1))),)
    if body.startswith("create "):
        first, _, rest = body.partition(". ")
        tokens = _tokens_in(first if first.endswith(".") else first + ".")
        if len(tokens) != 1:
            return None
        atoms = [("token",) + tokens[0]]
        rest = rest.strip()
        if rest == "then creatures you control gain haste until end of turn.":
            atoms.append(("grant", ("haste",), "all"))
        elif rest:
            return None
        return tuple(atoms)
    m = _ABILITY_COUNTER_RE.match(body)
    if m:
        scope = _ABILITY_COUNTER_SCOPE.get(m.group(2), "countered")
        return (("counter", _count(m.group(1)), scope),)
    for subj, scope in _ABILITY_SUBJECTS:
        sm = subj.match(body)
        if not sm:
            continue
        m = _ABILITY_PUMP_RE.match(body[sm.end():])
        if not m or not (m.group(1) or m.group(3)):
            return None
        atoms = []
        if m.group(1):
            atoms.append(("pump", int(m.group(1)), int(m.group(2)), scope))
        if m.group(3):
            kws = tuple(k.strip() for k in re.split(r",\s*(?:and\s+)?|\s+and\s+", m.group(3)) if k.strip())
            if not all(k in COMBAT_KEYWORDS for k in kws):
                return None
            atoms.append(("grant", kws, scope))
        return tuple(atoms)
    return None


def parse_abilities(card):
    """Aktivierbare Faehigkeiten der Vorderseite, deren Kosten nur aus Mana und {T} bestehen:
    ((Zahlungswege, Manawert, Tap, Tempo, Effekte), ...). Tempo: instant / sorcery ("Activate only as a sorcery") /
    own_turn ("Activate only during your turn"). Mana-Faehigkeiten zaehlen nicht dazu."""
    out = []
    for raw, low in _clean_lines(card):
        m = _ABILITY_RE.match(low)
        if not m or "add {" in low:
            continue
        head = raw.split(":", 1)[0]
        tap = "{t}" in m.group(1)
        mana = "".join(re.findall(r"\{[^}]+\}", head.replace("{T}", "")))
        body = m.group(2).strip()
        speed = "instant"
        if "activate only as a sorcery" in body:
            speed = "sorcery"
        elif "activate only during your turn" in body:
            speed = "own_turn"
        body = re.sub(r"\s*activate only[^.]*\.", "", body).strip()
        atoms = _ability_atoms(body)
        if atoms:
            out.append((cost_alternatives(mana) if mana else ((0, ()),), mana_value(mana) if mana else 0, tap, speed,
                        atoms))
    return tuple(out)


_SUBJ = r"(?:~|this creature)"
_COMBAT_DRAW_RE = re.compile(rf"^whenever {_SUBJ} deals combat damage to a player, draw (a|an|one|two|three|\d+) cards?")
_END_SAC_RE = re.compile(rf"^at the beginning of (?:the|your) end step, sacrifice {_SUBJ}\.?$")
_ALLY_LIFE_RE = re.compile(r"^whenever another creature you control enters, you gain (a|one|two|three|\d+) life")
_ENTER_COUNTER_RE = re.compile(r"^whenever (?:~|this creature) or another creature you control enters, put "
                               r"(a|an|one|two|three|\d+) \+1/\+1 counters? on target creature that entered this turn")
_ARTIFACT_PUMP_RE = re.compile(rf"^when {_SUBJ} enters, creatures you control gain ([a-z ,]+?) and get \+x/\+0 until "
                               r"end of turn, where x is the number of artifacts you control")
_DISCOUNT_RE = re.compile(r"^noncreature spells you cast cost \{(\d+)\} less to cast")
_TARGET_CAST_RE = re.compile(r"^whenever you cast a spell that targets [^,]*opponent[^,]*, put (a|an|one|two|\d+) "
                             r"\+1/\+1 counters? on ~")
_SURVEIL_ATTACK_RE = re.compile(r"^as long as you've (?:scried or )?surveilled this turn, " + _SUBJ +
                                r" can attack as though it didn't have defender")
_HAND_REMOVAL_RE = re.compile(r"^((?:\{[^}]+\})+),\s*discard (?:~|this card):\s*(.+)$")
_GY_ABILITY_RE = re.compile(r"^((?:\{[^}]+\})+),\s*exile (?:~|this card) from your graveyard:\s*(.+)$")


_LAND_TOKENS_RE = re.compile(r"you may sacrifice a land\. if you do, create (a|an|one|two|three) tapped ([a-z]+) "
                             r"tokens?\. \(they're [a-z ]+ artifacts? with \"\{t\}: add ((?:\{[wubrg]\}(?: or )?)+)\.\"\)")
_TAP_ARTIFACTS_RE = re.compile(r"^tap (a|an|one|two|three|\d+) untapped artifacts you control:\s*(.+)$")
_CAST_TOKEN_RE = re.compile(r"^whenever you cast a noncreature spell, create an? (\d+)/(\d+) colorless ([a-z]+) "
                            r"(treasure )?artifact creature token")
_ARTIFACT_VIGILANCE_RE = re.compile(r"^artifact creatures you control have vigilance")
_MILL_LAND_RE = re.compile(r"^when (?:~|this creature) enters, mill (a|one|two|three|four|\d+) cards?\. when you do, "
                           r"return target land card from your graveyard to the battlefield tapped")
_CONFIDANT_RE = re.compile(r"^at the beginning of your end step, if you gained life this turn, surveil 1\. if you put "
                           r"a card with mana value less than or equal to the amount of life you gained this turn into "
                           r"your graveyard this way, put that card into your hand")
_LIFEGAIN_COUNTER_RE = re.compile(r"^whenever you gain life, put (a|an|one|two|\d+) \+1/\+1 counters? on each ([a-z]+) "
                                  r"you control")
_OPP_TAX_RE = re.compile(r"^noncreature spells your opponents cast cost \{(\d+)\} more to cast")
_NULL_SUMMONER_RE = re.compile(r"^when (?:~|this creature) enters, if you cast it, target opponent reveals their hand\. "
                               r"you choose a nonland card from it\. exile that card")


def token_card(name, creature=False, power=0, toughness=0, artifact=True, mana_src=(), sac_mana=False, kw=(), types=()):
    return Card(False, 0, (), (), creature, False, power, toughness, name=name, is_artifact=artifact, is_token=True,
                mana_src=mana_src, sac_mana=sac_mana, kw=kw, creature_types=types)


_COLOR_WORDS = r"(?:colorless|white|blue|black|red|green)(?: and (?:white|blue|black|red|green))?"
_CREATE_TOKEN_RE = re.compile(r"\bcreate (a|an|one|two|three) (\d+)/(\d+) (?:" + _COLOR_WORDS + r" )?([a-z ]+?) "
                              r"creature tokens?(?: named ([a-z]+))?(?: with ([a-z ,]+?))?\.")


def _tokens_in(text):
    """Kreatur-Token in einem Text: [(Anzahl, Token-Card)]."""
    out = []
    for m in _CREATE_TOKEN_RE.finditer(text):
        types = m.group(4).split()
        artifact = "artifact" in types
        types = tuple(t for t in types if t != "artifact")
        kws = tuple(k.strip() for k in re.split(r",\s*(?:and\s+)?|\s+and\s+", m.group(6) or "")
                    if k.strip() in COMBAT_KEYWORDS)
        name = m.group(5).capitalize() if m.group(5) else " ".join(t.capitalize() for t in types)
        token = token_card(name, True, int(m.group(2)), int(m.group(3)), artifact, kw=kws, types=types)
        if "it gains haste" in text[m.end():m.end() + 40]:
            token = token._replace(haste=True)
        out.append((_count(m.group(1)), token))
    return out


def creates_tokens(card, type_line):
    """Kreatur-Token beim Wirken (Instant/Sorcery) bzw. beim Betreten ("When this ... enters, create ...")."""
    spell_face = "Instant" in type_line or "Sorcery" in type_line
    out = []
    for _raw, low in _clean_lines(card):
        if spell_face:
            if not re.match(r"^(when|whenever|at the beginning)\b", low):
                out += _tokens_in(low)
        else:
            m = _ETB_EFFECT_RE.match(low)
            if m:
                out += _tokens_in(m.group(1))
    return tuple(out)


def token_triggers(card):
    """Token, Mill, Enlightened Confidant und Null Summoner (Stufe 4b, Paket C) als dict mit den Card-Feldern."""
    out = {}
    for raw, low in _clean_lines(card):
        m = _LAND_TOKENS_RE.search(raw.lower())
        if m:
            colors = tuple(sorted(c.upper() for c in re.findall(r"\{([wubrg])\}", m.group(3))))
            out["land_to_tokens"] = (_count(m.group(1)), token_card(m.group(2).capitalize(), mana_src=(colors,)))
        m = _TAP_ARTIFACTS_RE.match(low)
        if m:
            atoms = _ability_atoms(m.group(2).strip())
            if atoms:
                out["tap_artifacts"] = (_count(m.group(1)), atoms)
        m = _CAST_TOKEN_RE.match(low)
        if m:
            out["cast_token"] = token_card(m.group(3).capitalize(), True, int(m.group(1)), int(m.group(2)),
                                           sac_mana=bool(m.group(4)) and "sacrifice this token: add one mana" in low,
                                           types=(m.group(3),),
                                           kw=("flying",) if "creature token with flying" in low else ())
        if _ARTIFACT_VIGILANCE_RE.match(low):
            out["artifact_vigilance"] = True
        m = _MILL_LAND_RE.match(low)
        if m:
            out["mill_land"] = _count(m.group(1))
        if _CONFIDANT_RE.match(low):
            out["confidant"] = True
        if _NULL_SUMMONER_RE.match(low):
            out["null_summoner"] = True
        m = _LANDFALL_LIFE_RE.match(low)
        if m:
            out["landfall_life"] = _EFFECT_NUM.get(m.group(1)) or int(m.group(1))
        m = _LIFEGAIN_COUNTER_RE.match(low)
        if m:
            out["lifegain_counter"] = (_count(m.group(1)), m.group(2))
        m = _OPP_TAX_RE.match(low)
        if m:
            out["opp_spell_tax"] = int(m.group(1))
    return out


def battle_triggers(card):
    """Weitere Ausloeser und Faehigkeiten fuer den Kampf (Stufe 4b), als dict mit den Card-Feldern."""
    out = {}
    for raw, low in _clean_lines(card):
        m = _COMBAT_DRAW_RE.match(low)
        if m:
            out["combat_draw"] = _count(m.group(1))
        if _END_SAC_RE.match(low):
            out["end_sacrifice"] = True
        m = _ALLY_LIFE_RE.match(low)
        if m:
            out["ally_enter_life"] = _EFFECT_NUM.get(m.group(1)) or int(m.group(1))
        m = _ENTER_COUNTER_RE.match(low)
        if m:
            out["enter_counter"] = _count(m.group(1))
        m = _ARTIFACT_PUMP_RE.match(low)
        if m:
            kws = tuple(k.strip() for k in re.split(r",\s*(?:and\s+)?|\s+and\s+", m.group(1)) if k.strip())
            if all(k in COMBAT_KEYWORDS for k in kws):
                out["artifact_pump"] = kws
        m = _DISCOUNT_RE.match(low)
        if m:
            out["spell_discount"] = int(m.group(1))
        m = _TARGET_CAST_RE.match(low)
        if m:
            out["target_cast_counter"] = _count(m.group(1))
        if _SURVEIL_ATTACK_RE.match(low):
            out["surveil_attack"] = True
        head = raw.split(":", 1)[0]
        mana = "".join(re.findall(r"\{[^}]+\}", head))
        m = _HAND_REMOVAL_RE.match(low)
        if m:
            res = _classify(m.group(2))
            spec = _spec_from(m.group(2), res[1]) if res else None
            if spec:
                out["hand_removal"] = (cost_alternatives(mana), spec + ("spell", False))
        m = _GY_ABILITY_RE.match(low)
        if m:
            atoms = _ability_atoms(m.group(2).strip())
            if atoms:
                out["gy_ability"] = (cost_alternatives(mana), atoms)
    return out


_ATTACK_PING_RE = re.compile(r"^whenever a creature you control attacks, that creature deals (\d+) damage to each "
                             r"opponent")
_ETB_DEATH_LIFE_RE = re.compile(r"^when (?:~|this creature) (enters or dies|enters|dies), you gain (a|one|two|three|\d+) "
                                r"life\.?$")
_SPELL_LIFE_RE = re.compile(r"\byou gain (a|one|two|three|\d+) life\b")
_EDICT_COST_RE = re.compile(r"^when (?:~|this creature) enters, you may sacrifice an? (?:creature|creature or "
                            r"planeswalker)\. when you do, each opponent sacrifices")
_GY_POWER_RE = re.compile(r"^(?:~|this creature) gets \+1/\+0 for each ((?:creature|planeswalker|artifact|land|instant|"
                          r"sorcery)(?: and (?:creature|planeswalker|artifact|land|instant|sorcery))*) cards? in your "
                          r"graveyard")
_HEXPROOF_UNTIL_RE = re.compile(r"^(?:~|this creature) has hexproof as long as (?:it|they) (?:hasn't|haven't) dealt "
                                r"combat damage yet")
_FLASHBACK_RE = re.compile(r"^flashback(?: |—)((?:\{[^}]+\})+)(, discard a card)?\.?$")
_ALT_DRAWS_RE = re.compile(r"if this spell wasn't cast from your hand, draw (a|one|two|three) cards? instead")
_REANIMATE_RE = re.compile(r"\breturn (target|all) (creature|permanent|land) cards?(?: with mana value (\d+) or less)? "
                           r"from your graveyard to (the battlefield|your hand)( tapped)?( with an additional \+1/\+1 "
                           r"counter on (?:it|them))?")
_GY_RETURN_RE = re.compile(r"^((?:\{[^}]+\})+)(, exile another creature card from your graveyard)?: return this card "
                           r"from your graveyard to (the battlefield|your hand)( tapped)?(?: with (?:a|an) "
                           r"(\+1/\+1|finality) counter on (?:it|her|him|them))?\.( activate only if an opponent has "
                           r"been dealt noncombat damage this turn\.)?$")
_PHOENIX_RE = re.compile(r"^at the beginning of combat on your turn, if two or more creatures died this turn, return "
                         r"this card from your graveyard to the battlefield")
_DOMAIN_POWER_RE = re.compile(r"^domain — (?:~|this creature)'s power is equal to the number of basic land types among "
                              r"lands you control")
_X_SEARCH_RE = re.compile(r"^when (?:~|this creature) enters, search your library for up to x basic land cards with "
                          r"different names, reveal them, put them into your hand")
_ALLY_DEATH_RE = re.compile(r"^whenever another creature(?: or planeswalker)? you control dies, (?:~|this creature) deals "
                            r"(\d+) damage to target opponent and you gain (\d+) life")
_NONCOMBAT_COUNTER_RE = re.compile(r"^whenever an opponent is dealt noncombat damage, put (a|an|one|two|\d+) \+1/\+1 "
                                   r"counters? on (?:~|this creature)")
_COMBAT_LAND_RE = re.compile(r"^whenever (?:~|this creature) deals combat damage to a player, return target land card "
                             r"from your graveyard to your hand")
_EXTRA_COST_RE = re.compile(r"^as an additional cost to cast this spell, [^.]*\bpay \{(\d+)\}")


_GRANT_KW_RE = re.compile(r"\btarget creature(?: you control)? (?:gets [^.]*? and )?gains ([a-z ,]+?) until end of turn")
_CHOOSE_RE = re.compile(r"^(?:when (?:~|this creature) enters, )?choose (one|two|three) —$")
_YOU_DRAW_LIFE_RE = re.compile(r"^you draw (a|an|one|two|three) cards? and gain (\d+) life\.", re.I)


def grant_keywords(card, type_line):
    """Zauber, die einer Kreatur Kampf-Schluesselwoerter bis Rundenende geben (fuer Kampftricks im Kampf)."""
    if not ("Instant" in type_line or "Sorcery" in type_line):
        return ()
    found = []
    for _raw, low in _clean_lines(card):
        if re.match(r"^(when|whenever|at the beginning)\b", low):
            continue
        for m in _GRANT_KW_RE.finditer(low):
            for k in re.split(r",\s*(?:and\s+)?|\s+and\s+", m.group(1)):
                if k.strip() in COMBAT_KEYWORDS and k.strip() not in found:
                    found.append(k.strip())
    return tuple(found)


def modal_choices(card, type_line):
    """Modale Karten: jeder Aufzaehlungspunkt nach "Choose one/two —" (auch "When this creature enters, choose two —")
    wird eine eigene Card mit genau diesem Text, gelesen mit denselben Bausteinen."""
    front = (card.get("card_faces") or [card])[0]
    lines = (front.get("oracle_text") or card.get("oracle_text") or "").split("\n")
    name = front.get("name") or card.get("name") or ""
    for i, raw in enumerate(lines):
        low = re.sub(r"\([^)]*\)", "", raw).strip().lower()
        for nm in (name, name.split(",")[0]):
            low = _name_to_tilde(low, nm)
        m = _CHOOSE_RE.match(low)
        if not m:
            continue
        etb = low.startswith("when ")
        subs = []
        for bullet in lines[i + 1:]:
            if not bullet.strip().startswith("•"):
                break
            text = bullet.strip().lstrip("•").strip()
            text = _YOU_DRAW_LIFE_RE.sub(lambda mm: f"Draw {mm.group(1)} card{'s' if mm.group(1) not in ('a', 'an', 'one') else ''}. "
                                         f"You gain {mm.group(2)} life.", text)
            if etb:
                text = "When this creature enters, " + text[0].lower() + text[1:]
            raw_sub = {"name": card["name"], "type_line": front.get("type_line") or card.get("type_line", ""),
                       "mana_cost": front.get("mana_cost") or card.get("mana_cost", ""), "cmc": card.get("cmc", 0),
                       "colors": card.get("colors", []), "oracle_text": text, "keywords": [], "layout": "normal",
                       "power": front.get("power") or card.get("power"),
                       "toughness": front.get("toughness") or card.get("toughness")}
            subs.append(card_info(raw_sub)[0]._replace(is_mode=True))
        if subs:
            return (_count(m.group(1)), tuple(subs))
    return ()


def life_and_costs(card, type_line, keywords):
    """Ingris-Schaden beim Angriff, Leben beim Betreten/Sterben/Wirken, Zusatzkosten und Prowess."""
    spell_face = "Instant" in type_line or "Sorcery" in type_line
    out = {}
    if "Prowess" in keywords:  # "Prowess, prowess" loest zweimal aus (702.108b)
        out["prowess"] = max([1] + [low.count("prowess") for _raw, low in _clean_lines(card)
                                    if re.fullmatch(r"prowess(?:, prowess)*", low)])
    for _raw, low in _clean_lines(card):
        m = _ATTACK_PING_RE.match(low)
        if m:
            out["attack_ping"] = int(m.group(1))
        m = _ETB_DEATH_LIFE_RE.match(low)
        if m:
            n = _EFFECT_NUM.get(m.group(2)) or int(m.group(2))
            if "enters" in m.group(1):
                out["etb_life"] = n
            if "dies" in m.group(1):
                out["death_life"] = n
        if spell_face and not re.match(r"^(when|whenever|at the beginning)\b", low):
            gain = sum(_EFFECT_NUM.get(m.group(1)) or int(m.group(1)) for m in _SPELL_LIFE_RE.finditer(low))
            if gain:
                out["spell_life"] = out.get("spell_life", 0) + gain
        m = _EXTRA_COST_RE.match(low)
        if m:
            out["extra_cost"] = int(m.group(1))
        if _EDICT_COST_RE.match(low):
            out["edict_cost"] = True
        if _HEXPROOF_UNTIL_RE.match(low):
            out["hexproof_until_damage"] = True
        m = _FLASHBACK_RE.match(low)
        if m and spell_face:
            out["flashback"] = cost_alternatives(m.group(1).upper())
            if m.group(2):
                out["flashback_discard"] = True
        m = _ALT_DRAWS_RE.search(low)
        if m:
            out["alt_draws"] = _count(m.group(1))
        if ((spell_face and not re.match(r"^(when|whenever|at the beginning)\b", low)) or
                (not spell_face and _ETB_EFFECT_RE.match(low))) and not _MILL_LAND_RE.match(low):
            m = _REANIMATE_RE.search(low)  # Primal Witchstalker (Mill + Land) ist eigene Logik
            if m:
                out["reanimate"] = (m.group(1), m.group(2), int(m.group(3)) if m.group(3) else 99,
                                    "battlefield" if m.group(4) == "the battlefield" else "hand",
                                    1 if m.group(6) else 0)
        m = _GY_RETURN_RE.match(low)
        if m:
            head = _raw.split(":", 1)[0]
            mana = "".join(re.findall(r"\{[^}]+\}", head))
            out["gy_return"] = (cost_alternatives(mana), "battlefield" if m.group(3) == "the battlefield" else "hand",
                                bool(m.group(4)), 1 if m.group(5) == "+1/+1" else 0,
                                "exile_creature" if m.group(2) else "", "noncombat" if m.group(6) else "")
            if m.group(5) == "finality":
                out["finality"] = True
        if _PHOENIX_RE.match(low):
            out["phoenix"] = True
        if _COMBAT_LAND_RE.match(low):
            out["combat_land_return"] = True
        if _DOMAIN_POWER_RE.match(low):
            out["domain_power"] = True
        if _X_SEARCH_RE.match(low):
            out["x_search_basics"] = True
        m = _ALLY_DEATH_RE.match(low)
        if m:
            out["ally_death_ping"] = (int(m.group(1)), int(m.group(2)))
        m = _NONCOMBAT_COUNTER_RE.match(low)
        if m:
            out["noncombat_counter"] = _count(m.group(1))
        m = _GY_POWER_RE.match(low)
        if m:
            out["gy_power"] = tuple(m.group(1).split(" and "))
    return out


_KW_LIST = r"([a-z ,]+?)\.?$"
_PACKAGE_S_RES = {
    "cast_counter": re.compile(r"^whenever you cast a noncreature spell, put (a|an|one|two|\d+) \+1/\+1 counters? on "
                               r"(?:~|this creature)"),
    "cast_team_pump": re.compile(r"^whenever you cast a noncreature spell, creatures you control get \+(\d+)/\+0 until "
                                 r"end of turn"),
    "type_haste": re.compile(r"^([a-z]+?)s you control have haste\.?$"),
    "lifegain_self": re.compile(r"^whenever you gain life, put (a|an|one|two|\d+) \+1/\+1 counters? on "
                                r"(?:~|this creature)"),
    "lifegain_draw": re.compile(r"^whenever you gain life, draw (a|one|two) cards?\. this ability triggers only once "
                                r"each turn"),
    "lifegain_loyalty": re.compile(r"^whenever you gain life, put (a|one|two) loyalty counters? on each planeswalker you "
                                   r"control"),
    "attack_drain": re.compile(r"^whenever (?:~|this creature) attacks, (?:it|~|this creature) deals (\d+) damage to "
                               r"each opponent and you gain (\d+) life"),
    "attack_exile_gy": re.compile(r"^whenever (?:~|this creature) attacks, exile up to one target card from a "
                                  r"graveyard"),
    "own_turn_kw": re.compile(r"^during your turn, (?:~|this creature) has " + _KW_LIST),
    "threshold_bonus": re.compile(r"^threshold — (?:~|this creature) gets \+(\d+)/\+\d+ as long as there are seven or "
                                  r"more cards in your graveyard"),
    "noncombat_kw": re.compile(r"^as long as an opponent was dealt noncombat damage this turn, (?:~|this creature) has "
                               + _KW_LIST),
    "counter_vigilance": re.compile(r"^each creature you control with a \+1/\+1 counter on it has vigilance"),
    "enters_counters": re.compile(r"^(?:~|this creature) enters with (a|an|one|two|three|\d+) \+1/\+1 counters? on "
                                  r"it"),
    "death_counters_move": re.compile(r"^when (?:~|this creature) dies, put its counters on (?:up to one )?target "
                                      r"creature you control"),
    "targeted_draw": re.compile(r"^whenever (?:~|this creature) becomes the target of a spell or ability an opponent "
                                r"controls, draw (a|one|two) cards?"),
    "discount_fixed": re.compile(r"^this spell costs \{(\d+)\} less to cast if you( control a legendary creature|"
                                 r"'ve cast a noncreature spell this turn)"),
    "discount_x": re.compile(r"^this spell costs \{x\} less to cast, where x is the greatest (power|toughness) among "
                             r"creatures you control"),
    "team_kw": re.compile(r"^other creatures you control have " + _KW_LIST),
    "defender_attack": re.compile(r"^creatures you control can attack as though they didn't have defender"),
    "hand_pick": re.compile(r"\btarget opponent reveals their hand\. you choose an? (nonland permanent|nonland) card "
                            r"from it\. that player discards that card"),
    "removal_exile": re.compile(r"\bif that (?:permanent|creature) would die this turn, exile it instead"),
}


def _keyword_list(text):
    kws = tuple(k.strip() for k in re.split(r",\s*(?:and\s+)?|\s+and\s+", text) if k.strip())
    return kws if kws and all(k in COMBAT_KEYWORDS or k == "haste" for k in kws) else ()


def package_s_traits(card):
    """Paket S: Ausloeser bei Nichtkreatur-Zaubern, Lebensgewinn und Angriff, kleine statische Effekte,
    Kostensenkung, Abwerfen nach Wahl, Exil statt Sterben (als dict mit den Card-Feldern)."""
    out = {}
    res = _PACKAGE_S_RES
    for _raw, low in _clean_lines(card):
        m = res["cast_counter"].match(low)
        if m:
            out["cast_counter"] = _count(m.group(1))
        m = res["cast_team_pump"].match(low)
        if m:
            out["cast_team_pump"] = int(m.group(1))
        m = res["type_haste"].match(low)
        if m and m.group(1) not in ("creature", "other creature"):
            out["type_haste"] = m.group(1)
        m = res["lifegain_self"].match(low)
        if m:
            out["lifegain_counter"] = (_count(m.group(1)), "self")
        m = res["lifegain_draw"].match(low)
        if m:
            out["lifegain_draw"] = _count(m.group(1))
        m = res["lifegain_loyalty"].match(low)
        if m:
            out["lifegain_loyalty"] = _count(m.group(1))
        m = res["attack_drain"].match(low)
        if m:
            out["attack_drain"] = (int(m.group(1)), int(m.group(2)))
        if res["attack_exile_gy"].match(low):
            out["attack_exile_gy"] = True
        m = res["own_turn_kw"].match(low)
        if m and _keyword_list(m.group(1)):
            out["own_turn_kw"] = _keyword_list(m.group(1))
        m = res["threshold_bonus"].match(low)
        if m:
            out["threshold_bonus"] = int(m.group(1))
        m = res["noncombat_kw"].match(low)
        if m and _keyword_list(m.group(1)):
            out["noncombat_kw"] = _keyword_list(m.group(1))
        if res["counter_vigilance"].match(low):
            out["counter_vigilance"] = True
        m = res["enters_counters"].match(low)
        if m:
            out["enters_counters"] = _count(m.group(1))
        if res["death_counters_move"].match(low):
            out["death_counters_move"] = True
        m = res["targeted_draw"].match(low)
        if m:
            out["targeted_draw"] = _count(m.group(1))
        m = res["discount_fixed"].match(low)
        if m:
            out["self_discount"] = ("legendary" if "legendary" in m.group(2) else "noncreature", int(m.group(1)))
        m = res["discount_x"].match(low)
        if m:
            out["self_discount"] = (m.group(1),)
        m = res["team_kw"].match(low)
        if m and _keyword_list(m.group(1)):
            out["team_kw"] = _keyword_list(m.group(1))
        if res["defender_attack"].match(low):
            out["defender_attack"] = True
        m = res["hand_pick"].search(low)
        if m:
            out["hand_pick"] = "permanent" if "permanent" in m.group(1) else "nonland"
        if res["removal_exile"].search(low):
            out["removal_exile"] = True
    return out


def targets_opponent(card, type_line, spec):
    """Zauber (Instant, Sorcery, Aura) mit Ziel beim Gegner: Removal auf eine Kreatur oder "target opponent/player"."""
    if not ("Instant" in type_line or "Sorcery" in type_line or "Aura" in type_line):
        return False
    if spec and spec[0] not in ("sweep", "sweep_damage", "edict"):
        return True
    return any("target opponent" in low or "target player" in low for _raw, low in _clean_lines(card))


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
                removal=removal_spec(card), discard=discard_count(card),
                abilities=parse_abilities(card) if not ("Instant" in type_line or "Sorcery" in type_line) else (),
                pump_tough=pump_toughness(card, type_line), legendary="Legendary" in type_line,
                is_artifact="Artifact" in type_line,
                targets_opp=targets_opponent(card, type_line, removal_spec(card)), **battle_triggers(card),
                **token_triggers(card), **life_and_costs(card, type_line, keywords),
                creates_tokens=creates_tokens(card, type_line), choices=modal_choices(card, type_line),
                grant_kw=grant_keywords(card, type_line), **package_s_traits(card),
                removal_points=(removal_info(card) or {}).get("points", 0.0),
                creature_types=(tuple(t.lower() for t in type_line.split("—", 1)[1].split())
                                if is_creature and "—" in type_line else ())), shown
