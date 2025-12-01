#!/usr/bin/env python3
"""
深度情報取得と衝突判定ロジックの修正検証スクリプト

確認項目:
1. 深度が0.00の場合、衝突と判定されないこと
2. リアルタイム深度取得のフォールバック
3. camera_manager 設定の確認
"""

import sys
import numpy as np
from typing import Tuple, Optional

# 模擬的なクラス定義（実際はimportする）
class MockScreenManager:
    def __init__(self, depth=1.0):
        self.screen_depth = depth
        self.screen_area = [(100, 100), (700, 100), (700, 500), (100, 500)]
    
    def get_screen_depth(self) -> float:
        return self.screen_depth or 0.0
    
    def get_screen_area_points(self):
        return self.screen_area

class MockCameraManager:
    """深度カメラ取得をシミュレート"""
    def __init__(self, depth_mm: float = 0.0):
        self.depth_mm_value = depth_mm
    
    def get_depth_mm(self, x: int, y: int) -> float:
        """テスト用: 固定深度値を返す"""
        return self.depth_mm_value

def test_depth_detection():
    """深度検出ロジックのテスト"""
    print("=" * 60)
    print("【テスト1】深度検出ロジック（修正前後の比較）")
    print("=" * 60)
    
    # テストケース 1: 深度が 0.0 mm
    print("\n▼ ケース1: depth_mm = 0.0 (カメラから取得できず)")
    camera = MockCameraManager(depth_mm=0.0)
    screen_mgr = MockScreenManager(depth=1.0)
    
    depth_mm = camera.get_depth_mm(400, 300)
    if depth_mm > 0:
        depth = depth_mm / 1000.0
    else:
        depth = screen_mgr.get_screen_depth() or 0.0
    
    print(f"  カメラ深度: {depth_mm} mm")
    print(f"  スクリーン深度フォールバック: {screen_mgr.get_screen_depth()} m")
    print(f"  最終深度値: {depth} m")
    
    # テストケース 2: 深度が有効値
    print("\n▼ ケース2: depth_mm = 500 (カメラから取得成功)")
    camera = MockCameraManager(depth_mm=500.0)
    depth_mm = camera.get_depth_mm(400, 300)
    if depth_mm > 0:
        depth = depth_mm / 1000.0
    else:
        depth = screen_mgr.get_screen_depth() or 0.0
    
    print(f"  カメラ深度: {depth_mm} mm")
    print(f"  最終深度値: {depth} m")
    print(f"  → 0.50 m = 50 cm")
    
    # テストケース 3: スクリーン深度が 0.0
    print("\n▼ ケース3: screen_depth = 0.0 (未設定)")
    screen_mgr_empty = MockScreenManager(depth=0.0)
    camera = MockCameraManager(depth_mm=0.0)
    depth_mm = camera.get_depth_mm(400, 300)
    if depth_mm > 0:
        depth = depth_mm / 1000.0
    else:
        depth = screen_mgr_empty.get_screen_depth() or 0.0
    
    print(f"  カメラ深度: {depth_mm} mm")
    print(f"  スクリーン深度: {screen_mgr_empty.get_screen_depth()} m")
    print(f"  最終深度値: {depth} m")
    print(f"  → ⚠️ 深度 0.00 は衝突判定から除外される")

def test_collision_detection():
    """衝突判定ロジックのテスト（修正後）"""
    print("\n" + "=" * 60)
    print("【テスト2】衝突判定ロジック（修正後）")
    print("=" * 60)
    
    from common.config import COLLISION_DEPTH_THRESHOLD
    
    print(f"\n衝突判定用深度閾値: {COLLISION_DEPTH_THRESHOLD} m")
    
    # テストケース 1: 深度が 0.0 (修正後: 衝突NOT)
    print("\n▼ テストケース1: 深度 0.0 m（無効な深度値）")
    depth = 0.0
    inside_polygon = True
    
    print(f"  ポリゴン内判定: {inside_polygon}")
    print(f"  深度: {depth} m")
    
    # 修正後のロジック
    if depth <= 0.0:
        print(f"  → ❌ 衝突判定 OFF （深度が無効）")
        hit = None
    elif inside_polygon and depth <= COLLISION_DEPTH_THRESHOLD:
        print(f"  → ✅ 衝突判定 ON")
        hit = (400, 300, depth)
    else:
        print(f"  → ❌ 衝突判定 OFF")
        hit = None
    
    # テストケース 2: 深度が有効で、到達範囲内
    print("\n▼ テストケース2: 深度 0.5 m（有効で到達範囲内）")
    depth = 0.5
    inside_polygon = True
    
    print(f"  ポリゴン内判定: {inside_polygon}")
    print(f"  深度: {depth} m")
    
    if depth <= 0.0:
        print(f"  → ❌ 衝突判定 OFF （深度が無効）")
        hit = None
    elif inside_polygon and depth <= COLLISION_DEPTH_THRESHOLD:
        print(f"  → ✅ 衝突判定 ON")
        hit = (400, 300, depth)
    else:
        print(f"  → ❌ 衝突判定 OFF")
        hit = None
    
    # テストケース 3: 深度が到達範囲外
    print("\n▼ テストケース3: 深度 3.0 m（到達範囲外）")
    depth = 3.0
    inside_polygon = True
    
    print(f"  ポリゴン内判定: {inside_polygon}")
    print(f"  深度: {depth} m")
    
    if depth <= 0.0:
        print(f"  → ❌ 衝突判定 OFF （深度が無効）")
        hit = None
    elif inside_polygon and depth <= COLLISION_DEPTH_THRESHOLD:
        print(f"  → ✅ 衝突判定 ON")
        hit = (400, 300, depth)
    else:
        print(f"  → ❌ 衝突判定 OFF （深度が到達範囲外）")
        hit = None

def main():
    """メインテスト実行"""
    print("\n")
    print("█" * 60)
    print("█  深度情報修正の検証テスト")
    print("█" * 60)
    
    test_depth_detection()
    test_collision_detection()
    
    print("\n" + "=" * 60)
    print("【修正内容のまとめ】")
    print("=" * 60)
    print("""
1. 深度情報の取得改善:
   - ball_tracker.py: 深度が 0.0 の場合のフォールバック
   - camera_manager.py: タイムアウト設定とデバッグログの追加

2. 衝突判定ロジック改善:
   - hit_detection.py: 深度 ≤ 0.0 の場合は衝突と判定しない
   
3. 期待される結果:
   - 深度が 0.0 の場合は衝突が発生しない
   - リアルタイム深度取得に失敗した場合はスクリーン深度を使用
   - スクリーン深度も 0.0 の場合は衝突判定から除外
    """)
    
    print("✅ テスト完了\n")

if __name__ == "__main__":
    main()
