#!/usr/bin/env python3
"""Persist player-defined display priority for pending action requests."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


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


def parse_request_ids(args: argparse.Namespace) -> list[str]:
    if args.request_ids_json:
        raw = json.loads(args.request_ids_json)
        if not isinstance(raw, list):
            raise SystemExit("--request-ids-json must be a JSON array")
        ids = [str(item) for item in raw]
    else:
        ids = list(args.request_id or [])
    if not ids:
        raise SystemExit("At least one request id is required")
    seen: set[str] = set()
    clean: list[str] = []
    for item in ids:
        request_id = validate_id(item, "request id")
        if request_id in seen:
            continue
        seen.add(request_id)
        clean.append(request_id)
    return clean


def main() -> int:
    parser = argparse.ArgumentParser(description="Persist player-defined action request display priority.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--request-id", action="append", help="Request ID in desired priority order. Repeatable.")
    parser.add_argument("--request-ids-json", help="JSON array of request IDs in desired priority order.")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.confirmed:
        raise SystemExit("Refusing to reorder action requests without --confirmed.")

    world = resolve_world(args.world)
    request_ids = parse_request_ids(args)
    active = parse_active(world)
    branch = world / active["branch_path"]
    root = branch / "runtime" / "action-requests"
    missing = [request_id for request_id in request_ids if not (root / request_id / "request.json").exists()]
    if missing:
        raise SystemExit(f"Action request IDs not found: {', '.join(missing)}")

    order_path = root / "priority-order.json"
    payload = {
        "schema": "be-a-god.action-request-priority.v1",
        "updated_at": utc_now(),
        "branch_id": active.get("branch_id", "main"),
        "request_ids": request_ids,
    }
    order_path.parent.mkdir(parents=True, exist_ok=True)
    order_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = {
        "ok": True,
        "order_path": str(order_path),
        "request_ids": request_ids,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"Saved action request order: {order_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
