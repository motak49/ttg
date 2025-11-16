# ball_tracker.py
import cv2
import numpy as np
import json
import os
from typing import Tuple, Optional, Dict, Any, List
from numpy.typing import NDArray
from backend.screen_manager import ScreenManager

from backend.interfaces import BallTrackerInterface
from common.logger import logger


class BallTracker(BallTrackerInterface):
    """ボールトラッキングクラス"""

    def __init__(self, screen_manager: ScreenManager):
        self.screen_manager = screen_manager
        self.tracked_ball: Optional[Dict[str, Any]] = None
        self.ball_history: List[Tuple[int, int]] = []
        # 設定ファイルのパスを定義
        self.config_file = "TrackBallLogs/tracked_ball_config.json"
        # デフォルトの最小面積（ピクセル）※UI から変更可能にする
        self.min_area: int = 30
        # 起動時に設定を読み込む
        self.load_config()
        # 衝突判定用内部状態
        self._last_center: Optional[Tuple[int, int]] = None
        self._prev_center: Optional[Tuple[int, int]] = None
        self._last_reached_coord: Optional[Tuple[int, int, float]] = None

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
            self.tracked_ball = {
                "type": "red_like",
                "sat_low": 100,
                "sat_high": 255,
                "val_low": 100,
                "val_high": 255
            }
        elif color == "ピンク":
            self.tracked_ball = {
                "type": "pink_like",
                "sat_low": 100,
                "sat_high": 255,
                "val_low": 100,
                "val_high": 255
            }
        else:
            raise ValueError("サポートされていない色です。'赤' または 'ピンク' を指定してください")

    def set_track_ball(self, color_range: Tuple[NDArray[np.uint8], NDArray[np.uint8]]) -> bool:
        """
        赤系ボールをトラッキング対象として登録

        Args:
            color_range (Tuple[NDArray[np.uint8], NDArray[np.uint8]]): 色範囲 (lower_bound, upper_bound)

        Returns:
            bool: 登録成功時にTrueを返す
        """
        # 色範囲だけでなく、Saturation と Value の閾値も保存しておくことで
        # UI から動的に調整できるようにする
        self.tracked_ball = {
            "color_range": color_range,   # (lower, upper) は互換性のため残す
            "type": "red_like",
            "sat_low": 100,
            "sat_high": 255,
            "val_low": 100,
            "val_high": 255
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
        mask  = cv2.bitwise_or(mask1, mask2)

        # マスクから輪郭を検出
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
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
        """
        ボールがスクリーン領域に衝突したか判定し、ヒット座標と深度を返す。
        1. ポリゴン内部または境界上にあるか cv2.pointPolygonTest で判定
        2. 条件 A が false の場合、軌道変化角度が大きく、ポリゴン境界付近 (距離 <= DIST_TOLERANCE) ならヒットとみなす。
        """
        result = self.detect_ball(frame)
        if result is None:
            return None
        x, y, depth = result

        # スクリーン領域取得
        points = self.screen_manager.get_screen_area_points()
        hit_detected = False

        if points and len(points) >= 4:
            poly = np.array(points, dtype=np.int32)
            # ポリゴン内部判定
            inside = cv2.pointPolygonTest(poly, (x, y), False) >= 0
            if inside:
                hit_detected = True
            else:
                # 軌道変化判定
                if self._last_center is not None:
                    v_prev = None
                    if self._prev_center is not None:
                        v_prev = np.array(self._last_center) - np.array(self._prev_center)
                    v_curr = np.array([x, y]) - np.array(self._last_center)
                    if v_prev is not None and np.linalg.norm(v_prev) > 0 and np.linalg.norm(v_curr) > 0:
                        # 角度計算
                        cos_theta = np.clip(np.dot(v_prev, v_curr) /
                                            (np.linalg.norm(v_prev) * np.linalg.norm(v_curr)), -1.0, 1.0)
                        angle_deg = float(np.degrees(np.arccos(cos_theta)))
                        # ポリゴン境界からの距離
                        dist_to_edge = abs(cv2.pointPolygonTest(poly, (x, y), True))
                        ANGLE_THRESHOLD = 45.0
                        DIST_TOLERANCE = 5.0
                        if angle_deg > ANGLE_THRESHOLD and dist_to_edge <= DIST_TOLERANCE:
                            hit_detected = True

        # 更新履歴
        self._prev_center = self._last_center
        self._last_center = (x, y)

        if hit_detected:
            self._last_reached_coord = (x, y, depth)
            return self._last_reached_coord
        return None

    def get_last_reached_coord(self) -> Optional[Tuple[int, int, float]]:
        """外部から最新のヒット座標と深度を取得"""
        return self._last_reached_coord

    def save_config(self) -> None:
        """トラッキング対象の設定をファイルに保存する"""
        # 設定データを取得
        config_data = {}
        if self.tracked_ball is not None:
            # 色範囲情報をJSONに保存できる形式に変換
            color_range = self.tracked_ball["color_range"]
            lower_bound, upper_bound = color_range
            config_data = {
                "color": self._get_color_from_range(lower_bound, upper_bound),
                "min_area": self.min_area,
                "sat_low": self.tracked_ball["sat_low"],
                "sat_high": self.tracked_ball["sat_high"],
                "val_low": self.tracked_ball["val_low"],
                "val_high": self.tracked_ball["val_high"]
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
                if color is not None and color in ["赤", "ピンク"]:
                    self.set_target_color(color)
                    # 設定ファイルから min_area と HSV を読み込む
                    self.min_area = config_data.get("min_area", 30)
                    if self.tracked_ball is not None and "sat_low" in config_data:
                        self.tracked_ball["sat_low"] = config_data["sat_low"]
                        self.tracked_ball["sat_high"] = config_data["sat_high"]
                        self.tracked_ball["val_low"] = config_data["val_low"]
                        self.tracked_ball["val_high"] = config_data["val_high"]
                else:
                    # 設定が無効な場合は初期状態（赤）で設定
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
