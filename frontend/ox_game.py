# ox_game.py
"""
OXゲーム（Tick & Cross）実装

- カメラ映像を表示し、リアルタイムでボールヒット座標を取得
- ヒット座標から 3×3 グリッドのセルへ変換
- プレイヤー交代でマーカー (〇/✕) を配置
- 勝利判定後にメッセージ表示し、盤面をリセット

依存:
    - PyQt6
    - backend.camera_manager.CameraManager
    - backend.screen_manager.ScreenManager
    - backend.ball_tracker.BallTracker
    - frontend.game_logic.GameLogic
"""

import numpy as np
from typing import Tuple, Optional

from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QMessageBox,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, QElapsedTimer
from common.config import OX_GAME_TARGET_FPS, TARGET_FPS, timer_interval_ms, GRID_LINE_WIDTH
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QFont, QCloseEvent

from backend.camera_manager import CameraManager
from backend.screen_manager import ScreenManager
from backend.ball_tracker import BallTracker
from frontend.game_logic import GameLogic


class OxGame(QWidget):
    """OXゲームウィジェット"""

    def __init__(
        self,
        camera_manager: CameraManager,
        screen_manager: ScreenManager,
        ball_tracker: BallTracker,
    ) -> None:
        super().__init__()
        self.setWindowTitle("OXゲーム")
        self.move(100, 100)
        self.resize(800, 600)   # 起動時サイズを領域設定と同じにし、以降はリサイズ可能

        # バックエンドコンポーネント
        self.camera_manager = camera_manager
        self.screen_manager = screen_manager
        # 永続化されたスクリーン領域・深度情報をロード
        self.screen_manager.load_log()
        self.ball_tracker = ball_tracker

        # ゲームロジック
        self.game_logic = GameLogic()
        self.game_logic.start_game("tick_cross")
        # 1: 壱号 (〇), 2: 弐号 (✕)
        self.current_player = 1
        self.debug = True
        self.collision_shown = False  # whether large blue circle has been drawn for current turn
        self.last_collision_point: Optional[Tuple[int, int]] = None
        self.first_hit_coord: Optional[Tuple[int, int]] = None

        # UI 要素
        self.fps_label = QLabel(self)
        self.fps_label.setText(f"FPS: {OX_GAME_TARGET_FPS}")

        # FPS計算用変数
        self.frame_count = 0
        self.last_time = QElapsedTimer()
        self.last_time.start()

        self.player_label = QLabel(self)
        self._update_player_label()

        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.video_label.setScaledContents(True)
        self.video_label.setMinimumSize(0, 0)

        layout = QVBoxLayout()
        layout.addWidget(self.fps_label)
        layout.addWidget(self.player_label)
        layout.addWidget(self.video_label)
        self.setLayout(layout)

        # タイマーでフレーム更新 & ヒット判定
        self.tracking_active = True
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)
        self.timer.start(timer_interval_ms(OX_GAME_TARGET_FPS))  # 約30fps (config)

    def _update_player_label(self) -> None:
        if self.current_player == 1:
            name, marker = "壱号", "〇"
        else:
            name, marker = "弐号", "✕"
        self.player_label.setText(f"現在のプレイヤー: {name} ({marker})")

    def _process_hit(self, hit_area: Tuple[int, int, float]) -> None:
        # 座標 → グリッド変換
        # 初回ヒット座標を記録（未設定の場合）
        if self.first_hit_coord is None:
            self.first_hit_coord = (hit_area[0], hit_area[1])
        row, col = self.game_logic.coords_to_grid(hit_area)

        # 盤面更新（上書き可）
        self.game_logic.board[(row, col)] = self.current_player

        # 勝利判定
        if self.game_logic.check_victory(self.current_player):
            QMessageBox.information(
                self,
                "勝利",
                f"プレイヤー {self.current_player} の勝ち！",
            )
            # 盤面リセット
            self.game_logic.board.clear()
            # ヒット座標のリセット（次ラウンド用）
            self.first_hit_coord = None
        else:
            # プレイヤー交代
            self.current_player = 2 if self.current_player == 1 else 1
            self._update_player_label()

    def _draw_markers(self, painter: QPainter, cell_w: int, cell_h: int) -> None:
        """盤面上のマーカー (〇/✕) を描画"""
        for (r, c), pid in self.game_logic.board.items():
            marker = "〇" if pid == 1 else "✕"
            color = QColor("#FF0000") if pid == 1 else QColor("#000000")
            painter.setPen(QPen(color))
            font = QFont()
            # セルサイズに合わせてフォントを調整
            font.setPointSize(min(cell_w, cell_h) // 2)
            painter.setFont(font)

            x_center = c * cell_w + cell_w // 2
            y_center = r * cell_h + cell_h // 2

            # テキストは中心に揃えるため、簡易的にオフセット調整
            metrics = painter.fontMetrics()
            text_width = metrics.horizontalAdvance(marker)
            text_height = metrics.height()

            painter.drawText(
                x_center - text_width // 2,
                y_center + text_height // 4,
                marker,
            )

    def _draw_grid(self, painter: QPainter, width: int, height: int) -> None:
        """3×3 グリッド描画"""
        pen = QPen(QColor(0, 0, 0), GRID_LINE_WIDTH)
        painter.setPen(pen)

        cell_w = width // 3
        cell_h = height // 3

        # 縦線
        for i in range(1, 3):
            x = i * cell_w
            painter.drawLine(x, 0, x, height)

        # 横線
        for i in range(1, 3):
            y = i * cell_h
            painter.drawLine(0, y, width, y)

    def _show_start_dialog(self) -> bool:
        dlg = QMessageBox(self)
        dlg.setWindowTitle("ゲームスタート")
        dlg.setText("ゲームを開始しますか？")
        dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
        result = dlg.exec()
        return result == QMessageBox.StandardButton.Ok

    def pause_tracking(self) -> None:
        """トラッキングを一時停止し、タイマーとフラグをオフにする"""
        if self.tracking_active:
            self.timer.stop()
            self.tracking_active = False

    def resume_tracking(self) -> None:
        """トラッキング再開。タイマー開始とフラグオン。衝突表示フラグリセット"""
        if not self.tracking_active:
            self.tracking_active = True
            self.timer.start(timer_interval_ms(OX_GAME_TARGET_FPS))
            self.collision_shown = False


    def _show_collision_stop_message(self) -> None:
        """衝突検知時にゲームを停止し、OK が押されるまで待機する"""
        self.pause_tracking()
        msg = QMessageBox(self)
        msg.setWindowTitle("衝突検知")
        msg.setText("ターゲットが衝突しました。続行するには OK を押してください。")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        # exec() はモーダルでブロックし、ユーザーの操作を待つ
        msg.exec()
        # OK 押下後1秒スリープ
        QTimer.singleShot(1000, self.resume_tracking)

    def _update_frame(self) -> None:
        """カメラフレーム取得 → UI 更新 + ヒット判定"""
        try:
            frame = self.camera_manager.get_frame()
        except Exception as e:
            # ログに出すだけで UI はそのまま
            print(f"カメラ取得エラー: {e}")
            frame = None

        if frame is None:
            # ウィンドウサイズに応じたプレースホルダー生成
            width = self.video_label.width() or self.width()
            height = self.video_label.height() or self.height()
            # ウィンドウがまだ初期化されていない場合、デフォルト値を設定
            if width <= 0 or height <= 0:
                width, height = 800, 600
            placeholder = QImage(width, height, QImage.Format.Format_RGB888)
            placeholder.fill(Qt.GlobalColor.lightGray)
            q_img = placeholder
        else:
            # OpenCV の ndarray → QImage に変換
            if isinstance(frame, np.ndarray):
                # Determine height and width (supports grayscale or color)
                h, w = frame.shape[:2]
                if len(frame.shape) == 2:
                    bytes_per_line = w
                    img_format = QImage.Format.Format_Grayscale8
                else:
                    bytes_per_line = 3 * w
                    img_format = QImage.Format.Format_BGR888

                q_img = QImage(
                    frame.data,
                    w,
                    h,
                    bytes_per_line,
                    img_format,
                )
            else:
                # 既に QImage の場合はそのまま使用
                q_img = frame

        pix = QPixmap.fromImage(q_img)

        # デバッグ用トラッキング情報取得
        detected = None
        hit = None
        if isinstance(frame, np.ndarray):
            detected = self.ball_tracker.get_hit_area(frame)
            hit = self.ball_tracker.check_target_hit(frame)
        else:
            detected = None
            hit = None

        painter = QPainter(pix)
        width, height = pix.width(), pix.height()

        # グリッド描画
        self._draw_grid(painter, width, height)

        # 既に取得したマーカー描画
        cell_w = width // 3
        cell_h = height // 3
        self._draw_markers(painter, cell_w, cell_h)

        # デバッグ描画: 検出されたボール位置 (緑の円) と深度表示
        if self.debug and self.tracking_active and detected is not None:
            x, y, depth = detected
            painter.setPen(QPen(QColor(0, 255, 0), 3))
            size = 30
            painter.drawRect(x - size // 2, y - size // 2, size, size)
            # 深度テキスト表示
            painter.setPen(QPen(QColor(0, 255, 0), 1))
            painter.drawText(x + size // 2 + 2, y - size // 2 - 2, f"{depth:.2f}")

        # ヒットが検出された場合は青い円で強調し深度表示
        if self.debug and self.tracking_active and hit is not None:
            hx, hy, hdepth = hit
            if not self.collision_shown:
                painter.setPen(QPen(QColor(0, 0, 255), 3))
                radius_hit = 50
                painter.drawEllipse(hx - radius_hit, hy - radius_hit, radius_hit * 2, radius_hit * 2)
                self.collision_shown = True
            # 深度テキスト表示（青）
            painter.setPen(QPen(QColor(0, 0, 255), 1))
            painter.drawText(hx + 52, hy - 48, f"{hdepth:.2f}")
            # 衝突座標をターミナルに出力
            print(f"Hit at ({hx}, {hy})")
            # 衝突座標を保持
            self.last_collision_point = (hx, hy)
            # 衝突検知時にゲーム停止 → OK ボタンで再開
            self._show_collision_stop_message()
        # 最初にヒットした座標を塗りつぶしの青円で固定表示
        if self.first_hit_coord is not None:
            fx, fy = self.first_hit_coord
            painter.setPen(QPen(QColor(0, 0, 255), 2))
            painter.setBrush(QColor(0, 0, 255))  # 塗りつぶし
            radius_first = 10
            painter.drawEllipse(fx - radius_first, fy - radius_first, radius_first * 2, radius_first * 2)

        painter.end()
        self.video_label.setPixmap(
            pix.scaled(
                self.video_label.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

        # ヒット判定（既に上部で取得済みの hit を使用）
        if self.tracking_active and hit is not None:
            self._process_hit(hit)

        # FPS計算と表示更新
        self.frame_count += 1
        elapsed = self.last_time.elapsed()
        if elapsed >= 1000:  # 1秒ごとにFPSを計算
            actual_fps = self.frame_count * 1000.0 / elapsed
            self.fps_label.setText(f"FPS: {OX_GAME_TARGET_FPS} (実測: {actual_fps:.1f})")
            self.frame_count = 0
            self.last_time.restart()

    def get_last_collision_point(self) -> Optional[Tuple[int, int]]:
        """直近の衝突座標を返す。衝突が無い場合は None を返す。"""
        return self.last_collision_point

    def closeEvent(self, a0: Optional[QCloseEvent] = None) -> None:
        """ウィンドウ閉じるときにタイマー停止・カメラ解放"""
        self.timer.stop()
        try:
            self.camera_manager.close_camera()
        finally:
            super().closeEvent(a0)
