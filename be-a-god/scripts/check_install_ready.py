#!/usr/bin/env python3
"""Read-only install readiness check for the be-a-god skill package."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


SKILL_NAME = "be-a-god"

REQUIRED_DIRS = [
    "agents",
    "assets",
    "assets/world-template",
    "assets/frontend-template",
    "assets/frontend-template/img",
    "assets/narrative-templates",
    "references",
    "scripts",
]

REQUIRED_FILES = [
    "SKILL.md",
    "agents/openai.yaml",
    "references/storage-contract.md",
    "references/game-master-protocol.md",
    "references/frontend-contract.md",
    "references/narrative-quality.md",
    "references/narrative-template-guide.md",
    "references/script-catalog.md",
    "references/validation-scenarios.md",
    "references/player-quickstart.md",
    "assets/world-template/WORLD-BRIEF.template.md",
    "assets/world-template/SAVE.template.md",
    "assets/world-template/content-profile.template.json",
    "assets/world-template/advance-profile.template.json",
    "assets/world-template/narrative-profile.template.json",
    "assets/world-template/llm-api.config.template.json",
    "assets/frontend-template/index.html",
    "assets/frontend-template/styles.css",
    "assets/frontend-template/app.js",
    "assets/frontend-template/img/flag-marker.png",
    "assets/frontend-template/img/forest-stamp.png",
    "assets/frontend-template/img/forest-cluster-stamp.png",
    "assets/frontend-template/img/hills-stamp.png",
    "assets/frontend-template/img/rocky-hills-stamp.png",
    "assets/frontend-template/img/mountain-ridge-stamp.png",
    "assets/frontend-template/img/creek-stamp.png",
    "assets/frontend-template/img/castle-stamp.png",
    "assets/frontend-template/img/village-stamp.png",
    "assets/frontend-template/img/bridge-stamp.png",
    "assets/frontend-template/img/road-stamp.png",
    "assets/frontend-template/img/farm-stamp.png",
    "assets/frontend-template/img/ruins-stamp.png",
    "assets/frontend-template/img/marsh-stamp.png",
    "assets/frontend-template/img/lake-stamp.png",
    "assets/frontend-template/img/shore-rocks-stamp.png",
    "assets/frontend-template/img/parchment-overlay.png",
    "assets/frontend-template/img/corner-ornament.png",
    "assets/frontend-template/img/ui-frame.png",
    "assets/frontend-template/img/hex-grassland.png",
    "assets/frontend-template/img/hex-forest.png",
    "assets/frontend-template/img/hex-hills.png",
    "assets/frontend-template/img/hex-mountain.png",
    "assets/frontend-template/img/hex-river.png",
    "assets/frontend-template/img/hex-lake.png",
    "assets/frontend-template/img/hex-marsh.png",
    "assets/frontend-template/img/hex-desert.png",
    "assets/frontend-template/img/hex-village.png",
    "assets/frontend-template/img/hex-castle.png",
    "assets/frontend-template/img/hex-farm.png",
    "assets/frontend-template/img/hex-ruins.png",
    "assets/frontend-template/sample-dashboard.json",
    "assets/frontend-template/sample-timeline.json",
    "assets/frontend-template/sample-map-layers.json",
    "assets/narrative-templates/interaction-result.template.json",
    "assets/narrative-templates/queued-event-result.template.json",
    "assets/narrative-templates/character-seed.template.json",
    "assets/narrative-templates/faction-pressure.template.json",
    "assets/narrative-templates/divine-intervention-result.template.json",
    "scripts/init_world.py",
    "scripts/create_demo_world.py",
    "scripts/call_llm.py",
    "scripts/external_play_turn.py",
    "scripts/serve_frontend.py",
    "scripts/validate_world_brief.py",
    "scripts/validate_settlement_result.py",
    "scripts/smoke_test.py",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_frontmatter(skill_md: str) -> tuple[dict[str, str], str | None]:
    if not skill_md.startswith("---\n"):
        return {}, "SKILL.md must start with YAML frontmatter"
    end = skill_md.find("\n---\n", 4)
    if end == -1:
        return {}, "SKILL.md frontmatter must close with ---"

    raw = skill_md[4:end]
    data: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            return data, f"invalid frontmatter line: {line}"
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        data[key] = value
    return data, None


def add_result(results: list[dict[str, Any]], level: str, check: str, message: str, **extra: Any) -> None:
    item: dict[str, Any] = {"level": level, "check": check, "message": message}
    item.update(extra)
    results.append(item)


def validate_metadata(skill_dir: Path, results: list[dict[str, Any]]) -> None:
    skill_path = skill_dir / "SKILL.md"
    if not skill_path.exists():
        add_result(results, "error", "metadata", "missing SKILL.md")
        return

    text = read_text(skill_path)
    data, error = parse_frontmatter(text)
    if error:
        add_result(results, "error", "metadata", error)
        return

    keys = sorted(data.keys())
    if keys != ["description", "name"]:
        add_result(results, "error", "metadata", "frontmatter must contain only name and description", keys=keys)
    else:
        add_result(results, "ok", "metadata", "frontmatter contains only name and description")

    name = data.get("name", "")
    if name != SKILL_NAME:
        add_result(results, "error", "metadata", f"skill name must be {SKILL_NAME}", found=name)
    else:
        add_result(results, "ok", "metadata", "skill name matches folder")

    if skill_dir.name != SKILL_NAME:
        add_result(results, "error", "metadata", f"skill folder must be named {SKILL_NAME}", found=skill_dir.name)
    else:
        add_result(results, "ok", "metadata", "folder name matches skill name")

    description = data.get("description", "")
    if len(description) < 80 or "TODO" in description.upper():
        add_result(results, "error", "metadata", "description is too short or still contains TODO", length=len(description))
    else:
        add_result(results, "ok", "metadata", "description is trigger-ready", length=len(description))


def validate_dirs_and_files(skill_dir: Path, results: list[dict[str, Any]]) -> None:
    for rel in REQUIRED_DIRS:
        path = skill_dir / rel
        if path.is_dir():
            add_result(results, "ok", "directory", f"found {rel}")
        else:
            add_result(results, "error", "directory", f"missing directory {rel}")

    for rel in REQUIRED_FILES:
        path = skill_dir / rel
        if path.is_file():
            add_result(results, "ok", "file", f"found {rel}")
        else:
            add_result(results, "error", "file", f"missing file {rel}")


def validate_openai_yaml(skill_dir: Path, results: list[dict[str, Any]]) -> None:
    path = skill_dir / "agents" / "openai.yaml"
    if not path.exists():
        return
    text = read_text(path)
    required_fragments = [
        "display_name:",
        "short_description:",
        "default_prompt:",
        "$be-a-god",
        "allow_implicit_invocation:",
    ]
    missing = [fragment for fragment in required_fragments if fragment not in text]
    if missing:
        add_result(results, "error", "agents", "openai.yaml is missing required UI metadata fragments", missing=missing)
    else:
        add_result(results, "ok", "agents", "openai.yaml contains required UI metadata")

    capability_fragments = [
        "Markdown",
        "map pieces",
        "timeline",
        "chronicle",
        "branch saves",
        "random logs",
        "lightweight context",
    ]
    capability_missing = [fragment for fragment in capability_fragments if fragment not in text]
    if capability_missing:
        add_result(results, "warning", "agents", "openai.yaml may not describe current core capabilities", missing=capability_missing)
    else:
        add_result(results, "ok", "agents", "openai.yaml describes current core capabilities")


def validate_references(skill_dir: Path, results: list[dict[str, Any]]) -> None:
    skill_text = read_text(skill_dir / "SKILL.md") if (skill_dir / "SKILL.md").exists() else ""
    refs = [
        "storage-contract.md",
        "game-master-protocol.md",
        "frontend-contract.md",
        "narrative-quality.md",
        "narrative-template-guide.md",
        "script-catalog.md",
        "validation-scenarios.md",
        "player-quickstart.md",
    ]
    missing_mentions = [ref for ref in refs if f"references/{ref}" not in skill_text]
    if missing_mentions:
        add_result(results, "error", "references", "SKILL.md does not route to every core reference", missing=missing_mentions)
    else:
        add_result(results, "ok", "references", "SKILL.md routes to all core references")

    direct_workflow_scripts = [
        "detect_manual_edits.py",
        "create_action_request.py",
        "cancel_action_request.py",
        "reorder_action_requests.py",
        "call_llm.py",
        "external_play_turn.py",
        "create_demo_world.py",
        "build_map_layers.py",
        "set_map_brush.py",
        "build_timeline.py",
        "export_dashboard.py",
        "prepare_frontend.py",
        "serve_frontend.py",
        "build_ignored_digest.py",
        "resolve_random.py",
        "set_attention.py",
        "set_advance_profile.py",
        "set_content_profile.py",
        "set_world_rule.py",
        "create_entity.py",
        "move_entity.py",
        "wander_entities.py",
        "update_action_request.py",
        "check_world_rules.py",
        "queue_event.py",
        "advance_world.py",
        "settle_queued_event.py",
        "create_handoff.py",
        "resume_world.py",
        "draft_branch.py",
        "create_branch.py",
        "switch_branch.py",
        "install_local_skill.py",
    ]
    missing_script_routes = [script for script in direct_workflow_scripts if f"scripts/{script}" not in skill_text]
    if missing_script_routes:
        add_result(results, "error", "references", "SKILL.md must route to every direct player workflow script", missing=missing_script_routes)
    else:
        add_result(results, "ok", "references", "SKILL.md routes to direct player workflow scripts")

    required_workflow_fragments = [
        "set_attention.py --world <world> --target-id <id> --state <ignored|followed|normal> --confirmed",
        "set_advance_profile.py --world <world> ... --confirmed",
        "set_content_profile.py --world <world> ... --confirmed",
        "create_entity.py --world <world> --kind <kind> --name <name> --confirmed",
        "move_entity.py --world <world> --entity-id <id> ... --confirmed",
        "create_action_request.py --world <world> --action terrain-brush --target-id MAP --target-kind world",
        "set_map_brush.py --world <world> --brush-id <id> --kind <river|tributary|hills|forest|custom> --points-json <json> --confirmed",
        "wander_entities.py --world <world> --confirmed",
        "switch_branch.py --world <world> --branch-path <path> --confirmed",
        "advance_world.py --world <world> --preset <preset-id> --confirmed",
        "cancel_action_request.py --world <world> --request-id <id> --confirmed",
        "reorder_action_requests.py --world <world> --request-id <id> ... --confirmed",
        "update_action_request.py",
        "check_world_rules.py",
        "queue_event.py --world <world> ... --confirmed",
        "create_handoff.py --world <world> --confirmed",
        "resume_world.py --world <world> --dry-run",
        "call_llm.py --world <world> --packet <packet-path> --prompt <instruction> --json",
        "external_play_turn.py --world <world> --target-id <id> --intent <intent> --confirmed --json",
        "external_play_turn.py --world <world> --packet <packet-id-or-path> --prompt <instruction> --call --confirmed --json",
        "create_demo_world.py --worlds-dir <worlds-dir> --world-id <world-id> --confirmed --json",
        "serve_frontend.py --world <world>",
        "draft_branch.py --world <world> --branch-id <branch-id> --fork-event <event-id> --change-summary <summary> ... --confirmed",
        "create_branch.py --world <world> --draft-id <id> --confirmed",
        "install_local_skill.py --skill-dir <skill-dir> --dry-run --json",
    ]
    missing_workflow_fragments = [fragment for fragment in required_workflow_fragments if fragment not in skill_text]
    if missing_workflow_fragments:
        add_result(results, "error", "references", "SKILL.md missing required direct workflow command fragments", missing=missing_workflow_fragments)
    else:
        add_result(results, "ok", "references", "SKILL.md preserves required direct workflow command fragments")


def validate_script_catalog(skill_dir: Path, results: list[dict[str, Any]]) -> None:
    catalog_path = skill_dir / "references" / "script-catalog.md"
    scripts_dir = skill_dir / "scripts"
    if not catalog_path.exists() or not scripts_dir.exists():
        return
    catalog = read_text(catalog_path)
    actual = sorted(path.name for path in scripts_dir.glob("*.py"))
    documented = sorted(set(re.findall(r"`scripts/([^`]+?\.py)`", catalog)))
    undocumented = [name for name in actual if name not in documented]
    missing = [name for name in documented if not (scripts_dir / name).exists()]
    if undocumented or missing:
        add_result(
            results,
            "error",
            "script-catalog",
            "script catalog and scripts directory are out of sync",
            undocumented=undocumented,
            missing=missing,
        )
    else:
        add_result(results, "ok", "script-catalog", "script catalog matches scripts directory", count=len(actual))


def validate_validation_scenarios(skill_dir: Path, results: list[dict[str, Any]]) -> None:
    path = skill_dir / "references" / "validation-scenarios.md"
    if not path.exists():
        return
    text = read_text(path)
    headings = re.findall(r"^##\s+(\d+)\.\s+(.+)$", text, re.MULTILINE)
    numbers = [int(number) for number, _title in headings]
    expected_numbers = list(range(1, max(numbers) + 1)) if numbers else []
    required_titles = [
        "Direct workflow routing",
        "Advance preset routing",
        "Future event queue confirmation",
        "Branch action request routing",
        "Interaction target resolution",
        "Path-backed id safety",
        "Active pointer path safety",
        "Manifest path safety",
        "Branch state snapshot inheritance",
        "Mutable terrain brush rendering",
        "Command terrain brush action routing",
        "Brush editor preview routing",
        "External model API host boundary",
        "External model packaged turn",
        "Local frontend app API boundary",
        "Hybrid historical narrative profile",
        "Settlement result quality gate",
        "Brush editor controlled styling",
        "Playable demo world generation",
        "Narrative template minimal set",
        "Map zoom and pan",
        "Medieval transparent PNG map assets",
    ]
    missing_titles = [title for title in required_titles if title not in text]
    if not numbers or max(numbers) < 38 or numbers != expected_numbers or missing_titles:
        add_result(
            results,
            "error",
            "validation-scenarios",
            "validation scenarios are stale or missing required coverage",
            count=len(numbers),
            max_number=max(numbers) if numbers else 0,
            numbers=numbers,
            missing_titles=missing_titles,
        )
    else:
        add_result(results, "ok", "validation-scenarios", "validation scenarios cover current core gates", count=len(numbers), max_number=max(numbers))


def validate_path_backed_id_safety(skill_dir: Path, results: list[dict[str, Any]]) -> None:
    scripts_dir = skill_dir / "scripts"
    required_script_markers = {
        "create_action_request.py": ["SAFE_ID_PATTERN", "validate_id", "--request-id"],
        "update_action_request.py": ["SAFE_ID_PATTERN", "validate_id", "--request-id"],
        "make_interaction_packet.py": ["SAFE_ID_PATTERN", "validate_id", "--packet-id", "--request-id"],
        "settle_interaction.py": ["SAFE_ID_PATTERN", "validate_id", "--packet"],
        "draft_branch.py": ["SAFE_ID_PATTERN", "validate_id", "--draft-id"],
        "create_branch.py": ["SAFE_ID_PATTERN", "validate_id", "--draft-id"],
        "create_handoff.py": ["SAFE_ID_PATTERN", "validate_id", "--handoff-id"],
        "resume_world.py": ["SAFE_ID_PATTERN", "validate_id", "--resume-id"],
        "check_world_rules.py": ["SAFE_ID_PATTERN", "validate_id", "--check-id", "--request-id"],
        "assess_divine_action.py": ["SAFE_ID_PATTERN", "validate_id", "--assessment-id"],
        "set_content_profile.py": ["SAFE_ID_PATTERN", "validate_id", "--soften-request-id"],
        "detect_manual_edits.py": ["SAFE_ID_PATTERN", "validate_id", "--report-id"],
        "apply_manual_edits.py": ["SAFE_ID_PATTERN", "validate_id", "--report-id"],
        "checkpoint.py": ["SAFE_ID_PATTERN", "validate_id", "--checkpoint-id"],
        "set_map_brush.py": ["SAFE_ID_PATTERN", "validate_id", "--brush-id"],
        "external_play_turn.py": ["SAFE_ID_PATTERN", "validate_id", "--run-id", "--packet-id", "--request-id"],
    }
    missing: dict[str, list[str]] = {}
    for script_name, markers in required_script_markers.items():
        path = scripts_dir / script_name
        if not path.exists():
            missing[script_name] = ["script missing"]
            continue
        text = read_text(path)
        script_missing = [marker for marker in markers if marker not in text]
        if script_missing:
            missing[script_name] = script_missing

    smoke = read_text(scripts_dir / "smoke_test.py") if (scripts_dir / "smoke_test.py").exists() else ""
    required_smoke_markers = [
        "did not reject unsafe request id",
        "did not reject unsafe packet id",
        "did not reject unsafe draft id",
        "did not reject unsafe handoff id",
        "did not reject unsafe resume id",
        "did not reject unsafe check id",
        "did not reject unsafe assessment id",
        "did not reject unsafe soften request id",
        "did not reject unsafe report id",
        "did not reject unsafe checkpoint id",
        "did not reject unsafe brush id",
        "did not reject unsafe run id",
    ]
    missing_smoke = [marker for marker in required_smoke_markers if marker not in smoke]

    if missing or missing_smoke:
        add_result(
            results,
            "error",
            "path-backed-id-safety",
            "path-backed ID safety markers are missing",
            missing_script_markers=missing,
            missing_smoke_markers=missing_smoke,
        )
    else:
        add_result(results, "ok", "path-backed-id-safety", "path-backed ID safety is covered by scripts and smoke tests", scripts=len(required_script_markers))


def validate_frontend_assets(skill_dir: Path, results: list[dict[str, Any]]) -> None:
    frontend = skill_dir / "assets" / "frontend-template"
    expected_schemas = {
        "sample-dashboard.json": "be-a-god.dashboard.v1",
        "sample-timeline.json": "be-a-god.timeline.v1",
        "sample-map-layers.json": "be-a-god.map-layers.v1",
    }
    schema_errors = []
    for name, expected_schema in expected_schemas.items():
        path = frontend / name
        if not path.exists():
            schema_errors.append({"file": name, "error": "missing"})
            continue
        try:
            data = json.loads(read_text(path))
        except json.JSONDecodeError as exc:
            schema_errors.append({"file": name, "error": str(exc)})
            continue
        if data.get("schema") != expected_schema:
            schema_errors.append({"file": name, "schema": data.get("schema"), "expected": expected_schema})

    app_path = frontend / "app.js"
    index_path = frontend / "index.html"
    css_path = frontend / "styles.css"
    marker_errors = []
    if app_path.exists():
        app_text = read_text(app_path)
        required_app_markers = [
            "generateWorldBrief",
            "open-tutorial",
            "tutorial-dialog",
            "actionRequestActionLabel",
            "actionRequestSummary",
            "待处理：",
            "create_action_request.py",
            "/api/health",
            "/api/state",
            "/api/action-request",
            "/api/advance-world",
            "/api/action-request/cancel",
            "/api/action-requests/reorder",
            "submitBackendActionRequest",
            "submitBackendAdvanceWorld",
            "submitBackendCancelActionRequest",
            "submitBackendActionRequestOrder",
            "pendingFrontendAction",
            "setPendingFrontendAction",
            "submitPendingFrontendAction",
            "HEX_LEVELS",
            "renderHexGrid",
            "renderHexUnit",
            "nearestHexCenter",
            "hexTileMetrics",
            "terrainAssetForKind",
            "hexGrassland",
            "hex-terrain-img",
            "draggedActionRequestId",
            "draggable = true",
            "request-cancel",
            "--preset",
            "--action branch",
            "--action terrain-brush",
            "promptBranchDraft",
            "promptTerrainBrushDraft",
            "commandJsonArg",
            "weather-override",
            "set-rule",
            "terrain-brush",
            "brushEditorPayload",
            "emitBrushEditorCommand",
            "handleBrushEditorMapClick",
            "brush-editor-preview",
            "brush-editor-width",
            "brush-editor-density",
            "brush-editor-jitter",
            "brush-editor-color",
            "brush-editor-points-json",
            "copyBrushEditorPoints",
            "undoBrushEditorPoint",
            "defaultBrushStyle",
            "syncBrushEditorOutputs",
            "ignore",
            "follow",
            "validateMapLayersData",
            "escapeHtml(JSON.stringify",
            "renderMapDecorations",
            "renderBrushSvg",
            "normalizeBrushPoint",
            "mapLayers.brushes",
            "narrative_profile",
            "renderNarrativeProfile",
            "narrative-profile",
            "terrain-layer",
            "compass-rose",
            "scale-bar",
            "map-legend",
            "classToken",
            "MAP_ASSETS",
            "MAP_ZOOM",
            "MAP_LEVELS",
            "mapLevelForScale",
            "opacityForLevel",
            "applyZoomFade",
            "applyZoomFadeToRenderedMap",
            "currentMapMode",
            "selectedActionTarget",
            "terrainZones",
            "renderUnitRoster",
            "unit-roster",
            "resetMapView",
            "handleMapWheel",
            "beginMapPan",
            "map-content",
            "renderBrushAssetStamps",
            "MAP_DECOR_STAMPS",
            "renderMapBackdropStamps",
            "nodeAssetName",
            "uiFrame",
            "castle",
            "village",
            "bridge",
            "road",
            "farm",
            "ruins",
            "marsh",
            "lake",
        ]
        missing = [marker for marker in required_app_markers if marker not in app_text]
        if missing:
            marker_errors.append({"file": "app.js", "missing": missing})
    if index_path.exists():
        index_text = read_text(index_path)
        required_index_markers = ["open-tutorial", "tutorial-dialog", "tutorial-page", "tutorial-grid", "tutorial-mini-map", "creation-dialog", "timeline", "branch-action", "terrain-brush-action", "commit-action", "pending-action-status", "clear-pending-action", "brush-editor", "brush-editor-command", "brush-editor-width", "brush-editor-density", "brush-editor-jitter", "brush-editor-color", "brush-editor-points-json", "brush-editor-undo", "brush-editor-copy", "narrative-profile", "ignore", "follow", "map-view-tools", "map-zoom-in", "map-zoom-out", "map-zoom-reset", "map-zoom-label", "map-zoom-mode", "zoom-depth", "<details", "<summary>"]
        missing = [marker for marker in required_index_markers if marker not in index_text]
        if missing:
            marker_errors.append({"file": "index.html", "missing": missing})
    if css_path.exists():
        css_text = read_text(css_path)
        required_css_markers = [
            "--paper-map",
            "--parchment-texture",
            "--ink-outline",
            "--comic-shadow",
            ".map::before",
            ".map::after",
            ".terrain-layer",
            ".brush-svg",
            ".brush-river",
            ".brush-forest",
            ".brush-hills",
            ".brush-editor-card",
            ".brush-editor-grid",
            ".brush-editor-preview",
            ".brush-editor-active",
            ".commit-panel",
            ".hex-grid",
            ".hex-tile",
            ".hex-unit",
            ".compass-rose",
            ".scale-bar",
            ".map-legend",
            ".map-content",
            ".map-view-tools",
            ".zoom-depth",
            "corner-ornament.png",
            ".terrain-stamp",
            ".terrain-forest",
            ".terrain-hills",
            ".terrain-river",
            ".map-decor-stamp",
            ".decor-castle",
            ".decor-village",
            ".decor-road",
            ".map-corner-ornament",
            ".piece::before",
            ".pin::before",
            ".map-node::before",
            ".brush-editor-card summary",
            ".requests-card summary",
            ".request-title",
            ".request-summary",
            ".request-id",
            ".request-row",
            ".request-cancel",
            ".dragging",
            ".drag-over",
            ".piece::after",
            ".piece.wandering",
            ".piece.followed",
            ".piece.paused",
            ".piece.dead",
            ".tutorial-dialog",
            ".tutorial-page",
            ".tutorial-hero",
            ".tutorial-grid",
            ".tutorial-card",
            ".tutorial-mini-map",
        ]
        missing = [marker for marker in required_css_markers if marker not in css_text]
        if missing:
            marker_errors.append({"file": "styles.css", "missing": missing})

    img_dir = frontend / "img"
    image_errors = []
    for name in [
        "flag-marker.png",
        "forest-stamp.png",
        "forest-cluster-stamp.png",
        "hills-stamp.png",
        "rocky-hills-stamp.png",
        "mountain-ridge-stamp.png",
        "creek-stamp.png",
        "castle-stamp.png",
        "village-stamp.png",
        "bridge-stamp.png",
        "road-stamp.png",
        "farm-stamp.png",
        "ruins-stamp.png",
        "marsh-stamp.png",
        "lake-stamp.png",
        "shore-rocks-stamp.png",
        "parchment-overlay.png",
        "corner-ornament.png",
        "ui-frame.png",
        "hex-grassland.png",
        "hex-forest.png",
        "hex-hills.png",
        "hex-mountain.png",
        "hex-river.png",
        "hex-lake.png",
        "hex-marsh.png",
        "hex-desert.png",
        "hex-village.png",
        "hex-castle.png",
        "hex-farm.png",
        "hex-ruins.png",
    ]:
        path = img_dir / name
        if not path.exists():
            image_errors.append({"file": f"img/{name}", "error": "missing"})
            continue
        with path.open("rb") as handle:
            header = handle.read(8)
        if header != b"\x89PNG\r\n\x1a\n":
            image_errors.append({"file": f"img/{name}", "error": "not a png"})
    if image_errors:
        marker_errors.append({"file": "img", "missing": image_errors})

    if schema_errors or marker_errors:
        add_result(results, "error", "frontend-assets", "frontend template assets failed schema or route marker checks", schema_errors=schema_errors, marker_errors=marker_errors)
    else:
        add_result(results, "ok", "frontend-assets", "frontend sample schemas and route markers are current")


def validate_narrative_templates(skill_dir: Path, results: list[dict[str, Any]]) -> None:
    templates_dir = skill_dir / "assets" / "narrative-templates"
    expected = {
        "interaction-result.template.json",
        "queued-event-result.template.json",
        "character-seed.template.json",
        "faction-pressure.template.json",
        "divine-intervention-result.template.json",
    }
    errors: list[dict[str, Any]] = []
    actual = {path.name for path in templates_dir.glob("*.json")} if templates_dir.exists() else set()
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        errors.append({"missing": missing})
    if extra:
        errors.append({"extra": extra})
    for name in sorted(expected & actual):
        path = templates_dir / name
        try:
            data = json.loads(read_text(path))
        except Exception as exc:
            errors.append({"file": name, "error": str(exc)})
            continue
        if data.get("schema") not in {"be-a-god.settlement-template.v1", "be-a-god.semantic-template.v1"}:
            errors.append({"file": name, "schema": data.get("schema")})
        if not data.get("template") or not data.get("use_when"):
            errors.append({"file": name, "error": "missing template or use_when"})
    guide = read_text(skill_dir / "references" / "narrative-template-guide.md") if (skill_dir / "references" / "narrative-template-guide.md").exists() else ""
    for marker in sorted(expected):
        if marker not in guide:
            errors.append({"guide_missing": marker})
    if errors:
        add_result(results, "error", "narrative-templates", "narrative templates failed minimal-set checks", errors=errors)
    else:
        add_result(results, "ok", "narrative-templates", "narrative templates are compact and routed", count=len(expected))


def validate_script_compile(skill_dir: Path, results: list[dict[str, Any]]) -> None:
    scripts = sorted((skill_dir / "scripts").glob("*.py"))
    if not scripts:
        add_result(results, "error", "scripts", "no Python scripts found")
        return

    failures = []
    for script in scripts:
        try:
            source = read_text(script)
            compile(source, str(script), "exec")
        except SyntaxError as exc:
            failures.append({"script": script.name, "error": str(exc)})

    if failures:
        add_result(results, "error", "scripts", "one or more Python scripts failed to compile", failures=failures)
    else:
        add_result(results, "ok", "scripts", "all Python scripts compile", count=len(scripts))


def run_smoke(skill_dir: Path, results: list[dict[str, Any]]) -> None:
    smoke = skill_dir / "scripts" / "smoke_test.py"
    if not smoke.exists():
        add_result(results, "error", "smoke", "missing smoke_test.py")
        return

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    completed = subprocess.run(
        [sys.executable, str(smoke)],
        cwd=str(skill_dir),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=120,
    )
    if completed.returncode == 0:
        add_result(results, "ok", "smoke", "smoke_test.py passed", stdout=completed.stdout.strip())
    else:
        add_result(
            results,
            "error",
            "smoke",
            "smoke_test.py failed",
            returncode=completed.returncode,
            stdout=completed.stdout[-4000:],
            stderr=completed.stderr[-4000:],
        )


def inspect_install_target(skill_dir: Path, results: list[dict[str, Any]]) -> dict[str, Any]:
    codex_home = os.environ.get("CODEX_HOME")
    target_parent = Path(codex_home) / "skills" if codex_home else Path.home() / ".codex" / "skills"
    target_skill_dir = target_parent / skill_dir.name
    info = {
        "codex_home": codex_home,
        "target_parent": str(target_parent),
        "target_skill_dir": str(target_skill_dir),
        "target_parent_exists": target_parent.exists(),
        "target_exists": target_skill_dir.exists(),
        "would_overwrite": target_skill_dir.exists(),
    }
    if target_skill_dir.exists():
        add_result(results, "warning", "install-target", "global skill target already exists; copying would overwrite or collide", **info)
    else:
        add_result(results, "ok", "install-target", "global skill target is free", **info)
    return info


def validate_text_encoding(skill_dir: Path, results: list[dict[str, Any]]) -> None:
    extensions = {".md", ".yaml", ".yml", ".json", ".py", ".html", ".css", ".js"}
    bad = []
    replacement = []
    for path in skill_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            bad.append({"path": str(path.relative_to(skill_dir)), "error": str(exc)})
            continue
        if "\ufffd" in text:
            replacement.append(str(path.relative_to(skill_dir)))

    if bad or replacement:
        add_result(results, "error", "encoding", "UTF-8 text validation failed", decode_errors=bad, replacement_chars=replacement)
    else:
        add_result(results, "ok", "encoding", "all text files decode as UTF-8 without replacement characters")


def build_report(skill_dir: Path, run_smoke_test: bool) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    skill_dir = skill_dir.resolve()

    validate_metadata(skill_dir, results)
    validate_dirs_and_files(skill_dir, results)
    validate_openai_yaml(skill_dir, results)
    validate_references(skill_dir, results)
    validate_script_catalog(skill_dir, results)
    validate_validation_scenarios(skill_dir, results)
    validate_path_backed_id_safety(skill_dir, results)
    validate_frontend_assets(skill_dir, results)
    validate_narrative_templates(skill_dir, results)
    validate_text_encoding(skill_dir, results)
    validate_script_compile(skill_dir, results)
    target = inspect_install_target(skill_dir, results)
    if run_smoke_test:
        run_smoke(skill_dir, results)

    errors = [item for item in results if item["level"] == "error"]
    warnings = [item for item in results if item["level"] == "warning"]
    return {
        "skill_dir": str(skill_dir),
        "skill_name": SKILL_NAME,
        "ready": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "install_target": target,
        "results": results,
    }


def print_text_report(report: dict[str, Any]) -> None:
    status = "READY" if report["ready"] else "NOT READY"
    print(f"Install readiness: {status}")
    print(f"Skill: {report['skill_name']}")
    print(f"Path: {report['skill_dir']}")
    print(f"Errors: {report['error_count']} | Warnings: {report['warning_count']}")
    print(f"Target: {report['install_target']['target_skill_dir']}")
    for item in report["results"]:
        level = item["level"].upper()
        check = item["check"]
        message = item["message"]
        print(f"[{level}] {check}: {message}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether the local be-a-god skill package is ready to install.")
    parser.add_argument("--skill-dir", default=str(Path(__file__).resolve().parents[1]), help="Path to the skill folder.")
    parser.add_argument("--run-smoke", action="store_true", help="Also run scripts/smoke_test.py.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    report = build_report(Path(args.skill_dir), args.run_smoke)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text_report(report)
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
