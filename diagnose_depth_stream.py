#!/usr/bin/env python3
"""
深度ストリームの診断スクリプト

目的:
  - 深度ストリームが正常に初期化されているか確認
  - 深度フレームが取得できるか確認
  - RGB と深度フレームのサイズを確認
  - 座標スケーリングの動作を確認
"""

import logging
import sys
from datetime import timedelta

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from backend.camera_manager import CameraManager
    logger.info("CameraManager をインポートしました")
except Exception as e:
    logger.error(f"CameraManager のインポートに失敗: {e}")
    sys.exit(1)


def main():
    logger.info("=" * 60)
    logger.info("深度ストリーム診断を開始します")
    logger.info("=" * 60)
    
    # カメラマネージャーを初期化
    cam = CameraManager()
    logger.info(f"初期状態: _initialized={cam._initialized}")
    logger.info(f"初期 RGB サイズ: {cam._rgb_frame_width}x{cam._rgb_frame_height}")
    logger.info(f"初期深度サイズ: {cam._depth_frame_width}x{cam._depth_frame_height}")
    
    logger.info("\n[1] カメラ初期化中...")
    result = cam.initialize_camera()
    if not result:
        logger.error("カメラ初期化に失敗しました")
        return False
    
    logger.info(f"初期化後: _initialized={cam._initialized}")
    logger.info(f"  depth_stream={cam.depth_stream}")
    
    logger.info("\n[2] フレーム取得テスト（5 フレーム）...")
    for i in range(5):
        # RGB フレーム取得
        rgb_frame = cam.get_frame()
        if rgb_frame is not None:
            if hasattr(rgb_frame, 'shape'):
                h, w = rgb_frame.shape[:2]
                logger.info(f"  [{i+1}] RGB フレーム: {w}x{h} (キャッシュ: {cam._rgb_frame_width}x{cam._rgb_frame_height})")
            else:
                logger.warning(f"  [{i+1}] RGB フレームが numpy array ではなく: {type(rgb_frame)}")
        else:
            logger.warning(f"  [{i+1}] RGB フレームが None")
        
        # 深度フレーム取得
        depth_frame = cam.get_depth_frame()
        if depth_frame is not None:
            h, w = depth_frame.shape[:2]
            logger.info(f"  [{i+1}] 深度フレーム: {w}x{h} (キャッシュ: {cam._depth_frame_width}x{cam._depth_frame_height})")
            
            # 統計情報を表示
            non_zero = (depth_frame > 0).sum()
            min_depth = depth_frame[depth_frame > 0].min() if non_zero > 0 else 0
            max_depth = depth_frame[depth_frame > 0].max() if non_zero > 0 else 0
            logger.info(f"     有効ピクセル: {non_zero} / {depth_frame.size}, 深度範囲: {min_depth}-{max_depth} mm")
        else:
            logger.warning(f"  [{i+1}] 深度フレームが None")
    
    logger.info("\n[3] 座標スケーリングテスト...")
    test_coords = [
        (640, 400),   # 中央近辺
        (1280, 800),  # 右下
        (0, 0),       # 左上
    ]
    for x, y in test_coords:
        scaled_x, scaled_y = cam._scale_rgb_to_depth_coords(x, y)
        logger.info(f"  RGB({x}, {y}) -> Depth({scaled_x}, {scaled_y})")
    
    logger.info("\n[4] 深度値取得テスト...")
    test_points = [
        (640, 400),   # 中央
        (100, 100),   # 左上
        (1200, 700),  # 右下
    ]
    for x, y in test_points:
        depth_mm = cam.get_depth_mm(x, y)
        depth_m = depth_mm / 1000.0 if depth_mm > 0 else 0.0
        logger.info(f"  RGB({x:4d}, {y:3d}) -> 深度: {depth_mm:7.1f} mm ({depth_m:.2f} m)")
    
    logger.info("\n[5] 複数フレーム深度値取得（リアルタイムシミュレーション）...")
    for i in range(3):
        depth_mm = cam.get_depth_mm(640, 400)
        depth_m = depth_mm / 1000.0 if depth_mm > 0 else 0.0
        logger.info(f"  フレーム {i+1}: {depth_mm:7.1f} mm ({depth_m:.2f} m)")
    
    logger.info("\n" + "=" * 60)
    logger.info("診断完了")
    logger.info("=" * 60)
    
    cam.close_camera()
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
