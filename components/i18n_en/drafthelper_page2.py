"""Drafthelper-Seite (PAGE in components/drafthelper.py), Teil 2: woertliche Ersetzungen Deutsch -> Englisch.
Jeder Schluessel muss genau so in PAGE vorkommen (siehe tests/test_i18n_drafthelper_page2.py)."""

PAGE = {
    # Farbnamen und Farbdiagramm
    '{W:"Weiß",U:"Blau",B:"Schwarz",R:"Rot",G:"Grün",M:"Mehrfarbig",C:"Farblos"}':
        '{W:"White",U:"Blue",B:"Black",R:"Red",G:"Green",M:"Multicolor",C:"Colorless"}',
    '" Karte":" Karten"': '" card":" cards"',
    '" (eine Karte, mehrere Farben)"': '" (one card, multiple colors)"',
    '" (mehrere Farben)"': '" (multiple colors)"',
    '"Jede Karte steht genau einmal im Diagramm (Balkenhöhe = Kartenzahl). Karten mit mehreren Farben bilden das goldene "':
        '"Each card appears exactly once in the chart (bar height = number of cards). Multicolor cards form the golden "',
    '"Segment „Mehrfarbig“."': '"“Multicolor” segment."',
    '"Eine mehrfarbige Karte zählt bei jeder ihrer Farben, z. B. eine Karte Grün/Weiß bei Grün und bei Weiß. Die Balken "':
        '"A multicolor card counts under each of its colors, e.g. a green/white card under green and under white. The bars "',
    '"ergeben deshalb zusammen mehr als die Kartenzahl."': '"therefore add up to more than the number of cards."',
    '" Nichtland-Karten in der Variante, davon "': '" nonland cards in the variant, of which "',
    '" mehrfarbig und "': '" multicolor and "',
    '" farblos."': '" colorless."',
    '" Mehrfarbig: "': '" Multicolor: "',
    # Typ-Uebersicht
    '"Ziehen (Draw)"': '"Draw"',
    '"Suchen (Search)"': '"Search"',
    '"Mill: sich selbst"': '"Mill: self"',
    '"Mill: Gegner möglich (auch „target player“)"': '"Mill: opponent possible (also “target player”)"',
    '"Karten gesamt"': '"Total cards"',
    '"Kreaturen"': '"Creatures"',
    '"Artefakte (ohne Kreaturen)"': '"Artifacts (excluding creatures)"',
    '"Verzauberungen"': '"Enchantments"',
    '"Länder gesamt"': '"Total lands"',
    '"davon Nicht-Standard-Länder"': '"of which nonbasic lands"',
    '"Empower Jace (Karten)"': '"Empower Jace (cards)"',
    '"Σ Loyalty beim Wirken/Betreten"': '"Σ Loyalty on cast/enter"',
    '"Flash (bleibende Karten)"': '"Flash (permanent cards)"',
    '"Removal (Karten)"': '"Removal (cards)"',
    '"Σ Removal-Punkte"': '"Σ Removal points"',
    '"Prepared (Karten)"': '"Prepared (cards)"',
    '"Manaquellen (Karten)"': '"Mana sources (cards)"',
    '"Friedhof-Interaktion (Karten)"': '"Graveyard interaction (cards)"',
    '"Σ Friedhof-Punkte"': '"Σ Graveyard points"',
    '"Friedhof-Enabler (Karten)"': '"Graveyard enabler (cards)"',
    '"Kartenfluss (Karten)"': '"Card flow (cards)"',
    '"Σ Synergie-Punkte"': '"Σ Synergy points"',
    'v.score.toFixed(1).replace(".",",")': 'v.score.toFixed(1)',
    '"Wie gut die Karten zusammenpassen (Abschnitt Synergie im Bericht); Ampel grün ab 6, gelb ab 3,5 bei 40 Karten"':
        '"How well the cards fit together (Synergy section in the report); traffic light green from 6, yellow from 3.5 at 40 cards"',
    '"Ohne Partner"': '"No partner"',
    '"Gezählt werden Kopien in der Variante (Core plus Gruppe) einschließlich Standardländern. Artefakte und "':
        '"Counted are copies in the variant (core plus group), including basic lands. Artifacts and "',
    '"Verzauberungen ohne Kreaturen und Länder; eine Karte kann in mehreren Zeilen stehen. Fett: Unterschied zwischen "':
        '"enchantments exclude creatures and lands; a card can appear in several rows. Bold: difference between "',
    '"den Varianten. Σ Loyalty: Zahlenwerte von Empower Jace beim Zauber oder Betreten (ohne X, ohne Auslöser). "':
        '"the variants. Σ Loyalty: numeric values of Empower Jace on cast or enter (without X, without triggers). "',
    '"Kartenfluss: Karten, die ziehen, suchen, surveilen, scrien oder explorieren; es erscheinen nur Arten, die im Pool "':
        '"Card flow: cards that draw, search, surveil, scry or explore; only kinds present in the pool "',
    '"vorkommen. Empower Jace zählt nicht dazu (eigene Zeile). Prepared: Karten, deren Zauberhälfte als Kopie "':
        '"appear. Empower Jace is not included (own row). Prepared: cards whose spell half can be "',
    '"gewirkt werden kann (nur, wenn der Pool solche Karten hat). Flash nur bei bleibenden Karten. Removal-Punkte: "':
        '"cast as a copy (only if the pool has such cards). Flash only for permanent cards. Removal points: "',
    '"1 = entfernt jede gegnerische Kreatur (Details unter „So funktioniert es“); Ampel grün ab 4, gelb ab 2,5 "':
        '"1 = removes any opposing creature (details under “How it works”); traffic light green from 4, yellow from 2.5 "',
    '"Punkten bei 40 Karten. Synergie-Punkte: Karten, die von anderen Karten im Deck profitieren, und wie gut das "':
        '"points at 40 cards. Synergy points: cards that benefit from other cards in the deck, and how well that "',
    '"erfüllt ist (Ampel grün ab 6, gelb ab 3,5 bei 40 Karten); „Ohne Partner“: Karten, deren Bedarf kaum erfüllt ist."':
        '"is met (traffic light green from 6, yellow from 3.5 at 40 cards); “No partner”: cards whose need is barely met."',
    # Export
    '"Splash-Variante"': '"Splash variant"',
    '"NoSplash-Variante"': '"NoSplash variant"',
    '"Deckvorschlag"': '"Deck proposal"',
    '" Karten im Deck, "': '" cards in deck, "',
    '" im Sideboard"': '" in sideboard"',
    '"Kopieren"': '"Copy"',
    '"Als Datei speichern"': '"Save as file"',
    '"Kopiert"': '"Copied"',
    # Uebersicht links
    '"Weiß","#f1e7b8"': '"White","#f1e7b8"',
    '"Blau","#3b82d6"': '"Blue","#3b82d6"',
    '"Schwarz","#4a4a4a"': '"Black","#4a4a4a"',
    '"Rot","#d6453b"': '"Red","#d6453b"',
    '"Grün","#3f9b4f"': '"Green","#3f9b4f"',
    '"Mehrfarbig","#d9a400"': '"Multicolor","#d9a400"',
    '"Farblos","#b7bcc6"': '"Colorless","#b7bcc6"',
    '"Länder","#9a7b4f"': '"Lands","#9a7b4f"',
    '"Zuordnung","grp"': '"Assignment","grp"',
    '"Kategorie","grp"': '"Category","grp"',
    '"Farbe","l"': '"Color","l"',
    '"Alle Kopien in Deck und Sideboard der Datei (ohne Standardländer)"':
        '"All copies in deck and sideboard of the file (excluding basic lands)"',
    '"ohne Kategorie"': '"no category"',
    '"Gesamt"': '"Total"',
    '"Mehrfarbige Karten stehen nur in „Mehrfarbig“. Pool = alle Kopien in Deck und Sideboard der Datei, ohne Standardländer. "':
        '"Multicolor cards appear only under “Multicolor”. Pool = all copies in deck and sideboard of the file, excluding basic lands. "',
    '"C/S/N = Core/Splash/NoSplash; der Rest des Pools ist „Aus“. Kategorien: "':
        '"C/S/N = Core/Splash/NoSplash; the rest of the pool is “Off”. Categories: "',
    # Deckvorschlag
    '"Deckvorschlag: "': '"Deck proposal: "',
    '" Karten (Ziel "': '" cards (target "',
    '"), davon "': '"), of which "',
    '" Länder · Farben "': '" lands · colors "',
    ':"keine")': ':"none")',
    '"Schließen"': '"Close"',
    '"Zauber ("': '"Spells ("',
    '"Länder ("': '"Lands ("',
    '" Karten ohne Kategorie wurden nicht berücksichtigt."': '" cards without a category were not taken into account."',
    '"Beim Simulieren erscheint der Deckvorschlag als weitere Variante (Haken „mitsimulieren“)."':
        '"When simulating, the deck proposal appears as another variant (checkbox “also simulate”)."',
    '"Fehler beim Deckvorschlag"': '"Error creating the deck proposal"',
    '"Fehler beim Vorschlag"': '"Error creating the suggestion"',
    '"Fehler bei der Land-Empfehlung"': '"Error in the land recommendation"',
    '"Keine Änderung"': '"No change"',
    '"Es gibt keine Karten mit Kategorie, die noch umgeordnet werden müssten."':
        '"There are no cards with a category that still need to be reassigned."',
    '"Zuordnung nach Kategorien gesetzt"': '"Assignment by category applied"',
    '"Nach Kategorie: "': '"By category: "',
    '" → Aus (NeverPlay)."': '" → Off (NeverPlay)."',
    '" nicht benötigt (Aus)."': '" not needed (Off)."',
    '"Größe: Splash-Variante "': '"Size: Splash variant "',
    '", NoSplash-Variante "': '", NoSplash variant "',
    '"Mit „Rückgängig“ stellst du den vorherigen Stand wieder her."': '"“Undo” restores the previous state."',
    '"Rückgängig gemacht"': '"Undone"',
    '"Der Stand vor dem letzten Vorschlag ist wiederhergestellt."': '"The state before the last suggestion has been restored."',
    'p>=0.9?"grün":p>=0.8?"gelb":"rot"': 'p>=0.9?"green":p>=0.8?"yellow":"red"',
}
