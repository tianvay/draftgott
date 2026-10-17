"""Berichts-Server fuer die Analyse (--bericht-server): zeigt den Bericht ueber http://127.0.0.1 an, damit
"Kampf simulieren" im Bericht funktioniert. Das Programm laeuft, bis "Beenden" geklickt oder das Fenster geschlossen
wird. Nur Standardbibliothek; der Server hoert ausschliesslich auf 127.0.0.1.
"""
import http.server
import json
import pathlib
import sys
import threading
import webbrowser

from components.battle_server import enemy_decks, start_battle
from components.drafthelper import Job, LocalServer

PORT = 8766
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent.parent


def make_app(report_html, entries, args, battle, save_battle, folder=SCRIPT_DIR):
    return {"report_html": report_html, "last_entries": entries, "last_args": args, "battle": battle,
            "save_battle": save_battle, "job": Job(), "folder": pathlib.Path(folder)}


def make_handler(app):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, body, ctype="text/html; charset=utf-8", code=200):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _json(self, obj, code=200):
            self._send(json.dumps(obj), "application/json; charset=utf-8", code)

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path in ("/", "/report"):
                self._send(app["report_html"])
            elif path == "/battle":
                self._send(app.get("battle_html") or "<p>Noch kein Kampfbericht vorhanden.</p>")
            elif path == "/api/enemies":
                self._json({"enemies": enemy_decks(app["folder"]), "quit": True})
            elif path == "/api/status":
                self._json(app["job"].status())
            else:
                self._send("Nicht gefunden", "text/plain; charset=utf-8", 404)

        def do_POST(self):
            path = self.path.split("?", 1)[0]
            if path == "/api/quit":
                self._json({"ok": True})
                threading.Thread(target=app["server"].shutdown, daemon=True).start()
                return
            if path != "/api/battle":
                self._send("Nicht gefunden", "text/plain; charset=utf-8", 404)
                return
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            except ValueError:
                body = {}
            code, answer = start_battle(app, body, app["folder"])
            self._json(answer, code)

    return Handler


def start(app, port=PORT):
    """Startet den Server im Hintergrund und gibt ihn zurueck (fuer Tests und serve_report)."""
    try:
        server = LocalServer(("127.0.0.1", port), make_handler(app))
    except OSError:
        server = LocalServer(("127.0.0.1", 0), make_handler(app))
    app["server"] = server
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def serve_report(report_html, entries, args, battle, save_battle, open_browser=True):
    """Zeigt den Bericht ueber den lokalen Server an und wartet, bis er beendet wird."""
    app = make_app(report_html, entries, args, battle, save_battle)
    server = start(app)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Bericht mit Kampf-Funktion: {url}", file=sys.stderr)
    print("Zum Beenden: Knopf 'Beenden' im Bericht oder Strg+C hier im Fenster.", file=sys.stderr)
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    stopped = threading.Event()
    original = server.shutdown

    def shutdown():
        original()
        stopped.set()

    server.shutdown = shutdown
    try:
        while not stopped.wait(0.5):
            pass
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("Bericht beendet.", file=sys.stderr)
