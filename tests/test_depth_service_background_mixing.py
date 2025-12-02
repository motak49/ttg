"""
背景混合問題対応テスト

テスト対象:
- 距離加重平均補間
- 段差検出と背景除外
- ボール+背景シーンでの正確な測定

【テストシナリオ】
- ボール（1.2m）とスクリーン背景（1.7m）の混在
- 背景除外後の正確な測定
- 複数深度値の統計処理
"""

import pytest
import numpy as np
import logging
from unittest.mock import Mock

from common.depth_service import DepthMeasurementService, DepthConfig


# ========== Fixtures ==========

@pytest.fixture
def mock_camera_manager_background():
    """モック CameraManager - 背景混合シーン用"""
    camera = Mock()
    
    # デフォルト: 640x360 の深度フレーム
    depth_frame_640x360 = np.zeros((360, 640), dtype=np.uint16)
    depth_frame_640x360[180, 320] = 2000  # 中央
    
    camera.get_depth_frame = Mock(return_value=depth_frame_640x360)
    camera.depth_frame_height = 360
    camera.depth_frame_width = 640
    
    return camera


@pytest.fixture
def depth_service_background(mock_camera_manager_background):
    """背景混合対応の深度測定サービス"""
    config = DepthConfig(
        min_valid_depth_m=0.5,
        max_valid_depth_m=5.0,
        interpolation_radius=10,
        reference_depth_m=2.0
    )
    return DepthMeasurementService(mock_camera_manager_background, config)


# ========== Test Cases ==========

class TestBackgroundMixingFix:
    """背景混合問題対応テスト"""
    
    def test_weighted_average_basic(self, depth_service_background):
        """距離加重平均の基本計算"""
        service = depth_service_background
        
        # テストデータ
        values = [
            (1200, 0),   # 距離0: 1200mm（weight=1.0）
            (1200, 1),   # 距離1: 1200mm（weight=0.5）
            (1200, 2),   # 距離2: 1200mm（weight=0.33）
        ]
        
        result = service._calculate_weighted_average(values)
        
        # すべて1200なので、加重平均も1200
        assert result == 1200, f"期待値1200mm、実際={result}mm"
    
    def test_weighted_average_prefers_close(self, depth_service_background):
        """距離加重平均で近い画素を優先"""
        service = depth_service_background
        
        values = [
            (1200, 0),   # 距離0: 1200mm（weight=1.0）
            (1700, 10),  # 距離10: 1700mm（weight=0.091）
        ]
        
        result = service._calculate_weighted_average(values)
        
        # 1200に大きく重み付け
        # (1200*1.0 + 1700*0.091) / (1.0 + 0.091) ≈ 1267
        assert 1200 <= result <= 1300, f"1200に近い値であるべき: {result}mm"
    
    def test_weighted_average_background_scenario(self, depth_service_background):
        """実際のボール+背景シーン"""
        service = depth_service_background
        
        # ボール周辺（1.2m）: 多い
        # 背景（1.7m）: 少ない
        values = [
            (1200, 1), (1200, 2), (1200, 3), (1200, 4),  # ボール周辺（近い）
            (1210, 5), (1210, 6), (1210, 7),            # ボール周辺（やや遠い）
            (1700, 15), (1700, 16), (1700, 17),         # 背景（遠い）
        ]
        
        result = service._calculate_weighted_average(values)
        
        # ボール側（1200-1210）に重み付けされるべき
        assert 1200 <= result <= 1300, f"ボール側に偏るべき: {result}mm"
    
    def test_filter_background_pixels_no_edge(self, depth_service_background):
        """段差なし（同一オブジェクト）- フィルタなし"""
        service = depth_service_background
        
        # 深度値がすべて近い（段差なし）
        values = [
            (1500, 1), (1500, 2), (1510, 3), (1490, 4),
        ]
        
        result = service._filter_background_pixels(values, 1500)
        
        # フィルタなし（すべて返す）
        assert len(result) == len(values), "段差なしはフィルタしない"
    
    def test_filter_background_pixels_with_edge(self, depth_service_background):
        """段差あり（異なるオブジェクト） - 背景除外"""
        service = depth_service_background
        
        # ボール（1200mm）とスクリーン背景（1700mm）が混在
        values = [
            (1200, 1), (1200, 2), (1200, 3),     # ボール
            (1210, 4), (1210, 5),                # ボール周辺
            (1700, 15), (1700, 16), (1700, 17), # 背景（段差500mm）
        ]
        
        # 参照値は加重平均（ボール側に偏ったもの）
        weighted_avg = service._calculate_weighted_average(values)
        assert 1200 <= weighted_avg <= 1400, f"加重平均がボール側: {weighted_avg}"
        
        # フィルタ実行
        result = service._filter_background_pixels(values, weighted_avg)
        
        # 背景（1700）がほぼ除外される
        depths_filtered = [d for d, _ in result]
        # 参照値±200mmの範囲内に絞られるべき
        # weighted_avg ≈ 1250 なら、1050-1450 範囲
        # 1700 はこの範囲外だから除外
        assert len(result) < len(values), "背景が大幅に削減されるべき"
    
    def test_interpolate_with_background_mixed(self, depth_service_background):
        """補間: ボール+背景混合シーン"""
        service = depth_service_background
        
        # 深度フレーム生成
        depth_frame = np.zeros((360, 640), dtype=np.uint16)
        
        # ボール（1.2m）周辺
        for dy in range(-5, 6):
            for dx in range(-5, 6):
                y, x = 180 + dy, 320 + dx
                if 0 <= y < 360 and 0 <= x < 640:
                    dist = (dx**2 + dy**2)**0.5
                    if dist <= 3:
                        depth_frame[y, x] = 0  # ボール中心は無効
                    elif dist <= 6:
                        depth_frame[y, x] = 1200  # ボール周辺
                    elif dist <= 15:
                        depth_frame[y, x] = 1200
                    else:
                        depth_frame[y, x] = 1700  # 背景
        
        # 補間実行
        result = service._interpolate_from_neighbors(depth_frame, 320, 180, is_small_object=False)
        
        # ボール値（1.2m）が返される（背景1.7mではない）
        assert result > 0, "補間値取得が失敗"
        assert 1.1 <= result <= 1.3, f"ボール側の値であるべき（期待1.2m、実際{result:.3f}m）"
    
    def test_interpolate_background_only(self, depth_service_background):
        """補間: 背景のみ（回帰テスト）"""
        service = depth_service_background
        
        # 背景のみ（1.7m）
        depth_frame = np.zeros((360, 640), dtype=np.uint16)
        for dy in range(-10, 11):
            for dx in range(-10, 11):
                y, x = 180 + dy, 320 + dx
                if 0 <= y < 360 and 0 <= x < 640:
                    depth_frame[y, x] = 1700
        
        # 中心を無効に
        depth_frame[180, 320] = 0
        
        result = service._interpolate_from_neighbors(depth_frame, 320, 180, is_small_object=False)
        
        # 背景値が返される
        assert 1.6 <= result <= 1.8, f"背景値であるべき（期待1.7m、実際{result:.3f}m）"
    
    def test_weighted_average_zero_distance(self, depth_service_background):
        """距離0画素を含む場合（ゼロ除算対策）"""
        service = depth_service_background
        
        values = [
            (1200, 0),   # 距離0（ゼロ除算対策が必要）
            (1200, 5),
        ]
        
        result = service._calculate_weighted_average(values)
        
        # ゼロ除算エラーなく計算
        assert result == 1200, f"正常計算: {result}mm"
    
    def test_filter_background_small_sample(self, depth_service_background):
        """フィルタ: サンプル数少ない場合"""
        service = depth_service_background
        
        # サンプル2個（少ない）
        values = [(1200, 1), (1700, 10)]
        
        result = service._filter_background_pixels(values, 1400)
        
        # サンプル少ないのでフィルタしない
        assert len(result) == 2, "少ないサンプルはフィルタしない"


class TestIntegrationBackgroundMixing:
    """背景混合対応の統合テスト"""
    
    def test_rgb_to_depth_with_background(self, depth_service_background):
        """RGB座標から背景混合シーンでの測定"""
        service = depth_service_background
        
        # ボール（1.2m）+背景（1.7m）フレーム
        depth_frame = np.zeros((360, 640), dtype=np.uint16)
        
        # ボール領域（中心のみ無効）
        for dy in range(-8, 9):
            for dx in range(-8, 9):
                y, x = 180 + dy, 320 + dx
                if 0 <= y < 360 and 0 <= x < 640:
                    dist = (dx**2 + dy**2)**0.5
                    if dist <= 2:
                        depth_frame[y, x] = 0      # 中心無効
                    elif dist <= 7:
                        depth_frame[y, x] = 1200   # ボール（1.2m）
                    else:
                        depth_frame[y, x] = 1700   # 背景（1.7m）
        
        service.camera_manager.get_depth_frame = Mock(return_value=depth_frame)
        
        # RGB座標で測定（中心付近）
        result = service.measure_at_rgb_coords(640, 400)
        
        # ボール値が返される
        assert result > 0, "測定成功"
        assert 1.1 <= result <= 1.3, f"ボール側の値（期待1.2m、実際{result:.3f}m）"
    
    def test_multiple_depth_layers(self, depth_service_background):
        """複数の深度層（より現実的なボール+背景比）"""
        service = depth_service_background
        
        depth_frame = np.zeros((360, 640), dtype=np.uint16)
        
        # より現実的な配置：ボール中心のみ無効、その周辺はボール、外側は背景
        # 補間半径は10pxなので、その範囲内でボールが多数派
        for dy in range(-10, 11):
            for dx in range(-10, 11):
                y, x = 180 + dy, 320 + dx
                if 0 <= y < 360 and 0 <= x < 640:
                    dist = (dx**2 + dy**2)**0.5
                    if dist <= 2:
                        depth_frame[y, x] = 0          # ボール中心無効
                    elif dist <= 6:
                        depth_frame[y, x] = 1200       # ボール（1.2m）
                    else:
                        depth_frame[y, x] = 1700       # 背景（1.7m）
        
        service.camera_manager.get_depth_frame = Mock(return_value=depth_frame)
        
        result = service._interpolate_from_neighbors(depth_frame, 320, 180, is_small_object=False)
        
        # 補間範囲10px内ではボールが支配的（距離2-6pxで多い）
        assert result > 0, "補間成功"
        # フィルタで背景が除外される可能性が高い
        assert 1.1 <= result <= 1.4, f"ボール側が優先される（実際{result:.3f}m）"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
