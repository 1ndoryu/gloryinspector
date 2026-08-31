from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.check_no_secrets import scan


class ScannerTests(unittest.TestCase):
    def test_synthetic_secret_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixtures = root / "fixtures"
            fixtures.mkdir()
            (fixtures / "bad.json").write_text('{"key":"ghp_123456789012345678901234"}', encoding="utf-8")
            self.assertEqual(scan(root), ["fixtures/bad.json"])


if __name__ == "__main__":
    unittest.main()
