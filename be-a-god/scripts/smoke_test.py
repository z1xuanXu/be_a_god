#!/usr/bin/env python3
"""Run a local smoke test for the be-a-god skill scripts."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent
SKILL = SCRIPTS.parent


def child_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    return env


def run(args: list[str], *, capture: bool = True) -> subprocess.CompletedProcess:
    completed = subprocess.run(
        [sys.executable, *args],
        check=False,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        env=child_env(),
    )
    if completed.returncode != 0:
        raise SystemExit(
            json.dumps(
                {
                    "failed_command": [sys.executable, *args],
                    "returncode": completed.returncode,
                    "stdout": completed.stdout[-4000:] if completed.stdout else "",
                    "stderr": completed.stderr[-4000:] if completed.stderr else "",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    return completed


def run_expect_fail(args: list[str]) -> subprocess.CompletedProcess:
    completed = subprocess.run(
        [sys.executable, *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=child_env(),
    )
    if completed.returncode == 0:
        raise SystemExit(
            json.dumps(
                {
                    "unexpected_success": [sys.executable, *args],
                    "stdout": completed.stdout[-4000:] if completed.stdout else "",
                    "stderr": completed.stderr[-4000:] if completed.stderr else "",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    return completed


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="be-a-god-smoke-") as td:
        root = Path(td)
        brief = root / "brief.md"
        worlds = root / "worlds"
        run(
            [
                str(SCRIPTS / "create_world_brief.py"),
                "--output",
                str(brief),
                "--world-id",
                "river-world",
                "--world-premise",
                "河流文明在洪水周期中生存。",
                "--starting-era",
                "青铜末期",
                "--starting-region",
                "河湾集市",
                "--god-role",
                "河与契约之神",
                "--absolute-prohibition",
                "不能轻描淡写誓言代价",
                "--tone",
                "史诗但克制",
                "--content-ban",
                "禁止描写玩家明确排除的场景",
            ]
        )
        brief_text = brief.read_text(encoding="utf-8")
        if "## Field source map" not in brief_text or "- World premise: player-locked" not in brief_text or "- Geography: ai-fill" not in brief_text:
            raise SystemExit("create_world_brief.py did not include field source map")
        if "## Content boundary" not in brief_text or "- absolute bans:" not in brief_text or "禁止描写玩家明确排除的场景" not in brief_text:
            raise SystemExit("create_world_brief.py did not include content-ban list")
        run([str(SCRIPTS / "validate_world_brief.py"), str(brief), "--json"])
        brief.write_text(brief.read_text(encoding="utf-8").replace("Status: draft", "Status: confirmed"), encoding="utf-8")
        run([str(SCRIPTS / "validate_world_brief.py"), str(brief), "--require-confirmed", "--json"])
        invalid_brief = root / "invalid-brief.md"
        invalid_brief.write_text("# WORLD-BRIEF\n\n## Player-locked facts\n\n- World premise: incomplete\n\n## Field source map\n\n- World premise: player-locked\n- Geography: ai-fill\n\n## Confirmation\n\nStatus: confirmed\n", encoding="utf-8")
        invalid_validation = run_expect_fail([str(SCRIPTS / "validate_world_brief.py"), str(invalid_brief), "--require-confirmed", "--json"])
        if "Required confirmed field is missing or blank" not in (invalid_validation.stdout + invalid_validation.stderr):
            raise SystemExit("validate_world_brief.py did not reject confirmed brief with missing required fields")
        no_source_map_brief = root / "no-source-map-brief.md"
        no_source_map_brief.write_text("# WORLD-BRIEF\n\n## Player-locked facts\n\n- World premise: complete\n- Starting era: era\n- Starting region: region\n- God role: god\n\n## Polishable facts\n\n- Tone: tone\n\n## Confirmation\n\nStatus: confirmed\n", encoding="utf-8")
        no_source_map_validation = run_expect_fail([str(SCRIPTS / "validate_world_brief.py"), str(no_source_map_brief), "--require-confirmed", "--json"])
        if "Confirmed WORLD-BRIEF must include a Field source map" not in (no_source_map_validation.stdout + no_source_map_validation.stderr):
            raise SystemExit("validate_world_brief.py did not reject confirmed brief missing source map")
        run([str(SCRIPTS / "init_world.py"), "--worlds-dir", str(worlds), "--world-id", "river-world", "--title", "河流世界", "--brief", str(brief), "--confirmed"])
        world = worlds / "river-world"
        world_spec = json.loads((world / "setup" / "world-spec.json").read_text(encoding="utf-8"))
        if world_spec.get("creation_fields", {}).get("god_role") != "河与契约之神":
            raise SystemExit("init_world.py did not preserve god role from WORLD-BRIEF")
        if world_spec.get("creation_field_sources", {}).get("God role") != "player-locked":
            raise SystemExit("init_world.py did not preserve field source map")
        if "不能轻描淡写誓言代价" not in world_spec.get("creation_fields", {}).get("absolute_prohibitions", []):
            raise SystemExit("init_world.py did not preserve absolute prohibitions list")
        if "禁止描写玩家明确排除的场景" not in world_spec.get("creation_fields", {}).get("content_bans", []):
            raise SystemExit("init_world.py did not preserve content bans in world-spec")
        llm_template = json.loads((SKILL / "assets" / "world-template" / "llm-api.config.template.json").read_text(encoding="utf-8"))
        if llm_template.get("schema") != "be-a-god.llm-api-config.v1" or llm_template.get("api_key"):
            raise SystemExit("llm-api config template is missing schema or contains a concrete api_key")
        narrative_template = json.loads((SKILL / "assets" / "world-template" / "narrative-profile.template.json").read_text(encoding="utf-8"))
        if narrative_template.get("schema") != "be-a-god.narrative-profile.v1" or narrative_template.get("default_profile") != "hybrid-historical":
            raise SystemExit("narrative profile template is missing the hybrid-historical default")
        llm_config_path = world / "setup" / "llm-api.config.json"
        if not llm_config_path.exists():
            raise SystemExit("init_world.py did not create setup/llm-api.config.json")
        llm_config = json.loads(llm_config_path.read_text(encoding="utf-8"))
        if llm_config.get("schema") != "be-a-god.llm-api-config.v1" or llm_config.get("enabled") is not False:
            raise SystemExit("init_world.py wrote invalid default LLM API config")
        llm_preview = json.loads(
            run(
                [
                    str(SCRIPTS / "call_llm.py"),
                    "--world",
                    str(world),
                    "--prompt",
                    "只预览一次外部模型请求。",
                    "--json",
                ]
            ).stdout
        )
        if llm_preview.get("mode") != "dry-run" or llm_preview.get("request", {}).get("model") != llm_config.get("model"):
            raise SystemExit("call_llm.py dry-run did not build a model request from setup/llm-api.config.json")
        if llm_preview.get("config", {}).get("api_key") not in ("", None):
            raise SystemExit("call_llm.py dry-run leaked an API key value")
        llm_user_prompt = llm_preview.get("request", {}).get("messages", [{}, {}])[1].get("content", "")
        for marker in ["## Narrative profile", "hybrid-historical", "settlement_plan"]:
            if marker not in llm_user_prompt:
                raise SystemExit(f"call_llm.py dry-run did not include narrative profile marker {marker}")
        if "不能轻描淡写誓言代价" not in (world / "WORLD.md").read_text(encoding="utf-8"):
            raise SystemExit("init_world.py did not mirror absolute prohibitions into WORLD.md")
        content_profile = json.loads((world / "setup" / "content-profile.json").read_text(encoding="utf-8"))
        if "禁止描写玩家明确排除的场景" not in content_profile.get("player_absolute_bans", []):
            raise SystemExit("init_world.py did not preserve content bans in content-profile.json")
        narrative_profile = json.loads((world / "setup" / "narrative-profile.json").read_text(encoding="utf-8"))
        default_narrative = narrative_profile.get("profiles", {}).get(narrative_profile.get("default_profile"), {})
        if narrative_profile.get("default_profile") != "hybrid-historical":
            raise SystemExit("init_world.py did not create the hybrid-historical narrative profile")
        for marker in ["causality", "world_continuity", "character_agency", "historical_texture"]:
            if marker not in default_narrative.get("priority_order", []):
                raise SystemExit(f"narrative profile missing priority marker {marker}")
        for marker in ["visible_narration", "gm_summary", "settlement_plan"]:
            if marker not in default_narrative.get("output_layers", {}).get("required", []):
                raise SystemExit(f"narrative profile missing output layer {marker}")
        for marker in ["character", "resource", "institution", "environment"]:
            if marker not in default_narrative.get("event_pressure_sources", []):
                raise SystemExit(f"narrative profile missing pressure source {marker}")
        if "god_view" not in default_narrative.get("character_fields", {}).get("required", []):
            raise SystemExit("narrative profile missing character god_view field")
        player_text = (world / "PLAYER.md").read_text(encoding="utf-8")
        if "- content_preset:" not in player_text:
            raise SystemExit("init_world.py did not mirror content preset summary into PLAYER.md")
        for content_ban in content_profile.get("player_absolute_bans", []):
            if content_ban and content_ban not in player_text:
                raise SystemExit("init_world.py did not mirror content bans summary into PLAYER.md")
        save_text = (world / "story" / "main" / "SAVE.md").read_text(encoding="utf-8")
        if "河与契约之神" not in player_text or "河湾集市" not in save_text:
            raise SystemExit("init_world.py did not copy creation brief fields into PLAYER.md and SAVE.md")
        structure_check = run([str(SCRIPTS / "validate_world_structure.py"), str(world)])
        if "World structure OK" not in structure_check.stdout:
            raise SystemExit("validate_world_structure.py did not accept initialized world")
        active_path = world / "ACTIVE.md"
        valid_active_text = active_path.read_text(encoding="utf-8")
        active_path.write_text(valid_active_text.replace("branch_path: story/main", "branch_path: ../outside"), encoding="utf-8")
        unsafe_active_validation = run_expect_fail([str(SCRIPTS / "validate_world.py"), "--world", str(world), "--json"])
        if "branch_path points outside world" not in (unsafe_active_validation.stdout + unsafe_active_validation.stderr):
            raise SystemExit("validate_world.py did not reject ACTIVE.md branch_path outside world")
        active_path.write_text(valid_active_text, encoding="utf-8")
        event_graph_preview = json.loads(run([str(SCRIPTS / "build_event_graph.py"), "--world", str(world), "--dry-run"]).stdout)
        if event_graph_preview.get("schema") != "be-a-god.event-graph.v1" or not any(node.get("id") == "EVT-0001" for node in event_graph_preview.get("nodes", [])):
            raise SystemExit("build_event_graph.py dry-run did not index initial event")
        run([str(SCRIPTS / "build_event_graph.py"), "--world", str(world)])
        if not (world / "indexes" / "event-graph.json").exists():
            raise SystemExit("build_event_graph.py did not write indexes/event-graph.json")
        manifest_path = world / "system" / "file-manifest.json"
        valid_manifest_text = manifest_path.read_text(encoding="utf-8")
        manifest_data = json.loads(valid_manifest_text)
        manifest_data["files"].append({"path": "../outside.md", "authority": "core", "sha256": "bad", "bytes": 0})
        manifest_path.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        unsafe_manifest_validation = run_expect_fail([str(SCRIPTS / "validate_world.py"), "--world", str(world), "--json"])
        if "manifest file path points outside world" not in (unsafe_manifest_validation.stdout + unsafe_manifest_validation.stderr):
            raise SystemExit("validate_world.py did not reject manifest path outside world")
        manifest_path.write_text(valid_manifest_text, encoding="utf-8")
        initial_advance_profile = json.loads((world / "setup" / "advance-profile.json").read_text(encoding="utf-8"))
        if initial_advance_profile.get("default_preset") != "hybrid":
            raise SystemExit("init_world.py did not create default advance profile")
        if "## Advance profile summary" not in player_text or "- advance_default_preset: hybrid" not in player_text:
            raise SystemExit("init_world.py did not mirror advance profile summary into PLAYER.md")
        if "## Narrative profile summary" not in player_text or "- narrative_default_profile: hybrid-historical" not in player_text:
            raise SystemExit("init_world.py did not mirror narrative profile summary into PLAYER.md")
        initial_dashboard = json.loads((world / "dashboard" / "data.json").read_text(encoding="utf-8"))
        if initial_dashboard.get("advance_profile", {}).get("default_preset") != "hybrid" or not initial_dashboard.get("advance_profile", {}).get("presets"):
            raise SystemExit("init_world.py did not export initial advance profile summary")
        if initial_dashboard.get("narrative_profile", {}).get("default_profile") != "hybrid-historical":
            raise SystemExit("init_world.py did not export initial narrative profile summary")
        if "latest_random" not in initial_dashboard:
            raise SystemExit("init_world.py did not initialize latest_random dashboard field")
        narrative_path = world / "setup" / "narrative-profile.json"
        valid_narrative_text = narrative_path.read_text(encoding="utf-8")
        broken_narrative = json.loads(valid_narrative_text)
        broken_narrative["profiles"]["hybrid-historical"]["output_layers"]["required"].remove("settlement_plan")
        narrative_path.write_text(json.dumps(broken_narrative, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        broken_narrative_validation = run_expect_fail([str(SCRIPTS / "validate_world.py"), "--world", str(world), "--json"])
        if "output_layers.required missing layers" not in (broken_narrative_validation.stdout + broken_narrative_validation.stderr):
            raise SystemExit("validate_world.py did not reject broken narrative output layers")
        narrative_path.write_text(valid_narrative_text, encoding="utf-8")
        rule_report = json.loads(
            run(
                [
                    str(SCRIPTS / "set_world_rule.py"),
                    "--world",
                    str(world),
                    "--rule-id",
                    "RULE-RIVER-OATH",
                    "--text",
                    "River oaths cannot be broken without a visible omen.",
                    "--scope",
                    "global",
                    "--tag",
                    "oath,river",
                    "--confirmed",
                    "--json",
                ]
            ).stdout
        )
        if rule_report.get("rule", {}).get("rule_id") != "RULE-RIVER-OATH":
            raise SystemExit("set_world_rule.py did not create the requested rule")
        rules = json.loads((world / "setup" / "world-rules.json").read_text(encoding="utf-8"))
        if not any(rule.get("rule_id") == "RULE-RIVER-OATH" for rule in rules.get("rules", [])):
            raise SystemExit("world-rules.json did not include created rule")
        if "RULE-RIVER-OATH" not in (world / "CANON.md").read_text(encoding="utf-8"):
            raise SystemExit("CANON.md did not include structured world rule")
        timeline_with_rule = json.loads(run([str(SCRIPTS / "build_timeline.py"), "--world", str(world), "--dry-run"]).stdout)
        if not any(node.get("state") == "locked" and node.get("event_id") == "RULE-RIVER-OATH" for node in timeline_with_rule.get("nodes", [])):
            raise SystemExit("build_timeline.py did not include locked world rule node")

        traits = root / "mira-traits.json"
        traits.write_text(
            json.dumps({"personality": "谨慎、记忆力强，不轻易承认神谕。", "desire": "保护河湾集市。"}, ensure_ascii=False),
            encoding="utf-8",
        )
        failed_entity_id = run_expect_fail([str(SCRIPTS / "create_entity.py"), "--world", str(world), "--kind", "character", "--entity-id", "../BAD", "--name", "Bad", "--confirmed"])
        if "--entity-id must contain only" not in (failed_entity_id.stderr + failed_entity_id.stdout):
            raise SystemExit("create_entity.py did not reject unsafe entity id")
        failed_entity_slug = run_expect_fail([str(SCRIPTS / "create_entity.py"), "--world", str(world), "--kind", "character", "--entity-id", "CHAR-BAD", "--name", "Bad", "--slug", "../bad", "--confirmed"])
        if "--slug must contain only" not in (failed_entity_slug.stderr + failed_entity_slug.stdout):
            raise SystemExit("create_entity.py did not reject unsafe slug")
        run(
            [
                str(SCRIPTS / "create_entity.py"),
                "--world",
                str(world),
                "--kind",
                "location",
                "--entity-id",
                "LOC-001",
                "--name",
                "河湾集市",
                "--slug",
                "river-market",
                "--level",
                "scene",
                "--x",
                "42",
                "--y",
                "61",
                "--confirmed",
                "--json",
            ]
        )
        run(
            [
                str(SCRIPTS / "create_entity.py"),
                "--world",
                str(world),
                "--kind",
                "location",
                "--entity-id",
                "LOC-002",
                "--name",
                "芦苇渡口",
                "--slug",
                "reed-ford",
                "--level",
                "scene",
                "--x",
                "73",
                "--y",
                "26",
                "--confirmed",
                "--json",
            ]
        )
        run(
            [
                str(SCRIPTS / "create_entity.py"),
                "--world",
                str(world),
                "--kind",
                "character",
                "--entity-id",
                "CHAR-0001",
                "--name",
                "米拉",
                "--slug",
                "mira",
                "--location",
                "LOC-001",
                "--status",
                "plot-ready",
                "--traits-json",
                str(traits),
                "--confirmed",
                "--json",
            ]
        )
        entity = world / "story" / "main" / "state" / "entities" / "CHAR-0001-mira.md"
        location_packet = json.loads(
            run(
                [
                    str(SCRIPTS / "make_interaction_packet.py"),
                    "--world",
                    str(world),
                    "--target-id",
                    "LOC-001",
                    "--target-kind",
                    "location",
                    "--intent",
                    "观察集市",
                    "--packet-id",
                    "IP-LOC-SMOKE",
                    "--dry-run",
                ]
            ).stdout
        )
        if location_packet.get("target", {}).get("file") != "story/main/state/locations/LOC-001-river-market.md":
            raise SystemExit("location interaction packet did not resolve state/locations card")
        if not any(rule.get("rule_id") == "RULE-RIVER-OATH" for rule in location_packet.get("world_rules", {}).get("active", [])):
            raise SystemExit("interaction packet did not include active world rule summary")
        decoy_entity = world / "story" / "main" / "state" / "entities" / "CHAR-0002-decoy.md"
        decoy_entity.write_text(
            "# CHAR-0002 Decoy\n\n- id: CHAR-0002\n- kind: character\n- name: Decoy\n- summary: This card mentions CHAR-0001 but must not be moved when CHAR-0001 is requested.\n",
            encoding="utf-8",
        )
        move_report = json.loads(
            run(
                [
                    str(SCRIPTS / "move_entity.py"),
                    "--world",
                    str(world),
                    "--entity-id",
                    "CHAR-0001",
                    "--x",
                    "50",
                    "--y",
                    "62",
                    "--status",
                    "wandering",
                    "--note",
                    "米拉巡视上涨的河水。",
                    "--confirmed",
                    "--json",
                ]
            ).stdout
        )
        if move_report.get("changes", {}).get("status") != "wandering":
            raise SystemExit("move_entity.py did not report movement changes")
        dashboard_after_move = json.loads((world / "dashboard" / "data.json").read_text(encoding="utf-8"))
        mira_piece = next((piece for piece in dashboard_after_move.get("pieces", []) if piece.get("id") == "CHAR-0001"), None)
        if not mira_piece or mira_piece.get("x") != 50.0 or mira_piece.get("status") != "wandering":
            raise SystemExit("move_entity.py did not update dashboard piece")
        decoy_text = decoy_entity.read_text(encoding="utf-8")
        if "- x: 50" in decoy_text or "- status: wandering" in decoy_text:
            raise SystemExit("move_entity.py moved a text-reference decoy instead of the exact entity id")
        decoy_entity.write_text(decoy_text.replace("- id: CHAR-0002", "- id: ../BAD"), encoding="utf-8")
        unsafe_state_validation = run_expect_fail([str(SCRIPTS / "validate_world.py"), "--world", str(world), "--json"])
        if "unsafe filename characters" not in (unsafe_state_validation.stdout + unsafe_state_validation.stderr):
            raise SystemExit("validate_world.py did not reject unsafe state card id")
        decoy_entity.write_text(decoy_text, encoding="utf-8")
        exact_interaction_packet = json.loads(
            run(
                [
                    str(SCRIPTS / "make_interaction_packet.py"),
                    "--world",
                    str(world),
                    "--target-id",
                    "CHAR-0001",
                    "--target-kind",
                    "character",
                    "--intent",
                    "快速观察",
                    "--packet-id",
                    "IP-EXACT-SMOKE",
                    "--dry-run",
                ]
            ).stdout
        )
        if exact_interaction_packet.get("target", {}).get("file") != "story/main/state/entities/CHAR-0001-mira.md":
            raise SystemExit("make_interaction_packet.py resolved a text-reference decoy instead of the exact entity id")
        if exact_interaction_packet.get("narrative_profile", {}).get("default_profile") != "hybrid-historical":
            raise SystemExit("make_interaction_packet.py did not include compact narrative profile")
        if not any(source.get("path") == "setup/narrative-profile.json" for source in exact_interaction_packet.get("context_policy", {}).get("allowed_sources", [])):
            raise SystemExit("make_interaction_packet.py did not include narrative profile source pointer")
        ambiguous_packet = run_expect_fail(
            [
                str(SCRIPTS / "make_interaction_packet.py"),
                "--world",
                str(world),
                "--target-id",
                "CHAR",
                "--target-kind",
                "character",
                "--intent",
                "快速观察",
                "--dry-run",
            ]
        )
        if "ambiguous" not in (ambiguous_packet.stdout + ambiguous_packet.stderr):
            raise SystemExit("make_interaction_packet.py did not reject ambiguous target prefix")
        outside_target = root / "outside-target.md"
        outside_target.write_text("# Outside\n\n- id: OUTSIDE\n", encoding="utf-8")
        outside_target_packet = run_expect_fail(
            [
                str(SCRIPTS / "make_interaction_packet.py"),
                "--world",
                str(world),
                "--target-id",
                "OUTSIDE",
                "--target-kind",
                "object",
                "--intent",
                "读取外部文件",
                "--target-file",
                str(outside_target),
                "--dry-run",
            ]
        )
        if "outside world directory" not in (outside_target_packet.stdout + outside_target_packet.stderr):
            raise SystemExit("make_interaction_packet.py did not reject outside target-file")
        failed_packet_id = run_expect_fail(
            [
                str(SCRIPTS / "make_interaction_packet.py"),
                "--world",
                str(world),
                "--target-id",
                "CHAR-0001",
                "--target-kind",
                "character",
                "--intent",
                "unsafe packet id must fail",
                "--packet-id",
                "../BAD",
                "--dry-run",
            ]
        )
        if "packet-id must contain" not in (failed_packet_id.stderr + failed_packet_id.stdout):
            raise SystemExit("make_interaction_packet.py did not reject unsafe packet id")
        failed_packet_request_id = run_expect_fail(
            [
                str(SCRIPTS / "make_interaction_packet.py"),
                "--world",
                str(world),
                "--target-id",
                "CHAR-0001",
                "--target-kind",
                "character",
                "--intent",
                "unsafe request id must fail",
                "--request-id",
                "../BAD",
                "--dry-run",
            ]
        )
        if "request-id must contain" not in (failed_packet_request_id.stderr + failed_packet_request_id.stdout):
            raise SystemExit("make_interaction_packet.py did not reject unsafe request id")
        wander_report = json.loads(
            run(
                [
                    str(SCRIPTS / "wander_entities.py"),
                    "--world",
                    str(world),
                    "--entity-id",
                    "CHAR-0001",
                    "--override",
                    "CHAR-0001=LOC-002",
                    "--confirmed",
                    "--json",
                ]
            ).stdout
        )
        if not wander_report.get("moves") or wander_report["moves"][0].get("mode") != "override":
            raise SystemExit("wander_entities.py did not record override movement")
        dashboard_after_wander = json.loads((world / "dashboard" / "data.json").read_text(encoding="utf-8"))
        mira_after_wander = next((piece for piece in dashboard_after_wander.get("pieces", []) if piece.get("id") == "CHAR-0001"), None)
        if not mira_after_wander or mira_after_wander.get("location") != "LOC-002" or mira_after_wander.get("x") != 73:
            raise SystemExit("wander_entities.py did not update dashboard destination")
        random_log_after_wander = (world / "story" / "main" / "random" / "random-log.jsonl").read_text(encoding="utf-8")
        if '"kind": "wander"' not in random_log_after_wander or '"mode": "override"' not in random_log_after_wander:
            raise SystemExit("wander_entities.py did not append wander override random log")

        action_request = json.loads(
            run(
                [
                    str(SCRIPTS / "create_action_request.py"),
                    "--world",
                    str(world),
                    "--action",
                    "intervene",
                    "--target-id",
                    "CHAR-0001",
                    "--target-kind",
                    "character",
                    "--intent",
                    "send a dream omen",
                    "--request-id",
                    "AR-SMOKE",
                    "--confirmed",
                    "--json",
                ]
            ).stdout
        )
        failed_action_request_id = run_expect_fail(
            [
                str(SCRIPTS / "create_action_request.py"),
                "--world",
                str(world),
                "--action",
                "observe",
                "--target-id",
                "CHAR-0001",
                "--target-kind",
                "character",
                "--intent",
                "unsafe request id must fail",
                "--request-id",
                "../BAD",
                "--confirmed",
            ]
        )
        if "request-id must contain" not in (failed_action_request_id.stderr + failed_action_request_id.stdout):
            raise SystemExit("create_action_request.py did not reject unsafe request id")
        action_request_path = world / "story" / "main" / "runtime" / "action-requests" / "AR-SMOKE" / "request.json"
        if not action_request_path.exists() or not action_request_path.with_name("request.md").exists():
            raise SystemExit("create_action_request.py did not write request files")
        action_request_data = json.loads(action_request_path.read_text(encoding="utf-8"))
        if action_request_data.get("action") != "intervene" or action_request_data.get("context_policy", {}).get("canonical_effect") != "none":
            raise SystemExit("action request changed canonical policy")
        if "make_interaction_packet.py" not in action_request.get("suggested_command", ""):
            raise SystemExit("intervention action request did not suggest interaction packet")
        if "--request-id AR-SMOKE" not in action_request.get("suggested_command", ""):
            raise SystemExit("intervention action request did not carry request id into suggested packet command")
        ignore_request = json.loads(
            run(
                [
                    str(SCRIPTS / "create_action_request.py"),
                    "--world",
                    str(world),
                    "--action",
                    "ignore",
                    "--target-id",
                    "CHAR-0001",
                    "--target-kind",
                    "character",
                    "--intent",
                    "ignore this character until clicked",
                    "--request-id",
                    "AR-IGNORE-SMOKE",
                    "--confirmed",
                    "--json",
                ]
            ).stdout
        )
        if "set_attention.py" not in ignore_request.get("suggested_command", "") or "--confirmed" not in ignore_request.get("suggested_command", ""):
            raise SystemExit("ignore action request did not suggest confirmed attention update")
        ignore_request_path = world / "story" / "main" / "runtime" / "action-requests" / "AR-IGNORE-SMOKE" / "request.json"
        valid_ignore_request = json.loads(ignore_request_path.read_text(encoding="utf-8"))
        stale_ignore_request = json.loads(json.dumps(valid_ignore_request))
        stale_ignore_request["suggested_command"] = stale_ignore_request["suggested_command"].replace(" --confirmed", "")
        ignore_request_path.write_text(json.dumps(stale_ignore_request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        stale_action_validation = run_expect_fail([str(SCRIPTS / "validate_world.py"), "--world", str(world), "--json"])
        if "confirmed attention update" not in (stale_action_validation.stdout + stale_action_validation.stderr):
            raise SystemExit("validate_world.py did not reject stale ignore action suggested command")
        ignore_request_path.write_text(json.dumps(valid_ignore_request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        advance_request = json.loads(
            run(
                [
                    str(SCRIPTS / "create_action_request.py"),
                    "--world",
                    str(world),
                    "--action",
                    "advance-time",
                    "--preset",
                    "hybrid",
                    "--intent",
                    "preset:hybrid",
                    "--request-id",
                    "AR-ADVANCE-SMOKE",
                    "--confirmed",
                    "--json",
                ]
            ).stdout
        )
        if "advance_world.py" not in advance_request.get("suggested_command", "") or "--preset hybrid" not in advance_request.get("suggested_command", ""):
            raise SystemExit("advance-time action request did not preserve selected advance preset")
        reorder_request = json.loads(
            run(
                [
                    str(SCRIPTS / "reorder_action_requests.py"),
                    "--world",
                    str(world),
                    "--request-id",
                    "AR-ADVANCE-SMOKE",
                    "--request-id",
                    "AR-SMOKE",
                    "--request-id",
                    "AR-IGNORE-SMOKE",
                    "--confirmed",
                    "--json",
                ]
            ).stdout
        )
        priority_path = world / "story" / "main" / "runtime" / "action-requests" / "priority-order.json"
        priority_data = json.loads(priority_path.read_text(encoding="utf-8"))
        if reorder_request.get("request_ids", [None])[0] != "AR-ADVANCE-SMOKE" or priority_data.get("request_ids", [None])[0] != "AR-ADVANCE-SMOKE":
            raise SystemExit("reorder_action_requests.py did not preserve requested priority order")
        dashboard_with_priority = json.loads(run([str(SCRIPTS / "export_dashboard.py"), "--world", str(world), "--dry-run"]).stdout)
        if dashboard_with_priority.get("pending_action_requests", [{}])[0].get("request_id") != "AR-ADVANCE-SMOKE":
            raise SystemExit("export_dashboard.py did not apply action request priority order")
        cancel_result = json.loads(
            run(
                [
                    str(SCRIPTS / "cancel_action_request.py"),
                    "--world",
                    str(world),
                    "--request-id",
                    "AR-ADVANCE-SMOKE",
                    "--confirmed",
                    "--json",
                ]
            ).stdout
        )
        cancelled_data = json.loads((world / "story" / "main" / "runtime" / "action-requests" / "AR-ADVANCE-SMOKE" / "request.json").read_text(encoding="utf-8"))
        if cancel_result.get("status") != "cancelled" or cancelled_data.get("status") != "cancelled":
            raise SystemExit("cancel_action_request.py did not mark request cancelled")
        dashboard_after_cancel = json.loads(run([str(SCRIPTS / "export_dashboard.py"), "--world", str(world), "--dry-run"]).stdout)
        if "AR-ADVANCE-SMOKE" in {item.get("request_id") for item in dashboard_after_cancel.get("pending_action_requests", [])}:
            raise SystemExit("cancelled action request still appears as pending")
        branch_request = json.loads(
            run(
                [
                    str(SCRIPTS / "create_action_request.py"),
                    "--world",
                    str(world),
                    "--action",
                    "branch",
                    "--target-id",
                    "EVT-0001",
                    "--target-kind",
                    "event",
                    "--payload-json",
                    "{\"branch_id\":\"save-mira-request\",\"fork_event\":\"EVT-0001\",\"change_summary\":\"save Mira instead\"}",
                    "--request-id",
                    "AR-BRANCH-SMOKE",
                    "--confirmed",
                    "--json",
                ]
            ).stdout
        )
        if (
            "draft_branch.py" not in branch_request.get("suggested_command", "")
            or "--branch-id save-mira-request" not in branch_request.get("suggested_command", "")
            or "--fork-event EVT-0001" not in branch_request.get("suggested_command", "")
            or "--confirmed" not in branch_request.get("suggested_command", "")
        ):
            raise SystemExit("branch action request did not suggest confirmed branch draft")
        branch_request_path = world / "story" / "main" / "runtime" / "action-requests" / "AR-BRANCH-SMOKE" / "request.json"
        valid_branch_request = json.loads(branch_request_path.read_text(encoding="utf-8"))
        stale_branch_request = json.loads(json.dumps(valid_branch_request))
        stale_branch_request["suggested_command"] = stale_branch_request["suggested_command"].replace(" --branch-id save-mira-request", "")
        branch_request_path.write_text(json.dumps(stale_branch_request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        stale_branch_validation = run_expect_fail([str(SCRIPTS / "validate_world.py"), "--world", str(world), "--json"])
        if "confirmed branch draft" not in (stale_branch_validation.stdout + stale_branch_validation.stderr):
            raise SystemExit("validate_world.py did not reject stale branch action suggested command")
        branch_request_path.write_text(json.dumps(valid_branch_request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        terrain_request = json.loads(
            run(
                [
                    str(SCRIPTS / "create_action_request.py"),
                    "--world",
                    str(world),
                    "--action",
                    "terrain-brush",
                    "--target-id",
                    "MAP",
                    "--target-kind",
                    "world",
                    "--intent",
                    "draw a new tributary from the upper river",
                    "--payload-json",
                    "{\"brush_id\":\"BRUSH-CMD-SMOKE\",\"kind\":\"tributary\",\"change_summary\":\"draw a new tributary from the upper river\",\"points_json\":\"[[16,20],[24,27],[37,44]]\",\"width\":4,\"density\":9}",
                    "--request-id",
                    "AR-TERRAIN-SMOKE",
                    "--confirmed",
                    "--json",
                ]
            ).stdout
        )
        if (
            "set_map_brush.py" not in terrain_request.get("suggested_command", "")
            or "--brush-id BRUSH-CMD-SMOKE" not in terrain_request.get("suggested_command", "")
            or "--kind tributary" not in terrain_request.get("suggested_command", "")
            or "--points-json" not in terrain_request.get("suggested_command", "")
            or "--confirmed" not in terrain_request.get("suggested_command", "")
        ):
            raise SystemExit("terrain-brush action request did not suggest confirmed map brush update")
        terrain_request_path = world / "story" / "main" / "runtime" / "action-requests" / "AR-TERRAIN-SMOKE" / "request.json"
        valid_terrain_request = json.loads(terrain_request_path.read_text(encoding="utf-8"))
        stale_terrain_request = json.loads(json.dumps(valid_terrain_request))
        stale_terrain_request["suggested_command"] = re.sub(r"\s--points-json\s+'?\[\[16,20\],\[24,27\],\[37,44\]\]'?", "", stale_terrain_request["suggested_command"])
        terrain_request_path.write_text(json.dumps(stale_terrain_request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        stale_terrain_validation = run_expect_fail([str(SCRIPTS / "validate_world.py"), "--world", str(world), "--json"])
        if "terrain brush update" not in (stale_terrain_validation.stdout + stale_terrain_validation.stderr) and "brush kind and points-json" not in (stale_terrain_validation.stdout + stale_terrain_validation.stderr):
            raise SystemExit("validate_world.py did not reject stale terrain-brush action suggested command")
        terrain_request_path.write_text(json.dumps(valid_terrain_request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        failed_update_request_id = run_expect_fail([str(SCRIPTS / "update_action_request.py"), "--world", str(world), "--request-id", "../BAD", "--status", "accepted", "--confirmed"])
        if "request-id must contain" not in (failed_update_request_id.stderr + failed_update_request_id.stdout):
            raise SystemExit("update_action_request.py did not reject unsafe request id")
        update_request = json.loads(
            run(
                [
                    str(SCRIPTS / "update_action_request.py"),
                    "--world",
                    str(world),
                    "--request-id",
                    "AR-SMOKE",
                    "--status",
                    "accepted",
                    "--note",
                    "smoke accepted",
                    "--confirmed",
                    "--json",
                ]
            ).stdout
        )
        updated_action_request = json.loads(action_request_path.read_text(encoding="utf-8"))
        if update_request.get("to") != "accepted" or updated_action_request.get("status") != "accepted" or not updated_action_request.get("lifecycle"):
            raise SystemExit("update_action_request.py did not update lifecycle")
        failed_assessment_id = run_expect_fail(
            [
                str(SCRIPTS / "assess_divine_action.py"),
                "--world",
                str(world),
                "--action",
                "intervene",
                "--description",
                "unsafe assessment id must fail",
                "--assessment-id",
                "../BAD",
                "--dry-run",
            ]
        )
        if "assessment-id must contain" not in (failed_assessment_id.stderr + failed_assessment_id.stdout):
            raise SystemExit("assess_divine_action.py did not reject unsafe assessment id")
        divine_assessment = json.loads(
            run(
                [
                    str(SCRIPTS / "assess_divine_action.py"),
                    "--world",
                    str(world),
                    "--action",
                    "intervene",
                    "--target-id",
                    "CHAR-0001",
                    "--request-id",
                    "AR-SMOKE",
                    "--description",
                    "send a dream omen",
                    "--scale",
                    "regional",
                    "--irreversibility",
                    "durable",
                    "--visibility",
                    "miracle",
                    "--assessment-id",
                    "DA-SMOKE",
                    "--confirmed",
                    "--json",
                ]
            ).stdout
        )
        if divine_assessment.get("status") != "major-overreach":
            raise SystemExit("assess_divine_action.py did not flag major overreach")
        assessment_path = world / "story" / "main" / "runtime" / "divine-assessments" / "DA-SMOKE" / "assessment.json"
        assessment_data = json.loads(assessment_path.read_text(encoding="utf-8"))
        if assessment_data.get("canonical_effect") != "none" or assessment_data.get("action_request_id") != "AR-SMOKE":
            raise SystemExit("divine assessment changed canonical policy or lost request pointer")
        absolute_assessment = json.loads(
            run(
                [
                    str(SCRIPTS / "assess_divine_action.py"),
                    "--world",
                    str(world),
                    "--action",
                    "intervene",
                    "--scale",
                    "world",
                    "--irreversibility",
                    "irreversible",
                    "--visibility",
                    "miracle",
                    "--absolute",
                    "--assessment-id",
                    "DA-ABS-SMOKE",
                    "--confirmed",
                    "--json",
                ]
            ).stdout
        )
        if absolute_assessment.get("status") != "absolute-authorized":
            raise SystemExit("absolute divine assessment did not preserve absolute authority")
        weather_request = json.loads(
            run(
                [
                    str(SCRIPTS / "create_action_request.py"),
                    "--world",
                    str(world),
                    "--action",
                    "weather-override",
                    "--value",
                    "神降暴雨",
                    "--request-id",
                    "AR-WEATHER-SMOKE",
                    "--confirmed",
                    "--json",
                ]
            ).stdout
        )
        if "resolve_random.py" not in weather_request.get("suggested_command", ""):
            raise SystemExit("weather action request did not suggest random resolver")
        rule_request = json.loads(
            run(
                [
                    str(SCRIPTS / "create_action_request.py"),
                    "--world",
                    str(world),
                    "--action",
                    "set-rule",
                    "--text",
                    "No iron bridge may stand over the sacred river.",
                    "--payload-json",
                    json.dumps({"scope": "global", "tags": ["bridge", "river"]}, ensure_ascii=False),
                    "--request-id",
                    "AR-RULE-SMOKE",
                    "--confirmed",
                    "--json",
                ]
            ).stdout
        )
        if "set_world_rule.py" not in rule_request.get("suggested_command", ""):
            raise SystemExit("set-rule action request did not suggest world rule setter")
        failed_rule_check_id = run_expect_fail([str(SCRIPTS / "check_world_rules.py"), "--world", str(world), "--check-id", "../BAD", "--dry-run"])
        if "check-id must contain" not in (failed_rule_check_id.stderr + failed_rule_check_id.stdout):
            raise SystemExit("check_world_rules.py did not reject unsafe check id")
        failed_rule_request_id = run_expect_fail([str(SCRIPTS / "check_world_rules.py"), "--world", str(world), "--request-id", "../BAD", "--dry-run"])
        if "request-id must contain" not in (failed_rule_request_id.stderr + failed_rule_request_id.stdout):
            raise SystemExit("check_world_rules.py did not reject unsafe request id")
        rule_check = json.loads(
            run(
                [
                    str(SCRIPTS / "check_world_rules.py"),
                    "--world",
                    str(world),
                    "--request-id",
                    "AR-RULE-SMOKE",
                    "--check-id",
                    "RC-SMOKE",
                    "--confirmed",
                    "--json",
                ]
            ).stdout
        )
        if rule_check.get("decision") != "needs-model-review" or rule_check.get("relevant_rule_count", 0) < 1:
            raise SystemExit("check_world_rules.py did not surface relevant active rule")
        rule_check_path = world / "story" / "main" / "runtime" / "rule-checks" / "RC-SMOKE" / "check.json"
        if not rule_check_path.exists() or not rule_check_path.with_name("check.md").exists():
            raise SystemExit("check_world_rules.py did not write rule check files")
        listed_requests = json.loads(
            run([str(SCRIPTS / "list_action_requests.py"), "--world", str(world), "--pending", "--json"]).stdout
        )
        listed_ids = {item.get("request_id") for item in listed_requests.get("requests", [])}
        if {"AR-SMOKE", "AR-WEATHER-SMOKE", "AR-RULE-SMOKE", "AR-TERRAIN-SMOKE"} - listed_ids:
            raise SystemExit("list_action_requests.py did not include pending requests")
        run([str(SCRIPTS / "export_dashboard.py"), "--world", str(world)])
        dashboard_with_requests = json.loads((world / "dashboard" / "data.json").read_text(encoding="utf-8"))
        dashboard_request_ids = {item.get("request_id") for item in dashboard_with_requests.get("pending_action_requests", [])}
        if "AR-WEATHER-SMOKE" not in dashboard_request_ids:
            raise SystemExit("export_dashboard.py did not include pending action requests")
        if not any(rule.get("rule_id") == "RULE-RIVER-OATH" for rule in dashboard_with_requests.get("world_rules", {}).get("active", [])):
            raise SystemExit("export_dashboard.py did not include active world rules")

        run([str(SCRIPTS / "build_file_manifest.py"), str(world)])
        outside_manifest = root / "outside-manifest.json"
        failed_outside_manifest = run_expect_fail([str(SCRIPTS / "build_file_manifest.py"), str(world), "--output", str(outside_manifest)])
        if "output must stay inside the world directory" not in (failed_outside_manifest.stderr + failed_outside_manifest.stdout):
            raise SystemExit("build_file_manifest.py outside output failure reason changed")
        interaction_packet = json.loads(
            run(
                [
                    str(SCRIPTS / "make_interaction_packet.py"),
                    "--world",
                    str(world),
                    "--target-id",
                    "CHAR-0001",
                    "--target-kind",
                    "character",
                    "--intent",
                    "对话",
                    "--packet-id",
                    "IP-SMOKE",
                    "--request-id",
                    "AR-SMOKE",
                    "--dry-run",
                ]
            ).stdout
        )
        if interaction_packet.get("request_id") != "AR-SMOKE" or interaction_packet.get("action_request", {}).get("source") != "story/main/runtime/action-requests/AR-SMOKE/request.json":
            raise SystemExit("make_interaction_packet.py did not attach action request")
        run([str(SCRIPTS / "make_interaction_packet.py"), "--world", str(world), "--target-id", "CHAR-0001", "--target-kind", "character", "--intent", "对话", "--packet-id", "IP-SMOKE", "--request-id", "AR-SMOKE"])
        manifest_after_packet = json.loads((world / "system" / "file-manifest.json").read_text(encoding="utf-8"))
        if "story/main/runtime/interaction-packets/IP-SMOKE.json" not in {item.get("path") for item in manifest_after_packet.get("files", [])}:
            raise SystemExit("make_interaction_packet.py did not refresh manifest for packet file")
        external_turn = json.loads(
            run(
                [
                    str(SCRIPTS / "external_play_turn.py"),
                    "--world",
                    str(world),
                    "--packet",
                    "IP-SMOKE",
                    "--prompt",
                    "Preview this turn without committing canon.",
                    "--run-id",
                    "EXT-SMOKE",
                    "--confirmed",
                    "--json",
                ]
            ).stdout
        )
        if external_turn.get("mode") != "dry-run" or external_turn.get("canonical_effect") != "none":
            raise SystemExit("external_play_turn.py did not preserve dry-run canon boundary")
        external_run_dir = world / "story" / "main" / "runtime" / "external-model-runs" / "EXT-SMOKE"
        for name in ["packet.used.json", "external-run.json", "llm-response.json"]:
            if not (external_run_dir / name).exists():
                raise SystemExit(f"external_play_turn.py did not write support artifact {name}")
        external_llm_prompt = external_turn.get("llm", {}).get("request", {}).get("messages", [{}, {}])[1].get("content", "")
        for marker in ["## Narrative profile", "hybrid-historical", "settlement_plan"]:
            if marker not in external_llm_prompt:
                raise SystemExit(f"external_play_turn.py dry-run did not include narrative profile marker {marker}")
        manifest_after_external_turn = json.loads((world / "system" / "file-manifest.json").read_text(encoding="utf-8"))
        if "story/main/runtime/external-model-runs/EXT-SMOKE/external-run.json" not in {item.get("path") for item in manifest_after_external_turn.get("files", [])}:
            raise SystemExit("external_play_turn.py did not refresh manifest for external run files")
        failed_external_turn_id = run_expect_fail([str(SCRIPTS / "external_play_turn.py"), "--world", str(world), "--packet", "IP-SMOKE", "--run-id", "../BAD", "--confirmed", "--json"])
        if "run-id must contain" not in (failed_external_turn_id.stderr + failed_external_turn_id.stdout):
            raise SystemExit("external_play_turn.py did not reject unsafe run id")
        source_packet = json.loads(
            run(
                [
                    str(SCRIPTS / "read_source_packet.py"),
                    "--world",
                    str(world),
                    "--from-packet",
                    "story/main/runtime/interaction-packets/IP-SMOKE.json",
                    "--max-chars",
                    "500",
                    "--total-budget",
                    "1800",
                    "--json",
                ]
            ).stdout
        )
        if not source_packet.get("sources") or source_packet.get("used_chars", 0) <= 0:
            raise SystemExit("read_source_packet.py did not read packet sources")
        blocked_source_packet = json.loads(
            run(
                [
                    str(SCRIPTS / "read_source_packet.py"),
                    "--world",
                    str(world),
                    "--source",
                    "../outside.md",
                    "--json",
                ]
            ).stdout
        )
        if blocked_source_packet.get("sources", [{}])[0].get("allowed") is not False:
            raise SystemExit("read_source_packet.py did not block outside source")
        result = root / "settlement.json"
        result.write_text(
            json.dumps(
                {
                    "summary": "米拉承认旧身份。",
                    "event": {"title": "米拉承认旧身份", "type": "dialogue"},
                    "state_appends": [{"path": "story/main/state/entities/CHAR-0001-mira.md", "text": "- last_interaction: 米拉承认旧身份。"}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        summary_only_result = root / "summary-only-settlement.json"
        summary_only_result.write_text(json.dumps({"summary": "只有漂亮文字，没有可结算后果。"}, ensure_ascii=False), encoding="utf-8")
        failed_result_validation = run_expect_fail([str(SCRIPTS / "validate_settlement_result.py"), "--result", str(summary_only_result), "--kind", "interaction", "--json"])
        if "no concrete settlement plan" not in (failed_result_validation.stdout + failed_result_validation.stderr):
            raise SystemExit("validate_settlement_result.py did not reject prose-only settlement result")
        failed_summary_only_settlement = run_expect_fail([str(SCRIPTS / "settle_interaction.py"), "--world", str(world), "--packet", "IP-SMOKE", "--result", str(summary_only_result), "--dry-run"])
        if "no concrete settlement plan" not in (failed_summary_only_settlement.stdout + failed_summary_only_settlement.stderr):
            raise SystemExit("settle_interaction.py did not reject prose-only settlement result before writes")
        layered_result_validation = json.loads(run([str(SCRIPTS / "validate_settlement_result.py"), "--result", str(result), "--kind", "interaction", "--json"]).stdout)
        if layered_result_validation.get("layers", {}).get("settlement_plan", {}).get("source") != "legacy-result-fields":
            raise SystemExit("validate_settlement_result.py did not infer settlement plan from legacy concrete fields")
        failed_settle_packet_id = run_expect_fail([str(SCRIPTS / "settle_interaction.py"), "--world", str(world), "--packet", "BAD/X", "--result", str(result), "--dry-run"])
        if "packet must contain" not in (failed_settle_packet_id.stderr + failed_settle_packet_id.stdout):
            raise SystemExit("settle_interaction.py did not reject unsafe packet id")
        run([str(SCRIPTS / "settle_interaction.py"), "--world", str(world), "--packet", "IP-SMOKE", "--result", str(result), "--confirmed"])
        interaction_event = sorted((world / "story" / "main" / "events").glob("EVT-0002*.md"))[-1]
        interaction_event.write_text(
            interaction_event.read_text(encoding="utf-8").rstrip()
            + "\n- location: LOC-002\n- actors: [CHAR-0001]\n- cause_refs: [EVT-0001]\n- effect_refs: []\n- effect_notes: [REL-MIRA-MARKET]\n- tags: [dialogue, identity]\n",
            encoding="utf-8",
        )
        interaction_event_text = interaction_event.read_text(encoding="utf-8")
        if "## GM summary" not in interaction_event_text or "## Settlement plan" not in interaction_event_text:
            raise SystemExit("settle_interaction.py did not write narrative settlement layers into event file")
        failed_queue = run_expect_fail(
            [
                str(SCRIPTS / "queue_event.py"),
                "--world",
                str(world),
                "--title",
                "Unconfirmed warning",
                "--summary",
                "This queue write must not persist without confirmation.",
                "--in-days",
                "1",
            ]
        )
        if "without --confirmed" not in (failed_queue.stderr + failed_queue.stdout):
            raise SystemExit("queue_event.py did not require --confirmed for writes")
        queued = json.loads(
            run(
                [
                    str(SCRIPTS / "queue_event.py"),
                    "--world",
                    str(world),
                    "--title",
                    "洪水警报",
                    "--summary",
                    "上游洪峰将在五天后抵达。",
                    "--kind",
                    "disaster-warning",
                    "--priority",
                    "high",
                    "--in-days",
                    "5",
                    "--target",
                    "LOC-001",
                    "--confirmed",
                ]
            ).stdout
        )
        if queued.get("status") != "queued" or not queued.get("pause"):
            raise SystemExit("queued event was not pause-ready")
        timeline_with_queue = json.loads(run([str(SCRIPTS / "build_timeline.py"), "--world", str(world), "--dry-run"]).stdout)
        if not any(node.get("state") == "queued" and node.get("queue_id") == queued["queue_id"] for node in timeline_with_queue.get("nodes", [])):
            raise SystemExit("build_timeline.py did not include queued future node")
        event_priority_plan = json.loads(
            run([str(SCRIPTS / "advance_world.py"), "--world", str(world), "--days", "30", "--until-next-queue", "--dry-run"]).stdout
        )
        if event_priority_plan.get("requested_days") != 5 or event_priority_plan.get("advance_profile", {}).get("resolved_next_queue_id") != queued["queue_id"]:
            raise SystemExit("advance_world.py --until-next-queue did not resolve to next queued event")
        run([str(SCRIPTS / "advance_world.py"), "--world", str(world), "--days", "30", "--summary", "世界自然运行，直到必须停下。", "--confirmed"])
        save_after_advance = (world / "story" / "main" / "SAVE.md").read_text(encoding="utf-8")
        if "- world_time: year 1, day 6" not in save_after_advance:
            raise SystemExit("advance_world.py did not stop on queued pause time")
        latest_run_dirs = sorted((world / "story" / "main" / "runtime" / "advance-runs").glob("ADV-*"), key=lambda path: path.name)
        if not latest_run_dirs or not (latest_run_dirs[-1] / "pause.md").exists():
            raise SystemExit("advance_world.py did not write pause.md")
        queue_text = (world / "story" / "main" / "queues" / "events.jsonl").read_text(encoding="utf-8")
        if '"status": "due"' not in queue_text:
            raise SystemExit("queued event was not marked due")
        queued_result = root / "queued-settlement.json"
        queued_result.write_text(
            json.dumps(
                {
                    "summary": "米拉敲响铜钟，河湾集市提前撤离，洪水只冲毁了外圈木栈道。",
                    "event": {"title": "洪水警报被兑现", "type": "disaster-warning"},
                    "chronicle": "洪水抵达前，河湾集市因警报撤离，损失被限制在外圈木栈道。",
                    "consequences": "LOC-001 的短期交通受损；米拉声望上升。",
                    "state_appends": [{"path": "story/main/state/entities/CHAR-0001-mira.md", "text": "- reputation: 洪水预警者"}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        failed_queued_summary_only = run_expect_fail([str(SCRIPTS / "settle_queued_event.py"), "--world", str(world), "--queue-id", queued["queue_id"], "--result", str(summary_only_result), "--dry-run", "--allow-not-due"])
        if "no concrete settlement plan" not in (failed_queued_summary_only.stdout + failed_queued_summary_only.stderr):
            raise SystemExit("settle_queued_event.py did not reject prose-only settlement result before writes")
        run([str(SCRIPTS / "settle_queued_event.py"), "--world", str(world), "--queue-id", queued["queue_id"], "--result", str(queued_result), "--confirmed"])
        queued_event = sorted((world / "story" / "main" / "events").glob("EVT-0003*.md"))[-1]
        queued_event.write_text(
            queued_event.read_text(encoding="utf-8").rstrip()
            + "\n- location: LOC-001\n- actors: [CHAR-0001]\n- cause_refs: [EVT-0002]\n- effect_refs: []\n- effect_notes: [QUEUE-SETTLED]\n- tags: [disaster, warning]\n",
            encoding="utf-8",
        )
        queued_event_text = queued_event.read_text(encoding="utf-8")
        if "## GM summary" not in queued_event_text or "## Settlement plan" not in queued_event_text:
            raise SystemExit("settle_queued_event.py did not write narrative settlement layers into event file")
        queue_text_after_settle = (world / "story" / "main" / "queues" / "events.jsonl").read_text(encoding="utf-8")
        if '"status": "settled"' not in queue_text_after_settle:
            raise SystemExit("queued event was not marked settled")
        save_after_queue_settlement = (world / "story" / "main" / "SAVE.md").read_text(encoding="utf-8")
        if "- active_pauses: []" not in save_after_queue_settlement:
            raise SystemExit("queued event settlement did not clear active pauses")
        dashboard_after_queue_settlement = json.loads((world / "dashboard" / "data.json").read_text(encoding="utf-8"))
        if any(item.get("queue_id") == queued["queue_id"] for item in dashboard_after_queue_settlement.get("unresolved_choices", [])):
            raise SystemExit("queued event settlement did not remove unresolved dashboard choice")
        advance_profile_report = json.loads(
            run(
                [
                    str(SCRIPTS / "set_advance_profile.py"),
                    "--world",
                    str(world),
                    "--preset-id",
                    "fast-watch",
                    "--mode",
                    "hybrid",
                    "--days",
                    "2",
                    "--summary",
                    "Preset smoke advance.",
                    "--wander",
                    "--wander-limit",
                    "1",
                    "--make-default",
                    "--confirmed",
                    "--json",
                ]
            ).stdout
        )
        if advance_profile_report.get("profile", {}).get("default_preset") != "fast-watch":
            raise SystemExit("set_advance_profile.py did not set default preset")
        player_after_advance_profile = (world / "PLAYER.md").read_text(encoding="utf-8")
        if "- advance_default_preset: fast-watch" not in player_after_advance_profile or "- advance_default_days: 2" not in player_after_advance_profile:
            raise SystemExit("set_advance_profile.py did not mirror advance profile summary into PLAYER.md")
        if player_after_advance_profile.count("- advance_default_preset:") != 1:
            raise SystemExit("set_advance_profile.py left stale advance profile summaries in PLAYER.md")
        player_path = world / "PLAYER.md"
        valid_player_text = player_path.read_text(encoding="utf-8")
        player_path.write_text(valid_player_text.replace("- advance_default_preset: fast-watch", "- advance_default_preset: stale"), encoding="utf-8")
        stale_player_validation = run_expect_fail([str(SCRIPTS / "validate_world.py"), "--world", str(world), "--json"])
        if "advance_default_preset summary does not match" not in (stale_player_validation.stdout + stale_player_validation.stderr):
            raise SystemExit("validate_world.py did not reject stale PLAYER.md advance summary")
        player_path.write_text(valid_player_text, encoding="utf-8")
        run([str(SCRIPTS / "advance_world.py"), "--world", str(world), "--preset", "fast-watch", "--confirmed"])
        latest_preset_runs = sorted((world / "story" / "main" / "runtime" / "advance-runs").glob("ADV-*"), key=lambda path: path.name)
        preset_run = json.loads((latest_preset_runs[-1] / "run.json").read_text(encoding="utf-8"))
        if preset_run.get("advance_profile", {}).get("preset_id") != "fast-watch" or preset_run.get("requested_days") != 2:
            raise SystemExit("advance_world.py did not apply selected advance preset")
        if not preset_run.get("wandering", {}).get("report", {}).get("moves"):
            raise SystemExit("advance_world.py preset did not record wandering report")
        run([str(SCRIPTS / "advance_world.py"), "--world", str(world), "--days", "1", "--summary", "河湾集市恢复通行，世界继续自然流动。", "--wander", "--wander-limit", "1", "--confirmed"])
        latest_wander_runs = sorted((world / "story" / "main" / "runtime" / "advance-runs").glob("ADV-*"), key=lambda path: path.name)
        wander_run = json.loads((latest_wander_runs[-1] / "run.json").read_text(encoding="utf-8"))
        if not wander_run.get("wandering", {}).get("report", {}).get("moves"):
            raise SystemExit("advance_world.py --wander did not record wandering report")
        dashboard_after_advance_wander = json.loads((world / "dashboard" / "data.json").read_text(encoding="utf-8"))
        if dashboard_after_advance_wander.get("time") != wander_run.get("to"):
            raise SystemExit("advance_world.py --wander did not preserve dashboard time")
        random_log_after_advance_wander = (world / "story" / "main" / "random" / "random-log.jsonl").read_text(encoding="utf-8")
        if f'"purpose": "advance:{wander_run["run_id"]}"' not in random_log_after_advance_wander:
            raise SystemExit("advance_world.py --wander did not append advance-scoped random log")
        event_count_before_soften = len(list((world / "story" / "main" / "events").glob("EVT-*.md")))
        failed_soften_request_id = run_expect_fail(
            [
                str(SCRIPTS / "set_content_profile.py"),
                "--world",
                str(world),
                "--preset",
                "gentle",
                "--soften-target",
                queued["queue_id"],
                "--soften-request-id",
                "../BAD",
                "--confirmed",
            ]
        )
        if "soften-request-id must contain" not in (failed_soften_request_id.stderr + failed_soften_request_id.stdout):
            raise SystemExit("set_content_profile.py did not reject unsafe soften request id")
        content_report = json.loads(
            run(
                [
                    str(SCRIPTS / "set_content_profile.py"),
                    "--world",
                    str(world),
                    "--preset",
                    "gentle",
                    "--topic",
                    "war=summary",
                    "--add-ban",
                    "不描写虐待细节",
                    "--soften-target",
                    queued["queue_id"],
                    "--soften-request-id",
                    "SOFT-SMOKE",
                    "--confirmed",
                    "--json",
                ]
            ).stdout
        )
        profile = json.loads((world / "setup" / "content-profile.json").read_text(encoding="utf-8"))
        if profile.get("preset") != "gentle" or profile.get("topics", {}).get("war") != "summary":
            raise SystemExit("content profile did not apply preset/topic")
        if "不描写虐待细节" not in profile.get("player_absolute_bans", []):
            raise SystemExit("content profile did not record absolute ban")
        updated_player_text = (world / "PLAYER.md").read_text(encoding="utf-8")
        if "- content_preset: gentle" not in updated_player_text or "不描写虐待细节" not in updated_player_text:
            raise SystemExit("set_content_profile.py did not mirror compact content boundary into PLAYER.md")
        if updated_player_text.count("- content_preset:") != 1:
            raise SystemExit("set_content_profile.py left stale content profile summaries in PLAYER.md")
        player_path.write_text(updated_player_text.replace("不描写虐待细节", "摘要缺失"), encoding="utf-8")
        stale_content_validation = run_expect_fail([str(SCRIPTS / "validate_world.py"), "--world", str(world), "--json"])
        if "content_absolute_bans summary missing ban" not in (stale_content_validation.stdout + stale_content_validation.stderr):
            raise SystemExit("validate_world.py did not reject stale PLAYER.md content summary")
        player_path.write_text(updated_player_text, encoding="utf-8")
        if not content_report.get("soften_request") or not Path(content_report["soften_request"]).exists():
            raise SystemExit("soften request was not created")
        soften_payload = json.loads(Path(content_report["soften_request"]).read_text(encoding="utf-8"))
        if "Do not change canon facts" not in soften_payload.get("instruction", ""):
            raise SystemExit("soften request did not preserve canon instruction")
        if len(list((world / "story" / "main" / "events").glob("EVT-*.md"))) != event_count_before_soften:
            raise SystemExit("content profile update changed event count")

        for script in ["update_chronicle.py", "render_chronicle_style.py", "build_timeline.py", "export_dashboard.py", "build_indexes.py", "build_map_layers.py", "update_map_state.py"]:
            run([str(SCRIPTS / script), "--world", str(world)])
        locations_index = json.loads((world / "indexes" / "locations.json").read_text(encoding="utf-8"))
        if not any(item.get("id") == "LOC-001" and item.get("source") == "story/main/state/locations/LOC-001-river-market.md" for item in locations_index.get("locations", [])):
            raise SystemExit("locations index did not include LOC-001 source")
        event_graph = json.loads((world / "indexes" / "event-graph.json").read_text(encoding="utf-8"))
        if not any(link.get("source", "").endswith(":EVT-0001") and link.get("target", "").endswith(":EVT-0002") for link in event_graph.get("links", [])):
            raise SystemExit("event graph did not include EVT-0001 -> EVT-0002 cause link")
        if "EVT-0002" not in event_graph.get("by_actor", {}).get("CHAR-0001", []):
            raise SystemExit("event graph did not index CHAR-0001 actor")
        if "EVT-0003" not in event_graph.get("by_tag", {}).get("warning", []):
            raise SystemExit("event graph did not index warning tag")
        map_layers = json.loads((world / "dashboard" / "map-layers.json").read_text(encoding="utf-8"))
        loc_node = next((node for node in map_layers.get("nodes", []) if node.get("id") == "LOC-001"), None)
        if not loc_node or loc_node.get("source") != "story/main/state/locations/LOC-001-river-market.md":
            raise SystemExit("map layers did not include location source pointer")
        if map_layers.get("map_generation", {}).get("status") == "generated":
            if not map_layers.get("brushes"):
                raise SystemExit("generated map did not include mutable terrain brushes")
        elif map_layers.get("map_generation", {}).get("status") != "pending":
            raise SystemExit("map layers did not declare map generation state")
        failed_brush_id = run_expect_fail([str(SCRIPTS / "set_map_brush.py"), "--world", str(world), "--brush-id", "../BAD", "--kind", "river", "--points-json", "[[1,2],[3,4]]", "--dry-run"])
        if "brush-id must contain" not in (failed_brush_id.stderr + failed_brush_id.stdout):
            raise SystemExit("set_map_brush.py did not reject unsafe brush id")
        run(
            [
                str(SCRIPTS / "set_map_brush.py"),
                "--world",
                str(world),
                "--brush-id",
                "BRUSH-RIVER-SMOKE",
                "--kind",
                "tributary",
                "--label",
                "神谕改出的支流",
                "--points-json",
                "[[18,22],[30,31],[42,61]]",
                "--width",
                "4",
                "--density",
                "9",
                "--jitter",
                "2",
                "--confirmed",
            ]
        )
        map_layers_after_brush = json.loads((world / "dashboard" / "map-layers.json").read_text(encoding="utf-8"))
        brush_state_path = world / "story" / "main" / "state" / "terrain-brushes.json"
        if not brush_state_path.exists():
            raise SystemExit("set_map_brush.py did not write active branch terrain brush state")
        smoke_brush = next((brush for brush in map_layers_after_brush.get("brushes", []) if brush.get("id") == "BRUSH-RIVER-SMOKE"), None)
        if not smoke_brush or smoke_brush.get("kind") != "tributary" or smoke_brush.get("points", [])[0] != [18.0, 22.0] or smoke_brush.get("source") != "story/main/state/terrain-brushes.json":
            raise SystemExit("set_map_brush.py did not update dashboard map brush layer")
        run([str(SCRIPTS / "validate_world.py"), "--world", str(world), "--json"])

        run([str(SCRIPTS / "checkpoint.py"), "--world", str(world), "--reason", "smoke"])
        failed_branch_id = run_expect_fail(
            [
                str(SCRIPTS / "draft_branch.py"),
                "--world",
                str(world),
                "--branch-id",
                "!!!",
                "--fork-event",
                "EVT-0001",
                "--change-summary",
                "invalid branch id must fail",
                "--confirmed",
            ]
        )
        if "branch-id must contain" not in (failed_branch_id.stderr + failed_branch_id.stdout):
            raise SystemExit("draft_branch.py did not reject empty normalized branch id")
        failed_draft_id = run_expect_fail(
            [
                str(SCRIPTS / "draft_branch.py"),
                "--world",
                str(world),
                "--branch-id",
                "unsafe-draft",
                "--fork-event",
                "EVT-0001",
                "--change-summary",
                "unsafe draft id must fail",
                "--draft-id",
                "../BAD",
                "--dry-run",
            ]
        )
        if "draft-id must contain" not in (failed_draft_id.stderr + failed_draft_id.stdout):
            raise SystemExit("draft_branch.py did not reject unsafe draft id")
        failed_create_draft_id = run_expect_fail([str(SCRIPTS / "create_branch.py"), "--world", str(world), "--draft-id", "../BAD", "--confirmed"])
        if "draft-id must contain" not in (failed_create_draft_id.stderr + failed_create_draft_id.stdout):
            raise SystemExit("create_branch.py did not reject unsafe draft id")
        branch_draft = json.loads(
            run(
                [
                    str(SCRIPTS / "draft_branch.py"),
                    "--world",
                    str(world),
                    "--branch-id",
                    "save-mira",
                    "--fork-event",
                    "EVT-0001",
                    "--change-summary",
                    "阻止放逐。",
                    "--draft-id",
                    "BRD-SMOKE",
                    "--confirmed",
                    "--json",
                ]
            ).stdout
        )
        if branch_draft.get("draft_json") != "story/main/runtime/branch-drafts/BRD-SMOKE/draft.json":
            raise SystemExit("draft_branch.py did not create expected draft path")
        run([str(SCRIPTS / "create_branch.py"), "--world", str(world), "--draft-id", "BRD-SMOKE", "--confirmed"])
        consumed_draft = json.loads((world / "story" / "main" / "runtime" / "branch-drafts" / "BRD-SMOKE" / "draft.json").read_text(encoding="utf-8"))
        if consumed_draft.get("status") != "consumed" or consumed_draft.get("created_branch_path") != "story/main/branches/save-mira":
            raise SystemExit("create_branch.py did not consume branch draft")
        story_tree_text = (world / "story" / "STORY-TREE.md").read_text(encoding="utf-8")
        if "save-mira" not in story_tree_text or "story/main/branches/save-mira" not in story_tree_text:
            raise SystemExit("STORY-TREE.md did not record child branch")
        parent_entity_card = world / "story" / "main" / "state" / "entities" / "CHAR-0001-mira.md"
        parent_location_card = world / "story" / "main" / "state" / "locations" / "LOC-001-river-market.md"
        child_branch = world / "story" / "main" / "branches" / "save-mira"
        child_entity_card = child_branch / "state" / "entities" / "CHAR-0001-mira.md"
        child_location_card = child_branch / "state" / "locations" / "LOC-001-river-market.md"
        if not child_entity_card.exists() or not child_location_card.exists():
            raise SystemExit("create_branch.py did not copy parent state snapshot into child branch")
        child_brush_state = child_branch / "state" / "terrain-brushes.json"
        if not child_brush_state.exists():
            raise SystemExit("create_branch.py did not copy branch-local terrain brush state into child branch")
        if child_entity_card.read_text(encoding="utf-8") != parent_entity_card.read_text(encoding="utf-8"):
            raise SystemExit("child branch entity snapshot did not match parent at fork")
        if child_location_card.read_text(encoding="utf-8") != parent_location_card.read_text(encoding="utf-8"):
            raise SystemExit("child branch location snapshot did not match parent at fork")
        active_child_validation = json.loads(run([str(SCRIPTS / "validate_world.py"), "--world", str(world), "--json"]).stdout)
        if not active_child_validation.get("ok"):
            raise SystemExit("validate_world.py failed on active child branch")
        child_dashboard = json.loads((world / "dashboard" / "data.json").read_text(encoding="utf-8"))
        if child_dashboard.get("branch_id") != "save-mira":
            raise SystemExit("create_branch.py did not rebuild dashboard for active child branch")
        if not any(piece.get("id") == "CHAR-0001" for piece in child_dashboard.get("pieces", [])):
            raise SystemExit("create_branch.py child dashboard did not inherit parent map pieces")
        child_map_layers = json.loads((world / "dashboard" / "map-layers.json").read_text(encoding="utf-8"))
        if not any(brush.get("id") == "BRUSH-RIVER-SMOKE" and brush.get("source") == "story/main/branches/save-mira/state/terrain-brushes.json" for brush in child_map_layers.get("brushes", [])):
            raise SystemExit("create_branch.py child dashboard did not inherit branch-local terrain brushes")
        view = json.loads(run([str(SCRIPTS / "resolve_branch_view.py"), "--world", str(world)]).stdout)
        if len(view.get("chain", [])) < 2:
            raise SystemExit("branch view did not include parent chain")
        run([str(SCRIPTS / "make_interaction_packet.py"), "--world", str(world), "--target-id", "CHAR-0001", "--target-kind", "character", "--intent", "子枝丫观察", "--packet-id", "IP-CHILD-SMOKE"])
        child_result = root / "child-settlement.json"
        child_result.write_text(
            json.dumps(
                {
                    "summary": "子枝丫独立互动。",
                    "event": {"title": "子枝丫独立互动", "type": "observation"},
                    "state_appends": [{"path": "story/main/branches/save-mira/state/entities/CHAR-0001-mira.md", "text": "- branch_only_memory: 子枝丫独立互动。"}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        parent_event_count_before_child_settle = len(list((world / "story" / "main" / "events").glob("EVT-*.md")))
        run([str(SCRIPTS / "settle_interaction.py"), "--world", str(world), "--packet", "IP-CHILD-SMOKE", "--result", str(child_result), "--confirmed"])
        child_events = list((world / "story" / "main" / "branches" / "save-mira" / "events").glob("EVT-0002*.md"))
        if not child_events or not any("子枝丫独立互动" in path.read_text(encoding="utf-8") for path in child_events):
            raise SystemExit("settle_interaction.py did not resolve packet id inside active child branch")
        if len(list((world / "story" / "main" / "events").glob("EVT-*.md"))) != parent_event_count_before_child_settle:
            raise SystemExit("settle_interaction.py wrote child packet settlement into parent branch")
        if "branch_only_memory" not in child_entity_card.read_text(encoding="utf-8"):
            raise SystemExit("settle_interaction.py did not append child branch state update")
        if "branch_only_memory" in parent_entity_card.read_text(encoding="utf-8"):
            raise SystemExit("child branch state update leaked into parent branch")
        failed_switch = run_expect_fail([str(SCRIPTS / "switch_branch.py"), "--world", str(world), "--branch-path", "story/main"])
        if "without --confirmed" not in (failed_switch.stderr + failed_switch.stdout):
            raise SystemExit("switch_branch.py did not require confirmation for active branch switch")
        run([str(SCRIPTS / "switch_branch.py"), "--world", str(world), "--branch-path", "story/main", "--confirmed"])
        timeline_with_branch = json.loads((world / "dashboard" / "timeline.json").read_text(encoding="utf-8"))
        if not any(node.get("state") == "branch" and node.get("branch_path") == "story/main/branches/save-mira" for node in timeline_with_branch.get("nodes", [])):
            raise SystemExit("build_timeline.py did not include child branch node after switching to parent")

        random_entry = json.loads(run([str(SCRIPTS / "resolve_random.py"), "--world", str(world), "--purpose", "weather", "--kind", "weather"]).stdout)
        if random_entry.get("mode") != "random":
            raise SystemExit("random entry mode mismatch")
        override_entry = json.loads(run([str(SCRIPTS / "resolve_random.py"), "--world", str(world), "--purpose", "weather", "--kind", "weather", "--override", "神降暴雨"]).stdout)
        if override_entry.get("mode") != "override":
            raise SystemExit("weather override mode mismatch")
        dashboard_after_weather = json.loads((world / "dashboard" / "data.json").read_text(encoding="utf-8"))
        if dashboard_after_weather.get("weather") != "神降暴雨":
            raise SystemExit("weather override did not sync to dashboard")
        if dashboard_after_weather.get("random_log", {}).get("latest", {}).get("value") != "神降暴雨":
            raise SystemExit("dashboard did not export latest random log summary")
        run([str(SCRIPTS / "export_dashboard.py"), "--world", str(world)])
        dashboard_after_rebuild = json.loads((world / "dashboard" / "data.json").read_text(encoding="utf-8"))
        if dashboard_after_rebuild.get("weather") != "神降暴雨" or dashboard_after_rebuild.get("latest_random", {}).get("value") != "神降暴雨":
            raise SystemExit("export_dashboard.py did not preserve latest weather random result")
        failed_attention = run_expect_fail([str(SCRIPTS / "set_attention.py"), "--world", str(world), "--target-id", "CHAR-0001", "--state", "ignored"])
        if "without --confirmed" not in (failed_attention.stderr + failed_attention.stdout):
            raise SystemExit("set_attention.py did not require confirmation for writes")
        run([str(SCRIPTS / "set_attention.py"), "--world", str(world), "--target-id", "CHAR-0001", "--state", "ignored", "--confirmed"])
        dashboard_after_attention = json.loads((world / "dashboard" / "data.json").read_text(encoding="utf-8"))
        if dashboard_after_attention.get("weather") != "神降暴雨":
            raise SystemExit("dashboard rebuild after attention change lost weather")
        if dashboard_after_attention.get("attention", {}).get("ignored_count", 0) < 1:
            raise SystemExit("dashboard attention summary did not include ignored character")
        decoy_event = world / "story" / "main" / "events" / "EVT-9998-decoy-mention.md"
        decoy_event.write_text(
            "# Decoy mention\n\n- id: EVT-9998\n- time: Y1-Summer\n- type: rumor\n- target_id: CHAR-9999\n- location: LOC-001\n- actors: [CHAR-9999]\n- causes: []\n- effects: []\n- tags: [rumor]\n\nThe crowd mentions CHAR-0001, but this event is not about that character.\n",
            encoding="utf-8",
        )
        timeline_after_attention = json.loads(run([str(SCRIPTS / "build_timeline.py"), "--world", str(world), "--dry-run"]).stdout)
        ignored_node = next((node for node in timeline_after_attention.get("nodes", []) if node.get("state") == "ignored" and node.get("target_id") == "CHAR-0001"), None)
        if not ignored_node:
            raise SystemExit("build_timeline.py did not include ignored digest node")
        if ignored_node.get("source") == "story/main/events/EVT-9998-decoy-mention.md":
            raise SystemExit("build_timeline.py included a body-text decoy event in ignored digest node")
        digest = json.loads(run([str(SCRIPTS / "build_ignored_digest.py"), "--world", str(world), "--target-id", "CHAR-0001"]).stdout)
        if not digest.get("attention_state_unchanged"):
            raise SystemExit("ignored digest changed attention state")
        if any(event.get("event_id") == "EVT-9998" for event in digest.get("events", [])):
            raise SystemExit("build_ignored_digest.py included a body-text decoy event")
        decoy_event.unlink()
        run([str(SCRIPTS / "build_ignored_digest.py"), "--world", str(world), "--target-id", "CHAR-0001", "--output", "story/main/runtime/ignored-digests/CHAR-0001.json"])
        ignored_digest_output = world / "story" / "main" / "runtime" / "ignored-digests" / "CHAR-0001.json"
        if not ignored_digest_output.exists():
            raise SystemExit("build_ignored_digest.py did not write requested world-local output")
        manifest_after_digest = json.loads((world / "system" / "file-manifest.json").read_text(encoding="utf-8"))
        if "story/main/runtime/ignored-digests/CHAR-0001.json" not in {item.get("path") for item in manifest_after_digest.get("files", [])}:
            raise SystemExit("build_ignored_digest.py did not refresh manifest for digest output")
        outside_digest = root / "outside-digest.json"
        failed_outside_digest = run_expect_fail([str(SCRIPTS / "build_ignored_digest.py"), "--world", str(world), "--target-id", "CHAR-0001", "--output", str(outside_digest)])
        if "output must stay inside the world directory" not in (failed_outside_digest.stderr + failed_outside_digest.stdout):
            raise SystemExit("build_ignored_digest.py outside-output failure reason changed")
        failed_overwrite_digest = run_expect_fail([str(SCRIPTS / "build_ignored_digest.py"), "--world", str(world), "--target-id", "CHAR-0001", "--output", "story/main/runtime/ignored-digests/CHAR-0001.json"])
        if "refusing to overwrite" not in (failed_overwrite_digest.stderr + failed_overwrite_digest.stdout):
            raise SystemExit("build_ignored_digest.py overwrite failure reason changed")

        entity.write_text(entity.read_text(encoding="utf-8") + "- public_identity: 被放逐的河神庙司铎\n", encoding="utf-8")
        failed_detect_report_id = run_expect_fail([str(SCRIPTS / "detect_manual_edits.py"), "--world", str(world), "--report-id", "../BAD"])
        if "report-id must contain" not in (failed_detect_report_id.stderr + failed_detect_report_id.stdout):
            raise SystemExit("detect_manual_edits.py did not reject unsafe report id")
        failed_apply_report_id = run_expect_fail([str(SCRIPTS / "apply_manual_edits.py"), "--world", str(world), "--report-id", "../BAD", "--confirmation", "unsafe", "--confirmed"])
        if "report-id must contain" not in (failed_apply_report_id.stderr + failed_apply_report_id.stdout):
            raise SystemExit("apply_manual_edits.py did not reject unsafe report id")
        run([str(SCRIPTS / "detect_manual_edits.py"), "--world", str(world), "--report-id", "MER-SMOKE"])
        run(
            [
                str(SCRIPTS / "apply_manual_edits.py"),
                "--world",
                str(world),
                "--report-id",
                "MER-SMOKE",
                "--accept",
                "story/main/state/entities/CHAR-0001-mira.md",
                "--confirmation",
                "smoke accept",
                "--confirmed",
            ]
        )

        failed_checkpoint_id = run_expect_fail([str(SCRIPTS / "checkpoint.py"), "--world", str(world), "--checkpoint-id", "../BAD", "--reason", "unsafe", "--dry-run"])
        if "checkpoint-id must contain" not in (failed_checkpoint_id.stderr + failed_checkpoint_id.stdout):
            raise SystemExit("checkpoint.py did not reject unsafe checkpoint id")
        run([str(SCRIPTS / "checkpoint.py"), "--world", str(world), "--checkpoint-id", "CP-RESTORE-BASELINE", "--reason", "restore baseline"])
        canon = world / "CANON.md"
        original_canon = canon.read_text(encoding="utf-8")
        canon.write_text(original_canon + "\n- smoke rejected mutation\n", encoding="utf-8")
        run([str(SCRIPTS / "detect_manual_edits.py"), "--world", str(world), "--report-id", "MER-RESTORE-SMOKE"])
        run(
            [
                str(SCRIPTS / "apply_manual_edits.py"),
                "--world",
                str(world),
                "--report-id",
                "MER-RESTORE-SMOKE",
                "--reject",
                "CANON.md",
                "--confirmation",
                "smoke restore rejected",
                "--restore-rejected",
                "--confirmed",
            ]
        )
        if canon.read_text(encoding="utf-8") != original_canon:
            raise SystemExit("restore-rejected did not restore CANON.md")

        pressure_before = json.loads(run([str(SCRIPTS / "check_context_pressure.py"), "--world", str(world), "--json"]).stdout)
        if pressure_before.get("status") != "suggest-handoff":
            raise SystemExit(f"expected suggest-handoff before first handoff, got {pressure_before.get('status')}")
        failed_handoff_id = run_expect_fail([str(SCRIPTS / "create_handoff.py"), "--world", str(world), "--handoff-id", "../BAD", "--dry-run"])
        if "handoff-id must contain" not in (failed_handoff_id.stderr + failed_handoff_id.stdout):
            raise SystemExit("create_handoff.py did not reject unsafe handoff id")
        handoff_report = json.loads(
            run([str(SCRIPTS / "create_handoff.py"), "--world", str(world), "--handoff-id", "HOF-SMOKE", "--confirmed", "--json"]).stdout
        )
        handoff_md = Path(handoff_report["markdown_path"])
        handoff_save_md = Path(handoff_report["save_markdown_path"])
        handoff_json = Path(handoff_report["json_path"])
        if not handoff_md.exists() or not handoff_save_md.exists() or not handoff_json.exists():
            raise SystemExit("handoff files were not created")
        handoff_data = json.loads(handoff_json.read_text(encoding="utf-8"))
        if "ACTIVE.md" not in handoff_data.get("first_read", []):
            raise SystemExit("handoff first_read does not include ACTIVE.md")
        if "米拉承认旧身份" not in handoff_md.read_text(encoding="utf-8"):
            raise SystemExit("handoff did not include recent event context")
        if handoff_save_md.read_text(encoding="utf-8") != handoff_md.read_text(encoding="utf-8"):
            raise SystemExit("handoff 存档.md did not mirror HANDOFF.md")
        failed_resume_id = run_expect_fail([str(SCRIPTS / "resume_world.py"), "--world", str(world), "--resume-id", "../BAD", "--dry-run"])
        if "resume-id must contain" not in (failed_resume_id.stderr + failed_resume_id.stdout):
            raise SystemExit("resume_world.py did not reject unsafe resume id")
        resume_report = json.loads(
            run([str(SCRIPTS / "resume_world.py"), "--world", str(world), "--resume-id", "RES-SMOKE", "--confirmed", "--json"]).stdout
        )
        resume_json = world / "story" / "main" / "runtime" / "resume-packets" / "RES-SMOKE" / "resume.json"
        if not resume_json.exists() or not resume_json.with_name("resume.md").exists():
            raise SystemExit("resume_world.py did not write resume packet files")
        resume_data = json.loads(resume_json.read_text(encoding="utf-8"))
        if "ACTIVE.md" not in resume_report.get("first_read", []) or not resume_data.get("latest_handoff", {}).get("save_markdown"):
            raise SystemExit("resume_world.py did not include startup first_read or latest handoff")
        pressure_after = json.loads(run([str(SCRIPTS / "check_context_pressure.py"), "--world", str(world), "--json"]).stdout)
        if pressure_after.get("status") != "keep-going":
            raise SystemExit(f"expected keep-going after handoff, got {pressure_after.get('status')}")

        install_preview = json.loads(
            run([str(SCRIPTS / "install_local_skill.py"), "--skill-dir", str(SKILL), "--dry-run", "--json"]).stdout
        )
        if not install_preview.get("install_ready", {}).get("ready") or install_preview.get("will_copy"):
            raise SystemExit("install_local_skill.py dry-run did not remain preview-only")

        frontend = SKILL / "assets" / "frontend-template"
        world_brief_template = (SKILL / "assets" / "world-template" / "WORLD-BRIEF.template.md").read_text(encoding="utf-8")
        for marker in ["## Content boundary", "- absolute bans:", "## Player notes", "## Field source map"]:
            if marker not in world_brief_template:
                raise SystemExit(f"WORLD-BRIEF template missing marker {marker}")
        quickstart = (SKILL / "references" / "player-quickstart.md").read_text(encoding="utf-8")
        for marker in ["install_local_skill.py", "serve_frontend.py", "call_llm.py", "external_play_turn.py", "create_demo_world.py", "resume_world.py", "points-json"]:
            if marker not in quickstart:
                raise SystemExit(f"player quickstart missing marker {marker}")
        narrative_templates = SKILL / "assets" / "narrative-templates"
        template_names = [
            "interaction-result.template.json",
            "queued-event-result.template.json",
            "character-seed.template.json",
            "faction-pressure.template.json",
            "divine-intervention-result.template.json",
        ]
        guide = (SKILL / "references" / "narrative-template-guide.md").read_text(encoding="utf-8")
        for name in template_names:
            template_path = narrative_templates / name
            if not template_path.exists():
                raise SystemExit(f"narrative template missing {name}")
            template = json.loads(template_path.read_text(encoding="utf-8"))
            if not template.get("template") or not template.get("use_when") or not str(template.get("schema", "")).startswith("be-a-god."):
                raise SystemExit(f"narrative template missing required metadata {name}")
            if name not in guide:
                raise SystemExit(f"narrative template guide does not route {name}")
        llm_api_template = json.loads((SKILL / "assets" / "world-template" / "llm-api.config.template.json").read_text(encoding="utf-8"))
        for marker in ["base_url", "endpoint_path", "api_key_env", "model"]:
            if marker not in llm_api_template:
                raise SystemExit(f"llm-api config template missing marker {marker}")
        narrative_profile_template = json.loads((SKILL / "assets" / "world-template" / "narrative-profile.template.json").read_text(encoding="utf-8"))
        if narrative_profile_template.get("default_profile") != "hybrid-historical":
            raise SystemExit("narrative profile template missing hybrid-historical default")
        for name in ["index.html", "styles.css", "app.js", "sample-dashboard.json", "sample-timeline.json", "sample-map-layers.json"]:
            if not (frontend / name).exists():
                raise SystemExit(f"frontend template missing {name}")
        sample_dashboard = json.loads((frontend / "sample-dashboard.json").read_text(encoding="utf-8"))
        sample_timeline = json.loads((frontend / "sample-timeline.json").read_text(encoding="utf-8"))
        sample_map_layers = json.loads((frontend / "sample-map-layers.json").read_text(encoding="utf-8"))
        if sample_dashboard.get("schema") != "be-a-god.dashboard.v1":
            raise SystemExit("sample-dashboard.json missing dashboard schema")
        if sample_timeline.get("schema") != "be-a-god.timeline.v1":
            raise SystemExit("sample-timeline.json missing timeline schema")
        if sample_map_layers.get("schema") != "be-a-god.map-layers.v1":
            raise SystemExit("sample-map-layers.json missing map-layers schema")
        if not any(brush.get("mutable_by_divine_action") for brush in sample_map_layers.get("brushes", [])):
            raise SystemExit("sample-map-layers.json missing mutable brush sample")
        frontend_html = (frontend / "index.html").read_text(encoding="utf-8")
        frontend_js = (frontend / "app.js").read_text(encoding="utf-8")
        for marker in ["open-tutorial", "tutorial-dialog", "tutorial-page", "tutorial-grid", "tutorial-mini-map", "creation-dialog", "brief-output", "download-brief", "brief-content-bans", "map-layers-file", "ignore", "follow", "weather-override", "set-rule", "terrain-brush-action", "brush-editor", "brush-editor-command", "brush-editor-width", "brush-editor-density", "brush-editor-jitter", "brush-editor-color", "brush-editor-points-json", "brush-editor-undo", "brush-editor-copy", "branch-action", "world-rules", "random-log", "attention-list", "action-requests", "map-view-tools", "map-zoom-in", "map-zoom-out", "map-zoom-reset", "map-zoom-label", "map-zoom-mode", "zoom-depth", "<details", "<summary>"]:
            if marker not in frontend_html:
                raise SystemExit(f"frontend creation wizard missing marker {marker}")
        for marker in ["open-tutorial", "tutorial-dialog", "actionRequestActionLabel", "actionRequestSummary", "待处理：", "draggedActionRequestId", "draggable = true", "request-cancel", "submitBackendCancelActionRequest", "submitBackendActionRequestOrder", "generateWorldBrief", "Status: draft", "downloadText", "absolute bans", "validateMapLayersData", "sample-map-layers.json", "create_action_request.py", "advance_world.py", "canonical_effect", "emitGlobalAction", "pending_action_requests", "renderActionRequests", "advance_profile", "world_rules", "renderWorldRules", "random_log", "renderRandomLog", "attention", "renderAttention", "set-rule", "--action branch", "--action terrain-brush", "/api/health", "/api/state", "/api/action-request", "/api/advance-world", "/api/action-request/cancel", "/api/action-requests/reorder", "submitBackendActionRequest", "submitBackendAdvanceWorld", "applyBackendState", "promptBranchDraft", "promptTerrainBrushDraft", "brushEditorPayload", "emitBrushEditorCommand", "handleBrushEditorMapClick", "brush-editor-preview", "brush-editor-width", "brush-editor-density", "brush-editor-jitter", "brush-editor-color", "brush-editor-points-json", "copyBrushEditorPoints", "undoBrushEditorPoint", "defaultBrushStyle", "syncBrushEditorOutputs", "commandJsonArg", "escapeHtml(JSON.stringify", "--preset", "preset:", "renderMapDecorations", "renderBrushSvg", "normalizeBrushPoint", "mapLayers.brushes", "terrain-layer", "compass-rose", "scale-bar", "map-legend", "classToken", "MAP_ASSETS", "MAP_ZOOM", "MAP_LEVELS", "mapLevelForScale", "opacityForLevel", "applyZoomFade", "applyZoomFadeToRenderedMap", "currentMapMode", "selectedActionTarget", "setMapZoom", "resetMapView", "handleMapWheel", "beginMapPan", "map-content", "renderBrushAssetStamps", "MAP_DECOR_STAMPS", "renderMapBackdropStamps", "nodeAssetName", "uiFrame", "castle", "village", "bridge", "road", "farm", "ruins", "marsh", "lake", "LOCK-RULE-RIVER-OATH", "Q-QUEUE-0001", "IGNORED-CHAR-0002"]:
            if marker not in frontend_js:
                raise SystemExit(f"frontend creation wizard missing script marker {marker}")
        frontend_css = (frontend / "styles.css").read_text(encoding="utf-8")
        for marker in ["--parchment-texture", "--ink-outline", "--comic-shadow", ".map::before", ".map::after", ".terrain-layer", ".map-content", ".map-view-tools", ".zoom-depth", "corner-ornament.png", ".terrain-stamp", ".terrain-forest", ".terrain-hills", ".terrain-river", ".map-decor-stamp", ".decor-castle", ".decor-village", ".decor-road", ".map-corner-ornament", ".brush-svg", ".brush-river", ".brush-forest", ".brush-hills", ".brush-editor-card", ".brush-editor-card summary", ".requests-card summary", ".request-title", ".request-summary", ".request-id", ".request-row", ".request-cancel", ".dragging", ".drag-over", ".brush-editor-grid", ".brush-editor-preview", ".brush-editor-active", ".tutorial-dialog", ".tutorial-page", ".tutorial-hero", ".tutorial-grid", ".tutorial-card", ".tutorial-mini-map", ".compass-rose", ".scale-bar", ".map-legend", ".piece::before", ".piece::after", ".pin::before", ".map-node::before", ".piece.wandering", ".piece.followed", ".piece.paused", ".piece.dead", ".timeline .queued", ".timeline .due", ".timeline .ignored"]:
            if marker not in frontend_css + frontend_js:
                raise SystemExit(f"frontend theme missing marker {marker}")
        frontend_image_assets = ["flag-marker.png", "forest-stamp.png", "forest-cluster-stamp.png", "hills-stamp.png", "rocky-hills-stamp.png", "mountain-ridge-stamp.png", "creek-stamp.png", "castle-stamp.png", "village-stamp.png", "bridge-stamp.png", "road-stamp.png", "farm-stamp.png", "ruins-stamp.png", "marsh-stamp.png", "lake-stamp.png", "shore-rocks-stamp.png", "parchment-overlay.png", "corner-ornament.png", "ui-frame.png"]
        for name in frontend_image_assets:
            asset_path = frontend / "img" / name
            if not asset_path.exists():
                raise SystemExit(f"frontend image asset missing img/{name}")
            if asset_path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
                raise SystemExit(f"frontend image asset is not PNG img/{name}")
        outside_frontend = root / "outside-frontend"
        failed_outside_frontend = run_expect_fail([str(SCRIPTS / "prepare_frontend.py"), "--world", str(world), "--output", str(outside_frontend), "--dry-run"])
        if "inside world directory" not in (failed_outside_frontend.stderr + failed_outside_frontend.stdout):
            raise SystemExit("prepare_frontend.py allowed outside-world output")
        run([str(SCRIPTS / "prepare_frontend.py"), "--world", str(world), "--confirmed"])
        frontend_app_check = json.loads(run([str(SCRIPTS / "serve_frontend.py"), "--world", str(world), "--check", "--json"]).stdout)
        if (
            "/api/state" not in frontend_app_check.get("endpoints", [])
            or "/api/action-request" not in frontend_app_check.get("endpoints", [])
            or "/api/advance-world" not in frontend_app_check.get("endpoints", [])
            or "/api/action-request/cancel" not in frontend_app_check.get("endpoints", [])
            or "/api/action-requests/reorder" not in frontend_app_check.get("endpoints", [])
        ):
            raise SystemExit("serve_frontend.py check did not expose local app endpoints")
        serve_frontend_text = (SCRIPTS / "serve_frontend.py").read_text(encoding="utf-8")
        for marker in ["charset=utf-8", "state_payload(world, refresh=True)"]:
            if marker not in serve_frontend_text:
                raise SystemExit(f"serve_frontend.py missing frontend runtime marker {marker}")
        prepared_frontend = world / "frontend"
        for name in ["index.html", "styles.css", "app.js", "dashboard.json", "timeline.json", "map-layers.json", "README.md"] + [f"img/{asset}" for asset in frontend_image_assets]:
            if not (prepared_frontend / name).exists():
                raise SystemExit(f"prepared frontend missing {name}")
        json.loads((prepared_frontend / "dashboard.json").read_text(encoding="utf-8"))
        json.loads((prepared_frontend / "timeline.json").read_text(encoding="utf-8"))
        json.loads((prepared_frontend / "map-layers.json").read_text(encoding="utf-8"))
        frontend_readme = (prepared_frontend / "README.md").read_text(encoding="utf-8")
        for marker in ["Open `index.html`", "serve_frontend.py --world <world>", "action request support files", "read-only for canon", "dashboard.json", "timeline.json", "map-layers.json"]:
            if marker not in frontend_readme:
                raise SystemExit(f"prepared frontend README missing marker {marker}")

        demo_report = json.loads(
            run(
                [
                    str(SCRIPTS / "create_demo_world.py"),
                    "--worlds-dir",
                    str(root / "demo-worlds"),
                    "--world-id",
                    "reedbend-demo",
                    "--confirmed",
                    "--json",
                ]
            ).stdout
        )
        demo_world = Path(demo_report["world"])
        if not (demo_world / "ACTIVE.md").exists() or not (demo_world / "frontend" / "index.html").exists():
            raise SystemExit("create_demo_world.py did not create a playable world with frontend")
        demo_dashboard = json.loads((demo_world / "dashboard" / "data.json").read_text(encoding="utf-8"))
        demo_map = json.loads((demo_world / "dashboard" / "map-layers.json").read_text(encoding="utf-8"))
        demo_timeline = json.loads((demo_world / "dashboard" / "timeline.json").read_text(encoding="utf-8"))
        if len(demo_dashboard.get("pieces", [])) < 3:
            raise SystemExit("demo world missing visible character pieces")
        if len(demo_map.get("brushes", [])) < 3:
            raise SystemExit("demo world missing terrain brushes")
        if not any(node.get("state") in {"queued", "due"} or node.get("queue_id") == "QUEUE-DEMO-FLOOD" for node in demo_timeline.get("nodes", [])):
            raise SystemExit("demo world missing queued timeline pressure")
        if not demo_dashboard.get("pending_action_requests"):
            raise SystemExit("demo world missing pending action request")
        duplicate_demo = run_expect_fail([str(SCRIPTS / "create_demo_world.py"), "--worlds-dir", str(root / "demo-worlds"), "--world-id", "reedbend-demo", "--confirmed", "--json"])
        if "already exists" not in (duplicate_demo.stdout + duplicate_demo.stderr):
            raise SystemExit("create_demo_world.py did not refuse an existing demo world")

        final_validation = json.loads(run([str(SCRIPTS / "validate_world.py"), "--world", str(world), "--json"]).stdout)
        if not final_validation.get("ok"):
            raise SystemExit(json.dumps(final_validation, ensure_ascii=False))

        print(json.dumps({"ok": True, "world": str(world), "scripts": "core smoke passed"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
