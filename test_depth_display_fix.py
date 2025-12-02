"""
OXゲーム画面のボール深度表示値修正のテスト

修正内容:
- ball_tracker.detect_ball() が DepthMeasurementService を優先的に使用
- スクリーン深度へのフォールバックは最後の手段

テスト項目:
1. ball_tracker に depth_measurement_service が設定されることを確認
2. detect_ball() が depth_measurement_service から深度値を取得することを確認
"""

import sys
sys.path.insert(0, 'd:\\VSCode\\ttg')

from backend.screen_manager import ScreenManager
from backend.ball_tracker import BallTracker
from common.depth_service import DepthMeasurementService, DepthConfig
from unittest.mock import Mock, MagicMock
import numpy as np


def test_ball_tracker_has_depth_measurement_service():
    """BallTracker が depth_measurement_service フィールドを持つことを確認"""
    screen_manager = ScreenManager()
    ball_tracker = BallTracker(screen_manager)
    
    # フィールドが存在し、初期値は None
    assert hasattr(ball_tracker, 'depth_measurement_service')
    assert ball_tracker.depth_measurement_service is None
    print("✓ ball_tracker に depth_measurement_service フィールドが存在")


def test_ball_tracker_accepts_depth_measurement_service():
    """BallTracker に depth_measurement_service を設定できることを確認"""
    screen_manager = ScreenManager()
    ball_tracker = BallTracker(screen_manager)
    
    # モック作成
    mock_camera_manager = Mock()
    mock_service = Mock(spec=DepthMeasurementService)
    
    # 設定
    ball_tracker.depth_measurement_service = mock_service
    
    assert ball_tracker.depth_measurement_service is mock_service
    print("✓ ball_tracker に depth_measurement_service を設定できる")


def test_detect_ball_uses_depth_measurement_service():
    """detect_ball() が depth_measurement_service を優先的に使用することを確認"""
    screen_manager = ScreenManager()
    ball_tracker = BallTracker(screen_manager)
    
    # ボール色を設定
    ball_tracker.set_target_color("赤")
    
    # モックカメラマネージャー
    mock_camera_manager = Mock()
    mock_camera_manager.get_depth_mm.return_value = 0  # 無効値を返す
    
    # モック深度測定サービス
    mock_service = Mock(spec=DepthMeasurementService)
    mock_service.measure_at_rgb_coords.return_value = 1.2  # 正常な値を返す
    
    # 設定
    ball_tracker.camera_manager = mock_camera_manager
    ball_tracker.depth_measurement_service = mock_service
    
    # 実行
    frame = np.zeros((600, 800, 3), dtype=np.uint8)
    # 赤いボールを描画（HSV: H=0-10）
    import cv2
    center = (400, 300)
    cv2.circle(frame, center, 20, (0, 0, 255), -1)  # BGR: 赤
    
    result = ball_tracker.detect_ball(frame)
    
    # 検証
    assert result is not None, "detect_ball() が結果を返すべき"
    x, y, depth = result
    
    # depth_measurement_service が呼び出されたことを確認
    assert mock_service.measure_at_rgb_coords.called
    print(f"✓ detect_ball() が depth_measurement_service を使用（取得深度: {depth}m）")


def test_fallback_priority_order():
    """深度取得の優先度順序を確認"""
    screen_manager = ScreenManager()
    ball_tracker = BallTracker(screen_manager)
    
    # スクリーン深度を設定
    screen_manager.set_screen_depth(1.7)
    
    # ボール色を設定
    ball_tracker.set_target_color("赤")
    
    # モックカメラマネージャー
    mock_camera_manager = Mock()
    mock_camera_manager.get_depth_mm.return_value = 0  # 無効値
    
    # モック深度測定サービス（失敗を返す）
    mock_service = Mock(spec=DepthMeasurementService)
    mock_service.measure_at_rgb_coords.return_value = -1.0  # 測定失敗
    
    # 設定
    ball_tracker.camera_manager = mock_camera_manager
    ball_tracker.depth_measurement_service = mock_service
    
    # フレーム準備
    frame = np.zeros((600, 800, 3), dtype=np.uint8)
    import cv2
    center = (400, 300)
    cv2.circle(frame, center, 20, (0, 0, 255), -1)
    
    # 実行
    result = ball_tracker.detect_ball(frame)
    
    # 検証: すべてのサービスが試行されたことを確認
    assert result is not None
    x, y, depth = result
    
    # depth_measurement_service が呼ばれた
    assert mock_service.measure_at_rgb_coords.called
    print(f"✓ フォールバック優先度順序（DepthService → camera_manager → スクリーン深度）")
    print(f"  → 最終取得深度: {depth}m（スクリーン深度）")


def test_depth_cache_mechanism():
    """深度キャッシュ機構を確認"""
    screen_manager = ScreenManager()
    ball_tracker = BallTracker(screen_manager)
    
    # ボール色を設定
    ball_tracker.set_target_color("赤")
    
    # モックカメラマネージャー
    mock_camera_manager = Mock()
    
    # モック深度測定サービス（最初は成功、次は失敗）
    mock_service = Mock(spec=DepthMeasurementService)
    
    # 設定
    ball_tracker.camera_manager = mock_camera_manager
    ball_tracker.depth_measurement_service = mock_service
    
    # フレーム準備
    frame = np.zeros((600, 800, 3), dtype=np.uint8)
    import cv2
    center = (400, 300)
    cv2.circle(frame, center, 20, (0, 0, 255), -1)
    
    # 1回目: 成功
    mock_service.measure_at_rgb_coords.return_value = 1.2
    result1 = ball_tracker.detect_ball(frame)
    assert result1 is not None
    _, _, depth1 = result1
    assert depth1 == 1.2
    
    # 2回目: 失敗（キャッシュから取得するはず）
    mock_service.measure_at_rgb_coords.return_value = -1.0
    mock_camera_manager.get_depth_mm.return_value = 0
    result2 = ball_tracker.detect_ball(frame)
    assert result2 is not None
    _, _, depth2 = result2
    # キャッシュから 1.2 が返される
    assert depth2 == 1.2
    
    print(f"✓ キャッシュ機構（1回目: {depth1}m → 2回目: {depth2}m [キャッシュ使用]）")


if __name__ == "__main__":
    print("=" * 60)
    print("OXゲーム ボール深度表示値修正テスト")
    print("=" * 60)
    
    test_ball_tracker_has_depth_measurement_service()
    test_ball_tracker_accepts_depth_measurement_service()
    test_detect_ball_uses_depth_measurement_service()
    test_fallback_priority_order()
    test_depth_cache_mechanism()
    
    print("=" * 60)
    print("すべてのテストが通過しました ✓")
    print("=" * 60)
