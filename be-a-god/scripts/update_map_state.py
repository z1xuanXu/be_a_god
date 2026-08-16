#!/usr/bin/env python3
"""Update dashboard piece positions from entity locations and map coordinates."""

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
    return data


def parse_field(text: str, field: str) -> str | None:
    match = re.search(rf"^\s*-\s*{re.escape(field)}:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def load_coordinates(world: Path) -> dict:
    path = world / "base" / "maps" / "coordinates.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for place in data.get("places", []):
        key = place.get("id") or place.get("name")
        if key:
            out[str(key)] = place
    return out


def entity_piece(path: Path, world: Path, coords: dict) -> dict:
    text = path.read_text(encoding="utf-8")
    entity_id = parse_field(text, "id") or path.stem
    name = parse_field(text, "public_name") or parse_field(text, "name") or entity_id
    location = parse_field(text, "location")
    coord = coords.get(str(location), {}) if location else {}
    direct_x = parse_field(text, "x")
    direct_y = parse_field(text, "y")
    piece = {
        "id": entity_id,
        "kind": parse_field(text, "kind") or "character",
        "label": name,
        "location": location,
        "status": parse_field(text, "status") or parse_field(text, "attention") or "ordinary",
        "attention": parse_field(text, "attention") or "normal",
        "source": path.relative_to(world).as_posix(),
    }
    if direct_x is not None:
        try:
            piece["x"] = float(direct_x)
        except ValueError:
            piece["x"] = direct_x
    elif "x" in coord:
        piece["x"] = coord["x"]
    if direct_y is not None:
        try:
            piece["y"] = float(direct_y)
        except ValueError:
            piece["y"] = direct_y
    elif "y" in coord:
        piece["y"] = coord["y"]
    level = parse_field(text, "level")
    if level:
        piece["level"] = level
    elif "level" in coord:
        piece["level"] = coord["level"]
    return piece


def main() -> int:
    parser = argparse.ArgumentParser(description="Update dashboard character piece map state.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    active = parse_active(world)
    branch = world / active["branch_path"]
    coords = load_coordinates(world)
    pieces = [entity_piece(path, world, coords) for path in sorted((branch / "state" / "entities").glob("*.md"))]
    dashboard_path = world / "dashboard" / "data.json"
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8")) if dashboard_path.exists() else {"schema": "be-a-god.dashboard.v1"}
    dashboard["pieces"] = pieces
    if args.dry_run:
        print(json.dumps(dashboard, ensure_ascii=False, indent=2))
        return 0
    dashboard_path.parent.mkdir(parents=True, exist_ok=True)
    dashboard_path.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated map state: {len(pieces)} pieces")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
