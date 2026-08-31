"""Text-only bundle analysis; untrusted JavaScript is never imported or executed."""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

MAX_BUNDLE_BYTES = 8 * 1024 * 1024
MAX_CONTEXT = 80


def load_pack(path: Path) -> dict[str, Any]:
    pack = json.loads(path.read_text(encoding="utf-8"))
    if pack.get("schema") != "inspector.pack/v1" or not isinstance(pack.get("rules"), list):
        raise ValueError("invalid bundle pack")
    return pack


def scan_bundle(path: Path, pack_path: Path) -> dict[str, Any]:
    started = time.monotonic()
    data = path.read_bytes()
    if len(data) > MAX_BUNDLE_BYTES:
        raise ValueError("bundle exceeds bounded 8 MiB limit")
    text = data.decode("utf-8", errors="replace")
    pack = load_pack(pack_path)
    seen: set[tuple[str, str, int]] = set()
    candidates: list[dict[str, Any]] = []
    for rule in pack["rules"]:
        pattern = str(rule["pattern"])
        if len(pattern) > 256:
            raise ValueError(f"bundle regex is not bounded: {rule.get('id')}")
        compiled = re.compile(pattern)
        for match in compiled.finditer(text):
            value = match.group(1) if match.lastindex else match.group(0)
            offset = len(text[: match.start()].encode("utf-8"))
            key = (str(rule["id"]), value, offset)
            if key in seen:
                continue
            seen.add(key)
            context_start = max(0, match.start() - MAX_CONTEXT)
            context_end = min(len(text), match.end() + MAX_CONTEXT)
            candidates.append({
                "rule": str(rule["id"]), "value": value, "offset": offset,
                "score": int(rule.get("priority", 1)), "confirmed": False,
                "context": text[context_start:context_end],
            })
    candidates.sort(key=lambda item: (item["offset"], item["rule"], item["value"]))
    return {
        "schema": "inspector.bundle-report/v1",
        "bundle_sha256": f"sha256:{hashlib.sha256(data).hexdigest()}",
        "size_bytes": len(data),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "duration_ms": int((time.monotonic() - started) * 1000),
        "executed": False,
        "tool_version": "0.1.0",
    }
