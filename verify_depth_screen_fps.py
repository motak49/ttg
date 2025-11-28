#!/usr/bin/env python3
"""
【深度設定画面 FPS 反映確認】

深度設定画面を含むすべての画面コンポーネントで
FPS 設定が正しく反映されているか確認
"""

import sys
from pathlib import Path


def check_fps_in_screen_components():
    """画面コンポーネント内の FPS 設定を確認"""
    print("\n" + "=" * 80)
    print("【深度設定・各画面コンポーネントの FPS 設定確認】")
    print("=" * 80)
    
    components = {
        "depth_config.py": ("深度設定画面", "TRACK_TARGET_CONFIG_FPS"),
        "track_target_config.py": ("トラッキング対象設定画面", "TRACK_TARGET_CONFIG_FPS"),
        "game_area.py": ("領域設定画面", "OX_GAME_TARGET_FPS"),
        "ox_game.py": ("Ox ゲーム画面", "OX_GAME_TARGET_FPS"),
    }
    
    all_ok = True
    
    for filename, (label, fps_var) in components.items():
        filepath = Path(f"frontend/{filename}")
        if not filepath.exists():
            print(f"\n❌ {label} ({filename}): ファイルが見つかりません")
            all_ok = False
            continue
        
        content = filepath.read_text(encoding="utf-8")
        
        print(f"\n【{label}】({filename})")
        print(f"  FPS 設定変数: {fps_var}")
        
        # FPS 変数が使われているか確認
        if fps_var in content:
            print(f"  ✅ {fps_var} が使用されている")
        else:
            print(f"  ❌ {fps_var} が見つかりません")
            all_ok = False
        
        # timer_interval_ms が使われているか確認
        if "timer_interval_ms" in content:
            print(f"  ✅ timer_interval_ms() が使用されている")
        else:
            print(f"  ⚠️  timer_interval_ms() が見つかりません")
        
        # timer.start() が使われているか確認
        if "self.timer.start" in content:
            print(f"  ✅ self.timer.start() が呼ばれている")
        else:
            print(f"  ❌ self.timer.start() が見つかりません")
            all_ok = False
        
        # ロギング確認
        if "[DepthConfig]" in content or "[TrackTargetConfig]" in content or "[GameArea]" in content or "[OxGame]" in content:
            print(f"  ✅ FPS 設定のロギングが実装されている")
        else:
            if filename == "ox_game.py" or filename == "game_area.py" or filename == "depth_config.py":
                print(f"  ⚠️  ロギングなし（推奨：デバッグ時に画面起動ログを確認できます）")
    
    return all_ok


def check_config_fps():
    """config.py の FPS 設定を確認"""
    print("\n" + "=" * 80)
    print("【common/config.py の FPS 設定確認】")
    print("=" * 80)
    
    config_file = Path("common/config.py")
    content = config_file.read_text(encoding="utf-8")
    
    # FPS 定数確認
    fps_configs = {
        "TARGET_FPS": 120,
        "OX_GAME_TARGET_FPS": 120,
        "TRACK_TARGET_CONFIG_FPS": 120,
    }
    
    all_ok = True
    for config_name, expected_value in fps_configs.items():
        if f"{config_name} = {expected_value}" in content:
            print(f"  ✅ {config_name} = {expected_value}")
        else:
            print(f"  ❌ {config_name} が {expected_value} に設定されていません")
            all_ok = False
    
    # timer_interval_ms 関数確認
    if "def timer_interval_ms" in content:
        print(f"  ✅ timer_interval_ms() 関数が定義されている")
    else:
        print(f"  ❌ timer_interval_ms() 関数が見つかりません")
        all_ok = False
    
    return all_ok


def display_expected_behavior():
    """期待される動作を表示"""
    print("\n" + "=" * 80)
    print("【期待される動作】")
    print("=" * 80)
    
    expected = """
▶️  アプリケーション起動時:
   各画面コンポーネント（深度設定、領域設定など）の
   コンストラクタで以下のログが出力される：
   
   INFO:root:[DepthConfig] FPS設定: 120 FPS, タイマー間隔: 8 ms で起動
   INFO:root:[GameArea] FPS設定: 120 FPS, タイマー間隔: 8 ms で起動
   INFO:root:[OxGame] FPS設定: 120 FPS, タイマー間隔: 8 ms で起動

▶️  実行時:
   • 深度設定画面（深度設定ボタン）
     └─ タイマー: 120 FPS（8ms 間隔）で映像更新
     └─ スムーズなカメラ映像が表示される
   
   • 領域設定画面（領域設定ボタン）
     └─ タイマー: 120 FPS（8ms 間隔）で映像更新
     └─ スムーズなカメラ映像が表示される
   
   • Ox ゲーム画面（OxGame ボタン）
     └─ タイマー: 120 FPS（8ms 間隔）で映像更新
     └─ FPS ラベル：「FPS: 120 (実測: XX.X)」と表示

【修正内容の要点】
   1. 古いコメント「約30fps」「約120fps」を統一
   2. 「120fps（ハードウェア上限）(config)」に統一
   3. 各画面コンポーネントで FPS 設定のロギング追加
   4. コンストラクタで timer_interval_ms() 計算時の
      FPS 設定とタイマー間隔をログ出力
"""
    print(expected)


if __name__ == '__main__':
    try:
        config_ok = check_config_fps()
        screen_ok = check_fps_in_screen_components()
        display_expected_behavior()
        
        print("\n" + "=" * 80)
        if config_ok and screen_ok:
            print("🎉 深度設定画面を含むすべての画面で FPS 設定が反映されています！")
            print("\n【確認方法】")
            print("1. アプリを起動：python main.py")
            print("2. 「深度設定」ボタンをクリック")
            print("3. コンソール出力を確認：")
            print("   INFO:root:[DepthConfig] FPS設定: 120 FPS, タイマー間隔: 8 ms で起動")
            print("4. 映像がスムーズに更新されることを確認")
        else:
            print("❌ 一部の設定に問題があります")
            print("上記の ❌ 項目を確認してください")
        print("=" * 80 + "\n")
        
        sys.exit(0 if config_ok and screen_ok else 1)
    except Exception as e:
        print(f"\n❌ 確認エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
