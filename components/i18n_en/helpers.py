"""Englisch fuer die Bausteine: stats, html_base, landadvice, simulation sowie die Konstanten aus coverage, mulligan,
graveyard und removal (deren Anzeige liegt in report.py, report_cards.py und howitworks.py und ruft t() darauf auf)."""

EN = {
    # stats.compare_metrics
    "Mulligan auf der ersten Hand": "Mulligan on the opening hand",
    "Spiel verloren (Mulligan)": "Game lost (mulligan)",
    "Zauber gespielt in Runde {t}": "Spell cast on turn {t}",
    "Alle Farben bis Runde 3": "All colors by turn 3",
    "Weiß": "White",
    "Blau": "Blue",
    "Schwarz": "Black",
    "Rot": "Red",
    "Grün": "Green",
    "≥ {k} Quellen {col} bis Runde {turn}": "≥ {k} {col} sources by turn {turn}",
    "Mana Screw nach Runde {T}": "Mana screw after turn {T}",
    "Flood ({n}+ Länder bis Runde {r})": "Flood ({n}+ lands by turn {r})",
    "Kreaturen auf dem Feld nach Runde {T}": "Creatures on the battlefield after turn {T}",
    "Gesamt-Power nach Runde {T}": "Total power after turn {T}",
    "Curve-Auslastung Runde 1–{C} (Mana genutzt)": "Curve utilization turns 1–{C} (mana used)",
    "{n} Schaden bis Runde {x}": "{n} damage by turn {x}",
    "Ø Runde für {n} Schaden": "Avg turn for {n} damage",
    "Jace-Aktivierungen bis Hand leer (Ø)": "Jace activations until hand empty (avg)",
    # html_base
    "Runde {r}": "Turn {r}",
    "ⓘ So funktioniert es": "ⓘ How it works",
    # landadvice
    "{g}: mehr passende Nicht-Standardländer ({n}) als Länder nach der Faustregel.":
        "{g}: more fitting nonbasic lands ({n}) than lands according to the rule of thumb.",
    "{g}: keine Karte verlangt eine bestimmte Farbe, deshalb werden keine Standardländer empfohlen.":
        "{g}: no card requires a specific color, so no basic lands are recommended.",
    "{g}: {spells} Zauber + {lands} Länder = {deck} Karten (Ziel {target}; Faustregel {low} bis {high} Länder).":
        "{g}: {spells} spells + {lands} lands = {deck} cards (target {target}; rule of thumb {low} to {high} lands).",
    # simulation
    "Fast jede Starthand fuehrt zum Mulligan: nur {played} von {sims} Spielen wurden gespielt. Das Deck ist mit "
    "diesen Mulligan-Regeln praktisch unspielbar.":
        "Almost every opening hand leads to a mulligan: only {played} of {sims} games were played. The deck is "
        "practically unplayable with these mulligan rules.",
    "Land fehlt": "Land missing",
    "Karte nicht spielbar": "Card not playable",
    # mulligan (Konstanten MULL_*; Anzeige in report.py)
    "Keine Karte nach Farben spielbar": "No card castable by colors",
    "6 oder mehr Länder": "6 or more lands",
    "Höchstens 2 Länder und weniger als 3 spielbare Karten": "At most 2 lands and fewer than 3 castable cards",
    # graveyard (kind; Anzeige in report_cards.py)
    "Zweitverwertung": "Second use",
    "Zurückholen": "Recursion",
    "Ressource": "Resource",
    # removal (kind; Anzeige in report_cards.py)
    "Massenremoval": "Mass removal",
    "Exil bis verlassen": "Exile until leaves",
    "Hart": "Hard",
    "Bedingt": "Conditional",
    "Bibliothek": "Library",
    "Edikt": "Edict",
    "Schaden": "Damage",
    "Fight": "Fight",
    "Bounce": "Bounce",
    "Toughness 0": "Toughness 0",
    "Lock": "Lock",
    "−1/−1-Marken": "−1/−1 counters",
    "Fähigkeit": "Ability",
    "Auslöser": "Trigger",
    # coverage (Konstanten; Anzeige in report.py, howitworks.py)
    "To Do: Noch nicht implementiert": "To do: not implemented yet",
    "Lethal / Schaden": "Lethal / damage",
    "Mana und Zauber pro Runde": "Mana and spells per turn",
    "Kartenfluss (Länder, Screw/Flood)": "Card flow (lands, screw/flood)",
    "keine (Gegner ist nicht Teil des Modells)": "none (opponent is not part of the model)",
    "unklar": "unclear",
    "Unbekannter Effekt": "Unknown effect",
    "Prepared-Zauberhälfte": "Prepared spell half",
    "Planeswalker-Fähigkeit": "Planeswalker ability",
    "Land: Bedingung nicht modelliert": "Land: condition not modeled",
    "Empower Jace (Wert nicht modelliert)": "Empower Jace (value not modeled)",
    "Empower Jace (Auslöser nicht modelliert)": "Empower Jace (trigger not modeled)",
    "Zauberhälfte": "Spell half",
    "Zählmarken / Stärkebonus": "Counters / power bonus",
    "Timing (Flash)": "Timing (flash)",
    "Zweitverwertung (Friedhof)": "Second use (graveyard)",
    "Kostensenkung / Convoke": "Cost reduction / convoke",
    "Kartenfluss": "Card flow",
    "Tokens erzeugen": "Create tokens",
    "Mana außer Ländern": "Mana besides lands",
    "Direkter Schaden": "Direct damage",
    "Defender-Ausnahme": "Defender exception",
    "Haste verleihen": "Grant haste",
    "Interaktion mit dem Gegner": "Interaction with the opponent",
    "Lebensgewinn": "Life gain",
    "Zusatzkosten": "Additional costs",
    "Schlüsselwort verleihen": "Grant keyword",
}
