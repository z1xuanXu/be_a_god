#!/usr/bin/env python3
"""Build dashboard/timeline.json from current branch events."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def resolve_world(path: str) -> Path:
    world = Path(path).resolve()
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    return world


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


def parse_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line.lstrip("# ").strip()
    return fallback


def parse_list(value: str | None) -> list[str]:
    if not value:
        return []
    raw = value.strip()
    if raw in {"[]", "none", "None", "null"}:
        return []
    if raw.startswith("[") and raw.endswith("]"):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            raw = raw[1:-1]
    return [item.strip().strip("'\"") for item in raw.split(",") if item.strip().strip("'\"")]


def event_involves_target(text: str, target_id: str) -> bool:
    actors = parse_list(parse_field(text, "actors"))
    if target_id in actors:
        return True
    return parse_field(text, "target_id") == target_id


def parse_save_time(branch: Path) -> str:
    save = branch / "SAVE.md"
    text = save.read_text(encoding="utf-8") if save.exists() else ""
    return parse_field(text, "world_time") or "unknown"


def event_sort_key(path: Path) -> tuple[int, str]:
    match = re.match(r"EVT-(\d+)", path.name)
    return (int(match.group(1)) if match else 999999, path.name)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def queue_entries(branch: Path) -> list[dict[str, Any]]:
    path = branch / "queues" / "events.jsonl"
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("status") in {"queued", "due"}:
            entries.append(item)
    return entries


def child_branch_nodes(branch: Path, world: Path) -> list[dict[str, Any]]:
    nodes = []
    branches_root = branch / "branches"
    if not branches_root.exists():
        return nodes
    for save_path in sorted(branches_root.glob("*/SAVE.md")):
        text = save_path.read_text(encoding="utf-8")
        branch_id = parse_field(text, "branch_id") or save_path.parent.name
        fork_event = parse_field(text, "fork_event") or ""
        world_time = parse_field(text, "world_time") or "unknown"
        current_scene = parse_field(text, "current_scene") or f"Branch {branch_id}"
        nodes.append(
            {
                "id": f"BR-{branch_id}",
                "event_id": fork_event,
                "time": world_time,
                "label": f"分支：{branch_id}",
                "summary": current_scene,
                "state": "branch",
                "source": save_path.relative_to(world).as_posix(),
                "branch_path": save_path.parent.relative_to(world).as_posix(),
            }
        )
    return nodes


def locked_rule_nodes(world: Path, current_time: str) -> list[dict[str, Any]]:
    data = read_json(world / "setup" / "world-rules.json")
    nodes = []
    for rule in data.get("rules", []):
        if not isinstance(rule, dict) or rule.get("status") != "active":
            continue
        rule_id = rule.get("rule_id") or "RULE"
        effective = rule.get("effective_time") or current_time
        nodes.append(
            {
                "id": f"LOCK-{rule_id}",
                "event_id": rule_id,
                "time": current_time if effective == "immediate" else effective,
                "label": f"锁定规则：{rule_id}",
                "summary": rule.get("text"),
                "state": "locked",
                "source": "setup/world-rules.json",
                "scope": rule.get("scope"),
                "target": rule.get("target"),
            }
        )
    return nodes


def queued_nodes(branch: Path, world: Path) -> list[dict[str, Any]]:
    nodes = []
    for entry in queue_entries(branch):
        queue_id = entry.get("queue_id") or "QUEUE"
        nodes.append(
            {
                "id": f"Q-{queue_id}",
                "event_id": queue_id,
                "time": entry.get("trigger_time") or "unknown",
                "label": f"预定：{entry.get('title') or queue_id}",
                "summary": entry.get("summary"),
                "state": "due" if entry.get("status") == "due" else "queued",
                "source": (branch / "queues" / "events.jsonl").relative_to(world).as_posix(),
                "queue_id": queue_id,
                "priority": entry.get("priority"),
                "pause": entry.get("pause"),
            }
        )
    return nodes


def ignored_attention(branch: Path) -> list[str]:
    data = read_json(branch / "state" / "attention.json")
    entities = data.get("entities", {})
    if not isinstance(entities, dict):
        return []
    return sorted(str(entity_id) for entity_id, item in entities.items() if isinstance(item, dict) and item.get("state") == "ignored")


def ignored_digest_nodes(branch: Path, world: Path) -> list[dict[str, Any]]:
    nodes = []
    for target_id in ignored_attention(branch):
        events = []
        for event_path in sorted((branch / "events").glob("EVT-*.md"), key=event_sort_key):
            text = event_path.read_text(encoding="utf-8")
            if not event_involves_target(text, target_id):
                continue
            events.append(
                {
                    "event_id": parse_field(text, "id") or event_path.stem,
                    "time": parse_field(text, "time") or "unknown",
                    "source": event_path.relative_to(world).as_posix(),
                }
            )
        if not events:
            continue
        latest = events[-1]
        nodes.append(
            {
                "id": f"IGNORED-{target_id}",
                "event_id": target_id,
                "time": latest["time"],
                "label": f"被忽略动态：{target_id}",
                "summary": f"{target_id} has {len(events)} collapsed related event(s). Use build_ignored_digest.py to inspect on demand.",
                "state": "ignored",
                "source": latest["source"],
                "target_id": target_id,
                "collapsed_event_count": len(events),
            }
        )
    return nodes


def build_timeline(world: Path) -> dict:
    active = parse_active(world)
    branch = world / active["branch_path"]
    current_time = parse_save_time(branch)
    nodes = []
    for idx, event_path in enumerate(sorted((branch / "events").glob("EVT-*.md"), key=event_sort_key), start=1):
        text = event_path.read_text(encoding="utf-8")
        event_id = parse_field(text, "id") or event_path.stem
        nodes.append(
            {
                "id": f"CHR-{idx:04d}",
                "event_id": event_id,
                "time": parse_field(text, "time") or "unknown",
                "label": parse_title(text, event_id),
                "state": "confirmed",
                "source": event_path.relative_to(world).as_posix(),
            }
        )
    nodes.extend(locked_rule_nodes(world, current_time))
    nodes.extend(queued_nodes(branch, world))
    nodes.extend(ignored_digest_nodes(branch, world))
    nodes.extend(child_branch_nodes(branch, world))
    return {
        "schema": "be-a-god.timeline.v1",
        "world_id": active.get("world_id", world.name),
        "branch_id": active.get("branch_id", "main"),
        "nodes": nodes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build timeline JSON from current branch events.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    world = resolve_world(args.world)
    timeline = build_timeline(world)
    if args.dry_run:
        print(json.dumps(timeline, ensure_ascii=False, indent=2))
        return 0
    output = world / "dashboard" / "timeline.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built timeline: {output} ({len(timeline['nodes'])} nodes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
