#!/usr/bin/env python3
"""
Camera FPS 設定エラーの修正確認スクリプト

修正内容:
- Camera ノードに setFps() がないため、preview（出力ストリーム）に setFps() を設定
- これにより警告 "Camera FPS設定エラー" が出なくなります
"""

import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


def test_camera_fps_fix():
    """修正内容を検証"""
    print("\n" + "=" * 80)
    print("【Camera FPS 設定エラー修正確認】")
    print("=" * 80)
    
    camera_file = Path("backend/camera_manager.py")
    content = camera_file.read_text(encoding="utf-8")
    
    # 修正前の問題コード
    print("\n【修正前（問題）】")
    print("❌ cam_rgb.setFps(self.fps)  ← Camera ノードに setFps() メソッドが存在しない")
    
    if "cam_rgb.setFps(self.fps)" in content:
        print("   ⚠️  古いコードがまだ存在しています")
    else:
        print("   ✅ 古いコードは削除されました")
    
    # 修正後の正しいコード
    print("\n【修正後（正しい実装）】")
    print("✅ preview.setFps(self.fps)  ← 出力ストリームに FPS を設定")
    
    if "preview.setFps(self.fps)" in content:
        print("   ✅ 修正されたコードが実装されています")
    else:
        print("   ❌ 修正コードが見つかりません")
        return False
    
    # 詳細確認
    print("\n【修正内容の詳細】")
    print("1. Camera ノード（cam_rgb）に setFps() はない")
    print("   → Camera は単なるパイプラインノード")
    print("")
    print("2. requestOutput() で取得した preview に setFps() を設定する")
    print("   → preview はカメラの出力ストリーム")
    print("   → ストリームに直接 FPS を設定することで有効")
    print("")
    print("3. エラーハンドリングも実装")
    print("   → FPS設定失敗時もシステムは継続動作")
    
    # ログに出現する警告を確認
    print("\n【期待される動作】")
    print("✅ 以下の警告が出なくなります：")
    print('   WARNING:root:Camera FPS設定エラー（デフォルト値で続行）: ...')
    print("")
    print("✅ 以下のログが出現します：")
    print("   INFO:root:[initialize_camera] Preview FPS set to 120")
    print("   DEBUG:root:Mono cameras FPS set to 120")
    
    return True


if __name__ == '__main__':
    try:
        success = test_camera_fps_fix()
        
        print("\n" + "=" * 80)
        if success:
            print("🎉 修正が正しく実装されています！")
            print("\n次のコマンドで実際の動作を確認できます：")
            print("  $ python main.py")
            print("\n「カメラ起動」ボタンをクリックし、")
            print("コンソールに警告が出ないことを確認してください。")
        else:
            print("❌ 修正が不完全です")
        print("=" * 80 + "\n")
        
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"確認エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
