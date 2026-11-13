"""Englische Texte fuer components/report.py (Bericht: Ueberschriften, Kennzahlen, Hinweise, Navigation, Schaltflaechen)."""

EN = {
    # Seitenleiste, Kopf, Fuss
    "Zauber R{n}": "Spells T{n}",
    "R{n}": "T{n}",
    "Lethal ab": "Lethal from",
    "Ø {n} Schaden": "Avg. {n} damage",
    "Kernzahlen": "Key figures",
    "Abschnitte": "Sections",
    "Einstellungen": "Settings",
    "MTG Simulation": "MTG simulation",
    "Starthand-Simulation · erstellt am {stamp}": "Opening hand simulation · created on {stamp}",
    "Bericht": "Report",
    "So funktioniert es": "How it works",
    "Erzeugt mit mtg_sim.py · Kartendaten von Scryfall": "Generated with mtg_sim.py · card data from Scryfall",
    "Vergleich mit {n} Alternative(n)": "Comparison with {n} alternative(s)",
    "{n} gespielte Spiele pro Modus": "{n} games played per mode",
    "Mulligan an": "Mulligan on",
    "ohne Mulligan": "no mulligan",
    "Auswertung Runde {n}": "Evaluation at turn {n}",
    "Beobachtung bis Runde {n}": "Observation up to turn {n}",
    "{n} Schaden": "{n} damage",
    "Flood ab {n} Ländern": "Flood from {n} lands",
    "Nicht bei Scryfall gefunden (nicht simuliert):": "Not found on Scryfall (not simulated):",
    "Details für:": "Details for:",
    "Details: {name}": "Details: {name}",
    "Deck-Vergleich": "Deck comparison",
    "Hauptdeck gegen {n} Alternative(n), mit statistischer Einordnung der Unterschiede.":
        "Main deck against {n} alternative(s), with a statistical assessment of the differences.",

    # Tabellenkoepfe, die mehrfach vorkommen
    "Karte": "Card",
    "Karten": "Cards",
    "Anz.": "Qty",
    "Kategorie": "Category",
    "Bereich": "Section",
    "Kosten": "Cost",
    "Eigenschaften": "Properties",
    "Status": "Status",
    "Betroffene Kennzahl": "Affected metric",
    "Kennzahl": "Metric",
    "Gesamt": "Total",
    "Runde": "Turn",
    "Runde {n}": "Turn {n}",
    "Median": "Median",
    "Eintritt": "Occurrence",
    "Ø Runde": "Avg. turn",

    # Great in this deck / Abdeckung
    "Great in this deck!": "Great in this deck!",
    "Als Matchwinner, Splashworthy oder MustPlay gekennzeichnete Karten dieses Decks (Draft-Helper).":
        "Cards of this deck marked as Matchwinner, Splashworthy or MustPlay (Draft Helper).",
    "Keine Matchwinner-, Splashworthy- oder MustPlay-Karten in diesem Deck.":
        "No Matchwinner, Splashworthy or MustPlay cards in this deck.",
    "Fehlt in diesem Deck:": "Missing from this deck:",
    "NeverPlay-Karten im Deck:": "NeverPlay cards in the deck:",
    "Modell-Abdeckung": "Model coverage",
    "Welche Karten dieses Decks Effekte haben, die die Simulation noch nicht abbildet.":
        "Which cards in this deck have effects that the simulation does not model yet.",
    "Keine Karte mit nicht implementierten Effekten gefunden.": "No cards with unimplemented effects found.",
    "<b>{n} Karten</b> ({k} Kopien) haben Effekte, die die Simulation noch nicht abbildet. Die Zahlen in diesem Bericht berücksichtigen sie nicht.":
        "<b>{n} cards</b> ({k} copies) have effects that the simulation does not model yet. The numbers in this report do not take them into account.",
    "To Do: Noch nicht implementiert": "To do: not implemented yet",
    "Lethal / Schaden": "Lethal / damage",
    "Mana und Zauber pro Runde": "Mana and spells per turn",
    "Kartenfluss (Länder, Screw/Flood)": "Card flow (lands, screw/flood)",
    "keine (Gegner ist nicht Teil des Modells)": "none (the opponent is not part of the model)",
    "unklar": "unclear",
    "Defender-Ausnahme": "Defender exception",
    "Direkter Schaden": "Direct damage",
    "Empower Jace (Wert nicht modelliert)": "Empower Jace (value not modeled)",
    "Haste verleihen": "Grant haste",
    "Interaktion mit dem Gegner": "Interaction with the opponent",
    "Kartenfluss": "Card flow",
    "Kostensenkung / Convoke": "Cost reduction / Convoke",
    "Land: Bedingung nicht modelliert": "Land: condition not modeled",
    "Lebensgewinn": "Life gain",
    "Mana außer Ländern": "Mana other than lands",
    "Planeswalker-Fähigkeit": "Planeswalker ability",
    "Prepared-Zauberhälfte": "Prepared spell half",
    "Schlüsselwort verleihen": "Grant keyword",
    "Timing (Flash)": "Timing (flash)",
    "Tokens erzeugen": "Create tokens",
    "Unbekannter Effekt": "Unknown effect",
    "Zusatzkosten": "Additional costs",
    "Zweitverwertung (Friedhof)": "Second use (graveyard)",
    "Zählmarken / Stärkebonus": "Counters / power bonus",

    # Auf einen Blick
    "Auf einen Blick": "At a glance",
    "Die wichtigsten Kennzahlen im Vergleich Play gegen Draw.": "The key figures, Play versus Draw.",
    "Zauber gespielt in Runde {n}": "Spell cast by turn {n}",
    "Mana Screw nach Runde {n}": "Mana screw after turn {n}",
    "Flood ({f}+ Länder bis Runde {h})": "Flood ({f}+ lands by turn {h})",
    "Schnellster Lethal ({n} Schaden)": "Fastest lethal ({n} damage)",
    "kein Lethal": "no lethal",
    "Ø Runde für {n} Schaden": "Avg. turn for {n} damage",
    "{p} der Spiele": "{p} of games",
    "Mulligan auf der ersten Hand": "Mulligan on the first hand",
    "Spiel verloren (Hand unter {n} Karten)": "Game lost (hand below {n} cards)",
    "Jace-Aktivierungen bis die Hand leer ist (Ø)": "Jace activations until the hand is empty (avg.)",

    # Deck
    "Deck": "Deck",
    "Kartendaten von Scryfall.": "Card data from Scryfall.",
    "{n} verschiedene": "{n} different",
    "Länder": "Lands",
    "{p} des Decks": "{p} of the deck",
    "Ø Manakosten": "Avg. mana cost",
    "ohne Länder": "excluding lands",
    "Farben": "Colors",
    "mehrfarbig": "multicolor",
    "einfarbig": "single color",
    "{n} Mana": "{n} mana",
    "Farbe": "Color",
    "Symbole": "Symbols",
    "Quellen": "Sources",
    "Anteil der Länder": "Share of lands",
    "Ø pünktlich": "Avg. on time",
    "Am knappsten": "Tightest",
    "Alle Dateien:": "All files:",
    "{n} Karten": "{n} cards",
    "Dieses Deck besteht aus {parts}; blass dargestellte Bereiche gehören nur zu einer anderen Variante. Eine Karte steht mit der Menge je Bereich, ihre Gesamtmenge im Deck ist die Summe der Bereiche des Decks.":
        "This deck consists of {parts}; faded sections only belong to another variant. A card is listed with the quantity per section; its total quantity in the deck is the sum of the deck's sections.",
    "Getappt-Bedingung nicht modelliert (als immer getappt gezählt):": "Tapped condition not modeled (counted as always tapped):",
    "Farbverteilung": "Color distribution",

    # Removal, Synergie
    "Removal": "Removal",
    "Wie viel Removal hat das Deck? Bewertung je Karte aus dem Kartentext.":
        "How much removal does the deck have? Rating per card from the card text.",
    "Synergie": "Synergy",
    "Welche Karten profitieren von anderen Karten im Deck, und wie gut ist das erfüllt?":
        "Which cards benefit from other cards in the deck, and how well is that met?",

    # Friedhof
    "Friedhof": "Graveyard",
    "Wie stark nutzt das Deck den Friedhof, und was liegt in der Simulation darin?":
        "How much does the deck use the graveyard, and what ends up in it in the simulation?",
    "Simulation": "Simulation",
    "nach Runde {n}": "after turn {n}",
    "Ø Karten im Friedhof": "Avg. cards in graveyard",
    "Ø höchster Manawert im Friedhof": "Avg. highest mana value in graveyard",
    "{names}: X = höchster Manawert im Friedhof beim Betreten":
        "{names}: X = highest mana value in the graveyard on entering",
    "gewirkt (Anzahl)": "cast (count)",

    # Mulligan
    "Mulligan": "Mulligan",
    "Wie oft die Starthand getauscht werden muss und wie oft das Spiel dadurch verloren geht.":
        "How often the opening hand has to be mulliganed and how often that loses the game.",
    "Verloren (< {n})": "Lost (< {n})",
    "Gespielt / verloren": "Played / lost",
    "Farben passen nicht": "Colors don't fit",
    "6+ Länder": "6+ lands",
    "≤ 2 Länder, < 3 spielbar": "≤ 2 lands, < 3 castable",
    "Erste 7-Karten-Hand: Gründe für einen Mulligan": "First 7-card hand: reasons for a mulligan",
    "Mulligan gesamt": "Mulligan total",
    "Mit wie vielen Karten startet das Spiel?": "How many cards does the game start with?",
    "(Behalten mit … Karten)": "(Keep with … cards)",

    # Jace
    "Jace & Planeswalker": "Jace & planeswalkers",
    "Karten mit Empower Jace oder anderen Planeswalker-Bezügen und deren Wirkung in der Simulation.":
        "Cards with Empower Jace or other planeswalker references and their effect in the simulation.",

    # Zauber pro Runde, Kreaturen, Screw & Flood
    "Zauber pro Runde": "Spells per turn",
    "{n} Simulationen pro Modus.": "{n} simulations per mode.",
    "Ø Länder in Starthand (nach Mulligan)": "Avg. lands in opening hand (after mulligan)",
    "Kreaturen": "Creatures",
    "Kreaturen nach Runde {n}": "Creatures after turn {n}",
    "Gesamt-Power": "Total power",
    "Gesamt-Toughness": "Total toughness",
    "Mana Screw & Flood": "Mana screw & flood",
    "Zu wenig Länder": "Too few lands",
    "Farben fehlen": "Colors missing",
    "Flooded": "Flooded",
    "Ø Länder gezogen": "Avg. lands drawn",

    # Farbverfuegbarkeit
    "Farbverfügbarkeit": "Color availability",
    "Wie oft liegen bis Runde 3 alle Farben, und wie oft genug Quellen für Mehrfach-Symbole (z. B. WW, GGGG) bis zur Runde, in der die günstigste solche Karte spielbar wäre?":
        "How often are all colors available by turn 3, and how often are there enough sources for multiple symbols (e.g. WW, GGGG) by the turn the cheapest such card would be castable?",

    # Splash-Karten
    "Splash-Karten": "Splash cards",
    "Wie oft werden die Karten der Splash-Gruppe spielbar, wenn man sie zieht?":
        "How often do the cards of the splash group become castable when you draw them?",
    "Gezogen": "Drawn",
    "Spielbar": "Castable",
    "Pünktlich": "On time",
    "Ø Wartezeit": "Avg. wait",
    "Gewirkt": "Cast",
    "Gezogen: Anteil aller Spiele. Die übrigen Spalten beziehen sich auf die Spiele, in denen die Karte auf die Hand kam: Spielbar, wenn gezogen · Pünktlich (bis Runde = Manawert) · Ø Wartezeit in Runden bis erstmals bezahlbar · Gewirkt, wenn gezogen.":
        "Drawn: share of all games. The other columns refer to the games in which the card reached the hand: Castable, if drawn · On time (by turn = mana value) · Avg. wait in turns until first affordable · Cast, if drawn.",

    # Curve-Auslastung
    "Curve-Auslastung": "Curve utilization",
    "Runde 1–{n}: wie gut wird das Mana genutzt?": "Turns 1–{n}: how well is the mana used?",
    "Ø Mana verfügbar": "Avg. mana available",
    "Ø Mana ausgegeben": "Avg. mana spent",
    "Auslastung": "Utilization",
    "Alles Mana genutzt": "All mana used",
    "Auslastung je Runde": "Utilization per turn",

    # Schaden
    "Schaden durch Kreaturen": "Damage from creatures",
    "Wahrscheinlichkeit, bis Runde X mindestens {n} Schaden verursacht zu haben":
        "Chance of having dealt at least {n} damage by turn X",
    "Pro Spiel aus Karten:": "Per game from cards:",
    "Ø {a} Schaden an den Gegner, Ø {b} +1/+1-Marken": "avg. {a} damage to the opponent, avg. {b} +1/+1 counters",
    "Erste Runde mit {n} Schaden": "First turn with {n} damage",

    # Lethal
    "Schnellster Lethal": "Fastest lethal",
    "Das schnellste von {n} simulierten Spielen (bei gleicher Runde das mit mehr Schaden) – ein Glücksfall, kein Erwartungswert.":
        "The fastest of {n} simulated games (with the same turn, the one with more damage) – a lucky outlier, not an expected value.",
    "getappt": "tapped",
    "Landcycling: {name}": "Landcycling: {name}",
    "Jace +{a} → {b} Loyalty": "Jace +{a} → {b} loyalty",
    "Jace aktiviert (+1 Karte)": "Jace activated (+1 card)",
    "Draw-Zauber: +{n} Karte": "Draw spell: +{n} card",
    "Draw-Zauber: +{n} Karten": "Draw spell: +{n} cards",
    "Mulligan: Starthand mit {n} Karten": "Mulligan: opening hand with {n} cards",
    "Starthand": "Opening hand",
    "Zieht": "Draws",
    "Land": "Land",
    "Zauber": "Spell",
    "Schaden": "Damage",

    # Landcycling
    "Landcycling": "Landcycling",
    "Karten im Deck:": "Cards in the deck:",
    "in {n} Simulationen nie nötig oder möglich": "never needed or possible in {n} simulations",
    "Spiele mit Cycling": "Games with cycling",
    "Ø pro Spiel": "Avg. per game",
    "Erstmals Ø in": "First avg. in",
    "Nicht-Land-Chance": "Non-land chance",
    "PP": "pp",
    "relativ": "relative",
    "Grund": "Reason",
    "Meistgenutzte Karte": "Most used card",

    # Draw-Zauber, Surveil, Prepared
    "Draw-Zauber": "Draw spells",
    "Spiele mit Draw-Zauber": "Games with draw spell",
    "Ø zusätzlich gezogen": "Avg. extra cards drawn",
    "Karten pro Spiel bis Runde {n}": "cards per game up to turn {n}",
    "Ø gleich genutzt": "Avg. used right away",
    "Länder und Zauber im selben Zug": "Lands and spells in the same turn",
    "Surveil durch Karten": "Surveil from cards",
    "Spiele mit Surveil": "Games with surveil",
    "Ø Surveils": "Avg. surveils",
    "pro Spiel bis Runde {n}": "per game up to turn {n}",
    "Ø Länder in den Friedhof": "Avg. lands into the graveyard",
    "pro Spiel": "per game",
    "Prepared": "Prepared",
    "Spiele mit Kopie": "Games with copy",
    "Ø Kopien": "Avg. copies",
    "Ø Mana für Kopien": "Avg. mana for copies",

    # Ramp
    "Ramp": "Ramp",
    "Mana außer Ländern – Karten im Deck:": "Mana other than lands – cards in the deck:",
    "Spiele mit Ramp": "Games with ramp",
    "mehr Mana als Länder": "more mana than lands",
    "Ø Angriffe ausgelassen": "Avg. attacks skipped",
    "Kreatur für Mana getappt": "creature tapped for mana",
    "Treasure Ø": "Treasure avg.",
    "genutzt / erzeugt pro Spiel": "used / created per game",
    "Ø zusätzliches Mana": "Avg. extra mana",

    # Tempo
    "Tempo": "Tempo",
    "Ereignis": "Event",
    "Hand komplett leer": "Hand completely empty",
    "Keine Zauber mehr auf der Hand": "No spells left in hand",
    "Top Card spielbar": "Top card castable",
    "Top Card: {names} (Manawert {n}).": "Top card: {names} (mana value {n}).",
}

# Feste Vorlagen: woertliche Ersetzungen (siehe i18n.tr_block)
FIGHT_JS_EN = {
    "'Kein Gegnerdeck gefunden (Dateien *.txt im Ordner enemydecks).'":
        "'No opponent deck found (*.txt files in the enemydecks folder).'",
    "'Kampf startet ...'": "'Battle starting ...'",
    "'Fehler'": "'Error'",
    "draftgott wurde beendet. Dieses Fenster kann geschlossen werden.":
        "draftgott has been closed. You can close this window.",
}

FIGHT_BAR_EN = {
    "Kampf gegen ein Gegnerdeck ist nur möglich, solange draftgott läuft (Analyse oder Drafthelper).":
        "A battle against an opponent deck is only possible while draftgott is running (analysis or Draft Helper).",
    ">Kampf: nur solange draftgott läuft<": ">Battle: only while draftgott is running<",
    ">Kampf gegen <select": ">Battle against <select",
    "Gegnerdecks im Ordner enemydecks": "Opponent decks in the enemydecks folder",
    "Kämpfe je Deck und Modus (On the Play und On the Draw); mehr Kämpfe sind genauer, dauern aber länger":
        "Battles per deck and mode (On the Play and On the Draw); more battles are more accurate but take longer",
    " Kämpfe</option>": " battles</option>",
    ">Kampf simulieren</button>": ">Simulate battle</button>",
    ">Beenden</button>": ">Quit</button>",
}

SWITCH_JS_EN = {}
