# camera_manager.py
import logging
from typing import Optional, Any

import depthai as dai
from PyQt6.QtCore import Qt

from backend.interfaces import CameraInterface


class CameraManager(CameraInterface):
    """DepthAI カメラ管理クラス（実機向け）"""

    def __init__(self) -> None:
        self.pipeline: Optional[dai.Pipeline] = None
        self.device: Optional[dai.Device] = None
        self.video_stream: Optional[Any] = None
        #self.fps: int = 60
        self.fps: int = 120
        # カメラ初期化状態フラグ
        self._initialized: bool = False

    def is_initialized(self) -> bool:
        """カメラが既に初期化されているかを返す"""
        return self._initialized

    def initialize_camera(self) -> bool:
        """
        カメラを実機でカラー画像取得モードで初期化する。
        1920x1080 (THE_1080_P) 解像度、self.fps fps を設定。
        例外が発生した場合はエラーをログに出力し、False を返す。
        """
        try:
            # Pipeline の作成
            self.pipeline = dai.Pipeline()

            # カラーカメラ設定（単一カラーカメラ）
            color_cam = self.pipeline.createColorCamera()
            # 解像度は 1920x1080 (DepthAI がサポートする最大解像度)
            color_cam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
            # FPS 設定
            color_cam.setFps(self.fps)

            # カラーデータを BGR 順序で取得（OpenCV 互換）
            color_cam.setInterleaved(False)
            color_cam.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)

            # プレビュー出力の作成
            xout = self.pipeline.createXLinkOut()
            xout.setStreamName("preview")
            # video 出力はフル解像度の BGR フレームを返す
            color_cam.video.link(xout.input)

            # デバイス接続（DepthAI の Device は自動で開始される）
            self.device = dai.Device(self.pipeline)

            # ストリーム取得（DepthAI の仕様に合わせて maxSize と blocking を設定）
            self.video_stream = self.device.getOutputQueue(name="preview")

            # 初期化成功フラグを立てる
            self._initialized = True
            return True

        except Exception as e:
            logging.error(f"カメラ初期化エラー: {e}")
            # 部分的に作成されたリソースがあればクローズしてリセット
            try:
                if self.device is not None:
                    self.device.close()
            finally:
                self.device = None
                self.pipeline = None
                self.video_stream = None
                self._initialized = False
            return False

    def get_frame(self) -> Optional[Any]:
        """
        カメラフレームを取得する。
        取得に失敗した場合は薄いグレーのプレースホルダー画像 (1280x800) を返す。
        """
        # If camera not initialized or stream missing, return placeholder without logging error
        if not self._initialized or self.video_stream is None:
            from PyQt6.QtGui import QImage
            width, height = 1280, 800
            placeholder = QImage(width, height, QImage.Format.Format_RGB888)
            placeholder.fill(Qt.GlobalColor.lightGray)
            return placeholder

        try:
            # ストリームからフレーム取得
            frame = self.video_stream.get()
            if frame is not None:
                # The returned object is a depthai.ImgFrame which has getCvFrame()
                return frame.getCvFrame()
            raise RuntimeError("No frame received")
        except Exception as e:
            logging.error(f"フレーム取得エラー: {e}")
            # プレースホルダー画像を生成して返す
            from PyQt6.QtGui import QImage
            width, height = 1280, 800
            placeholder = QImage(width, height, QImage.Format.Format_RGB888)
            placeholder.fill(Qt.GlobalColor.lightGray)
            return placeholder

    def set_fps(self, fps: int) -> None:
        """FPS を設定する（実機では使用しないがインターフェースは保持）"""
        self.fps = fps

    def close_camera(self) -> None:
        """カメラをクローズし、初期化フラグをリセット"""
        try:
            # Close device safely; no further action needed for mypy
            if self.device is not None:
                self.device.close()
        except Exception as e:
            logging.error(f"カメラクローズ時エラー: {e}")
        finally:
            self.device = None
            self.pipeline = None
            self.video_stream = None
            self._initialized = False
