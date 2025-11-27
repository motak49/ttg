"""アプリケーション全体で使うシングルトンサービスコンテナ

ここで生成したインスタンスはアプリ起動時に1つだけ作成し、各ウィンドウや
コンポーネントに渡すことで依存注入を簡潔にします。
"""
from typing import Optional

from backend.camera_manager import CameraManager
from backend.screen_manager import ScreenManager
from backend.ball_tracker import BallTracker
from backend.moving_target_manager import MovingTargetManager
from common.hit_detection import FrontCollisionDetector


class ServiceContainer:
    """シンプルなサービスコンテナ

    属性:
        camera_manager, screen_manager, front_detector, ball_tracker, moving_target_manager
    """

    def __init__(self) -> None:
        # 順序に注意: screen_manager は front_detector の依存先
        self.camera_manager: CameraManager = CameraManager()
        self.screen_manager: ScreenManager = ScreenManager()

        # 前面衝突検知器（ScreenManager を参照）
        self.front_detector: FrontCollisionDetector = FrontCollisionDetector(self.screen_manager)

        # BallTracker は collision_detector を注入して共有状態を持たせる
        self.ball_tracker: BallTracker = BallTracker(self.screen_manager, collision_detector=self.front_detector)

        # 動くターゲット管理
        self.moving_target_manager: MovingTargetManager = MovingTargetManager(self.screen_manager)

    # 簡便なゲッター（必要なら追加でラッパーを作れる）
    def get_camera_manager(self) -> CameraManager:
        return self.camera_manager

    def get_screen_manager(self) -> ScreenManager:
        return self.screen_manager

    def get_front_detector(self) -> FrontCollisionDetector:
        return self.front_detector

    def get_ball_tracker(self) -> BallTracker:
        return self.ball_tracker

    def get_moving_target_manager(self) -> MovingTargetManager:
        return self.moving_target_manager
