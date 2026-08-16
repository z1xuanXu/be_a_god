#!/usr/bin/env python3
"""Estimate whether a world should create a context handoff before continuing."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DEFAULT_SOFT_CHARS = 60_000
DEFAULT_HARD_CHARS = 120_000
DEFAULT_SOFT_EVENTS = 40
DEFAULT_HARD_EVENTS = 80


def resolve_world(path: str) -> Path:
    world = Path(path).resolve()
    if not world.exists() or not world.is_dir():
        raise SystemExit(f"world directory not found: {world}")
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
    data.setdefault("save_path", f"{data['branch_path']}/SAVE.md")
    return data


def char_count(path: Path) -> int:
    if not path.exists() or not path.is_file():
        return 0
    return len(path.read_text(encoding="utf-8", errors="replace"))


def count_lines(path: Path, prefix: str | None = None) -> int:
    if not path.exists():
        return 0
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if prefix is None:
        return sum(1 for line in lines if line.strip())
    return sum(1 for line in lines if line.strip().startswith(prefix))


def total_chars(paths: list[Path]) -> int:
    return sum(char_count(path) for path in paths)


def latest_handoff(branch: Path, world: Path) -> dict | None:
    root = branch / "runtime" / "context-handoffs"
    if not root.exists():
        return None
    candidates = sorted(root.glob("*/handoff.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        return None
    path = candidates[0]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {}
    return {
        "path": path.relative_to(world).as_posix(),
        "handoff_id": data.get("handoff_id", path.parent.name),
        "created_at": data.get("created_at"),
    }


def event_sort_key(path: Path) -> tuple[int, str]:
    match = re.search(r"EVT-(\d+)", path.name)
    return (int(match.group(1)) if match else 999999, path.name)


def estimate(world: Path, soft_chars: int, hard_chars: int, soft_events: int, hard_events: int) -> dict:
    active = parse_active(world)
    branch = world / active["branch_path"]
    if not branch.exists():
        raise SystemExit(f"active branch path not found: {branch}")

    minimum_files = [
        world / "ACTIVE.md",
        world / active["save_path"],
        world / "PLAYER.md",
        branch / "CURRENT.md",
        world / "dashboard" / "data.json",
        world / "dashboard" / "timeline.json",
    ]
    core_history_files = [
        *sorted((branch / "events").glob("EVT-*.md"), key=event_sort_key),
        *sorted((branch / "state" / "entities").glob("*.md")),
        *sorted((branch / "state" / "locations").glob("*.md")),
        branch / "chronicle" / "objective.md",
    ]
    minimum_chars = total_chars(minimum_files)
    core_history_chars = total_chars(core_history_files)
    event_count = len(list((branch / "events").glob("EVT-*.md")))
    chronicle_entries = count_lines(branch / "chronicle" / "objective.md", "- ")
    random_entries = count_lines(branch / "random" / "random-log.jsonl")
    handoff = latest_handoff(branch, world)

    score_reasons = []
    if minimum_chars >= hard_chars:
        score_reasons.append(f"minimum context chars {minimum_chars} >= hard threshold {hard_chars}")
    elif minimum_chars >= soft_chars:
        score_reasons.append(f"minimum context chars {minimum_chars} >= soft threshold {soft_chars}")
    if event_count >= hard_events:
        score_reasons.append(f"event count {event_count} >= hard threshold {hard_events}")
    elif event_count >= soft_events:
        score_reasons.append(f"event count {event_count} >= soft threshold {soft_events}")
    if handoff is None and (event_count > 0 or minimum_chars > 0):
        score_reasons.append("no handoff exists for current branch")

    if minimum_chars >= hard_chars or event_count >= hard_events:
        status = "urgent-handoff"
    elif minimum_chars >= soft_chars or event_count >= soft_events or handoff is None:
        status = "suggest-handoff"
    else:
        status = "keep-going"

    return {
        "schema": "be-a-god.context-pressure.v1",
        "world": str(world),
        "branch_id": active.get("branch_id", "main"),
        "branch_path": active["branch_path"],
        "status": status,
        "reasons": score_reasons,
        "metrics": {
            "minimum_context_chars": minimum_chars,
            "core_history_chars": core_history_chars,
            "event_count": event_count,
            "chronicle_entries": chronicle_entries,
            "random_log_entries": random_entries,
            "soft_chars": soft_chars,
            "hard_chars": hard_chars,
            "soft_events": soft_events,
            "hard_events": hard_events,
        },
        "latest_handoff": handoff,
        "recommended_action": "run create_handoff.py --world <world> --confirmed" if status != "keep-going" else "continue with minimum context",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Estimate be-a-god context pressure and handoff need.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--soft-chars", type=int, default=DEFAULT_SOFT_CHARS)
    parser.add_argument("--hard-chars", type=int, default=DEFAULT_HARD_CHARS)
    parser.add_argument("--soft-events", type=int, default=DEFAULT_SOFT_EVENTS)
    parser.add_argument("--hard-events", type=int, default=DEFAULT_HARD_EVENTS)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = estimate(resolve_world(args.world), args.soft_chars, args.hard_chars, args.soft_events, args.hard_events)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Context pressure: {result['status']}")
        for key, value in result["metrics"].items():
            print(f"{key}: {value}")
        for reason in result["reasons"]:
            print(f"reason: {reason}")
        print(f"recommended_action: {result['recommended_action']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
