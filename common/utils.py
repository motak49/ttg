# utils.py
"""
共通ユーティリティ関数群
"""

import os
import json
from typing import List, Tuple, Dict, Any, Callable, cast

def create_log_folder(folder_path: str) -> bool:
    """
    ログフォルダを作成する
    Args:
        folder_path (str): 作成するフォルダパス
    Returns:
        bool: 作成成功時にTrueを返す
    """
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        return True
    except Exception as e:
        print(f"フォルダ作成エラー: {e}")
        return False

def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    JSONファイルを読み込む
    Args:
        file_path (str): 読み込むファイルパス
    Returns:
        Dict[str, Any]: ファイル内容
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return cast(Dict[str, Any], json.load(f))
        return {}
    except Exception as e:
        print(f"JSON読み込みエラー: {e}")
        return {}

def save_json_file(file_path: str, data: Dict[str, Any]) -> bool:
    """
    JSONファイルを保存する
    Args:
        file_path (str): 保存するファイルパス
        data (Dict[str, Any]): 保存するデータ
    Returns:
        bool: 保存成功時にTrueを返す
    """
    try:
        # ディレクトリが存在しない場合は作成
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"JSON保存エラー: {e}")
        return False

def validate_coordinates(points: List[Tuple[int, int]]) -> bool:
    """
    座標のバリデーションを行う
    Args:
        points (List[Tuple[int, int]]): 座標リスト
    Returns:
        bool: バリデーション成功時にTrueを返す
    """
    if len(points) != 4:
        return False
    
    for point in points:
        # Each point must be a tuple of two integers
        if len(point) != 2:
            return False
        x, y = point
        if not isinstance(x, int) or not isinstance(y, int):
            return False
            
    return True

def calculate_distance(point1: Tuple[int, int], point2: Tuple[int, int]) -> float:
    """
    2点間の距離を計算する
    Args:
        point1 (Tuple[int, int]): 点1 (x, y)
        point2 (Tuple[int, int]): 点2 (x, y)
    Returns:
        float: 2点間の距離
    """
    x1, y1 = point1
    x2, y2 = point2
    # Explicitly cast to float for mypy compliance
    result = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    return float(result)

def get_screen_area_from_points(points: List[Tuple[int, int]]) -> Dict[str, Any]:
    """
    4点からスクリーン領域情報を生成する
    Args:
        points (List[Tuple[int, int]]): 4点の座標リスト
    Returns:
        Dict[str, Any]: スクリーン領域情報
    """
    if not validate_coordinates(points):
        return {}
        
    # 4点を適切な順序に並び替える（左上、右上、右下、左下）
    # 簡易的な実装：左上を基準にソート
    sorted_points = sorted(points, key=lambda p: (p[1], p[0]))  # y座標でソート

    return {
        "points": points,
        "area": {
            "top_left": sorted_points[0],
            "top_right": sorted_points[1],
            "bottom_right": sorted_points[2],
            "bottom_left": sorted_points[3]
        }
    }

# グローバルなユーティリティ関数
utils: Dict[str, Callable[..., Any]] = {
        "create_log_folder": create_log_folder,
        "load_json_file": load_json_file,
        "save_json_file": save_json_file,
        "validate_coordinates": validate_coordinates,
        "calculate_distance": calculate_distance,
        "get_screen_area_from_points": get_screen_area_from_points
    }
