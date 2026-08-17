# Be A God Project Handoff

This document is for the next AI agent taking over this repository. Read it before changing code or world state.

## Repository

- GitHub: `https://github.com/z1xuanXu/be_a_god`
- Branch: `main`
- Remote: `origin`
- Repository type: persistent narrative god-simulation game with canonical Markdown state, deterministic Python scripts, derived JSON, and a local HTML/CSS/JS frontend.
- Local development root on the current machine: `/Users/xuzixuan/Documents/BeAgod`

## Current User Priorities

The user prefers Chinese, direct factual reporting, and explicit separation between verified results and unverified claims.

Current product priorities:

- Natural-language geography must become an ordered, deterministic map, not random terrain noise.
- A map must distinguish terrain cells, terrain regions, locations, events, and movable units.
- Locations and events must not be rendered as meaningless building/place chess pieces.
- Movable units are icon-only on the map; their attributes appear in the right detail panel.
- A unit roster below the map lists every mapped movable unit. Clicking a roster item centers and zooms the map to that unit.
- The browser may read only filtered `dashboard.story` projections and derived map data; never expose raw Markdown, GM summaries, secrets, settlement plans, or future/private information.

## Current World

The current player world is:

```text
worlds/plain-sea-marsh/
```

It was created from a confirmed brief and currently contains:

- ordered terrain regions: west plain -> central sea -> danger marsh -> east plain;
- two characters: `CHAR-0001` 岑野 at `LOC-001`, and `CHAR-0002` 澜禾 at `LOC-004`;
- canonical locations `LOC-001` through `LOC-004`;
- first confirmed event `EVT-0001`;
- normalized map coordinates with `cell_size_meters: 5000`.

The world passed:

```bash
python3 be-a-god/scripts/validate_world.py \
  --world worlds/plain-sea-marsh --json
```

Do not reset, delete, or rewrite this world unless the user explicitly asks.

The world-local `frontend/` directory is intentionally absent after cleanup. Recreate it with:

```bash
python3 be-a-god/scripts/prepare_frontend.py \
  --world worlds/plain-sea-marsh --confirmed --overwrite
```

Serve it on an unused port, for example:

```bash
python3 be-a-god/scripts/serve_frontend.py \
  --world worlds/plain-sea-marsh --port 8766
```

Port `8766` may already be occupied by an older server. Check first with `lsof -nP -iTCP:8766 -sTCP:LISTEN`; use another port if needed.

## Canonical vs Derived Files

Canonical world state includes:

- `ACTIVE.md`
- `WORLD.md`, `PLAYER.md`, `CANON.md`
- `setup/WORLD-BRIEF.md`, `setup/world-spec.json`, and setup profiles
- `story/<branch>/SAVE.md`
- `story/<branch>/events/`
- `story/<branch>/state/entities/`
- `story/<branch>/state/locations/`
- `story/<branch>/chronicle/`
- `story/<branch>/queues/`
- `story/<branch>/random/`
- `base/maps/coordinates.json`
- `base/maps/hierarchy.json`
- `base/maps/terrain-brushes.json`

Derived/rebuildable files include:

- `dashboard/data.json`
- `dashboard/timeline.json`
- `dashboard/map-layers.json`
- `indexes/*.json`
- `system/file-manifest.json`
- `worlds/*/frontend/`

Support/runtime files include action requests, packets, drafts, handoffs, resume packets, browser artifacts, and external-model output. Do not treat them as canon without the normal settlement workflow.

## Map Semantics Fix

The previous frontend used deterministic noise and fixed decorative stamps to fill the map. It also rendered locations, events, and a fake world overview as map pieces. This produced unrelated terrain, duplicate long labels, truncated text, and building icons for plain regions.

The current implementation changes that contract:

### Creation map data

`init_world.py` now writes `terrain_zones` into `base/maps/hierarchy.json` when a confirmed brief contains an ordered two-plain plus sea description. Each zone has:

```json
{
  "id": "ZONE-CENTRAL-SEA",
  "name": "中央大海",
  "terrain": "coast",
  "bounds": [30, 0, 68, 100]
}
```

`build_map_layers.py` exports `terrain_zones` to `dashboard/map-layers.json`.

The frontend uses these bounds to assign terrain to every visible hex. When zones exist, they take precedence over background noise and base creation brushes. Only an explicit active-branch `/state/` brush can override a zone. This prevents old creation brushes from turning the central sea back into land.

`plain-sea-marsh` has these zones:

```text
[0, 0, 30, 100]   plain  西岸平原
[30, 0, 68, 100]  coast  黑潮大海
[52, 56, 68, 100] marsh  沉舟险沼, danger=true
[68, 0, 100, 100] plain  东岸平原
```

The old erroneous creation river brush was removed from this world. The marsh brush remains as a sparse danger detail, while the central sea is rendered as water cells.

### Frontend rendering

`be-a-god/assets/frontend-template/app.js` now:

- reads `mapLayers.terrain_zones`;
- renders one zone label per region instead of repeating location names on cells;
- does not render `mapLayers.nodes` as building/place pieces;
- does not render `dashboard.pins` as map chess pieces;
- does not render the fake `worldOverview` piece;
- renders actual `dashboard.pieces` as transparent icon-only units;
- renders `renderUnitRoster()` below the map;
- focuses and zooms to a unit when its roster button is clicked.

`export_dashboard.py` resolves a character's `location` through `base/maps/coordinates.json` and exports `x`, `y`, and `location_name` when the entity card lacks direct coordinates.

The reusable frontend template is the durable source. World-local `frontend/` copies must be regenerated, never edited as the primary fix.

## Validation

Run the focused map regression tests:

```bash
uv run --with pytest pytest tests/test_map_semantics.py -q
```

Run frontend syntax checking:

```bash
node --check be-a-god/assets/frontend-template/app.js
```

Run world validation:

```bash
python3 be-a-god/scripts/validate_world.py \
  --world worlds/plain-sea-marsh --json
```

Run package readiness and smoke validation:

```bash
python3 be-a-god/scripts/check_install_ready.py \
  --skill-dir be-a-god --run-smoke --json
```

At the last handoff, all of the above passed. The focused test result was `3 passed`; package readiness reported `ready=true`, `error_count=0`, `warning_count=0`; the smoke result reported `smoke_test.py passed`.

The full repository pytest suite still contains older tests with hard-coded Windows paths such as `F:/be_a_god/...`; on macOS those tests cannot collect without a compatibility fix. Do not claim the full suite passes unless that path issue is addressed and verified.

## Cleanup Rules

Safe to delete/recreate:

- `.pytest_cache/`
- `__pycache__/`
- `worlds/*/frontend/`
- local browser profiles, screenshots, logs, and temporary files

Do not delete without explicit user approval:

- `worlds/<id>/story/`
- `worlds/<id>/base/maps/`
- `worlds/<id>/setup/`
- `worlds/<id>/dashboard/`
- `system/file-manifest.json` unless immediately rebuilding it
- `worlds/<id>/setup/llm-api.config.json`

Never commit API keys, generated frontend copies, Python caches, browser profiles, or temporary screenshots.

## Git Discipline

- Check `git status --short --branch` before and after changes.
- Do not reset/revert unrelated user changes.
- Commit only files relevant to the task.
- Push to `origin/main` only after requested verification.
- Use conventional commit messages.

## Recommended Next Steps

1. Read this handoff, `README.md`, `be-a-god/SKILL.md`, and the relevant frontend/storage references.
2. Check `git status --short --branch`.
3. Validate `worlds/plain-sea-marsh` before gameplay changes.
4. For map issues, inspect in order:

```text
setup/WORLD-BRIEF.md
-> base/maps/hierarchy.json
-> base/maps/coordinates.json
-> base/maps/terrain-brushes.json
-> dashboard/map-layers.json
-> assets/frontend-template/app.js
```

5. Rebuild a world-local frontend only when testing the UI.
6. Keep semantic settlement and canonical world changes behind the supported action-request and settlement workflows.
