#!/usr/bin/env python3
"""Build a manifest of file hashes for a be-a-god world directory."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


DERIVED_PARTS = {"indexes", "dashboard"}
SYSTEM_DERIVED_NAMES = {"validation-report.md"}


def classify(path: Path, world: Path) -> str:
    rel = path.relative_to(world)
    parts = set(rel.parts)
    name = path.name
    if parts & DERIVED_PARTS or name in SYSTEM_DERIVED_NAMES:
        return "derived"
    if "random" in parts or name in {"ACTIVE.md", "CANON.md", "PLAYER.md", "WORLD.md"}:
        return "core"
    if "events" in parts or "chapters" in parts or "state" in parts or name == "SAVE.md":
        return "core"
    return "support"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(world: Path):
    for path in sorted(world.rglob("*")):
        if not path.is_file():
            continue
        if ".git" in path.parts:
            continue
        yield path


def resolve_output(world: Path, raw_output: str | None) -> Path:
    if not raw_output:
        return world / "system" / "file-manifest.json"
    raw = Path(raw_output)
    output = (world / raw).resolve() if not raw.is_absolute() else raw.resolve()
    try:
        output.relative_to(world)
    except ValueError as exc:
        raise SystemExit(f"output must stay inside the world directory: {output}") from exc
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("world", help="Path to worlds/<world-id>")
    parser.add_argument("--output", help="Manifest output path. Defaults to system/file-manifest.json")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    if not world.exists() or not world.is_dir():
        raise SystemExit(f"World directory not found: {world}")

    output = resolve_output(world, args.output)
    files = []
    for path in iter_files(world):
        if path.resolve() == output:
            continue
        rel = path.relative_to(world).as_posix()
        files.append(
            {
                "path": rel,
                "sha256": sha256_file(path),
                "authority": classify(path, world),
                "bytes": path.stat().st_size,
            }
        )

    manifest = {
        "schema": "be-a-god.file-manifest.v1",
        "world": world.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output} with {len(files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
