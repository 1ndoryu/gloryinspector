"""Classification is descriptive only; it never decides retry or fallback policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

TAXONOMY = "inspector.error/v1"
CODES = frozenset({"auth", "rate_limit", "foreign_toolset", "model_downgrade", "schema", "timeout", "stream_truncated", "model_not_found", "provider_error", "unknown"})


@dataclass(frozen=True)
class Classification:
    code: str
    taxonomy: str = TAXONOMY
    evidence: tuple[str, ...] = ()


def _body_error(response: dict[str, Any]) -> str | None:
    body = response.get("body")
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        code = body["error"].get("code")
        if isinstance(code, str):
            return code
    return None


def classify_response(response: dict[str, Any]) -> Classification:
    meta = response.get("meta", {}) if isinstance(response.get("meta"), dict) else {}
    body_error = _body_error(response)
    hint = meta.get("classification_hint")
    status = response.get("status")
    requested = meta.get("model_requested")
    effective = meta.get("model_effective")
    if body_error == "foreign_toolset" or hint == "foreign_toolset":
        return Classification("foreign_toolset", evidence=("structured_error",))
    if response.get("transport_error") == "timeout" or hint == "timeout" or status == 599:
        return Classification("timeout", evidence=("transport",))
    if meta.get("stream_complete") is False or hint == "stream_truncated":
        return Classification("stream_truncated", evidence=("stream_complete=false",))
    if meta.get("schema_valid") is False or hint == "schema":
        return Classification("schema", evidence=("schema_valid=false",))
    if isinstance(requested, str) and isinstance(effective, str) and requested != effective:
        return Classification("model_downgrade", evidence=("model_requested!=model_effective",))
    if status in (401, 403):
        return Classification("auth", evidence=(f"status={status}",))
    if status == 404 or hint == "model_not_found":
        return Classification("model_not_found", evidence=(f"status={status}",))
    if status == 429:
        return Classification("rate_limit", evidence=("status=429",))
    if isinstance(status, int) and status >= 500:
        return Classification("provider_error", evidence=(f"status={status}",))
    if isinstance(hint, str) and hint in CODES:
        return Classification(hint, evidence=("scenario_hint",))
    return Classification("unknown", evidence=("no_matching_rule",))
