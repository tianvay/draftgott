#!/usr/bin/env python3
"""draftgott starten: Windows per Doppelklick (ohne Konsole), Ubuntu mit "python3 draftgott.pyw" oder ueber den
Eintrag im Startmenue (im Launcher Knopf "Ins Startmenue", oder "python3 draftgott.pyw --desktop").
Der Launcher selbst steht in components/launcher.py."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from components.launcher import main  # noqa: E402

if __name__ == "__main__":
    main()
