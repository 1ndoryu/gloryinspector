"""Deterministic mock transport used by replay, diff, probe and track."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MockScenario:
    """A bounded response scenario; no scenario opens network access."""

    name: str = "historical-auto"
    status: int | None = None
    model_effective: str | None = None
    stream_truncated: bool = False
    schema_invalid: bool = False
    latency_ms: int = 10
    version: str = "mock-v1"
    forced_classification: str | None = None
    state: str = "ok"


@dataclass
class MockTarget:
    scenario: MockScenario = field(default_factory=MockScenario)
    calls: int = 0

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        body = request.get("body", {}).get("value", {}) if isinstance(request.get("body"), dict) else {}
        if not isinstance(body, dict):
            body = {}
        requested = request.get("meta", {}).get("model_requested") or body.get("model") or "unknown-model"
        status = self.scenario.status
        classification = self.scenario.forced_classification
        error: dict[str, Any] | None = None
        effective = self.scenario.model_effective or requested

        if status is None:
            tools = body.get("tools", [])
            malformed_tool = bool(tools) and any(isinstance(tool, dict) and tool.get("signature") != "expected-v1" for tool in tools)
            if malformed_tool:
                status = 429
                classification = "foreign_toolset"
                effective = "fallback-model"
                error = {"code": "foreign_toolset", "message": "tool contract rejected by mock"}
            else:
                status = {"ok": 200, "banned": 403, "rate_limited": 429, "token_invalid": 401, "country_blocked": 451, "model_locked": 409, "ip_capped": 429, "timeout": 599, "unknown": 520}.get(self.scenario.state, 520)
        if status == 401 and classification is None:
            classification = "auth"
        if status == 429 and classification is None:
            classification = "rate_limit"
        if status == 599:
            classification = classification or "timeout"
        if self.scenario.stream_truncated:
            classification = classification or "stream_truncated"
        if self.scenario.schema_invalid:
            classification = classification or "schema"
        response = {
            "status": status,
            "headers": {"content-type": "application/json"},
            "body": {"model": effective, "choices": [{"message": {"content": "synthetic"}}]},
            "meta": {
                "model_requested": requested,
                "model_effective": effective,
                "classification_hint": classification,
                "stream_complete": not self.scenario.stream_truncated,
                "schema_valid": not self.scenario.schema_invalid,
                "latency_ms": self.scenario.latency_ms,
                "mock_version": self.scenario.version,
            },
        }
        if error:
            response["body"]["error"] = error
        if self.scenario.stream_truncated:
            response["body"]["stream"] = "truncated"
        return response
