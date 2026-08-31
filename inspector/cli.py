"""Command-line facade for the offline, provider-neutral MVP."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .bundle import scan_bundle
from .capture import import_capture
from .core.classification import classify_response
from .core.mutations import MutationSpec
from .core.schema import SchemaValidationError, load_json, load_schema, validate
from .diff import run_diff
from .export import ExportError, write_export
from .probe import ProbePolicyError, probe_mock
from .redact import redact_file
from .replay import replay_request, target_from_uri
from .track import track_request


def _json_output(value: Any, output: Path | None, *, force: bool = False) -> None:
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if output is None:
        print(rendered, end="")
        return
    if output.exists() and not force:
        raise ValueError("output exists; use --force")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="inspector", description="Validate and reproduce sanitized gloryInspector evidence without network access.")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command")

    validate_parser = commands.add_parser("validate", help="validate explicit JSON against a schema")
    validate_parser.add_argument("--schema", required=True, type=Path)
    validate_parser.add_argument("--input", required=True, type=Path)
    validate_parser.add_argument("--format", choices=("json", "text"), default="text")

    redact_parser = commands.add_parser("redact", help="redact an explicit local file before persistence")
    redact_parser.add_argument("--input", required=True, type=Path)
    redact_parser.add_argument("--output", type=Path)
    redact_parser.add_argument("--session-id", default="cli-session")
    redact_parser.add_argument("--check", action="store_true")
    redact_parser.add_argument("--write", action="store_true")
    redact_parser.add_argument("--force", action="store_true")

    replay_parser = commands.add_parser("replay", help="replay a request against a deterministic mock target")
    replay_parser.add_argument("--input", required=True, type=Path)
    replay_parser.add_argument("--target", default="mock://historical-auto")
    replay_parser.add_argument("--timeout", type=int, default=10000)
    replay_parser.add_argument("--output", type=Path)
    replay_parser.add_argument("--force", action="store_true")

    classify_parser = commands.add_parser("classify", help="classify an explicit response or trace")
    classify_parser.add_argument("--input", required=True, type=Path)

    diff_parser = commands.add_parser("diff", help="run one allowlisted mutation at a time against the mock")
    diff_parser.add_argument("--input", required=True, type=Path)
    diff_parser.add_argument("--output", type=Path)
    diff_parser.add_argument("--force", action="store_true")

    bundle_parser = commands.add_parser("bundle", help="scan a local bundle as bytes without executing it")
    bundle_parser.add_argument("--input", required=True, type=Path)
    bundle_parser.add_argument("--pack", type=Path, default=Path("packs/bundle.json"))
    bundle_parser.add_argument("--output", type=Path)
    bundle_parser.add_argument("--force", action="store_true")

    capture_parser = commands.add_parser("capture", help="import explicit local evidence")
    capture_commands = capture_parser.add_subparsers(dest="capture_command")
    import_parser = capture_commands.add_parser("import", help="import HAR or record list")
    import_parser.add_argument("--input", required=True, type=Path)
    import_parser.add_argument("--output", required=True, type=Path)
    import_parser.add_argument("--session-id", default="import-session")
    capture_commands.add_parser("loopback", help="show the loopback-only adapter contract")

    probe_parser = commands.add_parser("probe", help="run a bounded mock probe")
    probe_parser.add_argument("--state", choices=("ok", "banned", "rate_limited", "token_invalid", "country_blocked", "model_locked", "ip_capped", "timeout", "unknown"), default="ok")
    probe_parser.add_argument("--account-alias", default="mock")
    probe_parser.add_argument("--live", action="store_true")
    probe_parser.add_argument("--confirm-live", action="store_true")

    track_parser = commands.add_parser("track", help="compare one mock run against a golden result")
    track_parser.add_argument("--input", required=True, type=Path)
    track_parser.add_argument("--golden", required=True, type=Path)
    track_parser.add_argument("--output", type=Path)
    track_parser.add_argument("--force", action="store_true")

    export_parser = commands.add_parser("export", help="export a bounded result envelope")
    export_parser.add_argument("--result", required=True, type=Path)
    export_parser.add_argument("--output", required=True, type=Path)
    export_parser.add_argument("--fixture-id", required=True)
    export_parser.add_argument("--profile-id", required=True)
    export_parser.add_argument("--source", choices=("mock", "import", "loopback", "authorized"), default="mock")
    export_parser.add_argument("--force", action="store_true")
    return parser


def _handle(args: argparse.Namespace) -> int:
    if args.command == "validate":
        schema = load_schema(args.schema)
        value = load_json(args.input)
        validate(value, schema)
        if args.format == "json":
            print(json.dumps({"status": "PASS", "schema": schema["schema"], "input": str(args.input)}, sort_keys=True))
        else:
            print(f"VALID: {args.input} against {schema['schema']}")
        return 0
    if args.command == "redact":
        if args.check and args.write:
            raise ValueError("--check and --write are mutually exclusive")
        if args.write and args.output is None:
            raise ValueError("--write requires --output")
        if args.output is not None and not args.write:
            raise ValueError("--output requires --write")
        result = redact_file(args.input, args.output if args.write else None, session_id=args.session_id, force=args.force)
        print(json.dumps({"status": result.status, "rules": result.rules, "matches": result.matches, "reason": result.reason}, sort_keys=True))
        return 3 if result.status in {"blocked", "unknown"} else 0
    if args.command == "replay":
        result = replay_request(load_json(args.input), target=target_from_uri(args.target), expectations={"downgrade_is_failure": True}, timeout_ms=args.timeout)
        _json_output({key: value for key, value in result.items() if key != "response"}, args.output, force=args.force)
        return 0 if result["status"] == "PASS" else 1 if result["status"] == "FAIL" else 4
    if args.command == "classify":
        classification = classify_response(load_json(args.input))
        print(json.dumps({"taxonomy": classification.taxonomy, "classification": classification.code, "evidence": classification.evidence}, sort_keys=True))
        return 0
    if args.command == "diff":
        case = load_json(args.input)
        matrix = run_diff(case["base"], MutationSpec.from_dict(case["mutation"]))
        _json_output({"schema": "inspector.diff/v1", "matrix": matrix}, args.output, force=args.force)
        return 0 if matrix else 1
    if args.command == "bundle":
        report = scan_bundle(args.input, args.pack)
        _json_output(report, args.output, force=args.force)
        return 0
    if args.command == "capture":
        if args.capture_command == "import":
            _json_output(import_capture(args.input, args.output, args.session_id), None)
            return 0
        if args.capture_command == "loopback":
            print(json.dumps({"adapter": "loopback", "bind": "127.0.0.1", "external_network": False}, sort_keys=True))
            return 0
        raise ValueError("capture requires import or loopback")
    if args.command == "probe":
        if args.live:
            raise ProbePolicyError("live transport is not implemented in the offline MVP")
        result = probe_mock(args.state, account_alias=args.account_alias)
        print(json.dumps(result.as_dict(), sort_keys=True))
        return result.exit_code
    if args.command == "track":
        report = track_request(load_json(args.input), load_json(args.golden))
        _json_output(report, args.output, force=args.force)
        return 0 if report["status"] in {"PASS", "WARN"} else 4 if report["status"] in {"TOOL_ERROR", "NOT_RUN"} else 1
    if args.command == "export":
        result = load_json(args.result)
        write_export(result, args.output, fixture_id=args.fixture_id, profile_id=args.profile_id, source=args.source, force=args.force)
        print(f"EXPORTED: {args.output}")
        return 0
    if args.command is None:
        build_parser().print_help()
        return 0
    raise ValueError(f"unknown command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        return _handle(parser.parse_args(argv))
    except (OSError, KeyError, TypeError, ValueError, SchemaValidationError, ExportError, ProbePolicyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2 if not isinstance(exc, ProbePolicyError) else 5
