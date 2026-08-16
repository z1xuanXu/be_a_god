#!/usr/bin/env python3
"""Build lightweight semantic map layers for the frontend."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def parse_active(world: Path) -> dict[str, str]:
    active_path = world / "ACTIVE.md"
    if not active_path.exists():
        return {"branch_path": "story/main"}
    data: dict[str, str] = {}
    for line in active_path.read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    data.setdefault("branch_path", "story/main")
    return data


def parse_field(text: str, field: str) -> str | None:
    match = re.search(rf"^\s*-\s*{re.escape(field)}:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def location_sources(world: Path, branch_path: str) -> dict[str, str]:
    sources: dict[str, str] = {}
    root = world / branch_path / "state" / "locations"
    if not root.exists():
        return sources
    for path in sorted(root.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        location_id = parse_field(text, "id") or path.stem.split("-", 1)[0]
        sources[location_id] = path.relative_to(world).as_posix()
    return sources


def collect_brushes_from(path: Path, source: str) -> list[dict]:
    data = load_json(path, {"brushes": []})
    brushes: list[dict] = []
    for brush in data.get("brushes", []):
        if not isinstance(brush, dict) or not brush.get("id"):
            continue
        merged = dict(brush)
        merged.setdefault("level", "region")
        merged.setdefault("density", 12)
        merged.setdefault("jitter", 2)
        merged.setdefault("width", 5)
        merged["source"] = source
        brushes.append(merged)
    return brushes


def normalize_brushes(world: Path, branch_path: str) -> list[dict]:
    merged_by_id: dict[str, dict] = {}
    for brush in collect_brushes_from(world / "base" / "maps" / "terrain-brushes.json", "base/maps/terrain-brushes.json"):
        merged_by_id[brush["id"]] = brush
    branch_source = f"{branch_path}/state/terrain-brushes.json"
    branch_path_file = world / branch_source
    if branch_path_file.exists():
        for brush in collect_brushes_from(branch_path_file, branch_source):
            if brush.get("removed") is True:
                merged_by_id.pop(brush["id"], None)
            else:
                merged_by_id[brush["id"]] = brush
    return list(merged_by_id.values())


def main() -> int:
    parser = argparse.ArgumentParser(description="Build map layer export from base map files.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    active = parse_active(world)
    hierarchy = load_json(world / "base" / "maps" / "hierarchy.json", {"levels": ["world", "region", "scene"], "nodes": []})
    coordinates = load_json(world / "base" / "maps" / "coordinates.json", {"places": []})
    brushes = normalize_brushes(world, active.get("branch_path", "story/main"))
    by_id = {place.get("id"): place for place in coordinates.get("places", []) if place.get("id")}
    sources = location_sources(world, active.get("branch_path", "story/main"))
    nodes = []
    for node in hierarchy.get("nodes", []):
        merged = dict(node)
        if node.get("id") in by_id:
            merged.update(by_id[node["id"]])
        if merged.get("id") in sources:
            merged["source"] = sources[merged["id"]]
        nodes.append(merged)
    places = []
    for place in coordinates.get("places", []):
        merged = dict(place)
        if merged.get("id") in sources:
            merged["source"] = sources[merged["id"]]
        places.append(merged)
    layers = {
        "schema": "be-a-god.map-layers.v1",
        "world_id": active.get("world_id", world.name),
        "levels": hierarchy.get("levels", ["world", "region", "scene"]),
        "nodes": nodes,
        "places": places,
        "brushes": brushes,
        "read_policy": "frontend map layers only; story text not included",
    }
    if args.dry_run:
        print(json.dumps(layers, ensure_ascii=False, indent=2))
        return 0
    output = world / "dashboard" / "map-layers.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(layers, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built map layers: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
