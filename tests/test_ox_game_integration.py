"""
OXゲーム統合テスト

OXゲームとDepthMeasurementServiceの統合を確認するテスト。
実機ハードウェアを使用しない、モック化されたテスト。
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import tempfile

from common.depth_service import DepthMeasurementService, DepthConfig
from common.depth_storage import DepthStorageService


@pytest.fixture
def mock_camera_manager():
    """モック CameraManager"""
    camera = Mock()
    
    # 深度フレーム（640x360）
    depth_frame = np.zeros((360, 640), dtype=np.uint16)
    depth_frame[180, 320] = 2000  # 中央: 2000mm = 2.0m
    depth_frame[180, 310:330] = 2000  # 周辺値
    
    camera.get_depth_frame = Mock(return_value=depth_frame)
    return camera


@pytest.fixture
def mock_screen_manager():
    """モック ScreenManager"""
    screen = Mock()
    screen.get_screen_depth = Mock(return_value=1.75)  # 設定値: 1.75m
    return screen


@pytest.fixture
def depth_measurement_service(mock_camera_manager):
    """DepthMeasurementService インスタンス"""
    config = DepthConfig(
        min_valid_depth_m=0.5,
        max_valid_depth_m=5.0,
        interpolation_radius=10
    )
    return DepthMeasurementService(mock_camera_manager, config)


@pytest.fixture
def temp_storage_dir():
    """一時ディレクトリ"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestOXGameIntegration:
    """OXゲーム統合テスト"""
    
    def test_depth_measurement_at_ball_position(self, depth_measurement_service):
        """ボール検出位置での深度測定テスト"""
        service = depth_measurement_service
        
        # OXゲーム映像の中央 (640, 400) からボールを検出したと仮定
        ball_pos_x, ball_pos_y = 640, 400
        
        # Service経由で深度を測定
        depth_m = service.measure_at_rgb_coords(ball_pos_x, ball_pos_y)
        
        # 期待値: 2.0m（中央の深度フレーム値）
        assert depth_m > 0, "深度測定失敗"
        assert 1.9 < depth_m < 2.1, f"深度値が期待値から逸脱: {depth_m}m"
    
    def test_confidence_score_at_ball_position(self, depth_measurement_service):
        """ボール検出位置での信頼度スコアテスト"""
        service = depth_measurement_service
        
        ball_pos_x, ball_pos_y = 640, 400
        
        # 信頼度を計算
        confidence = service.get_confidence_score(ball_pos_x, ball_pos_y)
        
        # 参考値 2.0m と一致しているため、高い信頼度
        assert 0.0 <= confidence <= 1.0, "信頼度が範囲外"
        assert confidence > 0.7, f"期待以上の信頼度: {confidence:.2f}"
    
    def test_depth_storage_with_game_result(self, temp_storage_dir):
        """ゲーム結果の深度値を保存・読み込みテスト"""
        storage_path = temp_storage_dir / "ox_game_depth.json"
        storage = DepthStorageService(str(storage_path))
        
        # ゲーム中に測定した深度値
        measured_depth = 2.05
        confidence = 0.92
        
        # 保存
        success = storage.save(
            measured_depth,
            source="ox_game_measurement",
            confidence=confidence
        )
        assert success, "深度値の保存失敗"
        
        # 読み込み
        loaded_depth = storage.load()
        assert loaded_depth is not None, "深度値の読み込み失敗"
        assert abs(loaded_depth - measured_depth) < 0.01, "読み込み値が一致しない"
        
        # メタデータ確認
        metadata = storage.load_full_metadata()
        assert metadata is not None
        assert metadata["source"] == "ox_game_measurement"
        assert metadata["confidence"] == 0.92
    
    def test_ball_tracking_depth_workflow(self, depth_measurement_service, temp_storage_dir):
        """ボール追跡から深度保存までの完全ワークフロー"""
        measurement = depth_measurement_service
        storage_path = temp_storage_dir / "tracking_depth.json"
        storage = DepthStorageService(str(storage_path))
        
        # Step 1: ボール検出座標
        detected_x, detected_y = 640, 400
        
        # Step 2: Service経由で深度を測定
        depth_m = measurement.measure_at_rgb_coords(detected_x, detected_y)
        assert depth_m > 0, "深度測定失敗"
        
        # Step 3: 信頼度を計算
        confidence = measurement.get_confidence_score(detected_x, detected_y)
        assert 0.0 <= confidence <= 1.0
        
        # Step 4: ゲーム設定値と比較
        screen_depth_m = 1.75  # ScreenManager.get_screen_depth() より
        depth_diff = abs(depth_m - screen_depth_m)
        
        # 実装では衝突判定に この深度差を使用
        assert depth_diff > 0, "深度差の計算失敗"
        
        # Step 5: 測定結果を保存
        success = storage.save(depth_m, source="ox_game_tracking", confidence=confidence)
        assert success, "深度値の保存失敗"
        
        # Step 6: ファイルから再度読み込み
        loaded = storage.load()
        assert loaded is not None
        assert abs(loaded - depth_m) < 0.01
    
    def test_multiple_measurements_sequential(self, depth_measurement_service):
        """複数フレームでの連続測定テスト"""
        service = depth_measurement_service
        
        # ボール位置が複数フレームで異なる場合をシミュレート
        positions = [
            (640, 400),   # フレーム1: 中央
            (650, 410),   # フレーム2: 右下へ移動
            (630, 390),   # フレーム3: 左上へ戻る
        ]
        
        depths = []
        for x, y in positions:
            depth = service.measure_at_rgb_coords(x, y)
            assert depth > 0, f"フレーム ({x}, {y}) での測定失敗"
            depths.append(depth)
        
        # 複数測定の統計情報
        avg_depth = sum(depths) / len(depths)
        stats = service.get_statistics()
        
        assert stats["total_measurements"] >= len(positions)
        assert abs(avg_depth - 2.0) < 0.5, "平均深度が予期する範囲外"
    
    def test_edge_case_invalid_position(self, depth_measurement_service):
        """エッジケース: 無効な座標での測定テスト"""
        service = depth_measurement_service
        
        # RGB フレーム外の座標
        invalid_x, invalid_y = 0, 0  # フレームコーナー（ゼロ値）
        
        # キャッシュから値が返される（初期値または前回値）
        depth = service.measure_at_rgb_coords(invalid_x, invalid_y)
        assert depth > 0, "エッジケースでキャッシュ値が返されていない"
    
    def test_service_statistics_reporting(self, depth_measurement_service):
        """Service統計情報の報告テスト"""
        service = depth_measurement_service
        
        # 複数回測定
        for i in range(5):
            service.measure_at_rgb_coords(640 + i * 10, 400)
        
        # 統計情報を取得
        stats = service.get_statistics()
        
        # 統計情報の妥当性を確認
        assert stats["total_measurements"] == 5, "測定回数が一致しない"
        assert "cache_hit_rate" in stats
        assert "last_valid_depth_m" in stats
        
        # キャッシュ利用率が報告されている
        cache_rate_str = stats["cache_hit_rate"]
        assert "%" in cache_rate_str, "キャッシュ利用率が報告されていない"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
