#!/usr/bin/env python3
"""Create a WORLD-BRIEF draft from player-provided fields."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_AI_FILL = [
    "Geography",
    "Weather model",
    "Factions",
    "Initial conflicts",
    "Wandering characters",
]


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff_-]+", "-", value.strip()).strip("-")
    return slug[:64] or "world-brief"


def list_lines(values: list[str]) -> str:
    if not values:
        return "- （未填写）"
    return "\n".join(f"- {value}" for value in values)


def source_map(ai_fill: list[str]) -> str:
    rows = [
        ("World premise", "player-locked"),
        ("Starting era", "player-locked"),
        ("Starting region", "player-locked"),
        ("God role", "player-locked"),
        ("Absolute prohibitions", "player-locked"),
        ("Tone", "polishable"),
        ("Genre references", "polishable"),
        ("Initial cultures", "polishable"),
        ("Content boundary", "player-setting"),
        ("Player notes", "player-note"),
    ]
    rows.extend((field, "ai-fill") for field in ai_fill)
    return "\n".join(f"- {name}: {source}" for name, source in rows)


def render(args: argparse.Namespace) -> str:
    ai_fill = args.ai_fill if args.ai_fill else DEFAULT_AI_FILL
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return f"""# WORLD-BRIEF

## Metadata

- draft_id: {args.draft_id}
- created_at: {created}
- status_note: This is a player-editable draft. Do not initialize a formal world until Status is confirmed.

## Player-locked facts

- World premise: {args.world_premise or ""}
- Starting era: {args.starting_era or ""}
- Starting region: {args.starting_region or ""}
- God role: {args.god_role or ""}
- Absolute prohibitions:
{list_lines(args.absolute_prohibition)}

## Polishable facts

- Tone: {args.tone or ""}
- Genre references:
{list_lines(args.genre_reference)}
- Initial cultures:
{list_lines(args.initial_culture)}

## AI-fill fields

{list_lines(ai_fill)}

## Field source map

{source_map(ai_fill)}

## Content boundary

- profile: {args.content_profile or "standard"}
- notes: {args.content_notes or ""}
- absolute bans:
{list_lines(args.content_ban)}

## Player notes

{args.player_notes or "（无）"}

## Confirmation

Status: draft

Do not create the formal world until the player confirms this brief.
"""


def resolve_output(args: argparse.Namespace) -> Path:
    if args.output:
        return Path(args.output).resolve()
    draft_dir = Path(args.draft_dir).resolve()
    base = slugify(args.world_id or args.world_premise or "world-brief")
    return draft_dir / f"{base}.WORLD-BRIEF.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a be-a-god WORLD-BRIEF draft.")
    parser.add_argument("--world-id", help="Optional future world id, used for the draft filename.")
    parser.add_argument("--draft-id", default="DRAFT-0001")
    parser.add_argument("--draft-dir", default="setup/drafts", help="Draft output directory when --output is omitted.")
    parser.add_argument("--output", help="Exact output path.")
    parser.add_argument("--world-premise", default="")
    parser.add_argument("--starting-era", default="")
    parser.add_argument("--starting-region", default="")
    parser.add_argument("--god-role", default="")
    parser.add_argument("--absolute-prohibition", action="append", default=[])
    parser.add_argument("--tone", default="")
    parser.add_argument("--genre-reference", action="append", default=[])
    parser.add_argument("--initial-culture", action="append", default=[])
    parser.add_argument("--ai-fill", action="append", default=[], help="AI-fill field to include. Repeat for multiple fields.")
    parser.add_argument("--content-profile", default="standard")
    parser.add_argument("--content-notes", default="")
    parser.add_argument("--content-ban", action="append", default=[], help="Player absolute content ban. Repeat for multiple bans.")
    parser.add_argument("--player-notes", default="")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing draft file.")
    parser.add_argument("--dry-run", action="store_true", help="Print draft without writing.")
    parser.add_argument("--json", action="store_true", help="Print JSON report.")
    args = parser.parse_args()

    output = resolve_output(args)
    text = render(args)
    if args.dry_run:
        if args.json:
            print(json.dumps({"ok": True, "dry_run": True, "output": str(output), "draft": text}, ensure_ascii=False, indent=2))
        else:
            print(text)
        return 0

    if output.exists() and not args.overwrite:
        raise SystemExit(f"refusing to overwrite existing draft: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    report = {"ok": True, "output": str(output), "status": "draft"}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Created WORLD-BRIEF draft: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
