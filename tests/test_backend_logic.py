import json
from pathlib import Path
from typing import Tuple

import pytest
from backend.backend_core import BackendCore


@pytest.fixture
def temp_dir(tmp_path: Path) -> str:
    """Provide a temporary directory path for tests."""
    return str(tmp_path)


def test_screen_area_save_and_load(temp_dir: str) -> None:
    core = BackendCore(base_path=temp_dir)
    top_left = (100, 150)
    bottom_right = (400, 350)
    core.set_screen_area(top_left, bottom_right)

    # Verify file exists and content matches
    log_file = Path(temp_dir) / "ScreenAreaLogs" / "area_log.json"
    assert log_file.is_file()
    with open(log_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["top_left"]["x"] == top_left[0]
    assert data["top_left"]["y"] == top_left[1]
    assert data["bottom_right"]["x"] == bottom_right[0]
    assert data["bottom_right"]["y"] == bottom_right[1]

    # Load the saved area with a new instance
    core2 = BackendCore(base_path=temp_dir)
    loaded_area = core2.get_screen_area()
    assert loaded_area is not None
    assert loaded_area["top_left"]["x"] == top_left[0]
    assert loaded_area["top_left"]["y"] == top_left[1]
    assert loaded_area["bottom_right"]["x"] == bottom_right[0]
    assert loaded_area["bottom_right"]["y"] == bottom_right[1]


def test_screen_depth_save_and_load(temp_dir: str) -> None:
    core = BackendCore(base_path=temp_dir)
    depth_value = 1.23
    core.set_screen_depth(depth_value)

    # Verify depth file exists and content matches
    depth_file = Path(temp_dir) / "ScreenDepthLogs" / "depth_log.json"
    assert depth_file.is_file()
    with open(depth_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert isinstance(data["depth"], (int, float))
        # Approx comparison
        assert float(data["depth"]) == pytest.approx(depth_value)

    # New instance should load the persisted depth
    core2 = BackendCore(base_path=temp_dir)
    core2.load_screen_depth()
    assert core2.get_screen_depth() == pytest.approx(depth_value)


def test_get_depth_frame_placeholder() -> None:
    """Placeholder test to ensure get_depth_frame is not implemented."""
    # No actual method exists; the test simply passes.
    assert True
