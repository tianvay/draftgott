"""Englisches Woerterbuch: Archetyp-Hinweise, Synergie-Ressourcen, Signale, Deckvorschlag, Meldungen."""
EN = {
    # Farbnamen (archetypes.COLOR_NAME)
    "Weiß": "White", "Blau": "Blue", "Schwarz": "Black", "Rot": "Red", "Grün": "Green",
    # Archetyp-Hinweise TRK
    "Sehr wichtig: die Zahl der Spacecraft und der Payoffs im Gleichgewicht halten.":
        "Very important: keep the number of Spacecraft and payoffs in balance.",
    "Spacecraft sind erst im mittleren bis späten Spiel Kreaturen – das Deck entsprechend bauen.":
        "Spacecraft only become creatures in the mid to late game - build the deck accordingly.",
    "Vigilance ist wichtig für Station.": "Vigilance matters for Station.",
    "Sehr flexibel.": "Very flexible.",
    "Kann mit Synergien das Spiel übernehmen.": "Can take over the game with synergies.",
    "Aggressiv: will den Gegner mit Sacrifice-Fodder und dem Wert daraus überrennen.":
        "Aggressive: wants to overrun the opponent with sacrifice fodder and the value it generates.",
    "Jede Karte, die mehrere Körper bringt, ist stark.": "Every card that brings multiple bodies is strong.",
    "Ramp + Stompy.": "Ramp + Stompy.",
    "Landfall-Trigger.": "Landfall triggers.",
    "Synergien sind sehr wichtig: Karten, die sich um +1/+1 counters kümmern.":
        "Synergies are very important: cards that care about +1/+1 counters.",
    "Aggro-Deck: auf Synergien und Artifact Creatures setzen.":
        "Aggro deck: lean on synergies and Artifact Creatures.",
    "Kleine Kreaturen zählen, weil das Removal flexibel ist.":
        "Small creatures count because the removal is flexible.",
    "Removal + Kartenziehen = Control.": "Removal + card draw = control.",
    "Darauf achten, genug Kreaturen zu spielen.": "Make sure to play enough creatures.",
    "Zäh und aufs späte Spiel ausgelegt: den Gegner mit Kartenvorteil ausspielen.":
        "Resilient and built for the late game: out-value the opponent with card advantage.",
    "Graveyard-Synergien machen aus 1-gegen-1-Tauschen Wert im späten Spiel.":
        "Graveyard synergies turn 1-for-1 trades into value in the late game.",
    "8 Power zu erreichen ist leichter als gedacht, wenn man genug Kreaturen spielt.":
        "Reaching 8 power is easier than it sounds if you play enough creatures.",
    "Aggressive 2-Drops sind der Schlüssel, um früh 8 Power zu erreichen.":
        "Aggressive 2-drops are the key to reaching 8 power early.",
    "Splash-freundlich, weil man viele verschieden benannte Länder will.":
        "Splash-friendly, since you want many differently named lands.",
    "Spielt gern Off-Color-Bomben.": "Happily plays off-color bombs.",
    # Archetyp-Hinweise FRA
    "Aufs Board spielen.": "Play to the board.",
    "Mit Surveil die starken Karten finden.": "Use surveil to find the strong cards.",
    "Empower Jace für Surveil-Synergien.": "Empower Jace for surveil synergies.",
    "Aufs lange Spiel spielen.": "Play for the long game.",
    "Flexible Karten bevorzugen.": "Prefer flexible cards.",
    "Billige Kreaturen spielen.": "Play cheap creatures.",
    "Spiele mit Direct Damage schnell beenden.": "Finish games quickly with direct damage.",
    "Ramp und teure Zauber im Gleichgewicht halten.": "Keep ramp and expensive spells in balance.",
    "Frühe Spielzüge zählen trotzdem.": "Early plays still matter.",
    "Removal und Blocker bevorzugen.": "Prefer removal and blockers.",
    "Aggressiv spielen.": "Play aggressively.",
    "Mit Lifegain das Damage-Race gewinnen.": "Win the damage race with lifegain.",
    "Spiele durch 1-gegen-1-Tausche in die Länge ziehen.": "Drag games out through 1-for-1 trades.",
    "Mit Recursion den Gegner im Kartenwert ausspielen.": "Out-value the opponent with recursion.",
    "Auf Zermürbung (Attrition) ausgelegt.": "Built for attrition.",
    "Prowess-Kreaturen sind der Schlüssel zum Sieg.": "Prowess creatures are the key to victory.",
    "Kartenziehen ist wichtig, damit die Hand voll bleibt.": "Card draw is important to keep your hand full.",
    "Gutes Removal spielen.": "Play good removal.",
    "Große Kreaturen spielen.": "Play big creatures.",
    "Wenig Synergie, hohe Kartenqualität.": "Little synergy, high card quality.",
    "So schnell wie möglich spielen.": "Play as fast as possible.",
    "So viele Kreaturen wie möglich.": "As many creatures as possible.",
    "Kämpfe mit Removal und Tricks gewinnen.": "Win combat with removal and tricks.",
    "Aufs späte Spiel auslegen.": "Build for the late game.",
    "Defensive Karten bevorzugen.": "Prefer defensive cards.",
    # Synergie-Ressourcen
    "+1/+1-Marken": "+1/+1 counters",
    "Buffs, Auren, Ausrüstung": "Buffs, Auras, Equipment",
    "Schutz (Hexproof, Indestructible)": "Protection (hexproof, indestructible)",
    "Gute Träger (Ausweichen, Schutz)": "Good carriers (evasion, protection)",
    "Kreaturen": "Creatures",
    "Lebensgewinn": "Lifegain",
    "Nichtkreatur-Zauber": "Noncreature spells",
    "Surveil": "Surveil",
    "Kreatur-Token": "Creature tokens",
    "Opfer-Möglichkeiten": "Sacrifice outlets",
    "Opferbares (Token, Sterbe-Ausloeser)": "Sacrifice fodder (tokens, death triggers)",
    "Friedhof füllen": "Filling the graveyard",
    "Artefakte": "Artifacts",
    "Verzauberungen": "Enchantments",
    "Legendäre Karten": "Legendary cards",
    "Planeswalker": "Planeswalkers",
    "Jace": "Jace",
    "Schaden außerhalb des Kampfs": "Damage outside of combat",
    "Abwerfen": "Discard",
    "Defender / Toughness > Power": "Defender / toughness > power",
    "Kleine Kreaturen (P oder T ≤ 1)": "Small creatures (P or T ≤ 1)",
    "Zauber mit Ziel beim Gegner": "Spells targeting the opponent",
    "Kreaturtyp {typ}": "Creature type {typ}",
    # Signale
    "Pick {pick}: {card} kam zurück": "Pick {pick}: {card} wheeled",
    "Pick {pick}: {card} von anderen genommen": "Pick {pick}: {card} taken by others",
    "Pick {pick}: {card} noch spät im Pack": "Pick {pick}: {card} still in the pack late",
    # Deckvorschlag
    "Eine Variante hat schon {n} Karten und liegt über dem Ziel von {target}.":
        "One variant already has {n} cards and is above the target of {target}.",
    "Nicht genug Filler: Splash-Variante {s} und NoSplash-Variante {n} Karten, Ziel {target}.":
        "Not enough filler: Splash variant {s} and NoSplash variant {n} cards, target {target}.",
    "Länder: {lands} (Faustregel bei {target} Karten: {low} bis {high}).":
        "Lands: {lands} (rule of thumb for {target} cards: {low} to {high}).",
    "Nicht genug Filler: Der Deckvorschlag hat {size} statt {target} Karten.":
        "Not enough filler: the deck suggestion has {size} instead of {target} cards.",
    # Meldungen
    "Kartenname fehlt": "Card name is missing",
    "Unbekannter Archetyp": "Unknown archetype",
    "Unbekannte Kategorie": "Unknown category",
}
