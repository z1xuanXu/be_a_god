from pathlib import Path

ROOT = Path(r"F:/be_a_god/be-a-god/assets/frontend-template")
APP = ROOT / "app.js"
IMG = ROOT / "img"


def test_default_world_grid_has_at_least_ten_times_original_cells():
    text = APP.read_text(encoding="utf-8")
    assert "world: { cols: 23, rows: 16" in text


def test_expanded_terrain_assets_are_routed_and_present():
    text = APP.read_text(encoding="utf-8")
    for kind in ("coast", "tundra", "snow", "volcanic", "badlands", "meadow"):
        assert f"hex-{kind}.png" in text
        assert (IMG / f"hex-{kind}.png").exists()


def test_map_renders_only_active_level_and_units_share_its_grid():
    text = APP.read_text(encoding="utf-8")
    assert "function renderHexGrid(parent, level)" in text
    assert "renderHexGrid(content, visibleLevel)" in text
    assert "const snapped = nearestHexCenter(pos, mapLevelForScale())" in text
    assert "Object.keys(HEX_LEVELS).forEach" not in text


def test_pan_and_same_level_zoom_do_not_walk_all_map_nodes():
    text = APP.read_text(encoding="utf-8")
    transform_body = text.split("function applyMapViewTransform()", 1)[1].split("function centerMapAnchor", 1)[0]
    assert "applyZoomFadeToRenderedMap" not in transform_body
    assert "terrainImage = document.createElement" not in text


def test_units_fit_inside_one_5000_meter_cell_and_scale_bar_tracks_it():
    text = APP.read_text(encoding="utf-8")
    css = (ROOT / "styles.css").read_text(encoding="utf-8")
    assert "const HEX_SIZE_METERS = 5000" in text
    assert "const pieceWidth = snapped.drawWidth * 0.72" in text
    assert "const pieceHeight = snapped.drawHeight * 0.72" in text
    assert "node.style.setProperty(\"--piece-width\"" in text
    assert "updateMapScaleBar()" in text
    assert "0</small><span></span><small>5 km" in text
    assert "width: var(--piece-width" in css
    assert "width: var(--scale-width" in css


def test_task_closeup_zoom_reaches_twelve_times_and_uses_ratio_steps():
    text = APP.read_text(encoding="utf-8")
    assert "max: 12" in text
    assert "factor: 1.25" in text
    assert "scale >= MAP_ZOOM.taskCloseup" in text
    assert "mapView.scale * MAP_ZOOM.factor" in text
    assert "mapView.scale / MAP_ZOOM.factor" in text


def test_city_units_are_routed_to_transparent_piece_assets():
    text = APP.read_text(encoding="utf-8")
    for kind in ("village", "town", "city", "fortress"):
        assert f"piece-city-{kind}.png" in text
        assert (IMG / "pieces" / f"piece-city-{kind}.png").exists()
    assert "pieceCityVillage" in text
    assert "pieceCityFortress" in text
