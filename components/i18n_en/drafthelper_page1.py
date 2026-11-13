"""Drafthelper-Seite (PAGE in components/drafthelper.py), Teil 1: woertliche Ersetzungen Deutsch -> Englisch.
Jeder Schluessel muss genau so in PAGE vorkommen (siehe tests/test_i18n_drafthelper_page1.py)."""

PAGE = {
    '<html lang="de">': '<html lang="en">',
    "<title>Draft-Helper</title>": "<title>Draft Helper</title>",
    "<h1>Draft-Helper</h1>": "<h1>Draft Helper</h1>",
    # Kopfleiste
    "Karten zeigen": "Show cards",
    'title="Blendet Karten anderer Kategorien aus"': 'title="Hides cards of other categories"',
    "Spiele pro Modus": "Games per mode",
    'title="Alle Karten eines Sets: Kategorie und Archetypen vorab festlegen"':
        'title="All cards of a set: assign category and archetypes in advance"',
    ">Set-Karten bewerten<": ">Rate set cards<",
    'title="Deckliste der Varianten zum Kopieren oder Speichern"': 'title="Deck list of the variants to copy or save"',
    ">Deckliste exportieren<": ">Export deck list<",
    ">Simulieren<": ">Simulate<",
    'title="Kampf der Varianten gegen ein Gegnerdeck, ohne vorher den Goldfish zu simulieren"':
        'title="Battle of the variants against an opponent deck, without simulating the Goldfish first"',
    'title="Gegnerdecks im Ordner enemydecks"': 'title="Opponent decks in the enemydecks folder"',
    'title="Kämpfe je Deck und Modus (On the Play und On the Draw)"':
        'title="Battles per deck and mode (On the Play and On the Draw)"',
    ">Kampf ohne Goldfish<": ">Battle without Goldfish<",
    'title="Draft-Helper beenden"': 'title="Quit Draft Helper"',
    ">Beenden<": ">Quit<",
    # Hilfetext
    "<b>So geht's:</b> Ordne unter jeder Karte zu (": "<b>How to use it:</b> Assign each card below (",
    "</b> oder\n    <b>Aus</b>), wähle bei Bedarf eine <b>Kategorie</b> und stelle oben die Standardländer ein. Danach auf\n"
    "    <b>Simulieren</b> klicken. Alle Regeln (Zuordnung, Kategorien, Deckvorschlag, Übersichten):\n    ":
        "</b> or\n    <b>Off</b>), choose a <b>category</b> if needed and set the basic lands at the top. Then click\n"
        "    <b>Simulate</b>. All rules (assignment, categories, deck proposal, overviews):\n    ",
    ">So funktioniert es<": ">How it works<",
    # Live-Draft
    'id="lhead">Live-Draft<': 'id="lhead">Live draft<',
    '<label class="filter">Archetyp <select id="lmanual" title="Automatisch erkennen oder selbst festlegen">':
        '<label class="filter">Archetype <select id="lmanual" title="Detect automatically or set manually">',
    'title="Schreibt das in Arena abgegebene Deck (Deck und Sideboard) in die Kartenpool-Datei"':
        'title="Writes the deck submitted in Arena (deck and sideboard) to the card pool file"',
    ">Deck + Sideboard übernehmen<": ">Use deck + sideboard<",
    'title="Karten ab Must Play, deren bester Archetyp (lila Knopf unter der Karte) dein Archetyp ist oder nahe dran '
    '(höchstens 3 Punkte hinter dem besten)"':
        'title="Cards rated Must Play or higher whose best archetype (purple button under the card) is your archetype '
        'or close to it (at most 3 points behind the best)"',
    'title="Offene Farben: starke Karten (Must Play oder höher), die zurückkommen oder spät im Pack liegen; umkämpft: '
    'starke Karten, die andere genommen haben"':
        'title="Open colors: strong cards (Must Play or higher) that wheel or are still in the pack late; contested: '
        'strong cards that others have taken"',
    "Reihenfolge: Kategorie (★ 4, MP 3, ohne 1,5, Fi 1, NP immer 0) + 3, wenn die Karte dem\n"
    "      Archetyp zugeordnet ist (grün), + 4, wenn er ihr bester ist (lila), sonst + 1, wenn ihre Farben passen "
    "(hellgrün), + Synergie mit deinen Picks (bis 2). Archetyp: aus deinen Picks\n"
    "      (Farben, Zuordnung, Kategorien), siehe ":
        "Order: category (★ 4, MP 3, none 1.5, Fi 1, NP always 0) + 3 if the card is assigned to the\n"
        "      archetype (green), + 4 if it is its best (purple), otherwise + 1 if its colors fit (light green), "
        "+ synergy with your picks (up to 2). Archetype: from your picks\n"
        "      (colors, assignment, categories), see ",
    "Die Picks landen in der Kartenpool-Datei, die Karten unten zeigen den Pool.":
        "The picks end up in the card pool file, the cards below show the pool.",
    ">Archetypen</summary>": ">Archetypes</summary>",
    "Hervorgehoben: der Archetyp deiner Core-Farben (die zwei Farben mit den meisten Core-Karten,\n"
    "      ohne Länder; mehrfarbige zählen für jede ihrer Farben).":
        "Highlighted: the archetype of your Core colors (the two colors with the most Core cards,\n"
        "      without lands; multicolor cards count for each of their colors).",
    # Seitenleiste
    "<h3>Übersicht nach Farbe</h3>": "<h3>Overview by color</h3>",
    ">Mana-Kurve</h3>": ">Mana curve</h3>",
    ">Mana-Kurve nach Farben</h3>": ">Mana curve by color</h3>",
    "<label>Variante <select": "<label>Variant <select",
    "<label>Ansicht <select": "<label>View <select",
    ">Mehrfarbige gesondert<": ">Multicolor separate<",
    ">Je Farbe (Mehrfarbige in jeder Farbe)<": ">Per color (multicolor in every color)<",
    ">Farben und Quellen</h3>": ">Colors and sources</h3>",
    ">Kartentypen je Variante</h3>": ">Card types per variant</h3>",
    # Werkzeugleiste
    'placeholder="Karte suchen (Name oder englischer Typ, z. B. Creature, Instant, Land)"':
        'placeholder="Search card (name or type, e.g. Creature, Instant, Land)"',
    "<label>Sortierung <select": "<label>Sort by <select",
    'value="mv">Manawert<': 'value="mv">Mana value<',
    'value="color">Farbe<': 'value="color">Color<',
    'value="mark">Zuordnung<': 'value="mark">Assignment<',
    'value="cat">Kategorie<': 'value="cat">Category<',
    "<label>Zielgröße <input": "<label>Target size <input",
    'title="Kartenzahl je Variante, alle Länder eingerechnet"> Karten</label>':
        'title="Number of cards per variant, all lands included"> cards</label>',
    'title="Farben, die im Deckvorschlag gespielt werden">Farben:': 'title="Colors played in the deck proposal">Colors:',
    'title="Baut aus den Kategorien ein eigenes Deck mit Ländern"':
        'title="Builds a custom deck with lands from the categories"',
    ">Deckvorschlag erstellen<": ">Create deck proposal<",
    'title="Simuliert den Deckvorschlag als weitere Variante neben Splash und NoSplash"':
        'title="Simulates the deck proposal as an additional variant alongside Splash and NoSplash"',
    "> mitsimulieren<": "> simulate too<",
    'title="Setzt die Zuordnung Core/Splash/NoSplash nach den Kategorien und füllt mit Filler auf"':
        'title="Sets the Core/Splash/NoSplash assignment by category and fills up with Filler"',
    ">Zuordnung nach Kategorien setzen<": ">Assign by category<",
    'title="Setzt Standardländer je Gruppe und ordnet passende Nicht-Standardländer zu (nach der aktuellen Zuordnung)"':
        'title="Sets basic lands per group and assigns suitable nonbasic lands (based on the current assignment)"',
    ">Länder empfehlen<": ">Recommend lands<",
    ">↶ Rückgängig<": ">↶ Undo<",
    "Deckvorschlag: eigenes Deck aus den Kategorien in den gewählten Farben, mit Ländern auf die\n"
    "          Faustregel aufgefüllt; die Zuordnung bleibt unverändert. MustPlay und Filler nur in den gewählten Farben,\n"
    "          Matchwinner und Splashworthy auch außerhalb.":
        "Deck proposal: custom deck from the categories in the chosen colors, filled up with lands to the\n"
        "          rule of thumb; the assignment stays unchanged. MustPlay and Filler only in the chosen colors,\n"
        "          Matchwinner and Splashworthy also outside.",
    "Standardländer <small>": "Basic lands <small>",
    "(Menge je Gruppe – auch Länder, die nicht im Pool sind, lassen sich hinzufügen)":
        "(amount per group – lands that are not in the pool can be added too)",
    # Overlays und Fenster
    "<b>Simulation läuft …</b>": "<b>Simulation running …</b>",
    "Format wie beim Import in MTG Arena und MTGO (Abschnitte Deck und Sideboard). Das Deck besteht aus\n"
    "    Core plus der Gruppe der Variante samt Standardländern; Sideboard sind alle übrigen Karten aus Deck und "
    "Sideboard der Datei.":
        "Format as for the import into MTG Arena and MTGO (Deck and Sideboard sections). The deck consists of\n"
        "    Core plus the group of the variant including basic lands; the sideboard is all other cards from the deck "
        "and sideboard of the file.",
    ">Schließen<": ">Close<",
    ">Laden<": ">Load<",
    'placeholder="Karte suchen (Name oder Typ)"': 'placeholder="Search card (name or type)"',
    '<label class="filter">Zeigen <select id="setfilter">': '<label class="filter">Show <select id="setfilter">',
    'value="">Alle Karten<': 'value="">All cards<',
    'value="nocat">Ohne Kategorie<': 'value="nocat">No category<',
    'value="noarch">Ohne Archetyp<': 'value="noarch">No archetype<',
    'value="W">Weiß<': 'value="W">White<',
    'value="U">Blau<': 'value="U">Blue<',
    'value="B">Schwarz<': 'value="B">Black<',
    'value="R">Rot<': 'value="R">Red<',
    'value="G">Grün<': 'value="G">Green<',
    'value="M">Mehrfarbig<': 'value="M">Multicolor<',
    'value="C">Farblos<': 'value="C">Colorless<',
    ">← Zurück zu den Karten<": ">← Back to the cards<",
    "Kategorie und Archetypen gelten je Kartenname für jeden\n"
    "    Pool und den Live-Draft (Dateien kartenbewertung.json und kartenarchetypen.json).":
        "Category and archetypes apply per card name for every\n"
        "    pool and the live draft (files kartenbewertung.json and kartenarchetypen.json).",
    'title="Bericht"': 'title="Report"',
    # JavaScript
    'nosplash:"NoSplash",off:"Aus"': 'nosplash:"NoSplash",off:"Off"',
    '"Bombe: entscheidet ein Match allein – kommt immer rein, notfalls als Splash"':
        '"Bomb: wins a match on its own – always makes the deck, as a splash if necessary"',
    '"Entscheidet Spiele allein – soll auf jeden Fall rein, auch wenn wir die Farbe nicht spielen"':
        '"Wins games on its own – should definitely be played, even if we are not playing that color"',
    '"Wird auf jeden Fall gespielt, wenn wir diese Farbe spielen"': '"Is definitely played if we play this color"',
    '"Füllt das Deck auf, wenn wir die Farbe spielen und nicht splashen"':
        '"Fills up the deck if we play the color and are not splashing"',
    '"Zu schlecht oder zu situativ, wird nicht gespielt"': '"Too weak or too situational, is not played"',
    '"Bewertung nicht gespeichert: "': '"Rating not saved: "',
    '||"Fehler"': '||"Error"',
    '"Im Pool: "': '"In pool: "',
    '"Nicht im Pool"': '"Not in pool"',
    'n===1?" Karte":" Karten"': 'n===1?" card":" cards"',
    '"Nicht-Standardländer"': '"Nonbasic lands"',
    '", aus Deck und Sideboard der Datei"': '", from deck and sideboard of the file"',
    'sel.title="Kategorie dieser Karte (gilt für alle Kopien)"': 'sel.title="Category of this card (applies to all copies)"',
    '"Kategorie: –"': '"Category: –"',
    '"abadge","Archetyp"': '"abadge","Archetype"',
    'isBest?"Bester Archetyp":"Archetyp"': 'isBest?"Best archetype":"Archetype"',
    '"Splash-Variante: "': '"Splash variant: "',
    'a+" Karten")': 'a+" cards")',
    '" · NoSplash-Variante: "': '" · NoSplash variant: "',
    'b+" Karten")': 'b+" cards")',
    '"  – unterschiedlich groß"': '"  – different sizes"',
    'COLOR_DE={W:"Weiß",U:"Blau",B:"Schwarz",R:"Rot",G:"Grün"}':
        'COLOR_DE={W:"White",U:"Blue",B:"Black",R:"Red",G:"Green"}',
    '"Archetypen von "': '"Archetypes of "',
    '"passt zu deinen Core-Farben"': '"fits your Core colors"',
    '"Erkannt: "': '"Detected: "',
    '" Core-Karten zugeordnet, "': '" Core cards assigned, "',
    '+" Punkte")': '+" points")',
    '"Keine farbigen Karten oder Quellen in dieser Variante."': '"No colored cards or sources in this variant."',
    '["Farbe","l",""]': '["Color","l",""]',
    '["Symbole",""': '["Symbols",""',
    '"Farbsymbole, die die Karten zwingend verlangen ({R}{R} zählt 2, Hybrid nicht)"':
        '"Color symbols that the cards strictly require ({R}{R} counts 2, hybrid does not)"',
    '["Karten","",': '["Cards","",',
    '"Karten, die die Farbe zwingend verlangen"': '"Cards that strictly require the color"',
    '["Quellen",""': '["Sources",""',
    '"Standardländer der Variante und zugeordnete Nicht-Standardländer"':
        '"Basic lands of the variant and assigned nonbasic lands"',
    '["Ø pünktlich",""': '["Avg on time",""',
    '"Chance, die Farbsymbole einer Karte bis Runde = Manawert zu haben (Play), gemittelt über die Karten der Farbe"':
        '"Chance of having the color symbols of a card by turn = mana value (on the play), averaged over the cards of the color"',
    '" NS)"': '" NB)"',
    '"davon "': '"of which "',
    '" Nicht-Standardländer"': '" nonbasic lands"',
    'Math.round(p*100)+" %");': 'Math.round(p*100)+"%");',
    '"Am knappsten: "': '"Tightest: "',
    '" ("+Math.round(r.worst.p*100)+" %)"': '" ("+Math.round(r.worst.p*100)+"%)"',
    '" Karten. NS = Nicht-Standardländer. Ø pünktlich wie in der "':
        '" cards. NB = nonbasic lands. Avg on time as in the "',
    '"Farbverteilung des Berichts; Ampel grün ab 90 %, gelb ab 80 %. Mit der Maus über dem Wert: die knappste Karte."':
        '"color distribution of the report; traffic light green from 90%, yellow from 80%. Hover over the value: the '
        'tightest card."',
    '": "+v+" Karten"': '": "+v+" cards"',
    '.toFixed(2).replace(".",",")': ".toFixed(2)",
    '"Splash-Variante: "+num.splash+" Karten, Ø Manawert "': '"Splash variant: "+num.splash+" cards, avg mana value "',
    '"NoSplash-Variante: "+num.nosplash+" Karten, Ø Manawert "':
        '"NoSplash variant: "+num.nosplash+" cards, avg mana value "',
    '"ohne Länder; Manawert 6+ zusammengefasst"': '"without lands; mana value 6+ combined"',
}
