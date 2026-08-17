#!/usr/bin/env python3
"""Initialize a formal be-a-god world from a confirmed creation draft."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path


SCHEMA = "be-a-god.world.v1"
BRANCH_ID = "main"
DEFAULT_ADVANCE_PROFILE = {
    "schema": "be-a-god.advance-profile.v1",
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
DEFAULT_NARRATIVE_PROFILE = {
    "schema": "be-a-god.narrative-profile.v1",
    "default_profile": "hybrid-historical",
    "profiles": {
        "hybrid-historical": {
            "label": "混合模式，但偏真实历史感",
            "summary": "近景角色有戏，长期文明自然演化；AI 优先因果、制度、资源、人物能动性和可落盘后果，不强行制造爽点。",
            "priority_order": [
                "causality",
                "world_continuity",
                "character_agency",
                "historical_texture",
                "dramatic_presentation",
            ],
            "balance": {
                "default_scale": "mixed-closeup-chronicle",
                "close_scene_weight": 0.45,
                "chronicle_weight": 0.55,
                "stop_for_player_worthy_events": True,
            },
            "principles": [
                "先模拟世界，再包装叙事。",
                "神谕进入因果链，不把后果藏在旁白里。",
                "角色有欲望、误解、资源限制和关系压力，不只是剧情工具。",
                "长期变化通过编年史、指标和事件链呈现；短期交互通过近景场面呈现。",
                "不为了戏剧性无视地理、粮食、合法性、信仰、恐惧、制度惯性和信息传播限制。",
                "玩家只看当前需要看的内容；旧事通过 source pointers 精准回溯。",
            ],
            "output_layers": {
                "required": ["visible_narration", "gm_summary", "settlement_plan"],
                "visible_narration": "玩家直接看到的场景或编年史文本。",
                "gm_summary": "给下一轮使用的紧凑因果摘要。",
                "settlement_plan": "可交给脚本落盘的事件、状态、编年史、队列或地图变更计划。",
            },
            "event_pressure_sources": ["character", "resource", "institution", "environment"],
            "event_chain": [
                "pressure",
                "actor_choice",
                "direct_consequence",
                "second_order_consequence",
                "player_intervention_point",
            ],
            "character_fields": {
                "required": [
                    "desire",
                    "fear",
                    "misunderstanding",
                    "resources",
                    "relationships",
                    "secret",
                    "god_view",
                ]
            },
            "social_indicators": [
                "faith",
                "stability",
                "food_pressure",
                "war_pressure",
                "legitimacy",
                "fear",
                "culture_change",
            ],
            "scale_rules": {
                "closeup": "对话、抉择、冲突和神谕响应；只读目标相关 packet 和必要 source pointers。",
                "regional": "迁徙、饥荒、制度变化、宗教传播、局部战争；用事件链和时间线节点表达。",
                "chronicle": "跨月或跨年变化；少写对白，多写可检验的趋势、代价和后果。",
            },
            "style": {
                "tone": "克制、具体、带历史质感",
                "prefer": [
                    "因果清楚",
                    "物资和制度约束",
                    "人物利益冲突",
                    "神谕后的二阶后果",
                    "可写入事件或状态的结果",
                ],
                "avoid": [
                    "无代价爽点",
                    "模糊史诗腔",
                    "角色突然失去能动性",
                    "只用命运、古老、回响等词替代具体原因",
                    "没有落盘计划的长篇铺陈",
                ],
            },
        }
    },
}
DEFAULT_LLM_API_CONFIG = {
    "schema": "be-a-god.llm-api-config.v1",
    "enabled": False,
    "provider_name": "openai-compatible",
    "protocol": "openai-chat-completions",
    "base_url": "https://api.openai.com/v1",
    "endpoint_path": "/chat/completions",
    "api_key_env": "BE_A_GOD_API_KEY",
    "api_key": "",
    "model": "gpt-4.1-mini",
    "temperature": 0.8,
    "max_tokens": 1200,
    "timeout_seconds": 60,
    "headers": {},
    "system_prompt": "You are a be-a-god narrative engine. Use only the supplied packet/context, keep durable changes as structured JSON plans, and do not invent broad history that was not provided.",
    "response_contract": {
        "format": "text",
        "settlement_hint": "For interaction or queued-event settlement, return concise prose plus a JSON object the host can save as a result file for settle_interaction.py or settle_queued_event.py.",
    },
    "notes": [
        "This file is visible configuration, not canon.",
        "Do not commit real API keys. Prefer setting the environment variable named by api_key_env.",
        "For local models, change base_url, endpoint_path, model, and api_key_env as needed.",
    ],
}
DIRECTORIES = [
    "setup/drafts",
    "story/main/chapters",
    "story/main/events",
    "story/main/state/entities",
    "story/main/state/locations",
    "story/main/chronicle",
    "story/main/queues",
    "story/main/random",
    "story/main/runtime/action-requests",
    "story/main/runtime/interaction-packets",
    "story/main/runtime/advance-runs",
    "story/main/runtime/branch-drafts",
    "story/main/runtime/context-handoffs",
    "story/main/runtime/divine-assessments",
    "story/main/runtime/manual-edit-reports",
    "story/main/runtime/resume-packets",
    "story/main/runtime/rule-checks",
    "story/main/runtime/soften-requests",
    "story/main/checkpoints",
    "story/main/branches",
    "base/entities",
    "base/maps",
    "indexes",
    "dashboard",
    "system",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-").lower()
    if not cleaned:
        raise ValueError("world id cannot be empty after normalization")
    if len(cleaned) > 80:
        cleaned = cleaned[:80].rstrip("-")
    return cleaned


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify(path: Path, world: Path) -> str:
    rel = path.relative_to(world)
    parts = set(rel.parts)
    name = path.name
    if "indexes" in parts or "dashboard" in parts or name in {"validation-report.md"}:
        return "derived"
    if "events" in parts or "chapters" in parts or "state" in parts:
        return "core"
    if "random" in parts or name in {"ACTIVE.md", "CANON.md", "PLAYER.md", "WORLD.md", "SAVE.md"}:
        return "core"
    return "support"


def build_manifest(world: Path) -> dict:
    files = []
    manifest_path = world / "system" / "file-manifest.json"
    for path in sorted(world.rglob("*")):
        if not path.is_file() or path == manifest_path:
            continue
        files.append(
            {
                "path": path.relative_to(world).as_posix(),
                "sha256": sha256_file(path),
                "authority": classify(path, world),
                "bytes": path.stat().st_size,
            }
        )
    return {
        "schema": "be-a-god.file-manifest.v1",
        "world": world.name,
        "generated_at": utc_now(),
        "files": files,
    }


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if text == "":
        path.write_text("", encoding="utf-8")
    else:
        path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_optional(path: Path | None, fallback: str) -> str:
    if path is None:
        return fallback
    return path.read_text(encoding="utf-8")


def brief_is_confirmed(text: str) -> bool:
    return bool(re.search(r"^\s*status\s*:\s*confirmed\s*$", text, re.IGNORECASE | re.MULTILINE))


def brief_value(text: str, field: str, fallback: str = "") -> str:
    match = re.search(rf"^\s*-\s*{re.escape(field)}:\s*(.*?)\s*$", text, re.MULTILINE)
    if not match:
        return fallback
    value = match.group(1).strip()
    return value if value else fallback


def brief_list_after_field(text: str, field: str) -> list[str]:
    pattern = rf"^\s*-\s*{re.escape(field)}:\s*$"
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        value = brief_value(text, field, "")
        return [value] if value else []
    out = []
    started = False
    for line in text[match.end():].splitlines():
        stripped = line.strip()
        if not stripped:
            if not started:
                continue
            break
        if stripped.startswith("## "):
            break
        if stripped.startswith("- "):
            item = stripped[2:].strip()
            if item and item != "（无）":
                out.append(item)
                started = True
            continue
        break
    return out


def brief_source_map(text: str) -> dict[str, str]:
    pattern = re.compile(r"^\s*-\s*([^:\n]+):\s*(player-locked|polishable|player-setting|player-note|ai-fill)\s*$", re.MULTILINE)
    return {field.strip(): source.strip() for field, source in pattern.findall(text)}


def default_advance_profile_summary() -> dict:
    presets = DEFAULT_ADVANCE_PROFILE["presets"]
    return {
        "source": "setup/advance-profile.json",
        "default_preset": DEFAULT_ADVANCE_PROFILE["default_preset"],
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
        ],
    }


def default_narrative_profile_summary() -> dict:
    default_profile = str(DEFAULT_NARRATIVE_PROFILE.get("default_profile") or "")
    profile = DEFAULT_NARRATIVE_PROFILE.get("profiles", {}).get(default_profile, {})
    return {
        "source": "setup/narrative-profile.json",
        "default_profile": default_profile,
        "default_scale": profile.get("balance", {}).get("default_scale"),
        "priority_order": profile.get("priority_order", []),
        "required_output_layers": profile.get("output_layers", {}).get("required", []),
    }


def mkdirs(world: Path) -> list[Path]:
    paths = [world / rel for rel in DIRECTORIES]
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
    return paths


def materialize_creation_map(brief_text: str, starting_region: str) -> dict:
    """Create a deterministic semantic map seed from the confirmed brief."""
    region_name = starting_region if starting_region and starting_region != "未指定起点" else "起始地区"
    region_id = "LOC-START"
    text = brief_text.lower()
    terrain_rules = [
        (("river", "河", "溪"), "river", [[18, 22], [34, 38], [51, 55], [78, 74]], 6, "#315b76"),
        (("forest", "woods", "森林", "林地"), "forest", [[58, 22], [66, 31], [73, 38]], 5, "#557542"),
        (("mountain", "山脉", "高山", "群山"), "hills", [[22, 68], [35, 61], [47, 67]], 6, "#765c38"),
        (("desert", "沙漠", "荒漠"), "desert", [[68, 26], [78, 38], [72, 51]], 7, "#b98c45"),
        (("marsh", "swamp", "沼泽", "湿地"), "marsh", [[24, 68], [31, 76], [42, 71]], 6, "#60734f"),
        (("coast", "island", "sea", "海岸", "大海", "海洋", "海峡", "海域"), "coast", [[10, 16], [9, 43], [12, 76]], 7, "#456f86"),
        (("snow", "tundra", "冰原", "雪原", "冻土"), "snow", [[32, 15], [50, 12], [67, 17]], 7, "#9eb5bd"),
        (("volcano", "volcanic", "火山"), "volcanic", [[76, 20], [82, 27]], 6, "#754538"),
    ]
    brushes = []
    for keywords, kind, points, width, color in terrain_rules:
        if not any(keyword in text for keyword in keywords):
            continue
        brushes.append({
            "id": f"BRUSH-CREATION-{kind.upper()}",
            "kind": kind,
            "label": f"创世地形：{kind}",
            "level": "region",
            "points": points,
            "width": width,
            "density": 16,
            "jitter": 2,
            "color": color,
            "mutable_by_divine_action": True,
        })
    terrain_zones = []
    plain_mentions = len(re.findall(r"plain|平原", text))
    has_sea = any(keyword in text for keyword in ("sea", "大海", "海洋", "海峡", "海域"))
    has_marsh = any(keyword in text for keyword in ("marsh", "swamp", "沼泽", "湿地"))
    if plain_mentions >= 2 and has_sea:
        terrain_zones = [
            {"id": "ZONE-WEST-PLAIN", "name": "西侧平原", "terrain": "plain", "bounds": [0, 0, 30, 100]},
            {"id": "ZONE-CENTRAL-SEA", "name": "中央大海", "terrain": "coast", "bounds": [30, 0, 68, 100]},
            {"id": "ZONE-EAST-PLAIN", "name": "东侧平原", "terrain": "plain", "bounds": [68, 0, 100, 100]},
        ]
        if has_marsh:
            terrain_zones.insert(2, {"id": "ZONE-DANGER-MARSH", "name": "危险沼泽", "terrain": "marsh", "bounds": [52, 56, 68, 100], "danger": True})
    map_generation = {
        "status": "generated" if brushes else "pending",
        "source": "setup/WORLD-BRIEF.md",
        "method": "confirmed-brief-keyword-seed",
    }
    return {
        "hierarchy": {
            "schema": "be-a-god.map-hierarchy.v1",
            "levels": ["world", "region", "scene"],
            "nodes": [{"id": region_id, "name": region_name, "kind": "region", "level": "region"}],
            "terrain_zones": terrain_zones,
            "map_generation": map_generation,
        },
        "coordinates": {
            "schema": "be-a-god.coordinates.v1",
            "coordinate_system": "normalized-0-100",
            "cell_size_meters": 5000,
            "places": [{"id": region_id, "name": region_name, "kind": "region", "level": "region", "x": 50, "y": 50}],
        },
        "brushes": brushes,
        "map_generation": map_generation,
    }


def initial_files(
    world: Path,
    world_id: str,
    title: str,
    brief_text: str,
    content_profile: dict,
    seed: str,
    created_at: str,
) -> dict[Path, str | dict]:
    story_main = world / "story" / "main"
    premise = brief_value(brief_text, "World premise", title)
    starting_era = brief_value(brief_text, "Starting era", "未指定时代")
    starting_region = brief_value(brief_text, "Starting region", "未指定起点")
    god_role = brief_value(brief_text, "God role", "未命名神明")
    tone = brief_value(brief_text, "Tone", "")
    absolute_prohibitions = brief_list_after_field(brief_text, "Absolute prohibitions")
    absolute_prohibitions_text = "；".join(absolute_prohibitions)
    source_map = brief_source_map(brief_text)
    content_bans = brief_list_after_field(brief_text, "absolute bans")
    content_preset = str(content_profile.get("preset") or "standard")
    player_absolute_bans = content_bans or content_profile.get("player_absolute_bans", [])
    player_absolute_bans_text = "; ".join(str(item) for item in player_absolute_bans if str(item).strip()) or "none"
    advance_default_preset = str(DEFAULT_ADVANCE_PROFILE.get("default_preset") or "hybrid")
    advance_default = DEFAULT_ADVANCE_PROFILE.get("presets", {}).get(advance_default_preset, {})
    narrative_default_profile = str(DEFAULT_NARRATIVE_PROFILE.get("default_profile") or "hybrid-historical")
    narrative_profile = DEFAULT_NARRATIVE_PROFILE.get("profiles", {}).get(narrative_default_profile, {})
    narrative_priority = " > ".join(str(item) for item in narrative_profile.get("priority_order", []))
    narrative_layers = ", ".join(str(item) for item in narrative_profile.get("output_layers", {}).get("required", []))
    content_profile_summary = (
        "## Content profile summary\n\n"
        f"- content_profile: setup/content-profile.json\n"
        f"- content_preset: {content_preset}\n"
        f"- content_absolute_bans: {player_absolute_bans_text}\n"
        f"- content_absolute_bans_count: {len(player_absolute_bans)}\n"
    )
    advance_profile_summary = (
        "## Advance profile summary\n\n"
        f"- advance_profile: setup/advance-profile.json\n"
        f"- advance_default_preset: {advance_default_preset}\n"
        f"- advance_default_mode: {advance_default.get('mode', '')}\n"
        f"- advance_default_days: {advance_default.get('days', '')}\n"
        f"- advance_default_wander: {advance_default.get('wander', '')}\n"
        f"- advance_default_stop_on_queue: {advance_default.get('stop_on_queue', '')}\n"
    )
    narrative_profile_summary = (
        "## Narrative profile summary\n\n"
        f"- narrative_profile: setup/narrative-profile.json\n"
        f"- narrative_default_profile: {narrative_default_profile}\n"
        f"- narrative_default_scale: {narrative_profile.get('balance', {}).get('default_scale', '')}\n"
        f"- narrative_priority: {narrative_priority}\n"
        f"- narrative_required_output_layers: {narrative_layers}\n"
    )
    world_summary_lines = [
        f"World ID: `{world_id}`",
        "",
        "Status: confirmed",
        "",
        f"- premise: {premise}",
        f"- starting_era: {starting_era}",
        f"- starting_region: {starting_region}",
        f"- god_role: {god_role}",
    ]
    if tone:
        world_summary_lines.append(f"- tone: {tone}")
    if absolute_prohibitions:
        world_summary_lines.append(f"- absolute_prohibitions: {absolute_prohibitions_text}")
    creation_map = materialize_creation_map(brief_text, starting_region)
    return {
        world / "setup" / "WORLD-BRIEF.md": brief_text,
        world / "setup" / "drafts" / "world-draft.md": brief_text,
        world / "setup" / "world-spec.json": {
            "schema": SCHEMA,
            "world_id": world_id,
            "title": title,
            "created_at": created_at,
            "status": "confirmed",
            "active_branch": BRANCH_ID,
            "creation_fields": {
                "world_premise": premise,
                "starting_era": starting_era,
                "starting_region": starting_region,
                "god_role": god_role,
                "tone": tone,
                "absolute_prohibitions": absolute_prohibitions,
                "absolute_prohibitions_text": absolute_prohibitions_text,
                "content_profile": content_profile.get("preset"),
                "content_bans": content_bans or content_profile.get("player_absolute_bans", []),
            },
            "creation_field_sources": source_map,
        },
        world / "setup" / "content-profile.json": content_profile,
        world / "setup" / "advance-profile.json": DEFAULT_ADVANCE_PROFILE,
        world / "setup" / "narrative-profile.json": DEFAULT_NARRATIVE_PROFILE,
        world / "setup" / "llm-api.config.json": DEFAULT_LLM_API_CONFIG,
        world / "setup" / "world-rules.json": {
            "schema": "be-a-god.world-rules.v1",
            "rules": [],
        },
        world / "WORLD.md": f"# {title}\n\n" + "\n".join(world_summary_lines) + "\n\nSee `setup/WORLD-BRIEF.md` for the full creation brief and field source map.",
        world / "ACTIVE.md": f"# ACTIVE\n\nworld_id: {world_id}\nbranch_id: {BRANCH_ID}\nbranch_path: story/main\nsave_path: story/main/SAVE.md\n",
        world / "CANON.md": "# CANON\n\nPlayer-confirmed facts and locked boundaries live here.\n\n- Do not overwrite locked facts without explicit player confirmation.\n\n## Structured world rules\n\n- No active structured world rules.",
        world / "PLAYER.md": f"# PLAYER\n\n- god_role: {god_role}\n- power_mode: hybrid\n- timeline_display: vertical\n\n{content_profile_summary}\n{advance_profile_summary}\n{narrative_profile_summary}",
        world / "story" / "STORY-TREE.md": "# STORY TREE\n\n- main\n  - branch_path: `story/main`\n  - parent: none\n  - status: active\n",
        story_main / "SAVE.md": f"# SAVE\n\n## Identity\n\n- world_id: {world_id}\n- branch_id: {BRANCH_ID}\n- parent_branch_id: none\n- parent_save: none\n- fork_event: none\n- inherit_until: world-start\n\n## Current state\n\n- world_time: year 1, day 1\n- focal_place: {starting_region}\n- current_scene: {premise} 已被确认。{god_role} 可以第一次观察、推进时间、点击棋子或干预世界。\n- player_god_role: {god_role}\n\n## Open items\n\n- unresolved_choices: []\n- active_pauses: []\n- watched_entities: []\n- ignored_entities: []\n\n## Source pointers\n\n- latest_event: EVT-0001\n- latest_chronicle_entry: CHR-0001\n- relevant_entities: []\n- relevant_locations: []\n\n## Resume prompt\n\nContinue from this save using the smallest needed context.",
        story_main / "CURRENT.md": "# CURRENT\n\n世界已初始化。等待玩家选择观察地图、推进时间、点击棋子或降下神谕。\n",
        story_main / "events" / "EVT-0001-world-confirmed.md": f"# EVT-0001 world confirmed\n\n- id: EVT-0001\n- type: world-start\n- time: year 1, day 1\n- branch_id: {BRANCH_ID}\n- source: setup/WORLD-BRIEF.md\n- tags: [world-start]\n\n玩家确认了世界草案，正式世界开始存在。\n",
        story_main / "chronicle" / "objective.md": "# Objective Chronicle\n\n- CHR-0001 | year 1, day 1 | 玩家确认世界草案，世界正式开始。\n",
        story_main / "chronicle" / "epic.md": "# Epic Chronicle\n\n世界在神明的确认中醒来。\n",
        story_main / "queues" / "events.jsonl": "",
        story_main / "random" / "seed.json": {
            "schema": "be-a-god.random-seed.v1",
            "world_id": world_id,
            "branch_id": BRANCH_ID,
            "seed": seed,
            "created_at": created_at,
        },
        story_main / "random" / "random-log.jsonl": "",
        world / "base" / "maps" / "hierarchy.json": creation_map["hierarchy"],
        world / "base" / "maps" / "coordinates.json": creation_map["coordinates"],
        world / "base" / "maps" / "terrain-brushes.json": {
            "schema": "be-a-god.terrain-brushes.v1",
            "brushes": creation_map["brushes"],
            "map_generation": creation_map["map_generation"],
            "read_policy": "terrain brush particles for frontend map only; story text not included",
        },
        world / "indexes" / "entities.json": {"schema": "be-a-god.entity-index.v1", "entities": []},
        world / "indexes" / "events.json": {"schema": "be-a-god.event-index.v1", "events": ["EVT-0001"]},
        world / "indexes" / "event-graph.json": {
            "schema": "be-a-god.event-graph.v1",
            "world_id": world_id,
            "branch_id": BRANCH_ID,
            "branch_path": "story/main",
            "nodes": [
                {
                    "id": "EVT-0001",
                    "title": "EVT-0001 world confirmed",
                    "type": "world-start",
                    "time": "year 1, day 1",
                    "branch_id": BRANCH_ID,
                    "location": None,
                    "actors": [],
                    "causes": [],
                    "effects": [],
                    "tags": ["world-start"],
                    "source": "story/main/events/EVT-0001-world-confirmed.md",
                    "source_pointer": "setup/WORLD-BRIEF.md",
                    "queue_id": None,
                }
            ],
            "links": [],
            "by_actor": {},
            "by_location": {},
            "by_tag": {"world-start": ["EVT-0001"]},
            "unresolved_refs": [],
        },
        world / "dashboard" / "data.json": {
            "schema": "be-a-god.dashboard.v1",
            "world_id": world_id,
            "branch_id": BRANCH_ID,
            "time": "year 1, day 1",
            "weather": None,
            "focal_place": starting_region,
            "current_scene": f"{premise} 已被确认。{god_role} 可以第一次观察、推进时间、点击棋子或干预世界。",
            "pieces": [],
            "pins": [{"id": "EVT-0001", "kind": "event", "label": "世界确认", "source": "story/main/events/EVT-0001-world-confirmed.md"}],
            "pending_action_requests": [],
            "advance_profile": default_advance_profile_summary(),
            "narrative_profile": default_narrative_profile_summary(),
            "world_rules": {"source": "setup/world-rules.json", "active": []},
            "latest_random": None,
            "random_log": {"source": "story/main/random/random-log.jsonl", "count": 0, "latest": None, "recent": []},
            "attention": {"followed_count": 0, "ignored_count": 0, "plot_ready_count": 0, "followed": [], "ignored": [], "plot_ready": []},
        },
        world / "dashboard" / "timeline.json": {
            "schema": "be-a-god.timeline.v1",
            "world_id": world_id,
            "branch_id": BRANCH_ID,
            "nodes": [
                {
                    "id": "CHR-0001",
                    "event_id": "EVT-0001",
                    "time": "year 1, day 1",
                    "label": "世界正式开始",
                    "state": "confirmed",
                    "source": "story/main/events/EVT-0001-world-confirmed.md",
                }
            ],
        },
        world / "dashboard" / "map-layers.json": {
            "schema": "be-a-god.map-layers.v1",
            "world_id": world_id,
            "levels": ["world", "region", "scene"],
            "nodes": creation_map["hierarchy"]["nodes"],
            "places": creation_map["coordinates"]["places"],
            "brushes": creation_map["brushes"],
            "map_generation": creation_map["map_generation"],
            "read_policy": "frontend map layers only; story text not included",
        },
        world / "system" / "turn-ledger.jsonl": "",
        world / "system" / "manual-edit-ledger.jsonl": "",
        world / "system" / "validation-report.md": "# Validation Report\n\nInitial structure created. Run `validate_world_structure.py` for checks.\n",
    }


def parse_content_profile(path: Path | None, brief_text: str) -> dict:
    if path is None:
        profile = brief_value(brief_text, "profile", "standard")
        notes = brief_value(brief_text, "notes", "")
        bans = brief_list_after_field(brief_text, "absolute bans")
        return {
            "preset": profile,
            "presentation": {
                "soften_on_request": True,
                "facts_remain_intact_when_softened": True,
                "notes": notes,
            },
            "topics": {},
            "player_absolute_bans": bans,
        }
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a confirmed be-a-god world.")
    parser.add_argument("--worlds-dir", default="worlds", help="Directory that contains world folders.")
    parser.add_argument("--world-id", required=True, help="Stable world id. Letters, numbers, dash and underscore are safest.")
    parser.add_argument("--title", help="Human-readable world title. Defaults to world id.")
    parser.add_argument("--brief", help="Confirmed WORLD-BRIEF.md draft.")
    parser.add_argument("--content-profile", help="Confirmed content-profile.json draft.")
    parser.add_argument("--seed", help="Optional explicit random seed. Defaults to a generated token.")
    parser.add_argument("--confirmed", action="store_true", help="Required for writing formal world files.")
    parser.add_argument("--allow-unconfirmed-brief", action="store_true", help="Allow initializing from a brief without `Status: confirmed`.")
    parser.add_argument("--dry-run", action="store_true", help="Print creation plan without writing files.")
    args = parser.parse_args()

    world_id = slug(args.world_id)
    title = args.title or world_id
    worlds_dir = Path(args.worlds_dir).resolve()
    world = worlds_dir / world_id
    brief_path = Path(args.brief).resolve() if args.brief else None
    profile_path = Path(args.content_profile).resolve() if args.content_profile else None
    seed = args.seed or secrets.token_hex(16)
    created_at = utc_now()

    if not args.dry_run and not args.confirmed:
        raise SystemExit("Refusing to write formal world files without --confirmed. Use --dry-run to inspect the plan.")
    if world.exists() and not args.dry_run:
        raise SystemExit(f"Refusing to overwrite existing world directory: {world}")

    brief_text = read_optional(
        brief_path,
        f"# WORLD-BRIEF\n\n## Player-locked facts\n\n- World premise: {title}\n\n## Confirmation\n\nStatus: confirmed\n",
    )
    if not args.allow_unconfirmed_brief and not brief_is_confirmed(brief_text):
        raise SystemExit("Refusing to initialize from an unconfirmed WORLD-BRIEF. Add `Status: confirmed` or pass --allow-unconfirmed-brief.")
    content_profile = parse_content_profile(profile_path, brief_text)
    files = initial_files(world, world_id, title, brief_text, content_profile, seed, created_at)
    dirs = mkdirs(world) if not args.dry_run else [world / rel for rel in DIRECTORIES]

    if args.dry_run:
        print(json.dumps(
            {
                "world": str(world),
                "world_id": world_id,
                "title": title,
                "directories_planned": len(dirs),
                "files_planned": len(files) + 1,
                "requires_confirmed_to_write": True,
            },
            ensure_ascii=False,
            indent=2,
        ))
        return 0

    for path, content in files.items():
        if isinstance(content, dict):
            write_json(path, content)
        else:
            write_text(path, content)

    manifest = build_manifest(world)
    write_json(world / "system" / "file-manifest.json", manifest)

    print(f"Created world: {world}")
    print(f"Active save: {world / 'story' / 'main' / 'SAVE.md'}")
    print(f"Manifest files: {len(manifest['files'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
