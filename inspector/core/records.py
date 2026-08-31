"""Versioned record and session primitives for sanitized local evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .schema import SchemaValidationError, load_schema, validate

INLINE_BODY_LIMIT = 1024 * 1024
MAX_BODY_BYTES = 8 * 1024 * 1024
RECORD_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "record-v1.json"


class RecordError(ValueError):
    """Raised when a record or artifact violates storage invariants."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_digest(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def body_descriptor(value: Any, artifacts_dir: Path, *, inline_limit: int = INLINE_BODY_LIMIT, max_bytes: int = MAX_BODY_BYTES) -> tuple[dict[str, Any], str]:
    """Return a deterministic inline/blob descriptor and its sanitized-body hash."""

    payload = canonical_json_bytes(value)
    if len(payload) > max_bytes:
        raise RecordError(f"body exceeds maximum size of {max_bytes} bytes")
    digest = sha256_digest(payload)
    if len(payload) <= inline_limit:
        return {"mode": "inline", "encoding": "json", "value": value}, digest
    blob_dir = (artifacts_dir / "blobs").resolve()
    blob_dir.mkdir(parents=True, exist_ok=True)
    blob_path = (blob_dir / f"{digest.removeprefix('sha256:')}.blob").resolve()
    if blob_dir not in blob_path.parents:
        raise RecordError("blob path escapes artifact directory")
    if blob_path.exists():
        if blob_path.read_bytes() != payload:
            raise RecordError("existing blob hash does not match sanitized body")
    else:
        blob_path.write_bytes(payload)
    return {"mode": "blob", "path": f"blobs/{blob_path.name}", "sha256": digest}, digest


def validate_record(record: dict[str, Any]) -> None:
    try:
        validate(record, load_schema(RECORD_SCHEMA_PATH))
    except SchemaValidationError as exc:
        raise RecordError(str(exc)) from exc


@dataclass
class SessionWriter:
    root: Path
    session_id: str
    profile_id: str = "local"
    tool_version: str = "0.1.0"
    _records: list[dict[str, Any]] = field(default_factory=list, init=False)
    _record_ids: set[str] = field(default_factory=set, init=False)
    _correlations: set[str] = field(default_factory=set, init=False)
    _last_sequence: int = field(default=0, init=False)
    _closed: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        self.root = self.root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.records_path = self.root / f"{self.session_id}.jsonl"
        self.manifest_path = self.root / f"{self.session_id}.manifest.json"
        if self.records_path.exists() or self.manifest_path.exists():
            raise RecordError(f"session output already exists: {self.session_id}")
        self.records_path.write_text("", encoding="utf-8")

    def append(self, record: dict[str, Any]) -> None:
        if self._closed:
            raise RecordError("session is already closed")
        validate_record(record)
        record_id = record["record_id"]
        if record_id in self._record_ids:
            raise RecordError(f"duplicate record_id: {record_id}")
        sequence = record["sequence"]
        if sequence <= self._last_sequence:
            raise RecordError("sequence must be strictly increasing")
        correlation = record["correlation_id"]
        if record["kind"] == "response" and correlation not in self._correlations and not record.get("orphaned", False):
            raise RecordError("response correlation_id was not observed in a request")
        if record["kind"] == "request":
            self._correlations.add(correlation)
        line = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self.records_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
        self._records.append(record)
        self._record_ids.add(record_id)
        self._last_sequence = sequence

    def close(self, *, complete: bool = True, source: str = "local") -> dict[str, Any]:
        if self._closed:
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        records_bytes = self.records_path.read_bytes()
        manifest = {
            "schema": "inspector.manifest/v1",
            "session_id": self.session_id,
            "profile_id": self.profile_id,
            "tool_version": self.tool_version,
            "record_schema": "inspector.record/v1",
            "record_count": len(self._records),
            "complete": complete,
            "source": source,
            "records_sha256": sha256_digest(records_bytes),
        }
        self.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        self._closed = True
        return manifest


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RecordError(f"invalid JSONL at line {line_number}: {exc}") from exc
        if not isinstance(value, dict):
            raise RecordError(f"record at line {line_number} is not an object")
        validate_record(value)
        records.append(value)
    return records
