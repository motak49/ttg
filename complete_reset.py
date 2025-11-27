#!/usr/bin/env python3
"""
カメラデバイス「5.2」の完全なリセットスクリプト
X_LINK_DEVICE_ALREADY_IN_USE エラーを根本的に解決
"""

import os
import sys
import time
import gc

def main():
    print("[1/5] Terminating all Python processes...")
    # PowerShell で Python プロセスを終了
    os.system('taskkill /IM python.exe /F 2>NUL')
    time.sleep(2)
    
    print("[2/5] Waiting for USB to stabilize...")
    time.sleep(3)
    
    print("[3/5] Running depthai device cleanup...")
    try:
        import depthai as dai
        
        # デバイス情報をリセット
        for i in range(5):
            try:
                devices = dai.Device.getAllAvailableDevices()
                print(f"  Attempt {i + 1}: Found {len(devices)} device(s): {[d.name for d in devices]}")
                
                for dev_info in devices:
                    try:
                        dev = dai.Device(dev_info)
                        dev.close()
                        print(f"    Device {dev_info.name} closed")
                    except Exception as e:
                        print(f"    Device {dev_info.name} error: {e}")
                
                time.sleep(0.5)
            except Exception as e:
                print(f"  Error in attempt {i + 1}: {e}")
                time.sleep(0.5)
        
        # ガベージコレクション
        gc.collect()
        time.sleep(1)
        
        # 最終確認
        print("[4/5] Final device enumeration...")
        final_devices = dai.Device.getAllAvailableDevices()
        print(f"  Final device count: {len(final_devices)}")
        for d in final_devices:
            print(f"    - {d.name}")
        
    except Exception as e:
        print(f"  Error: {e}")
        return False
    
    print("[5/5] Reset complete!")
    print("You can now run: python main.py")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
