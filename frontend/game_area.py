# game_area.py
import sys
import os
from typing import List, Tuple, Optional
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QSizePolicy,
    QPushButton,
    QHBoxLayout,
)
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QMouseEvent, QPainter, QColor, QPen, QImage, QPixmap, QCloseEvent, QPolygonF
 
from backend.camera_manager import CameraManager
from backend.screen_manager import ScreenManager
from backend.ball_tracker import BallTracker

# Removed unused interface imports
 
import logging
from common.config import OX_GAME_TARGET_FPS, timer_interval_ms
from common.logger import logger


class GameArea(QWidget):
    """
    カメラ映像を全画面に表示し、クリックで 4 点（左上・右上・左下・右下）を取得できる UI。
    - 起動時に既存のログがあれば点とオーバーレイを描画
    - クリックごとに点を保存し、4 点揃ったら ScreenManager に保存
    """

    def __init__(self, camera_manager: CameraManager, screen_manager: ScreenManager) -> None:
        super().__init__()
        self.setWindowTitle("スクリーン領域設定")
        self.setGeometry(100, 100, 800, 600)

        self.camera_manager = camera_manager
        self.screen_manager = screen_manager
        # BallTracker を初期化してヒット座標取得に利用
        self.ball_tracker = BallTracker(screen_manager)

        # カメラフレームを表示する QLabel
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # ラベルがウィンドウ領域全体を占有し、画像を自動リサイズ
        self.video_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.video_label.setScaledContents(True)

        # ボタンレイアウト
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_area)  # type: ignore
        self.save_btn.setEnabled(False)  # 初期状態では無効
        button_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("キャンセル")
        self.cancel_btn.clicked.connect(self.cancel_area)  # type: ignore
        button_layout.addWidget(self.cancel_btn)

        self.reset_btn = QPushButton("再設定")
        self.reset_btn.clicked.connect(self.reset_area)  # type: ignore
        button_layout.addWidget(self.reset_btn)

        layout = QVBoxLayout()
        layout.addWidget(self.video_label)
        layout.addLayout(button_layout)
        self.setLayout(layout)

        # 取得した点 (QPointF のリスト)
        self.points: List[QPointF] = []

        # タイマーで映像を更新
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
self.timer.start(timer_interval_ms(OX_GAME_TARGET_FPS))  # 約30fps (config)

        # ログがあればロードして表示
        try:
            self.screen_manager.load_log()
            if self.screen_manager.screen_area is not None:
                screen_area = self.screen_manager.screen_area
                if isinstance(screen_area, list) and len(screen_area) >= 4:  # type: ignore
                    self.points = [
                        QPointF(screen_area[0][0], screen_area[0][1]),
                        QPointF(screen_area[1][0], screen_area[1][1]),
                        QPointF(screen_area[2][0], screen_area[2][1]),
                        QPointF(screen_area[3][0], screen_area[3][1])
                    ]
                    print("ログデータから4点を正常に読み込みました")
                else:
                    import json
                    log_file = "ScreenAreaLogs/area_log.json"
                    if os.path.exists(log_file):
                        with open(log_file, 'r', encoding='utf-8') as f:
                            log_data_list = json.load(f)
                            if log_data_list and isinstance(log_data_list, list) and len(log_data_list) > 0:  # type: ignore
                                latest_log = log_data_list[-1]  # type: ignore
                                if "points" in latest_log and isinstance(latest_log["points"], list):  # type: ignore
                                    points = latest_log["points"]
                                    if len(points) >= 4:  # type: ignore
                                        self.points = [
                                            QPointF(points[0][0], points[0][1]),
                                            QPointF(points[1][0], points[1][1]),
                                            QPointF(points[2][0], points[2][1]),
                                            QPointF(points[3][0], points[3][1])
                                        ]
                                        print("ログデータから4点を正常に読み込みました")
        except Exception as e:
            print(f"ログ読み込みエラー: {e}")
            try:
                import json
                log_file = "ScreenAreaLogs/area_log.json"
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        log_data_list = json.load(f)
                        if log_data_list and isinstance(log_data_list, list) and len(log_data_list) > 0:  # type: ignore
                            latest_log = log_data_list[-1]  # type: ignore
                            if "points" in latest_log and isinstance(latest_log["points"], list):  # type: ignore
                                points = latest_log["points"]
                                if len(points) >= 4:  # type: ignore
                                    self.points = [
                                        QPointF(points[0][0], points[0][1]),
                                        QPointF(points[1][0], points[1][1]),
                                        QPointF(points[2][0], points[2][1]),
                                        QPointF(points[3][0], points[3][1])
                                    ]
                                    print("ログデータから4点を正常に読み込みました")
            except Exception as read_error:
                print(f"直接ログ読み込みエラー: {read_error}")
                self.points = []

    def update_frame(self) -> None:
        """カメラフレーム取得 → QLabel に描画 + オーバーレイ"""
        try:
            frame = self.camera_manager.get_frame()
        except Exception as e:
            logging.error(f"カメラ取得エラー: {e}")
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
                if len(frame.shape) == 2:
                    height, width = frame.shape
                    bytes_per_line = width
                    img_format = QImage.Format.Format_Grayscale8
                else:
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
                logging.error(f"フレーム取得時の形状エラー: {e}")
                return
        pix = QPixmap.fromImage(q_img)

        painter = QPainter(pix)

        width = pix.width()
        height = pix.height()

        cols, rows = 8, 6
        cell_w = width // cols
        cell_h = height // rows

        pen_grid = QPen(QColor(200, 200, 200), 1)
        painter.setPen(pen_grid)

        for c in range(1, cols):
            x = c * cell_w
            painter.drawLine(x, 0, x, height)
        for r in range(1, rows):
            y = r * cell_h
            painter.drawLine(0, y, width, y)

        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)
        pen_num = QPen(QColor(255, 0, 0))
        painter.setPen(pen_num)

        num = 1
        for r in range(rows):
            for c in range(cols):
                x = c * cell_w + 5
                y = r * cell_h + 15
                painter.drawText(x, y, str(num))
                num += 1




        # Draw vertical center line
        pen = QPen(QColor(0, 255, 0), 2)
        painter.setPen(pen)

        w, h = pix.width(), pix.height()
        painter.drawLine(w // 2, 0, w // 2, h)

        # Draw green circle at the screen center
        radius = 30
        painter.drawEllipse(QPointF(w // 2, h // 2), radius, radius)  # type: ignore

        # ---- 描画クリックポイントと四角形オーバーレイ ----
        # クリックした点を赤い円で表示
        if self.points:
            pen_points = QPen(QColor(255, 0, 0), 3)  # 赤色、太さ3
            painter.setPen(pen_points)
            for pt in self.points:
                painter.drawEllipse(QPointF(int(pt.x()), int(pt.y())), 5, 5)  # type: ignore

        # ポイントが2つ以上ある場合は線で結んでポリゴン（四角形）を描画
        if len(self.points) >= 2:
            pen_polygon = QPen(QColor(0, 0, 255), 2)  # 青色、太さ2
            painter.setPen(pen_polygon)
            polygon = QPolygonF([QPointF(int(pt.x()), int(pt.y())) for pt in self.points])
            painter.drawPolygon(polygon)  # type: ignore






        painter.end()
        self.video_label.setPixmap(
            pix.scaled(
                self.video_label.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.frame_width = width
        self.frame_height = height

    def mousePressEvent(self, a0: QMouseEvent | None) -> None:
        """クリックで点を取得し、4 点揃ったら保存"""
        if len(self.points) >= 4:
            return

        if a0 is None:
            return
        pos = a0.position()

        label_w = self.video_label.width()
        label_h = self.video_label.height()
        scale_x = getattr(self, "frame_width", 800) / max(label_w, 1)
        scale_y = getattr(self, "frame_height", 600) / max(label_h, 1)

        real_point = QPointF(pos.x() * scale_x, pos.y() * scale_y)
        self.points.append(real_point)

        if len(self.points) == 4:
            self.save_btn.setEnabled(True)

        self.update()

    def save_area(self) -> None:
        """領域を保存"""
        if len(self.points) != 4:
            return

        pts: List[Tuple[int, int]] = [(int(p.x()), int(p.y())) for p in self.points]
        self.screen_manager.set_screen_area(pts)
        logger.log_screen_area({"points": pts})
        self.save_btn.setEnabled(False)
        self.close()

    def cancel_area(self) -> None:
        """キャンセル"""
        self.points = []
        self.save_btn.setEnabled(False)
        self.update()

    def reset_area(self) -> None:
        """再設定"""
        self.points = []
        self.save_btn.setEnabled(False)
        self.update()

    def closeEvent(self, a0: Optional[QCloseEvent]) -> None:
        """ウィンドウが閉じられたときにタイマー停止・カメラ解放"""
        self.timer.stop()
        try:
            self.camera_manager.close_camera()
        finally:
            super().closeEvent(a0)


def main() -> None:
    app = QApplication(sys.argv)
    cam = CameraManager()
    scr = ScreenManager()
    if not cam.initialize_camera():
        sys.exit("カメラ初期化失敗")
    win = GameArea(cam, scr)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
