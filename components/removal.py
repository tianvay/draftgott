"""Flash, Deathtouch und Removal-Score aus dem Kartentext (Scryfall). Gemeinsam genutzt von Drafthelper und Bericht.

keyword_flags(card) -> ["flash", "deathtouch"]: Schluesselwoerter, die die Karte selbst hat (Vorderseite, eigene
    Schluesselwort-Zeile). Flash zaehlt nur bei bleibenden Karten; Verleihen ("have deathtouch") zaehlt nicht.
removal_info(card) -> {"points", "kind", "text"} oder None: bester Removal-Effekt der Karte (alle Seiten, bei modalen
    Karten der beste Modus). Punkte 0 bis 1, 1 = entfernt jede gegnerische Kreatur zuverlaessig:
        Hart (destroy/exile target creature) 1,0 · Massenremoval 1,0 · Exil bis verlassen (O-Ring) 0,9
        Edikt 0,7 (mit "greatest mana value" 0,9) · Toughness 0 (z. B. "base power and toughness 0/0") 0,7
        · Schaden und -X/-X nach Hoehe (1: 0,2 · 2: 0,4 · 3: 0,6 · 4: 0,8
        · 5+: 0,9, X: 0,5) · Lock-Aura 0,7 · Fight 0,5 · Bounce 0,3
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
_DAMAGE = re.compile(r"\bdeals? (\d+|x|damage equal to[^.]*?)(?: damage)? to (" + _TARGET +
                     r" (creature|planeswalker|creature or planeswalker)[^.]*|any target[^.]*)")
_DAMAGE_EACH = re.compile(r"\bdeals? (\d+) damage to each (creature|other creature)")
_MINUS = re.compile(r"\b" + _TARGET + r" creature[^.]*? gets? -(\d+|x)/-(\d+|x)")
_FIGHT = re.compile(r"\bfights? (" + _TARGET + r" creature[^.]*|another target creature[^.]*)")
_BOUNCE = re.compile(r"\breturn " + _TARGET + r" ([^.]*?) to (its|their) owner'?s'? hand")
# Basis-Toughness 0: "has base power and toughness 0/0", "becomes a 0/0", "has base toughness 0"
_TOUGH0 = re.compile(r"\b(" + _TARGET + r" creature[^.]*?)\b(?:has base power and toughness (?:\d+|x)/0|"
                     r"becomes an? (?:\d+|x)/0|has base toughness 0)\b")
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
        if not _HOLDS_CREATURE.search(phrase.split(" to ")[0]) or "you control" in phrase:
            continue
        until = " until " in phrase
        value, label = (0.9, "Exil bis verlassen") if until else (1.0, "Hart")
        if _CONDITION.search(phrase.split(" until ")[0]):
            value, label = 0.5, "Bedingt"
        found.append((value, label))
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


def removal_level(points, cards):
    """Ampel fuer die Summe der Removal-Punkte: gruen ab 4, gelb ab 2,5 bei 40 Karten (anteilig)."""
    scale = (cards or 40) / 40
    if points + 1e-9 >= GREEN_PER_40 * scale:
        return "green"
    if points + 1e-9 >= YELLOW_PER_40 * scale:
        return "yellow"
    return "red"
