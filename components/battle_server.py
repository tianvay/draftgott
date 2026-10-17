"""Gemeinsame Kampf-Schnittstelle fuer Drafthelper und Berichts-Server (Analyse).

enemy_decks(folder)               -> [{"file", "name"}] fuer alle _enemydeck*.txt im Ordner
start_battle(app, body, folder)   -> (HTTP-Status, Antwort): startet den Kampf der Varianten des letzten Berichts
                                     (app["last_entries"], app["last_args"]) als Hintergrund-Job (app["job"]);
                                     das Ergebnis steht danach in app["battle_html"].
"""
from components.deckfile import parse_deck_name


def enemy_decks(folder):
    out = []
    for p in sorted(folder.glob("_enemydeck*.txt")):
        stem = p.stem
        for prefix in ("_enemydeck_", "_enemydeck"):
            if stem.startswith(prefix):
                stem = stem[len(prefix):]
                break
        fallback = stem.replace("_", " ").strip() or p.stem
        try:
            name = parse_deck_name(p.read_text(encoding="utf-8"), fallback)
        except OSError:
            continue
        out.append({"file": p.name, "name": name})
    return out


def start_battle(app, body, folder):
    enemy = (body or {}).get("enemy")
    if enemy not in {e["file"] for e in enemy_decks(folder)}:
        return 400, {"ok": False, "error": "Unbekanntes Gegnerdeck"}
    if not app.get("last_entries"):
        return 400, {"ok": False, "error": "Bitte zuerst simulieren: Der Kampf nutzt die Varianten des Berichts."}
    if not app.get("battle"):
        return 400, {"ok": False, "error": "Kampf ist nicht verfuegbar"}
    entries, run_args = app["last_entries"], app["last_args"]

    def work(progress):
        html = app["battle"](entries, str(folder / enemy), run_args, progress)
        app["battle_html"] = html
        if app.get("save_battle"):
            app["save_battle"](html, run_args)
        return html

    if not app["job"].start(work):
        return 409, {"ok": False, "error": "Es laeuft bereits eine Simulation"}
    return 200, {"ok": True}
