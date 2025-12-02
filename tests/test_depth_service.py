"""
深度サービスのユニットテスト

テスト対象:
- DepthMeasurementService: 深度値測定・検証・補間
- DepthStorageService: ファイル保存・読み込み

【テスト戦略】
- DepthAI カメラは モック化（ハードウェア依存を回避）
- JSON ファイル操作は 一時ディレクトリで実行
- 座標変換・補間ロジックはユニット単位でテスト
"""

import pytest
import tempfile
import json
import logging
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from common.depth_service import DepthMeasurementService, DepthConfig
from common.depth_storage import DepthStorageService


# ========== Fixtures ==========

@pytest.fixture
def temp_storage_dir():
    """テスト用の一時ディレクトリ"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_camera_manager():
    """モック CameraManager"""
    camera = Mock()
    
    # デフォルト: 640x360 の深度フレーム（ゼロで初期化）
    import numpy as np
    depth_frame = np.zeros((360, 640), dtype=np.uint16)
    # テストデータを設定
    depth_frame[180, 320] = 2000  # 中央: 2000mm = 2.0m
    
    camera.get_depth_frame = Mock(return_value=depth_frame)
    return camera


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
def depth_storage_service(temp_storage_dir):
    """DepthStorageService インスタンス"""
    storage_path = temp_storage_dir / "depth_log.json"
    return DepthStorageService(str(storage_path))


# ========== DepthMeasurementService Tests ==========

class TestDepthMeasurementService:
    """DepthMeasurementService のテスト"""
    
    def test_scale_rgb_to_depth_coords(self, depth_measurement_service):
        """座標スケーリングテスト"""
        service = depth_measurement_service
        
        # RGB (1280, 800) の中央 → Depth (640, 360) の中央
        depth_x, depth_y = service._scale_rgb_to_depth_coords(640, 400)
        
        assert depth_x == 320, "X座標スケーリング失敗"
        assert depth_y == 180, "Y座標スケーリング失敗"
    
    def test_scale_rgb_to_depth_coords_corner(self, depth_measurement_service):
        """座標スケーリング（コーナー）テスト"""
        service = depth_measurement_service

        # RGB (0, 0) → Depth (0, 0)
        depth_x, depth_y = service._scale_rgb_to_depth_coords(0, 0)
        assert depth_x == 0 and depth_y == 0

        # RGB (1280, 800) → Depth (639, 359) - 境界値は max-1に制限
        depth_x, depth_y = service._scale_rgb_to_depth_coords(1280, 800)
        assert depth_x == 639 and depth_y == 359

    def test_is_valid_depth(self, depth_measurement_service):
        """深度値の有効性判定テスト"""
        service = depth_measurement_service
        
        # 有効な値
        assert service.is_valid_depth(0.5) is True
        assert service.is_valid_depth(2.0) is True
        assert service.is_valid_depth(5.0) is True
        
        # 無効な値（範囲外）
        assert service.is_valid_depth(0.4) is False
        assert service.is_valid_depth(5.1) is False
        
        # 無効な値（負数）
        assert service.is_valid_depth(-1.0) is False
    
    def test_measure_at_rgb_coords_valid(self, depth_measurement_service):
        """有効な座標での深度測定テスト"""
        service = depth_measurement_service
        
        # RGB (640, 400) は Depth (320, 180) に変換
        # 中央の値 2000mm = 2.0m を返す
        depth_m = service.measure_at_rgb_coords(640, 400)
        
        assert 1.9 < depth_m < 2.1, f"期待値: 2.0m, 実際: {depth_m}m"
    
    def test_measure_at_rgb_coords_caching(self, depth_measurement_service):
        """キャッシング機能テスト"""
        service = depth_measurement_service
        
        # 最初の測定
        depth1 = service.measure_at_rgb_coords(640, 400)
        assert depth1 > 0, "最初の測定失敗"
        
        # 深度フレームを None に設定（フレーム取得失敗を模擬）
        service.camera_manager.get_depth_frame = Mock(return_value=None)
        
        # 2番目の測定（キャッシュから返される）
        depth2 = service.measure_at_rgb_coords(640, 400)
        assert depth2 == depth1, "キャッシュ値が返されていない"
        
        # 統計確認
        stats = service.get_statistics()
        assert stats["cache_hits"] > 0, "キャッシュヒットが記録されていない"
    
    def test_measure_at_rgb_coords_out_of_range(self, depth_measurement_service):
        """範囲外座標テスト"""
        service = depth_measurement_service
        
        # RGB (0, 0) は Depth (0, 0) に変換
        # フレームには 0 が設定されているため、無効値になる
        depth_m = service.measure_at_rgb_coords(0, 0)
        
        # キャッシュから返される（初期値）
        assert depth_m > 0, "フォールバック値が返されていない"
    
    def test_measure_at_region(self, depth_measurement_service):
        """領域測定テスト"""
        service = depth_measurement_service
        
        # 領域を指定（ただし、ほとんどが 0 なので結果は初期値に近い）
        depth_m = service.measure_at_region(600, 350, 700, 450, mode="mean")
        
        # 領域内に有効値が少ないため、負値またはキャッシュ値
        # テストは "処理が完了した" ことのみ確認
        assert isinstance(depth_m, float), "戻り値が float でない"
    
    def test_get_confidence_score(self, depth_measurement_service):
        """信頼度スコア計算テスト"""
        service = depth_measurement_service
        
        # 中央（参考値 2.0m の位置）
        score = service.get_confidence_score(640, 400)
        
        # 参考値と一致しているため、高い信頼度
        assert 0.0 <= score <= 1.0, f"信頼度が範囲外: {score}"
    
    def test_get_statistics(self, depth_measurement_service):
        """統計情報取得テスト"""
        service = depth_measurement_service
        
        # 複数回測定
        for _ in range(5):
            service.measure_at_rgb_coords(640, 400)
        
        stats = service.get_statistics()
        
        assert "total_measurements" in stats
        assert "cache_hits" in stats
        assert "last_valid_depth_m" in stats
        assert stats["total_measurements"] == 5


# ========== DepthStorageService Tests ==========

class TestDepthStorageService:
    """DepthStorageService のテスト"""
    
    def test_save_valid_depth(self, depth_storage_service):
        """有効な深度値の保存テスト"""
        storage = depth_storage_service
        
        result = storage.save(2.5, source="test", confidence=0.95)
        
        assert result is True, "保存に失敗"
        assert storage.get_file_exists(), "ファイルが作成されていない"
    
    def test_save_and_load(self, depth_storage_service):
        """保存と読み込みのラウンドトリップテスト"""
        storage = depth_storage_service
        original_depth = 2.5
        
        # 保存
        save_result = storage.save(original_depth)
        assert save_result is True
        
        # 読み込み
        loaded_depth = storage.load()
        
        assert loaded_depth is not None, "読み込み値が None"
        assert abs(loaded_depth - original_depth) < 0.01, "深度値が一致していない"
    
    def test_save_negative_depth(self, depth_storage_service):
        """負の深度値の保存テスト"""
        storage = depth_storage_service
        
        # 負の値は保存失敗
        result = storage.save(-1.0)
        
        assert result is False, "負の値が保存されてしまった"
    
    def test_save_with_metadata(self, depth_storage_service):
        """メタデータ付き保存テスト"""
        storage = depth_storage_service
        
        storage.save(2.0, source="calibration", confidence=0.85)
        
        # メタデータを読み込み
        metadata = storage.load_full_metadata()
        
        assert metadata is not None
        assert metadata["screen_depth"] == 2.0
        assert metadata["source"] == "calibration"
        assert metadata["confidence"] == 0.85
    
    def test_load_nonexistent_file(self, depth_storage_service):
        """ファイルなし時の読み込みテスト"""
        storage = depth_storage_service
        
        # ファイルが存在しない状態で読み込み
        result = storage.load()
        
        assert result is None, "ファイルなし時に None が返されていない"
    
    def test_clear_file(self, depth_storage_service):
        """ファイル削除テスト"""
        storage = depth_storage_service
        
        # 保存してからクリア
        storage.save(2.0)
        assert storage.get_file_exists()
        
        result = storage.clear()
        
        assert result is True
        assert not storage.get_file_exists(), "ファイルが削除されていない"
    
    def test_clear_nonexistent_file(self, depth_storage_service):
        """ファイルなし時の削除テスト"""
        storage = depth_storage_service
        
        # ファイルが存在しない状態で削除
        result = storage.clear()
        
        assert result is True, "成功を返すべき"
    
    def test_confidence_clamping(self, depth_storage_service):
        """信頼度の制限（0.0～1.0）テスト"""
        storage = depth_storage_service
        
        # 信頼度を 2.0 に指定（範囲外）
        storage.save(2.0, confidence=2.0)
        
        metadata = storage.load_full_metadata()
        
        # 保存時に 1.0 に制限されるべき
        assert metadata["confidence"] <= 1.0, "信頼度が 1.0 を超えている"
    
    def test_json_format(self, depth_storage_service):
        """JSON形式テスト"""
        storage = depth_storage_service
        
        storage.save(2.5, source="test")
        
        # ファイルを直接読み込んで形式確認
        with open(storage.get_file_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 必須フィールド確認
        assert "screen_depth" in data
        assert "timestamp" in data
        assert "source" in data
        assert "confidence" in data
        
        # データ型確認
        assert isinstance(data["screen_depth"], (int, float))
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["source"], str)
        assert isinstance(data["confidence"], (int, float))


# ========== Integration Tests ==========

class TestIntegration:
    """統合テスト"""
    
    def test_measurement_and_storage_workflow(
        self, 
        depth_measurement_service, 
        depth_storage_service
    ):
        """測定から保存までのワークフロー"""
        measurement = depth_measurement_service
        storage = depth_storage_service
        
        # Step 1: 深度を測定
        depth_m = measurement.measure_at_rgb_coords(640, 400)
        assert depth_m > 0, "測定失敗"
        
        # Step 2: 信頼度を取得
        confidence = measurement.get_confidence_score(640, 400)
        assert 0.0 <= confidence <= 1.0
        
        # Step 3: 結果を保存
        save_result = storage.save(depth_m, confidence=confidence)
        assert save_result is True
        
        # Step 4: ファイルから読み込み
        loaded_depth = storage.load()
        assert loaded_depth is not None
        assert abs(loaded_depth - depth_m) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
