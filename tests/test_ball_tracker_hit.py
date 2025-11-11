"""
BallTracker hit detection unit tests
"""

import numpy as np
from unittest.mock import patch

from backend.ball_tracker import BallTracker
from backend.screen_manager import ScreenManager


def _create_screen_manager_with_area():
    # Define a simple square area covering (0,0) to (100,100)
    sm = ScreenManager()
    points = [(0, 0), (100, 0), (0, 100), (100, 100)]
    sm.set_screen_area_points(points)
    return sm


def test_check_target_hit_inside_polygon():
    screen_manager = _create_screen_manager_with_area()
    tracker = BallTracker(screen_manager)

    # Mock detect_ball to return a point inside the polygon
    mock_result = (50, 50, 1.0)  # x, y, depth

    dummy_frame = np.zeros((10, 10, 3), dtype=np.uint8)
    with patch.object(tracker, "detect_ball", return_value=mock_result):
        hit = tracker.check_target_hit(dummy_frame)

    assert hit == mock_result
    # Ensure internal state is updated
    assert tracker.get_last_reached_coord() == mock_result


def test_check_target_hit_outside_polygon():
    screen_manager = _create_screen_manager_with_area()
    tracker = BallTracker(screen_manager)

    # Mock detect_ball to return a point outside the polygon
    mock_result = (150, 150, 1.0)  # x, y, depth

    dummy_frame = np.zeros((10, 10, 3), dtype=np.uint8)
    with patch.object(tracker, "detect_ball", return_value=mock_result):
        hit = tracker.check_target_hit(dummy_frame)

    assert hit is None
    # Internal state should not have a last reached coordinate
    assert tracker.get_last_reached_coord() is None
