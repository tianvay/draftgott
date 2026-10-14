"""Erklaerseite "So funktioniert es": alle Regeln und Lesehilfen, getrennt von den Daten des Berichts.

Die Seite steht als zweite Ansicht in derselben HTML-Datei wie der Bericht (render_help_view) und fuer den Drafthelper
zusaetzlich als eigenstaendige Seite (render_help_page). Die Texte sind allgemein gehalten; die Werte eines Laufs
(Spiele, Runden, Schaden, Flood ...) stehen oben im Bericht. Die Abschnitte heissen wie im Bericht, mit "hiw-" davor.
"""
from components.cli import parse_args
from components.coverage import METRIC_ORDER
from components.html_base import HTML_CSS, esc
from components.report_cards import AVAIL_GREEN, AVAIL_YELLOW
from components.report_sections import JACE_RULES, render_logic_section
from components.stats import TRAFFIC

_D = parse_args(["deck.txt"])  # Standardwerte der Kommandozeile
# Abschnitte, die nur erscheinen, wenn der Bericht sie auch hat (z. B. Deck-Vergleich nur bei mehreren Decks)
CONDITIONAL = {"vergleich", "great", "mulligan", "jace", "farben", "landcycling"}


def _ul(items):
    return '<ul class="ass">' + "".join(f"<li>{x}</li>" for x in items) + "</ul>"


def _p(text):
    return f"<p>{text}</p>"


def _panel(title, body):
    return f'<div class="panel" style="margin-top:12px"><b>{esc(title)}</b>{body}</div>'


def _sections():
    traffic = "; ".join(f'{("Draw" if d else "Play")} Runde {t}: grün ab {g} %, gelb über {y} %'
                        for d, tt in TRAFFIC.items() for t, (g, y) in tt.items())
    return [
        ("vergleich", "Deck-Vergleich", _panel("Statistik", _p(
            "Jedes Deck wird unabhängig mit der eingestellten Zahl an Spielen pro Modus simuliert (<code>--sims</code>, "
            f"Standard {_D.sims}). Hinter den Werten steht das 95-%-Konfidenzintervall (±). Ein Unterschied (Δ) ist "
            "farbig, wenn er größer ist als der zufällige Fehler (|Δ| &gt; 1,96 × Standardfehler), grün bei besser und "
            "rot bei schlechter. Mit ≈ markierte Unterschiede sind nicht von Zufall zu trennen. PP = Prozentpunkte. Bei so "
            "vielen Kennzahlen sind einzelne zufällige Ausreißer zu erwarten, achte deshalb auf das Gesamtbild. Für eine "
            "höhere Genauigkeit hilft eine größere <code>--sims</code>-Zahl."))
         + _panel("Kartentypen im Vergleich", _p(
             "Eine Spalte je Deck, gezählt wie im Abschnitt Deck (siehe dort). Fett: Unterschied zwischen den Decks."))),
        ("blick", "Auf einen Blick", _panel("Ampeln", _ul([
            f"Ampel Zauber pro Runde – {traffic}.",
            "Schnellster Lethal: grün bis Runde 5, gelb Runde 6–7, rot ab Runde 8.",
            f"Alle Farben bis Runde 3: grün ab {AVAIL_GREEN} %, gelb ab {AVAIL_YELLOW} % (siehe Farbverfügbarkeit).",
            "Die Ampel bei „Zauber pro Runde“ rechnet mit der angezeigten ganzen Prozentzahl."]))),
        ("deck", "Deck", _panel("Kartentypen", _p(
            "Gezählt werden Kopien. Artefakte und Verzauberungen ohne Kreaturen und Länder; eine Karte kann in mehreren "
            "Zeilen stehen (z. B. Artifact Enchantment). Länder gesamt enthält die Standardländer, „davon Nicht-Standard“ "
            "nur die übrigen. Σ Loyalty: Zahlenwerte von Empower Jace beim Zauber oder Betreten (ohne X, ohne Auslöser). "
            "Kartenfluss: Karten, die ziehen (auch Cycling), suchen (auch Landcycling), Surveil, Scry, Explore oder Mill "
            "haben; Mill getrennt nach „sich selbst“ und „Gegner möglich“ („target player“ zählt bei beiden). Es "
            "erscheinen nur Arten, die im Deck vorkommen. Auslöser wie „whenever you draw“ und Ziehen des Gegners zählen "
            "nicht, Empower Jace hat eine eigene Zeile."))
         + _panel("Mana-Kurve nach Farben", _ul([
             "Gezählt werden Nichtland-Karten nach Manawert (aufgerundet ab ,5; 7 und mehr zusammen).",
             "<b>Mehrfarbige gesondert:</b> Jede Karte steht genau einmal im Diagramm, die Balkenhöhe ist die "
             "Kartenzahl. Karten mit mehreren Farben bilden das goldene Segment „Mehrfarbig“.",
             "<b>Je Farbe:</b> Eine mehrfarbige Karte zählt bei jeder ihrer Farben (eine Grün/Weiß-Karte bei Grün und bei "
             "Weiß). Die Balken ergeben deshalb zusammen mehr als die Kartenzahl.",
             "Darunter: Zahl der Karten, davon mehrfarbig und farblos, und die vorkommenden Farbkombinationen."]))
         + _panel("Farbverteilung", _p(
             "Karten = Nichtland-Karten, die die Farbe brauchen (in jedem Zahlungsweg; Hybrid zählt nicht) · Quellen = "
             "Länder, die sie erzeugen. Ein Land mit mehreren Farben zählt für jede davon."))
         + _panel("Kartentabelle und Bereiche", _p(
             "Beim Vergleich mit gemeinsamem Kern (Drafthelper oder <code>--core</code>) steht jede Karte mit ihrem "
             "Bereich (Core, Splash, NoSplash …). Mengen werden je Bereich getrennt geführt; blass dargestellte Bereiche "
             "gehören nur zu einer anderen Variante."))),
        ("great", "Great in this deck!", _panel("Was hier steht", _ul([
            "Karten mit der Kategorie ★ Splashworthy oder MustPlay aus dem Drafthelper, mit Bereich, Kosten und "
            "Eigenschaften.",
            "„Fehlt in diesem Deck“: eine MustPlay-Karte fehlt (in jeder Variante) oder eine Splashworthy-Karte fehlt "
            "in der Splash-Variante. Für den Deckvorschlag gibt es diesen Hinweis nicht, weil er nach Farbregeln gebaut "
            "wird.",
            "„NeverPlay-Karten im Deck“: Karten, die als NeverPlay gekennzeichnet und trotzdem im Deck sind."]))),
        ("abdeckung", "Modell-Abdeckung", _panel("Wie die Karten eingeordnet werden", _ul([
            "Die Erkennung arbeitet über den Kartentext von Scryfall und sortiert nur grob, weil Magic dasselbe oft "
            "unterschiedlich formuliert. Status jeder gelisteten Karte: „To Do: Noch nicht implementiert“.",
            "Nicht gemeldet wird, was die Simulation abbildet: aufgedrucktes Haste und Defender, Landcycling, die "
            "Bedingungen getappter Länder, Empower Jace mit festem Wert und Kampf-Schlüsselwörter ohne Gegner.",
            "Kategorien: Tokens erzeugen, Direkter Schaden, Zählmarken / Stärkebonus, Haste verleihen, Mana außer "
            "Ländern, Kartenfluss, Kostensenkung / Convoke, Zweitverwertung (Friedhof), Timing (Flash), Zusatzkosten, "
            "Prepared-Zauberhälfte, Planeswalker-Fähigkeit, Defender-Ausnahme, Interaktion mit dem Gegner, "
            "Lebensgewinn, Schlüsselwort verleihen und Empower-Sonderfälle. Was sich nicht einordnen lässt, heißt "
            "„Unbekannter Effekt“.",
            "Betroffene Kennzahl: " + ", ".join(METRIC_ORDER) + ". Bei „unklar“ ist nicht bekannt, was genau fehlt. "
            "Mit der Maus über der Kategorie steht die Textstelle."]))),
        ("mulligan", "Mulligan", _panel("Wann es einen Mulligan gibt", _ul([
            "<b>Farben:</b> Mit den Farben der Länder auf der Starthand ist keine Karte spielbar (nur die Farben zählen, "
            "nicht die Manamenge).",
            "<b>Zu viele Länder:</b> 6 oder mehr Länder auf der Starthand.",
            "<b>Zu wenige Länder:</b> Höchstens 2 Länder und weniger als 3 Karten, die sich mit diesen Ländern bezahlen "
            "lassen (Manawert und Farben). Zwei Länder plus lauter 1- und 2-Mana-Karten werden also behalten."])
            + _p("Bei einem Mulligan wird das Deck neu gemischt und eine neue Starthand mit einer Karte weniger gezogen. "
                 "Dieselben Regeln gelten für jede neue Hand. Fällt die Hand unter die Mindestzahl "
                 f"(<code>--min-handkarten</code>, Standard {_D.min_handkarten}), gilt das Spiel als verloren; auch eine "
                 "Hand dieser Größe, die einen Mulligan auslösen würde, zählt als verloren. Mit <code>--ohne-mulligan"
                 "</code> wird jede 7-Karten-Hand gespielt."))
         + _panel("Wie die Tabellen zu lesen sind", _ul([
             "Gründe: Anteil aller ersten 7-Karten-Hände. Die Gründe können zusammen auftreten, ihre Summe kann deshalb "
             "über dem Gesamtwert liegen.",
             "Startgröße: Prozent aller ausgeteilten Starthände. Verlorene Spiele werden nicht gespielt und fließen nicht "
             "in die übrigen Zahlen ein: Alle anderen Auswertungen beruhen auf den gespielten Spielen nach dem "
             "Mulligan."]))),
        ("jace", "Jace & Planeswalker", _panel("Modellregeln", _ul([esc(r) for r in JACE_RULES]))
         + _panel("Wie die Tabellen zu lesen sind", _ul([
             "Σ Empower: bei wiederkehrenden Karten der Wert je Auslösung beziehungsweise je Aktivierung. Eine Karte "
             "kann in mehreren Kategorien stehen, die Summe der Zeilen ist deshalb größer als „gesamt“.",
             "„Bis die Hand leer ist“: gezählt bis zum ersten Rundenende ohne Karten auf der Hand (nach dem Zaubern und "
             "einer möglichen Jace-Aktivierung); wird die Hand nie leer, zählt der ganze Beobachtungszeitraum.",
             "„Aktivierungen“ zählen das Ziehen (−3): Ø Aktivierungen ist zugleich die Zahl der durch Jace gezogenen "
             "Karten. „Ø Surveil“ zählt die −1-Aktivierungen, „Ø Länder in den Friedhof“ die dabei abgelegten Länder. "
             "„Ø Empower“ ist die erhaltene Loyalty insgesamt.",
             "Mit <code>--ohne-jace</code> wird Jace nicht simuliert, die Karten werden nur gezählt."]))),
        ("zauber", "Zauber pro Runde", _panel("Bedeutung", _p(
            "Anteil der Spiele, in denen in dieser Runde mindestens ein Zauber gespielt wird (Farben beachtet, gespielte "
            "Karten sind weg). Ausgewertet bis zur eingestellten Runde (<code>--turns</code>, Standard "
            f"{_D.turns})."))),
        ("kreaturen", "Kreaturen nach Runde X", _panel("Bedeutung", _p(
            "Durchschnitt auf dem Feld nach der Auswertungsrunde (<code>--turns</code>), aufgedruckte Werte ohne Auras "
            "und Boni."))),
        ("screw", "Mana Screw & Flood", _panel("Bedeutung", _ul([
            "<b>Mana Screw:</b> nach der Auswertungsrunde (<code>--turns</code>) weniger Länder auf dem Feld als die "
            "Rundenzahl oder, bei mehrfarbigen Decks, keine zwei Farben.",
            "<b>Flood:</b> bis zum Ende der Beobachtung (<code>--max-runden</code>, Standard "
            f"{_D.max_runden}) mindestens so viele Länder gezogen wie mit <code>--flood</code> eingestellt "
            f"(Standard {_D.flood}), die Starthand eingerechnet."]))),
        ("farben", "Farbverfügbarkeit", _panel("Bedeutung", _ul([
            "Quelle = Land auf dem Feld nach dem Landdrop der Runde (auch getappt), das die Farbe erzeugen kann; ein "
            "Land mit mehreren Farben zählt für jede davon.",
            "Runde 3: von jeder Farbe, die Karten im Deck zwingend brauchen, mindestens eine Quelle (alle zusammen und "
            "jede einzeln).",
            "Runde 4: zwei Quellen, aber nur für Farben, die eine Karte doppelt verlangt (z. B. RR); Hybrid zählt nicht.",
            f"Ampel: grün ab {AVAIL_GREEN} %, gelb ab {AVAIL_YELLOW} %, sonst rot. Manakreaturen und andere Manaquellen "
            "sind nicht modelliert."]))),
        ("curve", "Curve-Auslastung", _panel("Bedeutung", _p(
            "Ausgegebenes geteilt durch verfügbares Mana je Runde (bis <code>--curve-runden</code>, Standard "
            f"{_D.curve_runden}). Nur Mana aus Ländern, Manakreaturen und Artefakte sind nicht modelliert. Ein "
            "Rechenbeispiel steht unter Spiellogik."))),
        ("schaden", "Schaden durch Kreaturen", _panel("Bedeutung", _p(
            "Erste Runde, in der der Gesamtschaden das Ziel erreicht (<code>--schaden</code>, Standard "
            f"{_D.schaden}). Ø und Median nur über Spiele, in denen es bis zum Ende der Beobachtung eintritt. Alle "
            "Kreaturen greifen jede Runde an, Einsatzverzögerung außer Haste, Defender greift nie an, keine Blocker oder "
            "Removal, nur aufgedruckte Power."))),
        ("lethal", "Schnellster Lethal", _panel("Bedeutung", _p(
            "Das schnellste aller simulierten Spiele, bei gleicher Runde das mit mehr Schaden, mit Starthand und "
            "Rundenprotokoll. Ein Glücksfall, kein Erwartungswert – die typische Runde steht unter „Schaden durch "
            "Kreaturen“."))),
        ("landcycling", "Landcycling", _panel("Regeln", _ul([
            "<b>Land fehlt:</b> Ist in den ersten Runden (bis <code>--landcycling-runden</code>, Standard "
            f"{_D.landcycling_runden}) kein Land auf der Hand, wird ein Landcycler gecycelt, damit der Landdrop klappt.",
            "<b>Karte nicht spielbar:</b> Mit übrigem Mana wird eine Karte gecycelt, die in dieser Runde nicht "
            "spielbar ist, wenn es sich lohnt (Vorausschau auf die nächste Runde), und nur unter so vielen Ländern auf "
            f"Feld und Hand wie eingestellt (<code>--landcycling-max-laender</code>, Standard "
            f"{_D.landcycling_max_laender}).",
            "Die letzte Karte auf der Hand wird nicht gecycelt (außer mit <code>--landcycling-letzte-karte</code>); "
            "mit <code>--ohne-landcycling</code> wird nie gecycelt.",
            "„Nicht-Land-Chance“: wie stark das Cycling die Chance erhöht, im nächsten Zug ein Nicht-Land zu ziehen."]))),
        ("tempo", "Tempo", _panel("Bedeutung", _p(
            "Ø und Median nur über Spiele, in denen das Ereignis bis zum Ende der Beobachtung eintritt. Top Card: die "
            "Karte(n) mit dem höchsten Manawert; gezählt wird die erste Runde, in der sie spielbar wäre."))),
        ("logik", "Spiellogik", render_logic_section(True)),
        ("annahmen", "Modellannahmen", _panel("Annahmen", _ul([
            "Starthand 7 Karten mit Mulligan-Regeln (siehe Mulligan); jede Runde ziehen (On the Play erst ab Runde 2), "
            "ein Land legen, zaubern.",
            "Jede Nichtland-Karte wird gespielt, sobald sie bezahlbar ist; pro Runde wird möglichst viel Mana "
            "ausgegeben.",
            "Farben, Hybrid- und Phyrexian-Mana werden beachtet; Manakreaturen und Artefakte sind nicht modelliert.",
            "Länder, die getappt ins Spiel kommen, werden aus dem Kartentext erkannt; Shock-Länder zahlen die 2 Leben. "
            "Länder mit Planeswalker-Bedingung kommen untapped, wenn ein Planeswalker liegt; wenn möglich wird dafür "
            "zuerst ein Zauber gewirkt, der einen Planeswalker erschafft. „Behold a Jace“ gilt auch mit einer "
            "Jace-Karte auf der Hand.",
            "Auras werden nur mit eigener Kreatur gespielt (außer mit <code>--auras-ohne-kreatur</code>).",
            "Kreaturen: aufgedruckte Power/Toughness, Einsatzverzögerung außer Haste, Defender greift nie an, keine "
            "Blocker oder Removal.",
            "Landcycling und Empower Jace: Regeln in den jeweiligen Abschnitten.",
            "Was die Simulation nicht abbildet, zeigt der Abschnitt Modell-Abdeckung je Deck."]))),
        ("drafthelper", "Drafthelper", _drafthelper_help()),
    ]


def _drafthelper_help():
    return (
        _panel("Zuordnung", _ul([
            "<b>Core</b> – in beiden Varianten, <b>Splash</b> – nur in der Variante Splash, <b>NoSplash</b> – nur in der "
            "Variante NoSplash, <b>Aus</b> – in keiner Variante.",
            "Jede Kopie einer Karte wird einzeln zugeordnet (z. B. 2 von 3 Kopien in Core).",
            "Standardländer werden oben als Menge je Gruppe eingestellt, auch Länder, die nicht im Pool sind. Startwert: "
            "die Länder aus dem Deck der Pool-Datei als Core.",
            "Der Stand wird im Browser gemerkt, und zwar je Inhalt der Pool-Datei: ein anderer Pool startet neu."]))
        + _panel("Kategorien", _ul([
            "<b>★ Splashworthy</b> – entscheidet Spiele allein, soll auf jeden Fall rein, auch wenn wir die Farbe nicht "
            "spielen.",
            "<b>MustPlay</b> – wird auf jeden Fall gespielt, wenn wir diese Farbe spielen.",
            "<b>Filler</b> – füllt das Deck auf, wenn wir die Farbe spielen und nicht splashen.",
            "<b>NeverPlay</b> – zu schlecht oder zu situativ.",
            "Eine Kategorie gilt für alle Kopien einer Karte und beeinflusst die Simulation nicht; ★ Splashworthy und "
            "MustPlay erscheinen im Bericht in einem eigenen Abschnitt („Great in this deck“)."]))
        + _panel("Zuordnung nach Kategorien setzen", _ul([
            "MustPlay → Core, Splashworthy → Splash, NeverPlay → Aus, Karten ohne Kategorie bleiben unverändert.",
            "Filler füllt auf die Zielgröße auf (alle Länder zählen mit): zuerst Core, damit beide Varianten gleich groß "
            "werden, dann die NoSplash-Gruppe als Ersatz für die Splash-Karten; übrige Filler → Aus.",
            "Reihenfolge der Filler: nach der gewählten Sortierung, dann Farben, die schon im Deck sind, dann Manawert "
            "aufsteigend. „↶ Rückgängig“ stellt den Stand davor wieder her."]))
        + _panel("Deckvorschlag", _ul([
            "Ein eigenes Deck aus den Kategorien; die Zuordnung bleibt unverändert.",
            "MustPlay und Filler nur, wenn alle Farben der Karte gewählt sind (Farblos immer); Splashworthy immer, "
            "außerhalb der gewählten Farben als Splash; NeverPlay und Karten ohne Kategorie nicht.",
            "Länder: Nicht-Standardländer zählen als Länder; Standardländer werden auf die Faustregel ergänzt (40 Karten: "
            "17 Länder, Bereich 15 bis 17; 60 Karten: 22, Bereich 20 bis 24; dazwischen linear) und nach den "
            "Farbsymbolen verteilt, je Splash-Farbe bis zu 3. Bei Abweichung erscheint ein Hinweis.",
            "Mit „mitsimulieren“ wird der Vorschlag als weitere Variante verglichen; der Export zeigt ihn als dritte "
            "Spalte."]))
        + _panel("Übersicht links", _ul([
            "Übersicht nach Farbe: Pool, Zuordnung und Kategorien je Farbe (Kopien, ohne Standardländer).",
            "Mana-Kurve (Splash gegen NoSplash), Mana-Kurve nach Farben (wie im Bericht, Abschnitt Deck) und "
            "Kartentypen je Variante mit Empower Jace und Kartenfluss (gezählt wie im Bericht).",
            "Suche, Sortierung und Filter ändern nur die Anzeige, nicht die Zuordnung."]))
        + _panel("Simulieren und Export", _ul([
            "„Simulieren“ vergleicht Core + Splash mit Core + NoSplash (und optional den Deckvorschlag); der Bericht "
            "erscheint auf der Seite und wird zusätzlich als Datei gespeichert.",
            "„Deckliste exportieren“: jede Variante im Importformat von MTG Arena und MTGO (Deck und Sideboard)."])))


def _nav(sections, back_href, back_label):
    links = "".join(f'<a href="#hiw-{sid}">{esc(title)}</a>' for sid, title, _ in sections)
    return f'<nav><div class="in"><a class="back" href="{back_href}">← {esc(back_label)}</a>{links}</div></nav>'


def render_help_view(back_href="#top", back_label="Zurück zum Bericht", on=False, present=None):
    """Zweite Ansicht des Berichts. Abschnitte mit id "hiw-<Abschnitt des Berichts>".
    present: Abschnitte, die der Bericht hat; bedingte Abschnitte ohne Gegenstueck im Bericht entfallen."""
    sections = [s for s in _sections() if present is None or s[0] not in CONDITIONAL or s[0] in present]
    intro = ('<div id="hiw-start" class="panel" style="margin-top:22px"><b>So funktioniert es</b>'
             '<p class="muted" style="margin:6px 0 0">Wie die Simulation rechnet und wie die Zahlen zu lesen sind, '
             'Abschnitt für Abschnitt wie im Bericht. Die Werte deines Laufs (Spiele, Runden, Schaden, Flood …) stehen '
             'oben im Bericht; hier sind die Regeln allgemein mit ihren Parametern und Standardwerten beschrieben.</p>'
             '</div>')
    body = "".join(f'<section id="hiw-{sid}"><h2>{esc(title)}</h2>{html}</section>' for sid, title, html in sections)
    return (f'<div class="view{" on" if on else ""}" id="view-help"><div class="layout">'
            f'{_nav(sections, back_href, back_label)}<main>{intro}{body}</main></div></div>')


def render_help_page():
    """Eigenstaendige Seite (fuer den Drafthelper unter /howitworks.html)."""
    return ('<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>So funktioniert es – MTG Simulation</title><style>{HTML_CSS}</style></head><body>'
            '<header class="top" id="top"><h1>So funktioniert es</h1>'
            '<div class="sub">Regeln und Lesehilfen für Bericht und Drafthelper</div></header>'
            f'{render_help_view(back_href="/", back_label="Zurück zum Drafthelper", on=True)}</body></html>')
