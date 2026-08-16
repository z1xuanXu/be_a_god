# Narrative Quality

Use this when resolving scenes, advancing time, creating characters, using an external model API, or checking whether generated results match the player's selected default: hybrid mode, but with a realistic historical feel.

## Default profile

Read `setup/narrative-profile.json` when narration quality, event settlement, or external model prompts need the exact profile. The default profile is `hybrid-historical`.

Interpret it as:

- close-up scenes for characters, dialogue, divine interventions, and player-clicked pieces;
- chronicle view for long social, environmental, institutional, and cultural change;
- simulation-first causality before dramatic presentation.

## Priority order

Use this order when choices conflict:

1. Causality: events must follow from pressures, choices, resources, rules, and prior facts.
2. World continuity: do not break confirmed geography, deaths, queues, branch pointers, locked rules, or random logs.
3. Character agency: people and groups act from desire, fear, misunderstanding, resources, relationships, secrets, and their view of the god.
4. Historical texture: food, weather, terrain, legitimacy, faith, rumor, debt, kinship, trade, law, and institutions matter.
5. Dramatic presentation: make it readable, but do not force spectacle without cause.

## Required output layers

When resolving a meaningful model-generated event, produce or preserve these layers:

- `visible_narration`: the text the player sees now.
- `gm_summary`: compact causal summary for the next turn.
- `settlement_plan`: concrete changes that can be written by scripts, such as event node, state append, chronicle line, queue item, rule check, action request, or map brush update.

For quick low-risk interactions, keep these layers short and implicit in the result JSON. For major events, make them explicit before settlement.

## Event pressure chain

Build major emergent events from this chain:

`pressure -> actor_choice -> direct_consequence -> second_order_consequence -> player_intervention_point`

Pressure should usually come from at least one of:

- character pressure;
- resource pressure;
- institutional pressure;
- environmental pressure.

Avoid events that happen only because the plot needs them.

## Character creation and update

For important characters, track or infer these semantic fields:

- desire;
- fear;
- misunderstanding;
- resources;
- relationships;
- secret;
- god_view.

Only generate these with the model/player. Deterministic scripts should store or move the resulting fields; they should not invent them.

## God interventions

A divine action is not just a wish. Decide whether it is:

- absolute rewrite: the player intentionally overrides normal causality, often requiring branch or rule handling;
- in-world manifestation: the world experiences the god action through weather, terrain, bodies, omens, institutions, fear, faith, or rumor.

Record the second-order consequences when the intervention is material.

## Scale rules

- Close-up: use dialogue, sensory scene, immediate choices, and small packets. Do not load broad history unless source pointers require it.
- Regional: use short scenes plus causal summaries for migration, scarcity, law, faith, war, succession, and terrain.
- Chronicle: use restrained history-like prose, indicators, and durable event/state changes. Avoid excessive dialogue.

## Style rules

Prefer concrete cause and consequence. Write with a restrained historical texture. Avoid vague epic filler, cheap wish fulfillment, and repeated abstract words such as fate, ancient, echo, destiny, or eternal when no concrete cause is present.

If a generated passage is vivid but has no settlement plan, treat it as presentation only and do not commit it as canon until a concrete event/state consequence exists.
