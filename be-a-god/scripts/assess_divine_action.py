#!/usr/bin/env python3
"""Create a non-canonical cost preview for a divine action."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = "be-a-god.divine-assessment.v1"
SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
ACTION_BASE = {
    "observe": 0,
    "speak": 0,
    "weather-override": 2,
    "intervene": 4,
    "heal": 4,
    "curse": 5,
    "bless": 5,
    "create": 6,
    "destroy": 7,
    "resurrect": 9,
    "branch": 8,
    "rule-change": 10,
    "custom": 4,
}
SCALE_COST = {"personal": 0, "local": 2, "regional": 5, "world": 9}
IRREVERSIBILITY_COST = {"none": 0, "reversible": 1, "durable": 4, "irreversible": 8}
VISIBILITY_COST = {"hidden": 0, "subtle": 1, "open": 3, "miracle": 5}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_now_id() -> str:
    return "DA-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")


def parse_active(world: Path) -> dict[str, str]:
    active_path = world / "ACTIVE.md"
    if not active_path.exists():
        raise SystemExit(f"ACTIVE.md not found in world directory: {world}")
    data = {}
    for line in active_path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    data.setdefault("branch_path", "story/main")
    data.setdefault("branch_id", "main")
    data.setdefault("save_path", f"{data['branch_path']}/SAVE.md")
    return data


def parse_field(text: str, field: str) -> str | None:
    match = re.search(rf"^\s*-\s*{re.escape(field)}:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def resolve_world(path: str) -> Path:
    world = Path(path).resolve()
    if not world.exists() or not world.is_dir():
        raise SystemExit(f"World directory not found: {world}")
    return world


def validate_id(value: str, field: str) -> str:
    if not SAFE_ID_PATTERN.fullmatch(value):
        raise SystemExit(f"{field} must contain only letters, numbers, underscores, or hyphens: {value}")
    return value


def read_player_limit(world: Path, default: int) -> int:
    player = world / "PLAYER.md"
    if not player.exists():
        return default
    text = player.read_text(encoding="utf-8")
    for field in ("divine_power_limit", "god_power_limit", "normal_power_limit"):
        value = parse_field(text, field)
        if value is None:
            continue
        try:
            return int(value)
        except ValueError:
            continue
    return default


def target_pressure(target_count: int) -> int:
    if target_count <= 1:
        return 0
    if target_count <= 5:
        return 1
    if target_count <= 20:
        return 3
    return 6


def classify(score: int, normal_limit: int, absolute: bool) -> str:
    if absolute:
        return "absolute-authorized"
    if score <= normal_limit:
        return "within-normal-limit"
    if score <= normal_limit + 4:
        return "over-limit-warning"
    return "major-overreach"


def build_assessment(args: argparse.Namespace) -> tuple[dict[str, Any], Path, Path]:
    world = resolve_world(args.world)
    active = parse_active(world)
    branch = world / active["branch_path"]
    if not branch.exists():
        raise SystemExit(f"Active branch path missing: {active['branch_path']}")
    normal_limit = args.normal_limit if args.normal_limit is not None else read_player_limit(world, args.default_limit)
    score = (
        ACTION_BASE[args.action]
        + SCALE_COST[args.scale]
        + IRREVERSIBILITY_COST[args.irreversibility]
        + VISIBILITY_COST[args.visibility]
        + target_pressure(args.target_count)
    )
    status = classify(score, normal_limit, args.absolute)
    assessment_id = validate_id(args.assessment_id or utc_now_id(), "--assessment-id")
    output_dir = branch / "runtime" / "divine-assessments" / assessment_id
    assessment = {
        "schema": SCHEMA,
        "assessment_id": assessment_id,
        "created_at": utc_now(),
        "status": status,
        "canonical_effect": "none",
        "world_id": active.get("world_id", world.name),
        "branch_id": active.get("branch_id", "main"),
        "branch_path": active["branch_path"],
        "save_path": active["save_path"],
        "action_request_id": args.request_id,
        "action": args.action,
        "target_id": args.target_id,
        "description": args.description,
        "inputs": {
            "scale": args.scale,
            "irreversibility": args.irreversibility,
            "visibility": args.visibility,
            "target_count": args.target_count,
            "absolute": args.absolute,
        },
        "score": score,
        "normal_limit": normal_limit,
        "cost_breakdown": {
            "action": ACTION_BASE[args.action],
            "scale": SCALE_COST[args.scale],
            "irreversibility": IRREVERSIBILITY_COST[args.irreversibility],
            "visibility": VISIBILITY_COST[args.visibility],
            "target_count": target_pressure(args.target_count),
        },
        "player_options": [
            "accept normal cost" if score <= normal_limit else "accept over-limit cost",
            "narrow the action scope",
            "declare absolute divine authority",
            "cancel or delay the action",
        ],
        "policy": "Assessment is a preview only. It does not execute the action and does not write canon.",
    }
    return assessment, output_dir / "assessment.json", output_dir / "assessment.md"


def render_markdown(assessment: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# Divine Assessment {assessment['assessment_id']}",
            "",
            f"- status: {assessment['status']}",
            f"- canonical_effect: {assessment['canonical_effect']}",
            f"- action: {assessment['action']}",
            f"- target_id: {assessment.get('target_id') or 'WORLD'}",
            f"- score: {assessment['score']}",
            f"- normal_limit: {assessment['normal_limit']}",
            f"- action_request_id: {assessment.get('action_request_id') or 'none'}",
            "",
            "## Description",
            "",
            assessment.get("description") or "none",
            "",
            "## Cost breakdown",
            "",
            *[f"- {key}: {value}" for key, value in assessment["cost_breakdown"].items()],
            "",
            "## Player options",
            "",
            *[f"- {item}" for item in assessment["player_options"]],
            "",
            "## Policy",
            "",
            assessment["policy"],
            "",
        ]
    )


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def refresh_manifest(world: Path) -> None:
    script = Path(__file__).resolve().parent / "build_file_manifest.py"
    subprocess.run([sys.executable, str(script), str(world)], check=True, stdout=subprocess.DEVNULL)


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview divine-action cost without changing canon.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--action", required=True, choices=sorted(ACTION_BASE))
    parser.add_argument("--target-id", default="")
    parser.add_argument("--request-id", default="")
    parser.add_argument("--description", default="")
    parser.add_argument("--scale", default="personal", choices=sorted(SCALE_COST))
    parser.add_argument("--irreversibility", default="reversible", choices=sorted(IRREVERSIBILITY_COST))
    parser.add_argument("--visibility", default="subtle", choices=sorted(VISIBILITY_COST))
    parser.add_argument("--target-count", type=int, default=1)
    parser.add_argument("--normal-limit", type=int)
    parser.add_argument("--default-limit", type=int, default=8)
    parser.add_argument("--absolute", action="store_true")
    parser.add_argument("--assessment-id")
    parser.add_argument("--skip-manifest", action="store_true")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.target_count < 0:
        raise SystemExit("--target-count must be non-negative")
    assessment, json_path, md_path = build_assessment(args)
    if args.dry_run:
        print(json.dumps(assessment, ensure_ascii=False, indent=2))
        return 0
    if not args.confirmed:
        raise SystemExit("Refusing to write divine assessment without --confirmed. Use --dry-run to preview.")
    write_json(json_path, assessment)
    md_path.write_text(render_markdown(assessment), encoding="utf-8")
    if not args.skip_manifest:
        refresh_manifest(resolve_world(args.world))
    result = {
        "ok": True,
        "assessment_id": assessment["assessment_id"],
        "status": assessment["status"],
        "score": assessment["score"],
        "normal_limit": assessment["normal_limit"],
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Created divine assessment: {json_path}")
        print(f"Status: {assessment['status']} score={assessment['score']} limit={assessment['normal_limit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
