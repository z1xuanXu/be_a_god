#!/usr/bin/env python3
"""Settle a due queued event into confirmed branch history."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_settlement_result import validate_result  # noqa: E402


MANIFEST_SCHEMA = "be-a-god.file-manifest.v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: str) -> str:
    cleaned = re.sub(r"[^\w-]+", "-", value.strip(), flags=re.UNICODE).strip("-").lower()
    return cleaned[:48].rstrip("-") or "queued-event"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")


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


def relative_inside(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise SystemExit(f"path is outside world directory: {path}") from exc


def parse_field(text: str, field: str) -> str | None:
    match = re.search(rf"^\s*-\s*{re.escape(field)}:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def replace_or_append_field(markdown: str, field: str, value: str) -> str:
    line = f"- {field}: {value}"
    pattern = re.compile(rf"^\s*-\s*{re.escape(field)}:\s*.*$", re.MULTILINE)
    if pattern.search(markdown):
        return pattern.sub(line, markdown, count=1)
    return markdown.rstrip() + "\n" + line + "\n"


def event_number(path: Path) -> int:
    match = re.match(r"EVT-(\d+)", path.name)
    return int(match.group(1)) if match else 0


def next_event_id(events_dir: Path) -> str:
    existing = [event_number(path) for path in events_dir.glob("EVT-*.md")]
    return f"EVT-{(max(existing) if existing else 0) + 1:04d}"


def next_chronicle_id(chronicle_path: Path) -> str:
    if not chronicle_path.exists():
        return "CHR-0001"
    text = chronicle_path.read_text(encoding="utf-8")
    nums = [int(match.group(1)) for match in re.finditer(r"CHR-(\d+)", text)]
    return f"CHR-{(max(nums) if nums else 0) + 1:04d}"


def load_queue(branch: Path) -> list[dict]:
    queue_path = branch / "queues" / "events.jsonl"
    if not queue_path.exists():
        return []
    entries = []
    for line in queue_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entries.append(json.loads(line))
    return entries


def write_queue(branch: Path, entries: list[dict]) -> None:
    queue_path = branch / "queues" / "events.jsonl"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text("\n".join(json.dumps(entry, ensure_ascii=False) for entry in entries) + "\n", encoding="utf-8")


def find_queue(entries: list[dict], queue_id: str) -> dict:
    for entry in entries:
        if entry.get("queue_id") == queue_id:
            return entry
    raise SystemExit(f"queue_id not found: {queue_id}")


def normalize_result(result: dict) -> dict:
    if "summary" not in result:
        raise SystemExit("queued event settlement result must include `summary`")
    narrative_layers, warnings = validate_result(result, kind="queued-event", allow_legacy=True)
    result["_narrative_layers"] = narrative_layers
    result["_narrative_warnings"] = warnings
    result.setdefault("event", {})
    result["event"].setdefault("type", "queued-event")
    result["event"].setdefault("title", "Queued event settled")
    result.setdefault("state_appends", [])
    result.setdefault("save_updates", {})
    result.setdefault("dashboard", {})
    result.setdefault("current_scene", result["summary"])
    return result


def format_list(values) -> str:
    if values is None:
        return "[]"
    if isinstance(values, str):
        values = [item.strip() for item in values.split(",") if item.strip()]
    if not isinstance(values, list):
        values = [values]
    return "[" + ", ".join(str(item).strip() for item in values if str(item).strip()) + "]"


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
    if "random" in parts or "queues" in parts or name in {"ACTIVE.md", "CANON.md", "PLAYER.md", "WORLD.md", "SAVE.md"}:
        return "core"
    return "support"


def build_manifest(world: Path) -> dict:
    manifest_path = world / "system" / "file-manifest.json"
    files = []
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
        "schema": MANIFEST_SCHEMA,
        "world": world.name,
        "generated_at": utc_now(),
        "files": files,
    }


def settlement_plan(world: Path, branch: Path, branch_path: str, queue: dict, result: dict) -> dict:
    events_dir = branch / "events"
    event_id = result.get("event", {}).get("id") or next_event_id(events_dir)
    chronicle_path = branch / "chronicle" / "objective.md"
    chronicle_id = result.get("chronicle_id") or next_chronicle_id(chronicle_path)
    event_title = result["event"].get("title") or queue.get("title") or "Queued event settled"
    event_file = events_dir / f"{event_id}-{slug(event_title)}.md"
    return {
        "world": str(world),
        "branch_path": branch_path,
        "queue_id": queue.get("queue_id"),
        "event_id": event_id,
        "event_file": relative_inside(event_file, world),
        "chronicle_id": chronicle_id,
        "writes": [
            relative_inside(event_file, world),
            f"{branch_path}/queues/events.jsonl",
            f"{branch_path}/CURRENT.md",
            f"{branch_path}/SAVE.md",
            f"{branch_path}/chronicle/objective.md",
            "dashboard/timeline.json",
            "dashboard/data.json",
            "system/turn-ledger.jsonl",
            "system/file-manifest.json",
        ],
    }


def apply_settlement(world: Path, branch: Path, branch_path: str, queue_entries: list[dict], queue: dict, result: dict, plan: dict) -> None:
    event_id = plan["event_id"]
    chronicle_id = plan["chronicle_id"]
    event_file = world / plan["event_file"]
    queue_id = str(queue.get("queue_id"))
    event_time = result["event"].get("time") or queue.get("trigger_time") or "unknown"
    event = result.get("event", {})

    event_markdown = f"""# {event_id} {result['event'].get('title') or queue.get('title') or 'Queued event settled'}

- id: {event_id}
- type: {result['event'].get('type', queue.get('kind', 'queued-event'))}
- time: {event_time}
- branch_id: {queue.get('branch_id', 'main')}
- queue_id: {queue_id}
- queue_kind: {queue.get('kind', '')}
- queue_priority: {queue.get('priority', '')}
- queue_source: {queue.get('source', '')}
- location: {event.get('location') or ''}
- actors: {format_list(event.get('actors') or queue.get('targets'))}
- cause_refs: {format_list(event.get('cause_refs'))}
- cause_notes: {format_list(event.get('cause_notes') or event.get('causes'))}
- effect_refs: {format_list(event.get('effect_refs'))}
- effect_notes: {format_list(event.get('effect_notes') or event.get('effects'))}
- tags: {format_list(event.get('tags') or [queue.get('kind', 'queued-event')])}
- source: {queue.get('source', '')}

## Queued premise

{queue.get('summary') or queue.get('title') or ''}

## Settlement summary

{result['summary']}

## Visible narration

{result.get('_narrative_layers', {}).get('visible_narration', result.get('visible_narration', result['summary']))}

## GM summary

{result.get('_narrative_layers', {}).get('gm_summary', result['summary'])}

## Settlement plan

```json
{json.dumps(result.get('_narrative_layers', {}).get('settlement_plan', {}), ensure_ascii=False, indent=2)}
```

## Consequences

{result.get('consequences', 'No structured consequences supplied.')}
"""
    write_text(event_file, event_markdown)

    for update in result.get("state_appends", []):
        rel = update.get("path")
        text = update.get("text")
        if not rel or not text:
            continue
        target_path = (world / rel).resolve()
        relative_inside(target_path, world)
        allowed = f"{branch_path}/state/"
        if not target_path.relative_to(world).as_posix().startswith(allowed):
            raise SystemExit(f"state append is outside active branch state: {rel}")
        append_text(target_path, "\n\n## Queued event update\n\n" + text.strip() + "\n")

    for entry in queue_entries:
        if entry.get("queue_id") == queue_id:
            entry["status"] = "settled"
            entry["settled_at"] = utc_now()
            entry["event_id"] = event_id
            entry["event_file"] = plan["event_file"]
    write_queue(branch, queue_entries)

    write_text(branch / "CURRENT.md", "# CURRENT\n\n" + result["current_scene"])

    save_path = branch / "SAVE.md"
    save_text = save_path.read_text(encoding="utf-8")
    save_updates = result.get("save_updates", {})
    save_text = replace_or_append_field(save_text, "current_scene", save_updates.get("current_scene", result["summary"]))
    if "world_time" in save_updates:
        save_text = replace_or_append_field(save_text, "world_time", save_updates["world_time"])
    elif event_time != "unknown":
        save_text = replace_or_append_field(save_text, "world_time", event_time)
    if "focal_place" in save_updates:
        save_text = replace_or_append_field(save_text, "focal_place", save_updates["focal_place"])
    save_text = replace_or_append_field(save_text, "active_pauses", "[]")
    save_text = replace_or_append_field(save_text, "latest_event", event_id)
    save_text = replace_or_append_field(save_text, "latest_chronicle_entry", chronicle_id)
    write_text(save_path, save_text)

    chronicle_text = result.get("chronicle") or result["summary"]
    append_text(branch / "chronicle" / "objective.md", f"- {chronicle_id} | {event_time} | {chronicle_text}")

    timeline_path = world / "dashboard" / "timeline.json"
    timeline = read_json(timeline_path) if timeline_path.exists() else {"schema": "be-a-god.timeline.v1", "nodes": []}
    timeline.setdefault("nodes", []).append(
        {
            "id": chronicle_id,
            "event_id": event_id,
            "time": event_time,
            "label": result.get("timeline_label") or result["event"].get("title") or queue.get("title") or result["summary"][:40],
            "state": "confirmed",
            "source": plan["event_file"],
        }
    )
    write_json(timeline_path, timeline)

    dashboard_path = world / "dashboard" / "data.json"
    dashboard = read_json(dashboard_path) if dashboard_path.exists() else {"schema": "be-a-god.dashboard.v1"}
    dashboard["time"] = event_time
    pins = dashboard.setdefault("pins", [])
    pins.append(
        {
            "id": event_id,
            "kind": "event",
            "label": result.get("dashboard_label") or result["event"].get("title") or queue.get("title") or "队列事件",
            "source": plan["event_file"],
            "queue_id": queue_id,
        }
    )
    unresolved = dashboard.get("unresolved_choices", [])
    dashboard["unresolved_choices"] = [item for item in unresolved if item.get("queue_id") != queue_id]
    for piece_update in result.get("dashboard", {}).get("piece_updates", []):
        piece_id = piece_update.get("id")
        if not piece_id:
            continue
        for piece in dashboard.setdefault("pieces", []):
            if piece.get("id") == piece_id:
                piece.update(piece_update)
                break
        else:
            dashboard.setdefault("pieces", []).append(piece_update)
    write_json(dashboard_path, dashboard)

    ledger_entry = {
        "ts": utc_now(),
        "kind": "queued-event-settlement",
        "queue_id": queue_id,
        "event_id": event_id,
        "event_file": plan["event_file"],
        "chronicle_id": chronicle_id,
    }
    append_text(world / "system" / "turn-ledger.jsonl", json.dumps(ledger_entry, ensure_ascii=False))
    write_json(world / "system" / "file-manifest.json", build_manifest(world))


def main() -> int:
    parser = argparse.ArgumentParser(description="Settle a due queued event into confirmed world files.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--queue-id", required=True)
    parser.add_argument("--result", required=True, help="Confirmed queued event settlement JSON.")
    parser.add_argument("--allow-not-due", action="store_true", help="Allow settling a queued item before advance_world marks it due.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirmed", action="store_true")
    args = parser.parse_args()

    world = resolve_world(args.world)
    active = parse_active(world)
    branch_path = active["branch_path"]
    branch = world / branch_path
    queue_entries = load_queue(branch)
    queue = find_queue(queue_entries, args.queue_id)
    if queue.get("status") == "settled":
        raise SystemExit(f"queue item is already settled: {args.queue_id}")
    if queue.get("status") != "due" and not args.allow_not_due:
        raise SystemExit(f"queue item is not due yet: {args.queue_id}; pass --allow-not-due only after explicit player confirmation")
    result_path = Path(args.result).resolve()
    if not result_path.exists():
        raise SystemExit(f"settlement result not found: {result_path}")
    result = normalize_result(read_json(result_path))
    plan = settlement_plan(world, branch, branch_path, queue, result)

    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    if not args.confirmed:
        raise SystemExit("refusing to write queued event settlement without --confirmed")

    apply_settlement(world, branch, branch_path, queue_entries, queue, result, plan)
    print(f"Settled queued event {args.queue_id} as {plan['event_id']}: {world / plan['event_file']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
