#!/usr/bin/env python3
"""Read-only install readiness check for the non-frontend be-a-god skill."""

from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path

SKILL_NAME = "be-a-god"
REQUIRED_DIRS = ["agents", "assets/world-template", "assets/narrative-templates", "references", "scripts"]
REQUIRED_FILES = [
    "SKILL.md", "agents/openai.yaml", "references/storage-contract.md",
    "references/game-master-protocol.md", "references/narrative-quality.md",
    "references/narrative-template-guide.md", "references/script-catalog.md",
    "references/validation-scenarios.md", "references/player-quickstart.md",
    "assets/world-template/WORLD-BRIEF.template.md", "assets/world-template/SAVE.template.md",
    "assets/world-template/content-profile.template.json", "assets/world-template/advance-profile.template.json",
    "assets/world-template/narrative-profile.template.json", "assets/world-template/llm-api.config.template.json",
    "assets/narrative-templates/interaction-result.template.json",
    "assets/narrative-templates/queued-event-result.template.json",
    "assets/narrative-templates/character-seed.template.json",
    "assets/narrative-templates/faction-pressure.template.json",
    "assets/narrative-templates/divine-intervention-result.template.json",
    "scripts/init_world.py", "scripts/create_demo_world.py", "scripts/call_llm.py",
    "scripts/external_play_turn.py", "scripts/validate_world.py",
    "scripts/validate_world_brief.py", "scripts/validate_settlement_result.py",
    "scripts/smoke_test.py",
]


def result(level: str, check: str, message: str, **extra: object) -> dict:
    return {"level": level, "check": check, "message": message, **extra}


def check(skill_dir: Path, run_smoke: bool) -> dict:
    results: list[dict] = []
    skill = skill_dir / "SKILL.md"
    text = skill.read_text(encoding="utf-8") if skill.exists() else ""
    if text.startswith("---\nname: be-a-god\n"):
        results.append(result("ok", "metadata", "skill name matches folder"))
    else:
        results.append(result("error", "metadata", "SKILL.md is missing be-a-god frontmatter"))
    if "assets/frontend" not in text.lower() and "serve_frontend" not in text.lower():
        results.append(result("ok", "scope", "skill has no web UI dependency"))
    else:
        results.append(result("error", "scope", "SKILL.md still depends on removed web UI files"))
    for rel in REQUIRED_DIRS:
        results.append(result("ok" if (skill_dir / rel).is_dir() else "error", "directory", f"{'found' if (skill_dir / rel).is_dir() else 'missing'} {rel}"))
    for rel in REQUIRED_FILES:
        results.append(result("ok" if (skill_dir / rel).is_file() else "error", "file", f"{'found' if (skill_dir / rel).is_file() else 'missing'} {rel}"))
    scripts = sorted((skill_dir / "scripts").glob("*.py")) if (skill_dir / "scripts").is_dir() else []
    failures = []
    for path in scripts:
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            failures.append(f"{path.name}: {exc.msg}")
    results.append(result("ok" if not failures else "error", "scripts", "all Python scripts compile" if not failures else "Python compilation failed", failures=failures))
    if run_smoke:
        import subprocess, sys
        completed = subprocess.run([sys.executable, str(skill_dir / "scripts/smoke_test.py")], capture_output=True, text=True)
        results.append(result("ok" if completed.returncode == 0 else "error", "smoke", "smoke_test.py passed" if completed.returncode == 0 else "smoke_test.py failed", stdout=completed.stdout.strip(), stderr=completed.stderr.strip()))
    errors = sum(item["level"] == "error" for item in results)
    warnings = sum(item["level"] == "warning" for item in results)
    return {"skill_dir": str(skill_dir), "skill_name": SKILL_NAME, "ready": errors == 0, "error_count": errors, "warning_count": warnings, "results": results}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check non-frontend be-a-god package readiness.")
    parser.add_argument("--skill-dir", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--run-smoke", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = check(Path(args.skill_dir).resolve(), args.run_smoke)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else report)
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
