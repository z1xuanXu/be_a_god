# Frontend Contract

## Role

The frontend is an observation and command surface. It may prepare drafts and action requests, but formal canon world changes are committed through Codex/player confirmation and local scripts. It supports static mode and local app mode.

## Required panels

1. Creation wizard with locked / polishable / AI-fill fields.
2. Three-level semantic map: world or continent, region, city or concrete scene.
3. Visible character pieces, including wandering characters.
4. Event pins that open short event cards.
5. Always-visible vertical scrollable timeline similar to Civilization-style chronology.
6. Dashboard for time, weather, latest random result, attention list, current branch, default advance preset, unresolved choices, advance profile summary, recent random-log summary, and key warnings.
7. God action panel for observe, speak, intervene, advance time, branch, ignore/follow character, lock a world rule, command terrain-brush changes, and override random outcomes. Buttons should prepare a visible pending action draft first; the frontend must expose a clear commit control such as "确认提交 / 开始运行" before it calls the local backend or creates support files. The request is a support file with no canonical effect until Codex or a script executes the suggested next command. Advance time, weather override, rule locking, and terrain-brush commands are global actions and must not require a selected piece. Advance-time suggestions should prefer `dashboard.advance_profile.default_preset` when present and pass it as `--preset <preset-id>` rather than only embedding it in intent text. Terrain-brush suggestions must use action `terrain-brush` and payload fields such as `brush_id`, `kind`, `change_summary`, and either `points_json` or a placeholder for AI-generated geometry.
8. Brush editor panel for manual terrain sketching. It may collect 0..100 map coordinates by clicking the map, render a temporary preview stroke, expose editable width/density/jitter/color controls, show and copy the current `points-json`, support undo/clear, and generate the same `terrain-brush` action request. It must not write or mutate dashboard/map-layer JSON directly.
9. Branch action fill-in prompt for required branch fields. Before generating a branch request, collect at least `branch_id` and `change_summary`; use the selected event or piece source as `fork_event`.
10. Pending action request list sourced from `dashboard.pending_action_requests`, with Chinese player-readable action names, statuses, target summaries, request IDs, and source pointers. Do not expose only raw enum strings such as `requested`, `observe`, or `advance-time` as the primary label. In local app mode, pending items may be manually cancelled or drag-reordered by the player; cancellation marks the request `cancelled` instead of deleting audit files, and reordering persists only display/priority order.
11. Civilization-style medieval hex paper-map visual style. The default UI should feel like parchment with hand-inked borders, light comic shadows, and a three-level interlocking hex grid. Hexes must be mutually nested/offset like a 4X strategy map, not scattered cards. Each visible terrain hex should be filled by an AI-generated medieval PNG terrain asset such as grassland, forest, hills, mountain, river, lake, marsh, desert/plains, village, castle, farm, or ruins. Movable units, buildings, characters, and event pins should be displayed as medieval icon overlays inside or anchored to the relevant hex. Visual styling must not change map coordinates, IDs, source pointers, or world files.
12. Escaped JSON previews in the detail panel. Treat dashboard, timeline, map, action-request, rule, random-log text, and generated command JSON arguments as untrusted display/command text even when it is local.
13. Optional local backend connection. When served by `scripts/serve_frontend.py`, the frontend may call `/api/state` to refresh dashboard/timeline/map layers, `/api/action-request` to create non-canonical action request files, `/api/action-request/cancel` to cancel pending requests, `/api/action-requests/reorder` to persist display priority, `/api/map-brush/apply` to apply player-confirmed manual brush geometry through `set_map_brush.py`, and `/api/advance-world` to run the mechanical `advance_world.py` time step. It must still not settle interactions, queue event story content, AI-inferred terrain geometry, or other semantic canon consequences directly.
14. Map view controls for real zoom and pan. The player can zoom with controls or wheel and drag the paper map when not in brush-pick mode. Dragging must work even when the pointer starts on a hex tile, terrain PNG, unit icon, place icon, or event pin; native browser image dragging and text selection must be suppressed inside the map. A click without movement selects the target, while a drag with movement pans the map and must not also select a hex or unit at pointer-up. Zoom/pan are visual state only and must not rewrite coordinates, IDs, source pointers, dashboard JSON, or map-layer JSON.
15. Medieval transparent PNG map assets under `assets/frontend-template/img/`. The paper-map skin may decorate the whole UI shell, panels, buttons, pieces, event pins, map-layer nodes, terrain brush stamps, parchment texture, and corners with transparent PNGs, while preserving the data-driven SVG brush layer underneath for precise mutable terrain geometry. Keep final assets high enough resolution for zoomed map display; do not downscale source assets just to reduce file size unless a separate display derivative is created.
16. Built-in illustrated tutorial page. The dashboard must expose a visible tutorial entry that opens a guide explaining the timeline, map zoom levels, pieces/pins, right-side actions, advance-time behavior, attention controls, and brush editor workflow.
17. Detail cards should show player-facing Chinese plus the original English enum for type and status, such as `地图节点（map-node）` and `地区（region）`, so players can understand the panel while developers still see source terms.
18. The default frontend skin should use a serif font stack throughout the page, including buttons, inputs, IDs, code snippets, and generated command previews.
19. Player-visible story reader below the map, paired with a story directory in the left column. It reads only filtered narrative fields exported into dashboard JSON, never raw Markdown. Timeline entries with a matching confirmed event should open the same story entry; current scene remains a dedicated directory item.
20. Every map piece class—characters, mobile units, carts/boats, buildings, resources, items/relics, and event markers—uses a transparent-background medieval standard/pennant PNG with a strong silhouette outline. The map button and icon container must add no circular, square, parchment, or gradient background behind the art. Provide a generic standard fallback for unknown kinds.
21. Every non-map button and every text-entry control uses the GPT-generated transparent medieval control artwork under `img/ui/`, with live DOM text/value rendered directly over the asset. CSS must not add an ordinary border or filled backing behind these assets. Disable native dragging for controls and decorative images while preserving explicit application drag behavior such as map panning and draggable request rows.
22. The default world hex projection contains at least ten times the original 35 cells (`23 × 16 = 368` world cells), with larger region/scene projections, while retaining zoom and pan. Expanded terrain includes coast, tundra, snow, volcanic ground, badlands, and meadow using generated transparent outlined hex assets. Settlements route to village, town, city, and fortress banner pieces with transparent backgrounds and strong black silhouette outlines, rendered through the same movable-unit overlay system.

## Map behavior

Map zoom reads exported dashboard data only. It must not load full story text. Clicking a piece, pin, place, or hex selects it and shows a compact source pointer/detail card. A god-action button prepares a draft; the commit button starts the request or mechanical advance. Codex may create an interaction packet only if the player actually proceeds.

Zoom/pan uses a visual `map-content` transform. Brush editor coordinate capture must invert that transform so clicked points still serialize to the same 0..100 coordinate system after zooming or panning. Dragging the map is disabled while brush point selection is active.

Use a three-level hex projection in the template: coarse world hexes, medium region hexes, and finer scene hexes. The hex grid must use true honeycomb geometry in the rotated-90-degrees orientation requested by the player: pointy-top regular hexes with width-to-height ratio `sqrt(3) / 2`, vertical center spacing `0.75 * hexHeight`, and half-hex horizontal staggering on alternating rows. Adjacent terrain tiles should share full edges like a 4X strategy map, not overlap like cards or float with visible triangular gaps. The display layer may slightly overdraw tile artwork to hide browser antialiasing and transparent PNG borders, but the center coordinates and snapping math must remain the strict honeycomb grid. Terrain must be map-real, not zoom-random: the region grid is the canonical terrain grid, scene hexes are a finer sampling whose centers and terrain inherit from the corresponding region hex, and world hexes are coarse overview sampling. Zooming must never re-randomize a coordinate's biome or turn a previously visible region biome into an unrelated scene biome. Only the active zoom level should be interactive; other levels should be hidden except for the brief level-change fade. Existing 0..100 coordinates remain authoritative. The frontend may snap display placement to the nearest active hex center, but detail cards should preserve the original coordinate and source pointer.

Use medieval icon hex-units for characters, places, buildings, and event pins. Status rings or outlines should visibly distinguish ordinary, wandering or moving, plot-ready, followed, ignored, paused or danger, dead, and hidden. If movement speed fields such as `speed`, `move_speed`, or `speed_label` are present, show them on movable units. Class names derived from local JSON status fields must be normalized before being applied to DOM nodes.

Map-layer nodes should carry source pointers when a location card exists. Terrain visuals should come from `map-layers.brushes`, generated by merging `base/maps/terrain-brushes.json` with the active branch `state/terrain-brushes.json`. The frontend renders these as SVG brush particles for rivers, tributaries, hills, forests, or custom terrain, and may add transparent PNG terrain stamps (`forest-cluster-stamp.png`, `rocky-hills-stamp.png`, `creek-stamp.png`) as display decoration. The SVG brush layer must sit above terrain hex artwork and below unit/event/place icons, while the brush-editor preview sits above both so the player can see the pending stroke. Brush width in saved data is canonical command metadata; the frontend may use a thinner cosmetic display width so rivers and sketch previews do not cover hex details. It may also show low-opacity backdrop stamps such as castle, village, bridge, road, farm, ruins, marsh, lake, shoreline rocks, and mountain ridge to make the map feel inhabited. It must not fetch or display the Markdown body by itself.

## Timeline behavior

Timeline nodes distinguish confirmed events, current point, branch points, virtual future queue items, locked facts, and ignored-character collapsed summaries.

Clicking a timeline node should show its summary and source pointer. Expanding full story is an explicit action.

## Ignored characters

Ignored characters continue to move, age, suffer, act, and die. Their personal story is collapsed until the player clicks them. Viewing a digest does not automatically cancel ignore state.

## Template asset

Use `assets/frontend-template/` as the first local dashboard template. It is a static HTML/CSS/JS shell with sample data for:

- vertical scrollable timeline;
- map pieces;
- event pins;
- current time, weather, and branch dashboard;
- timeline states for confirmed, locked, queued, due, ignored, and branch nodes;
- active world-rule summary from `dashboard.world_rules.active`;
- recent random-log summary from `dashboard.random_log.recent`;
- pending action requests;
- advance profile summary from `dashboard.advance_profile`;
- illustrated tutorial page/modal reachable from the topbar;
- parchment / ink-outline / comic-shadow markers in the default paper-map CSS skin;
- real map zoom/pan controls and transform-safe brush-editor coordinate capture;
- transparent medieval PNG assets in `img/` for flags, UI frame, forest, hills, mountains, creek, castle, village, bridge, road, farm, ruins, marsh, lake, shoreline rocks, parchment overlay, and corner ornament;
- AI-generated transparent hex terrain PNGs in `img/` for grassland, forest, hills, mountain, river, lake, marsh, desert, village, castle, farm, and ruins;
- three-level interlocking hex grid rendering with PNG-filled terrain tiles and medieval icon overlays for places, pieces, buildings, and event pins;
- a visible pending-action commit panel so right-side buttons and brush editor commands do not silently start running before player confirmation;
- SVG terrain brush particles from `map-layers.brushes`, plus optional PNG terrain stamps and backdrop stamps, compass, scale bar, and map legend generated in the frontend from display-only markup;
- command-style terrain-brush action payloads that route through `create_action_request.py` before `set_map_brush.py`;
- brush editor preview points, width/density/jitter/color controls, copyable `points-json`, undo/clear controls, and generated `terrain-brush` action payloads;
- basic god action request payloads using `scripts/create_action_request.py`.
- optional backend detection through `/api/health`, `/api/state`, `/api/action-request`, `/api/action-request/cancel`, `/api/action-requests/reorder`, and `/api/advance-world`.

The template is an asset, not the final hosted frontend. It should be copied into a world-facing app or replaced by a richer implementation later.

The template should prefer `dashboard.json`, `timeline.json`, and `map-layers.json` when served beside `index.html`, fall back to sample JSON when those files are absent, and allow the player to manually load exported dashboard, timeline, or map-layer JSON through file pickers. Manual loading is observation-only; it must not commit world changes.

Use `scripts/prepare_frontend.py --world <world> --confirmed` to copy the static template into `<world>/frontend`, place current exported files as `dashboard.json`, `timeline.json`, and `map-layers.json`, and generate a local `README.md` that explains how to open the panel, what each JSON file means, and that the static frontend is read-only for canon. The script must refuse writes unless confirmed, keep output inside the world directory, and avoid overwriting existing frontend files unless `--overwrite` is supplied. Use `scripts/serve_frontend.py --world <world>` for local app mode; the server binds to localhost by default and exposes compact state refresh, action-request creation/cancellation/reordering, and mechanical time advance endpoints.

The creation wizard in the template may generate and download a `WORLD-BRIEF.md` draft from player fill-in fields. It should expose content-boundary presets (`gentle`, `standard`, `unsoftened`, `custom`) and absolute-ban lines, and include a `Field source map` that labels player-locked, polishable, player-setting, player-note, and AI-fill fields. This is a draft-only convenience path: it must leave `Status: draft`, and formal initialization still requires player confirmation plus the backend validation and `init_world.py` flow.
