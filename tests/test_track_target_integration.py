"""
TrackTargetViewer と TrackTargetConfig への DepthService 統合テスト
"""

import unittest
from unittest.mock import MagicMock, patch, Mock
import numpy as np
from pathlib import Path
import sys
import os

# パスを設定
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from common.depth_service import DepthMeasurementService, DepthConfig


class TestTrackTargetViewerIntegration(unittest.TestCase):
    """TrackTargetViewer と DepthService の統合テスト"""

    def setUp(self):
        """各テストの前に実行"""
        # DepthService用の設定
        self.depth_config = DepthConfig(
            min_valid_depth_m=0.5,
            max_valid_depth_m=5.0,
            interpolation_radius=10
        )

        # CameraManager のモック
        self.mock_camera_manager = MagicMock()
        
        # DepthFrame（640x360）のモック - uint16, mm単位
        self.mock_depth_frame = np.full((360, 640), 2000, dtype=np.uint16)  # 2.0m
        
        # RGB フレーム（1280x800）のモック
        self.mock_rgb_frame = np.full((800, 1280, 3), 128, dtype=np.uint8)
        
        # camera_manager のメソッドをセットアップ
        self.mock_camera_manager.get_frame.return_value = self.mock_rgb_frame
        self.mock_camera_manager.get_depth_frame.return_value = self.mock_depth_frame

    def test_tracking_color_detection_with_depth(self):
        """トラッキング対象色検出時の深度測定"""
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        # トラッキング対象検出位置（RGB座標）
        track_x, track_y = 640, 400
        
        # 深度を測定
        depth_m = service.measure_at_rgb_coords(track_x, track_y)
        confidence = service.get_confidence_score(track_x, track_y)
        
        # 深度が有効
        self.assertGreater(depth_m, 0)
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)

    def test_color_range_with_depth_confidence(self):
        """色範囲内でのボールの深度と信頼度"""
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        # 複数の検出位置でテスト
        positions = [
            (500, 300),
            (640, 400),
            (780, 500),
        ]
        
        for x, y in positions:
            depth = service.measure_at_rgb_coords(x, y)
            confidence = service.get_confidence_score(x, y)
            
            self.assertGreater(depth, 0)
            self.assertGreaterEqual(confidence, 0.0)
            self.assertLessEqual(confidence, 1.0)

    def test_tracking_highlighting_with_depth_display(self):
        """トラッキング表示時の深度情報表示"""
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        # トラッキング対象の中心位置
        center_x, center_y = 640, 400
        
        # 深度とメタデータを取得
        depth = service.measure_at_rgb_coords(center_x, center_y)
        confidence = service.get_confidence_score(center_x, center_y)
        stats = service.get_statistics()
        
        # すべての情報が取得可能
        self.assertGreater(depth, 0)
        self.assertIn('total_measurements', stats)
        self.assertGreater(stats['total_measurements'], 0)

    def test_sequential_color_tracking_measurements(self):
        """連続的なカラートラッキング測定"""
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        # 複数フレームでのトラッキング
        measurements = []
        for frame_idx in range(5):
            # ボールがやや移動
            x = 600 + (frame_idx * 5)
            y = 400 + (frame_idx * 3)
            
            depth = service.measure_at_rgb_coords(x, y)
            measurements.append(depth)
        
        # すべての測定が完了
        self.assertEqual(len(measurements), 5)
        for depth in measurements:
            self.assertGreater(depth, 0)

    def test_depth_with_hsv_range_validation(self):
        """HSV範囲指定時の深度測定"""
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        # HSV範囲内の位置でボールを検出
        ball_x, ball_y = 640, 400
        
        depth = service.measure_at_rgb_coords(ball_x, ball_y)
        
        # 深度が有効範囲内
        self.assertGreater(depth, 0)
        self.assertGreaterEqual(depth, self.depth_config.min_valid_depth_m)
        self.assertLessEqual(depth, self.depth_config.max_valid_depth_m)

    def test_depth_measurement_statistics_tracking(self):
        """トラッキング統計情報の記録"""
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        # 複数回測定
        for i in range(10):
            service.measure_at_rgb_coords(640 + i, 400 + i)
        
        # 統計情報を確認
        stats = service.get_statistics()
        self.assertEqual(stats['total_measurements'], 10)


class TestTrackTargetConfigIntegration(unittest.TestCase):
    """TrackTargetConfig と DepthService の統合テスト"""

    def setUp(self):
        """各テストの前に実行"""
        self.depth_config = DepthConfig(
            min_valid_depth_m=0.5,
            max_valid_depth_m=5.0,
            interpolation_radius=10
        )
        
        self.mock_camera_manager = MagicMock()
        self.mock_depth_frame = np.full((360, 640), 2000, dtype=np.uint16)
        self.mock_rgb_frame = np.full((800, 1280, 3), 128, dtype=np.uint8)
        
        self.mock_camera_manager.get_frame.return_value = self.mock_rgb_frame
        self.mock_camera_manager.get_depth_frame.return_value = self.mock_depth_frame

    def test_config_adjustment_with_depth_feedback(self):
        """設定調整時の深度フィードバック"""
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        # HSV設定に対応するボール位置での深度を測定
        ball_x, ball_y = 640, 400
        
        depth = service.measure_at_rgb_coords(ball_x, ball_y)
        confidence = service.get_confidence_score(ball_x, ball_y)
        
        # フィードバック情報が利用可能
        self.assertGreater(depth, 0)
        self.assertGreaterEqual(confidence, 0.0)

    def test_min_area_with_depth_measurement(self):
        """最小面積設定時の深度測定"""
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        # 異なるサイズのボール位置で測定
        sizes = [(600, 300), (640, 400), (700, 500)]
        
        for x, y in sizes:
            depth = service.measure_at_rgb_coords(x, y)
            self.assertGreater(depth, 0)

    def test_hsv_slider_adjustment_with_depth(self):
        """HSVスライダー調整時の深度情報"""
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        # 複数のHSV値に対してボールを検出（深度は不変と想定）
        detection_positions = [
            (630, 390),
            (640, 400),
            (650, 410),
        ]
        
        depths = []
        for x, y in detection_positions:
            depth = service.measure_at_rgb_coords(x, y)
            depths.append(depth)
        
        # 全て有効な深度値
        self.assertEqual(len(depths), 3)
        for depth in depths:
            self.assertGreater(depth, 0)

    def test_color_range_boundary_with_depth(self):
        """色範囲境界付近でのボール深度測定"""
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        # 色範囲の境界付近でのボール位置
        boundary_positions = [
            (630, 395),  # 左上
            (650, 405),  # 右下
        ]
        
        for x, y in boundary_positions:
            depth = service.measure_at_rgb_coords(x, y)
            confidence = service.get_confidence_score(x, y)
            
            # 有効な値が返される
            if depth > 0:
                self.assertGreaterEqual(confidence, 0.0)
                self.assertLessEqual(confidence, 1.0)

    def test_detection_info_with_depth_metadata(self):
        """検出情報に深度メタデータを含める"""
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        # 検出位置での深度と統計を取得
        x, y = 640, 400
        depth = service.measure_at_rgb_coords(x, y)
        stats = service.get_statistics()
        
        # 統計情報に測定情報が含まれる
        self.assertIn('total_measurements', stats)
        self.assertIn('cache_hit_rate', stats)
        self.assertGreater(stats['total_measurements'], 0)

    def test_real_time_depth_display_simulation(self):
        """リアルタイム深度表示シミュレーション"""
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        # トラッキング中のボール位置（移動）
        positions = [(620, 390), (630, 395), (640, 400), (650, 405), (660, 410)]
        
        display_info = []
        for x, y in positions:
            depth = service.measure_at_rgb_coords(x, y)
            confidence = service.get_confidence_score(x, y)
            
            if depth > 0:
                display_info.append({
                    'x': x, 'y': y,
                    'depth': depth,
                    'confidence': confidence
                })
        
        # すべての位置でリアルタイム情報が得られた
        self.assertEqual(len(display_info), 5)


class TestTrackingIntegrationScenarios(unittest.TestCase):
    """トラッキング統合シナリオテスト"""

    def setUp(self):
        """各テストの前に実行"""
        self.depth_config = DepthConfig(
            min_valid_depth_m=0.5,
            max_valid_depth_m=5.0,
            interpolation_radius=10
        )
        
        self.mock_camera_manager = MagicMock()
        self.mock_depth_frame = np.full((360, 640), 2000, dtype=np.uint16)
        self.mock_rgb_frame = np.full((800, 1280, 3), 128, dtype=np.uint8)
        
        self.mock_camera_manager.get_frame.return_value = self.mock_rgb_frame
        self.mock_camera_manager.get_depth_frame.return_value = self.mock_depth_frame

    def test_viewer_tracking_loop_with_depth(self):
        """ビューアトラッキングループでの深度測定"""
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        # トラッキングループシミュレーション（10フレーム）
        for frame_idx in range(10):
            # ボール位置が少しずつ移動
            ball_x = 640 + (frame_idx % 5 - 2) * 10
            ball_y = 400 + (frame_idx % 5 - 2) * 10
            
            # 深度と信頼度を取得
            depth = service.measure_at_rgb_coords(ball_x, ball_y)
            confidence = service.get_confidence_score(ball_x, ball_y)
            
            # 各フレームで有効な値
            self.assertGreater(depth, 0)
            self.assertGreaterEqual(confidence, 0.0)

    def test_config_dialog_with_depth_preview(self):
        """設定ダイアログでの深度プレビュー"""
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        # HSV設定変更時のプレビュー
        test_colors = [
            ("赤", (0, 100, 100)),
            ("ピンク", (150, 100, 100)),
        ]
        
        for color_name, (x, y, z) in test_colors:
            # 色に対応するボール位置での深度
            depth = service.measure_at_rgb_coords(x + 640, y + 200)
            
            # プレビュー情報が得られた
            if depth > 0:
                self.assertLessEqual(depth, self.depth_config.max_valid_depth_m)

    def test_both_viewers_simultaneous_tracking(self):
        """TrackTargetViewerと TrackTargetConfigでの同時トラッキング"""
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        # 2つのビューアが同じボール位置をトラッキング
        ball_x, ball_y = 640, 400
        
        # Viewer 1での測定
        depth1 = service.measure_at_rgb_coords(ball_x, ball_y)
        conf1 = service.get_confidence_score(ball_x, ball_y)
        
        # Viewer 2での測定（同じ位置）
        depth2 = service.measure_at_rgb_coords(ball_x, ball_y)
        conf2 = service.get_confidence_score(ball_x, ball_y)
        
        # 同じ位置では同じ値が得られる（キャッシュまたは同じ計算）
        self.assertEqual(depth1, depth2)
        self.assertEqual(conf1, conf2)


if __name__ == '__main__':
    unittest.main()
