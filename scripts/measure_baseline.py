"""Informational local baseline; it does not claim throughput or contact the network."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from inspector.bundle import scan_bundle  # noqa: E402
from inspector.core.redaction import redact_value  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure bounded offline redaction and bundle baselines")
    parser.add_argument("--mode", choices=("redaction", "bundle", "both"), default="both")
    args = parser.parse_args()
    report: dict[str, object] = {"tool_version": "0.1.0", "measurements": []}
    for size in (1024 * 1024, 8 * 1024 * 1024):
        if args.mode in {"redaction", "both"}:
            chunk = "x" * (60 * 1024)
            value = {"payload": [chunk] * max(1, (size - 20) // len(chunk))}
            started = time.perf_counter()
            result = redact_value(value, session_id="baseline")
            report["measurements"].append({"operation": "redaction", "size_bytes": size, "duration_ms": round((time.perf_counter() - started) * 1000, 3), "status": result.status})
        if args.mode in {"bundle", "both"}:
            with tempfile.TemporaryDirectory() as directory:
                bundle = Path(directory) / "synthetic.js"
                bundle.write_bytes(b"x" * size)
                started = time.perf_counter()
                result = scan_bundle(bundle, ROOT / "packs" / "bundle.json")
                report["measurements"].append({"operation": "bundle", "size_bytes": size, "duration_ms": round((time.perf_counter() - started) * 1000, 3), "candidate_count": result["candidate_count"]})
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
