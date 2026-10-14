"""Modell-Abdeckung: erkennt aus dem Kartentext (Scryfall), welche Effekte die Simulation noch nicht abbildet.

Die Erkennung ist bewusst grob: Magic formuliert dasselbe auf viele Arten, deshalb wird nur nach Mustern in
wenige Kategorien sortiert. Alles, was weder als modelliert noch als bekannte Kategorie erkannt wird, heisst
"Unbekannter Effekt". Jede erkannte Kategorie nennt die Kennzahl, die davon betroffen sein koennte.

analyze_card(scryfall_card) -> Liste von (Kategorie, Kennzahl, Textzeile); leer = nichts Auffaelliges.
"""
import re
from collections import Counter

from components.cards import (EMPOWER_RE, LANDCYCLE_RE, classify_empower_line, draw_line, land_tap_info,
                              prepared_mode, surveil_line)

STATUS_TEXT = "To Do: Noch nicht implementiert"

M_LETHAL = "Lethal / Schaden"
M_MANA = "Mana und Zauber pro Runde"
M_FLOW = "Kartenfluss (Länder, Screw/Flood)"
M_NONE = "keine (Gegner ist nicht Teil des Modells)"
M_UNKNOWN = "unklar"
METRIC_ORDER = (M_LETHAL, M_MANA, M_FLOW, M_NONE, M_UNKNOWN)

C_UNKNOWN = "Unbekannter Effekt"
C_PREPARED = "Prepared-Zauberhälfte"
C_WALKER = "Planeswalker-Fähigkeit"
C_LAND_COND = "Land: Bedingung nicht modelliert"
C_EMPOWER_X = "Empower Jace (Wert nicht modelliert)"

# Schluesselwoerter ohne Einfluss, solange es keinen Gegner gibt, oder bereits modelliert (Haste, Defender, Landcycling)
IGNORED_KEYWORDS = {
    "flying", "reach", "vigilance", "menace", "trample", "first strike", "double strike", "deathtouch", "lifelink",
    "hexproof", "ward", "indestructible", "shroud", "intimidate", "fear", "skulk", "protection", "haste", "defender",
    "enchant", "equip", "basic landcycling", "landcycling", "typecycling", "plainscycling", "islandcycling",
    "swampcycling", "mountaincycling", "forestcycling", "empower jace", "legendary", "prepared",
}
KEYWORD_CATEGORY = {
    "prowess": ("Zählmarken / Stärkebonus", M_LETHAL),
    "flash": ("Timing (Flash)", M_MANA),
    "flashback": ("Zweitverwertung (Friedhof)", M_MANA),
    "convoke": ("Kostensenkung / Convoke", M_MANA),
    "improvise": ("Kostensenkung / Convoke", M_MANA),
    "delve": ("Kostensenkung / Convoke", M_MANA),
    "cycling": ("Kartenfluss", M_FLOW),
    "surveil": ("Kartenfluss", M_FLOW),
    "scry": ("Kartenfluss", M_FLOW),
    "mill": ("Kartenfluss", M_FLOW),
    "mobilize": ("Tokens erzeugen", M_LETHAL),
    "treasure": ("Mana außer Ländern", M_MANA),
}

# (Kategorie, Kennzahl, Muster) - ein Text kann mehrere Kategorien treffen
LINE_RULES = [
    ("Tokens erzeugen", M_LETHAL,
     re.compile(r"\bcreates?\b[^.\n]*\btokens?\b|\bmobilize\b")),
    ("Direkter Schaden", M_LETHAL,
     re.compile(r"\bdeals? (\d+|x|that much|twice[^.\n]*)[^.\n]*damage to (any target|each opponent|target opponent|"
                r"target player|each player|an opponent|each other player)|(each|target) opponent loses \d+ life")),
    ("Zählmarken / Stärkebonus", M_LETHAL,
     re.compile(r"[+\-]\d+/[+\-]\d+|[+\-]x/[+\-]x|\bgets? [+\-]\d|(\+\d+/\+\d+|-\d+/-\d+) counters?|"
                r"enters with [^.\n]*counters?|\bprowess\b|base power and toughness")),
    ("Defender-Ausnahme", M_LETHAL, re.compile(r"didn't have defender")),
    ("Haste verleihen", M_LETHAL, re.compile(r"\b(gains?|have|has|with) haste\b")),
    ("Mana außer Ländern", M_MANA,
     re.compile(r"\{t\}[^.\n]*: add |(^|[,:•] ?)add \{|\badd (one|two|three|\w+) mana|treasure token|heartwood token|"
                r"\blotus\b|mana of any")),
    ("Kartenfluss", M_FLOW,
     re.compile(r"\bdraws? (a|an|one|two|three|four|\d+|x|that many|cards?)\b|\bsurveil\b|\bscry\b|"
                r"search your library|\bmill\b|look at the top|exile the top card of your library|"
                r"reveal the top|\bthen discard\b|\bcycling\b")),
    ("Kostensenkung / Convoke", M_MANA,
     re.compile(r"costs? (\{[^}]+\}|\d+) less|\bconvoke\b|\bimprovise\b|\bdelve\b")),
    ("Zweitverwertung (Friedhof)", M_MANA,
     re.compile(r"\bflashback\b|return [^.\n]*from (your|a|an|the) graveyard|from your graveyard|\bescape\b|\bunearth\b")),
    ("Interaktion mit dem Gegner", M_NONE,
     re.compile(r"\bdestroys? target|\bexiles? target|\bcounter target|return target [^.\n]* to (its|their) owner's "
                r"hand|(target|each) opponent[^.\n]* (sacrifices?|discards?|reveals?)|\bdestroys? all\b|\bexiles? up to \w+ target|\bdeals? damage equal to|\btap (target|enchanted|up to)|"
                r"\buntap target|stun counter|loses all abilities|doesn't untap|"
                r"\bfights?\b|deals? (\d+|x)[^.\n]*damage to (target|each|up to)[^.\n]*(creature|planeswalker)|"
                r"\bcan't (attack|block)|each player sacrifices")),
    ("Lebensgewinn", M_NONE, re.compile(r"\byou gain (\d+|x|that much)|\bgains? \d+ life|\bgain life")),
    ("Zusatzkosten", M_MANA, re.compile(r"as an additional cost")),
    ("Schlüsselwort verleihen", M_NONE,
     re.compile(r"\b(gains?|have|has)\b[^.\n]*\b(flying|trample|first strike|double strike|vigilance|deathtouch|"
                r"lifelink|hexproof|indestructible|menace|reach)\b|can't be blocked")),
]
LOYALTY_LINE = re.compile(r"^[+−\-]?(\d+|x):|^\[[^\]]+\]:")
MODAL_HEADER = re.compile(r"\bchoose (one|two|any number)( or (both|more))?\s*(—|-)?\s*$")
DECK_RULE = re.compile(r"^a deck can have|\bany number of cards named\b")
KEYWORD_SPLIT = re.compile(r"[,;]")


def _strip(line):
    line = re.sub(r"\([^)]*\)", "", line)
    return line.strip().lstrip("•").strip()


def _keyword_tokens(line, known):
    """Zerlegt eine Schluesselwort-Zeile ('Flying, trample', 'Ward {2}', 'Flashback {4}{W}') in Woerter.
    Gibt None zurueck, wenn die Zeile mehr als Schluesselwoerter enthaelt."""
    tokens = []
    for part in KEYWORD_SPLIT.split(line):
        head, dash, tail = part.partition(chr(0x2014))
        part = re.sub(r"\d+", "", re.sub(r"\{[^}]*\}", "", head)).strip().lower()
        if dash and tail.strip() and part not in IGNORED_KEYWORDS:
            return None  # Faehigkeitswort mit eigenem Text (Threshold, Domain, ...)
        if not part:
            continue
        if part not in known:
            return None
        tokens.append(part)
    return tokens or None


def _classify(low, is_planeswalker):
    found = []
    for category, metric, pattern in LINE_RULES:
        if pattern.search(low):
            found.append((category, metric))
    if any(c == "Tokens erzeugen" for c, _ in found) and re.search(r"treasure|heartwood|lotus", low):
        found = [(c, m) for c, m in found if c != "Tokens erzeugen"]
    if not found and is_planeswalker and LOYALTY_LINE.match(low):
        found.append((C_WALKER, M_UNKNOWN))
    return found


def analyze_card(card):
    """Gibt alle (Kategorie, Kennzahl, Textzeile) zurueck, die die Simulation noch nicht abbildet."""
    faces = card.get("card_faces") or [card]
    known = IGNORED_KEYWORDS | set(KEYWORD_CATEGORY) | {k.lower() for k in card.get("keywords") or []}
    prepare = card.get("layout") == "prepare" and len(faces) > 1
    prepare_modelled = bool(prepared_mode(card))  # Zauberhaelfte wird als Kopie gewirkt (siehe cards.prepared_spell)
    items = []
    for fi, face in enumerate(faces):
        type_line = face.get("type_line") or card.get("type_line") or ""
        is_land = "Land" in type_line.split("—")[0]
        is_walker = "Planeswalker" in type_line
        face_items = []
        for raw in (face.get("oracle_text") or "").split("\n"):
            line = _strip(raw)
            if not line:
                continue
            low = line.lower()
            if MODAL_HEADER.search(low) or DECK_RULE.search(low):
                continue
            if prepare and "prepared" in low:
                continue
            if LANDCYCLE_RE.search(line) and len(line) < 40:
                continue
            if low.startswith("enchant ") and "aura" in type_line.lower():
                continue
            spell_face = "Instant" in type_line or "Sorcery" in type_line
            modelled_face = fi == 0 or (prepare_modelled and fi == 1)
            if modelled_face and not raw.strip().startswith("•"):
                n, rest = surveil_line(line, spell_face, face.get("name") or card.get("name", ""))
                if n:  # Surveil mit fester Zahl ist modelliert; der Rest der Zeile wird weiter geprueft
                    if re.sub(r"[^a-z]", "", rest):
                        line, low = rest, rest
                    else:
                        continue
            if is_land:
                if re.match(r"^\{t\}: add ", low):
                    continue
                if re.search(r"enters( the battlefield)? tapped|behold a jace", low):
                    mode = land_tap_info(card, face)[0]
                    if mode == "tapped?":
                        face_items.append((C_LAND_COND, M_MANA, line))
                    continue
            if modelled_face and not is_land and not raw.strip().startswith("•"):  # Modi bleiben offen
                n, rest = draw_line(line, "Instant" in type_line or "Sorcery" in type_line, card.get("name", ""))
                if n:  # Ziehen mit fester Zahl ist modelliert; der Rest der Zeile wird weiter geprueft
                    if re.sub(r"[^a-z]", "", rest):
                        face_items += [(c, m, line) for c, m in (_classify(rest, False) or [(C_UNKNOWN, M_UNKNOWN)])]
                    continue
            if EMPOWER_RE.search(line):
                effects = classify_empower_line(line, "Instant" in type_line or "Sorcery" in type_line)
                amounts = EMPOWER_RE.findall(line)
                variable = all(a.lower() == "x" for a in amounts)
                if not (effects and not any(e[4] for e in effects) and not variable):
                    face_items.append((C_EMPOWER_X if variable else "Empower Jace (Auslöser nicht modelliert)",
                                       M_FLOW, line))
                rest = EMPOWER_RE.sub(" ", low)
                if len(re.sub(r"[^a-z]", "", rest)) > 12:
                    face_items += [(c, m, line) for c, m in _classify(rest, False)]
                continue
            tokens = _keyword_tokens(low, known)
            if tokens is not None:
                for token in tokens:
                    if token in IGNORED_KEYWORDS:
                        continue
                    category, metric = KEYWORD_CATEGORY.get(token, (C_UNKNOWN, M_UNKNOWN))
                    face_items.append((category, metric, line))
                continue
            cats = _classify(low, is_walker)
            if not cats:
                cats = [(C_UNKNOWN, M_UNKNOWN)]
            face_items += [(c, m, line) for c, m in cats]
        if prepare and fi >= 1 and not prepare_modelled:
            metrics = {m for _c, m, _l in face_items} | {M_MANA}
            first = next((l for _c, _m, l in face_items), "Zauberhälfte")
            items += [(C_PREPARED, m, first) for m in sorted(metrics, key=METRIC_ORDER.index)]
        else:
            items += face_items
    seen, out = set(), []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def metrics_of(items):
    return {m for _c, m, _l in items}


def summarize(coverage_by_name, qty_by_name):
    """Zaehlt Karten (nicht Kopien) je Kennzahl und Kategorie; coverage_by_name: {Name: analyze_card-Ergebnis}."""
    flagged = [n for n, items in coverage_by_name.items() if items]
    by_metric = {m: 0 for m in METRIC_ORDER}
    by_category = Counter()
    for n in flagged:
        for m in metrics_of(coverage_by_name[n]):
            by_metric[m] += 1
        for c in {c for c, _m, _l in coverage_by_name[n]}:
            by_category[c] += 1
    return {"flagged_cards": len(flagged), "flagged_copies": sum(qty_by_name.get(n, 1) for n in flagged),
            "by_metric": by_metric, "by_category": dict(by_category)}
