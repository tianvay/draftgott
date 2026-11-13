"""Kommandozeile: alle Parameter von mtg_sim.py."""
import argparse


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="MTG Starthand-Simulator: erzeugt einen HTML-Bericht")
    ap.add_argument("deckfile", nargs="*",
                    help="Deckliste(n). Mit --core: die Varianten, die zum Kern hinzukommen; die erste ist die Basis, "
                         "alle weiteren werden mit ihr verglichen")
    ap.add_argument("--drafthelper", nargs="?", const="_draftedcardpool.txt", default=None, metavar="DATEI",
                    help="Draft-Helper: Kartenseite im Browser, auf der Karten als Core/Splash/NoSplash markiert und "
                         "die Varianten direkt simuliert werden. Optional die Kartenpool-Datei "
                         "(Standard: _draftedcardpool.txt)")
    ap.add_argument("--core", metavar="DATEI", default=None,
                    help="Kern-Deckliste, die zu jeder Variante (deckfile / --deckalt) hinzugefuegt wird")
    ap.add_argument("--bewertung", default="kartenbewertung.json", metavar="DATEI",
                    help="Drafthelper: Datei mit der Kartenbewertung (Matchwinner, Splashworthy, MustPlay, Filler, NeverPlay) je "
                         "Kartenname, gilt fuer jeden Kartenpool (Standard: kartenbewertung.json, nicht im Git)")
    ap.add_argument("--archetypen", default="kartenarchetypen.json", metavar="DATEI",
                    help="Drafthelper: Datei mit der eigenen Archetyp-Zuordnung je Kartenname (Farbpaare wie BR), "
                         "gilt fuer jeden Kartenpool (Standard: kartenarchetypen.json, nicht im Git)")
    ap.add_argument("--live", action="store_true",
                    help="Drafthelper im Live-Draft: liest das Arena-Protokoll (Player.log) mit, schreibt die Picks in "
                         "die Kartenpool-Datei und zeigt das aktuelle Pack mit Bewertung und Archetyp, dazu ein "
                         "Seitenfenster ueber Arena")
    ap.add_argument("--arena-log", default=None, metavar="DATEI",
                    help="Live-Draft: Pfad des Arena-Protokolls (Standard: AppData/LocalLow/Wizards Of The Coast/"
                         "MTGA/Player.log)")
    ap.add_argument("--kein-overlay", action="store_true",
                    help="Live-Draft ohne Seitenfenster (nur die Seite im Browser)")
    ap.add_argument("--overlay", default=None, metavar="URL",
                    help="Nur das Seitenfenster fuer einen laufenden Live-Draft-Drafthelper unter URL oeffnen")
    ap.add_argument("--statistik", default="draftstatistik.json", metavar="DATEI",
                    help="Draft-Statistik des Live-Drafts (Picks, Decks, Matches je Draft; Standard: "
                         "draftstatistik.json, nicht im Git)")
    ap.add_argument("--statistik-neu", action="store_true",
                    help="Draft-Statistik aus den Arena-Protokollen (Player-prev.log und Player.log) neu aufbauen; die "
                         "alte Datei bleibt als <Name>.backup.json erhalten")
    ap.add_argument("--setauswertung", nargs="?", const="", default=None, metavar="SET",
                    help="Setauswertung: die Draft-Statistik eines Sets als HTML-Seite setauswertung_<set>.html "
                         "(ohne SET: das Set mit den meisten Drafts)")
    ap.add_argument("--neu-laden", action="store_true",
                    help="Kartendaten neu von Scryfall laden und den lokalen Cache (scryfall_cache.json) ueberschreiben")
    ap.add_argument("--sims", type=int, default=10000)
    ap.add_argument("--turns", type=int, default=3)
    ap.add_argument("--max-runden", type=int, default=15,
                    help="Bis zu welcher Runde fuer Handleer/Top-Card-Statistik simuliert wird")
    ap.add_argument("--deckalt", action="append", metavar="DATEI", default=None,
                    help="Alternative Deckliste zum Vergleich mit dem Hauptdeck (mehrfach angeben moeglich)")
    ap.add_argument("--seed", type=int, default=None,
                    help="Fester Zufallswert fuer reproduzierbare Ergebnisse (Standard: zufaellig)")
    ap.add_argument("--auras-ohne-kreatur", action="store_true",
                    help="Auras duerfen auch ohne eigene Kreatur auf dem Feld gespielt werden")
    ap.add_argument("--ohne-landcycling", action="store_true",
                    help="Landcycling nicht benutzen (Karten werden nur normal gespielt)")
    ap.add_argument("--landcycling-letzte-karte", action="store_true",
                    help="Landcycling auch dann, wenn die Karte die letzte Karte auf der Hand waere")
    ap.add_argument("--landcycling-runden", type=int, default=3,
                    help="Bis zu welcher Runde ein fehlender Landdrop per Landcycling gesichert wird")
    ap.add_argument("--landcycling-max-laender", type=int, default=6,
                    help="Cycling einer nicht spielbaren Karte nur bei weniger Laendern (Feld + Hand)")
    ap.add_argument("--ohne-mulligan", action="store_true",
                    help="Keine Mulligans: jede Starthand mit 7 Karten wird gespielt")
    ap.add_argument("--min-handkarten", type=int, default=5,
                    help="Faellt die Starthand durch Mulligans darunter, gilt das Spiel als verloren (Standard 5)")
    ap.add_argument("--ohne-jace", action="store_true",
                    help="Empower Jace nicht simulieren (die Zaehlung der Karten bleibt)")
    ap.add_argument("--curve-runden", type=int, default=6,
                    help="Bis zu welcher Runde die Curve-Auslastung berechnet wird")
    ap.add_argument("--schaden", type=int, default=20,
                    help="Gesamtschaden der Kreaturen, dessen erste Runde gemessen wird")
    ap.add_argument("--flood", type=int, default=11,
                    help="Ab wie vielen gezogenen Laendern (bis zur Maximalrunde) gilt man als geflutet")
    ap.add_argument("--gegner", action="append", metavar="DATEI", default=None,
                    help="Kampf simulieren gegen dieses Gegnerdeck (z. B. bad_creatures.txt aus dem Ordner enemydecks); mehrfach "
                         "angeben moeglich. Der Goldfish-Bericht bleibt unveraendert, der Kampf kommt in einen eigenen "
                         "Bericht (--kampf-ausgabe)")
    ap.add_argument("--bericht-server", action="store_true",
                    help="Bericht ueber einen lokalen Server zeigen (statt nur als Datei), damit 'Kampf simulieren' im "
                         "Bericht funktioniert; das Programm laeuft, bis es im Bericht beendet wird")
    ap.add_argument("--kampf-ausgabe", default="mtg_kampf.html", metavar="DATEI",
                    help="Name des Kampfberichts (Standard: mtg_kampf.html)")
    ap.add_argument("--kaempfe", type=int, default=500,
                    help="Kaempfe je Deck und Modus (On the Play / On the Draw) gegen jedes Gegnerdeck (Standard 500)")
    ap.add_argument("--kampf-runden", type=int, default=20,
                    help="Rundengrenze im Kampf; danach gilt das Spiel als unentschieden (Standard 20)")
    ap.add_argument("--ausgabe", "--html", dest="ausgabe", default="mtg_bericht.html", metavar="DATEI",
                    help="Name des HTML-Berichts (Standard: mtg_bericht.html)")
    ap.add_argument("--nicht-oeffnen", action="store_true",
                    help="HTML-Bericht nicht automatisch im Browser oeffnen")
    ap.add_argument("--lang", choices=("de", "en"), default="de",
                    help="Sprache von Bericht, Drafthelper, Setauswertung, Overlay und Konsole (de oder en, Standard de)")
    args = ap.parse_args(argv)
    if not args.deckfile and args.drafthelper is None and args.overlay is None and args.setauswertung is None \
            and not args.statistik_neu:
        ap.error("Bitte eine Deckliste angeben oder --drafthelper verwenden")
    return args
