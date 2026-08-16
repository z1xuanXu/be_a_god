#!/usr/bin/env python3
"""Create a child story branch from the active branch after player confirmation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


BRANCH_DIRS = [
    "chapters",
    "events",
    "state/entities",
    "state/locations",
    "chronicle",
    "queues",
    "random",
    "runtime/action-requests",
    "runtime/interaction-packets",
    "runtime/advance-runs",
    "runtime/branch-drafts",
    "runtime/context-handoffs",
    "runtime/divine-assessments",
    "runtime/manual-edit-reports",
    "runtime/resume-packets",
    "runtime/rule-checks",
    "runtime/soften-requests",
    "checkpoints",
    "branches",
]
SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
SNAPSHOT_STATE_DIRS = ["state/entities", "state/locations"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: str) -> str:
    cleaned = re.sub(r"[^\w-]+", "-", value.strip(), flags=re.UNICODE).strip("-").lower()
    return cleaned[:64].rstrip("-")


def normalize_branch_id(value: str) -> str:
    branch_id = slug(value)
    if not branch_id:
        raise SystemExit("--branch-id must contain at least one letter, number, underscore, or hyphen after slug normalization")
    return branch_id


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
    data.setdefault("save_path", f"{data['branch_path']}/SAVE.md")
    return data


def parse_field(text: str, field: str) -> str | None:
    match = re.search(rf"^\s*-\s*{re.escape(field)}:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def derive_seed(parent_seed: str, parent_branch: str, fork_event: str, branch_id: str) -> str:
    base = f"{parent_seed}|{parent_branch}|{fork_event}|{branch_id}".encode("utf-8")
    return hashlib.sha256(base).hexdigest()[:32]


def read_parent_seed(parent_branch: Path) -> str:
    seed_path = parent_branch / "random" / "seed.json"
    if not seed_path.exists():
        return "missing-parent-seed"
    try:
        data = json.loads(seed_path.read_text(encoding="utf-8"))
        return str(data.get("seed") or "missing-parent-seed")
    except json.JSONDecodeError:
        return "invalid-parent-seed"


def relative_inside(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise SystemExit(f"Path is outside world directory: {path}") from exc


def list_snapshot_sources(parent_branch: Path, world: Path) -> list[str]:
    sources: list[str] = []
    for rel in SNAPSHOT_STATE_DIRS:
        source_dir = parent_branch / rel
        if source_dir.exists():
            sources.append(relative_inside(source_dir, world))
    state_root = parent_branch / "state"
    if state_root.exists():
        for item in sorted(state_root.iterdir()):
            if item.is_file():
                sources.append(relative_inside(item, world))
    return sources


def copy_snapshot_file(source: Path, target: Path, world: Path) -> str:
    if source.is_symlink():
        raise SystemExit(f"Refusing to snapshot symlink: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return relative_inside(target, world)


def copy_branch_state_snapshot(parent_branch: Path, child_branch: Path, world: Path) -> list[str]:
    copied: list[str] = []
    for rel in SNAPSHOT_STATE_DIRS:
        source_dir = parent_branch / rel
        if not source_dir.exists():
            continue
        if not source_dir.is_dir():
            raise SystemExit(f"Snapshot source is not a directory: {source_dir}")
        for item in sorted(source_dir.rglob("*")):
            if item.is_symlink():
                raise SystemExit(f"Refusing to snapshot symlink: {item}")
            rel_item = item.relative_to(source_dir)
            target = child_branch / rel / rel_item
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            elif item.is_file():
                copied.append(copy_snapshot_file(item, target, world))

    state_root = parent_branch / "state"
    if state_root.exists():
        for item in sorted(state_root.iterdir()):
            if item.is_symlink():
                raise SystemExit(f"Refusing to snapshot symlink: {item}")
            if item.is_file():
                copied.append(copy_snapshot_file(item, child_branch / "state" / item.name, world))
    return copied


def load_draft(world: Path, active: dict[str, str], draft_id: str) -> tuple[dict, Path]:
    draft_id = validate_id(draft_id, "--draft-id")
    draft_path = world / active["branch_path"] / "runtime" / "branch-drafts" / draft_id / "draft.json"
    if not draft_path.exists():
        raise SystemExit(f"Branch draft not found: {draft_path}")
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    if draft.get("schema") != "be-a-god.branch-draft.v1":
        raise SystemExit(f"Branch draft has unexpected schema: {draft_path}")
    if draft.get("status") != "draft":
        raise SystemExit(f"Branch draft is not draft status: {draft.get('status')}")
    if draft.get("parent_branch_path") != active["branch_path"]:
        raise SystemExit("Branch draft parent path does not match active branch; switch to the draft parent branch first.")
    return draft, draft_path


def update_manifest(world: Path) -> None:
    subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "build_file_manifest.py"), str(world)], check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def rebuild_active_derivatives(world: Path) -> list[str]:
    ran: list[str] = []
    scripts = [
        ("build_timeline.py", ["--world", str(world)]),
        ("export_dashboard.py", ["--world", str(world)]),
        ("build_indexes.py", ["--world", str(world)]),
        ("build_event_graph.py", ["--world", str(world)]),
        ("build_map_layers.py", ["--world", str(world)]),
        ("update_map_state.py", ["--world", str(world)]),
    ]
    for script, args in scripts:
        subprocess.run([sys.executable, str(Path(__file__).resolve().parent / script), *args], check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ran.append(script)
    return ran


def update_story_tree(world: Path, branch_id: str, branch_path: str, parent_branch_id: str, fork_event: str) -> None:
    tree = world / "story" / "STORY-TREE.md"
    entry = f"\n- {branch_id}\n  - branch_path: `{branch_path}`\n  - parent: {parent_branch_id}\n  - fork_event: {fork_event}\n  - status: active-child\n"
    if tree.exists():
        text = tree.read_text(encoding="utf-8")
        if f"- {branch_id}\n" not in text:
            write_text(tree, text.rstrip() + "\n" + entry)
    else:
        write_text(tree, "# STORY TREE\n" + entry)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a confirmed child branch under the active branch.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--branch-id")
    parser.add_argument("--fork-event")
    parser.add_argument("--change-summary")
    parser.add_argument("--draft-id", help="Create from runtime/branch-drafts/<draft-id>/draft.json in the active branch.")
    parser.add_argument("--inherit-until", default="fork_event")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--no-switch", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-manifest", action="store_true")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    active = parse_active(world)
    parent_branch = world / active["branch_path"]
    draft = None
    draft_path = None
    if args.draft_id:
        draft, draft_path = load_draft(world, active, args.draft_id)
        args.branch_id = args.branch_id or draft["branch_id"]
        args.fork_event = args.fork_event or draft["fork_event"]
        args.change_summary = args.change_summary or draft["change_summary"]
        args.inherit_until = args.inherit_until if args.inherit_until != "fork_event" else draft.get("inherit_until", "fork_event")
        if draft.get("switch_after_create") is False:
            args.no_switch = True
    missing = [name for name in ["branch_id", "fork_event", "change_summary"] if not getattr(args, name)]
    if missing:
        raise SystemExit(f"Missing required branch fields: {', '.join(missing)}. Provide them directly or pass --draft-id.")
    branch_id = normalize_branch_id(args.branch_id)
    child_rel = f"{active['branch_path']}/branches/{branch_id}"
    child = world / child_rel
    plan = {
        "branch_id": branch_id,
        "branch_path": child_rel,
        "parent_branch_id": active.get("branch_id"),
        "parent_branch_path": active.get("branch_path"),
        "fork_event": args.fork_event,
        "inherit_until": args.inherit_until,
        "state_snapshot_policy": "copy active parent state files at fork; do not copy parent events, queues, random log, runtime, checkpoints, or sibling branches",
        "state_snapshot_sources": list_snapshot_sources(parent_branch, world),
        "switch_after_create": not args.no_switch,
        "draft_id": args.draft_id,
    }
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    if not args.confirmed:
        raise SystemExit("Refusing to create branch without --confirmed. Use --dry-run to inspect the plan.")
    if child.exists():
        raise SystemExit(f"Branch already exists: {child}")

    for rel in BRANCH_DIRS:
        (child / rel).mkdir(parents=True, exist_ok=True)

    snapshot_copied = copy_branch_state_snapshot(parent_branch, child, world)

    parent_save = parent_branch / "SAVE.md"
    parent_save_text = parent_save.read_text(encoding="utf-8") if parent_save.exists() else ""
    parent_seed = read_parent_seed(parent_branch)
    child_seed = derive_seed(parent_seed, active.get("branch_id", "main"), args.fork_event, branch_id)
    world_time = parse_field(parent_save_text, "world_time") or "unknown"
    focal_place = parse_field(parent_save_text, "focal_place") or "unknown"

    save = f"""# SAVE

## Identity

- world_id: {active.get('world_id', world.name)}
- branch_id: {branch_id}
- parent_branch_id: {active.get('branch_id')}
- parent_save: {active.get('save_path')}
- fork_event: {args.fork_event}
- inherit_until: {args.inherit_until}
- state_snapshot: copied from {active.get('branch_path')} at {args.fork_event}

## Current state

- world_time: {world_time}
- focal_place: {focal_place}
- current_scene: 新枝丫已从 `{args.fork_event}` 分出：{args.change_summary}
- player_god_role: inherited

## Open items

- unresolved_choices: []
- active_pauses: []
- watched_entities: []
- ignored_entities: []

## Source pointers

- latest_event: EVT-0001
- latest_chronicle_entry: CHR-0001
- relevant_entities: []
- relevant_locations: []

## Resume prompt

Continue this child branch. Resolve parent history only through parent pointers when needed.
"""
    write_text(child / "SAVE.md", save)
    write_text(child / "CURRENT.md", f"# CURRENT\n\n新枝丫 `{branch_id}` 已创建。{args.change_summary}\n")
    event = f"""# EVT-0001 divine revision

- id: EVT-0001
- type: divine-revision
- time: {world_time}
- branch_id: {branch_id}
- parent_branch_id: {active.get('branch_id')}
- fork_event: {args.fork_event}

## Divine change

{args.change_summary}
"""
    write_text(child / "events" / "EVT-0001-divine-revision.md", event)
    write_text(child / "chronicle" / "objective.md", f"# Objective Chronicle\n\n- CHR-0001 | {world_time} | 神明创建新枝丫：{args.change_summary} | source: {child_rel}/events/EVT-0001-divine-revision.md | event: EVT-0001\n")
    write_text(child / "chronicle" / "epic.md", f"# Epic Chronicle\n\n神明折开时间之枝，令新的可能性诞生：{args.change_summary}\n")
    write_text(child / "queues" / "events.jsonl", "")
    write_text(child / "random" / "random-log.jsonl", "")
    write_json(child / "random" / "seed.json", {"schema": "be-a-god.random-seed.v1", "branch_id": branch_id, "parent_seed_hash": hashlib.sha256(parent_seed.encode('utf-8')).hexdigest(), "seed": child_seed, "fork_event": args.fork_event, "created_at": utc_now()})
    update_story_tree(world, branch_id, child_rel, active.get("branch_id", "main"), args.fork_event)
    if draft and draft_path:
        draft["status"] = "consumed"
        draft["consumed_at"] = utc_now()
        draft["created_branch_path"] = child_rel
        draft["state_snapshot_copied"] = snapshot_copied
        write_json(draft_path, draft)

    if not args.no_switch:
        write_text(world / "ACTIVE.md", f"# ACTIVE\n\nworld_id: {active.get('world_id', world.name)}\nbranch_id: {branch_id}\nbranch_path: {child_rel}\nsave_path: {child_rel}/SAVE.md\n")
        rebuild_active_derivatives(world)
    if not args.skip_manifest:
        update_manifest(world)

    print(f"Created branch: {child}")
    print(f"Copied state snapshot files: {len(snapshot_copied)}")
    if not args.no_switch:
        print(f"Switched ACTIVE.md to: {branch_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
