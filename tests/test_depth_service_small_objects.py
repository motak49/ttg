"""
小さなボール対応のテスト

テスト対象:
- DepthAI無効フラグ検出（0および65535）
- 補間範囲の拡大（小オブジェクト対応）
- 動的深度フレーム解像度

【テストシナリオ】
- ゴルフボール（5-10px）の深度測定
- DepthAI無効マーカーの自動処理
- 複数ハードウェア解像度への対応
"""

import pytest
import numpy as np
import logging
from unittest.mock import Mock, MagicMock

from common.depth_service import DepthMeasurementService, DepthConfig


# ========== Fixtures ==========

@pytest.fixture
def mock_camera_manager_dynamic_resolution():
    """モック CameraManager - 動的解像度対応"""
    camera = Mock()
    
    # デフォルト: 640x360 の深度フレーム
    depth_frame_640x360 = np.zeros((360, 640), dtype=np.uint16)
    depth_frame_640x360[180, 320] = 2000  # 中央
    
    camera.get_depth_frame = Mock(return_value=depth_frame_640x360)
    camera.depth_frame_height = 360
    camera.depth_frame_width = 640
    
    return camera


@pytest.fixture
def depth_service_small_object(mock_camera_manager_dynamic_resolution):
    """小さなボール対応の深度測定サービス"""
    config = DepthConfig(
        min_valid_depth_m=0.5,
        max_valid_depth_m=5.0,
        interpolation_radius=10,  # デフォルト10px
        reference_depth_m=2.0
    )
    return DepthMeasurementService(mock_camera_manager_dynamic_resolution, config)


# ========== Test Cases ==========

class TestSmallObjectSupport:
    """小さなボール対応テスト"""
    
    def test_depthai_invalid_flag_zero(self, depth_service_small_object):
        """DepthAI無効フラグ（0）の自動検出"""
        service = depth_service_small_object
        
        # 深度フレームに無効フラグ（0）を設定
        depth_frame = np.zeros((360, 640), dtype=np.uint16)
        depth_frame[180, 320] = 0  # 無効フラグ
        depth_frame[179, 320] = 2000  # 近い有効値
        
        # _validate_and_interpolate で無効フラグを検出し、補間する
        result = service._validate_and_interpolate(0, depth_frame, 320, 180)
        
        # 補間により有効な値が返される
        assert result > 0, "無効フラグ0から補間値が取得できるべき"
        assert 0.5 <= result <= 5.0, "補間値は有効範囲内であるべき"
    
    def test_depthai_invalid_flag_65535(self, depth_service_small_object):
        """DepthAI無効フラグ（65535）の自動検出"""
        service = depth_service_small_object
        
        # 深度フレームに無効フラグ（65535）を設定
        depth_frame = np.zeros((360, 640), dtype=np.uint16)
        depth_frame[180, 320] = 65535  # 無効フラグ（uint16最大）
        depth_frame[181, 320] = 2000  # 近い有効値
        
        # _validate_and_interpolate で無効フラグ65535を検出し、補間する
        result = service._validate_and_interpolate(65535, depth_frame, 320, 180)
        
        # 補間により有効な値が返される
        assert result > 0, "無効フラグ65535から補間値が取得できるべき"
        assert 0.5 <= result <= 5.0, "補間値は有効範囲内であるべき"
    
    def test_golf_ball_measurement(self, depth_service_small_object):
        """ゴルフボール（5-10px）の深度測定"""
        service = depth_service_small_object
        
        # ゴルフボール（約8x8px）の周辺に有効値を配置
        depth_frame = np.zeros((360, 640), dtype=np.uint16)
        
        # ボール中心（ほぼ無効）
        depth_frame[180, 320] = 0
        depth_frame[180, 321] = 65535
        
        # ボール周辺に有効値
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                y, x = 180 + dy, 320 + dx
                if 0 <= y < 360 and 0 <= x < 640:
                    if abs(dy) >= 2 or abs(dx) >= 2:  # 外枠のみ
                        depth_frame[y, x] = 2000
        
        # 補間により有効な値が返される
        result = service._interpolate_from_neighbors(depth_frame, 320, 180, is_small_object=True)
        
        assert result > 0, "小さなボールから補間値が取得できるべき"
        assert result == 2.0, f"期待値2.0m、実際={result:.3f}m"
    
    def test_small_object_radius_expansion(self, depth_service_small_object):
        """小オブジェクト補間範囲の拡大"""
        service = depth_service_small_object
        
        # 補間範囲外のやや遠い有効値
        depth_frame = np.zeros((360, 640), dtype=np.uint16)
        
        # 中心が無効
        for dy in range(-5, 6):
            for dx in range(-5, 6):
                y, x = 180 + dy, 320 + dx
                if 0 <= y < 360 and 0 <= x < 640:
                    depth_frame[y, x] = 0  # すべて無効
        
        # 半径15px付近に有効値（通常の半径10pxでは検出できない）
        depth_frame[195, 320] = 3000  # 半径15px
        
        # 通常の補間では失敗
        result_normal = service._interpolate_from_neighbors(depth_frame, 320, 180, is_small_object=False)
        assert result_normal < 0, "通常の補間では失敗するべき（半径が短い）"
        
        # 小オブジェクト補間（範囲2倍）では成功
        result_small = service._interpolate_from_neighbors(depth_frame, 320, 180, is_small_object=True)
        assert result_small > 0, "小オブジェクト補間では成功するべき（範囲が拡大）"
        assert result_small == 3.0, f"期待値3.0m、実際={result_small:.3f}m"
    
    def test_dynamic_resolution_detection(self, mock_camera_manager_dynamic_resolution, depth_service_small_object):
        """動的深度フレーム解像度の検出"""
        service = depth_service_small_object
        
        # 初期状態ではキャッシュが未設定
        assert service._cached_depth_frame_width is None
        assert service._cached_depth_frame_height is None
        
        # 座標スケーリング実行時に解像度を検出
        depth_x, depth_y = service._scale_rgb_to_depth_coords(640, 400)
        
        # キャッシュが設定される
        assert service._cached_depth_frame_width == 640
        assert service._cached_depth_frame_height == 360
    
    def test_dynamic_resolution_fallback(self, depth_service_small_object):
        """フレーム取得失敗時のフォールバック"""
        service = depth_service_small_object
        
        # フレーム取得を失敗させる
        service.camera_manager.get_depth_frame = Mock(return_value=None)
        
        # デフォルト値（640x360）を使用
        depth_x, depth_y = service._scale_rgb_to_depth_coords(640, 400)
        
        # スケーリング計算が成功する（デフォルト値を使用）
        assert depth_x >= 0 and depth_y >= 0
        
        # キャッシュには設定されない
        assert service._cached_depth_frame_width is None
    
    def test_multiple_resolutions(self):
        """複数ハードウェア解像度への対応"""
        service = DepthMeasurementService(Mock(), DepthConfig())
        
        # 320x180（小型デバイス）の場合
        camera_small = Mock()
        depth_frame_small = np.zeros((180, 320), dtype=np.uint16)
        depth_frame_small[90, 160] = 2000
        camera_small.get_depth_frame = Mock(return_value=depth_frame_small)
        
        service.camera_manager = camera_small
        service._cached_depth_frame_width = None
        service._cached_depth_frame_height = None
        
        # 小型デバイスの解像度を検出
        depth_x, depth_y = service._scale_rgb_to_depth_coords(640, 400)
        assert service._cached_depth_frame_width == 320
        assert service._cached_depth_frame_height == 180
    
    def test_invalid_flag_logging(self, depth_service_small_object, caplog):
        """無効フラグ検出時のログ出力"""
        service = depth_service_small_object
        
        depth_frame = np.zeros((360, 640), dtype=np.uint16)
        depth_frame[180, 320] = 2000
        
        with caplog.at_level(logging.DEBUG):
            # 無効フラグ0を検出
            service._validate_and_interpolate(0, depth_frame, 320, 180)
            
            # DepthAI無効フラグ検出のログが記録される
            assert "DepthAI無効フラグ検出" in caplog.text or "補間を試みます" in caplog.text
    
    def test_small_object_median_interpolation(self, depth_service_small_object):
        """小オブジェクト補間で距離加重平均を使用（背景混合対応）"""
        service = depth_service_small_object
        
        # 周辺に複数の有効値（外れ値を含む）
        depth_frame = np.zeros((360, 640), dtype=np.uint16)
        
        # ボール中心は無効
        depth_frame[180, 320] = 0
        
        # 周辺値（バラツキあり）
        # 注意：現在のアルゴリズムは距離加重平均 + 背景フィルタリングを使用
        # これらの値は1500-2100の範囲にあり、段差検出（>200mm）は発動しない
        depth_frame[177, 320] = 1500  # 距離～5.66
        depth_frame[183, 320] = 2000  # 距離～5.66
        depth_frame[180, 317] = 2100  # 距離～3
        depth_frame[180, 323] = 1900  # 距離～3
        depth_frame[179, 320] = 1950  # 距離～1
        
        result = service._interpolate_from_neighbors(depth_frame, 320, 180, is_small_object=True)
        
        # 距離加重平均（外れ値には対応していない）
        # 距離加重式: weight = 1.0 / (distance + 1.0)
        # より近いピクセルほど重みが大きくなる
        # 背景フィルタリングなし（段差が200mm未満）の場合、1500が最小値
        assert 1.4 <= result <= 2.2, f"距離加重平均補間の結果：{result:.3f}m"


class TestIntegrationSmallObjects:
    """小さなボール対応の統合テスト"""
    
    def test_rgb_to_depth_measurement_small_object(self, depth_service_small_object):
        """RGB座標から小オブジェクト深度測定までの統合"""
        service = depth_service_small_object
        
        # 深度フレームをカスタマイズ
        depth_frame = np.zeros((360, 640), dtype=np.uint16)
        
        # ゴルフボール（中心は無効、周辺は有効）
        for dy in range(-8, 9):
            for dx in range(-8, 9):
                y, x = 180 + dy, 320 + dx
                if 0 <= y < 360 and 0 <= x < 640:
                    dist = (dx**2 + dy**2)**0.5
                    if dist > 5:  # 外枠のみ
                        depth_frame[y, x] = 2000
                    else:
                        depth_frame[y, x] = 0  # 中心は無効
        
        service.camera_manager.get_depth_frame = Mock(return_value=depth_frame)
        
        # RGB座標で測定（中心付近）
        # RGB (640, 400) → Depth (320, 180)
        result = service.measure_at_rgb_coords(640, 400)
        
        # 小さなボールでも測定できる
        assert result > 0, "小さなボール測定が失敗"
        assert 1.8 <= result <= 2.2, f"期待範囲外：{result:.3f}m"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
