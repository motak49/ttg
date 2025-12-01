"""
リアルタイム深度取得テスト

目的: 
- ボール位置でのリアルタイム深度がカメラから正しく取得されているか確認
"""

import sys
import numpy as np

def test_realtime_depth():
    """リアルタイム深度取得のテスト"""
    
    print("=" * 70)
    print("【リアルタイム深度取得テスト】")
    print("=" * 70)
    print()
    
    try:
        from backend.camera_manager import CameraManager
        from backend.screen_manager import ScreenManager
        from backend.ball_tracker import BallTracker
        from common.config import OX_GAME_TARGET_FPS, timer_interval_ms
        
        print("✓ 各モジュールのインポート完了")
        print()
        
        # マネージャー初期化
        print("【初期化開始】")
        camera_manager = CameraManager()
        screen_manager = ScreenManager()
        ball_tracker = BallTracker(screen_manager)
        
        # カメラマネージャーをball_trackerに設定
        ball_tracker.camera_manager = camera_manager
        
        # スクリーン情報をロード
        screen_manager.load_log()
        
        print("✓ CameraManager 初期化")
        print("✓ ScreenManager 初期化 (ログからロード)")
        print("✓ BallTracker 初期化")
        print("✓ ball_tracker.camera_manager 設定")
        print()
        
        # カメラ初期化
        print("【カメラ初期化】")
        if not camera_manager.is_initialized():
            success = camera_manager.initialize_camera()
            if success:
                print("✓ カメラ初期化成功")
            else:
                print("✗ カメラ初期化失敗")
                return False
        else:
            print("✓ カメラ既に初期化済み")
        print()
        
        # ボール色設定
        print("【ボール色設定】")
        ball_tracker.set_target_color("赤")
        print("✓ ボール色: 赤に設定")
        print()
        
        # リアルタイム深度取得テスト（10フレーム）
        print("【リアルタイム深度取得テスト（10フレーム）】")
        print()
        
        depths = []
        for i in range(10):
            try:
                frame = camera_manager.get_frame()
                if frame is None:
                    print(f"フレーム {i+1}: フレーム取得失敗")
                    continue
                
                # detect_ball() でリアルタイム深度取得
                result = ball_tracker.detect_ball(frame)
                if result is not None:
                    x, y, depth = result
                    depths.append(depth)
                    print(f"フレーム {i+1}: ({x:4d}, {y:4d}) → 深度: {depth:.3f}m")
                else:
                    print(f"フレーム {i+1}: ボール検出失敗")
            except Exception as e:
                print(f"フレーム {i+1}: エラー - {e}")
        
        print()
        print("=" * 70)
        print("【テスト結果】")
        print("=" * 70)
        
        if depths:
            print(f"✓ {len(depths)} フレームでボールを検出")
            print(f"  深度の範囲: {min(depths):.3f}m ~ {max(depths):.3f}m")
            print(f"  平均深度: {np.mean(depths):.3f}m")
            
            # 深度変動を確認
            depth_diff = max(depths) - min(depths)
            if depth_diff > 0.05:
                print(f"  ✓ 深度が変動しています（変動幅: {depth_diff:.3f}m）")
                print("     → リアルタイム深度取得が機能しています！")
            else:
                print(f"  ⚠ 深度の変動が小さい（変動幅: {depth_diff:.3f}m）")
                print("     → ボール位置が変わるか、カメラを動かして深度変動を確認してください")
        else:
            print("✗ ボール検出失敗")
            print("  トラッキング対象物（赤ボール）を確認してください")
        
        print()
        print("=" * 70)
        
        # カメラクローズ
        camera_manager.close_camera()
        print("✓ カメラクローズ完了")
        
        return len(depths) > 0
        
    except Exception as e:
        print(f"✗ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_realtime_depth()
    sys.exit(0 if success else 1)
