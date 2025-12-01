"""
衝突判定シミュレーション（修正版）

目的: FrontCollisionDetector のロジックをテストし、
衝突判定が期待通りに動作するか確認する
"""

import numpy as np
import cv2
import json

def main():
    """衝突判定のシミュレーション"""
    
    print("=" * 70)
    print("【衝突判定シミュレーション（修正版）】")
    print("=" * 70)
    print()
    
    # スクリーン領域を読み込む
    with open("ScreenAreaLogs/area_log.json", 'r', encoding='utf-8') as f:
        area_data = json.load(f)
        screen_area = area_data["screen_area"]
    
    # スクリーン深度を読み込む
    with open("ScreenDepthLogs/depth_log.json", 'r', encoding='utf-8') as f:
        depth_data = json.load(f)
        screen_depth_mm = depth_data["screen_depth"]
        screen_depth_m = screen_depth_mm / 1000.0 if screen_depth_mm else 1.0
    
    # 設定から閾値を取得
    from common.config import COLLISION_DEPTH_THRESHOLD, ENABLE_ANGLE_COLLISION_CHECK
    
    print("▼ スクリーン領域ポリゴン:")
    print(f"  点数: {len(screen_area)}")
    for i, p in enumerate(screen_area):
        print(f"    {i}: {p}")
    
    print()
    print("▼ スクリーン深度:")
    print(f"  設定深度: {screen_depth_m:.2f} m ({screen_depth_mm:.0f} mm)")
    print(f"  衝突判定閾値: {COLLISION_DEPTH_THRESHOLD} m")
    print()
    
    # ポリゴン中心を計算
    poly_array = np.array(screen_area, dtype=np.int32)
    center_x = int(np.mean([p[0] for p in screen_area]))
    center_y = int(np.mean([p[1] for p in screen_area]))
    
    print("▼ テストケース:")
    print()
    
    # テストケース1: ポリゴン内 + 深度OK
    print("【テスト1】ポリゴン内 + 深度OK")
    test_x, test_y = center_x, center_y
    inside = cv2.pointPolygonTest(poly_array, (test_x, test_y), False) >= 0
    depth_ok = screen_depth_m <= COLLISION_DEPTH_THRESHOLD
    print(f"  座標: ({test_x}, {test_y})")
    print(f"  ポリゴン内: {inside} {'✓' if inside else '✗'}")
    result_char = '✓' if depth_ok else '✗'
    print(f"  深度: {screen_depth_m:.2f}m <= {COLLISION_DEPTH_THRESHOLD}m → {depth_ok} {result_char}")
    print(f"  → 結果: {'✓ HIT' if (inside and depth_ok) else '✗ NO HIT'}")
    print()
    
    # テストケース2: ポリゴン外
    print("【テスト2】ポリゴン外（左上）")
    test_x, test_y = 100, 100
    inside = cv2.pointPolygonTest(poly_array, (test_x, test_y), False) >= 0
    print(f"  座標: ({test_x}, {test_y})")
    print(f"  ポリゴン内: {inside} ✗")
    print(f"  → 結果: ✗ NO HIT")
    print()
    
    # テストケース3: ポリゴン内だが深度NG
    print("【テスト3】ポリゴン内 + 深度NG（2.0m）")
    test_x, test_y = center_x, center_y
    test_depth = 2.0
    inside = cv2.pointPolygonTest(poly_array, (test_x, test_y), False) >= 0
    depth_ok = test_depth <= COLLISION_DEPTH_THRESHOLD
    print(f"  座標: ({test_x}, {test_y})")
    print(f"  ポリゴン内: {inside} ✓")
    result_char = '✓' if depth_ok else '✗'
    print(f"  深度: {test_depth:.2f}m <= {COLLISION_DEPTH_THRESHOLD}m → {depth_ok} {result_char}")
    print(f"  → 結果: {'✓ HIT' if (inside and depth_ok) else '✗ NO HIT'}")
    print()
    
    # テストケース4: 現在のスクリーン深度で判定
    print("【テスト4】現在のスクリーン深度での判定")
    print(f"  スクリーン深度: {screen_depth_m:.2f}m")
    print(f"  閾値: {COLLISION_DEPTH_THRESHOLD}m")
    if screen_depth_m <= COLLISION_DEPTH_THRESHOLD:
        print(f"  → ✓ 深度判定: PASS（衝突可能）")
    else:
        print(f"  → ✗ 深度判定: FAIL（衝突不可）")
        print(f"     現在のカメラ深度が閾値を超えています。")
    print()
    
    # 角度判定について
    print("▼ 角度判定:")
    print(f"  有効: {ENABLE_ANGLE_COLLISION_CHECK}")
    print()
    
    print("=" * 70)
    print("【診断結果】")
    print("=" * 70)
    print()
    if screen_depth_m <= COLLISION_DEPTH_THRESHOLD:
        print("✓ 深度判定: OK")
        print("  衝突判定が機能する準備ができました。")
        print("  ボールをスクリーン領域に向かって移動させてください。")
    else:
        print("✗ 深度判定: NG")
        print(f"  現在の深度 {screen_depth_m:.2f}m > 閾値 {COLLISION_DEPTH_THRESHOLD}m")
        print("  config.py の COLLISION_DEPTH_THRESHOLD を引き上げるか、")
        print("  depth_log.json の深度値を調整してください。")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
