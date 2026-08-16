#!/usr/bin/env python3
"""Resolve branch-isolated random values and append auditable random logs."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


WEATHER = ["晴", "多云", "小雨", "大雨", "雾", "强风", "闷热", "寒冷"]


def parse_active(world: Path) -> dict[str, str]:
    data = {}
    for line in (world / "ACTIVE.md").read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    data.setdefault("branch_path", "story/main")
    data.setdefault("branch_id", "main")
    return data


def load_seed(branch: Path) -> str:
    path = branch / "random" / "seed.json"
    if not path.exists():
        raise SystemExit(f"seed.json not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return str(data.get("seed") or "")


def log_count(log_path: Path) -> int:
    if not log_path.exists():
        return 0
    return sum(1 for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip())


def random_int(seed: str, index: int, purpose: str, low: int, high: int) -> int:
    if low > high:
        raise SystemExit("--min cannot be greater than --max")
    material = f"{seed}|{index}|{purpose}".encode("utf-8")
    value = int(hashlib.sha256(material).hexdigest(), 16)
    return low + (value % (high - low + 1))


def parse_options(raw: str | None) -> list[str]:
    if not raw:
        return []
    stripped = raw.strip()
    if stripped.startswith("["):
        return [str(item) for item in json.loads(stripped)]
    return [item.strip() for item in stripped.split(",") if item.strip()]


def update_dashboard_weather(world: Path, value: str, entry: dict) -> None:
    dashboard_path = world / "dashboard" / "data.json"
    if not dashboard_path.exists():
        return
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    dashboard["weather"] = value
    dashboard["latest_random"] = {
        "index": entry["index"],
        "purpose": entry["purpose"],
        "kind": entry["kind"],
        "mode": entry["mode"],
        "value": entry["value"],
    }
    active = parse_active(world)
    log_path = world / active["branch_path"] / "random" / "random-log.jsonl"
    entries = []
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            entries.append(
                {
                    "index": item.get("index"),
                    "ts": item.get("ts") or item.get("created_at"),
                    "purpose": item.get("purpose"),
                    "kind": item.get("kind"),
                    "mode": item.get("mode"),
                    "value": item.get("value"),
                    "entity_id": item.get("entity_id"),
                }
            )
    recent = entries[-8:]
    dashboard["random_log"] = {
        "source": f"{active['branch_path']}/random/random-log.jsonl",
        "count": len(entries),
        "latest": recent[-1] if recent else None,
        "recent": list(reversed(recent)),
    }
    dashboard_path.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_manifest(world: Path) -> None:
    script = Path(__file__).resolve().parent / "build_file_manifest.py"
    subprocess.run([sys.executable, str(script), str(world)], check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE)


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve deterministic branch random value.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--purpose", required=True)
    parser.add_argument("--kind", choices=["weather", "int", "choice"], default="int")
    parser.add_argument("--min", type=int, default=1)
    parser.add_argument("--max", type=int, default=100)
    parser.add_argument("--options", help="Comma list or JSON array for choice kind.")
    parser.add_argument("--override", help="Player override value; logged as override.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-dashboard", action="store_true", help="Do not sync weather results into dashboard/data.json.")
    parser.add_argument("--skip-manifest", action="store_true", help="Do not refresh system/file-manifest.json after writing.")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    active = parse_active(world)
    branch = world / active["branch_path"]
    seed = load_seed(branch)
    log_path = branch / "random" / "random-log.jsonl"
    index = log_count(log_path) + 1

    if args.override is not None:
        value = args.override
        mode = "override"
    elif args.kind == "weather":
        value = WEATHER[random_int(seed, index, args.purpose, 0, len(WEATHER) - 1)]
        mode = "random"
    elif args.kind == "choice":
        options = parse_options(args.options)
        if not options:
            raise SystemExit("--options is required for choice kind")
        value = options[random_int(seed, index, args.purpose, 0, len(options) - 1)]
        mode = "random"
    else:
        value = random_int(seed, index, args.purpose, args.min, args.max)
        mode = "random"

    entry = {
        "schema": "be-a-god.random-log.v1",
        "index": index,
        "ts": datetime.now(timezone.utc).isoformat(),
        "world_id": active.get("world_id", world.name),
        "branch_id": active.get("branch_id", "main"),
        "purpose": args.purpose,
        "kind": args.kind,
        "mode": mode,
        "value": value,
    }
    if args.dry_run:
        print(json.dumps(entry, ensure_ascii=False, indent=2))
        return 0
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    if args.kind == "weather" and not args.skip_dashboard:
        update_dashboard_weather(world, str(value), entry)
    if not args.skip_manifest:
        update_manifest(world)
    print(json.dumps(entry, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
