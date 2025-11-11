# screen_manager.py
import json
import os
from typing import List, Tuple, Optional, Any, Dict, cast

from backend.interfaces import ScreenManagerInterface

class ScreenManager(ScreenManagerInterface):
    """スクリーン管理クラス"""
    
    def __init__(self, log_folder: str = "ScreenAreaLogs"):
        self.log_folder = log_folder
        self.screen_area: Optional[List[Tuple[int, int]]] = None  # 4点の座標 (x1, y1, x2, y2, x3, y3, x4, y4)
        self.screen_depth: Optional[float] = None
        
        # ログフォルダの作成
        if not os.path.exists(self.log_folder):
            os.makedirs(self.log_folder)
        # 深度ログフォルダの作成
        depth_log_folder = "ScreenDepthLogs"
        if not os.path.exists(depth_log_folder):
            os.makedirs(depth_log_folder)
    
    def set_screen_area(self, points: List[Tuple[int, int]]) -> bool:
        """
        スクリーン領域を設定する（4点リスト）
        Args:
            points (List[Tuple[int, int]]): 4 点の座標 [(x1, y1), (x2, y2), (x3, y3), (x4, y4)]
        Returns:
            bool: 設定成功時にTrueを返す
        """
        self.screen_area = points
        self._save_area_log()
        return True

    def set_screen_area_points(self, points: List[Tuple[int, int]]) -> bool:
        """Set screen area directly from a list of four points."""
        self.screen_area = points
        self._save_area_log()
        return True

    def set_screen_area_legacy(self, top_left: Tuple[int, int], bottom_right: Tuple[int, int]) -> bool:
        """Legacy wrapper for backward compatibility."""
        # Compute the four corner points from top-left and bottom-right
        tl = top_left
        tr = (bottom_right[0], top_left[1])
        bl = (top_left[0], bottom_right[1])
        br = bottom_right
        self.screen_area = [tl, tr, bl, br]
        self._save_area_log()
        return True
    
    def get_screen_area(self) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """
        現在設定されているスクリーン領域を取得する
        Returns:
            Tuple[Tuple[int, int], Tuple[int, int]]: スクリーン領域の左上と右下の座標、未設定時はNoneを返す
        """
        if self.screen_area is None:
            return None
        # Return the stored area as top_left and bottom_right tuple for interface compatibility
        return (self.screen_area[0], self.screen_area[3])
    
    def get_screen_area_points(self) -> Optional[List[Tuple[int, int]]]:
        """
        現在設定されているスクリーン領域4点を取得する
        Returns:
            List[Tuple[int, int]]: スクリーン領域の4点座標、未設定時はNoneを返す
        """
        return self.screen_area
    def set_screen_depth(self, depth: float) -> None:
        """
        スクリーン距離を設定する
        Args:
            depth (float): スクリーンまでの距離
        """
        self.screen_depth = depth
        self._save_depth_log()
    
    

    def get_screen_depth(self) -> float:
        """
        設定済みのスクリーンまでの距離を取得する
        Returns:
            float: スクリーンまでの距離
        """
        # Return default value if not set, instead of None to match interface requirement
        return self.screen_depth or 0.0
    
    def _save_area_log(self) -> None:
        """領域ログを保存する"""
        # 4点形式のデータを保存するように変更
        log_data: Dict[str, Any] = {
            "screen_area": self.screen_area,
            "screen_depth": self.screen_depth
        }
        
        log_file = os.path.join(self.log_folder, "area_log.json")
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=4)

    def _save_depth_log(self) -> None:
        """深度ログを保存する"""
        log_data: Dict[str, Any] = {
            "screen_depth": self.screen_depth
        }
        
        depth_log_folder = "ScreenDepthLogs"
        log_file = os.path.join(depth_log_folder, "depth_log.json")
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=4)

    def load_log(self) -> None:
        """ログを読み込む"""
        # 領域ログの読み込み
        log_file = os.path.join(self.log_folder, "area_log.json")
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    data: Any = json.load(f)
                # 新形式（リスト）または旧形式（辞書）の処理
                if isinstance(data, list) and data:
                    latest = cast(Dict[str, Any], data[-1])
                    points_raw = latest.get("points")
                    if isinstance(points_raw, list):
                        points_raw = cast(List[List[int]], points_raw)
                        self.screen_area = [(int(p[0]), int(p[1])) for p in points_raw]
                    else:
                        self.screen_area = None
                elif isinstance(data, dict):
                    screen_data = cast(Dict[str, Any], data)
                    raw_area = screen_data.get("screen_area")
                    if isinstance(raw_area, list):
                        raw_area = cast(List[List[int]], raw_area)
                        self.screen_area = [(int(p[0]), int(p[1])) for p in raw_area]
                    else:
                        self.screen_area = None
                    self.screen_depth = screen_data.get("screen_depth")
                else:
                    self.screen_area = None
            except Exception as e:
                print(f"ログ読み込みエラー: {e}")
                self.screen_area = None

        # 深度ログの読み込み
        depth_log_file = os.path.join("ScreenDepthLogs", "depth_log.json")
        if os.path.exists(depth_log_file):
            try:
                with open(depth_log_file, 'r', encoding='utf-8') as f:
                    depth_data: Any = json.load(f)
                if isinstance(depth_data, dict):
                    depth_dict = cast(Dict[str, Any], depth_data)
                    self.screen_depth = depth_dict.get("screen_depth")
            except Exception as e:
                print(f"深度ログ読み込みエラー: {e}")
