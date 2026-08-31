from __future__ import annotations

import unittest
from pathlib import Path

from inspector.core.schema import load_json, load_schema, validate
from inspector.export import ExportError, build_export, validate_export

ROOT = Path(__file__).resolve().parents[1]


class ExportTests(unittest.TestCase):
    def test_static_export_fixture_is_schema_valid(self):
        validate(load_json(ROOT / "fixtures" / "export" / "foreign-toolset-v1.json"), load_schema(ROOT / "schemas" / "export-v1.json"))

    def test_export_is_contract_valid_and_bounded(self):
        result = {"status": "FAIL", "classification": "foreign_toolset", "findings": [{"code": "foreign_toolset"}], "assertions": [], "trace_id": "trace-1"}
        envelope = build_export(result, fixture_id="fixture-1", profile_id="profile-1", input_value={"model": "synthetic"})
        validate_export(envelope)
        self.assertNotIn("response", envelope)
        self.assertNotIn("credential_ref", json_text(envelope))

    def test_unsupported_version_or_source_is_rejected(self):
        with self.assertRaises(ExportError):
            build_export({"status": "PASS"}, fixture_id="fixture", profile_id="profile", source="upstream")
        with self.assertRaises(ExportError):
            validate_export({"schema": "inspector.export/v1", "export_version": 99})


def json_text(value):
    import json
    return json.dumps(value)


if __name__ == "__main__":
    unittest.main()
