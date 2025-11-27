#!/usr/bin/env python3
"""
depthai 3.1.0 で接続可能なデバイスを完全にリセットするスクリプト
すべてのキャッシュをクリアし、デバイスハンドルを完全に解放
"""

import logging
import time
import sys
import gc

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def forceful_device_cleanup():
    """全デバイスを強制クリーンアップ（複数回実行）"""
    try:
        import depthai as dai
        
        logger.info("Phase 1: Get available devices and close them")
        for attempt in range(5):
            try:
                devices_list = dai.Device.getAllAvailableDevices()
                logger.info(f"Attempt {attempt + 1}: Found {len(devices_list)} device(s)")
                
                for dev_info in devices_list:
                    logger.info(f"  - Device: {dev_info.name}")
                    try:
                        dev = dai.Device(dev_info)
                        dev.close()
                        logger.info(f"    Closed successfully")
                    except Exception as e:
                        logger.warning(f"    Failed to close: {e}")
                
                time.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"  Exception in attempt {attempt + 1}: {e}")
                time.sleep(0.5)
        
        logger.info("Phase 2: Garbage collection")
        gc.collect()
        time.sleep(1)
        
        logger.info("Phase 3: Final device enumeration")
        final_devices = dai.Device.getAllAvailableDevices()
        logger.info(f"Final device count: {len(final_devices)}")
        for dev in final_devices:
            logger.info(f"  - {dev.name}")
        
        logger.info("Device cleanup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("Starting comprehensive device cleanup...")
    success = forceful_device_cleanup()
    time.sleep(2)
    logger.info("Ready to launch main.py")
    sys.exit(0 if success else 1)
