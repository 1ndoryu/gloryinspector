"""Deterministic output helpers with explicit size limits."""

from __future__ import annotations

import json
from typing import Any

MAX_REPORT_BYTES = 10 * 1024 * 1024


def to_json(value: Any) -> str:
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if len(rendered.encode("utf-8")) > MAX_REPORT_BYTES:
        raise ValueError("report exceeds bounded output size")
    return rendered
