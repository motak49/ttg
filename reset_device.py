#!/usr/bin/env python3
"""
DepthAI デバイスのリセット・クリーンアップスクリプト
X_LINK_DEVICE_ALREADY_IN_USE エラーを解決するための補助ツール
"""

import logging
import time
import sys

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def reset_devices():
    """すべての OAK デバイスをリセット"""
    try:
        import depthai as dai
        logger.info("depthai module imported successfully")
        
        # 接続されているすべてのデバイスを取得
        device_infos = dai.Device.getAllAvailableDevices()
        logger.info(f"Found {len(device_infos)} device(s)")
        
        for device_info in device_infos:
            logger.info(f"Device: {device_info.name}")
            try:
                # デバイスを開く（パイプラインなしで）
                device = dai.Device(device_info)
                logger.info(f"Opened device: {device_info.name}")
                
                # デバイスを閉じる
                device.close()
                logger.info(f"Closed device: {device_info.name}")
                
                # 少し待つ
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error processing device {device_info.name}: {e}")
                continue
        
        logger.info("Device reset completed")
        
    except ImportError:
        logger.error("depthai module not found. Please install it with: pip install depthai")
        return False
    except Exception as e:
        logger.error(f"Error during device reset: {e}")
        return False
    
    return True

if __name__ == "__main__":
    logger.info("Starting DepthAI device reset...")
    success = reset_devices()
    time.sleep(1)
    logger.info("Reset complete. You can now run main.py")
    sys.exit(0 if success else 1)
