# Action Request AR-DEMO-MIRA

- schema: be-a-god.action-request.v1
- status: cancelled
- action: speak
- target_id: CHAR-0001
- target_kind: character
- intent: Ask Mira about the hidden oath tablet.
- created_at: 2026-08-13T13:03:37.867883+00:00
- updated_at: 2026-08-13T18:29:44.456582+00:00
- cancelled_at: 2026-08-13T18:29:44.456582+00:00

## Suggested command

```text
scripts/make_interaction_packet.py --world F:\be_a_god\worlds\reedbend-demo --target-id CHAR-0001 --target-kind character --intent "Ask Mira about the hidden oath tablet." --mode dialogue --request-id AR-DEMO-MIRA
```

## Payload

```json
{
  "topic": "ask Mira why a ferry heir is hiding an oath tablet",
  "suggested_template": "interaction-result.template.json"
}
```
