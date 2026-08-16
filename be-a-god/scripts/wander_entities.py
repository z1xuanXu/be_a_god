#!/usr/bin/env python3
"""Apply deterministic wandering moves for visible branch entities."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent
SKIP_STATUSES = {"dead", "destroyed", "missing", "paused"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_active(world: Path) -> dict[str, str]:
    data: dict[str, str] = {}
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


def replace_or_append_field(markdown: str, field: str, value: str) -> str:
    line = f"- {field}: {value}"
    pattern = re.compile(rf"^\s*-\s*{re.escape(field)}:\s*.*$", re.MULTILINE)
    if pattern.search(markdown):
        return pattern.sub(line, markdown, count=1)
    return markdown.rstrip() + "\n" + line + "\n"


def load_seed(branch: Path) -> str:
    path = branch / "random" / "seed.json"
    if not path.exists():
        raise SystemExit(f"Missing random seed: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    seed = str(data.get("seed") or "")
    if not seed:
        raise SystemExit(f"Random seed is empty: {path}")
    return seed


def load_world_time(branch: Path) -> str:
    save = branch / "SAVE.md"
    if not save.exists():
        return "unknown"
    return parse_field(save.read_text(encoding="utf-8"), "world_time") or "unknown"


def load_destinations(world: Path) -> list[dict]:
    path = world / "base" / "maps" / "coordinates.json"
    if not path.exists():
        raise SystemExit(f"Map coordinates missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    destinations = []
    for place in data.get("places", []):
        if place.get("id") and "x" in place and "y" in place:
            destinations.append(place)
    if not destinations:
        raise SystemExit("No coordinate places available for wandering.")
    return destinations


def iter_entities(branch: Path, entity_ids: list[str] | None, include_ignored: bool) -> list[tuple[Path, dict]]:
    root = branch / "state" / "entities"
    wanted = set(entity_ids or [])
    items: list[tuple[Path, dict]] = []
    for path in sorted(root.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        entity_id = parse_field(text, "id") or path.stem
        if wanted and entity_id not in wanted:
            continue
        status = parse_field(text, "status") or "ordinary"
        attention = parse_field(text, "attention") or "normal"
        kind = parse_field(text, "kind") or "character"
        if status in SKIP_STATUSES:
            continue
        if attention == "ignored" and not include_ignored:
            continue
        if kind not in {"character", "object", "item"}:
            continue
        items.append(
            (
                path,
                {
                    "id": entity_id,
                    "name": parse_field(text, "public_name") or parse_field(text, "name") or entity_id,
                    "kind": kind,
                    "status": status,
                    "attention": attention,
                    "location": parse_field(text, "location"),
                },
            )
        )
    if wanted:
        found = {item[1]["id"] for item in items}
        missing = sorted(wanted - found)
        if missing:
            raise SystemExit(f"Requested entities not movable or not found: {', '.join(missing)}")
    return items


def parse_overrides(raw: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for item in raw:
        if "=" not in item:
            raise SystemExit(f"Invalid --override format, expected ENTITY=LOCATION: {item}")
        entity_id, location_id = item.split("=", 1)
        entity_id = entity_id.strip()
        location_id = location_id.strip()
        if not entity_id or not location_id:
            raise SystemExit(f"Invalid --override format, expected ENTITY=LOCATION: {item}")
        overrides[entity_id] = location_id
    return overrides


def choose_destination(seed: str, world_time: str, purpose: str, entity_id: str, current: str | None, destinations: list[dict]) -> tuple[dict, int]:
    pool = [place for place in destinations if str(place.get("id")) != str(current)] or destinations
    material = f"{seed}|wander|{purpose}|{world_time}|{entity_id}".encode("utf-8")
    value = int(hashlib.sha256(material).hexdigest(), 16)
    index = value % len(pool)
    return pool[index], value


def next_random_index(branch: Path) -> int:
    log = branch / "random" / "random-log.jsonl"
    if not log.exists():
        return 1
    return sum(1 for line in log.read_text(encoding="utf-8").splitlines() if line.strip()) + 1


def build_plan(args: argparse.Namespace, world: Path) -> dict:
    active = parse_active(world)
    branch = world / active["branch_path"]
    seed = load_seed(branch)
    world_time = load_world_time(branch)
    destinations = load_destinations(world)
    by_id = {str(place["id"]): place for place in destinations}
    overrides = parse_overrides(args.override)
    entity_ids = args.entity_id if args.entity_id else None
    entities = iter_entities(branch, entity_ids, include_ignored=not args.exclude_ignored)
    if args.limit and not entity_ids:
        entities = entities[: args.limit]
    moves = []
    for path, entity in entities:
        mode = "override" if entity["id"] in overrides else "random"
        if mode == "override":
            destination = by_id.get(overrides[entity["id"]])
            if not destination:
                raise SystemExit(f"Override location not found in coordinates: {overrides[entity['id']]}")
            random_value = None
        else:
            destination, random_value = choose_destination(seed, world_time, args.purpose, entity["id"], entity.get("location"), destinations)
        moves.append(
            {
                "entity_id": entity["id"],
                "entity_file": path.relative_to(world).as_posix(),
                "name": entity["name"],
                "from_location": entity.get("location"),
                "to_location": destination["id"],
                "x": destination.get("x"),
                "y": destination.get("y"),
                "level": destination.get("level"),
                "status": args.status,
                "mode": mode,
                "random_value": random_value,
            }
        )
    return {
        "schema": "be-a-god.wander-plan.v1",
        "status": "dry-run" if args.dry_run else "applied",
        "world_id": active.get("world_id", world.name),
        "branch_id": active.get("branch_id", "main"),
        "branch_path": active["branch_path"],
        "world_time": world_time,
        "purpose": args.purpose,
        "moves": moves,
        "note": "mechanical wandering only; semantic motive and narration remain model/player work",
        "refreshed": [],
    }


def apply_move(world: Path, move: dict, note: str) -> None:
    path = world / move["entity_file"]
    text = path.read_text(encoding="utf-8")
    fields = {
        "location": str(move["to_location"]),
        "x": str(move["x"]),
        "y": str(move["y"]),
        "status": str(move["status"]),
    }
    if move.get("level"):
        fields["level"] = str(move["level"])
    for field, value in fields.items():
        text = replace_or_append_field(text, field, value)
    text = text.rstrip() + f"\n\n## Wandering log\n\n- wandered_at: {utc_now()}\n- from: {move.get('from_location') or 'unknown'}\n- to: {move['to_location']}\n- mode: {move['mode']}\n- note: {note}\n"
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def append_random_log(world: Path, plan: dict) -> None:
    branch = world / plan["branch_path"]
    log = branch / "random" / "random-log.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    index = next_random_index(branch)
    lines = []
    for offset, move in enumerate(plan["moves"]):
        entry = {
            "schema": "be-a-god.random-log.v1",
            "index": index + offset,
            "created_at": utc_now(),
            "purpose": plan["purpose"],
            "kind": "wander",
            "mode": move["mode"],
            "entity_id": move["entity_id"],
            "value": move["to_location"],
            "world_time": plan["world_time"],
        }
        if move.get("random_value") is not None:
            entry["random_value"] = move["random_value"]
        lines.append(json.dumps(entry, ensure_ascii=False))
    if lines:
        with log.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


def run_refresh(world: Path) -> list[str]:
    ran: list[str] = []
    for script, args in [
        ("build_indexes.py", ["--world", str(world)]),
        ("update_map_state.py", ["--world", str(world)]),
        ("build_file_manifest.py", [str(world)]),
    ]:
        subprocess.run([sys.executable, str(SCRIPTS / script), *args], check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ran.append(script)
    return ran


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply deterministic wandering moves for active branch entities.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--entity-id", action="append", help="Entity id to move. May be repeated. Defaults to movable entities in sorted order.")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--purpose", default="wandering")
    parser.add_argument("--status", default="wandering")
    parser.add_argument("--note", default="world tick wandering")
    parser.add_argument("--override", action="append", default=[], help="Player override in ENTITY=LOCATION format. May be repeated.")
    parser.add_argument("--exclude-ignored", action="store_true")
    parser.add_argument("--skip-refresh", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.limit < 0:
        raise SystemExit("--limit must be non-negative")
    world = Path(args.world).resolve()
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    plan = build_plan(args, world)
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2) if args.json else json.dumps(plan, ensure_ascii=False))
        return 0
    if not args.confirmed:
        raise SystemExit("Refusing to apply wandering without --confirmed. Use --dry-run to inspect the plan.")
    for move in plan["moves"]:
        apply_move(world, move, args.note)
    append_random_log(world, plan)
    if not args.skip_refresh:
        plan["refreshed"] = run_refresh(world)
    print(json.dumps(plan, ensure_ascii=False, indent=2) if args.json else f"Applied wandering moves: {len(plan['moves'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
