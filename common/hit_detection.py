"""
前面スクリーンへの衝突検知ロジックを共通化したモジュール

使用例:
    detector = FrontCollisionDetector(screen_manager)
    hit = detector.update_and_check(detected)  # detected: Optional[Tuple[int,int,float]]
    if hit is not None:
        # (x, y, depth) が返る

このクラスは内部で前フレームの位置履歴・衝突状態を保持します。
"""
from typing import Optional, Tuple, List
import numpy as np
import cv2
from common.config import COLLISION_DEPTH_THRESHOLD, ENABLE_ANGLE_COLLISION_CHECK


class FrontCollisionDetector:
    """前面スクリーンへの当たり判定を行うステートフルなヘルパー

    メソッド:
        update_and_check(detected) -> Optional[(x,y,depth)]
        get_last_reached_coord() -> Optional[(x,y,depth)]
        get_last_detected_position() -> Optional[(x,y)]
    """

    def __init__(self, screen_manager, angle_threshold: float = 45.0, dist_tolerance: float = 5.0, enable_angle_check: bool = ENABLE_ANGLE_COLLISION_CHECK):
        self.screen_manager = screen_manager
        self._prev_center: Optional[Tuple[int, int]] = None
        self._last_center: Optional[Tuple[int, int]] = None
        self._last_reached_coord: Optional[Tuple[int, int, float]] = None
        self._collision_state: str = "none"  # "none", "hit_front", "falling"
        self._depth_at_hit: Optional[float] = None
        self._prev_depth: Optional[float] = None
        self.angle_threshold = angle_threshold
        self.dist_tolerance = dist_tolerance
        self._enable_angle_check = enable_angle_check

    def update_and_check(self, detected: Optional[Tuple[int, int, float]]) -> Optional[Tuple[int, int, float]]:
        """
        検出座標を与えて衝突判定を行う。

        Args:
            detected: (x, y, depth) または None

        Returns:
            ヒットが確定した場合は (x, y, depth)、そうでなければ None
        """
        if detected is None:
            # 検出されない場合は内部状態をリセット
            if self._collision_state != "none":
                self._collision_state = "none"
            self._prev_center = self._last_center
            self._last_center = None
            self._last_reached_coord = None  # リセット
            return None

        x, y, depth = detected

        points = self.screen_manager.get_screen_area_points()
        hit_detected = False

        if points and len(points) >= 3:
            poly = np.array(points, dtype=np.int32)
            # ポリゴン内部判定
            inside = cv2.pointPolygonTest(poly, (x, y), False) >= 0
            if inside:
                hit_detected = True
            else:
                # 軌道変化判定（角度判定が有効な場合のみ実行）
                # ENABLE_ANGLE_COLLISION_CHECK = False の場合、この判定はスキップされ、深度のみでの判定になる
                if self._enable_angle_check and self._last_center is not None:
                    v_prev = None
                    if self._prev_center is not None:
                        v_prev = np.array(self._last_center) - np.array(self._prev_center)
                    v_curr = np.array([x, y]) - np.array(self._last_center)
                    if v_prev is not None and np.linalg.norm(v_prev) > 0 and np.linalg.norm(v_curr) > 0:
                        cos_theta = np.clip(np.dot(v_prev, v_curr) / (np.linalg.norm(v_prev) * np.linalg.norm(v_curr)), -1.0, 1.0)
                        angle_deg = float(np.degrees(np.arccos(cos_theta)))
                        dist_to_edge = abs(cv2.pointPolygonTest(poly, (x, y), True))
                        if angle_deg > self.angle_threshold and dist_to_edge <= self.dist_tolerance:
                            hit_detected = True

        # 更新履歴
        self._prev_center = self._last_center
        self._last_center = (x, y)

        # 深度チェック: 深度が0.00の場合は衝突と判定しない（無効な深度値）
        if depth <= 0.0:
            return None
        
#        if hit_detected and depth <= COLLISION_DEPTH_THRESHOLD:
        if hit_detected and depth <= COLLISION_DEPTH_THRESHOLD:
            # 衝突判定と深度判定の両方が満たされた場合のみヒットを返す
            self._collision_state = "none"
            self._last_reached_coord = (x, y, depth)
            return self._last_reached_coord
        else:
            # ヒット判定されなかった場合は状態リセット
            if self._collision_state != "none":
                self._collision_state = "none"
                self._last_reached_coord = None
            return None

    def get_last_reached_coord(self) -> Optional[Tuple[int, int, float]]:
        return self._last_reached_coord

    def get_last_detected_position(self) -> Optional[Tuple[int, int]]:
        return self._last_center
