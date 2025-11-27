#!/usr/bin/env python3
"""
DepthAI デバイスの強力なリセット・クリーンアップスクリプト
X_LINK_DEVICE_ALREADY_IN_USE エラーを解決するための補助ツール
"""

import logging
import time
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def reset_devices_forcefully():
    """すべての OAK デバイスを強力にリセット"""
    try:
        import depthai as dai
        logger.info("depthai module imported successfully")
        
        logger.info("Attempting to release all device connections...")
        
        # すべての利用可能デバイスを取得
        device_infos = dai.Device.getAllAvailableDevices()
        logger.info(f"Found {len(device_infos)} available device(s)")
        
        if len(device_infos) == 0:
            logger.warning("No available devices found. Trying to open default device...")
            try:
                device = dai.Device()
                logger.info("Default device opened")
                device.close()
                logger.info("Default device closed")
            except Exception as e:
                logger.warning(f"Could not open default device: {e}")
        else:
            for device_info in device_infos:
                logger.info(f"Processing device: {device_info.name}")
                try:
                    # Config を使用した適切なデバイス初期化
                    config = dai.Device.Config()
                    device = dai.Device(config, device_info)
                    logger.info(f"Device {device_info.name} opened successfully")
                    
                    device.close()
                    logger.info(f"Device {device_info.name} closed successfully")
                    time.sleep(1)
                    
                except Exception as e:
                    logger.warning(f"Error with device {device_info.name}: {e}")
                    try:
                        # 代替方法: デバイス名で開く
                        device = dai.Device(device_info.name)
                        logger.info(f"Device {device_info.name} opened via name")
                        device.close()
                        logger.info(f"Device {device_info.name} closed")
                        time.sleep(1)
                    except Exception as e2:
                        logger.warning(f"Alternative method also failed: {e2}")
        
        logger.info("Device reset completed")
        time.sleep(2)
        return True
        
    except ImportError:
        logger.error("depthai module not found")
        return False
    except Exception as e:
        logger.error(f"Error during device reset: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting DepthAI device reset (forceful)...")
    success = reset_devices_forcefully()
    logger.info("Reset complete. You can now run main.py")
    sys.exit(0 if success else 1)
