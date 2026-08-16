#!/usr/bin/env python3
"""Set character attention state: followed, normal, or ignored."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
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


def refresh_dashboard_and_manifest(world: Path) -> None:
    scripts = Path(__file__).resolve().parent
    subprocess.run([sys.executable, str(scripts / "export_dashboard.py"), "--world", str(world)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, str(scripts / "build_file_manifest.py"), str(world)], check=True, stdout=subprocess.DEVNULL)


def main() -> int:
    parser = argparse.ArgumentParser(description="Set entity attention state.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--state", required=True, choices=["followed", "normal", "ignored"])
    parser.add_argument("--reason", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirmed", action="store_true")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    active = parse_active(world)
    branch = world / active["branch_path"]
    state_path = branch / "state" / "attention.json"
    data = {"schema": "be-a-god.attention.v1", "entities": {}}
    if state_path.exists():
        data = json.loads(state_path.read_text(encoding="utf-8"))
        data.setdefault("entities", {})
    data["entities"][args.target_id] = {
        "state": args.state,
        "reason": args.reason,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if args.dry_run:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    if not args.confirmed:
        raise SystemExit("Refusing to set attention without --confirmed. Use --dry-run to preview.")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    refresh_dashboard_and_manifest(world)
    print(f"Set attention: {args.target_id} -> {args.state}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
