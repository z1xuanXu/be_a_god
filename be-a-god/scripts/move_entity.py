#!/usr/bin/env python3
"""Move a branch-local entity to a location or direct map coordinate."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_active(world: Path) -> dict[str, str]:
    active_path = world / "ACTIVE.md"
    if not active_path.exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    data: dict[str, str] = {}
    for line in active_path.read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    data.setdefault("branch_path", "story/main")
    data.setdefault("branch_id", "main")
    return data


def parse_field(text: str, field: str) -> str | None:
    match = re.search(rf"^\s*-\s*{re.escape(field)}:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def find_entity(branch: Path, entity_id: str) -> Path:
    root = branch / "state" / "entities"
    if not root.exists():
        raise SystemExit(f"Entity directory not found: {root}")
    prefix_matches: list[Path] = []
    for path in sorted(root.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if parse_field(text, "id") == entity_id:
            return path
        if path.stem.lower().startswith(entity_id.lower()):
            prefix_matches.append(path)
    if len(prefix_matches) == 1:
        return prefix_matches[0]
    if len(prefix_matches) > 1:
        choices = ", ".join(path.name for path in prefix_matches)
        raise SystemExit(f"Entity id is ambiguous; use the exact `- id:` value. Matches: {choices}")
    raise SystemExit(f"Entity not found in active branch: {entity_id}")


def replace_or_append_field(markdown: str, field: str, value: str) -> str:
    line = f"- {field}: {value}"
    pattern = re.compile(rf"^\s*-\s*{re.escape(field)}:\s*.*$", re.MULTILINE)
    if pattern.search(markdown):
        return pattern.sub(line, markdown, count=1)
    return markdown.rstrip() + "\n" + line + "\n"


def movement_plan(args: argparse.Namespace, world: Path, branch: Path, entity_path: Path) -> dict:
    changes: dict[str, str] = {}
    if args.location:
        changes["location"] = args.location
    if args.x is not None:
        changes["x"] = f"{args.x:g}"
    if args.y is not None:
        changes["y"] = f"{args.y:g}"
    if args.level:
        changes["level"] = args.level
    if args.status:
        changes["status"] = args.status
    if not changes:
        raise SystemExit("No movement changes supplied. Provide --location, --x/--y, --level, or --status.")
    return {
        "ok": True,
        "status": "dry-run" if args.dry_run else "moved",
        "entity_id": args.entity_id,
        "entity_file": entity_path.relative_to(world).as_posix(),
        "branch": branch.relative_to(world).as_posix(),
        "changes": changes,
        "note": args.note,
        "refreshed": [],
    }


def apply_movement(entity_path: Path, changes: dict[str, str], note: str) -> None:
    text = entity_path.read_text(encoding="utf-8")
    for field, value in changes.items():
        text = replace_or_append_field(text, field, value)
    if note:
        text = text.rstrip() + f"\n\n## Movement log\n\n- moved_at: {utc_now()}\n- note: {note}\n"
    entity_path.write_text(text.rstrip() + "\n", encoding="utf-8")


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
    parser = argparse.ArgumentParser(description="Move a visible entity/piece in the active branch.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--entity-id", required=True)
    parser.add_argument("--location")
    parser.add_argument("--x", type=float)
    parser.add_argument("--y", type=float)
    parser.add_argument("--level")
    parser.add_argument("--status")
    parser.add_argument("--note", default="")
    parser.add_argument("--skip-refresh", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    active = parse_active(world)
    branch = world / active["branch_path"]
    entity_path = find_entity(branch, args.entity_id)
    plan = movement_plan(args, world, branch, entity_path)

    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2) if args.json else json.dumps(plan, ensure_ascii=False))
        return 0
    if not args.confirmed:
        raise SystemExit("Refusing to move entity without --confirmed. Use --dry-run to preview.")

    apply_movement(entity_path, plan["changes"], args.note)
    if not args.skip_refresh:
        plan["refreshed"] = run_refresh(world)
    print(json.dumps(plan, ensure_ascii=False, indent=2) if args.json else f"Moved {args.entity_id}: {entity_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
