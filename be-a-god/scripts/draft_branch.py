#!/usr/bin/env python3
"""Create a branch draft under the active branch runtime folder."""

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
SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


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
    data: dict[str, str] = {}
    for line in (world / "ACTIVE.md").read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    data.setdefault("branch_path", "story/main")
    data.setdefault("branch_id", "main")
    data.setdefault("save_path", f"{data['branch_path']}/SAVE.md")
    return data


def read_parent_seed(parent_branch: Path) -> str:
    seed_path = parent_branch / "random" / "seed.json"
    if not seed_path.exists():
        return "missing-parent-seed"
    try:
        data = json.loads(seed_path.read_text(encoding="utf-8"))
        return str(data.get("seed") or "missing-parent-seed")
    except json.JSONDecodeError:
        return "invalid-parent-seed"


def derive_seed(parent_seed: str, parent_branch: str, fork_event: str, branch_id: str) -> str:
    base = f"{parent_seed}|{parent_branch}|{fork_event}|{branch_id}".encode("utf-8")
    return hashlib.sha256(base).hexdigest()[:32]


def update_manifest(world: Path) -> None:
    subprocess.run([sys.executable, str(SCRIPTS / "build_file_manifest.py"), str(world)], check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def build_draft(args: argparse.Namespace, world: Path) -> dict:
    active = parse_active(world)
    parent_branch = world / active["branch_path"]
    branch_id = normalize_branch_id(args.branch_id)
    draft_id = validate_id(args.draft_id or f"BRD-{branch_id}", "--draft-id")
    child_rel = f"{active['branch_path']}/branches/{branch_id}"
    parent_seed = read_parent_seed(parent_branch)
    child_seed = derive_seed(parent_seed, active.get("branch_id", "main"), args.fork_event, branch_id)
    return {
        "schema": "be-a-god.branch-draft.v1",
        "draft_id": draft_id,
        "status": "draft",
        "created_at": utc_now(),
        "world_id": active.get("world_id", world.name),
        "parent_branch_id": active.get("branch_id", "main"),
        "parent_branch_path": active["branch_path"],
        "parent_save": active.get("save_path"),
        "branch_id": branch_id,
        "branch_path": child_rel,
        "fork_event": args.fork_event,
        "inherit_until": args.inherit_until,
        "change_summary": args.change_summary,
        "switch_after_create": not args.no_switch,
        "seed_preview": {
            "parent_seed_hash": hashlib.sha256(parent_seed.encode("utf-8")).hexdigest(),
            "child_seed": child_seed,
            "rule": "sha256(parent_seed|parent_branch|fork_event|branch_id)[:32]",
        },
        "read_policy": "draft only; do not scan sibling branches; create confirmed branch only after player approval",
    }


def render_markdown(draft: dict) -> str:
    return f"""# Branch Draft {draft['draft_id']}

- schema: {draft['schema']}
- draft_id: {draft['draft_id']}
- status: {draft['status']}
- world_id: {draft['world_id']}
- parent_branch_id: {draft['parent_branch_id']}
- parent_branch_path: {draft['parent_branch_path']}
- parent_save: {draft['parent_save']}
- branch_id: {draft['branch_id']}
- branch_path: {draft['branch_path']}
- fork_event: {draft['fork_event']}
- inherit_until: {draft['inherit_until']}
- switch_after_create: {draft['switch_after_create']}

## Change summary

{draft['change_summary']}

## Seed derivation

- parent_seed_hash: {draft['seed_preview']['parent_seed_hash']}
- child_seed: {draft['seed_preview']['child_seed']}
- rule: {draft['seed_preview']['rule']}

## Confirmation boundary

This draft is support state only. It does not create confirmed history, branch files, event nodes, chronicle entries, or ACTIVE.md changes. Create the branch only after player approval.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a branch draft without changing canon.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--branch-id", required=True)
    parser.add_argument("--fork-event", required=True)
    parser.add_argument("--change-summary", required=True)
    parser.add_argument("--inherit-until", default="fork_event")
    parser.add_argument("--draft-id")
    parser.add_argument("--no-switch", action="store_true")
    parser.add_argument("--skip-manifest", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    draft = build_draft(args, world)
    active = parse_active(world)
    draft_dir = world / active["branch_path"] / "runtime" / "branch-drafts" / draft["draft_id"]
    report = {
        "ok": True,
        "status": "dry-run" if args.dry_run else "drafted",
        "draft_id": draft["draft_id"],
        "draft_dir": draft_dir.relative_to(world).as_posix(),
        "draft_json": (draft_dir / "draft.json").relative_to(world).as_posix(),
        "draft_md": (draft_dir / "draft.md").relative_to(world).as_posix(),
        "branch_id": draft["branch_id"],
        "branch_path": draft["branch_path"],
    }
    if args.dry_run:
        print(json.dumps({**report, "draft": draft}, ensure_ascii=False, indent=2) if args.json else render_markdown(draft))
        return 0
    if not args.confirmed:
        raise SystemExit("Refusing to write branch draft without --confirmed. Use --dry-run to inspect.")
    if draft_dir.exists():
        raise SystemExit(f"Branch draft already exists: {draft_dir}")
    draft_dir.mkdir(parents=True, exist_ok=False)
    (draft_dir / "draft.json").write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (draft_dir / "draft.md").write_text(render_markdown(draft).rstrip() + "\n", encoding="utf-8")
    if not args.skip_manifest:
        update_manifest(world)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else f"Wrote branch draft: {draft_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
