#!/usr/bin/env python3
"""Build lightweight entity and event indexes for the active branch."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from build_event_graph import build_graph


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


def entity_index(world: Path, branch: Path) -> list[dict]:
    items = []
    for path in sorted((branch / "state" / "entities").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        entity_id = parse_field(text, "id") or path.stem
        items.append(
            {
                "id": entity_id,
                "name": parse_field(text, "public_name") or parse_field(text, "name") or entity_id,
                "kind": parse_field(text, "kind") or "character",
                "location": parse_field(text, "location"),
                "status": parse_field(text, "status") or "ordinary",
                "source": path.relative_to(world).as_posix(),
            }
        )
    return items


def location_index(world: Path, branch: Path) -> list[dict]:
    items = []
    for path in sorted((branch / "state" / "locations").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        location_id = parse_field(text, "id") or path.stem
        item = {
            "id": location_id,
            "name": parse_field(text, "public_name") or parse_field(text, "name") or location_id,
            "kind": parse_field(text, "kind") or "location",
            "level": parse_field(text, "level"),
            "parent": parse_field(text, "location"),
            "status": parse_field(text, "status") or "ordinary",
            "source": path.relative_to(world).as_posix(),
        }
        for field in ["x", "y"]:
            value = parse_field(text, field)
            if value is None:
                continue
            try:
                item[field] = float(value)
            except ValueError:
                item[field] = value
        items.append(item)
    return items


def event_index(world: Path, branch: Path) -> list[dict]:
    items = []
    for path in sorted((branch / "events").glob("EVT-*.md")):
        text = path.read_text(encoding="utf-8")
        event_id = parse_field(text, "id") or path.stem
        items.append(
            {
                "id": event_id,
                "title": parse_title(text, event_id),
                "type": parse_field(text, "type"),
                "time": parse_field(text, "time"),
                "target_id": parse_field(text, "target_id"),
                "source": path.relative_to(world).as_posix(),
            }
        )
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description="Build active branch indexes.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    active = parse_active(world)
    branch = world / active["branch_path"]
    indexes = {
        "entities": {"schema": "be-a-god.entity-index.v1", "world_id": active.get("world_id", world.name), "branch_id": active.get("branch_id", "main"), "entities": entity_index(world, branch)},
        "locations": {"schema": "be-a-god.location-index.v1", "world_id": active.get("world_id", world.name), "branch_id": active.get("branch_id", "main"), "locations": location_index(world, branch)},
        "events": {"schema": "be-a-god.event-index.v1", "world_id": active.get("world_id", world.name), "branch_id": active.get("branch_id", "main"), "events": event_index(world, branch)},
        "event_graph": build_graph(world),
    }
    if args.dry_run:
        print(json.dumps(indexes, ensure_ascii=False, indent=2))
        return 0
    out_dir = world / "indexes"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "entities.json").write_text(json.dumps(indexes["entities"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "locations.json").write_text(json.dumps(indexes["locations"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "events.json").write_text(json.dumps(indexes["events"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "event-graph.json").write_text(json.dumps(indexes["event_graph"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built indexes: {len(indexes['entities']['entities'])} entities, {len(indexes['locations']['locations'])} locations, {len(indexes['events']['events'])} events, {len(indexes['event_graph']['links'])} event links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
