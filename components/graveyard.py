"""Friedhof-Score (Graveyard Interaction) aus dem Kartentext. Gemeinsam genutzt von Drafthelper und Bericht.

gy_info(card) -> {"points", "kind", "text"} oder None: beste Friedhof-Nutzung der Karte (alle Seiten):
    Zweitverwertung 1,0 - die Karte selbst noch einmal: Flashback, Escape, Unearth, Disturb, Jump-start, Retrace, Embalm,
        Eternalize, "return this card from your graveyard", Faehigkeiten mit "exile this card from your graveyard"
    Zurueckholen 0,7 - andere Karten aus dem Friedhof auf die Hand oder ins Spiel ("return target ... card from your
        graveyard")
    Ressource 0,5 - Wert haengt vom Friedhof ab ("cards in your graveyard", Threshold, Delve, andere Karten aus dem
        Friedhof exilieren)
gy_enabler(card) -> True, wenn die Karte den eigenen Friedhof fuellt (Mill, Surveil, Abwerfen, Landcycling/Cycling,
    "put ... into your graveyard"). Enabler haben keine Punkte.
"""
import re

RECAST_KEYWORDS = ("flashback", "escape", "unearth", "disturb", "jump-start", "retrace", "embalm", "eternalize",
                   "aftermath")
RESOURCE_KEYWORDS = ("threshold", "delve", "descend")

_RETURN_SELF = re.compile(r"\breturn (this card|~) from your graveyard\b|\bexile (this card|~) from your graveyard\b|"
                          r"\bcast (this card|~) from your graveyard\b")
_RETURN_OTHER = re.compile(r"\breturn (?:up to \w+ )?(?:another )?target [^.]*?cards? from your graveyard\b|"
                           r"\breturn [^.]*?cards? from your graveyard to (your hand|the battlefield)\b")
_RESOURCE = re.compile(r"\bcards? in your graveyard\b|\bexile (another|an?|\w+ other) [^.:]*?cards? from your "
                       r"graveyard\b|\bcards? from your graveyard\b")
_ENABLER = re.compile(r"(?<!opponent )(?<!player )\bmill (\d+|x|a|an|one|two|three|four|five|cards?)\b|\byou mill\b|"
                      r"(?<!whenever you )\bsurveil \d|\bdiscard (a|an|one|two|that|this|\w+) cards?\b|"
                      r"\binto your graveyard\b")
_TRIGGER_ON = re.compile(r"\bwhenever you (surveil|mill|discard|scry)\b")


def _faces(card):
    return card.get("card_faces") or [card]


def _lines(card):
    for face in _faces(card):
        text = face.get("oracle_text") if card.get("card_faces") else card.get("oracle_text")
        name = (face.get("name") or card.get("name") or "").lower()
        for raw in (text or "").split("\n"):
            line = re.sub(r"\([^)]*\)", " ", raw).strip()
            low = line.lower().lstrip("•").strip()
            if name:
                low = re.sub(r"(?<![a-z])" + re.escape(name) + r"(?![a-z])", "~", low)
            if low:
                yield raw.strip().lstrip("•").strip(), low


def gy_info(card):
    """Beste Friedhof-Nutzung der Karte oder None."""
    keywords = {k.lower() for k in card.get("keywords") or []}
    found = []
    for raw, low in _lines(card):
        head = re.split(r"[ —{]", low, maxsplit=1)[0]
        if head in RECAST_KEYWORDS or low.startswith(tuple(RECAST_KEYWORDS)):
            found.append((1.0, "Zweitverwertung", raw))
            continue
        if _RETURN_SELF.search(low):
            found.append((1.0, "Zweitverwertung", raw))
            continue
        if _RETURN_OTHER.search(low):
            found.append((0.7, "Zurückholen", raw))
            continue
        if low.startswith(tuple(RESOURCE_KEYWORDS)) or _RESOURCE.search(low):
            found.append((0.5, "Ressource", raw))
    if not found:
        for kw in keywords & set(RECAST_KEYWORDS):
            found.append((1.0, "Zweitverwertung", kw.capitalize()))
        for kw in keywords & set(RESOURCE_KEYWORDS):
            found.append((0.5, "Ressource", kw.capitalize()))
    if not found:
        return None
    points, kind, text = max(found, key=lambda f: f[0])
    return {"points": points, "kind": kind, "text": text}


def gy_enabler(card):
    """Fuellt die Karte den eigenen Friedhof (Mill, Surveil, Abwerfen, Cycling, 'into your graveyard')?"""
    keywords = {k.lower() for k in card.get("keywords") or []}
    if any("cycling" in k for k in keywords):
        return True
    for _raw, low in _lines(card):
        low = _TRIGGER_ON.sub(" ", low)
        if "opponent" in low and "mill" in low and "you mill" not in low:
            continue
        if _ENABLER.search(low):
            return True
    return False
