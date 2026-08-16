# Player Quickstart

Use this when the player asks how to start, continue, open the frontend, install the skill, create a handoff, or configure non-Codex play.

## Install

From the project folder:

```powershell
python scripts/install_local_skill.py --skill-dir F:\be_a_god\be-a-god --run-smoke --confirmed --json
```

After installation, start a new Codex turn and invoke:

```text
$be-a-god 开始一个新世界
```

## Start a world in Codex

1. Tell Codex the premise, god role, starting region, tone, and hard boundaries.
2. Codex creates or updates a `WORLD-BRIEF.md` draft.
3. Confirm the draft.
4. Codex runs initialization and creates a world tree under `worlds/<world-id>/`.
5. Continue by saying `继续`, `观察地图`, `推进时间`, `点击某人`, or `降下神谕`.

Codex should read only the active save and needed source pointers, not the full story tree.

## Create the small playable demo world

Use this when you want a real tutorial world that can be opened and continued immediately:

```powershell
python scripts/create_demo_world.py --worlds-dir worlds --world-id reedbend-demo --confirmed --json
```

Then open:

```text
worlds\reedbend-demo\frontend\index.html
```

The demo is intentionally small: three locations, three visible characters, one queued flood-pressure event, one pending character interaction, weather/random log, mutable terrain brushes, timeline, dashboard, and frontend files.

## Continue play

Typical player commands:

- `继续`
- `观察地图`
- `推进 7 天`
- `和 CHAR-0001 对话`
- `忽略这个角色，除非我主动点开`
- `创建一个从 EVT-0003 分叉的新枝丫`
- `把河流改道，绕过北部森林`

## Open the frontend

Static mode:

```powershell
python scripts/prepare_frontend.py --world <world> --confirmed --overwrite
```

Then open:

```text
<world>\frontend\index.html
```

Local app mode:

```powershell
python scripts/serve_frontend.py --world <world>
```

Open the printed localhost URL. In app mode the frontend can refresh map/timeline/dashboard data and create action request files. It still does not directly settle canon.

Map controls:

- Use `＋`, `−`, mouse wheel, or `重置` to change the map view.
- Drag the map to pan when the brush editor is not actively picking points.
- The paper-map skin uses local high-resolution transparent PNG assets from `frontend/img/` for the UI frame, flags, forest, hills, mountains, creek, castle, village, bridge, road, farm, ruins, marsh, lake, shoreline rocks, parchment texture, and corners. These are decoration only; terrain truth still comes from `map-layers.json`.

## Change terrain

Command style:

```text
把主河道向西改，新增一条支流进入集市
```

Brush style:

1. Open frontend.
2. Use `画笔编辑器`.
3. Enter brush ID and kind.
4. Set width, density, jitter, and color if needed.
5. Click the map to place points.
6. Use undo or copy `points-json` when adjusting geometry.
7. Generate the terrain action request.
8. Confirm the suggested `set_map_brush.py` command only after the geometry is acceptable.

## Continue in a new Codex conversation

When the conversation grows long:

```powershell
python scripts/create_handoff.py --world <world> --confirmed --json
```

In the new conversation, tell Codex:

```text
$be-a-god 从这个世界继续：<world>
```

Codex should run:

```powershell
python scripts/resume_world.py --world <world> --dry-run
```

Then read only the `first_read` files before expanding sources.

## Use your own model API

Edit:

```text
<world>\setup\llm-api.config.json
```

Typical fields:

- `base_url`
- `endpoint_path`
- `model`
- `api_key_env`
- `temperature`
- `max_tokens`

Prefer setting the API key in the environment variable named by `api_key_env`.

Packaged one-turn flow:

1. Build or load a compact interaction packet.
2. Preview the external-model request without contacting the API.
3. When explicitly requested, call the API.
4. Inspect the candidate settlement JSON.
5. Commit canon only through the normal settlement script.

Create a support-only run packet and dry-run the model request:

```powershell
python scripts/external_play_turn.py --world <world> --target-id <id> --target-kind character --intent "对话" --confirmed --json
```

Call the configured API for an existing packet:

```powershell
python scripts/external_play_turn.py --world <world> --packet <packet-id-or-path> --prompt "Continue the current scene and return settlement JSON." --call --confirmed --json
```

The wrapper writes support files under:

```text
<world>\story\<branch>\runtime\external-model-runs\<run-id>\
```

If the model returns a JSON object, it is saved as `settlement-result.candidate.json`, checked by `validate_settlement_result.py`, and reported with suggested `settle_interaction.py` commands. The wrapper never settles canon by itself.

Low-level dry-run:

```powershell
python scripts/call_llm.py --world <world> --prompt "Preview the current scene without committing canon." --json
```

Low-level actual call:

```powershell
python scripts/call_llm.py --world <world> --prompt "Continue the current scene and return settlement JSON." --call --json
```

External model output must be inspected and then settled through normal scripts; it must not directly edit canon.
