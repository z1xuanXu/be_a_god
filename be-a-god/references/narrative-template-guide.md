# Narrative Template Guide

Use these templates only when structure helps. Do not load every template for ordinary play.

## Routing

- `assets/narrative-templates/interaction-result.template.json`: close-up interactions before `settle_interaction.py`.
- `assets/narrative-templates/queued-event-result.template.json`: due queued events before `settle_queued_event.py`.
- `assets/narrative-templates/character-seed.template.json`: important character creation or promotion.
- `assets/narrative-templates/faction-pressure.template.json`: regional, institutional, or resource pressure.
- `assets/narrative-templates/divine-intervention-result.template.json`: direct god actions with durable consequences.

## Use rule

Prefer the smallest matching template. Templates define output shape and causal checks, not fixed plot. The language model still generates personalities, motives, dialogue, and local historical texture.

Every canonical settlement should still pass `scripts/validate_settlement_result.py` before write scripts commit it.
