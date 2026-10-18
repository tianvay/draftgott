"""Flash, Deathtouch und Removal-Score aus dem Kartentext (Scryfall). Gemeinsam genutzt von Drafthelper und Bericht.

keyword_flags(card) -> ["flash", "deathtouch"]: Schluesselwoerter, die die Karte selbst hat (Vorderseite, eigene
    Schluesselwort-Zeile). Flash zaehlt nur bei bleibenden Karten; Verleihen ("have deathtouch") zaehlt nicht.
removal_info(card) -> {"points", "kind", "text"} oder None: bester Removal-Effekt der Karte (alle Seiten, bei modalen
    Karten der beste Modus). Punkte 0 bis 1, 1 = entfernt jede gegnerische Kreatur zuverlaessig:
        Hart (destroy/exile target creature) 1,0 · Massenremoval 1,0 · Exil bis verlassen (O-Ring) 0,9
        Edikt 0,7 (mit "greatest mana value" 0,9) · Toughness 0 (z. B. "base power and toughness 0/0") 0,7
        · Schaden und -X/-X nach Hoehe (1: 0,2 · 2: 0,4 · 3: 0,6 · 4: 0,8
        · 5+: 0,9, X: 0,5) · Lock-Aura 0,7 · Fight 0,5 · Bounce 0,3 · Bibliothek (Besitzer waehlt oben/unten) 0,3
        Bedingung am Ziel (Manawert, Toughness, Flying, Farbe ...) oder eigenes Opfer ("you may sacrifice"): hoechstens
        0,5 · bezahlbare Faehigkeiten und Planeswalker-Faehigkeiten ("Faehigkeit") sowie andere Ausloeser als das
        Betreten ("Ausloeser"): halber Wert.
removal_level(points, cards) -> Ampel: gruen ab 4, gelb ab 2,5 Punkten bei 40 Karten (anteilig zur Deckgroesse).
"""
import re

KEYWORD_FLAGS = ("flash", "deathtouch")
GREEN_PER_40, YELLOW_PER_40 = 4.0, 2.5

_TARGET = r"(?:up to (?:one|two) )?(?:another )?target"
_HOLDS_CREATURE = re.compile(r"\b(creature|nonland permanent|permanent)\b")
_CONDITION = re.compile(
    r"\bwith\b|\bthat's\b|\bthat is\b|\btapped\b|\battacking\b|\bblocking\b|\bnon(?!land\b)[a-z]+\b|"
    r"\b(white|blue|black|red|green|colorless|multicolored|legendary|token)\b")
_DESTROY = re.compile(r"\b(destroy|exile)s? " + _TARGET + r" ([^.]*)")
_ALL = re.compile(r"\b(destroy|exile)s? all (creatures|nonland permanents|other creatures)")
_EDICT = re.compile(r"\b(target|each) opponents? (sacrifices|exiles) (a|an|one) (creature|nonland permanent)")
_COLORS = r"(?:(?:white|blue|black|red|green)(?: or (?:white|blue|black|red|green))? )?"
_DAMAGE = re.compile(r"\bdeals? (\d+|x|damage equal to[^.]*?)(?: damage)? to (" + _TARGET +
                     r" " + _COLORS + r"(creature|planeswalker|creature or planeswalker)[^.]*|any target[^.]*)")
# Biss nur in eine Richtung mit Bedingung im ersten Satz (Flourishing Grapple): "Target creature ... an opponent controls
# that's red or white ... Target creature you control deals damage equal to its power to that permanent."
_BITE_THAT = re.compile(r"\btarget creature(?: or planeswalker)? an opponent controls (that's [a-z ]+?) (?:loses|gets|gains)[^.]*\. target "
                        r"creature you control deals damage equal to its power to that (?:permanent|creature)")
# Zurueck in die Bibliothek, der Besitzer waehlt oben oder unten (Plan for All Outcomes)
_TUCK = re.compile(r"\bthe owner of (?:up to one )?(?:other )?target (nonland permanent|creature|permanent)[^.]* puts "
                   r"it on (?:their choice of )?the top or bottom of their library|\bchoose target nonland permanent\. "
                   r"its owner may put it on top of their library")
_DAMAGE_EACH = re.compile(r"\bdeals? (\d+) damage to each (creature|other creature)")
_MINUS = re.compile(r"\b" + _TARGET + r" creature[^.]*? gets? -(\d+|x)/-(\d+|x)")
_FIGHT = re.compile(r"\bfights? (" + _TARGET + r" creature[^.]*|another target creature[^.]*)")
_BOUNCE = re.compile(r"\breturn " + _TARGET + r" ([^.]*?) to (its|their) owner'?s'? hand")
# Basis-Toughness 0: "has base power and toughness 0/0", "becomes a 0/0", "has base toughness 0"
_TOUGH0 = re.compile(r"\b(" + _TARGET + r" creature[^.]*?)\b(?:has base power and toughness (?:\d+|x)/0|"
                     r"becomes an? (?:\d+|x)/0|has base toughness 0)\b")
_MINUS_COUNTERS = re.compile(r"\bput (x|\d+) -1/-1 counters? on (?:up to one )?(?:another )?target creature")
_LOCK = re.compile(r"\benchanted creature (?:[^.]*?\b)?(doesn't untap|can't attack|can't block)")
_ACTIVATED = re.compile(r"^[^:\"]*(\{[^}]+\}|\bsacrifice\b|\bdiscard\b|\bexile this\b)[^:\"]*:")
_LOYALTY = re.compile(r"^[+−\-]?(\d+|x):")
_TRIGGER = re.compile(r"^(when|whenever|at the beginning)\b")


def _strip(text):
    return re.sub(r"\([^)]*\)", " ", text or "")


def _faces(card):
    return card.get("card_faces") or [card]


def keyword_flags(card):
    """Flash (nur bleibende Karten) und Deathtouch, wenn die Vorderseite sie als eigene Schluesselwort-Zeile hat."""
    front = _faces(card)[0]
    type_line = (front.get("type_line") or card.get("type_line") or "").split(" // ")[0]
    text = front.get("oracle_text") if card.get("card_faces") else card.get("oracle_text")
    found = set()
    for raw in _strip(text).split("\n"):
        tokens = [t.strip().lower() for t in raw.split(",") if t.strip()]
        if tokens and all(re.fullmatch(r"[a-z ]{2,20}", t) for t in tokens):
            found |= set(tokens) & set(KEYWORD_FLAGS)
    if "Instant" in type_line or "Sorcery" in type_line:
        found.discard("flash")
    return [k for k in KEYWORD_FLAGS if k in found]


def _amount(word):
    if word.isdigit():
        n = int(word)
        return 0.2 if n <= 1 else 0.4 if n == 2 else 0.6 if n == 3 else 0.8 if n == 4 else 0.9
    return 0.5  # X oder "damage equal to ..."


def _classify(low):
    """(Punkte, Art) des besten Removal-Effekts einer Zeile (ohne Faehigkeits-/Ausloeser-Abzug) oder None."""
    found = []
    if _ALL.search(low):
        found.append((1.0, "Massenremoval"))
    m = _DAMAGE_EACH.search(low)
    if m:
        found.append((_amount(m.group(1)), "Massenremoval"))
    for m in _DESTROY.finditer(low):
        phrase = m.group(2)
        if not _HOLDS_CREATURE.search(phrase.split(" to ")[0]) or "you control" in phrase \
                or re.match(r"noncreature\b", phrase):  # "noncreature, nonland permanent" trifft keine Kreatur
            continue
        until = " until " in phrase
        value, label = (0.9, "Exil bis verlassen") if until else (1.0, "Hart")
        if _CONDITION.search(phrase.split(" until ")[0]):
            value, label = 0.5, "Bedingt"
        found.append((value, label))
    if _BITE_THAT.search(low):
        found.append((0.5, "Bedingt"))
    if _TUCK.search(low):
        found.append((0.3, "Bibliothek"))
    m = _EDICT.search(low)
    if m:
        found.append((0.9 if "greatest mana value" in low else 0.7, "Edikt"))
    for m in _DAMAGE.finditer(low):
        value = _amount(m.group(1).split()[0] if not m.group(1).startswith("damage") else "x")
        target = m.group(2)
        if "you control" in target:
            continue
        if _CONDITION.search(target):
            value, label = min(value, 0.5), "Bedingt"
        else:
            label = "Schaden"
        found.append((value, label))
    for m in _MINUS.finditer(low):
        if "you control" in low[max(0, m.start() - 5):m.end()] and "opponent" not in low[m.start():m.end()]:
            continue
        found.append((_amount(m.group(2)) if m.group(2) != "0" else 0.0, "−X/−X"))
    m = _FIGHT.search(low)
    if m and ("opponent controls" in low or "you don't control" in low):
        found.append((0.5, "Fight"))
    m = _BOUNCE.search(low)
    if m and _HOLDS_CREATURE.search(m.group(1)) and "you control" not in m.group(1):
        found.append((0.3, "Bounce"))
    for m in _TOUGH0.finditer(low):
        target = m.group(1)
        if "you control" in target:
            continue
        found.append((0.5, "Bedingt") if _CONDITION.search(target) else (0.7, "Toughness 0"))
    if _LOCK.search(low):
        found.append((0.7, "Lock"))
    m = _MINUS_COUNTERS.search(low)
    if m:
        found.append((_amount(m.group(1)), "−1/−1-Marken"))
    found = [f for f in found if f[0] > 0]
    if not found:
        return None
    best = max(found, key=lambda f: f[0])
    if "you may sacrifice" in low and best[1] == "Edikt":
        best = (0.5, "Bedingt")
    return best


def removal_info(card):
    """Bester Removal-Effekt der Karte: {"points", "kind", "text"} oder None."""
    best = None
    for face in _faces(card):
        type_line = face.get("type_line") or card.get("type_line") or ""
        name = (face.get("name") or card.get("name") or "").lower()
        text = face.get("oracle_text") if card.get("card_faces") else card.get("oracle_text")
        for raw in (text or "").split("\n"):
            line = _strip(raw).strip()
            low = line.lower().lstrip("•").strip()
            if not low or '"' in low or "“" in low:
                continue  # verliehene Faehigkeiten in Anfuehrungszeichen zaehlen nicht
            for nm in {name, name.split(",")[0]} - {""}:
                low = low.replace(nm, "~")
            res = _classify(low)
            if not res:
                continue
            value, label = res
            if _LOYALTY.match(low) and "Planeswalker" in type_line or _ACTIVATED.match(low):
                value, label = value / 2, "Fähigkeit"
            elif _TRIGGER.match(low) and "enters" not in low.split(",")[0]:
                value, label = value / 2, "Auslöser"
            value = round(value, 2)
            if best is None or value > best["points"]:
                best = {"points": value, "kind": label, "text": raw.strip().lstrip("•").strip()}
    return best


_COLOR_WORD = {"white": "W", "blue": "U", "black": "B", "red": "R", "green": "G"}
_DISCARD = re.compile(r"\b(?:each opponent|target opponent) discards (a|an|one|two|three|\d+) cards?\b")
_NUM = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3}


def _conditions(phrase):
    """Bedingungen am Ziel: Flying, Manawert, Toughness, Power, Farben."""
    out = []
    if re.search(r"\bwith flying\b", phrase):
        out.append(("flying",))
    m = re.search(r"mana value (\d+) or less", phrase)
    if m:
        out.append(("mv_le", int(m.group(1))))
    m = re.search(r"toughness (\d+) or greater", phrase)
    if m:
        out.append(("tough_ge", int(m.group(1))))
    m = re.search(r"power (\d+) or greater", phrase)
    if m:
        out.append(("pow_ge", int(m.group(1))))
    colors = [_COLOR_WORD[w] for w in re.findall(r"\b(white|blue|black|red|green)\b", phrase)]
    if colors:
        out.append(("color",) + tuple(dict.fromkeys(colors)))
    return tuple(out)


def _amount_of(word):
    return int(word) if word.isdigit() else -1


def _spec_from(low, label):
    """(Art, Menge, Bedingungen, any_target) fuer die Simulation im Kampf; Menge -1 = X, -2 = Power unserer
    Kreatur, -3 = hoechster Manawert im eigenen Friedhof."""
    target = low
    m = re.search(r"target ([^.]*)", low)
    if m:
        target = m.group(1)
    if label == "Massenremoval":
        m = _DAMAGE_EACH.search(low)
        if m:
            cond = (("opponents",),) if "opponents control" in low or "don't control" in low else ()
            return "sweep_damage", int(m.group(1)), cond, False
        return "sweep", 0, ((("chosen_type",),) if "chosen type" in low else ()), False
    if label in ("Hart", "Exil bis verlassen", "Toughness 0"):
        return "destroy", 0, _conditions(target), False
    if label == "Edikt" or (label == "Bedingt" and _EDICT.search(low)):
        return "edict", 0, ((("greatest",),) if "greatest mana value" in low else ()), False
    if label == "Fight":
        return "fight", 0, (), False
    if label == "Bounce":
        return "bounce", 0, (), False
    if label == "Lock":
        return "lock", 0, (), False
    if label == "Bibliothek":
        return "tuck", 0, (), False
    m = _BITE_THAT.search(low)
    if m:
        return "damage", -2, _conditions(m.group(1)), False
    if label == "−X/−X":
        m = _MINUS.search(low)
        return "minus", (_amount_of(m.group(2)) if m else -1), _conditions(target), False
    if label == "−1/−1-Marken":
        m = _MINUS_COUNTERS.search(low)
        amount = -3 if "graveyard" in low else (_amount_of(m.group(1)) if m else -1)
        return "counters", amount, (), False
    m = _DAMAGE.search(low)
    if m:
        word = m.group(1).split()[0]
        amount = -2 if word == "damage" else _amount_of(word)
        return "damage", amount, _conditions(m.group(2)), "any target" in m.group(2)
    if _DESTROY.search(low):
        return "destroy", 0, _conditions(target), False
    return None


def removal_spec(card):
    """Wirkung des Removals im Kampf: (Art, Menge, Bedingungen, any_target, Zeitpunkt, eigenes Abwerfen) oder ().
    Zeitpunkt: "spell" (Instant/Sorcery), "etb" (beim Betreten), "aura" (Lock-Aura beim Wirken). Faehigkeiten und
    andere Ausloeser werden im Kampf (noch) nicht genutzt."""
    front = _faces(card)[0]
    type_line = (front.get("type_line") or card.get("type_line") or "").split(" // ")[0]
    spell = "Instant" in type_line or "Sorcery" in type_line
    aura = "Aura" in type_line
    text = front.get("oracle_text") if card.get("card_faces") else card.get("oracle_text")
    name = (front.get("name") or card.get("name") or "").lower()
    best = None
    for raw in (text or "").split("\n"):
        low = _strip(raw).strip().lower().lstrip("•").strip()
        if not low or '"' in low or "“" in low or _ACTIVATED.match(low) or _LOYALTY.match(low):
            continue
        for nm in {name, name.split(",")[0]} - {""}:
            low = low.replace(nm, "~")
        if spell:
            if _TRIGGER.match(low):
                continue
            when = "spell"
        elif aura and low.startswith("enchanted creature"):
            when = "aura"
        else:
            head, _, body = low.partition(",")
            if not (_TRIGGER.match(low) and "enters" in head):
                continue
            when, low = "etb", body.strip()
        res = _classify(low)
        if not res:
            continue
        spec = _spec_from(low, res[1])
        if spec and (best is None or res[0] > best[0]):
            best = (res[0], spec + (when, "you may discard a card" in low))
    return best[1] if best else ()


def discard_count(card):
    """Karten, die der Gegner beim Wirken bzw. Betreten abwirft ("each opponent discards a card")."""
    front = _faces(card)[0]
    text = front.get("oracle_text") if card.get("card_faces") else card.get("oracle_text")
    total = 0
    for raw in (text or "").split("\n"):
        low = _strip(raw).lower()
        if re.match(r"\s*(whenever|at the beginning)\b", low):
            continue
        for m in _DISCARD.finditer(low):
            total += _NUM.get(m.group(1)) or int(m.group(1))
    return total


def has_flash(card):
    """Flash als eigene Schluesselwort-Zeile (bei Instants ohne Bedeutung)."""
    return "flash" in _own_keywords(card)


def _own_keywords(card):
    front = _faces(card)[0]
    text = front.get("oracle_text") if card.get("card_faces") else card.get("oracle_text")
    found = set()
    for raw in _strip(text).split("\n"):
        tokens = [t.strip().lower() for t in raw.split(",") if t.strip()]
        if tokens and all(re.fullmatch(r"[a-z ]{2,20}", t) for t in tokens):
            found |= set(tokens)
    return found


def removal_level(points, cards):
    """Ampel fuer die Summe der Removal-Punkte: gruen ab 4, gelb ab 2,5 bei 40 Karten (anteilig)."""
    scale = (cards or 40) / 40
    if points + 1e-9 >= GREEN_PER_40 * scale:
        return "green"
    if points + 1e-9 >= YELLOW_PER_40 * scale:
        return "yellow"
    return "red"
