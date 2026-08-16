#!/usr/bin/env python3
"""Apply explicitly accepted manual edits by updating manifest and ledger.

Rejected changes are recorded but not automatically restored. They remain
detectable until the file is manually restored or a future restore policy is
enabled from checkpoints.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


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


def classify(rel: str) -> str:
    if rel.startswith("dashboard/") or rel.startswith("indexes/") or rel.endswith("validation-report.md"):
        return "derived"
    if "/events/" in rel or "/state/" in rel or "/random/" in rel or rel.endswith("SAVE.md"):
        return "core"
    if rel in {"ACTIVE.md", "CANON.md", "PLAYER.md", "WORLD.md", "story/STORY-TREE.md"}:
        return "core"
    return "support"


def relative_inside(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise SystemExit(f"Path is outside world directory: {path}") from exc


def load_report(world: Path, report_id: str) -> tuple[dict, Path]:
    report_id = validate_id(report_id, "--report-id")
    active = parse_active(world)
    report_dir = world / active["branch_path"] / "runtime" / "manual-edit-reports" / report_id
    plan_path = report_dir / "merge-plan.json"
    if not plan_path.exists():
        raise SystemExit(f"merge-plan.json not found: {plan_path}")
    return json.loads(plan_path.read_text(encoding="utf-8")), plan_path


def split_csv(values: list[str]) -> set[str]:
    out = set()
    for value in values:
        for item in value.split(","):
            item = item.strip()
            if item:
                out.add(item)
    return out


def create_checkpoint(world: Path, report_id: str) -> None:
    script = Path(__file__).with_name("checkpoint.py")
    subprocess.run(
        [
            sys.executable,
            str(script),
            "--world",
            str(world),
            "--reason",
            f"before applying manual edits {report_id}",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def update_manifest(world: Path, accepted: set[str], changes_by_path: dict[str, dict]) -> dict:
    manifest_path = world / "system" / "file-manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"file-manifest.json not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = {item["path"]: item for item in manifest.get("files", [])}
    for rel in sorted(accepted):
        change = changes_by_path.get(rel)
        if not change:
            raise SystemExit(f"Accepted path is not in merge plan: {rel}")
        path = world / rel
        if change.get("status") == "deleted":
            files.pop(rel, None)
            continue
        if not path.exists() or not path.is_file():
            raise SystemExit(f"Accepted changed file does not exist: {rel}")
        files[rel] = {
            "path": rel,
            "sha256": sha256_file(path),
            "authority": files.get(rel, {}).get("authority") or classify(rel),
            "bytes": path.stat().st_size,
        }
    manifest["generated_at"] = datetime.now(timezone.utc).isoformat()
    manifest["files"] = [files[key] for key in sorted(files)]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def load_manifest_files(world: Path) -> dict[str, dict]:
    manifest_path = world / "system" / "file-manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"file-manifest.json not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {item["path"]: item for item in manifest.get("files", [])}


def iter_checkpoints(world: Path) -> list[Path]:
    active = parse_active(world)
    checkpoint_root = world / active["branch_path"] / "checkpoints"
    if not checkpoint_root.exists():
        return []
    return sorted((path for path in checkpoint_root.glob("CP-*") if path.is_dir()), key=lambda path: path.name, reverse=True)


def restore_from_snapshot(world: Path, rel: str, expected_sha: str | None) -> str:
    for checkpoint_dir in iter_checkpoints(world):
        meta_path = checkpoint_dir / "checkpoint.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        snapshot_rel = meta.get("core_snapshot", {}).get(rel)
        if not snapshot_rel:
            continue
        snapshot = (checkpoint_dir / snapshot_rel).resolve()
        relative_inside(snapshot, checkpoint_dir)
        if not snapshot.exists() or not snapshot.is_file():
            continue
        if expected_sha and sha256_file(snapshot) != expected_sha:
            continue
        target = (world / rel).resolve()
        relative_inside(target, world)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(snapshot, target)
        return checkpoint_dir.name
    raise SystemExit(f"No checkpoint core snapshot found for rejected path with matching manifest hash: {rel}")


def restore_rejected_changes(world: Path, rejected: set[str], changes_by_path: dict[str, dict]) -> dict[str, str]:
    manifest_files = load_manifest_files(world)
    restored = {}
    for rel in sorted(rejected):
        change = changes_by_path.get(rel)
        if not change:
            raise SystemExit(f"Rejected path is not in merge plan: {rel}")
        target = (world / rel).resolve()
        relative_inside(target, world)
        status = change.get("status")
        if status == "added":
            if target.exists():
                if not target.is_file():
                    raise SystemExit(f"Refusing to remove non-file rejected addition: {rel}")
                target.unlink()
            restored[rel] = "removed added file"
            continue
        expected_sha = manifest_files.get(rel, {}).get("sha256")
        restored[rel] = restore_from_snapshot(world, rel, expected_sha)
    return restored


def append_ledger(world: Path, entry: dict) -> None:
    path = world / "system" / "manual-edit-ledger.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply accepted manual edits to manifest and ledger.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--report-id", required=True)
    parser.add_argument("--accept", action="append", default=[], help="Accepted path, or comma-separated paths. Repeatable.")
    parser.add_argument("--reject", action="append", default=[], help="Rejected path, or comma-separated paths. Repeatable.")
    parser.add_argument("--confirmation", required=True, help="Player confirmation text.")
    parser.add_argument("--allow-high-risk", action="store_true")
    parser.add_argument("--restore-rejected", action="store_true", help="Restore rejected paths from checkpoint core-snapshot when possible.")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    plan, plan_path = load_report(world, args.report_id)
    changes_by_path = {item["path"]: item for item in plan.get("changes", [])}
    accepted = split_csv(args.accept)
    rejected = split_csv(args.reject)
    unknown = (accepted | rejected) - set(changes_by_path)
    if unknown:
        raise SystemExit("Paths not found in merge plan: " + ", ".join(sorted(unknown)))
    high_accepted = [path for path in accepted if changes_by_path[path].get("risk") == "high"]
    if high_accepted and not args.allow_high_risk:
        raise SystemExit("High-risk accepted changes require --allow-high-risk: " + ", ".join(high_accepted))
    blocked = [item["path"] for item in plan.get("blocked_changes", []) if item.get("path") not in accepted and item.get("path") not in rejected]
    result = {
        "schema": "be-a-god.manual-edit-apply.v1",
        "report_id": args.report_id,
        "plan": relative_inside(plan_path, world),
        "accepted_changes": sorted(accepted),
        "rejected_changes": sorted(rejected),
        "remaining_blocked_changes": sorted(blocked),
        "restore_rejected": args.restore_rejected,
        "confirmation": args.confirmation,
        "note": "Rejected changes are restored only when --restore-rejected is set; otherwise they remain detectable.",
    }
    if args.dry_run:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not args.confirmed:
        raise SystemExit("Refusing to apply manual edits without --confirmed. Use --dry-run to inspect the plan.")

    create_checkpoint(world, args.report_id)
    restored_rejected = restore_rejected_changes(world, rejected, changes_by_path) if args.restore_rejected else {}
    update_manifest(world, accepted, changes_by_path)
    ledger = {
        **result,
        "restored_rejected": restored_rejected,
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }
    append_ledger(world, ledger)
    plan["accepted_changes"] = [changes_by_path[path] for path in sorted(accepted)]
    plan["rejected_changes"] = [changes_by_path[path] for path in sorted(rejected)]
    plan["blocked_changes"] = [changes_by_path[path] for path in sorted(blocked)]
    plan["last_apply_result"] = ledger
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(ledger, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
