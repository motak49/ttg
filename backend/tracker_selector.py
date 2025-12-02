"""
トラッカーセレクター（選択可能なトラッキングモード）

従来の色ベース（BallTracker）と新しい深度ベース（MotionBasedTracker）
を切り替え可能にするレイヤー
"""

import logging
from typing import Optional, Any, Tuple, Dict
from enum import Enum

import numpy as np
from numpy.typing import NDArray


class TrackerMode(Enum):
    """トラッキングモード"""
    COLOR = "color"              # 従来：色ベース
    MOTION = "motion"            # 新規：深度ベース移動物体
    HYBRID = "hybrid"            # 両方の結果をスコアリング


class TrackerSelector:
    """
    トラッキングモード選択レイヤー
    
    複数のトラッカーを管理し、設定に応じて使い分ける
    """
    
    def __init__(
        self,
        color_tracker: Any,
        motion_tracker: Any,
        default_mode: TrackerMode = TrackerMode.MOTION
    ):
        """
        初期化
        
        Args:
            color_tracker: BallTracker インスタンス（色ベース）
            motion_tracker: MotionBasedTracker インスタンス（深度ベース）
            default_mode: デフォルトトラッキングモード
        """
        self.color_tracker = color_tracker
        self.motion_tracker = motion_tracker
        self.current_mode = default_mode
        
        # 統計情報
        self._color_hit_count = 0
        self._motion_hit_count = 0
        self._hybrid_mode_switch_count = 0
        
        logging.info(
            f"[TrackerSelector] 初期化完了 "
            f"(デフォルトモード: {default_mode.value})"
        )
    
    def set_mode(self, mode: TrackerMode) -> None:
        """トラッキングモードを設定"""
        self.current_mode = mode
        logging.info(f"[TrackerSelector] トラッキングモード変更: {mode.value}")
    
    def get_mode(self) -> TrackerMode:
        """現在のトラッキングモードを取得"""
        return self.current_mode
    
    def check_target_hit(self, frame: NDArray[np.uint8]) -> Optional[Tuple[int, int, float]]:
        """
        設定されたモードでトラッキングを実行
        
        Args:
            frame: RGB フレーム
        
        Returns:
            ヒット座標 (x, y, depth) または None
        """
        try:
            if self.current_mode == TrackerMode.COLOR:
                return self._check_color_mode(frame)
            elif self.current_mode == TrackerMode.MOTION:
                return self._check_motion_mode(frame)
            elif self.current_mode == TrackerMode.HYBRID:
                return self._check_hybrid_mode(frame)
            else:
                logging.warning(f"[check_target_hit] 不明なモード: {self.current_mode}")
                return None
        
        except Exception as e:
            logging.error(f"[check_target_hit] エラー: {e}")
            return None
    
    def get_hit_area(self, frame: NDArray[np.uint8]) -> Optional[Tuple[int, int, float]]:
        """
        互換性インターフェース（check_target_hit の別名）
        
        Args:
            frame: RGB フレーム
        
        Returns:
            ヒット座標 (x, y, depth) または None
        """
        return self.check_target_hit(frame)
    
    def _check_color_mode(self, frame: NDArray[np.uint8]) -> Optional[Tuple[int, int, float]]:
        """色ベーストラッキング（従来方式）"""
        try:
            result = self.color_tracker.check_target_hit(frame)
            if result is not None:
                self._color_hit_count += 1
                logging.debug("[_check_color_mode] ✓ 色ベース検知成功")
            return result
        except Exception as e:
            logging.error(f"[_check_color_mode] エラー: {e}")
            return None
    
    def _check_motion_mode(self, frame: NDArray[np.uint8]) -> Optional[Tuple[int, int, float]]:
        """深度ベース移動物体トラッキング（新方式）"""
        try:
            result = self.motion_tracker.check_target_hit(frame)
            if result is not None:
                self._motion_hit_count += 1
                logging.debug("[_check_motion_mode] ✓ 深度ベース検知成功")
            return result
        except Exception as e:
            logging.error(f"[_check_motion_mode] エラー: {e}")
            return None
    
    def _check_hybrid_mode(self, frame: NDArray[np.uint8]) -> Optional[Tuple[int, int, float]]:
        """ハイブリッドモード（両方を試行、信頼度が高い方を選択）"""
        try:
            color_result = self.color_tracker.check_target_hit(frame)
            motion_result = self.motion_tracker.check_target_hit(frame)
            
            # 両方失敗
            if color_result is None and motion_result is None:
                return None
            
            # 深度ベース成功、色失敗 → 深度ベースを優先
            if motion_result is not None and color_result is None:
                self._motion_hit_count += 1
                self._hybrid_mode_switch_count += 1
                logging.debug("[_check_hybrid_mode] 深度ベースを選択")
                return motion_result
            
            # 色成功、深度ベース失敗 → 色を使用（フォールバック）
            if color_result is not None and motion_result is None:
                self._color_hit_count += 1
                logging.debug("[_check_hybrid_mode] 色ベースを選択（フォールバック）")
                return color_result
            
            # 両方成功 → 深度ベースを優先（より信頼性が高い）
            if motion_result is not None and color_result is not None:
                self._motion_hit_count += 1
                self._hybrid_mode_switch_count += 1
                logging.debug(
                    f"[_check_hybrid_mode] 深度ベースを選択 "
                    f"(色: ({color_result[0]}, {color_result[1]}), "
                    f"深度: ({motion_result[0]}, {motion_result[1]}))"
                )
                return motion_result
        
        except Exception as e:
            logging.error(f"[_check_hybrid_mode] エラー: {e}")
            return None
        
        return None
    
    def get_detection_info(self, frame: NDArray[np.uint8]) -> Dict[str, Any]:
        """
        現在のモードでの検出情報を取得
        
        Returns:
            {
                'mode': 'color'|'motion'|'hybrid',
                'detected': bool,
                ...
            }
        """
        info: Dict[str, Any] = {'mode': self.current_mode.value}
        
        try:
            # カラートラッカーから検出情報を取得し、トップレベルにマージ
            if hasattr(self.color_tracker, 'get_detection_info'):
                color_info = self.color_tracker.get_detection_info(frame)
                if isinstance(color_info, dict):
                    info.update(color_info)  # merge keys like 'detected', 'pixel_count', etc.
            
            # MotionBasedTracker が get_detection_info を実装した場合はマージ
            if hasattr(self.motion_tracker, 'get_detection_info'):
                motion_info = self.motion_tracker.get_detection_info(frame)
                if isinstance(motion_info, dict):
                    # 競合キーがあればモーション側を優先（深度ベース情報が有用な場合）
                    info.update(motion_info)
            
            return info
        except Exception as e:
            logging.error(f"[get_detection_info] エラー: {e}")
            return info
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return {
            'mode': self.current_mode.value,
            'color_hit_count': self._color_hit_count,
            'motion_hit_count': self._motion_hit_count,
            'hybrid_switch_count': self._hybrid_mode_switch_count,
            'color_tracker_stats': (
                self.color_tracker.get_statistics() if hasattr(self.color_tracker, 'get_statistics') else {}
            ),
            'motion_tracker_stats': (
                self.motion_tracker.get_statistics() if hasattr(self.motion_tracker, 'get_statistics') else {}
            )
        }
    
    def set_target_color(self, color: str) -> None:
        """色ベーストラッカーのターゲット色を設定（互換性維持）"""
        try:
            self.color_tracker.set_target_color(color)
            logging.info(f"[set_target_color] 色設定: {color}")
        except Exception as e:
            logging.error(f"[set_target_color] エラー: {e}")
