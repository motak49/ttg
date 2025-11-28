# track_target_config.py
import json
import os
from typing import Dict, Any, Optional, Tuple

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QPushButton,
    QComboBox,
    QGridLayout,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from common.config import TRACK_TARGET_CONFIG_FPS, timer_interval_ms
from PyQt6.QtGui import QPainter, QColor, QPen, QImage, QPixmap, QCloseEvent, QFont
from backend.camera_manager import CameraManager
from backend.screen_manager import ScreenManager
from backend.ball_tracker import BallTracker
import cv2
import numpy as np
from common.logger import logger

# 永続化設定ファイルのパス
from common.config import TRACKED_TARGET_CONFIG_PATH
CONFIG_PATH = TRACKED_TARGET_CONFIG_PATH


class TrackTargetConfig(QWidget):
    """
    トラック対象設定と確認を統合した画面
    カメラ映像を表示し、HSV値のスライダーでリアルタイムにトラッキング対象を調整できる
    
    【改善点】
    - HSV値、検出状態を数値表示
    - マスク範囲をビジュアルで表示（検出ピクセルの可視化）
    - 検出輪郭をすべて表示、最大輪郭を赤枠で強調
    """

    # 設定変更シグナル
    config_changed = pyqtSignal(dict)

    def __init__(self, camera_manager: CameraManager, screen_manager: ScreenManager, ball_tracker: BallTracker) -> None:
        super().__init__()
        self.setWindowTitle("トラッキング対象設定・確認")
        self.setGeometry(100, 100, 1000, 800)

        self.camera_manager = camera_manager
        self.screen_manager = screen_manager
        self.ball_tracker = ball_tracker
        
        # デバッグ情報を保持
        self.last_detection_info: Dict[str, Any] = {
            "pixel_count": 0,
            "contour_count": 0,
            "max_area": 0,
            "detected_position": None,
        }

        # カメラ映像を表示する QLabel
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(800, 600)

        # ボタンレイアウト
        button_layout = QHBoxLayout()
        
        # カメラモード選択
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["カラー", "モノクロ"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        button_layout.addWidget(QLabel("カメラモード:"))
        button_layout.addWidget(self.mode_combo)
        
        # 戻るボタン
        self.back_btn = QPushButton("戻る")
        self.back_btn.clicked.connect(self.close)
        button_layout.addWidget(self.back_btn)

        # HSVスライダーのレイアウト
        hsv_layout = QVBoxLayout()
        hsv_layout.addWidget(QLabel("HSV値調整 (赤)"))
        
        # 現在のHSV値を表示するラベル
        self.hsv_value_label = QLabel("H: 0°  S: 100  V: 100")
        hsv_value_font = self.hsv_value_label.font()
        hsv_value_font.setPointSize(11)
        hsv_value_font.setBold(True)
        self.hsv_value_label.setFont(hsv_value_font)
        hsv_layout.addWidget(self.hsv_value_label)
        
        # H, S, V のスライダー
        self.h_slider = QSlider(Qt.Orientation.Horizontal)
        self.h_slider.setMinimum(0)
        self.h_slider.setMaximum(180)
        self.h_slider.setValue(0)
        self.h_slider.valueChanged.connect(self.on_hsv_changed)  # type: ignore
        hsv_layout.addWidget(QLabel("H (色相): 0° ～ 180°"))
        hsv_layout.addWidget(self.h_slider)
        
        self.s_slider = QSlider(Qt.Orientation.Horizontal)
        self.s_slider.setMinimum(0)
        self.s_slider.setMaximum(255)
        self.s_slider.setValue(100)
        self.s_slider.valueChanged.connect(self.on_hsv_changed)  # type: ignore
        hsv_layout.addWidget(QLabel("S (彩度): 0 ～ 255"))
        hsv_layout.addWidget(self.s_slider)
        
        self.v_slider = QSlider(Qt.Orientation.Horizontal)
        self.v_slider.setMinimum(0)
        self.v_slider.setMaximum(255)
        self.v_slider.setValue(100)
        self.v_slider.valueChanged.connect(self.on_hsv_changed)  # type: ignore
        hsv_layout.addWidget(QLabel("V (明度): 0 ～ 255"))
        hsv_layout.addWidget(self.v_slider)
        
        # 検出状態を表示するラベル
        self.detection_status_label = QLabel("検出状態: 未検出")
        detection_status_font = self.detection_status_label.font()
        detection_status_font.setPointSize(10)
        self.detection_status_label.setFont(detection_status_font)
        self.detection_status_label.setStyleSheet("color: #cc0000;")  # 赤色
        hsv_layout.addWidget(self.detection_status_label)

        # 最小面積スライダー
        min_area_layout = QVBoxLayout()
        min_area_layout.addWidget(QLabel("最小面積 (ピクセル)"))
        self.min_area_slider = QSlider(Qt.Orientation.Horizontal)
        self.min_area_slider.setMinimum(10)
        self.min_area_slider.setMaximum(200)
        self.min_area_slider.setValue(self.ball_tracker.min_area)
        self.min_area_slider.valueChanged.connect(self.on_min_area_changed)  # type: ignore
        min_area_layout.addWidget(self.min_area_slider)
        
        # 現在の最小面積値を表示
        self.min_area_value_label = QLabel(f"最小面積: {self.ball_tracker.min_area} pixels")
        min_area_layout.addWidget(self.min_area_value_label)

        # レイアウト設定
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.video_label)
        main_layout.addLayout(button_layout)
        main_layout.addLayout(hsv_layout)
        main_layout.addLayout(min_area_layout)
        self.setLayout(main_layout)

        # タイマーで映像を更新（120fps固定: ハードウェア上限）
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)  # type: ignore
        import logging
        fps_setting = TRACK_TARGET_CONFIG_FPS
        timer_interval = timer_interval_ms(fps_setting)
        logging.info(f"[TrackTargetConfig] FPS設定: {fps_setting} FPS, タイマー間隔: {timer_interval} ms で起動")
        self.timer.start(timer_interval)  # 120fps（ハードウェア上限）(config)

        # 現在の設定を保持
        self.current_config: Dict[str, Any] = {
            "mode": "カラー",  # カラー or モノクロ
            "h_min": 0,
            "s_min": 100,
            "v_min": 100,
            "h_max": 10,
            "s_max": 255,
            "v_max": 255,
        }

        # 永続化設定をロード
        self.load_config()

    def load_config(self) -> None:
        """永続化ファイルから設定を読み込み、UI に反映"""
        if not os.path.exists(CONFIG_PATH):
            return
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self.current_config.update(cfg)

            # UI の状態を更新
            mode = self.current_config.get("mode", "カラー")
            if mode in ["カラー", "モノクロ"]:
                idx = self.mode_combo.findText(mode)
                if idx >= 0:
                    self.mode_combo.setCurrentIndex(idx)

            self.h_slider.setValue(self.current_config.get("h_min", 0))
            self.s_slider.setValue(self.current_config.get("s_min", 100))
            self.v_slider.setValue(self.current_config.get("v_min", 100))
        except Exception as e:
            print(f"設定ロードエラー: {e}")

    def persist_config(self) -> None:
        """現在の設定をファイルに保存"""
        try:
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.current_config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"設定永続化エラー: {e}")

    def update_frame(self) -> None:
        """
        カメラフレーム取得 → QLabel に描画 + オーバーレイ
        
        【改善点】
        - 検出状態ラベルを常時更新
        """
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

            self.draw_tracking_highlight(painter, frame)

            self.video_label.setPixmap(
                pix.scaled(
                    self.video_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        except Exception as e:
            print(f"描画エラー: {e}")
        finally:
            painter.end()
        
        # 検出状態ラベルを常時更新
        self.update_detection_status_label()

    def draw_tracking_highlight(self, painter: QPainter, frame: Any) -> None:
        """
        トラッキング対象の色範囲を視覚的にハイライト表示
        
        【改善点】
        - マスク内のピクセルを半透明で表示
        - 検出輪郭をすべて描画
        - 最大輪郭を赤枠で強調
        - 検出統計情報をメモリに保存
        """
        try:
            h_min = self.current_config["h_min"]
            s_min = self.current_config["s_min"]
            v_min = self.current_config["v_min"]
            h_max = self.current_config["h_max"]
            s_max = self.current_config["s_max"]
            v_max = self.current_config["v_max"]

            if isinstance(frame, np.ndarray):
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)  # type: ignore
                lower_bound = np.array([h_min, s_min, v_min], dtype=np.uint8)
                upper_bound = np.array([h_max, s_max, v_max], dtype=np.uint8)
            else:
                return

            # マスク生成
            mask = cv2.inRange(hsv, lower_bound, upper_bound)  # type: ignore
            
            # 検出ピクセル数を記録
            pixel_count = np.count_nonzero(mask)
            self.last_detection_info["pixel_count"] = pixel_count

            # マスク内のピクセルを半透明で画面上に可視化
            # フレームのコピーを作成してマスク領域に色を付ける
            overlay = frame.copy()
            overlay[mask > 0] = [0, 255, 0]  # 緑色でマスク領域を表示
            alpha = 0.3
            frame = cv2.addWeighted(frame, 1 - alpha, overlay, alpha, 0)  # type: ignore

            # 輪郭検出
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # type: ignore
            self.last_detection_info["contour_count"] = len(contours)

            if not contours:
                self.last_detection_info["max_area"] = 0
                self.last_detection_info["detected_position"] = None
                return

            # 最小面積でフィルタ
            contours = [c for c in contours if cv2.contourArea(c) >= self.ball_tracker.min_area]  # type: ignore
            self.last_detection_info["contour_count"] = len(contours)
            
            if not contours:
                self.last_detection_info["max_area"] = 0
                self.last_detection_info["detected_position"] = None
                return

            # すべての輪郭を薄い青で描画
            cv2.drawContours(frame, contours, -1, (255, 100, 0), 2)  # type: ignore

            # 最大輪郭を検出
            largest_contour = max(contours, key=cv2.contourArea)  # type: ignore
            max_area = cv2.contourArea(largest_contour)  # type: ignore
            self.last_detection_info["max_area"] = int(max_area)
            
            x, y, w, h = cv2.boundingRect(largest_contour)  # type: ignore
            center_x = x + w // 2
            center_y = y + h // 2
            self.last_detection_info["detected_position"] = (center_x, center_y)

            # 最大輪郭を赤枠で強調
            pen = QPen(QColor(0, 0, 255), 3)
            painter.setPen(pen)
            painter.drawRect(x, y, w, h)
            
            # 中心に大きな青い円を描画（検出位置をマーク）
            circle_pen = QPen(QColor(0, 255, 255), 2)
            painter.setPen(circle_pen)
            painter.drawEllipse(center_x - 10, center_y - 10, 20, 20)

        except Exception as e:
            print(f"ハイライト表示エラー: {e}")

    def on_hsv_changed(self, value: int) -> None:
        """
        HSVスライダー変更時の処理
        
        【改善点】
        - 現在のHSV値を数値ラベルに表示
        - BallTracker に反映
        - 検出状態を更新
        """
        self.current_config["h_min"] = self.h_slider.value()
        self.current_config["s_min"] = self.s_slider.value()
        self.current_config["v_min"] = self.v_slider.value()
        # 修正: h_max も更新
        self.current_config["h_max"] = min(self.current_config["h_min"] + 10, 180)
        # 修正: s_max と v_max も更新
        self.current_config["s_max"] = self.s_slider.value()
        self.current_config["v_max"] = self.v_slider.value()
        
        # UI に現在値を表示
        h_val = self.h_slider.value()
        s_val = self.s_slider.value()
        v_val = self.v_slider.value()
        self.hsv_value_label.setText(f"H: {h_val}°  S: {s_val}  V: {v_val}")

        # BallTracker に反映
        lower_bound = np.array(
            [self.current_config["h_min"], self.current_config["s_min"], self.current_config["v_min"]], 
            dtype=np.uint8
        )
        upper_bound = np.array(
            [self.current_config["h_max"], self.current_config["s_max"], self.current_config["v_max"]], 
            dtype=np.uint8
        )
        # 修正: 新しい引数を渡すように変更
        self.ball_tracker.set_track_ball(
            (lower_bound, upper_bound),
            sat_low=self.current_config["s_min"],
            sat_high=self.current_config["s_max"],
            val_low=self.current_config["v_min"],
            val_high=self.current_config["v_max"]
        )

        self.config_changed.emit(self.current_config)
        self.persist_config()
        
        # 検出状態ラベルを更新（次のフレーム更新時に反映される）
        self.update_detection_status_label()

    def on_min_area_changed(self, value: int) -> None:
        """
        最小面積スライダー変更時の処理
        
        【改善点】
        - 最小面積値をラベルに表示
        - BallTracker に反映
        """
        self.ball_tracker.set_min_area(value)
        self.min_area_slider.setValue(value)
        self.min_area_value_label.setText(f"最小面積: {value} pixels")
        self.persist_config()
        print(f"Min area set to {value} pixels")
    
    def update_detection_status_label(self) -> None:
        """
        検出状態ラベルを更新
        最新の検出情報を表示
        """
        pixel_count = self.last_detection_info.get("pixel_count", 0)
        contour_count = self.last_detection_info.get("contour_count", 0)
        max_area = self.last_detection_info.get("max_area", 0)
        detected_pos = self.last_detection_info.get("detected_position")
        
        if pixel_count == 0 or contour_count == 0:
            self.detection_status_label.setText("検出状態: ✗ 未検出")
            self.detection_status_label.setStyleSheet("color: #cc0000;")  # 赤
        else:
            if detected_pos:
                pos_str = f"({detected_pos[0]}, {detected_pos[1]})"
            else:
                pos_str = "N/A"
            status_text = (
                f"検出状態: ✓ 検出中 | "
                f"ピクセル: {pixel_count} | "
                f"輪郭: {contour_count} | "
                f"最大面積: {max_area:.0f} | "
                f"位置: {pos_str}"
            )
            self.detection_status_label.setText(status_text)
            self.detection_status_label.setStyleSheet("color: #00aa00;")  # 緑

    def on_mode_changed(self, mode: str) -> None:
        """カメラモード変更時の処理"""
        self.current_config["mode"] = mode
        self.save_current_config()

    def save_current_config(self) -> None:
        """現在の設定を保存し、BallTracker に反映"""
        try:
            lower_bound = np.array(
                [self.current_config["h_min"], self.current_config["s_min"], self.current_config["v_min"]],
                dtype=np.uint8,
            )
            upper_bound = np.array(
                [self.current_config["h_max"], self.current_config["s_max"], self.current_config["v_max"]],
                dtype=np.uint8,
            )
            self.ball_tracker.set_track_ball((lower_bound, upper_bound))
            self.persist_config()
        except Exception as e:
            print(f"設定保存エラー: {e}")

    def closeEvent(self, a0: Optional[QCloseEvent] = None) -> None:
        """ウィンドウクローズ時の処理"""
        if hasattr(self, "timer") and self.timer.isActive():
            self.timer.stop()
        super().closeEvent(a0)
