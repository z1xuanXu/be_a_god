#!/usr/bin/env python3
"""Prepare a compact resume packet for continuing a world in a new conversation."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = "be-a-god.resume-packet.v1"
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


def parse_active(world: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in (world / "ACTIVE.md").read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    data.setdefault("branch_id", "main")
    data.setdefault("branch_path", "story/main")
    data.setdefault("save_path", f"{data['branch_path']}/SAVE.md")
    return data


def relative_inside(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise SystemExit(f"path is outside world directory: {path}") from exc


def validate_id(value: str, field: str) -> str:
    if not SAFE_ID_PATTERN.fullmatch(value):
        raise SystemExit(f"{field} must contain only letters, numbers, underscores, or hyphens: {value}")
    return value


def parse_field(text: str, field: str) -> str | None:
    match = re.search(rf"^\s*-\s*{re.escape(field)}:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def compact_save(save_path: Path) -> dict[str, Any]:
    text = save_path.read_text(encoding="utf-8") if save_path.exists() else ""
    return {
        "source": None,
        "world_time": parse_field(text, "world_time"),
        "focal_place": parse_field(text, "focal_place"),
        "current_scene": parse_field(text, "current_scene"),
        "active_pauses": parse_field(text, "active_pauses"),
        "context_pressure": parse_field(text, "context_pressure"),
    }


def load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def summarize_world_rules(world: Path, limit: int = 8) -> dict[str, Any]:
    path = world / "setup" / "world-rules.json"
    data = load_json_if_exists(path) or {}
    active = []
    for rule in data.get("rules", []):
        if isinstance(rule, dict) and rule.get("status") == "active":
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
    return {"source": relative_inside(path, world), "active": active[:limit], "omitted": max(0, len(active) - limit)}


def summarize_dashboard(world: Path) -> dict[str, Any]:
    path = world / "dashboard" / "data.json"
    data = load_json_if_exists(path) or {}
    return {
        "source": relative_inside(path, world),
        "piece_count": len(data.get("pieces", [])) if isinstance(data.get("pieces", []), list) else 0,
        "pin_count": len(data.get("pins", [])) if isinstance(data.get("pins", []), list) else 0,
        "pending_action_count": len(data.get("pending_action_requests", [])) if isinstance(data.get("pending_action_requests", []), list) else 0,
        "advance_profile": data.get("advance_profile"),
    }


def latest_handoff(branch: Path, world: Path) -> dict[str, Any] | None:
    root = branch / "runtime" / "context-handoffs"
    candidates = sorted(root.glob("*/handoff.json")) if root.exists() else []
    if not candidates:
        return None
    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    data = load_json_if_exists(latest) or {}
    markdown = latest.with_name("HANDOFF.md")
    save_markdown = latest.with_name("存档.md")
    return {
        "handoff_id": data.get("handoff_id") or latest.parent.name,
        "source": relative_inside(latest, world),
        "markdown": relative_inside(markdown, world) if markdown.exists() else None,
        "save_markdown": relative_inside(save_markdown, world) if save_markdown.exists() else None,
        "created_at": data.get("created_at"),
        "status": data.get("status"),
        "first_read": data.get("first_read", []),
    }


def short_text(path: Path, world: Path, max_chars: int) -> dict[str, Any]:
    if not path.exists():
        return {"source": relative_inside(path, world), "text": "", "missing": True}
    text = path.read_text(encoding="utf-8")
    return {
        "source": relative_inside(path, world),
        "text": text[:max_chars],
        "truncated": len(text) > max_chars,
    }


def build_packet(args: argparse.Namespace) -> tuple[dict[str, Any], Path, Path]:
    world = resolve_world(args.world)
    active = parse_active(world)
    branch = world / active["branch_path"]
    save_path = world / active["save_path"]
    save = compact_save(save_path)
    save["source"] = relative_inside(save_path, world)
    handoff = latest_handoff(branch, world)
    first_read = ["ACTIVE.md", active["save_path"], "PLAYER.md"]
    if handoff and handoff.get("save_markdown"):
        first_read.append(handoff["save_markdown"])
    else:
        first_read.append(f"{active['branch_path']}/CURRENT.md")
    first_read.extend(["setup/world-rules.json", "dashboard/data.json"])

    packet_id = validate_id(args.resume_id or "RES-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f"), "--resume-id")
    packet_dir = branch / "runtime" / "resume-packets" / packet_id
    packet_json = packet_dir / "resume.json"
    packet_md = packet_dir / "resume.md"
    if (packet_json.exists() or packet_md.exists()) and not args.dry_run:
        raise SystemExit(f"resume packet already exists: {packet_id}")

    packet = {
        "schema": SCHEMA,
        "resume_id": packet_id,
        "status": "draft" if args.dry_run else "recorded",
        "created_at": utc_now(),
        "world_id": active.get("world_id") or world.name,
        "branch_id": active.get("branch_id", "main"),
        "branch_path": active.get("branch_path", "story/main"),
        "save": save,
        "player": short_text(world / "PLAYER.md", world, args.player_chars),
        "latest_handoff": handoff,
        "world_rules": summarize_world_rules(world, args.rule_limit),
        "dashboard": summarize_dashboard(world),
        "first_read": first_read,
        "context_policy": {
            "canonical_effect": "none",
            "instruction": "Start the new conversation from first_read and this packet. Do not read full chapters or sibling branches unless a listed source pointer requires it.",
        },
    }
    return packet, packet_json, packet_md


def render_markdown(packet: dict[str, Any]) -> str:
    rules = packet.get("world_rules", {}).get("active", [])
    lines = [
        f"# Resume Packet {packet['resume_id']}",
        "",
        f"- schema: {packet['schema']}",
        f"- status: {packet['status']}",
        f"- created_at: {packet['created_at']}",
        f"- world_id: {packet['world_id']}",
        f"- branch_id: {packet['branch_id']}",
        f"- world_time: {packet['save'].get('world_time') or 'unknown'}",
        f"- focal_place: {packet['save'].get('focal_place') or 'unknown'}",
        "",
        "## First read",
        "",
    ]
    lines.extend(f"- {source}" for source in packet.get("first_read", []))
    lines.extend(["", "## Active rules", ""])
    if not rules:
        lines.append("- No active structured rules.")
    for rule in rules:
        lines.append(f"- {rule.get('rule_id')} [{rule.get('scope')}]: {rule.get('text')}")
    lines.extend(["", "## Context policy", "", packet["context_policy"]["instruction"], ""])
    return "\n".join(lines)


def refresh_manifest(world: Path) -> None:
    script = Path(__file__).resolve().parent / "build_file_manifest.py"
    subprocess.run([sys.executable, str(script), str(world)], check=True, stdout=subprocess.DEVNULL)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a compact resume packet for a be-a-god world.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--resume-id")
    parser.add_argument("--player-chars", type=int, default=1200)
    parser.add_argument("--rule-limit", type=int, default=8)
    parser.add_argument("--skip-manifest", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.player_chars < 0 or args.rule_limit < 0:
        raise SystemExit("--player-chars and --rule-limit must be >= 0")
    packet, packet_json, packet_md = build_packet(args)
    if args.dry_run:
        print(json.dumps(packet, ensure_ascii=False, indent=2))
        return 0
    if not args.confirmed:
        raise SystemExit("refusing to write resume packet without --confirmed")
    packet_json.parent.mkdir(parents=True, exist_ok=True)
    packet_json.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    packet_md.write_text(render_markdown(packet), encoding="utf-8")
    if not args.skip_manifest:
        refresh_manifest(resolve_world(args.world))
    result = {
        "ok": True,
        "resume_id": packet["resume_id"],
        "resume_json": str(packet_json),
        "resume_markdown": str(packet_md),
        "first_read": packet["first_read"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"Wrote resume packet: {packet_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
