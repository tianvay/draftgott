"""Obsidian-Export (components/obsidian.py): Deutsch -> Englisch."""
EN = {
    "Obsidian-Vault: {path} ({n} Notizen, {w} geschrieben, {s} eigene Dateien nicht angefasst)":
        "Obsidian vault: {path} ({n} notes, {w} written, {s} own files left untouched)",
    "In Obsidian: „Ordner als Vault öffnen“ und diesen Ordner wählen, dann Graph-Ansicht (Strg+G).":
        "In Obsidian: choose “Open folder as vault” and pick this folder, then open the graph view (Ctrl+G).",
    "## Eigene Notizen": "## My notes",
    "Scryfall nicht erreichbar, Export mit den Kartendaten aus dem Cache: {e}":
        "Scryfall not reachable, exporting with the card data from the cache: {e}",
    "Obsidian-Export fehlgeschlagen: {err}": "Obsidian export failed: {err}",
    "Zahlen": "Numbers",
    "Gedraftet: {n} (in {d} Drafts)": "Drafted: {n} (in {d} drafts)",
    "Im Deck: {n}": "In deck: {n}",
    "Ø Pick: {x}": "Avg pick: {x}",
    "Drafts: {n}": "Drafts: {n}",
    "Matches {a}-{b}": "Matches {a}-{b}",
    "Archetyp": "Archetype",
    "Bilanz": "Record",
    "Event": "Event",
    "Gegnerdeck": "Opponent deck",
    "Picks": "Picks",
    "Ergebnisse": "Results",
    "Sideboard": "Sideboard",
    "Pack {n}": "Pack {n}",
    "Kartentext": "Card text",
    "Druck": "Printing",
    "Sieg {a}-{b}": "Win {a}-{b}",
    "Niederlage {a}-{b}": "Loss {a}-{b}",
    # Erklaerseite (components/howitworks.py)
    "Obsidian-Export": "Obsidian export",
    "Der Live-Draft schreibt die Draft-Statistik zusätzlich als verlinkte Markdown-Notizen nach "
    "<code>daten/obsidian</code> (nicht im Git): je Draft, je gedraftete Karte, je Set und je Archetyp. In "
    "Obsidian „Ordner als Vault öffnen“ wählen; die Graph-Ansicht zeigt dann, welche Karten, Archetypen und "
    "Drafts zusammenhängen. Von Hand: <code>python mtg_sim.py --obsidian [ORDNER]</code>.":
        "The live draft also writes the draft statistics as linked Markdown notes to <code>daten/obsidian</code> "
        "(not in Git): one per draft, per drafted card, per set and per archetype. In Obsidian choose “Open folder as "
        "vault”; the graph view then shows how cards, archetypes and drafts connect. By hand: "
        "<code>python mtg_sim.py --obsidian [FOLDER]</code>.",
    "Eigene Gedanken gehören unter die Zeile <code>%% draftgott … %%</code> am Ende einer Notiz: Sie bleiben "
    "bei jedem Export erhalten. Eigene Dateien ohne die Kennung <code>draftgott: generated</code> werden nie "
    "angefasst.":
        "Your own thoughts go below the line <code>%% draftgott … %%</code> at the end of a note: they survive every "
        "export. Your own files without the mark <code>draftgott: generated</code> are never touched.",
}
