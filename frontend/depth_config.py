import json
import os
import logging
from typing import Optional, List, Tuple, Dict, Any

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QImage, QPixmap, QCloseEvent, QMouseEvent
from common.config import TRACK_TARGET_CONFIG_FPS, timer_interval_ms
from backend.camera_manager import CameraManager
from backend.screen_manager import ScreenManager

# 深度ログファイルのパス（プロジェクトルートからの絶対パスに変更）
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))   # frontend の親ディレクトリ (ttg)
DEPTH_LOG_PATH = os.path.join(BASE_DIR, "ScreenDepthLogs", "depth_log.json")


class DepthConfig(QWidget):
    """
    深度設定画面
    カメラ映像をグリッド付きで表示し、クリックした座標の深度を表示・保存可能
    """

    def __init__(self, camera_manager: CameraManager, screen_manager: ScreenManager) -> None:
        super().__init__()
        self.setWindowTitle("深度設定")
        self.setGeometry(100, 100, 1000, 700)

        self.camera_manager = camera_manager
        self.screen_manager = screen_manager

        # カメラ映像を表示する QLabel
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(800, 600)
        self.video_label.mousePressEvent = self.on_video_click  # クリックハンドラの設定

        # 深度表示用ラベル
        self.depth_label = QLabel(self)
        self.depth_label.setText("Depth: -- mm")
        self.depth_label.setStyleSheet("font-size: 16px; color: blue;")

        # デバッグオプション
        self._debug_confidence = False
        self._debug_contrast = False

        # ボタンレイアウト
        button_layout = QHBoxLayout()
        
        # 戻るボタン
        self.back_btn = QPushButton("戻る")
        self.back_btn.clicked.connect(self.close)
        button_layout.addWidget(self.back_btn)

        # 保存ボタン
        self.save_btn = QPushButton("深度を保存")
        self.save_btn.clicked.connect(self.save_depths)
        button_layout.addWidget(self.save_btn)

        # レイアウト設定
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.video_label)
        main_layout.addWidget(self.depth_label)  # 深度表示ラベルを追加
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        # タイマーで映像を更新（120fps固定）
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(timer_interval_ms(TRACK_TARGET_CONFIG_FPS))  # 約120fps (config)

        # クリックされた座標リスト
        self.click_points: List[Tuple[int, int]] = []
        # フレームと表示サイズの情報（座標変換用）
        self._frame_width = 0
        self._frame_height = 0
        self._displayed_width = 0
        self._displayed_height = 0
        # 深度フレームサイズ（座標変換用）
        self._depth_width = 0
        self._depth_height = 0

    def update_frame(self) -> None:
        """カメラフレーム取得 → QLabel に描画 + グリッドとクリックポイントをオーバーレイ"""
        try:
            frame = self.camera_manager.get_frame()
        except Exception as e:
            print(f"カメラ取得エラー: {e}")
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
                print(f"フレーム取得時の形状エラー: {e}")
                return
        pix = QPixmap.fromImage(q_img)

        painter = QPainter(pix)
        try:
            width = pix.width()
            height = pix.height()

            # グリッド線を描画 (10x10 マス)
            self.draw_grid(painter, width, height)

            # クリックされたポイントを描画（青い円）
            for point in self.click_points:
                x, y = point
                painter.setPen(QPen(QColor(0, 0, 255), 3))  # 青色
                painter.drawEllipse(x - 25, y - 25, 50, 50)  # 半径25の円

            # 信頼度マップをオーバーレイ表示（デバッグ時のみ）
            if self._debug_confidence:
                confidence_map = self.camera_manager.get_confidence_map()
                if confidence_map is not None:
                    try:
                        import cv2
                        # 信頼度マップを画像に変換（0〜255のグレースケール）
                        confidence_display = cv2.normalize(confidence_map, None, 0, 255, cv2.NORM_MINMAX)
                        confidence_qimg = QImage(
                            confidence_display.data,
                            confidence_display.shape[1],
                            confidence_display.shape[0],
                            confidence_display.strides[0],
                            QImage.Format.Format_Grayscale8
                        )
                        confidence_pixmap = QPixmap.fromImage(confidence_qimg)
                        # 画像を合成して半透明で表示（サイズは適宜調整）
                        painter.setOpacity(0.5)
                        painter.drawPixmap(0, 0, confidence_pixmap.scaled(width, height))
                        painter.setOpacity(1.0)
                    except Exception as e:
                        print(f"信頼度マップ描画エラー: {e}")

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
            
            # 深度フレームのサイズを取得
            depth_frame = self.camera_manager.get_depth_frame()
            if depth_frame is not None:
                self._depth_width, self._depth_height = depth_frame.shape[1], depth_frame.shape[0]
            else:
                self._depth_width = 0
                self._depth_height = 0
        except Exception as e:
            print(f"描画エラー: {e}")
        finally:
            painter.end()

    def draw_grid(self, painter: QPainter, width: int, height: int) -> None:
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

    def on_video_click(self, event: Optional[QMouseEvent] = None) -> None:
        """映像上でのクリック処理"""
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
        scale_x = self._frame_width / self._displayed_width
        scale_y = self._frame_height / self._displayed_height

        # 元フレーム座標に変換（丸め誤差を減らすため float で計算後 int に変換）
        img_x = int(round(x_rel * scale_x))
        img_y = int(round(y_rel * scale_y))

        # 座標をフレーム範囲内にクランプ（端のピクセルが範囲外になる問題を回避）
        img_x = max(0, min(self._frame_width - 1, img_x))
        img_y = max(0, min(self._frame_height - 1, img_y))

        # クリック座標リストへ保存（元画像座標で保持）
        self.click_points.append((img_x, img_y))

        # 深度情報を取得して表示
        try:
            # デバッグ用に座標変換の詳細を出力
            if self._depth_width > 0 and self._depth_height > 0:
                print(f"[DEBUG] Frame size: {self._frame_width}x{self._frame_height}, Depth size: {self._depth_width}x{self._depth_height}")
                print(f"[DEBUG] Clicked point: ({img_x}, {img_y})")
                depth_scale_x = self._depth_width / self._frame_width
                depth_scale_y = self._depth_height / self._frame_height
                depth_x = int(img_x * depth_scale_x)
                depth_y = int(img_y * depth_scale_y)
                # 深度フレームの範囲内にクランプ
                depth_x = max(0, min(self._depth_width - 1, depth_x))
                depth_y = max(0, min(self._depth_height - 1, depth_y))
                print(f"[DEBUG] Converted depth point: ({depth_x}, {depth_y})")
                # 生の深度値を取得し、表示前に確認
                raw_depth = self.camera_manager.get_depth_mm(depth_x, depth_y)
                print(f"[DEBUG] Raw depth (mm): {raw_depth} mm")
                # 補正なし（統一されたロジック）
                depth_mm = raw_depth
                print(f"[DEBUG] Final depth (mm): {depth_mm:.1f} mm")
            else:
                # 深度フレームが取得できない場合は元の座標を使用
                raw_depth = self.camera_manager.get_depth_mm_at(img_x, img_y)
                print(f"[DEBUG] Raw depth value (fallback): {raw_depth} mm")
                depth_mm = raw_depth  # 補正なし
            self.depth_label.setText(f"Depth: {depth_mm:.1f} mm")
        except Exception as e:
            print(f"深度取得エラー: {e}")
            self.depth_label.setText("Depth: Error")

    def save_depths(self) -> None:
        """クリックされた座標の深度をログファイルに保存（X,Y は保存しない）"""
        if not self.click_points:
            return

        try:
            # 最後にクリックした画像座標 (フレーム座標)
            img_x, img_y = self.click_points[-1]

            # 深度フレームサイズが取得できているか確認
            if self._depth_width > 0 and self._depth_height > 0:
                # フレーム → 深度フレームのスケール変換
                depth_scale_x = self._depth_width / self._frame_width
                depth_scale_y = self._depth_height / self._frame_height
                depth_x = int(img_x * depth_scale_x)
                depth_y = int(img_y * depth_scale_y)

                # 範囲外アクセス防止（クランプ）
                depth_x = max(0, min(self._depth_width - 1, depth_x))
                depth_y = max(0, min(self._depth_height - 1, depth_y))

                depth_mm = self.camera_manager.get_depth_mm_at(depth_x, depth_y)
                # 無効深度値（0 または NaN）を除外し、表示と保存をスキップ
                if not depth_mm or depth_mm <= 0:
                    print(f"[WARN] Invalid depth value detected: {depth_mm} mm. Skipping.")
                    self.depth_label.setText("Depth: N/A")
                    return
                # 深度が上限を超える場合は無効とみなす
                from common.config import MAX_VALID_DEPTH_MM
                if depth_mm > MAX_VALID_DEPTH_MM:
                    print(f"[WARN] Depth value exceeds limit ({MAX_VALID_DEPTH_MM} mm). Skipping.")
                    self.depth_label.setText("Depth: N/A")
                    return
            else:
                # 深度フレーム取得失敗時は画像座標で取得（フォールバック）
                depth_mm = self.camera_manager.get_depth_at(img_x, img_y)

            # デバッグ出力（ターミナルに表示させるだけ）
            logging.debug(f"保存対象深度: ({depth_x if self._depth_width>0 else img_x}, "
                          f"{depth_y if self._depth_height>0 else img_y}) -> {depth_mm:.1f} mm")

            # 単一値で保存（辞書形式） - screen_depth キーに統一
            data = {"screen_depth": round(depth_mm, 1)}
            os.makedirs(os.path.dirname(DEPTH_LOG_PATH), exist_ok=True)
            with open(DEPTH_LOG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            print("深度ログが保存されました。")
            self.click_points.clear()  # 保存後はクリア
            self.depth_label.setText("Depth: -- mm")

        except Exception as e:
            print(f"深度保存エラー: {e}")

    def closeEvent(self, a0: Optional[QCloseEvent] = None) -> None:
        """ウィンドウクローズ時の処理"""
        if hasattr(self, "timer") and self.timer.isActive():
            self.timer.stop()
        super().closeEvent(a0)
