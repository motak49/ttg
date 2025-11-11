# common/config.py
"""
共通設定ファイル

- 各 UI の目標フレームレート (FPS)
- タイマー間隔 (ms) を FPS から計算するユーティリティ関数
"""

# OxGame 用フレームレート（約30fps）
OX_GAME_TARGET_FPS = 30

# TrackTargetConfig 用フレームレート（約120fps）
TRACK_TARGET_CONFIG_FPS = 120


def timer_interval_ms(fps: int) -> int:
    """
    FPS からタイマー間隔 (ms) を計算します。
    最小 1 ms に丸め込み、整数で返却します。

    Args:
        fps: 目標フレームレート

    Returns:
        タイマーに渡すミリ秒数
    """
    if fps <= 0:
        return 1
    # round to nearest integer millisecond
    return max(1, int(round(1000 / fps)))
