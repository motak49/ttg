"""
深度軸ベースの移動物体トラッカー（MotionBasedTracker）

従来の色ベースのボールトラッキングではなく、深度軸上での物体移動
（スクリーンに向かって近づく物体）を検知します。

特徴:
- 色不依存 → 照度変動に強い
- 深度差分で物体移動を直接検知
- 移動していない背景は自動除外
- 複数物体対応可能

Usage:
    tracker = MotionBasedTracker(screen_manager, camera_manager)
    hit = tracker.check_target_hit(frame)  # None or (x, y, depth)
"""

import logging
from typing import Optional, Tuple, Dict, Any, List
from collections import deque

import cv2
import numpy as np
from numpy.typing import NDArray

from backend.screen_manager import ScreenManager
from backend.interfaces import BallTrackerInterface
from common.logger import logger


class MotionBasedTracker(BallTrackerInterface):
    """深度軸ベースの移動物体トラッキング"""
    
    def __init__(self, screen_manager: ScreenManager, camera_manager: Optional[Any] = None):
        """
        初期化
        
        Args:
            screen_manager: ScreenManager インスタンス
            camera_manager: CameraManager インスタンス（深度フレーム取得用）
        """
        self.screen_manager = screen_manager
        self.camera_manager = camera_manager
        self.depth_measurement_service: Optional[Any] = None
        
        # 深度フレームバッファ（t-1, t のペアを保持）
        self._depth_frame_prev: Optional[NDArray[np.uint16]] = None
        self._depth_frame_buffer: deque = deque(maxlen=2)
        
        # トラッキング状態
        self._last_detected_position: Optional[Tuple[int, int]] = None
        self._last_detected_depth: Optional[float] = None
        self._last_hit_coord: Optional[Tuple[int, int, float]] = None
        
        # パラメータ（調整可能）
        self.depth_change_threshold_mm: float = -50.0  # mm（負 = 近づいている）
        self.min_motion_area: int = 50  # 最小検出面積（ピクセル）
        self.max_motion_area: int = 10000  # 最大検出面積
        self.approach_confidence_threshold: float = 0.5  # スクリーン向き信頼度閾値
        self.depth_variance_threshold: float = 200.0  # mm（領域内の深度ばらつき）
        
        # ノイズ対策用フィルタ
        self._motion_filter_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        
        logging.info(
            f"[MotionBasedTracker] 初期化完了 "
            f"(深度変化閾値: {self.depth_change_threshold_mm}mm, "
            f"最小面積: {self.min_motion_area}px)"
        )
    
    def set_target_color(self, color: str) -> None:
        """
        互換性維持用メソッド（実装なし）
        
        深度ベーストラッキングでは色指定は不要です。
        """
        logging.debug("[MotionBasedTracker] set_target_color() 呼び出し（無視）")
    
    def get_hit_area(self, frame: NDArray[np.uint8]) -> Optional[Tuple[int, int, float]]:
        """
        フレームからヒット座標を取得する（互換性インターフェース）
        
        Args:
            frame: RGB フレーム
        
        Returns:
            (x, y, depth) または None
        """
        return self.check_target_hit(frame)
    
    def check_target_hit(self, frame: NDArray[np.uint8]) -> Optional[Tuple[int, int, float]]:
        """
        フレームから接近する物体を検知し、スクリーン衝突判定を行う
        
        Args:
            frame: RGB フレーム
        
        Returns:
            ヒット座標 (x, y, depth) または None
        """
        # ステップ1: 深度フレーム取得と差分計算
        depth_frame = self.camera_manager.get_depth_frame() if self.camera_manager else None
        if depth_frame is None:
            logging.debug("[check_target_hit] 深度フレーム取得失敗")
            return None
        
        # ステップ2: 深度バッファに追加
        self._depth_frame_buffer.append(depth_frame)
        
        # 2フレーム以上必要
        if len(self._depth_frame_buffer) < 2:
            logging.debug("[check_target_hit] フレームバッファ未充填")
            return None
        
        depth_frame_prev = self._depth_frame_buffer[0]
        depth_frame_curr = self._depth_frame_buffer[1]
        
        # ステップ3: 深度差分マップ計算
        delta_depth, motion_mask = self._compute_depth_change_map(depth_frame_prev, depth_frame_curr)
        
        if motion_mask is None or not motion_mask.any():
            logging.debug("[check_target_hit] 移動領域なし")
            self._last_detected_position = None
            return None
        
        # ステップ4: 移動物体検知
        candidates = self._detect_moving_objects(motion_mask, delta_depth, depth_frame_curr)
        
        if not candidates:
            logging.debug("[check_target_hit] 候補物体なし")
            self._last_detected_position = None
            return None
        
        # ステップ5: スクリーン向き判定と信頼度スコアリング
        best_candidate = self._select_best_candidate(candidates)
        
        if best_candidate is None or best_candidate['approach_confidence'] < self.approach_confidence_threshold:
            logging.debug(
                f"[check_target_hit] スクリーン向き判定失敗 "
                f"(信頼度: {best_candidate['approach_confidence'] if best_candidate else 'N/A'})"
            )
            return None
        
        # ステップ6: 深度値取得（DepthMeasurementService 優先）
        cx, cy = best_candidate['center']
        depth_m = self._get_depth_at_position(cx, cy, depth_frame_curr)
        
        if depth_m is None or depth_m <= 0:
            logging.debug("[check_target_hit] 深度値取得失敗")
            return None
        
        # ステップ7: スクリーン衝突判定
        screen_depth_m = self.screen_manager.get_screen_depth()
        if not self._check_collision_depth(depth_m, screen_depth_m):
            logging.debug(
                f"[check_target_hit] 深度がスクリーン範囲外 "
                f"(物体: {depth_m:.2f}m, スクリーン: {screen_depth_m:.2f}m)"
            )
            return None
        
        # ステップ8: スクリーン領域内判定
        screen_points = self.screen_manager.get_screen_area_points()
        if screen_points and len(screen_points) >= 3:
            poly = np.array(screen_points, dtype=np.int32)
            in_screen = cv2.pointPolygonTest(poly, (cx, cy), False) >= 0
            if not in_screen:
                logging.debug(f"[check_target_hit] スクリーン領域外 ({cx}, {cy})")
                return None
        
        # ヒット確定
        logging.info(
            f"[check_target_hit] ✓ ヒット検出 "
            f"({cx}, {cy}) 深度: {depth_m:.2f}m, "
            f"接近信頼度: {best_candidate['approach_confidence']:.2f}"
        )
        
        self._last_detected_position = (cx, cy)
        self._last_detected_depth = depth_m
        self._last_hit_coord = (cx, cy, depth_m)
        
        return self._last_hit_coord
    
    # ========== Private Methods ==========
    
    def _compute_depth_change_map(
        self,
        depth_prev: NDArray[np.uint16],
        depth_curr: NDArray[np.uint16]
    ) -> Tuple[Optional[NDArray[np.float32]], Optional[NDArray[np.uint8]]]:
        """
        深度フレーム間の変化をマップで計算
        
        Args:
            depth_prev: 前フレーム深度 (mm単位)
            depth_curr: 現在フレーム深度 (mm単位)
        
        Returns:
            (delta_depth, motion_mask)
            - delta_depth: 深度変化（負 = 近づいている）
            - motion_mask: バイナリマスク（移動領域）
        """
        try:
            # 無効値フィルタ（0 と 65535 は無効）
            valid_mask = ((depth_curr > 0) & (depth_curr < 65535) &
                         (depth_prev > 0) & (depth_prev < 65535))
            
            # 深度差分計算（mm単位）
            delta_depth = depth_curr.astype(np.float32) - depth_prev.astype(np.float32)
            
            # 物体が近づいている領域を抽出（Δdepth < -50mm）
            motion_mask = (delta_depth < self.depth_change_threshold_mm) & valid_mask
            
            # ノイズ除外（モルフォロジー演算）
            motion_mask = cv2.morphologyEx(
                motion_mask.astype(np.uint8),
                cv2.MORPH_OPEN,
                self._motion_filter_kernel
            )
            
            logging.debug(
                f"[_compute_depth_change_map] "
                f"移動ピクセル数: {np.count_nonzero(motion_mask)}"
            )
            
            return delta_depth, motion_mask
        
        except Exception as e:
            logging.error(f"[_compute_depth_change_map] エラー: {e}")
            return None, None
    
    def _detect_moving_objects(
        self,
        motion_mask: NDArray[np.uint8],
        delta_depth: NDArray[np.float32],
        depth_frame: NDArray[np.uint16]
    ) -> List[Dict[str, Any]]:
        """
        移動マスクから物体候補を検出
        
        Returns:
            List[{
                'center': (cx, cy),
                'area': area,
                'avg_delta_depth': mm,
                'depth_variance': mm
            }]
        """
        candidates = []
        
        try:
            contours, _ = cv2.findContours(
                motion_mask,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                # 面積フィルタ
                if area < self.min_motion_area or area > self.max_motion_area:
                    continue
                
                # 外接矩形から中心を計算
                x, y, w, h = cv2.boundingRect(contour)
                cx = x + w // 2
                cy = y + h // 2
                
                # ROI内の平均深度変化
                roi_delta = delta_depth[y:y+h, x:x+w]
                roi_motion = motion_mask[y:y+h, x:x+w]
                
                valid_delta = roi_delta[roi_motion > 0]
                if len(valid_delta) == 0:
                    continue
                
                avg_delta = float(np.mean(valid_delta))
                variance = float(np.std(valid_delta))
                
                candidates.append({
                    'center': (cx, cy),
                    'area': area,
                    'avg_delta_depth': avg_delta,
                    'depth_variance': variance,
                    'contour': contour
                })
            
            logging.debug(f"[_detect_moving_objects] {len(candidates)}個の候補検出")
            return candidates
        
        except Exception as e:
            logging.error(f"[_detect_moving_objects] エラー: {e}")
            return []
    
    def _select_best_candidate(
        self,
        candidates: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        複数の候補から最適な物体を選択
        
        スコア計算:
        1. 深度変化の大きさ（大きく近づいている）
        2. 連続性（前フレームの位置から大きく離れていない）
        3. 領域の一貫性（深度ばらつき小）
        """
        if not candidates:
            return None
        
        best_score = -1.0
        best_candidate = None
        
        for candidate in candidates:
            # スコア1: 深度変化（負の値が大きいほど高スコア）
            depth_score = min(abs(candidate['avg_delta_depth']) / 200.0, 1.0)
            
            # スコア2: 連続性（前フレームとの距離）
            if self._last_detected_position is not None:
                dx = candidate['center'][0] - self._last_detected_position[0]
                dy = candidate['center'][1] - self._last_detected_position[1]
                distance = np.sqrt(dx**2 + dy**2)
                continuity_score = max(1.0 - distance / 200.0, 0.0)
            else:
                continuity_score = 1.0
            
            # スコア3: 領域一貫性（ばらつき小）
            variance_score = max(1.0 - candidate['depth_variance'] / self.depth_variance_threshold, 0.0)
            
            # スコア4: 面積スコア（中程度の面積が最適）
            optimal_area = 500
            area_score = max(1.0 - abs(candidate['area'] - optimal_area) / 2000.0, 0.0)
            
            # 統合スコア
            total_score = (
                depth_score * 0.4 +
                continuity_score * 0.3 +
                variance_score * 0.2 +
                area_score * 0.1
            )
            
            # スクリーン向き判定（深度が減少 = 近づいている）
            approach_confidence = (
                depth_score if candidate['avg_delta_depth'] < 0 else 0.0
            )
            
            candidate['total_score'] = total_score
            candidate['approach_confidence'] = approach_confidence
            
            if total_score > best_score:
                best_score = total_score
                best_candidate = candidate
        
        if best_candidate:
            logging.debug(
                f"[_select_best_candidate] "
                f"最適候補選択 {best_candidate['center']}, "
                f"スコア: {best_score:.3f}"
            )
        
        return best_candidate
    
    def _get_depth_at_position(
        self,
        x: int,
        y: int,
        depth_frame: NDArray[np.uint16]
    ) -> Optional[float]:
        """
        位置 (x, y) での深度値を取得
        
        優先度:
        1. DepthMeasurementService (補間処理あり)
        2. 深度フレームから直接取得 + 補間
        """
        try:
            # 優先度1: DepthMeasurementService
            if self.depth_measurement_service is not None:
                depth_m = self.depth_measurement_service.measure_at_rgb_coords(x, y)
                if depth_m >= 0.0:
                    return depth_m
            
            # 優先度2: 深度フレームから直接
            # RGB座標を深度座標に変換
            depth_h, depth_w = depth_frame.shape[:2]
            depth_x = int(x * depth_w / 1280)
            depth_y = int(y * depth_h / 800)
            
            if 0 <= depth_x < depth_w and 0 <= depth_y < depth_h:
                depth_mm = float(depth_frame[depth_y, depth_x])
                if 0 < depth_mm < 65535:
                    return depth_mm / 1000.0
            
            # 補間処理
            depth_m = self._interpolate_depth(depth_x, depth_y, depth_frame)
            return depth_m
        
        except Exception as e:
            logging.error(f"[_get_depth_at_position] エラー: {e}")
            return None
    
    def _interpolate_depth(
        self,
        x: int,
        y: int,
        depth_frame: NDArray[np.uint16]
    ) -> Optional[float]:
        """
        周辺ピクセルから深度値を補間
        """
        h, w = depth_frame.shape
        radius = 10
        
        valid_depths = []
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    d = float(depth_frame[ny, nx])
                    if 0 < d < 65535:
                        distance = np.sqrt(dx**2 + dy**2)
                        weight = 1.0 / (distance + 1.0)
                        valid_depths.append((d, weight))
        
        if valid_depths:
            total_weight = sum(w for _, w in valid_depths)
            avg_depth_mm = sum(d * w for d, w in valid_depths) / total_weight
            return avg_depth_mm / 1000.0
        
        return None
    
    def _check_collision_depth(
        self,
        object_depth_m: float,
        screen_depth_m: float,
        tolerance_m: float = 0.1
    ) -> bool:
        """
        オブジェクトの深度がスクリーン深度に近いか判定
        """
        if screen_depth_m <= 0:
            return False
        
        return abs(object_depth_m - screen_depth_m) <= tolerance_m
    
    def get_last_reached_coord(self) -> Optional[Tuple[int, int, float]]:
        """最後にヒットした座標を取得"""
        return self._last_hit_coord
    
    def get_last_detected_position(self) -> Optional[Tuple[int, int]]:
        """最後に検出した位置を取得"""
        return self._last_detected_position
    
    def set_depth_change_threshold(self, threshold_mm: float) -> None:
        """深度変化閾値を設定（mm、負の値）"""
        self.depth_change_threshold_mm = threshold_mm
        logging.info(f"[MotionBasedTracker] 深度変化閾値: {threshold_mm}mm")
    
    def set_min_motion_area(self, area: int) -> None:
        """最小検出面積を設定"""
        self.min_motion_area = area
        logging.info(f"[MotionBasedTracker] 最小検出面積: {area}px")
