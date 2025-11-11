# track_target_viewer.py
import sys
from typing import List, Tuple, Optional

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QSizePolicy,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QMouseEvent, QPainter, QColor, QPen, QImage, QPixmap, QPolygonF, QBrush
from backend.camera_manager import CameraManager
from backend.screen_manager import ScreenManager
from backend.ball_tracker import BallTracker

from frontend.game_logic import game_logic
import logging
from common.logger import logger
from common.config import TRACK_TARGET_CONFIG_FPS, timer_interval_ms
import cv2
import numpy as np


class TrackTargetViewer(QWidget):
    """
    トラッキング対象を確認するためのウィンドウ
    カメラ映像を表示し、現在設定されているトラッキング対象色の範囲を視覚的に表示する
    """

    def __init__(self, camera_manager: CameraManager, screen_manager: ScreenManager, ball_tracker: BallTracker) -> None:
        super().__init__()
        self.setWindowTitle("トラッキング対象確認")
        self.setGeometry(100, 100, 800, 600)

        self.camera_manager = camera_manager
        self.screen_manager = screen_manager
        self.ball_tracker = ball_tracker

        # カメラフレームを表示する QLabel
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # ラベルがウィンドウ領域全体を占有し、画像を自動リサイズ
        self.video_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.video_label.setScaledContents(True)

        # 戻るボタン
        button_layout = QHBoxLayout()
        self.back_btn = QPushButton("戻る")
        self.back_btn.clicked.connect(self.close)
        button_layout.addWidget(self.back_btn)

        layout = QVBoxLayout()
        layout.addWidget(self.video_label)
        layout.addLayout(button_layout)
        self.setLayout(layout)

        # タイマーで映像を更新（120fps固定）
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        # 120fps = 1000ms / 120 ≈ 8.33ms
        self.timer.start(8)  # 約120fps

        # ログがあればロードして表示
        try:
            # ScreenManagerのload_logメソッドでデータを読み込む
            self.screen_manager.load_log()
        except Exception as e:
            print(f"ログ読み込みエラー: {e}")

    def update_frame(self) -> None:
        """カメラフレーム取得 → QLabel に描画 + オーバーレイ"""
        # ウィンドウが閉じられている場合は処理をスキップ
        if not self.isVisible():
            return
            
        try:
            # カメラからフレーム取得（デバイス未接続時は例外を抑制）
            frame = self.camera_manager.get_frame()
        except Exception as e:
            logging.error(f"カメラ取得エラー: {e}")
            frame = None

        if frame is None:
            # デバイスが利用できない場合はプレースホルダー画像を生成
            width, height = 800, 600  # デフォルトサイズ
            placeholder = QImage(width, height, QImage.Format.Format_RGB888)
            placeholder.fill(Qt.GlobalColor.lightGray)  # 薄いグレーで塗りつぶし
            frame = placeholder

        # フレーム形状をチェックし、モノクロかカラーかで処理を分岐
        if isinstance(frame, QImage):
            q_img = frame
        else:
            try:
                if len(frame.shape) == 2:  # モノクロ (height, width)
                    height, width = frame.shape
                    bytes_per_line = width  # 1 バイト/ピクセル
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
                logging.error(f"フレーム取得時の形状エラー: {e}")
                return
        pix = QPixmap.fromImage(q_img)

        # 描画用にコピーしてオーバーレイを描く
        try:
            # ウィンドウが閉じられた場合の安全チェック
            if not self.isVisible():
                return
                
            painter = QPainter(pix)
            # ここでウィンドウ状態を再確認
            if not self.isVisible():
                painter.end()  # パイプを閉じる
                return
                
            # フレームサイズ取得
            width = pix.width()
            height = pix.height()

            # 現在設定されているトラッキング対象色を表示
            try:
                tracked_ball = self.ball_tracker.get_track_ball()
                if tracked_ball is not None:
                    # 設定された色範囲を取得
                    color_range = tracked_ball["color_range"]
                    lower_bound, upper_bound = color_range
                    # 色の情報を表示
                    color_name = self._get_color_name_from_range(lower_bound, upper_bound)
                    if color_name:
                        font = painter.font()
                        font.setPointSize(16)
                        painter.setFont(font)
                        painter.setPen(QColor(255, 0, 0))  # 赤色で表示
                        painter.drawText(10, 30, f"現在のトラッキング対象: {color_name}")

                    # 色範囲を視覚的に表示（追跡対象の色をハイライト）
                    self._draw_tracking_highlight(painter, frame, lower_bound, upper_bound)
            except Exception as e:
                print(f"トラッキング対象表示エラー: {e}")

            # 元のフレーム描画
            if self.isVisible():  # 最終的なウィンドウ状態確認
                self.video_label.setPixmap(
                    pix.scaled(
                        self.video_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            painter.end()  # 必ずパイプを閉じる
        except Exception as e:
            # QPainter関連のエラーをキャッチして安全に終了
            print(f"描画エラー: {e}")
            try:
                if 'painter' in locals() and painter.isActive():
                    painter.end()
            except:
                pass
            return

    def _get_color_name_from_range(self, lower_bound: np.ndarray, upper_bound: np.ndarray) -> str:
        """HSV範囲から色名を取得"""
        # ここでは簡易的な判定を行う
        if (lower_bound[0] >= 0 and lower_bound[0] <= 10 and
            upper_bound[0] >= 10 and upper_bound[0] <= 255):
            return "赤"
        elif (lower_bound[0] >= 140 and lower_bound[0] <= 170 and
              upper_bound[0] >= 140 and upper_bound[0] <= 255):
            return "ピンク"
        else:
            return "不明"  # デフォルトは不明

    def _draw_tracking_highlight(self, painter: QPainter, frame: np.ndarray, lower_bound: np.ndarray, upper_bound: np.ndarray) -> None:
        """追跡対象の色範囲を視覚的にハイライト表示"""
        try:
            # フレームがnumpy配列でない場合は処理しない
            if not isinstance(frame, np.ndarray):
                return

            # 画像形式を確認し、必要に応じて変換
            if len(frame.shape) == 2:  # モノクロ画像の場合
                # カラー画像に変換
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            elif len(frame.shape) == 3 and frame.shape[2] == 1:  # 単一チャンネルの画像の場合
                # カラー画像に変換
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

            # カラー範囲を用いてマスクを作成
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, lower_bound, upper_bound)

            # マスクから輪郭を検出
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return

            # 最大の輪郭を取得して描画
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)

            # ボールの位置をハイライト表示（赤い四角形で囲む）
            pen = QPen(QColor(255, 0, 0), 3)  # 赤い線
            painter.setPen(pen)
            painter.drawRect(x, y, w, h)

        except Exception as e:
            print(f"ハイライト表示エラー: {e}")

    def closeEvent(self, event) -> None:
        """ウィンドウを閉じる際の処理"""
        # タイマーを停止
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
        
        # 描画処理が完了するまで待機（タイムアウト付き）
        try:
            import time
            start_time = time.time()
            # ウィンドウが閉じられる前に、すべての描画処理を安全に終了
            while self.isVisible() and (time.time() - start_time) < 2:  # 2秒間待機
                QApplication.processEvents()  # Qtイベントを処理
                time.sleep(0.01)
        except Exception as e:
            print(f"クローズ待機エラー: {e}")
        
        # クローズ処理を安全に実行
        try:
            super().closeEvent(event)
        except Exception as e:
            print(f"クローズ処理エラー: {e}")
            # 例外が発生しても強制的にクローズ
            event.accept()
