"""Import only explicit local evidence into the canonical record format."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core.records import RecordError, SessionWriter, body_descriptor
from ..core.redaction import redact_value


def _body(value: Any, artifacts: Path) -> tuple[dict[str, Any], str, str, tuple[str, ...]]:
    cleaned = redact_value(value, session_id="import-session")
    if cleaned.status in {"blocked", "unknown"}:
        raise RecordError(cleaned.reason or "body redaction blocked")
    descriptor, digest = body_descriptor(cleaned.value, artifacts)
    return descriptor, digest, cleaned.status, cleaned.rules


def _redact_mapping(value: dict[str, Any], session_id: str) -> tuple[dict[str, Any], str, tuple[str, ...]]:
    cleaned = redact_value(value, session_id=session_id)
    if cleaned.status in {"blocked", "unknown"} or not isinstance(cleaned.value, dict):
        raise RecordError(cleaned.reason or "mapping redaction blocked")
    return cleaned.value, cleaned.status, cleaned.rules


def har_to_records(document: dict[str, Any], *, session_id: str, artifacts: Path) -> list[dict[str, Any]]:
    entries = document.get("log", {}).get("entries", [])
    if not isinstance(entries, list):
        raise RecordError("HAR entries must be a list")
    records: list[dict[str, Any]] = []
    sequence = 1
    for index, entry in enumerate(entries):
        request = entry.get("request", {})
        response = entry.get("response", {})
        request_body = request.get("postData", {}).get("text") if isinstance(request.get("postData"), dict) else None
        if request_body:
            try:
                request_body = json.loads(request_body)
            except json.JSONDecodeError:
                pass
        request_descriptor, request_hash, request_status, request_rules = _body(request_body, artifacts) if request_body is not None else ({"mode": "absent", "reason": "not-captured"}, "", "clean", ())
        request_headers, headers_status, headers_rules = _redact_mapping({str(item.get("name")): str(item.get("value", "")) for item in request.get("headers", [])}, session_id)
        request_query, query_status, query_rules = _redact_mapping({str(item.get("name")): str(item.get("value", "")) for item in request.get("queryString", [])}, session_id)
        correlation = f"import-{index:04d}"
        records.append({
            "schema": "inspector.record/v1", "record_id": f"import-request-{index:04d}", "session_id": session_id, "correlation_id": correlation,
            "sequence": sequence, "ts": entry.get("startedDateTime", "unknown"), "kind": "request", "direction": "outbound",
            "url": request.get("url", "https://example.invalid/unknown"), "method": request.get("method", "GET"),
            "headers": request_headers, "query": request_query,
            "body": request_descriptor, **({"body_sha256": request_hash} if request_hash else {}),
            "meta": {"capture_adapter": "import", "redaction": {"status": "changed" if "changed" in {request_status, headers_status, query_status} else "clean", "rules": sorted(set(request_rules) | set(headers_rules) | set(query_rules))}},
        })
        sequence += 1
        response_body = response.get("content", {}).get("text") if isinstance(response.get("content"), dict) else None
        if response_body:
            try:
                response_body = json.loads(response_body)
            except json.JSONDecodeError:
                pass
        response_descriptor, response_hash, response_status, response_rules = _body(response_body, artifacts) if response_body is not None else ({"mode": "absent", "reason": "not-captured"}, "", "clean", ())
        response_headers, response_headers_status, response_headers_rules = _redact_mapping({str(item.get("name")): str(item.get("value", "")) for item in response.get("headers", [])}, session_id)
        records.append({
            "schema": "inspector.record/v1", "record_id": f"import-response-{index:04d}", "session_id": session_id, "correlation_id": correlation,
            "sequence": sequence, "ts": entry.get("startedDateTime", "unknown"), "kind": "response", "direction": "inbound",
            "url": request.get("url", "https://example.invalid/unknown"), "status": int(response.get("status", 599)),
            "headers": response_headers,
            "body": response_descriptor, **({"body_sha256": response_hash} if response_hash else {}),
            "meta": {"capture_adapter": "import", "redaction": {"status": "changed" if "changed" in {response_status, response_headers_status} else "clean", "rules": sorted(set(response_rules) | set(response_headers_rules))}},
        })
        sequence += 1
    return records


def import_file(input_path: Path, output_dir: Path, *, session_id: str = "import-session") -> dict[str, Any]:
    try:
        document = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RecordError(f"cannot load import input: {exc}") from exc
    artifacts = output_dir.resolve()
    if isinstance(document, dict) and "log" in document:
        records = har_to_records(document, session_id=session_id, artifacts=artifacts)
    elif isinstance(document, list):
        records = []
        for record in document:
            if not isinstance(record, dict):
                raise RecordError("record list contains a non-object")
            cleaned = redact_value(record, session_id=session_id)
            if cleaned.status in {"blocked", "unknown"} or not isinstance(cleaned.value, dict):
                raise RecordError(cleaned.reason or "record redaction blocked")
            record = cleaned.value
            body = record.get("body")
            if isinstance(body, dict) and body.get("mode") == "inline":
                descriptor, digest = body_descriptor(body.get("value"), artifacts)
                record["body"] = descriptor
                record["body_sha256"] = digest
            elif isinstance(body, dict) and body.get("mode") == "blob":
                raise RecordError("raw blob imports are blocked until their source is redacted")
            record.setdefault("meta", {})["redaction"] = {"status": cleaned.status, "rules": list(cleaned.rules)}
            records.append(record)
    else:
        raise RecordError("import input must be a HAR document or record list")
    writer = SessionWriter(artifacts, session_id)
    for record in records:
        writer.append(record)
    return writer.close(source="import")
