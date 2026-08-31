"""Capture facade for explicit local import and loopback adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .adapters.import_jsonl import import_file
from .adapters.loopback import LoopbackMockServer


def import_capture(input_path: Path, output_dir: Path, session_id: str = "import-session") -> dict[str, Any]:
    return import_file(input_path, output_dir, session_id=session_id)


def loopback_capture() -> LoopbackMockServer:
    return LoopbackMockServer()
