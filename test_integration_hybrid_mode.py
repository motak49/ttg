"""
統合テスト: HYBRID モードで色トラッキング & モーション検出を並行実行

テスト内容:
1. モックカメラから画像を読み込み
2. TrackerSelector(HYBRID) で両トラッカーを並行実行
3. 色 vs モーション検出の結果を比較
4. どちらが衝突判定を返すか確認
"""

import sys
import os
from typing import Optional, Tuple

# テスト用のモックオブジェクト
class MockCameraManager:
    """ダミーカメラマネージャー"""
    def __init__(self):
        self.frame_idx = 0
    
    def get_frame(self):
        # テスト用: 1280x800 の赤いグラデーション画像を返す
        import numpy as np
        h, w = 800, 1280
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        # 赤色で矩形を描画
        frame[200:300, 300:400] = [0, 0, 255]  # BGR: 赤
        self.frame_idx += 1
        return frame
    
    def get_depth_frame(self):
        # テスト用: 1280x800 深度フレーム（1700mmで統一）
        import numpy as np
        depth = np.ones((400, 640), dtype=np.uint16) * 1700
        return depth
    
    def get_depth_mm(self, x: int, y: int) -> float:
        # テスト用: 固定値
        return 1700.0


class MockScreenManager:
    """ダミースクリーンマネージャー"""
    def __init__(self):
        self.screen_area = [(0, 0), (1280, 0), (0, 800), (1280, 800)]
        self.screen_depth = 1.7
    
    def get_screen_area_points(self):
        return self.screen_area
    
    def get_screen_depth(self):
        return self.screen_depth
    
    def set_screen_depth(self, depth: float):
        self.screen_depth = depth
    
    def load_log(self):
        pass


def test_hybrid_mode():
    """HYBRID モード統合テスト"""
    print("=" * 70)
    print("統合テスト: HYBRID モード（色 + モーション検出並行）")
    print("=" * 70)
    
    # モックオブジェクト作成
    camera = MockCameraManager()
    screen_mgr = MockScreenManager()
    
    # インポート
    try:
        from backend.ball_tracker import BallTracker
        from backend.motion_tracker import MotionBasedTracker
        from backend.tracker_selector import TrackerSelector, TrackerMode
        print("✓ インポート成功")
    except ImportError as e:
        print(f"✗ インポート失敗: {e}")
        return False
    
    # トラッカー作成
    try:
        color_tracker = BallTracker(screen_manager=screen_mgr)
        color_tracker.camera_manager = camera
        color_tracker.set_target_color("赤")
        print("✓ 色トラッカー作成")
        
        motion_tracker = MotionBasedTracker(screen_manager=screen_mgr, camera_manager=camera)
        print("✓ モーショントラッカー作成")
        
        # TrackerSelector(HYBRID) 初期化
        selector = TrackerSelector(
            color_tracker=color_tracker,
            motion_tracker=motion_tracker,
            default_mode=TrackerMode.HYBRID
        )
        print("✓ TrackerSelector(HYBRID) 初期化")
    except Exception as e:
        print(f"✗ トラッカー初期化失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # テスト実行（複数フレーム）
    print("\n--- テスト実行（フレーム処理） ---")
    for frame_num in range(5):
        try:
            frame = camera.get_frame()
            if frame is None:
                print(f"[Frame {frame_num}] ✗ フレーム取得失敗")
                continue
            
            # HYBRID モードで処理
            result = selector.check_target_hit(frame)
            
            # 結果表示
            if result is None:
                print(f"[Frame {frame_num}] ? ヒットなし")
            else:
                x, y, depth = result
                print(f"[Frame {frame_num}] ✓ ヒット検出! 座標=({x}, {y}), 深度={depth:.2f}m")
            
            # 統計情報を表示
            stats = selector.get_statistics()
            print(f"      統計: カラー={stats['color_hit_count']}, モーション={stats['motion_hit_count']}, ハイブリッド={stats['hybrid_switch_count']}")
            
        except Exception as e:
            print(f"[Frame {frame_num}] ✗ 処理エラー: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print("\n✓ テスト完了!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = test_hybrid_mode()
    sys.exit(0 if success else 1)
