"""
FPS計測ヘルパー
"""

from time import perf_counter

class FpsCounter:
    """高精度なFPSカウンター"""
    
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.times: list[float] = []
        self.is_active = True  # デバッグ用ON/OFFフラグ

    def tick(self) -> float:
        """フレームをカウントし、平均FPSを返す"""
        if not self.is_active:
            return 0.0

        now = perf_counter()
        self.times.append(now)
        if len(self.times) > self.window_size:
            self.times.pop(0)
        if len(self.times) < 2:
            return 0.0
        elapsed = self.times[-1] - self.times[0]
        return (len(self.times) - 1) / elapsed if elapsed > 0 else 0.0

    def enable(self):
        """FPS表示を有効にする"""
        self.is_active = True

    def disable(self):
        """FPS表示を無効にする"""
