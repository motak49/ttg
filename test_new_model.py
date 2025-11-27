"""
depthai 3.1.0 の推奨パイプライン実行モデル

参考: tests/3_1_test.py の動作確認済みパターン

推奨方式:
1. Pipeline を作成
2. ノードを追加（Camera, ImageManip など）
3. requestOutput() または直接 createOutputQueue() でキューを生成
4. with pipeline: コンテキストマネージャーで自動管理
"""
import depthai as dai
import cv2

print("=== depthai 3.1.0 Pipeline Model ===\n")

# パイプライン作成
pipeline = dai.Pipeline()

# ノード作成: Camera（推奨）
print("1. Creating Camera node with requestOutput()")
cam_rgb = pipeline.create(dai.node.Camera).build()
preview = cam_rgb.requestOutput((640, 480), type=dai.ImgFrame.Type.RGB888p)
q = preview.createOutputQueue()
print(f"   ✓ Output queue created: {type(q).__name__}")

# Context manager での実行
print("\n2. Running pipeline with context manager")
try:
    with pipeline:
        print("   ✓ Pipeline started successfully")
        
        # フレーム取得テスト
        frame_count = 0
        while pipeline.isRunning() and frame_count < 10:
            if q.has():
                msg = q.get()
                frame = msg.getCvFrame()
                frame_count += 1
                print(f"   ✓ Frame {frame_count}: {frame.shape}")
                cv2.imshow("Feed", frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        
        print("   ✓ Pipeline context exited successfully")
except Exception as e:
    print(f"   ✗ Error: {e}")

cv2.destroyAllWindows()

print("\n=== Summary ===")
print("✓ depthai 3.1.0 推奨パターン:")
print("  - pipeline.start() または with pipeline: でパイプライン開始")
print("  - Output.createOutputQueue() でキューを生成")
print("  - Camera ノードを requestOutput() で出力設定")
print("  - Device を直接使用しない（自動管理）")
