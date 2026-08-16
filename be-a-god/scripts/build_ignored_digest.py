#!/usr/bin/env python3
"""Build an event-skeleton digest for an ignored character without cancelling ignore state."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


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


def parse_list(value: str | None) -> list[str]:
    if not value:
        return []
    raw = value.strip()
    if raw in {"[]", "none", "None", "null"}:
        return []
    if raw.startswith("[") and raw.endswith("]"):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            raw = raw[1:-1]
    return [item.strip().strip("'\"") for item in raw.split(",") if item.strip().strip("'\"")]


def event_involves_target(text: str, target_id: str) -> bool:
    actors = parse_list(parse_field(text, "actors"))
    if target_id in actors:
        return True
    return parse_field(text, "target_id") == target_id


def resolve_output(world: Path, output: str) -> Path:
    path = Path(output)
    if not path.is_absolute():
        path = world / path
    path = path.resolve()
    try:
        path.relative_to(world.resolve())
    except ValueError as exc:
        raise SystemExit(f"output must stay inside the world directory: {path}") from exc
    return path


def update_manifest(world: Path) -> None:
    script = Path(__file__).resolve().parent / "build_file_manifest.py"
    subprocess.run([sys.executable, str(script), str(world)], check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build ignored entity event digest.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--output")
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing an existing digest output inside the world.")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    active = parse_active(world)
    branch = world / active["branch_path"]
    events = []
    for path in sorted((branch / "events").glob("EVT-*.md")):
        text = path.read_text(encoding="utf-8")
        if not event_involves_target(text, args.target_id):
            continue
        events.append(
            {
                "event_id": parse_field(text, "id") or path.stem,
                "time": parse_field(text, "time") or "unknown",
                "title": parse_title(text, path.stem),
                "source": path.relative_to(world).as_posix(),
            }
        )
    digest = {
        "schema": "be-a-god.ignored-digest.v1",
        "world_id": active.get("world_id", world.name),
        "branch_id": active.get("branch_id", "main"),
        "target_id": args.target_id,
        "attention_state_unchanged": True,
        "events": events,
    }
    text = json.dumps(digest, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = resolve_output(world, args.output)
        if output.exists() and not args.overwrite:
            raise SystemExit(f"refusing to overwrite existing digest output without --overwrite: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        update_manifest(world)
        print(f"Wrote ignored digest: {output}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
