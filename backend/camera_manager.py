# camera_manager.py（簡素版）
import logging
from typing import Optional, Any
from datetime import timedelta

import depthai as dai  # used for pipeline creation
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
        # ★RGB フレームサイズキャッシュ（座標スケーリング用）
        self._rgb_frame_width: int = 1280
        self._rgb_frame_height: int = 800
        # ★深度フレームサイズキャッシュ
        self._depth_frame_width: int = 640
        self._depth_frame_height: int = 360

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
            
            # ステップ 3: プレビュー出力を requestOutput で作成
            logging.debug("[initialize_camera] Setting up preview output...")
            preview = cam_rgb.requestOutput((1280, 800), type=dai.ImgFrame.Type.RGB888p)
            
            # ステップ 3.5: 出力ストリームの FPS 設定は不要です。preview の setFps はサポートされていません。
            
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
                logging.info("[initialize_camera] ? Depth stream created successfully")
            except Exception as depth_err:
                logging.warning(f"[initialize_camera] 深度ストリーム設定エラー（無視）: {depth_err}")
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
                cv_frame = frame.getCvFrame()
                # ★RGB フレームサイズをキャッシュ
                if cv_frame is not None and hasattr(cv_frame, 'shape'):
                    h, w = cv_frame.shape[:2]
                    if self._rgb_frame_height != h or self._rgb_frame_width != w:
                        logging.debug(f"[get_frame] RGB フレームサイズ: {w}x{h}")
                        self._rgb_frame_width = w
                        self._rgb_frame_height = h
                return cv_frame
            raise RuntimeError("No frame received")
        except Exception as e:
            logging.error(f"フレーム取得エラー: {e}")
            from PyQt6.QtGui import QImage
            width, height = 1280, 800
            placeholder = QImage(width, height, QImage.Format.Format_RGB888)
            placeholder.fill(Qt.GlobalColor.lightGray)
            return placeholder

    def get_depth_frame(self) -> Optional[Any]:
        if not self._initialized or self.depth_stream is None:
            logging.debug("Depth stream not initialized")
            return None
        try:
            # DepthAI 3.1 新 API: timeout as timedelta
            # ★タイムアウトを 10ms から 100ms に増加（フレームが間に合うように）
            depth_msg = self.depth_stream.get(timeout=timedelta(milliseconds=100))
        except TypeError:
            # 旧 API が残っている場合のフォールバック
            try:
                depth_msg = self.depth_stream.get(timeoutMs=100)
            except Exception as e:
                logging.warning(f"Depth stream get() failed (fallback): {e}")
                depth_msg = None
        except Exception as e:
            logging.warning(f"Depth stream get() error: {e}")
            depth_msg = None

        if depth_msg is None:
            return None
        try:
            frame = depth_msg.getFrame()
            # ★深度フレームサイズをキャッシュ（初回）
            if frame is not None and frame.shape:
                h, w = frame.shape[:2]
                if self._depth_frame_height != h or self._depth_frame_width != w:
                    logging.info(f"[get_depth_frame] 深度フレームサイズ更新: {self._depth_frame_width}x{self._depth_frame_height} -> {w}x{h}")
                    self._depth_frame_width = w
                    self._depth_frame_height = h
            logging.debug(
                f"Depth frame obtained: shape={frame.shape}, dtype={frame.dtype}"
            )
            return frame
        except Exception as e:
            logging.error(f"Failed to extract depth frame: {e}")
            return None

    def get_depth_mm(self, x: int, y: int) -> float:
        """(x, y) の深度を mm 単位で返す
        
        注意: x, y は RGB フレーム座標です。
        内部で深度フレームに自動的にスケーリングされます。
        """
        depth_frame = self.get_depth_frame()
        if depth_frame is None:
            logging.warning(f"[get_depth_mm] 深度フレームが None (x={x}, y={y})")
            return 0.0
        
        # カラーフレームと深度フレームの解像度取得
        depth_h, depth_w = depth_frame.shape
        color_w, color_h = 1280, 800  # カラーフレーム解像度
    
        # 座標を深度フレーム座標系に変換
        depth_x = int(x * depth_w / color_w)
        depth_y = int(y * depth_h / color_h)
    
        # 範囲チェック
        if not (0 <= depth_x < depth_w and 0 <= depth_y < depth_h):
            logging.debug(f"座標が範囲外: depth({depth_x}, {depth_y}), フレーム size=({depth_w}x{depth_h})")
            return 0.0
    
        depth_value = float(depth_frame[depth_y, depth_x])
        if depth_value > 0:
            logging.debug(f"深度値取得: color({x}, {y}) -> depth({depth_x}, {depth_y}) -> {depth_value:.1f} mm")
        return depth_value
    
    def _scale_rgb_to_depth_coords(self, x: int, y: int) -> tuple[int, int]:
        """RGB フレーム座標を深度フレーム座標にスケーリングする
        
        Args:
            x, y: RGB フレーム上の座標
            
        Returns:
            tuple[int, int]: 深度フレーム上の座標
        """
        if self._rgb_frame_width <= 0 or self._rgb_frame_height <= 0:
            return (x, y)
        
        scale_x = self._depth_frame_width / self._rgb_frame_width
        scale_y = self._depth_frame_height / self._rgb_frame_height
        
        depth_x = int(x * scale_x)
        depth_y = int(y * scale_y)
        
        logging.debug(f"[_scale_rgb_to_depth_coords] RGB({x}, {y}) -> Depth({depth_x}, {depth_y}) (scale: {scale_x:.3f}, {scale_y:.3f})")
        
        return (depth_x, depth_y)
    
    def _get_nearby_depth_mm(self, x: int, y: int, depth_frame: Any) -> float:
        """
        周囲の深度値から有効な値を探索する（ノイズ対応）
        
        Args:
            x, y: 基準座標
            depth_frame: 深度フレーム
            
        Returns:
            float: 見つかった有効な深度値（mm）。見つからない場合は 0.0
        """
        h, w = depth_frame.shape
        search_radius = 10  # 検索半径（ピクセル）
        
        for dy in range(-search_radius, search_radius + 1):
            for dx in range(-search_radius, search_radius + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    try:
                        depth_val = float(depth_frame[ny, nx])
                        if depth_val > 0:
                            logging.info(f"[_get_nearby_depth_mm] 周囲値から代替深度取得: ({x}, {y}) -> ({nx}, {ny}) = {depth_val:.1f} mm")
                            return depth_val
                    except Exception:
                        pass
        
        logging.warning(f"[_get_nearby_depth_mm] 周囲検索でも有効な深度が見つかりません: ({x}, {y})")
        return 0.0

    def get_depth_mm_at(self, x: int, y: int) -> float:
        """互換性維持"""
        return self.get_depth_mm(x, y)

    def get_depth_at(self, x: int, y: int) -> float:
        """互換性維持"""
        return self.get_depth_mm(x, y)
    
    def get_raw_depth_at(self, x: int, y: int) -> float:
        """
        深度フレーム座標 (x, y) から深度を取得します（座標変換なし）

        Args:
            x (int): 深度フレーム上の X 座標
            y (int): 深度フレーム上の Y 座標

        Returns:
            float: 深度値 (mm)。範囲外または取得失敗時は 0.0 を返す
        """
        depth_frame = self.get_depth_frame()
        if depth_frame is None:
            logging.warning(f"[get_raw_depth_at] 深度フレームが None (x={x}, y={y})")
            return 0.0

        # 深度フレームのサイズを取得
        h, w = depth_frame.shape
        if not (0 <= x < w and 0 <= y < h):
            logging.debug(f"[get_raw_depth_at] 座標が範囲外: ({x}, {y}), フレーム size=({w}x{h})")
            return 0.0

        depth_value = float(depth_frame[y, x])
        if depth_value > 0:
            logging.debug(f"[get_raw_depth_at] 深度値取得: ({x}, {y}) -> {depth_value:.1f} mm")
        return depth_value

    def get_rgb_dimensions(self) -> tuple[int, int]:
        """
        現在の RGB フレーム幅と高さを取得する。
        カメラが未初期化またはフレーム未取得の場合はデフォルト (1280, 800) を返す。
        """
        return (self._rgb_frame_width, self._rgb_frame_height)

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
