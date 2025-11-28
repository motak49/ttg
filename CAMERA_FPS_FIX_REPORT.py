#!/usr/bin/env python3
"""
【修正完了報告】
Camera FPS 設定エラーの解決

修正日: 2025年11月27日
対象: backend/camera_manager.py
"""

FIX_SUMMARY = """
================================================================================
🔧【修正内容】Camera FPS 設定エラーの解決
================================================================================

【問題】
────────────────────────────────────────────────────────────────────────────

起動時に以下の警告が表示されていました：

  WARNING:root:Camera FPS設定エラー（デフォルト値で続行）: 
  'depthai.node.Camera' object has no attribute 'setFps'

原因: Camera ノードに setFps() メソッドが存在しない

【修正方法】
────────────────────────────────────────────────────────────────────────────

DepthAI SDK の API 仕様に基づき、FPS 設定位置を修正しました：

❌ 修正前（誤った実装）:
   cam_rgb = self.pipeline.create(dai.node.Camera).build()
   cam_rgb.setFps(self.fps)  ← Camera ノードには setFps() がない

✅ 修正後（正しい実装）:
   cam_rgb = self.pipeline.create(dai.node.Camera).build()
   preview = cam_rgb.requestOutput((1280, 800), type=dai.ImgFrame.Type.RGB888p)
   preview.setFps(self.fps)  ← 出力ストリームに FPS を設定

【技術的背景】
────────────────────────────────────────────────────────────────────────────

DepthAI パイプラインの構造：

  1. Camera ノード（cam_rgb）
     └─ パイプライン内の処理ユニット（FPS 設定できない）
  
  2. 出力ストリーム（preview）
     └─ requestOutput() で取得
     └─ setFps() メソッドを持つ（ここで FPS 設定可能）
  
  3. 出力キュー
     └─ createOutputQueue() で取得
     └─ フレームを取得する際に使用

→ FPS 設定は「出力ストリーム」に対して行う必要があります

【修正内容詳細】
────────────────────────────────────────────────────────────────────────────

修正ファイル: backend/camera_manager.py

【変更箇所1】カラーカメラ FPS 設定
─────────────────────────────────
  場所: initialize_camera() メソッド、ステップ 3.5

  before:
    cam_rgb.setFps(self.fps)  # Camera ノード（失敗）

  after:
    preview = cam_rgb.requestOutput((1280, 800), ...)
    preview.setFps(self.fps)  # 出力ストリーム（成功）

【変更箇所2】モノクロカメラ FPS 設定
─────────────────────────────────
  場所: initialize_camera() メソッド、ステップ 5

  before:
    mono_left.setFps(self.fps)  # これはそのまま（MonoCamera には有効）
    mono_right.setFps(self.fps)

  after:
    mono_left.setFps(self.fps)  # 変更なし（MonoCamera には setFps() 有効）
    mono_right.setFps(self.fps)

  ※ MonoCamera は ColorCamera と異なり、直接 setFps() を持ちます

【エラーハンドリング】
────────────────────────────────────────────────────────────────────────────

修正後も以下のように例外処理を実装：

  try:
      preview.setFps(self.fps)
      logging.info(f"Preview FPS set to {self.fps}")
  except Exception as fps_err:
      logging.warning(f"Preview FPS設定エラー（デフォルト値で続行）: {fps_err}")

効果: FPS 設定失敗時もシステムは継続動作（堅牢性向上）

【期待される結果】
────────────────────────────────────────────────────────────────────────────

✅ 修正前の症状
   WARNING が表示される
   FPS 設定が反映されない可能性

✅ 修正後の期待値
   WARNING が表示されない
   FPS が正常に 120 に設定される
   ログに以下が表示：
     INFO:root:[initialize_camera] Preview FPS set to 120
     DEBUG:root:Mono cameras FPS set to 120

【検証方法】
────────────────────────────────────────────────────────────────────────────

1️⃣  スクリプト検証（自動）
   $ python verify_fps_implementation.py
   $ python check_camera_fps_fix.py

2️⃣  実際の動作確認（手動）
   $ python main.py
   ↓
   コンソール出力を確認：
   - WARNING が出ないことを確認
   - Preview FPS set to 120 が表示されることを確認
   ↓
   「カメラ起動」ボタンをクリック
   ↓
   スムーズな映像投影が確認できることを確認

【参考】DepthAI API 仕様
────────────────────────────────────────────────────────────────────────────

• dai.node.Camera
  └─ setFps() メソッドなし（Camera はノードであり出力ではない）
  └─ requestOutput() で出力ストリームを取得
  
• dai.node.MonoCamera
  └─ setFps() メソッドあり（直接 FPS 設定可能）
  
• Output (requestOutput の戻り値)
  └─ setFps() メソッドあり（ストリームレベルでの FPS 設定）
  └─ createOutputQueue() で出力キューを取得

【今後の参考】
────────────────────────────────────────────────────────────────────────────

他のカメラノードを使用する場合は、各ノードの API ドキュメントで
setFps() メソッドの可用性を確認してください：

• ColorCamera → ノードレベルでは setFps() 不可、ストリームレベルで設定
• MonoCamera → ノードレベルで setFps() 可
• SpatialDetectionNetwork → ノードレベルでは setFps() 不可

================================================================================
"""

if __name__ == '__main__':
    print(FIX_SUMMARY)
    
    # 修正ログをファイルに保存
    with open("CAMERA_FPS_FIX_LOG.txt", "w", encoding="utf-8") as f:
        f.write(FIX_SUMMARY)
    
    print("💾 修正ログを CAMERA_FPS_FIX_LOG.txt に保存しました\n")
