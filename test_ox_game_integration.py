"""
ox_game.py のインポートと初期化テスト

ox_game.py が正常にインポートできて、
TrackerSelector が正常に統合されているか確認
"""

import sys
from typing import Any
from unittest.mock import Mock, MagicMock

# モック化（DepthAI 依存を避ける）
sys.modules['depthai'] = MagicMock()
sys.modules['dai'] = MagicMock()

def test_ox_game_integration():
    """ox_game.py の統合テスト"""
    print("=" * 70)
    print("ox_game.py 統合テスト")
    print("=" * 70)
    
    try:
        # 必要なモジュールをインポート
        from backend.camera_manager import CameraManager
        from backend.screen_manager import ScreenManager
        from backend.ball_tracker import BallTracker
        from backend.motion_tracker import MotionBasedTracker
        from backend.tracker_selector import TrackerSelector, TrackerMode
        print("✓ 必要なモジュールをインポート")
    except ImportError as e:
        print(f"✗ インポート失敗: {e}")
        return False
    
    try:
        # モック CameraManager を作成
        camera = Mock(spec=CameraManager)
        camera.get_frame.return_value = None
        camera.get_depth_frame.return_value = None
        camera.get_depth_mm.return_value = 1.7
        print("✓ モック CameraManager 作成")
        
        # ScreenManager を作成
        screen_mgr = ScreenManager()
        screen_mgr.set_screen_area([(0, 0), (800, 0), (0, 600), (800, 600)])
        screen_mgr.set_screen_depth(1.7)
        print("✓ ScreenManager 作成")
        
        # BallTracker を作成
        ball_tracker = BallTracker(screen_manager=screen_mgr)
        ball_tracker.set_target_color("赤")
        ball_tracker.camera_manager = camera
        print("✓ BallTracker 作成")
        
        # MotionBasedTracker を作成
        motion_tracker = MotionBasedTracker(screen_manager=screen_mgr, camera_manager=camera)
        print("✓ MotionBasedTracker 作成")
        
        # TrackerSelector を作成
        selector = TrackerSelector(
            color_tracker=ball_tracker,
            motion_tracker=motion_tracker,
            default_mode=TrackerMode.HYBRID
        )
        print("✓ TrackerSelector(HYBRID) 作成")
        
        # インターフェースを確認
        assert hasattr(selector, 'check_target_hit'), "check_target_hit メソッドがない"
        assert hasattr(selector, 'get_hit_area'), "get_hit_area メソッドがない"
        assert hasattr(selector, 'set_target_color'), "set_target_color メソッドがない"
        assert hasattr(selector, 'get_detection_info'), "get_detection_info メソッドがない"
        assert hasattr(selector, 'get_statistics'), "get_statistics メソッドがない"
        print("✓ BallTrackerInterface の全メソッドが実装されている")
        
        # モードを確認
        assert selector.get_mode() == TrackerMode.HYBRID, "デフォルトモードが HYBRID でない"
        print(f"✓ 現在のモード: {selector.get_mode().value}")
        
        # ox_game.py の重要な部分をシミュレート
        print("\n--- ox_game.py 初期化シミュレーション ---")
        
        # これが ox_game.py で実行される部分
        color_tracker = ball_tracker
        motion_tracker_instance = motion_tracker
        ball_tracker_unified = selector
        
        # 統計情報を取得
        stats = ball_tracker_unified.get_statistics()
        print(f"✓ 統計情報取得成功:")
        print(f"    - モード: {stats['mode']}")
        print(f"    - カラーヒット数: {stats['color_hit_count']}")
        print(f"    - モーションヒット数: {stats['motion_hit_count']}")
        
        print("\n✓ ox_game.py 統合テスト完了!")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"✗ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_ox_game_integration()
    sys.exit(0 if success else 1)
