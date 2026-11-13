"""Turniermodus (components/tournament.py): Deutsch -> Englisch."""
EN = {
    "Kein Deck mit Nummer {n}.": "No deck with number {n}.",
    "'{w}' passt nicht auf genau ein Deck.": "'{w}' does not match exactly one deck.",
    "Paarung '{p}' bitte als A-B angeben.": "Please enter pairing '{p}' as A-B.",
    "Ein Deck kann nicht gegen sich selbst spielen ({p}).": "A deck cannot play against itself ({p}).",
    "Turnier-Ordner (Nummer): ": "Tournament folder (number): ",
    "Decks:": "Decks:",
    "Paarungen, z. B. 1-3 2-4 (Enter = jeder gegen jeden): ":
        "Pairings, e.g. 1-3 2-4 (Enter = round robin): ",
    "{p} hätte gewinnen sollen": "{p} should have won",
    "zu knapp, kein klarer Favorit": "too close, no clear favourite",
    "Siegquote des Beginnenden: wenn {x} beginnt / wenn {y} beginnt":
        "Win rate of the starting player: when {x} starts / when {y} starts",
    "Deck A": "Deck A",
    "Siege A": "Wins A",
    "Unent.": "Draws",
    "Siege B": "Wins B",
    "Deck B": "Deck B",
    "Quote A": "Rate A",
    "95-%-Bereich": "95 % range",
    "Beginnender gewinnt": "Starting player wins",
    "Ergebnis": "Result",
    "Deck": "Deck",
    "Matches": "Matches",
    "Match-Bilanz (S-N-U)": "Match record (W-L-D)",
    "Spiele gewonnen": "Games won",
    "Spiele verloren": "Games lost",
    "Spielquote": "Game win rate",
    "Turnier {f}": "Tournament {f}",
    "Je Paarung {n} Spiele. Spiel 1 beginnt per Zufall, danach geht der Verlierer des vorigen Spiels "
    "zuerst (Regel 103.1: der Verlierer wählt, im Limited fast immer zuerst spielen); nach einem "
    "Unentschieden beginnt wieder derselbe. Beide Decks spielen nach den Regeln des Kampfmodells und "
    "geben beim Mulligan nie auf. Nach Runde {r} gilt ein Spiel als unentschieden.":
        "{n} games per pairing. Game 1 starts at random, after that the loser of the previous game goes first "
        "(rule 103.1: the loser chooses, in Limited almost always to play first); after a draw the same player "
        "starts again. Both decks play by the rules of the combat model and never concede at the mulligan. After "
        "turn {r} a game counts as a draw.",
    "Favorit: Liegt der 95-%-Bereich der Siegquote (ohne Unentschieden) ganz über 50 %, hätte das "
    "Deck statistisch gewinnen sollen; enthält er 50 %, ist das Matchup zu knapp für eine Aussage.":
        "Favourite: if the 95 % range of the win rate (without draws) lies entirely above 50 %, the deck should "
        "statistically have won; if it contains 50 %, the matchup is too close to call.",
    "Paarungen": "Pairings",
    "Tabelle": "Standings",
    "Sortiert nach Match-Siegen (mehr gewonnene Spiele der Paarung), dann nach Spielquote.":
        "Sorted by match wins (more games won in the pairing), then by game win rate.",
    "{n} Decks, {m} Paarungen": "{n} decks, {m} pairings",
    "Kein Unterordner mit Decks in {path}.": "No subfolder with decks in {path}.",
    "Turnier-Ordner nicht gefunden: {f} (vorhanden: {all})": "Tournament folder not found: {f} (available: {all})",
    "Für ein Turnier braucht der Ordner mindestens zwei Decks.":
        "A tournament needs at least two decks in the folder.",
    "{a} gegen {b}: {n} Spiele ...": "{a} vs {b}: {n} games ...",
    "Turnierbericht gespeichert: {path}": "Tournament report saved: {path}",
}
