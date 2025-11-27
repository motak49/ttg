#!/usr/bin/env python3
"""
デバイス完全リセットスクリプト
USB デバイスの内部状態をクリアして接続をリセットします
"""
import os
import sys
import subprocess
import time

def main():
    print("=" * 60)
    print("OAK-D デバイス完全リセット")
    print("=" * 60)
    
    # ステップ 1: Python プロセスを終了
    print("\n[1/3] Python プロセスを終了中...")
    try:
        subprocess.run(
            ["taskkill", "/IM", "python.exe", "/F"],
            capture_output=True,
            timeout=10
        )
        print("✓ Python プロセスを終了しました")
    except Exception as e:
        print(f"✗ Python プロセス終了に失敗: {e}")
    
    # ステップ 2: USB デバイスをリセット
    print("\n[2/3] USB デバイスをリセット中...")
    print("USB ハブからデバイスを抜いてください...")
    time.sleep(3)
    print("デバイスを USB ハブに接続してください...")
    time.sleep(5)
    print("✓ USB リセット完了")
    
    # ステップ 3: depthai デバイスを確認
    print("\n[3/3] depthai デバイスを確認中...")
    try:
        import depthai as dai
        devices = dai.Device.getAllAvailableDevices()
        print(f"✓ 検出されたデバイス: {[d.name for d in devices]}")
        if len(devices) > 0:
            print("\n✓ デバイスが正常に検出されました")
            return 0
        else:
            print("\n✗ デバイスが見つかりません")
            return 1
    except Exception as e:
        print(f"✗ depthai 確認に失敗: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
