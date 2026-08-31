"""Assertions turn observed response facts into explicit PASS/FAIL findings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Assertion:
    name: str
    passed: bool
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "message": self.message}


def assert_response(response: dict[str, Any], expectations: dict[str, Any] | None = None) -> list[Assertion]:
    expectations = expectations or {}
    assertions: list[Assertion] = []
    if "status" in expectations:
        expected = expectations["status"]
        actual = response.get("status")
        assertions.append(Assertion("status", actual == expected, f"expected status {expected}, observed {actual}"))
    meta = response.get("meta", {}) if isinstance(response.get("meta"), dict) else {}
    if expectations.get("schema_valid") is True:
        actual = meta.get("schema_valid") is True
        assertions.append(Assertion("schema", actual, "response schema is valid" if actual else "response schema is invalid"))
    if expectations.get("stream_complete") is True:
        actual = meta.get("stream_complete") is True
        assertions.append(Assertion("stream", actual, "stream completed" if actual else "stream was truncated"))
    if expectations.get("downgrade_is_failure"):
        requested = meta.get("model_requested")
        effective = meta.get("model_effective")
        actual = isinstance(requested, str) and isinstance(effective, str) and requested == effective
        assertions.append(Assertion("model_identity", actual, f"requested={requested!r}, effective={effective!r}"))
    if "required_headers" in expectations:
        headers = response.get("headers", {})
        for name, expected in expectations["required_headers"].items():
            actual = isinstance(headers, dict) and headers.get(name) == expected
            assertions.append(Assertion(f"header:{name}", actual, f"expected {expected!r}, observed {headers.get(name) if isinstance(headers, dict) else None!r}"))
    return assertions
