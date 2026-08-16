#!/usr/bin/env python3
"""Create a small playable demo world for be-a-god."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent
SKILL = SCRIPTS.parent


def child_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    return env


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, *args],
        check=False,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=child_env(),
    )
    if completed.returncode != 0:
        raise SystemExit(
            json.dumps(
                {
                    "failed_command": [sys.executable, *args],
                    "returncode": completed.returncode,
                    "stdout": completed.stdout[-3000:] if completed.stdout else "",
                    "stderr": completed.stderr[-3000:] if completed.stderr else "",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    return completed


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def script(name: str) -> str:
    return str(SCRIPTS / name)


def demo_brief() -> str:
    return """# WORLD-BRIEF

## Player-locked facts

- World premise: A river-market civilization survives between flood, oath, hunger, and divine attention.
- Starting era: late bronze age river basin
- Starting region: Reedbend Market
- God role: God of River Oaths

## Polishable facts

- Tone: paper-map myth with grounded historical causality

## AI-fill fields

- Geography: floodplain market, upstream cedar shrine, western hill pasture
- Starting factions: ferry families, grain counters, shrine keepers

## Content boundary

- profile: standard
- notes: keep violence consequential, not graphic
- absolute bans:
  - do not eroticize coercion
  - do not turn famine into spectacle

## Field source map

- World premise: player-locked
- Starting era: player-locked
- Starting region: player-locked
- God role: player-locked
- Tone: polishable
- Geography: ai-fill
- Starting factions: ai-fill
- profile: player-setting
- notes: player-note

## Confirmation

Status: confirmed
"""


def trait_file(root: Path, name: str, data: dict) -> Path:
    path = root / "demo-traits" / f"{name}.json"
    write_json(path, data)
    return path


def make_entity(world: Path, root: Path, *, kind: str, entity_id: str, name: str, summary: str, public_state: str, location: str = "", x: float | None = None, y: float | None = None, level: str = "region", status: str = "ordinary", attention: str = "normal", traits: dict | None = None) -> None:
    args = [
        script("create_entity.py"),
        "--world",
        str(world),
        "--kind",
        kind,
        "--entity-id",
        entity_id,
        "--name",
        name,
        "--summary",
        summary,
        "--public-state",
        public_state,
        "--status",
        status,
        "--attention",
        attention,
        "--level",
        level,
        "--source",
        "demo-world",
        "--confirmed",
    ]
    if location:
        args.extend(["--location", location])
    if x is not None:
        args.extend(["--x", str(x)])
    if y is not None:
        args.extend(["--y", str(y)])
    if traits is not None:
        args.extend(["--traits-json", str(trait_file(root, entity_id, traits))])
    run(args)


def create_demo(args: argparse.Namespace) -> dict:
    worlds_dir = Path(args.worlds_dir).resolve()
    world_id = args.world_id
    world = worlds_dir / world_id
    if world.exists() and not args.overwrite and not args.dry_run:
        raise SystemExit(f"Demo world already exists: {world}. Use --overwrite only when replacing it is intended.")

    plan = {
        "ok": True,
        "status": "dry-run" if args.dry_run else "created",
        "world": str(world),
        "world_id": world_id,
        "features": [
            "confirmed WORLD-BRIEF",
            "3 playable locations",
            "3 visible characters",
            "1 queued plot-ready event",
            "1 pending action request",
            "weather random log",
            "mutable river/forest/hill terrain brushes",
            "prepared frontend files",
        ],
    }
    if args.dry_run:
        return plan
    if not args.confirmed:
        raise SystemExit("Refusing to create demo world without --confirmed. Use --dry-run to preview.")

    if world.exists() and args.overwrite:
        raise SystemExit("Refusing to overwrite an existing demo world automatically. Delete or move the world directory first.")

    scratch = world.parent / f".{world_id}-demo-setup"
    scratch.mkdir(parents=True, exist_ok=True)
    brief = scratch / "WORLD-BRIEF.md"
    write_text(brief, demo_brief())

    run(
        [
            script("init_world.py"),
            "--worlds-dir",
            str(worlds_dir),
            "--world-id",
            world_id,
            "--title",
            "Reedbend Oath Demo",
            "--brief",
            str(brief),
            "--seed",
            args.seed,
            "--confirmed",
        ]
    )

    make_entity(
        world,
        scratch,
        kind="location",
        entity_id="LOC-001",
        name="Reedbend Market",
        summary="A floodplain market where grain, ferry rights, and oath tablets meet.",
        public_state="The stalls are raised on mud-brick platforms. Everyone watches the river level.",
        x=46,
        y=55,
        level="region",
    )
    make_entity(
        world,
        scratch,
        kind="location",
        entity_id="LOC-002",
        name="Cedar Shrine Ford",
        summary="An upstream ford guarded by shrine keepers and ferry families.",
        public_state="Cedar posts lean over the ford. Old oath knots hang from the rail.",
        x=31,
        y=31,
        level="region",
    )
    make_entity(
        world,
        scratch,
        kind="location",
        entity_id="LOC-003",
        name="West Hill Granary",
        summary="A hill granary that can survive the flood if the path stays open.",
        public_state="The granary is dry, watched, and politically dangerous.",
        x=68,
        y=42,
        level="region",
    )

    make_entity(
        world,
        scratch,
        kind="character",
        entity_id="CHAR-0001",
        name="Mira of the Ferry Rope",
        summary="Young ferry heir trying to keep the ford open without angering the shrine.",
        public_state="Mira stands near the market quay with wet rope burns on both palms.",
        location="LOC-001",
        x=44,
        y=57,
        status="plot-ready",
        attention="followed",
        traits={
            "desire": "secure ferry rights before the flood peaks",
            "fear": "the shrine will blame her family for broken oaths",
            "misunderstanding": "believes the grain counters control the missing tablets",
            "resources": ["ferry crew", "river knowledge", "public sympathy"],
            "relationships": {"CHAR-0002": "public rival", "CHAR-0003": "quietly trusts"},
            "secret": "hid one damaged oath tablet to protect a child witness",
            "god_view": "She will bargain honestly if the player asks directly.",
        },
    )
    make_entity(
        world,
        scratch,
        kind="character",
        entity_id="CHAR-0002",
        name="Tavin the Grain Counter",
        summary="A careful clerk whose ledgers can feed the town or expose theft.",
        public_state="Tavin counts jars under a red awning and avoids looking at the river.",
        location="LOC-001",
        x=53,
        y=54,
        status="ordinary",
        traits={
            "desire": "prove the granary losses are not his fault",
            "fear": "a public accusation before the flood audit",
            "misunderstanding": "thinks Mira wants to seize grain transport fees",
            "resources": ["ledger tablets", "two guards", "access to sealed grain rooms"],
            "relationships": {"CHAR-0001": "rival", "CHAR-0003": "ritual superior"},
            "secret": "his assistant falsified one delivery to feed refugees",
            "god_view": "He responds to evidence, not intimidation.",
        },
    )
    make_entity(
        world,
        scratch,
        kind="character",
        entity_id="CHAR-0003",
        name="Old Sela of Cedar Knots",
        summary="Shrine keeper who remembers which oaths were sworn before the last flood.",
        public_state="Sela sits at the cedar ford, tying and untying old oath cords.",
        location="LOC-002",
        x=31,
        y=33,
        status="wandering",
        attention="ignored",
        traits={
            "desire": "keep the river oath system from becoming a market weapon",
            "fear": "the god will answer too loudly and break human institutions",
            "misunderstanding": "underestimates how hungry the hill families are",
            "resources": ["oath memory", "ritual authority", "cedar shrine novices"],
            "relationships": {"CHAR-0001": "protective", "CHAR-0002": "suspicious"},
            "secret": "knows a pre-flood vow that can redirect blame away from the ferry",
            "god_view": "She notices subtle divine signs and will test them.",
        },
    )

    run([script("resolve_random.py"), "--world", str(world), "--purpose", "demo opening weather", "--kind", "weather", "--override", "heavy clouds over a rising river"])
    run([script("queue_event.py"), "--world", str(world), "--queue-id", "QUEUE-DEMO-FLOOD", "--title", "The first flood bell", "--summary", "When the water touches the lower shrine step, the market must choose who controls boats and grain.", "--kind", "flood-warning", "--priority", "high", "--in-days", "2", "--target", "LOC-001", "--target", "CHAR-0001", "--pause", "--confirmed"])
    run([script("set_map_brush.py"), "--world", str(world), "--brush-id", "DEMO-RIVER", "--kind", "river", "--label", "Rising river", "--points-json", "[[18,22],[30,31],[45,53],[58,66],[79,76]]", "--width", "7", "--density", "18", "--jitter", "2", "--color", "#315b76", "--confirmed"])
    run([script("set_map_brush.py"), "--world", str(world), "--brush-id", "DEMO-CEDARS", "--kind", "forest", "--label", "Cedar ford grove", "--points-json", "[[24,25],[29,29],[35,34],[39,38]]", "--width", "6", "--density", "26", "--jitter", "4", "--color", "#557542", "--confirmed"])
    run([script("set_map_brush.py"), "--world", str(world), "--brush-id", "DEMO-HILLS", "--kind", "hills", "--label", "West granary hill", "--points-json", "[[62,38],[68,42],[74,47]]", "--width", "8", "--density", "15", "--jitter", "3", "--color", "#765c38", "--confirmed"])
    action_payload = json.dumps({"topic": "ask Mira why a ferry heir is hiding an oath tablet", "suggested_template": "interaction-result.template.json"}, ensure_ascii=False)
    run([script("create_action_request.py"), "--world", str(world), "--action", "speak", "--target-id", "CHAR-0001", "--target-kind", "character", "--intent", "Ask Mira about the hidden oath tablet.", "--payload-json", action_payload, "--request-id", "AR-DEMO-MIRA", "--confirmed", "--json"])

    current = world / "story" / "main" / "CURRENT.md"
    write_text(
        current,
        """# CURRENT

Heavy clouds press over Reedbend Market. Mira waits near the ferry rope, Tavin counts grain jars, and Old Sela has withdrawn to the cedar ford.

Immediate playable choices:

- Click `CHAR-0001` and ask about the damaged oath tablet.
- Inspect the timeline node `QUEUE-DEMO-FLOOD`.
- Use the brush editor to preview a new tributary before the flood bell.
- Advance 2 days to the first flood bell.
""",
    )
    save_path = world / "story" / "main" / "SAVE.md"
    save = save_path.read_text(encoding="utf-8")
    save = save.replace("relevant_entities: []", "relevant_entities: [CHAR-0001, CHAR-0002, CHAR-0003]")
    save = save.replace("relevant_locations: []", "relevant_locations: [LOC-001, LOC-002, LOC-003]")
    save = save.replace("unresolved_choices: []", "unresolved_choices: [AR-DEMO-MIRA, QUEUE-DEMO-FLOOD]")
    save_path.write_text(save, encoding="utf-8")

    run([script("build_timeline.py"), "--world", str(world)])
    run([script("export_dashboard.py"), "--world", str(world)])
    run([script("build_map_layers.py"), "--world", str(world)])
    run([script("prepare_frontend.py"), "--world", str(world), "--confirmed"])
    run([script("build_file_manifest.py"), str(world)])
    validation = json.loads(run([script("validate_world.py"), "--world", str(world), "--json"]).stdout)
    if not validation.get("ok"):
        raise SystemExit(json.dumps(validation, ensure_ascii=False, indent=2))

    plan["frontend"] = str(world / "frontend" / "index.html")
    plan["first_actions"] = [
        "Open frontend/index.html",
        "Click CHAR-0001",
        "Inspect timeline queue QUEUE-DEMO-FLOOD",
        "Try terrain brush editor on a tributary",
        "Advance to the flood bell",
    ]
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a compact, playable be-a-god demo world.")
    parser.add_argument("--worlds-dir", default="worlds")
    parser.add_argument("--world-id", default="reedbend-demo")
    parser.add_argument("--seed", default="reedbend-demo-seed-v1")
    parser.add_argument("--overwrite", action="store_true", help="Reserved; existing demo worlds are not overwritten automatically.")
    parser.add_argument("--confirmed", action="store_true", help="Required for writing the demo world.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = create_demo(args)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
