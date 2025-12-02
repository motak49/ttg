"""
MovingTargetViewer と DepthMeasurementService の統合テスト
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


class TestMovingTargetViewerIntegration(unittest.TestCase):
    """MovingTargetViewer と DepthService の統合テスト"""

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

    def test_depth_measurement_at_ball_position(self):
        """ボール位置での深度測定"""
        # DepthService初期化
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        # ボール検出位置（RGB座標）
        ball_x, ball_y = 640, 400  # RGB フレームの中心付近
        
        # 深度を測定（スケーリングされて深度フレームの座標に変換される）
        depth_m = service.measure_at_rgb_coords(ball_x, ball_y)
        
        # 深度が有効範囲内であることを確認
        self.assertGreater(depth_m, 0)
        self.assertGreaterEqual(depth_m, self.depth_config.min_valid_depth_m)
        self.assertLessEqual(depth_m, self.depth_config.max_valid_depth_m)
        
        # 期待値の確認（2.0mのモック値）
        self.assertAlmostEqual(depth_m, 2.0, places=1)

    def test_confidence_score_at_ball_position(self):
        """ボール位置での信頼度スコア計算"""
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        ball_x, ball_y = 640, 400
        confidence = service.get_confidence_score(ball_x, ball_y)
        
        # 信頼度が 0.0-1.0 の範囲内
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)

    def test_ball_collision_depth_measurement_workflow(self):
        """ボール衝突時の深度測定ワークフロー"""
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        # 複数フレームでのボール位置トラッキング
        ball_positions = [
            (600, 380),
            (620, 390),
            (640, 400),
            (660, 410),
        ]
        
        depths = []
        confidences = []
        
        for x, y in ball_positions:
            depth = service.measure_at_rgb_coords(x, y)
            confidence = service.get_confidence_score(x, y)
            depths.append(depth)
            confidences.append(confidence)
        
        # すべての測定が有効
        self.assertEqual(len(depths), 4)
        for depth in depths:
            self.assertGreater(depth, 0)
        
        # すべての信頼度が有効
        self.assertEqual(len(confidences), 4)
        for conf in confidences:
            self.assertGreaterEqual(conf, 0.0)
            self.assertLessEqual(conf, 1.0)

    def test_depth_with_invalid_region(self):
        """無効な深度領域でのフォールバック"""
        # 一部が無効な深度フレーム（0や65535はDepthAIの無効値）
        invalid_depth_frame = np.full((360, 640), 2000, dtype=np.uint16)
        invalid_depth_frame[100:200, 100:200] = 0  # 無効な領域
        
        self.mock_camera_manager.get_depth_frame.return_value = invalid_depth_frame
        
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        # 最初は有効な深度を測定
        valid_depth = service.measure_at_rgb_coords(640, 400)
        self.assertGreater(valid_depth, 0)
        
        # 無効な領域に移動
        invalid_depth = service.measure_at_rgb_coords(100, 100)
        
        # フォールバック（キャッシュまたはエラー）
        # 最初の有効な値がキャッシュされていれば再利用
        self.assertGreaterEqual(invalid_depth, 0)

    def test_service_statistics_in_viewer_context(self):
        """ビューア利用時のサービス統計情報"""
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        # 複数の測定を実行
        for i in range(5):
            service.measure_at_rgb_coords(640 + i*10, 400 + i*10)
        
        # 統計情報を取得
        stats = service.get_statistics()
        
        # 測定回数、キャッシュ使用状況を確認
        self.assertIn('total_measurements', stats)
        self.assertIn('cache_hits', stats)
        self.assertIn('cache_hit_rate', stats)
        self.assertEqual(stats['total_measurements'], 5)

    def test_coordinate_scaling_rgb_to_depth(self):
        """RGB座標から深度座標へのスケーリング"""
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        # RGB座標（1280x800）を深度座標（640x360）にスケーリング
        # 期待値: scale_x=0.5, scale_y=0.45
        
        rgb_coords = [(1280, 800), (640, 400), (0, 0), (1000, 600)]
        
        for rgb_x, rgb_y in rgb_coords:
            depth_m = service.measure_at_rgb_coords(rgb_x, rgb_y)
            # スケーリングが正しく行われ、深度が返される
            self.assertGreaterEqual(depth_m, 0)

    def test_multiple_sequential_measurements(self):
        """複数フレームでの連続測定"""
        service = DepthMeasurementService(self.mock_camera_manager, self.depth_config)
        
        # 10フレーム分の測定をシミュレート
        measurements = []
        for frame_idx in range(10):
            # ボール位置が少しずつ移動
            ball_x = 600 + (frame_idx * 10)
            ball_y = 400 + (frame_idx * 5)
            
            depth = service.measure_at_rgb_coords(ball_x, ball_y)
            measurements.append(depth)
        
        # 10回の測定が完了
        self.assertEqual(len(measurements), 10)
        
        # すべて有効な値
        for depth in measurements:
            self.assertGreater(depth, 0)

    def test_depth_service_initialization_in_viewer(self):
        """ビューアでの DepthService 初期化"""
        # MovingTargetViewerと同じパターンで初期化
        depth_config = DepthConfig(
            min_valid_depth_m=0.5,
            max_valid_depth_m=5.0,
            interpolation_radius=10
        )
        
        service = DepthMeasurementService(
            self.mock_camera_manager,
            depth_config
        )
        
        # Service が正常に初期化される
        self.assertIsNotNone(service)
        self.assertEqual(service.config.min_valid_depth_m, 0.5)
        self.assertEqual(service.config.max_valid_depth_m, 5.0)


if __name__ == '__main__':
    unittest.main()
