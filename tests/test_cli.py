from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from inspector.cli import main


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_help_is_offline_and_successful(self):
        output = io.StringIO()
        with self.assertRaises(SystemExit) as raised:
            with redirect_stdout(output):
                main(["--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("Validate and reproduce sanitized", output.getvalue())

    def test_validate_fixture(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main([
                "validate",
                "--schema",
                str(ROOT / "schemas" / "record-v1.json"),
                "--input",
                str(ROOT / "fixtures" / "valid-request.json"),
            ])
        self.assertEqual(code, 0)
        self.assertIn("VALID", output.getvalue())

    def test_invalid_fixture_uses_input_exit_code(self):
        with redirect_stdout(io.StringIO()):
            code = main([
                "validate",
                "--schema",
                str(ROOT / "schemas" / "record-v1.json"),
                "--input",
                str(ROOT / "fixtures" / "invalid-record.json"),
            ])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
