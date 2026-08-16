#!/usr/bin/env python3
"""Create a branch-local player action request without changing canon."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = "be-a-god.action-request.v1"
SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
VALID_ACTIONS = {
    "observe",
    "speak",
    "intervene",
    "advance-time",
    "weather-override",
    "set-rule",
    "ignore",
    "follow",
    "branch",
    "terrain-brush",
    "custom",
}
TARGET_REQUIRED = {"observe", "speak", "intervene", "ignore", "follow"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_active(world: Path) -> dict[str, str]:
    active_path = world / "ACTIVE.md"
    if not active_path.exists():
        raise SystemExit(f"ACTIVE.md not found in world directory: {world}")
    data = {}
    for line in active_path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    data.setdefault("branch_path", "story/main")
    data.setdefault("branch_id", "main")
    data.setdefault("save_path", f"{data['branch_path']}/SAVE.md")
    return data


def parse_save_field(save_text: str, field: str) -> str | None:
    match = re.search(rf"^\s*-\s*{re.escape(field)}:\s*(.+?)\s*$", save_text, re.MULTILINE)
    return match.group(1).strip() if match else None


def resolve_world(path: str) -> Path:
    world = Path(path).resolve()
    if not world.exists() or not world.is_dir():
        raise SystemExit(f"World directory not found: {world}")
    return world


def relative_inside(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise SystemExit(f"Path is outside world directory: {path}") from exc


def read_payload(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    stripped = value.lstrip()
    if stripped.startswith("{"):
        data = json.loads(value)
    else:
        path = Path(value)
        try:
            exists = path.exists()
        except OSError:
            exists = False
        if exists:
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = json.loads(value)
    if not isinstance(data, dict):
        raise SystemExit("--payload-json must decode to a JSON object")
    return data


def validate_id(value: str, field: str) -> str:
    if not SAFE_ID_PATTERN.fullmatch(value):
        raise SystemExit(f"{field} must contain only letters, numbers, underscores, or hyphens: {value}")
    return value


def shell_arg(value: str) -> str:
    if value == "":
        return "''"
    if re.fullmatch(r"[A-Za-z0-9_./:\\-]+", value):
        return value
    return "'" + value.replace("'", "''") + "'"


def command_text(args: list[str]) -> str:
    return " ".join(shell_arg(str(arg)) for arg in args)


def suggested_command(action: str, world_arg: str, request_id: str, target_id: str | None, target_kind: str, intent: str, payload: dict[str, Any]) -> list[str]:
    if action in {"observe", "speak", "intervene"}:
        mode = {"observe": "observe", "speak": "dialogue", "intervene": "intervene"}[action]
        return [
            "scripts/make_interaction_packet.py",
            "--world",
            world_arg,
            "--target-id",
            target_id or "<target-id>",
            "--target-kind",
            target_kind,
            "--intent",
            intent or action,
            "--mode",
            mode,
            "--request-id",
            request_id,
        ]
    if action in {"ignore", "follow"}:
        return [
            "scripts/set_attention.py",
            "--world",
            world_arg,
            "--target-id",
            target_id or "<target-id>",
            "--state",
            "ignored" if action == "ignore" else "followed",
            "--confirmed",
        ]
    if action == "advance-time":
        preset = payload.get("preset") or payload.get("advance_preset")
        if preset:
            command = [
                "scripts/advance_world.py",
                "--world",
                world_arg,
                "--preset",
                str(preset),
            ]
            if payload.get("summary"):
                command.extend(["--summary", str(payload["summary"])])
            command.append("--confirmed")
            return command
        days = str(payload.get("days") or 1)
        summary = str(payload.get("summary") or "<summary>")
        return [
            "scripts/advance_world.py",
            "--world",
            world_arg,
            "--days",
            days,
            "--summary",
            summary,
            "--confirmed",
        ]
    if action == "weather-override":
        weather = str(payload.get("value") or payload.get("weather") or "<weather>")
        return [
            "scripts/resolve_random.py",
            "--world",
            world_arg,
            "--purpose",
            "weather",
            "--kind",
            "weather",
            "--override",
            weather,
        ]
    if action == "set-rule":
        text = str(payload.get("text") or payload.get("rule_text") or intent or "<rule-text>")
        command = [
            "scripts/set_world_rule.py",
            "--world",
            world_arg,
            "--text",
            text,
            "--scope",
            str(payload.get("scope") or "global"),
            "--confirmed",
        ]
        optional_pairs = [
            ("rule_id", "--rule-id"),
            ("target", "--target"),
            ("status", "--status"),
            ("effective_time", "--effective-time"),
            ("note", "--note"),
        ]
        for key, flag in optional_pairs:
            value = payload.get(key)
            if value:
                command.extend([flag, str(value)])
        for replaced in payload.get("replaces") or []:
            command.extend(["--replaces", str(replaced)])
        for tag in payload.get("tags") or []:
            command.extend(["--tag", str(tag)])
        return command
    if action == "branch":
        fork_event = payload.get("fork_event") or payload.get("from_event") or "<event-id>"
        return [
            "scripts/draft_branch.py",
            "--world",
            world_arg,
            "--branch-id",
            str(payload.get("branch_id") or "<branch-id>"),
            "--fork-event",
            str(fork_event),
            "--change-summary",
            str(payload.get("change_summary") or intent or "<change-summary>"),
            "--confirmed",
        ]
    if action == "terrain-brush":
        brush_id = str(payload.get("brush_id") or payload.get("id") or "<brush-id>")
        kind = str(payload.get("kind") or "custom")
        points_value = payload.get("points_json")
        if points_value is None and "points" in payload:
            points_value = json.dumps(payload["points"], ensure_ascii=False, separators=(",", ":"))
        command = [
            "scripts/set_map_brush.py",
            "--world",
            world_arg,
            "--brush-id",
            brush_id,
        ]
        if payload.get("remove"):
            command.append("--remove")
            command.append("--confirmed")
            return command
        command.extend(["--kind", kind, "--points-json", str(points_value or "<points-json>")])
        optional_pairs = [
            ("label", "--label"),
            ("level", "--level"),
            ("width", "--width"),
            ("density", "--density"),
            ("jitter", "--jitter"),
            ("color", "--color"),
        ]
        for key, flag in optional_pairs:
            value = payload.get(key)
            if value not in (None, ""):
                command.extend([flag, str(value)])
        command.append("--confirmed")
        return command
    return ["<custom-codex-action>"]


def build_request(args: argparse.Namespace) -> tuple[dict[str, Any], Path, Path]:
    if args.action not in VALID_ACTIONS:
        raise SystemExit(f"Unsupported action: {args.action}")
    if args.action in TARGET_REQUIRED and not args.target_id:
        raise SystemExit(f"--target-id is required for action `{args.action}`")

    world = resolve_world(args.world)
    active = parse_active(world)
    branch = world / active["branch_path"]
    if not branch.exists():
        raise SystemExit(f"Active branch path missing: {active['branch_path']}")
    save_path = world / active["save_path"]
    if not save_path.exists():
        raise SystemExit(f"Active SAVE.md not found: {save_path}")

    payload = read_payload(args.payload_json)
    if args.days is not None:
        payload["days"] = args.days
    if args.preset:
        payload["preset"] = args.preset
    if args.summary:
        payload["summary"] = args.summary
    if args.value:
        payload["value"] = args.value

    request_id = validate_id(args.request_id or "AR-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f"), "--request-id")
    request_dir = branch / "runtime" / "action-requests" / request_id
    request_json = request_dir / "request.json"
    request_md = request_dir / "request.md"
    if request_json.exists() or request_md.exists():
        raise SystemExit(f"Action request already exists: {request_id}")

    save_text = save_path.read_text(encoding="utf-8")
    intent = args.intent or args.text or args.action
    command_args = suggested_command(args.action, args.world, request_id, args.target_id, args.target_kind, intent, payload)
    if args.suggested_command:
        command_args = [args.suggested_command]

    request = {
        "schema": SCHEMA,
        "request_id": request_id,
        "status": "requested",
        "created_at": utc_now(),
        "world_id": active.get("world_id") or world.name,
        "branch_id": active.get("branch_id", "main"),
        "branch_path": active["branch_path"],
        "save_path": active["save_path"],
        "world_time": parse_save_field(save_text, "world_time"),
        "action": args.action,
        "target": {
            "id": args.target_id,
            "kind": args.target_kind,
            "source": args.target_source,
        },
        "intent": intent,
        "text": args.text,
        "payload": payload,
        "suggested_command_args": command_args,
        "suggested_command": command_args[0] if args.suggested_command else command_text(command_args),
        "context_policy": {
            "request_creation_reads": ["ACTIVE.md", active["save_path"]],
            "canonical_effect": "none",
            "settlement_required": args.action not in {"ignore", "follow", "weather-override", "advance-time", "set-rule"},
            "instruction": "Record the player's requested action first. Do not read broad story history merely to save this request.",
        },
    }
    return request, request_json, request_md


def render_markdown(request: dict[str, Any]) -> str:
    target = request["target"]
    return "\n".join(
        [
            f"# Action Request {request['request_id']}",
            "",
            f"- schema: {request['schema']}",
            f"- status: {request['status']}",
            f"- created_at: {request['created_at']}",
            f"- world_id: {request['world_id']}",
            f"- branch_id: {request['branch_id']}",
            f"- branch_path: {request['branch_path']}",
            f"- world_time: {request.get('world_time') or 'unknown'}",
            f"- action: {request['action']}",
            f"- target_id: {target.get('id') or 'WORLD'}",
            f"- target_kind: {target.get('kind') or 'world'}",
            f"- intent: {request['intent']}",
            "",
            "## Suggested command",
            "",
            "```text",
            request["suggested_command"],
            "```",
            "",
            "## Policy",
            "",
            "- This file is a support request, not canon.",
            "- Creating it must not change events, chronicle, state, random logs, queues, dashboard, or timeline.",
            "- Execute or settle the suggested command only after the player/Codex confirms the actual action.",
            "",
        ]
    )


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def refresh_manifest(world: Path) -> None:
    script = Path(__file__).resolve().parent / "build_file_manifest.py"
    subprocess.run([sys.executable, str(script), str(world)], check=True, stdout=subprocess.DEVNULL)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a durable player action request without changing canon.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--action", required=True, choices=sorted(VALID_ACTIONS))
    parser.add_argument("--target-id")
    parser.add_argument("--target-kind", default="world", choices=["character", "location", "object", "place", "event", "piece", "random", "world", "unknown"])
    parser.add_argument("--target-source", default="")
    parser.add_argument("--intent", default="")
    parser.add_argument("--text", default="")
    parser.add_argument("--payload-json", help="JSON object string or path to a JSON file.")
    parser.add_argument("--days", type=int)
    parser.add_argument("--preset", help="Advance profile preset for advance-time requests.")
    parser.add_argument("--summary", default="")
    parser.add_argument("--value", default="", help="Override value, e.g. weather text.")
    parser.add_argument("--suggested-command", default="")
    parser.add_argument("--request-id")
    parser.add_argument("--skip-manifest", action="store_true")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    request, request_json, request_md = build_request(args)
    if args.dry_run:
        print(json.dumps(request, ensure_ascii=False, indent=2))
        return 0
    if not args.confirmed:
        raise SystemExit("Refusing to write action request without --confirmed. Use --dry-run to preview.")

    write_json(request_json, request)
    request_md.write_text(render_markdown(request), encoding="utf-8")
    if not args.skip_manifest:
        refresh_manifest(resolve_world(args.world))

    result = {
        "ok": True,
        "request_id": request["request_id"],
        "request_json": str(request_json),
        "request_markdown": str(request_md),
        "suggested_command": request["suggested_command"],
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote action request: {request_json}")
        print(f"Suggested command: {request['suggested_command']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
