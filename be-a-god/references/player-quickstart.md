# Player Quickstart

Use this when the player asks how to start, continue, inspect a world, create a handoff, or configure external-model play. This project has no local web frontend; interact through the host conversation and deterministic scripts.

## Install

From the project folder:

```bash
python3 be-a-god/scripts/install_local_skill.py --skill-dir be-a-god --run-smoke --confirmed --json
```

Start a new host conversation and invoke:

```text
$be-a-god 开始一个新世界
```

## Start a World

1. State the premise, god role, starting region, tone, content boundaries, and locked facts.
2. The host writes a `WORLD-BRIEF.md` draft.
3. Confirm the draft.
4. The host initializes `worlds/<world-id>/`.
5. Continue with commands such as `继续`, `观察地图数据`, `推进 7 天`, `和 CHAR-0001 对话`, or `降下神谕`.

## Create a Demo World

```bash
python3 be-a-god/scripts/create_demo_world.py --worlds-dir worlds --world-id reedbend-demo --confirmed --json
```

The demo contains locations, characters, a queued flood-pressure event, a pending interaction, weather/random logs, terrain brush data, timeline data, and dashboard exports.

## Inspect Map and World State

Use the host conversation for narrative inspection. For derived structured data, rebuild and inspect:

```bash
python3 be-a-god/scripts/build_map_layers.py --world <world>
python3 be-a-god/scripts/build_timeline.py --world <world>
python3 be-a-god/scripts/export_dashboard.py --world <world>
```

The canonical map source is `base/maps/coordinates.json`, `base/maps/hierarchy.json`, and `base/maps/terrain-brushes.json`. Dashboard JSON is derived data, not canon.

## Change Terrain

Describe the intended change in conversation. The host first creates a non-canonical terrain request, then applies reviewed geometry through `set_map_brush.py`.

```text
把主河道向西改，新增一条支流进入集市
```

## Continue in a New Conversation

```bash
python3 be-a-god/scripts/create_handoff.py --world <world> --confirmed --json
```

Then say:

```text
$be-a-god 从这个世界继续：<world>
```

The host should run:

```bash
python3 be-a-god/scripts/resume_world.py --world <world> --dry-run
```

Read only the returned `first_read` paths before expanding old source pointers.

## Use Your Own Model API

Configure `<world>/setup/llm-api.config.json`. Prefer the environment variable named by `api_key_env` for secrets.

Preview a turn without a network call:

```bash
python3 be-a-god/scripts/external_play_turn.py --world <world> --target-id <id> --target-kind character --intent "对话" --confirmed --json
```

Call a configured API only when explicitly requested:

```bash
python3 be-a-god/scripts/external_play_turn.py --world <world> --packet <packet-id-or-path> --prompt "Continue the current scene and return settlement JSON." --call --confirmed --json
```

Inspect the candidate result and settle canon only through the normal confirmed settlement scripts.
