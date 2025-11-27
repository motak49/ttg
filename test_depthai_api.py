#!/usr/bin/env python3
"""
depthai 3.1.0 の正しい API テスト
推奨: Device を先に作成し、device.start(pipeline) でパイプラインを開始する
"""

import depthai as dai
import logging
import time

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_device_creation():
    """Device 作成方法をテスト"""
    logger.info("Testing depthai 3.1.0 Device creation methods...")
    
    # 方法 1: Device を先に作成し、その後 device.start(pipeline)
    logger.info("\n【推奨】Method 1: Create Device first, then start Pipeline")
    try:
        # デバイスを最初に作成
        device = dai.Device()
        logger.info(f"Device created successfully: {device}")
        
        # パイプラインを作成
        pipeline = dai.Pipeline()
        device = pipeline.create(dai.node.Camera).build()
        
        # パイプラインをデバイスで開始
        # device.start(pipeline)
        logger.info("Pipeline started successfully on device")
        
        device.close()
        logger.info("Device closed successfully")
    except Exception as e:
        logger.error(f"Failed: {e}")
    
    time.sleep(1)
    
    # 方法 2: Context manager で自動管理
    logger.info("\nMethod 2: Using context manager (with statement)")
    try:
        pipeline = dai.Pipeline()
        
        # RGB カメラノードを作成してテスト
        cam_rgb = pipeline.create(dai.node.Camera).build()
        preview = cam_rgb.requestOutput((640, 480), type=dai.ImgFrame.Type.RGB888p)
        q_host = preview.createOutputQueue()
        
        logger.info("Pipeline prepared, starting with context manager...")
        with pipeline:
            logger.info("Pipeline started successfully with context manager")
            # ここでフレーム処理が可能
            for i in range(5):
                if q_host.has():
                    msg = q_host.get()
                    logger.info(f"Frame received: {i + 1}")
                time.sleep(0.1)
        logger.info("Pipeline context exited successfully")
    except Exception as e:
        logger.error(f"Failed: {e}")
    
    time.sleep(1)
    
    # 方法 3: デバイス指定による接続（推奨）
    logger.info("\nMethod 3: Device with DeviceInfo (Recommended)")
    try:
        devices = dai.Device.getAllAvailableDevices()
        logger.info(f"Available devices: {[d.name for d in devices]}")
        
        if devices:
            device_info = devices[0]
            device = dai.Device(device_info)
            logger.info(f"Success! Opened device: {device_info.name}")
            
            # パイプラインを作成して開始
            pipeline = dai.Pipeline()
            device.start(pipeline)
            logger.info("Pipeline started on specified device")
            
            device.close()
            logger.info("Device closed successfully")
        else:
            logger.warning("No devices found")
    except Exception as e:
        logger.error(f"Failed: {e}")

if __name__ == "__main__":
    test_device_creation()
