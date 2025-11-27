#!/usr/bin/env python3
"""
TTG アプリケーション起動スクリプト
前の Python プロセスを確実に終了し、デバイスをリセットしてから起動
"""

import os
import sys
import time
import subprocess

def cleanup_and_launch():
    """クリーンアップとアプリ起動"""
    print("=" * 60)
    print("TTG - Touch The Golf")
    print("=" * 60)
    
    # ステップ 1: すべての Python プロセスを強制終了
    print("\n[1/4] Stopping all Python processes...")
    os.system('taskkill /IM python.exe /F 2>NUL')
    time.sleep(2)
    
    # ステップ 2: USB デバイスリセット待機
    print("[2/4] Waiting for USB device to stabilize...")
    time.sleep(3)
    
    # ステップ 3: アプリケーション起動
    print("[3/4] Starting application...")
    venv_python = r'D:\VSCode\ttg\.venv\Scripts\python.exe'
    app_script = r'd:\VSCode\ttg\main.py'
    
    try:
        # subprocess.run で起動（フォアグラウンド）
        result = subprocess.run([venv_python, app_script], cwd=r'd:\VSCode\ttg')
        print("\n[4/4] Application closed")
        return result.returncode
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(cleanup_and_launch())
