#!/usr/bin/env python3
"""Detect file changes against system/file-manifest.json and write a manual-edit report."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def utc_report_id() -> str:
    return datetime.now(timezone.utc).strftime("MER-%Y%m%d%H%M%S")


def validate_id(value: str, field: str) -> str:
    if not SAFE_ID_PATTERN.fullmatch(value):
        raise SystemExit(f"{field} must contain only letters, numbers, underscores, or hyphens: {value}")
    return value


def parse_active(world: Path) -> dict[str, str]:
    data = {}
    for line in (world / "ACTIVE.md").read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    data.setdefault("branch_path", "story/main")
    return data


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify(rel: str, authority: str | None, status: str) -> str:
    if status == "deleted":
        return "high"
    if "random/" in rel or rel in {"ACTIVE.md", "CANON.md", "story/STORY-TREE.md"}:
        return "high"
    if "/events/" in rel or rel.endswith("SAVE.md"):
        return "high"
    if "/state/" in rel or rel.endswith("CURRENT.md") or "/chronicle/objective.md" in rel:
        return "medium"
    if authority == "derived" or rel.startswith("dashboard/") or rel.startswith("indexes/") or rel.endswith("epic.md"):
        return "low"
    return "medium"


def current_hashes(world: Path) -> dict[str, str]:
    out = {}
    for path in sorted(world.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(world).as_posix()
        if should_ignore(rel):
            continue
        out[rel] = sha256_file(path)
    return out


def should_ignore(rel: str) -> bool:
    if rel == "system/file-manifest.json":
        return True
    if rel in {"system/manual-edit-ledger.jsonl", "system/turn-ledger.jsonl", "system/validation-report.md"}:
        return True
    parts = rel.split("/")
    if "runtime" in parts or "checkpoints" in parts:
        return True
    return False


def detect(world: Path) -> list[dict]:
    manifest_path = world / "system" / "file-manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"file-manifest.json not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_files = {item["path"]: item for item in manifest.get("files", [])}
    now = current_hashes(world)
    changes = []
    for rel, item in sorted(manifest_files.items()):
        if should_ignore(rel):
            continue
        if rel not in now:
            status = "deleted"
        elif now[rel] != item.get("sha256"):
            status = "modified"
        else:
            continue
        changes.append({"path": rel, "status": status, "risk": classify(rel, item.get("authority"), status), "authority": item.get("authority")})
    for rel in sorted(set(now) - set(manifest_files)):
        changes.append({"path": rel, "status": "added", "risk": classify(rel, None, "added"), "authority": None})
    return changes


def report_markdown(report_id: str, changes: list[dict]) -> str:
    lines = [f"# Manual Edit Report {report_id}", "", f"- total_changes: {len(changes)}", ""]
    for risk in ["high", "medium", "low"]:
        bucket = [item for item in changes if item["risk"] == risk]
        lines.append(f"## {risk} risk ({len(bucket)})")
        lines.append("")
        for item in bucket:
            lines.append(f"- `{item['path']}` | {item['status']} | authority: {item.get('authority')}")
        lines.append("")
    lines.append("High and medium risk changes require explicit player confirmation before becoming accepted canon.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect manual edits against the last file manifest.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--report-id")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    active = parse_active(world)
    changes = detect(world)
    report_id = validate_id(args.report_id or utc_report_id(), "--report-id")
    merge_plan = {
        "schema": "be-a-god.manual-edit-merge-plan.v1",
        "report_id": report_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "changes": changes,
        "accepted_changes": [],
        "rejected_changes": [],
        "blocked_changes": [item for item in changes if item["risk"] == "high"],
        "note": "Detection only. Applying accepted/rejected changes requires apply_manual_edits.py and a restore policy.",
    }
    report = report_markdown(report_id, changes)
    if args.dry_run:
        print(json.dumps(merge_plan, ensure_ascii=False, indent=2))
        return 0
    out_dir = world / active["branch_path"] / "runtime" / "manual-edit-reports" / report_id
    out_dir.mkdir(parents=True, exist_ok=False)
    (out_dir / "report.md").write_text(report, encoding="utf-8")
    (out_dir / "merge-plan.json").write_text(json.dumps(merge_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote manual edit report: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
