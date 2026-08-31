"""Small fail-closed validator for the project's deliberately bounded schema vocabulary."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

VOCABULARY = "inspector.schema/v1"
SUPPORTED_KEYWORDS = frozenset(
    {
        "type",
        "required",
        "properties",
        "additionalProperties",
        "items",
        "enum",
        "const",
        "oneOf",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "pattern",
    }
)
MAX_PATTERN_LENGTH = 256
MAX_PATTERN_INPUT = 64 * 1024
MAX_SCHEMA_DEPTH = 32


class SchemaValidationError(ValueError):
    """Raised when a value or schema document violates the F0 contract."""


def _path(path: str, key: str) -> str:
    if key.isidentifier():
        return f"{path}.{key}"
    return f"{path}[{key!r}]"


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    raise SchemaValidationError(f"unsupported type {expected!r}")


def _compile_bounded_pattern(pattern: str) -> re.Pattern[str]:
    if len(pattern) > MAX_PATTERN_LENGTH:
        raise SchemaValidationError("pattern must be a bounded string")
    # The bounded vocabulary intentionally rejects the common nested-quantifier
    # shape that can make backtracking regex engines consume unbounded CPU.
    if re.search(r"\([^)]*[+*][^)]*\)[+*?]", pattern) or re.search(r"\([^)]*\{[^}]+\}[^)]*\)[+*?]", pattern):
        raise SchemaValidationError("pattern contains an unbounded nested quantifier")
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise SchemaValidationError(f"invalid pattern: {exc}") from exc


def _check_schema_keywords(schema: Any, *, root: bool = False, depth: int = 0) -> None:
    if depth > MAX_SCHEMA_DEPTH:
        raise SchemaValidationError("schema exceeds the maximum nesting depth")
    if not isinstance(schema, dict):
        raise SchemaValidationError("schema nodes must be objects")

    allowed = SUPPORTED_KEYWORDS | ({"schema"} if root else set())
    unknown = set(schema) - allowed
    if unknown:
        names = ", ".join(sorted(map(str, unknown)))
        raise SchemaValidationError(f"unsupported schema keyword(s): {names}")
    if root and schema.get("schema") != VOCABULARY:
        raise SchemaValidationError(f"schema must declare {VOCABULARY!r}")

    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not types or any(not isinstance(item, str) for item in types):
            raise SchemaValidationError("type must be a string or a non-empty list of strings")
        for item in types:
            if item not in {"object", "array", "string", "integer", "number", "boolean", "null"}:
                raise SchemaValidationError(f"unsupported type {item!r}")
    if "required" in schema:
        required = schema["required"]
        if not isinstance(required, list) or any(not isinstance(item, str) for item in required):
            raise SchemaValidationError("required must be a list of strings")
    if "properties" in schema:
        if not isinstance(schema["properties"], dict):
            raise SchemaValidationError("properties must be an object")
        for child in schema["properties"].values():
            _check_schema_keywords(child, depth=depth + 1)
    if "additionalProperties" in schema:
        additional = schema["additionalProperties"]
        if not isinstance(additional, bool):
            _check_schema_keywords(additional, depth=depth + 1)
    if "items" in schema:
        _check_schema_keywords(schema["items"], depth=depth + 1)
    if "oneOf" in schema:
        branches = schema["oneOf"]
        if not isinstance(branches, list) or not branches:
            raise SchemaValidationError("oneOf must be a non-empty list")
        for branch in branches:
            _check_schema_keywords(branch, depth=depth + 1)
    if "enum" in schema and not isinstance(schema["enum"], list):
        raise SchemaValidationError("enum must be a list")
    if "const" in schema and isinstance(schema["const"], (dict, list)):
        raise SchemaValidationError("const must be a scalar in the bounded vocabulary")
    for keyword in ("minLength", "maxLength"):
        if keyword in schema and (not isinstance(schema[keyword], int) or isinstance(schema[keyword], bool) or schema[keyword] < 0):
            raise SchemaValidationError(f"{keyword} must be a non-negative integer")
    for keyword in ("minimum", "maximum"):
        if keyword in schema and (
            not isinstance(schema[keyword], (int, float)) or isinstance(schema[keyword], bool)
        ):
            raise SchemaValidationError(f"{keyword} must be numeric")
    if "pattern" in schema:
        pattern = schema["pattern"]
        if not isinstance(pattern, str):
            raise SchemaValidationError("pattern must be a bounded string")
        _compile_bounded_pattern(pattern)


def validate_schema_document(schema: Any) -> None:
    """Validate the schema document itself before it is used."""

    _check_schema_keywords(schema, root=True)


def _validate(value: Any, schema: dict[str, Any], path: str) -> None:
    if "oneOf" in schema:
        successes = 0
        errors: list[str] = []
        for branch in schema["oneOf"]:
            try:
                _validate(value, branch, path)
            except SchemaValidationError as exc:
                errors.append(str(exc))
            else:
                successes += 1
        if successes != 1:
            detail = "; ".join(errors[:3])
            raise SchemaValidationError(f"{path}: oneOf matched {successes} branches ({detail})")

    if "const" in schema and value != schema["const"]:
        raise SchemaValidationError(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise SchemaValidationError(f"{path}: expected one of {schema['enum']!r}")

    if "type" in schema:
        expected = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_matches(value, item) for item in expected):
            raise SchemaValidationError(f"{path}: expected type {expected!r}")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise SchemaValidationError(f"{path}: shorter than minLength")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise SchemaValidationError(f"{path}: longer than maxLength")
        if "pattern" in schema:
            if len(value) > MAX_PATTERN_INPUT:
                raise SchemaValidationError(f"{path}: pattern input exceeds bounded size")
            if _compile_bounded_pattern(schema["pattern"]).search(value) is None:
                raise SchemaValidationError(f"{path}: pattern did not match")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise SchemaValidationError(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise SchemaValidationError(f"{path}: above maximum")

    if isinstance(value, dict):
        required = schema.get("required", [])
        missing = [key for key in required if key not in value]
        if missing:
            raise SchemaValidationError(f"{path}: missing required field(s) {missing!r}")
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, child in value.items():
            if key in properties:
                _validate(child, properties[key], _path(path, key))
            elif additional is False:
                raise SchemaValidationError(f"{_path(path, key)}: additional property is not allowed")
            elif isinstance(additional, dict):
                _validate(child, additional, _path(path, key))

    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            _validate(item, schema["items"], f"{path}[{index}]")


def validate(value: Any, schema: dict[str, Any]) -> None:
    """Raise ``SchemaValidationError`` unless value matches schema exactly."""

    validate_schema_document(schema) if "schema" in schema else _check_schema_keywords(schema)
    effective = {key: child for key, child in schema.items() if key != "schema"}
    _validate(value, effective, "$")


def load_schema(path: str | Path) -> dict[str, Any]:
    """Load and validate a JSON schema document from an explicit path."""

    schema_path = Path(path)
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SchemaValidationError(f"cannot load schema {schema_path}: {exc}") from exc
    validate_schema_document(schema)
    return schema


def load_json(path: str | Path) -> Any:
    """Load JSON input with a user-facing validation error."""

    input_path = Path(path)
    try:
        return json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SchemaValidationError(f"cannot load JSON {input_path}: {exc}") from exc
