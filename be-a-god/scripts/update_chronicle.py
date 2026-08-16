#!/usr/bin/env python3
"""Rebuild the objective chronicle for the active branch from event nodes."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


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
    return data


def parse_field(text: str, field: str) -> str | None:
    match = re.search(rf"^\s*-\s*{re.escape(field)}:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def parse_summary(text: str) -> str:
    for heading in ("## Settlement summary", "## Summary", "## Consequences"):
        index = text.find(heading)
        if index >= 0:
            body = text[index + len(heading):].strip()
            lines = [line.strip() for line in body.splitlines() if line.strip() and not line.startswith("## ")]
            if lines:
                return lines[0]
    lines = [line.strip("# ").strip() for line in text.splitlines() if line.strip()]
    return lines[0] if lines else "未命名事件"


def event_sort_key(path: Path) -> tuple[int, str]:
    match = re.match(r"EVT-(\d+)", path.name)
    return (int(match.group(1)) if match else 999999, path.name)


def build_chronicle(world: Path) -> tuple[str, int]:
    active = parse_active(world)
    branch = world / active["branch_path"]
    events_dir = branch / "events"
    lines = ["# Objective Chronicle", ""]
    count = 0
    for event_path in sorted(events_dir.glob("EVT-*.md"), key=event_sort_key):
        text = event_path.read_text(encoding="utf-8")
        event_id = parse_field(text, "id") or event_path.stem.split("-")[0]
        time = parse_field(text, "time") or "unknown"
        summary = parse_summary(text)
        count += 1
        lines.append(f"- CHR-{count:04d} | {time} | {summary} | source: {event_path.relative_to(world).as_posix()} | event: {event_id}")
    lines.append("")
    return "\n".join(lines), count


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild objective chronicle from current branch events.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    world = resolve_world(args.world)
    active = parse_active(world)
    chronicle, count = build_chronicle(world)
    output = world / active["branch_path"] / "chronicle" / "objective.md"
    if args.dry_run:
        print(chronicle)
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(chronicle, encoding="utf-8")
    print(f"Rebuilt chronicle: {output} ({count} events)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
