#!/usr/bin/env python3
"""Create a compact branch-local handoff for continuing play in a new Codex conversation."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def utc_now_id() -> str:
    return datetime.now(timezone.utc).strftime("HOF-%Y%m%d-%H%M%S")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_world(path: str) -> Path:
    world = Path(path).resolve()
    if not world.exists() or not world.is_dir():
        raise SystemExit(f"world directory not found: {world}")
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    return world


def parse_active(world: Path) -> dict[str, str]:
    data = {}
    for line in (world / "ACTIVE.md").read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    data.setdefault("world_id", world.name)
    data.setdefault("branch_id", "main")
    data.setdefault("branch_path", "story/main")
    data.setdefault("save_path", f"{data['branch_path']}/SAVE.md")
    return data


def parse_field(text: str, field: str) -> str | None:
    match = re.search(rf"^\s*-\s*{re.escape(field)}:\s*(.*?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def section_lines(text: str, heading: str) -> list[str]:
    pattern = rf"^##\s+{re.escape(heading)}\s*$"
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return []
    start = match.end()
    next_match = re.search(r"^##\s+", text[start:], re.MULTILINE)
    end = start + next_match.start() if next_match else len(text)
    return [line.rstrip() for line in text[start:end].strip().splitlines() if line.strip()]


def rel(path: Path, world: Path) -> str:
    return path.relative_to(world).as_posix()


def validate_id(value: str, field: str) -> str:
    if not SAFE_ID_PATTERN.fullmatch(value):
        raise SystemExit(f"{field} must contain only letters, numbers, underscores, or hyphens: {value}")
    return value


def event_sort_key(path: Path) -> tuple[int, str]:
    match = re.search(r"EVT-(\d+)", path.name)
    return (int(match.group(1)) if match else 999999, path.name)


def read_recent_events(branch: Path, world: Path, limit: int) -> list[dict[str, str]]:
    events = []
    for path in sorted((branch / "events").glob("EVT-*.md"), key=event_sort_key)[-limit:]:
        text = path.read_text(encoding="utf-8")
        title = text.splitlines()[0].lstrip("# ").strip() if text.splitlines() else path.stem
        events.append(
            {
                "id": parse_field(text, "id") or path.stem,
                "title": title,
                "type": parse_field(text, "type") or "",
                "time": parse_field(text, "time") or "",
                "source": parse_field(text, "source") or rel(path, world),
                "path": rel(path, world),
            }
        )
    return events


def read_chronicle_tail(branch: Path, limit: int) -> list[str]:
    path = branch / "chronicle" / "objective.md"
    if not path.exists():
        return []
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip().startswith("- ")]
    return lines[-limit:]


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def build_handoff(world: Path, handoff_id: str, max_events: int, max_chronicle_lines: int) -> dict:
    active = parse_active(world)
    branch = world / active["branch_path"]
    if not branch.exists():
        raise SystemExit(f"active branch path not found: {branch}")
    save_path = world / active["save_path"]
    if not save_path.exists():
        save_path = branch / "SAVE.md"
    save_text = save_path.read_text(encoding="utf-8") if save_path.exists() else ""
    current_path = branch / "CURRENT.md"
    current_text = current_path.read_text(encoding="utf-8") if current_path.exists() else ""

    first_read = [
        "ACTIVE.md",
        active["save_path"],
        "PLAYER.md",
        f"{active['branch_path']}/CURRENT.md",
        f"{active['branch_path']}/runtime/context-handoffs/{handoff_id}/HANDOFF.md",
    ]
    optional_read = [
        "CANON.md",
        "dashboard/data.json",
        "dashboard/timeline.json",
        f"{active['branch_path']}/chronicle/objective.md",
        f"{active['branch_path']}/events/<event-id>.md",
        f"{active['branch_path']}/state/entities/<entity-id>.md",
    ]

    return {
        "schema": "be-a-god.handoff.v1",
        "handoff_id": handoff_id,
        "created_at": utc_now(),
        "world": {
            "world_id": active.get("world_id", world.name),
            "world_path": str(world),
            "branch_id": active.get("branch_id", "main"),
            "branch_path": active["branch_path"],
            "save_path": active["save_path"],
        },
        "current_state": {
            "world_time": parse_field(save_text, "world_time") or "",
            "focal_place": parse_field(save_text, "focal_place") or "",
            "current_scene": parse_field(save_text, "current_scene") or current_text.strip(),
            "player_god_role": parse_field(save_text, "player_god_role") or "",
        },
        "branch_inheritance": {
            "parent_branch_id": parse_field(save_text, "parent_branch_id") or "none",
            "parent_save": parse_field(save_text, "parent_save") or "none",
            "fork_event": parse_field(save_text, "fork_event") or "none",
            "inherit_until": parse_field(save_text, "inherit_until") or "",
        },
        "open_items": section_lines(save_text, "Open items"),
        "source_pointers": section_lines(save_text, "Source pointers"),
        "recent_chronicle": read_chronicle_tail(branch, max_chronicle_lines),
        "recent_events": read_recent_events(branch, world, max_events),
        "random": {
            "seed_path": f"{active['branch_path']}/random/seed.json",
            "random_log_path": f"{active['branch_path']}/random/random-log.jsonl",
            "random_log_entries": count_jsonl(branch / "random" / "random-log.jsonl"),
        },
        "derived_data": {
            "dashboard": "dashboard/data.json",
            "timeline": "dashboard/timeline.json",
            "map_layers": "dashboard/map-layers.json",
        },
        "resume_rules": [
            "Read the first_read files before continuing.",
            "Do not read sibling branches unless the player explicitly asks to compare branches.",
            "Expand event, entity, or chapter sources only when the current action requires exact history.",
            "Treat this handoff as an index and summary, not as a replacement for canonical files.",
        ],
        "first_read": first_read,
        "optional_read": optional_read,
    }


def render_markdown(handoff: dict) -> str:
    world = handoff["world"]
    state = handoff["current_state"]
    inherit = handoff["branch_inheritance"]
    lines = [
        f"# HANDOFF {handoff['handoff_id']}",
        "",
        "## Resume command",
        "",
        "Use `$be-a-god` and continue from this world with the smallest needed context.",
        "",
        "## Identity",
        "",
        f"- world_id: {world['world_id']}",
        f"- world_path: {world['world_path']}",
        f"- branch_id: {world['branch_id']}",
        f"- branch_path: {world['branch_path']}",
        f"- save_path: {world['save_path']}",
        f"- created_at: {handoff['created_at']}",
        "",
        "## Current state",
        "",
        f"- world_time: {state['world_time']}",
        f"- focal_place: {state['focal_place']}",
        f"- current_scene: {state['current_scene']}",
        f"- player_god_role: {state['player_god_role']}",
        "",
        "## Branch inheritance",
        "",
        f"- parent_branch_id: {inherit['parent_branch_id']}",
        f"- parent_save: {inherit['parent_save']}",
        f"- fork_event: {inherit['fork_event']}",
        f"- inherit_until: {inherit['inherit_until']}",
        "",
        "## First files to read",
        "",
    ]
    lines.extend(f"- `{item}`" for item in handoff["first_read"])
    lines.extend(["", "## Optional source expansion", ""])
    lines.extend(f"- `{item}`" for item in handoff["optional_read"])
    lines.extend(["", "## Open items", ""])
    lines.extend(handoff["open_items"] or ["- none recorded"])
    lines.extend(["", "## Source pointers from SAVE", ""])
    lines.extend(handoff["source_pointers"] or ["- none recorded"])
    lines.extend(["", "## Recent chronicle", ""])
    lines.extend(handoff["recent_chronicle"] or ["- none recorded"])
    lines.extend(["", "## Recent event nodes", ""])
    if handoff["recent_events"]:
        for event in handoff["recent_events"]:
            lines.append(f"- `{event['id']}` | {event['time']} | {event['title']} | source: `{event['source']}` | path: `{event['path']}`")
    else:
        lines.append("- none recorded")
    lines.extend(["", "## Random state", ""])
    random = handoff["random"]
    lines.extend(
        [
            f"- seed_path: `{random['seed_path']}`",
            f"- random_log_path: `{random['random_log_path']}`",
            f"- random_log_entries: {random['random_log_entries']}",
        ]
    )
    lines.extend(["", "## Resume rules", ""])
    lines.extend(f"- {item}" for item in handoff["resume_rules"])
    return "\n".join(lines).rstrip() + "\n"


def update_manifest(world: Path) -> None:
    script = Path(__file__).resolve().parent / "build_file_manifest.py"
    subprocess.run([sys.executable, str(script), str(world)], check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a compact handoff for a be-a-god world branch.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--handoff-id", default=utc_now_id())
    parser.add_argument("--max-events", type=int, default=8)
    parser.add_argument("--max-chronicle-lines", type=int, default=12)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirmed", action="store_true", help="Required for writing handoff files.")
    parser.add_argument("--skip-manifest", action="store_true", help="Do not refresh system/file-manifest.json after writing.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    world = resolve_world(args.world)
    if not args.dry_run and not args.confirmed:
        raise SystemExit("refusing to write handoff files without --confirmed")
    if args.max_events < 0 or args.max_chronicle_lines < 0:
        raise SystemExit("limits must be non-negative")
    args.handoff_id = validate_id(args.handoff_id, "--handoff-id")

    handoff = build_handoff(world, args.handoff_id, args.max_events, args.max_chronicle_lines)
    markdown = render_markdown(handoff)
    active = parse_active(world)
    output_dir = world / active["branch_path"] / "runtime" / "context-handoffs" / args.handoff_id
    report = {
        "ok": True,
        "dry_run": args.dry_run,
        "handoff_id": args.handoff_id,
        "output_dir": str(output_dir),
        "markdown_path": str(output_dir / "HANDOFF.md"),
        "save_markdown_path": str(output_dir / "存档.md"),
        "json_path": str(output_dir / "handoff.json"),
        "first_read": handoff["first_read"],
    }

    if args.dry_run:
        if args.json:
            print(json.dumps({**report, "handoff": handoff, "markdown": markdown}, ensure_ascii=False, indent=2))
        else:
            print(markdown)
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "HANDOFF.md").write_text(markdown, encoding="utf-8")
    (output_dir / "存档.md").write_text(markdown, encoding="utf-8")
    (output_dir / "handoff.json").write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.skip_manifest:
        update_manifest(world)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Created handoff: {output_dir / 'HANDOFF.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
