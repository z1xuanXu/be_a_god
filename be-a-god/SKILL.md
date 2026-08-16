---
name: be-a-god
description: Persistent god-simulation narrative game master for Codex or an external OpenAI-compatible model API. Use when the user wants to start, continue, inspect, advance, branch, intervene, configure model hosting, or run a local Markdown-based simulated world with map pieces, chronicle, timelines, random events, and long-running save files.
---

# Be A God

Run a persistent “play as a god” simulation inside the local workspace. Keep the world readable and editable as Markdown, but use scripts and structured files for deterministic state, random logs, indexes, timelines, and frontend data.

## Core rule

Treat confirmed world files as durable game state. Do not silently overwrite player-confirmed facts, random logs, branch pointers, deaths, world-ending facts, or manual Markdown edits.

Support two host modes:

- Codex-hosted play: continue the story directly in the Codex conversation and use scripts for durable state changes.
- External-model play: use `setup/llm-api.config.json` plus `scripts/call_llm.py` to send compact packets to an OpenAI-compatible API outside Codex. The external model may generate prose or result JSON, but durable writes still go through the same settlement scripts.

Use the minimum context needed for the current action. For close-up interaction, read only the active save, the current branch summary, the clicked entity or location, and explicit source pointers. Read older story only when promises, secrets, conflicts, irreversible actions, or branch inheritance require it.

Use `setup/narrative-profile.json` as the persistent narration-quality default. The default profile is `hybrid-historical`: close-up character drama plus long-run civilization evolution, with causality, continuity, character agency, and historical texture taking priority over forced spectacle. Use `references/narrative-quality.md` when resolving meaningful events, creating important characters, writing external-model prompts, or checking settlement quality.

Use `references/narrative-template-guide.md` only when a model result needs stronger structure. Pick one small template from `assets/narrative-templates/` for interaction settlement, queued-event settlement, character seeds, faction pressure, or divine intervention. Do not load all templates for ordinary play.

Use `scripts/set_world_rule.py` when the player explicitly defines, changes, revokes, or locks a world rule. Active rules are mirrored in `CANON.md` and included compactly in interaction packets and dashboard exports. Use `scripts/check_world_rules.py` before executing a material action that may contradict locked facts.

Use `indexes/event-graph.json` to find candidate old events by cause, effect, actor, location, or tag before reading older story. Then use `scripts/read_source_packet.py` for exact excerpts.

## First step each turn

1. Locate the active world:
   - If the user names a world path, use it.
   - Else look for `worlds/*/ACTIVE.md` under the current workspace.
   - If none exists and the user wants to start, create a world brief draft first.
2. Read only:
   - `ACTIVE.md`
   - current branch `SAVE.md`
   - `PLAYER.md`
   - relevant dashboard or entity files for the user’s requested action
3. If `system/file-manifest.json` exists and the player may have edited files directly, run `scripts/detect_manual_edits.py --world <world> --dry-run` before continuing.
4. If manual edits are detected, pause normal play and follow `references/storage-contract.md#manual-edits`.
5. When continuing from a new conversation or a handoff, run `scripts/resume_world.py --world <world> --dry-run` first and use its `first_read` list before expanding any old story sources.

## Main workflows

### Start a world

Use when the player wants a new game, new world, or creation screen.

1. Ask only for missing essential fields: world premise, tone/content boundary, initial region scale, starting god role, and any locked facts.
2. Let the player mark fields as locked, polishable, or AI-fill.
3. Write drafts under `setup/drafts/`; use `scripts/create_world_brief.py` when the player provides fill-in fields. Do not create formal world files until the player confirms.
4. Validate the confirmed draft with `scripts/validate_world_brief.py <draft> --require-confirmed`.
5. After confirmation, run `scripts/init_world.py --world-id <id> --brief <draft> --confirmed` to create the formal world tree, preserve creation fields plus field source map, materialize a deterministic initial semantic map from confirmed geography terms, and write the first `SAVE.md`. If no supported geography is present, mark map generation `pending` instead of silently substituting demo terrain or pseudo-random coordinates.
6. Initialize random seed files, chronicle files, dashboard files, and `system/file-manifest.json`.
7. Initialize `setup/narrative-profile.json` with the hybrid-historical default and mirror its compact summary into `PLAYER.md`.
8. Keep `setup/llm-api.config.json` visible for optional non-Codex model hosting; do not require an API key for Codex-hosted play.
9. For a compact playable sample world, use `scripts/create_demo_world.py --worlds-dir <worlds-dir> --world-id <world-id> --confirmed --json` only when the player asks for a demo/tutorial world.

Use `assets/world-template/` for starter file shapes. Use `references/storage-contract.md` for directory rules.

### Continue play

Use when the player says “继续”, “推进”, “看看现在发生了什么”, or similar.

1. Resolve the active branch from `ACTIVE.md`.
2. Run a light consistency check.
3. Present the current scene from the active branch summary, not from the full history.
4. Apply the active narrative profile: resolve small scenes quickly, but keep material events causal enough to produce visible narration, a compact GM summary, and a settlement plan.
5. Offer concise player actions: observe map, click piece, advance time, intervene, inspect timeline, branch, lock a world rule, or change settings.
6. Treat map clicks as selection/inspection first. When an actual action comes from a frontend button or quick player command, first record it with `scripts/create_action_request.py`; this writes support files only and does not change canon. Use `scripts/update_action_request.py` to mark the request accepted, executed, or cancelled after the player/Codex handles it.
7. Run `scripts/check_world_rules.py` before executing material actions that may touch locked facts; ask the player if the check surfaces a plausible conflict.
8. Use `scripts/assess_divine_action.py` before material divine interventions when mixed-mode cost, scope, or absolute authority matters.
9. Use `scripts/list_action_requests.py --world <world> --pending --json` or dashboard `pending_action_requests` when the player wants to review unresolved actions.
10. If the player cancels a pending action, use `scripts/cancel_action_request.py --world <world> --request-id <id> --confirmed`; do not delete the request folder.
11. If the player reorders pending action priority, use `scripts/reorder_action_requests.py --world <world> --request-id <id> ... --confirmed` to persist the display order.
12. For simple piece movement, use `scripts/move_entity.py --world <world> --entity-id <id> ... --confirmed` after the model or player has determined the destination and reason.
13. For routine offscreen wandering, use `scripts/wander_entities.py --world <world> --confirmed`; player destination overrides must be recorded as overrides.
14. When the player changes how time should usually pass, use `scripts/set_advance_profile.py --world <world> ... --confirmed` to update `setup/advance-profile.json`.

### Inspect map, timeline, or frontend

Use when the player asks to see the map, timeline, dashboard, ignored-character updates, or a local frontend panel.

1. Rebuild derived data only as needed:
   - `scripts/build_map_layers.py --world <world>` for map levels, places, mutable terrain brushes, pieces, and source pointers.
   - `scripts/build_timeline.py --world <world>` for confirmed events, locked rules, queued/due items, ignored digests, and branch nodes.
   - `scripts/export_dashboard.py --world <world>` for current time, weather, attention, random log, rules, action requests, and advance profile.
2. For ignored characters, keep their stories collapsed. Use `scripts/build_ignored_digest.py --world <world> --target-id <id>` only after the player clicks or asks for that ignored target.
3. When the player explicitly asks to ignore or follow a target, use `scripts/set_attention.py --world <world> --target-id <id> --state <ignored|followed|normal> --confirmed`; use `--dry-run` if intent is unclear.
4. To prepare a world-local static frontend, run `scripts/prepare_frontend.py --world <world> --confirmed`; use `--overwrite` only when replacing an existing frontend export is intended. For local app mode, run `scripts/serve_frontend.py --world <world>` and open the printed localhost URL. The local server may refresh frontend data, create/cancel/reorder non-canonical action requests, and run mechanical time advance, but it must not directly settle semantic canon. Frontend actions should use an explicit player-facing commit step: right-side buttons and brush editor commands prepare a visible draft, and only the commit control starts the backend request or mechanical advance.
5. When the player commands a godly terrain change such as moving a river, adding a tributary, raising hills, or growing/removing forest, first record it with `scripts/create_action_request.py --world <world> --action terrain-brush --target-id MAP --target-kind world --payload-json <json> --confirmed`. Generate or preview the geometry as compact `points-json`; after confirmation, execute the suggested `scripts/set_map_brush.py --world <world> --brush-id <id> --kind <river|tributary|hills|forest|custom> --points-json <json> --confirmed`.
6. Treat all frontend JSON as observation data. Frontend buttons create action requests first; they do not directly change canon. The frontend brush editor is a preview and command generator only: it collects map points, emits `points-json`, and routes through the same `terrain-brush` request plus `set_map_brush.py` path as command-style terrain changes.
7. The default frontend may render the map as a three-level interlocking hex projection with AI-generated PNG terrain tiles. Preserve the source 0..100 coordinates and source pointers; hex snapping is display-only unless a future script explicitly migrates the world into native hex coordinates.

### Random or player-overridden outcomes

Use when weather, wandering choice, chance, or a player-forced random result is needed.

1. Use `scripts/resolve_random.py --world <world> --purpose <purpose> --kind <weather|int|choice>` for deterministic branch-seeded random values.
2. When the player overrides a result, pass `--override <value>` so the override is logged instead of hidden in prose.
3. Weather results update dashboard weather and latest random summaries. Rebuilt dashboard data must preserve the latest weather from the active branch random log.

### Interact with a character, object, or place

Use a small interaction packet:

1. Include current time, location, target state, public facts, immediate scene, and allowed source pointers.
2. If the interaction begins as a UI/player intent, run `scripts/create_action_request.py --world <world> --action <observe|speak|intervene> --target-id <id> --target-kind <kind> --confirmed` first. For direct world-rule changes, use action `set-rule` and then execute the suggested `set_world_rule.py` command only if the player confirms the rule.
3. Run `scripts/make_interaction_packet.py --world <world> --target-id <id> --intent <intent>` when a character, object, place, piece, or pin is actually being resolved. It resolves targets by exact state-card `- id:` first, then by a unique filename prefix; it must not use body-text mentions as target matches. If the interaction came from an action request, pass `--request-id <id>` so the packet records and validates that request pointer.
4. Do not load full biography or full story unless the packet requests source expansion. For exact old text, use `scripts/read_source_packet.py --world <world> --source <pointer> --json` or `--from-packet <packet-path>`.
5. Resolve the interaction quickly.
6. Before canonical writes, check model/Codex output with `scripts/validate_settlement_result.py --result <result.json> --kind interaction --json` when the result may be prose-only or comes from an external model.
7. After the interaction, run `scripts/settle_interaction.py --world <world> --packet <packet> --result <result.json> --confirmed` to write mechanical consequences: event node, entity state, chronicle, timeline, dashboard export, and manifest update. The settlement script rejects prose-only results that lack concrete event/state/chronicle/queue/dashboard consequences.

### Use an external model API

Use when the player wants to脱离 Codex or bring a custom large-model API.

1. Read or edit `setup/llm-api.config.json`. It is support configuration, not canon. Prefer `api_key_env` over writing a key into the file.
2. For a packaged one-turn external flow, use `scripts/external_play_turn.py --world <world> --target-id <id> --intent <intent> --confirmed --json` to build/store a support packet and dry-run the external request without contacting the API.
3. Call only when explicitly requested with `scripts/external_play_turn.py --world <world> --packet <packet-id-or-path> --prompt <instruction> --call --confirmed --json`.
4. For low-level control, build the same compact packet you would use in Codex, such as `make_interaction_packet.py` output or a queued-event prompt.
5. Include the compact narrative-profile requirements in the prompt when the model will resolve a meaningful event: causality, continuity, character agency, historical texture, and settlement plan. `external_play_turn.py` and `call_llm.py` inject this profile automatically when a world is supplied.
6. Preview with `scripts/call_llm.py --world <world> --packet <packet-path> --prompt <instruction> --json`; this is dry-run and does not contact the API.
7. Call only when explicitly requested with `scripts/call_llm.py --world <world> --packet <packet-path> --prompt <instruction> --call --json`.
8. Save useful model output as a result JSON file, inspect it, validate it with `scripts/validate_settlement_result.py`, then settle with the normal scripts. Do not let API output directly edit canon files.

### Create a new entity or map piece

Use when a character, location, faction, item, or object must become durable world state.

1. Generate or ask for only high-semantic fields that need language judgment: personality, motive, secret, relationship, culture, or dramatic hook.
2. Put those semantic fields in a small JSON file when needed.
3. Run `scripts/create_entity.py --world <world> --kind <kind> --name <name> --confirmed`.
4. For visible map pieces, provide either `--location <LOC-id>` or direct `--x`/`--y`.
5. For places, use `--kind location`; the script updates branch location state and map coordinate files.
6. Do not load broad history just to create a simple entity. Expand older sources only if the entity depends on an old promise, secret, succession, war, death, or branch inheritance.

### Advance time

Use scripts for mechanical changes and the model for high-semantic events.

1. Support player-selected advance modes: step, fixed duration, condition, event priority, follow character, or regional focus.
2. For long jumps, use chronicle-style summaries.
3. Stop on deaths, disasters, wars, succession, betrayal, required player choices, or world-ending states.
4. When recording known future triggers before time advances, run `scripts/queue_event.py --world <world> ... --confirmed`.
5. When a queued event becomes due, resolve the scene semantically with the model, validate the result with `scripts/validate_settlement_result.py --result <result.json> --kind queued-event --json` if needed, then run `scripts/settle_queued_event.py --world <world> --queue-id <id> --result <result.json> --confirmed`.
6. When the player wants offscreen pieces to keep moving during a non-paused time jump, pass `--wander` to `scripts/advance_world.py`.
7. When the player has a saved advance style, run `scripts/advance_world.py --world <world> --preset <preset-id> --confirmed`; if no `--days` is supplied, the selected or default preset supplies the span and wandering settings.
8. For "advance to the next major event", use an event-priority preset or pass `--until-next-queue`; still settle the due queue item separately.
9. Never prewrite future events as confirmed history.

### Create a context handoff

Use when the conversation is getting long, the player wants to continue in a new task, or the model needs a compact resume point.

1. Run `scripts/check_context_pressure.py --world <world> --json` when context size, event count, or conversation length is concerning.
2. If the result is `suggest-handoff` or `urgent-handoff`, run `scripts/create_handoff.py --world <world> --confirmed`.
3. Hand the player the generated `runtime/context-handoffs/<handoff-id>/HANDOFF.md`.
4. In the next conversation, read the handoff plus its `first_read` files before expanding any source pointers.
5. Treat the handoff as an index and summary, not as a replacement for canonical story, event, state, branch, and random files.

### Branch or change the past

Never overwrite the current branch when the player changes past history.

1. Create a branch draft in current branch `runtime/branch-drafts/`.
2. Show inherited scope, fork event, first change, random seed derivation, and switch behavior.
3. Use `scripts/draft_branch.py --world <world> --branch-id <branch-id> --fork-event <event-id> --change-summary <summary> ... --confirmed` for the draft, then create the child branch only after player confirmation with `scripts/create_branch.py --world <world> --draft-id <id> --confirmed`.
4. Write the child branch’s first event as `divine-revision`.
5. Treat child creation as snapshot inheritance: the child copies the parent branch's current entity/location/attention state, but not parent events, queues, random log, runtime files, checkpoints, or sibling branches.
6. Use `scripts/switch_branch.py --world <world> --branch-path <path> --confirmed` when changing the active branch so derived dashboard, timeline, indexes, event graph, and map files are rebuilt for that branch.
7. Do not scan sibling branches unless the player explicitly requests comparison.

### Manual Markdown edits

Players may edit Markdown directly. Treat this as a controlled import, not immediate canon.

1. Detect changes against `system/file-manifest.json`.
2. Classify low-, medium-, and high-risk changes.
3. Run `scripts/detect_manual_edits.py --world <world>` to write a report and merge plan under current branch `runtime/manual-edit-reports/<report_id>/`.
4. Ask the player to accept, reject, or branch blocked changes.
5. Use `scripts/apply_manual_edits.py --world <world> --report-id <id> --accept <path> --confirmation <text> --confirmed` only for explicitly accepted paths.
6. Rejected paths are recorded but not restored by default. Add `--restore-rejected` only when the player explicitly wants rejected paths restored from checkpoint `core-snapshot/`.
7. Accepted factual changes must create `manual-correction` or `divine-revision` events when they alter canon, not merely summaries.

### Content boundary changes

Use when the player changes content intensity, topic limits, absolute bans, or asks to soften only the current paragraph.

1. Run `scripts/set_content_profile.py --world <world> ... --confirmed` for persistent preference changes.
2. For one-off softening, include `--soften-target <scene-or-event-id>` to create a support request under `runtime/soften-requests/`.
3. Never use softening to change canon facts, event outcomes, deaths, damage, random logs, queues, or chronicle entries.

## Reference routing

Read only the relevant reference:

- `references/storage-contract.md`: world files, branches, manifests, manual edits, save structure.
- `references/game-master-protocol.md`: narration, context budget, interaction packets, time advance, random events.
- `references/frontend-contract.md`: map, pieces, timeline, dashboard, player input flow.
- `references/narrative-quality.md`: hybrid-historical narrative profile, event pressure chain, output layers, and settlement quality rules.
- `references/narrative-template-guide.md`: small optional templates for settlement results, character seeds, faction pressure, and divine intervention.
- `references/script-catalog.md`: planned scripts and deterministic responsibilities.
- `references/validation-scenarios.md`: acceptance scenarios for core game, frontend, persistence, and install behavior.
- `references/player-quickstart.md`: player-facing start, continue, frontend, install, handoff, and external API usage.

## Validation and install

Run `scripts/validate_world.py --world <world> --json` for world checks. Run `scripts/check_install_ready.py --skill-dir <skill-dir> --run-smoke --json` before installing or updating the skill package. To install this project-local skill, preview with `scripts/install_local_skill.py --skill-dir <skill-dir> --dry-run --json`; copy only with explicit `--confirmed`.

## Safety boundaries

Honor the player’s content profile, but do not override Codex or platform safety requirements. If a requested scene must be softened, keep facts intact and change presentation only.

Do not use hidden background execution after the Codex task ends. Automation can run only during an active Codex task unless the user explicitly sets up a supported recurring automation.
