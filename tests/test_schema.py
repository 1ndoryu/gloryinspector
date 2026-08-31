from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from inspector.core.schema import (
    SchemaValidationError,
    load_json,
    load_schema,
    validate,
    validate_schema_document,
)


ROOT = Path(__file__).resolve().parents[1]


class SchemaVocabularyTests(unittest.TestCase):
    def assertInvalid(self, value, schema):
        with self.assertRaises(SchemaValidationError):
            validate(value, schema)

    def test_type_required_properties_and_additional_properties(self):
        schema = {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}, "additionalProperties": False}
        validate({"name": "ok"}, schema)
        self.assertInvalid({}, schema)
        self.assertInvalid({"name": "ok", "extra": 1}, schema)
        self.assertInvalid({"name": 1}, schema)

    def test_items_and_enum(self):
        schema = {"type": "array", "items": {"enum": ["a", "b"]}}
        validate(["a", "b"], schema)
        self.assertInvalid(["c"], schema)

    def test_const_and_one_of(self):
        schema = {"oneOf": [{"const": "request"}, {"const": "response"}]}
        validate("request", schema)
        self.assertInvalid("event", schema)

    def test_string_bounds_and_pattern(self):
        schema = {"type": "string", "minLength": 2, "maxLength": 4, "pattern": "^[a-z]+$"}
        validate("ab", schema)
        self.assertInvalid("a", schema)
        self.assertInvalid("abcde", schema)
        self.assertInvalid("AB", schema)

    def test_numeric_bounds_and_boolean_is_not_integer(self):
        schema = {"type": "integer", "minimum": 1, "maximum": 3}
        validate(2, schema)
        self.assertInvalid(0, schema)
        self.assertInvalid(4, schema)
        self.assertInvalid(True, schema)

    def test_unknown_keyword_is_rejected(self):
        with self.assertRaises(SchemaValidationError):
            validate_schema_document({"schema": "inspector.schema/v1", "description": "not supported"})

    def test_pattern_input_is_bounded(self):
        schema = {"type": "string", "pattern": "x"}
        self.assertInvalid("x" * (64 * 1024 + 1), schema)


class NormativeSchemaTests(unittest.TestCase):
    def test_all_f0_fixtures(self):
        for schema_name, fixture_names in {
            "record-v1.json": ("valid-request.json", "valid-response.json", "valid-event.json"),
            "profile-v1.json": ("valid-profile.json",),
            "result-v1.json": ("valid-result.json",),
        }.items():
            schema = load_schema(ROOT / "schemas" / schema_name)
            for fixture_name in fixture_names:
                with self.subTest(schema=schema_name, fixture=fixture_name):
                    validate(load_json(ROOT / "fixtures" / fixture_name), schema)

    def test_invalid_record_is_rejected(self):
        schema = load_schema(ROOT / "schemas" / "record-v1.json")
        with self.assertRaises(SchemaValidationError):
            validate(load_json(ROOT / "fixtures" / "invalid-record.json"), schema)

    def test_schema_files_are_json(self):
        for path in (ROOT / "schemas").glob("*.json"):
            with self.subTest(path=path.name):
                validate_schema_document(json.loads(path.read_text(encoding="utf-8")))

    def test_schema_loader_reports_missing_file(self):
        with self.assertRaises(SchemaValidationError):
            load_schema(ROOT / "schemas" / "missing.json")


if __name__ == "__main__":
    unittest.main()
