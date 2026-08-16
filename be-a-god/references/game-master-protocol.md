# Game Master Protocol

## Context budget

Default to small reads. Start from `ACTIVE.md`, current branch `SAVE.md`, `PLAYER.md`, and the exact entity/place/event requested by the player. `make_interaction_packet.py` automatically queries the active event graph, ranks at most three relevant visible events by target actor, location, intent/tag match, and active-branch preference, then reads their exact event sources within a 3600-character history budget. Parent history is visible only through the `parent_save` ancestry chain and only through each branch's `fork_event`; sibling branches and post-fork parent events remain blocked.

Event causality uses structured `cause_refs` and `effect_refs` containing valid visible event IDs. Put prose in `cause_notes` and `effect_notes`; legacy prose in `causes`/`effects` is indexed as notes rather than graph edges.

When continuing in a new conversation, run `scripts/resume_world.py --world <world> --dry-run` or read the latest `runtime/resume-packets/<id>/resume.json` first. Use its `first_read` list as the startup boundary before expanding any story sources.

Read older story only for:

- old promises or curses;
- secrets and knowledge boundaries;
- unresolved conflicts;
- death, succession, war, or other irreversible facts;
- branch inheritance checks;
- player-requested audit or recap.

## Narrative modes

- Map observation: divine overview.
- Piece click: close-up scene.
- Time jump: objective chronicle summary.
- Major event: pause and switch to close-up.

Characters know only what their own state and event history allow. The player may be omniscient; non-omniscient characters may not use player-only information.

## Narrative quality profile

Use `setup/narrative-profile.json` as the persistent default. The default profile is `hybrid-historical`: mixed close-up play and chronicle play, but biased toward realistic historical causality instead of forced spectacle.

For meaningful model-generated events, apply this priority order:

1. causality;
2. world continuity;
3. character agency;
4. historical texture;
5. dramatic presentation.

When a scene or event changes durable state, keep three layers available:

- `visible_narration`: what the player sees now;
- `gm_summary`: compact causal summary for future turns;
- `settlement_plan`: concrete event/state/chronicle/queue/map changes that scripts can write.

Major events should usually follow the chain `pressure -> actor_choice -> direct_consequence -> second_order_consequence -> player_intervention_point`. Pressures should come from characters, resources, institutions, or environment, not from plot convenience alone.

For important characters, generate or maintain desire, fear, misunderstanding, resources, relationships, secret, and god_view. These are semantic fields: the model or player supplies them; deterministic scripts only store, index, move, or settle them.

Use `references/narrative-quality.md` when a generated scene feels vivid but may lack concrete cause, consequence, or settlement.

## Content boundaries

Use `scripts/set_content_profile.py` to update player content-boundary preferences. The profile controls presentation mode only; it must not rewrite confirmed events, deaths, damage, random logs, queue results, or chronicle facts.

Supported topic modes are `allow`, `summary`, `soften`, and `avoid`. The `unsoftened` preset means the game does not add extra softening inside allowed content, but it never overrides Codex or platform safety boundaries.

For a one-off "soften this paragraph/scene" request, create a softening request with `--soften-target`. Treat the generated request as a rewrite instruction for presentation only. Keep canon facts intact.

## World rules and locked facts

Use `scripts/set_world_rule.py` when the player explicitly defines, changes, revokes, or locks a world rule. The script writes `setup/world-rules.json` and updates the structured rules block in `CANON.md`.

Treat active world rules as higher priority than generated events or random outcomes. If a requested action would violate a rule, surface the conflict and ask for explicit override, revision, or branching. Do not silently reinterpret locked facts.

For a material action that may touch locked facts, first prepare a compact rule check with `scripts/check_world_rules.py`. Use `--request-id <id>` when the action came from the frontend. Read only that packet and its listed sources unless the conflict cannot be resolved from the compact rule text.

## God action requests

When a frontend button or quick player command expresses intent, record it first with `scripts/create_action_request.py --world <world> --action <action> ... --confirmed`. Treat ordinary map clicks as selection or inspection unless the player also chooses an action.

This step is intentionally cheap: read only `ACTIVE.md` and the active `SAVE.md`, write `runtime/action-requests/<request_id>/request.json` plus `request.md`, and refresh the manifest. Do not load old chapters, sibling branches, full biographies, or broad event history merely to store the request.

Action requests are not canon. They only preserve the player's current intent and suggest the next mechanical command, such as `make_interaction_packet.py`, `advance_world.py`, `resolve_random.py`, `set_world_rule.py`, `set_attention.py`, `set_map_brush.py`, or `draft_branch.py`.

For command-style terrain edits, create a `terrain-brush` action request first. Convert the player's natural-language command into a compact brush payload only as far as needed: `brush_id`, `kind`, `change_summary`, and either confirmed `points_json` or a placeholder that tells the next Codex pass to generate geometry. Do not read broad story history merely to save or preview the request. Execute `set_map_brush.py` only after the player accepts the geometry or removal.

After the player confirms or dismisses the request, update the request lifecycle with `scripts/update_action_request.py --world <world> --request-id <id> --status <accepted|executed|cancelled> --confirmed`. Do not treat lifecycle status as proof of a world change; use result pointers and canonical files for that.

## Host modes

Default to Codex-hosted play: narrate and resolve semantic events in the active Codex conversation, then commit durable consequences through scripts.

When the player brings an external model API, treat it as a replaceable semantic engine over the same compact packets. Prefer `scripts/external_play_turn.py` for normal external play: it creates or loads a compact packet, previews or calls `scripts/call_llm.py`, stores support-only run artifacts under the active branch, extracts candidate settlement JSON, validates it, and suggests settlement commands. Use `scripts/call_llm.py` directly only for low-level debugging or custom host wrappers. The API may propose prose, event summaries, and result JSON, but it must not bypass normal confirmation or settlement scripts.

External-model prompts that resolve meaningful events must include the compact narrative-profile requirements: causality first, preserve continuity, keep character agency, use historical texture, and return a settlement plan rather than prose alone.

## Divine cost assessment

In mixed-mode play, preview material divine interventions with `scripts/assess_divine_action.py --world <world> --action <action> ... --dry-run` when the player is still considering the move. Use `--confirmed` only when writing the support-only assessment packet to `runtime/divine-assessments/`. Use this flow when an action changes weather, bodies, places, fate, rules, deaths, branches, or other durable world state.

The assessment is support-only. It estimates ordinary cost from action type, scale, irreversibility, visibility, and target count. If the score exceeds the normal limit, tell the player the over-limit status and offer: accept cost, narrow scope, declare absolute divine authority, cancel, or delay. If the player chooses absolute authority, pass `--absolute` so the assessment records `absolute-authorized`.

## Interaction packets

For close-up interaction, prepare a small packet containing:

- current world time and place;
- target ID and immediate visible state;
- public facts;
- player intent;
- compact narrative-profile requirements;
- allowed source pointers;
- forbidden source areas;
- source budget;
- follow-up source request field.

Finish the scene before broad retrieval unless the interaction touches old commitments, hidden facts, identity conflicts, or irreversible actions.

Use `scripts/make_interaction_packet.py` for this packet. If the interaction came from `runtime/action-requests/<request_id>/`, pass `--request-id <request_id>` so the packet records and validates the request pointer. The script does not settle consequences and intentionally avoids broad chapter/event reads. If the packet indicates that a promise, secret, war, death, succession, branch inheritance, or explicit player audit is involved, request the specific extra source before continuing.

The packet should include a compact `narrative_profile` object from `setup/narrative-profile.json`. Obey it without reading the full profile unless the player is changing narration-quality settings or auditing style.

When the packet or player requests exact old source text, use `scripts/read_source_packet.py --world <world> --source <pointer> --json` or `--from-packet <packet-path>`. Read only explicit pointers. The source reader blocks paths outside the world, outside the root allowlist, or outside the active branch's parent chain.

After narration, use `scripts/settle_interaction.py` with a confirmed settlement result. The settlement result should include visible narration or summary, a GM summary, and a settlement plan. Legacy concrete fields are accepted when they provide event title/type, state appends, chronicle text, consequences, save updates, or dashboard piece updates. Use `scripts/validate_settlement_result.py --result <result.json> --kind interaction --json` before writes when the result came from an external model or may be prose-only. The settlement script rejects prose-only results before canonical writes, writes narrative settlement layers into the event file, writes canonical consequences and derived frontend data, then refreshes the file manifest.

Target resolution must prefer exact state-card `- id:` matches, then allow only a unique filename-prefix fallback. It must not use body-text mentions as target matches. This prevents a decoy card containing `CHAR-0001` or `location: LOC-001` from stealing a click intended for the actual target card. Explicit `--target-file` values must stay inside the current world directory.

For causal recall, use `indexes/event-graph.json` before expanding old story. The graph can identify candidate events by actor, location, tag, cause, or effect without reading chapter prose. After selecting candidate event IDs, use explicit source pointers and `scripts/read_source_packet.py` for exact text.

## Time advancement

Support these advance modes: single step, fixed duration, condition until, event priority, follow character, and regional focus.

For long jumps, advance in slices. Confirm only events already reached and settled. Stop on configured pause conditions: death, destruction, war, succession, betrayal, blocked rules, or missing player choice.

Use `scripts/set_advance_profile.py` when the player wants persistent advance behavior such as step-by-step, hybrid, chronicle, event-priority, regional focus, or follow-character play. The profile is stored in `setup/advance-profile.json` and does not change canon by itself. Apply it with `scripts/advance_world.py --preset <preset-id>`; if `--days` is omitted, the default preset supplies the span and wandering settings. One-off player commands override preset fields for that run. For "advance to the next major event", use an event-priority preset with `until_next_queue: true` or pass `advance_world.py --until-next-queue`.

Use `scripts/queue_event.py --world <world> ... --confirmed` to record known future triggers, travel arrivals, warnings, plot-ready moments, or high-priority events before time advances. Use `--dry-run` when the trigger wording or pause policy is still unclear. `scripts/advance_world.py` must stop at the first queued pause event within the requested span, write `runtime/advance-runs/<run_id>/pause.md`, mark the queue item `due`, update `SAVE.md`/`CURRENT.md`, and surface the pause in dashboard unresolved choices.

After a queued event is due, do not treat the queue item itself as confirmed history. Narrate and resolve the event, ask for confirmation when consequences are material, write the result JSON, validate it with `scripts/validate_settlement_result.py --result <result.json> --kind queued-event --json` when needed, then use `scripts/settle_queued_event.py --world <world> --queue-id <id> --result <result.json> --confirmed`. The settlement rejects prose-only results, creates the event node and chronicle entry, clears the active pause, marks the queue item `settled`, removes the dashboard unresolved choice, and refreshes the manifest.

When the player wants time to pass with wandering pieces, pass `--wander` to `advance_world.py`. The optional wandering tick runs only after a non-paused advance. If a queued pause is reached, wandering is skipped and the queued event must be resolved first.

## Random and model generation

Use scripts for deterministic or rule-random work: weather, travel progress, queue selection, indexes, timelines, manifests, dashboard export.

Use the language model for high-semantic creation: personalities, dialogue, myths, political motives, cultural interpretation, and dramatic framing.

The player may override weather, events, or outcomes. Record overrides as divine actions. For weather, `scripts/resolve_random.py --kind weather --override <value>` should append the random log, update `dashboard/data.json`, and refresh the file manifest unless the caller explicitly skips those sync steps.

## Entity and piece creation

When a new character, location, faction, item, or object must enter play, split the work:

1. Let the model or player provide semantic fields such as personality, motive, secrets, cultural role, and dramatic hook.
2. Run `scripts/create_entity.py --world <world> --kind <kind> --name <name> --confirmed` to assign/store the entity card, refresh indexes, refresh map layers, refresh visible pieces, and update the file manifest.
3. For map-visible characters, include either a `location` whose coordinates exist in `base/maps/coordinates.json` or direct `x`/`y` fields.
4. For places, use kind `location`; the script updates `state/locations/`, `base/maps/hierarchy.json`, and `base/maps/coordinates.json` when coordinates are provided.
5. Do not ask the script to invent personality or political motives. Put those in `--traits-json` only after the model/player has supplied them.

For one-off piece movement, let the model decide why and where an entity moves, then run `scripts/move_entity.py --world <world> --entity-id <id> ... --confirmed` for the mechanical update. Use it for location, coordinate, map level, or status changes that should immediately appear on the dashboard map.

For routine wandering, use `scripts/wander_entities.py --world <world> --confirmed`. It uses the active branch seed and current world time to choose destinations, includes ignored characters by default so they keep living offscreen, logs each destination as `kind: wander` in `random/random-log.jsonl`, and supports player overrides with `--override ENTITY=LOCATION`.
