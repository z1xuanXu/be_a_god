#!/usr/bin/env python3
"""Mechanically advance active branch time without generating high-semantic events."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DAYS_PER_YEAR = 360
ADVANCE_PROFILE_SCHEMA = "be-a-god.advance-profile.v1"
DEFAULT_ADVANCE_PROFILE = {
    "schema": ADVANCE_PROFILE_SCHEMA,
    "default_preset": "hybrid",
    "presets": {
        "hybrid": {
            "mode": "hybrid",
            "days": 7,
            "summary": "Advance with mixed attention: current focus stays precise, background pieces may wander.",
            "wander": True,
            "wander_limit": 3,
            "wander_exclude_ignored": False,
            "stop_on_queue": True,
            "until_next_queue": False,
        }
    },
}


def utc_id() -> str:
    return datetime.now(timezone.utc).strftime("ADV-%Y%m%d%H%M%S%f")


def parse_active(world: Path) -> dict[str, str]:
    data = {}
    for line in (world / "ACTIVE.md").read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    data.setdefault("branch_path", "story/main")
    data.setdefault("branch_id", "main")
    return data


def parse_field(text: str, field: str) -> str | None:
    match = re.search(rf"^\s*-\s*{re.escape(field)}:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def replace_or_append_field(markdown: str, field: str, value: str) -> str:
    line = f"- {field}: {value}"
    pattern = re.compile(rf"^\s*-\s*{re.escape(field)}:\s*.*$", re.MULTILINE)
    if pattern.search(markdown):
        return pattern.sub(line, markdown, count=1)
    return markdown.rstrip() + "\n" + line + "\n"


def parse_world_time(value: str | None) -> tuple[int, int]:
    if not value:
        return 1, 1
    match = re.search(r"year\s+(\d+),\s*day\s+(\d+)", value, re.IGNORECASE)
    if not match:
        return 1, 1
    return int(match.group(1)), int(match.group(2))


def add_days(year: int, day: int, days: int) -> tuple[int, int]:
    absolute = (year - 1) * DAYS_PER_YEAR + (day - 1) + days
    return absolute // DAYS_PER_YEAR + 1, absolute % DAYS_PER_YEAR + 1


def absolute_day(year: int, day: int) -> int:
    return (year - 1) * DAYS_PER_YEAR + (day - 1)


def format_world_time(year: int, day: int) -> str:
    return f"year {year}, day {day}"


def load_weather(branch: Path) -> str | None:
    log = branch / "random" / "random-log.jsonl"
    if not log.exists():
        return None
    for line in reversed([line for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("kind") == "weather":
            return str(entry.get("value"))
    return None


def load_queue(branch: Path) -> list[dict]:
    path = branch / "queues" / "events.jsonl"
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def queue_trigger_abs(entry: dict) -> int | None:
    try:
        year, day = parse_world_time(str(entry.get("trigger_time", "")))
    except SystemExit:
        return None
    return absolute_day(year, day)


def find_due_pause(queue: list[dict], start_abs: int, target_abs: int) -> dict | None:
    due = []
    for entry in queue:
        if entry.get("status") not in {None, "queued"}:
            continue
        if not entry.get("pause") and entry.get("priority") not in {"high", "critical"}:
            continue
        trigger = queue_trigger_abs(entry)
        if trigger is None:
            continue
        if start_abs < trigger <= target_abs:
            due.append((trigger, entry))
    if not due:
        return None
    return sorted(due, key=lambda item: (item[0], str(item[1].get("queue_id", ""))))[0][1]


def find_next_pause_after(queue: list[dict], start_abs: int, target_abs: int | None = None) -> dict | None:
    due = []
    for entry in queue:
        if entry.get("status") not in {None, "queued"}:
            continue
        if not entry.get("pause") and entry.get("priority") not in {"high", "critical"}:
            continue
        trigger = queue_trigger_abs(entry)
        if trigger is None or trigger <= start_abs:
            continue
        if target_abs is not None and trigger > target_abs:
            continue
        due.append((trigger, entry))
    if not due:
        return None
    return sorted(due, key=lambda item: (item[0], str(item[1].get("queue_id", ""))))[0][1]


def mark_queue_due(branch: Path, queue_id: str) -> None:
    path = branch / "queues" / "events.jsonl"
    if not path.exists():
        return
    updated = []
    changed = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            updated.append(line)
            continue
        if entry.get("queue_id") == queue_id and entry.get("status") == "queued":
            entry["status"] = "due"
            entry["due_at"] = datetime.now(timezone.utc).isoformat()
            changed = True
        updated.append(json.dumps(entry, ensure_ascii=False))
    if changed:
        path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def update_manifest(world: Path) -> None:
    script = Path(__file__).resolve().parent / "build_file_manifest.py"
    subprocess.run([sys.executable, str(script), str(world)], check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE)


def run_wandering(world: Path, run_id: str, limit: int, exclude_ignored: bool) -> dict:
    script = Path(__file__).resolve().parent / "wander_entities.py"
    args = [
        sys.executable,
        str(script),
        "--world",
        str(world),
        "--purpose",
        f"advance:{run_id}",
        "--limit",
        str(limit),
        "--confirmed",
        "--json",
    ]
    if exclude_ignored:
        args.append("--exclude-ignored")
    completed = subprocess.run(args, check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return json.loads(completed.stdout)


def load_advance_profile(world: Path) -> tuple[dict[str, Any], str]:
    path = world / "setup" / "advance-profile.json"
    if not path.exists():
        return json.loads(json.dumps(DEFAULT_ADVANCE_PROFILE)), "builtin-default"
    profile = json.loads(path.read_text(encoding="utf-8"))
    if profile.get("schema") != ADVANCE_PROFILE_SCHEMA:
        raise SystemExit(f"setup/advance-profile.json schema must be {ADVANCE_PROFILE_SCHEMA}")
    if not isinstance(profile.get("presets"), dict) or not profile["presets"]:
        raise SystemExit("setup/advance-profile.json presets must be a non-empty object")
    return profile, "setup/advance-profile.json"


def choose_preset(profile: dict[str, Any], preset_id: str | None) -> tuple[str, dict[str, Any]]:
    presets = profile.get("presets", {})
    selected = preset_id or profile.get("default_preset")
    if not selected:
        raise SystemExit("advance profile has no default_preset; pass --days or --preset")
    if selected not in presets:
        raise SystemExit(f"advance preset `{selected}` not found")
    preset = presets[selected]
    if not isinstance(preset, dict):
        raise SystemExit(f"advance preset `{selected}` must be an object")
    return selected, preset


def resolve_options(world: Path, args: argparse.Namespace) -> dict[str, Any]:
    use_profile = bool(args.preset) or args.days is None
    profile_source = None
    preset_id = None
    preset: dict[str, Any] = {}
    if use_profile:
        profile, profile_source = load_advance_profile(world)
        preset_id, preset = choose_preset(profile, args.preset)

    days = args.days if args.days is not None else preset.get("days")
    if not isinstance(days, int):
        raise SystemExit("advance days must be provided by --days or by the selected advance preset")
    summary = args.summary if args.summary else str(preset.get("summary") or "")
    wander = args.wander if args.wander is not None else bool(preset.get("wander", False))
    wander_limit = args.wander_limit if args.wander_limit is not None else int(preset.get("wander_limit", 3))
    wander_exclude_ignored = (
        args.wander_exclude_ignored
        if args.wander_exclude_ignored is not None
        else bool(preset.get("wander_exclude_ignored", False))
    )
    ignore_queue = args.ignore_queue or (use_profile and preset.get("stop_on_queue") is False)
    until_next_queue = bool(args.until_next_queue or (use_profile and preset.get("until_next_queue") is True))
    return {
        "days": days,
        "summary": summary,
        "ignore_queue": ignore_queue,
        "until_next_queue": until_next_queue,
        "wander": wander,
        "wander_limit": wander_limit,
        "wander_exclude_ignored": wander_exclude_ignored,
        "profile_source": profile_source,
        "preset_id": preset_id,
        "preset": preset,
        "used_profile": use_profile,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Mechanically advance active branch time.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--days", type=int)
    parser.add_argument("--preset", help="Use a preset from setup/advance-profile.json. If --days is omitted, the default preset is used.")
    parser.add_argument("--summary", default="")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ignore-queue", action="store_true", help="Advance the full requested span without stopping on queued pause events.")
    parser.add_argument("--until-next-queue", action="store_true", help="Resolve requested days to the next queued pause/high-priority event within the requested span.")
    wander = parser.add_mutually_exclusive_group()
    wander.add_argument("--wander", dest="wander", action="store_true", help="After a non-paused advance, apply a routine wandering tick to visible entities.")
    wander.add_argument("--no-wander", dest="wander", action="store_false", help="Disable preset wandering for this advance.")
    parser.set_defaults(wander=None)
    parser.add_argument("--wander-limit", type=int)
    ignored = parser.add_mutually_exclusive_group()
    ignored.add_argument("--wander-exclude-ignored", dest="wander_exclude_ignored", action="store_true", help="Do not move ignored entities during the optional wandering tick.")
    ignored.add_argument("--wander-include-ignored", dest="wander_exclude_ignored", action="store_false", help="Include ignored entities during the optional wandering tick.")
    parser.set_defaults(wander_exclude_ignored=None)
    parser.add_argument("--skip-manifest", action="store_true")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    options = resolve_options(world, args)
    if options["days"] < 0:
        raise SystemExit("--days must be non-negative")
    if options["wander_limit"] < 0:
        raise SystemExit("--wander-limit must be non-negative")
    active = parse_active(world)
    branch = world / active["branch_path"]
    save_path = branch / "SAVE.md"
    save = save_path.read_text(encoding="utf-8")
    old_time = parse_field(save, "world_time")
    old_year, old_day = parse_world_time(old_time)
    start_abs = absolute_day(old_year, old_day)
    queue = load_queue(branch)
    resolved_next_queue = None
    original_days = options["days"]
    if options["until_next_queue"] and not options["ignore_queue"]:
        max_year, max_day = add_days(old_year, old_day, options["days"])
        max_abs = absolute_day(max_year, max_day)
        resolved_next_queue = find_next_pause_after(queue, start_abs, max_abs)
        if resolved_next_queue:
            trigger_abs = queue_trigger_abs(resolved_next_queue)
            if trigger_abs is not None:
                options["days"] = trigger_abs - start_abs
    requested_year, requested_day = add_days(old_year, old_day, options["days"])
    requested_abs = absolute_day(requested_year, requested_day)
    due_pause = None if options["ignore_queue"] else find_due_pause(queue, start_abs, requested_abs)
    if due_pause:
        new_year, new_day = parse_world_time(due_pause["trigger_time"])
        stopped_days = absolute_day(new_year, new_day) - start_abs
    else:
        new_year, new_day = requested_year, requested_day
        stopped_days = options["days"]
    new_time = format_world_time(new_year, new_day)
    run_id = utc_id()
    run = {
        "schema": "be-a-god.advance-run.v1",
        "run_id": run_id,
        "branch_id": active.get("branch_id", "main"),
        "from": old_time,
        "requested_to": format_world_time(requested_year, requested_day),
        "to": new_time,
        "requested_days": options["days"],
        "advanced_days": stopped_days,
        "summary": options["summary"],
        "paused": bool(due_pause),
        "pause_event": due_pause,
        "advance_profile": {
            "used": options["used_profile"],
            "source": options["profile_source"],
            "preset_id": options["preset_id"],
            "preset": options["preset"] if options["used_profile"] else None,
            "until_next_queue": options["until_next_queue"],
            "original_days_before_until_next_queue": original_days,
            "resolved_next_queue_id": resolved_next_queue.get("queue_id") if resolved_next_queue else None,
            "cli_overrides": {
                "days": args.days is not None,
                "summary": bool(args.summary),
                "wander": args.wander is not None,
                "wander_limit": args.wander_limit is not None,
                "wander_exclude_ignored": args.wander_exclude_ignored is not None,
                "ignore_queue": args.ignore_queue,
            },
        },
        "wandering": {
            "enabled": options["wander"],
            "applies_after_advance": bool(options["wander"] and not due_pause),
            "skipped_reason": "queued pause must be resolved first" if options["wander"] and due_pause else None,
            "report": None,
        },
        "note": "mechanical time advance only; semantic events require model settlement",
    }
    if args.dry_run:
        print(json.dumps(run, ensure_ascii=False, indent=2))
        return 0
    if not args.confirmed:
        raise SystemExit("Refusing to advance world without --confirmed. Use --dry-run to inspect the plan.")

    run_dir = branch / "runtime" / "advance-runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    save = replace_or_append_field(save, "world_time", new_time)
    if options["summary"]:
        save = replace_or_append_field(save, "current_scene", options["summary"])
        (branch / "CURRENT.md").write_text("# CURRENT\n\n" + options["summary"].rstrip() + "\n", encoding="utf-8")
    if due_pause:
        queue_id = str(due_pause.get("queue_id", "UNKNOWN"))
        pause_text = f"""# PAUSE {queue_id}

- reason: queued-event
- world_time: {new_time}
- queue_id: {queue_id}
- priority: {due_pause.get("priority", "")}
- kind: {due_pause.get("kind", "")}
- title: {due_pause.get("title", "")}
- summary: {due_pause.get("summary", "")}

Resolve this queued event before continuing automatic advancement.
"""
        (run_dir / "pause.md").write_text(pause_text, encoding="utf-8")
        save = replace_or_append_field(save, "active_pauses", f"[{queue_id}]")
        save = replace_or_append_field(save, "current_scene", f"自动推进在 `{queue_id}` 暂停：{due_pause.get('title', '')}")
        (branch / "CURRENT.md").write_text("# CURRENT\n\n" + f"自动推进在 `{queue_id}` 暂停：{due_pause.get('title', '')}\n", encoding="utf-8")
        mark_queue_due(branch, queue_id)
    save_path.write_text(save.rstrip() + "\n", encoding="utf-8")

    dashboard_path = world / "dashboard" / "data.json"
    if dashboard_path.exists():
        dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
        dashboard["time"] = new_time
        weather = load_weather(branch)
        if weather:
            dashboard["weather"] = weather
        if due_pause:
            dashboard.setdefault("unresolved_choices", [])
            dashboard["unresolved_choices"].append(
                {
                    "queue_id": due_pause.get("queue_id"),
                    "time": new_time,
                    "title": due_pause.get("title"),
                    "priority": due_pause.get("priority"),
                }
            )
        dashboard_path.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if options["wander"] and not due_pause:
        run["wandering"]["report"] = run_wandering(world, run_id, options["wander_limit"], options["wander_exclude_ignored"])
        (run_dir / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.skip_manifest:
        update_manifest(world)
    print(f"Advanced world: {old_time} -> {new_time}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
