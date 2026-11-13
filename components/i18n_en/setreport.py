"""Englische Texte der Setauswertung (components/setreport.py) und der Draft-Statistik (components/draftstats.py)."""

EN = {
    # Seitenkopf, Navigation
    "Setauswertung {code}": "Set report {code}",
    "aus der Draft-Statistik des Live-Drafts": "from the live draft statistics",
    "Abschnitte": "Sections",
    "Überblick": "Overview",
    "Archetypen": "Archetypes",
    "Beste und schwächste": "Best and weakest",
    "Beste und schwächste Karten": "Best and weakest cards",
    "Karten": "Cards",
    "Bewertung": "Rating",
    "Bewertung gegen Ergebnis": "Rating vs. result",
    "Drafts": "Drafts",
    "Erzeugt mit mtg_sim.py · Kartendaten und Bilder von Scryfall": "Generated with mtg_sim.py · card data and images from Scryfall",
    # Überblick
    "{a} bis {b}": "{a} to {b}",
    "mitgelesen": "tracked",
    "Games, {p} gewonnen": "games, {p} won",
    "Siege je Draft": "wins per draft",
    "alle mitgelesenen Drafts des Sets": "all tracked drafts of the set",
    "Match-Verlauf (älteste zuerst): {timeline}": "Match history (oldest first): {timeline}",
    "läuft noch": "still running",
    "Noch keine Drafts für dieses Set in der Statistik. Starte den Live-Draft (Menüpunkt 3), dann werden Drafts und Matches gesammelt.":
        "No drafts for this set in the statistics yet. Start the live draft (menu item 3) and drafts and matches will be collected.",
    # Archetypen
    "Je Draft erkannt wie im Live-Draft: aus dem Hauptdeck (sonst den Picks), mit deiner Archetyp-Zuordnung und Kategorie.":
        "Detected per draft as in the live draft: from the main deck (otherwise the picks), using your archetype assignment and category.",
    "Keine Drafts.": "No drafts.",
    "noch offen": "undecided",
    "Archetyp offen": "Archetype undecided",
    "Matches gewonnen": "Matches won",
    "Games gewonnen": "Games won",
    # Beste und schwächste
    "Karten mit mindestens {n} Games im Hauptdeck, nach Siegquote der Games.":
        "Cards with at least {n} games in the main deck, by game win rate.",
    "Noch keine Karte mit mindestens {n} Games im Hauptdeck – je mehr Drafts mitgelesen werden, desto aussagekräftiger wird diese Liste.":
        "No card with at least {n} games in the main deck yet – the more drafts are tracked, the more meaningful this list becomes.",
    "Am stärksten": "Strongest",
    "Am schwächsten": "Weakest",
    "{n}× gedraftet": "drafted {n}×",
    # Kartentabelle
    "Gedraftet: Kopien. Ø Pick: Pick-Nummer im Pack (1 = erster Pick aus einem vollen Pack; bei Pick Two zählen Picks, nicht Karten). Im Deck: Drafts, in deren Hauptdeck die Karte war. Games und Matches: mit der Karte im Hauptdeck; grün ab {good} %, rot unter {bad} %, grau unter {min} Games (nur ein Hinweis). Klick auf eine Spalte sortiert.":
        "Drafted: copies. Avg pick: pick number in the pack (1 = first pick from a full pack; in Pick Two, picks count, not cards). In deck: drafts whose main deck contained the card. Games and matches: with the card in the main deck; green from {good}%, red below {bad}%, gray below {min} games (just a hint). Click a column to sort.",
    "Karte": "Card",
    "Kosten": "Cost",
    "Selt.": "Rar.",
    "Kategorie": "Category",
    "Gedraftet": "Drafted",
    "Ø Pick": "Avg pick",
    "Im Deck": "In deck",
    "Games": "Games",
    "Matches": "Matches",
    "Karte suchen": "Search card",
    "nur gespielte Karten": "played cards only",
    "Weiß": "White",
    "Blau": "Blue",
    "Schwarz": "Black",
    "Rot": "Red",
    "Grün": "Green",
    "Mehrfarbig": "Multicolor",
    "Farblos": "Colorless",
    "Weniger als {n} Games: nur ein Hinweis": "Fewer than {n} games: just a hint",
    "ohne Kategorie": "no category",
    # Bewertung gegen Ergebnis
    "Deine Kategorien (kartenbewertung.json) und wie Karten jeder Kategorie im Deck abgeschnitten haben (Games je Karte gezählt). Liegt Filler über MustPlay, lohnt ein zweiter Blick auf die Bewertung.":
        "Your categories (kartenbewertung.json) and how cards of each category performed in the deck (games counted per card). If Filler is above MustPlay, the ratings deserve a second look.",
    "in {games} Games · {played} von {total} Karten gespielt": "in {games} games · {played} of {total} cards played",
    # Drafts
    "Neueste zuerst; S = Sieg, N = Niederlage, grau = läuft noch.": "Newest first; W = win, L = loss, gray = still running.",
    "Draft nicht mitgelesen": "Draft not tracked",
    " · Deck {n} Karten": " · deck {n} cards",
    "Games {a}-{b}": "Games {a}-{b}",
    # Konsole
    "Noch keine Drafts in {path}. Starte den Live-Draft (Menüpunkt 3), dann werden Drafts und Matches gesammelt.":
        "No drafts in {path} yet. Start the live draft (menu item 3) and drafts and matches will be collected.",
    "Scryfall nicht erreichbar, Auswertung ohne Kartendaten: {e}": "Scryfall unreachable, report without card data: {e}",
    "Setauswertung gespeichert: {path}": "Set report saved: {path}",
    "Gegnerdeck nicht gespeichert: {e}": "Opponent deck not saved: {e}",
    "Gegnerdeck gespeichert: {path}": "Opponent deck saved: {path}",
}
