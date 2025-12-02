import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QImage, QPixmap, QCloseEvent, QMouseEvent
from common.config import TRACK_TARGET_CONFIG_FPS, timer_interval_ms, SCREEN_DEPTH_LOG_PATH
from common.depth_service import DepthMeasurementService, DepthConfig as DepthServiceConfig
from common.depth_storage import DepthStorageService
from backend.camera_manager import CameraManager
from backend.screen_manager import ScreenManager


class ClickableLabel(QLabel):
    """マウスクリックをシグナルで通知する QLabel"""
    clicked = pyqtSignal(QMouseEvent)
    
    def mousePressEvent(self, ev: Optional[QMouseEvent]) -> None:
        if ev is not None:
            self.clicked.emit(ev)
        super().mousePressEvent(ev)


class DepthConfig(QWidget):
    """
    深度設定画面（改善版）
    
    DepthMeasurementService と DepthStorageService を利用して、
    カメラ映像をグリッド付きで表示し、クリックした座標の深度を表示・保存します。
    
    【機能】
    - リアルタイムカメラ映像表示
    - クリック座標の深度値測定・表示
    - 測定結果を JSON に保存
    - 信頼度スコア計算
    """

    def __init__(self, camera_manager: CameraManager, screen_manager: ScreenManager) -> None:
        super().__init__()
        self.setWindowTitle("深度設定")
        self.setGeometry(100, 100, 1000, 700)

        self.camera_manager = camera_manager
        self.screen_manager = screen_manager
        
        # ★Service インスタンス作成
        depth_service_config = DepthServiceConfig(
            min_valid_depth_m=0.5,
            max_valid_depth_m=5.0,
            interpolation_radius=10
        )
        self.depth_measurement_service = DepthMeasurementService(
            camera_manager, 
            depth_service_config
        )
        self.depth_storage_service = DepthStorageService(SCREEN_DEPTH_LOG_PATH)

        # カメラ映像を表示する ClickableLabel (マウスクリック対応)
        self.video_label = ClickableLabel(self)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(800, 600)
        # ★ClickableLabel のシグナルに接続
        self.video_label.clicked.connect(self._on_video_click)  # type: ignore

        # 深度表示用ラベル
        self.depth_label = QLabel(self)
        self.depth_label.setText("Depth: -- m")
        self.depth_label.setStyleSheet("font-size: 16px; color: blue;")

        # ボタンレイアウト
        button_layout = QHBoxLayout()
        
        # 戻るボタン
        self.back_btn = QPushButton("戻る")
        self.back_btn.clicked.connect(self.close)  # type: ignore
        button_layout.addWidget(self.back_btn)

        # 保存ボタン
        self.save_btn = QPushButton("深度を保存")
        self.save_btn.clicked.connect(self.save_depth)  # type: ignore
        button_layout.addWidget(self.save_btn)

        # レイアウト設定
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.video_label)
        main_layout.addWidget(self.depth_label)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        # クリックされた座標
        self.last_clicked_depth_m: Optional[float] = None
        self.last_clicked_confidence: float = 0.0
        
        # フレームと表示サイズの情報（座標変換用）
        self._frame_width: int = 0
        self._frame_height: int = 0
        self._displayed_width: int = 0
        self._displayed_height: int = 0

        # タイマーで映像を更新
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)  # type: ignore
        fps_setting = TRACK_TARGET_CONFIG_FPS
        timer_interval = timer_interval_ms(fps_setting)
        logging.info(
            f"[DepthConfig] FPS設定: {fps_setting} FPS, "
            f"タイマー間隔: {timer_interval} ms"
        )
        self.timer.start(timer_interval)

    def update_frame(self) -> None:
        """カメラフレーム取得 → QLabel に描画 + グリッドをオーバーレイ"""
        try:
            frame = self.camera_manager.get_frame()
        except Exception as e:
            logging.error(f"[update_frame] カメラ取得エラー: {e}")
            frame = None

        if frame is None:
            width, height = 800, 600
            placeholder = QImage(width, height, QImage.Format.Format_RGB888)
            placeholder.fill(Qt.GlobalColor.lightGray)
            frame = placeholder

        if isinstance(frame, QImage):
            q_img = frame
        else:
            try:
                if len(frame.shape) == 2:  # モノクロ (height, width)
                    height, width = frame.shape
                    bytes_per_line = width
                    img_format = QImage.Format.Format_Grayscale8
                else:  # カラー (height, width, channels)
                    height, width, _ = frame.shape
                    bytes_per_line = 3 * width
                    img_format = QImage.Format.Format_BGR888

                q_img = QImage(
                    frame.data,
                    width,
                    height,
                    bytes_per_line,
                    img_format,
                )
            except Exception as e:
                logging.error(f"[update_frame] フレーム形状エラー: {e}")
                return

        pix = QPixmap.fromImage(q_img)

        painter = QPainter(pix)
        try:
            width = pix.width()
            height = pix.height()

            # グリッド線を描画
            self._draw_grid(painter, width, height)

            self.video_label.setPixmap(
                pix.scaled(
                    self.video_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            # 座標変換用にフレームと表示サイズを保持
            self._frame_width = width
            self._frame_height = height
            displayed_pixmap = self.video_label.pixmap()
            if displayed_pixmap:
                self._displayed_width = displayed_pixmap.width()
                self._displayed_height = displayed_pixmap.height()
            else:
                self._displayed_width = self.video_label.width()
                self._displayed_height = self.video_label.height()

        except Exception as e:
            logging.error(f"[update_frame] 描画エラー: {e}")
        finally:
            painter.end()

    def _draw_grid(self, painter: QPainter, width: int, height: int) -> None:
        """グリッド線を描画"""
        grid_size = 50  # グリッドの間隔（ピクセル）
        pen = QPen(QColor(200, 200, 200), 1)  # 軽い灰色
        painter.setPen(pen)

        # 垂直線
        for x in range(0, width, grid_size):
            painter.drawLine(x, 0, x, height)
        # 水平線
        for y in range(0, height, grid_size):
            painter.drawLine(0, y, width, y)

    def _on_video_click(self, event: Optional[QMouseEvent] = None) -> None:
        """映像上でのクリック処理 (Service 経由)"""
        if event is None:
            return
        
        try:
            # QLabel 内の座標に変換
            label_pos = self.video_label.mapFromGlobal(event.globalPosition().toPoint())

            # ラベルと実際に表示されている画像サイズの差分（余白）を計算
            offset_x = (self.video_label.width() - self._displayed_width) // 2
            offset_y = (self.video_label.height() - self._displayed_height) // 2

            # 余白分を除去して画像上の相対座標へ変換
            x_rel = label_pos.x() - offset_x
            y_rel = label_pos.y() - offset_y

            # クリックが画像領域外だったら無視
            if not (0 <= x_rel < self._displayed_width and 0 <= y_rel < self._displayed_height):
                return

            # スケール比率を算出（元フレーム ↔ 表示サイズ）
            scale_x = self._frame_width / self._displayed_width if self._displayed_width > 0 else 1.0
            scale_y = self._frame_height / self._displayed_height if self._displayed_height > 0 else 1.0

            # RGB 座標（フレーム座標）に変換
            rgb_x = int(round(x_rel * scale_x))
            rgb_y = int(round(y_rel * scale_y))

            # 座標をフレーム範囲内にクランプ
            rgb_x = max(0, min(self._frame_width - 1, rgb_x))
            rgb_y = max(0, min(self._frame_height - 1, rgb_y))

            # ★Service を使用して深度を測定
            depth_m = self.depth_measurement_service.measure_at_rgb_coords(rgb_x, rgb_y)
            confidence = self.depth_measurement_service.get_confidence_score(rgb_x, rgb_y)
            
            # 結果を保存
            self.last_clicked_depth_m = depth_m
            self.last_clicked_confidence = confidence
            
            # UI に表示
            if depth_m >= 0.0:
                self.depth_label.setText(
                    f"Depth: {depth_m:.3f} m (信頼度: {confidence:.2f})"
                )
                logging.info(
                    f"[_on_video_click] RGB({rgb_x}, {rgb_y}): "
                    f"深度={depth_m:.3f}m, 信頼度={confidence:.2f}"
                )
            else:
                self.depth_label.setText("Depth: 無効")
                logging.warning(
                    f"[_on_video_click] RGB({rgb_x}, {rgb_y}): 無効な深度値"
                )

        except Exception as e:
            logging.error(f"[_on_video_click] エラー: {e}")
            self.depth_label.setText("Depth: Error")

    def save_depth(self) -> None:
        """最後に測定した深度をファイルに保存"""
        try:
            if self.last_clicked_depth_m is None or self.last_clicked_depth_m < 0.0:
                logging.warning("[save_depth] 有効な深度値がないため、保存スキップ")
                self.depth_label.setText("Depth: 保存失敗（無効値）")
                return
            
            # ★Service を使用して保存
            success = self.depth_storage_service.save(
                self.last_clicked_depth_m,
                source="user_measurement",
                confidence=self.last_clicked_confidence
            )
            
            if success:
                logging.info(
                    f"[save_depth] ✓ 保存成功: {self.last_clicked_depth_m:.3f}m"
                )
                self.depth_label.setText("Depth: 保存完了")
                # リセット
                self.last_clicked_depth_m = None
                self.last_clicked_confidence = 0.0
            else:
                logging.error("[save_depth] ✗ 保存失敗")
                self.depth_label.setText("Depth: 保存失敗")

        except Exception as e:
            logging.error(f"[save_depth] エラー: {e}")
            self.depth_label.setText("Depth: Error")

    def closeEvent(self, a0: Optional[QCloseEvent] = None) -> None:
        """ウィンドウクローズ時の処理"""
        if hasattr(self, "timer") and self.timer.isActive():
            self.timer.stop()
        super().closeEvent(a0)
