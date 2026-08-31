"""Offline redaction command implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .core.redaction import RedactionResult, redact_value


def _load_input(path: Path) -> tuple[Any, bool]:
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text), True
    except json.JSONDecodeError:
        return text, False


def redact_file(input_path: Path, output_path: Path | None, *, session_id: str, force: bool = False) -> RedactionResult:
    value, is_json = _load_input(input_path)
    result = redact_value(value, session_id=session_id)
    if result.status in {"blocked", "unknown"}:
        return result
    if output_path is not None:
        if output_path.exists() and not force:
            return RedactionResult(value=result.value, status="blocked", rules=result.rules, matches=result.matches, reason="output exists; use --force")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if is_json:
            output_path.write_text(json.dumps(result.value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        else:
            output_path.write_text(str(result.value), encoding="utf-8")
    return result
