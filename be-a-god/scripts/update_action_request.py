#!/usr/bin/env python3
"""Update a branch-local action request lifecycle without executing it."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = "be-a-god.action-request.v1"
SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
FINAL_STATUSES = {"executed", "cancelled"}
TRANSITIONS = {
    "requested": {"accepted", "executed", "cancelled"},
    "accepted": {"executed", "cancelled"},
    "executed": set(),
    "cancelled": set(),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    return data


def resolve_world(path: str) -> Path:
    world = Path(path).resolve()
    if not world.exists() or not world.is_dir():
        raise SystemExit(f"World directory not found: {world}")
    return world


def relative_or_literal(path_text: str, world: Path) -> str:
    if not path_text:
        return ""
    path = Path(path_text)
    if not path.is_absolute():
        return path_text.replace("\\", "/")
    try:
        return path.resolve().relative_to(world.resolve()).as_posix()
    except ValueError:
        return str(path)


def validate_id(value: str, field: str) -> str:
    if not SAFE_ID_PATTERN.fullmatch(value):
        raise SystemExit(f"{field} must contain only letters, numbers, underscores, or hyphens: {value}")
    return value


def load_request(world: Path, branch_path: str, request_id: str) -> tuple[dict[str, Any], Path, Path]:
    request_id = validate_id(request_id, "--request-id")
    request_dir = world / branch_path / "runtime" / "action-requests" / request_id
    request_json = request_dir / "request.json"
    request_md = request_dir / "request.md"
    if not request_json.exists():
        raise SystemExit(f"Action request not found in active branch: {request_json}")
    data = json.loads(request_json.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise SystemExit(f"Unexpected action request schema in {request_json}")
    return data, request_json, request_md


def render_markdown(request: dict[str, Any]) -> str:
    target = request.get("target", {})
    lines = [
        f"# Action Request {request['request_id']}",
        "",
        f"- schema: {request['schema']}",
        f"- status: {request['status']}",
        f"- created_at: {request.get('created_at', '')}",
        f"- updated_at: {request.get('updated_at', '')}",
        f"- world_id: {request.get('world_id', '')}",
        f"- branch_id: {request.get('branch_id', '')}",
        f"- branch_path: {request.get('branch_path', '')}",
        f"- world_time: {request.get('world_time') or 'unknown'}",
        f"- action: {request.get('action', '')}",
        f"- target_id: {target.get('id') or 'WORLD'}",
        f"- target_kind: {target.get('kind') or 'world'}",
        f"- intent: {request.get('intent', '')}",
        "",
        "## Suggested command",
        "",
        "```text",
        request.get("suggested_command", ""),
        "```",
        "",
        "## Lifecycle",
        "",
    ]
    for item in request.get("lifecycle", []):
        result = f" result={item.get('result_path')}" if item.get("result_path") else ""
        note = f" note={item.get('note')}" if item.get("note") else ""
        lines.append(f"- {item.get('at')}: {item.get('from')} -> {item.get('to')}{result}{note}")
    if not request.get("lifecycle"):
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Policy",
            "",
            "- This file is a support request, not canon.",
            "- Updating its status must not change events, chronicle, state, random logs, queues, dashboard, or timeline.",
            "- `executed` means the suggested action was handled elsewhere; inspect `result_path` or linked canon files for effects.",
            "",
        ]
    )
    return "\n".join(lines)


def refresh_manifest(world: Path) -> None:
    script = Path(__file__).resolve().parent / "build_file_manifest.py"
    subprocess.run([sys.executable, str(script), str(world)], check=True, stdout=subprocess.DEVNULL)


def main() -> int:
    parser = argparse.ArgumentParser(description="Update an action request status without executing its suggested command.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--status", required=True, choices=["accepted", "executed", "cancelled"])
    parser.add_argument("--note", default="")
    parser.add_argument("--result-path", default="")
    parser.add_argument("--force", action="store_true", help="Allow updating a final or otherwise invalid transition.")
    parser.add_argument("--skip-manifest", action="store_true")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    world = resolve_world(args.world)
    active = parse_active(world)
    request, request_json, request_md = load_request(world, active["branch_path"], args.request_id)
    old_status = request.get("status", "requested")
    allowed = TRANSITIONS.get(old_status, set())
    if args.status not in allowed and not args.force:
        if old_status in FINAL_STATUSES:
            raise SystemExit(f"Action request is final (`{old_status}`). Use --force only for explicit repair.")
        raise SystemExit(f"Invalid transition: {old_status} -> {args.status}")

    updated = dict(request)
    updated["status"] = args.status
    updated["updated_at"] = utc_now()
    lifecycle = list(updated.get("lifecycle", []))
    lifecycle.append(
        {
            "at": updated["updated_at"],
            "from": old_status,
            "to": args.status,
            "note": args.note,
            "result_path": relative_or_literal(args.result_path, world),
        }
    )
    updated["lifecycle"] = lifecycle

    if args.dry_run:
        print(json.dumps(updated, ensure_ascii=False, indent=2))
        return 0
    if not args.confirmed:
        raise SystemExit("Refusing to update action request without --confirmed. Use --dry-run to preview.")

    request_json.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    request_md.write_text(render_markdown(updated), encoding="utf-8")
    if not args.skip_manifest:
        refresh_manifest(world)

    result = {
        "ok": True,
        "request_id": args.request_id,
        "from": old_status,
        "to": args.status,
        "request_json": str(request_json),
        "request_markdown": str(request_md),
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Updated action request: {args.request_id} {old_status} -> {args.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
