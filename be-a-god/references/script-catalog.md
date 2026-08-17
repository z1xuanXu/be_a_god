# Script Catalog

Use deterministic scripts for mechanics and the host/model for semantic invention. The project has no local web frontend.

## Core Lifecycle

- `create_world_brief.py`: write editable world briefs.
- `validate_world_brief.py`: validate drafts before initialization.
- `init_world.py`: initialize a confirmed world with canonical files, semantic map data, profiles, and first save.
- `create_demo_world.py`: create a compact playable script-driven demo world.
- `validate_world.py`: validate world structure, canonical pointers, map data, derived JSON, profiles, queues, logs, handoffs, and manifests.
- `check_install_ready.py`: validate the non-frontend skill package and optionally run smoke tests.
- `install_local_skill.py`: preview or install the skill only after explicit confirmation.

## State, Map, and Derived Data

- `create_entity.py`, `move_entity.py`, `wander_entities.py`: create and update entity/location state.
- `set_map_brush.py`: create/update/remove confirmed terrain brush geometry.
- `build_indexes.py`, `build_event_graph.py`: rebuild indexes.
- `build_map_layers.py`: rebuild derived semantic map data.
- `build_timeline.py`: rebuild timeline data.
- `export_dashboard.py`: rebuild compact derived world summaries.
- `build_file_manifest.py`: rebuild file hashes and authority classification.

## Play and Settlement

- `create_action_request.py`, `update_action_request.py`, `cancel_action_request.py`, `reorder_action_requests.py`, `list_action_requests.py`: non-canonical player intent records.
- `make_interaction_packet.py`, `read_source_packet.py`: bounded interaction context and exact source reads.
- `settle_interaction.py`, `settle_queued_event.py`, `validate_settlement_result.py`: canonical settlement workflow.
- `advance_world.py`, `queue_event.py`, `resolve_random.py`: deterministic time and random state.
- `set_world_rule.py`, `check_world_rules.py`, `assess_divine_action.py`: rules and intervention review.
- `set_attention.py`, `build_ignored_digest.py`: attention state and collapsed summaries.
- `draft_branch.py`, `create_branch.py`, `switch_branch.py`, `resolve_branch_view.py`: branch workflow.
- `create_handoff.py`, `resume_world.py`, `check_context_pressure.py`: context handoff and resume.
- `call_llm.py`, `external_play_turn.py`: optional external-model host flow; output never writes canon directly.

Path-backed IDs must use only letters, numbers, underscores, and hyphens.
