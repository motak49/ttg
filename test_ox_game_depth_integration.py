#!/usr/bin/env python3
"""
OXゲーム深度取得の統合テスト

目的:
  - OXゲーム起動時のボールトラッキング初期化を確認
  - リアルタイム深度取得パイプラインを検証
"""

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

def test_ox_game_depth():
    """OXゲームのリアルタイム深度取得をシミュレート"""
    logger.info("=" * 70)
    logger.info("OXゲーム深度取得統合テスト")
    logger.info("=" * 70)
    
    try:
        from backend.camera_manager import CameraManager
        from backend.screen_manager import ScreenManager
        from backend.ball_tracker import BallTracker
        
        logger.info("\n[初期化] コンポーネントをセットアップ中...")
        cam = CameraManager()
        scr = ScreenManager()
        tracker = BallTracker(scr)
        
        # カメラマネージャーをトラッキャーに設定
        tracker.camera_manager = cam
        logger.info("  ✓ BallTracker に CameraManager を設定")
        
        # カメラ初期化
        logger.info("\n[カメラ初期化] 実機に接続中...")
        if not cam.initialize_camera():
            logger.error("  ✗ カメラ初期化失敗")
            return False
        logger.info("  ✓ カメラ初期化成功")
        
        # スクリーン設定値を設定（テスト用）
        scr.set_screen_depth(1.75)
        logger.info("  ✓ スクリーン深度: 1.75m")
        
        # ボール色設定
        tracker.set_target_color("赤")
        logger.info("  ✓ トラッキング対象色: 赤")
        
        logger.info("\n[フレーム取得テスト] 10 フレーム×リアルタイム深度測定")
        success_count = 0
        depth_values = []
        
        for i in range(10):
            frame = cam.get_frame()
            if frame is None:
                logger.warning(f"  フレーム {i+1}: RGB フレーム取得失敗")
                continue
            
            # ボール検出と深度取得
            result = tracker.detect_ball(frame)
            if result is not None:
                x, y, depth_m = result
                logger.info(f"  フレーム {i+1}: ボール検出 ({x}, {y}) → 深度 {depth_m:.2f}m")
                depth_values.append(depth_m)
                success_count += 1
            else:
                logger.info(f"  フレーム {i+1}: ボール未検出")
        
        logger.info(f"\n[結果] 成功: {success_count}/10 フレーム")
        
        if depth_values:
            avg_depth = sum(depth_values) / len(depth_values)
            min_depth = min(depth_values)
            max_depth = max(depth_values)
            logger.info(f"  深度値統計:")
            logger.info(f"    平均: {avg_depth:.2f}m")
            logger.info(f"    範囲: {min_depth:.2f}m ~ {max_depth:.2f}m")
            logger.info(f"    変動: {max_depth - min_depth:.2f}m")
            
            if min_depth > 0 and max_depth > 0:
                logger.info("  ✓ リアルタイム深度取得: 成功")
            else:
                logger.warning("  ⚠ 一部のフレームでログ値にフォールバック")
        
        cam.close_camera()
        logger.info("\n" + "=" * 70)
        logger.info("統合テスト完了")
        logger.info("=" * 70)
        
        return True
        
    except Exception as e:
        logger.error(f"テスト実行中にエラー: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_ox_game_depth()
    sys.exit(0 if success else 1)
