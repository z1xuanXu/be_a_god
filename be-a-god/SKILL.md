---
name: be-a-god
description: Persistent Markdown god-simulation narrative game master for local worlds, maps, timelines, branches, random logs, and long-running save files.
---

# Be A God

Run a persistent "play as a god" simulation in the local workspace. Markdown holds player-readable narrative; JSON and JSONL hold deterministic state, indexes, map data, queues, timelines, and random logs. This skill has **no local web frontend**: play through the host conversation and scripts.

## Core Rule

Treat confirmed world files as durable game state. Never silently overwrite player-confirmed facts, random logs, branch pointers, deaths, world-ending facts, or manual Markdown edits.

## Start of Each Turn

1. Locate the active world: use the named path, otherwise inspect `worlds/*/ACTIVE.md`.
2. Read only `ACTIVE.md`, the active branch `SAVE.md`, `PLAYER.md`, and directly relevant cards/data.
3. For a resumed world, run `scripts/resume_world.py --world <world> --dry-run` first and follow `first_read`.
4. If manual edits may exist, run `scripts/detect_manual_edits.py --world <world> --dry-run` before normal play.

## Start a World

1. Gather missing essentials: premise, tone/content boundary, starting scale, god role, and locked facts.
2. Write a draft under `setup/drafts/` using `scripts/create_world_brief.py`.
3. Do not initialize formal files until the player confirms.
4. Validate with `scripts/validate_world_brief.py <draft> --require-confirmed`.
5. Initialize with `scripts/init_world.py --world-id <id> --brief <draft> --confirmed`.
6. Inspect `base/maps/hierarchy.json`, `base/maps/coordinates.json`, and `base/maps/terrain-brushes.json` before continuing. Preserve explicit `terrain_zones`; never replace structured geography with random terrain.

## Continue Play

Use action requests for player intent and settlement scripts for material semantic consequences.

- `scripts/create_action_request.py`: record non-canonical observe, speak, intervene, terrain, rule, branch, or advance requests.
- `scripts/make_interaction_packet.py`: construct bounded target context.
- `scripts/settle_interaction.py` and `scripts/settle_queued_event.py`: write confirmed narrative consequences into canon.
- `scripts/advance_world.py`: mechanical time advancement only.
- `scripts/set_map_brush.py`: apply reviewed, confirmed terrain geometry.
- `scripts/create_entity.py`, `scripts/move_entity.py`, and `scripts/wander_entities.py`: deterministic entity state.

## Inspect Derived Data

The project keeps JSON projections for tools and scripted inspection, not browser display:

```text
scripts/build_indexes.py --world <world>
scripts/build_map_layers.py --world <world>
scripts/build_timeline.py --world <world>
scripts/export_dashboard.py --world <world>
```

`dashboard/`, `indexes/`, and `system/file-manifest.json` are derived; source facts remain in `setup/`, `story/`, and `base/maps/`.

## References

Load only the relevant reference:

- `references/storage-contract.md`: authority, world layout, branches, manifests, handoffs.
- `references/game-master-protocol.md`: narration and bounded context.
- `references/narrative-quality.md`: causality and settlement quality.
- `references/narrative-template-guide.md`: optional structured templates.
- `references/script-catalog.md`: deterministic script responsibilities.
- `references/validation-scenarios.md`: core persistence and script scenarios.
- `references/player-quickstart.md`: player-facing start, continue, handoff, and external API flow.

## Validation

```text
scripts/validate_world.py --world <world> --json
scripts/check_install_ready.py --skill-dir <skill-dir> --run-smoke --json
```

## Safety

Honor the content profile without overriding platform requirements. Automation runs only during an active task unless the user explicitly configures a supported recurring job.
