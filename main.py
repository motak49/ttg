# main.py
"""
Touch The Golf - メインアプリケーション
"""

import sys
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
