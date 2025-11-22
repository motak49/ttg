"""
動くターゲットの管理モジュール
"""

import random
import logging
from typing import List, Tuple
from backend.moving_target import MovingTarget
from backend.screen_manager import ScreenManager

# ログ設定
logger = logging.getLogger("moving_target")

class MovingTargetManager:
    """動くターゲットの管理クラス"""
    
    def __init__(self, screen_manager: ScreenManager):
        self.screen_manager = screen_manager
        self.targets: List[MovingTarget] = []
        self.bounds: Tuple[int, int, int, int] = (0, 0, 0, 0)  # (xmin, xmax, ymin, ymax)
        
    def load_bounds(self):
        """スクリーン領域から移動範囲を読み込む"""
        try:
            self.screen_manager.load_log()
            points = self.screen_manager.get_screen_area_points()
            
            if points is None:
                logger.warning("スクリーン領域が設定されていません")
                return False
                
            # 4点の座標から矩形範囲を計算
            x_coords = [p[0] for p in points]
            y_coords = [p[1] for p in points]
            
            self.bounds = (
                int(min(x_coords)),
                int(max(x_coords)),
                int(min(y_coords)),
                int(max(y_coords))
            )
            
            logger.info(f"移動範囲を読み込みました: {self.bounds}")
            return True
            
        except Exception as e:
            logger.error(f"移動範囲の読み込みに失敗しました: {e}")
            return False
    
    def add_target(self, image_path: str, initial_position: Tuple[int, int] = None, speed_level: int = 3):
        """
        新しいターゲットを追加
        
        Args:
            image_path (str): ターゲット画像のパス
            initial_position (Tuple[int, int], optional): 初期位置。指定されない場合は範囲内ランダム。
            speed_level (int): 移動速度レベル（1〜5）
        """
        if not self.bounds or len(self.bounds) < 4:
            logger.warning("移動範囲が設定されていません")
            return
            
        # 初期位置を設定
        if initial_position is None:
            xmin, xmax, ymin, ymax = self.bounds
            x = random.randint(xmin, xmax - 100)  # 100pxは画像サイズ
            y = random.randint(ymin, ymax - 100)
        else:
            x, y = initial_position
            
        # 初期速度をランダムに設定（速度レベルに応じて範囲変更）
        speed_map = {1: 2, 2: 4, 3: 6, 4: 8, 5: 10}
        max_speed = speed_map.get(speed_level, 6)  # デフォルトはレベル3
        dx = random.randint(-max_speed, max_speed)
        dy = random.randint(-max_speed, max_speed)
        
        # ゼロ除算回避（斜め移動保証）
        if dx == 0 and dy == 0:
            dx = 1
        elif dx == 0:
            dx = random.choice([i for i in range(-max_speed, max_speed+1) if i != 0])
        elif dy == 0:
            dy = random.choice([i for i in range(-max_speed, max_speed+1) if i != 0])
            
        target = MovingTarget(
            image_path=image_path,
            position=(x, y),
            velocity=(dx, dy)
        )
        
        self.targets.append(target)
        logger.info(f"ターゲットを追加しました: {image_path}")
    
    def update_all(self):
        """すべてのターゲットを更新"""
        for target in self.targets:
            target.update(self.bounds)
    
    def get_targets(self) -> List[MovingTarget]:
        """現在のターゲットリストを取得"""
        return self.targets.copy()

    def check_ball_collision(self, ball_pos: Tuple[int, int]) -> List[MovingTarget]:
        """ボールとターゲットの衝突を判定"""
        collisions = []
        for target in self.targets:
            # 簡易的なAABB（軸平行境界ボックス）衝突判定
            tx, ty = target.position
            # ターゲットは100x100pxと仮定
            if (tx <= ball_pos[0] <= tx + 100 and
                ty <= ball_pos[1] <= ty + 100):
                collisions.append(target)
        return collisions
