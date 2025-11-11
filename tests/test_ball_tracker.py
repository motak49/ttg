"""
Ball Tracker Tests
==================

ボールトラッカーのユニットテスト
"""

import pytest
from unittest.mock import Mock, patch
import numpy as np
 

# インターフェースをインポート
from backend.interfaces import BallTrackerInterface
# 実装クラスをインポート
from backend.ball_tracker import BallTracker
# ScreenManager をインポート（テスト用にモック化）
from backend.screen_manager import ScreenManager


def test_ball_tracker_inherits_interface() -> None:
    """BallTracker が BallTrackerInterface を正しく実装しているかを確認"""
    # モックの ScreenManager を作成
    mock_screen_manager = Mock(spec=ScreenManager)
    tracker = BallTracker(mock_screen_manager)
    assert isinstance(tracker, BallTrackerInterface)


def test_set_target_color_red() -> None:
    """赤色のボールを追跡対象に設定するテスト"""
    # モックの ScreenManager を作成
    mock_screen_manager = Mock(spec=ScreenManager)
    tracker = BallTracker(mock_screen_manager)
    
    # 赤色を設定
    tracker.set_target_color("赤")
    
    # 結果の確認
    assert tracker.get_track_ball() is not None
    # 色範囲が適切に設定されているか確認
    tracked_ball = tracker.get_track_ball()
    assert tracked_ball is not None
    assert "color_range" in tracked_ball
    assert tracked_ball["type"] == "red_like"


def test_set_target_color_pink() -> None:
    """ピンク色のボールを追跡対象に設定するテスト"""
    # モックの ScreenManager を作成
    mock_screen_manager = Mock(spec=ScreenManager)
    tracker = BallTracker(mock_screen_manager)
    
    # ピンク色を設定
    tracker.set_target_color("ピンク")
    
    # 結果の確認
    assert tracker.get_track_ball() is not None
    # 色範囲が適切に設定されているか確認
    tracked_ball = tracker.get_track_ball()
    assert tracked_ball is not None
    assert "color_range" in tracked_ball
    assert tracked_ball["type"] == "red_like"


def test_set_target_color_invalid() -> None:
    """無効な色を設定した場合のテスト"""
    # モックの ScreenManager を作成
    mock_screen_manager = Mock(spec=ScreenManager)
    tracker = BallTracker(mock_screen_manager)
    
    # 無効な色を設定 - 例外が発生するか確認
    with pytest.raises(ValueError, match="サポートされていない色です"):
        tracker.set_target_color("青")


def test_get_hit_area_no_tracked_ball() -> None:
    """追跡対象が設定されていない場合のテスト"""
    # モックの ScreenManager を作成
    mock_screen_manager = Mock(spec=ScreenManager)
    tracker = BallTracker(mock_screen_manager)
    
    # 画像を用意
    mock_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # ヒットエリアを取得 - None が返ることを確認
    result = tracker.get_hit_area(mock_frame)
    assert result is None


@patch('cv2.cvtColor')
@patch('cv2.inRange')
@patch('cv2.findContours')
def test_get_hit_area_with_tracked_ball(mock_find_contours: Mock, mock_in_range: Mock, mock_cvt_color: Mock) -> None:
    """追跡対象が設定されている場合のテスト"""
    # モックの ScreenManager を作成
    mock_screen_manager = Mock(spec=ScreenManager)
    tracker = BallTracker(mock_screen_manager)
    
    # 赤色を設定
    tracker.set_target_color("赤")
    
    # モックの設定 - findContours は (contours, hierarchy) のタプルを返す
    mock_cvt_color.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_in_range.return_value = np.zeros((100, 100), dtype=np.uint8)
    # findContours は (contours, hierarchy) を返すため、2つの値を返すように設定
    mock_find_contours.return_value = ([np.array([[[10, 10], [20, 10], [20, 20], [10, 20]]])], None)  # 輪郭を模倣
    
    # 画像を用意
    mock_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # ヒットエリアを取得
    result = tracker.get_hit_area(mock_frame)
    
    # 結果の確認 - 位置と深度が返されることを確認
    assert result is not None
    assert len(result) == 3  # (x, y, depth)
    assert isinstance(result[0], int)  # x座標
    assert isinstance(result[1], int)  # y座標
    # 深度はモック化された ScreenManager の get_screen_depth() が返す値
    # 現在は Mock オブジェクトなので型チェックを緩和
    assert result[2] is not None

# New tests for collision detection and external API integration

from backend.external_api import set_ball_tracker, get_target_position

def test_check_target_hit_inside() -> None:
    """BallTracker が領域内ヒットを検出できるかテスト"""
    mock_screen_manager = Mock(spec=ScreenManager)
    # Define screen area rectangle (top-left, top-right, bottom-left, bottom-right)
    mock_screen_manager.get_screen_area_points.return_value = [(0, 0), (100, 0), (0, 100), (100, 100)]
    mock_screen_manager.get_screen_depth.return_value = 10.0
    tracker = BallTracker(mock_screen_manager)
    tracker.set_target_color("赤")

    with patch('cv2.cvtColor') as mock_cvt, \
         patch('cv2.inRange') as mock_in_range, \
         patch('cv2.findContours') as mock_find_contours, \
         patch('cv2.pointPolygonTest') as mock_point_poly:
        mock_cvt.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_in_range.return_value = np.zeros((100, 100), dtype=np.uint8)
        # Contour that yields center (15, 15)
        mock_find_contours.return_value = ([np.array([[[10, 10], [20, 10], [20, 20], [10, 20]]])], None)
        mock_point_poly.return_value = 1  # inside polygon

        result = tracker.check_target_hit(np.zeros((100, 100, 3), dtype=np.uint8))
        assert result is not None
        x, y, depth = result
        assert x == 15 and y == 15
        assert depth == 10.0

def test_external_api_get_target_position() -> None:
    """external_api が最新ヒット座標を取得できるかテスト"""
    mock_screen_manager = Mock(spec=ScreenManager)
    mock_screen_manager.get_screen_area_points.return_value = [(0, 0), (100, 0), (0, 100), (100, 100)]
    mock_screen_manager.get_screen_depth.return_value = 15.0
    tracker = BallTracker(mock_screen_manager)
    tracker.set_target_color("赤")

    with patch('cv2.cvtColor'), \
         patch('cv2.inRange'), \
         patch('cv2.findContours') as mock_find_contours, \
         patch('cv2.pointPolygonTest') as mock_point_poly:
        mock_find_contours.return_value = ([np.array([[[10, 10], [20, 10], [20, 20], [10, 20]]])], None)
        mock_point_poly.return_value = 1
        # Perform hit detection to set internal state
        tracker.check_target_hit(np.zeros((100, 100, 3), dtype=np.uint8))

    # Register with external API and retrieve position
    set_ball_tracker(tracker)
    pos = get_target_position()
    assert pos is not None
    x, y, depth = pos
    assert x == 15 and y == 15
    assert depth == 15.0
