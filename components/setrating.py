"""Set bewerten (--set-bewerten [SET], Menuepunkt 5 in draftgott.bat): lokaler Webserver mit einer eigenen Seite.

Erst waehlt man eines der fertig umgesetzten Sets (alle Sets mit Archetypen in components/archetypes.py, derzeit TRK
und FRA), dann legt man je Karte die Kategorie (Matchwinner bis NeverPlay) und die Archetypen fest (neutral -> gruen
= passt gut -> lila = bester Archetyp). Gespeichert wird sofort in dieselben Dateien wie im Drafthelper und im
Live-Draft (kartenbewertung.json, kartenarchetypen.json): die Bewertung gilt je Kartenname fuer jeden Pool und jeden
Draft, man macht sie also einmal je Set und nicht nach jedem Draft.

Die Kartenliste kommt von Scryfall (components/scryfall.fetch_set_cards, danach aus scryfall_set_cache.json).
Nur Standardbibliothek. Der Server hoert ausschliesslich auf 127.0.0.1.
"""
import http.server
import json
import sys
import threading
import webbrowser

from components import archetypes as set_archetypes
from components import cardarchetypes
from components import ratings as card_ratings
from components.i18n import html_lang, t
from components.symbols import active as active_symbols, symbol_css

PORT = 8767
SYMBOL_KEYS = ("W", "U", "B", "R", "G")


class LocalServer(http.server.ThreadingHTTPServer):
    allow_reuse_address = False  # wie im Drafthelper: belegter Port -> freien Port waehlen


def implemented_sets():
    """Fertig umgesetzte Sets (mit Archetypen): [{"code": "TRK", "archetypes": [{"colors", "name"}]}]."""
    return [{"code": code.upper(), "archetypes": [{"colors": a["colors"], "name": a["name"]} for a in lst]}
            for code, lst in set_archetypes.ARCHETYPES.items()]


def start_set(code):
    """Vorauswahl aus der Kommandozeile: Setcode in Grossbuchstaben, wenn das Set umgesetzt ist, sonst ""."""
    code = (code or "").strip().lower()
    return code.upper() if set_archetypes.for_set(code) else ""


def rating_name(sc):
    """Name, unter dem eine Scryfall-Karte bewertet wird: wie in Arena und in den Pool-Dateien. Zweiseitige Karten
    (z. B. FRA "Pyre Rhymer // Molten Tide", Layout prepare) heissen dort nur nach der Vorderseite; Split-Karten
    behalten den ganzen Namen."""
    name = sc.get("name") or ""
    return name if sc.get("layout") == "split" else name.split(" // ")[0]


def set_cards(code, fetch):
    """Karten eines Sets fuer die Seite (Reihenfolge von Scryfall), ohne Standardlaender und ohne zweite Drucke."""
    from components.livedraft import card_summary
    out, seen = [], set()
    for sc in fetch(code.lower()) or []:
        name = rating_name(sc)
        if not name or name in seen:
            continue
        card = card_summary(sc, name, code, sc.get("collector_number") or "")
        if cardarchetypes.is_basic(card):
            continue
        seen.add(name)
        out.append(card)
    return out


def progress(cards, ratings, assign):
    """Stand eines Sets: Karten, mit Kategorie, mit Archetyp, fertig (Kategorie und Archetyp; NeverPlay braucht
    keinen Archetyp) und Karten je Kategorie."""
    names = [c["name"] for c in cards]
    rated = [n for n in names if ratings.get(n) in card_ratings.CATEGORIES]
    assigned = [n for n in names if assign.get(n)]
    done = [n for n in rated if assign.get(n) or ratings[n] == "neverplay"]
    cats = {k: 0 for k in card_ratings.CATEGORIES}
    for n in rated:
        cats[ratings[n]] += 1
    return {"total": len(names), "rated": len(rated), "assigned": len(assigned), "done": len(done), "cats": cats}


def make_handler(app):
    """app: {"ratings", "cardarch" (Dateipfade), "fetch_set" (Setcode -> Scryfall-Karten), "start", "server"}."""
    app.setdefault("cards", {})
    lock = threading.Lock()

    def ratings():
        return card_ratings.load_ratings(app["ratings"])

    def known():
        return {c["name"] for cards in app["cards"].values() for c in cards}

    def current_progress():
        cards = [c for cs in app["cards"].values() for c in cs]
        return progress(cards, ratings(), cardarchetypes.load_assign(app["cardarch"]))

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

        def _body(self):
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            if not isinstance(data, dict):
                raise ValueError(t("Ungültige Anfrage"))
            return data

        def do_GET(self):
            path, _, query = self.path.partition("?")
            if path == "/":
                self._send(render_page())
            elif path == "/api/sets":
                self._json({"sets": implemented_sets(), "start": app.get("start") or ""})
            elif path == "/api/setcards":
                params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
                self._set(params.get("set") or "")
            else:
                self._send(t("Nicht gefunden"), "text/plain; charset=utf-8", 404)

        def _set(self, code):
            found = set_archetypes.for_set(code) if code.isalnum() else None
            if not found:
                self._json({"ok": False, "error": t("Set {code} ist nicht umgesetzt", code=code.upper()[:8])}, 400)
                return
            code = code.lower()
            cards = set_cards(code, app["fetch_set"])
            if not cards:
                self._json({"ok": False, "error": t("Set {code} konnte nicht geladen werden (Scryfall)",
                                                    code=code.upper())}, 502)
                return
            with lock:
                app["cards"][code] = cards
            names = {c["name"] for c in cards}
            assign = cardarchetypes.load_assign(app["cardarch"])
            best = cardarchetypes.load_best(app["cardarch"])
            rat = ratings()
            self._json({"ok": True, "set": code.upper(), "cards": cards,
                        "archetypes": [{"colors": a["colors"], "name": a["name"]} for a in found],
                        "ratings": {n: v for n, v in rat.items() if n in names},
                        "cardarch": {n: v for n, v in assign.items() if n in names},
                        "cardbest": {n: v for n, v in best.items() if n in names},
                        "progress": progress(cards, rat, assign)})

        def do_POST(self):
            path = self.path.split("?", 1)[0]
            if path == "/api/quit":
                self._json({"ok": True})
                threading.Thread(target=app["server"].shutdown, daemon=True).start()
                return
            if path not in ("/api/rating", "/api/cardarch"):
                self._send(t("Nicht gefunden"), "text/plain; charset=utf-8", 404)
                return
            try:
                body = self._body()
                name = body.get("name")
                if name not in known():
                    raise ValueError(t("Unbekannte Karte"))
                with lock:
                    if path == "/api/rating":
                        card_ratings.set_rating(app["ratings"], name, body.get("cat") or "")
                    else:
                        best = body.get("best")
                        if best is not None and not isinstance(best, str):
                            raise ValueError(t("Unbekannter Archetyp"))
                        cardarchetypes.set_assign(app["cardarch"], name, body.get("arch") or [], best)
            except (ValueError, TypeError, OSError) as exc:
                self._json({"ok": False, "error": str(exc)}, 400)
                return
            assign, best = cardarchetypes.load_assign(app["cardarch"]), cardarchetypes.load_best(app["cardarch"])
            self._json({"ok": True, "rating": ratings().get(name, ""), "cardarch": {name: assign.get(name, [])},
                        "cardbest": {name: best.get(name, "")}, "progress": self._set_progress(name)})

        def _set_progress(self, name):
            """Stand des Sets, zu dem die Karte gehoert."""
            for cards in app["cards"].values():
                if any(c["name"] == name for c in cards):
                    return progress(cards, ratings(), cardarchetypes.load_assign(app["cardarch"]))
            return current_progress()

    return Handler


def page_texts():
    """Sichtbare Texte der Seite in der aktuellen Sprache (als JSON in die Seite eingesetzt)."""
    return {
        "loading": t("Lade Set {code} von Scryfall …"),
        "failed": t("Set konnte nicht geladen werden: {err}"),
        "error": t("Fehler"),
        "notSaved": t("Nicht gespeichert: {err}"),
        "progress": t("{done} von {total} Karten fertig · {rated} mit Kategorie · {assigned} mit Archetyp"),
        "shown": t("gezeigt: {n}"),
        "none": t("Keine Karten für diese Auswahl."),
        "best": t("bester Archetyp"),
        "fits": t("passt gut"),
        "archTitle": t("Archetypen dieser Karte. Klick: neutral → grün (passt gut) → lila (bester Archetyp, nur einer) "
                       "→ neutral"),
        "quitAsk": t("Set bewerten beenden?"),
        "quitDone": t("Set bewerten wurde beendet. Du kannst dieses Fenster jetzt schließen."),
        "cats": {
            "matchwinner": t("Bombe: entscheidet ein Match allein – kommt immer rein, notfalls als Splash"),
            "splashworthy": t("Entscheidet Spiele allein – soll auf jeden Fall rein, auch wenn wir die Farbe nicht "
                              "spielen"),
            "mustplay": t("Wird auf jeden Fall gespielt, wenn wir diese Farbe spielen"),
            "playable": t("Solide, wird meist gespielt, wenn wir diese Farbe spielen, aber nicht zwingend"),
            "filler": t("Füllt das Deck auf, wenn wir die Farbe spielen und nicht splashen"),
            "neverplay": t("Zu schlecht oder zu situativ, wird nicht gespielt"),
        },
        "rarity": {"common": "Common", "uncommon": "Uncommon", "rare": "Rare", "mythic": "Mythic"},
    }


PAGE = r"""<!DOCTYPE html>
<html lang="__LANG__"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#f4f6f9;--card:#fff;--ink:#1d2430;--muted:#667085;--line:#d9dee7;--accent:#2f6fd6;
--mw:#8e2bd6;--sw:#e0a800;--mp:#2e9e5b;--pl:#3f8f9a;--fi:#6b7d99;--np:#8b2f2f}
*{box-sizing:border-box}
[hidden]{display:none!important}
body{margin:0;font:14px/1.4 system-ui,"Segoe UI",sans-serif;background:var(--bg);color:var(--ink)}
header{position:sticky;top:0;z-index:5;background:#fff;border-bottom:1px solid var(--line);padding:10px 20px;
  display:flex;flex-direction:column;gap:8px}
.row{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px}
h1{font-size:18px;margin:0 8px 0 0}
.btn{font:inherit;padding:6px 12px;border-radius:8px;border:1px solid var(--line);background:#fff;cursor:pointer}
.btn:hover{border-color:var(--accent)}
#quit{margin-left:auto}
#sets{display:flex;gap:6px;flex-wrap:wrap}
#sets button{font:inherit;font-weight:700;padding:6px 14px;border-radius:999px;border:2px solid var(--line);
  background:#fff;cursor:pointer}
#sets button.on{border-color:var(--accent);background:#e8f0fd;color:#1b4fa3}
.bar{flex:1;min-width:200px;height:10px;border-radius:999px;background:#e6e9ef;overflow:hidden;display:flex}
.bar span{display:block;height:100%}
#ptext{color:var(--muted);font-size:13px}
input[type=search],select{font:inherit;padding:6px 10px;border-radius:8px;border:1px solid var(--line);background:#fff}
input[type=search]{flex:1;min-width:180px}
#legend{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12.5px;color:var(--muted)}
#legend b{color:var(--ink)}
.hint{font-size:12.5px;color:var(--muted)}
main{padding:12px 20px 60px}
#start{max-width:640px;margin:40px auto;text-align:center;color:var(--muted)}
#start .big{display:flex;justify-content:center;gap:16px;margin-top:18px;flex-wrap:wrap}
#start .big button{font:inherit;font-size:22px;font-weight:800;padding:22px 34px;border-radius:14px;
  border:2px solid var(--line);background:#fff;cursor:pointer}
#start .big button:hover{border-color:var(--accent);color:var(--accent)}
#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(172px,1fr));gap:14px}
.tile{background:var(--card);border:2px solid transparent;border-radius:12px;padding:8px;box-shadow:0 1px 3px #0001;
  display:flex;flex-direction:column;gap:6px}
.tile.done{border-color:#cfe9d9}
.tile.hover{outline:2px solid var(--accent)}
.tile img{width:100%;border-radius:8px;display:block;cursor:zoom-in;aspect-ratio:488/680;object-fit:cover;background:#eee}
.tile .ph{aspect-ratio:488/680;border-radius:8px;background:#e6e9ef;display:flex;align-items:center;justify-content:center;
  text-align:center;padding:8px;font-weight:700}
.tile .nm{font-weight:700;font-size:13px;line-height:1.25}
.tile .nm small{font-weight:600;color:var(--muted);margin-left:4px}
.cats{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:3px}
.cats button{font:inherit;font-size:11px;font-weight:700;padding:4px 0;border-radius:6px;border:1px solid var(--line);
  background:#f8f9fb;color:var(--muted);cursor:pointer}
.cats button.on{color:#fff;border-color:transparent}
.cats button.on.matchwinner{background:var(--mw)}.cats button.on.splashworthy{background:var(--sw);color:#2d2100}
.cats button.on.mustplay{background:var(--mp)}.cats button.on.playable{background:var(--pl)}
.cats button.on.filler{background:var(--fi)}.cats button.on.neverplay{background:var(--np)}
.achips{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:3px}
.achips button{border:1px solid var(--line);background:#f8f9fb;border-radius:6px;padding:3px 0;font-size:10.5px;
  cursor:pointer;color:var(--muted);font-weight:600}
.achips button .m.ms{margin:0;width:11px;height:11px;vertical-align:middle}
.achips button.on{background:#e3f4ea;border-color:#2e9e5b;color:#146c3d;font-weight:700}
.achips button.best{background:#f1e4fb;border-color:#8e2bd6;color:#5b1d99;font-weight:700}
.anames{font-size:11.5px;color:var(--muted);min-height:15px}
#lightbox{display:none;position:fixed;inset:0;z-index:20;background:#000c;align-items:center;justify-content:center}
#lightbox.show{display:flex}#lightbox img{max-height:92vh;max-width:92vw;border-radius:14px}
#toast{position:fixed;bottom:16px;left:50%;transform:translateX(-50%);background:#8b2f2f;color:#fff;padding:8px 14px;
  border-radius:8px;display:none;z-index:30}
@media (max-width:700px){header{position:static}main{padding:12px 16px 60px}header{padding:10px 16px}}
@media (prefers-color-scheme:dark){
  :root{--bg:#14181f;--card:#1d232d;--ink:#e6e9ef;--muted:#9aa4b5;--line:#343c4a}
  header,.btn,#sets button,#start .big button,input[type=search],select{background:#1d232d;color:var(--ink)}
  #sets button.on{background:#1f3357;color:#cfe0ff}
  .cats button,.achips button{background:#252c37}
  .achips button.on{background:#1f3b2b;color:#9fe0b8}.achips button.best{background:#35204a;color:#e0c2ff}
  .bar{background:#2a313d}.tile .ph{background:#2a313d}
}
/*SYMBOL_CSS*/
</style></head><body>
<header>
  <div class="row"><h1>__TITLE__</h1><div id="sets"></div>
    <div class="bar" id="progress" title=""></div><button class="btn" id="quit">__QUIT__</button></div>
  <div class="row" id="tools" hidden>
    <input type="search" id="search" placeholder="__SEARCH__">
    <label>__SHOW__ <select id="filter">
      <option value="">__ALL__</option><option value="open">__OPEN__</option>
      <option value="nocat">__NOCAT__</option><option value="noarch">__NOARCH__</option></select></label>
    <label>__COLOR__ <select id="color">
      <option value="">__ALL__</option><option value="W">__W__</option><option value="U">__U__</option>
      <option value="B">__B__</option><option value="R">__R__</option><option value="G">__G__</option>
      <option value="M">__MULTI__</option><option value="C">__COLORLESS__</option></select></label>
    <label>__RARITY__ <select id="rarity"><option value="">__ALL__</option>
      <option value="common">Common</option><option value="uncommon">Uncommon</option>
      <option value="rare">Rare</option><option value="mythic">Mythic</option></select></label>
    <span id="ptext"></span></div>
  <div id="legend" hidden></div>
  <div class="hint" id="keys" hidden>__KEYS__</div>
</header>
<main>
  <div id="start"><p>__INTRO__</p><div class="big" id="bigsets"></div><p id="startnote"></p></div>
  <div id="grid"></div>
</main>
<div id="lightbox"><img alt=""></div><div id="toast"></div>
<script>
const TX=__TX__;
const SYMBOLS=__SYMBOLS__;
const CATS=[["matchwinner","♛","Matchwinner"],["splashworthy","★","Splashworthy"],["mustplay","MP","MustPlay"],
  ["playable","Pl","Playable"],["filler","Fi","Filler"],["neverplay","NP","NeverPlay"]];
const CATCOL={matchwinner:"var(--mw)",splashworthy:"var(--sw)",mustplay:"var(--mp)",playable:"var(--pl)",filler:"var(--fi)",neverplay:"var(--np)"};
let sets=[],code="",cards=[],archs=[],ratings={},cardarch={},cardbest={},prog=null,hover=null;
const tiles=new Map();
const $=id=>document.getElementById(id);
const el=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!=null)e.textContent=text;return e};
const fmt=(s,o)=>s.replace(/\{(\w+)\}/g,(m,k)=>k in o?o[k]:m);
function manaSym(k){if(!SYMBOLS.includes(k))return document.createTextNode(k);const s=el("span","m ms ms-"+k);s.title="{"+k+"}";return s}
function toast(msg){const t=$("toast");t.textContent=msg;t.style.display="block";clearTimeout(toast.h);toast.h=setTimeout(()=>t.style.display="none",4000)}
async function api(path,body){const r=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});return r.json()}
const archName=k=>(archs.find(a=>a.colors===k)||{}).name||k;
const isDone=n=>!!ratings[n]&&((cardarch[n]||[]).length>0||ratings[n]==="neverplay");

function renderSets(){
  const box=$("sets"),big=$("bigsets");box.textContent="";big.textContent="";
  for(const s of sets){const b=el("button",s.code===code?"on":"",s.code);b.onclick=()=>loadSet(s.code);box.appendChild(b);
    const g=el("button",null,s.code);g.onclick=()=>loadSet(s.code);big.appendChild(g)}}
async function loadSet(c){
  code=c;renderSets();$("start").style.display="";$("bigsets").style.display="none";
  $("startnote").textContent=fmt(TX.loading,{code:c});$("grid").textContent="";tiles.clear();
  let r=null;try{r=await (await fetch("/api/setcards?set="+encodeURIComponent(c.toLowerCase()))).json()}catch(e){}
  if(!r||!r.ok){$("startnote").textContent=fmt(TX.failed,{err:(r&&r.error)||TX.error});$("bigsets").style.display="";return}
  cards=r.cards;archs=r.archetypes;ratings=r.ratings||{};cardarch=r.cardarch||{};cardbest=r.cardbest||{};prog=r.progress;
  $("start").style.display="none";["tools","legend","keys"].forEach(i=>$(i).hidden=false);
  const lg=$("legend");lg.textContent="";
  for(const a of archs){const s=el("span");[...a.colors].forEach(x=>s.appendChild(manaSym(x)));s.appendChild(el("b",null," "+a.name));lg.appendChild(s)}
  cards.forEach(cd=>tiles.set(cd.name,makeTile(cd)));renderGrid();renderProgress()}
function shownCards(){
  const q=$("search").value.trim().toLowerCase(),f=$("filter").value,col=$("color").value,rar=$("rarity").value;
  return cards.filter(c=>{const cs=c.colors||[];
    if(q&&!(c.name+" "+(c.type||"")).toLowerCase().includes(q))return false;
    if(rar&&c.rarity!==rar)return false;
    if(col==="M"&&cs.length<2)return false;if(col==="C"&&cs.length)return false;
    if("WUBRG".includes(col)&&col&&!cs.includes(col))return false;
    if(f==="open")return !isDone(c.name);if(f==="nocat")return !ratings[c.name];
    if(f==="noarch")return !(cardarch[c.name]||[]).length;return true})}
function renderGrid(){
  const g=$("grid");g.textContent="";const shown=shownCards();
  shown.forEach(c=>g.appendChild(tiles.get(c.name).node));
  if(!shown.length)g.appendChild(el("p","hint",TX.none));
  $("ptext").textContent=fmt(TX.shown,{n:shown.length})}
function renderProgress(){
  const p=prog||{total:0,done:0,rated:0,assigned:0,cats:{}},bar=$("progress");bar.textContent="";
  for(const [k] of CATS){const n=p.cats[k]||0;if(!n||!p.total)continue;const s=el("span");s.style.width=(100*n/p.total)+"%";
    s.style.background=CATCOL[k];s.title=k+": "+n;bar.appendChild(s)}
  bar.title=fmt(TX.progress,p);$("ptext").textContent=fmt(TX.progress,p)+" · "+fmt(TX.shown,{n:$("grid").querySelectorAll(".tile").length})}
function makeTile(c){
  const d=el("div","tile"),t={node:d,card:c};
  d.onmouseenter=()=>{hover=c.name;d.classList.add("hover")};d.onmouseleave=()=>{if(hover===c.name)hover=null;d.classList.remove("hover")};
  if(c.image){const pic=el("img");pic.src=c.image;pic.alt=c.name;pic.loading="lazy";
    pic.onclick=()=>{$("lightbox").querySelector("img").src=c.large||c.image;$("lightbox").classList.add("show")};d.appendChild(pic)}
  else d.appendChild(el("div","ph",c.name));
  const nm=el("div","nm",c.name);nm.appendChild(el("small",null,(c.rarity||"").charAt(0).toUpperCase()));
  nm.title=(c.type||"")+(c.rarity?" · "+(TX.rarity[c.rarity]||c.rarity):"");d.appendChild(nm);
  t.cats=el("div","cats");
  for(const [k,ab,lb] of CATS){const b=el("button",k,ab);b.dataset.k=k;b.title=lb+": "+TX.cats[k];
    b.onclick=()=>setCat(c.name,ratings[c.name]===k?"":k);t.cats.appendChild(b)}
  d.appendChild(t.cats);
  t.chips=el("div","achips");t.chips.title=TX.archTitle;
  for(const a of archs){const b=el("button");b.dataset.a=a.colors;[...a.colors].forEach(x=>b.appendChild(manaSym(x)));
    b.onclick=()=>toggleArch(c.name,a.colors);t.chips.appendChild(b)}
  d.appendChild(t.chips);t.names=el("div","anames");d.appendChild(t.names);
  paint(t);return t}
function paint(t){
  const n=t.card.name,k=ratings[n]||"",mine=cardarch[n]||[],top=cardbest[n]||"";
  t.cats.querySelectorAll("button").forEach(b=>b.classList.toggle("on",b.dataset.k===k));
  t.chips.querySelectorAll("button").forEach(b=>{const a=b.dataset.a;b.classList.toggle("on",mine.includes(a)&&a!==top);
    b.classList.toggle("best",a===top);b.title=archName(a)+(a===top?" · "+TX.best:mine.includes(a)?" · "+TX.fits:"")});
  t.names.textContent=mine.map(a=>(a===top?"◆ ":"")+archName(a)).join(" · ");
  t.node.classList.toggle("done",isDone(n))}
function applyAnswer(name,r){
  if(!r||!r.ok){toast(fmt(TX.notSaved,{err:(r&&r.error)||TX.error}));return}
  if(r.rating)ratings[name]=r.rating;else delete ratings[name];
  cardarch[name]=r.cardarch[name]||[];if(r.cardbest[name])cardbest[name]=r.cardbest[name];else delete cardbest[name];
  prog=r.progress;paint(tiles.get(name));renderProgress()}
async function setCat(name,cat){let r=null;try{r=await api("/api/rating",{name,cat})}catch(e){}applyAnswer(name,r)}
// Drei Stufen je Archetyp wie im Drafthelper: neutral -> gruen (zugeordnet) -> lila (bester, nur einer) -> neutral
async function toggleArch(name,colors){
  const mine=cardarch[name]||[],top=cardbest[name]||"";let next=mine,best=top;
  if(top===colors){next=mine.filter(x=>x!==colors);best=""}
  else if(mine.includes(colors))best=colors;
  else next=[...mine,colors];
  let r=null;try{r=await api("/api/cardarch",{name,arch:next,best})}catch(e){}applyAnswer(name,r)}
document.addEventListener("keydown",e=>{
  if(e.key==="Escape"){$("lightbox").classList.remove("show");return}
  if(!hover||e.target.tagName==="INPUT"||e.target.tagName==="SELECT"||e.ctrlKey||e.altKey||e.metaKey)return;
  const i="123456".indexOf(e.key);
  if(i>=0){const k=CATS[i][0];setCat(hover,ratings[hover]===k?"":k);e.preventDefault()}
  else if(e.key==="0"||e.key==="Backspace"){setCat(hover,"");e.preventDefault()}});
["search","filter","color","rarity"].forEach(i=>$(i)[i==="search"?"oninput":"onchange"]=()=>{renderGrid();renderProgress()});
$("lightbox").onclick=()=>$("lightbox").classList.remove("show");
$("quit").onclick=async()=>{if(!confirm(TX.quitAsk))return;try{await api("/api/quit",{})}catch(e){}
  document.body.innerHTML="";document.body.appendChild(el("h2",null,TX.quitDone)).style.margin="40px"};
(async()=>{
  let d={sets:[],start:""};try{d=await (await fetch("/api/sets")).json()}catch(e){}
  sets=d.sets;renderSets();if(d.start)loadSet(d.start);
})();
</script></body></html>
"""


def render_page():
    """Die Seite in der aktuellen Sprache, mit den vorhandenen Original-Manasymbolen."""
    have = [k for k in SYMBOL_KEYS if k in active_symbols()]
    parts = {
        "__LANG__": html_lang(), "__TITLE__": t("Set bewerten"), "__QUIT__": t("Beenden"),
        "__SEARCH__": t("Karte suchen (Name oder Typ)"), "__SHOW__": t("Zeigen"), "__ALL__": t("Alle Karten"),
        "__OPEN__": t("Noch offen"), "__NOCAT__": t("Ohne Kategorie"), "__NOARCH__": t("Ohne Archetyp"),
        "__COLOR__": t("Farbe"), "__W__": t("Weiß"), "__U__": t("Blau"), "__B__": t("Schwarz"), "__R__": t("Rot"),
        "__G__": t("Grün"), "__MULTI__": t("Mehrfarbig"), "__COLORLESS__": t("Farblos"),
        "__RARITY__": t("Seltenheit"),
        "__KEYS__": t("Tipp: Maus auf eine Karte und Taste 1 bis 6 drücken (1 = Matchwinner … 6 = NeverPlay, noch "
                      "einmal = entfernen, 0 = entfernen). Archetypen: neutral → grün (passt gut) → lila (bester "
                      "Archetyp) → neutral. Alles wird sofort gespeichert und gilt für jeden Pool und jeden Draft."),
        "__INTRO__": t("Welches Set willst du bewerten? Kategorie und Archetypen legst du hier einmal je Karte fest; "
                       "Drafthelper und Live-Draft nutzen sie danach in jedem Draft."),
    }
    page = PAGE
    for key, value in parts.items():
        page = page.replace(key, value)
    return (page.replace("/*SYMBOL_CSS*/", symbol_css(have))
            .replace("const TX=__TX__;", "const TX=" + json.dumps(page_texts(), ensure_ascii=False) + ";")
            .replace("const SYMBOLS=__SYMBOLS__;", "const SYMBOLS=" + json.dumps(have) + ";"))


def serve(args):
    """Startet die Seite (Menuepunkt 5) und oeffnet den Browser; laeuft bis "Beenden" oder Strg+C."""
    from components.drafthelper import archetypes_path, ratings_path
    from components.scryfall import fetch_set_cards
    app = {"ratings": ratings_path(args), "cardarch": archetypes_path(args), "fetch_set": fetch_set_cards,
           "start": start_set(getattr(args, "set_bewerten", ""))}
    if getattr(args, "set_bewerten", "") and not app["start"]:
        print(t("Set {code} ist nicht umgesetzt, bitte auf der Seite wählen.", code=args.set_bewerten.upper()),
              file=sys.stderr)
    try:
        server = LocalServer(("127.0.0.1", PORT), make_handler(app))
    except OSError:
        server = LocalServer(("127.0.0.1", 0), make_handler(app))
    app["server"] = server
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(t("Set bewerten läuft: {url}", url=url), file=sys.stderr)
    print(t("Zum Beenden: Button 'Beenden' auf der Seite oder Strg+C hier im Fenster."), file=sys.stderr)
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
    print(t("Set bewerten beendet."), file=sys.stderr)
