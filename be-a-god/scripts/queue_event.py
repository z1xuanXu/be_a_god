#!/usr/bin/env python3
"""Queue a future event or pause trigger for the active branch."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


DAYS_PER_YEAR = 360


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def parse_world_time(value: str | None) -> tuple[int, int]:
    if not value:
        return 1, 1
    match = re.search(r"year\s+(\d+),\s*day\s+(\d+)", value, re.IGNORECASE)
    if not match:
        raise SystemExit(f"unsupported world time format: {value}")
    return int(match.group(1)), int(match.group(2))


def add_days(year: int, day: int, days: int) -> tuple[int, int]:
    absolute = (year - 1) * DAYS_PER_YEAR + (day - 1) + days
    return absolute // DAYS_PER_YEAR + 1, absolute % DAYS_PER_YEAR + 1


def format_time(year: int, day: int) -> str:
    return f"year {year}, day {day}"


def next_queue_id(queue_path: Path) -> str:
    highest = 0
    if queue_path.exists():
        for line in queue_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            match = re.search(r"QUEUE-(\d+)", str(item.get("queue_id", "")))
            if match:
                highest = max(highest, int(match.group(1)))
    return f"QUEUE-{highest + 1:04d}"


def update_manifest(world: Path) -> None:
    script = Path(__file__).resolve().parent / "build_file_manifest.py"
    subprocess.run([sys.executable, str(script), str(world)], check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE)


def build_entry(args: argparse.Namespace, world: Path, branch: Path, active: dict[str, str]) -> dict:
    save = (branch / "SAVE.md").read_text(encoding="utf-8")
    current_year, current_day = parse_world_time(parse_field(save, "world_time"))
    if args.trigger_time:
        trigger_time = args.trigger_time
    else:
        if args.in_days is None:
            raise SystemExit("provide either --trigger-time or --in-days")
        trigger_time = format_time(*add_days(current_year, current_day, args.in_days))

    queue_path = branch / "queues" / "events.jsonl"
    return {
        "schema": "be-a-god.event-queue.v1",
        "queue_id": args.queue_id or next_queue_id(queue_path),
        "created_at": utc_now(),
        "world_id": active.get("world_id", world.name),
        "branch_id": active.get("branch_id", "main"),
        "status": "queued",
        "trigger_time": trigger_time,
        "priority": args.priority,
        "kind": args.kind,
        "title": args.title,
        "summary": args.summary,
        "targets": args.target,
        "pause": args.pause or args.priority in {"high", "critical"},
        "source": args.source,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Queue a future be-a-god branch event.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--queue-id")
    parser.add_argument("--title", required=True)
    parser.add_argument("--summary", default="")
    parser.add_argument("--kind", default="event")
    parser.add_argument("--priority", choices=["low", "normal", "high", "critical"], default="normal")
    parser.add_argument("--trigger-time", help="World time like `year 1, day 30`.")
    parser.add_argument("--in-days", type=int, help="Schedule relative to current SAVE world_time.")
    parser.add_argument("--target", action="append", default=[])
    parser.add_argument("--source", default="")
    parser.add_argument("--pause", action="store_true", help="Force advance_world.py to pause when this event becomes due.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--skip-manifest", action="store_true")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    active = parse_active(world)
    branch = world / active["branch_path"]
    entry = build_entry(args, world, branch, active)
    if args.dry_run:
        print(json.dumps(entry, ensure_ascii=False, indent=2))
        return 0
    if not args.confirmed:
        raise SystemExit("refusing to write event queue without --confirmed")

    queue_path = branch / "queues" / "events.jsonl"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with queue_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    if not args.skip_manifest:
        update_manifest(world)
    print(json.dumps(entry, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
