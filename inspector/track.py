"""Single-run drift tracker with actionable field-level findings."""

from __future__ import annotations

from typing import Any

from .replay import replay_request


def _observed(result: dict[str, Any]) -> dict[str, Any]:
    response = result.get("response", {}) if isinstance(result.get("response"), dict) else {}
    meta = response.get("meta", {}) if isinstance(response.get("meta"), dict) else {}
    return {
        "schema": result.get("schema"),
        "status": result.get("status"),
        "classification": result.get("classification"),
        "model_effective": meta.get("model_effective"),
        "stream_complete": meta.get("stream_complete"),
        "latency_bucket": "unknown" if meta.get("latency_ms") is None else ("lt_100ms" if meta.get("latency_ms", 0) < 100 else "100_500ms" if meta.get("latency_ms", 0) < 500 else "gte_500ms"),
    }


def compare_golden(golden: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    if current.get("status") == "TOOL_ERROR":
        return {"schema": "inspector.track/v1", "status": "TOOL_ERROR", "findings": [{"field": "transport", "severity": "error", "message": "target could not be executed"}], "next_action": "inspect transport error", "baseline_trace": golden.get("trace_id"), "current_trace": current.get("trace_id")}
    if current.get("status") == "NOT_RUN":
        return {"schema": "inspector.track/v1", "status": "NOT_RUN", "findings": [{"field": "coverage", "severity": "info", "message": "target was not executed"}], "next_action": "run the declared target", "baseline_trace": golden.get("trace_id"), "current_trace": current.get("trace_id")}
    expected = golden.get("observed", _observed(golden))
    observed = _observed(current)
    findings: list[dict[str, Any]] = []
    for field in ("schema", "status", "classification", "model_effective", "stream_complete"):
        if expected.get(field) != observed.get(field):
            findings.append({"field": field, "severity": "error", "expected": expected.get(field), "observed": observed.get(field)})
    if expected.get("latency_bucket") != observed.get("latency_bucket"):
        findings.append({"field": "latency_bucket", "severity": "warning", "expected": expected.get("latency_bucket"), "observed": observed.get("latency_bucket")})
    status = "FAIL" if any(item["severity"] == "error" for item in findings) else "WARN" if findings else "PASS"
    return {"schema": "inspector.track/v1", "status": status, "findings": findings, "next_action": "review changed contract fields" if findings else "none", "baseline_trace": golden.get("trace_id"), "current_trace": current.get("trace_id"), "observed": observed}


def track_request(request: dict[str, Any], golden: dict[str, Any], *, target: Any | None = None) -> dict[str, Any]:
    current = replay_request(request, target=target, expectations={"downgrade_is_failure": False})
    return compare_golden(golden, current)
