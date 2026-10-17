@echo off
rem draftgott: Startmenue fuer den MTG-Simulator per Doppelklick.
rem   1 = Analyse    (Deckliste _normaldeck.txt simulieren, Bericht meinbericht.html; laeuft weiter fuer den
rem                   Kampf aus dem Bericht, bis "Beenden" geklickt wird)
rem   2 = Drafthelper (Kartenseite im Browser mit _draftedcardpool.txt)
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
  pause
  exit /b 1
)

echo.
echo  draftgott
echo  ---------
echo   1 = Analyse       (_normaldeck.txt simulieren, Bericht meinbericht.html, Kampf im Bericht)
echo   2 = Drafthelper   (Karten aus _draftedcardpool.txt auswaehlen und vergleichen)
echo.
choice /c 12 /n /m "Auswahl (1 oder 2): "
if errorlevel 2 goto drafthelper
if errorlevel 1 goto analyse
exit /b 1

:analyse
echo.
echo Analyse laeuft, der Bericht oeffnet sich danach im Browser ...
echo Dieses Fenster bitte offen lassen, solange du im Bericht "Kampf simulieren" nutzen willst.
echo Zum Beenden: Knopf "Beenden" im Bericht oder dieses Fenster schliessen.
%PY% mtg_sim.py _normaldeck.txt --sims 10000 --html meinbericht.html --bericht-server %*
goto ende

:drafthelper
echo.
echo Der Drafthelper wird gestartet, der Browser oeffnet sich gleich.
echo Dieses Fenster bitte offen lassen. Zum Beenden: Button "Beenden" auf der Seite
echo oder dieses Fenster schliessen.
echo.
%PY% mtg_sim.py --drafthelper _draftedcardpool.txt %*
goto ende

:ende
if errorlevel 1 (
  echo.
  echo Das Programm wurde mit einem Fehler beendet. Meldung siehe oben.
  echo.
  pause
)
