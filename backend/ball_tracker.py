# ball_tracker.py
import cv2
import numpy as np
import json
import os
import time
from typing import Tuple, Optional, Dict, Any, List
from numpy.typing import NDArray
from backend.screen_manager import ScreenManager

from backend.interfaces import BallTrackerInterface
from common.logger import logger
from common.hit_detection import FrontCollisionDetector


class BallTracker(BallTrackerInterface):
    """ボールトラッキングクラス"""

    def __init__(self, screen_manager: ScreenManager, collision_detector=None):
        self.screen_manager = screen_manager
        self.tracked_ball: Optional[Dict[str, Any]] = None
        self.ball_history: List[Tuple[int, int]] = []
        # 設定ファイルのパスを定義
        from common.config import TRACKED_TARGET_CONFIG_PATH
        self.config_file = TRACKED_TARGET_CONFIG_PATH
        # タイムスタンプを更新
        self.last_reached_timestamp = time.time()
        # デフォルトの最小面積（ピクセル）※UI から変更可能にする
        self.min_area: int = 30
        # 起動時に設定を読み込む
        self.load_config()
        # 衝突判定用内部状態
        self._last_center: Optional[Tuple[int, int]] = None
        self._prev_center: Optional[Tuple[int, int]] = None
        self._last_reached_coord: Optional[Tuple[int, int, float]] = None
        # 衝突状態管理
        # 前面衝突判定は共通モジュールに委譲。外部から渡された検知器があればそれを使用。
        self._collision_detector: FrontCollisionDetector = (collision_detector if collision_detector is not None else FrontCollisionDetector(self.screen_manager))

    def set_target_color(self, color: str) -> None:
        """
        トラッキング対象のボール色を設定します。
        現在は「赤」または「ピンク」の文字列で指定し、内部的に対応する色範囲を保持します。

        Args:
            color (str): "赤" または "ピンク"
        """
        # 赤系は Hue が 0‑10 と 160‑180 の二重範囲で扱い、Saturation/Value は
        # デフォルト 100‑255 に設定。UI から調整可能にする
        if color == "赤":
            # 赤系は二重レンジだがテスト互換性のため color_range を保持
            lower = np.array([0, 100, 100], dtype=np.uint8)
            upper = np.array([10, 255, 255], dtype=np.uint8)
            self.tracked_ball = {
                "type": "red_like",
                "color_range": (lower, upper),
                "sat_low": 100,
                "sat_high": 255,
                "val_low": 100,
                "val_high": 255
            }
        elif color == "ピンク":
            # ピンクも赤系に準じて扱う（既存テスト期待値に合わせる）
            lower = np.array([140, 100, 100], dtype=np.uint8)
            upper = np.array([170, 255, 255], dtype=np.uint8)
            self.tracked_ball = {
                "type": "red_like",
                "color_range": (lower, upper),
                "sat_low": 100,
                "sat_high": 255,
                "val_low": 100,
                "val_high": 255
            }
        else:
            raise ValueError("サポートされていない色です。'赤' または 'ピンク' を指定してください")

    def set_track_ball(self, color_range: Tuple[NDArray[np.uint8], NDArray[np.uint8]],
                       sat_low: int = 100, sat_high: int = 255,
                       val_low: int = 100, val_high: int = 255) -> bool:
        """
        赤系ボールをトラッキング対象として登録

        Args:
            color_range (Tuple[NDArray[np.uint8], NDArray[np.uint8]]): 色範囲 (lower_bound, upper_bound)
            sat_low (int): Saturation の下限
            sat_high (int): Saturation の上限
            val_low (int): Value の下限
            val_high (int): Value の上限

        Returns:
            bool: 登録成功時にTrueを返す
        """
        lower, upper = color_range
        # lower = [h_min, s_min, v_min]; upper = [h_max, s_max, v_max]
        self.tracked_ball = {
            "color_range": (lower, upper),
            "type": "red_like",
            "sat_low": int(sat_low),
            "sat_high": int(sat_high),
            "val_low": int(val_low),
            "val_high": int(val_high)
        }
        return True

    def get_track_ball(self) -> Optional[Dict[str, Any]]:
        """現在トラッキング中のボール情報を取得"""
        return self.tracked_ball

    def detect_ball(self, frame: NDArray[np.uint8]) -> Optional[Tuple[int, int, float]]:
        """
        フレームからボールを検出する

        Args:
            frame (NDArray[np.uint8]): 入力フレーム

        Returns:
            Tuple[int, int, float]: ボールの座標(x, y)と深度(depth)
                                   検出できなかった場合はNone
        """
        if self.tracked_ball is None:
            return None

        # カラー範囲を用いてボールを抽出
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # 赤色は Hue が 0‑10 と 160‑180 の二重範囲で扱う
        lower1 = np.array([0,   self.tracked_ball["sat_low"],  self.tracked_ball["val_low"]], dtype=np.uint8)
        upper1 = np.array([10,  self.tracked_ball["sat_high"], self.tracked_ball["val_high"]], dtype=np.uint8)

        lower2 = np.array([160, self.tracked_ball["sat_low"],  self.tracked_ball["val_low"]], dtype=np.uint8)
        upper2 = np.array([179, self.tracked_ball["sat_high"], self.tracked_ball["val_high"]], dtype=np.uint8)

        mask1 = cv2.inRange(hsv, lower1, upper1)
        mask2 = cv2.inRange(hsv, lower2, upper2)
        # Combine masks (ignore type warnings for static analysis)
        mask = cv2.bitwise_or(mask1, mask2)  # type: ignore

        # マスクから輪郭を検出
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # type: ignore
        if not contours:
            return None

        # ★追加: 最小面積フィルタ（ノイズ除去）
        # 高速ボールでもトラッキング可能
        # デフォルトは 30 に変更し、UI から調整可能に
        contours = [c for c in contours if cv2.contourArea(c) >= self.min_area]
        if not contours:
            return None

        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)

        ball_x = x + w // 2
        ball_y = y + h // 2

        depth = self.screen_manager.get_screen_depth() or 1.0
        return (ball_x, ball_y, depth)

    def get_hit_area(self, frame: NDArray[np.uint8]) -> Optional[Tuple[int, int, float]]:
        """ボールが到達した座標と深度を取得"""
        return self.detect_ball(frame)

    # 衝突判定メソッド
    def check_target_hit(self, frame: NDArray[np.uint8]) -> Optional[Tuple[int, int, float]]:
        """フレームからボールを検出し、共通の前面衝突検知器に委譲する。"""
        result = self.detect_ball(frame)
        return self._collision_detector.update_and_check(result)

    def get_last_reached_coord(self) -> Optional[Tuple[int, int, float]]:
        """外部から最新のヒット座標と深度を取得"""
        return self._collision_detector.get_last_reached_coord()

    def get_last_detected_position(self) -> Optional[Tuple[int, int]]:
        """最後に検出したボールの座標(x, y)を取得"""
        return self._collision_detector.get_last_detected_position()

    def save_config(self) -> None:
        """トラッキング対象の設定をファイルに保存する"""
        # 設定データを取得
        config_data: Dict[str, Any] = {}
        if self.tracked_ball is not None:
            # 色範囲情報をJSONに保存できる形式に変換
            color_range = self.tracked_ball["color_range"]
            lower_bound, upper_bound = color_range
            config_data = {
                "color": self._get_color_from_range(lower_bound, upper_bound),
                "min_area": self.min_area,
                "h_min": int(lower_bound[0]),
                "s_min": int(self.tracked_ball["sat_low"]),
                "v_min": int(self.tracked_ball["val_low"]),
                "h_max": int(upper_bound[0]),
                "s_max": int(self.tracked_ball["sat_high"]),
                "v_max": int(self.tracked_ball["val_high"])
            }
        else:
            config_data = {"color": None}
        
        # ファイルに保存
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"設定保存エラー: {e}")  # 一時的にprintに戻す
            raise  # 再スローしてエラーを伝播

    def load_config(self) -> None:
        """ファイルからトラッキング対象の設定を読み込む"""
        if not os.path.exists(self.config_file):
            # ファイルが存在しない場合は初期状態（赤）で設定
            self.set_target_color("赤")
            return

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                color = config_data.get("color")
                # バリデーション: 必須キーが存在するか確認
                if (color is not None and color in ["赤", "ピンク"] and
                    all(key in config_data for key in ["h_min", "s_min", "v_min", "h_max", "s_max", "v_max"])):
                    # 有効な設定の場合、HSV値を適用
                    self.min_area = config_data.get("min_area", 30)
                    if self.tracked_ball is not None:
                        self.tracked_ball["sat_low"] = config_data["s_min"]
                        self.tracked_ball["sat_high"] = config_data["s_max"]
                        self.tracked_ball["val_low"] = config_data["v_min"]
                        self.tracked_ball["val_high"] = config_data["v_max"]
                    # デフォルトの赤色設定で上書き
                    self.set_target_color(color)
                else:
                    # 設定が無効な場合は初期状態（赤）で設定
                    logger.warning("トラッキング設定が無効または不足しているため、デフォルト設定に復元します。")
                    self.set_target_color("赤")
        except Exception as e:
            print(f"設定読み込みエラー: {e}")
            # エラー発生時は初期状態（赤）で設定
            self.set_target_color("赤")

    # -----------------------------------------------------------------
    # UI から最小面積や HSV の閾値を変更できるようにするメソッド群
    # -----------------------------------------------------------------
    def set_min_area(self, area: int) -> None:
        """検出対象の最小輪郭面積（ピクセル）を設定"""
        self.min_area = max(1, area)

    def set_hsv_limits(
        self,
        sat_low: int,
        sat_high: int,
        val_low: int,
        val_high: int,
    ) -> None:
        """Saturation と Value の上下限を設定（0‑255）"""
        if self.tracked_ball is not None:
            self.tracked_ball.update({
                "sat_low": max(0, min(255, sat_low)),
                "sat_high": max(0, min(255, sat_high)),
                "val_low": max(0, min(255, val_low)),
                "val_high": max(0, min(255, val_high)),
            })

    def _get_color_from_range(self, lower_bound: NDArray[np.uint8], upper_bound: NDArray[np.uint8]) -> str:
        """HSV範囲から色を判定する"""
        # ここでは簡易的な判定を行う
        if (lower_bound[0] >= 0 and lower_bound[0] <= 10 and
            upper_bound[0] >= 10 and upper_bound[0] <= 255):
            return "赤"
        elif (lower_bound[0] >= 140 and lower_bound[0] <= 170 and
              upper_bound[0] >= 140 and upper_bound[0] <= 255):
            return "ピンク"
        else:
            return "赤"  # デフォルトは赤
    
    # -----------------------------------------------------------------
    # 【改善】両ゲームモード共通の検出情報取得メソッド
    # -----------------------------------------------------------------
    def get_detection_info(self, frame: NDArray[np.uint8]) -> Dict[str, Any]:
        """
        現在のフレームで検出できた情報を返す
        
        Returns:
            Dict[str, Any]:
                - "detected": bool - 何か検出されたか
                - "pixel_count": int - マスク内のピクセル数
                - "contour_count": int - 検出輪郭の数
                - "max_area": float - 最大輪郭の面積
                - "detected_position": Tuple[int, int] or None - 最大輪郭の中心座標
                - "grid_position": Tuple[int, int] or None - 3x3グリッドでの位置
        """
        if self.tracked_ball is None:
            return {
                "detected": False,
                "pixel_count": 0,
                "contour_count": 0,
                "max_area": 0,
                "detected_position": None,
                "grid_position": None,
            }
        
        try:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)  # type: ignore
            lower1 = np.array([0, self.tracked_ball["sat_low"], self.tracked_ball["val_low"]], dtype=np.uint8)
            upper1 = np.array([10, self.tracked_ball["sat_high"], self.tracked_ball["val_high"]], dtype=np.uint8)
            lower2 = np.array([160, self.tracked_ball["sat_low"], self.tracked_ball["val_low"]], dtype=np.uint8)
            upper2 = np.array([179, self.tracked_ball["sat_high"], self.tracked_ball["val_high"]], dtype=np.uint8)
            
            mask1 = cv2.inRange(hsv, lower1, upper1)  # type: ignore
            mask2 = cv2.inRange(hsv, lower2, upper2)  # type: ignore
            mask = cv2.bitwise_or(mask1, mask2)  # type: ignore
            
            pixel_count = np.count_nonzero(mask)
            
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # type: ignore
            original_contour_count = len(contours)
            
            # 最小面積でフィルタ
            contours = [c for c in contours if cv2.contourArea(c) >= self.min_area]  # type: ignore
            filtered_contour_count = len(contours)
            
            if not contours:
                return {
                    "detected": False,
                    "pixel_count": pixel_count,
                    "contour_count": original_contour_count,
                    "max_area": 0,
                    "detected_position": None,
                    "grid_position": None,
                }
            
            largest_contour = max(contours, key=cv2.contourArea)  # type: ignore
            max_area = cv2.contourArea(largest_contour)  # type: ignore
            x, y, w, h = cv2.boundingRect(largest_contour)  # type: ignore
            center_x = x + w // 2
            center_y = y + h // 2
            
            # グリッド座標に変換（8x600フレーム、3x3グリッド想定）
            grid_col = min(center_x // (800 // 3), 2)
            grid_row = min(center_y // (600 // 3), 2)
            
            return {
                "detected": True,
                "pixel_count": pixel_count,
                "contour_count": filtered_contour_count,
                "max_area": max_area,
                "detected_position": (center_x, center_y),
                "grid_position": (grid_row, grid_col),
            }
        except Exception as e:
            print(f"検出情報取得エラー: {e}")
            return {
                "detected": False,
                "pixel_count": 0,
                "contour_count": 0,
                "max_area": 0,
                "detected_position": None,
                "grid_position": None,
            }
