#!/usr/bin/env python3
"""Export lightweight dashboard data for map, pieces, pins, and status panels."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def resolve_world(path: str) -> Path:
    world = Path(path).resolve()
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    return world


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


def parse_save(branch: Path) -> dict:
    save = branch / "SAVE.md"
    text = save.read_text(encoding="utf-8") if save.exists() else ""
    return {
        "time": parse_field(text, "world_time"),
        "focal_place": parse_field(text, "focal_place"),
        "current_scene": parse_field(text, "current_scene"),
    }


def parse_entity(path: Path, world: Path, location_coords: dict[str, dict] | None = None) -> dict:
    text = path.read_text(encoding="utf-8")
    entity_id = parse_field(text, "id") or path.stem
    name = parse_field(text, "public_name") or parse_field(text, "name") or entity_id
    piece = {
        "id": entity_id,
        "kind": parse_field(text, "kind") or "character",
        "type": parse_field(text, "type"),
        "label": name,
        "location": parse_field(text, "location"),
        "status": parse_field(text, "status") or parse_field(text, "attention") or "ordinary",
        "attention": parse_field(text, "attention") or "normal",
        "source": path.relative_to(world).as_posix(),
    }
    for field in ["x", "y"]:
        value = parse_field(text, field)
        if value is None:
            continue
        try:
            piece[field] = float(value)
        except ValueError:
            piece[field] = value
    level = parse_field(text, "level")
    if level:
        piece["level"] = level
    location = (location_coords or {}).get(str(piece.get("location")))
    if location and "x" not in piece and "y" not in piece:
        piece["x"] = location.get("x")
        piece["y"] = location.get("y")
        piece["location_name"] = location.get("name")
    return piece


def load_attention(branch: Path) -> dict[str, str]:
    path = branch / "state" / "attention.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    entities = data.get("entities", {})
    if not isinstance(entities, dict):
        return {}
    states: dict[str, str] = {}
    for entity_id, payload in entities.items():
        if isinstance(payload, dict) and payload.get("state"):
            states[str(entity_id)] = str(payload["state"])
    return states


def apply_attention(pieces: list[dict], attention: dict[str, str]) -> None:
    for piece in pieces:
        state = attention.get(str(piece.get("id")))
        if not state:
            continue
        piece["attention"] = state
        if state in {"ignored", "followed"}:
            piece["status"] = state


def parse_event_pin(path: Path, world: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    event_id = parse_field(text, "id") or path.stem
    label = event_id
    for line in text.splitlines():
        if line.startswith("# "):
            label = line.lstrip("# ").strip()
            break
    return {
        "id": event_id,
        "kind": "event",
        "label": label,
        "source": path.relative_to(world).as_posix(),
        "target_id": parse_field(text, "target_id"),
    }


HIDDEN_STORY_HEADINGS = {
    "gm summary",
    "settlement plan",
    "secret",
    "secrets",
    "主持人摘要",
    "结算计划",
    "秘密",
}


def player_visible_event_text(text: str) -> str:
    """Export only player-facing prose, not event metadata or GM-only sections."""
    output: list[str] = []
    hidden = False
    for line in text.splitlines()[1:]:
        stripped = line.strip()
        if stripped.startswith("## "):
            heading = stripped[3:].strip().lower()
            hidden = heading in HIDDEN_STORY_HEADINGS
            if heading in {"settlement summary", "queued premise", "player intent", "consequences"}:
                hidden = True
            if not hidden and heading not in {"visible narration", "玩家可见叙事", "正文"}:
                output.append(stripped)
            continue
        if hidden or stripped.startswith("- "):
            continue
        output.append(line.rstrip())
    return "\n".join(output).strip()


def build_story_catalog(branch: Path, world: Path, save: dict) -> dict:
    entries = []
    for path in sorted((branch / "events").glob("EVT-*.md")):
        text = path.read_text(encoding="utf-8")
        event_id = parse_field(text, "id") or path.stem
        title = next((line[2:].strip() for line in text.splitlines() if line.startswith("# ")), event_id)
        narrative = player_visible_event_text(text)
        if not narrative:
            continue
        entries.append(
            {
                "id": event_id,
                "title": title,
                "time": parse_field(text, "time") or "unknown",
                "state": "confirmed",
                "narrative": narrative,
                "source": path.relative_to(world).as_posix(),
            }
        )
    current = {
        "id": "CURRENT-SCENE",
        "title": save.get("focal_place") or "当前剧情",
        "time": save.get("time") or "unknown",
        "state": "current",
        "narrative": save.get("current_scene") or "当前没有可显示的场景正文。",
        "source": f"{branch.relative_to(world).as_posix()}/SAVE.md",
    }
    return {"current": current, "entries": entries}


def summarize_action_request(path: Path, world: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    target = data.get("target") or {}
    return {
        "request_id": data.get("request_id") or path.parent.name,
        "status": data.get("status", "unknown"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at"),
        "action": data.get("action"),
        "target_id": target.get("id"),
        "target_kind": target.get("kind"),
        "intent": data.get("intent"),
        "suggested_command": data.get("suggested_command"),
        "source": path.relative_to(world).as_posix(),
    }


def load_action_request_priority(root: Path) -> dict[str, int]:
    path = root / "priority-order.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    request_ids = data.get("request_ids", [])
    if not isinstance(request_ids, list):
        return {}
    return {str(request_id): index for index, request_id in enumerate(request_ids)}


def list_pending_action_requests(branch: Path, world: Path, limit: int = 8) -> list[dict]:
    root = branch / "runtime" / "action-requests"
    requests = []
    priority = load_action_request_priority(root)
    if root.exists():
        for path in sorted(root.glob("*/request.json")):
            item = summarize_action_request(path, world)
            if item and item.get("status") in {"requested", "accepted"}:
                request_id = str(item.get("request_id") or "")
                if request_id in priority:
                    item["priority_index"] = priority[request_id]
                requests.append(item)
    requests.sort(
        key=lambda item: (
            0 if "priority_index" in item else 1,
            int(item.get("priority_index", 999999)),
            str(item.get("updated_at") or item.get("created_at") or ""),
        )
    )
    manual = [item for item in requests if "priority_index" in item]
    automatic = [item for item in requests if "priority_index" not in item]
    automatic.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)
    requests = manual + automatic
    return requests[:limit]


def summarize_advance_profile(world: Path) -> dict | None:
    path = world / "setup" / "advance-profile.json"
    if not path.exists():
        return None
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    presets = profile.get("presets", {})
    if not isinstance(presets, dict):
        return None
    return {
        "source": path.relative_to(world).as_posix(),
        "default_preset": profile.get("default_preset"),
        "presets": [
            {
                "id": preset_id,
                "mode": preset.get("mode"),
                "days": preset.get("days"),
                "wander": preset.get("wander"),
                "wander_limit": preset.get("wander_limit"),
                "stop_on_queue": preset.get("stop_on_queue"),
                "until_next_queue": preset.get("until_next_queue"),
                "summary": preset.get("summary"),
            }
            for preset_id, preset in sorted(presets.items())
            if isinstance(preset, dict)
        ],
    }


def summarize_narrative_profile(world: Path) -> dict | None:
    path = world / "setup" / "narrative-profile.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    profiles = data.get("profiles", {})
    default_profile = data.get("default_profile")
    if not isinstance(profiles, dict) or default_profile not in profiles:
        return None
    profile = profiles.get(default_profile)
    if not isinstance(profile, dict):
        return None
    return {
        "source": path.relative_to(world).as_posix(),
        "default_profile": default_profile,
        "label": profile.get("label"),
        "default_scale": profile.get("balance", {}).get("default_scale") if isinstance(profile.get("balance"), dict) else None,
        "priority_order": profile.get("priority_order", []),
        "required_output_layers": profile.get("output_layers", {}).get("required", []) if isinstance(profile.get("output_layers"), dict) else [],
    }


def summarize_world_rules(world: Path, limit: int = 8) -> dict:
    path = world / "setup" / "world-rules.json"
    if not path.exists():
        return {"source": path.relative_to(world).as_posix(), "active": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"source": path.relative_to(world).as_posix(), "active": [], "warning": "invalid-json"}
    active = []
    for rule in data.get("rules", []):
        if not isinstance(rule, dict) or rule.get("status") != "active":
            continue
        active.append(
            {
                "rule_id": rule.get("rule_id"),
                "text": rule.get("text"),
                "scope": rule.get("scope"),
                "target": rule.get("target"),
                "effective_time": rule.get("effective_time"),
                "tags": rule.get("tags", []),
            }
        )
    return {"source": path.relative_to(world).as_posix(), "active": active[:limit]}


def list_recent_random(branch: Path, world: Path, limit: int = 8) -> dict:
    path = branch / "random" / "random-log.jsonl"
    entries = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            entries.append(
                {
                    "index": entry.get("index"),
                    "ts": entry.get("ts") or entry.get("created_at"),
                    "purpose": entry.get("purpose"),
                    "kind": entry.get("kind"),
                    "mode": entry.get("mode"),
                    "value": entry.get("value"),
                    "entity_id": entry.get("entity_id"),
                }
            )
    recent = entries[-limit:]
    return {
        "source": path.relative_to(world).as_posix(),
        "count": len(entries),
        "latest": recent[-1] if recent else None,
        "recent": list(reversed(recent)),
    }


def latest_weather_from_random(branch: Path) -> str | None:
    path = branch / "random" / "random-log.jsonl"
    if not path.exists():
        return None
    latest = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("kind") == "weather" or entry.get("purpose") == "weather":
            latest = entry.get("value")
    return str(latest) if latest is not None else None


def summarize_attention(pieces: list[dict], limit: int = 8) -> dict:
    followed = [piece for piece in pieces if piece.get("attention") == "followed"]
    ignored = [piece for piece in pieces if piece.get("attention") == "ignored" or piece.get("status") == "ignored"]
    plot_ready = [piece for piece in pieces if piece.get("status") in {"plot-ready", "paused"}]

    def compact(items: list[dict]) -> list[dict]:
        return [
            {
                "id": item.get("id"),
                "label": item.get("label"),
                "status": item.get("status"),
                "attention": item.get("attention"),
                "source": item.get("source"),
            }
            for item in items[:limit]
        ]

    return {
        "followed_count": len(followed),
        "ignored_count": len(ignored),
        "plot_ready_count": len(plot_ready),
        "followed": compact(followed),
        "ignored": compact(ignored),
        "plot_ready": compact(plot_ready),
    }


def build_dashboard(world: Path) -> dict:
    active = parse_active(world)
    branch = world / active["branch_path"]
    save = parse_save(branch)
    try:
        coordinate_data = json.loads((world / "base" / "maps" / "coordinates.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        coordinate_data = {}
    location_coords = {str(item.get("id")): item for item in coordinate_data.get("places", []) if isinstance(item, dict) and item.get("id")}
    pieces = [parse_entity(path, world, location_coords) for path in sorted((branch / "state" / "entities").glob("*.md"))]
    apply_attention(pieces, load_attention(branch))
    pins = [parse_event_pin(path, world) for path in sorted((branch / "events").glob("EVT-*.md"))]
    pending_action_requests = list_pending_action_requests(branch, world)
    advance_profile = summarize_advance_profile(world)
    narrative_profile = summarize_narrative_profile(world)
    world_rules = summarize_world_rules(world)
    random_log = list_recent_random(branch, world)
    attention = summarize_attention(pieces)
    weather = latest_weather_from_random(branch)
    story = build_story_catalog(branch, world, save)
    return {
        "schema": "be-a-god.dashboard.v1",
        "world_id": active.get("world_id", world.name),
        "branch_id": active.get("branch_id", "main"),
        "time": save["time"],
        "weather": weather,
        "focal_place": save["focal_place"],
        "current_scene": save["current_scene"],
        "pieces": pieces,
        "pins": pins,
        "pending_action_requests": pending_action_requests,
        "advance_profile": advance_profile,
        "narrative_profile": narrative_profile,
        "world_rules": world_rules,
        "latest_random": random_log.get("latest"),
        "random_log": random_log,
        "attention": attention,
        "story": story,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export lightweight frontend dashboard data.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    world = resolve_world(args.world)
    dashboard = build_dashboard(world)
    if args.dry_run:
        print(json.dumps(dashboard, ensure_ascii=False, indent=2))
        return 0
    output = world / "dashboard" / "data.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported dashboard: {output} ({len(dashboard['pieces'])} pieces, {len(dashboard['pins'])} pins)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
