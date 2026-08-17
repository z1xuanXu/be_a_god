# Storage Contract

## Authority

Use Markdown for player-readable narrative and JSON/JSONL for deterministic machine state. Treat event nodes, entity cards, random logs, branch pointers, and player-confirmed setup as canonical. Treat indexes, dashboards, timelines, `CURRENT.md`, and styled chronicle text as rebuildable derivatives unless explicitly promoted by the player.

## World tree

```text
worlds/<world-id>/
├─ setup/
│  ├─ WORLD-BRIEF.md
│  ├─ world-spec.json
│  ├─ content-profile.json
│  ├─ advance-profile.json
│  ├─ narrative-profile.json
│  └─ drafts/
├─ WORLD.md
├─ ACTIVE.md
├─ CANON.md
├─ PLAYER.md
├─ story/
│  ├─ STORY-TREE.md
│  └─ main/
│     ├─ SAVE.md
│     ├─ CURRENT.md
│     ├─ chapters/
│     ├─ events/
│     ├─ state/
│     ├─ chronicle/
│     ├─ queues/
│     ├─ random/
│     ├─ runtime/
│     │  ├─ action-requests/
│     │  ├─ context-handoffs/
│     │  ├─ divine-assessments/
│     │  ├─ resume-packets/
│     │  ├─ rule-checks/
│     │  ├─ soften-requests/
│     ├─ checkpoints/
│     └─ branches/
├─ base/
├─ indexes/
├─ dashboard/
└─ system/
   ├─ turn-ledger.jsonl
   ├─ file-manifest.json
   ├─ manual-edit-ledger.jsonl
   └─ validation-report.md
```

## Save files

`setup/world-spec.json` stores the confirmed creation fields and `creation_field_sources` extracted from `setup/WORLD-BRIEF.md`. Use it for quick checks of player-locked, polishable, player-setting, player-note, and AI-fill boundaries without rereading the full brief.

Each branch owns its own `SAVE.md`. Include world ID, branch ID, parent branch ID, parent save pointer, fork event, inherited boundary, current time, focal place, player status, unresolved choices, and compact source pointers.

Do not resolve sibling branches during normal play. Resolve only the current branch and its parent chain as needed.

Use `scripts/read_source_packet.py` for exact old source text. It may read only explicit relative pointers, root allowlisted files, and files under the active branch ancestry. It must not perform broad discovery or scan sibling branches.

When switching active branches, use `scripts/switch_branch.py`. It updates `ACTIVE.md` and rebuilds the active-branch derived files by default, including dashboard, timeline, indexes, event graph, map layers, and manifest. Use `--skip-derived` only for dry diagnostics where stale derived files are acceptable.

`build_timeline.py` exports a lightweight current-branch timeline. It should include confirmed event nodes from `events/`, active locked world rules from `setup/world-rules.json`, queued or due future items from `queues/events.jsonl`, ignored-character collapsed summaries from `state/attention.json`, and child branch entry points under the active branch `branches/`. Timeline nodes are display/index pointers; they do not replace canonical event, rule, queue, attention, or branch files.

## Event graph index

Use `indexes/event-graph.json` as a rebuildable derived index over active-branch event nodes. It stores event nodes, cause/effect links, and reverse lookups by actor, location, and tag. It is not a source of truth; exact facts still come from event Markdown files and their source pointers.

Use `scripts/build_event_graph.py --world <world>` to rebuild it directly, or `scripts/build_indexes.py --world <world>` to rebuild it with the other indexes. Event Markdown may include compact metadata lines:

- `actors: [CHAR-0001, FACTION-001]`
- `location: LOC-001`
- `causes: [EVT-0001]`
- `effects: [QUEUE-0001, REL-001]`
- `tags: [flood, oath, succession]`

When reading old context, prefer this index to find candidate event IDs, then use `scripts/read_source_packet.py` for exact source excerpts.

## Context handoffs

When the active Codex conversation grows too long or the player wants to continue elsewhere, create a branch-local handoff under `runtime/context-handoffs/<handoff_id>/`.

Each handoff must contain:

- `HANDOFF.md`: player-readable resume file;
- `存档.md`: player-readable Chinese alias containing the same resume content as `HANDOFF.md`;
- `handoff.json`: machine-readable equivalent;
- active world path, branch path, save path, current state, branch inheritance, open items, recent chronicle entries, recent event nodes, random log position, dashboard pointers, and explicit first-read files.

Handoffs are support files. They do not replace `SAVE.md`, event nodes, entity cards, random logs, or branch pointers. They may summarize recent state, but source pointers must remain available for exact recall.

After writing a handoff, refresh `system/file-manifest.json` unless the caller explicitly skips manifest update for a dry diagnostic flow.

Use `scripts/check_context_pressure.py --world <world> --json` to estimate whether the current branch should create a handoff. The check reports minimum resume-context size, core-history size, event count, chronicle entries, random-log entries, latest handoff, and a recommended status: `keep-going`, `suggest-handoff`, or `urgent-handoff`.

At the start of a new conversation or after loading a handoff, first run `scripts/resume_world.py --world <world> --dry-run` to get the minimal startup `first_read` list without writing files. If the player or host wants a durable resume packet, run `scripts/resume_world.py --world <world> --confirmed`; it creates `runtime/resume-packets/<resume_id>/resume.json` and `resume.md` with active save fields, latest handoff pointer, compact player preferences, active rules, dashboard counts, and an explicit first-read list. Resume packets are support files and have `context_policy.canonical_effect: none`.

## Content profile

Store player content-boundary preferences in `setup/content-profile.json`. During initialization, parse `Content boundary` from `setup/WORLD-BRIEF.md` when no separate content-profile draft is supplied, including player absolute bans. Sync a compact summary into `PLAYER.md` so close-up interaction packets do not need to read the full profile every time.

One-off softening requests live under the active branch `runtime/soften-requests/`. These requests are support files. They can change how a paragraph or scene is presented, but they must not alter event nodes, state changes, random logs, queue results, chronicle entries, deaths, damage, or other canon facts.

## World rules

Store player-confirmed world rules and locked facts in `setup/world-rules.json`, with a readable active-rule summary mirrored into `CANON.md`.

Use `scripts/set_world_rule.py --world <world> --text <rule> --confirmed` to create or update rules. Rules include `rule_id`, `text`, `scope`, optional `target`, `effective_time`, `status`, `replaces`, and `tags`. Changing a rule is canon configuration, but it does not by itself narrate or settle downstream events; material consequences still need normal event settlement.

Interaction packets and derived dashboard exports include a compact `world_rules.active` summary and pointers to `setup/world-rules.json` and `CANON.md`, so the host can obey locked facts without loading broad history.

Before executing a material action that may contradict locked facts, create a non-canonical rule check under the active branch with `scripts/check_world_rules.py --world <world> --request-id <id> --confirmed`. Rule checks live in `runtime/rule-checks/<check_id>/` and contain only the action summary, relevant active rules, source pointers, and a decision field. They do not change canon.

## Advance profile

Store player time-advance preferences in `setup/advance-profile.json`. This file is support configuration, not story canon. It defines named presets such as step, hybrid, chronicle, or event-priority advancement.

Use `scripts/set_advance_profile.py` to create or update presets. Presets may define default days, summary, wandering behavior, ignored-character inclusion, and whether queued pause events stop the advance. Changing this file must not directly write event nodes, state cards, random logs, chronicle entries, timeline nodes, or `SAVE.md`.

Use `scripts/advance_world.py --preset <preset-id>` to apply a preset. If `--days` is omitted, `advance_world.py` uses the selected preset or the profile default preset. One-off command-line flags override preset fields for that run, and the run record stores the selected preset plus override flags under `advance_profile`.

For event-priority play, set a preset with `until_next_queue: true` or pass `advance_world.py --until-next-queue`. The script resolves the requested span to the next queued pause/high-priority item in the active branch, if one exists within the span. It still does not settle that item as history; settlement remains a separate player/model-confirmed step.

## Narrative profile

Store narration-quality preferences in `setup/narrative-profile.json`, copied from `assets/world-template/narrative-profile.template.json` during initialization. This file is support configuration, not story canon. It controls how the model should resolve scenes and events, but changing it must not directly write event nodes, state cards, random logs, chronicle entries, queues, terrain brushes, or `SAVE.md`.

The default profile is `hybrid-historical`: close-up scenes plus long-run chronicle, with causality, world continuity, character agency, and historical texture prioritized before dramatic presentation.

Sync a compact narrative summary into `PLAYER.md` so close-up interactions and external-model prompts can obey the profile without reading the full JSON every turn. Dashboard export may include the same compact summary as `narrative_profile`.

Interaction packets should include a compact `narrative_profile` object and an allowed source pointer to `setup/narrative-profile.json`. External-model prompts built by `call_llm.py` should inject the same compact profile before the supplied packet or player prompt.

When generated text creates durable consequences, store the consequences through normal settlement files and scripts. A vivid passage without a `settlement_plan` is presentation only and must not be treated as canon until a concrete event/state/chronicle/queue/map consequence exists.

## Host and LLM API config

Codex-hosted play and external-model play must use the same world tree, action requests, interaction packets, result JSON files, and settlement scripts. The host changes only where semantic text is generated.

Store optional external model settings in `setup/llm-api.config.json`, copied from `assets/world-template/llm-api.config.template.json` during initialization. This file is support configuration, not canon. It may contain `base_url`, `endpoint_path`, `api_key_env`, `model`, `temperature`, `max_tokens`, `timeout_seconds`, extra headers, and a compact system prompt.

Do not require this file to be enabled for Codex play. For external play, prefer environment variables for secrets and use `scripts/call_llm.py` to preview or call an OpenAI-compatible chat-completions endpoint. API output must not directly edit canon files; save useful output as a result file, inspect it, then apply it through `settle_interaction.py`, `settle_queued_event.py`, or another confirmed deterministic script.

## Action requests

Player commands should first write support requests under the active branch `runtime/action-requests/<request_id>/`.

Each request must contain:

- `request.json`: machine-readable action, target, intent, suggested next command, active branch pointer, world time, and context policy;
- `request.md`: player-readable equivalent;
- `context_policy.canonical_effect: none`.

Creating an action request must not change event nodes, entity/location state, random logs, queues, chronicle entries, dashboard data, map layers, or timeline data. It may refresh `system/file-manifest.json` because the request itself is a support file.

Use `scripts/create_action_request.py` for observe, speak, intervene, advance-time, weather-override, set-rule, ignore, follow, branch, terrain-brush, and custom requests. After review, execute the suggested script if the player confirms the actual effect.

Use `scripts/update_action_request.py` to mark a request `accepted`, `executed`, or `cancelled`. This lifecycle update remains non-canonical; any real world effect must be visible through the linked interaction packet, random log, queue settlement, event node, or other result pointer.

Use `scripts/list_action_requests.py --pending --json` or `dashboard.pending_action_requests` to show the player unresolved requests without reading story history. The exported dashboard should include only request summaries and source pointers.

## Divine assessments

Mixed-mode god play should preview ordinary intervention cost before a material divine action. Use `scripts/assess_divine_action.py --dry-run` while the player is considering the move. Store a preview under the active branch `runtime/divine-assessments/<assessment_id>/` only after the player or host confirms the support packet with `--confirmed`.

Each assessment must contain:

- `assessment.json`: action, target, scale, irreversibility, visibility, score, normal limit, action request pointer, and status;
- `assessment.md`: player-readable equivalent;
- `canonical_effect: none`.

Use `scripts/assess_divine_action.py` before material interventions when cost, scope, or absolute authority matters. The assessment does not execute the action and has no canonical effect. If the player declares absolute divine authority, record `status: absolute-authorized` in the assessment and continue with the actual action/settlement script.

## Entity and location cards

Branch-local moving entities live under `story/<branch>/state/entities/*.md`. Branch-local locations live under `story/<branch>/state/locations/*.md`. Entity and location cards are canonical state files; `indexes/entities.json`, `indexes/locations.json`, dashboard pieces, and map layers are rebuildable derivatives.

Use `scripts/create_entity.py` for new cards when possible. The script handles IDs, filenames, card fields, optional map coordinates for locations, derived indexes, map layers, visible pieces, and manifest refresh. It does not invent semantic content; personality, motives, secrets, and faction meaning should come from the player or model and be passed as stored fields.

Characters, items, factions, or objects stored in `state/entities/` are canonical moving/entity state. Give map-relevant entities either direct `x`/`y` fields or a `location` resolving through `base/maps/coordinates.json` so derived map data remains accurate.

Initial terrain brush geometry lives in `base/maps/terrain-brushes.json`. Branch-local terrain changes live in `story/<branch>/state/terrain-brushes.json` as overrides, additions, or tombstones. `build_map_layers.py` merges base and active-branch brush state into `dashboard/map-layers.json` for script and host inspection. Command-style terrain edits first create a non-canonical `terrain-brush` action request, then run `scripts/set_map_brush.py` after geometry or removal is confirmed.

Use `scripts/move_entity.py` for mechanical movement. It updates only the active branch entity card and rebuildable derivatives; it does not decide narrative motive or create a confirmed event by itself.

Use `scripts/wander_entities.py` for routine wandering ticks. It writes entity location/status fields, appends a `kind: wander` random log entry for each moved entity, and rebuilds map pieces. It does not create event nodes or chronicle entries unless the model later promotes a movement into a meaningful event.

`export_dashboard.py` exports attention counts and compact followed, ignored, and plot-ready lists so the host can inspect attention state without scanning every entity card.

`advance_world.py --wander` may call the wandering tick after a successful non-paused time advance. If the advance stops on a queued pause, wandering is skipped until the pause is resolved.

## Branches

Create branches through drafts:

1. Run `scripts/draft_branch.py --world <world> --branch-id <branch-id> --fork-event <event-id> --change-summary <summary> ... --confirmed` to write `runtime/branch-drafts/<draft_id>/draft.md` and `draft.json`.
2. Show the fork event, inheritance boundary, first change, and random seed derivation.
3. Create the branch only after player confirmation, preferably with `scripts/create_branch.py --world <world> --draft-id <draft_id> --confirmed`.
4. The consumed draft must be marked `status: consumed` with `created_branch_path`.
5. Write the first child event as `divine-revision`.

Child branch creation uses snapshot inheritance. Copy the active parent branch's current `state/entities/`, `state/locations/`, and direct `state/*` files into the child branch at fork time. Do not copy parent `events/`, `chronicle/`, `queues/`, `random/random-log.jsonl`, `runtime/`, `checkpoints/`, or nested `branches/`. After the fork, parent and child state files are write-separated; child interactions must not mutate parent cards.

Branch IDs are slug-normalized and must not normalize to an empty value. If a proposed ID contains no usable letter, number, underscore, or hyphen, ask the player for a clearer ID instead of silently creating `branch`.

Path-backed IDs that become directory or file names must contain only letters, numbers, underscores, and hyphens. This includes action request IDs, interaction packet IDs, branch draft IDs, handoff IDs, resume packet IDs, rule-check IDs, divine-assessment IDs, soften-request IDs, manual-edit report IDs, and checkpoint IDs. Do not accept `../`, slashes, spaces, or other path characters for these fields.

`ACTIVE.md` pointers are authoritative but still bounded. `branch_path` and `save_path` must be relative world-local paths, and `save_path` must resolve to the active branch `SAVE.md`. Validation must reject absolute paths, `../` escapes, or mismatched save pointers before other branch checks run.

`system/file-manifest.json` paths are also bounded. Manifest entries must be relative world-local paths before their existence, hash, or authority can be trusted. Validation must reject absolute paths and `../` escapes.

## Random logs

Random output must be reproducible per branch. Store a branch seed and append each call to `random/random-log.jsonl`. User overrides are allowed, but record them as overrides rather than silently replacing previous random outcomes.

Weather random results and player weather overrides should update `dashboard/data.json` so derived world summaries remain current. `export_dashboard.py` rebuilds a compact `random_log` summary from the active branch `random/random-log.jsonl`, including only recent entries and the source pointer. Refresh `system/file-manifest.json` after random writes unless running a dry diagnostic flow.

## Event queues

Store future triggers in the active branch `queues/events.jsonl`. Queue items should include queue ID, trigger time, priority, kind, title, targets, pause flag, and status.

`advance_world.py` may mark a queued item as `due` when it stops on that item. It must not convert the queued item into confirmed history by itself; the model and player-confirmed settlement still create the actual event node.

`settle_queued_event.py` is the canonical bridge from queue to history. It may settle only a `due` queue item by default, unless the caller explicitly passes `--allow-not-due` after player confirmation. Settlement must write an event node, append the objective chronicle, update `SAVE.md` and `CURRENT.md`, mark the queue item `settled`, remove matching dashboard unresolved choices, append `system/turn-ledger.jsonl`, and refresh the manifest.

## Manual edits

Before continuing play, compare current files to `system/file-manifest.json`. If differences exist:

1. Write `runtime/manual-edit-reports/<report_id>/report.md`.
2. Write `runtime/manual-edit-reports/<report_id>/merge-plan.json`.
3. Classify changes:
   - Low risk: spelling, prose polish, display-only chronicle text.
   - Medium risk: entity state, relationships, location facts, `SAVE.md`, objective chronicle.
   - High risk: event IDs, parent pointers, fork events, random logs, deaths, resurrection, locked canon.
4. Ask the player to accept, reject, branch, or explain conflicts.
5. Create a checkpoint before applying accepted changes.
6. Accepted factual changes must create `manual-correction` or `divine-revision` events.
7. Rebuild indexes, timeline, dashboard, validation report, and file manifest.

Current implementation detail: `apply_manual_edits.py` updates the manifest only for explicitly accepted paths. Rejected paths are logged but not restored by default. When the player explicitly requests restoration, run it with `--restore-rejected`; the script restores rejected paths from checkpoint `core-snapshot/` only when a snapshot with the manifest-matching hash exists. If no matching snapshot exists, it fails rather than guessing.
