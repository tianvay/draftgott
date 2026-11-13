"""Englisches Woerterbuch: Erklaerseite "So funktioniert es"."""
EN = {
    '{mode} Runde {turn}: grün ab {g} %, gelb über {y} %':
        '{mode} turn {turn}: green from {g}%, yellow above {y}%',
    'Statistik':
        'Statistics',
    'Jedes Deck wird unabhängig mit der eingestellten Zahl an Spielen pro Modus simuliert (<code>--sims</code>, Standard {sims}). Hinter den Werten steht das 95-%-Konfidenzintervall (±). Ein Unterschied (Δ) ist farbig, wenn er größer ist als der zufällige Fehler (|Δ| &gt; 1,96 × Standardfehler), grün bei besser und rot bei schlechter. Mit ≈ markierte Unterschiede sind nicht von Zufall zu trennen. PP = Prozentpunkte. Bei so vielen Kennzahlen sind einzelne zufällige Ausreißer zu erwarten, achte deshalb auf das Gesamtbild. Für eine höhere Genauigkeit hilft eine größere <code>--sims</code>-Zahl.':
        'Each deck is simulated independently with the set number of games per mode (<code>--sims</code>, default {sims}). The 95% confidence interval (±) follows the values. A difference (Δ) is colored when it is larger than the random error (|Δ| &gt; 1.96 × standard error), green if better and red if worse. Differences marked ≈ cannot be told apart from chance. PP = percentage points. With this many metrics, a few random outliers are to be expected, so look at the overall picture. A larger <code>--sims</code> value gives higher accuracy.',
    'Kartentypen im Vergleich':
        'Card types compared',
    'Eine Spalte je Deck, gezählt wie im Abschnitt Deck (siehe dort). Fett: Unterschied zwischen den Decks.':
        'One column per deck, counted as in the Deck section (see there). Bold: difference between the decks.',
    'Ampeln':
        'Traffic lights',
    'Ampel Zauber pro Runde – {traffic}.':
        'Traffic light Spells per turn – {traffic}.',
    'Schnellster Lethal: grün bis Runde 5, gelb Runde 6–7, rot ab Runde 8.':
        'Fastest lethal: green up to turn 5, yellow turns 6–7, red from turn 8.',
    'Alle Farben bis Runde 3: grün ab {green} %, gelb ab {yellow} % (siehe Farbverfügbarkeit).':
        'All colors by turn 3: green from {green}%, yellow from {yellow}% (see Color availability).',
    'Die Ampel bei „Zauber pro Runde“ rechnet mit der angezeigten ganzen Prozentzahl.':
        'The traffic light for “Spells per turn” uses the whole percentage shown.',
    'Kartentypen':
        'Card types',
    'Gezählt werden Kopien. Artefakte und Verzauberungen ohne Kreaturen und Länder; eine Karte kann in mehreren Zeilen stehen (z. B. Artifact Enchantment). Länder gesamt enthält die Standardländer, „davon Nicht-Standard“ nur die übrigen. Σ Loyalty: Zahlenwerte von Empower Jace beim Zauber oder Betreten (ohne X, ohne Auslöser). Kartenfluss: Karten, die ziehen (auch Cycling), suchen (auch Landcycling), Surveil, Scry, Explore oder Mill haben; Mill getrennt nach „sich selbst“ und „Gegner möglich“ („target player“ zählt bei beiden). Es erscheinen nur Arten, die im Deck vorkommen. Auslöser wie „whenever you draw“ und Ziehen des Gegners zählen nicht, Empower Jace hat eine eigene Zeile. „Prepared (Karten)“: Karten, deren Zauberhälfte als Kopie gewirkt werden kann (nur, wenn solche Karten im Deck sind). Flash zählt nur bei bleibenden Karten, Deathtouch nur, wenn die Karte es selbst hat (nicht, wenn sie es verleiht).':
        'Copies are counted. Artifacts and enchantments exclude creatures and lands; a card can appear in several rows (e.g. Artifact Enchantment). Lands total includes the basic lands, “of which non-basic” only the others. Σ Loyalty: numeric values of Empower Jace on cast or enter (without X, without triggers). Card flow: cards that draw (including cycling), search (including landcycling), surveil, scry, explore or mill; mill is split into “self” and “opponent possible” (“target player” counts for both). Only kinds that occur in the deck are shown. Triggers like “whenever you draw” and the opponent drawing do not count; Empower Jace has its own row. “Prepared (cards)”: cards whose spell half can be cast as a copy (only if such cards are in the deck). Flash only counts on permanents, deathtouch only if the card has it itself (not if it grants it).',
    'Mana-Kurve nach Farben':
        'Mana curve by color',
    'Gezählt werden Nichtland-Karten nach Manawert (aufgerundet ab ,5; 7 und mehr zusammen).':
        'Nonland cards are counted by mana value (rounded up from .5; 7 and above together).',
    '<b>Mehrfarbige gesondert:</b> Jede Karte steht genau einmal im Diagramm, die Balkenhöhe ist die Kartenzahl. Karten mit mehreren Farben bilden das goldene Segment „Mehrfarbig“.':
        '<b>Multicolor separately:</b> Each card appears exactly once in the chart; the bar height is the card count. Cards with several colors form the golden “Multicolor” segment.',
    '<b>Je Farbe:</b> Eine mehrfarbige Karte zählt bei jeder ihrer Farben (eine Grün/Weiß-Karte bei Grün und bei Weiß). Die Balken ergeben deshalb zusammen mehr als die Kartenzahl.':
        '<b>Per color:</b> A multicolor card counts for each of its colors (a green/white card for green and for white). The bars therefore add up to more than the card count.',
    'Darunter: Zahl der Karten, davon mehrfarbig und farblos, und die vorkommenden Farbkombinationen.':
        'Below: number of cards, of which multicolor and colorless, and the color combinations that occur.',
    'Farbverteilung':
        'Color distribution',
    'Symbole = Farbsymbole, die diese Karten zwingend verlangen, mal Kopien ({R}{R} zählt 2, Hybrid nicht) · Karten = Nichtland-Karten, die die Farbe brauchen (in jedem Zahlungsweg; Hybrid zählt nicht) · Quellen = Länder, die sie erzeugen. Ein Land mit mehreren Farben zählt für jede davon. Ø pünktlich: Chance, dass bis zur Runde = Manawert (mindestens Runde 1, auf dem Play) genug Quellen für die Farbsymbole der Karte gezogen sind, gerechnet mit Hypergeometrie und gemittelt über die Karten der Farbe. Bei mehrfarbigen Karten werden die Farben multipliziert, die Gesamtzahl der Länder spielt keine Rolle. Ampel wie bei der Farbverfügbarkeit: grün ab {green} %, gelb ab {yellow} %. „Am knappsten“: die Karte der Farbe mit der niedrigsten Chance. Dieselbe Rechnung nutzt „Länder empfehlen“ im Drafthelper.':
        "Symbols = color symbols these cards strictly require, times copies ({R}{R} counts 2, hybrid does not) · Cards = nonland cards that need the color (in every way of paying; hybrid does not count) · Sources = lands that produce it. A land with several colors counts for each of them. Avg on time: chance that by the turn = mana value (at least turn 1, on the play) enough sources for the card's color symbols have been drawn, computed with the hypergeometric distribution and averaged over the cards of the color. For multicolor cards the colors are multiplied; the total number of lands does not matter. Traffic light as for color availability: green from {green}%, yellow from {yellow}%. “Tightest”: the card of the color with the lowest chance. “Recommend lands” in the Draft Helper uses the same calculation.",
    'Kartentabelle und Bereiche':
        'Card table and areas',
    'Beim Vergleich mit gemeinsamem Kern (Drafthelper oder <code>--core</code>) steht jede Karte mit ihrem Bereich (Core, Splash, NoSplash …). Mengen werden je Bereich getrennt geführt; blass dargestellte Bereiche gehören nur zu einer anderen Variante.':
        'When comparing with a shared core (Draft Helper or <code>--core</code>), each card is shown with its area (Core, Splash, NoSplash …). Quantities are kept separately per area; faded areas belong only to another variant.',
    'Bewertung':
        'Rating',
    'Jede Karte bekommt Punkte für ihren besten Removal-Effekt (alle Seiten, bei modalen Karten der beste Modus); 1 Punkt = entfernt jede gegnerische Kreatur zuverlässig. Σ Removal-Punkte ist die Summe über alle Kopien und liest sich wie „so viele harte Removals“.':
        'Each card gets points for its best removal effect (all sides; for modal cards the best mode); 1 point = reliably removes any opposing creature. Σ removal points is the sum over all copies and reads like “this many hard removals”.',
    '<b>Hart</b> (destroy/exile target creature) 1,0 · <b>Massenremoval</b> 1,0 · <b>Exil bis verlassen</b> („until … leaves the battlefield“) 0,9 · <b>Edikt</b> (Gegner opfert) 0,7, mit „greatest mana value“ 0,9 · <b>Toughness 0</b> (z. B. „has base power and toughness 0/0“; die Kreatur stirbt mit 0 Toughness) 0,7 · <b>Lock</b>-Aura (enttappt nicht, kann nicht angreifen) 0,7 · <b>Fight</b> 0,5 · <b>Bounce</b> 0,3 · zurück in die <b>Bibliothek</b> (der Besitzer wählt oben oder unten) 0,3.':
        "<b>Hard</b> (destroy/exile target creature) 1.0 · <b>Mass removal</b> 1.0 · <b>Exile until it leaves</b> (“until … leaves the battlefield”) 0.9 · <b>Edict</b> (opponent sacrifices) 0.7, with “greatest mana value” 0.9 · <b>Toughness 0</b> (e.g. “has base power and toughness 0/0”; the creature dies with 0 toughness) 0.7 · <b>Lock</b> aura (doesn't untap, can't attack) 0.7 · <b>Fight</b> 0.5 · <b>Bounce</b> 0.3 · back to the <b>library</b> (the owner chooses top or bottom) 0.3.",
    '<b>Schaden und −X/−X</b> nach Höhe: 1 → 0,2 · 2 → 0,4 · 3 → 0,6 · 4 → 0,8 · ab 5 → 0,9; X oder „damage equal to …“ 0,5. −X/−0 zählt nicht.':
        '<b>Damage and −X/−X</b> by amount: 1 → 0.2 · 2 → 0.4 · 3 → 0.6 · 4 → 0.8 · 5 and up → 0.9; X or “damage equal to …” 0.5. −X/−0 does not count.',
    '<b>Bedingt</b> (Bedingung am Ziel wie Manawert, Toughness, Flying, Farbe, oder eigenes Opfer): höchstens 0,5. <b>Fähigkeit</b> (bezahlbare Fähigkeit oder Planeswalker-Fähigkeit) und <b>Auslöser</b> (außer beim Betreten): halber Wert.':
        '<b>Conditional</b> (condition on the target such as mana value, toughness, flying, color, or your own sacrifice): at most 0.5. <b>Ability</b> (payable ability or planeswalker ability) and <b>trigger</b> (other than on entering): half value.',
    'Nicht gezählt: Counterspells, Kampftricks, Schaden nur an Spieler und verliehene Fähigkeiten in Anführungszeichen.':
        'Not counted: counterspells, combat tricks, damage to players only, and granted abilities in quotation marks.',
    'Ampel: grün ab 4, gelb ab 2,5 Punkten bei 40 Karten, bei anderer Kartenzahl anteilig. Richtwert für Limited: etwa 4 bis 6 Removal-Karten.':
        'Traffic light: green from 4, yellow from 2.5 points at 40 cards, proportionally for other card counts. Rule of thumb for Limited: about 4 to 6 removal cards.',
    'Die Tabelle zeigt jede erkannte Karte mit Art, Punkten je Karte, Summe und der erkannten Textstelle zur Kontrolle. Der Goldfish nutzt den Score nicht (es gibt keinen Gegner); im Kampfmodell wirken die Removal-Effekte selbst, der Score dient dort nur bei Gleichstand (z. B. welche Karte aus der Hand des Gegners gewählt wird).':
        "The table shows each recognized card with its kind, points per card, total and the recognized text passage for checking. The goldfish does not use the score (there is no opponent); in the battle model the removal effects themselves take effect, and the score is only used there as a tiebreaker (e.g. which card is chosen from the opponent's hand).",
    'Geber und Nehmer':
        'Givers and takers',
    'Jede Karte bekommt aus ihren erkannten Effekten Tags: was sie dem Deck <b>gibt</b> (Lebensgewinn, +1/+1-Marken, Buffs, Schutz wie Hexproof oder Indestructible, Nichtkreatur-Zauber, Surveil, Token, Opfer-Möglichkeiten, Artefakte, Kreaturtypen …) und wovon sie <b>profitiert</b> (z. B. „Whenever you gain life“, Prowess, Belohnungen für Marken, Sterbe- und Opfer-Auslöser, Friedhofsgröße).':
        'From its recognized effects each card gets tags: what it <b>gives</b> the deck (life gain, +1/+1 counters, buffs, protection like hexproof or indestructible, noncreature spells, surveil, tokens, sacrifice options, artifacts, creature types …) and what it <b>benefits from</b> (e.g. “Whenever you gain life”, prowess, rewards for counters, death and sacrifice triggers, graveyard size).',
    '<b>Aktive Synergie</b>: Wer Marken, Buffs oder Schutz verteilt, profitiert von Kreaturen im Deck; Auren und Ausrüstung profitieren von guten Trägern (Flying, Menace, Trample, Double Strike, Hexproof, Ward, unblockbar) und von Schutz.':
        '<b>Active synergy</b>: Cards that distribute counters, buffs or protection benefit from creatures in the deck; auras and equipment benefit from good carriers (flying, menace, trample, double strike, hexproof, ward, unblockable) and from protection.',
    '<b>Erfüllung</b> je Nehmer = 1 − (1 − p)<sup>k</sup>, k = Geber-Einheiten im Deck ohne die eigene Kopie, p je Ressource (z. B. Lebensgewinn 0,2, Nichtkreatur-Zauber 0,12, Kreaturen 0,08). Der dritte Geber bringt also weniger als der erste. Punkte = Gewicht des Nehmers × Erfüllung × Anzahl; die Summe ist der Synergiewert. Ampel je 40 Karten: grün ab {green}, gelb ab {yellow}.':
        '<b>Fulfillment</b> per taker = 1 − (1 − p)<sup>k</sup>, k = giver units in the deck excluding its own copy, p per resource (e.g. life gain 0.2, noncreature spells 0.12, creatures 0.08). The third giver therefore adds less than the first. Points = weight of the taker × fulfillment × count; the sum is the synergy score. Traffic light per 40 cards: green from {green}, yellow from {yellow}.',
    '<b>Ohne Partner</b>: Nehmer, deren Erfüllung unter {orphan} liegt – die Karte wartet im Deck auf Karten, die es kaum gibt.':
        '<b>Without partner</b>: takers whose fulfillment is below {orphan} – the card waits in the deck for cards that barely exist.',
    'Länder zählen nicht (Landfall ist in jedem Deck erfüllt). Im Live-Draft kommt der Zuwachs des Synergiewerts durch eine Pack-Karte (× 2, höchstens + 2) zu ihren Punkten.':
        'Lands do not count (landfall is fulfilled in every deck). In the live draft, the gain in synergy score from a pack card (× 2, at most + 2) is added to its points.',
    'Friedhof-Score':
        'Graveyard score',
    'Jede Karte bekommt Punkte für ihre beste Nutzung des Friedhofs (aus dem Kartentext): <b>Zweitverwertung</b> 1,0 (die Karte selbst noch einmal: Flashback, Escape, Unearth, Disturb, Jump-start, Retrace, „return this card from your graveyard“, Fähigkeiten mit „exile this card from your graveyard“) · <b>Zurückholen</b> 0,7 (andere Karten aus dem Friedhof auf die Hand oder ins Spiel) · <b>Ressource</b> 0,5 (Wert hängt vom Friedhof ab, Threshold, Delve, andere Karten aus dem Friedhof exilieren).':
        'Each card gets points for its best use of the graveyard (from the card text): <b>Second use</b> 1.0 (the card itself once more: flashback, escape, unearth, disturb, jump-start, retrace, “return this card from your graveyard”, abilities with “exile this card from your graveyard”) · <b>Recursion</b> 0.7 (other cards from the graveyard to hand or play) · <b>Resource</b> 0.5 (value depends on the graveyard, threshold, delve, exiling other cards from the graveyard).',
    '<b>Enabler</b> füllen den eigenen Friedhof (Mill, Surveil, Abwerfen, Cycling und Landcycling, „into your graveyard“); sie werden gezählt, haben aber keine Punkte.':
        '<b>Enablers</b> fill your own graveyard (mill, surveil, discarding, cycling and landcycling, “into your graveyard”); they are counted but have no points.',
    'Der Goldfish wirkt keine Karten aus dem Friedhof (außer Campus Crier: Empower aus dem Friedhof); der Score bewertet nur. Im Kampfmodell kommen Karten aus dem Friedhof zurück (Flashback, „return this card“, Phoenix, Reanimation, Fähigkeiten aus dem Friedhof).':
        'The goldfish does not cast cards from the graveyard (except Campus Crier: Empower from the graveyard); the score only rates. In the battle model, cards come back from the graveyard (flashback, “return this card”, Phoenix, reanimation, abilities from the graveyard).',
    'Friedhof in der Simulation':
        'Graveyard in the simulation',
    'In den Friedhof kommen gewirkte Instants und Sorceries (Prepared-Kopien nicht), gelandcycelte Karten und Karten, die Surveil oder Mill ablegt (Karten oder Jace). Kreaturen sterben im Goldfish nicht (kein Kampf mit Blockern); im Kampfmodell kommen gestorbene Kreaturen in den Friedhof.':
        'Cast instants and sorceries (not prepared copies), landcycled cards and cards that surveil or mill puts there (cards or Jace) go to the graveyard. Creatures are never killed in the goldfish (no combat with blockers); in the battle model, creatures that have died go to the graveyard.',
    'Gezählt wird mit den Manakosten der Karte; eine gelandcycelte 6-Mana-Kreatur zählt also 6.':
        "Counting uses the card's mana cost; a landcycled 6-mana creature therefore counts as 6.",
    '„Ø höchster Manawert“ ist für Karten wie Hapatra wichtig: X = höchster Manawert im Friedhof, wenn sie ins Spiel kommt (Ø X und wie oft X ≥ 3 bzw. ≥ 5).':
        '“Avg highest mana value” matters for cards like Hapatra: X = highest mana value in the graveyard when it enters the battlefield (avg X and how often X ≥ 3 or ≥ 5).',
    'Was hier steht':
        'What this shows',
    'Karten mit der Kategorie ♛ Matchwinner, ★ Splashworthy oder MustPlay aus dem Drafthelper, mit Bereich, Kosten und Eigenschaften.':
        'Cards with the category ♛ Matchwinner, ★ Splashworthy or MustPlay from the Draft Helper, with area, cost and properties.',
    '„Fehlt in diesem Deck“: eine MustPlay-Karte fehlt (in jeder Variante) oder eine Matchwinner- oder Splashworthy-Karte fehlt in der Splash-Variante. Für den Deckvorschlag gibt es diesen Hinweis nicht, weil er nach Farbregeln gebaut wird.':
        '“Missing from this deck”: a MustPlay card is missing (in every variant) or a Matchwinner or Splashworthy card is missing in the splash variant. This note does not exist for the deck suggestion because it is built by color rules.',
    '„NeverPlay-Karten im Deck“: Karten, die als NeverPlay gekennzeichnet und trotzdem im Deck sind.':
        '“NeverPlay cards in the deck”: cards marked as NeverPlay that are in the deck anyway.',
    'Wie die Karten eingeordnet werden':
        'How cards are classified',
    'Die Erkennung arbeitet über den Kartentext von Scryfall und sortiert nur grob, weil Magic dasselbe oft unterschiedlich formuliert. Status jeder gelisteten Karte: „To Do: Noch nicht implementiert“.':
        'Recognition works on the Scryfall card text and sorts only roughly, because Magic often words the same thing differently. Status of every listed card: “To do: not implemented yet”.',
    'Nicht gemeldet wird, was die Simulation abbildet: aufgedrucktes Haste und Defender, Landcycling, die Bedingungen getappter Länder, Empower Jace mit festem Wert, Draw-Zauber und Surveil mit fester Zahl, Prepared-Zauberhälften als Kopie (deren übrige Effekte stehen mit ihrer eigenen Kategorie da), Manaquellen und Treasure, Schaden an den Gegner beim Wirken oder Betreten, +1/+1-Marken und Pumps bis Rundenende beim Wirken oder Betreten, Landfall-Schaden und -Marken, Marken am Rundenende ohne Zauber (Edgar) und bei Loyalty (Tethermage), Kostensenkung (Geist of Saint Thalia, Ghalta, Wrath of the Bloodmane, Traxos) sowie Kampf-Schlüsselwörter ohne Gegner. Außerdem jede Zeile, die das Kartenmodell erkennt (Goldfish und/oder Kampfmodell, z. B. Removal, Token, Lebensgewinn, Planeswalker): Dafür wird die Karte nur mit dieser Zeile geparst; bei teilweise erkannten Zeilen bleibt der offene Rest stehen. Zeilen, deren Modell erst aus der ganzen Karte entsteht (z. B. der Bonus einer Ausrüstung zusammen mit ihren Equip-Kosten), gelten ebenfalls als abgedeckt.':
        "Not reported is what the simulation models: printed haste and defender, landcycling, the conditions of tapped lands, Empower Jace with a fixed value, draw spells and surveil with a fixed number, prepared spell halves as a copy (their other effects appear with their own category), mana sources and Treasure, damage to the opponent on cast or enter, +1/+1 counters and pumps until end of turn on cast or enter, landfall damage and counters, counters at end of turn without a spell (Edgar) and on loyalty (Tethermage), cost reduction (Geist of Saint Thalia, Ghalta, Wrath of the Bloodmane, Traxos) and combat keywords without an opponent. Also every line the card model recognizes (goldfish and/or battle model, e.g. removal, tokens, life gain, planeswalkers): for it the card is parsed with only that line; for partially recognized lines the open remainder stays listed. Lines whose model only arises from the whole card (e.g. an equipment's bonus together with its equip cost) also count as covered.",
    "Bewusst nicht (vollständig) modelliert und deshalb nicht gemeldet: Theorist's Proxy (opfert sich nie), Marwyn, the Preserver (Hexproof für Länder), Paradox Shaper ({2}: Karte unter die Bibliothek), Sphinx's Approach (fünf Exemplare), Winter, Team Player (Convoke), Tam, the Possibility (Proliferate) und Extrapolate the Impossible (Karten von außerhalb des Spiels).":
        "Deliberately not (fully) modeled and therefore not reported: Theorist's Proxy (never sacrifices itself), Marwyn, the Preserver (hexproof for lands), Paradox Shaper ({2}: card under the library), Sphinx's Approach (five copies), Winter, Team Player (convoke), Tam, the Possibility (proliferate) and Extrapolate the Impossible (cards from outside the game).",
    'Kategorien: Tokens erzeugen, Direkter Schaden, Zählmarken / Stärkebonus, Haste verleihen, Mana außer Ländern, Kartenfluss, Kostensenkung / Convoke, Zweitverwertung (Friedhof), Timing (Flash), Zusatzkosten, Prepared-Zauberhälfte, Planeswalker-Fähigkeit, Defender-Ausnahme, Interaktion mit dem Gegner, Lebensgewinn, Schlüsselwort verleihen und Empower-Sonderfälle. Was sich nicht einordnen lässt, heißt „Unbekannter Effekt“.':
        'Categories: create tokens, direct damage, counters / power bonus, grant haste, mana other than lands, card flow, cost reduction / convoke, second use (graveyard), timing (flash), additional costs, prepared spell half, planeswalker ability, defender exception, interaction with the opponent, life gain, grant keyword and Empower special cases. What cannot be classified is called “Unknown effect”.',
    'Betroffene Kennzahl: {metrics}. Bei „unklar“ ist nicht bekannt, was genau fehlt. Mit der Maus über der Kategorie steht die Textstelle.':
        'Affected metric: {metrics}. For “unclear” it is not known what exactly is missing. Hover over the category with the mouse to see the text passage.',
    'Wann es einen Mulligan gibt':
        'When there is a mulligan',
    '<b>Farben:</b> Mit den Farben der Länder auf der Starthand ist keine Karte spielbar (nur die Farben zählen, nicht die Manamenge).':
        '<b>Colors:</b> With the colors of the lands in the opening hand no card is castable (only the colors count, not the amount of mana).',
    '<b>Zu viele Länder:</b> 6 oder mehr Länder auf der Starthand.':
        '<b>Too many lands:</b> 6 or more lands in the opening hand.',
    '<b>Zu wenige Länder:</b> Höchstens 2 Länder und weniger als 3 Karten, die sich mit diesen Ländern bezahlen lassen (Manawert und Farben). Zwei Länder plus lauter 1- und 2-Mana-Karten werden also behalten.':
        '<b>Too few lands:</b> At most 2 lands and fewer than 3 cards that can be paid for with these lands (mana value and colors). Two lands plus only 1- and 2-mana cards are therefore kept.',
    'Bei einem Mulligan wird das Deck neu gemischt, es werden wieder 7 Karten gezogen und je Mulligan eine Karte unter die Bibliothek gelegt (London-Mulligan): behalten wird die Auswahl ohne Mulligan-Grund, dann mit dem Länderanteil am nächsten am Deck, dann mit den meisten bezahlbaren Karten, dann mit den geringsten Manakosten. Ausnahme Landcycling: eine Hand mit 6 oder 7 Karten, mindestens 2 Ländern, einer Karte mit Basic Landcycling und einer anderen Nichtland-Karte bis Manawert 3 wird trotz zu weniger Länder oder fehlender Farben behalten. Dieselben Regeln gelten für jede neue Hand. Fällt die Hand unter die Mindestzahl (<code>--min-handkarten</code>, Standard {min_hand}), gilt das Spiel als verloren; auch eine Hand dieser Größe, die einen Mulligan auslösen würde, zählt als verloren. Mit <code>--ohne-mulligan</code> wird jede 7-Karten-Hand gespielt.':
        "On a mulligan the deck is reshuffled, 7 cards are drawn again and one card per mulligan is put under the library (London mulligan): the selection without a mulligan reason is kept, then the one whose land share is closest to the deck's, then the one with the most castable cards, then the one with the lowest mana costs. Exception landcycling: a hand with 6 or 7 cards, at least 2 lands, a card with basic landcycling and another nonland card up to mana value 3 is kept despite too few lands or missing colors. The same rules apply to every new hand. If the hand falls below the minimum size (<code>--min-handkarten</code>, default {min_hand}), the game counts as lost; a hand of this size that would trigger a mulligan also counts as lost. With <code>--ohne-mulligan</code> every 7-card hand is played.",
    'Wie die Tabellen zu lesen sind':
        'How to read the tables',
    'Gründe: Anteil aller ersten 7-Karten-Hände. Die Gründe können zusammen auftreten, ihre Summe kann deshalb über dem Gesamtwert liegen.':
        'Reasons: share of all first 7-card hands. The reasons can occur together, so their sum can be above the total.',
    'Startgröße: Prozent aller ausgeteilten Starthände. Verlorene Spiele werden nicht gespielt und fließen nicht in die übrigen Zahlen ein: Alle anderen Auswertungen beruhen auf den gespielten Spielen nach dem Mulligan.':
        'Starting size: percent of all dealt opening hands. Lost games are not played and do not feed into the other numbers: all other evaluations are based on the games played after the mulligan.',
    'Modellregeln':
        'Model rules',
    'Σ Empower: bei wiederkehrenden Karten der Wert je Auslösung beziehungsweise je Aktivierung. Eine Karte kann in mehreren Kategorien stehen, die Summe der Zeilen ist deshalb größer als „gesamt“.':
        'Σ Empower: for recurring cards the value per trigger or per activation. A card can appear in several categories, so the sum of the rows is larger than “total”.',
    '„Bis die Hand leer ist“: gezählt bis zum ersten Rundenende ohne Karten auf der Hand (nach dem Zaubern und einer möglichen Jace-Aktivierung); wird die Hand nie leer, zählt der ganze Beobachtungszeitraum.':
        '“Until the hand is empty”: counted up to the first end of turn without cards in hand (after casting and a possible Jace activation); if the hand never becomes empty, the whole observation period counts.',
    '„Aktivierungen“ zählen das Ziehen (−3): Ø Aktivierungen ist zugleich die Zahl der durch Jace gezogenen Karten. „Ø Surveil“ zählt die −1-Aktivierungen, „Ø Länder in den Friedhof“ die dabei abgelegten Länder. „Ø Empower“ ist die erhaltene Loyalty insgesamt.':
        '“Activations” count drawing (−3): avg activations is also the number of cards drawn by Jace. “Avg surveil” counts the −1 activations, “Avg lands to graveyard” the lands put there in the process. “Avg Empower” is the total loyalty gained.',
    'Mit <code>--ohne-jace</code> wird Jace nicht simuliert, die Karten werden nur gezählt.':
        'With <code>--ohne-jace</code> Jace is not simulated; the cards are only counted.',
    'Bedeutung':
        'Meaning',
    'Anteil der Spiele, in denen in dieser Runde mindestens ein Zauber gespielt wird (Farben beachtet, gespielte Karten sind weg). Ausgewertet bis zur eingestellten Runde (<code>--turns</code>, Standard {turns}).':
        'Share of games in which at least one spell is cast in this turn (colors respected, cast cards are gone). Evaluated up to the set turn (<code>--turns</code>, default {turns}).',
    'Durchschnitt auf dem Feld nach der Auswertungsrunde (<code>--turns</code>), aufgedruckte Werte plus dauerhafte +1/+1-Marken, ohne Auras und Boni bis Rundenende.':
        'Average on the battlefield after the evaluation turn (<code>--turns</code>), printed values plus permanent +1/+1 counters, without auras and bonuses until end of turn.',
    '<b>Mana Screw:</b> nach der Auswertungsrunde (<code>--turns</code>) weniger Länder auf dem Feld als die Rundenzahl oder, bei mehrfarbigen Decks, keine zwei Farben.':
        '<b>Mana Screw:</b> after the evaluation turn (<code>--turns</code>) fewer lands on the battlefield than the turn number or, for multicolor decks, no two colors.',
    '<b>Flood:</b> bis zum Ende der Beobachtung (<code>--max-runden</code>, Standard {max_runden}) mindestens so viele Länder gezogen wie mit <code>--flood</code> eingestellt (Standard {flood}), die Starthand eingerechnet.':
        '<b>Flood:</b> by the end of the observation (<code>--max-runden</code>, default {max_runden}) at least as many lands drawn as set with <code>--flood</code> (default {flood}), the opening hand included.',
    'Quelle = Land auf dem Feld nach dem Landdrop der Runde (auch getappt), das die Farbe erzeugen kann, oder eine Manaquelle außer Ländern, die in der Runde Mana liefert (Kreaturen ab der Runde nach dem Wirken, Artefakte sofort; Treasure zählen nicht). Eine Quelle mit mehreren Farben zählt für jede davon.':
        "Source = land on the battlefield after the turn's land drop (also tapped) that can produce the color, or a non-land mana source that provides mana in the turn (creatures from the turn after casting, artifacts immediately; Treasure does not count). A source with several colors counts for each of them.",
    'Runde 3: von jeder Farbe, die Karten im Deck zwingend brauchen, mindestens eine Quelle (alle zusammen und jede einzeln).':
        'Turn 3: at least one source of every color that cards in the deck strictly need (all together and each individually).',
    'Mehrfach-Symbole: Für jede Farbe und Symbolzahl (WW, GGGG …), die eine Karte zwingend verlangt, zählt die günstigste Karte. Gemessen wird, wie oft bis zur Runde = ihr Manawert mindestens so viele Quellen der Farbe liegen, z. B. {2}{W}{W}{B} → 2 Quellen Weiß bis Runde 5, {G}{G}{G}{G} → 4 Quellen Grün bis Runde 4. Hybrid zählt nicht; liegt die Runde nach dem Ende der Beobachtung, steht „–“.':
        'Multiple symbols: for each color and symbol count (WW, GGGG …) that a card strictly requires, the cheapest card counts. What is measured is how often, by the turn = its mana value, at least that many sources of the color are in play, e.g. {2}{W}{W}{B} → 2 white sources by turn 5, {G}{G}{G}{G} → 4 green sources by turn 4. Hybrid does not count; if the turn lies after the end of the observation, “–” is shown.',
    'Ampel: grün ab {green} %, gelb ab {yellow} %, sonst rot. Mehr zu Manaquellen im Abschnitt Ramp.':
        'Traffic light: green from {green}%, yellow from {yellow}%, otherwise red. More on mana sources in the Ramp section.',
    'Nur im Bericht des Drafthelpers, für die Splash-Variante: alle Nichtland-Karten der Gruppe Splash.':
        "Only in the Draft Helper's report, for the splash variant: all nonland cards of the Splash group.",
    '<b>Gezogen:</b> Anteil der Spiele, in denen die Karte bis zum Ende der Beobachtung auf die Hand kommt (Starthand eingerechnet).':
        '<b>Drawn:</b> share of games in which the card reaches the hand by the end of the observation (opening hand included).',
    '<b>Spielbar, wenn gezogen:</b> Anteil dieser Spiele, in denen ihre Kosten irgendwann nach dem Landdrop mit den untappten Ländern bezahlbar sind (Farben und Manamenge; andere Zauber derselben Runde zählen nicht dagegen). Ampel wie bei der Farbverfügbarkeit: grün ab {green} %, gelb ab {yellow} %.':
        '<b>Castable when drawn:</b> share of these games in which its cost can be paid at some point after the land drop with the untapped lands (colors and amount of mana; other spells of the same turn do not count against it). Traffic light as for color availability: green from {green}%, yellow from {yellow}%.',
    '<b>Pünktlich:</b> bezahlbar spätestens in der Runde = Manawert, oder sofort, wenn sie erst später auf die Hand kommt. Zum Vergleich mit „Ø pünktlich“ in der Farbverteilung, die nur rechnet und Mulligan, getappte Länder, Landcycling, Draw und Surveil nicht kennt.':
        '<b>On time:</b> payable by the turn = mana value at the latest, or immediately if it only reaches the hand later. For comparison with “Avg on time” in the color distribution, which only calculates and does not know mulligan, tapped lands, landcycling, draw and surveil.',
    '<b>Ø Wartezeit:</b> Runden zwischen „auf der Hand“ und „erstmals bezahlbar“ (0 = sofort).':
        '<b>Avg wait:</b> turns between “in hand” and “first payable” (0 = immediately).',
    '<b>Gewirkt, wenn gezogen:</b> Anteil, in dem die Simulation die Karte tatsächlich gespielt hat (sie kann auch zugunsten anderer Karten warten).':
        '<b>Cast when drawn:</b> share in which the simulation actually cast the card (it may also wait in favor of other cards).',
    'Die Messung verändert den Spielablauf nicht.':
        'The measurement does not change the course of the game.',
    'Ausgegebenes geteilt durch verfügbares Mana je Runde (bis <code>--curve-runden</code>, Standard {curve_runden}). Verfügbar ist das Mana aus Ländern und aus Manaquellen außer Ländern (Manakreaturen, Artefakte, genutzte Treasure, siehe Ramp). Ausgegeben zählt das tatsächlich bezahlte Mana: Kostensenkung nach den Kreaturen, die zu Rundenbeginn auf dem Feld liegen (Geist of Saint Thalia, Ghalta nach höchster Power bzw. Toughness, Wrath of the Bloodmane mit legendärer Kreatur; Traxos, wenn in derselben Runde ein Nichtkreatur-Zauber gewirkt wird), macht Karten billiger, ihr Manawert bleibt gleich. Ein Rechenbeispiel steht unter Spiellogik.':
        'Spent divided by available mana per turn (up to <code>--curve-runden</code>, default {curve_runden}). Available is the mana from lands and from non-land mana sources (mana creatures, artifacts, used Treasure, see Ramp). Spent counts the mana actually paid: cost reduction by the creatures on the battlefield at the start of the turn (Geist of Saint Thalia, Ghalta by highest power or toughness, Wrath of the Bloodmane with a legendary creature; Traxos if a noncreature spell is cast in the same turn) makes cards cheaper, their mana value stays the same. A worked example is under Game logic.',
    'Erste Runde, in der der Gesamtschaden das Ziel erreicht (<code>--schaden</code>, Standard {schaden}). Ø und Median nur über Spiele, in denen es bis zum Ende der Beobachtung eintritt. Alle Kreaturen greifen jede Runde an, Einsatzverzögerung außer Haste, Defender greift nie an (außer mit Ghalta the Immovable, der auch Schaden nach Toughness gibt), keine Blocker oder Removal. Schaden = Power plus +1/+1-Marken und Pumps dieser Runde, dazu Schaden an den Gegner aus Zaubern, beim Betreten und durch Landfall (auch „any target“ zählt als Schaden an den Gegner). Marken und Pumps gehen an die stärkste Kreatur, die in dieser Runde angreift; dauerhafte Marken ohne Angreifer an die stärkste Kreatur, Pumps ohne Angreifer verpuffen. Modale Karten: der Modus mit dem meisten Schaden, bei Gleichstand der mit dauerhaften Marken. Edgar bekommt am Rundenende 2 Marken, wenn kein Zauber gewirkt wurde; Inspired Tethermage 1 Marke je Empower Jace.':
        'First turn in which total damage reaches the goal (<code>--schaden</code>, default {schaden}). Avg and median only over games in which it happens by the end of the observation. All creatures attack every turn, summoning sickness except haste, defender never attacks (except with Ghalta the Immovable, which also deals damage by toughness), no blockers or removal. Damage = power plus +1/+1 counters and pumps of this turn, plus damage to the opponent from spells, on entering and through landfall (also “any target” counts as damage to the opponent). Counters and pumps go to the strongest creature attacking this turn; permanent counters without attackers go to the strongest creature, pumps without attackers fizzle. Modal cards: the mode with the most damage, on a tie the one with permanent counters. Edgar gets 2 counters at end of turn if no spell was cast; Inspired Tethermage 1 counter per Empower Jace.',
    'Das schnellste aller simulierten Spiele, bei gleicher Runde das mit mehr Schaden, mit Starthand und Rundenprotokoll. Ein Glücksfall, kein Erwartungswert – die typische Runde steht unter „Schaden durch Kreaturen“.':
        'The fastest of all simulated games, on the same turn the one with more damage, with opening hand and turn log. A stroke of luck, not an expected value – the typical turn is under “Damage from creatures”.',
    'Regeln':
        'Rules',
    '<b>Land fehlt:</b> Ist in den ersten Runden (bis <code>--landcycling-runden</code>, Standard {landcycling_runden}) kein Land auf der Hand, wird ein Landcycler gecycelt, damit der Landdrop klappt.':
        '<b>Land missing:</b> If there is no land in hand in the first turns (up to <code>--landcycling-runden</code>, default {landcycling_runden}), a landcycler is cycled so that the land drop works.',
    '<b>Karte nicht spielbar:</b> Mit übrigem Mana wird eine Karte gecycelt, die in dieser Runde nicht spielbar ist, wenn es sich lohnt (Vorausschau auf die nächste Runde), und nur unter so vielen Ländern auf Feld und Hand wie eingestellt (<code>--landcycling-max-laender</code>, Standard {max_laender}).':
        '<b>Card not castable:</b> With leftover mana, a card that is not castable this turn is cycled if it is worthwhile (looking ahead to the next turn), and only with as few lands on the battlefield and in hand as set (<code>--landcycling-max-laender</code>, default {max_laender}).',
    'Die letzte Karte auf der Hand wird nicht gecycelt (außer mit <code>--landcycling-letzte-karte</code>); mit <code>--ohne-landcycling</code> wird nie gecycelt.':
        'The last card in hand is not cycled (except with <code>--landcycling-letzte-karte</code>); with <code>--ohne-landcycling</code> nothing is ever cycled.',
    '„Nicht-Land-Chance“: wie stark das Cycling die Chance erhöht, im nächsten Zug ein Nicht-Land zu ziehen.':
        '“Nonland chance”: how much the cycling raises the chance of drawing a nonland next turn.',
    'Modelliert sind Instants und Sorceries, die mit „Draw N cards.“ beginnen (N fest), und bleibende Karten mit „When this … enters, draw N cards.“. Steht in der Zeile noch mehr (z. B. Schaden), bleibt dieser Teil in der Modell-Abdeckung.':
        'Modeled are instants and sorceries that begin with “Draw N cards.” (N fixed) and permanents with “When this … enters, draw N cards.”. If the line contains more (e.g. damage), that part stays in the model coverage.',
    'Nicht modelliert: modale Karten („Choose one“), Ziehen mit Abwerfen, „you may“, X-Werte, Auslöser wie „whenever you gain life“ und bezahlbare Fähigkeiten. Sie stehen in der Modell-Abdeckung.':
        'Not modeled: modal cards (“Choose one”), drawing with discarding, “you may”, X values, triggers like “whenever you gain life” and payable abilities. They are listed in the model coverage.',
    'Draw-Zauber werden bei der Auswahl nicht bevorzugt, sondern nach denselben Auswahlregeln wie alle Zauber gewählt. Nach dem Zaubern kommen die Karten sofort auf die Hand: Ist der Landdrop noch frei, wird ein gezogenes Land gelegt, und mit dem übrigen Mana wird weiter gezaubert (auch weitere Draw-Zauber).':
        'Draw spells are not preferred when choosing; they are chosen by the same selection rules as all spells. After casting, the cards go to hand immediately: if the land drop is still free, a drawn land is played, and casting continues with the remaining mana (including further draw spells).',
    '„Ø zusätzlich gezogen“: Karten pro Spiel durch Draw-Zauber, bis zum Ende der Beobachtung. „Ø gleich genutzt“: danach im selben Zug zusätzlich gelegte Länder und gewirkte Zauber.':
        '“Avg extra drawn”: cards per game from draw spells, up to the end of the observation. “Avg used right away”: lands played and spells cast additionally in the same turn afterwards.',
    'Modelliert ist „Surveil N.“ als eigener Satz in Instants und Sorceries sowie „When this … enters, surveil N.“ bei Kreaturen, anderen bleibenden Karten und Ländern (N fest). Der Rest einer Zeile (z. B. Exil) bleibt in der Modell-Abdeckung.':
        'Modeled is “Surveil N.” as its own sentence in instants and sorceries as well as “When this … enters, surveil N.” on creatures, other permanents and lands (N fixed). The rest of a line (e.g. exile) stays in the model coverage.',
    'Surveil der Prepared-Kopie zählt wie bei anderen Zaubern. Nicht modelliert im Goldfish: Auslöser wie „whenever another creature enters“, bezahlbare Fähigkeiten, modale Karten und X-Werte (das Kampfmodell kennt die Auslöser).':
        'Surveil of the prepared copy counts as with other spells. Not modeled in the goldfish: triggers like “whenever another creature enters”, payable abilities, modal cards and X values (the battle model knows the triggers).',
    'Zeitpunkt: nach dem Zaubern der Runde, zuerst das gelegte Land, dann die Zauber in der Reihenfolge des Wirkens.':
        'Timing: after casting for the turn, first the land played, then the spells in the order of casting.',
    'Entscheidung wie bei Jace: Ein Land bleibt oben, solange für die teuerste Karte auf der Hand Länder fehlen (Länder auf dem Feld und auf der Hand zählen); sonst kommt es in den Friedhof. Zauber bleiben immer oben.':
        'Decision as with Jace: a land stays on top as long as lands are missing for the most expensive card in hand (lands on the battlefield and in hand count); otherwise it goes to the graveyard. Spells always stay on top.',
    'Surveils durch Jace stehen im Abschnitt Jace & Planeswalker und zählen hier nicht mit.':
        'Surveils by Jace are in the Jace & Planeswalker section and do not count here.',
    'Karten mit Zauberhälfte (Layout „prepare“): Die Kreatur wird normal gewirkt. Kommt sie prepared ins Spiel („enters prepared“), darf eine Kopie ihres Zaubers gewirkt werden; danach ist sie nicht mehr prepared. Steht „at the beginning of your upkeep … becomes prepared“ auf der Karte, wird sie in jedem eigenen Upkeep wieder prepared.':
        'Cards with a spell half (layout “prepare”): the creature is cast normally. If it enters prepared (“enters prepared”), a copy of its spell may be cast; afterwards it is no longer prepared. If “at the beginning of your upkeep … becomes prepared” is on the card, it becomes prepared again in each of your own upkeeps.',
    'Die Kopie kostet die Manakosten der Zauberhälfte, verbraucht keine Handkarte und zählt als gespielter Zauber und als ausgegebenes Mana. Sie wird mit den übrigen Zaubern nach denselben Auswahlregeln gewählt; bei Gleichstand kommt zuerst die Handkarte (die Kopie bleibt verfügbar).':
        'The copy costs the mana cost of the spell half, uses no card from hand and counts as a cast spell and as spent mana. It is chosen together with the other spells by the same selection rules; on a tie the hand card comes first (the copy stays available).',
    'Auch in der Runde, in der die Kreatur ins Spiel kommt, wird die Kopie mit dem übrigen Mana gewirkt.':
        'Also in the turn in which the creature enters, the copy is cast with the remaining mana.',
    'Effekte der Kopie wie bei anderen Zaubern: Draw N, Surveil N, Empower Jace, Schaden an den Gegner, Marken und Pumps, Mill und Heartwood-Token. Kreatur-Token und Loot der Kopie wirken nur im Kampfmodell.':
        'Effects of the copy as with other spells: draw N, surveil N, Empower Jace, damage to the opponent, counters and pumps, mill and Heartwood tokens. Creature tokens and loot of the copy only work in the battle model.',
    'Prepared-Karten mit anderem Wortlaut werden nicht als Kopie gewirkt und stehen in der Modell-Abdeckung als „Prepared-Zauberhälfte“.':
        'Prepared cards with different wording are not cast as a copy and appear in the model coverage as “Prepared spell half”.',
    'Manaquellen außer Ländern: bleibende Karten mit „{T}: Add …“ ohne Zusatzkosten, also eine Farbe („Add {G}“), eine Auswahl („Add {R} or {G}“), jede Farbe („one mana of any color“) oder mehrere Mana („Add {C}{C}“). Sie zählen wie zusätzliche Länder.':
        'Mana sources other than lands: permanents with “{T}: Add …” without additional costs, i.e. one color (“Add {G}”), a choice (“Add {R} or {G}”), any color (“one mana of any color”) or several mana (“Add {C}{C}”). They count like additional lands.',
    'Kreaturen liefern Mana ab der Runde nach dem Wirken (außer mit Haste), Artefakte und Verzauberungen sofort; kommen sie in dieser Runde ins Spiel, wird mit ihrem Mana noch weiter gezaubert.':
        'Creatures provide mana from the turn after casting (except with haste), artifacts and enchantments immediately; if they enter in this turn, casting continues with their mana.',
    'Wird das Mana einer Kreatur gebraucht, ist sie getappt und greift nicht an. Zuerst werden Länder, Artefakte und Treasure genutzt, dann die Kreaturen mit der kleinsten Power.':
        "If a creature's mana is needed, it is tapped and does not attack. Lands, artifacts and Treasure are used first, then the creatures with the smallest power.",
    'Treasure (aus „When … enters, create a Treasure token“ oder einem Zauber): bleibt liegen und wird nur geopfert, wenn er in einer Runde mehr Mana in Zauber bringt; ein Treasure gibt einmal ein Mana beliebiger Farbe.':
        'Treasure (from “When … enters, create a Treasure token” or a spell): stays around and is only sacrificed if it gets more mana into spells in a turn; a Treasure gives one mana of any color once.',
    'Heartwood-Token (aus Zaubern und beim Betreten) sind Artefakte und liefern sofort Mana; Mana aus verliehenen Jace-Fähigkeiten zählt in der Runde, in der es genutzt wird. Mana echter Planeswalker und Heartwood beim Sterben gibt es nur im Kampfmodell.':
        'Heartwood tokens (from spells and on entering) are artifacts and provide mana immediately; mana from granted Jace abilities counts in the turn in which it is used. Mana from real planeswalkers and Heartwood on dying only exists in the battle model.',
    'Nicht modelliert im Goldfish: Fähigkeiten mit Zusatzkosten („{1}, {T}: Add …“), Mana durch Opfern außer Treasure, Rituale und Treasure aus anderen Auslösern.':
        'Not modeled in the goldfish: abilities with additional costs (“{1}, {T}: Add …”), mana from sacrificing other than Treasure, rituals and Treasure from other triggers.',
    '„Spiele mit Ramp“: mindestens eine Runde mit Mana aus solchen Quellen; „Ø zusätzliches Mana“: Mana aus Manaquellen und genutzten Treasure je Runde; „Ø Angriffe ausgelassen“: Kreaturen, die für Mana getappt wurden und sonst hätten angreifen können.':
        '“Games with ramp”: at least one turn with mana from such sources; “Avg extra mana”: mana from mana sources and used Treasure per turn; “Avg attacks skipped”: creatures that were tapped for mana and could otherwise have attacked.',
    'Mana Screw und Flood zählen weiter nur Länder; die Farbverfügbarkeit zählt Manaquellen mit.':
        'Mana Screw and Flood still count only lands; color availability counts mana sources too.',
    'Ø und Median nur über Spiele, in denen das Ereignis bis zum Ende der Beobachtung eintritt. Top Card: die Karte(n) mit dem höchsten Manawert; gezählt wird die erste Runde, in der sie spielbar wäre.':
        'Avg and median only over games in which the event happens by the end of the observation. Top card: the card(s) with the highest mana value; the first turn in which it would be castable is counted.',
    'Annahmen':
        'Assumptions',
    'Starthand 7 Karten mit Mulligan-Regeln (siehe Mulligan); jede Runde ziehen (On the Play erst ab Runde 2), ein Land legen, zaubern.':
        'Opening hand of 7 cards with mulligan rules (see Mulligan); draw every turn (On the Play only from turn 2), play a land, cast spells.',
    'Jede Nichtland-Karte wird gespielt, sobald sie bezahlbar ist; pro Runde wird möglichst viel Mana ausgegeben.':
        'Every nonland card is cast as soon as it is payable; as much mana as possible is spent each turn.',
    'Farben, Hybrid- und Phyrexian-Mana werden beachtet; Manaquellen außer Ländern und Treasure siehe Ramp.':
        'Colors, hybrid and Phyrexian mana are respected; for mana sources other than lands and Treasure see Ramp.',
    'Länder, die getappt ins Spiel kommen, werden aus dem Kartentext erkannt; Shock-Länder zahlen die 2 Leben. Länder mit Planeswalker-Bedingung kommen untapped, wenn ein Planeswalker liegt; wenn möglich wird dafür zuerst ein Zauber gewirkt, der einen Planeswalker erschafft. „Behold a Jace“ gilt auch mit einer Jace-Karte auf der Hand.':
        'Lands that enter tapped are recognized from the card text; shock lands pay the 2 life. Lands with a planeswalker condition enter untapped if a planeswalker is in play; if possible, a spell that creates a planeswalker is cast first for this. “Behold a Jace” also works with a Jace card in hand.',
    'Auras werden nur mit eigener Kreatur gespielt (außer mit <code>--auras-ohne-kreatur</code>).':
        'Auras are only cast with a creature of your own (except with <code>--auras-ohne-kreatur</code>).',
    'Kreaturen: aufgedruckte Power/Toughness plus +1/+1-Marken, Einsatzverzögerung außer Haste, Defender greift nie an (außer mit Ghalta the Immovable, der auch Schaden nach Toughness gibt), keine Blocker oder Removal.':
        'Creatures: printed power/toughness plus +1/+1 counters, summoning sickness except haste, defender never attacks (except with Ghalta the Immovable, which also deals damage by toughness), no blockers or removal.',
    'Landcycling, Empower Jace, Draw-Zauber, Surveil durch Karten und Prepared: Regeln in den jeweiligen Abschnitten.':
        'Landcycling, Empower Jace, draw spells, surveil from cards and prepared: rules in the respective sections.',
    'Was die Simulation nicht abbildet, zeigt der Abschnitt Modell-Abdeckung je Deck.':
        'What the simulation does not model is shown by the Model coverage section for each deck.',
    'Diese Annahmen gelten für den Goldfish (ohne Gegner). Das Kampfmodell spielt gegen ein Gegnerdeck mit Blockern, Removal, Instants und Planeswalkern; seine Regeln stehen im Kampfbericht.':
        'These assumptions apply to the goldfish (no opponent). The battle model plays against an opponent deck with blockers, removal, instants and planeswalkers; its rules are in the battle report.',
    'Start':
        'Start',
    'Menüpunkt <b>3</b> in <code>draftgott.bat</code> oder <code>python mtg_sim.py --drafthelper _livedraft.txt --live</code>. Der Drafthelper liest das Protokoll von MTG Arena mit (<code>Player.log</code> unter <code>AppData/LocalLow/Wizards Of The Coast/MTGA</code>, anderer Pfad mit <code>--arena-log DATEI</code>). Gelesen wird nur diese Datei, das Spiel selbst wird nicht berührt.':
        'Menu item <b>3</b> in <code>draftgott.bat</code> or <code>python mtg_sim.py --drafthelper _livedraft.txt --live</code>. The Draft Helper reads along with the MTG Arena log (<code>Player.log</code> under <code>AppData/LocalLow/Wizards Of The Coast/MTGA</code>, another path with <code>--arena-log FILE</code>). Only this file is read; the game itself is not touched.',
    'In Arena muss unter Optionen → Konto „Detailed Logs (Plugin Support)“ eingeschaltet sein (danach Arena neu starten).':
        'In Arena, “Detailed Logs (Plugin Support)” must be switched on under Options → Account (then restart Arena).',
    'Die Kartennamen kommen aus Arenas eigener Kartendatenbank (im Installationsordner), sonst aus Scryfall.':
        "Card names come from Arena's own card database (in the install folder), otherwise from Scryfall.",
    'Jeder Pick landet sofort in der Kartenpool-Datei (<code>_livedraft.txt</code>, Format wie der Deck-Export von Arena); die Seite lädt danach neu und zeigt den Pool wie gewohnt. Ein neuer Draft beginnt die Datei von vorn. Auch ein schon laufender Draft wird beim Start nachgelesen.':
        "Each pick goes straight into the card pool file (<code>_livedraft.txt</code>, same format as Arena's deck export); the page then reloads and shows the pool as usual. A new draft starts the file from scratch. A draft that is already running is also read back at startup.",
    'Aktuelles Pack':
        'Current pack',
    'Oben auf der Seite steht das Pack, aus dem du gerade wählst, als Rangliste. Punkte je Karte: Kategorie (♛ Matchwinner 5, ★ Splashworthy 4, MustPlay 3, ohne Kategorie 1,5, Filler 1) + 3, wenn die Karte dem Archetyp zugeordnet ist (grün hervorgehoben, „passt zu …“), + 4, wenn er ihr bester Archetyp ist (lila, pulsierender Rand, „am besten in …“), sonst + 1, wenn ihre Farben in den Farben des Archetyps liegen (hellgrün). NeverPlay hat immer 0 Punkte.':
        "At the top of the page is the pack you are currently picking from, as a ranking. Points per card: category (♛ Matchwinner 5, ★ Splashworthy 4, MustPlay 3, no category 1.5, Filler 1) + 3 if the card is assigned to the archetype (highlighted green, “fits …”), + 4 if it is its best archetype (purple, pulsing border, “best in …”), otherwise + 1 if its colors are within the archetype's colors (light green). NeverPlay always has 0 points.",
    '<b>Synergie</b>: Dazu kommt, wie viel die Karte den Synergiewert deiner Picks erhöht (bis + 2, „Synergie + … mit …“ unter der Karte, im Seitenfenster „Syn+“). Mit erkanntem Archetyp zählen nur Picks in seinen Farben. Synergie heißt: Eine Karte profitiert von anderen (Lebensgewinn-Auslöser und Lebensgewinn, Prowess und Nichtkreatur-Zauber, Marken-Belohnungen und Marken, Auren und Ausrüstung mit fliegenden oder geschützten Trägern, Marken und Buffs verteilen mit genug Kreaturen, Kreaturtypen …). Der Bericht hat dazu den Abschnitt „Synergie“.':
        '<b>Synergy</b>: On top comes how much the card raises the synergy score of your picks (up to + 2, “Synergy + … with …” under the card, “Syn+” in the overlay). With a recognized archetype only picks in its colors count. Synergy means: a card benefits from others (life gain triggers and life gain, prowess and noncreature spells, counter rewards and counters, auras and equipment with flying or protected carriers, distributing counters and buffs with enough creatures, creature types …). The report has the section “Synergy” on this.',
    '<b>Top-Pick</b>: Eine Karte ab MustPlay, deren bester Archetyp dein Archetyp ist (erkannt oder selbst gewählt) oder bei der du nahe dran bist (ihr bester Archetyp hat Punkte und liegt höchstens 3 Punkte hinter dem führenden), steht lila und pulsierend oben im Live-Bereich („◆ Top-Pick: …“) und blinkend oben im Seitenfenster, auch im minimierten Kasten.':
        '<b>Top pick</b>: A card of MustPlay or higher whose best archetype is your archetype (recognized or chosen yourself) or where you are close (its best archetype has points and is at most 3 points behind the leader) is shown purple and pulsing at the top of the live area (“◆ Top pick: …”) and blinking at the top of the overlay, also in the minimized box.',
    'Kategorie und Archetypen lassen sich direkt an den Pack-Karten festlegen; das gilt sofort.':
        'Category and archetypes can be set directly on the pack cards; this takes effect immediately.',
    'Pick Two: beide gewählten Karten zählen als Picks.':
        'Pick Two: both chosen cards count as picks.',
    'Kennzahlen der Picks':
        'Pick metrics',
    'Im Live-Bereich und im Seitenfenster stehen zu den bisherigen Picks: Kreaturen, Removal (Karten und Removal-Punkte wie im Bericht) und Kartenfluss (Karten, die ziehen, suchen, surveilen, scrien oder explorieren). Ist ein Archetyp erkannt, dieselben Zahlen noch einmal nur für Karten in seinen Farben (farblose zählen mit).':
        'The live area and the overlay show, for your picks so far: creatures, removal (cards and removal points as in the report) and card flow (cards that draw, search, surveil, scry or explore). If an archetype is recognized, the same numbers once more for only the cards in its colors (colorless ones count too).',
    'Pack-Karten mit Removal tragen ihre Removal-Punkte (im Seitenfenster „R1,5“).':
        'Pack cards with removal carry their removal points (“R1.5” in the overlay).',
    'Archetypen im Draft':
        'Archetypes in the draft',
    'Eine Tabelle zeigt je Archetyp, welche deiner Picks und welche Karten des aktuellen Packs ihm zugeordnet sind (Picks mit Anzahl). Grün: der erkannte Archetyp. Das Seitenfenster zeigt dasselbe kurz („Sacrifice: 3 Picks · im Pack: …“).':
        'A table shows, per archetype, which of your picks and which cards of the current pack are assigned to it (picks with count). Green: the recognized archetype. The overlay shows the same in short (“Sacrifice: 3 picks · in pack: …”).',
    'Tipps zum Archetyp: Ist ein Archetyp erkannt oder gewählt und hat das Set Archetypen mit Hinweisen, stehen dessen Tipps während des Drafts unten im Live-Bereich und unten im Seitenfenster.':
        'Archetype tips: If an archetype is recognized or chosen and the set has archetypes with hints, its tips are shown during the draft at the bottom of the live area and at the bottom of the overlay.',
    'Es zählt nur deine eigene Zuordnung (Knöpfe unter den Karten, kartenarchetypen.json): Karten ohne Zuordnung gehören keinem Archetyp an, eine Karte kann zu mehreren gehören. Archetypen ohne Karten fehlen.':
        'Only your own assignment counts (buttons under the cards, kartenarchetypen.json): cards without an assignment belong to no archetype, a card can belong to several. Archetypes without cards are missing.',
    'Pack-Karten nennen ihre Archetypen zusätzlich unter dem Namen.':
        'Pack cards also name their archetypes under the name.',
    '<b>Drei Stufen</b> je Archetyp-Knopf: Klick schaltet neutral → grün (passt gut) → lila (bester Archetyp) → neutral. Eine Karte hat höchstens einen besten Archetyp; wird ein anderer lila, wird der bisherige wieder grün. Der beste zählt wie eine Zuordnung, im Pack mit + 4 statt + 3. Im Pool trägt eine Karte, deren bester Archetyp der erkannte ist, einen lila pulsierenden Rahmen. Der Bericht nennt im Archetyp-Kasten „Am besten in …“.':
        '<b>Three levels</b> per archetype button: a click switches neutral → green (fits well) → purple (best archetype) → neutral. A card has at most one best archetype; if another turns purple, the previous one turns green again. The best one counts like an assignment, in the pack with + 4 instead of + 3. In the pool, a card whose best archetype is the recognized one has a purple pulsing frame. The report names “Best in …” in the archetype box.',
    'Offene Farben':
        'Open colors',
    'Während des Drafts zeigen Live-Bereich und Seitenfenster, welche Farben offen sind („Signale (Pick Two): R offen +3 · G umkämpft −2“). Stark ist eine Karte mit deiner Kategorie MustPlay oder höher (★ Splashworthy, ♛ Matchwinner); mehrfarbige zählen für jede ihrer Farben, farblose nicht.':
        'During the draft the live area and overlay show which colors are open (“Signals (Pick Two): R open +3 · G contested −2”). A card with your category MustPlay or higher (★ Splashworthy, ♛ Matchwinner) counts as strong; multicolor cards count for each of their colors, colorless ones do not.',
    '<b>Wheel</b> (+2): Ein Pack kommt zurück und eine starke Karte liegt noch drin – das Hauptsignal. Ein Pack gilt als zurückgekommen, wenn es eine Teilmenge eines früheren Packs derselben Runde (ohne deine Picks daraus) ist; das klappt für jede Spielerzahl, für Pick Two wie für den normalen Draft.':
        '<b>Wheel</b> (+2): A pack comes back and a strong card is still in it – the main signal. A pack counts as returned if it is a subset of an earlier pack of the same round (without your picks from it); this works for any number of players, for Pick Two as for the normal draft.',
    '<b>Spät</b> (+1): eine starke Karte in einem Pack, das schon mindestens 3 andere Spieler gesehen haben. Gezählt werden Spieler, nicht Karten: Pick Two nimmt 2 Karten je Pick, ein Pack mit 8 von 14 Karten haben also 3 Spieler gesehen (im normalen Draft 6).':
        '<b>Late</b> (+1): a strong card in a pack that at least 3 other players have already seen. Players are counted, not cards: Pick Two takes 2 cards per pick, so a pack with 8 of 14 cards has been seen by 3 players (6 in the normal draft).',
    '<b>Umkämpft</b> (−1): eine starke Karte, die zwischen zwei Besuchen eines Packs von anderen genommen wurde.':
        '<b>Contested</b> (−1): a strong card that was taken by others between two visits to a pack.',
    'Wert je Farbe = offen − umkämpft: ab 3 offen, ab 1 evtl. offen, ab −2 umkämpft. Pick Two erkennt der Drafthelper an zwei Karten je Pick (sonst am Eventnamen). Darunter stehen die letzten Hinweise („Pick 9: … kam zurück“).':
        'Value per color = open − contested: from 3 open, from 1 maybe open, from −2 contested. The Draft Helper recognizes Pick Two by two cards per pick (otherwise by the event name). Below are the latest notes (“Pick 9: … wheeled”).',
    'Im Spiel: Tricks bei offenem Mana':
        'In game: tricks with open mana',
    'Oben in der Spielansicht der Seite und im Trick-Warner (eigenes Fenster) stehen alle Instants und Karten mit Flash des Sets, die der Gegner mit seinen ungetappten Ländern jetzt wirken könnte, mit Kosten, deiner Kategorie und Removal-Punkten. Aktivierbare Fähigkeiten auf dem Feld zählen nicht, ebenso wenig Mana aus Kreaturen oder Treasure.':
        "At the top of the page's game view and in the Trick Warner (separate window) are all instants and cards with flash of the set that the opponent could cast right now with his untapped lands, with cost, your category and removal points. Activatable abilities on the battlefield do not count, nor does mana from creatures or Treasure.",
    'Die Liste ändert sich mit jedem Land, das er spielt oder tappt.':
        'The list changes with every land he plays or taps.',
    'Fährt die Maus über einen Trick, erscheint ein kleines Fenster mit dem Kartentext (Kosten, Typzeile, Stärke/Widerstand, Text und Removal-Punkte, englisch von Scryfall); auf der Seite steht derselbe Text als Hinweis an der Karte.':
        'When the mouse moves over a trick, a small window with the card text appears (cost, type line, power/toughness, text and removal points, in English from Scryfall); on the page the same text appears as a hint on the card.',
    'Gegnerfarben: Hat der Gegner Zauber in mindestens zwei Farben offen gezeigt, kommen nur Tricks in diesen Farben und in den Farben seiner Standardländer in Frage (ein Tri-Land zeigt sonst Farben, die er gar nicht spielt). Farblose Tricks gehen immer.':
        "Opponent colors: If the opponent has shown spells in at least two colors, only tricks in these colors and in the colors of his basic lands are considered (a tri-land otherwise shows colors he doesn't play at all). Colorless tricks always apply.",
    'Die Karten des Sets kommen von Scryfall (einmal geladen, dann aus <code>scryfall_set_cache.json</code>). Minimiert zeigt das Seitenfenster „Tricks 3 · offen 2“.':
        "The set's cards come from Scryfall (loaded once, then from <code>scryfall_set_cache.json</code>). Minimized, the overlay shows “Tricks 3 · open 2”.",
    'Im Spiel: Ziehchancen':
        'In game: draw chances',
    'Während eines Spiels zeigen Seite und Seitenfenster statt des Packs die eigene Bibliothek. Arena meldet beim Spielstart das Deck des Spiels und danach laufend, wo die eigenen Karten liegen; Bibliothek = Deck minus Hand, Spielfeld, Friedhof, Exil und Stapel. Das gilt für jedes Spiel, nicht nur im Draft.':
        "During a game the page and the overlay show your own library instead of the pack. Arena reports the game's deck at game start and then continuously where your cards are; library = deck minus hand, battlefield, graveyard, exile and stack. This applies to every game, not only in the draft.",
    'Je Gruppe (Land, Kreatur, Removal, Quellen je Farbe) und je Karte: wie viele noch drin sind, die Chance für die nächste Karte und für mindestens eine unter den nächsten 3 Karten (hypergeometrisch: 1 − C(L − n, k) / C(L, k) bei L Karten in der Bibliothek, n passenden, k gezogenen).':
        'Per group (land, creature, removal, sources per color) and per card: how many are still in, the chance for the next card and for at least one among the next 3 cards (hypergeometric: 1 − C(L − n, k) / C(L, k) with L cards in the library, n matching, k drawn).',
    'Removal: übrige Karten und Punkte im Vergleich zum ganzen Deck.':
        'Removal: remaining cards and points compared to the whole deck.',
    '<b>Spielbar</b> (oben in der Liste): Karten der Bibliothek, die du mit deinen Ländern auf dem Spielfeld bezahlen kannst (das Mana dieses Zuges, getappt oder nicht; Hybrid und Phyrexian werden berücksichtigt, X zählt 0). Länder selbst und andere Manaquellen (Kreaturen, Treasure) zählen nicht. Spielbare Karten tragen einen Haken.':
        "<b>Castable</b> (at the top of the list): cards in the library that you can pay for with your lands on the battlefield (this turn's mana, tapped or not; hybrid and Phyrexian are taken into account, X counts as 0). Lands themselves and other mana sources (creatures, Treasure) do not count. Castable cards carry a check mark.",
    'Im Spiel ist der Knopf „Deck + Sideboard übernehmen“ ausgeblendet.':
        'In game, the “Use deck + sideboard” button is hidden.',
    'Das Seitenfenster lässt sich mit dem Knopf oben rechts (oder einem Doppelklick) zu einem kleinen Kasten minimieren: im Spiel nur die Chancen auf Removal, Land und Kreatur für die nächste Karte, im Draft Pick, Archetyp und beste Karte. Noch einmal klicken klappt es in der alten Größe wieder auf.':
        'The overlay can be minimized to a small box with the button at the top right (or a double click): in game only the chances for removal, land and creature for the next card, in the draft pick, archetype and best card. Clicking once more expands it to the old size.',
    'Nach dem Draft und zwischen den Spielen zeigt das Seitenfenster statt „Pick 43“ eine kurze <b>Deck-Übersicht</b>: Archetyp und Bilanz (Siege–Niederlagen), Karten, Länder und Zauber mit Ø Manawert, Mana-Kurve (als Balken, der höchste gelb), Kreaturen, Removal (Karten und Punkte), Kartenfluss, Zauber je Farbe (als Balken in den Manafarben) und die Bomben (eigene Bewertung Matchwinner; Splashworthy und Must-Play zählen nicht). Grundlage ist das in Arena abgegebene Hauptdeck, vorher alle Picks. Minimiert: Bilanz, Kreaturen und Removal.':
        'After the draft and between games the overlay shows a short <b>deck overview</b> instead of “Pick 43”: archetype and record (wins–losses), cards, lands and spells with avg mana value, mana curve (as bars, the highest in yellow), creatures, removal (cards and points), card flow, spells per color (as bars in the mana colors) and the bombs (your own rating Matchwinner; Splashworthy and Must-Play do not count). It is based on the main deck submitted in Arena, before that all picks. Minimized: record, creatures and removal.',
    'Karten, die per Mulligan oder Scry unter die Bibliothek gelegt wurden, zählen wie alle anderen (ihre Lage ist nicht bekannt). Passt die Rechnung nicht genau zur Bibliothek (z. B. durch Token oder Sideboard), steht ein Hinweis dabei.':
        'Cards put under the library by mulligan or scry count like all others (their position is not known). If the calculation does not exactly match the library (e.g. due to tokens or sideboard), a note is shown.',
    'Deck nach dem Draft übernehmen':
        'Apply deck after the draft',
    'Nach dem Draft (42 Picks oder sobald Arena ein Deck meldet) erscheint oben im Live-Bereich und im Seitenfenster der Knopf <b>Deck + Sideboard übernehmen</b>. In Arena selbst lässt sich kein Knopf einblenden.':
        'After the draft (42 picks or as soon as Arena reports a deck) the button <b>Use deck + sideboard</b> appears at the top of the live area and in the overlay. No button can be shown inside Arena itself.',
    'Klickbar wird er, sobald du in Arena den Deckbau mit „Fertig“ abschließt: Arena schreibt dann Deck und Sideboard ins Protokoll. Ein Klick schreibt beides in die Kartenpool-Datei (Abschnitte Deck und Sideboard, Standardländer im Deck); der Drafthelper lädt neu, Deckkarten und Länder stehen auf Core, das Sideboard auf Aus.':
        'It becomes clickable as soon as you finish deck building in Arena with “Done”: Arena then writes deck and sideboard to the log. One click writes both into the card pool file (Deck and Sideboard sections, basic lands in the deck); the Draft Helper reloads, deck cards and lands are on Core, the sideboard on Off.',
    'Ein Deck zählt nur, wenn mindestens 80 % seiner Karten (ohne Standardländer) aus deinen Picks stammen; ein altes Deck desselben Events bleibt so außen vor. Die übernommene Datei wird nicht mehr mit der einfachen Pick-Liste überschrieben, auch nicht nach einem Neustart; erst ein neuer Draft beginnt sie neu.':
        'A deck only counts if at least 80% of its cards (excluding basic lands) come from your picks; this leaves out an old deck of the same event. The applied file is no longer overwritten with the simple pick list, not even after a restart; only a new draft starts it anew.',
    'Archetyp erkennen':
        'Recognize archetype',
    'Jeder Pick zählt mit dem Gewicht seiner Kategorie (Matchwinner 3, Splashworthy und MustPlay 2, ohne Kategorie und Filler 1, NeverPlay 0) für jeden Archetyp, in dessen Farben alle seine Farben liegen, und noch einmal für jeden Archetyp, dem er zugeordnet ist. Farblose Karten zählen nur über die Zuordnung, Länder gar nicht.':
        'Each pick counts with the weight of its category (Matchwinner 3, Splashworthy and MustPlay 2, no category and Filler 1, NeverPlay 0) for every archetype in whose colors all of its colors lie, and once more for every archetype it is assigned to. Colorless cards count only via the assignment, lands not at all.',
    'Erkannt ist der Archetyp mit den meisten Punkten, wenn er mindestens 3 Punkte hat und allein vorn liegt; sonst ist er noch offen und es wird nichts hervorgehoben.':
        'The archetype with the most points is recognized if it has at least 3 points and is alone in front; otherwise it is still open and nothing is highlighted.',
    'Mit der Auswahl <b>Archetyp</b> lässt er sich auch selbst festlegen (zurück mit „Automatisch“). Dazu stehen die Hinweise zum Archetyp und die Punkte der führenden Archetypen.':
        'With the <b>Archetype</b> selection it can also be set yourself (back with “Automatic”). The archetype hints and the points of the leading archetypes are shown with it.',
    'Seitenfenster':
        'Overlay',
    'Startet mit dem Live-Draft (abschalten mit <code>--kein-overlay</code>): ein kleines Fenster, das immer im Vordergrund bleibt, mit Pick-Nummer, Archetyp und der Rangliste des Packs (◆ bester Archetyp der Karte, ● dem Archetyp zugeordnet, ○ Farben passen, dazu Farben, Kategorie und zugeordnete Archetypen).':
        'Starts with the live draft (switch off with <code>--kein-overlay</code>): a small window that always stays in the foreground, with pick number, archetype and the pack ranking (◆ best archetype of the card, ● assigned to the archetype, ○ colors fit, plus colors, category and assigned archetypes).',
    'Arena dafür im Fenster oder im randlosen Vollbild spielen; über exklusivem Vollbild liegt kein Fenster. Das Fenster lässt sich verschieben und schließt sich, wenn der Drafthelper beendet wird. Einzeln: <code>python mtg_sim.py --overlay http://127.0.0.1:8765/</code>.':
        'Play Arena in a window or in borderless full screen for this; no window appears over exclusive full screen. The window can be moved and closes when the Draft Helper is quit. Standalone: <code>python mtg_sim.py --overlay http://127.0.0.1:8765/</code>.',
    'Am linken Bildschirmrand steht das <b>Steuerfenster</b>: Häkchen schalten das Seitenfenster (Draft / Bibliothek) und den <b>Trick-Warner</b> an und ab. Der Trick-Warner ist ein eigenes Fenster links unter dem Steuerfenster und erscheint nur im Spiel. Schließt man das Steuerfenster, sind alle Fenster zu.':
        'At the left screen edge is the <b>control window</b>: check boxes switch the overlay (draft / library) and the <b>Trick Warner</b> on and off. The Trick Warner is a separate window at the left below the control window and appears only in game. If you close the control window, all windows are closed.',
    'Draft-Statistik':
        'Draft statistics',
    'Solange der Live-Draft läuft, sammelt er je Draft die Picks, das abgegebene Deck und die Ergebnisse der Matches (je Game und fürs Match) in <code>draftstatistik.json</code> im Projektordner (nicht im Git, anderer Name mit <code>--statistik DATEI</code>). Gezählt werden nur Draft- und Sealed-Events.':
        'While the live draft runs, it collects per draft the picks, the submitted deck and the results of the matches (per game and per match) in <code>draftstatistik.json</code> in the project folder (not in Git, another name with <code>--statistik FILE</code>). Only draft and sealed events are counted.',
    'Matches und Decks gehören zum letzten Draft desselben Events. Wurde der Draft nicht mitgelesen, zählt das Event trotzdem, nur ohne Picks. Beim Start wird auch die vorherige Protokolldatei (<code>Player-prev.log</code>) nachgelesen. Dasselbe Protokoll zweimal gelesen zählt nicht doppelt.':
        'Matches and decks belong to the last draft of the same event. If the draft was not read along, the event still counts, just without picks. At startup the previous log file (<code>Player-prev.log</code>) is read back as well. Reading the same log twice does not count twice.',
    'An jeder Karte (Pool, Pack, Set-Ansicht) und im Seitenfenster: wie oft gedraftet, in wie vielen Decks, und die Siegquote der Games mit der Karte im Hauptdeck. Unter 20 Games ist sie grau: nur ein Hinweis.':
        'On every card (pool, pack, set view) and in the overlay: how often drafted, in how many decks, and the win rate of the games with the card in the main deck. Under 20 games it is gray: only a hint.',
    'Der Bericht zeigt die Zahlen der Deckkarten im Abschnitt „Deck“ (Kasten „Deine Draft-Statistik“).':
        'The report shows the numbers for the deck cards in the “Deck” section (box “Your draft statistics”).',
    'Pick Two und Drafts mit Menschen: Beim Draften nennt das Protokoll nur eine Draft-Kennung, kein Event. Das Set kommt dann aus den Karten; das erste Deck des Events, dessen Karten zu mindestens 80 % aus den Picks stammen, gehört zu diesem Draft und nennt das Event. Mit <code>python mtg_sim.py --statistik-neu</code> wird die Statistik aus <code>Player-prev.log</code> und <code>Player.log</code> neu aufgebaut (alte Datei als <code>draftstatistik.backup.json</code>).':
        'Pick Two and drafts with humans: While drafting, the log names only a draft ID, no event. The set then comes from the cards; the first deck of the event whose cards come at least 80% from the picks belongs to this draft and names the event. <code>python mtg_sim.py --statistik-neu</code> rebuilds the statistics from <code>Player-prev.log</code> and <code>Player.log</code> (old file as <code>draftstatistik.backup.json</code>).',
    'Gegnerdecks aus 4-Sieg-Decks':
        'Opponent decks from 4-win decks',
        'Holt ein mitgelesener Draft die höchste Zahl an Match-Siegen seines Formats (Pick Two 4, Traditional 3, sonst 7, z. B. Quick und Premier Draft), speichert der Live-Draft das Deck dieses Matches (mit Sideboard) einmal als Gegnerdeck: <code>enemydecks/drafted_&lt;SET&gt;_&lt;N&gt;wins_&lt;Farben&gt;_&lt;JJJJ-MM-TT&gt;_&lt;hhmm&gt;.txt</code>, z. B. <code>drafted_TRK_4wins_…</code> bei Pick Two; Zeit des letzten Siegs aus dem Protokoll.':
        "When a draft that was read along reaches the highest number of match wins of its format (Pick Two 4, Traditional 3, otherwise 7, e.g. Quick and Premier Draft), the live draft saves that match's deck (with sideboard) once as an opponent deck: <code>enemydecks/drafted_&lt;SET&gt;_&lt;N&gt;wins_&lt;colors&gt;_&lt;YYYY-MM-DD&gt;_&lt;hhmm&gt;.txt</code>, e.g. <code>drafted_TRK_4wins_…</code> for Pick Two; time of the last win from the log.",
    'Farben: aus den Nicht-Land-Karten des Hauptdecks, die mit den meisten Karten zuerst (Gleichstand: WUBRG). Eine Farbe mit höchstens 2 Karten wird als Splash angehängt, z. B. <code>redwhitesplashblue</code>.':
        'Colors: from the nonland cards of the main deck, the one with the most cards first (tie: WUBRG). A color with at most 2 cards is appended as a splash, e.g. <code>redwhitesplashblue</code>.',
    'Das Seitenfenster feiert das kurz mit Pokal und Konfetti (Klick schließt): Das Deck ist in die „Hall of Fame“ der Gegnerdecks aufgenommen.':
        'The overlay celebrates this briefly with a trophy and confetti (click closes): The deck has been added to the “Hall of Fame” of opponent decks.',
    'Eine vorhandene Datei wird nie überschrieben. Seite und Seitenfenster melden „Gegnerdeck gespeichert“, die Gegnerdeck-Auswahl im Drafthelper hat es sofort. Beim Neuaufbau der Statistik (--statistik-neu) wird nichts gespeichert.':
        'An existing file is never overwritten. Page and overlay report “Opponent deck saved”, the opponent deck selection in the Draft Helper has it immediately. When the statistics are rebuilt (--statistik-neu), nothing is saved.',
    'Setauswertung':
        'Set report',
    'Menüpunkt <b>4</b> in <code>draftgott.bat</code> oder <code>python mtg_sim.py --setauswertung [SET]</code>: schreibt <code>setauswertung_&lt;set&gt;.html</code> und öffnet sie (ohne SET das Set mit den meisten Drafts).':
        'Menu item <b>4</b> in <code>draftgott.bat</code> or <code>python mtg_sim.py --setauswertung [SET]</code>: writes <code>setauswertung_&lt;set&gt;.html</code> and opens it (without SET the set with the most drafts).',
    'Inhalt: Überblick (Drafts, Matches und Games mit Bilanz), Archetypen (je Draft erkannt wie im Live-Draft, aus dem Hauptdeck), beste und schwächste Karten (ab 10 Games), alle Karten als sortierbare Tabelle (gedraftet, Ø Pick-Nummer im Pack, im Deck, Games, Siegquote, Matches), Bewertung gegen Ergebnis je Kategorie und die Liste der Drafts.':
        'Contents: overview (drafts, matches and games with record), archetypes (recognized per draft as in the live draft, from the main deck), best and weakest cards (from 10 games), all cards as a sortable table (drafted, avg pick number in pack, in deck, games, win rate, matches), rating versus result per category and the list of drafts.',
    'Zuordnung':
        'Assignment',
    '<b>Core</b> – in beiden Varianten, <b>Splash</b> – nur in der Variante Splash, <b>NoSplash</b> – nur in der Variante NoSplash, <b>Aus</b> – in keiner Variante.':
        '<b>Core</b> – in both variants, <b>Splash</b> – only in the Splash variant, <b>NoSplash</b> – only in the NoSplash variant, <b>Off</b> – in no variant.',
    'Jede Kopie einer Karte wird einzeln zugeordnet (z. B. 2 von 3 Kopien in Core).':
        'Each copy of a card is assigned individually (e.g. 2 of 3 copies in Core).',
    'Standardländer werden oben als Menge je Gruppe eingestellt, auch Länder, die nicht im Pool sind. Startwert: die Länder aus dem Deck der Pool-Datei als Core.':
        'Basic lands are set at the top as a quantity per group, including lands that are not in the pool. Starting value: the lands from the deck of the pool file as Core.',
    'Nicht-Standardländer stehen direkt darunter in einem eigenen Bereich (aus Deck und Sideboard der Datei) und werden wie andere Karten je Kopie zugeordnet.':
        'Non-basic lands are directly below in their own area (from deck and sideboard of the file) and are assigned per copy like other cards.',
    'Der Stand wird im Browser gemerkt, und zwar je Inhalt der Pool-Datei: ein anderer Pool startet neu.':
        'The state is remembered in the browser, per content of the pool file: a different pool starts fresh.',
    'Archetypen des Sets':
        'Archetypes of the set',
    'Sind für das Set des Pools Archetypen hinterlegt (derzeit TRK und FRA), stehen sie über den Karten: je Farbpaar der englische Titel und Hinweise zum Deckbau. Das Set ist das häufigste Set der Nicht-Länder im Pool.':
        "If archetypes are stored for the pool's set (currently TRK and FRA), they are shown above the cards: per color pair the English title and deck-building hints. The set is the most common set of the nonlands in the pool.",
    'Hervorgehoben ist der Archetyp der Core-Farben: die zwei Farben mit den meisten Core-Karten (Kopien, ohne Länder, mehrfarbige zählen für jede ihrer Farben). Der Bericht zeigt im Abschnitt „Deck“ denselben Archetyp, dort nach den Nicht-Länder-Karten des Decks.':
        'Highlighted is the archetype of the Core colors: the two colors with the most Core cards (copies, without lands, multicolor cards count for each of their colors). In the “Deck” section the report shows the same archetype, there by the nonland cards of the deck.',
    'Der Kasten lässt sich zuklappen; der Browser merkt sich das. Neue Sets werden in <code>components/archetypes.py</code> ergänzt.':
        'The box can be collapsed; the browser remembers this. New sets are added in <code>components/archetypes.py</code>.',
    'Archetyp-Zuordnung je Karte':
        'Archetype assignment per card',
    'Unter jeder Karte eines Sets mit Archetypen stehen Knöpfe mit den Farbpaaren der Archetypen (Mauszeiger darüber: Name). Ein Klick ordnet die Karte dem Archetyp zu oder nimmt die Zuordnung zurück; eine Karte kann zu mehreren Archetypen passen.':
        'Under each card of a set with archetypes are buttons with the color pairs of the archetypes (hover: name). A click assigns the card to the archetype or withdraws the assignment; a card can fit several archetypes.',
    'Die Zuordnung gilt je Kartenname für jeden Pool und den Live-Draft und steht in <code>kartenarchetypen.json</code> im Projektordner (nicht im Git, anderer Name mit <code>--archetypen DATEI</code>).':
        'The assignment applies per card name for every pool and the live draft and is stored in <code>kartenarchetypen.json</code> in the project folder (not in Git, another name with <code>--archetypen FILE</code>).',
    '<b>Set-Karten bewerten</b> (oben) lädt alle Karten eines Sets von Scryfall: Kategorie und Archetypen lassen sich so schon vor dem Draft festlegen. Filter: ohne Kategorie, ohne Archetyp, je Farbe.':
        '<b>Rate set cards</b> (at the top) loads all cards of a set from Scryfall: category and archetypes can thus be set before the draft. Filters: no category, no archetype, per color.',
    'Erkannter Archetyp: aus den Core-Karten wie im Live-Draft (siehe dort). Im Archetyp-Kasten steht je Archetyp, wie viele Core-Karten ihm zugeordnet sind; der erkannte ist grün umrandet, seine Karten tragen die Plakette „Archetyp“. Der Bericht zeigt dieselbe Zählung und Erkennung im Archetyp-Kasten.':
        'Recognized archetype: from the Core cards as in the live draft (see there). The archetype box shows per archetype how many Core cards are assigned to it; the recognized one has a green outline, its cards carry the “Archetype” badge. The report shows the same count and recognition in the archetype box.',
    'Kategorien':
        'Categories',
    '<b>♛ Matchwinner</b> – die Bombe: entscheidet ein Match allein und kommt immer rein, notfalls als Splash (beim Deckbau wie Splashworthy, im Draft und in der Deck-Übersicht ganz oben).':
        '<b>♛ Matchwinner</b> – the bomb: decides a match on its own and always goes in, if necessary as a splash (in deck building like Splashworthy, at the very top in the draft and in the deck overview).',
    '<b>★ Splashworthy</b> – entscheidet Spiele allein, soll auf jeden Fall rein, auch wenn wir die Farbe nicht spielen.':
        "<b>★ Splashworthy</b> – decides games on its own, should go in in any case, even if we don't play the color.",
    '<b>MustPlay</b> – wird auf jeden Fall gespielt, wenn wir diese Farbe spielen.':
        '<b>MustPlay</b> – is played in any case if we play this color.',
    '<b>Filler</b> – füllt das Deck auf, wenn wir die Farbe spielen und nicht splashen.':
        "<b>Filler</b> – fills up the deck if we play the color and don't splash.",
    '<b>NeverPlay</b> – zu schlecht oder zu situativ.':
        '<b>NeverPlay</b> – too bad or too situational.',
    'Eine Kategorie gilt für alle Kopien einer Karte und beeinflusst die Simulation nicht; ♛ Matchwinner, ★ Splashworthy und MustPlay erscheinen im Bericht in einem eigenen Abschnitt („Great in this deck“).':
        'A category applies to all copies of a card and does not affect the simulation; ♛ Matchwinner, ★ Splashworthy and MustPlay appear in the report in their own section (“Great in this deck”).',
    'Zuordnung nach Kategorien setzen':
        'Set assignment by categories',
    'MustPlay → Core, Matchwinner und Splashworthy → Splash, NeverPlay → Aus, Karten ohne Kategorie bleiben unverändert.':
        'MustPlay → Core, Matchwinner and Splashworthy → Splash, NeverPlay → Off, cards without a category stay unchanged.',
    'Filler füllt auf die Zielgröße auf (alle Länder zählen mit): zuerst Core, damit beide Varianten gleich groß werden, dann die NoSplash-Gruppe als Ersatz für die Splash-Karten; übrige Filler → Aus.':
        'Filler fills up to the target size (all lands count): first Core so that both variants become equally large, then the NoSplash group as a replacement for the splash cards; remaining Filler → Off.',
    'Reihenfolge der Filler: nach der gewählten Sortierung, dann Farben, die schon im Deck sind, dann Manawert aufsteigend. „↶ Rückgängig“ stellt den Stand davor wieder her.':
        'Order of the Filler: by the chosen sorting, then colors already in the deck, then mana value ascending. “↶ Undo” restores the previous state.',
    'Länder empfehlen':
        'Recommend lands',
    'Nimmt die aktuelle Zuordnung (Core, Splash, NoSplash) und setzt die Standardländer je Gruppe sowie die Zuordnung der Nicht-Standardländer neu. Die Zauber bleiben unverändert; „↶ Rückgängig“ stellt den Stand davor wieder her.':
        'Takes the current assignment (Core, Splash, NoSplash) and resets the basic lands per group as well as the assignment of the non-basic lands. The spells stay unchanged; “↶ Undo” restores the previous state.',
    'Farben einer Variante: jede Farbe, deren Symbol auf mindestens einer Nichtland-Karte steht (Hybrid zählt für beide Farben).':
        'Colors of a variant: every color whose symbol is on at least one nonland card (hybrid counts for both colors).',
    'Nicht-Standardland: passt, wenn alle seine Farben in der Variante vorkommen (ein R/G-Land passt zu R/G/W, aber nicht zu G/W). Passt es zu beiden Varianten → Core, nur zu einer → Splash bzw. NoSplash, sonst Aus. Passende Länder werden immer genommen, auch wenn sie getappt kommen.':
        'Non-basic land: fits if all its colors occur in the variant (an R/G land fits R/G/W, but not G/W). If it fits both variants → Core, only one → Splash or NoSplash, otherwise Off. Fitting lands are always taken, even if they enter tapped.',
    'Zahl der Länder je Variante: Zielgröße minus Zauber, begrenzt auf die Faustregel (40 Karten: 15 bis 17). Nicht-Standardländer ersetzen Standardländer.':
        'Number of lands per variant: target size minus spells, limited to the rule of thumb (40 cards: 15 to 17). Non-basic lands replace basic lands.',
    'Verteilung: Jede Farbe, die eine Karte zwingend verlangt, bekommt mindestens 3 Quellen (Nicht-Standardländer zählen mit). Die übrigen Standardländer gehen einzeln an die Farbe, die die Summe der Chancen „pünktlich“ aller Karten am stärksten erhöht (siehe Farbverteilung im Bericht).':
        'Distribution: every color that a card strictly requires gets at least 3 sources (non-basic lands count). The remaining basic lands go one by one to the color that raises the sum of the “on time” chances of all cards the most (see color distribution in the report).',
    'Core enthält die Standardländer, die beide Varianten brauchen, der Rest steht in Splash bzw. NoSplash.':
        'Core contains the basic lands both variants need, the rest is in Splash or NoSplash.',
    'Die Meldung zeigt je Variante die Länder und je Farbe Quellen, Karten, Ø pünktlich und die knappste Karte.':
        'The message shows per variant the lands and per color sources, cards, avg on time and the tightest card.',
    'Deckvorschlag':
        'Deck suggestion',
    'Ein eigenes Deck aus den Kategorien; die Zuordnung bleibt unverändert.':
        'A deck of its own from the categories; the assignment stays unchanged.',
    'MustPlay und Filler nur, wenn alle Farben der Karte gewählt sind (Farblos immer); Matchwinner und Splashworthy immer, außerhalb der gewählten Farben als Splash; NeverPlay und Karten ohne Kategorie nicht.':
        'MustPlay and Filler only if all colors of the card are chosen (colorless always); Matchwinner and Splashworthy always, outside the chosen colors as a splash; NeverPlay and cards without a category not.',
    'Länder: Nicht-Standardländer zählen als Länder; Standardländer werden auf die Faustregel ergänzt (40 Karten: 17 Länder, Bereich 15 bis 17; 60 Karten: 22, Bereich 20 bis 24; dazwischen linear) und nach den Farbsymbolen verteilt, je Splash-Farbe bis zu 3. Bei Abweichung erscheint ein Hinweis.':
        'Lands: non-basic lands count as lands; basic lands are added up to the rule of thumb (40 cards: 17 lands, range 15 to 17; 60 cards: 22, range 20 to 24; linear in between) and distributed by color symbols, up to 3 per splash color. A note appears on deviation.',
    'Mit „mitsimulieren“ wird der Vorschlag als weitere Variante verglichen; der Export zeigt ihn als dritte Spalte.':
        'With “simulate too” the suggestion is compared as a further variant; the export shows it as a third column.',
    'Übersicht links':
        'Overview on the left',
    'Übersicht nach Farbe: Pool, Zuordnung und Kategorien je Farbe (Kopien, ohne Standardländer).':
        'Overview by color: pool, assignment and categories per color (copies, without basic lands).',
    'Mana-Kurve (Splash gegen NoSplash), Mana-Kurve nach Farben (wie im Bericht, Abschnitt Deck) und Kartentypen je Variante mit Empower Jace und Kartenfluss (gezählt wie im Bericht).':
        'Mana curve (Splash vs NoSplash), mana curve by color (as in the report, Deck section) and card types per variant with Empower Jace and card flow (counted as in the report).',
    'Farben und Quellen: je Farbe Symbole, Karten, Quellen (Standardländer der Variante und zugeordnete Nicht-Standardländer, NS) und Ø pünktlich mit Ampel, gerechnet wie die Farbverteilung im Bericht. Der Block aktualisiert sich bei jeder Änderung; mit der Maus über Ø pünktlich steht die knappste Karte.':
        'Colors and sources: per color symbols, cards, sources (basic lands of the variant and assigned non-basic lands, NS) and avg on time with traffic light, calculated like the color distribution in the report. The block updates with every change; hover over avg on time to see the tightest card.',
    'Manasymbole: die Originalsymbole von Scryfall (einmal geladen und in scryfall_symbols.json gespeichert); ohne sie erscheinen einfache Symbole.':
        'Mana symbols: the original symbols from Scryfall (loaded once and saved in scryfall_symbols.json); without them simple symbols appear.',
    'Suche, Sortierung und Filter ändern nur die Anzeige, nicht die Zuordnung.':
        'Search, sorting and filters change only the display, not the assignment.',
    'Simulieren und Export':
        'Simulate and export',
    '„Simulieren“ vergleicht Core + Splash mit Core + NoSplash (und optional den Deckvorschlag); der Bericht erscheint auf der Seite und wird zusätzlich als Datei gespeichert.':
        '“Simulate” compares Core + Splash with Core + NoSplash (and optionally the deck suggestion); the report appears on the page and is additionally saved as a file.',
    '„Kampf ohne Goldfish“ (neben „Simulieren“, nur wenn Gegnerdecks im Ordner enemydecks liegen): dieselben Varianten kämpfen direkt gegen das gewählte Gegnerdeck, ohne vorher den Goldfish zu simulieren. Es zählt die aktuelle Zuordnung, nicht der letzte Bericht; der Kampfbericht wird auch als Datei gespeichert.':
        '“Battle without Goldfish” (next to “Simulate”, only if opponent decks are in the enemydecks folder): the same variants fight directly against the chosen opponent deck, without simulating the goldfish first. The current assignment counts, not the last report; the battle report is also saved as a file.',
    '„Deckliste exportieren“: jede Variante im Importformat von MTG Arena und MTGO (Deck und Sideboard).':
        '“Export deck list”: every variant in the import format of MTG Arena and MTGO (deck and sideboard).',
    'So funktioniert es':
        'How it works',
    'Wie die Simulation rechnet und wie die Zahlen zu lesen sind, Abschnitt für Abschnitt wie im Bericht. Die Werte deines Laufs (Spiele, Runden, Schaden, Flood …) stehen oben im Bericht; hier sind die Regeln allgemein mit ihren Parametern und Standardwerten beschrieben.':
        'How the simulation calculates and how to read the numbers, section by section as in the report. The values of your run (games, turns, damage, flood …) are at the top of the report; here the rules are described in general with their parameters and default values.',
    'So funktioniert es – MTG Simulation':
        'How it works – MTG Simulation',
    'Regeln und Lesehilfen für Bericht und Drafthelper':
        'Rules and reading aids for the report and the Draft Helper',
    'Deck-Vergleich':
        'Deck comparison',
    'Auf einen Blick':
        'At a glance',
    'Deck':
        'Deck',
    'Removal':
        'Removal',
    'Synergie':
        'Synergy',
    'Friedhof':
        'Graveyard',
    'Great in this deck!':
        'Great in this deck!',
    'Modell-Abdeckung':
        'Model coverage',
    'Mulligan':
        'Mulligan',
    'Jace & Planeswalker':
        'Jace & Planeswalker',
    'Zauber pro Runde':
        'Spells per turn',
    'Kreaturen nach Runde X':
        'Creatures after turn X',
    'Mana Screw & Flood':
        'Mana Screw & Flood',
    'Farbverfügbarkeit':
        'Color availability',
    'Splash-Karten':
        'Splash cards',
    'Curve-Auslastung':
        'Curve usage',
    'Schaden durch Kreaturen':
        'Damage from creatures',
    'Schnellster Lethal':
        'Fastest lethal',
    'Landcycling':
        'Landcycling',
    'Draw-Zauber':
        'Draw spells',
    'Surveil durch Karten':
        'Surveil from cards',
    'Prepared':
        'Prepared',
    'Ramp':
        'Ramp',
    'Tempo':
        'Tempo',
    'Spiellogik':
        'Game logic',
    'Modellannahmen':
        'Model assumptions',
    'Drafthelper':
        'Draft Helper',
    'Live-Draft':
        'Live draft',
    'Der Jace-Token startet mit 0 Loyalty und hat die Fähigkeiten −1: Surveil 1 und −3: eine Karte ziehen. Empower legt Loyalty auf den Token, ohne Token wird ein neuer erstellt. Bei 0 Loyalty verschwindet er, der nächste Empower erstellt einen neuen.':
        'The Jace token starts with 0 loyalty and has the abilities −1: surveil 1 and −3: draw a card. Empower adds loyalty to the token; without a token a new one is created. At 0 loyalty it disappears, the next Empower creates a new one.',
    'Jace wird höchstens einmal pro Runde aktiviert und nur, wenn die Bibliothek nicht leer ist. Zu Rundenbeginn mit Loyalty aus früheren Runden nur zum Ziehen (ab 3 Loyalty, die Karte kann dann noch gespielt werden). Nach dem Zaubern: ab 3 Loyalty ziehen, sonst −1: Surveil 1, auch wenn er dadurch auf 0 sinkt und verschwindet.':
        'Jace is activated at most once per turn and only if the library is not empty. At the start of the turn with loyalty from earlier turns only to draw (from 3 loyalty; the card can still be cast then). After casting: from 3 loyalty draw, otherwise −1: surveil 1, even if it drops to 0 and disappears.',
    'Surveil: Ein Land bleibt oben, wenn die teuerste Karte auf der Hand noch nicht gespielt werden kann, weil Länder fehlen (Länder auf dem Feld und auf der Hand weniger als ihr Manawert). Sonst kommt das Land in den Friedhof. Zauber bleiben immer oben.':
        'Surveil: A land stays on top if the most expensive card in hand cannot be cast yet because lands are missing (lands on the battlefield and in hand fewer than its mana value). Otherwise the land goes to the graveyard. Spells always stay on top.',
    'Einmalig: Zauber (Instant, Sorcery) und „beim Betreten“-Effekte wirken sofort beim Ausspielen, auch bei Ländern.':
        'One-time: spells (instant, sorcery) and “when it enters” effects take effect immediately when cast, also for lands.',
    'Wiederkehrend, modelliert: „whenever you cast …“ (alle, Kreatur, Nichtkreatur, Instant oder Sorcery), „whenever … enters“ (Kreatur, Land, Permanent), „whenever … attacks“ (ab der Runde nach dem Ausspielen, mit Haste sofort, nie bei Defender) und „at the beginning of …“ (einmal pro Runde ab der Folgerunde). Karten reagieren nur auf Ereignisse, nachdem sie im Spiel sind.':
        'Recurring, modeled: “whenever you cast …” (all, creature, noncreature, instant or sorcery), “whenever … enters” (creature, land, permanent), “whenever … attacks” (from the turn after casting, immediately with haste, never with defender) and “at the beginning of …” (once per turn from the following turn). Cards react to events only after they are in play.',
    'Bezahlbare Fähigkeiten werden mit dem Mana benutzt, das nach dem Zaubern übrig ist, so oft es reicht (höchstens 10-mal pro Runde). Mit {T} im Preis nur einmal pro Runde und bei Kreaturen erst ab der Folgerunde. Exil aus dem Friedhof (Campus Crier) ist modelliert, andere Kosten (Opfern, Ablegen) nicht.':
        'Payable abilities are used with the mana left after casting, as often as it suffices (at most 10 times per turn). With {T} in the cost only once per turn and for creatures only from the following turn. Exile from the graveyard (Campus Crier) is modeled, other costs (sacrificing, discarding) are not.',
    'Modale Zauber zählen ihren Empower immer. Es wird nur die Vorderseite einer Karte simuliert, die Zählung berücksichtigt alle Seiten.':
        'Modal spells always count their Empower. Only the front side of a card is simulated; the count takes all sides into account.',
    'Variables Empower (X): beim Angriff X = Zahl der eigenen Kreaturen (Repurposed Enforcer), Jace, Reality Sculptor nach den eigenen Islands; im Kampfmodell zusätzlich exilierte Kreaturen (Overwrite the Multiverse) und überschüssiger Schaden (Violent Echoes). Andere X zählen als 0 und stehen unten.':
        'Variable Empower (X): on attack X = number of your own creatures (Repurposed Enforcer), Jace, Reality Sculptor by your own Islands; in the battle model additionally exiled creatures (Overwrite the Multiverse) and excess damage (Violent Echoes). Other X count as 0 and are listed below.',
    'Die Einordnung stammt aus dem Kartentext von Scryfall und ist unten zur Kontrolle neben jeder Karte aufgeführt. Echte Planeswalker spielen ihre Loyalty-Fähigkeiten im Goldfish (ohne Gegner) und im Kampfmodell.':
        'The classification comes from the Scryfall card text and is listed next to each card below for checking. Real planeswalkers play their loyalty abilities in the goldfish (no opponent) and in the battle model.',
    'Zurück zum Bericht':
        'Back to the report',
    'Zurück zum Drafthelper':
        'Back to the Draft Helper',
    'Lethal / Schaden':
        'Lethal / damage',
    'Mana und Zauber pro Runde':
        'Mana and spells per turn',
    'Kartenfluss (Länder, Screw/Flood)':
        'Card flow (lands, screw/flood)',
    'keine (Gegner ist nicht Teil des Modells)':
        'none (the opponent is not part of the model)',
    'unklar':
        'unclear',
    'Gegnerdecks aus Decks mit Höchststand': 'Opponent decks from decks with a perfect run',
    'Das <b>Karten-Overlay</b> legt beim Picken die Zahlen direkt auf die Karten im Arena-Fenster: oben links der Rang im Pack, oben rechts die Bewertung, unten Punkte, Farben des besten Archetyps, Passung (✓ dein Archetyp, ≈ nahe dran, ○ Farben passen, – fremde Farben), Removal, Kartenfluss, Synergie, Kreatur und deine Siegquote mit der Karte; Rahmen lila = Top-Pick, grün = passt, grau = fremd. Einmal bei vollem Pack „Kalibrieren“ im Steuerfenster und fünf Ecken anklicken (Karte 1 oben links und unten rechts, Karte 2 oben links, letzte Karte der ersten Reihe oben links, erste Karte der zweiten Reihe oben links); gespeichert in <code>kartenoverlay.json</code> (nicht im Git). Jede Karte zeigt unten klein ihren Namen aus dem Protokoll: passt er nicht zur Karte darunter, sortiert Arena die Karten anders. Klicks gehen durch das Overlay zu Arena.':
        'The <b>card overlay</b> puts the numbers directly onto the cards in the Arena window while picking: top left the rank in the pack, top right the rating, at the bottom points, colors of the best archetype, fit (✓ your archetype, ≈ close, ○ colors fit, – other colors), removal, card flow, synergy, creature and your win rate with the card; frame purple = top pick, green = fits, grey = other. Once, with a full pack, press “Calibrate” in the control window and click five corners (card 1 top left and bottom right, card 2 top left, last card of the first row top left, first card of the second row top left); saved in <code>kartenoverlay.json</code> (not in Git). Each card shows its name from the log in small print at the bottom: if it does not match the card below, Arena sorts the cards differently. Clicks go through the overlay to Arena.',
}
