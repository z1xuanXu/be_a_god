#!/usr/bin/env python3
"""List branch-local action requests without reading story history."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


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


def summarize_request(path: Path, world: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    target = data.get("target") or {}
    return {
        "request_id": data.get("request_id") or path.parent.name,
        "status": data.get("status", "unknown"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "action": data.get("action"),
        "target_id": target.get("id"),
        "target_kind": target.get("kind"),
        "intent": data.get("intent"),
        "suggested_command": data.get("suggested_command"),
        "source": path.relative_to(world).as_posix(),
    }


def list_requests(world: Path, status_filter: set[str] | None, limit: int) -> dict[str, Any]:
    active = parse_active(world)
    root = world / active["branch_path"] / "runtime" / "action-requests"
    items: list[dict[str, Any]] = []
    if root.exists():
        for path in sorted(root.glob("*/request.json")):
            item = summarize_request(path, world)
            if not item:
                continue
            if status_filter and item["status"] not in status_filter:
                continue
            items.append(item)
    items.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)
    if limit > 0:
        items = items[:limit]
    return {
        "schema": "be-a-god.action-request-list.v1",
        "world_id": active.get("world_id", world.name),
        "branch_id": active.get("branch_id", "main"),
        "branch_path": active["branch_path"],
        "count": len(items),
        "requests": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="List action requests in the active branch.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--status", action="append", choices=["requested", "accepted", "executed", "cancelled"], help="Filter by status. Can be repeated.")
    parser.add_argument("--pending", action="store_true", help="Shortcut for requested and accepted requests.")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    world = resolve_world(args.world)
    statuses = set(args.status or [])
    if args.pending:
        statuses.update({"requested", "accepted"})
    result = list_requests(world, statuses or None, args.limit)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for item in result["requests"]:
            print(f"{item['request_id']} [{item['status']}] {item.get('action')} -> {item.get('target_id') or 'WORLD'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
