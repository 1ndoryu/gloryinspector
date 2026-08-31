"""Context-aware, bounded redaction used before any evidence is persisted."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import Any

MAX_DEPTH = 32
MAX_STRING_LENGTH = 64 * 1024
MAX_MATCHES = 1000

SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "api-key",
        "api_key",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "password",
        "credential",
    }
)

PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("bearer", re.compile(r"\bBearer\s+[A-Za-z0-9._~-]{12,}\b", re.IGNORECASE)),
    ("api_key", re.compile(r"\b(?:sk|rk)-[A-Za-z0-9_-]{16,}\b")),
    ("aws_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("uuid", re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b")),
)


@dataclass(frozen=True)
class RedactionResult:
    value: Any
    status: str
    rules: tuple[str, ...] = ()
    matches: int = 0
    reason: str | None = None

    @property
    def changed(self) -> bool:
        return self.status == "changed"


@dataclass
class _Context:
    session_id: str
    max_matches: int
    matches: int = 0
    rules: list[str] = field(default_factory=list)

    def placeholder(self, rule: str, raw: str) -> str:
        self.matches += 1
        if self.matches > self.max_matches:
            raise ValueError("maximum redaction matches exceeded")
        digest = hashlib.sha256(f"{self.session_id}\0{rule}\0{raw}".encode("utf-8")).hexdigest()[:12]
        if rule not in self.rules:
            self.rules.append(rule)
        return f"{{{{redacted:{rule}:{digest}}}}}"


def _is_high_entropy(value: str) -> bool:
    if len(value) < 24 or value.startswith("{{"):
        return False
    alphabet = set(value)
    if len(alphabet) < 10 or not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
        return False
    counts = {char: value.count(char) for char in alphabet}
    entropy = -sum((count / len(value)) * math.log2(count / len(value)) for count in counts.values())
    return entropy >= 3.5


def _key_is_sensitive(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    return normalized in {item.replace("-", "_") for item in SENSITIVE_KEYS} or any(
        token in normalized for token in ("authorization", "cookie", "token", "secret", "password", "api_key", "credential")
    )


def _redact_text(value: str, context: _Context) -> str:
    if len(value) > MAX_STRING_LENGTH:
        raise ValueError("string exceeds bounded redaction size")
    redacted = value
    for rule, pattern in PATTERNS:
        redacted = pattern.sub(lambda match: context.placeholder(rule, match.group(0)), redacted)
    if _is_high_entropy(redacted):
        redacted = context.placeholder("high_entropy", redacted)
    return redacted


def _redact(value: Any, context: _Context, *, depth: int, key: str | None = None) -> Any:
    if depth > MAX_DEPTH:
        raise ValueError("JSON depth exceeds bounded redaction depth")
    if isinstance(value, str):
        if key and _key_is_sensitive(key):
            return context.placeholder("sensitive_field", value)
        return _redact_text(value, context)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, list):
        return [_redact(item, context, depth=depth + 1) for item in value]
    if isinstance(value, dict):
        return {str(item_key): _redact(item, context, depth=depth + 1, key=str(item_key)) for item_key, item in value.items()}
    raise TypeError(f"unsupported value type: {type(value).__name__}")


def redact_value(value: Any, *, session_id: str, max_matches: int = MAX_MATCHES) -> RedactionResult:
    """Redact a JSON-compatible value, blocking unsupported or oversized input."""

    context = _Context(session_id=session_id, max_matches=min(max_matches, MAX_MATCHES))
    try:
        cleaned = _redact(value, context, depth=0)
    except TypeError as exc:
        return RedactionResult(value=None, status="unknown", matches=context.matches, rules=tuple(context.rules), reason=str(exc))
    except ValueError as exc:
        return RedactionResult(value=None, status="blocked", matches=context.matches, rules=tuple(context.rules), reason=str(exc))
    status = "changed" if cleaned != value else "clean"
    return RedactionResult(value=cleaned, status=status, matches=context.matches, rules=tuple(context.rules))


def redact_text(value: str, *, session_id: str, max_matches: int = MAX_MATCHES) -> RedactionResult:
    return redact_value(value, session_id=session_id, max_matches=max_matches)
