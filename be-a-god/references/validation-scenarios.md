# Validation Scenarios

Use these scenarios to test the non-frontend skill before calling it playable.

1. **Draft to world** — a world brief stays a draft until confirmation, then initialization preserves locked fields and source maps.
2. **Map semantics** — confirmed geography becomes ordered `terrain_zones`, normalized coordinates, and terrain brushes; it must not fall back to random geography.
3. **Close-up interaction** — use bounded packets and settle concrete consequences without broad history reads.
4. **Time advance** — advance in slices, stop on meaningful queued events, and never prewrite future confirmed history.
5. **Branching** — create a reviewed draft then an isolated child branch; never overwrite the active parent.
6. **Manual edits** — detect, classify, and require confirmation before importing Markdown changes.
7. **Rules and action requests** — durable rules are recorded in setup; player intent is non-canonical until a confirmed script settles it.
8. **Derived rebuilds** — `build_indexes.py`, `build_map_layers.py`, `build_timeline.py`, and `export_dashboard.py` reproduce derived JSON without changing canon.
9. **External models** — dry runs do not contact an API; candidate model output is validated and settled through normal scripts.
10. **Handoffs** — resume starts from `first_read`, not broad history or sibling branches.
11. **Install safety** — readiness checks and install previews do not overwrite global skills.
12. **World validation** — active pointers, state IDs, queues, random logs, map data, profiles, handoffs, and manifests are checked before reporting success.
