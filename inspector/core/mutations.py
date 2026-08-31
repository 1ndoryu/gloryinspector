"""Allowlisted, one-variable-at-a-time mutation primitives."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any

MAX_VARIANTS = 32
_PATH_PART = re.compile(r"(?:\.([A-Za-z_][A-Za-z0-9_-]*)|\[([0-9]+)\])")


class MutationError(ValueError):
    """Raised when a mutation spec is ambiguous or exceeds the budget."""


@dataclass(frozen=True)
class MutationSpec:
    variable: str
    path: str
    variants: tuple[Any, ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MutationSpec":
        if set(value) - {"variable", "path", "variants"}:
            raise MutationError("mutation spec contains unsupported fields")
        variable = value.get("variable")
        path = value.get("path")
        variants = value.get("variants")
        if not isinstance(variable, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", variable):
            raise MutationError("variable must be a stable identifier")
        if not isinstance(path, str) or "*" in path or not path.startswith("$"):
            raise MutationError("path must be an explicit JSON path without wildcards")
        if not isinstance(variants, list) or not variants or len(variants) > MAX_VARIANTS:
            raise MutationError("variants must contain between 1 and 32 values")
        _parse_path(path)
        return cls(variable, path, tuple(variants))


def _parse_path(path: str) -> list[str | int]:
    if path == "$":
        raise MutationError("root mutation is not allowed")
    position = 1
    parts: list[str | int] = []
    while position < len(path):
        match = _PATH_PART.match(path, position)
        if not match:
            raise MutationError(f"invalid mutation path near {path[position:]!r}")
        parts.append(match.group(1) if match.group(1) is not None else int(match.group(2)))
        position = match.end()
    return parts


def apply_mutation(value: Any, spec: MutationSpec, variant: Any) -> Any:
    result = copy.deepcopy(value)
    parts = _parse_path(spec.path)
    cursor = result
    for part in parts[:-1]:
        if isinstance(part, int):
            if not isinstance(cursor, list) or part >= len(cursor):
                raise MutationError("mutation path index does not exist")
            cursor = cursor[part]
        else:
            if not isinstance(cursor, dict) or part not in cursor:
                raise MutationError("mutation path field does not exist")
            cursor = cursor[part]
    last = parts[-1]
    delete = isinstance(variant, dict) and variant.get("delete") is True and set(variant) == {"delete"}
    if isinstance(last, int):
        if not isinstance(cursor, list) or last >= len(cursor):
            raise MutationError("mutation path index does not exist")
        if delete:
            cursor.pop(last)
        else:
            cursor[last] = copy.deepcopy(variant)
    else:
        if not isinstance(cursor, dict):
            raise MutationError("mutation path parent is not an object")
        if delete:
            cursor.pop(last, None)
        else:
            cursor[last] = copy.deepcopy(variant)
    return result
