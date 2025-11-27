# main.py
"""
Touch The Golf - メインアプリケーション
"""

import sys
import time
import logging
import gc

# depthai の初期化（QApplication 作成前）
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # 前のセッションの depthai モジュールをクリア
    logger.debug("Clearing previous depthai session...")
    modules_to_remove = [
        name for name in list(sys.modules.keys())
        if 'depthai' in name or 'pal' in name or '_depthai' in name
    ]
    for module_name in modules_to_remove:
        logger.debug(f"  Unloading {module_name}")
        del sys.modules[module_name]
    gc.collect()
    
    # depthai を新規インポート
    import depthai as dai
    logger.info("Pre-initializing depthai before PyQt6...")
    
    # デバイスを検出
    devices = dai.Device.getAllAvailableDevices()
    logger.info(f"Devices detected (pre-init): {[d.name for d in devices]}")
    time.sleep(0.5)
except Exception as e:
    logger.warning(f"Pre-initialization warning: {e}")

from PyQt6.QtWidgets import QApplication
from frontend.main_window import MainWindow

def main() -> None:
    """メイン関数"""
    app = QApplication(sys.argv)
    app.setApplicationName("Touch The Golf")
    
    # メインウィンドウの作成と表示
    window = MainWindow()
    window.show()
    
    # アプリケーションの実行
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
