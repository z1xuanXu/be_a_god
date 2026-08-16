# Be A God Project Handoff

This document is for the next AI agent taking over this repository. Read it before changing code or world state.

## Repository

- Local root: `F:\be_a_god`
- GitHub: `https://github.com/z1xuanXu/be_a_god`
- Branch: `main`
- Current baseline commit: `9b74ff8 fix: materialize maps from natural language creation briefs`
- Git remote: `origin` points to the GitHub repository above.

The repository is a persistent narrative god-simulation game. It combines Markdown canonical world state, deterministic Python scripts, derived JSON, and a local HTML/CSS/JS frontend.

## First Reads

Read these before making a behavioral change:

1. `README.md`
2. `be-a-god/SKILL.md`
3. `be-a-god/references/storage-contract.md`
4. `be-a-god/references/frontend-contract.md`
5. `be-a-god/references/narrative-quality.md` for story/settlement work
6. `worlds/reedbend-demo/ACTIVE.md`
7. `worlds/reedbend-demo/story/main/SAVE.md`

For a resumed play session, run:

```bash
PY='C:/Users/xuzix/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
"$PY" 'F:/be_a_god/be-a-god/scripts/resume_world.py' \
  --world 'F:/be_a_god/worlds/reedbend-demo' --dry-run
```

Read only the `first_read` files returned by that command before expanding historical sources.

## Current User Priorities

The user prefers Chinese, direct factual reporting, and explicit separation between verified results and unverified claims.

Product requirements that must be preserved:

- The frontend is independently playable: a story directory stays on the left and player-visible story prose appears below the map.
- The frontend may read only filtered `dashboard.story` projections. Never expose raw Markdown, GM summaries, secrets, settlement plans, or future/private information to the browser.
- Map characters, moving units, vehicles, buildings, resources, objects, cities, and events use transparent PNG medieval pennant pieces with strong dark outlines. Do not add circular, square, card, parchment-pill, or gradient backing surfaces behind map pieces.
- Non-map buttons, inputs, selects, and textareas use generated transparent medieval control artwork. Live text stays as DOM text over the artwork. Native dragging is disabled for controls/decorations, but map panning and explicit request-row dragging remain enabled.
- Every map cell represents `5000m x 5000m`. The lower-left scale bar reads `0 - 5 km` and matches one currently visible cell width.
- Pieces must stay within a single active hex cell. Current CSS/JS target 72% of active cell width and height.
- Final manuscript export must remain faithful to stored choices, scenes, causes, player-visible narration, and branch state. Editorial prose may bridge scenes but must not invent missing major canonical facts.

## Architecture and Data Authority

### Canonical world state

A world is rooted under `worlds/<world-id>/`.

Important authoritative files:

- `ACTIVE.md`: active branch and save path.
- `story/<branch>/SAVE.md`: current time, scene, branch pointers, relevant entity/location pointers.
- `story/<branch>/events/EVT-*.md`: confirmed event records.
- `story/<branch>/state/entities/*.md`: durable entity state.
- `story/<branch>/state/locations/*.md`: durable location state.
- `story/<branch>/chronicle/`: objective and epic chronicle records.
- `story/<branch>/queues/events.jsonl`: queued events.
- `base/maps/hierarchy.json`: semantic map nodes.
- `base/maps/coordinates.json`: normalized `0..100` map coordinates.
- `base/maps/terrain-brushes.json`: persistent terrain geometry.
- `setup/WORLD-BRIEF.md`: confirmed creation brief.

Do not silently overwrite player-confirmed facts, branch pointers, random logs, manual edits, or canonical story state.

### Derived files

These are regenerated and must not be manually treated as canon:

- `dashboard/data.json`
- `dashboard/timeline.json`
- `dashboard/map-layers.json`
- `indexes/*.json`
- `system/file-manifest.json`
- `worlds/*/frontend/`

`worlds/*/frontend/` is deliberately Git-ignored. Rebuild it from the template; do not make durable fixes only in that copy.

### Support-only files

Runtime packets, action requests, drafts, handoffs, external model output, and browser data are support/audit artifacts. They are not automatically canonical.

## Main Scripts

Core scripts live in `be-a-god/scripts/`.

- `create_world_brief.py`: writes a player-editable `WORLD-BRIEF` draft.
- `validate_world_brief.py`: validates a confirmed brief.
- `init_world.py`: creates a formal world from a confirmed brief.
- `build_map_layers.py`: builds frontend map data from canonical map files.
- `export_dashboard.py`: exports player-safe dashboard data and story catalog.
- `build_timeline.py`: builds timeline projection.
- `build_indexes.py`: builds entity/location/event indexes and event graph.
- `prepare_frontend.py`: copies the reusable frontend template into a world-local frontend folder.
- `serve_frontend.py`: serves local frontend mode and limited mechanical endpoints.
- `make_interaction_packet.py`: makes bounded interaction context.
- `read_source_packet.py`: reads exact approved source pointers under a budget.
- `settle_interaction.py` / `settle_queued_event.py`: only these settle semantic events into canon.
- `advance_world.py`: mechanical time advancement only. It does not create a full confirmed event by itself.
- `set_map_brush.py`: deterministic confirmed terrain brush write.
- `create_branch.py`, `draft_branch.py`, `switch_branch.py`: branch workflow.

## Natural-Language Creation Map Fix

This was the latest functional defect and is fixed in commit `9b74ff8`.

### Previous failure

The creation wizard generated only prose `WORLD-BRIEF.md`. `init_world.py` then created empty `hierarchy.json` and `coordinates.json`. The frontend drew fixed demo terrain and used pseudo-random fallback positions for pieces without coordinates. A newly created world could therefore describe a river kingdom but show unrelated/default map terrain and incorrectly placed pieces.

### Current behavior

`init_world.py` calls `materialize_creation_map()`:

- It creates `LOC-START` at normalized coordinates `x=50, y=50` for the starting region.
- It writes semantic nodes into `base/maps/hierarchy.json`.
- It writes coordinates and `cell_size_meters: 5000` into `base/maps/coordinates.json`.
- It derives initial terrain brushes from recognized confirmed-brief geography terms.
- It stores `map_generation` metadata in hierarchy, terrain brush state, and map-layer dashboard output.

Recognized terms currently cover river/stream, forest/woods, mountains, desert, marsh/swamp, coast/sea/island, snow/tundra, and volcano/volcanic, including Chinese equivalents.

When recognized geography exists:

```json
{
  "status": "generated",
  "source": "setup/WORLD-BRIEF.md",
  "method": "confirmed-brief-keyword-seed"
}
```

When it does not:

```json
{
  "status": "pending"
}
```

The frontend no longer uses pseudo-random fallback positions. Objects without valid coordinates are not displayed as falsely positioned pieces. This is intentional. Do not restore pseudo-random placement.

### Important limitation

The current creation map generator is deterministic keyword seeding, not a full semantic map planner. It produces a coherent initial map from confirmed terms, but it does not parse arbitrary spatial prose such as "the city lies east of the second tributary" into exact geometry. If asked to improve this, create an explicit reviewed map-plan stage or structured map data; do not let an AI silently write canonical geometry from ambiguous prose.

### Migration

This fix applies to worlds initialized after `9b74ff8`. Existing worlds should not be silently rewritten. For an old world, either:

1. create a reviewed migration plan for nodes, coordinates, and brushes, then apply it through supported deterministic scripts; or
2. let the player draw/review terrain with the map brush editor and commit explicit `points-json`.

## Frontend and Map Details

Reusable source template:

```text
be-a-god/assets/frontend-template/
```

Primary files:

- `app.js`: map rendering, zoom/pan, piece routing, creation wizard, local backend calls.
- `styles.css`: medieval UI skin, transparent map pieces, cell-relative piece sizing, scale bar.
- `img/`: generated terrain, city/unit, button/input assets.

The map is a display projection with normalized `0..100` coordinates. It has three visible zoom levels:

- world: `23 x 16 = 368` cells
- region: `31 x 21 = 651` cells
- scene: `47 x 32 = 1504` cells

Only the active level is rendered. This was necessary to avoid rendering all 2,523 hexes simultaneously. On same-level pan/zoom, only the map container transform changes. Rebuild occurs only at a level boundary.

Do not reintroduce per-tile child image elements or map-wide node traversal on every pointer move.

Map pieces snap to the active visible level. They are intentionally display-snapped; original `0..100` source coordinates and source pointers remain in detail data.

## History Recall and Branching

The project has branch-aware bounded history recall:

- `indexes/event-graph.json` uses branch-qualified node keys.
- `make_interaction_packet.py` ranks up to three old events by actor/location/intent/tag relevance.
- It reads event source pointers under a bounded character budget.
- `read_source_packet.py` allows only the active branch and permitted parent history before `fork_event`; sibling branches are rejected.
- Structured event causes/effects use event IDs. Natural language belongs in `cause_notes` / `effect_notes`.

Regression tests are in `tests/test_event_recall.py`.

## Story Persistence Caveat

The current demo world has confirmed event files through `EVT-0007`. A later mechanical five-day advance updated time/current-scene data but did not create matching confirmed event and chronicle entries. Do not claim it is a complete continuous manuscript.

For future work, persist scene-level records for normal transitions and confirmed event-level records for material outcomes. Final export may add non-canonical transitions and prose polish, but not major unstored choices or consequences.

## Current Demo World

```text
worlds/reedbend-demo/
```

This is a test/demo world, not a neutral fresh-world template. It contains existing narrative and a manually confirmed river brush around Mira from prior QA. Do not reset, rewrite, or advance it unless the user explicitly asks.

The frontend directory is normally absent after cleanup. Recreate it with:

```bash
PY='C:/Users/xuzix/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
"$PY" 'F:/be_a_god/be-a-god/scripts/prepare_frontend.py' \
  --world 'F:/be_a_god/worlds/reedbend-demo' --confirmed --overwrite
```

Then serve it:

```bash
"$PY" 'F:/be_a_god/be-a-god/scripts/serve_frontend.py' \
  --world 'F:/be_a_god/worlds/reedbend-demo' --port 8765
```

## Verification

On Windows the terminal runs Git Bash/MSYS. Use `python`, not `python3`; the runtime Python has previously been:

```bash
PY='C:/Users/xuzix/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
```

Run this before reporting a code change as complete:

```bash
node --check 'F:/be_a_god/be-a-god/assets/frontend-template/app.js'
uv run --with pytest pytest 'F:/be_a_god/tests' -q
"$PY" 'F:/be_a_god/be-a-god/scripts/check_install_ready.py' \
  --skill 'F:/be_a_god/be-a-god' --run-smoke --json
```

Known environment pitfall: an old shell environment variable `TMP=F:/be_a_god/worlds/.map-pipeline-test` can cause `uv`/pytest to fail after that temporary directory is deleted. If pytest fails with a missing `.map-pipeline-test/.tmp...` path, run:

```bash
unset TMP TMPDIR TEMP
```

and rerun the test command. This is a local shell contamination issue, not a project failure.

For frontend changes, additionally:

1. run `prepare_frontend.py` against a disposable or explicitly approved world;
2. start `serve_frontend.py` on an unused port;
3. test the real browser with an isolated profile;
4. inspect failed image count and browser console errors;
5. do not leave browser profile/cache directories inside the repository.

## Cleanup Rules

Safe to delete/recreate:

- `.pytest_cache/`
- `__pycache__/`
- `worlds/*/frontend/`
- local browser profiles, preview images, logs, and temporary screenshots

Do not delete without user approval:

- `worlds/<id>/story/`
- `worlds/<id>/base/maps/`
- `worlds/<id>/setup/`
- `worlds/<id>/dashboard/`
- `system/file-manifest.json` unless immediately rebuilding it
- `worlds/<id>/setup/llm-api.config.json` (local ignored configuration; may contain an active external API setup)

The old root-level versioned blueprints, old handoff, and validation fragment files were removed in `46ed206`. Do not recreate versioned `v1.xx补充.md` files for routine work. Prefer updating durable references, tests, and this handoff.

## Git Discipline

- Do not reset/revert unrelated user changes.
- Check `git status --short --branch` before edits and before commits.
- Commit only files relevant to the task.
- Push to `origin/main` only after requested/appropriate verification.
- Never put secrets, generated world frontend copies, Python caches, or browser profiles in Git.

## Recommended First Task for a New AI

1. Run `git status --short --branch`.
2. Read the first-read documents above.
3. Run the verification command block.
4. If continuing gameplay, run `resume_world.py --dry-run` before reading broad history.
5. If debugging a map issue, inspect this sequence first:

```text
setup/WORLD-BRIEF.md
-> base/maps/hierarchy.json
-> base/maps/coordinates.json
-> base/maps/terrain-brushes.json
-> dashboard/map-layers.json
-> frontend map rendering
```

6. If creating a new world, confirm the brief first; initialize it; inspect `map_generation`, `nodes`, `places`, and `brushes` before opening the frontend.
