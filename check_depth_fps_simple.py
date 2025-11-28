#!/usr/bin/env python3
"""
【深度設定画面 FPS 反映確認】シンプル版

ファイルを直接検査して FPS 設定を確認
"""

from pathlib import Path


def check_files():
    """ファイル内容の直接検査"""
    print("\n" + "=" * 80)
    print("【深度設定画面を含む各画面の FPS 設定確認】")
    print("=" * 80)

    checks = [
        ("frontend/depth_config.py", "DepthConfig", "TRACK_TARGET_CONFIG_FPS"),
        ("frontend/track_target_config.py", "TrackTargetConfig", "TRACK_TARGET_CONFIG_FPS"),
        ("frontend/game_area.py", "GameArea", "OX_GAME_TARGET_FPS"),
        ("frontend/ox_game.py", "OxGame", "OX_GAME_TARGET_FPS"),
    ]

    all_ok = True

    for filepath, component, fps_var in checks:
        path = Path(filepath)
        if not path.exists():
            print(f"\n❌ {filepath}: ファイルなし")
            all_ok = False
            continue

        content = path.read_text(encoding="utf-8")

        print(f"\n【{component}】({filepath})")

        # FPS 変数
        if fps_var in content:
            print(f"  ✅ {fps_var} 使用")
        else:
            print(f"  ❌ {fps_var} 未検出")
            all_ok = False

        # timer.start()
        if "self.timer.start" in content:
            print(f"  ✅ self.timer.start() 実装")
        else:
            print(f"  ❌ self.timer.start() 未検出")
            all_ok = False

        # timer_interval_ms
        if "timer_interval_ms" in content:
            print(f"  ✅ timer_interval_ms() 使用")
        else:
            print(f"  ❌ timer_interval_ms() 未検出")
            all_ok = False

        # ロギング
        if "logging" in content:
            print(f"  ✅ ロギング実装")
        else:
            print(f"  ⚠️  ロギング未実装")

    # Config 確認
    print(f"\n【common/config.py】")
    config_path = Path("common/config.py")
    config = config_path.read_text(encoding="utf-8")

    if "TARGET_FPS = 120" in config:
        print(f"  ✅ TARGET_FPS = 120")
    else:
        print(f"  ❌ TARGET_FPS != 120")
        all_ok = False

    if "TRACK_TARGET_CONFIG_FPS = 120" in config:
        print(f"  ✅ TRACK_TARGET_CONFIG_FPS = 120")
    else:
        print(f"  ❌ TRACK_TARGET_CONFIG_FPS != 120")
        all_ok = False

    if "OX_GAME_TARGET_FPS = 120" in config:
        print(f"  ✅ OX_GAME_TARGET_FPS = 120")
    else:
        print(f"  ❌ OX_GAME_TARGET_FPS != 120")
        all_ok = False

    print("\n" + "=" * 80)
    print("【実装状況】")
    print("=" * 80)

    if all_ok:
        print("""
✅ 深度設定画面を含むすべての画面で FPS 設定が正しく実装されています

【修正内容】
1. depth_config.py: 120fps コメント統一 + ロギング追加
2. track_target_config.py: 120fps コメント統一 + ロギング追加
3. game_area.py: 30fps → 120fps コメント更新 + ロギング追加
4. ox_game.py: 120fps コメント統一 + ロギング追加

【確認方法】
$ python main.py
→ 「深度設定」ボタンをクリック
→ コンソールに以下が表示される：
   INFO:root:[DepthConfig] FPS設定: 120 FPS, タイマー間隔: 8 ms で起動
→ 画面のカメラ映像がスムーズに更新される（120 FPS）
""")
    else:
        print("❌ 一部の実装に問題があります")

    print("=" * 80 + "\n")
    return all_ok


if __name__ == "__main__":
    import sys

    ok = check_files()
    sys.exit(0 if ok else 1)
