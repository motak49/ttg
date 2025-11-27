#!/usr/bin/env python3
"""デバイスとパイプライン実行を確認します"""
import depthai as dai
import time

def main():
    devices = dai.Device.getAllAvailableDevices()
    print(f"Found {len(devices)} device(s)")
    
    if len(devices) == 0:
        print("No devices found!")
        return
    
    dev_info = devices[0]
    print(f"Using device: {dev_info.name} (ID: {dev_info.deviceId})")
    
    # デバイス作成
    try:
        device = dai.Device(dev_info)
        print(f"✓ Device created successfully")
        
        # パイプライン作成＋ノード追加
        pipeline = dai.Pipeline()
        color_cam = pipeline.create(dai.node.ColorCamera)
        color_cam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
        
        # 出力キュー作成
        color_cam.video.createOutputQueue(maxSize=4, blocking=False)
        print(f"✓ Pipeline configured successfully")
        
        # パイプライン実行（depthai 3.1.0 対応）
        print(f"Starting pipeline...")
        device.start(pipeline)
        print(f"✓ Pipeline started successfully!")
        
        time.sleep(1)
        device.close()
        print(f"✓ Device closed successfully")
        
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
