#!/usr/bin/env python3
"""
depthai 3.1.0 - USB OAK カメラの簡潔な接続例
参考: 3_1_test.py の動作確認済みコード
"""

import cv2
import depthai as dai


def main():
    """USB OAK カメラに接続してフレームを表示"""
    
    try:
        # パイプラインを作成
        pipeline = dai.Pipeline()
        
        # RGB カメラノード（Camera ノードを使用）
        cam_rgb = pipeline.create(dai.node.Camera).build()
        
        # プレビューを作成
        preview = cam_rgb.requestOutput((1920, 1280), type=dai.ImgFrame.Type.RGB888p)
        
        # 出力キューを作成
        q1 = preview.createOutputQueue()
        
        print("カメラに接続中...")
        
        # パイプラインを開始（depthai 3.1.0対応）
        with pipeline:
            print("カメラに接続しました。'q' キーで終了します。")
            while pipeline.isRunning():
                if q1.has():
                    frame = q1.get().getCvFrame()
                    cv2.imshow("USB OAK Camera", frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    finally:
        cv2.destroyAllWindows()
        print("終了しました")


if __name__ == "__main__":
    main()

