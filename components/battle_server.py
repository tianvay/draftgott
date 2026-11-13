"""Gemeinsame Kampf-Schnittstelle fuer Drafthelper und Berichts-Server (Analyse).

enemy_decks(folder)               -> [{"file", "name"}] fuer alle *.txt im Unterordner enemydecks
start_battle(app, body, folder)   -> (HTTP-Status, Antwort): startet den Kampf der Varianten des letzten Berichts
                                     (app["last_entries"], app["last_args"]) als Hintergrund-Job (app["job"]);
                                     das Ergebnis steht danach in app["battle_html"], alle Spiele in app["battle_games"].
game_fragment(app, query)         -> Protokoll eines einzelnen Spiels (Spieleliste im Kampfbericht)
"""
import copy
from urllib.parse import parse_qs
from components.deckfile import parse_deck_name
from components.i18n import t

FIGHT_COUNTS = (50, 100, 250, 500, 1000)  # Auswahl in der Kampf-Leiste (Spiele je Modus)
MAX_FIGHTS = 5000
ENEMY_DIR = "enemydecks"  # Gegnerdecks liegen im Unterordner enemydecks des Projektordners


def enemy_decks(folder):
    out = []
    for p in sorted((folder / ENEMY_DIR).glob("*.txt")):
        fallback = p.stem.replace("_", " ").strip() or p.stem
        try:
            name = parse_deck_name(p.read_text(encoding="utf-8"), fallback)
        except OSError:
            continue
        out.append({"file": p.name, "name": name})
    return out


def start_battle(app, body, folder):
    enemy = (body or {}).get("enemy")
    if enemy not in {e["file"] for e in enemy_decks(folder)}:
        return 400, {"ok": False, "error": t("Unbekanntes Gegnerdeck")}
    if not app.get("last_entries"):
        return 400, {"ok": False, "error": t("Bitte zuerst simulieren: Der Kampf nutzt die Varianten des Berichts.")}
    if not app.get("battle"):
        return 400, {"ok": False, "error": t("Kampf ist nicht verfuegbar")}
    entries, run_args = app["last_entries"], app["last_args"]
    games = (body or {}).get("games")
    if games is not None:  # gewaehlte Kampfzahl; die Einstellung des Berichts bleibt unveraendert
        try:
            games = int(games)
        except (TypeError, ValueError):
            games = 0
        if not 0 < games <= MAX_FIGHTS:
            return 400, {"ok": False, "error": t("Ungueltige Zahl der Kaempfe (1 bis {max})", max=MAX_FIGHTS)}
        run_args = copy.copy(run_args)
        run_args.kaempfe = games

    def work(progress):
        result = app["battle"](entries, str(folder / ENEMY_DIR / enemy), run_args, progress)
        html, games = result if isinstance(result, tuple) else (result, {})
        app["battle_html"], app["battle_games"] = html, games
        if app.get("save_battle"):
            app["save_battle"](html, run_args)
        return html

    if not app["job"].start(work):
        return 409, {"ok": False, "error": t("Es laeuft bereits eine Simulation")}
    return 200, {"ok": True}


def game_fragment(app, query):
    """Protokoll eines Spiels: Parameter d (Deck), e (Gegner), m (play/draw), n (Nummer)."""
    from components.battle_report import protocol_html
    q = parse_qs(query or "")
    try:
        d, e, n = int(q["d"][0]), int(q["e"][0]), int(q["n"][0])
        mode = q["m"][0]
        game = (app.get("battle_games") or {})[(d, e, mode)][n]
    except (KeyError, IndexError, ValueError):
        return "<p class=\"muted\">" + t("Spiel nicht gefunden (Kampfbericht neu erstellen).") + "</p>"
    label = t("Sieg") if game["winner"] == "a" else t("Niederlage") if game["winner"] == "b" else t("Unentschieden")
    if game.get("note"):
        return "<p class=\"muted\">" + t("Spiel {n}: {note} (keine Züge).", n=n + 1, note=game['note']) + "</p>"
    mode_label = "On the Play" if mode == "play" else "On the Draw"
    return protocol_html(game, mode_label, t("Spiel {n}: {label}", n=n + 1, label=label))
