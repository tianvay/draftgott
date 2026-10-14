"""Draft-Helper (--drafthelper): lokaler Webserver mit Kartenseite.

Die Seite zeigt Deck und Sideboard aus der Kartenpool-Datei als Karten (Daten und Bilder von Scryfall). Jede Kopie
einer Karte wird als Core, Splash, NoSplash oder Aus markiert. Standardlaender werden getrennt davon als Mengen je
Gruppe eingestellt (auch solche, die nicht im Pool sind). Ein Klick auf "Simulieren" baut daraus die Varianten
Core + Splash und Core + NoSplash, simuliert sie mit der normalen Pipeline und zeigt den Vergleichsbericht.

Nur Standardbibliothek. Der Server hoert ausschliesslich auf 127.0.0.1.
"""
import argparse
import hashlib
import re
import http.server
import json
import pathlib
import sys
import threading
import time
import traceback
import urllib.error
import webbrowser
from collections import Counter

from components.cards import card_info
from components.cardkinds import (FLOW_ORDER, empower_points, flow_kinds,  # noqa: F401 (auch von Tests benutzt)
                                  type_kinds)
from components.deckfile import parse_pool
from components.howitworks import render_help_page
from components.landadvice import color_overview, recommend
from components.symbols import active as active_symbols, symbol_css
from components.scryfall import card_image_url, fetch_cards_cached, fetch_printing_images
from components.suggest import WUBRG, propose, suggest

PORT = 8765
MARKS = ("core", "splash", "nosplash", "off")
GROUPS = ("core", "splash", "nosplash")
BASIC_LANDS = ("Plains", "Island", "Swamp", "Mountain", "Forest")
MAX_BASICS = 40  # je Land und Gruppe
CATEGORIES = ("splashworthy", "mustplay", "filler", "neverplay")  # Kategorie je Karte, hoechstens eine
SORTS = ("mv", "name", "color", "mark", "cat")  # Sortierungen der Seite (fuer die Filler-Reihenfolge)
SIM_OPTIONS = (1000, 5000, 10000)
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent.parent


def load_pool(path, refresh=False):
    """Liest die Pool-Datei und ergaenzt Typ, Manawert und Bild-URL von Scryfall.
    Gibt (cards, basics, signature) zurueck: cards ohne Standardlaender (Reihenfolge Deck, Sideboard), basics mit
    allen fuenf Standardlaendern (Startwert Core = Anzahl im Deck der Datei, 'pool' = Anzahl in Deck und Sideboard)
    und eine Signatur des Dateiinhalts (die Seite speichert ihren Stand je Signatur, nicht je Dateiname)."""
    p = pathlib.Path(path)
    if not p.exists() and (SCRIPT_DIR / p).exists():
        p = SCRIPT_DIR / p
    if not p.exists():
        sys.exit(f"Kartenpool-Datei nicht gefunden: {path}")
    rows = parse_pool(p.read_text(encoding="utf-8"))
    if not rows:
        sys.exit(f"Keine Karten in {p} gefunden (erwartet: Abschnitte 'Deck' und 'Sideboard').")
    signature = hashlib.sha1(json.dumps(rows, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    print(f"Kartenpool: {sum(r['qty'] for r in rows)} Karten aus {p}", file=sys.stderr)
    print("Lade Kartendaten und Bilder von Scryfall ...", file=sys.stderr)
    try:
        data = fetch_cards_cached(sorted({r["name"] for r in rows} | set(BASIC_LANDS)), refresh)
    except urllib.error.URLError as e:
        sys.exit(f"Scryfall nicht erreichbar: {e}")
    images = fetch_printing_images([(r["set"], r["number"]) for r in rows if r["set"] and r["number"]])
    cards = []
    basics = {n: {"name": n, "image": None, "core": 0, "pool": 0, "set": "", "number": ""} for n in BASIC_LANDS}
    for r in rows:
        sc = data.get(r["name"]) or data.get(r["name"].split(" // ")[0]) or {}
        image = images.get(f"{r['set']}/{r['number']}") or card_image_url(sc)
        if r["name"] in basics:
            b = basics[r["name"]]
            b["pool"] += r["qty"]
            b["core"] += r["qty"] if r["section"] == "deck" else 0
            b["image"] = b["image"] or image
            if not b["set"]:
                b["set"], b["number"] = r["set"], r["number"]
            continue
        type_line = sc.get("type_line") or ""
        empower = card_info(sc)[0].empower if sc else ()
        faces = sc.get("card_faces") or []
        colors = sc.get("colors") or (faces[0].get("colors") if faces else None) or []
        cards.append({
            "name": r["name"], "qty": r["qty"], "section": r["section"], "image": image, "colors": colors,
            "set": r["set"], "number": r["number"], "type": type_line,
            "cost": sc.get("mana_cost") or (faces[0].get("mana_cost") if faces else "") or "",
            "large": image.replace("/normal/", "/large/") if image else None,
            "land": "Land" in type_line.split("—")[0], "mv": sc.get("cmc") or 0, "found": bool(sc),
            "produces": sc.get("produced_mana") or (faces[0].get("produced_mana") if faces else None) or [],
            "kinds": type_kinds(type_line), "empower": bool(empower), "flow": flow_kinds(sc),
            # Loyalty, die beim Wirken bzw. Betreten sofort dazukommt (ohne X und ohne wiederkehrende Ausloeser)
            "empower_points": empower_points(empower),
        })
    order = {"deck": 0, "sideboard": 1}  # je Bereich: Nichtlaender nach Manawert, Laender zuletzt
    cards.sort(key=lambda c: (order.get(c["section"], 2), c["land"], c["mv"], c["name"]))
    for b in basics.values():
        b["image"] = b["image"] or card_image_url(data.get(b["name"]) or {})
        b["large"] = b["image"].replace("/normal/", "/large/") if b["image"] else None
    return cards, list(basics.values()), signature


def entries_from_marks(pool, marks, basics=None, cats=None):
    """Baut die Deck-Eintraege fuer die Simulation. marks: je Pool-Karte eine Liste mit einer Markierung je Kopie.
    basics: {Landname: {core, splash, nosplash}} mit der Menge je Gruppe.
    cats: {Kartenname: Kategorie}; wird an die Eintraege gehaengt (Abschnitt "Great in this deck!" im Bericht)."""
    cats = dict(cats or {})
    groups = {m: Counter() for m in MARKS}
    for card, ms in zip(pool, marks):
        for m in ms:
            groups[m][card["name"]] += 1
    for name, counts in (basics or {}).items():
        for g in GROUPS:
            if counts.get(g):
                groups[g][name] += counts[g]
    core = dict(groups["core"])
    if not groups["splash"] and not groups["nosplash"]:
        return [{"path": "", "name": "Core", "deck": core, "parts": [("Core", core)], "cats": cats, "role": "core"}]
    entries = []
    for label, key in (("Splash", "splash"), ("NoSplash", "nosplash")):
        part = dict(groups[key])
        deck = Counter(core)
        deck.update(part)
        entries.append({"path": "", "name": label, "deck": dict(deck), "parts": [("Core", dict(core)), (label, part)],
                        "cats": cats, "role": key})
    return entries


def parse_state(body, pool):
    """Liest und prueft den Stand der Seite (Markierungen, Standardlaender, Kategorien) aus einer Anfrage.
    Gibt (marks, basics, cats) zurueck; wirft ValueError/KeyError/TypeError bei ungueltigen Angaben.
    Unbekannte Karten und Kategorien in cats werden verworfen."""
    marks = body["marks"]
    if len(marks) != len(pool) or any(len(ms) != c["qty"] or any(m not in MARKS for m in ms)
                                      for ms, c in zip(marks, pool)):
        raise ValueError("Markierungen passen nicht zum Kartenpool")
    names = {c["name"] for c in pool}
    cats = {n: k for n, k in (body.get("cats") or {}).items() if n in names and k in CATEGORIES}
    basics = {}
    for name in BASIC_LANDS:
        c = (body.get("basics") or {}).get(name) or {}
        basics[name] = {g: int(c.get(g) or 0) for g in GROUPS}
        if any(not 0 <= v <= MAX_BASICS for v in basics[name].values()):
            raise ValueError(f"Anzahl {name}: erlaubt sind 0 bis {MAX_BASICS} je Gruppe")
    return marks, basics, cats


def parse_proposal_spec(spec):
    """Prueft die Angaben fuer den Deckvorschlag (Farben, Zielgroesse, Sortierung). Gibt (colors, target, sort)."""
    if not isinstance(spec, dict):
        raise ValueError("Angaben zum Deckvorschlag fehlen")
    colors = spec.get("colors", [])
    if not isinstance(colors, list) or any(c not in WUBRG or len(str(c)) != 1 for c in colors):
        raise ValueError("Unbekannte Farbe (erlaubt: W, U, B, R, G)")
    target, sort = int(spec.get("target") or 40), spec.get("sort") or "mv"
    if not 10 <= target <= 200:
        raise ValueError("Die Zielgröße muss zwischen 10 und 200 Karten liegen")
    if sort not in SORTS:
        raise ValueError("Unbekannte Sortierung")
    return colors, target, sort


MIN_PROPOSAL_CARDS = 8  # kleiner ist ein Deck nicht simulierbar (7 Starthandkarten plus ziehen)


class Job:
    """Eine Simulation im Hintergrund; Zustand fuer die Statusabfrage der Seite."""

    def __init__(self):
        self.lock = threading.Lock()
        self.state, self.message, self.started, self.finished = "idle", "", 0.0, 0.0
        self.report = None

    def status(self):
        with self.lock:
            end = self.finished if self.state in ("done", "error") else time.time()
            elapsed = round(end - self.started, 1) if self.started else 0.0
            return {"state": self.state, "message": self.message, "elapsed": elapsed}

    def start(self, work):
        with self.lock:
            if self.state == "running":
                return False
            self.state, self.message, self.started, self.report = "running", "Starte ...", time.time(), None
        threading.Thread(target=self._run, args=(work,), daemon=True).start()
        return True

    def progress(self, msg):
        print(msg, file=sys.stderr)
        with self.lock:
            self.message = msg

    def _run(self, work):
        try:
            report = work(self.progress)
            state, message = "done", "Fertig"
        except SystemExit as e:  # die Simulation meldet Fehler per sys.exit(Text)
            report, state, message = None, "error", str(e.code) if e.code is not None else "Abgebrochen"
        except Exception as e:  # unerwartet: Meldung zeigen, Details ins Terminal
            traceback.print_exc()
            report, state, message = None, "error", f"Unerwarteter Fehler: {e}"
        with self.lock:
            self.report, self.state, self.message, self.finished = report, state, message, time.time()


class LocalServer(http.server.ThreadingHTTPServer):
    # Unter Windows erlaubt SO_REUSEADDR, einen Port doppelt zu belegen: dann landet der Browser womoeglich bei einer
    # alten Instanz. Ohne Wiederverwendung schlaegt das Binden fehl und es wird ein freier Port gewaehlt.
    allow_reuse_address = False


def make_handler(app):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):  # keine Zugriffsprotokolle im Terminal
            pass

        def _send(self, body, ctype="text/html; charset=utf-8", code=200):
            data = body if isinstance(body, bytes) else body.encode("utf-8")
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
            if path == "/":
                self._send(render_page())
            elif path == "/api/pool":
                self._json({"cards": app["pool"], "basics": app["basics"], "sims": app["args"].sims,
                            "options": app["options"], "file": app["file"],
                            "signature": app["signature"]})
            elif path == "/howitworks.html":
                self._send(render_help_page())
            elif path == "/api/status":
                self._json(app["job"].status())
            elif path == "/report":
                rep = app["job"].report
                self._send(rep if rep else "<p>Noch kein Bericht vorhanden.</p>")
            else:
                self._send("Nicht gefunden", "text/plain; charset=utf-8", 404)

        def do_POST(self):
            path = self.path.split("?", 1)[0]
            if path == "/api/quit":
                self._json({"ok": True})
                threading.Thread(target=app["server"].shutdown, daemon=True).start()
                return
            if path not in ("/api/simulate", "/api/suggest", "/api/propose", "/api/lands", "/api/colors"):
                self._send("Nicht gefunden", "text/plain; charset=utf-8", 404)
                return
            pool = app["pool"]
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                marks, basics, cats = parse_state(body, pool)
                if path == "/api/suggest":
                    target, sort = int(body.get("target") or 40), body.get("sort") or "mv"
                    if not 10 <= target <= 200:
                        raise ValueError("Die Zielgröße muss zwischen 10 und 200 Karten liegen")
                    if sort not in SORTS:
                        raise ValueError("Unbekannte Sortierung")
                elif path == "/api/propose":
                    colors, target, sort = parse_proposal_spec(body)
                elif path == "/api/lands":
                    target = int(body.get("target") or 40)
                    if not 10 <= target <= 200:
                        raise ValueError("Die Zielgröße muss zwischen 10 und 200 Karten liegen")
                else:
                    sims = int(body.get("sims") or app["args"].sims)
                    if not 100 <= sims <= 100000:
                        raise ValueError("Anzahl der Spiele muss zwischen 100 und 100000 liegen")
                    proposal = None
                    if body.get("proposal"):
                        colors, target, sort = parse_proposal_spec(body["proposal"])
                        proposal = propose(pool, marks, cats, colors, target, sort)
                        if proposal["summary"]["size"] < MIN_PROPOSAL_CARDS:
                            raise ValueError("Der Deckvorschlag ist zu klein zum Simulieren (weniger als "
                                             f"{MIN_PROPOSAL_CARDS} Karten): Bitte Farben und Kategorien prüfen.")
            except (ValueError, KeyError, TypeError) as e:
                self._json({"ok": False, "error": str(e)}, 400)
                return
            if path == "/api/suggest":
                result = suggest(pool, marks, basics, cats, target, sort)
                self._json({"ok": True, "marks": result["marks"], "summary": result["summary"]})
                return
            if path == "/api/lands":
                self._json({"ok": True, **recommend(pool, marks, target)})
                return
            if path == "/api/colors":
                self._json({"ok": True, **color_overview(pool, marks, basics)})
                return
            if path == "/api/propose":
                result = propose(pool, marks, cats, colors, target, sort)
                self._json({"ok": True, "deck": result["deck"], "summary": result["summary"]})
                return
            run_args = argparse.Namespace(**vars(app["args"]))
            run_args.sims, run_args.core = sims, "Core"  # core: Herkunft der Karten (Core/Splash/NoSplash) im Bericht

            def work(progress):
                entries = entries_from_marks(pool, marks, basics, cats)
                if proposal:
                    deck = dict(proposal["deck"])
                    entries.append({"path": "", "name": "Vorschlag", "deck": deck, "parts": [("Vorschlag", deck)],
                                    "cats": dict(cats), "role": "proposal"})
                html = app["simulate"](entries, run_args, progress)
                app["save"](html, run_args)
                return html

            if not app["job"].start(work):
                self._json({"ok": False, "error": "Es laeuft bereits eine Simulation"}, 409)
                return
            self._json({"ok": True})

    return Handler


def serve(args, simulate, save):
    pool, basics, signature = load_pool(args.drafthelper, args.neu_laden)
    options = sorted(set(SIM_OPTIONS) | {args.sims})
    app = {"pool": pool, "basics": basics, "args": args, "simulate": simulate, "save": save, "job": Job(), "options": options,
           "file": pathlib.Path(args.drafthelper).name, "signature": signature}
    try:
        server = LocalServer(("127.0.0.1", PORT), make_handler(app))
    except OSError:  # Port belegt: freien Port waehlen lassen
        server = LocalServer(("127.0.0.1", 0), make_handler(app))
    app["server"] = server
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Draft-Helper laeuft: {url}", file=sys.stderr)
    print("Zum Beenden: Button 'Beenden' auf der Seite oder Strg+C hier im Fenster.", file=sys.stderr)
    if not args.nicht_oeffnen:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    print("Draft-Helper beendet.", file=sys.stderr)


PAGE = r"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Draft-Helper</title>
<style>
:root{--bg:#f4f6f9;--card:#fff;--ink:#1d2430;--muted:#667085;--line:#d9dee7;
--core:#2f6fd6;--splash:#d6453b;--nosplash:#d9a400;--off:#8a93a3}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,"Segoe UI",Roboto,sans-serif}
header.bar{position:sticky;top:0;z-index:5;background:#fff;border-bottom:1px solid var(--line);padding:10px 20px;
  display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center}
header.bar h1{font-size:18px;margin:0}
.counts{display:flex;gap:8px;flex-wrap:wrap}
.chip{border-radius:999px;padding:3px 11px;font-weight:600;color:#fff;font-size:13px}
.chip.core{background:var(--core)}.chip.splash{background:var(--splash)}
.chip.nosplash{background:var(--nosplash);color:#2a2000}.chip.off{background:var(--off)}
.sizes{color:var(--muted);font-size:13px}
.sizes b{color:var(--ink)}
.warn{color:#b42318;font-weight:600}
.spacer{flex:1}
button{font:inherit;cursor:pointer}
.btn{border:1px solid var(--line);background:#fff;border-radius:8px;padding:8px 14px}
.btn.primary{background:var(--core);border-color:var(--core);color:#fff;font-weight:700;padding:9px 20px}
.btn:disabled{opacity:.55;cursor:default}
select{font:inherit;padding:7px;border-radius:8px;border:1px solid var(--line);background:#fff}
main{padding:16px 20px 60px;max-width:1500px;margin:0 auto}
.help{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin-bottom:6px}
.help ul{margin:6px 0 0;padding-left:20px}
h2{margin:26px 0 10px;font-size:18px}
h2 small{color:var(--muted);font-weight:400}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(168px,1fr));gap:14px}
.tile{background:var(--card);border:3px solid var(--line);border-radius:12px;padding:6px;transition:opacity .15s}
.tile.m-core{border-color:var(--core)}.tile.m-splash{border-color:var(--splash)}
.tile.m-nosplash{border-color:var(--nosplash)}.tile.m-off{border-color:var(--line);opacity:.55}
.tile img{width:100%;display:block;border-radius:8px;cursor:zoom-in;aspect-ratio:488/680;background:#e9edf3}
.ph{aspect-ratio:488/680;background:#e9edf3;border-radius:8px;display:flex;align-items:center;justify-content:center;
  text-align:center;padding:8px;color:var(--muted)}
.cap{font-size:12.5px;margin:6px 2px 5px;display:flex;justify-content:space-between;gap:6px}
.cap span{color:var(--muted);white-space:nowrap}
.seg{display:grid;grid-template-columns:1fr 1fr;gap:4px}
.seg button{border:1px solid var(--line);background:#f8f9fb;border-radius:6px;padding:5px 2px;font-size:12.5px}
.seg button.on[data-m=core]{background:var(--core);border-color:var(--core);color:#fff}
.seg button.on[data-m=splash]{background:var(--splash);border-color:var(--splash);color:#fff}
.seg button.on[data-m=nosplash]{background:var(--nosplash);border-color:var(--nosplash);color:#2a2000}
.seg button.on[data-m=off]{background:var(--off);border-color:var(--off);color:#fff}
#overlay,#lightbox{position:fixed;inset:0;display:none;z-index:20}
#overlay{background:rgba(20,26,38,.72);align-items:center;justify-content:center}
#overlay .box{background:#fff;border-radius:14px;padding:26px 32px;max-width:520px;text-align:center}
#overlay.show,#lightbox.show{display:flex}
#lightbox{background:rgba(0,0,0,.8);align-items:center;justify-content:center;cursor:zoom-out}
#lightbox img{max-height:92vh;max-width:92vw;border-radius:14px}
.spin{width:38px;height:38px;border:5px solid #dfe5ee;border-top-color:var(--core);border-radius:50%;
  animation:sp 1s linear infinite;margin:0 auto 12px}
@keyframes sp{to{transform:rotate(360deg)}}
#results{display:none;position:fixed;inset:0;z-index:10;background:var(--bg);flex-direction:column}
#results.show{display:flex}
#results .rbar{padding:10px 20px;background:#fff;border-bottom:1px solid var(--line);display:flex;gap:12px;align-items:center}
#results iframe{flex:1;border:0;width:100%}
.basics{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px}
.bl{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px;display:flex;gap:10px}
.bl img{width:84px;border-radius:6px;cursor:zoom-in;align-self:flex-start;aspect-ratio:488/680;background:#e9edf3}
.bl .bn{flex:1}
.bl b{display:block;margin-bottom:2px}
.bl .pooln{font-size:12px;color:var(--muted);margin-bottom:6px}
.step{display:flex;align-items:center;gap:6px;margin:4px 0}
.step .lab{width:66px;font-size:12.5px;font-weight:600}
.step .lab.core{color:var(--core)}.step .lab.splash{color:var(--splash)}.step .lab.nosplash{color:#a37c00}
.step button{width:28px;height:28px;border:1px solid var(--line);background:#f8f9fb;border-radius:6px;font-size:16px;line-height:1;padding:0}
.step .val{min-width:24px;text-align:center;font-weight:700}
.imgw{position:relative}
.badge{position:absolute;top:6px;left:6px;border-radius:999px;padding:2px 9px;font-size:12px;font-weight:700;
  color:#fff;box-shadow:0 1px 3px rgba(0,0,0,.35)}
.tile.c-splashworthy .badge,.cdot.splashworthy{background:#e0a800;color:#2d2100}
.tile.c-mustplay .badge,.cdot.mustplay{background:#2e9e5b}
.tile.c-filler .badge,.cdot.filler{background:#6b7d99}
.tile.c-neverplay .badge,.cdot.neverplay{background:#8b2f2f}
.tile.c-splashworthy{box-shadow:0 0 0 3px #ffc83d88}
.tile.c-mustplay{box-shadow:0 0 0 3px #2e9e5b55}
.tile.c-neverplay img{filter:grayscale(.75)}
.catsel{width:100%;margin-top:5px;padding:4px 6px;font-size:12.5px}
.chip.cat{color:#fff}
.chip.cat.splashworthy{background:#e0a800;color:#2d2100}.chip.cat.mustplay{background:#2e9e5b}
.chip.cat.filler{background:#6b7d99}.chip.cat.neverplay{background:#8b2f2f}
.filter{display:flex;align-items:center;gap:6px;font-size:13px}
.layout{display:grid;grid-template-columns:400px 1fr;gap:20px;align-items:start;margin-top:14px}
.side{position:sticky;top:calc(var(--hbar,70px) + 12px);background:#fff;border:1px solid var(--line);border-radius:12px;
  padding:12px;max-height:calc(100vh - var(--hbar,70px) - 24px);overflow:auto}
.side h3{margin:0 0 6px;font-size:15px}
.side table{width:100%;border-collapse:collapse;font-size:12.5px}
.side th,.side td{padding:3px 2px;text-align:center;border-bottom:1px solid #eef0f4}
.side th{font-weight:700;color:var(--muted);font-size:11.5px}
.side th.grp{border-bottom:2px solid var(--line)}
.side td.l,.side th.l{text-align:left}
.side td.z{color:#c3c8d2}
.side tr.tot td{font-weight:700;border-top:2px solid var(--line)}
.side .note{font-size:11.5px;color:var(--muted);margin-top:8px;line-height:1.35}
.side td.good{background:#d9f3e4;color:#146c3d;font-weight:700}.side td.warn{background:#ffedc2;color:#7a5200;font-weight:700}
.side td.bad{background:#fde0e0;color:#a82a2a;font-weight:700}
.side .m.ms{margin-right:4px}.side .csym{display:inline-block;min-width:18px;font-weight:700}
.cdot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:baseline;border:1px solid rgba(0,0,0,.2)}
@media(max-width:1100px){.layout{grid-template-columns:1fr}.side{position:static;max-height:none}}
.toolbar{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;margin:0 0 12px}
.toolbar input[type=search]{flex:1;min-width:200px;font:inherit;padding:7px 10px;border-radius:8px;border:1px solid var(--line);background:#fff}
.toolbar label{font-size:13px;display:flex;align-items:center;gap:6px}
.curve .bars{display:flex;gap:6px;align-items:flex-end}
.curve .bcol{flex:1;text-align:center}
.curve .pair{display:flex;gap:2px;align-items:flex-end;justify-content:center;height:96px}
.curve .bw{display:flex;flex-direction:column;align-items:center;justify-content:flex-end;width:13px}
.curve .bv{font-size:10.5px;color:var(--muted);height:13px;line-height:13px}
.curve .bar{width:13px;border-radius:3px 3px 0 0;min-height:1px}
.curve .bar.splash{background:var(--splash)}.curve .bar.nosplash{background:var(--nosplash)}
.curve .bx{font-size:11.5px;color:var(--muted);margin-top:3px}
.curve .legend{font-size:11.5px;color:var(--muted);margin-top:8px;line-height:1.5}
.curve .legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;vertical-align:baseline}
#exportbox{position:fixed;inset:0;display:none;z-index:25;background:rgba(20,26,38,.72);align-items:flex-start;
  justify-content:center;padding:30px 16px;overflow:auto}
#exportbox.show{display:flex}
.xbox{background:#fff;border-radius:14px;padding:18px 22px;max-width:980px;width:100%}
.xhead{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.xnote{font-size:13px;color:var(--muted);margin:0 0 12px}
.xcols{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}
.xcol h3{margin:0 0 2px;font-size:15px}
.xcol .xcount{font-size:12.5px;color:var(--muted);margin-bottom:6px}
.xcol textarea{width:100%;height:340px;font:12.5px/1.45 ui-monospace,Consolas,monospace;border:1px solid var(--line);
  border-radius:8px;padding:8px;resize:vertical}
.xcol .xbtns{display:flex;gap:8px;margin-top:8px}
.suggestbar{display:flex;flex-wrap:wrap;gap:10px 14px;align-items:center;background:#fff;border:1px solid var(--line);
  border-radius:10px;padding:10px 14px;margin:0 0 12px}
.suggestbar label{font-size:13px;display:flex;align-items:center;gap:6px}
.suggestbar input[type=number]{width:72px;font:inherit;padding:6px 8px;border-radius:8px;border:1px solid var(--line)}
.suggestbar .hint{font-size:12.5px;color:var(--muted);flex:1;min-width:220px}
.colpick{display:flex;gap:6px;align-items:center;font-size:13px}
.colpick label{display:flex;align-items:center;gap:3px;border:1px solid var(--line);border-radius:999px;padding:2px 9px 2px 6px;
  background:#fff;cursor:pointer}
.colpick input{margin:0}
.pcols{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:4px 24px;margin:6px 0}
.pcol h4{margin:4px 0;font-size:13.5px}
.pcol div{font-size:13px}
.ptag{margin-left:6px;font-size:11px;font-weight:700;color:#fff;background:var(--splash);border-radius:999px;padding:0 7px}
.nhint{color:#8a5a00;font-weight:600}
.nmuted{color:var(--muted)}
.nsub{padding-left:18px;font-size:13.5px}
.notice{display:none;background:#eef4ff;border:1px solid #b7cdf5;border-radius:10px;padding:10px 14px;margin:0 0 12px;
  font-size:13.5px;line-height:1.55}
.notice .nh{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:4px}
.notice .nw{color:#b42318;font-weight:600}
.types table{width:100%;border-collapse:collapse;font-size:12.5px}
.types th,.types td{padding:3px 4px;text-align:right;border-bottom:1px solid #eef0f4}
.types th{font-weight:700;font-size:11.5px;color:var(--muted)}
.types td.l,.types th.l{text-align:left}
.types td.sub{padding-left:14px;color:var(--muted)}
.types tr.sep td{border-top:2px solid var(--line)}
.types .diff{font-weight:700}
.cc-controls{display:flex;flex-wrap:wrap;gap:6px 12px;margin:4px 0 8px;font-size:12px}
.cc-controls label{display:flex;align-items:center;gap:5px}
.cc-controls select{font-size:12px;padding:3px 6px}
.ccbars{display:flex;gap:6px;align-items:flex-end;height:112px}
.cccol{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end}
.cctop{font-size:10.5px;color:var(--muted);height:13px;line-height:13px}
.ccstack{display:flex;justify-content:center;width:100%}
.ccstack.stacked{flex-direction:column-reverse;align-items:center}
.ccstack.percolor{align-items:flex-end;gap:1px}
.ccseg{border:1px solid rgba(0,0,0,.25)}
.ccstack.stacked .ccseg{width:22px}
.ccstack.percolor .ccseg{width:7px}
.ccx{font-size:11.5px;color:var(--muted);margin-top:3px}
.ccleg{display:flex;flex-wrap:wrap;gap:3px 10px;font-size:11.5px;color:var(--muted);margin-top:8px}
.ccleg i{display:inline-block;width:10px;height:10px;border:1px solid rgba(0,0,0,.25);margin-right:4px;border-radius:2px}
.ccnote{font-size:11.5px;color:var(--muted);margin-top:6px;line-height:1.4}
.err{background:#fef3f2;border:1px solid #fda29b;color:#b42318;border-radius:10px;padding:12px 16px;margin:10px 0;display:none}
/*SYMBOL_CSS*/
</style></head><body>
<header class="bar">
  <h1>Draft-Helper</h1>
  <div class="counts" id="counts"></div>
  <div class="sizes" id="sizes"></div>
  <label class="filter">Karten zeigen
    <select id="catfilter" title="Blendet Karten anderer Kategorien aus"></select></label>
  <div class="spacer"></div>
  <label>Spiele pro Modus <select id="sims"></select></label>
  <button class="btn" id="export" title="Deckliste der Varianten zum Kopieren oder Speichern">Deckliste exportieren</button>
  <button class="btn primary" id="go">Simulieren</button>
  <button class="btn" id="quit" title="Draft-Helper beenden">Beenden</button>
</header>
<main>
  <div class="help"><b>So geht's:</b> Ordne unter jeder Karte zu (<b>Core</b>, <b>Splash</b>, <b>NoSplash</b> oder
    <b>Aus</b>), wähle bei Bedarf eine <b>Kategorie</b> und stelle oben die Standardländer ein. Danach auf
    <b>Simulieren</b> klicken. Alle Regeln (Zuordnung, Kategorien, Deckvorschlag, Übersichten):
    <a href="/howitworks.html#hiw-drafthelper" target="_blank">So funktioniert es</a>.</div>
  <div class="err" id="err"></div>
  <div class="layout">
    <aside class="side"><h3>Übersicht nach Farbe</h3><div id="overview"></div>
      <h3 style="margin-top:18px">Mana-Kurve</h3><div id="curve" class="curve"></div>
      <h3 style="margin-top:18px">Mana-Kurve nach Farben</h3>
      <div class="cc-controls">
        <label>Variante <select id="ccvar"><option value="splash">Splash</option>
          <option value="nosplash">NoSplash</option></select></label>
        <label>Ansicht <select id="ccmode">
          <option value="stacked">Mehrfarbige gesondert</option>
          <option value="percolor">Je Farbe (Mehrfarbige in jeder Farbe)</option></select></label>
      </div>
      <div id="colorcurve" class="colorcurve"></div>
      <h3 style="margin-top:18px">Farben und Quellen</h3>
      <div class="cc-controls"><label>Variante <select id="fqvar"><option value="splash">Splash</option>
          <option value="nosplash">NoSplash</option></select></label></div>
      <div id="colorsrc"></div>
      <h3 style="margin-top:18px">Kartentypen je Variante</h3><div id="types"></div></aside>
    <div>
      <div class="toolbar">
        <input type="search" id="search" placeholder="Karte suchen (Name oder englischer Typ, z. B. Creature, Instant, Land)">
        <label>Sortierung <select id="sort">
          <option value="mv">Manawert</option><option value="name">Name</option><option value="color">Farbe</option>
          <option value="mark">Zuordnung</option><option value="cat">Kategorie</option></select></label>
      </div>
      <div class="suggestbar">
        <label>Zielgröße <input type="number" id="target" value="40" min="10" max="200"
          title="Kartenzahl je Variante, alle Länder eingerechnet"> Karten</label>
        <span class="colpick" title="Farben, die im Deckvorschlag gespielt werden">Farben:
          <label><input type="checkbox" value="W"> W</label><label><input type="checkbox" value="U"> U</label>
          <label><input type="checkbox" value="B"> B</label><label><input type="checkbox" value="R"> R</label>
          <label><input type="checkbox" value="G"> G</label></span>
        <button class="btn" id="propose" title="Baut aus den Kategorien ein eigenes Deck mit Ländern">Deckvorschlag erstellen</button>
        <label title="Simuliert den Deckvorschlag als weitere Variante neben Splash und NoSplash"><input type="checkbox"
          id="simprop"> mitsimulieren</label>
        <button class="btn" id="suggest" title="Setzt die Zuordnung Core/Splash/NoSplash nach den Kategorien und füllt mit Filler auf">Zuordnung nach Kategorien setzen</button>
        <button class="btn" id="lands" title="Setzt Standardländer je Gruppe und ordnet passende Nicht-Standardländer zu (nach der aktuellen Zuordnung)">Länder empfehlen</button>
        <button class="btn" id="undo" style="display:none">↶ Rückgängig</button>
        <span class="hint">Deckvorschlag: eigenes Deck aus den Kategorien in den gewählten Farben, mit Ländern auf die
          Faustregel aufgefüllt; die Zuordnung bleibt unverändert. MustPlay und Filler nur in den gewählten Farben,
          Splashworthy auch außerhalb.</span>
      </div>
      <div class="notice" id="proposal"></div>
      <div class="notice" id="notice"></div>
      <h2 style="margin-top:0">Standardländer <small>(Menge je Gruppe – auch Länder, die nicht im Pool sind, lassen sich hinzufügen)</small></h2>
      <div class="basics" id="basics"></div>
      <div id="nonbasics"></div>
      <div id="sections"></div>
    </div>
  </div>
</main>
<div id="overlay"><div class="box"><div class="spin"></div><b>Simulation läuft …</b>
  <div id="ovmsg" style="margin-top:8px"></div><div id="ovtime" style="color:var(--muted);margin-top:4px"></div></div></div>
<div id="lightbox"><img alt=""></div>
<div id="exportbox"><div class="xbox"><div class="xhead"><b style="font-size:17px">Deckliste exportieren</b>
  <button class="btn" id="xclose">Schließen</button></div>
  <p class="xnote">Format wie beim Import in MTG Arena und MTGO (Abschnitte Deck und Sideboard). Das Deck besteht aus
    Core plus der Gruppe der Variante samt Standardländern; Sideboard sind alle übrigen Karten aus Deck und Sideboard der Datei.</p>
  <div class="xcols" id="xcols"></div></div></div>
<div id="results"><div class="rbar"><button class="btn" id="back">← Zurück zu den Karten</button>
  <span id="rnote" style="color:var(--muted)"></span></div><iframe id="frame" title="Bericht"></iframe></div>
<script>
const LABEL={core:"Core",splash:"Splash",nosplash:"NoSplash",off:"Aus"};
const SYMBOLS=[];  // vorhandene Original-Manasymbole (vom Server eingesetzt, siehe render_page)
function manaSym(k){if(!SYMBOLS.includes(k))return null;const s=el("span","m ms ms-"+k);s.title="{"+k+"}";return s}
let pool=[], state=[], basics=[], storeKey="", searchQ="", sortKey="mv", proposal=null, colorsFromSave=false;
const $=id=>document.getElementById(id);
const el=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!=null)e.textContent=text;return e};

const GROUPS=["core","splash","nosplash"];
// Kategorie je Karte (nicht je Kopie), hoechstens eine. Weitere Kategorien: hier einen Eintrag ergaenzen.
const CATS=[
 {key:"splashworthy",abbr:"★",label:"Splashworthy",hint:"Entscheidet Spiele allein – soll auf jeden Fall rein, auch wenn wir die Farbe nicht spielen"},
 {key:"mustplay",abbr:"MP",label:"MustPlay",hint:"Wird auf jeden Fall gespielt, wenn wir diese Farbe spielen"},
 {key:"filler",abbr:"Fi",label:"Filler",hint:"Füllt das Deck auf, wenn wir die Farbe spielen und nicht splashen"},
 {key:"neverplay",abbr:"NP",label:"NeverPlay",hint:"Zu schlecht oder zu situativ, wird nicht gespielt"}];
let cats={};  // Kartenname -> Kategorie
const catOf=name=>cats[name]||"";
function save(){try{localStorage.setItem(storeKey,JSON.stringify({marks:state.map(t=>t.mark),
  basics:basics.map(b=>GROUPS.map(g=>b[g])),cats,target:+$("target").value||40,colors:chosenColors()}))}catch(e){}}
function restore(){try{const s=JSON.parse(localStorage.getItem(storeKey)||"null");if(!s)return;
  if(Array.isArray(s.marks)&&s.marks.length===state.length&&s.marks.every(m=>m in LABEL))s.marks.forEach((m,i)=>state[i].mark=m);
  const names=new Set(pool.map(c=>c.name)),keys=new Set(CATS.map(c=>c.key));
  if(s.cats&&typeof s.cats==="object")for(const [n,k] of Object.entries(s.cats))if(names.has(n)&&keys.has(k))cats[n]=k;
  if(s.tags&&typeof s.tags==="object")for(const [n,v] of Object.entries(s.tags))  // aelterer Speicherstand
    if(names.has(n)&&!cats[n]&&Array.isArray(v)&&keys.has(v[0]))cats[n]=v[0];
  if(Number.isInteger(+s.target)&&s.target>=10&&s.target<=200)$("target").value=s.target;
  if(Array.isArray(s.colors)){setColors(s.colors);colorsFromSave=true}
  if(Array.isArray(s.basics)&&s.basics.length===basics.length)
    s.basics.forEach((v,i)=>GROUPS.forEach((g,k)=>{const n=+v[k];if(Number.isInteger(n)&&n>=0&&n<=40)basics[i][g]=n}))}catch(e){}}
function buildBasics(){
  const box=$("basics");box.textContent="";
  for(const b of basics){
    const d=el("div","bl");
    if(b.image){const im=el("img");im.src=b.image;im.alt=b.name;im.loading="lazy";
      im.onclick=()=>{$("lightbox").querySelector("img").src=b.large||b.image;$("lightbox").classList.add("show")};d.appendChild(im)}
    const r=el("div","bn");r.appendChild(el("b",null,b.name));
    r.appendChild(el("div","pooln",b.pool?"Im Pool: "+b.pool:"Nicht im Pool"));
    for(const g of GROUPS){
      const row=el("div","step");row.appendChild(el("span","lab "+g,LABEL[g]));
      const minus=el("button",null,"−"),val=el("span","val",String(b[g])),plus=el("button",null,"+");
      const set=n=>{b[g]=Math.max(0,Math.min(40,n));val.textContent=b[g];summary();save()};
      minus.onclick=()=>set(b[g]-1);plus.onclick=()=>set(b[g]+1);
      row.append(minus,val,plus);r.appendChild(row)}
    d.appendChild(r);box.appendChild(d)}
}

// Nicht-Standardlaender stehen in einem eigenen Bereich direkt unter den Standardlaendern. Die Reihenfolge in
// state bleibt die des Pools (Deck, Sideboard), weil der gespeicherte Stand und die Anfragen sie benutzen.
function build(){
  state=[];const box=$("sections");box.textContent="";const nb=$("nonbasics");nb.textContent="";
  const grids={};
  const section=(parent,key,title,cards,note)=>{
    if(!cards.length)return;
    const h=el("h2",null,title+" ");
    const n=cards.reduce((m,c)=>m+c.qty,0);
    h.appendChild(el("small",null,"("+n+(n===1?" Karte":" Karten")+(note||"")+")"));
    parent.appendChild(h);grids[key]=el("div","grid");parent.appendChild(grids[key]);
  };
  section(nb,"land","Nicht-Standardländer",pool.filter(c=>c.land),", aus Deck und Sideboard der Datei");
  section(box,"deck","Deck",pool.filter(c=>c.section==="deck"&&!c.land));
  section(box,"sideboard","Sideboard",pool.filter(c=>c.section==="sideboard"&&!c.land));
  for(const c of pool)for(let k=1;k<=c.qty;k++)state.push({card:c,copy:k,mark:c.section==="deck"?"core":"off"});
  restore();buildBasics();
  for(const t of state){t.grid=grids[t.card.land?"land":t.card.section];t.grid.appendChild(tile(t))}
  refresh();
}
function tile(t){
  const d=el("div","tile");t.node=d;
  const w=el("div","imgw");
  if(t.card.image){const im=el("img");im.src=t.card.image;im.alt=t.card.name;im.loading="lazy";
    im.onclick=()=>{$("lightbox").querySelector("img").src=t.card.large||t.card.image;$("lightbox").classList.add("show")};
    w.appendChild(im)}
  else w.appendChild(el("div","ph",t.card.name));
  t.badge=el("div","badge");w.appendChild(t.badge);
  d.appendChild(w);
  const cap=el("div","cap");cap.appendChild(el("b",null,t.card.name));
  if(t.card.qty>1)cap.appendChild(el("span",null,t.copy+"/"+t.card.qty));
  d.appendChild(cap);
  const seg=el("div","seg");
  for(const m of ["core","splash","nosplash","off"]){
    const b=el("button",null,LABEL[m]);b.dataset.m=m;b.onclick=()=>{t.mark=m;paint(t);summary();save()};seg.appendChild(b)}
  d.appendChild(seg);
  const sel=el("select","catsel");sel.title="Kategorie dieser Karte (gilt für alle Kopien)";
  const o0=el("option",null,"Kategorie: –");o0.value="";sel.appendChild(o0);
  for(const c of CATS){const o=el("option",null,c.abbr+" "+c.label);o.value=c.key;o.title=c.hint;sel.appendChild(o)}
  sel.onchange=()=>setCat(t.card.name,sel.value);t.sel=sel;d.appendChild(sel);
  paint(t);return d;
}
function paint(t){
  const k=catOf(t.card.name),c=CATS.find(x=>x.key===k),f=$("catfilter").value;
  const hidden=(f&&(f==="none"?k:k!==f))||(searchQ&&!((t.card.name+" "+(t.card.type||"")).toLowerCase().includes(searchQ)));
  t.node.className="tile m-"+t.mark+(k?" c-"+k:"");
  t.badge.textContent=c?c.abbr+" "+c.label:"";t.badge.style.display=c?"":"none";
  t.sel.value=k;
  t.node.querySelectorAll(".seg button").forEach(b=>b.classList.toggle("on",b.dataset.m===t.mark));
  t.node.style.display=hidden?"none":""}
function setCat(name,key){
  if(key)cats[name]=key;else delete cats[name];
  state.filter(t=>t.card.name===name).forEach(paint);summary();save()}
function refresh(){state.forEach(paint);summary()}
function summary(){
  const n={core:0,splash:0,nosplash:0,off:0};state.forEach(t=>n[t.mark]++);
  basics.forEach(b=>GROUPS.forEach(g=>n[g]+=b[g]));
  const c=$("counts");c.textContent="";
  for(const m of ["core","splash","nosplash","off"])c.appendChild(el("span","chip "+m,LABEL[m]+" "+n[m]));
  for(const cat of CATS){const k=state.filter(t=>catOf(t.card.name)===cat.key).length;
    if(k)c.appendChild(el("span","chip cat "+cat.key,cat.abbr+" "+cat.label+" "+k))}
  const a=n.core+n.splash,b=n.core+n.nosplash,s=$("sizes");s.textContent="";
  s.appendChild(document.createTextNode("Splash-Variante: "));s.appendChild(el("b",null,a+" Karten"));
  s.appendChild(document.createTextNode(" · NoSplash-Variante: "));s.appendChild(el("b",null,b+" Karten"));
  if(a!==b)s.appendChild(el("span","warn","  – unterschiedlich groß"));
  overview();curve();typeOverview();renderColorCurve();scheduleColors();
}
// Farben und Quellen: gerechnet auf dem Server (components/landadvice.py, wie Land-Empfehlung und Bericht)
let colorTimer=null,colorData=null;
function scheduleColors(){clearTimeout(colorTimer);colorTimer=setTimeout(loadColors,200)}
async function loadColors(){
  try{const r=await api("/api/colors",{marks:marksPerCard(),basics:basicsBody(),cats});if(r.ok){colorData=r;renderColors()}}
  catch(e){}
}
function renderColors(){
  const box=$("colorsrc");box.textContent="";if(!colorData)return;
  const vs=colorData.variants,sel=$("fqvar");
  sel.parentNode.style.display=vs.length>1?"":"none";
  const v=vs.length>1?(vs.find(x=>x.key===sel.value)||vs[0]):vs[0];
  if(!v.rows.length){box.appendChild(el("div","note","Keine farbigen Karten oder Quellen in dieser Variante."));return}
  const tb=el("table"),hr=el("tr");
  [["Farbe","l",""],["Symbole","","Farbsymbole, die die Karten zwingend verlangen ({R}{R} zählt 2, Hybrid nicht)"],
   ["Karten","","Karten, die die Farbe zwingend verlangen"],["Quellen","","Standardländer der Variante und zugeordnete Nicht-Standardländer"],
   ["Ø pünktlich","","Chance, die Farbsymbole einer Karte bis Runde = Manawert zu haben (Play), gemittelt über die Karten der Farbe"]]
    .forEach(([t,cls,tip])=>{const h=el("th",cls||null,t);if(tip)h.title=tip;hr.appendChild(h)});
  const th=el("thead");th.appendChild(hr);tb.appendChild(th);
  const body=el("tbody");
  for(const r of v.rows){
    const tr=el("tr"),lab=el("td","l");
    lab.appendChild(manaSym(r.color)||el("span","csym",r.color));lab.append(COLOR_NAME[r.color]);tr.appendChild(lab);
    tr.appendChild(el("td",r.pips?null:"z",r.pips?String(r.pips):"·"));
    tr.appendChild(el("td",r.cards?null:"z",r.cards?String(r.cards):"·"));
    const src=el("td",r.sources?null:"z",r.sources?String(r.sources):"0");
    if(r.nonbasic){src.appendChild(el("small",null," ("+r.nonbasic+" NS)"));src.title="davon "+r.nonbasic+" Nicht-Standardländer"}
    tr.appendChild(src);
    const p=r.avg;
    const pc=el("td",p===null?"z":p>=0.9?"good":p>=0.8?"warn":"bad",p===null?"–":Math.round(p*100)+" %");
    if(r.worst)pc.title="Am knappsten: "+r.worst.name+" ("+Math.round(r.worst.p*100)+" %)";
    tr.appendChild(pc);body.appendChild(tr);
  }
  tb.appendChild(body);box.appendChild(tb);
  box.appendChild(el("div","note",v.label+": "+v.deck+" Karten. NS = Nicht-Standardländer. Ø pünktlich wie in der "+
    "Farbverteilung des Berichts; Ampel grün ab 90 %, gelb ab 80 %. Mit der Maus über dem Wert: die knappste Karte."));
}
// Mana-Kurve: Nichtland-Karten je Manawert, Splash- und NoSplash-Variante nebeneinander
function curve(){
  const B=7,cnt={splash:Array(B).fill(0),nosplash:Array(B).fill(0)},sum={splash:0,nosplash:0},num={splash:0,nosplash:0};
  for(const t of state){if(t.card.land||t.mark==="off")continue;const i=Math.min(Math.round(t.card.mv),B-1);
    for(const g of ["splash","nosplash"])if(t.mark==="core"||t.mark===g){cnt[g][i]++;sum[g]+=t.card.mv;num[g]++}}
  const max=Math.max(1,...cnt.splash,...cnt.nosplash),box=$("curve");box.textContent="";
  const bars=el("div","bars");
  for(let i=0;i<B;i++){
    const col=el("div","bcol"),pair=el("div","pair");
    for(const g of ["splash","nosplash"]){
      const v=cnt[g][i],w=el("div","bw"),bar=el("div","bar "+g);
      bar.style.height=Math.round(v/max*72)+"px";bar.title=(g==="splash"?"Splash":"NoSplash")+": "+v+" Karten";
      w.append(el("span","bv",v?String(v):""),bar);pair.appendChild(w)}
    col.append(pair,el("div","bx",i===B-1?(B-1)+"+":String(i)));bars.appendChild(col)}
  box.appendChild(bars);
  const avg=g=>num[g]?(sum[g]/num[g]).toFixed(2).replace(".",","):"–";
  const lg=el("div","legend");
  const i1=el("i");i1.style.background="var(--splash)";const i2=el("i");i2.style.background="var(--nosplash)";
  lg.append(i1,"Splash-Variante: "+num.splash+" Karten, Ø Manawert "+avg("splash"),document.createElement("br"),
            i2,"NoSplash-Variante: "+num.nosplash+" Karten, Ø Manawert "+avg("nosplash"),document.createElement("br"),
            "ohne Länder; Manawert 6+ zusammengefasst");
  box.appendChild(lg);
}
// BEGIN colorCurve
// Mana-Kurve nach Farben fuer eine Variante. mode "stacked": mehrfarbige Karten bilden ein eigenes Segment "M" (jede
// Karte steht genau einmal); "percolor": eine mehrfarbige Karte zaehlt bei jeder ihrer Farben (Balken nebeneinander).
const CURVE_BUCKETS=7;
const WUBRG="WUBRG";
function colorCurve(copies,variant,mode){
  const keys=mode==="stacked"?["W","U","B","R","G","M","C"]:["W","U","B","R","G","C"];
  const buckets=[];
  for(let i=0;i<CURVE_BUCKETS;i++){const b={};keys.forEach(k=>{b[k]=0});buckets.push(b)}
  const pairs={};let total=0,multi=0,colorless=0;
  for(const c of copies){
    if(c.land||c.mark==="off"||(c.mark!=="core"&&c.mark!==variant))continue;
    const i=Math.min(Math.round(c.mv||0),CURVE_BUCKETS-1);
    const cols=(c.colors||[]).filter(x=>WUBRG.includes(x)).sort((a,b)=>WUBRG.indexOf(a)-WUBRG.indexOf(b));
    total++;
    if(!cols.length){buckets[i].C++;colorless++}
    else if(cols.length===1){buckets[i][cols[0]]++}
    else{
      multi++;const key=cols.join("/");pairs[key]=(pairs[key]||0)+1;
      if(mode==="stacked")buckets[i].M++;else cols.forEach(x=>{buckets[i][x]++});
    }
  }
  let max=1;
  for(const b of buckets){
    const h=mode==="stacked"?keys.reduce((t,k)=>t+b[k],0):Math.max(...keys.map(k=>b[k]));
    if(h>max)max=h;
  }
  return {buckets,keys,pairs,total,multi,colorless,max};
}
// Kacheln der Seite -> Eingabe von colorCurve
function colorCopiesOf(tiles){
  return tiles.map(x=>({colors:x.card.colors||[],mv:x.card.mv||0,mark:x.mark,land:!!x.card.land}));
}
// END colorCurve
const COLOR_HEX={W:"#f1e7b8",U:"#3b82d6",B:"#4a4a4a",R:"#d6453b",G:"#3f9b4f",M:"#d9a400",C:"#b7bcc6"};
const COLOR_NAME={W:"Weiß",U:"Blau",B:"Schwarz",R:"Rot",G:"Grün",M:"Mehrfarbig",C:"Farblos"};
function renderColorCurve(){
  const variant=$("ccvar").value,mode=$("ccmode").value;
  const r=colorCurve(colorCopiesOf(state),variant,mode);
  const box=$("colorcurve");box.textContent="";
  const H=84,bars=el("div","ccbars");
  for(let i=0;i<CURVE_BUCKETS;i++){
    const col=el("div","cccol"),stack=el("div","ccstack "+mode);
    let sum=0;
    for(const k of r.keys){
      const v=r.buckets[i][k];if(!v)continue;
      sum+=v;
      const seg=el("div","ccseg");seg.style.background=COLOR_HEX[k];
      seg.style.height=Math.max(3,Math.round(v/r.max*H))+"px";
      seg.title=COLOR_NAME[k]+": "+v+(v===1?" Karte":" Karten")+(k==="M"?" (eine Karte, mehrere Farben)":"");
      stack.appendChild(seg);
    }
    col.append(el("div","cctop",mode==="stacked"&&sum?String(sum):""),stack,
      el("div","ccx",i===CURVE_BUCKETS-1?(CURVE_BUCKETS-1)+"+":String(i)));
    bars.appendChild(col);
  }
  box.appendChild(bars);
  const leg=el("div","ccleg");
  for(const k of r.keys){const item=el("span");const dot=el("i");dot.style.background=COLOR_HEX[k];
    item.append(dot,COLOR_NAME[k]+(k==="M"?" (mehrere Farben)":""));leg.appendChild(item)}
  box.appendChild(leg);
  const note=mode==="stacked"
    ?"Jede Karte steht genau einmal im Diagramm (Balkenhöhe = Kartenzahl). Karten mit mehreren Farben bilden das goldene "+
     "Segment „Mehrfarbig“."
    :"Eine mehrfarbige Karte zählt bei jeder ihrer Farben, z. B. eine Karte Grün/Weiß bei Grün und bei Weiß. Die Balken "+
     "ergeben deshalb zusammen mehr als die Kartenzahl.";
  box.appendChild(el("div","ccnote",note));
  const pairs=Object.entries(r.pairs).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]))
    .map(([k,n])=>k.split("/").map(c=>COLOR_NAME[c]).join("/")+" "+n);
  const info=r.total+" Nichtland-Karten in der Variante, davon "+r.multi+" mehrfarbig und "+r.colorless+" farblos."+
    (pairs.length?" Mehrfarbig: "+pairs.join(" · ")+".":"");
  box.appendChild(el("div","ccnote",info));
}
// BEGIN typeCounts
const FLOW_KINDS=["draw","search","surveil","scry","explore","mill_self","mill_opp"];
// Zaehlt je Variante (Core + Splash bzw. Core + NoSplash) Kopien nach Typ. copies: {kinds, mark, empower, points};
// basics: {core, splash, nosplash} je Standardland (zaehlen als Land und Karte, nie als Nicht-Standardland).
function typeCounts(copies, basics){
  const rows=["creature","instant","sorcery","land","nonbasic_land","artifact","enchantment","planeswalker"];
  const out={splash:{},nosplash:{}};
  for(const g of ["splash","nosplash"]){
    const o=out[g];rows.forEach(r=>{o[r]=0});o.cards=0;o.empower=0;o.points=0;o.flow=0;
    FLOW_KINDS.forEach(k=>{o["flow_"+k]=0});
    for(const c of copies){
      if(c.mark!=="core"&&c.mark!==g)continue;
      o.cards++;
      c.kinds.forEach(k=>{if(k in o)o[k]++});
      if(c.empower){o.empower++;o.points+=c.points}
      const fl=c.flow||[];
      if(fl.length){o.flow++;fl.forEach(k=>{if(("flow_"+k) in o)o["flow_"+k]++})}
    }
    for(const b of basics){const n=b.core+b[g];o.land+=n;o.cards+=n}
  }
  return out;
}
// Kacheln der Seite -> Eingabe von typeCounts (alle gezaehlten Felder muessen hier weitergegeben werden)
function copiesOf(tiles){
  return tiles.map(x=>({kinds:x.card.kinds||[],mark:x.mark,empower:!!x.card.empower,
    points:x.card.empower_points||0,flow:x.card.flow||[]}));
}
// END typeCounts
const FLOW_LABELS={draw:"Ziehen (Draw)",search:"Suchen (Search)",surveil:"Surveil",scry:"Scry",explore:"Explore",
  mill_self:"Mill: sich selbst",mill_opp:"Mill: Gegner möglich (auch „target player“)"};
const TYPE_ROWS=[["cards","Karten gesamt",""],["creature","Kreaturen",""],["instant","Instants",""],
  ["sorcery","Sorceries",""],["artifact","Artefakte (ohne Kreaturen)",""],["enchantment","Verzauberungen",""],
  ["planeswalker","Planeswalker",""],["land","Länder gesamt","sep"],["nonbasic_land","davon Nicht-Standard-Länder","sub"],
  ["empower","Empower Jace (Karten)","sep"],["points","Σ Loyalty beim Wirken/Betreten","sub"]];
// Zeilen der Typ-Uebersicht; Kartenfluss-Arten erscheinen nur, wenn eine Karte im Pool sie hat
function typeRows(){
  const rows=TYPE_ROWS.slice();
  const present=FLOW_KINDS.filter(k=>pool.some(c=>(c.flow||[]).includes(k)));
  if(present.length){
    rows.push(["flow","Kartenfluss (Karten)","sep"]);
    present.forEach(k=>rows.push(["flow_"+k,FLOW_LABELS[k],"sub"]));
  }
  return rows;
}
function typeOverview(){
  const t=typeCounts(copiesOf(state),basics);
  const tb=el("table"),head=el("tr");
  head.append(el("th","l",""),el("th",null,"Splash"),el("th",null,"NoSplash"));
  const th=el("thead");th.appendChild(head);tb.appendChild(th);
  const body=el("tbody");
  for(const [key,label,cls] of typeRows()){
    const tr=el("tr",cls==="sep"?"sep":null);
    tr.appendChild(el("td","l"+(cls==="sub"?" sub":""),label));
    const a=t.splash[key],b=t.nosplash[key];
    tr.appendChild(el("td",a!==b?"diff":null,String(a)));
    tr.appendChild(el("td",a!==b?"diff":null,String(b)));
    body.appendChild(tr);
  }
  tb.appendChild(body);
  const box=$("types");box.textContent="";box.className="types";box.appendChild(tb);
  box.appendChild(el("div","note",
    "Gezählt werden Kopien in der Variante (Core plus Gruppe) einschließlich Standardländern. Artefakte und "+
    "Verzauberungen ohne Kreaturen und Länder; eine Karte kann in mehreren Zeilen stehen. Fett: Unterschied zwischen "+
    "den Varianten. Σ Loyalty: Zahlenwerte von Empower Jace beim Zauber oder Betreten (ohne X, ohne Auslöser). "+
    "Kartenfluss: Karten, die ziehen, suchen, surveilen, scrien oder explorieren; es erscheinen nur Arten, die im Pool "+
    "vorkommen. Empower Jace zählt nicht dazu (eigene Zeile)."));
}
// Sortierung nur der Anzeige (die Reihenfolge der Zuordnungen bleibt unberuehrt)
const COLOR_ORDER=["W","U","B","R","G","M","C","L"];
function sortKeyOf(t){
  const c=t.card,nm=c.name.toLowerCase(),land=c.land?1:0;
  switch(sortKey){
    case "name":return [nm];
    case "color":return [COLOR_ORDER.indexOf(rowKey(c)),land,c.mv,nm];
    case "mark":return [["core","splash","nosplash","off"].indexOf(t.mark),land,c.mv,nm];
    case "cat":{const k=catOf(c.name);return [k?CATS.findIndex(x=>x.key===k):99,land,c.mv,nm]}
    default:return [land,c.mv,nm];
  }
}
function applySort(){
  const groups=new Map();
  for(const t of state){if(!groups.has(t.grid))groups.set(t.grid,[]);groups.get(t.grid).push(t)}
  for(const [grid,ts] of groups){
    ts.map(t=>[sortKeyOf(t),t]).sort((x,y)=>{
      for(let i=0;i<x[0].length;i++){if(x[0][i]<y[0][i])return -1;if(x[0][i]>y[0][i])return 1}
      return x[1].copy-y[1].copy}).forEach(([,t])=>grid.appendChild(t.node))}
}
// Export: Arena/MTGO-Format je Variante (Deck = Core + Gruppe + Standardlaender, Sideboard = uebrige Karten)
function exportLists(){
  const res={};
  for(const grp of ["splash","nosplash"]){
    const deck=new Map(),side=new Map();
    const add=(m,x,n)=>{const k=x.name+"|"+x.set+"|"+x.number;const e=m.get(k)||{name:x.name,set:x.set,number:x.number,n:0};e.n+=n;m.set(k,e)};
    for(const t of state)add(t.mark==="core"||t.mark===grp?deck:side,t.card,1);
    basics.forEach(b=>{const n=b.core+b[grp];if(n)add(deck,b,n)});
    const line=e=>e.n+" "+e.name+(e.set?" ("+e.set.toUpperCase()+") "+e.number:"");
    const dl=[...deck.values()].map(line),sl=[...side.values()].map(line);
    res[grp]={count:[...deck.values()].reduce((a,e)=>a+e.n,0),sideCount:[...side.values()].reduce((a,e)=>a+e.n,0),
      text:"Deck\n"+dl.join("\n")+(sl.length?"\n\nSideboard\n"+sl.join("\n"):"")+"\n"}}
  return res;
}
function download(name,text){
  const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([text],{type:"text/plain;charset=utf-8"}));
  a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
function proposalExport(r){
  const info={};pool.forEach(c=>{info[c.name]={set:c.set,number:c.number}});
  basics.forEach(b=>{info[b.name]={set:b.set,number:b.number}});
  const line=(n,q)=>q+" "+n+(info[n]&&info[n].set?" ("+info[n].set.toUpperCase()+") "+info[n].number:"");
  const dl=Object.entries(r.deck).map(([n,q])=>line(n,q));
  const sl=[];let side=0;
  for(const c of pool){const rest=c.qty-(r.deck[c.name]||0);if(rest>0){sl.push(line(c.name,rest));side+=rest}}
  return {count:Object.values(r.deck).reduce((a,q)=>a+q,0),sideCount:side,
    text:"Deck\n"+dl.join("\n")+(sl.length?"\n\nSideboard\n"+sl.join("\n"):"")+"\n"};
}
async function openExport(){
  const box=$("xcols");box.textContent="";const lists=exportLists();
  if(proposal){  // aktuellen Stand des Vorschlags holen (Kategorien oder Farben koennen sich geaendert haben)
    try{const r=await api("/api/propose",proposalBody());if(r.ok)proposal=r}catch(e){}
    lists.proposal=proposalExport(proposal);
  }
  const variants=[["splash","Splash-Variante"],["nosplash","NoSplash-Variante"]];
  if(lists.proposal)variants.push(["proposal","Deckvorschlag"]);
  for(const [grp,title] of variants){
    const r=lists[grp],col=el("div","xcol");
    col.appendChild(el("h3",null,title));
    col.appendChild(el("div","xcount",r.count+" Karten im Deck, "+r.sideCount+" im Sideboard"));
    const ta=el("textarea");ta.readOnly=true;ta.value=r.text;ta.onfocus=()=>ta.select();col.appendChild(ta);
    const btns=el("div","xbtns"),cp=el("button","btn","Kopieren"),sv=el("button","btn","Als Datei speichern");
    cp.onclick=async()=>{try{await navigator.clipboard.writeText(r.text)}catch(e){ta.focus();ta.select();document.execCommand("copy")}
      cp.textContent="Kopiert";setTimeout(()=>cp.textContent="Kopieren",1500)};
    sv.onclick=()=>download("draftgott_"+grp+".txt",r.text);
    btns.append(cp,sv);col.appendChild(btns);box.appendChild(col)}
  $("exportbox").classList.add("show");
}
// Uebersicht links: Karten je Farbe, Zuordnung (C/S/N) und Kategorie (zaehlt Kopien, ohne Standardlaender)
const COLORS=[["W","Weiß","#f1e7b8"],["U","Blau","#3b82d6"],["B","Schwarz","#4a4a4a"],["R","Rot","#d6453b"],
  ["G","Grün","#3f9b4f"],["M","Mehrfarbig","#d9a400"],["C","Farblos","#b7bcc6"],["L","Länder","#9a7b4f"]];
const rowKey=card=>{if(card.land)return "L";const c=card.colors||[];return c.length===0?"C":c.length>1?"M":c[0]};
function overview(){
  const acc={};COLORS.forEach(([k])=>acc[k]={pool:0,core:0,splash:0,nosplash:0,none:0,cat:{}});
  for(const t of state){const a=acc[rowKey(t.card)]||acc.C;a.pool++;if(t.mark!=="off")a[t.mark]++;
    const k=catOf(t.card.name);if(k)a.cat[k]=(a.cat[k]||0)+1;else a.none++}
  const tb=el("table"),th=el("thead"),r1=el("tr"),r2=el("tr");
  const h=(tr,txt,cls,span,title)=>{const c=el("th",cls||null,txt);if(span)c.colSpan=span;if(title)c.title=title;tr.appendChild(c);return c};
  h(r1,"","");h(r1,"","");h(r1,"Zuordnung","grp",3);h(r1,"Kategorie","grp",CATS.length+1);
  h(r2,"Farbe","l");h(r2,"Pool","",0,"Alle Kopien in Deck und Sideboard der Datei (ohne Standardländer)");
  h(r2,"C","",0,"Core").style.color="var(--core)";h(r2,"S","",0,"Splash").style.color="var(--splash)";
  h(r2,"N","",0,"NoSplash").style.color="#a37c00";
  for(const c of CATS)h(r2,c.abbr,"",0,c.label+": "+c.hint);
  h(r2,"–","",0,"ohne Kategorie");
  th.append(r1,r2);tb.appendChild(th);
  const body=el("tbody"),tot={pool:0,core:0,splash:0,nosplash:0,none:0,cat:{}};
  const cell=(tr,v,cls)=>{tr.appendChild(el("td",v?cls||null:"z",v?String(v):"·"))};
  for(const [k,name,col] of COLORS){
    const a=acc[k],tr=el("tr");
    const lab=el("td","l");const dot=manaSym(k)||el("span","cdot");if(!dot.title)dot.style.background=col;
    lab.append(dot,name);tr.appendChild(lab);
    cell(tr,a.pool);cell(tr,a.core);cell(tr,a.splash);cell(tr,a.nosplash);
    for(const c of CATS)cell(tr,a.cat[c.key]||0);cell(tr,a.none);
    body.appendChild(tr);
    for(const f of ["pool","core","splash","nosplash","none"])tot[f]+=a[f];
    for(const c of CATS)tot.cat[c.key]=(tot.cat[c.key]||0)+(a.cat[c.key]||0)}
  const tr=el("tr","tot");tr.appendChild(el("td","l","Gesamt"));
  [tot.pool,tot.core,tot.splash,tot.nosplash,...CATS.map(c=>tot.cat[c.key]||0),tot.none].forEach(v=>tr.appendChild(el("td",null,String(v))));
  body.appendChild(tr);tb.appendChild(body);
  const box=$("overview");box.textContent="";box.appendChild(tb);
  const note=el("div","note",
    "Mehrfarbige Karten stehen nur in „Mehrfarbig“. Pool = alle Kopien in Deck und Sideboard der Datei, ohne Standardländer. "+
    "C/S/N = Core/Splash/NoSplash; der Rest des Pools ist „Aus“. Kategorien: "+CATS.map(c=>c.abbr+" "+c.label).join(", ")+".");
  box.appendChild(note);
}
// Deck-Vorschlag: die Regeln liegen auf dem Server (components/suggest.py); hier nur Anwenden und Rueckgaengig
const undoStack=[];
function chosenColors(){return [...document.querySelectorAll(".colpick input:checked")].map(i=>i.value)}
function setColors(list){document.querySelectorAll(".colpick input").forEach(i=>{i.checked=list.includes(i.value)})}
// Standardfarben: Farben der Nichtland-Karten, die aktuell im Core sind (sonst alle fuenf)
function defaultColors(){
  const found=new Set();
  state.forEach(t=>{if(t.mark==="core"&&!t.card.land)(t.card.colors||[]).forEach(c=>found.add(c))});
  return found.size?[...found]:["W","U","B","R","G"];
}
function proposalBody(){return {marks:marksPerCard(),basics:basicsBody(),cats,colors:chosenColors(),
  target:+$("target").value||40,sort:sortKey}}
function renderProposal(){
  const box=$("proposal");box.textContent="";
  if(!proposal){box.style.display="none";return}
  const deck=proposal.deck,m=proposal.summary,byName={};
  pool.forEach(c=>{byName[c.name]=c});
  const head=el("div","nh");
  head.appendChild(el("b",null,"Deckvorschlag: "+m.size+" Karten (Ziel "+m.target+"), davon "+m.lands+" Länder · Farben "+
    (m.colors.length?m.colors.join(""):"keine")));
  const x=el("button","btn","Schließen");x.onclick=()=>{proposal=null;renderProposal()};head.appendChild(x);
  box.appendChild(head);
  const spells=[],lands=[];
  for(const [n,q] of Object.entries(deck)){const c=byName[n];(!c||c.land?lands:spells).push([n,q,c])}
  spells.sort((a,b)=>(a[2].mv-b[2].mv)||a[0].localeCompare(b[0]));
  lands.sort((a,b)=>(!!a[2]-!!b[2])||a[0].localeCompare(b[0]));
  const sum=rows=>rows.reduce((t,r)=>t+r[1],0);
  const col=(title,rows)=>{const d=el("div","pcol");d.appendChild(el("h4",null,title));
    rows.forEach(([n,q])=>{const l=el("div",null,q+"× "+n);if(m.splash_cards[n])l.appendChild(el("span","ptag","Splash"));d.appendChild(l)});
    return d};
  const cols=el("div","pcols");
  cols.append(col("Zauber ("+sum(spells)+")",spells),col("Länder ("+sum(lands)+")",lands));
  box.appendChild(cols);
  m.hints.forEach(t=>noticeLine(box,t,"nhint"));m.warnings.forEach(t=>noticeLine(box,t,"nw"));
  if(m.ignored)noticeLine(box,m.ignored+" Karten ohne Kategorie wurden nicht berücksichtigt.","nmuted");
  noticeLine(box,"Beim Simulieren erscheint der Deckvorschlag als weitere Variante (Haken „mitsimulieren“).","nmuted");
  box.style.display="block";
}
async function createProposal(){
  showErr("");
  const r=await api("/api/propose",proposalBody());
  if(!r.ok){showErr(r.error||"Fehler beim Deckvorschlag");return}
  proposal=r;$("simprop").checked=true;renderProposal();save();
}
function marksPerCard(){const out=[];let i=0;for(const c of pool){const ms=[];for(let k=0;k<c.qty;k++)ms.push(state[i++].mark);out.push(ms)}return out}
function basicsBody(){const bs={};basics.forEach(b=>bs[b.name]={core:b.core,splash:b.splash,nosplash:b.nosplash});return bs}
function noticeLine(box,text,cls){box.appendChild(el("div",cls||null,text))}
function showNotice(title,lines,warnings,withUndo){
  const box=$("notice");box.textContent="";
  const head=el("div","nh");head.appendChild(el("b",null,title));
  const x=el("button","btn","Schließen");x.onclick=()=>{box.style.display="none"};head.appendChild(x);
  box.appendChild(head);
  lines.forEach(t=>t.startsWith("   ")?noticeLine(box,t.trim(),"nsub"):noticeLine(box,t));
  warnings.forEach(t=>noticeLine(box,t,"nw"));
  box.style.display="block";
}
function updateUndo(){$("undo").style.display=undoStack.length?"":"none"}
async function suggestDeck(){
  showErr("");
  const before=marksPerCard();
  const r=await api("/api/suggest",{marks:before,basics:basicsBody(),cats,target:+$("target").value||40,sort:sortKey});
  if(!r.ok){showErr(r.error||"Fehler beim Vorschlag");return}
  if(JSON.stringify(r.marks)===JSON.stringify(before)){
    showNotice("Keine Änderung",["Es gibt keine Karten mit Kategorie, die noch umgeordnet werden müssten."],r.summary.warnings);return}
  undoStack.push(before.flat());
  let i=0;r.marks.forEach(ms=>ms.forEach(m=>{state[i++].mark=m}));
  state.forEach(paint);summary();save();updateUndo();
  const m=r.summary,a=m.assigned,f=m.filler;
  showNotice("Zuordnung nach Kategorien gesetzt",[
    "Nach Kategorie: "+a.core+" → Core (MustPlay), "+a.splash+" → Splash (Splashworthy), "+a.off+" → Aus (NeverPlay).",
    "Filler: "+f.core+" → Core, "+f.nosplash+" → NoSplash, "+f.off+" nicht benötigt (Aus).",
    "Größe: Splash-Variante "+m.sizes.splash+", NoSplash-Variante "+m.sizes.nosplash+" Karten (Ziel "+m.target+").",
    "Mit „Rückgängig“ stellst du den vorherigen Stand wieder her."],m.warnings);
}
function undoSuggest(){
  const snap=undoStack.pop();if(!snap)return;
  const ms=Array.isArray(snap)?snap:snap.marks;  // Land-Empfehlung merkt sich auch die Standardlaender
  ms.forEach((m,i)=>{if(state[i])state[i].mark=m});
  if(!Array.isArray(snap)){snap.basics.forEach((v,i)=>GROUPS.forEach((g,k)=>{basics[i][g]=v[k]}));buildBasics()}
  state.forEach(paint);summary();save();updateUndo();
  showNotice("Rückgängig gemacht",["Der Stand vor dem letzten Vorschlag ist wiederhergestellt."],[]);
}
// Land-Empfehlung: Regeln auf dem Server (components/landadvice.py); hier Anwenden, Anzeige und Rueckgaengig
const BASIC_OF={W:"Plains",U:"Island",B:"Swamp",R:"Mountain",G:"Forest"};
const pct=p=>Math.round(p*100)+" %";
const ampel=p=>p>=0.9?"grün":p>=0.8?"gelb":"rot";
async function recommendLands(){
  showErr("");
  const before=marksPerCard(),bBefore=basics.map(b=>GROUPS.map(g=>b[g]));
  const r=await api("/api/lands",{marks:before,basics:basicsBody(),cats,target:+$("target").value||40});
  if(!r.ok){showErr(r.error||"Fehler bei der Land-Empfehlung");return}
  undoStack.push({marks:before.flat(),basics:bBefore});
  let i=0;r.marks.forEach(ms=>ms.forEach(m=>{state[i++].mark=m}));
  basics.forEach(b=>{const v=r.basics[b.name];if(v)GROUPS.forEach(g=>{b[g]=v[g]})});
  buildBasics();state.forEach(paint);summary();save();updateUndo();
  const lines=[];
  for(const v of r.variants){
    const bs=Object.entries(v.basics).map(([c,k])=>k+" "+BASIC_OF[c]).join(", ")||"keine Standardländer";
    lines.push(v.label+" ("+(v.colors.join("")||"farblos")+"): "+v.lands+" Länder = "+
      (v.nonbasic?v.nonbasic+" Nicht-Standard + ":"")+bs+" · "+v.spells+" Zauber, "+v.size+" Karten");
    for(const [c,x] of Object.entries(v.report)){
      if(!x.cards)continue;
      lines.push("   "+c+": "+x.sources+" Quellen · "+x.cards+(x.cards===1?" Karte":" Karten")+" · Ø "+pct(x.avg)+" pünktlich ("+ampel(x.avg)+")"+
        (x.worst?" · am knappsten: "+x.worst.name+" "+pct(x.worst.p):""));
    }
  }
  const to={core:"Core",splash:"Splash",nosplash:"NoSplash"};
  const fit=r.lands.filter(l=>l.group!=="off").map(l=>l.name+" → "+to[l.group]);
  const bad=r.lands.filter(l=>l.group==="off").map(l=>l.name+(l.colors.length?" ("+l.colors.join("")+
    (l.missing.length?", "+l.missing.join("")+" fehlt":", passt zu keiner Variante")+")":" (keine Farbe)"));
  if(fit.length)lines.push("Nicht-Standardländer empfohlen: "+fit.join("; "));
  if(bad.length)lines.push("Nicht empfohlen (Aus): "+bad.join("; "));
  lines.push("Pünktlich: Chance, die Farbsymbole einer Karte bis zur Runde = Manawert zu haben (auf dem Play). "+
    "Mit „Rückgängig“ stellst du den vorherigen Stand wieder her.");
  showNotice("Länder empfohlen",lines,r.warnings);
}
function showErr(msg){const e=$("err");e.textContent=msg||"";e.style.display=msg?"block":"none"}
async function api(path,body){
  const r=await fetch(path,body?{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}:undefined);
  return r.json();
}
async function simulate(){
  showErr("");$("go").disabled=true;
  const marks=[];let i=0;for(const c of pool){const ms=[];for(let k=0;k<c.qty;k++)ms.push(state[i++].mark);marks.push(ms)}
  const bs={};basics.forEach(b=>bs[b.name]={core:b.core,splash:b.splash,nosplash:b.nosplash});
  const prop=$("simprop").checked?{colors:chosenColors(),target:+$("target").value||40,sort:sortKey}:undefined;
  const r=await api("/api/simulate",{marks,basics:bs,cats,sims:+$("sims").value,proposal:prop});
  if(!r.ok){showErr(r.error||"Fehler");$("go").disabled=false;return}
  $("overlay").classList.add("show");poll();
}
async function poll(){
  let s;try{s=await api("/api/status")}catch(e){setTimeout(poll,1500);return}
  if(s.state==="running"){
    $("ovmsg").textContent=s.message;const t=Math.round(s.elapsed);
    $("ovtime").textContent="vergangene Zeit: "+Math.floor(t/60)+":"+String(t%60).padStart(2,"0");
    setTimeout(poll,1000);return}
  $("overlay").classList.remove("show");$("go").disabled=false;
  if(s.state==="done"){$("frame").src="/report?"+Date.now();$("results").classList.add("show");
    $("rnote").textContent="Der Bericht wurde auch als Datei gespeichert."}
  else if(s.state==="error")showErr(s.message);
}
$("go").onclick=simulate;
$("catfilter").onchange=()=>state.forEach(paint);
$("search").oninput=()=>{searchQ=$("search").value.trim().toLowerCase();state.forEach(paint)};
$("sort").onchange=()=>{sortKey=$("sort").value;applySort()};
$("export").onclick=openExport;
$("ccvar").onchange=renderColorCurve;
$("ccmode").onchange=renderColorCurve;
$("suggest").onclick=suggestDeck;
$("propose").onclick=createProposal;
document.querySelectorAll(".colpick input").forEach(i=>{i.onchange=save;
  const sym=manaSym(i.value);if(sym&&i.nextSibling){i.nextSibling.textContent="";i.parentNode.appendChild(sym)}});
$("undo").onclick=undoSuggest;
$("lands").onclick=recommendLands;
$("fqvar").onchange=renderColors;
$("target").onchange=save;
$("xclose").onclick=()=>$("exportbox").classList.remove("show");
$("exportbox").onclick=e=>{if(e.target===$("exportbox"))$("exportbox").classList.remove("show")};
const fixBar=()=>document.documentElement.style.setProperty("--hbar",document.querySelector("header.bar").offsetHeight+"px");
window.addEventListener("resize",fixBar);
$("back").onclick=()=>$("results").classList.remove("show");
$("lightbox").onclick=()=>$("lightbox").classList.remove("show");
document.addEventListener("keydown",e=>{if(e.key==="Escape"){
  $("lightbox").classList.remove("show");$("exportbox").classList.remove("show")}});
$("quit").onclick=async()=>{if(!confirm("Draft-Helper beenden?"))return;
  try{await api("/api/quit",{})}catch(e){}
  document.body.innerHTML="<main><h2>Draft-Helper wurde beendet.</h2><p>Du kannst dieses Fenster jetzt schließen.</p></main>"};
(async()=>{
  const d=await api("/api/pool");pool=d.cards;
  // Speicherstand je Inhalt der Pool-Datei: ein anderer Kartenpool startet mit den Vorgaben der Datei
  storeKey="draft3:"+d.signature;
  try{Object.keys(localStorage).filter(k=>/^draft2?:/.test(k)).forEach(k=>localStorage.removeItem(k))}catch(e){}
  basics=d.basics.map(b=>({name:b.name,image:b.image,large:b.large,pool:b.pool,core:b.core,splash:0,nosplash:0,
    set:b.set,number:b.number}));
  const cf=$("catfilter");
  for(const [v,t] of [["","Alle Karten"],...CATS.map(c=>[c.key,c.abbr+" "+c.label]),["none","Ohne Kategorie"]]){
    const o=el("option",null,t);o.value=v;cf.appendChild(o)}
  const sel=$("sims");d.options.forEach(o=>{const op=el("option",null,o.toLocaleString("de-DE"));op.value=o;
    if(o===d.sims)op.selected=true;sel.appendChild(op)});
  build();fixBar();
  if(!colorsFromSave)setColors(defaultColors());
})();
</script></body></html>
"""


SYMBOL_KEYS = ("W", "U", "B", "R", "G", "C")


def render_page():
    """Die Seite mit den vorhandenen Original-Manasymbolen (Farben und Farblos) als eingebettetem CSS."""
    have = [k for k in SYMBOL_KEYS if k in active_symbols()]
    return (PAGE.replace("/*SYMBOL_CSS*/", symbol_css(have))
            .replace("const SYMBOLS=[];", "const SYMBOLS=" + json.dumps(have, separators=(",", ":")) + ";"))
