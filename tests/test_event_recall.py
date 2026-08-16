import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "be-a-god" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from build_event_graph import build_graph
from make_interaction_packet import make_packet
from read_source_packet import build_packet as build_source_packet


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def event(path: Path, event_id: str, actor: str, tags: str, causes: str = "[]", body: str = "正文") -> None:
    write(
        path,
        f"# {event_id} event\n\n- id: {event_id}\n- type: interaction\n- time: year 1, day 1\n"
        f"- branch_id: test\n- location: LOC-001\n- actors: [{actor}]\n- causes: {causes}\n"
        f"- effects: [natural language outcome]\n- tags: [{tags}]\n\n## Visible narration\n\n{body}\n",
    )


def world_tree(tmp_path: Path) -> Path:
    world = tmp_path / "world"
    write(world / "ACTIVE.md", "# ACTIVE\n\nworld_id: test\nbranch_id: child\nbranch_path: story/branches/child\nsave_path: story/branches/child/SAVE.md\n")
    write(world / "PLAYER.md", "# PLAYER\n\n- god_role: test\n")
    write(world / "CANON.md", "# CANON\n")
    write(world / "setup/world-rules.json", '{"rules": []}\n')
    write(world / "setup/narrative-profile.json", '{"default_profile":"p","profiles":{"p":{"priority_order":[],"output_layers":{"required":[]},"balance":{}}}}\n')
    write(world / "dashboard/data.json", '{"pieces": []}\n')

    write(world / "story/main/SAVE.md", "# SAVE\n\n- branch_id: main\n- parent_save: none\n- world_time: year 1, day 3\n")
    event(world / "story/main/events/EVT-0001-start.md", "EVT-0001", "CHAR-0001", "start", body="父枝第一事件")
    event(world / "story/main/events/EVT-0002-oath.md", "EVT-0002", "CHAR-0001", "oath,evidence", causes="[EVT-0001, rising river]", body="关键旧誓正文")
    event(world / "story/main/events/EVT-0003-after-fork.md", "EVT-0003", "CHAR-0001", "later", body="分叉之后不可继承")

    child = world / "story/branches/child"
    write(child / "SAVE.md", "# SAVE\n\n- branch_id: child\n- parent_save: story/main/SAVE.md\n- fork_event: EVT-0002\n- inherit_until: fork_event\n- world_time: year 1, day 4\n- focal_place: Market\n- current_scene: child current\n")
    write(child / "CURRENT.md", "# CURRENT\n\nchild current\n")
    write(child / "state/entities/CHAR-0001-hero.md", "# Hero\n\n- id: CHAR-0001\n- kind: character\n- public_name: Hero\n- location: LOC-001\n")
    event(child / "events/EVT-C001-child.md", "EVT-C001", "CHAR-0001", "child", causes="[EVT-0002]", body="子枝当前事件")

    sibling = world / "story/branches/sibling"
    write(sibling / "SAVE.md", "# SAVE\n\n- branch_id: sibling\n- parent_save: story/main/SAVE.md\n- fork_event: EVT-0001\n")
    event(sibling / "events/EVT-S001-secret.md", "EVT-S001", "CHAR-0001", "secret", body="兄弟枝秘密")
    return world


def test_event_graph_uses_valid_refs_and_branch_ancestry(tmp_path: Path) -> None:
    graph = build_graph(world_tree(tmp_path))
    sources = {node["source"] for node in graph["nodes"]}
    assert "story/main/events/EVT-0001-start.md" in sources
    assert "story/main/events/EVT-0002-oath.md" in sources
    assert "story/branches/child/events/EVT-C001-child.md" in sources
    assert "story/main/events/EVT-0003-after-fork.md" not in sources
    assert not any("sibling" in source for source in sources)
    keys = {node["key"] for node in graph["nodes"]}
    assert all(link["source"] in keys and link["target"] in keys for link in graph["links"])
    oath = next(node for node in graph["nodes"] if node["id"] == "EVT-0002")
    assert oath["cause_refs"] == ["EVT-0001"]
    assert oath["cause_notes"] == ["rising river"]
    assert oath["effect_refs"] == []
    assert oath["effect_notes"] == ["natural language outcome"]
    assert graph["unresolved_refs"] == []


def test_interaction_packet_selects_and_reads_key_old_events(tmp_path: Path) -> None:
    world = world_tree(tmp_path)
    args = argparse.Namespace(
        world=str(world), target_id="CHAR-0001", target_kind="character",
        intent="ask about oath evidence", mode="dialogue", target_file=None,
        source_budget=6, packet_id="IP-TEST", request_id=None, dry_run=True,
    )
    packet, _ = make_packet(args)
    recall = packet["history_context"]
    assert [item["event_id"] for item in recall["selected_events"]][:2] == ["EVT-0002", "EVT-C001"]
    joined = "\n".join(item["text"] for item in recall["sources"])
    assert "关键旧誓正文" in joined
    assert "子枝当前事件" in joined
    assert "分叉之后不可继承" not in joined
    assert "兄弟枝秘密" not in joined
    assert recall["used_chars"] <= recall["total_budget"]


def test_source_reader_blocks_parent_event_after_fork(tmp_path: Path) -> None:
    world = world_tree(tmp_path)
    packet = build_source_packet(
        world,
        ["story/main/events/EVT-0002-oath.md", "story/main/events/EVT-0003-after-fork.md", "story/branches/sibling/events/EVT-S001-secret.md"],
        max_chars=1600,
        total_budget=5000,
    )
    by_path = {item["path"]: item for item in packet["sources"]}
    assert by_path["story/main/events/EVT-0002-oath.md"]["allowed"] is True
    assert by_path["story/main/events/EVT-0003-after-fork.md"]["allowed"] is False
    assert by_path["story/branches/sibling/events/EVT-S001-secret.md"]["allowed"] is False
