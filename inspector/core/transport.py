"""Transport boundary with resource limits and no implicit retries."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse
from dataclasses import dataclass
from threading import Event
from typing import Any, Protocol


class TransportError(RuntimeError):
    """Raised for timeout, cancellation, size, or target errors."""


class Target(Protocol):
    def handle(self, request: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class TransportLimits:
    timeout_ms: int = 10_000
    max_response_bytes: int = 8 * 1024 * 1024
    retries: int = 0


class LoopbackHttpTarget:
    """HTTP target restricted to an explicitly loopback IPv4 URL."""

    def __init__(self, url: str):
        parsed = urlparse(url)
        if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.username or parsed.password:
            raise TransportError("replay HTTP target must be http://127.0.0.1")
        self.url = url

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        body = request.get("body", {}).get("value", {})
        payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        http_request = urllib.request.Request(self.url, data=payload, method="POST", headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(http_request, timeout=10) as response:
                status = response.status
                raw = response.read()
                headers = dict(response.headers.items())
        except urllib.error.HTTPError as exc:
            status = exc.code
            raw = exc.read()
            headers = dict(exc.headers.items())
        try:
            parsed_body: Any = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed_body = {"text": raw.decode("utf-8", errors="replace")}
        requested = request.get("meta", {}).get("model_requested") if isinstance(request.get("meta"), dict) else None
        return {"status": status, "headers": headers, "body": parsed_body, "meta": {"model_requested": requested, "model_effective": parsed_body.get("model") if isinstance(parsed_body, dict) else None, "stream_complete": True, "schema_valid": True, "latency_ms": 0}}


class BoundedTransport:
    def __init__(self, target: Target, limits: TransportLimits | None = None):
        self.target = target
        self.limits = limits or TransportLimits()
        if self.limits.retries != 0:
            raise TransportError("retries are disabled in the MVP")

    def send(self, request: dict[str, Any], cancel: Event | None = None) -> dict[str, Any]:
        if cancel and cancel.is_set():
            raise TransportError("cancelled")
        started = time.monotonic()
        try:
            response = self.target.handle(request)
        except Exception as exc:
            raise TransportError(f"target error: {exc}") from exc
        elapsed_ms = int((time.monotonic() - started) * 1000)
        simulated_latency = response.get("meta", {}).get("latency_ms", 0) if isinstance(response.get("meta"), dict) else 0
        if elapsed_ms + simulated_latency > self.limits.timeout_ms:
            raise TransportError("timeout")
        if cancel and cancel.is_set():
            raise TransportError("cancelled")
        response_bytes = len(json.dumps(response, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        if response_bytes > self.limits.max_response_bytes:
            raise TransportError("response exceeds maximum size")
        return response
