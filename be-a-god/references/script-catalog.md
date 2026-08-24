# Script Catalog

Use scripts for mechanical work. Keep semantic invention in the model.

## MVP scripts

- `init_world.py`: create formal world files from confirmed setup drafts, preserving creation fields, content bans, the field source map, and the default hybrid-historical narrative profile in `world-spec.json`, `content-profile.json`, `narrative-profile.json`, `WORLD.md`, `PLAYER.md`, and the initial `SAVE.md`.
- `create_demo_world.py`: create a compact playable demo/tutorial world with real locations, visible character pieces, terrain brushes, a queued pressure event, a pending action request, frontend export, and validation.
- `create_world_brief.py`: create editable WORLD-BRIEF drafts from player fill-in fields, including content bans and a field source map for locked, polishable, and AI-fill fields.
- `create_map_plan.py`: deterministically convert confirmed brief geography into a reviewable MAP-PLAN draft with cardinal terrain zones, directional features, stable settlement coordinates, and explicit unresolved claims; it makes no model/API call.
- `validate_world_brief.py`: validate creation drafts before initialization, rejecting confirmed drafts that miss required creation fields or the field source map.
- `create_entity.py`: create branch-local entity/location cards from player/model-provided fields, reject unsafe `entity_id`/slug filename parts, then refresh indexes, map layers, pieces, and manifest.
- `move_entity.py`: update a visible entity's location, coordinates, level, or status using exact `- id:` or a unique filename-prefix match, then refresh indexes, map pieces, and manifest.
- `wander_entities.py`: apply branch-seeded or player-overridden wandering moves for visible entities, log wander random entries, and refresh map pieces.
- `draft_branch.py`: write a non-canonical branch draft under the active branch before creating a child branch.
- `create_branch.py`: create a child branch after player confirmation, copy the active parent branch state snapshot into the child, and keep parent events/queues/random/runtime files separate.
- `resolve_branch_view.py`: resolve current branch plus parent pointers without scanning siblings.
- `switch_branch.py`: update `ACTIVE.md` after confirmation, then rebuild active-branch dashboard, timeline, indexes, event graph, map layers, and manifest unless `--skip-derived` is supplied.
- `resolve_random.py`: produce branch-isolated random outputs and append logs.
- `assess_divine_action.py`: preview mixed-mode divine action cost and absolute-authority status without changing canon.
- `set_world_rule.py`: record player-confirmed world rules or locked facts in `setup/world-rules.json` and `CANON.md`.
- `check_world_rules.py`: prepare a compact non-canonical rule-conflict check packet before executing material actions.
- `queue_event.py`: append future event or pause triggers to the active branch event queue; writing requires `--confirmed`, while `--dry-run` previews the queue item.
- `set_advance_profile.py`: create or update player advance presets in `setup/advance-profile.json`, mirror compact default-preset summaries into `PLAYER.md`, and avoid changing canon.
- `advance_world.py`: advance time in slices, apply advance presets, optionally resolve to the next queued pause event, stop on queued pause conditions, and optionally run a non-paused wandering tick.
- `settle_queued_event.py`: validate queued-event settlement results, reject prose-only output, then convert a due queued event into confirmed event, chronicle, save, dashboard, queue, ledger, and manifest updates.
- `check_context_pressure.py`: estimate whether the current branch should create a context handoff before continuing.
- `create_handoff.py`: create branch-local context handoffs for continuing play in a new Codex conversation.
- `resume_world.py`: prepare a compact resume packet for continuing a world in a new Codex conversation without loading broad history.
- `build_map_layers.py`: create semantic map layers and coordinates.
- `scripts/set_map_brush.py`: create, update, or remove mutable terrain brush particles such as rivers, tributaries, hills, and forests after player confirmation, then refresh map layers and manifest.
- `update_map_state.py`: update character piece positions and statuses.
- `build_event_graph.py`: rebuild `indexes/event-graph.json` from active-branch event metadata for cause/effect, actor, location, tag, and source-pointer lookup.
- `set_attention.py`: set followed, normal, or ignored character state; writing requires `--confirmed`, while `--dry-run` previews the change.
- `build_ignored_digest.py`: summarize ignored-character event skeletons on demand by event metadata (`actors` or legacy `target_id`), not body-text mentions; optional output must stay inside the world directory, refuses overwrite by default, and refreshes the manifest.
- `set_content_profile.py`: update content-boundary preferences, mirror compact preset/topic/absolute-ban summaries into `PLAYER.md`, and create presentation-only soften requests.
- `create_action_request.py`: record frontend/player god actions as non-canonical support requests before execution or settlement, including advance preset requests, `set-rule` requests that point to `set_world_rule.py`, `terrain-brush` requests that point to `set_map_brush.py`, and confirmed attention updates for ignore/follow requests.
- `cancel_action_request.py`: mark a pending action request as cancelled without deleting its JSON/Markdown audit files; cancelled requests disappear from pending dashboard export.
- `reorder_action_requests.py`: persist a player-defined pending action priority order under active-branch runtime files so dashboard export can show dragged requests first.
- `update_action_request.py`: mark action requests accepted, executed, or cancelled without running the suggested command.
- `list_action_requests.py`: list pending or filtered action requests from the active branch for player review and dashboard export.
- `make_interaction_packet.py`: prepare minimal context for close-up interaction, include compact narrative-profile requirements, resolve targets by exact `- id:` or unique filename prefix without body-text matching, reject outside `--target-file`, optionally attach a validated action request, then refresh the file manifest when writing a packet.
- `read_source_packet.py`: read short excerpts from explicit source pointers only, constrained to root allowlist and active branch ancestry.
- `settle_interaction.py`: validate interaction settlement results, reject prose-only output, and write results back to canonical and derived files; packet IDs resolve inside the current `ACTIVE.md` branch, while explicit packet paths must remain inside the world directory.
- `validate_settlement_result.py`: check model/Codex settlement result JSON before canon writes, requiring visible narration or summary, GM summary, and a concrete settlement plan or legacy concrete event/state/chronicle/consequence fields.
- `call_llm.py`: preview or call a user-configured OpenAI-compatible model API from `setup/llm-api.config.json`; it injects compact narrative-profile requirements, supplies compact packets to an external model, and does not directly write canon files.
- `external_play_turn.py`: package one external-model play turn by creating or loading a compact interaction packet, dry-running or calling `call_llm.py`, storing support-only run artifacts, extracting candidate settlement JSON, validating it, and suggesting settlement commands without directly changing canon.
- `update_chronicle.py`: update objective chronicle from confirmed events.
- `render_chronicle_style.py`: rebuild epic chronicle display text from objective chronicle.
- `build_timeline.py`: export current branch timeline with confirmed events, active locked rules, queued/due future items, ignored-character collapsed summaries based on event metadata rather than body-text mentions, and child branch entry points.
- `checkpoint.py`: archive current branch save before risky writes.
- `build_file_manifest.py`: record hashes and authority classes for files; custom manifest output must stay inside the world directory.
- `detect_manual_edits.py`: detect player edits and create report plus merge plan.
- `apply_manual_edits.py`: apply accepted manual edits after confirmation.
- `build_indexes.py`: rebuild entity, location, and event indexes.
- `validate_world.py`: check links, branch pointers, branch drafts, story tree entries, state card IDs/filenames, queues, random logs, handoffs, action-request suggested command routing, frontend/dashboard/timeline/map-layer JSON structure, manifest references, narrative profile structure, `PLAYER.md` compact preference summaries, and missing files.
- `export_dashboard.py`: export frontend-ready data, preserving latest weather and latest_random from the active branch random log.
- `prepare_frontend.py`: copy the static frontend template plus exported dashboard/timeline/map-layer JSON into a world-local frontend folder, reject outside-world output paths, and generate a README that explains the read-only canon boundary.
- `serve_frontend.py`: serve the frontend on localhost with compact `/api/state`, `/api/action-request`, `/api/advance-world`, `/api/action-request/cancel`, and `/api/action-requests/reorder` endpoints; it may refresh derived frontend data, create/cancel/reorder non-canonical action requests, and run mechanical time advance but must not directly settle semantic canon.
- `smoke_test.py`: run a temporary end-to-end validation of the core script chain.
- `check_install_ready.py`: run read-only install readiness checks before copying the skill to Codex's global skill directory, including UI metadata capability freshness, required direct-workflow command fragments, validation-scenario coverage, frontend sample schema/route markers, path-backed ID safety markers, and escaped JSON preview markers.

Path-backed or file-adjacent IDs must be path-safe: letters, numbers, underscores, and hyphens only. Covered IDs include request, packet, branch draft, handoff, resume, rule-check, divine-assessment, soften-request, manual-edit report, checkpoint, and terrain brush IDs.
- `install_local_skill.py`: validate and copy the project-local skill into Codex's global skills directory only after explicit confirmation.

## Initial implemented utilities

The current skeleton includes:

- `scripts/init_world.py`
- `scripts/create_demo_world.py`
- `scripts/create_world_brief.py`
- `scripts/create_map_plan.py`
- `scripts/validate_world_brief.py`
- `scripts/create_entity.py`
- `scripts/move_entity.py`
- `scripts/wander_entities.py`
- `scripts/draft_branch.py`
- `scripts/build_file_manifest.py`
- `scripts/make_interaction_packet.py`
- `scripts/read_source_packet.py`
- `scripts/settle_interaction.py`
- `scripts/validate_settlement_result.py`
- `scripts/call_llm.py`
- `scripts/external_play_turn.py`
- `scripts/update_chronicle.py`
- `scripts/build_timeline.py`
- `scripts/export_dashboard.py`
- `scripts/build_indexes.py`
- `scripts/validate_world.py`
- `scripts/prepare_frontend.py`
- `scripts/checkpoint.py`
- `scripts/create_branch.py`
- `scripts/switch_branch.py`
- `scripts/resolve_branch_view.py`
- `scripts/resolve_random.py`
- `scripts/assess_divine_action.py`
- `scripts/set_world_rule.py`
- `scripts/check_world_rules.py`
- `scripts/queue_event.py`
- `scripts/set_advance_profile.py`
- `scripts/advance_world.py`
- `scripts/settle_queued_event.py`
- `scripts/check_context_pressure.py`
- `scripts/create_handoff.py`
- `scripts/resume_world.py`
- `scripts/build_map_layers.py`
- `scripts/update_map_state.py`
- `scripts/build_event_graph.py`
- `scripts/set_attention.py`
- `scripts/build_ignored_digest.py`
- `scripts/set_content_profile.py`
- `scripts/create_action_request.py`
- `scripts/cancel_action_request.py`
- `scripts/reorder_action_requests.py`
- `scripts/update_action_request.py`
- `scripts/list_action_requests.py`
- `scripts/render_chronicle_style.py`
- `scripts/detect_manual_edits.py`
- `scripts/apply_manual_edits.py`
- `scripts/validate_world_structure.py`
- `scripts/serve_frontend.py`
- `scripts/smoke_test.py`
- `scripts/check_install_ready.py`
- `scripts/install_local_skill.py`

The MVP script set is implemented. Add later scripts only when new mechanics require stable file formats.
