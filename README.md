# MTG Starthand-Simulator

Liest eine Deckliste, holt die Kartendaten von [Scryfall](https://scryfall.com) und simuliert viele Spiele
(On the Play und On the Draw). Das Ergebnis ist ein HTML-Bericht, der sich im Browser öffnet.

Es gibt drei Teile:

- **Goldfish-Simulation und Bericht:** Das Deck spielt allein (ohne Gegner) und wird nach Mana, Tempo, Schaden,
  Mulligans und vielem mehr ausgewertet (siehe „Was im Bericht steht“).
- **Kampfmodell und Kampfbericht:** Das Deck spielt gegen Gegnerdecks (`_enemydeck*.txt`) mit Leben, Angriff,
  Blocks, Removal, Instants und vielen Kartenmechaniken. Ergebnis ist die Siegquote mit Protokollen einzelner
  Spiele (siehe „Kampf gegen Gegnerdecks“).
- **Drafthelper:** Eine Kartenseite für den Draft-Pool, auf der Varianten zusammengestellt, simuliert und gegen
  Gegnerdecks getestet werden (siehe „Draft-Helper“).

## Voraussetzungen

- Python 3.8 oder neuer, keine zusätzlichen Pakete
- Internetverbindung (Kartendaten von Scryfall)
- Die Dateien müssen so liegen: `mtg_sim.py` im Hauptordner und daneben der Ordner `components/` mit allen Bausteinen
  (`scryfall.py`, `cards.py`, `mana.py`, `simulation.py`, `report.py` …). Der Cache `scryfall_cache.json` entsteht
  automatisch neben `mtg_sim.py`.

## Tests

```
python -m unittest
```

im Projektordner. Es werden keine zusätzlichen Pakete und kein Netzwerk gebraucht (die Testkarten stehen in
`tests/fixtures.py`, `tests/fixtures_walkers.py` und in den Testdateien selbst); ein Lauf dauert etwa eine halbe
Minute. Die Tests decken Parser, Kartenmodell, Mana, Mulligan, Schadens- und Einsatzverzögerungs-Regeln der
Simulation (inklusive Referenzlauf mit festem Seed), das Kampfmodell (`tests/test_battle*.py`, je Ausbaustufe bzw.
Kartenpaket eine Datei), den Variantenbau und Server des Drafthelpers sowie Bericht und Kampfbericht ab. Die
Oberfläche im Browser (Sortierung, Suche, Export) ist nicht automatisch getestet.

**Arbeitsregel:** Neue Funktionen bekommen zuerst Tests, dann den Code. Neue Tests werden gegengeprüft, indem der
Code absichtlich kaputt gemacht wird (der Test muss dann fehlschlagen). Bestehende Tests werden nicht verändert,
damit sie grün werden; sollen sie wegen bewusst geändertem Verhalten angepasst werden, passiert das nur nach
ausdrücklicher Freigabe. Regelfragen werden mit dem Regelwerk `MagicCompRules.txt` (Comprehensive Rules) im
Projektordner geklärt; Abweichungen davon stehen mit Regelnummer im Code bzw. in den Regeln des Kampfberichts.

## Aufbau des Codes

| Datei | Aufgabe |
|---|---|
| `mtg_sim.py` | Startpunkt: Decks laden, simulieren, Bericht schreiben |
| `components/cli.py` | Alle Kommandozeilen-Parameter |
| `components/deckfile.py` | Deckdateien und Datei-Angaben (`datei=Label`) einlesen |
| `components/scryfall.py` | Kartendaten von Scryfall holen und zwischenspeichern |
| `components/mana.py` | Kosten, Hybrid/Phyrexian, Bezahlbarkeit durch Länder |
| `components/cards.py` | Kartenmodell `Card` und alle Parser aus dem Kartentext (Länder, Landcycling, Empower Jace, Draw, Surveil, Prepared, Mana, Kampf-Schlüsselwörter, Fähigkeiten, Auslöser, Token, modale Karten, Kostensenkung …) |
| `components/removal.py` | Removal-Erkennung und Removal-Score, Flash/Deathtouch, Abwerfen |
| `components/graveyard.py` | Friedhof-Score (Zweitverwertung, Zurückholen, Ressource) |
| `components/cardkinds.py` | Kartentypen und Kartenfluss für Seitenleiste und Bericht |
| `components/coverage.py` | Modell-Abdeckung: erkennt aus dem Kartentext, welche Effekte noch nicht simuliert werden |
| `components/jace.py` | Jace-Zustand in der Simulation, Effekt-Filter, Deck-Analyse |
| `components/mulligan.py` | Mulligan-Regeln und Starthand |
| `components/simulation.py` | Goldfish: Spielablauf, Zauber-/Landauswahl, Kostensenkung, Landcycling, Draw, Surveil, Prepared, Ramp, Messwerte |
| `components/battle.py` | Kampfmodell: zwei Spieler, Angriff, Block, Schaden, Removal, Instants, Fähigkeiten, Auslöser |
| `components/battle_report.py` | Kampfbericht (Siegquoten, Kennzahlen, Spieleliste mit Protokollen, Regeln) |
| `components/battle_server.py` | Gemeinsame Kampf-Schnittstelle für Drafthelper und Berichts-Server |
| `components/report_server.py` | Lokaler Server für den Bericht (`--bericht-server`, „Kampf simulieren“ im Bericht) |
| `components/landadvice.py` | Land-Empfehlung und „Farben und Quellen“ |
| `components/mana.py` | Kosten, Hybrid/Phyrexian, Bezahlbarkeit, Farbprüfungen (`pip_checks`) |
| `components/suggest.py` | Deckvorschlag und Zuordnung nach Kategorien im Drafthelper |
| `components/symbols.py` | Original-Manasymbole von Scryfall (Cache `scryfall_symbols.json`) |
| `components/stats.py` | Ampel-Schwellen, Zeitkennzahlen, Signifikanz-Rechnung |
| `components/html_base.py` | Gemeinsames Design (CSS im Stil des Drafthelpers), Seitenlayout, Tabellen, SVG-Diagramme |
| `components/report_sections.py` | Berichtsabschnitte Spiellogik, Deck-Vergleich, Jace |
| `components/report_cards.py` | Kartentabellen im Bericht |
| `components/howitworks.py` | Erklärseite „So funktioniert es“ |
| `components/report.py` | Bericht zusammensetzen |
| `components/drafthelper.py` | Drafthelper-Seite und -Server |

## Draft-Helper (`--drafthelper`)

```
python mtg_sim.py --drafthelper
```

Liest den Kartenpool aus `_draftedcardpool.txt` (Abschnitte `Deck` und `Sideboard`, Zeilen wie in den Deckdateien,
mit Setcode und Nummer) und öffnet im Browser eine Seite mit allen Karten als Bild (Daten und Bilder von Scryfall).
Eine andere Datei geht so: `python mtg_sim.py --drafthelper meinpool.txt`.

- Jede Kopie einer Karte (außer Standardländern) wird einzeln als **Core**, **Splash**, **NoSplash** oder **Aus** markiert. Vorbelegung:
  Deck = Core, Sideboard = Aus.
- **Kategorie je Karte** (Auswahl unter dem Bild, gilt für alle Kopien, höchstens eine): **★ Splashworthy**
  (entscheidet Spiele allein, soll auf jeden Fall rein, auch wenn wir die Farbe nicht spielen), **MustPlay**
  (wird gespielt, wenn wir diese Farbe spielen), **Filler** (füllt auf, wenn wir die Farbe spielen und nicht
  splashen) und **NeverPlay** (zu schlecht oder zu situativ). Die Kategorie ist unabhängig von
  Core/Splash/NoSplash/Aus und beeinflusst die Simulation nicht. Die Kopfleiste zählt je Kategorie und hat einen
  Filter „Karten zeigen“.
- **Deckvorschlag (eigenes drittes Deck):** Über den Karten stehen **Zielgröße** (Standard 40, wählbar 10 bis 200,
  alle Länder zählen mit), die **Farben** (W U B R G, vorbelegt mit den Farben des Cores) und der Button
  **Deckvorschlag erstellen**. Der Vorschlag baut aus den Kategorien ein eigenes Deck und lässt deine Zuordnung
  unverändert:
  - MustPlay und Filler kommen nur rein, wenn alle Farben der Karte gewählt sind (Farblos immer).
  - Splashworthy kommt immer rein; liegt die Farbe außerhalb der gewählten, ist die Karte ein Splash.
  - NeverPlay und Karten ohne Kategorie kommen nicht rein.
  - Länder: Nicht-Standardländer zählen als Länder, Standardländer werden bis zur Faustregel ergänzt (40 Karten:
    17, 60 Karten: 22; Bereich 15 bis 17 bzw. 20 bis 24, dazwischen linear) und nach den Farbsymbolen verteilt, je
    Splash-Farbe bis zu 3. Weicht die Länderzahl vom Bereich ab, steht ein Hinweis da.
  - Filler: Reihenfolge nach der gewählten Sortierung, danach Farben, die schon im Deck sind, danach Manawert
    aufsteigend.
  Mit dem Haken **mitsimulieren** wird der Vorschlag beim Simulieren als weitere Variante („Vorschlag“) neben Splash
  und NoSplash verglichen, und die Deckliste-Export-Ansicht zeigt ihn als dritte Spalte.
- **Zuordnung nach Kategorien setzen:** Der frühere Deck-Vorschlag: schreibt die Kategorien in die Zuordnung
  (MustPlay → Core, Splashworthy → Splash, NeverPlay → Aus, Filler füllt zuerst Core, dann NoSplash auf die
  Zielgröße). **↶ Rückgängig** stellt den Stand davor wieder her.
- **Übersicht links:** Karten je Farbe (Weiß, Blau, Schwarz, Rot, Grün, Mehrfarbig, Farblos, Länder) mit Pool-Menge,
  Zuordnung (Core/Splash/NoSplash) und Kategorien. Gezählt werden Kopien ohne Standardländer.
- **Suche und Sortierung:** Das Suchfeld über den Karten filtert nach Name oder (englischem) Typ, z. B. „Creature“.
  Die Sortierung (Manawert, Name, Farbe, Zuordnung, Kategorie) ändert nur die Anzeige, nicht die Zuordnungen.
- **Mana-Kurve links:** Anzahl der Nichtland-Karten je Manawert für Splash- und NoSplash-Variante nebeneinander,
  dazu Kartenzahl und Ø Manawert je Variante.
- **Mana-Kurve nach Farben (links):** Eine zweite Kurve unter der Mana-Kurve zeigt die Nichtland-Karten einer wählbaren
  Variante (Splash oder NoSplash) nach Manawert und Farbe. Zwei Ansichten: **Mehrfarbige gesondert** (gestapelt, jede
  Karte genau einmal, mehrfarbige Karten bilden ein goldenes Segment „Mehrfarbig“) und **Je Farbe** (eine mehrfarbige
  Karte zählt bei jeder ihrer Farben, die Balken ergeben dann mehr als die Kartenzahl). Eine Erklärung wechselt mit der
  Ansicht; darunter stehen Kartenzahl, mehrfarbige und farblose Karten sowie die vorkommenden Farbkombinationen
  („Schwarz/Rot 4 · Schwarz/Grün 1“).
- **Kartentypen je Variante (links):** Unter der Mana-Kurve steht für die Splash- und die NoSplash-Variante, wie
  viele Karten (Kopien, mit Standardländern) es gibt: Karten gesamt, Kreaturen, Instants, Sorceries, Artefakte,
  Verzauberungen, Planeswalker, Länder (davon Nicht-Standard-Länder) sowie Empower Jace (Karten und die Summe der
  sofortigen Loyalty beim Wirken oder Betreten, ohne X und ohne Auslöser). Artefakte und Verzauberungen zählen ohne
  Kreaturen und Länder; eine Karte kann in mehreren Zeilen stehen. Unterschiede zwischen den Varianten sind fett.
  Darunter steht der **Kartenfluss**: Karten, die ziehen (Draw, auch Cycling), Länder oder Karten suchen (Search,
  auch Landcycling), Surveil, Scry, Explore oder Mill haben. Mill ist getrennt nach „sich selbst“ (z. B.
  „Mill three cards“) und „Gegner möglich“ („target opponent mills“, „each opponent mills“; „target player mills“ und
  „each player mills“ zählen in beiden Zeilen, weil sie auch dich treffen können). Eine Karte zählt einmal gesamt und je Art. Es erscheinen nur
  Arten, die im Pool vorkommen. Auslöser, die nur auf Ziehen oder Scry/Surveil reagieren („whenever you draw …“),
  und Ziehen des Gegners zählen nicht; Empower Jace hat eine eigene Zeile.
  In „Kartentypen“ stehen außerdem Flash, Deathtouch, Removal (Score mit Ampel: grün ab 4, gelb ab 2,5 Punkten je
  40 Karten), Manaquellen und Prepared-Karten.
- **Farben und Quellen (links):** je Farbe die verlangten Symbole und die Quellen (Länder und Manaquellen) der
  Varianten, mit den Original-Manasymbolen von Scryfall.
- **Länder empfehlen:** setzt die Standardländer je Gruppe und ordnet passende Nicht-Standardländer zu. Ein
  Nicht-Standardland passt nur, wenn alle seine Farben im Deck sind; mindestens 3 Quellen je verlangter Farbe, der Rest
  nach Hypergeometrie; Länder = Zielgröße minus Zauber, begrenzt auf 15 bis 17.
- **Kampf simulieren:** Nach dem Simulieren lassen sich die Varianten gegen ein Gegnerdeck aus dem Projektordner
  (`_enemydeck*.txt`) antreten lassen; der Kampfbericht erscheint auf der Seite (siehe „Kampf gegen Gegnerdecks“).
- **Deckliste exportieren:** Der Button in der Kopfleiste zeigt beide Varianten im Arena/MTGO-Importformat
  (`Deck` und `Sideboard`, mit Set und Nummer), zum Kopieren oder Speichern als `draftgott_splash.txt` bzw.
  `draftgott_nosplash.txt`. Deck = Core + Gruppe der Variante + Standardländer, Sideboard = alle übrigen Karten.
- **Bericht, Abschnitt „Great in this deck!“:** listet je Variante die ★ Splashworthy- und MustPlay-Karten des
  Decks (mit Bereich) und weist darauf hin, wenn eine MustPlay-Karte (in der Splash-Variante auch eine
  Splashworthy-Karte) im Deck fehlt oder eine NeverPlay-Karte enthalten ist.
- **Standardländer** (Plains, Island, Swamp, Mountain, Forest) werden nicht als Einzelkarten markiert, sondern oben
  als Menge je Gruppe eingestellt (Core / Splash / NoSplash, mit − und +). Startwert ist die Anzahl im Deck der
  Datei als Core. Länder, die nicht im Pool sind (z. B. Swamp für einen anderen Splash), lassen sich ebenfalls
  hinzufügen.
- **Start per Doppelklick (Windows):** `draftgott.bat` im Projektordner doppelklicken. Ein Menü fragt nach der
  Betriebsart: **1 = Analyse** (simuliert `_normaldeck.txt` mit 10 000 Spielen, schreibt `meinbericht.html` und
  zeigt ihn über den Berichts-Server, damit „Kampf simulieren“ im Bericht funktioniert) oder **2 = Drafthelper**
  (Kartenseite mit `_draftedcardpool.txt`). Das Skript sucht Python selbst (`py` oder `python`). In beiden Fällen
  das schwarze Fenster offen lassen und zum Beenden den Button „Beenden“ auf der Seite benutzen oder das Fenster
  schließen. Weitere Parameter werden an den gewählten Aufruf angehängt (`draftgott.bat --sims 1000`).
- **Simulieren** baut die Varianten *Core + Splash* und *Core + NoSplash*, simuliert beide und zeigt den
  Vergleichsbericht direkt auf der Seite (zusätzlich als Datei, siehe `--ausgabe`). Danach geht es mit
  „Zurück zu den Karten“ weiter.
- Die Simulationsparameter (`--sims`, `--seed`, `--turns` …) kommen von der Kommandozeile, die Spielanzahl lässt
  sich auf der Seite ändern.
- Der Server läuft nur lokal (127.0.0.1, Port 8765, ist er belegt, ein freier Port). Beenden: Button „Beenden“ oder Strg+C im Terminal.
- Wird weder Splash noch NoSplash markiert, wird nur das Core-Deck simuliert.

## Schnellstart

```
python mtg_sim.py deck.txt
```

Das schreibt `mtg_bericht.html` in den aktuellen Ordner und öffnet den Bericht im Browser. Auf manchen Systemen
heißt der Befehl `python3`. Im Terminal erscheinen nur kurze Statusmeldungen (Laden, Simulieren, Speicherort).

Standardmäßig werden 10 000 Spiele pro Modus simuliert. Das dauert etwas, liefert aber stabile Zahlen. Für einen
schnellen Test reicht zum Beispiel `--sims 1000`.

### Decks vergleichen

**Herkunft der Karten:** Mit `--core` zeigt die Deckliste im Abschnitt „Deck“ alle Karten aus allen Dateien, jede Zeile mit
ihrem Bereich (z. B. `Core`, `Splash`, `Nosplash`). Mengen werden pro Bereich getrennt geführt, eine Karte kann in mehreren
Bereichen stehen: `Plains` mit 6 im Kern und 3 in `_nosplash.txt` erscheint als zwei Zeilen (6 × Core, 3 × Nosplash), im
Deck mit der Nosplash-Variante sind es 9. Die Bereiche sind farbig: Kern blau, erste Variante rot, zweite Variante gelb
(weitere ebenfalls gelb). Bereiche, die nicht zum gezeigten Deck gehören, sind blass dargestellt.
Der Bereichsname ist der Dateiname ohne führenden Unterstrich. Eigener Name: `_nosplash.txt=NoSplash` (auch bei `--core`
und `--deckalt`).

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

### Kampf gegen Gegnerdecks

| Parameter | Standard | Wirkung |
|---|---|---|
| `--gegner DATEI` | keiner | Kampf gegen dieses Gegnerdeck simulieren (z. B. `_enemydeck_bad_creatures.txt`), mehrfach angeben möglich. Der Goldfish-Bericht bleibt unverändert, der Kampf kommt in einen eigenen Bericht. |
| `--bericht-server` | aus | Zeigt den Bericht über einen lokalen Server statt nur als Datei, damit „Kampf simulieren“ im Bericht funktioniert. Das Programm läuft, bis es im Bericht beendet wird. |
| `--kampf-ausgabe DATEI` | `mtg_kampf.html` | Name des Kampfberichts. |
| `--kaempfe N` | `500` | Kämpfe je Deck und Modus (On the Play / On the Draw) gegen jedes Gegnerdeck. |
| `--kampf-runden N` | `20` | Rundengrenze im Kampf; danach ist das Spiel unentschieden. |

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

# Kampf gegen zwei Gegnerdecks mit je 1000 Kämpfen pro Modus
python mtg_sim.py deck.txt --gegner _enemydeck_bad_creatures.txt --gegner _enemydeck_hard_whiteblue_creatures.txt --kaempfe 1000

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
- **Kreaturen und Schaden:** aufgedruckte Power und Toughness, Einsatzverzögerung außer bei aufgedrucktem Haste, Kreaturen mit Defender
  greifen nie an (außer mit Ghalta the Immovable: dann greifen sie an, und Kreaturen mit mehr Toughness als
  Power machen Schaden in Höhe der Toughness), alle anderen Kreaturen greifen jede Runde an. Jace und andere Planeswalker haben keine
  Einsatzverzögerung (Aktivierung höchstens 1x pro Runde), keine Blocker, kein Removal. Gezählt werden +1/+1-Marken
  und Pumps beim Wirken oder Betreten (auf die stärkste angreifende Kreatur), Landfall-Schaden und -Marken, Marken
  am Rundenende ohne Zauber (Edgar) und bei Loyalty (Inspired Tethermage) sowie Schaden an den Gegner aus Zaubern und
  beim Betreten. Boni durch Auras und andere statische Effekte werden nicht gezählt.
- **Mana:** Länder, Manaquellen außer Ländern („{T}: Add …“ ohne Zusatzkosten; Kreaturen ab der Folgerunde,
  Artefakte sofort; für Mana getappte Kreaturen greifen nicht an) und Treasure (nur, wenn er in der Runde mehr
  ermöglicht). Rituale sind nicht modelliert.
- **Kostensenkung:** Nach den Kreaturen, die zu Rundenbeginn auf dem Feld liegen: Geist of Saint Thalia
  (Nichtkreatur-Zauber {1} billiger), Ghalta (um die höchste Power bzw. Toughness), Wrath of the Bloodmane (mit
  legendärer Kreatur); Traxos wird billiger, wenn in derselben Runde ein Nichtkreatur-Zauber gewirkt wird. Gesenkt wird
  nur generisches Mana, der Manawert bleibt gleich (601.2f); die Curve-Auslastung zählt das tatsächlich bezahlte Mana.
  Im Kampfmodell gilt dieselbe Rechnung.
- **Verliehene Loyalty-Fähigkeiten:** Way of the …, Sanctum Lurker, Kiora und Avatar geben dem Jace-Token
  weitere Fähigkeiten; gewählt wird wie im Kampfmodell, im Goldfish ohne Token (Schaden, Ziehen, Surveil,
  Mana, Marken, weiterer Landdrop).
- **Splinter Twin:** Die verzauberte Kreatur kopiert sich am Ende jedes gegnerischen Zugs (Haste, nur aufgedruckte
  Werte); die Kopie wiederholt ihre Betreten-Effekte und greift neben dem Original an. Gleiche Regeln wie im
  Kampfmodell (Wahl der Kreatur, 302.6, nur wenn die Kreatur schon liegt).
- **Draw, Surveil, Prepared:** Draw-Zauber mit fester Zahl ziehen sofort (Landdrop nachholen, mit übrigem Mana
  weiterzaubern). Surveil durch Karten nach dem Zaubern, Land zuerst. Prepared-Kreaturen: die Kopie der Zauberhälfte
  ist ein zusätzlicher Zauber ohne Handkarte, auch in der Runde des Betretens; Upkeep-Karten werden jede Runde wieder
  prepared.
- **Getappte Länder:** Werden aus dem Kartentext erkannt (immer getappt, Check-, Fast- und Slow-Länder). Shock-Länder
  zahlen die 2 Leben. Andere Bedingungen (zum Beispiel Reveal-Länder) werden als „immer getappt“ gezählt und im Bericht
  aufgelistet.
- **Länder mit Planeswalker-Bedingung** („enters tapped unless you control a planeswalker“, z. B. die Commons und
  Annexes aus FRA): Sie kommen untapped, wenn ein Planeswalker auf dem Tisch liegt. Das ist der Jace-Token (Loyalty
  größer 0) oder eine gewirkte Planeswalker-Karte. Liegt keiner da und ist ein Zauber auf der Hand, der einen
  Planeswalker erschafft (Planeswalker-Karte oder Empower Jace) und vor dem Land bezahlbar ist, wird dieser Zauber
  zuerst gewirkt und danach das Land gelegt. Tokens zählen nur auf dem Tisch, nie von der Hand.
- **„Behold a Jace“** (z. B. Theorist's Sanctum): Das Land kommt untapped, wenn ein Jace auf dem Tisch liegt (Token
  oder Planeswalker mit Untertyp Jace) oder eine Jace-Karte auf der Hand ist (sie wird nur gezeigt, nicht gewirkt).
  Andere Planeswalker genügen nicht. Als vorgezogener Zauber kommen nur Karten in Frage, die einen Jace erschaffen.
- **Kartentypen und Farben im Bericht:** Die Übersichten aus dem Drafthelper stehen auch im Bericht. Im Abschnitt
  „Deck“ ersetzt **„Mana-Kurve nach Farben“** die bisherige einfarbige Kurve: links gestapelt mit mehrfarbigen
  Karten als goldenem Segment (jede Karte einmal, Summe über dem Balken), rechts je Farbe (mehrfarbige Karten zählen
  bei jeder ihrer Farben). Darunter die Farbkombinationen. Daneben die Tabelle **„Kartentypen“** (Kreaturen,
  Instants, Sorceries, Artefakte, Verzauberungen, Planeswalker, Länder, Empower Jace, Kartenfluss nach Art). Im
  „Deck-Vergleich“ steht „Kartentypen im Vergleich“ mit einer Spalte je Deck, Unterschiede fett.
- **Jace und Surveil:** Der Jace-Token hat −1: Surveil 1 und −3: eine Karte ziehen, höchstens eine Aktivierung pro
  Runde. Zu Rundenbeginn wird nur gezogen (ab 3 Loyalty). Nach dem Zaubern: ab 3 Loyalty ziehen, sonst Surveil 1, auch
  wenn Jace dadurch auf 0 sinkt und verschwindet. Beim Surveil bleibt ein Land oben, wenn die teuerste Karte auf der
  Hand noch nicht gespielt werden kann, weil Länder fehlen (Länder auf dem Feld und auf der Hand weniger als ihr
  Manawert); sonst kommt es in den Friedhof. Zauber bleiben immer oben. Der Jace-Abschnitt im Bericht zeigt
  zusätzlich Ø Surveil und Ø abgelegte Länder.
- **Bericht und Erklärung getrennt („So funktioniert es“):** Der Bericht zeigt nur noch Daten. Alle Regeln und
  Lesehilfen (Spiellogik, Modellannahmen, Mulligan- und Jace-Regeln, Ampel-Schwellen, Statistik des Vergleichs,
  Zählregeln, Drafthelper …) stehen auf einer eigenen Erklärseite, Abschnitt für Abschnitt wie im Bericht. Oben im
  Bericht wechselt „Bericht | So funktioniert es“ die Ansicht; jeder Abschnitt hat einen Link „ⓘ So funktioniert es“
  zu seiner Erklärung, von dort führt „← Zurück zum Bericht“ wieder an dieselbe Stelle. Beides steckt in derselben
  HTML-Datei. Die Erklärseite beschreibt die Regeln allgemein mit Parametern und Standardwerten; die Werte des Laufs
  stehen oben im Bericht. Im Drafthelper gibt es die Erklärseite zusätzlich unter „So funktioniert es“ im Hilfekasten.
- **Design und Navigation:** Bericht und Kampfbericht haben das helle Design des Drafthelpers (Splash rot,
  NoSplash gold). Die Kopfleiste bleibt oben stehen. Links steht eine Seitenleiste mit **Kernzahlen** (Mulligan,
  Zauber in der Auswertungsrunde, schnellster Lethal, Ø Runde für den Schaden; im Kampfbericht die Siegquoten),
  den Sprungmarken zu den Abschnitten (der aktuelle Abschnitt ist markiert) und den Einstellungen des Laufs. Auf
  schmalen Bildschirmen (unter 900 Pixel) steht die Seitenleiste oben.
- **Farbverfügbarkeit (Bericht):** Eigener Abschnitt und eine Zeile in „Auf einen Blick“: Wie oft liegen nach dem
  Landdrop von Runde 3 **alle Farben** des Decks (mindestens eine Quelle je Farbe) und je Farbe einzeln? Für Farben, die
  eine Karte doppelt verlangt (z. B. RR, mit Kartennamen), zusätzlich: Wie oft liegen bis Runde 4 **zwei Quellen**?
  Quelle = Land auf dem Feld (auch getappt), ein Land mit mehreren Farben zählt für jede. Ampel: grün ab 90 %, gelb ab
  80 %. Im Deck-Vergleich stehen „Alle Farben bis Runde 3“ und die Zwei-Quellen-Werte als eigene Kennzahlen.
- **Modell-Abdeckung (Bericht):** Der Abschnitt „Modell-Abdeckung“ listet je Deck die Karten, deren Effekte die
  Simulation noch nicht abbildet, mit dem Status „To Do: Noch nicht implementiert“, einer groben Kategorie
  (Tokens, Direkter Schaden, Zählmarken / Stärkebonus, Haste verleihen, Mana außer Ländern, Kartenfluss,
  Kostensenkung, Zweitverwertung, Prepared, Interaktion mit dem Gegner, Lebensgewinn, …) und der betroffenen
  Kennzahl (Lethal, Mana und Zauber pro Runde, Kartenfluss, keine, unklar). Oben steht, wie viele Karten welche
  Kennzahl betreffen. Die Erkennung arbeitet nur über den Kartentext und ist grob; was nicht einzuordnen ist, heißt
  „Unbekannter Effekt“ (Kennzahl „unklar“). Die Zahlen im Bericht ändern sich dadurch nicht.
- **Einschränkung:** In einer Runde, in der ein Zauber vor dem Land gewirkt wird, entfällt das Landcycling nach dem
  Land (die Bezahlung wäre sonst nicht gesichert). Für die Planung der Folgerunde (Landcycling-Vorausschau) werden
  Planeswalker-Länder weiterhin als getappt behandelt.
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
der Erklärseite „So funktioniert es“.

## Was im Bericht steht

Deck-Vergleich (nur mit `--deckalt` bzw. mehreren Varianten), Great in this deck! (nur aus dem Drafthelper), Auf
einen Blick, Deck (Mana-Kurve nach Farben, Farbverteilung, Kartentypen, Kartentabelle), Removal, Friedhof,
Modell-Abdeckung, Mulligan, Jace & Planeswalker, Zauber pro Runde, Kreaturen, Mana Screw und Flood,
Farbverfügbarkeit, Splash-Karten (nur Splash-Variante aus dem Drafthelper), Curve-Auslastung, Schaden durch
Kreaturen, schnellster Lethal (mit Spielverlauf), Landcycling, Draw-Zauber, Surveil durch Karten, Prepared, Ramp
und Tempo. Abschnitte zu Mechaniken erscheinen nur, wenn das Deck passende Karten hat. Spiellogik, Modellannahmen
und die Erklärung jedes Abschnitts stehen auf der Erklärseite „So funktioniert es“; die Einstellungen des Laufs
stehen oben im Bericht und in der Seitenleiste.

Mit `--bericht-server` (bzw. Analyse über `draftgott.bat`) hat der Bericht oben die Leiste **Kampf simulieren**:
Gegnerdeck wählen, Kämpfe starten, der Kampfbericht öffnet sich danach.

## Kampf gegen Gegnerdecks

Gegnerdecks sind Deckdateien im Projektordner, deren Name mit `_enemydeck` beginnt (z. B.
`_enemydeck_bad_creatures.txt`, `_enemydeck_hard_whiteblue_creatures.txt`). Angezeigt wird die Zeile `Name` aus der
Datei, sonst der Dateiname ohne `_enemydeck_`. Gestartet wird der Kampf mit `--gegner`, über „Kampf simulieren“ im
Bericht (mit `--bericht-server`) oder im Drafthelper.

**Kampfbericht:** Siegquote je Gegner und Variante (Play / Draw) als Kacheln und in der Seitenleiste, eine Übersicht
(Siege, Niederlagen, davon durch Mulligan, Unentschieden), je Gegner Kennzahlen (Ø Runde, Kampfschaden und direkter
Schaden, gestorbene Kreaturen, Lebensverlauf), besondere Spiele und eine Spieleliste, in der jedes Spiel mit seinem
vollständigen Protokoll aufklappt. Die Regeln des Kampfmodells stehen ausführlich am Ende des Kampfberichts.

**Kampfmodell (Kurzfassung):**

- Beide Spieler starten mit 20 Leben und spielen nach denselben Regeln, ohne die Hand des anderen zu kennen.
  Mulligan wie in MTG Arena (wie im Goldfish); fällt unsere Hand unter die Mindestzahl, geben wir auf.
- Ein Zug: Untap, Draw, Main 1 (Land und alle Zauber außer Kreaturen ohne Haste; Kreaturen, deren Betreten den
  Kampf verbessert, schon hier), Kampf, Main 2, End Phase. Übriges Mana bleibt offen für Instants, Flash,
  Kampftricks und Fähigkeiten, auch im Zug des Gegners. Hat der Gegner eine Kreatur, die unser Removal töten kann,
  halten wir die Kosten des billigsten Instant-, Flash- oder Abwerf-Removals frei.
- Angriff: alles bei sicherem Lethal, sonst nur Kreaturen, die kein Blocker tötet und dabei überlebt. Block:
  Blocker tötet und überlebt, Tausch bei mindestens gleichem Manawert, Doppel-Block, Chump nur gegen Lethal.
- Kampf-Schlüsselwörter: Flying, Reach, First Strike, Double Strike, Deathtouch, Trample, Lifelink, Menace,
  Vigilance, Haste, Defender, Hexproof (auch bedingt, z. B. nur im eigenen Zug).
- Removal (Destroy/Exile, Schaden, −X/−X, Edikt, Fight, Biss, Bounce, Lock, zurück in die Bibliothek,
  Massenremoval) trifft die gefährlichste passende Kreatur; Removal-Instants vor dem Angriff, gegen Angreifer oder am
  Ende des gegnerischen Zugs.
- Modelliert sind u. a. Jace (Empower) mit Angriffen auf Jace, aktivierte Fähigkeiten, Token, Prowess,
  Auslöser beim Wirken, Betreten, Angriff, Tod, Lebensgewinn, Scry/Surveil und Landfall, Friedhof (Flashback, Zurückholen,
  Phoenix, Finality), modale Karten, Loot und Rummage, Ward, Ausrüstung, Stun-Marken, Karten aus dem
  Exil spielen, Schaden nach Toughness (Ghalta the Immovable), Legend-Regel, Handlimit, Kostensenkung und
  Zusatzkosten.
- Counterspells: gekontert wird, was Lethal bringt, Removal auf die gefährlichste eigene Kreatur und Kreaturen
  ab Manawert 3; ab Runde 5 bleibt Mana dafür frei. Festgelegt: keine Gegenkonter.
- Nicht modelliert sind u. a. Planeswalker außer dem Jace-Token, Convoke, Opfern als Kosten (außer Edgar, Ancient Bloodlord); solche Karten werden gespielt, wirken aber nur mit ihren modellierten Effekten.

## Details pro Variante

Mit `--deckalt` oder mehreren Deckdateien werden alle Detailabschnitte (Auf einen Blick bis Modellannahmen, also auch
Schnellster Lethal, Jace & Planeswalker, Mulligan, Curve …) für **jedes** Deck berechnet. Unter „Deck-Vergleich“ wählst du
mit den Knöpfen „Details für: …“ das Deck aus. Die Navigation oben passt sich an. Ohne JavaScript stehen alle Decks
untereinander.

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
