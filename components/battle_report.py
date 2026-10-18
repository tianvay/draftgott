"""Kampfbericht: eigene HTML-Seite fuer die Kaempfe gegen ein Gegnerdeck (Uebersicht und Protokolle).

render_battle_html(decks, args): decks wie im Goldfish (build_deck), jeweils mit "battles" (mtg_sim.simulate_battles).
Inhalt: Uebersicht (Siege/Niederlagen je Deck und Modus), je Deck der schnellste Sieg und die schnellste Niederlage als
Zugprotokoll beider Spieler, Regeln des Kampfs. Bei mehreren Decks (Splash/NoSplash) Umschalter an jeder Ueberschrift.
"""
import datetime

from components.battle import _end_life, _max_gap
from components.html_base import HTML_CSS, LAYOUT_JS, LABEL_CLASS, esc, h_bar_cell, h_mode, h_section, h_table, svg_lines

MODES = ("On the Play", "On the Draw")

RULES = [
    "Beide Spieler starten mit 20 Lebenspunkten und sind abwechselnd dran. Ein Zug: Untap, Draw (entfällt im "
    "allerersten Zug), Main 1, Kampf, Main 2, End Phase. Bei „On the Play“ beginnen wir, bei „On the Draw“ der Gegner.",
    "Mulligan wie im Goldfish. Fällt unsere Hand unter die Mindestzahl, geben wir auf (Niederlage durch Mulligan). Der "
    "Gegner gibt nie auf: Er behält dann seine Hand mit der Mindestzahl an Karten.",
    "Gespielt wird mit derselben Auswahl wie im Goldfish, in den Main Phases aber nur Sorcery-Speed (Permanents, "
    "Sorceries, Sorcery-Removal mit gültigem Ziel). Main 1: das Land und alle Zauber außer Kreaturen ohne Haste; Main 2: "
    "Kreaturen ohne Haste. Kreaturen, deren Betreten den Kampf verbessert, kommen schon in Main 1: Surveil, während "
    "eine Kreatur auf ein Surveil wartet (Surveillance Phantasm), Removal gegen einen Blocker, der einen Angreifer "
    "fressen würde, Pumps/Marken für Angreifer, Lebensgewinn für angreifende Engel (Lyra). Übriges Mana bleibt offen "
    "für Instants und Flash, auch im Zug des Gegners. Hat der Gegner eine Kreatur, die unser Removal töten kann, "
    "bleiben die Kosten des billigsten solchen Removals frei (Instants, Flash-Kreaturen mit Removal beim Betreten, "
    "Removal per Abwerfen wie Sureshot Sower); eingesetzt wird es dann im Zug des Gegners.",
    "<b>Removal</b> trifft die gefährlichste passende Kreatur (höchste Power, dann Flying/Trample/Deathtouch, dann "
    "Manawert): Destroy/Exile, Schaden und −X/−X nur, wenn sie tötet, Edikt (der Gegner opfert seine schwächste "
    "Kreatur, bei „greatest mana value“ die teuerste), Fight, Bounce (zurück auf die Hand), Lock-Aura (greift nicht an, "
    "blockt nicht), Massenremoval (alle Kreaturen). Removal-Instants: vor dem eigenen Angriff gegen einen Blocker, der "
    "einen Angreifer fressen würde; im Zug des Gegners gegen den gefährlichsten Angreifer; sonst am Ende des "
    "gegnerischen Zugs.",
    "<b>„Any target“-Schaden</b> trifft die gefährlichste Kreatur, die er tötet (nur Kreaturen mit Power über 0); ist "
    "Schaden am Gegner tödlich oder gibt es keine solche Kreatur, geht er an den Gegner.",
    "<b>Kampftricks</b> (Instants und Flash-Karten mit Pump oder Marken) nach den Blockern, wenn danach eine eigene "
    "Kreatur überlebt, eine gegnerische stirbt oder es Lethal ist. <b>Flash-Kreaturen</b> blocken, wenn das einen "
    "guten Block ergibt oder Lethal verhindert, sonst kommen sie am Ende des gegnerischen Zugs. <b>Sonstige "
    "Instants</b> (z. B. Ziehen) am Ende des gegnerischen Zugs.",
    "<b>Abwerfen</b> (z. B. Rank Rat): ein überzähliges Land (Feld + Hand reichen für die teuerste Handkarte), sonst "
    "die günstigste Karte.",
    "<b>Angriff:</b> Alles greift an, wenn selbst bei bestem Blocken genug Schaden für Lethal durchkommt. Sonst greift "
    "eine Kreatur an, solange kein ungetappter Blocker sie tötet und dabei überlebt (ein Tausch ist in Ordnung). Wäre "
    "sonst der Gegenangriff im nächsten Zug Lethal, bleiben die schwächsten Angreifer zu Hause.",
    "<b>Block:</b> Ein Blocker, der den Angreifer tötet und überlebt; sonst ein Tausch, wenn der Angreifer mindestens so "
    "viel Manawert hat; sonst ein Doppel-Block, bei dem einer der Blocker überlebt. Chump-Blocks nur gegen Lethal.",
    "<b>Schaden:</b> First Strike zuerst, Double Strike in beiden Schritten, Deathtouch (1 Schaden reicht, auch mit "
    "Trample), Trample, Lifelink. Flying kann nur von Flying oder Reach geblockt werden, Menace nur von zwei Kreaturen. "
    "Getappte Kreaturen greifen nicht an und blocken nicht (auch nicht, wenn sie für Mana getappt wurden); Vigilance "
    "tappt beim Angriff nicht.",
    "Beide Seiten spielen nach denselben Regeln und kennen die Handkarten des anderen nicht. Gestorbene Kreaturen kommen "
    "in den Friedhof; „damage to each player“ trifft auch den Spieler selbst.",
    "Spielende: 0 Lebenspunkte, Ziehen aus leerer Bibliothek oder Aufgabe durch Mulligan. Nach der Rundengrenze "
    "(<code>--kampf-runden</code>, Standard 20 eigene Züge) ist es unentschieden.",
    "Surveil durch Karten und Länder wie im Goldfish (Land bleibt oben, solange Länder für die teuerste Handkarte "
    "fehlen). Prepared: Die Kopie ist wie eine Handkarte nur in der eigenen Main Phase spielbar; Upkeep-Karten werden "
    "zu Beginn des Zugs wieder prepared.",
    "Treasure: im eigenen Zug nur, wenn er mehr Zauber ermöglicht; im Zug des Gegners für Instants und Flash nur, wenn "
    "das offene Mana nicht reicht.",
    "Jace (Empower): Loyalty aus Zaubern, Betreten, Auslösern und Fähigkeiten (siehe unten). Zu Beginn des Zugs ab 3 "
    "Loyalty −3: Karte ziehen; nach Main 2 ab 3 ziehen, sonst −1: Surveil 1. Jace wird angegriffen, wenn er "
    "dadurch unter 3 Loyalty fällt oder stirbt (nicht, wenn wir stattdessen Lethal auf den Spieler hätten): dafür die "
    "schwächsten Angreifer, gerade so viele, wie nötig; kein Chump-Block zum Schutz von Jace.",
    "Fähigkeiten mit Kosten (nur Mana und {T}): „Activate only as a sorcery“ nur in der eigenen Main Phase, „only "
    "during your turn“ nur im eigenen Zug, sonst jederzeit. Freies Mana: Mana, nach dessen Einsatz jede bezahlbare "
    "Instant-, Flash- oder Landcycling-Karte der Hand bezahlbar bleibt.",
    "Pumps und verliehene Schlüsselwörter bis Rundenende: als Angreifer nach den Blockern bei Lethal (auch mit Treasure), "
    "sonst mit freiem Mana, wenn der Kampf besser wird (mehr Schaden, Kreatur überlebt, Blocker stirbt); Flying und "
    "Menace schon vor dem Angriff, wenn dadurch mehr durchkommt. Als Verteidiger vor und nach den Blockern, wenn der "
    "Block besser wird (z. B. Reach gegen einen Flieger).",
    "+1/+1-Marken und Empower durch Fähigkeiten: im eigenen Zug vor dem Angriff mit freiem Mana, sonst mit dem Rest am "
    "Ende des gegnerischen Zugs (nach Instants, Flash und Landcycling, ohne Treasure); Marken vor Empower, auf die "
    "stärkste passende Kreatur.",
    "Landcycling: Fehlt bis Runde 3 im eigenen Zug ein Land für den Landdrop, wird sofort gecycelt. Sonst am Ende des "
    "gegnerischen Zugs mit dem offenen Mana, das Instants und Flash übrig lassen (bis 6 Länder auf Feld und Hand, nicht "
    "die letzte Handkarte, nicht wenn die Karte nächste Runde spielbar ist).",
    "Weitere Auslöser: Kampfschaden am Spieler zieht Karten (Frostbite Pyromental), Opfern zu Beginn des Endsegments, "
    "Leben und Marken, wenn eigene Kreaturen ins Spiel kommen (Greenhouse Propagator, Mabel: auf die stärkste Kreatur, "
    "die in diesem Zug kam), Team-Pump nach Artefakten (Craterclaw Colossus), Kostensenkung für Nichtkreatur-Zauber "
    "(Geist of Saint Thalia), Marken bei Zaubern mit Ziel beim Gegner (Danitha), Empower X beim Angriff "
    "(X = eigene Kreaturen).",
    "Fähigkeiten mit Sonderkosten: „Discard this card“ als Removal von der Hand wie ein Instant (Sureshot Sower, kein "
    "Zauber); „Exile this card from your graveyard“ wie Marken und Empower (Campus Crier). Surveil-Fähigkeiten am Ende "
    "des gegnerischen Zugs; im eigenen Zug nur, wenn eine Kreatur dadurch trotz Defender angreifen darf "
    "(Surveillance Phantasm, auch nach Surveil durch Karten oder Jace).",
    "Token: Tenured Tethermage opfert immer ein Land (farblos zuerst, sonst das, dessen Farben am häufigsten vorkommen; "
    "bei Gleichstand ein getapptes, dann ein Basic Land; ein ungetapptes nimmt sein offenes Mana mit) für zwei Heartwood-Token "
    "(Mana ab dem nächsten Zug); „Tap two untapped artifacts“ am Ende des gegnerischen Zugs mit Artefakten, die nicht "
    "mehr gebraucht werden. Vraska: Sculpture-Token bei jedem Nichtkreatur-Zauber, nutzbar wie Treasure (ab dem nächsten "
    "eigenen Zug), Artefaktkreaturen mit Vigilance. Token kommen nicht in den Friedhof.",
    "Primal Witchstalker: Mill 4, dann das Land aus dem Friedhof mit den meisten neuen Farben. Enlightened Confidant: "
    "nach Lebensgewinn Surveil 1; ein abgelegtes Land kommt auf die Hand. Null Summoner: exiliert aus der Hand des "
    "Gegners zuerst das teuerste Removal, sonst die teuerste Nichtland-Karte; ab 7 Karten im eigenen Friedhof wirkt er "
    "sie selbst mit Mana jeder Art. Sie geht danach in den Friedhof bzw. auf die Hand ihres Besitzers.",
    "Kreatur-Token aus Zaubern, Prepared-Kopien, Betreten und Fähigkeiten (z. B. Cadet, Ingris mit Haste) liegen als "
    "Kreaturen auf dem Feld; sterben sie oder gehen sie auf die Hand, verschwinden sie.",
    "Leben: Landfall-Lebensgewinn (Koth of the Homestead). Lyra zählt Lebensgewinne, nicht Leben: zwei Kreaturen mit "
    "Lifelink lösen zweimal aus, eine einmal; die Marken gibt es nach dem Kampfschaden nur für Engel, die noch leben. "
    "Thalia, the Survivor: Nichtkreatur-Zauber des anderen Spielers kosten {1} mehr (auch Prepared-Kopien und "
    "exilierte Karten).",
    "Weitere Effekte: Schaden je Angreifer beim Angriff (Ingris Stingerquill), Leben beim Betreten, Sterben und Wirken "
    "(Apex Witchstalker, Extended Absence; Schaden und Leben von Instants auch im Zug des Gegners), Prowess. "
    "Zusatzkosten „sacrifice … or pay {N}“ zahlen wir immer mit Mana (Silence the Echo: {3} mehr).",
    "Legend-Regel: je Spieler nur ein legendäres Permanent gleichen Namens (die stärkere Kreatur bleibt); ein zweites "
    "Exemplar wird nicht gewirkt. Handlimit: am Ende des eigenen Zugs auf 7 Karten abwerfen. Winter: wir opfern "
    "unsere schwächste andere Kreatur, nur wenn der Gegner eine Kreatur hat; er opfert seine schwächste.",
    "Hexproof: Kreaturen mit Hexproof sind kein Ziel für Zauber und Fähigkeiten des Gegners (Ruric Thar, bis er "
    "Kampfschaden zugefügt hat); Effekte ohne Ziel wie Schaden an allen Kreaturen oder Edikte treffen sie trotzdem. "
    "Flashback: Sorceries aus dem Friedhof in der Main Phase wie Handkarten, Instants auch im Zug des Gegners (mit "
    "„Discard a card“ wird die Karte abgeworfen, die wir sonst auch abwerfen würden); danach ins Exil. Karten, die erst "
    "in diesem Zug in den Friedhof kamen, gehen erst im nächsten Zug.",
    "Aus dem Friedhof zurück: Zauber holen die stärkste passende Karte (höchster Manawert, dann Power; Länder mit den "
    "meisten neuen Farben) bzw. alle passenden; ohne passende Karte werden sie nicht gewirkt. Fähigkeiten aus dem "
    "Friedhof (Blessed Ghoul, Theoretical Necromancer, Gallia, Grim Repriser) wie Marken: mit freiem Mana im eigenen Zug, "
    "sonst mit dem Rest am Ende des gegnerischen Zugs. Darklight Phoenix kehrt zu Beginn des eigenen Kampfs zurück, "
    "wenn in diesem Zug zwei oder mehr Kreaturen gestorben sind. Finality: stirbt die Kreatur, wird sie exiliert.",
    "Betreten-Effekte („When this creature enters“, 603.6a) wirken bei jedem Weg ins Spiel: gewirkt, mit Flash, als "
    "Token oder aus dem Friedhof. Auslöser beim Wirken („whenever you cast“, „if you cast it“, Prowess) nur beim Wirken.",
    "X-Kosten (Fblthp): X ist das freie Mana nach den übrigen Zaubern der Main Phase, höchstens so viel, wie es "
    "nutzt; aus dem Friedhof zurück ist X = 0. Fblthp sucht zuerst Basic Lands mit neuen Farben; seine Power ist die "
    "Zahl der Basic-Land-Typen unter unseren Ländern. Massacre Girl: Tod einer anderen eigenen Kreatur (auch im selben "
    "Moment wie sie selbst) gibt 1 Schaden am Gegner und 1 Leben; jeder Schaden außerhalb des Kampfs am Gegner gibt "
    "ihr eine Marke.",
    "Modale Karten („Choose one/two —“): jeder Aufzählungspunkt ist ein Modus; gewählt werden die wertvollsten: "
    "Lethal, Removal (tötet), Karte ziehen, Token, Marken/Pumps, Schaden, Leben. Modale Instants: Removal-Modi wie "
    "Removal-Instants, Pumps und Schlüsselwörter als Kampftrick, sonst am Ende des gegnerischen Zugs ein Wert-Modus "
    "(z. B. Cadet, Karte ziehen). Counterspells und Mana-Modi werden nicht genutzt.",
    "Removal mit Bedingungen: nur passende Farben (Essence Burn: schwarz oder grün, stirbt das Ziel, wird es "
    "exiliert; Flourishing Grapple: rot oder weiß, unsere stärkste Kreatur beißt, ohne Rückschlag). Zurück in die "
    "Bibliothek (Plan for All Outcomes): der Besitzer legt die Karte oben hin, wenn er sie im nächsten Zug wieder "
    "wirken kann (Manawert höchstens seine Länder + 1), sonst unten; Token verschwinden (111.7). Abwerfen nach Wahl "
    "(Solve for Disappointment): wir nehmen die bleibende Karte, die er nächste Runde wirken könnte, mit dem "
    "höchsten Manawert (Gleichstand: höchster Removal-Score), sonst die teuerste.",
    "Nichtkreatur-Zauber: Marke (Chandra's Emberling), alle +1/+0 (Winter, Team Player), Prowess zählt jedes "
    "Exemplar (702.108b, Ruric Thar). Lebensgewinn: Marke auf sich (Unflinching Hortimancer), einmal pro Zug eine "
    "Karte (Bloombrute), Loyalty auf einen vorhandenen Jace (Way of the Mentor). Angriff: Schaden und Leben "
    "(Screeching Soulbreaker); Afterthought Sentry exiliert aus dem Friedhof des Gegners zuerst eine Karte, die sich "
    "selbst nutzt (zurückholen, Phoenix, Flashback, Fähigkeit), sonst seine teuerste Kreatur.",
    "Statische Effekte: First Strike im eigenen Zug (Skilled Battlecarver), Threshold +1/+1 (Void Extrapolator), "
    "Flying und Haste nach Schaden außerhalb des Kampfs am Gegner (Whiplash Wordsmith; kommt dann schon in Main 1, "
    "auch zusammen mit seiner Vicious-Verse-Kopie), Haste für Thopter (Saheeli), Vigilance mit Marke (Vigorbloom "
    "Vanguard), Trample für andere (Ghalta the Unstoppable), Defender greift an (Ghalta the Immovable), Marken beim "
    "Betreten und beim Tod weitergeben (Graft Surgeon), Karte ziehen, wenn ein gegnerischer Zauber sie zum Ziel hat "
    "(Ruric Thar). Kostensenkung (601.2f, auch im Goldfish): Ghalta um die höchste Power bzw. Toughness, Wrath of the "
    "Bloodmane mit legendärer Kreatur, Traxos, wenn in diesem Zug zuerst ein Nichtkreatur-Zauber gewirkt wird.",
    "Scry/Surveil-Auslöser: Prudent Fateseer (alle +1/+0) und Saheeli, Consul of Oversight (Thopter) einmal pro Zug, "
    "Proft bei jedem Surveil ({2} mit freiem Mana: Marke und eine Karte). Bringt ein Surveil im Kampf etwas "
    "(Fateseer, Desperate Futurescribe), surveilt Jace mit weniger als 3 Loyalty schon vor dem Kampf; "
    "Surveil-Fähigkeiten mit freiem Mana vor dem Angriff, wenn dadurch mehr Schaden durchkommt. Futurescribe: zu "
    "Beginn des eigenen Kampfs bekommt der stärkste andere Angreifer +1/+1, nach einem Surveil eine Marke.",
    "Tod und Opfern: Way of the Necromancer gibt einem vorhandenen Jace je gestorbene eigene Kreatur eine Loyalty, "
    "Edgar, Ancient Bloodlord 1 Leben je andere gestorbene Kreatur. Der Jace-Token stirbt mit 0 Loyalty (704.5i, "
    "700.4) und löst Edgar und Massacre Girl aus. Edgar opfert ({2}, Marke und Menace): einen Blocker, der stirbt, "
    "ohne den Angreifer zu töten (der Angreifer bleibt geblockt, 509.1h; nicht gegen Trample); eine Kreatur, auf die "
    "ein gegnerisches Removal zielt (Destroy, Schaden, −X/−X, Marken, Lock; der Zauber hat dann kein Ziel mehr, "
    "608.2b); vor dem Angriff die schwächsten anderen Kreaturen (Token zuerst), wenn das Lethal ergibt – gerechnet "
    "ohne den Schaden der Geopferten.",
    "Ziehen per Fähigkeit: Loot (ziehen, dann abwerfen) am Ende des gegnerischen Zugs; Arni, Humble Scribe lootet "
    "auch im eigenen Zug vor einer Nicht-Token-Kreatur, die ihn wieder enttappt. Rummage (erst abwerfen: Hallway "
    "Heckler, Improvised Act) nur mit überzähligem Land; Marwyn, the Clearcutter opfert ein Land ab 6 Ländern auf dem "
    "Feld, wenn es mehr sind als der höchste Manawert der Hand. {T}-Fähigkeiten nur von Kreaturen, die seit Beginn "
    "des eigenen Zugs da sind (302.6).",
    "Ausweichen mit {T}-Fähigkeiten (Eardrum Rattler: unblockbar für Power bis 2; Tomik: Flying für eine Kreatur mit "
    "Marke) vor dem Angriff, wenn insgesamt mehr Schaden durchkommt, obwohl die Quelle nicht angreift. Pia: +X/+0, X = "
    "unsere Artefakte (auch Treasure). Arni, Renowned Champion wächst um die Power jeder neuen Kreatur; kann er "
    "angreifen, kommen Kreaturen schon in Main 1. Gideon the Oathless: 1 Schaden für jede Kreatur und jede "
    "Jace-Aktivierung des Gegners.",
    "Ward (702.21): Ziel ist die gefährlichste Kreatur, deren Ward wir zahlen können, sonst die nächstbeste; in der "
    "Main Phase werden die Ward-Kosten wie Zusatzkosten eingeplant (ohne bezahlbares Ziel wird der Zauber nicht "
    "gewirkt). „Discard a card“ zahlen wir mit der Karte, die wir sonst auch abwerfen würden. Gilt auch für Removal "
    "beim Betreten und Lock-Auras, für beide Seiten.",
    "Ghalta the Immovable: unsere Kreaturen mit mehr Toughness als Power machen Kampfschaden in Höhe ihrer "
    "Toughness (als Angreifer und Blocker, auch für Lifelink, Trample, Angriffs- und Blockplanung und Lethal); "
    "Defender greift an. Fight und „damage equal to its power“ bleiben bei der Power.",
    "−N/−0-Kampftricks (Icy Reception) nach den Blocks: als Verteidiger auf einen Angreifer, wenn dadurch ein "
    "Blocker überlebt, gegen Lethal oder wenn ein ungeblockter Angreifer mindestens 4 Schaden weniger macht; als "
    "Angreifer auf einen Blocker, wenn unser Angreifer dadurch überlebt. Counterspell-Modi werden nicht genutzt. "
    "Cryotheory Adept aus dem Friedhof (Sorcery-Zeit, freies Mana): tappt die gefährlichste Kreatur des Gegners, "
    "die blocken könnte oder 3+ Kampfschaden macht; die Stun-Marke hält sie beim nächsten Untap getappt (122.1g).",
    "Blazing Crescendo: die oberste Karte ins Exil, bis Ende unseres nächsten Zugs in der Main Phase spielbar "
    "(Länder als Landdrop). Lyra, Tolarian Archangel: am Ende jedes Zugs ein 3/3-Engel mit Flying, wenn wir in "
    "diesem Zug 3 oder mehr Karten gezogen haben (alle Ziehungen zählen); ihre Fähigkeit vor dem Angriff mit freiem "
    "Mana, wenn sie angreift und kein Blocker sie aufhalten kann. Ausrüstung (Warrior's Blades): vor dem Angriff "
    "mit freiem Mana an den stärksten Angreifer (Gleichstand: meiste Marken, Equip {1} billiger je Marke); "
    "umgehängt nur, wenn die bisherige Kreatur nicht angreifen kann; stirbt sie, bleibt die Ausrüstung liegen.",
    "Counterspells (701.6): Vor dem Auflösen jedes Zaubers darf der andere Spieler kontern. Gekontert wird nur, "
    "1. was Lethal bringt (Schaden am Spieler, Kampftrick oder Kreatur mit Haste, mit denen der Angriff Lethal wird), "
    "2. Removal auf unsere gefährlichste Kreatur (auch Massenremoval, das sie tötet; keine Edikte), 3. eine Kreatur "
    "ab Manawert 3. Der billigste passende Counterspell (Farbe, Kreatur/Nichtkreatur); „unless its controller pays "
    "{N}“ nur, wenn der Zaubernde nicht zahlen kann (er zahlt, wenn er kann, plant es aber nicht ein). Ab Runde 5 "
    "halten wir Mana für den billigsten Counterspell frei (mit Removal zusammen, wenn das Mana reicht, sonst nur den "
    "Counterspell). Gekonterte Zauber gehen in den Friedhof (Flashback: Exil); Auslöser beim Wirken passieren "
    "trotzdem. Countersculpt: „behold a Jace“ mit Jace-Token oder Jace-Karte auf der Hand, sonst {1} mehr. "
    "Fähigkeiten sind keine Zauber und können nicht gekontert werden.",
    "Festgelegt: keine Gegenkonter. Ein Counterspell ist keiner der drei Gründe, also wird er selbst nie gekontert "
    "(bewusst so gewählt, kann später erweitert werden).",
    "Splinter Twin: kommt auf eine eigene Kreatur mit Betreten-Effekt (höchster Removal-Score, dann Manawert), sonst "
    "auf die gefährlichste nicht legendäre; legendäre nur, wenn ihr Betreten-Effekt Lethal bringt. Gewirkt wird Twin "
    "nur, wenn die Kreatur schon liegt. Die Kopie (707.2: nur aufgedruckte Werte, dazu Haste) entsteht am Ende des "
    "gegnerischen Zugs; nach 513.2 lebt sie bis zu unserem Zugende und greift neben dem enttappten Original an. Im "
    "eigenen Zug nur, wenn sie Lethal bringt. Betreten-Effekte der Kopie wirken (603.6a), „if you cast it“ nicht; "
    "eine legendäre Kopie stirbt nach ihrem Effekt an der Legend-Regel. Twin geht mit der Kreatur in den Friedhof "
    "(704.5m). Im Goldfish genauso, gegen einen Gegner, der nichts tut.",
    "Verliehene Loyalty-Fähigkeiten (Way of the …, Sanctum Lurker, Kiora, Avatar) für den Jace-Token: eine "
    "Aktivierung pro Zug (606.3), Minus-Kosten nur mit genug Loyalty (606.6). Wahl: Lethal (Schaden am Gegner, oder "
    "Warlord tötet den Blocker, der Lethal verhindert) > Removal (Warlord tötet die gefährlichste Kreatur) > großes "
    "Token (Leviathan vor Beast; Deathbringer opfert eine Kreatur unter 4/4, Token zuerst; Avatar ab 4 Ländern) > "
    "Ziehen > Cadet und Surveil > Plus-Fähigkeit (Lurker; Pyromancer nur, wenn das {R} einen Zauber ermöglicht) > "
    "Surveil. Ziehen zu Beginn des Zugs, Lethal/Removal/Mana/Marken in Main 1 vor dem Zaubern (mit Kiora jede "
    "Fähigkeit), sonst nach Main 2. Way of the Mind Sculptor: Karte bei −2 oder mehr; Way of the Paradox: 1 Leben "
    "und ein weiterer Landdrop (dann wird schon zu Beginn des Zugs aktiviert); Kiora: nach einer Aktivierung wird "
    "der stärkste Angreifer enttappt und unblockbar. Sanctum Lurker: Jace bleibt mit 0 Loyalty liegen (nie "
    "negativ), stirbt aber, wenn Lurker geht. Im Goldfish dieselbe Wahl ohne Token.",
    "Way of the Cryomancer (−3: den nächsten Instant/Sorcery dieses Zugs kopieren): nur in Main 1 vor dem Zaubern, "
    "bewertet wird der erste geplante Instant/Sorcery: Lethal (Schaden doppelt reicht) 8, Removal mit einem zweiten "
    "gültigen Ziel 6, Ziehen 4, sonst 2; echte Planeswalker nur für Lethal oder Removal. Die Kopie wird nicht gewirkt "
    "(707.10: kein Prowess, kein „whenever you cast“), löst zuerst auf und wählt neue Ziele (707.10c); Empower gehört "
    "zum Effekt und zählt mit. Mit Cryomancer und Instant/Sorcery auf der Hand zieht der Jace-Token nicht schon zu "
    "Beginn des Zugs. Jace's Machinations: am Ende des gegnerischen Zugs (Empower 8), danach je eine weitere "
    "Aktivierung des Jace-Tokens und jedes echten Jace-Planeswalkers (606.3 zählt je Zug), andere Planeswalker nicht. "
    "Im Goldfish genauso, die Kopie aber nur für Schaden.",
    "Tomik, Orzhov Lawmage: höchstens ein Angreifer je Planeswalker seines Spielers, der schwächste, der ihn tötet, "
    "sonst der stärkste; auf den Jace-Token nur ein einzelner Angreifer, der reicht. Entrust the Spark: nur mit "
    "Jace-Token, der geopfert wird (stirbt, 700.4), nie ein echter Planeswalker; geholt wird der Planeswalker mit dem "
    "höchsten Manawert ohne Legend-Konflikt, er darf im selben Zug aktivieren. Loyal Tutor: am Ende des gegnerischen "
    "Zugs, wenn kein Planeswalker auf der Hand ist; oben auf die Bibliothek kommt der teuerste, den wir nächste Runde "
    "bezahlen können (Länder + 1), sonst der billigste. Teyo legt seine Marke nie auf einen Planeswalker. Im Goldfish "
    "Entrust und Loyal Tutor genauso.",
    "Echte Planeswalker (L2): kommen mit ihrer aufgedruckten Loyalty (306.5b), eine Loyalty-Fähigkeit pro Zug "
    "(606.3), Minus-Kosten nur mit genug Loyalty (606.6), −X so groß wie möglich ohne zu sterben, Tod bei 0 "
    "(704.5i, mit Sanctum Lurker nicht). Wahl: Lethal > Ultimate (−6 oder mehr) oder Emblem > Removal > großes Token "
    "(ab 4/4) > Ziehen > kleines Token > Plus mit Wert > Plus ohne Wert; eine Minus-Fähigkeit, die auf 0 bringt, nur "
    "für Lethal, Ultimate oder Removal. Ein Emblem „whenever you cast a spell“ nur mit einem Zauber auf der Hand. "
    "Zeitpunkt: vorhandene Planeswalker in Main 1 vor dem Zaubern (Team-Pump und Angriffs-Buff erst direkt vor dem "
    "Kampf), frisch gewirkte nach den Zaubern aus Main 1, sonst nach Main 2. Verliehene Fähigkeiten (Way of the …) "
    "und Auslöser bei Aktivierungen (Ajani Unrelenting: Cadet auch für den Jace-Token, Mind Sculptor, Paradox, "
    "Gideon, Tethermage, Mentor, Necromancer) gelten auch für sie. Angriff: echte Planeswalker des Gegners immer, mit "
    "so wenig Schaden wie nötig (der kleinste Angreifer, der reicht, sonst die schwächsten bis es reicht; reicht "
    "alles nicht, greift alles Übrige ihn an); Lethal auf den Spieler geht vor; Schaden nimmt Loyalty (120.3c). "
    "Removal „creature or planeswalker“: ein echter Planeswalker, wenn es ihn tötet und der Gegner keine Kreatur mit "
    "Power 4+ hat; der Jace-Token nur ab 5 Loyalty und ohne Kreatur als Ziel. Nicht modelliert: das Wirken der von "
    "Chandra exilierten Karte, Jace, Reality Sculptors Sieg-Fähigkeit, Garruk, Veiled Butchers Exil statt Sterben. "
    "Im Goldfish ohne Token und Removal (Schaden, Ziehen, Mana, Marken, Embleme, Empower).",
    "Heartwood-Token (111.10x, Artefakt mit {T}: {R} oder {G}) aus Soul Tether, Aerid Konstrari, Hungering "
    "Puppetbeast: Mana ab dem nächsten Zug. Statische Team-Effekte, auch von Verzauberungen: Samut (alle haben "
    "Haste), Ajani's Anguish (Trample), Tetsuko Umezawa, Fugitive (Power oder Toughness höchstens 1: unblockbar), "
    "Gallia (Haste mit Marke), Master of Barbs (+1/+0 bei Schaden außerhalb des Kampfs am Gegner). Scry/Surveil: "
    "Denzilore (Marke auf jede Kreatur) und Diviner of Victory (+1/+1) bei jedem Surveil; Proctor of Potential "
    "surveilt, wenn eine eigene Kreatur kommt. Abwerfen (701.9): Tinybones schädigt bei jedem Abwerfen eines "
    "Spielers; Loot als Effekt (Divining Duelist, Echoverse Fulcrum) und als Artefakt-Fähigkeit (Murmuring Volume). "
    "Jiang Yanggu: legendäres Token Mowu, eigene Token enttappen am Zugende. Proft, Sinister Mastermind erst ab "
    "Threshold wirkbar (601.3). „You lose N life“ beim Auflösen.",
    "Exil bis zum Verlassen (610.3; Memory Trap, Solitary Cell): die gefährlichste passende Kreatur, sonst ein "
    "Nichtkreatur-Permanent. Verlässt die Falle das Spielfeld, kommt die Karte unter der Kontrolle ihres Besitzers "
    "zurück (610.3c) als neues Objekt (400.7: ohne Marken, mit Einsatzverzögerung, Betreten-Effekte wirken); Token "
    "nicht (111.8). Nichtkreatur-Ziele: 1. Falle mit unserer Karte, 2. Lock-Aura auf unserer Kreatur, 3. Splinter "
    "Twin oder Ausrüstung an seiner Kreatur, 4. sonstige Verzauberungen/Artefakte (Way of … vor anderen, dann "
    "Manawert), nie Token. Budding Insurgent opfert sich nur für Rang 1–3 (Karte bei legendärer Verzauberung); "
    "Archive Arbiter zerstört bei Rang 1–4, sonst 4 Leben. Lock-Auras geben die Kreatur frei, wenn sie gehen, und "
    "gehen, wenn die Kreatur geht (704.5m). Clash of Elements wie Plan for All Outcomes, oben mit 2 Schaden; Vraska, "
    "the Cutting Glare ab 6 Ländern (der Gegner bekommt ein Treasure); Living Library mit 6 offenem Mana gegen die "
    "gefährlichste Kreatur (in die Bibliothek gemischt); The Echoverse Fulcrum, wenn die gegnerischen Kreaturen "
    "(Manawert + Power) mindestens doppelt so viel wert sind wie unsere.",
    "Noch nicht im Kampf: weitere Auslöser und Fähigkeiten (siehe Modell-Abdeckung). Solche Karten werden gewirkt, "
    "wirken aber nur mit den schon modellierten Effekten.",
]

CSS = """
.proto td{vertical-align:top;font-size:12.5px;padding:5px 6px}
.proto th{white-space:normal;vertical-align:bottom;padding:5px 6px}
.proto tr.p-Wir td:first-child,.proto tr.p-Wir td:nth-child(2){border-left:3px solid var(--play)}
.proto tr.p-Gegner td:first-child,.proto tr.p-Gegner td:nth-child(2){border-left:3px solid var(--draw)}
.proto .dead{color:var(--bad);font-weight:600}
.proto .small{font-size:12px;color:var(--muted)}
.gfilter{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:8px;font-size:13px}
.gfilter select{font:inherit;padding:3px 8px;border-radius:8px;border:1px solid var(--line);background:var(--panel);color:var(--text)}
.glist{max-height:340px;overflow:auto}
.glist tr.game{cursor:pointer}
.glist tr.game:hover td{background:var(--chip)}
.glist tr.game.sel td{background:var(--chip);font-weight:600}
.res-win{color:var(--good);font-weight:600}.res-loss{color:var(--bad);font-weight:600}
.mull{color:var(--bad);font-weight:700}
.hands{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px;margin:8px 0 12px}
.kpi .v .vs{font-size:14px;color:var(--muted);font-weight:600;margin:0 4px}
.kpi .v small{font-size:12px;color:var(--muted);font-weight:600;margin-right:2px}
"""


def _avg(xs):
    return f"{sum(xs) / len(xs):.1f}" if xs else "–"


def _fastest(results, key):
    """(Spiel, Modus) mit der kleinsten Runde ueber beide Modi oder (None, None)."""
    best = None
    for mode in MODES:
        g = results[mode][key]
        if g and (best is None or g["round"] < best[0]["round"]):
            best = (g, mode)
    return best or (None, None)


def _attacks_html(attacks):
    out = []
    for at in attacks:
        att = esc(at["attacker"]) + (' <span class="dead">†</span>' if at["attacker_dies"] else "")
        if at.get("jace"):
            att += " (auf Jace)"
        if at.get("walker"):
            att += f" (auf {esc(at['walker'])})"
        if not at["blockers"]:
            out.append(f"{att} → ungeblockt")
        else:
            bl = ", ".join(esc(b) + (' <span class="dead">†</span>' if d else "")
                           for b, d in zip(at["blockers"], at["blockers_die"]))
            out.append(f"{att} ✕ {bl}")
    return "<br>".join(out) or "–"


def _protocol(game, mode, title):
    """Zugprotokoll eines Spiels."""
    hands = "".join(
        f'<div class="panel"><b>Starthand {esc(who)}</b>'
        f'{" <span class=small>(" + str(game["mulligans"][who]) + " Mulligan)</span>" if game["mulligans"][who] else ""}'
        f'<div class="small" style="margin-top:4px">{esc(", ".join(game["opening"][who]))}</div></div>'
        for who in ("Wir", "Gegner"))
    rows = []
    for e in game["log"]:
        life = e.get("life") or {}
        board = e.get("board") or {}
        dmg = str(e["damage"]) + (f' + {e["face"]} direkt' if e["face"] else "")
        cls = f'p-{e["player"]}'
        cells = [f'<td>{e["round"]}</td>', f'<td class="l"><b>{esc(e["player"])}</b></td>',
                 f'<td class="l">{esc(e["drew"] or "–")}</td>', f'<td class="l">{esc(e["land"] or "–")}</td>',
                 f'<td class="l">{esc(", ".join(e["main1"]) or "–")}</td>',
                 f'<td class="l">{_attacks_html(e["attacks"])}</td>',
                 f'<td class="l">{esc(", ".join(e["main2"]) or "–")}</td>',
                 f'<td class="l small">{"<br>".join(esc(x) for x in e.get("events", [])) or "–"}</td>',
                 f'<td>{dmg}</td>',
                 f'<td>{life.get("Wir", "–")} / {life.get("Gegner", "–")}</td>',
                 f'<td class="l small">Wir: {esc(", ".join(board.get("Wir", [])) or "–")}<br>'
                 f'Gegner: {esc(", ".join(board.get("Gegner", [])) or "–")}'
                 + (f'<br><b>{esc(e["note"])}</b>' if e.get("note") else "") + '</td>']
        rows.append(f'<tr class="{cls}">' + "".join(cells) + "</tr>")
    head = "".join(f'<th class="{"l" if i in (1, 2, 3, 4, 5, 6, 7, 10) else ""}">{h}</th>' for i, h in enumerate(
        ["Runde", "Spieler", "Zieht", "Land", "Main 1", "Kampf († = stirbt)", "Main 2",
         "Removal, Instants, Flash", "Schaden", "Leben Wir / Gegner", "Feld danach"]))
    return (f'<div class="note" style="margin:0 0 6px"><b>{esc(title)}</b> in Runde {game["round"]} '
            f'({esc(mode)})</div><div class="hands">{hands}</div>'
            f'<div class="panel"><div class="tw"><table class="proto"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div></div>')


SWITCH_JS = """<script>
document.documentElement.classList.add('js');
document.querySelectorAll('.gsw button').forEach(function(b){  // Farben wie im Drafthelper
  var t=b.textContent.trim().toLowerCase();
  if(t==='splash')b.classList.add('v-splash');else if(t==='nosplash')b.classList.add('v-nosplash');});
function showGroup(g){
  document.querySelectorAll('[data-g]').forEach(function(e){e.classList.toggle('on',e.getAttribute('data-g')===g)});
}
document.querySelectorAll('.gsw button').forEach(function(b){b.addEventListener('click',function(){
  var g=b.getAttribute('data-g'),sec=b.getAttribute('data-sec');
  var top=b.closest('section').getBoundingClientRect().top;
  showGroup(g);
  var target=document.getElementById(g==='0'?sec:sec+'-'+g);
  if(target)window.scrollTo({top:window.scrollY+target.getBoundingClientRect().top-top,behavior:'instant'});});});
</script>"""


MULL_WARN = 0.05  # Hinweis, wenn mehr als 5 % der Spiele durch Mulligan-Aufgabe verloren gehen

SPECIALS = [  # (Schluessel, Abschnitt, Titel, Auswahl ueber beide Modi)
    ("fastest_win", "sieg", "Schnellster Sieg", lambda g: g["round"]),
    ("fastest_loss", "niederlage", "Schnellste Niederlage", lambda g: g["round"]),
    ("closest_win", "knapp-sieg", "Knappster Sieg", lambda g: (_end_life(g, "Wir"), g["round"])),
    ("closest_loss", "knapp-niederlage", "Knappste Niederlage", lambda g: (_end_life(g, "Gegner"), -g["round"])),
    ("comeback_win", "gedreht-sieg", "Gedrehter Sieg", lambda g: (-_max_gap(g, "Wir"), g["round"])),
    ("comeback_loss", "gedreht-niederlage", "Gedrehte Niederlage", lambda g: (-_max_gap(g, "Gegner"), g["round"])),
]
SPECIAL_NOTE = {
    "closest_win": "Sieg mit den wenigsten eigenen Lebenspunkten am Ende",
    "closest_loss": "Niederlage, bei der der Gegner am Ende die wenigsten Lebenspunkte hatte",
    "comeback_win": "Sieg nach dem größten Rückstand an Lebenspunkten",
    "comeback_loss": "Niederlage nach dem größten Vorsprung an Lebenspunkten",
}
MODE_KEY = {"On the Play": "play", "On the Draw": "draw"}

GAMES_JS = """<script>
(function(){
  var served=location.protocol.indexOf('http')===0;
  document.querySelectorAll('.gamesbox').forEach(function(box){
    var view=box.querySelector('.gameview');
    function filter(){
      var m=box.querySelector('.fmode').value,r=box.querySelector('.fres').value;
      box.querySelectorAll('tr.game').forEach(function(tr){
        var ok=(m===''||tr.getAttribute('data-m')===m)&&(r===''||tr.getAttribute('data-r')===r);
        tr.style.display=ok?'':'none'});
    }
    box.querySelector('.fmode').addEventListener('change',filter);
    box.querySelector('.fres').addEventListener('change',filter);
    box.querySelectorAll('tr.game').forEach(function(tr){tr.addEventListener('click',function(){
      box.querySelectorAll('tr.game.sel').forEach(function(x){x.classList.remove('sel')});tr.classList.add('sel');
      if(!served){view.innerHTML='<p class="muted">Das Protokoll einzelner Spiele gibt es nur, solange draftgott läuft '+
        '(Drafthelper oder Analyse). Die besonderen Spiele stehen oben.</p>';return}
      view.innerHTML='<p class="muted">Lade Protokoll …</p>';
      fetch('game?d='+tr.getAttribute('data-d')+'&e='+tr.getAttribute('data-e')+'&m='+tr.getAttribute('data-m')+
        '&n='+tr.getAttribute('data-n')).then(function(r){return r.text()}).then(function(h){view.innerHTML=h;
        view.scrollIntoView({block:'nearest'})}).catch(function(){view.innerHTML='<p class="muted">Fehler beim Laden.</p>'});
    })});
  });
})();
</script>"""


def protocol_html(game, mode, title):
    """Protokoll eines einzelnen Spiels (fuer die Spieleliste auf Abruf)."""
    return _protocol(game, mode, title)


def _pct(n, d):
    return f"{n / d:.0%}" if d else "–"


def _kpi_tiles(decks):
    """Kacheln: Siegquote je Gegner (und Variante), Play und Draw."""
    multi = len(decks) > 1
    tiles = []
    for dd in decks:
        for b in dd.get("battles") or []:
            vals = []
            for mode in MODES:
                r = b["results"][mode]
                vals.append(f'<small>{"Play" if mode == MODES[0] else "Draw"}</small>{r["wins"] / (r["games"] or 1):.0%}')
            head = (f'{esc(dd["name"])} · ' if multi else "") + f'gegen {esc(b["enemy"])}'
            tiles.append(f'<div class="panel kpi"><div class="l">{head}</div>'
                         f'<div class="v">{vals[0]}<span class="vs">/</span>{vals[1]}</div>'
                         f'<div class="s">Siege On the Play / On the Draw</div></div>')
    return f'<div class="grid g4" style="margin-bottom:14px">{"".join(tiles)}</div>' if tiles else ""


def _overview(decks):
    rows, warnings = [], []
    draws = any(b["results"][m]["draws"] for dd in decks for b in dd.get("battles") or [] for m in MODES)
    for dd in decks:
        for b in dd.get("battles") or []:
            for mode in MODES:
                r = b["results"][mode]
                n = r["games"] or 1
                played = n - r["mull_losses"]
                mull = (f'<td class="bad">{r["mull_losses"]} ({_pct(r["mull_losses"], n)})</td>'
                        if r["mull_losses"] else '<td class="muted">0</td>')
                rows.append([f'<td class="l"><b>{esc(dd["name"])}</b></td>', f'<td class="l">{esc(b["enemy"])}</td>',
                             h_mode(mode), h_bar_cell(r["wins"] / n, f'{r["wins"] / n:.0%}', LABEL_CLASS.get(mode, "")),
                             f'<td>{r["losses"] / n:.0%}</td>', mull]
                            + ([f'<td>{r["draws"] / n:.0%}</td>'] if draws else [])
                            + [f'<td>{_pct(r["wins"], played)}</td>',
                               f'<td>{_avg(r["win_rounds"])}</td>', f'<td>{_avg(r["loss_rounds"])}</td>'])
                if r["mull_losses"] / n > MULL_WARN:
                    warnings.append(f'{esc(dd["name"])} ({esc(mode)}): {r["mull_losses"]} von {n} Spielen '
                                    f'({r["mull_losses"] / n:.0%}) geben wir schon beim Mulligan auf')
    games = next((b["results"][MODES[0]]["games"] for dd in decks for b in dd.get("battles") or []), 0)
    warn = ('<div class="warnbox"><b>Mulligan-Aufgaben:</b> ' + "; ".join(warnings) + '. Die Hand fiel dabei unter '
            'die Mindestzahl an Karten (<code>--min-handkarten</code>).</div>') if warnings else ""
    heads = (["Deck", "Gegner", "", "Siege", "Niederlagen", "davon durch Mulligan"] + (["Unentschieden"] if draws else [])
             + ["Siege ohne Mulligan-Aufgaben", "Ø Runde Sieg", "Ø Runde Niederlage"])
    return (_kpi_tiles(decks) + warn + '<div class="panel">' + h_table(heads, rows, extra='class="wrap"',
                                                                        left=(0, 1, 2))
        + f'<div class="note">{games} Spiele je Deck und Modus. Runde = Zahl der eigenen Züge. „davon durch Mulligan“: '
          f'Niederlagen, weil unsere Hand unter die Mindestzahl fiel (der Gegner gibt nie auf). „Siege ohne '
          f'Mulligan-Aufgaben“: Siege unter den Spielen, die wirklich gespielt wurden. Mulligan-Aufgaben zählen nicht '
          f'bei Runden, Kennzahlen und besonderen Spielen.</div></div>')


def _verlauf(b):
    res = b["results"]
    rounds = max([max(r["win_by_round"], default=0) for r in res.values()] + [6])
    xs = list(range(1, rounds + 1))
    cum = {}
    for mode in MODES:
        r = res[mode]
        total, acc, vals = r["games"] or 1, 0, []
        for t in xs:
            acc += r["win_by_round"].get(t, 0)
            vals.append(acc / total)
        cum[mode] = vals
    charts = [f'<div class="panel"><b>Siege bis Runde N</b> <span class="muted">(Anteil aller Spiele)</span>'
              f'{svg_lines(xs, cum)}</div>']
    for mode in MODES:
        curve = res[mode]["life_curve"]
        n = len(curve["Wir"])
        if not n:
            charts.append(f'<div class="panel"><b>Lebenspunkte {esc(mode)}</b><p class="muted">keine Spiele</p></div>')
            continue
        top = max(20, max(curve["Wir"] + curve["Gegner"]))
        charts.append(f'<div class="panel"><b>Lebenspunkte je Runde – {esc(mode)}</b> '
                      f'<span class="muted">(Ø über alle gespielten Spiele, nach Spielende der letzte Stand)</span>'
                      + svg_lines(list(range(1, n + 1)), curve, ymax=top, fmt=lambda v: f"{v:.0f}",
                                  classes={"Wir": "play", "Gegner": "draw"})
                      + '<div class="legend"><span><span class="dot play"></span>Wir</span>'
                        '<span><span class="dot draw"></span>Gegner</span></div></div>')
    rows = []
    for mode in MODES:
        r = res[mode]
        rows.append([h_mode(mode), f'<td>{_avg(r["end_life_win"])}</td>', f'<td>{_avg(r["end_life_loss"])}</td>',
                     f'<td>{r["combat_damage"]["Wir"]:.1f} / {r["combat_damage"]["Gegner"]:.1f}</td>',
                     f'<td>{r["direct_damage"]["Wir"]:.1f} / {r["direct_damage"]["Gegner"]:.1f}</td>',
                     f'<td>{r["deaths"]["Wir"]:.1f} / {r["deaths"]["Gegner"]:.1f}</td>'])
    table = ('<div class="panel"><b>Kennzahlen je Spiel</b>' + h_table(
        ["", "Ø Leben am Ende (Sieg, unsere)", "Ø Leben am Ende (Niederlage, Gegner)", "Ø Kampfschaden Wir / Gegner",
         "Ø direkter Schaden Wir / Gegner", "Ø gestorbene Kreaturen Wir / Gegner"], rows)
             + '<div class="note">Direkter Schaden: Burn, Landfall, „any target“ an den Gegner. Ohne Spiele, die durch '
               'Mulligan entschieden wurden.</div></div>')
    return f'<div class="grid g2">{"".join(charts)}</div>{table}'


def _games_list(d_idx, e_idx, b):
    rows = []
    for mode in MODES:
        for g in b["results"][mode]["games_list"]:
            if g["mulligan_loss"]:
                res, cls, rkey = "Aufgabe (Mulligan)", "mull", "mull"
            elif g["winner"] == "a":
                res, cls, rkey = "Sieg", "res-win", "win"
            elif g["winner"] == "b":
                res, cls, rkey = "Niederlage", "res-loss", "loss"
            else:
                res, cls, rkey = "Unentschieden", "muted", "draw"
            mull = f'{g["mulligans"]["Wir"]} / {g["mulligans"]["Gegner"]}'
            rows.append(f'<tr class="game" data-d="{d_idx}" data-e="{e_idx}" data-m="{MODE_KEY[mode]}" '
                        f'data-n="{g["n"]}" data-r="{rkey}"><td>{g["n"] + 1}</td>{h_mode(mode)}'
                        f'<td class="l {cls}">{res}</td><td>{g["round"] or "–"}</td>'
                        f'<td>{g["life"]["Wir"]} / {g["life"]["Gegner"]}</td><td>{mull}</td></tr>')
    head = "".join(f'<th class="{"l" if i == 2 else ""}">{h}</th>' for i, h in enumerate(
        ["Nr.", "Modus", "Ergebnis", "Runde", "Leben Wir / Gegner", "Mulligans Wir / Gegner"]))
    filters = ('<div class="gfilter">Modus <select class="fmode"><option value="">alle</option>'
               '<option value="play">On the Play</option><option value="draw">On the Draw</option></select>'
               'Ergebnis <select class="fres"><option value="">alle</option><option value="win">Siege</option>'
               '<option value="loss">Niederlagen</option><option value="mull">Aufgabe (Mulligan)</option>'
               '<option value="draw">Unentschieden</option></select>'
               '<span class="muted">Klick auf ein Spiel zeigt sein Protokoll (solange draftgott läuft).</span></div>')
    return (f'<div class="panel gamesbox">{filters}<div class="glist tw"><table><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div><div class="gameview" id="gameview"></div></div>')


def _nav_links(items):
    """Links der Seitenleiste; Abschnitte je Gegner in einer einklappbaren Gruppe."""
    out, groups = [], {}
    for item in items:
        sid, label = item[0], item[1]
        enemy = item[2] if len(item) > 2 else None
        if enemy is None:
            out.append(f'<a href="#{sid}">{esc(label)}</a>')
        else:
            if enemy not in groups:
                groups[enemy] = []
                out.append(enemy)
            groups[enemy].append(f'<a href="#{sid}">{esc(label)}</a>')
    return "".join(x if x.startswith("<a") else
                   f'<details open><summary>gegen {esc(x)}</summary>{"".join(groups[x])}</details>' for x in out)


def _side_kpis(decks):
    """Siegquote je Gegner (Play / Draw) fuer die Seitenleiste; bei mehreren Varianten je Variante umschaltbar."""
    blocks = []
    for i, dd in enumerate(decks):
        rows = []
        for b in dd.get("battles") or []:
            cells = [f'<td class="l">{esc(b["enemy"])}</td>']
            for mode in MODES:
                r = b["results"][mode]
                cells.append(f'<td>{r["wins"] / (r["games"] or 1):.0%}</td>')
            rows.append(cells)
        table = h_table(["Gegner", "Play", "Draw"], rows) if rows else '<p class="muted">–</p>'
        if len(decks) > 1:
            blocks.append(f'<div class="sidekpi grpkpi{" on" if i == 0 else ""}" data-g="{i}">'
                          f'<div class="kvar">{esc(dd["name"])}</div>{table}</div>')
        else:
            blocks.append(f'<div class="sidekpi">{table}</div>')
    return "".join(blocks)


def render_battle_html(decks, args):
    enemies = []
    for dd in decks:
        for b in dd.get("battles") or []:
            if b["enemy"] not in enemies:
                enemies.append(b["enemy"])
    title = "Kampf gegen " + ", ".join(enemies)
    multi = len(decks) > 1
    names = [d["name"] for d in decks]
    games = next((b["results"][MODES[0]]["games"] for dd in decks for b in dd.get("battles") or []), 0)
    sections = [h_section("uebersicht", "Übersicht", "Wie oft gewinnen wir?", _overview(decks))]
    nav = [("uebersicht", "Übersicht")]

    groups, navs = [], []
    for i, dd in enumerate(decks):
        suffix = "" if i == 0 else f"-{i}"
        secs, nv = [], []

        def add(base, heading, body, hint="", short=None, enemy=None):
            html = h_section(base + suffix, heading, hint, body)
            if multi:
                buttons = "".join(f'<button type="button" data-g="{k}" data-sec="{base}" '
                                  f'class="{"on" if k == i else ""}">{esc(n)}</button>' for k, n in enumerate(names))
                html = html.replace("</h2>", f'<span class="gsw">{buttons}</span></h2>', 1)
            secs.append(html)
            nv.append((base + suffix, short or heading, enemy))

        for e_idx, b in enumerate(dd.get("battles") or []):
            tag = "" if e_idx == 0 else str(e_idx)
            vs = f" gegen {b['enemy']}" if len(enemies) > 1 else ""
            add("verlauf" + tag, "Verlauf und Kennzahlen" + vs, _verlauf(b), short="Verlauf und Kennzahlen",
                enemy=b["enemy"])
            for key, sid, label, order in SPECIALS:
                cands = [(b["results"][m][key], m) for m in MODES if b["results"][m].get(key)]
                if cands:
                    game, mode = min(cands, key=lambda gm: order(gm[0]))
                    body = _protocol(game, mode, label)
                else:
                    body = (f'<div class="panel"><p class="muted">In keinem Spiel gegen {esc(b["enemy"])} '
                            f'({"kein Sieg" if "win" in key else "keine Niederlage"}).</p></div>')
                add(sid + tag, label + vs, body, SPECIAL_NOTE.get(key, ""), short=label, enemy=b["enemy"])
            add("spiele" + tag, "Alle Spiele" + vs, _games_list(i, e_idx, b), short="Alle Spiele", enemy=b["enemy"])
        if multi:
            groups.append(f'<div class="grp{" on" if i == 0 else ""}" data-g="{i}">'
                          f'<h2 class="gh">Details: {esc(dd["name"])}</h2>{"".join(secs)}</div>')
            navs.append(f'<div class="in grpnav{" on" if i == 0 else ""}" data-g="{i}">' + _nav_links(nav + nv) + "</div>")
        else:
            groups += secs
            nav += nv
    rules = h_section("regeln", "So funktioniert der Kampf", "",
                      '<div class="panel"><ul class="ass">' + "".join(f"<li>{r}</li>" for r in RULES) + "</ul></div>")
    if multi:
        nav_html = "".join(navs)
    else:
        nav_html = '<div class="in">' + _nav_links(nav) + "</div>"
    nav_html += '<div class="in"><a href="#regeln">So funktioniert der Kampf</a></div>'
    stamp = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    chips = [f"{games} Spiele je Modus", f"Rundengrenze {getattr(args, 'kampf_runden', 20)}",
             "Varianten: " + ", ".join(names)] + ([f"Seed {args.seed}"] if getattr(args, "seed", None) is not None else [])
    side_html = (f'<h3>Siegquote</h3>{_side_kpis(decks)}<div class="navsep"></div><h3>Abschnitte</h3>{nav_html}'
                 f'<div class="navsep"></div><h3>Einstellungen</h3>'
                 f'<div class="chips">{"".join(f"<span class=chip>{esc(c)}</span>" for c in chips)}</div>')
    return (f'<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)} – MTG Simulation</title><style>{HTML_CSS}{CSS}</style></head><body>'
            f'<header class="top" id="top"><h1>{esc(title)}</h1>'
            f'<span class="sub">Kampf-Simulation · erstellt am {stamp}</span>'
            '<a id="backlink" class="btn" href="report" style="display:none;margin-left:auto">← Zurück zum Bericht</a>'
            '</header>'
            f'<div class="layout"><nav>{side_html}</nav><main>{"".join(sections)}{"".join(groups)}{rules}</main></div>'
            f'<footer>Erzeugt mit mtg_sim.py · Kartendaten von Scryfall</footer>'
            + LAYOUT_JS + (SWITCH_JS if multi else "") + GAMES_JS
            + "<script>if(location.protocol.indexOf('http')===0)document.getElementById('backlink').style.display="
              "'inline-block'</script></body></html>")
