#!/usr/bin/env python3
"""Build a lightweight event relationship graph for the active branch."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from read_source_packet import branch_scopes, event_is_within_limit


GRAPH_SCHEMA = "be-a-god.event-graph.v1"


def parse_active(world: Path) -> dict[str, str]:
    data = {}
    for line in (world / "ACTIVE.md").read_text(encoding="utf-8").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    data.setdefault("branch_path", "story/main")
    data.setdefault("branch_id", "main")
    return data


def parse_field(text: str, field: str) -> str | None:
    values = []
    pattern = re.compile(rf"^[ \t]*-[ \t]*{re.escape(field)}:[ \t]*(.*?)[ \t]*$", re.MULTILINE)
    for match in pattern.finditer(text):
        value = match.group(1).strip()
        if value:
            values.append(value)
    return values[-1] if values else None


def parse_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line.lstrip("# ").strip()
    return fallback


def parse_list(value: str | None) -> list[str]:
    if not value:
        return []
    raw = value.strip()
    if raw in {"[]", "none", "None", "null"}:
        return []
    if raw.startswith("[") and raw.endswith("]"):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            raw = raw[1:-1]
    return [item.strip().strip("'\"") for item in raw.split(",") if item.strip().strip("'\"")]


def add_to_bucket(index: dict[str, list[str]], key: str | None, event_id: str) -> None:
    if not key:
        return
    index.setdefault(key, []).append(event_id)


def parse_structured_refs(text: str, ref_field: str, legacy_field: str) -> list[str]:
    explicit = parse_field(text, ref_field)
    if explicit is not None:
        return parse_list(explicit)
    return [value for value in parse_list(parse_field(text, legacy_field)) if re.fullmatch(r"EVT-[A-Za-z0-9_-]+", value)]


def parse_legacy_notes(text: str, ref_field: str, legacy_field: str) -> list[str]:
    if parse_field(text, ref_field) is not None:
        return []
    return [value for value in parse_list(parse_field(text, legacy_field)) if not re.fullmatch(r"EVT-[A-Za-z0-9_-]+", value)]


def event_node(path: Path, world: Path, branch_path: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    event_id = parse_field(text, "id") or path.stem
    actors = parse_list(parse_field(text, "actors"))
    target_id = parse_field(text, "target_id")
    if target_id and target_id not in actors:
        actors.append(target_id)
    location = parse_field(text, "location")
    return {
        "id": event_id,
        "key": f"{branch_path}:{event_id}",
        "branch_path": branch_path,
        "title": parse_title(text, event_id),
        "type": parse_field(text, "type"),
        "time": parse_field(text, "time"),
        "branch_id": parse_field(text, "branch_id"),
        "location": location,
        "actors": actors,
        "causes": parse_structured_refs(text, "cause_refs", "causes"),
        "effects": parse_structured_refs(text, "effect_refs", "effects"),
        "declared_cause_notes": parse_list(parse_field(text, "cause_notes")) + parse_legacy_notes(text, "cause_refs", "causes"),
        "declared_effect_notes": parse_list(parse_field(text, "effect_notes")) + parse_legacy_notes(text, "effect_refs", "effects"),
        "tags": parse_list(parse_field(text, "tags")),
        "source": path.relative_to(world).as_posix(),
        "source_pointer": parse_field(text, "source") or parse_field(text, "packet") or parse_field(text, "queue_source"),
        "queue_id": parse_field(text, "queue_id"),
    }


def build_graph(world: Path) -> dict[str, Any]:
    active = parse_active(world)
    scopes = branch_scopes(world, active)
    nodes = []
    for scope in scopes:
        branch_path = str(scope["path"])
        for path in sorted((world / branch_path / "events").glob("EVT-*.md")):
            if event_is_within_limit(path, scope.get("event_limit")):
                nodes.append(event_node(path, world, branch_path))
    links: list[dict[str, str]] = []
    by_actor: dict[str, list[str]] = {}
    by_location: dict[str, list[str]] = {}
    by_tag: dict[str, list[str]] = {}

    visible_by_id: dict[str, list[str]] = {}
    for node in nodes:
        visible_by_id.setdefault(node["id"], []).append(node["key"])
    unresolved_refs: list[dict[str, str]] = []
    for node in nodes:
        event_id = node["id"]
        event_key = node["key"]
        add_to_bucket(by_location, node.get("location"), event_id)
        for actor in node.get("actors", []):
            add_to_bucket(by_actor, actor, event_id)
        for tag in node.get("tags", []):
            add_to_bucket(by_tag, tag, event_id)
        cause_refs, cause_notes = [], list(node.pop("declared_cause_notes", []))
        for cause in node.get("causes", []):
            matches = visible_by_id.get(cause, [])
            if len(matches) == 1:
                cause_refs.append(cause)
                links.append({"source": matches[0], "target": event_key, "kind": "causes"})
            else:
                cause_notes.append(cause)
        effect_refs, effect_notes = [], list(node.pop("declared_effect_notes", []))
        for effect in node.get("effects", []):
            matches = visible_by_id.get(effect, [])
            if len(matches) == 1:
                effect_refs.append(effect)
                links.append({"source": event_key, "target": matches[0], "kind": "effects"})
            else:
                effect_notes.append(effect)
        node["cause_refs"], node["cause_notes"] = cause_refs, cause_notes
        node["effect_refs"], node["effect_notes"] = effect_refs, effect_notes

    return {
        "schema": GRAPH_SCHEMA,
        "world_id": active.get("world_id", world.name),
        "branch_id": active.get("branch_id", "main"),
        "branch_path": active["branch_path"],
        "nodes": nodes,
        "links": links,
        "by_actor": {key: sorted(set(value)) for key, value in sorted(by_actor.items())},
        "by_location": {key: sorted(set(value)) for key, value in sorted(by_location.items())},
        "by_tag": {key: sorted(set(value)) for key, value in sorted(by_tag.items())},
        "unresolved_refs": unresolved_refs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build active branch event graph index.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    world = Path(args.world).resolve()
    if not (world / "ACTIVE.md").exists():
        raise SystemExit(f"ACTIVE.md not found in world: {world}")
    graph = build_graph(world)
    if args.dry_run:
        print(json.dumps(graph, ensure_ascii=False, indent=2))
        return 0
    output = world / "indexes" / "event-graph.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built event graph: {len(graph['nodes'])} nodes, {len(graph['links'])} links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
