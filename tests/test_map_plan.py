import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"F:/be_a_god")
SCRIPTS = ROOT / "be-a-god" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from create_map_plan import build_plan


BRIEF = """
# WORLD-BRIEF

## Player-locked facts

- World premise: 北方是雪山，西边有浓密森林，一条河从北向南穿过中央，东部有沙漠城邦，首都位于河流东岸。
- Starting era: 神话时代
- Starting region: 河东首都
- God role: 河流见证者

## Confirmation

Status: confirmed
"""


def zone(plan, terrain):
    return next(item for item in plan["terrain_zones"] if item["terrain"] == terrain)


def test_build_plan_maps_cardinal_terrain_and_settlement_relation():
    plan = build_plan(BRIEF, "river-world")
    assert plan["status"] == "draft"
    assert zone(plan, "snow")["bounds"] == [0, 0, 100, 25]
    assert zone(plan, "forest")["bounds"] == [0, 25, 30, 100]
    assert zone(plan, "desert")["bounds"] == [70, 25, 100, 100]
    river = next(feature for feature in plan["linear_features"] if feature["kind"] == "river")
    assert river["points"][0][1] < river["points"][-1][1]
    capital = next(item for item in plan["settlements"] if item["name"] == "河东首都")
    assert capital["x"] > 50
    assert capital["y"] == 50


def test_build_plan_reports_unresolved_spatial_claims_instead_of_guessing():
    plan = build_plan("神秘高塔在月光照耀的裂谷后方。", "mystery")
    assert plan["status"] == "draft"
    assert plan["unresolved"]
    assert not plan["terrain_zones"]


def test_map_plan_requires_player_confirmation_before_canonicalization(tmp_path):
    brief = tmp_path / "WORLD-BRIEF.md"
    brief.write_text(BRIEF, encoding="utf-8")
    plan_path = tmp_path / "MAP-PLAN.json"
    plan = build_plan(BRIEF, "river-world")
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    command = [sys.executable, str(SCRIPTS / "init_world.py"), "--worlds-dir", str(tmp_path / "worlds"), "--world-id", "river-world", "--brief", str(brief), "--map-plan", str(plan_path), "--confirmed"]
    blocked = subprocess.run(command, capture_output=True, text=True)
    assert blocked.returncode != 0
    assert "unconfirmed MAP-PLAN" in blocked.stderr
    plan["status"] = "confirmed"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    accepted = subprocess.run(command, capture_output=True, text=True)
    assert accepted.returncode == 0
    hierarchy = json.loads((tmp_path / "worlds" / "river-world" / "base/maps/hierarchy.json").read_text(encoding="utf-8"))
    assert hierarchy["terrain_zones"]
    assert hierarchy["map_generation"]["source"] == "setup/MAP-PLAN.json"
