#!/usr/bin/env python3
"""Create, update, or remove mutable map terrain brushes."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
VALID_KINDS = {"river", "tributary", "hills", "forest", "custom"}


def validate_id(value: str, field: str) -> str:
    if not SAFE_ID_PATTERN.fullmatch(value):
        raise SystemExit(f"{field} must contain only letters, numbers, underscores, or hyphens: {value}")
    return value


def read_json(path: Path, fallback: dict) -> dict:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_active(world: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in (world / "ACTIVE.md").read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    data.setdefault("branch_path", "story/main")
    data.setdefault("branch_id", "main")
    return data


def parse_points(raw: str) -> list[list[float]]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"--points-json must be JSON: {exc}") from exc
    if not isinstance(data, list) or not data:
        raise SystemExit("--points-json must be a non-empty list of [x,y] points")
    points: list[list[float]] = []
    for index, point in enumerate(data, start=1):
        if not isinstance(point, list) or len(point) != 2:
            raise SystemExit(f"--points-json point {index} must be [x,y]")
        x, y = point
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise SystemExit(f"--points-json point {index} must contain numbers")
        if not 0 <= x <= 100 or not 0 <= y <= 100:
            raise SystemExit(f"--points-json point {index} must stay in 0..100 map coordinates")
        points.append([float(x), float(y)])
    return points


def validate_non_negative(value: float, field: str) -> float:
    if value < 0:
        raise SystemExit(f"{field} must be non-negative")
    return value


def refresh(world: Path) -> list[str]:
    ran: list[str] = []
    scripts = [
        ("build_map_layers.py", ["--world", str(world)]),
        ("build_file_manifest.py", [str(world)]),
    ]
    for script, args in scripts:
        subprocess.run([sys.executable, str(Path(__file__).resolve().parent / script), *args], check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ran.append(script)
    return ran


def collect_brushes(path: Path) -> list[dict]:
    return read_json(path, {"brushes": []}).get("brushes", [])


def main() -> int:
    parser = argparse.ArgumentParser(description="Set a mutable map terrain brush after player confirmation.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--brush-id", required=True)
    parser.add_argument("--kind", choices=sorted(VALID_KINDS), help="Brush kind to create or update.")
    parser.add_argument("--points-json", help="JSON list of [x,y] points in 0..100 map coordinates.")
    parser.add_argument("--label")
    parser.add_argument("--level", default="region")
    parser.add_argument("--width", type=float, default=5)
    parser.add_argument("--density", type=float, default=12)
    parser.add_argument("--jitter", type=float, default=2)
    parser.add_argument("--color")
    parser.add_argument("--remove", action="store_true")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    active = parse_active(world)
    branch_path = active.get("branch_path", "story/main")
    brush_id = validate_id(args.brush_id, "--brush-id")
    path = world / branch_path / "state" / "terrain-brushes.json"
    base_path = world / "base" / "maps" / "terrain-brushes.json"
    data = read_json(path, {"schema": "be-a-god.terrain-brushes.v1", "brushes": [], "read_policy": "terrain brush data only; story text not included"})
    brushes = data.setdefault("brushes", [])
    if not isinstance(brushes, list):
        raise SystemExit("terrain-brushes.json `brushes` must be a list")
    existing = next((brush for brush in brushes if isinstance(brush, dict) and brush.get("id") == brush_id), None)
    base_existing = next((brush for brush in collect_brushes(base_path) if isinstance(brush, dict) and brush.get("id") == brush_id), None)
    effective_existing = existing or base_existing

    if args.remove:
        plan = {"action": "remove", "brush_id": brush_id, "exists": effective_existing is not None, "path": f"{branch_path}/state/terrain-brushes.json"}
    else:
        if not args.kind and effective_existing is None:
            raise SystemExit("--kind is required when creating a new brush")
        if not args.points_json and effective_existing is None:
            raise SystemExit("--points-json is required when creating a new brush")
        existing_data = effective_existing or {}
        points = parse_points(args.points_json) if args.points_json else existing_data.get("points", [])
        width = validate_non_negative(args.width, "--width")
        density = validate_non_negative(args.density, "--density")
        jitter = validate_non_negative(args.jitter, "--jitter")
        plan = {
            "action": "upsert",
            "brush": {
                "id": brush_id,
                "kind": args.kind or existing_data.get("kind"),
                "label": args.label or existing_data.get("label") or brush_id,
                "level": args.level or existing_data.get("level") or "region",
                "points": points,
                "width": width,
                "density": density,
                "jitter": jitter,
                "color": args.color or existing_data.get("color"),
                "mutable_by_divine_action": True,
            },
            "path": f"{branch_path}/state/terrain-brushes.json",
        }

    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    if not args.confirmed:
        raise SystemExit("Refusing to change map brushes without --confirmed. Use --dry-run to inspect the plan.")

    if args.remove:
        replacement = {"id": brush_id, "kind": (effective_existing or {}).get("kind", "custom"), "points": [[0, 0]], "removed": True, "mutable_by_divine_action": True}
        if existing is None:
            brushes.append(replacement)
        else:
            existing.clear()
            existing.update(replacement)
    else:
        brush = plan["brush"]
        if existing is None:
            brushes.append(brush)
        else:
            existing.clear()
            existing.update(brush)
    data["schema"] = "be-a-god.terrain-brushes.v1"
    data["read_policy"] = "terrain brush data only; story text not included"
    write_json(path, data)
    ran = refresh(world)
    print(json.dumps({"ok": True, "brush_id": brush_id, "terrain_brushes": f"{branch_path}/state/terrain-brushes.json", "refreshed": ran}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
