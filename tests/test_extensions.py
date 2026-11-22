"""The Custom Extensions' own tests (`extensions/*/test/*.test.mjs`), run with Node's test runner. Needs Node 24
(`nvm use`); no tenant."""
import shutil
import subprocess
import unittest
from pathlib import Path

EXT_DIR = Path(__file__).resolve().parent.parent / "extensions"


@unittest.skipIf(shutil.which("node") is None, "Node is not installed (nvm use)")
class ExtensionTests(unittest.TestCase):
    def test_node_tests_pass(self):
        files = sorted(str(p) for p in EXT_DIR.glob("*/test/*.test.mjs"))
        self.assertTrue(files)
        r = subprocess.run(["node", "--test", *files], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
