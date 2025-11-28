# common/validation.py
"""
永続化設定のバリデーションユーティリティ
"""

import os
import json
from typing import Tuple, List
from common.utils import load_json_file, save_json_file
from common.config import SCREEN_AREA_LOG_PATH, SCREEN_DEPTH_LOG_PATH, TRACKED_TARGET_CONFIG_PATH

def check_persistent_settings() -> Tuple[bool, List[str]]:
    """
    必要なログファイルが存在し、内容が有効か検証する。
    Returns:
        (is_ok, messages)  # is_ok が False のとき messages に警告文が格納される
    """
    msgs: List[str] = []
    ok = True

    # スクリーン領域
    area_path = SCREEN_AREA_LOG_PATH
    if not os.path.isfile(area_path):
        ok = False; msgs.append("スクリーン領域ログが見つかりません。")
    else:
        try:
            data = load_json_file(area_path)
            if not data.get("screen_area"):
                ok = False; msgs.append("スクリーン領域データが空です。")
        except Exception:
            ok = False; msgs.append("スクリーン領域ログの読み込みに失敗しました。")

    # 深度
    depth_path = SCREEN_DEPTH_LOG_PATH
    if not os.path.isfile(depth_path):
        ok = False; msgs.append("深度ログが見つかりません。")
    else:
        try:
            data = load_json_file(depth_path)
            if data.get("screen_depth") is None:
                ok = False; msgs.append("深度情報が設定されていません。")
        except Exception:
            ok = False; msgs.append("深度ログの読み込みに失敗しました。")

    # トラッキング設定
    track_path = TRACKED_TARGET_CONFIG_PATH
    if not os.path.isfile(track_path):
        ok = False; msgs.append("トラッキング設定ファイルが見つかりません。")
    else:
        try:
            data = load_json_file(track_path)
            if not data.get("color"):
                ok = False; msgs.append("トラッキング色が未設定です。")
        except Exception:
            ok = False; msgs.append("トラッキング設定の読み込みに失敗しました。")

    return ok, msgs

def create_default_settings() -> None:
    """
    ログファイルが存在しない場合、デフォルト設定を作成する
    """
    # スクリーン領域のデフォルト値
    default_area = {
        "screen_area": [
            [0, 0],
            [1920, 0],
            [1920, 1080],
            [0, 1080]
        ]
    }
    
    # 深度のデフォルト値
    default_depth = {
        "screen_depth": 1.0
    }
    
    # トラッキング設定のデフォルト値（赤色） - 新しい形式に変更
    default_track = {
        "color": "赤",
        "h_min": 0,
        "s_min": 100,
        "v_min": 100,
        "h_max": 10,
        "s_max": 255,
        "v_max": 255
    }
    
    # ディレクトリ作成
    os.makedirs("ScreenAreaLogs", exist_ok=True)
    os.makedirs("ScreenDepthLogs", exist_ok=True)
    os.makedirs("TrackBallLogs", exist_ok=True)
    
    # ファイル保存
    save_json_file(SCREEN_AREA_LOG_PATH, default_area)
    save_json_file(SCREEN_DEPTH_LOG_PATH, default_depth)
    save_json_file(TRACKED_TARGET_CONFIG_PATH, default_track)

def validate_and_create_defaults() -> bool:
    """
    バリデーションを実行し、問題があればデフォルト設定を作成する
    Returns:
        bool: バリデーションが成功した場合 True
    """
    is_ok, messages = check_persistent_settings()
    
    if not is_ok:
        print("設定ファイルの検証に失敗しました。")
        for msg in messages:
            print(f"警告: {msg}")
        
        print("デフォルト設定を生成します...")
        create_default_settings()
        print("デフォルト設定が生成されました。")
        
        # 再度バリデーション
        is_ok, _ = check_persistent_settings()
    
    return is_ok
