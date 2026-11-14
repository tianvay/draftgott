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
    # Formate (Pick Two, Pick One, ...)
    "{w} Siege / {l} Niederlagen": "{w} wins / {l} losses",
    "{n} Matches": "{n} matches",
    "1 Trophäe": "1 trophy",
    "{n} Trophäen": "{n} trophies",
    "{n} Runs, {d} abgeschlossen": "{n} runs, {d} finished",
    "1 Run, {d} abgeschlossen": "1 run, {d} finished",
    "Siege je abgeschlossenem Run": "wins per finished run",
    "Ansicht": "View",
    "Alle Formate": "All formats",
    "Formate": "Formats",
    "Formate im Vergleich": "Formats compared",
    "Je Format: wie viele Siege deine Runs am Ende hatten (Gold = Trophäe), wie oft du das 1., 2., 3. … Match gewinnst (später triffst du auf Gegner mit ähnlicher Bilanz; blass = weniger als 3 Matches) und wie lange gewonnene und verlorene Games dauern (Spielstatistik, Züge beider Spieler).":
        "Per format: how many wins your runs ended with (gold = trophy), how often you win the 1st, 2nd, 3rd … match (later you meet opponents with a similar record; faded = fewer than 3 matches) and how long won and lost games last (game statistics, turns of both players).",
    "{d} abgeschlossene Runs von {n}": "{d} finished runs of {n}",
    "Wie weit kommen deine Runs? (Siege am Ende)": "How far do your runs get? (wins at the end)",
    "{w} Siege: 1 Run": "{w} wins: 1 run",
    "{w} Siege: {n} Runs": "{w} wins: {n} runs",
    "Siegquote je Match-Nummer": "Win rate by match number",
    "Match {i}: {w} von {n} gewonnen": "Match {i}: {w} of {n} won",
    "Spieltempo (Ø je Game)": "Game pace (avg per game)",
    "Züge": "Turns",
    "Zauber": "Spells",
    "Besiegt": "Killed",
    "Schaden": "Damage",
    "Gewonnen": "Won",
    "Verloren": "Lost",
    "{n}× · Ø {w} Siege": "{n}× · avg {w} wins",
    # Formatvorteil
    "Formatvorteil": "Format edge",
    "Karten, die in einem Format deutlich besser abschneiden als im anderen (mindestens {n} Games in jedem). Bei Pick Two kommt der Synergie-Partner oft im selben Pick mit – solche Karten steigen hier nach oben.":
        "Cards that perform clearly better in one format than in the other (at least {n} games in each). In Pick Two the synergy partner often comes along in the same pick – such cards rise to the top here.",
    "Punkt = Siegquote der Games mit der Karte im Deck; Linie = Unterschied.":
        "Dot = game win rate with the card in the deck; line = difference.",
    "Noch keine Karte mit mindestens {n} Games in beiden Formaten und {d} Prozentpunkten Unterschied.":
        "No card with at least {n} games in both formats and a difference of {d} percentage points yet.",
    "{a}: {ra} in {ga} Games · {b}: {rb} in {gb} Games": "{a}: {ra} in {ga} games · {b}: {rb} in {gb} games",
    "Stärker in {f}": "Stronger in {f}",
    "Keine.": "None.",
    # Duos
    "Pick-Two-Duos": "Pick Two duos",
    "Duos": "Duos",
    "Paare, die du im selben Pick zusammen genommen hast und die beide im Hauptdeck gelandet sind, nach Games mit beiden im Deck. 🔗 = die Karten haben Synergie (Geber und Nehmer wie im Drafthelper).":
        "Pairs you took together in the same pick that both ended up in the main deck, by games with both in the deck. 🔗 = the cards have synergy (givers and takers as in the draft helper).",
    "Duos in {n} Pick-Two-Drafts": "duos in {n} Pick Two drafts",
    "beide im Hauptdeck": "both in the main deck",
    "Games gewonnen mit Synergie-Duo ({n} Games)": "games won with a synergy duo ({n} games)",
    "ohne Synergie ({n} Games)": "without synergy ({n} games)",
    "Noch kein Duo, bei dem beide Karten im Hauptdeck gelandet sind.": "No duo with both cards in the main deck yet.",
    "Duo": "Duo",
    "Zusammen gepickt": "Picked together",
    "Beide im Deck": "Both in deck",
    "Synergie": "Synergy",
    # Pick-Wert
    "Pick-Wert": "Pick value",
    "Wann du eine Karte genommen hast gegen wie gut sie lief (mindestens {n} Games). Rechts oben stehen späte Picks mit hoher Siegquote – die lohnt es sich früher zu nehmen; links unten frühe Picks, die enttäuscht haben.":
        "When you took a card versus how well it did (at least {n} games). Top right: late picks with a high win rate – worth taking earlier; bottom left: early picks that disappointed.",
    "Noch zu wenige Karten mit mindestens {n} Games und bekanntem Pick.":
        "Too few cards with at least {n} games and a known pick yet.",
    "Ø Pick (rechts = später genommen)": "Avg pick (right = taken later)",
    "Späte Perlen": "Late gems",
    "Früh und stark": "Early and strong",
    "Überschätzt?": "Overrated?",
    "Zu Recht spät": "Rightly late",
    "{name}: {p} in {g} Games, Ø Pick {pick}": "{name}: {p} in {g} games, avg pick {pick}",
    "Gestrichelt: Ø Siegquote dieser Karten ({p}). Kreisgröße = Games; mit der Maus auf einen Punkt zeigen für Name und Zahlen.":
        "Dashed: average win rate of these cards ({p}). Circle size = games; hover a dot for name and numbers.",
    # Runs
    "Neueste zuerst; S = Sieg, N = Niederlage, grau = läuft noch. Die Leiter zeigt die Siege bis zur Trophäe, die Herzen die Niederlagen, die das Format erlaubt.":
        "Newest first; W = win, L = loss, gray = still running. The ladder shows the wins up to the trophy, the hearts the losses the format allows.",
    "Trophäe": "Trophy",
    "ausgeschieden": "eliminated",
    "läuft": "running",
}
