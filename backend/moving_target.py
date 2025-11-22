"""
動くターゲットの実装モジュール
"""

import random
from typing import Tuple
from dataclasses import dataclass

@dataclass
class MovingTarget:
    """動くターゲットのデータクラス"""
    
    # 画像パス
    image_path: str
    
    # 現在位置 (x, y)
    position: Tuple[int, int]
    
    # 移動速度 (dx, dy) 
    velocity: Tuple[int, int]
    
    # ログ用の前回時刻と座標
    last_log_time: float = 0.0
    last_logged_position: Tuple[int, int] | None = None
    
    def update(self, bounds: Tuple[int, int, int, int]):
        """
        ターゲットを更新（位置と速度の更新）

        Args:
            bounds: (xmin, xmax, ymin, ymax) - 移動範囲
        """
        # 画像サイズ（固定）を考慮した有効領域
        target_w, target_h = 100, 100
        xmin, xmax, ymin, ymax = bounds
        effective_xmax = xmax - target_w
        effective_ymax = ymax - target_h

        x, y = self.position
        dx, dy = self.velocity

        # 位置を更新（オーバーラン前）
        new_x = x + dx
        new_y = y + dy

        # X軸の反射と補正
        if new_x < xmin:
            new_x = xmin + (xmin - new_x)   # 鏡像で内部へ戻す
            dx = -dx
        elif new_x > effective_xmax:
            new_x = effective_xmax - (new_x - effective_xmax)
            dx = -dx

        # Y軸の反射と補正
        if new_y < ymin:
            new_y = ymin + (ymin - new_y)
            dy = -dy
        elif new_y > effective_ymax:
            new_y = effective_ymax - (new_y - effective_ymax)
            dy = -dy

        # 斜め移動保証：速度が0になった場合は再設定
        if dx == 0:
            dx = random.choice([i for i in range(-5, 6) if i != 0])
        if dy == 0:
            dy = random.choice([i for i in range(-5, 6) if i != 0])

        # デバッグロギング（テスト完了後に削除予定）
        import logging
        logger = logging.getLogger("moving_target_debug")
        logger.debug(
            f"Update -> pos:({x},{y}) vel:({dx},{dy}) "
            f"=> new_pos:({new_x},{new_y}) bounds:({xmin},{effective_xmax},{ymin},{effective_ymax})"
        )

        # 速度（dx, dy）をオブジェクトに保存
        self.velocity = (dx, dy)

        # 新しい位置と速度を設定
        self.position = (new_x, new_y)
        
        # 1秒ごとに移動状況をログ出力
        import time
        now = time.time()
        if now - self.last_log_time >= 1.0:
            # 前回ログ時点と比較して位置が変化したか判定
            if self.last_logged_position is None or self.position != self.last_logged_position:
                logger = logging.getLogger("moving_target")
                logger.info(f"Target moved: {self.last_logged_position} → {self.position}")
            else:
                logger = logging.getLogger("moving_target")
                logger.debug("Target stationary")
            # 状態更新
            self.last_log_time = now
