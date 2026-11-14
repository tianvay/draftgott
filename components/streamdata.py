"""Daten fuer das Stream-Overlay (/api/stream des Drafthelpers): dieselben Zeilen wie das Seitenfenster
(overlay.rows_for) und der Trick-Warner (overlay.trick_window_rows), dazu Bilanz, Farben, Kurve und Format als Werte.
Eine Browserquelle in OBS holt das jede Sekunde und zeichnet es in eigenem Stil (die Tk-Fenster sind Werkzeugfenster,
die die Fensteraufnahme von OBS nicht sieht)."""
from components import overlay
from components.i18n import get_lang


def _mode(snap):
    if not snap or snap.get("status") in ("nolog", "idle", "off"):
        return "off"
    if (snap.get("game") or {}).get("active"):
        return "game"
    if snap.get("complete") and snap.get("deckinfo"):
        return "deck"
    return "draft"


def _record(snap):
    s = snap.get("summary") or {}
    if s.get("games"):
        return {"wins": s["wins"], "losses": s["losses"]}
    r = (snap.get("deckinfo") or {}).get("record") or {}
    if r.get("matches"):
        return {"wins": r["wins"], "losses": r["losses"]}
    return None


def payload(snap):
    """Alles, was das Stream-Overlay braucht, als JSON-faehiges dict."""
    snap = snap or None
    rows = [list(r) for r in overlay.rows_for(snap)]
    tricks = [list(r) for r in overlay.trick_window_rows(snap)]
    if not snap:
        return {"mode": "off", "main": rows, "tricks": tricks, "record": None, "colors": [], "curve": None,
                "format": None, "lang": get_lang()}
    main = (snap.get("detect") or {}).get("main") or ""
    info = snap.get("deckinfo") or {}
    return {"mode": _mode(snap), "main": rows, "tricks": tricks, "record": _record(snap),
            "colors": [c for c in main if c in "WUBRG"], "curve": info.get("curve"),
            "format": (snap.get("signals") or {}).get("format"), "lang": get_lang()}
