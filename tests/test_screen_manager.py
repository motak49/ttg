# tests/test_screen_manager.py
"""
ScreenManager Tests
===================

スクリーンマネージャーのユニットテスト
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import pytest
from backend.screen_manager import ScreenManager


def test_set_and_get_screen_area(tmp_path: Path) -> None:
    """set_screen_area と get_screen_area_points が正しく動作するか"""
    old_cwd = os.getcwd()
    os.chdir(str(tmp_path))
    try:
        sm = ScreenManager()  # default log_folder
        points = [(0, 0), (100, 0), (100, 200), (0, 200)]
        assert sm.set_screen_area(points) is True
        tl_br = sm.get_screen_area()
        assert tl_br == (points[0], points[3])
        assert sm.get_screen_area_points() == points

        log_file = Path(sm.log_folder) / "area_log.json"
        with open(log_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)
        area = data.get("screen_area")
        assert isinstance(area, list)
        stored_points = [(int(p[0]), int(p[1])) for p in area]
        assert stored_points == points
    finally:
        os.chdir(old_cwd)


def test_set_and_get_screen_depth(tmp_path: Path) -> None:
    """set_screen_depth と get_screen_depth が正しく動作するか"""
    old_cwd = os.getcwd()
    os.chdir(str(tmp_path))
    try:
        sm = ScreenManager()
        depth_val = 2.5
        sm.set_screen_depth(depth_val)

        assert sm.get_screen_depth() == depth_val

        depth_file = Path("ScreenDepthLogs") / "depth_log.json"
        with open(depth_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)
        assert data["screen_depth"] == depth_val
    finally:
        os.chdir(old_cwd)


def test_load_log_old_and_new_format(tmp_path: Path) -> None:
    """古い辞書形式と新しいリスト形式の両方から正しくロードできるか"""
    old_dir = tmp_path / "ScreenAreaLogs"
    old_dir.mkdir()
    # old dict format
    old_content: Dict[str, Any] = {
        "screen_area": [[0, 0], [100, 0], [100, 200], [0, 200]],
        "screen_depth": 1.5,
    }
    with open(old_dir / "area_log.json", "w", encoding="utf-8") as f:
        json.dump(old_content, f)

    old_cwd = os.getcwd()
    os.chdir(str(tmp_path))
    try:
        sm = ScreenManager(log_folder=str(old_dir))
        sm.load_log()
        assert sm.screen_area == [(0, 0), (100, 0), (100, 200), (0, 200)]
        assert sm.screen_depth == 1.5

        # new list format
        new_content: List[Dict[str, Any]] = [
            {
                "points": [[10, 10], [20, 10], [20, 20], [10, 20]],
                "screen_depth": 2.0,
            }
        ]
        with open(old_dir / "area_log.json", "w", encoding="utf-8") as f:
            json.dump(new_content, f)

        sm.load_log()
        assert sm.screen_area == [(10, 10), (20, 10), (20, 20), (10, 20)]
        # depth may stay previous or be None
        assert sm.screen_depth == 1.5 or sm.screen_depth is None
    finally:
        os.chdir(old_cwd)
