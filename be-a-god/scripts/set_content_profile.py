#!/usr/bin/env python3
"""Update content-boundary preferences without changing canon events."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PRESETS = {
    "gentle": {
        "presentation": {"soften_on_request": True, "facts_remain_intact_when_softened": True},
        "topics": {"violence": "soften", "politics": "summary", "religion": "allow", "romance": "summary", "horror": "soften"},
    },
    "standard": {
        "presentation": {"soften_on_request": True, "facts_remain_intact_when_softened": True},
        "topics": {"violence": "summary", "politics": "allow", "religion": "allow", "romance": "summary", "horror": "summary"},
    },
    "unsoftened": {
        "presentation": {"soften_on_request": True, "facts_remain_intact_when_softened": True},
        "topics": {"violence": "allow", "politics": "allow", "religion": "allow", "romance": "allow", "horror": "allow"},
    },
    "custom": {
        "presentation": {"soften_on_request": True, "facts_remain_intact_when_softened": True},
        "topics": {},
    },
}

VALID_TOPIC_MODES = {"allow", "summary", "soften", "avoid"}
SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_world(path: str) -> Path:
    world = Path(path).resolve()
    if not world.exists() or not world.is_dir():
        raise SystemExit(f"world directory not found: {world}")
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    return world


def validate_id(value: str, field: str) -> str:
    if not SAFE_ID_PATTERN.fullmatch(value):
        raise SystemExit(f"{field} must contain only letters, numbers, underscores, or hyphens: {value}")
    return value


def read_json_or_default(path: Path) -> dict:
    if not path.exists():
        return {"preset": "standard", **PRESETS["standard"], "player_absolute_bans": []}
    return json.loads(path.read_text(encoding="utf-8"))


def parse_topic(raw: str) -> tuple[str, str]:
    if "=" not in raw:
        raise SystemExit(f"--topic must use name=mode, got: {raw}")
    name, mode = raw.split("=", 1)
    name = name.strip()
    mode = mode.strip()
    if not name:
        raise SystemExit("--topic name cannot be blank")
    if mode not in VALID_TOPIC_MODES:
        raise SystemExit(f"invalid topic mode `{mode}`; expected one of {sorted(VALID_TOPIC_MODES)}")
    return name, mode


def update_player_summary(player_path: Path, profile: dict) -> None:
    player_text = player_path.read_text(encoding="utf-8") if player_path.exists() else "# PLAYER\n"
    absolute_bans = profile.get("player_absolute_bans", [])
    absolute_bans_text = "; ".join(str(item) for item in absolute_bans if str(item).strip()) or "none"
    summary = (
        f"- content_profile: setup/content-profile.json\n"
        f"- content_preset: {profile.get('preset', 'standard')}\n"
        f"- content_topics_summary: {json.dumps(profile.get('topics', {}), ensure_ascii=False, sort_keys=True)}\n"
        f"- content_absolute_bans: {absolute_bans_text}\n"
        f"- content_absolute_bans_count: {len(absolute_bans)}"
    )
    block = f"## Content profile summary\n\n{summary}\n"
    if re.search(r"^## Content profile summary\s*$", player_text, re.MULTILINE):
        start = re.search(r"^## Content profile summary\s*$", player_text, re.MULTILINE).start()
        next_match = re.search(r"^##\s+", player_text[start + 1 :], re.MULTILINE)
        end = start + 1 + next_match.start() if next_match else len(player_text)
        player_text = player_text[:start].rstrip() + "\n\n" + block + player_text[end:].lstrip()
    else:
        player_text = player_text.rstrip() + "\n\n" + block
    player_path.write_text(player_text.rstrip() + "\n", encoding="utf-8")


def update_manifest(world: Path) -> None:
    script = Path(__file__).resolve().parent / "build_file_manifest.py"
    subprocess.run([sys.executable, str(script), str(world)], check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE)


def build_profile(args: argparse.Namespace, existing: dict) -> dict:
    preset = args.preset or existing.get("preset", "standard")
    base = {
        "schema": "be-a-god.content-profile.v1",
        "preset": preset,
        "presentation": dict(PRESETS.get(preset, PRESETS["custom"])["presentation"]),
        "topics": dict(PRESETS.get(preset, PRESETS["custom"])["topics"]),
        "player_absolute_bans": list(existing.get("player_absolute_bans", [])),
        "updated_at": utc_now(),
    }
    if preset == "custom":
        base["topics"].update(existing.get("topics", {}))
    for raw in args.topic or []:
        name, mode = parse_topic(raw)
        base["topics"][name] = mode
    if args.ban is not None:
        base["player_absolute_bans"] = args.ban
    if args.add_ban:
        seen = set(base["player_absolute_bans"])
        for ban in args.add_ban:
            if ban not in seen:
                base["player_absolute_bans"].append(ban)
                seen.add(ban)
    if args.soften_on_request is not None:
        base["presentation"]["soften_on_request"] = args.soften_on_request
    base["presentation"]["facts_remain_intact_when_softened"] = True
    return base


def write_soften_request(world: Path, args: argparse.Namespace, profile: dict) -> Path:
    active = {}
    for line in (world / "ACTIVE.md").read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            active[key.strip()] = value.strip()
    branch_path = active.get("branch_path", "story/main")
    request_id = validate_id(args.soften_request_id or datetime.now(timezone.utc).strftime("SOFT-%Y%m%d-%H%M%S"), "--soften-request-id")
    output = world / branch_path / "runtime" / "soften-requests" / f"{request_id}.json"
    payload = {
        "schema": "be-a-god.soften-request.v1",
        "request_id": request_id,
        "created_at": utc_now(),
        "target": args.soften_target,
        "instruction": "Soften presentation only. Do not change canon facts, event nodes, random logs, chronicle entries, deaths, damage, or consequences.",
        "content_profile_summary": {
            "preset": profile.get("preset"),
            "topics": profile.get("topics", {}),
            "player_absolute_bans": profile.get("player_absolute_bans", []),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Set be-a-god content boundary preferences.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--preset", choices=sorted(PRESETS), help="Content profile preset.")
    parser.add_argument("--topic", action="append", help="Topic rule as name=allow|summary|soften|avoid.")
    parser.add_argument("--ban", action="append", help="Replace absolute bans with this repeated list.")
    parser.add_argument("--add-ban", action="append", help="Append an absolute ban.")
    parser.add_argument("--soften-on-request", dest="soften_on_request", action="store_true")
    parser.add_argument("--no-soften-on-request", dest="soften_on_request", action="store_false")
    parser.set_defaults(soften_on_request=None)
    parser.add_argument("--soften-target", help="Create a presentation-only soften request for a scene/event/paragraph.")
    parser.add_argument("--soften-request-id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--skip-manifest", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    world = resolve_world(args.world)
    profile_path = world / "setup" / "content-profile.json"
    existing = read_json_or_default(profile_path)
    profile = build_profile(args, existing)
    report = {
        "ok": True,
        "dry_run": args.dry_run,
        "profile_path": str(profile_path),
        "profile": profile,
        "soften_request": None,
    }
    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else json.dumps(profile, ensure_ascii=False, indent=2))
        return 0
    if not args.confirmed:
        raise SystemExit("refusing to write content profile without --confirmed")

    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    update_player_summary(world / "PLAYER.md", profile)
    if args.soften_target:
        report["soften_request"] = str(write_soften_request(world, args, profile))
    if not args.skip_manifest:
        update_manifest(world)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else f"Updated content profile: {profile_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
