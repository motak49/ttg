# camera_manager.py（簡素版）
import logging
from typing import Optional, Any

import depthai as dai
from PyQt6.QtCore import Qt

from backend.interfaces import CameraInterface


class CameraManager(CameraInterface):
    """DepthAI カメラ管理クラス（実機向け）"""

    def __init__(self) -> None:
        self.pipeline: Any = None
        self.video_stream: Optional[Any] = None
        self.fps: int = 120  # ハードウェア上限 120 FPS（DepthAI カメラ最大）
        self._initialized: bool = False
        self.depth_stream: Optional[Any] = None
        self.calibration_data: Optional[dict[str, Any]] = None

    def is_initialized(self) -> bool:
        """カメラが既に初期化されているかを返す"""
        return self._initialized

    def initialize_camera(self) -> bool:
        """
        カメラを実機でカラー画像取得モードで初期化する（depthai 3.1.0 対応）。
        参考: tests/3_1_test.py の動作確認済みパターン
        """
        try:
            # ステップ 0: depthai モジュールを再ロードして内部状態をリセット
            import sys
            import gc
            logging.debug("[initialize_camera] Reloading depthai modules...")
            modules_to_remove = [
                name for name in list(sys.modules.keys())
                if 'depthai' in name or '_depthai' in name or 'pal' in name
            ]
            for module_name in modules_to_remove:
                try:
                    del sys.modules[module_name]
                except Exception:
                    pass
            gc.collect()
            # depthai を再インポート
            import depthai as dai
            logging.debug("[initialize_camera] Depthai modules reloaded")
            
            logging.debug("[initialize_camera] Starting camera initialization")
            available_devices = dai.Device.getAllAvailableDevices()
            logging.info(f"[initialize_camera] Available devices: {[d.name for d in available_devices]}")
            
            if len(available_devices) == 0:
                raise RuntimeError("No DepthAI devices found")
            
            # ステップ 1: パイプラインを作成（depthai 3.1.0: Device の前に Pipeline を作成）
            logging.debug("[initialize_camera] Creating pipeline...")
            self.pipeline = dai.Pipeline()

            # ステップ 2: Camera ノードを作成（ColorCamera ではなく Camera を使用）
            logging.debug("[initialize_camera] Creating Camera node...")
            cam_rgb = self.pipeline.create(dai.node.Camera).build()
            
            # ステップ 2.5: カラーカメラの FPS を 120 に設定（ハードウェア上限）
            logging.debug(f"[initialize_camera] Setting camera FPS to {self.fps}...")
            try:
                cam_rgb.setFps(self.fps)
                logging.info(f"[initialize_camera] Camera FPS set to {self.fps}")
            except Exception as fps_err:
                logging.warning(f"Camera FPS設定エラー（デフォルト値で続行）: {fps_err}")
            
            # ステップ 3: プレビュー出力を requestOutput で作成
            logging.debug("[initialize_camera] Setting up preview output...")
            preview = cam_rgb.requestOutput((1280, 800), type=dai.ImgFrame.Type.RGB888p)
            
            # ステップ 4: 出力キューを作成
            logging.debug("[initialize_camera] Creating output queue...")
            self.video_stream = preview.createOutputQueue()
            logging.info("[initialize_camera] Output queue created successfully")

            # ステップ 5: 深度ストリーム（オプション）
            try:
                logging.debug("[initialize_camera] Creating depth setup...")
                mono_left = self.pipeline.create(dai.node.MonoCamera)
                mono_right = self.pipeline.create(dai.node.MonoCamera)
                mono_left.setResolution(dai.MonoCameraProperties.SensorResolution.THE_720_P)
                mono_right.setResolution(dai.MonoCameraProperties.SensorResolution.THE_720_P)
                mono_left.setBoardSocket(dai.CameraBoardSocket.LEFT)
                mono_right.setBoardSocket(dai.CameraBoardSocket.RIGHT)
                
                # モノクロカメラの FPS を 120 に設定（ハードウェア上限）
                try:
                    mono_left.setFps(self.fps)
                    mono_right.setFps(self.fps)
                    logging.debug(f"Mono cameras FPS set to {self.fps}")
                except Exception as mono_fps_err:
                    logging.warning(f"Mono camera FPS設定エラー（デフォルト値で続行）: {mono_fps_err}")

                stereo = self.pipeline.create(dai.node.StereoDepth)
                try:
                    stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DETAIL)
                except Exception:
                    pass

                mono_left.out.link(stereo.left)
                mono_right.out.link(stereo.right)
                
                self.depth_stream = stereo.depth.createOutputQueue()
                logging.debug("Depth stream created successfully")
            except Exception as depth_err:
                logging.warning(f"深度ストリーム設定エラー（無視）: {depth_err}")
                self.depth_stream = None

            # ステップ 6: パイプラインを context manager で開始（depthai 3.1.0対応）
            logging.debug("[initialize_camera] Starting pipeline with context manager...")
            self.pipeline.start()
            logging.info("[initialize_camera] Pipeline started successfully")

            # 初期化成功
            self._initialized = True
            return True

        except Exception as e:
            logging.error(f"カメラ初期化エラー: {e}")
            import traceback
            traceback.print_exc()
            try:
                if self.pipeline is not None:
                    self.pipeline = None
            finally:
                self.pipeline = None
                self.video_stream = None
                self.depth_stream = None
                self._initialized = False
            return False

    def get_frame(self) -> Optional[Any]:
        """カメラフレームを取得する"""
        if not self._initialized or self.video_stream is None:
            from PyQt6.QtGui import QImage
            width, height = 1280, 800
            placeholder = QImage(width, height, QImage.Format.Format_RGB888)
            placeholder.fill(Qt.GlobalColor.lightGray)
            return placeholder

        try:
            frame = self.video_stream.get()
            if frame is not None:
                return frame.getCvFrame()
            raise RuntimeError("No frame received")
        except Exception as e:
            logging.error(f"フレーム取得エラー: {e}")
            from PyQt6.QtGui import QImage
            width, height = 1280, 800
            placeholder = QImage(width, height, QImage.Format.Format_RGB888)
            placeholder.fill(Qt.GlobalColor.lightGray)
            return placeholder

    def get_depth_frame(self) -> Optional[Any]:
        """最新の深度フレームを取得"""
        if not self._initialized or self.depth_stream is None:
            return None
        try:
            depth_msg = self.depth_stream.get()
            return depth_msg.getFrame() if depth_msg else None
        except Exception as e:
            logging.error(f"深度フレーム取得エラー: {e}")
            return None

    def get_depth_mm(self, x: int, y: int) -> float:
        """(x, y) の深度を mm 単位で返す"""
        depth_frame = self.get_depth_frame()
        if depth_frame is None:
            return 0.0
        h, w = depth_frame.shape
        if not (0 <= x < w and 0 <= y < h):
            return 0.0
        return float(depth_frame[y, x])

    def get_depth_mm_at(self, x: int, y: int) -> float:
        """互換性維持"""
        return self.get_depth_mm(x, y)

    def get_depth_at(self, x: int, y: int) -> float:
        """互換性維持"""
        return self.get_depth_mm(x, y)

    def set_fps(self, fps: int) -> None:
        """FPS を設定"""
        self.fps = fps

    def close_camera(self) -> None:
        """カメラをクローズ"""
        try:
            if self.pipeline is not None:
                # depthai 3.1.0: pipeline の自動クローズは with ブロックで管理
                pass
        except Exception as e:
            logging.error(f"カメラクローズ時エラー: {e}")
        finally:
            self.pipeline = None
            self.video_stream = None
            self.depth_stream = None
            self._initialized = False

    def load_calibration(self, file_path: str) -> bool:
        """キャリブレーションデータをロード"""
        try:
            import json
            with open(file_path, "r", encoding="utf-8") as f:
                self.calibration_data = json.load(f)
            return True
        except Exception as e:
            logging.error(f"キャリブレーション読み込みエラー: {e}")
            return False

    def get_confidence_map(self) -> Optional[Any]:
        """信頼度マップを取得"""
        if not self._initialized or self.depth_stream is None:
            return None
        try:
            depth_msg = self.depth_stream.get()
            if hasattr(depth_msg, 'getConfidenceMap'):
                return depth_msg.getConfidenceMap()
            return None
        except Exception as e:
            logging.error(f"信頼度マップ取得エラー: {e}")
            return None
