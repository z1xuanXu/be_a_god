#!/usr/bin/env python3
"""Install this project-local skill into Codex's global skills directory after validation."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def default_skill_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def default_target_parent() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser().resolve() / "skills"
    return Path.home().resolve() / ".codex" / "skills"


def load_skill_name(skill_dir: Path) -> str:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        raise SystemExit(f"SKILL.md not found: {skill_md}")
    in_frontmatter = False
    for line in skill_md.read_text(encoding="utf-8").splitlines():
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter and line.startswith("name:"):
            name = line.split(":", 1)[1].strip()
            if name:
                return name
    raise SystemExit(f"Skill name not found in {skill_md}")


def run_install_ready(skill_dir: Path, run_smoke: bool) -> dict[str, Any]:
    script = skill_dir / "scripts" / "check_install_ready.py"
    args = [sys.executable, str(script), "--skill-dir", str(skill_dir), "--json"]
    if run_smoke:
        args.append("--run-smoke")
    completed = subprocess.run(args, check=False, capture_output=True, text=True, encoding="utf-8")
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError:
        raise SystemExit(f"check_install_ready.py did not return JSON: {completed.stdout}\n{completed.stderr}")
    if completed.returncode != 0 or not report.get("ready"):
        raise SystemExit(json.dumps({"install_ready": report, "stderr": completed.stderr}, ensure_ascii=False, indent=2))
    return report


def ignore_patterns(_: str, names: list[str]) -> set[str]:
    ignored = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
    return {name for name in names if name in ignored or name.endswith(".pyc")}


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    skill_dir = Path(args.skill_dir).expanduser().resolve()
    if not skill_dir.exists() or not skill_dir.is_dir():
        raise SystemExit(f"skill directory not found: {skill_dir}")
    skill_name = load_skill_name(skill_dir)
    target_parent = Path(args.target_parent).expanduser().resolve() if args.target_parent else default_target_parent()
    target = target_parent / skill_name
    report = run_install_ready(skill_dir, args.run_smoke)
    return {
        "ok": True,
        "dry_run": args.dry_run,
        "skill_name": skill_name,
        "skill_dir": str(skill_dir),
        "target_parent": str(target_parent),
        "target": str(target),
        "target_exists": target.exists(),
        "target_parent_exists": target_parent.exists(),
        "install_ready": {"ready": report.get("ready"), "error_count": report.get("error_count"), "warning_count": report.get("warning_count")},
        "will_copy": bool(args.confirmed and not args.dry_run),
        "policy": "Refuse if target exists. No overwrite or delete is performed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Install this local skill into Codex global skills after validation.")
    parser.add_argument("--skill-dir", default=str(default_skill_dir()))
    parser.add_argument("--target-parent", help="Defaults to CODEX_HOME/skills or ~/.codex/skills.")
    parser.add_argument("--run-smoke", action="store_true", help="Run the full smoke test before installing.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    plan = build_plan(args)
    target_parent = Path(plan["target_parent"])
    target = Path(plan["target"])
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    if not args.confirmed:
        raise SystemExit("refusing to install without --confirmed. Use --dry-run to preview.")
    if target.exists():
        raise SystemExit(f"refusing to overwrite existing skill directory: {target}")
    target_parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(Path(plan["skill_dir"]), target, ignore=ignore_patterns)
    result = {**plan, "installed": True, "target": str(target)}
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"Installed skill to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
