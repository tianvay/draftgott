"""Erklaerseite "So funktioniert es": alle Regeln und Lesehilfen, getrennt von den Daten des Berichts.

Die Seite steht als zweite Ansicht in derselben HTML-Datei wie der Bericht (render_help_view) und fuer den Drafthelper
zusaetzlich als eigenstaendige Seite (render_help_page). Die Texte sind allgemein gehalten; die Werte eines Laufs
(Spiele, Runden, Schaden, Flood ...) stehen oben im Bericht. Die Abschnitte heissen wie im Bericht, mit "hiw-" davor.
"""
from components.cli import parse_args
from components.coverage import METRIC_ORDER
from components.html_base import HTML_CSS, esc
from components.i18n import dec, html_lang, t
from components.report_cards import AVAIL_GREEN, AVAIL_YELLOW
from components.report_sections import JACE_RULES, render_logic_section
from components.stats import TRAFFIC
from components import synergy

_D = parse_args(["deck.txt"])  # Standardwerte der Kommandozeile
# Abschnitte, die nur erscheinen, wenn der Bericht sie auch hat (z. B. Deck-Vergleich nur bei mehreren Decks)
CONDITIONAL = {"vergleich", "great", "mulligan", "jace", "farben", "landcycling", "ziehen", "surveil", "prepared",
               "splashkarten", "removal", "ramp", "friedhof"}


def _de(x):
    """Zahl mit deutschem Komma (6,0 -> "6", 3,5 -> "3,5")."""
    return dec(f"{x:g}")


def _ul(items):
    return '<ul class="ass">' + "".join(f"<li>{x}</li>" for x in items) + "</ul>"


def _p(text):
    return f"<p>{text}</p>"


def _panel(title, body):
    return f'<div class="panel" style="margin-top:12px"><b>{esc(title)}</b>{body}</div>'


def _sections():
    traffic = "; ".join(t("{mode} Runde {turn}: grün ab {g} %, gelb über {y} %", mode=("Draw" if d else "Play"),
                          turn=rd, g=g, y=y)
                        for d, tt in TRAFFIC.items() for rd, (g, y) in tt.items())
    return [
        ("vergleich", "Deck-Vergleich", _panel(t("Statistik"), _p(
            t("Jedes Deck wird unabhängig mit der eingestellten Zahl an Spielen pro Modus simuliert (<code>--sims</code>, "
            "Standard {sims}). Hinter den Werten steht das 95-%-Konfidenzintervall (±). Ein Unterschied (Δ) ist "
            "farbig, wenn er größer ist als der zufällige Fehler (|Δ| &gt; 1,96 × Standardfehler), grün bei besser und "
            "rot bei schlechter. Mit ≈ markierte Unterschiede sind nicht von Zufall zu trennen. PP = Prozentpunkte. Bei so "
            "vielen Kennzahlen sind einzelne zufällige Ausreißer zu erwarten, achte deshalb auf das Gesamtbild. Für eine "
            "höhere Genauigkeit hilft eine größere <code>--sims</code>-Zahl.", sims=_D.sims)))
         + _panel(t("Kartentypen im Vergleich"), _p(
             t("Eine Spalte je Deck, gezählt wie im Abschnitt Deck (siehe dort). Fett: Unterschied zwischen den Decks.")))),
        ("blick", "Auf einen Blick", _panel(t("Ampeln"), _ul([
            t("Ampel Zauber pro Runde – {traffic}.", traffic=traffic),
            t("Schnellster Lethal: grün bis Runde 5, gelb Runde 6–7, rot ab Runde 8."),
            t("Alle Farben bis Runde 3: grün ab {green} %, gelb ab {yellow} % (siehe Farbverfügbarkeit).",
              green=AVAIL_GREEN, yellow=AVAIL_YELLOW),
            t("Die Ampel bei „Zauber pro Runde“ rechnet mit der angezeigten ganzen Prozentzahl.")]))),
        ("deck", "Deck", _panel(t("Kartentypen"), _p(
            t("Gezählt werden Kopien. Artefakte und Verzauberungen ohne Kreaturen und Länder; eine Karte kann in mehreren "
            "Zeilen stehen (z. B. Artifact Enchantment). Länder gesamt enthält die Standardländer, „davon Nicht-Standard“ "
            "nur die übrigen. Σ Loyalty: Zahlenwerte von Empower Jace beim Zauber oder Betreten (ohne X, ohne Auslöser). "
            "Kartenfluss: Karten, die ziehen (auch Cycling), suchen (auch Landcycling), Surveil, Scry, Explore oder Mill "
            "haben; Mill getrennt nach „sich selbst“ und „Gegner möglich“ („target player“ zählt bei beiden). Es "
            "erscheinen nur Arten, die im Deck vorkommen. Auslöser wie „whenever you draw“ und Ziehen des Gegners zählen "
            "nicht, Empower Jace hat eine eigene Zeile. „Prepared (Karten)“: Karten, deren Zauberhälfte als Kopie "
            "gewirkt werden kann (nur, wenn solche Karten im Deck sind). Flash zählt nur bei bleibenden Karten, "
            "Deathtouch nur, wenn die Karte es selbst hat (nicht, wenn sie es verleiht).")))
         + _panel(t("Mana-Kurve nach Farben"), _ul([
             t("Gezählt werden Nichtland-Karten nach Manawert (aufgerundet ab ,5; 7 und mehr zusammen)."),
             t("<b>Mehrfarbige gesondert:</b> Jede Karte steht genau einmal im Diagramm, die Balkenhöhe ist die "
             "Kartenzahl. Karten mit mehreren Farben bilden das goldene Segment „Mehrfarbig“."),
             t("<b>Je Farbe:</b> Eine mehrfarbige Karte zählt bei jeder ihrer Farben (eine Grün/Weiß-Karte bei Grün und bei "
             "Weiß). Die Balken ergeben deshalb zusammen mehr als die Kartenzahl."),
             t("Darunter: Zahl der Karten, davon mehrfarbig und farblos, und die vorkommenden Farbkombinationen.")]))
         + _panel(t("Farbverteilung"), _p(
             t("Symbole = Farbsymbole, die diese Karten zwingend verlangen, mal Kopien ({R}{R} zählt 2, Hybrid nicht) · "
             "Karten = Nichtland-Karten, die die Farbe brauchen (in jedem Zahlungsweg; Hybrid zählt nicht) · Quellen = "
             "Länder, die sie erzeugen. Ein Land mit mehreren Farben zählt für jede davon. Ø pünktlich: Chance, dass "
             "bis zur Runde = Manawert (mindestens Runde 1, auf dem Play) genug Quellen für die Farbsymbole der Karte "
             "gezogen sind, gerechnet mit Hypergeometrie und gemittelt über die Karten der Farbe. Bei mehrfarbigen "
             "Karten werden die Farben multipliziert, die Gesamtzahl der Länder spielt keine Rolle. Ampel wie bei der "
             "Farbverfügbarkeit: grün ab {green} %, gelb ab {yellow} %. „Am knappsten“: die Karte der Farbe mit der "
             "niedrigsten Chance. Dieselbe Rechnung nutzt „Länder empfehlen“ im Drafthelper.",
             green=AVAIL_GREEN, yellow=AVAIL_YELLOW)))
         + _panel(t("Kartentabelle und Bereiche"), _p(
             t("Beim Vergleich mit gemeinsamem Kern (Drafthelper oder <code>--core</code>) steht jede Karte mit ihrem "
             "Bereich (Core, Splash, NoSplash …). Mengen werden je Bereich getrennt geführt; blass dargestellte Bereiche "
             "gehören nur zu einer anderen Variante.")))),
        ("removal", "Removal", _panel(t("Bewertung"), _ul([
             t("Jede Karte bekommt Punkte für ihren besten Removal-Effekt (alle Seiten, bei modalen Karten der beste "
             "Modus); 1 Punkt = entfernt jede gegnerische Kreatur zuverlässig. Σ Removal-Punkte ist die Summe über "
             "alle Kopien und liest sich wie „so viele harte Removals“."),
             t("<b>Hart</b> (destroy/exile target creature) 1,0 · <b>Massenremoval</b> 1,0 · <b>Exil bis verlassen</b> "
             "(„until … leaves the battlefield“) 0,9 · <b>Edikt</b> (Gegner opfert) 0,7, mit „greatest mana value“ "
             "0,9 · <b>Toughness 0</b> (z. B. „has base power and toughness 0/0“; die Kreatur stirbt mit 0 "
             "Toughness) 0,7 · <b>Lock</b>-Aura (enttappt nicht, kann nicht angreifen) 0,7 · <b>Fight</b> 0,5 · "
             "<b>Bounce</b> 0,3 · zurück in die <b>Bibliothek</b> (der Besitzer wählt oben oder unten) 0,3."),
             t("<b>Schaden und −X/−X</b> nach Höhe: 1 → 0,2 · 2 → 0,4 · 3 → 0,6 · 4 → 0,8 · ab 5 → 0,9; X oder "
             "„damage equal to …“ 0,5. −X/−0 zählt nicht."),
             t("<b>Bedingt</b> (Bedingung am Ziel wie Manawert, Toughness, Flying, Farbe, oder eigenes Opfer): höchstens "
             "0,5. <b>Fähigkeit</b> (bezahlbare Fähigkeit oder Planeswalker-Fähigkeit) und <b>Auslöser</b> (außer "
             "beim Betreten): halber Wert."),
             t("Nicht gezählt: Counterspells, Kampftricks, Schaden nur an Spieler und verliehene Fähigkeiten in "
             "Anführungszeichen."),
             t("Ampel: grün ab 4, gelb ab 2,5 Punkten bei 40 Karten, bei anderer Kartenzahl anteilig. Richtwert für "
             "Limited: etwa 4 bis 6 Removal-Karten."),
             t("Die Tabelle zeigt jede erkannte Karte mit Art, Punkten je Karte, Summe und der erkannten Textstelle zur "
             "Kontrolle. Der Goldfish nutzt den Score nicht (es gibt keinen Gegner); im Kampfmodell wirken die "
             "Removal-Effekte selbst, der Score dient dort nur bei Gleichstand (z. B. welche Karte aus der Hand des "
             "Gegners gewählt wird).")]))),
        ("synergie", "Synergie", _panel(t("Geber und Nehmer"), _ul([
            t("Jede Karte bekommt aus ihren erkannten Effekten Tags: was sie dem Deck <b>gibt</b> (Lebensgewinn, "
            "+1/+1-Marken, Buffs, Schutz wie Hexproof oder Indestructible, Nichtkreatur-Zauber, Surveil, Token, "
            "Opfer-Möglichkeiten, Artefakte, Kreaturtypen …) und wovon sie <b>profitiert</b> (z. B. „Whenever you gain "
            "life“, Prowess, Belohnungen für Marken, Sterbe- und Opfer-Auslöser, Friedhofsgröße)."),
            t("<b>Aktive Synergie</b>: Wer Marken, Buffs oder Schutz verteilt, profitiert von Kreaturen im Deck; Auren und "
            "Ausrüstung profitieren von guten Trägern (Flying, Menace, Trample, Double Strike, Hexproof, Ward, "
            "unblockbar) und von Schutz."),
            t("<b>Erfüllung</b> je Nehmer = 1 − (1 − p)<sup>k</sup>, k = Geber-Einheiten im Deck ohne die eigene Kopie, p "
            "je Ressource (z. B. Lebensgewinn 0,2, Nichtkreatur-Zauber 0,12, Kreaturen 0,08). Der dritte Geber bringt "
            "also weniger als der erste. Punkte = Gewicht des Nehmers × Erfüllung × Anzahl; die Summe ist der "
            "Synergiewert. Ampel je 40 Karten: grün ab {green}, gelb ab {yellow}.",
            green=dec(f"{synergy.GREEN:g}"), yellow=dec(f"{synergy.YELLOW:g}")),
            t("<b>Ohne Partner</b>: Nehmer, deren Erfüllung unter {orphan} liegt – die Karte wartet im Deck auf "
              "Karten, die es kaum gibt.", orphan=f"{synergy.ORPHAN:.0%}"),
            t("Länder zählen nicht (Landfall ist in jedem Deck erfüllt). Im Live-Draft kommt der Zuwachs des "
            "Synergiewerts durch eine Pack-Karte (× 2, höchstens + 2) zu ihren Punkten.")]))),
        ("friedhof", "Friedhof", _panel(t("Friedhof-Score"), _ul([
            t("Jede Karte bekommt Punkte für ihre beste Nutzung des Friedhofs (aus dem Kartentext): <b>Zweitverwertung</b> "
            "1,0 (die Karte selbst noch einmal: Flashback, Escape, Unearth, Disturb, Jump-start, Retrace, „return this "
            "card from your graveyard“, Fähigkeiten mit „exile this card from your graveyard“) · <b>Zurückholen</b> "
            "0,7 (andere Karten aus dem Friedhof auf die Hand oder ins Spiel) · <b>Ressource</b> 0,5 (Wert hängt vom "
            "Friedhof ab, Threshold, Delve, andere Karten aus dem Friedhof exilieren)."),
            t("<b>Enabler</b> füllen den eigenen Friedhof (Mill, Surveil, Abwerfen, Cycling und Landcycling, „into your "
            "graveyard“); sie werden gezählt, haben aber keine Punkte."),
            t("Der Goldfish wirkt keine Karten aus dem Friedhof (außer Campus Crier: Empower aus dem Friedhof); der Score "
            "bewertet nur. Im Kampfmodell kommen Karten aus dem Friedhof zurück (Flashback, „return this card“, Phoenix, "
            "Reanimation, Fähigkeiten aus dem Friedhof).")]))
         + _panel(t("Friedhof in der Simulation"), _ul([
             t("In den Friedhof kommen gewirkte Instants und Sorceries (Prepared-Kopien nicht), gelandcycelte Karten "
             "und Karten, die Surveil oder Mill ablegt (Karten oder Jace). Kreaturen sterben im Goldfish nicht (kein Kampf "
             "mit Blockern); im Kampfmodell kommen gestorbene Kreaturen in den Friedhof."),
             t("Gezählt wird mit den Manakosten der Karte; eine gelandcycelte 6-Mana-Kreatur zählt also 6."),
             t("„Ø höchster Manawert“ ist für Karten wie Hapatra wichtig: X = höchster Manawert im Friedhof, wenn sie ins "
             "Spiel kommt (Ø X und wie oft X ≥ 3 bzw. ≥ 5).")]))),
        ("great", "Great in this deck!", _panel(t("Was hier steht"), _ul([
            t("Karten mit der Kategorie ♛ Matchwinner, ★ Splashworthy oder MustPlay aus dem Drafthelper, mit Bereich, Kosten und "
            "Eigenschaften."),
            t("„Fehlt in diesem Deck“: eine MustPlay-Karte fehlt (in jeder Variante) oder eine Matchwinner- oder Splashworthy-Karte fehlt "
            "in der Splash-Variante. Für den Deckvorschlag gibt es diesen Hinweis nicht, weil er nach Farbregeln gebaut "
            "wird."),
            t("„NeverPlay-Karten im Deck“: Karten, die als NeverPlay gekennzeichnet und trotzdem im Deck sind.")]))),
        ("abdeckung", "Modell-Abdeckung", _panel(t("Wie die Karten eingeordnet werden"), _ul([
            t("Die Erkennung arbeitet über den Kartentext von Scryfall und sortiert nur grob, weil Magic dasselbe oft "
            "unterschiedlich formuliert. Status jeder gelisteten Karte: „To Do: Noch nicht implementiert“."),
            t("Nicht gemeldet wird, was die Simulation abbildet: aufgedrucktes Haste und Defender, Landcycling, die "
            "Bedingungen getappter Länder, Empower Jace mit festem Wert, Draw-Zauber und Surveil mit fester Zahl, "
            "Prepared-Zauberhälften als Kopie (deren übrige Effekte stehen mit ihrer eigenen Kategorie da), Manaquellen "
            "und Treasure, Schaden an den Gegner beim Wirken oder Betreten, +1/+1-Marken und Pumps bis Rundenende beim "
            "Wirken oder Betreten, Landfall-Schaden und -Marken, Marken am Rundenende ohne Zauber (Edgar) und bei "
            "Loyalty (Tethermage), Kostensenkung (Geist of Saint Thalia, Ghalta, Wrath of the Bloodmane, Traxos) sowie "
            "Kampf-Schlüsselwörter ohne Gegner. Außerdem jede Zeile, die das Kartenmodell erkennt (Goldfish und/oder "
            "Kampfmodell, z. B. Removal, Token, Lebensgewinn, Planeswalker): Dafür wird die Karte nur mit dieser Zeile "
            "geparst; bei teilweise erkannten Zeilen bleibt der offene Rest stehen. Zeilen, deren Modell erst aus der "
            "ganzen Karte entsteht (z. B. der Bonus einer Ausrüstung zusammen mit ihren Equip-Kosten), gelten ebenfalls "
            "als abgedeckt."),
            t("Bewusst nicht (vollständig) modelliert und deshalb nicht gemeldet: Theorist's Proxy (opfert sich nie), "
            "Marwyn, the Preserver (Hexproof für Länder), Paradox Shaper ({2}: Karte unter die Bibliothek), Sphinx's "
            "Approach (fünf Exemplare), Winter, Team Player (Convoke), Tam, the Possibility (Proliferate) und "
            "Extrapolate the Impossible (Karten von außerhalb des Spiels)."),
            t("Kategorien: Tokens erzeugen, Direkter Schaden, Zählmarken / Stärkebonus, Haste verleihen, Mana außer "
            "Ländern, Kartenfluss, Kostensenkung / Convoke, Zweitverwertung (Friedhof), Timing (Flash), Zusatzkosten, "
            "Prepared-Zauberhälfte, Planeswalker-Fähigkeit, Defender-Ausnahme, Interaktion mit dem Gegner, "
            "Lebensgewinn, Schlüsselwort verleihen und Empower-Sonderfälle. Was sich nicht einordnen lässt, heißt "
            "„Unbekannter Effekt“."),
            t("Betroffene Kennzahl: {metrics}. Bei „unklar“ ist nicht bekannt, was genau fehlt. "
              "Mit der Maus über der Kategorie steht die Textstelle.", metrics=", ".join(t(m) for m in METRIC_ORDER))]))),
        ("mulligan", "Mulligan", _panel(t("Wann es einen Mulligan gibt"), _ul([
            t("<b>Farben:</b> Mit den Farben der Länder auf der Starthand ist keine Karte spielbar (nur die Farben zählen, "
            "nicht die Manamenge)."),
            t("<b>Zu viele Länder:</b> 6 oder mehr Länder auf der Starthand."),
            t("<b>Zu wenige Länder:</b> Höchstens 2 Länder und weniger als 3 Karten, die sich mit diesen Ländern bezahlen "
            "lassen (Manawert und Farben). Zwei Länder plus lauter 1- und 2-Mana-Karten werden also behalten.")])
            + _p(t("Bei einem Mulligan wird das Deck neu gemischt, es werden wieder 7 Karten gezogen und je Mulligan "
                 "eine Karte unter die Bibliothek gelegt (London-Mulligan): behalten wird die Auswahl ohne "
                 "Mulligan-Grund, dann mit dem Länderanteil am nächsten am Deck, dann mit den meisten bezahlbaren "
                 "Karten, dann mit den geringsten Manakosten. "
                 "Ausnahme Landcycling: eine Hand mit 6 oder 7 Karten, mindestens 2 Ländern, einer Karte mit Basic Landcycling und einer anderen Nichtland-Karte bis Manawert 3 wird trotz zu weniger Länder oder fehlender Farben behalten. "
                 "Dieselben Regeln gelten für jede neue Hand. Fällt die Hand unter die Mindestzahl "
                 "(<code>--min-handkarten</code>, Standard {min_hand}), gilt das Spiel als verloren; auch eine "
                 "Hand dieser Größe, die einen Mulligan auslösen würde, zählt als verloren. Mit <code>--ohne-mulligan"
                 "</code> wird jede 7-Karten-Hand gespielt.", min_hand=_D.min_handkarten)))
         + _panel(t("Wie die Tabellen zu lesen sind"), _ul([
             t("Gründe: Anteil aller ersten 7-Karten-Hände. Die Gründe können zusammen auftreten, ihre Summe kann deshalb "
             "über dem Gesamtwert liegen."),
             t("Startgröße: Prozent aller ausgeteilten Starthände. Verlorene Spiele werden nicht gespielt und fließen nicht "
             "in die übrigen Zahlen ein: Alle anderen Auswertungen beruhen auf den gespielten Spielen nach dem "
             "Mulligan.")]))),
        ("jace", "Jace & Planeswalker", _panel(t("Modellregeln"), _ul([esc(t(r)) for r in JACE_RULES]))
         + _panel(t("Wie die Tabellen zu lesen sind"), _ul([
             t("Σ Empower: bei wiederkehrenden Karten der Wert je Auslösung beziehungsweise je Aktivierung. Eine Karte "
             "kann in mehreren Kategorien stehen, die Summe der Zeilen ist deshalb größer als „gesamt“."),
             t("„Bis die Hand leer ist“: gezählt bis zum ersten Rundenende ohne Karten auf der Hand (nach dem Zaubern und "
             "einer möglichen Jace-Aktivierung); wird die Hand nie leer, zählt der ganze Beobachtungszeitraum."),
             t("„Aktivierungen“ zählen das Ziehen (−3): Ø Aktivierungen ist zugleich die Zahl der durch Jace gezogenen "
             "Karten. „Ø Surveil“ zählt die −1-Aktivierungen, „Ø Länder in den Friedhof“ die dabei abgelegten Länder. "
             "„Ø Empower“ ist die erhaltene Loyalty insgesamt."),
             t("Mit <code>--ohne-jace</code> wird Jace nicht simuliert, die Karten werden nur gezählt.")]))),
        ("zauber", "Zauber pro Runde", _panel(t("Bedeutung"), _p(
            t("Anteil der Spiele, in denen in dieser Runde mindestens ein Zauber gespielt wird (Farben beachtet, gespielte "
              "Karten sind weg). Ausgewertet bis zur eingestellten Runde (<code>--turns</code>, Standard "
              "{turns}).", turns=_D.turns)))),
        ("kreaturen", "Kreaturen nach Runde X", _panel(t("Bedeutung"), _p(
            t("Durchschnitt auf dem Feld nach der Auswertungsrunde (<code>--turns</code>), aufgedruckte Werte plus "
            "dauerhafte +1/+1-Marken, ohne Auras und Boni bis Rundenende.")))),
        ("screw", "Mana Screw & Flood", _panel(t("Bedeutung"), _ul([
            t("<b>Mana Screw:</b> nach der Auswertungsrunde (<code>--turns</code>) weniger Länder auf dem Feld als die "
            "Rundenzahl oder, bei mehrfarbigen Decks, keine zwei Farben."),
            t("<b>Flood:</b> bis zum Ende der Beobachtung (<code>--max-runden</code>, Standard "
              "{max_runden}) mindestens so viele Länder gezogen wie mit <code>--flood</code> eingestellt "
              "(Standard {flood}), die Starthand eingerechnet.", max_runden=_D.max_runden, flood=_D.flood)]))),
        ("farben", "Farbverfügbarkeit", _panel(t("Bedeutung"), _ul([
            t("Quelle = Land auf dem Feld nach dem Landdrop der Runde (auch getappt), das die Farbe erzeugen kann, oder "
            "eine Manaquelle außer Ländern, die in der Runde Mana liefert (Kreaturen ab der Runde nach dem Wirken, "
            "Artefakte sofort; Treasure zählen nicht). Eine Quelle mit mehreren Farben zählt für jede davon."),
            t("Runde 3: von jeder Farbe, die Karten im Deck zwingend brauchen, mindestens eine Quelle (alle zusammen und "
            "jede einzeln)."),
            t("Mehrfach-Symbole: Für jede Farbe und Symbolzahl (WW, GGGG …), die eine Karte zwingend verlangt, zählt die "
            "günstigste Karte. Gemessen wird, wie oft bis zur Runde = ihr Manawert mindestens so viele Quellen der Farbe "
            "liegen, z. B. {2}{W}{W}{B} → 2 Quellen Weiß bis Runde 5, {G}{G}{G}{G} → 4 Quellen Grün bis Runde 4. Hybrid "
            "zählt nicht; liegt die Runde nach dem Ende der Beobachtung, steht „–“."),
            t("Ampel: grün ab {green} %, gelb ab {yellow} %, sonst rot. Mehr zu Manaquellen im Abschnitt Ramp.",
              green=AVAIL_GREEN, yellow=AVAIL_YELLOW)]))),
        ("splashkarten", "Splash-Karten", _panel(t("Bedeutung"), _ul([
            t("Nur im Bericht des Drafthelpers, für die Splash-Variante: alle Nichtland-Karten der Gruppe Splash."),
            t("<b>Gezogen:</b> Anteil der Spiele, in denen die Karte bis zum Ende der Beobachtung auf die Hand kommt "
            "(Starthand eingerechnet)."),
            t("<b>Spielbar, wenn gezogen:</b> Anteil dieser Spiele, in denen ihre Kosten irgendwann nach dem Landdrop mit "
            "den untappten Ländern bezahlbar sind (Farben und Manamenge; andere Zauber derselben Runde zählen nicht "
            "dagegen). Ampel wie bei der Farbverfügbarkeit: grün ab {green} %, gelb ab {yellow} %.",
              green=AVAIL_GREEN, yellow=AVAIL_YELLOW),
            t("<b>Pünktlich:</b> bezahlbar spätestens in der Runde = Manawert, oder sofort, wenn sie erst später auf die "
            "Hand kommt. Zum Vergleich mit „Ø pünktlich“ in der Farbverteilung, die nur rechnet und Mulligan, getappte "
            "Länder, Landcycling, Draw und Surveil nicht kennt."),
            t("<b>Ø Wartezeit:</b> Runden zwischen „auf der Hand“ und „erstmals bezahlbar“ (0 = sofort)."),
            t("<b>Gewirkt, wenn gezogen:</b> Anteil, in dem die Simulation die Karte tatsächlich gespielt hat (sie kann "
            "auch zugunsten anderer Karten warten)."),
            t("Die Messung verändert den Spielablauf nicht.")]))),
        ("curve", "Curve-Auslastung", _panel(t("Bedeutung"), _p(
            t("Ausgegebenes geteilt durch verfügbares Mana je Runde (bis <code>--curve-runden</code>, Standard "
            "{curve_runden}). Verfügbar ist das Mana aus Ländern und aus Manaquellen außer Ländern (Manakreaturen, "
            "Artefakte, genutzte Treasure, siehe Ramp). Ausgegeben zählt das tatsächlich bezahlte Mana: Kostensenkung "
            "nach den Kreaturen, die zu Rundenbeginn auf dem Feld liegen (Geist of Saint Thalia, Ghalta nach höchster "
            "Power bzw. Toughness, Wrath of the Bloodmane mit legendärer Kreatur; Traxos, wenn in derselben Runde ein "
            "Nichtkreatur-Zauber gewirkt wird), macht Karten billiger, ihr Manawert bleibt gleich. Ein "
            "Rechenbeispiel steht unter Spiellogik.", curve_runden=_D.curve_runden)))),
        ("schaden", "Schaden durch Kreaturen", _panel(t("Bedeutung"), _p(
            t("Erste Runde, in der der Gesamtschaden das Ziel erreicht (<code>--schaden</code>, Standard "
            "{schaden}). Ø und Median nur über Spiele, in denen es bis zum Ende der Beobachtung eintritt. Alle "
            "Kreaturen greifen jede Runde an, Einsatzverzögerung außer Haste, Defender greift nie an (außer mit Ghalta the Immovable, der auch Schaden nach Toughness gibt), keine Blocker oder "
            "Removal. Schaden = Power plus +1/+1-Marken und Pumps dieser Runde, dazu Schaden an den Gegner aus Zaubern, "
            "beim Betreten und durch Landfall (auch „any target“ zählt als Schaden an den Gegner). Marken und Pumps gehen "
            "an die stärkste Kreatur, die in dieser Runde angreift; dauerhafte Marken ohne Angreifer an die stärkste "
            "Kreatur, Pumps ohne Angreifer verpuffen. Modale Karten: der Modus mit dem meisten Schaden, bei Gleichstand "
            "der mit dauerhaften Marken. Edgar bekommt am Rundenende 2 Marken, wenn kein Zauber gewirkt wurde; "
            "Inspired Tethermage 1 Marke je Empower Jace.", schaden=_D.schaden)))),
        ("lethal", "Schnellster Lethal", _panel(t("Bedeutung"), _p(
            t("Das schnellste aller simulierten Spiele, bei gleicher Runde das mit mehr Schaden, mit Starthand und "
            "Rundenprotokoll. Ein Glücksfall, kein Erwartungswert – die typische Runde steht unter „Schaden durch "
            "Kreaturen“.")))),
        ("landcycling", "Landcycling", _panel(t("Regeln"), _ul([
            t("<b>Land fehlt:</b> Ist in den ersten Runden (bis <code>--landcycling-runden</code>, Standard "
              "{landcycling_runden}) kein Land auf der Hand, wird ein Landcycler gecycelt, damit der Landdrop klappt.",
              landcycling_runden=_D.landcycling_runden),
            t("<b>Karte nicht spielbar:</b> Mit übrigem Mana wird eine Karte gecycelt, die in dieser Runde nicht "
            "spielbar ist, wenn es sich lohnt (Vorausschau auf die nächste Runde), und nur unter so vielen Ländern auf "
            "Feld und Hand wie eingestellt (<code>--landcycling-max-laender</code>, Standard "
            "{max_laender}).", max_laender=_D.landcycling_max_laender),
            t("Die letzte Karte auf der Hand wird nicht gecycelt (außer mit <code>--landcycling-letzte-karte</code>); "
            "mit <code>--ohne-landcycling</code> wird nie gecycelt."),
            t("„Nicht-Land-Chance“: wie stark das Cycling die Chance erhöht, im nächsten Zug ein Nicht-Land zu ziehen.")]))),
        ("ziehen", "Draw-Zauber", _panel(t("Regeln"), _ul([
            t("Modelliert sind Instants und Sorceries, die mit „Draw N cards.“ beginnen (N fest), und bleibende Karten "
            "mit „When this … enters, draw N cards.“. Steht in der Zeile noch mehr (z. B. Schaden), bleibt dieser Teil "
            "in der Modell-Abdeckung."),
            t("Nicht modelliert: modale Karten („Choose one“), Ziehen mit Abwerfen, „you may“, X-Werte, Auslöser wie "
            "„whenever you gain life“ und bezahlbare Fähigkeiten. Sie stehen in der Modell-Abdeckung."),
            t("Draw-Zauber werden bei der Auswahl nicht bevorzugt, sondern nach denselben Auswahlregeln wie alle Zauber "
            "gewählt. Nach dem Zaubern kommen die Karten sofort auf die Hand: Ist der Landdrop noch frei, wird ein "
            "gezogenes Land gelegt, und mit dem übrigen Mana wird weiter gezaubert (auch weitere Draw-Zauber)."),
            t("„Ø zusätzlich gezogen“: Karten pro Spiel durch Draw-Zauber, bis zum Ende der Beobachtung. „Ø gleich "
            "genutzt“: danach im selben Zug zusätzlich gelegte Länder und gewirkte Zauber.")]))),
        ("surveil", "Surveil durch Karten", _panel(t("Regeln"), _ul([
            t("Modelliert ist „Surveil N.“ als eigener Satz in Instants und Sorceries sowie „When this … enters, surveil "
            "N.“ bei Kreaturen, anderen bleibenden Karten und Ländern (N fest). Der Rest einer Zeile (z. B. Exil) bleibt "
            "in der Modell-Abdeckung."),
            t("Surveil der Prepared-Kopie zählt wie bei anderen Zaubern. Nicht modelliert im Goldfish: Auslöser wie "
            "„whenever another creature enters“, bezahlbare Fähigkeiten, modale Karten und X-Werte (das Kampfmodell "
            "kennt die Auslöser)."),
            t("Zeitpunkt: nach dem Zaubern der Runde, zuerst das gelegte Land, dann die Zauber in der Reihenfolge des "
            "Wirkens."),
            t("Entscheidung wie bei Jace: Ein Land bleibt oben, solange für die teuerste Karte auf der Hand Länder fehlen "
            "(Länder auf dem Feld und auf der Hand zählen); sonst kommt es in den Friedhof. Zauber bleiben immer oben."),
            t("Surveils durch Jace stehen im Abschnitt Jace & Planeswalker und zählen hier nicht mit.")]))),
        ("prepared", "Prepared", _panel(t("Regeln"), _ul([
            t("Karten mit Zauberhälfte (Layout „prepare“): Die Kreatur wird normal gewirkt. Kommt sie prepared ins Spiel "
            "(„enters prepared“), darf eine Kopie ihres Zaubers gewirkt werden; danach ist sie nicht mehr prepared. Steht "
            "„at the beginning of your upkeep … becomes prepared“ auf der Karte, wird sie in jedem eigenen Upkeep "
            "wieder prepared."),
            t("Die Kopie kostet die Manakosten der Zauberhälfte, verbraucht keine Handkarte und zählt als gespielter "
            "Zauber und als ausgegebenes Mana. Sie wird mit den übrigen Zaubern nach denselben Auswahlregeln gewählt; "
            "bei Gleichstand kommt zuerst die Handkarte (die Kopie bleibt verfügbar)."),
            t("Auch in der Runde, in der die Kreatur ins Spiel kommt, wird die Kopie mit dem übrigen Mana gewirkt."),
            t("Effekte der Kopie wie bei anderen Zaubern: Draw N, Surveil N, Empower Jace, Schaden an den Gegner, Marken "
            "und Pumps, Mill und Heartwood-Token. Kreatur-Token und Loot der Kopie wirken nur im Kampfmodell."),
            t("Prepared-Karten mit anderem Wortlaut werden nicht als Kopie gewirkt und stehen in der Modell-Abdeckung als "
            "„Prepared-Zauberhälfte“.")]))),
        ("ramp", "Ramp", _panel(t("Regeln"), _ul([
            t("Manaquellen außer Ländern: bleibende Karten mit „{T}: Add …“ ohne Zusatzkosten, also eine Farbe "
            "(„Add {G}“), eine Auswahl („Add {R} or {G}“), jede Farbe („one mana of any color“) oder mehrere Mana "
            "(„Add {C}{C}“). Sie zählen wie zusätzliche Länder."),
            t("Kreaturen liefern Mana ab der Runde nach dem Wirken (außer mit Haste), Artefakte und Verzauberungen sofort; "
            "kommen sie in dieser Runde ins Spiel, wird mit ihrem Mana noch weiter gezaubert."),
            t("Wird das Mana einer Kreatur gebraucht, ist sie getappt und greift nicht an. Zuerst werden Länder, "
            "Artefakte und Treasure genutzt, dann die Kreaturen mit der kleinsten Power."),
            t("Treasure (aus „When … enters, create a Treasure token“ oder einem Zauber): bleibt liegen und wird nur "
            "geopfert, wenn er in einer Runde mehr Mana in Zauber bringt; ein Treasure gibt einmal ein Mana "
            "beliebiger Farbe."),
            t("Heartwood-Token (aus Zaubern und beim Betreten) sind Artefakte und liefern sofort Mana; Mana aus "
            "verliehenen Jace-Fähigkeiten zählt in der Runde, in der es genutzt wird. Mana echter Planeswalker und "
            "Heartwood beim Sterben gibt es nur im Kampfmodell."),
            t("Nicht modelliert im Goldfish: Fähigkeiten mit Zusatzkosten („{1}, {T}: Add …“), Mana durch Opfern außer "
            "Treasure, Rituale und Treasure aus anderen Auslösern."),
            t("„Spiele mit Ramp“: mindestens eine Runde mit Mana aus solchen Quellen; „Ø zusätzliches Mana“: Mana aus "
            "Manaquellen und genutzten Treasure je Runde; „Ø Angriffe ausgelassen“: Kreaturen, die für Mana getappt "
            "wurden und sonst hätten angreifen können."),
            t("Mana Screw und Flood zählen weiter nur Länder; die Farbverfügbarkeit zählt Manaquellen mit.")]))),
        ("tempo", "Tempo", _panel(t("Bedeutung"), _p(
            t("Ø und Median nur über Spiele, in denen das Ereignis bis zum Ende der Beobachtung eintritt. Top Card: die "
            "Karte(n) mit dem höchsten Manawert; gezählt wird die erste Runde, in der sie spielbar wäre.")))),
        ("logik", "Spiellogik", render_logic_section(True)),
        ("annahmen", "Modellannahmen", _panel(t("Annahmen"), _ul([
            t("Starthand 7 Karten mit Mulligan-Regeln (siehe Mulligan); jede Runde ziehen (On the Play erst ab Runde 2), "
            "ein Land legen, zaubern."),
            t("Jede Nichtland-Karte wird gespielt, sobald sie bezahlbar ist; pro Runde wird möglichst viel Mana "
            "ausgegeben."),
            t("Farben, Hybrid- und Phyrexian-Mana werden beachtet; Manaquellen außer Ländern und Treasure siehe Ramp."),
            t("Länder, die getappt ins Spiel kommen, werden aus dem Kartentext erkannt; Shock-Länder zahlen die 2 Leben. "
            "Länder mit Planeswalker-Bedingung kommen untapped, wenn ein Planeswalker liegt; wenn möglich wird dafür "
            "zuerst ein Zauber gewirkt, der einen Planeswalker erschafft. „Behold a Jace“ gilt auch mit einer "
            "Jace-Karte auf der Hand."),
            t("Auras werden nur mit eigener Kreatur gespielt (außer mit <code>--auras-ohne-kreatur</code>)."),
            t("Kreaturen: aufgedruckte Power/Toughness plus +1/+1-Marken, Einsatzverzögerung außer Haste, Defender greift nie an (außer mit Ghalta the Immovable, der auch Schaden nach Toughness gibt), keine "
            "Blocker oder Removal."),
            t("Landcycling, Empower Jace, Draw-Zauber, Surveil durch Karten und Prepared: Regeln in den jeweiligen "
            "Abschnitten."),
            t("Was die Simulation nicht abbildet, zeigt der Abschnitt Modell-Abdeckung je Deck."),
            t("Diese Annahmen gelten für den Goldfish (ohne Gegner). Das Kampfmodell spielt gegen ein Gegnerdeck mit "
            "Blockern, Removal, Instants und Planeswalkern; seine Regeln stehen im Kampfbericht.")]))),
        ("drafthelper", "Drafthelper", _drafthelper_help()),
        ("live", "Live-Draft", _live_help()),
    ]


def _live_help():
    return (
        _panel(t("Start"), _ul([
            t("Menüpunkt <b>3</b> in <code>draftgott.bat</code> oder <code>python mtg_sim.py --drafthelper "
            "_livedraft.txt --live</code>. Der Drafthelper liest das Protokoll von MTG Arena mit "
            "(<code>Player.log</code> unter <code>AppData/LocalLow/Wizards Of The Coast/MTGA</code>, anderer Pfad mit "
            "<code>--arena-log DATEI</code>). Gelesen wird nur diese Datei, das Spiel selbst wird nicht berührt."),
            t("In Arena muss unter Optionen → Konto „Detailed Logs (Plugin Support)“ eingeschaltet sein (danach Arena "
            "neu starten)."),
            t("Die Kartennamen kommen aus Arenas eigener Kartendatenbank (im Installationsordner), sonst aus Scryfall."),
            t("Jeder Pick landet sofort in der Kartenpool-Datei (<code>_livedraft.txt</code>, Format wie der "
            "Deck-Export von Arena); die Seite lädt danach neu und zeigt den Pool wie gewohnt. Ein neuer Draft "
            "beginnt die Datei von vorn. Auch ein schon laufender Draft wird beim Start nachgelesen.")]))
        + _panel(t("Aktuelles Pack"), _ul([
            t("Oben auf der Seite steht das Pack, aus dem du gerade wählst, als Rangliste. Punkte je Karte: Kategorie "
            "(♛ Matchwinner 5, ★ Splashworthy 4, MustPlay 3, ohne Kategorie 1,5, Filler 1) + 3, wenn die Karte dem Archetyp "
            "zugeordnet ist (grün hervorgehoben, „passt zu …“), + 4, wenn er ihr bester Archetyp ist (lila, "
            "pulsierender Rand, „am besten in …“), sonst + 1, wenn ihre Farben in den Farben des "
            "Archetyps liegen (hellgrün). NeverPlay hat immer 0 Punkte."),
            t("<b>Synergie</b>: Dazu kommt, wie viel die Karte den Synergiewert deiner Picks erhöht (bis + 2, „Synergie "
            "+ … mit …“ unter der Karte, im Seitenfenster „Syn+“). Mit erkanntem Archetyp zählen nur Picks in seinen "
            "Farben, und nur bei Karten, die in ihn passen (seine Farben, ihm zugeordnet oder farblos); bei "
            "anderen steht die Synergie nur da. Synergie heißt: Eine Karte profitiert von anderen (Lebensgewinn-Auslöser und Lebensgewinn, Prowess "
            "und Nichtkreatur-Zauber, Marken-Belohnungen und Marken, Auren und Ausrüstung mit fliegenden oder "
            "geschützten Trägern, Marken und Buffs verteilen mit genug Kreaturen, Kreaturtypen …). Der Bericht hat "
            "dazu den Abschnitt „Synergie“."),
            t("<b>Top-Pick</b>: Eine Karte ab MustPlay, deren bester Archetyp dein Archetyp ist (erkannt oder selbst "
            "gewählt) oder bei der du nahe dran bist (ihr bester Archetyp hat Punkte und liegt höchstens 3 Punkte "
            "hinter dem führenden), steht lila und pulsierend oben im Live-Bereich („◆ Top-Pick: …“) und blinkend "
            "oben im Seitenfenster, auch im minimierten Kasten."),
            t("Kategorie und Archetypen lassen sich direkt an den Pack-Karten festlegen; das gilt sofort."),
            t("Pick Two: beide gewählten Karten zählen als Picks.")]))
        + _panel(t("Kennzahlen der Picks"), _ul([
            t("Im Live-Bereich und im Seitenfenster stehen zu den bisherigen Picks: Kreaturen, Removal (Karten und "
            "Removal-Punkte wie im Bericht) und Kartenfluss (Karten, die ziehen, suchen, surveilen, scrien oder "
            "explorieren). Ist ein Archetyp erkannt, dieselben Zahlen noch einmal nur für Karten in seinen Farben "
            "(farblose zählen mit)."),
            t("Pack-Karten mit Removal tragen ihre Removal-Punkte (im Seitenfenster „R1,5“)."),
            t("<b>Mana-Kurve zu hoch</b>: Ab 8 Zaubern in den Farben des Archetyps (farblose zählen mit, ohne "
            "Archetyp alle) warnen Live-Bereich und Seitenfenster rot, wenn der Ø Manawert über 3,3 liegt, auf 23 "
            "Zauber hochgerechnet mehr als 6 Karten 5+ Mana kosten oder weniger als 5 Karten höchstens 2 Mana. Der "
            "minimierte Kasten zeigt „⚠ Kurve zu hoch“. Dann lieber günstige Karten nehmen."),
            t("Die Fenster des Overlays passen ihre Höhe selbst an den Inhalt an, damit keine Zeilen abgeschnitten "
            "werden; die Breite bleibt, wie du sie ziehst. Reicht der Platz nach unten nicht, rutscht das Fenster "
            "nach oben.")]))
        + _panel(t("Archetypen im Draft"), _ul([
            t("Eine Tabelle zeigt je Archetyp, welche deiner Picks und welche Karten des aktuellen Packs ihm "
            "zugeordnet sind (Picks mit Anzahl). Grün: der erkannte Archetyp. Das Seitenfenster zeigt dasselbe "
            "kurz („Sacrifice: 3 Picks · im Pack: …“)."),
            t("Tipps zum Archetyp: Ist ein Archetyp erkannt oder gewählt und hat das Set Archetypen mit Hinweisen, "
            "stehen dessen Tipps während des Drafts unten im Live-Bereich und unten im Seitenfenster."),
            t("Es zählt nur deine eigene Zuordnung (Knöpfe unter den Karten, kartenarchetypen.json): Karten ohne "
            "Zuordnung gehören keinem Archetyp an, eine Karte kann zu mehreren gehören. Archetypen ohne Karten "
            "fehlen."),
            t("Pack-Karten nennen ihre Archetypen zusätzlich unter dem Namen."),
            t("<b>Drei Stufen</b> je Archetyp-Knopf: Klick schaltet neutral → grün (passt gut) → lila (bester "
            "Archetyp) → neutral. Eine Karte hat höchstens einen besten Archetyp; wird ein anderer lila, wird der "
            "bisherige wieder grün. Der beste zählt wie eine Zuordnung, im Pack mit + 4 statt + 3. Im Pool trägt "
            "eine Karte, deren bester Archetyp der erkannte ist, einen lila pulsierenden Rahmen. Der Bericht nennt "
            "im Archetyp-Kasten „Am besten in …“.")]))
        + _panel(t("Offene Farben"), _ul([
            t("Während des Drafts zeigen Live-Bereich und Seitenfenster, welche Farben offen sind („Signale (Pick Two): "
            "R offen +3 · G umkämpft −2“). Stark ist eine Karte mit deiner Kategorie MustPlay oder höher "
            "(★ Splashworthy, ♛ Matchwinner); mehrfarbige zählen für jede ihrer Farben, farblose nicht."),
            t("<b>Wheel</b> (+2): Ein Pack kommt zurück und eine starke Karte liegt noch drin – das Hauptsignal. Ein Pack "
            "gilt als zurückgekommen, wenn es eine Teilmenge eines früheren Packs derselben Runde (ohne deine Picks "
            "daraus) ist; das klappt für jede Spielerzahl, für Pick Two wie für den normalen Draft."),
            t("<b>Spät</b> (+1): eine starke Karte in einem Pack, das schon mindestens 3 andere Spieler gesehen haben. "
            "Gezählt werden Spieler, nicht Karten: Pick Two nimmt 2 Karten je Pick, ein Pack mit 8 von 14 Karten "
            "haben also 3 Spieler gesehen (im normalen Draft 6)."),
            t("<b>Umkämpft</b> (−1): eine starke Karte, die zwischen zwei Besuchen eines Packs von anderen genommen wurde."),
            t("Wert je Farbe = offen − umkämpft: ab 3 offen, ab 1 evtl. offen, ab −2 umkämpft. Pick Two erkennt der "
            "Drafthelper an zwei Karten je Pick (sonst am Eventnamen). Darunter stehen die letzten Hinweise "
            "(„Pick 9: … kam zurück“).")]))
        + _panel(t("Im Spiel: Tricks bei offenem Mana"), _ul([
            t("Oben in der Spielansicht der Seite und im Trick-Warner (eigenes Fenster) stehen alle Instants und Karten mit Flash des Sets, "
            "die der Gegner mit seinen ungetappten Ländern jetzt wirken könnte, mit Kosten, deiner Kategorie und "
            "Removal-Punkten. Aktivierbare Fähigkeiten auf dem Feld zählen nicht, ebenso wenig Mana aus Kreaturen "
            "oder Treasure."),
            t("Die Liste ändert sich mit jedem Land, das er spielt oder tappt."),
            t("Es stehen nur Tricks da, die zählen: Tricks ohne Kampfwirkung (nur Karten ziehen, abwerfen, Surveil, "
            "Scry, Mill, Lebenspunkte oder Friedhof) fallen weg. Hat der Gegner keine Kreatur auf dem Feld, fallen "
            "auch Tricks weg, die eine eigene Kreatur brauchen (Pump, Schutz, Auren, Blinken, Opfern als "
            "Zusatzkosten). Flash-Kreaturen bleiben immer (überraschender Blocker), ebenso Removal, Tappen und "
            "Konter. Bei mehreren Modi zählt der stärkste. Eine Zeile „Ausgeblendet: …“ sagt, wie viele fehlen."),
            t("Die Kopfzeile nennt die Zahl seiner Handkarten. Hat der Gegner keine Handkarten, kann er keine Tricks "
            "wirken: Dann steht dort nur „Gegner hat keine Handkarten: keine Tricks“, minimiert „Gegner ohne "
            "Handkarten“."),
            t("Fährt die Maus über einen Trick, erscheint ein kleines Fenster mit dem Kartentext (Kosten, Typzeile, "
            "Stärke/Widerstand, Text und Removal-Punkte, englisch von Scryfall); auf der Seite steht derselbe Text "
            "als Hinweis an der Karte."),
            t("Gegnerfarben: Hat der Gegner Zauber in mindestens zwei Farben offen gezeigt, kommen nur Tricks in diesen "
            "Farben und in den Farben seiner Standardländer in Frage (ein Tri-Land zeigt sonst Farben, die er gar "
            "nicht spielt). Farblose Tricks gehen immer."),
            t("Die Karten des Sets kommen von Scryfall (einmal geladen, dann aus <code>scryfall_set_cache.json</code>). "
            "Minimiert zeigt das Seitenfenster „Tricks 3 · offen 2“.")]))
        + _panel(t("Im Spiel: Ziehchancen"), _ul([
            t("Während eines Spiels zeigen Seite und Seitenfenster statt des Packs die eigene Bibliothek. Arena meldet "
            "beim Spielstart das Deck des Spiels und danach laufend, wo die eigenen Karten liegen; Bibliothek = Deck "
            "minus Hand, Spielfeld, Friedhof, Exil und Stapel. Das gilt für jedes Spiel, nicht nur im Draft."),
            t("Je Gruppe (Land, Kreatur, Removal, Quellen je Farbe) und je Karte: wie viele noch drin sind, die Chance "
            "für die nächste Karte und für mindestens eine unter den nächsten 3 Karten (hypergeometrisch: 1 − "
            "C(L − n, k) / C(L, k) bei L Karten in der Bibliothek, n passenden, k gezogenen)."),
            t("Removal: übrige Karten und Punkte im Vergleich zum ganzen Deck."),
            t("<b>Spielbar</b> (oben in der Liste): Karten der Bibliothek, die du mit deinen Ländern auf dem Spielfeld "
            "bezahlen kannst (das Mana dieses Zuges, getappt oder nicht; Hybrid und Phyrexian werden berücksichtigt, "
            "X zählt 0). Länder selbst und andere Manaquellen (Kreaturen, Treasure) zählen nicht. Spielbare Karten "
            "tragen einen Haken."),
            t("Im Spiel ist der Knopf „Deck + Sideboard übernehmen“ ausgeblendet."),
            t("Das Seitenfenster lässt sich mit dem Knopf oben rechts (oder einem Doppelklick) zu einem kleinen Kasten "
            "minimieren: im Spiel nur die Chancen auf Removal, Land und Kreatur für die nächste Karte, im Draft Pick, "
            "Archetyp und beste Karte. Noch einmal klicken klappt es in der alten Größe wieder auf."),
            t("Nach dem Draft und zwischen den Spielen zeigt das Seitenfenster statt „Pick 43“ eine kurze "
            "<b>Deck-Übersicht</b>: Archetyp und Bilanz (Siege–Niederlagen), Karten, Länder und Zauber mit Ø Manawert, "
            "Mana-Kurve (als Balken, der höchste gelb), Kreaturen, Removal (Karten und Punkte), Kartenfluss, Zauber je Farbe "
            "(als Balken in den Manafarben) und die Bomben (eigene "
            "Bewertung Matchwinner; Splashworthy und Must-Play zählen nicht). Grundlage ist das in Arena abgegebene Hauptdeck, vorher alle "
            "Picks. Minimiert: Bilanz, Kreaturen und Removal."),
            t("Karten, die per Mulligan oder Scry unter die Bibliothek gelegt wurden, zählen wie alle anderen (ihre "
            "Lage ist nicht bekannt). Passt die Rechnung nicht genau zur Bibliothek (z. B. durch Token oder "
            "Sideboard), steht ein Hinweis dabei.")]))
        + _panel(t("Deck nach dem Draft übernehmen"), _ul([
            t("Nach dem Draft (42 Picks oder sobald Arena ein Deck meldet) erscheint oben im Live-Bereich und im "
            "Seitenfenster der Knopf <b>Deck + Sideboard übernehmen</b>. In Arena selbst lässt sich kein Knopf "
            "einblenden."),
            t("Klickbar wird er, sobald du in Arena den Deckbau mit „Fertig“ abschließt: Arena schreibt dann Deck und "
            "Sideboard ins Protokoll. Ein Klick schreibt beides in die Kartenpool-Datei (Abschnitte Deck und "
            "Sideboard, Standardländer im Deck); der Drafthelper lädt neu, Deckkarten und Länder stehen auf Core, "
            "das Sideboard auf Aus."),
            t("Ein Deck zählt nur, wenn mindestens 80 % seiner Karten (ohne Standardländer) aus deinen Picks stammen; "
            "ein altes Deck desselben Events bleibt so außen vor. Die übernommene Datei wird nicht mehr mit der "
            "einfachen Pick-Liste überschrieben, auch nicht nach einem Neustart; erst ein neuer Draft beginnt sie "
            "neu.")]))
        + _panel(t("Archetyp erkennen"), _ul([
            t("Jeder Pick zählt mit dem Gewicht seiner Kategorie (Matchwinner 3, Splashworthy und MustPlay 2, ohne Kategorie und Filler "
            "1, NeverPlay 0) für jeden Archetyp, in dessen Farben alle seine Farben liegen, und noch einmal für jeden "
            "Archetyp, dem er zugeordnet ist. Farblose Karten zählen nur über die Zuordnung, Länder gar nicht."),
            t("Erkannt ist der Archetyp mit den meisten Punkten, wenn er mindestens 3 Punkte hat und allein vorn "
            "liegt; sonst ist er noch offen und es wird nichts hervorgehoben."),
            t("Mit der Auswahl <b>Archetyp</b> lässt er sich auch selbst festlegen (zurück mit „Automatisch“). Dazu "
            "stehen die Hinweise zum Archetyp und die Punkte der führenden Archetypen.")]))
        + _panel(t("Seitenfenster"), _ul([
            t("Startet mit dem Live-Draft (abschalten mit <code>--kein-overlay</code>): ein kleines Fenster, das immer im "
            "Vordergrund bleibt, mit Pick-Nummer, Archetyp und der Rangliste des Packs (◆ bester Archetyp der "
            "Karte, ● dem Archetyp zugeordnet, "
            "○ Farben passen, dazu Farben, Kategorie und zugeordnete Archetypen)."),
            t("Arena dafür im Fenster oder im randlosen Vollbild spielen; über exklusivem Vollbild liegt kein Fenster. "
            "Das Fenster lässt sich verschieben und schließt sich, wenn der Drafthelper beendet wird. Einzeln: "
            "<code>python mtg_sim.py --overlay http://127.0.0.1:8765/</code>."),
            t("Am linken Bildschirmrand steht das <b>Steuerfenster</b>: Häkchen schalten das Seitenfenster (Draft / "
            "Bibliothek) und den <b>Trick-Warner</b> an und ab. Der Trick-Warner ist ein eigenes Fenster links unter "
            "dem Steuerfenster und erscheint nur im Spiel. Schließt man das Steuerfenster, sind alle Fenster zu."),
            t('Das <b>Karten-Overlay</b> legt beim Picken die Zahlen direkt auf die Karten im Arena-Fenster: oben links der Rang im Pack, oben rechts die Bewertung, unten Punkte, Farben des besten Archetyps, Passung (✓ dein Archetyp, ≈ nahe dran, ○ Farben passen, – fremde Farben), Removal, Kartenfluss, Synergie, Kreatur und deine Siegquote mit der Karte; Rahmen lila = Top-Pick, grün = passt, grau = fremd. Einmal bei vollem Pack „Kalibrieren“ im Steuerfenster und fünf Ecken anklicken (Karte 1 oben links und unten rechts, Karte 2 oben links, letzte Karte der ersten Reihe oben links, erste Karte der zweiten Reihe oben links); gespeichert in <code>kartenoverlay.json</code> (nicht im Git). Die Zahlen liegen in der Reihenfolge wie in Arena (Seltenheit, Farbe, dann Sammlernummer); jede Karte zeigt unten klein ihren Namen zur Kontrolle. Klicks gehen durch das Overlay zu Arena; zeigt die Maus auf eine Karte, verschwinden die Zahlen dort, wo Arena die große Kartenansicht öffnet. Solange das Overlay an und kalibriert ist, lässt das Seitenfenster Pack-Liste und Top-Pick weg; Archetyp, Signale, Archetyp-Tracker und Tipps bleiben.')]))
        + _panel(t("Draft-Statistik"), _ul([
            t("Solange der Live-Draft läuft, sammelt er je Draft die Picks, das abgegebene Deck und die Ergebnisse der "
            "Matches (je Game und fürs Match) in <code>draftstatistik.json</code> im Projektordner (nicht im Git, "
            "anderer Name mit <code>--statistik DATEI</code>). Gezählt werden nur Draft- und Sealed-Events."),
            t("Matches und Decks gehören zum letzten Draft desselben Events. Wurde der Draft nicht mitgelesen, zählt "
            "das Event trotzdem, nur ohne Picks. Beim Start wird auch die vorherige Protokolldatei "
            "(<code>Player-prev.log</code>) nachgelesen. Dasselbe Protokoll zweimal gelesen zählt nicht doppelt."),
            t("An jeder Karte (Pool, Pack, Set-Ansicht) und im Seitenfenster: wie oft gedraftet, in wie vielen Decks, "
            "und die Siegquote der Games mit der Karte im Hauptdeck. Unter 20 Games ist sie grau: nur ein Hinweis."),
            t("Der Bericht zeigt die Zahlen der Deckkarten im Abschnitt „Deck“ (Kasten „Deine Draft-Statistik“)."),
            t("Pick Two und Drafts mit Menschen: Beim Draften nennt das Protokoll nur eine Draft-Kennung, kein Event. Das Set "
            "kommt dann aus den Karten; das erste Deck des Events, dessen Karten zu mindestens 80 % aus den Picks stammen, "
            "gehört zu diesem Draft und nennt das Event. Mit <code>python mtg_sim.py --statistik-neu</code> wird die "
            "Statistik aus <code>Player-prev.log</code> und <code>Player.log</code> neu aufgebaut (alte Datei als "
            "<code>draftstatistik.backup.json</code>).")]))
        + _panel(t("Gegnerdecks aus Decks mit Höchststand"), _ul([
            t("Holt ein mitgelesener Draft die höchste Zahl an Match-Siegen seines Formats (Pick Two 4, Traditional 3, "
            "sonst 7, z. B. Quick und Premier Draft), speichert der Live-Draft das Deck dieses Matches (mit "
            "Sideboard) einmal als Gegnerdeck: <code>enemydecks/drafted_&lt;SET&gt;_&lt;N&gt;wins_&lt;Farben&gt;_"
            "&lt;JJJJ-MM-TT&gt;_&lt;hhmm&gt;.txt</code>, z. B. <code>drafted_TRK_4wins_…</code> bei Pick Two; Zeit "
            "des letzten Siegs aus dem Protokoll."),
            t("Farben: aus den Nicht-Land-Karten des Hauptdecks, die mit den meisten Karten zuerst (Gleichstand: WUBRG). "
            "Eine Farbe mit höchstens 2 Karten wird als Splash angehängt, z. B. <code>redwhitesplashblue</code>."),
            t("Das Seitenfenster feiert das kurz mit Pokal und Konfetti (Klick schließt): Das Deck ist in die "
            "„Hall of Fame“ der Gegnerdecks aufgenommen."),
            t("Eine vorhandene Datei wird nie überschrieben. Seite und Seitenfenster melden „Gegnerdeck gespeichert“, die "
            "Gegnerdeck-Auswahl im Drafthelper hat es sofort. Beim Neuaufbau der Statistik (--statistik-neu) wird "
            "nichts gespeichert.")]))
        + _panel(t("Setauswertung"), _ul([
            t("Menüpunkt <b>4</b> in <code>draftgott.bat</code> oder <code>python mtg_sim.py --setauswertung "
            "[SET]</code>: schreibt <code>setauswertung_&lt;set&gt;.html</code> und öffnet sie (ohne SET das Set mit "
            "den meisten Drafts)."),
            t("Inhalt: Überblick (Drafts, Matches und Games mit Bilanz), Archetypen (je Draft erkannt wie im "
            "Live-Draft, aus dem Hauptdeck), beste und schwächste Karten (ab 10 Games), alle Karten als sortierbare "
            "Tabelle (gedraftet, Ø Pick-Nummer im Pack, im Deck, Games, Siegquote, Matches), Bewertung gegen "
            "Ergebnis je Kategorie und die Liste der Drafts.")]))
    )


def _drafthelper_help():
    return (
        _panel(t("Zuordnung"), _ul([
            t("<b>Core</b> – in beiden Varianten, <b>Splash</b> – nur in der Variante Splash, <b>NoSplash</b> – nur in der "
            "Variante NoSplash, <b>Aus</b> – in keiner Variante."),
            t("Jede Kopie einer Karte wird einzeln zugeordnet (z. B. 2 von 3 Kopien in Core)."),
            t("Standardländer werden oben als Menge je Gruppe eingestellt, auch Länder, die nicht im Pool sind. Startwert: "
            "die Länder aus dem Deck der Pool-Datei als Core."),
            t("Nicht-Standardländer stehen direkt darunter in einem eigenen Bereich (aus Deck und Sideboard der Datei) und "
            "werden wie andere Karten je Kopie zugeordnet."),
            t("Der Stand wird im Browser gemerkt, und zwar je Inhalt der Pool-Datei: ein anderer Pool startet neu.")]))
        + _panel(t("Archetypen des Sets"), _ul([
            t("Sind für das Set des Pools Archetypen hinterlegt (derzeit TRK und FRA), stehen sie über den Karten: je Farbpaar "
            "der englische Titel und Hinweise zum Deckbau. Das Set ist das häufigste Set der Nicht-Länder "
            "im Pool."),
            t("Hervorgehoben ist der Archetyp der Core-Farben: die zwei Farben mit den meisten Core-Karten (Kopien, ohne "
            "Länder, mehrfarbige zählen für jede ihrer Farben). Der Bericht zeigt im Abschnitt „Deck“ denselben "
            "Archetyp, dort nach den Nicht-Länder-Karten des Decks."),
            t("Der Kasten lässt sich zuklappen; der Browser merkt sich das. Neue Sets werden in "
            "<code>components/archetypes.py</code> ergänzt.")]))
        + _panel(t("Archetyp-Zuordnung je Karte"), _ul([
            t("Unter jeder Karte eines Sets mit Archetypen stehen Knöpfe mit den Farbpaaren der Archetypen (Mauszeiger "
            "darüber: Name). Ein Klick ordnet die Karte dem Archetyp zu oder nimmt die Zuordnung zurück; eine Karte "
            "kann zu mehreren Archetypen passen."),
            t("Die Zuordnung gilt je Kartenname für jeden Pool und den Live-Draft und steht in "
            "<code>kartenarchetypen.json</code> im Projektordner (nicht im Git, anderer Name mit "
            "<code>--archetypen DATEI</code>)."),
            t("<b>Set-Karten bewerten</b> (oben) lädt alle Karten eines Sets von Scryfall: Kategorie und Archetypen "
            "lassen sich so schon vor dem Draft festlegen. Filter: ohne Kategorie, ohne Archetyp, je Farbe."),
            t("Erkannter Archetyp: aus den Core-Karten wie im Live-Draft (siehe dort). Im Archetyp-Kasten steht je "
            "Archetyp, wie viele Core-Karten ihm zugeordnet sind; der erkannte ist grün umrandet, seine Karten "
            "tragen die Plakette „Archetyp“. Der Bericht zeigt dieselbe Zählung und Erkennung im Archetyp-Kasten.")]))
        + _panel(t("Kategorien"), _ul([
            t("<b>♛ Matchwinner</b> – die Bombe: entscheidet ein Match allein und kommt immer rein, notfalls als "
            "Splash (beim Deckbau wie Splashworthy, im Draft und in der Deck-Übersicht ganz oben)."),
            t("<b>★ Splashworthy</b> – entscheidet Spiele allein, soll auf jeden Fall rein, auch wenn wir die Farbe nicht "
            "spielen."),
            t("<b>MustPlay</b> – wird auf jeden Fall gespielt, wenn wir diese Farbe spielen."),
            t("<b>Playable</b> – solide, wird meist gespielt, wenn wir diese Farbe spielen, aber nicht zwingend. Zählt im Draft zwischen MustPlay und Filler (Pack 2 Punkte, Archetyp-Gewicht 1,5), aber nicht als starke Karte (Top-Pick, Signale)."),
            t("<b>Filler</b> – füllt das Deck auf, wenn wir die Farbe spielen und nicht splashen."),
            t("<b>NeverPlay</b> – zu schlecht oder zu situativ."),
            t("Eine Kategorie gilt für alle Kopien einer Karte und beeinflusst die Simulation nicht; ♛ Matchwinner, ★ Splashworthy und "
            "MustPlay erscheinen im Bericht in einem eigenen Abschnitt („Great in this deck“).")]))
        + _panel(t("Zuordnung nach Kategorien setzen"), _ul([
            t("MustPlay → Core, Matchwinner und Splashworthy → Splash, NeverPlay → Aus, Karten ohne Kategorie bleiben unverändert."),
            t("Filler füllt auf die Zielgröße auf (alle Länder zählen mit): zuerst Core, damit beide Varianten gleich groß "
            "werden, dann die NoSplash-Gruppe als Ersatz für die Splash-Karten; übrige Filler → Aus."),
            t("Playable füllt wie Filler auf, kommt aber vor allen Fillern dran (im Deckvorschlag ebenso, nur in den gewählten Farben)."),
            t("Reihenfolge der Filler: nach der gewählten Sortierung, dann Farben, die schon im Deck sind, dann Manawert "
            "aufsteigend. „↶ Rückgängig“ stellt den Stand davor wieder her.")]))
        + _panel(t("Länder empfehlen"), _ul([
            t("Nimmt die aktuelle Zuordnung (Core, Splash, NoSplash) und setzt die Standardländer je Gruppe sowie die "
            "Zuordnung der Nicht-Standardländer neu. Die Zauber bleiben unverändert; „↶ Rückgängig“ stellt den Stand "
            "davor wieder her."),
            t("Farben einer Variante: jede Farbe, deren Symbol auf mindestens einer Nichtland-Karte steht (Hybrid zählt für "
            "beide Farben)."),
            t("Nicht-Standardland: passt, wenn alle seine Farben in der Variante vorkommen (ein R/G-Land passt zu R/G/W, "
            "aber nicht zu G/W). Passt es zu beiden Varianten → Core, nur zu einer → Splash bzw. NoSplash, sonst Aus. "
            "Passende Länder werden immer genommen, auch wenn sie getappt kommen."),
            t("Zahl der Länder je Variante: Zielgröße minus Zauber, begrenzt auf die Faustregel (40 Karten: 15 bis 17). "
            "Nicht-Standardländer ersetzen Standardländer."),
            t("Verteilung: Jede Farbe, die eine Karte zwingend verlangt, bekommt mindestens 3 Quellen (Nicht-Standardländer "
            "zählen mit). Die übrigen Standardländer gehen einzeln an die Farbe, die die Summe der Chancen „pünktlich“ "
            "aller Karten am stärksten erhöht (siehe Farbverteilung im Bericht)."),
            t("Core enthält die Standardländer, die beide Varianten brauchen, der Rest steht in Splash bzw. NoSplash."),
            t("Die Meldung zeigt je Variante die Länder und je Farbe Quellen, Karten, Ø pünktlich und die knappste "
            "Karte.")]))
        + _panel(t("Deckvorschlag"), _ul([
            t("Ein eigenes Deck aus den Kategorien; die Zuordnung bleibt unverändert."),
            t("MustPlay und Filler nur, wenn alle Farben der Karte gewählt sind (Farblos immer); Matchwinner und Splashworthy immer, "
            "außerhalb der gewählten Farben als Splash; NeverPlay und Karten ohne Kategorie nicht."),
            t("Länder: Nicht-Standardländer zählen als Länder; Standardländer werden auf die Faustregel ergänzt (40 Karten: "
            "17 Länder, Bereich 15 bis 17; 60 Karten: 22, Bereich 20 bis 24; dazwischen linear) und nach den "
            "Farbsymbolen verteilt, je Splash-Farbe bis zu 3. Bei Abweichung erscheint ein Hinweis."),
            t("Mit „mitsimulieren“ wird der Vorschlag als weitere Variante verglichen; der Export zeigt ihn als dritte "
            "Spalte.")]))
        + _panel(t("Übersicht links"), _ul([
            t("Übersicht nach Farbe: Pool, Zuordnung und Kategorien je Farbe (Kopien, ohne Standardländer)."),
            t("Mana-Kurve (Splash gegen NoSplash), Mana-Kurve nach Farben (wie im Bericht, Abschnitt Deck) und "
            "Kartentypen je Variante mit Empower Jace und Kartenfluss (gezählt wie im Bericht)."),
            t("Farben und Quellen: je Farbe Symbole, Karten, Quellen (Standardländer der Variante und zugeordnete "
            "Nicht-Standardländer, NS) und Ø pünktlich mit Ampel, gerechnet wie die Farbverteilung im Bericht. Der Block "
            "aktualisiert sich bei jeder Änderung; mit der Maus über Ø pünktlich steht die knappste Karte."),
            t("Manasymbole: die Originalsymbole von Scryfall (einmal geladen und in scryfall_symbols.json gespeichert); "
            "ohne sie erscheinen einfache Symbole."),
            t("Suche, Sortierung und Filter ändern nur die Anzeige, nicht die Zuordnung.")]))
        + _panel(t("Simulieren und Export"), _ul([
            t("„Simulieren“ vergleicht Core + Splash mit Core + NoSplash (und optional den Deckvorschlag); der Bericht "
            "erscheint auf der Seite und wird zusätzlich als Datei gespeichert."),
            t("„Kampf ohne Goldfish“ (neben „Simulieren“, nur wenn Gegnerdecks im Ordner enemydecks liegen): dieselben "
            "Varianten kämpfen direkt gegen das gewählte Gegnerdeck, ohne vorher den Goldfish zu simulieren. Es "
            "zählt die aktuelle Zuordnung, nicht der letzte Bericht; der Kampfbericht wird auch als Datei gespeichert."),
            t("„Deckliste exportieren“: jede Variante im Importformat von MTG Arena und MTGO (Deck und Sideboard).")])))


def _nav(sections, back_href, back_label):
    links = "".join(f'<a href="#hiw-{sid}">{esc(t(title))}</a>' for sid, title, _ in sections)
    return f'<nav><div class="in"><a class="back" href="{back_href}">← {esc(t(back_label))}</a>{links}</div></nav>'


def render_help_view(back_href="#top", back_label="Zurück zum Bericht", on=False, present=None):
    """Zweite Ansicht des Berichts. Abschnitte mit id "hiw-<Abschnitt des Berichts>".
    present: Abschnitte, die der Bericht hat; bedingte Abschnitte ohne Gegenstueck im Bericht entfallen."""
    sections = [s for s in _sections() if present is None or s[0] not in CONDITIONAL or s[0] in present]
    intro = ('<div id="hiw-start" class="panel" style="margin-top:22px"><b>' + t("So funktioniert es") + '</b>'
             '<p class="muted" style="margin:6px 0 0">'
             + t("Wie die Simulation rechnet und wie die Zahlen zu lesen sind, "
                 "Abschnitt für Abschnitt wie im Bericht. Die Werte deines Laufs (Spiele, Runden, Schaden, Flood …) stehen "
                 "oben im Bericht; hier sind die Regeln allgemein mit ihren Parametern und Standardwerten beschrieben.")
             + '</p></div>')
    body = "".join(f'<section id="hiw-{sid}"><h2>{esc(t(title))}</h2>{html}</section>' for sid, title, html in sections)
    return (f'<div class="view{" on" if on else ""}" id="view-help"><div class="layout">'
            f'{_nav(sections, back_href, back_label)}<main>{intro}{body}</main></div></div>')


def render_help_page():
    """Eigenstaendige Seite (fuer den Drafthelper unter /howitworks.html)."""
    return (f'<!DOCTYPE html><html lang="{html_lang()}"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{t("So funktioniert es – MTG Simulation")}</title><style>{HTML_CSS}</style></head><body>'
            f'<header class="top" id="top"><h1>{t("So funktioniert es")}</h1>'
            f'<div class="sub">{t("Regeln und Lesehilfen für Bericht und Drafthelper")}</div></header>'
            f'{render_help_view(back_href="/", back_label="Zurück zum Drafthelper", on=True)}</body></html>')
