"""Englische Texte fuer den Python-Teil von components/drafthelper.py (Konsole, Fehlermeldungen der Seite)."""
EN = {
    "Kartenpool-Datei nicht gefunden: {path}\n"
    "Der Drafthelper braucht deinen gedrafteten Kartenpool als Textdatei im Projektordner "
    "({dir}).\n"
    "Lege die Datei {name} an, z. B. mit dem Deck-Export aus MTG Arena: "
    "ein Abschnitt 'Deck' und ein Abschnitt 'Sideboard', darunter Zeilen wie\n"
    "  1 Curse-Marred Demon (FRA) 79\n"
    "Die Datei liegt nicht im Git, jeder hat seine eigene.":
        "Card pool file not found: {path}\n"
        "The Draft Helper needs your drafted card pool as a text file in the project folder "
        "({dir}).\n"
        "Create the file {name}, e.g. with the deck export from MTG Arena: "
        "a 'Deck' section and a 'Sideboard' section, followed by lines like\n"
        "  1 Curse-Marred Demon (FRA) 79\n"
        "The file is not in Git; everyone has their own.",
    "Keine Karten in {p} gefunden (erwartet: Abschnitte 'Deck' und 'Sideboard').":
        "No cards found in {p} (expected: 'Deck' and 'Sideboard' sections).",
    "Kartenpool: {n} Karten aus {p}": "Card pool: {n} cards from {p}",
    "Lade Kartendaten und Bilder von Scryfall ...": "Loading card data and images from Scryfall ...",
    "Scryfall nicht erreichbar: {e}": "Scryfall not reachable: {e}",
    "Markierungen passen nicht zum Kartenpool": "Marks do not match the card pool",
    "Anzahl {name}: erlaubt sind 0 bis {max} je Gruppe": "Count {name}: 0 to {max} allowed per group",
    "Angaben zum Deckvorschlag fehlen": "Deck proposal details are missing",
    "Unbekannte Farbe (erlaubt: W, U, B, R, G)": "Unknown color (allowed: W, U, B, R, G)",
    "Die Zielgröße muss zwischen 10 und 200 Karten liegen": "The target size must be between 10 and 200 cards",
    "Unbekannte Sortierung": "Unknown sort order",
    "Der Deckvorschlag ist zu klein zum Simulieren (weniger als "
    "{n} Karten): Bitte Farben und Kategorien prüfen.":
        "The deck proposal is too small to simulate (fewer than {n} cards): please check colors and categories.",
    "Starte ...": "Starting ...",
    "Fertig": "Done",
    "Abgebrochen": "Aborted",
    "Unerwarteter Fehler: {e}": "Unexpected error: {e}",
    "<p>Noch kein Bericht vorhanden.</p>": "<p>No report yet.</p>",
    "<p>Noch kein Kampfbericht vorhanden.</p>": "<p>No battle report yet.</p>",
    "Nicht gefunden": "Not found",
    "Kein Live-Draft": "No live draft",
    "Anzahl der Spiele muss zwischen 100 und 100000 liegen": "Number of games must be between 100 and 100000",
    "Es laeuft bereits eine Simulation": "A simulation is already running",
    "Keine Bewertungsdatei": "No ratings file",
    "Unbekannte Karte": "Unknown card",
    "Kein Live-Draft (Drafthelper mit --live starten).": "No live draft (start the Draft Helper with --live).",
    "Unbekannter Archetyp": "Unknown archetype",
    "Keine Datei für die Archetyp-Zuordnung": "No file for the archetype assignment",
    "Unbekanntes Set": "Unknown set",
    "Seitenfenster konnte nicht gestartet werden: {e}": "Overlay could not be started: {e}",
    "Live-Draft: lese {log}, Draft-Statistik in {stats}": "Live draft: reading {log}, draft statistics in {stats}",
    "Draft-Helper laeuft: {url}": "Draft Helper running: {url}",
    "Zum Beenden: Button 'Beenden' auf der Seite oder Strg+C hier im Fenster.":
        "To quit: 'Quit' button on the page or Ctrl+C in this window.",
    "Draft-Helper beendet.": "Draft Helper stopped.",
    "Kämpfe": "battles",
    "Vorschlag": "Proposal",
}
