"""Profile loading without resolving or serializing credential values."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .schema import SchemaValidationError, load_schema, validate

PROFILE_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "profile-v1.json"


class ProfileError(ValueError):
    """Raised when a profile is structurally or operationally unsafe."""


def load_profile(path: Path) -> dict[str, Any]:
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProfileError(f"cannot load profile: {exc}") from exc
    try:
        validate(profile, load_schema(PROFILE_SCHEMA_PATH))
    except SchemaValidationError as exc:
        raise ProfileError(str(exc)) from exc
    for name, target in profile["targets"].items():
        parsed = urlparse(target["url_template"])
        if parsed.scheme != "https" or not parsed.hostname:
            raise ProfileError(f"target {name} must use an explicit HTTPS URL")
        if "{" in target["url_template"] or "}" in target["url_template"]:
            raise ProfileError(f"target {name} cannot contain arbitrary URL templates")
        auth = target.get("auth")
        if auth and ("credential" in auth or "value" in auth or "secret" in auth):
            raise ProfileError(f"target {name} contains an inline credential")
    for host in profile["capture"]["host_allowlist"]:
        if not re.fullmatch(r"(?:[A-Za-z0-9-]+\.)*[A-Za-z0-9-]+", host):
            raise ProfileError(f"invalid capture host allowlist entry: {host!r}")
    return profile
