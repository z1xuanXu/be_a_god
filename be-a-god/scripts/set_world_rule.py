#!/usr/bin/env python3
"""Record player-confirmed world rules and locked facts."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = "be-a-god.world-rules.v1"
VALID_STATUS = {"active", "superseded", "revoked"}
VALID_SCOPE = {"global", "regional", "local", "branch", "character", "custom"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-").upper()
    return cleaned[:48].rstrip("-") or "RULE"


def resolve_world(path: str) -> Path:
    world = Path(path).resolve()
    if not world.exists() or not world.is_dir():
        raise SystemExit(f"world directory not found: {world}")
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    return world


def parse_active(world: Path) -> dict[str, str]:
    data = {}
    for line in (world / "ACTIVE.md").read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    data.setdefault("branch_path", "story/main")
    data.setdefault("branch_id", "main")
    return data


def rules_path(world: Path) -> Path:
    return world / "setup" / "world-rules.json"


def load_rules(world: Path) -> dict[str, Any]:
    path = rules_path(world)
    if not path.exists():
        return {"schema": SCHEMA, "rules": []}
    return json.loads(path.read_text(encoding="utf-8"))


def next_rule_id(rules: dict[str, Any]) -> str:
    highest = 0
    for rule in rules.get("rules", []):
        match = re.search(r"RULE-(\d+)", str(rule.get("rule_id", "")))
        if match:
            highest = max(highest, int(match.group(1)))
    return f"RULE-{highest + 1:04d}"


def validate_rules(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != SCHEMA:
        errors.append(f"world-rules schema must be {SCHEMA}")
    rules = data.get("rules")
    if not isinstance(rules, list):
        errors.append("world-rules rules must be a list")
        return errors
    seen: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict):
            errors.append("world-rules entries must be objects")
            continue
        rule_id = rule.get("rule_id")
        if not rule_id:
            errors.append("world rule missing rule_id")
            continue
        if rule_id in seen:
            errors.append(f"duplicate world rule id: {rule_id}")
        seen.add(rule_id)
        if not rule.get("text"):
            errors.append(f"world rule `{rule_id}` missing text")
        if rule.get("scope") not in VALID_SCOPE:
            errors.append(f"world rule `{rule_id}` has invalid scope `{rule.get('scope')}`")
        if rule.get("status") not in VALID_STATUS:
            errors.append(f"world rule `{rule_id}` has invalid status `{rule.get('status')}`")
        replaces = rule.get("replaces", [])
        if not isinstance(replaces, list):
            errors.append(f"world rule `{rule_id}` replaces must be a list")
        tags = rule.get("tags", [])
        if not isinstance(tags, list):
            errors.append(f"world rule `{rule_id}` tags must be a list")
    return errors


def parse_tags(raw_tags: list[str] | None) -> list[str]:
    tags: list[str] = []
    for raw in raw_tags or []:
        for tag in raw.split(","):
            tag = tag.strip()
            if tag and tag not in tags:
                tags.append(tag)
    return tags


def build_rule(args: argparse.Namespace, world: Path, active: dict[str, str], existing: dict[str, Any]) -> dict[str, Any]:
    rule_id = args.rule_id or next_rule_id(existing)
    rule_id = slug(rule_id)
    return {
        "rule_id": rule_id,
        "text": args.text,
        "scope": args.scope,
        "target": args.target,
        "status": args.status,
        "effective_time": args.effective_time,
        "authority": "player-confirmed",
        "branch_id": active.get("branch_id", "main"),
        "branch_path": active.get("branch_path", "story/main"),
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "replaces": args.replaces or [],
        "tags": parse_tags(args.tag),
        "note": args.note,
    }


def upsert_rule(data: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    data.setdefault("schema", SCHEMA)
    data.setdefault("rules", [])
    replaced = False
    for index, item in enumerate(data["rules"]):
        if item.get("rule_id") == rule["rule_id"]:
            prior = dict(item)
            rule["created_at"] = prior.get("created_at", rule["created_at"])
            data["rules"][index] = rule
            replaced = True
            break
    if not replaced:
        data["rules"].append(rule)
    return data


def update_canon(world: Path, rules: dict[str, Any]) -> None:
    canon_path = world / "CANON.md"
    canon_text = canon_path.read_text(encoding="utf-8") if canon_path.exists() else "# CANON\n"
    active_rules = [rule for rule in rules.get("rules", []) if rule.get("status") == "active"]
    lines = ["## Structured world rules", ""]
    if not active_rules:
        lines.append("- No active structured world rules.")
    for rule in active_rules:
        scope = rule.get("scope", "global")
        target = f" target={rule.get('target')}" if rule.get("target") else ""
        tags = f" tags={','.join(rule.get('tags', []))}" if rule.get("tags") else ""
        lines.append(f"- {rule.get('rule_id')} [{scope}{target}{tags}]: {rule.get('text')}")
    block = "\n".join(lines).rstrip() + "\n"
    marker = "## Structured world rules"
    if marker in canon_text:
        start = canon_text.index(marker)
        next_match = re.search(r"^##\s+", canon_text[start + len(marker) :], re.MULTILINE)
        end = start + len(marker) + next_match.start() if next_match else len(canon_text)
        canon_text = canon_text[:start].rstrip() + "\n\n" + block + canon_text[end:].lstrip()
    else:
        canon_text = canon_text.rstrip() + "\n\n" + block
    canon_path.write_text(canon_text.rstrip() + "\n", encoding="utf-8")


def update_manifest(world: Path) -> None:
    script = Path(__file__).resolve().parent / "build_file_manifest.py"
    subprocess.run([sys.executable, str(script), str(world)], check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def main() -> int:
    parser = argparse.ArgumentParser(description="Set a player-confirmed world rule or locked fact.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--rule-id", help="Stable rule id. Defaults to next RULE-####.")
    parser.add_argument("--text", required=True, help="Rule or locked fact text.")
    parser.add_argument("--scope", choices=sorted(VALID_SCOPE), default="global")
    parser.add_argument("--target", help="Optional target entity, location, faction, region, or branch.")
    parser.add_argument("--status", choices=sorted(VALID_STATUS), default="active")
    parser.add_argument("--effective-time", default="immediate")
    parser.add_argument("--replaces", action="append", help="Rule id this rule replaces. Repeatable.")
    parser.add_argument("--tag", action="append", help="Tag or comma-separated tags.")
    parser.add_argument("--note", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--skip-manifest", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    world = resolve_world(args.world)
    active = parse_active(world)
    existing = load_rules(world)
    rule = build_rule(args, world, active, existing)
    rules = upsert_rule(existing, rule)
    errors = validate_rules(rules)
    if errors:
        raise SystemExit("; ".join(errors))

    report = {"ok": True, "dry_run": args.dry_run, "rules_path": str(rules_path(world)), "rule": rule, "rule_count": len(rules.get("rules", []))}
    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else json.dumps(rule, ensure_ascii=False, indent=2))
        return 0
    if not args.confirmed:
        raise SystemExit("refusing to write world rule without --confirmed")

    path = rules_path(world)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rules, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    update_canon(world, rules)
    if not args.skip_manifest:
        update_manifest(world)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else f"Updated world rule: {rule['rule_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
