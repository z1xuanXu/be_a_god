#!/usr/bin/env python3
"""Validate a WORLD-BRIEF draft before formal world initialization."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REQUIRED_CONFIRMED_FIELDS = {
    "world premise": ["world premise", "世界前提"],
    "starting era": ["starting era", "起始时代", "era"],
    "starting region": ["starting region", "起始地区", "starting area"],
    "god role": ["god role", "神格", "神明角色"],
}

RECOMMENDED_FIELDS = {
    "tone": ["tone", "基调", "风格"],
}


def has_confirmed_status(text: str) -> bool:
    return bool(re.search(r"^\s*status\s*:\s*confirmed\s*$", text, re.IGNORECASE | re.MULTILINE))


def has_source_map(text: str) -> bool:
    return "## Field source map" in text and "player-locked" in text and "ai-fill" in text


def find_field(text: str, aliases: list[str]) -> bool:
    lower = text.lower()
    for alias in aliases:
        alias_lower = alias.lower()
        if re.search(rf"^\s*-\s*{re.escape(alias_lower)}\s*:\s*\S+", lower, re.MULTILINE):
            return True
        if re.search(rf"^\s*{re.escape(alias_lower)}\s*:\s*\S+", lower, re.MULTILINE):
            return True
    return False


def validate(path: Path, require_confirmed: bool) -> dict:
    text = path.read_text(encoding="utf-8")
    missing_required = [name for name, aliases in REQUIRED_CONFIRMED_FIELDS.items() if not find_field(text, aliases)]
    missing_recommended = [name for name, aliases in RECOMMENDED_FIELDS.items() if not find_field(text, aliases)]
    confirmed = has_confirmed_status(text)
    errors = []
    warnings = []
    if require_confirmed and not confirmed:
        errors.append("WORLD-BRIEF is not confirmed. Add `Status: confirmed` after player confirmation.")
    if require_confirmed and confirmed:
        for field in missing_required:
            errors.append(f"Required confirmed field is missing or blank: {field}")
    else:
        for field in missing_required:
            warnings.append(f"Required field is missing or blank before confirmation: {field}")
    source_map_present = has_source_map(text)
    if require_confirmed and confirmed and not source_map_present:
        errors.append("Confirmed WORLD-BRIEF must include a Field source map for locked, polishable, and AI-fill fields.")
    elif not source_map_present:
        warnings.append("WORLD-BRIEF has no Field source map for locked, polishable, and AI-fill fields.")
    for field in missing_recommended:
        warnings.append(f"Recommended field is missing or blank: {field}")
    return {
        "schema": "be-a-god.world-brief-validation.v1",
        "path": str(path),
        "ok": not errors,
        "confirmed": confirmed,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a be-a-god WORLD-BRIEF draft.")
    parser.add_argument("brief")
    parser.add_argument("--require-confirmed", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    path = Path(args.brief).resolve()
    if not path.exists() or not path.is_file():
        raise SystemExit(f"WORLD-BRIEF not found: {path}")
    result = validate(path, args.require_confirmed)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("WORLD-BRIEF validation OK" if result["ok"] else "WORLD-BRIEF validation FAILED")
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")
        for error in result["errors"]:
            print(f"ERROR: {error}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
