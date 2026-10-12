# MTG Starthand-Simulator

Liest eine Deckliste, holt die Kartendaten von [Scryfall](https://scryfall.com) und simuliert viele Spiele
(On the Play und On the Draw). Das Ergebnis ist ein HTML-Bericht, der sich im Browser öffnet.

## Voraussetzungen

- Python 3.8 oder neuer, keine zusätzlichen Pakete
- Internetverbindung (Kartendaten von Scryfall)
- Zwei Dateien, die im **selben Ordner** liegen müssen: `mtg_sim.py` (Simulation und Bericht) und `scryfall.py` (Abruf und
  Cache der Kartendaten). Der Cache `scryfall_cache.json` entsteht automatisch daneben.

## Schnellstart

```
python mtg_sim.py deck.txt
```

Das schreibt `mtg_bericht.html` in den aktuellen Ordner und öffnet den Bericht im Browser. Auf manchen Systemen
heißt der Befehl `python3`. Im Terminal erscheinen nur kurze Statusmeldungen (Laden, Simulieren, Speicherort).

Standardmäßig werden 10 000 Spiele pro Modus simuliert. Das dauert etwas, liefert aber stabile Zahlen. Für einen
schnellen Test reicht zum Beispiel `--sims 1000`.

### Decks vergleichen

Mit gemeinsamem Kern (z. B. `core.txt` mit 32 Karten, `whitesplash.txt` und `nosplash.txt` mit je 8 Karten):

```
python mtg_sim.py whitesplash.txt nosplash.txt --core core.txt --seed 42
```

Die erste Variante ist die Basis, alle weiteren werden mit ihr verglichen. Ohne `--core` enthält jede Datei ein
vollständiges Deck.

Kerndeck mit mehreren Varianten für die letzten Karten (Splash, Removal-Paket, Kartenzieh-Motor …): Jede Variante ist
eine eigene Deckdatei. Die erste Datei ist die Basis, alle mit `--deckalt` angegebenen Decks werden dagegen verglichen:

```
python mtg_sim.py kern_mit_giants.txt --deckalt kern_splash.txt --deckalt kern_removal.txt --seed 42
```

## Format der Deckdatei

```
About
Name Mein Deck

Deck
17 Plains
4 Beispielkarte
4 Grand Entryway // Elegant Rotunda

Sideboard
2 Andere Karte
```

- Gelesen wird nur der Abschnitt `Deck`. `Sideboard`, `Commander` und `Companion` werden ignoriert.
- Zeilen haben die Form `Anzahl Kartenname`, ein `x` hinter der Zahl ist erlaubt. Set-Kürzel in Klammern am
  Zeilenende werden ignoriert.
- Die Zeile `Name ...` im Abschnitt `About` wird als Titel des Berichts verwendet, sonst der Dateiname.
- Karten, die Scryfall nicht findet, werden übersprungen. Sie erscheinen als Hinweis oben im Bericht.

## Parameter

Alle Parameter sind optional. Nur `deckfile` (die Deckdatei) ist Pflicht.

### Deck-Vergleich

| Parameter | Standard | Wirkung |
|---|---|---|
| `--core DATEI` | keiner | Kern-Deckliste (z. B. 32 Karten). Sie wird zu **jeder** angegebenen Deckdatei hinzugefügt. Die Dateien enthalten dann nur die Varianten (z. B. je 8 Karten). Name und Bericht-Titel kommen aus der Variante. |
| `--deckalt DATEI` | keiner | Weitere Deckliste, die mit dem Hauptdeck verglichen wird. Darf mehrfach angegeben werden. Alle Decks werden mit denselben Einstellungen simuliert. Gleiche Deck-Namen werden mit „(2)“ usw. unterschieden. |

### Umfang der Simulation

| Parameter | Standard | Wirkung |
|---|---|---|
| `--sims N` | `10000` | Anzahl der **gespielten** Spiele pro Modus (Play und Draw). Verlorene Spiele durch Mulligan kommen zusätzlich dazu und werden nicht mitgezählt. |
| `--seed N` | zufällig | Startwert des Zufallsgenerators. Mit gleichem Seed und gleichen Decklisten kommt exakt derselbe Bericht heraus. Jedes Deck bekommt daraus einen eigenen, festen Startwert. |
| `--turns N` | `3` | Bis zu welcher Runde die Hauptauswertung läuft: Spalten bei „Zauber pro Runde“, Kreaturen auf dem Feld nach Runde N und die Mana-Screw-Regel („weniger als N Länder auf dem Feld“). Die Ampelfarben gibt es nur für Runde 1 bis 3. |
| `--max-runden N` | `15` | Beobachtungszeitraum für Flood, Tempo (Hand leer, Top Card), Schaden und schnellsten Lethal. Jedes Spiel läuft mindestens so lange. |
| `--curve-runden N` | `6` | Bis zu welcher Runde die Curve-Auslastung berechnet wird (Tabellen und Diagramm). |

Die tatsächliche Länge eines Spiels ist der größte der drei Werte `--max-runden`, `--turns` und `--curve-runden`.

### Schwellenwerte für Kennzahlen

| Parameter | Standard | Wirkung |
|---|---|---|
| `--schaden N` | `20` | Gesamtschaden der Kreaturen, dessen erste Runde gemessen wird („Ø Runde für N Schaden“, Liniendiagramm, schnellster Lethal). |
| `--flood N` | `11` | Ab so vielen gezogenen Ländern (Starthand inklusive) bis zur Runde `--max-runden` gilt ein Spiel als geflutet. Bei weniger Runden ist der Wert schwerer zu erreichen. |

### Mulligan

| Parameter | Standard | Wirkung |
|---|---|---|
| `--ohne-mulligan` | aus (Mulligans aktiv) | Schaltet Mulligans ab: Jede 7-Karten-Hand wird gespielt. Der Abschnitt „Mulligan“ im Bericht entfällt. |
| `--min-handkarten N` | `5` | Fällt die Starthand durch Mulligans unter N Karten, gilt das Spiel als verloren und wird nicht gespielt. Bei `4` darf also noch auf 4 Karten gespielt werden. |

Die Mulligan-Regeln selbst (keine spielbare Karte nach Farben, 6 oder mehr Länder, höchstens 2 Länder bei weniger als
3 spielbaren Karten) sind fest eingebaut. Siehe „Feste Annahmen“.

### Landcycling

Diese Parameter wirken nur, wenn das Deck Karten mit Landcycling enthält (zum Beispiel „Basic landcycling {2}“).

| Parameter | Standard | Wirkung |
|---|---|---|
| `--ohne-landcycling` | aus (Landcycling aktiv) | Die Karten werden nur normal gespielt, nie gecycelt. Gut zum Vergleichen, was die Cycler dem Deck bringen. Der Abschnitt „Landcycling“ entfällt. |
| `--landcycling-runden N` | `3` | Bis zu welcher Runde ein fehlender Landdrop per Landcycling gesichert wird (Pflicht-Cycling, wenn kein Land auf der Hand ist). |
| `--landcycling-max-laender N` | `6` | Eine nicht spielbare Karte wird nur gecycelt, solange man (Feld plus Hand) weniger als N Länder hat. |
| `--landcycling-letzte-karte` | aus | Erlaubt Landcycling auch dann, wenn die Karte die letzte Karte auf der Hand wäre. Standard ist: nicht cyceln. Die Prüfung, ob sich Cycling lohnt, gilt weiterhin. |

### Empower Jace

| Parameter | Standard | Wirkung |
|---|---|---|
| `--ohne-jace` | aus (Jace wird simuliert) | Schaltet nur die **Simulation** von Jace ab: Es gibt keinen Jace-Token, keine Aktivierungen und keine zusätzlich gezogenen Karten. Die Zählung der Karten und die Einordnung im Abschnitt „Jace & Planeswalker“ bleiben erhalten. Gut zum Vergleichen, was Jace dem Deck bringt. |

Der Abschnitt „Jace & Planeswalker“ erscheint nur, wenn das Deck Karten mit „Empower Jace“ oder anderen
Planeswalker-Bezügen enthält. Er hat keine eigenen Schwellenwerte. Der Aktivierungswert 3 und die Grenze von einer
Aktivierung pro Runde sind fest im Skript (siehe „Feste Annahmen“).

### Spielregeln

| Parameter | Standard | Wirkung |
|---|---|---|
| `--auras-ohne-kreatur` | aus | Standard: Auras werden nur gespielt, wenn eine Kreatur auf dem Feld liegt oder in derselben Runde ausgespielt wird. Mit dem Parameter dürfen Auras auch ohne eigene Kreatur gespielt werden. |

### Ausgabe

| Parameter | Standard | Wirkung |
|---|---|---|
| `--neu-laden` | aus | Kartendaten werden in `scryfall_cache.json` neben dem Script gespeichert, bei späteren Läufen werden nur unbekannte Karten nachgeladen. Mit `--neu-laden` wird alles frisch von Scryfall geholt. |
| `--ausgabe DATEI` (auch `--html DATEI`) | `mtg_bericht.html` | Name und Ort des HTML-Berichts. Eine vorhandene Datei wird überschrieben. |
| `--nicht-oeffnen` | aus (Bericht wird geöffnet) | Der Bericht wird nur gespeichert, der Browser öffnet sich nicht. |
| `-h`, `--help` | | Zeigt die Kurzhilfe. |

## Beispiele

```
# Schneller Test mit weniger Spielen
python mtg_sim.py deck.txt --sims 1000

# Drei Varianten für die letzten 5 Karten vergleichen, reproduzierbar
python mtg_sim.py kern_a.txt --deckalt kern_b.txt --deckalt kern_c.txt --seed 42

# Wie viel bringen die Landcycler? Zwei Berichte vergleichen
python mtg_sim.py deck.txt --sims 5000 --ausgabe mit_cycling.html
python mtg_sim.py deck.txt --sims 5000 --ohne-landcycling --ausgabe ohne_cycling.html

# Wie hart sind die Mulligan-Regeln? Mit und ohne vergleichen
python mtg_sim.py deck.txt --sims 5000 --ohne-mulligan --ausgabe ohne_mulligan.html

# Schnellerer Lethal-Test: 15 statt 20 Schaden, Flood schon ab 10 Ländern
python mtg_sim.py deck.txt --schaden 15 --flood 10

# Frühes Spiel genauer: Auswertung bis Runde 4, Curve bis Runde 8
python mtg_sim.py deck.txt --turns 4 --curve-runden 8

# Was bringt Jace? Zwei Berichte vergleichen
python mtg_sim.py deck.txt --sims 5000 --ausgabe mit_jace.html
python mtg_sim.py deck.txt --sims 5000 --ohne-jace --ausgabe ohne_jace.html

# Bericht speichern, ohne den Browser zu öffnen
python mtg_sim.py deck.txt --nicht-oeffnen
```

## Feste Annahmen (nicht per Parameter änderbar)

Diese Werte stehen im Skript und lassen sich nur dort ändern.

- **Starthand:** 7 Karten. On the Play wird in Runde 1 nicht gezogen, On the Draw in jeder Runde.
- **Ampelgrenzen** für „Zauber gespielt in Runde 1 bis 3“ (Konstante `TRAFFIC` am Anfang der Datei):

  | | Runde 1 | Runde 2 | Runde 3 |
  |---|---|---|---|
  | On the Play, grün ab / gelb über | 20 % / 0 % | 90 % / 80 % | 95 % / 90 % |
  | On the Draw, grün ab / gelb über | 22 % / 0 % | 92 % / 83 % | 96 % / 85 % |

  Alles darunter ist rot. Beim schnellsten Lethal gilt: grün bis Runde 5, gelb Runde 6 und 7, rot ab Runde 8
  (Funktion `lethal_level`).
- **Mulligan-Regeln:** (1) mit den Länderfarben der Hand ist keine Karte spielbar (nur Farben, nicht die Manamenge),
  (2) 6 oder mehr Länder, (3) höchstens 2 Länder und weniger als 3 mit diesen Ländern bezahlbare Karten. Bei einem
  Mulligan wird neu gemischt und eine Karte weniger gezogen, dieselben Regeln gelten für jede neue Hand.
- **Kartenauswahl pro Runde:** Aus allen zusammen bezahlbaren Kombinationen gewinnt nacheinander: (1) die meiste
  Mana-Ausgabe, (2) die meisten Kreaturen, (3) die höchste Summe aus Power und Toughness, (4) die meisten Karten.
  Es gibt keine Vorausschau auf spätere Runden, außer beim Landcycling.
- **Kreaturen und Schaden:** aufgedruckte Power und Toughness, Einsatzverzögerung außer bei Haste, alle Kreaturen
  greifen jede Runde an, keine Blocker, kein Removal. Boni durch Auras oder andere Effekte werden nicht gezählt.
- **Mana:** Nur Mana aus Ländern. Manakreaturen, Artefakte und Rituale sind nicht modelliert.
- **Getappte Länder:** Werden aus dem Kartentext erkannt (immer getappt, Check-, Fast- und Slow-Länder). Shock-Länder
  zahlen die 2 Leben. Andere Bedingungen (zum Beispiel Reveal-Länder) werden als „immer getappt“ gezählt und im Bericht
  aufgelistet.
- **Empower Jace (Zählung):** Erkannt wird aus dem Kartentext von Scryfall, auf allen Seiten einer Karte. Eingeteilt wird nach
  Art: einmalig (Instant oder Sorcery, „beim Betreten“, einmaliger Sonderfall wie „beim Sterben“) und wiederkehrend
  („whenever“ und „at the beginning“-Auslöser, bezahlbare Fähigkeiten mit Kosten). Eine Karte kann in mehreren Gruppen
  stehen. Die Summe der Empower-Werte wird getrennt für einmalig und wiederkehrend ausgewiesen, bei wiederkehrenden als
  Wert je Auslösung. Zusätzlich gezählt werden Karten, die Jace oder Planeswalker erwähnen (helfend), Karten gegen
  Planeswalker (zerstören, Schaden) und Planeswalker-Karten selbst. Diese Bezüge werden nur gezählt, nicht simuliert.
  Neben jeder Karte steht im Bericht der erkannte Text, damit du die Einordnung prüfen kannst.
- **Empower Jace (Simulation):** Der Jace-Token startet mit 0 Loyalty und hat −3: eine Karte ziehen. Er wird aktiviert,
  sobald er mindestens 3 Loyalty hat und die Bibliothek nicht leer ist, **höchstens einmal pro Runde**: zu Rundenbeginn mit
  Loyalty aus früheren Runden, sonst nach dem Zaubern. Bei 0 Loyalty verschwindet der Token, der nächste Empower erstellt
  einen neuen. Einmalige Effekte wirken sofort beim Ausspielen (auch bei Ländern). Von den wiederkehrenden Effekten sind
  modelliert: „whenever you cast …“ (alle, Kreatur, Nichtkreatur, Instant oder Sorcery), „whenever … enters“ (Kreatur,
  Land, Permanent), „whenever … attacks“ und „at the beginning of …“ (einmal pro Runde ab der Folgerunde). Bezahlbare
  Fähigkeiten nutzen das Mana, das nach dem Zaubern übrig ist, so oft es reicht (höchstens 10-mal pro Runde, mit {T} im
  Preis einmal). Nicht modelliert und im Bericht aufgelistet sind unbekannte Auslöser, andere Kosten (Opfern, Ablegen)
  und Sonderfälle wie „beim Sterben“. Ein variabler Wert (X) zählt in der Simulation als 0. Modale Zauber zählen ihren
  Empower immer.
- **Jace-Statistik „bis die Hand leer ist“:** Gezählt wird bis zum ersten Rundenende ohne Karten auf der Hand (nach dem
  Zaubern und einer möglichen Aktivierung). Wird die Hand nie leer, zählt der ganze Beobachtungszeitraum
  (`--max-runden`). Jede Aktivierung zieht genau eine Karte, Aktivierungen und gezogene Karten sind also gleich viele.
- **Sicherung gegen unspielbare Decks:** Sind nach `50 × --sims + 1000` ausgeteilten Händen noch nicht `--sims`
  Spiele gespielt, bricht das Skript mit einer Fehlermeldung ab.

Eine ausführliche Beschreibung der Auswahllogik mit einem durchgerechneten Beispiel steht im Abschnitt „Spiellogik“
des Berichts.

## Was im Bericht steht

Deck-Vergleich (nur mit `--deckalt`), Auf einen Blick, Deck (Mana-Kurve, Farbverteilung, Kartentabelle), Mulligan, Jace & Planeswalker (nur bei passenden
Karten), Zauber pro Runde, Kreaturen, Mana Screw
und Flood, Curve-Auslastung, Spiellogik, Schaden durch Kreaturen, schnellster Lethal (mit Spielverlauf), Landcycling
(nur bei passenden Karten), Tempo und Modellannahmen. Die Modellannahmen im Bericht zeigen immer die Einstellungen,
mit denen er erzeugt wurde.

## Der Abschnitt „Deck-Vergleich“

Er erscheint nur mit `--deckalt` und steht ganz oben im Bericht.

- **Übersicht:** Welche Karten jede Alternative gegenüber dem Basisdeck hinzufügt (grün) oder entfernt (rot).
- **Fazit:** Pro Alternative und Modus, bei wie vielen Kennzahlen sie signifikant besser, schlechter oder
  nicht unterscheidbar ist.
- **Detailtabellen:** Pro Modus (Play und Draw) jede Kennzahl mit Wert ± Konfidenzintervall und der Differenz Δ zum Basisdeck.
- **Methode:** Anteile (z. B. Mana Screw) mit Wilson-Intervall (95 %), Mittelwerte mit Standardfehler. Eine Differenz gilt als
  signifikant, wenn |Δ| größer als 1,96 × Standardfehler der Differenz ist. Wegen der vielen Kennzahlen sind einzelne
  „signifikante“ Treffer nicht überzubewerten (Mehrfachvergleich). Bei identischen Decks lag die Fehlalarmquote in Tests
  bei etwa 7–10 % statt 5 %, die Intervalle sind also leicht zu optimistisch.

## Hinweise zur Deutung

- **Nur Zufallsstichproben:** Ergebnisse sind Schätzungen. Je höher `--sims`, desto kleiner die Schwankung.
- **Schnellster Lethal:** Das ist das beste von allen simulierten Spielen, also ein Glücksfall und kein Erwartungswert.
  Für den typischen Fall gelten „Ø Runde“ und das Liniendiagramm.
- **Deck-Vergleich:** Decklisten am besten mit `--deckalt` vergleichen. Kleine Unterschiede innerhalb der Intervalle sind
  Rauschen. Mehr `--sims` verkleinert die Intervalle.
- **Einstellungen vergleichen:** Wer Einstellungen (z. B. `--ohne-jace`) vergleicht, rechnet beide Läufe mit demselben
  `--sims` und `--seed` und öffnet die Berichte nebeneinander.
