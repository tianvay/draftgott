@echo off
rem draftgott: Startmenue fuer den MTG-Simulator per Doppelklick. Zuerst die Sprache (1 = Deutsch, 2 = English,
rem   wird als --lang de/en weitergegeben), dann der Modus:
rem   1 = Analyse    (Deckliste _normaldeck.txt simulieren, Bericht meinbericht.html; laeuft weiter fuer den
rem                   Kampf aus dem Bericht, bis "Beenden" geklickt wird)
rem   2 = Drafthelper (Kartenseite im Browser mit _draftedcardpool.txt)
rem   3 = Live-Draft  (Drafthelper liest MTG Arena mit: Picks nach _livedraft.txt, Pack mit Bewertung und
rem                   Archetyp auf der Seite und im Seitenfenster ueber Arena)
rem   4 = Setauswertung (Draft-Statistik des Live-Drafts als HTML-Seite)
rem   5 = Turnier     (Gegnerdecks eines Unterordners von enemydecks, z. B. wc32, spielen gegeneinander;
rem                   Paarungen werden abgefragt, Bericht turnier_<Ordner>.html)
rem Zusaetzliche Parameter werden an den gewaehlten Aufruf angehaengt,
rem z. B.:  draftgott.bat --sims 1000
setlocal
cd /d "%~dp0"
title draftgott

rem Python suchen: erst der Windows-Launcher "py", dann "python"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo Python wurde nicht gefunden.
  echo Bitte Python 3.8 oder neuer installieren: https://www.python.org/downloads/
  echo Wichtig: bei der Installation "Add python.exe to PATH" anhaken.
  echo.
  echo Python was not found.
  echo Please install Python 3.8 or newer: https://www.python.org/downloads/
  echo Important: tick "Add python.exe to PATH" during installation.
  echo.
  pause
  exit /b 1
)

echo.
echo  draftgott
echo  ---------
echo   1 = Deutsch
echo   2 = English
echo.
choice /c 12 /n /m "Sprache / Language (1 oder/or 2): "
if errorlevel 2 goto en_menu
if errorlevel 1 goto de_menu
exit /b 1

:de_menu
set "LANGARG=--lang de"
echo.
echo   1 = Analyse       (_normaldeck.txt simulieren, Bericht meinbericht.html, Kampf im Bericht)
echo   2 = Drafthelper   (Karten aus _draftedcardpool.txt auswaehlen und vergleichen)
echo   3 = Live-Draft    (Arena mitlesen: Pack bewerten, Archetyp erkennen, Seitenfenster)
echo   4 = Setauswertung (Statistik der Drafts eines Sets als HTML-Seite)
echo   5 = Turnier       (Decks aus einem Unterordner von enemydecks gegeneinander, je Paarung 500 Spiele)
echo.
choice /c 12345 /n /m "Auswahl (1, 2, 3, 4 oder 5): "
if errorlevel 5 goto turnier
if errorlevel 4 goto setauswertung
if errorlevel 3 goto live
if errorlevel 2 goto drafthelper
if errorlevel 1 goto analyse
exit /b 1

:en_menu
set "LANGARG=--lang en"
echo.
echo   1 = Deck analysis (simulate _normaldeck.txt, report meinbericht.html, battles from the report)
echo   2 = Draft Helper  (pick and compare cards from _draftedcardpool.txt)
echo   3 = Live draft    (follow MTG Arena: rate the pack, detect the archetype, overlay)
echo   4 = Set report    (statistics of the drafts of a set as an HTML page)
echo   5 = Tournament    (decks from a subfolder of enemydecks against each other, 500 games per pairing)
echo.
choice /c 12345 /n /m "Choice (1, 2, 3, 4 or 5): "
if errorlevel 5 goto en_turnier
if errorlevel 4 goto en_setauswertung
if errorlevel 3 goto en_live
if errorlevel 2 goto en_drafthelper
if errorlevel 1 goto en_analyse
exit /b 1

:analyse
echo.
echo Analyse laeuft, der Bericht oeffnet sich danach im Browser ...
echo Dieses Fenster bitte offen lassen, solange du im Bericht "Kampf simulieren" nutzen willst.
echo Zum Beenden: Knopf "Beenden" im Bericht oder dieses Fenster schliessen.
goto run_analyse

:en_analyse
echo.
echo Analysis is running, the report opens in your browser afterwards ...
echo Please keep this window open as long as you want to use "Simulate battle" in the report.
echo To quit: button "Quit" in the report, or close this window.
goto run_analyse

:run_analyse
%PY% mtg_sim.py _normaldeck.txt --sims 10000 --html meinbericht.html --bericht-server %LANGARG% %*
goto ende

:drafthelper
echo.
echo Der Drafthelper wird gestartet, der Browser oeffnet sich gleich.
echo Dieses Fenster bitte offen lassen. Zum Beenden: Button "Beenden" auf der Seite
echo oder dieses Fenster schliessen.
echo.
goto run_drafthelper

:en_drafthelper
echo.
echo The Draft Helper is starting, your browser opens in a moment.
echo Please keep this window open. To quit: button "Quit" on the page
echo or close this window.
echo.
goto run_drafthelper

:run_drafthelper
%PY% mtg_sim.py --drafthelper _draftedcardpool.txt %LANGARG% %*
goto ende

:live
echo.
echo Live-Draft: Der Drafthelper liest das Protokoll von MTG Arena mit (Player.log).
echo Die Picks landen in _livedraft.txt, das Seitenfenster bleibt ueber Arena im Vordergrund.
echo Arena bitte im Fenster oder randlosen Vollbild spielen. In Arena muss unter Optionen - Konto
echo "Detailed Logs (Plugin Support)" eingeschaltet sein.
echo Dieses Fenster bitte offen lassen. Zum Beenden: Button "Beenden" auf der Seite.
echo.
goto run_live

:en_live
echo.
echo Live draft: the Draft Helper follows the MTG Arena log (Player.log).
echo Your picks go to _livedraft.txt, the overlay stays on top of Arena.
echo Please play Arena windowed or in borderless fullscreen. In Arena, Options - Account
echo "Detailed Logs (Plugin Support)" must be switched on.
echo Please keep this window open. To quit: button "Quit" on the page.
echo.
goto run_live

:run_live
%PY% mtg_sim.py --drafthelper _livedraft.txt --live %LANGARG% %*
goto ende

:setauswertung
echo.
echo Setauswertung: die gesammelten Drafts (draftstatistik.json) als HTML-Seite.
echo Ohne Angabe nimmt sie das Set mit den meisten Drafts, ein anderes z. B. mit:  draftgott.bat TRK
echo (dann 4 waehlen). Die Seite oeffnet sich danach im Browser.
echo.
goto run_setauswertung

:en_setauswertung
echo.
echo Set report: the collected drafts (draftstatistik.json) as an HTML page.
echo By default it takes the set with the most drafts; for another one use e.g.:  draftgott.bat TRK
echo (then choose 4). The page opens in your browser afterwards.
echo.
goto run_setauswertung

:run_setauswertung
%PY% mtg_sim.py --setauswertung %LANGARG% %*
goto ende

:turnier
echo.
echo Turnier: Decks aus einem Unterordner von enemydecks spielen gegeneinander.
echo Paarungen z. B. 1-3 2-4 (etwa wie in der Swiss-Runde), Enter = jeder gegen jeden.
echo Der Bericht oeffnet sich danach im Browser.
echo.
goto run_turnier

:en_turnier
echo.
echo Tournament: decks from a subfolder of enemydecks play against each other.
echo Pairings e.g. 1-3 2-4 (like a Swiss round), Enter = round robin.
echo The report opens in your browser afterwards.
echo.
goto run_turnier

:run_turnier
%PY% mtg_sim.py --turnier %LANGARG% %*
goto ende

:ende
if errorlevel 1 (
  echo.
  if "%LANGARG%"=="--lang en" (
    echo The program ended with an error. See the message above.
  ) else (
    echo Das Programm wurde mit einem Fehler beendet. Meldung siehe oben.
  )
  echo.
  pause
)
