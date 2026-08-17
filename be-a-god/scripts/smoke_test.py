#!/usr/bin/env python3
"""Compact integration smoke test for the non-frontend be-a-god skill."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True)
    if completed.returncode:
        raise SystemExit(f"command failed: {' '.join(args)}\n{completed.stdout}\n{completed.stderr}")
    return completed


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="be-a-god-smoke-") as temp:
        root = Path(temp)
        draft_dir = root / "drafts"
        run([
            str(SCRIPTS / "create_world_brief.py"), "--world-id", "river-world", "--draft-dir", str(draft_dir),
            "--world-premise", "Two plains surround a central sea and dangerous marsh.",
            "--starting-era", "early iron age", "--starting-region", "west plain and east plain",
            "--god-role", "god of crossings", "--tone", "grounded historical causality",
            "--initial-culture", "two isolated settlements", "--ai-fill", "characters",
            "--content-profile", "standard", "--json",
        ], root)
        brief = draft_dir / "river-world.WORLD-BRIEF.md"
        brief.write_text(brief.read_text(encoding="utf-8").replace("Status: draft", "Status: confirmed"), encoding="utf-8")
        run([str(SCRIPTS / "validate_world_brief.py"), str(brief), "--require-confirmed", "--json"], root)
        run([str(SCRIPTS / "init_world.py"), "--worlds-dir", str(root / "worlds"), "--world-id", "river-world", "--brief", str(brief), "--confirmed"], root)
        world = root / "worlds" / "river-world"
        run([str(SCRIPTS / "build_indexes.py"), "--world", str(world)], root)
        run([str(SCRIPTS / "build_map_layers.py"), "--world", str(world)], root)
        run([str(SCRIPTS / "build_timeline.py"), "--world", str(world)], root)
        run([str(SCRIPTS / "export_dashboard.py"), "--world", str(world)], root)
        report = json.loads(run([str(SCRIPTS / "validate_world.py"), "--world", str(world), "--json"], root).stdout)
        if not report.get("ok"):
            raise SystemExit(json.dumps(report, ensure_ascii=False))
        zones = json.loads((world / "base/maps/hierarchy.json").read_text(encoding="utf-8")).get("terrain_zones", [])
        if [zone.get("terrain") for zone in zones] != ["plain", "coast", "marsh", "plain"]:
            raise SystemExit("creation map did not materialize ordered terrain zones")
        print(json.dumps({"ok": True, "world": str(world), "scripts": "core smoke passed"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
