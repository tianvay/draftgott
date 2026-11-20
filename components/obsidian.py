"""Obsidian-Export (Nutzer 20.11.2026): die Draft-Statistik (components/draftstats.py) als verlinkte Markdown-Notizen
in einem Obsidian-Vault, damit die Graph-Ansicht zeigt, welche Karten, Archetypen und Drafts zusammenhaengen.

Vault: standardmaessig daten/obsidian (wie alle eigenen Daten nicht im Git; --obsidian ORDNER lenkt um). In Obsidian
"Ordner als Vault oeffnen" waehlen. Ordner (sprachunabhaengig, damit ein Sprachwechsel keine Doppel erzeugt):
  Drafts/<Datum> <SET> <Format>.md   je Draft: Bilanz, Archetyp, Deck, Sideboard, Picks je Pack, Matches
  Cards/<Name>.md                    je gedraftete Karte (ohne Standardlaender): Set, Kosten, Bewertung, Archetypen,
                                     Zahlen wie in der Setauswertung, Kartentext (aus dem Scryfall-Cache)
  Sets/<SET>.md                      je Set: Summen, Archetypen, alle Drafts
  Archetypes/<SET> <Farben> <Name>.md je Archetyp eines Sets mit Archetypen (components/archetypes.py)
Dateinamen ohne Zeichen, die Windows oder Obsidian-Links nicht vertragen (safe_name); weicht der Name ab, steht der
echte Name als alias im Kopf und Links lauten [[Dateiname|Name]].

Erzeugte Notizen tragen "draftgott: generated" im Kopf. Alles unter der Zeile MARKER gehoert dem Nutzer und bleibt
bei jedem Export erhalten; Dateien ohne diese Kennung (eigene Notizen gleichen Namens) werden nie angefasst. Nur
geaenderte Dateien werden geschrieben. .obsidian/graph.json (Farben der Ordner im Graph) entsteht nur, wenn es fehlt.

Ausloeser: python mtg_sim.py --obsidian [ORDNER] und automatisch im Live-Draft (AutoExport), wenn sich die
Draft-Statistik aendert (Picks, Deck, Matches), gebuendelt nach DELAY Sekunden, ohne Netzwerk (nur Scryfall-Cache).
"""
import json
import pathlib
import re
import sys
import threading
import urllib.error

from components import archetypes as set_archetypes
from components import cardarchetypes
from components import draftstats as ds
from components import paths
from components import ratings as card_ratings
from components.i18n import dec, t

DEFAULT_VAULT = "obsidian"
MARKER = "%% draftgott ▲ export | own notes / eigene Notizen ▼ %%"
GENERATED = "draftgott: generated"
DELAY = 5.0
RATING_LABEL = {"matchwinner": "Matchwinner", "splashworthy": "Splashworthy", "mustplay": "MustPlay",
                "playable": "Playable", "filler": "Filler", "neverplay": "NeverPlay"}
_BAD = re.compile(r'[<>:"/\\|?*#^\[\]]+')
_PLAIN = re.compile(r"^[\w .\-/+]+$")
GRAPH = {"colorGroups": [
    {"query": "path:Drafts", "color": {"a": 1, "rgb": 0xE0B040}},
    {"query": "path:Archetypes", "color": {"a": 1, "rgb": 0xA070E0}},
    {"query": "path:Sets", "color": {"a": 1, "rgb": 0x50C080}},
    {"query": "path:Cards", "color": {"a": 1, "rgb": 0x5090E0}},
]}


def vault_path(name):
    """Vault-Ordner: ein blosser Name liegt in daten (wie alle eigenen Daten), sonst der Pfad wie angegeben."""
    return paths.data_file(name or DEFAULT_VAULT)


def safe_name(name):
    """Dateiname ohne Zeichen, die Windows oder Obsidian-Links stoeren ("Kirk: Captain" -> "Kirk - Captain")."""
    out = name.replace(" // ", " - ")
    out = re.sub(r"\s*:\s*", " - ", out)
    out = _BAD.sub("-", out)
    out = re.sub(r"\s+", " ", out).strip(" .-")
    return out or "_"


def link(name, target=None):
    """Obsidian-Link auf die Notiz zu name (Datei safe_name(target or name)), mit Anzeigename, wenn er abweicht."""
    file = safe_name(target or name)
    return f"[[{file}]]" if file == name else f"[[{file}|{name}]]"


def _val(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_val(x) for x in v) + "]"
    s = str(v)
    return s if s and _PLAIN.match(s) and s.strip() == s else json.dumps(s, ensure_ascii=False)


def _front(fields):
    lines = ["---", GENERATED]
    lines += [f"{k}: {_val(v)}" for k, v in fields.items() if v not in (None, "", [])]
    return "\n".join(lines + ["---", ""])


def _tail():
    return f"\n{MARKER}\n\n{t('## Eigene Notizen')}\n\n"


def _note(fields, body):
    return _front(fields) + body.rstrip("\n") + "\n" + _tail()


def _is_card(name):
    return bool(name) and name not in ds.BASICS and not name.startswith("#")


def _colors(cards):
    out = {}
    for name, sc in cards.items():
        sc = sc or {}
        faces = sc.get("card_faces") or []
        out[name] = sc.get("colors") or (faces[0].get("colors") if faces else None) or []
    return out


def _arch_title(code, a):
    return f"{code} {a['colors']} {a['name']}"


def _results(rec):
    return [m for m in rec.get("matches") or [] if m.get("win") is not None]


def _games(ms):
    won = sum(1 for m in ms for g in m.get("games") or [] if g)
    return won, sum(len(m.get("games") or []) for m in ms) - won


def _pct(won, total):
    return f" ({round(100 * won / total)} %)" if total else ""


def _packs(rec):
    """Picks je Pack: ein neues Pack beginnt, wenn die Packgroesse wieder steigt."""
    sizes = list(rec.get("pick_sizes") or [])
    packs, prev = [], None
    for i, name in enumerate(rec.get("picks") or []):
        size = sizes[i] if i < len(sizes) else None
        if not packs or (size and prev and size > prev):
            packs.append([])
        if size:
            prev = size
        packs[-1].append(name)
    return packs


def _card_ref(name, known):
    return link(name) if name in known else name


def _deck_lines(cards, known):
    real = sorted((n for n in cards if _is_card(n)), key=lambda n: (-cards[n], n))
    rest = sorted(n for n in cards if not _is_card(n))
    return [f"- {cards[n]} {_card_ref(n, known)}" for n in real] + [f"- {cards[n]} {n}" for n in rest]


def _draft_titles(records):
    """Notizname je Draft (in Reihenfolge der Statistik): "<Datum> <SET> <Format>", Doppel mit " (2)", " (3)" ..."""
    seen, out = {}, []
    for rec in records:
        fmt = ds.FORMATS[ds.event_format(rec.get("event"))]["label"]
        base = safe_name(f"{rec.get('started') or '0000-00-00'} {(rec.get('set') or '').upper() or '-'} {fmt}")
        seen[base] = seen.get(base, 0) + 1
        out.append(base if seen[base] == 1 else f"{base} ({seen[base]})")
    return out


def build_notes(data, cards, assign, ratings):
    """{Pfad im Vault: Inhalt} aller Notizen. cards: Scryfall-Daten je Kartenname (darf fehlen), assign: eigene
    Archetyp-Zuordnung, ratings: Kategorie je Karte."""
    cards, assign, raw = cards or {}, assign or {}, ratings or {}
    ratings = {n: RATING_LABEL.get(c, c) for n, c in raw.items()}  # Anzeige wie im Drafthelper
    records = list(data.get("drafts", []))
    colors = _colors(cards)
    titles = _draft_titles(records)
    notes = {}

    # Archetypen je Set und Archetyp je Draft
    arch_of_set = {}
    for rec in records:
        code = (rec.get("set") or "").upper()
        if code and code not in arch_of_set:
            arch_of_set[code] = {a["colors"]: a for a in set_archetypes.for_set(code) or []}
    rec_arch = [ds.record_archetype(r, colors, assign, raw) if arch_of_set.get((r.get("set") or "").upper())
                else None for r in records]

    # Karten: aus Picks und Decks
    card_set = {}
    for rec in records:
        deck = rec.get("deck") or {}
        for name in list(rec.get("picks") or []) + list(deck.get("main") or {}) + list(deck.get("side") or {}):
            if _is_card(name):
                card_set.setdefault(name, (rec.get("set") or "").upper())
    known = set(card_set)
    stats = ds.card_stats(data)

    def arch_link(code, pair):
        a = arch_of_set.get(code, {}).get(pair)
        return link(_arch_title(code, a)) if a else pair

    # Drafts
    for rec, title, arch in zip(records, titles, rec_arch):
        code = (rec.get("set") or "").upper()
        st = ds.run_state(rec)
        ms = _results(rec)
        gw, gl = _games(ms)
        deck = rec.get("deck") or {}
        fmt = ds.FORMATS[st["format"]]["label"]
        head = [f"# {title}", "",
                f"{t('Set')}: {link(code) if code else '-'} · {t('Archetyp')}: "
                f"{arch_link(code, arch) if arch else t('offen')} · {t('Bilanz')} {st['wins']}-{st['losses']} "
                f"({t('Games {a}-{b}', a=gw, b=gl)})" + (" · 🏆" if st["trophy"] else "")]
        if rec.get("event"):
            head.append(f"{t('Event')}: {rec['event']}")
        if rec.get("enemy_deck"):
            head.append(f"{t('Gegnerdeck')}: enemydecks/{rec['enemy_deck']}")
        body = head
        if deck.get("main"):
            body += ["", f"## {t('Deck')} ({sum(deck['main'].values())})"] + _deck_lines(deck["main"], known)
        if deck.get("side"):
            body += ["", f"## {t('Sideboard')} ({sum(deck['side'].values())})"] + _deck_lines(deck["side"], known)
        packs = _packs(rec)
        if packs:
            body += ["", f"## {t('Picks')}"]
            body += [f"- {t('Pack {n}', n=i)}: " + ", ".join(_card_ref(n, known) for n in p if not n.startswith("#"))
                     for i, p in enumerate(packs, 1)]
        if rec.get("matches"):
            body += ["", f"## {t('Matches')}"]
            for i, m in enumerate(rec["matches"], 1):
                won = sum(1 for g in m.get("games") or [] if g)
                lost = len(m.get("games") or []) - won
                body.append(f"{i}. " + (t("läuft noch") if m.get("win") is None else
                                        t("Sieg {a}-{b}", a=won, b=lost) if m["win"] else
                                        t("Niederlage {a}-{b}", a=won, b=lost)))
        fields = {"type": "draft", "set": code, "format": fmt, "event": rec.get("event"),
                  "date": rec.get("started"), "wins": st["wins"], "losses": st["losses"], "archetype": arch,
                  "trophy": st["trophy"], "tags": ["draftgott/draft"] + ([f"set/{code}"] if code else [])}
        notes[f"Drafts/{title}.md"] = _note(fields, "\n".join(body))

    # Karten
    for name, code in sorted(card_set.items()):
        sc = cards.get(name) or {}
        faces = sc.get("card_faces") or []
        front = faces[0] if faces and not sc.get("mana_cost") else sc
        s = stats.get(name) or {}
        pairs = assign.get(name, [])
        printed = (sc.get("set") or "").upper()  # Gastkarte (z. B. MH3 im TRK-Draft): gehoert zum Set des Drafts
        printed = printed if printed and printed != code else ""
        lines = [f"# {name}", "",
                 " · ".join(x for x in (f"{t('Set')}: {link(code)}" if code else "",
                                        f"{t('Druck')}: {printed}" if printed else "", front.get("mana_cost") or "",
                                        front.get("type_line") or sc.get("type_line") or "",
                                        sc.get("rarity") or "") if x)]
        if ratings.get(name):
            lines.append(f"{t('Bewertung')}: {ratings[name]}")
        if pairs:
            lines.append(f"{t('Archetypen')}: " + ", ".join(arch_link(code, p) for p in pairs))
        lines += ["", f"## {t('Zahlen')}",
                  f"- {t('Gedraftet: {n} (in {d} Drafts)', n=s.get('drafted', 0), d=s.get('drafts', 0))}",
                  f"- {t('Im Deck: {n}', n=s.get('decks', 0))}"]
        if s.get("avg_pick"):
            lines.append(f"- {t('Ø Pick: {x}', x=dec(str(s['avg_pick'])))}")
        if s.get("games"):
            lines.append(f"- {t('Games {a}-{b}', a=s['wins'], b=s['games'] - s['wins'])}{_pct(s['wins'], s['games'])}"
                         f" · {t('Matches {a}-{b}', a=s['match_wins'], b=s['matches'] - s['match_wins'])}")
        text = sc.get("oracle_text") or "\n//\n".join(f.get("oracle_text") or "" for f in faces)
        if text.strip():
            lines += ["", f"## {t('Kartentext')}"] + [f"> {x}" if x else ">" for x in text.splitlines()]
        file = safe_name(name)
        fields = {"type": "card", "aliases": [name] if file != name else None, "set": code,
                  "print_set": printed,
                  "colors": colors.get(name) or None, "mana_cost": front.get("mana_cost"),
                  "rarity": sc.get("rarity"), "rating": ratings.get(name), "archetypes": pairs or None,
                  "tags": ["draftgott/card"] + ([f"set/{code}"] if code else [])}
        notes[f"Cards/{file}.md"] = _note(fields, "\n".join(lines))

    # Archetypen
    for code, found in arch_of_set.items():
        for pair, a in found.items():
            title = _arch_title(code, a)
            idx = [i for i, k in enumerate(rec_arch) if k == pair and (records[i].get("set") or "").upper() == code]
            ms = [m for i in idx for m in _results(records[i])]
            mw = sum(1 for m in ms if m["win"])
            gw, gl = _games(ms)
            lines = [f"# {title}", "", f"{t('Set')}: {link(code)} · {t('Farben')}: {pair}", ""]
            lines += [f"- {tip}" for tip in a.get("tips") or []]
            lines += ["", f"## {t('Ergebnisse')}", f"- {t('Drafts: {n}', n=len(idx))}",
                      f"- {t('Matches {a}-{b}', a=mw, b=len(ms) - mw)} · {t('Games {a}-{b}', a=gw, b=gl)}"
                      f"{_pct(gw, gw + gl)}"]
            mine = sorted((n for n, c in card_set.items() if c == code and pair in assign.get(n, [])),
                          key=lambda n: (-(stats.get(n) or {}).get("decks", 0), n))
            if mine:
                lines += ["", f"## {t('Karten')}"] + [f"- {link(n)}" + (f" · {ratings[n]}" if ratings.get(n) else "")
                                                     for n in mine]
            if idx:
                lines += ["", f"## {t('Drafts')}"] + [f"- {link(titles[i])}" for i in reversed(idx)]
            fields = {"type": "archetype", "set": code, "colors": pair, "drafts": len(idx),
                      "tags": ["draftgott/archetype", f"set/{code}"]}
            notes[f"Archetypes/{safe_name(title)}.md"] = _note(fields, "\n".join(lines))

    # Sets
    for code in ds.sets_in(data):
        s = ds.summary(data, code)
        lines = [f"# {code}", "", f"- {t('Drafts: {n}', n=s['drafts'])}",
                 f"- {t('Matches {a}-{b}', a=s['match_wins'], b=s['matches'] - s['match_wins'])} · "
                 f"{t('Games {a}-{b}', a=s['wins'], b=s['games'] - s['wins'])}{_pct(s['wins'], s['games'])}"]
        found = arch_of_set.get(code) or {}
        if found:
            lines += ["", f"## {t('Archetypen')}"] + [f"- {link(_arch_title(code, a))}" for a in found.values()]
        idx = [i for i, r in enumerate(records) if (r.get("set") or "").upper() == code]
        lines += ["", f"## {t('Drafts')}"]
        for i in sorted(idx, key=lambda i: (records[i].get("started") or "", i), reverse=True):
            st = ds.run_state(records[i])
            lines.append(f"- {link(titles[i])} · {st['wins']}-{st['losses']}" + (" 🏆" if st["trophy"] else ""))
        notes[f"Sets/{safe_name(code)}.md"] = _note({"type": "set", "set": code, "drafts": s["drafts"],
                                                     "tags": ["draftgott/set", f"set/{code}"]}, "\n".join(lines))
    return notes


def _split(text):
    """(Teil bis einschliesslich der Markierungszeile, Rest) oder (text, None) ohne Markierung."""
    pos = 0
    for line in text.splitlines(keepends=True):
        if line.startswith("%% draftgott"):
            return text[:pos + len(line)], text[pos + len(line):]
        pos += len(line)
    return text, None


def _generated(text):
    if not text.startswith("---"):
        return False
    end = text.find("\n---", 3)
    return GENERATED in (text[:end] if end > 0 else text)


def write_vault(vault, notes):
    """Schreibt die Notizen in den Vault; eigene Notizen unter MARKER bleiben, fremde Dateien bleiben unberuehrt.
    Gibt {"written", "skipped", "notes"} zurueck."""
    vault = pathlib.Path(vault)
    written = skipped = 0
    for rel, content in sorted(notes.items()):
        path = vault / rel
        old = None
        if path.exists():
            old = path.read_text(encoding="utf-8")
            if not _generated(old):
                skipped += 1
                continue
            head, _ = _split(content)
            _, tail = _split(old)
            if tail is not None:
                content = head + tail
        if content == old:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        written += 1
    return {"written": written, "skipped": skipped, "notes": len(notes)}


def export(data, vault, cards, assign, ratings):
    """Alle Notizen bauen und schreiben, dazu einmalig die Farben des Graphen."""
    vault = pathlib.Path(vault)
    res = write_vault(vault, build_notes(data, cards, assign, ratings))
    graph = vault / ".obsidian" / "graph.json"
    if not graph.exists():
        graph.parent.mkdir(parents=True, exist_ok=True)
        graph.write_text(json.dumps(GRAPH, indent=2), encoding="utf-8")
    return res


def card_names(data):
    names = set()
    for rec in data.get("drafts", []):
        deck = rec.get("deck") or {}
        names.update(n for n in list(rec.get("picks") or []) + list(deck.get("main") or {})
                     + list(deck.get("side") or {}) if _is_card(n))
    return sorted(names)


def cached_cards(names):
    """Scryfall-Daten aus dem Cache (ohne Netzwerk); fehlende Karten fehlen auch hier."""
    from components.scryfall import CACHE_FILE
    try:
        cache = json.loads(pathlib.Path(CACHE_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out = {}
    for n in names:
        sc = cache.get(n) or cache.get(n.split(" // ")[0])
        if sc:
            out[n] = sc
    return out


class AutoExport:
    """Export im Hintergrund fuer den Live-Draft: poke() nach jeder Aenderung der Statistik, nach DELAY Sekunden
    ohne weitere Aenderung wird exportiert. Fehler stoppen den Live-Draft nie."""

    def __init__(self, stats, ratings, archetypes, vault, cards=cached_cards, delay=DELAY):
        self.stats, self.ratings, self.archetypes = stats, ratings, archetypes
        self.vault, self.cards, self.delay = pathlib.Path(vault), cards, delay
        self._timer, self._lock = None, threading.Lock()

    def poke(self):
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self.delay, self.run_now)
            self._timer.daemon = True
            self._timer.start()

    def run_now(self):
        try:
            data = ds.load_stats(self.stats)
            return export(data, self.vault, self.cards(card_names(data)),
                          cardarchetypes.load_assign(self.archetypes), card_ratings.load_ratings(self.ratings))
        except (OSError, ValueError) as e:
            print(t("Obsidian-Export fehlgeschlagen: {err}", err=e), file=sys.stderr)
            return None


def run(args):
    """--obsidian [ORDNER]: einmal exportieren (fehlende Kartendaten von Scryfall nachladen, sonst aus dem Cache)."""
    stats = paths.data_file(args.statistik)
    data = ds.load_stats(stats)
    if not data.get("drafts"):
        sys.exit(t("Noch keine Drafts in {path}. Starte den Live-Draft im Launcher, dann werden "
                   "Drafts und Matches gesammelt.", path=stats))
    names = card_names(data)
    try:
        from components.scryfall import fetch_cards_cached
        fetch_cards_cached(names)
    except (urllib.error.URLError, OSError) as e:
        print(t("Scryfall nicht erreichbar, Export mit den Kartendaten aus dem Cache: {e}", e=e), file=sys.stderr)
    vault = vault_path(args.obsidian)
    res = export(data, vault, cached_cards(names), cardarchetypes.load_assign(paths.data_file(args.archetypen)),
                 card_ratings.load_ratings(paths.data_file(args.bewertung)))
    print(t("Obsidian-Vault: {path} ({n} Notizen, {w} geschrieben, {s} eigene Dateien nicht angefasst)",
            path=vault, n=res["notes"], w=res["written"], s=res["skipped"]), file=sys.stderr)
    print(t("In Obsidian: „Ordner als Vault öffnen“ und diesen Ordner wählen, dann Graph-Ansicht (Strg+G)."),
          file=sys.stderr)
    return res
