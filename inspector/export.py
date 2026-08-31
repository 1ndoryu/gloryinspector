"""Export only bounded, sanitized result facts across the repository boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .core.schema import SchemaValidationError, load_schema, validate

EXPORT_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "export-v1.json"


class ExportError(ValueError):
    """Raised when an export cannot be proven safe or schema-compatible."""


def _hash_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def build_export(result: dict[str, Any], *, fixture_id: str, profile_id: str, source: str = "mock", input_value: Any | None = None) -> dict[str, Any]:
    if source not in {"mock", "import", "loopback", "authorized"}:
        raise ExportError("unsupported export source")
    envelope = {
        "schema": "inspector.export/v1", "export_version": 1,
        "provenance": {"fixture_id": fixture_id, "profile_id": profile_id, "source": source, "tool_version": "0.1.0"},
        "status": result.get("status", "TOOL_ERROR"), "classification": result.get("classification"),
        "findings": result.get("findings", []), "assertions": result.get("assertions", []), "trace_id": result.get("trace_id"),
        "input_sha256": _hash_json(input_value) if input_value is not None else None,
        "trace_sha256": _hash_json({"status": result.get("status"), "classification": result.get("classification"), "findings": result.get("findings", [])}),
        "compatibility": {"contract": "gloryapi-compatibility-adapter", "supported_versions": [1]},
    }
    try:
        validate(envelope, load_schema(EXPORT_SCHEMA_PATH))
    except SchemaValidationError as exc:
        raise ExportError(str(exc)) from exc
    return envelope


def write_export(result: dict[str, Any], output_path: Path, *, fixture_id: str, profile_id: str, source: str = "mock", input_value: Any | None = None, force: bool = False) -> dict[str, Any]:
    if output_path.exists() and not force:
        raise ExportError("output exists; use --force")
    envelope = build_export(result, fixture_id=fixture_id, profile_id=profile_id, source=source, input_value=input_value)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return envelope


def validate_export(value: dict[str, Any]) -> None:
    try:
        validate(value, load_schema(EXPORT_SCHEMA_PATH))
    except SchemaValidationError as exc:
        raise ExportError(str(exc)) from exc
