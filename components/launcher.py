"""Launcher (Nutzer 17.11.2026, Entwurf B "Kommandobruecke"): ein Fenster statt draftgott.bat, fuer Windows und Ubuntu.

Start: Doppelklick auf draftgott.pyw (Windows, ohne Konsole) bzw. "python3 draftgott.pyw" oder der Eintrag im
Ubuntu-Menue (Knopf "Ins Startmenue" im Launcher legt ~/.local/share/applications/draftgott.desktop an).

Startoptionen sind nur noch Live-Draft, Setauswertung und Set bewerten. Drafthelper und Analyse gibt es nicht mehr als
eigenen Start: die Leute draften immer live und machen von dort mit Goldfish-Simulation und Kampf gegen Gegnerdecks
weiter. Fuer Entwicklung und Kommandozeile bleibt mtg_sim.py mit allen Parametern.

Technik wie beim Drafthelper: kleiner Server auf 127.0.0.1 plus HTML-Seite, geoeffnet als App-Fenster von Edge,
Chrome oder Chromium (eigenes Profil in daten/browserprofil), sonst im normalen Browser. Die Seite fragt alle paar
Sekunden den Zustand ab; kommt lange nichts mehr (Fenster zu), beendet sich der Launcher von selbst. Gestartete
Funktionen laufen als eigene Prozesse weiter, ihre Ausgabe landet in daten/log_<modus>.txt."""
import json
import locale
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from components import i18n, paths
from components.draftstats import load_stats
from components.html_base import esc
from components.i18n import t
from components.theme import FONT_MONO, FONT_UI, LOGO_SVG, logo_uri, theme_css

ROOT = paths.ROOT
SCRIPT = ROOT / "mtg_sim.py"
PORT = 8770
VERSION = "0.9"
MODES = ("live", "setreport", "setrate")
STEAM_ARENA = "2141910"  # Steam-Nummer von MTG Arena (Proton-Ordner compatdata/<Nummer>)
IDLE_EXIT = 150      # Sekunden ohne Abfrage: Fenster zu (versteckte Fenster fragen nur noch etwa minuetlich)
FIRST_WAIT = 300     # Sekunden bis zur ersten Abfrage, bevor der Launcher aufgibt
BYE_EXIT = 4         # Sekunden nach dem Schliessen der Seite, wenn sie nicht neu geladen wird


# ---------- Startbefehle ----------

def command(mode, lang, python=None, arena_log=None, set_code=None):
    """Aufruf von mtg_sim.py fuer eine Startoption (Liste fuer subprocess). ValueError bei unbekanntem Modus."""
    py = python or sys.executable
    if mode == "live":
        args = ["--drafthelper", "_livedraft.txt", "--live", "--lang", lang]
        if arena_log:
            args += ["--arena-log", str(arena_log)]
    elif mode == "setreport":
        args = ["--setauswertung"]
        if set_code:
            if not re.fullmatch(r"[A-Za-z0-9]{2,6}", set_code):
                raise ValueError(f"Set: {set_code}")
            args.append(set_code.upper())
        args += ["--lang", lang]
    elif mode == "setrate":
        args = ["--set-bewerten", "--lang", lang]
    else:
        raise ValueError(f"Modus: {mode}")
    return [py, str(SCRIPT)] + args


# ---------- Zustand: Arena, Statistik, Gegnerdecks ----------

def arena_log_candidates(home, system=None):
    """Moegliche Orte von Player.log: Windows direkt, Ubuntu ueber Steam/Proton, Lutris oder Wine."""
    system = system or sys.platform
    home = pathlib.Path(home)
    tail = pathlib.Path("AppData", "LocalLow", "Wizards Of The Coast", "MTGA", "Player.log")
    if system.startswith("win"):
        return [home / tail]
    user_tail = pathlib.Path("drive_c", "users")
    out = []
    for steam in (home / ".steam" / "steam", home / ".local" / "share" / "Steam",
                  home / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam"):
        out.append(steam / "steamapps" / "compatdata" / STEAM_ARENA / "pfx" / user_tail / "steamuser" / tail)
    user = home.name or "user"
    for prefix in (home / "Games" / "magic-the-gathering-arena", home / ".wine"):
        out.append(prefix / user_tail / user / tail)
    return out


def find_arena_log(home=None, system=None):
    home = home or os.path.expanduser("~")
    for p in arena_log_candidates(home, system):
        if p.is_file():
            return p
    return None


def detailed_logs(path, max_lines=400):
    """True/False, wenn Player.log sagt, ob "Detailed Logs" in Arena an sind; None, wenn unbekannt."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if "DETAILED LOGS:" in line:
                    return "ENABLED" in line
                if i >= max_lines:
                    break
    except OSError:
        pass
    return None


def draft_counts(data):
    """[(Set, Anzahl Drafts)], meiste zuerst."""
    c = Counter((d.get("set") or "").upper() for d in data.get("drafts", []) if isinstance(d, dict))
    c.pop("", None)
    return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))


def enemy_deck_count(folder):
    folder = pathlib.Path(folder)
    return sum(1 for _ in folder.rglob("*.txt")) if folder.is_dir() else 0


# ---------- Fenster ----------

def browser_command(url, profile, system=None, which=shutil.which, exists=os.path.exists):
    """Befehl fuer ein App-Fenster (Edge, Chrome, Chromium) oder None, wenn keiner da ist."""
    system = system or sys.platform
    found = None
    if system.startswith("win"):
        for base in (os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"),
                     os.environ.get("ProgramFiles", "C:/Program Files"),
                     os.environ.get("LOCALAPPDATA", "")):
            for rel in ("Microsoft/Edge/Application/msedge.exe", "Google/Chrome/Application/chrome.exe"):
                p = pathlib.Path(base, rel).as_posix() if base else None
                if p and exists(p):
                    found = p
                    break
            if found:
                break
    if not found:
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge",
                     "msedge", "chrome"):
            found = which(name)
            if found:
                break
    if not found:
        return None
    return [found, f"--app={url}", f"--user-data-dir={profile}", "--window-size=1040,700",
            "--no-first-run", "--no-default-browser-check"]


def open_window(url):
    cmd = browser_command(url, str(paths.DATA_DIR / "browserprofil"))
    if cmd:
        try:
            subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             **_detach())
            return
        except OSError:
            pass
    webbrowser.open(url)


def _detach():
    if sys.platform.startswith("win"):
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    return {"start_new_session": True}


def should_exit(now, started, last, bye):
    """Soll sich der Launcher beenden? last: letzte Abfrage der Seite, bye: Zeitpunkt, an dem die Seite zuging."""
    if last is None:
        return now - started > FIRST_WAIT
    if bye is not None and bye >= last and now - bye > BYE_EXIT:
        return True
    return now - last > IDLE_EXIT


# ---------- Ubuntu-Menue ----------

def desktop_entry(root, python):
    root = pathlib.Path(root).as_posix()
    return ("[Desktop Entry]\nType=Application\nName=draftgott\n"
            "Comment=MTG Arena draft helper\nComment[de]=Draft-Helfer fuer MTG Arena\n"
            f'Exec="{python}" "{root}/draftgott.pyw"\nPath={root}\nIcon={root}/assets/draftgott.svg\n'
            "Terminal=false\nCategories=Game;CardGame;\n")


def install_desktop_entry(home=None, root=None, python=None):
    home = pathlib.Path(home or os.path.expanduser("~"))
    target = home / ".local" / "share" / "applications" / "draftgott.desktop"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(desktop_entry(root or ROOT, python or sys.executable), encoding="utf-8")
    try:
        target.chmod(0o755)
    except OSError:
        pass
    return target


def open_folder(path):
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # noqa: S606 (nur der eigene Projektordner)
    else:
        subprocess.Popen(["xdg-open", str(path)], **_detach())


# ---------- Prozesse ----------

class Job:
    """Gestartete Funktion: laeuft sie noch, und wie ging sie aus?"""

    def __init__(self, proc, log):
        self.proc, self.log = proc, log

    def running(self):
        return self.proc.poll() is None

    def code(self):
        return self.proc.poll()

    def tail(self, n=6):
        try:
            lines = pathlib.Path(self.log).read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return ""
        return "\n".join(line for line in lines[-n:] if line.strip())


class FakeJob:
    """Fuer Tests: laeuft, bis stop() gerufen wird."""

    def __init__(self):
        self.done = False

    def running(self):
        return not self.done

    def code(self):
        return 0 if self.done else None

    def tail(self, n=6):
        return ""


def spawn(cmd, mode):
    log = paths.data_file(f"log_{mode}.txt")
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    with open(log, "w", encoding="utf-8") as out:
        proc = subprocess.Popen(cmd, cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                env=env, **_detach())
    return Job(proc, log)


def default_lang():
    try:
        loc = locale.getlocale()[0] or os.environ.get("LANG", "")
    except ValueError:
        loc = os.environ.get("LANG", "")
    return "de" if (loc or "").lower().startswith(("de", "german")) else "en"


class State:
    """Alles, was der Server braucht; spawn und settings lassen sich fuer Tests ersetzen."""

    def __init__(self, settings=None, spawn=spawn):
        self.settings = pathlib.Path(settings) if settings else paths.data_file("launcher.json")
        self.spawn = spawn
        self.jobs = {}
        self.lock = threading.Lock()
        self.started = time.time()
        self.last = None
        self.bye = None
        self.quit = False
        try:
            saved = json.loads(self.settings.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            saved = {}
        self.lang = saved.get("lang") if saved.get("lang") in i18n.LANGS else default_lang()
        i18n.set_lang(self.lang)

    def save(self):
        try:
            self.settings.write_text(json.dumps({"lang": self.lang}) + "\n", encoding="utf-8")
        except OSError:
            pass

    def set_lang(self, lang):
        if lang not in i18n.LANGS:
            raise ValueError(lang)
        self.lang = lang
        i18n.set_lang(lang)
        self.save()

    def status(self):
        log = find_arena_log()
        age = None
        if log:
            try:
                age = int(time.time() - log.stat().st_mtime)
            except OSError:
                pass
        jobs = {}
        for mode, job in self.jobs.items():
            running = job.running()
            code = None if running else job.code()
            jobs[mode] = {"running": running, "code": code, "tail": job.tail() if code else ""}
        return {"python": platform.python_version(), "system": platform.system() or sys.platform,
                "linux": sys.platform.startswith("linux"),
                "arena_log": str(log) if log else None, "arena_age": age,
                "detailed": detailed_logs(log) if log else None,
                "drafts": draft_counts(load_stats(paths.data_file("draftstatistik.json"))),
                "enemy_decks": enemy_deck_count(ROOT / "enemydecks"), "jobs": jobs}

    def start(self, mode, set_code=None):
        with self.lock:
            job = self.jobs.get(mode)
            if job and job.running():
                return False, t("{name} läuft schon.", name=mode_name(mode))
            log = find_arena_log()
            default = arena_log_candidates(os.path.expanduser("~"), "win32")[0]
            extra = str(log) if mode == "live" and log and log != default else None
            cmd = command(mode, self.lang, arena_log=extra, set_code=set_code or None)
            self.jobs[mode] = self.spawn(cmd, mode)
            return True, ""


def mode_name(mode):
    return {"live": t("Live-Draft"), "setreport": t("Setauswertung"), "setrate": t("Set bewerten")}[mode]


# ---------- Server ----------

def make_server(state, port=PORT):
    class Handler(BaseHTTPRequestHandler):
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
            n = int(self.headers.get("Content-Length") or 0)
            try:
                return json.loads(self.rfile.read(n).decode("utf-8") or "{}") if n else {}
            except ValueError:
                return {}

        def do_GET(self):
            state.last = time.time()
            path = self.path.split("?")[0]
            if path == "/":
                self._send(render_page(state.status()))
            elif path == "/api/status":
                self._json(state.status())
            elif path == "/api/ping":
                self._json({"app": "draftgott", "version": VERSION})
            elif path == "/favicon.svg":
                self._send(LOGO_SVG, "image/svg+xml")
            else:
                self._send("not found", "text/plain", 404)

        def do_POST(self):
            path = self.path.split("?")[0]
            body = self._body()
            if path == "/api/bye":
                state.bye = time.time()
                self._json({"ok": True})
                return
            state.last = time.time()
            try:
                if path == "/api/start":
                    mode = body.get("mode")
                    if mode not in MODES:
                        raise ValueError(mode)
                    ok, msg = state.start(mode, body.get("set"))
                    self._json({"ok": ok, "error": msg})
                elif path == "/api/lang":
                    state.set_lang(body.get("lang"))
                    self._json({"ok": True})
                elif path == "/api/folder":
                    open_folder(ROOT)
                    self._json({"ok": True})
                elif path == "/api/desktop":
                    p = install_desktop_entry()
                    self._json({"ok": True, "path": str(p)})
                elif path == "/api/quit":
                    state.quit = True
                    self._json({"ok": True})
                else:
                    self._json({"ok": False, "error": "unknown"}, 404)
            except (ValueError, OSError) as e:
                self._json({"ok": False, "error": t("Nicht möglich: {e}", e=e)})

    class Server(ThreadingHTTPServer):
        daemon_threads = True
        allow_reuse_address = False

    return Server(("127.0.0.1", port), Handler)


def _already_running(url):
    try:
        with urllib.request.urlopen(url + "api/ping", timeout=2) as r:
            return json.loads(r.read().decode("utf-8")).get("app") == "draftgott"
    except (OSError, ValueError):
        return False


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    paths.tidy_up()
    if "--desktop" in argv:
        print(install_desktop_entry())
        return
    state = State()
    try:
        server = make_server(state, PORT)
    except OSError:
        url = f"http://127.0.0.1:{PORT}/"
        if _already_running(url):  # zweiter Doppelklick: vorhandenen Launcher zeigen
            open_window(url)
            return
        server = make_server(state, 0)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    if "--nicht-oeffnen" not in argv:
        open_window(url)
    try:
        while not state.quit and not should_exit(time.time(), state.started, state.last, state.bye):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    server.shutdown()
    server.server_close()


# ---------- Seite ----------

def _icon(name):
    icons = {
        "live": '<circle cx="20" cy="20" r="14"/><circle cx="20" cy="20" r="5"/><path d="M20 3v7M20 30v7M3 20h7M30 20h7"/>',
        "setreport": '<path d="M6 34h28M10 34V22M17 34V12M24 34V18M31 34V7"/>',
        "setrate": '<path d="M20 5l4.5 9.5 10.5 1.3-7.7 7.2 2 10.4L20 28.3 10.7 33.4l2-10.4L5 15.8l10.5-1.3z"/>',
    }
    return (f'<svg class="ico" viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="1.6" '
            f'stroke-linejoin="round" aria-hidden="true">{icons[name]}</svg>')


def _chips(st):
    out = [f'<span class="chip ok"><i></i>Python {esc(st["python"])}</span>']
    if st.get("arena_log"):
        out.append(f'<span class="chip ok" title="{esc(st["arena_log"])}"><i></i>{t("Arena-Protokoll gefunden")}</span>')
        if st.get("detailed") is False:
            out.append(f'<span class="chip warn" title="{esc(t("In Arena: Optionen – Konto – Detailed Logs (Plugin Support) einschalten"))}">'
                       f'<i></i>{t("Detailed Logs aus")}</span>')
        elif st.get("detailed"):
            out.append(f'<span class="chip ok"><i></i>{t("Detailed Logs an")}</span>')
        else:
            out.append(f'<span class="chip warn" title="{esc(t("In Arena: Optionen – Konto – Detailed Logs (Plugin Support) einschalten"))}">'
                       f'<i></i>{t("Detailed Logs prüfen")}</span>')
    else:
        out.append(f'<span class="chip warn" title="{esc(t("Arena einmal starten, dann findet der Launcher das Protokoll."))}">'
                   f'<i></i>{t("Arena-Protokoll nicht gefunden")}</span>')
    return "".join(out)


def _bars(drafts):
    if not drafts:
        return f'<p class="empty">{t("Noch keine Drafts gesammelt. Nach dem ersten Live-Draft steht hier, wie viele Drafts je Set da sind.")}</p>'
    top = drafts[0][1] or 1
    rows = "".join(f'<div><span>{esc(code)}</span><s style="--w:{round(100 * n / top)}%"></s><b>{n}</b></div>'
                   for code, n in drafts[:3])
    return f'<div class="bars"><div class="bh">{t("Drafts je Set")}</div>{rows}</div>'


def render_page(st):
    lang = i18n.get_lang()
    drafts = st.get("drafts") or []
    options = "".join(f'<option value="{esc(c)}"{" selected" if i == 0 else ""}>{esc(c)} · {n}</option>'
                      for i, (c, n) in enumerate(drafts))
    set_select = (f'<label class="setsel" title="{esc(t("Set der Auswertung"))}">{t("Set")} '
                  f'<select id="repset">{options}</select></label>' if drafts else "")
    desktop = (f'<button class="lbtn" id="desktop">{t("Ins Startmenü")}</button>' if st.get("linux") else "")
    texts = {"running": t("läuft"), "start": t("Starten"), "started": t("Gestartet."),
             "failed": t("{name} wurde mit einem Fehler beendet:"), "quit": t("Der Launcher ist beendet. Du kannst das Fenster schließen."),
             "desktop": t("Eintrag im Startmenü angelegt: {path}"),
             "names": {m: mode_name(m) for m in MODES}}
    return PAGE.format(
        lang=lang, title=t("draftgott"), favicon=esc(logo_uri()), css=theme_css() + CSS, ui=FONT_UI, mono=FONT_MONO,
        version=VERSION, chips=_chips(st),
        live=_icon("live"), setreport=_icon("setreport"), setrate=_icon("setrate"),
        h_live=t("Live-Draft"), ready=t("Bereit für Arena"),
        d_live=t("Liest MTG Arena mit, bewertet jedes Pack, erkennt deinen Archetyp und blendet die Säulen über dem Spiel ein."),
        after=t("Nach dem Draft geht es im selben Fenster weiter: {goldfish} simulieren oder gegen Gegnerdecks kämpfen.",
                goldfish=f'<b>{t("Goldfish")}</b>'),
        bars=_bars(drafts), enemy=t("{n} Gegnerdecks gesammelt", n=st.get("enemy_decks", 0)),
        b_live=t("Live-Draft starten"),
        h_report=t("Setauswertung"), d_report=t("Was deine Drafts eines Sets ergeben haben: Karten, Farben, Siege."),
        set_select=set_select, b_report=t("Auswertung öffnen"),
        h_rate=t("Set bewerten"), d_rate=t("Kategorie und Archetypen je Karte einmal festlegen. Gilt danach für jeden Draft."),
        b_rate=t("Set bewerten starten"),
        folder=t("Ordner öffnen"), desktop=desktop, quit=t("Beenden"),
        de_on=" on" if lang == "de" else "", en_on=" on" if lang == "en" else "",
        texts=json.dumps(texts, ensure_ascii=False).replace("</", "<\\/"),
        hint_arena=esc(t("In Arena muss unter Optionen – Konto „Detailed Logs (Plugin Support)“ eingeschaltet sein.")))


CSS = """
/* Launcher: Kopf mit Marke und Zustand, links gross der Live-Draft, rechts die zwei Set-Seiten, unten Sprache und Knoepfe */
html,body{height:100%}
body{margin:0;display:flex;flex-direction:column;font-size:15px;line-height:1.45}
.top{display:flex;flex-wrap:wrap;gap:12px 24px;align-items:center;justify-content:space-between;padding:18px 26px;
  border-bottom:1px solid var(--dg-line);background:#0a0e14}
.brand{display:flex;gap:12px;align-items:center}
.brand img{width:36px;height:36px}
.brand b{font-size:23px;letter-spacing:-.01em}
.brand small{display:block;font-family:var(--mono);color:var(--dg-muted);font-size:11px}
.chips{display:flex;flex-wrap:wrap;gap:8px;font-family:var(--mono);font-size:11.5px}
.chip{border:1px solid var(--dg-line);border-radius:6px;padding:5px 9px;display:flex;gap:7px;align-items:center;color:var(--dg-muted)}
.chip i{width:7px;height:7px;border-radius:50%;background:var(--dg-accent);display:block}
.chip.warn{color:var(--dg-amber);border-color:#5a4520}.chip.warn i{background:var(--dg-amber)}
main{flex:1;display:grid;grid-template-columns:1.3fr 1fr;grid-template-rows:auto auto;gap:16px;padding:22px 26px;
  align-content:start;max-width:1200px;width:100%;margin:0 auto;box-sizing:border-box}
.tile{background:var(--dg-panel);border:1px solid var(--dg-line);border-radius:12px;padding:20px;display:flex;
  flex-direction:column;gap:10px;min-width:0;transition:border-color .15s,transform .15s}
.tile:hover{border-color:var(--dg-line2)}
.tile h2{margin:0;font-size:19px;font-weight:600;display:flex;gap:10px;align-items:center}
.tile p{margin:0;color:var(--dg-muted);font-size:14px}
.ico{width:26px;height:26px;color:var(--dg-accent);flex:none}
.hero{grid-row:span 2;background:linear-gradient(160deg,rgba(59,227,208,.15),rgba(59,227,208,0) 55%),var(--dg-panel);
  border-color:rgba(59,227,208,.45);padding:24px}
.hero h2{font-size:34px;font-weight:700;letter-spacing:-.02em}
.hero h2 .ico{width:38px;height:38px}
.hero .after{color:var(--dg-text);font-size:14px;border-left:3px solid var(--dg-accent);padding:2px 0 2px 10px}
.live{display:inline-flex;gap:8px;align-items:center;font-family:var(--mono);font-size:11px;color:var(--dg-accent);
  letter-spacing:.08em;text-transform:uppercase}
.live i{width:8px;height:8px;border-radius:50%;background:var(--dg-accent);animation:pulse 1.8s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(59,227,208,.6)}70%{box-shadow:0 0 0 9px rgba(59,227,208,0)}100%{box-shadow:0 0 0 0 rgba(59,227,208,0)}}
@media (prefers-reduced-motion:reduce){.live i{animation:none}}
.bars{display:flex;flex-direction:column;gap:7px;font-family:var(--mono);font-size:12px;color:var(--dg-muted);margin-top:4px}
.bars .bh{text-transform:uppercase;letter-spacing:.08em;font-size:10.5px}
.bars div:not(.bh){display:grid;grid-template-columns:52px 1fr 36px;gap:10px;align-items:center}
.bars b{color:var(--dg-text);text-align:right;font-weight:600}
.bars s{display:block;height:6px;border-radius:3px;background:var(--dg-line);text-decoration:none;position:relative;overflow:hidden}
.bars s::after{content:"";position:absolute;inset:0;width:var(--w);background:var(--dg-accent);border-radius:3px}
.empty{font-size:13px}
.meta{font-family:var(--mono);font-size:11.5px;color:var(--dg-muted)}
.go{margin-top:auto;align-self:flex-start;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.start{font:inherit;font-weight:700;font-size:15px;border-radius:8px;padding:11px 20px;cursor:pointer;border:1px solid var(--dg-line2);
  background:var(--dg-panel2);color:var(--dg-text)}
.start:hover:not(:disabled){border-color:var(--dg-accent)}
.start.pri{background:var(--dg-accent);border-color:var(--dg-accent);color:var(--dg-on-accent);font-size:16px;padding:13px 24px}
.start.pri:hover:not(:disabled){filter:brightness(1.08)}
.start:disabled{opacity:.6;cursor:default}
.run{display:none;font-family:var(--mono);font-size:11px;color:var(--dg-accent);border:1px solid rgba(59,227,208,.45);
  border-radius:999px;padding:2px 9px;letter-spacing:.06em;text-transform:uppercase}
.tile.running .run{display:inline-block}
.setsel{font-size:13px;color:var(--dg-muted);display:flex;gap:6px;align-items:center}
.setsel select{font:inherit;font-family:var(--mono);font-size:12.5px;padding:6px 8px;border-radius:7px;border:1px solid var(--dg-line2)}
.msg{grid-column:1/-1;display:none;border-radius:10px;padding:10px 14px;font-size:13.5px;white-space:pre-wrap;
  background:var(--dg-badbg);color:var(--dg-bad);border:1px solid #6a2a2a}
.msg.ok{background:var(--dg-goodbg);color:var(--dg-good);border-color:#24553a}
.msg.show{display:block}
.msg code{display:block;margin-top:6px;font-size:12px;color:var(--dg-text);opacity:.85}
.bot{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;padding:12px 26px;
  border-top:1px solid var(--dg-line);font-family:var(--mono);font-size:12px;color:var(--dg-muted)}
.bot .grp{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.lbtn{font:inherit;color:var(--dg-text);background:none;border:1px solid var(--dg-line2);border-radius:6px;padding:4px 11px;cursor:pointer}
.lbtn:hover{border-color:var(--dg-accent)}
.lbtn.on{border-color:var(--dg-accent);color:var(--dg-accent)}
#quit:hover{border-color:var(--dg-bad);color:var(--dg-bad)}
body.ended main,body.ended .bot .grp{opacity:.35;pointer-events:none}
@media (max-width:760px){main{grid-template-columns:1fr;padding:16px}.hero{grid-row:auto}.top,.bot{padding-left:16px;padding-right:16px}}
"""

PAGE = """<!DOCTYPE html>
<html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<link rel="icon" href="{favicon}">
<style>:root{{--mono:{mono}}}{css}</style></head>
<body>
<header class="top">
  <div class="brand"><img src="{favicon}" alt=""><div><b>draftgott</b><small>v{version}</small></div></div>
  <div class="chips" id="chips">{chips}</div>
</header>
<main>
  <section class="tile hero" data-tile="live">
    <span class="live"><i></i>{ready}</span>
    <h2>{live}{h_live} <span class="run"></span></h2>
    <p>{d_live}</p>
    <p class="after">{after}</p>
    {bars}
    <div class="meta">{enemy}</div>
    <div class="go"><button class="start pri" data-mode="live" title="{hint_arena}">{b_live}</button></div>
  </section>
  <section class="tile" data-tile="setreport">
    <h2>{setreport}{h_report} <span class="run"></span></h2>
    <p>{d_report}</p>
    <div class="go">{set_select}<button class="start" data-mode="setreport">{b_report}</button></div>
  </section>
  <section class="tile" data-tile="setrate">
    <h2>{setrate}{h_rate} <span class="run"></span></h2>
    <p>{d_rate}</p>
    <div class="go"><button class="start" data-mode="setrate">{b_rate}</button></div>
  </section>
  <div class="msg" id="msg" role="status"></div>
</main>
<footer class="bot">
  <span class="grp"><button class="lbtn{de_on}" data-lang="de">DE</button><button class="lbtn{en_on}" data-lang="en">EN</button></span>
  <span class="grp"><button class="lbtn" id="folder">{folder}</button>{desktop}<button class="lbtn" id="quit">{quit}</button></span>
</footer>
<script>
const TX={texts};
const $=s=>document.querySelector(s);
async function post(path,body){{
  try{{const r=await fetch(path,{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify(body||{{}})}});return await r.json()}}
  catch(e){{return {{ok:false,error:String(e)}}}}
}}
function msg(text,ok,detail){{
  const m=$("#msg");m.textContent=text;m.className="msg show"+(ok?" ok":"");
  if(detail){{const c=document.createElement("code");c.textContent=detail;m.appendChild(c)}}
}}
const seen={{}};
function apply(st){{
  for(const [mode,j] of Object.entries(st.jobs||{{}})){{
    const tile=document.querySelector('[data-tile="'+mode+'"]');if(!tile)continue;
    tile.classList.toggle("running",j.running);
    tile.querySelector(".run").textContent=TX.running;
    const b=tile.querySelector(".start");if(mode!=="setreport")b.disabled=j.running;
    if(!j.running&&j.code&&seen[mode]!=="err"){{seen[mode]="err";msg(TX.failed.replace("{{name}}",TX.names[mode]),false,j.tail)}}
    if(j.running)seen[mode]="run";
  }}
}}
async function poll(){{
  try{{const r=await fetch("/api/status");apply(await r.json())}}catch(e){{}}
}}
document.querySelectorAll(".start").forEach(b=>b.addEventListener("click",async()=>{{
  const mode=b.dataset.mode,body={{mode}};
  if(mode==="setreport"&&$("#repset"))body.set=$("#repset").value;
  b.disabled=true;
  const r=await post("/api/start",body);
  if(r.ok){{seen[mode]="run";msg(TX.names[mode]+": "+TX.started,true)}}else msg(r.error||"?",false);
  setTimeout(()=>{{b.disabled=false;poll()}},1500);
}}));
document.querySelectorAll("[data-lang]").forEach(b=>b.addEventListener("click",async()=>{{
  if(b.classList.contains("on"))return;
  const r=await post("/api/lang",{{lang:b.dataset.lang}});if(r.ok)location.reload();
}}));
$("#folder").addEventListener("click",()=>post("/api/folder"));
if($("#desktop"))$("#desktop").addEventListener("click",async()=>{{
  const r=await post("/api/desktop");if(r.ok)msg(TX.desktop.replace("{{path}}",r.path),true);else msg(r.error||"?",false);
}});
$("#quit").addEventListener("click",async()=>{{
  await post("/api/quit");document.body.classList.add("ended");msg(TX.quit,true);setTimeout(()=>window.close(),600);
}});
window.addEventListener("pagehide",()=>{{try{{navigator.sendBeacon("/api/bye","{{}}")}}catch(e){{}}}});
poll();setInterval(poll,3000);
</script>
</body></html>
"""
