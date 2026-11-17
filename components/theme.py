"""Gemeinsames Aussehen aller draftgott-Seiten (Nutzer 17.11.2026, Entwurf B "Kommandobruecke"): dunkle Flaeche,
tuerkiser Akzent, Space Grotesk fuer Text und JetBrains Mono fuer Zahlen und Dateinamen (wenn installiert, sonst die
Systemschrift). Launcher, Drafthelper, Bericht, Kampfbericht, Setauswertung, Turnierbericht und Set bewerten haengen
THEME_CSS hinter ihr eigenes CSS; so gewinnen die Farbwerte hier und alles wirkt aus einem Guss.

Keine Schrift aus dem Netz: die Seiten laufen lokal und sollen ohne Internet gleich aussehen."""

FONT_UI = '"Space Grotesk","Segoe UI Variable Text","Segoe UI",Ubuntu,Cantarell,system-ui,sans-serif'
FONT_MONO = '"JetBrains Mono","Cascadia Mono",Consolas,"Ubuntu Mono",ui-monospace,monospace'

# Farben (Name: Wert); als CSS-Variablen --dg-<name>
COLORS = {
    "bg": "#0d1117", "panel": "#151b24", "panel2": "#1b2330", "raise": "#202938",
    "line": "#243040", "line2": "#2f3d52", "text": "#e6edf5", "muted": "#8796a8",
    "accent": "#3be3d0", "on-accent": "#05211e", "amber": "#ffb547",
    "good": "#5fd38f", "goodbg": "#12301f", "warn": "#ffc565", "warnbg": "#3a2a0c",
    "bad": "#ff8a80", "badbg": "#3a1616",
}

# Logo: Rahmen mit "D" und Punkt (wie im Launcher), als Daten-URI fuer CSS
LOGO_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 34 34">'
            '<rect x="1" y="1" width="32" height="32" rx="8" fill="none" stroke="#3be3d0" stroke-width="1.6"/>'
            '<path d="M10 9h7a8 8 0 010 16h-7z" fill="none" stroke="#e6edf5" stroke-width="2.2"/>'
            '<circle cx="17" cy="17" r="2.6" fill="#3be3d0"/></svg>')


def logo_uri():
    return "data:image/svg+xml," + (LOGO_SVG.replace("#", "%23").replace('"', "'").replace("<", "%3C")
                                    .replace(">", "%3E"))


def _vars():
    return ";".join(f"--dg-{k}:{v}" for k, v in COLORS.items())


def theme_css():
    """CSS, das hinter das eigene CSS einer Seite kommt: Farbwerte der Seiten auf das draftgott-Schema, Schrift,
    Kopfleiste mit Logo, Knoepfe, Eingabefelder, Bildlaufleisten und Fokusrahmen."""
    return (
        ":root{" + _vars() + ";color-scheme:dark;"
        # Namen, die die einzelnen Seiten fuer ihre Grundfarben benutzen
        "--bg:var(--dg-bg);--panel:var(--dg-panel);--card:var(--dg-panel);--text:var(--dg-text);--ink:var(--dg-text);"
        "--muted:var(--dg-muted);--line:var(--dg-line);--soft:var(--dg-panel2);--chip:var(--dg-panel2);"
        "--track:var(--dg-line);--accent:var(--dg-accent);"
        "--good:var(--dg-good);--goodbg:var(--dg-goodbg);--warn:var(--dg-warn);--warnbg:var(--dg-warnbg);"
        "--bad:var(--dg-bad);--badbg:var(--dg-badbg)}\n"
        "body{background:var(--dg-bg);color:var(--dg-text);font-family:" + FONT_UI + "}\n"
        "code,kbd,pre,textarea,.mono{font-family:" + FONT_MONO + "}\n"
        "a{color:var(--dg-accent)}\n"
        # Kopfleisten aller Seiten
        "header.top,header.bar,body>header,#results .rbar,#setview .sbar{background:#0a0e14;"
        "border-bottom:1px solid var(--dg-line)}\n"
        "header.top h1,header.bar h1,body>header h1{display:flex;align-items:center;gap:10px;"
        "letter-spacing:-.01em;font-weight:700}\n"
        "header.top h1::before,header.bar h1::before,body>header h1::before{content:\"\";width:26px;height:26px;"
        "flex:none;background:url(\"" + logo_uri() + "\") center/contain no-repeat}\n"
        # Knoepfe: Hauptknopf tuerkis mit dunkler Schrift, sonst dunkel mit Rahmen
        ".btn{background:var(--dg-panel2);color:var(--dg-text);border-color:var(--dg-line2)}\n"
        ".btn:hover:not(:disabled){border-color:var(--dg-accent)}\n"
        ".btn.primary,#go,.fightbar #fbgo{background:var(--dg-accent);border-color:var(--dg-accent);"
        "color:var(--dg-on-accent)}\n"
        ".btn.primary:hover:not(:disabled){filter:brightness(1.08)}\n"
        "input,select,textarea{background:var(--dg-panel2);color:var(--dg-text);border-color:var(--dg-line2)}\n"
        ":focus-visible{outline:2px solid var(--dg-accent);outline-offset:2px}\n"
        "::selection{background:#3be3d055}\n"
        "*{scrollbar-color:var(--dg-line2) var(--dg-bg)}\n"
        # Drucken: helle Werte, damit Text auf Papier lesbar bleibt
        "@media print{:root{--bg:#fff;--panel:#fff;--card:#fff;--text:#111;--ink:#111;--muted:#555;--line:#ccc;"
        "--soft:#f3f3f3;--chip:#f3f3f3;color-scheme:light}body{background:#fff;color:#111}}\n"
    )
