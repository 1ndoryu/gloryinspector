"""Mock-first health probe with bounded cache and explicit live safety gates."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from .adapters.mock import MockScenario, MockTarget
from .core.classification import classify_response
from .core.profiles import ProfileError, load_profile
from .core.transport import BoundedTransport, TransportLimits, TransportError

STATES = ("ok", "banned", "rate_limited", "token_invalid", "country_blocked", "model_locked", "ip_capped", "timeout", "unknown")


class ProbePolicyError(ValueError):
    """Raised when a probe would violate explicit live or target policy."""


@dataclass(frozen=True)
class ProbeResult:
    state: str
    status: str
    classification: str
    exit_code: int
    trace_id: str
    cache_ttl_ms: int
    account_alias: str

    def as_dict(self) -> dict[str, Any]:
        return {"schema": "inspector.result/v1", "status": self.status, "findings": [] if self.status == "PASS" else [{"code": self.classification}], "classification": self.classification, "assertions": [], "trace_id": self.trace_id, "tool_version": "0.1.0", "exit_code": self.exit_code, "probe_state": self.state, "cache_ttl_ms": self.cache_ttl_ms, "account_alias": self.account_alias}


class ProbeCache:
    def __init__(self, max_entries: int = 64):
        self.max_entries = max_entries
        self._values: dict[str, tuple[float, ProbeResult]] = {}

    def get(self, key: str) -> ProbeResult | None:
        item = self._values.get(key)
        if item is None:
            return None
        expires, result = item
        if expires <= time.monotonic():
            self._values.pop(key, None)
            return None
        return result

    def put(self, key: str, result: ProbeResult, ttl_ms: int) -> None:
        if len(self._values) >= self.max_entries and key not in self._values:
            self._values.pop(next(iter(self._values)))
        self._values[key] = (time.monotonic() + ttl_ms / 1000, result)


def probe_mock(state: str, *, account_alias: str = "mock", cache: ProbeCache | None = None, ttl_ms: int = 1000) -> ProbeResult:
    if state not in STATES:
        raise ProbePolicyError(f"unsupported probe state: {state}")
    cache = cache or ProbeCache()
    key = f"mock:{state}:{account_alias}"
    cached = cache.get(key)
    if cached:
        return cached
    scenario = MockScenario(state=state, latency_ms=20 if state == "timeout" else 10)
    request = {"body": {"mode": "inline", "encoding": "json", "value": {"model": "probe-model"}}, "meta": {"model_requested": "probe-model"}}
    try:
        response = BoundedTransport(MockTarget(scenario), TransportLimits(timeout_ms=10)).send(request)
        classification = classify_response(response).code
        actual_state = state
        status = "PASS" if state == "ok" else "FAIL"
        exit_code = 0 if status == "PASS" else 1
    except TransportError:
        actual_state, classification, status, exit_code = state, "timeout", "TOOL_ERROR", 4
    result = ProbeResult(actual_state, status, classification, exit_code, f"probe-{state}", ttl_ms, account_alias)
    cache.put(key, result, ttl_ms)
    return result


def ensure_live_allowed(*, live: bool, confirm_live: bool, host: str, allowlist: list[str]) -> None:
    if not live:
        return
    if not confirm_live:
        raise ProbePolicyError("live probe requires --confirm-live")
    if host not in allowlist:
        raise ProbePolicyError("live probe host is outside the profile allowlist")
    raise ProbePolicyError("live transport is not implemented in the offline MVP")
