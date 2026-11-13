"""Spielstatistik aus dem Arena-Protokoll fuer die Draft-Bilanz (components/draftstats.py).

Arena schreibt waehrend des Spiels die Nachrichten des Spielservers ("greToClientEvent", siehe components/gamestate.py).
Gezaehlt wird je Spiel (Match-Kennung "gameInfo.matchID" und "gameNumber"; die meisten Nachrichten nennen kein
gameInfo, sie gehoeren zum laufenden Spiel) aus den Annotationen:
  - AnnotationType_ZoneTransfer mit "category": Draw (gezogene Karten, ohne Starthand), CastSpell (gewirkte Zauber),
    PlayLand (gelegte Laender) fuer eigene Objekte; SBA_Damage, SBA_ZeroToughness, SBA_Deathtouch, Destroy fuer
    gegnerische Kreaturen (besiegte Kreaturen)
  - AnnotationType_DamageDealt ("damage"): Quelle (affectorId) und Ziel (affectedIds; 1 und 2 sind die Spieler):
    Schaden am Gegner (und groesster einzelner Treffer), an gegnerischen Kreaturen, erlittener Schaden
  - "turnInfo.turnNumber": Runden (gezaehlt werden die Zuege beider Spieler, wie Arena sie nummeriert)
Wem ein Objekt gehoert, steht in "gameObjects" (controllerSeatId); der eigene Platz kommt aus ConnectResp
("systemSeatIds"). Jede Annotation zaehlt je Spiel nur einmal (Kennung "id"). Wird dasselbe Protokoll noch einmal
gelesen (draftgott neu gestartet), beginnt die Zaehlung eines Spiels beim ersten Lesen in diesem Lauf von vorn, das
Ergebnis ist also dasselbe.
"""
import json

KILL = {"SBA_Damage", "SBA_ZeroToughness", "SBA_Deathtouch", "Destroy"}
FIELDS = ("drawn", "spells", "lands", "damage_dealt", "damage_creatures", "damage_taken", "biggest_hit", "kills",
          "turns")


def empty_stats():
    return {k: 0 for k in FIELDS}


def _detail(a, key, kind):
    for d in a.get("details") or []:
        if d.get("key") == key:
            vals = d.get(kind) or []
            return vals[0] if vals else None
    return None


class GameStats:
    """Liest greToClientEvent-Zeilen; games: {(Match, Spiel): Zahlen} der in diesem Lauf gelesenen Spiele."""

    def __init__(self):
        self.seat = None
        self.objects = {}  # Kennung -> (Platz des Kontrollierenden, Kreatur?)
        self.games = {}
        self._seen = {}  # (Match, Spiel) -> Kennungen der schon gezaehlten Annotationen
        self.finished = []  # (Match, Spiel), deren Ende in diesem Lauf gelesen wurde (noch nicht abgeholt)
        self.current = None  # (Match, Spiel) der letzten Nachricht mit gameInfo

    def feed_line(self, line):
        """True, wenn die Zeile eine Spielnachricht war."""
        if not line or "greToClientEvent" not in line:
            return False
        try:
            messages = json.loads(line[line.index("{"):])["greToClientEvent"]["greToClientMessages"]
        except (ValueError, KeyError, TypeError):
            return False
        for m in messages if isinstance(messages, list) else []:
            if not isinstance(m, dict):
                continue
            seats = m.get("systemSeatIds") or []
            if m.get("type") == "GREMessageType_ConnectResp" and len(seats) == 1:
                self.seat = seats[0]
            elif m.get("type") == "GREMessageType_GameStateMessage":
                if self.seat is None and len(seats) == 1:
                    self.seat = seats[0]
                self._state(m.get("gameStateMessage") or {})
        return True

    def _state(self, g):
        info = g.get("gameInfo") or {}
        match, number = info.get("matchID"), info.get("gameNumber")
        for o in g.get("gameObjects") or []:
            if isinstance(o, dict) and "instanceId" in o:
                self.objects[o["instanceId"]] = (o.get("controllerSeatId", o.get("ownerSeatId")),
                                                 "CardType_Creature" in (o.get("cardTypes") or []))
        if match and number:  # die meisten Diffs nennen kein gameInfo: dann gilt das laufende Spiel
            self.current = (match, number)
        key = self.current
        if key is None:
            return
        stats = self.games.get(key)
        if stats is None:
            stats = self.games[key] = empty_stats()
            self._seen[key] = set()
        turn = (g.get("turnInfo") or {}).get("turnNumber")
        if isinstance(turn, int):
            stats["turns"] = max(stats["turns"], turn)
        for a in g.get("annotations") or []:
            if isinstance(a, dict) and a.get("id") not in self._seen[key]:
                self._seen[key].add(a.get("id"))
                self._annotation(stats, a)
        if info.get("stage") == "GameStage_GameOver" and key not in self.finished:
            self.finished.append(key)

    def _mine(self, iid):
        owner = self.objects.get(iid, (None, False))[0]
        return None if owner is None or self.seat is None else owner == self.seat

    def _annotation(self, stats, a):
        types = a.get("type") or []
        ids = a.get("affectedIds") or []
        if "AnnotationType_ZoneTransfer" in types:
            cat = _detail(a, "category", "valueString")
            for iid in ids:
                mine = self._mine(iid)
                if mine and cat == "Draw":
                    stats["drawn"] += 1
                elif mine and cat == "CastSpell":
                    stats["spells"] += 1
                elif mine and cat == "PlayLand":
                    stats["lands"] += 1
                elif mine is False and cat in KILL and self.objects[iid][1]:
                    stats["kills"] += 1
        if "AnnotationType_DamageDealt" in types:
            n = _detail(a, "damage", "valueInt32") or 0
            src = self._mine(a.get("affectorId"))
            if src is None or self.seat is None:
                return
            for target in ids:
                if target in (1, 2):  # Spieler
                    if src and target != self.seat:
                        stats["damage_dealt"] += n
                        stats["biggest_hit"] = max(stats["biggest_hit"], n)
                    elif not src and target == self.seat:
                        stats["damage_taken"] += n
                elif src and self._mine(target) is False:
                    stats["damage_creatures"] += n


def summarize(rec, max_wins):
    """Draft-Bilanz aus einem Draft-Eintrag der Statistik: Siege, Niederlagen und die Summen aller Spiele."""
    out = empty_stats()
    out["games"] = 0
    for m in rec.get("matches") or []:
        for st in (m.get("game_stats") or {}).values():
            out["games"] += 1
            for k in FIELDS:
                out[k] = max(out[k], st.get(k, 0)) if k == "biggest_hit" else out[k] + st.get(k, 0)
    ms = rec.get("matches") or []
    out.update(wins=sum(1 for m in ms if m.get("win") is True), losses=sum(1 for m in ms if m.get("win") is False),
               max_wins=max_wins)
    return out
