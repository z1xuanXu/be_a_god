# Be A God Project Handoff

## Repository

- GitHub: `https://github.com/z1xuanXu/be_a_god`
- Branch: `main`
- Local root: `/Users/xuzixuan/Documents/BeAgod`
- Project type: persistent narrative god-simulation with canonical Markdown state and deterministic Python scripts.

## Product Direction

**The local web frontend has been intentionally removed.** Do not recreate browser UI, frontend templates, image assets, static exports, local HTTP UI servers, or frontend-only tests unless the user explicitly reverses this decision.

Use the host conversation plus world scripts for all gameplay. Keep map data as structured world state, not visual UI content.

The user prefers Chinese, direct factual reporting, and explicit separation between verified results and unverified claims.

## Current Player World

`worlds/plain-sea-marsh/` is a canonical player world. Do not delete, reset, or rewrite it without explicit user approval.

Its locked geographic order is:

```text
西岸平原 -> 黑潮大海 -> 沉舟险沼 -> 东岸平原
```

Its two characters are `CHAR-0001` 岑野 at `LOC-001` and `CHAR-0002` 澜禾 at `LOC-004`.

Canonical map sources are:

- `base/maps/hierarchy.json` — semantic nodes and `terrain_zones`
- `base/maps/coordinates.json` — normalized coordinates
- `base/maps/terrain-brushes.json` — persistent terrain geometry

The `terrain_zones` order is meaningful and must not be replaced by random terrain generation.

## Canonical and Derived State

Canonical:

- `ACTIVE.md`, `WORLD.md`, `PLAYER.md`, `CANON.md`
- `setup/`
- `story/<branch>/SAVE.md`, events, entity/location state, chronicle, queues, random logs
- `base/maps/`

Derived/rebuildable:

- `dashboard/`
- `indexes/`
- `system/file-manifest.json`

Runtime files such as action requests, interaction packets, handoffs, external-model runs, and resume packets are support/audit data; they are not canon without a settlement script.

## Core Workflow

1. For a resumed world, run `scripts/resume_world.py --world <world> --dry-run`.
2. Read only its `first_read` paths before expanding history.
3. Use action requests for player intent that must be reviewed before effect.
4. Use settlement scripts for confirmed semantic events.
5. Rebuild indexes, map layers, timeline, dashboard, and file manifest after deterministic state changes where the responsible script does not already do so.

## Verification

```bash
uv run --with pytest pytest tests/test_event_recall.py -q
python3 be-a-god/scripts/check_install_ready.py --skill-dir be-a-god --run-smoke --json
python3 be-a-god/scripts/validate_world.py --world worlds/plain-sea-marsh --json
```

The full legacy pytest suite previously contained hard-coded Windows paths; do not claim a full-suite pass without verifying it on the target platform.

## Cleanup

Safe to delete/recreate:

- `.pytest_cache/`
- `__pycache__/`
- temporary logs and screenshots

Do not delete without explicit approval:

- `worlds/<id>/story/`
- `worlds/<id>/base/maps/`
- `worlds/<id>/setup/`
- `worlds/<id>/dashboard/`
- `system/file-manifest.json` unless immediately rebuilding it
- `worlds/<id>/setup/llm-api.config.json`

## Git Discipline

- Check `git status --short --branch` before edits and commits.
- Do not reset unrelated user changes.
- Do not commit secrets, caches, logs, screenshots, or removed frontend artifacts.
- Push to `origin/main` only after requested verification.
