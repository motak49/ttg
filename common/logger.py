# logger.py
import json
import os
from typing import Dict, Any

class Logger:
    """ログ出力クラス"""

    def __init__(self) -> None:
        # ログフォルダの作成
        self.log_folders = {
            "screen_area": "ScreenAreaLogs",
            "track_ball": "TrackBallLogs",
            "screen_depth": "ScreenDepthLogs"
        }

        for folder in self.log_folders.values():
            if not os.path.exists(folder):
                os.makedirs(folder)

    def log_screen_area(self, area_data: Dict[str, Any]) -> None:
        """スクリーン領域ログを出力"""
        log_file = os.path.join(self.log_folders["screen_area"], "area_log.json")
        self._write_log(log_file, area_data)

    def log_track_ball(self, ball_data: Dict[str, Any]) -> None:
        """ボールトラッキングログを出力"""
        log_file = os.path.join(self.log_folders["track_ball"], "track_ball.json")
        self._write_log(log_file, ball_data)

    def log_screen_depth(self, depth_data: Dict[str, Any]) -> None:
        """スクリーン深度ログを出力"""
        log_file = os.path.join(self.log_folders["screen_depth"], "depth_log.json")
        self._write_log(log_file, depth_data)

    def _write_log(self, log_file: str, data: Dict[str, Any]) -> None:
        """内部ヘルパー：ログを書き込む"""
        try:
            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    # 既存データがリスト形式でない場合は、新しいリストとして初期化
                    if not isinstance(existing_data, list):
                        existing_data = []
            else:
                existing_data = []

            existing_data.append(data)

            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=4)

        except Exception as e:
            print(f"ログ出力エラー: {e}")

    def info(self, message: str) -> None:
        print(f"[INFO] {message}")

    def warning(self, message: str) -> None:
        print(f"[WARNING] {message}")

    def error(self, message: str) -> None:
        print(f"[ERROR] {message}")

# グローバルな Logger インスタンス
logger = Logger()

def get_logger(name: str):
    """Return a logger instance (currently returns the global logger)."""
    return logger
