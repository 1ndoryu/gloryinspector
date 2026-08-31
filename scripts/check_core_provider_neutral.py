"""Keep core modules independent from provider-specific integrations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

FORBIDDEN_TERMS = ("openai", "anthropic", "gemini", "claude", "azure")


def scan(root: Path) -> list[str]:
    core = root / "inspector" / "core"
    findings: list[str] = []
    if not core.exists():
        return findings
    for path in sorted(item for item in core.rglob("*.py") if item.is_file()):
        text = path.read_text(encoding="utf-8").lower()
        for term in FORBIDDEN_TERMS:
            if term in text:
                findings.append(f"{path.relative_to(root)}:{term}")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check provider neutrality of inspector/core")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    findings = scan(args.root.resolve())
    if findings:
        for finding in findings:
            print(f"PROVIDER_SPECIFIC_CORE_REFERENCE: {finding}", file=sys.stderr)
        return 1
    print("CORE_PROVIDER_NEUTRAL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
