#!/usr/bin/env python3
"""Mark a pending action request as cancelled without deleting its files."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_id(value: str, label: str) -> str:
    if not value or not SAFE_ID_PATTERN.fullmatch(value):
        raise SystemExit(f"{label} must contain only letters, numbers, underscore, or hyphen: {value!r}")
    return value


def resolve_world(raw: str) -> Path:
    world = Path(raw).resolve()
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    return world


def parse_active(world: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in (world / "ACTIVE.md").read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    data.setdefault("branch_path", "story/main")
    data.setdefault("branch_id", "main")
    return data


def write_request_markdown(request: dict[str, Any], path: Path) -> None:
    target = request.get("target") or {}
    lines = [
        f"# Action Request {request.get('request_id')}",
        "",
        f"- schema: {request.get('schema', '')}",
        f"- status: {request.get('status', '')}",
        f"- action: {request.get('action', '')}",
        f"- target_id: {target.get('id') or ''}",
        f"- target_kind: {target.get('kind') or ''}",
        f"- intent: {request.get('intent') or ''}",
        f"- created_at: {request.get('created_at') or ''}",
        f"- updated_at: {request.get('updated_at') or ''}",
        f"- cancelled_at: {request.get('cancelled_at') or ''}",
        "",
        "## Suggested command",
        "",
        "```text",
        str(request.get("suggested_command") or ""),
        "```",
        "",
        "## Payload",
        "",
        "```json",
        json.dumps(request.get("payload") or {}, ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Cancel a pending be-a-god action request without deleting audit files.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--reason", default="cancelled by player")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.confirmed:
        raise SystemExit("Refusing to cancel action request without --confirmed.")

    world = resolve_world(args.world)
    request_id = validate_id(args.request_id, "--request-id")
    active = parse_active(world)
    branch = world / active["branch_path"]
    request_dir = branch / "runtime" / "action-requests" / request_id
    request_json = request_dir / "request.json"
    request_md = request_dir / "request.md"
    if not request_json.exists():
        raise SystemExit(f"Action request not found: {request_id}")

    request = json.loads(request_json.read_text(encoding="utf-8"))
    status = request.get("status")
    if status in {"executed", "done", "completed"}:
        raise SystemExit(f"Cannot cancel already executed action request: {request_id}")
    now = utc_now()
    request["status"] = "cancelled"
    request["updated_at"] = now
    request["cancelled_at"] = now
    request["cancel_reason"] = args.reason
    request_json.write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_request_markdown(request, request_md)

    result = {
        "ok": True,
        "request_id": request_id,
        "status": "cancelled",
        "request_json": str(request_json),
        "request_markdown": str(request_md),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"Cancelled action request: {request_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
