#!/usr/bin/env python3
"""
depthai 3.1.0 を使用して USB 接続されているカメラに接続するプログラム
"""

import depthai as dai
import cv2
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def connect_to_camera():
    """
    USB 接続されているカメラに接続し、RGB フレームをキャプチャして表示
    """
    try:
        # パイプライン作成
        pipeline = dai.Pipeline()

        # RGB カメラノード作成
        cam_rgb = pipeline.create(dai.node.Camera).build()
        
        # プレビューを作成（キューをホストに接続）
        preview = cam_rgb.requestOutput((640, 480), type=dai.ImgFrame.Type.RGB888p)
        q_host = preview.createOutputQueue()

        logger.info("フレームキャプチャを開始します。'q' キーで終了します。")
        frame_count = 0
        
        try:
            with pipeline:
                while True:
                    if q_host.has():
                        in_msg = q_host.get()
                        frame = in_msg.getCvFrame()
                        height, width = frame.shape[:2]
                        frame_count += 1

                        cv2.putText(
                            frame,
                            f"Resolution: {width}x{height}",
                            (10, 30),
                            cv2.FONT_HERSHEY_TRIPLEX,
                            0.5,
                            (0, 255, 0)
                        )
                        cv2.putText(
                            frame,
                            f"Frame: {frame_count}",
                            (10, 60),
                            cv2.FONT_HERSHEY_TRIPLEX,
                            0.5,
                            (0, 255, 0)
                        )

                        cv2.imshow("USB Camera - OAK", frame)
                        if frame_count % 30 == 0:
                            logger.info(f"フレーム取得: {width}x{height} (frame #{frame_count})")

                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        logger.info("終了します")
                        break
        finally:
            cv2.destroyAllWindows()
            logger.info("カメラから切断しました")
            return True

    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = connect_to_camera()
    exit(0 if success else 1)
