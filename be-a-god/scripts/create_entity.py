#!/usr/bin/env python3
"""Create a branch-local entity/location card and refresh lightweight indexes."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPTS = Path(__file__).resolve().parent
ID_PREFIX = {
    "character": "CHAR",
    "location": "LOC",
    "faction": "FAC",
    "item": "ITEM",
    "object": "OBJ",
}


def parse_active(world: Path) -> dict[str, str]:
    path = world / "ACTIVE.md"
    if not path.exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    data: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    data.setdefault("branch_path", "story/main")
    data.setdefault("branch_id", "main")
    return data


def parse_field(text: str, field: str) -> str | None:
    match = re.search(rf"^\s*-\s*{re.escape(field)}:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def slugify(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback.lower()


def validate_filename_part(value: str, field: str) -> str:
    if not value or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise SystemExit(f"{field} must contain only letters, numbers, underscores, or hyphens: {value}")
    return value


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def iter_known_ids(branch: Path) -> set[str]:
    ids: set[str] = set()
    for root in [branch / "state" / "entities", branch / "state" / "locations"]:
        if not root.exists():
            continue
        for path in root.glob("*.md"):
            text = path.read_text(encoding="utf-8")
            ids.add(parse_field(text, "id") or path.stem.split("-", 1)[0])
    return ids


def next_id(branch: Path, kind: str) -> str:
    prefix = ID_PREFIX[kind]
    highest = 0
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
    for entity_id in iter_known_ids(branch):
        match = pattern.match(entity_id)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"{prefix}-{highest + 1:04d}" if prefix != "LOC" else f"{prefix}-{highest + 1:03d}"


def ensure_unique_id(branch: Path, entity_id: str, overwrite: bool) -> None:
    if overwrite:
        return
    if entity_id in iter_known_ids(branch):
        raise SystemExit(f"Entity id already exists in active branch: {entity_id}")


def target_dir(branch: Path, kind: str) -> Path:
    if kind == "location":
        return branch / "state" / "locations"
    return branch / "state" / "entities"


def render_card(args: argparse.Namespace, entity_id: str, active: dict[str, str], traits: Any | None) -> str:
    title = f"# {entity_id} {args.name}"
    lines = [
        title,
        "",
        "- schema: be-a-god.entity-card.v1",
        f"- id: {entity_id}",
        f"- kind: {args.kind}",
        f"- public_name: {args.name}",
        f"- branch_id: {active.get('branch_id', 'main')}",
        f"- status: {args.status}",
        f"- attention: {args.attention}",
    ]
    if args.summary:
        lines.append(f"- summary: {args.summary}")
    if args.location:
        lines.append(f"- location: {args.location}")
    if args.x is not None:
        lines.append(f"- x: {args.x:g}")
    if args.y is not None:
        lines.append(f"- y: {args.y:g}")
    if args.level:
        lines.append(f"- level: {args.level}")
    if args.source:
        lines.append(f"- source: {args.source}")
    lines.extend(["", "## Public state", ""])
    lines.append(args.public_state or "未记录。")
    if traits is not None:
        lines.extend(
            [
                "",
                "## Model semantic draft",
                "",
                "The language model may generate or revise this section; the script only stores it.",
                "",
                "```json",
                json.dumps(traits, ensure_ascii=False, indent=2),
                "```",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def upsert_location_map(world: Path, args: argparse.Namespace, entity_id: str) -> list[str]:
    changed: list[str] = []
    if args.kind != "location":
        return changed

    maps = world / "base" / "maps"
    hierarchy_path = maps / "hierarchy.json"
    coordinates_path = maps / "coordinates.json"
    hierarchy = load_json(hierarchy_path, {"levels": ["world", "region", "scene"], "nodes": []})
    coordinates = load_json(coordinates_path, {"places": []})

    nodes = hierarchy.setdefault("nodes", [])
    node = next((item for item in nodes if item.get("id") == entity_id), None)
    if node is None:
        node = {"id": entity_id}
        nodes.append(node)
    node["name"] = args.name
    node["level"] = args.level or node.get("level") or "scene"
    if args.location:
        node["parent"] = args.location

    places = coordinates.setdefault("places", [])
    place = next((item for item in places if item.get("id") == entity_id), None)
    if place is None:
        place = {"id": entity_id}
        places.append(place)
    place["name"] = args.name
    if args.x is not None:
        place["x"] = args.x
    if args.y is not None:
        place["y"] = args.y
    place["level"] = args.level or place.get("level") or "scene"

    write_json(hierarchy_path, hierarchy)
    write_json(coordinates_path, coordinates)
    changed.extend([hierarchy_path.relative_to(world).as_posix(), coordinates_path.relative_to(world).as_posix()])
    return changed


def run_refresh(world: Path) -> list[str]:
    ran: list[str] = []
    for script, args in [
        ("build_indexes.py", ["--world", str(world)]),
        ("build_map_layers.py", ["--world", str(world)]),
        ("update_map_state.py", ["--world", str(world)]),
        ("build_file_manifest.py", [str(world)]),
    ]:
        subprocess.run([sys.executable, str(SCRIPTS / script), *args], check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ran.append(script)
    return ran


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a deterministic entity/location card in the active branch.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--kind", choices=sorted(ID_PREFIX), default="character")
    parser.add_argument("--entity-id")
    parser.add_argument("--name", required=True)
    parser.add_argument("--slug")
    parser.add_argument("--summary", default="")
    parser.add_argument("--public-state", default="")
    parser.add_argument("--location", help="Current location id for entities, or parent location id for locations.")
    parser.add_argument("--status", default="ordinary")
    parser.add_argument("--attention", choices=["followed", "normal", "ignored"], default="normal")
    parser.add_argument("--x", type=float)
    parser.add_argument("--y", type=float)
    parser.add_argument("--level", default="")
    parser.add_argument("--source", default="model-generated-draft")
    parser.add_argument("--traits-json", help="Optional JSON file generated by the model for high-semantic traits.")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--skip-refresh", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    active = parse_active(world)
    branch = world / active["branch_path"]
    if not branch.exists():
        raise SystemExit(f"Active branch path not found: {branch}")

    entity_id = validate_filename_part(args.entity_id, "--entity-id") if args.entity_id else next_id(branch, args.kind)
    ensure_unique_id(branch, entity_id, args.overwrite)
    slug = validate_filename_part(args.slug, "--slug") if args.slug else slugify(args.name, entity_id)
    output = target_dir(branch, args.kind) / f"{entity_id}-{slug}.md"
    if output.exists() and not args.overwrite:
        raise SystemExit(f"Target file already exists: {output}")

    traits = load_json(Path(args.traits_json), None) if args.traits_json else None
    card = render_card(args, entity_id, active, traits)
    report = {
        "ok": True,
        "status": "dry-run" if args.dry_run else "created",
        "entity_id": entity_id,
        "kind": args.kind,
        "path": output.relative_to(world).as_posix(),
        "changed": [output.relative_to(world).as_posix()],
        "refreshed": [],
    }

    if args.dry_run:
        report["preview"] = card
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else card)
        return 0
    if not args.confirmed:
        raise SystemExit("Refusing to write entity card without --confirmed. Use --dry-run to preview.")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(card, encoding="utf-8")
    report["changed"].extend(upsert_location_map(world, args, entity_id))
    if not args.skip_refresh:
        report["refreshed"] = run_refresh(world)

    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else f"Created {entity_id}: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
