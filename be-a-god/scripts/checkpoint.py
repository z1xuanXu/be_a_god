#!/usr/bin/env python3
"""Create a recoverable checkpoint for the active branch."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def utc_id() -> str:
    return datetime.now(timezone.utc).strftime("CP-%Y%m%d%H%M%S%f")


def validate_id(value: str, field: str) -> str:
    if not SAFE_ID_PATTERN.fullmatch(value):
        raise SystemExit(f"{field} must contain only letters, numbers, underscores, or hyphens: {value}")
    return value


def parse_active(world: Path) -> dict[str, str]:
    data = {}
    for line in (world / "ACTIVE.md").read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    data.setdefault("branch_path", "story/main")
    data.setdefault("branch_id", "main")
    return data


def copy_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def relative_inside(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise SystemExit(f"Path is outside world directory: {path}") from exc


def load_core_files(world: Path) -> list[Path]:
    manifest_path = world / "system" / "file-manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        paths = []
        for item in manifest.get("files", []):
            if item.get("authority") != "core":
                continue
            rel = item.get("path")
            if not rel:
                continue
            path = (world / rel).resolve()
            relative_inside(path, world)
            if path.exists() and path.is_file():
                paths.append(path)
        return sorted(set(paths))

    fallback = []
    for rel in ["WORLD.md", "ACTIVE.md", "CANON.md", "PLAYER.md", "story/STORY-TREE.md"]:
        path = world / rel
        if path.exists():
            fallback.append(path)
    for pattern in ["story/**/SAVE.md", "story/**/events/*.md", "story/**/state/**/*.md", "story/**/random/*.json", "story/**/random/*.jsonl"]:
        fallback.extend(path for path in world.glob(pattern) if path.is_file())
    return sorted(set(fallback))


def copy_core_snapshot(world: Path, out_dir: Path) -> dict[str, str]:
    mapping = {}
    snapshot_dir = out_dir / "core-snapshot"
    for src in load_core_files(world):
        rel = relative_inside(src, world)
        dst = snapshot_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        mapping[rel] = dst.relative_to(out_dir).as_posix()
    return mapping


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an active branch checkpoint.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--reason", default="manual checkpoint")
    parser.add_argument("--checkpoint-id")
    parser.add_argument("--no-core-snapshot", action="store_true", help="Skip copying core files into core-snapshot/.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    active = parse_active(world)
    branch = world / active["branch_path"]
    checkpoint_id = validate_id(args.checkpoint_id or utc_id(), "--checkpoint-id")
    out_dir = branch / "checkpoints" / checkpoint_id
    files = {
        "SAVE.md": branch / "SAVE.md",
        "CURRENT.md": branch / "CURRENT.md",
        "timeline.json": world / "dashboard" / "timeline.json",
        "dashboard.json": world / "dashboard" / "data.json",
        "file-manifest.json": world / "system" / "file-manifest.json",
    }
    plan = {
        "checkpoint_id": checkpoint_id,
        "branch_id": active.get("branch_id"),
        "branch_path": active.get("branch_path"),
        "output": str(out_dir),
        "reason": args.reason,
        "files": {name: str(path) for name, path in files.items() if path.exists()},
        "core_snapshot": "skipped" if args.no_core_snapshot else f"{out_dir}/core-snapshot",
    }
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    if out_dir.exists():
        raise SystemExit(f"Checkpoint already exists: {out_dir}")
    out_dir.mkdir(parents=True)
    copied = {}
    for name, src in files.items():
        copied[name] = copy_if_exists(src, out_dir / name)
    core_snapshot = {} if args.no_core_snapshot else copy_core_snapshot(world, out_dir)
    metadata = {
        "schema": "be-a-god.checkpoint.v1",
        "checkpoint_id": checkpoint_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reason": args.reason,
        "branch_id": active.get("branch_id"),
        "branch_path": active.get("branch_path"),
        "copied": copied,
        "core_snapshot": core_snapshot,
    }
    (out_dir / "checkpoint.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Created checkpoint: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
