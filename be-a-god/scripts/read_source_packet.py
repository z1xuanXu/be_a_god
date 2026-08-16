#!/usr/bin/env python3
"""Read a bounded packet from explicit source pointers only."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


TEXT_EXTENSIONS = {".md", ".txt", ".json", ".jsonl", ".yaml", ".yml"}
ROOT_ALLOWED = {"ACTIVE.md", "CANON.md", "PLAYER.md", "WORLD.md"}
ROOT_ALLOWED_DIRS = {"setup", "base", "indexes", "dashboard", "system"}


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


def relative_inside(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise SystemExit(f"Path is outside world directory: {path}") from exc


def branch_scopes(world: Path, active: dict[str, str]) -> list[dict[str, str | None]]:
    scopes: list[dict[str, str | None]] = []
    branch_path = active["branch_path"]
    seen = set()
    event_limit: str | None = None
    while branch_path and branch_path not in seen:
        seen.add(branch_path)
        scopes.append({"path": branch_path, "event_limit": event_limit})
        save = world / branch_path / "SAVE.md"
        if not save.exists():
            break
        save_text = save.read_text(encoding="utf-8")
        parent_save = parse_field(save_text, "parent_save")
        if not parent_save or parent_save in {"none", "None", "null"}:
            break
        event_limit = parse_field(save_text, "fork_event")
        parent = Path(parent_save).parent.as_posix()
        if not parent or parent == ".":
            break
        branch_path = parent
    return scopes


def branch_ancestry(world: Path, active: dict[str, str]) -> list[str]:
    return [str(scope["path"]) for scope in branch_scopes(world, active)]


def event_is_within_limit(path: Path, limit: str | None) -> bool:
    if not limit or limit in {"none", "None", "null"}:
        return True
    text = path.read_text(encoding="utf-8")
    event_id = parse_field(text, "id") or path.stem
    if event_id == limit:
        return True
    match_event = re.search(r"(\d+)$", event_id)
    match_limit = re.search(r"(\d+)$", limit)
    return bool(match_event and match_limit and int(match_event.group(1)) <= int(match_limit.group(1)))


def strip_fragment(pointer: str) -> tuple[str, str]:
    if "#" not in pointer:
        return pointer, ""
    path, fragment = pointer.split("#", 1)
    return path, fragment


def load_sources_from_packet(world: Path, packet_pointer: str) -> list[str]:
    rel, _fragment = strip_fragment(packet_pointer)
    packet_path = (world / rel).resolve()
    relative_inside(packet_path, world)
    if not packet_path.exists():
        raise SystemExit(f"Interaction packet not found: {packet_path}")
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    sources = []
    for item in packet.get("context_policy", {}).get("allowed_sources", []):
        if isinstance(item, dict) and item.get("path"):
            sources.append(str(item["path"]))
    return sources


def is_allowed_source(rel: str, branch_paths: list[str]) -> bool:
    rel_path = Path(rel)
    parts = rel_path.parts
    if not parts:
        return False
    if rel in ROOT_ALLOWED:
        return True
    if parts[0] in ROOT_ALLOWED_DIRS:
        return True
    if parts[0] != "story":
        return False
    normalized = rel_path.as_posix()
    return any(normalized == branch or normalized.startswith(branch.rstrip("/") + "/") for branch in branch_paths)


def read_excerpt(path: Path, max_chars: int) -> tuple[str, bool]:
    text = path.read_text(encoding="utf-8")
    truncated = len(text) > max_chars
    return (text[:max_chars] if truncated else text), truncated


def build_packet(world: Path, sources: list[str], max_chars: int, total_budget: int) -> dict[str, Any]:
    active = parse_active(world)
    scopes = branch_scopes(world, active)
    branches = [str(scope["path"]) for scope in scopes]
    limits = {str(scope["path"]): scope.get("event_limit") for scope in scopes}
    seen = set()
    items = []
    used_chars = 0
    for raw_pointer in sources:
        if not raw_pointer:
            continue
        rel, fragment = strip_fragment(raw_pointer.strip())
        rel = rel.replace("\\", "/").lstrip("/")
        if rel in seen:
            continue
        seen.add(rel)
        allowed = is_allowed_source(rel, branches)
        item: dict[str, Any] = {
            "pointer": raw_pointer,
            "path": rel,
            "fragment": fragment,
            "allowed": allowed,
            "exists": False,
            "chars": 0,
            "truncated": False,
            "text": "",
        }
        if not allowed:
            item["error"] = "source is outside root allowlist or active branch ancestry"
            items.append(item)
            continue
        path = (world / rel).resolve()
        relative_inside(path, world)
        if not path.exists() or not path.is_file():
            item["error"] = "source file missing"
            items.append(item)
            continue
        matched_branch = next((branch for branch in branches if rel == branch or rel.startswith(branch.rstrip("/") + "/")), None)
        if matched_branch and "/events/" in f"/{rel}" and not event_is_within_limit(path, limits.get(matched_branch)):
            item["allowed"] = False
            item["error"] = "event is after the active branch fork point"
            items.append(item)
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            item["error"] = "unsupported source file type"
            item["exists"] = True
            items.append(item)
            continue
        remaining = max(0, total_budget - used_chars)
        if remaining <= 0:
            item["error"] = "total source budget exhausted"
            item["exists"] = True
            items.append(item)
            continue
        text, truncated = read_excerpt(path, min(max_chars, remaining))
        item.update({"exists": True, "chars": len(text), "truncated": truncated, "text": text})
        used_chars += len(text)
        items.append(item)
    return {
        "schema": "be-a-god.source-packet.v1",
        "world_id": active.get("world_id", world.name),
        "branch_id": active.get("branch_id", "main"),
        "branch_path": active["branch_path"],
        "allowed_branch_ancestry": branches,
        "source_count": len(items),
        "used_chars": used_chars,
        "max_chars_per_source": max_chars,
        "total_budget": total_budget,
        "sources": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read exact source pointers with branch and token-budget guardrails.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--source", action="append", default=[], help="Relative source pointer. Can include #fragment.")
    parser.add_argument("--from-packet", help="Read context_policy.allowed_sources from an interaction packet path.")
    parser.add_argument("--max-chars", type=int, default=1600)
    parser.add_argument("--total-budget", type=int, default=5000)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.max_chars <= 0 or args.total_budget <= 0:
        raise SystemExit("budgets must be positive")
    world = resolve_world(args.world)
    sources = list(args.source)
    if args.from_packet:
        sources.extend(load_sources_from_packet(world, args.from_packet))
    if not sources:
        raise SystemExit("provide --source or --from-packet")
    packet = build_packet(world, sources, args.max_chars, args.total_budget)
    if args.json:
        print(json.dumps(packet, ensure_ascii=False, indent=2))
    else:
        for item in packet["sources"]:
            status = "ok" if item.get("exists") and item.get("allowed") else item.get("error", "blocked")
            print(f"{item['path']} [{status}] {item.get('chars', 0)} chars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
