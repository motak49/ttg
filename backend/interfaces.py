"""
Backend Interfaces
==================

抽象インターフェースを定義し、UI とバックエンドの結合度を低減します。
"""

from typing import Tuple, Optional, Any, List
from abc import ABC, abstractmethod


class CameraInterface(ABC):
    """カメラデバイス操作のインターフェース"""

    @abstractmethod
    def is_initialized(self) -> bool:
        """カメラが初期化されているかを返す"""
        pass

    @abstractmethod
    def initialize_camera(self) -> bool:
        """カメラを初期化する"""
        pass

    @abstractmethod
    def get_frame(self) -> Optional[Any]:
        """カメラフレームを取得する"""
        pass

    @abstractmethod
    def set_fps(self, fps: int) -> None:
        """FPS を設定する"""
        pass

    @abstractmethod
    def close_camera(self) -> None:
        """カメラをクローズする"""
        pass


class BallTrackerInterface(ABC):
    """ボール追跡ロジックのインターフェース"""

    @abstractmethod
    def get_hit_area(self, frame: Any) -> Optional[Tuple[int, int, float]]:
        """フレームからヒット座標を取得する"""
        pass

    @abstractmethod
    def set_target_color(self, color: str) -> None:
        """追跡対象の色を設定する"""
        pass


class ScreenManagerInterface(ABC):
    """画面領域と深度情報管理のインターフェース"""

    @abstractmethod
    def get_screen_area(self) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """現在のスクリーン領域を取得する"""
        pass

    @abstractmethod
    def set_screen_area(self, points: List[Tuple[int, int]]) -> bool:
        """スクリーン領域を設定する（4点リスト）"""
        pass

    @abstractmethod
    def set_screen_area_legacy(self, top_left: Tuple[int, int], bottom_right: Tuple[int, int]) -> bool:
        """Legacy wrapper for backward compatibility."""
        pass

    @abstractmethod
    def get_screen_depth(self) -> float:
        """現在のスクリーン深度を取得する"""
        pass

    @abstractmethod
    def set_screen_depth(self, depth: float) -> None:
        """スクリーン深度を設定する"""
        pass

    @abstractmethod
    def get_screen_area_points(self) -> Optional[List[Tuple[int, int]]]:
        """現在のスクリーン領域4点を取得する"""
        pass
