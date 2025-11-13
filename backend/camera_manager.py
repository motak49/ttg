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
        # 深度ストリーム
        self.depth_stream: Optional[Any] = None
        # キャリブレーションデータ
        self.calibration_data: Optional[dict[str, Any]] = None

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
            preview_xout = self.pipeline.createXLinkOut()
            preview_xout.setStreamName("preview")
            color_cam.video.link(preview_xout.input)

            # ----- ステレオ深度ストリームの構築 -----
            mono_left = self.pipeline.createMonoCamera()
            mono_right = self.pipeline.createMonoCamera()
            mono_left.setResolution(dai.MonoCameraProperties.SensorResolution.THE_720_P)
            mono_right.setResolution(dai.MonoCameraProperties.SensorResolution.THE_720_P)
            mono_left.setBoardSocket(dai.CameraBoardSocket.LEFT)
            mono_right.setBoardSocket(dai.CameraBoardSocket.RIGHT)

            stereo = self.pipeline.createStereoDepth()
            stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)

            # 深度出力サイズをカラーフレーム解像度に合わせる（1920x1080）
            # これにより深度フレームとカラー画像の解像度が一致し、座標変換誤差を減らす
            color_width, color_height = 1920, 1080
            stereo.setOutputSize(color_width, color_height)

            # キャリブレーションデータを適用（あれば）
            if self.calibration_data is not None:
                try:
                    # DepthAI API が提供するキャリブレーション設定
                    # 実際のAPI呼び出しはカメラの型によって異なるため、エラーを無視
                    if hasattr(color_cam, 'setCalibrationData'):
                        try:
                            color_cam.setCalibrationData(self.calibration_data["intrinsics_left"])
                        except Exception as e1:
                            logging.warning(f"カラーカメラキャリブレーション設定失敗: {e1}")

                    if hasattr(mono_left, 'setCalibrationData'):
                        try:
                            mono_left.setCalibrationData(self.calibration_data["intrinsics_left"])
                        except Exception as e2:
                            logging.warning(f"左モノクロカメラキャリブレーション設定失敗: {e2}")

                    if hasattr(mono_right, 'setCalibrationData'):
                        try:
                            mono_right.setCalibrationData(self.calibration_data["intrinsics_right"])
                        except Exception as e3:
                            logging.warning(f"右モノクロカメラキャリブレーション設定失敗: {e3}")

                    if hasattr(stereo, 'setBaseline'):
                        try:
                            stereo.setBaseline(self.calibration_data["baseline"])  # mm 単位
                        except Exception as e4:
                            logging.warning(f"ベースライン設定失敗: {e4}")

                except KeyError as e:
                    logging.warning(f"キャリブレーションデータ不足: {e}")

            mono_left.out.link(stereo.left)
            mono_right.out.link(stereo.right)

            depth_xout = self.pipeline.createXLinkOut()
            depth_xout.setStreamName("depth")
            stereo.depth.link(depth_xout.input)

            # デバイス接続（DepthAI の Device は自動で開始される）
            self.device = dai.Device(self.pipeline)

            # ストリーム取得
            self.video_stream = self.device.getOutputQueue(name="preview")
            try:
                self.depth_stream = self.device.getOutputQueue(name="depth")
            except Exception as e:
                logging.error(f"深度ストリーム取得エラー: {e}")
                self.depth_stream = None  # 深度機能は無効化

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
                self.depth_stream = None
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

    def get_depth_frame(self) -> Optional[Any]:
        """最新の深度フレーム (numpy 配列) を取得。取得できなければ None."""
        if not self._initialized or self.depth_stream is None:
            return None
        try:
            depth_msg = self.depth_stream.get()
            # DepthAI の ImgFrame から numpy 配列へ変換
            depth_frame = depth_msg.getFrame()   # getFrame() は uint16 (mm) データを返す
            return depth_frame
        except Exception as e:
            logging.error(f"深度フレーム取得エラー: {e}")
            return None

    def get_depth_at(self, x: int, y: int) -> float:
        """
        (x, y) のピクセル座標に対する深度を mm 単位で返す。
        取得できない場合は 0.0 を返す（呼び出し側でエラーハンドリング）。
        """
        depth_frame = self.get_depth_frame()
        if depth_frame is None:
            return 0.0
        # 範囲チェック
        h, w = depth_frame.shape
        if not (0 <= x < w and 0 <= y < h):
            return 0.0
        # DepthAI の深度は uint16 (mm) なのでそのまま返す
        raw_depth = float(depth_frame[y, x])
        # DepthAI が cm 単位を返す場合、mm に変換（自動判定）
        if raw_depth > 5000:          # 実測距離上限の約2倍以上なら cm とみなす
            corrected = raw_depth / 10.0   # cm → mm に変換
            print(f"[DEBUG] Converting cm→mm: {raw_depth} -> {corrected} mm")
            return corrected
        print(f"[DEBUG] Raw depth (mm): {raw_depth} mm")
        return raw_depth

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
            self.depth_stream = None   # 追加
            self._initialized = False

    def load_calibration(self, file_path: str) -> bool:
        """キャリブレーションデータをファイルから読み込む"""
        try:
            import json
            with open(file_path, "r", encoding="utf-8") as f:
                calib_data = json.load(f)
            self.calibration_data = calib_data
            return True
        except Exception as e:
            logging.error(f"キャリブレーションデータ読み込みエラー: {e}")
            return False

    def get_confidence_map(self) -> Optional[Any]:
        """最新の信頼度マップ (numpy 配列) を取得。取得できなければ None."""
        if not self._initialized or self.depth_stream is None:
            return None
        try:
            depth_msg = self.depth_stream.get()
            # DepthAI が confidence map を提供する場合
            if hasattr(depth_msg, 'getConfidenceMap'):
                return depth_msg.getConfidenceMap()
            else:
                return None
        except Exception as e:
            logging.error(f"信頼度マップ取得エラー: {e}")
            return None
