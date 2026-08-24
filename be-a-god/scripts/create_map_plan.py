#!/usr/bin/env python3
"""Build a reviewable low-cost semantic map plan from a WORLD-BRIEF."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CARDINAL_ZONES = {
    "north": [0, 0, 100, 25],
    "south": [0, 75, 100, 100],
    "west": [0, 25, 30, 100],
    "east": [70, 25, 100, 100],
    "center": [30, 25, 70, 75],
}

DIRECTION_WORDS = {
    "north": ("north", "northern", "北方", "北部", "北边"),
    "south": ("south", "southern", "南方", "南部", "南边"),
    "west": ("west", "western", "西方", "西部", "西边"),
    "east": ("east", "eastern", "东方", "东部", "东边"),
    "center": ("center", "central", "中央", "中部", "中心"),
}

TERRAIN_WORDS = {
    "snow": ("snow", "tundra", "ice", "雪山", "雪原", "冰原", "冻土", "雪"),
    "mountain": ("mountain", "mountains", "山脉", "群山", "高山"),
    "forest": ("forest", "woods", "森林", "林地"),
    "desert": ("desert", "wasteland", "沙漠", "荒漠", "荒原"),
    "marsh": ("marsh", "swamp", "wetland", "沼泽", "湿地"),
    "coast": ("coast", "sea", "ocean", "海岸", "大海", "海洋", "海峡", "海域"),
    "plain": ("plain", "plains", "grassland", "平原", "草原"),
    "volcanic": ("volcano", "volcanic", "火山"),
}


def contains(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def direction_before_terrain(text: str, terrain_words: tuple[str, ...]) -> str | None:
    for direction, words in DIRECTION_WORDS.items():
        for word in words:
            for terrain in terrain_words:
                pattern = rf"{re.escape(word)}[^。；，,.\\n]{{0,24}}{re.escape(terrain)}"
                if re.search(pattern, text):
                    return direction
    return None


def direction_sequence(text: str, starts: tuple[str, ...], ends: tuple[str, ...]):
    for start in starts:
        for end in ends:
            start_at = text.find(start)
            end_at = text.find(end, start_at + len(start)) if start_at >= 0 else -1
            if start_at >= 0 and end_at >= 0 and end_at - start_at <= 24:
                yield True


def extract_starting_region(brief: str) -> str:
    match = re.search(r"^\s*-\s*Starting region:\s*(.+?)\s*$", brief, re.MULTILINE)
    return match.group(1).strip() if match else "起始地区"


def build_plan(brief_text: str, world_id: str) -> dict:
    text = brief_text.lower()
    zones = []
    unresolved = []
    for terrain, words in TERRAIN_WORDS.items():
        if not contains(text, words):
            continue
        direction = direction_before_terrain(text, words)
        if direction is None:
            unresolved.append({"claim": terrain, "reason": "terrain mentioned without a supported cardinal direction"})
            continue
        zones.append({
            "id": f"ZONE-{direction.upper()}-{terrain.upper()}",
            "name": f"{direction}-{terrain}",
            "terrain": terrain,
            "bounds": CARDINAL_ZONES[direction],
            "source_text": f"{direction} {terrain}",
        })

    features = []
    river_words = ("river", "河流", "大河", "河")
    if contains(text, river_words):
        north_to_south = any(phrase in text for phrase in ("从北向南", "由北向南", "north to south", "north-south")) or any(direction_sequence(text, DIRECTION_WORDS["north"], DIRECTION_WORDS["south"]))
        west_to_east = any(phrase in text for phrase in ("从西向东", "由西向东", "west to east", "west-east")) or any(direction_sequence(text, DIRECTION_WORDS["west"], DIRECTION_WORDS["east"]))
        if north_to_south:
            points = [[50, 0], [48, 32], [52, 68], [50, 100]]
        elif west_to_east:
            points = [[0, 50], [32, 48], [68, 52], [100, 50]]
        else:
            unresolved.append({"claim": "river", "reason": "river mentioned without supported flow direction"})
            points = []
        if points:
            features.append({"id": "FEATURE-RIVER-001", "kind": "river", "points": points, "source_text": "river direction"})

    settlements = []
    starting_region = extract_starting_region(brief_text)
    if starting_region:
        x, y = 50, 50
        if any(word in text for word in ("river east bank", "河流东岸", "河东岸", "河东")):
            x = 65
        elif any(word in text for word in ("river west bank", "河流西岸", "河西岸", "河西")):
            x = 35
        settlements.append({"id": "LOC-START", "name": starting_region, "kind": "region", "x": x, "y": y, "source_text": "Starting region"})

    if not zones and not features:
        unresolved.append({"claim": "map", "reason": "no supported spatial terrain or directional feature could be materialized"})
    return {
        "schema": "be-a-god.map-plan.v1",
        "world_id": world_id,
        "status": "draft",
        "coordinate_system": "normalized-0-100",
        "cell_size_meters": 5000,
        "terrain_zones": zones,
        "linear_features": features,
        "settlements": settlements,
        "unresolved": unresolved,
        "generation": {"method": "deterministic-cardinal-parser", "model_call": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a reviewable MAP-PLAN from a WORLD-BRIEF.")
    parser.add_argument("--brief", required=True)
    parser.add_argument("--world-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    brief = Path(args.brief).read_text(encoding="utf-8")
    output = Path(args.output)
    if output.exists() and not args.overwrite:
        raise SystemExit(f"refusing to overwrite existing map plan: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build_plan(brief, args.world_id), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Created MAP-PLAN: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
