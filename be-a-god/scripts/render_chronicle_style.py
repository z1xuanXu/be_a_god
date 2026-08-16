#!/usr/bin/env python3
"""Render display-style chronicle text from the objective chronicle."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def parse_active(world: Path) -> dict[str, str]:
    data = {}
    for line in (world / "ACTIVE.md").read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    data.setdefault("branch_path", "story/main")
    return data


def epic_line(line: str) -> str:
    match = re.match(r"-\s*(CHR-\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)(?:\s*\|\s*source:.*)?$", line)
    if not match:
        return ""
    chronicle_id, time, fact = match.groups()
    return f"- {chronicle_id}｜{time}｜群星记下此事：{fact}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render epic chronicle from objective chronicle.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--style", choices=["epic", "objective-copy"], default="epic")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    active = parse_active(world)
    branch = world / active["branch_path"]
    objective = branch / "chronicle" / "objective.md"
    if not objective.exists():
        raise SystemExit(f"Objective chronicle not found: {objective}")
    lines = ["# Epic Chronicle" if args.style == "epic" else "# Chronicle Display", ""]
    for line in objective.read_text(encoding="utf-8").splitlines():
        if not line.startswith("- "):
            continue
        rendered = epic_line(line) if args.style == "epic" else line
        if rendered:
            lines.append(rendered)
    lines.append("")
    text = "\n".join(lines)
    if args.dry_run:
        print(text)
        return 0
    output = branch / "chronicle" / "epic.md"
    output.write_text(text, encoding="utf-8")
    print(f"Rendered chronicle: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
