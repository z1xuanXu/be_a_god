import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "worlds" / "plain-sea-marsh"


def test_plain_sea_marsh_has_ordered_terrain_zones():
    hierarchy = json.loads((WORLD / "base/maps/hierarchy.json").read_text(encoding="utf-8"))
    zones = hierarchy["terrain_zones"]
    assert [zone["terrain"] for zone in zones] == ["plain", "coast", "marsh", "plain"]
    assert [zone["name"] for zone in zones] == ["西岸平原", "黑潮大海", "沉舟险沼", "东岸平原"]
    assert zones[0]["bounds"][:3] == [0, 0, 30]
    assert zones[-1]["bounds"][:3] == [68, 0, 100]


def test_dashboard_units_are_located_characters_only():
    dashboard = json.loads((WORLD / "dashboard/data.json").read_text(encoding="utf-8"))
    pieces = dashboard["pieces"]
    assert {piece["kind"] for piece in pieces} == {"character"}
    assert {piece["location"] for piece in pieces} == {"LOC-001", "LOC-004"}
    assert all("x" in piece and "y" in piece for piece in pieces)


def test_frontend_uses_zones_and_roster_without_map_location_labels():
    app = (ROOT / "be-a-god/assets/frontend-template/app.js").read_text(encoding="utf-8")
    html = (ROOT / "be-a-god/assets/frontend-template/index.html").read_text(encoding="utf-8")
    assert "terrain_zones" in app
    assert "renderUnitRoster" in app
    assert "renderMapDecorations(map, content);" in app
    assert "mapLayers.nodes || []" not in app
    assert "dashboard.pins || []" not in app
    assert 'id="unit-roster"' in html
