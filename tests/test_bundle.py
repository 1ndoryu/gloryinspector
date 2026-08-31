from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from inspector.bundle import scan_bundle


ROOT = Path(__file__).resolve().parents[1]


class BundleTests(unittest.TestCase):
    def test_extracts_reproducible_candidates_without_execution(self):
        content = b'const x = "https://example.invalid/v1"; const tool = {"name":"weather"};'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bundle.js"
            path.write_bytes(content)
            first = scan_bundle(path, ROOT / "packs" / "bundle.json")
            second = scan_bundle(path, ROOT / "packs" / "bundle.json")
            self.assertEqual(first, second)
            self.assertFalse(first["executed"])
            self.assertTrue(any(item["rule"] == "url" for item in first["candidates"]))
            self.assertTrue(all(item["confirmed"] is False for item in first["candidates"]))

    def test_eight_mib_is_allowed_and_over_limit_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bundle.js"
            path.write_bytes(b"x" * (8 * 1024 * 1024))
            report = scan_bundle(path, ROOT / "packs" / "bundle.json")
            self.assertEqual(report["size_bytes"], 8 * 1024 * 1024)
            path.write_bytes(b"x" * (8 * 1024 * 1024 + 1))
            with self.assertRaises(ValueError):
                scan_bundle(path, ROOT / "packs" / "bundle.json")


if __name__ == "__main__":
    unittest.main()
