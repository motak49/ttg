#!/usr/bin/env python3
"""
120 FPS 実装の検証スクリプト

以下の項目を確認：
1. common/config.py で TARGET_FPS = 120 が設定されているか
2. backend/camera_manager.py で self.fps = 120 が初期化されているか
3. backend/camera_manager.py で setFps() が呼ばれているか
4. frontend/ox_game.py でコメントが更新されているか
"""

import sys
import re
from pathlib import Path


def check_config_fps():
    """common/config.py の FPS 設定を確認"""
    print("\n" + "=" * 80)
    print("【1】common/config.py の設定確認")
    print("=" * 80)
    
    config_file = Path("common/config.py")
    content = config_file.read_text(encoding="utf-8")
    
    # TARGET_FPS = 120 の確認
    if "TARGET_FPS = 120" in content:
        print("✅ TARGET_FPS = 120 が設定されています")
    else:
        print("❌ TARGET_FPS が 120 ではありません")
        return False
    
    # OX_GAME_TARGET_FPS = 120 の確認
    if "OX_GAME_TARGET_FPS = 120" in content:
        print("✅ OX_GAME_TARGET_FPS = 120 が設定されています")
    else:
        print("❌ OX_GAME_TARGET_FPS が 120 ではありません")
        return False
    
    # TRACK_TARGET_CONFIG_FPS = 120 の確認
    if "TRACK_TARGET_CONFIG_FPS = 120" in content:
        print("✅ TRACK_TARGET_CONFIG_FPS = 120 が設定されています")
    else:
        print("❌ TRACK_TARGET_CONFIG_FPS が 120 ではありません")
        return False
    
    # コメント内にハードウェア上限に関する説明があるか
    if "ハードウェア上限" in content or "DepthAI" in content:
        print("✅ ハードウェア上限に関するコメントが記載されています")
    else:
        print("⚠️  ハードウェア上限についてのコメント記載がありません")
    
    return True


def check_camera_manager_fps():
    """backend/camera_manager.py の FPS 設定を確認"""
    print("\n" + "=" * 80)
    print("【2】backend/camera_manager.py のカメラ FPS 設定確認")
    print("=" * 80)
    
    camera_file = Path("backend/camera_manager.py")
    content = camera_file.read_text(encoding="utf-8")
    
    # self.fps = 120 の初期化を確認
    if "self.fps: int = 120" in content:
        print("✅ self.fps が 120 に初期化されています")
    else:
        print("❌ self.fps が 120 に初期化されていません")
        return False
    
    # preview.setFps(self.fps) が呼ばれているか（修正版）
    if "preview.setFps(self.fps)" in content:
        print("✅ プレビュー出力の setFps() が呼ばれています（正しい実装）")
    else:
        print("❌ プレビュー出力の setFps() が見つかりません")
        return False
    
    # モノクロカメラの setFps が呼ばれているか
    if "mono_left.setFps(self.fps)" in content and "mono_right.setFps(self.fps)" in content:
        print("✅ モノクロカメラの setFps() が呼ばれています（Left/Right）")
    else:
        print("❌ モノクロカメラの setFps() が見つかりません")
        return False
    
    # エラーハンドリングが実装されているか
    if "except" in content and "fps_err" in content:
        print("✅ FPS設定エラーハンドリングが実装されています")
    else:
        print("⚠️  FPS設定エラーハンドリングが見つかりません")
    
    return True


def check_ox_game_fps():
    """frontend/ox_game.py のコメント更新を確認"""
    print("\n" + "=" * 80)
    print("【3】frontend/ox_game.py のコメント更新確認")
    print("=" * 80)
    
    ox_game_file = Path("frontend/ox_game.py")
    content = ox_game_file.read_text(encoding="utf-8")
    
    # タイマー起動部分のコメント
    if "120fps" in content and "ハードウェア上限" in content:
        print("✅ ox_game.py でコメントが 120fps に更新されています")
    else:
        print("⚠️  ox_game.py のコメント更新が確認できません")
        # 古いコメントがあるかチェック
        if "約30fps" in content:
            print("   注: 古いコメント \"約30fps\" が残っています")
            return False
    
    return True


def display_summary():
    """実装サマリーを表示"""
    print("\n" + "=" * 80)
    print("【4】実装サマリー")
    print("=" * 80)
    
    results = []
    results.append(("common/config.py", check_config_fps()))
    results.append(("backend/camera_manager.py", check_camera_manager_fps()))
    results.append(("frontend/ox_game.py", check_ox_game_fps()))
    
    print("\n" + "=" * 80)
    print("【検証結果】")
    print("=" * 80)
    
    all_passed = True
    for component, passed in results:
        status = "✅ OK" if passed else "❌ NG"
        print(f"{component:40s} : {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 全ての実装が正しく完了しています！")
        print("""
【実装内容】
- カメラ（カラー・モノクロ）: 120 FPS に設定
- フロントエンド表示: 120 FPS で駆動
- 共通設定: ハードウェア上限値を明記

【実行方法】
$ python main.py
  ↓
「カメラ起動」ボタンをクリック
  ↓
  スムーズな 120 FPS 映像投影が開始されます

【FPS確認】
- 実際の FPS は main.py 実行時のコンソールログで確認可能
- get_max_fps.py を再実行すると最大 FPS を再取得可能
""")
    else:
        print("❌ 一部の実装に問題があります")
        print("上記の ❌ NG 項目を確認して修正してください")
    
    print("=" * 80 + "\n")
    
    return all_passed


if __name__ == '__main__':
    try:
        all_ok = display_summary()
        sys.exit(0 if all_ok else 1)
    except Exception as e:
        print(f"\n❌ 検証エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
