# Map-plan creation and confirmation

Natural-language geography must pass through this reviewable low-cost stage before formal initialization:

```bash
PY='C:/Users/xuzix/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
"$PY" 'F:/be_a_god/be-a-god/scripts/create_map_plan.py' \
  --brief 'F:/path/to/world.WORLD-BRIEF.md' \
  --world-id '<world-id>' \
  --output 'F:/path/to/MAP-PLAN.json'
```

`create_map_plan.py` makes no model/API call. It recognizes bounded cardinal spatial rules and emits `status: draft`, terrain-zone bounds, river direction, settlement coordinates, source labels, and `unresolved` claims.

The player or host must inspect the file. For an accepted plan, change only:

```json
"status": "confirmed"
```

Then initialize the world with the plan:

```bash
"$PY" 'F:/be_a_god/be-a-god/scripts/init_world.py' \
  --worlds-dir 'F:/be_a_god/worlds' \
  --world-id '<world-id>' \
  --brief 'F:/path/to/world.WORLD-BRIEF.md' \
  --map-plan 'F:/path/to/MAP-PLAN.json' \
  --confirmed
```

An unconfirmed MAP-PLAN is rejected. Without `--map-plan`, legacy keyword seeding remains available for compatibility but should not be used when the player supplied spatial layout requirements.
