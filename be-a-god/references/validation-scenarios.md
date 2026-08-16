# Validation Scenarios

Use these scenarios to test the skill before calling it playable.

## 1. Creation to formal world

Player provides a partly locked world brief. The system must draft first, distinguish player facts from AI fill, require confirmation, then create formal world files.

Failure: draft becomes canon before confirmation.

## 2. Close-up interaction

Player clicks a character and gives a simple command. The system must use a minimal packet, avoid full-history reads, resolve quickly, then settle consequences.

Failure: whole biography or full story tree is loaded before a simple interaction.

## 3. Cross-year advancement

Player advances a year. The system must advance in slices, update objective chronicle, stop on major events, and avoid prewriting unconfirmed future.

Failure: skipped deaths, missing pause package, or future events written as confirmed history.

## 4. Change the past

Player prevents a past death. The system must create a branch draft, confirm with the player, then create a child branch with a `divine-revision` event.

Failure: current branch overwritten or sibling branches contaminated.

## 5. Manual Markdown edit

Player changes a character identity and accidentally changes an event ID. The system must detect manual edits, classify risks, generate report and merge plan, accept only confirmed changes, and block unsafe structural changes.

Failure: manual edits silently become canon.

## 6. Lock a world rule

Player declares a durable world rule. The system must record it through `set_world_rule.py`, mirror active rules to `CANON.md`, include compact rules in interaction packets and dashboard data, and avoid broad history reads.

Failure: the rule exists only in conversation memory or is silently ignored by later interactions.

## 7. Rule conflict before material action

Player requests an intervention that may contradict locked facts. The system must create a compact `check_world_rules.py` packet, review only relevant active rules, and ask for override, revision, or branching if a conflict is plausible.

Failure: the action is executed while contradicting an active player-confirmed rule.

## 8. New conversation resume

Player continues from a new Codex conversation after a handoff. The system must use `resume_world.py` or the latest resume packet, follow its `first_read` list, and avoid loading full chapters or sibling branches during startup.

Failure: resume depends on hidden chat memory or reads broad history before establishing the active branch.

## 9. Frontend permanent panels

The frontend loads exported dashboard, timeline, and map-layer JSON. It must show current time/weather/branch, active rules, recent random records, attention summary, pending action requests, visible pieces, branch action entry, and a vertical timeline without committing world changes.

Failure: the frontend mutates canon directly, lacks a branch action entry, or requires full Markdown story files to render the normal dashboard.

## 10. Install preview

Player asks whether the skill can be installed. The system must run install readiness checks and `install_local_skill.py --dry-run` first, refuse overwrites, and install only after explicit confirmation.

Failure: global skill files are copied or overwritten during a preview/check.

## 11. Creation fields survive initialization

Player confirms a world brief with a named god role, starting region, and field source map. The system must preserve those fields in `setup/world-spec.json`, `WORLD.md`, `PLAYER.md`, and the first branch `SAVE.md`.

Failure: formal world files revert to placeholders such as unnamed god, unspecified starting place, or lose player-locked / AI-fill source labels.

## 12. Dashboard rebuild preserves weather

Player overrides weather through a random result. Later dashboard rebuilds triggered by attention changes, map changes, or frontend preparation must recover the latest weather from the active branch random log.

Failure: `export_dashboard.py` resets weather to `None` or drops `latest_random`.

## 13. Frontend export is self-describing and read-only

Player prepares the local frontend folder. The output must stay inside the world directory and include `index.html`, frontend assets, live JSON files, and a `README.md` explaining the open path, JSON meanings, sample fallback files, and read-only canon boundary.

Failure: the prepared frontend writes outside the world directory, lacks a local explanation, or implies that UI actions directly mutate canon.

## 14. Ignored digest output is safe

Player asks to inspect an ignored character. The timeline collapsed node and optional digest may be shown from world-local state. Written digest output must stay inside the world directory, refuse overwrite by default, keep ignore state unchanged, refresh the file manifest, and include only events whose metadata names the target in `actors` or legacy `target_id`.

Failure: ignored timeline/digest cancels ignore state, overwrites an existing file silently, writes outside the world directory, or includes an event merely because the body text mentions the ignored character ID.

## 15. Direct workflow routing

A fresh Codex instance reads only `SKILL.md` after the skill triggers. It must still be able to route player-facing map, timeline, dashboard, frontend, entity creation, piece movement, wandering, ignored digest, random outcome, and manual-edit detection requests to their deterministic scripts.

Failure: a direct player workflow script exists only in `script-catalog.md`, so normal play misses it unless the model happens to inspect the full catalog.

Entity/card creation failure: player-provided IDs or slugs can escape the active branch state folder or create unsafe filenames.

## 16. Compact player preference summaries

Player changes content boundaries or default time-advance behavior. The system must update `setup/content-profile.json` or `setup/advance-profile.json` and keep the compact summaries in `PLAYER.md` synchronized.

Failure: close-up interaction packets must read full setup JSON files because `PLAYER.md` has stale or missing content/advance summaries.

## 17. Confirmed player-state operations

Player asks to ignore/follow a character or switch active branches. The system must support dry-run preview and require explicit `--confirmed` for writes to attention state or `ACTIVE.md`.

Failure: a frontend click, stale suggested command, or accidental script call silently changes ignored/followed state or switches the active branch.

## 18. Advance preset routing

Player uses a saved advance mode from the dashboard. The direct frontend backend path must call `advance_world.py --preset <preset-id> --confirmed`, refresh dashboard state, and preserve the existing action-request route for manual/Codex-driven advance requests.

Failure: the UI shows a preset but the generated command falls back to a one-day/default advance.

## 19. Future event queue confirmation

Player or Codex records a known future trigger before advancing time. The system must preview uncertain queue items with `queue_event.py --dry-run` and require `queue_event.py --confirmed` before writing to the active branch queue.

Failure: a vague future trigger or accidental script call silently appends a queue item that later stops world time.

## 20. Branch action request routing

Player selects an event or piece and asks to create an alternate branch. The frontend/action-request path must route to `create_action_request.py --action branch`, and the resulting request must suggest `draft_branch.py --branch-id <branch-id> --fork-event <event-id> ... --confirmed` rather than directly rewriting history.

Failure: a branch button only changes UI state, creates no action request, or suggests direct parent-branch history edits.

## 21. Interaction target resolution

Player clicks `CHAR-0001` while another state card only mentions `CHAR-0001` in its summary. The interaction packet must select the exact `- id: CHAR-0001` card, reject ambiguous filename prefixes, and reject explicit `--target-file` paths outside the world directory.

Failure: a body-text mention steals the target, ambiguous prefixes silently pick the first file, or an outside Markdown file is loaded into the interaction packet.

## 22. Path-backed id safety

Player or frontend supplies path-backed IDs such as request, packet, branch draft, handoff, resume, rule-check, divine-assessment, soften-request, manual-edit report, or checkpoint IDs. Scripts that use these IDs in paths must allow only letters, numbers, underscores, and hyphens.

Failure: an ID containing `../`, slashes, spaces, or other path characters creates, reads, updates, or previews a file outside its intended directory.

## 23. Active pointer path safety

Player or manual edits change `ACTIVE.md`. `branch_path` and `save_path` must remain world-local relative paths, and `save_path` must point to the active branch `SAVE.md`.

Failure: validation accepts an absolute path, `../` escape, or save pointer that does not belong to the active branch.

## 24. Manifest path safety

Player or manual edits corrupt `system/file-manifest.json`. Every listed file path must remain a world-local relative path before existence checks are trusted.

Failure: validation accepts a manifest entry with an absolute path or `../` escape, even if the referenced external file exists.

## 25. Branch state snapshot inheritance

Player creates a child branch from a live parent branch that already has visible characters, locations, and map pieces. The child branch must copy the parent branch's current state snapshot so its dashboard and map show inherited pieces immediately, while later child-only state changes remain isolated from the parent.

Failure: the child branch opens with empty pieces, has to scan parent history to reconstruct current state, or writes child interaction updates back into the parent branch.

## 26. Mutable terrain brush rendering

Player confirms a divine terrain change such as moving a river, adding a tributary, raising hills, or growing forest. The system must update the active branch `state/terrain-brushes.json` through a confirmed script, rebuild `dashboard/map-layers.json` with `brushes`, and let the frontend render those brushes as SVG particle strokes without hardcoded CSS terrain.

Failure: rivers, hills, or forests exist only as fixed decorative CSS, a terrain change rewrites unrelated map coordinates or story files, or frontend rendering cannot reflect updated brush data.

## 27. Command terrain brush action routing

Player uses a command-style god action to change terrain. The frontend or Codex must first create a non-canonical `create_action_request.py --action terrain-brush` request with compact payload fields such as `brush_id`, `kind`, `change_summary`, and `points_json` or a geometry placeholder. The request must suggest a confirmed `set_map_brush.py` command and must not directly write map data until the player accepts the geometry/removal.

Failure: a terrain command bypasses action requests, has no `set_map_brush.py` suggested command, drops the brush ID/kind/points payload, or mutates `dashboard/map-layers.json` directly without updating the active branch brush state.

## 28. Brush editor preview routing

Player opens the frontend brush editor, clicks the paper map to place terrain points, and asks it to generate a terrain change. The UI must render only a temporary preview layer, produce compact 0..100 `points-json`, and output a `create_action_request.py --action terrain-brush` command that later routes to `set_map_brush.py`.

Failure: map clicks mutate exported JSON in the browser, preview points disappear from the generated command, the brush editor creates a separate storage format, or the generated command bypasses the action-request confirmation path.

## 29. External model API host boundary

Player wants to run the world outside Codex with a custom large-model API. World initialization must create a visible `setup/llm-api.config.json`, the skill must document Codex-hosted and external-model play as two host modes over the same files, and `call_llm.py` must dry-run without contacting the API unless `--call` is explicit.

Failure: external API settings are hidden in code, real API keys are required for Codex play, dry-run makes a network call, or model output can directly mutate canon without passing through normal settlement scripts.

## 30. Local frontend app API boundary

Player serves the frontend with `serve_frontend.py` instead of opening static HTML. The app must load `/api/state`, refresh dashboard/timeline/map layers, let interaction buttons create non-canonical action requests through `/api/action-request`, and let the advance-time button run the mechanical `/api/advance-world` endpoint.

Failure: the local server exposes broad filesystem access, action buttons directly settle canon, static mode stops working, or the backend API bypasses the same `create_action_request.py` support-file lifecycle.

## 31. Hybrid historical narrative profile

Player chooses the default narrative direction: mixed mode, but biased toward realistic historical feel. World initialization must create `setup/narrative-profile.json` with default profile `hybrid-historical`, mirror a compact summary into `PLAYER.md`, export a dashboard `narrative_profile` summary, include compact narrative-profile requirements in interaction packets and external-model prompts, and validate priority order, required output layers, event pressure sources, event chain, character fields, social indicators, and style avoid rules.

Failure: the game only records this as an informal chat preference, close-up packets or external-model play cannot see the same profile, `validate_world.py` accepts a profile missing `settlement_plan`, or generated major events are treated as canon without a visible narration, compact GM summary, and concrete settlement plan.

## 32. Settlement result quality gate

Codex or an external model returns a settlement result after a close-up interaction or due queued event. Before canonical writes, the system must reject prose-only results that contain only summary/visible text and no event, chronicle, consequences, state appends, save updates, dashboard updates, or explicit settlement plan. Accepted results must write GM summary and settlement plan layers into the confirmed event file.

Failure: `settle_interaction.py` or `settle_queued_event.py` commits a beautiful paragraph with no durable consequence, or event files omit the narrative layers needed for later compact recall.

## 33. External model packaged turn

Player wants to continue a turn through a custom OpenAI-compatible API without staying inside Codex. The system must provide a wrapper that can create or load a compact interaction packet, dry-run without network calls, call only when `--call` is explicit, store support-only run artifacts in the active branch, validate any candidate settlement JSON, suggest normal settlement commands, refresh the manifest, and never mutate canon directly.

Failure: external-model play requires hand-assembling packets, hides generated request/response files, calls the network during preview, accepts unsafe run/packet/request IDs, or writes confirmed events/state without passing through settlement scripts.

## 34. Brush editor controlled styling

Player uses the frontend brush editor to alter rivers, tributaries, hills, or forests. The editor must expose width, density, jitter, and color controls; show copyable `points-json`; support undo/clear; render only a temporary preview; and include the style fields in the generated `terrain-brush` action payload.

Failure: brush style controls affect only CSS but not the command payload, copied points do not match the preview, undo/clear corrupts existing map-layer data, or the editor bypasses the action-request confirmation path.

## 35. Playable demo world generation

Player asks for a real opening demo world rather than screenshots or sample JSON. The system must create a compact confirmed world under `worlds/<world-id>/` with a real active save, visible locations, character pieces, terrain brushes, weather/random log, a queued pressure event, a pending action request, timeline/dashboard/map exports, frontend files, and a passing `validate_world.py` result.

Failure: the demo is only documentation, cannot be continued as a normal world, lacks real map/timeline/dashboard files, overwrites an existing world silently, or requires broad story reads before the first click.

## 36. Narrative template minimal set

The skill provides a small optional set of narrative/event templates for common generation shapes: interaction settlement, queued-event settlement, character seed, faction pressure, and divine intervention. Templates must define structure and causal checks without becoming a large fixed plot library.

Failure: templates are absent, too numerous, not routed from a guide, missing schema/use cases, or encourage fixed repetitive story beats instead of model-generated local causes and character agency.

## 37. Map zoom and pan

Player opens the frontend map and needs to inspect crowded pieces, pins, and terrain. The map must provide explicit zoom controls, wheel zoom, and drag panning outside brush-pick mode. Zoom/pan must be purely visual, implemented on a map content layer, and the brush editor must still serialize clicked points in the stable 0..100 map coordinate system after the view is transformed.

Failure: the map only switches semantic levels without real zoom, dragging triggers accidental brush points, zoom rewrites map-layer coordinates, or post-zoom brush clicks produce wrong `points-json`.

## 38. Medieval transparent PNG map assets

The paper-map frontend uses a small local PNG asset set for medieval hand-painted decoration: flag marker, forest stamp, hills stamp, creek stamp, parchment overlay, and corner ornament. These assets live under `assets/frontend-template/img/`, are copied into world frontends by `prepare_frontend.py`, and remain display-only decoration over data-driven map layers.

Failure: assets remain only in the conversation or global generated-image folder, the exported world frontend lacks `img/`, PNGs are not valid image files, terrain decoration replaces the mutable brush data source, or missing assets break the static frontend.
