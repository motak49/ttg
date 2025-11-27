# camera_manager.py
import logging
from typing import Optional, Any

import depthai as dai
from PyQt6.QtCore import Qt

from backend.interfaces import CameraInterface
from backend.depthai_compat import (
    create_node,
    create_device,
    safe_link,
)


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
        カメラを実機でカラー画像取得モードで初期化する（depthai 3.1.0 対応）。
        1920x1080 (THE_1080_P) 解像度、self.fps fps を設定。
        
        depthai 3.1.0 ではパイプラインモデルが大きく変わったため、
        以下の変更を実装:
        - XLinkOut ノード廃止 → Output.createOutputQueue() を使用
        - Device(pipeline) 廃止 → Output から直接キューを生成
        """
        try:
            # デバッグ: 初期化前のデバイス状態を確認
            logging.debug("[initialize_camera] Starting camera initialization")
            available_devices = dai.Device.getAllAvailableDevices()
            logging.info(f"[initialize_camera] Available devices before init: {[d.name for d in available_devices]}")
            
            # デバイス情報をキャッシュ（後で create_device に渡すため）
            device_info_to_use = available_devices[0] if len(available_devices) > 0 else None
            if device_info_to_use:
                logging.info(f"[initialize_camera] Using device: {device_info_to_use.name}")
            else:
                raise RuntimeError("No DepthAI devices found during initialization")
            
            # 既存デバイスが残っている場合はクローズしてリセット
            if self.device is not None:
                try:
                    self.device.close()
                except Exception as e_close:
                    logging.warning(f"既存デバイスのクローズに失敗: {e_close}")
                finally:
                    self.device = None
            
            # **デバイス作成（Pipeline 作成前）**
            logging.debug("[initialize_camera] Creating device...")
            self.device = create_device(self.pipeline, device_info_to_use)
            logging.info("[initialize_camera] Device created successfully")
            
            # Pipeline の作成（Device 作成後）
            self.pipeline = dai.Pipeline()

            # カラーカメラ設定（ColorCamera は deprecated だが互換性のため使用）
            try:
                color_cam = create_node(self.pipeline, dai.node.ColorCamera, legacy_name='createColorCamera')
                # 解像度は 1920x1080 (DepthAI がサポートする最大解像度)
                color_cam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
                # FPS 設定
                color_cam.setFps(self.fps)

                # カラーデータを BGR 順序で取得（OpenCV 互換）
                try:
                    color_cam.setInterleaved(False)
                except Exception:
                    pass
                try:
                    color_cam.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
                except Exception:
                    pass
            except Exception as color_err:
                logging.error(f"カラーカメラ作成エラー: {color_err}")
                try:
                    self.device.close()
                except Exception:
                    pass
                finally:
                    self.device = None
                raise

            # ----- ステレオ深度ストリームの構築 （オプション、エラー時は無視） -----
            try:
                mono_left = create_node(self.pipeline, dai.node.MonoCamera, legacy_name='createMonoCamera')
                mono_right = create_node(self.pipeline, dai.node.MonoCamera, legacy_name='createMonoCamera')
                mono_left.setResolution(dai.MonoCameraProperties.SensorResolution.THE_720_P)
                mono_right.setResolution(dai.MonoCameraProperties.SensorResolution.THE_720_P)
                mono_left.setBoardSocket(dai.CameraBoardSocket.LEFT)
                mono_right.setBoardSocket(dai.CameraBoardSocket.RIGHT)

                stereo = create_node(self.pipeline, dai.node.StereoDepth, legacy_name='createStereoDepth')
                try:
                    # depthai 3.1.0: HIGH_DENSITY は HIGH_DETAIL に変更
                    stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DETAIL)
                except Exception:
                    pass

                # 深度出力サイズをカラーフレーム解像度に合わせる（1920x1080）
                color_width, color_height = 1920, 1080
                try:
                    stereo.setOutputSize(color_width, color_height)
                except Exception:
                    pass

                # リンク処理も安全に行う
                safe_link(mono_left, stereo, src_candidates=['out'], dst_candidates=['left', 'inputLeft'])
                safe_link(mono_right, stereo, src_candidates=['out'], dst_candidates=['right', 'inputRight'])
                
                # 深度ストリーム作成を試みる
                logging.debug("Depth pipeline setup completed")
                depth_enabled = True
            except Exception as depth_err:
                logging.warning(f"深度ストリーム設定エラー（無視）: {depth_err}")
                depth_enabled = False
                stereo = None            stereo = create_node(self.pipeline, dai.node.StereoDepth, legacy_name='createStereoDepth')
            try:
                # depthai 3.1.0: HIGH_DENSITY は HIGH_DETAIL に変更
                stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DETAIL)
            except Exception:
                pass

            # 深度出力サイズをカラーフレーム解像度に合わせる（1920x1080）
            color_width, color_height = 1920, 1080
            try:
                stereo.setOutputSize(color_width, color_height)
            except Exception:
                pass

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

            # リンク処理も安全に行う
            safe_link(mono_left, stereo, src_candidates=['out'], dst_candidates=['left', 'inputLeft'])
            safe_link(mono_right, stereo, src_candidates=['out'], dst_candidates=['right', 'inputRight'])

            # depthai 3.1.0 では XLinkOut が廃止。
            # Output から直接キューを生成する。
            # プレビュー（カラー）ストリーム
            try:
                self.video_stream = color_cam.video.createOutputQueue(maxSize=4, blocking=False)
                logging.debug("Preview stream created via Output.createOutputQueue()")
            except Exception as e:
                logging.error(f"プレビューストリーム作成エラー: {e}")
                # デバイスをクローズしてリセット
                try:
                    self.device.close()
                except Exception:
                    pass
                finally:
                    self.device = None
                raise

            # 深度ストリーム
            try:
                self.depth_stream = stereo.depth.createOutputQueue(maxSize=4, blocking=False)
                logging.debug("Depth stream created via Output.createOutputQueue()")
            except Exception as e:
                logging.error(f"深度ストリーム取得エラー: {e}")
                # デバイスをクローズしてリセット
                try:
                    self.device.close()
                except Exception:
                    pass
                finally:
                    self.device = None
                self.depth_stream = None  # 深度機能は無効化
                raise

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

    def get_depth_mm(self, x: int, y: int) -> float:
        """
        (x, y) のピクセル座標に対する深度を mm 単位で返す（DepthAI 出力は既に mm）。
        取得できない場合は 0.0 を返す（呼び出し側でエラーハンドリング）。
        """
        depth_frame = self.get_depth_frame()
        if depth_frame is None:
            return 0.0
        # 範囲チェック
        h, w = depth_frame.shape
        if not (0 <= x < w and 0 <= y < h):
            return 0.0
        # DepthAI の depth ストリームは既に mm 単位（uint16）
        depth_mm = float(depth_frame[y, x])
        logging.debug(f"[DEBUG] Raw depth (mm): {depth_mm} mm")
        return depth_mm

    def get_depth_mm_at(self, x: int, y: int) -> float:
        """
        (x, y) のピクセル座標に対する深度を mm 単位で返す（互換性維持）。
        取得できない場合は 0.0 を返す（呼び出し側でエラーハンドリング）。
        """
        return self.get_depth_mm(x, y)

    def get_depth_at(self, x: int, y: int) -> float:
        """
        (x, y) のピクセル座標に対する深度を **視差** 単位で返す（互換性維持）。
        取得できない場合は 0.0 を返す（呼び出し側でエラーハンドリング）。
        """
        depth_frame = self.get_depth_frame()
        if depth_frame is None:
            return 0.0
        # 範囲チェック
        h, w = depth_frame.shape
        if not (0 <= x < w and 0 <= y < h):
            return 0.0
        # DepthAI の深度は uint16 (mm) なのでそのまま返す（互換性維持）
        raw_depth = float(depth_frame[y, x])
        logging.debug(f"Raw depth (disparity): {raw_depth} disparity")
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
