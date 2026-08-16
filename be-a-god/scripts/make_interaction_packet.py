#!/usr/bin/env python3
"""Create a minimal interaction packet for close-up play.

This script intentionally does not read full chapters or broad event history.
It prepares a bounded packet for Codex to narrate a quick interaction, then
another settlement script can write canonical consequences afterward.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from build_event_graph import build_graph
from read_source_packet import build_packet as build_source_packet


SCHEMA = "be-a-god.interaction-packet.v1"
SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
DEFAULT_SOURCE_BUDGET = 6
MAX_TEXT_CHARS = 4000
HISTORY_EVENT_LIMIT = 3
HISTORY_SOURCE_BUDGET = 3600
TARGET_SEARCH_DIRS = [
    "story/main/state/entities",
    "story/main/state/locations",
    "base/entities",
    "base/locations",
]
FORBIDDEN_SOURCE_AREAS = [
    "story/*/chapters/**",
    "story/*/events/** except explicitly listed event pointers",
    "story/*/branches/** except active parent chain when branch inheritance is required",
    "sibling branches",
    "random/random-log.jsonl except when the interaction directly audits a random result",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_text(path: Path, max_chars: int = MAX_TEXT_CHARS) -> str:
    text = path.read_text(encoding="utf-8")
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n[TRUNCATED_FOR_PACKET]"
    return text


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_world_rules(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = read_json(path)
    except json.JSONDecodeError:
        return []
    rules = []
    for rule in data.get("rules", []):
        if isinstance(rule, dict) and rule.get("status") == "active":
            rules.append(
                {
                    "rule_id": rule.get("rule_id"),
                    "text": rule.get("text"),
                    "scope": rule.get("scope"),
                    "target": rule.get("target"),
                    "effective_time": rule.get("effective_time"),
                    "tags": rule.get("tags", []),
                }
            )
    return rules


def summarize_narrative_profile(path: Path, world: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = read_json(path)
    except json.JSONDecodeError:
        return None
    profiles = data.get("profiles", {})
    default_profile = data.get("default_profile")
    if not isinstance(profiles, dict) or default_profile not in profiles:
        return None
    profile = profiles.get(default_profile)
    if not isinstance(profile, dict):
        return None
    output_layers = profile.get("output_layers", {})
    balance = profile.get("balance", {})
    return {
        "source": relative_inside(path, world),
        "default_profile": default_profile,
        "label": profile.get("label"),
        "default_scale": balance.get("default_scale") if isinstance(balance, dict) else None,
        "priority_order": profile.get("priority_order", []),
        "required_output_layers": output_layers.get("required", []) if isinstance(output_layers, dict) else [],
        "event_pressure_sources": profile.get("event_pressure_sources", []),
        "event_chain": profile.get("event_chain", []),
        "style_avoid": profile.get("style", {}).get("avoid", []) if isinstance(profile.get("style"), dict) else [],
    }


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_manifest(world: Path) -> None:
    script = Path(__file__).resolve().parent / "build_file_manifest.py"
    subprocess.run([sys.executable, str(script), str(world)], check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE)


def parse_active(active_path: Path) -> dict[str, str]:
    active = {}
    for line in active_path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        active[key.strip()] = value.strip()
    if "branch_path" not in active:
        active["branch_path"] = "story/main"
    if "save_path" not in active:
        active["save_path"] = f"{active['branch_path']}/SAVE.md"
    return active


def parse_save_field(save_text: str, field: str) -> str | None:
    pattern = re.compile(rf"^\s*-\s*{re.escape(field)}:\s*(.+?)\s*$", re.MULTILINE)
    match = pattern.search(save_text)
    return match.group(1).strip() if match else None


def resolve_world(path: str) -> Path:
    world = Path(path).resolve()
    if not world.exists() or not world.is_dir():
        raise SystemExit(f"World directory not found: {world}")
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world directory: {world}")
    return world


def relative_inside(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise SystemExit(f"Path is outside world directory: {path}") from exc


def validate_id(value: str, field: str) -> str:
    if not SAFE_ID_PATTERN.fullmatch(value):
        raise SystemExit(f"{field} must contain only letters, numbers, underscores, or hyphens: {value}")
    return value


def candidate_target_files(world: Path, target_id: str, branch_path: str) -> list[Path]:
    exact_candidates = []
    prefix_candidates = []
    branch_dirs = [
        Path(branch_path) / "state" / "entities",
        Path(branch_path) / "state" / "locations",
    ]
    rel_dirs = branch_dirs + [Path(rel) for rel in TARGET_SEARCH_DIRS]
    seen = set()
    for rel_dir in rel_dirs:
        directory = world / rel_dir
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.md")):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                text = read_text(path, max_chars=1200)
            except UnicodeDecodeError:
                continue
            if parse_save_field(text, "id") == target_id:
                exact_candidates.append(path)
                continue
            if path.stem.lower().startswith(target_id.lower()):
                prefix_candidates.append(path)
    if exact_candidates:
        return exact_candidates
    if len(prefix_candidates) > 1:
        matches = ", ".join(path.name for path in prefix_candidates[:8])
        raise SystemExit(f"Target id is ambiguous; use exact `- id:` value or --target-file. Matches: {matches}")
    return prefix_candidates


def find_dashboard_target(dashboard: dict, target_id: str) -> dict | None:
    for key in ("pieces", "pins", "entities", "locations"):
        items = dashboard.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict) and str(item.get("id")) == target_id:
                return {"source": f"dashboard.data.{key}", "data": item}
    return None


def select_history_events(graph: dict, target_id: str, location: str | None, intent: str, active_branch: str) -> list[dict]:
    terms = {term for term in re.findall(r"[a-z0-9_-]+", intent.lower()) if len(term) > 2}
    ranked = []
    for order, node in enumerate(graph.get("nodes", [])):
        score = 0
        if target_id in node.get("actors", []):
            score += 6
        if location and node.get("location") == location:
            score += 3
        searchable = " ".join([str(node.get("title") or ""), *node.get("tags", []), *node.get("cause_notes", []), *node.get("effect_notes", [])]).lower()
        score += 2 * sum(term in searchable for term in terms)
        if node.get("branch_path") == active_branch:
            score += 1
        if score:
            ranked.append((score, order, node))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [node for _score, _order, node in ranked[:HISTORY_EVENT_LIMIT]]


def build_history_context(world: Path, active: dict[str, str], target_id: str, location: str | None, intent: str) -> dict:
    selected = select_history_events(build_graph(world), target_id, location, intent, active["branch_path"])
    source_packet = build_source_packet(world, [str(node["source"]) for node in selected], max_chars=1600, total_budget=HISTORY_SOURCE_BUDGET)
    return {
        "selection_policy": "target actor > same location > intent/tag match > active branch; newest breaks ties",
        "selected_events": [
            {"event_id": node.get("id"), "event_key": node.get("key"), "title": node.get("title"), "source": node.get("source")}
            for node in selected
        ],
        "sources": [item for item in source_packet["sources"] if item.get("allowed") and item.get("exists")],
        "used_chars": source_packet["used_chars"],
        "total_budget": source_packet["total_budget"],
    }


def load_action_request(world: Path, branch_path: str, request_id: str, target_id: str) -> dict:
    request_id = validate_id(request_id, "--request-id")
    request_path = world / branch_path / "runtime" / "action-requests" / request_id / "request.json"
    if not request_path.exists():
        raise SystemExit(f"Action request not found: {request_path}")
    request = read_json(request_path)
    if request.get("schema") != "be-a-god.action-request.v1":
        raise SystemExit(f"Unexpected action request schema: {request_path}")
    request_target = request.get("target", {})
    request_target_id = request_target.get("id")
    if request_target_id and request_target_id != target_id:
        raise SystemExit(f"Action request target `{request_target_id}` does not match packet target `{target_id}`")
    return {
        "request_id": request.get("request_id") or request_id,
        "status": request.get("status"),
        "action": request.get("action"),
        "intent": request.get("intent"),
        "source": relative_inside(request_path, world),
    }


def make_packet(args: argparse.Namespace) -> tuple[dict, Path | None]:
    world = resolve_world(args.world)
    active_path = world / "ACTIVE.md"
    active = parse_active(active_path)
    branch_path = active["branch_path"]
    branch = world / branch_path
    save_path = world / active["save_path"]
    current_path = branch / "CURRENT.md"
    player_path = world / "PLAYER.md"
    canon_path = world / "CANON.md"
    rules_path = world / "setup" / "world-rules.json"
    narrative_profile_path = world / "setup" / "narrative-profile.json"
    dashboard_path = world / "dashboard" / "data.json"

    required = [save_path, current_path, player_path]
    for path in required:
        if not path.exists():
            raise SystemExit(f"Required file missing for interaction packet: {path}")

    save_text = read_text(save_path)
    current_text = read_text(current_path)
    player_text = read_text(player_path)
    dashboard = read_json(dashboard_path) if dashboard_path.exists() else {}

    target_file = Path(args.target_file).resolve() if args.target_file else None
    if target_file and (not target_file.exists() or not target_file.is_file()):
        raise SystemExit(f"Target file not found: {target_file}")
    if target_file:
        relative_inside(target_file, world)

    target_candidates = []
    if target_file:
        target_candidates = [target_file]
    else:
        target_candidates = candidate_target_files(world, args.target_id, branch_path)

    target_doc = None
    if target_candidates:
        target_file = target_candidates[0]
        target_doc = read_text(target_file)

    dashboard_target = find_dashboard_target(dashboard, args.target_id)
    target_location = parse_save_field(target_doc or "", "location")
    history_context = build_history_context(world, active, args.target_id, target_location, args.intent)
    packet_id = validate_id(args.packet_id or "IP-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"), "--packet-id")
    output_path = branch / "runtime" / "interaction-packets" / f"{packet_id}.json"
    action_request = load_action_request(world, branch_path, args.request_id, args.target_id) if args.request_id else None

    required_sources = [
        {"path": relative_inside(active_path, world), "reason": "active world and branch pointer"},
        {"path": relative_inside(save_path, world), "reason": "active branch compact save"},
        {"path": relative_inside(current_path, world), "reason": "current immediate scene"},
        {"path": relative_inside(player_path, world), "reason": "player god settings and display preference"},
        {"path": relative_inside(rules_path, world), "reason": "active player-confirmed world rules"},
    ]
    if narrative_profile_path.exists():
        required_sources.append({"path": relative_inside(narrative_profile_path, world), "reason": "compact narrative quality profile"})
    if target_file:
        required_sources.append({"path": relative_inside(target_file, world), "reason": "clicked target card"})

    optional_sources = []
    if dashboard_path.exists():
        optional_sources.append({"path": relative_inside(dashboard_path, world), "reason": "map piece and dashboard state"})

    requested_source_budget = max(1, args.source_budget)
    source_budget = max(requested_source_budget, len(required_sources))
    allowed_sources = required_sources[:]
    remaining = max(0, source_budget - len(allowed_sources))
    allowed_sources.extend(optional_sources[:remaining])

    packet = {
        "schema": SCHEMA,
        "packet_id": packet_id,
        "request_id": args.request_id,
        "created_at": utc_now(),
        "world_id": active.get("world_id"),
        "branch_id": active.get("branch_id", "main"),
        "branch_path": branch_path,
        "player_intent": args.intent,
        "action_request": action_request,
        "interaction": {
            "target_id": args.target_id,
            "target_kind": args.target_kind,
            "mode": args.mode,
        },
        "scene": {
            "world_time": parse_save_field(save_text, "world_time"),
            "focal_place": parse_save_field(save_text, "focal_place"),
            "current_scene": parse_save_field(save_text, "current_scene"),
            "current_summary": current_text,
        },
        "player": {
            "summary": player_text,
        },
        "world_rules": {
            "source": relative_inside(rules_path, world),
            "canon_source": relative_inside(canon_path, world),
            "active": summarize_world_rules(rules_path),
        },
        "narrative_profile": summarize_narrative_profile(narrative_profile_path, world),
        "target": {
            "file": relative_inside(target_file, world) if target_file else None,
            "document": target_doc,
            "dashboard_state": dashboard_target,
            "candidate_count": len(target_candidates),
        },
        "history_context": history_context,
        "context_policy": {
            "allowed_sources": allowed_sources,
            "forbidden_sources": FORBIDDEN_SOURCE_AREAS,
            "source_budget": source_budget,
            "requested_source_budget": requested_source_budget,
            "knowledge_boundary": "Use only packet content and allowed source pointers unless followup_source_request is approved.",
            "must_not_do": [
                "Do not read full chapters before a simple interaction.",
                "Do not scan sibling branches.",
                "Do not settle canonical consequences in this packet step.",
                "Do not let non-omniscient characters use player-only knowledge.",
                "Do not ignore the supplied narrative profile when resolving meaningful events.",
            ],
        },
        "followup_source_request": {
            "needed": False,
            "reason": None,
            "requested_sources": [],
            "trigger_conditions": [
                "old promise, curse, oath, or debt is invoked",
                "hidden identity or secret knowledge matters",
                "death, succession, war, branch inheritance, or irreversible action is touched",
                "player explicitly asks for recap or audit",
            ],
        },
        "settlement_hint": {
            "after_narration_run": "settle_interaction.py",
            "expected_outputs": [
                "event node",
                "entity/location state update if changed",
                "objective chronicle entry if formal event occurred",
                "timeline/dashboard rebuild",
                "file manifest refresh",
            ],
        },
    }
    return packet, output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a minimal close-up interaction packet.")
    parser.add_argument("--world", required=True, help="Path to worlds/<world-id>.")
    parser.add_argument("--target-id", required=True, help="Clicked character, object, place, piece, or pin id.")
    parser.add_argument("--target-kind", default="unknown", choices=["character", "location", "object", "place", "event", "piece", "unknown"])
    parser.add_argument("--intent", required=True, help="Player's immediate intent, e.g. observe, speak, intervene.")
    parser.add_argument("--mode", default="close-up", choices=["close-up", "observe", "dialogue", "intervene"])
    parser.add_argument("--target-file", help="Explicit target Markdown file to include.")
    parser.add_argument("--source-budget", type=int, default=DEFAULT_SOURCE_BUDGET)
    parser.add_argument("--packet-id", help="Optional stable packet id.")
    parser.add_argument("--request-id", help="Optional action request id to attach and validate.")
    parser.add_argument("--dry-run", action="store_true", help="Print packet JSON without writing it.")
    args = parser.parse_args()

    packet, output_path = make_packet(args)
    if args.dry_run:
        print(json.dumps(packet, ensure_ascii=False, indent=2))
        return 0
    if output_path is None:
        raise SystemExit("Internal error: output path was not resolved")
    write_json(output_path, packet)
    update_manifest(resolve_world(args.world))
    print(f"Wrote interaction packet: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
