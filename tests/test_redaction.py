from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from inspector.core.redaction import redact_value
from inspector.redact import redact_file


class RedactionTests(unittest.TestCase):
    def test_contexts_and_stable_session_placeholder(self):
        value = {"Authorization": "Bearer abcdefghijklmnop", "contact": "person@example.invalid", "id": "123e4567-e89b-12d3-a456-426614174000"}
        first = redact_value(value, session_id="s-1")
        second = redact_value(value, session_id="s-1")
        other = redact_value(value, session_id="s-2")
        self.assertEqual(first.status, "changed")
        self.assertEqual(first.value, second.value)
        self.assertNotEqual(first.value, other.value)
        self.assertNotIn("Bearer abcdefghijklmnop", json.dumps(first.value))
        self.assertIn("sensitive_field", first.rules)
        self.assertIn("email", first.rules)

    def test_unknown_and_limits_block(self):
        self.assertEqual(redact_value(object(), session_id="s").status, "unknown")
        self.assertEqual(redact_value("x" * (64 * 1024 + 1), session_id="s").status, "blocked")
        self.assertEqual(redact_value({"nested": {"x": 1}}, session_id="s", max_matches=0).status, "clean")

    def test_scanner_style_secret_is_removed(self):
        result = redact_value({"token": "ghp_123456789012345678901234"}, session_id="s")
        self.assertEqual(result.status, "changed")
        self.assertNotIn("ghp_", result.value["token"])

    def test_file_never_overwrites_without_force(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            output = root / "output.json"
            source.write_text('{"email": "person@example.invalid"}\n', encoding="utf-8")
            output.write_text("existing\n", encoding="utf-8")
            blocked = redact_file(source, output, session_id="s")
            self.assertEqual(blocked.status, "blocked")
            self.assertEqual(output.read_text(encoding="utf-8"), "existing\n")
            written = redact_file(source, output, session_id="s", force=True)
            self.assertEqual(written.status, "changed")
            self.assertNotIn("person@example.invalid", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
