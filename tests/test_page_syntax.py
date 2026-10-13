import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

from components import drafthelper as dh


@unittest.skipUnless(shutil.which("node"), "Node.js nicht installiert")
class PageScriptTests(unittest.TestCase):
    def test_page_script_is_valid_javascript(self):
        """Faengt Syntaxfehler im eingebetteten JavaScript ab (die Seite waere sonst leer)."""
        scripts = re.findall(r"<script>(.*?)</script>", dh.PAGE, re.S)
        self.assertTrue(scripts)
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "page.js"
            path.write_text("\n".join(scripts), encoding="utf-8")
            out = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_page_has_the_elements_the_script_looks_up(self):
        script = "\n".join(re.findall(r"<script>(.*?)</script>", dh.PAGE, re.S))
        wanted = set(re.findall(r'\$\("([A-Za-z0-9_]+)"\)', script))
        present = set(re.findall(r'id="([A-Za-z0-9_]+)"', dh.PAGE))
        # Elemente, die erst zur Laufzeit entstehen, stehen nicht im HTML
        missing = wanted - present
        self.assertEqual(missing, set(), f"IDs im Skript ohne Element im HTML: {sorted(missing)}")


if __name__ == "__main__":
    unittest.main()
