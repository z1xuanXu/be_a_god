# Action Request AR-20260813182042541029

- schema: be-a-god.action-request.v1
- status: cancelled
- action: terrain-brush
- target_id: MAP
- target_kind: world
- intent: draw hills terrain brush
- created_at: 2026-08-13T18:20:42.541029+00:00
- updated_at: 2026-08-13T18:29:10.828710+00:00
- cancelled_at: 2026-08-13T18:29:10.828710+00:00

## Suggested command

```text
scripts/set_map_brush.py --world F:\be_a_god\worlds\reedbend-demo --brush-id 11 --kind hills --points-json '[[61.7,9.2],[50.3,13.8],[49.5,14.4],[31,16.3],[51.9,28.5],[66.3,14.7],[62.9,10.4]]' --label 'draw hills terrain brush' --width 6 --density 10 --jitter 3 --color '#765c38' --confirmed
```

## Payload

```json
{
  "brush_id": "11",
  "kind": "hills",
  "label": "draw hills terrain brush",
  "change_summary": "draw hills terrain brush",
  "points_json": "[[61.7,9.2],[50.3,13.8],[49.5,14.4],[31,16.3],[51.9,28.5],[66.3,14.7],[62.9,10.4]]",
  "width": 6,
  "density": 10,
  "jitter": 3,
  "color": "#765c38"
}
```
