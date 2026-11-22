"""Englische Texte fuer Set bewerten (components/setrating.py)."""

EN = {
    "Lade Set {code} von Scryfall …": "Loading set {code} from Scryfall …",
    "Set konnte nicht geladen werden: {err}": "Set could not be loaded: {err}",
    "Fehler": "Error",
    "Nicht gespeichert: {err}": "Not saved: {err}",
    "{done} von {total} Karten fertig · {rated} mit Kategorie · {assigned} mit Archetyp":
        "{done} of {total} cards done · {rated} with category · {assigned} with archetype",
    "gezeigt: {n}": "shown: {n}",
    "Keine Karten für diese Auswahl.": "No cards for this selection.",
    "bester Archetyp": "best archetype",
    "passt gut": "fits well",
    "Archetypen dieser Karte. Klick: neutral → grün (passt gut) → lila (bester Archetyp, nur einer) → neutral":
        "Archetypes of this card. Click: neutral → green (fits well) → purple (best archetype, only one) → neutral",
    "Set bewerten beenden?": "Quit Rate a set?",
    "Set bewerten wurde beendet. Du kannst dieses Fenster jetzt schließen.":
        "Rate a set has been closed. You can close this window now.",
    "Set bewerten": "Rate a set",
    "Beenden": "Quit",
    "Karte suchen (Name oder Typ)": "Search card (name or type)",
    "Zeigen": "Show",
    "Alle Karten": "All cards",
    "Noch offen": "Still open",
    "Ohne Kategorie": "Without category",
    "Ohne Archetyp": "Without archetype",
    "Seltenheit": "Rarity",
    "Tipp: Klick auf ein Kartenbild öffnet die Großansicht, dort wechseln die Pfeiltasten zur nächsten Karte. Auch "
    "hier: Maus auf eine Karte und Taste 1 bis 6 drücken (1 = Matchwinner … 6 = NeverPlay, noch einmal = entfernen, "
    "0 = entfernen). Archetypen: neutral → grün (passt gut) → lila (bester Archetyp) → neutral. Alles wird sofort "
    "gespeichert und gilt für jeden Pool und jeden Draft.":
        "Tip: clicking a card image opens the large view, where the arrow keys switch to the next card. Here too: "
        "hover over a card and press 1 to 6 (1 = Matchwinner … 6 = NeverPlay, same key again = remove, 0 = remove). "
        "Archetypes: neutral → green (fits well) → purple (best archetype) → neutral. Everything is saved at once "
        "and applies to every pool and every draft.",
    "Karte {i} von {n}": "Card {i} of {n}",
    "Klick aufs Kartenbild öffnet die Großansicht: Karte groß, Knöpfe mit Namen, ← → (Tasten oder Pfeilknöpfe) zur "
    "vorigen bzw. nächsten der gerade gezeigten Karten, Esc schließt.":
        "Clicking the card image opens the large view: the card in big, buttons with names, ← → (keys or arrow "
        "buttons) to the previous or next of the cards currently shown, Esc closes.",
    "Kategorie": "Category",
    "Archetypen": "Archetypes",
    "← → nächste Karte · 1 bis 6 Kategorie, 0 entfernen · Esc schließen. Archetypen: Klick wechselt neutral → grün "
    "(passt gut) → lila (bester Archetyp) → neutral.":
        "← → next card · 1 to 6 category, 0 remove · Esc close. Archetypes: click switches neutral → green (fits "
        "well) → purple (best archetype) → neutral.",
    "Welches Set willst du bewerten? Kategorie und Archetypen legst du hier einmal je Karte fest; Drafthelper und "
    "Live-Draft nutzen sie danach in jedem Draft.":
        "Which set do you want to rate? Here you set the category and archetypes of each card once; the Draft "
        "Helper and the live draft then use them in every draft.",
    "Set bewerten läuft: {url}": "Rate a set is running: {url}",
    "Set bewerten beendet.": "Rate a set closed.",
    "Bombe: entscheidet ein Match allein – kommt immer rein, notfalls als Splash":
        "Bomb: wins a match on its own – always goes in, as a splash if necessary",
    "Entscheidet Spiele allein – soll auf jeden Fall rein, auch wenn wir die Farbe nicht spielen":
        "Wins games on its own – should go in even if we don't play its color",
    "Wird auf jeden Fall gespielt, wenn wir diese Farbe spielen": "Always played if we play this color",
    "Solide, wird meist gespielt, wenn wir diese Farbe spielen, aber nicht zwingend":
        "Solid, usually played if we play this color, but not necessarily",
    "Füllt das Deck auf, wenn wir die Farbe spielen und nicht splashen":
        "Fills up the deck if we play the color and don't splash it",
    "Zu schlecht oder zu situativ, wird nicht gespielt": "Too weak or too situational, not played",
    "Set {code} ist nicht umgesetzt, bitte auf der Seite wählen.":
        "Set {code} is not supported, please choose on the page.",
    "Ungültige Anfrage": "Invalid request",
    "Set {code} ist nicht umgesetzt": "Set {code} is not supported",
    "Set {code} konnte nicht geladen werden (Scryfall)": "Set {code} could not be loaded (Scryfall)",
    # Hilfe (components/howitworks.py)
    "Im Launcher (<code>draftgott.pyw</code>) <b>Set bewerten starten</b> oder <code>python mtg_sim.py --set-bewerten [SET]</code>: "
    "eigene Seite im Browser. Zuerst ein fertig umgesetztes Set wählen (alle Sets mit Archetypen, derzeit TRK, FRA "
    "und SOS), dann je Karte Kategorie und Archetypen festlegen.":
        "In the launcher (<code>draftgott.pyw</code>) <b>Start rating</b> or <code>python mtg_sim.py --set-bewerten [SET]</code>: a "
        "page of its own in the browser. First choose a fully supported set (all sets with archetypes, currently "
        "TRK, FRA and SOS), then set the category and archetypes of each card.",
    "Zu TRK gehören auch die 30 Karten des Bonusblatts Stardates (SDS), die selten in den Boostern liegen; sie stehen "
    "in der Set-Ansicht hinter den TRK-Karten.":
        "TRK also includes the 30 cards of the Stardates (SDS) bonus sheet, which rarely turn up in boosters; they "
        "come after the TRK cards in the set view.",
    "Kategorie per Knopf (♛ Matchwinner bis NP NeverPlay) oder mit der Tastatur: Maus auf die Karte, Taste 1 bis 6, "
    "0 entfernt. Archetypen per Klick: neutral → grün (passt gut) → lila (bester Archetyp) → neutral.":
        "Category by button (♛ Matchwinner to NP NeverPlay) or by keyboard: hover over the card, key 1 to 6, 0 "
        "removes. Archetypes by click: neutral → green (fits well) → purple (best archetype) → neutral.",
    "Alles wird sofort in <code>kartenbewertung.json</code> und <code>kartenarchetypen.json</code> gespeichert und "
    "gilt je Kartenname für jeden Pool, den Drafthelper und den Live-Draft: ein Set wird einmal bewertet, nicht nach "
    "jedem Draft. Der Balken zeigt den Fortschritt (fertig = Kategorie und Archetyp, NeverPlay braucht keinen "
    "Archetyp); der Filter „Noch offen“ zeigt die übrigen Karten.":
        "Everything is saved at once to <code>kartenbewertung.json</code> and <code>kartenarchetypen.json</code> "
        "and applies per card name to every pool, the Draft Helper and the live draft: a set is rated once, not "
        "after every draft. The bar shows the progress (done = category and archetype, NeverPlay needs no "
        "archetype); the filter “Still open” shows the remaining cards.",
}
