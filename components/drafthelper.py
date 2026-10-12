"""Draft-Helper (--drafthelper): lokaler Webserver mit Kartenseite.

Die Seite zeigt Deck und Sideboard aus der Kartenpool-Datei als Karten (Daten und Bilder von Scryfall). Jede Kopie
einer Karte wird als Core, Splash, NoSplash oder Aus markiert. Ein Klick auf "Simulieren" baut daraus die Varianten
Core + Splash und Core + NoSplash, simuliert sie mit der normalen Pipeline und zeigt den Vergleichsbericht.

Nur Standardbibliothek. Der Server hoert ausschliesslich auf 127.0.0.1.
"""
import argparse
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

from components.deckfile import parse_pool
from components.scryfall import card_image_url, fetch_cards_cached, fetch_printing_images

PORT = 8765
MARKS = ("core", "splash", "nosplash", "off")
SIM_OPTIONS = (1000, 5000, 10000)
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent.parent


def load_pool(path, refresh=False):
    """Liest die Pool-Datei und ergaenzt Typ, Manawert und Bild-URL von Scryfall. Reihenfolge: Deck, Sideboard."""
    p = pathlib.Path(path)
    if not p.exists() and (SCRIPT_DIR / p).exists():
        p = SCRIPT_DIR / p
    if not p.exists():
        sys.exit(f"Kartenpool-Datei nicht gefunden: {path}")
    rows = parse_pool(p.read_text(encoding="utf-8"))
    if not rows:
        sys.exit(f"Keine Karten in {p} gefunden (erwartet: Abschnitte 'Deck' und 'Sideboard').")
    print(f"Kartenpool: {sum(r['qty'] for r in rows)} Karten aus {p}", file=sys.stderr)
    print("Lade Kartendaten und Bilder von Scryfall ...", file=sys.stderr)
    try:
        data = fetch_cards_cached(sorted({r["name"] for r in rows}), refresh)
    except urllib.error.URLError as e:
        sys.exit(f"Scryfall nicht erreichbar: {e}")
    images = fetch_printing_images([(r["set"], r["number"]) for r in rows if r["set"] and r["number"]])
    cards = []
    for r in rows:
        sc = data.get(r["name"]) or data.get(r["name"].split(" // ")[0]) or {}
        image = images.get(f"{r['set']}/{r['number']}") or card_image_url(sc)
        type_line = sc.get("type_line") or ""
        cards.append({
            "name": r["name"], "qty": r["qty"], "section": r["section"], "image": image,
            "large": image.replace("/normal/", "/large/") if image else None,
            "land": "Land" in type_line.split("—")[0], "mv": sc.get("cmc") or 0, "found": bool(sc),
        })
    order = {"deck": 0, "sideboard": 1}  # je Bereich: Nichtlaender nach Manawert, Laender zuletzt
    cards.sort(key=lambda c: (order.get(c["section"], 2), c["land"], c["mv"], c["name"]))
    return cards


def entries_from_marks(pool, marks):
    """Baut die Deck-Eintraege fuer die Simulation. marks: je Pool-Karte eine Liste mit einer Markierung je Kopie."""
    groups = {m: Counter() for m in MARKS}
    for card, ms in zip(pool, marks):
        for m in ms:
            groups[m][card["name"]] += 1
    core = dict(groups["core"])
    if not groups["splash"] and not groups["nosplash"]:
        return [{"path": "", "name": "Core", "deck": core, "parts": [("Core", core)]}]
    entries = []
    for label, key in (("Splash", "splash"), ("NoSplash", "nosplash")):
        part = dict(groups[key])
        deck = Counter(core)
        deck.update(part)
        entries.append({"path": "", "name": label, "deck": dict(deck), "parts": [("Core", dict(core)), (label, part)]})
    return entries


class Job:
    """Eine Simulation im Hintergrund; Zustand fuer die Statusabfrage der Seite."""

    def __init__(self):
        self.lock = threading.Lock()
        self.state, self.message, self.started, self.finished = "idle", "", 0.0, 0.0
        self.report = None

    def status(self):
        with self.lock:
            end = self.finished if self.state in ("done", "error") else time.time()
            return {"state": self.state, "message": self.message, "elapsed": round(end - self.started, 1)}

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
                self._send(PAGE)
            elif path == "/api/pool":
                self._json({"cards": app["pool"], "sims": app["args"].sims, "options": app["options"],
                            "file": app["file"]})
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
            if path != "/api/simulate":
                self._send("Nicht gefunden", "text/plain; charset=utf-8", 404)
                return
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                marks, sims = body["marks"], int(body.get("sims") or app["args"].sims)
                pool = app["pool"]
                if len(marks) != len(pool) or any(len(ms) != c["qty"] or any(m not in MARKS for m in ms)
                                                  for ms, c in zip(marks, pool)):
                    raise ValueError("Markierungen passen nicht zum Kartenpool")
                if not 100 <= sims <= 100000:
                    raise ValueError("Anzahl der Spiele muss zwischen 100 und 100000 liegen")
            except (ValueError, KeyError, TypeError) as e:
                self._json({"ok": False, "error": str(e)}, 400)
                return
            run_args = argparse.Namespace(**vars(app["args"]))
            run_args.sims, run_args.core = sims, "Core"  # core: Herkunft der Karten (Core/Splash/NoSplash) im Bericht

            def work(progress):
                html = app["simulate"](entries_from_marks(pool, marks), run_args, progress)
                app["save"](html, run_args)
                return html

            if not app["job"].start(work):
                self._json({"ok": False, "error": "Es laeuft bereits eine Simulation"}, 409)
                return
            self._json({"ok": True})

    return Handler


def serve(args, simulate, save):
    pool = load_pool(args.drafthelper, args.neu_laden)
    options = sorted(set(SIM_OPTIONS) | {args.sims})
    app = {"pool": pool, "args": args, "simulate": simulate, "save": save, "job": Job(), "options": options,
           "file": pathlib.Path(args.drafthelper).name}
    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), make_handler(app))
    except OSError:  # Port belegt: freien Port waehlen lassen
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
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
.err{background:#fef3f2;border:1px solid #fda29b;color:#b42318;border-radius:10px;padding:12px 16px;margin:10px 0;display:none}
</style></head><body>
<header class="bar">
  <h1>Draft-Helper</h1>
  <div class="counts" id="counts"></div>
  <div class="sizes" id="sizes"></div>
  <div class="spacer"></div>
  <label>Spiele pro Modus <select id="sims"></select></label>
  <button class="btn primary" id="go">Simulieren</button>
  <button class="btn" id="quit" title="Draft-Helper beenden">Beenden</button>
</header>
<main>
  <div class="help"><b>So geht's:</b> Wähle unter jeder Karte, wohin sie gehört.
    <ul>
      <li><b style="color:var(--core)">Core</b> – Karte ist in beiden Varianten dabei.</li>
      <li><b style="color:var(--splash)">Splash</b> – Karte ist nur in der Variante „Splash“ dabei.</li>
      <li><b style="color:#a37c00">NoSplash</b> – Karte ist nur in der Variante „NoSplash“ dabei.</li>
      <li><b style="color:var(--off)">Aus</b> – Karte ist in keiner Variante dabei.</li>
    </ul>
    Mehrfach vorhandene Karten (z. B. 4 Plains) erscheinen einzeln und können unterschiedlich zugeordnet werden.
    Ein Klick auf das Bild zeigt die Karte groß. Danach auf <b>Simulieren</b> klicken.</div>
  <div class="err" id="err"></div>
  <div id="sections"></div>
</main>
<div id="overlay"><div class="box"><div class="spin"></div><b>Simulation läuft …</b>
  <div id="ovmsg" style="margin-top:8px"></div><div id="ovtime" style="color:var(--muted);margin-top:4px"></div></div></div>
<div id="lightbox"><img alt=""></div>
<div id="results"><div class="rbar"><button class="btn" id="back">← Zurück zu den Karten</button>
  <span id="rnote" style="color:var(--muted)"></span></div><iframe id="frame" title="Bericht"></iframe></div>
<script>
const LABEL={core:"Core",splash:"Splash",nosplash:"NoSplash",off:"Aus"};
let pool=[], tiles=[], state=[], file="";
const $=id=>document.getElementById(id);
const el=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!=null)e.textContent=text;return e};

function save(){try{localStorage.setItem("draft:"+file,JSON.stringify(state.map(t=>t.mark)))}catch(e){}}
function restore(){try{const s=JSON.parse(localStorage.getItem("draft:"+file)||"null");
  if(Array.isArray(s)&&s.length===state.length&&s.every(m=>m in LABEL))s.forEach((m,i)=>state[i].mark=m)}catch(e){}}

function build(){
  state=[];const box=$("sections");box.textContent="";
  for(const [sec,title] of [["deck","Deck"],["sideboard","Sideboard"]]){
    const cards=pool.filter(c=>c.section===sec);if(!cards.length)continue;
    const h=el("h2",null,title+" ");const small=el("small",null,"");h.appendChild(small);box.appendChild(h);
    const grid=el("div","grid");box.appendChild(grid);let n=0;
    for(const c of cards){
      for(let k=1;k<=c.qty;k++){
        n++;const t={card:c,copy:k,mark:sec==="deck"?"core":"off"};state.push(t);
      }
    }
    small.textContent="("+n+" Karten)";
    grid._cards=cards;
  }
  restore();
  // Tiles in Reihenfolge der Sektionen erzeugen
  let idx=0;const grids=[...box.querySelectorAll(".grid")];
  grids.forEach(grid=>{for(const c of grid._cards){for(let k=1;k<=c.qty;k++){grid.appendChild(tile(state[idx],idx));idx++}}});
  refresh();
}
function tile(t,i){
  const d=el("div","tile");t.node=d;
  if(t.card.image){const im=el("img");im.src=t.card.image;im.alt=t.card.name;im.loading="lazy";
    im.onclick=()=>{$("lightbox").querySelector("img").src=t.card.large||t.card.image;$("lightbox").classList.add("show")};
    d.appendChild(im)}
  else d.appendChild(el("div","ph",t.card.name));
  const cap=el("div","cap");cap.appendChild(el("b",null,t.card.name));
  if(t.card.qty>1)cap.appendChild(el("span",null,t.copy+"/"+t.card.qty));
  d.appendChild(cap);
  const seg=el("div","seg");
  for(const m of ["core","splash","nosplash","off"]){
    const b=el("button",null,LABEL[m]);b.dataset.m=m;b.onclick=()=>{t.mark=m;paint(t);summary();save()};seg.appendChild(b)}
  d.appendChild(seg);paint(t);return d;
}
function paint(t){t.node.className="tile m-"+t.mark;
  t.node.querySelectorAll(".seg button").forEach(b=>b.classList.toggle("on",b.dataset.m===t.mark))}
function refresh(){state.forEach(paint);summary()}
function summary(){
  const n={core:0,splash:0,nosplash:0,off:0};state.forEach(t=>n[t.mark]++);
  const c=$("counts");c.textContent="";
  for(const m of ["core","splash","nosplash","off"])c.appendChild(el("span","chip "+m,LABEL[m]+" "+n[m]));
  const a=n.core+n.splash,b=n.core+n.nosplash,s=$("sizes");s.textContent="";
  s.appendChild(document.createTextNode("Splash-Variante: "));s.appendChild(el("b",null,a+" Karten"));
  s.appendChild(document.createTextNode(" · NoSplash-Variante: "));s.appendChild(el("b",null,b+" Karten"));
  if(a!==b)s.appendChild(el("span","warn","  – unterschiedlich groß"));
}
function showErr(msg){const e=$("err");e.textContent=msg||"";e.style.display=msg?"block":"none"}
async function api(path,body){
  const r=await fetch(path,body?{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}:undefined);
  return r.json();
}
async function simulate(){
  showErr("");$("go").disabled=true;
  const marks=[];let i=0;for(const c of pool){const ms=[];for(let k=0;k<c.qty;k++)ms.push(state[i++].mark);marks.push(ms)}
  const r=await api("/api/simulate",{marks,sims:+$("sims").value});
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
$("back").onclick=()=>$("results").classList.remove("show");
$("lightbox").onclick=()=>$("lightbox").classList.remove("show");
document.addEventListener("keydown",e=>{if(e.key==="Escape")$("lightbox").classList.remove("show")});
$("quit").onclick=async()=>{if(!confirm("Draft-Helper beenden?"))return;
  try{await api("/api/quit",{})}catch(e){}
  document.body.innerHTML="<main><h2>Draft-Helper wurde beendet.</h2><p>Du kannst dieses Fenster jetzt schließen.</p></main>"};
(async()=>{
  const d=await api("/api/pool");pool=d.cards;file=d.file;
  const sel=$("sims");d.options.forEach(o=>{const op=el("option",null,o.toLocaleString("de-DE"));op.value=o;
    if(o===d.sims)op.selected=true;sel.appendChild(op)});
  build();
})();
</script></body></html>
"""
