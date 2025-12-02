# common/config.py
"""
共通設定ファイル

- 各 UI の目標フレームレート (FPS)
- タイマー間隔 (ms) を FPS から計算するユーティリティ関数

【FPS設定について】
- DepthAI カメラのハードウェア上限: 120 FPS
  （カラー・モノクロ両方で 120 FPS に対応）
- スムーズな映像投影のため、最大値 120 FPS で統一設定
- 実測値は backend/camera_manager.py で確認可能
- 測定ツール: get_max_fps.py で再取得可能
"""

# OxGame 用フレームレート（ハードウェア上限: 120fps）
OX_GAME_TARGET_FPS = 120
TARGET_FPS = OX_GAME_TARGET_FPS

# TrackTargetConfig 用フレームレート（ハードウェア上限: 120fps）
TRACK_TARGET_CONFIG_FPS = 120
GRID_LINE_WIDTH = 40  # 線幅 (ピクセル) ? デフォルトは 2px から変更
BLUE_BORDER_WIDTH = 10  # 青枠の太さ（ピクセル）
TIMER_INTERVAL_MS = int(1000 / TARGET_FPS)

# 衝突判定用深度閾値（メートル単位、スクリーン前面からの距離）
COLLISION_DEPTH_THRESHOLD = 2.0   # Updated threshold to accommodate measured depth

# 深度測定の有効範囲上限（mm）
MAX_VALID_DEPTH_MM = 3000   # 例: 5m までを有効とみなす

# 衝突判定時の許容誤差（メートル単位）
DEPTH_TOLERANCE_M = 0.05

# 角度による衝突判定を有効にするか（デフォルトは無効）
ENABLE_ANGLE_COLLISION_CHECK = False

# フォールバック設定: BallTracker が深度取得失敗時にスクリーン深度へフォールバックしない
FALLBACK_TO_SCREEN_DEPTH = False

# 設定ファイルパス
TRACKED_TARGET_CONFIG_PATH = "TrackBallLogs/tracked_target_config.json"
SCREEN_AREA_LOG_PATH = "ScreenAreaLogs/area_log.json"
SCREEN_DEPTH_LOG_PATH = "ScreenDepthLogs/depth_log.json"


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
