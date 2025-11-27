"""
depthai 3.1.0 の新しい出力キュー生成方法
参考: tests/3_1_test.py の動作確認済みパターン
"""
import depthai as dai
import cv2

print("=== New Output Queue Model (depthai 3.1.0) ===\n")

pipeline = dai.Pipeline()

# Camera ノード（ColorCamera ではなく Camera を使用）
cam_rgb = pipeline.create(dai.node.Camera).build()

# プレビュー出力を requestOutput で作成（推奨方法）
preview = cam_rgb.requestOutput((640, 480), type=dai.ImgFrame.Type.RGB888p)

# 出力キューを作成
q = preview.createOutputQueue()
print("✓ preview.createOutputQueue() works")
print(f"  Queue type: {type(q)}")

# depthai 3.1.0: context manager を使用
print("\n=== Starting Pipeline with Context Manager ===")
try:
    with pipeline:
        print("✓ Pipeline started successfully with context manager")
        
        # フレーム取得テスト
        frame_count = 0
        while pipeline.isRunning() and frame_count < 30:
            if q.has():
                msg = q.get()
                frame = msg.getCvFrame()
                frame_count += 1
                print(f"  Frame {frame_count}: {frame.shape}")
                cv2.imshow("Camera Feed", frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    
    print("✓ Pipeline context exited successfully")
    
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")

cv2.destroyAllWindows()

# 古い方法の確認（参考用）
print("\n=== Checking for Deprecated Methods ===")
print(f"pipeline.createXLinkOut exists: {hasattr(pipeline, 'createXLinkOut')}")
print(f"dai.node.XLinkOut exists: {hasattr(dai.node, 'XLinkOut')}")

print("\n=== All checks completed ===")

