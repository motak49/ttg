#!/usr/bin/env python3
"""
DepthAI カメラの最大FPS取得スクリプト（改良版）

カラーカメラ（RGB）とモノクロカメラ（Mono）の最大FPS値を
各解像度ごとに一覧出力します。
ハードウェア上限まで FPS を高く設定し、滑らかな映像投影が可能です。
"""

import depthai as dai
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def get_color_camera_max_fps():
    """
    カラーカメラ（ColorCamera）の最大FPS値を取得
    """
    logger.info("=" * 80)
    logger.info("【カラーカメラ（RGB）の最大FPS一覧】")
    logger.info("=" * 80)
    
    results = {}
    
    try:
        # パイプラインを作成
        pipeline = dai.Pipeline()
        cam_rgb = pipeline.create(dai.node.ColorCamera)
        
        # カラーカメラのメソッドを確認
        logger.info(f"\n利用可能なメソッド（一部）:")
        methods = [m for m in dir(cam_rgb) if 'video' in m.lower() or 'resolution' in m.lower()]
        for m in methods:
            logger.info(f"  - {m}")
        
        # 標準的なカラーカメラ解像度を試す
        standard_resolutions = [
            (1920, 1080, "Full HD (1920x1080)"),
            (1280, 800, "HD (1280x800)"),
            (1280, 720, "HD (1280x720)"),
            (800, 600, "SVGA (800x600)"),
            (640, 480, "VGA (640x480)"),
            (400, 300, "QVGA (400x300)"),
        ]
        
        logger.info(f"\n標準解像度での最大FPS調査:")
        for width, height, desc in standard_resolutions:
            try:
                cam_rgb.setVideoSize(width, height)
                
                # FPS の調査：高い順から試す
                max_fps = None
                for test_fps in [120, 100, 90, 80, 70, 60, 50, 40, 30, 25, 24, 15, 10]:
                    try:
                        cam_rgb.setFps(test_fps)
                        actual_fps = cam_rgb.getFps()
                        logger.info(f"  {desc:25s} | FPS指定: {test_fps:3d} → 実際: {actual_fps:6.1f} FPS ✓")
                        max_fps = actual_fps
                        break  # 最初に成功した値が対応可能な最大値
                    except Exception:
                        logger.debug(f"    FPS {test_fps} は未対応")
                        continue
                
                if max_fps is not None:
                    results[f"{width}x{height}"] = max_fps
                    logger.info(f"    → 最大FPS: {max_fps}")
                
            except Exception as e:
                logger.debug(f"  {desc}: 解像度不対応 ({e})")
        
    except Exception as e:
        logger.error(f"カラーカメラ取得エラー: {e}")
        import traceback
        traceback.print_exc()
    
    return results


def get_mono_camera_max_fps():
    """
    モノクロカメラ（MonoCamera）の最大FPS値を取得
    """
    logger.info("\n" + "=" * 80)
    logger.info("【モノクロカメラ（Mono Left/Right）の最大FPS一覧】")
    logger.info("=" * 80)
    
    results = {}
    
    try:
        # パイプラインを作成
        pipeline = dai.Pipeline()
        mono_left = pipeline.create(dai.node.MonoCamera)
        
        logger.info(f"\nサポートされている解像度:")
        
        # モノクロカメラでサポートされている標準的な解像度
        resolutions = [
            ('THE_400_P', dai.MonoCameraProperties.SensorResolution.THE_400_P),
            ('THE_480_P', dai.MonoCameraProperties.SensorResolution.THE_480_P),
            ('THE_720_P', dai.MonoCameraProperties.SensorResolution.THE_720_P),
            ('THE_800_P', dai.MonoCameraProperties.SensorResolution.THE_800_P),
        ]
        
        for name, resolution in resolutions:
            try:
                mono_left.setResolution(resolution)
                
                # FPS の調査：高い順から試す
                max_fps = None
                for test_fps in [120, 100, 90, 80, 70, 60, 50, 40, 30, 25, 24, 15, 10]:
                    try:
                        mono_left.setFps(test_fps)
                        actual_fps = mono_left.getFps()
                        logger.info(f"  {name:12s} | FPS指定: {test_fps:3d} → 実際: {actual_fps:6.1f} FPS ✓")
                        max_fps = actual_fps
                        break  # 最初に成功した値が対応可能な最大値
                    except Exception:
                        logger.debug(f"    FPS {test_fps} は未対応")
                        continue
                
                if max_fps is not None:
                    results[name] = max_fps
                    logger.info(f"    → 最大FPS: {max_fps}")
                else:
                    logger.warning(f"  {name}: FPS設定エラー")
                
            except Exception as e:
                logger.warning(f"  {name} 設定エラー: {e}")
        
    except Exception as e:
        logger.error(f"モノクロカメラ取得エラー: {e}")
        import traceback
        traceback.print_exc()
    
    return results


def get_device_capabilities():
    """
    DepthAI デバイスの基本情報を取得
    """
    logger.info("=" * 80)
    logger.info("【DepthAI デバイス情報】")
    logger.info("=" * 80)
    
    capabilities = {}
    
    try:
        # 利用可能なデバイスを取得
        devices = dai.Device.getAllAvailableDevices()
        logger.info(f"\n利用可能なデバイス数: {len(devices)}")
        
        for i, device in enumerate(devices):
            logger.info(f"\n  デバイス {i + 1}:")
            logger.info(f"    名前: {device.name}")
            logger.info(f"    MxID: {device.getMxId()}")
            logger.info(f"    USB バージョン: {device.getUsbSpeed()}")
            
            capabilities[f"device_{i}"] = {
                'name': device.name,
                'mx_id': device.getMxId(),
            }
        
    except Exception as e:
        logger.error(f"デバイス情報取得エラー: {e}")
    
    return capabilities


def display_summary(color_fps, mono_fps):
    """
    最大FPS の概要を表示
    """
    logger.info("\n" + "=" * 80)
    logger.info("【推奨FPS設定一覧】")
    logger.info("=" * 80)
    
    if color_fps:
        logger.info("\n【カラーカメラ（RGB）】")
        for resolution, fps in sorted(color_fps.items()):
            logger.info(f"  {resolution:20s} : {fps:7.1f} FPS")
        max_color = max(color_fps.values())
        logger.info(f"\n  🎯 カラーカメラ最大FPS: {max_color:.1f} FPS")
    else:
        logger.info("\n【カラーカメラ（RGB）】")
        logger.info("  ⚠️  FPS情報を取得できませんでした")
    
    if mono_fps:
        logger.info("\n【モノクロカメラ（Mono）】")
        for resolution, fps in sorted(mono_fps.items()):
            logger.info(f"  {resolution:20s} : {fps:7.1f} FPS")
        max_mono = max(mono_fps.values())
        logger.info(f"\n  🎯 モノクロカメラ最大FPS: {max_mono:.1f} FPS")
    else:
        logger.info("\n【モノクロカメラ（Mono）】")
        logger.info("  ⚠️  FPS情報を取得できませんでした")
    
    # 実装の推奨値を表示
    logger.info("\n" + "=" * 80)
    logger.info("【実装に向けた推奨値】")
    logger.info("=" * 80)
    logger.info("""
スムーズな映像投影のため、以下の値をカメラ・フロントエンド設定に反映してください：

📍 backend/camera_manager.py の FPS 設定:""")
    
    if mono_fps:
        max_mono = max(mono_fps.values())
        logger.info(f"    ✓ モノクロ: 最大 {max_mono:.0f} FPS で設定可能")
    
    if color_fps:
        max_color = max(color_fps.values())
        logger.info(f"    ✓ カラー: 最大 {max_color:.0f} FPS で設定可能")
    
    logger.info("""
📍 frontend/main_window.py または frontend/game_logic.py の FPS:
    ✓ フロントエンド表示 FPS = min(カメラ最大FPS, 120)
    ✓ ゲームロジック tick_cross_game の更新周期を同じ FPS で駆動

📍 common/config.py の定数:
    ✓ DEFAULT_FPS, TARGET_FPS などを上記値に更新して一貫性を保つ
""")


if __name__ == '__main__':
    logger.info("\n" + "=" * 80)
    logger.info("DepthAI カメラ最大FPS取得ツール")
    logger.info("=" * 80 + "\n")
    
    try:
        # デバイス情報を取得
        get_device_capabilities()
        
        # カラーカメラの最大FPSを取得
        color_max_fps = get_color_camera_max_fps()
        
        # モノクロカメラの最大FPSを取得
        mono_max_fps = get_mono_camera_max_fps()
        
        # 概要と推奨設定を表示
        display_summary(color_max_fps, mono_max_fps)
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ FPS情報の取得が完了しました")
        logger.info("=" * 80 + "\n")
        
    except Exception as e:
        logger.error(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
