"""Fail-closed scanner for obvious secret-shaped values in local artifacts."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:sk|rk)-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~-]{20,}\b", re.IGNORECASE),
)
SCAN_DIRS = ("inspector", "schemas", "fixtures", "docs", "profiles", "packs")


def scan(root: Path) -> list[str]:
    findings: list[str] = []
    for directory in SCAN_DIRS:
        base = root / directory
        if not base.exists():
            continue
        for path in sorted(item for item in base.rglob("*") if item.is_file()):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for pattern in PATTERNS:
                if pattern.search(text):
                    findings.append(path.relative_to(root).as_posix())
                    break
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan project artifacts for obvious secret-shaped values")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    findings = scan(args.root.resolve())
    if findings:
        for finding in findings:
            print(f"SECRET_SHAPED_VALUE: {finding}", file=sys.stderr)
        return 3
    print("NO_SECRET_SHAPED_VALUES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
