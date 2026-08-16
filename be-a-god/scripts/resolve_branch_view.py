#!/usr/bin/env python3
"""Resolve the active branch and its parent chain without scanning siblings."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def parse_active(world: Path) -> dict[str, str]:
    data = {}
    for line in (world / "ACTIVE.md").read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    data.setdefault("branch_path", "story/main")
    data.setdefault("branch_id", "main")
    return data


def parse_field(text: str, field: str) -> str | None:
    match = re.search(rf"^\s*-\s*{re.escape(field)}:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def branch_record(world: Path, branch_path: str) -> dict:
    branch = world / branch_path
    save = branch / "SAVE.md"
    if not save.exists():
        raise SystemExit(f"SAVE.md not found for branch: {branch_path}")
    text = save.read_text(encoding="utf-8")
    return {
        "branch_id": parse_field(text, "branch_id") or branch.name,
        "branch_path": branch_path,
        "parent_branch_id": parse_field(text, "parent_branch_id"),
        "parent_save": parse_field(text, "parent_save"),
        "fork_event": parse_field(text, "fork_event"),
        "inherit_until": parse_field(text, "inherit_until"),
        "world_time": parse_field(text, "world_time"),
        "focal_place": parse_field(text, "focal_place"),
        "latest_event": parse_field(text, "latest_event"),
        "save": f"{branch_path}/SAVE.md",
    }


def parent_branch_path(record: dict) -> str | None:
    parent_save = record.get("parent_save")
    if not parent_save or parent_save in {"none", "None", "null"}:
        return None
    suffix = "/SAVE.md"
    if parent_save.endswith(suffix):
        return parent_save[:-len(suffix)]
    return None


def resolve(world: Path, max_depth: int) -> dict:
    active = parse_active(world)
    chain = []
    seen = set()
    branch_path = active["branch_path"]
    for _ in range(max_depth):
        if branch_path in seen:
            raise SystemExit(f"Branch parent cycle detected at: {branch_path}")
        seen.add(branch_path)
        record = branch_record(world, branch_path)
        chain.append(record)
        parent = parent_branch_path(record)
        if not parent:
            break
        branch_path = parent
    return {
        "schema": "be-a-god.branch-view.v1",
        "world_id": active.get("world_id", world.name),
        "active_branch_id": active.get("branch_id"),
        "active_branch_path": active.get("branch_path"),
        "chain": chain,
        "read_policy": "current branch plus parent pointers only; sibling branches not scanned",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve active branch inheritance view.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--max-depth", type=int, default=8)
    parser.add_argument("--output")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    view = resolve(world, args.max_depth)
    text = json.dumps(view, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = Path(args.output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        print(f"Wrote branch view: {output}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
