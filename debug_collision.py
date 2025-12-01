"""
衝突判定デバッグスクリプト

目的:
1. スクリーン領域が正しく設定されているか確認
2. スクリーン深度が正しく設定されているか確認
3. 衝突判定の内部ロジックを追跡
"""

import json
import os
from pathlib import Path

def check_screen_config():
    """スクリーン領域設定の確認"""
    print("=" * 60)
    print("【スクリーン領域設定の確認】")
    print("=" * 60)
    
    area_log_path = "ScreenAreaLogs/area_log.json"
    if os.path.exists(area_log_path):
        with open(area_log_path, 'r', encoding='utf-8') as f:
            area_data = json.load(f)
            print(f"✓ スクリーン領域ファイル存在: {area_log_path}")
            print(f"  内容: {json.dumps(area_data, indent=2, ensure_ascii=False)}")
            
            # ポリゴンの点数と座標範囲を確認
            if "screen_area_points" in area_data:
                points = area_data["screen_area_points"]
                print(f"  ポリゴン点数: {len(points)}")
                if points:
                    xs = [p[0] for p in points]
                    ys = [p[1] for p in points]
                    print(f"  X范围: {min(xs)} - {max(xs)}")
                    print(f"  Y范围: {min(ys)} - {max(ys)}")
    else:
        print(f"✗ スクリーン領域ファイルが見つかりません: {area_log_path}")
        print("  → first_run で領域を設定してください")
    
    print()


def check_screen_depth():
    """スクリーン深度設定の確認"""
    print("=" * 60)
    print("【スクリーン深度設定の確認】")
    print("=" * 60)
    
    depth_log_path = "ScreenDepthLogs/depth_log.json"
    if os.path.exists(depth_log_path):
        with open(depth_log_path, 'r', encoding='utf-8') as f:
            depth_data = json.load(f)
            print(f"✓ スクリーン深度ファイル存在: {depth_log_path}")
            print(f"  内容: {json.dumps(depth_data, indent=2, ensure_ascii=False)}")
            
            if "screen_depth_m" in depth_data:
                depth = depth_data["screen_depth_m"]
                print(f"  設定深度: {depth} m")
                
                # 衝突判定の深度閾値と比較
                from common.config import COLLISION_DEPTH_THRESHOLD
                print(f"  衝突判定用閾値: {COLLISION_DEPTH_THRESHOLD} m")
                if depth <= COLLISION_DEPTH_THRESHOLD:
                    print(f"  ✓ 深度判定: PASS (実深度 <= 閾値)")
                else:
                    print(f"  ✗ 深度判定: FAIL (実深度 > 閾値)")
                    print(f"    → 衝突判定が発火しません")
    else:
        print(f"✗ スクリーン深度ファイルが見つかりません: {depth_log_path}")
        print("  → depth_config で深度を設定してください")
    
    print()


def check_ball_tracking_config():
    """ボール トラッキング設定の確認"""
    print("=" * 60)
    print("【ボール トラッキング設定の確認】")
    print("=" * 60)
    
    track_log_path = "TrackBallLogs/tracked_target_config.json"
    if os.path.exists(track_log_path):
        with open(track_log_path, 'r', encoding='utf-8') as f:
            track_data = json.load(f)
            print(f"✓ トラッキング設定ファイル存在: {track_log_path}")
            print(f"  色: {track_data.get('color', 'N/A')}")
            print(f"  最小面積: {track_data.get('min_area', 'N/A')} px")
            print(f"  HSV範囲:")
            print(f"    Hue: {track_data.get('h_min', 'N/A')} - {track_data.get('h_max', 'N/A')}")
            print(f"    Saturation: {track_data.get('s_min', 'N/A')} - {track_data.get('s_max', 'N/A')}")
            print(f"    Value: {track_data.get('v_min', 'N/A')} - {track_data.get('v_max', 'N/A')}")
    else:
        print(f"✗ トラッキング設定ファイルが見つかりません: {track_log_path}")
        print("  → track_target_config で色を設定してください")
    
    print()


def check_collision_threshold():
    """衝突判定用パラメータの確認"""
    print("=" * 60)
    print("【衝突判定パラメータの確認】")
    print("=" * 60)
    
    from common.config import COLLISION_DEPTH_THRESHOLD, ENABLE_ANGLE_COLLISION_CHECK
    
    print(f"深度閾値 (COLLISION_DEPTH_THRESHOLD): {COLLISION_DEPTH_THRESHOLD} m")
    print(f"角度判定有効 (ENABLE_ANGLE_COLLISION_CHECK): {ENABLE_ANGLE_COLLISION_CHECK}")
    print()
    print("衝突判定は以下の条件で発火します:")
    print("1. ボール位置がスクリーン領域ポリゴン内OR軌道変化検出 (ENABLE_ANGLE_COLLISION_CHECK=True の場合)")
    print("2. かつ、ボール深度 <= 深度閾値")
    print()


def main():
    """全体チェック実行"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "衝突判定 デバッグ情報" + " " * 20 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    check_screen_config()
    check_screen_depth()
    check_ball_tracking_config()
    check_collision_threshold()
    
    print("=" * 60)
    print("【診断結果】")
    print("=" * 60)
    print("以下の順番で確認・設定してください:")
    print("1. ScreenAreaLogs/area_log.json - スクリーン領域の4隅を設定")
    print("2. ScreenDepthLogs/depth_log.json - スクリーン面までの距離を設定")
    print("3. TrackBallLogs/tracked_target_config.json - ボール色を設定")
    print()
    print("その後、ox_game.py で深度テキスト表示と衝突判定を確認してください")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
