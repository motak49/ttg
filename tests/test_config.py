# tests/test_config.py
"""
config.py のテスト
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

from common.config import OX_GAME_TARGET_FPS, TRACK_TARGET_CONFIG_FPS, TARGET_FPS, TIMER_INTERVAL_MS

def test_config_constants():
    """config.py の定数が正しく定義されているかをテスト"""
    # テスト用の関数
    assert OX_GAME_TARGET_FPS == 120
    assert TRACK_TARGET_CONFIG_FPS == 120
    assert TARGET_FPS == 120
    assert TIMER_INTERVAL_MS == 8  # 1000 / 120 = 8.33... -> int(8.33) = 8
    
    print("config.py のテストに成功しました")

if __name__ == "__main__":
    test_config_constants()
