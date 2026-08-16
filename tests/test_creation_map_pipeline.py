import json
from pathlib import Path

ROOT = Path(r"F:/be_a_god")
SCRIPTS = ROOT / "be-a-god" / "scripts"


def test_init_world_materializes_map_from_brief():
    text = (SCRIPTS / "init_world.py").read_text(encoding="utf-8")
    assert "materialize_creation_map" in text
    assert "hierarchy.json" in text
    assert "coordinates.json" in text
    assert "map_generation" in text


def test_map_builder_rejects_empty_generated_map_without_explicit_pending_state():
    text = (SCRIPTS / "build_map_layers.py").read_text(encoding="utf-8")
    assert "map_generation" in text
    assert "pending" in text
    assert "status" in text


def test_frontend_does_not_use_pseudo_random_fallback_for_missing_coordinates():
    text = (ROOT / "be-a-god/assets/frontend-template/app.js").read_text(encoding="utf-8")
    assert "fallbackIndex * 19" not in text
    assert "MAP_COORDINATES_PENDING" in text
