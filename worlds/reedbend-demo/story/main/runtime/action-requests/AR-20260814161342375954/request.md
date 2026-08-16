# Action Request AR-20260814161342375954

- schema: be-a-god.action-request.v1
- status: executed
- created_at: 2026-08-14T16:13:42.377461+00:00
- updated_at: 2026-08-14T16:13:47.917469+00:00
- world_id: reedbend-demo
- branch_id: main
- branch_path: story/main
- world_time: year 1, day 7
- action: speak
- target_id: CHAR-0002
- target_kind: character
- intent: convene the first public river-grain hearing

## Suggested command

```text
scripts/make_interaction_packet.py --world F:\be_a_god\worlds\reedbend-demo --target-id CHAR-0002 --target-kind character --intent 'convene the first public river-grain hearing' --mode dialogue --request-id AR-20260814161342375954
```

## Lifecycle

- 2026-08-14T16:13:47.917469+00:00: requested -> executed

## Policy

- This file is a support request, not canon.
- Updating its status must not change events, chronicle, state, random logs, queues, dashboard, or timeline.
- `executed` means the suggested action was handled elsewhere; inspect `result_path` or linked canon files for effects.
