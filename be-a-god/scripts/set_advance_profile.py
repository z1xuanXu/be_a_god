#!/usr/bin/env python3
"""Create or update player advance presets without changing canon story state."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = "be-a-god.advance-profile.v1"
VALID_MODES = {"step", "fixed", "condition", "event-priority", "follow", "regional", "hybrid", "chronicle", "custom"}

DEFAULT_PROFILE = {
    "schema": SCHEMA,
    "default_preset": "hybrid",
    "presets": {
        "step": {
            "mode": "step",
            "days": 1,
            "summary": "Advance one short world step.",
            "wander": False,
            "wander_limit": 0,
            "wander_exclude_ignored": False,
            "stop_on_queue": True,
        },
        "hybrid": {
            "mode": "hybrid",
            "days": 7,
            "summary": "Advance with mixed attention: current focus stays precise, background pieces may wander.",
            "wander": True,
            "wander_limit": 3,
            "wander_exclude_ignored": False,
            "stop_on_queue": True,
        },
        "chronicle": {
            "mode": "chronicle",
            "days": 30,
            "summary": "Advance in chronicle view and summarize ordinary background changes.",
            "wander": True,
            "wander_limit": 5,
            "wander_exclude_ignored": False,
            "stop_on_queue": True,
        },
        "event-watch": {
            "mode": "event-priority",
            "days": 90,
            "summary": "Advance toward the next player-worthy queued or emergent event.",
            "wander": True,
            "wander_limit": 6,
            "wander_exclude_ignored": False,
            "stop_on_queue": True,
            "until_next_queue": True,
        },
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_world(path: str) -> Path:
    world = Path(path).resolve()
    if not world.exists() or not world.is_dir():
        raise SystemExit(f"world directory not found: {world}")
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    return world


def profile_path(world: Path) -> Path:
    return world / "setup" / "advance-profile.json"


def load_profile(world: Path) -> dict[str, Any]:
    path = profile_path(world)
    if not path.exists():
        return json.loads(json.dumps(DEFAULT_PROFILE))
    return json.loads(path.read_text(encoding="utf-8"))


def validate_preset(preset_id: str, preset: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(preset, dict):
        return [f"preset `{preset_id}` must be an object"]
    if preset.get("mode", "custom") not in VALID_MODES:
        errors.append(f"preset `{preset_id}` has invalid mode `{preset.get('mode')}`")
    days = preset.get("days")
    if not isinstance(days, int) or days < 0:
        errors.append(f"preset `{preset_id}` days must be a non-negative integer")
    wander = preset.get("wander")
    if not isinstance(wander, bool):
        errors.append(f"preset `{preset_id}` wander must be boolean")
    wander_limit = preset.get("wander_limit")
    if not isinstance(wander_limit, int) or wander_limit < 0:
        errors.append(f"preset `{preset_id}` wander_limit must be a non-negative integer")
    for field in ["wander_exclude_ignored", "stop_on_queue"]:
        if not isinstance(preset.get(field), bool):
            errors.append(f"preset `{preset_id}` {field} must be boolean")
    if "until_next_queue" in preset and not isinstance(preset.get("until_next_queue"), bool):
        errors.append(f"preset `{preset_id}` until_next_queue must be boolean when present")
    return errors


def validate_profile(profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if profile.get("schema") != SCHEMA:
        errors.append(f"advance profile schema must be {SCHEMA}")
    presets = profile.get("presets")
    if not isinstance(presets, dict) or not presets:
        errors.append("advance profile presets must be a non-empty object")
        return errors
    default_preset = profile.get("default_preset")
    if not isinstance(default_preset, str) or default_preset not in presets:
        errors.append("advance profile default_preset must reference an existing preset")
    for preset_id, preset in presets.items():
        if not isinstance(preset_id, str) or not preset_id.strip():
            errors.append("advance profile preset ids must be non-empty strings")
            continue
        errors.extend(validate_preset(preset_id, preset))
    return errors


def update_manifest(world: Path) -> None:
    script = Path(__file__).resolve().parent / "build_file_manifest.py"
    subprocess.run([sys.executable, str(script), str(world)], check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE)


def update_player_summary(world: Path, profile: dict[str, Any]) -> None:
    player_path = world / "PLAYER.md"
    player_text = player_path.read_text(encoding="utf-8") if player_path.exists() else "# PLAYER\n"
    default_preset = str(profile.get("default_preset") or "hybrid")
    preset = profile.get("presets", {}).get(default_preset, {})
    summary = (
        f"- advance_profile: setup/advance-profile.json\n"
        f"- advance_default_preset: {default_preset}\n"
        f"- advance_default_mode: {preset.get('mode', '')}\n"
        f"- advance_default_days: {preset.get('days', '')}\n"
        f"- advance_default_wander: {preset.get('wander', '')}\n"
        f"- advance_default_stop_on_queue: {preset.get('stop_on_queue', '')}"
    )
    block = f"## Advance profile summary\n\n{summary}\n"
    if re.search(r"^## Advance profile summary\s*$", player_text, re.MULTILINE):
        start = re.search(r"^## Advance profile summary\s*$", player_text, re.MULTILINE).start()
        next_match = re.search(r"^##\s+", player_text[start + 1 :], re.MULTILINE)
        end = start + 1 + next_match.start() if next_match else len(player_text)
        player_text = player_text[:start].rstrip() + "\n\n" + block + player_text[end:].lstrip()
    else:
        player_text = player_text.rstrip() + "\n\n" + block
    player_path.write_text(player_text.rstrip() + "\n", encoding="utf-8")


def summarize(profile: dict[str, Any]) -> dict[str, Any]:
    presets = profile.get("presets", {})
    return {
        "schema": profile.get("schema"),
        "default_preset": profile.get("default_preset"),
        "presets": {
            preset_id: {
                "mode": preset.get("mode"),
                "days": preset.get("days"),
                "wander": preset.get("wander"),
                "wander_limit": preset.get("wander_limit"),
                "wander_exclude_ignored": preset.get("wander_exclude_ignored"),
                "stop_on_queue": preset.get("stop_on_queue"),
            }
            for preset_id, preset in presets.items()
        },
    }


def build_updated_profile(args: argparse.Namespace, existing: dict[str, Any]) -> dict[str, Any]:
    profile = json.loads(json.dumps(existing))
    profile.setdefault("schema", SCHEMA)
    profile.setdefault("default_preset", DEFAULT_PROFILE["default_preset"])
    profile.setdefault("presets", {})
    for preset_id, preset in DEFAULT_PROFILE["presets"].items():
        profile["presets"].setdefault(preset_id, preset)

    if args.preset_id:
        existing_preset = dict(profile["presets"].get(args.preset_id, {}))
        if not existing_preset:
            existing_preset = {
                "mode": args.mode or "custom",
                "days": 1 if args.days is None else args.days,
                "summary": args.summary or f"Advance with preset {args.preset_id}.",
                "wander": False if args.wander is None else args.wander,
                "wander_limit": 3 if args.wander_limit is None else args.wander_limit,
                "wander_exclude_ignored": False if args.wander_exclude_ignored is None else args.wander_exclude_ignored,
                "stop_on_queue": True if args.stop_on_queue is None else args.stop_on_queue,
                "until_next_queue": False if args.until_next_queue is None else args.until_next_queue,
            }
        if args.mode is not None:
            existing_preset["mode"] = args.mode
        if args.days is not None:
            existing_preset["days"] = args.days
        if args.summary is not None:
            existing_preset["summary"] = args.summary
        if args.wander is not None:
            existing_preset["wander"] = args.wander
        if args.wander_limit is not None:
            existing_preset["wander_limit"] = args.wander_limit
        if args.wander_exclude_ignored is not None:
            existing_preset["wander_exclude_ignored"] = args.wander_exclude_ignored
        if args.stop_on_queue is not None:
            existing_preset["stop_on_queue"] = args.stop_on_queue
        if args.until_next_queue is not None:
            existing_preset["until_next_queue"] = args.until_next_queue
        if args.focus_region is not None:
            existing_preset["focus_region"] = args.focus_region
        if args.follow_entity is not None:
            existing_preset["follow_entity"] = args.follow_entity
        profile["presets"][args.preset_id] = existing_preset

    if args.default_preset:
        profile["default_preset"] = args.default_preset
    elif args.make_default and args.preset_id:
        profile["default_preset"] = args.preset_id

    profile["updated_at"] = utc_now()
    return profile


def main() -> int:
    parser = argparse.ArgumentParser(description="Set player advance presets for a be-a-god world.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--preset-id", help="Preset to create or update.")
    parser.add_argument("--default-preset", help="Set the world default preset.")
    parser.add_argument("--make-default", action="store_true", help="Make --preset-id the default preset.")
    parser.add_argument("--mode", choices=sorted(VALID_MODES), help="Informational advance mode.")
    parser.add_argument("--days", type=int, help="Default days advanced by this preset.")
    parser.add_argument("--summary", help="Default summary used when no one-off summary is provided.")
    wander = parser.add_mutually_exclusive_group()
    wander.add_argument("--wander", dest="wander", action="store_true")
    wander.add_argument("--no-wander", dest="wander", action="store_false")
    parser.set_defaults(wander=None)
    parser.add_argument("--wander-limit", type=int)
    ignored = parser.add_mutually_exclusive_group()
    ignored.add_argument("--wander-exclude-ignored", dest="wander_exclude_ignored", action="store_true")
    ignored.add_argument("--wander-include-ignored", dest="wander_exclude_ignored", action="store_false")
    parser.set_defaults(wander_exclude_ignored=None)
    queue = parser.add_mutually_exclusive_group()
    queue.add_argument("--stop-on-queue", dest="stop_on_queue", action="store_true")
    queue.add_argument("--ignore-queue", dest="stop_on_queue", action="store_false")
    parser.set_defaults(stop_on_queue=None)
    next_queue = parser.add_mutually_exclusive_group()
    next_queue.add_argument("--until-next-queue", dest="until_next_queue", action="store_true")
    next_queue.add_argument("--no-until-next-queue", dest="until_next_queue", action="store_false")
    parser.set_defaults(until_next_queue=None)
    parser.add_argument("--focus-region")
    parser.add_argument("--follow-entity")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--skip-manifest", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.days is not None and args.days < 0:
        raise SystemExit("--days must be non-negative")
    if args.wander_limit is not None and args.wander_limit < 0:
        raise SystemExit("--wander-limit must be non-negative")

    world = resolve_world(args.world)
    existing = load_profile(world)
    profile = build_updated_profile(args, existing)
    errors = validate_profile(profile)
    if errors:
        raise SystemExit("; ".join(errors))

    path = profile_path(world)
    report = {
        "ok": True,
        "dry_run": args.dry_run,
        "profile_path": str(path),
        "profile": summarize(profile),
    }
    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else json.dumps(profile, ensure_ascii=False, indent=2))
        return 0
    if not args.confirmed:
        raise SystemExit("refusing to write advance profile without --confirmed")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    update_player_summary(world, profile)
    if not args.skip_manifest:
        update_manifest(world)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else f"Updated advance profile: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
