"""Single-variable differential runner over the deterministic mock."""

from __future__ import annotations

import hashlib
from typing import Any

from .adapters.mock import MockTarget
from .core.mutations import MutationSpec, apply_mutation
from .core.records import canonical_json_bytes
from .replay import replay_request


def latency_bucket(value: Any) -> str:
    try:
        milliseconds = int(value)
    except (TypeError, ValueError):
        return "unknown"
    if milliseconds < 100:
        return "lt_100ms"
    if milliseconds < 500:
        return "100_500ms"
    return "gte_500ms"


def run_diff(base_body: dict[str, Any], spec: MutationSpec, *, target: MockTarget | None = None, budget: int = 32) -> list[dict[str, Any]]:
    if len(spec.variants) > budget:
        raise ValueError("mutation budget exceeded")
    matrix: list[dict[str, Any]] = []
    for index, variant in enumerate(spec.variants):
        mutated_body = apply_mutation(base_body, spec, variant)
        request = {
            "schema": "inspector.record/v1", "record_id": f"diff-{index:04d}", "session_id": "diff-session", "correlation_id": f"diff-{index:04d}",
            "sequence": 1, "ts": "2026-08-10T00:00:00Z", "kind": "request", "direction": "outbound",
            "url": "https://example.invalid/v1/chat/completions", "method": "POST", "headers": {}, "query": {},
            "body": {"mode": "inline", "encoding": "json", "value": mutated_body}, "meta": {"model_requested": mutated_body.get("model", "unknown-model")},
        }
        result = replay_request(request, target=target or MockTarget(), expectations={"downgrade_is_failure": True})
        response = result.get("response", {})
        meta = response.get("meta", {}) if isinstance(response.get("meta"), dict) else {}
        matrix.append({
            "input_hash": hashlib.sha256(canonical_json_bytes(mutated_body)).hexdigest(),
            "variable": spec.variable,
            "variant_index": index,
            "result": result["status"],
            "classification": result.get("classification"),
            "model_effective": meta.get("model_effective"),
            "latency_bucket": latency_bucket(meta.get("latency_ms")),
            "trace_id": result.get("trace_id"),
        })
    return matrix
