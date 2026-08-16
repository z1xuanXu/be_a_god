#!/usr/bin/env python3
"""Validate model/Codex settlement result JSON before canon writes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


CONCRETE_LEGACY_FIELDS = ["event", "state_appends", "chronicle", "consequences", "save_updates", "dashboard"]
REQUIRED_LAYERS = ["visible_narration", "gm_summary", "settlement_plan"]


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid settlement result JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("Settlement result must be a JSON object")
    return data


def non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def has_concrete_legacy_plan(result: dict[str, Any]) -> bool:
    event = result.get("event")
    if isinstance(event, dict) and (non_empty_text(event.get("title")) or non_empty_text(event.get("type"))):
        return True
    if isinstance(result.get("state_appends"), list) and result.get("state_appends"):
        return True
    if non_empty_text(result.get("chronicle")):
        return True
    if non_empty_text(result.get("consequences")):
        return True
    if isinstance(result.get("save_updates"), dict) and result.get("save_updates"):
        return True
    dashboard = result.get("dashboard")
    if isinstance(dashboard, dict) and any(dashboard.get(key) for key in dashboard):
        return True
    return False


def inferred_settlement_plan(result: dict[str, Any]) -> dict[str, Any]:
    event = result.get("event") if isinstance(result.get("event"), dict) else {}
    dashboard = result.get("dashboard") if isinstance(result.get("dashboard"), dict) else {}
    return {
        "source": "legacy-result-fields",
        "event": {
            "title": event.get("title"),
            "type": event.get("type"),
            "actors": event.get("actors", []),
            "causes": event.get("causes", []),
            "effects": event.get("effects", []),
            "tags": event.get("tags", []),
        },
        "state_appends_count": len(result.get("state_appends", []) or []),
        "has_chronicle": non_empty_text(result.get("chronicle")),
        "has_consequences": non_empty_text(result.get("consequences")),
        "save_update_fields": sorted((result.get("save_updates") or {}).keys()) if isinstance(result.get("save_updates"), dict) else [],
        "dashboard_update_fields": sorted(dashboard.keys()),
    }


def validate_result(result: dict[str, Any], *, kind: str = "settlement", allow_legacy: bool = True) -> tuple[dict[str, Any], list[str]]:
    """Return normalized narrative layers plus warnings, or raise SystemExit."""
    warnings: list[str] = []
    if not non_empty_text(result.get("summary")) and not non_empty_text(result.get("visible_narration")):
        raise SystemExit(f"{kind} result must include `summary` or `visible_narration`.")

    visible = result.get("visible_narration") or result.get("summary") or result.get("current_scene")
    gm_summary = result.get("gm_summary") or result.get("summary")
    settlement_plan = result.get("settlement_plan")

    if not non_empty_text(visible):
        raise SystemExit(f"{kind} result missing visible narration text.")
    if not non_empty_text(gm_summary):
        raise SystemExit(f"{kind} result missing gm_summary text.")

    if settlement_plan is None:
        if allow_legacy and has_concrete_legacy_plan(result):
            settlement_plan = inferred_settlement_plan(result)
            warnings.append("settlement_plan inferred from legacy result fields")
        else:
            raise SystemExit(
                f"{kind} result has no concrete settlement plan. Include `settlement_plan` or concrete fields such as event, chronicle, consequences, state_appends, save_updates, or dashboard."
            )
    elif not isinstance(settlement_plan, (dict, list)):
        raise SystemExit(f"{kind} result `settlement_plan` must be an object or list.")

    return {
        "visible_narration": str(visible).strip(),
        "gm_summary": str(gm_summary).strip(),
        "settlement_plan": settlement_plan,
        "required_layers": REQUIRED_LAYERS,
    }, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a be-a-god settlement result JSON before canonical writes.")
    parser.add_argument("--result", required=True, help="Settlement result JSON file.")
    parser.add_argument("--kind", default="settlement", choices=["settlement", "interaction", "queued-event"])
    parser.add_argument("--strict", action="store_true", help="Require explicit visible_narration, gm_summary, and settlement_plan keys.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = read_json(Path(args.result).resolve())
    if args.strict:
        missing = [field for field in REQUIRED_LAYERS if field not in result]
        if missing:
            raise SystemExit(f"Strict settlement result missing required layers: {missing}")
    layers, warnings = validate_result(result, kind=args.kind, allow_legacy=not args.strict)
    report = {"ok": True, "kind": args.kind, "layers": layers, "warnings": warnings}
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else "Settlement result OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
