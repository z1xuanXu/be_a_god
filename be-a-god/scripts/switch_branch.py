#!/usr/bin/env python3
"""Switch ACTIVE.md to a branch path inside the current world."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_save_branch_id(save_path: Path) -> str | None:
    if not save_path.exists():
        return None
    for line in save_path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("- branch_id:"):
            return line.split(":", 1)[1].strip()
    return None


def run_script(world: Path, script_name: str) -> None:
    script = Path(__file__).resolve().parent / script_name
    subprocess.run([sys.executable, str(script), "--world", str(world)], check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def rebuild_active_derivatives(world: Path) -> list[str]:
    scripts = [
        "build_timeline.py",
        "export_dashboard.py",
        "build_indexes.py",
        "build_map_layers.py",
        "update_map_state.py",
    ]
    for script in scripts:
        run_script(world, script)
    return scripts


def update_manifest(world: Path) -> None:
    script = Path(__file__).resolve().parent / "build_file_manifest.py"
    subprocess.run([sys.executable, str(script), str(world)], check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def main() -> int:
    parser = argparse.ArgumentParser(description="Switch active branch.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--branch-path", required=True, help="Branch path relative to world, e.g. story/main/branches/foo.")
    parser.add_argument("--skip-derived", action="store_true", help="Only update ACTIVE.md; do not rebuild dashboard, timeline, indexes, map layers, or manifest.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirmed", action="store_true")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    branch = (world / args.branch_path).resolve()
    try:
        rel = branch.relative_to(world).as_posix()
    except ValueError as exc:
        raise SystemExit(f"Branch path is outside world: {branch}") from exc
    save = branch / "SAVE.md"
    if not save.exists():
        raise SystemExit(f"Branch SAVE.md not found: {save}")
    branch_id = parse_save_branch_id(save) or branch.name
    text = f"# ACTIVE\n\nworld_id: {world.name}\nbranch_id: {branch_id}\nbranch_path: {rel}\nsave_path: {rel}/SAVE.md\n"
    if args.dry_run:
        print(text)
        return 0
    if not args.confirmed:
        raise SystemExit("Refusing to switch active branch without --confirmed. Use --dry-run to preview.")
    (world / "ACTIVE.md").write_text(text, encoding="utf-8")
    rebuilt = [] if args.skip_derived else rebuild_active_derivatives(world)
    if not args.skip_derived:
        update_manifest(world)
    suffix = "" if args.skip_derived else f" (rebuilt: {', '.join(rebuilt)})"
    print(f"Switched active branch to {branch_id}: {rel}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
