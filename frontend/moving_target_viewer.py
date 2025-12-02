"""
動くターゲットを表示するウィンドウ
"""

from PyQt6.QtWidgets import (
    QMainWindow,
    QLabel,
    QVBoxLayout,
    QWidget,
    QMessageBox,
    QSizePolicy,
)
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QCloseEvent
from PyQt6.QtCore import Qt, QTimer
from typing import Any, Optional
from backend.camera_manager import CameraManager
from backend.screen_manager import ScreenManager
from backend.ball_tracker import BallTracker
from backend.moving_target_manager import MovingTargetManager
from common.hit_detection import FrontCollisionDetector
from common.depth_service import DepthMeasurementService, DepthConfig as DepthServiceConfig
import cv2
import numpy as np
from pathlib import Path
import os
from backend.target_manager import TargetManager

class MovingTargetViewer(QMainWindow):
    """動くターゲットを表示するウィンドウ"""
    front_detector: FrontCollisionDetector
    zoom_factor: float = 1.0
    timer: QTimer
    
    def __init__(
        self,
        camera_manager: CameraManager,
        screen_manager: ScreenManager,
        ball_tracker: BallTracker,
        front_detector: Optional[FrontCollisionDetector] = None,
    ):
        super().__init__()
        self.setWindowTitle("動くターゲット表示")
        self.setGeometry(100, 100, 800, 600)
        
        # コンポーネントの保持
        self.camera_manager = camera_manager
        self.screen_manager = screen_manager
        self.ball_tracker = ball_tracker
        
        # 動くターゲット管理
        self.moving_target_manager = MovingTargetManager(screen_manager)

        # 前面スクリーン衝突検知器（共通） ? 外部から渡された検知器があればそれを使用
        if front_detector is not None:
            self.front_detector = front_detector
        else:
            self.front_detector = FrontCollisionDetector(screen_manager)
        
        # 深度測定サービス（DepthService）初期化
        depth_config = DepthServiceConfig(
            min_valid_depth_m=0.5,
            max_valid_depth_m=5.0,
            interpolation_radius=10
        )
        self.depth_measurement_service = DepthMeasurementService(
            camera_manager,
            depth_config
        )
        
        # カメラフレーム表示用ラベル
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Make the image label expand to fill available space
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding,
                                       QSizePolicy.Policy.Expanding)

        # 検出情報ラベル（デバッグ用）
        self.detection_label = QLabel()
        self.detection_label.setText("検出情報: -")
        self.detection_label.setStyleSheet("background-color: #f0f0f0; padding: 4px;")
        # Make the detection label expand horizontally but keep fixed height
        self.detection_label.setSizePolicy(QSizePolicy.Policy.Expanding,
                                            QSizePolicy.Policy.Fixed)

        # ズームコントロール（削除済み）
        
        # レイアウト設定
        layout = QVBoxLayout()
        layout.addWidget(self.detection_label)

        # ズームコントロールレイアウト（削除済み）
        layout.addWidget(self.image_label)
        
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        # タイマー設定（FPSに合わせて更新）
        from common.config import TARGET_FPS
        self.timer_interval = 1000 // TARGET_FPS  # ms
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)  # type: ignore
        self.timer.start(self.timer_interval)
        
        # Set minimum window size to prevent extreme shrinking
        self.setMinimumSize(400, 300)
        
        # 初期化
        self.is_initialized = False
        self.initialize()
    
    def initialize(self):
        """初期化処理"""
        try:
            # 移動範囲を読み込み
            if not self.moving_target_manager.load_bounds():
                QMessageBox.warning(self, "警告", "移動範囲の読み込みに失敗しました")
                return

            # アクティブターゲット取得
            target_manager = TargetManager()
            active_name = target_manager.get_active_target()

            if active_name:
                default_image = os.path.join("assets", "targets", active_name)
            else:
                # フォールバック: 既存のハードコード画像（存在すれば使用）またはスキップ
                fallback_path = "assets/targets/8369a130-b841-4da4-9f1e-e51ca0f7f6a6.jpg"
                default_image = fallback_path if os.path.exists(fallback_path) else None

            # デフォルト画像が取得できたらターゲット追加
            if default_image and Path(default_image).exists():
                self.moving_target_manager.add_target(default_image)
            else:
                QMessageBox.warning(
                    self,
                    "警告",
                    f"デフォルト画像が見つかりません: {default_image or 'None'}"
                )
                # ここでターゲット追加はスキップ
                print("デフォルト画像が見つからないため、ターゲットを追加しません。")
            
            print("動くターゲットビューアーが初期化されました")
            self.is_initialized = True
            
        except Exception as e:
            print(f"初期化エラー: {e}")
            QMessageBox.critical(self, "エラー", f"初期化に失敗しました: {e}")
    
    def update_frame(self) -> None:
        """フレームを更新"""
        if not self.is_initialized:
            return
            
        try:
            # カメラからフレームを取得
            frame = self.camera_manager.get_frame()
            if not isinstance(frame, np.ndarray):
                print("カメラフレームが取得できませんまたは無効です")
                return
                
            # 動くターゲットを更新
            self.moving_target_manager.update_all()
            
            # ボール位置を取得して、動くターゲットへの当たり判定
            ball_pos = self.ball_tracker.get_last_detected_position()
            if ball_pos is not None:
                # ボール位置での深度を測定
                ball_x, ball_y = ball_pos
                depth_m = self.depth_measurement_service.measure_at_rgb_coords(ball_x, ball_y)
                confidence = self.depth_measurement_service.get_confidence_score(ball_x, ball_y)
                depth_source = "Service (RT)" if depth_m > 0 else "Cache"
                
                # 動くターゲットへの当たり判定
                collisions = self.moving_target_manager.check_ball_collision(ball_pos)
                if collisions:
                    collision_msg = f"ボールがターゲットに当たった！\n深度: {depth_m:.2f}m (信頼度: {confidence:.2f}) [{depth_source}]"
                    QMessageBox.information(self, "当たり！", collision_msg)

            # 前面スクリーンへの衝突判定（深度を含む検出結果で判定）
            detected = self.ball_tracker.get_hit_area(frame)  # type: ignore[arg-type]
            hit = self.front_detector.update_and_check(detected)
            if hit is not None:
                # 前面スクリーンに当たった場合の表示/処理
                QMessageBox.information(self, "衝突検知", "前面スクリーンに衝突しました！")
            
            # 検出情報を取得（改善: 両ゲームモード共通機能）
            detection_info = self.ball_tracker.get_detection_info(frame)  # type: ignore[arg-type]
            if detection_info:
                if detection_info["detected"]:
                    status = f"✓ 検出中 | 輪郭: {detection_info['contour_count']} | 面積: {detection_info['max_area']:.0f}"
                    self.detection_label.setStyleSheet("background-color: #e8f5e9; padding: 4px;")
                else:
                    status = f"✗ 未検出 | ピクセル: {detection_info['pixel_count']}"
                    self.detection_label.setStyleSheet("background-color: #ffebee; padding: 4px;")
                self.detection_label.setText(status)
            
            # ウィンドウサイズに合わせてフレームをスケーリング
            label_w = self.image_label.width()
            label_h = self.image_label.height()
            # Ensure we are working with a numpy array
            frame_np: np.ndarray = frame
            h, w = frame_np.shape[:2]
            scale_w = label_w / w if w > 0 else 1.0  # type: ignore
            scale_h = label_h / h if h > 0 else 1.0  # type: ignore
            # 保持アスペクト比で最小スケールを使用
            self.zoom_factor = min(scale_w, scale_h, 1.0)  # type: ignore
            if self.zoom_factor != 1.0:
                new_w = int(w * self.zoom_factor)  # type: ignore
                new_h = int(h * self.zoom_factor)  # type: ignore
                display_frame = cv2.resize(frame_np.astype(np.uint8), (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            else:
                display_frame = frame_np

            annotated_frame = self._draw_targets(display_frame)
            
            # 画像を表示
            self._display_frame(annotated_frame)
            
        except Exception as e:
            print(f"フレーム更新エラー: {e}")
    
    def _draw_targets(self, frame: Any) -> QImage:
        """ターゲットをフレームに描画"""
        try:
            # 画像をQImageに変換
            height, width = frame.shape[:2]
            
            # RGBからBGRへ変換（OpenCVの形式）
            if len(frame.shape) == 3:
                bgr_frame = frame[:, :, ::-1]  # BGRに変換
            else:
                bgr_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                
            # NumPy配列をbytesに変換してQImageに渡す
            bytes_per_line = width * 3
            qimage = QImage(
                bgr_frame.tobytes(),  # type: ignore
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_BGR888
            )  # type: ignore
            
            # QPainterで描画
            painter = QPainter(qimage)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # 動くターゲットを描画
            targets = self.moving_target_manager.get_targets()
            for target in targets:
                x, y = target.position
                # ズーム倍率を座標に適用
                x = int(x * self.zoom_factor)
                y = int(y * self.zoom_factor)
                # 画像ファイルから読み込み、リサイズして描画
                try:
                    # プロジェクトルートからの絶対パス取得
                    project_root = Path(__file__).resolve().parents[1]   # frontend の上位がプロジェクトルート
                    img_path = (project_root / target.image_path).as_posix()
                    
                    img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
                    if img is not None:
                        # ターゲット表示サイズ（例: 100x100px）
                        target_size = 100
                        resized_img = cv2.resize(img, (target_size, target_size), interpolation=cv2.INTER_AREA)
                        
                        # BGRからRGBに変換
                        if len(resized_img.shape) == 3:
                            rgb_img = cv2.cvtColor(resized_img, cv2.COLOR_BGR2RGB)
                        else:
                            rgb_img = cv2.cvtColor(resized_img, cv2.COLOR_GRAY2RGB)
                        
                        # QImageに変換
                        bytes_per_line = target_size * 3
                        qimage_target = QImage(
                            rgb_img.tobytes(),
                            target_size,
                            target_size,
                            bytes_per_line,
                            QImage.Format.Format_RGB888
                        )
                        painter.drawImage(x, y, qimage_target)
                    else:
                        # 画像読み込み失敗時は矩形描画をフォールバック
                        print(f"画像読み込み失敗: {img_path}")  # 一度だけ警告
                        painter.setPen(QPen(QColor(255, 0, 0), 2))
                        painter.drawRect(x, y, 100, 100)
                except Exception as e:
                    print(f"画像描画エラー: {e}")
                    # エラー時は矩形描画をフォールバック
                    painter.setPen(QPen(QColor(255, 0, 0), 2))
                    painter.drawRect(x, y, 100, 100)
                
            painter.end()
            
            return qimage
            
        except Exception as e:
            print(f"描画エラー: {e}")
            return QImage()
    
    def _display_frame(self, qimage: QImage) -> None:
        """フレームをラベルに表示"""
        try:
            if not qimage.isNull():
                pixmap = QPixmap.fromImage(qimage)
                self.image_label.setPixmap(pixmap.scaled(
                    self.image_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
        except Exception as e:
            print(f"表示エラー: {e}")

    # ズームスライダーは削除されました

    def closeEvent(self, a0: Optional[QCloseEvent] = None) -> None:
        """ウィンドウクローズ時の処理"""
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
        print("動くターゲットビューアーが閉じられました")
        super().closeEvent(a0)
