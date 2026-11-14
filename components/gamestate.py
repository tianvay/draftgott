"""Im Spiel (Live-Draft): welche eigenen Karten noch in der Bibliothek liegen und wie die Chancen stehen, sie zu ziehen.

Arena schreibt waehrend des Spiels die Nachrichten des Spielservers ins Protokoll ("greToClientEvent"):
  - ConnectResp: das eigene Deck dieses Spiels ("deckMessage" -> "deckCards", eine Arena-Nummer je Kopie) und den
    eigenen Platz ("systemSeatIds")
  - GameStateMessage: Zonen (Hand, Spielfeld, Friedhof, Exil, Stapel, Bibliothek ...) mit den Kennungen der Objekte
    darin und die Objekte selbst (Arena-Nummer, Besitzer); "Full" ersetzt alles, "Diff" nur das Genannte,
    "diffDeletedInstanceIds" entfernt Objekte; "gameInfo.stage" GameOver beendet das Spiel.
Bibliothek = Deck minus alle bekannten eigenen Karten ausserhalb der Bibliothek (Limbo, Sideboard und Aufgedecktes
zaehlen nicht, sie sind Doppel). Die Groesse der Bibliothek kommt direkt aus ihrer Zone. Karten, die per Mulligan
oder Scry unter die Bibliothek gelegt wurden, zaehlen wie alle anderen (ihre Lage ist nicht bekannt).

Spielbar: Karten der Bibliothek, die mit den eigenen Laendern auf dem Spielfeld (getappt oder nicht, also dem Mana
dieses Zuges) bezahlt werden koennen (Hybrid und Phyrexian ueber components/mana.py, X = 0). Laender selbst zaehlen
nicht als spielbar. Andere Manaquellen (Kreaturen, Treasure) zaehlen nicht.

Chancen (hypergeometrisch): mindestens eine von n passenden Karten unter den naechsten k Karten einer Bibliothek
mit L Karten = 1 - C(L - n, k) / C(L, k).
"""
import json
import math
from collections import Counter

from components.i18n import t
from components.mana import can_pay, cost_alternatives

KNOWN_ZONES = {"ZoneType_Hand", "ZoneType_Battlefield", "ZoneType_Graveyard", "ZoneType_Exile", "ZoneType_Stack",
               "ZoneType_Command"}
LOOK_AHEAD = 3  # "in den naechsten 3 Zuegen"
PUBLIC_ZONES = {"ZoneType_Battlefield", "ZoneType_Graveyard", "ZoneType_Exile", "ZoneType_Stack"}
COLOR_CODES = {"CardColor_White": "W", "CardColor_Blue": "U", "CardColor_Black": "B", "CardColor_Red": "R",
               "CardColor_Green": "G"}


def at_least_one(n, library, k):
    """Chance auf mindestens eine von n Karten unter den naechsten k Karten einer Bibliothek mit library Karten."""
    if n <= 0 or library <= 0 or k <= 0:
        return 0.0
    n, k = min(n, library), min(k, library)
    if library - n < k:
        return 1.0
    return 1 - math.comb(library - n, k) / math.comb(library, k)


def can_cast(cost, producing):
    """Kann eine Karte mit diesen Laendern (je Land die Menge seiner Farben) bezahlt werden?"""
    return any(can_pay(list(producing), g, Counter(dict(req))) for g, req in cost_alternatives(cost or ""))


def pct(p):
    if p <= 0:
        return "0 %"
    if p < 0.005:
        return "< 1 %"
    return f"{round(p * 100)} %"


class GameState:
    def __init__(self):
        self.seat = None
        self.deck = Counter()
        self.zones, self.objects = {}, {}
        self.active, self.turn = False, 0

    def _new_game(self):
        self.zones, self.objects, self.turn = {}, {}, 0

    def _state(self, g):
        if g.get("type") == "GameStateType_Full":
            self.zones, self.objects = {}, {}
        info = g.get("gameInfo") or {}
        if info.get("stage") == "GameStage_GameOver":
            self.active = False
        elif info.get("stage") in ("GameStage_Start", "GameStage_Play"):
            self.active = True
        for z in g.get("zones") or []:
            if isinstance(z, dict) and "zoneId" in z:
                self.zones[z["zoneId"]] = {"type": z.get("type"), "owner": z.get("ownerSeatId"),
                                           "ids": list(z.get("objectInstanceIds") or [])}
        for o in g.get("gameObjects") or []:
            if isinstance(o, dict) and "instanceId" in o:  # Arena schickt geaenderte Objekte immer ganz
                self.objects[o["instanceId"]] = {
                    "grp": o.get("grpId"), "owner": o.get("ownerSeatId"),
                    "controller": o.get("controllerSeatId", o.get("ownerSeatId")),
                    "land": "CardType_Land" in (o.get("cardTypes") or []), "tapped": bool(o.get("isTapped")),
                    "creature": "CardType_Creature" in (o.get("cardTypes") or []),
                    "subtypes": [s for s in o.get("subtypes") or [] if isinstance(s, str)],
                    "colors": [COLOR_CODES[c] for c in o.get("color") or [] if c in COLOR_CODES]}
        for iid in g.get("diffDeletedInstanceIds") or []:
            self.objects.pop(iid, None)
        turn = (g.get("turnInfo") or {}).get("turnNumber")
        if isinstance(turn, int):
            self.turn = turn

    def feed_line(self, line):
        """Verarbeitet eine Protokollzeile; True, wenn sie eine Spielnachricht war."""
        if not line or "greToClientEvent" not in line:
            return False
        try:
            data = json.loads(line[line.index("{"):])
            messages = data["greToClientEvent"]["greToClientMessages"]
        except (ValueError, KeyError, TypeError):
            return False
        if not isinstance(messages, list):
            return False
        for m in messages:
            if not isinstance(m, dict):
                continue
            seats = m.get("systemSeatIds") or []
            if m.get("type") == "GREMessageType_ConnectResp":
                cards = ((m.get("connectResp") or {}).get("deckMessage") or {}).get("deckCards") or []
                self.deck = Counter(c for c in cards if isinstance(c, int))
                if len(seats) == 1:
                    self.seat = seats[0]
                self._new_game()
                self.active = True
            elif m.get("type") == "GREMessageType_GameStateMessage":
                if self.seat is None and len(seats) == 1:
                    self.seat = seats[0]
                self._state(m.get("gameStateMessage") or {})
        return True

    def _zone(self, ztype):
        return next((z for z in self.zones.values() if z["type"] == ztype and z["owner"] == self.seat), None)

    def library(self):
        """(Zahl der Karten in der Bibliothek, {Arena-Nummer: Kopien, die noch drin sein muessen})."""
        lib = self._zone("ZoneType_Library")
        size = len(lib["ids"]) if lib else 0
        if not self.deck:
            return size, {}
        known = Counter()
        for z in self.zones.values():
            if z["type"] not in KNOWN_ZONES:
                continue
            for iid in z["ids"]:
                o = self.objects.get(iid)
                if o and o["owner"] == self.seat and o["grp"] in self.deck:
                    known[o["grp"]] += 1
        remaining = {g: n - known[g] for g, n in self.deck.items() if n - known[g] > 0}
        return size, remaining

    def lands_in_play(self):
        """Arena-Nummern der Objekte auf dem Spielfeld, die man selbst kontrolliert."""
        out = []
        for z in self.zones.values():
            if z["type"] == "ZoneType_Battlefield":
                for iid in z["ids"]:
                    o = self.objects.get(iid)
                    if o and o["controller"] == self.seat:
                        out.append(o["grp"])
        return out

    def hand_size(self):
        hand = self._zone("ZoneType_Hand")
        return len(hand["ids"]) if hand else 0

    def opponent_hand_size(self):
        """Handkarten des Gegners (Arena nennt nur ihre Kennungen; eine leere Hand kommt ohne Liste), None, solange
        Platz oder Zone unbekannt sind."""
        if self.seat is None:
            return None
        hand = next((z for z in self.zones.values() if z["type"] == "ZoneType_Hand" and z["owner"] is not None
                     and z["owner"] != self.seat), None)
        return len(hand["ids"]) if hand else None

    def _opponent(self, o):
        return o is not None and self.seat is not None and o["controller"] is not None and o["controller"] != self.seat

    def opponent_creatures(self):
        """Zahl der Kreaturen, die der Gegner auf dem Spielfeld kontrolliert."""
        return sum(1 for z in self.zones.values() if z["type"] == "ZoneType_Battlefield" for iid in z["ids"]
                   if self._opponent(self.objects.get(iid)) and self.objects[iid].get("creature"))

    def opponent_lands(self):
        """Laender des Gegners auf dem Spielfeld: [{"grp", "tapped", "subtypes"}]."""
        out = []
        for z in self.zones.values():
            if z["type"] == "ZoneType_Battlefield":
                for iid in z["ids"]:
                    o = self.objects.get(iid)
                    if self._opponent(o) and o["land"]:
                        out.append({"grp": o["grp"], "tapped": o["tapped"], "subtypes": o["subtypes"]})
        return out

    def opponent_spell_colors(self):
        """Farben der Nichtland-Karten, die der Gegner offen gezeigt hat (Spielfeld, Friedhof, Exil, Stapel)."""
        colors = set()
        for z in self.zones.values():
            if z["type"] not in PUBLIC_ZONES:
                continue
            for iid in z["ids"]:
                o = self.objects.get(iid)
                if o and not o["land"] and o["owner"] is not None and o["owner"] != self.seat and self.seat is not None:
                    colors |= set(o["colors"])
        return colors


def _group(key, label, n, library):
    return {"key": key, "label": label, "n": n, "next": at_least_one(n, library, 1),
            "in3": at_least_one(n, library, LOOK_AHEAD)}


def game_view(game, info):
    """Anzeige fuer Seite und Seitenfenster; info: {Arena-Nummer: Kartendaten (livedraft.card_summary)}.
    Gruppen: Land, Kreatur, Removal und je Farbe die Quellen (Laender, die die Farbe erzeugen)."""
    if not game.active:
        return {"active": False}
    library, remaining = game.library()

    def card(grp):
        return info.get(grp) or {"name": f"#{grp}", "land": False, "creature": False, "removal": 0, "produces": []}

    lands = sum(n for g, n in remaining.items() if card(g)["land"])
    creatures = sum(n for g, n in remaining.items() if card(g).get("creature"))
    removal = sum(n for g, n in remaining.items() if card(g).get("removal"))
    producing, mana_colors = [], Counter()
    for g in game.lands_in_play():
        c = info.get(g)
        if c and c["land"]:
            colors = set(c.get("produces") or []) or {"C"}
            producing.append(colors)
            for col in colors:
                mana_colors[col] += 1
    castable_grps = {g for g in remaining if not card(g)["land"] and can_cast(card(g).get("cost"), producing)}
    castable = sum(remaining[g] for g in castable_grps)
    groups = [_group("castable", t("Spielbar"), castable, library),
              _group("land", t("Land"), lands, library), _group("creature", t("Kreatur"), creatures, library),
              _group("removal", t("Removal"), removal, library)]
    deck_colors = set()
    for g in game.deck:
        c = card(g)
        if c["land"]:
            deck_colors |= set(c.get("produces") or [])
    for color in "WUBRG":
        if color in deck_colors:
            n = sum(n for g, n in remaining.items() if card(g)["land"] and color in (card(g).get("produces") or []))
            groups.append(_group(f"src_{color}", t("{color}-Quelle", color=color), n, library))
    rem_total = sum(n for g, n in game.deck.items() if card(g).get("removal"))
    points_total = sum(n * card(g).get("removal", 0) for g, n in game.deck.items())
    points_left = sum(n * card(g).get("removal", 0) for g, n in remaining.items())
    cards = []
    for g, n in remaining.items():
        c = card(g)
        cards.append({"name": c["name"], "n": n, "deck": game.deck[g], "next": at_least_one(n, library, 1),
                      "in3": at_least_one(n, library, LOOK_AHEAD), "land": c["land"],
                      "creature": bool(c.get("creature")), "removal": c.get("removal", 0),
                      "castable": g in castable_grps})
    cards.sort(key=lambda c: (c["land"], -c["n"], -c["removal"], c["name"]))
    return {"active": True, "turn": game.turn, "library": library, "hand": game.hand_size(),
            "deck": sum(game.deck.values()), "groups": groups,
            "mana": {"lands": len(producing), "colors": dict(mana_colors)},
            "removal": {"left": removal, "total": rem_total, "points_left": round(points_left, 2),
                        "points_total": round(points_total, 2)},
            "cards": cards, "consistent": sum(remaining.values()) == library}
