#!/usr/bin/env python3
"""Validate be-a-god world structure, active branch, and core derived files."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REQUIRED_WORLD_FILES = ["WORLD.md", "ACTIVE.md", "CANON.md", "PLAYER.md", "story/STORY-TREE.md"]
REQUIRED_BRANCH_PATHS = [
    "SAVE.md",
    "CURRENT.md",
    "events",
    "state",
    "chronicle",
    "random",
    "queues",
    "runtime",
    "runtime/action-requests",
    "runtime/context-handoffs",
    "runtime/divine-assessments",
    "runtime/resume-packets",
    "runtime/rule-checks",
    "runtime/soften-requests",
    "checkpoints",
]
SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def parse_active(world: Path) -> dict[str, str]:
    data = {}
    for line in (world / "ACTIVE.md").read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    data.setdefault("branch_path", "story/main")
    data.setdefault("branch_id", "main")
    data.setdefault("save_path", f"{data['branch_path']}/SAVE.md")
    return data


def validate_world_relative_path(world: Path, raw_path: str, field: str, errors: list[str]) -> Path | None:
    if not raw_path:
        errors.append(f"ACTIVE.md {field} is missing")
        return None
    path = Path(raw_path)
    if path.is_absolute():
        errors.append(f"ACTIVE.md {field} must be relative to world: {raw_path}")
        return None
    resolved = (world / path).resolve()
    try:
        resolved.relative_to(world.resolve())
    except ValueError:
        errors.append(f"ACTIVE.md {field} points outside world: {raw_path}")
        return None
    return resolved


def parse_field(text: str, field: str) -> str | None:
    match = re.search(rf"^\s*-\s*{re.escape(field)}:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def read_json(path: Path, errors: list[str], rel: str) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid JSON in {rel}: {exc}")
        return None


def require_object(data: object, errors: list[str], rel: str) -> dict | None:
    if not isinstance(data, dict):
        errors.append(f"{rel} must be a JSON object")
        return None
    return data


def require_list(value: object, errors: list[str], rel: str, field: str) -> list | None:
    if not isinstance(value, list):
        errors.append(f"{rel} `{field}` must be a list")
        return None
    return value


def validate_source_pointer(pointer: object, world: Path, errors: list[str], warnings: list[str], rel: str, field: str) -> None:
    if pointer in {None, ""}:
        errors.append(f"{rel} `{field}` missing source pointer")
        return
    if not isinstance(pointer, str):
        errors.append(f"{rel} `{field}` source pointer must be a string")
        return
    if pointer.startswith("<"):
        return
    if ".." in Path(pointer).parts or Path(pointer).is_absolute():
        errors.append(f"{rel} `{field}` source pointer must stay relative: {pointer}")
        return
    if not (world / pointer).exists():
        warnings.append(f"{rel} `{field}` source pointer target missing: {pointer}")


def validate_dashboard_data(data: object, world: Path, active: dict[str, str], errors: list[str], warnings: list[str], rel: str) -> None:
    dashboard = require_object(data, errors, rel)
    if not dashboard:
        return
    if dashboard.get("schema") != "be-a-god.dashboard.v1":
        errors.append(f"{rel} has unexpected schema")
    if dashboard.get("world_id") != active.get("world_id", world.name):
        errors.append(f"{rel} world_id does not match ACTIVE.md")
    if dashboard.get("branch_id") != active.get("branch_id", "main"):
        errors.append(f"{rel} branch_id does not match ACTIVE.md")
    for field in ["time", "focal_place", "current_scene"]:
        if not isinstance(dashboard.get(field), str):
            errors.append(f"{rel} `{field}` must be a string")
    pieces = require_list(dashboard.get("pieces"), errors, rel, "pieces") or []
    pins = require_list(dashboard.get("pins"), errors, rel, "pins") or []
    for field in ["pending_action_requests"]:
        require_list(dashboard.get(field), errors, rel, field)
    for field in ["advance_profile", "world_rules", "random_log", "attention"]:
        if not isinstance(dashboard.get(field), dict):
            errors.append(f"{rel} `{field}` must be an object")
    for index, piece in enumerate(pieces, start=1):
        if not isinstance(piece, dict):
            errors.append(f"{rel} pieces[{index}] must be an object")
            continue
        for field in ["id", "kind", "label", "status", "source"]:
            if not piece.get(field):
                errors.append(f"{rel} pieces[{index}] missing `{field}`")
        validate_source_pointer(piece.get("source"), world, errors, warnings, rel, f"pieces[{index}].source")
    for index, pin in enumerate(pins, start=1):
        if not isinstance(pin, dict):
            errors.append(f"{rel} pins[{index}] must be an object")
            continue
        for field in ["id", "kind", "label", "source"]:
            if not pin.get(field):
                errors.append(f"{rel} pins[{index}] missing `{field}`")
        validate_source_pointer(pin.get("source"), world, errors, warnings, rel, f"pins[{index}].source")


def validate_timeline_data(data: object, world: Path, active: dict[str, str], errors: list[str], warnings: list[str], rel: str) -> None:
    timeline = require_object(data, errors, rel)
    if not timeline:
        return
    if timeline.get("schema") != "be-a-god.timeline.v1":
        errors.append(f"{rel} has unexpected schema")
    if timeline.get("world_id") != active.get("world_id", world.name):
        errors.append(f"{rel} world_id does not match ACTIVE.md")
    if timeline.get("branch_id") != active.get("branch_id", "main"):
        errors.append(f"{rel} branch_id does not match ACTIVE.md")
    nodes = require_list(timeline.get("nodes"), errors, rel, "nodes") or []
    valid_states = {"confirmed", "current", "branch", "queued", "due", "locked", "ignored"}
    seen_ids = set()
    for index, node in enumerate(nodes, start=1):
        if not isinstance(node, dict):
            errors.append(f"{rel} nodes[{index}] must be an object")
            continue
        node_id = node.get("id")
        if not node_id:
            errors.append(f"{rel} nodes[{index}] missing `id`")
        elif node_id in seen_ids:
            errors.append(f"{rel} duplicate timeline node id `{node_id}`")
        seen_ids.add(node_id)
        if node.get("state") not in valid_states:
            errors.append(f"{rel} nodes[{index}] has invalid state `{node.get('state')}`")
        for field in ["event_id", "time", "label", "source"]:
            if not node.get(field):
                errors.append(f"{rel} nodes[{index}] missing `{field}`")
        validate_source_pointer(node.get("source"), world, errors, warnings, rel, f"nodes[{index}].source")


def validate_map_layers_data(data: object, world: Path, active: dict[str, str], errors: list[str], warnings: list[str], rel: str) -> None:
    layers = require_object(data, errors, rel)
    if not layers:
        return
    if layers.get("schema") != "be-a-god.map-layers.v1":
        errors.append(f"{rel} has unexpected schema")
    if layers.get("world_id") != active.get("world_id", world.name):
        errors.append(f"{rel} world_id does not match ACTIVE.md")
    levels = require_list(layers.get("levels"), errors, rel, "levels") or []
    if not levels:
        errors.append(f"{rel} levels must not be empty")
    nodes = require_list(layers.get("nodes"), errors, rel, "nodes") or []
    places = require_list(layers.get("places"), errors, rel, "places") or []
    brushes = layers.get("brushes", [])
    if brushes is None:
        brushes = []
    if not isinstance(brushes, list):
        errors.append(f"{rel} `brushes` must be a list when present")
        brushes = []
    read_policy = layers.get("read_policy")
    if not isinstance(read_policy, str) or "story text not included" not in read_policy:
        errors.append(f"{rel} read_policy must state that story text is not included")
    for collection_name, collection in [("nodes", nodes), ("places", places)]:
        for index, item in enumerate(collection, start=1):
            if not isinstance(item, dict):
                errors.append(f"{rel} {collection_name}[{index}] must be an object")
                continue
            for field in ["id", "name", "level"]:
                if not item.get(field):
                    errors.append(f"{rel} {collection_name}[{index}] missing `{field}`")
            if item.get("level") and item.get("level") not in levels:
                errors.append(f"{rel} {collection_name}[{index}] level `{item.get('level')}` is not in levels")
            if "source" in item:
                validate_source_pointer(item.get("source"), world, errors, warnings, rel, f"{collection_name}[{index}].source")
    valid_brush_kinds = {"river", "tributary", "hills", "forest", "marsh", "coast", "custom"}
    for index, brush in enumerate(brushes, start=1):
        if not isinstance(brush, dict):
            errors.append(f"{rel} brushes[{index}] must be an object")
            continue
        for field in ["id", "kind", "points"]:
            if field not in brush:
                errors.append(f"{rel} brushes[{index}] missing `{field}`")
        if brush.get("kind") not in valid_brush_kinds:
            errors.append(f"{rel} brushes[{index}] has invalid kind `{brush.get('kind')}`")
        points = brush.get("points")
        if not isinstance(points, list) or not points:
            errors.append(f"{rel} brushes[{index}] points must be a non-empty list")
        else:
            for point_index, point in enumerate(points, start=1):
                if (
                    not isinstance(point, list)
                    or len(point) != 2
                    or not all(isinstance(value, (int, float)) and 0 <= value <= 100 for value in point)
                ):
                    errors.append(f"{rel} brushes[{index}].points[{point_index}] must be [x,y] numbers in 0..100")
        if brush.get("level") and brush.get("level") not in levels:
            errors.append(f"{rel} brushes[{index}] level `{brush.get('level')}` is not in levels")
        for numeric_field in ["width", "density", "jitter"]:
            if numeric_field in brush and not isinstance(brush.get(numeric_field), (int, float)):
                errors.append(f"{rel} brushes[{index}] `{numeric_field}` must be numeric")
            elif numeric_field in brush and brush.get(numeric_field) < 0:
                errors.append(f"{rel} brushes[{index}] `{numeric_field}` must be non-negative")
        if "source" in brush:
            validate_source_pointer(brush.get("source"), world, errors, warnings, rel, f"brushes[{index}].source")


def validate_derived_json(rel: str, data: object, world: Path, active: dict[str, str], errors: list[str], warnings: list[str]) -> None:
    if rel.endswith("dashboard/data.json"):
        validate_dashboard_data(data, world, active, errors, warnings, rel)
    elif rel.endswith("dashboard/timeline.json"):
        validate_timeline_data(data, world, active, errors, warnings, rel)
    elif rel.endswith("dashboard/map-layers.json"):
        validate_map_layers_data(data, world, active, errors, warnings, rel)


def validate_state_cards(branch: Path, world: Path, errors: list[str], warnings: list[str]) -> None:
    seen: dict[str, str] = {}
    for folder in [branch / "state" / "entities", branch / "state" / "locations"]:
        if not folder.exists():
            warnings.append(f"State card directory missing: {folder.relative_to(world).as_posix()}")
            continue
        for path in sorted(folder.glob("*.md")):
            rel = path.relative_to(world).as_posix()
            text = path.read_text(encoding="utf-8")
            card_id = parse_field(text, "id")
            if not card_id:
                errors.append(f"State card missing `- id:` field: {rel}")
                continue
            if not SAFE_ID_PATTERN.fullmatch(card_id):
                errors.append(f"State card id contains unsafe filename characters: {rel} id={card_id}")
            if not path.stem.startswith(card_id):
                errors.append(f"State card filename must start with its id `{card_id}`: {rel}")
            previous = seen.get(card_id)
            if previous:
                errors.append(f"Duplicate state card id `{card_id}` in {previous} and {rel}")
            else:
                seen[card_id] = rel


def iter_jsonl(path: Path, errors: list[str], rel: str):
    if not path.exists():
        return
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            yield line_no, json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid JSONL in {rel}:{line_no}: {exc}")


def validate_queue(branch: Path, world: Path, errors: list[str], warnings: list[str]) -> None:
    queue_path = branch / "queues" / "events.jsonl"
    rel = queue_path.relative_to(world).as_posix()
    valid_status = {"queued", "due", "settled", "cancelled"}
    seen_ids = set()
    for line_no, item in iter_jsonl(queue_path, errors, rel) or []:
        queue_id = item.get("queue_id")
        if not queue_id:
            errors.append(f"Queue item missing queue_id at {rel}:{line_no}")
            continue
        if queue_id in seen_ids:
            errors.append(f"Duplicate queue_id `{queue_id}` in {rel}")
        seen_ids.add(queue_id)
        status = item.get("status")
        if status not in valid_status:
            errors.append(f"Queue item `{queue_id}` has invalid status `{status}`")
        if not item.get("trigger_time"):
            warnings.append(f"Queue item `{queue_id}` missing trigger_time")
        if status == "settled":
            event_id = item.get("event_id")
            event_file = item.get("event_file")
            if not event_id or not event_file:
                errors.append(f"Settled queue item `{queue_id}` missing event_id or event_file")
            elif not (world / event_file).exists():
                errors.append(f"Settled queue item `{queue_id}` references missing event file: {event_file}")


def validate_random(branch: Path, world: Path, errors: list[str], warnings: list[str]) -> None:
    seed_path = branch / "random" / "seed.json"
    if not seed_path.exists():
        errors.append(f"Missing random seed: {seed_path.relative_to(world).as_posix()}")
    else:
        seed = read_json(seed_path, errors, seed_path.relative_to(world).as_posix())
        if seed and not seed.get("seed"):
            errors.append(f"Random seed file missing seed value: {seed_path.relative_to(world).as_posix()}")
    log_path = branch / "random" / "random-log.jsonl"
    expected = 1
    for line_no, item in iter_jsonl(log_path, errors, log_path.relative_to(world).as_posix()) or []:
        index = item.get("index")
        if index != expected:
            warnings.append(f"Random log index expected {expected}, found {index} at line {line_no}")
            expected = index if isinstance(index, int) else expected
        expected += 1
        if item.get("mode") not in {"random", "override"}:
            errors.append(f"Random log line {line_no} has invalid mode `{item.get('mode')}`")


def validate_handoffs(branch: Path, world: Path, errors: list[str], warnings: list[str]) -> None:
    root = branch / "runtime" / "context-handoffs"
    if not root.exists():
        warnings.append(f"Context handoff directory missing: {root.relative_to(world).as_posix()}")
        return
    for handoff_json in sorted(root.glob("*/handoff.json")):
        rel = handoff_json.relative_to(world).as_posix()
        data = read_json(handoff_json, errors, rel)
        if not data:
            continue
        handoff_md = handoff_json.parent / "HANDOFF.md"
        if not handoff_md.exists():
            errors.append(f"Handoff missing HANDOFF.md beside {rel}")
        save_md = handoff_json.parent / "存档.md"
        if not save_md.exists():
            errors.append(f"Handoff missing 存档.md beside {rel}")
        if data.get("schema") != "be-a-god.handoff.v1":
            errors.append(f"Handoff has unexpected schema in {rel}")
        for pointer in data.get("first_read", []):
            if "<" in pointer:
                continue
            path = world / pointer
            if not path.exists():
                errors.append(f"Handoff first_read points to missing file: {pointer}")


def validate_action_requests(branch: Path, world: Path, errors: list[str], warnings: list[str]) -> None:
    root = branch / "runtime" / "action-requests"
    if not root.exists():
        warnings.append(f"Action request directory missing: {root.relative_to(world).as_posix()}")
        return
    valid_status = {"requested", "accepted", "executed", "cancelled"}
    for request_json in sorted(root.glob("*/request.json")):
        rel = request_json.relative_to(world).as_posix()
        data = read_json(request_json, errors, rel)
        if not data:
            continue
        if data.get("schema") != "be-a-god.action-request.v1":
            errors.append(f"Action request has unexpected schema: {rel}")
        if data.get("status") not in valid_status:
            errors.append(f"Action request has invalid status `{data.get('status')}`: {rel}")
        if not data.get("request_id"):
            errors.append(f"Action request missing request_id: {rel}")
        if not data.get("action"):
            errors.append(f"Action request missing action: {rel}")
        if data.get("context_policy", {}).get("canonical_effect") != "none":
            errors.append(f"Action request must be non-canonical on creation: {rel}")
        suggested = data.get("suggested_command") or ""
        action = data.get("action")
        payload = data.get("payload", {}) if isinstance(data.get("payload"), dict) else {}
        if not suggested:
            warnings.append(f"Action request missing suggested_command: {rel}")
        elif action in {"observe", "speak", "intervene"}:
            if "make_interaction_packet.py" not in suggested or "--request-id" not in suggested:
                errors.append(f"Action request `{action}` must suggest interaction packet with request id: {rel}")
        elif action in {"ignore", "follow"}:
            expected_state = "ignored" if action == "ignore" else "followed"
            if "set_attention.py" not in suggested or expected_state not in suggested or "--confirmed" not in suggested:
                errors.append(f"Action request `{action}` must suggest confirmed attention update: {rel}")
        elif action == "advance-time":
            preset = payload.get("preset") or payload.get("advance_preset")
            if "advance_world.py" not in suggested or "--confirmed" not in suggested:
                errors.append(f"Action request `advance-time` must suggest confirmed advance_world.py command: {rel}")
            if preset and f"--preset {preset}" not in suggested:
                errors.append(f"Action request `advance-time` lost selected preset `{preset}`: {rel}")
            if "preset:" in str(data.get("intent", "")) and "--preset" not in suggested:
                errors.append(f"Action request `advance-time` mentions a preset in intent but does not pass --preset: {rel}")
        elif action == "weather-override":
            if "resolve_random.py" not in suggested or "--override" not in suggested:
                errors.append(f"Action request `weather-override` must suggest random override logging: {rel}")
        elif action == "set-rule":
            if "set_world_rule.py" not in suggested or "--confirmed" not in suggested:
                errors.append(f"Action request `set-rule` must suggest confirmed world rule update: {rel}")
        elif action == "branch":
            if "draft_branch.py" not in suggested or "--branch-id" not in suggested or "--fork-event" not in suggested or "--confirmed" not in suggested:
                errors.append(f"Action request `branch` must suggest confirmed branch draft: {rel}")
        elif action == "terrain-brush":
            if "set_map_brush.py" not in suggested or "--brush-id" not in suggested or "--confirmed" not in suggested:
                errors.append(f"Action request `terrain-brush` must suggest confirmed terrain brush update: {rel}")
            if not payload.get("remove") and ("--kind" not in suggested or "--points-json" not in suggested):
                errors.append(f"Action request `terrain-brush` must carry brush kind and points-json unless removing: {rel}")
        request_md = request_json.parent / "request.md"
        if not request_md.exists():
            errors.append(f"Action request missing request.md beside {rel}")


def validate_divine_assessments(branch: Path, world: Path, errors: list[str], warnings: list[str]) -> None:
    root = branch / "runtime" / "divine-assessments"
    if not root.exists():
        warnings.append(f"Divine assessment directory missing: {root.relative_to(world).as_posix()}")
        return
    valid_status = {"within-normal-limit", "over-limit-warning", "major-overreach", "absolute-authorized"}
    for assessment_json in sorted(root.glob("*/assessment.json")):
        rel = assessment_json.relative_to(world).as_posix()
        data = read_json(assessment_json, errors, rel)
        if not data:
            continue
        if data.get("schema") != "be-a-god.divine-assessment.v1":
            errors.append(f"Divine assessment has unexpected schema: {rel}")
        if data.get("status") not in valid_status:
            errors.append(f"Divine assessment has invalid status `{data.get('status')}`: {rel}")
        if data.get("canonical_effect") != "none":
            errors.append(f"Divine assessment must be non-canonical: {rel}")
        if not isinstance(data.get("score"), int):
            errors.append(f"Divine assessment score must be an integer: {rel}")
        assessment_md = assessment_json.parent / "assessment.md"
        if not assessment_md.exists():
            errors.append(f"Divine assessment missing assessment.md beside {rel}")


def validate_rule_checks(branch: Path, world: Path, errors: list[str], warnings: list[str]) -> None:
    root = branch / "runtime" / "rule-checks"
    if not root.exists():
        warnings.append(f"Rule check directory missing: {root.relative_to(world).as_posix()}")
        return
    valid_decisions = {"needs-model-review", "no-conflict", "conflict", "override-requested"}
    for check_json in sorted(root.glob("*/check.json")):
        rel = check_json.relative_to(world).as_posix()
        data = read_json(check_json, errors, rel)
        if not data:
            continue
        if data.get("schema") != "be-a-god.rule-check.v1":
            errors.append(f"Rule check has unexpected schema: {rel}")
        if data.get("decision") not in valid_decisions:
            errors.append(f"Rule check has invalid decision `{data.get('decision')}`: {rel}")
        if not isinstance(data.get("relevant_rules", []), list):
            errors.append(f"Rule check relevant_rules must be a list: {rel}")
        if not isinstance(data.get("active_rule_count"), int):
            errors.append(f"Rule check active_rule_count must be an integer: {rel}")
        source_policy = data.get("source_policy", {})
        if "setup/world-rules.json" not in source_policy.get("required_sources", []):
            errors.append(f"Rule check must point to setup/world-rules.json: {rel}")
        check_md = check_json.parent / "check.md"
        if not check_md.exists():
            errors.append(f"Rule check missing check.md beside {rel}")


def validate_resume_packets(branch: Path, world: Path, errors: list[str], warnings: list[str]) -> None:
    root = branch / "runtime" / "resume-packets"
    if not root.exists():
        warnings.append(f"Resume packet directory missing: {root.relative_to(world).as_posix()}")
        return
    for resume_json in sorted(root.glob("*/resume.json")):
        rel = resume_json.relative_to(world).as_posix()
        data = read_json(resume_json, errors, rel)
        if not data:
            continue
        if data.get("schema") != "be-a-god.resume-packet.v1":
            errors.append(f"Resume packet has unexpected schema: {rel}")
        if data.get("context_policy", {}).get("canonical_effect") != "none":
            errors.append(f"Resume packet must be non-canonical: {rel}")
        first_read = data.get("first_read", [])
        if not isinstance(first_read, list) or "ACTIVE.md" not in first_read:
            errors.append(f"Resume packet first_read must include ACTIVE.md: {rel}")
        if not data.get("save", {}).get("source"):
            errors.append(f"Resume packet missing save source: {rel}")
        resume_md = resume_json.parent / "resume.md"
        if not resume_md.exists():
            errors.append(f"Resume packet missing resume.md beside {rel}")



def validate_content_profile(world: Path, errors: list[str], warnings: list[str]) -> None:
    path = world / "setup" / "content-profile.json"
    if not path.exists():
        errors.append("Missing setup/content-profile.json")
        return
    profile = read_json(path, errors, "setup/content-profile.json")
    if not profile:
        return
    topics = profile.get("topics")
    if not isinstance(topics, dict):
        errors.append("content-profile topics must be an object")
    else:
        valid = {"allow", "summary", "soften", "avoid"}
        for topic, mode in topics.items():
            if mode not in valid:
                errors.append(f"content-profile topic `{topic}` has invalid mode `{mode}`")
    bans = profile.get("player_absolute_bans", [])
    if not isinstance(bans, list):
        errors.append("content-profile player_absolute_bans must be a list")
    presentation = profile.get("presentation", {})
    if presentation.get("facts_remain_intact_when_softened") is not True:
        errors.append("content-profile must keep facts_remain_intact_when_softened=true")


def validate_advance_profile(world: Path, errors: list[str], warnings: list[str]) -> None:
    path = world / "setup" / "advance-profile.json"
    if not path.exists():
        errors.append("Missing setup/advance-profile.json")
        return
    profile = read_json(path, errors, "setup/advance-profile.json")
    if not profile:
        return
    if profile.get("schema") != "be-a-god.advance-profile.v1":
        errors.append("advance-profile has unexpected schema")
    presets = profile.get("presets")
    if not isinstance(presets, dict) or not presets:
        errors.append("advance-profile presets must be a non-empty object")
        return
    default_preset = profile.get("default_preset")
    if not isinstance(default_preset, str) or default_preset not in presets:
        errors.append("advance-profile default_preset must reference an existing preset")
    valid_modes = {"step", "fixed", "condition", "event-priority", "follow", "regional", "hybrid", "chronicle", "custom"}
    for preset_id, preset in presets.items():
        if not isinstance(preset, dict):
            errors.append(f"advance-profile preset `{preset_id}` must be an object")
            continue
        if preset.get("mode", "custom") not in valid_modes:
            errors.append(f"advance-profile preset `{preset_id}` has invalid mode `{preset.get('mode')}`")
        if not isinstance(preset.get("days"), int) or preset.get("days") < 0:
            errors.append(f"advance-profile preset `{preset_id}` days must be a non-negative integer")
        if not isinstance(preset.get("wander"), bool):
            errors.append(f"advance-profile preset `{preset_id}` wander must be boolean")
        if not isinstance(preset.get("wander_limit"), int) or preset.get("wander_limit") < 0:
            errors.append(f"advance-profile preset `{preset_id}` wander_limit must be a non-negative integer")
        for field in ["wander_exclude_ignored", "stop_on_queue"]:
            if not isinstance(preset.get(field), bool):
                errors.append(f"advance-profile preset `{preset_id}` {field} must be boolean")
        if "until_next_queue" in preset and not isinstance(preset.get("until_next_queue"), bool):
            errors.append(f"advance-profile preset `{preset_id}` until_next_queue must be boolean when present")


def validate_narrative_profile(world: Path, errors: list[str], warnings: list[str]) -> None:
    path = world / "setup" / "narrative-profile.json"
    if not path.exists():
        errors.append("Missing setup/narrative-profile.json")
        return
    data = read_json(path, errors, "setup/narrative-profile.json")
    if not data:
        return
    if data.get("schema") != "be-a-god.narrative-profile.v1":
        errors.append("narrative-profile has unexpected schema")
    profiles = data.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        errors.append("narrative-profile profiles must be a non-empty object")
        return
    default_profile = data.get("default_profile")
    if not isinstance(default_profile, str) or default_profile not in profiles:
        errors.append("narrative-profile default_profile must reference an existing profile")
        return
    profile = profiles.get(default_profile)
    if not isinstance(profile, dict):
        errors.append(f"narrative-profile `{default_profile}` must be an object")
        return

    priority_order = profile.get("priority_order")
    required_priorities = {"causality", "world_continuity", "character_agency", "historical_texture"}
    if not isinstance(priority_order, list):
        errors.append("narrative-profile priority_order must be a list")
    elif not required_priorities.issubset(set(priority_order)):
        errors.append(f"narrative-profile priority_order missing required priorities: {sorted(required_priorities - set(priority_order))}")

    output_layers = profile.get("output_layers")
    required_layers = {"visible_narration", "gm_summary", "settlement_plan"}
    if not isinstance(output_layers, dict):
        errors.append("narrative-profile output_layers must be an object")
    else:
        layers = output_layers.get("required")
        if not isinstance(layers, list):
            errors.append("narrative-profile output_layers.required must be a list")
        elif not required_layers.issubset(set(layers)):
            errors.append(f"narrative-profile output_layers.required missing layers: {sorted(required_layers - set(layers))}")

    pressure_sources = profile.get("event_pressure_sources")
    required_pressure_sources = {"character", "resource", "institution", "environment"}
    if not isinstance(pressure_sources, list):
        errors.append("narrative-profile event_pressure_sources must be a list")
    elif not required_pressure_sources.issubset(set(pressure_sources)):
        errors.append(f"narrative-profile event_pressure_sources missing sources: {sorted(required_pressure_sources - set(pressure_sources))}")

    event_chain = profile.get("event_chain")
    required_chain = [
        "pressure",
        "actor_choice",
        "direct_consequence",
        "second_order_consequence",
        "player_intervention_point",
    ]
    if not isinstance(event_chain, list):
        errors.append("narrative-profile event_chain must be a list")
    elif event_chain[: len(required_chain)] != required_chain:
        errors.append("narrative-profile event_chain must start with pressure -> actor_choice -> direct_consequence -> second_order_consequence -> player_intervention_point")

    character_fields = profile.get("character_fields")
    required_character_fields = {"desire", "fear", "misunderstanding", "resources", "relationships", "secret", "god_view"}
    if not isinstance(character_fields, dict):
        errors.append("narrative-profile character_fields must be an object")
    else:
        fields = character_fields.get("required")
        if not isinstance(fields, list):
            errors.append("narrative-profile character_fields.required must be a list")
        elif not required_character_fields.issubset(set(fields)):
            errors.append(f"narrative-profile character_fields.required missing fields: {sorted(required_character_fields - set(fields))}")

    social_indicators = profile.get("social_indicators")
    if not isinstance(social_indicators, list) or not social_indicators:
        errors.append("narrative-profile social_indicators must be a non-empty list")

    balance = profile.get("balance")
    if not isinstance(balance, dict):
        errors.append("narrative-profile balance must be an object")
    elif balance.get("default_scale") != "mixed-closeup-chronicle":
        warnings.append("narrative-profile default_scale is not the default mixed-closeup-chronicle")

    style = profile.get("style")
    if not isinstance(style, dict):
        errors.append("narrative-profile style must be an object")
    elif not isinstance(style.get("avoid"), list) or not style.get("avoid"):
        errors.append("narrative-profile style.avoid must be a non-empty list")


def validate_llm_api_config(world: Path, errors: list[str], warnings: list[str]) -> None:
    path = world / "setup" / "llm-api.config.json"
    if not path.exists():
        errors.append("Missing setup/llm-api.config.json")
        return
    config = read_json(path, errors, "setup/llm-api.config.json")
    if not config:
        return
    if config.get("schema") != "be-a-god.llm-api-config.v1":
        errors.append("llm-api.config has unexpected schema")
    if config.get("protocol") != "openai-chat-completions":
        errors.append("llm-api.config protocol must be openai-chat-completions")
    if not isinstance(config.get("enabled"), bool):
        errors.append("llm-api.config enabled must be boolean")
    base_url = config.get("base_url")
    if not isinstance(base_url, str) or not base_url.startswith(("http://", "https://")):
        errors.append("llm-api.config base_url must start with http:// or https://")
    endpoint_path = config.get("endpoint_path")
    if not isinstance(endpoint_path, str) or not endpoint_path.startswith("/"):
        errors.append("llm-api.config endpoint_path must start with /")
    if not isinstance(config.get("api_key_env"), str):
        errors.append("llm-api.config api_key_env must be a string")
    if config.get("api_key"):
        warnings.append("setup/llm-api.config.json contains an api_key value; prefer environment variables for secrets")
    if not isinstance(config.get("model"), str) or not config.get("model", "").strip():
        errors.append("llm-api.config model must be a non-empty string")
    for field in ["temperature", "max_tokens", "timeout_seconds"]:
        value = config.get(field)
        if not isinstance(value, (int, float)) or value < 0:
            errors.append(f"llm-api.config {field} must be a non-negative number")
    if not isinstance(config.get("headers", {}), dict):
        errors.append("llm-api.config headers must be an object")


def validate_player_summaries(world: Path, errors: list[str], warnings: list[str]) -> None:
    player_path = world / "PLAYER.md"
    if not player_path.exists():
        errors.append("Missing PLAYER.md")
        return
    player_text = player_path.read_text(encoding="utf-8")
    if "## Content profile summary" not in player_text:
        warnings.append("PLAYER.md missing Content profile summary block")
    if "## Advance profile summary" not in player_text:
        warnings.append("PLAYER.md missing Advance profile summary block")
    if "## Narrative profile summary" not in player_text:
        warnings.append("PLAYER.md missing Narrative profile summary block")

    content_path = world / "setup" / "content-profile.json"
    if content_path.exists():
        content_profile = read_json(content_path, errors, "setup/content-profile.json")
        if content_profile:
            preset = content_profile.get("preset")
            if preset and f"- content_preset: {preset}" not in player_text:
                errors.append("PLAYER.md content_preset summary does not match setup/content-profile.json")
            for ban in content_profile.get("player_absolute_bans", []) or []:
                if str(ban).strip() and str(ban) not in player_text:
                    errors.append(f"PLAYER.md content_absolute_bans summary missing ban: {ban}")

    advance_path = world / "setup" / "advance-profile.json"
    if advance_path.exists():
        advance_profile = read_json(advance_path, errors, "setup/advance-profile.json")
        if advance_profile:
            default_preset = advance_profile.get("default_preset")
            if default_preset and f"- advance_default_preset: {default_preset}" not in player_text:
                errors.append("PLAYER.md advance_default_preset summary does not match setup/advance-profile.json")

    narrative_path = world / "setup" / "narrative-profile.json"
    if narrative_path.exists():
        narrative_profile = read_json(narrative_path, errors, "setup/narrative-profile.json")
        if narrative_profile:
            default_profile = narrative_profile.get("default_profile")
            if default_profile and f"- narrative_default_profile: {default_profile}" not in player_text:
                errors.append("PLAYER.md narrative_default_profile summary does not match setup/narrative-profile.json")


def validate_world_rules(world: Path, errors: list[str], warnings: list[str]) -> None:
    path = world / "setup" / "world-rules.json"
    if not path.exists():
        errors.append("Missing setup/world-rules.json")
        return
    data = read_json(path, errors, "setup/world-rules.json")
    if not data:
        return
    if data.get("schema") != "be-a-god.world-rules.v1":
        errors.append("world-rules has unexpected schema")
    rules = data.get("rules")
    if not isinstance(rules, list):
        errors.append("world-rules rules must be a list")
        return
    seen = set()
    valid_scope = {"global", "regional", "local", "branch", "character", "custom"}
    valid_status = {"active", "superseded", "revoked"}
    for rule in rules:
        if not isinstance(rule, dict):
            errors.append("world-rules entry must be an object")
            continue
        rule_id = rule.get("rule_id")
        if not rule_id:
            errors.append("world-rules entry missing rule_id")
            continue
        if rule_id in seen:
            errors.append(f"duplicate world rule id: {rule_id}")
        seen.add(rule_id)
        if not rule.get("text"):
            errors.append(f"world rule `{rule_id}` missing text")
        if rule.get("scope") not in valid_scope:
            errors.append(f"world rule `{rule_id}` has invalid scope `{rule.get('scope')}`")
        if rule.get("status") not in valid_status:
            errors.append(f"world rule `{rule_id}` has invalid status `{rule.get('status')}`")
        if not isinstance(rule.get("replaces", []), list):
            errors.append(f"world rule `{rule_id}` replaces must be a list")
        if not isinstance(rule.get("tags", []), list):
            errors.append(f"world rule `{rule_id}` tags must be a list")


def validate_event_graph(world: Path, active: dict[str, str], branch: Path, errors: list[str], warnings: list[str]) -> None:
    path = world / "indexes" / "event-graph.json"
    if not path.exists():
        warnings.append("Derived file missing: indexes/event-graph.json")
        return
    graph = read_json(path, errors, "indexes/event-graph.json")
    if not graph:
        return
    if graph.get("schema") != "be-a-god.event-graph.v1":
        errors.append("event-graph has unexpected schema")
    if graph.get("branch_id") != active.get("branch_id", "main"):
        errors.append("event-graph branch_id does not match ACTIVE.md")
    nodes = graph.get("nodes")
    if not isinstance(nodes, list):
        errors.append("event-graph nodes must be a list")
        return
    node_ids = {node.get("id") for node in nodes if isinstance(node, dict)}
    event_ids = set()
    for event_path in sorted((branch / "events").glob("EVT-*.md")):
        text = event_path.read_text(encoding="utf-8")
        event_ids.add(parse_field(text, "id") or event_path.stem)
    missing_nodes = sorted(event_ids - node_ids)
    if missing_nodes:
        errors.append(f"event-graph missing event nodes: {missing_nodes}")
    links = graph.get("links", [])
    if not isinstance(links, list):
        errors.append("event-graph links must be a list")
    else:
        for link in links:
            if not isinstance(link, dict):
                errors.append("event-graph link must be an object")
                continue
            if not link.get("source") or not link.get("target") or not link.get("kind"):
                errors.append(f"event-graph link missing source/target/kind: {link}")
    unresolved_refs = graph.get("unresolved_refs", [])
    if not isinstance(unresolved_refs, list):
        errors.append("event-graph unresolved_refs must be a list")
    else:
        for ref in unresolved_refs:
            if isinstance(ref, dict):
                warnings.append(f"event-graph unresolved {ref.get('field')} reference `{ref.get('ref')}` from {ref.get('event_id')}")


def validate_branch_tree(world: Path, active: dict[str, str], branch: Path, errors: list[str], warnings: list[str]) -> None:
    story_tree = world / "story" / "STORY-TREE.md"
    tree_text = story_tree.read_text(encoding="utf-8") if story_tree.exists() else ""
    active_branch_path = active.get("branch_path", "story/main")
    active_branch_id = active.get("branch_id", "main")
    if active_branch_path != "story/main":
        if active_branch_path not in tree_text or active_branch_id not in tree_text:
            errors.append(f"Active child branch is missing from STORY-TREE.md: {active_branch_id} {active_branch_path}")

    save_path = branch / "SAVE.md"
    if save_path.exists():
        save_text = save_path.read_text(encoding="utf-8")
        parent_save = parse_field(save_text, "parent_save")
        if parent_save and parent_save not in {"none", "None", "null"} and not (world / parent_save).exists():
            errors.append(f"Active branch parent_save points to missing file: {parent_save}")

    for draft_json in sorted((world / "story").glob("**/runtime/branch-drafts/*/draft.json")):
        rel = draft_json.relative_to(world).as_posix()
        draft = read_json(draft_json, errors, rel)
        if not draft:
            continue
        if draft.get("schema") != "be-a-god.branch-draft.v1":
            errors.append(f"Branch draft has unexpected schema: {rel}")
        status = draft.get("status")
        if status not in {"draft", "consumed"}:
            errors.append(f"Branch draft has invalid status `{status}`: {rel}")
        parent_branch_path = draft.get("parent_branch_path")
        if parent_branch_path and not (world / parent_branch_path / "SAVE.md").exists():
            errors.append(f"Branch draft parent branch is missing: {parent_branch_path}")
        branch_path = draft.get("branch_path")
        if status == "draft" and branch_path and (world / branch_path).exists():
            warnings.append(f"Draft branch path already exists before consumption: {branch_path}")
        if status == "consumed":
            created_branch_path = draft.get("created_branch_path") or branch_path
            if not created_branch_path or not (world / created_branch_path / "SAVE.md").exists():
                errors.append(f"Consumed branch draft points to missing created branch: {rel}")
            if created_branch_path and created_branch_path not in tree_text:
                errors.append(f"Consumed branch draft created branch missing from STORY-TREE.md: {created_branch_path}")


def validate(world: Path) -> tuple[list[str], list[str]]:
    errors = []
    warnings = []
    if not world.exists() or not world.is_dir():
        return [f"World directory not found: {world}"], warnings

    for rel in REQUIRED_WORLD_FILES:
        if not (world / rel).exists():
            errors.append(f"Missing required file: {rel}")

    if errors:
        return errors, warnings

    active = parse_active(world)
    branch = validate_world_relative_path(world, active.get("branch_path", ""), "branch_path", errors)
    save_pointer = validate_world_relative_path(world, active.get("save_path", ""), "save_path", errors)
    if errors:
        return errors, warnings
    assert branch is not None
    assert save_pointer is not None
    if not branch.exists():
        errors.append(f"Active branch path missing: {active['branch_path']}")
        return errors, warnings

    for rel in REQUIRED_BRANCH_PATHS:
        if not (branch / rel).exists():
            errors.append(f"Missing active branch path: {active['branch_path']}/{rel}")

    save_path = save_pointer
    expected_save_path = (branch / "SAVE.md").resolve()
    if save_path != expected_save_path:
        errors.append(f"ACTIVE.md save_path must point to active branch SAVE.md: {active.get('save_path')}")
    if save_path.exists():
        save_text = save_path.read_text(encoding="utf-8")
        save_branch = parse_field(save_text, "branch_id")
        if save_branch and save_branch != active.get("branch_id"):
            errors.append(f"SAVE.md branch_id `{save_branch}` does not match ACTIVE.md `{active.get('branch_id')}`")
        latest_event = parse_field(save_text, "latest_event")
        if latest_event and latest_event != "none" and not list((branch / "events").glob(f"{latest_event}*.md")):
            warnings.append(f"latest_event not found in events directory: {latest_event}")

    for path in sorted((branch / "events").glob("EVT-*.md")):
        text = path.read_text(encoding="utf-8")
        event_id = parse_field(text, "id")
        if event_id and not path.name.startswith(event_id):
            warnings.append(f"Event id `{event_id}` does not match filename: {path.relative_to(world).as_posix()}")

    manifest_path = world / "system" / "file-manifest.json"
    if not manifest_path.exists():
        warnings.append("system/file-manifest.json is missing")
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for item in manifest.get("files", []):
                rel = item.get("path")
                if not rel:
                    continue
                manifest_target = validate_world_relative_path(world, rel, "manifest file path", errors)
                if manifest_target and not manifest_target.exists():
                    warnings.append(f"Manifest references missing file: {rel}")
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid file-manifest.json: {exc}")

    for rel in ["indexes/entities.json", "indexes/locations.json", "indexes/events.json", "dashboard/timeline.json", "dashboard/data.json", "dashboard/map-layers.json"]:
        path = world / rel
        if not path.exists():
            warnings.append(f"Derived file missing: {rel}")
            continue
        data = read_json(path, errors, rel)
        if data is not None:
            validate_derived_json(rel, data, world, active, errors, warnings)

    validate_queue(branch, world, errors, warnings)
    validate_random(branch, world, errors, warnings)
    validate_state_cards(branch, world, errors, warnings)
    validate_handoffs(branch, world, errors, warnings)
    validate_action_requests(branch, world, errors, warnings)
    validate_divine_assessments(branch, world, errors, warnings)
    validate_rule_checks(branch, world, errors, warnings)
    validate_resume_packets(branch, world, errors, warnings)

    validate_content_profile(world, errors, warnings)
    validate_advance_profile(world, errors, warnings)
    validate_narrative_profile(world, errors, warnings)
    validate_llm_api_config(world, errors, warnings)
    validate_player_summaries(world, errors, warnings)
    validate_world_rules(world, errors, warnings)
    validate_event_graph(world, active, branch, errors, warnings)
    validate_branch_tree(world, active, branch, errors, warnings)

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a be-a-god world.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    errors, warnings = validate(world)
    result = {"world": str(world), "ok": not errors, "errors": errors, "warnings": warnings}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("World validation OK" if not errors else "World validation FAILED")
        for warning in warnings:
            print(f"WARNING: {warning}")
        for error in errors:
            print(f"ERROR: {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
