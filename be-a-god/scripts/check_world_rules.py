#!/usr/bin/env python3
"""Prepare a compact world-rule conflict check packet."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = "be-a-god.rule-check.v1"
RULES_SCHEMA = "be-a-god.world-rules.v1"
SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
VALID_DECISIONS = {"needs-model-review", "no-conflict", "conflict", "override-requested"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_world(path: str) -> Path:
    world = Path(path).resolve()
    if not world.exists() or not world.is_dir():
        raise SystemExit(f"world directory not found: {world}")
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    return world


def parse_active(world: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in (world / "ACTIVE.md").read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    data.setdefault("branch_id", "main")
    data.setdefault("branch_path", "story/main")
    return data


def relative_inside(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise SystemExit(f"path is outside world directory: {path}") from exc


def validate_id(value: str, field: str) -> str:
    if not SAFE_ID_PATTERN.fullmatch(value):
        raise SystemExit(f"{field} must contain only letters, numbers, underscores, or hyphens: {value}")
    return value


def load_world_rules(world: Path) -> tuple[Path, list[dict[str, Any]]]:
    path = world / "setup" / "world-rules.json"
    if not path.exists():
        return path, []
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != RULES_SCHEMA:
        raise SystemExit(f"world-rules schema must be {RULES_SCHEMA}")
    rules = data.get("rules", [])
    if not isinstance(rules, list):
        raise SystemExit("world-rules rules must be a list")
    active = [rule for rule in rules if isinstance(rule, dict) and rule.get("status") == "active"]
    return path, active


def load_action_request(world: Path, active: dict[str, str], request_id: str | None) -> tuple[dict[str, Any] | None, str | None]:
    if not request_id:
        return None, None
    request_id = validate_id(request_id, "--request-id")
    path = world / active["branch_path"] / "runtime" / "action-requests" / request_id / "request.json"
    if not path.exists():
        raise SystemExit(f"action request not found: {relative_inside(path, world)}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("request_id") != request_id:
        raise SystemExit(f"action request id mismatch: {request_id}")
    return data, relative_inside(path, world)


def tokens(value: str) -> set[str]:
    return {part.lower() for part in re.findall(r"[\w-]{3,}", value or "")}


def compact_rule(rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "rule_id": rule.get("rule_id"),
        "text": rule.get("text"),
        "scope": rule.get("scope"),
        "target": rule.get("target"),
        "effective_time": rule.get("effective_time"),
        "tags": rule.get("tags", []),
    }


def relevance(rule: dict[str, Any], action_text: str, target_id: str, target_kind: str) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    scope = rule.get("scope")
    target = str(rule.get("target") or "")
    if scope == "global":
        reasons.append("global rule")
    if target and target in {target_id, target_kind}:
        reasons.append("target match")
    action_tokens = tokens(action_text)
    for tag in rule.get("tags") or []:
        if str(tag).lower() in action_tokens:
            reasons.append(f"tag match: {tag}")
    if not reasons and scope in {"branch", "custom"}:
        reasons.append("scope may require review")
    return bool(reasons), reasons


def build_check(args: argparse.Namespace) -> tuple[dict[str, Any], Path, Path]:
    world = resolve_world(args.world)
    active = parse_active(world)
    request, request_source = load_action_request(world, active, args.request_id)
    rules_path, active_rules = load_world_rules(world)

    target = request.get("target", {}) if request else {}
    action = args.action or (request or {}).get("action") or "custom"
    target_id = args.target_id or target.get("id") or "WORLD"
    target_kind = args.target_kind or target.get("kind") or "world"
    description = args.description or (request or {}).get("intent") or (request or {}).get("text") or action
    action_text = " ".join([action, target_id or "", target_kind or "", description or ""])

    relevant_rules = []
    background_rules = []
    for rule in active_rules:
        is_relevant, reasons = relevance(rule, action_text, target_id, target_kind)
        item = compact_rule(rule)
        item["relevance"] = reasons
        if is_relevant:
            relevant_rules.append(item)
        else:
            background_rules.append(item)

    decision = args.decision
    if not decision:
        decision = "needs-model-review" if relevant_rules else "no-conflict"

    check_id = validate_id(args.check_id or "RC-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f"), "--check-id")
    branch = world / active["branch_path"]
    check_dir = branch / "runtime" / "rule-checks" / check_id
    check_json = check_dir / "check.json"
    check_md = check_dir / "check.md"
    if (check_json.exists() or check_md.exists()) and not args.dry_run:
        raise SystemExit(f"rule check already exists: {check_id}")

    check = {
        "schema": SCHEMA,
        "check_id": check_id,
        "status": "draft" if args.dry_run else "recorded",
        "created_at": utc_now(),
        "world_id": active.get("world_id") or world.name,
        "branch_id": active.get("branch_id", "main"),
        "branch_path": active.get("branch_path", "story/main"),
        "action_request": {"request_id": args.request_id, "source": request_source},
        "action": {"type": action, "target_id": target_id, "target_kind": target_kind, "description": description},
        "decision": decision,
        "active_rule_count": len(active_rules),
        "relevant_rules": relevant_rules,
        "background_rules_omitted": max(0, len(background_rules) - args.background_limit),
        "background_rules_sample": background_rules[: args.background_limit],
        "source_policy": {
            "required_sources": ["ACTIVE.md", relative_inside(rules_path, world)],
            "optional_sources": [request_source] if request_source else [],
            "instruction": "Use this packet before executing a material action. Do not load broad history unless a relevant rule needs source expansion.",
        },
        "gm_instruction": (
            "If decision is needs-model-review, compare the action against relevant_rules only. "
            "If a rule conflict is plausible, ask the player to override, revise the rule, or branch. "
            "Do not silently reinterpret active player-confirmed rules."
        ),
    }
    return check, check_json, check_md


def render_markdown(check: dict[str, Any]) -> str:
    lines = [
        f"# Rule Check {check['check_id']}",
        "",
        f"- schema: {check['schema']}",
        f"- status: {check['status']}",
        f"- created_at: {check['created_at']}",
        f"- branch_id: {check['branch_id']}",
        f"- action: {check['action']['type']}",
        f"- target_id: {check['action']['target_id']}",
        f"- decision: {check['decision']}",
        "",
        "## Relevant active rules",
        "",
    ]
    if not check["relevant_rules"]:
        lines.append("- None detected by lightweight matching.")
    for rule in check["relevant_rules"]:
        reasons = ", ".join(rule.get("relevance") or ["review"])
        lines.append(f"- {rule.get('rule_id')} [{rule.get('scope')} | {reasons}]: {rule.get('text')}")
    lines.extend(
        [
            "",
            "## Instruction",
            "",
            check["gm_instruction"],
            "",
        ]
    )
    return "\n".join(lines)


def refresh_manifest(world: Path) -> None:
    script = Path(__file__).resolve().parent / "build_file_manifest.py"
    subprocess.run([sys.executable, str(script), str(world)], check=True, stdout=subprocess.DEVNULL)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a compact world-rule conflict check packet.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--request-id")
    parser.add_argument("--action", default="")
    parser.add_argument("--target-id", default="")
    parser.add_argument("--target-kind", default="")
    parser.add_argument("--description", default="")
    parser.add_argument("--decision", choices=sorted(VALID_DECISIONS), default="")
    parser.add_argument("--background-limit", type=int, default=3)
    parser.add_argument("--check-id")
    parser.add_argument("--skip-manifest", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.background_limit < 0:
        raise SystemExit("--background-limit must be >= 0")
    check, check_json, check_md = build_check(args)
    if args.dry_run:
        print(json.dumps(check, ensure_ascii=False, indent=2))
        return 0
    if not args.confirmed:
        raise SystemExit("refusing to write rule check without --confirmed")

    check_json.parent.mkdir(parents=True, exist_ok=True)
    check_json.write_text(json.dumps(check, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    check_md.write_text(render_markdown(check), encoding="utf-8")
    if not args.skip_manifest:
        refresh_manifest(resolve_world(args.world))
    result = {
        "ok": True,
        "check_id": check["check_id"],
        "decision": check["decision"],
        "relevant_rule_count": len(check["relevant_rules"]),
        "check_json": str(check_json),
        "check_markdown": str(check_md),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"Wrote rule check: {check_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
