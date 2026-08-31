"""Replay use case; only mock targets are enabled by default."""

from __future__ import annotations

import hashlib
from typing import Any

from .adapters.mock import MockScenario, MockTarget
from .core.assertions import assert_response
from .core.classification import classify_response
from .core.transport import BoundedTransport, LoopbackHttpTarget, TransportError, TransportLimits


def replay_request(request: dict[str, Any], *, target: MockTarget | None = None, expectations: dict[str, Any] | None = None, timeout_ms: int = 10_000) -> dict[str, Any]:
    trace_id = hashlib.sha256(repr(sorted(request.items())).encode("utf-8")).hexdigest()[:16]
    target = target or MockTarget()
    try:
        response = BoundedTransport(target, TransportLimits(timeout_ms=timeout_ms)).send(request)
    except TransportError as exc:
        response = {"status": None, "transport_error": "timeout" if "timeout" in str(exc) else "tool_error", "meta": {}}
        classification = classify_response(response)
        return {"schema": "inspector.result/v1", "status": "TOOL_ERROR", "findings": [{"code": classification.code, "message": str(exc)}], "classification": classification.code, "assertions": [], "trace_id": trace_id, "tool_version": "0.1.0"}
    classification = classify_response(response)
    assertions = assert_response(response, expectations)
    status = "FAIL" if any(not item.passed for item in assertions) else "PASS"
    findings = [] if status == "PASS" else [{"code": classification.code, "message": item.message} for item in assertions if not item.passed]
    return {"schema": "inspector.result/v1", "status": status, "findings": findings, "classification": classification.code, "assertions": [item.as_dict() for item in assertions], "trace_id": trace_id, "tool_version": "0.1.0", "response": response}


def target_from_uri(uri: str) -> MockTarget:
    if uri.startswith("http://127.0.0.1"):
        return LoopbackHttpTarget(uri)
    if not uri.startswith("mock://"):
        raise ValueError("targets must use mock:// or http://127.0.0.1")
    scenario_name = uri.removeprefix("mock://") or "historical-auto"
    if scenario_name == "downgrade":
        return MockTarget(MockScenario(model_effective="fallback-model"))
    if scenario_name in {"timeout", "rate_limited", "token_invalid", "banned", "country_blocked", "model_locked", "ip_capped", "unknown"}:
        return MockTarget(MockScenario(state=scenario_name))
    return MockTarget(MockScenario(name=scenario_name))
